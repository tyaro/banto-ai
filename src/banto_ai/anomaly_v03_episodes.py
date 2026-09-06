"""S2 label-free episodes, first-onset matching and fixed-denominator accounting.

These pure functions consume in-memory ledgers, not artifacts. Recomputing
episode structure is mandatory before using event labels. This is producer
logic, NOT an independent S6 audit, CI estimator or promotion decision.
"""

from __future__ import annotations

import math
from copy import deepcopy

from . import _anomaly_v03_contract as c
from . import anomaly_v03 as v
from ._anomaly_v03_numeric import median
from ._anomaly_v03_schema import common_defs

__all__ = ["build_episodes", "match_incidents", "scheduled_clean_mask", "account_metrics"]


def _source_order(row):
    return row["onset_ms"], row["full_target"], row["episode_id"]


def build_episodes(scores: list[dict]) -> tuple[list, list, list]:
    """Return fresh score backlinks/streaks, source episodes and merged episodes.

    Incoming streak/backlink fields are provisional; threshold and availability
    claims are checked. Matching subsequently compares ALL reconstructed fields
    and intervals with the supplied ledgers, including missing/truncated runs.
    """
    v.require(type(scores) is list, "score ledger must be an array")
    defs = common_defs()
    result, sources, previous, active, ids = deepcopy(scores), [], {}, {}, set()
    for row in result:
        v._shape(row, {**defs["score"], "$defs": defs})
        v.require(row["score_id"] not in ids, "duplicate score ID")
        ids.add(row["score_id"])
        v.require(row["timestamp_ms"] == c.START_MS+row["sample"]*1000, "score time mismatch")
        v.require(row["full_target"].startswith(row["equipment"]+"."), "score equipment mismatch")
        v.require(row["recipe"] == c.RECIPES[c.MODES.index(row["mode"])], "score recipe mismatch")
        key = (row["dataset_id"], row["candidate_id"], row["full_target"])
        old = previous.get(key)
        v.require(old is None or row["timestamp_ms"] > old["timestamp_ms"], "duplicate/reversed score time")
        previous[key] = row
        threshold = 4.0 if row["candidate_id"] == c.CANDIDATES[0] else 6.0
        if row["available"]:
            v.require(row["score"] is not None and row["score"] >= 0 and row["residual"] is not None
                      and row["phase"] not in (None, 0) and not row["exclusion_tags"] and row["exclusion_reason"] is None,
                      "invalid available episode input")
            exceeded = row["score"] > threshold
        else:
            v.require(row["score"] is None and bool(row["exclusion_tags"])
                      and row["exclusion_reason"] == next(r for r in c.REASONS if r in row["exclusion_tags"]), "invalid unavailable episode input")
            exceeded = False
        v.require(row["threshold_exceeded"] == exceeded, "threshold claim disagrees with strict comparison")
        row.update(streak=0, source_episode_id=None)
        same_run = (old is not None and old["threshold_exceeded"] and exceeded
                    and row["timestamp_ms"] == old["timestamp_ms"]+1000
                    and all(row[k] == old[k] for k in ("equipment", "mode", "recipe", "profile_id"))
                    and row["phase"] == old["phase"]+1)
        if not same_run:
            active.pop(key, None)
        if not exceeded:
            continue
        row["streak"] = old["streak"]+1 if same_run else 1
        if row["streak"] == 2:
            source = {"episode_id": row["score_id"]+"-source", "dataset_id": row["dataset_id"], "candidate_id": row["candidate_id"],
                      "equipment": row["equipment"], "full_target": row["full_target"], "mode": row["mode"], "recipe": row["recipe"],
                      "visit_start_sample": row["sample"]-row["phase"], "profile_id": row["profile_id"],
                      "onset_ms": row["timestamp_ms"], "end_ms": row["timestamp_ms"]+1000,
                      "support_score_ids": [old["score_id"], row["score_id"]]}
            active[key] = source
            sources.append(source)
        if row["streak"] >= 2:
            active[key]["end_ms"] = row["timestamp_ms"]+1000
            row["source_episode_id"] = active[key]["episode_id"]
    sources.sort(key=lambda r: (r["dataset_id"], r["candidate_id"], r["equipment"], *_source_order(r)))
    groups = {}
    for source in sources:
        key = tuple(source[k] for k in ("dataset_id", "candidate_id", "equipment", "mode", "recipe", "visit_start_sample"))
        groups.setdefault(key, []).append(source)
    equipment = []
    for key, group in groups.items():
        merged = None
        for source in sorted(group, key=_source_order):
            if merged is None or source["onset_ms"] > merged["end_ms"]:
                merged = dict(zip(("dataset_id", "candidate_id", "equipment", "mode", "recipe", "visit_start_sample"), key))
                merged.update(episode_id=source["episode_id"]+"-equipment", onset_ms=source["onset_ms"], end_ms=source["end_ms"],
                              source_episode_ids=[], matched_event_id=None, context_tags=[])
                equipment.append(merged)
            merged["end_ms"] = max(merged["end_ms"], source["end_ms"])
            merged["source_episode_ids"].append(source["episode_id"])
    equipment.sort(key=lambda r: (r["onset_ms"], r["episode_id"]))
    return result, sources, equipment


