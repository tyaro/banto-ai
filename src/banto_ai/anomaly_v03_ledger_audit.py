"""Independent ledger reconstruction from supplied scores, using only stdlib.

Implements plan sections 4.3/5.1/5.2 without producer scoring, episode, matching
or accounting helpers. Does NOT independently establish profiles or score values.
The IO caller must validate/pin the event inventory and enclosing result schema.
"""
from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict

START_MS = 1767225600000
EQUIPMENT = ("motor-01", "conveyor-01")
TARGETS = tuple(e + "." + t for e in EQUIPMENT for t in
                ("motor_current", "motor_temperature", "conveyor_speed", "vibration_feature"))
THRESHOLDS = {"c0-diff-control": 4.0, "c1-phase-level": 6.0, "c2-phase-conditional": 6.0}
REASONS = ("current_target_quality", "current_nonfinite", "no_previous_or_gap",
           "previous_target_quality_or_nonfinite", "mode_recipe_or_phase", "peer_quality_or_nonfinite",
           "profile_inconclusive", "nonfinite_score")


def need(condition, reason):
    if not condition:
        raise ValueError("ledger audit: " + reason)


def exact(actual, expected, reason):
    need(json.dumps(actual, sort_keys=True, separators=(",", ":"), allow_nan=False) ==
         json.dumps(expected, sort_keys=True, separators=(",", ":"), allow_nan=False), reason)


def _unique(rows, field):
    result = {row[field]: row for row in rows}
    need(len(result) == len(rows), "duplicate " + field)
    return result


def reconstruct_episodes(scores):
    """Partition each target's ordered rows into maximal threshold runs."""
    _unique(scores, "score_id")
    by_target = defaultdict(list)
    for row in scores:
        need(type(row["sample"]) is int and row["timestamp_ms"] == START_MS + 1000 * row["sample"], "score coordinate")
        need(row["full_target"] in TARGETS and row["full_target"].startswith(row["equipment"] + "."), "score target")
        need(type(row["available"]) is bool, "availability type")
        if row["available"]:
            need(type(row["score"]) in (int, float) and math.isfinite(row["score"]) and row["score"] >= 0,
                 "available score is not finite")
            need(type(row["phase"]) is int and 0 < row["phase"] < 30 and row["residual"] is not None
                 and not row["exclusion_tags"] and row["exclusion_reason"] is None, "available row exclusions/phase")
            exceeded = row["score"] > THRESHOLDS[row["candidate_id"]]
        else:
            tags = row["exclusion_tags"]
            need(row["score"] is None and tags and set(tags) <= set(REASONS), "unavailable row exclusions")
            need(row["exclusion_reason"] == next(reason for reason in REASONS if reason in tags), "exclusion priority")
            exceeded = False
        exact(row["threshold_exceeded"], exceeded, "strict threshold differs")
        key = tuple(row[k] for k in ("dataset_id", "candidate_id", "full_target"))
        chain = by_target[key]
        need(not chain or chain[-1]["timestamp_ms"] < row["timestamp_ms"], "reversed or duplicate score origin")
        chain.append(row)

    sources = []
    def finish(run):
        if not run:
            return
        source_id = run[1]["score_id"] + "-source" if len(run) > 1 else None
        for position, row in enumerate(run):
            exact([row["streak"], row["source_episode_id"]],
                  [position + 1, source_id if position else None], "streak/backlink differs")
        if len(run) > 1:
            onset = run[1]
            sources.append({**{k: onset[k] for k in ("dataset_id", "candidate_id", "equipment", "full_target", "mode", "recipe", "profile_id")},
                "episode_id": source_id, "visit_start_sample": onset["sample"] - onset["phase"],
                "onset_ms": onset["timestamp_ms"], "end_ms": run[-1]["timestamp_ms"] + 1000,
                "support_score_ids": [run[0]["score_id"], onset["score_id"]]})
    for chain in by_target.values():
        run = []
        for row in chain:
            connects = run and row["timestamp_ms"] == run[-1]["timestamp_ms"] + 1000 and all(
                row[k] == run[-1][k] for k in ("equipment", "mode", "recipe", "profile_id")) and row["phase"] == run[-1]["phase"] + 1
            if not row["threshold_exceeded"] or not connects:
                finish(run)
                run = []
            if row["threshold_exceeded"]:
                run.append(row)
            else:
                exact([row["streak"], row["source_episode_id"]], [0, None], "non-exceeding backlink")
        finish(run)
    sources.sort(key=lambda s: tuple(s[k] for k in ("dataset_id", "candidate_id", "equipment", "onset_ms", "full_target", "episode_id")))
    visits = defaultdict(list)
    fields = ("dataset_id", "candidate_id", "equipment", "mode", "recipe", "visit_start_sample")
    for source in sources:
        visits[tuple(source[k] for k in fields)].append(source)
    merged = []
    for visit, intervals in visits.items():
        components = []
        for source in sorted(intervals, key=lambda x: (x["onset_ms"], x["full_target"], x["episode_id"])):
            if not components or source["onset_ms"] > max(s["end_ms"] for s in components[-1]):
                components.append([])
            components[-1].append(source)
        for component in components:
            merged.append({**dict(zip(fields, visit)), "episode_id": component[0]["episode_id"] + "-equipment",
                "onset_ms": min(s["onset_ms"] for s in component), "end_ms": max(s["end_ms"] for s in component),
                "source_episode_ids": [s["episode_id"] for s in component], "matched_event_id": None, "context_tags": []})
    merged.sort(key=lambda x: (x["onset_ms"], x["episode_id"]))
    return sources, merged


