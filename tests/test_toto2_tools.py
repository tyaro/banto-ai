from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from tools import toto2
from tools.toto2 import preflight, run_benchmark, run_matrix, run_smoke
from banto_ai.adapters.toto2 import BackendForecast, OFFICIAL_QUANTILES, Toto2Adapter
from banto_ai.benchmark import _select_origins
from banto_ai.generator import generate_synthetic
from banto_ai.manifest import load_json, validate
from banto_ai.matrix import MatrixError, expand_cells


ROOT = Path(__file__).resolve().parents[1]


class Toto2ToolTests(unittest.TestCase):
    def test_preflight_is_cpu_offline_and_external_cache_only(self):
        with tempfile.TemporaryDirectory() as directory:
            report = preflight.collect_preflight(Path(directory), python_version=(3, 14, 0), total_ram_bytes=8 * 1024**3, available_disk_bytes=4 * 1024**3, optional_packages={})
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["evaluation"]["decode_block_size"], None)
        self.assertEqual(report["checkpoint"]["model_size_bytes"], 16582848)

    def test_environment_contexts_restore_caller_values(self):
        names = ("HF_HUB_OFFLINE", "HF_HOME")
        original = {name: os.environ.get(name) for name in names}
        try:
            with tempfile.TemporaryDirectory() as directory:
                os.environ["HF_HUB_OFFLINE"] = "caller"
                with toto2.offline_environment(), toto2.cache_environment(Path(directory)):
                    self.assertEqual(os.environ["HF_HUB_OFFLINE"], "1")
                    self.assertEqual(os.environ["HF_HOME"], str(Path(directory).resolve()))
                self.assertEqual(os.environ["HF_HUB_OFFLINE"], "caller")
        finally:
            for name, value in original.items():
                if value is None: os.environ.pop(name, None)
                else: os.environ[name] = value

    def test_smoke_case_preserves_metropt_like_contract(self):
        request, _ = run_smoke.build_smoke_case()
        self.assertEqual(len(request.contexts[0].points), 120)
        self.assertEqual(request.horizon, 15)
        self.assertEqual(request.target_signal_ids, ("motor_current", "oil_temperature"))
        self.assertEqual([s.metadata.signal_id for s in request.known_future_covariates], [])

    def test_shared_factory_rejects_unknown_or_invalid_toto_parameters(self):
        with tempfile.TemporaryDirectory() as directory:
            factory = run_benchmark.make_shared_toto_factory(toto2.load_manifest(), Path(directory))
            invalid_parameters = (
                {"unknown": True},
                {"device": "cuda"},
                {"batch_size": 2},
                {"local_files_only": False},
                {"patch_size": 16},
                {"checkpoint_revision": "0" * 40},
            )
            for parameters in invalid_parameters:
                with self.subTest(parameters=parameters):
                    with self.assertRaises(ValueError):
                        factory("metropt3-apu-01", parameters)

    def test_all_toto_entrypoints_import_from_repository_and_external_cwd(self):
        scripts = tuple(ROOT / "tools" / "toto2" / name for name in ("preflight.py", "prepare_checkpoint.py", "run_smoke.py", "run_benchmark.py", "run_matrix.py", "analyze_controlled_acceptance.py"))
        environment = dict(os.environ)
        environment.pop("PYTHONPATH", None)
        with tempfile.TemporaryDirectory() as external_cwd:
            for script in scripts:
                with self.subTest(cwd="repository", script=script.name):
                    completed = subprocess.run([sys.executable, script.relative_to(ROOT).as_posix(), "--help"], cwd=ROOT, env=environment, capture_output=True, text=True)
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    self.assertNotIn("ModuleNotFoundError", completed.stderr)
                    if script.name == "analyze_controlled_acceptance.py":
                        self.assertIn("--recover-incomplete", completed.stdout)
                with self.subTest(cwd="external", script=script.name):
                    completed = subprocess.run([sys.executable, str(script), "--help"], cwd=external_cwd, env=environment, capture_output=True, text=True)
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    self.assertNotIn("ModuleNotFoundError", completed.stderr)

    def test_prepare_cli_acceptance_gate_reaches_mock_without_download(self):
        with tempfile.TemporaryDirectory() as cache_dir, tempfile.TemporaryDirectory() as external_cwd:
            code = (
                "import json, sys\n"
                "from unittest.mock import patch\n"
                "import tools.toto2.prepare_checkpoint as target\n"
                "def fake(cache, manifest, *, accepted):\n"
                "    print(json.dumps({'cache': str(cache), 'accepted': accepted}))\n"
                "    return {'status': 'mocked-no-download'}\n"
                "with patch.object(target, 'prepare_checkpoint', fake):\n"
                "    raise SystemExit(target.main(sys.argv[1:]))\n"
            )
            environment = dict(os.environ)
            environment["PYTHONPATH"] = os.pathsep.join((str(ROOT), str(ROOT / "src")))
            completed = subprocess.run([sys.executable, "-c", code, "--cache-dir", cache_dir, "--accept-apache-2.0"], cwd=external_cwd, env=environment, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn('"accepted": true', completed.stdout)
        self.assertIn("mocked-no-download", completed.stdout)
        self.assertNotIn("AttributeError", completed.stderr)

    def test_smoke_publishes_with_deterministic_fake_backend(self):
        class FakeBackend:
            def forecast(self, variates, observed_mask, horizon, **kwargs):
                point = [[float(index + 1) for _ in range(horizon)] for index in range(len(variates))]
                quantiles = [[[value + (level_index - 4) for value in row] for row in point] for level_index in range(9)]
                return BackendForecast(point, quantiles, OFFICIAL_QUANTILES)
        with tempfile.TemporaryDirectory() as cache_dir:
            artifacts = ROOT / "artifacts"
            artifacts.mkdir(exist_ok=True)
            with tempfile.TemporaryDirectory(dir=artifacts) as output_dir:
                output = Path(output_dir) / "smoke.json"
                factory = lambda manifest, config: Toto2Adapter(manifest, config=config, backend=FakeBackend())
                with patch.object(run_smoke, "_verify_installed_package"):
                    payload = run_smoke.run_smoke(Path(cache_dir), output, adapter_factory=factory, skip_checkpoint_verification=True)
                self.assertEqual(payload["status"], "pass")
                self.assertEqual(payload["input"]["effective_model_input_length"], 128)
                self.assertEqual(payload["model"]["provenance"]["verification_status"], "skipped-test-only")

    def test_small_matrix_configs_cover_eight_cells_and_synthetic_data(self):
        matrix = load_json(ROOT / "examples/configs/benchmark-matrix-toto2-small.json")
        validate(matrix, load_json(ROOT / "schemas/benchmark-matrix-config.schema.json"))
        self.assertEqual(
            expand_cells(matrix),
            (
                (17, 15, 64), (17, 15, 120), (17, 30, 64), (17, 30, 120),
                (42, 15, 64), (42, 15, 120), (42, 30, 64), (42, 30, 120),
            ),
        )
        generator_config = load_json(ROOT / matrix["generator_config_path"])
        validate(
            generator_config,
            load_json(ROOT / "schemas/synthetic-generator-config.schema.json"),
        )
        regimes = generator_config["regimes"]
        self.assertEqual((regimes[0]["start_sample"], regimes[-1]["end_sample"]), (0, 480))
        self.assertTrue(all(left["end_sample"] == right["start_sample"] for left, right in zip(regimes, regimes[1:])))
        benchmark_config = load_json(ROOT / matrix["benchmark_config_path"])
        validate(
            benchmark_config,
            load_json(ROOT / "schemas/benchmark-run-config.schema.json"),
        )
        self.assertEqual(benchmark_config["known_future_covariate_ids"], [])
        self.assertEqual([model["name"] for model in benchmark_config["models"]].count("toto2"), 1)

        artifacts = ROOT / "artifacts"
        artifacts.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=artifacts) as directory:
            output = generate_synthetic(
                ROOT / matrix["generator_config_path"], Path(directory) / "dataset", ROOT
            )
            summary = load_json(output / "summary.json")
            rows_by_equipment = {}
            with (output / "observations.jsonl").open(encoding="utf-8") as handle:
                for line in handle:
                    row = json.loads(line)
                    rows_by_equipment.setdefault(row["equipment_id"], []).append(row)
        self.assertEqual(summary["sample_count_per_equipment"], 480)
        self.assertEqual(summary["equipment_count"], 2)
        self.assertEqual(summary["observation_record_count"], 960)
        self.assertEqual(summary["configured_event_count"], 12)
        self.assertEqual(summary["disabled_event_count"], 1)
        self.assertEqual(summary["event_count"], 11)
        self.assertEqual(set(summary["regime_coverage"].values()), {80})
        self.assertEqual(summary["event_coverage"]["stuck_value"], 1)
        self.assertEqual(
            {event_type: count for event_type, count in summary["event_coverage"].items() if event_type not in ("stuck_value", "stale_value")},
            {"sensor_drift": 2, "spike": 2, "dropout": 2, "overheating_trend": 2, "jam_or_slip": 2},
        )
        self.assertEqual(summary["event_coverage"]["stale_value"], 0)
        expected_origins = {
            ("validation", 15): (288, 363),
            ("validation", 30): (288, 348),
            ("test", 15): (384, 459),
            ("test", 30): (384, 444),
        }
        for horizon in (15, 30):
            for context_length in (64, 120):
                for split_name, (start, end) in (("validation", (288, 384)), ("test", (384, 480))):
                    origins = _select_origins(
                        start, end, context_length, horizon, split_name, benchmark_config
                    )
                    self.assertEqual(origins, expected_origins[(split_name, horizon)])
                    for rows in rows_by_equipment.values():
                        for origin in origins:
                            selected = rows[origin - context_length:origin + horizon]
                            for row in selected:
                                for signal_id in ("motor_current", "motor_temperature", "load_proxy"):
                                    self.assertIsNotNone(row["signals"][signal_id]["value"])

    def test_matrix_wrapper_reuses_single_run_guards_and_shared_factory(self):
        matrix_config = Path("examples/configs/benchmark-matrix-toto2-small.json")
        with tempfile.TemporaryDirectory() as cache_dir:
            captured = {}
            shared_factory = lambda _equipment_id, _parameters: object()

            def fake_runner(config_path, root, registry):
                captured["config_path"] = config_path
                captured["root"] = root
                captured["registry"] = registry
                captured["cells"] = expand_cells(load_json(config_path))
                return ROOT / "artifacts" / "toto2" / "matrix" / "fake-result"

            tracked_names = (
                "HF_HUB_OFFLINE", "HF_HUB_DISABLE_TELEMETRY", "TRANSFORMERS_OFFLINE",
                "DO_NOT_TRACK", "HF_HOME", "HF_HUB_CACHE", "TRANSFORMERS_CACHE",
            )
            original = {name: os.environ.get(name) for name in tracked_names}
            try:
                os.environ["HF_HUB_OFFLINE"] = "caller-offline"
                os.environ["HF_HOME"] = "caller-home"
                with patch.object(run_matrix.single_run, "_external_cache", return_value=Path(cache_dir)) as external_cache, \
                    patch.object(run_matrix.single_run, "_load_and_validate_license", return_value={"allowed_use": "commercial-evaluation"}) as load_license, \
                    patch.object(run_matrix.single_run, "_verify_cached_checkpoint") as verify_checkpoint, \
                    patch.object(run_matrix.single_run, "_verify_installed_package") as verify_package, \
                    patch.object(run_matrix.single_run, "make_shared_toto_factory", return_value=shared_factory) as make_factory:
                    output = run_matrix.run_toto2_matrix(
                        matrix_config, ROOT, Path(cache_dir),
                        matrix_runner=fake_runner,
                    )
            finally:
                for name, value in original.items():
                    if value is None:
                        os.environ.pop(name, None)
                    else:
                        os.environ[name] = value

            self.assertEqual(output, ROOT / "artifacts" / "toto2" / "matrix" / "fake-result")
            self.assertEqual(captured["config_path"], ROOT / matrix_config)
            self.assertEqual(captured["root"], ROOT.resolve())
            self.assertEqual(len(captured["cells"]), 8)
            self.assertIs(captured["registry"]._factories["toto2"], shared_factory)
            external_cache.assert_called_once_with(Path(cache_dir), must_exist=True)
            load_license.assert_called_once_with(run_matrix.MANIFEST_PATH)
            verify_checkpoint.assert_called_once_with(Path(cache_dir))
            verify_package.assert_called_once_with()
            make_factory.assert_called_once_with(
                {"allowed_use": "commercial-evaluation"}, Path(cache_dir)
            )
            self.assertEqual(os.environ.get("HF_HUB_OFFLINE"), original["HF_HUB_OFFLINE"])
            self.assertEqual(os.environ.get("HF_HOME"), original["HF_HOME"])

    def test_matrix_wrapper_rejects_toto_contract_before_external_cache(self):
        matrix = load_json(ROOT / "examples/configs/benchmark-matrix-toto2-small.json")
        benchmark = load_json(ROOT / matrix["benchmark_config_path"])
        artifacts = ROOT / "artifacts"
        artifacts.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=artifacts) as directory:
            control = Path(directory)
            benchmark_path = control / "benchmark.json"
            matrix_path = control / "matrix.json"
            benchmark["known_future_covariate_ids"] = ["future_signal"]
            benchmark_path.write_text(json.dumps(benchmark), encoding="utf-8")
            matrix["benchmark_config_path"] = benchmark_path.relative_to(ROOT).as_posix()
            matrix["dataset_output_root"] = f"artifacts/toto2/test-{uuid4().hex}/datasets"
            matrix["benchmark_output_root"] = f"artifacts/toto2/test-{uuid4().hex}/benchmarks"
            matrix["matrix_output_dir"] = f"artifacts/toto2/test-{uuid4().hex}/matrix"
            matrix_path.write_text(json.dumps(matrix), encoding="utf-8")
            with patch.object(run_matrix.single_run, "_external_cache") as external_cache:
                with self.assertRaises(MatrixError):
                    run_matrix.run_toto2_matrix(matrix_path.relative_to(ROOT), ROOT, Path("C:/outside/cache"))
            external_cache.assert_not_called()

    def test_matrix_wrapper_rejects_invalid_generator_before_external_cache(self):
        matrix = load_json(ROOT / "examples/configs/benchmark-matrix-toto2-small.json")
        generator = load_json(ROOT / matrix["generator_config_path"])
        artifacts = ROOT / "artifacts"
        artifacts.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=artifacts) as directory:
            control = Path(directory)
            generator["sample_count"] = 0
            generator_path = control / "generator.json"
            matrix_path = control / "matrix.json"
            generator_path.write_text(json.dumps(generator), encoding="utf-8")
            matrix["generator_config_path"] = generator_path.relative_to(ROOT).as_posix()
            matrix["dataset_output_root"] = f"artifacts/toto2/test-{uuid4().hex}/datasets"
            matrix["benchmark_output_root"] = f"artifacts/toto2/test-{uuid4().hex}/benchmarks"
            matrix["matrix_output_dir"] = f"artifacts/toto2/test-{uuid4().hex}/matrix"
            matrix_path.write_text(json.dumps(matrix), encoding="utf-8")
            with patch.object(run_matrix.single_run, "_external_cache") as external_cache:
                with self.assertRaises(MatrixError):
                    run_matrix.run_toto2_matrix(matrix_path.relative_to(ROOT), ROOT, Path("C:/outside/cache"))
            external_cache.assert_not_called()

    def test_matrix_wrapper_rejects_invalid_inputs_before_external_cache_table(self):
        base_matrix = load_json(ROOT / "examples/configs/benchmark-matrix-toto2-small.json")
        base_benchmark = load_json(ROOT / base_matrix["benchmark_config_path"])
        artifacts = ROOT / "artifacts"
        artifacts.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=artifacts) as directory:
            control = Path(directory)
            cases = []

            cases.append(
                (
                    "absolute config path",
                    ROOT / "examples/configs/benchmark-matrix-toto2-small.json",
                )
            )
            for label, field, value in (
                ("generator traversal", "generator_config_path", "../outside.json"),
                ("generator backslash", "generator_config_path", "examples\\configs\\synthetic-motor-toto2-matrix.json"),
                ("benchmark drive path", "benchmark_config_path", "C:/outside.json"),
                ("matrix output traversal", "matrix_output_dir", "../outside"),
            ):
                invalid_matrix = dict(base_matrix)
                invalid_matrix[field] = value
                path = control / f"{label.replace(' ', '-')}.json"
                path.write_text(json.dumps(invalid_matrix), encoding="utf-8")
                cases.append((label, path))

            model_cases = (
                ("model missing", lambda benchmark: benchmark.update(models=[])),
                (
                    "model duplicate",
                    lambda benchmark: benchmark["models"].append(
                        dict(next(model for model in benchmark["models"] if model["name"] == "toto2"))
                    ),
                ),
                (
                    "non-native policy",
                    lambda benchmark: next(model for model in benchmark["models"] if model["name"] == "toto2").update(
                        quantile_policy="validation-residual-by-lead"
                    ),
                ),
                (
                    "revision mismatch",
                    lambda benchmark: next(model for model in benchmark["models"] if model["name"] == "toto2")["parameters"].update(
                        checkpoint_revision="0" * 40
                    ),
                ),
                (
                    "device mismatch",
                    lambda benchmark: next(model for model in benchmark["models"] if model["name"] == "toto2")["parameters"].update(
                        device="cuda"
                    ),
                ),
                (
                    "batch mismatch",
                    lambda benchmark: next(model for model in benchmark["models"] if model["name"] == "toto2")["parameters"].update(
                        batch_size=2
                    ),
                ),
                (
                    "batch bool",
                    lambda benchmark: next(model for model in benchmark["models"] if model["name"] == "toto2")["parameters"].update(
                        batch_size=True
                    ),
                ),
                (
                    "local files disabled",
                    lambda benchmark: next(model for model in benchmark["models"] if model["name"] == "toto2")["parameters"].update(
                        local_files_only=False
                    ),
                ),
                (
                    "patch mismatch",
                    lambda benchmark: next(model for model in benchmark["models"] if model["name"] == "toto2")["parameters"].update(
                        patch_size=16
                    ),
                ),
            )
            for label, mutate in model_cases:
                benchmark = json.loads(json.dumps(base_benchmark))
                mutate(benchmark)
                benchmark_path = control / f"{label.replace(' ', '-')}-benchmark.json"
                matrix_path = control / f"{label.replace(' ', '-')}-matrix.json"
                benchmark_path.write_text(json.dumps(benchmark), encoding="utf-8")
                matrix = dict(base_matrix)
                matrix["benchmark_config_path"] = benchmark_path.relative_to(ROOT).as_posix()
                matrix_path.write_text(json.dumps(matrix), encoding="utf-8")
                cases.append((label, matrix_path))

            context_matrix = dict(base_matrix)
            context_matrix["axes"] = dict(base_matrix["axes"])
            context_matrix["axes"]["context_lengths"] = [31]
            context_path = control / "context-length-below-toto-minimum.json"
            context_path.write_text(json.dumps(context_matrix), encoding="utf-8")
            cases.append(("context length below Toto minimum", context_path))

            for label, config_path in cases:
                with self.subTest(case=label):
                    with patch.object(run_matrix.single_run, "_external_cache") as external_cache:
                        with self.assertRaises(MatrixError):
                            run_matrix.run_toto2_matrix(
                                config_path, ROOT, Path("C:/outside/cache")
                            )
                    external_cache.assert_not_called()

    def test_matrix_module_import_does_not_load_heavy_backend(self):
        code = (
            "import sys; import tools.toto2.run_matrix; "
            "print(sorted(set(sys.modules) & {'torch', 'numpy', 'toto2', 'huggingface_hub'}))"
        )
        environment = dict(os.environ)
        environment["PYTHONPATH"] = os.pathsep.join((str(ROOT), str(ROOT / "src")))
        completed = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "[]")


if __name__ == "__main__":
    unittest.main()
