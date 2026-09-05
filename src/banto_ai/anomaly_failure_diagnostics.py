"""D1 validation, read-only D2-A replay, and atomic staged D2-B publication."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import stat
import subprocess
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from pathlib import PureWindowsPath
from collections import Counter, defaultdict
from copy import deepcopy
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping

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
DIAGNOSTICS_COMPLETION_MARKER_TYPE = "event-aware-anomaly-failure-diagnostics-complete"
_STAGED_MARKER = ".complete"
_STAGING_PREFIX = ".anomaly-multiseed-v02-diagnostics-v01.staging-"
EXPECTED_ARTIFACT_CODE_REVISION = "15a0f60433703c32a1bfa989f7f779c6828a1096"
EXPECTED_CONFIG_CANONICAL_SHA256 = "933446fda04913ad23fb3168173152e0f21838427b04754872c3e913f43ba2e1"
EXPECTED_SCHEMA_CANONICAL_SHA256 = "1543b43feb48cb60988852852662bc19225719bff31145d7d3e3c202e8ef301a"
EXPECTED_RESULT_SCHEMA_CANONICAL_SHA256 = "218a69829815c766d5edd888ea01567d113ad2745bf5b4c9ab7ba029fe53c17d"
EXPECTED_CONFIG_RAW_SHA256 = "bafa6a4d24ec7899c0c015a79a23d91dd65368c2a5078a18662c1a40de182a8e"
EXPECTED_CONFIG_SCHEMA_RAW_SHA256 = "5840f1097ea3f1e68e530288430d4afb4b21a0c2dea3344094c42a716f7d4fe3"
EXPECTED_RESULT_SCHEMA_RAW_SHA256 = "ee71348890b77d0c3b49007784e618e69fa3b40b48c5d2ee01a04e52800e8877"
CANONICALIZATION_ID = "utf-8-json-sort-keys-compact-no-trailing-newline-v1"
MATRIX_SAMPLING_INTERVAL_MS = 1000
MATRIX_PERSISTENCE_POINTS = 2
MATRIX_ROBUST_Z_THRESHOLD = 4
_EXCLUSION_KEYS = ("quality_non_ok", "previous_quality_non_ok", "mode_boundary", "gap", "previous_event_overlap", "profile_inconclusive", "no_previous_observation", "nonfinite_value", "previous_nonfinite_value", "nonfinite_residual", "nonfinite_score")
_CALIBRATION_EXCLUSION_KEYS = ("event_overlap", "nonfinite", "quality_non_ok", "residual_unavailable")
CANONICAL_SIGNAL_IDS = (
    "motor-01.motor_current", "motor-01.motor_temperature", "motor-01.conveyor_speed", "motor-01.vibration_feature",
    "conveyor-01.motor_current", "conveyor-01.motor_temperature", "conveyor-01.conveyor_speed", "conveyor-01.vibration_feature",
)
CANONICAL_OPERATING_MODES = ("stopped", "startup", "low_speed", "nominal", "high_load", "cooldown")
CANONICAL_EQUIPMENT_IDS = ("motor-01", "conveyor-01")
CANONICAL_LAYOUT_IDS = ("motor-01-stopped", "motor-01-startup", "motor-01-low-speed", "motor-01-nominal", "motor-01-high-load", "motor-01-cooldown", "conveyor-01-stopped", "conveyor-01-startup", "conveyor-01-low-speed", "conveyor-01-nominal", "conveyor-01-high-load", "conveyor-01-cooldown")
CANONICAL_SIGNAL_MODE_PAIRS = {(signal_id, operating_mode) for signal_id in CANONICAL_SIGNAL_IDS for operating_mode in CANONICAL_OPERATING_MODES}

EXPECTED_INPUT_ARTIFACT = {
    "result_path": "result.json",
    "summary_path": "summary.md",
    "completion_marker_path": ".complete",
    "result_sha256": "7bc546936c1a99100204d7fe2852b9dd8c500ac0dd2e3c3d7ccbc139c918de31",
    "summary_sha256": "e132b3ea14e06be94b4df0cd4b052b1f270797744ca532fb333f1d0e94e289f9",
    "completion_marker_sha256": "cc58b420901c9d31a415a89808d882c5b9a7d2936d0923e4102cee1acce85995",
    "inventory_sha256": "2a4a62332c1c15c48b077aa59dbbccae01559558df162d5d1484aa1ae345af0e",
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


_VERIFIED_RESULT_TOKEN = object()
_DRAFT_FLAGS = {"status": "draft", "run_status": "not_run", "engineering_status": "not_evaluated"}
_COMPLETE_FLAGS = {"status": "complete", "run_status": "complete", "engineering_status": "pass"}


class VerifiedDiagnosticsResult(Mapping[str, Any]):
    """Read-only replay result, issued only by the single replay API after its final audit.

    Nested values are defensive copies. The private issuance token prevents normal
    construction from a mapping; this is an API boundary, not a sandbox against
    hostile in-process reflection or monkeypatching.
    """

    __slots__ = ("__payload",)

    def __init__(self, payload: Mapping[str, Any], *, _token: object = None) -> None:
        if _token is not _VERIFIED_RESULT_TOKEN:
            raise AnomalyFailureDiagnosticsError("verified results can only be issued by replay_and_build_diagnostics_result")
        object.__setattr__(self, "_VerifiedDiagnosticsResult__payload", MappingProxyType(deepcopy(dict(payload))))

    def __getitem__(self, key: str) -> Any:
        return deepcopy(self.__payload[key])

    def __iter__(self):
        return iter(self.__payload)

    def __len__(self) -> int:
        return len(self.__payload)

    def __setattr__(self, name: str, value: Any) -> None:
        raise TypeError("verified diagnostics results are read-only")

    def __init_subclass__(cls, **kwargs) -> None:
        raise TypeError("verified diagnostics results cannot be subclassed")

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self

    def __reduce_ex__(self, protocol):
        raise TypeError("verified diagnostics results cannot be deserialized; replay is required")


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


def _fail(message: str) -> None:
    raise AnomalyFailureDiagnosticsError(message)


def _key(row: Mapping[str, Any], fields: Iterable[str]) -> tuple[Any, ...]:
    return tuple(row.get(field) for field in fields)


def _ledger_sort_key(section: str, row: Mapping[str, Any]) -> tuple[Any, ...]:
    cell = (row.get("seed", 0), row.get("layout_index", 0), str(row.get("cell_id", "")), str(row.get("layout_id", "")))
    if section == "incident_windows":
        return cell + (str(row.get("event_id", "")),)
    if section == "incident_points":
        return cell + (str(row.get("event_id", "")), int(row.get("offset", 0)))
    if section == "clean_source_alerts":
        return cell + (str(row.get("equipment_id", "")), str(row.get("source_alert_episode_id", "")))
    if section == "clean_equipment_alerts":
        return cell + (str(row.get("equipment_id", "")), str(row.get("equipment_episode_id", "")))
    if section == "availability":
        return cell + (CANONICAL_SIGNAL_IDS.index(row.get("signal_id")), CANONICAL_OPERATING_MODES.index(row.get("operating_mode")))
    if section == "calibration_profiles":
        return cell + (CANONICAL_SIGNAL_IDS.index(row.get("signal_id")), CANONICAL_OPERATING_MODES.index(row.get("operating_mode")))
    return cell


def _validate_ledger_order(section: str, rows: list[Mapping[str, Any]]) -> None:
    if [_ledger_sort_key(section, row) for row in rows] != sorted(_ledger_sort_key(section, row) for row in rows):
        _fail(f"{section} is not in deterministic fixed order")


def _assert_unique(rows: Iterable[Mapping[str, Any]], fields: Iterable[str], label: str) -> None:
    seen: set[tuple[Any, ...]] = set()
    for index, row in enumerate(rows):
        value = _key(row, fields)
        if value in seen:
            _fail(f"{label} contains a duplicate composite key at row {index}: {value!r}")
        seen.add(value)


def _dimension_value(row: Mapping[str, Any]) -> tuple[str, Any]:
    dimension = row.get("dimension")
    if not isinstance(dimension, Mapping):
        _fail("aggregate dimension is not an object")
    name, value = dimension.get("dimension_name"), dimension.get("dimension_value")
    if not isinstance(name, str):
        _fail("aggregate dimension name is missing")
    return name, value


def _numeric_distribution(values: Iterable[Any]) -> dict[str, Any]:
    values_list = list(values)
    if any(isinstance(value, bool) for value in values_list if value is not None):
        _fail("numeric distribution contains a boolean")
    non_null = [float(value) for value in values_list if value is not None]
    if any(not math.isfinite(value) for value in non_null):
        _fail("numeric distribution contains a non-finite value")
    return {
        "total_count": len(values_list),
        "non_null_count": len(non_null),
        "null_count": len(values_list) - len(non_null),
        "min": min(non_null) if non_null else None,
        "max": max(non_null) if non_null else None,
        "mean": sum(non_null) / len(non_null) if non_null else None,
    }


def _reason_distribution(values: Iterable[Any]) -> list[dict[str, Any]]:
    counts = Counter(values)
    return [{"reason": reason, "count": counts[reason]} for reason in sorted(counts, key=lambda item: (item is not None, "" if item is None else str(item)))]


def _incident_dimensions() -> tuple[tuple[str, tuple[Any, ...]], ...]:
    return (
        ("event_class", ("machine_fault", "sensor_fault")),
        ("event_type", ("jam_or_slip", "spike")),
        ("signal_id", ("motor-01.motor_current", "conveyor-01.conveyor_speed", "motor-01.motor_temperature", "conveyor-01.motor_temperature")),
        ("equipment_id", CANONICAL_EQUIPMENT_IDS),
        ("operating_mode", CANONICAL_OPERATING_MODES),
    )


_INCIDENT_MARGINAL_COUNTS = {"event_class": 120, "event_type": 120, "signal_id": 60, "equipment_id": 120, "operating_mode": 40}
_INCIDENT_COMPOSITION_FIELDS = ("event_id", "event_class", "event_type", "signal_id", "equipment_id", "operating_mode")


def _expected_incident_composition(layout_index: int) -> Counter:
    equipment = CANONICAL_EQUIPMENT_IDS[layout_index // 6]
    mode = CANONICAL_OPERATING_MODES[layout_index % 6]
    layout = CANONICAL_LAYOUT_IDS[layout_index]
    machine_signal = "motor_current" if equipment == "motor-01" else "conveyor_speed"
    return Counter({
        (layout + "-machine-fault", "machine_fault", "jam_or_slip", equipment + "." + machine_signal, equipment, mode): 1,
        (layout + "-sensor-fault", "sensor_fault", "spike", equipment + ".motor_temperature", equipment, mode): 1,
    })


def _clean_dimensions() -> tuple[tuple[str, tuple[Any, ...]], ...]:
    return (
        ("signal_id", CANONICAL_SIGNAL_IDS),
        ("operating_mode", CANONICAL_OPERATING_MODES),
        ("signal_id×operating_mode", tuple((signal, mode) for signal in CANONICAL_SIGNAL_IDS for mode in CANONICAL_OPERATING_MODES)),
        ("mode_entry_offset", tuple(range(30))),
    )


def _validate_incident_semantics(result: Mapping[str, Any]) -> None:
    ledger = result["ledger"]
    windows = ledger["incident_windows"]
    points = ledger["incident_points"]
    if len(windows) != EXPECTED_COUNTS["eligible_incident_windows"] or len(points) != EXPECTED_COUNTS["combined_incident_point_rows"]:
        _fail("incident ledger cardinality is not exact")
    expected_incident_dimensions = [(name, value) for name, values in _incident_dimensions() for value in values]
    if [(_dimension_value(row)) for row in result["aggregates"]["incident_window_aggregates"]] != expected_incident_dimensions:
        _fail("incident window aggregate order or coverage is not deterministic")
    if [(_dimension_value(row), row.get("offset")) for row in result["aggregates"]["incident_offset_aggregates"]] != [(dimension, offset) for dimension in expected_incident_dimensions for offset in (-1, 0, 1, 2, 3, 4, 5)]:
        _fail("incident offset aggregate order or coverage is not deterministic")
    _assert_unique(windows, ("cell_id", "seed", "layout_id", "layout_index", "event_id"), "incident_windows")
    _assert_unique(points, ("cell_id", "seed", "layout_id", "layout_index", "event_id", "offset"), "incident_points")
    available_cells = {row.get("cell_id") for row in result["ledger"]["availability"]}
    cell_metadata = {}
    for row in result["ledger"]["availability"]:
        identity = (row.get("seed"), row.get("layout_id"), row.get("layout_index"))
        if row.get("cell_id") in cell_metadata and cell_metadata[row.get("cell_id")] != identity:
            _fail(f"availability cell identity is inconsistent: {row.get('cell_id')}")
        cell_metadata[row.get("cell_id")] = identity
    for row in windows + points:
        if row.get("cell_id") not in cell_metadata or cell_metadata[row.get("cell_id")] != (row.get("seed"), row.get("layout_id"), row.get("layout_index")):
            _fail(f"incident row references a fake or mismatched cell identity: {row.get('cell_id')}")
        index = row["layout_index"]
        if type(index) is not int or not 0 <= index < 12:
            _fail("incident layout index is invalid")
        equipment_id = CANONICAL_EQUIPMENT_IDS[index // 6]
        if row["operating_mode"] != CANONICAL_OPERATING_MODES[index % 6] or row["equipment_id"] != equipment_id or not row["signal_id"].startswith(equipment_id + "."):
            _fail("incident identity differs from its fixed layout")
    incident_cell_counts = Counter(row.get("cell_id") for row in windows)
    if set(incident_cell_counts) != available_cells or any(count != 2 for count in incident_cell_counts.values()):
        _fail("incident windows do not map exactly two eligible windows to each verified cell")
    for cell_id, (_, _, layout_index) in cell_metadata.items():
        composition = Counter(_key(row, _INCIDENT_COMPOSITION_FIELDS) for row in windows if row["cell_id"] == cell_id)
        if composition != _expected_incident_composition(layout_index):
            _fail(f"incident class/type/signal/event-ID composition differs from the fixed layout for {cell_id}")
    for name, values in _incident_dimensions():
        if Counter(row[name] for row in windows) != Counter({value: _INCIDENT_MARGINAL_COUNTS[name] for value in values}):
            _fail(f"incident global category counts differ from the fixed {name} marginal")
    by_event: dict[tuple[Any, ...], list[Mapping[str, Any]]] = defaultdict(list)
    episode_profiles: dict[tuple[str, str], tuple[Any, ...]] = {}
    for point in points:
        by_event[_key(point, ("cell_id", "seed", "layout_id", "layout_index", "event_id"))].append(point)
        if point["alert_episode_id"] is not None:
            episode_key = (point["cell_id"], point["alert_episode_id"])
            profile = _key(point, ("equipment_id", "signal_id", "operating_mode"))
            if episode_profiles.setdefault(episode_key, profile) != profile:
                _fail("one cell-local alert episode cannot belong to multiple signal profiles")
    for window in windows:
        event_key = _key(window, ("cell_id", "seed", "layout_id", "layout_index", "event_id"))
        event_points = by_event.get(event_key, [])
        if {point.get("offset") for point in event_points} != {-1, 0, 1, 2, 3, 4, 5}:
            _fail(f"incident event {event_key!r} does not have exactly offsets -1..5")
        if any(_key(point, ("event_class", "event_type", "equipment_id", "signal_id", "operating_mode")) != _key(window, ("event_class", "event_type", "equipment_id", "signal_id", "operating_mode")) for point in event_points):
            _fail(f"incident event {event_key!r} point identity drifted")
        ordered = {point["offset"]: point for point in event_points}
        for offset in (-1, 0, 1, 2, 3, 4, 5):
            point = ordered[offset]
            if point.get("available") is True:
                if isinstance(point.get("score"), bool) or not isinstance(point.get("score"), (int, float)) or not math.isfinite(float(point["score"])) or point.get("score") < 0 or point.get("exclusion_reason") is not None:
                    _fail(f"incident point {event_key!r}/{offset} has inconsistent available score fields")
                if point.get("exceeds_threshold") is not (point.get("score") > MATRIX_ROBUST_Z_THRESHOLD):
                    _fail(f"incident point {event_key!r}/{offset} exceeds_threshold is inconsistent with the fixed threshold")
            else:
                if point.get("score") is not None or not isinstance(point.get("exclusion_reason"), str) or point.get("persistence_streak") != 0 or point.get("exceeds_threshold") is not False or point.get("alert_episode_id") is not None:
                    _fail(f"incident point {event_key!r}/{offset} has inconsistent unavailable score fields")
            if offset > -1:
                previous = ordered[offset - 1]
                continuation = point.get("available") is True and point.get("exceeds_threshold") is True and previous.get("available") is True and previous.get("exceeds_threshold") is True
                expected_streak = int(previous.get("persistence_streak", 0)) + 1 if continuation else (1 if point.get("exceeds_threshold") is True else 0)
                if point.get("persistence_streak") != expected_streak:
                    _fail(f"incident point {event_key!r}/{offset} persistence streak is inconsistent")
            if point.get("exceeds_threshold") is False and point.get("persistence_streak") != 0:
                _fail(f"incident point {event_key!r}/{offset} non-exceeding score has a nonzero persistence streak")
            if point.get("exceeds_threshold") is True and point.get("persistence_streak", 0) < 1:
                _fail(f"incident point {event_key!r}/{offset} exceedance has no persistence streak")
            if point.get("alert_episode_id") is not None and (point.get("exceeds_threshold") is not True or point.get("persistence_streak", 0) < MATRIX_PERSISTENCE_POINTS):
                _fail(f"incident point {event_key!r}/{offset} links an alert before persistence is satisfied")
            if point.get("exceeds_threshold") is True and point["persistence_streak"] >= MATRIX_PERSISTENCE_POINTS and point["alert_episode_id"] is None:
                _fail(f"incident point {event_key!r}/{offset} has persistent exceedance without an alert link")
            if offset >= 0 and point.get("alert_episode_id") is not None and ordered[offset - 1].get("alert_episode_id") is not None and point["alert_episode_id"] != ordered[offset - 1]["alert_episode_id"]:
                _fail("sampling-contiguous alert points change episode identity")
        timestamp_by_offset = {offset: _utc_timestamp(ordered[offset]["timestamp"], f"incident point timestamp {event_key!r}/{offset}") for offset in (-1, 0, 1, 2, 3, 4, 5)}
        event_start = _utc_timestamp(window["event_start_timestamp"], "event start")
        if (_utc_timestamp(window["event_end_timestamp"], "event end") <= event_start
                or _utc_timestamp(window["detection_window_start"], "detection window start") != event_start
                or _utc_timestamp(window["detection_window_end"], "detection window end") != event_start + timedelta(milliseconds=6 * MATRIX_SAMPLING_INTERVAL_MS)):
            _fail(f"incident event {event_key!r} does not have valid event bounds and the fixed [0,6) detection window")
        interval = timestamp_by_offset[0] - timestamp_by_offset[-1]
        if timestamp_by_offset[0] != event_start or interval != timedelta(milliseconds=MATRIX_SAMPLING_INTERVAL_MS) or any(timestamp_by_offset[offset] - timestamp_by_offset[offset - 1] != interval for offset in range(0, 6)):
            _fail(f"incident event {event_key!r} points are not sampling-contiguous around event_start")
        run = 0
        maximum = 0
        for offset in range(6):
            run = run + 1 if ordered[offset].get("available") is True and ordered[offset].get("exceeds_threshold") is True else 0
            maximum = max(maximum, run)
        if window.get("max_in_window_consecutive_exceedances") != maximum:
            _fail(f"incident event {event_key!r} has an incorrect maximum contiguous run")
        pre = ordered[-1]
        if window.get("pre_event_support") is not (pre.get("available") is True and pre.get("exceeds_threshold") is True):
            _fail(f"incident event {event_key!r} has incorrect pre-event support")
        # Replay formal matching independently of the declared match: only new
        # onsets in [0,6) qualify. A pre-window episode continuing from -1 does not.
        previous_episode = ordered[-1]["alert_episode_id"]
        seen_episodes = {previous_episode} if previous_episode is not None else set()
        new_onsets = []
        for offset in range(6):
            episode = ordered[offset]["alert_episode_id"]
            if episode is not None and episode != previous_episode:
                if episode in seen_episodes:
                    _fail(f"incident event {event_key!r} reuses an episode ID after a break")
                seen_episodes.add(episode)
                new_onsets.append(offset)
            previous_episode = episode
        onset_offset = new_onsets[0] if new_onsets else None
        expected_match = ordered[onset_offset]["alert_episode_id"] if onset_offset is not None else None
        expected_onset = ordered[onset_offset]["timestamp"] if onset_offset is not None else None
        expected_delay = (timestamp_by_offset[onset_offset] - event_start).total_seconds() if onset_offset is not None else None
        if (window["detected"] is not bool(new_onsets)
                or window["matched_alert_episode_id"] != expected_match
                or window["alert_onset_timestamp"] != expected_onset
                or window["detection_delay_seconds"] != expected_delay):
            _fail(f"incident event {event_key!r} canonical detection differs from its first new eligible onset")
        expected_causal = False
        if onset_offset is not None:
            support = [ordered[index] for index in range(onset_offset - (MATRIX_PERSISTENCE_POINTS - 1), onset_offset + 1)] if onset_offset >= MATRIX_PERSISTENCE_POINTS - 1 else []
            expected_causal = len(support) == MATRIX_PERSISTENCE_POINTS and all(point.get("available") is True and point.get("exceeds_threshold") is True for point in support)
        if window.get("event_causal_support_qualified") is not expected_causal:
            _fail(f"incident event {event_key!r} causal qualification is inconsistent")

    for dimension_name, values in _incident_dimensions():
        for value in values:
            value = {"signal_id": value[0], "operating_mode": value[1]} if dimension_name == "signal_id×operating_mode" else value
            selected = [row for row in windows if row.get(dimension_name) == value]
            aggregates = [row for row in result["aggregates"]["incident_window_aggregates"] if _dimension_value(row) == (dimension_name, value)]
            if len(aggregates) != 1:
                _fail(f"incident window aggregate coverage is not exact for {dimension_name}={value!r}")
            aggregate = aggregates[0]
            expected = {
                "denominator": _INCIDENT_MARGINAL_COUNTS[dimension_name], "window_count": _INCIDENT_MARGINAL_COUNTS[dimension_name],
                "detected_count": sum(row.get("detected") is True for row in selected),
                "event_causal_support_qualified_count": sum(row.get("event_causal_support_qualified") is True for row in selected),
                "pre_event_support_count": sum(row.get("pre_event_support") is True for row in selected),
            }
            if any(aggregate.get(field) != value for field, value in expected.items()):
                _fail(f"incident window aggregate does not reconcile for {dimension_name}={value!r}")
            distribution = Counter(row.get("max_in_window_consecutive_exceedances") for row in selected)
            if [item.get("window_count") for item in aggregate.get("max_consecutive_run_distribution", [])] != [distribution.get(run_length, 0) for run_length in range(7)]:
                _fail(f"incident run distribution does not reconcile for {dimension_name}={value!r}")
            for offset in (-1, 0, 1, 2, 3, 4, 5):
                offset_rows = [row for row in points if row.get("offset") == offset and row.get(dimension_name) == value]
                offsets = [row for row in result["aggregates"]["incident_offset_aggregates"] if _dimension_value(row) == (dimension_name, value) and row.get("offset") == offset]
                if len(offsets) != 1 or offsets[0].get("total_count") != _INCIDENT_MARGINAL_COUNTS[dimension_name] or offsets[0].get("available_count") != sum(row.get("available") is True for row in offset_rows) or offsets[0].get("exceed_count") != sum(row.get("exceeds_threshold") is True for row in offset_rows) or offsets[0].get("denominator") != _INCIDENT_MARGINAL_COUNTS[dimension_name] * 7:
                    _fail(f"incident offset aggregate does not reconcile for {dimension_name}={value!r}, offset={offset}")


def _validate_clean_semantics(result: Mapping[str, Any]) -> None:
    ledger = result["ledger"]
    sources, equipment = ledger["clean_source_alerts"], ledger["clean_equipment_alerts"]
    _assert_unique(sources, ("cell_id", "source_alert_episode_id"), "clean_source_alerts")
    _assert_unique(equipment, ("cell_id", "equipment_episode_id"), "clean_equipment_alerts")
    for index, row in enumerate(sources):
        if row.get("signal_id") not in CANONICAL_SIGNAL_IDS or row.get("operating_mode") not in CANONICAL_OPERATING_MODES or row.get("equipment_id") not in CANONICAL_EQUIPMENT_IDS or row.get("equipment_id") != str(row.get("signal_id")).split(".", 1)[0]:
            _fail(f"clean source {index} violates canonical signal/mode/equipment attribution")
    for index, row in enumerate(equipment):
        if row.get("equipment_id") not in CANONICAL_EQUIPMENT_IDS:
            _fail(f"clean equipment {index} has an unknown equipment id")
    cell_metadata = {row.get("cell_id"): (row.get("seed"), row.get("layout_id"), row.get("layout_index")) for row in ledger["availability"]}
    for index, row in enumerate(sources + equipment):
        if row.get("cell_id") not in cell_metadata or cell_metadata[row.get("cell_id")] != (row.get("seed"), row.get("layout_id"), row.get("layout_index")):
            _fail(f"clean row {index} references a fake or mismatched cell identity")
    source_by_group: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    equipment_by_group: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in sources:
        source_by_group[(row["cell_id"], row["equipment_id"])].append(row)
    for row in equipment:
        if row.get("merge_size") != len(row.get("source_alert_episode_ids", [])):
            _fail("clean equipment merge_size does not equal its source id count")
        if len(set(row.get("source_alert_episode_ids", []))) != len(row.get("source_alert_episode_ids", [])):
            _fail("clean equipment source ids are not unique")
        equipment_by_group[(row["cell_id"], row["equipment_id"])].append(row)
    reconciliation = result["reconciliation"]["clean_alerts"]
    _assert_unique(reconciliation, ("cell_id", "equipment_id"), "clean reconciliation")
    expected_groups = {(row.get("cell_id"), equipment_id) for row in ledger["availability"] for equipment_id in CANONICAL_EQUIPMENT_IDS}
    expected_groups = {(cell_id, equipment_id) for cell_id, equipment_id in expected_groups if cell_id is not None}
    available_cell_ids = {row.get("cell_id") for row in ledger["availability"]}
    if {row.get("cell_id") for row in sources + equipment} - available_cell_ids:
        _fail("clean ledger contains a cell outside the verified availability/calibration inventory")
    if {_key(row, ("cell_id", "equipment_id")) for row in reconciliation} != expected_groups:
        _fail("clean reconciliation does not cover every cell/equipment group")
    for row in reconciliation:
        group = (row["cell_id"], row["equipment_id"])
        group_sources = source_by_group.get(group, [])
        group_equipment = equipment_by_group.get(group, [])
        source_ids = {item["source_alert_episode_id"] for item in group_sources}
        equipment_ids = [source_id for item in group_equipment for source_id in item["source_alert_episode_ids"]]
        source_to_equipment: dict[str, str] = {}
        for equipment_row in group_equipment:
            for source_id in equipment_row["source_alert_episode_ids"]:
                if source_id in source_to_equipment or not isinstance(equipment_row.get("equipment_episode_id"), str):
                    _fail(f"clean source id is assigned to multiple equipment episodes for {group!r}")
                source_to_equipment[source_id] = equipment_row["equipment_episode_id"]
        if any(source_to_equipment.get(source["source_alert_episode_id"]) != source.get("equipment_episode_id") for source in group_sources):
            _fail(f"clean source episode is not attributed to its containing equipment episode for {group!r}")
        if row.get("source_count") != len(equipment_ids) or row.get("equipment_count") != len(group_equipment) or row.get("merge_size_sum") != sum(item["merge_size"] for item in group_equipment) or set(equipment_ids) != source_ids:
            _fail(f"clean reconciliation does not exactly join {group!r}")
    aggregates = result["aggregates"]["clean_alerts"]
    if len(aggregates) != 94:
        _fail("clean aggregate cardinality is not exact")
    aggregate_keys = [(_dimension_value(row)[0], json.dumps(_dimension_value(row)[1], sort_keys=True, ensure_ascii=False, separators=(",", ":"))) for row in aggregates]
    expected_aggregate_keys = [(name, json.dumps({"signal_id": value[0], "operating_mode": value[1]} if name == "signal_id×operating_mode" else value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))) for name, values in _clean_dimensions() for value in values] + [("equipment_id", json.dumps(value, ensure_ascii=False, separators=(",", ":"))) for value in CANONICAL_EQUIPMENT_IDS]
    if aggregate_keys != expected_aggregate_keys:
        _fail("clean aggregate domain coverage is not exactly the fixed 94 categories")
    for aggregate in aggregates:
        name, value = _dimension_value(aggregate)
        if name == "signal_id":
            expected = sum(row.get("signal_id") == value for row in sources)
            if aggregate.get("source_episode_count") != expected:
                _fail("clean signal aggregate does not reconcile")
        elif name == "operating_mode":
            expected = sum(row.get("operating_mode") == value for row in sources)
            if aggregate.get("source_episode_count") != expected:
                _fail("clean mode aggregate does not reconcile")
        elif name == "signal_id×operating_mode":
            expected = sum(row.get("signal_id") == value.get("signal_id") and row.get("operating_mode") == value.get("operating_mode") for row in sources)
            if aggregate.get("source_episode_count") != expected:
                _fail("clean signal/mode aggregate does not reconcile")
        elif name == "mode_entry_offset":
            expected = sum(row.get("mode_entry_offset") == value for row in sources)
            if aggregate.get("source_episode_count") != expected:
                _fail("clean mode-entry aggregate does not reconcile")
        elif name == "equipment_id":
            expected = sum(row.get("equipment_id") == value for row in equipment)
            if aggregate.get("equipment_episode_count") != expected:
                _fail("clean equipment aggregate does not reconcile")


def _validate_availability_calibration_semantics(result: Mapping[str, Any]) -> None:
    ledger = result["ledger"]
    availability = ledger["availability"]
    calibration = ledger["calibration_profiles"]
    expected_pairs = [(signal_id, operating_mode) for signal_id in CANONICAL_SIGNAL_IDS for operating_mode in CANONICAL_OPERATING_MODES]
    if [(row.get("dimension", {}).get("signal_id"), row.get("dimension", {}).get("operating_mode")) for row in result["aggregates"]["availability"]] != expected_pairs or [(row.get("signal_id"), row.get("operating_mode")) for row in result["reconciliation"]["availability"]] != expected_pairs or [(row.get("dimension", {}).get("signal_id"), row.get("dimension", {}).get("operating_mode")) for row in result["aggregates"]["calibration"]] != expected_pairs or [(row.get("signal_id"), row.get("operating_mode")) for row in result["reconciliation"]["calibration"]] != expected_pairs:
        _fail("availability/calibration aggregate order is not deterministic fixed signal/mode order")
    _assert_unique(availability, ("cell_id", "signal_id", "operating_mode"), "availability")
    _assert_unique(calibration, ("cell_id", "signal_id", "operating_mode"), "calibration_profiles")
    cells = sorted({row.get("cell_id") for row in availability})
    if len(cells) != EXPECTED_COUNTS["cells"]:
        _fail("cell inventory is not the fixed 120-cell inventory")
    expected_seeds = tuple(EXPECTED_COUNTS["seed_values"])
    cell_pairs: set[tuple[Any, Any]] = set()
    for cell_id in cells:
        cell_rows = [row for row in availability if row.get("cell_id") == cell_id]
        profiles = [row for row in calibration if row.get("cell_id") == cell_id]
        cell_seed_layouts = {(row.get("seed"), row.get("layout_index")) for row in cell_rows}
        profile_seed_layouts = {(row.get("seed"), row.get("layout_index")) for row in profiles}
        if len(cell_rows) != 48 or len(profiles) != 48 or len(cell_seed_layouts) != 1 or cell_seed_layouts != profile_seed_layouts:
            _fail(f"cell seed/layout inventory is not exact for {cell_id}")
        seed, layout_index = next(iter(cell_seed_layouts))
        layout_ids = {row.get("layout_id") for row in cell_rows + profiles}
        if isinstance(layout_index, bool) or not isinstance(layout_index, int) or not 0 <= layout_index < len(CANONICAL_LAYOUT_IDS) or len(layout_ids) != 1 or next(iter(layout_ids)) != CANONICAL_LAYOUT_IDS[layout_index] or cell_id != f"seed-{seed:03d}-layout-{layout_index:02d}-{CANONICAL_LAYOUT_IDS[layout_index]}":
            _fail(f"cell identity is not the canonical seed/layout identity: {cell_id}")
        cell_pairs.update(cell_seed_layouts)
    if cell_pairs != {(seed, layout_index) for seed in expected_seeds for layout_index in range(12)}:
        _fail("cell seed/layout pair inventory is not exact")
    for row in availability:
        if row["available_points"] + sum(row["exclusion_counts"].values()) != row["total_points"] or row["total_points"] != 30:
            _fail("availability ledger totals do not reconcile")
    for signal_id, operating_mode in CANONICAL_SIGNAL_MODE_PAIRS:
        rows = [row for row in availability if row["signal_id"] == signal_id and row["operating_mode"] == operating_mode]
        aggregate = next((row for row in result["aggregates"]["availability"] if row.get("dimension") == _pair_dimension(signal_id, operating_mode)), None)
        recon = next((row for row in result["reconciliation"]["availability"] if (row.get("signal_id"), row.get("operating_mode")) == (signal_id, operating_mode)), None)
        if aggregate is None or recon is None or len(rows) != 120:
            _fail(f"availability group coverage is not exact for {(signal_id, operating_mode)!r}")
        available = sum(row["available_points"] for row in rows)
        exclusions = {key: sum(row["exclusion_counts"][key] for row in rows) for key in _EXCLUSION_KEYS}
        if aggregate.get("available_points") != available or aggregate.get("exclusion_counts") != exclusions or available + sum(exclusions.values()) != 3600:
            _fail("availability aggregate does not reconcile")
        if recon.get("available_points") != available or recon.get("excluded_points") != sum(exclusions.values()) or recon.get("total_points") != 3600:
            _fail("availability reconciliation does not reconcile")
        profiles = [row for row in calibration if row["signal_id"] == signal_id and row["operating_mode"] == operating_mode]
        cal_aggregate = next((row for row in result["aggregates"]["calibration"] if row.get("dimension") == _pair_dimension(signal_id, operating_mode)), None)
        if len(profiles) != 120 or cal_aggregate is None or cal_aggregate.get("profile_count") != 120:
            _fail("calibration group coverage is not exact")
        if next((row for row in result["reconciliation"]["calibration"] if (row.get("signal_id"), row.get("operating_mode")) == (signal_id, operating_mode)), {}).get("profile_count") != 120:
            _fail("calibration reconciliation does not reconcile")
        for seed in EXPECTED_COUNTS["seed_values"]:
            seed_rows = [row for row in profiles if row.get("seed") == seed]
            summary = next((row for row in cal_aggregate["seed_summaries"] if row.get("seed") == seed), None)
            if summary is None or len(seed_rows) != 12 or summary.get("profile_count") != 12 or summary.get("layout_indexes") != list(range(12)):
                _fail("calibration seed summary coverage is not exact")
            for field in ("calibration_point_count", "center", "mad", "scale"):
                if summary.get(f"{field}_distribution") != _numeric_distribution(row.get(field) for row in seed_rows):
                    _fail(f"calibration {field} distribution does not reconcile")
            if summary.get("status_counts") != {"calibrated": sum(row.get("status") == "calibrated" for row in seed_rows), "inconclusive": sum(row.get("status") == "inconclusive" for row in seed_rows)}:
                _fail("calibration status distribution does not reconcile")
            if summary.get("reason_counts") != _reason_distribution(row.get("reason") for row in seed_rows):
                _fail("calibration reason distribution does not reconcile")


_NUMERIC_FIELD_NAMES = {
    "seed", "layout_index", "offset", "available_points", "total_points", "point_count", "max_score", "mode_entry_offset",
    "merge_size", "calibration_point_count", "center", "mad", "scale", "denominator", "window_count", "detected_count",
    "event_causal_support_qualified_count", "pre_event_support_count", "run_length", "total_count", "available_count", "exceed_count",
    "source_episode_count", "equipment_episode_count", "profile_count", "excluded_points", "detection_delay_seconds", "persistence_streak",
    "actual", "previous_actual", "residual", "score", "min", "max", "mean", "null_count", "non_null_count", "merge_size_sum", "source_count", "equipment_count",
}
LIMITATIONS = [
    "合成データのみを対象とする探索用の診断であり、顧客実データは含まない。",
    "threshold、モデル、winner、promotion gateは変更せず、性能評価と昇格判定は実施しない。",
    "canonical detectedは正式成果物の値を保持し、因果性補助判定は別フィールドに記録する。",
    "制御系およびBanto Hubへの書込みは行わない。",
]


def _validate_json_number_safety(value: Any, path: str = "$", field_name: str | None = None) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        _fail(f"non-finite JSON number at {path}")
    if field_name in _NUMERIC_FIELD_NAMES and isinstance(value, bool):
        _fail(f"boolean used as a number at {path}")
    if isinstance(value, Mapping):
        for key, child in value.items():
            _validate_json_number_safety(child, f"{path}.{key}", str(key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _validate_json_number_safety(child, f"{path}[{index}]")


def _validate_calibration_null_rules(result: Mapping[str, Any]) -> None:
    for index, row in enumerate(result["ledger"]["calibration_profiles"]):
        status = row.get("status")
        values = (row.get("center"), row.get("mad"), row.get("scale"))
        if status == "calibrated" and any(value is None for value in values):
            _fail(f"calibrated profile {index} has null calibration parameters")
        if status == "inconclusive" and any(value is not None for value in values):
            _fail(f"inconclusive profile {index} has non-null calibration parameters")


def _validate_distribution_shape(result: Mapping[str, Any]) -> None:
    def check(distribution: Mapping[str, Any], label: str) -> None:
        total, non_null, null = distribution.get("total_count"), distribution.get("non_null_count"), distribution.get("null_count")
        if total != non_null + null or total < 0 or non_null < 0 or null < 0:
            _fail(f"{label} numeric distribution counts do not reconcile")
        if non_null == 0 and (distribution.get("min") is not None or distribution.get("max") is not None or distribution.get("mean") is not None):
            _fail(f"{label} empty numeric distribution has values")
        if non_null and (distribution.get("min") is None or distribution.get("max") is None or distribution.get("mean") is None):
            _fail(f"{label} non-empty numeric distribution is missing values")
    for index, aggregate in enumerate(result["aggregates"]["calibration"]):
        for seed_summary in aggregate["seed_summaries"]:
            for field in ("calibration_point_count_distribution", "center_distribution", "mad_distribution", "scale_distribution"):
                check(seed_summary[field], f"calibration[{index}].{field}")


def _is_digest(value: Any, length: int = 64) -> bool:
    return isinstance(value, str) and len(value) == length and all(char in "0123456789abcdef" for char in value)


def _expected_input_provenance() -> dict[str, str]:
    fields = ("result_sha256", "summary_sha256", "completion_marker_sha256", "inventory_sha256")
    for field in fields:
        if not _is_digest(EXPECTED_INPUT_ARTIFACT[field]):
            _fail(f"fixed input artifact pin is not a lowercase SHA-256 digest: {field}")
    return {"path": EXPECTED_INPUT_ROOT, **{field: EXPECTED_INPUT_ARTIFACT[field] for field in fields}}


def _validate_provenance_semantics(result: Mapping[str, Any]) -> None:
    provenance = result.get("provenance")
    if not isinstance(provenance, Mapping) or provenance.get("canonicalization") != CANONICALIZATION_ID:
        _fail("diagnostics provenance canonicalization is not fixed")
    for field in ("artifact_code_revision", "replay_code_revision"):
        revision = provenance.get(field)
        if not isinstance(revision, Mapping) or revision.get("status") != "git" or revision.get("dirty") is not False or not isinstance(revision.get("head"), str) or len(revision["head"]) != 40 or any(char not in "0123456789abcdef" for char in revision["head"]):
            _fail(f"diagnostics provenance revision is not a clean git revision: {field}")
        if not isinstance(revision.get("diff_sha256"), str) or len(revision["diff_sha256"]) != 64 or revision["diff_sha256"] != revision["diff_sha256"].lower() or any(char not in "0123456789abcdef" for char in revision["diff_sha256"]):
            _fail(f"diagnostics provenance revision diff digest is invalid: {field}")
    if provenance["artifact_code_revision"].get("diff_sha256") != _sha256_bytes(b"") or provenance["replay_code_revision"].get("diff_sha256") != _sha256_bytes(b""):
        _fail("diagnostics provenance revision diff is not the clean empty-tree digest")
    if provenance["artifact_code_revision"].get("head") != EXPECTED_ARTIFACT_CODE_REVISION:
        _fail("diagnostics artifact_code_revision is not the fixed artifact revision")
    input_artifact = provenance.get("input_artifact")
    if input_artifact != _expected_input_provenance():
        _fail("diagnostics input artifact provenance does not match the preregistered artifact pins")
    snapshot = provenance.get("input_snapshot")
    if snapshot != {"equal": True, "before_inventory_sha256": EXPECTED_INPUT_ARTIFACT["inventory_sha256"], "after_inventory_sha256": EXPECTED_INPUT_ARTIFACT["inventory_sha256"]}:
        _fail("diagnostics input snapshot is not an equal before/after capture")
    compatibility = provenance.get("revision_compatibility")
    if not isinstance(compatibility, Mapping) or compatibility.get("policy") != EXPECTED_REVISION_COMPATIBILITY["policy"] or compatibility.get("artifact_revision") != provenance.get("artifact_code_revision") or compatibility.get("current_only_paths") != EXPECTED_REVISION_COMPATIBILITY["current_only_paths"]:
        _fail("diagnostics revision compatibility is not tied to artifact_code_revision")
    current = compatibility.get("current_d2_diagnostics")
    if not isinstance(current, Mapping) or set(current) != {"module_raw_sha256", "cli_raw_sha256", "renderer_raw_sha256", "schema_raw_sha256", "config_raw_sha256"} or any(not _is_digest(value) for value in current.values()):
        _fail("diagnostics current D2 source digest record is invalid")
    sources = compatibility.get("semantic_sources")
    if not isinstance(sources, list) or len(sources) != 88:
        _fail("diagnostics semantic source digest records are invalid")
    paths = []
    for source in sources:
        if not isinstance(source, Mapping) or set(source) != {"path", "artifact_blob_sha256", "current_raw_sha256"}:
            _fail("diagnostics semantic source record shape is invalid")
        path = _safe_relative(source["path"], "semantic source")
        if not any(path.startswith(prefix + "/") for prefix in EXPECTED_REVISION_COMPATIBILITY["artifact_source_prefixes"]) or path in EXPECTED_REVISION_COMPATIBILITY["current_only_paths"]:
            _fail("diagnostics semantic source path is outside the historical source tree")
        if not _is_digest(source["artifact_blob_sha256"]) or not _is_digest(source["current_raw_sha256"]) or source["artifact_blob_sha256"] != source["current_raw_sha256"]:
            _fail("diagnostics semantic source digests must be equal lowercase SHA-256 values")
        paths.append(path)
    if paths != sorted(set(paths)):
        _fail("diagnostics semantic source paths must be sorted and unique")
    for field, expected_path, expected_sha in (("config", CONFIG_PATH, EXPECTED_CONFIG_RAW_SHA256), ("config_schema", SCHEMA_PATH, EXPECTED_CONFIG_SCHEMA_RAW_SHA256), ("result_schema", RESULT_SCHEMA_PATH, EXPECTED_RESULT_SCHEMA_RAW_SHA256)):
        source = provenance.get(field)
        if not isinstance(source, Mapping) or source.get("path") != expected_path or source.get("sha256") != expected_sha:
            _fail(f"diagnostics {field} provenance does not match the fixed source bytes")
    if current.get("schema_raw_sha256") != EXPECTED_RESULT_SCHEMA_RAW_SHA256 or current.get("config_raw_sha256") != EXPECTED_CONFIG_RAW_SHA256:
        _fail("current D2 source digest record is inconsistent with fixed config/result sources")


def _merged_clean_intervals(rows: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda item: (_utc_timestamp(item["onset_timestamp"], "clean source onset"), item["source_alert_episode_id"])):
        start, end = _utc_timestamp(row["onset_timestamp"], "clean source onset"), _utc_timestamp(row["end_timestamp"], "clean source end")
        if start > end:
            _fail("clean source interval has start after end")
        if merged and start <= _utc_timestamp(merged[-1]["end_timestamp"], "merged clean end"):
            current_end = _utc_timestamp(merged[-1]["end_timestamp"], "merged clean end")
            merged[-1]["end_timestamp"] = _canonical_utc(max(current_end, end))
            merged[-1]["source_alert_episode_ids"].append(row["source_alert_episode_id"])
        else:
            merged.append({"start_timestamp": _canonical_utc(start), "end_timestamp": _canonical_utc(end), "source_alert_episode_ids": [row["source_alert_episode_id"]]})
    return merged


def _utc_timestamp(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        _fail(f"{label} must be a UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AnomalyFailureDiagnosticsError(f"{label} is not parseable as a UTC timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        _fail(f"{label} must include UTC timezone")
    return parsed


def _canonical_utc(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _mode_entry_offset(timestamp: Any, mode: Any, generator_config: Mapping[str, Any]) -> int:
    onset = _utc_timestamp(timestamp, "clean source onset")
    interval_ms = generator_config.get("sampling_interval_ms")
    if isinstance(interval_ms, bool) or not isinstance(interval_ms, int) or interval_ms <= 0:
        _fail("generator sampling interval is invalid")
    start = _utc_timestamp(generator_config.get("start_timestamp"), "generator start timestamp")
    interval = timedelta(milliseconds=interval_ms)
    regimes = generator_config.get("regimes")
    if not isinstance(regimes, list):
        _fail("generator regimes are missing for mode-entry replay")
    sample_position = (onset - start).total_seconds() / interval.total_seconds()
    if not sample_position.is_integer() or sample_position < 0:
        _fail("clean source onset is not an aligned generator sample")
    sample_index = int(sample_position)
    matches = [regime for regime in regimes if isinstance(regime, Mapping) and regime.get("regime") == mode and int(regime.get("start_sample", -1)) <= sample_index < int(regime.get("end_sample", -1))]
    if len(matches) != 1:
        _fail(f"generator mode regime containing onset is not unique: {mode!r}/{sample_index}")
    delta = interval * (sample_index - int(matches[0]["start_sample"]))
    sample_offset = delta.total_seconds() / interval.total_seconds()
    if not sample_offset.is_integer() or not 0 <= int(sample_offset) <= 29:
        _fail("clean source onset is not an aligned mode-entry offset in 0..29")
    return int(sample_offset)


def _validate_clean_interval_replay(result: Mapping[str, Any]) -> None:
    sources = result["ledger"]["clean_source_alerts"]
    equipment = result["ledger"]["clean_equipment_alerts"]
    by_group: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    actual_by_group: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in sources:
        by_group[(row["cell_id"], row["equipment_id"])].append(row)
    for row in equipment:
        actual_by_group[(row["cell_id"], row["equipment_id"])].append(row)
    for group, rows in by_group.items():
        expected = _merged_clean_intervals(rows)
        actual = sorted(actual_by_group.get(group, []), key=lambda item: _utc_timestamp(item["start_timestamp"], "clean equipment start"))
        if len(expected) != len(actual):
            _fail(f"clean interval merge cardinality differs for {group!r}")
        for expected_item, actual_item in zip(expected, actual):
            if _utc_timestamp(actual_item["start_timestamp"], "clean equipment start") != _utc_timestamp(expected_item["start_timestamp"], "merged start") or _utc_timestamp(actual_item["end_timestamp"], "clean equipment end") != _utc_timestamp(expected_item["end_timestamp"], "merged end") or actual_item["source_alert_episode_ids"] != expected_item["source_alert_episode_ids"] or actual_item["merge_size"] != len(expected_item["source_alert_episode_ids"]):
                _fail(f"clean interval merge replay differs for {group!r}")
    for group in set(actual_by_group) - set(by_group):
        _fail(f"clean equipment episode has no source interval for {group!r}")


def _validate_result_semantics(result: Mapping[str, Any]) -> None:
    _validate_json_number_safety(result)
    _validate_provenance_semantics(result)
    for section, rows in result["ledger"].items():
        if isinstance(rows, list):
            _validate_ledger_order(section, rows)
    _validate_calibration_null_rules(result)
    _validate_distribution_shape(result)
    _validate_clean_interval_replay(result)
    _validate_incident_semantics(result)
    _validate_clean_semantics(result)
    _validate_availability_calibration_semantics(result)


def _validate_diagnostics_draft(draft: Mapping[str, Any], schema: Mapping[str, Any]) -> None:
    """Check untrusted draft semantics only; never attest that a live replay occurred."""
    if any(draft.get(field) != value for field, value in _DRAFT_FLAGS.items()):
        _fail("untrusted diagnostics draft has invalid draft-only status flags")
    # A transient schema projection preserves the frozen completed-result schema.
    # It is neither returned nor issued as a VerifiedDiagnosticsResult.
    _validate_result_payload({**draft, **_COMPLETE_FLAGS}, schema)


def _validate_result_payload(result: Mapping[str, Any], schema: Mapping[str, Any]) -> None:
    """Private shape/semantic check, not live-replay evidence or a result issuer."""
    if _sha256_bytes(_canonical_json(schema)) != EXPECTED_RESULT_SCHEMA_CANONICAL_SHA256:
        _fail("diagnostics result schema is not the fixed schema")
    _validate_json_number_safety(result)
    try:
        validate(result, schema)
    except ManifestValidationError as exc:
        raise AnomalyFailureDiagnosticsError(f"diagnostics result does not satisfy its schema: {exc}") from exc
    if result.get("status") != "complete" or result.get("run_status") != "complete" or result.get("exploratory_only") is not True or result.get("promotion_eligible") is not False:
        _fail("diagnostics result status flags are not the fixed exploratory contract")
    _validate_d2_domain_semantics(result)
    _validate_result_semantics(result)


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _git_run(root: Path, *args: str) -> bytes:
    try:
        environment = {**os.environ, "GIT_OPTIONAL_LOCKS": "0", "GIT_NO_LAZY_FETCH": "1"}
        completed = subprocess.run(["git", "-c", "core.fsmonitor=false", *args], cwd=root, env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    except OSError as exc:
        raise AnomalyFailureDiagnosticsError("git is unavailable for fail-closed revision verification") from exc
    if completed.returncode != 0:
        raise AnomalyFailureDiagnosticsError(f"git verification failed: {' '.join(args)}")
    return completed.stdout


def _git_revision(root: Path, expected_head: str | None = None) -> dict[str, Any]:
    if expected_head is not None and not _is_digest(expected_head, 40):
        _fail("expected replay HEAD must be a full lowercase git commit")
    head = _git_run(root, "rev-parse", "--verify", "HEAD").decode("ascii", errors="strict").strip()
    if len(head) != 40 or any(char not in "0123456789abcdef" for char in head):
        _fail("repository HEAD is not a full hexadecimal commit")
    if expected_head is not None and head != expected_head:
        _fail(f"replay HEAD is not the expected clean commit: {head}")
    status = _git_run(root, "status", "--porcelain", "--untracked-files=all")
    if status:
        _fail("replay repository is dirty")
    diff = _git_run(root, "diff", "--binary", "--no-ext-diff", "--no-textconv")
    if diff:
        _fail("replay diff is not empty")
    return {"status": "git", "head": head, "dirty": False, "diff_sha256": _sha256_bytes(diff)}


def _git_tree(root: Path, revision: str, prefixes: Iterable[str]) -> dict[str, tuple[str, bytes, str]]:
    raw = _git_run(root, "ls-tree", "-r", "-z", "--full-tree", revision, "--", *prefixes)
    tree: dict[str, tuple[str, bytes, str]] = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        try:
            metadata, path_raw = record.split(b"\t", 1)
            mode, kind, blob = metadata.decode("ascii").split(" ")
            path = path_raw.decode("utf-8")
        except (UnicodeDecodeError, ValueError) as exc:
            _fail("historical git tree is malformed")
        if kind != "blob" or mode not in {"100644", "100755"}:
            _fail(f"historical tree entry is not a regular file: {path}")
        if path in tree:
            _fail(f"historical git tree contains a duplicate path: {path}")
        blob_bytes = _git_run(root, "cat-file", "blob", f"{revision}:{path}")
        tree[path] = (_sha256_bytes(blob_bytes), blob_bytes, mode)
    return tree


def _workspace_regular_files(root: Path, prefixes: Iterable[str]) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for prefix in prefixes:
        base = root / prefix
        if _is_reparse_point(base) or not base.is_dir():
            _fail(f"revision source prefix is not a regular directory: {prefix}")
        for directory, dirnames, filenames in os.walk(base, topdown=True, followlinks=False):
            directory_path = Path(directory)
            safe_dirs: list[str] = []
            for dirname in dirnames:
                path = directory_path / dirname
                if _is_reparse_point(path):
                    _fail(f"revision source tree contains a reparse point: {path}")
                if not path.is_dir():
                    _fail(f"revision source tree contains a non-directory entry: {path}")
                safe_dirs.append(dirname)
            dirnames[:] = safe_dirs
            for filename in filenames:
                path = directory_path / filename
                if _is_reparse_point(path) or not path.is_file():
                    _fail(f"revision source tree contains a non-regular file: {path}")
                relative = path.relative_to(root).as_posix()
                files[relative] = path.read_bytes()
    return files


def _validate_revision_compatibility(root: Path | None = None, *, replay_head: str) -> dict[str, Any]:
    """Compare the historical artifact code tree with current regular-file bytes, without checkout or execution."""
    repository = _repository(root)
    if not _is_digest(replay_head, 40):
        _fail("expected replay HEAD is required")
    current_revision = _git_revision(repository, replay_head)
    prefixes = tuple(EXPECTED_REVISION_COMPATIBILITY["artifact_source_prefixes"])
    historical = _git_tree(repository, EXPECTED_ARTIFACT_CODE_REVISION, prefixes)
    if len(historical) != 88:
        _fail("historical artifact tree must contain exactly 88 regular files")
    current_index = _git_tree(repository, current_revision["head"], prefixes)
    current = _workspace_regular_files(repository, prefixes)
    current_only_order = list(EXPECTED_REVISION_COMPATIBILITY["current_only_paths"])
    current_only = set(current_only_order)
    if set(historical) & current_only:
        _fail("current-only revision paths overlap the historical artifact tree")
    expected_paths = set(historical) | current_only
    if set(current_index) != expected_paths:
        _fail("current Git index path set differs from the historical tree plus the fixed current-only allowlist")
    if set(current) != expected_paths:
        missing, extra = sorted(expected_paths - set(current)), sorted(set(current) - expected_paths)
        _fail(f"revision source tree path set differs; missing={missing!r}, extra={extra!r}")
    semantic_sources: list[dict[str, str]] = []
    for path in sorted(historical):
        current_raw = current[path]
        blob_sha, historical_raw, historical_mode = historical[path]
        if current_index[path][2] != historical_mode:
            _fail(f"Git mode differs from artifact revision: {path}")
        if current_raw != historical_raw:
            _fail(f"revision source bytes differ from artifact revision: {path}")
        if _sha256_bytes(historical_raw) != blob_sha:
            _fail(f"historical blob hash differs from git content: {path}")
        semantic_sources.append({"path": path, "artifact_blob_sha256": blob_sha, "current_raw_sha256": _sha256_bytes(current_raw)})
    for path in sorted(current_only):
        if current_index[path][2] not in {"100644", "100755"}:
            _fail(f"current-only Git entry is not a regular file: {path}")
    for path in expected_paths:
        if current_index[path][1] != current[path]:
            _fail(f"current raw bytes differ from clean Git HEAD: {path}")
    source_files = {
        "module_raw_sha256": "src/banto_ai/anomaly_failure_diagnostics.py",
        "cli_raw_sha256": "tools/evaluator/diagnose_anomaly_matrix.py",
        "renderer_raw_sha256": "tools/evaluator/render_anomaly_failure_diagnostics.py",
        "schema_raw_sha256": RESULT_SCHEMA_PATH,
        "config_raw_sha256": CONFIG_PATH,
    }
    current_d2: dict[str, str] = {}
    for field, relative in source_files.items():
        path = _safe_repo_path(repository, relative, "current D2 source", must_exist=True)
        if _is_reparse_point(path) or not path.is_file():
            _fail(f"current D2 diagnostic source is not a regular file: {relative}")
        current_d2[field] = _sha256_bytes(path.read_bytes())
    return {
        "policy": EXPECTED_REVISION_COMPATIBILITY["policy"],
        "artifact_revision": {"status": "git", "head": EXPECTED_ARTIFACT_CODE_REVISION, "dirty": False, "diff_sha256": _sha256_bytes(b"")},
        "semantic_sources": semantic_sources,
        "current_only_paths": current_only_order,
        "current_d2_diagnostics": current_d2,
        "replay_revision": current_revision,
    }


def _exclusion_totals(rows: Iterable[Mapping[str, Any]], field: str = "exclusion_counts", keys: Iterable[str] = _EXCLUSION_KEYS) -> dict[str, int]:
    return {key: sum(int(row[field][key]) for row in rows) for key in keys}


def _pair_dimension(signal_id: str, operating_mode: str) -> dict[str, Any]:
    return {"signal_id": signal_id, "operating_mode": operating_mode}


def _build_aggregates(ledger: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    windows = ledger["incident_windows"]
    points = ledger["incident_points"]
    incident_windows: list[dict[str, Any]] = []
    incident_offsets: list[dict[str, Any]] = []
    for name, values in _incident_dimensions():
        for value in values:
            selected = [row for row in windows if row.get(name) == value]
            dimension = {"dimension_name": name, "dimension_value": value}
            incident_windows.append({
                "dimension": dimension, "count_unit": "eligible_incident_windows", "scope": "marginal_over_other_incident_dimensions", "denominator": len(selected), "window_count": len(selected),
                "detected_count": sum(row["detected"] is True for row in selected), "event_causal_support_qualified_count": sum(row["event_causal_support_qualified"] is True for row in selected), "pre_event_support_count": sum(row["pre_event_support"] is True for row in selected),
                "max_consecutive_run_distribution": [{"run_length": run, "window_count": sum(row["max_in_window_consecutive_exceedances"] == run for row in selected)} for run in range(7)],
            })
            for offset in (-1, 0, 1, 2, 3, 4, 5):
                selected_points = [row for row in points if row.get(name) == value and row.get("offset") == offset]
                incident_offsets.append({"dimension": dimension, "count_unit": "incident_points", "scope": "marginal_over_other_incident_dimensions", "denominator": len(selected) * 7, "offset": offset, "total_count": len(selected_points), "available_count": sum(row["available"] is True for row in selected_points), "exceed_count": sum(row["exceeds_threshold"] is True for row in selected_points)})

    sources, equipment = ledger["clean_source_alerts"], ledger["clean_equipment_alerts"]
    clean_aggregates: list[dict[str, Any]] = []
    for name, values in _clean_dimensions():
        for value in values:
            if name == "signal_id×operating_mode":
                selected = sum(row["signal_id"] == value[0] and row["operating_mode"] == value[1] for row in sources)
                dimension_value: Any = _pair_dimension(value[0], value[1])
            else:
                selected = sum(row.get(name) == value for row in sources)
                dimension_value = value
            clean_aggregates.append({"dimension": {"dimension_name": name, "dimension_value": dimension_value}, "count_unit": "source_alert_episodes", "scope": "source_alert_episode_marginal", "source_episode_count": selected})
    for equipment_id in CANONICAL_EQUIPMENT_IDS:
        clean_aggregates.append({"dimension": {"dimension_name": "equipment_id", "dimension_value": equipment_id}, "count_unit": "equipment_merged_episodes", "scope": "equipment_merged_episode_marginal", "equipment_episode_count": sum(row["equipment_id"] == equipment_id for row in equipment), "equipment_attribution_rule": "equipment_episode_count=count of cell-local merged equipment episodes whose equipment_id equals dimension_value, each episode counted exactly once"})

    availability_aggregates: list[dict[str, Any]] = []
    calibration_aggregates: list[dict[str, Any]] = []
    for signal_id, operating_mode in ((signal, mode) for signal in CANONICAL_SIGNAL_IDS for mode in CANONICAL_OPERATING_MODES):
        availability_rows = [row for row in ledger["availability"] if row["signal_id"] == signal_id and row["operating_mode"] == operating_mode]
        profiles = [row for row in ledger["calibration_profiles"] if row["signal_id"] == signal_id and row["operating_mode"] == operating_mode]
        exclusion_counts = _exclusion_totals(availability_rows)
        availability_aggregates.append({"dimension": _pair_dimension(signal_id, operating_mode), "available_points": sum(row["available_points"] for row in availability_rows), "total_points": sum(row["total_points"] for row in availability_rows), "exclusion_counts": exclusion_counts})
        seed_summaries: list[dict[str, Any]] = []
        for seed in EXPECTED_COUNTS["seed_values"]:
            seed_rows = [row for row in profiles if row["seed"] == seed]
            seed_summaries.append({"seed": seed, "layout_indexes": sorted(row["layout_index"] for row in seed_rows), "profile_count": len(seed_rows), "calibration_point_count_distribution": _numeric_distribution(row["calibration_point_count"] for row in seed_rows), "center_distribution": _numeric_distribution(row["center"] for row in seed_rows), "mad_distribution": _numeric_distribution(row["mad"] for row in seed_rows), "scale_distribution": _numeric_distribution(row["scale"] for row in seed_rows), "status_counts": {"calibrated": sum(row["status"] == "calibrated" for row in seed_rows), "inconclusive": sum(row["status"] == "inconclusive" for row in seed_rows)}, "reason_counts": _reason_distribution(row["reason"] for row in seed_rows)})
        calibration_aggregates.append({"grain": "signal_id×operating_mode", "dimension": _pair_dimension(signal_id, operating_mode), "profile_count": len(profiles), "seed_summaries": seed_summaries})

    cells = sorted({row["cell_id"] for row in ledger["availability"]})
    clean_reconciliation: list[dict[str, Any]] = []
    source_by_group: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    equipment_by_group: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in sources: source_by_group[(row["cell_id"], row["equipment_id"])].append(row)
    for row in equipment: equipment_by_group[(row["cell_id"], row["equipment_id"])].append(row)
    for cell_id in cells:
        for equipment_id in CANONICAL_EQUIPMENT_IDS:
            group = (cell_id, equipment_id)
            merged = equipment_by_group.get(group, [])
            clean_reconciliation.append({"cell_id": cell_id, "equipment_id": equipment_id, "source_count": sum(len(row["source_alert_episode_ids"]) for row in merged), "equipment_count": len(merged), "merge_size_sum": sum(row["merge_size"] for row in merged), "interval_boundary": "[start,end)", "source_ids_scope": "cell_id+equipment_id", "source_ids_exact": {source["source_alert_episode_id"] for source in source_by_group.get(group, [])} == {source_id for row in merged for source_id in row["source_alert_episode_ids"]}, "merge_size_rule": "merge_size=len(source_alert_episode_ids)", "source_count_rule": "source_count=sum(len(source_alert_episode_ids)) within each cell/equipment", "interval_merge_replay": "canonical_[start,end)_interval_merge", "exact": True})
    availability_reconciliation = [{"signal_id": signal_id, "operating_mode": operating_mode, "available_points": row["available_points"], "total_points": row["total_points"], "excluded_points": sum(row["exclusion_counts"].values()), "exclusion_reasons_exact": True, "exact": True} for row in availability_aggregates for signal_id, operating_mode in [(row["dimension"]["signal_id"], row["dimension"]["operating_mode"])] ]
    calibration_reconciliation = [{"signal_id": row["dimension"]["signal_id"], "operating_mode": row["dimension"]["operating_mode"], "profile_count": row["profile_count"], "grain": "signal_id×operating_mode", "exact": True} for row in calibration_aggregates]
    return {"incident_window_aggregates": incident_windows, "incident_offset_aggregates": incident_offsets, "clean_alerts": clean_aggregates, "availability": availability_aggregates, "calibration": calibration_aggregates}, {"clean_alerts": clean_reconciliation, "availability": availability_reconciliation, "calibration": calibration_reconciliation, "cardinality_exact": True}


def _build_diagnostics_draft(replay: Mapping[str, Any], provenance: Mapping[str, Any], *, schema: Mapping[str, Any]) -> dict[str, Any]:
    """Build an untrusted private draft; pure reconciliation is not replay evidence."""
    ledger = replay.get("ledger")
    if not isinstance(ledger, Mapping):
        _fail("verified replay payload is missing ledger data")
    _validate_json_number_safety(ledger)
    ledger = deepcopy(ledger)
    aggregates, reconciliation = _build_aggregates(ledger)
    counts = json.loads(json.dumps(EXPECTED_COUNTS))
    ordered_ledger = {key: sorted(list(value), key=lambda row, section=key: _ledger_sort_key(section, row)) for key, value in ledger.items()}
    result = {
        "schema_version": SCHEMA_VERSION, "result_type": RESULT_TYPE, "diagnostics_id": DIAGNOSTICS_ID, "matrix_id": EXPECTED_MATRIX_ID,
        **_DRAFT_FLAGS, "performance_status": "not_evaluated", "exploratory_only": True, "promotion_eligible": False,
        "provenance": deepcopy(provenance), "counts": counts, "ledger": ordered_ledger, "aggregates": aggregates, "reconciliation": reconciliation,
        "limitations": list(LIMITATIONS),
    }
    _validate_diagnostics_draft(result, schema)
    return result


def replay_and_build_diagnostics_result(root: Path, *, replay_head: str) -> VerifiedDiagnosticsResult:
    """Public read-only API: return a sealed result without claiming or writing output."""
    result, _, _ = _replay_and_build_with_context(root, replay_head=replay_head)
    return result


def _replay_and_build_with_context(root: Path, *, replay_head: str) -> tuple[VerifiedDiagnosticsResult, dict[str, Any], bytes]:
    """Retain fresh replay context privately for D2-B's marker-boundary rechecks."""
    verified = _verify_input_replay(root, replay_head=replay_head)
    ledgers = _build_ledgers_from_verified_replay(verified)
    provenance = _build_provenance_from_verified_replay(verified, root)
    schema = verified["diagnostics_result_schema_source"].get("value")
    if not isinstance(schema, Mapping):
        _fail("verified replay did not retain the fixed diagnostics result schema")
    result = _build_diagnostics_draft({"ledger": ledgers}, provenance, schema=schema)
    if result["provenance"] != _build_provenance_from_verified_replay(verified, root):
        _fail("built provenance differs from the verified replay")
    original_payload = _canonical_json({**result, **_COMPLETE_FLAGS})
    _recheck_verified_replay_boundary(verified, _repository(root))
    sealed = VerifiedDiagnosticsResult({**result, **_COMPLETE_FLAGS}, _token=_VERIFIED_RESULT_TOKEN)
    return sealed, verified, original_payload


