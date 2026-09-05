from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import banto_ai.anomaly_matrix_analysis as analysis


ROOT = Path(__file__).resolve().parents[1]


class AnomalyMatrixAnalysisPureTests(unittest.TestCase):
    def test_config_validation_is_read_only_and_pinned(self) -> None:
        output = ROOT / "artifacts" / "anomaly-multiseed-v02-analysis"
        if output.exists():
            self.fail("analysis output must not exist during pure config validation")
        before = sorted(path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file())
        summary = analysis.validate_analysis_config(root=ROOT)
        after = sorted(path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file())
        self.assertEqual(before, after)
        self.assertEqual(summary["status"], "configuration_valid")
        self.assertEqual(summary["run_status"], "not_run")
        self.assertEqual(summary["performance_status"], "not_evaluated")
        self.assertEqual(summary["config_canonical_sha256"], analysis.EXPECTED_ANALYSIS_CONFIG_CANONICAL_SHA256)

    def test_ratio_of_sums_and_percentile_definition(self) -> None:
        aggregate = analysis._Aggregate(precision_num=9, precision_den=235, machine_num=0, machine_den=120, sensor_num=9, sensor_den=120, clean_alerts=222, clean_hours=10.8, clean_milliseconds=38_880_000)
        values = analysis._primary_values(aggregate)
        self.assertAlmostEqual(values["overall_incident_precision"], 9 / 235)
        self.assertAlmostEqual(values["clean_false_alerts_per_8_equipment_hours"], 222 / 10.8 * 8)
        self.assertEqual(analysis.percentile_linear([0.0, 10.0, 20.0], 0.025), 0.5)
        self.assertEqual(analysis.percentile_linear([0.0, 10.0, 20.0], 0.975), 19.5)

    def test_bootstrap_draws_are_version_stable(self) -> None:
        draws, digest = analysis.bootstrap_draws()
        self.assertEqual(len(draws), 10000)
        self.assertTrue(all(len(row) == 10 and all(0 <= value < 10 for value in row) for row in draws))
        self.assertEqual(digest, "5b311c270aaef7bb942e0c4fbe761e8e225aaa0a1314a8bd2e70875f0fd46548")
        self.assertEqual(analysis.bootstrap_draws()[1], digest)

    def test_undefined_replicate_is_inconclusive(self) -> None:
        empty = analysis._Aggregate()
        point, ci = analysis._bootstrap_metric([empty] * 10, [[0] * 10], "machine_fault_recall")
        self.assertIsNone(point)
        self.assertEqual(ci["status"], "inconclusive")
        self.assertEqual(ci["undefined_replicates"], 1)

    def test_precision_slice_bootstrap_uses_ratio_of_sums_and_unknown_kind_fails(self) -> None:
        slices = [{"motor-01|nominal": [2, 4]} for _ in range(10)]
        point, ci = analysis._bootstrap_slice(slices, [[0] * 10], "motor-01|nominal", "precision")
        self.assertEqual(point, 0.5)
        self.assertEqual(ci["status"], "pass")
        with self.assertRaises(analysis.AnalysisGlobalFailure):
            analysis._bootstrap_slice(slices, [[0] * 10], "motor-01|nominal", "unexpected")

    def test_slice_maps_reject_non_object_values_at_schema_level(self) -> None:
        schema = json.loads((ROOT / "schemas/anomaly-multiseed-analysis-result-v0.2.schema.json").read_text(encoding="utf-8"))
        estimates = schema["$defs"]["estimates"]["properties"]
        for field in ("availability_by_mode", "incident_slices", "precision_slices", "clean_alert_slices"):
            self.assertEqual(estimates[field]["type"], "object")
            for bad_value in ([], "not-an-object"):
                with self.assertRaises(analysis.ManifestValidationError):
                    analysis.validate(bad_value, estimates[field])

    def test_manifest_validator_enforces_one_of_and_property_names(self) -> None:
        one_of = {"oneOf": [{"const": "pass"}, {"const": "inconclusive"}]}
        analysis.validate("pass", one_of)
        with self.assertRaises(analysis.ManifestValidationError):
            analysis.validate("other", one_of)
        with self.assertRaises(analysis.ManifestValidationError):
            analysis.validate("both", {"oneOf": [{"type": "string"}, {"minLength": 1}]})

        property_names = {"type": "object", "propertyNames": {"pattern": "^allowed$"}, "additionalProperties": {}}
        analysis.validate({"allowed": 1}, property_names)
        with self.assertRaises(analysis.ManifestValidationError):
            analysis.validate({"blocked": 1}, property_names)

    def test_promotion_gate_schemas_are_metric_specific_and_strict(self) -> None:
        schema = json.loads((ROOT / "schemas/anomaly-multiseed-analysis-result-v0.2.schema.json").read_text(encoding="utf-8"))
        metric_gate = schema["$defs"]["overallIncidentPrecisionGate"]
        valid = {"status": "pass", "point": 0.9, "ci_lower": 0.8, "ci_upper": 1.0, "threshold": {"point_min": 0.8, "ci_lower_min": 0.6}}
        analysis.validate(valid, metric_gate, root=schema)
        with self.assertRaises(analysis.ManifestValidationError):
            analysis.validate({key: value for key, value in valid.items() if key != "threshold"}, metric_gate, root=schema)
        bad_threshold = copy.deepcopy(valid)
        bad_threshold["threshold"]["point_min"] = 0.7
        with self.assertRaises(analysis.ManifestValidationError):
            analysis.validate(bad_threshold, metric_gate, root=schema)

        availability_gate = schema["$defs"]["signalAvailabilityGate"]
        keys = ["motor-01.motor_current", "motor-01.motor_temperature", "motor-01.conveyor_speed", "motor-01.vibration_feature", "conveyor-01.motor_current", "conveyor-01.motor_temperature", "conveyor-01.conveyor_speed", "conveyor-01.vibration_feature"]
        availability = {key: {"available_points": 1, "total_points": 1, "availability_ratio": 1.0} for key in keys}
        analysis.validate({"status": "pass", "minimum": 0.95, "signals": availability}, availability_gate, root=schema)
        with self.assertRaises(analysis.ManifestValidationError):
            analysis.validate({"status": "pass", "minimum": 0.95, "signals": {**availability, "other.signal": availability[keys[0]]}}, availability_gate, root=schema)
        missing_signal = dict(availability)
        del missing_signal[keys[-1]]
        with self.assertRaises(analysis.ManifestValidationError):
            analysis.validate({"status": "pass", "minimum": 0.95, "signals": missing_signal}, availability_gate, root=schema)

    def test_cell_aggregate_preserves_fully_qualified_signal_ids(self) -> None:
        config = {
            "layouts": [{"layout_id": "layout-0", "operating_mode": "nominal"}],
            "expanded_window_grace_points": 3,
            "test_split": {"start_sample": 0},
        }
        generator = {
            "start_timestamp": "2026-01-01T00:00:00Z",
            "sampling_interval_ms": 1000,
            "events": [],
            "regimes": [{"regime": "nominal", "start_sample": 0, "end_sample": 10}],
        }
        cell = {"layout_id": "layout-0", "_generator_config": generator}
        evaluation = {
            "metrics": {
                "overall": {"matched_eligible_alert_episodes": 0, "evaluated_alert_episode_count": 0},
                "clean_false_alert_equipment_episode_count": 0,
                "clean_monitored_equipment_hours": 1 / 3600,
                "score_availability_by_signal": {},
            },
            "incidents": [],
            "scores": [{
                "equipment_id": "motor-01", "signal_id": "motor-01.motor_current",
                "operating_mode": "nominal", "timestamp": "2026-01-01T00:00:00Z", "available": True,
            }],
            "alert_episode_accounting": [], "alert_episodes": [], "clean_false_alert_episodes": [],
        }
        aggregate, slices = analysis._cell_aggregate(evaluation, cell, config)
        self.assertEqual(aggregate.availability, {"motor-01.motor_current": [1, 1]})
        self.assertEqual(slices["availability_modes"], {"motor-01.motor_current|nominal": [1, 1]})
        self.assertEqual(len(slices["clean_slices"]), 20)
        self.assertEqual(slices["clean_slices"]["motor-01|*"], [0.0, 1000.0])
        self.assertEqual(slices["clean_slices"]["conveyor-01|*"], [0.0, 0.0])

        malformed = copy.deepcopy(evaluation)
        malformed["scores"][0]["signal_id"] = "conveyor-01.motor_current"
        with self.assertRaises(analysis.AnalysisGlobalFailure):
            analysis._cell_aggregate(malformed, cell, config)

    def test_analysis_publish_is_non_overwriting_and_cleans_failed_staging(self) -> None:
        result = {
            "status": "pass", "run_status": "complete", "engineering_status": "pass", "performance_status": "pass",
            "bootstrap": {"algorithm_id": "test", "resamples": 1, "draw_digest": "digest"},
            "estimates": {"primary": {}}, "promotion_gates": {},
        }
        with tempfile.TemporaryDirectory(prefix="analysis-publish-") as raw:
            root = Path(raw)
            output = root / "analysis"
            published = analysis._publish_analysis(root, output, result, lambda: None)
            self.assertEqual(published, output)
            self.assertTrue((output / ".complete").is_file())
            with self.assertRaises(analysis.AnalysisGlobalFailure):
                analysis._publish_analysis(root, output, result, lambda: None)

            failed_output = root / "failed"
            with self.assertRaises(RuntimeError):
                analysis._publish_analysis(root, failed_output, result, lambda: (_ for _ in ()).throw(RuntimeError("verify")))
            self.assertFalse(failed_output.exists())

    def test_gate_status_preserves_fail_and_inconclusive(self) -> None:
        threshold = {"point_min": 0.8, "ci_lower_min": 0.6}
        self.assertEqual(analysis._gate_status(0.9, {"status": "pass", "lower": 0.7, "upper": 1.0}, threshold), "pass")
        self.assertEqual(analysis._gate_status(0.7, {"status": "pass", "lower": 0.7, "upper": 1.0}, threshold), "fail")
        self.assertEqual(analysis._gate_status(None, {"status": "inconclusive", "lower": None, "upper": None}, threshold), "inconclusive")

    def test_config_profile_mix_and_nonfinite_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="analysis-config-") as raw:
            repository = Path(raw)
            for relative in (
                "examples/configs/anomaly-multiseed-analysis-v0.2.json",
                "schemas/anomaly-multiseed-analysis-config-v0.2.schema.json",
            ):
                target = repository / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / relative, target)
            config_path = repository / "examples/configs/anomaly-multiseed-analysis-v0.2.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["matrix_id"] = "anomaly-multiseed-v01"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaises(analysis.AnomalyMatrixAnalysisError):
                analysis.validate_analysis_config(root=repository)

            config = json.loads((ROOT / "examples/configs/anomaly-multiseed-analysis-v0.2.json").read_text(encoding="utf-8"))
            config["input_root"] = "../outside"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaises(analysis.AnomalyMatrixAnalysisError):
                analysis.validate_analysis_config(root=repository)

    def test_config_validation_rechecks_all_inputs_for_toctou_drift(self) -> None:
        files = (
            "examples/configs/anomaly-multiseed-analysis-v0.2.json",
            "schemas/anomaly-multiseed-analysis-config-v0.2.schema.json",
            "schemas/anomaly-multiseed-analysis-result-v0.2.schema.json",
            "examples/configs/anomaly-multiseed-v0.2.json",
            "schemas/anomaly-multiseed-matrix-result-v0.2.schema.json",
        )
        for mutated in files[:3]:
            with self.subTest(mutated=mutated), tempfile.TemporaryDirectory(prefix="analysis-toctou-") as raw:
                repository = Path(raw)
                for relative in files:
                    target = repository / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(ROOT / relative, target)

                def mutate(repo: Path, _config_path: str | Path) -> None:
                    target = repo / mutated
                    target.write_bytes(target.read_bytes() + b" ")

                with patch.object(analysis, "_ANALYSIS_VALIDATION_FINAL_READ_HOOK", mutate):
                    with self.assertRaises(analysis.AnomalyMatrixAnalysisError):
                        analysis.validate_analysis_config(root=repository)
