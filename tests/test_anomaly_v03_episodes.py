"""M1-M9 and adversarial accounting from explicit scores, never run results."""

from __future__ import annotations

import copy
import unittest
from contextlib import ExitStack
from unittest.mock import patch

from banto_ai import _anomaly_v03_contract as c
from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_episodes as e
from tests.test_anomaly_v03_scoring import identity
from tools.ci_shared_fixtures import record


def profiles_for(ident):
    rows = []
    for equipment in c.EQUIPMENT:
        for target in c.TARGETS:
            for mi, mode in enumerate(c.MODES):
                rows.append({"profile_id": f"p-{equipment}-{target}-{mode}", "identity": dict(ident), "profile_version": "0.3",
                             "equipment": equipment, "full_target": equipment+"."+target, "mode": mode, "recipe": c.RECIPES[mi],
                             "status": "calibrated", "fit_samples": [1800+180*r+30*mi+u for r in range(20) for u in range(30)],
                             "calibration_samples": [5400+180*r+30*mi+u for r in range(10) for u in range(1, 30)],
                             "planned_calibration_points": 290, "minimum_calibration_points": 250, "phase_medians": [0.0]*30,
                             "center": 0.0, "scale": 1.0, "c2_state": None, "reason": None})
    return rows


def score(ident, target, sample, value=0.0):
    equipment, signal = target.split(".")
    mi, phase = (sample % 180)//30, sample % 30
    if phase == 0: value = None
    return {"score_id": f"s-{target}-{sample}", "dataset_id": ident["dataset_id"], "candidate_id": ident["candidate_id"],
            "equipment": equipment, "full_target": target, "sample": sample, "timestamp_ms": c.START_MS+sample*1000,
            "phase": phase, "mode": c.MODES[mi], "recipe": c.RECIPES[mi], "profile_id": f"p-{equipment}-{signal}-{c.MODES[mi]}",
            "dependencies": [{"full_target": target, "sample": k, "timestamp_ms": c.START_MS+k*1000, "quality": "ok", "value": 0.0} for k in (sample-1, sample)],
            "residual": value, "score": value, "available": value is not None, "exclusion_reason": None if value is not None else "mode_recipe_or_phase",
            "exclusion_tags": [] if value is not None else ["mode_recipe_or_phase"], "threshold_exceeded": value is not None and value > 6,
            "streak": int(value is not None and value > 6), "source_episode_id": None}


def fixture(points, *, mode_entry=False, exact=None):
    ident = identity(1, layout=0 if mode_entry else 1)
    events = v.event_inventory(ident)
    event = events[0]
    target, other = event["full_target"], event["equipment"]+".vibration_feature"
    targets = {"T": target, "U": other, "V": event["equipment"]+".conveyor_speed"}
    rows = []
    for name in points:
        for offset in range(-3 if not mode_entry else 0, 10):
            value = (exact or {}).get((name, offset), 7.0 if offset in points[name] else 0.0)
            rows.append(score(ident, targets[name], event["start_sample"]+offset, value))
    scores, sources, equipment = e.build_episodes(rows)
    return ident, event, {"events": events, "profiles": profiles_for(ident), "scores": scores,
                           "source_episodes": sources, "equipment_episodes": equipment}


def selected(ident, event, ledgers):
    incidents, episodes = e.match_incidents(ident, **ledgers)
    return next(i for i in incidents if i["event_id"] == event["event_id"]), episodes


