import json
from datetime import timedelta
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch

from banto_ai.benchmark import ModelRegistry, _make_request, run_benchmark
from banto_ai.contracts import Forecaster
from banto_ai.generator import generate_synthetic
from banto_ai.manifest import ManifestValidationError, load_json, validate
from banto_ai.types import ForecastResult, ForecastSeriesResult, QuantileForecast


ROOT = Path(__file__).resolve().parents[1]


class FakeNativeForecaster(Forecaster):
    def __init__(self, requests: list, *, fail: bool = False) -> None:
        self.requests = requests
        self.fail = fail

    def forecast(self, request):
        if self.fail:
            raise RuntimeError("injected inference failure")
        self.requests.append(request)
        reference = {series.metadata.signal_id: series for series in request.contexts}
        forecasts = []
        # 応答順を意図的に逆にし、runnerがtarget IDで対応付けることを検証する。
        for signal_id in reversed(request.target_signal_ids):
            context = reference[signal_id]
            last = float(context.points[-1].value)
            timestamps = tuple(context.points[-1].timestamp + timedelta(seconds=step) for step in range(1, request.horizon + 1))
            point = tuple(last + step for step in range(request.horizon))
            quantiles = tuple(QuantileForecast(q, tuple(value + (q - 0.5) * 2 for value in point)) for q in request.quantiles)
            forecasts.append(ForecastSeriesResult(signal_id, timestamps, point, quantiles))
        return ForecastResult(tuple(forecasts), "fake-native-0.1", request.profile_version)


class BenchmarkIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.dataset = ROOT / "artifacts" / "test-benchmark-integration-dataset"
        self.output = ROOT / "artifacts" / "test-benchmark-integration-output"
        for path in (self.dataset, self.output):
            if path.exists():
                shutil.rmtree(path)

    def tearDown(self):
        for path in (self.dataset, self.output):
            if path.exists():
                shutil.rmtree(path)

    def _config(self, models):
        value = load_json(ROOT / "examples" / "configs" / "benchmark-small.json")
        value.update(
            dataset_path="artifacts/test-benchmark-integration-dataset",
            output_dir="artifacts/test-benchmark-integration-output",
            models=models,
            past_only_covariate_ids=["load_proxy"],
            known_future_covariate_ids=[],
            validation_origin_stride=3,
            test_origin_stride=3,
            max_validation_origins=2,
            max_test_origins=2,
        )
        return value

    def _generate(self):
        generate_synthetic(ROOT / "examples" / "configs" / "synthetic-motor-small.json", self.dataset, ROOT)

    def test_factory_reuse_multi_target_id_mapping_native_and_result_schema(self):
        self._generate()
        requests = []
        built = []

        def factory(equipment_id, parameters):
            self.assertEqual(parameters, {})
            built.append(equipment_id)
            return FakeNativeForecaster(requests)

        config = self._config([{"name": "timesfm3", "quantile_policy": "native"}])
        config_path = ROOT / "artifacts" / "test-benchmark-integration-config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        try:
            output = run_benchmark(config_path, ROOT, ModelRegistry({"timesfm3": factory}))
        finally:
            config_path.unlink(missing_ok=True)
        self.assertEqual(sorted(built), ["conveyor-01", "motor-01"])
        self.assertTrue(requests)
        self.assertTrue(all(len(request.target_signal_ids) == 2 for request in requests))
        self.assertTrue(all(len(request.known_future_covariates) == 0 for request in requests))
        result = load_json(output / "result.json")
        validate(result, load_json(ROOT / "schemas" / "benchmark-result.schema.json"))
        self.assertEqual(result["provenance"]["quantile_policy_by_model"], {"timesfm3": "native"})
        self.assertEqual(set(result["metrics"]["by_model"]), {"timesfm3"})
        self.assertEqual(result["metrics"]["by_model"]["timesfm3"]["count"], 24)
        self.assertEqual(result["runtime"]["latency_by_model"]["timesfm3"]["call_count"], 4)
        self.assertIn(result["runtime"]["memory_source"], {"os.process_peak_working_set", "os.resource.ru_maxrss", "tracemalloc.fallback"})
        predictions = [json.loads(line) for line in (output / "predictions.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual({item["target_signal_id"] for item in predictions}, {"motor-01.motor_current", "motor-01.motor_temperature", "conveyor-01.motor_current", "conveyor-01.motor_temperature"})

    def test_model_metrics_latency_and_origins_are_separate(self):
        self._generate()
        requests = []

        def factory(_equipment_id, _parameters):
            return FakeNativeForecaster(requests)

        config = self._config([{"name": "last-value"}, {"name": "timesfm3", "quantile_policy": "native"}])
        config_path = ROOT / "artifacts" / "test-benchmark-integration-config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        try:
            output = run_benchmark(config_path, ROOT, ModelRegistry({"timesfm3": factory}))
        finally:
            config_path.unlink(missing_ok=True)
        result = load_json(output / "result.json")
        self.assertEqual(set(result["metrics"]["by_model"]), {"last-value", "timesfm3"})
        self.assertEqual(result["metrics"]["by_model"]["last-value"]["count"], 24)
        self.assertEqual(result["metrics"]["by_model"]["timesfm3"]["count"], 24)
        self.assertEqual(result["runtime"]["latency_by_model"]["last-value"]["call_count"], 4)
        self.assertEqual(result["runtime"]["latency_by_model"]["timesfm3"]["call_count"], 4)
        predictions = [json.loads(line) for line in (output / "predictions.jsonl").read_text(encoding="utf-8").splitlines()]
        origins = {
            model: {item["origin_timestamp"] for item in predictions if item["model"] == model}
            for model in ("last-value", "timesfm3")
        }
        self.assertEqual(origins["last-value"], origins["timesfm3"])
        self.assertEqual(result["provenance"]["origin_selection"]["test"]["motor-01"]["count"], 2)

    def test_build_failure_is_isolated_from_other_model(self):
        self._generate()

        def factory(_equipment_id, _parameters):
            raise RuntimeError("injected construction failure")

        config = self._config([{"name": "last-value"}, {"name": "timesfm3", "quantile_policy": "native"}])
        config_path = ROOT / "artifacts" / "test-benchmark-integration-config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        try:
            output = run_benchmark(config_path, ROOT, ModelRegistry({"timesfm3": factory}))
        finally:
            config_path.unlink(missing_ok=True)
        result = load_json(output / "result.json")
        self.assertEqual(result["status"], "partial")
        self.assertEqual(set(result["metrics"]["by_model"]), {"last-value"})
        self.assertTrue(all(item["model"] == "timesfm3" for item in result["failures"]))

    def test_memory_source_is_recorded_from_shared_process_helper(self):
        self._generate()
        config = self._config([{"name": "last-value"}])
        config_path = ROOT / "artifacts" / "test-benchmark-integration-config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        try:
            with patch("banto_ai.benchmark.process_peak_memory_bytes", return_value=(123456, "os.resource.ru_maxrss")):
                result = load_json(run_benchmark(config_path, ROOT) / "result.json")
        finally:
            config_path.unlink(missing_ok=True)
        self.assertEqual(result["runtime"]["peak_memory_bytes"], 123456)
        self.assertEqual(result["runtime"]["memory_source"], "os.resource.ru_maxrss")

    def test_timesfm_runtime_paths_are_not_benchmark_config_fields(self):
        config = self._config([{"name": "timesfm3", "quantile_policy": "native"}])
        schema = load_json(ROOT / "schemas" / "benchmark-run-config.schema.json")
        for field in ("cache_dir", "license_manifest"):
            invalid = json.loads(json.dumps(config))
            invalid["models"][0]["parameters"] = {field: "external-value"}
            with self.assertRaises(ManifestValidationError):
                validate(invalid, schema)

    def test_past_only_and_known_future_boundaries_are_strict(self):
        self._generate()
        manifest = load_json(self.dataset / "dataset-manifest.json")
        rows = [json.loads(line) for line in (self.dataset / manifest["data_path"]).read_text(encoding="utf-8").splitlines() if json.loads(line)["equipment_id"] == "motor-01"]
        signals = {item["signal_id"]: item for item in manifest["signals"]}
        target = "motor-01.motor_current"
        past = "motor-01.load_proxy"
        request = _make_request(rows, signals, (target,), 30, 12, 3, (0.1, 0.5, 0.9), (past,), ())
        self.assertEqual(len(request.contexts[1].points), 12)
        self.assertEqual(len(request.known_future_covariates), 0)
        request = _make_request(rows, signals, (target,), 30, 12, 3, (0.1, 0.5, 0.9), (), (past,))
        self.assertEqual(len(request.contexts[1].points), 12)
        self.assertEqual(len(request.known_future_covariates[0].points), 15)
        self.assertEqual(request.known_future_covariates[0].points[-1].timestamp, request.contexts[0].points[-1].timestamp + timedelta(seconds=3))

    def test_model_failure_is_isolated_from_other_model(self):
        self._generate()
        built = []

        def factory(equipment_id, parameters):
            built.append(equipment_id)
            return FakeNativeForecaster([], fail=True)

        config = self._config([{"name": "last-value"}, {"name": "timesfm3", "quantile_policy": "native"}])
        config_path = ROOT / "artifacts" / "test-benchmark-integration-config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        try:
            result = load_json(run_benchmark(config_path, ROOT, ModelRegistry({"timesfm3": factory})) / "result.json")
        finally:
            config_path.unlink(missing_ok=True)
        self.assertEqual(result["status"], "partial")
        self.assertTrue(result["prediction_count"] > 0)
        self.assertTrue(any(item["model"] == "timesfm3" for item in result["failures"]))
        self.assertTrue(all(item["model"] == "last-value" for item in [json.loads(line) for line in (self.output / "predictions.jsonl").read_text(encoding="utf-8").splitlines()]))


if __name__ == "__main__":
    unittest.main()