def reconstruct_matching(events, scores, sources, merged):
    """Claim the earliest group before examining target/support; never retry."""
    _unique(events, "event_id")
    source_by_id, score_by_id = _unique(sources, "episode_id"), _unique(scores, "score_id")
    groups = [{**row, "source_episode_ids": list(row["source_episode_ids"])} for row in merged]
    for group in groups:
        own = [e for e in events if e["equipment"] == group["equipment"]]
        t, end = group["onset_ms"], group["end_ms"]
        in_window = [e for e in own if e["start_ms"] <= t < e["window_end_ms"]]
        tags = {"raw-event": any(e["start_ms"] <= t < e["end_ms"] for e in own),
                "grace": any(e["end_ms"] <= t < e["window_end_ms"] for e in own), "clean": not in_window,
                "quality": any(e["event_class"] == "data_quality" for e in in_window),
                "ignored": any(e["event_class"] == "ignored" for e in in_window),
                "pre-event": any(t < e["start_ms"] < end for e in own)}
        group["context_tags"] = [key for key, present in tags.items() if present]
        group["matched_event_id"] = None
    claims, incidents = set(), []
    for event in sorted((e for e in events if e["event_class"] in ("machine", "sensor")), key=lambda e: (e["start_ms"], e["event_id"])):
        candidates = sorted((g for g in groups if g["episode_id"] not in claims and
            (g["dataset_id"], g["equipment"]) == (event["dataset_id"], event["equipment"])
            and event["start_ms"] <= g["onset_ms"] < event["window_end_ms"]), key=lambda g: (g["onset_ms"], g["episode_id"]))
        item = {"dataset_id": event["dataset_id"], "event_id": event["event_id"], "status": "processed",
            "candidate_count": len(candidates), "candidate_episode_ids": [g["episode_id"] for g in candidates],
            "selected_candidate_episode_id": None, "selected_source_episode_id": None, "support_score_ids": [],
            "reason": "no_candidate_in_window", "matched_episode_id": None, "causal_detected": False,
            "delay_seconds": None, "secondary_canonical_detected": None}
        if candidates:
            first = candidates[0]
            claims.add(first["episode_id"])
            item["selected_candidate_episode_id"] = first["episode_id"]
            item["reason"] = "first_candidate_no_target_onset"
            eligible = [source_by_id[s] for s in first["source_episode_ids"] if
                        source_by_id[s]["full_target"] == event["full_target"] and source_by_id[s]["onset_ms"] == first["onset_ms"]]
            need(len(eligible) <= 1, "multiple onset sources for target")
            if eligible:
                source = eligible[0]
                item.update(selected_source_episode_id=source["episode_id"], support_score_ids=list(source["support_score_ids"]),
                            reason="first_candidate_noncausal_support")
                times = [score_by_id[s]["timestamp_ms"] for s in source["support_score_ids"]]
                if event["start_ms"] <= min(times) and max(times) < event["window_end_ms"]:
                    item.update(causal_detected=True, reason="causal_detected", matched_episode_id=first["episode_id"],
                                delay_seconds=(first["onset_ms"] - event["start_ms"]) / 1000)
                    first["matched_event_id"] = event["event_id"]
        incidents.append(item)
    return incidents, groups