class MatchingGoldenTests(unittest.TestCase):
    def record_matching(self, fixture_id, ident, event, rows, incident, episodes):
        record(fixture_id, self.id(), lambda: {"identity": ident, "event": event,
               "profile_ids": [p["profile_id"] for p in rows["profiles"]], "scores": rows["scores"],
               "sources": rows["source_episodes"], "incident": incident, "episodes": episodes})

    def test_M1_first_pre_event_support_no_retry(self):
        ident, event, rows = fixture({"T": {-1, 0, 3, 4}})
        incident, episodes = selected(ident, event, rows)
        self.assertEqual((incident["candidate_count"], incident["reason"]), (2, "first_candidate_noncausal_support"))
        self.assertEqual(incident["selected_candidate_episode_id"], episodes[0]["episode_id"])
        self.assertFalse(incident["causal_detected"])
        self.assertTrue(all(r["matched_event_id"] is None for r in episodes))
        self.record_matching("M1", ident, event, rows, incident, episodes)

    def test_M2_minimum_causal_delay_one_second(self):
        ident, event, rows = fixture({"T": {0, 1}})
        incident, episodes = selected(ident, event, rows)
        self.assertEqual((incident["causal_detected"], incident["delay_seconds"]), (True, 1.0))
        self.assertEqual(incident["support_score_ids"], rows["source_episodes"][0]["support_score_ids"])
        self.assertEqual(len(episodes), 1)
        self.record_matching("M2", ident, event, rows, incident, episodes)

    def test_M3_ended_pre_event_episode_not_a_candidate(self):
        ident, event, rows = fixture({"T": {-2, -1, 2, 3}})
        incident, episodes = selected(ident, event, rows)
        self.assertEqual((incident["candidate_count"], incident["delay_seconds"]), (1, 3.0))
        self.assertEqual(incident["selected_candidate_episode_id"], episodes[1]["episode_id"])
        self.record_matching("M3", ident, event, rows, incident, episodes)

    def test_M4_right_endpoint_is_outside_half_open_window(self):
        ident, event, rows = fixture({"T": {5, 6}})
        incident, episodes = selected(ident, event, rows)
        self.assertEqual((len(episodes), incident["candidate_count"], incident["reason"]), (1, 0, "no_candidate_in_window"))
        self.record_matching("M4", ident, event, rows, incident, episodes)

    def test_M5_first_other_target_does_not_retry(self):
        ident, event, rows = fixture({"U": {0, 1}, "T": {3, 4}})
        incident, episodes = selected(ident, event, rows)
        self.assertEqual((incident["candidate_count"], incident["reason"]), (2, "first_candidate_no_target_onset"))
        self.assertIsNone(incident["selected_source_episode_id"])
        self.record_matching("M5", ident, event, rows, incident, episodes)

    def test_M6_late_target_in_merge_never_moves_group_onset(self):
        ident, event, rows = fixture({"U": {0, 1, 2}, "T": {1, 2}})
        incident, episodes = selected(ident, event, rows)
        self.assertEqual((len(episodes), incident["reason"]), (1, "first_candidate_no_target_onset"))
        self.assertEqual(episodes[0]["onset_ms"], event["start_ms"]+1000)
        self.assertEqual(len(episodes[0]["source_episode_ids"]), 2)
        self.record_matching("M6", ident, event, rows, incident, episodes)

    def test_M7_mode_entry_minimum_delay_two_seconds(self):
        ident, event, rows = fixture({"T": {1, 2}}, mode_entry=True)
        incident, episodes = selected(ident, event, rows)
        self.assertFalse(rows["scores"][0]["available"])
        self.assertEqual((incident["causal_detected"], incident["delay_seconds"]), (True, 2.0))
        self.record_matching("M7", ident, event, rows, incident, episodes)

    def test_M8_equality_does_not_exceed(self):
        ident, event, rows = fixture({"T": {0, 1}}, exact={("T", 1): 6.0})
        incident, episodes = selected(ident, event, rows)
        self.assertEqual(episodes, [])
        self.assertEqual(incident["reason"], "no_candidate_in_window")
        self.record_matching("M8", ident, event, rows, incident, episodes)

    def test_M9_forged_unavailable_support_stops_before_selection(self):
        ident, _, rows = fixture({"T": {0, 1}})
        bad = next(r for r in rows["scores"] if r["streak"] == 2)
        bad.update(score=None, residual=None, available=False, threshold_exceeded=False, streak=0, source_episode_id=None,
                   exclusion_reason="current_target_quality", exclusion_tags=["current_target_quality"])
        before = copy.deepcopy(rows)
        with self.assertRaises(v.V03ValidationError) as caught, patch.object(e, "_context", side_effect=AssertionError("matching started before structure check")) as context:
            e.match_incidents(ident, **rows)
        self.assertEqual(rows, before)
        context.assert_not_called()
        record("M9", self.id(), lambda: {"rejected": type(caught.exception).__name__, "context_calls": context.call_count,
                                         "scores": rows["scores"], "unchanged": rows == before})


