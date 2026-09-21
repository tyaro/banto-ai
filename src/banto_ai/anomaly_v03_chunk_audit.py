"""Read-only selected chunk IO and evidence binding, never a campaign controller."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from . import anomaly_v03 as v
from . import anomaly_v03_attempt_files as attempts
from . import anomaly_v03_attempt_descriptor as descriptor
from . import anomaly_v03_checkpoints as checkpoints
from . import anomaly_v03_checkpoint_evidence as evidence
from . import anomaly_v03_checkpoint_store as store
from . import anomaly_v03_chunk_contract as chunk
from . import anomaly_v03_engineering_contract as policy
from . import anomaly_v03_saved_audit as saved
from . import _anomaly_v03_runtime as rt
from . import _anomaly_v03_io as storage

AUDIT_FORMAT = "anomaly-v03-chunk-ledger-audit-v1"
AUDIT_SCOPE = "saved-dev-smoke-chunk-ledgers"
SUPERVISION_FORMAT = "anomaly-v03-chunk-supervision-v1"


def read_plan(path, digest):
    path = rt.regular_path(Path(path))
    raw = store.read_metadata(path, store.MAX_PLAN_BYTES)
    plan = v.strict_json(raw)
    saved._same(v.canonical_sha256(plan), digest, "external chunk plan hash mismatch")
    checkpoints.validate_plan(plan)
    return path, raw, plan


def _input(plan_path, plan, index, attempt):
    return {"campaign_plan_path": str(Path(plan_path).absolute()),
            "binding": chunk.chunk_plan(plan, index, attempt)["binding"]}


def validate_supervision(value, plan, index, attempt):
    """Whole-producer observation; same runtime at both ends of one attempt."""
    saved._same([value["format"], value["policy_id"], value["scope"], value["attempt_id"], value["binding"]],
        [SUPERVISION_FORMAT, policy.POLICY_ID, chunk.SCOPE, "result", chunk.chunk_plan(plan, index, attempt)["binding"]],
        "chunk supervision selection")
    saved._same([value["status"], value["exit_code"], value["worker_exit_confirmed"], value["stop_reason"],
                 value["observation_errors"], value["formal_permission"], value["performance_status"]],
        ["complete", 0, True, None, [], False, "not_evaluated"], "chunk supervision did not complete")
    saved._same(value["resource_measurement_scope"], "whole_worker_including_replays_and_exit", "chunk supervision scope")
    policy.validate_runtime(value["runtime"])
    saved._same(value["runtime_after"], value["runtime"], "chunk producer runtime changed")
    from . import _anomaly_v03_engineering_runtime as resources
    resources.check_budget(value["elapsed_seconds"], value["peak_worker_private_bytes"], 0)


def invocation(consumer_root, result_root, marker_hash, supervision_hash, producer_root, consumer_revision,
               plan_path, plan_hash, index, attempt):
    return [sys.executable, "-B", str(Path(consumer_root).absolute() / "tools/evaluator/audit_anomaly_v03_chunk.py"),
        "--input-root", str(Path(result_root).absolute()), "--marker-sha256", marker_hash,
        "--supervision-sha256", supervision_hash, "--producer-root", str(Path(producer_root).absolute()),
        "--consumer-revision", consumer_revision, "--plan", str(Path(plan_path).absolute()),
        "--plan-sha256", plan_hash, "--chunk-index", str(index), "--attempt", str(attempt)]


def audit_saved_chunk(root, marker_sha256, supervision_sha256, producer_root, consumer_revision,
                      plan_path, plan_sha256, chunk_index, attempt):
    """Pin selected saved payload and clean sources, then recompute six ledgers."""
    plan_path, plan_raw, plan = read_plan(plan_path, plan_sha256)
    extra = _input(plan_path, plan, chunk_index, attempt)
    root = rt.regular_path(Path(root), directory=True)
    rt.require(root.name == "result", "chunk result directory name")
    attempts._payload_limits(root / "payload")
    report = saved._audit_saved(root, marker_sha256, supervision_sha256, Path(producer_root),
        plan["source_bindings"]["producer_revision"], consumer_revision,
        supervision_path=root.parent / "producer-control/supervision.json",
        payload_auditor=lambda files, producer: chunk.audit_chunk_payloads(files, producer, plan, chunk_index, attempt),
        supervision_scope=chunk.SCOPE, report_format=AUDIT_FORMAT, report_scope=AUDIT_SCOPE,
        supervision_validator=lambda value: validate_supervision(value, plan, chunk_index, attempt), input_extra=extra)
    rt.require(store.read_metadata(plan_path, store.MAX_PLAN_BYTES) == plan_raw, "chunk plan changed while auditing")
    return {**report, "budgets_frozen": False, "execution_authorized": False, "campaign_evaluations_credited": 0}


def audit_chunk_attempt(root, plan, records, descriptor_sha256, producer_root, consumer_root, verifier_revision,
                        plan_path, **pins):
    """Bind the latest verified declaration to fresh chunk replay and monitors."""
    descriptor.describe_layout(plan, records, **pins)
    record = records[-1]
    rt.require(record["status"] in checkpoints.VERIFIED, "chunk audit requires a verified declaration")
    plan_path, plan_raw, on_disk = read_plan(plan_path, pins["expected_plan_sha256"])
    saved._same(on_disk, plan, "chunk plan differs from journal plan")
    index, attempt = record["chunk_index"], record["attempt"]
    extra = _input(plan_path, plan, index, attempt)

    def verify(root, value, raw, payload_bytes, publication):
        layout, bindings, hashes = value["layout"], plan["source_bindings"], record["evidence"]
        result_root = root / layout["result_root"]
        historical = rt.capture_checkout(Path(consumer_root), bindings["consumer_revision"])
        stored = v.strict_json(raw["audit_report"])
        saved._same(value["audit_runtime"], {"before": stored["consumer_runtime"], "after": stored["consumer_runtime"]},
                    "descriptor audit runtime differs from report")
        manifest_path = result_root / "payload/manifest.json"
        manifest_raw = attempts._read(manifest_path, 1024**2)
        manifest = v.strict_json(manifest_raw)
        chunk.validate_manifest(manifest, plan, index, attempt)
        supervision = v.strict_json(raw["producer_supervision"])
        validate_supervision(supervision, plan, index, attempt)
        monitor = v.strict_json(raw["audit_supervision"])
        saved._same([monitor["runtime_before"], monitor["runtime_after"]],
                    [stored["consumer_runtime"]] * 2, "chunk audit monitor runtime binding")
        for key in ("budgets_frozen", "execution_authorized", "campaign_evaluations_credited"):
            saved._same(stored[key], 0 if key == "campaign_evaluations_credited" else False, "stored chunk audit permissions")
        fresh = audit_saved_chunk(result_root, hashes["marker_sha256"], hashes["supervision_sha256"],
            producer_root, verifier_revision, plan_path, pins["expected_plan_sha256"], index, attempt)
        reference = {"trial_root": str(result_root), "producer_root": str(Path(producer_root).absolute()),
            "consumer_root": str(Path(consumer_root).absolute()), "journal": pins,
            "audit_monitor_sha256": value["artifacts"]["audit_supervision"]["sha256"]}
        bound = evidence._bind_checked_trial(plan, record, reference, manifest, supervision, stored, fresh,
            monitor, raw["audit_report"], historical.source_descriptor(), scope=chunk.SCOPE,
            audit_format=AUDIT_FORMAT, audit_scope=AUDIT_SCOPE, input_extra=extra,
            invocation=invocation(consumer_root, result_root, hashes["marker_sha256"], hashes["supervision_sha256"],
                producer_root, bindings["consumer_revision"], plan_path, pins["expected_plan_sha256"], index, attempt))
        saved._same(fresh["resources"]["input_payload_bytes"], payload_bytes, "chunk audit payload bytes")
        saved._same(fresh["storage_verification"], publication, "chunk audit publication differs")
        rt.require(attempts._read(manifest_path, 1024**2) == manifest_raw, "chunk manifest changed")
        historical.recheck()
        return {"status": "attempt_chunk_ledgers_verified", "evidence_body_bindings_verified": True,
            "saved_ledgers_revalidated": True, "source_checkouts_verified": True, "evaluations_checked": 6,
            "binding": extra["binding"], "budgets_frozen": False,
            **{key: bound[key] for key in ("producer_revision", "historical_consumer_revision", "verifier_revision",
                "historical_producer_runtime", "historical_consumer_runtime", "verifier_runtime")},
            "audit_resources": fresh["resources"]}

    report = attempts._inspect(root, plan, records, descriptor_sha256, pins, verify)
    rt.require(store.read_metadata(plan_path, store.MAX_PLAN_BYTES) == plan_raw, "chunk plan changed during verification")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only saved ledger audit for one registered dev/smoke chunk")
    for name in ("input-root", "producer-root", "plan"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("marker-sha256", "supervision-sha256", "consumer-revision", "plan-sha256"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--chunk-index", type=int, required=True)
    parser.add_argument("--attempt", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        report = audit_saved_chunk(args.input_root, args.marker_sha256, args.supervision_sha256,
            args.producer_root, args.consumer_revision, args.plan, args.plan_sha256, args.chunk_index, args.attempt)
        print(json.dumps(report, sort_keys=True, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"status": "chunk_audit_failed", "error_type": type(error).__name__, "message": str(error)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
