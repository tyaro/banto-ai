"""Observer integration and fault tests; fake kernel only, no native calls."""

import json
import unittest
from unittest.mock import Mock, patch

from tests.fixtures.anomaly_v03_debug_observer import DebugObserver
from tests.fixtures.anomaly_v03_debug_stop import OwnedDebugStop
from tests.fixtures.anomaly_v03_debug_memory import DebugMemory
from tests.fixtures.anomaly_v03_debug_transport import (
    DebugEventTransport, TransportError, BREAKPOINT, DBG_NOT_HANDLED,
)


class DebugObserverTests(unittest.TestCase):
    def observer(self, events=(3, 6, 5), *, code=0, clock=lambda: 0, memory=lambda: 0, deferred=False):
        kernel = Mock()
        kernel.GetCurrentThreadId.return_value = 7
        kernel.GetProcessId.return_value = 17
        kernel.CloseHandle.return_value = kernel.ContinueDebugEvent.return_value = True
        kernel.TerminateProcess.return_value = True
        kernel.WaitForSingleObject.return_value = 0
        sequence = iter(events)
        def deliver(pointer, timeout):
            kind = next(sequence, None)
            if kind is None:
                return False
            raw = pointer.contents
            raw.kind, raw.pid, raw.tid = kind, 17, 19
            if kind == 3:
                raw.info.create_process.file = 101
            elif kind == 6:
                raw.info.load_dll.file = 102
            elif kind == 1:
                raw.info.exception.record.code = code
                raw.info.exception.first_chance = 1
            elif kind == 5:
                raw.info.exit_code = code
            return True
        kernel.WaitForDebugEventEx.side_effect = deliver
        transport = DebugEventTransport(kernel=kernel, last_error=lambda: 121)
        stop = OwnedDebugStop(transport, clock=lambda: 0)
        if deferred:
            observer = DebugObserver(stop, sample_memory=memory, clock=clock)
        transport.bind(17)
        stop.adopt(501, 502)
        return observer if deferred else DebugObserver(stop, sample_memory=memory, clock=clock), kernel

    def test_observer_and_recorder_are_preallocated_before_pid_is_known(self):
        observer, kernel = self.observer(deferred=True)
        self.assertIsNone(observer.events.pid)
        slots, result = observer.events.slots, observer.result
        with patch("tests.fixtures.anomaly_v03_debug_observer.StartupEvents", side_effect=MemoryError()):
            returned = observer.run()
        self.assertIs(returned, result)
        self.assertIs(observer.events.slots, slots)
        self.assertEqual(observer.events.pid, 17)
        self.assertEqual(returned["status"], "observed")

    def test_exact_memory_limit_stops_before_wait(self):
        observer, kernel = self.observer(memory=lambda: DebugObserver.MEMORY_LIMIT)
        result = observer.run()
        self.assertTrue(result["resource_stop"])
        kernel.WaitForDebugEventEx.assert_not_called()

    def test_memory_adapter_integrates_with_deferred_recorder_and_owned_stop(self):
        for amount in (100, DebugMemory.LIMIT // 2):
            observer, kernel = self.observer(deferred=True)
            kernel.GetCurrentProcess.return_value = -1
            psapi = Mock()
            def query(handle, pointer, size):
                pointer.contents.peak_pagefile = amount
                return True
            psapi.GetProcessMemoryInfo.side_effect = query
            observer.sample_memory = DebugMemory(observer.stop, psapi)
            result = observer.run()
            self.assertEqual(result["status"], "observed" if amount == 100 else "failed")
            self.assertEqual(result["resource_stop"], amount != 100)
            if amount != 100:
                kernel.WaitForDebugEventEx.assert_not_called()
                self.assertEqual(psapi.GetProcessMemoryInfo.call_count, 2)

    def test_observed_exit_is_never_native_acceptance_or_cause_attribution(self):
        observer, kernel = self.observer(code=0xC0000142)
        result = observer.run()
        self.assertEqual(result["status"], "observed")
        self.assertEqual(result["exit_code_observed"], 0xC0000142)
        self.assertEqual(result["continued_events"], 3)
        self.assertEqual(observer.events.status, "completed")
        self.assertFalse(result["native_accepted"])
        self.assertFalse(result["formal_permission"])
        self.assertIs(result.private_owner, observer)
        self.assertEqual([call.args[0] for call in kernel.CloseHandle.call_args_list], [101, 102, 502, 501])
        kernel.TerminateProcess.assert_not_called()
        self.assertNotIn("faulting_module", result)

    def test_unknown_bootstrap_goes_to_owned_stop_before_exception_continuation(self):
        observer, kernel = self.observer((3, 1, 5), code=BREAKPOINT)
        kernel.WaitForSingleObject.side_effect = [258, 0]
        result = observer.run()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(observer.primary.reason, "bootstrap_unverified")
        self.assertEqual(observer.events.confirmed, 1)
        methods = [call[0] for call in kernel.mock_calls]
        termination = methods.index("TerminateProcess")
        continues = [i for i, method in enumerate(methods) if method == "ContinueDebugEvent"]
        self.assertLess(continues[0], termination)
        self.assertGreater(continues[1], termination)
        self.assertEqual(kernel.ContinueDebugEvent.call_args_list[1].args[2], DBG_NOT_HANDLED)

    def test_wait_timeouts_are_bounded_even_with_frozen_clock(self):
        observer, kernel = self.observer(())
        result = observer.run()
        self.assertEqual(observer.waits, 300)
        self.assertEqual(kernel.WaitForDebugEventEx.call_count, 300)
        self.assertEqual(observer.primary.reason, "observation_wait_limit")
        self.assertEqual(result["status"], "failed")

    def test_deadline_after_delivery_preserves_buffer_without_normal_continue(self):
        clock = Mock(side_effect=[0, 0, 0, 0, 30])
        observer, kernel = self.observer(clock=clock)
        result = observer.run()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(observer.primary.reason, "observation_deadline")
        self.assertEqual(observer.transport.count, 1)
        self.assertEqual(observer.transport.pending, 0)
        kernel.ContinueDebugEvent.assert_not_called()

    def test_memory_stop_and_bad_samples_prevent_wait_and_keep_primary_private(self):
        for sample in (DebugObserver.MEMORY_LIMIT + 1, -1, True, None):
            observer, kernel = self.observer(memory=lambda: sample)
            result = observer.run()
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["resource_stop"], sample == DebugObserver.MEMORY_LIMIT + 1)
            kernel.WaitForDebugEventEx.assert_not_called()
        original = MemoryError("DUMMY_PRIVATE")
        observer, kernel = self.observer(memory=Mock(side_effect=original))
        result = observer.run()
        self.assertIs(observer.primary, original)
        self.assertIs(observer.stop.primary, original)
        self.assertTrue(result["resource_stop"])
        self.assertNotIn("DUMMY", json.dumps(result) + repr(observer))

    def test_memory_exhaustion_after_delivery_allows_only_stop_and_close(self):
        observer, kernel = self.observer(memory=Mock(side_effect=[0, 0, MemoryError()]))
        kernel.WaitForSingleObject.side_effect = [258, 0]
        result = observer.run()
        self.assertTrue(result["resource_stop"])
        self.assertEqual(observer.events.count, 0)
        methods = [call[0] for call in kernel.mock_calls]
        self.assertLess(methods.index("TerminateProcess"), methods.index("ContinueDebugEvent"))
        self.assertEqual(observer.sample_memory.call_count, 3)

    def test_child_resource_exit_is_recorded_but_not_normal_completion(self):
        observer, kernel = self.observer((3, 5), code=80)
        result = observer.run()
        self.assertEqual(result["exit_code_observed"], 80)
        self.assertTrue(result["resource_stop"])
        self.assertEqual(result["continued_events"], 1)
        self.assertEqual(observer.primary.reason, "child_resource_stop")

    def test_uncertain_continue_is_not_retried_by_integration(self):
        observer, kernel = self.observer()
        kernel.ContinueDebugEvent.return_value = False
        kernel.WaitForSingleObject.return_value = 258
        result = observer.run()
        kernel.ContinueDebugEvent.assert_called_once()
        self.assertEqual(result["teardown_status"], "failed")
        self.assertEqual(observer.stop.handles, [501, 502])
        self.assertTrue(observer.transport.continue_inflight)

    def test_exit_without_process_signal_and_teardown_close_failure_are_failed(self):
        observer, kernel = self.observer()
        kernel.WaitForSingleObject.side_effect = [258, 0]
        result = observer.run()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(observer.events.status, "stopped")
        observer, kernel = self.observer((3, 5))
        kernel.CloseHandle.side_effect = [True, False, True]
        result = observer.run()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["teardown_status"], "failed")
        self.assertEqual(observer.stop.handles, [None, 502])

    def test_decode_recorder_and_reporting_faults_retain_owners(self):
        for phase in ("decode", "receive", "continued", "report", "stop"):
            observer, kernel = self.observer()
            owner, attribute = {"decode": (observer.transport, "event"),
                                "receive": (observer.events, "receive"),
                                "continued": (observer.events, "continued"),
                                "report": (observer.result, "update"),
                                "stop": (observer.stop, "run")}[phase]
            original = MemoryError("DUMMY_PRIVATE")
            with self.subTest(phase=phase), patch.object(owner, attribute, side_effect=original):
                result = observer.run()
            self.assertTrue(result["resource_stop"])
            self.assertIs(result.private_owner.stop, observer.stop)
            self.assertIn(original, (observer.primary, observer.secondary))
            self.assertNotEqual(result["status"], "observed")
            self.assertNotIn("DUMMY", json.dumps(result))

    def test_wrong_order_and_capacity_failure_retain_delivered_events(self):
        for events in ((6,), (3, 3), (3,) + (6,) * 256):
            observer, kernel = self.observer(events)
            result = observer.run()
            self.assertEqual(result["status"], "failed")
            self.assertLessEqual(observer.transport.count, 256)
            self.assertLessEqual(observer.events.count, 256)

    def test_expired_sampler_and_existing_resource_stop_do_not_start_wait(self):
        observer, kernel = self.observer(clock=Mock(side_effect=[0, 30]))
        observer.run()
        self.assertEqual(observer.primary.reason, "observation_deadline")
        kernel.WaitForDebugEventEx.assert_not_called()
        memory = Mock(return_value=0)
        observer, kernel = self.observer(memory=memory)
        observer.transport.resource_stop = True
        result = observer.run()
        self.assertTrue(result["resource_stop"])
        memory.assert_not_called()
        kernel.WaitForDebugEventEx.assert_not_called()

    def test_interrupt_after_recorder_completion_preserves_primary_and_returns_result(self):
        observer, kernel = self.observer()
        original = KeyboardInterrupt("DUMMY_PRIVATE")
        complete = observer.events.process_signaled
        def interrupted():
            complete()
            raise original
        with patch.object(observer.events, "process_signaled", side_effect=interrupted):
            result = observer.run()
        self.assertEqual(result["status"], "failed")
        self.assertIs(observer.primary, original)
        self.assertIs(observer.stop.primary, original)
        self.assertIsNotNone(observer.secondary)
        self.assertIs(result.private_owner, observer)
        self.assertEqual(observer.transport.state, "stopped")

    def test_stop_entry_interruption_cannot_reopen_normal_continue(self):
        observer, kernel = self.observer()
        primary = ValueError("DUMMY_PRIVATE_PRIMARY")
        secondary = KeyboardInterrupt("DUMMY_PRIVATE_SECONDARY")
        with patch.object(observer.events, "receive", side_effect=primary), \
             patch.object(observer.stop, "run", side_effect=secondary):
            result = observer.run()
        self.assertEqual(result["status"], "failed")
        self.assertIs(observer.primary, primary)
        self.assertIs(observer.secondary, secondary)
        self.assertEqual(observer.transport.pending, 0)
        self.assertEqual(observer.stop.handles, [501, 502])
        observer.transport.close_file(0)
        with self.assertRaises(TransportError):
            observer.transport.continue_event()
        kernel.ContinueDebugEvent.assert_not_called()


if __name__ == "__main__":
    unittest.main()
