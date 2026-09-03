import math
import json
import os
import shutil
import subprocess
import sys
import unittest
from datetime import datetime, timedelta, timezone

from banto_ai.baselines import (
    CovariateLinearRegressionForecaster,
    EWMAForecaster,
    HoltLinearForecaster,
    MovingAverageForecaster,
    SeasonalNaiveForecaster,
)
from banto_ai.metrics import MetricError, interval_coverage, interval_width, mae, mase, rmse, weighted_interval_score
from banto_ai.benchmark import _aggregate_predictions, _model_state_bytes, _percentile, _split_indices_for_rows
from banto_ai.benchmark import BenchmarkError, _validate_config
from banto_ai.manifest import ManifestValidationError, load_json, validate, validate_manifest
from banto_ai.types import ForecastRequest, ForecastSeriesResult, QuantileForecast, SignalMetadata, SignalPoint, TimeSeries
from banto_ai.generator import generate_synthetic


class Phase2Tests(unittest.TestCase):
    def _series(self, signal_id: str, values: list[float], role: str = "target") -> TimeSeries:
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        return TimeSeries(
            SignalMetadata(signal_id, signal_id, "unit", 1000, role),
            tuple(SignalPoint(start + timedelta(seconds=i), value) for i, value in enumerate(values)),
        )

    def test_all_statistical_baselines_have_common_contract(self) -> None:
        context = self._series("target", [1, 2, 3, 4, 5])
        request = ForecastRequest((context,), ("target",), 2, (0.1, 0.5, 0.9))
        for model in (SeasonalNaiveForecaster(2), MovingAverageForecaster(2), EWMAForecaster(0.5), HoltLinearForecaster()):
            with self.subTest(model=model.model_version):
                result = model.forecast(request).forecasts[0]
                self.assertEqual(len(result.point_forecast), 2)
                self.assertTrue(all(math.isfinite(v) for v in result.point_forecast))
                self.assertEqual(len(result.timestamps), 2)

    def test_covariate_regression_exact_case_and_no_fallback(self) -> None:
        target = self._series("target", [2, 5, 8, 11, 14, 17])
        covariate = self._series("load_proxy", [0, 1, 2, 3, 4, 5, 6, 7], "covariate")
        request = ForecastRequest((target,), ("target",), 2, known_future_covariates=(covariate,))
        result = CovariateLinearRegressionForecaster(("load_proxy",)).forecast(request).forecasts[0]
        self.assertEqual(result.point_forecast, (20.0, 23.0))
        with self.assertRaises(ValueError):
            CovariateLinearRegressionForecaster(("missing",)).forecast(request)

    def test_metrics_golden_case(self) -> None:
        actual, predicted = (1.0, 2.0, 3.0), (2.0, 2.0, 2.0)
        self.assertAlmostEqual(mae(actual, predicted), 2 / 3)
        self.assertAlmostEqual(rmse(actual, predicted), math.sqrt(2 / 3))
        self.assertAlmostEqual(mase(actual, predicted, (0.0, 1.0, 2.0, 3.0)), 2 / 3)
        forecasts = {0.1: (0.0, 1.0, 2.0), 0.5: predicted, 0.9: (4.0, 3.0, 4.0)}
        self.assertAlmostEqual(interval_coverage(actual, forecasts[0.1], forecasts[0.9]), 1.0)
        self.assertAlmostEqual(interval_width(forecasts[0.1], forecasts[0.9]), 8 / 3)
        self.assertTrue(math.isfinite(weighted_interval_score(actual, forecasts)))
        self.assertAlmostEqual(weighted_interval_score((2.0,), {0.1: (0.0,), 0.5: (2.0,), 0.9: (4.0,)}), 0.4 / 1.5)
        outside = {0.1: (0.0,), 0.5: (2.0,), 0.9: (4.0,)}
        self.assertAlmostEqual(weighted_interval_score((-1.0,), outside), 2.9 / 1.5)
        self.assertAlmostEqual(weighted_interval_score((5.0,), outside), 2.9 / 1.5)

    def test_raw_point_aggregation_keeps_rmse_distinct_from_mae(self) -> None:
        def prediction(actual: float, predicted: float, timestamp: str) -> dict[str, object]:
            return {"model": "last-value", "equipment_id": "equipment-1", "target_signal_id": "equipment-1.target", "operating_mode": "nominal", "split": "test", "origin_timestamp": "2026-01-01T00:00:00Z", "timestamp": timestamp, "lead_time": 1, "actual": actual, "point_forecast": predicted, "quantiles": {"0.1": predicted - 1.0, "0.5": predicted, "0.9": predicted + 1.0}}

        rows = [prediction(0.0, 0.0, "2026-01-01T00:00:01Z"), prediction(2.0, 0.0, "2026-01-01T00:00:02Z")]
        result = _aggregate_predictions(rows, (0.1, 0.5, 0.9), {("equipment-1", "equipment-1.target"): (0.0, 1.0, 2.0)})
        self.assertEqual(result["count"], 2)
        self.assertAlmostEqual(result["mae"], 1.0)
        self.assertAlmostEqual(result["rmse"], math.sqrt(2.0))
        self.assertAlmostEqual(result["mase"], 1.0)

    def test_metrics_fail_closed(self) -> None:
        with self.assertRaises(MetricError):
            mae((1.0,), (float("nan"),))
        with self.assertRaises(MetricError):
            mase((1.0,), (1.0,), (1.0, 1.0, 1.0))
        with self.assertRaises(MetricError):
            weighted_interval_score((1.0,), {0.1: (2.0,), 0.5: (1.0,), 0.9: (0.0,)})
        with self.assertRaises(ValueError):
            ForecastSeriesResult(
                "target",
                tuple(point.timestamp for point in self._series("target", [1, 2]).points),
                (1.0, 2.0),
                (QuantileForecast(0.1, (2.0, 3.0)), QuantileForecast(0.9, (1.0, 2.0))),
            )
        with self.assertRaises(MetricError):
            weighted_interval_score((1.0,), {0.1: (0.0,), 0.5: (1.0,)})
        self.assertEqual(_percentile([0.001, 0.002, 0.003], 0.5), 0.002)
        self.assertGreaterEqual(_percentile([0.001, 0.002, 0.003], 0.95), _percentile([0.001, 0.002, 0.003], 0.5))

    def test_split_manifest_is_the_only_boundary_source(self) -> None:
        rows = [{"timestamp": (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=i)).isoformat().replace("+00:00", "Z")} for i in range(10)]
        manifest = {"splits": [
            {"split_id": "train", "start_timestamp": rows[0]["timestamp"], "end_timestamp": rows[3]["timestamp"]},
            {"split_id": "validation", "start_timestamp": rows[3]["timestamp"], "end_timestamp": rows[7]["timestamp"]},
            {"split_id": "test", "start_timestamp": rows[7]["timestamp"], "end_timestamp": "2026-01-01T00:00:10.000Z"},
        ]}
        self.assertEqual(_split_indices_for_rows(rows, manifest, "equipment-1"), {"train": (0, 3), "validation": (3, 7), "test": (7, 10)})

    def test_clean_checkout_benchmark_subprocess_and_overwrite_refusal(self) -> None:
        root = __import__("pathlib").Path(__file__).resolve().parents[1]
        sample_config = load_json(root / "examples/configs/benchmark-small.json")
        dataset_rel = sample_config["dataset_path"]
        output_rel = sample_config["output_dir"]
        dataset = root / dataset_rel
        output = root / output_rel
        if dataset.exists():
            shutil.rmtree(dataset)
        if output.exists():
            shutil.rmtree(output)
        try:
            generate_synthetic(root / "examples/configs/synthetic-motor-small.json", dataset, root)
            env = os.environ.copy()
            env.pop("PYTHONPATH", None)
            command = [sys.executable, "tools/evaluator/run_benchmark.py", "--config", "examples/configs/benchmark-small.json"]
            completed = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, check=False)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertTrue((output / "result.json").is_file())
            result = json.loads((output / "result.json").read_text(encoding="utf-8"))
            validate_manifest(output / "result.json", root / "schemas/benchmark-result.schema.json")
            self.assertEqual(set(result), {"schema_version", "result_type", "run_id", "status", "dataset_fingerprint", "generator_version", "run_config", "code_revision", "seed", "model_parameters", "prediction_count", "failures", "metrics", "runtime", "provenance"})
            self.assertEqual(result["dataset_fingerprint"], json.loads((dataset / "fingerprint.json").read_text(encoding="utf-8"))["dataset_fingerprint"])
            predictions = [json.loads(line) for line in (output / "predictions.jsonl").read_text(encoding="utf-8").splitlines()]
            prediction = predictions[0]
            self.assertEqual(set(prediction), {"model", "equipment_id", "target_signal_id", "operating_mode", "split", "origin_timestamp", "timestamp", "lead_time", "actual", "point_forecast", "quantiles"})
            self.assertAlmostEqual(result["metrics"]["aggregate"]["mae"], mae(tuple(row["actual"] for row in predictions), tuple(row["point_forecast"] for row in predictions)))
            self.assertAlmostEqual(result["metrics"]["aggregate"]["rmse"], rmse(tuple(row["actual"] for row in predictions), tuple(row["point_forecast"] for row in predictions)))
            self.assertNotAlmostEqual(result["metrics"]["aggregate"]["mae"], result["metrics"]["aggregate"]["rmse"])
            self.assertEqual(result["runtime"]["model_state_bytes"], _model_state_bytes(sample_config["models"]))
            self.assertEqual(set(result["runtime"]["model_state_bytes"]), {model["name"] for model in sample_config["models"]})
            self.assertTrue(all(isinstance(value, int) and value >= 0 for value in result["runtime"]["model_state_bytes"].values()))
            second = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, check=False)
            self.assertNotEqual(second.returncode, 0)
        finally:
            if dataset.exists():
                shutil.rmtree(dataset)
            if output.exists():
                shutil.rmtree(output)

    def test_config_schema_and_strict_parameter_gates(self) -> None:
        root = __import__("pathlib").Path(__file__).resolve().parents[1]
        config = load_json(root / "examples/configs/benchmark-small.json")
        validate(config, load_json(root / "schemas/benchmark-run-config.schema.json"))
        with self.assertRaises(ManifestValidationError):
            invalid = dict(config)
            invalid["unknown"] = True
            validate(invalid, load_json(root / "schemas/benchmark-run-config.schema.json"))
        for bad in ("C:/outside", "../outside", "..\\outside"):
            with self.assertRaises(BenchmarkError):
                invalid = dict(config)
                invalid["dataset_path"] = bad
                _validate_config(invalid, root)
        with self.assertRaises(BenchmarkError):
            invalid = dict(config)
            invalid["models"] = [{"name": "ewma", "parameters": {"alpha": "0.5"}}]
            _validate_config(invalid, root)
        with self.assertRaises(BenchmarkError):
            invalid = dict(config)
            invalid["models"] = [{"name": "last-value"}, {"name": "last-value"}]
            _validate_config(invalid, root)
        with self.assertRaises(ManifestValidationError):
            invalid = dict(config)
            invalid["models"] = [{"name": "ewma", "parameters": {"alpha": 0.5, "unexpected": 1}}]
            validate(invalid, load_json(root / "schemas/benchmark-run-config.schema.json"))
        for quantiles in ([0.5, 0.1, 0.9], [0.1, 0.5, 0.5, 0.9], [0.1, 0.2, 0.8, 0.9], [0.1, 0.5, 0.8]):
            with self.subTest(quantiles=quantiles), self.assertRaises(BenchmarkError):
                invalid = dict(config)
                invalid["quantiles"] = quantiles
                _validate_config(invalid, root)


if __name__ == "__main__":
    unittest.main()
