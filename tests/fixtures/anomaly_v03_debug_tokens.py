"""Preowned parent/restricted token and SID outputs for a future driver.

No import-time native calls. Matches the core restricted-token recipe without
letting helper-local output buffers escape ownership on interrupted returns.
"""

import ctypes as C

from banto_ai import _anomaly_v03_windows as w
from tests.fixtures.anomaly_v03_debug_transport import TransportError, need


class DebugTokens:
    def __init__(self, api):
        self.api = api
        self.buffers = tuple(w.H() for _ in range(2 + len(w._PRIVILEGED) + 1))
        self.pointers = tuple(C.pointer(value) for value in self.buffers)
        self.acquire = ["not_started"] * len(self.buffers)
        self.release = ["not_started"] * len(self.buffers)
        self.disable = (w._SidAttr * len(w._PRIVILEGED))()
        self.restrict = (w._SidAttr * 1)()
        self.parent_profile = self.restricted_profile = None
        self.primary = self.secondary = None
        self.started = self.closed = self.resource_stop = False
        self.status = "not_started"
        self.invalid_handle = w.H(-1).value

    def __repr__(self):
        return "DebugTokens(<private profiles and owned outputs>)"

    def _confirmed(self, index, ok):
        if not ok:
            self.acquire[index] = "failed"
            raise TransportError("token_preparation_api")
        self.acquire[index] = "acquired"
        need(self.buffers[index].value not in (None, 0, self.invalid_handle), "token_preparation_output")

    def _sid(self, index, value):
        self.acquire[index] = "uncertain"
        self._confirmed(index, self.api.a.ConvertStringSidToSidW(value, self.pointers[index]))
        return self.buffers[index].value

    def _release(self, indexes):
        for index in indexes:
            if self.acquire[index] != "acquired" or self.release[index] != "not_started":
                continue
            try:
                value = self.buffers[index].value
                need(value not in (None, 0, self.invalid_handle), "token_preparation_output")
                self.release[index] = "uncertain"
                ok = self.api.k.CloseHandle(value) if index < 2 else not self.api.k.LocalFree(value)
                if not ok:
                    self.release[index] = "failed"
                    raise TransportError("token_preparation_release")
                self.release[index] = "closed"
            except BaseException as error:
                if self.secondary is None:
                    self.secondary = error
                self.resource_stop |= w._resource_stop(error)

    def resolved(self, indexes):
        return all(self.acquire[index] in ("not_started", "failed")
                   or self.acquire[index] == "acquired" and self.release[index] == "closed"
                   for index in indexes)

    def prepare(self):
        need(not self.started and not self.closed, "token_preparation_retry")
        self.started = True
        try:
            self.api.no_impersonation()
            parent = self.api.k.GetCurrentProcess()
            self.acquire[0] = "uncertain"
            self._confirmed(0, self.api.a.OpenProcessToken(parent, 0x8B, self.pointers[0]))
            self.parent_profile = self.api.profile(self.buffers[0].value)
            w._validate_parent(self.parent_profile)
            groups = tuple(group[0] for group in self.parent_profile["groups"] if group[0] in w._PRIVILEGED)
            need(len(groups) <= len(self.disable), "token_disable_capacity")
            for index, group in enumerate(groups):
                self.disable[index].sid = self._sid(index + 2, group)
            self.restrict[0].sid = self._sid(len(self.buffers) - 1, w._RC)
            self.acquire[1] = "uncertain"
            self._confirmed(1, self.api.a.CreateRestrictedToken(
                self.buffers[0].value, 9, len(groups), self.disable, 0, None, 1,
                self.restrict, self.pointers[1]))
            self.restricted_profile = self.api.profile(self.buffers[1].value)
            w._validate_restricted(self.parent_profile, self.restricted_profile)
            self.status = "prepared"
        except BaseException as error:
            self.primary = error
            self.resource_stop |= w._resource_stop(error)
            self.status = "failed"
        finally:
            self._release(range(2, len(self.buffers)))
        if self.secondary is not None or not self.resolved(range(2, len(self.buffers))) or self.resource_stop:
            self.status = "failed"
        return self

    def close(self):
        # Closing before prepare permanently prevents future acquisition.
        self.closed = True
        self._release((1, 0))
        self._release(range(2, len(self.buffers)))
        return self.resolved(range(len(self.buffers)))
