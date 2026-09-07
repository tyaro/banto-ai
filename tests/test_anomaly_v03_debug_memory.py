"""Memory adapter fault tests: no process creation or native query."""

import ctypes as C
import unittest
from unittest.mock import Mock

from tests import test_anomaly_v03_debug_stop as fixtures
from tests.fixtures.anomaly_v03_debug_memory import DebugMemory
from tests.fixtures.anomaly_v03_debug_transport import TransportError


class DebugMemoryTests(unittest.TestCase):
    def sampler(self, amounts=(100, 200)):
        stop, kernel = fixtures.DebugStopTests().controller()
        kernel.GetCurrentProcess.return_value = -1
        psapi = Mock()
        iterator = iter(amounts)
        def query(handle, pointer, size):
            pointer.contents.peak_pagefile = next(iterator)
            pointer.contents.peak_working = 50
            return True
        psapi.GetProcessMemoryInfo.side_effect = query
        return DebugMemory(stop, psapi), kernel, psapi

    def test_native_layout_and_reused_buffers_preserve_peak_metric(self):
        sampler, kernel, psapi = self.sampler((100, 200, 90, 180))
        identities = tuple(id(buffer) for buffer in sampler.buffers)
        self.assertEqual(C.sizeof(sampler.buffers[0]), 80)
        self.assertEqual(type(sampler.buffers[0]).peak_pagefile.offset, 64)
        self.assertEqual(type(sampler.buffers[0]).private.offset, 72)
        self.assertEqual(sampler(), 300)
        self.assertEqual(sampler(), 300)
        self.assertEqual(sampler.peak_working, 100)
        self.assertEqual(sampler.samples, 2)
        self.assertEqual(tuple(id(buffer) for buffer in sampler.buffers), identities)
        self.assertEqual([call.args[0] for call in psapi.GetProcessMemoryInfo.call_args_list], [-1, 501, -1, 501])
        kernel.CloseHandle.assert_not_called()

    def test_at_limit_stops_without_further_query_or_continue(self):
        for amounts, calls in (((DebugMemory.LIMIT,), 1), ((100, DebugMemory.LIMIT - 100), 2)):
            sampler, kernel, psapi = self.sampler(amounts)
            with self.assertRaises(TransportError):
                sampler()
            self.assertTrue(sampler.resource_stop)
            self.assertTrue(sampler.transport.resource_stop)
            self.assertEqual(sampler.state, "stopped")
            with self.assertRaises(TransportError):
                sampler()
            self.assertEqual(psapi.GetProcessMemoryInfo.call_count, calls)
            kernel.ContinueDebugEvent.assert_not_called()

    def test_partial_query_failure_retains_slots_and_latches_oom(self):
        for original in (MemoryError("DUMMY_PRIVATE"), KeyboardInterrupt(), False):
            sampler, kernel, psapi = self.sampler()
            def query(handle, pointer, size):
                pointer.contents.peak_pagefile = 777
                if handle == 501:
                    if isinstance(original, BaseException):
                        raise original
                    return False
                return True
            psapi.GetProcessMemoryInfo.side_effect = query
            with self.assertRaises((MemoryError, KeyboardInterrupt, TransportError)) as caught:
                sampler()
            self.assertIs(sampler.primary, caught.exception)
            self.assertEqual(sampler.buffers[1].peak_pagefile, 777)
            self.assertEqual(sampler.samples, 0)
            self.assertEqual(sampler.resource_stop, isinstance(original, MemoryError))
            with self.assertRaises(TransportError):
                sampler()
            self.assertEqual(psapi.GetProcessMemoryInfo.call_count, 2)
            self.assertEqual(sampler.transport.state, "stopped")

    def test_prior_child_peak_proves_limit_before_another_child_query(self):
        mib = 1024 * 1024
        sampler, kernel, psapi = self.sampler((100 * mib, 300 * mib, 212 * mib))
        self.assertEqual(sampler(), 400 * mib)
        with self.assertRaises(TransportError) as caught:
            sampler()
        self.assertEqual(caught.exception.reason, "memory_budget")
        self.assertEqual(sampler.peak_commit, DebugMemory.LIMIT)
        self.assertTrue(sampler.resource_stop)
        self.assertTrue(sampler.transport.resource_stop)
        self.assertEqual(sampler.samples, 1)
        self.assertEqual(psapi.GetProcessMemoryInfo.call_count, 3)
        self.assertEqual(sampler.process_commit_peaks, [212 * mib, 300 * mib])

    def test_stop_resource_identity_and_thread_checks_block_queries(self):
        for fault in ("stopped", "resource", "identity", "thread"):
            sampler, kernel, psapi = self.sampler()
            if fault == "stopped":
                sampler.stop.started = True
            elif fault == "resource":
                sampler.transport.resource_stop = True
            elif fault == "identity":
                kernel.GetProcessId.return_value = 99
            else:
                kernel.GetCurrentThreadId.side_effect = MemoryError()
            with self.assertRaises((TransportError, MemoryError)):
                sampler()
            psapi.GetProcessMemoryInfo.assert_not_called()
            self.assertEqual(sampler.transport.state, "stopped")
            if fault in ("resource", "thread"):
                self.assertTrue(sampler.resource_stop)

    def test_bad_counter_size_fails_closed(self):
        sampler, kernel, psapi = self.sampler()
        def query(handle, pointer, size):
            pointer.contents.cb = 0
            return True
        psapi.GetProcessMemoryInfo.side_effect = query
        with self.assertRaises(TransportError):
            sampler()
        psapi.GetProcessMemoryInfo.assert_called_once()


if __name__ == "__main__":
    unittest.main()
