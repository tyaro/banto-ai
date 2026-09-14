"""Two fresh parent-share controls: peer opens versus CREATE_NEW child.

No payload write/delete/rename/enumeration, and no assertion of namespace isolation.
All known roots remain held through result persistence; ambiguity requires exit.
"""
import hashlib
import json
from dataclasses import dataclass

from . import anomaly_v03_directory_acquisition as acq
from . import anomaly_v03_directory_peer as peer
from . import anomaly_v03_delete_matrix as empty
from . import anomaly_v03_handle_owner as owned
from . import anomaly_v03_held_driver as terminal
from . import anomaly_v03_prepublication as prep
from . import anomaly_v03_rename_adapter as rename
from .anomaly_v03_tracked_open import TrackedOpen


@dataclass(frozen=True)
class Plan:
    name: str
    parent_share: int


PLANS = (Plan("share-read-write", 3), Plan("share-read-only", 1))


class ParentBackend(acq.WindowsDirectoryBackend):
    def __init__(self, win, api, *, path, user, share):
        owned._need(type(share) is int and share in (1, 3), "namespace_parent_share")
        self.share = share
        super().__init__(win, api, path=path, user=user)

    def prepare(self):
        super().prepare()
        path, access, _, redirects, security = self._arguments
        self._arguments = (path, access, self.share, redirects, security)


class ParentPeers:
    def __init__(self, parent):
        self.parent = parent

    def open_existing(self, mask):
        owned._need(mask in dict(peer.CASES).values(), "namespace_peer_mask")
        return self.parent._api.k.CreateFileW(str(self.parent._path), mask, 7, None, 3, 0x02200000, None)

    def get_last_error(self):
        return self.parent.get_last_error()

    def granted_access(self, handle):
        return self.parent.granted_access(handle)

    def inspect(self, handle, *, guard):
        return self.parent.inspect(handle, guard=guard)

    def close_handle(self, handle):
        return self.parent.close_handle(handle)


