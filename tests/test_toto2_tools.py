from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools import toto2
from tools.toto2 import preflight, run_benchmark, run_smoke
from banto_ai.adapters.toto2 import BackendForecast, OFFICIAL_QUANTILES, Toto2Adapter


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
        scripts = tuple(ROOT / "tools" / "toto2" / name for name in ("preflight.py", "prepare_checkpoint.py", "run_smoke.py", "run_benchmark.py"))
        environment = dict(os.environ)
        environment.pop("PYTHONPATH", None)
        with tempfile.TemporaryDirectory() as external_cwd:
            for script in scripts:
                with self.subTest(cwd="repository", script=script.name):
                    completed = subprocess.run([sys.executable, script.relative_to(ROOT).as_posix(), "--help"], cwd=ROOT, env=environment, capture_output=True, text=True)
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    self.assertNotIn("ModuleNotFoundError", completed.stderr)
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


if __name__ == "__main__":
    unittest.main()
