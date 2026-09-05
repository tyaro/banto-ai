from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import banto_ai.anomaly_evaluation as anomaly_evaluation
import banto_ai.anomaly_matrix_runner as runner_module
import banto_ai.quality as quality_module
from banto_ai.anomaly_evaluation import AnomalyEvaluationError, _canonical_json, _evaluate_core
from banto_ai.anomaly_matrix_runner import AnomalyMatrixRunnerError, run_anomaly_matrix
from banto_ai.generator import FINGERPRINT_ALGORITHM, FINGERPRINT_CANONICALIZATION, FINGERPRINT_FILE_NAMES, expected_catalog, generate_synthetic
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
        observation_indices = [*range(540, 552), *range(720, 750)]
        observations = []
        for item in config["equipment"]:
            catalog = {
                entry["signal_id"].rsplit(".", 1)[1]: entry
                for entry in expected_catalog(item["equipment_id"], item["equipment_type"], config["sampling_interval_ms"])
                if entry["signal_id"].rsplit(".", 1)[1] in runner_module.SIGNALS
            }
            for index in observation_indices:
                regime = next(regime for regime in config["regimes"] if regime["start_sample"] <= index < regime["end_sample"])
                values = {}
                for signal_offset, signal_id in enumerate(runner_module.SIGNALS):
                    value = 10.0 + signal_offset * 10.0 + index * 0.01 + ((index + signal_offset) % 2) * 0.2
                    if item["equipment_id"] == "motor-01" and signal_id == "motor_current" and index == 734:
                        value += 5.0
                    values[signal_id] = value
                observations.append({
                    "cell": config["dataset_id"],
                    "equipment_id": item["equipment_id"],
                    "equipment_type": item["equipment_type"],
                    "operating_mode": regime["regime"],
                    "recipe_step": regime.get("recipe_step", regime["regime"]),
                    "seed": config["seed"],
                    "timestamp": runner_module._iso_at(config["start_timestamp"], index, config["sampling_interval_ms"]),
                    "signals": {
                        signal_id: {"unit": catalog[signal_id]["unit"], "value": value}
                        for signal_id, value in values.items()
                    },
                    "quality": {signal_id: "ok" for signal_id in values},
                })
        _write_jsonl(output / "observations.jsonl", observations)
        _write_jsonl(output / "events.jsonl", events)
        split_start = runner_module._iso_at(config["start_timestamp"], 0, config["sampling_interval_ms"])
        validation_start = runner_module._iso_at(config["start_timestamp"], 540, config["sampling_interval_ms"])
        test_start = runner_module._iso_at(config["start_timestamp"], 720, config["sampling_interval_ms"])
        test_end = runner_module._iso_at(config["start_timestamp"], 900, config["sampling_interval_ms"])
        equipment_ids = [item["equipment_id"] for item in config["equipment"]]
        split_template = lambda split_id, split_equipment_ids, start, end, record_count: {"split_id": split_id, "equipment_ids": split_equipment_ids, "start_timestamp": start, "end_timestamp": end, "record_count": record_count}
        _write_json(output / "split-manifest.json", {
            "schema_version": "0.1", "manifest_type": "split", "dataset_id": config["dataset_id"], "generator_version": config["generator_version"],
            "seed": config["seed"], "sampling_interval_ms": config["sampling_interval_ms"], "sample_count": config["sample_count"], "boundary_semantics": "[start,end)",
            "strategies": [
                {"strategy": "chronological", "splits": [split_template("train", equipment_ids, split_start, validation_start, 1080), split_template("validation", equipment_ids, validation_start, test_start, 360), split_template("test", equipment_ids, test_start, test_end, 360)]},
                {"strategy": "cross_equipment", "splits": [split_template("train", equipment_ids[:1], split_start, test_end, 900), split_template("test", equipment_ids[1:], split_start, test_end, 900)]},
            ],
        })
        manifest = {
            "schema_version": "0.1", "manifest_type": "dataset", "dataset_id": config["dataset_id"], "provenance": "synthetic",
            "data_path": "observations.jsonl", "events_path": "events.jsonl", "split_manifest_path": "split-manifest.json",
            "fingerprint_path": "fingerprint.json", "generator_config_path": "generator-config.json", "summary_path": "summary.json",
            "generator_version": config["generator_version"], "seed": config["seed"], "sampling_interval_ms": config["sampling_interval_ms"],
            "sample_count": config["sample_count"], "license": "MIT",
            "equipment": [{"equipment_id": item["equipment_id"], "equipment_type": item["equipment_type"]} for item in config["equipment"]],
            "signals": [
                signal
                for equipment in config["equipment"]
                for signal in expected_catalog(equipment["equipment_id"], equipment["equipment_type"], config["sampling_interval_ms"])
            ],
        }
        _write_json(output / "dataset-manifest.json", manifest)
        hashes = {name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in FINGERPRINT_FILE_NAMES}
        fingerprint_input = "".join(f"{name}\n{digest}\n" for name, digest in sorted(hashes.items())).encode("utf-8")
        fingerprint = {"algorithm": FINGERPRINT_ALGORITHM, "canonicalization": FINGERPRINT_CANONICALIZATION, "dataset_fingerprint": hashlib.sha256(fingerprint_input).hexdigest(), "files": hashes}
        _write_json(output / "fingerprint.json", fingerprint)
        _write_json(output / "summary.json", {"dataset_fingerprint": fingerprint["dataset_fingerprint"], "event_count": 4})
        return output

    def _refresh_fake_fingerprint(self, output: Path) -> None:
        hashes = {name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in FINGERPRINT_FILE_NAMES}
        fingerprint_input = "".join(f"{name}\n{digest}\n" for name, digest in sorted(hashes.items())).encode("utf-8")
        fingerprint = {
            "algorithm": FINGERPRINT_ALGORITHM,
            "canonicalization": FINGERPRINT_CANONICALIZATION,
            "dataset_fingerprint": hashlib.sha256(fingerprint_input).hexdigest(),
            "files": hashes,
        }
        _write_json(output / "fingerprint.json", fingerprint)
        summary = load_json(output / "summary.json")
        summary["dataset_fingerprint"] = fingerprint["dataset_fingerprint"]
        _write_json(output / "summary.json", summary)

    def _compact_quality_semantics(
        self,
        manifest: dict,
        split: dict,
        config: dict,
        observations: list[dict],
        events: list[dict],
        summary: dict,
        fingerprint: dict,
        hash_inventory: dict[str, str],
    ) -> dict:
        """Strict quality contract for the intentionally sparse test-only fixture."""
        quality_module._check_synthetic_structure(manifest, split, config)
        if len(observations) == 84:
            expected_indices = [*range(540, 552), *range(720, 750)]
        elif len(observations) == 60:
            expected_indices = [*range(720, 750)]
        else:
            self.fail(f"unexpected compact fixture row count: {len(observations)}")
        expected_catalog_by_equipment = {
            item["equipment_id"]: {
                signal["signal_id"].rsplit(".", 1)[1]: signal
                for signal in expected_catalog(item["equipment_id"], item["equipment_type"], config["sampling_interval_ms"])
            }
            for item in config["equipment"]
        }
        rows_by_equipment = {item["equipment_id"]: [] for item in config["equipment"]}
        for row in observations:
            self.assertIn(row["equipment_id"], rows_by_equipment)
            rows_by_equipment[row["equipment_id"]].append(row)
            self.assertEqual(set(row), quality_module.OBSERVATION_KEYS | {"cell", "seed"})
            self.assertEqual(row["equipment_type"], next(item["equipment_type"] for item in config["equipment"] if item["equipment_id"] == row["equipment_id"]))
            self.assertEqual(set(row["signals"]), set(runner_module.SIGNALS))
            self.assertEqual(set(row["quality"]), set(runner_module.SIGNALS))
            for signal_id, payload in row["signals"].items():
                self.assertEqual(set(payload), quality_module.SIGNAL_KEYS)
                self.assertEqual(payload["unit"], expected_catalog_by_equipment[row["equipment_id"]][signal_id]["unit"])
                self.assertIsInstance(payload["value"], (int, float))
                self.assertTrue(payload["value"] == payload["value"] and abs(payload["value"]) != float("inf"))
                self.assertEqual(row["quality"][signal_id], "ok")
        for equipment_id, rows in rows_by_equipment.items():
            self.assertEqual(len(rows), len(expected_indices))
            self.assertEqual(
                [runner_module._canonical_timestamp(row["timestamp"], "compact timestamp")[1] for row in rows],
                [runner_module._canonical_timestamp(runner_module._iso_at(config["start_timestamp"], index, config["sampling_interval_ms"]), "expected compact timestamp")[1] for index in expected_indices],
            )
        replay_cell = {"generator_config": config, "evaluator_config": {"target_signal_ids": list(runner_module.SIGNALS)}}
        runner_module._build_dataset_semantic_ledger(replay_cell, observations, split, events)
        quality_module._check_fingerprint(manifest, summary, fingerprint, hash_inventory)
        return {
            "status": "pass",
            "observation_record_count": len(observations),
            "equipment_count": len(rows_by_equipment),
            "checks": ["compact_fixture_exact_structure", "compact_fixture_fingerprint"],
        }

    def _materialized_fake_dataset(self) -> tuple[dict, dict, bytes, Path]:
        matrix_config = load_json(CONFIG_PATH)
        base = load_json(ROOT / "examples/configs/synthetic-anomaly-evaluation-v0.1.json")
        output = self.temp_root / f"manifest-validation-{uuid4().hex}"
        output.mkdir()
        cell = runner_module._materialize_cell(matrix_config, base, 11, matrix_config["layouts"][0], ROOT, output)
        cell["paths"]["generator_config"].parent.mkdir(parents=True)
        generator_raw = _write_json(cell["paths"]["generator_config"], cell["generator_config"])
        self._fake_generator(cell["paths"]["generator_config"], cell["paths"]["dataset"], ROOT)
        return cell, base, generator_raw, cell["paths"]["dataset"]

    def _refresh_fake_accounting(self, result: dict, config: dict, root: Path, dataset_path: Path) -> None:
        manifest = load_json(dataset_path / "dataset-manifest.json")
        events, _events_raw = runner_module._jsonl_objects(dataset_path / "events.jsonl", "fake accounting events")
        base = load_json(root / "examples/configs/synthetic-anomaly-evaluation-v0.1.json")
        accounting_events = []
        for event in events:
            full_signal = event["signal_id"]
            if not full_signal.startswith(f"{event['equipment_id']}."):
                full_signal = f"{event['equipment_id']}.{full_signal}"
            accounting_events.append({
                "event_id": event["event_id"],
                "event_type": event["event_type"],
                "equipment_id": event["equipment_id"],
                "signal_id": full_signal,
                "start": runner_module._canonical_timestamp(event["start_timestamp"], "fake event start")[1],
                "end": runner_module._canonical_timestamp(event["end_timestamp"], "fake event end")[1],
            })
        validation_start = runner_module._canonical_timestamp(runner_module._iso_at(base["start_timestamp"], 540, manifest["sampling_interval_ms"]), "fake validation start")[1]
        test_start = runner_module._canonical_timestamp(runner_module._iso_at(base["start_timestamp"], 720, manifest["sampling_interval_ms"]), "fake test start")[1]
        test_end = runner_module._canonical_timestamp(runner_module._iso_at(base["start_timestamp"], 900, manifest["sampling_interval_ms"]), "fake test end")[1]
        accounting_dataset = {
            "manifest": {"sampling_interval_ms": manifest["sampling_interval_ms"]},
            "split_times": {"validation": (validation_start, test_start), "test": (test_start, test_end)},
            "events": accounting_events,
        }
        classifications = {item["event_id"]: item["event_class"] for item in config["event_classifications"]}
        expected_incidents, expected_clean_alerts, expected_metrics, expected_event_exclusions = anomaly_evaluation._event_records_and_metrics(
            accounting_dataset,
            [item["equipment_id"] for item in manifest["equipment"]],
            result["parameters"]["target_signal_ids"],
            classifications,
            result["alert_episodes"],
            {"detection_grace_points": config["detection_grace_points"]},
            result["scores"],
        )
        result["incidents"] = expected_incidents
        result["alert_episode_accounting"] = expected_metrics.pop("_alert_episode_accounting")
        result["clean_false_alert_episodes"] = expected_clean_alerts
        result["metrics"] = expected_metrics
        result["exclusions"]["events"] = expected_event_exclusions
        unavailable_by_reason = {}
        available_points = 0
        for score in result["scores"]:
            if score["available"] is True:
                available_points += 1
            else:
                reason = score["exclusion_reason"] or "score_unavailable"
                unavailable_by_reason[reason] = unavailable_by_reason.get(reason, 0) + 1
        result["exclusions"]["calibration"]["profiles_inconclusive"] = sum(profile["status"] == "inconclusive" for profile in result["profiles"])
        result["exclusions"]["scoring"].update(
            total_points=len(result["scores"]),
            available_points=available_points,
            unavailable_by_reason=unavailable_by_reason,
        )
        result["row_counts"].update(
            score_rows=len(result["scores"]),
            alert_episodes=len(result["alert_episodes"]),
            alert_episode_accounting=len(result["alert_episode_accounting"]),
            incidents=len(result["incidents"]),
            clean_false_alert_episodes=len(result["clean_false_alert_episodes"]),
            clean_false_alert_signal_episodes=result["metrics"]["clean_false_alert_signal_episode_count"],
        )

    def _fake_evaluator(self, config_path: Path, root: Path, *, recover_incomplete: bool = False, allowed_output_parent: Path | None = None) -> Path:
        config = load_json(config_path)
        output = root / config["output_dir"]
        self.evaluator_calls.append(output.parent.name)
        output.mkdir(parents=True)
        result = copy.deepcopy(self.template_result)
        dataset_path = root / config["dataset_path"]
        manifest = load_json(dataset_path / "dataset-manifest.json")
        observations, _observations_raw = runner_module._jsonl_objects(dataset_path / "observations.jsonl", "fake evaluator observations")
        events, _events_raw = runner_module._jsonl_objects(dataset_path / "events.jsonl", "fake evaluator events")
        generator_config = load_json(dataset_path / "generator-config.json")
        split_manifest = load_json(dataset_path / "split-manifest.json")
        replay_cell = {"generator_config": generator_config, "evaluator_config": config}
        replay_ledger = runner_module._build_dataset_semantic_ledger(replay_cell, observations, split_manifest, events)
        semantic = runner_module._replay_evaluator_semantics(replay_cell, replay_ledger)
        result["provenance"]["config"].update(path=config_path.relative_to(root).as_posix(), sha256=hashlib.sha256(config_path.read_bytes()).hexdigest())
        result["provenance"]["schema"].update(path="schemas/anomaly-evaluation-result.schema.json", sha256=hashlib.sha256((root / "schemas/anomaly-evaluation-result.schema.json").read_bytes()).hexdigest())
        result["provenance"]["config_schema"].update(path="schemas/anomaly-evaluation-config.schema.json", sha256=hashlib.sha256((root / "schemas/anomaly-evaluation-config.schema.json").read_bytes()).hexdigest())
        fingerprint = load_json(dataset_path / "fingerprint.json")
        summary = load_json(dataset_path / "summary.json")
        hash_inventory = {name: hashlib.sha256((dataset_path / name).read_bytes()).hexdigest() for name in FINGERPRINT_FILE_NAMES}
        quality_gate = self._compact_quality_semantics(manifest, split_manifest, generator_config, observations, events, summary, fingerprint, hash_inventory)
        dataset_fingerprint = fingerprint["dataset_fingerprint"]
        result["provenance"]["dataset"].update(kind="synthetic-dataset", path=config["dataset_path"], dataset_id=manifest["dataset_id"], dataset_fingerprint=dataset_fingerprint, manifest_sha256=hashlib.sha256((dataset_path / "dataset-manifest.json").read_bytes()).hexdigest())
        result["provenance"]["quality_gate"] = copy.deepcopy(quality_gate)
        for key in runner_module._EVALUATOR_SEMANTIC_FIELDS:
            result[key] = copy.deepcopy(semantic[key])
        self._refresh_fake_accounting(result, config, root, dataset_path)
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
            with patch.object(runner_module.quality, "check_synthetic_dataset_semantics", side_effect=self._compact_quality_semantics):
                return run_anomaly_matrix(CONFIG_PATH, ROOT, generator=generator or self._fake_generator, evaluator=evaluator or self._fake_evaluator, recover_incomplete=recover_incomplete)

    def _prepare_fake_evaluation_validation(self) -> tuple[dict, dict, dict, dict, Path]:
        cell, base, generator_raw, dataset_path = self._materialized_fake_dataset()
        cell["paths"]["evaluator_config"].parent.mkdir(parents=True, exist_ok=True)
        evaluator_raw = _write_json(cell["paths"]["evaluator_config"], cell["evaluator_config"])
        with patch.object(runner_module.quality, "check_synthetic_dataset_semantics", side_effect=self._compact_quality_semantics):
            dataset, dataset_snapshot, dataset_ledger = runner_module._validate_dataset(
                cell,
                base,
                ROOT,
                load_json(ROOT / "schemas/synthetic-dataset-manifest.schema.json"),
                generator_raw,
            )
        evaluation_output = self._fake_evaluator(cell["paths"]["evaluator_config"], ROOT)
        sources, _values = runner_module._snapshot_inputs(ROOT, CONFIG_PATH)
        self.assertEqual(evaluator_raw, cell["paths"]["evaluator_config"].read_bytes())
        self.assertNotIn("_captured_bytes", dataset_snapshot)
        runner_module._assert_tree_unchanged(dataset_path, dataset_snapshot, "prepared fake dataset", ROOT)
        return cell, dataset, dataset_ledger, sources, evaluation_output

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
        runner_module._verify_aggregate_result(result, load_json(CONFIG_PATH))
        failed_index = next(index for index, cell in enumerate(result["cells"]) if cell["status"] == "failed")
        for mutate in (
            lambda payload: payload["cells"][failed_index].update(evaluator_status="partial"),
            lambda payload: payload["cells"][failed_index].update(failure_stage="validate_dataset"),
            lambda payload: payload["cells"][failed_index]["artifacts"].update(evaluation={"status": "success", "evaluator_status": "pass"}),
        ):
            tampered = copy.deepcopy(result)
            mutate(tampered)
            with self.assertRaises(runner_module._GlobalFailure):
                runner_module._verify_aggregate_result(tampered, load_json(CONFIG_PATH))

    def test_self_consistent_profile_score_removal_fails_one_cell_and_continues(self) -> None:
        def semantic_attack(config_path: Path, root: Path, **kwargs: object) -> Path:
            output = self._fake_evaluator(config_path, root, **kwargs)
            config = load_json(config_path)
            if not config["dataset_path"].endswith("seed-042-layout-11-conveyor-01-cooldown"):
                return output
            result = load_json(output / "result.json")
            profile = result["profiles"][0]
            profile_key = tuple(profile["profile_key"][key] for key in ("equipment_id", "signal_id", "operating_mode"))
            result["profiles"] = [item for item in result["profiles"] if tuple(item["profile_key"][key] for key in ("equipment_id", "signal_id", "operating_mode")) != profile_key]
            result["scores"] = [item for item in result["scores"] if tuple(item["profile_key"][key] for key in ("equipment_id", "signal_id", "operating_mode")) != profile_key]
            result["status"] = "inconclusive"
            self._refresh_fake_accounting(result, config, root, root / config["dataset_path"])
            result_raw = _write_json(output / "result.json", result)
            summary_raw = (output / "summary.md").read_bytes()
            _write_json(output / ".complete", {"marker_type": "event-aware-anomaly-complete", "schema_version": "0.1", "result_sha256": hashlib.sha256(result_raw).hexdigest(), "summary_sha256": hashlib.sha256(summary_raw).hexdigest()})
            return output

        output = self._run(evaluator=semantic_attack)
        result = load_json(output / "result.json")
        self.assertEqual(result["counts"], {"total": 120, "success": 119, "partial": 0, "inconclusive": 0, "failed": 1})
        failed = [cell for cell in result["cells"] if cell["status"] == "failed"]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["cell_id"], "seed-042-layout-11-conveyor-01-cooldown")
        self.assertEqual(failed[0]["failure_stage"], "validate_evaluation")
        self.assertEqual(len(self.generator_calls), 120)
        self.assertEqual(len(self.evaluator_calls), 120)

    def test_self_consistent_incident_outcome_fails_one_cell_and_continues(self) -> None:
        def incident_attack(config_path: Path, root: Path, **kwargs: object) -> Path:
            output = self._fake_evaluator(config_path, root, **kwargs)
            config = load_json(config_path)
            if not config["dataset_path"].endswith("seed-042-layout-00-motor-01-stopped"):
                return output
            result = load_json(output / "result.json")
            incident = next(item for item in result["incidents"] if item["event_id"] == "motor-01-stopped-machine-fault")
            incident.update(
                eligible=False,
                eligibility_reason="outside_test_split",
                detected=False,
                matched_alert_episode_id=None,
                alert_onset_timestamp=None,
                detection_delay_seconds=None,
            )
            result["metrics"]["overall"].update(eligible_incidents=1, detected_incidents=0, missed_incidents=1, incident_recall=0.0, detection_delay_seconds=None)
            result["metrics"]["by_class"]["machine_fault"].update(eligible_incidents=0, detected_incidents=0, missed_incidents=0, incident_recall=None, detection_delay_seconds=None)
            result_raw = _write_json(output / "result.json", result)
            summary_raw = (output / "summary.md").read_bytes()
            _write_json(output / ".complete", {"marker_type": "event-aware-anomaly-complete", "schema_version": "0.1", "result_sha256": hashlib.sha256(result_raw).hexdigest(), "summary_sha256": hashlib.sha256(summary_raw).hexdigest()})
            return output

        output = self._run(evaluator=incident_attack)
        result = load_json(output / "result.json")
        self.assertEqual(result["counts"], {"total": 120, "success": 119, "partial": 0, "inconclusive": 0, "failed": 1})
        failed = [cell for cell in result["cells"] if cell["status"] == "failed"]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["cell_id"], "seed-042-layout-00-motor-01-stopped")
        self.assertEqual(failed[0]["failure_stage"], "validate_evaluation")
        self.assertEqual(len(self.generator_calls), 120)
        self.assertEqual(len(self.evaluator_calls), 120)

    def test_self_consistent_score_replay_tamper_fails_one_cell_and_continues(self) -> None:
        def score_attack(config_path: Path, root: Path, **kwargs: object) -> Path:
            output = self._fake_evaluator(config_path, root, **kwargs)
            config = load_json(config_path)
            if not config["dataset_path"].endswith("seed-042-layout-00-motor-01-stopped"):
                return output
            result = load_json(output / "result.json")
            score = next(item for item in result["scores"] if item["available"] is True)
            start = runner_module._canonical_timestamp(score["timestamp"], "tamper episode start")[1]
            end = start + timedelta(seconds=1)
            episode = {
                "episode_id": "alert-999999",
                "equipment_id": score["equipment_id"],
                "signal_id": score["signal_id"],
                "start_timestamp": anomaly_evaluation._canonical_time(start),
                "onset_timestamp": anomaly_evaluation._canonical_time(start),
                "end_timestamp": anomaly_evaluation._canonical_time(end),
                "point_count": 1,
                "max_score": 0.581799,
                "profile_key": copy.deepcopy(score["profile_key"]),
            }
            score.update(score=0.581799, exceeds_threshold=True, persistence_streak=2, alert_episode_id=episode["episode_id"])
            result["alert_episodes"].append(episode)
            self._refresh_fake_accounting(result, config, root, root / config["dataset_path"])
            result_raw = _write_json(output / "result.json", result)
            summary_raw = (output / "summary.md").read_bytes()
            _write_json(output / ".complete", {"marker_type": "event-aware-anomaly-complete", "schema_version": "0.1", "result_sha256": hashlib.sha256(result_raw).hexdigest(), "summary_sha256": hashlib.sha256(summary_raw).hexdigest()})
            return output

        output = self._run(evaluator=score_attack)
        result = load_json(output / "result.json")
        self.assertEqual(result["counts"], {"total": 120, "success": 119, "partial": 0, "inconclusive": 0, "failed": 1})
        failed = [cell for cell in result["cells"] if cell["status"] == "failed"]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["cell_id"], "seed-042-layout-00-motor-01-stopped")
        self.assertEqual(failed[0]["failure_stage"], "validate_evaluation")
        self.assertEqual(len(self.generator_calls), 120)
        self.assertEqual(len(self.evaluator_calls), 120)

    def test_limitations_replay_tamper_fails_one_cell_and_continues(self) -> None:
        def limitations_attack(config_path: Path, root: Path, **kwargs: object) -> Path:
            output = self._fake_evaluator(config_path, root, **kwargs)
            config = load_json(config_path)
            if not config["dataset_path"].endswith("seed-042-layout-00-motor-01-stopped"):
                return output
            result = load_json(output / "result.json")
            result["limitations"][0] = "schema-valid replacement"
            result_raw = _write_json(output / "result.json", result)
            summary_raw = (output / "summary.md").read_bytes()
            _write_json(output / ".complete", {"marker_type": "event-aware-anomaly-complete", "schema_version": "0.1", "result_sha256": hashlib.sha256(result_raw).hexdigest(), "summary_sha256": hashlib.sha256(summary_raw).hexdigest()})
            return output

        output = self._run(evaluator=limitations_attack)
        result = load_json(output / "result.json")
        self.assertEqual(result["counts"], {"total": 120, "success": 119, "partial": 0, "inconclusive": 0, "failed": 1})
        failed = [cell for cell in result["cells"] if cell["status"] == "failed"]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["cell_id"], "seed-042-layout-00-motor-01-stopped")
        self.assertEqual(failed[0]["failure_stage"], "validate_evaluation")

    def test_success_output_is_byte_deterministic(self) -> None:
        first = self._run()
        first_result = (first / "result.json").read_bytes()
        first_summary = (first / "summary.md").read_bytes()
        shutil.rmtree(first)
        second = self._run()
        self.assertEqual(first_result, (second / "result.json").read_bytes())
        self.assertEqual(first_summary, (second / "summary.md").read_bytes())

    def test_inconclusive_status_and_marker_is_published_last(self) -> None:
        def status_generator(config_path: Path, output: Path, root: Path) -> Path:
            dataset_path = self._fake_generator(config_path, output, root)
            config = load_json(config_path)
            if config["dataset_id"].endswith("seed-011-layout-01-motor-01-startup"):
                observations, _observations_raw = runner_module._jsonl_objects(dataset_path / "observations.jsonl", "status-test observations")
                test_start = runner_module._iso_at(config["start_timestamp"], 720, config["sampling_interval_ms"])
                _write_jsonl(dataset_path / "observations.jsonl", [row for row in observations if row["timestamp"] >= test_start])
                self._refresh_fake_fingerprint(dataset_path)
            return dataset_path

        with patch.object(runner_module, "_place_no_replace", wraps=runner_module._place_no_replace) as place:
            output = self._run(generator=status_generator)
        result = load_json(output / "result.json")
        self.assertEqual(result["counts"]["partial"], 0)
        self.assertEqual(result["counts"]["inconclusive"], 1)
        self.assertEqual(result["counts"]["success"], 119)
        self.assertEqual(result["engineering_status"], "fail")
        self.assertEqual(result["cells"][0]["status"], "success")
        self.assertEqual(result["cells"][0]["evaluator_status"], "pass")
        self.assertEqual(result["cells"][1]["status"], "inconclusive")
        self.assertEqual(result["cells"][1]["evaluator_status"], "inconclusive")
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

    def test_initial_cell_artifact_failures_are_ordinary_and_tree_context_is_scoped(self) -> None:
        with tempfile.TemporaryDirectory(dir=self.temp_root) as temporary:
            directory = Path(temporary)
            tree = directory / "tree"
            tree.mkdir()
            regular_file = tree / "regular"
            regular_file.write_bytes(b"value")
            with self.assertRaises(AnomalyMatrixRunnerError):
                runner_module._tree_snapshot(regular_file, "cell artifact", failure_scope="cell")
            with self.assertRaises(runner_module._GlobalFailure):
                runner_module._tree_snapshot(regular_file, "global artifact")
            with patch.object(runner_module.os, "scandir", side_effect=OSError("unreadable")):
                with self.assertRaises(AnomalyMatrixRunnerError):
                    runner_module._tree_snapshot(tree, "cell tree", failure_scope="cell")
                with self.assertRaises(runner_module._GlobalFailure):
                    runner_module._tree_snapshot(tree, "global tree")
            missing = directory / "missing.json"
            for raw in (b"{", b'{"value":NaN}', b'{"value":1,"value":2}', b"[]"):
                missing.write_bytes(raw)
                with self.assertRaises(AnomalyMatrixRunnerError):
                    runner_module._cell_json_object(missing, "cell JSON")
            missing.unlink()
            with self.assertRaises(AnomalyMatrixRunnerError):
                runner_module._cell_json_object(missing, "missing cell JSON")

    def test_evaluation_marker_uses_snapshot_bytes_without_late_read(self) -> None:
        cell, dataset, dataset_ledger, sources, evaluation_output = self._prepare_fake_evaluation_validation()
        marker_path = evaluation_output / runner_module.COMPLETION_MARKER
        original_read_bytes = Path.read_bytes
        marker_reads = 0
        evaluator_config_sha256 = runner_module._sha256_bytes(cell["paths"]["evaluator_config"].read_bytes())

        def read_bytes(path: Path) -> bytes:
            nonlocal marker_reads
            if path.absolute() == marker_path.absolute():
                marker_reads += 1
                if marker_reads >= 3:
                    raise OSError("late completion-marker read forbidden")
            return original_read_bytes(path)

        with patch.object(Path, "read_bytes", autospec=True, side_effect=read_bytes):
            evidence, snapshot = runner_module._validate_evaluation(
                cell,
                evaluation_output,
                ROOT,
                load_json(ROOT / "schemas/anomaly-evaluation-result.schema.json"),
                sources,
                REVISION,
                dataset,
                dataset_ledger,
                evaluator_config_sha256,
            )
        self.assertEqual(marker_reads, 2)
        self.assertEqual(evidence["status"], "success")
        self.assertNotIn("_captured_bytes", snapshot)

    def test_evaluation_snapshot_after_read_failure_is_global(self) -> None:
        cell, dataset, dataset_ledger, sources, evaluation_output = self._prepare_fake_evaluation_validation()
        marker_path = evaluation_output / runner_module.COMPLETION_MARKER
        original_read_bytes = Path.read_bytes
        marker_reads = 0
        evaluator_config_sha256 = runner_module._sha256_bytes(cell["paths"]["evaluator_config"].read_bytes())

        def read_bytes(path: Path) -> bytes:
            nonlocal marker_reads
            if path.absolute() == marker_path.absolute():
                marker_reads += 1
                if marker_reads >= 2:
                    raise OSError("snapshot-after completion-marker read failed")
            return original_read_bytes(path)

        with patch.object(Path, "read_bytes", autospec=True, side_effect=read_bytes):
            with self.assertRaises(runner_module._GlobalFailure):
                runner_module._validate_evaluation(
                    cell,
                    evaluation_output,
                    ROOT,
                    load_json(ROOT / "schemas/anomaly-evaluation-result.schema.json"),
                    sources,
                    REVISION,
                    dataset,
                    dataset_ledger,
                    evaluator_config_sha256,
                )
        self.assertEqual(marker_reads, 2)

    def test_manifest_fields_catalog_and_fixed_paths_match_generator_config(self) -> None:
        mutations = (
            ("generator_version", lambda manifest: manifest.update(generator_version="0.1.1")),
            ("sampling_interval_ms", lambda manifest: manifest.update(sampling_interval_ms=manifest["sampling_interval_ms"] + 1)),
            ("sample_count", lambda manifest: manifest.update(sample_count=manifest["sample_count"] + 1)),
            ("equipment", lambda manifest: manifest.update(equipment=list(reversed(manifest["equipment"])))),
            ("signals", lambda manifest: manifest["signals"][0].update(unit="wrong-unit")),
            ("fixed_path", lambda manifest: manifest.update(summary_path="events.jsonl")),
        )
        for label, mutate in mutations:
            with self.subTest(field=label):
                cell, base, generator_raw, dataset_path = self._materialized_fake_dataset()
                manifest_path = dataset_path / "dataset-manifest.json"
                manifest = load_json(manifest_path)
                mutate(manifest)
                _write_json(manifest_path, manifest)
                self._refresh_fake_fingerprint(dataset_path)
                with self.assertRaises(AnomalyMatrixRunnerError):
                    runner_module._validate_dataset(cell, base, ROOT, load_json(ROOT / "schemas/synthetic-dataset-manifest.schema.json"), generator_raw)

    def test_split_manifest_boundaries_and_counts_match_generator_config(self) -> None:
        mutations = (
            ("chronological_boundary", lambda split, base: split["strategies"][0]["splits"][2].update(start_timestamp=runner_module._iso_at(base["start_timestamp"], 721, base["sampling_interval_ms"]))),
            ("record_count", lambda split, _base: split["strategies"][0]["splits"][2].update(record_count=split["strategies"][0]["splits"][2]["record_count"] + 1)),
            ("equipment_ids", lambda split, _base: split["strategies"][0]["splits"][1].update(equipment_ids=list(reversed(split["strategies"][0]["splits"][1]["equipment_ids"])))),
        )
        for label, mutate in mutations:
            with self.subTest(field=label):
                cell, base, generator_raw, dataset_path = self._materialized_fake_dataset()
                split_path = dataset_path / "split-manifest.json"
                split = load_json(split_path)
                mutate(split, base)
                _write_json(split_path, split)
                validate(split, load_json(ROOT / "schemas/split-manifest.schema.json"))
                self._refresh_fake_fingerprint(dataset_path)
                with self.assertRaises(AnomalyMatrixRunnerError):
                    runner_module._validate_dataset(cell, base, ROOT, load_json(ROOT / "schemas/synthetic-dataset-manifest.schema.json"), generator_raw)

    def test_repository_containment_rejects_ancestor_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as external:
            link_parent = ROOT / "artifacts" / f"ancestor-link-{uuid4().hex}"
            try:
                os.symlink(external, link_parent, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"directory symlink unavailable: {exc}")
            try:
                with self.assertRaises(runner_module._GlobalFailure):
                    runner_module._assert_contained_path(link_parent / "child", ROOT, "planned artifact", must_exist=False)
            finally:
                link_parent.unlink(missing_ok=True)

    def test_repository_containment_rejects_ancestor_junction(self) -> None:
        junction_parent = ROOT / "artifacts" / f"junction-like-{uuid4().hex}"
        junction_parent.mkdir()
        try:
            with patch.object(runner_module.os.path, "isjunction", side_effect=lambda value: Path(value) == junction_parent):
                with self.assertRaises(runner_module._GlobalFailure):
                    runner_module._assert_contained_path(junction_parent / "child", ROOT, "planned artifact", must_exist=False)
        finally:
            junction_parent.rmdir()

    def test_repository_containment_rejects_real_ntfs_junction(self) -> None:
        if os.name != "nt":
            self.skipTest("NTFS junction test requires Windows")
        with tempfile.TemporaryDirectory() as external:
            junction_parent = ROOT / "artifacts" / f"ntfs-junction-{uuid4().hex}"

            def remove_junction_leaf() -> None:
                if junction_parent.exists() or junction_parent.is_symlink():
                    subprocess.run(["cmd.exe", "/c", "rmdir", "/q", str(junction_parent)], check=False, capture_output=True)

            created = subprocess.run(
                ["cmd.exe", "/c", "mklink", "/J", str(junction_parent), external],
                check=False,
                capture_output=True,
                text=True,
            )
            if created.returncode != 0:
                remove_junction_leaf()
                detail = (created.stderr or created.stdout or "mklink /J failed").strip()
                self.skipTest(f"NTFS junction unavailable: {detail}")
            try:
                with self.assertRaises(runner_module._GlobalFailure):
                    runner_module._assert_contained_path(junction_parent / "child", ROOT, "real junction artifact", must_exist=False)
            finally:
                remove_junction_leaf()

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

    def test_production_quality_pure_rejects_sparse_and_structural_tampering(self) -> None:
        _cell, _base, _generator_raw, sparse_path = self._materialized_fake_dataset()

        def captured_inputs(dataset_path: Path) -> tuple[dict, dict, dict, list[dict], list[dict], dict, dict, dict[str, str]]:
            snapshot = runner_module._tree_snapshot(
                dataset_path,
                "quality pure test dataset",
                containment_root=ROOT,
                failure_scope="global",
                capture_files=("dataset-manifest.json", "generator-config.json", "observations.jsonl", "events.jsonl", "split-manifest.json", "summary.json", "fingerprint.json"),
            )
            captured = snapshot["_captured_bytes"]
            parse = lambda name, label: runner_module._parse_json_object_bytes(captured[name], label, AnomalyMatrixRunnerError)
            return (
                parse("dataset-manifest.json", "quality manifest"),
                parse("split-manifest.json", "quality split"),
                parse("generator-config.json", "quality config"),
                runner_module._jsonl_objects_from_raw(captured["observations.jsonl"], "quality observations"),
                runner_module._jsonl_objects_from_raw(captured["events.jsonl"], "quality events"),
                parse("summary.json", "quality summary"),
                parse("fingerprint.json", "quality fingerprint"),
                snapshot["hashes"],
            )

        sparse_inputs = captured_inputs(sparse_path)
        with self.assertRaises(quality_module.DatasetQualityError):
            quality_module.check_synthetic_dataset_semantics(*sparse_inputs)

        full_inputs = captured_inputs(self.template_dataset)
        expected = quality_module.check_synthetic_dataset_semantics(*full_inputs)
        self.assertEqual(expected["status"], "pass")
        self.assertEqual(expected["observation_record_count"], 1800)
        self.assertEqual(expected["equipment_count"], 2)
        self.assertEqual(expected["checks"], quality_module.SYNTHETIC_QUALITY_CHECKS)
        for label, mutate in (
            ("extra key", lambda value: value[0].update(extra="rejected")),
            ("missing timestamp", lambda value: value[3][0].pop("timestamp")),
            ("bad quality", lambda value: value[3][0]["quality"].update(motor_current="bad")),
            ("bad unit", lambda value: value[3][0]["signals"]["motor_current"].update(unit="wrong")),
        ):
            with self.subTest(field=label):
                tampered = copy.deepcopy(full_inputs)
                mutate(tampered)
                with self.assertRaises(quality_module.DatasetQualityError):
                    quality_module.check_synthetic_dataset_semantics(*tampered)

    def test_sparse_official_fake_without_quality_patch_fails_closed(self) -> None:
        cell, base, generator_raw, _dataset_path = self._materialized_fake_dataset()
        with self.assertRaises(AnomalyMatrixRunnerError) as context:
            runner_module._validate_dataset(
                cell,
                base,
                ROOT,
                load_json(ROOT / "schemas/synthetic-dataset-manifest.schema.json"),
                generator_raw,
            )
        self.assertIn("quality gate", str(context.exception))

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
        template_snapshot = runner_module._tree_snapshot(
            self.template_dataset,
            "template dataset semantic ledger",
            containment_root=ROOT,
            failure_scope="global",
            capture_files=("dataset-manifest.json", "generator-config.json", "observations.jsonl", "events.jsonl", "split-manifest.json", "summary.json", "fingerprint.json"),
        )
        template_captured = template_snapshot["_captured_bytes"]
        template_manifest = runner_module._parse_json_object_bytes(template_captured["dataset-manifest.json"], "template dataset manifest", AnomalyMatrixRunnerError)
        template_config = runner_module._parse_json_object_bytes(template_captured["generator-config.json"], "template generator config", AnomalyMatrixRunnerError)
        template_split = runner_module._parse_json_object_bytes(template_captured["split-manifest.json"], "template split manifest", AnomalyMatrixRunnerError)
        template_summary = runner_module._parse_json_object_bytes(template_captured["summary.json"], "template summary", AnomalyMatrixRunnerError)
        template_fingerprint = runner_module._parse_json_object_bytes(template_captured["fingerprint.json"], "template fingerprint", AnomalyMatrixRunnerError)
        dataset_ledger = runner_module._build_dataset_semantic_ledger(
            cell,
            runner_module._jsonl_objects_from_raw(template_captured["observations.jsonl"], "template observations"),
            template_split,
            runner_module._jsonl_objects_from_raw(template_captured["events.jsonl"], "template events"),
        )
        dataset_ledger["quality_gate"] = quality_module.check_synthetic_dataset_semantics(
            template_manifest,
            template_split,
            template_config,
            runner_module._jsonl_objects_from_raw(template_captured["observations.jsonl"], "template observations"),
            runner_module._jsonl_objects_from_raw(template_captured["events.jsonl"], "template events"),
            template_summary,
            template_fingerprint,
            template_snapshot["hashes"],
        )
        runner_module._verify_evaluator_cross_fields(result, cell, dataset, dataset_ledger)

        def refresh_score_counts(payload: dict) -> None:
            availability = {}
            unavailable_by_reason = {}
            for signal_id in payload["parameters"]["target_signal_ids"]:
                rows = [item for item in payload["scores"] if item["signal_id"] == signal_id]
                available_points = sum(item["available"] is True for item in rows)
                availability[signal_id] = {
                    "available_points": available_points,
                    "total_points": len(rows),
                    "availability_ratio": available_points / len(rows) if rows else None,
                }
                for item in rows:
                    if item["available"] is not True:
                        reason = item["exclusion_reason"] or "score_unavailable"
                        unavailable_by_reason[reason] = unavailable_by_reason.get(reason, 0) + 1
            available_points = sum(item["available_points"] for item in availability.values())
            payload["metrics"]["score_availability_by_signal"] = availability
            payload["exclusions"]["scoring"].update(total_points=len(payload["scores"]), available_points=available_points, unavailable_by_reason=unavailable_by_reason)
            payload["row_counts"]["score_rows"] = len(payload["scores"])

        def remove_profile_and_scores(payload: dict) -> None:
            profile = next(item for item in payload["profiles"] if item["status"] == "calibrated")
            profile_key = tuple(profile["profile_key"][key] for key in ("equipment_id", "signal_id", "operating_mode"))
            profile_scores = [item for item in payload["scores"] if tuple(item["profile_key"][key] for key in ("equipment_id", "signal_id", "operating_mode")) == profile_key]
            self.assertEqual(len(profile_scores), 30)
            payload["profiles"] = [item for item in payload["profiles"] if tuple(item["profile_key"][key] for key in ("equipment_id", "signal_id", "operating_mode")) != profile_key]
            payload["scores"] = [item for item in payload["scores"] if tuple(item["profile_key"][key] for key in ("equipment_id", "signal_id", "operating_mode")) != profile_key]
            refresh_score_counts(payload)

        def remove_score_identity(payload: dict) -> None:
            payload["scores"].pop()
            refresh_score_counts(payload)

        def refresh_incident_counts(payload: dict) -> None:
            for event_class, target in ((None, payload["metrics"]["overall"]), ("machine_fault", payload["metrics"]["by_class"]["machine_fault"]), ("sensor_fault", payload["metrics"]["by_class"]["sensor_fault"])):
                selected = [
                    item
                    for item in payload["incidents"]
                    if item["eligible"] is True and (event_class is None or item["event_class"] == event_class)
                ]
                detected = [item for item in selected if item["detected"] is True]
                delays = [float(item["detection_delay_seconds"]) for item in detected]
                target.update(
                    eligible_incidents=len(selected),
                    detected_incidents=len(detected),
                    missed_incidents=len(selected) - len(detected),
                    incident_recall=len(detected) / len(selected) if selected else None,
                    detection_delay_seconds=anomaly_evaluation._delay_summary(delays),
                )

        def refresh_full_accounting(payload: dict) -> None:
            self._refresh_fake_accounting(payload, cell["evaluator_config"], ROOT, ROOT / dataset["path"])

        def shifted_timestamp(value: str, milliseconds: int) -> str:
            stamp = runner_module._canonical_timestamp(value, "tamper timestamp")[1] + timedelta(milliseconds=milliseconds)
            return stamp.isoformat(timespec="milliseconds").replace("+00:00", "Z")

        def episode_from_score(score: dict, episode_id: str, start_offset_ms: int = 0, end_offset_ms: int = 1000) -> dict:
            start = shifted_timestamp(score["timestamp"], start_offset_ms)
            return {
                "episode_id": episode_id,
                "equipment_id": score["equipment_id"],
                "signal_id": score["signal_id"],
                "start_timestamp": start,
                "onset_timestamp": start,
                "end_timestamp": shifted_timestamp(score["timestamp"], end_offset_ms),
                "point_count": 1,
                "max_score": 0.581799,
                "profile_key": copy.deepcopy(score["profile_key"]),
            }

        def orphan_subsample_episode(payload: dict) -> None:
            score = next(item for item in payload["scores"] if item["available"] is True and item["alert_episode_id"] is None)
            payload["alert_episodes"].append(episode_from_score(score, "alert-999999", 100, 900))
            refresh_full_accounting(payload)

        def below_threshold_linked_episode(payload: dict) -> None:
            score = next(item for item in payload["scores"] if item["available"] is True and item["alert_episode_id"] is None)
            episode = episode_from_score(score, "alert-999999")
            score.update(score=0.581799, exceeds_threshold=True, persistence_streak=2, alert_episode_id=episode["episode_id"])
            payload["alert_episodes"].append(episode)
            refresh_full_accounting(payload)

        def episode_point_count_drift(payload: dict) -> None:
            payload["alert_episodes"][0]["point_count"] += 1
            refresh_full_accounting(payload)

        def episode_max_score_drift(payload: dict) -> None:
            payload["alert_episodes"][0]["max_score"] += 1.0
            refresh_full_accounting(payload)

        def episode_onset_drift(payload: dict) -> None:
            episode = payload["alert_episodes"][0]
            episode["onset_timestamp"] = shifted_timestamp(episode["end_timestamp"], -1)
            refresh_full_accounting(payload)

        def episode_profile_key_drift(payload: dict) -> None:
            episode = payload["alert_episodes"][0]
            profile = next(item for item in payload["profiles"] if item["profile_key"] != episode["profile_key"])
            episode["profile_key"] = copy.deepcopy(profile["profile_key"])
            refresh_full_accounting(payload)

        def score_numeric_drift(payload: dict) -> None:
            score = next(item for item in payload["scores"] if item["alert_episode_id"] is not None)
            score["score"] += 1.0
            episode = next(item for item in payload["alert_episodes"] if item["episode_id"] == score["alert_episode_id"])
            episode["max_score"] = score["score"]
            refresh_full_accounting(payload)

        def profile_center_drift(payload: dict) -> None:
            payload["profiles"][0]["center"] += 0.25
            refresh_full_accounting(payload)

        def profile_scale_drift(payload: dict) -> None:
            payload["profiles"][0]["scale"] *= 2.0
            refresh_full_accounting(payload)

        def profile_status_drift(payload: dict) -> None:
            profile = payload["profiles"][0]
            profile["status"] = "inconclusive"
            for score in payload["scores"]:
                if score["profile_key"] == profile["profile_key"]:
                    score.update(available=False, score=None, exclusion_reason="profile_inconclusive", exceeds_threshold=False, persistence_streak=0, alert_episode_id=None)
            refresh_full_accounting(payload)

        def score_actual_drift(payload: dict) -> None:
            score = next(item for item in payload["scores"] if item["alert_episode_id"] is None)
            score["actual"] = float(score["actual"]) + 1.0
            refresh_full_accounting(payload)

        def score_residual_drift(payload: dict) -> None:
            score = next(item for item in payload["scores"] if item["alert_episode_id"] is None and item["residual"] is not None)
            score["residual"] = float(score["residual"]) + 1.0
            refresh_full_accounting(payload)

        def score_availability_drift(payload: dict) -> None:
            score = next(item for item in payload["scores"] if item["available"] is True and item["alert_episode_id"] is None)
            score.update(available=False, score=None, exclusion_reason="profile_inconclusive", exceeds_threshold=False, persistence_streak=0, alert_episode_id=None)
            refresh_full_accounting(payload)

        def score_streak_drift(payload: dict) -> None:
            score = next(item for item in payload["scores"] if item["alert_episode_id"] is not None)
            score["persistence_streak"] += 1
            refresh_full_accounting(payload)

        def incident_eligibility_drift(payload: dict) -> None:
            incident = next(item for item in payload["incidents"] if item["event_id"] == "motor-01-machine-fault")
            incident.update(
                eligible=False,
                eligibility_reason="outside_test_split",
                detected=False,
                matched_alert_episode_id=None,
                alert_onset_timestamp=None,
                detection_delay_seconds=None,
            )
            refresh_incident_counts(payload)

        def incident_linkage_drift(payload: dict) -> None:
            incident = next(item for item in payload["incidents"] if item["event_id"] == "motor-01-machine-fault")
            incident.update(
                eligible=True,
                eligibility_reason=None,
                detected=True,
                matched_alert_episode_id="alert-999999",
                alert_onset_timestamp=incident["event_start_timestamp"],
                detection_delay_seconds=0.0,
            )
            refresh_incident_counts(payload)
            payload["metrics"]["overall"].update(
                matched_eligible_alert_episodes=payload["metrics"]["overall"]["matched_eligible_alert_episodes"] + 1,
                evaluated_alert_episode_count=payload["metrics"]["overall"]["evaluated_alert_episode_count"] + 1,
                incident_precision=1.0,
            )

        mutations = (
            ("provenance.dataset.dataset_id", lambda payload: payload["provenance"]["dataset"].update(dataset_id="wrong")),
            ("provenance.dataset.manifest_sha256", lambda payload: payload["provenance"]["dataset"].update(manifest_sha256="0" * 64)),
            ("provenance.quality_gate.observation_record_count", lambda payload: payload["provenance"]["quality_gate"].update(observation_record_count=2)),
            ("provenance.quality_gate.checks_fabricated", lambda payload: payload["provenance"]["quality_gate"].update(checks=["fabricated"])),
            ("provenance.quality_gate.checks_reordered", lambda payload: payload["provenance"]["quality_gate"].update(checks=list(reversed(payload["provenance"]["quality_gate"]["checks"]))),),
            ("parameters.target_signal_ids", lambda payload: payload["parameters"].update(target_signal_ids=list(reversed(payload["parameters"]["target_signal_ids"]))),),
            ("parameters.robust_z_threshold", lambda payload: payload["parameters"].update(robust_z_threshold=99.0)),
            ("row_counts.score_rows", lambda payload: payload["row_counts"].update(score_rows=payload["row_counts"]["score_rows"] + 1)),
            ("metrics.score_availability_by_signal", lambda payload: payload["metrics"]["score_availability_by_signal"].pop(next(iter(payload["metrics"]["score_availability_by_signal"]))),),
            ("incidents", lambda payload: (payload.update(incidents=[]), payload["metrics"]["overall"].update(eligible_incidents=1, detected_incidents=0, missed_incidents=1))),
            ("incidents_missing_event", lambda payload: (payload["incidents"].pop(), payload["row_counts"].update(incidents=len(payload["incidents"]))),),
            ("incidents_duplicate_event", lambda payload: payload["incidents"].__setitem__(-1, copy.deepcopy(payload["incidents"][0]))),
            ("profiles", lambda payload: payload.update(profiles=[])),
            ("scores", lambda payload: payload.update(scores=[])),
            ("profile_and_scores_self_consistent", remove_profile_and_scores),
            ("score_missing_identity", remove_score_identity),
            ("scores_duplicate_identity", lambda payload: payload["scores"].__setitem__(1, copy.deepcopy(payload["scores"][0]))),
            ("score_alert_episode_unknown", lambda payload: next(item for item in payload["scores"] if item["alert_episode_id"] is not None).update(alert_episode_id="alert-999999")),
            ("score_alert_episode_missing", lambda payload: next(item for item in payload["scores"] if item["alert_episode_id"] is not None).update(alert_episode_id=None)),
            ("orphan_subsample_episode", orphan_subsample_episode),
            ("below_threshold_linked_episode", below_threshold_linked_episode),
            ("episode_point_count", episode_point_count_drift),
            ("episode_max_score", episode_max_score_drift),
            ("episode_onset", episode_onset_drift),
            ("episode_profile_key", episode_profile_key_drift),
            ("score_numeric", score_numeric_drift),
            ("profile_center", profile_center_drift),
            ("profile_scale", profile_scale_drift),
            ("profile_status", profile_status_drift),
            ("score_actual", score_actual_drift),
            ("score_residual", score_residual_drift),
            ("score_availability", score_availability_drift),
            ("score_persistence_streak", score_streak_drift),
            ("incident_eligibility_self_consistent", incident_eligibility_drift),
            ("incident_linkage_self_consistent", incident_linkage_drift),
            ("metrics.overall.eligible_incidents", lambda payload: payload["metrics"]["overall"].update(eligible_incidents=99)),
            ("limitations", lambda payload: payload["limitations"].__setitem__(0, "schema-valid replacement")),
            ("status", lambda payload: payload.update(status="partial")),
        )
        for _label, mutate in mutations[:2]:
            with self.subTest(field=_label):
                tampered = copy.deepcopy(result)
                mutate(tampered)
                validate(tampered, load_json(ROOT / "schemas/anomaly-evaluation-result.schema.json"))
                with self.assertRaises(runner_module._GlobalFailure):
                    runner_module._verify_evaluator_cross_fields(tampered, cell, dataset, dataset_ledger)
        for _label, mutate in mutations[2:]:
            with self.subTest(field=_label):
                tampered = copy.deepcopy(result)
                mutate(tampered)
                validate(tampered, load_json(ROOT / "schemas/anomaly-evaluation-result.schema.json"))
                with self.assertRaises(runner_module._CellSemanticFailure):
                    runner_module._verify_evaluator_cross_fields(tampered, cell, dataset, dataset_ledger)

    def test_aggregate_verifier_rejects_tampered_counts(self) -> None:
        matrix_config = load_json(CONFIG_PATH)
        cells = []
        for seed in matrix_config["seeds"]:
            for layout in matrix_config["layouts"]:
                cell_id = f"seed-{seed:03d}-layout-{layout['layout_index']:02d}-{layout['layout_id']}"
                cells.append({
                    "cell_id": cell_id,
                    "seed": seed,
                    "seed_sha256": hashlib.sha256(runner_module._canonical_json(seed)).hexdigest(),
                    "layout_id": layout["layout_id"],
                    "layout_index": layout["layout_index"],
                    "layout_canonical_sha256": hashlib.sha256(runner_module._canonical_json(layout)).hexdigest(),
                    "all_layouts_canonical_sha256": hashlib.sha256(runner_module._canonical_json(matrix_config["layouts"])).hexdigest(),
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
        for field in ("seed", "seed_sha256", "layout_index", "layout_canonical_sha256", "all_layouts_canonical_sha256"):
            with self.subTest(field=field):
                tampered = copy.deepcopy(result)
                tampered["cells"][0][field] = 0 if field == "seed" else (99 if field == "layout_index" else "0" * 64)
                with self.assertRaises(runner_module._GlobalFailure):
                    runner_module._verify_aggregate_result(tampered, matrix_config)
        wrong_status_tuples = {
            "success": (("partial", "success", "pass"), ("pass", "partial", "pass"), ("pass", "success", "partial")),
            "partial": (("pass", "partial", "partial"), ("partial", "success", "partial"), ("partial", "partial", "pass")),
            "inconclusive": (("pass", "inconclusive", "inconclusive"), ("inconclusive", "pass", "inconclusive"), ("inconclusive", "inconclusive", "pass")),
        }
        for status, wrong_tuples in wrong_status_tuples.items():
            for index, (cell_evaluator_status, evaluation_status, evaluation_evaluator_status) in enumerate(wrong_tuples):
                with self.subTest(status=status, tuple_index=index):
                    tampered = copy.deepcopy(result)
                    tampered_cell = tampered["cells"][0]
                    tampered_cell["status"] = status
                    tampered_cell["evaluator_status"] = cell_evaluator_status
                    tampered_cell["artifacts"]["evaluation"] = {"status": evaluation_status, "evaluator_status": evaluation_evaluator_status}
                    tampered["counts"] = {"total": 120, "success": 119, "partial": int(status == "partial"), "inconclusive": int(status == "inconclusive"), "failed": 0}
                    tampered["engineering_status"] = "fail" if status != "success" else "pass"
                    tampered["status"] = "not_complete" if status != "success" else "pass"
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
