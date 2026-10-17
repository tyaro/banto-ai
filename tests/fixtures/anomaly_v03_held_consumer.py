"""Collect bounded bytes inside an existing sealed generation's root borrow.

Collection evidence only. Whole-namespace consistency is unresolved, so the
external consumer payload gate stays closed. No ownership or handle escapes.
"""
import ctypes as C
from dataclasses import dataclass
import hashlib
import json

from . import anomaly_v03_handle_owner as owned
from . import anomaly_v03_observed_evidence as bridge
from . import anomaly_v03_prepublication as prep
from . import anomaly_v03_publication_model as model
from . import anomaly_v03_rename_adapter as rename
from . import anomaly_v03_sealed_files as seal


@dataclass(frozen=True)
class HeldMetadata:
    handle: int
    volume: int
    file_id: bytes
    directory: bool
    descriptor: bytes
    length: int | None


class _Standard(C.Structure):
    _fields_ = [("allocation", C.c_int64), ("end", C.c_int64), ("links", C.c_uint32),
                ("pending", C.c_ubyte), ("directory", C.c_ubyte)]


class ReadStorage:
    def __init__(self, length):
        owned._need(type(length) is int and 0 <= length <= model.MAX_FILE_BYTES, "held_read_budget")
        self.length = length
        self.buffer = C.create_string_buffer(length + 1)
        self.count = C.c_uint32()
        self.attempted = self.called = self.returned = False


