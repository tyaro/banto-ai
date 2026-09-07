"""Dormant x64 Win32 debug-event transport; no launch/attach entry point.

Construction allocates all event buffers before a future caller creates a child.
The caller owns launch handles and termination/draining; event process/thread
handles remain OS-managed. Native execution is not enabled by this fixture.
"""

import ctypes as C
import os

from tests.fixtures.anomaly_v03_startup_events import StartupEvent

D, H, Z = C.c_uint32, C.c_void_p, C.c_size_t
DBG_CONTINUE, DBG_NOT_HANDLED = 0x10002, 0x80010001
BREAKPOINT = 0x80000003


class ExceptionRecord(C.Structure):
    _fields_ = [("code", D), ("flags", D), ("record", H), ("address", H),
                ("parameters", D), ("information", Z * 15)]


class ExceptionInfo(C.Structure):
    _fields_ = [("record", ExceptionRecord), ("first_chance", D)]


class CreateProcessInfo(C.Structure):
    _fields_ = [("file", H), ("process", H), ("thread", H), ("base", H),
                ("debug_offset", D), ("debug_size", D), ("tls", H), ("start", H),
                ("image_name", H), ("unicode", C.c_uint16)]


class CreateThreadInfo(C.Structure):
    _fields_ = [("thread", H), ("tls", H), ("start", H)]


class LoadDllInfo(C.Structure):
    _fields_ = [("file", H), ("base", H), ("debug_offset", D), ("debug_size", D),
                ("image_name", H), ("unicode", C.c_uint16)]


class DebugStringInfo(C.Structure):
    _fields_ = [("data", H), ("unicode", C.c_uint16), ("length", C.c_uint16)]


class RipInfo(C.Structure):
    _fields_ = [("error", D), ("kind", D)]


class EventUnion(C.Union):
    _fields_ = [("exception", ExceptionInfo), ("create_process", CreateProcessInfo),
                ("create_thread", CreateThreadInfo), ("exit_code", D), ("load_dll", LoadDllInfo),
                ("unload_base", H), ("debug_string", DebugStringInfo), ("rip", RipInfo)]


class DebugEvent(C.Structure):
    _fields_ = [("kind", D), ("pid", D), ("tid", D), ("info", EventUnion)]

    def __repr__(self):
        return "DebugEvent(<private native buffer>)"


class TransportError(RuntimeError):
    def __init__(self, reason, winerror=0):
        self.reason, self.winerror = reason, winerror

    def __str__(self):
        return "startup_transport_failed"


def need(ok, reason):
    if not ok:
        raise TransportError(reason)


