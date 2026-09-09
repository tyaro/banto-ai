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


def chained_fixture():
    raw, stack = fixture()
    raw[0x210:0x216] = bytes.fromhex("534883ec2090")
    raw[0x220:0x232] = (bytes.fromhex("488974243048897c2438e8")
                        + struct.pack("<i", 0x1000 - 0x102f) + bytes.fromhex("31c0c3"))
    raw[0x330:0x338] = bytes.fromhex("0105020005320130")
    raw[0x340:0x358] = (bytes.fromhex("210a04000a74070005640600")
                        + struct.pack("<III", 0x1010, 0x1016, 0x1130))
    struct.pack_into("<II", raw, 0x98 + 136, 0x1200, 48)
    struct.pack_into("<12I", raw, 0x400, 0x1000, 0x1001, 0x1100,
                     0x1010, 0x1016, 0x1130, 0x1020, 0x1032, 0x1140,
                     0x1040, 0x1050, 0x1120)
    struct.pack_into("<i", raw, 0x245, 0x1010 - 0x1049)
    struct.pack_into("<Q", stack, 0, BASE + 0x102f)
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
        for value, expected in ((0x29, "unwind_flags_or_frame_register"),
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

    def test_chained_saves_use_primary_entry_and_fixed_stack_base(self):
        raw, stack = chained_fixture()
        report = walk(bytes(raw), BASE, BASE + 0x1000, bytes(stack))
        self.assertEqual(len(report["steps"]), 2)
        step = report["steps"][1]
        self.assertEqual(step["primary_entry_rva"], "0x1010")
        self.assertEqual(step["unwind_chain_rvas"], ["0x1140", "0x1130"])
        self.assertEqual(step["restored_registers"], [7, 6, 3])
        self.assertEqual(step["return_stack_offset"], 48)
        self.assertEqual(step["call_target_rva"], "0x1010")
        # A direct call to the secondary fragment is not a primary entry call.
        struct.pack_into("<i", raw, 0x245, 0x1020 - 0x1049)
        rejected = walk(bytes(raw), BASE, BASE + 0x1000, bytes(stack))
        self.assertEqual(len(rejected["steps"]), 1)
        self.assertEqual(rejected["stop_reason"], "direct_call_target_mismatch")

    def test_chained_bare_ret_does_not_unwind_body_again(self):
        raw, stack = chained_fixture()
        struct.pack_into("<Q", stack, 0, BASE + 0x1049)
        report = walk(bytes(raw), BASE, BASE + 0x1031, bytes(stack))
        self.assertEqual(len(report["steps"]), 1)
        self.assertEqual(report["steps"][0]["return_stack_offset"], 0)
        self.assertEqual(report["steps"][0]["restored_registers"], [])

    def test_chain_cycle_and_non_table_parent_are_rejected(self):
        for parent, expected in (((0x1020, 0x1032, 0x1140), "unwind_chain_cycle"),
                                 ((0x1010, 0x1015, 0x1130), "unwind_chain_entry")):
            raw, stack = chained_fixture()
            struct.pack_into("<III", raw, 0x34c, *parent)
            report = walk(bytes(raw), BASE, BASE + 0x1000, bytes(stack))
            self.assertEqual(report["stop_reason"], expected)
            self.assertEqual(len(report["steps"]), 1)

    def test_chain_rejects_stack_changes_bad_slots_and_saved_window_escape(self):
        for offset, value, expected in ((0x345, 0x32, "unwind_chain_save_only"),
                                        (0x342, 3, "unwind_chain_save_only"),
                                        (0x344, 11, "unwind_code_order"),
                                        (0x347, 1, "saved_stack_exhausted")):
            raw, stack = chained_fixture()
            raw[offset] = value
            report = walk(bytes(raw), BASE, BASE + 0x1000, bytes(stack))
            self.assertEqual(report["stop_reason"], expected)
            self.assertEqual(len(report["steps"]), 1)

    def test_chain_depth_is_bounded(self):
        raw, _ = fixture()
        rows = [(0x1000 + i * 16, 0x1001 + i * 16, 0x1300 + i * 16) for i in range(9)]
        struct.pack_into("<II", raw, 0x98 + 136, 0x1200, len(rows) * 12)
        for i, row in enumerate(rows):
            struct.pack_into("<III", raw, 0x400 + i * 12, *row)
            off = row[2] - 0x1000 + 0x200
            raw[off:off + 4] = bytes((0x21 if i else 1, 0, 0, 0))
            if i:
                struct.pack_into("<III", raw, off + 4, *rows[i - 1])
        image = Image(bytes(raw))
        self.assertEqual(len(image.unwind_chain(rows[7], rows[7][0])), 8)
        with self.assertRaisesRegex(UnwindStop, "unwind_chain_limit"):
            image.unwind_chain(rows[8], rows[8][0])

    def test_handler_metadata_does_not_change_context_unwind(self):
        for flags in (1, 2, 3):
            raw, stack = fixture()
            raw[0x310] = 1 | flags << 3
            struct.pack_into("<I", raw, 0x318, 0x1000)
            raw[0x31c:0x320] = b"\xff" * 4  # Opaque language-specific data.
            report = walk(bytes(raw), BASE, BASE + 0x1000, bytes(stack))
            self.assertEqual(len(report["steps"]), 2)
            self.assertEqual(report["steps"][1]["handler_rva"], "0x1000")
            self.assertEqual(report["steps"][1]["return_stack_offset"], 48)
            self.assertFalse(report["handlers_invoked"])
        raw, stack = chained_fixture()
        raw[0x330] = 0x11
        struct.pack_into("<I", raw, 0x338, 0x1000)
        report = walk(bytes(raw), BASE, BASE + 0x1000, bytes(stack))
        self.assertEqual(len(report["steps"]), 2)
        self.assertEqual(report["steps"][1]["handler_rva"], "0x1000")

    def test_invalid_or_truncated_handler_rva_stops_before_accepting(self):
        for target in (0, 0x1021, 0x1fff, 0xffffffff):
            raw, stack = fixture()
            raw[0x310] = 0x11
            struct.pack_into("<I", raw, 0x318, target)
            report = walk(bytes(raw), BASE, BASE + 0x1000, bytes(stack))
            self.assertEqual(len(report["steps"]), 1)
        raw, stack = fixture()
        struct.pack_into("<I", raw, 0x414, 0x13fc)
        raw[0x5fc:0x600] = bytes.fromhex("11000000")
        report = walk(bytes(raw), BASE, BASE + 0x1000, bytes(stack))
        self.assertEqual(len(report["steps"]), 1)
        self.assertEqual(report["stop_reason"], "rva_mapping")

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

    def test_non_stack_arithmetic_is_body_but_stack_aliases_still_stop(self):
        for code, accepted in (("488d4c2420", True), ("83c0019090", True),
                               ("488d642420", False), ("8d64242090", False),
                               ("4883c40190", False), ("83c4019090", False)):
            raw, stack = fixture()
            raw[0x22a:0x22f] = bytes.fromhex(code)
            report = walk(bytes(raw), BASE, BASE + 0x1000, bytes(stack))
            self.assertEqual(len(report["steps"]), 2 if accepted else 1, code)
            if not accepted:
                self.assertEqual(report["stop_reason"], "possible_epilogue_unsupported", code)

    def test_pe_range_and_stack_shape_are_checked(self):
        raw, stack = fixture()
        with self.assertRaises(UnwindStop): Image(bytes(raw[:64]))
        with self.assertRaises(UnwindStop): walk(bytes(raw), BASE, BASE + 0x1000, b"")
        struct.pack_into("<I", raw, 0x98 + 136, 0x1fff)
        with self.assertRaises(UnwindStop): Image(bytes(raw))