class WindowsHeldReadBackend:
    """Use already-bound synchronous APIs; no DLL load, path open or close.

The supplied SealedFiles generation must come from the trusted synchronous
WindowsSealBackend. This adapter does not accept asynchronous or device reads.
"""
    def __init__(self, generation):
        self.generation = generation
        owned._need(C.sizeof(_Standard) == 24 and _Standard.pending.offset == 20
                    and _Standard.directory.offset == 21, "held_standard_abi")

    def metadata(self, lease, *, guard):
        guard()
        view = lease.observed
        owned._need(view.handle == lease.handle, "held_view_binding")
        before = view.observe()  # Same-handle queries only, never _Bound.check().
        guard()
        sd = view.api.security(lease.handle)
        guard()
        descriptor = json.dumps(sd, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii")
        owned._need(0 < len(descriptor) <= prep.MAX_DESCRIPTOR_BYTES, "held_descriptor_budget")
        length = None
        if before["directory"] is False:
            info = _Standard()
            guard()
            view.api.call(view.api.k.GetFileInformationByHandleEx(lease.handle, 1, C.byref(info), C.sizeof(info)),
                          "held_standard")
            guard()
            owned._need(info.directory == 0 and info.pending == 0 and info.links == 1
                        and 0 <= info.end <= model.MAX_FILE_BYTES and info.allocation >= info.end, "held_file_state")
            length = int(info.end)
        after = view.observe()
        guard()
        owned._need(before == after, "held_metadata_changed")
        return HeldMetadata(lease.handle, before["volume"], bytes.fromhex(before["file_id"]),
                            before["directory"], descriptor, length)

    def granted_access(self, lease, *, guard):
        guard()
        access = self.generation._backend.granted_access(lease.handle)
        guard()
        return access

    def read(self, lease, storage, *, guard):
        owned._need(type(storage) is ReadStorage and not storage.attempted, "held_read_reused")
        storage.attempted = True
        guard()
        api = lease.observed.api
        api.call(api.k.SetFilePointerEx(lease.handle, 0, None, 0), "held_read_seek")
        guard()
        storage.called = True
        result = api.k.ReadFile(lease.handle, storage.buffer, len(storage.buffer), C.byref(storage.count), None)
        storage.returned = True
        owned._need(type(result) is int and -(1 << 31) <= result < 1 << 31, "held_read_response")
        api.call(result, "held_read")  # Capture native failure before another guard/API.
        guard()
        owned._need(storage.count.value == storage.length, "held_read_length")
        return storage.buffer.raw[:storage.count.value]


class HeldConsumer:
    """Single collection attempt; the original generation owns all cleanup.

Construct before seal_and_use. run() invokes that existing owner protocol and
only records success after its confirmed child closes. Raw observations remain
private evidence until a separate whole-namespace consumer gate is implemented.
"""
    MAX_GUARDS = 512

    def __init__(self, generation, backend, *, root_observation, source_revision, guard):
        owned._need(type(generation) is seal.SealedFiles and not generation._started and not generation._done
                    and type(root_observation) is prep.Observation and callable(guard), "held_consumer_shape")
        rename._pin(root_observation.pin)
        owned._need(root_observation.pin == generation._group.owner._slots[generation._root_index].pin
                    and root_observation.pin.directory and type(root_observation.descriptor) is bytes
                    and 0 < len(root_observation.descriptor) <= prep.MAX_DESCRIPTOR_BYTES, "held_root_pin")
        owned._need(type(generation._marker_index) is int, "held_marker_required")
        plans = generation._plans
        files = {plan.name: plan.raw for i, plan in enumerate(plans) if i != generation._marker_index}
        marker = plans[generation._marker_index].raw
        model.verify_marker(marker, expected_marker_sha256=generation._group.owner._journal.snapshot()["marker_sha256"],
                            source_revision=source_revision, files=files)
        self.generation, self.backend = generation, backend
        self._root = root_observation
        self._external_guard = guard
        self._storage = tuple(ReadStorage(len(plan.raw)) for plan in plans)
        self._captured = [None] * len(plans)
        self._before = [None] * len(plans)
        self._leases = generation._leases
        self._plans = plans
        self._root_lease = generation._group._leases[generation._root_index]
        self._root_view = self._root_lease.observed
        self._pins = self._views = None
        self._started = self._busy = self._done = self._verified = self._resource = False
        self._error = None
        self._guards = 0

    def _record(self, error):
        if self._error is None:
            self._error = error
        self._resource = self._resource or owned._resource(error)
        try:
            self.generation._record(error)
        except BaseException as later:
            self._resource = self._resource or owned._resource(later)

    def _upstream(self):
        files, owner = self.generation, self.generation._group.owner
        primary = owner._first_error if owner._first_error is not None else files._error
        self._resource = self._resource or files._resource or owner._resource_stop
        try:
            state = owner._journal.snapshot()
        except BaseException as later:
            self._resource = self._resource or owned._resource(later)
            if primary is not None:
                raise primary
            raise
        self._resource = self._resource or state["resource_stop"]
        # The owner sees generation rejections too, so its first error is the
        # oldest upstream failure even if the final guard swallowed it.
        if primary is not None:
            raise primary
        if self._resource:
            raise MemoryError("held_upstream_resource_stop")
        owned._need(not owner._started and not owner._done and state["teardown"] == "not_started"
                    and state["model_status"] in ("not_started", "in_progress"), "held_upstream_stopped")

    def _guard(self):
        if self._error is not None:
            raise self._error
        owned._need(self._busy and not self._done and self._pins is not None, "held_consumer_not_active")
        if self._guards >= self.MAX_GUARDS:
            raise MemoryError("held_guard_budget")
        self._guards += 1
        owned._need(self._external_guard() is None, "held_guard_response")
        if self._error is not None:
            raise self._error
        self._upstream()
        files = self.generation
        if files._error is not None:
            raise files._error
        owned._need(files._busy and not files._done and files._continuation == "pending"
                    and files._group.owner._busy and files._leases is self._leases
                    and files._plans is self._plans, "held_borrow_not_active")
        bridge._observation_ready(self._root_lease)
        owned._need(self._root_lease.handle == self._root.pin.handle
                    and self._root_lease.observed is self._root_view and self._root_lease._custodian is files._group
                    and files._group.owner._states[files._root_index] == "owned", "held_root_lifetime")
        for index, (lease, observation, view) in enumerate(zip(self._leases, self._pins.observations, self._views)):
            bridge._observation_ready(lease)
            owned._need(lease.handle == observation.pin.handle and lease.observed is view
                        and view.handle == lease.handle and lease._custodian is None
                        and files._seal_states[index] == "verified" and files._sealed[index] is observation,
                        "held_child_lifetime")

    @staticmethod
    def _match(metadata, observation, length):
        pin = observation.pin
        owned._need(type(metadata) is HeldMetadata and type(metadata.handle) is int
                    and type(metadata.volume) is int and type(metadata.file_id) is bytes
                    and type(metadata.directory) is bool and type(metadata.descriptor) is bytes
                    and (metadata.length is None if length is None else type(metadata.length) is int)
                    and (metadata.handle, metadata.volume, metadata.file_id, metadata.directory,
                         metadata.descriptor, metadata.length)
                    == (pin.handle, pin.volume, pin.file_id, pin.directory, observation.descriptor, length), "held_pin_changed")

    def _capture(self, pins):
        try:
            owned._need(self._busy and self._pins is None and type(pins) is seal.SealedPins
                        and pins.parent == self._root.pin and pins.marker_index == self.generation._marker_index
                        and pins.observations == tuple(self.generation._sealed)
                        and len(pins.observations) == len(self._leases), "held_continuation_binding")
            self._pins = pins
            self._views = tuple(lease.observed for lease in self._leases)
            self._guard()
            root_before = self.backend.metadata(self._root_lease, guard=self._guard)
            self._guard()
            self._match(root_before, self._root, None)
            # Validate every child before reading the first byte.
            for i, (lease, observation, plan) in enumerate(zip(self._leases, pins.observations, self.generation._plans)):
                metadata = self.backend.metadata(lease, guard=self._guard)
                self._guard()
                self._match(metadata, observation, len(plan.raw))
                access = self.backend.granted_access(lease, guard=self._guard)
                self._guard()
                owned._need(type(access) is int and access == seal.access_for(plan), "held_access_changed")
                self._before[i] = metadata
            for i, (lease, observation, plan) in enumerate(zip(self._leases, pins.observations, self.generation._plans)):
                self._guard()
                actual = self.backend.read(lease, self._storage[i], guard=self._guard)
                self._guard()
                owned._need(type(actual) is bytes and len(actual) == len(plan.raw) and actual == plan.raw
                            and hashlib.sha256(actual).hexdigest() == observation.pin.content_sha256, "held_bytes_changed")
                self._captured[i] = actual
            # Every original lease remains live through the final metadata pass.
            for i, lease in enumerate(self._leases):
                metadata = self.backend.metadata(lease, guard=self._guard)
                self._guard()
                self._match(metadata, pins.observations[i], len(self._plans[i].raw))
                owned._need(metadata == self._before[i], "held_postread_changed")
                access = self.backend.granted_access(lease, guard=self._guard)
                self._guard()
                owned._need(type(access) is int and access == seal.access_for(self._plans[i]), "held_access_changed")
            root_after = self.backend.metadata(self._root_lease, guard=self._guard)
            self._guard()
            self._match(root_after, self._root, None)
            owned._need(root_after == root_before, "held_root_changed")
            self._verified = True
        except BaseException as error:
            self._record(error)
            raise self._error

    def run(self):
        entered = False
        try:
            owned._need(not self._started and not self._busy and not self._done, "held_consumer_reused")
            self._started = self._busy = entered = True
            owned._need(self._external_guard() is None, "held_guard_response")
            if self._error is not None:
                raise self._error
            self._upstream()
            self.generation.seal_and_use(self._capture)
            # No native IO here: the enclosing borrow has returned and all
            # child close acknowledgments must be present before completion.
            owned._need(self._verified and self.generation._done and self.generation._continuation == "returned"
                        and all(lease.close_state == "closed" and lease._error is None for lease in self._leases),
                        "held_collection_close_unconfirmed")
            owned._need(self._external_guard() is None, "held_guard_response")
            if self._error is not None:
                raise self._error
        except BaseException as error:
            self._record(error)
        finally:
            if entered:
                self._busy = False
                self._done = True
                try:
                    self._upstream()
                except BaseException as error:
                    self._record(error)
                if self._error is not None:
                    for i in range(len(self._captured)):
                        self._captured[i] = None
        if self._error is not None:
            raise self._error

    def consumer_payload(self):
        if self._error is not None:
            raise self._error
        raise owned.OwnershipError("held_consumer_isolation_unresolved")

    def requires_exit(self):
        # A future caller must retain the parent when an original child close
        # remains unknown. This component never takes over parent cleanup.
        for lease in self._leases:
            if lease.state != "not_started" and lease.close_state not in ("closed", "not_needed"):
                return True
        return self._root_lease.close_state in ("pending", "unknown", "unavailable")

    def snapshot(self):
        owned._need(not self._busy and not self._resource, "held_report_unavailable")
        return {"collection": "complete" if self._done and self._verified and self._error is None else "incomplete",
                "finished": self._done, "stopped": self._error is not None,
                "failure_reason": None if self._error is None else getattr(self._error, "reason", type(self._error).__name__),
                "guards": self._guards, "files": [{"name": plan.name, "byte_count": len(plan.raw),
                    "captured_sha256": None if raw is None else hashlib.sha256(raw).hexdigest(),
                    "close_state": lease.close_state} for plan, raw, lease in zip(self.generation._plans, self._captured, self._leases)],
                "consumer_payload_released": False, "namespace_consistency": "unresolved",
                "worker_exit_required": self.requires_exit(),
                "consumer_path_reopened": False, "consumer_handles_acquired": 0,
                "consumer_handles_closed": 0, "isolation_certified": False, "protected_commit_allowed": False,
                "future_immutability_proven": False, "native_publication_performed": False,
                "formal_permission": False, "execution_authenticated": False, "acceptance_status": "not_completed"}
