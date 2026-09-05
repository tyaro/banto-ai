from __future__ import annotations

import io
import builtins
import hashlib
import inspect
import json
import os
import shutil
import tempfile
import unittest
import socket
from contextlib import ExitStack, contextmanager, redirect_stdout
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import banto_ai.anomaly_failure_diagnostics as diagnostics
from banto_ai.manifest import ManifestValidationError
from tools.evaluator.render_anomaly_failure_diagnostics import render_summary
from banto_ai import anomaly_matrix_analysis as analysis, anomaly_matrix_runner as runner


ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def _write_traps():
    """Exercise runtime APIs after fixture setup; reject every ordinary write route."""
    original_open, original_io_open = builtins.open, io.open
    attempts = []

    def guarded(original):
        def open_read_only(file, mode="r", *args, **kwargs):
            if any(flag in mode for flag in "wax+"):
                attempts.append((str(file), mode))
                raise AssertionError("runtime attempted a file write")
            return original(file, mode, *args, **kwargs)
        return open_read_only

    def forbidden(*args, **kwargs):
        attempts.append((args, kwargs))
        raise AssertionError("runtime attempted a filesystem or network mutation")

    with ExitStack() as stack:
        stack.enter_context(patch.object(builtins, "open", guarded(original_open)))
        stack.enter_context(patch.object(io, "open", guarded(original_io_open)))
        for method in ("write_text", "write_bytes", "mkdir", "unlink", "rename", "replace", "touch"):
            stack.enter_context(patch.object(Path, method, forbidden))
        for method in ("open", "write", "mkdir", "makedirs", "unlink", "remove", "rename", "replace", "rmdir", "truncate"):
            stack.enter_context(patch.object(os, method, forbidden))
        stack.enter_context(patch.object(socket, "create_connection", forbidden))
        yield attempts
    if attempts:
        raise AssertionError(f"write attempts: {attempts}")


def _single_cell_replay():
    """Formal v0.2 field shapes, repeated regimes, and 1,440 synthetic score rows."""
    matrix = json.loads((ROOT / diagnostics.EXPECTED_MATRIX_CONFIG_PATH).read_text(encoding="utf-8"))
    base = json.loads((ROOT / matrix["base_generator_config_path"]).read_text(encoding="utf-8"))
    expected = runner._materialize_cell(matrix, base, 11, matrix["layouts"][0], ROOT, ROOT / "fixture-input")
    cell = {field: expected[field] for field in ("cell_id", "seed", "layout_id", "layout_index")}
    scores, profiles = [], []
    start = diagnostics._utc_timestamp(base["start_timestamp"], "fixture start")
    for signal in diagnostics.CANONICAL_SIGNAL_IDS:
        equipment = signal.split(".", 1)[0]
        for mode_index, mode in enumerate(diagnostics.CANONICAL_OPERATING_MODES):
            key = {"equipment_id": equipment, "signal_id": signal, "operating_mode": mode}
            profiles.append({"profile_key": key, "status": "calibrated", "calibration_point_count": 30,
                             "center": 0, "mad": 1, "scale": 1, "reason": None,
                             "excluded_counts": {name: 0 for name in diagnostics._CALIBRATION_EXCLUSION_KEYS}})
            for offset in range(30):
                stamp = start + timedelta(seconds=720 + mode_index * 30 + offset)
                scores.append({**key, "profile_key": dict(key), "timestamp": diagnostics._canonical_utc(stamp),
                               "quality_status": "ok", "actual": 0, "previous_actual": 0, "residual": 0,
                               "available": True, "score": 0, "exclusion_reason": None,
                               "exceeds_threshold": False, "persistence_streak": 0, "alert_episode_id": None})
    event = expected["generator_config"]["events"][1]
    event_start = start + timedelta(seconds=event["start_sample"])
    incident = {"event_id": event["event_id"], "event_class": "sensor_fault", "event_type": event["event_type"],
                "equipment_id": event["equipment_id"], "signal_id": f"{event['equipment_id']}.{event['signal_id']}",
                "event_start_timestamp": diagnostics._canonical_utc(event_start),
                "event_end_timestamp": diagnostics._canonical_utc(event_start + timedelta(seconds=3)),
                "detection_window_start": diagnostics._canonical_utc(event_start),
                "detection_window_end": diagnostics._canonical_utc(event_start + timedelta(seconds=6)),
                "eligible": True, "detected": True, "matched_alert_episode_id": "alert-local",
                "alert_onset_timestamp": diagnostics._canonical_utc(event_start), "detection_delay_seconds": 0}
    for score in scores:
        stamp = diagnostics._utc_timestamp(score["timestamp"], "fixture score")
        if score["signal_id"] == incident["signal_id"] and stamp in (event_start - timedelta(seconds=1), event_start):
            score.update(score=5, exceeds_threshold=True, persistence_streak=1 if stamp < event_start else 2,
                         alert_episode_id=None if stamp < event_start else "alert-local")
    onset = diagnostics._canonical_utc(start + timedelta(seconds=751))
    end = diagnostics._canonical_utc(start + timedelta(seconds=752))
    source = {"episode_id": "clean-source-local", "equipment_id": "conveyor-01", "signal_id": "conveyor-01.vibration_feature",
              "profile_key": {"equipment_id": "conveyor-01", "signal_id": "conveyor-01.vibration_feature", "operating_mode": "startup"},
              "onset_timestamp": onset, "start_timestamp": onset, "end_timestamp": end, "point_count": 1, "max_score": 5}
    evaluation = {"scores": scores, "profiles": profiles, "incidents": [incident], "alert_episodes": [source],
                  "alert_episode_accounting": [{"episode_id": source["episode_id"], "partition": "clean_false_alert"}],
                  "clean_false_alert_episodes": [{"equipment_episode_id": "clean-000001", "equipment_id": "conveyor-01",
                    "start_timestamp": onset, "end_timestamp": end, "source_alert_episode_ids": [source["episode_id"]]}]}
    return {"values": {"matrix_config": matrix}, "evaluations": [{"cell": cell, "evaluation": evaluation, "expected": expected}]}