class CreationCase:
    def __init__(self, plan, parent, child, peer_backend, *, guard):
        owned._need(type(plan) is Plan and plan in PLANS and callable(guard), "namespace_case")
        self.plan, self.parent_backend, self.child_backend = plan, parent, child
        self.root = acq.DirectoryAcquisition(parent, guard=self._guard)
        self.child = TrackedOpen(child)
        self.peer_backend, self.peers, self._external_guard = peer_backend, None, guard
        self._started = self._busy = self._complete = self._resource = False
        self._children_done = self._root_done = False
        self._error = self._parent = self._child = None
        self._creation = "not_started"
        self._create_error = None

    def _record(self, error):
        if self._error is None:
            self._error = error
        self._resource = self._resource or owned._resource(error)

    def _guard(self):
        if self._error is not None:
            raise self._error
        owned._need(self._busy and not self._children_done and not self._root_done, "namespace_inactive")
        owned._need(self._external_guard() is None, "namespace_guard_response")
        if self._error is not None:
            raise self._error
        if self._parent is not None:
            lease = self.root._lease
            owned._need(lease.state == "ready" and lease.close_state == "not_started" and lease._error is None
                        and lease.handle == self._parent.pin.handle and lease._custodian is None, "namespace_parent_lifetime")

    def _recheck_parent(self):
        self._guard()
        now = self.parent_backend.inspect(self.root._lease.handle, guard=self._guard)
        self._guard()
        owned._need(now == self._parent, "namespace_parent_changed")

    def run(self):
        entered = False
        try:
            owned._need(not self._started and not self._busy and not self._children_done and not self._root_done,
                        "namespace_case_reused")
            self._started = self._busy = entered = True
            self._guard()
            self._parent = self.root.acquire()
            self._guard()
            self.peers = peer.PeerAcquisitions(self.peer_backend, self._parent, guard=self._guard)
            self.peers.run()
            self._recheck_parent()
            owned._need(self.child_backend.prepare() is None, "namespace_child_prepare_response")
            self._guard()

            def create(cell):
                try:
                    self._guard()
                    self._creation = "unknown"
                    owned._need(self.child_backend.create(cell) is None and rename._handle(cell.handle),
                                "namespace_create_response")
                    self._creation = "accepted"
                except BaseException as error:
                    code = getattr(error, "winerror", None)
                    if (getattr(self.child_backend, "_returned", False) and type(cell.handle) is int
                            and cell.handle in (-1, peer.INVALID) and type(code) is int and code in (5, 32)):
                        self._creation, self._create_error = "denied", code
                    # Even a classified creating failure keeps the parent; do
                    # not import OPEN_EXISTING's known-no-handle exception.
                    self._record(error)
                    raise self._error

            def inspect(handle):
                try:
                    self._guard()
                    access = self.child_backend.granted_access(handle)
                    self._guard()
                    owned._need(type(access) is int and access == empty.FILE_ACCESS, "namespace_child_access")
                    value = self.child_backend.inspect(handle, guard=self._guard)
                    self._guard()
                    owned._need(type(value) is prep.Observation, "namespace_child_observation")
                    rename._pin(value.pin)
                    owned._need(value.pin.handle == handle and not value.pin.directory
                                and value.pin.content_sha256 == hashlib.sha256(b"").hexdigest()
                                and type(value.descriptor) is bytes and 0 < len(value.descriptor) <= prep.MAX_DESCRIPTOR_BYTES,
                                "namespace_child_observation")
                    return value
                except BaseException as error:
                    self._record(error)
                    raise self._error

            self._child = self.child.acquire(create, inspect)
            self._recheck_parent()
            self._complete = True
        except BaseException as error:
            self._record(error)
        finally:
            if entered:
                self._busy = False
                self.finish_children()
        if self._error is not None:
            raise self._error

    def finish_children(self, *, primary=None):
        if primary is not None:
            self._record(primary)
        if self._busy:
            self._record(owned.OwnershipError("namespace_case_active"))
            raise self._error
        if not self._children_done:
            self._children_done = self._busy = True
            try:
                if self.peers is not None:
                    try:
                        self.peers.finish(primary=self._error)
                    except BaseException as error:
                        self._record(error)
                    self._resource = self._resource or self.peers._resource
                for operation in (self.child.close, self.child_backend.release):
                    try:
                        owned._need(operation() is None, "namespace_child_finish_response")
                    except BaseException as error:
                        self._record(error)
                self._resource = self._resource or self.child.resource_stop or self.root._resource
            finally:
                self._busy = False
        if self._error is not None:
            raise self._error

    def children_require_exit(self):
        return (not terminal._closed(self.child) or self.child_backend.requires_exit()
                or self.peers is not None and self.peers.requires_exit())

    def finish_root(self, *, primary=None):
        if primary is not None:
            self._record(primary)
        if self._busy:
            self._record(owned.OwnershipError("namespace_case_active"))
            raise self._error
        owned._need(self._children_done and not self.children_require_exit(), "namespace_child_unresolved")
        if not self._root_done:
            self._root_done = self._busy = True
            try:
                try:
                    self.root.finish(primary=self._error)
                except BaseException as error:
                    self._record(error)
                self._resource = self._resource or self.root._resource
            finally:
                self._busy = False
        if self._error is not None:
            raise self._error

    def root_requires_exit(self):
        return not terminal._closed(self.root._lease) or self.parent_backend.requires_exit()

    def snapshot(self):
        owned._need(not self._busy and not self._resource, "namespace_report_unavailable")
        return {"name": self.plan.name, "parent_share": self.plan.parent_share,
                "complete": self._complete and self._error is None, "child_create": self._creation,
                "create_winerror": self._create_error,
                "parent": self.root.snapshot(), "parent_backend": self.parent_backend.snapshot(),
                "peers": None if self.peers is None else self.peers.snapshot(),
                "child": self.child.snapshot(), "child_backend": self.child_backend.snapshot(),
                "parent_id": None if self._parent is None else self._parent.pin.file_id.hex(),
                "child_id": None if self._child is None else self._child.pin.file_id.hex(),
                "same_process_same_token": True, "path_creation_attempted": self._creation != "not_started",
                "postclose_namespace_inspected": False, "namespace_isolation_proven": False}


