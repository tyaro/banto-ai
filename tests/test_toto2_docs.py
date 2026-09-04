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


if __name__ == "__main__":
    unittest.main()
