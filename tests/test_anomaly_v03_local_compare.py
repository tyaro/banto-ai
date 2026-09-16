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


def detail_score(sample, available, exceeded):
    return compare._Score(available, exceeded, c.START_MS+sample*1000,
                          7.123456789012345 if available and exceeded else 0.0 if available else None,
                          1.25 if available else None, sample % 30, c.MODES[0], c.RECIPES[0],
                          () if available else ("profile_unavailable",))


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
        left = {(c.FULL_TARGETS[0], 7201+i): detail_score(7201+i, *value) for i, value in enumerate([(True, False), (True, True), (True, False), (True, True), (False, False), (False, False)])}
        right = {(c.FULL_TARGETS[0], 7201+i): detail_score(7201+i, *value) for i, value in enumerate([(True, False), (True, True), (True, True), (False, False), (True, True), (False, False)])}
        with patch.object(compare, "_load_result", side_effect=[(reports[0], left, self.raw), (reports[1], right, None)]):
            report = compare.compare_local_previews(self.results[:2])
        pair = report["pairs"][0]
        self.assertEqual({name: pair[name] for name in ("total", "both_available", "same_decision", "different_decision", "only_left_available", "only_right_available", "neither_available")},
                         {"total": 6, "both_available": 3, "same_decision": 2, "different_decision": 1, "only_left_available": 1, "only_right_available": 1, "neither_available": 1})
        self.assertEqual(report["details"]["total"], 3)
        self.assertEqual([row["sample"] for row in report["details"]["rows"]], [7203, 7204, 7205])
        self.assertEqual([row["difference_kinds"] for row in report["details"]["rows"]], [["threshold_decision"], ["availability"], ["availability"]])
        unavailable = report["details"]["rows"][1]["candidates"][1]
        self.assertEqual(unavailable["decision"], "unavailable")
        self.assertIsNone(unavailable["score"])
        self.assertEqual(unavailable["exclusion_tags"], ["profile_unavailable"])

    def test_three_candidate_differences_are_unique_rows_not_a_sum_of_pair_counts(self):
        reports = [json.loads((root/"payload/preview.json").read_bytes()) for root, _ in self.results]
        states = [((True, True), (True, True)), ((True, False), (True, False)), ((True, False), (False, False))]
        maps = [{(c.FULL_TARGETS[0], 7201+i): detail_score(7201+i, *value) for i, value in enumerate(values)} for values in states]
        with patch.object(compare, "_load_result", side_effect=[(report, rows, self.raw if index == 0 else None) for index, (report, rows) in enumerate(zip(reports, maps))]):
            report = compare.compare_local_previews(self.results)
        self.assertEqual(report["details"]["total"], 2)
        self.assertEqual(sum(pair["different_decision"] for pair in report["pairs"]), 3)
        self.assertEqual(report["details"]["rows"][1]["difference_kinds"], ["threshold_decision", "availability"])
        markdown = compare.comparison_markdown(report)
        self.assertIn("2026-01-01T02:00:01.000Z", markdown)
        self.assertIn("7.123456789012345", markdown)
        self.assertIn("| unavailable | n/a | n/a |", markdown)

    def test_details_page_is_stable_and_matches_saved_scores_without_changing_totals(self):
        report = compare.compare_local_previews(self.results[:2], details_offset=1, details_limit=2)
        details = report["details"]
        self.assertEqual({key: details[key] for key in ("total", "offset", "limit", "shown", "omitted_before", "omitted_after")},
                         {"total": 16, "offset": 1, "limit": 2, "shown": 2, "omitted_before": 1, "omitted_after": 13})
        self.assertEqual([(row["sample"], row["full_target"]) for row in details["rows"]],
                         [(7201, "motor-01.motor_current"), (7201, "motor-01.motor_temperature")])
        self.assertEqual(report["pairs"][0]["total"], 20)
        for index, (root, _) in enumerate(self.results[:2]):
            saved = {(row["sample"], row["full_target"]): row for row in (json.loads(line) for line in (root/"payload/scores.jsonl").read_bytes().splitlines())}
            for row in details["rows"]:
                source = saved[row["sample"], row["full_target"]]
                shown = row["candidates"][index]
                self.assertEqual(row["timestamp_ms"], source["timestamp_ms"])
                for key in ("available", "score", "residual", "phase", "mode", "recipe", "exclusion_tags"):
                    self.assertEqual(shown[key], source[key])
        reverse = compare.compare_local_previews(self.results[:2][::-1], details_offset=1, details_limit=2)
        self.assertEqual(reverse, report)

    def test_empty_pages_distinguish_hidden_differences_from_no_differences(self):
        for limit, offset, expected_before, expected_after in ((0, 0, 0, 16), (2, 99, 16, 0)):
            report = compare.compare_local_previews(self.results[:2], details_limit=limit, details_offset=offset)
            details = report["details"]
            self.assertEqual((details["total"], details["shown"], details["omitted_before"], details["omitted_after"]),
                             (16, 0, expected_before, expected_after))
            self.assertEqual(details["rows"], [])
        report = compare.compare_local_previews(self.results[1:])
        self.assertEqual(report["details"]["total"], 0)
        self.assertIn("Unique sample/target differences: 0", compare.comparison_markdown(report))
        del report["details"]
        self.assertNotIn("## Difference details", compare.comparison_markdown(report))

    def test_detail_bounds_rejected_before_reading_results(self):
        with patch.object(compare, "_load_result", side_effect=AssertionError("unnecessary read")):
            for args in ({"details_limit": -1}, {"details_limit": 101}, {"details_limit": True}, {"details_limit": 1.5},
                         {"details_offset": -1}, {"details_offset": True}, {"details_offset": 1.5}):
                with self.subTest(args=args), self.assertRaises(rt.IntegrityError):
                    compare.compare_local_previews(self.results, **args)

    def test_observation_context_preserves_all_four_signals_and_c0_input_difference(self):
        report = compare.compare_local_previews(self.results[:2], details_offset=5, details_limit=1)
        detail = report["details"]["rows"][0]
        self.assertEqual((detail["sample"], detail["full_target"]), (7202, "motor-01.motor_current"))
        context = detail["observations"]
        self.assertEqual([row["relation"] for row in context], ["previous", "current", "next"])
        self.assertEqual([row["sample"] for row in context], [7201, 7202, 7203])
        saved = {row["timestamp"]: row for row in (json.loads(line) for line in self.raw.splitlines())}
        for row in context:
            source = saved[f"2026-01-01T02:00:{row['sample']-7200:02d}.000Z"]
            self.assertTrue(row["present"])
            self.assertEqual(row["timestamp_ms"], c.START_MS+row["sample"]*1000)
            self.assertEqual((row["mode"], row["recipe"]), (source["operating_mode"], source["recipe_step"]))
            self.assertEqual([item["full_target"] for item in row["signals"]], ["motor-01."+target for target in c.TARGETS])
            for item, target in zip(row["signals"], c.TARGETS):
                self.assertEqual((item["value"], item["unit"], item["quality"]),
                                 (source["signals"][target]["value"], source["signals"][target]["unit"], source["quality"][target]))
        self.assertAlmostEqual(context[1]["signals"][0]["value"]-context[0]["signals"][0]["value"], detail["candidates"][0]["residual"])
        self.assertIn("Next is inspection only", compare.comparison_markdown(report))
        del detail["observations"]
        self.assertIn("### Sample 7202", compare.comparison_markdown(report))
        self.assertNotIn("Saved observations", compare.comparison_markdown(report))

    def test_context_uses_exact_equipment_times_and_keeps_missing_rows_distinct_from_null_values(self):
        source = [json.loads(line) for line in self.raw.splitlines()]
        raw_rows = [json.loads(m.json_bytes(row)) for row in source]
        current = next(row for row in raw_rows if row["timestamp"] == "2026-01-01T02:00:02.000Z")
        current["signals"]["motor_temperature"]["value"] = None
        current["quality"]["motor_temperature"] = "missing"
        current["signals"]["motor_current"]["unit"] = "A|<b>\n[x](link)_unit"
        # Another equipment at the timestamp must not fill a later test gap.
        other = json.loads(m.json_bytes(source[-4]))
        other["equipment_id"], other["equipment_type"] = "conveyor-01", "conveyor"
        raw_rows.append(other)
        raw = m.jsonl(raw_rows)
        source_path = self.parent/"context-input.jsonl"
        source_path.write_bytes(raw)
        roots = []
        for index, candidate in enumerate(c.CANDIDATES[:2]):
            receipt = preview.run_local_preview(source_path, self.parent, f"context-{index}", candidate=candidate)["receipt"]
            roots.append((Path(receipt["output_path"]), receipt["marker_raw_sha256"]))
        # The source filename is not consulted once publication has saved it.
        source_path.write_bytes(b"changed after saving\n")
        report = compare.compare_local_previews(roots)
        detail = next(row for row in report["details"]["rows"] if row["sample"] == 7203 and row["full_target"] == "motor-01.motor_current")
        self.assertEqual(detail["observations"][0]["signals"][1]["value"], None)
        self.assertEqual(detail["observations"][0]["signals"][1]["quality"], "missing")
        # A gap resets scoring phase, so check gap display independently of the
        # intact-phase comparison above. Do not substitute earlier samples.
        gap_raw = m.jsonl([row for row in raw_rows if not (row["equipment_id"] == "motor-01" and row["timestamp"] == "2026-01-01T02:00:01.000Z")])
        preview.scoring.decode_saved_observations(gap_raw, expected_sha256=m.sha(gap_raw))
        boundaries = [{"sample":7202,"full_target":"motor-01.motor_current"}, {"sample":7204,"full_target":"motor-01.motor_current"}]
        compare._attach_observation_context(gap_raw, boundaries)
        self.assertFalse(boundaries[0]["observations"][0]["present"])
        self.assertEqual(boundaries[0]["observations"][0]["signals"], [])
        self.assertTrue(boundaries[0]["observations"][1]["present"])
        self.assertFalse(boundaries[1]["observations"][2]["present"])
        text = "\n".join(compare._observations_markdown(boundaries[0]["observations"]))
        self.assertIn("observation absent", text)
        self.assertIn("| null | hand-fixture | missing |", text)
        self.assertIn("A&#124;&lt;b&gt;<br>", text)
        self.assertNotIn("A|<b>", text)

    def test_no_details_skip_context_parsing_and_only_one_verified_snapshot_is_retained(self):
        with patch.object(compare, "_load_result", wraps=compare._load_result) as load:
            compare.compare_local_previews(self.results[:2], details_limit=1)
        self.assertEqual([call.kwargs["keep_observations"] for call in load.call_args_list], [True, False])
        with patch.object(compare, "_load_result", wraps=compare._load_result) as load:
            report = compare.compare_local_previews(self.results[:2], details_limit=0)
        self.assertEqual([call.kwargs["keep_observations"] for call in load.call_args_list], [False, False])
        self.assertEqual(report["details"]["rows"], [])
        compare._attach_observation_context(None, [])

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
        detail_args = ["--details-offset", "1", "--details-limit", "2"]
        process = subprocess.run(args+detail_args+["--format", "json"], capture_output=True, timeout=15)
        self.assertEqual(process.returncode, 0, process.stderr)
        report = json.loads(process.stdout)
        self.assertEqual(report["details"]["shown"], 2)
        self.assertEqual(report["details"]["offset"], 1)
        process = subprocess.run(args+detail_args, capture_output=True, timeout=15)
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
