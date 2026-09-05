from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import banto_ai.anomaly_matrix as anomaly_matrix
from banto_ai.anomaly_matrix import (
    AnomalyMatrixError,
    _load_object_snapshot,
    validate_anomaly_matrix_config,
)
from banto_ai.manifest import load_json, validate


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "examples" / "configs" / "anomaly-multiseed-v0.1.json"
SCHEMA_PATH = ROOT / "schemas" / "anomaly-multiseed-matrix-config.schema.json"
CONFIG_V02_PATH = ROOT / "examples" / "configs" / "anomaly-multiseed-v0.2.json"
SCHEMA_V02_PATH = ROOT / "schemas" / "anomaly-multiseed-matrix-config-v0.2.schema.json"


def _json_diff_paths(left: object, right: object, path: str = "") -> set[str]:
    if type(left) is not type(right):
        return {path}
    if isinstance(left, dict) and isinstance(right, dict):
        paths: set[str] = set()
        for key in set(left) | set(right):
            child = f"{path}.{key}" if path else key
            if key not in left or key not in right:
                paths.add(child)
            else:
                paths.update(_json_diff_paths(left[key], right[key], child))
        return paths
    if isinstance(left, list) and isinstance(right, list):
        paths: set[str] = set()
        if len(left) != len(right):
            paths.add(path)
        for index, (left_item, right_item) in enumerate(zip(left, right)):
            paths.update(_json_diff_paths(left_item, right_item, f"{path}[{index}]"))
        return paths
    return set() if left == right else {path}


class AnomalyMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_json(CONFIG_PATH)
        cls.schema = load_json(SCHEMA_PATH)

    def _candidate(self, value: object, directory: Path) -> Path:
        repository = directory / "repository"
        self._copy_matrix_inputs(repository)
        path = repository / "examples" / "configs" / "anomaly-multiseed-v0.1.json"
        path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        return path

    def _copy_matrix_inputs(self, repository: Path) -> None:
        (repository / "examples" / "configs").mkdir(parents=True, exist_ok=True)
        (repository / "schemas").mkdir(exist_ok=True)
        for relative in (
            "examples/configs/synthetic-anomaly-evaluation-v0.1.json",
            "schemas/synthetic-generator-config.schema.json",
            "schemas/anomaly-multiseed-matrix-config.schema.json",
            "schemas/anomaly-multiseed-matrix-config-v0.2.schema.json",
            "schemas/anomaly-multiseed-matrix-result.schema.json",
            "schemas/anomaly-multiseed-matrix-result-v0.2.schema.json",
        ):
            target = repository / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)

    def _assert_invalid(self, mutate, directory: Path) -> None:
        candidate = copy.deepcopy(self.config)
        mutate(candidate)
        with self.assertRaises(AnomalyMatrixError):
            path = self._candidate(candidate, directory)
            validate_anomaly_matrix_config(path, path.parents[2])

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
        self.assertEqual(first["canonicalization"], anomaly_matrix.CANONICALIZATION_ID)
        self.assertEqual(first["config_canonical_sha256"], anomaly_matrix.EXPECTED_CONFIG_CANONICAL_SHA256)
        self.assertEqual(first["base_generator_schema"]["canonical_sha256"], anomaly_matrix.EXPECTED_BASE_SCHEMA_CANONICAL_SHA256)
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

    def test_v02_profile_is_valid_and_only_changes_registered_identity_fields(self) -> None:
        v01_summary = validate_anomaly_matrix_config(CONFIG_PATH, ROOT)
        v02_summary = validate_anomaly_matrix_config(CONFIG_V02_PATH, ROOT)
        self.assertEqual(v01_summary["config_canonical_sha256"], anomaly_matrix.EXPECTED_CONFIG_CANONICAL_SHA256)
        self.assertEqual(v02_summary["config_canonical_sha256"], anomaly_matrix.EXPECTED_V02_CONFIG_CANONICAL_SHA256)
        self.assertEqual(v02_summary["schema"]["canonical_sha256"], anomaly_matrix.EXPECTED_V02_SCHEMA_CANONICAL_SHA256)
        self.assertEqual(v02_summary["config_canonical_sha256"], "3e206fc6c988850953d7ddd739a0504cb8cdd92f6726848b78ce4803461daa26")
        self.assertEqual(v02_summary["schema"]["canonical_sha256"], "fbd081961bfd8a56f3ac24514310f0a17f89c02174db44bfeb3fb6b3911f1c4d")
        self.assertEqual(v02_summary["matrix_id"], "anomaly-multiseed-v02")
        self.assertEqual(v02_summary["config_path"], "examples/configs/anomaly-multiseed-v0.2.json")
        self.assertEqual(v02_summary["schema"]["path"], "schemas/anomaly-multiseed-matrix-config-v0.2.schema.json")
        self.assertEqual(v02_summary["safety"]["output_root"], "artifacts/anomaly-multiseed-v02")
        self.assertEqual(v01_summary["counts"], v02_summary["counts"])
        self.assertEqual(v01_summary["fixed_parameters"], v02_summary["fixed_parameters"])
        self.assertEqual(v01_summary["layout_ids"], v02_summary["layout_ids"])
        validate(load_json(CONFIG_V02_PATH), load_json(SCHEMA_V02_PATH))

        v01 = load_json(CONFIG_PATH)
        v02 = load_json(CONFIG_V02_PATH)
        allowed_config_identity_diff = {"schema_version", "matrix_id", "schema_path", "schema_canonical_sha256", "output_root"}
        self.assertEqual(set(v01), set(v02))
        for key in v01:
            if key not in allowed_config_identity_diff:
                self.assertEqual(v01[key], v02[key], key)

        with tempfile.TemporaryDirectory(prefix="anomaly-matrix-profile-") as raw_repo:
            repository = Path(raw_repo)
            self._copy_matrix_inputs(repository)
            unknown_path = repository / "examples" / "configs" / "unknown.json"
            unknown_path.write_bytes(CONFIG_V02_PATH.read_bytes())
            with self.assertRaisesRegex(AnomalyMatrixError, "unknown matrix profile"):
                validate_anomaly_matrix_config(unknown_path, repository)

            v01_substitution = repository / "examples" / "configs" / "anomaly-multiseed-v0.1.json"
            v01_substitution.write_bytes(CONFIG_V02_PATH.read_bytes())
            with self.assertRaises(AnomalyMatrixError):
                validate_anomaly_matrix_config(v01_substitution, repository)

            v02_substitution = repository / "examples" / "configs" / "anomaly-multiseed-v0.2.json"
            v02_substitution.write_bytes(CONFIG_PATH.read_bytes())
            with self.assertRaises(AnomalyMatrixError):
                validate_anomaly_matrix_config(v02_substitution, repository)

    def test_v02_schema_lineage_changes_only_registered_identity_fields(self) -> None:
        self.assertEqual(_json_diff_paths(4.0, 4, "detector.robust_z_threshold"), {"detector.robust_z_threshold"})
        v01_config = load_json(CONFIG_PATH)
        v02_config = load_json(CONFIG_V02_PATH)
        self.assertEqual(
            _json_diff_paths(v01_config, v02_config),
            {"schema_version", "matrix_id", "schema_path", "schema_canonical_sha256", "output_root"},
        )

        v01_schema = load_json(SCHEMA_PATH)
        v02_schema = load_json(SCHEMA_V02_PATH)
        self.assertEqual(
            _json_diff_paths(v01_schema, v02_schema),
            {"$id", "title", "properties.schema_version.const", "properties.matrix_id.const"},
        )

        v01_result_schema = load_json(ROOT / "schemas" / "anomaly-multiseed-matrix-result.schema.json")
        v02_result_schema = load_json(ROOT / "schemas" / "anomaly-multiseed-matrix-result-v0.2.schema.json")
        self.assertEqual(
            _json_diff_paths(v01_result_schema, v02_result_schema),
            {"$id", "title", "properties.matrix_id.const"},
        )

    def test_seeds_layouts_classes_mapping_slots_and_fixed_parameters_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="anomaly-matrix-test-", dir=ROOT / "artifacts") as raw_dir:
            directory = Path(raw_dir)
            invalid_mutations = (
                lambda value: value.update(seeds=[11, 17, 23, 29, 37, 42, 53, 67, 79, 98]),
                lambda value: value.update(seeds=list(reversed(value["seeds"]))),
                lambda value: value.update(seeds=[11, 17, 23, 29, 37, 42, 53, 67, 79, 11]),
                lambda value: value["layouts"].pop(),
                lambda value: value["layouts"].append(copy.deepcopy(value["layouts"][0])),
                lambda value: value["layouts"][1].update(layout_id=value["layouts"][0]["layout_id"]),
                lambda value: value["layouts"][0]["events"].pop(),
                lambda value: value["layouts"][0]["events"][1].update(event_class="machine_fault"),
                lambda value: value["layouts"][0].update(events=[value["layouts"][0]["events"][1], value["layouts"][0]["events"][0], value["layouts"][0]["events"][2], value["layouts"][0]["events"][3]]),
                lambda value: value["layouts"][0]["events"][0].update(event_type="spike"),
                lambda value: value["layouts"][0]["events"][0].update(start_offset_samples=9),
                lambda value: value["layouts"][0].update(mode_end_sample=749),
                lambda value: value["detector"].update(robust_z_threshold=5.0),
                lambda value: value["bootstrap"].update(resamples=9999),
                lambda value: value.update(base_generator_config_canonical_sha256="0" * 64),
                lambda value: value.update(schema_canonical_sha256="0" * 64),
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

    def test_lf_and_crlf_have_same_canonical_identity(self) -> None:
        with tempfile.TemporaryDirectory(prefix="anomaly-matrix-repo-") as raw_repo:
            repository = Path(raw_repo)
            self._copy_matrix_inputs(repository)
            config_directory = repository / "examples" / "configs"
            lf_path = config_directory / "anomaly-multiseed-v0.1.json"
            lf_path.write_bytes((json.dumps(self.config, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
            crlf_raw = (json.dumps(self.config, ensure_ascii=False, indent=2) + "\n").replace("\n", "\r\n").encode("utf-8")
            lf_summary = validate_anomaly_matrix_config(lf_path, repository)
            lf_path.write_bytes(crlf_raw)
            crlf_summary = validate_anomaly_matrix_config(lf_path, repository)
        self.assertNotEqual(lf_summary["config_raw_sha256"], crlf_summary["config_raw_sha256"])
        self.assertEqual(lf_summary["config_canonical_sha256"], crlf_summary["config_canonical_sha256"])
        self.assertEqual(lf_summary["config_canonical_sha256"], anomaly_matrix.EXPECTED_CONFIG_CANONICAL_SHA256)

    def test_base_schema_snapshot_drift_and_completion_toctou_fail_closed(self) -> None:
        original = anomaly_matrix._load_object_snapshot

        def base_drift(path: Path, label: str):
            value, raw, raw_sha256, canonical_sha256 = original(path, label)
            if label == "base generator config":
                value = dict(value, sample_count=899)
                canonical_sha256 = hashlib.sha256(anomaly_matrix._canonical_json(value)).hexdigest()
            return value, raw, raw_sha256, canonical_sha256

        with patch.object(anomaly_matrix, "_load_object_snapshot", side_effect=base_drift):
            with self.assertRaises(AnomalyMatrixError):
                validate_anomaly_matrix_config(CONFIG_PATH, ROOT)

        def schema_drift(path: Path, label: str):
            value, raw, raw_sha256, canonical_sha256 = original(path, label)
            if label == "matrix config schema":
                value = dict(value, title="drifted schema")
                canonical_sha256 = hashlib.sha256(anomaly_matrix._canonical_json(value)).hexdigest()
            return value, raw, raw_sha256, canonical_sha256

        with patch.object(anomaly_matrix, "_load_object_snapshot", side_effect=schema_drift):
            with self.assertRaises(AnomalyMatrixError):
                validate_anomaly_matrix_config(CONFIG_PATH, ROOT)

        def base_schema_drift(path: Path, label: str):
            value, raw, raw_sha256, canonical_sha256 = original(path, label)
            if label == "base generator schema":
                value = dict(value, title="drifted base schema")
                canonical_sha256 = hashlib.sha256(anomaly_matrix._canonical_json(value)).hexdigest()
            return value, raw, raw_sha256, canonical_sha256

        with patch.object(anomaly_matrix, "_load_object_snapshot", side_effect=base_schema_drift):
            with self.assertRaises(AnomalyMatrixError):
                validate_anomaly_matrix_config(CONFIG_PATH, ROOT)

        def completion_toctou(path: Path, label: str):
            value, raw, raw_sha256, canonical_sha256 = original(path, label)
            if label == "matrix config completion snapshot":
                raw = raw + b" "
                raw_sha256 = hashlib.sha256(raw).hexdigest()
            return value, raw, raw_sha256, canonical_sha256

        with patch.object(anomaly_matrix, "_load_object_snapshot", side_effect=completion_toctou):
            with self.assertRaisesRegex(AnomalyMatrixError, "changed during validation"):
                validate_anomaly_matrix_config(CONFIG_PATH, ROOT)

    def test_completion_revalidates_input_paths_and_output_root(self) -> None:
        original = anomaly_matrix._safe_repo_path

        def input_path_drift(root: Path, value: object, label: str, *, must_exist: bool) -> Path:
            resolved = original(root, value, label, must_exist=must_exist)
            if label == "schema_path completion snapshot":
                return resolved.parent / "replaced-schema.json"
            return resolved

        with patch.object(anomaly_matrix, "_safe_repo_path", side_effect=input_path_drift):
            with self.assertRaisesRegex(AnomalyMatrixError, "matrix schema path changed"):
                validate_anomaly_matrix_config(CONFIG_PATH, ROOT)

        def output_junction(root: Path, value: object, label: str, *, must_exist: bool) -> Path:
            if label == "output_root completion snapshot":
                raise AnomalyMatrixError("output_root cannot traverse a symlink or junction")
            return original(root, value, label, must_exist=must_exist)

        with patch.object(anomaly_matrix, "_safe_repo_path", side_effect=output_junction):
            with self.assertRaisesRegex(AnomalyMatrixError, "output_root cannot traverse"):
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
