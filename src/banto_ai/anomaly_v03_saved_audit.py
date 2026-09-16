"""Read-only IO envelope for the independent, partial ledger audit.

Shares JSON/schema, registry and storage checks, not producer numerical helpers.
Never calls a materializer, scorer, episode builder, matcher or campaign runner.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

from . import _anomaly_v03_io as storage
from . import _anomaly_v03_runtime as rt
from . import _anomaly_v03_engineering_runtime as resources
from . import anomaly_v03 as v
from . import anomaly_v03_engineering_contract as policy
from . import anomaly_v03_ledger_audit as audit

MAX_FILE_BYTES = 32 * 1024**2
MAX_PAYLOAD_BYTES = 256 * 1024**2


def _pin(path, digest, maximum=1024**2):
    rt.require(type(digest) is str and re.fullmatch("[0-9a-f]{64}", digest), "invalid external hash")
    path = rt.regular_path(path)
    rt.require(path.stat().st_size <= maximum, "audit control file too large")
    raw = storage.read_regular(path)
    rt.require(storage.sha(raw) == digest, "audit external hash mismatch")
    return raw


def _same(actual, expected, reason):
    rt.require(v.canonical_json(actual) == v.canonical_json(expected), reason)


def audit_payloads(files, producer):
    manifest = v.strict_json(files["manifest.json"])
    policy.validate_manifest(manifest)
    rt.require(manifest["state"] == "complete", "only completed engineering trials can be audited")
    _same(manifest["source"], producer.source_descriptor(), "producer source descriptor mismatch")
    _same(v.strict_json(files["planned.json"]), policy.new_manifest(manifest["attempt_id"]), "planned slots changed")
    _same(v.strict_json(files["context.json"]), {"source": manifest["source"], "runtime": manifest["runtime"]}, "saved context changed")
    expected = {"manifest.json", "planned.json", "context.json"}
    for dataset in manifest["datasets"]:
        for entry in dataset["files"]:
            raw = files[entry["path"]]
            _same(policy.file_record(entry["path"], raw), entry, "dataset hash/bytes changed")
            expected.add(entry["path"])
    reports = []
    for index, slot in enumerate(manifest["slots"]):
        entry = slot["evaluation"]
        raw = files[entry["path"]]
        _same(policy.file_record(entry["path"], raw), entry, "evaluation hash/bytes changed")
        value = v.strict_json(raw)
        v.validate_result_contract(value, source_snapshots=producer.snapshots())
        _same(value["identity"], slot["identity"], "evaluation identity changed")
        _same(value["input_hashes"], slot["input_hashes"], "evaluation input hashes changed")
        _same(value["events"], v.event_inventory(slot["identity"]), "registered event inventory changed")
        _same(value["provenance"]["producer_source"], manifest["source"], "evaluation source changed")
        status = "inconclusive" if any(p["status"] != "calibrated" for p in value["profiles"]) else "success"
        rt.require(slot["status"] == status, "profile status changed")
        report = audit.audit_evaluation(value)
        reports.append({"identity": slot["identity"], **report})
        start, done = f"journal/{index:02d}-started.json", f"journal/{index:02d}-done.json"
        _same(v.strict_json(files[start]), slot["identity"], "start journal changed")
        _same(v.strict_json(files[done]), slot, "done journal changed")
        expected.update((entry["path"], start, done))
        del value, raw
    rt.require(set(files) == expected, "audit payload inventory differs")
    return manifest, reports


def audit_saved(root, marker_sha256, supervision_sha256, producer_root, producer_revision, consumer_revision):
    started = time.monotonic()
    root = rt.regular_path(root, directory=True)
    producer = rt.capture_checkout(producer_root, producer_revision)
    consumer = rt.capture_checkout(Path(__file__).resolve().parents[2], consumer_revision)
    before = resources.require_start_resources(root)
    observed_runtime = resources.probe_runtime(root)
    control = root.parent / (root.name + "-control")
    supervision_raw = _pin(control / "supervision.json", supervision_sha256)
    supervision = v.strict_json(supervision_raw)
    rt.require(supervision["status"] == "complete" and type(supervision["exit_code"]) is int and supervision["exit_code"] == 0
        and supervision["worker_exit_confirmed"] is True and not supervision["observation_errors"]
        and supervision["stop_reason"] is None and supervision["formal_permission"] is False
        and supervision["performance_status"] == "not_evaluated", "trial supervision did not complete")
    _same([supervision["policy_id"], supervision["scope"], supervision["attempt_id"]],
          [policy.POLICY_ID, policy.SCOPE, root.name], "supervision identity changed")
    resources.check_budget(supervision["elapsed_seconds"], supervision["peak_worker_private_bytes"], 0)
    view = storage.PayloadView(root / "payload")
    sizes = [rt.regular_path(view.root / name).stat().st_size for name in view]
    rt.require(sizes and max(sizes) <= MAX_FILE_BYTES and sum(sizes) <= MAX_PAYLOAD_BYTES, "audit input byte limit")
    captured = {}
    def verify(files):
        manifest, reports = audit_payloads(files, producer)
        _same(supervision["runtime"], manifest["runtime"], "supervision/runtime mismatch")
        rt.require(manifest["attempt_id"] == root.name, "attempt path mismatch")
        captured.update(manifest=manifest, evaluations=reports)
    verified = storage.verify_local_publication(root, expected_marker_sha256=marker_sha256, verify_semantics=verify)
    producer.recheck()
    consumer.recheck()
    rt.require(storage.read_regular(control / "supervision.json") == supervision_raw, "supervision changed while auditing")
    _same(resources.probe_runtime(root), observed_runtime, "audit runtime changed")
    peak = resources.memory_bytes()["peak_private_bytes"]
    elapsed = time.monotonic() - started
    resources.check_budget(elapsed, peak, 0)
    return {"format": "anomaly-v03-independent-ledger-audit-v1", "scope": "saved-engineering-six-cell-ledgers",
        "status": "ledger_checks_passed", "producer_source": producer.source_descriptor(),
        "consumer_source": consumer.source_descriptor(), "consumer_runtime": observed_runtime,
        "input": {"root": str(root), "marker_sha256": marker_sha256, "supervision_sha256": supervision_sha256},
        "storage_verification": verified, "evaluations": captured["evaluations"],
        "checked": ["strict_threshold", "streak_and_source_episodes", "equipment_merge", "first_candidate_no_retry",
                    "causal_support", "context_tags", "fixed_denominator_metrics", "availability", "delay_summary"],
        "shared_checks": ["strict_json_schema", "frozen_registry_event_inventory", "source_capture", "storage_inventory_hashes"],
        "not_checked_independently": ["normal_generator", "observation_quantization", "profile_fit_calibration",
                                      "residual_score_derivation", "bootstrap", "performance_gates", "full_campaign_inventory"],
        "independent_s6_complete": False, "performance_status": "not_evaluated", "formal_permission": False,
        "resources": {"elapsed_seconds": elapsed, "peak_private_bytes": peak, "input_payload_bytes": sum(sizes),
                      "free_before": before, "free_after": resources.free_resources(root)}}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only partial independent audit of six saved engineering evaluations")
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--marker-sha256", required=True)
    parser.add_argument("--supervision-sha256", required=True)
    parser.add_argument("--producer-root", type=Path, required=True)
    parser.add_argument("--producer-revision", required=True)
    parser.add_argument("--consumer-revision", required=True)
    args = parser.parse_args(argv)
    try:
        report = audit_saved(args.input_root, args.marker_sha256, args.supervision_sha256,
                             args.producer_root, args.producer_revision, args.consumer_revision)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"status": "audit_failed", "error_type": type(error).__name__, "message": str(error)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
