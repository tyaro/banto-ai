"""Outer driver wiring tests, fake filesystem/runtime and fake Win32 only."""

from contextlib import ExitStack
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from tests import test_anomaly_v03_debug_session as fixtures
from tests.fixtures import anomaly_v03_debug_driver as d
from tests.fixtures.anomaly_v03_debug_transport import BREAKPOINT, DBG_NOT_HANDLED


class DebugDriverTests(unittest.TestCase):
    def driver(self, stack):
        unused, api, kernel, identity, validate, access = fixtures.DebugSessionTests().session(stack)
        api.p = Mock()
        def memory(handle, pointer, size):
            pointer.contents.peak_pagefile = 10
            return True
        def performance(pointer, size):
            pointer.contents.page_size = 4096
            pointer.contents.limit = pointer.contents.physical = 100
            return True
        api.p.GetProcessMemoryInfo.side_effect = memory
        api.p.GetPerformanceInfo.side_effect = performance
        preflight = Mock(started=False, resource_stop=False, primary=None, secondary=None)
        preflight.result = {"status": "verified", "sources": [
            {"path": "src/banto_ai/_anomaly_v03_windows.py", "sha256": "a" * 64, "bytes": 1},
            {"path": "tests/fixtures/anomaly_v03_native_child.py", "sha256": "b" * 64, "bytes": 1}]}
        def verify():
            preflight.started = True
            return preflight.result
        preflight.run.side_effect = verify
        tokens = Mock(status="prepared", resource_stop=False, primary=None, secondary=None)
        tokens.parent_profile = {"user": ["DUMMY_PRIVATE", 0]}
        tokens.restricted_profile = {"type": 1, "shape": "same"}
        tokens.buffers = (d.w.H(401), d.w.H(402))
        tokens.close.return_value = True
        fixture = Mock(root=Path("C:/DUMMY PRIVATE/new-fixture"), ledger={})
        stack.enter_context(patch.object(d, "StartupPreflight", return_value=preflight))
        stack.enter_context(patch.object(d.w, "_api", return_value=api))
        stack.enter_context(patch.object(d.w, "_temporary_path", return_value=Path("C:/DUMMY PRIVATE")))
        disk = stack.enter_context(patch.object(d.shutil, "disk_usage", return_value=SimpleNamespace(free=d.DebugDriver.MIN_FREE_DISK)))
        stack.enter_context(patch.object(d, "DebugTokens", return_value=tokens))
        stack.enter_context(patch.object(d.w, "_Fixture", return_value=fixture))
        return d.DebugDriver(), api, kernel, preflight, tokens, fixture, disk

    def test_full_wiring_preflight_once_and_evidence_retention_without_acceptance(self):
        with ExitStack() as stack:
            driver, api, kernel, preflight, tokens, fixture, disk = self.driver(stack)
            result = driver.run()
            self.assertEqual(result["status"], "observed")
            self.assertEqual(result["teardown_status"], "pass")
            self.assertEqual(result["fixture_retention"], "unverified")
            self.assertIs(result.private_owner, driver)
            preflight.run.assert_called_once()
            fixture.create.assert_called_once()
            fixture.close.assert_called_once()
            tokens.close.assert_called_once()
            fixture.cleanup.assert_not_called()
            self.assertEqual(driver.request["version"], "b1.2")
            self.assertEqual(len(driver.request["source"]), 2)
            self.assertEqual(driver.launch.arguments[0], 402)
            self.assertFalse(result["native_accepted"])
            self.assertNotIn("DUMMY", json.dumps(result) + repr(driver))
            with self.assertRaises(d.TransportError):
                driver.run()

    def test_low_disk_and_preflight_failure_do_not_create_fixture(self):
        for phase in ("disk", "preflight"):
            with ExitStack() as stack, self.subTest(phase=phase):
                driver, api, kernel, preflight, tokens, fixture, disk = self.driver(stack)
                if phase == "disk":
                    disk.return_value.free = d.DebugDriver.MIN_FREE_DISK - 1
                else:
                    preflight.result["status"] = "failed"
                    preflight.primary = MemoryError()
                    preflight.resource_stop = True
                result = driver.run()
                self.assertEqual(result["status"], "failed")
                tokens.prepare.assert_not_called()
                fixture.create.assert_not_called()
                api.a.CreateProcessAsUserW.assert_not_called()
                if phase == "preflight":
                    disk.assert_not_called()
                    self.assertIs(driver.primary, preflight.primary)

    def test_unverified_breakpoint_stops_whole_driver_and_retains_raw_evidence(self):
        for fault in (None, "terminate", "continue"):
            with ExitStack() as stack, self.subTest(fault=fault):
                driver, api, kernel, preflight, tokens, fixture, disk = self.driver(stack)
                events = iter((3, 6, 1, 5))
                def deliver(pointer, timeout):
                    raw = pointer.contents
                    raw.kind, raw.pid, raw.tid = next(events), 17, 19
                    if raw.kind == 3:
                        raw.info.create_process.file = 101
                    elif raw.kind == 6:
                        raw.info.load_dll.file = 102
                    elif raw.kind == 1:
                        raw.info.exception.record.code = BREAKPOINT
                        raw.info.exception.record.address = 0x12345678
                        raw.info.exception.first_chance = 1
                    elif raw.kind == 5:
                        raw.info.exit_code = 1
                    return True
                kernel.WaitForDebugEventEx.side_effect = deliver
                kernel.WaitForSingleObject.side_effect = [258, 0]
                kernel.TerminateProcess.return_value = fault != "terminate"
                if fault == "continue":
                    kernel.ContinueDebugEvent.side_effect = [True, True, MemoryError()]
                result = driver.run()
                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["teardown_status"], "pass" if fault is None else "failed")
                self.assertEqual(driver.primary.reason, "bootstrap_unverified")
                self.assertIs(driver.primary, driver.observer.primary)
                self.assertEqual(driver.transport.count, 3)
                raw = result.private_owner.transport.buffers[2]
                self.assertEqual(raw.info.exception.record.address, 0x12345678)
                self.assertEqual(raw.info.exception.record.code, BREAKPOINT)
                self.assertEqual(driver.observer.events.confirmed, 2)
                self.assertIsNone(driver.observer.result["exit_code_observed"])
                kernel.ResumeThread.assert_called_once_with(502)
                kernel.TerminateProcess.assert_called_once_with(501, 1)
                methods = [call[0] for call in kernel.mock_calls]
                stop_index = methods.index("TerminateProcess")
                continues = [i for i, method in enumerate(methods) if method == "ContinueDebugEvent"]
                self.assertLess(continues[1], stop_index)
                self.assertEqual(len(continues), 4 if fault is None else 2 if fault == "terminate" else 3)
                if fault != "terminate":
                    self.assertGreater(continues[2], stop_index)
                    self.assertEqual(kernel.ContinueDebugEvent.call_args_list[2].args[2], DBG_NOT_HANDLED)
                self.assertEqual(driver.stop.handles, [None, None] if fault is None else [501, 502])
                if fault is None:
                    self.assertEqual(driver.stop.drain.buffers[0].info.exit_code, 1)
                    self.assertTrue(driver.stop.result["process_signaled"])
                self.assertEqual(result["resource_stop"], fault == "continue")
                self.assertEqual(driver.session.tokens, [None, None])
                closed = [call.args[0] for call in kernel.CloseHandle.call_args_list]
                self.assertEqual(closed, [101, 102, 502, 501, 702, 701] if fault is None
                                 else [101, 102, 702, 701])
                fixture.close.assert_called_once()
                tokens.close.assert_called_once()
                fixture.cleanup.assert_not_called()
                fixture.capture_cleanup.assert_not_called()
                self.assertFalse(result["native_accepted"])
                self.assertFalse(result["formal_permission"])

    def test_preparation_faults_close_only_existing_owners_without_cleanup(self):
        for phase in ("tokens", "create", "freeze", "request"):
            with ExitStack() as stack, self.subTest(phase=phase):
                driver, api, kernel, preflight, tokens, fixture, disk = self.driver(stack)
                original = MemoryError()
                function = {"tokens": tokens.prepare, "create": fixture.create,
                            "freeze": fixture.freeze, "request": fixture.file}[phase]
                function.side_effect = original
                result = driver.run()
                self.assertIs(driver.primary, original)
                self.assertTrue(result["resource_stop"])
                tokens.close.assert_called_once()
                fixture.cleanup.assert_not_called()
                api.a.CreateProcessAsUserW.assert_not_called()
                if phase != "tokens":
                    fixture.close.assert_called_once()

    def test_resource_failure_in_session_retains_fixture_and_skips_reads(self):
        with ExitStack() as stack:
            driver, api, kernel, preflight, tokens, fixture, disk = self.driver(stack)
            kernel.ResumeThread.side_effect = MemoryError()
            result = driver.run()
            self.assertTrue(result["resource_stop"])
            self.assertEqual(result["status"], "failed")
            fixture.cleanup.assert_not_called()
            fixture.capture_cleanup.assert_not_called()
            self.assertTrue(driver.stop.started)
            self.assertEqual(driver.session.tokens, [None, None])
            disk.assert_called_once()

    def test_secondary_release_and_report_faults_never_report_observed(self):
        for phase in ("fixture", "tokens", "report"):
            with ExitStack() as stack, self.subTest(phase=phase):
                driver, api, kernel, preflight, tokens, fixture, disk = self.driver(stack)
                if phase == "fixture":
                    fixture.close.side_effect = MemoryError()
                elif phase == "tokens":
                    tokens.close.return_value = False
                else:
                    stack.enter_context(patch.object(driver.result, "update", side_effect=MemoryError()))
                result = driver.run()
                self.assertNotEqual(result["status"], "observed")
                self.assertEqual(result["teardown_status"], "failed")
                self.assertIs(result.private_owner, driver)

    def test_outer_teardown_includes_uncertain_child_token_and_live_process(self):
        for phase in ("token", "continue", "create"):
            with ExitStack() as stack, self.subTest(phase=phase):
                driver, api, kernel, preflight, tokens, fixture, disk = self.driver(stack)
                if phase in ("token", "create"):
                    function = api.a.OpenProcessToken if phase == "token" else api.a.CreateProcessAsUserW
                    original = function.side_effect
                    def interrupted(*args):
                        original(*args)
                        raise MemoryError()
                    function.side_effect = interrupted
                else:
                    kernel.ContinueDebugEvent.return_value = False
                    kernel.WaitForSingleObject.return_value = 258
                result = driver.run()
                self.assertEqual(result["status"], "failed")
                self.assertEqual(result["teardown_status"], "failed")
                if phase == "token":
                    self.assertFalse(driver.session.tokens_resolved())
                    self.assertEqual(driver.session.token_buffers[0].value, 701)
                elif phase == "continue":
                    self.assertEqual(driver.stop.handles, [501, 502])
                    kernel.ContinueDebugEvent.assert_called_once()
                else:
                    self.assertEqual(driver.launch.creation_state, "uncertain")
                    kernel.TerminateProcess.assert_not_called()


if __name__ == "__main__":
    unittest.main()
