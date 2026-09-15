"""Small algebraic observations; no registered seed or campaign data generation."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from banto_ai import _anomaly_v03_contract as c
from banto_ai import _anomaly_v03_runtime as rt
from banto_ai import anomaly_v03_local_preview as preview
from banto_ai import anomaly_v03_materializer as m
from banto_ai import anomaly_v03_scoring as scoring


def hand_observations():
    # Ten short calibration visits, then five test origins. Deliberately partial.
    samples = [sample for base in range(5400, 7200, 180) for sample in range(base-1, base+30)]
    samples.extend(range(7199, 7205))
    rows = []
    for sample in samples:
        mode, phase = (sample % 180)//30, sample % 30
        values = [round(100+i*10+phase+(0.0, 0.1, -0.1, 0.2)[phase % 4], 6) for i in range(4)]
        if sample == 7202:
            values[0] += 15.0
        timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)+timedelta(seconds=sample)
        rows.append({"timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%S.000Z"), "equipment_id": "motor-01",
                     "equipment_type": "motor", "operating_mode": c.MODES[mode], "recipe_step": c.RECIPES[mode],
                     "signals": {target: {"value": value, "unit": "hand-fixture"} for target, value in zip((*c.TARGETS, "load_proxy"), (*values, 0.0))},
                     "quality": dict.fromkeys((*c.TARGETS, "load_proxy"), "ok")})
    return m.jsonl(rows)


class LocalPreviewTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="banto-local-preview-tests-")
        self.addCleanup(temporary.cleanup)
        self.parent = Path(temporary.name)
        self.raw = hand_observations()
        self.source = self.parent/"input.jsonl"
        self.source.write_bytes(self.raw)

    def test_c0_calculates_known_residual_and_keeps_incomplete_input_visible(self):
        payloads = preview.build_preview_payloads(self.raw, c.CANDIDATES[0])
        report = json.loads(payloads["preview.json"])
        scores = [json.loads(line) for line in payloads["scores.jsonl"].splitlines()]
        self.assertEqual(report["input"]["rows"], 316)
        self.assertEqual(report["calibrated_profiles"], 4)
        self.assertEqual(report["score_counts"], {"total": 20, "available": 16, "unavailable": 4, "threshold_exceeded": 2})
        self.assertEqual(report["preview_status"], "inconclusive")
        self.assertIn("incomplete_normal_prefix", report["normal_prefix_issues"])
        current = next(row for row in scores if row["sample"] == 7202 and row["full_target"] == "motor-01.motor_current")
        self.assertAlmostEqual(current["residual"], 15.8)
        self.assertAlmostEqual(current["score"], (15.8-1.1)/(1.4826*0.2), places=8)
        self.assertTrue(current["threshold_exceeded"])
        self.assertFalse(any({"score_id", "dataset_id", "profile_id", "source_episode_id"} & set(row) for row in scores))
        self.assertFalse(report["formal_permission"])

    def test_c1_and_c2_keep_unavailable_scores_without_inventing_fit_data(self):
        for candidate in c.CANDIDATES[1:]:
            with self.subTest(candidate=candidate):
                report = json.loads(preview.build_preview_payloads(self.raw, candidate)["preview.json"])
                self.assertEqual(report["calibrated_profiles"], 0)
                self.assertEqual(report["score_counts"]["total"], 20)
                self.assertEqual(report["score_counts"]["unavailable"], 20)
                self.assertEqual(report["preview_status"], "inconclusive")

    def test_pipeline_saves_input_snapshot_and_recomputes_after_source_changes(self):
        result = preview.run_local_preview(self.source, self.parent, "saved")
        self.source.write_bytes(b"original source changed after saving\n")
        root = Path(result["receipt"]["output_path"])
        self.assertEqual((root/"payload"/"observations.jsonl").read_bytes(), self.raw)
        verified = preview.verify_local_preview(root, marker_sha256=result["receipt"]["marker_raw_sha256"])
        self.assertEqual(verified["preview"], result["preview"])
        self.assertEqual(verified["verification"]["payloads"], 4)
        with self.assertRaisesRegex(rt.IntegrityError, "s4_acceptance_not_frozen"):
            rt.require_campaign_acceptance()

    def test_duplicate_output_rejected_before_reading_or_calculating(self):
        preview.run_local_preview(self.source, self.parent, "same")
        with patch.object(preview, "_read_input", side_effect=AssertionError("duplicate input read")), \
                patch.object(preview, "build_preview_payloads", side_effect=AssertionError("duplicate calculation")):
            with self.assertRaises(FileExistsError):
                preview.run_local_preview(self.source, self.parent, "same")

    def test_summary_counts_and_scores_must_match_recalculation(self):
        original = preview.build_preview_payloads(self.raw, c.CANDIDATES[0])
        for path in ("preview.json", "scores.jsonl", "summary.md"):
            with self.subTest(path=path):
                files = dict(original)
                if path == "preview.json":
                    report = json.loads(files[path]); report["score_counts"]["available"] += 1
                    files[path] = m.json_bytes(report)
                else:
                    files[path] += b"extra\n"
                with self.assertRaisesRegex(rt.IntegrityError, "recomputation"):
                    preview._verify_payloads(files)

    def test_changed_calculation_during_publication_leaves_no_marker(self):
        original = scoring.preview_saved_observations
        calls = []
        def changed(*args, **kwargs):
            result = original(*args, **kwargs)
            calls.append(None)
            if len(calls) > 1:
                result = copy.deepcopy(result)
                result["scores"][4]["score"] = 123.0
            return result
        with patch.object(scoring, "preview_saved_observations", side_effect=changed), \
                self.assertRaisesRegex(rt.IntegrityError, "recomputation"):
            preview.run_local_preview(self.source, self.parent, "changed")
        self.assertFalse((self.parent/"changed"/".complete").exists())

    def test_bad_input_and_resource_limits_do_not_produce_a_completed_result(self):
        for raw in (b"", b"{}\n", self.raw[:-1], b"not-json\n"):
            with self.subTest(raw=raw[:10]), self.assertRaises(ValueError):
                preview.build_preview_payloads(raw, c.CANDIDATES[0])
        with patch.object(preview, "MAX_INPUT_BYTES", 16), \
                patch.object(scoring, "preview_saved_observations", side_effect=AssertionError("over-budget calculation")):
            with self.assertRaises(rt.IntegrityError):
                preview.run_local_preview(self.source, self.parent, "oversized")
        self.assertFalse((self.parent/"oversized"/".complete").exists())
        with patch.object(preview, "MAX_INPUT_ROWS", 2), self.assertRaises(rt.IntegrityError):
            preview.build_preview_payloads(self.raw, c.CANDIDATES[0])
        with self.assertRaises(ValueError):
            preview.run_local_preview(self.source, self.parent, "unknown", candidate="other")
        self.assertFalse((self.parent/"unknown").exists())

    def test_cli_run_and_sequential_verify(self):
        entry = Path(__file__).resolve().parents[1]/"tools/evaluator/preview_anomaly_v03.py"
        run = subprocess.run([sys.executable, str(entry), "run", "--observations", str(self.source),
                              "--output-parent", str(self.parent), "--name", "cli"], capture_output=True, timeout=15)
        self.assertEqual(run.returncode, 0, run.stderr.decode(errors="replace"))
        receipt = json.loads(run.stdout)["receipt"]
        verified = subprocess.run([sys.executable, str(entry), "verify", "--output", receipt["output_path"],
                                   "--marker-sha256", receipt["marker_raw_sha256"]], capture_output=True, timeout=15)
        self.assertEqual(verified.returncode, 0, verified.stderr.decode(errors="replace"))
        self.assertTrue(json.loads(verified.stdout)["verification"]["local_verified"])


if __name__ == "__main__":
    unittest.main()
