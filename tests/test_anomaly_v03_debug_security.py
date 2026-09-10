"""Fixed local buffers and fake security APIs only."""

import ctypes as C
import json
import struct
import unittest
from unittest.mock import Mock, patch

from tests.fixtures import anomaly_v03_debug_security as s
from tests.fixtures.anomaly_v03_debug_transport import TransportError


def acl(ace=b"", count=0):
    return struct.pack("<BBHHH", 2, 0, 8 + len(ace), count, 0) + ace


class DebugSecurityTests(unittest.TestCase):
    def collector(self, *, token_acl=acl(), descriptor=None):
        api = Mock()
        collector = s.DebugSecurity()
        collector.bind(api)
        def token(handle, kind, pointer, capacity, length):
            self.assertEqual(kind, 6)
            raw = (0 if token_acl is None else pointer.value + 8).to_bytes(8, "little")
            raw += token_acl or b""
            C.memmove(pointer, raw, len(raw))
            length.contents.value = len(raw)
            return True
        def kernel(handle, info, pointer, capacity, length):
            self.assertEqual(info, 0x17)
            raw = descriptor if descriptor is not None else struct.pack("<BBHIIII", 1, 0, 0x8004, 0, 0, 0, 20) + acl()
            C.memmove(pointer, raw, len(raw))
            length.contents.value = len(raw)
            return True
        api.a.GetTokenInformation.side_effect = token
        api.a.GetKernelObjectSecurity.side_effect = kernel
        return collector, api, Mock()

    def test_null_empty_present_and_opaque_acl_are_distinct(self):
        sid = b"\x01\x01" + bytes(5) + b"\x05" + (18).to_bytes(4, "little")
        allow = struct.pack("<BBHI", 0, 0, 8 + len(sid), 0x1fffff) + sid
        for raw, expected, opaque in ((None, "null", 0), (acl(), "empty", 0),
                                      (acl(allow, 1), "present", 0), (acl(b"\x42\x00\x04\x00", 1), "present", 1)):
            with self.subTest(expected=expected, opaque=opaque):
                collector, api, budget = self.collector(token_acl=raw)
                collector.capture(0, 101, budget)
                row = collector.rows[0]
                self.assertEqual(row["acl"]["state"], expected)
                self.assertEqual(row["acl"].get("opaque_ace_count", 0), opaque)
                self.assertEqual(row["acl_hex"], (raw or b"").hex())
                self.assertEqual(row["status"], "confirmed")
                api.a.GetTokenInformation.assert_called_once()
                api.k.CloseHandle.assert_not_called()

    def test_absolute_pointer_outside_owned_return_buffer_is_never_followed(self):
        for offset in (-4, 0, 4, 9, 1024, 2**32):
            with self.subTest(offset=offset):
                collector, api, budget = self.collector()
                def invalid(handle, kind, pointer, capacity, length):
                    C.memmove(pointer, (pointer.value + offset).to_bytes(8, "little"), 8)
                    length.contents.value = 16
                    return True
                api.a.GetTokenInformation.side_effect = invalid
                with self.assertRaises(TransportError):
                    collector.capture(0, 101, budget)
                self.assertEqual(collector.rows[0]["status"], "query_confirmed")

    def test_self_relative_sd_distinguishes_absent_null_empty(self):
        for control, offset, data, expected in ((0x8000, 0, b"", "absent"),
                                               (0x8004, 0, b"", "null"),
                                               (0x8004, 20, acl(), "empty")):
            raw = struct.pack("<BBHIIII", 1, 0, control, 0, 0, 0, offset) + data
            collector, api, budget = self.collector(descriptor=raw)
            collector.capture(3, 501, budget)
            self.assertEqual(collector.rows[3]["descriptor"]["dacl"]["state"], expected)
            self.assertEqual(collector.rows[3]["descriptor_hex"], raw.hex())

    def test_acl_and_sd_bounds_reject_truncation_and_bad_counts(self):
        invalid = (acl()[:-1], struct.pack("<BBHHH", 2, 0, 8, 1, 0),
                   acl(b"\x00\x00\xff\x00", 1), acl(b"\x00\x00\x04\x00", 1))
        for raw in invalid:
            collector, api, budget = self.collector(token_acl=raw)
            with self.assertRaises(TransportError):
                collector.capture(0, 101, budget)
        for raw in (bytes(19), struct.pack("<BBHIIII", 1, 0, 4, 0, 0, 0, 0),
                    struct.pack("<BBHIIII", 1, 0, 0x8004, 0, 0, 0, 1024)):
            collector, api, budget = self.collector(descriptor=raw)
            with self.assertRaises(TransportError):
                collector.capture(3, 501, budget)

    def test_api_size_and_memory_failures_stop_without_retry(self):
        for phase in ("false", "oversize", "oom", "budget"):
            with self.subTest(phase=phase), patch.object(C, "get_last_error", return_value=8, create=True):
                collector, api, budget = self.collector()
                if phase == "false":
                    api.a.GetTokenInformation.side_effect = None
                    api.a.GetTokenInformation.return_value = False
                elif phase == "oversize":
                    def oversized(*args):
                        args[-1].contents.value = 1025
                        return True
                    api.a.GetTokenInformation.side_effect = oversized
                elif phase == "oom":
                    api.a.GetTokenInformation.side_effect = MemoryError()
                else:
                    budget.side_effect = [None, MemoryError()]
                with self.assertRaises((s.w._Failure, TransportError, MemoryError)):
                    collector.capture(0, 101, budget)
                primary = collector.primary
                with self.assertRaises(TransportError):
                    collector.capture(0, 101, budget)
                self.assertIs(collector.primary, primary)
                api.a.GetTokenInformation.assert_called_once()
                self.assertEqual(collector.resource_stop, phase != "oversize")

    def test_full_capacity_private_hex_stays_within_security_metadata_allowance(self):
        token = acl(b"\x42\x00\x04\x00" * 252, 252)
        descriptor = struct.pack("<BBHIIII", 1, 0, 0x8004, 0, 0, 0, 20) + acl(b"\x42\x00\x04\x00" * 249, 249)
        collector, api, budget = self.collector(token_acl=token, descriptor=descriptor)
        for index in range(5):
            collector.capture(index, 101 + index, budget)
        encoded = json.dumps({"state": collector.state, "rows": collector.rows}, separators=(",", ":"))
        self.assertLess(len(encoded), 16 * 1024)
        self.assertNotIn("descriptor_hex", repr(collector))


if __name__ == "__main__":
    unittest.main()
