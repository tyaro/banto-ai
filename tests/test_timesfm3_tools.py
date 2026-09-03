import json
import hashlib
import ctypes
from dataclasses import replace
import os
from pathlib import Path
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from banto_ai.adapters.timesfm3 import BackendForecast, TimesFM3Adapter, TimesFM3Config
from banto_ai.types import ForecastSeriesResult, ForecastResult, QuantileForecast, QualityStatus
from tools.timesfm3 import preflight, prepare_checkpoint, run_benchmark, run_smoke


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "examples" / "manifests" / "model-license-timesfm3.json"


class TimesFM3ToolTests(unittest.TestCase):
    def test_benchmark_factory_shares_one_adapter_across_equipment(self):
        adapter_instances = []

        class FakeAdapter:
            def __init__(self, manifest, config):
                adapter_instances.append((manifest, config))

        with patch.object(run_benchmark, "TimesFM3Adapter", FakeAdapter):
            manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
            factory = run_benchmark.make_shared_timesfm_factory(manifest, Path("C:/external/timesfm-cache"))
            first = factory("motor-01", {})
            second = factory("conveyor-01", {})
        self.assertIs(first, second)
        self.assertEqual(len(adapter_instances), 1)

    def test_preflight_is_machine_readable_and_fails_closed(self):
        report = preflight.collect_preflight(
            Path("C:/external/timesfm-cache"),
            python_version=(3, 11, 9),
            total_ram_bytes=preflight.MIN_RAM_BYTES - 1,
            available_disk_bytes=preflight.MIN_DISK_BYTES - 1,
            optional_packages={name: False for name in preflight.OPTIONAL_PACKAGES},
        )
        encoded = json.dumps(report, allow_nan=False)
        self.assertEqual(json.loads(encoded)["status"], "fail")
        self.assertFalse(report["checks"]["python"]["ok"])
        self.assertFalse(report["checks"]["ram"]["ok"])
        self.assertFalse(report["checks"]["disk"]["ok"])
        self.assertFalse(report["evaluation"]["cuda_required"])
        self.assertIn("not searched", preflight.human_summary(report))

    def test_preflight_passes_when_cpu_requirements_pass_without_cuda(self):
        report = preflight.collect_preflight(
            Path("C:/external/timesfm-cache"),
            python_version=(3, 14, 0),
            total_ram_bytes=preflight.MIN_RAM_BYTES,
            available_disk_bytes=preflight.MIN_DISK_BYTES,
            optional_packages={name: False for name in preflight.OPTIONAL_PACKAGES},
        )
        self.assertEqual(report["status"], "pass")
        self.assertTrue(all(check["ok"] for check in report["checks"].values()))

    def test_prepare_requires_explicit_license_acceptance_before_import(self):
        with tempfile.TemporaryDirectory() as cache:
            with patch.dict(sys.modules, {"huggingface_hub": None}):
                with self.assertRaises(ValueError):
                    prepare_checkpoint.prepare_checkpoint(Path(cache), MANIFEST, accepted=False)

    def test_prepare_rejects_repository_cache(self):
        with self.assertRaises(ValueError):
            prepare_checkpoint.prepare_checkpoint(
                ROOT / "artifacts" / "timesfm-cache", MANIFEST, accepted=True,
            )

    def test_prepare_download_arguments_are_fixed(self):
        calls = []
        content = b"fake-model-safetensors"

        class FakeHub:
            @staticmethod
            def snapshot_download(**kwargs):
                calls.append(kwargs)
                snapshot = Path(kwargs["cache_dir"]) / "snapshots" / "fixed"
                snapshot.mkdir(parents=True, exist_ok=True)
                (snapshot / "model.safetensors").write_bytes(content)
                (snapshot / "config.json").write_text("{}", encoding="utf-8")
                (snapshot / "LICENSE").write_text("license", encoding="utf-8")
                (snapshot / "README.md").write_text("readme", encoding="utf-8")
                return str(snapshot)

        with tempfile.TemporaryDirectory() as cache:
            with patch.dict(sys.modules, {"huggingface_hub": FakeHub}):
                with patch.object(prepare_checkpoint, "EXPECTED_MODEL_SIZE_BYTES", len(content)):
                    with patch.object(prepare_checkpoint, "EXPECTED_MODEL_SHA256", hashlib.sha256(content).hexdigest()):
                        with patch.object(prepare_checkpoint, "load_checkpoint_provenance", return_value={}):
                            result = prepare_checkpoint.prepare_checkpoint(Path(cache), MANIFEST, accepted=True)
        self.assertEqual(calls, [{
            "repo_id": "google/timesfm-3.0-pytorch",
            "revision": "43046b85ec22d584a13f8098c2ed39c889e129c2",
            "cache_dir": str(Path(cache).resolve()),
            "allow_patterns": ["config.json", "model.safetensors", "LICENSE", "README.md"],
        }])
        self.assertEqual(result["allowed_use"], "research-only")
        self.assertEqual(result["model_artifact"]["size_bytes"], len(content))

    def test_prepare_rejects_model_digest_mismatch(self):
        content = b"fake-model-safetensors"

        class FakeHub:
            @staticmethod
            def snapshot_download(**kwargs):
                snapshot = Path(kwargs["cache_dir"]) / "snapshots" / "fixed"
                snapshot.mkdir(parents=True, exist_ok=True)
                (snapshot / "model.safetensors").write_bytes(content)
                (snapshot / "config.json").write_text("{}", encoding="utf-8")
                (snapshot / "LICENSE").write_text("license", encoding="utf-8")
                (snapshot / "README.md").write_text("readme", encoding="utf-8")
                return str(snapshot)

        with tempfile.TemporaryDirectory() as cache:
            with patch.dict(sys.modules, {"huggingface_hub": FakeHub}):
                with patch.object(prepare_checkpoint, "load_checkpoint_provenance", return_value={}):
                    with patch.object(prepare_checkpoint, "EXPECTED_MODEL_SIZE_BYTES", len(content)):
                        with patch.object(prepare_checkpoint, "EXPECTED_MODEL_SHA256", "0" * 64):
                            with self.assertRaises(ValueError):
                                prepare_checkpoint.prepare_checkpoint(Path(cache), MANIFEST, accepted=True)

    def test_checkpoint_provenance_contains_official_artifact_expectations(self):
        provenance = prepare_checkpoint.load_checkpoint_provenance()
        self.assertEqual(
            provenance["checkpoint_allow_patterns"],
            ["config.json", "model.safetensors", "LICENSE", "README.md"],
        )
        self.assertEqual(provenance["checkpoint_model_size_bytes"], 1322898824)
        self.assertEqual(
            provenance["checkpoint_model_sha256"],
            "a7592b0a8432baee54483254e5647856911ce69e09d09a9bb65904b2d98f17da",
        )

    def test_windows_cpu_lock_contains_expected_26_packages_and_provenance_runtime(self):
        lock_path = ROOT / "environments" / "timesfm3" / "requirements-windows-cpu-py314.lock"
        packages = {}
        for line in lock_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            name, version = line.split("==", 1)
            packages[name.lower()] = version
        expected = {
            "anyio": "4.15.0",
            "certifi": "2026.7.22",
            "click": "8.5.0",
            "colorama": "0.4.6",
            "filelock": "3.32.5",
            "fsspec": "2026.7.0",
            "h11": "0.16.0",
            "hf-xet": "1.6.0",
            "huggingface_hub": "1.30.0",
            "httpcore": "1.0.9",
            "httpx": "0.28.1",
            "idna": "3.19",
            "jinja2": "3.1.6",
            "markupsafe": "3.0.3",
            "mpmath": "1.3.0",
            "networkx": "3.6.1",
            "numpy": "2.5.2",
            "packaging": "26.3",
            "pyyaml": "6.0.3",
            "safetensors": "0.8.0",
            "setuptools": "84.0.0",
            "sympy": "1.14.0",
            "timesfm": "3.0.0",
            "torch": "2.14.0",
            "tqdm": "4.70.0",
            "typing_extensions": "4.16.0",
        }
        self.assertEqual(len(packages), 26)
        self.assertEqual(packages, expected)
        provenance = json.loads(
            (ROOT / "environments" / "timesfm3" / "package-provenance.json").read_text(encoding="utf-8")
        )
        self.assertEqual(packages[provenance["package_name"]], provenance["package_version"])
        for required in ("timesfm", "huggingface_hub", "numpy", "safetensors", "torch"):
            self.assertIn(required, packages)

    def _output_path(self):
        directory = ROOT / "artifacts" / "test-timesfm3-tools"
        directory.mkdir(parents=True, exist_ok=True)
        return directory / "smoke.json"

    def _fake_factory(self, calls):
        def factory(manifest, config):
            calls.append({
                "manifest": manifest,
                "config": config,
                "offline": (
                    os.environ.get("HF_HUB_OFFLINE"),
                    os.environ.get("HF_HUB_DISABLE_TELEMETRY"),
                ),
            })

            class FakeBackend:
                def forecast(self, targets, past_only_covariates, past_future_covariates, horizon, return_quantiles):
                    self.args = (targets, past_only_covariates, past_future_covariates, horizon, return_quantiles)
                    return BackendForecast(
                        tuple(tuple(float(value[-1] + step) for step in range(horizon)) for value in targets),
                        tuple(
                            tuple(
                                tuple(float(target[-1] + step + q * 0.01) for q in range(9))
                                for step in range(horizon)
                            )
                            for target in targets
                        ),
                    )

            return TimesFM3Adapter(manifest, config=config, backend=FakeBackend())

        return factory

    def test_run_smoke_fake_adapter_publishes_expected_artifact(self):
        calls = []
        output = self._output_path()
        if output.exists():
            output.unlink()
        with patch.dict(os.environ, {
            "HF_HUB_OFFLINE": "caller-value",
            "HF_HUB_DISABLE_TELEMETRY": "caller-value",
        }):
            with tempfile.TemporaryDirectory() as cache:
                payload = run_smoke.run_smoke(
                    Path(cache), output, adapter_factory=self._fake_factory(calls),
                )
            self.assertEqual(os.environ["HF_HUB_OFFLINE"], "caller-value")
            self.assertEqual(os.environ["HF_HUB_DISABLE_TELEMETRY"], "caller-value")
        artifact = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(payload, artifact)
        self.assertEqual(artifact["status"], "passed")
        self.assertTrue(artifact["research_only"])
        self.assertFalse(artifact["production"])
        self.assertFalse(artifact["control_write"])
        self.assertTrue(artifact["safety"]["local_files_only"])
        self.assertFalse(artifact["safety"]["network_fallback"])
        self.assertFalse(artifact["safety"]["plc_write"])
        self.assertEqual(artifact["input"]["target_count"], 2)
        self.assertEqual(artifact["input"]["context_length"], 64)
        self.assertEqual(artifact["input"]["horizon"], 8)
        self.assertEqual(artifact["input"]["known_future_covariate_count"], 1)
        self.assertEqual(set(artifact["predictions"][0]["quantile_forecast"]), {"0.1", "0.5", "0.9"})
        self.assertEqual(len(artifact["predictions"][0]["actual"]), 8)
        self.assertEqual(set(artifact["metrics"]["target"]["motor_current"]), {"mae", "rmse", "mean_p90_p10_width"})
        self.assertEqual(set(artifact["metrics"]["aggregate"]), {"mae", "rmse", "mean_p90_p10_width"})
        self.assertEqual(set(artifact["metrics"]["baseline"]["aggregate"]), {"mae", "rmse"})
        self.assertIn("mae", artifact["metrics"]["comparison"]["aggregate"])
        self.assertIn("absolute_difference", artifact["metrics"]["comparison"]["aggregate"]["mae"])
        self.assertIn("do not represent production equipment performance", artifact["metrics"]["interpretation"])
        self.assertTrue(artifact["offline_env_enforced"])
        self.assertTrue(artifact["safety"]["offline_env_enforced"])
        self.assertEqual(calls[0]["offline"], ("1", "1"))
        self.assertEqual(calls[0]["config"].local_files_only, True)
        self.assertEqual(calls[0]["config"].cache_dir, str(Path(cache).resolve()))
        output.unlink()

    def test_smoke_case_is_non_linear_and_fingerprint_includes_future_metadata(self):
        request, actual = run_smoke.build_smoke_case()
        self.assertEqual(len(request.contexts[0].points), 64)
        self.assertEqual(request.horizon, 8)
        self.assertEqual(tuple(len(values) for values in actual.values()), (8, 8))
        self.assertNotEqual(
            request.contexts[0].points[0].value,
            request.contexts[0].points[1].value,
        )
        original_fingerprint = run_smoke._request_fingerprint(request)
        future = request.known_future_covariates[0]
        changed_metadata = replace(future.metadata, unit="different-unit")
        changed_future = replace(future, metadata=changed_metadata)
        changed_request = replace(request, known_future_covariates=(changed_future,))
        self.assertNotEqual(original_fingerprint, run_smoke._request_fingerprint(changed_request))

    def test_comparison_is_inconclusive_when_baseline_is_zero(self):
        comparison = run_smoke._comparison_metrics(
            {"mae": 0.5, "rmse": 0.5},
            {"mae": 0.0, "rmse": 0.0},
        )
        self.assertIsNone(comparison["mae"]["improvement_rate"])
        self.assertEqual(comparison["mae"]["status"], "inconclusive: baseline metric is zero")

    def test_run_smoke_rejects_repository_cache_and_unsafe_output(self):
        output = self._output_path()
        if output.exists():
            output.unlink()
        with self.assertRaises(ValueError):
            run_smoke.run_smoke(ROOT / "artifacts" / "cache", output, adapter_factory=lambda *_: None)
        with tempfile.TemporaryDirectory() as cache:
            with self.assertRaises(ValueError):
                run_smoke.run_smoke(Path(cache), ROOT / "outside.json", adapter_factory=lambda *_: None)

    def test_run_smoke_refuses_existing_output_before_adapter(self):
        output = self._output_path()
        output.write_text("sentinel", encoding="utf-8")
        try:
            with tempfile.TemporaryDirectory() as cache:
                with self.assertRaises(FileExistsError):
                    run_smoke.run_smoke(Path(cache), output, adapter_factory=lambda *_: self.fail("adapter must not run"))
            self.assertEqual(output.read_text(encoding="utf-8"), "sentinel")
        finally:
            output.unlink(missing_ok=True)

    def test_atomic_publish_rejects_racing_existing_target_without_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            output = parent / "result.json"
            with patch.object(run_smoke.os, "link", side_effect=FileExistsError("race")):
                with self.assertRaises(FileExistsError):
                    run_smoke._atomic_publish(output, {"status": "passed"})
            self.assertFalse(output.exists())
            self.assertEqual(tuple(parent.glob("*.tmp")), ())

    def test_windows_memory_helper_uses_complete_process_memory_counters(self):
        class FakeFunction:
            def __init__(self, value=None):
                self.value = value
                self.argtypes = None
                self.restype = None
                self.size = None

            def __call__(self, *args):
                if len(args) == 3 and self.size is None:
                    self.size = args[2]
                    counters = args[1]._obj
                    counters.PeakWorkingSetSize = 123456789
                    counters.WorkingSetSize = 111
                return self.value

        class FakePsapi:
            def __init__(self):
                self.GetProcessMemoryInfo = FakeFunction(1)

        class FakeKernel32:
            def __init__(self):
                self.GetCurrentProcess = FakeFunction(7)

        psapi = FakePsapi()
        kernel32 = FakeKernel32()
        value = run_smoke._windows_peak_working_set_bytes(psapi=psapi, kernel32=kernel32)
        self.assertEqual(value, 123456789)
        self.assertEqual(len(psapi.GetProcessMemoryInfo.argtypes), 3)
        self.assertIsNotNone(psapi.GetProcessMemoryInfo.restype)
        self.assertIsNotNone(kernel32.GetCurrentProcess.restype)
        self.assertGreaterEqual(
            psapi.GetProcessMemoryInfo.size,
            ctypes.sizeof(ctypes.c_size_t) * 8 + ctypes.sizeof(ctypes.c_ulong) * 2,
        )


if __name__ == "__main__":
    unittest.main()
