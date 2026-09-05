"""D1 contract validator for exploratory v0.2 anomaly failure diagnostics."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from pathlib import PureWindowsPath
from typing import Any, Mapping

from . import anomaly_matrix
from .manifest import ManifestValidationError, validate


SCHEMA_VERSION = "0.1"
CONFIG_TYPE = "event-aware-anomaly-failure-diagnostics-config"
RESULT_TYPE = "event-aware-anomaly-failure-diagnostics"
DIAGNOSTICS_ID = "anomaly-multiseed-v02-diagnostics-v01"
CONFIG_PATH = "examples/configs/anomaly-multiseed-failure-diagnostics-v0.1.json"
SCHEMA_PATH = "schemas/anomaly-multiseed-failure-diagnostics-config-v0.1.schema.json"
RESULT_SCHEMA_PATH = "schemas/anomaly-multiseed-failure-diagnostics-result-v0.1.schema.json"
EXPECTED_MATRIX_ID = "anomaly-multiseed-v02"
EXPECTED_MATRIX_CONFIG_PATH = "examples/configs/anomaly-multiseed-v0.2.json"
EXPECTED_MATRIX_CONFIG_CANONICAL_SHA256 = "3e206fc6c988850953d7ddd739a0504cb8cdd92f6726848b78ce4803461daa26"
EXPECTED_MATRIX_RESULT_SCHEMA_PATH = "schemas/anomaly-multiseed-matrix-result-v0.2.schema.json"
EXPECTED_MATRIX_RESULT_SCHEMA_CANONICAL_SHA256 = "79acd31482bae6702dcb6bf6145a58342730a0b61c053592a720fa9e01e53326"
EXPECTED_INPUT_ROOT = "artifacts/anomaly-multiseed-v02"
EXPECTED_OUTPUT_ROOT = "artifacts/anomaly-multiseed-v02-diagnostics-v01"
EXPECTED_ARTIFACT_CODE_REVISION = "15a0f60433703c32a1bfa989f7f779c6828a1096"
EXPECTED_CONFIG_CANONICAL_SHA256 = "7355894316ba3fe48895196213c8c4973b11322c71986701172a4a637deff349"
EXPECTED_SCHEMA_CANONICAL_SHA256 = "b3353de2abf637ad564cc1db6d3eec816bc7fe750ed97982bb8dd4c829b57136"
EXPECTED_RESULT_SCHEMA_CANONICAL_SHA256 = "218a69829815c766d5edd888ea01567d113ad2745bf5b4c9ab7ba029fe53c17d"
CANONICALIZATION_ID = "utf-8-json-sort-keys-compact-no-trailing-newline-v1"
CANONICAL_SIGNAL_IDS = (
    "motor-01.motor_current", "motor-01.motor_temperature", "motor-01.conveyor_speed", "motor-01.vibration_feature",
    "conveyor-01.motor_current", "conveyor-01.motor_temperature", "conveyor-01.conveyor_speed", "conveyor-01.vibration_feature",
)
CANONICAL_OPERATING_MODES = ("stopped", "startup", "low_speed", "nominal", "high_load", "cooldown")
CANONICAL_EQUIPMENT_IDS = ("motor-01", "conveyor-01")
CANONICAL_SIGNAL_MODE_PAIRS = {(signal_id, operating_mode) for signal_id in CANONICAL_SIGNAL_IDS for operating_mode in CANONICAL_OPERATING_MODES}

EXPECTED_INPUT_ARTIFACT = {
    "result_path": "result.json",
    "summary_path": "summary.md",
    "completion_marker_path": ".complete",
    "result_sha256": "7bc546936c1a99100204d7fe2852b9dd8c500ac0dd2e3c3d7ccbc139c918de31",
    "summary_sha256": "e132b3ea14e06be94b4df0cd4b052b1f270797744ca532fb333f1d0e94e289f9",
    "completion_marker_sha256": "cc58b420901c9d31a415a89808d882c5b9a7d2936d0923e4102cee1acce85995",
    "inventory_sha256": "2a4a62332c1c15c48b077aa59dbbccae01559558df162d5d1484aa1ae345af0",
}
EXPECTED_COUNTS = {
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
        "clean_aggregate_rows": "8+6+48+2+30=94",
        "incident_window_aggregate_rows": "2+2+4+2+6=16",
        "incident_offset_aggregate_rows": "16*7=112",
        "clean_reconciliation_rows": "cells*equipment=120*2=240",
        "availability_aggregate_rows": "8*6=48",
        "calibration_aggregate_rows": "8*6=48",
    },
}
EXPECTED_LEDGER_CONTRACT = {
    "incident_windows": {
        "offset_basis": "event_start_sample_relative",
        "pre_event_support_offsets": [-1],
        "detection_window_offsets": [0, 1, 2, 3, 4, 5],
        "window_boundary": "[start,end)",
        "event_id_scope": "cell_local",
        "fully_qualified_signal": True,
        "window_key_fields": ["cell_id", "seed", "layout_id", "layout_index", "event_id"],
        "window_fields": [
            "cell_id", "seed", "layout_id", "layout_index", "event_id", "event_class", "event_type",
            "equipment_id", "signal_id", "operating_mode", "event_start_timestamp", "event_end_timestamp",
            "detection_window_start", "detection_window_end", "detected", "matched_alert_episode_id",
            "alert_onset_timestamp", "detection_delay_seconds", "max_in_window_consecutive_exceedances",
            "pre_event_support", "event_causal_support_qualified",
        ],
        "point_key_fields": ["cell_id", "seed", "layout_id", "layout_index", "event_id", "offset"],
        "point_fields": [
            "cell_id", "seed", "layout_id", "layout_index", "event_id", "event_class", "event_type",
            "equipment_id", "signal_id", "operating_mode", "offset", "timestamp", "quality_status",
            "actual", "previous_actual", "residual", "available", "exclusion_reason", "score",
            "exceeds_threshold", "persistence_streak", "alert_episode_id",
        ],
        "aggregation_dimensions": ["event_class", "event_type", "signal_id", "equipment_id", "operating_mode"],
        "canonical_detection_field": "detected",
        "exploratory_support_field": "event_causal_support_qualified",
        "consecutive_definition": "available_and_exceeds_threshold_contiguous_at_sampling_interval",
        "cardinality_rule": "event_rows=480; eligible_incident_windows=240; pre_event_support_rows=240; detection_window_point_rows=1440; combined_incident_point_rows=1680",
        "aggregate_shapes": {
            "incident_window_aggregates": ["dimension", "count_unit", "scope", "denominator", "window_count", "detected_count", "event_causal_support_qualified_count", "pre_event_support_count", "max_consecutive_run_distribution"],
            "incident_offset_aggregates": ["dimension", "count_unit", "scope", "denominator", "offset", "total_count", "available_count", "exceed_count"],
        },
        "aggregate_row_counts": {"incident_window_aggregates": 16, "incident_offset_aggregates": 112},
        "run_distribution": {"bins": [0, 1, 2, 3, 4, 5, 6], "sum_rule": "sum(window_count)=window_count"},
        "marginal_domains": {
            "event_class": ["machine_fault", "sensor_fault"],
            "event_type": ["jam_or_slip", "spike"],
            "signal_id": ["motor-01.motor_current", "conveyor-01.conveyor_speed", "motor-01.motor_temperature", "conveyor-01.motor_temperature"],
            "equipment_id": ["motor-01", "conveyor-01"],
            "operating_mode": ["stopped", "startup", "low_speed", "nominal", "high_load", "cooldown"],
        },
        "marginal_denominators": {"event_class": 120, "event_type": 120, "signal_id": 60, "equipment_id": 120, "operating_mode": 40},
        "semantic_verification": {
            "composite_key_uniqueness": ["incident_window=(cell_id,seed,layout_id,layout_index,event_id)", "incident_point=(incident_window_key,offset)"],
            "offset_cardinality": {"-1": 240, "0": 240, "1": 240, "2": 240, "3": 240, "4": 240, "5": 240},
            "counts_reconciliation": ["incident_windows=eligible_incident_windows", "incident_points=pre_event_support_rows+detection_window_point_rows", "aggregate offsets reconcile to incident points"],
        },
        "causal_support": {
            "formula": "detected is true AND matched alert onsetから persistence_points 個をsampling intervalで後方追跡した全support rowsがavailable=true、exceeds=true、連続、同一signal/mode/profileで、全timestamp/offsetがevent_start以降（offset>=0）",
            "false_for": ["undetected", "unmatched", "missing_alert_onset"],
            "canonical_detection_immutable": True,
            "later_in_window_run_cannot_replace_onset": True,
        },
    },
    "clean_alerts": {
        "source_partition": "clean_false_alert",
        "fully_qualified_signal": True,
        "source_key_fields": ["cell_id", "source_alert_episode_id"],
        "source_fields": ["cell_id", "seed", "layout_id", "layout_index", "source_alert_episode_id", "equipment_id", "signal_id", "operating_mode", "onset_timestamp", "end_timestamp", "point_count", "max_score", "mode_entry_offset", "equipment_episode_id"],
        "equipment_key_fields": ["cell_id", "equipment_episode_id"],
        "equipment_fields": ["cell_id", "seed", "layout_id", "layout_index", "equipment_episode_id", "equipment_id", "start_timestamp", "end_timestamp", "source_alert_episode_ids", "merge_size"],
        "dimensions": ["signal_id", "operating_mode", "signal_id×operating_mode", "equipment_id", "mode_entry_offset"],
        "merge_boundary": "[start,end)",
        "reconciliation_fields": ["source_alert_episode_ids", "equipment_episode_id", "merge_size", "source_count", "equipment_count", "source_ids_scope", "source_ids_exact", "merge_size_rule", "source_count_rule", "interval_merge_replay"],
        "reconciliation_rule": "signal_source_episodes_reconcile_exactly_to_equipment_merged_episodes",
        "interval_reconciliation_rule": "source_intervals_union_exactly_equals_equipment_interval_under_[start,end)_boundary",
        "source_join_scope": "cell_local_only",
        "source_exactly_once": True,
        "merge_size_rule": "merge_size=len(source_alert_episode_ids)",
        "source_count_rule": "source_count=sum(len(source_alert_episode_ids)) within each cell/equipment",
        "equipment_attribution_rule": "equipment_episode_count=count of cell-local merged equipment episodes whose equipment_id equals dimension_value, each episode counted exactly once",
        "marginal_dimension_exact_once": "all fixed domain categories emit exactly once, including mode_entry_offset 0..29",
        "reconciliation_row_count": 240,
        "reconciliation_grain": "cell×equipment_id",
        "aggregate_shapes": {
            "source_aggregates": ["dimension", "count_unit", "scope", "source_episode_count"],
            "equipment_aggregates": ["dimension", "count_unit", "scope", "equipment_episode_count", "equipment_attribution_rule"],
            "dimension_types": ["signal_id", "operating_mode", "signal_id×operating_mode", "equipment_id", "mode_entry_offset"],
            "fixed_dimension_row_counts": {"signal_id": 8, "operating_mode": 6, "signal_id×operating_mode": 48, "equipment_id": 2, "mode_entry_offset": 30},
            "fixed_domains": {"signal_id": ["motor-01.motor_current", "motor-01.motor_temperature", "motor-01.conveyor_speed", "motor-01.vibration_feature", "conveyor-01.motor_current", "conveyor-01.motor_temperature", "conveyor-01.conveyor_speed", "conveyor-01.vibration_feature"], "operating_mode": ["stopped", "startup", "low_speed", "nominal", "high_load", "cooldown"], "equipment_id": ["motor-01", "conveyor-01"], "mode_entry_offset": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29]},
            "count_units": {"source_dimensions": "source_alert_episodes", "equipment_dimension": "equipment_merged_episodes"},
            "mode_entry_offset_definition": "integer sample offset from source onset to containing generator regime start",
        },
    },
    "availability": {
        "dimensions": ["signal_id", "operating_mode", "exclusion_reason"],
        "fully_qualified_signal": True,
        "reconciliation_rule": "available_points_plus_exclusions_equals_total_points",
        "row_grain": "cell×fully-qualified signal×mode",
        "row_fields": ["cell_id", "seed", "layout_id", "layout_index", "equipment_id", "signal_id", "operating_mode", "available_points", "total_points", "exclusion_counts"],
        "exact_exclusion_reasons": ["quality_non_ok", "previous_quality_non_ok", "mode_boundary", "gap", "previous_event_overlap", "profile_inconclusive", "no_previous_observation", "nonfinite_value", "previous_nonfinite_value", "nonfinite_residual", "nonfinite_score"],
        "fixed_domains": {"signal_id": ["motor-01.motor_current", "motor-01.motor_temperature", "motor-01.conveyor_speed", "motor-01.vibration_feature", "conveyor-01.motor_current", "conveyor-01.motor_temperature", "conveyor-01.conveyor_speed", "conveyor-01.vibration_feature"], "operating_mode": ["stopped", "startup", "low_speed", "nominal", "high_load", "cooldown"], "equipment_id": ["motor-01", "conveyor-01"]},
        "exact_cartesian_rule": "all cells emit each of 8 signal_id×6 operating_mode pairs exactly once; no missing, duplicate, or unknown pair",
        "equipment_prefix_rule": "equipment_id equals signal_id prefix before first dot",
        "cardinality_rule": "availability_group_rows=5760; points_per_cell_signal_mode=30; total_points=172800; aggregate_signal_mode_groups=48; aggregate_points_per_signal_mode=3600",
        "aggregate_row_count": 48,
        "points_per_cell_signal_mode": 30,
        "aggregate_points_per_signal_mode": 3600,
        "reason_families": {
            "quality_dropout": ["quality_non_ok", "previous_quality_non_ok"],
            "mode_boundary": ["mode_boundary"],
            "gap": ["gap"],
            "event_overlap": ["previous_event_overlap"],
            "profile_inconclusive": ["profile_inconclusive"],
            "other": ["no_previous_observation", "nonfinite_value", "previous_nonfinite_value", "nonfinite_residual", "nonfinite_score"],
        },
    },
    "calibration": {
        "dimensions": ["equipment_id", "signal_id", "operating_mode", "seed", "cell_id"],
        "fixed_domains": {"signal_id": ["motor-01.motor_current", "motor-01.motor_temperature", "motor-01.conveyor_speed", "motor-01.vibration_feature", "conveyor-01.motor_current", "conveyor-01.motor_temperature", "conveyor-01.conveyor_speed", "conveyor-01.vibration_feature"], "operating_mode": ["stopped", "startup", "low_speed", "nominal", "high_load", "cooldown"], "equipment_id": ["motor-01", "conveyor-01"]},
        "exact_cartesian_rule": "all cells emit each of 8 signal_id×6 operating_mode pairs exactly once; no missing, duplicate, or unknown pair",
        "equipment_prefix_rule": "equipment_id equals signal_id prefix before first dot",
        "unique_key_fields": ["cell_id", "seed", "layout_id", "layout_index", "equipment_id", "signal_id", "operating_mode"],
        "row_count": 5760,
        "required_fields": ["calibration_point_count", "center", "mad", "scale", "status", "excluded_counts", "reason"],
        "distribution_fields": ["calibration_point_count", "center", "mad", "scale", "status", "reason"],
        "excluded_count_keys": ["event_overlap", "nonfinite", "quality_non_ok", "residual_unavailable"],
        "aggregate_grain": "signal_id×operating_mode",
        "aggregate_row_count": 48,
        "aggregate_profiles_per_group": 120,
        "aggregate_seed_summary_count": 10,
        "aggregate_profiles_per_seed_summary": 12,
    },
}
EXPECTED_REVISION_COMPATIBILITY = {
    "artifact_revision": EXPECTED_ARTIFACT_CODE_REVISION,
    "policy": "artifact_revision_full_regular_file_tree_bytes_must_match_current_workspace",
    "artifact_source_prefixes": ["src/banto_ai", "schemas", "examples/configs"],
    "current_only_paths": [
        "src/banto_ai/anomaly_failure_diagnostics.py",
        "examples/configs/anomaly-multiseed-failure-diagnostics-v0.1.json",
        "schemas/anomaly-multiseed-failure-diagnostics-config-v0.1.schema.json",
        "schemas/anomaly-multiseed-failure-diagnostics-result-v0.1.schema.json",
    ],
    "reject_conditions": ["missing", "modified", "link", "reparse"],
    "d2_record_fields": [
        "artifact_revision", "replay_head", "semantic_source_path", "artifact_blob_sha256", "current_raw_sha256",
        "current_d2_diagnostics_module_raw_sha256", "current_d2_diagnostics_cli_raw_sha256",
        "current_d2_diagnostics_renderer_raw_sha256", "current_d2_diagnostics_schema_raw_sha256",
        "current_d2_diagnostics_config_raw_sha256",
    ],
    "d2_freeze_rule": "freeze_after_D2_code_audit_before_formal_exploratory_run",
}
EXPECTED_SAFETY = {
    "input_artifact_write": False,
    "formal_artifact_write": False,
    "customer_data": False,
    "network": False,
    "weights": False,
    "checkpoint": False,
    "control_write": False,
    "banto_hub_write": False,
}


class AnomalyFailureDiagnosticsError(ValueError):
    """Diagnostics configuration or repository safety contract violation."""


def _validate_d2_domain_semantics(result: Mapping[str, Any]) -> None:
    """Validate D2's canonical signal/mode/equipment domain and exact coverage rules."""
    try:
        ledger = result["ledger"]
        aggregates = result["aggregates"]
        reconciliation = result["reconciliation"]
    except (KeyError, TypeError) as exc:
        raise AnomalyFailureDiagnosticsError("result is missing D2 domain sections") from exc

    def check_identity(row: Mapping[str, Any], label: str) -> tuple[str, str]:
        try:
            signal_id = row["signal_id"]
            operating_mode = row["operating_mode"]
            equipment_id = row["equipment_id"]
        except (KeyError, TypeError) as exc:
            raise AnomalyFailureDiagnosticsError(f"{label} is missing canonical identity") from exc
        if signal_id not in CANONICAL_SIGNAL_IDS or operating_mode not in CANONICAL_OPERATING_MODES or equipment_id not in CANONICAL_EQUIPMENT_IDS:
            raise AnomalyFailureDiagnosticsError(f"{label} contains an unknown canonical domain value")
        if equipment_id != signal_id.split(".", 1)[0]:
            raise AnomalyFailureDiagnosticsError(f"{label} violates equipment_id signal prefix rule")
        return signal_id, operating_mode

    def check_pair(row: Mapping[str, Any], label: str) -> tuple[str, str]:
        try:
            dimension = row["dimension"]
            signal_id = dimension["signal_id"]
            operating_mode = dimension["operating_mode"]
        except (KeyError, TypeError) as exc:
            raise AnomalyFailureDiagnosticsError(f"{label} is missing canonical signal/mode pair") from exc
        if (signal_id, operating_mode) not in CANONICAL_SIGNAL_MODE_PAIRS:
            raise AnomalyFailureDiagnosticsError(f"{label} contains an unknown canonical signal/mode pair")
        return signal_id, operating_mode

    per_cell: dict[str, set[tuple[str, str]]] = {}
    per_cell_rows: dict[str, int] = {}
    for section_name in ("availability", "calibration_profiles"):
        for index, row in enumerate(ledger[section_name]):
            signal_id, operating_mode = check_identity(row, f"ledger.{section_name}[{index}]")
            cell_id = row.get("cell_id")
            if not isinstance(cell_id, str) or not cell_id:
                raise AnomalyFailureDiagnosticsError(f"ledger.{section_name}[{index}] has no cell_id")
            per_cell.setdefault(cell_id, set()).add((signal_id, operating_mode))
            per_cell_rows[cell_id] = per_cell_rows.get(cell_id, 0) + 1
        for cell_id, pairs in per_cell.items():
            if per_cell_rows[cell_id] != len(CANONICAL_SIGNAL_MODE_PAIRS) or pairs != CANONICAL_SIGNAL_MODE_PAIRS:
                raise AnomalyFailureDiagnosticsError(f"ledger.{section_name} has missing or duplicate canonical pairs for {cell_id}")
        per_cell.clear()
        per_cell_rows.clear()

    for section_name in ("availability", "calibration"):
        pairs = {check_pair(row, f"aggregates.{section_name}[{index}]") for index, row in enumerate(aggregates[section_name])}
        if len(aggregates[section_name]) != len(CANONICAL_SIGNAL_MODE_PAIRS) or pairs != CANONICAL_SIGNAL_MODE_PAIRS:
            raise AnomalyFailureDiagnosticsError(f"aggregates.{section_name} has missing, duplicate, or unknown canonical pairs")

    for section_name in ("availability", "calibration"):
        pairs = set()
        for index, row in enumerate(reconciliation[section_name]):
            pairs.add(check_pair({"dimension": {"signal_id": row["signal_id"], "operating_mode": row["operating_mode"]}}, f"reconciliation.{section_name}[{index}]"))
        if len(reconciliation[section_name]) != len(CANONICAL_SIGNAL_MODE_PAIRS) or pairs != CANONICAL_SIGNAL_MODE_PAIRS:
            raise AnomalyFailureDiagnosticsError(f"reconciliation.{section_name} has missing, duplicate, or unknown canonical pairs")


