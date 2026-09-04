"""MetroPT-3 public benchmark contract tests without checking in public data."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from banto_ai.benchmark import BenchmarkError, _normalize_quality_gate, _policy, _summary_disclaimer
from banto_ai.manifest import validate


ROOT = Path(__file__).resolve().parents[1]


class PublicBenchmarkTests(unittest.TestCase):
    def test_quality_gate_is_normalized_and_invalid_values_fail_closed(self):
        detailed = {
            "status": "pass",
            "observation_record_count": 120,
            "equipment_count": 2,
            "checks": ["fingerprint"],
            "dataset_id": "public-dataset",
            "dataset_fingerprint": "external-detail",
        }
        normalized = _normalize_quality_gate(detailed)
        self.assertEqual(
            normalized,
            {
                "status": "pass",
                "observation_record_count": 120,
                "equipment_count": 2,
                "checks": ["fingerprint"],
            },
        )
        for invalid in (
            {},
            {**detailed, "status": "fail"},
            {**detailed, "observation_record_count": True},
            {**detailed, "checks": []},
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(BenchmarkError):
                    _normalize_quality_gate(invalid)

    def test_summary_disclaimer_is_provenance_aware_and_fail_closed(self):
        self.assertEqual(
            _summary_disclaimer("synthetic"),
            "合成データの結果であり、実設備の性能を示しません。",
        )
        self.assertEqual(
            _summary_disclaimer("public"),
            "公開実データの限定区間による研究評価であり、実設備一般の性能や製品適合性を示しません。",
        )
        unknown = _summary_disclaimer("unrecognized")
        self.assertIn("研究評価", unknown)
        self.assertIn("実設備一般の性能", unknown)

    def test_metropt3_baseline_config_is_schema_valid_and_past_only(self):
        config = json.loads(
            (ROOT / "examples/configs/benchmark-metropt3-baselines.json").read_text(encoding="utf-8")
        )
        schema = json.loads(
            (ROOT / "schemas/benchmark-run-config.schema.json").read_text(encoding="utf-8")
        )
        validate(config, schema)
        self.assertEqual(config["run_id"], "benchmark-metropt3-baselines")
        self.assertEqual(config["dataset_path"], "artifacts/public-datasets/metropt3-public-2020-02-21")
        self.assertEqual(config["output_dir"], "artifacts/benchmark/benchmark-metropt3-baselines")
        self.assertEqual(config["horizon"], 15)
        self.assertEqual(config["context_length"], 120)
        self.assertEqual(config["equipment_ids"], ["metropt3-apu-01"])
        self.assertEqual(config["target_signal_ids"], ["tp3", "oil_temperature", "motor_current"])
        self.assertEqual(config["known_future_covariate_ids"], [])
        self.assertEqual(config["validation_origin_stride"], 15)
        self.assertEqual(config["test_origin_stride"], 15)
        self.assertEqual(config["max_validation_origins"], 16)
        self.assertEqual(config["max_test_origins"], 16)
        self.assertEqual(config["quantiles"], [0.1, 0.5, 0.9])
        self.assertNotIn("seed", config)
        self.assertEqual(
            config["past_only_covariate_ids"],
            ["tp2", "h1", "dv_pressure", "reservoirs", "comp", "dv_electric", "towers", "mpg", "lps", "pressure_switch", "oil_level"],
        )
        self.assertEqual(
            config["models"],
            [
                {"name": "last-value"},
                {"name": "seasonal-naive", "parameters": {"season_length": 60}},
                {"name": "moving-average", "parameters": {"window": 15}},
                {"name": "ewma", "parameters": {"alpha": 0.3}},
                {"name": "holt-linear", "parameters": {"alpha": 0.8, "beta": 0.2}},
            ],
        )
        model_names = [model["name"] for model in config["models"]]
        self.assertNotIn("linear-regression-covariates", model_names)
        self.assertNotIn("timesfm3", model_names)
        self.assertNotIn("chronos2", model_names)
        self.assertEqual(
            {_policy(model) for model in config["models"]},
            {"validation-residual-by-lead"},
        )


if __name__ == "__main__":
    unittest.main()