def _ratio(numerator, denominator, multiplier=1):
    return {"numerator": numerator, "denominator": denominator,
        "value": numerator * multiplier / denominator if denominator else None,
        "ci_status": "not_evaluated" if denominator else "inconclusive",
        "ci_lower": None, "ci_upper": None, "null_replicates": 0}


def _numeric_equal(actual, expected, path="metrics"):
    if type(expected) is dict:
        need(type(actual) is dict and actual.keys() == expected.keys(), path + " fields")
        for name, value in expected.items():
            _numeric_equal(actual[name], value, path + "." + name)
    elif type(expected) is list:
        need(type(actual) is list and len(actual) == len(expected), path + " length")
        for i, value in enumerate(expected):
            _numeric_equal(actual[i], value, path + "." + str(i))
    elif type(expected) is float:
        need(type(actual) in (int, float) and math.isfinite(actual) and
             math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), path + " value")
    else:
        need(type(actual) is type(expected) and actual == expected, path + " literal")


def audit_evaluation(result):
    """Audit complete score→episode→incident→metric ledgers, not score derivation."""
    scores, events = result["scores"], result["events"]
    need(len(scores) == 14400 and {(s["full_target"], s["sample"]) for s in scores} ==
         {(target, sample) for target in TARGETS for sample in range(7200, 9000)}, "planned score coverage")
    need(len(result["profiles"]) == 48, "planned profile count")
    need(len(events) == 40 and all(sum(e["event_class"] == kind for e in events) == 10
         for kind in ("machine", "sensor", "data_quality", "ignored")), "planned event count")
    sources, groups = reconstruct_episodes(scores)
    exact(result["source_episodes"], sources, "source episode reconstruction")
    incidents, groups = reconstruct_matching(events, scores, sources, groups)
    exact(result["equipment_episodes"], groups, "equipment merge/match/context reconstruction")
    exact(result["incidents"], incidents, "incident selection/support reconstruction")
    # Interval membership rather than producer's subtractive set implementation.
    clean = {(equipment, sample) for equipment in EQUIPMENT for sample in range(7200, 9000)
             if not any(e["equipment"] == equipment and e["start_sample"] <= sample < e["window_end_sample"] for e in events)}
    need(len(clean) == 3365, "scheduled clean denominator")
    available = {(s["equipment"], s["sample"]) for s in scores if s["available"]}
    effective = len(clean.intersection(available))
    unmatched = [g for g in groups if g["matched_event_id"] is None]
    false_clean = sum((g["equipment"], (g["onset_ms"] - START_MS) // 1000) in clean for g in unmatched)
    kinds = {e["event_id"]: e["event_class"] for e in events}
    detected = [i for i in incidents if i["causal_detected"]]
    delays = [i["delay_seconds"] for i in detected]
    metrics = {"machine_recall": _ratio(sum(kinds[i["event_id"]] == "machine" for i in detected), 10),
        "sensor_recall": _ratio(sum(kinds[i["event_id"]] == "sensor" for i in detected), 10),
        "precision": _ratio(len(detected), len(groups)), "clean_rate": _ratio(false_clean, len(clean), 28800),
        "false_alert_burden": _ratio(len(unmatched), 20, 100),
        "availability": [{"full_target": target, "metric": _ratio(sum(s["available"] for s in scores if s["full_target"] == target), 1800)} for target in TARGETS],
        "scheduled_clean_seconds": len(clean), "effective_clean_seconds": effective,
        "effective_clean_rate": 28800 * false_clean / effective if effective else None,
        "delay_summary": {"count": len(delays), "median": statistics.median(delays) if delays else None,
            "mean": math.fsum(delays) / len(delays) if delays else None, "min": min(delays) if delays else None,
            "max": max(delays) if delays else None, "conditioned_on": "causal-detected-only", "undetected_fill": "forbidden", "unit": "seconds"}}
    _numeric_equal(result["metrics"], metrics)
    return {"status": "ledger_checks_passed", "score_rows": len(scores), "source_episodes": len(sources),
            "equipment_episodes": len(groups), "incidents": len(incidents), "metrics": metrics,
            "score_derivation_verified": False, "independent_s6_complete": False, "performance_status": "not_evaluated"}
