"""Bounded local score preview: saved observations -> S2 arithmetic -> local result.

No dataset generator, event matching, campaign identity, or formal run entry.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

from . import _anomaly_v03_contract as c
from . import _anomaly_v03_io as storage
from . import _anomaly_v03_runtime as rt
from . import anomaly_v03 as v
from . import anomaly_v03_scoring as scoring
from .anomaly_v03_materializer import json_bytes, jsonl, sha

MAX_INPUT_BYTES = 16 * 1024 * 1024
MAX_INPUT_ROWS = 18000
PAYLOAD_NAMES = {"observations.jsonl", "preview.json", "scores.jsonl", "summary.md"}


def _check_input(raw):
    rt.require(type(raw) is bytes and 0 < len(raw) <= MAX_INPUT_BYTES, "observation bytes outside local preview limit")
    rt.require(0 < raw.count(b"\n") <= MAX_INPUT_ROWS, "observation rows outside local preview limit")


def _read_input(path):
    path = rt.regular_path(Path(path))
    rt.require(0 < path.stat().st_size <= MAX_INPUT_BYTES, "observation bytes outside local preview limit")
    with path.open("rb") as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    _check_input(raw)
    return raw


def _summary_bytes(report):
    counts = report["score_counts"]
    lines = ["# Local anomaly score preview", "", f"Candidate: {report['candidate_id']}",
             f"Status: {report['preview_status']}", f"Input rows: {report['input']['rows']}",
             f"Calibrated profiles: {report['calibrated_profiles']} / {len(report['profiles'])}",
             f"Score rows: {counts['total']} (available: {counts['available']}, unavailable: {counts['unavailable']})",
             f"Instantaneous threshold exceedances: {counts['threshold_exceeded']}", "",
             "Normal-prefix issues: " + (", ".join(report["normal_prefix_issues"]) or "none"), "",
             "Counts describe supplied observations only. An exceedance is not a confirmed anomaly event.",
             "Local development preview; performance not evaluated; formal permission not granted.", "",
             "| Target | Available | Unavailable | Threshold exceeded |", "| --- | ---: | ---: | ---: |"]
    for item in report["targets"]:
        lines.append(f"| {item['full_target']} | {item['available']} | {item['unavailable']} | {item['threshold_exceeded']} |")
    return ("\n".join(lines) + "\n").encode("utf-8")


def build_preview_payloads(raw: bytes, candidate: str) -> dict[str, bytes]:
    """Deterministic calculation, preserving unavailable rows and prefix defects."""
    _check_input(raw)
    computed = scoring.preview_saved_observations(candidate, raw, expected_sha256=sha(raw))
    profiles, scores = computed["profiles"], computed["scores"]
    targets = []
    exclusions = Counter()
    for full_target in c.FULL_TARGETS:
        rows = [row for row in scores if row["full_target"] == full_target]
        targets.append({"full_target": full_target, "available": sum(row["available"] for row in rows),
                        "unavailable": sum(not row["available"] for row in rows),
                        "threshold_exceeded": sum(row["threshold_exceeded"] for row in rows)})
    for row in scores:
        exclusions.update(row["exclusion_tags"])
    available = sum(row["available"] for row in scores)
    calibrated = sum(p["status"] == "calibrated" for p in profiles)
    report = {"format": "anomaly-v03-local-preview-v1", "scope": "local_development", "candidate_id": candidate,
              "input": {"raw_sha256": sha(raw), "bytes": len(raw), "rows": raw.count(b"\n")},
              "preview_status": "computed" if not computed["normal_prefix_issues"] and calibrated == 48 and available else "inconclusive",
              "coverage": "provided_observations_only", "normal_prefix_issues": computed["normal_prefix_issues"],
              "profiles": profiles, "calibrated_profiles": calibrated,
              "score_counts": {"total": len(scores), "available": available, "unavailable": len(scores)-available,
                               "threshold_exceeded": sum(row["threshold_exceeded"] for row in scores)},
              "targets": targets, "exclusion_tag_counts": dict(sorted(exclusions.items())),
              "performance_status": "not_evaluated", "formal_permission": False}
    return {"observations.jsonl": raw, "preview.json": json_bytes(report),
            "scores.jsonl": jsonl(scores), "summary.md": _summary_bytes(report)}


def _verify_payloads(files, *, expected_candidate=None):
    rt.require(set(files) == PAYLOAD_NAMES, "local preview payload inventory differs")
    report = v.strict_json(files["preview.json"])
    rt.require(type(report) is dict, "preview report must be an object")
    candidate = report.get("candidate_id")
    rt.require(expected_candidate is None or candidate == expected_candidate, "preview candidate changed")
    expected = build_preview_payloads(files["observations.jsonl"], candidate)
    for path, raw in expected.items():
        rt.require(files[path] == raw, "local preview recomputation differs: " + path)
    return v.strict_json(expected["preview.json"])


def _brief(report):
    return {name: report[name] for name in ("candidate_id", "preview_status", "input", "calibrated_profiles",
                                           "normal_prefix_issues", "score_counts", "performance_status", "formal_permission")}


def run_local_preview(observations: Path, parent: Path, name: str, *, candidate=c.CANDIDATES[0]):
    rt.require(type(candidate) is str and candidate in c.CANDIDATES, "unknown candidate")
    # Claim before input IO/calculation so duplicate requests do no expensive work.
    with storage.LocalPublication(parent, name) as store:
        store.write("observations.jsonl", _read_input(observations))
        payloads = build_preview_payloads(store.read("observations.jsonl"), candidate)
        for path in ("preview.json", "scores.jsonl", "summary.md"):
            store.write(path, payloads[path])
        receipt = store.publish(lambda files: _verify_payloads(files, expected_candidate=candidate), lambda: None)
    return {"receipt": receipt, "preview": _brief(v.strict_json(payloads["preview.json"]))}


def verify_local_preview(root: Path, *, marker_sha256: str):
    rt.require(type(marker_sha256) is str and re.fullmatch("[0-9a-f]{64}", marker_sha256), "invalid marker digest")
    captured = {}
    def verify(files):
        captured.update(_brief(_verify_payloads(files)))
    report = storage.verify_local_publication(root, expected_marker_sha256=marker_sha256, verify_semantics=verify)
    return {"verification": report, "preview": captured}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Local single-candidate score preview from saved v0.3 observations")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="calculate and save under a new result name")
    run.add_argument("--observations", type=Path, required=True)
    run.add_argument("--output-parent", type=Path, required=True)
    run.add_argument("--name", required=True)
    run.add_argument("--candidate", choices=c.CANDIDATES, default=c.CANDIDATES[0])
    verify = commands.add_parser("verify", help="recompute and verify a completed local result")
    verify.add_argument("--output", type=Path, required=True)
    verify.add_argument("--marker-sha256", required=True)
    compare = commands.add_parser("compare", help="verify and compare two or three saved candidates without writing files")
    compare.add_argument("--result", nargs=2, action="append", required=True, metavar=("OUTPUT", "MARKER_SHA256"))
    compare.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            result = run_local_preview(args.observations, args.output_parent, args.name, candidate=args.candidate)
        elif args.command == "verify":
            result = verify_local_preview(args.output, marker_sha256=args.marker_sha256)
        else:
            from .anomaly_v03_local_compare import compare_local_previews, comparison_markdown
            result = compare_local_previews(args.result)
            if args.format == "markdown":
                print(comparison_markdown(result), end="")
                return 0
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError) as error:
        print(json.dumps({"status": "failed", "error_type": type(error).__name__, "message": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