def _complete_result_fixture() -> dict[str, object]:
    digest = "0" * 64
    empty_digest = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    revision = {"status": "git", "head": "0" * 40, "dirty": False, "diff_sha256": empty_digest}
    source = {"path": "config.json", "sha256": digest}
    event_classes = ["machine_fault", "sensor_fault"]
    event_types = ["jam_or_slip", "spike"]
    incident_signal_ids = ["motor-01.motor_current", "conveyor-01.conveyor_speed", "motor-01.motor_temperature", "conveyor-01.motor_temperature"]
    signal_ids = ["motor-01.motor_current", "motor-01.motor_temperature", "motor-01.conveyor_speed", "motor-01.vibration_feature", "conveyor-01.motor_current", "conveyor-01.motor_temperature", "conveyor-01.conveyor_speed", "conveyor-01.vibration_feature"]
    equipment_ids = ["motor-01", "conveyor-01"]
    operating_modes = ["stopped", "startup", "low_speed", "nominal", "high_load", "cooldown"]
    seeds = (11, 17, 23, 29, 37, 42, 53, 67, 79, 97)
    layout_ids = ("motor-01-stopped", "motor-01-startup", "motor-01-low-speed", "motor-01-nominal", "motor-01-high-load", "motor-01-cooldown", "conveyor-01-stopped", "conveyor-01-startup", "conveyor-01-low-speed", "conveyor-01-nominal", "conveyor-01-high-load", "conveyor-01-cooldown")
    windows = []
    points = []
    for index in range(240):
        cell_index = index // 2
        cell_id = f"seed-{seeds[cell_index // 12]:03d}-layout-{cell_index % 12:02d}-{layout_ids[cell_index % 12]}"
        equipment_id = equipment_ids[(cell_index % 12) // 6]
        signal = "motor_temperature" if index % 2 else ("motor_current" if equipment_id == "motor-01" else "conveyor_speed")
        window = {
            "cell_id": cell_id, "seed": seeds[cell_index // 12], "layout_id": layout_ids[cell_index % 12], "layout_index": cell_index % 12,
            "event_id": layout_ids[cell_index % 12] + ("-machine-fault" if index % 2 == 0 else "-sensor-fault"), "event_class": event_classes[index % 2], "event_type": event_types[index % 2],
            "equipment_id": equipment_id, "signal_id": f"{equipment_id}.{signal}", "operating_mode": operating_modes[cell_index % 6],
            "event_start_timestamp": "2026-01-01T00:00:00Z", "event_end_timestamp": "2026-01-01T00:01:00Z",
            "detection_window_start": "2026-01-01T00:00:00Z", "detection_window_end": "2026-01-01T00:00:06Z",
            "detected": False, "matched_alert_episode_id": None, "alert_onset_timestamp": None,
            "detection_delay_seconds": None, "max_in_window_consecutive_exceedances": 0,
            "pre_event_support": False, "event_causal_support_qualified": False,
        }
        windows.append(window)
        for offset in (-1, 0, 1, 2, 3, 4, 5):
            points.append({
                "cell_id": cell_id, "seed": window["seed"], "layout_id": window["layout_id"], "layout_index": window["layout_index"],
                "event_id": window["event_id"], "event_class": window["event_class"], "event_type": window["event_type"],
                "equipment_id": window["equipment_id"], "signal_id": window["signal_id"], "operating_mode": window["operating_mode"],
                "offset": offset, "timestamp": (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=offset)).isoformat().replace("+00:00", "Z"), "quality_status": "ok",
                "actual": 0, "previous_actual": 0, "residual": 0, "available": True, "exclusion_reason": None,
                "score": 0, "exceeds_threshold": False, "persistence_streak": 0, "alert_episode_id": None,
            })
    availability_exclusions = {key: 0 for key in ("quality_non_ok", "previous_quality_non_ok", "mode_boundary", "gap", "previous_event_overlap", "profile_inconclusive", "no_previous_observation", "nonfinite_value", "previous_nonfinite_value", "nonfinite_residual", "nonfinite_score")}
    calibration_exclusions = {key: 0 for key in ("event_overlap", "nonfinite", "quality_non_ok", "residual_unavailable")}
    availability = []
    calibration = []
    for cell_index in range(120):
        for signal_id in signal_ids:
            for mode in operating_modes:
                layout_index = cell_index % 12
                common = {"cell_id": f"seed-{seeds[cell_index // 12]:03d}-layout-{layout_index:02d}-{layout_ids[layout_index]}", "seed": seeds[cell_index // 12], "layout_id": layout_ids[layout_index], "layout_index": layout_index, "equipment_id": signal_id.split(".", 1)[0], "signal_id": signal_id, "operating_mode": mode}
                availability.append({**common, "available_points": 30, "total_points": 30, "exclusion_counts": dict(availability_exclusions)})
                calibration.append({**common, "calibration_point_count": 1, "center": 0, "mad": 0, "scale": 1, "status": "calibrated", "excluded_counts": dict(calibration_exclusions), "reason": None})
    clean_sources = []
    clean_equipment = []
    clean_reconciliation = []
    for cell_index in range(120):
        cell_id = f"seed-{seeds[cell_index // 12]:03d}-layout-{cell_index % 12:02d}-{layout_ids[cell_index % 12]}"
        for equipment_id in equipment_ids:
            episode_id = f"equipment-episode-{cell_index:03d}-{equipment_id}"
            source_id = f"source-episode-{cell_index:03d}-{equipment_id}"
            layout_index = cell_index % 12
            seed = seeds[cell_index // 12]
            layout_id = layout_ids[layout_index]
            clean_sources.append({"cell_id": cell_id, "seed": seed, "layout_id": layout_id, "layout_index": layout_index, "source_alert_episode_id": source_id, "equipment_id": equipment_id, "signal_id": signal_ids[0] if equipment_id == "motor-01" else signal_ids[4], "operating_mode": operating_modes[0], "onset_timestamp": "2026-01-01T00:00:00Z", "end_timestamp": "2026-01-01T00:00:01Z", "point_count": 1, "max_score": 0, "mode_entry_offset": 0, "equipment_episode_id": episode_id})
            clean_equipment.append({"cell_id": cell_id, "seed": seed, "layout_id": layout_id, "layout_index": layout_index, "equipment_episode_id": episode_id, "equipment_id": equipment_id, "start_timestamp": "2026-01-01T00:00:00Z", "end_timestamp": "2026-01-01T00:00:01Z", "source_alert_episode_ids": [source_id], "merge_size": 1})
            clean_reconciliation.append({"cell_id": cell_id, "equipment_id": equipment_id, "source_count": 1, "equipment_count": 1, "merge_size_sum": 1, "interval_boundary": "[start,end)", "source_ids_scope": "cell_id+equipment_id", "source_ids_exact": True, "merge_size_rule": "merge_size=len(source_alert_episode_ids)", "source_count_rule": "source_count=sum(len(source_alert_episode_ids)) within each cell/equipment", "interval_merge_replay": "canonical_[start,end)_interval_merge", "exact": True})
    def marginal(kind: str, value: object) -> dict[str, object]:
        if kind == "signal_id×operating_mode":
            value = {"signal_id": value[0], "operating_mode": value[1]}
        return {"dimension_name": kind, "dimension_value": value}
    incident_denominators = {"event_class": 120, "event_type": 120, "signal_id": 60, "equipment_id": 120, "operating_mode": 40}
    def incident_aggregate(kind: str, value: object) -> dict[str, object]:
        denominator = incident_denominators[kind]
        return {"dimension": marginal(kind, value), "count_unit": "eligible_incident_windows", "scope": "marginal_over_other_incident_dimensions", "denominator": denominator, "window_count": denominator, "detected_count": 0, "event_causal_support_qualified_count": 0, "pre_event_support_count": 0, "max_consecutive_run_distribution": [{"run_length": run_length, "window_count": denominator if run_length == 0 else 0} for run_length in range(7)]}
    incident_window_aggregates = [incident_aggregate("event_class", value) for value in event_classes] + [incident_aggregate("event_type", value) for value in event_types] + [incident_aggregate("signal_id", value) for value in incident_signal_ids] + [incident_aggregate("equipment_id", value) for value in equipment_ids] + [incident_aggregate("operating_mode", value) for value in operating_modes]
    incident_offset_aggregates = [
        {"dimension": aggregate["dimension"], "count_unit": "incident_points", "scope": "marginal_over_other_incident_dimensions", "denominator": aggregate["denominator"] * 7, "offset": offset, "total_count": aggregate["denominator"], "available_count": aggregate["denominator"], "exceed_count": 0}
        for aggregate in incident_window_aggregates for offset in (-1, 0, 1, 2, 3, 4, 5)
    ]
    availability_aggregates = [{"dimension": {"signal_id": signal_id, "operating_mode": mode}, "available_points": 3600, "total_points": 3600, "exclusion_counts": dict(availability_exclusions)} for signal_id in signal_ids for mode in operating_modes]
    def numeric_distribution() -> dict[str, object]:
        return {"total_count": 12, "non_null_count": 12, "null_count": 0, "min": 1, "max": 1, "mean": 1}
    seed_summaries = [{"seed": seed, "layout_indexes": list(range(12)), "profile_count": 12, "calibration_point_count_distribution": numeric_distribution(), "center_distribution": numeric_distribution(), "mad_distribution": numeric_distribution(), "scale_distribution": numeric_distribution(), "status_counts": {"calibrated": 12, "inconclusive": 0}, "reason_counts": [{"reason": None, "count": 12}]} for seed in (11, 17, 23, 29, 37, 42, 53, 67, 79, 97)]
    calibration_aggregates = [{"grain": "signal_id×operating_mode", "dimension": {"signal_id": signal_id, "operating_mode": mode}, "profile_count": 120, "seed_summaries": deepcopy(seed_summaries)} for signal_id in signal_ids for mode in operating_modes]
    availability_reconciliation = [{"signal_id": signal_id, "operating_mode": mode, "available_points": 3600, "total_points": 3600, "excluded_points": 0, "exclusion_reasons_exact": True, "exact": True} for signal_id in signal_ids for mode in operating_modes]
    calibration_reconciliation = [{"signal_id": signal_id, "operating_mode": mode, "profile_count": 120, "grain": "signal_id×operating_mode", "exact": True} for signal_id in signal_ids for mode in operating_modes]
    clean_source_values = [("signal_id", signal_id) for signal_id in signal_ids] + [("operating_mode", mode) for mode in operating_modes] + [("signal_id×operating_mode", (signal_id, mode)) for signal_id in signal_ids for mode in operating_modes] + [("mode_entry_offset", offset) for offset in range(30)]
    clean_aggregates = [{"dimension": marginal(kind, value), "count_unit": "source_alert_episodes", "scope": "source_alert_episode_marginal", "source_episode_count": 0} for kind, value in clean_source_values] + [{"dimension": marginal("equipment_id", equipment_id), "count_unit": "equipment_merged_episodes", "scope": "equipment_merged_episode_marginal", "equipment_episode_count": 0, "equipment_attribution_rule": "equipment_episode_count=count of cell-local merged equipment episodes whose equipment_id equals dimension_value, each episode counted exactly once"} for equipment_id in equipment_ids]
    return {
        "schema_version": "0.1",
        "result_type": diagnostics.RESULT_TYPE,
        "diagnostics_id": diagnostics.DIAGNOSTICS_ID,
        "matrix_id": diagnostics.EXPECTED_MATRIX_ID,
        "status": "complete",
        "run_status": "complete",
        "engineering_status": "pass",
        "performance_status": "not_evaluated",
        "exploratory_only": True,
        "promotion_eligible": False,
        "provenance": {
            "canonicalization": diagnostics.CANONICALIZATION_ID,
            "artifact_code_revision": {"status": "git", "head": diagnostics.EXPECTED_ARTIFACT_CODE_REVISION, "dirty": False, "diff_sha256": empty_digest},
            "replay_code_revision": {**revision, "diff_sha256": empty_digest},
            "input_artifact": {
                "path": diagnostics.EXPECTED_INPUT_ROOT,
                "result_sha256": diagnostics.EXPECTED_INPUT_ARTIFACT["result_sha256"],
                "summary_sha256": diagnostics.EXPECTED_INPUT_ARTIFACT["summary_sha256"],
                "completion_marker_sha256": diagnostics.EXPECTED_INPUT_ARTIFACT["completion_marker_sha256"],
                "inventory_sha256": diagnostics.EXPECTED_INPUT_ARTIFACT["inventory_sha256"],
            },
            "input_snapshot": {
                "before_inventory_sha256": diagnostics.EXPECTED_INPUT_ARTIFACT["inventory_sha256"],
                "after_inventory_sha256": diagnostics.EXPECTED_INPUT_ARTIFACT["inventory_sha256"],
                "equal": True,
            },
            "revision_compatibility": {
                "policy": "artifact_revision_full_regular_file_tree_bytes_must_match_current_workspace",
                "artifact_revision": {"status": "git", "head": diagnostics.EXPECTED_ARTIFACT_CODE_REVISION, "dirty": False, "diff_sha256": empty_digest},
                "semantic_sources": [{"path": f"src/banto_ai/file-{index:03d}.py", "artifact_blob_sha256": digest, "current_raw_sha256": digest} for index in range(88)],
                "current_only_paths": list(diagnostics.EXPECTED_REVISION_COMPATIBILITY["current_only_paths"]),
                "current_d2_diagnostics": {
                    "module_raw_sha256": digest,
                    "cli_raw_sha256": digest,
                    "renderer_raw_sha256": digest,
                    "schema_raw_sha256": diagnostics.EXPECTED_RESULT_SCHEMA_RAW_SHA256,
                    "config_raw_sha256": diagnostics.EXPECTED_CONFIG_RAW_SHA256,
                },
            },
            "config": {"path": diagnostics.CONFIG_PATH, "sha256": diagnostics.EXPECTED_CONFIG_RAW_SHA256},
            "config_schema": {"path": diagnostics.SCHEMA_PATH, "sha256": diagnostics.EXPECTED_CONFIG_SCHEMA_RAW_SHA256},
            "result_schema": {"path": diagnostics.RESULT_SCHEMA_PATH, "sha256": diagnostics.EXPECTED_RESULT_SCHEMA_RAW_SHA256},
        },
        "counts": {
            "cells": 120,
            "seed_clusters": 10,
            "layouts_per_seed": 12,
            "events_per_seed": 48,
            "seed_values": [11, 17, 23, 29, 37, 42, 53, 67, 79, 97],
            "event_rows": 480,
            "eligible_incident_windows": 240,
            "pre_event_support_rows": 240,
            "detection_window_point_rows": 1440,
            "combined_incident_point_rows": 1680,
            "score_availability_source_points": 172800,
            "availability_group_rows": 5760,
            "calibration_profile_rows": 5760,
            "aggregate_signal_mode_groups": 48,
            "clean_aggregate_rows": 94,
            "incident_window_aggregate_rows": 16,
            "incident_offset_aggregate_rows": 112,
            "clean_reconciliation_rows": 240,
            "availability_aggregate_rows": 48,
            "calibration_aggregate_rows": 48,
            "cardinality_formulas": {
                "event_rows": "seed_clusters*events_per_seed=10*48=480",
                "eligible_incident_windows": "seed_clusters*(events_per_seed/2)=10*(48/2)=240",
                "pre_event_support_rows": "eligible_incident_windows*1=240*1=240",
                "detection_window_point_rows": "eligible_incident_windows*6=240*6=1440",
                "combined_incident_point_rows": "eligible_incident_windows*(1+6)=240*7=1680",
                "score_availability_source_points": "cells*1440=120*1440=172800",
                "availability_group_rows": "cells*aggregate_signal_mode_groups=120*48=5760",
                "calibration_profile_rows": "cells*aggregate_signal_mode_groups=120*48=5760",
                "aggregate_signal_mode_groups": "8_fully_qualified_signals*6_operating_modes=48",
                "incident_window_aggregate_rows": "2+2+4+2+6=16",
                "incident_offset_aggregate_rows": "16*7=112",
                "clean_reconciliation_rows": "cells*equipment=120*2=240",
                "availability_aggregate_rows": "8*6=48",
                "calibration_aggregate_rows": "8*6=48",
                "clean_aggregate_rows": "8+6+48+2+30=94",
            },
        },
        "ledger": {
            "incident_windows": windows,
            "incident_points": points,
            "clean_source_alerts": clean_sources,
            "clean_equipment_alerts": clean_equipment,
            "availability": availability,
            "calibration_profiles": calibration,
        },
        "aggregates": {"incident_window_aggregates": incident_window_aggregates, "incident_offset_aggregates": incident_offset_aggregates, "clean_alerts": clean_aggregates, "availability": availability_aggregates, "calibration": calibration_aggregates},
        "reconciliation": {"clean_alerts": clean_reconciliation, "availability": availability_reconciliation, "calibration": calibration_reconciliation, "cardinality_exact": True},
        "limitations": ["complete schema fixture"],
    }


class AnomalyFailureDiagnosticsTests(unittest.TestCase):
    def test_fixed_config_is_valid_and_validate_only_is_read_only(self) -> None:
        config_path = ROOT / diagnostics.CONFIG_PATH
        schema_path = ROOT / diagnostics.SCHEMA_PATH
        result_schema_path = ROOT / diagnostics.RESULT_SCHEMA_PATH
        output_path = ROOT / diagnostics.EXPECTED_OUTPUT_ROOT
        config_before = config_path.read_bytes()
        schema_before = schema_path.read_bytes()
        result_schema_before = result_schema_path.read_bytes()
        output_existed = output_path.exists()

        summary = diagnostics.validate_diagnostics_config(root=ROOT)

        self.assertEqual(summary["status"], "configuration_valid")
        self.assertEqual(summary["run_status"], "not_run")
        self.assertEqual(summary["performance_status"], "not_evaluated")
        self.assertTrue(summary["exploratory_only"])
        self.assertFalse(summary["promotion_eligible"])
        self.assertEqual(summary["config_canonical_sha256"], diagnostics.EXPECTED_CONFIG_CANONICAL_SHA256)
        self.assertEqual(config_path.read_bytes(), config_before)
        self.assertEqual(schema_path.read_bytes(), schema_before)
        self.assertEqual(result_schema_path.read_bytes(), result_schema_before)
        self.assertEqual(output_path.exists(), output_existed)

    def test_schema_rejects_promotion_and_winner_fields(self) -> None:
        config = json.loads((ROOT / diagnostics.CONFIG_PATH).read_text(encoding="utf-8"))
        schema = json.loads((ROOT / diagnostics.SCHEMA_PATH).read_text(encoding="utf-8"))
        for field in ("promotion_gates", "alternative_thresholds", "winner"):
            invalid = dict(config)
            invalid[field] = {}
            with self.subTest(field=field), self.assertRaises(ManifestValidationError):
                diagnostics.validate(invalid, schema)

    def test_result_schema_accepts_complete_fixture_and_rejects_promotion_fields(self) -> None:
        schema = json.loads((ROOT / diagnostics.RESULT_SCHEMA_PATH).read_text(encoding="utf-8"))
        result = _complete_result_fixture()
        diagnostics.validate(result, schema)
        diagnostics._validate_d2_domain_semantics(result)
        self.assertEqual(set(result["ledger"]["calibration_profiles"][0]["excluded_counts"]), {"event_overlap", "nonfinite", "quality_non_ok", "residual_unavailable"})
        self.assertEqual(result["ledger"]["availability"][0]["total_points"], 30)
        self.assertEqual(result["aggregates"]["availability"][0]["total_points"], 3600)
        self.assertEqual(result["reconciliation"]["availability"][0]["total_points"], 3600)
        self.assertEqual(result["ledger"]["clean_source_alerts"][0]["mode_entry_offset"], 0)
        self.assertEqual({key: result["counts"][key] for key in ("incident_window_aggregate_rows", "incident_offset_aggregate_rows", "clean_reconciliation_rows", "availability_aggregate_rows", "calibration_aggregate_rows")}, {"incident_window_aggregate_rows": 16, "incident_offset_aggregate_rows": 112, "clean_reconciliation_rows": 240, "availability_aggregate_rows": 48, "calibration_aggregate_rows": 48})
        for row in result["ledger"]["availability"]:
            self.assertEqual(row["available_points"] + sum(row["exclusion_counts"].values()), row["total_points"])
        for row in result["aggregates"]["availability"]:
            self.assertEqual(row["available_points"] + sum(row["exclusion_counts"].values()), row["total_points"])
        for row in result["reconciliation"]["availability"]:
            self.assertEqual(row["available_points"] + row["excluded_points"], row["total_points"])
        for field in ("promotion_gates", "alternative_thresholds", "winner"):
            invalid = dict(result)
            invalid[field] = {}
            with self.subTest(field=field), self.assertRaises(ManifestValidationError):
                diagnostics.validate(invalid, schema)
        invalid_status = deepcopy(result)
        invalid_status["status"] = "synthetic"
        with self.assertRaises(ManifestValidationError):
            diagnostics.validate(invalid_status, schema)
        invalid_profile = deepcopy(result)
        invalid_profile["ledger"]["calibration_profiles"][0]["excluded_counts"] = {key: 0 for key in ("quality_non_ok", "previous_quality_non_ok", "mode_boundary", "gap", "previous_event_overlap", "profile_inconclusive", "no_previous_observation", "nonfinite_value", "previous_nonfinite_value", "nonfinite_residual", "nonfinite_score")}
        with self.assertRaises(ManifestValidationError):
            diagnostics.validate(invalid_profile, schema)

    def test_complete_result_rejects_empty_one_short_and_one_long_structural_ledgers(self) -> None:
        schema = json.loads((ROOT / diagnostics.RESULT_SCHEMA_PATH).read_text(encoding="utf-8"))
        result = _complete_result_fixture()
        structural = {
            "incident_windows": 240,
            "incident_points": 1680,
            "availability": 5760,
            "calibration_profiles": 5760,
        }
        empty = deepcopy(result)
        for key in structural:
            empty["ledger"][key] = []
        with self.assertRaises(ManifestValidationError):
            diagnostics.validate(empty, schema)
        for key in structural:
            short = deepcopy(result)
            short["ledger"][key] = short["ledger"][key][:-1]
            with self.subTest(kind="one_short", key=key), self.assertRaises(ManifestValidationError):
                diagnostics.validate(short, schema)
            long = deepcopy(result)
            long["ledger"][key] = long["ledger"][key] + [deepcopy(long["ledger"][key][0])]
            with self.subTest(kind="one_long", key=key), self.assertRaises(ManifestValidationError):
                diagnostics.validate(long, schema)

    def test_complete_result_rejects_wrong_aggregate_and_reconciliation_cardinality(self) -> None:
        schema = json.loads((ROOT / diagnostics.RESULT_SCHEMA_PATH).read_text(encoding="utf-8"))
        result = _complete_result_fixture()
        arrays = {
            ("aggregates", "incident_window_aggregates"): 16,
            ("aggregates", "incident_offset_aggregates"): 112,
            ("aggregates", "clean_alerts"): 94,
            ("aggregates", "availability"): 48,
            ("aggregates", "calibration"): 48,
            ("reconciliation", "clean_alerts"): 240,
            ("reconciliation", "availability"): 48,
            ("reconciliation", "calibration"): 48,
        }
        for (section, key), expected in arrays.items():
            for replacement in ([], result[section][key][:-1], result[section][key] + [deepcopy(result[section][key][0])]):
                invalid = deepcopy(result)
                invalid[section][key] = replacement
                with self.subTest(section=section, key=key, length=len(replacement), expected=expected), self.assertRaises(ManifestValidationError):
                    diagnostics.validate(invalid, schema)

    def test_result_schema_enforces_marginal_dimensions_and_distribution_shapes(self) -> None:
        schema = json.loads((ROOT / diagnostics.RESULT_SCHEMA_PATH).read_text(encoding="utf-8"))
        result = _complete_result_fixture()
        invalid_cases = [
            ("incident_cartesian_dimension", lambda r: r["aggregates"]["incident_window_aggregates"][0]["dimension"].update({"event_type": "spike"})),
            ("clean_signal_mode_string", lambda r: r["aggregates"]["clean_alerts"][14]["dimension"].update({"dimension_value": "motor-01.motor_current×stopped"})),
            ("missing_equipment_attribution_rule", lambda r: r["aggregates"]["clean_alerts"][-1].pop("equipment_attribution_rule")),
            ("ambiguous_equipment_attribution_rule", lambda r: r["aggregates"]["clean_alerts"][-1].update({"equipment_attribution_rule": "cell-local source set intersects the marginal bucket"})),
            ("null_mode_entry_offset", lambda r: r["ledger"]["clean_source_alerts"][0].update({"mode_entry_offset": None})),
            ("wrong_availability_ledger_denominator", lambda r: r["ledger"]["availability"][0].update({"total_points": 1})),
            ("wrong_availability_aggregate_denominator", lambda r: r["aggregates"]["availability"][0].update({"total_points": 1})),
            ("wrong_availability_reconciliation_denominator", lambda r: r["reconciliation"]["availability"][0].update({"total_points": 1})),
            ("old_calibration_distribution_shape", lambda r: (r["aggregates"]["calibration"][0]["seed_summaries"][0]["center_distribution"].pop("total_count"), r["aggregates"]["calibration"][0]["seed_summaries"][0]["center_distribution"].update({"count": 12}))),
        ]
        for name, mutate in invalid_cases:
            invalid = deepcopy(result)
            mutate(invalid)
            with self.subTest(name=name), self.assertRaises(ManifestValidationError):
                diagnostics.validate(invalid, schema)

    def test_d2_domain_contract_rejects_unknown_and_prefix_mismatches_in_all_six_row_variants(self) -> None:
        schema = json.loads((ROOT / diagnostics.RESULT_SCHEMA_PATH).read_text(encoding="utf-8"))
        result = _complete_result_fixture()
        row_variants = [
            ("ledger", "availability", lambda r: r["ledger"]["availability"][0]),
            ("ledger", "calibration_profiles", lambda r: r["ledger"]["calibration_profiles"][0]),
            ("aggregate", "availability", lambda r: r["aggregates"]["availability"][0]),
            ("aggregate", "calibration", lambda r: r["aggregates"]["calibration"][0]),
            ("reconciliation", "availability", lambda r: r["reconciliation"]["availability"][0]),
            ("reconciliation", "calibration", lambda r: r["reconciliation"]["calibration"][0]),
        ]
        for section, kind, get_row in row_variants:
            for field, value in (("signal_id", "bogus.signal"), ("operating_mode", "bogus_mode")):
                invalid = deepcopy(result)
                row = get_row(invalid)
                if section == "ledger":
                    row[field] = value
                elif section == "aggregate":
                    row["dimension"][field] = value
                else:
                    row[field] = value
                with self.subTest(section=section, kind=kind, field=field), self.assertRaises(ManifestValidationError):
                    diagnostics.validate(invalid, schema)
                with self.subTest(semantic_section=section, semantic_kind=kind, field=field), self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
                    diagnostics._validate_d2_domain_semantics(invalid)
            if section == "ledger":
                invalid = deepcopy(result)
                row = get_row(invalid)
                row["equipment_id"] = "conveyor-01" if row["signal_id"].startswith("motor-01.") else "motor-01"
                with self.subTest(section=section, kind=kind, field="equipment_prefix"), self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
                    diagnostics._validate_d2_domain_semantics(invalid)

    def test_d2_domain_contract_pins_exact_cartesian_and_rejects_missing_or_duplicate_pairs(self) -> None:
        config = json.loads((ROOT / diagnostics.CONFIG_PATH).read_text(encoding="utf-8"))
        expected_domains = {"signal_id": list(diagnostics.CANONICAL_SIGNAL_IDS), "operating_mode": list(diagnostics.CANONICAL_OPERATING_MODES), "equipment_id": list(diagnostics.CANONICAL_EQUIPMENT_IDS)}
        for section in ("availability", "calibration"):
            contract = config["ledger_contract"][section]
            self.assertEqual(contract["fixed_domains"], expected_domains)
            self.assertEqual(contract["exact_cartesian_rule"], "all cells emit each of 8 signal_id×6 operating_mode pairs exactly once; no missing, duplicate, or unknown pair")
            self.assertEqual(contract["equipment_prefix_rule"], "equipment_id equals signal_id prefix before first dot")
        for section, key in (("ledger", "availability"), ("aggregates", "availability"), ("reconciliation", "availability")):
            invalid = _complete_result_fixture()
            rows = invalid[section][key]
            rows.pop()
            with self.subTest(section=section, kind="missing"), self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
                diagnostics._validate_d2_domain_semantics(invalid)
            invalid = _complete_result_fixture()
            rows = invalid[section][key]
            rows.append(deepcopy(rows[0]))
            with self.subTest(section=section, kind="duplicate"), self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
                diagnostics._validate_d2_domain_semantics(invalid)

    def test_semantic_contract_rejects_nonisolated_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="failure-diagnostics-paths-") as raw:
            root = Path(raw)
            diagnostics._validate_isolated_paths(root, "artifacts/input", "artifacts/output")
            for input_root, output_root in (
                ("artifacts", "artifacts/output"),
                ("artifacts/input", "artifacts/input"),
                ("artifacts/../outside", "artifacts/output"),
                (r"C:\outside", "artifacts/output"),
            ):
                with self.subTest(input_root=input_root, output_root=output_root), self.assertRaises(ValueError):
                    diagnostics._validate_isolated_paths(root, input_root, output_root)

    def test_semantic_contract_rejects_reparse_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="failure-diagnostics-reparse-") as raw:
            root = Path(raw)
            artifacts = root / "artifacts"
            artifacts.mkdir()
            target = root / "target"
            target.mkdir()
            link = artifacts / "link"
            try:
                os.symlink(target, link, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink unavailable: {exc}")
            with self.assertRaises(ValueError):
                diagnostics._validate_isolated_paths(root, "artifacts/link/input", "artifacts/output")

            output_target = root / "output-target"
            output_target.mkdir()
            output_link = root / "output-link"
            try:
                os.symlink(output_target, output_link, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink unavailable: {exc}")
            with self.assertRaises(ValueError):
                diagnostics._validate_isolated_paths(root, "artifacts/input", "output-link/leaf")

            real_root = root / "real-root"
            real_root.mkdir()
            root_link = root / "root-link"
            try:
                os.symlink(real_root, root_link, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink unavailable: {exc}")
            with self.assertRaises(ValueError):
                diagnostics._repository(root_link)

    def test_repository_rejects_generic_reparse_attribute(self) -> None:
        with tempfile.TemporaryDirectory(prefix="failure-diagnostics-reparse-attribute-") as raw:
            root = Path(raw)
            fake_stat = type("FakeStat", (), {"st_file_attributes": diagnostics.FILE_ATTRIBUTE_REPARSE_POINT})()
            with patch.object(diagnostics.os, "lstat", return_value=fake_stat):
                with self.assertRaises(ValueError):
                    diagnostics._repository(root)

    def test_strict_json_rejects_duplicate_property(self) -> None:
        with tempfile.TemporaryDirectory(prefix="failure-diagnostics-json-") as raw:
            path = Path(raw) / "duplicate.json"
            path.write_text('{"a": 1, "a": 2}', encoding="utf-8")
            with self.assertRaises(ValueError):
                diagnostics._strict_object(path, "duplicate")

    def test_final_read_hook_detects_config_drift_without_touching_real_config(self) -> None:
        with tempfile.TemporaryDirectory(prefix="failure-diagnostics-toctou-") as raw:
            repository = Path(raw)
            for relative in (diagnostics.CONFIG_PATH, diagnostics.SCHEMA_PATH, diagnostics.RESULT_SCHEMA_PATH):
                target = repository / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / relative, target)

            def mutate(repo: Path, _config_path: str | Path) -> None:
                target = repo / diagnostics.CONFIG_PATH
                target.write_bytes(target.read_bytes() + b" ")

            with patch.object(diagnostics, "_VALIDATION_FINAL_READ_HOOK", mutate):
                with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
                    diagnostics.validate_diagnostics_config(root=repository)

    def test_final_read_hook_detects_result_schema_drift(self) -> None:
        with tempfile.TemporaryDirectory(prefix="failure-diagnostics-result-toctou-") as raw:
            repository = Path(raw)
            for relative in (diagnostics.CONFIG_PATH, diagnostics.SCHEMA_PATH, diagnostics.RESULT_SCHEMA_PATH):
                target = repository / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / relative, target)

            def mutate(repo: Path, _config_path: str | Path) -> None:
                target = repo / diagnostics.RESULT_SCHEMA_PATH
                target.write_bytes(target.read_bytes() + b" ")

            with patch.object(diagnostics, "_VALIDATION_FINAL_READ_HOOK", mutate):
                with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
                    diagnostics.validate_diagnostics_config(root=repository)

    def test_d2a_builder_and_full_verifier_recompute_all_aggregates(self) -> None:
        fixture = _complete_result_fixture()
        schema = json.loads((ROOT / diagnostics.RESULT_SCHEMA_PATH).read_text(encoding="utf-8"))
        result = diagnostics._build_diagnostics_draft({"ledger": fixture["ledger"]}, fixture["provenance"], schema=schema)
        self.assertEqual(result["aggregates"]["clean_alerts"][0]["source_episode_count"], 120)
        for path in (
            ("aggregates", "incident_window_aggregates", 0, "window_count"),
            ("aggregates", "availability", 0, "available_points"),
            ("reconciliation", "calibration", 0, "profile_count"),
        ):
            invalid = deepcopy(result)
            target = invalid[path[0]][path[1]][path[2]]
            target[path[3]] += 1
            with self.subTest(path=path), self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
                diagnostics._validate_diagnostics_draft(invalid, schema)

    def test_d2a_full_verifier_rejects_provenance_numbers_and_interval_tamper(self) -> None:
        fixture = _complete_result_fixture()
        schema = json.loads((ROOT / diagnostics.RESULT_SCHEMA_PATH).read_text(encoding="utf-8"))
        result = diagnostics._build_diagnostics_draft({"ledger": fixture["ledger"]}, fixture["provenance"], schema=schema)
        cases = []
        invalid = deepcopy(result)
        invalid["provenance"]["input_snapshot"]["equal"] = False
        cases.append(invalid)
        invalid = deepcopy(result)
        invalid["ledger"]["availability"][0]["available_points"] = True
        cases.append(invalid)
        invalid = deepcopy(result)
        invalid["ledger"]["clean_equipment_alerts"][0]["start_timestamp"] = "2026-01-01T00:00:02Z"
        cases.append(invalid)
        invalid = deepcopy(result)
        invalid["ledger"]["availability"][0]["cell_id"] = "fake-cell"
        cases.append(invalid)
        invalid = deepcopy(result)
        invalid["ledger"]["clean_source_alerts"][0]["equipment_episode_id"] = "other-equipment-episode"
        cases.append(invalid)
        invalid = deepcopy(result)
        invalid["aggregates"]["clean_alerts"][1]["dimension"] = deepcopy(invalid["aggregates"]["clean_alerts"][0]["dimension"])
        cases.append(invalid)
        for invalid in cases:
            with self.assertRaises((diagnostics.AnomalyFailureDiagnosticsError, ManifestValidationError)):
                diagnostics._validate_diagnostics_draft(invalid, schema)

    def test_d2a_semantically_valid_draft_is_not_renderable(self) -> None:
        fixture = _complete_result_fixture()
        schema = json.loads((ROOT / diagnostics.RESULT_SCHEMA_PATH).read_text(encoding="utf-8"))
        draft = diagnostics._build_diagnostics_draft({"ledger": fixture["ledger"]}, fixture["provenance"], schema=schema)
        diagnostics._validate_diagnostics_draft(draft, schema)
        self.assertEqual(draft["status"], "draft")
        with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
            render_summary(draft)
        with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
            render_summary(fixture)

    def test_d2a_private_builder_requires_schema_and_rejects_unverified_complete_result(self) -> None:
        fixture = _complete_result_fixture()
        with self.assertRaises(TypeError):
            diagnostics._build_diagnostics_draft({"ledger": fixture["ledger"]}, fixture["provenance"])  # type: ignore[call-arg]
        schema = json.loads((ROOT / diagnostics.RESULT_SCHEMA_PATH).read_text(encoding="utf-8"))
        with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
            render_summary(fixture)
        for name in ("build_diagnostics_result", "validate_diagnostics_result", "validate_diagnostics_result_full", "build_provenance_from_verified_replay", "build_ledgers_from_verified_replay", "verify_input_replay"):
            self.assertFalse(hasattr(diagnostics, name), name)

    def test_d2a_mode_entry_offset_uses_containing_repeated_regime(self) -> None:
        generator = {
            "start_timestamp": "2026-01-01T00:00:00Z",
            "sampling_interval_ms": 1000,
            "regimes": [
                {"regime": "startup", "start_sample": 0, "end_sample": 30},
                {"regime": "nominal", "start_sample": 30, "end_sample": 60},
                {"regime": "startup", "start_sample": 60, "end_sample": 90},
            ],
        }
        self.assertEqual(diagnostics._mode_entry_offset("2026-01-01T00:01:00Z", "startup", generator), 0)
        self.assertEqual(diagnostics._mode_entry_offset("2026-01-01T00:01:29Z", "startup", generator), 29)
        with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
            diagnostics._mode_entry_offset("2026-01-01T00:00:30Z", "startup", {**generator, "regimes": generator["regimes"][:2]})

    def test_d2a_canonical_detection_at_offset_zero_is_not_causal_without_two_post_start_support_rows(self) -> None:
        fixture = _complete_result_fixture()
        window = fixture["ledger"]["incident_windows"][0]
        points = [row for row in fixture["ledger"]["incident_points"] if (row["cell_id"], row["event_id"]) == (window["cell_id"], window["event_id"])]
        window.update({"detected": True, "matched_alert_episode_id": "episode-offset-zero", "alert_onset_timestamp": next(row["timestamp"] for row in points if row["offset"] == 0), "detection_delay_seconds": 0.0, "max_in_window_consecutive_exceedances": 1, "pre_event_support": True})
        for row in points:
            if row["offset"] == -1:
                row.update({"score": 5, "exceeds_threshold": True, "persistence_streak": 1})
            elif row["offset"] == 0:
                row.update({"alert_episode_id": "episode-offset-zero", "score": 5, "exceeds_threshold": True, "persistence_streak": 2})
            elif row["offset"] == 1:
                row.update({"score": 0, "exceeds_threshold": False, "persistence_streak": 0})
        schema = json.loads((ROOT / diagnostics.RESULT_SCHEMA_PATH).read_text(encoding="utf-8"))
        result = diagnostics._build_diagnostics_draft({"ledger": fixture["ledger"]}, fixture["provenance"], schema=schema)
        self.assertFalse(result["ledger"]["incident_windows"][0]["event_causal_support_qualified"])

    def test_d2a_revision_verification_fails_closed_on_dirty_or_wrong_head(self) -> None:
        with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
            diagnostics._validate_revision_compatibility(ROOT, replay_head="0" * 40)

    def test_cli_requires_validate_only_and_does_not_run_diagnostics(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = diagnostics.main(["--root", str(ROOT)])
        self.assertEqual(exit_code, 2)
        self.assertIn("--validate-only only", output.getvalue())

    def test_cli_validate_only_returns_safe_summary(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = diagnostics.main([
                "--root", str(ROOT),
                "--config", diagnostics.CONFIG_PATH,
                "--validate-only",
            ])
        self.assertEqual(exit_code, 0)
        rendered = output.getvalue()
        self.assertIn("configuration_valid", rendered)
        self.assertIn("run_status: not_run", rendered)
        self.assertIn("filesystem_write: false", rendered)


class D2AIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads((ROOT / diagnostics.RESULT_SCHEMA_PATH).read_text(encoding="utf-8"))
        fixture = _complete_result_fixture()
        cls.result = diagnostics._build_diagnostics_draft({"ledger": fixture["ledger"]}, fixture["provenance"], schema=cls.schema)

    def test_private_drafts_and_correct_pin_strings_cannot_bypass_replay_issuance(self):
        with patch.object(diagnostics, "replay_and_build_diagnostics_result", side_effect=AssertionError("live replay disabled")) as replay:
            fixture = _complete_result_fixture()
            draft = diagnostics._build_diagnostics_draft({"ledger": fixture["ledger"]}, fixture["provenance"], schema=self.schema)
            self.assertEqual(draft["provenance"]["replay_code_revision"]["head"], "0" * 40)
            self.assertTrue(all(row["artifact_blob_sha256"] == "0" * 64 for row in draft["provenance"]["revision_compatibility"]["semantic_sources"]))
            diagnostics._validate_diagnostics_draft(draft, self.schema)
            self.assertEqual({field: draft[field] for field in diagnostics._DRAFT_FLAGS}, diagnostics._DRAFT_FLAGS)
            forged_complete = {**draft, **diagnostics._COMPLETE_FLAGS}
            diagnostics._validate_result_payload(forged_complete, self.schema)
            for payload in (fixture, draft, forged_complete):
                with self.subTest(status=payload["status"]), self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
                    render_summary(payload)
                with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
                    diagnostics.VerifiedDiagnosticsResult(payload)
                with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
                    diagnostics.VerifiedDiagnosticsResult(payload, _token=object())
            replay.assert_not_called()
        with self.assertRaises(TypeError):
            type("ForgedResult", (diagnostics.VerifiedDiagnosticsResult,), {})

    def test_first_new_episode_cannot_be_replaced_by_a_later_episode(self):
        result = deepcopy(self.result)
        points = result["ledger"]["incident_points"][:7]
        for index, streak, episode in ((0, 1, None), (1, 2, "episode-A"), (3, 1, None), (4, 2, "episode-B")):
            points[index].update(score=5, exceeds_threshold=True, persistence_streak=streak, alert_episode_id=episode)
        window = result["ledger"]["incident_windows"][0]
        window.update(detected=True, matched_alert_episode_id="episode-A", alert_onset_timestamp=points[1]["timestamp"],
                      detection_delay_seconds=0, max_in_window_consecutive_exceedances=2, pre_event_support=True,
                      event_causal_support_qualified=False)
        valid = diagnostics._build_diagnostics_draft({"ledger": result["ledger"]}, result["provenance"], schema=self.schema)
        self.assertEqual(valid["ledger"]["incident_windows"][0]["matched_alert_episode_id"], "episode-A")
        window.update(matched_alert_episode_id="episode-B", alert_onset_timestamp=points[4]["timestamp"],
                      detection_delay_seconds=3, event_causal_support_qualified=True)
        result["aggregates"], result["reconciliation"] = diagnostics._build_aggregates(result["ledger"])
        with self.assertRaisesRegex(diagnostics.AnomalyFailureDiagnosticsError, "first new eligible onset"):
            diagnostics._validate_diagnostics_draft(result, self.schema)

    def test_new_offset_one_onset_cannot_be_declared_undetected(self):
        result = deepcopy(self.result)
        points = result["ledger"]["incident_points"][:7]
        points[1].update(score=5, exceeds_threshold=True, persistence_streak=1)
        points[2].update(score=5, exceeds_threshold=True, persistence_streak=2, alert_episode_id="episode-A")
        window = result["ledger"]["incident_windows"][0]
        window.update(detected=True, matched_alert_episode_id="episode-A", alert_onset_timestamp=points[2]["timestamp"],
                      detection_delay_seconds=1, max_in_window_consecutive_exceedances=2, event_causal_support_qualified=True)
        diagnostics._build_diagnostics_draft({"ledger": result["ledger"]}, result["provenance"], schema=self.schema)
        window.update(detected=False, matched_alert_episode_id=None, alert_onset_timestamp=None,
                      detection_delay_seconds=None, event_causal_support_qualified=False)
        result["aggregates"], result["reconciliation"] = diagnostics._build_aggregates(result["ledger"])
        with self.assertRaisesRegex(diagnostics.AnomalyFailureDiagnosticsError, "first new eligible onset"):
            diagnostics._validate_diagnostics_draft(result, self.schema)

    def test_prior_episode_continuation_does_not_mask_later_new_onset_or_allow_reuse(self):
        result = deepcopy(self.result)
        points = result["ledger"]["incident_points"][:7]
        for index, streak, episode in ((0, 3, "prior-A"), (1, 4, "prior-A"), (3, 1, None), (4, 2, "new-B")):
            points[index].update(score=5, exceeds_threshold=True, persistence_streak=streak, alert_episode_id=episode)
        window = result["ledger"]["incident_windows"][0]
        window.update(detected=True, matched_alert_episode_id="new-B", alert_onset_timestamp=points[4]["timestamp"],
                      detection_delay_seconds=3, max_in_window_consecutive_exceedances=2, pre_event_support=True,
                      event_causal_support_qualified=True)
        diagnostics._build_diagnostics_draft({"ledger": result["ledger"]}, result["provenance"], schema=self.schema)
        points[4]["alert_episode_id"] = "prior-A"
        with self.assertRaisesRegex(diagnostics.AnomalyFailureDiagnosticsError, "reuses an episode ID"):
            diagnostics._build_diagnostics_draft({"ledger": result["ledger"]}, result["provenance"], schema=self.schema)

    def test_fixed_event_compositions_match_all_twelve_matrix_layouts(self):
        matrix = json.loads((ROOT / diagnostics.EXPECTED_MATRIX_CONFIG_PATH).read_text(encoding="utf-8"))
        for layout in matrix["layouts"]:
            actual = []
            for event in layout["events"]:
                if event["event_class"] in ("machine_fault", "sensor_fault"):
                    actual.append((event["event_id"], event["event_class"], event["event_type"], layout["equipment_id"] + "." + event["signal_id"], layout["equipment_id"], layout["operating_mode"]))
            with self.subTest(layout=layout["layout_id"]):
                self.assertEqual(sorted(actual), sorted(diagnostics._expected_incident_composition(layout["layout_index"]).elements()))

    def test_one_episode_id_cannot_match_two_incident_signals_in_one_cell(self):
        result = deepcopy(self.result)
        for window in result["ledger"]["incident_windows"][:2]:
            points = [row for row in result["ledger"]["incident_points"] if (row["cell_id"], row["event_id"]) == (window["cell_id"], window["event_id"])]
            points[1].update(score=5, exceeds_threshold=True, persistence_streak=1)
            points[2].update(score=5, exceeds_threshold=True, persistence_streak=2, alert_episode_id="same-episode")
            window.update(detected=True, matched_alert_episode_id="same-episode", alert_onset_timestamp=points[2]["timestamp"],
                          detection_delay_seconds=1, max_in_window_consecutive_exceedances=2, event_causal_support_qualified=True)
        with self.assertRaisesRegex(diagnostics.AnomalyFailureDiagnosticsError, "multiple signal profiles"):
            diagnostics._build_diagnostics_draft({"ledger": result["ledger"]}, result["provenance"], schema=self.schema)

    def test_category_and_event_id_mutations_fail_after_aggregate_recomputation(self):
        changes = ({"event_class": "sensor_fault"}, {"event_type": "spike"}, {"signal_id": "motor-01.motor_temperature"},
                   {"event_class": "sensor_fault", "event_type": "spike", "signal_id": "motor-01.motor_temperature"},
                   {"event_id": "fabricated-event"}, {"event_id": ""})
        for change in changes:
            result = deepcopy(self.result)
            window = result["ledger"]["incident_windows"][0]
            identity = window["cell_id"], window["event_id"]
            window.update(change)
            for row in result["ledger"]["incident_points"]:
                if (row["cell_id"], row["event_id"]) == identity: row.update(change)
            result["aggregates"], result["reconciliation"] = diagnostics._build_aggregates(result["ledger"])
            with self.subTest(change=change), self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
                diagnostics._validate_diagnostics_draft(result, self.schema)

    def test_duplicate_cell_category_and_balanced_global_swap_are_rejected(self):
        for balanced in (False, True):
            result = deepcopy(self.result)
            first, second = result["ledger"]["incident_windows"][0], result["ledger"]["incident_windows"][3 if balanced else 1]
            fields = ("event_class", "event_type", "signal_id")
            first_category, second_category = {field: first[field] for field in fields}, {field: second[field] for field in fields}
            replacements = [(first, second_category), (second, first_category)] if balanced else [(second, first_category)]
            for window, change in replacements:
                for point in result["ledger"]["incident_points"]:
                    if (point["cell_id"], point["event_id"]) == (window["cell_id"], window["event_id"]): point.update(change)
                window.update(change)
            result["aggregates"], result["reconciliation"] = diagnostics._build_aggregates(result["ledger"])
            if balanced:
                self.assertEqual(result["aggregates"]["incident_window_aggregates"], self.result["aggregates"]["incident_window_aggregates"])
            with self.subTest(balanced=balanced), self.assertRaisesRegex(diagnostics.AnomalyFailureDiagnosticsError, "composition differs"):
                diagnostics._validate_diagnostics_draft(result, self.schema)

    def test_each_fixed_marginal_denominator_is_independent_of_aggregate_claims(self):
        for name, expected in diagnostics._INCIDENT_MARGINAL_COUNTS.items():
            result = deepcopy(self.result)
            window_row = next(row for row in result["aggregates"]["incident_window_aggregates"] if row["dimension"]["dimension_name"] == name)
            offset_row = next(row for row in result["aggregates"]["incident_offset_aggregates"] if row["dimension"]["dimension_name"] == name)
            self.assertEqual(window_row["denominator"], expected)
            self.assertEqual(offset_row["denominator"], expected * 7)
            window_row["denominator"] -= 1
            offset_row["denominator"] -= 7
            with self.subTest(name=name), self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
                diagnostics._validate_diagnostics_draft(result, self.schema)

    def test_fixed_pins_match_lf_files_and_inventory_erratum(self):
        self.assertEqual(diagnostics.EXPECTED_INPUT_ARTIFACT["inventory_sha256"], "2a4a62332c1c15c48b077aa59dbbccae01559558df162d5d1484aa1ae345af0e")
        for path, digest in ((diagnostics.CONFIG_PATH, diagnostics.EXPECTED_CONFIG_RAW_SHA256),
                             (diagnostics.SCHEMA_PATH, diagnostics.EXPECTED_CONFIG_SCHEMA_RAW_SHA256),
                             (diagnostics.RESULT_SCHEMA_PATH, diagnostics.EXPECTED_RESULT_SCHEMA_RAW_SHA256)):
            raw = (ROOT / path).read_bytes()
            self.assertNotIn(b"\r", raw)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), digest)

    def test_each_input_and_snapshot_digest_is_pinned(self):
        diagnostics._validate_provenance_semantics(self.result)
        for section, fields in (("input_artifact", ("result_sha256", "summary_sha256", "completion_marker_sha256", "inventory_sha256")),
                                ("input_snapshot", ("before_inventory_sha256", "after_inventory_sha256"))):
            for field in fields:
                result = deepcopy(self.result)
                result["provenance"][section][field] = "f" * 64
                with self.subTest(section=section, field=field), self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
                    diagnostics._validate_provenance_semantics(result)
        result = deepcopy(self.result)
        result["provenance"]["input_snapshot"].update(before_inventory_sha256="f" * 64, after_inventory_sha256="f" * 64)
        result["provenance"]["input_artifact"]["inventory_sha256"] = "f" * 64
        with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
            diagnostics._validate_provenance_semantics(result)

    def test_each_current_digest_and_semantic_digest_requires_lowercase_hex(self):
        for field in self.result["provenance"]["revision_compatibility"]["current_d2_diagnostics"]:
            for invalid in ("A" * 64, "g" * 64, "0" * 63):
                result = deepcopy(self.result)
                result["provenance"]["revision_compatibility"]["current_d2_diagnostics"][field] = invalid
                with self.subTest(field=field, invalid=invalid), self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
                    diagnostics._validate_provenance_semantics(result)
        for field in ("artifact_blob_sha256", "current_raw_sha256"):
            result = deepcopy(self.result)
            result["provenance"]["revision_compatibility"]["semantic_sources"][0][field] = "G" * 64
            with self.subTest(field=field), self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
                diagnostics._validate_provenance_semantics(result)
        result = deepcopy(self.result)
        record = result["provenance"]["revision_compatibility"]["semantic_sources"][0]
        record.update(artifact_blob_sha256="g" * 64, current_raw_sha256="g" * 64)
        with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
            diagnostics._validate_provenance_semantics(result)

    def test_current_only_order_is_fixed_and_other_order_rejected(self):
        expected = diagnostics.EXPECTED_REVISION_COMPATIBILITY["current_only_paths"]
        self.assertEqual(self.result["provenance"]["revision_compatibility"]["current_only_paths"], expected)
        result = deepcopy(self.result)
        result["provenance"]["revision_compatibility"]["current_only_paths"] = sorted(expected)
        with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
            diagnostics._validate_provenance_semantics(result)

    def test_threshold_boundary_unavailable_alert_and_continuity_mutations(self):
        changes = [
            {"score": 4, "exceeds_threshold": True, "persistence_streak": 1},
            {"score": 5, "exceeds_threshold": False},
            {"available": False, "score": None, "exclusion_reason": "quality_non_ok", "exceeds_threshold": True},
            {"score": 4, "alert_episode_id": "forbidden"},
            {"score": 5, "exceeds_threshold": True, "persistence_streak": 2},
            {"score": 5, "exceeds_threshold": True, "persistence_streak": 1, "alert_episode_id": "premature"},
            {"score": True}, {"score": float("nan")}, {"score": float("inf")}, {"persistence_streak": True},
        ]
        for change in changes:
            result = deepcopy(self.result)
            result["ledger"]["incident_points"][1].update(change)
            with self.subTest(change=change), self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
                diagnostics._validate_diagnostics_draft(result, self.schema)
        result = deepcopy(self.result)
        result["ledger"]["incident_points"][1]["score"] = 4
        diagnostics._validate_diagnostics_draft(result, self.schema)
        result = deepcopy(self.result)
        result["ledger"]["incident_points"][0].update(score=5, exceeds_threshold=True, persistence_streak=0)
        with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
            diagnostics._validate_diagnostics_draft(result, self.schema)

    def test_unmatched_prior_alert_does_not_change_canonical_detected(self):
        fixture = deepcopy(self.result)
        points = fixture["ledger"]["incident_points"]
        for index in (0, 1):
            points[index].update(score=5, exceeds_threshold=True, persistence_streak=index + 3, alert_episode_id="prior-unmatched")
        fixture["ledger"]["incident_windows"][0].update(pre_event_support=True, max_in_window_consecutive_exceedances=1)
        result = diagnostics._build_diagnostics_draft({"ledger": fixture["ledger"]}, fixture["provenance"], schema=self.schema)
        self.assertFalse(result["ledger"]["incident_windows"][0]["detected"])
        self.assertIsNone(result["ledger"]["incident_windows"][0]["matched_alert_episode_id"])
        self.assertFalse(result["ledger"]["incident_windows"][0]["event_causal_support_qualified"])
        result["ledger"]["incident_windows"][0].update(detected=True, matched_alert_episode_id="prior-unmatched",
                    alert_onset_timestamp=result["ledger"]["incident_points"][1]["timestamp"], detection_delay_seconds=0)
        with self.assertRaisesRegex(diagnostics.AnomalyFailureDiagnosticsError, "first new eligible onset"):
            diagnostics._build_diagnostics_draft({"ledger": result["ledger"]}, result["provenance"], schema=self.schema)

    def test_fake_layout_mapping_and_clean_dimension_replacement_fail(self):
        for change in ("layout", "equipment", "dimension", "order"):
            result = deepcopy(self.result)
            if change == "layout":
                original = result["ledger"]["availability"][0]["cell_id"]
                for rows in result["ledger"].values():
                    for row in rows:
                        if row["cell_id"] == original:
                            row.update(cell_id="seed-011-layout-00-fake", layout_id="fake")
            elif change == "equipment":
                result["ledger"]["clean_source_alerts"][0]["equipment_id"] = "motor-01"
            elif change == "dimension":
                result["aggregates"]["clean_alerts"][1] = deepcopy(result["aggregates"]["clean_alerts"][0])
            else:
                result["aggregates"]["availability"].reverse()
            with self.subTest(change=change), self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
                diagnostics._validate_diagnostics_draft(result, self.schema)

    def test_clean_membership_swap_within_one_equipment_group_fails(self):
        result = deepcopy(self.result)
        source = result["ledger"]["clean_source_alerts"][0]
        equipment = next(row for row in result["ledger"]["clean_equipment_alerts"] if row["equipment_episode_id"] == source["equipment_episode_id"])
        second_source, second_equipment = deepcopy(source), deepcopy(equipment)
        second_source.update(source_alert_episode_id="second-source", equipment_episode_id="second-equipment",
                             onset_timestamp="2026-01-01T00:00:03Z", end_timestamp="2026-01-01T00:00:04Z")
        second_equipment.update(equipment_episode_id="second-equipment", source_alert_episode_ids=["second-source"],
                                start_timestamp="2026-01-01T00:00:03Z", end_timestamp="2026-01-01T00:00:04Z")
        result["ledger"]["clean_source_alerts"].append(second_source)
        result["ledger"]["clean_equipment_alerts"].append(second_equipment)
        valid = diagnostics._build_diagnostics_draft({"ledger": result["ledger"]}, result["provenance"], schema=self.schema)
        source["equipment_episode_id"], second_source["equipment_episode_id"] = second_source["equipment_episode_id"], source["equipment_episode_id"]
        with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
            diagnostics._build_diagnostics_draft({"ledger": result["ledger"]}, result["provenance"], schema=self.schema)
        self.assertEqual(len(valid["ledger"]["clean_source_alerts"]), 241)

    def test_realistic_extraction_preserves_nine_offset_zero_detections_and_ids(self):
        replay = _single_cell_replay()
        first = replay["evaluations"][0]
        replay["evaluations"] = [deepcopy(first) for _ in range(9)]
        for seed, item in zip(diagnostics.EXPECTED_COUNTS["seed_values"], replay["evaluations"]):
            item["cell"].update(seed=seed, cell_id=f"seed-{seed:03d}-layout-00-motor-01-stopped")
        with _write_traps():
            ledger = diagnostics._build_ledgers_from_verified_replay(replay)
        self.assertEqual(len(ledger["incident_windows"]), 9)
        self.assertTrue(all(row["detected"] and row["pre_event_support"] and not row["event_causal_support_qualified"] for row in ledger["incident_windows"]))
        self.assertTrue(all(row["equipment_episode_id"] == "clean-000001" and row["mode_entry_offset"] == 1 for row in ledger["clean_source_alerts"]))
        self.assertEqual(ledger["clean_equipment_alerts"][0]["source_alert_episode_ids"], ["clean-source-local"])

    def test_capture_extraction_rejects_missing_duplicate_profile_and_legacy_shape(self):
        replay = _single_cell_replay()
        event = replay["evaluations"][0]["evaluation"]["incidents"][0]
        for change in ("missing", "duplicate", "profile", "all-profiles", "legacy", "gap", "clean-join", "clean-missing", "clean-duplicate"):
            invalid = deepcopy(replay)
            evaluation = invalid["evaluations"][0]["evaluation"]
            point = next(row for row in evaluation["scores"] if row["signal_id"] == event["signal_id"] and row["timestamp"] == event["event_start_timestamp"])
            if change == "missing": evaluation["scores"].remove(point)
            elif change == "duplicate": evaluation["scores"].append(deepcopy(point))
            elif change == "profile": point["profile_key"]["operating_mode"] = "startup"
            elif change == "all-profiles":
                for row in evaluation["scores"]: row["profile_key"]["equipment_id"] = "wrong-equipment"
            elif change == "gap": point["timestamp"] = "2026-01-01T00:00:00Z"
            elif change == "clean-join": evaluation["clean_false_alert_episodes"][0]["equipment_id"] = "motor-01"
            elif change == "clean-missing": evaluation["clean_false_alert_episodes"] = []
            elif change == "clean-duplicate": evaluation["alert_episodes"].append(deepcopy(evaluation["alert_episodes"][0]))
            else: evaluation["clean_false_alert_episodes"] = [{"episode_id": "legacy"}]
            with self.subTest(change=change), self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
                diagnostics._build_ledgers_from_verified_replay(invalid)

    def test_renderer_rejects_arbitrary_mapping_and_schema_injection(self):
        for value in ({}, self.result):
            with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
                render_summary(value)
        self.assertNotIn("cell_collector", inspect.signature(diagnostics._verify_input_replay).parameters)
        self.assertNotIn("schema", inspect.signature(diagnostics.replay_and_build_diagnostics_result).parameters)
        self.assertNotIn("schema", inspect.signature(render_summary).parameters)
        with self.assertRaises(TypeError):
            render_summary(self.result, {})

    def test_persistent_exceedance_cannot_drop_alert_link(self):
        result = deepcopy(self.result)
        result["ledger"]["incident_points"][0].update(score=5, exceeds_threshold=True, persistence_streak=2)
        with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
            diagnostics._validate_diagnostics_draft(result, self.schema)

    def test_incident_window_bounds_cannot_drift(self):
        for field, stamp in (("event_end_timestamp", "2025-12-31T23:59:59Z"),
                             ("detection_window_start", "2026-01-01T00:00:01Z"),
                             ("detection_window_end", "2026-01-01T00:00:05Z")):
            result = deepcopy(self.result)
            result["ledger"]["incident_windows"][0][field] = stamp
            with self.subTest(field=field), self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
                diagnostics._validate_diagnostics_draft(result, self.schema)

    def test_clean_merge_tie_break_is_formal_source_id_not_end_time(self):
        rows = [{"source_alert_episode_id": "alert-a", "onset_timestamp": "2026-01-01T00:00:00Z", "end_timestamp": "2026-01-01T00:00:03Z"},
                {"source_alert_episode_id": "alert-b", "onset_timestamp": "2026-01-01T00:00:00Z", "end_timestamp": "2026-01-01T00:00:01Z"}]
        merged = diagnostics._merged_clean_intervals(list(reversed(rows)))
        self.assertEqual(merged, [{"start_timestamp": "2026-01-01T00:00:00Z", "end_timestamp": "2026-01-01T00:00:03Z", "source_alert_episode_ids": ["alert-a", "alert-b"]}])

    def test_git_read_disables_optional_writes_fetch_and_fsmonitor(self):
        with patch.object(diagnostics.subprocess, "run") as run:
            run.return_value.returncode, run.return_value.stdout = 0, b"read-only"
            self.assertEqual(diagnostics._git_run(ROOT, "status", "--porcelain"), b"read-only")
        self.assertEqual(run.call_args.args[0][:3], ["git", "-c", "core.fsmonitor=false"])
        self.assertEqual(run.call_args.kwargs["env"]["GIT_OPTIONAL_LOCKS"], "0")
        self.assertEqual(run.call_args.kwargs["env"]["GIT_NO_LAZY_FETCH"], "1")

    def test_revision_positive_and_git_tree_mutations_without_checkout(self):
        head = "1" * 40
        historical = {f"src/banto_ai/historical-{index:03d}.py": (b"historical\n", "100644") for index in range(88)}
        current = {**historical, **{path: (b"diagnostics\n", "100644") for path in diagnostics.EXPECTED_REVISION_COMPATIBILITY["current_only_paths"]}}
        for change in (None, "dirty", "diff", "head", "mode", "link", "missing", "extra", "raw", "current-only-raw"):
            tree = deepcopy(current)
            workspace = {path: raw for path, (raw, _) in tree.items()}
            first = next(iter(historical))
            if change == "mode": tree[first] = (tree[first][0], "100755")
            elif change == "link": tree[first] = (tree[first][0], "120000")
            elif change == "missing": workspace.pop(first)
            elif change == "extra": workspace["src/banto_ai/extra.py"] = b"extra"
            elif change == "raw": workspace[first] += b"changed"
            elif change == "current-only-raw": workspace[diagnostics.CONFIG_PATH] += b"changed"

            def git_read(root, *args):
                if args[0] == "rev-parse": return (("2" * 40 if change == "head" else head) + "\n").encode()
                if args[0] == "status": return b" M file\n" if change == "dirty" else b""
                if args[0] == "diff": return b"diff" if change == "diff" else b""
                if args[0] == "ls-tree":
                    selected = historical if args[4] == diagnostics.EXPECTED_ARTIFACT_CODE_REVISION else tree
                    return b"".join(f"{mode} blob {'0' * 40}\t{path}\0".encode() for path, (_, mode) in selected.items())
                if args[0] == "cat-file":
                    revision, path = args[-1].split(":", 1)
                    return (historical if revision == diagnostics.EXPECTED_ARTIFACT_CODE_REVISION else tree)[path][0]
                raise AssertionError(f"unexpected git operation: {args}")

            with self.subTest(change=change), patch.object(diagnostics, "_git_run", side_effect=git_read), patch.object(diagnostics, "_workspace_regular_files", return_value=workspace), _write_traps():
                if change is None:
                    result = diagnostics._validate_revision_compatibility(ROOT, replay_head=head)
                    self.assertEqual(len(result["semantic_sources"]), 88)
                    self.assertEqual(result["current_only_paths"], diagnostics.EXPECTED_REVISION_COMPATIBILITY["current_only_paths"])
                else:
                    with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
                        diagnostics._validate_revision_compatibility(ROOT, replay_head=head)

    def test_source_and_artifact_walk_reject_reparse_points(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "src" / "banto_ai"
            source.mkdir(parents=True)
            (source / "regular.py").write_bytes(b"data")
            with _write_traps():
                self.assertEqual(diagnostics._workspace_regular_files(root, ["src/banto_ai"]), {"src/banto_ai/regular.py": b"data"})
                self.assertEqual(diagnostics._capture_tree_bytes(source, "fixture")["bytes"], {"regular.py": b"data"})
                with patch.object(diagnostics, "_is_reparse_point", side_effect=lambda path: path.name == "regular.py"):
                    with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
                        diagnostics._workspace_regular_files(root, ["src/banto_ai"])
                    with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
                        diagnostics._capture_tree_bytes(source, "fixture")

    def test_single_api_final_recheck_and_zero_writes(self):
        config, config_source, config_schema, result_schema = diagnostics._load_config(diagnostics.CONFIG_PATH, ROOT)
        _, analysis_source, analysis_schema = analysis._load_analysis_inputs(analysis.ANALYSIS_CONFIG_PATH, ROOT)
        sources, values = runner._snapshot_inputs(ROOT, ROOT / diagnostics.EXPECTED_MATRIX_CONFIG_PATH)
        provenance = self.result["provenance"]
        compatibility = deepcopy(provenance["revision_compatibility"])
        compatibility["replay_revision"] = deepcopy(provenance["replay_code_revision"])
        capture = {"bytes": {"synthetic-only.json": b"{}"}, "inventory": (("synthetic-only.json", "file"),), "hashes": {"synthetic-only.json": hashlib.sha256(b"{}").hexdigest()}}
        verified = {"diagnostics_config": config, "diagnostics_config_source": config_source,
                    "diagnostics_schema_source": config_schema, "diagnostics_result_schema_source": result_schema,
                    "analysis_source": analysis_source, "analysis_schema_source": analysis_schema,
                    "sources": sources, "values": values, "input_capture": capture,
                    "input_artifact": provenance["input_artifact"], "input_snapshot": provenance["input_snapshot"],
                    "revision_compatibility": compatibility, "replay_revision": compatibility["replay_revision"]}
        original_builder, original_strict = diagnostics._build_diagnostics_draft, diagnostics._strict_object
        original_recheck, original_issue = diagnostics._recheck_verified_replay_boundary, diagnostics.VerifiedDiagnosticsResult.__init__
        original_snapshot = diagnostics.anomaly_matrix._load_object_snapshot
        # Only the entry audit is stubbed: the real builder, fixed-schema verifier,
        # provenance assertion, source checks and final boundary all execute.
        for change in (None, "artifact", "config", "config-schema", "result-schema", "analysis-config", "analysis-schema", "matrix-source", "revision", "provenance"):
            state = {"built": False, "rechecked": False, "issued": 0}
            changed_paths = {"config": diagnostics.CONFIG_PATH, "config-schema": diagnostics.SCHEMA_PATH,
                             "result-schema": diagnostics.RESULT_SCHEMA_PATH, "analysis-config": analysis_source["path"],
                             "analysis-schema": analysis_schema["path"]}

            def build_then_drift(*args, **kwargs):
                result = original_builder(*args, **kwargs)
                self.assertEqual({field: result[field] for field in diagnostics._DRAFT_FLAGS}, diagnostics._DRAFT_FLAGS)
                state["built"] = True
                state["draft"] = result
                if change == "provenance": result["provenance"]["replay_code_revision"]["head"] = "f" * 40
                return result

            def recheck_then_allow_issue(*args):
                original_recheck(*args)
                state["rechecked"] = True

            def issue_only_after_recheck(instance, payload, **kwargs):
                self.assertTrue(state["rechecked"])
                state["issued"] += 1
                original_issue(instance, payload, **kwargs)

            def final_capture(*args, **kwargs):
                observed = deepcopy(capture)
                if state["built"] and change == "artifact": observed["bytes"]["synthetic-only.json"] = b"changed"
                return observed

            def final_strict(path, label):
                value, raw, raw_sha, canonical_sha = original_strict(path, label)
                if state["built"] and path == ROOT / changed_paths.get(change, "unused"):
                    raw += b" "
                return value, raw, raw_sha, canonical_sha

            def source_read(path, label):
                value, raw, raw_sha, canonical_sha = original_snapshot(path, label)
                if state["built"] and change == "matrix-source" and path == sources["matrix_config"]["_resolved"]:
                    raw += b" "
                return value, raw, raw_sha, canonical_sha

            def revision_read(*args, **kwargs):
                observed = deepcopy(compatibility)
                if state["built"] and change == "revision": observed["current_d2_diagnostics"]["module_raw_sha256"] = "f" * 64
                return observed

            with self.subTest(change=change), ExitStack() as stack:
                stack.enter_context(patch.object(diagnostics, "_verify_input_replay", return_value=deepcopy(verified)))
                stack.enter_context(patch.object(diagnostics, "_build_ledgers_from_verified_replay", return_value=self.result["ledger"]))
                stack.enter_context(patch.object(diagnostics, "_build_diagnostics_draft", side_effect=build_then_drift))
                stack.enter_context(patch.object(diagnostics, "_recheck_verified_replay_boundary", side_effect=recheck_then_allow_issue))
                stack.enter_context(patch.object(diagnostics.VerifiedDiagnosticsResult, "__init__", issue_only_after_recheck))
                stack.enter_context(patch.object(diagnostics, "_capture_tree_bytes", side_effect=final_capture))
                stack.enter_context(patch.object(diagnostics, "_strict_object", side_effect=final_strict))
                stack.enter_context(patch.object(diagnostics, "_validate_revision_compatibility", side_effect=revision_read))
                stack.enter_context(patch.object(diagnostics.anomaly_matrix, "_load_object_snapshot", side_effect=source_read))
                original_safe = diagnostics.anomaly_matrix._safe_repo_path
                stack.enter_context(patch.object(diagnostics.anomaly_matrix, "_safe_repo_path", side_effect=lambda root, path, label, **kwargs: root / path if path == diagnostics.EXPECTED_INPUT_ROOT else original_safe(root, path, label, **kwargs)))
                stack.enter_context(_write_traps())
                if change is None:
                    result = diagnostics.replay_and_build_diagnostics_result(ROOT, replay_head=compatibility["replay_revision"]["head"])
                    self.assertIs(type(result), diagnostics.VerifiedDiagnosticsResult)
                    self.assertEqual({field: result[field] for field in diagnostics._COMPLETE_FLAGS}, diagnostics._COMPLETE_FLAGS)
                    self.assertEqual(result["provenance"], provenance)
                    self.assertEqual(result["counts"], diagnostics.EXPECTED_COUNTS)
                    first = render_summary(result)
                    self.assertEqual(first, render_summary(deepcopy(result)))
                    self.assertNotIn(b"\r", first)
                    self.assertTrue(first.endswith(b"\n"))
                    self.assertIn("異常検知".encode("utf-8"), first)
                    detached = result["ledger"]
                    detached["incident_windows"][0]["detected"] = True
                    state["draft"]["counts"]["cells"] = 999
                    self.assertEqual(render_summary(result), first)
                    with self.assertRaises(TypeError): result["status"] = "draft"
                    with self.assertRaises(TypeError): result.status = "draft"
                    with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError): render_summary(dict(result))
                else:
                    with self.assertRaises((diagnostics.AnomalyFailureDiagnosticsError, runner.AnomalyMatrixRunnerError)):
                        diagnostics.replay_and_build_diagnostics_result(ROOT, replay_head=compatibility["replay_revision"]["head"])
                self.assertTrue(state["built"])
                self.assertEqual(state["issued"], 1 if change is None else 0)

    def test_replay_adapter_captures_120_cells_and_rejects_helper_drift(self):
        """Exercise the adapter, not the formal evaluator: all artifacts are synthetic.

        Only this test patches the artifact pin for its synthetic inventory. Fixed
        real pins are checked separately; no formal artifact is opened or produced.
        """
        loaded = diagnostics._load_config(diagnostics.CONFIG_PATH, ROOT)
        analysis_loaded = analysis._load_analysis_inputs(analysis.ANALYSIS_CONFIG_PATH, ROOT)
        sources, values = runner._snapshot_inputs(ROOT, ROOT / diagnostics.EXPECTED_MATRIX_CONFIG_PATH)
        values["matrix_result_schema"] = {}  # Formal schema/evaluation delegate is deliberately stubbed.
        compatibility = deepcopy(self.result["provenance"]["revision_compatibility"])
        compatibility["replay_revision"] = deepcopy(self.result["provenance"]["replay_code_revision"])
        input_root = ROOT / diagnostics.EXPECTED_INPUT_ROOT
        cells, payloads, cell_outputs = [], {}, {}
        directories = {"configs", "configs/generator", "configs/evaluator", "datasets", "evaluations"}
        for seed in diagnostics.EXPECTED_COUNTS["seed_values"]:
            for layout in values["matrix_config"]["layouts"]:
                expected = runner._materialize_cell(values["matrix_config"], values["base_generator_config"], seed, layout, ROOT, input_root)
                cell = {key: expected[key] for key in ("cell_id", "seed", "layout_id", "layout_index")}
                cell["status"] = "success"
                cells.append(cell)
                evaluation = {"synthetic_cell_id": cell["cell_id"]}
                generator_path = expected["paths"]["generator_config"].relative_to(input_root).as_posix()
                evaluator_path = expected["paths"]["evaluator_config"].relative_to(input_root).as_posix()
                evaluation_dir = expected["paths"]["evaluation"].relative_to(input_root).as_posix()
                files = {generator_path, evaluator_path, evaluation_dir + "/result.json"}
                payloads[generator_path] = analysis._json_bytes(expected["generator_config"])
                payloads[evaluator_path] = analysis._json_bytes(expected["evaluator_config"])
                payloads[evaluation_dir + "/result.json"] = analysis._json_bytes(evaluation)
                directories.add(evaluation_dir)
                cell_outputs[cell["cell_id"]] = (evaluation, expected, files, {evaluation_dir})
        result = {"cells": cells}
        summary = b"synthetic adapter summary\n"
        payloads["result.json"] = analysis._json_bytes(result)
        payloads["summary.md"] = summary
        marker = {"schema_version": runner.SCHEMA_VERSION, "marker_type": runner.COMPLETION_MARKER_TYPE,
                  "result_sha256": diagnostics._strict_bytes(payloads["result.json"], "fixture")[1],
                  "summary_sha256": hashlib.sha256(summary).hexdigest()}
        payloads[".complete"] = analysis._json_bytes(marker)

        for change in (None, "evaluation", "generator-raw", "evaluator-raw", "missing-summary", "extra-file", "after-capture"):
            captured = deepcopy(payloads)
            first = cell_outputs[cells[0]["cell_id"]]
            if change in ("generator-raw", "evaluator-raw"):
                field = "generator_config" if change == "generator-raw" else "evaluator_config"
                captured[first[1]["paths"][field].relative_to(input_root).as_posix()] += b"\n"
            elif change == "missing-summary": captured.pop("summary.md")
            elif change == "extra-file": captured["extra.json"] = b"{}"
            inventory = tuple(sorted([(path, "file") for path in captured] + [(path, "directory") for path in directories]))
            capture = {"bytes": captured, "inventory": inventory, "hashes": {path: hashlib.sha256(raw).hexdigest() for path, raw in sorted(captured.items())}}
            snapshot = {key: capture[key] for key in ("inventory", "hashes")}
            synthetic_pin = {**diagnostics.EXPECTED_INPUT_ARTIFACT, "result_sha256": marker["result_sha256"],
                             "summary_sha256": marker["summary_sha256"],
                             "completion_marker_sha256": diagnostics._strict_bytes(payloads[".complete"], "fixture")[1],
                             "inventory_sha256": hashlib.sha256(diagnostics._canonical_json(snapshot)).hexdigest()}
            config, config_source, config_schema, result_schema = deepcopy(loaded)
            config["expected_input_artifact"] = synthetic_pin
            config_raw = analysis._json_bytes(config)
            config_source.update(raw=config_raw, raw_sha256=hashlib.sha256(config_raw).hexdigest(), canonical_sha256=hashlib.sha256(diagnostics._canonical_json(config)).hexdigest())
            original_strict, original_safe = diagnostics._strict_object, diagnostics.anomaly_matrix._safe_repo_path

            def strict_read(path, label):
                if path == ROOT / diagnostics.CONFIG_PATH:
                    return config, config_raw, config_source["raw_sha256"], config_source["canonical_sha256"]
                return original_strict(path, label)

            def formal_cell(cell, matrix, base, root, artifact_root, cell_sources, cell_values, revision):
                self.assertEqual(revision, compatibility["artifact_revision"])
                evaluation, expected, files, dirs = deepcopy(cell_outputs[cell["cell_id"]])
                if change == "evaluation": evaluation["changed-on-disk"] = True
                return evaluation, expected, files, dirs

            after = deepcopy(snapshot)
            if change == "after-capture": after["hashes"]["result.json"] = "f" * 64
            with self.subTest(change=change), ExitStack() as stack:
                stack.enter_context(patch.object(diagnostics, "EXPECTED_INPUT_ARTIFACT", synthetic_pin))
                stack.enter_context(patch.object(diagnostics, "_load_config", return_value=(config, config_source, config_schema, result_schema)))
                stack.enter_context(patch.object(diagnostics, "_strict_object", side_effect=strict_read))
                stack.enter_context(patch.object(diagnostics, "_validate_revision_compatibility", return_value=compatibility))
                stack.enter_context(patch.object(diagnostics, "_capture_tree_bytes", return_value=capture))
                stack.enter_context(patch.object(analysis, "_load_analysis_inputs", return_value=analysis_loaded))
                stack.enter_context(patch.object(runner, "_snapshot_inputs", return_value=(sources, values)))
                stack.enter_context(patch.object(runner, "_matrix_summary", return_value=summary))
                aggregate_check = stack.enter_context(patch.object(runner, "_verify_aggregate_result"))
                provenance_check = stack.enter_context(patch.object(analysis, "_verify_source_provenance"))
                cell_check = stack.enter_context(patch.object(analysis, "_verify_cell_and_collect", side_effect=formal_cell))
                stack.enter_context(patch.object(runner, "_tree_snapshot", return_value=after))
                # Sources remain real: restore the formal schema value for their unchanged check.
                source_values = {**values, "matrix_result_schema": json.loads(sources["matrix_result_schema"]["_raw"])}
                original_unchanged = runner._assert_inputs_unchanged
                stack.enter_context(patch.object(runner, "_assert_inputs_unchanged", side_effect=lambda root, entries, _, boundary: original_unchanged(root, entries, source_values, boundary)))
                stack.enter_context(patch.object(diagnostics.anomaly_matrix, "_safe_repo_path", side_effect=lambda root, path, label, **kwargs: root / path if path == diagnostics.EXPECTED_INPUT_ROOT else original_safe(root, path, label, **kwargs)))
                stack.enter_context(_write_traps())
                if change is None:
                    verified = diagnostics._verify_input_replay(ROOT, replay_head=compatibility["replay_revision"]["head"])
                    self.assertEqual(len(verified["evaluations"]), 120)
                    self.assertEqual(cell_check.call_count, 120)
                    aggregate_check.assert_called_once()
                    self.assertEqual(provenance_check.call_args.args[-1], compatibility["artifact_revision"])
                    self.assertEqual(verified["input_capture"], capture)
                    self.assertIsNot(verified["evaluations"][0]["evaluation"], first[0])
                else:
                    with self.assertRaises(diagnostics.AnomalyFailureDiagnosticsError):
                        diagnostics._verify_input_replay(ROOT, replay_head=compatibility["replay_revision"]["head"])


if __name__ == "__main__":
    unittest.main()
