"""Pure attempt path/evidence contract, anchored to an external journal snapshot.

Consumes declarations only. Does not open attempt files, certify their contents,
launch workers, allocate directories, or grant campaign coverage/resume rights.
"""
from __future__ import annotations

import copy
import re

from . import anomaly_v03 as v
from . import anomaly_v03_checkpoints as checkpoints

FORMAT = "anomaly-v03-attempt-descriptor-v1"
SCOPE = "engineering-dev-smoke-attempt-metadata"
ROLES = ("marker", "producer_supervision", "audit_report", "audit_supervision")
JOURNAL_EVIDENCE = {"marker": "marker_sha256", "producer_supervision": "supervision_sha256",
                    "audit_report": "audit_sha256"}


def _same(actual, expected, reason):
    v.require(v.canonical_json(actual) == v.canonical_json(expected), reason)


def _keys(value, keys, reason):
    v.require(type(value) is dict and set(value) == set(keys), reason)


def _snapshot(plan, records, pins):
    checkpoints.reduce_journal(plan, records, **pins)
    v.require(bool(records), "attempt descriptor needs a started journal")
    return records[-1]


def _layout(record):
    root = record["attempt_root"]
    return {"attempt_root": root, "descriptor_path": f"{root}/descriptors/{record['sequence']:06d}.json",
        "result_root": root + "/result", "payload_root": root + "/result/payload",
        "producer_control_root": root + "/producer-control", "audit_root": root + "/audit",
        "files": {"marker": root + "/result/.complete",
            "producer_supervision": root + "/producer-control/supervision.json",
            "audit_report": root + "/audit/report.json", "audit_supervision": root + "/audit/supervision.json"}}


def describe_layout(plan, records, **pins):
    """Return paths and requirements, never fabricate absent file hashes/sizes."""
    record = _snapshot(plan, records, pins)
    return {"format": "anomaly-v03-attempt-layout-v1", "scope": SCOPE, "journal": copy.deepcopy(pins),
        "chunk_index": record["chunk_index"], "attempt": record["attempt"], "state": record["status"],
        "layout": _layout(record), "journal_evidence": copy.deepcopy(record["evidence"]),
        "required_for_verified_declaration": list(ROLES), "execution_authorized": False}


def _base(plan, record, pins):
    return {"format": FORMAT, "scope": SCOPE, "journal": copy.deepcopy(pins),
        "record": {"sequence": record["sequence"], "sha256": checkpoints.record_hash(record),
                   "chunk_index": record["chunk_index"], "attempt": record["attempt"],
                   "state": record["status"], "reason": record["reason"]},
        "layout": _layout(record), "identities": copy.deepcopy(plan["chunks"][record["chunk_index"]]["identities"]),
        "context": copy.deepcopy(record["context"]), "outcome": copy.deepcopy(record["outcome"]),
        "execution_authorized": False, "resume_authorized": False, "campaign_completed": False,
        "formal_permission": False, "independent_s6_complete": False, "performance_status": "not_evaluated"}


def _validate(descriptor, plan, record, pins):
    base = _base(plan, record, pins)
    _keys(descriptor, (*base, "artifacts", "audit_runtime"), "attempt descriptor fields")
    _same({key: descriptor[key] for key in base}, base, "attempt descriptor journal/context/layout mismatch")
    files = descriptor["artifacts"]
    _keys(files, ROLES, "attempt artifact roles")
    present = []
    for role, entry in files.items():
        expected_hash = record["evidence"].get(JOURNAL_EVIDENCE.get(role))
        if entry is None:
            v.require(role not in JOURNAL_EVIDENCE or expected_hash is None, "journal evidence lacks artifact metadata")
            continue
        _keys(entry, ("path", "bytes", "sha256"), "artifact descriptor fields")
        # Exact spelling fixes containment, separators and role/attempt identity.
        # Filesystem topology/actual containment still requires a later reader.
        _same(entry["path"], base["layout"]["files"][role], "artifact path/role mismatch")
        v.safe_relative_path(entry["path"])
        v.require(type(entry["bytes"]) is int and entry["bytes"] > 0, "artifact byte count")
        v.require(type(entry["sha256"]) is str and re.fullmatch("[0-9a-f]{64}", entry["sha256"]), "artifact hash")
        if role in JOURNAL_EVIDENCE:
            _same(entry["sha256"], expected_hash, "artifact hash differs from journal")
        present.append(role)
    state = record["status"]
    audit_runtime = descriptor["audit_runtime"]
    has_audit = files["audit_report"] is not None or files["audit_supervision"] is not None
    if state == "running":
        v.require(not present and audit_runtime is None, "running has completed evidence")
    if not has_audit:
        v.require(audit_runtime is None, "audit runtime without audit evidence")
    if audit_runtime is not None:
        _keys(audit_runtime, ("before", "after"), "audit runtime fields")
        checkpoints._runtime(audit_runtime["before"])
        if audit_runtime["after"] is not None:
            checkpoints._runtime(audit_runtime["after"])
            if v.canonical_json(audit_runtime["before"]) != v.canonical_json(audit_runtime["after"]):
                v.require(state == "blocked_integrity" and record["reason"] == "runtime_changed",
                          "audit runtime change must block attempt")
    if state in checkpoints.VERIFIED:
        v.require(len(present) == len(ROLES), "verified attempt needs marker and both supervision records and audit")
        v.require(audit_runtime is not None and audit_runtime["after"] is not None, "verified audit needs runtime before/after")
        _same(audit_runtime["before"], audit_runtime["after"], "verified audit runtime changed")
    return {"status": "attempt_descriptor_metadata_valid", "scope": SCOPE,
        "descriptor_canonical_sha256": v.canonical_sha256(descriptor), "journal": copy.deepcopy(pins),
        "chunk_index": record["chunk_index"], "attempt": record["attempt"], "state": state,
        "artifact_roles_present": [role for role in ROLES if role in present],
        "missing_for_verified_declaration": [role for role in ROLES if role not in present],
        "artifact_bytes_verified": False, "filesystem_containment_verified": False,
        "campaign_evaluations_credited": 0, "execution_authorized": False, "resume_authorized": False,
        "campaign_completed": False, "independent_s6_complete": False, "formal_permission": False}


def new_descriptor(plan, records, artifacts, *, audit_runtime=None, **pins):
    """Build from explicit file metadata; missing files remain None, never invented."""
    record = _snapshot(plan, records, pins)
    value = _base(plan, record, pins)
    value.update(artifacts=copy.deepcopy(artifacts), audit_runtime=copy.deepcopy(audit_runtime))
    _validate(value, plan, record, pins)
    return value


def validate_descriptor(descriptor, plan, records, **pins):
    """Check against the externally selected journal snapshot, not its own head."""
    record = _snapshot(plan, records, pins)
    return _validate(descriptor, plan, record, pins)
