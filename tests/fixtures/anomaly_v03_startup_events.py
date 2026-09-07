"""Offline startup-event contract. No native API, process, file or network IO.

The future adapter owns handles, validates native fields and observes actual
ContinueDebugEvent results. This recorder neither owns nor closes handles.
"""

from dataclasses import dataclass


class EventContractError(ValueError):
    def __str__(self):
        return "startup_event_contract_failed"


def require(value):
    if not value:
        raise EventContractError()


@dataclass(frozen=True, repr=False)
class StartupEvent:
    kind: str
    pid: int
    tid: int
    code: int = 0
    first_chance: bool = False

    def __repr__(self):
        return "StartupEvent(<private>)"


class StartupEvents:
    """Preallocated slots retain a delivered event before any continuation.

    `continued` is confirmation supplied by an adapter, never an API substitute.
    No breakpoint is automatically swallowed: bootstrap identification belongs
    to a separately reviewed adapter; unknown exceptions remain unhandled.
    """
    LIMIT = 256
    TIME_LIMIT_MS = 30_000
    KINDS = ("create_process", "create_thread", "load_dll", "unload_dll",
             "exception", "debug_string", "exit_thread", "exit_process", "rip")

    def __init__(self, pid):
        require(type(pid) is int and 0 < pid < 2**32)
        self.pid = pid
        self.slots = [None] * self.LIMIT
        self.count = self.confirmed = self.elapsed_ms = 0
        self.pending = None
        self.status = "prepared"
        self.resource_stop = False
        self.exit_observed = None

    def __repr__(self):
        return "StartupEvents(<private>)"

    def receive(self, event, elapsed_ms):
        require(self.status in ("prepared", "running") and self.pending is None)
        require(type(event) is StartupEvent and event.kind in self.KINDS)
        require(type(event.pid) is int and event.pid == self.pid)
        require(type(event.tid) is int and 0 < event.tid < 2**32)
        require(type(event.code) is int and 0 <= event.code < 2**32)
        require(type(event.first_chance) is bool)
        require(type(elapsed_ms) is int and self.elapsed_ms <= elapsed_ms < self.TIME_LIMIT_MS)
        require(self.count < self.LIMIT)
        require(event.kind == "create_process" if self.count == 0 else event.kind != "create_process")
        require(event.kind == "exception" or event.first_chance is False)
        require(event.kind in ("exception", "exit_thread", "exit_process", "rip") or event.code == 0)
        self.slots[self.count] = event
        self.pending = event
        self.count += 1
        self.elapsed_ms = elapsed_ms
        self.status = "running"
        if event.kind == "exit_process":
            self.exit_observed = event.code

    def continued(self):
        require(self.status == "running" and self.pending is not None)
        event = self.pending
        self.confirmed += 1
        self.pending = None
        if event.kind == "exit_process":
            # EXIT event continuation is not a signaled process-handle wait.
            self.status = "exit_continued"

    def process_signaled(self):
        require(self.status == "exit_continued")
        self.status = "completed"

    def stop(self, *, resource=False):
        require(type(resource) is bool and self.status != "completed")
        self.resource_stop |= resource
        self.status = "stopped"

    def report(self):
        # Allocates: only render when memory is available, outside OOM handling.
        events = self.slots[:self.count]
        return {"status": self.status, "events": self.count, "continued_events": self.confirmed,
                "pending_event": self.pending.kind if self.pending else None,
                "dll_load_events": sum(event.kind == "load_dll" for event in events),
                "exception_events": sum(event.kind == "exception" for event in events),
                "exit_code_observed": self.exit_observed, "resource_stop": self.resource_stop,
                "faulting_module": None, "native_accepted": False, "formal_permission": False}
