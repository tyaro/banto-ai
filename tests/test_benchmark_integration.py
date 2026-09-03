import json
from datetime import timedelta
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch
from uuid import uuid4

from banto_ai.benchmark import BenchmarkError, ModelRegistry, _dimension_metrics, _make_request, run_benchmark
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
        self.artifact_root = ROOT / "artifacts" / f"test-benchmark-integration-{uuid4().hex}"
        self.artifact_root.mkdir(parents=True, exist_ok=False)
        self._owned_paths = [self.artifact_root]
        self.dataset = self.artifact_root / "dataset"
        self.output = self.artifact_root / "output"
        self.config_path = self.artifact_root / "benchmark-config.json"

    def tearDown(self):
        for path in reversed(self._owned_paths):
            try:
                if path.is_dir() and not path.is_symlink():
                    shutil.rmtree(path)
                else:
                    path.unlink(missing_ok=True)
            except OSError:
                pass

    def _repo_relative(self, path):
        return path.resolve().relative_to(ROOT.resolve()).as_posix()

    def _config(self, models):
        value = load_json(ROOT / "examples" / "configs" / "benchmark-small.json")
        value.update(
            dataset_path=self._repo_relative(self.dataset),
            output_dir=self._repo_relative(self.output),
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
        generate_synthetic(ROOT / "examples" / "configs" / "synthetic-motor-small.json", self._repo_relative(self.dataset), ROOT)

    def _write_config(self, config):
        if self.config_path not in self._owned_paths:
            self._owned_paths.append(self.config_path)
        self.config_path.write_text(json.dumps(config), encoding="utf-8")
        return Path(self._repo_relative(self.config_path))

    def _run(self, config, registry=None):
        config_path = self._write_config(config)
        self.assertFalse(config_path.is_absolute())
        self.assertNotIn("\\", config_path.as_posix())
        self.assertNotIn("\\", config["dataset_path"])
        self.assertNotIn("\\", config["output_dir"])
        return run_benchmark(config_path, ROOT, registry)

    def test_factory_reuse_multi_target_id_mapping_native_and_result_schema(self):
        self._generate()
        requests = []
        built = []

        def factory(equipment_id, parameters):
            self.assertEqual(parameters, {})
            built.append(equipment_id)
            return FakeNativeForecaster(requests)

        config = self._config([{"name": "timesfm3", "quantile_policy": "native"}])
        output = self._run(config, ModelRegistry({"timesfm3": factory}))
        self.assertEqual(sorted(built), ["conveyor-01", "motor-01"])
        self.assertTrue(requests)
        self.assertTrue(all(len(request.target_signal_ids) == 2 for request in requests))
        self.assertTrue(all(len(request.known_future_covariates) == 0 for request in requests))
        result = load_json(output / "result.json")
        validate(result, load_json(ROOT / "schemas" / "benchmark-result.schema.json"))
        self.assertEqual(result["provenance"]["quantile_policy_by_model"], {"timesfm3": "native"})
        self.assertEqual(set(result["metrics"]["by_model"]), {"timesfm3"})
        self.assertEqual(result["metrics"]["by_model"]["timesfm3"]["count"], 24)
        self.assertEqual(
            [(item["model"], item["target_signal_key"], item["unit"]) for item in result["metrics"]["by_model_target"]],
            [("timesfm3", "motor_current", "A"), ("timesfm3", "motor_temperature", "degC")],
        )
        self.assertEqual(
            [(item["equipment_id"], item["target_signal_id"], item["metrics"]["count"]) for item in result["metrics"]["by_model_equipment_target"]],
            [
                ("motor-01", "motor-01.motor_current", 6),
                ("motor-01", "motor-01.motor_temperature", 6),
                ("conveyor-01", "conveyor-01.motor_current", 6),
                ("conveyor-01", "conveyor-01.motor_temperature", 6),
            ],
        )
        summary = (output / "summary.md").read_text(encoding="utf-8")
        self.assertIn("## model-target別metrics", summary)
        self.assertIn("## model-equipment-target別metrics", summary)

        invalid = json.loads(json.dumps(result))
        invalid["metrics"]["by_model_target"][0]["extra"] = True
        with self.assertRaises(ManifestValidationError):
            validate(invalid, load_json(ROOT / "schemas" / "benchmark-result.schema.json"))
        invalid = json.loads(json.dumps(result))
        del invalid["metrics"]["by_model_equipment_target"][0]["metrics"]["count"]
        with self.assertRaises(ManifestValidationError):
            validate(invalid, load_json(ROOT / "schemas" / "benchmark-result.schema.json"))
        self.assertEqual(result["runtime"]["latency_by_model"]["timesfm3"]["call_count"], 4)
        self.assertIn(result["runtime"]["memory_source"], {"os.process_peak_working_set", "os.resource.ru_maxrss", "tracemalloc.fallback"})
        predictions = [json.loads(line) for line in (output / "predictions.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual({item["target_signal_id"] for item in predictions}, {"motor-01.motor_current", "motor-01.motor_temperature", "conveyor-01.motor_current", "conveyor-01.motor_temperature"})

    def test_omitted_targets_use_each_equipments_manifest_targets(self):
        self._generate()
        expected = {
            "motor-01": ("motor-01.motor_current", "motor-01.motor_temperature", "motor-01.conveyor_speed", "motor-01.vibration_feature"),
            "conveyor-01": ("conveyor-01.motor_current", "conveyor-01.motor_temperature", "conveyor-01.conveyor_speed", "conveyor-01.vibration_feature"),
        }
        for equipment_id, expected_targets in expected.items():
            with self.subTest(equipment_id=equipment_id):
                requests = []

                def factory(_equipment_id, _parameters):
                    return FakeNativeForecaster(requests)

                config = self._config([{"name": "timesfm3", "quantile_policy": "native"}])
                config.pop("target_signal_ids")
                config["equipment_ids"] = [equipment_id]
                output = self.output / equipment_id
                config["output_dir"] = self._repo_relative(output)
                result_path = self._run(config, ModelRegistry({"timesfm3": factory}))
                result = load_json(result_path / "result.json")
                self.assertTrue(requests)
                self.assertTrue(all(request.target_signal_ids == expected_targets for request in requests))
                self.assertEqual(
                    [item["target_signal_id"] for item in result["metrics"]["by_model_equipment_target"]],
                    list(expected_targets),
                )

    def test_full_ids_are_rejected_across_equipment_and_allowed_for_one(self):
        self._generate()

        cases = (
            {"target_signal_ids": ["motor-01.motor_current"]},
            {"past_only_covariate_ids": ["motor-01.load_proxy"]},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides):
                config = self._config([{"name": "last-value"}])
                config.update(overrides)
                with self.assertRaisesRegex(BenchmarkError, "multiple equipment.*short ID"):
                    self._run(config)

        requests = []

        def factory(_equipment_id, _parameters):
            return FakeNativeForecaster(requests)

        config = self._config([{"name": "timesfm3", "quantile_policy": "native"}])
        config.update(
            equipment_ids=["motor-01"],
            target_signal_ids=["motor-01.motor_current"],
            past_only_covariate_ids=["motor-01.load_proxy"],
        )
        self._run(config, ModelRegistry({"timesfm3": factory}))
        self.assertTrue(requests)
        self.assertTrue(all(request.target_signal_ids == ("motor-01.motor_current",) for request in requests))
        self.assertTrue(all(request.contexts[1].metadata.signal_id == "motor-01.load_proxy" for request in requests))

    def test_duplicate_or_empty_targets_are_rejected(self):
        self._generate()
        for target_ids, message in (
            (["motor_current", "motor-01.motor_current"], "logical target keys"),
            ([], "too few items"),
        ):
            with self.subTest(target_ids=target_ids):
                config = self._config([{"name": "last-value"}])
                config["target_signal_ids"] = target_ids
                with self.assertRaisesRegex(BenchmarkError, message):
                    self._run(config)

    def test_model_metrics_latency_and_origins_are_separate(self):
        self._generate()
        requests = []

        def factory(_equipment_id, _parameters):
            return FakeNativeForecaster(requests)

        config = self._config([{"name": "last-value"}, {"name": "timesfm3", "quantile_policy": "native"}])
        output = self._run(config, ModelRegistry({"timesfm3": factory}))
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
        output = self._run(config, ModelRegistry({"timesfm3": factory}))
        result = load_json(output / "result.json")
        self.assertEqual(result["status"], "partial")
        self.assertEqual(set(result["metrics"]["by_model"]), {"last-value"})
        self.assertEqual(len(result["metrics"]["by_model_target"]), 2)
        self.assertTrue(all(item["model"] == "last-value" for item in result["metrics"]["by_model_target"]))
        self.assertTrue(all(item["model"] == "timesfm3" for item in result["failures"]))

    def test_dimension_aggregation_fails_closed_on_mixed_units(self):
        with self.assertRaises(BenchmarkError):
            _dimension_metrics(
                [
                    {"model": "last-value", "equipment_id": "motor-01", "target_signal_id": "motor-01.motor_current"},
                    {"model": "last-value", "equipment_id": "conveyor-01", "target_signal_id": "conveyor-01.motor_current"},
                ],
                (0.1, 0.5, 0.9),
                {},
                ("last-value",),
                ("motor-01", "conveyor-01"),
                {
                    "motor-01": (("motor-01.motor_current", "motor_current"),),
                    "conveyor-01": (("conveyor-01.motor_current", "motor_current"),),
                },
                {
                    ("motor-01", "motor-01.motor_current"): "A",
                    ("conveyor-01", "conveyor-01.motor_current"): "kA",
                },
            )

    def test_memory_source_is_recorded_from_shared_process_helper(self):
        self._generate()
        config = self._config([{"name": "last-value"}])
        with patch("banto_ai.benchmark.process_peak_memory_bytes", return_value=(123456, "os.resource.ru_maxrss")):
            result = load_json(self._run(config) / "result.json")
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
        with self.assertRaises(BenchmarkError):
            _make_request(rows, signals, (target,), len(rows) - 2, 12, 3, (), (), (past,))

    def test_known_future_series_is_identical_for_every_model(self):
        self._generate()
        requests = []

        def factory(_equipment_id, _parameters):
            return FakeNativeForecaster(requests)

        config = self._config([{"name": "last-value"}, {"name": "timesfm3", "quantile_policy": "native"}])
        config.update(past_only_covariate_ids=[], known_future_covariate_ids=["load_proxy"])
        self._run(config, ModelRegistry({"last-value": factory, "timesfm3": factory}))
        self.assertGreater(len(requests), 1)
        groups = {}
        for request in requests:
            equipment_id = request.target_signal_ids[0].split(".", 1)[0]
            origin_timestamp = request.contexts[0].points[-1].timestamp
            groups.setdefault((equipment_id, origin_timestamp), []).append(request)
        for grouped_requests in groups.values():
            encoded = [
                [(point.timestamp, point.value) for point in request.known_future_covariates[0].points]
                for request in grouped_requests
            ]
            self.assertTrue(all(len(points) == 15 for points in encoded))
            self.assertTrue(all(points == encoded[0] for points in encoded[1:]))

    def test_model_failure_is_isolated_from_other_model(self):
        self._generate()
        built = []

        def factory(equipment_id, parameters):
            built.append(equipment_id)
            return FakeNativeForecaster([], fail=True)

        config = self._config([{"name": "last-value"}, {"name": "timesfm3", "quantile_policy": "native"}])
        result = load_json(self._run(config, ModelRegistry({"timesfm3": factory})) / "result.json")
        self.assertEqual(result["status"], "partial")
        self.assertTrue(result["prediction_count"] > 0)
        self.assertTrue(any(item["model"] == "timesfm3" for item in result["failures"]))
        self.assertTrue(all(item["model"] == "last-value" for item in [json.loads(line) for line in (self.output / "predictions.jsonl").read_text(encoding="utf-8").splitlines()]))


if __name__ == "__main__":
    unittest.main()
