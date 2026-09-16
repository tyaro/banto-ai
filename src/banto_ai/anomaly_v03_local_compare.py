"""Read-only comparison of two or three verified local score previews."""
from __future__ import annotations

import re
from itertools import combinations
from pathlib import Path

from . import _anomaly_v03_contract as c
from . import _anomaly_v03_io as storage
from . import _anomaly_v03_runtime as rt
from . import anomaly_v03 as v
from . import anomaly_v03_local_preview as preview


def _load_result(root, marker_sha256):
    rt.require(type(marker_sha256) is str and re.fullmatch("[0-9a-f]{64}", marker_sha256), "invalid marker digest")
    captured = {}
    def verify(files):
        report = preview._verify_payloads(files)
        # Retain only the decisions needed for comparison after sequential replay.
        decisions = {}
        for line in files["scores.jsonl"].splitlines():
            row = v.strict_json(line)
            key = (row["full_target"], row["sample"])
            rt.require(key not in decisions, "duplicate comparison score key")
            decisions[key] = (row["available"], row["threshold_exceeded"])
        captured.update(report=report, decisions=decisions)
    storage.verify_local_publication(Path(root), expected_marker_sha256=marker_sha256, verify_semantics=verify)
    return captured["report"], captured["decisions"]


def compare_local_previews(results):
    """Recompute each completed result, require identical input, compare decisions.

    results contains (output_directory, marker_sha256) pairs. No file is written.
    Scores from different candidate definitions are not ranked or subtracted.
    """
    rt.require(2 <= len(results) <= len(c.CANDIDATES), "comparison requires two or three results")
    candidates, decisions_by_candidate = {}, {}
    common_input = None
    common_keys = None
    for root, marker_sha256 in results:
        report, decisions = _load_result(root, marker_sha256)
        candidate = report["candidate_id"]
        rt.require(candidate not in candidates, "duplicate comparison candidate")
        if common_input is None:
            common_input, common_keys = report["input"], set(decisions)
        rt.require(report["input"] == common_input, "comparison inputs differ")
        rt.require(set(decisions) == common_keys, "comparison score keys differ")
        candidates[candidate] = {name: report[name] for name in (
            "candidate_id", "preview_status", "normal_prefix_issues", "calibrated_profiles",
            "score_counts", "targets", "exclusion_tag_counts")}
        candidates[candidate]["marker_raw_sha256"] = marker_sha256
        decisions_by_candidate[candidate] = decisions
    ordered = [candidate for candidate in c.CANDIDATES if candidate in candidates]
    pairs = []
    for left, right in combinations(ordered, 2):
        counts = dict.fromkeys(("both_available", "same_decision", "different_decision",
                                "only_left_available", "only_right_available", "neither_available"), 0)
        for key in common_keys:
            left_available, left_exceeded = decisions_by_candidate[left][key]
            right_available, right_exceeded = decisions_by_candidate[right][key]
            if left_available and right_available:
                counts["both_available"] += 1
                counts["same_decision" if left_exceeded == right_exceeded else "different_decision"] += 1
            elif left_available:
                counts["only_left_available"] += 1
            elif right_available:
                counts["only_right_available"] += 1
            else:
                counts["neither_available"] += 1
        pairs.append({"left": left, "right": right, "total": len(common_keys), **counts})
    return {"format": "anomaly-v03-local-comparison-v1", "scope": "local_development", "input": common_input,
            "comparison_status": "computed" if all(item["preview_status"] == "computed" for item in candidates.values()) else "inconclusive",
            "coverage": "provided_observations_only", "candidates": [candidates[name] for name in ordered],
            "pairs": pairs, "performance_status": "not_evaluated", "formal_permission": False}


def comparison_markdown(report):
    """Display verified counts and coverage, without a performance winner."""
    lines = ["# Local anomaly score comparison", "", f"Status: {report['comparison_status']}",
             f"Input rows: {report['input']['rows']}", f"Input SHA256: {report['input']['raw_sha256']}", "",
             "| Candidate | Status | Calibrated / 48 | Scores | Available | Unavailable | Threshold exceeded |",
             "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for item in report["candidates"]:
        counts = item["score_counts"]
        lines.append(f"| {item['candidate_id']} | {item['preview_status']} | {item['calibrated_profiles']} | {counts['total']} | {counts['available']} | {counts['unavailable']} | {counts['threshold_exceeded']} |")
    lines.extend(["", "## Decision agreement", "",
                  "Only rows available to both candidates enter same/different decision counts. Unavailable is not a negative decision.", "",
                  "| Left | Right | Both available | Same | Different | Left only | Right only | Neither |",
                  "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |"])
    for pair in report["pairs"]:
        lines.append(f"| {pair['left']} | {pair['right']} | {pair['both_available']} | {pair['same_decision']} | {pair['different_decision']} | {pair['only_left_available']} | {pair['only_right_available']} | {pair['neither_available']} |")
    lines.extend(["", "## Targets", "", "| Target | Candidate | Available | Unavailable | Threshold exceeded |",
                  "| --- | --- | ---: | ---: | ---: |"])
    for full_target in c.FULL_TARGETS:
        for candidate in report["candidates"]:
            target = next(item for item in candidate["targets"] if item["full_target"] == full_target)
            lines.append(f"| {full_target} | {candidate['candidate_id']} | {target['available']} | {target['unavailable']} | {target['threshold_exceeded']} |")
    lines.extend(["", "## Input and availability notes", ""])
    for candidate in report["candidates"]:
        prefix = ", ".join(candidate["normal_prefix_issues"]) or "none"
        exclusions = ", ".join(f"{tag}={count}" for tag, count in candidate["exclusion_tag_counts"].items()) or "none"
        lines.append(f"- {candidate['candidate_id']}: normal-prefix issues: {prefix}; exclusion tags: {exclusions}.")
    lines.extend(["", "Exclusion tags may overlap. Counts describe supplied observations only.",
                  "Threshold exceedances are instantaneous decisions, not confirmed anomaly events.",
                  "Scores have candidate-specific definitions; this comparison does not rank detection performance.",
                  "Local development comparison; performance not evaluated; formal permission not granted."])
    return "\n".join(lines) + "\n"
