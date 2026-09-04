"""Chronos-2 tool boundary tests; no network, checkpoint, or ML package required."""

from __future__ import annotations

import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from banto_ai.adapters.chronos2 import BackendForecast, Chronos2Adapter, Chronos2Config  # noqa: E402
from banto_ai.manifest import load_json as load_json_file, validate  # noqa: E402
from tools.chronos2 import (  # noqa: E402
    CHECKPOINT_ALLOW_PATTERNS,
    DEFAULT_REVISION,
    OFFICIAL_CHECKPOINT,
    external_cache,
    load_manifest,
    offline_environment,
    verify_snapshot,
)
from tools.chronos2 import prepare_checkpoint, run_benchmark, run_matrix, run_smoke  # noqa: E402
import tools.chronos2 as chronos_tools  # noqa: E402
from tools.chronos2 import preflight  # noqa: E402


MANIFEST = ROOT / "examples" / "manifests" / "model-license-chronos2.json"


class FakeHub:
    def __init__(self, snapshot: Path) -> None:
        self.snapshot = snapshot
        self.kwargs: dict[str, object] | None = None

    def snapshot_download(self, **kwargs: object) -> str:
        self.kwargs = kwargs
        self.xet_disabled = os.environ.get("HF_HUB_DISABLE_XET")
        return str(self.snapshot)


class FakeChronosBackend:
    def forecast(self, targets, past_covariates, future_covariates, horizon, quantiles, **kwargs):
        if set(past_covariates) != {"speed", "planned_load"}:
            raise AssertionError(f"unexpected past covariates: {past_covariates}")
        if set(future_covariates) != {"planned_load"} or len(future_covariates["planned_load"]) != horizon:
            raise AssertionError(f"unexpected future covariates: {future_covariates}")
        points = [[float(row[-1]) + step for step in range(1, horizon + 1)] for row in targets]
        tensor = [[[value - 1.0, value, value + 1.0] for value in row] for row in points]
        return BackendForecast(points, tensor, tuple(quantiles))


