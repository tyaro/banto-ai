"""Chronos-2の設定契約と文書境界を、外部依存なしで検証する。"""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from banto_ai.manifest import ManifestValidationError, load_json, validate


ROOT = Path(__file__).resolve().parents[1]
RUN_SCHEMA_PATH = ROOT / "schemas" / "benchmark-run-config.schema.json"
RESULT_SCHEMA_PATH = ROOT / "schemas" / "benchmark-result.schema.json"
REVISION = "29ec3766d36d6f73f0696f85560a422f50e8498c"
MODEL_SIZE = "477,930,472 bytes"
MODEL_SHA256 = "ddcda3c7508bf2528087723e98a20707cc04b7f370ae275a9fd88078ddba4f42"
PAST_MAE = "0.20672198138554906"
PAST_WIS = "0.1952207659517925"
KNOWN_MAE = "0.1691488806622826"
KNOWN_RMSE = "0.25764632773710655"
KNOWN_MASE = "0.8187799631009623"
KNOWN_COVERAGE = "0.8333333333333334"
KNOWN_WIDTH = "1.4527024229367573"
KNOWN_WIS = "0.15937026919725228"
CHRONOS_CONFIGS = (
    "benchmark-chronos2-small.json",
    "benchmark-chronos2-baselines-past-only.json",
    "benchmark-chronos2-known-load.json",
    "benchmark-metropt3-chronos2.json",
    "benchmark-metropt3-chronos2-point-calibrated.json",
)


