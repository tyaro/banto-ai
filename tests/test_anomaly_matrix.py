from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from banto_ai.anomaly_matrix import (
    AnomalyMatrixError,
    _load_object_snapshot,
    validate_anomaly_matrix_config,
)
from banto_ai.manifest import load_json, validate


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "examples" / "configs" / "anomaly-multiseed-v0.1.json"
SCHEMA_PATH = ROOT / "schemas" / "anomaly-multiseed-matrix-config.schema.json"


class AnomalyMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_json(CONFIG_PATH)
        cls.schema = load_json(SCHEMA_PATH)

    def _candidate(self, value: object, directory: Path) -> Path:
        path = directory / "candidate.json"
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path

    def _assert_invalid(self, mutate, directory: Path) -> None:
        candidate = copy.deepcopy(self.config)
        mutate(candidate)
        with self.assertRaises(AnomalyMatrixError):
            validate_anomaly_matrix_config(self._candidate(candidate, directory), ROOT)

    def test_happy_path_is_exact_deterministic_and_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory(prefix="anomaly-matrix-test-", dir=ROOT / "artifacts") as raw_dir:
            directory = Path(raw_dir)
            before = sorted(path.name for path in (ROOT / "artifacts").iterdir())
            first = validate_anomaly_matrix_config(CONFIG_PATH, ROOT)
            second = validate_anomaly_matrix_config(CONFIG_PATH, ROOT)
            after = sorted(path.name for path in (ROOT / "artifacts").iterdir())
        self.assertEqual(first, second)
        self.assertEqual(before, after)
        self.assertEqual(first["status"], "configuration_valid")
        self.assertEqual(first["run_status"], "not_run")
        self.assertEqual(first["performance_status"], "not_evaluated")
        self.assertEqual(first["counts"], {
            "cell_count": 120,
            "layout_count": 12,
            "event_count_per_seed": 48,
            "positive_event_count_per_seed": 24,
            "suppression_event_count_per_seed": 24,
            "positive_event_count_total": 240,
            "suppression_event_count_total": 240,
        })
        self.assertEqual(len(first["target_signal_ids"]), 8)
        validate(self.config, self.schema)

    def test_seeds_layouts_classes_mapping_slots_and_fixed_parameters_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="anomaly-matrix-test-", dir=ROOT / "artifacts") as raw_dir:
            directory = Path(raw_dir)
            invalid_mutations = (
                lambda value: value.update(seeds=[11, 17, 23, 29, 37, 42, 53, 67, 79, 98]),
                lambda value: value.update(seeds=list(reversed(value["seeds"]))),
                lambda value: value.update(seeds=value["seeds"] + [11]),
                lambda value: value["layouts"].pop(),
                lambda value: value["layouts"].append(copy.deepcopy(value["layouts"][0])),
                lambda value: value["layouts"][1].update(layout_id=value["layouts"][0]["layout_id"]),
                lambda value: value["layouts"][0]["events"].pop(),
                lambda value: value["layouts"][0]["events"][1].update(event_class="machine_fault"),
                lambda value: value["layouts"][0]["events"][0].update(event_type="spike"),
                lambda value: value["layouts"][0]["events"][0].update(start_offset_samples=9),
                lambda value: value["layouts"][0].update(mode_end_sample=749),
                lambda value: value["detector"].update(robust_z_threshold=5.0),
                lambda value: value["bootstrap"].update(resamples=9999),
                lambda value: value.update(base_generator_config_sha256="0" * 64),
                lambda value: value.update(schema_sha256="0" * 64),
                lambda value: value.update(output_root="artifacts/../outside"),
            )
            for mutate in invalid_mutations:
                self._assert_invalid(mutate, directory)

    def test_unknown_nested_duplicate_and_nonfinite_json_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="anomaly-matrix-test-", dir=ROOT / "artifacts") as raw_dir:
            directory = Path(raw_dir)
            unknown = copy.deepcopy(self.config)
            unknown["unexpected"] = True
            self._assert_invalid(lambda value: value.update(unexpected=True), directory)

            duplicate = directory / "duplicate.json"
            duplicate.write_text('{"schema_version":"0.1","schema_version":"0.1"}\n', encoding="utf-8")
            with self.assertRaises(AnomalyMatrixError):
                _load_object_snapshot(duplicate, "duplicate")

            nested_duplicate = directory / "nested-duplicate.json"
            nested_duplicate.write_text('{"detector":{"detection_grace_points":3,"detection_grace_points":4}}\n', encoding="utf-8")
            with self.assertRaises(AnomalyMatrixError):
                _load_object_snapshot(nested_duplicate, "nested duplicate")

            nonfinite = directory / "nonfinite.json"
            nonfinite.write_text('{"value":NaN}\n', encoding="utf-8")
            with self.assertRaises(AnomalyMatrixError):
                _load_object_snapshot(nonfinite, "nonfinite")

    def test_path_and_link_boundaries_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="anomaly-matrix-test-", dir=ROOT / "artifacts") as raw_dir:
            directory = Path(raw_dir)
            self._assert_invalid(lambda value: value.update(base_generator_config_path="C:/outside.json"), directory)
            self._assert_invalid(lambda value: value.update(schema_path="../schemas/other.json"), directory)
            link = directory / "config-link.json"
            try:
                os.symlink(CONFIG_PATH, link)
            except (OSError, NotImplementedError):
                link = None
            if link is not None:
                with self.assertRaises(AnomalyMatrixError):
                    validate_anomaly_matrix_config(link, ROOT)
            with patch("banto_ai.anomaly_matrix.os.path.isjunction", create=True, return_value=True):
                with self.assertRaises(AnomalyMatrixError):
                    validate_anomaly_matrix_config(CONFIG_PATH, ROOT)

    def test_cli_help_and_external_cwd_are_side_effect_free(self) -> None:
        with tempfile.TemporaryDirectory(prefix="anomaly-matrix-cwd-") as raw_dir:
            help_result = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "evaluator" / "validate_anomaly_matrix.py"), "--help"],
                cwd=raw_dir,
                capture_output=True,
                text=True,
                check=False,
            )
            run_result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools" / "evaluator" / "validate_anomaly_matrix.py"),
                    "--root",
                    str(ROOT),
                    "--config",
                    "examples/configs/anomaly-multiseed-v0.1.json",
                    "--format",
                    "text",
                ],
                cwd=raw_dir,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("--config", help_result.stdout)
        self.assertEqual(run_result.returncode, 0, run_result.stderr)
        self.assertIn("run=not_run", run_result.stdout)
        self.assertIn("performance=not_evaluated", run_result.stdout)


if __name__ == "__main__":
    unittest.main()
