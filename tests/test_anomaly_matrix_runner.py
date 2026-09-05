from __future__ import annotations

import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import banto_ai.anomaly_matrix_runner as runner_module
from banto_ai.anomaly_evaluation import AnomalyEvaluationError, _canonical_json, _evaluate_core
from banto_ai.anomaly_matrix_runner import AnomalyMatrixRunnerError, run_anomaly_matrix
from banto_ai.generator import FINGERPRINT_ALGORITHM, FINGERPRINT_CANONICALIZATION, FINGERPRINT_FILE_NAMES, generate_synthetic
from banto_ai.manifest import ManifestValidationError, load_json, validate


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "examples/configs/anomaly-multiseed-v0.1.json"
SOURCE_ROOT = ROOT
REVISION = {"status": "git", "head": "a" * 40, "dirty": False, "diff_sha256": "b" * 64}


def _write_json(path: Path, value: object) -> bytes:
    raw = _canonical_json(value)
    path.write_bytes(raw + b"\n")
    return raw + b"\n"


def _write_jsonl(path: Path, rows: list[dict]) -> bytes:
    raw = b"".join(runner_module._canonical_json(row) + b"\n" for row in rows)
    path.write_bytes(raw)
    return raw


class AnomalyMatrixRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(tempfile.mkdtemp(prefix="matrix-runner-repo-"))
        shutil.copytree(SOURCE_ROOT / "examples", cls.repo_root / "examples")
        shutil.copytree(SOURCE_ROOT / "schemas", cls.repo_root / "schemas")
        global ROOT, CONFIG_PATH
        ROOT = cls.repo_root
        CONFIG_PATH = ROOT / "examples/configs/anomaly-multiseed-v0.1.json"
        cls.artifact_parent = cls.repo_root / "artifacts"
        cls.artifact_parent.mkdir(parents=True, exist_ok=True)
        cls.token = uuid4().hex[:10]
        cls.temp_root = Path(tempfile.mkdtemp(prefix="matrix-runner-test-", dir=cls.artifact_parent))
        base = load_json(ROOT / "examples/configs/synthetic-anomaly-evaluation-v0.1.json")
        base["dataset_id"] = f"runner-template-{cls.token}"
        base_path = cls.temp_root / "base.json"
        base_path.write_text(json.dumps(base, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        cls.template_dataset = cls.temp_root / "template-dataset"
        generate_synthetic(base_path, cls.template_dataset, ROOT)
        eval_config = load_json(ROOT / "examples/configs/anomaly-evaluation-v0.1.json")
        eval_config["dataset_path"] = cls.template_dataset.relative_to(ROOT).as_posix()
        cls.template_evaluation_output = cls.artifact_parent / f"runner-template-evaluation-{cls.token}"
        eval_config["output_dir"] = cls.template_evaluation_output.relative_to(ROOT).as_posix()
        eval_config_path = cls.temp_root / "template-evaluation.json"
        eval_config_path.write_text(json.dumps(eval_config, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        _output, cls.template_result = _evaluate_core(eval_config_path, ROOT)
        cls.full_template_result = copy.deepcopy(cls.template_result)
        for key in ("profiles", "scores", "alert_episodes", "alert_episode_accounting", "incidents", "clean_false_alert_episodes"):
            cls.template_result[key] = []
        cls.outputs: list[Path] = []

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.repo_root, ignore_errors=True)

    def tearDown(self) -> None:
        output = self.repo_root / "artifacts" / "anomaly-multiseed-v01"
        if output.exists() and not output.is_symlink():
            shutil.rmtree(output, ignore_errors=True)
        for path in self.repo_root.glob("artifacts/.anomaly-multiseed-v01.incomplete-*"):
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path, ignore_errors=True)

    def setUp(self) -> None:
        self.generator_calls: list[tuple[int, str]] = []
        self.evaluator_calls: list[str] = []

    def _output(self) -> Path:
        output = ROOT / "artifacts" / "anomaly-multiseed-v01"
        self.outputs.append(output)
        return output

    def _fake_generator(self, config_path: Path, output: Path, root: Path) -> Path:
        config = load_json(config_path)
        self.generator_calls.append((config["seed"], config["dataset_id"]))
        output.mkdir(parents=True)
        generator_raw = config_path.read_bytes()
        (output / "generator-config.json").write_bytes(generator_raw)
        events = []
        for event in config["events"]:
            events.append({
                "event_id": event["event_id"],
                "event_type": event["event_type"],
                "equipment_id": event["equipment_id"],
                "signal_id": event["signal_id"],
                "start_timestamp": runner_module._iso_at(config["start_timestamp"], event["start_sample"], config["sampling_interval_ms"]),
                "end_timestamp": runner_module._iso_at(config["start_timestamp"], event["end_sample"], config["sampling_interval_ms"]),
                "boundary_semantics": "[start,end)",
                "magnitude": event["magnitude"],
                "description": event["description"],
            })
        observations = [{"cell": config["dataset_id"], "seed": config["seed"]}]
        _write_jsonl(output / "observations.jsonl", observations)
        _write_jsonl(output / "events.jsonl", events)
        _write_json(output / "split-manifest.json", {"dataset_id": config["dataset_id"], "seed": config["seed"]})
        manifest = {
            "schema_version": "0.1", "manifest_type": "dataset", "dataset_id": config["dataset_id"], "provenance": "synthetic",
            "data_path": "observations.jsonl", "events_path": "events.jsonl", "split_manifest_path": "split-manifest.json",
            "fingerprint_path": "fingerprint.json", "generator_config_path": "generator-config.json", "summary_path": "summary.json",
            "generator_version": config["generator_version"], "seed": config["seed"], "sampling_interval_ms": config["sampling_interval_ms"],
            "sample_count": config["sample_count"], "license": "MIT",
            "equipment": [{"equipment_id": item["equipment_id"], "equipment_type": item["equipment_type"]} for item in config["equipment"]],
            "signals": [{"signal_id": "motor-01.motor_current", "name": "motor current", "unit": "A", "role": "target", "sampling_interval_ms": config["sampling_interval_ms"]}],
        }
        _write_json(output / "dataset-manifest.json", manifest)
        hashes = {name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in FINGERPRINT_FILE_NAMES}
        fingerprint_input = "".join(f"{name}\n{digest}\n" for name, digest in sorted(hashes.items())).encode("utf-8")
        fingerprint = {"algorithm": FINGERPRINT_ALGORITHM, "canonicalization": FINGERPRINT_CANONICALIZATION, "dataset_fingerprint": hashlib.sha256(fingerprint_input).hexdigest(), "files": hashes}
        _write_json(output / "fingerprint.json", fingerprint)
        _write_json(output / "summary.json", {"dataset_fingerprint": fingerprint["dataset_fingerprint"], "event_count": 4})
        return output

    def _fake_evaluator(self, config_path: Path, root: Path, *, recover_incomplete: bool = False, allowed_output_parent: Path | None = None) -> Path:
        config = load_json(config_path)
        output = root / config["output_dir"]
        self.evaluator_calls.append(output.parent.name)
        output.mkdir(parents=True)
        result = copy.deepcopy(self.template_result)
        dataset_path = root / config["dataset_path"]
        manifest = load_json(dataset_path / "dataset-manifest.json")
        result["provenance"]["config"].update(path=config_path.relative_to(root).as_posix(), sha256=hashlib.sha256(config_path.read_bytes()).hexdigest())
        result["provenance"]["schema"].update(path="schemas/anomaly-evaluation-result.schema.json", sha256=hashlib.sha256((root / "schemas/anomaly-evaluation-result.schema.json").read_bytes()).hexdigest())
        result["provenance"]["config_schema"].update(path="schemas/anomaly-evaluation-config.schema.json", sha256=hashlib.sha256((root / "schemas/anomaly-evaluation-config.schema.json").read_bytes()).hexdigest())
        dataset_fingerprint = load_json(dataset_path / "fingerprint.json")["dataset_fingerprint"]
        result["provenance"]["dataset"].update(kind="synthetic-dataset", path=config["dataset_path"], dataset_id=manifest["dataset_id"], dataset_fingerprint=dataset_fingerprint, manifest_sha256=hashlib.sha256((dataset_path / "dataset-manifest.json").read_bytes()).hexdigest())
        result["provenance"]["quality_gate"].update(status="pass", observation_record_count=1, equipment_count=len(manifest["equipment"]))
        base = load_json(root / "examples/configs/synthetic-anomaly-evaluation-v0.1.json")
        result["parameters"].update(
            target_signal_ids=runner_module._expected_target_signal_ids({"generator_config": base, "evaluator_config": config}),
            min_calibration_points=config["min_calibration_points"],
            robust_z_threshold=config["robust_z_threshold"],
            persistence_points=config["persistence_points"],
            detection_grace_points=config["detection_grace_points"],
            sampling_interval_ms=manifest["sampling_interval_ms"],
            calibration_split="validation",
            scoring_split="test",
            boundary_semantics="[start,end)",
        )
        result["exclusions"]["calibration"]["profiles_inconclusive"] = 0
        result["metrics"]["overall"]["eligible_incidents"] = 1
        result["metrics"]["score_availability_by_signal"] = {
            signal_id: {"available_points": 1, "total_points": 1, "availability_ratio": 1.0}
            for signal_id in result["parameters"]["target_signal_ids"]
        }
        result["metrics"]["clean_false_alert_signal_episode_count"] = 0
        result["row_counts"].update(dataset_observations=1, score_rows=0, alert_episodes=0, alert_episode_accounting=0, incidents=0, clean_false_alert_episodes=0, clean_false_alert_signal_episodes=0)
        result["provenance"]["code_revision"] = copy.deepcopy(REVISION)
        result_raw = _write_json(output / "result.json", result)
        summary_raw = b"fake evaluator summary\n"
        (output / "summary.md").write_bytes(summary_raw)
        marker = {"marker_type": "event-aware-anomaly-complete", "schema_version": "0.1", "result_sha256": hashlib.sha256(result_raw).hexdigest(), "summary_sha256": hashlib.sha256(summary_raw).hexdigest()}
        _write_json(output / ".complete", marker)
        return output

    def _run(self, *, generator=None, evaluator=None, recover_incomplete=False) -> Path:
        output = self._output()
        with patch.object(runner_module, "_revision", return_value=copy.deepcopy(REVISION)):
            return run_anomaly_matrix(CONFIG_PATH, ROOT, generator=generator or self._fake_generator, evaluator=evaluator or self._fake_evaluator, recover_incomplete=recover_incomplete)

    def test_order_materialization_and_provenance_inventory(self) -> None:
        output = self._run()
        self.assertEqual(output, ROOT / "artifacts" / "anomaly-multiseed-v01")
        self.assertEqual(len(self.generator_calls), 120)
        self.assertEqual(len(self.evaluator_calls), 120)
        self.assertEqual([seed for seed, _dataset_id in self.generator_calls[:12]], [11] * 12)
        self.assertEqual([seed for seed, _dataset_id in self.generator_calls[12:24]], [17] * 12)
        result = load_json(output / "result.json")
        self.assertEqual(result["counts"], {"total": 120, "success": 120, "partial": 0, "inconclusive": 0, "failed": 0})
        self.assertEqual(result["engineering_status"], "pass")
        self.assertEqual(result["performance_status"], "not_evaluated")
        self.assertTrue(result["invariants"]["distinct_dataset_fingerprints_by_layout"])
        self.assertTrue(result["invariants"]["distinct_observations_by_layout"])
        self.assertEqual(result["cells"][0]["layout_index"], 0)
        self.assertTrue((output / ".complete").is_file())

    def test_one_cell_failure_continues_and_publishes_failure_inventory(self) -> None:
        def malformed_evaluator(config_path: Path, root: Path, **kwargs: object) -> Path:
            config = load_json(config_path)
            output = self._fake_evaluator(config_path, root, **kwargs)
            if config["dataset_path"].endswith("seed-042-layout-11-conveyor-01-cooldown"):
                (output / "result.json").write_bytes(b"{")
            return output

        output = self._run(evaluator=malformed_evaluator)
        result = load_json(output / "result.json")
        self.assertEqual(result["counts"]["failed"], 1)
        self.assertEqual(result["counts"]["total"], 120)
        self.assertEqual(result["engineering_status"], "fail")
        failed = [cell for cell in result["cells"] if cell["status"] == "failed"]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["error_type"], "AnomalyMatrixRunnerError")
        self.assertEqual(failed[0]["failure_stage"], "validate_evaluation")
        self.assertIsNotNone(failed[0]["artifacts"]["generator_config"])
        self.assertIsNotNone(failed[0]["artifacts"]["evaluator_config"])
        self.assertIsNotNone(failed[0]["artifacts"]["dataset"])
        self.assertIsNone(failed[0]["artifacts"]["evaluation"])
        self.assertEqual(len(self.generator_calls), 120)
        self.assertEqual(len(self.evaluator_calls), 120)

    def test_success_output_is_byte_deterministic(self) -> None:
        first = self._run()
        first_result = (first / "result.json").read_bytes()
        first_summary = (first / "summary.md").read_bytes()
        shutil.rmtree(first)
        second = self._run()
        self.assertEqual(first_result, (second / "result.json").read_bytes())
        self.assertEqual(first_summary, (second / "summary.md").read_bytes())

    def test_status_mapping_and_marker_is_published_last(self) -> None:
        def partial_evaluator(config_path: Path, root: Path, **kwargs: object) -> Path:
            output = self._fake_evaluator(config_path, root, **kwargs)
            if len(self.evaluator_calls) <= 2:
                result = load_json(output / "result.json")
                if len(self.evaluator_calls) == 1:
                    result["status"] = "partial"
                    result["metrics"]["overall"]["eligible_incidents"] = 0
                else:
                    result["status"] = "inconclusive"
                    result["exclusions"]["calibration"]["profiles_inconclusive"] = 1
                result_raw = _write_json(output / "result.json", result)
                summary_raw = (output / "summary.md").read_bytes()
                _write_json(output / ".complete", {
                    "marker_type": "event-aware-anomaly-complete",
                    "schema_version": "0.1",
                    "result_sha256": hashlib.sha256(result_raw).hexdigest(),
                    "summary_sha256": hashlib.sha256(summary_raw).hexdigest(),
                })
            return output

        with patch.object(runner_module, "_place_no_replace", wraps=runner_module._place_no_replace) as place:
            output = self._run(evaluator=partial_evaluator)
        result = load_json(output / "result.json")
        self.assertEqual(result["counts"]["partial"], 1)
        self.assertEqual(result["counts"]["inconclusive"], 1)
        self.assertEqual(result["counts"]["success"], 118)
        self.assertEqual(result["engineering_status"], "fail")
        self.assertEqual(result["cells"][0]["status"], "partial")
        self.assertEqual(result["cells"][0]["evaluator_status"], "partial")
        self.assertEqual(result["cells"][2]["status"], "success")
        self.assertEqual(result["cells"][2]["evaluator_status"], "pass")
        aggregate_targets = [call.args[1].name for call in place.call_args_list]
        self.assertEqual(aggregate_targets[-1], ".complete")

    def test_strict_jsonl_and_repository_relative_path_helpers(self) -> None:
        with tempfile.TemporaryDirectory(dir=self.temp_root) as temporary:
            path = Path(temporary) / "rows.jsonl"
            path.write_bytes(b'{"value":1e999}\n')
            with self.assertRaises(AnomalyMatrixRunnerError):
                runner_module._jsonl_objects(path, "test rows")
            path.write_bytes(b'{"value":NaN}\n')
            with self.assertRaises(AnomalyMatrixRunnerError):
                runner_module._jsonl_objects(path, "test rows")
            path.write_bytes(b'{"value":1,"value":2}\n')
            with self.assertRaises(AnomalyMatrixRunnerError):
                runner_module._jsonl_objects(path, "test rows")
        path_schema = load_json(ROOT / "schemas/anomaly-multiseed-matrix-result.schema.json")["$defs"]["path"]
        for value in ("../x", "a/../x", "a/./x", "a//x", "a/"):
            with self.assertRaises(AnomalyMatrixRunnerError):
                runner_module._strict_repo_relative(value, "test path")
            with self.assertRaises(ManifestValidationError):
                validate(value, path_schema)
        self.assertEqual(
            load_json(ROOT / "schemas/anomaly-multiseed-matrix-result.schema.json")["$defs"]["path"]["pattern"],
            r"^(?!.*//)(?!.*(?:^|/)[.]{1,2}(?:/|$))(?!.*/$)[A-Za-z0-9][A-Za-z0-9._/-]*$",
        )

    def test_injected_internal_typeerror_is_called_once(self) -> None:
        calls = 0

        def injected(*args: object, **kwargs: object) -> None:
            nonlocal calls
            calls += 1
            raise TypeError("internal fake error")

        with self.assertRaises(TypeError):
            runner_module._call_injected(injected, "config", "root", ignored=True)
        self.assertEqual(calls, 1)

    def test_cell_failure_is_byte_stable_and_does_not_include_exception_path(self) -> None:
        matrix_config = load_json(CONFIG_PATH)
        base = load_json(ROOT / "examples/configs/synthetic-anomaly-evaluation-v0.1.json")
        output = ROOT / "artifacts" / "failure-stability"
        cell = runner_module._materialize_cell(matrix_config, base, 11, matrix_config["layouts"][0], ROOT, output)
        generator_raw = runner_module._json_bytes(cell["generator_config"])
        evaluator_raw = runner_module._json_bytes(cell["evaluator_config"])
        first = runner_module._cell_failure(cell, ValueError("C:/tmp/one"), ROOT, "validate_dataset", generator_raw, evaluator_raw, None)
        second = runner_module._cell_failure(cell, ValueError("D:/tmp/two"), ROOT, "validate_dataset", generator_raw, evaluator_raw, None)
        self.assertEqual(runner_module._json_bytes(first), runner_module._json_bytes(second))
        encoded = runner_module._json_bytes(first).decode("utf-8")
        self.assertNotIn("C:/tmp/one", encoded)
        self.assertNotIn("D:/tmp/two", encoded)

    def test_evaluator_cross_field_helper_rejects_schema_valid_drift(self) -> None:
        base = load_json(ROOT / "examples/configs/synthetic-anomaly-evaluation-v0.1.json")
        evaluation_config = load_json(ROOT / "examples/configs/anomaly-evaluation-v0.1.json")
        result = copy.deepcopy(self.full_template_result)
        dataset_provenance = result["provenance"]["dataset"]
        dataset = {
            "path": dataset_provenance["path"],
            "dataset_id": dataset_provenance["dataset_id"],
            "dataset_fingerprint": dataset_provenance["dataset_fingerprint"],
            "manifest_sha256": dataset_provenance["manifest_sha256"],
            "observation_record_count": result["row_counts"]["dataset_observations"],
            "equipment_count": len(base["equipment"]),
        }
        base["dataset_id"] = dataset["dataset_id"]
        cell = {"generator_config": base, "evaluator_config": evaluation_config}
        runner_module._verify_evaluator_cross_fields(result, cell, dataset)
        mutations = (
            ("provenance.dataset.dataset_id", lambda payload: payload["provenance"]["dataset"].update(dataset_id="wrong")),
            ("provenance.dataset.manifest_sha256", lambda payload: payload["provenance"]["dataset"].update(manifest_sha256="0" * 64)),
            ("provenance.quality_gate.observation_record_count", lambda payload: payload["provenance"]["quality_gate"].update(observation_record_count=1)),
            ("parameters.target_signal_ids", lambda payload: payload["parameters"].update(target_signal_ids=list(reversed(payload["parameters"]["target_signal_ids"]))),),
            ("parameters.robust_z_threshold", lambda payload: payload["parameters"].update(robust_z_threshold=99.0)),
            ("row_counts.score_rows", lambda payload: payload["row_counts"].update(score_rows=payload["row_counts"]["score_rows"] + 1)),
            ("status", lambda payload: payload.update(status="partial")),
        )
        for _label, mutate in mutations:
            tampered = copy.deepcopy(result)
            mutate(tampered)
            with self.assertRaises(runner_module._GlobalFailure):
                runner_module._verify_evaluator_cross_fields(tampered, cell, dataset)

    def test_aggregate_verifier_rejects_tampered_counts(self) -> None:
        matrix_config = load_json(CONFIG_PATH)
        cells = []
        for seed in matrix_config["seeds"]:
            for layout in matrix_config["layouts"]:
                cell_id = f"seed-{seed:03d}-layout-{layout['layout_index']:02d}-{layout['layout_id']}"
                cells.append({
                    "cell_id": cell_id,
                    "layout_id": layout["layout_id"],
                    "status": "success",
                    "evaluator_status": "pass",
                    "error_type": None,
                    "reason": None,
                    "failure_stage": None,
                    "artifacts": {
                        "generator_config": {},
                        "evaluator_config": {},
                        "dataset": {"dataset_fingerprint": f"{seed:02x}" * 32, "observations_sha256": f"{seed + 1:02x}" * 32},
                        "evaluation": {"status": "success", "evaluator_status": "pass"},
                    },
                })
        result = {
            "cells": cells,
            "counts": {"total": 120, "success": 120, "partial": 0, "inconclusive": 0, "failed": 0},
            "invariants": {"all_cells_processed": True, "cell_order": True, "event_inventory": True, "distinct_dataset_fingerprints_by_layout": True, "distinct_observations_by_layout": True},
            "engineering_status": "pass",
            "status": "pass",
            "run_status": "complete",
            "performance_status": "not_evaluated",
        }
        runner_module._verify_aggregate_result(result, matrix_config)
        tampered = copy.deepcopy(result)
        tampered["counts"]["success"] = 119
        with self.assertRaises(runner_module._GlobalFailure):
            runner_module._verify_aggregate_result(tampered, matrix_config)

    def test_post_validation_dataset_mutation_is_global_failure_at_first_cell(self) -> None:
        def mutating_evaluator(config_path: Path, root: Path, **kwargs: object) -> Path:
            output = self._fake_evaluator(config_path, root, **kwargs)
            config = load_json(config_path)
            dataset_path = root / config["dataset_path"]
            (dataset_path / "observations.jsonl").write_bytes((dataset_path / "observations.jsonl").read_bytes() + b"\n")
            return output

        with self.assertRaises(runner_module._GlobalFailure):
            self._run(evaluator=mutating_evaluator)
        self.assertEqual(len(self.generator_calls), 1)
        self.assertEqual(len(self.evaluator_calls), 1)

    def test_atomic_placement_fails_closed_without_target(self) -> None:
        with tempfile.TemporaryDirectory(dir=self.repo_root) as temporary:
            directory = Path(temporary)
            source = directory / "source"
            target = directory / "target"
            source.write_bytes(b"payload")
            with patch("os.link", side_effect=OSError("cross-device")):
                with self.assertRaises(AnomalyMatrixRunnerError):
                    runner_module._place_no_replace(source, target, "test artifact")
                with self.assertRaises(AnomalyEvaluationError):
                    from banto_ai import anomaly_evaluation
                    anomaly_evaluation._place_no_replace(source, target)
            self.assertFalse(target.exists())

    def test_global_provenance_failure_leaves_incomplete_evidence(self) -> None:
        calls = 0
        original = runner_module._assert_inputs_unchanged

        def fail_after_claim(root: Path, sources: object, values: object, boundary: str) -> None:
            nonlocal calls
            calls += 1
            if calls == 3:
                raise runner_module.AnomalyMatrixRunnerError("fake provenance mutation")
            original(root, sources, values, boundary)

        with patch.object(runner_module, "_assert_inputs_unchanged", side_effect=fail_after_claim):
            with self.assertRaises(AnomalyMatrixRunnerError):
                self._run()
        output = ROOT / "artifacts" / "anomaly-multiseed-v01"
        self.assertTrue((output / "failure.json").is_file())
        self.assertFalse((output / ".complete").exists())

    def test_non_overwrite_and_recovery_quarantine(self) -> None:
        output = self._run()
        with patch.object(runner_module, "_revision", return_value=copy.deepcopy(REVISION)):
            with self.assertRaises(AnomalyMatrixRunnerError):
                run_anomaly_matrix(CONFIG_PATH, ROOT, generator=self._fake_generator, evaluator=self._fake_evaluator)
        shutil.rmtree(output)
        output.mkdir(parents=True)
        (output / "partial.txt").write_text("incomplete", encoding="utf-8")
        with patch.object(runner_module, "_revision", return_value=copy.deepcopy(REVISION)):
            run_anomaly_matrix(CONFIG_PATH, ROOT, generator=self._fake_generator, evaluator=self._fake_evaluator, recover_incomplete=True)
        quarantines = list(ROOT.glob("artifacts/.anomaly-multiseed-v01.incomplete-*"))
        self.assertTrue(quarantines)
        self.assertTrue(any((path / "partial.txt").is_file() for path in quarantines))


if __name__ == "__main__":
    unittest.main()
