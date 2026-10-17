"""Bounded synthetic file-hold intervals, never a native isolation certificate.

Open/close/read replies are trusted model events. No IO, timers, callbacks,
OS handles, account changes, or publisher permissions are provided here.
"""
from dataclasses import dataclass
import hashlib
import re

from . import anomaly_v03_publication_order_model as order
from . import anomaly_v03_sealed_files as sealed

VERSION = "s4-b2-retention.model.1"
MAX_FILES, MAX_SLOTS, MAX_EVENTS = 8, 24, 128
MAX_FILE_BYTES, MAX_DESCRIPTOR_BYTES = 65536, 8192
READER = 0x120081
WRITER = 0x120083
# Deliberately restricted to these existing file roles, not a general Win32 ACL model.
ACCESS = {READER: 1, WRITER: 3, sealed.FILE_SEAL_ACCESS: 1, sealed.MARKER_SEAL_ACCESS: 5}


@dataclass(frozen=True)
class FilePin:
    name: str
    volume: int
    file_id: bytes
    raw: bytes
    descriptor: bytes


def share_compatible(access, share, other_access, other_share):
    """Bilateral data read/write/delete sharing only; no ACL or API success claim."""
    order._need(all(type(value) is int for value in (access, share, other_access, other_share))
                and access in ACCESS and other_access in ACCESS and 0 <= share <= 7 and 0 <= other_share <= 7,
                "sharing_shape")
    return not (ACCESS[access] & ~other_share or ACCESS[other_access] & ~share)


