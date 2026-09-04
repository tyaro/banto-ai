from __future__ import annotations

import copy
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import banto_ai.anomaly_evaluation as anomaly_module
from banto_ai.anomaly_evaluation import (
    AnomalyEvaluationError,
    _canonical_json,
    _canonical_time,
    _calibrate_profiles,
    _event_records_and_metrics,
    _evaluate_core,
    _score_and_alert,
    _strict_json,
    _validate_config,
    _validate_result,
    evaluate_anomalies,
)
from banto_ai.event_slices import _verify_dataset
from banto_ai.generator import generate_synthetic
from banto_ai.manifest import load_json, validate
from banto_ai.quality import check_dataset


ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc


def _row(stamp: datetime, value: float | None, *, mode: str = "nominal", quality: str = "ok") -> dict:
    return {
        "timestamp": _canonical_time(stamp),
        "operating_mode": mode,
        "quality": {"motor_current": quality},
        "signals": {"motor_current": {"value": value}},
    }


def _tiny_dataset(rows: list[dict], *, test_start: datetime, test_end: datetime, events: list[dict] | None = None) -> dict:
    start = datetime.fromisoformat(rows[0]["timestamp"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(rows[-1]["timestamp"].replace("Z", "+00:00")) + timedelta(seconds=1)
    return {
        "manifest": {"sampling_interval_ms": 1000},
        "observations": {"motor-01": rows},
        "events": events or [],
        "signals": {"motor-01.motor_current": {"role": "target"}},
        "split_times": {
            "train": (start, start + timedelta(seconds=1)),
            "validation": (start, test_start),
            "test": (test_start, test_end),
        },
    }


def _event(event_id: str, signal_id: str, start: datetime, end: datetime, event_type: str = "spike") -> dict:
    return {
        "event_id": event_id,
        "event_type": event_type,
        "equipment_id": "motor-01",
        "signal_id": signal_id,
        "start": start,
        "end": end,
    }


def _episode(episode_id: str, signal_id: str, start: datetime, onset: datetime, end: datetime) -> dict:
    return {
        "episode_id": episode_id,
        "equipment_id": "motor-01",
        "signal_id": signal_id,
        "start_timestamp": _canonical_time(start),
        "onset_timestamp": _canonical_time(onset),
        "end_timestamp": _canonical_time(end),
        "point_count": 1,
        "max_score": 8.0,
        "profile_key": {"equipment_id": "motor-01", "signal_id": signal_id, "operating_mode": "nominal"},
    }


class AnomalyEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        artifact_parent = ROOT / "artifacts"
        artifact_parent.mkdir(parents=True, exist_ok=True)
        cls.token = uuid4().hex[:10]
        cls.temp_root = Path(tempfile.mkdtemp(prefix="anomaly-test-", dir=artifact_parent))
        generator = load_json(ROOT / "examples/configs/synthetic-anomaly-evaluation-v0.1.json")
        generator["dataset_id"] = f"anomaly-test-{cls.token}"
        cls.generator_path = cls.temp_root / "generator.json"
        cls.generator_path.write_text(json.dumps(generator, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        cls.dataset_path = cls.temp_root / "dataset"
        generate_synthetic(cls.generator_path, cls.dataset_path.relative_to(ROOT).as_posix(), ROOT)
        cls.dataset = _verify_dataset(cls.dataset_path, ROOT)
        cls.template = load_json(ROOT / "examples/configs/anomaly-evaluation-v0.1.json")
        cls.outputs: list[Path] = []

    @classmethod
    def tearDownClass(cls) -> None:
        for output in cls.outputs:
            if output.is_dir() and not output.is_symlink():
                for child in output.iterdir():
                    if child.is_file() or child.is_symlink():
                        child.unlink(missing_ok=True)
                output.rmdir()
        import shutil

        shutil.rmtree(cls.temp_root, ignore_errors=True)

    def _relative(self, path: Path) -> str:
        return path.absolute().relative_to(ROOT.absolute()).as_posix()

    def _config(self, label: str) -> tuple[Path, Path, dict]:
        config = copy.deepcopy(self.template)
        output = ROOT / "artifacts" / f"anomaly-test-output-{self.token}-{label}-{uuid4().hex[:6]}"
        config["dataset_path"] = self._relative(self.dataset_path)
        config["output_dir"] = self._relative(output)
        path = self.temp_root / f"evaluation-{label}-{uuid4().hex[:6]}.json"
        path.write_text(json.dumps(config, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
        self.outputs.append(output)
        return path, output, config

    def test_scenario_schema_quality_gate_and_cli_help(self) -> None:
        generator = load_json(self.generator_path)
        validate(generator, load_json(ROOT / "schemas/synthetic-generator-config.schema.json"))
        evaluate_schema = load_json(ROOT / "schemas/anomaly-evaluation-config.schema.json")
        _path, _output, config = self._config("schema")
        validate(config, evaluate_schema)
        quality = check_dataset(self.dataset_path, ROOT)
        self.assertEqual(quality["status"], "pass")
        self.assertEqual(quality["observation_record_count"], 1800)
        self.assertEqual(len(self.dataset["events"]), 4)
        completed = subprocess.run(
            [sys.executable, str(ROOT / "tools/evaluator/evaluate_anomalies.py"), "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0)
        self.assertIn("Event-aware anomaly evaluation v0.1", completed.stdout)
        self.assertIn("--recover-incomplete", completed.stdout)

    def test_publish_result_has_complete_provenance_and_all_test_modes_profiled(self) -> None:
        config_path, output, _config = self._config("publish")
        published = evaluate_anomalies(config_path, ROOT)
        self.assertEqual(published, output)
        result, result_raw = _strict_json(output / "result.json", "published result")
        self.assertIsInstance(result, dict)
        _validate_result(result, ROOT)
        self.assertTrue((output / ".complete").is_file())
        marker = json.loads((output / ".complete").read_text(encoding="utf-8"))
        self.assertEqual(marker["result_sha256"], anomaly_module._sha256_bytes(result_raw))
        self.assertEqual(result["provenance"]["quality_gate"]["status"], "pass")
        self.assertEqual(result["parameters"]["calibration_split"], "validation")
        self.assertEqual(result["parameters"]["scoring_split"], "test")
        self.assertEqual(len(result["profiles"]), 2 * 4 * 6)
        self.assertTrue(all(profile["status"] == "calibrated" for profile in result["profiles"]))
        self.assertEqual(result["row_counts"]["score_rows"], 2 * 4 * 180)
        self.assertEqual(result["metrics"]["overall"]["evaluated_alert_episode_count"], result["metrics"]["overall"]["matched_eligible_alert_episodes"] + result["metrics"]["overall"]["unmatched_eligible_alert_episodes"] + result["metrics"]["positive_nonmatching_signal_false_alert_episode_count"] + result["metrics"]["clean_false_alert_signal_episode_count"])
        partition = result["metrics"]["alert_episode_partition"]
        self.assertEqual(partition["total_alert_episodes"], len(result["alert_episodes"]))
        self.assertEqual(partition["total_alert_episodes"], len(result["alert_episode_accounting"]))
        self.assertEqual(
            partition["total_alert_episodes"],
            partition["matched_eligible_alert_episodes"]
            + partition["unmatched_eligible_same_signal_alert_episodes"]
            + partition["positive_nonmatching_signal_false_alert_episodes"]
            + partition["clean_false_alert_signal_episodes"]
            + partition["suppressed_event_window_alert_episodes"],
        )
        self.assertGreaterEqual(partition["positive_nonmatching_signal_false_alert_episodes"], 0)
        self.assertEqual(partition["suppressed_event_window_by_reason"], {"data_quality": 0, "ignored": 0})
        self.assertEqual(partition["suppressed_event_window_alert_episodes"], 0)
        self.assertTrue(partition["precision_denominator_excludes_suppressed"])
        for summary in result["metrics"]["score_availability_by_signal"].values():
            self.assertGreater(summary["total_points"], 0)
            self.assertGreater(summary["available_points"], 0)
            self.assertGreaterEqual(summary["availability_ratio"], 0.0)

    def test_calibration_is_invariant_to_test_observations_and_event_labels(self) -> None:
        config_path, _output, config = self._config("invariance")
        equipment_ids, target_ids, labels = _validate_config(config, ROOT, self.dataset)
        profiles_a, _ = _calibrate_profiles(self.dataset, equipment_ids, target_ids, config)
        changed_dataset = copy.deepcopy(self.dataset)
        for row in changed_dataset["observations"]["motor-01"]:
            stamp = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
            if stamp >= changed_dataset["split_times"]["test"][0]:
                row["signals"]["motor_current"]["value"] = 9999.0
        profiles_b, _ = _calibrate_profiles(changed_dataset, equipment_ids, target_ids, config)
        profile_rows = lambda profiles: [profiles[key] for key in sorted(profiles)]
        self.assertEqual(_canonical_json(profile_rows(profiles_a)), _canonical_json(profile_rows(profiles_b)))

        relabeled = copy.deepcopy(config)
        relabeled["event_classifications"][0]["event_class"] = "ignored"
        equipment_b, target_b, labels_b = _validate_config(relabeled, ROOT, changed_dataset)
        profiles_c, _ = _calibrate_profiles(changed_dataset, equipment_b, target_b, relabeled)
        self.assertEqual(_canonical_json(profile_rows(profiles_b)), _canonical_json(profile_rows(profiles_c)))
        scores_a, _episodes_a, _ = _score_and_alert(self.dataset, equipment_ids, target_ids, profiles_a, config)
        scores_b, _episodes_b, _ = _score_and_alert(changed_dataset, equipment_b, target_b, profiles_c, relabeled)
        self.assertNotEqual(_canonical_json(scores_a), _canonical_json(scores_b), "test observation changes should affect scores, not calibration")
        _incidents_a, _clean_a, metrics_a, _ = _event_records_and_metrics(self.dataset, equipment_ids, target_ids, labels, _episodes_a, config)
        _incidents_b, _clean_b, metrics_b, _ = _event_records_and_metrics(self.dataset, equipment_ids, target_ids, labels_b, _episodes_a, relabeled)
        self.assertNotEqual(metrics_a["overall"]["eligible_incidents"], metrics_b["overall"]["eligible_incidents"])
        self.assertEqual(metrics_a["overall"]["eligible_incidents"], 2)
        self.assertEqual(metrics_b["overall"]["eligible_incidents"], 1)
        self.assertEqual(_canonical_json(scores_a), _canonical_json(_score_and_alert(self.dataset, equipment_ids, target_ids, profiles_a, relabeled)[0]))

    def test_zero_mad_and_test_only_mode_are_inconclusive(self) -> None:
        start = datetime(2026, 1, 1, tzinfo=UTC)
        rows = [_row(start + timedelta(seconds=index), 1.0, mode="nominal" if index < 6 else "high_load") for index in range(9)]
        dataset = _tiny_dataset(rows, test_start=start + timedelta(seconds=6), test_end=start + timedelta(seconds=9))
        config = {"min_calibration_points": 2}
        profiles, summary = _calibrate_profiles(dataset, ["motor-01"], ["motor-01.motor_current"], config)
        self.assertEqual(summary["profiles_inconclusive"], 2)
        self.assertEqual(profiles[("motor-01", "motor-01.motor_current", "nominal")]["reason"], "mad_zero")
        self.assertEqual(profiles[("motor-01", "motor-01.motor_current", "high_load")]["reason"], "min_calibration_points_not_met")
        self.assertIsNone(profiles[("motor-01", "motor-01.motor_current", "nominal")]["scale"])

    def test_calibration_excludes_residual_immediately_after_event_end(self) -> None:
        start = datetime(2026, 1, 1, tzinfo=UTC)
        rows = [_row(start + timedelta(seconds=index), 0.0) for index in range(9)]
        event = _event("validation-event", "motor-01.motor_current", start + timedelta(seconds=3), start + timedelta(seconds=4))
        dataset = _tiny_dataset(rows, test_start=start + timedelta(seconds=6), test_end=start + timedelta(seconds=9), events=[event])
        profiles, summary = _calibrate_profiles(dataset, ["motor-01"], ["motor-01.motor_current"], {"min_calibration_points": 2})
        profile = profiles[("motor-01", "motor-01.motor_current", "nominal")]
        self.assertEqual(summary["event_overlap"], 2)
        self.assertEqual(profile["excluded_counts"]["event_overlap"], 2)
        self.assertEqual(profile["calibration_point_count"], 3)

    def test_event_eligibility_excludes_left_and_right_censored_incidents(self) -> None:
        start = datetime(2026, 1, 1, tzinfo=UTC)
        test_start = start + timedelta(seconds=3)
        test_end = start + timedelta(seconds=10)
        events = [
            _event("left", "motor-01.motor_current", start + timedelta(seconds=2), start + timedelta(seconds=3, milliseconds=500)),
            _event("right", "motor-01.motor_current", start + timedelta(seconds=8), start + timedelta(seconds=9, milliseconds=500)),
            _event("boundary", "motor-01.motor_current", test_start, start + timedelta(seconds=8)),
        ]
        dataset = {"manifest": {"sampling_interval_ms": 1000}, "observations": {}, "events": events, "split_times": {"validation": (start, test_start), "test": (test_start, test_end)}}
        episodes = [_episode("boundary-alert", "motor-01.motor_current", start + timedelta(seconds=3), start + timedelta(seconds=3), start + timedelta(seconds=4))]
        incidents, _clean, metrics, exclusions = _event_records_and_metrics(
            dataset,
            ["motor-01"],
            ["motor-01.motor_current"],
            {"left": "machine_fault", "right": "machine_fault", "boundary": "machine_fault"},
            episodes,
            {"detection_grace_points": 1},
        )
        by_id = {row["event_id"]: row for row in incidents}
        self.assertEqual(by_id["left"]["eligibility_reason"], "left_censored")
        self.assertEqual(by_id["right"]["eligibility_reason"], "right_censored_detection_window")
        self.assertTrue(by_id["boundary"]["eligible"])
        self.assertEqual(metrics["overall"]["eligible_incidents"], 1)
        self.assertEqual(exclusions["ineligible_by_reason"], {"left_censored": 1, "right_censored_detection_window": 1})

    def test_current_event_is_visible_but_previous_event_resets_residual(self) -> None:
        start = datetime(2026, 1, 1, tzinfo=UTC)
        rows = [_row(start + timedelta(seconds=index), float(index)) for index in range(6)]
        events = [
            _event("previous-event", "motor-01.motor_current", start + timedelta(seconds=2), start + timedelta(seconds=3)),
            _event("current-event", "motor-01.motor_current", start + timedelta(seconds=4), start + timedelta(seconds=5)),
        ]
        dataset = _tiny_dataset(rows, test_start=start + timedelta(seconds=3), test_end=start + timedelta(seconds=6), events=events)
        profiles = {("motor-01", "motor-01.motor_current", "nominal"): {"status": "calibrated", "center": 0.0, "scale": 1.0}}
        scores, episodes, _ = _score_and_alert(dataset, ["motor-01"], ["motor-01.motor_current"], profiles, {"robust_z_threshold": 0.5, "persistence_points": 1})
        by_time = {row["timestamp"]: row for row in scores}
        self.assertTrue(by_time[_canonical_time(start + timedelta(seconds=4))]["available"])
        self.assertEqual(by_time[_canonical_time(start + timedelta(seconds=4))]["persistence_streak"], 1)
        self.assertFalse(by_time[_canonical_time(start + timedelta(seconds=5))]["available"])
        self.assertEqual(by_time[_canonical_time(start + timedelta(seconds=5))]["exclusion_reason"], "previous_event_overlap")
        self.assertEqual(len(episodes), 1)

    def test_incomplete_output_recovery_quarantines_evidence_and_preserves_complete_outputs(self) -> None:
        config_path, output, _config = self._config("recovery")
        output.mkdir()
        evidence = output / "partial.txt"
        evidence.write_text("preserve me", encoding="utf-8")
        with self.assertRaises(AnomalyEvaluationError):
            evaluate_anomalies(config_path, ROOT)
        published = evaluate_anomalies(config_path, ROOT, recover_incomplete=True)
        self.assertEqual(published, output)
        self.assertTrue((output / ".complete").is_file())
        quarantined = [path for path in output.parent.iterdir() if path.name.startswith(f".{output.name}.incomplete-")]
        self.assertEqual(len(quarantined), 1)
        self.assertEqual((quarantined[0] / "partial.txt").read_text(encoding="utf-8"), "preserve me")
        with self.assertRaises(AnomalyEvaluationError):
            evaluate_anomalies(config_path, ROOT, recover_incomplete=True)
        for path in quarantined:
            if path.is_dir():
                self.outputs.append(path)

    def test_quality_gap_mode_and_persistence_reset(self) -> None:
        start = datetime(2026, 1, 1, tzinfo=UTC)
        values = [0.0, 0.0, 0.0, 5.0, 10.0, None, 10.0, 15.0, 20.0, 25.0]
        rows = [
            _row(start + timedelta(seconds=index), value, mode="nominal" if index < 8 else "high_load", quality="missing" if value is None else "ok")
            for index, value in enumerate(values)
        ]
        dataset = _tiny_dataset(rows, test_start=start + timedelta(seconds=3), test_end=start + timedelta(seconds=10))
        profile = lambda mode: {"status": "calibrated", "center": 0.0, "scale": 1.0}
        profiles = {
            ("motor-01", "motor-01.motor_current", "nominal"): profile("nominal"),
            ("motor-01", "motor-01.motor_current", "high_load"): profile("high_load"),
        }
        config = {"robust_z_threshold": 4.0, "persistence_points": 2}
        scores, episodes, _ = _score_and_alert(dataset, ["motor-01"], ["motor-01.motor_current"], profiles, config)
        self.assertEqual([episode["onset_timestamp"] for episode in episodes], [_canonical_time(start + timedelta(seconds=4))])
        by_time = {score["timestamp"]: score for score in scores}
        self.assertFalse(by_time[_canonical_time(start + timedelta(seconds=5))]["available"])
        self.assertEqual(by_time[_canonical_time(start + timedelta(seconds=5))]["exclusion_reason"], "quality_non_ok")
        self.assertFalse(by_time[_canonical_time(start + timedelta(seconds=6))]["available"])
        self.assertEqual(by_time[_canonical_time(start + timedelta(seconds=6))]["exclusion_reason"], "previous_quality_non_ok")
        self.assertFalse(by_time[_canonical_time(start + timedelta(seconds=8))]["available"])
        self.assertEqual(by_time[_canonical_time(start + timedelta(seconds=8))]["exclusion_reason"], "mode_boundary")
        self.assertEqual(by_time[_canonical_time(start + timedelta(seconds=7))]["persistence_streak"], 1)
        self.assertEqual(by_time[_canonical_time(start + timedelta(seconds=9))]["persistence_streak"], 1)

        gap_rows = rows[:4] + [_row(start + timedelta(seconds=5), 20.0), rows[6]]
        gap_dataset = _tiny_dataset(gap_rows, test_start=start + timedelta(seconds=3), test_end=start + timedelta(seconds=7))
        gap_scores, _gap_episodes, _ = _score_and_alert(gap_dataset, ["motor-01"], ["motor-01.motor_current"], {("motor-01", "motor-01.motor_current", "nominal"): profile("nominal")}, config)
        self.assertEqual(gap_scores[1]["exclusion_reason"], "gap")

    def test_event_partition_and_matching_boundaries(self) -> None:
        config_path, _output, config = self._config("partition")
        dataset = copy.deepcopy(self.dataset)
        equipment_ids, target_ids, labels = _validate_config(config, ROOT, dataset)
        duplicate = copy.deepcopy(config)
        duplicate["event_classifications"].append(copy.deepcopy(duplicate["event_classifications"][0]))
        with self.assertRaises(AnomalyEvaluationError):
            _validate_config(duplicate, ROOT, dataset)
        unknown = copy.deepcopy(config)
        unknown["event_classifications"][0]["event_id"] = "unknown-event"
        with self.assertRaises(AnomalyEvaluationError):
            _validate_config(unknown, ROOT, dataset)
        missing = copy.deepcopy(config)
        missing["event_classifications"] = missing["event_classifications"][:-1]
        with self.assertRaises(AnomalyEvaluationError):
            _validate_config(missing, ROOT, dataset)

        start = datetime(2026, 1, 1, tzinfo=UTC)
        events = [
            _event("fault", "motor-01.motor_current", start + timedelta(seconds=4), start + timedelta(seconds=5)),
            _event("sensor", "motor-01.motor_temperature", start + timedelta(seconds=7), start + timedelta(seconds=8)),
            _event("outside", "motor-01.motor_current", start + timedelta(seconds=1), start + timedelta(seconds=2)),
            _event("unconfigured", "motor-01.load_proxy", start + timedelta(seconds=9), start + timedelta(seconds=10)),
            _event("quality", "motor-01.motor_current", start + timedelta(seconds=10), start + timedelta(seconds=11), event_type="dropout"),
        ]
        metric_dataset = {"manifest": {"sampling_interval_ms": 1000}, "observations": {}, "events": events, "split_times": {"validation": (start, start + timedelta(seconds=3)), "test": (start + timedelta(seconds=3), start + timedelta(seconds=12))}}
        classifications = {"fault": "machine_fault", "sensor": "sensor_fault", "outside": "machine_fault", "unconfigured": "machine_fault", "quality": "data_quality"}
        episodes = [
            _episode("pre-event", "motor-01.motor_current", start + timedelta(seconds=3), start + timedelta(seconds=3), start + timedelta(seconds=4, milliseconds=500)),
            _episode("fault-alert", "motor-01.motor_current", start + timedelta(seconds=4), start + timedelta(seconds=4), start + timedelta(seconds=5, milliseconds=500)),
            _episode("sensor-alert", "motor-01.motor_temperature", start + timedelta(seconds=7), start + timedelta(seconds=7, milliseconds=500), start + timedelta(seconds=8, milliseconds=500)),
            _episode("quality-window-alert", "motor-01.motor_current", start + timedelta(seconds=10), start + timedelta(seconds=10), start + timedelta(seconds=11)),
        ]
        event_config = {"detection_grace_points": 2}
        incidents, _clean, metrics, exclusions = _event_records_and_metrics(metric_dataset, ["motor-01"], ["motor-01.motor_current", "motor-01.motor_temperature"], classifications, episodes, event_config)
        rows = {row["event_id"]: row for row in incidents}
        self.assertEqual(rows["fault"]["matched_alert_episode_id"], "fault-alert")
        self.assertTrue(rows["fault"]["detected"])
        self.assertTrue(rows["sensor"]["detected"])
        self.assertEqual(rows["fault"]["detection_delay_seconds"], 0.0)
        self.assertEqual(rows["sensor"]["detection_delay_seconds"], 0.5)
        self.assertFalse(rows["outside"]["eligible"])
        self.assertEqual(rows["outside"]["eligibility_reason"], "outside_test_split")
        self.assertFalse(rows["unconfigured"]["eligible"])
        self.assertEqual(rows["unconfigured"]["eligibility_reason"], "unconfigured_equipment_or_signal")
        self.assertFalse(rows["quality"]["eligible"])
        self.assertEqual(rows["quality"]["eligibility_reason"], "event_class_data_quality")
        self.assertEqual(metrics["overall"]["detected_incidents"], 2)
        self.assertEqual(metrics["overall"]["matched_eligible_alert_episodes"], 2)
        self.assertEqual(metrics["overall"]["unmatched_eligible_alert_episodes"], 1)
        self.assertEqual(metrics["suppressed_event_window_alert_episode_count"], 1)
        partition = metrics["alert_episode_partition"]
        self.assertEqual(partition["total_alert_episodes"], 4)
        self.assertEqual(partition["matched_eligible_alert_episodes"], 2)
        self.assertEqual(partition["unmatched_eligible_same_signal_alert_episodes"], 1)
        self.assertEqual(partition["positive_nonmatching_signal_false_alert_episodes"], 0)
        self.assertEqual(partition["clean_false_alert_signal_episodes"], 0)
        self.assertEqual(partition["suppressed_event_window_alert_episodes"], 1)
        self.assertEqual(partition["suppressed_event_window_by_reason"], {"data_quality": 1, "ignored": 0})
        accounting = {row["episode_id"]: row for row in metrics["_alert_episode_accounting"]}
        self.assertEqual(accounting["quality-window-alert"]["reason"], "data_quality_event_window")
        self.assertFalse(accounting["quality-window-alert"]["included_in_precision_denominator"])
        self.assertEqual(exclusions["total_events"], 5)

        overlap_events = [
            _event("a", "motor-01.motor_current", start + timedelta(seconds=4), start + timedelta(seconds=6)),
            _event("b", "motor-01.motor_current", start + timedelta(seconds=5), start + timedelta(seconds=7)),
        ]
        overlap_dataset = dict(metric_dataset, events=overlap_events)
        with self.assertRaises(AnomalyEvaluationError):
            _event_records_and_metrics(overlap_dataset, ["motor-01"], ["motor-01.motor_current"], {"a": "machine_fault", "b": "sensor_fault"}, [], event_config)

    def test_alert_episode_partition_records_each_suppression_reason(self) -> None:
        start = datetime(2026, 1, 1, tzinfo=UTC)
        events = [
            _event("positive-other", "motor-01.motor_temperature", start + timedelta(seconds=5), start + timedelta(seconds=6), event_type="jam_or_slip"),
            _event("quality", "motor-01.motor_current", start + timedelta(seconds=8), start + timedelta(seconds=9), event_type="dropout"),
            _event("ignored", "motor-01.motor_temperature", start + timedelta(seconds=11), start + timedelta(seconds=12), event_type="stuck_value"),
            _event("ignored-later", "motor-01.motor_temperature", start + timedelta(seconds=16), start + timedelta(seconds=17), event_type="stuck_value"),
        ]
        dataset = {"manifest": {"sampling_interval_ms": 1000}, "observations": {}, "events": events, "split_times": {"validation": (start, start + timedelta(seconds=3)), "test": (start + timedelta(seconds=3), start + timedelta(seconds=20))}}
        episodes = [
            _episode("positive-other-alert", "motor-01.motor_current", start + timedelta(seconds=5), start + timedelta(seconds=5), start + timedelta(seconds=5, milliseconds=500)),
            _episode("quality-alert", "motor-01.motor_current", start + timedelta(seconds=8), start + timedelta(seconds=8), start + timedelta(seconds=8, milliseconds=500)),
            _episode("ignored-alert", "motor-01.motor_current", start + timedelta(seconds=11), start + timedelta(seconds=11), start + timedelta(seconds=11, milliseconds=500)),
            _episode("clean-crossing-alert", "motor-01.motor_current", start + timedelta(seconds=15), start + timedelta(seconds=15), start + timedelta(seconds=17)),
        ]
        classifications = {"positive-other": "machine_fault", "quality": "data_quality", "ignored": "ignored", "ignored-later": "ignored"}
        _incidents, _clean, metrics, _exclusions = _event_records_and_metrics(dataset, ["motor-01"], ["motor-01.motor_current", "motor-01.motor_temperature"], classifications, episodes, {"detection_grace_points": 0})
        partition = metrics["alert_episode_partition"]
        self.assertEqual(partition["total_alert_episodes"], 4)
        self.assertEqual(partition["matched_eligible_alert_episodes"], 0)
        self.assertEqual(partition["unmatched_eligible_same_signal_alert_episodes"], 0)
        self.assertEqual(partition["clean_false_alert_signal_episodes"], 1)
        self.assertEqual(partition["positive_nonmatching_signal_false_alert_episodes"], 1)
        self.assertEqual(partition["suppressed_event_window_alert_episodes"], 2)
        self.assertEqual(partition["suppressed_event_window_by_reason"], {"data_quality": 1, "ignored": 1})
        self.assertEqual(
            partition["total_alert_episodes"],
            partition["matched_eligible_alert_episodes"]
            + partition["unmatched_eligible_same_signal_alert_episodes"]
            + partition["positive_nonmatching_signal_false_alert_episodes"]
            + partition["clean_false_alert_signal_episodes"]
            + partition["suppressed_event_window_alert_episodes"],
        )
        self.assertEqual(sum(partition["suppressed_event_window_by_reason"].values()), partition["suppressed_event_window_alert_episodes"])
        accounting = {row["episode_id"]: row for row in metrics["_alert_episode_accounting"]}
        self.assertEqual(accounting["clean-crossing-alert"]["partition"], "clean_false_alert")
        self.assertEqual(accounting["clean-crossing-alert"]["onset_event_ids"], [])

    def test_simultaneous_multisignal_clean_alerts_are_equipment_deduplicated(self) -> None:
        start = datetime(2026, 1, 1, tzinfo=UTC)
        dataset = {"manifest": {"sampling_interval_ms": 1000}, "observations": {}, "events": [], "split_times": {"validation": (start, start + timedelta(seconds=3)), "test": (start + timedelta(seconds=3), start + timedelta(seconds=20))}}
        episodes = [
            _episode("current-alert", "motor-01.motor_current", start + timedelta(seconds=5), start + timedelta(seconds=5), start + timedelta(seconds=7)),
            _episode("temperature-alert", "motor-01.motor_temperature", start + timedelta(seconds=5), start + timedelta(seconds=5), start + timedelta(seconds=8)),
            _episode("later-alert", "motor-01.motor_current", start + timedelta(seconds=12), start + timedelta(seconds=12), start + timedelta(seconds=13)),
            _episode("adjacent-alert", "motor-01.motor_temperature", start + timedelta(seconds=13), start + timedelta(seconds=13), start + timedelta(seconds=14)),
        ]
        _incidents, clean, metrics, _ = _event_records_and_metrics(dataset, ["motor-01"], ["motor-01.motor_current", "motor-01.motor_temperature"], {}, episodes, {"detection_grace_points": 0})
        self.assertEqual(len(clean), 2)
        self.assertEqual(clean[0]["source_alert_episode_ids"], ["current-alert", "temperature-alert"])
        self.assertEqual(clean[1]["source_alert_episode_ids"], ["later-alert", "adjacent-alert"])
        self.assertEqual(metrics["clean_false_alert_episode_count"], 2)
        self.assertEqual(metrics["clean_false_alert_equipment_episode_count"], 2)
        self.assertEqual(metrics["clean_false_alert_signal_episode_count"], 4)
        self.assertEqual(metrics["overall"]["evaluated_alert_episode_count"], 4)
        self.assertEqual(metrics["overall"]["incident_precision"], 0.0)

    def test_deterministic_output_strict_nan_and_no_overwrite(self) -> None:
        config_path, output, config = self._config("deterministic")
        _first_path, first = _evaluate_core(config_path, ROOT)
        _second_path, second = _evaluate_core(config_path, ROOT)
        self.assertEqual(_canonical_json(first), _canonical_json(second))
        result_with_nan = copy.deepcopy(first)
        result_with_nan["parameters"]["robust_z_threshold"] = math.nan
        with self.assertRaises(AnomalyEvaluationError):
            _validate_result(result_with_nan, ROOT)
        evaluate_anomalies(config_path, ROOT)
        before = (output / "result.json").read_bytes()
        with self.assertRaises(AnomalyEvaluationError):
            evaluate_anomalies(config_path, ROOT)
        self.assertEqual((output / "result.json").read_bytes(), before)

        duplicate_path = self.temp_root / "duplicate.json"
        duplicate_path.write_text('{"schema_version":"0.1","schema_version":"0.1"}', encoding="utf-8")
        with self.assertRaises(AnomalyEvaluationError):
            _strict_json(duplicate_path, "duplicate config")
        nan_config = copy.deepcopy(config)
        nan_config_path = self.temp_root / "nan.json"
        nan_config_path.write_text(json.dumps(nan_config, sort_keys=True).replace('"robust_z_threshold": 4.0', '"robust_z_threshold": NaN'), encoding="utf-8")
        with self.assertRaises(AnomalyEvaluationError):
            evaluate_anomalies(nan_config_path, ROOT)

    def test_path_symlink_and_toctou_fail_closed(self) -> None:
        config_path, output, config = self._config("security")
        traversal = copy.deepcopy(config)
        traversal["output_dir"] = "artifacts/../outside-anomaly-output"
        traversal_path = self.temp_root / "traversal.json"
        traversal_path.write_text(json.dumps(traversal, sort_keys=True), encoding="utf-8")
        with self.assertRaises(AnomalyEvaluationError):
            evaluate_anomalies(traversal_path, ROOT)
        nested = copy.deepcopy(config)
        nested["output_dir"] = f"artifacts/nested/{self.token}"
        nested_path = self.temp_root / "nested.json"
        nested_path.write_text(json.dumps(nested, sort_keys=True), encoding="utf-8")
        with self.assertRaises(AnomalyEvaluationError):
            evaluate_anomalies(nested_path, ROOT)

        link_path = self.temp_root / "config-link.json"
        try:
            os.symlink(config_path, link_path)
        except (OSError, NotImplementedError):
            link_path = None
        if link_path is not None:
            with self.assertRaises(AnomalyEvaluationError):
                evaluate_anomalies(link_path, ROOT)
            dataset_link = self.temp_root / "dataset-link"
            os.symlink(self.dataset_path, dataset_link)
            linked_dataset = copy.deepcopy(config)
            linked_dataset["dataset_path"] = self._relative(dataset_link)
            linked_path = self.temp_root / "linked-dataset.json"
            linked_path.write_text(json.dumps(linked_dataset, sort_keys=True), encoding="utf-8")
            with self.assertRaises(AnomalyEvaluationError):
                evaluate_anomalies(linked_path, ROOT)

        with patch.object(anomaly_module, "_assert_input_unchanged", side_effect=AnomalyEvaluationError("input changed during evaluation")):
            with self.assertRaises(AnomalyEvaluationError):
                evaluate_anomalies(config_path, ROOT)
        self.assertFalse(output.exists())

        with patch.object(
            anomaly_module,
            "_assert_input_unchanged",
            side_effect=[None, AnomalyEvaluationError("input changed before completion marker")],
        ):
            with self.assertRaises(AnomalyEvaluationError):
                evaluate_anomalies(config_path, ROOT)
        self.assertTrue(output.is_dir())
        self.assertFalse((output / ".complete").exists())


if __name__ == "__main__":
    unittest.main()
