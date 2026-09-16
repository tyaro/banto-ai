"""Read-only comparison of two or three verified local score previews."""
from __future__ import annotations

import re
from html import escape
from io import BytesIO
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

from . import _anomaly_v03_contract as c
from . import _anomaly_v03_io as storage
from . import _anomaly_v03_runtime as rt
from . import anomaly_v03 as v
from . import anomaly_v03_local_preview as preview


DEFAULT_DETAILS_LIMIT = 20
MAX_DETAILS_LIMIT = 100


@dataclass(frozen=True, slots=True)
class _Score:
    available: bool
    threshold_exceeded: bool
    timestamp_ms: int
    score: float | None
    residual: float | None
    phase: int | None
    mode: str
    recipe: str
    exclusion_tags: tuple[str, ...]


def _load_result(root, marker_sha256, *, keep_observations=False):
    rt.require(type(marker_sha256) is str and re.fullmatch("[0-9a-f]{64}", marker_sha256), "invalid marker digest")
    captured = {}
    def verify(files):
        report = preview._verify_payloads(files)
        # Compact records avoid retaining all parsed score dictionaries.
        decisions = {}
        for line in files["scores.jsonl"].splitlines():
            row = v.strict_json(line)
            key = (row["full_target"], row["sample"])
            rt.require(key not in decisions, "duplicate comparison score key")
            decisions[key] = _Score(row["available"], row["threshold_exceeded"], row["timestamp_ms"],
                                    row["score"], row["residual"], row["phase"], row["mode"], row["recipe"],
                                    tuple(row["exclusion_tags"]))
        captured.update(report=report, decisions=decisions,
                        observations=files["observations.jsonl"] if keep_observations else None)
    storage.verify_local_publication(Path(root), expected_marker_sha256=marker_sha256, verify_semantics=verify)
    return captured["report"], captured["decisions"], captured["observations"]


def _attach_observation_context(raw, details):
    """Select exact adjacent timestamps from a verified snapshot, after scoring.

    Retain only the displayed equipment/times, not the entire decoded input.
    The next observation is inspection context and never a scoring input here.
    """
    if not details:
        return
    rt.require(type(raw) is bytes, "verified observations required for context")
    wanted = {(item["full_target"].split(".", 1)[0], item["sample"]+offset)
              for item in details for offset in (-1, 0, 1)}
    selected = {}
    start = datetime.fromtimestamp(c.START_MS/1000, timezone.utc)
    for line in BytesIO(raw):
        row = v.strict_json(line)
        delta = datetime.fromisoformat(row["timestamp"]) - start
        sample = delta.days*86400 + delta.seconds
        key = row["equipment_id"], sample
        if key not in wanted:
            continue
        selected[key] = {"mode": row["operating_mode"], "recipe": row["recipe_step"],
                         "signals": [{"full_target": row["equipment_id"]+"."+target,
                                      "value": row["signals"][target]["value"], "unit": row["signals"][target]["unit"],
                                      "quality": row["quality"][target]} for target in c.TARGETS]}
    for item in details:
        equipment = item["full_target"].split(".", 1)[0]
        observations = []
        for offset, relation in ((-1, "previous"), (0, "current"), (1, "next")):
            sample = item["sample"]+offset
            source = selected.get((equipment, sample))
            observations.append({"sample": sample, "timestamp_ms": c.START_MS+sample*1000,
                                 "relation": relation, "present": source is not None,
                                 "mode": source["mode"] if source else None,
                                 "recipe": source["recipe"] if source else None,
                                 "signals": source["signals"] if source else []})
        item["observations"] = observations


