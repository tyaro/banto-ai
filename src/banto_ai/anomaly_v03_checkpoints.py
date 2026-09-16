"""Metadata-only campaign plan and journal reducer; no execution or file IO.

Hash chains detect edits/truncation only against an externally retained head.
Declared verification is never a substitute for re-reading saved evidence.
"""
from __future__ import annotations

import copy
import hashlib
import re
from collections import Counter

from . import _anomaly_v03_contract as c
from . import anomaly_v03 as v

PLAN_FORMAT = "anomaly-v03-checkpoint-plan-v1"
RECORD_FORMAT = "anomaly-v03-checkpoint-record-v1"
SCOPE = "engineering-dev-smoke-checkpoints"
MAX_RECORDS = 4096
STATES = ("not_started", "running", "saved_pending_verification", "failed",
          "interrupted", "blocked_integrity", "verified_complete", "verified_inconclusive")
VERIFIED = ("verified_complete", "verified_inconclusive")
FAILURES = ("failed", "interrupted", "blocked_integrity")
REASONS = ("worker_exit", "exception", "resource_limit", "interrupted",
           "hash_mismatch", "source_mismatch", "runtime_changed", "verification_failed")
INTEGRITY_REASONS = ("hash_mismatch", "source_mismatch", "runtime_changed")


def _keys(value, keys, reason):
    v.require(type(value) is dict and set(value) == set(keys.split()), reason)


def _exact(value, expected, reason):
    v.require(v.canonical_json(value) == v.canonical_json(expected), reason)


def _hex(value, length, reason):
    v.require(type(value) is str and re.fullmatch(f"[0-9a-f]{{{length}}}", value), reason)


def _int(value, minimum, reason):
    v.require(type(value) is int and value >= minimum, reason)


def _bindings(value):
    _keys(value, "producer_revision consumer_revision", "source binding fields")
    for revision in value.values():
        _hex(revision, 40, "source revision")


def _runtime(value):
    expected = c.formal_runtime()
    _keys(value, " ".join(expected), "runtime fields")
    _int(value["os_build"], 22000, "OS build")
    _int(value["os_ubr"], 0, "OS UBR")
    expected.update(os_build=value["os_build"], os_ubr=value["os_ubr"])
    _exact(value, expected, "unsupported engineering runtime")


def fixed_plan(producer_revision, consumer_revision):
    """Build all 120 chunks; revision bindings are declarations, not Git checks."""
    bindings = {"producer_revision": producer_revision, "consumer_revision": consumer_revision}
    _bindings(bindings)
    chunks = []
    for role in ("dev", "smoke"):
        identities = v.evaluation_inventory(role)
        for offset in range(0, len(identities), 6):
            group = identities[offset:offset + 6]
            chunks.append({"chunk_index": len(chunks), "role": role,
                "seed": group[0]["seed"], "layout": group[0]["layout"], "identities": group,
                "identities_sha256": v.canonical_sha256(group)})
    return {"format": PLAN_FORMAT, "scope": SCOPE, "status": "metadata_only",
        "policy_id": "anomaly-v03-single-writer-v1", "source_bindings": bindings,
        "science": {"science_revision": c.SCIENCE_REVISION, "post_audit_revision": c.STATUS_REVISION,
                    "registry_raw_sha256": v.REGISTRY_RAW_SHA256, "seed_list_sha256": c.SEED_HASH},
        "runtime_policy": {"os_updates_between_attempts": "record_observed_build_and_ubr",
            "change_within_attempt": "blocked_integrity", "other_pins": c.formal_runtime(),
            "mixed_runtime_acceptance": "not_completed"},
        "budgets": {"status": "not_frozen", "chunk": None, "campaign": None,
                    "controller_and_consumer": None},
        "chunks": chunks, "chunks_sha256": v.canonical_sha256(chunks),
        "planned_counts": {"dev_chunks": 96, "smoke_chunks": 24, "chunks": 120,
            "dev_evaluations": 576, "smoke_evaluations": 144, "evaluations": 720},
        "execution_authorized": False, "formal_permission": False,
        "acceptance_status": "not_completed", "performance_status": "not_evaluated"}