def _validate_structure(identity, events, profiles, scores, source_episodes, equipment_episodes):
    # Clear only evaluator annotations, never change score/source/time evidence.
    neutral = deepcopy(equipment_episodes)
    for row in neutral:
        row["matched_event_id"] = None
        row["context_tags"] = []
    v.validate_ledger_rows(identity, events=events, profiles=profiles, scores=scores,
                          source_episodes=source_episodes, equipment_episodes=neutral, incidents=[])
    recomputed_scores, sources, equipment = build_episodes(scores)
    v.require(v.canonical_json(scores) == v.canonical_json(recomputed_scores), "score streak/backlink reconstruction mismatch")
    v.require(v.canonical_json(source_episodes) == v.canonical_json(sources), "source episode reconstruction mismatch")
    v.require(v.canonical_json(neutral) == v.canonical_json(equipment), "equipment merge reconstruction mismatch")


def _context(episode, events):
    tags = set()
    onset = episode["onset_ms"]
    own = [e for e in events if e["equipment"] == episode["equipment"]]
    for event in own:
        if event["start_ms"] <= onset < event["end_ms"]:
            tags.add("raw-event")
        elif event["end_ms"] <= onset < event["window_end_ms"]:
            tags.add("grace")
        if event["start_ms"] <= onset < event["window_end_ms"]:
            if event["event_class"] == "data_quality":
                tags.add("quality")
            elif event["event_class"] == "ignored":
                tags.add("ignored")
        if onset < event["start_ms"] < episode["end_ms"]:
            tags.add("pre-event")
    if not any(e["start_ms"] <= onset < e["window_end_ms"] for e in own):
        tags.add("clean")
    return [tag for tag in ("raw-event", "grace", "clean", "quality", "ignored", "pre-event") if tag in tags]


def match_incidents(identity: dict, *, events: list, profiles: list, scores: list,
                    source_episodes: list, equipment_episodes: list) -> tuple[list, list]:
    """Validate first, enumerate all candidates, claim first, never retry."""
    _validate_structure(identity, events, profiles, scores, source_episodes, equipment_episodes)
    episodes, claims, incidents = deepcopy(equipment_episodes), set(), []
    sources = {row["episode_id"]: row for row in source_episodes}
    score_map = {row["score_id"]: row for row in scores}
    for episode in episodes:
        episode["matched_event_id"] = None
        episode["context_tags"] = _context(episode, events)
    positives = sorted((e for e in events if e["event_class"] in ("machine", "sensor")), key=lambda e: (e["start_ms"], e["event_id"]))
    for event in positives:
        candidates = sorted((e for e in episodes if e["episode_id"] not in claims and e["equipment"] == event["equipment"]
                             and e["dataset_id"] == event["dataset_id"] and event["start_ms"] <= e["onset_ms"] < event["window_end_ms"]),
                            key=lambda e: (e["onset_ms"], e["episode_id"]))
        incident = {"dataset_id": event["dataset_id"], "event_id": event["event_id"], "status": "processed",
                    "candidate_count": len(candidates), "candidate_episode_ids": [e["episode_id"] for e in candidates],
                    "selected_candidate_episode_id": None, "selected_source_episode_id": None, "support_score_ids": [],
                    "reason": "no_candidate_in_window", "matched_episode_id": None, "causal_detected": False,
                    "delay_seconds": None, "secondary_canonical_detected": None}
        if candidates:
            selected = candidates[0]
            incident["selected_candidate_episode_id"] = selected["episode_id"]
            claims.add(selected["episode_id"])
            target_sources = [sources[sid] for sid in selected["source_episode_ids"]
                              if sources[sid]["full_target"] == event["full_target"] and sources[sid]["onset_ms"] == selected["onset_ms"]]
            v.require(len(target_sources) <= 1, "multiple same-target same-onset sources")
            incident["reason"] = "first_candidate_no_target_onset"
            if target_sources:
                source = target_sources[0]
                incident.update(selected_source_episode_id=source["episode_id"], support_score_ids=list(source["support_score_ids"]),
                                reason="first_candidate_noncausal_support")
                if all(event["start_ms"] <= score_map[sid]["timestamp_ms"] < event["window_end_ms"] for sid in source["support_score_ids"]):
                    incident.update(reason="causal_detected", causal_detected=True, matched_episode_id=selected["episode_id"],
                                    delay_seconds=(selected["onset_ms"]-event["start_ms"])/1000)
                    selected["matched_event_id"] = event["event_id"]
        incidents.append(incident)
    v.validate_ledger_rows(identity, events=events, profiles=profiles, scores=scores, source_episodes=source_episodes,
                          equipment_episodes=episodes, incidents=incidents)
    return incidents, episodes


