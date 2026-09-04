"""Toto 2.0 controlled 4-track cross-matrix acceptance analyzer.

The analyzer is deliberately post-hoc and fail-closed.  It does not retain
customer identifiers or raw data in its output; raw files are read only to
re-check the declared provenance and the controlled truth windows.
"""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import tempfile
from pathlib import Path, PureWindowsPath
from typing import Any, Iterable, Mapping

from .benchmark import PREDICTION_KEYS, _policy, _revision
from .event_slices import _verify_dataset
from .manifest import ManifestValidationError, load_json, validate


class AcceptanceError(ValueError):
    """Acceptance input, semantic contract, or output violation."""


TRACK_IDS = ("control", "target-fault", "target-quality", "covariate-quality")
TRACK_ROLES = {
    "control": "control",
    "target-fault": "target-fault",
    "target-quality": "target-quality",
    "covariate-quality": "covariate-quality",
}
EXPECTED_EVENT_CONTRACTS = {
    "control": (),
    "target-fault": (("motor-01-current-jam-or-slip-test", "motor-01", "motor_current", "jam_or_slip", 388, 396, 0.35, True, "target"),),
    "target-quality": (
        ("motor-01-current-dropout-context", "motor-01", "motor_current", "dropout", 368, 372, 0.0, True, "target"),
        ("motor-01-temperature-stale-context", "motor-01", "motor_temperature", "stale_value", 372, 376, 0.0, True, "target"),
    ),
    "covariate-quality": (
        ("motor-01-load-dropout-context", "motor-01", "load_proxy", "dropout", 368, 372, 0.0, True, "covariate"),
        ("motor-01-load-stale-context", "motor-01", "load_proxy", "stale_value", 372, 376, 0.0, True, "covariate"),
    ),
}
EXPECTED_MATRIX_IDS = {
    "control": "toto2-ctl-a",
    "target-fault": "toto2-ctl-b",
    "target-quality": "toto2-ctl-c",
    "covariate-quality": "toto2-ctl-d",
}
ORIGIN_INDEX = 384
EXPECTED_AXES = {"seeds": [17, 29, 42, 73, 101], "horizons": [15, 30], "context_lengths": [64, 120], "expansion_order": ["seed", "horizon", "context_length"]}
EXPECTED_BENCHMARK_MODELS = [
    {"name": "last-value"},
    {"name": "seasonal-naive", "parameters": {"season_length": 15}},
    {"name": "moving-average", "parameters": {"window": 15}},
    {"name": "ewma", "parameters": {"alpha": 0.3}},
    {"name": "holt-linear", "parameters": {"alpha": 0.8, "beta": 0.2}},
    {"name": "toto2", "quantile_policy": "native", "parameters": {"checkpoint_revision": "8306a9801cf98c0f5ffe4b2dcc8f496e616d84d9", "batch_size": 1, "device": "cpu", "local_files_only": True, "patch_size": 32}},
]


class _DuplicateJSON(ValueError):
    pass


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJSON(f"duplicate JSON property: {key}")
        result[key] = value
    return result


def _strict_json(path: Path, label: str) -> tuple[Any, bytes]:
    try:
        raw = path.read_bytes()
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
            parse_float=lambda value: float(value) if math.isfinite(float(value)) else (_ for _ in ()).throw(ValueError(value)),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise AcceptanceError(f"{label} is not strict UTF-8 JSON: {exc}") from exc
    return value, raw