def _canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise AnomalyFailureDiagnosticsError(f"value cannot be canonically serialized: {exc}") from exc


def _require_exact(actual: Any, expected: Any, label: str) -> None:
    if isinstance(actual, (int, float)) and not isinstance(actual, bool) and isinstance(expected, (int, float)) and not isinstance(expected, bool):
        if actual == expected:
            return
    if actual != expected or type(actual) is not type(expected):
        raise AnomalyFailureDiagnosticsError(f"{label} is not fixed to {expected!r}")


def _strict_object(path: Path, label: str) -> tuple[dict[str, Any], bytes, str, str]:
    try:
        value, raw, raw_sha256, canonical_sha256 = anomaly_matrix._load_object_snapshot(path, label)
    except (anomaly_matrix.AnomalyMatrixError, OSError) as exc:
        raise AnomalyFailureDiagnosticsError(f"{label} cannot be read safely") from exc
    if not isinstance(value, dict):
        raise AnomalyFailureDiagnosticsError(f"{label} must be an object")
    return value, raw, raw_sha256, canonical_sha256


def _validate_strict_schema_tree(schema: Mapping[str, Any], label: str) -> None:
    """Require every schema node describing an object to reject extra properties."""
    if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
        raise AnomalyFailureDiagnosticsError(f"{label} must be a strict object schema")

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if (node.get("type") == "object" or "properties" in node) and node.get("additionalProperties") is not False:
                raise AnomalyFailureDiagnosticsError(f"{label} contains a non-strict object schema")
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(schema)