def _filesystem_identity(metadata: os.stat_result) -> tuple[int, int]:
    identity = (metadata.st_dev, metadata.st_ino)
    if not identity[1]:
        _fail("filesystem identity is unavailable; refusing diagnostics publication")
    return identity


def _directory_identity(path: Path) -> tuple[int, int]:
    metadata = path.lstat()
    if not stat.S_ISDIR(metadata.st_mode) or _is_reparse_point(path):
        _fail("diagnostics output ancestry is not a regular directory")
    return _filesystem_identity(metadata)


def _require_windows_publication() -> None:
    if os.name != "nt":
        _fail("D2-B publication is Windows-only; --run is disabled on non-Windows; --validate-only and D2-A read-only replay remain available")


def _prepare_publication_rename() -> Callable[[Any, Any, int | None], None]:
    """Resolve a no-replace directory rename before staging; never emulate overwrite."""
    _require_windows_publication()
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.SetFileInformationByHandle.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
        kernel.SetFileInformationByHandle.restype = wintypes.BOOL

        class FileRenameInfo(ctypes.Structure):
            _fields_ = [("ReplaceIfExists", ctypes.c_ubyte), ("RootDirectory", wintypes.HANDLE),
                        ("FileNameLength", wintypes.DWORD), ("FileName", wintypes.WCHAR * 1)]

        def windows_rename(source: Any, target: Any, directory_fd: int | None) -> None:
            if directory_fd is not None or type(source) is not int or source <= 0 or not Path(target).is_absolute() or Path(target).name != Path(EXPECTED_OUTPUT_ROOT).name:
                _fail("Windows publication rename requires the held staging handle and fixed target")
            # FileRenameInfo (3), ReplaceIfExists=FALSE. The SOURCE is the held
            # DELETE-capable staging handle, never a mutable source path.
            # RootDirectory=NULL plus the absolute target is the documented Win32
            # form. The output/ancestry directory guards remain held throughout.
            raw = str(target).encode("utf-16-le")
            buffer = ctypes.create_string_buffer(max(ctypes.sizeof(FileRenameInfo), FileRenameInfo.FileName.offset + len(raw) + 2))
            info = FileRenameInfo.from_buffer(buffer)
            info.ReplaceIfExists, info.RootDirectory, info.FileNameLength = 0, None, len(raw)
            ctypes.memmove(ctypes.addressof(buffer) + FileRenameInfo.FileName.offset, raw, len(raw))
            if not kernel.SetFileInformationByHandle(source, 3, buffer, len(buffer)):
                raise ctypes.WinError(ctypes.get_last_error())
        return windows_rename


