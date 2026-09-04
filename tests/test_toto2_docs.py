from pathlib import Path
import unittest

from banto_ai.manifest import ManifestValidationError, load_json, validate

ROOT = Path(__file__).resolve().parents[1]


class Toto2DocumentationTests(unittest.TestCase):
    def test_docs_record_fixed_artifacts_and_boundaries(self):
        combined = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "docs/toto2-notes.md", ROOT / "tools/toto2/README.md", ROOT / "README.md"))
        for required in ("toto-2==2.0.0", "toto-models==1.0.0", "8306a9801cf98c0f5ffe4b2dcc8f496e616d84d9", "16582848", "316660d5afb47943e531f39242e0b02ca0b8bb73be5709dfe07ca80dfce9805e", "commercial-evaluation", "decode_block_size=None", "padding", "known-future", "Git"):
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
            "--config examples/configs/benchmark-matrix-toto2-small.json",
            "8条件",
            "context=64はpaddingなし",
            "context=120はpatch_size=32に合わせて128点入力",
            "8/8 cell success、partial 0、failed 0",
            "docs/results/toto2-matrix-2026-09-04.md",
            "同じ共有Toto adapterを8セルで再利用",
        ):
            with self.subTest(required=required):
                self.assertIn(required, readme)
        self.assertNotIn(
            "--config examples\\configs\\benchmark-matrix-toto2-small.json", readme
        )

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
