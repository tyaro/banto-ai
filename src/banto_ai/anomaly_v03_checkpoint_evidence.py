"""Read-only preflight binding of a reference journal to an existing six-cell trial.

The explicit mapping is for historical trial evidence only. It never verifies a
campaign attempt root or supplies campaign coverage/resume permission.
"""
from __future__ import annotations

import math
from pathlib import Path
import re
import sys

from . import _anomaly_v03_io as storage
from . import _anomaly_v03_runtime as rt
from . import _anomaly_v03_engineering_runtime as resources
from . import anomaly_v03 as v
from . import anomaly_v03_checkpoints as checkpoints
from . import anomaly_v03_engineering_contract as policy
from . import anomaly_v03_saved_audit as audit

REFERENCE_FORMAT = "anomaly-v03-checkpoint-preflight-reference-v1"
PURPOSE = "historical-six-cell-trial-only"
PATH_KEYS = ("trial_root", "producer_root", "consumer_root", "audit_path", "audit_monitor_path")


def _same(actual, expected, reason):
    rt.require(v.canonical_json(actual) == v.canonical_json(expected), reason)


def validate_reference(reference):
    rt.require(type(reference) is dict and set(reference) == {
        "format", "purpose", "journal", "audit_monitor_sha256", *PATH_KEYS}, "preflight reference fields")
    _same([reference["format"], reference["purpose"]], [REFERENCE_FORMAT, PURPOSE], "preflight reference purpose")
    for key in PATH_KEYS:
        value = reference[key]
        rt.require(type(value) is str and bool(value) and Path(value).is_absolute(), "absolute reference path required")
    journal = reference["journal"]
    rt.require(type(journal) is dict and set(journal) == {
        "expected_plan_sha256", "expected_record_count", "expected_head_sha256"}, "external journal pins")
    for digest in (reference["audit_monitor_sha256"], journal["expected_plan_sha256"], journal["expected_head_sha256"]):
        rt.require(type(digest) is str and re.fullmatch("[0-9a-f]{64}", digest), "external preflight hash")
    _same(journal["expected_record_count"], 3, "preflight requires one three-record reference attempt")


def validate_declaration(plan, records, reference):
    validate_reference(reference)
    reduced = checkpoints.reduce_journal(plan, records, **reference["journal"])
    _same([row["status"] for row in records[:2]], ["running", "saved_pending_verification"], "preflight start/save records")
    rt.require(records[-1]["status"] in checkpoints.VERIFIED, "preflight requires verified declaration")
    _same([[row["chunk_index"], row["attempt"]] for row in records], [[0, 1]] * 3,
          "preflight limited to first registered six-cell trial")
    return reduced


def _monitor(monitor, audit_raw, reference, pins, bindings):
    _same([monitor["status"], monitor["exit_code"], monitor["worker_exit_confirmed"], monitor["stop_reason"],
           monitor["observation_errors"], monitor["formal_permission"]],
          ["complete", 0, True, None, [], False], "saved audit monitor did not complete")
    _same(monitor["output"], {"bytes": len(audit_raw), "sha256": storage.sha(audit_raw)}, "monitor output binding")
    _same(monitor["stderr"], {"bytes": 0, "sha256": storage.sha(b"")}, "audit monitor stderr")
    _same(monitor["limits"], {"wall_seconds": 600, "private_bytes": 1024**3, "output_bytes": 8 * 1024**2},
          "historical audit monitor limits")
    elapsed, peak = monitor["elapsed_seconds"], monitor["peak_worker_private_bytes"]
    rt.require(type(elapsed) in (int, float) and math.isfinite(elapsed) and 0 <= elapsed <= 600,
               "historical audit time limit")
    rt.require(type(peak) is int and 0 <= peak <= 1024**3 and len(audit_raw) <= 8 * 1024**2,
               "historical audit memory/output limit")
    expected_argv = [sys.executable, "-B", str(Path(reference["consumer_root"]) / "tools/evaluator/audit_anomaly_v03_saved.py"),
        "--input-root", str(Path(reference["trial_root"])), "--marker-sha256", pins["marker_sha256"],
        "--supervision-sha256", pins["supervision_sha256"], "--producer-root", str(Path(reference["producer_root"])),
        "--producer-revision", bindings["producer_revision"], "--consumer-revision", bindings["consumer_revision"]]
    _same(monitor["argv"], expected_argv, "audit monitor invocation binding")