def _create_private_staging_directory(path: Path, parent_fd: int | None) -> None:
    _require_windows_publication()
    if parent_fd is not None:
        _fail("Windows staging cannot accept a directory descriptor")
    import ctypes
    from ctypes import wintypes
    security = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    security.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(wintypes.LPVOID), wintypes.LPVOID]
    security.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wintypes.BOOL
    class SecurityAttributes(ctypes.Structure):
        _fields_ = [("nLength", wintypes.DWORD), ("lpSecurityDescriptor", wintypes.LPVOID), ("bInheritHandle", wintypes.BOOL)]
    kernel.CreateDirectoryW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(SecurityAttributes)]
    kernel.CreateDirectoryW.restype = wintypes.BOOL
    kernel.LocalFree.argtypes, kernel.LocalFree.restype = [wintypes.LPVOID], wintypes.LPVOID
    descriptor = wintypes.LPVOID()
    # Private and protected FROM CREATION, on both Python versions. No inheritable
    # ACEs means future children get token-default, explicit DACLs; freezing this
    # directory later cannot remove ACEs inherited from this parent on a racing
    # extra child. Never apply a new initial ACL to a preexisting path.
    if not security.ConvertStringSecurityDescriptorToSecurityDescriptorW("D:P(A;;FA;;;OW)(A;;FA;;;SY)(A;;FA;;;BA)", 1, ctypes.byref(descriptor), None):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        attributes = SecurityAttributes(ctypes.sizeof(SecurityAttributes), descriptor, False)
        if not kernel.CreateDirectoryW(str(path), ctypes.byref(attributes)):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel.LocalFree(descriptor)