class Chronos2DocumentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.run_schema = load_json(RUN_SCHEMA_PATH)
        cls.result_schema = load_json(RESULT_SCHEMA_PATH)

    def test_all_chronos2_examples_are_valid_run_configs(self) -> None:
        for filename in CHRONOS_CONFIGS:
            with self.subTest(filename=filename):
                config = load_json(ROOT / "examples" / "configs" / filename)
                validate(config, self.run_schema)
                chronos = next(model for model in config["models"] if model["name"] == "chronos2")
                self.assertIn(chronos["quantile_policy"], {"native", "validation-residual-by-lead"})
                self.assertEqual(chronos["parameters"]["checkpoint_revision"], REVISION)
                self.assertEqual(chronos["parameters"]["batch_size"], 1)
                self.assertEqual(chronos["parameters"]["context_length"], config["context_length"])
                self.assertFalse(chronos["parameters"]["cross_learning"])
                self.assertEqual(chronos["parameters"]["device_map"], "cpu")
                self.assertTrue(chronos["parameters"]["local_files_only"])

    def test_chronos2_result_run_config_and_model_parameters_are_valid(self) -> None:
        for filename in CHRONOS_CONFIGS:
            with self.subTest(filename=filename):
                config = load_json(ROOT / "examples" / "configs" / filename)
                validate(config, self.result_schema["$defs"]["runConfig"], root=self.result_schema)
                chronos = next(model for model in config["models"] if model["name"] == "chronos2")
                validate(chronos["parameters"], self.result_schema["$defs"]["modelParameters"], root=self.result_schema)

    def test_unknown_chronos_parameter_is_rejected_by_both_schemas(self) -> None:
        config = load_json(ROOT / "examples" / "configs" / CHRONOS_CONFIGS[0])
        invalid = copy.deepcopy(config)
        chronos = next(model for model in invalid["models"] if model["name"] == "chronos2")
        chronos["parameters"]["trust_remote_code"] = False
        with self.assertRaises(ManifestValidationError):
            validate(invalid, self.run_schema)
        with self.assertRaises(ManifestValidationError):
            validate(invalid, self.result_schema["$defs"]["runConfig"], root=self.result_schema)

    def test_chronos2_quantile_policy_and_parameter_bounds_are_strict(self) -> None:
        config = load_json(ROOT / "examples" / "configs" / CHRONOS_CONFIGS[0])
        invalid_policy = copy.deepcopy(config)
        invalid_policy["models"][1]["quantile_policy"] = "p50-calibration"
        with self.assertRaises(ManifestValidationError):
            validate(invalid_policy, self.run_schema)
        with self.assertRaises(ManifestValidationError):
            validate(invalid_policy, self.result_schema["$defs"]["runConfig"], root=self.result_schema)

        for key, value in (
            ("checkpoint_revision", "not-a-revision"),
            ("batch_size", 0),
            ("context_length", 1),
            ("context_length", 8193),
            ("cross_learning", "false"),
            ("device_map", ""),
            ("local_files_only", "true"),
        ):
            with self.subTest(key=key, value=value):
                invalid = copy.deepcopy(config)
                invalid["models"][1]["parameters"][key] = value
                with self.assertRaises(ManifestValidationError):
                    validate(invalid, self.run_schema)

    def test_chronos2_tool_readme_keeps_single_run_and_matrix_policy_boundaries(self) -> None:
        readme = (ROOT / "tools" / "chronos2" / "README.md").read_text(encoding="utf-8")
        for required in (
            "single-runのquantile policyは`native`と`validation-residual-by-lead`を受け付けます",
            "`native`は公式分位点をそのまま検証し、交差時は補正せず`partial`とします",
            "`validation-residual-by-lead`は公式point-only予測とvalidation residual by lead校正を使う別scenarioです",
            "`run_matrix.py`は`native`限定を維持",
        ):
            with self.subTest(required=required):
                self.assertIn(required, readme)
        self.assertNotIn("quantile policyは`native`だけを受け付け", readme)

    def test_metropt3_chronos_result_documents_two_scenarios_and_current_boundary(self) -> None:
        report = (ROOT / "docs" / "results" / "chronos2-metropt3-evaluation-2026-09-04.md").read_text(encoding="utf-8")
        for required in (
            "Scenario 1: native",
            "Scenario 2: point-calibrated",
            "artifacts/benchmark/benchmark-metropt3-chronos2",
            "artifacts/benchmark/benchmark-metropt3-chronos2-point-calibrated",
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "partial",
            "success",
            "commercial-evaluation",
            "product-candidate",
            "forecast-only",
            "Banto Hub／PLCへのwrite",
            "Git管理対象外",
        ):
            with self.subTest(required=required):
                self.assertIn(required, report)

        docs = "\n".join(
            (ROOT / path).read_text(encoding="utf-8")
            for path in (
                "README.md",
                "docs/chronos2-notes.md",
                "docs/research-roadmap.md",
                "docs/research-implementation-plan.md",
                "docs/architecture.md",
            )
        )
        for obsolete in (
            "rolling benchmark・モデル評価は未実施",
            "Chronos-2／TimesFM 3.0の公開実データ評価は未実施",
        ):
            with self.subTest(obsolete=obsolete):
                self.assertNotIn(obsolete, docs)

    def test_known_load_example_is_not_documented_as_observed_future_data(self) -> None:
        config = load_json(ROOT / "examples" / "configs" / "benchmark-chronos2-known-load.json")
        self.assertEqual(config["past_only_covariate_ids"], [])
        self.assertEqual(config["known_future_covariate_ids"], ["load_proxy"])
        text = (ROOT / "docs" / "chronos2-notes.md").read_text(encoding="utf-8")
        self.assertIn("oracle leakage", text)
        self.assertIn("originの時点で計画システムから確定して取得できた", text)

    def test_documents_fix_isolation_license_p50_missing_and_promotion_boundary(self) -> None:
        notes = (ROOT / "docs" / "chronos2-notes.md").read_text(encoding="utf-8")
        adr = (ROOT / "docs" / "adr-0004-chronos2-isolation.md").read_text(encoding="utf-8")
        architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "docs" / "research-roadmap.md").read_text(encoding="utf-8")
        plan = (ROOT / "docs" / "research-implementation-plan.md").read_text(encoding="utf-8")
        survey = (ROOT / "docs" / "time-series-model-survey.md").read_text(encoding="utf-8")
        combined = "\n".join((notes, adr, architecture, roadmap, plan, survey))
        for required in (
            "chronos-forecasting==2.3.1",
            REVISION,
            "Apache-2.0",
            "commercial-evaluation",
            "product-candidate",
            "median／p50",
            "local_files_only",
            "repository外cache",
            "fail closed",
            "TimesFM 3.0",
            "Chronos-2",
            "https://github.com/amazon-science/chronos-forecasting/blob/v2.3.1/pyproject.toml",
            "https://huggingface.co/amazon/chronos-2/blob/29ec3766d36d6f73f0696f85560a422f50e8498c/config.json",
        ):
            with self.subTest(required=required):
                self.assertIn(required, combined)

    def test_documents_use_computed_checkpoint_evidence_and_distinguish_smoke_scope(self) -> None:
        notes = (ROOT / "docs" / "chronos2-notes.md").read_text(encoding="utf-8")
        adr = (ROOT / "docs" / "adr-0004-chronos2-isolation.md").read_text(encoding="utf-8")
        for name, text in (("notes", notes), ("adr", adr)):
            with self.subTest(document=name):
                self.assertIn(MODEL_SIZE, text)
                self.assertIn(MODEL_SHA256, text)
                self.assertNotIn("X-Xet-Hash", text)
                self.assertNotIn("Xet CDN", text)
                self.assertIn("Python 3.14", text)
                self.assertIn("2 targets", text)
                self.assertIn("3 quantiles", text)
                self.assertIn("1.335", text)
        self.assertIn("Banto adapter／tool経由のCPU smoke", notes)
        self.assertIn("初期rolling benchmark", notes)
        self.assertIn("実model matrix", notes)
        self.assertIn("未実施", notes)

    def test_initial_evaluation_report_records_artifact_exact_values_and_limits(self) -> None:
        report = (ROOT / "docs" / "results" / "chronos2-initial-evaluation-2026-09-04.md").read_text(encoding="utf-8")
        for required in (
            MODEL_SIZE,
            MODEL_SHA256,
            "artifacts/chronos2/cpu-smoke-provenance-2026-09-04.json",
            "artifacts/benchmark/benchmark-chronos2-baselines-past-only/result.json",
            "artifacts/benchmark/benchmark-chronos2-known-load/result.json",
            "12.057009100011783",
            "model.provenance.verification_status=verified",
            "d9d00ec9b1621235bfb26685638bf054885f4c000863678f1c775dfab2697496",
            "allowed use",
            PAST_MAE,
            PAST_WIS,
            KNOWN_MAE,
            KNOWN_RMSE,
            KNOWN_MASE,
            KNOWN_COVERAGE,
            KNOWN_WIDTH,
            KNOWN_WIS,
            "100.6970499875024",
            "120.42497499205638",
            "1,065,250,816 bytes",
            "112.99855000106618",
            "134.7454250077135",
            "1,063,981,056 bytes",
            "dirty=true",
            "oracle leakage",
            "commercial-evaluation",
            "product-candidate",
        ):
            with self.subTest(required=required):
                self.assertIn(required, report)
        self.assertNotIn("正本: `artifacts/chronos2/cpu-smoke-2026-09-04.json`", report)
        self.assertNotIn("0.165581", report)

    def test_matrix_report_records_all_cells_exact_metrics_and_runtime_boundary(self) -> None:
        report = (ROOT / "docs" / "results" / "chronos2-matrix-2026-09-04.md").read_text(encoding="utf-8")
        for required in (
            "artifacts/chronos2/matrix/benchmark-matrix-chronos2-small/result.json",
            "3f57c8500f2a746dd0fce1d02bb9eba566d47748",
            "b0ce7e603eb44deb8ec11fb63bbc88869ab7c91eef0403009d2c8092e08e6c29",
            "f5601fe7038a936ea5a8e4aa0c69c137e3a7e7552fd7be7410accf7350c16d29",
            "8/8 success",
            "0.09357873712348952",
            "0.1389435288047789",
            "0.08927573903020222",
            "0.12088567491340627",
            "0.047065349975586646",
            "0.18173534655761747",
            "0.14721594184366876",
            "0.3063958502044678",
            "coverage",
            "1.1584290564060211",
            "0.9669468402862549",
            "3/6",
            "1/6",
            "moving-average",
            "Holt linear",
            "213.79575624632707",
            "330.96445437840885",
            "1,064,873,984 bytes",
            "78.77301149998675",
            "1.3655998000176623",
            "2.886316399992211",
            "commercial-evaluation",
            "product-candidate",
            "past-only",
            "known-future",
            "high-water mark",
            "拡張した評価条件をclean savepointから再実行",
        ):
            with self.subTest(required=required):
                self.assertIn(required, report)
        self.assertIn("初回loadを含むcold実行時間とは別", report)
        self.assertIn("単純合算を代表値として扱わない", report)
        self.assertNotIn("[Chronos-2 matrix result", report)

    def test_readme_and_plans_record_completed_initial_run_and_completed_matrix(self) -> None:
        paths = (
            ROOT / "README.md",
            ROOT / "docs" / "chronos2-notes.md",
            ROOT / "docs" / "research-roadmap.md",
            ROOT / "docs" / "research-implementation-plan.md",
        )
        for path in paths:
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertIn("chronos2-initial-evaluation-2026-09-04.md", text)
                self.assertIn("chronos2-matrix-2026-09-04.md", text)
                self.assertIn("chronos2-metropt3-evaluation-2026-09-04.md", text)
                self.assertIn(KNOWN_MAE, text)
                self.assertIn("実model matrix", text)
                self.assertIn("commercial-evaluation", text)
                self.assertIn("product-candidate", text)

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("tools\\chronos2\\run_smoke.py", readme)
        self.assertIn("artifacts\\chronos2\\cpu-smoke-provenance-2026-09-04.json", readme)
        self.assertIn("artifacts/chronos2/cpu-smoke-provenance-2026-09-04.json", readme)
        self.assertIn("12.057009100011783", readme)
        self.assertIn("verification_status=verified", readme)
        self.assertIn("benchmark-chronos2-baselines-past-only.json", readme)
        self.assertIn("benchmark-chronos2-known-load.json", readme)
        self.assertIn("py -3.14 -m venv ..\\.venv-banto-ai-chronos2", readme)
        self.assertIn(
            "$chronosPython = '..\\.venv-banto-ai-chronos2\\Scripts\\python.exe'",
            readme,
        )
        self.assertNotRegex(
            readme,
            r"(?im)^\s*(?:py(?:\s+-\d+(?:\.\d+)?)?|python(?:\.exe)?)"
            r"\s+-m\s+venv\s+[A-Za-z]:[\\/]",
        )
        self.assertNotIn("Savepoint 2では", readme)


if __name__ == "__main__":
    unittest.main()