FILE_ATTRIBUTE_REPARSE_POINT = 0x400


def _is_reparse_point(path: Path) -> bool:
    """Reject symlinks, junctions, and generic Windows reparse points."""
    try:
        attributes = getattr(os.lstat(path), "st_file_attributes", 0)
        if attributes & FILE_ATTRIBUTE_REPARSE_POINT:
            return True
        if path.is_symlink():
            return True
        junction_check = getattr(os.path, "isjunction", None) or getattr(os, "isjunction", None)
        if junction_check is not None and junction_check(path):
            return True
        return False
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise AnomalyFailureDiagnosticsError(f"cannot inspect path safely: {path}") from exc


def _repository(root: Path | None) -> Path:
    supplied = Path(root or Path(__file__).resolve().parents[2]).expanduser()
    if _is_reparse_point(supplied):
        raise AnomalyFailureDiagnosticsError("repository root cannot be a symlink, junction, or reparse point")
    try:
        if not supplied.is_dir():
            raise AnomalyFailureDiagnosticsError(f"repository root is not a directory: {supplied}")
        resolved = supplied.resolve()
    except OSError as exc:
        raise AnomalyFailureDiagnosticsError("repository root cannot be resolved safely") from exc
    if _is_reparse_point(resolved):
        raise AnomalyFailureDiagnosticsError("resolved repository root cannot be a reparse point")
    return resolved


