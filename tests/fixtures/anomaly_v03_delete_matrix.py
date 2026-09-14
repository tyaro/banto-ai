"""Four fresh empty-file DeleteFileW cases; no publisher or retained-peer proof."""
import ctypes as C
import hashlib
import json
from dataclasses import dataclass

from . import anomaly_v03_directory_acquisition as acq
from . import anomaly_v03_directory_driver as driver
from . import anomaly_v03_directory_peer as peer
from . import anomaly_v03_handle_owner as owned
from . import anomaly_v03_prepublication as prep
from . import anomaly_v03_rename_adapter as rename
from .anomaly_v03_tracked_open import TrackedOpen

FILE_ACCESS = 0x120081  # Read-only lifetime handle, no DELETE or WRITE_DAC.


@dataclass(frozen=True)
class CasePlan:
    name: str
    deny_parent: bool
    deny_child: bool
    child_share: int


CASES = (CasePlan("file-permission", True, False, 7),
         CasePlan("parent-permission", False, True, 7),
         CasePlan("sharing-block", False, True, 3),
         CasePlan("both-denied", True, True, 7))


def policy(user, *, directory, deny):
    mask = 0x40 if directory else 0x10000
    rows = ([[1, 0, mask, "S-1-1-0"]] if deny else [])
    rows += [[0, 0, 0x1F01FF, sid] for sid in (user, "S-1-5-18", "S-1-5-32-544")]
    return "D:P" + "".join(f"({'D' if kind else 'A'};;0x{bits:x};;;{sid})" for kind, _, bits, sid in rows), rows


class PolicyBackend(acq.WindowsDirectoryBackend):
    def __init__(self, win, api, *, path, user, deny):
        owned._need(type(deny) is bool, "delete_policy")
        self.deny = deny
        super().__init__(win, api, path=path, user=user)

    def _sddl(self):
        return policy(self._user, directory=self.DIRECTORY, deny=self.deny)[0]

    def _verify_policy(self, sd):
        owned._need(sd["protected"] is True and sd["owner"] == self._user and bool(sd["group"])
                    and sd["aces"] == policy(self._user, directory=self.DIRECTORY, deny=self.deny)[1], "delete_sd_policy")


class _Standard(C.Structure):
    _fields_ = [("allocation", C.c_int64), ("end", C.c_int64), ("links", C.c_uint32),
                ("pending", C.c_ubyte), ("directory", C.c_ubyte)]