class EpisodeAdversarialTests(unittest.TestCase):
    def test_transitive_adjacency_merge_with_late_bridge_and_fixed_minimum(self):
        ident, event, rows = fixture({"T": {0, 1}, "U": {1, 2, 3}, "V": {3, 4}})
        episode = rows["equipment_episodes"][0]
        self.assertEqual(len(rows["equipment_episodes"]), 1)
        self.assertEqual(len(episode["source_episode_ids"]), 3)
        self.assertEqual((episode["onset_ms"], episode["end_ms"]), (event["start_ms"]+1000, event["start_ms"]+5000))
        self.assertTrue(selected(ident, event, rows)[0]["causal_detected"])

    def test_pre_event_group_late_target_never_reonsets(self):
        ident, event, rows = fixture({"U": {-2, -1, 0, 1, 2}, "T": {0, 1}})
        incident, episodes = selected(ident, event, rows)
        self.assertEqual(incident["reason"], "no_candidate_in_window")
        self.assertEqual(episodes[0]["onset_ms"], event["start_ms"]-1000)
        self.assertIn("pre-event", episodes[0]["context_tags"])

    def test_no_episode_from_singleton_and_long_run_has_unique_onset(self):
        _, event, rows = fixture({"T": {0, 1, 2, 3, 4, 7}})
        source = rows["source_episodes"][0]
        self.assertEqual(len(rows["source_episodes"]), 1)
        self.assertEqual((source["onset_ms"], source["end_ms"]), (event["start_ms"]+1000, event["start_ms"]+5000))
        first = next(r for r in rows["scores"] if r["timestamp_ms"] == event["start_ms"])
        self.assertIsNone(first["source_episode_id"])
        self.assertEqual([r["streak"] for r in rows["scores"] if r["source_episode_id"]], [2, 3, 4, 5])

    def test_profile_change_gap_unavailable_and_low_score_reset_runs(self):
        for kind in ("profile", "gap", "unavailable", "low"):
            ident = identity(1)
            scores = [score(ident, c.FULL_TARGETS[0], sample, 7.0) for sample in range(7201, 7206)]
            if kind == "profile":
                for row in scores[2:]: row["profile_id"] = "changed-profile"
            elif kind == "gap": scores.pop(2)
            elif kind == "unavailable":
                scores[2].update(score=None, residual=None, available=False, threshold_exceeded=False, streak=0,
                                 exclusion_reason="current_target_quality", exclusion_tags=["current_target_quality"])
            else: scores[2].update(score=0.0, residual=0.0, threshold_exceeded=False, streak=0)
            updated, sources, _ = e.build_episodes(scores)
            self.assertEqual(len(sources), 2, kind)
            self.assertEqual([r["streak"] for r in updated if r["timestamp_ms"] == sources[-1]["onset_ms"]], [2])

    def test_other_mode_visit_equipment_dataset_and_candidate_do_not_merge(self):
        ident = identity(1)
        scores = [score(ident, c.FULL_TARGETS[0], sample, 7.0) for sample in (7228, 7229, 7230, 7231, 7232, 7381, 7382)]
        scores.extend(score(ident, c.FULL_TARGETS[4], sample, 7.0) for sample in (7231, 7232))
        for field, val in (("dataset_id", "other-dataset"), ("candidate_id", c.CANDIDATES[2])):
            other = [score(ident, c.FULL_TARGETS[0], k, 7.0) for k in (7231, 7232)]
            for row in other: row[field] = val; row["score_id"] += "-"+val
            scores.extend(other)
        _, sources, equipment = e.build_episodes(scores)
        self.assertEqual((len(sources), len(equipment)), (6, 6))

    def test_duplicate_reversed_threshold_bool_and_nonfinite_scores_rejected(self):
        ident = identity(1)
        for kind in ("duplicate", "reverse", "flag", "bool", "nan"):
            rows = [score(ident, c.FULL_TARGETS[0], sample, 7.0) for sample in (7201, 7202)]
            if kind == "duplicate": rows.append(copy.deepcopy(rows[0]))
            elif kind == "reverse": rows.reverse()
            elif kind == "flag": rows[0]["score"] = 6.0
            elif kind == "bool": rows[0]["score"] = True
            else: rows[0]["score"] = float("nan")
            with self.subTest(kind=kind), self.assertRaises(v.V03ValidationError): e.build_episodes(rows)

    def test_C0_strict_four_and_C1_strict_six_no_threshold_tolerance(self):
        for candidate, threshold in ((0, 4.0), (1, 6.0)):
            ident = identity(candidate)
            scores = [score(ident, c.FULL_TARGETS[0], sample, threshold) for sample in (7201, 7202)]
            self.assertFalse(e.build_episodes(scores)[1])
            for row in scores: row.update(score=threshold+1e-10, threshold_exceeded=True)
            self.assertEqual(len(e.build_episodes(scores)[1]), 1)

    def test_reconstruction_catches_missing_truncated_extended_and_split_merge(self):
        for kind in ("missing-source", "truncated", "extended", "missing-interior", "streak", "missing-equipment", "unmerged"):
            ident, _, rows = fixture({"U": {0, 1, 2, 3}, "T": {1, 2, 3}})
            if kind == "missing-source": rows["source_episodes"].pop()
            elif kind == "truncated": rows["source_episodes"][0]["end_ms"] -= 1000
            elif kind == "extended": rows["source_episodes"][0]["end_ms"] += 1000
            elif kind == "missing-interior":
                del rows["scores"][next(i for i, r in enumerate(rows["scores"]) if r["streak"] == 3)]
            elif kind == "streak": next(r for r in rows["scores"] if r["streak"] == 3)["streak"] = 10
            elif kind == "missing-equipment": rows["equipment_episodes"] = []
            else:
                group = rows["equipment_episodes"].pop()
                for source in rows["source_episodes"]:
                    ep = copy.deepcopy(group)
                    ep.update(episode_id=source["episode_id"]+"-equipment", onset_ms=source["onset_ms"], end_ms=source["end_ms"], source_episode_ids=[source["episode_id"]])
                    rows["equipment_episodes"].append(ep)
            with self.subTest(kind=kind), self.assertRaises(v.V03ValidationError): e.match_incidents(ident, **rows)

    def test_GT_changes_cannot_change_label_free_episode_outputs(self):
        ident, _, rows = fixture({"T": {0, 1}, "U": {3, 4}})
        before = e.build_episodes(rows["scores"])
        rows["events"][0]["magnitude"] = 999.0
        rows["events"][0]["start_ms"] -= 999000
        self.assertEqual(before, e.build_episodes(rows["scores"]))
        with self.assertRaises(v.V03ValidationError): e.match_incidents(ident, **rows)

    def test_episode_prefix_future_invariance_onset_support_and_score_links(self):
        ident, _, rows = fixture({"T": {0, 1, 2, 3, 4}})
        onset = rows["source_episodes"][0]["onset_ms"]
        prefix = [r for r in rows["scores"] if r["timestamp_ms"] <= onset]
        small = e.build_episodes(prefix)
        self.assertEqual(small[0], [r for r in rows["scores"] if r["timestamp_ms"] <= onset])
        self.assertEqual(small[1][0]["support_score_ids"], rows["source_episodes"][0]["support_score_ids"])
        self.assertEqual(small[1][0]["onset_ms"], onset)
        self.assertLess(small[1][0]["end_ms"], rows["source_episodes"][0]["end_ms"])


class AccountingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ident = identity(1, stratum="quality-stress")
        cls.events = v.event_inventory(cls.ident)
        cls.profiles = profiles_for(cls.ident)
        scores = [score(cls.ident, target, sample) for target in c.FULL_TARGETS for sample in range(7200, 9000)]
        cls.scores, cls.sources, cls.episodes = e.build_episodes(scores)
        cls.incidents, cls.episodes = e.match_incidents(cls.ident, events=cls.events, profiles=cls.profiles, scores=cls.scores, source_episodes=cls.sources, equipment_episodes=cls.episodes)

    def rows(self):
        return dict(events=self.events, profiles=self.profiles, scores=self.scores, source_episodes=self.sources, equipment_episodes=self.episodes, incidents=self.incidents)

    def test_zero_alert_precision_null_all_planned_incidents_and_origins(self):
        metrics = e.account_metrics(self.ident, **self.rows())
        self.assertEqual((metrics["precision"]["value"], metrics["precision"]["ci_status"]), (None, "inconclusive"))
        self.assertEqual(metrics["sensor_recall"]["denominator"], 10)
        self.assertEqual(metrics["machine_recall"]["denominator"], 10)
        self.assertEqual(metrics["false_alert_burden"]["denominator"], 20)
        self.assertEqual(metrics["scheduled_clean_seconds"], 3365)
        self.assertLessEqual(metrics["effective_clean_seconds"], 3365)
        self.assertTrue(all(a["metric"]["denominator"] == 1800 and a["metric"]["numerator"] == 1740 for a in metrics["availability"]))
        self.assertEqual(metrics["delay_summary"]["count"], 0)
        self.assertIsNone(metrics["delay_summary"]["mean"])
        record("accounting", self.id(), lambda: {"identity": self.ident, "score_count": len(self.scores),
                                                 "incidents": self.incidents, "metrics": metrics})

    def test_clean_time_not_multiplied_by_signals_and_core_mask_matches_stress(self):
        core = identity(1)
        stress_mask = e.scheduled_clean_mask(self.ident, self.events)
        core_mask = e.scheduled_clean_mask(core, v.event_inventory(core))
        self.assertEqual(core_mask, stress_mask)
        self.assertEqual(len(core_mask), 3365)
        self.assertEqual(sum(equipment == "conveyor-01" for equipment, _ in core_mask), 1800)

    def test_drop_overlap_miss_cannot_be_deleted_from_incident_denominator(self):
        rows = copy.deepcopy(self.rows())
        event = next(e for e in rows["events"] if e["cycle"] == 9 and e["event_class"] == "sensor")
        rows["incidents"] = [i for i in rows["incidents"] if i["event_id"] != event["event_id"]]
        with self.assertRaisesRegex(v.V03ValidationError, "incident recomputation"):
            e.account_metrics(self.ident, **rows)

    def test_missing_origin_is_engineering_failure_not_smaller_denominator(self):
        rows = copy.deepcopy(self.rows()); rows["scores"].pop()
        with self.assertRaisesRegex(v.V03ValidationError, "incomplete planned score"):
            e.account_metrics(self.ident, **rows)

    def test_unprocessed_and_forged_miss_never_becomes_formal_recall(self):
        for change in ("unprocessed", "reason", "candidate-count"):
            rows = copy.deepcopy(self.rows())
            if change == "unprocessed": rows["incidents"][0].update(status="not_processed", causal_detected=None, reason="not_processed")
            elif change == "reason": rows["incidents"][0]["reason"] = "first_candidate_no_target_onset"
            else: rows["incidents"][0]["candidate_count"] = 10
            with self.subTest(change=change), self.assertRaises(v.V03ValidationError):
                e.account_metrics(self.ident, **rows)

    def test_all_episode_precision_raw_grace_ignored_quality_and_clean_burden(self):
        ident = identity(1, layout=1)
        events = v.event_inventory(ident)
        profiles = profiles_for(ident)
        points = {(c.FULL_TARGETS[4], k) for k in (7201, 7202)}
        machine, sensor, quality, ignored = events[:4]
        for offset in (-1, 0, 3, 4): points.add((machine["full_target"], machine["start_sample"]+offset))
        for offset in (0, 1): points.add((sensor["full_target"], sensor["start_sample"]+offset))
        for offset in (0, 1): points.add((c.FULL_TARGETS[3], quality["start_sample"]+offset))
        for offset in (1, 2): points.add((c.FULL_TARGETS[0], ignored["start_sample"]+offset))
        scores = [score(ident, t, k, 7.0 if (t, k) in points else 0.0) for t in c.FULL_TARGETS for k in range(7200, 9000)]
        scores, sources, episodes = e.build_episodes(scores)
        rows = dict(events=events, profiles=profiles, scores=scores, source_episodes=sources, equipment_episodes=episodes)
        incidents, rows["equipment_episodes"] = e.match_incidents(ident, **rows)
        metrics = e.account_metrics(ident, **rows, incidents=incidents)
        self.assertEqual((metrics["precision"]["numerator"], metrics["precision"]["denominator"]), (1, 6))
        self.assertEqual((metrics["false_alert_burden"]["numerator"], metrics["false_alert_burden"]["value"]), (5, 25.0))
        self.assertEqual(metrics["clean_rate"]["numerator"], 1)
        self.assertEqual(metrics["clean_rate"]["value"], 8/(3365/3600))
        self.assertEqual(metrics["delay_summary"]["mean"], 1.0)
        tags = {t for episode in rows["equipment_episodes"] for t in episode["context_tags"]}
        self.assertTrue({"raw-event", "grace", "ignored", "quality", "clean"}.issubset(tags))

    def test_dropout_overlap_records_every_lost_origin_and_incident(self):
        rows = copy.deepcopy(self.rows())
        quality_windows = [(x["equipment"], x["start_sample"], x["end_sample"]) for x in self.events if x["event_class"] == "data_quality"]
        lost = set()
        for row in rows["scores"]:
            if row["full_target"] != c.FULL_TARGETS[1]: continue
            sample = row["sample"]
            if any(eq == row["equipment"] and start <= sample <= end for eq, start, end in quality_windows):
                if row["available"]: lost.add(sample)
                row.update(score=None, residual=None, available=False, threshold_exceeded=False, streak=0,
                           exclusion_reason="current_target_quality", exclusion_tags=["current_target_quality"])
        rows["scores"], rows["source_episodes"], rows["equipment_episodes"] = e.build_episodes(rows["scores"])
        rows["incidents"], rows["equipment_episodes"] = e.match_incidents(self.ident, **{k: val for k, val in rows.items() if k != "incidents"})
        metrics = e.account_metrics(self.ident, **rows)
        self.assertEqual(metrics["sensor_recall"]["denominator"], 10)
        self.assertEqual(metrics["availability"][1]["metric"]["numerator"], 1740-len(lost))
        self.assertEqual(metrics["availability"][1]["metric"]["denominator"], 1800)
        self.assertEqual(metrics["scheduled_clean_seconds"], 3365)

    def test_pure_matching_and_mask_no_IO_or_external_writes(self):
        ident, _, rows = fixture({"T": {0, 1}})
        before = copy.deepcopy(rows)
        with ExitStack() as traps:
            for name in ("builtins.open", "pathlib.Path.open", "os.stat", "os.getenv", "socket.socket", "subprocess.run"):
                traps.enter_context(patch(name, side_effect=AssertionError("unexpected I/O")))
            e.match_incidents(ident, **rows)
            self.assertEqual(len(e.scheduled_clean_mask(ident, rows["events"])), 3365)
        self.assertEqual(rows, before)


if __name__ == "__main__":
    unittest.main()
