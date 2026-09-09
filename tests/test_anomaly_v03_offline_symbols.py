"""Synthetic PDB bytes only; no symbol server, disk, API or child access."""

import struct
import unittest

from tests.fixtures.anomaly_v03_offline_symbols import Msf, SymbolStop, match_public_functions


GUID = bytes(range(1, 17))


def public(name, offset=16, flags=2, segment=1):
    body = struct.pack("<HIIH", 0x110e, flags, offset, segment) + name + b"\0"
    padding = (-len(body) - 2) % 4
    return struct.pack("<H", len(body) + padding) + body + b"\0" * padding


def fixture(symbols=None):
    section = bytearray(40)
    section[:8] = b".text\0\0\0"
    struct.pack_into("<IIII", section, 8, 0x1000, 0x1000, 0x1000, 0x400)
    struct.pack_into("<I", section, 36, 0x60000020)
    info = struct.pack("<III", 20000404, 0, 1) + GUID
    dbi = bytearray(86)
    struct.pack_into("<iII", dbi, 0, -1, 19990903, 1)
    struct.pack_into("<H", dbi, 20, 4)
    struct.pack_into("<i", dbi, 48, 22)
    struct.pack_into("<HH", dbi, 56, 2, 0x8664)
    dbi[64:] = b"\xff" * 22
    struct.pack_into("<H", dbi, 74, 5)
    if symbols is None:
        symbols = public(b"Near", 0) + public(b"Target") + public(b"Alias") + public(b"Data", flags=0)
    streams = [None, info, None, dbi, symbols, section]
    raw = bytearray(9 * 4096)
    raw[:32] = b"Microsoft C/C++ MSF 7.00\r\n\x1aDS\0\0\0"
    directory = struct.pack("<7I", 6, *(0xffffffff if s is None else len(s) for s in streams))
    directory += struct.pack("<4I", 5, 6, 7, 8)
    struct.pack_into("<6I", raw, 32, 4096, 1, 9, len(directory), 0, 3)
    struct.pack_into("<I", raw, 3 * 4096, 4)
    raw[4 * 4096:4 * 4096 + len(directory)] = directory
    for block, data in zip((5, 6, 7, 8), (info, dbi, symbols, section)):
        assert len(data) <= 4096
        raw[block * 4096:block * 4096 + len(data)] = data
    return raw, bytes(section)


def lookup(raw, sections, entries=(0x1001, 0x1010)):
    return match_public_functions(bytes(raw), GUID, 1, sections, entries)


class OfflineSymbolTests(unittest.TestCase):
    def test_exact_entries_only_and_aliases_retained(self):
        raw, sections = fixture()
        report = lookup(raw, sections)
        self.assertEqual(report["exact_entry_symbols"], {"0x1001": [], "0x1010": ["Target", "Alias"]})
        self.assertTrue(report["pdb_guid_match"])
        self.assertFalse(report["loaded_bytes_match_proven"])
        self.assertFalse(report["native_accepted"])

    def test_identity_and_machine_mismatch_stop(self):
        for offset, data in ((5 * 4096 + 12, b"\xff"), (5 * 4096 + 8, b"\x00"),
                             (6 * 4096 + 8, b"\x02"), (6 * 4096 + 8, b"\x00"),
                             (6 * 4096 + 58, b"\0\0")):
            raw, sections = fixture()
            raw[offset:offset + len(data)] = data
            with self.assertRaises(SymbolStop):
                lookup(raw, sections)

    def test_newer_info_age_requires_exact_dbi_age(self):
        raw, sections = fixture()
        struct.pack_into("<I", raw, 5 * 4096 + 8, 4)
        report = lookup(raw, sections)
        self.assertEqual((report["image_age"], report["pdb_info_age"], report["dbi_age"]), (1, 4, 1))
        self.assertEqual(report["exact_entry_symbols"]["0x1010"], ["Target", "Alias"])
        struct.pack_into("<I", raw, 6 * 4096 + 8, 4)
        with self.assertRaisesRegex(SymbolStop, "pdb_dbi_identity"):
            lookup(raw, sections)

    def test_msf_shape_block_ranges_and_ownership(self):
        for offset, value in ((32, 512), (40, 10),
                               (3 * 4096, 9), (4 * 4096 + 28, 4), (4 * 4096 + 32, 5)):
            raw, _ = fixture()
            struct.pack_into("<I", raw, offset, value)
            with self.assertRaises(SymbolStop):
                Msf(bytes(raw))
        raw, _ = fixture()
        with self.assertRaises(SymbolStop):
            Msf(bytes(raw[:-1]))

    def test_dbi_sizes_indices_and_omap(self):
        for offset, code, value in ((24, "i", -1), (48, "i", 20), (20, "H", 0xffff),
                                   (70, "H", 4), (72, "H", 4)):
            raw, sections = fixture()
            struct.pack_into("<" + code, raw, 6 * 4096 + offset, value)
            with self.assertRaises(SymbolStop):
                lookup(raw, sections)

    def test_section_headers_and_executable_mapping(self):
        raw, sections = fixture()
        different = bytearray(sections)
        different[8] ^= 1
        with self.assertRaisesRegex(SymbolStop, "pdb_section_headers_mismatch"):
            lookup(raw, bytes(different))
        with self.assertRaisesRegex(SymbolStop, "lookup_not_executable"):
            lookup(raw, sections, (0x3000,))
        struct.pack_into("<I", raw, 8 * 4096 + 36, 0x40000040)
        with self.assertRaisesRegex(SymbolStop, "lookup_not_executable"):
            lookup(raw, bytes(raw[8 * 4096:8 * 4096 + 40]))

    def test_malformed_records_and_symbol_bounds(self):
        for symbols in (b"\0\0\0\0", b"\xff\xff\x0e\x11", public(b"Bad", segment=0),
                        public(b"Bad", offset=0x1000), public(b"Bad", flags=18),
                        public(b"Bad\nName"), public(b"A" * 513)):
            raw, sections = fixture(symbols)
            with self.assertRaises(SymbolStop):
                lookup(raw, sections)
        raw, sections = fixture(public(b"Bad"))
        raw[7 * 4096 + 14:7 * 4096 + 20] = b"x" * 6
        with self.assertRaisesRegex(SymbolStop, "pdb_symbol_name"):
            lookup(raw, sections)

    def test_lookup_and_alias_counts_are_bounded(self):
        raw, sections = fixture(b"".join(public(str(i).encode()) for i in range(9)))
        with self.assertRaisesRegex(SymbolStop, "pdb_symbol_alias_limit"):
            lookup(raw, sections)
        with self.assertRaisesRegex(SymbolStop, "lookup_entries"):
            lookup(raw, sections, [0x1010] * 17)


if __name__ == "__main__":
    unittest.main()