def bind_evidence(plan, records, reference, manifest, supervision, stored_audit, fresh_audit,
                  monitor, audit_raw, historical_consumer_source):
    """Cross-check supplied evidence; caller must verify file/source pins first."""
    validate_declaration(plan, records, reference)
    record = records[-1]
    policy.validate_manifest(manifest)
    rt.require(manifest["state"] == "complete", "preflight trial is incomplete")
    _same(manifest["attempt_id"], Path(reference["trial_root"]).name, "trial name mismatch")
    _same(manifest["plan"]["identities"], plan["chunks"][0]["identities"], "trial identity inventory")
    bindings, pins = plan["source_bindings"], record["evidence"]
    _same(manifest["source"], fresh_audit["producer_source"], "manifest/fresh source mismatch")
    _same(manifest["source"]["revision"], bindings["producer_revision"], "declared producer revision")
    _same(record["context"]["runtime"], manifest["runtime"], "declared trial runtime")
    _same(record["outcome"], {
        "slots": [{"evaluation_id": row["identity"]["evaluation_id"], "status": row["status"]} for row in manifest["slots"]],
        "worker_exit_confirmed": True, "runtime_after": supervision["runtime"], "audit_scope": "stored_score_ledgers_only"},
        "journal outcome differs from saved trial")
    _same([supervision["status"], supervision["exit_code"], supervision["worker_exit_confirmed"], supervision["stop_reason"],
           supervision["observation_errors"], supervision["formal_permission"], supervision["performance_status"],
           supervision["attempt_id"], supervision["policy_id"], supervision["scope"], supervision["runtime"]],
          ["complete", 0, True, None, [], False, "not_evaluated", manifest["attempt_id"], policy.POLICY_ID,
           policy.SCOPE, manifest["runtime"]], "trial supervision binding")
    _same(supervision["resource_measurement_scope"], "whole_worker_including_replays_and_exit", "supervision scope")
    resources.check_budget(supervision["elapsed_seconds"], supervision["peak_worker_private_bytes"], 0)
    _same(stored_audit["consumer_source"], historical_consumer_source, "historical consumer source changed")
    _same(historical_consumer_source["revision"], bindings["consumer_revision"], "declared consumer revision")
    policy.validate_runtime(stored_audit["consumer_runtime"])
    _same(stored_audit["input"], {"root": str(Path(reference["trial_root"])),
        "marker_sha256": pins["marker_sha256"], "supervision_sha256": pins["supervision_sha256"]}, "audit input binding")
    _same(stored_audit["input"], fresh_audit["input"], "fresh audit input differs")
    # Compare stable conclusions, not elapsed time or the new verifier's source/runtime.
    for key in ("format", "scope", "status", "producer_source", "storage_verification", "evaluations",
                "checked", "shared_checks", "not_checked_independently", "independent_s6_complete",
                "performance_status", "formal_permission"):
        _same(stored_audit[key], fresh_audit[key], "stored/fresh audit differs: " + key)
    _same([fresh_audit["format"], fresh_audit["scope"], fresh_audit["status"], fresh_audit["independent_s6_complete"],
           fresh_audit["formal_permission"], fresh_audit["performance_status"]],
          ["anomaly-v03-independent-ledger-audit-v1", "saved-engineering-six-cell-ledgers", "ledger_checks_passed",
           False, False, "not_evaluated"], "partial audit status")
    _same([row["identity"] for row in fresh_audit["evaluations"]], manifest["plan"]["identities"], "audit six-cell coverage")
    for row in fresh_audit["evaluations"]:
        _same([row["status"], row["score_derivation_verified"], row["independent_s6_complete"], row["performance_status"]],
              ["ledger_checks_passed", False, False, "not_evaluated"], "evaluation audit scope")
    _same(stored_audit["resources"]["input_payload_bytes"], fresh_audit["resources"]["input_payload_bytes"], "payload byte count")
    _monitor(monitor, audit_raw, reference, pins, bindings)
    return {"format": "anomaly-v03-checkpoint-preflight-binding-v1", "status": "preflight_evidence_verified",
        "purpose": PURPOSE, "journal": reference["journal"], "declared_attempt_root": record["attempt_root"],
        "historical_trial_root": reference["trial_root"], "preflight_evidence_revalidated": True,
        "evaluations_checked": 6, "evidence": dict(pins), "audit_monitor_sha256": reference["audit_monitor_sha256"],
        "producer_revision": bindings["producer_revision"], "historical_consumer_revision": bindings["consumer_revision"],
        "verifier_revision": fresh_audit["consumer_source"]["revision"],
        "historical_producer_runtime": manifest["runtime"], "historical_consumer_runtime": stored_audit["consumer_runtime"],
        "verifier_runtime": fresh_audit["consumer_runtime"],
        "campaign_evaluations_credited": 0, "campaign_attempt_roots_verified": False,
        "resume_authorized": False, "campaign_completed": False, "independent_s6_complete": False,
        "score_derivation_verified": False, "formal_permission": False, "performance_status": "not_evaluated"}


def verify_preflight(plan, records, reference, verifier_revision):
    """Pin stored reports, repeat six saved-ledger audits, then bind declarations."""
    validate_declaration(plan, records, reference)
    paths = {key: rt.regular_path(Path(reference[key]), directory=key.endswith("_root")) for key in PATH_KEYS}
    pins = records[-1]["evidence"]
    trial_root = paths["trial_root"]
    # Historical audit source is distinct from the new verification implementation.
    historical_consumer = rt.capture_checkout(paths["consumer_root"], plan["source_bindings"]["consumer_revision"])
    audit_raw = audit._pin(paths["audit_path"], pins["audit_sha256"], maximum=8 * 1024**2)
    monitor_raw = audit._pin(paths["audit_monitor_path"], reference["audit_monitor_sha256"])
    supervision_path = trial_root.parent / (trial_root.name + "-control") / "supervision.json"
    supervision_raw = audit._pin(supervision_path, pins["supervision_sha256"])
    manifest_path = trial_root / "payload/manifest.json"
    rt.require(rt.regular_path(manifest_path).stat().st_size <= 1024**2, "trial manifest too large")
    manifest_raw = storage.read_regular(manifest_path)
    fresh = audit.audit_saved(trial_root, pins["marker_sha256"], pins["supervision_sha256"], paths["producer_root"],
                              plan["source_bindings"]["producer_revision"], verifier_revision)
    result = bind_evidence(plan, records, reference, v.strict_json(manifest_raw), v.strict_json(supervision_raw),
        v.strict_json(audit_raw), fresh, v.strict_json(monitor_raw), audit_raw, historical_consumer.source_descriptor())
    for path, raw in ((paths["audit_path"], audit_raw), (paths["audit_monitor_path"], monitor_raw),
                      (supervision_path, supervision_raw), (manifest_path, manifest_raw)):
        rt.require(storage.read_regular(path) == raw, "preflight evidence changed during verification")
    historical_consumer.recheck()
    result["resources"] = fresh["resources"]
    return result
