import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from math import inf, nan
from pathlib import Path
from unittest.mock import patch

from banto_ai.license_gate import evaluate_promotion
from banto_ai.cli import validate_naive_result, validate_samples
from banto_ai.manifest import ManifestValidationError, load_json, validate
from banto_ai.naive import LastValueForecaster, mean_absolute_error
from banto_ai.safety import RepositorySafetyError, scan_repository
from banto_ai.types import (
    AnomalyRequest,
    AnomalyResult,
    AnomalySeriesResult,
    ForecastRequest,
    ForecastSeriesResult,
    QualityStatus,
    QuantileForecast,
    SignalMetadata,
    SignalPoint,
    TimeSeries,
)


ROOT = Path(__file__).resolve().parents[1]


class Phase0Tests(unittest.TestCase):
    def _series(self) -> TimeSeries:
        metadata = SignalMetadata("s1", "current", "A", 1000)
        points = tuple(
            SignalPoint(datetime(2026, 1, 1, 0, 0, index, tzinfo=timezone.utc), float(index))
            for index in range(3)
        )
        return TimeSeries(metadata, points)

    def test_last_value_and_mae(self) -> None:
        result = LastValueForecaster().forecast(ForecastRequest(
            contexts=(self._series(),), target_signal_ids=("s1",), horizon=2, quantiles=(0.1, 0.9),
        ))
        forecast = result.forecasts[0]
        self.assertEqual(forecast.point_forecast, (2.0, 2.0))
        self.assertEqual(forecast.quality_status, QualityStatus.OK)
        self.assertEqual(result.profile_version, "baseline")
        self.assertEqual(mean_absolute_error((3.0, 4.0), forecast.point_forecast), 1.5)

    def test_multivariate_context_targets_and_known_future_covariate(self) -> None:
        speed = TimeSeries(
            SignalMetadata("speed", "conveyor speed", "%", 1000, role="covariate"),
            self._series().points,
        )
        request = ForecastRequest(
            contexts=(self._series(), speed),
            target_signal_ids=("s1",),
            horizon=2,
            known_future_covariates=(speed,),
        )
        result = LastValueForecaster().forecast(request)
        self.assertEqual([item.signal_id for item in result.forecasts], ["s1"])
        self.assertEqual(result.forecasts[0].point_forecast, (2.0, 2.0))

    def test_anomaly_contract_allows_multiple_series(self) -> None:
        request = AnomalyRequest((self._series(),), "detector-0.1.0")
        score = AnomalySeriesResult("s1", tuple(point.timestamp for point in self._series().points), (0.0, 0.1, 0.0), QualityStatus.OK)
        result = AnomalyResult((score,), request.model_version, request.profile_version)
        self.assertEqual(result.scores[0].signal_id, "s1")

    def test_timeseries_requires_strictly_increasing_timestamps(self) -> None:
        series = self._series()
        with self.assertRaises(ValueError):
            TimeSeries(series.metadata, (series.points[0], series.points[1], series.points[1]))
        with self.assertRaises(ValueError):
            TimeSeries(series.metadata, tuple(reversed(series.points)))

    def test_last_value_uses_context_end_after_trailing_missing(self) -> None:
        series = self._series()
        trailing_missing = SignalPoint(
            series.points[-1].timestamp + timedelta(seconds=1), None, QualityStatus.MISSING,
        )
        context = TimeSeries(series.metadata, series.points + (trailing_missing,))
        result = LastValueForecaster().forecast(ForecastRequest(
            contexts=(context,), target_signal_ids=("s1",), horizon=2,
        ))
        forecast = result.forecasts[0]
        self.assertEqual(forecast.point_forecast, (2.0, 2.0))
        self.assertEqual(forecast.quality_status, QualityStatus.MISSING)
        self.assertEqual(
            forecast.timestamps,
            (trailing_missing.timestamp + timedelta(seconds=1), trailing_missing.timestamp + timedelta(seconds=2)),
        )

    def test_output_types_reject_nonfinite_and_empty_values(self) -> None:
        timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for value in (nan, inf, -inf):
            with self.assertRaises(ValueError):
                QuantileForecast(0.5, (value,))
            with self.assertRaises(ValueError):
                ForecastSeriesResult("s1", (timestamp,), (value,), ())
            with self.assertRaises(ValueError):
                AnomalySeriesResult("s1", (timestamp,), (value,), QualityStatus.OK)
        with self.assertRaises(ValueError):
            ForecastSeriesResult("s1", (), (), ())
        with self.assertRaises(ValueError):
            ForecastSeriesResult("s1", (timestamp,), (), ())
        with self.assertRaises(ValueError):
            AnomalySeriesResult("s1", (), (), QualityStatus.OK)

    def test_output_types_require_strict_timestamps_and_quantiles(self) -> None:
        first = datetime(2026, 1, 1, tzinfo=timezone.utc)
        second = first + timedelta(seconds=1)
        quantile_values = (1.0, 1.0)
        q10 = QuantileForecast(0.1, quantile_values)
        q90 = QuantileForecast(0.9, quantile_values)
        with self.assertRaises(ValueError):
            ForecastSeriesResult("s1", (first, first), quantile_values, (q10,))
        with self.assertRaises(ValueError):
            ForecastSeriesResult("s1", (second, first), quantile_values, (q10,))
        with self.assertRaises(ValueError):
            ForecastSeriesResult("s1", (first, second), quantile_values, (q90, q10))
        with self.assertRaises(ValueError):
            ForecastSeriesResult("s1", (first, second), quantile_values, (q10, q10))
        with self.assertRaises(ValueError):
            AnomalySeriesResult("s1", (first, first), (0.0, 0.1), QualityStatus.OK)
        with self.assertRaises(ValueError):
            AnomalySeriesResult("s1", (second, first), (0.0, 0.1), QualityStatus.OK)

    def test_mean_absolute_error_rejects_nonfinite_values(self) -> None:
        for values in ((nan, 1.0), (1.0, inf), (1.0, -inf)):
            with self.assertRaises(ValueError):
                mean_absolute_error(values, (1.0, 1.0))
            with self.assertRaises(ValueError):
                mean_absolute_error((1.0, 1.0), values)

    def test_manifest_samples_validate(self) -> None:
        for manifest_type in ("dataset", "run", "result", "model-license"):
            schema = json.loads((ROOT / "schemas" / f"{manifest_type}-manifest.schema.json").read_text(encoding="utf-8"))
            manifests = sorted((ROOT / "examples" / "manifests").glob(f"{manifest_type}*.json"))
            self.assertTrue(manifests)
            for path in manifests:
                validate(json.loads(path.read_text(encoding="utf-8")), schema)

    def test_manifest_rejects_unknown_property(self) -> None:
        schema = json.loads((ROOT / "schemas" / "model-license-manifest.schema.json").read_text(encoding="utf-8"))
        invalid = {"schema_version": "0.1", "manifest_type": "model-license", "model_id": "x", "code_license": "MIT", "weights_license": "MIT", "allowed_use": "product-candidate", "extra": True}
        with self.assertRaises(ManifestValidationError):
            validate(invalid, schema)

    def test_result_manifest_rejects_nonfinite_metrics(self) -> None:
        schema = json.loads((ROOT / "schemas/result-manifest.schema.json").read_text(encoding="utf-8"))
        base = {
            "schema_version": "0.1", "manifest_type": "result", "result_id": "r1", "run_id": "run1",
            "status": "complete", "model_version": "model1", "profile_version": "baseline",
        }
        for value in (nan, inf, -inf):
            with self.subTest(value=value), self.assertRaises(ManifestValidationError):
                validate(dict(base, metrics={"mae": value}), schema)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            for literal in ("NaN", "Infinity", "-Infinity", "1e999"):
                path.write_text('{"metrics":{"mae":' + literal + '}}', encoding="utf-8")
                with self.subTest(literal=literal), self.assertRaises(ManifestValidationError):
                    load_json(path)

    def test_manifest_rejects_missing_license_reference(self) -> None:
        schema = json.loads((ROOT / "schemas/run-manifest.schema.json").read_text(encoding="utf-8"))
        manifest = json.loads((ROOT / "examples/manifests/run-naive.json").read_text(encoding="utf-8"))
        manifest.pop("model_license_manifest")
        with self.assertRaises(ManifestValidationError):
            validate(manifest, schema)

    def test_dataset_manifest_rejects_unsafe_data_paths(self) -> None:
        schema = json.loads((ROOT / "schemas/dataset-manifest.schema.json").read_text(encoding="utf-8"))
        manifest = json.loads((ROOT / "examples/manifests/dataset-synthetic-motor.json").read_text(encoding="utf-8"))
        for data_path in ("/tmp/data.json", "C:/data.json", "C:\\data.json", "../data.json", "examples/../data.json"):
            invalid = dict(manifest, data_path=data_path)
            with self.subTest(data_path=data_path), self.assertRaises(ManifestValidationError):
                validate(invalid, schema)

    def test_validate_samples_rejects_a_missing_sample_type(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "examples" / "manifests").mkdir(parents=True)
            with self.assertRaises(ManifestValidationError):
                validate_samples(root)

    def test_smoke_detects_declared_mae_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result_path = root / "examples" / "manifests" / "result-naive.json"
            result_path.parent.mkdir(parents=True)
            result_path.write_text(json.dumps({"metrics": {"mae": 1.0}}), encoding="utf-8")
            with self.assertRaises(ManifestValidationError):
                validate_naive_result(root, 0.75)

    def test_license_gate_fails_closed(self) -> None:
        research = json.loads((ROOT / "examples/manifests/model-license-timesfm3.json").read_text(encoding="utf-8"))
        self.assertFalse(evaluate_promotion(research, "product-candidate").allowed)
        self.assertFalse(evaluate_promotion({"code_license": "", "weights_license": "MIT", "allowed_use": "product-candidate"}, "product-candidate").allowed)
        self.assertFalse(evaluate_promotion({"code_license": "unknown", "weights_license": "MIT", "allowed_use": "product-candidate"}, "product-candidate").allowed)
        self.assertFalse(evaluate_promotion({"code_license": "MIT", "weights_license": "MIT", "allowed_use": "unknown"}, "product-candidate").allowed)
        self.assertFalse(evaluate_promotion({"code_license": "MIT", "weights_license": "MIT", "allowed_use": "product-candidate"}, "unknown-target").allowed)
        product = json.loads((ROOT / "examples/manifests/model-license-last-value.json").read_text(encoding="utf-8"))
        self.assertTrue(evaluate_promotion(product, "product-candidate").allowed)

    def test_safety_guard_rejects_dangerous_tracked_path_and_csv(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "customer-data").mkdir()
            dangerous = root / "customer-data" / "input.csv"
            dangerous.write_text("secret,data\n")
            compressed = root / "forecast.csv.gz"
            compressed.write_bytes(b"not a customer file")
            findings = scan_repository(root, paths=(dangerous, compressed))
            self.assertTrue(any("customer-data" in finding for finding in findings))
            self.assertTrue(any("forecast.csv.gz" in finding for finding in findings))

    def test_safety_guard_ignores_local_data_in_non_git_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            local = root / "datasets" / "local"
            local.mkdir(parents=True)
            (local / "customer-data.csv").write_text("customer,data\n")
            (root / "data").mkdir()
            (root / "data" / "private.csv").write_text("private,data\n")
            (root / "README.md").write_text("safe fallback fixture\n")
            self.assertEqual(scan_repository(root), [])

    def test_safety_guard_scans_git_tracked_files_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".git").mkdir()
            tracked = root / "customer-data" / "tracked.json"
            tracked.parent.mkdir()
            tracked.write_text("{}")
            (root / "customer-data" / "untracked.csv").write_text("customer,data\n")
            (root / "safe.md").write_text("safe\n")
            with patch("banto_ai.safety.subprocess.run") as run:
                run.return_value.stdout = b"customer-data/tracked.json\0"
                findings = scan_repository(root)
            self.assertTrue(any("tracked.json" in finding for finding in findings))
            self.assertFalse(any("untracked.csv" in finding for finding in findings))

    def test_safety_guard_fails_closed_when_git_enumeration_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".git").mkdir()
            with patch("banto_ai.safety.subprocess.run", side_effect=OSError("git unavailable")):
                with self.assertRaises(RepositorySafetyError):
                    scan_repository(root)

    def test_safety_guard_accepts_repository(self) -> None:
        self.assertEqual(scan_repository(ROOT), [])


if __name__ == "__main__":
    unittest.main()
