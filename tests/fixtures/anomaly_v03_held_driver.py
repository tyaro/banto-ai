"""Bounded held-reader driver and fresh-fixture context; no native entry point.

Trusted synchronous callbacks only. Retain this context until worker exit when
any child/root/ancestor close is unknown. Reports never release consumer bytes.
"""
import ctypes as C
import hashlib
import json

from . import anomaly_v03_directory_driver as acquisition
from . import anomaly_v03_handle_owner as owned
from . import anomaly_v03_held_consumer as held
from . import anomaly_v03_observed_evidence as bridge
from . import anomaly_v03_prepublication as prep
from . import anomaly_v03_publication_model as model
from . import anomaly_v03_reader_reacquisition as reopen
from . import anomaly_v03_sealed_files as seal
from .anomaly_v03_private_sink import WindowsPrivateSink


class HeldDriver:
    MAX_REPORT_BYTES = 256 * 1024

    def __init__(self, context):
        self.context = context
        self._started = self._busy = self._done = self._resource = False
        self._verified = self._retained = False
        self._error = None
        self._phase = self._evidence = "not_started"

    def _record(self, error):
        if self._error is None:
            self._error = error
        self._resource = self._resource or owned._resource(error)

    def _sync(self):
        # Error recording never calls an allocating status/report callback.
        try:
            primary, resource = self.context.status()
            owned._need((primary is None or isinstance(primary, BaseException)) and type(resource) is bool,
                        "held_driver_status_response")
            if primary is not None:
                self._record(primary)
            self._resource = self._resource or resource
            if resource and self._error is None:
                self._record(MemoryError("held_driver_resource_stop"))
        except BaseException as error:
            self._record(error)

    def _guard(self):
        self._sync()
        if self._error is not None:
            raise self._error
        owned._need(self._busy and not self._done, "held_driver_not_active")
        owned._need(self.context.guard() is None, "held_driver_guard_response")
        self._sync()
        if self._error is not None:
            raise self._error

    def run(self):
        entered = False
        try:
            owned._need(not self._started and not self._busy and not self._done, "held_driver_reused")
            self._started = self._busy = entered = True
            self._sync()
            if self._error is not None:
                raise self._error
            self._phase = "connect"
            owned._need(self.context.connect() is None, "held_driver_connect_response")
            self._guard()
            self._phase = "prepare"
            owned._need(self.context.prepare(self._guard) is None, "held_driver_prepare_response")
            self._guard()
            self._phase = "collect"
            owned._need(self.context.reader.run() is None, "held_driver_read_response")
            self._guard()
            state = self.context.reader.snapshot()
            owned._need(state["collection"] == "complete" and state["consumer_payload_released"] is False,
                        "held_driver_collection_incomplete")
            self._verified = True
            self._phase = "evidence"
            self._evidence = "pending"
            owned._need(self.context.persist_collection(state) is None, "held_driver_evidence_response")
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

    def _unknown(self, query):
        # A failed lifetime query never authorizes releasing a parent.
        try:
            value = query()
            owned._need(type(value) is bool, "held_driver_lifetime_response")
            return value
        except BaseException as error:
            self._record(error)
            return True

    def _close(self, operation):
        try:
            owned._need(operation(primary=self._error) is None, "held_driver_close_response")
        except BaseException as error:
            self._record(error)
        self._sync()

    def finish(self):
        if self._busy:
            self._record(owned.OwnershipError("held_driver_active"))
            raise self._error
        if not self._done:
            self._busy = True
            try:
                self._close(self.context.close_children)
                self._retained = self._unknown(self.context.children_require_exit)
                if not self._retained:
                    self._close(self.context.close_root)
                    self._retained = self._unknown(self.context.root_requires_exit)
                if not self._retained:
                    self._close(self.context.close_ancestors)
                    self._retained = self._unknown(self.context.requires_exit)
                self._sync()
                if self._retained and self._error is None:
                    self._record(owned.OwnershipError("held_driver_worker_exit"))
            finally:
                self._busy = False
                self._done = True
        if self._error is not None:
            raise self._error

    def exit_code(self):
        # No callbacks or report allocation may change the termination choice.
        if self._resource:
            return 80
        if self._retained:
            return 81
        return 0 if (self._started and self._done and not self._busy and self._error is None
                     and self._verified and self._evidence == "saved") else 1

    def report_bytes(self):
        entered = False
        try:
            owned._need(self._done and not self._busy and not self._resource, "held_driver_report_unavailable")
            self._busy = entered = True
            before = self._error
            context = self.context.snapshot()
            self._sync()
            owned._need(self._error is before and not self._resource, "held_driver_report_interrupted")
            # exit_code deliberately refuses success while an operation is busy.
            complete = self._started and self._error is None and self._verified and self._evidence == "saved" and not self._retained
            report = {"held_driver": "complete" if complete else "failed",
                      "phase": self._phase, "evidence": self._evidence,
                      "collection_verified": self._verified,
                      "error_type": None if self._error is None else type(self._error).__name__,
                      "error_reason": None if self._error is None else getattr(self._error, "reason", None),
                      "retained_for_worker_exit": self._retained, "context": context,
                      "consumer_payload_released": False, "namespace_consistency": "unresolved",
                      "isolation_certified": False, "protected_commit_allowed": False,
                      "future_immutability_proven": False, "native_publication_performed": False,
                      "formal_permission": False, "execution_authenticated": False,
                      "acceptance_status": "not_completed"}
            raw = (json.dumps(report, sort_keys=True, ensure_ascii=True) + "\n").encode("ascii")
            if len(raw) > self.MAX_REPORT_BYTES:
                raise MemoryError("held_driver_report_budget")
            owned._need(self._error is before and not self._resource, "held_driver_report_interrupted")
            return raw
        except BaseException as error:
            self._record(error)
            raise self._error
        finally:
            if entered:
                self._busy = False


