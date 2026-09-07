"""Pure cleanup design prototype; deliberately outside the production source tree.

This module never performs IO or grants permission to mutate an object. A native
caller must bind and verify each owned identity before starting an operation.
Private snapshots contain evidence and must not be printed. report() is redacted.
"""

from dataclasses import dataclass, field
import hashlib
import json
import re

_MAX_OBJECTS = 32
_MAX_FILE_BYTES = 1024 * 1024
_MAX_TOTAL_BYTES = 4 * _MAX_FILE_BYTES
_MAX_METADATA_BYTES = 64 * 1024


class CleanupEvidenceError(ValueError):
    def __init__(self):
        super().__init__("cleanup_evidence_contract")


def _require(condition):
    if not condition:
        raise CleanupEvidenceError()


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _metadata(value):
    # Only captured canonical bytes cross this boundary. No arbitrary serializers
    # or callbacks may execute after a native mutation has begun.
    _require(type(value) is bytes and 0 < len(value) <= _MAX_METADATA_BYTES)
    return value


@dataclass(frozen=True, repr=False)
class CapturedObject:
    name: str
    directory: bool
    identity: bytes = field(repr=False)
    security: bytes = field(repr=False)
    cleanup_security: bytes = field(repr=False)
    content: bytes = field(repr=False)

    def __post_init__(self):
        _require(type(self.name) is str and len(self.name) <= 128)
        _require(self.name == "" or re.fullmatch(r"[a-z0-9_.-]+(?:/[a-z0-9_.-]+)*", self.name)
                 and all(part not in (".", "..") for part in self.name.split("/")))
        _require(type(self.directory) is bool)
        _metadata(self.identity)
        _metadata(self.security)
        _metadata(self.cleanup_security)
        _require(type(self.content) is bytes and len(self.content) <= _MAX_FILE_BYTES)
        _require(not self.directory or not self.content)

    def __repr__(self):
        return "CapturedObject(<private evidence>)"


@dataclass(repr=False)
class _Progress:
    acl: str = "unchanged"
    deletion: str = "not_started"
    close: str = "not_started"
    failed_operation: str | None = None