def _set_windows_dacl(handle: int, sddl: str) -> None:
    """Set only a held object's protected DACL, never owner/group or a named tree."""
    import ctypes
    from ctypes import wintypes
    security = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    security.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(wintypes.LPVOID), wintypes.LPVOID]
    security.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wintypes.BOOL
    security.GetSecurityDescriptorDacl.argtypes = [wintypes.LPVOID, ctypes.POINTER(wintypes.BOOL), ctypes.POINTER(wintypes.LPVOID), ctypes.POINTER(wintypes.BOOL)]
    security.GetSecurityDescriptorDacl.restype = wintypes.BOOL
    security.SetSecurityInfo.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.DWORD, wintypes.LPVOID, wintypes.LPVOID, wintypes.LPVOID, wintypes.LPVOID]
    security.SetSecurityInfo.restype = wintypes.DWORD
    kernel.LocalFree.argtypes, kernel.LocalFree.restype = [wintypes.LPVOID], wintypes.LPVOID
    descriptor = wintypes.LPVOID()
    if not security.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, 1, ctypes.byref(descriptor), None):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        present, defaulted, dacl = wintypes.BOOL(), wintypes.BOOL(), wintypes.LPVOID()
        if not security.GetSecurityDescriptorDacl(descriptor, ctypes.byref(present), ctypes.byref(dacl), ctypes.byref(defaulted)):
            raise ctypes.WinError(ctypes.get_last_error())
        if not present.value or not dacl.value:
            _fail("diagnostics staging DACL must not be absent or null")
        error = security.SetSecurityInfo(handle, 1, 0x80000004, None, None, dacl, None)
        if error:
            raise ctypes.WinError(error)
    finally:
        kernel.LocalFree(descriptor)


