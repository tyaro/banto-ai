"""TimesFM 3 execution documentation contract tests."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class TimesFM3DocumentationTests(unittest.TestCase):
    def test_metropt3_readme_fixes_procedure_and_safety_boundary(self):
        readme = (ROOT / "tools" / "timesfm3" / "README.md").read_text(encoding="utf-8")
        for required in (
            "benchmark-metropt3-timesfm3.json",
            "environments\\timesfm3\\.venv\\Scripts\\python.exe",
            "environments\\timesfm3\\requirements-windows-cpu-py314.lock",
            "preflight.py",
            "prepare_checkpoint.py",
            "run_benchmark.py",
            "C:\\banto-cache\\timesfm3",
            "research-only",
            "non-production",
            "partial",
            "sort",
            "clip",
            "fallback",
            "Banto Hub／PLC",
            "Git",
        ):
            with self.subTest(required=required):
                self.assertIn(required, readme)
        self.assertIn("必要な場合だけcheckpointを準備", readme)
        self.assertNotIn("評価完了", readme)

    def test_metropt3_result_records_exact_provenance_metrics_and_boundaries(self):
        report = (ROOT / "docs" / "results" / "timesfm3-metropt3-evaluation-2026-09-04.md").read_text(encoding="utf-8")
        for required in (
            "artifacts/benchmark/benchmark-metropt3-timesfm3",
            "2506a8d54c33558b0f2b793ffd7306fc86b021ac",
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "success",
            "status / failures",
            "`success` / 0",
            "4,320 = 6 models × 3 targets × 16 origins × 15 leads",
            "720 = 3 targets × 16 origins × 15 leads",
            "e6210e4e48e05c025fc8895ddeddf0c53a49dc53fd1c2f49e8c3272a3c7b37b0",
            "bb5e14e5371f97a507f69a3029a09e08c08a624dcbe9bbafa3e5a66d148bd899",
            "b78e7658c10ffa5fbd0fd8aa1139ea9189a4c768c5d335258b0c81d904ceb228",
            "0.30800515920396826",
            "0.8771395713563943",
            "0.8559598828544691",
            "48.28%（last-value）",
            "14.09%",
            "2118.109999995795 ms",
            "3907.7310250140727 ms",
            "2.773 GiB",
            "timesfm-non-commercial-license-v1.0",
            "research-only",
            "non-production",
            "Banto Hub／PLC write",
            "Git管理対象外",
            "sort、clip、fallbackは行っていない",
            "Chronos-2 nativeはquantile crossingにより`partial`",
            "CI `33851877697`",
        ):
            with self.subTest(required=required):
                self.assertIn(required, report)
        self.assertNotIn("次はTimesFM 3.0を同じMetroPT条件", report)

    def test_plans_and_chronos_report_no_longer_leave_timesfm_comparison_pending(self):
        paths = (
            ROOT / "README.md",
            ROOT / "docs" / "timesfm-notes.md",
            ROOT / "docs" / "chronos2-notes.md",
            ROOT / "docs" / "research-roadmap.md",
            ROOT / "docs" / "research-implementation-plan.md",
            ROOT / "docs" / "results" / "chronos2-metropt3-evaluation-2026-09-04.md",
        )
        combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        self.assertIn("timesfm3-metropt3-evaluation-2026-09-04.md", combined)
        for obsolete in (
            "次はTimesFM 3.0を同じMetroPT条件",
            "同じMetroPT条件でのTimesFM 3.0比較。",
            "TimesFM 3.0の公開実データ評価は未実施",
        ):
            with self.subTest(obsolete=obsolete):
                self.assertNotIn(obsolete, combined)
        self.assertIn("Phase 2は未完了", combined)


if __name__ == "__main__":
    unittest.main()