class CleanupJournal:
    """One attempt, no retries; mark pending BEFORE each external mutation.

    A failed native call can have side effects. 'unknown' preserves that fact.
    A successful delete disposition and close do not prove name absence.
    Full snapshots are retained in memory only, with no crash-durability claim.
    """

    def __init__(self, objects, operations):
        _require(type(objects) is tuple and 0 < len(objects) <= _MAX_OBJECTS)
        _require(all(type(item) is CapturedObject for item in objects))
        _require(type(operations) is bytes and 0 < len(operations) <= _MAX_FILE_BYTES)
        names = {item.name for item in objects}
        _require(len(names) == len(objects) and "" in names)
        by_name = {item.name: item for item in objects}
        _require(by_name[""].directory)
        for item in objects:
            if item.name:
                parent = item.name.rpartition("/")[0]
                _require(parent in by_name and by_name[parent].directory)
        _require(sum(len(item.content) for item in objects) <= _MAX_TOTAL_BYTES)
        # Immutable input objects and byte strings cannot alias the mutable native
        # ledger. Allocate every transition slot before exposing this journal.
        self._objects = tuple(sorted(objects, key=lambda item: item.name))
        self._operations = operations
        self._progress = {item.name: _Progress() for item in self._objects}
        inventory = [{"name": item.name, "directory": item.directory,
                      "identity_sha256": _sha(item.identity), "security_sha256": _sha(item.security),
                      "cleanup_security_sha256": _sha(item.cleanup_security),
                      "content_sha256": _sha(item.content), "bytes": len(item.content)}
                     for item in self._objects]
        self._snapshot_digest = _sha(json.dumps(
            {"version": 1, "objects": inventory, "operations_sha256": _sha(operations)},
            sort_keys=True, separators=(",", ":")).encode("ascii"))
        self._status = "prepared"
        self._resource_stop = False
        self._active = None

    def __repr__(self):
        return "CleanupJournal(<private evidence>)"

    @property
    def private_snapshot(self):
        """Explicit in-memory access only; callers must not log this evidence."""
        return self._objects, self._operations

    def _row(self, name):
        _require(type(name) is str and name in self._progress)
        return self._progress[name]

    def begin(self, name, operation):
        _require(self._status in ("prepared", "running") and not self._resource_stop)
        _require(self._active is None and operation in ("acl", "delete", "absence"))
        row = self._row(name)
        if operation == "acl":
            _require(row.acl == "unchanged" and row.deletion == "not_started")
        elif operation == "delete":
            _require(row.acl == "changed" and row.deletion == "not_started")
            # A parent may be deleted only after all its captured descendants
            # have confirmed absence. Unknown/foreign children remain a native
            # preflight concern, and never get added to this journal.
            _require(all(other.deletion == "absent" for child, other in self._progress.items()
                         if child != name and (not name or child.startswith(name + "/"))))
        else:
            _require(row.deletion == "armed" and row.close == "confirmed")
        # Allocate the pair before updating any state; allocation failure leaves
        # the old state intact and the native caller has not started the API yet.
        active = (name, operation)
        if operation == "acl":
            row.acl = "pending"
        elif operation == "delete":
            row.deletion = "pending"
        self._active, self._status = active, "running"

    def confirmed(self):
        _require(self._status == "running" and self._active is not None and not self._resource_stop)
        name, operation = self._active
        row = self._progress[name]
        if operation == "acl":
            row.acl = "changed"  # Caller has verified the new descriptor.
        elif operation == "delete":
            row.deletion = "armed"  # Native disposition accepted, not absence.
        else:
            row.deletion = "absent"  # Caller has positively verified absence.
        self._active = None

    def close_confirmed(self, name):
        # Handle-only teardown is permitted after a failure/resource stop. It
        # never upgrades an uncertain disposition to confirmed absence.
        row = self._row(name)
        _require(self._active is None and row.deletion in ("armed", "unknown") and row.close != "confirmed")
        row.close = "confirmed"

    def failed(self, *, resource_stop=False):
        _require(type(resource_stop) is bool and self._status != "completed")
        if self._active is not None:
            name, operation = self._active
            row = self._progress[name]
            row.failed_operation = operation
            if operation == "acl":
                row.acl = "unknown"
            elif operation == "delete":
                row.deletion = "unknown"
            self._active = None
        self._status = "failed"
        self._resource_stop |= resource_stop

    def close_failed(self, name, *, resource_stop=False):
        _require(type(resource_stop) is bool and self._status != "completed")
        row = self._row(name)
        _require(self._active is None and row.deletion in ("armed", "unknown") and row.close != "confirmed")
        row.close = "unknown"
        self.failed(resource_stop=resource_stop)
        # Keep a prior mutation failure as the primary cause.
        if row.failed_operation is None:
            row.failed_operation = "close"

    def complete(self):
        _require(self._status == "running" and self._active is None and not self._resource_stop)
        _require(all(row.deletion == "absent" for row in self._progress.values()))
        self._status = "completed"

    def report(self):
        """Redacted, bounded memory-only view. It allocates; not an OOM handler.

        Retained bounds describe captured objects only. They are not a fresh
        filesystem inventory and say nothing about foreign objects or disk usage.
        """
        rows, absent_bytes, present_bytes, uncertain_bytes = [], 0, 0, 0
        absent_count = present_count = uncertain_count = 0
        for item in self._objects:
            row = self._progress[item.name]
            size = len(item.content)
            if row.deletion == "absent":
                absent_count += 1
                absent_bytes += size
            elif row.deletion == "not_started":
                present_count += 1
                present_bytes += size
            else:
                uncertain_count += 1
                uncertain_bytes += size
            rows.append({"name": item.name, "acl": row.acl, "deletion": row.deletion,
                         "close": row.close, "failed_operation": row.failed_operation})
        return {"version": 1, "status": self._status, "resource_stop": self._resource_stop,
                "snapshot_sha256": self._snapshot_digest, "objects": rows,
                "captured_objects": len(rows), "captured_bytes": absent_bytes + present_bytes + uncertain_bytes,
                "confirmed_absent_objects": absent_count, "confirmed_absent_bytes": absent_bytes,
                "retained_captured_objects_min": present_count,
                "retained_captured_objects_max": present_count + uncertain_count,
                "retained_captured_bytes_min": present_bytes,
                "retained_captured_bytes_max": present_bytes + uncertain_bytes,
                "unknown_objects": uncertain_count,
                "success_residue_count": 0 if self._status == "completed" else None,
                "filesystem_reobserved": False, "native_accepted": False, "formal_permission": False}
