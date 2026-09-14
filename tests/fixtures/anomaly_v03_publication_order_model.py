"""Bounded counterfactual publication-order model. No IO or native adapter.

No isolation evidence exists here. The optional isolated-world assumption is
only for exercising later fault states; it never confers campaign acceptance.
External peer events remain observable after publisher stop or model release.
"""
import hashlib

from . import anomaly_v03_publication_model as previous

VERSION = "s4-b2-order.model.1"
MAX_PEERS = 8
MAX_PEER_EVENTS = 32
RIGHTS = frozenset(("add_child", "delete_child"))


class OrderError(ValueError):
    def __init__(self, reason):
        self.reason = reason
        super().__init__("invalid_publication_order")


def _need(condition, reason):
    if not condition:
        raise OrderError(reason)


def _marker(raw):
    _need(type(raw) is bytes and 0 < len(raw) <= previous.MAX_MARKER_BYTES, "marker_bound")


def _limits():
    return {"protected_commit_allowed": False, "future_immutability_proven": False,
            "native_publication_performed": False, "acceptance_status": "not_completed",
            "formal_permission": False, "execution_authenticated": False}


class PublicationOrder:
    """Trusted synthetic acknowledgments, not evidence that an OS action ran.

    Peer handles model a conservative possibility of parent mutation using
    preexisting access. They do not assert which Windows operations permit it.
    There is no revoke/forget/isolation-certification API.
    """
    def __init__(self, expected_marker, *, assume_isolated_for_test=False):
        _marker(expected_marker)
        _need(type(assume_isolated_for_test) is bool, "isolation_assumption")
        self._marker = expected_marker
        self._assumed = assume_isolated_for_test
        self._phase = "new"
        self._peers = {}
        self._peer_events = self._epoch = 0
        self._namespace_changed = False
        self._verified_epoch = None
        self._parent_sealed = self._resource = False
        self._error = None
        self._rename = self._commit = "not_started"
        self._written = 0

    def _latch(self, reason, *, resource=False):
        if self._error is None:
            self._error = OrderError(reason)
        self._resource = self._resource or resource
        if self._rename == "pending":
            self._rename = "unknown"
        # A historical close acknowledgment survives a later failure; it is
        # never a claim that the current namespace remains protected.
        if self._commit == "pending":
            self._commit = "unknown"

    def _require(self, condition, reason="phase_order"):
        if self._error is not None:
            raise self._error
        if not condition:
            self._latch(reason)
            raise self._error

    def _step(self, expected, new):
        self._require(self._phase == expected)
        self._phase = new

    def prepare(self):
        self._step("new", "prepared")  # Empty exclusive marker reservation.

    def seal_payload(self):
        self._step("prepared", "payload_sealed")  # Writers/children closed.

    def begin_rename(self):
        self._step("payload_sealed", "rename_pending")
        self._rename = "pending"

    def confirm_rename(self):
        self._step("rename_pending", "renamed")
        self._rename = "confirmed"

    def seal_parent(self):
        self._step("renamed", "parent_sealed")
        self._parent_sealed = True  # Does not erase peer handles/rights.

    def _peer_input(self, condition, reason):
        # External observations can arrive after local stop/release.
        if not condition:
            self._latch(reason)
            raise self._error
        if self._peer_events >= MAX_PEER_EVENTS:
            self._latch("peer_event_budget", resource=True)
            raise self._error
        self._peer_events += 1

    def record_preexisting_peer(self, handle_id, rights):
        """May be learned late; no assumption that it was opened after seal."""
        self._peer_input(type(handle_id) is int and 1 <= handle_id <= MAX_PEERS
                         and handle_id not in self._peers and type(rights) is frozenset
                         and bool(rights) and rights <= RIGHTS, "peer_handle_shape")
        self._peers[handle_id] = rights
        self._epoch += 1
        if self._phase in ("verified", "writing", "written", "flush_pending", "flushed", "close_pending", "released"):
            self._latch("peer_capability_observed")

    def peer_mutation(self, handle_id, right):
        """Model a possible add/delete even after publisher stop or release."""
        self._peer_input(type(handle_id) is int and handle_id in self._peers
                         and type(right) is str and right in self._peers[handle_id], "peer_mutation_binding")
        self._epoch += 1
        self._namespace_changed = True
        if self._phase in ("verified", "writing", "written", "flush_pending", "flushed", "close_pending", "released"):
            self._latch("peer_namespace_changed")

    def verify_final(self, *, inventory_matches, identities_match, bytes_match, descriptors_match):
        self._require(self._phase == "parent_sealed")
        values = (inventory_matches, identities_match, bytes_match, descriptors_match)
        self._require(all(type(value) is bool and value for value in values)
                      and not self._namespace_changed, "final_observation_mismatch")
        self._verified_epoch = self._epoch
        self._phase = "verified"

    def _write_gate(self):
        self._require(self._assumed and not self._peers, "isolation_unresolved")
        self._require(self._parent_sealed and self._verified_epoch == self._epoch
                      and not self._namespace_changed, "final_observation_stale")

    def begin_marker_write(self):
        self._require(self._phase == "verified")
        self._write_gate()
        self._phase = "writing"
        self._commit = "pending"  # Intent first; a lost write may have effects.

    def acknowledge_write(self, raw):
        self._require(self._phase == "writing")
        self._write_gate()
        self._require(type(raw) is bytes and 0 < len(raw) <= len(self._marker) - self._written
                      and self._marker.startswith(raw, self._written), "marker_write_mismatch")
        self._written += len(raw)
        if self._written == len(self._marker):
            self._phase = "written"

    def begin_flush(self):
        self._require(self._phase == "written")
        self._write_gate()
        self._phase = "flush_pending"

    def confirm_flush(self):
        self._step("flush_pending", "flushed")

    def begin_close(self):
        self._require(self._phase == "flushed")
        self._write_gate()
        self._phase = "close_pending"

    def confirm_close(self):
        self._step("close_pending", "released")
        self._commit = "confirmed_model_only"

    def stop(self, *, resource=False):
        if type(resource) is not bool:
            self._latch("resource_flag_shape")
            raise self._error
        self._latch("resource_stop" if resource else "operation_error", resource=resource)

    def snapshot(self):
        """Bounded detached metadata; no guarantee of allocation under OOM."""
        return {"model_version": VERSION, "phase": self._phase, "stopped": self._error is not None,
                "failure_reason": None if self._error is None else self._error.reason,
                "resource_stop": self._resource, "parent_sealed": self._parent_sealed,
                "isolation_basis": "test_assumption_only" if self._assumed else "unresolved",
                "peer_handles": [{"id": key, "rights": sorted(value)} for key, value in sorted(self._peers.items())],
                "peer_events": self._peer_events, "namespace_epoch": self._epoch,
                "verified_epoch": self._verified_epoch, "namespace_changed": self._namespace_changed,
                "final_observation_current": self._verified_epoch is not None and self._verified_epoch == self._epoch
                                             and not self._namespace_changed,
                "rename_observation": self._rename, "marker_commit_observation": self._commit,
                "marker_bytes_acknowledged": self._written, "marker_bytes_expected": len(self._marker),
                "retry_permitted": False, "cleanup_permitted": False, **_limits()}


