import copy
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from uuid import uuid4

from banto_ai.event_slices import (
    EventSliceError,
    _classify_context,
    _classify_forecast,
    _macro,
    _metric,
    analyze_event_slices,
)
from banto_ai.manifest import load_json, validate
from banto_ai.matrix import run_matrix


ROOT = Path(__file__).resolve().parents[1]


class EventSliceTests(unittest.TestCase):
    def setUp(self):
        self.token = uuid4().hex
        self.artifact_root = ROOT / "artifacts" / "test-event-slices" / self.token
        self.control = self.artifact_root / "control"
        self.control.mkdir(parents=True, exist_ok=False)
        self.addCleanup(lambda: shutil.rmtree(self.artifact_root, ignore_errors=True))

    def _write_json(self, path: Path, value: dict) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        return path

    def _relative(self, path: Path) -> str:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()

    def _run_matrix(self, seeds=(42,), label="main") -> Path:
        generator = copy.deepcopy(load_json(ROOT / "examples" / "configs" / "synthetic-motor-small.json"))
        generator["dataset_id"] = "synthetic-event-slice-" + self.token[:8]
        generator["events"] = [
            {"event_id": "target-covered", "event_type": "spike", "equipment_id": "motor-01", "signal_id": "motor_current", "start_sample": 48, "end_sample": 51, "magnitude": 2.0, "enabled": True},
            {"event_id": "target-uncovered", "event_type": "overheating_trend", "equipment_id": "motor-01", "signal_id": "motor_temperature", "start_sample": 30, "end_sample": 32, "magnitude": 2.0, "enabled": True},
            {"event_id": "boundary-before-test", "event_type": "spike", "equipment_id": "motor-01", "signal_id": "motor_current", "start_sample": 46, "end_sample": 48, "magnitude": 1.0, "enabled": True},
            {"event_id": "covariate-context", "event_type": "stuck_value", "equipment_id": "motor-01", "signal_id": "load_proxy", "start_sample": 47, "end_sample": 48, "magnitude": 0.0, "enabled": True},
            {"event_id": "covariate-simultaneous", "event_type": "stuck_value", "equipment_id": "motor-01", "signal_id": "load_proxy", "start_sample": 48, "end_sample": 50, "magnitude": 0.0, "enabled": True},
            {"event_id": "other-simultaneous", "event_type": "spike", "equipment_id": "motor-01", "signal_id": "vibration_feature", "start_sample": 49, "end_sample": 50, "magnitude": 1.0, "enabled": True},
        ]
        generator_path = self._write_json(self.control / "generator.json", generator)
        benchmark = copy.deepcopy(load_json(ROOT / "examples" / "configs" / "benchmark-small.json"))
        benchmark.update({
            "run_id": "base",
            "models": [{"name": "last-value"}],
            "past_only_covariate_ids": ["load_proxy"],
            "known_future_covariate_ids": [],
            "validation_origin_stride": 1,
            "test_origin_stride": 1,
            "max_validation_origins": 1,
            "max_test_origins": 1,
            "horizon": 3,
            "context_length": 3,
        })
        benchmark_path = self._write_json(self.control / "benchmark.json", benchmark)
        matrix_id = "event-slice-" + label + "-" + self.token[:10]
        matrix = {
            "schema_version": "0.1",
            "matrix_id": matrix_id,
            "generator_config_path": self._relative(generator_path),
            "benchmark_config_path": self._relative(benchmark_path),
            "dataset_output_root": self._relative(self.artifact_root / ("datasets-" + label)),
            "benchmark_output_root": self._relative(self.artifact_root / ("runs-" + label)),
            "matrix_output_dir": self._relative(self.artifact_root / ("matrix-" + label)),
            "axes": {"seeds": list(seeds), "horizons": [3], "context_lengths": [3]},
        }
        matrix_path = self._write_json(self.control / "matrix.json", matrix)
        return run_matrix(matrix_path, ROOT)

    def test_boundary_priority_and_context_categories(self):
        utc = timezone.utc
        event = lambda event_id, signal, start, end: {"event_id": event_id, "signal_id": signal, "equipment_id": "motor-01", "start": datetime(2026, 1, 1, 0, 0, start, tzinfo=utc), "end": datetime(2026, 1, 1, 0, 0, end, tzinfo=utc), "event_type": "spike"}
        target = event("target", "motor-01.motor_current", 10, 20)
        other = event("other", "motor-01.vibration_feature", 10, 25)
        covariate = event("cov", "motor-01.load_proxy", 5, 10)
        events = [target, other, covariate]
        self.assertEqual(_classify_forecast(events, "motor-01", target["signal_id"], target["start"])[0], "target_event")
        self.assertEqual(_classify_forecast(events, "motor-01", target["signal_id"], target["end"])[0], "other_signal_event")
        self.assertEqual(_classify_forecast(events, "motor-01", target["signal_id"], datetime(2026, 1, 1, 0, 0, 30, tzinfo=utc))[0], "clean")
        interval = timedelta(seconds=1)
        self.assertEqual(_classify_context(events, "motor-01", "motor-01.motor_temperature", set(), {covariate["signal_id"]}, datetime(2026, 1, 1, 0, 0, 10, tzinfo=utc), 5, interval)[0], "context_covariate_event")
        self.assertEqual(_classify_context(events, "motor-01", target["signal_id"], set(), set(), datetime(2026, 1, 1, 0, 0, 20, tzinfo=utc), 10, interval)[0], "context_target_event")
        self.assertEqual(_classify_context(events, "motor-01", "motor-01.motor_temperature", set(), set(), datetime(2026, 1, 1, 0, 0, 10, tzinfo=utc), 5, interval)[0], "context_other_signal_event")
        self.assertEqual(_classify_context(events, "motor-01", "motor-01.motor_temperature", set(), set(), datetime(2026, 1, 1, 0, 0, 30, tzinfo=utc), 5, interval)[0], "context_clean")

        simultaneous_context = [target, covariate]
        self.assertEqual(_classify_context(simultaneous_context, "motor-01", target["signal_id"], set(), {covariate["signal_id"]}, datetime(2026, 1, 1, 0, 0, 20, tzinfo=utc), 15, interval)[0], "context_target_event")

    def test_existing_predictions_are_analyzed_with_coverage_audit(self):
        matrix_result_dir = self._run_matrix()
        matrix_result = matrix_result_dir / "result.json"
        output = self.artifact_root / "analysis"
        output_path = analyze_event_slices(self._relative(matrix_result), self._relative(output), ROOT)
        result = load_json(output_path / "result.json")
        validate(result, load_json(ROOT / "schemas" / "benchmark-event-slice-result.schema.json"))
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["counts"]["analyzed_cells"], 1)
        self.assertEqual(result["counts"]["total_prediction_count"], result["counts"]["analyzed_prediction_count"])
        cell = result["cells"][0]
        coverage = {item["event_id"]: item for item in cell["event_coverage"]}
        self.assertTrue(coverage["target-covered"]["covered_by_forecast_timestamp"])
        self.assertFalse(coverage["target-uncovered"]["covered_by_forecast_timestamp"])
        self.assertFalse(coverage["boundary-before-test"]["overlaps_test_split"])
        self.assertTrue(coverage["other-simultaneous"]["covered_by_forecast_timestamp"])
        self.assertTrue(coverage["covariate-simultaneous"]["covered_by_forecast_timestamp"])
        self.assertGreater(coverage["covariate-context"]["context_point_count"], 0)
        self.assertEqual(cell["forecast_exposure_counts"]["target_event"], 3)
        self.assertEqual(cell["context_exposure_counts"]["context_covariate_event"], 3)
        self.assertTrue(any(row["dimension"] == "operating_mode" for row in cell["metric_rows"]))
        self.assertTrue(any(row["unit"] == "A" and row["target_signal_key"] == "motor_current" for row in result["macro_summary"]))
        self.assertIn("未cover", (output_path / "summary.md").read_text(encoding="utf-8"))

    def test_macro_is_mean_of_cell_metrics_not_pooled_points(self):
        matrix_result_dir = self._run_matrix((42, 43))
        matrix_result_path = matrix_result_dir / "result.json"
        output_path = analyze_event_slices(self._relative(matrix_result_path), self._relative(self.artifact_root / "analysis-two-seeds"), ROOT)
        result = load_json(output_path / "result.json")
        cell_metrics = [
            row["metrics"]["mae"]
            for cell in result["cells"]
            for row in cell["metric_rows"]
            if row["dimension"] == "forecast_exposure" and row["exposure"] == "clean" and row["target_signal_key"] == "motor_temperature" and row["unit"] == "degC"
        ]
        self.assertEqual(len(cell_metrics), 2)
        macro = next(row for row in result["macro_summary"] if row["dimension"] == "forecast_exposure" and row["exposure"] == "clean" and row["target_signal_key"] == "motor_temperature" and row["unit"] == "degC")
        self.assertAlmostEqual(macro["metrics"]["mae"]["mean"], sum(cell_metrics) / 2.0)
        matrix = load_json(matrix_result_path)
        pooled_actual = []
        pooled_predicted = []
        for cell in matrix["cells"]:
            cell_result = load_json(ROOT / cell["result_path"])
            for line in (ROOT / cell["output_dir"] / "predictions.jsonl").read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                if row["target_signal_id"].endswith(".motor_temperature"):
                    pooled_actual.append(row["actual"])
                    pooled_predicted.append(row["point_forecast"])
        pooled_mae = sum(abs(actual - predicted) for actual, predicted in zip(pooled_actual, pooled_predicted)) / len(pooled_actual)
        self.assertNotAlmostEqual(macro["metrics"]["mae"]["mean"], pooled_mae, places=10)
        rows = [
            {"dimension": "forecast_exposure", "exposure": "clean", "operating_mode": None, "model": "m", "target_signal_key": "x", "unit": "u", "horizon": 1, "context_length": 2, "metrics": {"count": 1, "mae": 1.0}},
            {"dimension": "forecast_exposure", "exposure": "clean", "operating_mode": None, "model": "m", "target_signal_key": "x", "unit": "u", "horizon": 1, "context_length": 2, "metrics": {"count": 9, "mae": 3.0}},
        ]
        pure_macro = _macro(rows)[0]
        self.assertEqual(pure_macro["metrics"]["mae"]["mean"], 2.0)
        self.assertNotEqual(pure_macro["metrics"]["mae"]["mean"], (1.0 * 1 + 3.0 * 9) / 10)

    def test_mase_uses_each_equipment_scale(self):
        quantiles = {"0.1": 1.0, "0.5": 1.0, "0.9": 1.0}
        points = [
            {"equipment_id": "e1", "actual": 2.0, "point_forecast": 3.0, "quantiles": quantiles},
            {"equipment_id": "e2", "actual": 20.0, "point_forecast": 21.0, "quantiles": quantiles},
        ]
        metrics = _metric(points, {"e1": [0.0, 1.0], "e2": [0.0, 10.0]})
        self.assertAlmostEqual(metrics["mase"], 0.55)

    def test_matrix_semantics_and_cell_revision_fail_closed(self):
        matrix_result_dir = self._run_matrix()
        matrix_result_path = matrix_result_dir / "result.json"
        matrix = load_json(matrix_result_path)
        matrix["counts"]["total_cells"] += 1
        self._write_json(matrix_result_path, matrix)
        with self.assertRaises(EventSliceError):
            analyze_event_slices(self._relative(matrix_result_path), self._relative(self.artifact_root / "analysis-counts"), ROOT)

        matrix_result_dir = self._run_matrix(label="r")
        matrix_result_path = matrix_result_dir / "result.json"
        matrix = load_json(matrix_result_path)
        cell = matrix["cells"][0]
        cell_result_path = ROOT / cell["result_path"]
        cell_result = load_json(cell_result_path)
        cell_result["code_revision"]["head"] = "0" * 40
        self._write_json(cell_result_path, cell_result)
        with self.assertRaises(EventSliceError):
            analyze_event_slices(self._relative(matrix_result_path), self._relative(self.artifact_root / "analysis-revision"), ROOT)

        matrix_result_dir = self._run_matrix(label="x")
        matrix_result_path = matrix_result_dir / "result.json"
        matrix = load_json(matrix_result_path)
        cell = matrix["cells"][0]
        cell_result_path = ROOT / cell["result_path"]
        cell_result = load_json(cell_result_path)
        cell_result["provenance"]["origin_selection"]["test"]["motor-01"]["indices"] = [49]
        self._write_json(cell_result_path, cell_result)
        with self.assertRaises(EventSliceError):
            analyze_event_slices(self._relative(matrix_result_path), self._relative(self.artifact_root / "analysis-extra-origin"), ROOT)

    def test_partial_cell_reports_failure_and_missing_prediction_groups(self):
        matrix_result_dir = self._run_matrix(label="partial")
        matrix_result_path = matrix_result_dir / "result.json"
        matrix = load_json(matrix_result_path)
        cell = matrix["cells"][0]
        cell_result_path = ROOT / cell["result_path"]
        cell_result = load_json(cell_result_path)
        prediction_path = ROOT / cell["output_dir"] / "predictions.jsonl"
        lines = prediction_path.read_text(encoding="utf-8").splitlines()
        prediction_path.write_text("\n".join(lines[3:]) + "\n", encoding="utf-8")
        cell_result["prediction_count"] -= 3
        cell_result["status"] = "partial"
        cell_result["failures"].append({"model": "last-value", "equipment_id": "motor-01", "target_signal_id": "motor-01.motor_current", "status": "failed", "reason": "test fixture failure", "split": "test"})
        self._write_json(cell_result_path, cell_result)
        cell["status"] = "partial"
        cell["benchmark_failure_count"] = 1
        matrix["status"] = "partial"
        matrix["counts"].update({"successful_cells": 0, "partial_cells": 1, "failed_cells": 0, "completed_cells": 1})
        self._write_json(matrix_result_path, matrix)
        output_path = analyze_event_slices(self._relative(matrix_result_path), self._relative(self.artifact_root / "analysis-partial"), ROOT)
        result = load_json(output_path / "result.json")
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["cells"][0]["status"], "partial")
        self.assertEqual(result["cells"][0]["excluded_prediction_count"], 3)
        self.assertTrue(result["cells"][0]["completeness"]["missing_groups"])
        self.assertEqual(result["cells"][0]["source_failures"][-1]["reason"], "test fixture failure")

    def test_origin_metadata_config_duplicates_and_failure_domain_fail_closed(self):
        matrix_result_dir = self._run_matrix(label="o")
        matrix_result_path = matrix_result_dir / "result.json"
        matrix = load_json(matrix_result_path)
        cell = matrix["cells"][0]
        cell_result_path = ROOT / cell["result_path"]
        cell_result = load_json(cell_result_path)
        selection = cell_result["provenance"]["origin_selection"]["test"]["motor-01"]
        selection["count"] += 1
        self._write_json(cell_result_path, cell_result)
        with self.assertRaises(EventSliceError):
            analyze_event_slices(self._relative(matrix_result_path), self._relative(self.artifact_root / "analysis-origin-metadata"), ROOT)

        matrix_result_dir = self._run_matrix(label="d")
        matrix_result_path = matrix_result_dir / "result.json"
        matrix = load_json(matrix_result_path)
        cell_result_path = ROOT / matrix["cells"][0]["result_path"]
        cell_result = load_json(cell_result_path)
        cell_result["run_config"]["models"].append({"name": "last-value"})
        self._write_json(cell_result_path, cell_result)
        with self.assertRaises(EventSliceError):
            analyze_event_slices(self._relative(matrix_result_path), self._relative(self.artifact_root / "analysis-config-duplicates"), ROOT)

        matrix_result_dir = self._run_matrix(label="f")
        matrix_result_path = matrix_result_dir / "result.json"
        matrix = load_json(matrix_result_path)
        cell = matrix["cells"][0]
        cell_result_path = ROOT / cell["result_path"]
        cell_result = load_json(cell_result_path)
        cell_result["failures"].append({"model": "not-a-model", "equipment_id": "motor-01", "target_signal_id": "motor-01.motor_current", "status": "failed", "reason": "unrelated", "split": "test"})
        self._write_json(cell_result_path, cell_result)
        cell["benchmark_failure_count"] = 1
        self._write_json(matrix_result_path, matrix)
        with self.assertRaises(EventSliceError):
            analyze_event_slices(self._relative(matrix_result_path), self._relative(self.artifact_root / "analysis-failure-domain"), ROOT)

    def test_duplicate_prediction_and_symlink_escape_fail_without_source_mutation(self):
        matrix_result_dir = self._run_matrix()
        matrix_result_path = matrix_result_dir / "result.json"
        matrix = load_json(matrix_result_path)
        cell = matrix["cells"][0]
        cell_result_path = ROOT / cell["result_path"]
        cell_result = load_json(cell_result_path)
        prediction_path = ROOT / cell["output_dir"] / "predictions.jsonl"
        lines = prediction_path.read_text(encoding="utf-8").splitlines()
        prediction_path.write_text("\n".join(lines + [lines[0]]) + "\n", encoding="utf-8")
        cell_result["prediction_count"] += 1
        self._write_json(cell_result_path, cell_result)
        source_before = matrix_result_path.read_bytes()
        with self.assertRaises(EventSliceError):
            analyze_event_slices(self._relative(matrix_result_path), self._relative(self.artifact_root / "analysis-duplicate"), ROOT)
        self.assertEqual(matrix_result_path.read_bytes(), source_before)

        with tempfile.TemporaryDirectory() as external:
            link = self.artifact_root / "outside-link"
            try:
                os.symlink(external, link, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("directory symlinks are unavailable")
            with self.assertRaises(EventSliceError):
                analyze_event_slices("artifacts/does-not-exist/result.json", link.relative_to(ROOT).as_posix() + "/analysis", ROOT)

    def test_fail_closed_for_traversal_and_existing_output(self):
        with self.assertRaises(EventSliceError):
            analyze_event_slices("../outside/result.json", "artifacts/test-event-slices/bad", ROOT)
        matrix_result_dir = self._run_matrix()
        matrix_result = matrix_result_dir / "result.json"
        output = self.artifact_root / "analysis-existing"
        output.mkdir()
        with self.assertRaises(EventSliceError):
            analyze_event_slices(self._relative(matrix_result), self._relative(output), ROOT)
        self.assertEqual(list(output.iterdir()), [])

    def test_cli_help_works_from_external_cwd(self):
        with tempfile.TemporaryDirectory() as external:
            completed = subprocess.run([sys.executable, str(ROOT / "tools" / "evaluator" / "analyze_event_slices.py"), "--help"], cwd=external, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--matrix-result", completed.stdout)


if __name__ == "__main__":
    unittest.main()
