"""One-directory acquisition driver; no payload, marker, rename or cleanup."""
import ctypes as C
import hashlib
import json
from pathlib import Path
import shutil
import time

from . import anomaly_v03_directory_acquisition as acq
from . import anomaly_v03_handle_owner as owned
from .anomaly_v03_private_sink import WindowsPrivateSink


class AcquisitionDriver:
    """Retain context before run; all callbacks are trusted and synchronous."""
    def __init__(self, context):
        self.context = context
        self._started = self._busy = self._done = self._resource = False
        self._error = None
        self._evidence = "not_started"
        self._verified = self._retained = False
        self._phase = "not_started"

    def _record(self, error):
        if self._error is None:
            self._error = error
        self._resource = self._resource or owned._resource(error) or self.context.resource_stop()

    def _guard(self):
        if self._error is not None:
            raise self._error
        owned._need(not self._done, "driver_finished")
        self._check_resource()
        owned._need(self.context.guard() is None, "driver_guard_response")
        self._check_resource()
        if self._error is not None:
            raise self._error

    def _check_resource(self):
        if self._resource or self.context.resource_stop():
            self._resource = True
            raise MemoryError("driver_resource_stop")

    def run(self):
        entered = False
        try:
            owned._need(not self._started and not self._busy and not self._done, "driver_reused")
            self._started = self._busy = entered = True
            self._check_resource()
            self._phase = "connect"
            owned._need(self.context.connect() is None, "driver_connect_response")
            self._guard()
            owned._need(self.context.configure_directory(self._guard) is None, "driver_configure_response")
            self._guard()
            self._phase = "acquire"
            observed = self.context.directory.acquire()
            self._guard()
            self._phase = "evidence"
            self._evidence = "pending"
            owned._need(self.context.persist(observed) is None, "driver_evidence_response")
            self._guard()
            self._evidence = "saved"
            self._phase = "recheck"
            checked = self.context.backend.inspect(observed.pin.handle, guard=self._guard)
            self._guard()
            owned._need(checked == observed, "driver_directory_changed")
            self._verified = True
        except BaseException as error:
            self._record(error)
        finally:
            if entered:
                self._busy = False
                self.finish()
        if self._error is not None:
            raise self._error

    def finish(self):
        if self._busy:
            self._record(owned.OwnershipError("driver_active"))
            raise self._error
        if not self._done:
            self._done = self._busy = True
            try:
                directory = self.context.directory
                if directory is not None:
                    try:
                        directory.finish(primary=self._error)
                    except BaseException as error:
                        self._record(error)
                    self._resource = self._resource or directory._resource
                # An unknown child may still be live. Ancestors and descriptor
                # remain reachable until the dedicated worker actually exits.
                self._retained = self.context.child_requires_exit()
                if not self._retained:
                    try:
                        owned._need(self.context.finish() is None, "driver_finish_response")
                    except BaseException as error:
                        self._record(error)
                self._resource = self._resource or self.context.resource_stop()
            finally:
                self._busy = False
        if self._error is not None:
            raise self._error

    def exit_code(self):
        if self._resource:
            return 80
        if self._retained or self.context.requires_exit():
            return 81
        return 0 if (self._error is None and self._started and self._done and not self._busy
                     and self._evidence == "saved" and self._verified) else 1

    def snapshot(self):
        owned._need(self._done and not self._busy and not self._resource, "driver_report_unavailable")
        directory = self.context.directory
        return {"phase": self._phase, "directory_acquisition": "pass" if self.exit_code() == 0 else "fail",
                "error_type": None if self._error is None else type(self._error).__name__,
                "error_reason": None if self._error is None else getattr(self._error, "reason", None),
                "winerror": None if self._error is None else getattr(self._error, "winerror", getattr(self._error, "error", None)),
                "evidence": self._evidence, "same_handle_rechecked": self._verified,
                "ancestors_retained_for_worker_exit": self._retained,
                "directory": None if directory is None else directory.snapshot(),
                "context": self.context.snapshot(), "worker_exit_required": self.exit_code() == 81,
                "resource_stop": False, "isolation_certified": False, "protected_commit_allowed": False,
                "native_publication_performed": False, "native_acceptance_completed": False,
                "formal_permission": False, "execution_authenticated": False, "acceptance_status": "not_completed"}