def validate_plan(plan):
    v.require(type(plan) is dict and "source_bindings" in plan, "plan fields")
    _bindings(plan["source_bindings"])
    _exact(plan, fixed_plan(**plan["source_bindings"]), "fixed checkpoint plan changed")
    return {"status": "metadata_plan_valid", "plan_sha256": v.canonical_sha256(plan),
            "planned_counts": dict(plan["planned_counts"]), "execution_authorized": False}


def encode_record(record):
    """Canonical bytes are the journal format, including one trailing LF."""
    return v.canonical_json(record) + b"\n"


def record_hash(record):
    return hashlib.sha256(encode_record(record)).hexdigest()


def make_record(plan_sha256, previous_sha256, sequence, chunk_index, attempt, status,
                context, *, evidence=None, outcome=None, reason=None):
    """Construct a declaration. Only reduce_journal validates the whole history."""
    return copy.deepcopy({"format": RECORD_FORMAT, "plan_sha256": plan_sha256,
        "previous_sha256": previous_sha256, "sequence": sequence, "chunk_index": chunk_index,
        "attempt": attempt, "attempt_root": f"chunks/{chunk_index:03d}/attempt-{attempt:04d}",
        "status": status, "context": context,
        "evidence": evidence or {"marker_sha256": None, "supervision_sha256": None, "audit_sha256": None},
        "outcome": outcome, "reason": reason})


def _record(record, plan, plan_hash, sequence, previous):
    _keys(record, "format plan_sha256 previous_sha256 sequence chunk_index attempt attempt_root status context evidence outcome reason",
          "journal record fields")
    _exact([record["format"], record["plan_sha256"], record["sequence"], record["previous_sha256"]],
           [RECORD_FORMAT, plan_hash, sequence, previous], "journal chain/sequence/plan mismatch")
    _int(record["chunk_index"], 0, "chunk index")
    v.require(record["chunk_index"] < 120, "chunk index outside plan")
    _int(record["attempt"], 1, "attempt number")
    v.require(record["attempt_root"] == f"chunks/{record['chunk_index']:03d}/attempt-{record['attempt']:04d}",
              "attempt root changed")
    status = record["status"]
    v.require(type(status) is str and status in STATES[1:], "journal status")
    _keys(record["context"], "source_bindings runtime", "attempt context fields")
    _exact(record["context"]["source_bindings"], plan["source_bindings"], "attempt source mismatch")
    _runtime(record["context"]["runtime"])
    evidence = record["evidence"]
    _keys(evidence, "marker_sha256 supervision_sha256 audit_sha256", "evidence pin fields")
    for digest in evidence.values():
        if digest is not None:
            _hex(digest, 64, "evidence hash")
    if status == "running":
        v.require(all(x is None for x in evidence.values()), "running already has evidence")
    elif status == "saved_pending_verification":
        v.require(evidence["marker_sha256"] is not None, "saved record missing marker")
    elif status in VERIFIED:
        v.require(all(x is not None for x in evidence.values()), "verification missing evidence")
        outcome = record["outcome"]
        _keys(outcome, "slots worker_exit_confirmed runtime_after audit_scope", "verification outcome fields")
        _exact(outcome["worker_exit_confirmed"], True, "worker exit not confirmed")
        _exact(outcome["runtime_after"], record["context"]["runtime"], "runtime changed within attempt")
        v.require(outcome["audit_scope"] == "stored_score_ledgers_only", "unsupported audit scope")
        slots = outcome["slots"]
        v.require(type(slots) is list and len(slots) == 6, "six slot outcomes required")
        for slot, identity in zip(slots, plan["chunks"][record["chunk_index"]]["identities"]):
            _keys(slot, "evaluation_id status", "slot outcome fields")
            v.require(slot["evaluation_id"] == identity["evaluation_id"], "slot identity/order changed")
            v.require(type(slot["status"]) is str and slot["status"] in ("success", "inconclusive"), "slot outcome")
        expected = "verified_inconclusive" if any(s["status"] == "inconclusive" for s in slots) else "verified_complete"
        v.require(status == expected, "inconclusive outcome hidden")
    if status not in VERIFIED:
        v.require(record["outcome"] is None, "unverified record claims outcome")
    if status in FAILURES:
        reason = record["reason"]
        v.require(type(reason) is str and reason in REASONS, "failure needs classified reason")
        if reason in INTEGRITY_REASONS:
            v.require(status == "blocked_integrity", "integrity failure must block campaign")
        if status == "interrupted":
            v.require(reason == "interrupted", "interruption reason")
    else:
        v.require(record["reason"] is None, "nonfailure has failure reason")


