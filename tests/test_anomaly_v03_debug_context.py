"""Fake-only context/memory reads; no child, native query or remote memory."""

import ctypes as C
import json
import struct
import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock

from tests.fixtures.anomaly_v03_debug_context import DebugContext
from tests.fixtures.anomaly_v03_debug_transport import DebugEventTransport, TransportError
from banto_ai import _anomaly_v03_windows as w


class DebugContextTests(unittest.TestCase):
    def fixture(self):
        k = Mock()
        k.GetCurrentThreadId.return_value = 7
        k.GetProcessId.return_value = k.GetProcessIdOfThread.return_value = 17
        k.GetThreadId.return_value = 19
        t = DebugEventTransport(kernel=k, last_error=lambda: 8)
        stop = NS(transport=t, started=False, resource_stop=False,
                  drain=NS(resource_stop=False), handles=[101, 102])
        launch = NS(stop=stop, started=False, creation_state="not_started", transferred=False,
                    process=NS(process=101, thread=102, pid=17, tid=19))
        owner = DebugContext()
        owner.bind(stop, launch)
        launch.started, launch.creation_state, launch.transferred = True, "created", True
        t.bind(17)
        t.count, t.pending, t.state = 1, 0, "pending"
        t.buffers[0].kind, t.buffers[0].pid, t.buffers[0].tid = 7, 17, 19
        def context(handle, pointer):
            self.assertEqual(handle, 102)
            self.assertEqual(pointer.value % 16, 0)
            self.assertEqual(struct.unpack_from("<I", owner.context, 48)[0], 0x100003)
            struct.pack_into("<Q", owner.context, 152, 0x10000)
            struct.pack_into("<Q", owner.context, 248, 0x20000)
            return True
        def read(handle, remote, local, size, length):
            self.assertEqual((handle, remote.value, size), (101, 0x10000, 2048))
            C.memmove(local, b"X" * size, size)
            length.contents.value = size
            return True
        k.GetThreadContext.side_effect = context
        k.ReadProcessMemory.side_effect = read
        return owner, k, stop, launch, Mock()

    def test_aligned_borrowed_once_and_bounded_payload(self):
        owner, k, stop, launch, budget = self.fixture()
        owner.capture(budget)
        self.assertEqual(owner.state, "completed")
        self.assertEqual(owner.row["status"], "confirmed")
        self.assertEqual(len(owner.row["context_hex"]), 1232 * 2)
        self.assertEqual(len(owner.row["stack_hex"]), 2048 * 2)
        self.assertLess(len(json.dumps({"state": owner.state, "row": owner.row})), 8 * 1024)
        before = len(k.mock_calls)
        owner.capture(budget)
        self.assertEqual(len(k.mock_calls), before)
        k.GetThreadContext.assert_called_once()
        k.ReadProcessMemory.assert_called_once()
        for name in ("OpenProcess", "OpenThread", "CloseHandle", "SuspendThread", "ResumeThread",
                     "SetThreadContext", "WriteProcessMemory"):
            getattr(k, name).assert_not_called()

    def test_other_thread_consumes_selection_without_query(self):
        owner, k, stop, launch, budget = self.fixture()
        stop.transport.buffers[0].tid = 99
        owner.capture(budget)
        self.assertEqual(owner.row["status"], "not_initial_thread")
        stop.transport.buffers[0].tid = 19
        owner.capture(budget)
        k.GetThreadContext.assert_not_called()
        budget.assert_not_called()

    def test_non_unload_is_not_selected(self):
        for kind in (1, 3, 5, 6, 8, 9):
            owner, k, stop, launch, budget = self.fixture()
            stop.transport.buffers[0].kind = kind
            owner.capture(budget)
            self.assertEqual(owner.row["status"], "not_observed")
            k.GetThreadContext.assert_not_called()

    def test_invalid_ownership_and_pending_stop_before_query(self):
        for fault in ("inflight", "stopped", "handle", "pid", "resource", "thread_identity"):
            with self.subTest(fault=fault):
                owner, k, stop, launch, budget = self.fixture()
                if fault == "inflight": stop.transport.continue_inflight = True
                elif fault == "stopped": stop.started = True
                elif fault == "handle": stop.handles[1] = 333
                elif fault == "pid": stop.transport.buffers[0].pid = 123
                elif fault == "resource": stop.resource_stop = True
                else: k.GetThreadId.return_value = 20
                with self.assertRaises(TransportError): owner.capture(budget)
                k.GetThreadContext.assert_not_called()

    def test_false_short_and_interrupted_reads_preserve_primary_without_retry(self):
        for fault in ("identity_zero", "context_false", "read_false", "short", "oversize", "oom"):
            with self.subTest(fault=fault):
                owner, k, stop, launch, budget = self.fixture()
                if fault == "identity_zero": k.GetThreadId.return_value = 0
                elif fault == "context_false":
                    k.GetThreadContext.side_effect = None
                    k.GetThreadContext.return_value = False
                elif fault == "oom": k.ReadProcessMemory.side_effect = MemoryError()
                else:
                    def read(*args):
                        args[-1].contents.value = 2049 if fault == "oversize" else 1
                        return fault != "read_false"
                    k.ReadProcessMemory.side_effect = read
                with self.assertRaises((w._Failure, TransportError, MemoryError)): owner.capture(budget)
                primary, before = owner.primary, len(k.mock_calls)
                with self.assertRaises(TransportError): owner.capture(budget)
                self.assertIs(owner.primary, primary)
                self.assertEqual(len(k.mock_calls), before)
                self.assertNotIn("stack_hex", owner.row)
                self.assertEqual(owner.resource_stop, fault in ("identity_zero", "context_false", "read_false", "oom"))

    def test_invalid_context_blocks_stack_read(self):
        for offset, value in ((48, 0), (152, 0), (152, 2**64 - 1), (248, 0)):
            owner, k, stop, launch, budget = self.fixture()
            original = k.GetThreadContext.side_effect
            def context(*args):
                original(*args)
                struct.pack_into("<I" if offset == 48 else "<Q", owner.context, offset, value)
                return True
            k.GetThreadContext.side_effect = context
            with self.assertRaises(TransportError): owner.capture(budget)
            k.ReadProcessMemory.assert_not_called()

    def test_budget_failure_and_event_change_after_context_prevent_read(self):
        for fault in ("budget", "event"):
            owner, k, stop, launch, budget = self.fixture()
            original = k.GetThreadContext.side_effect
            def context(*args):
                original(*args)
                if fault == "budget": budget.side_effect = MemoryError()
                else: stop.transport.continue_inflight = True
                return True
            k.GetThreadContext.side_effect = context
            with self.assertRaises((MemoryError, TransportError)): owner.capture(budget)
            k.ReadProcessMemory.assert_not_called()
            self.assertEqual(owner.row["context_state"], "query_confirmed")
