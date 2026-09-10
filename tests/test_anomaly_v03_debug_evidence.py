"""Evidence format and IO faults using local buffers and a fake kernel only."""

from contextlib import ExitStack
import ctypes as C
import json
from unittest.mock import Mock, patch
import unittest

from tests import test_anomaly_v03_debug_driver as fixtures
from tests.fixtures import anomaly_v03_debug_evidence as e
from tests.fixtures.anomaly_v03_debug_transport import TransportError


class DebugEvidenceTests(unittest.TestCase):
    def evidence(self, stack):
        driver, api, kernel, preflight, tokens, fixture, disk = fixtures.DebugDriverTests().driver(stack)
        preflight.runtime = {"build": "10.0.26200.9445"}
        preflight.rows = preflight.result["sources"]
        driver.run()
        evidence = e.DebugEvidence()
        evidence.capture(driver)
        kernel.reset_mock()
        return evidence, driver, kernel

    def test_round_trip_preserves_unconfirmed_slots_and_separates_drain(self):
        with ExitStack() as stack:
            evidence, driver, kernel = self.evidence(stack)
            self.assertEqual(evidence.capture_state, "captured")
            driver.transport.buffers[7].info.exception.record.address = 0x12345678
            driver.stop.drain.buffers[9].info.exception.record.address = 0x87654321
            driver.transport.wait_inflight = True
            evidence = e.DebugEvidence()
            evidence.capture(driver)
            self.assertEqual(evidence.capture_state, "captured")
            raw = evidence.buffer.raw[:evidence.size]
            magic, size, event_size, slots, regions = evidence.HEADER.unpack_from(raw)
            self.assertEqual((magic, event_size, slots, regions), (b"B1DBG001", 176, 256, 2))
            self.assertEqual(len(raw), evidence.HEADER.size + size + 2 * evidence.REGION_SIZE)
            metadata = json.loads(raw[evidence.HEADER.size:evidence.HEADER.size + size])
            self.assertEqual(metadata["normal"]["confirmed_buffers"], 2)
            self.assertTrue(metadata["normal"]["wait_inflight"])
            self.assertEqual(metadata["drain"]["confirmed_buffers"], 0)
            offset = evidence.HEADER.size + size
            normal = e.DebugEvent.from_buffer_copy(raw, offset + 7 * event_size)
            drain = e.DebugEvent.from_buffer_copy(raw, offset + evidence.REGION_SIZE + 9 * event_size)
            self.assertEqual(normal.info.exception.record.address, 0x12345678)
            self.assertEqual(drain.info.exception.record.address, 0x87654321)
            self.assertFalse(metadata["driver"]["native_accepted"])
            self.assertEqual(metadata["runtime"]["build"], "10.0.26200.9445")
            self.assertLess(evidence.CAPACITY, 1024 * 1024)
            self.assertIs(evidence.owner, driver)
            self.assertNotIn("DUMMY", repr(evidence))

    def test_resource_skip_does_not_copy_or_encode(self):
        with ExitStack() as stack:
            unused, driver, kernel = self.evidence(stack)
            driver.resource_stop = True
            evidence = e.DebugEvidence()
            with patch.object(e.C, "memmove", side_effect=AssertionError("copy")), \
                    patch.object(e.json, "JSONEncoder", side_effect=AssertionError("encode")):
                evidence.capture(driver)
            self.assertEqual(evidence.capture_state, "resource_skipped")
            self.assertTrue(evidence.resource_stop)
            evidence.write(kernel, 801)
            kernel.WriteFile.assert_not_called()

    def test_capture_faults_retain_original_and_never_write_partial_snapshot(self):
        for fault in ("capacity", "oom", "running"):
            with ExitStack() as stack, self.subTest(fault=fault):
                unused, driver, kernel = self.evidence(stack)
                evidence = e.DebugEvidence()
                if fault == "capacity":
                    driver.preflight.runtime = {"build": "x" * evidence.METADATA_LIMIT}
                elif fault == "oom":
                    stack.enter_context(patch.object(e.C, "memmove", side_effect=MemoryError()))
                else:
                    driver.transport.state = "pending"
                evidence.capture(driver)
                self.assertEqual(evidence.capture_state, "failed")
                self.assertIs(evidence.owner, driver)
                self.assertEqual(evidence.size, 0)
                self.assertEqual(evidence.resource_stop, fault == "oom")
                primary = evidence.primary
                evidence.write(kernel, 801)
                self.assertIs(evidence.primary, primary)
                kernel.WriteFile.assert_not_called()

    def test_single_write_flush_and_no_close_or_readback(self):
        with ExitStack() as stack:
            evidence, driver, unused = self.evidence(stack)
            kernel = Mock()
            def write(handle, pointer, size, written, overlapped):
                self.assertEqual(C.string_at(pointer, size), evidence.buffer.raw[:evidence.size])
                written.contents.value = size
                return True
            kernel.WriteFile.side_effect = write
            evidence.write(kernel, 801)
            self.assertEqual(evidence.write_state, "confirmed")
            self.assertEqual(evidence.flush_state, "confirmed")
            self.assertEqual([call[0] for call in kernel.mock_calls], ["WriteFile", "FlushFileBuffers"])
            with self.assertRaises(TransportError):
                # Retry raises the transport contract error, not a second IO.
                evidence.write(kernel, 801)
            kernel.WriteFile.assert_called_once()

    def test_io_failure_and_uncertainty_are_not_retried(self):
        for fault in ("false", "short", "write_oom", "flush_false", "flush_oom"):
            with ExitStack() as stack, self.subTest(fault=fault):
                evidence, driver, unused = self.evidence(stack)
                kernel = Mock()
                def write(handle, pointer, size, written, overlapped):
                    written.contents.value = size - 1 if fault == "short" else size
                    if fault == "write_oom":
                        raise MemoryError()
                    return fault != "false"
                kernel.WriteFile.side_effect = write
                if fault == "flush_oom":
                    kernel.FlushFileBuffers.side_effect = MemoryError()
                else:
                    kernel.FlushFileBuffers.return_value = fault != "flush_false"
                evidence.write(kernel, 801)
                self.assertIsNotNone(evidence.primary)
                self.assertEqual(evidence.resource_stop, fault.endswith("oom"))
                self.assertNotEqual(evidence.flush_state, "confirmed")
                self.assertIs(evidence.owner, driver)
                if fault in ("false", "short", "write_oom"):
                    kernel.FlushFileBuffers.assert_not_called()
                kernel.CloseHandle.assert_not_called()
                self.assertEqual(evidence.written.value, evidence.size - (fault == "short"))
                with self.assertRaises(TransportError):
                    evidence.write(kernel, 801)
                kernel.WriteFile.assert_called_once()

    def test_resource_latch_after_capture_and_wrong_thread_reject_before_io(self):
        for fault in ("resource", "thread"):
            with ExitStack() as stack, self.subTest(fault=fault):
                evidence, driver, unused = self.evidence(stack)
                kernel = Mock()
                if fault == "resource":
                    driver.stop.drain.resource_stop = True
                else:
                    evidence.creator_thread = -1
                evidence.write(kernel, 801)
                self.assertEqual(evidence.write_state, "rejected")
                self.assertEqual(evidence.resource_stop, fault == "resource")
                self.assertEqual(kernel.mock_calls, [])