class RetentionWindow:
    def __init__(self, pins, *, marker_name, assume_other_boundaries_stable_for_test=False):
        order._need(type(pins) is tuple and 2 <= len(pins) <= MAX_FILES, "retention_pins")
        names, identities = set(), set()
        for pin in pins:
            order._need(type(pin) is FilePin and type(pin.name) is str
                        and re.fullmatch(r"[a-z][a-z0-9_.-]{0,63}", pin.name) is not None
                        and pin.name not in names and type(pin.volume) is int and 0 < pin.volume < 1 << 64
                        and type(pin.file_id) is bytes and len(pin.file_id) == 16 and any(pin.file_id)
                        and (pin.volume, pin.file_id) not in identities
                        and type(pin.raw) is bytes and len(pin.raw) <= MAX_FILE_BYTES
                        and type(pin.descriptor) is bytes and 0 < len(pin.descriptor) <= MAX_DESCRIPTOR_BYTES,
                        "retention_pin")
            names.add(pin.name)
            identities.add((pin.volume, pin.file_id))
        order._need(type(marker_name) is str and marker_name in names
                    and type(assume_other_boundaries_stable_for_test) is bool, "retention_basis")
        self._pins = {pin.name: pin for pin in pins}
        order._marker(self._pins[marker_name].raw)
        self._marker_name = marker_name
        self._assumed = assume_other_boundaries_stable_for_test
        self._slots = {}
        self._events = 0
        self._error = None
        self._resource = False
        self._phase = "new"
        self._publication_started = False
        self._publication_gaps = set()
        self._window_gaps = set()
        self._reads = {}
        self._result = None
        self._external_change = False

    def _latch(self, reason, *, resource=False):
        if self._error is None:
            self._error = order.OrderError(reason)
        self._resource = self._resource or resource

    def _need(self, condition, reason):
        if self._error is not None:
            raise self._error
        if not condition:
            self._latch(reason)
            raise self._error

    def _event(self, *, teardown=False):
        if not teardown:
            self._need(True, "stopped")
        if self._events >= MAX_EVENTS:
            self._latch("retention_event_budget", resource=True)
            raise self._error
        self._events += 1

    def _slot(self, slot, state):
        self._need(type(slot) is int and slot in self._slots and self._slots[slot]["state"] == state,
                   "retention_slot_state")
        return self._slots[slot]

    def _missing(self):
        missing = set()
        for name in self._pins:
            for label, bit in (("delete", 4), ("data_write", 2)):
                if not any(row["name"] == name and row["state"] == "held" and not row["share"] & bit
                           for row in self._slots.values()):
                    missing.add((name, label))
        return missing

    def _track_gaps(self):
        missing = self._missing()
        if self._publication_started and self._phase != "observed":
            self._publication_gaps.update(missing)
        if self._phase == "reading":
            self._window_gaps.update(missing)

    def begin_open(self, slot, name, *, access=READER, share=1):
        self._event()
        self._need(type(slot) is int and 1 <= slot <= MAX_SLOTS and slot not in self._slots
                   and type(name) is str and name in self._pins
                   and type(access) is int and access in ACCESS and type(share) is int and 0 <= share <= 7,
                   "retention_open_shape")
        self._slots[slot] = {"name": name, "access": access, "share": share, "state": "opening"}

    def confirm_open(self, slot, *, volume, file_id, granted_access):
        self._event()
        row = self._slot(slot, "opening")
        pin = self._pins[row["name"]]
        self._need(type(volume) is int and volume == pin.volume and type(file_id) is bytes and file_id == pin.file_id
                   and type(granted_access) is int and granted_access == row["access"], "retention_open_binding")
        for other in self._slots.values():
            if other is not row and other["name"] == row["name"] and other["state"] != "closed":
                self._need(other["state"] == "held" and share_compatible(row["access"], row["share"],
                           other["access"], other["share"]), "retention_sharing_conflict_or_unknown")
        row["state"] = "held"
        self._track_gaps()  # A later reopen cannot erase earlier gaps.

    def begin_close(self, slot):
        # Teardown is still recordable after stop; this never calls CloseHandle.
        self._event(teardown=True)
        if not (type(slot) is int and slot in self._slots and self._slots[slot]["state"] == "held"):
            self._latch("retention_close_state")
            raise self._error
        self._slots[slot]["state"] = "closing"
        self._track_gaps()  # Stop relying on a handle as soon as close may execute.

    def confirm_close(self, slot):
        self._event(teardown=True)
        if not (type(slot) is int and slot in self._slots and self._slots[slot]["state"] == "closing"):
            self._latch("retention_close_state")
            raise self._error
        self._slots[slot]["state"] = "closed"

    def start_publication_interval(self):
        self._event()
        self._need(not self._publication_started and self._phase == "new", "retention_publication_order")
        self._publication_started = True
        self._track_gaps()

    def begin_observation(self):
        self._event()
        self._need(self._publication_started and self._phase == "new", "retention_observation_order")
        self._phase = "reading"
        self._track_gaps()

    def observe(self, slot, *, volume, file_id, raw, descriptor):
        self._event()
        self._need(self._phase == "reading", "retention_observation_order")
        row = self._slot(slot, "held")
        pin = self._pins[row["name"]]
        self._need(row["name"] not in self._reads and type(volume) is int and volume == pin.volume
                   and type(file_id) is bytes and file_id == pin.file_id
                   and type(raw) is bytes and len(raw) <= MAX_FILE_BYTES and raw == pin.raw
                   and type(descriptor) is bytes and len(descriptor) <= MAX_DESCRIPTOR_BYTES
                   and descriptor == pin.descriptor, "retention_read_binding")
        self._reads[row["name"]] = raw  # Return these exact checked bytes, no path reread.

    def finish_observation(self):
        self._event()
        self._need(self._phase == "reading" and len(self._reads) == len(self._pins), "retention_incomplete_read")
        self._need(not self._unresolved(), "retention_operation_unresolved")
        self._track_gaps()
        self._result = ("common_interval_model_only" if not self._window_gaps and self._assumed
                        else "observations_match_only")
        self._phase = "observed"
        return self._result

    def checked_payload(self):
        self._need(self._phase == "observed" and self._result == "common_interval_model_only", "retention_delivery_unresolved")
        self._need(not self._unresolved(), "retention_operation_unresolved")
        return tuple((name, self._reads[name]) for name in self._pins if name != self._marker_name)

    def _unresolved(self):
        return any(row["state"] in ("opening", "closing") for row in self._slots.values())

    def record_external_change(self):
        # Can invalidate a completed read after publisher stop/close; no ABA reset.
        self._event(teardown=True)
        self._external_change = True
        self._latch("retention_external_change")

    def stop(self, *, resource=False):
        if type(resource) is not bool:
            self._latch("retention_resource_shape")
            raise self._error
        self._latch("retention_resource_stop" if resource else "retention_operation_error", resource=resource)

    def snapshot(self):
        return {"model_version": VERSION, "phase": self._phase, "events": self._events,
                "stopped": self._error is not None, "resource_stop": self._resource,
                "failure_reason": None if self._error is None else self._error.reason,
                "slots": [{"slot": slot, **row} for slot, row in self._slots.items()],
                "unresolved_open_or_close": self._unresolved(),
                "publication_interval_started": self._publication_started,
                "publication_gaps": sorted(self._publication_gaps), "observation_gaps": sorted(self._window_gaps),
                "currently_uncovered": sorted(self._missing()),
                "consumer_observation": self._result, "external_change_observed": self._external_change,
                "checked_bytes": {name: hashlib.sha256(raw).hexdigest() for name, raw in self._reads.items()},
                "other_boundaries_basis": "test_assumption_only" if self._assumed else "unresolved",
                "isolation_certified": False, "native_publication_performed": False,
                "protected_commit_allowed": False, "future_immutability_proven": False,
                "formal_permission": False, "execution_authenticated": False,
                "acceptance_status": "not_completed", "retry_permitted": False, "cleanup_permitted": False}