def compare_local_previews(results, *, details_limit=DEFAULT_DETAILS_LIMIT, details_offset=0):
    """Recompute each completed result, require identical input, compare decisions.

    results contains (output_directory, marker_sha256) pairs. No file is written.
    Scores from different candidate definitions are not ranked or subtracted.
    """
    rt.require(2 <= len(results) <= len(c.CANDIDATES), "comparison requires two or three results")
    rt.require(type(details_limit) is int and 0 <= details_limit <= MAX_DETAILS_LIMIT, "details limit must be between 0 and 100")
    rt.require(type(details_offset) is int and details_offset >= 0, "details offset must be nonnegative")
    candidates, decisions_by_candidate = {}, {}
    common_input = None
    common_keys = None
    saved_observations = None
    for root, marker_sha256 in results:
        report, decisions, raw = _load_result(root, marker_sha256, keep_observations=common_input is None and details_limit > 0)
        candidate = report["candidate_id"]
        rt.require(candidate not in candidates, "duplicate comparison candidate")
        if common_input is None:
            common_input, common_keys = report["input"], set(decisions)
            saved_observations = raw
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
            left_score = decisions_by_candidate[left][key]
            right_score = decisions_by_candidate[right][key]
            if left_score.available and right_score.available:
                counts["both_available"] += 1
                counts["same_decision" if left_score.threshold_exceeded == right_score.threshold_exceeded else "different_decision"] += 1
            elif left_score.available:
                counts["only_left_available"] += 1
            elif right_score.available:
                counts["only_right_available"] += 1
            else:
                counts["neither_available"] += 1
        pairs.append({"left": left, "right": right, "total": len(common_keys), **counts})
    detail_rows, total_differences = [], 0
    for key in sorted(common_keys, key=lambda key: (key[1], key[0])):
        scores = [decisions_by_candidate[name][key] for name in ordered]
        kinds = []
        if len({row.threshold_exceeded for row in scores if row.available}) > 1:
            kinds.append("threshold_decision")
        if len({row.available for row in scores}) > 1:
            kinds.append("availability")
        if not kinds:
            continue
        index = total_differences
        total_differences += 1
        if not details_offset <= index < details_offset + details_limit:
            continue
        items = []
        for candidate, row in zip(ordered, scores):
            decision = ("threshold_exceeded" if row.threshold_exceeded else "below_or_at_threshold") if row.available else "unavailable"
            items.append({"candidate_id": candidate, "available": row.available, "decision": decision,
                          "score": row.score, "residual": row.residual, "phase": row.phase,
                          "mode": row.mode, "recipe": row.recipe, "exclusion_tags": list(row.exclusion_tags)})
        detail_rows.append({"sample": key[1], "timestamp_ms": scores[0].timestamp_ms, "full_target": key[0],
                            "difference_kinds": kinds, "candidates": items})
    _attach_observation_context(saved_observations, detail_rows)
    details = {"order": "sample_then_full_target", "total": total_differences, "offset": details_offset,
               "limit": details_limit, "shown": len(detail_rows), "omitted_before": min(details_offset, total_differences),
               "omitted_after": max(total_differences-details_offset-len(detail_rows), 0), "rows": detail_rows}
    return {"format": "anomaly-v03-local-comparison-v1", "scope": "local_development", "input": common_input,
            "comparison_status": "computed" if all(item["preview_status"] == "computed" for item in candidates.values()) else "inconclusive",
            "coverage": "provided_observations_only", "candidates": [candidates[name] for name in ordered],
            "pairs": pairs, "details": details, "performance_status": "not_evaluated", "formal_permission": False}


def _markdown_cell(value):
    # Units are free text in the input contract. Keep them inside one table cell.
    text = escape(str(value), quote=False).replace("|", "&#124;")
    text = re.sub(r"([\\`*_{}\[\]()!])", r"\\\1", text)
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def _observations_markdown(observations):
    lines = ["", "Saved observations (same equipment, all four scoring signals). Next is inspection only; it is not used to compute the displayed score.", "",
             "| Relative time / sample | Signal | Value | Unit | Quality | Mode / recipe |",
             "| --- | --- | ---: | --- | --- | --- |"]
    for observation in observations:
        relative = f"{observation['relation']} / {observation['sample']}"
        if not observation["present"]:
            lines.append(f"| {relative} | observation absent | n/a | n/a | n/a | n/a |")
            continue
        for signal in observation["signals"]:
            value = "null" if signal["value"] is None else repr(signal["value"])
            lines.append(f"| {relative} | {signal['full_target']} | {value} | {_markdown_cell(signal['unit'])} | {signal['quality']} | {_markdown_cell(observation['mode'])} / {_markdown_cell(observation['recipe'])} |")
    return lines


def _details_markdown(details):
    lines = ["", "## Difference details", "",
             f"Unique sample/target differences: {details['total']}; shown: {details['shown']}; offset: {details['offset']}; limit: {details['limit']}.",
             f"Omitted before: {details['omitted_before']}; omitted after: {details['omitted_after']}.", "",
             "Rows are ordered by sample, then target. Pairwise counts can include the same row more than once.",
             "Differences include threshold decisions among available candidates and availability mismatches."]
    if not details["rows"]:
        lines.extend(["", "No detail rows on this page; use the total and omitted counts above to distinguish an empty page from no differences."])
    for row in details["rows"]:
        timestamp = datetime.fromtimestamp(row["timestamp_ms"]/1000, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        lines.extend(["", f"### Sample {row['sample']} / {row['full_target']}", "",
                      f"UTC: {timestamp}; differences: {', '.join(row['difference_kinds'])}.", "",
                      "| Candidate | Decision | Score | Residual | Phase | Mode / recipe | Exclusions |",
                      "| --- | --- | ---: | ---: | ---: | --- | --- |"])
        for item in row["candidates"]:
            score = "n/a" if item["score"] is None else repr(item["score"])
            residual = "n/a" if item["residual"] is None else repr(item["residual"])
            phase = "n/a" if item["phase"] is None else str(item["phase"])
            exclusions = ", ".join(item["exclusion_tags"]) or "none"
            lines.append(f"| {item['candidate_id']} | {item['decision']} | {score} | {residual} | {phase} | {item['mode']} / {item['recipe']} | {exclusions} |")
        if "observations" in row:  # Previous detail JSON remains renderable.
            lines.extend(_observations_markdown(row["observations"]))
    return lines


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
    if "details" in report:  # Existing v1 comparison JSON remains renderable.
        lines.extend(_details_markdown(report["details"]))
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