class CreationMatrix:
    def __init__(self, cases, guard):
        owned._need(type(cases) is tuple and len(cases) == 2 and tuple(c.plan for c in cases) == PLANS,
                    "namespace_matrix_plan")
        self.cases, self._guard = cases, guard
        self._started = self._busy = self._complete = self._resource = False
        self._error = None

    def _record(self, error):
        if self._error is None:
            self._error = error
        self._resource = self._resource or owned._resource(error)

    def run(self):
        if self._started or self._busy or self._error is not None:
            self._record(owned.OwnershipError("namespace_matrix_reused"))
            raise self._error
        self._started = self._busy = True
        try:
            for case in self.cases:
                self._guard()
                case.run()
                self._guard()
                owned._need(case._complete and case._error is None, "namespace_case_incomplete")
            self._complete = True
        except BaseException as error:
            self._record(error)
            raise self._error
        finally:
            self._busy = False

    def _finish(self, method, primary):
        if primary is not None:
            self._record(primary)
        if self._busy:
            self._record(owned.OwnershipError("namespace_matrix_active"))
            raise self._error
        self._busy = True
        try:
            for case in reversed(self.cases):
                try:
                    getattr(case, method)(primary=self._error)
                except BaseException as error:
                    self._record(error)
                self._resource = self._resource or case._resource
        finally:
            self._busy = False
        if self._error is not None:
            raise self._error

    def children_require_exit(self):
        return any(case.children_require_exit() for case in self.cases)

    def root_requires_exit(self):
        return any(case.root_requires_exit() for case in self.cases)

    def snapshot(self):
        owned._need(not self._busy and not self._resource, "namespace_matrix_report_unavailable")
        return {"collection": "complete" if self._complete and self._error is None else "incomplete",
                "consumer_payload_released": False, "cases": [case.snapshot() for case in self.cases],
                "namespace_consistency": "unresolved", "isolation_certified": False,
                "acceptance_status": "not_completed"}


class RetainedProfiledSink(peer.ProfiledSink, terminal.RetainedSink):
    pass


class NamespaceContext(terminal.WindowsHeldContext):
    def __init__(self, attempt, revision):
        super().__init__(attempt, revision)
        self.sink = RetainedProfiledSink()

    def prepare(self, guard):
        owned._need(self.reader is None, "namespace_context_reused")
        cases = []
        for plan in PLANS:
            parent = ParentBackend(self.sink._win, self.sink._api, path=str(self.attempt / plan.name),
                                   user=self.sink._user, share=plan.parent_share)
            child = empty.FileBackend(self.sink._win, self.sink._api,
                path=str(self.attempt / plan.name / "new-empty.bin"), user=self.sink._user, deny=False, share=7)
            cases.append(CreationCase(plan, parent, child, ParentPeers(parent), guard=guard))
        self.reader = CreationMatrix(tuple(cases), guard)
        self._prepared = True

    def persist_collection(self, state):
        raw = (json.dumps({"scope": "parent sharing versus path CREATE_NEW", "source_revision": self.revision,
                           "matrix": state, "initial_token_basis": self.sink.token_basis,
                           "isolation_certified": False, "acceptance_status": "not_completed"},
                           sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
        if len(raw) > 32 * 1024:
            raise MemoryError("namespace_evidence_budget")
        digest = hashlib.sha256(raw).hexdigest()
        self.sink.persist_evidence("prepare", raw, digest)
        self._evidence_bytes, self._evidence_sha = len(raw), digest

    def close_children(self, *, primary=None):
        if primary is not None:
            self._record(primary)
        if self.reader is not None:
            self.reader._finish("finish_children", primary)

    def children_require_exit(self):
        if self._parent_sd_state not in ("not_started", "freed"):
            return True
        if self.reader is not None and self.reader.children_require_exit():
            return True
        return (self.sink._started and not self.sink._connected
                or any(cell.close_state in ("pending", "unknown", "unavailable") for cell in self.sink._leases)
                or self.sink._token is not None and not terminal._closed(self.sink._token))

    def close_root(self, *, primary=None):
        if self.reader is not None:
            self.reader._finish("finish_root", primary)
        self._root_finished = True

    def root_requires_exit(self):
        return self.children_require_exit() or self.reader is not None and self.reader.root_requires_exit()

    def snapshot(self):
        report = super().snapshot()
        report["initial_token_basis"] = self.sink.token_basis
        report["source_scope"] = "two fresh case directories; source-fixture is not created"
        return report
