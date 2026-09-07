"""Owned-stop/drain controller tested without any native process or debug API."""

import json
import unittest
from unittest.mock import Mock, patch

from tests.fixtures.anomaly_v03_debug_stop import OwnedDebugStop
from tests.fixtures.anomaly_v03_debug_transport import DebugEventTransport, TransportError


class DebugStopTests(unittest.TestCase):
    def controller(self, events=(5,)):
        kernel = Mock()
        kernel.GetCurrentThreadId.return_value = 7
        kernel.GetProcessId.return_value = 17
        kernel.TerminateProcess.return_value = kernel.CloseHandle.return_value = True
        kernel.ContinueDebugEvent.return_value = True
        kernel.WaitForSingleObject.side_effect = [258, 0]
        iterator = iter(events)
        def wait(pointer, timeout):
            try:
                kind = next(iterator)
            except StopIteration:
                return False
            raw = pointer.contents
            raw.kind, raw.pid, raw.tid = kind, 17, 19
            if kind == 6:
                raw.info.load_dll.file = 102
            if kind == 5:
                raw.info.exit_code = 1
            return True
        kernel.WaitForDebugEventEx.side_effect = wait
        transport = DebugEventTransport(kernel=kernel, last_error=lambda: 121)
        stop = OwnedDebugStop(transport, clock=lambda: 0)
        transport.bind(17)
        stop.adopt(501, 502)
        return stop, kernel

    def test_terminate_drain_signal_and_only_owned_handles_close(self):
        stop, kernel = self.controller((6, 5))
        result = stop.run()
        self.assertEqual(result["status"], "stopped")
        self.assertEqual(result["teardown_status"], "pass")
        self.assertTrue(result["process_signaled"])
        self.assertTrue(result["exit_continued"])
        kernel.TerminateProcess.assert_called_once_with(501, 1)
        self.assertEqual([call.args[0] for call in kernel.CloseHandle.call_args_list], [102, 502, 501])
        self.assertEqual(stop.handles, [None, None])
        self.assertIs(result.private_owner, stop)
        self.assertFalse(result["native_accepted"])
        with self.assertRaises(TransportError):
            stop.transport.wait()

    def test_existing_pending_event_is_released_after_termination_not_before(self):
        stop, kernel = self.controller((6, 5))
        stop.transport.wait()
        result = stop.run()
        self.assertTrue(result["process_signaled"])
        methods = [call[0] for call in kernel.mock_calls]
        self.assertLess(methods.index("TerminateProcess"), methods.index("ContinueDebugEvent"))

    def test_uncertain_continue_is_never_retried_even_after_stop_erases_state(self):
        stop, kernel = self.controller((6,))
        stop.transport.wait()
        stop.transport.close_file(0)
        kernel.ContinueDebugEvent.return_value = False
        with self.assertRaises(TransportError):
            stop.transport.continue_event()
        stop.transport.stop()
        result = stop.run()
        self.assertEqual(result["status"], "unconfirmed")
        kernel.ContinueDebugEvent.assert_called_once()
        self.assertEqual(stop.handles, [501, 502])
        self.assertTrue(stop.transport.continue_inflight)

    def test_timeout_is_bounded_and_never_means_process_gone(self):
        stop, kernel = self.controller(())
        result = stop.run()
        self.assertEqual(result["status"], "unconfirmed")
        self.assertEqual(result["drain_waits"], 32)
        self.assertEqual(kernel.WaitForDebugEventEx.call_count, 32)
        self.assertEqual(stop.handles, [501, 502])
        kernel.CloseHandle.assert_not_called()

    def test_exit_continue_without_signal_keeps_launch_handles(self):
        stop, kernel = self.controller()
        kernel.WaitForSingleObject.side_effect = [258, 258]
        result = stop.run()
        self.assertTrue(result["exit_continued"])
        self.assertFalse(result["process_signaled"])
        self.assertEqual(result["status"], "unconfirmed")
        kernel.CloseHandle.assert_not_called()

    def test_resource_primary_and_close_secondary_are_preserved_without_reads(self):
        stop, kernel = self.controller((6, 5))
        primary = MemoryError("DUMMY_PRIVATE_PRIMARY")
        kernel.CloseHandle.side_effect = [False, True, True, True]
        result = stop.run(primary)
        self.assertIs(stop.primary, primary)
        self.assertTrue(result["resource_stop"])
        self.assertTrue(result["process_signaled"])
        self.assertEqual(result["teardown_status"], "failed")
        self.assertNotIn("DUMMY", json.dumps(result) + repr(stop))
        kernel.ReadProcessMemory.assert_not_called()

    def test_launch_close_interruption_is_uncertain_and_does_not_block_other_handle(self):
        stop, kernel = self.controller()
        kernel.CloseHandle.side_effect = [KeyboardInterrupt(), True]
        result = stop.run()
        self.assertEqual(result["teardown_status"], "failed")
        self.assertEqual(stop.close_state, ["closed", "uncertain"])
        self.assertEqual(stop.handles, [None, 502])
        with self.assertRaises(TransportError):
            stop.run()
        self.assertEqual(kernel.CloseHandle.call_count, 2)

    def test_foreign_event_or_wrong_process_cannot_be_continued_or_terminated(self):
        stop, kernel = self.controller()
        kernel.GetProcessId.return_value = 99
        result = stop.run()
        self.assertEqual(result["status"], "unconfirmed")
        kernel.TerminateProcess.assert_not_called()
        kernel.ContinueDebugEvent.assert_not_called()
        stop, kernel = self.controller((6,))
        stop.transport.wait()
        stop.transport.buffers[0].pid = 99
        result = stop.run()
        self.assertEqual(result["status"], "unconfirmed")
        kernel.ContinueDebugEvent.assert_not_called()

    def test_signaled_process_is_not_terminated_again(self):
        stop, kernel = self.controller()
        kernel.WaitForSingleObject.side_effect = [0]
        result = stop.run()
        self.assertTrue(result["process_signaled"])
        kernel.TerminateProcess.assert_not_called()
        kernel.WaitForDebugEventEx.assert_not_called()

    def test_signaled_process_does_not_resolve_uncertain_wait_or_continue(self):
        for phase in ("wait", "continue"):
            stop, kernel = self.controller((6,))
            if phase == "wait":
                def interrupted(pointer, timeout):
                    pointer.contents.kind = 6
                    pointer.contents.info.load_dll.file = 102
                    raise MemoryError()
                kernel.WaitForDebugEventEx.side_effect = interrupted
                with self.assertRaises(MemoryError):
                    stop.transport.wait()
            else:
                stop.transport.wait()
                stop.transport.close_file(0)
                kernel.ContinueDebugEvent.return_value = False
                with self.assertRaises(TransportError):
                    stop.transport.continue_event()
            kernel.WaitForSingleObject.side_effect = [0]
            previous_continues = kernel.ContinueDebugEvent.call_count
            result = stop.run()
            self.assertTrue(result["process_signaled"])
            self.assertFalse(result["debug_ownership_resolved"])
            self.assertEqual(result["teardown_status"], "failed")
            self.assertGreater(result["failure_count"], 0)
            self.assertIs(result.private_owner.transport, stop.transport)
            self.assertEqual(kernel.ContinueDebugEvent.call_count, previous_continues)
            kernel.TerminateProcess.assert_not_called()
            if phase == "wait":
                self.assertEqual(stop.transport.buffers[stop.transport.pending].info.load_dll.file, 102)
                self.assertNotIn(102, [call.args[0] for call in kernel.CloseHandle.call_args_list])

    def test_existing_transport_resource_latch_survives_successful_stop_without_primary(self):
        stop, kernel = self.controller((6, 5))
        stop.transport.wait()
        with patch("tests.fixtures.anomaly_v03_debug_transport.StartupEvent", side_effect=MemoryError()), \
             self.assertRaises(MemoryError):
            stop.transport.event()
        result = stop.run()
        self.assertTrue(result["process_signaled"])
        self.assertTrue(result["debug_ownership_resolved"])
        self.assertTrue(result["resource_stop"])
        self.assertTrue(stop.resource_stop)
        self.assertTrue(stop.transport.resource_stop)
        self.assertTrue(stop.drain.resource_stop)

    def test_result_render_failure_keeps_private_owner_and_primary(self):
        stop, kernel = self.controller()
        primary = ValueError("DUMMY_PRIVATE")
        with patch.object(stop.result, "update", side_effect=MemoryError()):
            result = stop.run(primary)
        self.assertIs(result.private_owner, stop)
        self.assertIs(stop.primary, primary)
        self.assertEqual(result["status"], "report_failed")
        self.assertTrue(stop.resource_stop)
