"""Bounded same-process, same-token peer opens; no namespace mutation."""
import ctypes as C
import hashlib
import json

from . import anomaly_v03_directory_driver as driver
from . import anomaly_v03_handle_owner as owned
from . import anomaly_v03_prepublication as prep
from . import anomaly_v03_rename_adapter as rename
from .anomaly_v03_tracked_open import TrackedOpen

# READ_ATTRIBUTES | READ_CONTROL | SYNCHRONIZE, plus exactly one tested bit.
CASES = (("list_control", 0x120081), ("add_file", 0x120082),
         ("add_subdirectory", 0x120084), ("delete_child", 0x1200C0))
INVALID = (1 << 64) - 1


class _Denied(owned.OwnershipError):
    pass


class PeerAcquisitions:
    """Retained before run. Backend returns fresh handles from OPEN_EXISTING.

    Only documented INVALID_HANDLE_VALUE plus error 5/32 is a known denial.
    This exception to unknown ownership applies to this noncreating open only.
    All other ambiguous replies require worker exit with the root retained.
    """
    def __init__(self, backend, original, *, guard):
        owned._need(type(original) is prep.Observation and callable(guard), "peer_original")
        rename._pin(original.pin)
        owned._need(original.pin.directory and type(original.descriptor) is bytes
                    and 0 < len(original.descriptor) <= prep.MAX_DESCRIPTOR_BYTES, "peer_original")
        self._backend, self._original, self._external_guard = backend, original, guard
        self._leases = tuple(TrackedOpen(backend) for _ in CASES)
        self._called = [False] * len(CASES)
        self._returned = [False] * len(CASES)
        self._denied = [False] * len(CASES)
        self._codes = [None] * len(CASES)
        self._access = [None] * len(CASES)
        self._states = ["not_started"] * len(CASES)
        self._started = self._busy = self._done = self._complete = self._resource = False
        self._error = None

    def _record(self, error):
        if self._error is None:
            self._error = error
        self._resource = self._resource or owned._resource(error)

    def _guard(self):
        if self._error is not None:
            raise self._error
        owned._need(not self._done, "peer_finished")
        owned._need(self._external_guard() is None, "peer_guard_response")
        if self._error is not None:
            raise self._error

    def run(self):
        entered = False
        try:
            owned._need(not self._started and not self._done and not self._busy, "peer_reused")
            self._started = self._busy = entered = True
            for index, (_, mask) in enumerate(CASES):
                self._guard()
                lease = self._leases[index]
                def open_one(cell):
                    try:
                        self._called[index] = True
                        self._states[index] = "open_pending"
                        cell.handle = self._backend.open_existing(mask)
                        self._returned[index] = True
                        if type(cell.handle) is int and cell.handle in (-1, INVALID):
                            code = self._backend.get_last_error()  # Before any guard/native callback.
                            self._codes[index] = code
                            if type(code) is int and code in (5, 32):
                                raise _Denied("peer_open_denied", code)
                            raise owned.OwnershipError("peer_open_failed", code if type(code) is int else 0)
                        owned._need(rename._handle(cell.handle), "peer_open_value")
                    except _Denied:
                        raise
                    except BaseException as error:
                        self._record(error)  # Before TrackedOpen invokes cleanup callbacks.
                        raise self._error

                def inspect(handle):
                    try:
                        self._guard()
                        access = self._backend.granted_access(handle)
                        self._guard()
                        self._access[index] = access
                        owned._need(type(access) is int and access == mask, "peer_granted_access")
                        observed = self._backend.inspect(handle, guard=self._guard)
                        self._guard()
                        owned._need(type(observed) is prep.Observation, "peer_observation")
                        old, new = self._original.pin, observed.pin
                        rename._pin(new)
                        owned._need(new.handle == handle and (new.volume, new.file_id, new.directory)
                                    == (old.volume, old.file_id, old.directory)
                                    and observed.descriptor == self._original.descriptor, "peer_object_changed")
                        return observed
                    except BaseException as error:
                        self._record(error)
                        raise self._error

                try:
                    lease.acquire(open_one, inspect)
                except _Denied as denial:
                    owned._need(type(denial) is _Denied and lease._error is denial
                                and self._returned[index] and type(lease.handle) is int
                                and lease.handle in (-1, INVALID) and self._codes[index] in (5, 32), "peer_denial_binding")
                    self._denied[index] = True
                    self._states[index] = "denied"
                    self._guard()
                    owned._need(index != 0, "peer_control_denied")
                else:
                    self._guard()
                    self._states[index] = "granted"
                    lease.close()
                    self._guard()
            self._complete = True
        except BaseException as error:
            self._record(error)
        finally:
            if entered:
                self._busy = False
                self.finish()
        if self._error is not None:
            raise self._error

    def finish(self, *, primary=None):
        if primary is not None:
            self._record(primary)
        if self._busy:
            self._record(owned.OwnershipError("peer_active"))
            raise self._error
        if not self._done:
            self._done = self._busy = True
            try:
                for index in reversed(range(len(self._leases))):
                    lease = self._leases[index]
                    try:
                        lease.close()
                    except BaseException as error:
                        if not (self._denied[index] and type(error) is _Denied and error is lease._error):
                            self._record(error)
                    self._resource = self._resource or lease.resource_stop
            finally:
                self._busy = False
        if self._error is not None:
            raise self._error

    def requires_exit(self):
        return any(called and not denied and lease.close_state not in ("closed", "not_needed")
                   for called, denied, lease in zip(self._called, self._denied, self._leases))

    def snapshot(self):
        owned._need(self._done and not self._busy and not self._resource, "peer_report_unavailable")
        return {"matrix_complete": self._complete and self._error is None,
                "cases": [{"name": name, "requested_access": mask, "granted_access": self._access[i],
                           "state": self._states[i], "winerror": self._codes[i], "open_called": self._called[i],
                           "open_returned": self._returned[i], "known_no_handle_denial": self._denied[i],
                           "close": self._leases[i].snapshot()} for i, (name, mask) in enumerate(CASES)],
                "same_process_same_token": True, "independent_process_tested": False,
                "namespace_mutation_performed": False, "worker_exit_required": self.requires_exit(),
                "isolation_certified": False, "acceptance_status": "not_completed"}


