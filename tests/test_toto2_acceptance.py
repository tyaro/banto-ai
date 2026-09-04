"""Toto 2.0 controlled acceptance analyzer tests with a fake artifact registry."""

from __future__ import annotations

import copy
import json
import math
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from banto_ai.generator import generate_synthetic
from banto_ai.manifest import load_json, validate
from banto_ai.quality import check_dataset
from banto_ai.event_slices import _verify_dataset
from banto_ai.toto2_acceptance import AcceptanceError, _validate_cross_track_truth, analyze_controlled_acceptance, validate_acceptance_config


ROOT = Path(__file__).resolve().parents[1]
SEEDS = [17, 29, 42, 73, 101]
HORIZONS = [15, 30]
CONTEXTS = [64, 120]
TRACKS = ("control", "target-fault", "target-quality", "covariate-quality")
MATRIX_IDS = dict(zip(TRACKS, ("toto2-ctl-a", "toto2-ctl-b", "toto2-ctl-c", "toto2-ctl-d")))


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")


def _metric(count: int = 1) -> dict:
    return {"count": count, "mae": 0.0, "rmse": 0.0, "mase": 0.0, "wis": 0.0, "nominal_interval_coverage": 1.0, "interval_width": 0.0}


class Toto2AcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = Path(tempfile.mkdtemp(prefix="t2-acceptance-", dir=ROOT / "artifacts"))
        cls.config_path = cls._make_fixture()

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.temp, ignore_errors=True)

    def setUp(self) -> None:
        self._revision_patch = patch("banto_ai.toto2_acceptance._revision", return_value={"status": "git", "head": "a" * 40, "dirty": False, "diff_sha256": "b" * 64})
        self._revision_patch.start()
        self.addCleanup(self._revision_patch.stop)

    @classmethod
    def _make_fixture(cls) -> Path:
        config_dir = cls.temp / "configs"
        base_benchmark = load_json(ROOT / "examples/configs/benchmark-toto2-controlled.json")
        benchmark_path = config_dir / "benchmark.json"
        _write(benchmark_path, base_benchmark)
        analyzer = load_json(ROOT / "examples/configs/toto2-controlled-acceptance.json")
        analyzer["output_dir"] = f"artifacts/{cls.temp.name}/acceptance"
        datasets_by_track: dict[str, dict[int, tuple[str, str]]] = {}
        for track in TRACKS:
            original_generator = load_json(ROOT / "examples/configs" / f"synthetic-toto2-controlled-{track if track != 'target-fault' else 'target-fault'}.json")
            # The control filename already follows the track name.
            generator_path = config_dir / f"generator-{track}.json"
            _write(generator_path, original_generator)
            datasets_by_track[track] = {}
            for seed in SEEDS:
                generated = copy.deepcopy(original_generator)
                generated["seed"] = seed
                generated["dataset_id"] = f"{original_generator['dataset_id']}--{MATRIX_IDS[track]}--seed-{seed}"
                materialized = cls.temp / "matrix" / track / "configs" / "generators" / f"seed-{seed}.json"
                _write(materialized, generated)
                relative_dataset = f"artifacts/{cls.temp.name}/ds/{track}/{MATRIX_IDS[track]}/seed-{seed}"
                generate_synthetic(materialized, relative_dataset, ROOT)
                datasets_by_track[track][seed] = (relative_dataset, materialized.relative_to(ROOT).as_posix())

        revision = {"status": "git", "head": "a" * 40, "dirty": False, "diff_sha256": "b" * 64}
        for track in TRACKS:
            matrix_id = MATRIX_IDS[track]
            matrix_dir = cls.temp / "matrix" / track
            benchmark_root = f"artifacts/{cls.temp.name}/bench/{track}"
            dataset_root = f"artifacts/{cls.temp.name}/ds/{track}"
            matrix_relative = f"artifacts/{cls.temp.name}/matrix/{track}"
            generator_path = config_dir / f"generator-{track}.json"
            matrix_config = {
                "schema_version": "0.1", "matrix_id": matrix_id,
                "generator_config_path": generator_path.relative_to(ROOT).as_posix(),
                "benchmark_config_path": benchmark_path.relative_to(ROOT).as_posix(),
                "dataset_output_root": dataset_root, "benchmark_output_root": benchmark_root,
                "matrix_output_dir": matrix_relative,
                "axes": {"seeds": SEEDS, "horizons": HORIZONS, "context_lengths": CONTEXTS},
            }
            matrix_config_path = config_dir / f"matrix-{track}.json"
            _write(matrix_config_path, matrix_config)
            datasets = []
            for seed in SEEDS:
                dataset_relative, materialized_relative = datasets_by_track[track][seed]
                materialized_raw = (ROOT / materialized_relative).read_bytes()
                manifest = load_json(ROOT / dataset_relative / "dataset-manifest.json")
                fingerprint = load_json(ROOT / dataset_relative / "fingerprint.json")
                datasets.append({
                    "seed": seed, "dataset_id": manifest["dataset_id"], "dataset_path": dataset_relative,
                    "generator_config_path": materialized_relative, "generator_config_sha256": __import__("hashlib").sha256(materialized_raw).hexdigest(),
                    "dataset_fingerprint": fingerprint["dataset_fingerprint"],
                    "observations_sha256": __import__("hashlib").sha256((ROOT / dataset_relative / "observations.jsonl").read_bytes()).hexdigest(),
                    "quality_gate": {"status": "pass", "observation_record_count": manifest["sample_count"] * len(manifest["equipment"]), "equipment_count": len(manifest["equipment"])},
                })
            cells = []
            for seed in SEEDS:
                dataset_relative, _ = datasets_by_track[track][seed]
                dataset = load_json(ROOT / dataset_relative / "dataset-manifest.json")
                observations = [json.loads(line) for line in (ROOT / dataset_relative / "observations.jsonl").read_text(encoding="utf-8").splitlines()]
                by_equipment = {equipment["equipment_id"]: [row for row in observations if row["equipment_id"] == equipment["equipment_id"]] for equipment in dataset["equipment"]}
                for horizon in HORIZONS:
                    for context in CONTEXTS:
                        cell_id = f"seed-{seed}--horizon-{horizon}--context-{context}"
                        output_relative = f"{benchmark_root}/{matrix_id}/{cell_id}"
                        cell_config = copy.deepcopy(base_benchmark)
                        cell_config.update({"run_id": f"{base_benchmark['run_id']}--{matrix_id}--{cell_id}", "dataset_path": dataset_relative, "output_dir": output_relative, "seed": seed, "horizon": horizon, "context_length": context})
                        cell_config_path = matrix_dir / "configs" / "benchmarks" / f"{cell_id}.json"
                        _write(cell_config_path, cell_config)
                        predictions = []
                        for model in base_benchmark["models"]:
                            for equipment in base_benchmark["equipment_ids"]:
                                for target in base_benchmark["target_signal_ids"]:
                                    full_target = f"{equipment}.{target}"
                                    for lead in range(1, horizon + 1):
                                        point = by_equipment[equipment][384 + lead - 1]["signals"][target]["value"]
                                        timestamp = by_equipment[equipment][384 + lead - 1]["timestamp"]
                                        predictions.append({"model": model["name"], "equipment_id": equipment, "target_signal_id": full_target, "operating_mode": "nominal", "split": "test", "origin_timestamp": by_equipment[equipment][384]["timestamp"], "timestamp": timestamp, "lead_time": lead, "actual": point, "point_forecast": point, "quantiles": {"0.1": point, "0.5": point, "0.9": point}})
                        quality = check_dataset(ROOT / dataset_relative, ROOT)
                        policies = {model["name"]: ("native" if model["name"] == "toto2" else "validation-residual-by-lead") for model in base_benchmark["models"]}
                        result = {
                            "schema_version": "0.2", "result_type": "benchmark", "run_id": cell_config["run_id"], "status": "success", "dataset_fingerprint": dataset["dataset_id"] and load_json(ROOT / dataset_relative / "fingerprint.json")["dataset_fingerprint"], "generator_version": "0.1.0", "run_config": cell_config, "code_revision": revision, "seed": seed, "model_parameters": {model["name"]: model.get("parameters", {}) for model in base_benchmark["models"]}, "prediction_count": len(predictions), "failures": [],
                            "metrics": {"aggregate": _metric(len(predictions)), "by_model": {model["name"]: _metric(1) for model in base_benchmark["models"]}, "slices": {}, "by_model_target": [{"model": model["name"], "target_signal_key": target, "unit": "A", "metrics": _metric(1)} for model in base_benchmark["models"] for target in base_benchmark["target_signal_ids"]], "by_model_equipment_target": [{"model": model["name"], "equipment_id": equipment, "target_signal_id": f"{equipment}.{target}", "unit": "A", "metrics": _metric(1)} for model in base_benchmark["models"] for equipment in base_benchmark["equipment_ids"] for target in base_benchmark["target_signal_ids"]]},
                            "runtime": {"validation_seconds": 0.0, "test_seconds": 0.0, "total_seconds": 0.0, "p50_latency_ms": 0.0, "p95_latency_ms": 0.0, "latency_by_model": {model["name"]: {"call_count": 1, "p50_ms": 0.0, "p95_ms": 0.0} for model in base_benchmark["models"]}, "peak_memory_bytes": 0, "memory_source": "unavailable", "model_state_bytes": {model["name"]: 0 for model in base_benchmark["models"]}, "output_size_bytes_excluding_result": 0, "os": "fake", "python": "fake", "cpu": "fake", "calibration_source": "fake", "quantile_policy_by_model": policies},
                            "provenance": {"quality_gate": quality, "split": {equipment: {"train": {"start_index": 0, "end_index": 240}, "validation": {"start_index": 240, "end_index": 360}, "test": {"start_index": 360, "end_index": 480}} for equipment in base_benchmark["equipment_ids"]}, "origin_selection": {"validation": {equipment: {"count": 1, "indices": [240], "stride": 15, "max_origins": 1, "rule": "fake"} for equipment in base_benchmark["equipment_ids"]}, "test": {equipment: {"count": 1, "indices": [384], "stride": 15, "max_origins": 1, "rule": "fake"} for equipment in base_benchmark["equipment_ids"]}}, "quantile_calibration": "fake", "quantile_policy_by_model": policies},
                        }
                        result_path = ROOT / output_relative / "result.json"
                        prediction_path = result_path.parent / "predictions.jsonl"
                        _write(result_path, result)
                        prediction_path.parent.mkdir(parents=True, exist_ok=True)
                        prediction_path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in predictions) + "\n", encoding="utf-8", newline="\n")
                        import hashlib
                        cell_hash = hashlib.sha256(cell_config_path.read_bytes()).hexdigest()
                        cells.append({"cell_id": cell_id, "run_id": cell_config["run_id"], "seed": seed, "horizon": horizon, "context_length": context, "dataset_id": dataset["dataset_id"], "dataset_path": dataset_relative, "dataset_fingerprint": result["dataset_fingerprint"], "benchmark_config_path": cell_config_path.relative_to(ROOT).as_posix(), "benchmark_config_sha256": cell_hash, "output_dir": output_relative, "result_path": f"{output_relative}/result.json", "status": "success", "benchmark_failure_count": 0, "failure": None})
            matrix_result = {"schema_version": "0.1", "result_type": "benchmark-matrix", "matrix_id": matrix_id, "status": "success", "matrix_config": matrix_config, "code_revision": revision, "base_configs": {"generator": {"path": matrix_config["generator_config_path"], "sha256": __import__("hashlib").sha256(generator_path.read_bytes()).hexdigest()}, "benchmark": {"path": benchmark_path.relative_to(ROOT).as_posix(), "sha256": __import__("hashlib").sha256(benchmark_path.read_bytes()).hexdigest()}}, "axes": {**matrix_config["axes"], "expansion_order": ["seed", "horizon", "context_length"]}, "outputs": {"dataset_output_root": dataset_root, "benchmark_output_root": benchmark_root, "matrix_output_dir": matrix_relative}, "counts": {"total_cells": 20, "successful_cells": 20, "partial_cells": 0, "failed_cells": 0, "completed_cells": 20}, "datasets": datasets, "cells": cells, "macro_summary": [], "research_only_notice": None, "limitations": ["fake"]}
            _write(matrix_dir / "result.json", matrix_result)
            track_cfg = next(item for item in analyzer["tracks"] if item["track_id"] == track)
            track_cfg.update({"matrix_result_path": (matrix_dir / "result.json").relative_to(ROOT).as_posix(), "matrix_config_path": matrix_config_path.relative_to(ROOT).as_posix(), "generator_config_path": generator_path.relative_to(ROOT).as_posix(), "benchmark_config_path": benchmark_path.relative_to(ROOT).as_posix(), "dataset_output_root": dataset_root, "benchmark_output_root": benchmark_root, "matrix_output_dir": matrix_relative})
        analyzer_path = config_dir / "acceptance.json"
        _write(analyzer_path, analyzer)
        return analyzer_path

    def test_static_config_can_validate_without_artifacts(self) -> None:
        config = load_json(ROOT / "examples/configs/toto2-controlled-acceptance.json")
        validate_acceptance_config(config, ROOT)
        config["tracks"][0]["unexpected"] = True
        with self.assertRaises(AcceptanceError):
            validate_acceptance_config(config, ROOT)
        link = self.temp / "configs" / "matrix-result-link.json"
        try:
            os.symlink(ROOT / "examples/configs/toto2-controlled-acceptance.json", link)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink test unavailable: {exc}")
        try:
            symlink_config = load_json(ROOT / "examples/configs/toto2-controlled-acceptance.json")
            symlink_config["tracks"][0]["matrix_result_path"] = link.relative_to(ROOT).as_posix()
            with self.assertRaises(AcceptanceError):
                validate_acceptance_config(symlink_config, ROOT)
        finally:
            link.unlink(missing_ok=True)
        config_link = self.temp / "configs" / "analyzer-config-link.json"
        try:
            os.symlink(self.config_path, config_link)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"config symlink test unavailable: {exc}")
        try:
            with self.assertRaises(AcceptanceError):
                analyze_controlled_acceptance(config_link, ROOT)
        finally:
            config_link.unlink(missing_ok=True)

    def test_matrix_revision_origin_hash_actual_and_quantile_contracts_fail_closed(self) -> None:
        def rejected(label: str, path: Path, mutate) -> None:
            original = path.read_bytes()
            try:
                value = load_json(path)
                mutate(value)
                _write(path, value)
                config = load_json(self.config_path); config["output_dir"] = f"artifacts/{self.temp.name}/{label}-output"; config_path = self.temp / "configs" / f"{label}.json"; _write(config_path, config)
                with self.assertRaises(AcceptanceError): analyze_controlled_acceptance(config_path, ROOT)
            finally:
                path.write_bytes(original)

        matrix_path = self.temp / "matrix" / "control" / "result.json"
        rejected("axis", matrix_path, lambda value: value["axes"].update({"horizons": [14, 30]}))
        rejected("revision", matrix_path, lambda value: value["code_revision"].update({"head": "c" * 40}))
        cell_result_path = ROOT / load_json(matrix_path)["cells"][0]["result_path"]
        rejected("origin", cell_result_path, lambda value: value["provenance"]["origin_selection"]["test"]["motor-01"].update({"indices": [383]}))
        prediction_path = cell_result_path.parent / "predictions.jsonl"
        original_predictions = prediction_path.read_text(encoding="utf-8")
        try:
            rows = original_predictions.splitlines()
            first = json.loads(rows[0]); first["actual"] = float(first["actual"]) + 1.0; rows[0] = json.dumps(first, sort_keys=True)
            prediction_path.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
            config = load_json(self.config_path); config["output_dir"] = f"artifacts/{self.temp.name}/actual-output"; actual_config = self.temp / "configs" / "actual.json"; _write(actual_config, config)
            with self.assertRaises(AcceptanceError): analyze_controlled_acceptance(actual_config, ROOT)
        finally:
            prediction_path.write_text(original_predictions, encoding="utf-8", newline="\n")
        try:
            rows = original_predictions.splitlines()
            first = json.loads(rows[0]); first["quantiles"]["0.8"] = first["quantiles"]["0.9"]; rows[0] = json.dumps(first, sort_keys=True)
            prediction_path.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
            config = load_json(self.config_path); config["output_dir"] = f"artifacts/{self.temp.name}/quantile-output"; quantile_config = self.temp / "configs" / "quantile.json"; _write(quantile_config, config)
            with self.assertRaises(AcceptanceError): analyze_controlled_acceptance(quantile_config, ROOT)
        finally:
            prediction_path.write_text(original_predictions, encoding="utf-8", newline="\n")
        try:
            rows = original_predictions.splitlines()
            toto_row_index = next(index for index, line in enumerate(rows) if json.loads(line)["model"] == "toto2")
            toto_row = json.loads(rows[toto_row_index]); toto_row["point_forecast"] = float(toto_row["point_forecast"]) + 1.0; rows[toto_row_index] = json.dumps(toto_row, sort_keys=True)
            prediction_path.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
            config = load_json(self.config_path); config["output_dir"] = f"artifacts/{self.temp.name}/p50-output"; p50_config = self.temp / "configs" / "p50.json"; _write(p50_config, config)
            with self.assertRaises(AcceptanceError): analyze_controlled_acceptance(p50_config, ROOT)
        finally:
            prediction_path.write_text(original_predictions, encoding="utf-8", newline="\n")

    def test_fake_four_track_success_and_no_ranking(self) -> None:
        output = analyze_controlled_acceptance(self.config_path, ROOT)
        result = load_json(output / "result.json")
        self.assertEqual(result["controlled_acceptance_status"], "pass")
        self.assertFalse(result["cross_model_ranking_allowed"])
        self.assertEqual(result["counts"], {"tracks": 4, "expected_cells": 80, "cells": 80, "expected_groups": 1920, "groups": 1920})
        self.assertEqual(len(result["paired_deltas"]), 1440)
        self.assertTrue(all(delta["ranking"] == "no-rank" for delta in result["paired_deltas"]))
        validate(result, load_json(ROOT / "schemas/toto2-controlled-acceptance-result.schema.json"))

    def test_duplicate_extra_and_missing_predictions_fail_safely(self) -> None:
        matrix = load_json(self.temp / "matrix" / "control" / "result.json")
        cell = matrix["cells"][0]
        predictions = ROOT / cell["output_dir"] / "predictions.jsonl"
        original = predictions.read_text(encoding="utf-8")
        result_path = ROOT / cell["result_path"]
        original_result = result_path.read_bytes()
        try:
            predictions.write_text(original + original.splitlines()[0] + "\n", encoding="utf-8", newline="\n")
            config = load_json(self.config_path); config["output_dir"] = f"artifacts/{self.temp.name}/duplicate-output"; duplicate_config = self.temp / "configs" / "duplicate.json"; _write(duplicate_config, config)
            with self.assertRaises(AcceptanceError): analyze_controlled_acceptance(duplicate_config, ROOT)
            predictions.write_text("\n".join(original.splitlines()[:-1]) + "\n", encoding="utf-8", newline="\n")
            result = load_json(result_path)
            result["prediction_count"] -= 1
            _write(result_path, result)
            config["output_dir"] = f"artifacts/{self.temp.name}/missing-output"; missing_config = self.temp / "configs" / "missing.json"; _write(missing_config, config)
            output = analyze_controlled_acceptance(missing_config, ROOT)
            self.assertEqual(load_json(output / "result.json")["controlled_acceptance_status"], "blocked")
        finally:
            predictions.write_text(original, encoding="utf-8", newline="\n")
            result_path.write_bytes(original_result)

    def test_overwrite_and_unsafe_output_are_rejected(self) -> None:
        config = load_json(self.config_path)
        config["output_dir"] = "../outside"
        unsafe = self.temp / "configs" / "unsafe.json"; _write(unsafe, config)
        with self.assertRaises(AcceptanceError): analyze_controlled_acceptance(unsafe, ROOT)
        config = load_json(self.config_path); config["output_dir"] = f"artifacts/{self.temp.name}/overwrite"; overwrite = self.temp / "configs" / "overwrite.json"; _write(overwrite, config)
        (ROOT / config["output_dir"]).mkdir(parents=True, exist_ok=True)
        with self.assertRaises(AcceptanceError): analyze_controlled_acceptance(overwrite, ROOT)

    def test_partial_cell_is_blocked_and_context_semantics_are_separated(self) -> None:
        matrix = load_json(self.temp / "matrix" / "target-quality" / "result.json")
        cell = matrix["cells"][0]
        result_path = ROOT / cell["result_path"]
        predictions = ROOT / cell["output_dir"] / "predictions.jsonl"
        original_predictions = predictions.read_text(encoding="utf-8")
        original_result = result_path.read_bytes()
        matrix_path = self.temp / "matrix" / "target-quality" / "result.json"
        original_matrix = matrix_path.read_bytes()
        try:
            rows = [json.loads(line) for line in original_predictions.splitlines()]
            removed = rows.pop()
            predictions.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8", newline="\n")
            result = load_json(result_path)
            result["status"] = "partial"
            result["prediction_count"] = len(rows)
            result["failures"] = [{"model": removed["model"], "equipment_id": removed["equipment_id"], "target_signal_id": removed["target_signal_id"], "status": "failed", "reason": "fake validation failure", "split": "validation"}]
            _write(result_path, result)
            matrix["cells"][0]["status"] = "partial"
            matrix["cells"][0]["benchmark_failure_count"] = 1
            matrix["counts"].update({"successful_cells": 19, "partial_cells": 1})
            matrix["status"] = "partial"
            _write(matrix_path, matrix)
            config = load_json(self.config_path); config["output_dir"] = f"artifacts/{self.temp.name}/partial-output"; partial_config = self.temp / "configs" / "partial.json"; _write(partial_config, config)
            output = analyze_controlled_acceptance(partial_config, ROOT)
            result = load_json(output / "result.json")
            self.assertEqual(result["controlled_acceptance_status"], "blocked")
            groups = result["tracks"][2]["cells"][0]["groups"]
            baseline = next(item for item in groups if item["group"]["model"] == "last-value")
            toto = next(item for item in groups if item["group"]["model"] == "toto2")
            self.assertEqual(baseline["expected_consumed_signal_set"], [baseline["group"]["equipment_id"] + "." + baseline["group"]["target_signal_id"].split(".")[-1]])
            self.assertGreaterEqual(toto["padding_count"], 0)
            failed = next(item for item in groups if item["group"]["model"] == removed["model"] and item["group"]["equipment_id"] == removed["equipment_id"] and item["group"]["target_signal_id"] == removed["target_signal_id"])
            self.assertEqual(failed["status"], "failed")
            self.assertEqual(failed["failure"]["split"], "validation")
        finally:
            predictions.write_text(original_predictions, encoding="utf-8", newline="\n")
            result_path.write_bytes(original_result)
            matrix_path.write_bytes(original_matrix)

    def test_truth_contract_violation_is_fail_closed_without_publishing(self) -> None:
        dataset = self.temp / "ds" / "control" / MATRIX_IDS["control"] / "seed-17" / "observations.jsonl"
        original = dataset.read_bytes()
        try:
            rows = [json.loads(line) for line in original.decode("utf-8").splitlines()]
            target = next(row for row in rows if row["equipment_id"] == "motor-01" and row["timestamp"] == "2026-01-01T00:06:24.000Z")
            target["quality"]["motor_current"] = "missing"
            dataset.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8", newline="\n")
            config = load_json(self.config_path); config["output_dir"] = f"artifacts/{self.temp.name}/truth-output"; truth_config = self.temp / "configs" / "truth.json"; _write(truth_config, config)
            with self.assertRaises(AcceptanceError): analyze_controlled_acceptance(truth_config, ROOT)
            self.assertFalse((ROOT / config["output_dir"]).exists())
        finally:
            dataset.write_bytes(original)

    def test_cross_track_truth_helper_rejects_quality_and_fault_contract_drift(self) -> None:
        datasets = {}
        for track in TRACKS:
            datasets[track] = {seed: _verify_dataset(ROOT / f"artifacts/{self.temp.name}/ds/{track}/{MATRIX_IDS[track]}/seed-{seed}", ROOT) for seed in SEEDS}
        with self.subTest("quality future differs"):
            mutated = copy.deepcopy(datasets)
            point = mutated["target-quality"][17]["observations"]["motor-01"][384]
            point["signals"]["motor_current"]["value"] = float(point["signals"]["motor_current"]["value"]) + 1.0
            with self.assertRaises(AcceptanceError): _validate_cross_track_truth(mutated, load_json(ROOT / "examples/configs/benchmark-toto2-controlled.json"), SEEDS)
        with self.subTest("fault changes outside event"):
            mutated = copy.deepcopy(datasets)
            point = mutated["target-fault"][17]["observations"]["motor-01"][384]
            point["signals"]["motor_current"]["value"] = float(point["signals"]["motor_current"]["value"]) + 1.0
            with self.assertRaises(AcceptanceError): _validate_cross_track_truth(mutated, load_json(ROOT / "examples/configs/benchmark-toto2-controlled.json"), SEEDS)
        with self.subTest("fault does not change event"):
            mutated = copy.deepcopy(datasets)
            for index in range(388, 396):
                mutated["target-fault"][17]["observations"]["motor-01"][index]["signals"]["motor_current"]["value"] = datasets["control"][17]["observations"]["motor-01"][index]["signals"]["motor_current"]["value"]
            with self.assertRaises(AcceptanceError): _validate_cross_track_truth(mutated, load_json(ROOT / "examples/configs/benchmark-toto2-controlled.json"), SEEDS)

    def test_source_mutation_between_snapshot_checks_is_not_published(self) -> None:
        config = load_json(self.config_path)
        config["output_dir"] = f"artifacts/{self.temp.name}/mutation-output"
        mutation_config = self.temp / "configs" / "mutation.json"; _write(mutation_config, config)
        import banto_ai.toto2_acceptance as analyzer
        original_check = analyzer._assert_unchanged
        mutation_source = ROOT / config["tracks"][0]["matrix_config_path"]
        original_source = mutation_source.read_bytes()
        calls = {"count": 0}
        def mutate_on_second(snapshots):
            calls["count"] += 1
            if calls["count"] == 2:
                source = mutation_source
                source.write_bytes(source.read_bytes() + b"\n")
            return original_check(snapshots)
        try:
            with patch.object(analyzer, "_assert_unchanged", side_effect=mutate_on_second):
                with self.assertRaises(AcceptanceError): analyze_controlled_acceptance(mutation_config, ROOT)
            self.assertFalse((ROOT / config["output_dir"]).exists())
        finally:
            mutation_source.write_bytes(original_source)


if __name__ == "__main__":
    unittest.main()