class WindowsAcquisitionContext:
    """Evidence sink owns the exact ancestor chain of the new source sibling.

    Evidence bootstrap retains the earlier private sink trust limitations.
    No failed/colliding source is read, opened by name, reused or deleted.
    """
    def __init__(self, attempt, revision):
        self.attempt, self.revision = Path(attempt), revision
        self.source_path = self.attempt / "source-fixture"
        self.sink = WindowsPrivateSink()
        self.directory = self.backend = None
        self._ancestors = self._before = ()
        self._connected = self._finished = False
        self._start = time.monotonic()
        self._points = []
        self._evidence_bytes = self._evidence_sha = None
        self._parent_sd = C.c_void_p()
        self._parent_sd_state = "not_started"
        self._parent_sd_error = None
        self._parent_sd_resource = False

    def resource_stop(self):
        return self.sink._resource or self._parent_sd_resource

    def _parent_security(self, handle):
        if self._parent_sd_error is not None:
            raise self._parent_sd_error
        owned._need(self._parent_sd_state in ("not_started", "freed"), "driver_parent_sd_unavailable")
        api = self.sink._api
        length = api.a.GetSecurityDescriptorLength
        length.restype, length.argtypes = C.c_uint32, [C.c_void_p]
        self._parent_sd.value = None
        self._parent_sd_state = "pending"
        try:
            # Existing ancestors may inherit ACLs; compare their complete
            # returned descriptor without imposing the new-root private ACL.
            code = api.a.GetSecurityInfo(handle, 1, 0x17, None, None, None, None, C.byref(self._parent_sd))
            if type(code) is not int or code != 0 or self._parent_sd.value is None:
                raise owned.OwnershipError("driver_parent_sd_query", code if type(code) is int else None)
            self._parent_sd_state = "owned"
            control, revision = C.c_uint16(), C.c_uint32()
            api.call(api.a.GetSecurityDescriptorControl(self._parent_sd, C.byref(control), C.byref(revision)),
                     "driver_parent_sd_control")
            owned._need(control.value & 0x8000, "driver_parent_sd_not_relative")
            size = length(self._parent_sd)
            owned._need(type(size) is int and 20 <= size <= 8192, "driver_parent_sd_budget")
            raw = C.string_at(self._parent_sd, size)
        except BaseException as error:
            self._parent_sd_error = error
            self._parent_sd_resource = owned._resource(error)
        finally:
            if self._parent_sd_state == "owned":
                self._parent_sd_state = "free_unknown"
                try:
                    owned._need(not api.k.LocalFree(self._parent_sd), "driver_parent_sd_free")
                    self._parent_sd_state = "freed"
                except BaseException as error:
                    if self._parent_sd_error is None:
                        self._parent_sd_error = error
                    self._parent_sd_resource = self._parent_sd_resource or owned._resource(error)
        if self._parent_sd_error is not None:
            raise self._parent_sd_error
        return raw

    def budget(self):
        if len(self._points) >= 64:
            raise MemoryError("driver_point_budget")
        win, api = self.sink._win, self.sink._api
        memory, performance = win._Memory(), win._Performance()
        memory.cb, performance.cb = C.sizeof(memory), C.sizeof(performance)
        api.call(api.p.GetProcessMemoryInfo(api.k.GetCurrentProcess(), C.byref(memory), memory.cb), "probe_memory")
        api.call(api.p.GetPerformanceInfo(C.byref(performance), performance.cb), "probe_available_memory")
        point = {"elapsed_seconds": round(time.monotonic() - self._start, 3),
                 "private_bytes": memory.private, "working_bytes": memory.working,
                 "peak_working_bytes": memory.peak_working,
                 "available_ram_bytes": performance.available * performance.page_size,
                 "free_disk_bytes": shutil.disk_usage(self.attempt).free}
        self._points.append(point)
        if point["elapsed_seconds"] > 40 or memory.private > 256 * 1024**2 or memory.working > 384 * 1024**2 \
                or point["available_ram_bytes"] < 2 * 1024**3 or point["free_disk_bytes"] < 2 * 1024**3:
            raise MemoryError("driver_resource_limit")

    def _observe_parent(self, lease):
        owned._need(lease.state == "ready" and lease.close_state == "not_started" and lease._error is None
                    and lease._custodian is None, "driver_parent_not_owned")
        view = lease.observed
        identity = view.observe()
        owned._need(identity == view.identity and identity["directory"] is True, "driver_parent_identity")
        sd = self._parent_security(lease.handle)
        owned._need(view.observe() == identity, "driver_parent_changed")
        return identity, sd

    def connect(self):
        owned._need(not self._connected and not self._finished, "driver_context_reused")
        self.sink.connect(self.attempt / "private-evidence")
        self.budget()
        paths = tuple(reversed(self.source_path.parents))
        self._ancestors = tuple(self.sink._leases[:-1])
        owned._need(0 < len(paths) <= 16 and len(self._ancestors) == len(paths)
                    and tuple(lease.observed.path for lease in self._ancestors) == paths, "driver_parent_chain")
        self._before = tuple(self._observe_parent(lease) for lease in self._ancestors)
        owned._need(len({(value[0]["volume"], value[0]["file_id"]) for value in self._before}) == len(paths),
                    "driver_duplicate_parent")
        self._connected = True

    def guard(self):
        owned._need(self._connected and not self._finished and not self.sink._failed, "driver_context_unavailable")
        self.budget()
        for lease, expected in zip(self._ancestors, self._before):
            owned._need(self._observe_parent(lease) == expected, "driver_parent_binding_changed")

    def configure_directory(self, guard):
        owned._need(self.directory is None and self.backend is None, "driver_directory_reused")
        self.backend = acq.WindowsDirectoryBackend(self.sink._win, self.sink._api,
                                                   path=str(self.source_path), user=self.sink._user)
        self.directory = acq.DirectoryAcquisition(self.backend, guard=guard)

    def persist(self, observation):
        raw = (json.dumps({"scope": "single_call_directory_acquisition", "source_revision": self.revision,
                           "directory": {"volume": observation.pin.volume, "file_id": observation.pin.file_id.hex(),
                                         "descriptor_sha256": hashlib.sha256(observation.descriptor).hexdigest()},
                           "ancestors": [{"volume": identity["volume"], "file_id": identity["file_id"],
                                          "descriptor_sha256": hashlib.sha256(sd).hexdigest()}
                                         for identity, sd in self._before],
                           "isolation_certified": False, "acceptance_status": "not_completed"},
                          sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
        owned._need(len(raw) <= 16 * 1024, "driver_evidence_budget")
        digest = hashlib.sha256(raw).hexdigest()
        self.sink.persist_evidence("prepare", raw, digest)
        self._evidence_bytes, self._evidence_sha = len(raw), digest

    def child_requires_exit(self):
        if self._parent_sd_state not in ("not_started", "freed"):
            return True
        if self.directory is None:
            return False
        return (self.directory._lease.close_state in ("pending", "unknown", "unavailable")
                or self.backend._descriptor_state in ("allocating", "unavailable", "free_unknown", "retained_unknown"))

    def finish(self):
        if not self._finished:
            self._finished = True
            self.sink.finish()

    def requires_exit(self):
        return self.child_requires_exit() or any(cell.close_state not in ("closed", "not_needed")
                                                for cell in self.sink._leases) \
            or self.sink._token is not None and self.sink._token.close_state != "closed"

    def snapshot(self):
        return {"connected": self._connected, "finished": self._finished, "ancestor_count": len(self._ancestors),
                "evidence_bytes": self._evidence_bytes, "evidence_sha256": self._evidence_sha,
                "backend": None if self.backend is None else self.backend.snapshot(),
                "parent_descriptor_state": self._parent_sd_state,
                "sink": self.sink.snapshot(), "resources": list(self._points),
                "source_reopened_by_path": False, "source_postclose_read": False,
                "source_cleanup_performed": False}