class RetainedSink(WindowsPrivateSink):
    def finish(self, *, primary=None):
        # Bootstrap failure must not close ancestors below an unknown child.
        # The containing driver owns terminal traversal, including partial setup.
        if primary is not None:
            raise primary


def _closed(lease):
    return lease.state == "not_started" or lease.close_state in ("closed", "not_needed")


class WindowsHeldContext(acquisition.WindowsAcquisitionContext):
    MAX_POINTS = 1024

    def __init__(self, attempt, revision):
        super().__init__(attempt, revision)
        self.sink, self.source = RetainedSink(), RetainedSink()
        self.group = bridge.AcquiredOwner()
        self.reader = self.generation = None
        self._primary = None
        self._resource = self._retained = self._prepared = False
        self._children_finished = self._root_finished = self._ancestors_finished = False
        self._source_root = None
        self._prepare_bytes = self._prepare_sha = None

    def _record(self, error):
        if self._primary is None:
            self._primary = error
        self._resource = self._resource or owned._resource(error)

    def status(self):
        primary = self._primary
        resource = self._resource or self.source._resource or self.sink._resource or self._parent_sd_resource
        if self.group.active:
            owner = self.group.owner
            primary = primary if primary is not None else owner._first_error
            resource = resource or owner._resource_stop
        if self.reader is not None:
            primary = primary if primary is not None else self.reader._error
            resource = resource or self.reader._resource
        if self.generation is not None:
            primary = primary if primary is not None else self.generation._error
            resource = resource or self.generation._resource
            for lease in self.generation._leases:
                resource = resource or lease.resource_stop
        return primary, resource

    def resource_stop(self):
        return self.status()[1]

    def guard(self):
        primary, resource = self.status()
        if primary is not None:
            raise primary
        if resource:
            raise MemoryError("held_context_resource_stop")
        super().guard()  # Bounded resources and original external ancestor pins.
        if self.group.active:
            state = self.group.owner._journal.snapshot()
            if state["resource_stop"]:
                self._resource = True
                raise MemoryError("held_context_journal_resource")
            owned._need(state["model_status"] in ("not_started", "in_progress")
                        and state["teardown"] == "not_started", "held_context_journal_stopped")

    def prepare(self, guard):
        owned._need(not self.source._started and self.reader is None, "held_context_reused")
        guard()
        self.source.connect(self.source_path)
        self._source_root = self.source._leases[-1]
        guard()
        source = self.source
        files = {"facts.json": b'{"scope":"held_consumer_probe","count":2}\n'}
        marker = model.marker_bytes(self.revision, files)
        journal = model.PublicationJournal(hashlib.sha256(marker).hexdigest())
        selected = [self._source_root]
        inputs = (("facts.json", files["facts.json"]), ("marker-pending.json", marker))
        for name, raw in inputs:
            owned._need(len(raw) <= 4096, "held_context_fixture_budget")
            guard()
            buffer, written = C.create_string_buffer(raw), source._win.D()
            lease = source._open(source._root / name, directory=False, create=True)
            selected.append(lease)
            guard()
            source._win._verify_sd(source._api.security(lease.handle), source._user, "private", False)
            guard()
            source._api.call(source._api.k.WriteFile(lease.handle, buffer, len(raw), C.byref(written), None), "held_fixture_write")
            owned._need(written.value == len(raw), "held_fixture_short_write")
            guard()
            source._api.call(source._api.k.FlushFileBuffers(lease.handle), "held_fixture_flush")
            guard()
        observations = tuple(bridge.inspect_native(lease, expected=raw, private_user=source._user, guard=guard)
                             for lease, raw in zip(selected, (None, files["facts.json"], marker)))
        self.group.adopt(leases=tuple(selected), journal=journal, observations=observations, parents=(None, 0, 0))
        guard()
        plans = tuple(reopen.ReadPlan(index, name, raw, observations[index])
                      for index, (name, raw) in enumerate(inputs, 1))
        self.generation = seal.SealedFiles(seal.WindowsSealBackend(source), group=self.group, root_index=0,
                                           plans=plans, user=source._user)
        self.reader = held.HeldConsumer(self.generation, held.WindowsHeldReadBackend(self.generation),
            root_observation=observations[0], source_revision=self.revision, guard=guard)
        journal.begin("prepare")
        record = bridge.capture_record(self.group, "prepare", source_revision=self.revision, files=files, marker=marker,
                                       bindings=((1, "facts.json"), (2, None)), private_indices=(0, 1, 2), user=source._user)
        if len(record.raw) > 64 * 1024:
            raise MemoryError("held_prepare_evidence_budget")
        guard()
        barrier = prep.EvidenceBarrier(self.sink, owner=self.group.owner, protected=(0,))
        barrier.save_and_release(record, (1, 2))
        guard()
        owned._need(barrier.snapshot()["steps"][0]["state"] == "released", "held_prepare_not_released")
        self._prepare_bytes, self._prepare_sha = len(record.raw), record.sha256
        self._prepared = True

    def persist_collection(self, state):
        raw = (json.dumps({"scope": "held-handle collection evidence only", "source_revision": self.revision,
                           "collection": state, "prepare_sha256": self._prepare_sha,
                           "acceptance_status": "not_completed"}, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
        owned._need(len(raw) <= 16 * 1024, "held_collection_evidence_budget")
        digest = hashlib.sha256(raw).hexdigest()
        # Storage slot name only: no publication-journal seal_payload transition.
        self.sink.persist_evidence("seal_payload", raw, digest)
        self._evidence_bytes, self._evidence_sha = len(raw), digest

    def _close_lease(self, lease):
        if _closed(lease):
            return True
        try:
            lease.close()
        except BaseException as error:
            self._record(error)
        self._resource = self._resource or lease.resource_stop
        return _closed(lease)

    def close_children(self, *, primary=None):
        if primary is not None:
            self._record(primary)
        if self._children_finished:
            return
        self._children_finished = True
        if self.generation is not None and not self.generation._done:
            try:
                self.generation.finish(primary=primary)
            except BaseException as error:
                self._record(error)
        if self.group.active:
            # Before writer-release confirmation retain the whole adopted tree;
            # HandleOwner.finish otherwise closes a parent after unknown child.
            if any(not _closed(lease) for lease in self.group._leases[1:]):
                self._retained = True
        elif self._source_root is not None:
            for lease in reversed(self.source._leases):
                if lease is self._source_root:
                    break
                if not self._close_lease(lease):
                    self._retained = True
                    break

    def children_require_exit(self):
        if self._retained or self._parent_sd_state not in ("not_started", "freed"):
            return True
        if self.reader is not None and self.reader.requires_exit():
            return True
        for sink in (self.source, self.sink):
            if sink._started and not sink._connected:
                return True  # Includes unconfirmed directory bootstrap.
            if any(lease.close_state in ("pending", "unknown", "unavailable") for lease in sink._leases):
                return True
            if sink._token is not None and not _closed(sink._token):
                return True
        return False

    def close_root(self, *, primary=None):
        if self._root_finished:
            return
        self._root_finished = True
        if self.group.active:
            try:
                self.group.finish(primary=primary)
            except BaseException as error:
                self._record(error)
        elif self._source_root is not None:
            self._close_lease(self._source_root)

    def root_requires_exit(self):
        return self.children_require_exit() or self._source_root is not None and not _closed(self._source_root)

    def close_ancestors(self, *, primary=None):
        if self._ancestors_finished:
            return
        self._ancestors_finished = True
        for sink in (self.source, self.sink):
            for lease in reversed(sink._leases):
                if _closed(lease):
                    continue
                if not self._close_lease(lease):
                    self._retained = True
                    return  # No ancestor release after an unconfirmed close.
            sink._finished = True
        self._finished = True

    def requires_exit(self):
        return self.root_requires_exit() or any(not _closed(lease) for sink in (self.source, self.sink)
                                                for lease in sink._leases)

    def snapshot(self):
        return {"prepared": self._prepared, "prepare_bytes": self._prepare_bytes, "prepare_sha256": self._prepare_sha,
                "collection_evidence_bytes": self._evidence_bytes, "collection_evidence_sha256": self._evidence_sha,
                "source": self.source.snapshot(), "sink": self.sink.snapshot(), "resources": list(self._points),
                "root_finished": self._root_finished, "ancestors_finished": self._finished,
                "postclose_source_inspected": False, "source_cleanup_performed": False}
