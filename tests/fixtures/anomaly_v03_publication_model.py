"""B2 prototype: bounded in-memory marker and operation journal only.

No native adapter, filesystem operation, campaign entry, or acceptance receipt.
Callers represent a trusted adapter's observations; the model cannot prove any
operation, semantic check, DACL check, or process actually ran.
"""

import hashlib
import re

from banto_ai import anomaly_v03 as v

VERSION = "s4-b2-model.1"
MAX_FILES = 8
MAX_FILE_BYTES = 64 * 1024
MAX_TOTAL_BYTES = 256 * 1024
MAX_MARKER_BYTES = 16 * 1024
STEPS = ("prepare", "verify_prepared", "seal_payload", "rename_payload", "verify_final", "commit_marker")
MUTATIONS = frozenset(("prepare", "seal_payload", "rename_payload", "commit_marker"))


class ModelError(ValueError):
    """Fixed, non-sensitive protocol failure; never echo caller values."""


def _need(condition):
    if not condition:
        raise ModelError("invalid_publication_model")


def _digest(value, length=64):
    return type(value) is str and re.fullmatch(r"[a-f0-9]{" + str(length) + "}", value) is not None


def marker_bytes(source_revision, files):
    """Describe caller-owned toy bytes, without asserting their semantics."""
    _need(_digest(source_revision, 40) and type(files) is dict and 0 < len(files) <= MAX_FILES)
    total = 0
    folded = set()
    spellings = {}
    for name, raw in files.items():
        _need(type(name) is str and len(name) <= 128 and type(raw) is bytes and len(raw) <= MAX_FILE_BYTES)
        try:
            v.safe_relative_path(name)
        except v.V03ValidationError:
            raise ModelError("invalid_publication_model") from None
        _need(name.casefold() not in folded)
        folded.add(name.casefold())
        parts = name.split("/")
        for index in range(1, len(parts) + 1):
            prefix = "/".join(parts[:index])
            key = prefix.casefold()
            _need(key not in spellings or spellings[key] == prefix)
            spellings[key] = prefix
        total += len(raw)
        _need(total <= MAX_TOTAL_BYTES)
    _need(all(not any("/".join(name.split("/")[:i]) in folded
                      for i in range(1, len(name.split("/")))) for name in folded))
    entries = [{"path": name, "byte_count": len(files[name]), "raw_sha256": hashlib.sha256(files[name]).hexdigest()}
               for name in sorted(files)]
    marker = {"model_version": VERSION, "source_revision": source_revision,
              "payload_inventory": entries, "inventory_sha256": v.canonical_sha256(entries),
              "acceptance_status": "not_completed", "formal_permission": False, "execution_authenticated": False}
    raw = v.canonical_json(marker) + b"\n"
    _need(len(raw) <= MAX_MARKER_BYTES)
    return raw


def verify_marker(raw, *, expected_marker_sha256, source_revision, files):
    """Byte verification against an external pin; not execution/semantic proof."""
    _need(type(raw) is bytes and 0 < len(raw) <= MAX_MARKER_BYTES and _digest(expected_marker_sha256))
    _need(hashlib.sha256(raw).hexdigest() == expected_marker_sha256)
    # Exact reconstruction rejects duplicate keys, extra fields and formatting.
    _need(raw == marker_bytes(source_revision, files))
    return {"model_version": VERSION, "marker_verified": True, "semantic_verification": "not_performed",
            "acceptance_status": "not_completed", "formal_permission": False, "execution_authenticated": False}


class PublicationJournal:
    """One attempt; record intent BEFORE an adapter operation can be invoked.

    All six slots exist up front. Mutation without acknowledged success remains
    unknown, never assumed absent or safe to retry. No cleanup/recovery API.
    Public snapshots are detached; private fields are trusted caller state.
    """

    def __init__(self, marker_sha256):
        _need(_digest(marker_sha256))
        self._marker_sha256 = marker_sha256
        self._states = ["not_started"] * len(STEPS)
        self._next = 0
        self._active = None
        self._stopped = False
        self._reason = None
        self._resource = False
        self._teardown = "not_started"

    def _stop(self, reason, resource=False):
        self._stopped = True
        if self._reason is None:
            self._reason = reason
        self._resource = self._resource or resource
        if self._active is not None:
            self._states[self._active] = "unknown" if STEPS[self._active] in MUTATIONS else "failed"
            self._active = None

    def _guard(self, condition):
        if not condition:
            self._stop("protocol_error")
            raise ModelError("invalid_publication_transition")

    def begin(self, step):
        self._guard(not self._stopped and self._teardown == "not_started" and self._active is None
                    and self._next < len(STEPS) and type(step) is str and step == STEPS[self._next])
        self._active = self._next
        self._states[self._active] = "pending"

    def succeed(self, step):
        self._guard(not self._stopped and self._active is not None and type(step) is str
                    and step == STEPS[self._active])
        self._states[self._active] = "succeeded"
        self._active = None
        self._next += 1

    def fail(self, *, resource=False):
        self._guard(type(resource) is bool and not self._stopped and self._active is not None)
        self._stop("resource_stop" if resource else "operation_error", resource)

    def stop(self, *, resource=False):
        """Stop between steps or at teardown; preserve cause, escalate resource."""
        self._guard(type(resource) is bool)
        self._stop("resource_stop" if resource else "operation_error", resource)

    def finish_teardown(self, *, success):
        self._guard(type(success) is bool and self._active is None and self._teardown == "not_started"
                    and (self._stopped or self._next == len(STEPS)))
        self._teardown = "succeeded" if success else "failed"
        if not success:
            self._stop("teardown_error")

    def snapshot(self):
        """Pure detached formatting; no low-memory allocation guarantee."""
        marker_state = self._states[-1]
        commit = "confirmed" if marker_state == "succeeded" else "unknown" if marker_state in ("pending", "unknown") else "not_started"
        if self._stopped:
            status = "stopped"
        elif self._next == len(STEPS):
            status = "complete" if self._teardown == "succeeded" else "awaiting_teardown"
        else:
            status = "in_progress" if self._next or self._active is not None else "not_started"
        return {"model_version": VERSION, "model_status": status, "marker_sha256": self._marker_sha256,
                "steps": [{"step": name, "state": state} for name, state in zip(STEPS, self._states)],
                "commit_observation": commit, "failure_reason": self._reason, "resource_stop": self._resource,
                "teardown": self._teardown, "retry_permitted": False, "cleanup_permitted": False,
                "acceptance_status": "not_completed", "formal_permission": False, "execution_authenticated": False}
