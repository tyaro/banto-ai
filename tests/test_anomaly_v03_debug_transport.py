"""Fake-kernel tests for a dormant native transport. No debug/child APIs run."""

import ctypes as C
import unittest
from unittest.mock import Mock, patch

from tests.fixtures import anomaly_v03_debug_transport as d


class DebugTransportTests(unittest.TestCase):
    def transport(self, kind=3):
        kernel = Mock()
        kernel.GetCurrentThreadId.return_value = 7
        kernel.CloseHandle.return_value = kernel.ContinueDebugEvent.return_value = True
        def deliver(pointer, timeout):
            raw = pointer.contents
            raw.kind, raw.pid, raw.tid = kind, 17, 19
            if kind == 3:
                raw.info.create_process.file = 101
                raw.info.create_process.process = 201
                raw.info.create_process.thread = 301
            elif kind == 6:
                raw.info.load_dll.file = 102
            return True
        kernel.WaitForDebugEventEx.side_effect = deliver
        transport = d.DebugEventTransport(kernel=kernel, last_error=lambda: 5)
        transport.bind(17)
        return transport, kernel

    def test_x64_abi_layout(self):
        self.assertEqual(C.sizeof(d.ExceptionRecord), 152)
        self.assertEqual(C.sizeof(d.ExceptionInfo), 160)
        self.assertEqual(C.sizeof(d.CreateProcessInfo), 72)
        self.assertEqual(C.sizeof(d.LoadDllInfo), 40)
        self.assertEqual(C.sizeof(d.DebugEvent), 176)
        self.assertEqual(d.DebugEvent.info.offset, 16)
        self.assertEqual(d.ExceptionRecord.information.offset, 32)

    def test_create_event_closes_only_image_file_and_continues_once(self):
        transport, kernel = self.transport()
        self.assertTrue(transport.wait())
        self.assertEqual(transport.event().kind, "create_process")
        with self.assertRaises(d.TransportError):
            transport.continue_event()
        kernel.ContinueDebugEvent.assert_not_called()
        transport.close_file(0)
        transport.continue_event()
        kernel.CloseHandle.assert_called_once_with(101)
        kernel.ContinueDebugEvent.assert_called_once_with(17, 19, d.DBG_CONTINUE)
        transport.close_retained_files()
        kernel.CloseHandle.assert_called_once()
        self.assertEqual(transport.state, "idle")

    def test_close_failure_retains_raw_handle_and_allows_one_teardown_retry(self):
        transport, kernel = self.transport(6)
        kernel.CloseHandle.side_effect = [False, True]
        transport.wait()
        with self.assertRaises(d.TransportError):
            transport.close_file(0)
        self.assertEqual(transport.buffers[0].info.load_dll.file, 102)
        self.assertFalse(transport.file_closed[0])
        with self.assertRaises(d.TransportError):
            transport.continue_event()
        transport.close_retained_files()
        self.assertTrue(transport.file_closed[0])
        self.assertEqual(kernel.CloseHandle.call_count, 2)
        self.assertEqual(transport.state, "stopped")
        kernel.ContinueDebugEvent.assert_not_called()

    def test_repeated_close_failure_is_bounded_and_retains_ownership(self):
        transport, kernel = self.transport(6)
        kernel.CloseHandle.return_value = False
        transport.wait()
        for _ in range(3):
            with self.assertRaises(d.TransportError):
                transport.close_retained_files()
        self.assertEqual(kernel.CloseHandle.call_count, 2)
        self.assertFalse(transport.file_closed[0])
        self.assertEqual(transport.buffers[0].info.load_dll.file, 102)

    def test_decoding_memory_failure_preserves_event_and_closes_file_without_continue(self):
        transport, kernel = self.transport(6)
        transport.wait()
        original = MemoryError("DUMMY_PRIVATE")
        with patch.object(d, "StartupEvent", side_effect=original), self.assertRaises(MemoryError) as caught:
            transport.event()
        self.assertIs(caught.exception, original)
        self.assertTrue(transport.resource_stop)
        self.assertEqual(transport.pending, 0)
        transport.close_retained_files()
        kernel.CloseHandle.assert_called_once_with(102)
        with self.assertRaises(d.TransportError):
            transport.continue_event()
        kernel.ContinueDebugEvent.assert_not_called()

    def test_continue_failure_is_never_retried_or_called_successful(self):
        for error in (False, MemoryError()):
            transport, kernel = self.transport()
            transport.wait()
            transport.close_file(0)
            if isinstance(error, BaseException):
                kernel.ContinueDebugEvent.side_effect = error
            else:
                kernel.ContinueDebugEvent.return_value = error
            with self.assertRaises((d.TransportError, MemoryError)):
                transport.continue_event()
            self.assertEqual(transport.state, "continue_uncertain")
            self.assertEqual(transport.pending, 0)
            with self.assertRaises(d.TransportError):
                transport.continue_event()
            kernel.ContinueDebugEvent.assert_called_once()

    def test_wait_timeout_vs_failure_and_boundaries(self):
        for code in (121, 5):
            transport, kernel = self.transport()
            kernel.WaitForDebugEventEx.side_effect = None
            kernel.WaitForDebugEventEx.return_value = False
            transport.last_error = lambda: code
            if code == 121:
                self.assertFalse(transport.wait())
                self.assertEqual(transport.state, "idle")
            else:
                with self.assertRaises(d.TransportError):
                    transport.wait()
                self.assertEqual(transport.state, "wait_failed")
            self.assertEqual(transport.count, 0)
        transport, kernel = self.transport()
        for value in (-1, 101, True):
            with self.assertRaises(d.TransportError):
                transport.wait(value)
        kernel.WaitForDebugEventEx.assert_not_called()

    def test_wait_allocation_failure_retains_buffer_without_claiming_delivery(self):
        transport, kernel = self.transport()
        def interrupted(pointer, timeout):
            pointer.contents.kind = 6
            pointer.contents.info.load_dll.file = 102
            raise MemoryError()
        kernel.WaitForDebugEventEx.side_effect = interrupted
        with self.assertRaises(MemoryError):
            transport.wait()
        self.assertEqual(transport.state, "wait_uncertain")
        self.assertEqual(transport.buffers[transport.pending].info.load_dll.file, 102)
        self.assertTrue(transport.resource_stop)
        # No success return from Wait: buffer provenance is uncertain. Preserve
        # it for the owner; do not blindly close or claim ownership resolved.
        self.assertEqual(transport.count, 0)
        with self.assertRaises(d.TransportError):
            transport.wait()

    def test_unknown_breakpoint_is_not_swallowed_and_other_exceptions_are_unhandled(self):
        for code in (d.BREAKPOINT, 0xC0000005):
            transport, kernel = self.transport(1)
            transport.wait()
            transport.buffers[0].info.exception.record.code = code
            transport.buffers[0].info.exception.first_chance = 1
            transport.close_file(0)
            if code == d.BREAKPOINT:
                with self.assertRaises(d.TransportError):
                    transport.continue_event()
                kernel.ContinueDebugEvent.assert_not_called()
            else:
                transport.continue_event()
                kernel.ContinueDebugEvent.assert_called_once_with(17, 19, d.DBG_NOT_HANDLED)

    def test_thread_identity_foreign_pid_unknown_kind_and_capacity_block_calls(self):
        transport, kernel = self.transport()
        kernel.GetCurrentThreadId.return_value = 8
        with self.assertRaises(d.TransportError):
            transport.wait()
        kernel.WaitForDebugEventEx.assert_not_called()
        for change in ("pid", "kind"):
            transport, kernel = self.transport()
            transport.wait()
            setattr(transport.buffers[0], change, 99)
            with self.assertRaises(d.TransportError):
                transport.event()
            self.assertEqual(transport.state, "stopped")
            kernel.ContinueDebugEvent.assert_not_called()
        transport, kernel = self.transport()
        transport.count = transport.LIMIT
        with self.assertRaises(d.TransportError):
            transport.wait()
        kernel.WaitForDebugEventEx.assert_not_called()

    def test_exit_continue_is_not_process_wait_and_prevents_more_events(self):
        transport, kernel = self.transport(5)
        transport.wait()
        transport.buffers[0].info.exit_code = 0xC0000142
        self.assertEqual(transport.event().code, 0xC0000142)
        transport.close_file(0)
        transport.continue_event()
        self.assertEqual(transport.state, "exit_continued")
        kernel.CloseHandle.assert_not_called()
        with self.assertRaises(d.TransportError):
            transport.wait()
