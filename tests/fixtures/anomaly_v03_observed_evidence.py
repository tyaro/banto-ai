"""Shared acquisition close authority and native observation-to-barrier bridge.

Trusted synchronous engineering adapters only. No acquisition or DLL loading here.
The caller retains this holder before adopt(), so lost adoption replies do not
lose the receiver. Each TrackedOpen remains the sole caller of raw CloseHandle.
"""
import hashlib
import json

from . import anomaly_v03_handle_owner as owned
from . import anomaly_v03_prepublication as prep
from . import anomaly_v03_publication_model as model
from . import anomaly_v03_rename_adapter as rename
from .anomaly_v03_tracked_open import TrackedOpen


class AcquiredOwner:
    def __init__(self):
        self.active = False
        self._attempted = False
        self._owner = None
        self._leases = ()

    def adopt(self, *, leases, journal, observations, parents):
        if self._attempted:
            error = owned.OwnershipError("adoption_reused")
            if self.active:
                self.reject(error)
            raise error
        self._attempted = True
        owned._need(type(leases) is tuple and type(observations) is tuple and type(parents) is tuple
                    and 0 < len(leases) <= owned.MAX_HANDLES
                    and len(leases) == len(observations) == len(parents), "adoption_shape")
        for lease, observation in zip(leases, observations):
            owned._need(type(lease) is TrackedOpen and lease.state == "ready"
                        and lease.close_state == "not_started" and lease._error is None
                        and lease._custodian is None, "acquisition_not_available")
            owned._need(type(observation) is prep.Observation and lease.handle == observation.pin.handle,
                        "adoption_pin")
        slots = tuple(owned.OwnedSlot(observation.pin, parent)
                      for observation, parent in zip(observations, parents))
        # Validate graph and allocate owner state while the caller still owns.
        owner = owned.HandleOwner(self, journal=journal, slots=slots)
        self._leases, self._owner = leases, owner
        # No native calls/callbacks in the handover. Until the single active
        # transition, close() on every source cell still belongs to the caller.
        for lease in leases:
            lease._custodian = self
        self.active = True

    @property
    def owner(self):
        owned._need(self.active and self._owner is not None, "adoption_not_active")
        return self._owner

    def reject(self, error):
        self._owner._record(error)
        self._owner._stop_safely()

    def close_handle(self, handle):
        owned._need(self.active, "adoption_not_active")
        for lease in self._leases:
            if lease.handle == handle:
                lease._close_owned(self)
                return 1
        raise owned.OwnershipError("unregistered_close")

    def get_last_error(self):
        raise owned.OwnershipError("unexpected_close_error_query")

    def finish(self, *, primary=None):
        if self.active:
            return self._owner.finish(primary=primary)
        # Failed before activation: source cells remain caller-owned. No raw
        # close here, and callers retain all their original acquisition cells.
        if primary is not None:
            raise primary


def _observation_ready(lease, guard=None):
    if guard is not None:
        guard()
    owned._need(type(lease) is TrackedOpen, "observation_lease_type")
    if lease._error is not None:
        raise lease._error
    owned._need(lease.state == "ready" and lease.close_state == "not_started", "observation_not_owned")
    if lease._custodian is not None and lease._custodian.active:
        owner = lease._custodian.owner
        if owner._first_error is not None:
            raise owner._first_error
        state = owner._journal.snapshot()
        if owner._resource_stop or state["resource_stop"]:
            raise MemoryError("observation_resource_stop")
        owned._need(not owner._started and state["model_status"] in ("not_started", "in_progress"),
                    "observation_owner_stopped")


def inspect_native(lease, *, expected=None, private_user=None, guard=None, security_mode="private"):
    """Read one already-held _Bound view; never open a writer or change DACL.

    expected is exact file bytes; directories require None. The descriptor is
    canonical JSON of the existing Win.security observation, not a binary SD
    nor evidence of independent-token enforcement.
    """
    _observation_ready(lease, guard)
    owned._need(security_mode in ("private", "frozen"), "observation_security_mode")
    view = lease.observed
    owned._need(view.handle == lease.handle, "observation_handle_mismatch")
    before = view.check()
    _observation_ready(lease, guard)
    owned._need(type(before) is dict and type(before["directory"]) is bool, "observation_shape")
    if before["directory"]:
        owned._need(expected is None, "directory_bytes")
        digest = None
    else:
        owned._need(type(expected) is bytes and len(expected) <= model.MAX_FILE_BYTES, "file_bytes")
        actual = view.read()
        _observation_ready(lease, guard)
        owned._need(actual == expected, "native_bytes_mismatch")
        digest = hashlib.sha256(actual).hexdigest()
    security = view.api.security(lease.handle)
    _observation_ready(lease, guard)
    if private_user is not None:
        from banto_ai import _anomaly_v03_windows as win
        win._verify_sd(security, private_user, security_mode, before["directory"])
    _observation_ready(lease, guard)
    descriptor = json.dumps(security, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii")
    owned._need(0 < len(descriptor) <= prep.MAX_DESCRIPTOR_BYTES, "descriptor_budget")
    after = view.check()
    _observation_ready(lease, guard)
    owned._need(after == before, "observation_interrupted")
    pin = rename.ObjectPin(lease.handle, before["volume"], bytes.fromhex(before["file_id"]),
                           before["directory"], digest)
    rename._pin(pin)
    return prep.Observation(pin, descriptor)


def capture_record(group, step, *, source_revision, files, marker, bindings, private_indices, user):
    """Bind every live file slot to exactly one payload name or None (marker).

    All owner slots must still be owned. This first bridge captures prepare
    before any selective release; later-phase refresh/reacquisition is separate.
    """
    def capture(pins):
        owned._need(type(bindings) is tuple and type(private_indices) is tuple, "binding_shape")
        owned._need(type(user) is str and bool(user), "private_user")
        model.verify_marker(marker, expected_marker_sha256=group.owner._journal.snapshot()["marker_sha256"],
                            source_revision=source_revision, files=files)
        expected_slots = {i for i, pin in enumerate(pins) if not pin.directory}
        mapping = {}
        names = []
        for pair in bindings:
            owned._need(type(pair) is tuple and len(pair) == 2, "binding_shape")
            index, name = pair
            owned._need(type(index) is int and index in expected_slots and index not in mapping
                        and (name is None or type(name) is str and name in files), "file_binding")
            mapping[index] = marker if name is None else files[name]
            names.append(name)
        owned._need(set(mapping) == expected_slots and len(names) == len(files) + 1
                    and names.count(None) == 1 and set(names) == set(files) | {None}, "binding_inventory")
        owned._need(len(set(private_indices)) == len(private_indices)
                    and all(type(i) is int and 0 <= i < len(pins) for i in private_indices)
                    and expected_slots.issubset(private_indices), "private_selection")
        observations = tuple(inspect_native(lease, expected=mapping.get(index),
                                            private_user=user if index in private_indices else None)
                             for index, lease in enumerate(group._leases))
        owned._need(all(observation.pin == pin for observation, pin in zip(observations, pins)),
                    "adopted_identity_changed")
        return prep.build_evidence(step, source_revision=source_revision, files=files,
                                   marker=marker, observations=observations)
    owned._need(type(group) is AcquiredOwner, "acquired_owner_type")
    return group.owner.borrowed(tuple(range(len(group._leases))), capture)