class FileBackend(PolicyBackend):
    """Reuse captured descriptor/call/close ownership; acquire via TrackedOpen.

    DirectoryAcquisition itself is used only for case directories.
    """
    DIRECTORY = False

    def __init__(self, win, api, *, path, user, deny, share):
        owned._need(type(share) is int and share in (3, 7), "delete_share")
        self.share = share
        super().__init__(win, api, path=path, user=user, deny=deny)

    def prepare(self):
        super().prepare()
        owned._need(C.sizeof(_Standard) == 24 and _Standard.pending.offset == 20
                    and _Standard.directory.offset == 21, "file_standard_abi")
        self._create = self._api.k.CreateFileW
        self._arguments = (str(self._path), FILE_ACCESS, self.share, C.byref(self._security), 1, 0x00200000, None)
        self._delete_buffer = C.create_unicode_buffer(str(self._path))
        self._delete_pointer = C.cast(self._delete_buffer, C.c_wchar_p)

    def standard(self, handle):
        value = _Standard()
        self._api.call(self._api.k.GetFileInformationByHandleEx(handle, 1, C.byref(value), C.sizeof(value)), "delete_standard")
        owned._need(value.directory == 0 and value.pending in (0, 1) and value.links in (0, 1)
                    and value.end == 0 and value.allocation == 0, "delete_empty_file_changed")
        return {"allocation": value.allocation, "end": value.end, "links": value.links, "pending": bool(value.pending)}

    def _content_hash(self, handle, *, guard):
        guard()
        info = self.standard(handle)
        guard()
        owned._need(info["pending"] is False and info["links"] == 1, "delete_initial_file_state")
        return hashlib.sha256(b"").hexdigest()

    def after(self, handle, original, *, guard):
        # A delete-pending file may no longer support path-based observation.
        # Query only the retained handle's ID, SD and standard information.
        ident = self._win._FileId()
        guard()
        self._api.call(self._api.k.GetFileInformationByHandleEx(handle, 18, C.byref(ident), C.sizeof(ident)), "delete_file_id")
        guard()
        owned._need(ident.volume == original.pin.volume and bytes(ident.identifier) == original.pin.file_id,
                    "delete_original_file_changed")
        sd = self._api.security(handle)
        guard()
        self._verify_policy(sd)
        raw = json.dumps(sd, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii")
        owned._need(raw == original.descriptor, "delete_file_sd_changed")
        return self.standard(handle)

    def delete(self):
        return self._api.k.DeleteFileW(self._delete_pointer)


class DeleteCase:
    """Root, child and input storage remain reachable until confirmed finish."""
    def __init__(self, plan, root_backend, file_backend, *, guard):
        owned._need(type(plan) is CasePlan and plan in CASES and callable(guard), "delete_case_plan")
        self.plan, self.root_backend, self.file_backend = plan, root_backend, file_backend
        self._external_guard = guard
        self.root = acq.DirectoryAcquisition(root_backend, guard=self._guard)
        self.child = TrackedOpen(file_backend)
        self._started = self._busy = self._done = self._resource = self._complete = False
        self._error = None
        self._root_observed = self._child_observed = self._before = self._after = None
        self._delete_called = self._delete_returned = self._retained = False
        self._result, self._code = "not_started", None

    def _record(self, error):
        if self._error is None:
            self._error = error
        self._resource = self._resource or owned._resource(error)

    def _guard(self):
        if self._error is not None:
            raise self._error
        owned._need(not self._done, "delete_case_finished")
        owned._need(self._external_guard() is None, "delete_guard_response")
        if self._error is not None:
            raise self._error
        if self._root_observed is not None:
            lease = self.root._lease
            owned._need(lease.state == "ready" and lease.close_state == "not_started" and lease._error is None
                        and lease._custodian is None and lease.handle == self._root_observed.pin.handle, "delete_root_not_owned")

    def run(self):
        entered = False
        try:
            owned._need(not self._started and not self._busy and not self._done, "delete_case_reused")
            self._started = self._busy = entered = True
            self._guard()
            self._root_observed = self.root.acquire()
            self._guard()
            owned._need(self.file_backend.prepare() is None, "delete_file_prepare_response")
            self._guard()
            def create(cell):
                try:
                    self._guard()
                    owned._need(self.file_backend.create(cell) is None and rename._handle(cell.handle), "delete_file_create_response")
                except BaseException as error:
                    self._record(error)
                    raise self._error
            def inspect(handle):
                try:
                    self._guard()
                    access = self.file_backend.granted_access(handle)
                    self._guard()
                    owned._need(type(access) is int and access == FILE_ACCESS, "delete_file_access")
                    observed = self.file_backend.inspect(handle, guard=self._guard)
                    self._guard()
                    owned._need(type(observed) is prep.Observation, "delete_file_observation")
                    rename._pin(observed.pin)
                    owned._need(not observed.pin.directory and observed.pin.handle == handle
                                and type(observed.descriptor) is bytes and 0 < len(observed.descriptor) <= prep.MAX_DESCRIPTOR_BYTES,
                                "delete_file_observation")
                    return observed
                except BaseException as error:
                    self._record(error)
                    raise self._error
            self._child_observed = self.child.acquire(create, inspect)
            self._guard()
            self._before = self.file_backend.standard(self.child.handle)
            self._guard()
            owned._need(self._before["pending"] is False and self._before["links"] == 1, "delete_initial_state")
            owned._need(self.root_backend.inspect(self.root._lease.handle, guard=self._guard) == self._root_observed,
                        "delete_parent_changed")
            self._guard()
            self._delete_called = True
            self._result = "unknown"
            result = self.file_backend.delete()
            self._delete_returned = True
            if type(result) is int and result == 0:
                self._code = self.file_backend.get_last_error()  # No guard/API before this capture.
                if type(self._code) is not int or self._code not in (5, 32):
                    raise owned.OwnershipError("delete_unclassified_failure", self._code if type(self._code) is int else 0)
                self._result = "denied"
            else:
                owned._need(type(result) is int and -(1 << 31) <= result < 1 << 31 and result != 0, "delete_response_shape")
                self._result = "accepted"
            self._guard()
            self._after = self.file_backend.after(self.child.handle, self._child_observed, guard=self._guard)
            self._guard()
            owned._need(self._after["pending"] is (self._result == "accepted"), "delete_pending_mismatch")
            owned._need(self.root_backend.inspect(self.root._lease.handle, guard=self._guard) == self._root_observed,
                        "delete_parent_changed")
            self._guard()
            owned._need(self.plan != CASES[0] or self._result == "accepted", "delete_positive_control_failed")
            self._complete = True
        except BaseException as error:
            self._record(error)
        finally:
            if entered:
                self._busy = False
                self.finish()
        if self._error is not None:
            raise self._error

    def _file_unknown(self):
        return (self.child.state != "not_started" and self.child.close_state not in ("closed", "not_needed")
                or self.file_backend.requires_exit())

    def finish(self, *, primary=None):
        if primary is not None:
            self._record(primary)
        if self._busy:
            self._record(owned.OwnershipError("delete_case_active"))
            raise self._error
        if not self._done:
            self._done = self._busy = True
            try:
                if self._delete_called and self._result == "unknown":
                    self._retained = True  # Retain known child, root and path input until exit.
                else:
                    for operation in (self.child.close, self.file_backend.release):
                        try:
                            owned._need(operation() is None, "delete_finish_response")
                        except BaseException as error:
                            self._record(error)
                    self._resource = self._resource or self.child.resource_stop
                    self._retained = True  # A failed lifetime query cannot release the parent.
                    try:
                        self._retained = self._file_unknown()
                    except BaseException as error:
                        self._record(error)
                    if not self._retained:
                        try:
                            self.root.finish(primary=self._error)
                        except BaseException as error:
                            self._record(error)
                        self._resource = self._resource or self.root._resource
                self.requires_exit()  # Latch state-query faults before the caller reads resource_stop.
            finally:
                self._busy = False
        if self._error is not None:
            raise self._error

    def requires_exit(self):
        if self._retained:
            return True
        try:
            return (self.root._lease.state != "not_started"
                    and self.root._lease.close_state not in ("closed", "not_needed")) or self.root_backend.requires_exit()
        except BaseException as error:
            self._retained = True
            self._record(error)
            return True

    def snapshot(self):
        owned._need(self._done and not self._busy and not self._resource, "delete_report_unavailable")
        def observation(value):
            return None if value is None else {"volume": value.pin.volume, "file_id": value.pin.file_id.hex(),
                    "descriptor_sha256": hashlib.sha256(value.descriptor).hexdigest()}
        return {"name": self.plan.name, "deny_parent_delete_child": self.plan.deny_parent,
                "deny_child_delete": self.plan.deny_child, "child_share": self.plan.child_share,
                "complete": self._complete and self._error is None, "delete_called": self._delete_called,
                "delete_returned": self._delete_returned, "delete_result": self._result, "winerror": self._code,
                "before": self._before, "after": self._after, "root_observation": observation(self._root_observed),
                "child_observation": observation(self._child_observed), "root": self.root.snapshot(),
                "child_close": self.child.snapshot(), "root_backend": self.root_backend.snapshot(),
                "file_backend": self.file_backend.snapshot(), "worker_exit_required": self.requires_exit(),
                "postclose_path_inspected": False, "retained_parent_capability_tested": False,
                "isolation_certified": False, "acceptance_status": "not_completed"}


class DeleteMatrix:
    def __init__(self, context, guard):
        self._context, self._external_guard = context, guard
        self._started = self._busy = self._done = self._complete = self._resource = False
        self._error = None
        win, api, user = context.sink._win, context.sink._api, context.sink._user
        self.cases = tuple(DeleteCase(plan,
            PolicyBackend(win, api, path=str(context.attempt / plan.name), user=user, deny=plan.deny_parent),
            FileBackend(win, api, path=str(context.attempt / plan.name / "empty.bin"), user=user,
                        deny=plan.deny_child, share=plan.child_share), guard=self._guard) for plan in CASES)

    def _record(self, error):
        if self._error is None:
            self._error = error
        self._resource = self._resource or owned._resource(error)

    def _guard(self):
        if self._error is not None:
            raise self._error
        owned._need(not self._done, "delete_matrix_finished")
        owned._need(self._external_guard() is None, "delete_matrix_guard_response")
        if self._error is not None:
            raise self._error

    def run(self):
        entered = False
        try:
            owned._need(not self._started and not self._busy and not self._done, "delete_matrix_reused")
            self._started = self._busy = entered = True
            for case in self.cases:
                self._guard()
                case.run()
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
            self._record(owned.OwnershipError("delete_matrix_active"))
            raise self._error
        if not self._done:
            self._done = self._busy = True
            try:
                for case in reversed(self.cases):
                    try:
                        case.finish()
                    except BaseException as error:
                        self._record(error)
                    self._resource = self._resource or case._resource
            finally:
                self._busy = False
        if self._error is not None:
            raise self._error

    def requires_exit(self):
        return any(case.requires_exit() for case in self.cases)

    def snapshot(self):
        owned._need(self._done and not self._busy and not self._resource, "delete_matrix_report_unavailable")
        return {"matrix_complete": self._complete and self._error is None, "cases": [case.snapshot() for case in self.cases],
                "namespace_mutation_attempted": any(case._delete_called for case in self.cases),
                "same_process_same_token": True, "independent_process_tested": False,
                "retained_parent_capability_tested": False, "isolation_certified": False,
                "acceptance_status": "not_completed"}


class DeleteContext(peer.PeerContext):
    MAX_POINTS = 256

    def configure_cases(self, guard):
        owned._need(self.peers is None, "delete_context_reused")
        self.peers = DeleteMatrix(self, guard)

    def persist(self):
        raw = (json.dumps({"scope": "four fresh empty-file DeleteFileW controls", "source_revision": self.revision,
                           "matrix": self.peers.snapshot(), "initial_token_basis": self.sink.token_basis,
                           "isolation_certified": False, "acceptance_status": "not_completed"},
                          sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
        owned._need(len(raw) <= 16 * 1024, "delete_evidence_budget")
        digest = hashlib.sha256(raw).hexdigest()
        self.sink.persist_evidence("prepare", raw, digest)
        self._evidence_bytes, self._evidence_sha = len(raw), digest

    def snapshot(self):
        report = driver.WindowsAcquisitionContext.snapshot(self)
        report["matrix"] = None if self.peers is None else self.peers.snapshot()
        report["initial_token_basis"] = self.sink.token_basis
        report["source_scope"] = "four fixed case siblings; no source-fixture object"
        return report


class DeleteDriver(peer.PeerDriver):
    def run(self):
        entered = False
        try:
            owned._need(not self._started and not self._busy and not self._done, "delete_driver_reused")
            self._started = self._busy = entered = True
            self._check_resource()
            self._phase = "connect"
            owned._need(self.context.connect() is None, "delete_connect_response")
            self._guard()
            owned._need(self.context.configure_cases(self._guard) is None, "delete_configure_response")
            self._guard()
            self._phase = "delete_matrix"
            owned._need(self.context.peers.run() is None, "delete_matrix_response")
            self._guard()
            self._verified = self.context.peers._complete
            owned._need(self._verified is True, "delete_matrix_incomplete")
            self._phase = "evidence"
            self._evidence = "pending"
            owned._need(self.context.persist() is None, "delete_evidence_response")
            self._guard()
            self._evidence = "saved"
        except BaseException as error:
            self._record(error)
        finally:
            if entered:
                self._busy = False
                self.finish()
        if self._error is not None:
            raise self._error

    def snapshot(self):
        report = super().snapshot()
        report["delete_matrix"] = "complete" if self.exit_code() == 0 else "failed"
        report.pop("directory_acquisition")
        report.pop("same_handle_rechecked")  # Case records carry individual observations.
        return report
