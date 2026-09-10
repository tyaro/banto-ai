"""Opt-in four-site console failure probe; first exception always ends the run.

Uses the existing owned initial thread and debug-register-only Set once.
Retains a candidate status before cleanup; never continues a captured exception
normally, infers a final root cause, restores registers, or rearms a slot.
"""

import hashlib
import json
import struct

from banto_ai import _anomaly_v03_windows as w
from tests.fixtures.anomaly_v03_debug_init_return import DebugInitReturn
from tests.fixtures.anomaly_v03_debug_transport import TransportError, need


class DebugConsoleFailure(DebugInitReturn):
    RECIPE = "kernelbase-26200.9445-console-failure-v1"
    BREAK_RVAS = (0xBECC2, 0xBECAF, 0xBED34, 0xBED9C)
    CANDIDATES = ("critical_section", "allocation", "connection", "standard_io")
    CALLER_RVA = 0x4EBE6
    WINDOWS = (
        (0x4E6C0, 1836, "ff2bf35f46cc2d9a066260b8678a9e0ef6d0bacfb12c4374199e6bb58ae8870c"),
        (0xBEB60, 586, "d162a1ead64d7d54975d3b4440ee8280b3a924113f1a870f284f5a6d36aceeb3"),
    )
    READ_LIMIT, BYTE_LIMIT = 4, 2432  # code 2422 + caller slot 8 + stage 2

    def __init__(self, images):
        super().__init__(images)
        self.targets = None
        self.hit_index = self.caller_slot = None

    def __repr__(self):
        return "DebugConsoleFailure(<private registers and caller>)"

    def _read(self, address, size, budget):
        # Fixed sequence only. The sole stack read is the verified frame's
        # return-address slot; its contents are never followed as a pointer.
        index = self.row["read_attempts"]
        need(index < self.READ_LIMIT, "console_read_limit")
        expected = ((self.base + self.WINDOWS[index][0], self.WINDOWS[index][1])
                    if index < 2 else (self.caller_slot, 8) if index == 2
                    else (self.base + self.STAGE_RVA, 2))
        need(type(address) is int and address >= 0x10000 and 0 < size <= self.STACK_SIZE
             and address <= self.USER_MAX - size + 1 and (address, size) == expected,
             "console_read_range")
        need(self.row["confirmed_bytes"] + size <= self.BYTE_LIMIT, "console_byte_limit")
        self._budget(budget)
        self.row["read_attempts"] += 1
        self.row["read_state"] = "uncertain"
        self.bytes_read.value = 0
        ok = self.kernel.ReadProcessMemory(self.stop.handles[0], w.H(address), self.stack_pointer,
                                          size, self.bytes_read_pointer)
        self.row["last_read_bytes"] = self.bytes_read.value
        if not ok:
            self.row["read_state"] = "failed"
            raise w._Failure("console_memory_read", self.transport.last_error())
        self._budget(budget)
        need(self.bytes_read.value == size, "console_read_length")
        self.row["read_state"] = "confirmed"
        self.row["confirmed_bytes"] += size
        return self.stack.raw[:size]

    def _programmed(self, registers, *, hit):
        dr6, dr7 = registers[4:]
        cause = (1 << self.hit_index) if hit else 0
        checks = {"dr0_to_dr3_match": registers[:4] == self.targets,
                  "dr7_matches": dr7 & ~0x400 == 0x55,
                  "dr6_standard_cause_matches": dr6 & self.CAUSE_MASK == cause}
        if hit:
            checks["dr6_baseline_matches"] = (self.armed_dr6 is not None
                and dr6 & self.CAUSE_MASK == (self.armed_dr6 & self.CAUSE_MASK) | cause)
        self.row["debug_checks"] = {"phase": "hit" if hit else "arm", "matches": checks,
                                    "dr6_compared_mask": self.CAUSE_MASK,
                                    "expected_cause": cause}
        # Keep raw API bytes in inherited _get(); no hardware inference from
        # reserved/BLD/RTM bits. All four addresses and local enables must agree.
        need(all(checks.values()), "console_debug_registers")

    def _arm(self, raw, budget):
        need(self.state == "ready" and self.row["set_state"] == "not_started", "console_rearm")
        self.state, self.slot = "querying", self.transport.pending
        self.selected_kind = 6
        self.row.update(status="arming", load_slot=self.slot)
        self.base = raw.info.load_dll.base
        need(type(self.base) is int and 0x10000 <= self.base <= self.USER_MAX - self.IMAGE_SIZE + 1
             and self.base % 0x10000 == 0, "console_image_range")
        self.targets = tuple(self.base + rva for rva in self.BREAK_RVAS)
        self._identity(budget)
        for rva, size, digest in self.WINDOWS:
            need(hashlib.sha256(self._read(self.base + rva, size, budget)).hexdigest() == digest,
                 "console_code_mismatch")
            self.row["code_windows_confirmed"] += 1
        original = self._get(self.DEBUG_FLAGS, budget)
        self.row["original_debug_hex"] = bytes(self.context[72:120]).hex()
        need(original[:4] == (0, 0, 0, 0) and original[5] in (0, 0x400)
             and original[4] & self.CAUSE_MASK == 0, "console_debug_in_use")
        struct.pack_into("<6Q", self.context, 72, *self.targets, original[4] | 0x10800, original[5] | 0x55)
        struct.pack_into("<I", self.context, 48, self.DEBUG_FLAGS)
        self.row["requested_debug_hex"] = bytes(self.context[72:120]).hex()
        self._budget(budget)
        self.row["set_state"] = "uncertain"
        if not self.kernel.SetThreadContext(self.stop.handles[1], self.context_pointer):
            self.row["set_state"] = "failed"
            raise w._Failure("console_context_set", self.transport.last_error())
        self.row["set_state"] = "query_confirmed"
        self._budget(budget)
        programmed = self._get(self.DEBUG_FLAGS, budget)
        self._programmed(programmed, hit=False)
        self.armed_dr6 = programmed[4]
        self.row["armed_debug_hex"] = bytes(self.context[72:120]).hex()
        self.row.update(status="armed", set_state="verified")
        self.state, self.slot = "armed", None

    def _hit(self, raw, budget):
        self.state, self.slot = "querying", self.transport.pending
        self.selected_kind = 1
        self.row.update(status="hit_uncertain", event_slot=self.slot)
        info = raw.info.exception
        need(info.first_chance == 1 and info.record.code == 0x80000004
             and info.record.flags == 0 and info.record.record is None
             and info.record.parameters == 0 and info.record.address in self.targets,
             "console_exception_mismatch")
        self.hit_index = self.targets.index(info.record.address)
        self.row.update(hit_index=self.hit_index, hit_rva=self.BREAK_RVAS[self.hit_index])
        self._identity(budget)
        registers = self._get(self.HIT_FLAGS, budget)
        self._programmed(registers, hit=True)
        rip = struct.unpack_from("<Q", self.context, 248)[0]
        rsp, rbp = struct.unpack_from("<2Q", self.context, 152)
        need(rip == self.targets[self.hit_index]
             and struct.unpack_from("<I", self.context, 68)[0] & 0x100 == 0,
             "console_callsite_mismatch")
        # All four sites share the checked prologue: push rbp/rsi/rdi,
        # mov rbp,rsp; sub rsp,0x70. Caller return is at rbp+0x18.
        need(0x10000 <= rsp <= self.USER_MAX - 0x90 + 1 and rsp % 16 == 0
             and rbp == rsp + 0x70, "console_frame_range")
        self.caller_slot = rsp + 0x88
        caller = self._read(self.caller_slot, 8, budget)
        self.row["caller_hex"] = caller.hex()
        need(struct.unpack("<Q", caller)[0] == self.base + self.CALLER_RVA,
             "console_caller_mismatch")
        stage = self._read(self.base + self.STAGE_RVA, 2, budget)
        self.row.update(stage_hex=stage.hex(), stage_value=struct.unpack("<H", stage)[0])
        value = struct.unpack_from("<I", self.context, 120)[0]
        self.row.update(status_u32=value, status_negative=bool(value & 0x80000000))
        need(self.row["stage_value"] == 600 and self.row["status_negative"], "console_result_mismatch")
        self._budget(budget)
        self.row.update(status="confirmed", candidate=self.CANDIDATES[self.hit_index],
                        connection_recovery_path_present=self.hit_index == 2, intended_termination=True)
        need(len(json.dumps({"state": "completed", "row": self.row}, ensure_ascii=True))
             <= self.JSON_LIMIT, "console_json_size")
        self.state = "completed"
        raise TransportError("console_failure_observed_stop")