class DebugEventTransport:
    LIMIT = 256
    NAMES = (None, "exception", "create_thread", "create_process", "exit_thread",
             "exit_process", "load_dll", "unload_dll", "debug_string", "rip")

    def __init__(self, *, kernel=None, last_error=None):
        need(C.sizeof(H) == 8 and C.sizeof(DebugEvent) == 176, "abi")
        if kernel is None:
            need(os.name == "nt", "platform")
            kernel = C.WinDLL("kernel32", use_last_error=True)
            for name, result, args in (
                    ("WaitForDebugEventEx", C.c_int32, (C.POINTER(DebugEvent), D)),
                    ("ContinueDebugEvent", C.c_int32, (D, D, D)),
                    ("CloseHandle", C.c_int32, (H,)),
                    ("GetCurrentThreadId", D, ())):
                function = getattr(kernel, name)
                function.restype, function.argtypes = result, args
        self.kernel = kernel
        self.last_error = last_error if last_error is not None else C.get_last_error
        self.creator_thread = kernel.GetCurrentThreadId()
        self.buffers = tuple(DebugEvent() for _ in range(self.LIMIT))
        self.pointers = tuple(C.pointer(event) for event in self.buffers)
        self.file_closed = [False] * self.LIMIT
        self.file_close_state = ["not_started"] * self.LIMIT
        self.file_close_attempts = [0] * self.LIMIT
        self.count = 0
        self.pending = None
        self.state = "idle"
        self.resource_stop = False
        self.pid = None

    def __repr__(self):
        return "DebugEventTransport(<private evidence and ownership>)"

    def bind(self, pid):
        self._thread()
        need(self.pid is None and self.count == 0 and self.state == "idle", "already_bound")
        need(type(pid) is int and 0 < pid < 2**32, "pid")
        self.pid = pid

    def _thread(self):
        try:
            need(self.kernel.GetCurrentThreadId() == self.creator_thread, "creator_thread")
        except BaseException as error:
            self.resource_stop |= isinstance(error, MemoryError)
            self.state = "stopped"
            raise

    def wait(self, timeout_ms=100):
        self._thread()
        need(self.pid is not None and self.state == "idle" and not self.resource_stop, "wait_state")
        need(type(timeout_ms) is int and 0 <= timeout_ms <= 100, "wait_timeout")
        need(self.count < self.LIMIT, "event_limit")
        # Retain the exact buffer before the OS can deliver any owned handles.
        self.pending = self.count
        self.state = "waiting"
        try:
            ok = self.kernel.WaitForDebugEventEx(self.pointers[self.count], timeout_ms)
            if not ok:
                code = self.last_error()
                if code == 121:  # ERROR_SEM_TIMEOUT; no event was delivered.
                    self.pending, self.state = None, "idle"
                    return False
                self.state = "wait_failed"
                raise TransportError("debug_wait", code)
            self.count += 1
            self.state = "pending"
            return True
        except BaseException as error:
            self.resource_stop |= isinstance(error, MemoryError)
            if self.state == "waiting":
                self.state = "wait_uncertain"
            raise

    def event(self):
        try:
            return self._decode_event()
        except BaseException as error:
            self.resource_stop |= isinstance(error, MemoryError)
            self.state = "stopped"
            raise

    def _decode_event(self):
        self._thread()
        need(self.state == "pending", "event_state")
        raw = self.buffers[self.pending]
        need(raw.pid == self.pid and raw.tid != 0, "event_identity")
        need(1 <= raw.kind <= 9, "event_kind")
        code, chance = 0, False
        if raw.kind == 1:
            need(raw.info.exception.first_chance in (0, 1), "first_chance")
            need(raw.info.exception.record.parameters <= 15, "exception_parameters")
            code, chance = raw.info.exception.record.code, bool(raw.info.exception.first_chance)
        elif raw.kind in (4, 5):
            code = raw.info.exit_code
        elif raw.kind == 9:
            code = raw.info.rip.error
        return StartupEvent(self.NAMES[raw.kind], raw.pid, raw.tid, code, chance)

    def close_file(self, index):
        try:
            return self._close_file(index)
        except BaseException as error:
            self.resource_stop |= isinstance(error, MemoryError)
            self.state = "stopped"
            raise

    def _close_file(self, index):
        self._thread()
        need(type(index) is int and 0 <= index < self.count, "close_index")
        if self.file_closed[index]:
            return
        raw = self.buffers[index]
        handle = raw.info.create_process.file if raw.kind == 3 else raw.info.load_dll.file if raw.kind == 6 else None
        if handle is None:
            self.file_closed[index] = True
            return
        need(handle != C.c_void_p(-1).value, "invalid_event_file")
        need(self.file_close_state[index] in ("not_started", "failed"), "close_result_uncertain")
        need(self.file_close_attempts[index] < 2, "close_retry_limit")
        self.file_close_attempts[index] += 1
        # Publish uncertainty before the API: interruption after it succeeds
        # must never cause a second CloseHandle on a potentially reused value.
        self.file_close_state[index] = "uncertain"
        if not self.kernel.CloseHandle(handle):
            self.file_close_state[index] = "failed"
            raise TransportError("event_file_close", self.last_error())
        self.file_closed[index] = True
        self.file_close_state[index] = "closed"

    def continue_event(self):
        self._thread()
        need(self.state == "pending" and not self.resource_stop, "continue_state")
        event = self.event()
        # Bootstrap identity is not implemented: stop rather than swallow an
        # arbitrary breakpoint or deliver the OS bootstrap breakpoint unhandled.
        need(not (event.kind == "exception" and event.code == BREAKPOINT), "bootstrap_unverified")
        need(self.file_closed[self.pending], "event_file_not_closed")
        status = DBG_NOT_HANDLED if event.kind == "exception" else DBG_CONTINUE
        self.state = "continue_attempted"
        try:
            if not self.kernel.ContinueDebugEvent(event.pid, event.tid, status):
                raise TransportError("debug_continue", self.last_error())
            self.pending = None
            self.state = "exit_continued" if event.kind == "exit_process" else "idle"
        except BaseException as error:
            self.resource_stop |= isinstance(error, MemoryError)
            self.state = "continue_uncertain"
            raise

    def stop(self, *, resource=False):
        self._thread()
        need(type(resource) is bool, "resource_type")
        self.resource_stop |= resource
        self.state = "stopped"

    def close_retained_files(self):
        """Bounded handle-only retry. Caller retains this object on any failure."""
        self._thread()
        first = None
        for index in range(self.count):
            try:
                self.close_file(index)
            except BaseException as error:
                self.resource_stop |= isinstance(error, MemoryError)
                if first is None:
                    first = error
        if first is not None:
            raise first
