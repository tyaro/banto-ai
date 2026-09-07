"""Dormant owned-child termination/drain controller; no launcher or attachment.

Allocate before child creation, then give it only the launcher's OWNED handles.
The launcher must retain the returned object, including uncertain ownership.
No fixture cleanup, filesystem read, remote memory read or acceptance occurs.
"""

import ctypes as C
import time

from tests.fixtures.anomaly_v03_debug_transport import (
    DebugEventTransport, TransportError, D, H, DBG_CONTINUE, DBG_NOT_HANDLED, need,
)


class StopResult(dict):
    def __init__(self, owner):
        super().__init__(status="not_started", native_accepted=False, formal_permission=False,
                         process_signaled=False, terminate_state="not_started", exit_continued=False,
                         failure_count=0, resource_stop=False, drain_waits=0, teardown_status="not_started",
                         debug_ownership_resolved=False)
        self.private_owner = owner


class OwnedDebugStop:
    """Single attempt, at most 32 drain waits/events of at most 100 ms each.

    A failed/uncertain Continue is never retried. Termination request, exit
    continuation, and signaled confirmation are independent observations.
    """
    LIMIT = 32

    def __init__(self, transport, *, clock=time.monotonic):
        self.transport, self.kernel, self.clock = transport, transport.kernel, clock
        self.drain = DebugEventTransport(kernel=self.kernel, last_error=transport.last_error)
        # Configure only native ctypes exports; fake kernels do not load DLLs.
        if isinstance(self.kernel, C.CDLL):
            for name, result, args in (
                    ("TerminateProcess", C.c_int32, (H, D)),
                    ("WaitForSingleObject", D, (H, D)),
                    ("GetProcessId", D, (H,))):
                function = getattr(self.kernel, name)
                function.restype, function.argtypes = result, args
        self.handles = [None, None]
        self.close_state = ["not_started", "not_started"]
        self.errors = [None] * 8
        self.error_count = 0
        self.primary = None
        self.resource_stop = False
        self.started = False
        self.terminate_state = "not_started"
        self.exit_continued = False
        self.signaled = False
        self.waits = 0
        self.result = StopResult(self)

    def __repr__(self):
        return "OwnedDebugStop(<private ownership and evidence>)"

    def adopt(self, process, thread):
        need(not self.started and all(handle is None for handle in self.handles), "already_owned")
        # Record ownership before any validation that can fail.
        self.handles[0], self.handles[1] = process, thread
        need(type(process) is int and process > 0 and type(thread) is int and thread > 0
             and process != thread, "owned_handles")
        need(self.kernel.GetProcessId(process) == self.transport.pid, "owned_process_identity")
        self.drain.bind(self.transport.pid)

    def _record(self, reason, error):
        if self.error_count < len(self.errors):
            self.errors[self.error_count] = reason
        self.error_count = min(self.error_count + 1, 65535)
        self.resource_stop |= isinstance(error, MemoryError)
        if self.primary is None:
            self.primary = error

    def _release_pending(self, source):
        need(not source.wait_inflight and not source.continue_inflight, "pending_outcome_uncertain")
        index = source.pending
        need(index is not None and index < source.count, "pending_delivery_unconfirmed")
        raw = source.buffers[index]
        need(raw.pid == self.transport.pid and raw.tid != 0 and 1 <= raw.kind <= 9, "drain_identity")
        try:
            source.close_file(index)
        except BaseException as error:
            self._record("event_file_close", error)
        # After confirmed TerminateProcess, this only releases debug suspension.
        # Never mark any target exception handled, including a breakpoint.
        status = DBG_NOT_HANDLED if raw.kind == 1 else DBG_CONTINUE
        source.continue_inflight = True
        source.state = "continue_attempted"
        if not self.kernel.ContinueDebugEvent(raw.pid, raw.tid, status):
            raise TransportError("drain_continue", self.transport.last_error())
        source.pending = None
        source.state = "exit_continued" if raw.kind == 5 else "idle"
        source.continue_inflight = False
        if raw.kind == 5:
            self.exit_continued = True

    def _close_launch_handles(self):
        # Only after process signal; otherwise preserve handles for the owner.
        if not self.signaled:
            return
        for index in (1, 0):
            handle = self.handles[index]
            if handle is None or self.close_state[index] != "not_started":
                continue
            self.close_state[index] = "uncertain"
            try:
                if not self.kernel.CloseHandle(handle):
                    self.close_state[index] = "failed"
                    raise TransportError("launch_handle_close", self.transport.last_error())
                self.handles[index] = None
                self.close_state[index] = "closed"
            except BaseException as error:
                self._record("launch_handle_close", error)

    def run(self, primary=None):
        need(not self.started, "stop_retry")
        self.started = True
        self.primary = primary
        self.resource_stop |= (isinstance(primary, MemoryError) or self.transport.resource_stop
                               or self.drain.resource_stop)
        self.result["status"] = "stopping"
        try:
            self.transport._thread()
            process = self.handles[0]
            need(process is not None and self.drain.pid == self.transport.pid, "unbound_owner")
            need(self.kernel.GetProcessId(process) == self.transport.pid, "owned_process_identity")
            wait = self.kernel.WaitForSingleObject(process, 0)
            need(wait in (0, 258), "owned_process_wait")
            self.signaled = wait == 0
            if not self.signaled:
                self.terminate_state = "uncertain"
                if not self.kernel.TerminateProcess(process, 1):
                    self.terminate_state = "failed"
                    raise TransportError("owned_terminate", self.transport.last_error())
                self.terminate_state = "requested"
                need(not self.transport.wait_inflight and not self.transport.continue_inflight,
                     "pending_outcome_uncertain")
                if self.transport.pending is not None:
                    self._release_pending(self.transport)
                deadline = self.clock() + 5
                for _ in range(self.LIMIT):
                    if self.exit_continued:
                        break
                    need(self.clock() < deadline, "drain_deadline")
                    self.waits += 1
                    if self.drain.wait(100):
                        self._release_pending(self.drain)
                need(self.exit_continued, "drain_exit_unconfirmed")
                wait = self.kernel.WaitForSingleObject(process, 100)
                need(wait in (0, 258), "owned_process_wait")
                self.signaled = wait == 0
                need(self.signaled, "owned_exit_unconfirmed")
        except BaseException as error:
            self._record("owned_stop", error)
        finally:
            for source in (self.transport, self.drain):
                try:
                    source.close_retained_files()
                except BaseException as error:
                    self._record("event_file_teardown", error)
                source.resource_stop |= self.resource_stop
                source.state = "stopped"
            self._close_launch_handles()
            for source in (self.transport, self.drain):
                source.resource_stop |= self.resource_stop
        try:
            resolved = all(source.pending is None and not source.wait_inflight and not source.continue_inflight
                           and all(source.file_closed[:source.count]) for source in (self.transport, self.drain))
            if not resolved:
                self._record("debug_ownership_unresolved", TransportError("debug_ownership_unresolved"))
            self.result.update(status="stopped" if self.signaled else "unconfirmed",
                               process_signaled=self.signaled, terminate_state=self.terminate_state,
                               exit_continued=self.exit_continued, failure_count=self.error_count,
                               resource_stop=self.resource_stop, drain_waits=self.waits,
                               teardown_status="failed" if self.error_count else "pass",
                               debug_ownership_resolved=resolved)
        except BaseException as error:
            self._record("stop_report", error)
            self.result["status"] = "report_failed"
            self.result["teardown_status"] = "failed"
            self.result["resource_stop"] = self.resource_stop
            self.transport.resource_stop |= self.resource_stop
            self.drain.resource_stop |= self.resource_stop
        return self.result
