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


if __name__ == "__main__":
    unittest.main()
