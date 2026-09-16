"""Hand-counted plan fixtures; no registered observations or producer helpers."""
import ast
import copy
import inspect
import unittest

from banto_ai import anomaly_v03_ledger_audit as a


def score(target, sample, value=0.0, *, available=True, phase=None):
    phase = sample % 30 if phase is None else phase
    return {"score_id": f"score-{target}-{sample}", "dataset_id": "dataset", "candidate_id": "c1-phase-level",
        "equipment": target.split('.')[0], "full_target": target, "sample": sample,
        "timestamp_ms": a.START_MS + sample * 1000, "mode": "nominal", "recipe": "run",
        "profile_id": "profile-" + target, "phase": phase, "available": available,
        "residual": 0.0 if available else None, "score": value if available else None,
        "threshold_exceeded": available and value > 6, "streak": 0, "source_episode_id": None,
        "exclusion_reason": None if available else "mode_recipe_or_phase",
        "exclusion_tags": [] if available else ["mode_recipe_or_phase"]}


def event(kind, start, number=0):
    return {"dataset_id": "dataset", "event_id": f"event-{number:02d}-{kind}", "equipment": "motor-01",
        "full_target": "motor-01.motor_current", "event_class": kind, "enabled": kind != "data_quality",
        "start_sample": start, "end_sample": start + 3, "window_end_sample": start + 6,
        "start_ms": a.START_MS + start * 1000, "end_ms": a.START_MS + (start + 3) * 1000,
        "window_end_ms": a.START_MS + (start + 6) * 1000}


def matching_case(target_offsets, other_offsets=(), *, mode_entry=False, equal_offset=None):
    origin = 7290 if mode_entry else 7297
    rows = []
    for target, exceeds in (("motor-01.motor_current", target_offsets), ("motor-01.motor_temperature", other_offsets)):
        streak, backlink = 0, None
        for offset in range(-3, 8):
            row = score(target, origin + offset, 7.0 if offset in exceeds else 0.0,
                        available=not (mode_entry and offset == 0))
            if offset == equal_offset:
                row.update(score=6.0, threshold_exceeded=False)
            if row["threshold_exceeded"]:
                streak += 1
                if streak == 2:
                    backlink = row["score_id"] + "-source"
                row.update(streak=streak, source_episode_id=backlink)
            else:
                streak, backlink = 0, None
            rows.append(row)
    return event("machine", origin), rows


def zero_result():
    rows = [score(target, sample, available=sample % 30 != 0)
            for target in a.TARGETS for sample in range(7200, 9000)]
    events = []
    for cycle in range(10):
        starts = [0, 7, 8 if cycle == 9 else 14, 21]
        for kind, offset in zip(("machine", "sensor", "data_quality", "ignored"), starts):
            events.append(event(kind, 7200 + cycle * 180 + offset, cycle))
    positives = sorted((e for e in events if e["event_class"] in ("machine", "sensor")), key=lambda e: (e["start_ms"], e["event_id"]))
    incidents = [{"dataset_id": "dataset", "event_id": e["event_id"], "status": "processed",
        "candidate_count": 0, "candidate_episode_ids": [], "selected_candidate_episode_id": None,
        "selected_source_episode_id": None, "support_score_ids": [], "reason": "no_candidate_in_window",
        "matched_episode_id": None, "causal_detected": False, "delay_seconds": None,
        "secondary_canonical_detected": None} for e in positives]
    def metric(n, d, value):
        return {"numerator": n, "denominator": d, "value": value, "ci_status": "not_evaluated" if d else "inconclusive",
                "ci_lower": None, "ci_upper": None, "null_replicates": 0}
    # 120 mode entry equipment-seconds minus ten entries already excluded by
    # planned event windows = 110 fewer effective seconds than scheduled clean.
    metrics = {"machine_recall": metric(0, 10, 0.0), "sensor_recall": metric(0, 10, 0.0),
        "precision": metric(0, 0, None), "clean_rate": metric(0, 3365, 0.0), "false_alert_burden": metric(0, 20, 0.0),
        "availability": [{"full_target": t, "metric": metric(1740, 1800, 1740 / 1800)} for t in a.TARGETS],
        "scheduled_clean_seconds": 3365, "effective_clean_seconds": 3255, "effective_clean_rate": 0.0,
        "delay_summary": {"count": 0, "median": None, "mean": None, "min": None, "max": None,
                          "conditioned_on": "causal-detected-only", "undetected_fill": "forbidden", "unit": "seconds"}}
    return {"scores": rows, "events": events, "profiles": [{"status": "calibrated"} for _ in range(48)],
            "source_episodes": [], "equipment_episodes": [], "incidents": incidents, "metrics": metrics}


