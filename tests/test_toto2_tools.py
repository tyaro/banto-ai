from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import toto2
from tools.toto2 import preflight, run_smoke
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
