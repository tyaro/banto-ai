from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import banto_ai.anomaly_matrix_analysis as analysis


ROOT = Path(__file__).resolve().parents[1]


class AnomalyMatrixAnalysisPureTests(unittest.TestCase):
    def test_config_validation_is_read_only_and_pinned(self) -> None:
        output = ROOT / "artifacts" / "anomaly-multiseed-v02-analysis"
        if output.exists():
            self.fail("analysis output must not exist during pure config validation")
        before = sorted(path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file())
        summary = analysis.validate_analysis_config(root=ROOT)
        after = sorted(path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file())
        self.assertEqual(before, after)
        self.assertEqual(summary["status"], "configuration_valid")
        self.assertEqual(summary["run_status"], "not_run")
        self.assertEqual(summary["performance_status"], "not_evaluated")
        self.assertEqual(summary["config_canonical_sha256"], analysis.EXPECTED_ANALYSIS_CONFIG_CANONICAL_SHA256)

    def test_ratio_of_sums_and_percentile_definition(self) -> None:
        aggregate = analysis._Aggregate(precision_num=9, precision_den=235, machine_num=0, machine_den=120, sensor_num=9, sensor_den=120, clean_alerts=222, clean_hours=10.8)
        values = analysis._primary_values(aggregate)
        self.assertAlmostEqual(values["overall_incident_precision"], 9 / 235)
        self.assertAlmostEqual(values["clean_false_alerts_per_8_equipment_hours"], 222 / 10.8 * 8)
        self.assertEqual(analysis.percentile_linear([0.0, 10.0, 20.0], 0.025), 0.5)
        self.assertEqual(analysis.percentile_linear([0.0, 10.0, 20.0], 0.975), 19.5)

    def test_bootstrap_draws_are_version_stable(self) -> None:
        draws, digest = analysis.bootstrap_draws()
        self.assertEqual(len(draws), 10000)
        self.assertTrue(all(len(row) == 10 and all(0 <= value < 10 for value in row) for row in draws))
        self.assertEqual(digest, "5b311c270aaef7bb942e0c4fbe761e8e225aaa0a1314a8bd2e70875f0fd46548")
        self.assertEqual(analysis.bootstrap_draws()[1], digest)

    def test_undefined_replicate_is_inconclusive(self) -> None:
        empty = analysis._Aggregate()
        _point, ci = analysis._bootstrap_metric([empty] * 10, [[0] * 10], "machine_fault_recall")
        self.assertEqual(ci["status"], "inconclusive")
        self.assertEqual(ci["undefined_replicates"], 1)

    def test_gate_status_preserves_fail_and_inconclusive(self) -> None:
        threshold = {"point_min": 0.8, "ci_lower_min": 0.6}
        self.assertEqual(analysis._gate_status(0.9, {"status": "pass", "lower": 0.7, "upper": 1.0}, threshold), "pass")
        self.assertEqual(analysis._gate_status(0.7, {"status": "pass", "lower": 0.7, "upper": 1.0}, threshold), "fail")
        self.assertEqual(analysis._gate_status(None, {"status": "inconclusive", "lower": None, "upper": None}, threshold), "inconclusive")

    def test_config_profile_mix_and_nonfinite_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="analysis-config-") as raw:
            repository = Path(raw)
            for relative in (
                "examples/configs/anomaly-multiseed-analysis-v0.2.json",
                "schemas/anomaly-multiseed-analysis-config-v0.2.schema.json",
            ):
                target = repository / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / relative, target)
            config_path = repository / "examples/configs/anomaly-multiseed-analysis-v0.2.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["matrix_id"] = "anomaly-multiseed-v01"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaises(analysis.AnomalyMatrixAnalysisError):
                analysis.validate_analysis_config(root=repository)

            config = json.loads((ROOT / "examples/configs/anomaly-multiseed-analysis-v0.2.json").read_text(encoding="utf-8"))
            config["input_root"] = "../outside"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaises(analysis.AnomalyMatrixAnalysisError):
                analysis.validate_analysis_config(root=repository)