class _OutputDirectoryGuard:
    """No-follow directory binding; Windows guards deny delete sharing.

    Repository/artifacts guards allow write sharing so unrelated children remain
    usable. Staging denies write/delete sharing and carries its own rename rights.
    These publication guards are Windows-only.
    """

    def __init__(self, path: Path, *, allow_directory_writes: bool = False, staging: bool = False):
        _require_windows_publication()
        self.path, self.identity = path, _directory_identity(path)
        self.fd, self.handle, self.kernel = None, None, None
        try:
            if os.name == "nt":
                import ctypes
                from ctypes import wintypes
                self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
                self.kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
                self.kernel.CreateFileW.restype = wintypes.HANDLE
                self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
                self.kernel.CloseHandle.restype = wintypes.BOOL
                # FILE_LIST_DIRECTORY | FILE_READ_ATTRIBUTES, FILE_SHARE_READ, OPEN_EXISTING,
                # FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT.
                # Attribute-only handles do NOT enforce the rename sharing lock.
                access = 0x81 | (0x70000 if staging else 0)  # DELETE | READ_CONTROL | WRITE_DAC for private staging only.
                handle = self.kernel.CreateFileW(str(path), access, 0x3 if allow_directory_writes else 0x1, None, 3, 0x02200000, None)
                if handle == ctypes.c_void_p(-1).value:
                    raise ctypes.WinError(ctypes.get_last_error())
                self.handle = handle
            self.check()
        except BaseException:
            self.close()
            raise

    def check(self) -> None:
        if _directory_identity(self.path) != self.identity:
            _fail("diagnostics output directory identity changed")

    def close(self) -> None:
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
        if self.handle is not None:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


