"""Dormant bounded observation loop. No launcher, attach or bootstrap bypass.

The future launcher supplies an owned stop controller and a trusted combined
parent/child memory sampler. Construction and retention precede observation.
Raw events, primary failures and uncertain handles remain private on the owner.
"""

import math
import time

from tests.fixtures.anomaly_v03_debug_transport import TransportError, need
from tests.fixtures.anomaly_v03_startup_events import StartupEvents


class ObservationResult(dict):
    def __init__(self, owner):
        super().__init__(status="not_started", native_accepted=False, formal_permission=False,
                         resource_stop=False, events=0, continued_events=0,
                         exit_code_observed=None, teardown_status="not_started")
        self.private_owner = owner


class DebugObserver:
    MEMORY_LIMIT = 512 * 1024 * 1024
    WAIT_LIMIT = 300

    def __init__(self, stop, *, sample_memory, clock=time.monotonic):
        self.stop, self.transport = stop, stop.transport
        self.sample_memory, self.clock = sample_memory, clock
        self.events = StartupEvents(self.transport.pid)
        self.started = False
        self.primary = self.secondary = None
        self.resource_stop = False
        self.origin = self.last_clock = None
        self.waits = 0
        self.stop_result = None
        self.result = ObservationResult(self)

    def __repr__(self):
        return "DebugObserver(<private evidence and ownership>)"

    def _latch(self, error):
        self.resource_stop |= (isinstance(error, MemoryError) or self.transport.resource_stop
                               or self.stop.resource_stop or self.stop.drain.resource_stop)
        self.transport.resource_stop |= self.resource_stop
        self.events.resource_stop |= self.resource_stop

    def _time(self):
        now = self.clock()
        need(type(now) in (int, float) and math.isfinite(now), "clock_value")
        if self.origin is None:
            self.origin = self.last_clock = now
        need(now >= self.last_clock, "clock_reversed")
        self.last_clock = now
        need(now - self.origin < 30, "observation_deadline")
        return int((now - self.origin) * 1000)

    def _budget(self):
        need(not (self.resource_stop or self.transport.resource_stop or self.stop.resource_stop
                  or self.stop.drain.resource_stop), "resource_latched")
        self._time()
        memory = self.sample_memory()
        need(type(memory) is int and memory >= 0, "memory_sample")
        if memory >= self.MEMORY_LIMIT:
            self.resource_stop = True
            raise TransportError("memory_budget")
        need(not (self.resource_stop or self.transport.resource_stop or self.stop.resource_stop
                  or self.stop.drain.resource_stop), "resource_latched")
        return self._time()

    def run(self):
        need(not self.started, "observation_retry")
        self.started = True
        try:
            need(not self.stop.started and self.stop.handles[0] is not None
                 and self.stop.drain.pid == self.transport.pid, "observation_owner")
            need(self.transport.state == "idle" and self.transport.count == 0,
                 "observation_transport")
            if self.events.pid is None:
                self.events.bind(self.transport.pid)
            need(self.events.pid == self.transport.pid, "recorder_identity")
            self.transport._thread()
            need(self.transport.kernel.GetProcessId(self.stop.handles[0]) == self.transport.pid,
                 "owned_process_identity")
            self._budget()
            while self.transport.state != "exit_continued":
                self._budget()
                need(self.waits < self.WAIT_LIMIT, "observation_wait_limit")
                self.waits += 1
                delivered = self.transport.wait(100)
                elapsed = self._budget()
                if not delivered:
                    continue
                event = self.transport.event()
                self.events.receive(event, elapsed)
                if event.kind == "exit_process" and event.code == 80:
                    self.resource_stop = True
                    raise TransportError("child_resource_stop")
                self.transport.close_file(self.transport.pending)
                self._budget()
                # Transport refuses every unverified breakpoint. No callback
                # supplied by the caller can mark an arbitrary exception handled.
                self.transport.continue_event()
                self.events.continued()
            wait = self.transport.kernel.WaitForSingleObject(self.stop.handles[0], 100)
            need(wait == 0, "observation_exit_unconfirmed")
            self._budget()
            self.events.process_signaled()
        except BaseException as error:
            self.primary = error
            self._latch(error)
            try:
                self.events.stop(resource=self.resource_stop)
            except BaseException as secondary:
                self.secondary = secondary
                self._latch(secondary)
        finally:
            # Publish the terminal normal-channel state independently of the
            # stop controller, whose own entry/report can be interrupted.
            # Raw pending/inflight ownership is preserved for its drain path.
            self.transport.state = "stopped"
            try:
                self.stop_result = self.stop.run(self.primary)
            except BaseException as error:
                # Retain the preallocated controller even if its report fails.
                self.secondary = error
                self._latch(error)
        try:
            self._latch(self.secondary)
            clean = (self.stop_result is not None
                     and self.stop_result["teardown_status"] == "pass"
                     and self.stop_result["process_signaled"]
                     and self.stop_result["debug_ownership_resolved"])
            self.result.update(status="observed" if self.primary is None and self.secondary is None
                               and clean and not self.resource_stop else "failed",
                               resource_stop=self.resource_stop, events=self.events.count,
                               continued_events=self.events.confirmed,
                               exit_code_observed=self.events.exit_observed,
                               teardown_status="pass" if clean else "failed")
        except BaseException as error:
            self.secondary = error
            self._latch(error)
            self.result["status"] = "report_failed"
            self.result["resource_stop"] = self.resource_stop
            self.result["teardown_status"] = "failed"
        return self.result
