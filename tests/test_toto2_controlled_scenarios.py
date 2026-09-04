from __future__ import annotations

import json
import math
from pathlib import Path
import shutil
import tempfile
import unittest

from banto_ai.adapters.toto2 import BackendForecast, OFFICIAL_QUANTILES, Toto2Adapter
from banto_ai.baselines import _finite_history
from banto_ai.benchmark import ModelRegistry, _make_request, _select_origins, run_benchmark
from banto_ai.generator import SIGNALS, generate_synthetic
from banto_ai.manifest import load_json, validate
from banto_ai.quality import check_dataset


ROOT = Path(__file__).resolve().parents[1]
SEEDS = (17, 29, 42, 73, 101)
HORIZONS = (15, 30)
CONTEXT_LENGTHS = (64, 120)
TRACKS = {
    "control": {
        "generator": "synthetic-toto2-controlled-control.json",
        "matrix": "benchmark-matrix-toto2-controlled-control.json",
        "events": (),
    },
    "target-fault": {
        "generator": "synthetic-toto2-controlled-target-fault.json",
        "matrix": "benchmark-matrix-toto2-controlled-target-fault.json",
        "events": (("motor-01", "motor_current", "jam_or_slip", 388, 396, "target"),),
    },
    "target-quality": {
        "generator": "synthetic-toto2-controlled-target-quality.json",
        "matrix": "benchmark-matrix-toto2-controlled-target-quality.json",
        "events": (
            ("motor-01", "motor_current", "dropout", 368, 372, "target"),
            ("motor-01", "motor_temperature", "stale_value", 372, 376, "target"),
        ),
    },
    "covariate-quality": {
        "generator": "synthetic-toto2-controlled-covariate-quality.json",
        "matrix": "benchmark-matrix-toto2-controlled-covariate-quality.json",
        "events": (
            ("motor-01", "load_proxy", "dropout", 368, 372, "covariate"),
            ("motor-01", "load_proxy", "stale_value", 372, 376, "covariate"),
        ),
    },
}


class RecordingBackend:
    def __init__(self, equipment_id: str) -> None:
        self.equipment_id = equipment_id
        self.calls = []

    def forecast(self, variates, observed_mask, horizon, **kwargs):
        self.calls.append((variates, observed_mask, horizon, kwargs))
        point = [[float(index + lead) for lead in range(horizon)] for index in range(len(variates))]
        quantiles = [
            [[value + (level_index - 4) * 0.1 for value in row] for row in point]
            for level_index in range(len(OFFICIAL_QUANTILES))
        ]
        return BackendForecast(point, quantiles, OFFICIAL_QUANTILES)


def _overlaps(start: int, end: int, window_start: int, window_end: int) -> bool:
    return start < window_end and window_start < end


