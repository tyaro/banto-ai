import hashlib
import json
from pathlib import Path
import unittest

from banto_ai.manifest import ManifestValidationError, load_json, validate

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED_ARTIFACT_ROOT = ROOT / "artifacts" / "toto2" / "ctl"


class Toto2DocumentationTests(unittest.TestCase):
    def test_docs_record_fixed_artifacts_and_boundaries(self):
        combined = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "docs/toto2-notes.md", ROOT / "tools/toto2/README.md", ROOT / "README.md"))
        for required in ("toto-2==2.0.0", "toto-models==1.0.0", "8306a9801cf98c0f5ffe4b2dcc8f496e616d84d9", "16582848", "316660d5afb47943e531f39242e0b02ca0b8bb73be5709dfe07ca80dfce9805e", "commercial-evaluation", "decode_block_size=None", "padding", "known-future", "Git", "missingは`value=null`", "staleは有限値＋quality flag", "target_mask=false", "has_missing_values=true", "`stale_value`はsource ageやtransport freshnessの証拠ではありません"):
            with self.subTest(required=required): self.assertIn(required, combined)

    def test_config_keeps_metropt_contract(self):
        config = (ROOT / "examples/configs/benchmark-metropt3-toto2-4m.json").read_text(encoding="utf-8")
        for required in ('"context_length": 120', '"horizon": 15', '"tp3"', '"oil_temperature"', '"motor_current"', '"known_future_covariate_ids": []', '"name": "toto2"'):
            self.assertIn(required, config)

    def test_config_and_result_model_parameters_validate_with_toto(self):
        config = load_json(ROOT / "examples/configs/benchmark-metropt3-toto2-4m.json")
        run_schema = load_json(ROOT / "schemas/benchmark-run-config.schema.json")
        result_schema = load_json(ROOT / "schemas/benchmark-result.schema.json")
        validate(config, run_schema)
        toto = next(model for model in config["models"] if model["name"] == "toto2")
        validate(config, result_schema["$defs"]["runConfig"], root=result_schema)
        validate({"toto2": toto["parameters"]}, result_schema["properties"]["model_parameters"], root=result_schema)

    def test_small_matrix_documentation_matches_measured_scope(self):
        readme = (ROOT / "tools/toto2/README.md").read_text(encoding="utf-8")
        for required in (
            "run_matrix.py",
            "小規模 benchmark matrix（既存 small matrix）",
            "--config examples/configs/benchmark-matrix-toto2-small.json",
            "8条件",
            "context=64はpaddingなし",
            "context=120はpatch_size=32に合わせて128点入力",
            "8/8 cell success、partial 0、failed 0",
            "docs/results/toto2-matrix-2026-09-04.md",
            "同じ共有Toto adapterを8セルで再利用",
            "下記 controlled scenario の結果ではありません",
            "controlled commands は、この README 冒頭で setup した `$totoPython` を使います",
        ):
            with self.subTest(required=required):
                self.assertIn(required, readme)
        self.assertNotIn(
            "--config examples\\configs\\benchmark-matrix-toto2-small.json", readme
        )

    def test_controlled_scenario_definition_and_results_are_referenced(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        notes = (ROOT / "docs/toto2-notes.md").read_text(encoding="utf-8")
        tool_readme = (ROOT / "tools/toto2/README.md").read_text(encoding="utf-8")
        for text in (readme, notes, tool_readme):
            self.assertIn("toto2-controlled-scenarios.md", text)
            self.assertIn("toto2-controlled-evaluation-2026-09-05.md", text)
        for matrix_name in (
            "benchmark-matrix-toto2-controlled-control.json",
            "benchmark-matrix-toto2-controlled-target-fault.json",
            "benchmark-matrix-toto2-controlled-target-quality.json",
            "benchmark-matrix-toto2-controlled-covariate-quality.json",
        ):
            self.assertIn(matrix_name, tool_readme)
        controlled = (ROOT / "docs/toto2-controlled-scenarios.md").read_text(encoding="utf-8")
        for required in (
            "test origin は `384`",
            "truth が unavailable",
            "model ranking",
            "anomaly detection",
            "Phase 2 の完了",
            "4 config を定義しただけでは paired 比較の受入完了ではありません",
            "cross-matrix acceptance analyzer",
            "比較採用不可",
            "non-OK target history を除外して短縮",
            "past-only covariate は使わない",
        ):
            self.assertIn(required, controlled)

    def test_controlled_report_records_fixed_evidence_and_boundaries(self):
        report = (ROOT / "docs/results/toto2-controlled-evaluation-2026-09-05.md").read_text(encoding="utf-8")
        for required in (
            "336afae6e2e7edf80d8e0c3b0f4834e76a5ff257",
            "git clean",
            "https://github.com/tyaro/banto-ai/actions/runs/33888043470",
            "80/80 cells",
            "1,920/1,920 groups",
            "1,440/1,440 paired deltas",
            "availability deltaは全件0",
            "cross_model_ranking_allowed=false",
            "10,800",
            "43,200",
            "137.54 s",
            "120.97 s",
            "131.71 s",
            "118.12 s",
            "707.64 MiB",
            "707.49 MiB",
            "707.89 MiB",
            "707.16 MiB",
            "5795ed4",
            "2026-01-01T00:06:24.000Z",
            "2026-01-01T00:06:24Z",
            "旧artifactはlocal quarantine",
            "実設備への一般化",
            "異常検知accuracy",
            "commissioning自動調整",
            "Banto Hub write",
            "22M",
            "cross-model順位や製品昇格を主張しません",
            "event-aware anomaly scoring",
            "commissioning baseline calibration",
            "shadow／read-only Banto Hub境界",
            "316660d5afb47943e531f39242e0b02ca0b8bb73be5709dfe07ca80dfce9805e",
            "2 equipment、2 target",
            "1 past-only covariate",
            "Toto 2.0同一モデル内",
            "conveyor集約",
            "2 targets × 20 cells",
        ):
            with self.subTest(required=required):
                self.assertIn(required, report)
        for digest in (
            "88cd3afdd25178808ddecb4b01c58e00e520bd67ab82dcf4ec6ba5b9856a16ae",
            "46d07a04f5b3455a6baf8f0ff95fb835b155aad3056af90013f31aeb300ee573",
            "552bd6b58c478f3ff17d59d4b5505d1941df0a9a3c28b4e8a788f25ccdeabe92",
            "349f8c2187a29339995ae0dddb392f874bd16ce4752238de2ba0fd2bf6f54144",
            "dafd58b804d3c7d907a063669cf62a941e87c21e5dc7b80e66e877a8768bc992",
            "040e3d9c39885328b9c833d68fbc772f70b7535889f629000cba653e52372e7f",
            "22b88556aa8ef7403828ea57c44179f6e2bba2912569207073908b827ddf5608",
        ):
            with self.subTest(digest=digest):
                self.assertIn(digest, report)

    def test_controlled_artifacts_are_verified_when_available(self):
        if not CONTROLLED_ARTIFACT_ROOT.is_dir():
            self.skipTest(f"controlled Toto artifact unavailable: {CONTROLLED_ARTIFACT_ROOT}")

        expected_hashes = {
            "m-a/result.json": "88cd3afdd25178808ddecb4b01c58e00e520bd67ab82dcf4ec6ba5b9856a16ae",
            "m-b/result.json": "46d07a04f5b3455a6baf8f0ff95fb835b155aad3056af90013f31aeb300ee573",
            "m-c/result.json": "552bd6b58c478f3ff17d59d4b5505d1941df0a9a3c28b4e8a788f25ccdeabe92",
            "m-d/result.json": "349f8c2187a29339995ae0dddb392f874bd16ce4752238de2ba0fd2bf6f54144",
            "acceptance/result.json": "dafd58b804d3c7d907a063669cf62a941e87c21e5dc7b80e66e877a8768bc992",
            "acceptance/summary.md": "040e3d9c39885328b9c833d68fbc772f70b7535889f629000cba653e52372e7f",
            "acceptance/.complete": "22b88556aa8ef7403828ea57c44179f6e2bba2912569207073908b827ddf5608",
        }
        for relative, expected in expected_hashes.items():
            path = CONTROLLED_ARTIFACT_ROOT / relative
            self.assertTrue(path.is_file(), path)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected, relative)

        acceptance = load_json(CONTROLLED_ARTIFACT_ROOT / "acceptance/result.json")
        self.assertEqual(acceptance["controlled_acceptance_status"], "pass")
        self.assertEqual(acceptance["analyzer_code_revision"]["head"], "336afae6e2e7edf80d8e0c3b0f4834e76a5ff257")
        self.assertFalse(acceptance["analyzer_code_revision"]["dirty"])
        self.assertEqual(acceptance["counts"], {"tracks": 4, "expected_cells": 80, "cells": 80, "expected_groups": 1920, "groups": 1920})
        self.assertEqual(len(acceptance["paired_deltas"]), 1440)
        self.assertFalse(acceptance["cross_model_ranking_allowed"])
        self.assertTrue(all(item["status"] == "paired" for item in acceptance["paired_deltas"]))
        self.assertTrue(all(item["ranking"] == "no-rank" and item["availability_delta"] == 0 for item in acceptance["paired_deltas"]))
        self.assertTrue(all(track["status"] == "pass" for track in acceptance["tracks"]))
        self.assertTrue(all(cell["status"] == "pass" for track in acceptance["tracks"] for cell in track["cells"]))
        self.assertTrue(all(group["status"] == "complete" for track in acceptance["tracks"] for cell in track["cells"] for group in cell["groups"]))

        marker = json.loads((CONTROLLED_ARTIFACT_ROOT / "acceptance/.complete").read_text(encoding="utf-8"))
        self.assertEqual(set(marker), {"marker_type", "result_sha256", "schema_version", "summary_sha256"})
        self.assertEqual(marker["marker_type"], "toto2-controlled-acceptance-complete")
        self.assertEqual(marker["result_sha256"], expected_hashes["acceptance/result.json"])
        self.assertEqual(marker["summary_sha256"], expected_hashes["acceptance/summary.md"])

        expected_matrix_ids = {"m-a": "toto2-ctl-a", "m-b": "toto2-ctl-b", "m-c": "toto2-ctl-c", "m-d": "toto2-ctl-d"}
        expected_runtime = {"m-a": 137.54, "m-b": 120.97, "m-c": 131.71, "m-d": 118.12}
        expected_peak_mib = {"m-a": 707.64, "m-b": 707.49, "m-c": 707.89, "m-d": 707.16}
        for matrix_name, matrix_id in expected_matrix_ids.items():
            matrix = load_json(CONTROLLED_ARTIFACT_ROOT / matrix_name / "result.json")
            self.assertEqual(matrix["matrix_id"], matrix_id)
            self.assertEqual(matrix["status"], "success")
            self.assertEqual(matrix["counts"], {"total_cells": 20, "successful_cells": 20, "partial_cells": 0, "failed_cells": 0, "completed_cells": 20})
            self.assertEqual(matrix["code_revision"]["head"], "336afae6e2e7edf80d8e0c3b0f4834e76a5ff257")
            results = list((CONTROLLED_ARTIFACT_ROOT / "bench" / matrix_id).rglob("result.json"))
            self.assertEqual(len(results), 20)
            values = [load_json(path) for path in results]
            self.assertEqual(sum(value["prediction_count"] for value in values), 10800)
            self.assertTrue(all(value["status"] == "success" and not value["failures"] for value in values))
            self.assertAlmostEqual(sum(value["runtime"]["total_seconds"] for value in values), expected_runtime[matrix_name], places=2)
            self.assertAlmostEqual(max(value["runtime"]["peak_memory_bytes"] for value in values) / (1024 ** 2), expected_peak_mib[matrix_name], places=2)

    def test_event_slice_report_pins_artifact_hashes_scope_and_limits(self):
        report = (ROOT / "docs/results/toto2-event-slices-2026-09-04.md").read_text(encoding="utf-8")
        required = (
            "statusは`success`",
            "8/8 cells analyzed",
            "excluded 0",
            "8,640",
            "3de9b683df25a871bcc1000f6a75ba21a301f55dad316cc15bc3675441959784",
            "832b9e088fccf5711eb31205b4848473111d38310953901842331023dcfd8e70",
            "973154dee1ca1b37a53cadf035d4e752b4ddbe09be125c7f06a1a4fe3027d826",
            "1c42926903bf3235ef8b86badf0491a5575b4060",
            "221e3bd7d5385f0446f7c32bb406baf876a87066",
            "clean` | 6,048",
            "other_signal_event` | 2,088",
            "target_event` | 504",
            "context_clean` | 1,080",
            "context_target_event` | 1,440",
            "context_covariate_event` | 3,060",
            "context_other_signal_event` | 3,060",
            "| 15 | 64 | 10 | 0.41415010607910185 | 0.4861204730542228 | 0.23458896053059908 | 1.0 | 1.4480838775634766 |",
            "| 15 | 120 | 10 | 0.6752031117675781 | 0.8066231182605325 | 0.32857936105550145 | 0.8 | 1.4139863967895507 |",
            "| 30 | 64 | 32 | 2.615565466388703 | 3.203644755407434 | 1.9790756186141971 | 0.3125 | 3.828602373600006 |",
            "| 30 | 120 | 32 | 3.4872136562347413 | 4.080344173064958 | 2.5833244569740295 | 0.25 | 5.113024294376373 |",
            "conveyor-01.motor_temperature",
            "motor-01-slip-test",
            "forecast timestampのcoverは0",
            "再推論なし",
            "[start,end)",
            "seed cell-macro",
            "anomaly detection性能",
            "missing／stale robustness",
            "commercial-evaluation",
            "Phase 2未完了",
            "evidence-completeness受入条件",
            "全cellでforecast-covered",
            "paired event-level bootstrap 95% CI",
            "昇格閾値はこのrunでは未定義",
            "toto2-matrix-2026-09-04.md",
        )
        for required_value in required:
            with self.subTest(required_value=required_value):
                self.assertIn(required_value, report)
        for linked in (
            "artifacts/toto2/matrix/benchmark-matrix-toto2-small/result.json",
            "artifacts/toto2/event-slices/benchmark-matrix-toto2-small/result.json",
        ):
            with self.subTest(linked=linked):
                self.assertIn(linked, report)
        evaluator_readme = (ROOT / "tools/evaluator/README.md").read_text(encoding="utf-8")
        schema = (ROOT / "schemas/benchmark-event-slice-result.schema.json").read_text(encoding="utf-8")
        self.assertIn("priority分類bucketに属したprediction rowと重なった全event ID", evaluator_readme)
        self.assertIn("Overlap provenance of all event IDs that overlap prediction rows in a priority classification bucket", schema)

    def test_event_slice_local_artifacts_are_checked_when_present(self):
        paths = {
            "source_matrix": ROOT / "artifacts/toto2/matrix/benchmark-matrix-toto2-small/result.json",
            "event_result": ROOT / "artifacts/toto2/event-slices/benchmark-matrix-toto2-small/result.json",
            "generated_summary": ROOT / "artifacts/toto2/event-slices/benchmark-matrix-toto2-small/summary.md",
        }
        missing = [name for name, path in paths.items() if not path.is_file()]
        if missing:
            self.skipTest("local Toto event-slice artifacts unavailable: " + ", ".join(missing))

        self.assertEqual(
            hashlib.sha256(paths["source_matrix"].read_bytes()).hexdigest(),
            "3de9b683df25a871bcc1000f6a75ba21a301f55dad316cc15bc3675441959784",
        )
        self.assertEqual(
            hashlib.sha256(paths["event_result"].read_bytes()).hexdigest(),
            "832b9e088fccf5711eb31205b4848473111d38310953901842331023dcfd8e70",
        )
        self.assertEqual(
            hashlib.sha256(paths["generated_summary"].read_bytes()).hexdigest(),
            "973154dee1ca1b37a53cadf035d4e752b4ddbe09be125c7f06a1a4fe3027d826",
        )

        event_result = json.loads(paths["event_result"].read_text(encoding="utf-8"))
        validate(event_result, load_json(ROOT / "schemas/benchmark-event-slice-result.schema.json"))
        self.assertEqual(event_result["status"], "success")
        self.assertEqual(event_result["matrix_result_path"], "artifacts/toto2/matrix/benchmark-matrix-toto2-small/result.json")
        self.assertEqual(event_result["source_matrix_sha256"], "3de9b683df25a871bcc1000f6a75ba21a301f55dad316cc15bc3675441959784")
        self.assertEqual(event_result["counts"], {
            "total_cells": 8,
            "analyzed_cells": 8,
            "excluded_cells": 0,
            "excluded_by_status": {"failed": 0},
            "total_prediction_count": 8640,
            "analyzed_prediction_count": 8640,
            "forecast_exposure_counts": {"clean": 6048, "other_signal_event": 2088, "target_event": 504},
            "context_exposure_counts": {"context_clean": 1080, "context_target_event": 1440, "context_covariate_event": 3060, "context_other_signal_event": 3060},
        })

        expected_metrics = {
            (15, 64): (10, 0.41415010607910185, 0.4861204730542228, 0.23458896053059908, 1.0, 1.4480838775634766),
            (15, 120): (10, 0.6752031117675781, 0.8066231182605325, 0.32857936105550145, 0.8, 1.4139863967895507),
            (30, 64): (32, 2.615565466388703, 3.203644755407434, 1.9790756186141971, 0.3125, 3.828602373600006),
            (30, 120): (32, 3.4872136562347413, 4.080344173064958, 2.5833244569740295, 0.25, 5.113024294376373),
        }
        target_rows = {
            (row["horizon"], row["context_length"]): row
            for row in event_result["macro_summary"]
            if row["dimension"] == "forecast_exposure"
            and row["exposure"] == "target_event"
            and row["model"] == "toto2"
            and row["target_signal_key"] == "motor_temperature"
        }
        self.assertEqual(set(target_rows), set(expected_metrics))
        for key, expected in expected_metrics.items():
            row = target_rows[key]
            self.assertEqual(row["total_point_count"], expected[0])
            for metric_name, expected_value in zip(("mae", "rmse", "wis", "nominal_interval_coverage", "interval_width"), expected[1:]):
                self.assertAlmostEqual(row["metrics"][metric_name]["mean"], expected_value, places=15)

        slip_coverage = []
        for cell in event_result["cells"]:
            matches = [item for item in cell["event_coverage"] if item["event_id"] == "motor-01-slip-test"]
            self.assertEqual(len(matches), 1)
            slip_coverage.append(matches[0])
        self.assertEqual(len(slip_coverage), 8)
        self.assertTrue(all(item["forecast_point_count"] == 0 for item in slip_coverage))
        self.assertTrue(all(item["covered_by_forecast_timestamp"] is False for item in slip_coverage))

    def test_matrix_report_records_artifact_provenance_metrics_and_next_gates(self):
        report = (ROOT / "docs/results/toto2-matrix-2026-09-04.md").read_text(encoding="utf-8")
        required = (
            "8/8 cell success",
            "partial 0",
            "failed 0",
            "1c42926903bf3235ef8b86badf0491a5575b4060",
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "3de9b683df25a871bcc1000f6a75ba21a301f55dad316cc15bc3675441959784",
            "78,629 bytes",
            "d683ff6ccc6d760ac7d1f5b09b0c7b648368cc15e5c8bb60cad1e7d0c5c62d21",
            "0bcdbf65e99f4b5ef62f309ebf517f0f59267ac0174ffa39e6d931a4eb896740",
            "ce464d618f923c10d9ed543e2f5ee54738b1f235088e9551733087532993eb16",
            "5ed5ca824e3fe21522c2f91e41ca1c037d1166de102dd887d5b8ff33f443a439",
            "h15: `[288, 363]`",
            "h30: `[288, 348]`",
            "test h15: `[384, 459]`",
            "test h30: `[384, 444]`",
            "8,640件",
            "1,440件",
            "32回",
            "0.06990157314809163",
            "0.6487267033140818",
            "1.278612267920939",
            "0.7135191171000164",
            "0.18535192643958195",
            "0.6237563177244398",
            "172.4390500166919",
            "1071.7355999950087",
            "1901.820460008457",
            "108.64316670005792 s",
            "741,568,512 bytes",
            "vibration_feature",
            "product-candidate",
            "seedを5以上",
            "22M",
            "Granite TTM",
        )
        for required_value in required:
            with self.subTest(required_value=required_value):
                self.assertIn(required_value, report)

        for path in (
            ROOT / "README.md",
            ROOT / "docs/toto2-notes.md",
            ROOT / "docs/research-roadmap.md",
            ROOT / "docs/research-implementation-plan.md",
            ROOT / "tools/toto2/README.md",
        ):
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path):
                self.assertIn("toto2-matrix-2026-09-04.md", text)
                self.assertNotIn("matrix未実施", text)
                self.assertNotIn("matrixの実測値・結果artifactはまだ作成していません", text)

    def test_invalid_or_unknown_toto_parameters_fail_closed_in_schema(self):
        config_path = ROOT / "examples/configs/benchmark-metropt3-toto2-4m.json"
        schema = load_json(ROOT / "schemas/benchmark-run-config.schema.json")
        base = load_json(config_path)
        invalid_parameters = (
            {"unknown": True},
            {"checkpoint_revision": "0" * 39 + "Z", "batch_size": 1, "device": "cpu", "local_files_only": True, "patch_size": 32},
            {"checkpoint_revision": "0" * 40, "batch_size": 2, "device": "cpu", "local_files_only": True, "patch_size": 32},
            {"checkpoint_revision": "0" * 40, "batch_size": 1, "device": "cuda", "local_files_only": True, "patch_size": 32},
            {"checkpoint_revision": "0" * 40, "batch_size": 1, "device": "cpu", "local_files_only": False, "patch_size": 32},
            {"checkpoint_revision": "0" * 40, "batch_size": 1, "device": "cpu", "local_files_only": True, "patch_size": 16},
        )
        for parameters in invalid_parameters:
            with self.subTest(parameters=parameters):
                invalid = {**base, "models": [{**base["models"][-1], "parameters": parameters}]}
                with self.assertRaises(ManifestValidationError):
                    validate(invalid, schema)
        invalid_policy = {**base, "models": [{**base["models"][-1], "quantile_policy": "validation-residual-by-lead"}]}
        with self.assertRaises(ManifestValidationError):
            validate(invalid_policy, schema)

    def test_evaluation_report_records_result_provenance_metrics_and_boundaries(self):
        report = (ROOT / "docs/results/toto2-metropt3-evaluation-2026-09-04.md").read_text(encoding="utf-8")
        required = (
            "結果は`success`",
            "prediction 4,320",
            "failure 0",
            "artifacts/toto2/cpu-smoke.json",
            "status=`pass`",
            "c696daf5ba58055d92607ccdbd5d47b775e24024",
            "e6210e4e48e05c025fc8895ddeddf0c53a49dc53fd1c2f49e8c3272a3c7b37b0",
            "context / horizon | 120分 / 15分",
            "128点、先頭8点の未観測padding",
            "past-only 11、known-future 0",
            "validation 16、test 16",
            "native `p10` / `p50` / `p90`",
            "5eb922f8162a800d6d31cffb10e3f4c079276b12c41e272129e5b4a930943f71",
            "0.2838531311307635",
            "0.976644075030372",
            "0.8562984656547269",
            "116.79421359999105",
            "584.8305000108667",
            "2391.030899991165",
            "752,611,328 bytes",
            "production=false",
            "control_write=false",
            "repo-root direct invocation",
            "既存cacheを用いて実成功",
            "automated subprocessでは全4 scriptについて",
            "`--help`でimport／CLI起動確認した",
            "accept flagからmainを経て`prepare_checkpoint`へ到達する経路",
            "`python -c`＋mockでdownloadなしに確認した",
            "CPU smoke artifactの`production=false`",
            "22M、matrix、fine-tuning",
        )
        for required_value in required:
            with self.subTest(required_value=required_value):
                self.assertIn(required_value, report)

        for path in (
            ROOT / "README.md",
            ROOT / "docs/toto2-notes.md",
            ROOT / "docs/research-roadmap.md",
            ROOT / "docs/research-implementation-plan.md",
            ROOT / "tools/toto2/README.md",
        ):
            with self.subTest(path=path):
                self.assertNotIn("実model benchmarkは未実施", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