class LedgerAuditTests(unittest.TestCase):
    def test_numerical_module_imports_only_standard_library(self):
        tree = ast.parse(inspect.getsource(a))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                self.assertEqual(node.level, 0)
                imports.append(node.module)
        self.assertEqual(set(imports), {"__future__", "json", "math", "statistics", "collections"})

    def test_M1_to_M8_hand_matching_cases(self):
        cases = [
            ({-1, 0, 3, 4}, (), {}, 2, "first_candidate_noncausal_support", None),
            ({0, 1}, (), {}, 1, "causal_detected", 1.0),
            ({-2, -1, 2, 3}, (), {}, 1, "causal_detected", 3.0),
            ({5, 6}, (), {}, 0, "no_candidate_in_window", None),
            ({3, 4}, {0, 1}, {}, 2, "first_candidate_no_target_onset", None),
            ({1, 2}, {0, 1, 2}, {}, 1, "first_candidate_no_target_onset", None),
            ({1, 2}, (), {"mode_entry": True}, 1, "causal_detected", 2.0),
            ({0, 1}, (), {"equal_offset": 1}, 0, "no_candidate_in_window", None)]
        for number, (t, u, options, count, reason, delay) in enumerate(cases, 1):
            with self.subTest(fixture="M" + str(number)):
                ev, scores = matching_case(t, u, **options)
                before = copy.deepcopy(scores)
                sources, groups = a.reconstruct_episodes(scores)
                incidents, matched = a.reconstruct_matching([ev], scores, sources, groups)
                self.assertEqual((incidents[0]["candidate_count"], incidents[0]["reason"], incidents[0]["delay_seconds"]), (count, reason, delay))
                self.assertEqual(sum(g["matched_event_id"] is not None for g in matched), int(delay is not None))
                self.assertEqual(scores, before)

    def test_M9_unavailable_support_is_rejected(self):
        ev, scores = matching_case({0, 1})
        row = next(s for s in scores if s["streak"] == 2)
        row.update(available=False, score=None, exclusion_tags=["current_target_quality"], exclusion_reason="current_target_quality", threshold_exceeded=False)
        with self.assertRaisesRegex(ValueError, "backlink"):
            a.reconstruct_episodes(scores)

    def test_duplicate_score_and_tampered_strict_threshold_are_rejected(self):
        _, scores = matching_case({0, 1})
        with self.assertRaisesRegex(ValueError, "duplicate"):
            a.reconstruct_episodes(scores + [scores[0]])
        row = next(s for s in scores if s["streak"] == 1)
        row["score"] = 6.0
        with self.assertRaisesRegex(ValueError, "strict threshold"):
            a.reconstruct_episodes(scores)

    def test_profile_change_breaks_run_and_cannot_keep_source(self):
        _, scores = matching_case({0, 1, 2})
        row = next(s for s in scores if s["streak"] == 2)
        row["profile_id"] += "-changed"
        with self.assertRaisesRegex(ValueError, "streak/backlink"):
            a.reconstruct_episodes(scores)

    def test_transitive_adjacent_sources_merge_once(self):
        _, scores = matching_case({0, 1, 3, 4}, {1, 2, 3})
        sources, groups = a.reconstruct_episodes(scores)
        self.assertEqual((len(sources), len(groups)), (3, 1))
        self.assertEqual(len(groups[0]["source_episode_ids"]), 3)

    def test_zero_alert_precision_is_null_and_planned_denominators_stay(self):
        result = zero_result()
        report = a.audit_evaluation(result)
        self.assertEqual(report["metrics"], result["metrics"])
        self.assertEqual(report["metrics"]["precision"]["ci_status"], "inconclusive")
        self.assertFalse(report["score_derivation_verified"])
        self.assertFalse(report["independent_s6_complete"])

    def test_missing_score_row_cannot_shrink_availability_denominator(self):
        result = zero_result()
        result["scores"].pop()
        with self.assertRaisesRegex(ValueError, "coverage"):
            a.audit_evaluation(result)

    def test_core_disabled_quality_windows_still_exclude_clean_exposure(self):
        result = zero_result()
        self.assertEqual(sum(not e["enabled"] for e in result["events"]), 10)
        result["metrics"]["scheduled_clean_seconds"] += 5
        with self.assertRaisesRegex(ValueError, "scheduled_clean_seconds"):
            a.audit_evaluation(result)

    def test_forged_incident_or_metric_is_rejected(self):
        for location in ("incident", "metric", "bool"):
            result = zero_result()
            if location == "incident":
                result["incidents"][0].update(causal_detected=True)
            else:
                result["metrics"]["machine_recall"]["numerator"] = True if location == "bool" else 1
            with self.subTest(location=location), self.assertRaises(ValueError):
                a.audit_evaluation(result)

    def test_null_delays_are_not_filled_with_zero(self):
        result = zero_result()
        result["metrics"]["delay_summary"]["median"] = 0.0
        with self.assertRaisesRegex(ValueError, "delay_summary.median"):
            a.audit_evaluation(result)

    def test_context_counts_disabled_quality_and_pre_event_group(self):
        ev, scores = matching_case({-1, 0, 1})
        sources, groups = a.reconstruct_episodes(scores)
        quality = event("data_quality", ev["start_sample"])
        _, annotated = a.reconstruct_matching([ev, quality], scores, sources, groups)
        self.assertEqual(annotated[0]["context_tags"], ["raw-event", "quality"])


if __name__ == "__main__":
    unittest.main()