class ControlledScenarioTests(unittest.TestCase):
    def setUp(self) -> None:
        artifact_parent = ROOT / "artifacts"
        artifact_parent.mkdir(parents=True, exist_ok=True)
        self.temp_root = Path(tempfile.mkdtemp(prefix="t2c-", dir=artifact_parent))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_root, ignore_errors=True)

    def _relative(self, path: Path) -> str:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()

    def _write_config(self, name: str, config: dict) -> Path:
        path = self.temp_root / name
        path.write_text(json.dumps(config, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        return path

    def _generate(self, track: str, seed: int = 42) -> Path:
        config = load_json(ROOT / "examples/configs" / TRACKS[track]["generator"])
        config["seed"] = seed
        config["dataset_id"] = f"{config['dataset_id']}--seed-{seed}"
        config_path = self._write_config(f"g-{track}-{seed}.json", config)
        dataset = self.temp_root / f"d-{track}-{seed}"
        output = generate_synthetic(config_path, self._relative(dataset), ROOT)
        self.assertEqual(check_dataset(output, ROOT)["status"], "pass")
        return output

    def test_all_configs_and_windows_match_static_contract(self) -> None:
        generator_schema = load_json(ROOT / "schemas/synthetic-generator-config.schema.json")
        benchmark_schema = load_json(ROOT / "schemas/benchmark-run-config.schema.json")
        matrix_schema = load_json(ROOT / "schemas/benchmark-matrix-config.schema.json")
        benchmark = load_json(ROOT / "examples/configs/benchmark-toto2-controlled.json")
        validate(benchmark, benchmark_schema)
        self.assertEqual(benchmark["horizon"], 15)
        self.assertEqual(benchmark["context_length"], 64)
        self.assertEqual(benchmark["target_signal_ids"], ["motor_current", "motor_temperature"])
        self.assertEqual(benchmark["past_only_covariate_ids"], ["load_proxy"])
        self.assertEqual(benchmark["known_future_covariate_ids"], [])
        self.assertEqual(benchmark["max_validation_origins"], 1)
        self.assertEqual(benchmark["max_test_origins"], 1)
        self.assertEqual([model["name"] for model in benchmark["models"]], [
            "last-value", "seasonal-naive", "moving-average", "ewma", "holt-linear", "toto2",
        ])

        base_generator = None
        generator_ids = []
        matrix_ids = []
        matrix_outputs = []
        for track, definition in TRACKS.items():
            generator_path = ROOT / "examples/configs" / definition["generator"]
            matrix_path = ROOT / "examples/configs" / definition["matrix"]
            generator = load_json(generator_path)
            matrix = load_json(matrix_path)
            validate(generator, generator_schema)
            validate(matrix, matrix_schema)
            self.assertEqual(generator["sample_count"], 480)
            self.assertEqual(len(generator["events"]), len(definition["events"]))
            if base_generator is None:
                base_generator = generator
            else:
                self.assertEqual(generator["equipment"], base_generator["equipment"])
                self.assertEqual(generator["regimes"], base_generator["regimes"])
            self.assertGreaterEqual(len(matrix["axes"]["seeds"]), 5)
            self.assertEqual(tuple(matrix["axes"]["seeds"]), SEEDS)
            self.assertEqual(tuple(matrix["axes"]["horizons"]), HORIZONS)
            self.assertEqual(tuple(matrix["axes"]["context_lengths"]), CONTEXT_LENGTHS)
            self.assertLessEqual(len(generator["dataset_id"]), 16)
            self.assertLessEqual(len(matrix["matrix_id"]), 16)
            generator_ids.append(generator["dataset_id"])
            matrix_ids.append(matrix["matrix_id"])
            matrix_outputs.append(matrix["matrix_output_dir"])
            dataset_matrix_output = Path(matrix["dataset_output_root"]) / matrix["matrix_id"]
            benchmark_matrix_output = Path(matrix["benchmark_output_root"]) / matrix["matrix_id"]
            matrix_output = Path(matrix["matrix_output_dir"])
            outputs = (dataset_matrix_output, benchmark_matrix_output, matrix_output)
            self.assertEqual(len({path.as_posix() for path in outputs}), 3)
            for left_index, left in enumerate(outputs):
                for right in outputs[left_index + 1:]:
                    self.assertFalse(left == right or left in right.parents or right in left.parents)
            for horizon in HORIZONS:
                for context_length in CONTEXT_LENGTHS:
                    self.assertEqual(
                        _select_origins(384, 480, context_length, horizon, "test", benchmark),
                        (384,),
                    )

            for event, expected in zip(generator["events"], definition["events"]):
                equipment_id, signal_id, event_type, start, end, role = expected
                self.assertEqual((event["equipment_id"], event["signal_id"], event["event_type"], event["start_sample"], event["end_sample"]), expected[:5])
                self.assertEqual(SIGNALS[signal_id][2], "target" if role == "target" else "covariate")
                forecast_overlaps = [_overlaps(start, end, 384, 384 + horizon) for horizon in HORIZONS]
                context_overlaps = [_overlaps(start, end, 384 - context, 384) for context in CONTEXT_LENGTHS]
                if track == "target-fault":
                    self.assertEqual(forecast_overlaps, [True, True])
                    self.assertEqual(context_overlaps, [False, False])
                else:
                    self.assertEqual(forecast_overlaps, [False, False])
                    self.assertEqual(context_overlaps, [True, True])

        self.assertEqual(len(set(generator_ids)), 4)
        self.assertEqual(len(set(matrix_ids)), 4)
        self.assertEqual(len(set(matrix_outputs)), 4)

    def test_control_and_quality_forecast_actuals_are_byte_equivalent_and_valid(self) -> None:
        control_forecasts = {}
        for seed in SEEDS:
            control_dataset = self._generate("control", seed)
            quality_datasets = {
                track: self._generate(track, seed)
                for track in ("target-quality", "covariate-quality")
            }
            def target_actual(dataset: Path) -> bytes:
                manifest = load_json(dataset / "dataset-manifest.json")
                rows = [json.loads(line) for line in (dataset / manifest["data_path"]).read_text(encoding="utf-8").splitlines()]
                motor_rows = [row for row in rows if row["equipment_id"] == "motor-01"]
                payload = [
                    {signal_id: {"value": row["signals"][signal_id]["value"], "quality": row["quality"][signal_id]} for signal_id in ("motor_current", "motor_temperature")}
                    for row in motor_rows[384:414]
                ]
                for item in payload:
                    for signal in item.values():
                        self.assertIsNotNone(signal["value"])
                        self.assertTrue(math.isfinite(signal["value"]))
                        self.assertEqual(signal["quality"], "ok")
                return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")

            control_forecasts[seed] = target_actual(control_dataset)
            for track, dataset in quality_datasets.items():
                self.assertEqual(target_actual(dataset), control_forecasts[seed], track)

    def test_target_fault_is_generated_and_confined_to_forecast_window(self) -> None:
        def read_rows(dataset: Path) -> dict[str, list[dict]]:
            manifest = load_json(dataset / "dataset-manifest.json")
            rows = [json.loads(line) for line in (dataset / manifest["data_path"]).read_text(encoding="utf-8").splitlines()]
            result = {}
            for equipment_id in ("motor-01", "conveyor-01"):
                result[equipment_id] = [row for row in rows if row["equipment_id"] == equipment_id]
            return result

        for seed in SEEDS:
            with self.subTest(seed=seed):
                control = read_rows(self._generate("control", seed))
                fault = read_rows(self._generate("target-fault", seed))
                self.assertNotEqual(
                    [row["signals"]["motor_current"]["value"] for row in fault["motor-01"][388:396]],
                    [row["signals"]["motor_current"]["value"] for row in control["motor-01"][388:396]],
                )
                for equipment_id in ("motor-01", "conveyor-01"):
                    for index in range(384, 414):
                        for signal_id in ("motor_current", "motor_temperature"):
                            payload = fault[equipment_id][index]
                            self.assertEqual(payload["quality"][signal_id], "ok")
                            self.assertTrue(math.isfinite(payload["signals"][signal_id]["value"]))
                for index in range(480):
                    if not 388 <= index < 396:
                        self.assertEqual(
                            fault["motor-01"][index]["signals"]["motor_current"],
                            control["motor-01"][index]["signals"]["motor_current"],
                        )
                for index in range(384, 414):
                    for signal_id in ("motor_current", "motor_temperature"):
                        self.assertEqual(
                            fault["conveyor-01"][index]["signals"][signal_id],
                            control["conveyor-01"][index]["signals"][signal_id],
                        )

    def test_generator_to_adapter_quality_masks_cover_horizons_and_contexts(self) -> None:
        for track, affected_indices in (("target-quality", (0, 1)), ("covariate-quality", (2,))):
            dataset = self._generate(track)
            manifest = load_json(dataset / "dataset-manifest.json")
            rows = [json.loads(line) for line in (dataset / manifest["data_path"]).read_text(encoding="utf-8").splitlines()]
            motor_rows = [row for row in rows if row["equipment_id"] == "motor-01"]
            signals = {
                f"motor-01.{signal_id}": {
                    "signal_id": f"motor-01.{signal_id}",
                    "name": signal_id,
                    "unit": SIGNALS[signal_id][1],
                    "sampling_interval_ms": 1000,
                    "role": SIGNALS[signal_id][2],
                }
                for signal_id in SIGNALS
            }
            for horizon in HORIZONS:
                for context_length in CONTEXT_LENGTHS:
                    with self.subTest(track=track, horizon=horizon, context_length=context_length):
                        backend = RecordingBackend("motor-01")
                        request = _make_request(
                            motor_rows,
                            signals,
                            ("motor-01.motor_current", "motor-01.motor_temperature"),
                            384,
                            context_length,
                            horizon,
                            past_only_ids=("motor-01.load_proxy",),
                        )
                        result = Toto2Adapter(
                            load_json(ROOT / "examples/manifests/model-license-toto2.json"),
                            backend=backend,
                        ).forecast(request)
                        self.assertEqual(len(result.forecasts), 2)
                        self.assertTrue(all(len(forecast.point_forecast) == horizon for forecast in result.forecasts))
                        self.assertTrue(all(math.isfinite(value) for forecast in result.forecasts for value in forecast.point_forecast))
                        variates, masks, called_horizon, kwargs = backend.calls[0]
                        self.assertEqual(called_horizon, horizon)
                        padding = (-context_length) % 32
                        self.assertEqual(len(variates), 3)
                        self.assertEqual(len(variates[0]), context_length + padding)
                        for values, mask in zip(variates, masks):
                            self.assertEqual(values[:padding], (0.0,) * padding)
                            self.assertEqual(mask[:padding], (False,) * padding)
                        expected_false = {index: set() for index in range(3)}
                        event_position = 368 - (384 - context_length)
                        if track == "target-quality":
                            expected_false[0].update(range(padding + event_position, padding + event_position + 4))
                            expected_false[1].update(range(padding + event_position + 4, padding + event_position + 8))
                        else:
                            expected_false[2].update(range(padding + event_position, padding + event_position + 8))
                        for variate_index, (values, mask) in enumerate(zip(variates, masks)):
                            for position, observed in enumerate(mask):
                                expected_observed = position >= padding and position not in expected_false[variate_index]
                                self.assertEqual(observed, expected_observed)
                                if not observed:
                                    self.assertEqual(values[position], 0.0)
                        self.assertTrue(kwargs["has_missing_values"])

    def test_fake_toto_pipeline_masks_quality_and_preserves_prediction_completeness(self) -> None:
        for track, expected_false_index in (("target-quality", (0, 1)), ("covariate-quality", (2,))):
            with self.subTest(track=track):
                dataset = self._generate(track)
                benchmark = load_json(ROOT / "examples/configs/benchmark-toto2-controlled.json")
                benchmark["dataset_path"] = self._relative(dataset)
                benchmark["output_dir"] = self._relative(self.temp_root / f"b-{track}")
                config_path = self._write_config(f"b-{track}.json", benchmark)
                backends = {}
                def factory(equipment_id, _parameters):
                    backend = RecordingBackend(equipment_id)
                    backends[equipment_id] = backend
                    return Toto2Adapter(
                        load_json(ROOT / "examples/manifests/model-license-toto2.json"), backend=backend
                    )
                registry = ModelRegistry({
                    "toto2": factory
                })
                output = run_benchmark(config_path, ROOT, registry)
                result = load_json(output / "result.json")
                self.assertEqual(result["status"], "success")
                predictions = [json.loads(line) for line in (output / "predictions.jsonl").read_text(encoding="utf-8").splitlines()]
                toto_predictions = [item for item in predictions if item["model"] == "toto2"]
                self.assertEqual(len(toto_predictions), 2 * 2 * 15)
                self.assertEqual(result["metrics"]["by_model"]["toto2"]["count"], 60)
                motor_backend = backends["motor-01"]
                self.assertTrue(motor_backend.calls)
                motor_call = next(call for call in motor_backend.calls if any(any(not value for value in mask) for mask in call[1]))
                variates, masks, horizon, kwargs = motor_call
                self.assertEqual(horizon, 15)
                self.assertTrue(kwargs["has_missing_values"])
                false_spans = {0: (48, 52), 1: (52, 56), 2: (48, 56)}
                for variate_index in range(3):
                    expected_missing = variate_index in expected_false_index
                    self.assertEqual(any(not value for value in masks[variate_index]), expected_missing)
                    if expected_missing:
                        start, end = false_spans[variate_index]
                        self.assertEqual(variates[variate_index][start:end], (0.0,) * (end - start))
                        self.assertEqual(masks[variate_index][start:end], (False,) * (end - start))

                manifest = load_json(dataset / "dataset-manifest.json")
                rows = [json.loads(line) for line in (dataset / manifest["data_path"]).read_text(encoding="utf-8").splitlines()]
                motor_rows = [row for row in rows if row["equipment_id"] == "motor-01"]
                signals = {f"motor-01.{signal_id}": {"signal_id": f"motor-01.{signal_id}", "name": signal_id, "unit": SIGNALS[signal_id][1], "sampling_interval_ms": 1000, "role": SIGNALS[signal_id][2]} for signal_id in SIGNALS}
                request = _make_request(motor_rows, signals, ("motor-01.motor_current", "motor-01.motor_temperature"), 384, 64, 15, past_only_ids=("motor-01.load_proxy",))
                non_ok = {
                    signal_id: sum(point.quality_status.value != "ok" for point in next(series for series in request.contexts if series.metadata.signal_id == signal_id).points)
                    for signal_id in request.target_signal_ids + ("motor-01.load_proxy",)
                }
                self.assertEqual(non_ok, {"motor-01.motor_current": 4 if track == "target-quality" else 0, "motor-01.motor_temperature": 4 if track == "target-quality" else 0, "motor-01.load_proxy": 8 if track == "covariate-quality" else 0})
                for signal_id, excluded_count in non_ok.items():
                    self.assertEqual(len(_finite_history(request, signal_id)), 64 - excluded_count)


if __name__ == "__main__":
    unittest.main()
