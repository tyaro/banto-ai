from pathlib import Path
import unittest


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


if __name__ == "__main__":
    unittest.main()
