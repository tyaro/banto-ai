from __future__ import annotations

import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import banto_ai.anomaly_failure_diagnostics as diagnostics
from banto_ai.manifest import ManifestValidationError


ROOT = Path(__file__).resolve().parents[1]


def _complete_result_fixture() -> dict[str, object]:
    digest = "0" * 64
    revision = {"status": "git", "head": "0" * 40, "dirty": False, "diff_sha256": digest}
    source = {"path": "config.json", "sha256": digest}
    event_classes = ["machine_fault", "sensor_fault"]
    event_types = ["jam_or_slip", "spike"]
    incident_signal_ids = ["motor-01.motor_current", "conveyor-01.conveyor_speed", "motor-01.motor_temperature", "conveyor-01.motor_temperature"]
    signal_ids = ["motor-01.motor_current", "motor-01.motor_temperature", "motor-01.conveyor_speed", "motor-01.vibration_feature", "conveyor-01.motor_current", "conveyor-01.motor_temperature", "conveyor-01.conveyor_speed", "conveyor-01.vibration_feature"]
    equipment_ids = ["motor-01", "conveyor-01"]
    operating_modes = ["stopped", "startup", "low_speed", "nominal", "high_load", "cooldown"]
    windows = []
    points = []
    for index in range(240):
        cell_id = f"cell-{index:03d}"
        window = {
            "cell_id": cell_id, "seed": 11, "layout_id": "layout-0", "layout_index": 0,
            "event_id": f"event-{index:03d}", "event_class": event_classes[index % 2], "event_type": event_types[index % 2],
            "equipment_id": equipment_ids[index % 2], "signal_id": incident_signal_ids[index % 4], "operating_mode": operating_modes[index % 6],
            "event_start_timestamp": "2026-01-01T00:00:00Z", "event_end_timestamp": "2026-01-01T00:01:00Z",
            "detection_window_start": "2026-01-01T00:00:00Z", "detection_window_end": "2026-01-01T00:00:06Z",
            "detected": False, "matched_alert_episode_id": None, "alert_onset_timestamp": None,
            "detection_delay_seconds": None, "max_in_window_consecutive_exceedances": 0,
            "pre_event_support": False, "event_causal_support_qualified": False,
        }
        windows.append(window)
        for offset in (-1, 0, 1, 2, 3, 4, 5):
            points.append({
                "cell_id": cell_id, "seed": 11, "layout_id": "layout-0", "layout_index": 0,
                "event_id": window["event_id"], "event_class": window["event_class"], "event_type": window["event_type"],
                "equipment_id": window["equipment_id"], "signal_id": window["signal_id"], "operating_mode": window["operating_mode"],
                "offset": offset, "timestamp": "2026-01-01T00:00:00Z", "quality_status": "ok",
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
                common = {"cell_id": f"cell-{cell_index:03d}", "seed": (11, 17, 23, 29, 37, 42, 53, 67, 79, 97)[cell_index // 12], "layout_id": f"layout-{layout_index}", "layout_index": layout_index, "equipment_id": signal_id.split(".", 1)[0], "signal_id": signal_id, "operating_mode": mode}
                availability.append({**common, "available_points": 30, "total_points": 30, "exclusion_counts": dict(availability_exclusions)})
                calibration.append({**common, "calibration_point_count": 1, "center": 0, "mad": 0, "scale": 1, "status": "calibrated", "excluded_counts": dict(calibration_exclusions), "reason": None})
    clean_sources = []
    clean_equipment = []
    clean_reconciliation = []
    for cell_index in range(120):
        cell_id = f"cell-{cell_index:03d}"
        for equipment_id in equipment_ids:
            episode_id = f"equipment-episode-{cell_index:03d}-{equipment_id}"
            source_id = f"source-episode-{cell_index:03d}-{equipment_id}"
            layout_index = cell_index % 12
            seed = (11, 17, 23, 29, 37, 42, 53, 67, 79, 97)[cell_index // 12]
            layout_id = f"layout-{layout_index}"
            clean_sources.append({"cell_id": cell_id, "seed": seed, "layout_id": layout_id, "layout_index": layout_index, "source_alert_episode_id": source_id, "equipment_id": equipment_id, "signal_id": signal_ids[0], "operating_mode": operating_modes[0], "onset_timestamp": "2026-01-01T00:00:00Z", "end_timestamp": "2026-01-01T00:00:01Z", "point_count": 1, "max_score": 0, "mode_entry_offset": 0, "equipment_episode_id": episode_id})
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
            "artifact_code_revision": revision,
            "replay_code_revision": revision,
            "input_artifact": {
                "path": "artifacts/input",
                "result_sha256": digest,
                "summary_sha256": digest,
                "completion_marker_sha256": digest,
                "inventory_sha256": digest,
            },
            "input_snapshot": {
                "before_inventory_sha256": digest,
                "after_inventory_sha256": digest,
                "equal": True,
            },
            "revision_compatibility": {
                "policy": "artifact_revision_full_regular_file_tree_bytes_must_match_current_workspace",
                "artifact_revision": revision,
                "semantic_sources": [],
                "current_only_paths": [],
                "current_d2_diagnostics": {
                    "module_raw_sha256": digest,
                    "cli_raw_sha256": digest,
                    "renderer_raw_sha256": digest,
                    "schema_raw_sha256": digest,
                    "config_raw_sha256": digest,
                },
            },
            "config": source,
            "config_schema": {"path": "schema.json", "sha256": digest},
            "result_schema": {"path": "result-schema.json", "sha256": digest},
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


if __name__ == "__main__":
    unittest.main()
