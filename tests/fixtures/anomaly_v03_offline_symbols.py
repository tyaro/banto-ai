"""Bounded MSF7/PDB public-function lookup from bytes only.

No file/network/native calls. GUID/DBI age and PE section headers must match;
the PDB Info age may be newer, following Microsoft's OpenValidate4 rule.
Only exact requested entry RVAs are returned; OMAP is deliberately unsupported.
This is a limited reader, not full PDB validation or loaded-image authentication.
"""

import struct


class SymbolStop(ValueError):
    pass


def need(value, reason):
    if not value:
        raise SymbolStop(reason)


def part(raw, offset, size):
    need(0 <= offset and 0 <= size and offset + size <= len(raw), "pdb_bounds")
    return raw[offset:offset + size]


def number(raw, offset, code="I"):
    return struct.unpack("<" + code, part(raw, offset, struct.calcsize("<" + code)))[0]


class Msf:
    def __init__(self, raw):
        need(type(raw) is bytes and 4096 <= len(raw) <= 16 * 1024 * 1024, "pdb_size")
        need(raw[:32] == b"Microsoft C/C++ MSF 7.00\r\n\x1aDS\0\0\0", "msf_magic")
        block_size, free_map, blocks, directory_size, _, block_map = struct.unpack("<6I", part(raw, 32, 24))
        need(block_size == 4096 and free_map in (1, 2) and blocks * block_size == len(raw),
             "msf_layout")
        need(4 <= directory_size <= 1024 * 1024 and 3 <= block_map < blocks, "msf_directory_size")
        self.raw, self.blocks = raw, blocks
        used = {0, block_map} | {i for i in range(blocks) if i % 4096 in (1, 2)}
        need(block_map % 4096 not in (1, 2), "msf_block_map")

        def claim(indices):
            need(all(0 <= i < blocks and i not in used for i in indices)
                 and len(set(indices)) == len(indices), "msf_block_overlap_or_range")
            used.update(indices)

        count = (directory_size + 4095) // 4096
        pointers = part(raw, block_map * 4096, count * 4)
        directory_blocks = [row[0] for row in struct.iter_unpack("<I", pointers)]
        claim(directory_blocks)
        directory = self.join(directory_blocks, directory_size)
        streams = number(directory, 0)
        need(4 <= streams <= 4096, "msf_stream_count")
        sizes = [row[0] for row in struct.iter_unpack("<I", part(directory, 4, streams * 4))]
        cursor = 4 + streams * 4
        self.streams = []
        for size in sizes:
            need(size == 0xffffffff or size <= len(raw), "msf_stream_size")
            count = 0 if size == 0xffffffff else (size + 4095) // 4096
            pointers = part(directory, cursor, count * 4)
            indices = [row[0] for row in struct.iter_unpack("<I", pointers)]
            claim(indices)
            self.streams.append((size, indices))
            cursor += count * 4
        need(cursor == len(directory), "msf_directory_tail")

    def join(self, blocks, size):
        return b"".join(part(self.raw, index * 4096, 4096) for index in blocks)[:size]

    def stream(self, index, limit):
        need(type(index) is int and 0 <= index < len(self.streams), "pdb_stream_index")
        size, blocks = self.streams[index]
        need(size != 0xffffffff and size <= limit, "pdb_stream_size")
        return self.join(blocks, size)


