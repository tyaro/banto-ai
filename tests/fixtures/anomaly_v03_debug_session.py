"""Prepared-fixture diagnostic session; no CLI or automatic native execution.

The outer driver still owns creation/validation of the new fixture and parent/
restricted token. This session owns only actual/duplicate child tokens. It ties
preflight, suspended creation, actual-child checks, resume and observation to
one retained result. Bootstrap remains fail-closed in the existing transport.
"""

import ctypes as C
import os

from banto_ai import _anomaly_v03_windows as w
from tests.fixtures.anomaly_v03_debug_transport import TransportError, need


class SessionResult(dict):
    def __init__(self, owner):
        super().__init__(status="not_started", resume_state="not_started",
                         resource_stop=False, token_teardown="not_started",
                         native_accepted=False, formal_permission=False)
        self.private_owner = owner


class DebugSession:
    def __init__(self, preflight, launch, observer, parent_profile, restricted_profile):
        need(observer.stop is launch.stop and observer.transport is launch.transport, "session_owner")
        self.preflight, self.launch, self.observer = preflight, launch, observer
        self.api, self.stop, self.transport = launch.api, launch.stop, launch.transport
        self.parent_profile, self.restricted_profile = parent_profile, restricted_profile
        self.tokens = [None, None]
        self.token_buffers = (w.H(), w.H())
        self.token_pointers = tuple(C.pointer(value) for value in self.token_buffers)
        self.token_acquire_state = ["not_started", "not_started"]
        self.token_close_state = ["not_started", "not_started"]
        self.primary = self.secondary = None
        self.resource_stop = self.started = False
        self.resume_state = "not_started"
        self.identity = self.actual_profile = self.duplicate_profile = self.access = None
        self.preflight_result = self.launch_result = self.observation_result = self.stop_result = None
        self.result = SessionResult(self)

    def __repr__(self):
        return "DebugSession(<private profiles, evidence and ownership>)"

    def _latch(self, error):
        self.resource_stop |= (w._resource_stop(error) or self.preflight.resource_stop
                               or self.launch.resource_stop or self.observer.resource_stop
                               or self.transport.resource_stop or self.stop.resource_stop)
        self.transport.resource_stop |= self.resource_stop
        self.stop.resource_stop |= self.resource_stop

    def _close_tokens(self):
        for index in (1, 0):
            if self.token_acquire_state[index] != "acquired" or self.token_close_state[index] != "not_started":
                continue
            try:
                # Recover confirmed output even if slot assignment after the
                # success marker was interrupted. Uncertain API output is only
                # retained, never guessed to be a valid token for CloseHandle.
                handle = self.token_buffers[index].value
                self.tokens[index] = handle
                need(handle not in (None, 0, w.H(-1).value), "session_token_handle")
                self.token_close_state[index] = "uncertain"
                if not self.api.k.CloseHandle(handle):
                    self.token_close_state[index] = "failed"
                    raise TransportError("session_token_close", self.transport.last_error())
                self.tokens[index] = None
                self.token_close_state[index] = "closed"
            except BaseException as error:
                if self.secondary is None:
                    self.secondary = error
                self._latch(error)

    def _acquire_token(self, index):
        need(self.token_acquire_state[index] == "not_started", "session_token_retry")
        self.token_acquire_state[index] = "uncertain"
        if index == 0:
            ok = self.api.a.OpenProcessToken(self.launch.process.process, 0xA, self.token_pointers[0])
        else:
            ok = self.api.a.DuplicateTokenEx(self.tokens[0], 8, None, 2, 2, self.token_pointers[1])
        if not ok:
            self.token_acquire_state[index] = "failed"
            raise TransportError("session_token_acquire", self.transport.last_error())
        self.token_acquire_state[index] = "acquired"
        self.tokens[index] = self.token_buffers[index].value
        need(self.tokens[index] not in (None, 0, w.H(-1).value), "session_token_handle")

    def _completed(self, result, owner, status, reason):
        if result["status"] != status or self.resource_stop:
            raise owner.primary or owner.secondary or TransportError(reason)

    def _validate_child(self):
        process = self.launch.process
        self.observer._budget()
        self.identity = w._process_identity(self.api, process.process)
        need(self.identity["pid"] != os.getpid() and self.identity["pid"] == process.pid, "child_pid")
        self.observer._budget()
        self._acquire_token(0)
        self.actual_profile = self.api.profile(self.tokens[0])
        w._validate_restricted(self.parent_profile, self.actual_profile)
        need(w._shape(self.actual_profile) == w._shape(self.restricted_profile), "child_primary_profile")
        self.observer._budget()
        self._acquire_token(1)
        self.duplicate_profile = self.api.profile(self.tokens[1])
        need(self.duplicate_profile["type"] == 2
             and w._shape(self.duplicate_profile) == w._shape(self.actual_profile), "child_duplicate_profile")
        self.observer._budget()
        self.access = w._access_matrix(self.api, self.launch.fixture.root,
                                       self.launch.fixture.ledger, self.tokens[1])
        self.observer._budget()

    def run(self):
        need(not self.started, "session_retry")
        self.started = True
        try:
            need(not self.launch.started and not self.observer.started and not self.stop.started,
                 "session_started_components")
            self.preflight_result = self.preflight.run()
            self._latch(self.preflight.primary)
            self._completed(self.preflight_result, self.preflight, "verified", "session_preflight")
            # One 30-second observation clock includes creation/validation and
            # Resume; observer.run must not reset it after the child starts.
            self.observer._time()
            self.launch_result = self.launch.create()
            self._latch(self.launch.primary)
            self._completed(self.launch_result, self.launch, "suspended", "session_create")
            self._validate_child()
            self.transport._thread()
            self.resume_state = "uncertain"
            previous = self.api.k.ResumeThread(self.launch.process.thread)
            need(type(previous) is int and previous == 1, "session_resume_count")
            self.resume_state = "resumed"
            self.observation_result = self.observer.run()
            self._latch(self.observer.primary)
            self._completed(self.observation_result, self.observer, "observed", "session_observation")
        except BaseException as error:
            self.primary = error
            self._latch(error)
        finally:
            self.transport.state = "stopped"
            if self.launch.creation_state == "created" and not self.stop.started:
                try:
                    self.stop_result = self.stop.run(self.primary)
                except BaseException as error:
                    self.secondary = error
                    self._latch(error)
            self._close_tokens()
        try:
            self._latch(self.secondary)
            token_clean = all(self.tokens[index] is None
                              and (self.token_acquire_state[index] in ("not_started", "failed")
                                   or self.token_acquire_state[index] == "acquired"
                                   and self.token_close_state[index] == "closed") for index in (0, 1))
            self.result.update(status="observed" if self.primary is None and self.secondary is None
                               and not self.resource_stop and token_clean else "failed",
                               resume_state=self.resume_state, resource_stop=self.resource_stop,
                               token_teardown="pass" if token_clean else "failed")
        except BaseException as error:
            self.secondary = error
            self._latch(error)
            self.result["status"] = "report_failed"
            self.result["resource_stop"] = self.resource_stop
            self.result["token_teardown"] = "failed"
        return self.result
