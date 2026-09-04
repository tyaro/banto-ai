import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PublicDataDocumentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.readme = (ROOT / "README.md").read_text(encoding="utf-8")
        cls.datasets = (ROOT / "datasets" / "README.md").read_text(encoding="utf-8")
        cls.survey = (ROOT / "docs" / "public-dataset-survey.md").read_text(encoding="utf-8")
        cls.adr = (ROOT / "docs" / "adr-0005-public-dataset-boundary.md").read_text(encoding="utf-8")
        cls.roadmap = (ROOT / "docs" / "research-roadmap.md").read_text(encoding="utf-8")
        cls.plan = (ROOT / "docs" / "research-implementation-plan.md").read_text(encoding="utf-8")
        cls.baseline_result = (ROOT / "docs" / "results" / "metropt3-baseline-evaluation-2026-09-04.md").read_text(encoding="utf-8")

    def test_required_documents_exist(self):
        for relative in (
            "docs/public-dataset-survey.md",
            "docs/adr-0005-public-dataset-boundary.md",
            "datasets/README.md",
            "docs/results/metropt3-baseline-evaluation-2026-09-04.md",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_metropt3_baseline_result_records_fixed_contract_and_scope(self):
        for fact in (
            "e6210e4e48e05c025fc8895ddeddf0c53a49dc53fd1c2f49e8c3272a3c7b37b0",
            "test prediction countは3,600",
            "validation / test = 15 / 15",
            "validation / test = 16 / 16",
            "past-only 11、known-future 0",
            "`validation-residual-by-lead`",
            "5 × 3 × 16 × 15 = 3,600",
            "Public-only quality gateはPASS",
            "CC BY 4.0",
            "異常検知性能を示さない",
            "known-future contractそのものは今回テストしていない",
            "Chronos-2とTimesFM 3.0",
            "b9b0a678f1ef9ef685dc450824a4705ff9881cf0",
            "detached clean worktree",
            "`code_revision.status`は`git`",
            "`code_revision.dirty`は`false`",
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "6894ecd0a24c057f13afcf505baa30a96b04a3d4203c6e24a964691d2c4520d0",
            "0.8732296999951359",
            "2.04535770000075",
            "16.17603400000371",
            "0.8707499946467578",
            "2.8196649916935708",
            "47255552",
            "Windows 11",
            "性能保証ではない",
        ):
            self.assertIn(fact, self.baseline_result)
        for model in ("last-value", "seasonal-naive", "moving-average", "ewma", "holt-linear"):
            self.assertIn(f"| {model} |", self.baseline_result)

    def test_official_sources_and_licenses_are_linked(self):
        for text in (self.survey, self.adr):
            self.assertIn("https://archive.ics.uci.edu/dataset/791/metropt%2B3%2Bdataset", text)
            self.assertIn("https://archive.ics.uci.edu/dataset/447/condition%2Bmonitoring%2Bof%2Bhydraulic%2Bsystems", text)
            self.assertIn("https://data.nasa.gov/dataset/cmapss-jet-engine-simulated-data", text)
        self.assertIn("https://doi.org/10.24432/C5VW3R", self.survey)
        self.assertIn("https://doi.org/10.24432/C5CW21", self.survey)
        self.assertIn("CC BY 4.0", self.survey)
        self.assertIn("License not specified", self.survey)

    def test_metro_evidence_preserves_uncertainty(self):
        self.assertIn("218,381,995 bytes", self.survey)
        for digest in (
            "aab991a970e58210de853bb8078ce0e63abb4d9412fdc5c79792dae3d8e1721a",
            "b00fac0e8899854078309bef4adaa480d82ecf14dc81c5097c3646973e824127",
            "db30ccb4ea402e3c8bf2c99db06e288d4f2a772f6928f9dbe26a920d69793e24",
        ):
            self.assertIn(digest, self.survey)
        self.assertRegex(self.survey, r"1 Hz.*0\.1 Hz|0\.1 Hz.*1 Hz")
        self.assertIn("timezone", self.survey)
        self.assertIn("UTC と断定しない", self.survey)
        self.assertIn("2020-02-21", self.survey)

    def test_boundary_is_external_and_fail_closed(self):
        for text in (self.survey, self.adr, self.datasets):
            self.assertIn("cache", text)
            self.assertIn("raw", text)
        self.assertIn("fail closed", self.survey)
        self.assertIn("fail closed", self.adr)
        self.assertIn("顧客", self.datasets)
        self.assertIn("補間せず", self.survey)

    def test_cmapss_is_rejected_without_unofficial_mirror(self):
        self.assertIn("C-MAPSS", self.survey)
        self.assertIn("License not specified", self.adr)
        self.assertIn("mirror", self.adr)
        self.assertNotRegex((self.survey + self.adr).lower(), r"kaggle|github\.com/.+cmapss")

    def test_source_pin_is_not_claimed_as_evaluation(self):
        combined = self.readme + self.roadmap + self.plan + self.survey + self.adr
        self.assertIn("source pin", combined)
        self.assertIn("cached_verified", combined)
        self.assertIn("verification_status", combined)
        self.assertIn("source pin tool", self.readme)
        self.assertIn("source pin", self.roadmap)
        self.assertIn("公開実データ評価", self.plan)
        self.assertIn("download／verify", self.adr)

    def test_readme_points_to_public_data_documents(self):
        self.assertIn("docs/public-dataset-survey.md", self.readme)
        self.assertIn("docs/adr-0005-public-dataset-boundary.md", self.readme)
        self.assertIn("MetroPT-3", self.readme)

    def test_verified_manifest_and_tool_are_linked(self):
        for text in (self.readme, self.survey, self.adr):
            self.assertIn("datasets/manifests/metropt3-source.json", text)
            self.assertIn("tools/public-data/README.md", text)
            self.assertIn("tools/public-data/prepare_metropt3.py", text)


if __name__ == "__main__":
    unittest.main()