def match_public_functions(raw, guid_bytes_le, age, pe_section_headers, entry_rvas):
    """Match public function symbols at exact image-relative entry addresses."""
    need(type(guid_bytes_le) is bytes and len(guid_bytes_le) == 16 and any(guid_bytes_le)
         and type(age) is int and 0 < age < 2**32, "expected_pdb_identity")
    need(type(pe_section_headers) is bytes and 40 <= len(pe_section_headers) <= 96 * 40
         and len(pe_section_headers) % 40 == 0, "expected_sections")
    need(type(entry_rvas) in (list, tuple) and 1 <= len(entry_rvas) <= 16
         and all(type(rva) is int and 0 < rva < 128 * 1024 * 1024 for rva in entry_rvas),
         "lookup_entries")
    wanted = set(entry_rvas)
    msf = Msf(raw)
    info = msf.stream(1, 65536)
    info_age = number(info, 8)
    # Microsoft PDB1::OpenValidate4: Info age >= image age, DBI age == image age.
    # We do not accept the legacy DBI-age-zero exception.
    need(number(info, 0) == 20000404 and info_age >= age
         and part(info, 12, 16) == guid_bytes_le, "pdb_guid_age_mismatch")
    dbi = msf.stream(3, 4 * 1024 * 1024)
    need(number(dbi, 0, "i") == -1 and number(dbi, 4) == 19990903
         and number(dbi, 8) == age and number(dbi, 58, "H") == 0x8664, "pdb_dbi_identity")
    sizes = [number(dbi, offset, "i") for offset in (24, 28, 32, 36, 40, 52, 48)]
    need(all(size >= 0 for size in sizes) and 64 + sum(sizes) == len(dbi), "pdb_dbi_substreams")
    optional = part(dbi, 64 + sum(sizes[:-1]), sizes[-1])
    need(12 <= len(optional) <= 64 and len(optional) % 2 == 0, "pdb_debug_header")
    need(number(optional, 6, "H") == number(optional, 8, "H") == 0xffff, "pdb_omap_unsupported")
    section_headers = msf.stream(number(optional, 10, "H"), 96 * 40)
    need(section_headers == pe_section_headers, "pdb_section_headers_mismatch")
    sections = []
    for offset in range(0, len(section_headers), 40):
        virtual_size, rva = struct.unpack("<II", part(section_headers, offset + 8, 8))
        flags = number(section_headers, offset + 36)
        need(0 < rva and rva + virtual_size <= 128 * 1024 * 1024, "pdb_section_range")
        sections.append((rva, virtual_size, flags))
    for rva in wanted:
        matches = [row for row in sections if row[0] <= rva < row[0] + row[1]]
        need(len(matches) == 1 and matches[0][2] & 0x20000000, "lookup_not_executable")

    symbols = msf.stream(number(dbi, 20, "H"), 8 * 1024 * 1024)
    cursor, count, public_functions = 0, 0, 0
    names = {hex(rva): [] for rva in sorted(wanted)}
    while cursor < len(symbols):
        length, kind = struct.unpack("<HH", part(symbols, cursor, 4))
        need(length >= 2, "pdb_record_length")
        record = part(symbols, cursor, length + 2)
        count += 1
        need(count <= 200000, "pdb_record_limit")
        if kind == 0x110e:  # S_PUB32
            flags, offset, segment = struct.unpack("<IIH", part(record, 4, 10))
            need(flags & ~15 == 0, "pdb_public_flags")
            if flags & 2:  # Function; data symbols cannot label a function.
                public_functions += 1
                need(1 <= segment <= len(sections), "pdb_symbol_segment")
                base, size, section_flags = sections[segment - 1]
                need(offset < size, "pdb_symbol_offset")
                rva = base + offset
                if rva in wanted:
                    name, terminator, padding = record[14:].partition(b"\0")
                    need(terminator and 0 < len(name) <= 512
                         and all(32 <= byte < 127 for byte in name)
                         and len(padding) <= 3 and all(byte in (0, 0xf1, 0xf2, 0xf3) for byte in padding),
                         "pdb_symbol_name")
                    decoded = name.decode("ascii")
                    if decoded not in names[hex(rva)]:
                        names[hex(rva)].append(decoded)
                        need(len(names[hex(rva)]) <= 8, "pdb_symbol_alias_limit")
        cursor += len(record)
    return {"pdb_guid_match": True, "pdb_info_age_compatible": True,
            "image_age": age, "pdb_info_age": info_age, "dbi_age": number(dbi, 8),
            "dbi_age_machine_match": True,
            "section_headers_match": True, "omap_present": False,
            "record_count": count, "public_function_count": public_functions,
            "exact_entry_symbols": names, "loaded_bytes_match_proven": False,
            "native_accepted": False}
