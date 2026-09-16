"""Small local comparisons; no registered data generation or formal run."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from banto_ai import _anomaly_v03_contract as c
from banto_ai import _anomaly_v03_runtime as rt
from banto_ai import anomaly_v03_local_compare as compare
from banto_ai import anomaly_v03_local_preview as preview
from banto_ai import anomaly_v03_materializer as m
from tests.test_anomaly_v03_local_preview import hand_observations


class LocalCompareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory(prefix="banto-local-compare-tests-")
        cls.addClassCleanup(temporary.cleanup)
        cls.parent = Path(temporary.name)
        cls.raw = hand_observations()
        cls.source = cls.parent/"input.jsonl"
        cls.source.write_bytes(cls.raw)
        cls.results = []
        for index, candidate in enumerate(c.CANDIDATES):
            result = preview.run_local_preview(cls.source, cls.parent, f"candidate-{index}", candidate=candidate)
            receipt = result["receipt"]
            cls.results.append((Path(receipt["output_path"]), receipt["marker_raw_sha256"]))

    def test_partial_input_exposes_unavailability_and_does_not_count_it_as_agreement(self):
        before = {path: path.read_bytes() for root, _ in self.results for path in root.rglob("*") if path.is_file()}
        report = compare.compare_local_previews(self.results[:2])
        self.assertEqual(report["comparison_status"], "inconclusive")
        self.assertEqual(report["input"]["raw_sha256"], m.sha(self.raw))
        self.assertEqual(report["pairs"], [{"left": c.CANDIDATES[0], "right": c.CANDIDATES[1], "total": 20,
            "both_available": 0, "same_decision": 0, "different_decision": 0,
            "only_left_available": 16, "only_right_available": 0, "neither_available": 4}])
        self.assertEqual(report["candidates"][0]["score_counts"]["threshold_exceeded"], 2)
        self.assertIn("incomplete_normal_prefix", report["candidates"][0]["normal_prefix_issues"])
        self.assertEqual(report["performance_status"], "not_evaluated")
        self.assertFalse(report["formal_permission"])
        self.assertEqual(before, {path: path.read_bytes() for root, _ in self.results for path in root.rglob("*") if path.is_file()})

    def test_three_candidates_are_in_contract_order_regardless_of_argument_order(self):
        report = compare.compare_local_previews(self.results[::-1])
        self.assertEqual([item["candidate_id"] for item in report["candidates"]], list(c.CANDIDATES))
        self.assertEqual(len(report["pairs"]), 3)
        pair = report["pairs"][2]
        self.assertEqual(pair["neither_available"], 20)
        self.assertEqual(pair["same_decision"], 0)
        self.assertEqual(pair["different_decision"], 0)

    def test_pair_counts_separate_decision_agreement_from_each_availability_case(self):
        reports = [json.loads((root/"payload/preview.json").read_bytes()) for root, _ in self.results[:2]]
        left = {i: value for i, value in enumerate([(True, False), (True, True), (True, False), (True, True), (False, False), (False, False)])}
        right = {i: value for i, value in enumerate([(True, False), (True, True), (True, True), (False, False), (True, True), (False, False)])}
        with patch.object(compare, "_load_result", side_effect=[(reports[0], left), (reports[1], right)]):
            pair = compare.compare_local_previews(self.results[:2])["pairs"][0]
        self.assertEqual({name: pair[name] for name in ("total", "both_available", "same_decision", "different_decision", "only_left_available", "only_right_available", "neither_available")},
                         {"total": 6, "both_available": 3, "same_decision": 2, "different_decision": 1, "only_left_available": 1, "only_right_available": 1, "neither_available": 1})

    def test_different_observation_bytes_and_duplicate_candidates_are_rejected(self):
        rows = [json.loads(line) for line in self.raw.splitlines()]
        rows[0]["signals"]["motor_current"]["value"] += 0.5
        changed_source = self.parent/"changed-input.jsonl"
        changed_source.write_bytes(m.jsonl(rows))
        receipt = preview.run_local_preview(changed_source, self.parent, "different-input", candidate=c.CANDIDATES[1])["receipt"]
        with self.assertRaisesRegex(rt.IntegrityError, "inputs differ"):
            compare.compare_local_previews([self.results[0], (Path(receipt["output_path"]), receipt["marker_raw_sha256"])])
        with self.assertRaisesRegex(rt.IntegrityError, "duplicate comparison candidate"):
            compare.compare_local_previews([self.results[0], self.results[0]])

    def test_invalid_result_count_rejected_before_reading_and_bad_marker_rejected(self):
        with patch.object(compare, "_load_result", side_effect=AssertionError("unnecessary read")):
            for results in ([], self.results[:1], self.results+self.results[:1]):
                with self.assertRaisesRegex(rt.IntegrityError, "two or three"):
                    compare.compare_local_previews(results)
        for digest in ("bad", "0"*64):
            with self.subTest(digest=digest), self.assertRaises(ValueError):
                compare.compare_local_previews([(self.results[0][0], digest), self.results[1]])

    def test_modified_payload_is_rejected_instead_of_displaying_false_counts(self):
        receipt = preview.run_local_preview(self.source, self.parent, "modified")["receipt"]
        root = Path(receipt["output_path"])
        path = root/"payload/preview.json"
        report = json.loads(path.read_bytes())
        report["score_counts"]["threshold_exceeded"] = 0
        path.write_bytes(m.json_bytes(report))
        with self.assertRaises(ValueError):
            compare.compare_local_previews([(root, receipt["marker_raw_sha256"]), self.results[1]])

    def test_markdown_and_json_cli_and_failure_have_clear_output(self):
        entry = Path(__file__).resolve().parents[1]/"tools/evaluator/preview_anomaly_v03.py"
        args = [sys.executable, str(entry), "compare"]
        for root, digest in self.results[:2]:
            args.extend(["--result", str(root), digest])
        process = subprocess.run(args+["--format", "json"], capture_output=True, timeout=15)
        self.assertEqual(process.returncode, 0, process.stderr)
        report = json.loads(process.stdout)
        process = subprocess.run(args, capture_output=True, timeout=15)
        self.assertEqual(process.returncode, 0, process.stderr)
        # Console newline translation is platform dependent; content is stable.
        self.assertEqual(process.stdout.decode().replace("\r\n", "\n"), compare.comparison_markdown(report))
        self.assertIn("Unavailable is not a negative decision.", process.stdout.decode())
        self.assertIn("incomplete_normal_prefix", process.stdout.decode())
        failed = subprocess.run(args[:6], capture_output=True, timeout=15)
        self.assertEqual(failed.returncode, 2)
        self.assertEqual(failed.stdout, b"")
        self.assertEqual(json.loads(failed.stderr)["status"], "failed")


if __name__ == "__main__":
    unittest.main()
