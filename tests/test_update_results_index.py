import tempfile
import unittest
import os
import subprocess
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from update_results_index import prepare_result_index

ROOT = Path(__file__).resolve().parents[1]

class ResultIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "artifacts")
        self.addCleanup(self.temp.cleanup)
        self.docs = Path(self.temp.name) / "docs"
        self.index = self.docs / "results/README.md"
        self.index.parent.mkdir(parents=True)
        self.existing = self.index.parent / "existing.md"
        self.existing.write_bytes(b"# existing\n")
        self.original = ("# index\n\n## v0.3の少量devモデル評価（46件）\n\n"
                         "- [existing](existing.md)\n\n## history\n\nkeep\n").encode()
        self.index.write_bytes(self.original)

    def prepare(self, report, title="new", **kwargs):
        return prepare_result_index(self.index, report, title, docs_root=self.docs, **kwargs)

    def test_moved_report_uses_relative_encoded_path_and_counts_entries(self):
        report = self.docs / "anomaly/evaluation/新 報告(1).md"
        updated = self.prepare(report, pending_report="# 日本語\n".encode())
        self.assertIn("## v0.3の少量devモデル評価（2件）".encode(), updated)
        self.assertIn(b"../anomaly/evaluation/%E6%96%B0%20%E5%A0%B1%E5%91%8A%281%29.md", updated)
        self.assertTrue(updated.endswith(b"## history\n\nkeep\n"))
        self.assertEqual(self.index.read_bytes(), self.original)
        self.assertFalse(report.exists())

    def test_existing_link_is_idempotent_and_repairs_stale_count(self):
        updated = self.prepare(self.existing, "existing")
        self.assertIn("（1件）".encode(), updated)
        self.index.write_bytes(updated)
        self.assertEqual(self.prepare(self.existing, "existing"), updated)
        self.assertEqual(updated.count(b"](existing.md)"), 1)

    def test_section_missing_or_ambiguous_fails_before_any_write(self):
        for content in (b"# missing\n", self.original + self.original):
            self.index.write_bytes(content)
            with self.assertRaises(ValueError):
                self.prepare(self.existing, "existing")
            self.assertEqual(self.index.read_bytes(), content)

    def test_duplicate_or_conflicting_link_fails_before_any_write(self):
        cases = [self.original.replace(b"## history", b"- [again](./existing.md)\n\n## history"),
                 self.original, self.original.replace(b"[existing]", b"[new]")]
        reports = [self.existing, self.existing, self.docs / "new.md"]
        titles = ["existing", "different", "new"]
        for content, report, title in zip(cases, reports, titles):
            self.index.write_bytes(content)
            with self.assertRaises(ValueError):
                self.prepare(report, title, **({"pending_report": b"# new"} if not report.exists() else {}))
            self.assertEqual(self.index.read_bytes(), content)

    def test_pending_report_requires_absent_path_and_valid_utf8(self):
        for report, raw, error in [(self.existing, b"# replace", FileExistsError),
                                   (self.docs / "new.md", b"\xff", UnicodeDecodeError),
                                   (Path(self.temp.name) / "outside.md", b"# new", ValueError)]:
            with self.assertRaises(error):
                self.prepare(report, pending_report=raw)
            self.assertEqual(self.index.read_bytes(), self.original)

    def test_malformed_or_external_report_links_are_rejected(self):
        for link in (b"- broken", b"- [external](https://example.com/report.md)"):
            content = self.original.replace(b"- [existing](existing.md)", link)
            self.index.write_bytes(content)
            with self.assertRaises(ValueError):
                self.prepare(self.existing, "existing")
            self.assertEqual(self.index.read_bytes(), content)

    def test_cli_diff_is_utf8_from_other_cwd_and_never_writes_index(self):
        report = self.docs / "new.md"
        report.write_bytes(b"# new\n")
        result = subprocess.run([
            sys.executable, "-B", str(ROOT / "tools/update_results_index.py"),
            "--index", str(self.index), "--report", str(report),
            "--title", "新🙂", "--docs-root", str(self.docs), "--check",
        ], cwd=self.temp.name, env={**os.environ, "PYTHONIOENCODING": "ascii"},
            capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("新🙂".encode("utf-8"), result.stdout)
        self.assertEqual(self.index.read_bytes(), self.original)

    def test_empty_section_keeps_blank_lines_between_heading_list_and_next_heading(self):
        self.index.write_bytes(b"# index\n\n## maintenance\n\n## history\n\nkeep\n")
        updated = self.prepare(self.existing, "existing", section="maintenance")
        self.assertEqual(updated, ("# index\n\n## maintenance（1件）\n\n"
                                   "- [existing](existing.md)\n\n## history\n\nkeep\n").encode())


if __name__ == "__main__":
    unittest.main()