def _strict_object(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    value, raw = _strict_json(path, label)
    if not isinstance(value, dict):
        raise AcceptanceError(f"{label} must be a JSON object")
    return value, raw


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise AcceptanceError(f"source file is unreadable: {path}") from exc


def _safe_relative(raw: Any, label: str) -> str:
    if (
        not isinstance(raw, str)
        or not raw
        or raw.startswith("/")
        or "\\" in raw
        or PureWindowsPath(raw).drive
    ):
        raise AcceptanceError(f"{label} must be a repository-relative POSIX path")
    parts = raw.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise AcceptanceError(f"{label} must be normalized and traversal-free")
    return raw


def _safe_path(root: Path, raw: Any, label: str, *, must_exist: bool = True) -> Path:
    relative = _safe_relative(raw, label)
    cursor = root
    for part in relative.split("/"):
        cursor = cursor / part
        if cursor.is_symlink():
            raise AcceptanceError(f"{label} cannot traverse a symlink")
    resolved = (root / relative).resolve()
    if resolved == root or root not in resolved.parents:
        raise AcceptanceError(f"{label} must remain inside repository")
    if must_exist and not resolved.exists():
        raise AcceptanceError(f"{label} does not exist: {relative}")
    return resolved


def _safe_file(root: Path, raw: Any, label: str) -> Path:
    path = _safe_path(root, raw, label)
    if path.is_symlink() or not path.is_file():
        raise AcceptanceError(f"{label} must be a regular file")
    return path


def _artifact_output(root: Path, raw: Any) -> Path:
    path = _safe_path(root, raw, "output_dir", must_exist=False)
    artifacts = (root / "artifacts").resolve()
    if path == artifacts or artifacts not in path.parents:
        raise AcceptanceError("output_dir must be below artifacts")
    return path


def _overlap(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


def _schema(root: Path, name: str) -> dict[str, Any]:
    value = load_json(root / "schemas" / name)
    if not isinstance(value, dict):
        raise AcceptanceError(f"schema is not an object: {name}")
    return value


def _schema_validate(value: Any, schema: dict[str, Any], label: str) -> None:
    try:
        validate(value, schema)
    except ManifestValidationError as exc:
        raise AcceptanceError(f"{label} does not satisfy its schema: {exc}") from exc


def _duplicates(values: Iterable[Any]) -> bool:
    items = list(values)
    return len(items) != len(set(items))


def validate_acceptance_config(config: Mapping[str, Any], root: Path) -> None:
    """Validate the analyzer config without requiring any result artifact."""
    if not isinstance(config, dict):
        raise AcceptanceError("analyzer config must be an object")
    _schema_validate(dict(config), _schema(root, "toto2-controlled-acceptance-config.schema.json"), "analyzer config")
    if config.get("track_order") != list(TRACK_IDS):
        raise AcceptanceError("track_order must be control, target-fault, target-quality, covariate-quality")
    tracks = config.get("tracks")
    if not isinstance(tracks, list) or [item.get("track_id") for item in tracks] != list(TRACK_IDS):
        raise AcceptanceError("tracks must contain the four controlled tracks in fixed order")
    if _duplicates(item["matrix_result_path"] for item in tracks):
        raise AcceptanceError("matrix_result_path must be unique")
    output = _artifact_output(root, config["output_dir"])
    for track in tracks:
        if track["role"] != TRACK_ROLES[track["track_id"]]:
            raise AcceptanceError(f"track role is invalid: {track['track_id']}")
        for name in ("matrix_result_path", "matrix_config_path", "generator_config_path", "benchmark_config_path"):
            _safe_path(root, track[name], name, must_exist=False)
        expected = track["expected_events"]
        expected_contract = tuple((
            event["event_id"], event["equipment_id"], event["signal_id"], event["event_type"],
            event["start_sample"], event["end_sample"], event["magnitude"], event["enabled"], event["role"]
        ) for event in expected)
        if expected_contract != EXPECTED_EVENT_CONTRACTS[track["track_id"]]:
            raise AcceptanceError(f"expected event contract is not the fixed controlled contract: {track['track_id']}")
        if _duplicates((event["equipment_id"], event["signal_id"], event["event_type"], event["start_sample"], event["end_sample"]) for event in expected):
            raise AcceptanceError(f"duplicate expected event: {track['track_id']}")
    source_specs: list[tuple[Path, str]] = []
    for track in tracks:
        source_specs.extend((_safe_path(root, track[name], name, must_exist=False), name) for name in ("matrix_result_path", "matrix_config_path", "generator_config_path", "benchmark_config_path"))
    if any(_overlap(left, right) and not (left == right and left_name == right_name == "benchmark_config_path") for index, (left, left_name) in enumerate(source_specs) for right, right_name in source_specs[index + 1:]):
        raise AcceptanceError("analyzer source paths must be disjoint")
    if any(_overlap(output, path) for path, _ in source_specs):
        raise AcceptanceError("output_dir overlaps a matrix result source")


def _cell_id(seed: int, horizon: int, context: int) -> str:
    return f"seed-{seed}--horizon-{horizon}--context-{context}"


def _expected_cells(axes: Mapping[str, Any]) -> list[tuple[str, int, int, int]]:
    return [
        (_cell_id(seed, horizon, context), seed, horizon, context)
        for seed in axes["seeds"]
        for horizon in axes["horizons"]
        for context in axes["context_lengths"]
    ]


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _canonical_without(value: Mapping[str, Any], *names: str) -> dict[str, Any]:
    return {key: value for key, value in value.items() if key not in names}


def _event_tuples(generator: Mapping[str, Any]) -> tuple[tuple[Any, ...], ...]:
    events = []
    for event in generator.get("events", []):
        events.append((
            event["equipment_id"], event.get("signal_id"), event["event_type"],
            event["start_sample"], event["end_sample"],
        ))
    return tuple(events)


def _event_roles(generator: Mapping[str, Any]) -> dict[tuple[Any, ...], str]:
    signals = {item["signal_id"]: item for item in generator.get("signals", []) if isinstance(item, dict)}
    # The synthetic generator config does not carry signal metadata; use the
    # fixed catalog when available and let the dataset manifest re-check it.
    role_by_signal = {"motor_current": "target", "motor_temperature": "target", "load_proxy": "covariate", "conveyor_speed": "target", "vibration_feature": "target"}
    return {
        (event["equipment_id"], event.get("signal_id"), event["event_type"], event["start_sample"], event["end_sample"]): role_by_signal.get(event.get("signal_id"), signals.get(event.get("signal_id"), {}).get("role"))
        for event in generator.get("events", [])
    }


def _parse_jsonl(path: Path, label: str) -> list[dict[str, Any]]:
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise AcceptanceError(f"{label} is not strict UTF-8 JSONL") from exc
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            raise AcceptanceError(f"{label}:{number} is blank")
        try:
            value = json.loads(
                line,
                object_pairs_hook=_pairs,
                parse_constant=lambda item: (_ for _ in ()).throw(ValueError(item)),
                parse_float=lambda item: float(item) if math.isfinite(float(item)) else (_ for _ in ()).throw(ValueError(item)),
            )
        except (json.JSONDecodeError, ValueError) as exc:
            raise AcceptanceError(f"{label}:{number} is not strict JSON") from exc
        if not isinstance(value, dict):
            raise AcceptanceError(f"{label}:{number} must be an object")
        rows.append(value)
    if not rows:
        raise AcceptanceError(f"{label} must not be empty")
    return rows


def _snapshot(snapshots: dict[Path, str], path: Path) -> None:
    snapshots.setdefault(path.resolve(), _sha256(path))


def _assert_unchanged(snapshots: Mapping[Path, str]) -> None:
    for path, digest in snapshots.items():
        if not path.exists() or _sha256(path) != digest:
            raise AcceptanceError(f"source artifact changed during analysis: {path}")


def _quality_counts(dataset: Mapping[str, Any], equipment: str, signals: list[str], origin: int, context: int) -> dict[str, Any]:
    rows = dataset["observations"].get(equipment, [])
    selected = rows[origin - context:origin]
    metadata = dataset["signals"]
    by_role: dict[str, dict[str, dict[str, int]]] = {}
    for signal in signals:
        role = metadata[signal]["role"]
        logical = signal.rsplit(".", 1)[-1]
        counts = {"ok": 0, "missing": 0, "stale": 0, "non_ok": 0, "other": 0, "finite_value_count": 0, "model_observed_value_count": 0}
        for row in selected:
            status = row["quality"].get(logical)
            if status not in ("ok", "missing", "stale"):
                status_key = "other"
            else:
                status_key = status
            counts[status_key] += 1
            if status_key != "ok":
                counts["non_ok"] += 1
            if _finite(row["signals"][logical]["value"]):
                counts["finite_value_count"] += 1
            if status_key == "ok" and _finite(row["signals"][logical]["value"]):
                counts["model_observed_value_count"] += 1
        by_role.setdefault(role, {})[logical] = counts
    return {
        "signals": by_role,
        "context_row_count": len(selected),
        "expected_value_count": len(signals) * context,
        "source_finite_value_count": sum(counts["finite_value_count"] for values in by_role.values() for counts in values.values()),
        "model_observed_value_count": sum(counts["model_observed_value_count"] for values in by_role.values() for counts in values.values()),
    }


def _validate_context_audit(audit: Mapping[str, Any], signal_count: int, context: int) -> None:
    if audit.get("context_row_count") != context or audit.get("expected_value_count") != signal_count * context:
        raise AcceptanceError("context audit row/value denominator is inconsistent")
    finite = 0
    observed = 0
    for role_values in audit.get("signals", {}).values():
        for counts in role_values.values():
            if sum(counts[key] for key in ("ok", "missing", "stale", "other")) != context or counts["non_ok"] != counts["missing"] + counts["stale"] + counts["other"] or counts["model_observed_value_count"] > counts["finite_value_count"]:
                raise AcceptanceError("context signal quality counts are inconsistent")
            finite += counts["finite_value_count"]
            observed += counts["model_observed_value_count"]
    if audit.get("source_finite_value_count") != finite or audit.get("model_observed_value_count") != observed:
        raise AcceptanceError("context finite/observed counts are inconsistent")


def _truth(dataset: Mapping[str, Any], equipment: str, target: str, origin: int, horizon: int) -> tuple[str, list[float | None], list[str]]:
    rows = dataset["observations"].get(equipment, [])
    logical = target.rsplit(".", 1)[-1]
    values: list[float | None] = []
    quality: list[str] = []
    for row in rows[origin:origin + horizon]:
        value = row["signals"][logical]["value"]
        values.append(float(value) if _finite(value) else None)
        quality.append(str(row["quality"].get(logical)))
    if len(values) != horizon:
        return "unavailable", values, quality
    if any(value is None for value in values):
        return "unavailable", values, quality
    if any(status != "ok" for status in quality):
        return "non_ok", values, quality
    return "valid", values, quality


def _future_pair(dataset: Mapping[str, Any], equipment: str, target: str) -> list[tuple[Any, Any]]:
    logical = target.rsplit(".", 1)[-1]
    rows = dataset["observations"].get(equipment, [])
    return [(row["signals"][logical]["value"], row["quality"].get(logical)) for row in rows[384:414]]


def _validate_cross_track_truth(track_datasets: Mapping[str, Mapping[int, Mapping[str, Any]]], benchmark: Mapping[str, Any], seeds: Iterable[int]) -> None:
    control = track_datasets["control"]
    for seed in seeds:
        for equipment in benchmark["equipment_ids"]:
            for target in benchmark["target_signal_ids"]:
                control_future = _future_pair(control[seed], equipment, target)
                if len(control_future) != 30 or any(not _finite(value) or quality != "ok" for value, quality in control_future):
                    raise AcceptanceError(f"control future truth is not finite/quality-ok: {seed}/{equipment}/{target}")
                for track_id in ("target-quality", "covariate-quality"):
                    degraded_future = _future_pair(track_datasets[track_id][seed], equipment, target)
                    if degraded_future != control_future:
                        raise AcceptanceError(f"quality track future target truth differs from control: {track_id}/{seed}/{equipment}/{target}")
                    if any(not _finite(value) or quality != "ok" for value, quality in degraded_future):
                        raise AcceptanceError(f"quality track future truth is not finite/quality-ok: {track_id}/{seed}/{equipment}/{target}")
                fault_future = _future_pair(track_datasets["target-fault"][seed], equipment, target)
                if len(fault_future) != 30 or any(not _finite(value) or quality != "ok" for value, quality in fault_future):
                    raise AcceptanceError(f"fault future truth is not finite/quality-ok: {seed}/{equipment}/{target}")
                is_fault_target = equipment == "motor-01" and target.rsplit(".", 1)[-1] == "motor_current"
                for offset, pair in enumerate(fault_future):
                    in_event = 4 <= offset < 12
                    if not (is_fault_target and in_event) and pair != control_future[offset]:
                        raise AcceptanceError(f"fault track changed truth outside its event: {seed}/{equipment}/{target}/{384 + offset}")
                if is_fault_target and any(fault_future[offset] == control_future[offset] for offset in range(4, 12)):
                    raise AcceptanceError(f"fault track did not change every motor_current point in [388,396): {seed}")


def _source_record(path: Path, root: Path, snapshots: dict[Path, str], kind: str) -> dict[str, Any]:
    _snapshot(snapshots, path)
    try:
        relative = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise AcceptanceError(f"source path escaped repository: {path}") from exc
    return {"kind": kind, "path": relative, "sha256": snapshots[path.resolve()]}


def _matrix_config_consistent(actual: Mapping[str, Any], track: Mapping[str, Any]) -> None:
    if actual.get("matrix_id") != track["matrix_id"]:
        raise AcceptanceError(f"matrix_id mismatch for {track['track_id']}")
    for name in ("generator_config_path", "benchmark_config_path", "dataset_output_root", "benchmark_output_root", "matrix_output_dir"):
        if actual.get(name) != track[name]:
            raise AcceptanceError(f"matrix {name} mismatch for {track['track_id']}")


def _revision_consistent(revision: Mapping[str, Any]) -> None:
    if revision.get("status") != "git" or revision.get("dirty") is not False or not isinstance(revision.get("head"), str) or len(revision["head"]) != 40 or any(char not in "0123456789abcdef" for char in revision["head"]) or not isinstance(revision.get("diff_sha256"), str) or len(revision["diff_sha256"]) != 64 or any(char not in "0123456789abcdef" for char in revision["diff_sha256"]):
        raise AcceptanceError("matrix/code revision must be git and clean")


def _cell_result_audit(
    *, root: Path, track: Mapping[str, Any], matrix: Mapping[str, Any], cell: Mapping[str, Any],
    matrix_revision: Mapping[str, Any], benchmark: Mapping[str, Any], dataset: Mapping[str, Any],
    dataset_entry: Mapping[str, Any], snapshots: dict[Path, str], expected: tuple[str, int, int, int],
) -> dict[str, Any]:
    cell_id, seed, horizon, context = expected
    if tuple(cell.get(name) for name in ("cell_id", "seed", "horizon", "context_length")) != (cell_id, seed, horizon, context):
        raise AcceptanceError(f"cell metadata mismatch: {track['track_id']}/{cell_id}")
    expected_output_dir_text = f"{track['benchmark_output_root']}/{track['matrix_id']}/{cell_id}"
    expected_run_id = f"{benchmark['run_id']}--{track['matrix_id']}--{cell_id}"
    if cell.get("run_id") != expected_run_id or cell.get("dataset_id") != dataset_entry.get("dataset_id") or cell.get("dataset_path") != dataset_entry.get("dataset_path") or cell.get("dataset_fingerprint") != dataset_entry.get("dataset_fingerprint") or cell.get("output_dir") != expected_output_dir_text:
        raise AcceptanceError(f"cell identity/output metadata mismatch: {cell_id}")
    if cell.get("benchmark_config_path") is None or cell.get("result_path") is None:
        if cell.get("status") != "failed":
            raise AcceptanceError(f"missing failed-cell evidence: {track['track_id']}/{cell_id}")
        if not isinstance(cell.get("failure"), dict):
            raise AcceptanceError(f"failed cell has no failure evidence: {track['track_id']}/{cell_id}")
        return _blocked_cell(cell, cell_id, seed, horizon, context, "cell has no result artifact")
    config_path = _safe_file(root, cell["benchmark_config_path"], "cell benchmark config")
    result_path = _safe_file(root, cell["result_path"], "cell result")
    expected_config_path = _safe_path(root, f"{track['matrix_output_dir']}/configs/benchmarks/{cell_id}.json", "expected cell benchmark config")
    expected_output_dir = _safe_path(root, expected_output_dir_text, "expected cell output")
    expected_result_path = expected_output_dir / "result.json"
    if config_path != expected_config_path or result_path != expected_result_path or cell.get("output_dir") != f"{track['benchmark_output_root']}/{track['matrix_id']}/{cell_id}":
        raise AcceptanceError(f"cell path does not follow matrix runner layout: {track['track_id']}/{cell_id}")
    if _sha256(config_path) != cell.get("benchmark_config_sha256"):
        raise AcceptanceError(f"cell benchmark config hash mismatch: {cell_id}")
    if result_path.parent != _safe_path(root, cell["output_dir"], "cell output_dir"):
        raise AcceptanceError(f"cell result path/output_dir mismatch: {cell_id}")
    _snapshot(snapshots, config_path)
    _snapshot(snapshots, result_path)
    result, _ = _strict_object(result_path, "cell result")
    _schema_validate(result, _schema(root, "benchmark-result.schema.json"), "cell result")
    materialized_config, materialized_raw = _strict_object(config_path, "cell benchmark config")
    if result.get("run_config") != materialized_config:
        raise AcceptanceError(f"cell result run_config mismatch: {cell_id}")
    allowed = {"run_id", "dataset_path", "output_dir", "seed", "horizon", "context_length"}
    if _canonical_without(materialized_config, *allowed) != _canonical_without(benchmark, *allowed):
        raise AcceptanceError(f"materialized benchmark config changed an unapproved field: {cell_id}")
    if materialized_config.get("run_id") != expected_run_id or materialized_config.get("dataset_path") != dataset_entry.get("dataset_path") or materialized_config.get("output_dir") != cell.get("output_dir") or materialized_config.get("seed") != seed or materialized_config.get("horizon") != horizon or materialized_config.get("context_length") != context:
        raise AcceptanceError(f"materialized benchmark config identity mismatch: {cell_id}")
    if _sha256_bytes(materialized_raw) != cell.get("benchmark_config_sha256"):
        raise AcceptanceError(f"materialized benchmark config hash mismatch: {cell_id}")
    if result.get("code_revision") != matrix_revision:
        raise AcceptanceError(f"cell code_revision mismatch: {cell_id}")
    expected_policies = {model["name"]: _policy(model) for model in benchmark["models"]}
    if result.get("runtime", {}).get("quantile_policy_by_model") != expected_policies or result.get("provenance", {}).get("quantile_policy_by_model") != expected_policies:
        raise AcceptanceError(f"cell quantile policy provenance mismatch: {cell_id}")
    expected_parameters = {model["name"]: model.get("parameters", {}) for model in benchmark["models"]}
    if result.get("model_parameters") != expected_parameters:
        raise AcceptanceError(f"cell model parameters provenance mismatch: {cell_id}")
    if result.get("generator_version") != dataset["manifest"].get("generator_version") or result.get("provenance", {}).get("quality_gate") != dataset["quality"]:
        raise AcceptanceError(f"cell dataset provenance mismatch: {cell_id}")
    if result.get("seed") != seed or result.get("dataset_fingerprint") != dataset_entry["dataset_fingerprint"]:
        raise AcceptanceError(f"cell provenance mismatch: {cell_id}")
    if result.get("run_id") != cell.get("run_id") or result.get("status") != cell.get("status"):
        raise AcceptanceError(f"cell result identity/status mismatch: {cell_id}")
    if cell.get("benchmark_failure_count") != len(result.get("failures", [])):
        raise AcceptanceError(f"cell benchmark_failure_count mismatch: {cell_id}")
    origin_selection = result.get("provenance", {}).get("origin_selection", {}).get("test", {})
    for equipment in benchmark["equipment_ids"]:
        selected = origin_selection.get(equipment)
        if not isinstance(selected, dict) or selected.get("indices") != [ORIGIN_INDEX] or selected.get("count") != 1:
            raise AcceptanceError(f"test origin must be exactly 384: {cell_id}/{equipment}")
    prediction_path = result_path.parent / "predictions.jsonl"
    prediction_path = _safe_file(root, prediction_path.relative_to(root).as_posix(), "predictions")
    _snapshot(snapshots, prediction_path)
    rows = _parse_jsonl(prediction_path, "predictions.jsonl")
    rows_by_equipment = dataset["observations"]
    for equipment in benchmark["equipment_ids"]:
        if len(rows_by_equipment.get(equipment, [])) < ORIGIN_INDEX + horizon:
            raise AcceptanceError(f"dataset has no complete origin 384/horizon: {cell_id}/{equipment}")
    quantile_keys = [str(value) for value in benchmark["quantiles"]]
    expected_keys: set[tuple[Any, ...]] = set()
    for model in benchmark["models"]:
        for equipment in benchmark["equipment_ids"]:
            equipment_origin_timestamp = rows_by_equipment[equipment][ORIGIN_INDEX]["timestamp"]
            for target in benchmark["target_signal_ids"]:
                for lead in range(1, horizon + 1):
                    expected_keys.add((model["name"], equipment, f"{equipment}.{target.rsplit('.', 1)[-1]}", equipment_origin_timestamp, lead))
    observed: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        if set(row) != PREDICTION_KEYS:
            raise AcceptanceError(f"prediction keys are not exact: {cell_id}")
        if row.get("split") != "test" or not isinstance(row.get("lead_time"), int) or row["lead_time"] <= 0:
            raise AcceptanceError(f"prediction metadata is invalid: {cell_id}")
        if not all(_finite(row.get(key)) for key in ("actual", "point_forecast")) or not isinstance(row.get("quantiles"), dict):
            raise AcceptanceError(f"prediction values are invalid: {cell_id}")
        if list(row["quantiles"]) != quantile_keys or any(not _finite(value) for value in row["quantiles"].values()):
            raise AcceptanceError(f"prediction quantiles are invalid: {cell_id}")
        ordered_quantiles = [float(row["quantiles"][key]) for key in quantile_keys]
        if any(left > right for left, right in zip(ordered_quantiles, ordered_quantiles[1:])):
            raise AcceptanceError(f"prediction quantile crossing detected: {cell_id}")
        key = (row.get("model"), row.get("equipment_id"), row.get("target_signal_id"), row.get("origin_timestamp"), row.get("lead_time"))
        if key not in expected_keys:
            raise AcceptanceError(f"extra prediction key: {cell_id}/{key}")
        equipment = row["equipment_id"]
        expected_timestamp = rows_by_equipment[equipment][ORIGIN_INDEX + row["lead_time"] - 1]["timestamp"]
        if row["timestamp"] != expected_timestamp:
            raise AcceptanceError(f"prediction timestamp/lead mismatch: {cell_id}/{key}")
        if row["model"] == "toto2":
            median = float(row["quantiles"]["0.5"])
            tolerance = 1e-5 * max(1.0, abs(float(row["point_forecast"])), abs(median))
            if abs(float(row["point_forecast"]) - median) > tolerance:
                raise AcceptanceError(f"Toto native p50/point mismatch: {cell_id}/{key}")
        if key in observed:
            raise AcceptanceError(f"duplicate prediction key: {cell_id}/{key}")
        observed[key] = row
    groups: list[dict[str, Any]] = []
    failures: dict[tuple[Any, ...], dict[str, Any]] = {}
    configured_models = {model["name"] for model in benchmark["models"]}
    configured_equipment = set(benchmark["equipment_ids"])
    configured_targets = {f"{equipment}.{target.rsplit('.', 1)[-1]}" for equipment in benchmark["equipment_ids"] for target in benchmark["target_signal_ids"]}
    for item in result.get("failures", []):
        if not isinstance(item, dict) or item.get("split") not in ("validation", "test") or item.get("status") not in ("failed", "inconclusive"):
            raise AcceptanceError(f"failure provenance is invalid: {cell_id}")
        failure_key = (item.get("model"), item.get("equipment_id"), item.get("target_signal_id"))
        if failure_key in failures or failure_key[0] not in configured_models or failure_key[1] not in configured_equipment or failure_key[2] not in configured_targets:
            raise AcceptanceError(f"duplicate or unknown failure group: {cell_id}")
        failures[failure_key] = item
    if result.get("status") == "success" and failures:
        raise AcceptanceError(f"successful cell contains failures: {cell_id}")
    if result.get("prediction_count") != len(rows):
        raise AcceptanceError(f"prediction_count mismatch: {cell_id}")
    for model_cfg in benchmark["models"]:
        model = model_cfg["name"]
        for equipment in benchmark["equipment_ids"]:
            context_signals = [f"{equipment}.{name.rsplit('.', 1)[-1]}" for name in benchmark["target_signal_ids"] + benchmark.get("past_only_covariate_ids", []) + benchmark.get("known_future_covariate_ids", [])]
            for target in benchmark["target_signal_ids"]:
                target_id = f"{equipment}.{target.rsplit('.', 1)[-1]}"
                group_origin_timestamp = rows_by_equipment[equipment][ORIGIN_INDEX]["timestamp"]
                key_prefix = (model, equipment, target_id, group_origin_timestamp)
                group_rows = [row for key, row in observed.items() if key[:4] == key_prefix]
                truth_status, truths, truth_quality = _truth(dataset, equipment, target, ORIGIN_INDEX, horizon)
                valid_rows = 0
                mismatch = False
                errors: list[float] = []
                for row in group_rows:
                    lead = row["lead_time"]
                    actual = truths[lead - 1] if lead <= len(truths) else None
                    if actual is None or truth_status != "valid":
                        continue
                    if float(row["actual"]) != float(actual):
                        mismatch = True
                    else:
                        valid_rows += 1
                        errors.append(abs(float(row["point_forecast"]) - float(actual)))
                if mismatch:
                    raise AcceptanceError(f"prediction actual disagrees with dataset truth: {cell_id}/{equipment}/{target}")
                failure = failures.get((model, equipment, target_id))
                if failure and len(group_rows) == horizon:
                    raise AcceptanceError(f"failure evidence contradicts complete predictions: {cell_id}/{equipment}/{target_id}")
                group_status = "complete" if len(group_rows) == horizon and valid_rows == horizon and truth_status == "valid" else "blocked"
                if failure:
                    group_status = failure.get("status", "failed")
                consumed = context_signals if model == "toto2" else [target_id]
                context_audit = _quality_counts(dataset, equipment, consumed, ORIGIN_INDEX, context)
                _validate_context_audit(context_audit, len(consumed), context)
                non_ok_excluded = sum(
                    counts["non_ok"]
                    for role_values in context_audit["signals"].values()
                    for counts in role_values.values()
                ) if model != "toto2" else 0
                semantics = "Toto は全targetとpast-only covariateのmaskを使い、paddingはsource qualityと別に数える" if model == "toto2" else "baseline は当該targetのnon-OK historyを除外して短縮し、past-only covariateを使わない"
                groups.append({
                    "group": {"model": model, "equipment_id": equipment, "target_signal_id": target_id, "origin_sample": ORIGIN_INDEX, "origin_timestamp": group_origin_timestamp},
                    "expected_prediction_count": horizon,
                    "observed_prediction_count": len(group_rows),
                    "valid_prediction_count": valid_rows,
                    "availability": len(group_rows) / horizon,
                    "status": group_status,
                    "failure": ({"status": failure.get("status"), "reason": failure.get("reason"), "split": failure.get("split")} if failure else None),
                    "truth": {"status": truth_status, "quality": {status: truth_quality.count(status) for status in sorted(set(truth_quality))}},
                    "context": context_audit,
                    "expected_consumed_signal_set": consumed,
                    "consumption_evidence": "static-contract",
                    "non_ok_history_excluded_count": non_ok_excluded,
                    "padding_count": ((-context) % 32) if model == "toto2" else 0,
                    "input_semantics": semantics,
                    "accuracy": {"mae": sum(errors) / len(errors) if errors else None, "status": "valid" if valid_rows == horizon and truth_status == "valid" else "inconclusive"},
                })
    source = [
        _source_record(result_path, root, snapshots, "cell-result"),
        _source_record(prediction_path, root, snapshots, "predictions"),
        _source_record(config_path, root, snapshots, "cell-benchmark-config"),
    ]
    return {"cell_id": cell_id, "seed": seed, "horizon": horizon, "context_length": context, "status": "pass" if all(item["status"] == "complete" for item in groups) and cell.get("status") == "success" else "blocked", "source_artifacts": source, "groups": groups}


def _blocked_cell(cell: Mapping[str, Any], cell_id: str, seed: int, horizon: int, context: int, reason: str) -> dict[str, Any]:
    return {"cell_id": cell_id, "seed": seed, "horizon": horizon, "context_length": context, "status": "blocked", "source_artifacts": [], "groups": [], "failure": reason}


def _mae(group: Mapping[str, Any]) -> float | None:
    value = group.get("accuracy", {}).get("mae")
    return float(value) if _finite(value) else None


def _paired_deltas(control: Mapping[str, Any], degraded: Mapping[str, Any], track_id: str) -> list[dict[str, Any]]:
    left = {tuple(item["group"][key] for key in ("model", "equipment_id", "target_signal_id", "origin_timestamp")): item for item in control.get("groups", [])}
    output = []
    for right in degraded.get("groups", []):
        key = tuple(right["group"][name] for name in ("model", "equipment_id", "target_signal_id", "origin_timestamp"))
        baseline = left.get(key)
        if baseline is None:
            output.append({"track_id": track_id, "cell_id": degraded["cell_id"], "group": right["group"], "status": "inconclusive", "availability_delta": None, "accuracy_delta": None, "truth_status": "inconclusive", "ranking": "no-rank"})
            continue
        truth_valid = baseline.get("truth", {}).get("status") == "valid" and right.get("truth", {}).get("status") == "valid"
        output.append({
            "track_id": track_id, "cell_id": degraded["cell_id"], "group": right["group"],
            "status": "paired" if truth_valid and baseline.get("status") == "complete" and right.get("status") == "complete" else "inconclusive",
            "availability_delta": right.get("availability", 0.0) - baseline.get("availability", 0.0),
            "accuracy_delta": ({"mae": _mae(right) - _mae(baseline), "definition": "degraded MAE - control MAE"} if truth_valid and _mae(right) is not None and _mae(baseline) is not None else None),
            "truth_status": "valid" if truth_valid else "inconclusive",
            "ranking": "no-rank",
        })
    return output


def _summary(result: Mapping[str, Any]) -> str:
    counts = result["counts"]
    lines = [
        "# Toto 2.0 controlled 4-track acceptance analyzer結果", "",
        "これは合成controlled scenarioの契約検証結果であり、実設備性能・顧客データ・製品採用を示しません。", "",
        "## 判定", "",
        f"- controlled acceptance status: `{result['controlled_acceptance_status']}`",
        f"- tracks: {counts['tracks']} / 4", f"- cells: {counts['cells']} / {counts['expected_cells']}",
        f"- groups: {counts['groups']} / {counts['expected_groups']}",
        f"- analyzer code revision: `{result['analyzer_code_revision']['head']}`（git cleanを再検証）",
        "- cross-model ranking: `禁止（cross_model_ranking_allowed=false）`", "",
        "## track", "", "| track | role | matrix | status |", "| --- | --- | --- | --- |",
    ]
    for track in result["tracks"]:
        lines.append(f"| `{track['track_id']}` | `{track['role']}` | `{track['matrix_id']}` | `{track['status']}` |")
    lines.extend(["", "## input semantics", "", "baseline は non-OK target history を除外して短縮し、past-only covariate を使いません。Toto は mask を使います。padding count は source quality count と分離しています。", "", "## paired delta", "", "同一 model・equipment・target・origin・cell の control → degraded のみを比較します。truth が valid でない場合は accuracy delta を出さず `inconclusive/no-rank` とします。", "", "## source", "", "指定されたmatrix/cell/dataset artifactを、source hashとanalyzer／matrix／cellのclean code revisionの再検証後に解析した結果です。expected consumed signal setはruntime traceではなくstatic contract evidenceです。"])
    return "\n".join(lines) + "\n"


def analyze_controlled_acceptance(config_path: str | Path, root: Path) -> Path:
    """Analyze four declared matrices and atomically publish a result directory."""
    root = Path(root).expanduser().resolve()
    analyzer_code_revision = _revision(root)
    _revision_consistent(analyzer_code_revision)
    config_input = Path(config_path).expanduser()
    if config_input.is_absolute():
        try:
            config_relative = config_input.relative_to(root)
        except ValueError as exc:
            raise AcceptanceError("config must be a repository-local regular file") from exc
        if config_relative.as_posix() in ("", "."):
            raise AcceptanceError("config must be a repository-local regular file")
        config_file = _safe_path(root, config_relative.as_posix(), "config_path")
    else:
        config_file = _safe_path(root, config_input.as_posix(), "config_path")
    if config_file.is_symlink() or not config_file.is_file():
        raise AcceptanceError("config must be a repository-local regular file")
    config, config_raw = _strict_object(config_file, "analyzer config")
    validate_acceptance_config(config, root)
    output = _artifact_output(root, config["output_dir"])
    if output.exists():
        raise AcceptanceError(f"refusing to overwrite existing output: {output}")
    snapshots: dict[Path, str] = {config_file: _sha256_bytes(config_raw)}
    tracks_cfg = {track["track_id"]: track for track in config["tracks"]}
    matrix_infos: dict[str, dict[str, Any]] = {}
    common_axes: dict[str, Any] | None = None
    common_revision: Mapping[str, Any] | None = None
    common_benchmark: Mapping[str, Any] | None = None
    common_benchmark_hash: str | None = None
    common_generator_normalized: dict[str, Any] | None = None
    for track_id in TRACK_IDS:
        track = tracks_cfg[track_id]
        matrix_path = _safe_file(root, track["matrix_result_path"], "matrix_result_path")
        expected_matrix_result_path = _safe_path(root, f"{track['matrix_output_dir']}/result.json", "expected matrix result")
        if matrix_path != expected_matrix_result_path:
            raise AcceptanceError(f"matrix result path does not follow matrix runner layout: {track_id}")
        _snapshot(snapshots, matrix_path)
        matrix, matrix_raw = _strict_object(matrix_path, f"{track_id} matrix result")
        _schema_validate(matrix, _schema(root, "benchmark-matrix-result.schema.json"), f"{track_id} matrix result")
        _matrix_config_consistent(matrix["matrix_config"], track)
        if matrix.get("outputs") != {"dataset_output_root": track["dataset_output_root"], "benchmark_output_root": track["benchmark_output_root"], "matrix_output_dir": track["matrix_output_dir"]}:
            raise AcceptanceError(f"matrix outputs do not match matrix config: {track_id}")
        matrix_config_path = _safe_file(root, track["matrix_config_path"], "matrix_config_path")
        _snapshot(snapshots, matrix_config_path)
        declared_matrix_config, matrix_config_raw = _strict_object(matrix_config_path, f"{track_id} matrix config")
        if declared_matrix_config != matrix["matrix_config"]:
            raise AcceptanceError(f"matrix config artifact differs from matrix result declaration: {track_id}")
        if matrix["matrix_id"] != track["matrix_id"] or matrix["matrix_id"] != EXPECTED_MATRIX_IDS[track_id]:
            raise AcceptanceError(f"configured matrix ID mismatch: {track_id}")
        _revision_consistent(matrix["code_revision"])
        if matrix["code_revision"] != analyzer_code_revision:
            raise AcceptanceError(f"matrix code revision does not match analyzer execution revision: {track_id}")
        if common_revision is None:
            common_revision = matrix["code_revision"]
        elif matrix["code_revision"] != common_revision:
            raise AcceptanceError("four matrix code revisions are not identical")
        axes = matrix["axes"]
        result_axes_without_expansion = {key: value for key, value in axes.items() if key != "expansion_order"}
        if result_axes_without_expansion != matrix["matrix_config"]["axes"]:
            raise AcceptanceError(f"matrix result axes differ from matrix config axes: {track_id}")
        if axes != EXPECTED_AXES:
            raise AcceptanceError(f"controlled axes are not the fixed axes: {track_id}")
        if common_axes is None:
            common_axes = axes
        elif axes != common_axes:
            raise AcceptanceError("four matrix axes are not identical")
        expected_cells = _expected_cells(axes)
        if len(expected_cells) != 20:
            raise AcceptanceError("controlled acceptance requires exactly 20 cells per matrix")
        if matrix["counts"]["total_cells"] != 20 or len(matrix["cells"]) != 20:
            raise AcceptanceError(f"matrix does not declare exactly 20 cells: {track_id}")
        cells_status = [cell["status"] for cell in matrix["cells"]]
        if matrix["counts"]["successful_cells"] != cells_status.count("success") or matrix["counts"]["partial_cells"] != cells_status.count("partial") or matrix["counts"]["failed_cells"] != cells_status.count("failed") or matrix["counts"]["completed_cells"] != cells_status.count("success") + cells_status.count("partial") or sum(matrix["counts"][key] for key in ("successful_cells", "partial_cells", "failed_cells")) != 20:
            raise AcceptanceError(f"matrix cell counts are inconsistent: {track_id}")
        expected_matrix_status = "failed" if matrix["counts"]["completed_cells"] == 0 else "success" if matrix["counts"]["successful_cells"] == 20 else "partial"
        if matrix["status"] != expected_matrix_status:
            raise AcceptanceError(f"matrix status/counts are inconsistent: {track_id}")
        if [cell["cell_id"] for cell in matrix["cells"]] != [item[0] for item in expected_cells]:
            raise AcceptanceError(f"matrix cell IDs/order do not match axes: {track_id}")
        gen_path = _safe_file(root, track["generator_config_path"], "generator_config_path")
        benchmark_path = _safe_file(root, track["benchmark_config_path"], "benchmark_config_path")
        _snapshot(snapshots, gen_path); _snapshot(snapshots, benchmark_path)
        generator, gen_raw = _strict_object(gen_path, f"{track_id} generator config")
        benchmark, bench_raw = _strict_object(benchmark_path, f"{track_id} benchmark config")
        _schema_validate(generator, _schema(root, "synthetic-generator-config.schema.json"), f"{track_id} generator config")
        _schema_validate(benchmark, _schema(root, "benchmark-run-config.schema.json"), f"{track_id} benchmark config")
        if matrix["base_configs"]["generator"] != {"path": track["generator_config_path"], "sha256": _sha256_bytes(gen_raw)}:
            raise AcceptanceError(f"generator base raw hash/path mismatch: {track_id}")
        if matrix["base_configs"]["benchmark"] != {"path": track["benchmark_config_path"], "sha256": _sha256_bytes(bench_raw)}:
            raise AcceptanceError(f"benchmark base raw hash/path mismatch: {track_id}")
        if common_benchmark is None:
            common_benchmark, common_benchmark_hash = benchmark, _sha256_bytes(bench_raw)
        elif benchmark != common_benchmark or _sha256_bytes(bench_raw) != common_benchmark_hash:
            raise AcceptanceError("benchmark base config is not common across tracks")
        normalized_generator = _canonical_without(generator, "dataset_id", "events")
        if common_generator_normalized is None:
            common_generator_normalized = normalized_generator
        elif normalized_generator != common_generator_normalized:
            raise AcceptanceError("generator semantic diff exceeds dataset_id/events")
        actual_contract = tuple((
            event.get("event_id"), event["equipment_id"], event.get("signal_id"), event["event_type"],
            event["start_sample"], event["end_sample"], event.get("magnitude", 0.0), event.get("enabled")
        ) for event in generator.get("events", []))
        expected_contract = tuple((
            event["event_id"], event["equipment_id"], event["signal_id"], event["event_type"],
            event["start_sample"], event["end_sample"], event["magnitude"], event["enabled"]
        ) for event in track["expected_events"])
        if actual_contract != expected_contract:
            raise AcceptanceError(f"generator event contract mismatch: {track_id}")
        roles = _event_roles(generator)
        for event in track["expected_events"]:
            key = (event["equipment_id"], event["signal_id"], event["event_type"], event["start_sample"], event["end_sample"])
            if roles.get(key) != event["role"]:
                raise AcceptanceError(f"generator event role mismatch: {track_id}")
        matrix_infos[track_id] = {"matrix": matrix, "generator": generator, "benchmark": benchmark, "path": matrix_path, "raw": matrix_raw, "generator_path": gen_path, "benchmark_path": benchmark_path}
    assert common_axes is not None and common_revision is not None and common_benchmark is not None
    if common_benchmark.get("horizon") != 15 or common_benchmark.get("context_length") != 64 or common_benchmark.get("seed") != 42 or common_benchmark.get("target_signal_ids") != ["motor_current", "motor_temperature"] or common_benchmark.get("equipment_ids") != ["motor-01", "conveyor-01"] or common_benchmark.get("past_only_covariate_ids") != ["load_proxy"] or common_benchmark.get("known_future_covariate_ids", []) != [] or common_benchmark.get("validation_origin_stride") != 15 or common_benchmark.get("test_origin_stride") != 15 or common_benchmark.get("max_validation_origins") != 1 or common_benchmark.get("max_test_origins") != 1 or common_benchmark.get("quantiles") != [0.1, 0.5, 0.9] or common_benchmark.get("models") != EXPECTED_BENCHMARK_MODELS:
        raise AcceptanceError("controlled benchmark contract is not the fixed Toto contract")
    tracks_out = []
    all_cell_audits: dict[str, dict[str, Any]] = {}
    expected_groups = len(common_benchmark["models"]) * len(common_benchmark["equipment_ids"]) * len(common_benchmark["target_signal_ids"]) * 80
    all_dataset_data: dict[str, dict[int, dict[str, Any]]] = {}
    for track_id in TRACK_IDS:
        track = tracks_cfg[track_id]
        info = matrix_infos[track_id]
        matrix = info["matrix"]
        datasets = {item["seed"]: item for item in matrix["datasets"]}
        if set(datasets) != set(common_axes["seeds"]):
            raise AcceptanceError(f"dataset seeds do not match axes: {track_id}")
        if len(matrix["datasets"]) != len(datasets) or len({item["dataset_id"] for item in matrix["datasets"]}) != len(datasets) or len({item["dataset_path"] for item in matrix["datasets"]}) != len(datasets) or len({item["dataset_fingerprint"] for item in matrix["datasets"]}) != len(datasets):
            raise AcceptanceError(f"matrix datasets are not unique: {track_id}")
        if [item["seed"] for item in matrix["datasets"]] != list(common_axes["seeds"]):
            raise AcceptanceError(f"matrix dataset order does not match seed axis: {track_id}")
        dataset_data: dict[int, dict[str, Any]] = {}
        dataset_sources: list[dict[str, Any]] = []
        for seed in common_axes["seeds"]:
            entry = datasets[seed]
            dataset_path = _safe_path(root, entry["dataset_path"], "dataset_path")
            dataset_files = [
                _safe_file(root, (dataset_path / name).relative_to(root).as_posix(), f"dataset {name}")
                for name in ("dataset-manifest.json", "fingerprint.json", "observations.jsonl", "events.jsonl", "split-manifest.json")
            ]
            for artifact in dataset_files:
                _snapshot(snapshots, artifact)
            try:
                verified = _verify_dataset(dataset_path, root)
            except Exception as exc:
                raise AcceptanceError(f"dataset quality/fingerprint validation failed: {track_id}/{seed}: {exc}") from exc
            if verified["fingerprint"]["dataset_fingerprint"] != entry["dataset_fingerprint"] or _sha256(dataset_path / "observations.jsonl") != entry["observations_sha256"]:
                raise AcceptanceError(f"dataset fingerprint/observations hash mismatch: {track_id}/{seed}")
            if verified["manifest"]["dataset_id"] != entry["dataset_id"]:
                raise AcceptanceError(f"dataset ID mismatch: {track_id}/{seed}")
            expected_dataset_id = f"{info['generator']['dataset_id']}--{track['matrix_id']}--seed-{seed}"
            if entry["dataset_id"] != expected_dataset_id:
                raise AcceptanceError(f"dataset ID does not follow matrix materialization: {track_id}/{seed}")
            gen_materialized_path = _safe_file(root, entry["generator_config_path"], "materialized generator config")
            expected_gen_path = _safe_path(root, f"{track['matrix_output_dir']}/configs/generators/seed-{seed}.json", "expected materialized generator config")
            expected_dataset_path = _safe_path(root, f"{track['dataset_output_root']}/{track['matrix_id']}/seed-{seed}", "expected dataset path")
            if gen_materialized_path != expected_gen_path or dataset_path != expected_dataset_path:
                raise AcceptanceError(f"dataset/generator path does not follow matrix runner layout: {track_id}/{seed}")
            materialized, materialized_raw = _strict_object(gen_materialized_path, "materialized generator config")
            _schema_validate(materialized, _schema(root, "synthetic-generator-config.schema.json"), "materialized generator config")
            if _canonical_without(materialized, "dataset_id", "seed") != _canonical_without(info["generator"], "dataset_id", "seed") or _event_tuples(materialized) != _event_tuples(info["generator"]):
                raise AcceptanceError(f"materialized generator semantic mismatch: {track_id}/{seed}")
            if materialized.get("seed") != seed or materialized.get("dataset_id") != entry["dataset_id"]:
                raise AcceptanceError(f"materialized generator seed/id mismatch: {track_id}/{seed}")
            if _sha256_bytes(materialized_raw) != entry.get("generator_config_sha256"):
                raise AcceptanceError(f"materialized generator config hash mismatch: {track_id}/{seed}")
            quality_gate = entry.get("quality_gate")
            quality = verified.get("quality")
            if not isinstance(quality_gate, dict) or not isinstance(quality, dict) or quality_gate.get("status") != "pass" or quality_gate.get("observation_record_count") != quality.get("observation_record_count") or quality_gate.get("equipment_count") != quality.get("equipment_count"):
                raise AcceptanceError(f"dataset quality gate evidence mismatch: {track_id}/{seed}")
            _snapshot(snapshots, gen_materialized_path)
            for name, artifact in zip(("dataset-manifest.json", "fingerprint.json", "observations.jsonl", "events.jsonl", "split-manifest.json"), dataset_files):
                dataset_sources.append(_source_record(artifact, root, snapshots, f"dataset-{name}"))
            dataset_data[seed] = verified
        all_dataset_data[track_id] = dataset_data
        if track_id == "covariate-quality":
            _validate_cross_track_truth(all_dataset_data, common_benchmark, common_axes["seeds"])
        cells = []
        cell_by_id = {cell["cell_id"]: cell for cell in matrix["cells"]}
        for expected in _expected_cells(common_axes):
            audit = _cell_result_audit(root=root, track=track, matrix=matrix, cell=cell_by_id[expected[0]], matrix_revision=common_revision, benchmark=common_benchmark, dataset=dataset_data[expected[1]], dataset_entry=datasets[expected[1]], snapshots=snapshots, expected=expected)
            cells.append(audit)
            all_cell_audits[f"{track_id}:{expected[0]}"] = audit
        tracks_out.append({
            "track_id": track_id, "role": track["role"], "matrix_id": matrix["matrix_id"],
            "matrix_result": _source_record(info["path"], root, snapshots, "matrix-result"),
            "source_artifacts": [
                _source_record(info["generator_path"], root, snapshots, "generator-config"),
                _source_record(info["benchmark_path"], root, snapshots, "benchmark-config"),
                _source_record(_safe_file(root, track["matrix_config_path"], "matrix_config_path"), root, snapshots, "matrix-config"),
            ],
            "dataset_sources": dataset_sources,
            "status": "pass" if all(cell["status"] == "pass" for cell in cells) else "blocked", "cells": cells,
        })
    deltas = []
    for degraded in TRACK_IDS[1:]:
        for expected in _expected_cells(common_axes):
            deltas.extend(_paired_deltas(all_cell_audits[f"control:{expected[0]}"], all_cell_audits[f"{degraded}:{expected[0]}"], degraded))
    if any(_overlap(output, source) for source in snapshots):
        raise AcceptanceError("output_dir overlaps a source artifact")
    if _revision(root) != analyzer_code_revision:
        raise AcceptanceError("repository code revision changed during analysis")
    _assert_unchanged(snapshots)
    actual_cell_count = sum(len(track["cells"]) for track in tracks_out)
    actual_group_count = sum(len(cell["groups"]) for track in tracks_out for cell in track["cells"])
    expected_delta_count = len(TRACK_IDS[1:]) * 20 * len(common_benchmark["models"]) * len(common_benchmark["equipment_ids"]) * len(common_benchmark["target_signal_ids"])
    blocked = any(track["status"] != "pass" for track in tracks_out) or any(item["status"] != "paired" for item in deltas) or actual_cell_count != 80 or actual_group_count != expected_groups or len(deltas) != expected_delta_count
    result = {
        "schema_version": "0.1", "result_type": "toto2-controlled-acceptance", "analyzer_id": config["analyzer_id"], "analyzer_code_revision": analyzer_code_revision,
        "analyzer_config": {"kind": "analyzer-config", "path": config_file.resolve().relative_to(root).as_posix(), "sha256": snapshots[config_file.resolve()]},
        "controlled_acceptance_status": "blocked" if blocked else "pass", "cross_model_ranking_allowed": False,
        "pairing": {"key": ["seed", "horizon", "context_length", "model", "equipment_id", "target_signal_id", "origin_sample"], "comparison": "control_to_each_degraded_same_model_group", "truth_unavailable": "inconclusive/no-rank"},
        "tracks": tracks_out, "paired_deltas": deltas,
        "counts": {"tracks": 4, "expected_cells": 80, "cells": actual_cell_count, "expected_groups": expected_groups, "groups": actual_group_count},
        "limitations": ["指定されたmatrix/cell/dataset artifactをsource hashとclean code revision付きで解析した", "合成データは実設備性能や顧客データを示さない", "cross-model rankingは禁止し、controlから各degradedへの同一group paired deltaだけを出力する"],
    }
    _schema_validate(result, _schema(root, "toto2-controlled-acceptance-result.schema.json"), "acceptance result")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".toto2-acceptance.", dir=output.parent))
    try:
        (temporary / "result.json").write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
        (temporary / "summary.md").write_text(_summary(result), encoding="utf-8", newline="\n")
        if _revision(root) != analyzer_code_revision:
            raise AcceptanceError("repository code revision changed before publish")
        _assert_unchanged(snapshots)
        if output.exists():
            raise AcceptanceError(f"refusing to overwrite existing output: {output}")
        temporary.rename(output)
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)
        raise
    return output


__all__ = ["AcceptanceError", "analyze_controlled_acceptance", "validate_acceptance_config"]
