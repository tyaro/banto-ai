"""Opt-in initial-thread hardware return probe; capture then terminate.

One debug-register SetThreadContext at a verified DLL load, never code writes.
The observed exception is NEVER continued normally or marked handled. Every
terminal path uses the existing owned termination/drain, without rearming.
"""

import ctypes as C
import hashlib
import json
import struct

from banto_ai import _anomaly_v03_windows as w
from tests.fixtures.anomaly_v03_debug_context import DebugContext
from tests.fixtures.anomaly_v03_debug_evidence import _resource
from tests.fixtures.anomaly_v03_debug_transport import TransportError, need


class DebugInitReturn(DebugContext):
    RECIPE = "kernelbase-26200.9445-return-v1"
    BREAK_RVA, STAGE_RVA, IMAGE_SIZE = 0x50BA, 0x3AEEA0, 4202496
    DEBUG_FLAGS, HIT_FLAGS = 0x100010, 0x100013
    CAUSE_MASK = 0xE00F
    WINDOWS = (
        (0x5060, 359, "7c00209c3aa4a3e3ca691c3b49ace93f09e55fa8acd0db498a0402e3b434d79f"),
        (0x4E6C0, 1836, "ff2bf35f46cc2d9a066260b8678a9e0ef6d0bacfb12c4374199e6bb58ae8870c"),
    )

    def __init__(self, images):
        super().__init__(images=images)
        # Reuse the preallocated 2048-byte scratch; no target stack is read.
        self.row = {"status": "not_observed", "recipe": self.RECIPE,
                    "set_state": "not_started", "get_attempts": 0,
                    "read_attempts": 0, "confirmed_bytes": 0, "code_windows_confirmed": 0}
        self.base = self.target = None
        self.armed_dr6 = None
        self.selected_kind = None

    def __repr__(self):
        return "DebugInitReturn(<private registers and stage>)"

    def bind(self, stop, launch):
        super().bind(stop, launch)
        if isinstance(self.kernel, C.CDLL):
            self.kernel.SetThreadContext.restype = w.B
            self.kernel.SetThreadContext.argtypes = (w.H, w.H)

    def _guard(self):
        need(self.state in ("ready", "querying", "armed") and self.stop is not None
             and not self.stop.started and not (self.resource_stop or self.stop.resource_stop
                 or self.stop.drain.resource_stop or self.transport.resource_stop), "return_stopped")
        t, launch = self.transport, self.launch
        need(t.state == "pending" and not t.wait_inflight and not t.continue_inflight
             and type(t.pending) is int and 0 <= t.pending < t.count, "return_pending")
        need(self.slot is None or self.slot == t.pending, "return_event_changed")
        need(launch.creation_state == "created" and launch.transferred
             and t.pid == launch.process.pid
             and self.stop.handles == [launch.process.process, launch.process.thread]
             and all(type(h) is int and 0 < h < w.H(-1).value for h in self.stop.handles),
             "return_owner")
        raw = t.buffers[t.pending]
        need(raw.pid == t.pid and raw.tid != 0, "return_event_identity")
        if self.slot is not None:
            need(raw.tid == launch.process.tid and raw.kind == self.selected_kind, "return_initial_thread")
        t._thread()

    def _identity(self, budget):
        for function, handle, expected in (
                (self.kernel.GetProcessId, self.stop.handles[0], self.transport.pid),
                (self.kernel.GetThreadId, self.stop.handles[1], self.launch.process.tid),
                (self.kernel.GetProcessIdOfThread, self.stop.handles[1], self.transport.pid)):
            self._budget(budget)
            value = function(handle)
            if value == 0:
                raise w._Failure("return_handle_query", self.transport.last_error())
            need(type(value) is int and value == expected, "return_handle_identity")
            self._budget(budget)

    def _get(self, flags, budget):
        self._budget(budget)
        need(self.row["get_attempts"] < 3, "return_get_limit")
        C.memset(self.context_pointer, 0, self.CONTEXT_SIZE)
        struct.pack_into("<I", self.context, 48, flags)
        self.row["get_attempts"] += 1
        self.row["get_state"] = "uncertain"
        if not self.kernel.GetThreadContext(self.stop.handles[1], self.context_pointer):
            self.row["get_state"] = "failed"
            raise w._Failure("return_context_query", self.transport.last_error())
        self.row["get_state"] = "query_confirmed"
        self._budget(budget)
        need(struct.unpack_from("<I", self.context, 48)[0] & flags == flags, "return_context_flags")
        self.row["get_state"] = "confirmed"
        return struct.unpack_from("<6Q", self.context, 72)

    def _read(self, address, size, budget):
        need(type(address) is int and self.base <= address
             and address + size <= self.base + self.IMAGE_SIZE and 0 < size <= self.STACK_SIZE,
             "return_read_range")
        self._budget(budget)
        need(self.row["read_attempts"] < 3, "return_read_limit")
        self.row["read_attempts"] += 1
        self.row["read_state"] = "uncertain"
        self.bytes_read.value = 0
        ok = self.kernel.ReadProcessMemory(self.stop.handles[0], w.H(address), self.stack_pointer,
                                          size, self.bytes_read_pointer)
        self.row["last_read_bytes"] = self.bytes_read.value
        if not ok:
            self.row["read_state"] = "failed"
            raise w._Failure("return_memory_read", self.transport.last_error())
        self._budget(budget)
        need(self.bytes_read.value == size, "return_read_length")
        self.row["read_state"] = "confirmed"
        self.row["confirmed_bytes"] += size
        return self.stack.raw[:size]

    def _programmed(self, registers, *, hit):
        dr0, dr1, dr2, dr3, dr6, dr7 = registers
        # Bit 10 of DR7 may be normalized by the OS; all other bits are exact.
        need(dr0 == self.target and (dr1, dr2, dr3) == (0, 0, 0) and dr6 & 0x10800 == 0x10800
             and dr7 & ~0x400 == 1 and dr6 & self.CAUSE_MASK == (1 if hit else 0),
             "return_debug_registers")
        if hit:
            need(self.armed_dr6 is not None and dr6 == self.armed_dr6 | 1,
                 "return_debug_cause_changed")

    def _arm(self, raw, budget):
        need(self.state == "ready" and self.row["set_state"] == "not_started", "return_rearm")
        self.state, self.slot = "querying", self.transport.pending
        self.selected_kind = 6
        self.row.update(status="arming", load_slot=self.slot)
        self.base = raw.info.load_dll.base
        need(type(self.base) is int and 0x10000 <= self.base <= self.USER_MAX - self.IMAGE_SIZE + 1
             and self.base % 0x10000 == 0, "return_image_range")
        self.target = self.base + self.BREAK_RVA
        self._identity(budget)
        for rva, size, digest in self.WINDOWS:
            need(hashlib.sha256(self._read(self.base + rva, size, budget)).hexdigest() == digest,
                 "return_code_mismatch")
            self.row["code_windows_confirmed"] += 1
        original = self._get(self.DEBUG_FLAGS, budget)
        self.row["original_debug_hex"] = bytes(self.context[72:120]).hex()
        need(original[:4] == (0, 0, 0, 0) and original[5] in (0, 0x400)
             and original[4] & self.CAUSE_MASK == 0, "return_debug_in_use")
        struct.pack_into("<Q", self.context, 72, self.target)
        # BLD and RTM are active-low causes; establish their inactive baseline.
        struct.pack_into("<Q", self.context, 104, original[4] | 0x10800)
        struct.pack_into("<Q", self.context, 112, original[5] | 1)
        # Only the DEBUG_REGISTERS group is written. RIP/EFLAGS/GPRs stay untouched.
        struct.pack_into("<I", self.context, 48, self.DEBUG_FLAGS)
        self._budget(budget)
        self.row["set_state"] = "uncertain"
        if not self.kernel.SetThreadContext(self.stop.handles[1], self.context_pointer):
            self.row["set_state"] = "failed"
            raise w._Failure("return_context_set", self.transport.last_error())
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
             and info.record.parameters == 0 and info.record.address == self.target,
             "return_exception_mismatch")
        self._identity(budget)
        registers = self._get(self.HIT_FLAGS, budget)
        self.row["context_hex"] = bytes(self.context).hex()
        self._programmed(registers, hit=True)
        need(struct.unpack_from("<Q", self.context, 248)[0] == self.target
             and struct.unpack_from("<I", self.context, 144)[0] == 1
             and struct.unpack_from("<I", self.context, 68)[0] & 0x100 == 0,
             "return_callsite_mismatch")
        stage = struct.unpack("<H", self._read(self.base + self.STAGE_RVA, 2, budget))[0]
        result = struct.unpack_from("<Q", self.context, 120)[0] & 255
        self._budget(budget)
        self.row.update(status="confirmed", return_byte=result, returns_false=result == 0,
                        stage_value=stage, intended_termination=True)
        need(len(json.dumps({"state": "completed", "row": self.row}, ensure_ascii=True))
             <= self.JSON_LIMIT, "return_json_size")
        self.state = "completed"
        # Deliberate terminal observation. No normal Continue after this point.
        raise TransportError("init_return_observed_stop")

    def capture(self, budget):
        try:
            self._guard()
            raw = self.transport.buffers[self.transport.pending]
            if raw.kind == 6:
                need(self.images is not None and self.images.state == "ready"
                     and not self.images.resource_stop, "return_images")
                rows = [r for r in self.images.rows if r is not None
                        and r.get("event_slot") == self.transport.pending and r.get("status") == "confirmed"]
                need(len(rows) == 1, "return_image_unconfirmed")
                if rows[0].get("name", "").casefold().endswith("\\kernelbase.dll"):
                    self._arm(raw, budget)
            elif self.state == "armed":
                # The first exception consumes the observation, even if unrelated.
                if raw.kind == 1:
                    self._hit(raw, budget)
                elif raw.kind in (2, 4, 5, 7, 9):
                    raise TransportError("return_not_observed")
            elif raw.kind == 5:
                raise TransportError("return_module_not_observed")
        except BaseException as error:
            if self.primary is None:
                self.primary = error
            else:
                self.secondary = error
            self.resource_stop |= _resource(error)
            if self.stop is not None:
                self.resource_stop |= (self.stop.resource_stop or self.stop.drain.resource_stop
                                       or self.transport.resource_stop)
                self.transport.resource_stop |= self.resource_stop
            if self.state != "completed":
                self.state = "stopped"
            raise