class Chronos2ToolTests(unittest.TestCase):
    def test_accept_gate_rejects_before_cache_or_hub(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "chronos2"
            with patch.object(prepare_checkpoint.importlib, "import_module") as importer:
                with self.assertRaisesRegex(ValueError, "accept-apache-2.0"):
                    prepare_checkpoint.prepare_checkpoint(target, MANIFEST, accepted=False)
            self.assertFalse(target.exists())
            importer.assert_not_called()

    def test_external_cache_rejects_repository_path(self):
        with self.assertRaisesRegex(ValueError, "outside"):
            external_cache(ROOT / "artifacts" / "chronos2")

    def test_manifest_and_provenance_are_fixed(self):
        manifest = load_manifest(MANIFEST)
        self.assertEqual(manifest["allowed_use"], "commercial-evaluation")
        self.assertEqual(manifest["checkpoint"], OFFICIAL_CHECKPOINT)
        self.assertEqual(manifest["checkpoint_revision"], DEFAULT_REVISION)
        provenance = json.loads((ROOT / "environments" / "chronos2" / "package-provenance.json").read_text(encoding="utf-8"))
        self.assertEqual(provenance["package_version"], "2.3.1")
        self.assertEqual(provenance["package_sha256"], "d9d00ec9b1621235bfb26685638bf054885f4c000863678f1c775dfab2697496")
        self.assertEqual(provenance["checkpoint_allow_patterns"], list(CHECKPOINT_ALLOW_PATTERNS))
        self.assertEqual(provenance["transitive_lock_status"], "verified")
        self.assertEqual(provenance["lock_scope"], "fully-resolved-pip-freeze-without-hashes")
        self.assertEqual(provenance["transitive_lock_file"], "requirements-windows-cpu-py314.lock")

    def test_environment_metadata_has_no_machine_specific_validation_path(self):
        environment = ROOT / "environments" / "chronos2"
        absolute_windows_path = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z]:\\")
        readme_lines = (environment / "README.md").read_text(encoding="utf-8").splitlines()
        readme_lock_source = next(
            line for line in readme_lines
            if "requirements-windows-cpu-py314.lock" in line and "pip freeze" in line
        )
        lock_source = (environment / "requirements-windows-cpu-py314.lock").read_text(
            encoding="utf-8"
        ).splitlines()[0]
        provenance = json.loads(
            (environment / "package-provenance.json").read_text(encoding="utf-8")
        )
        validation_sources = {
            "readme_lock_source": readme_lock_source,
            "lock_header": lock_source,
            "provenance_reason": provenance["transitive_lock_reason"],
        }
        for source, text in validation_sources.items():
            with self.subTest(source=source):
                self.assertIsNone(absolute_windows_path.search(text))

    def test_manifest_requires_exact_verified_at(self):
        manifest = dict(load_manifest(MANIFEST))
        manifest.pop("verified_at")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "verified_at"):
                load_manifest(path)

    def test_prepare_uses_fixed_download_arguments_and_verifies_artifact(self):
        content = b"small deterministic test artifact"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = root / "cache" / "snapshots" / DEFAULT_REVISION
            snapshot.mkdir(parents=True)
            for name in CHECKPOINT_ALLOW_PATTERNS:
                (snapshot / name).write_bytes(content if name == "model.safetensors" else name.encode())
            hub = FakeHub(snapshot)
            with patch.object(prepare_checkpoint, "load_checkpoint_provenance", return_value={"package_sha256": "pkg"}), patch.object(prepare_checkpoint, "EXPECTED_MODEL_SIZE_BYTES", len(content)), patch.object(prepare_checkpoint, "EXPECTED_MODEL_SHA256", hashlib.sha256(content).hexdigest()), patch.object(prepare_checkpoint.importlib, "import_module", return_value=hub):
                result = prepare_checkpoint.prepare_checkpoint(root / "cache", MANIFEST, accepted=True)
            self.assertEqual(hub.kwargs, {
                "repo_id": OFFICIAL_CHECKPOINT,
                "revision": DEFAULT_REVISION,
                "cache_dir": str((root / "cache").resolve()),
                "allow_patterns": list(CHECKPOINT_ALLOW_PATTERNS),
                "local_files_only": False,
                "max_workers": 1,
            })
            self.assertEqual(hub.xet_disabled, "1")
            self.assertEqual(result["model_artifact"]["size_bytes"], len(content))
            self.assertEqual(result["model_artifact"]["sha256"], hashlib.sha256(content).hexdigest())

    def test_verify_snapshot_checks_actual_size_and_hash(self):
        content = b"hash checked"
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory) / DEFAULT_REVISION
            snapshot.mkdir()
            for name in CHECKPOINT_ALLOW_PATTERNS:
                (snapshot / name).write_bytes(content if name == "model.safetensors" else b"metadata")
            with patch("tools.chronos2.EXPECTED_MODEL_SIZE_BYTES", len(content)), patch("tools.chronos2.EXPECTED_MODEL_SHA256", hashlib.sha256(content).hexdigest()):
                artifact = verify_snapshot(snapshot)
            self.assertEqual(artifact["size_bytes"], len(content))
            self.assertEqual(artifact["sha256"], hashlib.sha256(content).hexdigest())

    def test_offline_environment_restores_existing_values(self):
        with patch.dict("os.environ", {"HF_HUB_OFFLINE": "old", "HF_HUB_DISABLE_TELEMETRY": "old-telemetry"}, clear=False):
            with offline_environment():
                self.assertEqual(__import__("os").environ["HF_HUB_OFFLINE"], "1")
                self.assertEqual(__import__("os").environ["HF_HUB_DISABLE_TELEMETRY"], "1")
            self.assertEqual(__import__("os").environ["HF_HUB_OFFLINE"], "old")
            self.assertEqual(__import__("os").environ["HF_HUB_DISABLE_TELEMETRY"], "old-telemetry")

    def test_preflight_cache_check_requires_external_directory_candidate(self):
        report = preflight.collect_preflight(
            ROOT / "artifacts" / "repo-cache",
            total_ram_bytes=preflight.MIN_RAM_BYTES,
            available_disk_bytes=preflight.MIN_DISK_BYTES,
            optional_packages={},
        )
        self.assertFalse(report["checks"]["cache"]["ok"])
        self.assertFalse(report["checks"]["cache"]["path_outside_repository"])
        with tempfile.TemporaryDirectory() as directory:
            file_path = Path(directory) / "cache-file"
            file_path.write_text("not a directory", encoding="utf-8")
            report = preflight.collect_preflight(
                file_path,
                total_ram_bytes=preflight.MIN_RAM_BYTES,
                available_disk_bytes=preflight.MIN_DISK_BYTES,
                optional_packages={},
            )
        self.assertFalse(report["checks"]["cache"]["ok"])
        self.assertTrue(report["checks"]["cache"]["path_outside_repository"])
        self.assertFalse(report["checks"]["cache"]["directory_ok"])

    def test_shared_factory_and_native_policy(self):
        class FakeConfig:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        class FakeAdapter:
            def __init__(self, manifest, config):
                self.config = config

        with patch.object(run_benchmark, "Chronos2Adapter", FakeAdapter), patch.object(run_benchmark, "Chronos2Config", FakeConfig):
            with tempfile.TemporaryDirectory() as directory:
                factory = run_benchmark.make_shared_chronos_factory(load_manifest(MANIFEST), Path(directory))
                first = factory("motor-01", {"device_map": "cpu", "local_files_only": True, "cross_learning": False})
                second = factory("motor-02", {"device_map": "cpu", "local_files_only": True, "cross_learning": False})
        self.assertIs(first, second)
        with self.assertRaisesRegex(ValueError, "unsupported"):
            run_benchmark.run_chronos_benchmark  # keep public runner discoverable
            # Factory validation is intentionally before any model construction.
            with tempfile.TemporaryDirectory() as directory:
                factory = run_benchmark.make_shared_chronos_factory(load_manifest(MANIFEST), Path(directory))
                factory("motor-01", {"device_map": "cpu", "local_files_only": True, "quantile_policy": "p50-calibration"})

    def test_metropt3_config_reaches_validated_chronos_wrapper_settings(self):
        config = load_json_file(ROOT / "examples" / "configs" / "benchmark-metropt3-chronos2.json")
        chronos = next(model for model in config["models"] if model["name"] == "chronos2")

        class FakeAdapter:
            def __init__(self, manifest, config):
                self.manifest = manifest
                self.config = config

        with patch.object(run_benchmark, "Chronos2Adapter", FakeAdapter):
            with tempfile.TemporaryDirectory() as directory:
                adapter = run_benchmark.make_shared_chronos_factory(
                    load_manifest(MANIFEST), Path(directory)
                )("metropt3-apu-01", chronos["parameters"])

        self.assertIsInstance(adapter.config, Chronos2Config)
        self.assertEqual(adapter.config.checkpoint_revision, DEFAULT_REVISION)
        self.assertEqual(adapter.config.cache_dir, str(Path(directory).resolve()))
        self.assertEqual(adapter.config.context_length, config["context_length"])
        self.assertEqual(adapter.config.batch_size, 1)
        self.assertFalse(adapter.config.cross_learning)
        self.assertEqual(adapter.config.device_map, "cpu")
        self.assertTrue(adapter.config.local_files_only)

    def test_shared_factory_rejects_implicit_type_coercions(self):
        class FakeConfig:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        class FakeAdapter:
            def __init__(self, manifest, config):
                self.config = config

        invalid_parameters = (
            {"batch_size": True},
            {"context_length": True},
            {"cross_learning": 0},
            {"local_files_only": 1},
            {"device_map": True},
            {"checkpoint_revision": True},
        )
        with patch.object(run_benchmark, "Chronos2Adapter", FakeAdapter), patch.object(run_benchmark, "Chronos2Config", FakeConfig):
            for parameters in invalid_parameters:
                with self.subTest(parameters=parameters):
                    with tempfile.TemporaryDirectory() as directory:
                        factory = run_benchmark.make_shared_chronos_factory(load_manifest(MANIFEST), Path(directory))
                        with self.assertRaises(ValueError):
                            factory("motor-01", parameters)

    def test_benchmark_requires_exactly_one_chronos_model_and_allows_both_policies(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config.json"
            config.write_text(json.dumps({"models": [{"name": "chronos2"}, {"name": "chronos2"}]}), encoding="utf-8")
            common = {"_external_cache": patch.object(run_benchmark, "_external_cache", return_value=Path(directory)), "_load": patch.object(run_benchmark, "_load_and_validate_license", return_value=load_manifest(MANIFEST)), "_checkpoint": patch.object(run_benchmark, "_verify_cached_checkpoint"), "_package": patch.object(run_benchmark, "_verify_installed_package")}
            with common["_external_cache"], common["_load"], common["_checkpoint"], common["_package"]:
                with self.assertRaisesRegex(ValueError, "exactly one"):
                    run_benchmark.run_chronos_benchmark(config, ROOT, Path(directory))

            for policy in ("native", "validation-residual-by-lead", None):
                model = {"name": "chronos2"}
                if policy is not None:
                    model["quantile_policy"] = policy
                config.write_text(json.dumps({"models": [model]}), encoding="utf-8")
                with patch.object(run_benchmark, "_external_cache", return_value=Path(directory)), patch.object(run_benchmark, "_load_and_validate_license", return_value=load_manifest(MANIFEST)), patch.object(run_benchmark, "_verify_cached_checkpoint"), patch.object(run_benchmark, "_verify_installed_package"), patch.object(run_benchmark, "run_benchmark", return_value=Path(directory) / "result"):
                    result = run_benchmark.run_chronos_benchmark(config, ROOT, Path(directory))
                self.assertEqual(result, Path(directory) / "result")

            config.write_text(json.dumps({"models": [{"name": "chronos2", "quantile_policy": "p50-calibration"}]}), encoding="utf-8")
            with patch.object(run_benchmark, "_external_cache", return_value=Path(directory)), patch.object(run_benchmark, "_load_and_validate_license", return_value=load_manifest(MANIFEST)), patch.object(run_benchmark, "_verify_cached_checkpoint"), patch.object(run_benchmark, "_verify_installed_package"):
                with self.assertRaisesRegex(ValueError, "native or validation"):
                    run_benchmark.run_chronos_benchmark(config, ROOT, Path(directory))

    def test_installed_package_version_is_checked(self):
        with patch("tools.chronos2.importlib.metadata.version", return_value="2.3.0"):
            with self.assertRaisesRegex(ValueError, "does not match"):
                importlib.import_module("tools.chronos2").verify_installed_package()

    def test_smoke_request_is_multivariate_and_uses_both_covariate_modes(self):
        request, _ = run_smoke.build_smoke_case()
        self.assertEqual(len(request.target_signal_ids), 2)
        self.assertEqual([series.metadata.signal_id for series in request.known_future_covariates], ["planned_load"])
        self.assertIn("speed", [series.metadata.signal_id for series in request.contexts])

    def test_smoke_outputs_machine_readable_contract_with_fake_backend(self):
        with tempfile.TemporaryDirectory() as cache_directory, tempfile.TemporaryDirectory(dir=ROOT / "artifacts") as output_directory:
            output = Path(output_directory) / "smoke.json"
            factory = lambda manifest, config: Chronos2Adapter(manifest, config=config, backend=FakeChronosBackend())
            with patch.object(run_smoke, "_verify_installed_package"), patch.object(run_smoke, "Chronos2Adapter", Chronos2Adapter), patch.object(run_smoke, "Chronos2Config", importlib.import_module("banto_ai.adapters.chronos2").Chronos2Config):
                payload = run_smoke.run_smoke(Path(cache_directory), output, adapter_factory=factory, skip_checkpoint_verification=True)
            self.assertEqual(payload["status"], "pass")
            self.assertEqual(payload["request"]["past_only_covariate_ids"], ["speed"])
            self.assertEqual(payload["request"]["known_future_covariate_ids"], ["planned_load"])
            provenance = payload["model"]["provenance"]
            self.assertEqual(provenance["verification_status"], "skipped-test-only")
            self.assertIsNone(provenance["checkpoint_model_size_bytes"])
            self.assertIsNone(provenance["checkpoint_model_sha256"])
            self.assertEqual(provenance["allowed_use"], "commercial-evaluation")
            self.assertFalse(payload["runtime"]["snapshot_verified"])
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["status"], "pass")

    def test_smoke_records_verified_checkpoint_evidence(self):
        with tempfile.TemporaryDirectory() as cache_directory, tempfile.TemporaryDirectory(dir=ROOT / "artifacts") as output_directory:
            cache = Path(cache_directory)
            snapshot = cache / "snapshots" / DEFAULT_REVISION
            output = Path(output_directory) / "verified-smoke.json"
            artifact = {
                "path": str(snapshot / "model.safetensors"),
                "size_bytes": chronos_tools.EXPECTED_MODEL_SIZE_BYTES,
                "sha256": chronos_tools.EXPECTED_MODEL_SHA256,
            }
            factory = lambda manifest, config: Chronos2Adapter(manifest, config=config, backend=FakeChronosBackend())
            with patch.object(run_smoke, "_verify_installed_package"), patch.object(run_smoke, "_verify_cached_checkpoint", return_value=snapshot), patch.object(run_smoke, "_verify_model_artifact", return_value=artifact):
                payload = run_smoke.run_smoke(cache, output, adapter_factory=factory)
            provenance = payload["model"]["provenance"]
            self.assertEqual(provenance["package_sha256"], chronos_tools.OFFICIAL_PACKAGE_SHA256)
            self.assertEqual(provenance["checkpoint_model_size_bytes"], chronos_tools.EXPECTED_MODEL_SIZE_BYTES)
            self.assertEqual(provenance["checkpoint_model_sha256"], chronos_tools.EXPECTED_MODEL_SHA256)
            self.assertEqual(provenance["allowed_use"], "commercial-evaluation")
            self.assertEqual(provenance["verification_status"], "verified")
            self.assertTrue(payload["runtime"]["snapshot_verified"])

    def test_tool_import_does_not_import_heavy_backend_modules(self):
        code = "import sys; import tools.chronos2.run_benchmark; print(sorted({'torch','numpy','transformers','chronos'} & set(sys.modules)))"
        result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, check=True, capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), "[]")

    def test_chronos_matrix_config_has_eight_schema_valid_cells_and_dedicated_outputs(self):
        path = ROOT / "examples" / "configs" / "benchmark-matrix-chronos2-small.json"
        config = load_json_file(path)
        validate(config, load_json_file(ROOT / "schemas" / "benchmark-matrix-config.schema.json"))
        self.assertEqual(config["generator_config_path"], "examples/configs/synthetic-motor-small.json")
        self.assertEqual(config["benchmark_config_path"], "examples/configs/benchmark-chronos2-baselines-past-only.json")
        self.assertEqual(config["axes"], {"seeds": [17, 42], "horizons": [1, 3], "context_lengths": [6, 12]})
        self.assertEqual(
            len(config["axes"]["seeds"]) * len(config["axes"]["horizons"]) * len(config["axes"]["context_lengths"]),
            8,
        )
        outputs = (config["dataset_output_root"], config["benchmark_output_root"], config["matrix_output_dir"])
        self.assertTrue(all("chronos2" in output for output in outputs))
        self.assertEqual(len(set(outputs)), 3)

    def test_chronos_matrix_wrapper_validates_environment_and_shares_factory(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts") as control_directory, tempfile.TemporaryDirectory() as cache_directory:
            control = Path(control_directory)
            benchmark = load_json_file(ROOT / "examples" / "configs" / "benchmark-chronos2-baselines-past-only.json")
            benchmark_path = control / "benchmark.json"
            benchmark_path.write_text(json.dumps(benchmark), encoding="utf-8")
            matrix = load_json_file(ROOT / "examples" / "configs" / "benchmark-matrix-chronos2-small.json")
            matrix["benchmark_config_path"] = benchmark_path.relative_to(ROOT).as_posix()
            matrix["dataset_output_root"] = f"artifacts/chronos2-test-data-{control.name}"
            matrix["benchmark_output_root"] = f"artifacts/chronos2-test-runs-{control.name}"
            matrix["matrix_output_dir"] = f"artifacts/chronos2-test-result-{control.name}"
            matrix_path = control / "matrix.json"
            matrix_path.write_text(json.dumps(matrix), encoding="utf-8")
            relative_matrix = matrix_path.relative_to(ROOT).as_posix()
            cache = Path(cache_directory)
            shared_factory = lambda _equipment_id, _parameters: object()
            calls = []

            def fake_runner(path, root, registry):
                calls.append({
                    "path": path,
                    "root": root,
                    "registry": registry,
                    "offline": (os.environ.get("HF_HUB_OFFLINE"), os.environ.get("HF_HUB_DISABLE_TELEMETRY")),
                    "cache": (os.environ.get("HF_HOME"), os.environ.get("HF_HUB_CACHE")),
                })
                self.assertIs(registry._factories["chronos2"], shared_factory)
                return control / "fake-output"

            manifest = {"allowed_use": "commercial-evaluation"}
            with patch.object(run_matrix.single_run, "_external_cache", return_value=cache) as external, patch.object(run_matrix.single_run, "_load_and_validate_license", return_value=manifest) as license_check, patch.object(run_matrix.single_run, "_verify_cached_checkpoint") as checkpoint, patch.object(run_matrix.single_run, "_verify_installed_package") as package, patch.object(run_matrix.single_run, "make_shared_chronos_factory", return_value=shared_factory) as factory, patch.dict(os.environ, {"HF_HUB_OFFLINE": "caller", "HF_HUB_DISABLE_TELEMETRY": "caller", "HF_HOME": "caller-home", "HF_HUB_CACHE": "caller-cache"}, clear=False):
                output = run_matrix.run_chronos_matrix(
                    relative_matrix,
                    ROOT,
                    cache,
                    MANIFEST,
                    matrix_runner=fake_runner,
                )
                self.assertEqual(os.environ["HF_HUB_OFFLINE"], "caller")
                self.assertEqual(os.environ["HF_HUB_DISABLE_TELEMETRY"], "caller")
                self.assertEqual(os.environ["HF_HOME"], "caller-home")
                self.assertEqual(os.environ["HF_HUB_CACHE"], "caller-cache")
            self.assertEqual(output, control / "fake-output")
            self.assertEqual(calls[0]["path"], matrix_path.resolve())
            self.assertEqual(calls[0]["root"], ROOT.resolve())
            self.assertEqual(calls[0]["offline"], ("1", "1"))
            self.assertEqual(calls[0]["cache"], (str(cache.resolve()), str(cache.resolve())))
            external.assert_called_once_with(cache, must_exist=True)
            license_check.assert_called_once_with(MANIFEST)
            checkpoint.assert_called_once_with(cache)
            package.assert_called_once_with()
            factory.assert_called_once_with(manifest, cache)

    def test_chronos_matrix_rejects_invalid_paths_before_environment_checks(self):
        with patch.object(run_matrix.single_run, "_external_cache") as external:
            with self.assertRaisesRegex(ValueError, "repository-relative POSIX"):
                run_matrix.run_chronos_matrix(
                    str((ROOT / "examples" / "configs" / "benchmark-matrix-chronos2-small.json").resolve()),
                    ROOT,
                    Path("unused"),
                )
        external.assert_not_called()
        invalid_paths = (
            ("generator_config_path", "../outside.json"),
            ("benchmark_config_path", "examples\\configs\\benchmark.json"),
            ("matrix_output_dir", "C:\\absolute\\matrix"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts") as directory:
            for field, value in invalid_paths:
                with self.subTest(field=field):
                    matrix = load_json_file(ROOT / "examples" / "configs" / "benchmark-matrix-chronos2-small.json")
                    matrix[field] = value
                    path = Path(directory) / f"invalid-{field}.json"
                    path.write_text(json.dumps(matrix), encoding="utf-8")
                    with patch.object(run_matrix.single_run, "_external_cache") as external:
                        with self.assertRaises(ValueError):
                            run_matrix.run_chronos_matrix(path.relative_to(ROOT).as_posix(), ROOT, Path("unused"))
                    external.assert_not_called()

    def test_chronos_matrix_rejects_invalid_model_policy_and_runtime_boundaries(self):
        base = load_json_file(ROOT / "examples" / "configs" / "benchmark-chronos2-baselines-past-only.json")
        chronos = next(model for model in base["models"] if model["name"] == "chronos2")
        cases = {
            "missing-model": [model for model in base["models"] if model["name"] != "chronos2"],
            "duplicate-model": [*base["models"], dict(chronos)],
            "invalid-policy": [*base["models"][:-1], {**chronos, "quantile_policy": "validation-residual-by-lead"}],
            "invalid-revision": [*base["models"][:-1], {**chronos, "parameters": {**chronos["parameters"], "checkpoint_revision": "0" * 40}}],
            "invalid-device": [*base["models"][:-1], {**chronos, "parameters": {**chronos["parameters"], "device_map": "cuda"}}],
            "network-enabled": [*base["models"][:-1], {**chronos, "parameters": {**chronos["parameters"], "local_files_only": False}}],
        }
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts") as directory:
            control = Path(directory)
            for label, models in cases.items():
                with self.subTest(label=label):
                    benchmark = dict(base)
                    benchmark["models"] = models
                    benchmark_path = control / f"benchmark-{label}.json"
                    benchmark_path.write_text(json.dumps(benchmark), encoding="utf-8")
                    matrix = load_json_file(ROOT / "examples" / "configs" / "benchmark-matrix-chronos2-small.json")
                    matrix["benchmark_config_path"] = benchmark_path.relative_to(ROOT).as_posix()
                    matrix_path = control / f"matrix-{label}.json"
                    matrix_path.write_text(json.dumps(matrix), encoding="utf-8")
                    with patch.object(run_matrix.single_run, "_external_cache") as external:
                        with self.assertRaises(ValueError):
                            run_matrix.run_chronos_matrix(matrix_path.relative_to(ROOT).as_posix(), ROOT, Path("unused"))
                    external.assert_not_called()


if __name__ == "__main__":
    unittest.main()