class WindowsPeerBackend:
    def __init__(self, context):
        self.context = context

    def open_existing(self, mask):
        owned._need(mask in dict(CASES).values(), "peer_access_plan")
        # Share all permits the original handle's access. Security attributes
        # NULL makes this new handle noninheritable; never CREATE/DELETE_ON_CLOSE.
        return self.context.sink._api.k.CreateFileW(str(self.context.source_path), mask, 7, None, 3, 0x02200000, None)

    def get_last_error(self):
        return self.context.backend.get_last_error()

    def granted_access(self, handle):
        return self.context.backend.granted_access(handle)

    def inspect(self, handle, *, guard):
        return self.context.backend.inspect(handle, guard=guard)

    def close_handle(self, handle):
        return self.context.backend.close_handle(handle)


class ProfiledSink(driver.WindowsPrivateSink):
    """Read initial primary-token facts using the sink's existing query slot."""
    def __init__(self):
        super().__init__()
        self.token_basis = None

    def _read_user(self):
        token = self._token = TrackedOpen(self._backend)
        def open_token(cell):
            value = self._win.H()
            ok = self._api.a.OpenProcessToken(self._api.k.GetCurrentProcess(), 8, C.byref(value))
            self._api.call(ok, "peer_token_query")
            cell.handle = value.value
        def inspect(handle):
            profile = self._api.profile(handle)
            enabled = [name for name, attributes in profile["privileges"] if attributes & 2]
            owned._need(profile["type"] == 1 and profile["elevated"] == 0
                        and profile["integrity"] == "S-1-16-8192"
                        and not {"SeBackupPrivilege", "SeRestorePrivilege"}.intersection(enabled), "peer_token_basis")
            self.token_basis = {key: profile[key] for key in ("user", "token_id", "modified_id", "authentication_id",
                                                              "integrity", "elevated", "type")}
            self.token_basis["enabled_privileges"] = enabled
            owned._need(len(json.dumps(self.token_basis)) <= 4096, "peer_token_basis_budget")
            return profile["user"][0]
        try:
            return token.acquire(open_token, inspect)
        finally:
            try:
                token.close()
            finally:
                self._resource = self._resource or token.resource_stop


class PeerContext(driver.WindowsAcquisitionContext):
    MAX_POINTS = 96  # Extra read-only guards; same memory, disk and time limits.

    def __init__(self, attempt, revision):
        super().__init__(attempt, revision)
        self.sink = ProfiledSink()
        self.peers = None
        self._driver_guard = None

    def configure_directory(self, guard):
        self._driver_guard = guard
        super().configure_directory(guard)

    def _peer_guard(self):
        self._driver_guard()
        lease = self.directory._lease
        owned._need(lease.state == "ready" and lease.close_state == "not_started" and lease._error is None
                    and lease._custodian is None, "peer_original_not_owned")

    def persist(self, observation):
        owned._need(self.peers is None, "peer_context_reused")
        self.peers = PeerAcquisitions(WindowsPeerBackend(self), observation, guard=self._peer_guard)
        self.peers.run()
        self._peer_guard()
        raw = (json.dumps({"scope": "same-token directory access acquisition only", "source_revision": self.revision,
                           "directory": {"volume": observation.pin.volume, "file_id": observation.pin.file_id.hex(),
                                         "descriptor_sha256": hashlib.sha256(observation.descriptor).hexdigest()},
                           "peers": self.peers.snapshot(), "isolation_certified": False,
                           "initial_token_basis": self.sink.token_basis,
                           "acceptance_status": "not_completed"}, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
        owned._need(len(raw) <= 16 * 1024, "peer_evidence_budget")
        digest = hashlib.sha256(raw).hexdigest()
        self.sink.persist_evidence("prepare", raw, digest)
        self._evidence_bytes, self._evidence_sha = len(raw), digest

    def resource_stop(self):
        return super().resource_stop() or self.peers is not None and self.peers._resource

    def child_requires_exit(self):
        return super().child_requires_exit() or self.peers is not None and self.peers.requires_exit()

    def snapshot(self):
        report = super().snapshot()
        report["peers"] = None if self.peers is None else self.peers.snapshot()
        report["initial_token_basis"] = self.sink.token_basis
        report["source_reopened_by_path"] = self.peers is not None and any(self.peers._called)
        report["source_reopen_scope"] = "intentional same-token peer requests while original root is retained"
        return report


class PeerDriver(driver.AcquisitionDriver):
    def finish(self):
        if self._busy:
            return super().finish()  # Latch reentry, including swallowed callbacks.
        if not self._done and self.context.peers is not None:
            self._busy = True
            try:
                peers = self.context.peers
                try:
                    peers.finish(primary=self._error)
                except BaseException as error:
                    self._record(error)
                self._resource = self._resource or peers._resource
                if peers.requires_exit():
                    # Do not let the base driver close the root before an
                    # unknown peer; retain the entire context until exit.
                    self._retained = self._done = True
            finally:
                self._busy = False
        return super().finish()
