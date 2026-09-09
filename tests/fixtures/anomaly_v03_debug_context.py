"""One read-only initial-thread snapshot during the first normal DLL unload.

Borrowed launch handles only. No suspend/resume, open/close, write, unwind,
symbol lookup or retry. Partial buffers remain private and never become a stack.
"""

import ctypes as C
import json
import struct

from banto_ai import _anomaly_v03_windows as w
from tests.fixtures.anomaly_v03_debug_evidence import _resource
from tests.fixtures.anomaly_v03_debug_transport import need


class DebugContext:
    CONTEXT_SIZE = 1232
    FLAGS_OFFSET, RSP_OFFSET, RIP_OFFSET = 48, 152, 248
    FLAGS = 0x00100003
    STACK_SIZE = 2048
    JSON_LIMIT = 8 * 1024
    USER_MAX = 0x00007FFFFFFFFFFF

    def __init__(self):
        need(C.sizeof(w.H) == 8, "context_abi")
        self.storage = C.create_string_buffer(self.CONTEXT_SIZE + 15)
        base = C.addressof(self.storage)
        address = (base + 15) & ~15
        self.context = (C.c_ubyte * self.CONTEXT_SIZE).from_buffer(self.storage, address - base)
        self.context_pointer = w.H(address)
        need(address % 16 == 0 and address + self.CONTEXT_SIZE <= base + C.sizeof(self.storage),
             "context_alignment")
        struct.pack_into("<I", self.context, self.FLAGS_OFFSET, self.FLAGS)
        self.stack = C.create_string_buffer(self.STACK_SIZE)
        self.stack_pointer = C.cast(self.stack, w.H)
        self.bytes_read = C.c_size_t()
        self.bytes_read_pointer = C.pointer(self.bytes_read)
        self.stop = self.launch = self.transport = self.kernel = None
        self.state = "ready"
        self.resource_stop = False
        self.primary = self.secondary = None
        self.row = {"status": "not_observed", "context_state": "not_started",
                    "stack_state": "not_started", "identity_state": "not_started"}
        self.slot = None

    def __repr__(self):
        return "DebugContext(<private context and stack>)"

    def bind(self, stop, launch):
        need(self.stop is None and self.state == "ready" and not stop.started
             and not launch.started and launch.stop is stop, "context_bind")
        self.stop, self.launch, self.transport = stop, launch, stop.transport
        self.kernel = self.transport.kernel
        if isinstance(self.kernel, C.CDLL):
            for name, result, args in (
                    ("GetThreadContext", w.B, (w.H, w.H)),
                    ("GetThreadId", w.D, (w.H,)),
                    ("GetProcessIdOfThread", w.D, (w.H,)),
                    ("ReadProcessMemory", w.B,
                     (w.H, w.H, w.H, C.c_size_t, C.POINTER(C.c_size_t)))):
                function = getattr(self.kernel, name)
                function.restype, function.argtypes = result, args

    def _guard(self):
        need(self.state in ("ready", "querying") and self.stop is not None
             and not self.stop.started and not (self.resource_stop or self.stop.resource_stop
                 or self.stop.drain.resource_stop or self.transport.resource_stop), "context_stopped")
        t, launch = self.transport, self.launch
        need(t.state == "pending" and not t.wait_inflight and not t.continue_inflight
             and type(t.pending) is int and 0 <= t.pending < t.count, "context_pending")
        need(self.slot is None or t.pending == self.slot, "context_event_changed")
        need(launch.creation_state == "created" and launch.transferred
             and t.pid == launch.process.pid
             and self.stop.handles == [launch.process.process, launch.process.thread]
             and all(type(h) is int and 0 < h < w.H(-1).value for h in self.stop.handles),
             "context_owner")
        raw = t.buffers[t.pending]
        need(raw.pid == t.pid and raw.tid != 0, "context_event_identity")
        if self.slot is not None:
            need(raw.kind == 7 and raw.tid == launch.process.tid, "context_selected_event")
        t._thread()

    def _budget(self, budget):
        self._guard()
        budget()
        self._guard()

    def capture(self, budget):
        # A completed selection is never shifted to a later unload event.
        if self.state == "completed":
            return
        try:
            self._guard()
            raw = self.transport.buffers[self.transport.pending]
            if raw.kind != 7:
                return
            self.row.update(event_slot=self.transport.pending, event_tid=raw.tid)
            if raw.tid != self.launch.process.tid:
                self.row["status"] = "not_initial_thread"
                self.state = "completed"
                return
            self.slot = self.transport.pending
            self.state = "querying"
            self.row["status"] = "querying"
            for label, function, handle, expected in (
                    ("process", self.kernel.GetProcessId, self.stop.handles[0], raw.pid),
                    ("thread", self.kernel.GetThreadId, self.stop.handles[1], raw.tid),
                    ("thread_process", self.kernel.GetProcessIdOfThread, self.stop.handles[1], raw.pid)):
                self._budget(budget)
                self.row["identity_state"] = label + "_uncertain"
                value = function(handle)
                if value == 0:
                    self.row["identity_state"] = label + "_failed"
                    raise w._Failure("context_handle_query", self.transport.last_error())
                need(type(value) is int and value == expected, "context_handle_identity")
                self.row["identity_state"] = label + "_confirmed"
                self._budget(budget)
            self._budget(budget)
            self.row["context_state"] = "uncertain"
            if not self.kernel.GetThreadContext(self.stop.handles[1], self.context_pointer):
                self.row["context_state"] = "failed"
                raise w._Failure("context_query", self.transport.last_error())
            self.row["context_state"] = "query_confirmed"
            self._budget(budget)
            flags = struct.unpack_from("<I", self.context, self.FLAGS_OFFSET)[0]
            need(flags & self.FLAGS == self.FLAGS, "context_flags")
            rsp = struct.unpack_from("<Q", self.context, self.RSP_OFFSET)[0]
            rip = struct.unpack_from("<Q", self.context, self.RIP_OFFSET)[0]
            need(0 < rip <= self.USER_MAX and 0 < rsp <= self.USER_MAX - self.STACK_SIZE + 1,
                 "context_address_range")
            self.row.update(context_state="confirmed", context_hex=bytes(self.context).hex(),
                            rip=rip, rsp=rsp, requested_stack_bytes=self.STACK_SIZE)
            self._budget(budget)
            self.row["stack_state"] = "uncertain"
            ok = self.kernel.ReadProcessMemory(self.stop.handles[0], w.H(rsp), self.stack_pointer,
                                               self.STACK_SIZE, self.bytes_read_pointer)
            self.row["bytes_read"] = self.bytes_read.value
            if not ok:
                self.row["stack_state"] = "failed"
                raise w._Failure("context_stack_read", self.transport.last_error())
            self.row["stack_state"] = "query_confirmed"
            self._budget(budget)
            need(self.bytes_read.value == self.STACK_SIZE, "context_stack_length")
            self.row.update(stack_state="confirmed", stack_hex=self.stack.raw.hex(), status="confirmed")
            need(len(json.dumps({"state": "completed", "row": self.row}, ensure_ascii=True))
                 <= self.JSON_LIMIT, "context_json_size")
            self._budget(budget)
            self.state = "completed"
        except BaseException as error:
            if self.primary is None:
                self.primary = error
            else:
                self.secondary = error
            self.resource_stop |= _resource(error)
            if self.stop is not None:
                self.resource_stop |= (self.stop.resource_stop or self.stop.drain.resource_stop
                                       or self.transport.resource_stop)
            if self.transport is not None:
                self.transport.resource_stop |= self.resource_stop
            self.state = "stopped"
            raise
