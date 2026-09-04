import copy
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from uuid import uuid4

from banto_ai.event_slices import (
    EventSliceError,
    _classify_context,
    _classify_forecast,
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

    def _run_matrix(self) -> Path:
        generator = copy.deepcopy(load_json(ROOT / "examples" / "configs" / "synthetic-motor-small.json"))
        generator["dataset_id"] = "synthetic-event-slice-" + self.token[:8]
        generator["events"] = [
            {"event_id": "target-covered", "event_type": "spike", "equipment_id": "motor-01", "signal_id": "motor_current", "start_sample": 48, "end_sample": 51, "magnitude": 2.0, "enabled": True},
            {"event_id": "target-uncovered", "event_type": "overheating_trend", "equipment_id": "motor-01", "signal_id": "motor_temperature", "start_sample": 30, "end_sample": 32, "magnitude": 2.0, "enabled": True},
            {"event_id": "covariate-context", "event_type": "stuck_value", "equipment_id": "motor-01", "signal_id": "load_proxy", "start_sample": 47, "end_sample": 48, "magnitude": 0.0, "enabled": True},
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
        matrix_id = "event-slice-" + self.token[:10]
        matrix = {
            "schema_version": "0.1",
            "matrix_id": matrix_id,
            "generator_config_path": self._relative(generator_path),
            "benchmark_config_path": self._relative(benchmark_path),
            "dataset_output_root": self._relative(self.artifact_root / "datasets"),
            "benchmark_output_root": self._relative(self.artifact_root / "runs"),
            "matrix_output_dir": self._relative(self.artifact_root / "matrix"),
            "axes": {"seeds": [42], "horizons": [3], "context_lengths": [3]},
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
        self.assertGreater(coverage["covariate-context"]["context_point_count"], 0)
        self.assertEqual(cell["forecast_exposure_counts"]["target_event"], 3)
        self.assertEqual(cell["context_exposure_counts"]["context_covariate_event"], 6)
        self.assertTrue(any(row["dimension"] == "operating_mode" for row in cell["metric_rows"]))
        self.assertTrue(any(row["unit"] == "A" and row["target_signal_key"] == "motor_current" for row in result["macro_summary"]))
        self.assertIn("未cover", (output_path / "summary.md").read_text(encoding="utf-8"))

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
            completed = subprocess.run(["py", "-3.14", str(ROOT / "tools" / "evaluator" / "analyze_event_slices.py"), "--help"], cwd=external, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--matrix-result", completed.stdout)


if __name__ == "__main__":
    unittest.main()