class _DiagnosticsOutputClaim:
    """Tentative private staging reservation, never authority to delete anything.

    mkdir and acquiring an identity/handle are not atomic. A hostile same-user
    empty-directory swap in between cannot be reliably detected by this API.
    """

    def __init__(self, repository: Path):
        _require_windows_publication()
        self.repository = repository
        self.destination = repository / EXPECTED_OUTPUT_ROOT
        self.path = self.destination.parent / (_STAGING_PREFIX + uuid.uuid4().hex)
        self.guards: list[_OutputDirectoryGuard] = []
        self.directory: _OutputDirectoryGuard | None = None
        self.identity: tuple[int, int] | None = None
        self.claimed = False
        self.pinned_descriptors: dict[str, int] = {}
        self.files: dict[str, tuple[int, int]] = {}

    def claim(self) -> None:
        _require_windows_publication()
        parent = _safe_repo_path(self.repository, "artifacts", "diagnostics output parent", must_exist=True)
        # Do not lock ancestors above the repository or block sibling writes.
        for ancestor in (self.repository, parent):
            self.guards.append(_OutputDirectoryGuard(ancestor, allow_directory_writes=True))
        self.check_parents()
        parent_fd = self.guards[-1].fd
        _create_private_staging_directory(self.path, parent_fd)  # One attempt; no adoption/recovery.
        self.claimed = True
        self.identity = _directory_identity(self.path)
        self.directory = _OutputDirectoryGuard(self.path, staging=True)
        self.check()
        with os.scandir(self.directory.fd if self.directory.fd is not None else self.path) as entries:
            if next(entries, None) is not None:
                _fail("new diagnostics output is not empty; possible competing writer")

    def check_parents(self) -> None:
        for guard in self.guards:
            guard.check()
        _safe_repo_path(self.repository, self.path.relative_to(self.repository).as_posix(), "diagnostics staging", must_exist=False)
        _safe_repo_path(self.repository, EXPECTED_OUTPUT_ROOT, "diagnostics output", must_exist=False)

    def check(self) -> None:
        self.check_parents()
        if not self.claimed or self.identity is None or _directory_identity(self.path) != self.identity:
            _fail("diagnostics output claim no longer names its original directory")
        if self.directory is not None:
            self.directory.check()

    def _leaf(self, name: str) -> tuple[Any, dict[str, Any]]:
        if name not in {"result.json", "summary.md", _STAGED_MARKER}:
            _fail("diagnostics file name is not fixed")
        if self.directory is not None and self.directory.fd is not None:
            return name, {"dir_fd": self.directory.fd}
        return self.path / name, {}

    def write_exclusive(self, name: str, payload: bytes) -> None:
        self.check()
        target, relative = self._leaf(name)
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0), 0o600, **relative)
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                _fail("diagnostics output file is not regular")
            self.files[name] = _filesystem_identity(metadata)
            with os.fdopen(descriptor, "wb") as handle:
                descriptor = None
                if handle.write(payload) != len(payload):
                    _fail("diagnostics output write was incomplete")
                handle.flush()
                os.fsync(handle.fileno())
        finally:
            if descriptor is not None:
                os.close(descriptor)
        self.check()

    def read_owned(self, name: str) -> bytes:
        self.check()
        target, relative = self._leaf(name)
        metadata = os.stat(target, follow_symlinks=False, **relative)
        if not stat.S_ISREG(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT or _filesystem_identity(metadata) != self.files.get(name):
            _fail("diagnostics output file identity or regular-file status changed")
        if name in self.pinned_descriptors:
            # Verify the same identity-bound handle acquired before permissions
            # were frozen, without closing any pin during final validation.
            descriptor = self.pinned_descriptors[name]
            if _filesystem_identity(os.fstat(descriptor)) != self.files[name]:
                _fail("pinned diagnostics file identity changed")
            os.lseek(descriptor, 0, os.SEEK_SET)
            chunks = []
            while chunk := os.read(descriptor, 65536):
                chunks.append(chunk)
            return b"".join(chunks)
        descriptor = os.open(target, os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0), **relative)
        try:
            if _filesystem_identity(os.fstat(descriptor)) != self.files[name]:
                _fail("diagnostics output file changed during readback")
            with os.fdopen(descriptor, "rb") as handle:
                descriptor = None
                return handle.read()
        finally:
            if descriptor is not None:
                os.close(descriptor)

    def verify_files(self, expected: Mapping[str, bytes]) -> None:
        self.check()
        with os.scandir(self.directory.fd if self.directory.fd is not None else self.path) as entries:
            names = set()
            for entry in entries:
                metadata = entry.stat(follow_symlinks=False)
                if not stat.S_ISREG(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT:
                    _fail("diagnostics output must have no directories, links, or reparse points")
                names.add(entry.name)
        if names != set(expected):
            _fail("diagnostics output file inventory is not exact")
        for name, raw in expected.items():
            if self.read_owned(name) != raw:
                _fail("diagnostics output bytes/hash readback differs")

    def prepare_publication_commit(self) -> None:
        _require_windows_publication()
        self._pin_and_freeze_windows_staging()

    def install_output(self, rename: Callable[[Any, Any, int | None], None]) -> None:
        _require_windows_publication()
        self.check()
        if self.pinned_descriptors:
            _fail("publication requires all child handles released after final verification")
        # FINAL commit: all three prepared files become visible at the fixed path
        # together. No read, verification, mutation or cleanup may follow.
        rename(self.directory.handle, self.destination, None)

    def _pin_and_freeze_windows_staging(self) -> None:
        """Reject existing writers, then freeze both bytes AND directory inventory."""
        import ctypes
        import msvcrt
        kernel = self.directory.kernel
        # READ_DATA | READ_ATTRIBUTES, SHARE_READ only: no concurrent writer,
        # replacement, unlink or rename. An already-open incompatible writer or
        # delete-capable handle makes this acquisition fail closed.
        for name in ("result.json", "summary.md", _STAGED_MARKER):
            access = 0x60081  # READ_DATA | READ_ATTRIBUTES | READ_CONTROL | WRITE_DAC.
            handle = kernel.CreateFileW(str(self.path / name), access, 0x1, None, 3, 0x00200000, None)
            if handle == ctypes.c_void_p(-1).value:
                raise ctypes.WinError(ctypes.get_last_error())
            try:
                descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
            except BaseException:
                kernel.CloseHandle(handle)
                raise
            self.pinned_descriptors[name] = descriptor
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT or _filesystem_identity(metadata) != self.files[name]:
                _fail("pinned diagnostics handle differs from its exclusive file")
        # Deny ordinary file mutation/deletion and directory add-child/delete-child.
        # No inheritable ACEs: only these four held objects are changed. Owner keeps
        # WRITE_DAC for explicit manual inspection/recovery; this is NOT a sandbox
        # against an owner deliberately changing permissions or privileged access.
        for descriptor in self.pinned_descriptors.values():
            _set_windows_dacl(msvcrt.get_osfhandle(descriptor), "D:P(D;;0x10116;;;WD)(A;;FA;;;OW)(A;;FA;;;SY)(A;;FA;;;BA)")
        _set_windows_dacl(self.directory.handle, "D:P(D;;0x10156;;;WD)(A;;FA;;;OW)(A;;FA;;;SY)(A;;FA;;;BA)")

    def release_child_handles(self) -> None:
        # Windows refuses directory rename while any child handle is open, even
        # with delete sharing. Frozen permissions remain in place across release.
        for name in list(self.pinned_descriptors):
            descriptor = self.pinned_descriptors.pop(name)
            os.close(descriptor)  # Any error is still BEFORE the commit point.

    def close(self) -> None:
        # Best-effort handle release only: an already committed publication must
        # never be reported as failed because releasing a handle raises OSError.
        for descriptor in self.pinned_descriptors.values():
            try:
                os.close(descriptor)
            except OSError:
                pass
        self.pinned_descriptors.clear()
        for guard in ([self.directory] if self.directory is not None else []) + list(reversed(self.guards)):
            try:
                guard.close()
            except OSError:
                pass


def _sealed_payload_bytes(result: VerifiedDiagnosticsResult, original: bytes) -> bytes:
    if type(result) is not VerifiedDiagnosticsResult:
        _fail("diagnostics publishing requires a freshly replayed VerifiedDiagnosticsResult")
    payload = _canonical_json(dict(result))
    if payload != original:
        _fail("sealed diagnostics payload differs from the original draft")
    return payload


def _render_verified_summary(result: VerifiedDiagnosticsResult, context: Mapping[str, Any], repository: Path) -> bytes:
    """Load only the freshly audited renderer source, without stale module/pyc caches."""
    path = _safe_repo_path(repository, "tools/evaluator/render_anomaly_failure_diagnostics.py", "diagnostics renderer", must_exist=True)
    raw = path.read_bytes()
    if _sha256_bytes(raw) != context["revision_compatibility"]["current_d2_diagnostics"]["renderer_raw_sha256"]:
        _fail("diagnostics renderer changed after replay")
    namespace = {"__name__": "_fixed_diagnostics_renderer", "__file__": str(path)}
    exec(compile(raw, str(path), "exec"), namespace)
    return namespace["render_summary"](result)


def run_and_publish_diagnostics(root: Path, *, replay_head: str) -> dict[str, str]:
    """Windows-only D2-B API: fresh replay then atomic directory publication.

    No result, schema, output, renderer, or callback can be supplied. A previously
    issued result is never a publication input. The return value is a receipt,
    not a replacement for VerifiedDiagnosticsResult or evidence for promotion.
    """
    _require_windows_publication()  # Before replay, path inspection or any claim.
    if not _is_digest(replay_head, 40):
        _fail("--run requires a full lowercase 40-character replay HEAD")
    repository = _repository(root)
    target = _safe_repo_path(repository, EXPECTED_OUTPUT_ROOT, "diagnostics output", must_exist=False)
    if os.path.lexists(target):
        _fail("diagnostics output already exists; overwrite/recovery is disabled")
    parent = _safe_repo_path(repository, "artifacts", "diagnostics staging parent", must_exist=True)
    with os.scandir(parent) as entries:
        if any(entry.name.startswith(_STAGING_PREFIX) for entry in entries):
            _fail("diagnostics staging residue already exists; manual inspection required; recovery is disabled")
    claim = _DiagnosticsOutputClaim(repository)
    try:
        rename_output = _prepare_publication_rename()
        result, context, original = _replay_and_build_with_context(repository, replay_head=replay_head)
        payload = _sealed_payload_bytes(result, original)
        summary = _render_verified_summary(result, context, repository)
        if not isinstance(summary, bytes) or b"\r" in summary or not summary.endswith(b"\n"):
            _fail("diagnostics renderer did not return deterministic UTF-8/LF bytes")
        summary.decode("utf-8", errors="strict")
        marker = {"schema_version": SCHEMA_VERSION, "marker_type": DIAGNOSTICS_COMPLETION_MARKER_TYPE,
                  "result_sha256": _sha256_bytes(payload), "summary_sha256": _sha256_bytes(summary)}
        marker_raw = _canonical_json(marker)
        receipt = {"status": "published", "output_path": str(target), "result_sha256": marker["result_sha256"],
                   "summary_sha256": marker["summary_sha256"], "completion_marker_sha256": _sha256_bytes(marker_raw)}
        staged = {"result.json": payload, "summary.md": summary, _STAGED_MARKER: marker_raw}
        claim.claim()
        for name, raw in staged.items():
            claim.write_exclusive(name, raw)
        claim.verify_files(staged)
        claim.prepare_publication_commit()
        _recheck_verified_replay_boundary(context, repository)
        _sealed_payload_bytes(result, original)
        claim.verify_files(staged)
        observed, _, _ = _strict_bytes(claim.read_owned(_STAGED_MARKER), "diagnostics completion marker")
        if observed != marker:
            _fail("diagnostics completion marker differs from the fixed contract")
        claim.release_child_handles()
        claim.install_output(rename_output)
        return receipt
    except BaseException as exc:
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        if claim.claimed:
            raise AnomalyFailureDiagnosticsError(f"diagnostics publish failed; staging retained for inspection: {claim.path.name}; no automatic cleanup/recovery") from exc
        if isinstance(exc, AnomalyFailureDiagnosticsError):
            raise
        raise AnomalyFailureDiagnosticsError("diagnostics publish failed before output claim; any competing output is untouched") from exc
    finally:
        claim.close()


def _verify_input_replay(root: Path | None = None, *, replay_head: str) -> dict[str, Any]:
    """Run the existing strict, read-only matrix replay route and return verified in-memory inputs.

    This is deliberately an API-only D2-A seam. It never invokes a CLI, publishes output,
    or creates a directory.
    """
    repository = _repository(root)
    diagnostics_config, diagnostics_config_source, diagnostics_schema_source, diagnostics_result_schema_source = _load_config(CONFIG_PATH, repository)
    _validate_semantics(diagnostics_config, repository)
    _expected_input_provenance()
    if diagnostics_config.get("input_root") != EXPECTED_INPUT_ROOT or diagnostics_config.get("matrix_config_path") != EXPECTED_MATRIX_CONFIG_PATH:
        _fail("diagnostics config input_root or matrix_config_path is not the fixed replay profile")
    compatibility = _validate_revision_compatibility(repository, replay_head=replay_head)
    from . import anomaly_matrix_analysis as analysis
    from . import anomaly_matrix_runner as runner

    analysis_config, analysis_source, analysis_schema_source = analysis._load_analysis_inputs(analysis.ANALYSIS_CONFIG_PATH, repository)
    for field in ("input_root", "matrix_config_path"):
        if analysis_config.get(field) != diagnostics_config[field]:
            _fail(f"analysis and diagnostics configs differ: {field}")
    matrix_config_path = anomaly_matrix._safe_repo_path(repository, analysis_config["matrix_config_path"], "matrix config", must_exist=True)
    sources, values = runner._snapshot_inputs(repository, matrix_config_path)
    replay_revision = compatibility["replay_revision"]
    artifact_revision = compatibility["artifact_revision"]
    input_root = anomaly_matrix._safe_repo_path(repository, analysis_config["input_root"], "input_root", must_exist=True)
    captured_input = _capture_tree_bytes(input_root, "matrix artifact before diagnostics")
    before = {"inventory": captured_input["inventory"], "hashes": captured_input["hashes"]}
    if not {"result.json", "summary.md", ".complete"}.issubset(captured_input["bytes"]):
        _fail("matrix aggregate summary or completion marker is missing")
    result, result_sha, _ = _strict_bytes(captured_input["bytes"]["result.json"], "matrix aggregate result")
    summary_raw = captured_input["bytes"]["summary.md"]
    marker, marker_sha, _ = _strict_bytes(captured_input["bytes"][".complete"], "matrix completion marker")
    expected_input = analysis_config.get("expected_input_artifact", EXPECTED_INPUT_ARTIFACT)
    observed_inventory_sha = _sha256_bytes(_canonical_json(before))
    if expected_input != EXPECTED_INPUT_ARTIFACT:
        _fail("analysis input artifact contract is not fixed")
    observed_input_initial = {"result_sha256": result_sha, "summary_sha256": _sha256_bytes(summary_raw), "completion_marker_sha256": marker_sha, "inventory_sha256": observed_inventory_sha}
    for field, value in observed_input_initial.items():
        if value != EXPECTED_INPUT_ARTIFACT[field]:
            _fail(f"matrix input artifact digest does not match the preregistered pin: {field}")
    if marker != {"result_sha256": result_sha, "summary_sha256": _sha256_bytes(summary_raw), "marker_type": runner.COMPLETION_MARKER_TYPE, "schema_version": runner.SCHEMA_VERSION}:
        _fail("matrix completion marker does not match captured input artifacts")
    if summary_raw != runner._matrix_summary(result):
        _fail("matrix summary is not deterministic")
    try:
        validate(result, values["matrix_result_schema"])
    except ManifestValidationError as exc:
        raise AnomalyFailureDiagnosticsError(f"matrix result does not satisfy its schema: {exc}") from exc
    analysis._verify_source_provenance(result, {key: value for key, value in sources.items() if not key.startswith("_")}, artifact_revision)
    runner._verify_aggregate_result(result, values["matrix_config"])
    base = values["base_generator_config"]
    evaluations: list[dict[str, Any]] = []
    expected_files = {"result.json", "summary.md", ".complete"}
    expected_dirs = {"configs", "configs/generator", "configs/evaluator", "datasets", "evaluations"}
    for cell in result.get("cells", []):
        if cell.get("status") != "success":
            _fail("diagnostics replay requires every matrix cell to be successful")
        evaluation, expected, cell_files, cell_dirs = analysis._verify_cell_and_collect(cell, values["matrix_config"], base, repository, input_root, sources, values, artifact_revision)
        generator_relative = expected["paths"]["generator_config"].relative_to(input_root).as_posix()
        evaluator_relative = expected["paths"]["evaluator_config"].relative_to(input_root).as_posix()
        evaluation_relative = f"{expected['paths']['evaluation'].relative_to(input_root).as_posix()}/result.json"
        for relative in (generator_relative, evaluator_relative, evaluation_relative):
            if relative not in captured_input["bytes"]:
                _fail(f"captured input tree is missing verified JSON: {relative}")
        captured_generator, _, _ = _strict_bytes(captured_input["bytes"][generator_relative], f"captured {generator_relative}")
        captured_evaluator, _, _ = _strict_bytes(captured_input["bytes"][evaluator_relative], f"captured {evaluator_relative}")
        captured_evaluation, _, _ = _strict_bytes(captured_input["bytes"][evaluation_relative], f"captured {evaluation_relative}")
        if (captured_input["bytes"][generator_relative] != analysis._json_bytes(expected["generator_config"])
                or captured_input["bytes"][evaluator_relative] != analysis._json_bytes(expected["evaluator_config"])
                or _canonical_json(captured_evaluation) != _canonical_json(evaluation)):
            _fail(f"disk replay helper payload differs from the captured input bytes: {cell['cell_id']}")
        for relative in cell_files:
            if relative not in captured_input["bytes"]:
                _fail(f"captured input tree is missing verified cell artifact: {relative}")
        expected_files.update(cell_files)
        expected_dirs.update(cell_dirs)
        captured_expected = deepcopy(expected)
        captured_expected["generator_config"] = captured_generator
        captured_expected["evaluator_config"] = captured_evaluator
        evaluations.append({"cell": deepcopy(cell), "evaluation": captured_evaluation, "expected": captured_expected})
    if len(evaluations) != EXPECTED_COUNTS["cells"]:
        _fail("verified matrix cell count is not 120")
    actual_files = {name for name, kind in before["inventory"] if kind == "file"}
    actual_dirs = {name for name, kind in before["inventory"] if kind == "directory"}
    if actual_files != expected_files or actual_dirs != expected_dirs:
        _fail("matrix artifact inventory does not exactly match the verified cell plan")
    after = runner._tree_snapshot(input_root, "matrix artifact after diagnostics", containment_root=repository, failure_scope="global")
    if before != after:
        _fail("matrix artifact changed during diagnostics replay")
    runner._assert_inputs_unchanged(repository, sources, values, "diagnostics replay")
    for captured, relative, label in ((diagnostics_config_source, CONFIG_PATH, "diagnostics config"), (diagnostics_schema_source, SCHEMA_PATH, "diagnostics config schema"), (diagnostics_result_schema_source, RESULT_SCHEMA_PATH, "diagnostics result schema"), (analysis_source, analysis_source["path"], "analysis config"), (analysis_schema_source, analysis_schema_source["path"], "analysis config schema")):
        current, raw, raw_sha, canonical_sha = _strict_object(repository / relative, f"{label} final read")
        if current != captured.get("value", diagnostics_config if relative == CONFIG_PATH else None) and relative == CONFIG_PATH:
            _fail(f"{label} changed during replay")
        if raw != captured["raw"] or raw_sha != captured["raw_sha256"] or canonical_sha != captured["canonical_sha256"]:
            _fail(f"{label} bytes or digest changed during replay")
    final_compatibility = _validate_revision_compatibility(repository, replay_head=replay_revision["head"])
    if final_compatibility != compatibility:
        _fail("revision compatibility changed during diagnostics replay")
    observed_input = {"path": analysis_config["input_root"], "result_sha256": result_sha, "summary_sha256": _sha256_bytes(summary_raw), "completion_marker_sha256": marker_sha, "inventory_sha256": _sha256_bytes(_canonical_json(before))}
    return {"diagnostics_config": diagnostics_config, "diagnostics_config_source": diagnostics_config_source, "diagnostics_schema_source": diagnostics_schema_source, "diagnostics_result_schema_source": diagnostics_result_schema_source, "analysis_config": analysis_config, "analysis_source": analysis_source, "analysis_schema_source": analysis_schema_source, "sources": sources, "values": values, "matrix_result": result, "evaluations": evaluations, "input_capture": captured_input, "input_artifact": observed_input, "input_snapshot": {"before_inventory_sha256": observed_input["inventory_sha256"], "after_inventory_sha256": _sha256_bytes(_canonical_json(after)), "equal": before == after}, "revision_compatibility": compatibility, "replay_revision": replay_revision}


def _recheck_verified_replay_boundary(verified: Mapping[str, Any], repository: Path) -> None:
    from . import anomaly_matrix_runner as runner
    input_root = anomaly_matrix._safe_repo_path(repository, verified["input_artifact"]["path"], "final input_root", must_exist=True)
    final_capture = _capture_tree_bytes(input_root, "matrix artifact final diagnostics recheck")
    initial_capture = verified["input_capture"]
    if final_capture != initial_capture:
        raise AnomalyFailureDiagnosticsError("captured matrix artifact changed after result construction")
    runner._assert_inputs_unchanged(repository, verified["sources"], verified["values"], "final diagnostics recheck")
    for source, label in ((verified["diagnostics_config_source"], "diagnostics config"), (verified["diagnostics_schema_source"], "diagnostics config schema"), (verified["diagnostics_result_schema_source"], "diagnostics result schema"), (verified["analysis_source"], "analysis config"), (verified["analysis_schema_source"], "analysis config schema")):
        current, raw, raw_sha, canonical_sha = _strict_object(repository / source["path"], f"{label} final result recheck")
        if raw != source["raw"] or raw_sha != source["raw_sha256"] or canonical_sha != source["canonical_sha256"]:
            raise AnomalyFailureDiagnosticsError(f"{label} changed after result construction")
    final_compatibility = _validate_revision_compatibility(repository, replay_head=verified["replay_revision"]["head"])
    if final_compatibility != verified["revision_compatibility"]:
        raise AnomalyFailureDiagnosticsError("revision compatibility changed after result construction")


def _build_provenance_from_verified_replay(verified: Mapping[str, Any], repository: Path | None = None) -> dict[str, Any]:
    """Create the result provenance block from a completed read-only replay audit."""
    compatibility = verified["revision_compatibility"]
    def source(item: Mapping[str, Any]) -> dict[str, str]:
        return {"path": item["path"], "sha256": item["raw_sha256"]}
    current_d2 = compatibility["current_d2_diagnostics"]
    return {
        "canonicalization": CANONICALIZATION_ID,
        "artifact_code_revision": compatibility["artifact_revision"],
        "replay_code_revision": compatibility["replay_revision"],
        "input_artifact": verified["input_artifact"],
        "input_snapshot": verified["input_snapshot"],
        "revision_compatibility": {"policy": compatibility["policy"], "artifact_revision": compatibility["artifact_revision"], "semantic_sources": compatibility["semantic_sources"], "current_only_paths": compatibility["current_only_paths"], "current_d2_diagnostics": current_d2},
        "config": source(verified["diagnostics_config_source"]),
        "config_schema": source(verified["diagnostics_schema_source"]),
        "result_schema": source(verified["diagnostics_result_schema_source"]),
    }


def _build_ledgers_from_verified_replay(verified: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Materialize D2 ledgers from evaluations already checked by the formal replay helpers."""
    ledgers = {"incident_windows": [], "incident_points": [], "clean_source_alerts": [], "clean_equipment_alerts": [], "availability": [], "calibration_profiles": []}
    for item in verified.get("evaluations", []):
        cell, evaluation, expected = item["cell"], item["evaluation"], item["expected"]
        cell_id, seed, layout_id, layout_index = cell["cell_id"], cell["seed"], cell["layout_id"], cell["layout_index"]
        scores = [row for row in evaluation.get("scores", []) if isinstance(row, Mapping)]
        profiles = [row for row in evaluation.get("profiles", []) if isinstance(row, Mapping)]
        incidents = [row for row in evaluation.get("incidents", []) if isinstance(row, Mapping) and row.get("eligible") is True]
        for incident in incidents:
            identity = {"cell_id": cell_id, "seed": seed, "layout_id": layout_id, "layout_index": layout_index, "event_id": incident["event_id"], "event_class": incident["event_class"], "event_type": incident["event_type"], "equipment_id": incident["equipment_id"], "signal_id": incident["signal_id"]}
            mode = next((layout.get("operating_mode") for layout in verified["values"]["matrix_config"]["layouts"] if layout.get("layout_id") == layout_id), None)
            if mode is None:
                _fail(f"matrix layout has no operating mode: {layout_id}")
            identity["operating_mode"] = mode
            window = {**identity, "event_start_timestamp": incident["event_start_timestamp"], "event_end_timestamp": incident["event_end_timestamp"], "detection_window_start": incident["detection_window_start"], "detection_window_end": incident["detection_window_end"], "detected": incident["detected"], "matched_alert_episode_id": incident["matched_alert_episode_id"], "alert_onset_timestamp": incident["alert_onset_timestamp"], "detection_delay_seconds": incident["detection_delay_seconds"], "max_in_window_consecutive_exceedances": 0, "pre_event_support": False, "event_causal_support_qualified": False}
            interval_ms = expected["generator_config"].get("sampling_interval_ms")
            if isinstance(interval_ms, bool) or not isinstance(interval_ms, int) or interval_ms != MATRIX_SAMPLING_INTERVAL_MS:
                _fail("generator sampling interval is invalid for incident replay")
            event_start = _utc_timestamp(incident["event_start_timestamp"], "incident event start")
            candidate_scores = [row for row in scores if row.get("equipment_id") == incident.get("equipment_id") and row.get("signal_id") == incident.get("signal_id") and row.get("operating_mode") == mode]
            selected: list[Mapping[str, Any]] = []
            for offset in (-1, 0, 1, 2, 3, 4, 5):
                expected_timestamp = event_start + timedelta(milliseconds=interval_ms * offset)
                matches = [row for row in candidate_scores if _utc_timestamp(row.get("timestamp"), "incident score timestamp") == expected_timestamp]
                if len(matches) != 1:
                    _fail(f"incident score replay did not provide one exact point at offset {offset}: {cell_id}/{incident['event_id']}")
                selected.append(matches[0])
            expected_profile = {"equipment_id": incident["equipment_id"], "signal_id": incident["signal_id"], "operating_mode": mode}
            if any(row.get("profile_key") != expected_profile for row in selected):
                _fail(f"incident score replay has a noncanonical profile: {cell_id}/{incident['event_id']}")
            for offset, score in zip((-1, 0, 1, 2, 3, 4, 5), selected):
                ledgers["incident_points"].append({**identity, "offset": offset, "timestamp": score["timestamp"], "quality_status": score["quality_status"], "actual": score.get("actual"), "previous_actual": score.get("previous_actual"), "residual": score.get("residual"), "available": score["available"], "exclusion_reason": score.get("exclusion_reason"), "score": score.get("score"), "exceeds_threshold": score["exceeds_threshold"], "persistence_streak": score["persistence_streak"], "alert_episode_id": score.get("alert_episode_id")})
            window["max_in_window_consecutive_exceedances"] = max((len(run) for run in _contiguous_true_runs([point["available"] is True and point["exceeds_threshold"] is True for point in ledgers["incident_points"][-6:]])), default=0)
            window["pre_event_support"] = ledgers["incident_points"][-7]["available"] is True and ledgers["incident_points"][-7]["exceeds_threshold"] is True
            if window["detected"] is False:
                if any(window.get(field) is not None for field in ("matched_alert_episode_id", "alert_onset_timestamp", "detection_delay_seconds")):
                    _fail(f"undetected incident has canonical detection metadata: {cell_id}/{incident['event_id']}")
                window["event_causal_support_qualified"] = False
            else:
                matched_indices = [index for index, score in enumerate(selected) if score.get("alert_episode_id") == window["matched_alert_episode_id"]]
                if not matched_indices or window["alert_onset_timestamp"] != selected[matched_indices[0]].get("timestamp"):
                    _fail(f"detected incident onset is not the canonical first matched score: {cell_id}/{incident['event_id']}")
                expected_delay = (_utc_timestamp(window["alert_onset_timestamp"], "alert onset") - event_start).total_seconds()
                if window["detection_delay_seconds"] != expected_delay:
                    _fail(f"detected incident delay is not canonical: {cell_id}/{incident['event_id']}")
                onset_index = matched_indices[0]
                onset_offset = onset_index - 1
                support = selected[onset_index - (MATRIX_PERSISTENCE_POINTS - 1):onset_index + 1] if onset_offset >= MATRIX_PERSISTENCE_POINTS - 1 else []
                window["event_causal_support_qualified"] = len(support) == MATRIX_PERSISTENCE_POINTS and all(score.get("available") is True and score.get("exceeds_threshold") is True for score in support)
            ledgers["incident_windows"].append(window)
        for profile in profiles:
            profile_key = profile.get("profile_key", {})
            signal_id, mode = profile_key.get("signal_id"), profile_key.get("operating_mode")
            equipment_id = profile_key.get("equipment_id")
            excluded = profile.get("excluded_counts", {})
            ledgers["calibration_profiles"].append({"cell_id": cell_id, "seed": seed, "layout_id": layout_id, "layout_index": layout_index, "equipment_id": equipment_id, "signal_id": signal_id, "operating_mode": mode, "calibration_point_count": profile.get("calibration_point_count"), "center": profile.get("center"), "mad": profile.get("mad"), "scale": profile.get("scale"), "status": profile.get("status"), "excluded_counts": {key: excluded.get(key, 0) for key in _CALIBRATION_EXCLUSION_KEYS}, "reason": profile.get("reason")})
        clean_entries = [episode for episode in evaluation.get("clean_false_alert_episodes", []) if isinstance(episode, Mapping)]
        accounting = {row.get("episode_id"): row for row in evaluation.get("alert_episode_accounting", []) if isinstance(row, Mapping)}
        alert_by_id = {row.get("episode_id"): row for row in evaluation.get("alert_episodes", []) if isinstance(row, Mapping)}
        if len(accounting) != len(evaluation.get("alert_episode_accounting", [])) or len(alert_by_id) != len(evaluation.get("alert_episodes", [])):
            _fail(f"duplicate or malformed source alert/accounting rows for {cell_id}")
        joined_clean_ids: set[str] = set()
        if any("source_alert_episode_ids" not in episode or "equipment_episode_id" not in episode for episode in clean_entries):
            _fail(f"clean_false_alert_episodes must use the canonical equipment episode shape for {cell_id}")
        for equipment_episode in clean_entries:
            equipment_id = equipment_episode.get("equipment_id")
            source_ids = equipment_episode.get("source_alert_episode_ids")
            equipment_episode_id = equipment_episode.get("equipment_episode_id")
            if not isinstance(equipment_id, str) or not isinstance(equipment_episode_id, str) or not isinstance(source_ids, list) or not source_ids or len(set(source_ids)) != len(source_ids):
                _fail(f"clean equipment episode identity is invalid for {cell_id}")
            for source_id in source_ids:
                if source_id in joined_clean_ids:
                    _fail(f"clean source alert is joined more than once for {cell_id}/{source_id}")
                joined_clean_ids.add(source_id)
                source = alert_by_id.get(source_id)
                account = accounting.get(source_id)
                if not isinstance(source, Mapping) or not isinstance(account, Mapping) or account.get("partition") != "clean_false_alert":
                    _fail(f"clean equipment/source/accounting join is not exact for {cell_id}/{source_id}")
                profile_key = source.get("profile_key", {})
                mode = profile_key.get("operating_mode")
                if source.get("equipment_id") != equipment_id or profile_key != {"equipment_id": equipment_id, "signal_id": source.get("signal_id"), "operating_mode": mode}:
                    _fail(f"clean source equipment/profile differs from its join for {cell_id}/{source_id}")
                onset = source.get("onset_timestamp", source.get("start_timestamp"))
                ledgers["clean_source_alerts"].append({"cell_id": cell_id, "seed": seed, "layout_id": layout_id, "layout_index": layout_index, "source_alert_episode_id": source_id, "equipment_id": source["equipment_id"], "signal_id": source["signal_id"], "operating_mode": mode, "onset_timestamp": onset, "end_timestamp": source["end_timestamp"], "point_count": source["point_count"], "max_score": source["max_score"], "mode_entry_offset": _mode_entry_offset(onset, mode, expected["generator_config"]), "equipment_episode_id": equipment_episode_id})
            if equipment_episode.get("merge_size") not in (None, len(source_ids)) or _utc_timestamp(equipment_episode.get("start_timestamp"), "clean equipment start") > _utc_timestamp(equipment_episode.get("end_timestamp"), "clean equipment end"):
                _fail(f"clean equipment episode bounds or merge_size are invalid for {cell_id}/{equipment_episode_id}")
            ledgers["clean_equipment_alerts"].append({"cell_id": cell_id, "seed": seed, "layout_id": layout_id, "layout_index": layout_index, "equipment_episode_id": equipment_episode_id, "equipment_id": equipment_id, "start_timestamp": equipment_episode["start_timestamp"], "end_timestamp": equipment_episode["end_timestamp"], "source_alert_episode_ids": list(source_ids), "merge_size": len(source_ids)})
        if joined_clean_ids != {episode_id for episode_id, account in accounting.items() if account.get("partition") == "clean_false_alert"}:
            _fail(f"clean source/accounting membership is not exact for {cell_id}")
        for signal_id in CANONICAL_SIGNAL_IDS:
            for mode in CANONICAL_OPERATING_MODES:
                group = [row for row in scores if row.get("signal_id") == signal_id and row.get("operating_mode") == mode]
                exclusion_counts = {key: sum(row.get("exclusion_reason") == key for row in group) for key in _EXCLUSION_KEYS}
                ledgers["availability"].append({"cell_id": cell_id, "seed": seed, "layout_id": layout_id, "layout_index": layout_index, "equipment_id": signal_id.split(".", 1)[0], "signal_id": signal_id, "operating_mode": mode, "available_points": sum(row.get("available") is True for row in group), "total_points": len(group), "exclusion_counts": exclusion_counts})
    return ledgers


def _contiguous_true_runs(values: Iterable[bool]) -> list[list[bool]]:
    runs: list[list[bool]] = []
    current: list[bool] = []
    for value in values:
        if value:
            current.append(True)
        elif current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    return runs


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


def _strict_bytes(raw: bytes, label: str) -> tuple[dict[str, Any], str, str]:
    def reject_duplicate(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate JSON property: {key}")
            value[key] = item
        return value
    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON constant: {value}")
    def parse_float(value: str) -> float:
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError(f"non-finite JSON number: {value}")
        return parsed
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicate, parse_constant=reject_constant, parse_float=parse_float)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise AnomalyFailureDiagnosticsError(f"{label} is not strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        _fail(f"{label} must be a JSON object")
    return value, _sha256_bytes(raw), _sha256_bytes(_canonical_json(value))


def _capture_tree_bytes(path: Path, label: str) -> dict[str, Any]:
    if _is_reparse_point(path) or not path.is_dir():
        _fail(f"{label} must be a regular directory")
    inventory: list[tuple[str, str]] = []
    hashes: dict[str, str] = {}
    captured: dict[str, bytes] = {}
    pending = [path]
    try:
        while pending:
            directory = pending.pop()
            with os.scandir(directory) as entries:
                for entry in entries:
                    candidate = Path(entry.path)
                    relative = candidate.relative_to(path).as_posix()
                    if _is_reparse_point(candidate):
                        raise OSError(f"reparse point: {relative}")
                    if entry.is_dir(follow_symlinks=False):
                        inventory.append((relative, "directory"))
                        pending.append(candidate)
                    elif entry.is_file(follow_symlinks=False):
                        raw = candidate.read_bytes()
                        inventory.append((relative, "file"))
                        hashes[relative] = _sha256_bytes(raw)
                        captured[relative] = raw
                    else:
                        raise OSError(f"non-regular entry: {relative}")
    except (OSError, ValueError) as exc:
        raise AnomalyFailureDiagnosticsError(f"{label} could not be captured as one regular byte tree") from exc
    return {"inventory": tuple(sorted(inventory)), "hashes": dict(sorted(hashes.items())), "bytes": captured}


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
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--validate-only", action="store_true")
    modes.add_argument("--run", action="store_true")
    parser.add_argument("--replay-head")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)
    if not args.validate_only and not args.run:
        print("FAIL: choose explicitly --validate-only or --run")
        return 2
    if args.validate_only and args.replay_head is not None:
        print("FAIL: --replay-head is only valid with --run")
        return 2
    if args.run and (not _is_digest(args.replay_head, 40) or args.config != CONFIG_PATH):
        print("FAIL: --run requires the fixed config and a full lowercase 40-character --replay-head")
        return 2
    try:
        if args.run:
            _require_windows_publication()
        root = Path(args.root).absolute() if args.root else None
        if args.validate_only:
            summary = validate_diagnostics_config(args.config, root)
            print(_text_summary(summary), end="")
        else:
            receipt = run_and_publish_diagnostics(_repository(root), replay_head=args.replay_head)
            print(f"published: {receipt['output_path']}")
            for field in ("result_sha256", "summary_sha256", "completion_marker_sha256"):
                print(f"{field}: {receipt[field]}")
    except (AnomalyFailureDiagnosticsError, ManifestValidationError, OSError, KeyError, ValueError) as exc:
        print(f"FAIL: {str(exc).splitlines()[0][:200] if str(exc) else 'diagnostics failed'}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
