"""Conservative byte-only x64 unwind of one PE image and a saved stack window.

No IO, remote reads, symbols, execution or native acceptance. Only complete
version-1, frame-pointer-free bodies and a bare RET are supported. Secondary
chained records may only save nonvolatile registers without changing RSP.
Every accepted caller must directly CALL the previous function's primary entry.
Handler RVAs are range-checked only; no handler or language data is evaluated.
"""

import struct


class UnwindStop(ValueError):
    pass


def need(value, reason):
    if not value:
        raise UnwindStop(reason)


class Image:
    def __init__(self, raw):
        need(type(raw) is bytes and 64 <= len(raw) <= 8 * 1024 * 1024, "image_size")
        self.raw = raw
        pe = self.number(60, "I")
        need(raw[:2] == b"MZ" and self.slice(pe, 4) == b"PE\0\0", "pe_signature")
        need(self.number(pe + 4, "H") == 0x8664, "pe_machine")
        count, optional_size = self.number(pe + 6, "H"), self.number(pe + 20, "H")
        optional = pe + 24
        need(1 <= count <= 96 and optional_size >= 144
             and self.number(optional, "H") == 0x20b, "pe_optional")
        need(self.number(optional + 108, "I") >= 4, "pe_directories")
        self.size = self.number(optional + 56, "I")
        need(0 < self.size <= 128 * 1024 * 1024, "image_virtual_size")
        self.sections = []
        for index in range(count):
            off = optional + optional_size + index * 40
            row = self.slice(off, 40)
            virtual_size, rva, size, pointer = struct.unpack_from("<IIII", row, 8)
            flags = struct.unpack_from("<I", row, 36)[0]
            need(rva + max(virtual_size, size) <= self.size and pointer + size <= len(raw),
                 "section_bounds")
            self.sections.append((rva, virtual_size, size, pointer, flags))
        rva, size = struct.unpack("<II", self.slice(optional + 136, 8))
        need(0 < size <= 1024 * 1024 and size % 12 == 0, "runtime_table_size")
        table = self.at(rva, size)
        self.functions = list(struct.iter_unpack("<III", table))
        previous_end = 0
        for start, end, unwind in self.functions:
            need(previous_end <= start < end <= self.size and 0 < unwind < self.size
                 and unwind % 4 == 0, "runtime_table_bounds")
            previous_end = end

    def slice(self, off, size):
        need(0 <= off and 0 <= size and off + size <= len(self.raw), "file_bounds")
        return self.raw[off:off + size]

    def number(self, off, code):
        return struct.unpack("<" + code, self.slice(off, struct.calcsize("<" + code)))[0]

    def at(self, rva, size):
        need(0 <= rva and 0 <= size and rva + size <= self.size, "rva_bounds")
        matches = [pointer + rva - start for start, vs, rawsize, pointer, flags in self.sections
                   if start <= rva and rva + size <= start + rawsize]
        need(len(matches) == 1, "rva_mapping")
        return self.slice(matches[0], size)

    def function(self, rva):
        need(any(start <= rva < start + size and flags & 0x20000000
                 for start, size, rawsize, pointer, flags in self.sections), "non_executable_rva")
        matches = [row for row in self.functions if row[0] <= rva < row[1]]
        need(len(matches) == 1, "runtime_function_missing")
        return matches[0]

    def instructions(self, function, decoder):
        start, end, unwind = function
        need(end - start <= 16384, "function_decode_limit")
        code = self.at(start, end - start)
        instructions = list(decoder.disasm(code, start))
        need(instructions and sum(i.size for i in instructions) == len(code), "function_decode_incomplete")
        return instructions

    def unwind_chain(self, function, rva):
        """Bounded metadata chain, with exact pdata membership for each parent."""
        records, seen = [], set()
        for _ in range(8):
            start, end, unwind = function
            need(unwind not in seen, "unwind_chain_cycle")
            seen.add(unwind)
            version_flags, prolog, count, frame = self.at(unwind, 4)
            need(version_flags & 7 == 1, "unwind_version")
            flags = version_flags >> 3
            need(flags in (0, 1, 2, 3, 4) and frame == 0, "unwind_flags_or_frame_register")
            need(prolog <= end - start, "unwind_prolog_size")
            need(records or rva - start >= prolog, "in_prolog")
            padded_size = ((count + 1) // 2) * 4
            codes = self.at(unwind + 4, padded_size)[:count * 2]
            if flags == 4:
                # Shrink-wrapped saves may not push or allocate another frame.
                index, last_offset = 0, prolog + 1
                while index < count:
                    offset, packed = codes[index * 2:index * 2 + 2]
                    need(0 < offset <= prolog and offset <= last_offset, "unwind_code_order")
                    need(packed & 15 == 4 and packed >> 4 in (3, 5, 6, 7, 12, 13, 14, 15)
                         and index + 2 <= count, "unwind_chain_save_only")
                    last_offset, index = offset, index + 2
            handler = None
            if flags in (1, 2, 3):
                handler = struct.unpack("<I", self.at(unwind + 4 + padded_size, 4))[0]
                # This is a context walk, not exception dispatch. Validate the
                # handler entry but never decode/call it or parse language data.
                need(self.function(handler)[0] == handler, "unwind_handler_entry")
                self.at(handler, 1)
            records.append((function, prolog, count, codes, handler))
            if flags != 4:
                return records
            parent = struct.unpack("<III", self.at(unwind + 4 + padded_size, 12))
            need(parent in self.functions and self.function(parent[0]) == parent,
                 "unwind_chain_entry")
            need(parent[2] not in seen, "unwind_chain_cycle")
            need(parent[1] <= start, "unwind_chain_order")
            function = parent
        raise UnwindStop("unwind_chain_limit")


def walk(raw_image, image_base, rip, stack, *, limit=16):
    """Return image-relative frames only; input provenance belongs to the caller.

    A stopped row is diagnostic metadata, not an accepted additional frame.
    Missing image/stack/unsupported unwind semantics stop the walk explicitly.
    """
    import capstone

    need(type(stack) is bytes and len(stack) == 2048, "stack_size")
    need(type(image_base) is int and type(rip) is int and 0 < image_base <= rip < 2**64,
         "address_range")
    need(type(limit) is int and 1 <= limit <= 16, "frame_limit")
    image = Image(raw_image)
    decoder = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    decoder.detail = True
    report = {"frames": [], "steps": [], "stop_reason": "frame_limit",
              "capstone_version": capstone.__version__, "loaded_bytes_match_proven": False,
              "native_accepted": False, "handlers_invoked": False}
    sp, rva = 0, rip - image_base
    registers = {}

    def read_stack(offset):
        need(0 <= offset <= len(stack) - 8, "saved_stack_exhausted")
        return struct.unpack_from("<Q", stack, offset)[0]

    try:
        first_function = image.function(rva)
        report["frames"].append({"rip_rva": hex(rva), "begin_rva": hex(first_function[0]),
                                 "end_rva": hex(first_function[1]), "stack_offset": sp})
        for _ in range(limit):
            function = image.function(rva)
            start, end, unwind = function
            instructions = image.instructions(function, decoder)
            current = [i for i in instructions if i.address == rva]
            need(len(current) == 1, "instruction_boundary")
            instruction = current[0]
            records = image.unwind_chain(function, rva)
            primary_start = records[-1][0][0]
            step = {"from_rva": hex(rva), "unwind_rva": hex(unwind), "stack_offset_before": sp,
                    "instruction": instruction.mnemonic,
                    "primary_entry_rva": hex(primary_start),
                    "unwind_chain_rvas": [hex(row[0][2]) for row in records],
                    "handler_rva": hex(records[-1][4]) if records[-1][4] is not None else None,
                    "restored_registers": []}
            cursor = sp
            if instruction.bytes == b"\xc3":
                # A bare RET is the last epilogue instruction; no prolog effects remain.
                step["mode"] = "bare_ret"
            else:
                # Stack adjustment can begin an epilogue; arithmetic on other
                # registers cannot. Still reject unknown destinations and SP aliases.
                need(instruction.mnemonic not in ("pop", "ret", "jmp"),
                     "possible_epilogue_unsupported")
                if instruction.mnemonic in ("add", "lea"):
                    operands = instruction.operands
                    need(operands and operands[0].type == capstone.x86.X86_OP_REG
                         and instruction.reg_name(operands[0].reg) not in ("rsp", "esp", "sp", "spl"),
                         "possible_epilogue_unsupported")
                step["mode"] = "body"
                for _, prolog, count, codes, _ in records:
                    index, last_offset = 0, prolog + 1
                    while index < count:
                        code_offset, packed = codes[index * 2:index * 2 + 2]
                        opcode, info = packed & 15, packed >> 4
                        need(0 < code_offset <= prolog and code_offset <= last_offset, "unwind_code_order")
                        last_offset = code_offset
                        index += 1
                        if opcode == 0:  # UWOP_PUSH_NONVOL
                            need(info in (3, 5, 6, 7, 12, 13, 14, 15), "volatile_register")
                            registers[info] = read_stack(cursor)
                            step["restored_registers"].append(info)
                            cursor += 8
                        elif opcode == 2:  # UWOP_ALLOC_SMALL
                            cursor += info * 8 + 8
                        elif opcode == 1:  # UWOP_ALLOC_LARGE
                            slots = 1 if info == 0 else 2
                            need(info in (0, 1) and index + slots <= count, "unwind_large_slots")
                            amount = int.from_bytes(codes[index * 2:(index + slots) * 2], "little")
                            cursor += amount * 8 if info == 0 else amount
                            index += slots
                        elif opcode == 4:  # UWOP_SAVE_NONVOL, no frame pointer
                            need(info in (3, 5, 6, 7, 12, 13, 14, 15) and index < count,
                                 "unwind_save_slots")
                            offset = int.from_bytes(codes[index * 2:index * 2 + 2], "little") * 8
                            registers[info] = read_stack(sp + offset)
                            step["restored_registers"].append(info)
                            index += 1
                        else:
                            raise UnwindStop("unwind_opcode_unsupported_" + str(opcode))
                        need(sp <= cursor <= len(stack), "saved_stack_exhausted")
            address = read_stack(cursor)
            caller_rva = address - image_base
            caller_function = image.function(caller_rva)
            caller_instructions = image.instructions(caller_function, decoder)
            calls = [i for i in caller_instructions if i.address + i.size == caller_rva
                     and i.mnemonic == "call" and i.size == 5 and i.bytes[0] == 0xe8]
            need(len(calls) == 1, "direct_callsite_missing")
            call = calls[0]
            target = caller_rva + int.from_bytes(call.bytes[1:], "little", signed=True)
            need(target == primary_start, "direct_call_target_mismatch")
            step.update(return_stack_offset=cursor, caller_rva=hex(caller_rva),
                        callsite_rva=hex(call.address), call_target_rva=hex(target))
            report["steps"].append(step)
            sp, rva = cursor + 8, caller_rva
            report["frames"].append({"rip_rva": hex(rva), "begin_rva": hex(caller_function[0]),
                                     "end_rva": hex(caller_function[1]), "stack_offset": sp})
    except UnwindStop as error:
        report["stop_reason"] = str(error)
    return report
