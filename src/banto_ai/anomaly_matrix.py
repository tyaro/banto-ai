"""Savepoint A: validate the preregistered anomaly multi-seed matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path, PureWindowsPath
from typing import Any, Mapping

from .manifest import ManifestValidationError, validate


MATRIX_SCHEMA_VERSION = "0.1"
MATRIX_CONFIG_TYPE = "event-aware-anomaly-matrix"
MATRIX_ID = "anomaly-multiseed-v01"
EXPECTED_SEEDS = (11, 17, 23, 29, 37, 42, 53, 67, 79, 97)
EXPECTED_MODES = ("stopped", "startup", "low_speed", "nominal", "high_load", "cooldown")
EXPECTED_EQUIPMENT = ("motor-01", "conveyor-01")
EXPECTED_EQUIPMENT_TYPES = {"motor-01": "motor", "conveyor-01": "conveyor"}
EXPECTED_TARGETS = ("motor_current", "motor_temperature", "conveyor_speed", "vibration_feature")
EXPECTED_CLASSES = ("machine_fault", "sensor_fault", "data_quality", "ignored")
EXPECTED_SLOT_OFFSETS = (2, 9, 16, 23)
EXPECTED_TEST_SPLIT = (720, 900)
EXPECTED_MODE_WINDOW = 30
EXPECTED_EVENT_DURATION = 3
EXPECTED_GRACE_POINTS = 3
EXPECTED_BOOTSTRAP = {"seed": 20260905, "resamples": 10000, "confidence_level": 0.95}
EXPECTED_OUTPUT_ROOT = "artifacts/anomaly-multiseed-v01"
EXPECTED_BASE_CONFIG = "examples/configs/synthetic-anomaly-evaluation-v0.1.json"
EXPECTED_SCHEMA_PATH = "schemas/anomaly-multiseed-matrix-config.schema.json"
EXPECTED_BASE_SHA256 = "ab13ce9cc64c6d8892dde2d64c79097266b0e68e64cc659e3fdd7bd06afa9bff"
EXPECTED_SCHEMA_SHA256 = "50dd3a5704192bc303fdab9d0334de8d0f0835d9b960ea499d9f78cb995a6b4f"


class AnomalyMatrixError(ValueError):
    """matrix configuration or repository safety contract violation."""


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AnomalyMatrixError(f"duplicate JSON property: {key}")
        result[key] = value
    return result


def _load_object_snapshot(path: Path, label: str) -> tuple[dict[str, Any], bytes, str]:
    try:
        if _is_link(path) or not path.is_file():
            raise OSError(f"not a regular file: {path}")
        raw = path.read_bytes()

        def reject_constant(value: str) -> None:
            raise AnomalyMatrixError(f"{label} contains a non-finite JSON constant: {value}")

        def parse_float(value: str) -> float:
            parsed = float(value)
            if not math.isfinite(parsed):
                raise AnomalyMatrixError(f"{label} contains a non-finite JSON number: {value}")
            return parsed

        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=reject_constant,
            parse_float=parse_float,
        )
    except AnomalyMatrixError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise AnomalyMatrixError(f"{label} is not strict UTF-8 JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise AnomalyMatrixError(f"{label} must be a JSON object")
    return value, raw, hashlib.sha256(raw).hexdigest()


def _is_link(path: Path) -> bool:
    junction_check = getattr(os.path, "isjunction", None)
    return path.is_symlink() or bool(junction_check(path) if junction_check is not None else False)


def _safe_relative(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or value.startswith("/") or "\\" in value or PureWindowsPath(value).drive:
        raise AnomalyMatrixError(f"{label} must be a repository-relative POSIX path")
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise AnomalyMatrixError(f"{label} must not contain empty, dot, or traversal segments")
    return value


def _safe_repo_path(root: Path, value: Any, label: str, *, must_exist: bool) -> Path:
    relative = _safe_relative(value, label)
    root = root.absolute()
    if _is_link(root) or not root.is_dir():
        raise AnomalyMatrixError(f"repository root is not a regular directory: {root}")
    cursor = root
    for part in relative.split("/"):
        cursor = cursor / part
        if _is_link(cursor):
            raise AnomalyMatrixError(f"{label} cannot traverse a symlink or junction")
    resolved = (root / relative).resolve()
    if resolved == root or root not in resolved.parents:
        raise AnomalyMatrixError(f"{label} must remain inside the repository")
    if must_exist and not resolved.exists():
        raise AnomalyMatrixError(f"{label} does not exist: {relative}")
    return resolved


def _resolve_config_path(config_path: str | Path, root: Path) -> Path:
    candidate = Path(config_path)
    if candidate.is_absolute():
        try:
            relative = candidate.absolute().relative_to(root.absolute()).as_posix()
        except ValueError as exc:
            raise AnomalyMatrixError("config must be a repository-local regular file") from exc
    else:
        relative = candidate.as_posix()
    path = _safe_repo_path(root, relative, "config_path", must_exist=True)
    if _is_link(path) or not path.is_file():
        raise AnomalyMatrixError("config must be a repository-local regular file")
    return path


def _require_exact(value: Any, expected: Any, label: str) -> None:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and isinstance(expected, (int, float)) and not isinstance(expected, bool):
        if value == expected:
            return
    if value != expected or type(value) is not type(expected):
        raise AnomalyMatrixError(f"{label} is not fixed to {expected!r}")


def _validate_base_generator(base: Mapping[str, Any], root: Path) -> list[dict[str, Any]]:
    schema_path = _safe_repo_path(root, "schemas/synthetic-generator-config.schema.json", "base generator schema", must_exist=True)
    schema, _raw, _sha = _load_object_snapshot(schema_path, "base generator schema")
    try:
        validate(dict(base), schema)
    except ManifestValidationError as exc:
        raise AnomalyMatrixError(f"base generator config does not satisfy its schema: {exc}") from exc
    _require_exact(base.get("config_type"), "synthetic-generator", "base config_type")
    _require_exact(base.get("sample_count"), 900, "base sample_count")
    _require_exact(base.get("sampling_interval_ms"), 1000, "base sampling_interval_ms")
    equipment = base.get("equipment")
    if not isinstance(equipment, list) or [(item.get("equipment_id"), item.get("equipment_type")) for item in equipment] != [(item, EXPECTED_EQUIPMENT_TYPES[item]) for item in EXPECTED_EQUIPMENT]:
        raise AnomalyMatrixError("base equipment mapping drifted")
    regimes = base.get("regimes")
    if not isinstance(regimes, list):
        raise AnomalyMatrixError("base regimes must be an array")
    ordered = sorted(regimes, key=lambda item: item.get("start_sample", -1))
    if len(ordered) != len(regimes) or any(
        not isinstance(item.get("start_sample"), int)
        or not isinstance(item.get("end_sample"), int)
        or item["end_sample"] != next_item["start_sample"]
        for item, next_item in zip(ordered, ordered[1:])
    ):
        raise AnomalyMatrixError("base regimes must be contiguous and ordered")
    if not ordered or ordered[0].get("start_sample") != 0 or ordered[-1].get("end_sample") != 900:
        raise AnomalyMatrixError("base regimes must cover sample_count exactly")
    test_regimes = [item for item in ordered if item.get("start_sample", -1) >= EXPECTED_TEST_SPLIT[0]]
    expected = [
        {"regime": mode, "start_sample": 720 + index * 30, "end_sample": 750 + index * 30}
        for index, mode in enumerate(EXPECTED_MODES)
    ]
    if [(item.get("regime"), item.get("start_sample"), item.get("end_sample")) for item in test_regimes] != [
        (item["regime"], item["start_sample"], item["end_sample"]) for item in expected
    ]:
        raise AnomalyMatrixError("base test mode boundaries drifted from the 60/20/20 contract")
    if test_regimes[-1]["end_sample"] != EXPECTED_TEST_SPLIT[1]:
        raise AnomalyMatrixError("base test split must be [720,900)")
    return test_regimes


def _expected_event(layout: Mapping[str, Any], event_class: str, equipment_type: str) -> tuple[str, str, float]:
    if event_class == "machine_fault":
        return "jam_or_slip", "motor_current" if equipment_type == "motor" else "conveyor_speed", 0.55
    if event_class == "sensor_fault":
        return "spike", "motor_temperature", 8.0
    if event_class == "data_quality":
        return "dropout", "motor_temperature", 0.0
    if event_class == "ignored":
        return "stuck_value", "load_proxy", 0.0
    raise AnomalyMatrixError(f"unsupported event class: {event_class}")


def _validate_semantics(config: Mapping[str, Any], base: Mapping[str, Any], test_regimes: list[dict[str, Any]]) -> dict[str, Any]:
    _require_exact(config.get("schema_version"), MATRIX_SCHEMA_VERSION, "schema_version")
    _require_exact(config.get("config_type"), MATRIX_CONFIG_TYPE, "config_type")
    _require_exact(config.get("matrix_id"), MATRIX_ID, "matrix_id")
    _require_exact(config.get("base_generator_config_path"), EXPECTED_BASE_CONFIG, "base_generator_config_path")
    _require_exact(config.get("schema_path"), EXPECTED_SCHEMA_PATH, "schema_path")
    _require_exact(config.get("base_generator_config_sha256"), EXPECTED_BASE_SHA256, "base_generator_config_sha256")
    _require_exact(config.get("schema_sha256"), EXPECTED_SCHEMA_SHA256, "schema_sha256")
    _require_exact(config.get("seeds"), list(EXPECTED_SEEDS), "seeds")
    _require_exact(config.get("test_split"), {"start_sample": 720, "end_sample": 900}, "test_split")
    _require_exact(config.get("mode_window_samples"), EXPECTED_MODE_WINDOW, "mode_window_samples")
    _require_exact(config.get("slot_offsets_samples"), list(EXPECTED_SLOT_OFFSETS), "slot_offsets_samples")
    _require_exact(config.get("event_duration_samples"), EXPECTED_EVENT_DURATION, "event_duration_samples")
    _require_exact(config.get("expanded_window_grace_points"), EXPECTED_GRACE_POINTS, "expanded_window_grace_points")
    _require_exact(config.get("targets"), list(EXPECTED_TARGETS), "targets")
    _require_exact(config.get("detector"), {
        "min_calibration_points": 10,
        "robust_z_threshold": 4.0,
        "persistence_points": 2,
        "detection_grace_points": 3,
    }, "detector")
    _require_exact(config.get("bootstrap"), EXPECTED_BOOTSTRAP, "bootstrap")
    _require_exact(config.get("output_root"), EXPECTED_OUTPUT_ROOT, "output_root")

    layouts = config.get("layouts")
    if not isinstance(layouts, list) or len(layouts) != 12:
        raise AnomalyMatrixError("layouts must contain exactly 12 entries")
    expected_layouts = [(f"{equipment}-{mode.replace('_', '-')}", equipment, mode) for equipment in EXPECTED_EQUIPMENT for mode in EXPECTED_MODES]
    event_ids: set[str] = set()
    base_event_ids = {event.get("event_id") for event in base.get("events", []) if isinstance(event, dict)}
    slot_counts = {event_class: {offset: 0 for offset in EXPECTED_SLOT_OFFSETS} for event_class in EXPECTED_CLASSES}
    total_events = 0
    positive_events = 0
    suppression_events = 0
    full_targets = [f"{equipment}.{target}" for equipment in EXPECTED_EQUIPMENT for target in EXPECTED_TARGETS]

    for expected_index, (layout, expected_identity, regime) in enumerate(zip(layouts, expected_layouts, test_regimes * 2)):
        expected_layout_id, expected_equipment, expected_mode = expected_identity
        _require_exact(layout.get("layout_id"), expected_layout_id, f"layouts[{expected_index}].layout_id")
        _require_exact(layout.get("layout_index"), expected_index, f"layouts[{expected_index}].layout_index")
        _require_exact(layout.get("equipment_id"), expected_equipment, f"layouts[{expected_index}].equipment_id")
        _require_exact(layout.get("operating_mode"), expected_mode, f"layouts[{expected_index}].operating_mode")
        _require_exact(layout.get("mode_start_sample"), regime["start_sample"], f"{expected_layout_id}.mode_start_sample")
        _require_exact(layout.get("mode_end_sample"), regime["end_sample"], f"{expected_layout_id}.mode_end_sample")
        events = layout.get("events")
        if not isinstance(events, list) or len(events) != 4:
            raise AnomalyMatrixError(f"{expected_layout_id} must contain exactly four events")
        classes_seen: set[str] = set()
        expanded: list[tuple[int, int, str]] = []
        for class_index, event in enumerate(events):
            event_class = event.get("event_class")
            if event_class in classes_seen or event_class not in EXPECTED_CLASSES:
                raise AnomalyMatrixError(f"{expected_layout_id} event classes must be an exact partition")
            classes_seen.add(event_class)
            expected_slot = EXPECTED_SLOT_OFFSETS[(class_index + expected_index) % 4]
            event_id = f"{expected_layout_id}-{event_class.replace('_', '-') }"
            _require_exact(event.get("event_id"), event_id, f"{expected_layout_id}.{event_class}.event_id")
            if event_id in event_ids or event_id in base_event_ids:
                raise AnomalyMatrixError(f"event ID is duplicated or reuses the base event ID: {event_id}")
            event_ids.add(event_id)
            _require_exact(event.get("enabled"), True, f"{event_id}.enabled")
            _require_exact(event.get("start_offset_samples"), expected_slot, f"{event_id}.start_offset_samples")
            _require_exact(event.get("duration_samples"), EXPECTED_EVENT_DURATION, f"{event_id}.duration_samples")
            expected_type, expected_signal, expected_magnitude = _expected_event(layout, event_class, EXPECTED_EQUIPMENT_TYPES[expected_equipment])
            _require_exact(event.get("event_type"), expected_type, f"{event_id}.event_type")
            _require_exact(event.get("signal_id"), expected_signal, f"{event_id}.signal_id")
            _require_exact(event.get("magnitude"), expected_magnitude, f"{event_id}.magnitude")
            start = regime["start_sample"] + expected_slot
            end = start + EXPECTED_EVENT_DURATION
            expanded_end = end + EXPECTED_GRACE_POINTS
            if not regime["start_sample"] <= start < end <= expanded_end <= regime["end_sample"]:
                raise AnomalyMatrixError(f"{event_id} raw or expanded window escapes its mode")
            if not EXPECTED_TEST_SPLIT[0] <= start < expanded_end <= EXPECTED_TEST_SPLIT[1]:
                raise AnomalyMatrixError(f"{event_id} raw or expanded window escapes the test split")
            expanded.append((start, expanded_end, event_id))
            slot_counts[event_class][expected_slot] += 1
            total_events += 1
            if event_class in ("machine_fault", "sensor_fault"):
                positive_events += 1
            else:
                suppression_events += 1
        if classes_seen != set(EXPECTED_CLASSES):
            raise AnomalyMatrixError(f"{expected_layout_id} event classes must be an exact partition")
        for previous, current in zip(sorted(expanded), sorted(expanded)[1:]):
            if previous[1] > current[0]:
                raise AnomalyMatrixError(f"expanded accounting windows overlap: {previous[2]} and {current[2]}")

    for event_class in EXPECTED_CLASSES:
        if slot_counts[event_class] != {offset: 3 for offset in EXPECTED_SLOT_OFFSETS}:
            raise AnomalyMatrixError(f"{event_class} slot balance is not three per slot: {slot_counts[event_class]}")
    if total_events != 48 or positive_events != 24 or suppression_events != 24:
        raise AnomalyMatrixError("per-seed event counts are inconsistent")
    return {
        "layout_ids": [layout["layout_id"] for layout in layouts],
        "target_signal_ids": full_targets,
        "slot_counts": slot_counts,
        "event_count_per_seed": total_events,
        "positive_event_count_per_seed": positive_events,
        "suppression_event_count_per_seed": suppression_events,
    }


def validate_anomaly_matrix_config(config_path: str | Path, root: Path | None = None) -> dict[str, Any]:
    """Purely validate a preregistered matrix config and return an audit summary."""
    repository = (root or Path(__file__).resolve().parents[2]).absolute()
    path = _resolve_config_path(config_path, repository)
    config, config_raw, config_sha256 = _load_object_snapshot(path, "matrix config")
    try:
        schema_path = _safe_repo_path(repository, config.get("schema_path"), "schema_path", must_exist=True)
    except (AttributeError, TypeError) as exc:
        raise AnomalyMatrixError("schema_path must be present before path validation") from exc
    schema, schema_raw, schema_sha256 = _load_object_snapshot(schema_path, "matrix config schema")
    try:
        validate(config, schema)
    except ManifestValidationError as exc:
        raise AnomalyMatrixError(f"matrix config does not satisfy its schema: {exc}") from exc
    if schema_sha256 != EXPECTED_SCHEMA_SHA256 or config.get("schema_sha256") != schema_sha256:
        raise AnomalyMatrixError("matrix config schema SHA-256 pin is invalid")
    base_path = _safe_repo_path(repository, config["base_generator_config_path"], "base_generator_config_path", must_exist=True)
    base, base_raw, base_sha256 = _load_object_snapshot(base_path, "base generator config")
    if base_sha256 != EXPECTED_BASE_SHA256 or config.get("base_generator_config_sha256") != base_sha256:
        raise AnomalyMatrixError("base generator config SHA-256 pin is invalid")
    output_path = _safe_repo_path(repository, config["output_root"], "output_root", must_exist=False)
    if output_path.exists() and not output_path.is_dir():
        raise AnomalyMatrixError("output_root must be a directory when it already exists")
    test_regimes = _validate_base_generator(base, repository)
    details = _validate_semantics(config, base, test_regimes)

    # Re-read the three input snapshots before returning so a mutation during validation fails closed.
    current_config, current_config_raw, _ = _load_object_snapshot(path, "matrix config completion snapshot")
    current_schema, current_schema_raw, _ = _load_object_snapshot(schema_path, "matrix config schema completion snapshot")
    current_base, current_base_raw, _ = _load_object_snapshot(base_path, "base generator config completion snapshot")
    if current_config_raw != config_raw or current_schema_raw != schema_raw or current_base_raw != base_raw:
        raise AnomalyMatrixError("matrix inputs changed during validation")
    if current_config != config or current_schema != schema or current_base != base:
        raise AnomalyMatrixError("matrix input objects changed during validation")

    return {
        "schema_version": MATRIX_SCHEMA_VERSION,
        "summary_type": "event-aware-anomaly-matrix-validation",
        "status": "configuration_valid",
        "run_status": "not_run",
        "performance_status": "not_evaluated",
        "config_type": MATRIX_CONFIG_TYPE,
        "matrix_id": MATRIX_ID,
        "config_path": path.relative_to(repository).as_posix(),
        "config_sha256": config_sha256,
        "schema": {"path": schema_path.relative_to(repository).as_posix(), "sha256": schema_sha256},
        "base_generator": {"path": base_path.relative_to(repository).as_posix(), "sha256": base_sha256},
        "seeds": list(EXPECTED_SEEDS),
        "layout_ids": details["layout_ids"],
        "target_signal_ids": details["target_signal_ids"],
        "counts": {
            "cell_count": len(EXPECTED_SEEDS) * len(details["layout_ids"]),
            "layout_count": len(details["layout_ids"]),
            "event_count_per_seed": details["event_count_per_seed"],
            "positive_event_count_per_seed": details["positive_event_count_per_seed"],
            "suppression_event_count_per_seed": details["suppression_event_count_per_seed"],
            "positive_event_count_total": details["positive_event_count_per_seed"] * len(EXPECTED_SEEDS),
            "suppression_event_count_total": details["suppression_event_count_per_seed"] * len(EXPECTED_SEEDS),
        },
        "fixed_parameters": {
            "test_split": {"start_sample": EXPECTED_TEST_SPLIT[0], "end_sample": EXPECTED_TEST_SPLIT[1]},
            "mode_window_samples": EXPECTED_MODE_WINDOW,
            "slot_offsets_samples": list(EXPECTED_SLOT_OFFSETS),
            "event_duration_samples": EXPECTED_EVENT_DURATION,
            "expanded_window_grace_points": EXPECTED_GRACE_POINTS,
            "detector": dict(config["detector"]),
            "bootstrap": dict(config["bootstrap"]),
        },
        "slot_balance": details["slot_counts"],
        "safety": {
            "filesystem_write": False,
            "output_root": config["output_root"],
            "customer_data": False,
            "checkpoint_or_weights": False,
            "control_or_banto_hub_write": False,
        },
    }


def _text_summary(summary: Mapping[str, Any]) -> str:
    counts = summary["counts"]
    return "\n".join((
        "anomaly matrix configuration: PASS",
        f"status: {summary['status']} (run={summary['run_status']}, performance={summary['performance_status']})",
        f"cells/layouts: {counts['cell_count']} / {counts['layout_count']}",
        f"events per seed: {counts['event_count_per_seed']} (positive={counts['positive_event_count_per_seed']}, suppression={counts['suppression_event_count_per_seed']})",
        f"events total: positive={counts['positive_event_count_total']}, suppression={counts['suppression_event_count_total']}",
        f"config sha256: {summary['config_sha256']}",
    ))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="validate_anomaly_matrix")
    parser.add_argument("--config", required=True, help="repository-relative matrix config JSON")
    parser.add_argument("--root", help="repository root; defaults to this checkout")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    args = parser.parse_args(argv)
    try:
        summary = validate_anomaly_matrix_config(args.config, Path(args.root).absolute() if args.root else None)
    except (AnomalyMatrixError, KeyError, OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))
    else:
        print(_text_summary(summary))
    return 0


validate_matrix_config = validate_anomaly_matrix_config


if __name__ == "__main__":
    raise SystemExit(main())
