"""Opt-in verification of one fixed loader breakpoint, using borrowed handles.

This is a build-specific diagnostic consistency check, not bootstrap provenance.
No context/memory writes, new breakpoints, handle opens or retries.
"""
import ctypes as C
import hashlib
import json
import struct

from banto_ai import _anomaly_v03_windows as w
from tests.fixtures.anomaly_v03_debug_transport import BREAKPOINT, need
from tests.fixtures.anomaly_v03_debug_evidence import _resource
from tests.fixtures.anomaly_v03_debug_unload_entry import DebugUnloadEntry


class DebugBootstrap:
    RECIPE = "ntdll-26200.9445-bootstrap-v1"
    IMAGE_SIZE = 2519040
    CODE_RVA, CODE_SIZE = 0x122204, 62
    CODE_SHA256 = "cc1cef07481f3ac8e2dc416ffe823e0fd00b0c493355ade7e14aa31067bfa009"
    BREAK_RVA = 0x122239
    CALLERS = (0x8C2E0, 0x8DBE1, 0x8DF44)
    FLAGS, CONTEXT_SIZE, JSON_LIMIT = 0x100003, 1232, 4096
    USER_MAX = 0x00007FFFFFFFFFFF

    def __init__(self, images):
        need(C.sizeof(w.H) == 8, "bootstrap_abi")
        self.storage = C.create_string_buffer(self.CONTEXT_SIZE + 15)
        base = C.addressof(self.storage)
        address = (base + 15) & ~15
        self.context = (C.c_ubyte * self.CONTEXT_SIZE).from_buffer(self.storage, address-base)
        self.context_pointer = w.H(address)
        self.scratch = C.create_string_buffer(self.CODE_SIZE)
        self.pointer = C.cast(self.scratch, w.H)
        self.bytes_read = C.c_size_t()
        self.length_pointer = C.pointer(self.bytes_read)
        self.images = images
        self.stop = self.launch = self.transport = self.kernel = None
        self.slot = self.selected_raw = self.image_base = self.image_row = None
        self.state, self.resource_stop = "ready", False
        self.row = {"status": "not_observed", "recipe": self.RECIPE,
                    "get_attempts": 0, "read_attempts": 0, "confirmed_bytes": 0,
                    "continue_state": "not_started"}
        self.primary = None

    def __repr__(self):
        return "DebugBootstrap(<private context and caller>)"

    def bind(self, stop, launch):
        need(self.stop is None and not stop.started and not launch.started and launch.stop is stop,
             "bootstrap_bind")
        self.stop, self.launch, self.transport = stop, launch, stop.transport
        self.kernel = self.transport.kernel
        if isinstance(self.kernel, C.CDLL):
            for name, result, args in (
                    ("GetThreadContext", w.B, (w.H, w.H)),
                    ("GetThreadId", w.D, (w.H,)),
                    ("GetProcessIdOfThread", w.D, (w.H,)),
                    ("ReadProcessMemory", w.B, (w.H, w.H, w.H, C.c_size_t, C.POINTER(C.c_size_t)))):
                function = getattr(self.kernel, name)
                function.restype, function.argtypes = result, args

    @classmethod
    def _address(cls, address, size, alignment=1):
        need(type(address) is int and 0x10000 <= address <= cls.USER_MAX-size+1
             and address % alignment == 0, "bootstrap_address")

    def _guard(self):
        t, launch = self.transport, self.launch
        need(self.state in ("ready", "querying", "verified", "consumed", "continued")
             and self.stop is not None and not self.stop.started
             and not (self.resource_stop or self.stop.resource_stop or self.stop.drain.resource_stop
                      or t.resource_stop or self.images.resource_stop), "bootstrap_stopped")
        need(t.state == "pending" and not t.wait_inflight and not t.continue_inflight
             and type(t.pending) is int and 0 <= t.pending < t.count <= t.LIMIT, "bootstrap_pending")
        need(launch.creation_state == "created" and launch.transferred
             and t.pid == launch.process.pid
             and self.stop.handles == [launch.process.process, launch.process.thread]
             and all(type(h) is int and 0 < h < w.H(-1).value for h in self.stop.handles),
             "bootstrap_owner")
        t._thread()
        if self.slot is not None and self.state != "continued":
            need(t.pending == self.slot and bytes(t.buffers[self.slot]) == self.selected_raw,
                 "bootstrap_event_changed")
        if self.image_row is not None and self.state != "continued":
            need(DebugUnloadEntry._active_image(self, self.images, self.image_base) is self.image_row,
                 "bootstrap_image_changed")

    def _budget(self, budget):
        self._guard()
        budget()
        self._guard()

    def _read(self, budget, address, size, label):
        self._address(address, size)
        need(0 < size <= self.CODE_SIZE and self.row["read_attempts"] < 3, "bootstrap_read_limit")
        self._budget(budget)
        self.row["read_attempts"] += 1
        self.row["read_state"] = label + "_uncertain"
        self.bytes_read.value = 0
        ok = self.kernel.ReadProcessMemory(self.stop.handles[0], w.H(address),
                                          self.pointer, size, self.length_pointer)
        self.row["last_read_bytes"] = self.bytes_read.value
        self.row[label+"_hex"] = self.scratch.raw[:min(size, self.bytes_read.value)].hex()
        if not ok:
            raise w._Failure("bootstrap_memory_read", self.transport.last_error())
        self._budget(budget)
        need(self.bytes_read.value == size, "bootstrap_read_length")
        self.row["confirmed_bytes"] += size
        self.row["read_state"] = label + "_confirmed"
        return self.scratch.raw[:size]

    def capture(self, budget):
        try:
            self._guard()
            t = self.transport
            raw = t.buffers[t.pending]
            if raw.kind != 1:
                return
            if self.state == "continued":
                need(raw.info.exception.record.code != BREAKPOINT, "bootstrap_retry")
                return
            need(self.state == "ready", "bootstrap_retry")
            # Consume selection before validation; no later exception can replace it.
            self.state, self.slot = "querying", t.pending
            self.selected_raw = bytes(raw)
            self.row.update(status="querying", event_slot=self.slot)
            info = raw.info.exception
            need(raw.pid == t.pid and raw.tid == self.launch.process.tid
                 and info.first_chance == 1 and info.record.code == BREAKPOINT
                 and info.record.flags == 0 and info.record.record is None
                 and info.record.parameters == 1 and info.record.information[0] == 0,
                 "bootstrap_exception")
            need(self.slot > 0 and t.buffers[0].kind == 3
                 and t.buffers[0].pid == raw.pid and t.buffers[0].tid == raw.tid
                 and all(event.kind != 1 for event in t.buffers[:self.slot]),
                 "bootstrap_first_exception")
            need(self.images.state == "ready", "bootstrap_images")
            candidates = [r for r in self.images.rows if r is not None and r.get("status") == "confirmed"
                          and r.get("name", "").casefold().endswith("\\ntdll.dll")]
            need(len(candidates) == 1, "bootstrap_ntdll_unique")
            image = candidates[0]
            load_slot = image.get("event_slot")
            need(type(load_slot) is int and 0 < load_slot < self.slot
                 and t.buffers[load_slot].kind == 6, "bootstrap_ntdll_event")
            self.image_base = t.buffers[load_slot].info.load_dll.base
            self._address(self.image_base, self.IMAGE_SIZE, 0x10000)
            need(DebugUnloadEntry._active_image(self, self.images, self.image_base) is image,
                 "bootstrap_ntdll_lifetime")
            self.image_row = image
            self.row["load_slot"] = load_slot
            need(info.record.address == self.image_base+self.BREAK_RVA, "bootstrap_break_address")
            for function, handle, expected in (
                    (self.kernel.GetProcessId, self.stop.handles[0], raw.pid),
                    (self.kernel.GetThreadId, self.stop.handles[1], raw.tid),
                    (self.kernel.GetProcessIdOfThread, self.stop.handles[1], raw.pid)):
                self._budget(budget)
                need(function(handle) == expected, "bootstrap_handle_identity")
                self._budget(budget)
            code = self._read(budget, self.image_base+self.CODE_RVA, self.CODE_SIZE, "code")
            need(hashlib.sha256(code).hexdigest() == self.CODE_SHA256, "bootstrap_code_mismatch")
            self._budget(budget)
            struct.pack_into("<I", self.context, 48, self.FLAGS)
            self.row.update(get_attempts=1, get_state="uncertain")
            if not self.kernel.GetThreadContext(self.stop.handles[1], self.context_pointer):
                raise w._Failure("bootstrap_context_query", t.last_error())
            self.row.update(get_state="captured", context_hex=bytes(self.context).hex())
            self._budget(budget)
            need(struct.unpack_from("<I", self.context, 48)[0] & self.FLAGS == self.FLAGS,
                 "bootstrap_context_flags")
            rsp = struct.unpack_from("<Q", self.context, 152)[0]
            rip = struct.unpack_from("<Q", self.context, 248)[0]
            need(rip == self.image_base+self.BREAK_RVA+1
                 and struct.unpack_from("<I", self.context, 68)[0] & 0x100 == 0,
                 "bootstrap_context_position")
            self._address(rsp, 0x40, 16)
            caller = struct.unpack("<Q", self._read(budget, rsp+0x38, 8, "caller"))[0]
            need(caller-self.image_base in self.CALLERS, "bootstrap_caller")
            self.row["caller_rva"] = caller-self.image_base
            call = self._read(budget, caller-5, 5, "call")
            need(call[0] == 0xE8 and caller+struct.unpack_from("<i", call, 1)[0]
                 == self.image_base+self.CODE_RVA, "bootstrap_call_mismatch")
            self.row["status"] = "verified"
            need(len(json.dumps({"state": "continued", "row": self.row}, ensure_ascii=True))
                 <= self.JSON_LIMIT, "bootstrap_json_size")
            self._budget(budget)
            self.state = "verified"
        except BaseException as error:
            self.primary = error
            self.resource_stop |= _resource(error)
            if self.transport is not None:
                self.transport.resource_stop |= self.resource_stop
            self.state = "stopped"
            raise

    def consume(self, transport):
        need(transport is self.transport and self.state == "verified", "bootstrap_unverified")
        self._guard()
        need(transport.file_closed[self.slot], "event_file_not_closed")
        self.state = "consumed"
        self.row["continue_state"] = "uncertain"

    def continued(self):
        need(self.state == "consumed", "bootstrap_continue_state")
        self.row["continue_state"] = "confirmed"
        self.state = "continued"