def reduce_journal(plan, records, *, expected_plan_sha256, expected_record_count, expected_head_sha256):
    """Restore declarations only. No byte revalidation, skipping or run permission.

    The caller must retain all three expected pins outside the loaded journal.
    For an empty journal its head is the canonical plan hash.
    """
    validate_plan(plan)
    plan_hash = v.canonical_sha256(plan)
    _hex(expected_plan_sha256, 64, "external plan hash")
    v.require(plan_hash == expected_plan_sha256, "external plan hash mismatch")
    _hex(expected_head_sha256, 64, "external journal head hash")
    _int(expected_record_count, 0, "external journal count")
    v.require(type(records) is list and len(records) == expected_record_count <= MAX_RECORDS,
              "journal truncated or record count limit")
    previous = plan_hash
    current = None
    next_chunk = 0
    chunks = [{"chunk_index": i, "status": "not_started", "attempts": []} for i in range(120)]
    for sequence, record in enumerate(records, 1):
        _record(record, plan, plan_hash, sequence, previous)
        index, attempt, status = record["chunk_index"], record["attempt"], record["status"]
        v.require(index == next_chunk, "chunk order/duplicate violation")
        if current is None or current["status"] in ("failed", "interrupted"):
            expected_attempt = 1 if current is None else current["attempt"] + 1
            v.require(status == "running" and attempt == expected_attempt, "new attempt must start in sequence")
            chunks[index]["attempts"].append({"attempt": attempt, "attempt_root": record["attempt_root"],
                "status": status, "reason": None, "record_sequences": []})
        else:
            v.require(current["status"] != "blocked_integrity", "campaign blocked by integrity failure")
            v.require(attempt == current["attempt"], "attempt changed without failed/interrupted record")
            _exact(record["context"], current["context"], "attempt context changed")
            allowed = ({"saved_pending_verification", *FAILURES} if current["status"] == "running"
                       else {*VERIFIED, *FAILURES})
            v.require(status in allowed, "invalid state transition")
            for name, digest in current["evidence"].items():
                v.require(digest is None or record["evidence"][name] == digest, "attempt evidence pin changed")
        row = chunks[index]
        row["status"] = status
        row["attempts"][-1].update(status=status, reason=record["reason"],
            context=copy.deepcopy(record["context"]), evidence=copy.deepcopy(record["evidence"]))
        row["attempts"][-1]["record_sequences"].append(sequence)
        current = record
        if status in VERIFIED:
            row.update(evidence=copy.deepcopy(record["evidence"]), outcome=copy.deepcopy(record["outcome"]))
            next_chunk += 1
            current = None
        previous = record_hash(record)
    v.require(previous == expected_head_sha256, "external journal head mismatch")
    counts = Counter(row["status"] for row in chunks)
    verified = counts["verified_complete"] + counts["verified_inconclusive"]
    status = current["status"] if current else "not_started"
    if status == "blocked_integrity":
        action = "investigate_integrity_failure"
    elif verified:
        action = "revalidate_saved_evidence"
    else:
        action = {"running": "reconcile_interrupted_attempt", "saved_pending_verification": "verify_saved_attempt",
                  "failed": "new_attempt_required", "interrupted": "new_attempt_required"}.get(status, "execution_not_authorized")
    return {"status": "journal_metadata_valid", "scope": SCOPE, "plan_sha256": plan_hash,
        "record_count": len(records), "head_sha256": previous, "chunks": chunks,
        "coverage": {state: counts[state] for state in STATES},
        "attempt_count": sum(len(row["attempts"]) for row in chunks),
        "failed_attempt_count": sum(a["status"] in ("failed", "interrupted", "blocked_integrity")
                                    for row in chunks for a in row["attempts"]),
        "declared_coverage_complete": verified == 120,
        "next_unverified_chunk": next_chunk if next_chunk < 120 else None, "next_action": action,
        "evidence_revalidated": False, "resume_authorized": False, "campaign_completed": False,
        "independent_s6_complete": False, "performance_status": "not_evaluated", "formal_permission": False}
