"""Synthetic PE/stack bytes only. No Windows API, file or child."""

import importlib.util
import json
import struct
import unittest

from tests.fixtures.anomaly_v03_offline_unwind import Image, UnwindStop, walk


BASE = 0x70000000


def fixture():
    raw = bytearray(0x600)
    raw[:2] = b"MZ"
    struct.pack_into("<I", raw, 60, 0x80)
    raw[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<HH", raw, 0x84, 0x8664, 1)
    struct.pack_into("<H", raw, 0x94, 240)
    opt = 0x98
    struct.pack_into("<H", raw, opt, 0x20b)
    struct.pack_into("<I", raw, opt + 56, 0x2000)
    struct.pack_into("<I", raw, opt + 108, 16)
    struct.pack_into("<II", raw, opt + 136, 0x1200, 36)
    section = opt + 240
    struct.pack_into("<IIII", raw, section + 8, 0x400, 0x1000, 0x400, 0x200)
    struct.pack_into("<I", raw, section + 36, 0x60000020)
    def put(rva, content):
        raw[rva - 0x1000 + 0x200:rva - 0x1000 + 0x200 + len(content)] = content
    put(0x1000, b"\xc3")
    put(0x1020, b"\x53\x48\x83\xec\x20\xe8" + struct.pack("<i", 0x1000 - 0x102a)
        + bytes.fromhex("48836330004883c4205bc3"))
    put(0x1040, bytes.fromhex("4883ec28e8") + struct.pack("<i", 0x1020 - 0x1049)
        + bytes.fromhex("31c04883c428c3"))
    put(0x1100, bytes.fromhex("01000000"))
    put(0x1110, bytes.fromhex("0105020005320130"))
    put(0x1120, bytes.fromhex("0104010004420000"))
    put(0x1200, struct.pack("<9I", 0x1000, 0x1001, 0x1100,
                          0x1020, 0x1035, 0x1110, 0x1040, 0x1050, 0x1120))
    stack = bytearray(2048)
    struct.pack_into("<Q", stack, 0, BASE + 0x102a)
    struct.pack_into("<Q", stack, 40, 0x1122334455667788)
    struct.pack_into("<Q", stack, 48, BASE + 0x1049)
    return raw, stack


@unittest.skipUnless(importlib.util.find_spec("capstone"),
                     "optional offline-analysis extra is not installed; not native acceptance")
class OfflineUnwindTests(unittest.TestCase):
    def test_instruction_operands_are_not_published(self):
        raw, stack = fixture()
        raw[0x22a:0x234] = b"\x48\xb8" + struct.pack("<Q", 0x1122334455667788)
        report = walk(bytes(raw), BASE, BASE + 0x1000, bytes(stack))
        self.assertEqual(len(report["steps"]), 2)
        self.assertEqual(report["steps"][1]["instruction"], "movabs")
        text = json.dumps(report)
        self.assertNotIn("1122334455667788", text)
        self.assertNotIn(str(0x1122334455667788), text)

    def test_two_callers_verified_and_private_values_omitted(self):
        raw, stack = fixture()
        report = walk(bytes(raw), BASE, BASE + 0x1000, bytes(stack))
        self.assertEqual(len(report["steps"]), 2)
        self.assertEqual([x["return_stack_offset"] for x in report["steps"]], [0, 48])
        self.assertEqual(report["steps"][1]["restored_registers"], [3])
        self.assertEqual(report["stop_reason"], "non_executable_rva")
        self.assertNotIn(str(0x1122334455667788), json.dumps(report))
        self.assertFalse(report["native_accepted"])

    def test_call_target_mismatch_does_not_accept_candidate(self):
        raw, stack = fixture()
        struct.pack_into("<i", raw, 0x226, 1)
        report = walk(bytes(raw), BASE, BASE + 0x1000, bytes(stack))
        self.assertEqual(report["stop_reason"], "direct_call_target_mismatch")
        self.assertEqual(len(report["frames"]), 1)

    def test_chain_and_unhandled_opcodes_stop(self):
        for value, expected in ((0x21, "unwind_flags_or_frame_register"),
                                (2, "unwind_version")):
            raw, stack = fixture()
            raw[0x310] = value
            report = walk(bytes(raw), BASE, BASE + 0x1000, bytes(stack))
            self.assertEqual(report["stop_reason"], expected)
            self.assertEqual(len(report["steps"]), 1)
        raw, stack = fixture()
        raw[0x315] = 0x3a
        report = walk(bytes(raw), BASE, BASE + 0x1000, bytes(stack))
        self.assertEqual(report["stop_reason"], "unwind_opcode_unsupported_10")

    def test_large_allocation_cannot_leave_saved_window(self):
        raw, stack = fixture()
        raw[0x314:0x318] = bytes.fromhex("05010002")
        report = walk(bytes(raw), BASE, BASE + 0x1000, bytes(stack))
        self.assertEqual(report["stop_reason"], "saved_stack_exhausted")
        self.assertEqual(len(report["steps"]), 1)

    def test_potential_epilogue_and_mid_instruction_stop(self):
        raw, stack = fixture()
        report = walk(bytes(raw), BASE, BASE + 0x102f, bytes(stack))
        self.assertEqual(report["stop_reason"], "possible_epilogue_unsupported")
        report = walk(bytes(raw), BASE, BASE + 0x102b, bytes(stack))
        self.assertEqual(report["stop_reason"], "instruction_boundary")

    def test_pe_range_and_stack_shape_are_checked(self):
        raw, stack = fixture()
        with self.assertRaises(UnwindStop): Image(bytes(raw[:64]))
        with self.assertRaises(UnwindStop): walk(bytes(raw), BASE, BASE + 0x1000, b"")
        struct.pack_into("<I", raw, 0x98 + 136, 0x1fff)
        with self.assertRaises(UnwindStop): Image(bytes(raw))
