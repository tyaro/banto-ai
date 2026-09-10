"""Fake event handles and fixed output buffers, no real images or child."""

import ctypes as C
import json
import unittest
from unittest.mock import Mock, patch

from tests.fixtures.anomaly_v03_debug_transport import DebugEventTransport, TransportError
from tests.fixtures.anomaly_v03_debug_images import DebugImages
from tests.fixtures import anomaly_v03_debug_images as m


class DebugImagesTests(unittest.TestCase):
    def setup_images(self):
        kernel = Mock()
        kernel.GetCurrentThreadId.return_value = 7
        transport = DebugEventTransport(kernel=kernel, last_error=lambda: 0)
        transport.count, transport.pending, transport.state = 1, 0, "pending"
        transport.buffers[0].kind = 6
        transport.buffers[0].info.load_dll.file = 101
        def identity(handle, kind, pointer, size):
            pointer.contents.volume = 1
            pointer.contents.identifier[0] = 7
            return True
        def name(handle, buffer, size, flags):
            buffer.value = "\\Device\\HarddiskVolume1\\DUMMY_PRIVATE.dll"
            return len(buffer.value)
        kernel.GetFileInformationByHandleEx.side_effect = identity
        kernel.GetFinalPathNameByHandleW.side_effect = name
        return DebugImages(), transport, kernel, Mock()

    def test_queries_same_borrowed_handle_without_open_or_close(self):
        images, transport, kernel, budget = self.setup_images()
        images.capture(transport, budget)
        self.assertEqual(images.rows[0]["status"], "confirmed")
        self.assertEqual(images.rows[0]["event_slot"], 0)
        self.assertEqual(images.rows[0]["file_id"], "07" + "00" * 15)
        self.assertEqual(images.rows[0]["name"], "\\Device\\HarddiskVolume1\\DUMMY_PRIVATE.dll")
        self.assertEqual(kernel.GetFileInformationByHandleEx.call_count, 2)
        self.assertTrue(all(call.args[0] == 101 for call in kernel.GetFileInformationByHandleEx.call_args_list))
        self.assertEqual(budget.call_count, 4)
        kernel.CloseHandle.assert_not_called()
        kernel.CreateFileW.assert_not_called()
        self.assertNotIn("DUMMY", repr(images))
        with self.assertRaises(TransportError):
            images.capture(transport, budget)
        kernel.GetFinalPathNameByHandleW.assert_called_once()

    def test_missing_handle_is_explicit_without_queries(self):
        images, transport, kernel, budget = self.setup_images()
        transport.buffers[0].info.load_dll.file = None
        images.capture(transport, budget)
        self.assertEqual(images.rows[0]["status"], "no_file_handle")
        kernel.GetFileInformationByHandleEx.assert_not_called()
        budget.assert_not_called()

    def test_stopped_resource_and_closed_file_never_query(self):
        for fault in ("stopped", "resource", "closed", "capacity"):
            with self.subTest(fault=fault):
                images, transport, kernel, budget = self.setup_images()
                if fault == "stopped":
                    transport.state = "stopped"
                elif fault == "resource":
                    transport.resource_stop = True
                elif fault == "closed":
                    transport.file_closed[0] = True
                else:
                    images.count = images.LIMIT
                with self.assertRaises(TransportError):
                    images.capture(transport, budget)
                kernel.GetFileInformationByHandleEx.assert_not_called()

    def test_partial_failures_preserve_buffers_and_do_not_retry(self):
        for fault in ("identity", "name", "long_name", "changed", "json", "budget"):
            with self.subTest(fault=fault), patch.object(C, "get_last_error", return_value=8, create=True):
                images, transport, kernel, budget = self.setup_images()
                if fault == "identity":
                    kernel.GetFileInformationByHandleEx.side_effect = None
                    kernel.GetFileInformationByHandleEx.return_value = False
                elif fault == "name":
                    kernel.GetFinalPathNameByHandleW.side_effect = MemoryError()
                elif fault == "long_name":
                    kernel.GetFinalPathNameByHandleW.side_effect = None
                    kernel.GetFinalPathNameByHandleW.return_value = images.NAME_UNITS
                elif fault == "changed":
                    original = kernel.GetFileInformationByHandleEx.side_effect
                    def changed(*args):
                        original(*args)
                        args[2].contents.volume = kernel.GetFileInformationByHandleEx.call_count
                        return True
                    kernel.GetFileInformationByHandleEx.side_effect = changed
                elif fault == "json":
                    images.JSON_LIMIT = 1
                else:
                    budget.side_effect = [None, MemoryError()]
                with self.assertRaises((m.w._Failure, TransportError, MemoryError)):
                    images.capture(transport, budget)
                self.assertEqual(images.state, "stopped")
                self.assertEqual(images.count, 1)
                self.assertIsNotNone(images.rows[0])
                primary = images.primary
                before = len(kernel.mock_calls)
                with self.assertRaises(TransportError):
                    images.capture(transport, budget)
                self.assertEqual(len(kernel.mock_calls), before)
                self.assertIs(images.primary, primary)
                kernel.CloseHandle.assert_not_called()
                self.assertEqual(images.resource_stop, fault in ("identity", "name", "budget"))

    def test_total_metadata_envelope_and_future_partial_rows_fit_cap(self):
        images, transport, kernel, budget = self.setup_images()
        def name(handle, buffer, size, flags):
            buffer.value = "\\Device\\" + "\u3042" * 300
            return len(buffer.value)
        kernel.GetFinalPathNameByHandleW.side_effect = name
        stopped = False
        for index in range(images.LIMIT):
            transport.count, transport.pending = index + 1, index
            transport.buffers[index].kind = 6
            transport.buffers[index].info.load_dll.file = 101
            try:
                images.capture(transport, budget)
            except TransportError as error:
                self.assertEqual(error.reason, "images_metadata_capacity")
                stopped = True
            encoded = json.dumps({"state": images.state, "rows": images.rows},
                                 ensure_ascii=True, separators=(",", ":")).encode("ascii")
            self.assertLessEqual(len(encoded), images.JSON_LIMIT)
            if stopped:
                break
        self.assertTrue(stopped)
        self.assertEqual(images.rows[images.count - 1]["status"], "identity_recheck_uncertain")