def classify_marker(*, expected_marker, read_status, raw=None, namespace_matches=None,
                    identities_match=None, payload_bytes_match=None, descriptors_match=None):
    """One bounded synthetic reader observation; no polling or file access.

    Equality to a pinned toy marker and supplied namespace/SD observations is
    a point-in-time match only, even if the producer reported a failure.
    """
    _marker(expected_marker)
    _need(type(read_status) is str and read_status in ("absent", "sharing_violation", "read_error", "readable"), "read_status")
    checks = (namespace_matches, identities_match, payload_bytes_match, descriptors_match)
    _need(all(value is None or type(value) is bool for value in checks), "read_observation_shape")
    if read_status != "readable":
        _need(raw is None and all(value is None for value in checks), "unreadable_bytes")
        state = "indeterminate" if read_status == "read_error" else "not_ready"
    else:
        _need(type(raw) is bytes, "read_bytes_shape")
        if not raw:
            state = "not_ready"
        elif len(raw) > previous.MAX_MARKER_BYTES:
            state = "invalid"
        elif raw != expected_marker:
            state = "incomplete" if expected_marker.startswith(raw) else "invalid"
        elif any(value is False for value in checks):
            state = "invalid"
        elif any(value is None for value in checks):
            state = "indeterminate"
        else:
            state = "snapshot_matches"
    return {"observation": state, "snapshot_matches": state == "snapshot_matches",
            "expected_marker_sha256": hashlib.sha256(expected_marker).hexdigest(),
            "polling_performed": False, **_limits()}