def scheduled_clean_mask(identity: dict, events: list) -> frozenset:
    """Equipment-second coordinates, subtracting all planned windows in core too."""
    v.require(v.canonical_json(events) == v.canonical_json(v.event_inventory(identity)), "planned event inventory mismatch")
    mask = {(e, sample) for e in c.EQUIPMENT for sample in range(7200, 9000)}
    for event in events:
        mask.difference_update((event["equipment"], sample) for sample in range(event["start_sample"], event["window_end_sample"]))
    v.require(len(mask) == 3365, "scheduled clean equipment-time mismatch")
    return frozenset(mask)


def _metric(numerator, denominator, name="ratio"):
    value = None if denominator == 0 else (8*numerator/(denominator/3600) if name == "clean" else
                                           (100*numerator/denominator if name == "burden" else numerator/denominator))
    return {"numerator": numerator, "denominator": denominator, "value": value,
            "ci_status": "inconclusive" if denominator == 0 else "not_evaluated", "ci_lower": None, "ci_upper": None, "null_replicates": 0}


def account_metrics(identity: dict, *, events: list, profiles: list, scores: list,
                    source_episodes: list, equipment_episodes: list, incidents: list) -> dict:
    """Complete per-evaluation raw accounting only. Missing rows raise, not miss.

    No bootstrap/CI/gates/promotion. All 20 positives and 8*1800 origins must be
    present. Inconclusive profiles and real quality exclusions remain in place.
    """
    expected_incidents, expected_episodes = match_incidents(identity, events=events, profiles=profiles, scores=scores,
                                                          source_episodes=source_episodes, equipment_episodes=equipment_episodes)
    v.require(v.canonical_json(incidents) == v.canonical_json(expected_incidents), "incident recomputation mismatch")
    v.require(v.canonical_json(equipment_episodes) == v.canonical_json(expected_episodes), "matched/context episode mismatch")
    coordinates = {(row["full_target"], row["sample"]) for row in scores}
    v.require(coordinates == {(t, s) for t in c.FULL_TARGETS for s in range(7200, 9000)} and len(scores) == 14400, "incomplete planned score origins")
    v.require(len(profiles) == 48, "incomplete planned profiles")
    clean = scheduled_clean_mask(identity, events)
    effective = clean & {(s["equipment"], s["sample"]) for s in scores if s["available"]}
    unmatched = [e for e in equipment_episodes if e["matched_event_id"] is None]
    false_clean = sum((e["equipment"], (e["onset_ms"]-c.START_MS)//1000) in clean for e in unmatched)
    event_map = {e["event_id"]: e for e in events}
    counts = {kind: sum(i["causal_detected"] and event_map[i["event_id"]]["event_class"] == kind for i in incidents) for kind in ("machine", "sensor")}
    delays = [i["delay_seconds"] for i in incidents if i["causal_detected"]]
    summary = {"count": len(delays), "median": median(delays) if delays else None,
               "mean": math.fsum(delays)/len(delays) if delays else None, "min": min(delays) if delays else None, "max": max(delays) if delays else None,
               "conditioned_on": "causal-detected-only", "undetected_fill": "forbidden", "unit": "seconds"}
    metrics = {"machine_recall": _metric(counts["machine"], 10), "sensor_recall": _metric(counts["sensor"], 10),
               "precision": _metric(len(delays), len(equipment_episodes)), "clean_rate": _metric(false_clean, len(clean), "clean"),
               "false_alert_burden": _metric(len(unmatched), 20, "burden"),
               "availability": [{"full_target": t, "metric": _metric(sum(s["available"] for s in scores if s["full_target"] == t), 1800)} for t in c.FULL_TARGETS],
               "scheduled_clean_seconds": len(clean), "effective_clean_seconds": len(effective),
               "effective_clean_rate": 8*false_clean/(len(effective)/3600) if effective else None, "delay_summary": summary}
    v._reported_metrics(metrics, datasets=1)
    return metrics