def _safe_relative(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or value.startswith("/") or "\\" in value or PureWindowsPath(value).drive:
        raise AnomalyFailureDiagnosticsError(f"{label} must be a repository-relative POSIX path")
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise AnomalyFailureDiagnosticsError(f"{label} must not contain empty, dot, or traversal segments")
    return value


def _safe_repo_path(root: Path, value: Any, label: str, *, must_exist: bool) -> Path:
    if _is_reparse_point(root) or not root.is_dir():
        raise AnomalyFailureDiagnosticsError(f"repository root is not a regular directory: {root}")
    relative = _safe_relative(value, label)
    cursor = root
    for part in relative.split("/"):
        cursor = cursor / part
        if _is_reparse_point(cursor):
            raise AnomalyFailureDiagnosticsError(f"{label} cannot traverse a symlink, junction, or reparse point")
    try:
        resolved = (root / relative).resolve()
    except OSError as exc:
        raise AnomalyFailureDiagnosticsError(f"{label} cannot be resolved safely") from exc
    if resolved == root or root not in resolved.parents:
        raise AnomalyFailureDiagnosticsError(f"{label} must remain inside the repository")
    if must_exist and not (root / relative).exists():
        raise AnomalyFailureDiagnosticsError(f"{label} does not exist: {relative}")
    return resolved


def _validate_isolated_paths(root: Path, input_root: str, output_root: str) -> tuple[Path, Path]:
    input_path = _safe_repo_path(root, input_root, "input_root", must_exist=False)
    output_path = _safe_repo_path(root, output_root, "output_root", must_exist=False)
    if input_path == output_path or input_path in output_path.parents or output_path in input_path.parents:
        raise AnomalyFailureDiagnosticsError("input_root and output_root must be distinct non-ancestor paths")
    return input_path, output_path


def _load_config(config_path: str | Path, root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    try:
        candidate = Path(config_path)
        if candidate.is_absolute():
            relative = candidate.absolute().relative_to(root.absolute()).as_posix()
        else:
            relative = candidate.as_posix()
    except ValueError as exc:
        raise AnomalyFailureDiagnosticsError("config must be a repository-local regular file") from exc
    if relative != CONFIG_PATH:
        raise AnomalyFailureDiagnosticsError(f"unknown diagnostics profile: {relative}")
    path = _safe_repo_path(root, relative, "diagnostics config", must_exist=True)
    config, raw, raw_sha256, canonical_sha256 = _strict_object(path, "diagnostics config")
    schema_relative = config.get("schema_path")
    if schema_relative != SCHEMA_PATH:
        raise AnomalyFailureDiagnosticsError("diagnostics schema path is not the fixed profile")
    schema_path = _safe_repo_path(root, schema_relative, "diagnostics config schema", must_exist=True)
    schema, schema_raw, schema_raw_sha256, schema_canonical_sha256 = _strict_object(schema_path, "diagnostics config schema")
    _validate_strict_schema_tree(schema, "diagnostics config schema")
    if EXPECTED_SCHEMA_CANONICAL_SHA256 and schema_canonical_sha256 != EXPECTED_SCHEMA_CANONICAL_SHA256:
        raise AnomalyFailureDiagnosticsError("diagnostics schema canonical SHA-256 pin is invalid")
    if EXPECTED_CONFIG_CANONICAL_SHA256 and canonical_sha256 != EXPECTED_CONFIG_CANONICAL_SHA256:
        raise AnomalyFailureDiagnosticsError("diagnostics config canonical SHA-256 pin is invalid")
    try:
        validate(config, schema)
    except ManifestValidationError as exc:
        raise AnomalyFailureDiagnosticsError(f"diagnostics config does not satisfy its schema: {exc}") from exc
    if config.get("schema_canonical_sha256") != schema_canonical_sha256:
        raise AnomalyFailureDiagnosticsError("diagnostics config schema digest pin is invalid")
    result_schema_relative = config.get("result_schema_path")
    if result_schema_relative != RESULT_SCHEMA_PATH:
        raise AnomalyFailureDiagnosticsError("diagnostics result schema path is not the fixed profile")
    result_schema_path = _safe_repo_path(root, result_schema_relative, "diagnostics result schema", must_exist=True)
    result_schema, result_schema_raw, result_schema_raw_sha256, result_schema_canonical_sha256 = _strict_object(result_schema_path, "diagnostics result schema")
    _validate_strict_schema_tree(result_schema, "diagnostics result schema")
    if EXPECTED_RESULT_SCHEMA_CANONICAL_SHA256 and result_schema_canonical_sha256 != EXPECTED_RESULT_SCHEMA_CANONICAL_SHA256:
        raise AnomalyFailureDiagnosticsError("diagnostics result schema canonical SHA-256 pin is invalid")
    if config.get("result_schema_canonical_sha256") != result_schema_canonical_sha256:
        raise AnomalyFailureDiagnosticsError("diagnostics result schema digest pin is invalid")
    return config, {
        "path": relative,
        "raw": raw,
        "raw_sha256": raw_sha256,
        "canonical_sha256": canonical_sha256,
    }, {
        "path": schema_relative,
        "raw": schema_raw,
        "raw_sha256": schema_raw_sha256,
        "canonical_sha256": schema_canonical_sha256,
        "value": schema,
    }, {
        "path": result_schema_relative,
        "raw": result_schema_raw,
        "raw_sha256": result_schema_raw_sha256,
        "canonical_sha256": result_schema_canonical_sha256,
        "value": result_schema,
    }


def _validate_semantics(config: Mapping[str, Any], root: Path) -> None:
    _require_exact(config.get("schema_version"), SCHEMA_VERSION, "schema_version")
    _require_exact(config.get("config_type"), CONFIG_TYPE, "config_type")
    _require_exact(config.get("diagnostics_id"), DIAGNOSTICS_ID, "diagnostics_id")
    _require_exact(config.get("result_type"), RESULT_TYPE, "result_type")
    _require_exact(config.get("matrix_id"), EXPECTED_MATRIX_ID, "matrix_id")
    _require_exact(config.get("matrix_config_path"), EXPECTED_MATRIX_CONFIG_PATH, "matrix_config_path")
    _require_exact(config.get("matrix_config_canonical_sha256"), EXPECTED_MATRIX_CONFIG_CANONICAL_SHA256, "matrix_config_canonical_sha256")
    _require_exact(config.get("matrix_result_schema_path"), EXPECTED_MATRIX_RESULT_SCHEMA_PATH, "matrix_result_schema_path")
    _require_exact(config.get("matrix_result_schema_canonical_sha256"), EXPECTED_MATRIX_RESULT_SCHEMA_CANONICAL_SHA256, "matrix_result_schema_canonical_sha256")
    _require_exact(config.get("result_schema_path"), RESULT_SCHEMA_PATH, "result_schema_path")
    _require_exact(config.get("result_schema_canonical_sha256"), EXPECTED_RESULT_SCHEMA_CANONICAL_SHA256, "result_schema_canonical_sha256")
    _require_exact(config.get("input_root"), EXPECTED_INPUT_ROOT, "input_root")
    _require_exact(config.get("output_root"), EXPECTED_OUTPUT_ROOT, "output_root")
    _require_exact(config.get("artifact_code_revision"), EXPECTED_ARTIFACT_CODE_REVISION, "artifact_code_revision")
    _require_exact(config.get("expected_input_artifact"), EXPECTED_INPUT_ARTIFACT, "expected_input_artifact")
    _require_exact(config.get("expected_counts"), EXPECTED_COUNTS, "expected_counts")
    _require_exact(config.get("exploratory_only"), True, "exploratory_only")
    _require_exact(config.get("promotion_eligible"), False, "promotion_eligible")
    _require_exact(config.get("performance_status"), "not_evaluated", "performance_status")
    _require_exact(config.get("ledger_contract"), EXPECTED_LEDGER_CONTRACT, "ledger_contract")
    _require_exact(config.get("revision_compatibility"), EXPECTED_REVISION_COMPATIBILITY, "revision_compatibility")
    _require_exact(config.get("safety"), EXPECTED_SAFETY, "safety")
    _validate_isolated_paths(root, config["input_root"], config["output_root"])
    if config["input_root"] == config["output_root"]:
        raise AnomalyFailureDiagnosticsError("input_root and output_root must not be identical")


def validate_diagnostics_config(config_path: str | Path = CONFIG_PATH, root: Path | None = None) -> dict[str, Any]:
    """Validate the fixed D1 contract without reading or writing artifacts."""
    repository = _repository(root)
    config, config_source, schema_source, result_schema_source = _load_config(config_path, repository)
    _validate_semantics(config, repository)
    if _VALIDATION_FINAL_READ_HOOK is not None:
        _VALIDATION_FINAL_READ_HOOK(repository, config_path)
    final_config, final_config_source, final_schema_source, final_result_schema_source = _load_config(config_path, repository)
    if (
        final_config != config
        or final_config_source != config_source
        or final_schema_source != schema_source
        or final_result_schema_source != result_schema_source
    ):
        raise AnomalyFailureDiagnosticsError("diagnostics config or schema inputs changed during validation")
    return {
        "schema_version": SCHEMA_VERSION,
        "summary_type": "event-aware-anomaly-failure-diagnostics-config-validation",
        "status": "configuration_valid",
        "run_status": "not_run",
        "performance_status": "not_evaluated",
        "diagnostics_id": DIAGNOSTICS_ID,
        "config_type": CONFIG_TYPE,
        "result_type": RESULT_TYPE,
        "matrix_id": EXPECTED_MATRIX_ID,
        "config_path": config_source["path"],
        "config_canonical_sha256": config_source["canonical_sha256"],
        "schema": {"path": schema_source["path"], "canonical_sha256": schema_source["canonical_sha256"]},
        "result_schema": {"path": result_schema_source["path"], "canonical_sha256": result_schema_source["canonical_sha256"]},
        "input_root": EXPECTED_INPUT_ROOT,
        "output_root": EXPECTED_OUTPUT_ROOT,
        "exploratory_only": True,
        "promotion_eligible": False,
        "execution": {"implemented": False, "validate_only": True, "artifact_read": False, "artifact_write": False},
        "safety": {"filesystem_write": False, "matrix_artifact_write": False, "formal_artifact_write": False, "customer_data": False, "network": False, "weights": False, "checkpoint": False, "control_write": False, "banto_hub_write": False},
    }


_VALIDATION_FINAL_READ_HOOK: Any = None


def _text_summary(summary: Mapping[str, Any]) -> str:
    return (
        f"anomaly failure diagnostics config: {summary['status']}\n"
        f"diagnostics_id: {summary['diagnostics_id']}\n"
        f"run_status: {summary['run_status']}\n"
        f"performance_status: {summary['performance_status']}\n"
        "D1 execution: not implemented; --validate-only only\n"
        "filesystem_write: false\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="diagnose_anomaly_matrix")
    parser.add_argument("--config", default=CONFIG_PATH)
    parser.add_argument("--root")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)
    if not args.validate_only:
        print("FAIL: D1 supports --validate-only only; diagnostic execution is not implemented")
        return 2
    root = Path(args.root).absolute() if args.root else None
    try:
        summary = validate_diagnostics_config(args.config, root)
        print(_text_summary(summary), end="")
    except (AnomalyFailureDiagnosticsError, ManifestValidationError, OSError, KeyError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
