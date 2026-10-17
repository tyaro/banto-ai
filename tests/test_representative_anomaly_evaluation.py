"""Essential evaluation failures, without running registered observations."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
spec = importlib.util.spec_from_file_location("representative", ROOT / "tools/evaluator/run_representative_anomaly.py")
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)


class RepresentativeEvaluationTests(unittest.TestCase):
    def test_computation_failure_is_failed_not_success_and_stops_remaining_cell(self):
        identity = evaluation.v.evaluation_inventory("dev")[0]
        files = {n: b"fixture\n" for n in evaluation.m.DATASET_FILES}
        checkout = evaluation.rt.Checkout(ROOT, "a" * 40, ((evaluation.CONFIG_PATH, b"{}"),))
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts") as temporary:
            output = Path(temporary) / "failed-evaluation"
            with patch.object(evaluation, "load_input", return_value=(identity, files, {})), \
                 patch.object(evaluation, "capture_source", return_value=(checkout, [])), \
                 patch.object(evaluation, "source_unchanged"), \
                 patch.object(evaluation.resources, "memory_bytes", return_value={"peak_private_bytes": 1}), \
                 patch.object(evaluation.runner, "compute_evaluation", side_effect=ValueError("scorer failed")) as calculate:
                with self.assertRaisesRegex(ValueError, "scorer failed"):
                    evaluation.run(output, manifest_path="unused", manifest_sha256="a" * 64, dataset_id=identity["dataset_id"])
            manifest = json.loads((output / "manifest.json").read_bytes())
            self.assertEqual(manifest["status"], "failed")
            self.assertEqual(manifest["successful_cells"], 0)
            self.assertEqual([x["status"] for x in manifest["cells"]], ["failed", "not_started"])
            self.assertTrue(all(x["metrics"] is None for x in manifest["cells"]))
            self.assertEqual(calculate.call_count, 1)
            with self.assertRaises(FileExistsError):
                evaluation.run(output)

    def test_failed_completion_journal_does_not_count_as_success(self):
        identity = evaluation.v.evaluation_inventory("dev")[0]
        files = {n: b"fixture\n" for n in evaluation.m.DATASET_FILES}
        checkout = evaluation.rt.Checkout(ROOT, "a" * 40, ((evaluation.CONFIG_PATH, b"{}"),))
        result = {"identity": identity, "status": {"engineering_status": "pass"},
                  "input_hashes": {k: evaluation.pin(files[n])["sha256"] for k, n in evaluation.m.INPUT_FILES.items()},
                  "metrics": {}, "row_counts": {"scores": 1}}
        original_open = Path.open
        def fail_done(path, *args, **kwargs):
            if path.name == "cell-0-done.json":
                raise OSError("journal write failed")
            return original_open(path, *args, **kwargs)
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts") as temporary:
            output = Path(temporary) / "failed-journal"
            with patch.object(evaluation, "load_input", return_value=(identity, files, {})), \
                 patch.object(evaluation, "capture_source", return_value=(checkout, [])), \
                 patch.object(evaluation, "source_unchanged"), \
                 patch.object(evaluation.resources, "memory_bytes", return_value={"peak_private_bytes": 1}), \
                 patch.object(evaluation.runner, "compute_evaluation", return_value=result), \
                 patch.object(Path, "open", fail_done):
                with self.assertRaisesRegex(OSError, "journal write failed"):
                    evaluation.run(output, manifest_path="unused", manifest_sha256="a" * 64,
                                   dataset_id=identity["dataset_id"], candidates=[identity["candidate_id"]])
            manifest = json.loads((output / "manifest.json").read_bytes())
            self.assertEqual(manifest["status"], "failed")
            self.assertEqual(manifest["successful_cells"], 0)
            self.assertEqual(manifest["cells"][0]["status"], "failed")
            self.assertIsNone(manifest["cells"][0]["metrics"])
            self.assertTrue((output / "evaluation-0.json").is_file())

    def test_holdout_refused_before_observations_read(self):
        identity = evaluation.v.evaluation_inventory("holdout")[0]
        manifest = {"state": "complete", "datasets": [{"identity": identity, "files": []}]}
        with patch.object(evaluation.rt, "regular_path", return_value=ROOT / "unused.json"), \
             patch.object(evaluation, "pinned_json", return_value=manifest), \
             patch.object(evaluation, "read") as read:
            with self.assertRaisesRegex(evaluation.rt.IntegrityError, "holdout is not permitted"):
                evaluation.load_input(ROOT / "unused.json", "a" * 64, identity["dataset_id"])
            read.assert_not_called()

    def test_changed_replay_input_is_rejected_before_computation(self):
        identity = evaluation.v.evaluation_inventory("dev")[0]
        manifest = {"format": evaluation.FORMAT, "status": "complete", "identity": identity,
                    "input_files": {n: evaluation.pin(b"original") for n in evaluation.m.DATASET_FILES}}
        with patch.object(evaluation.rt, "regular_path", return_value=ROOT / "unused"), \
             patch.object(evaluation, "pinned_json", return_value=manifest), \
             patch.object(evaluation, "read", return_value=b"changed"):
            with self.assertRaisesRegex(evaluation.rt.IntegrityError, "replay input pin mismatch"):
                evaluation.replay_input(ROOT / "unused", "a" * 64)


if __name__ == "__main__":
    unittest.main()