class EvidenceFileTests(unittest.TestCase):
    def file(self, stack):
        api, fixture = Mock(), Mock()
        stack.enter_context(patch.object(e.C, "get_last_error", return_value=0, create=True))
        api.k.CreateFileW.return_value = 801
        api.k.CloseHandle.return_value = True
        fixture.path.return_value = "C:/DUMMY_PRIVATE/control/startup-evidence.bin"
        fixture.ledger = {e.EvidenceFile.NAME: {"identity": {"file_id": "known"}}}
        stack.enter_context(patch.object(e.w._Bound, "observe", return_value={"file_id": "known"}))
        check = stack.enter_context(patch.object(e.w._Bound, "check"))
        stack.enter_context(patch.object(e.w._Bound, "streams"))
        stack.enter_context(patch.object(e.w, "_verify_sd"))
        return e.EvidenceFile(api), api, fixture, check

    def test_prepare_verifies_private_empty_identity_before_borrowing_and_closes_once(self):
        with ExitStack() as stack:
            owner, api, fixture, check = self.file(stack)
            owner.prepare(fixture)
            self.assertEqual(owner.open_state, "prepared")
            fixture.file.assert_called_once_with(owner.NAME, b"", "private")
            api.k.CreateFileW.assert_called_once_with(str(fixture.path.return_value), 0x40020081,
                                                    1, None, 3, 0x00200000, None)
            self.assertFalse(owner.resolved())
            calls = len(api.mock_calls)
            owner.close()
            self.assertTrue(owner.resolved())
            self.assertIsNone(owner.bound.handle)
            self.assertEqual([call[0] for call in api.mock_calls[calls:]], ["k.CloseHandle"])
            with self.assertRaises(TransportError):
                owner.close()
            api.k.CloseHandle.assert_called_once_with(801)

    def test_prepare_failure_retains_known_or_uncertain_ownership(self):
        for fault in ("create", "open_false", "open_oom", "validate"):
            with ExitStack() as stack, self.subTest(fault=fault):
                owner, api, fixture, check = self.file(stack)
                if fault == "create":
                    fixture.file.side_effect = MemoryError()
                elif fault == "open_false":
                    api.k.CreateFileW.return_value = C.c_void_p(-1).value
                elif fault == "open_oom":
                    api.k.CreateFileW.side_effect = MemoryError()
                else:
                    check.side_effect = MemoryError()
                with self.assertRaises((MemoryError, e.w._Failure)):
                    owner.prepare(fixture)
                if fault == "open_oom":
                    with self.assertRaises(TransportError):
                        owner.close()
                    self.assertFalse(owner.resolved())
                else:
                    owner.close()
                    self.assertTrue(owner.resolved())
                if fault == "validate":
                    api.k.CloseHandle.assert_called_once_with(801)
                else:
                    api.k.CloseHandle.assert_not_called()

    def test_close_failure_retains_handle_without_retry(self):
        for fault in (False, MemoryError()):
            with ExitStack() as stack, self.subTest(fault=type(fault).__name__):
                owner, api, fixture, check = self.file(stack)
                owner.prepare(fixture)
                if fault is False:
                    api.k.CloseHandle.return_value = False
                else:
                    api.k.CloseHandle.side_effect = fault
                with self.assertRaises((MemoryError, e.w._Failure)):
                    owner.close()
                self.assertFalse(owner.resolved())
                self.assertEqual(owner.handle, 801)
                with self.assertRaises(TransportError):
                    owner.close()
                api.k.CloseHandle.assert_called_once()

    def test_native_resource_errors_are_retained_and_latched(self):
        for code in (8, 14, 39, 112, 1450, 1455, 1816):
            with ExitStack() as stack, self.subTest(code=code):
                owner, api, fixture, check = self.file(stack)
                api.k.CreateFileW.return_value = C.c_void_p(-1).value
                stack.enter_context(patch.object(e.C, "get_last_error", return_value=code, create=True))
                with self.assertRaises(e.w._Failure):
                    owner.prepare(fixture)
                self.assertTrue(owner.resource_stop)
                self.assertEqual(owner.primary.error, code)
                owner.close()
                self.assertTrue(owner.resolved())


if __name__ == "__main__":
    unittest.main()
