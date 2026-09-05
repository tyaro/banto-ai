"""Deterministic, fail-closed runner for the preregistered anomaly matrix."""

from __future__ import annotations

import hashlib
import inspect
import json
import math
import os
import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from pathlib import PureWindowsPath
from typing import Any, Callable, Mapping
from uuid import uuid4

from . import anomaly_evaluation, anomaly_matrix, quality
from .anomaly_evaluation import evaluate_anomalies
from .benchmark import _revision
from .generator import SIGNALS, expected_catalog, generate_synthetic
from .manifest import ManifestValidationError, validate


SCHEMA_VERSION = "0.1"
RESULT_TYPE = "event-aware-anomaly-matrix"
COMPLETION_MARKER = ".complete"
COMPLETION_MARKER_TYPE = "event-aware-anomaly-matrix-complete"
RESULT_SCHEMA_PATH = "schemas/anomaly-multiseed-matrix-result.schema.json"
ANOMALY_CONFIG_SCHEMA_PATH = "schemas/anomaly-evaluation-config.schema.json"
ANOMALY_RESULT_SCHEMA_PATH = "schemas/anomaly-evaluation-result.schema.json"
DATASET_MANIFEST_SCHEMA_PATH = "schemas/synthetic-dataset-manifest.schema.json"


class AnomalyMatrixRunnerError(ValueError):
    """A matrix run could not be safely completed or published."""


class _GlobalFailure(AnomalyMatrixRunnerError):
    """A provenance, input, path, or schema failure that invalidates the run."""


class _CellSemanticFailure(AnomalyMatrixRunnerError):
    """A semantically invalid result belonging to one cell."""


def _canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise _GlobalFailure(f"value cannot be canonically serialized: {exc}") from exc


def _json_bytes(value: Any) -> bytes:
    return _canonical_json(value) + b"\n"


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _is_link(path: Path) -> bool:
    junction_check = getattr(os.path, "isjunction", None)
    try:
        attributes = int(getattr(path.lstat(), "st_file_attributes", 0))
    except FileNotFoundError:
        attributes = 0
    except OSError:
        return True
    try:
        is_junction = bool(junction_check(path)) if junction_check is not None else False
    except FileNotFoundError:
        is_junction = False
    except OSError:
        return True
    try:
        is_symlink = path.is_symlink()
    except OSError:
        return True
    return is_symlink or is_junction or bool(attributes & 0x0400)


def _parse_json_object_bytes(raw: bytes, label: str, failure_type: type[AnomalyMatrixRunnerError]) -> dict[str, Any]:
    try:
        def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, value in items:
                if key in result:
                    raise ValueError(f"duplicate JSON property: {key}")
                result[key] = value
            return result

        def parse_float(value: str) -> float:
            parsed = float(value)
            if not math.isfinite(parsed):
                raise ValueError(f"non-finite JSON number: {value}")
            return parsed

        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-finite JSON constant: {value}")),
            parse_float=parse_float,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise failure_type(f"{label} is not strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise failure_type(f"{label} must be a JSON object")
    return value


def _strict_json_object(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        if _is_link(path) or not path.is_file():
            raise OSError(f"not a regular file: {path}")
        raw = path.read_bytes()
    except OSError as exc:
        raise _GlobalFailure(f"{label} is not strict UTF-8 JSON: {exc}") from exc
    return _parse_json_object_bytes(raw, label, _GlobalFailure), raw


def _cell_json_object(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        if _is_link(path) or not path.is_file():
            raise OSError(f"not a regular file: {path}")
        raw = path.read_bytes()
    except OSError as exc:
        raise AnomalyMatrixRunnerError(f"{label} is not strict UTF-8 JSON") from exc
    return _parse_json_object_bytes(raw, label, AnomalyMatrixRunnerError), raw


def _jsonl_objects_from_raw(raw: bytes, label: str) -> list[dict[str, Any]]:
    try:
        rows: list[dict[str, Any]] = []
        for line_number, line in enumerate(raw.splitlines(), start=1):
            def parse_float(value: str) -> float:
                parsed = float(value)
                if not math.isfinite(parsed):
                    raise ValueError(f"non-finite JSON number: {value}")
                return parsed

            value = json.loads(
                line.decode("utf-8"),
                object_pairs_hook=lambda pairs: _reject_duplicate_pairs(pairs, label, line_number),
                parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-finite JSON constant: {value}")),
                parse_float=parse_float,
            )
            if not isinstance(value, dict):
                raise ValueError(f"line {line_number} is not an object")
            rows.append(value)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise AnomalyMatrixRunnerError(f"{label} is not strict JSONL: {exc}") from exc
    return rows


def _jsonl_objects(path: Path, label: str) -> tuple[list[dict[str, Any]], bytes]:
    try:
        if _is_link(path) or not path.is_file():
            raise OSError(f"not a regular file: {path}")
        raw = path.read_bytes()
    except OSError as exc:
        raise AnomalyMatrixRunnerError(f"{label} is not strict JSONL: {exc}") from exc
    return _jsonl_objects_from_raw(raw, label), raw


def _assert_contained_path(path: Path, root: Path, label: str, *, must_exist: bool) -> Path:
    root = Path(root).absolute()
    candidate = Path(path).absolute()
    try:
        relative = candidate.relative_to(root).as_posix()
    except ValueError as exc:
        raise _GlobalFailure(f"{label} escaped the repository") from exc
    if _is_link(root) or not root.is_dir():
        raise _GlobalFailure(f"repository root is not a regular directory: {root}")
    cursor = root
    for part in relative.split("/"):
        cursor = cursor / part
        if _is_link(cursor):
            raise _GlobalFailure(f"{label} traversed a symlink, reparse point, or junction")
    try:
        resolved = candidate.resolve()
    except (OSError, RuntimeError) as exc:
        raise _GlobalFailure(f"{label} could not be resolved safely") from exc
    if resolved == root or root not in resolved.parents:
        raise _GlobalFailure(f"{label} escaped the repository")
    if must_exist and not candidate.exists():
        raise _GlobalFailure(f"{label} does not exist")
    if candidate.exists() and resolved != candidate:
        raise _GlobalFailure(f"{label} is not the planned resolved path")
    return resolved


def _tree_snapshot(
    path: Path,
    label: str,
    *,
    containment_root: Path | None = None,
    failure_scope: str = "global",
    capture_files: tuple[str, ...] = (),
) -> dict[str, Any]:
    if containment_root is not None:
        _assert_contained_path(path, containment_root, label, must_exist=True)
    if failure_scope not in ("global", "cell"):
        raise ValueError(f"unsupported tree snapshot failure scope: {failure_scope}")
    failure = _GlobalFailure if failure_scope == "global" else AnomalyMatrixRunnerError
    capture_names = set(capture_files)
    if _is_link(path) or not path.is_dir():
        raise failure(f"{label} must be a regular directory")
    inventory: list[tuple[str, str]] = []
    hashes: dict[str, str] = {}
    captured_bytes: dict[str, bytes] = {}
    pending = [path]
    try:
        while pending:
            directory = pending.pop()
            with os.scandir(directory) as entries:
                for entry in entries:
                    candidate = Path(entry.path)
                    relative = candidate.relative_to(path).as_posix()
                    if _is_link(candidate):
                        raise OSError(f"symlink or junction: {relative}")
                    if entry.is_dir(follow_symlinks=False):
                        inventory.append((relative, "directory"))
                        pending.append(candidate)
                    elif entry.is_file(follow_symlinks=False):
                        inventory.append((relative, "file"))
                        raw = candidate.read_bytes()
                        hashes[relative] = _sha256_bytes(raw)
                        if relative in capture_names:
                            captured_bytes[relative] = raw
                    else:
                        raise OSError(f"non-regular entry: {relative}")
        if set(captured_bytes) != capture_names:
            missing = sorted(capture_names - set(captured_bytes))
            raise OSError(f"captured files are missing: {missing}")
    except (OSError, ValueError) as exc:
        raise failure(f"{label} tree is not a stable regular tree") from exc
    snapshot: dict[str, Any] = {"inventory": tuple(sorted(inventory)), "hashes": dict(sorted(hashes.items()))}
    if capture_names:
        snapshot["_captured_bytes"] = {name: captured_bytes[name] for name in sorted(capture_names)}
    return snapshot


def _assert_tree_unchanged(path: Path, snapshot: Mapping[str, Any], label: str, root: Path) -> None:
    capture_files = tuple(snapshot.get("_captured_bytes", {}))
    current = _tree_snapshot(path, label, containment_root=root, failure_scope="global", capture_files=capture_files)
    if current != dict(snapshot):
        raise _GlobalFailure(f"{label} changed after validation")


def _assert_materialized_config(path: Path, raw: bytes, label: str, root: Path) -> None:
    try:
        _assert_contained_path(path, root, label, must_exist=True)
        if _is_link(path) or not path.is_file() or path.read_bytes() != raw:
            raise OSError("config bytes changed")
    except OSError as exc:
        raise _GlobalFailure(f"{label} changed after materialization") from exc


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]], label: str, line_number: int) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"{label} line {line_number} has duplicate JSON property: {key}")
        result[key] = value
    return result


def _safe_relative(path: Path, root: Path, label: str) -> str:
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError as exc:
        raise _GlobalFailure(f"{label} escaped the repository") from exc
    return _strict_repo_relative(relative, label)


def _strict_repo_relative(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or value.startswith("/") or "\\" in value or PureWindowsPath(value).drive:
        raise _GlobalFailure(f"{label} must be a normalized repository-relative POSIX path")
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise _GlobalFailure(f"{label} must not contain empty, dot, or traversal segments")
    if not (value[0].isascii() and value[0].isalnum()):
        raise _GlobalFailure(f"{label} must start with an ASCII alphanumeric character")
    if any(not (char.isascii() and (char.isalnum() or char in "._/-")) for char in value):
        raise _GlobalFailure(f"{label} contains characters outside the normalized POSIX path contract")
    return value


def _write_exclusive(path: Path, payload: bytes, label: str) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    descriptor: int | None = None
    try:
        descriptor = os.open(path, flags, 0o644)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise AnomalyMatrixRunnerError(f"refusing to overwrite {label}: {path}") from exc
    except OSError as exc:
        raise AnomalyMatrixRunnerError(f"could not write {label}: {path}") from exc
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass


def _place_no_replace(source: Path, target: Path, label: str) -> None:
    try:
        os.link(source, target)
        return
    except FileExistsError as exc:
        raise AnomalyMatrixRunnerError(f"refusing to replace published {label}: {target}") from exc
    except OSError as exc:
        raise AnomalyMatrixRunnerError(f"atomic placement unavailable for {label}") from exc


def _source_entry(root: Path, path: Path, relative: str, label: str) -> tuple[dict[str, Any], dict[str, Any]]:
    value, raw, raw_sha256, canonical_sha256 = anomaly_matrix._load_object_snapshot(path, label)
    return value, {
        "path": relative,
        "raw_sha256": raw_sha256,
        "canonical_sha256": canonical_sha256,
        "_resolved": path,
        "_value": value,
        "_raw": raw,
    }


def _snapshot_inputs(root: Path, config_path: str | Path) -> tuple[dict[str, Any], dict[str, Any]]:
    config_relative = anomaly_matrix._config_relative_path(config_path, root)
    _assert_contained_path(root / config_relative, root, "matrix config", must_exist=True)
    config_resolved = anomaly_matrix._resolve_config_path(config_path, root)
    config, config_source = _source_entry(root, config_resolved, config_relative, "matrix config")
    raw_paths = {
        "matrix_schema": (config.get("schema_path"), "matrix config schema"),
        "base_generator_config": (config.get("base_generator_config_path"), "base generator config"),
        "base_generator_schema": (config.get("base_generator_schema_path"), "base generator schema"),
        "anomaly_config_schema": (ANOMALY_CONFIG_SCHEMA_PATH, "anomaly evaluation config schema"),
        "anomaly_result_schema": (ANOMALY_RESULT_SCHEMA_PATH, "anomaly evaluation result schema"),
        "dataset_manifest_schema": (DATASET_MANIFEST_SCHEMA_PATH, "synthetic dataset manifest schema"),
        "matrix_result_schema": (RESULT_SCHEMA_PATH, "anomaly matrix result schema"),
    }
    sources: dict[str, Any] = {"matrix_config": config_source}
    values: dict[str, Any] = {"matrix_config": config}
    for key, (relative, label) in raw_paths.items():
        _assert_contained_path(root / relative, root, label, must_exist=True)
        path = anomaly_matrix._safe_repo_path(root, relative, label, must_exist=True)
        value, source = _source_entry(root, path, relative, label)
        sources[key] = source
        values[key] = value
    sources["_config_relative"] = config_relative
    return sources, values


def _public_source(source: Mapping[str, Any]) -> dict[str, str]:
    return {key: str(source[key]) for key in ("path", "raw_sha256", "canonical_sha256")}


def _assert_inputs_unchanged(root: Path, sources: Mapping[str, Any], values: Mapping[str, Any], boundary: str) -> None:
    for key, source in sources.items():
        if key.startswith("_"):
            continue
        _assert_contained_path(root / source["path"], root, f"{key} {boundary}", must_exist=True)
        current_path = anomaly_matrix._safe_repo_path(root, source["path"], f"{key} {boundary}", must_exist=True)
        if current_path != source["_resolved"]:
            raise _GlobalFailure(f"{key} path changed at {boundary}")
        current_value, current_raw, current_raw_sha256, current_canonical_sha256 = anomaly_matrix._load_object_snapshot(current_path, f"{key} {boundary}")
        if current_raw != source["_raw"] or current_value != values[key]:
            raise _GlobalFailure(f"{key} content changed at {boundary}")
        if current_raw_sha256 != source["raw_sha256"] or current_canonical_sha256 != source["canonical_sha256"]:
            raise _GlobalFailure(f"{key} digest changed at {boundary}")


def _require_revision(root: Path, expected: Mapping[str, Any] | None = None, boundary: str = "start") -> dict[str, Any]:
    revision = _revision(root)
    if revision.get("status") != "git" or not isinstance(revision.get("head"), str) or len(revision["head"]) != 40 or any(char not in "0123456789abcdef" for char in revision["head"]) or revision.get("dirty") is not False:
        raise _GlobalFailure(f"repository revision is not clean git at {boundary}")
    if expected is not None and revision != dict(expected):
        raise _GlobalFailure(f"repository revision changed at {boundary}")
    return revision


def _layout_event(layout: Mapping[str, Any], event: Mapping[str, Any]) -> dict[str, Any]:
    start = int(layout["mode_start_sample"]) + int(event["start_offset_samples"])
    return {
        "event_id": event["event_id"],
        "event_type": event["event_type"],
        "equipment_id": layout["equipment_id"],
        "signal_id": event["signal_id"],
        "start_sample": start,
        "end_sample": start + int(event["duration_samples"]),
        "magnitude": event["magnitude"],
        "enabled": True,
        "description": f"{event['event_class']}: preregistered anomaly matrix event",
    }


def _materialize_cell(config: Mapping[str, Any], base: Mapping[str, Any], seed: int, layout: Mapping[str, Any], root: Path, output: Path) -> dict[str, Any]:
    layout_index = int(layout["layout_index"])
    cell_id = f"seed-{seed:03d}-layout-{layout_index:02d}-{layout['layout_id']}"
    generator_config = json.loads(json.dumps(base, ensure_ascii=False))
    generator_config["dataset_id"] = f"anomaly-multiseed-v01-{cell_id}"
    generator_config["seed"] = seed
    generator_config["events"] = [_layout_event(layout, event) for event in layout["events"]]
    dataset_path = output / "datasets" / cell_id
    evaluation_path = output / "evaluations" / cell_id
    generator_config_path = output / "configs" / "generator" / f"{cell_id}.json"
    evaluator_config_path = output / "configs" / "evaluator" / f"{cell_id}.json"
    evaluator_config = {
        "schema_version": "0.1",
        "config_type": "event-aware-anomaly-evaluation",
        "analyzer_id": "event-aware-anomaly-v0.1",
        "dataset_path": _safe_relative(dataset_path, root, "dataset path"),
        "output_dir": _safe_relative(evaluation_path, root, "evaluation output path"),
        "target_signal_ids": list(config["targets"]),
        "min_calibration_points": config["detector"]["min_calibration_points"],
        "robust_z_threshold": config["detector"]["robust_z_threshold"],
        "persistence_points": config["detector"]["persistence_points"],
        "detection_grace_points": config["detector"]["detection_grace_points"],
        "event_classifications": [{"event_id": event["event_id"], "event_class": event["event_class"]} for event in layout["events"]],
    }
    return {
        "cell_id": cell_id,
        "seed": seed,
        "seed_sha256": _sha256_bytes(_canonical_json(seed)),
        "layout_id": layout["layout_id"],
        "layout_index": layout_index,
        "layout_canonical_sha256": _sha256_bytes(_canonical_json(layout)),
        "all_layouts_canonical_sha256": _sha256_bytes(_canonical_json(config["layouts"])),
        "generator_config": generator_config,
        "evaluator_config": evaluator_config,
        "paths": {
            "generator_config": generator_config_path,
            "evaluator_config": evaluator_config_path,
            "dataset": dataset_path,
            "evaluation": evaluation_path,
        },
    }


def _assert_cell_paths_contained(cell: Mapping[str, Any], root: Path) -> None:
    for key, label in (
        ("generator_config", "generator config planned"),
        ("evaluator_config", "evaluator config planned"),
        ("dataset", "dataset planned"),
        ("evaluation", "evaluation planned"),
    ):
        path = cell["paths"][key]
        _assert_contained_path(path, root, label, must_exist=False)
        _assert_contained_path(path.parent, root, f"{label} parent", must_exist=True)


def _assert_cell_parents_contained(cell: Mapping[str, Any], root: Path) -> None:
    for key, label in (
        ("generator_config", "generator config planned"),
        ("evaluator_config", "evaluator config planned"),
        ("dataset", "dataset planned"),
        ("evaluation", "evaluation planned"),
    ):
        _assert_contained_path(cell["paths"][key].parent, root, f"{label} parent", must_exist=True)


def _iso_at(start_timestamp: str, sample: int, interval_ms: int) -> str:
    try:
        start = datetime.fromisoformat(start_timestamp.replace("Z", "+00:00"))
        if start.tzinfo is None or start.utcoffset() != timedelta(0):
            raise ValueError("timestamp must be UTC")
        value = start.astimezone(timezone.utc) + sample * timedelta(milliseconds=interval_ms)
        return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    except (TypeError, ValueError) as exc:
        raise AnomalyMatrixRunnerError(f"base start_timestamp is invalid: {exc}") from exc


def _canonical_timestamp(value: Any, label: str) -> tuple[str, datetime]:
    try:
        if not isinstance(value, str) or not value:
            raise ValueError("timestamp must be a non-empty string")
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
            raise ValueError("timestamp must be explicit UTC")
        parsed = parsed.astimezone(timezone.utc)
        return parsed.isoformat(timespec="milliseconds").replace("+00:00", "Z"), parsed
    except (TypeError, ValueError) as exc:
        raise AnomalyMatrixRunnerError(f"{label} is invalid") from exc


def _build_dataset_semantic_ledger(
    cell: Mapping[str, Any],
    observations: list[dict[str, Any]],
    split_manifest: Mapping[str, Any],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    generator_config = cell["generator_config"]
    expected_split_fields = {
        "schema_version": "0.1",
        "manifest_type": "split",
        "dataset_id": generator_config["dataset_id"],
        "generator_version": generator_config["generator_version"],
        "seed": generator_config["seed"],
        "sampling_interval_ms": generator_config["sampling_interval_ms"],
        "sample_count": generator_config["sample_count"],
        "boundary_semantics": "[start,end)",
    }
    if any(split_manifest.get(key) != value for key, value in expected_split_fields.items()):
        raise AnomalyMatrixRunnerError("generated split manifest fields drifted")
    strategies = split_manifest.get("strategies")
    equipment_ids = [item["equipment_id"] for item in generator_config["equipment"]]
    if len(equipment_ids) != len(set(equipment_ids)):
        raise AnomalyMatrixRunnerError("generated equipment inventory is duplicated")
    sample_count = int(generator_config["sample_count"])
    interval_ms = int(generator_config["sampling_interval_ms"])
    split_start = _iso_at(generator_config["start_timestamp"], 0, interval_ms)
    split_end = _iso_at(generator_config["start_timestamp"], sample_count, interval_ms)
    validation_start_sample = max(1, sample_count * 6 // 10)
    test_start_sample = max(2, sample_count * 8 // 10)
    expected_chronological = [
        {
            "split_id": split_id,
            "equipment_ids": equipment_ids,
            "start_timestamp": _iso_at(generator_config["start_timestamp"], start_sample, interval_ms),
            "end_timestamp": _iso_at(generator_config["start_timestamp"], end_sample, interval_ms),
            "record_count": (end_sample - start_sample) * len(equipment_ids),
        }
        for split_id, start_sample, end_sample in (
            ("train", 0, validation_start_sample),
            ("validation", validation_start_sample, test_start_sample),
            ("test", test_start_sample, sample_count),
        )
    ]
    cross_equipment_cut = max(1, len(equipment_ids) * 7 // 10)
    expected_cross_equipment = [
        {
            "split_id": "train",
            "equipment_ids": equipment_ids[:cross_equipment_cut],
            "start_timestamp": split_start,
            "end_timestamp": split_end,
            "record_count": sample_count * cross_equipment_cut,
        },
        {
            "split_id": "test",
            "equipment_ids": equipment_ids[cross_equipment_cut:],
            "start_timestamp": split_start,
            "end_timestamp": split_end,
            "record_count": sample_count * (len(equipment_ids) - cross_equipment_cut),
        },
    ]
    expected_strategies = [
        {"strategy": "chronological", "splits": expected_chronological},
        {"strategy": "cross_equipment", "splits": expected_cross_equipment},
    ]
    if strategies != expected_strategies:
        raise AnomalyMatrixRunnerError("generated split manifest boundaries or record counts drifted")
    split_times: dict[str, tuple[datetime, datetime]] = {}
    for split in expected_chronological:
        _start_value, start = _canonical_timestamp(split["start_timestamp"], "split start timestamp")
        _end_value, end = _canonical_timestamp(split["end_timestamp"], "split end timestamp")
        split_times[split["split_id"]] = (start, end)
    validation_start, validation_end = split_times["validation"]
    test_start, test_end = split_times["test"]
    equipment_set = set(equipment_ids)
    target_signal_ids = _expected_target_signal_ids(cell)
    if len(target_signal_ids) != len(set(target_signal_ids)):
        raise AnomalyMatrixRunnerError("evaluator target signal inventory is duplicated")
    configured_modes = {item["regime"] for item in generator_config["regimes"]}
    profile_keys: set[tuple[str, str, str]] = set()
    score_identities: list[tuple[Any, ...]] = []
    observation_keys: set[tuple[str, str]] = set()
    observations_by_equipment: dict[str, list[dict[str, Any]]] = {equipment_id: [] for equipment_id in equipment_ids}
    last_stamp_by_equipment: dict[str, datetime] = {}
    for row in observations:
        equipment_id = row.get("equipment_id")
        operating_mode = row.get("operating_mode")
        timestamp, stamp = _canonical_timestamp(row.get("timestamp"), "observation timestamp")
        if (
            not isinstance(equipment_id, str)
            or equipment_id not in equipment_set
            or not isinstance(operating_mode, str)
            or operating_mode not in configured_modes
        ):
            raise AnomalyMatrixRunnerError("generated observation identity is invalid")
        if row.get("timestamp") != timestamp:
            raise AnomalyMatrixRunnerError("generated observation timestamp is not canonical")
        observation_key = (equipment_id, timestamp)
        if observation_key in observation_keys:
            raise AnomalyMatrixRunnerError("generated observations contain duplicate equipment timestamps")
        if equipment_id in last_stamp_by_equipment and stamp <= last_stamp_by_equipment[equipment_id]:
            raise AnomalyMatrixRunnerError("generated observations are not chronological per equipment")
        observation_keys.add(observation_key)
        observations_by_equipment[equipment_id].append(row)
        last_stamp_by_equipment[equipment_id] = stamp
        in_validation = validation_start <= stamp < validation_end
        in_test = test_start <= stamp < test_end
        if in_validation or in_test:
            for signal_id in target_signal_ids:
                if signal_id.rsplit(".", 1)[0] == equipment_id:
                    profile_keys.add((equipment_id, signal_id, operating_mode))
        if in_test:
            for signal_id in target_signal_ids:
                if signal_id.rsplit(".", 1)[0] == equipment_id:
                    profile_key = (equipment_id, signal_id, operating_mode)
                    score_identities.append((timestamp, equipment_id, signal_id, operating_mode, profile_key))
    if len(score_identities) != len(set(score_identities)):
        raise AnomalyMatrixRunnerError("generated score identity ledger is duplicated")
    expected_events = cell["generator_config"]["events"]
    expected_by_id = {event["event_id"]: event for event in expected_events}
    actual_by_id: dict[str, dict[str, Any]] = {}
    for event in events:
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or event_id in actual_by_id:
            raise AnomalyMatrixRunnerError("generated dataset event inventory is duplicated or invalid")
        actual_by_id[event_id] = event
    if set(actual_by_id) != set(expected_by_id):
        raise AnomalyMatrixRunnerError("generated dataset event inventory IDs drifted")
    normalized_events: list[dict[str, Any]] = []
    for event_id, expected in expected_by_id.items():
        actual = actual_by_id[event_id]
        expected_values = {
            "event_type": expected["event_type"],
            "equipment_id": expected["equipment_id"],
            "signal_id": expected["signal_id"],
            "start_timestamp": _iso_at(generator_config["start_timestamp"], expected["start_sample"], interval_ms),
            "end_timestamp": _iso_at(generator_config["start_timestamp"], expected["end_sample"], interval_ms),
            "magnitude": expected["magnitude"],
        }
        if any(actual.get(key) != value for key, value in expected_values.items()):
            raise AnomalyMatrixRunnerError(f"generated dataset event inventory drifted: {event_id}")
        _start_value, start = _canonical_timestamp(actual["start_timestamp"], "event start timestamp")
        _end_value, end = _canonical_timestamp(actual["end_timestamp"], "event end timestamp")
        normalized_signal_id = actual["signal_id"]
        if not normalized_signal_id.startswith(f"{actual['equipment_id']}."):
            normalized_signal_id = f"{actual['equipment_id']}.{normalized_signal_id}"
        normalized_events.append(
            {
                "event_id": event_id,
                "event_type": actual["event_type"],
                "equipment_id": actual["equipment_id"],
                "signal_id": normalized_signal_id,
                "start": start,
                "end": end,
            }
        )
    return {
        "profile_keys": tuple(sorted(profile_keys)),
        "score_identities": tuple(sorted(score_identities)),
        "sampling_interval_ms": interval_ms,
        "split_times": split_times,
        "events": tuple(normalized_events),
        "replay_dataset": {
            "manifest": {"sampling_interval_ms": interval_ms},
            "observations": observations_by_equipment,
            "events": tuple(normalized_events),
            "split_times": split_times,
        },
    }


def _validate_dataset(
    cell: Mapping[str, Any],
    base: Mapping[str, Any],
    root: Path,
    schema: Mapping[str, Any],
    generator_config_raw: bytes,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    dataset_path = cell["paths"]["dataset"]
    if _is_link(dataset_path) or not dataset_path.is_dir():
        raise AnomalyMatrixRunnerError(f"generated dataset is not a regular directory: {dataset_path}")
    snapshot_before = _tree_snapshot(
        dataset_path,
        "dataset before validation",
        containment_root=root,
        failure_scope="cell",
        capture_files=("dataset-manifest.json", "generator-config.json", "observations.jsonl", "events.jsonl", "split-manifest.json", "summary.json", "fingerprint.json"),
    )
    captured_bytes = snapshot_before["_captured_bytes"]
    manifest_raw = captured_bytes["dataset-manifest.json"]
    manifest = _parse_json_object_bytes(manifest_raw, "dataset manifest", AnomalyMatrixRunnerError)
    try:
        validate(manifest, schema)
    except ManifestValidationError as exc:
        raise AnomalyMatrixRunnerError(f"generated dataset manifest does not satisfy its schema: {exc}") from exc
    if manifest.get("dataset_id") != cell["generator_config"]["dataset_id"] or manifest.get("seed") != cell["seed"]:
        raise AnomalyMatrixRunnerError("generated dataset manifest identity drifted")
    generator_config = cell["generator_config"]
    expected_manifest_fields = {
        "generator_version": generator_config["generator_version"],
        "seed": generator_config["seed"],
        "sampling_interval_ms": generator_config["sampling_interval_ms"],
        "sample_count": generator_config["sample_count"],
        "data_path": "observations.jsonl",
        "events_path": "events.jsonl",
        "split_manifest_path": "split-manifest.json",
        "fingerprint_path": "fingerprint.json",
        "generator_config_path": "generator-config.json",
        "summary_path": "summary.json",
    }
    if any(manifest.get(key) != value for key, value in expected_manifest_fields.items()):
        raise AnomalyMatrixRunnerError("generated dataset manifest generator fields drifted")
    expected_equipment = [
        {"equipment_id": item["equipment_id"], "equipment_type": item["equipment_type"]}
        for item in generator_config["equipment"]
    ]
    if manifest.get("equipment") != expected_equipment:
        raise AnomalyMatrixRunnerError("generated dataset manifest equipment catalog drifted")
    expected_signals = [
        signal
        for equipment in expected_equipment
        for signal in expected_catalog(equipment["equipment_id"], equipment["equipment_type"], generator_config["sampling_interval_ms"])
    ]
    if manifest.get("signals") != expected_signals:
        raise AnomalyMatrixRunnerError("generated dataset manifest signal catalog drifted")
    generated_config_raw = captured_bytes["generator-config.json"]
    generated_config = _parse_json_object_bytes(generated_config_raw, "generated generator config", AnomalyMatrixRunnerError)
    if generated_config_raw != generator_config_raw:
        raise AnomalyMatrixRunnerError("generated dataset generator config does not match materialized config")
    observations_path = dataset_path / "observations.jsonl"
    events_path = dataset_path / "events.jsonl"
    observations_raw = captured_bytes["observations.jsonl"]
    observations = _jsonl_objects_from_raw(observations_raw, "observations")
    events_raw = captured_bytes["events.jsonl"]
    events = _jsonl_objects_from_raw(events_raw, "events")
    split_raw = captured_bytes["split-manifest.json"]
    split_manifest = _parse_json_object_bytes(split_raw, "split manifest", AnomalyMatrixRunnerError)
    summary_raw = captured_bytes["summary.json"]
    summary = _parse_json_object_bytes(summary_raw, "dataset summary", AnomalyMatrixRunnerError)
    fingerprint_raw = captured_bytes["fingerprint.json"]
    fingerprint = _parse_json_object_bytes(fingerprint_raw, "dataset fingerprint", AnomalyMatrixRunnerError)
    try:
        quality_gate = quality.check_synthetic_dataset_semantics(
            manifest,
            split_manifest,
            generated_config,
            observations,
            events,
            summary,
            fingerprint,
            snapshot_before["hashes"],
        )
    except quality.DatasetQualityError as exc:
        raise AnomalyMatrixRunnerError(f"generated dataset quality gate failed: {exc}") from exc
    dataset_ledger = _build_dataset_semantic_ledger(cell, observations, split_manifest, events)
    dataset_ledger["quality_gate"] = quality_gate
    expected_snapshot_hashes = {name: _sha256_bytes(raw) for name, raw in captured_bytes.items()}
    if any(snapshot_before["hashes"].get(name) != digest for name, digest in expected_snapshot_hashes.items()):
        raise _GlobalFailure("validated dataset evidence did not come from the initial snapshot")
    snapshot_after = _tree_snapshot(
        dataset_path,
        "dataset after validation",
        containment_root=root,
        failure_scope="global",
        capture_files=tuple(captured_bytes),
    )
    if snapshot_after != snapshot_before:
        raise _GlobalFailure("dataset changed during validation")
    sanitized_snapshot = {"inventory": snapshot_after["inventory"], "hashes": snapshot_after["hashes"]}
    evidence = {
        "path": _safe_relative(dataset_path, root, "dataset path"),
        "dataset_id": manifest["dataset_id"],
        "dataset_fingerprint": fingerprint["dataset_fingerprint"],
        "manifest_sha256": _sha256_bytes(manifest_raw),
        "observations_path": _safe_relative(observations_path, root, "observations path"),
        "observations_sha256": _sha256_bytes(observations_raw),
        "observation_record_count": len(observations),
        "equipment_count": len(manifest["equipment"]),
        "event_count": len(events),
    }
    return evidence, sanitized_snapshot, dataset_ledger


def _call_injected(function: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    try:
        signature = inspect.signature(function)
    except (TypeError, ValueError):
        return function(*args, **kwargs)
    accepts_kwargs = any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in signature.parameters.values())
    filtered = kwargs if accepts_kwargs else {key: value for key, value in kwargs.items() if key in signature.parameters}
    return function(*args, **filtered)


def _validate_evaluation(
    cell: Mapping[str, Any],
    evaluation_return: Any,
    root: Path,
    result_schema: Mapping[str, Any],
    sources: Mapping[str, Any],
    revision: Mapping[str, Any],
    dataset: Mapping[str, Any],
    dataset_ledger: Mapping[str, Any],
    evaluator_config_raw_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    expected_path = cell["paths"]["evaluation"]
    returned_path = Path(evaluation_return)
    if not returned_path.is_absolute():
        returned_path = (root / returned_path).absolute()
    if returned_path != expected_path:
        raise _GlobalFailure("evaluator returned a path outside the planned evaluation output")
    if _is_link(returned_path) or not returned_path.is_dir():
        raise AnomalyMatrixRunnerError("evaluator output is not a regular directory")
    snapshot_before = _tree_snapshot(
        returned_path,
        "evaluator output before validation",
        containment_root=root,
        failure_scope="cell",
        capture_files=("result.json", "summary.md", COMPLETION_MARKER),
    )
    result_path = returned_path / "result.json"
    summary_path = returned_path / "summary.md"
    marker_path = returned_path / COMPLETION_MARKER
    captured_bytes = snapshot_before["_captured_bytes"]
    result_raw = captured_bytes["result.json"]
    result = _parse_json_object_bytes(result_raw, "cell evaluator result", AnomalyMatrixRunnerError)
    try:
        validate(result, result_schema)
    except ManifestValidationError as exc:
        raise AnomalyMatrixRunnerError(f"cell evaluator result does not satisfy its schema: {exc}") from exc
    if result.get("status") not in ("pass", "partial", "inconclusive"):
        raise AnomalyMatrixRunnerError("cell evaluator status is invalid")
    summary_raw = captured_bytes["summary.md"]
    marker_raw = captured_bytes[COMPLETION_MARKER]
    marker = _parse_json_object_bytes(marker_raw, "cell evaluator completion marker", AnomalyMatrixRunnerError)
    if set(marker) != {"marker_type", "schema_version", "result_sha256", "summary_sha256"} or marker.get("marker_type") != "event-aware-anomaly-complete" or marker.get("schema_version") != "0.1" or marker.get("result_sha256") != _sha256_bytes(result_raw) or marker.get("summary_sha256") != _sha256_bytes(summary_raw):
        raise AnomalyMatrixRunnerError("cell evaluator completion marker is invalid")
    provenance = result.get("provenance")
    if not isinstance(provenance, dict):
        raise AnomalyMatrixRunnerError("cell evaluator provenance is missing")
    expected = {
        "config": ("config", _safe_relative(cell["paths"]["evaluator_config"], root, "evaluator config path"), evaluator_config_raw_sha256),
        "schema": ("schema", sources["anomaly_result_schema"]["path"], sources["anomaly_result_schema"]["raw_sha256"]),
        "config_schema": ("config_schema", sources["anomaly_config_schema"]["path"], sources["anomaly_config_schema"]["raw_sha256"]),
    }
    for key, (_label, expected_path_value, expected_hash) in expected.items():
        item = provenance.get(key)
        expected_kind = {"config": "anomaly-evaluation-config", "schema": "anomaly-evaluation-result-schema", "config_schema": "anomaly-evaluation-config-schema"}[key]
        if not isinstance(item, dict) or item.get("kind") != expected_kind or item.get("path") != expected_path_value or item.get("sha256") != expected_hash:
            raise _GlobalFailure(f"cell evaluator {key} provenance drifted")
    dataset_provenance = provenance.get("dataset")
    if not isinstance(dataset_provenance, dict) or dataset_provenance.get("path") != dataset["path"] or dataset_provenance.get("dataset_fingerprint") != dataset["dataset_fingerprint"]:
        raise _GlobalFailure("cell evaluator dataset provenance drifted")
    if provenance.get("code_revision") != dict(revision):
        raise _GlobalFailure("cell evaluator code revision provenance drifted")
    _verify_evaluator_cross_fields(result, cell, dataset, dataset_ledger)
    snapshot_after = _tree_snapshot(
        returned_path,
        "evaluator output after validation",
        containment_root=root,
        failure_scope="global",
        capture_files=tuple(captured_bytes),
    )
    if snapshot_after != snapshot_before:
        raise _GlobalFailure("evaluator output changed during validation")
    if snapshot_before["hashes"].get("result.json") != _sha256_bytes(result_raw) or snapshot_before["hashes"].get("summary.md") != _sha256_bytes(summary_raw) or snapshot_before["hashes"].get(COMPLETION_MARKER) != _sha256_bytes(marker_raw):
        raise _GlobalFailure("evaluator evidence did not come from the initial snapshot")
    sanitized_snapshot = {"inventory": snapshot_after["inventory"], "hashes": snapshot_after["hashes"]}
    evidence = {
        "path": _safe_relative(returned_path, root, "evaluation path"),
        "result_path": _safe_relative(result_path, root, "cell result path"),
        "result_sha256": snapshot_before["hashes"]["result.json"],
        "summary_path": _safe_relative(summary_path, root, "cell summary path"),
        "summary_sha256": snapshot_before["hashes"]["summary.md"],
        "completion_marker_path": _safe_relative(marker_path, root, "cell completion marker path"),
        "completion_marker_sha256": snapshot_before["hashes"][COMPLETION_MARKER],
        "status": {"pass": "success", "partial": "partial", "inconclusive": "inconclusive"}[result["status"]],
        "evaluator_status": result["status"],
    }
    return evidence, sanitized_snapshot


def _expected_target_signal_ids(cell: Mapping[str, Any]) -> list[str]:
    equipment_ids = [item["equipment_id"] for item in cell["generator_config"]["equipment"]]
    available = {f"{equipment_id}.{signal_id}" for equipment_id in equipment_ids for signal_id in SIGNALS}
    resolved: list[str] = []
    for raw in cell["evaluator_config"]["target_signal_ids"]:
        candidates = [raw] if raw in available else [f"{equipment_id}.{raw}" for equipment_id in equipment_ids]
        for candidate in candidates:
            if candidate in available and candidate not in resolved:
                resolved.append(candidate)
    return resolved


_EVALUATOR_SEMANTIC_FIELDS = (
    "schema_version",
    "result_type",
    "analyzer_id",
    "status",
    "parameters",
    "profiles",
    "scores",
    "alert_episodes",
    "alert_episode_accounting",
    "incidents",
    "clean_false_alert_episodes",
    "metrics",
    "exclusions",
    "row_counts",
    "limitations",
)


def _replay_evaluator_semantics(cell: Mapping[str, Any], dataset_ledger: Mapping[str, Any]) -> dict[str, Any]:
    """Replay the evaluator contract once per cell; validation cost is intentionally comparable to evaluation."""
    replay_dataset = dataset_ledger.get("replay_dataset")
    if not isinstance(replay_dataset, Mapping):
        raise _CellSemanticFailure("captured dataset replay context is missing")
    target_signal_ids = _expected_target_signal_ids(cell)
    equipment_ids = [item["equipment_id"] for item in cell["generator_config"]["equipment"]]
    classifications: dict[str, str] = {}
    for item in cell["evaluator_config"]["event_classifications"]:
        event_id = item["event_id"]
        if event_id in classifications:
            raise _CellSemanticFailure("cell evaluator event classifications are duplicated")
        classifications[event_id] = item["event_class"]
    expected_event_ids = [event["event_id"] for event in cell["generator_config"]["events"]]
    if len(expected_event_ids) != len(set(expected_event_ids)) or set(classifications) != set(expected_event_ids):
        raise _CellSemanticFailure("cell evaluator event classification inventory does not match generator events")
    evaluator_config = cell["evaluator_config"]
    config = {
        "min_calibration_points": evaluator_config["min_calibration_points"],
        "robust_z_threshold": evaluator_config["robust_z_threshold"],
        "persistence_points": evaluator_config["persistence_points"],
        "detection_grace_points": evaluator_config["detection_grace_points"],
    }
    try:
        profiles, calibration_exclusions = anomaly_evaluation._calibrate_profiles(
            replay_dataset,
            equipment_ids,
            target_signal_ids,
            config,
        )
        scores, episodes, scoring_exclusions = anomaly_evaluation._score_and_alert(
            replay_dataset,
            equipment_ids,
            target_signal_ids,
            profiles,
            config,
        )
        incidents, clean_false_alerts, metrics, event_exclusions = anomaly_evaluation._event_records_and_metrics(
            replay_dataset,
            equipment_ids,
            target_signal_ids,
            classifications,
            episodes,
            config,
            scores,
        )
    except (anomaly_evaluation.AnomalyEvaluationError, KeyError, TypeError, ValueError) as exc:
        raise _CellSemanticFailure("cell evaluator semantics could not be replayed") from exc
    alert_episode_accounting = metrics.pop("_alert_episode_accounting", None)
    if not isinstance(alert_episode_accounting, list):
        raise _CellSemanticFailure("replayed alert accounting is missing")
    availability = metrics["score_availability_by_signal"]
    status = "inconclusive" if (
        calibration_exclusions["profiles_inconclusive"]
        or any(summary["available_points"] == 0 for summary in availability.values())
    ) else ("partial" if not metrics["overall"]["eligible_incidents"] else "pass")
    parameters = {
        "target_signal_ids": target_signal_ids,
        "min_calibration_points": evaluator_config["min_calibration_points"],
        "robust_z_threshold": evaluator_config["robust_z_threshold"],
        "persistence_points": evaluator_config["persistence_points"],
        "detection_grace_points": evaluator_config["detection_grace_points"],
        "sampling_interval_ms": cell["generator_config"]["sampling_interval_ms"],
        "calibration_split": "validation",
        "scoring_split": "test",
        "boundary_semantics": "[start,end)",
    }
    semantic = {
        "schema_version": anomaly_evaluation.SCHEMA_VERSION,
        "result_type": anomaly_evaluation.RESULT_TYPE,
        "analyzer_id": anomaly_evaluation.ANALYZER_ID,
        "status": status,
        "parameters": parameters,
        "profiles": [profiles[key] for key in sorted(profiles)],
        "scores": scores,
        "alert_episodes": episodes,
        "alert_episode_accounting": alert_episode_accounting,
        "incidents": incidents,
        "clean_false_alert_episodes": clean_false_alerts,
        "metrics": metrics,
        "exclusions": {
            "calibration": calibration_exclusions,
            "scoring": scoring_exclusions,
            "events": event_exclusions,
        },
        "row_counts": {
            "dataset_observations": sum(len(rows) for rows in replay_dataset["observations"].values()),
            "score_rows": len(scores),
            "alert_episodes": len(episodes),
            "alert_episode_accounting": len(alert_episode_accounting),
            "incidents": len(incidents),
            "clean_false_alert_episodes": len(clean_false_alerts),
            "clean_false_alert_signal_episodes": metrics["clean_false_alert_signal_episode_count"],
        },
        "limitations": anomaly_evaluation.evaluator_limitations(),
    }
    return semantic


def _verify_evaluator_cross_fields(
    result: Mapping[str, Any],
    cell: Mapping[str, Any],
    dataset: Mapping[str, Any],
    dataset_ledger: Mapping[str, Any],
) -> None:
    provenance = result.get("provenance")
    if not isinstance(provenance, Mapping):
        raise _GlobalFailure("cell evaluator provenance is missing")
    dataset_provenance = provenance.get("dataset")
    expected_dataset = {
        "kind": "synthetic-dataset",
        "path": dataset["path"],
        "dataset_id": cell["generator_config"]["dataset_id"],
        "dataset_fingerprint": dataset["dataset_fingerprint"],
        "manifest_sha256": dataset["manifest_sha256"],
    }
    if dataset_provenance != expected_dataset:
        raise _GlobalFailure("cell evaluator dataset cross-field provenance drifted")
    quality = provenance.get("quality_gate")
    expected_quality = dataset_ledger.get("quality_gate")
    if not isinstance(expected_quality, Mapping) or quality != expected_quality:
        raise _CellSemanticFailure("cell evaluator quality gate cross-fields drifted")
    parameters = result.get("parameters")
    expected_parameters = {
        "target_signal_ids": _expected_target_signal_ids(cell),
        "min_calibration_points": cell["evaluator_config"]["min_calibration_points"],
        "robust_z_threshold": cell["evaluator_config"]["robust_z_threshold"],
        "persistence_points": cell["evaluator_config"]["persistence_points"],
        "detection_grace_points": cell["evaluator_config"]["detection_grace_points"],
        "sampling_interval_ms": cell["generator_config"]["sampling_interval_ms"],
        "calibration_split": "validation",
        "scoring_split": "test",
        "boundary_semantics": "[start,end)",
    }
    if not isinstance(parameters, Mapping) or any(parameters.get(key) != value for key, value in expected_parameters.items()):
        raise _CellSemanticFailure("cell evaluator parameters cross-fields drifted")
    arrays = {
        "scores": result.get("scores"),
        "alert_episodes": result.get("alert_episodes"),
        "alert_episode_accounting": result.get("alert_episode_accounting"),
        "incidents": result.get("incidents"),
        "clean_false_alert_episodes": result.get("clean_false_alert_episodes"),
    }
    metrics = result.get("metrics")
    if not isinstance(metrics, Mapping):
        raise _CellSemanticFailure("cell evaluator metrics are missing")
    target_signal_ids = expected_parameters["target_signal_ids"]
    target_set = set(target_signal_ids)
    equipment_ids = {item["equipment_id"] for item in cell["generator_config"]["equipment"]}
    operating_modes = {item["regime"] for item in cell["generator_config"]["regimes"]}
    profiles = result.get("profiles")
    if not isinstance(profiles, list):
        raise _CellSemanticFailure("cell evaluator profiles are missing")

    def profile_key(value: Any) -> tuple[str, str, str]:
        if not isinstance(value, Mapping) or not all(isinstance(value.get(key), str) and value.get(key) for key in ("equipment_id", "signal_id", "operating_mode")):
            raise _CellSemanticFailure("cell evaluator profile key is invalid")
        return value["equipment_id"], value["signal_id"], value["operating_mode"]

    profile_by_key: dict[tuple[str, str, str], Mapping[str, Any]] = {}
    for profile in profiles:
        if not isinstance(profile, Mapping):
            raise _CellSemanticFailure("cell evaluator profile is invalid")
        key = profile_key(profile.get("profile_key"))
        if key in profile_by_key or key[0] not in equipment_ids or key[1] not in target_set or key[2] not in operating_modes:
            raise _CellSemanticFailure("cell evaluator profile coverage is invalid")
        if profile.get("status") not in ("calibrated", "inconclusive"):
            raise _CellSemanticFailure("cell evaluator profile status is invalid")
        profile_by_key[key] = profile
    scores = arrays["scores"]
    score_profile_keys: set[tuple[str, str, str]] = set()
    score_identities: list[tuple[Any, ...]] = []
    availability_expected: dict[str, dict[str, Any]] = {
        signal_id: {"available_points": 0, "total_points": 0, "availability_ratio": None}
        for signal_id in target_signal_ids
    }
    for score in scores if isinstance(scores, list) else ():
        if not isinstance(score, Mapping) or score.get("signal_id") not in target_set or not isinstance(score.get("available"), bool) or not isinstance(score.get("timestamp"), str):
            raise _CellSemanticFailure("cell evaluator score coverage is invalid")
        key = profile_key(score.get("profile_key"))
        if score.get("equipment_id") not in equipment_ids or score.get("operating_mode") not in operating_modes or key not in profile_by_key or key != (score.get("equipment_id"), score.get("signal_id"), score.get("operating_mode")):
            raise _CellSemanticFailure("cell evaluator score references an uncovered profile")
        score_profile_keys.add(key)
        score_identities.append((score["timestamp"], score["equipment_id"], score["signal_id"], score["operating_mode"], key))
        signal_id = score["signal_id"]
        availability_expected[signal_id]["total_points"] += 1
        if score["available"]:
            availability_expected[signal_id]["available_points"] += 1
            if profile_by_key[key]["status"] != "calibrated":
                raise _CellSemanticFailure("inconclusive profile produced an available score")
    if set(availability_expected) != target_set:
        raise _CellSemanticFailure("cell evaluator profile or target coverage is incomplete")
    expected_profile_keys = set(dataset_ledger["profile_keys"])
    expected_score_identities = tuple(dataset_ledger["score_identities"])
    if set(profile_by_key) != expected_profile_keys or not score_profile_keys.issubset(expected_profile_keys):
        raise _CellSemanticFailure("cell evaluator profile ledger does not match dataset observations")
    if len(score_identities) != len(set(score_identities)) or len(expected_score_identities) != len(set(expected_score_identities)) or set(score_identities) != set(expected_score_identities):
        raise _CellSemanticFailure("cell evaluator score ledger does not match test observations")
    for summary in availability_expected.values():
        if summary["total_points"]:
            summary["availability_ratio"] = summary["available_points"] / summary["total_points"]
    availability = metrics.get("score_availability_by_signal")
    if not isinstance(availability, Mapping) or set(availability) != target_set or any(availability.get(key) != value for key, value in availability_expected.items()):
        raise _CellSemanticFailure("cell evaluator score availability cross-fields drifted")
    profile_inconclusive_count = sum(profile.get("status") == "inconclusive" for profile in profile_by_key.values())
    exclusions = result.get("exclusions")
    calibration = exclusions.get("calibration") if isinstance(exclusions, Mapping) else None
    if not isinstance(calibration, Mapping) or calibration.get("profiles_inconclusive") != profile_inconclusive_count:
        raise _CellSemanticFailure("cell evaluator profile status count drifted")
    row_counts = result.get("row_counts")
    if not isinstance(row_counts, Mapping) or row_counts.get("dataset_observations") != dataset["observation_record_count"]:
        raise _CellSemanticFailure("cell evaluator dataset row count cross-field drifted")
    row_count_keys = {
        "scores": "score_rows",
        "alert_episodes": "alert_episodes",
        "alert_episode_accounting": "alert_episode_accounting",
        "incidents": "incidents",
        "clean_false_alert_episodes": "clean_false_alert_episodes",
    }
    for key, rows in arrays.items():
        if not isinstance(rows, list) or row_counts.get(row_count_keys[key]) != len(rows):
            raise _CellSemanticFailure(f"cell evaluator {key} row count cross-field drifted")
    scoring = exclusions.get("scoring") if isinstance(exclusions, Mapping) else None
    if not isinstance(scoring, Mapping) or scoring.get("total_points") != len(scores) or scoring.get("available_points") != sum(summary["available_points"] for summary in availability_expected.values()) or not isinstance(scoring.get("unavailable_by_reason"), Mapping) or sum(scoring["unavailable_by_reason"].values()) != len(scores) - scoring.get("available_points"):
        raise _CellSemanticFailure("cell evaluator scoring counts cross-fields drifted")
    if row_counts.get("clean_false_alert_signal_episodes") != metrics.get("clean_false_alert_signal_episode_count"):
        raise _CellSemanticFailure("cell evaluator clean false-alert row count cross-field drifted")
    expected_semantic = _replay_evaluator_semantics(cell, dataset_ledger)
    actual_semantic = {key: result.get(key) for key in _EVALUATOR_SEMANTIC_FIELDS}
    try:
        expected_semantic_raw = _canonical_json(expected_semantic)
        actual_semantic_raw = _canonical_json(actual_semantic)
    except _GlobalFailure as exc:
        raise _CellSemanticFailure("cell evaluator semantic payload is not canonicalizable") from exc
    if actual_semantic_raw != expected_semantic_raw:
        raise _CellSemanticFailure("cell evaluator semantic payload drifted from pure replay")


def _safe_error(exc: BaseException, root: Path) -> str:
    value = str(exc).replace("\\", "/")
    return value.replace(str(root).replace("\\", "/"), "<repository>")


def _config_artifact(path: Path, raw: bytes, value: Mapping[str, Any], root: Path, label: str) -> dict[str, str] | None:
    try:
        if _is_link(path) or not path.is_file() or path.read_bytes() != raw:
            return None
        return {
            "path": _safe_relative(path, root, label),
            "raw_sha256": _sha256_bytes(raw),
            "canonical_sha256": _sha256_bytes(_canonical_json(value)),
        }
    except Exception:
        return None


def _cell_failure(
    cell: Mapping[str, Any],
    exc: BaseException,
    root: Path,
    failure_stage: str,
    generator_config_raw: bytes,
    evaluator_config_raw: bytes,
    dataset: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return {
        "cell_id": cell["cell_id"],
        "seed": cell["seed"],
        "seed_sha256": cell["seed_sha256"],
        "layout_id": cell["layout_id"],
        "layout_index": cell["layout_index"],
        "layout_canonical_sha256": cell["layout_canonical_sha256"],
        "all_layouts_canonical_sha256": cell["all_layouts_canonical_sha256"],
        "status": "failed",
        "evaluator_status": None,
        "error_type": type(exc).__name__,
        "reason": f"{failure_stage}_failed",
        "failure_stage": failure_stage,
        "artifacts": {
            "generator_config": _config_artifact(cell["paths"]["generator_config"], generator_config_raw, cell["generator_config"], root, "generator config path"),
            "evaluator_config": _config_artifact(cell["paths"]["evaluator_config"], evaluator_config_raw, cell["evaluator_config"], root, "evaluator config path"),
            "dataset": dataset,
            "evaluation": None,
        },
    }


def _cell_success(cell: Mapping[str, Any], root: Path, generator_config_raw: bytes, evaluator_config_raw: bytes, dataset: Mapping[str, Any], evaluation: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "cell_id": cell["cell_id"],
        "seed": cell["seed"],
        "seed_sha256": cell["seed_sha256"],
        "layout_id": cell["layout_id"],
        "layout_index": cell["layout_index"],
        "layout_canonical_sha256": cell["layout_canonical_sha256"],
        "all_layouts_canonical_sha256": cell["all_layouts_canonical_sha256"],
        "status": evaluation["status"],
        "evaluator_status": evaluation["evaluator_status"],
        "error_type": None,
        "reason": None,
        "failure_stage": None,
        "artifacts": {
            "generator_config": {"path": _safe_relative(cell["paths"]["generator_config"], root, "generator config path"), "raw_sha256": _sha256_bytes(generator_config_raw), "canonical_sha256": _sha256_bytes(_canonical_json(cell["generator_config"]))},
            "evaluator_config": {"path": _safe_relative(cell["paths"]["evaluator_config"], root, "evaluator config path"), "raw_sha256": _sha256_bytes(evaluator_config_raw), "canonical_sha256": _sha256_bytes(_canonical_json(cell["evaluator_config"]))},
            "dataset": dataset,
            "evaluation": evaluation,
        },
    }


def _assert_runtime_snapshot(snapshot: Mapping[str, Any], boundary: str) -> None:
    if snapshot.get("generator_config_raw") is not None:
        _assert_materialized_config(snapshot["generator_config_path"], snapshot["generator_config_raw"], f"generator config at {boundary}", snapshot["repository_root"])
    if snapshot.get("evaluator_config_raw") is not None:
        _assert_materialized_config(snapshot["evaluator_config_path"], snapshot["evaluator_config_raw"], f"evaluator config at {boundary}", snapshot["repository_root"])
    if snapshot.get("dataset") is not None:
        dataset_path, dataset_tree = snapshot["dataset"]
        _assert_tree_unchanged(dataset_path, dataset_tree, f"dataset at {boundary}", snapshot["repository_root"])
    if snapshot.get("evaluation") is not None:
        evaluation_path, evaluation_tree = snapshot["evaluation"]
        _assert_tree_unchanged(evaluation_path, evaluation_tree, f"evaluation output at {boundary}", snapshot["repository_root"])


def _assert_runtime_snapshots(snapshots: Mapping[str, Mapping[str, Any]], boundary: str) -> None:
    for snapshot in snapshots.values():
        _assert_runtime_snapshot(snapshot, boundary)


def _verify_aggregate_result(result: Mapping[str, Any], config: Mapping[str, Any]) -> None:
    cells = result.get("cells")
    if not isinstance(cells, list) or len(cells) != 120:
        raise _GlobalFailure("aggregate cell inventory is not exactly 120 cells")
    ordered_layouts = sorted(config["layouts"], key=lambda item: item["layout_index"])
    expected_ids = [
        f"seed-{seed:03d}-layout-{int(layout['layout_index']):02d}-{layout['layout_id']}"
        for seed in config["seeds"]
        for layout in ordered_layouts
    ]
    actual_ids = [cell.get("cell_id") if isinstance(cell, Mapping) else None for cell in cells]
    if actual_ids != expected_ids:
        raise _GlobalFailure("aggregate cell order or identity drifted")
    all_layouts_hash = _sha256_bytes(_canonical_json(config["layouts"]))
    expected_metadata = [
        {
            "seed": seed,
            "seed_sha256": _sha256_bytes(_canonical_json(seed)),
            "layout_id": layout["layout_id"],
            "layout_index": int(layout["layout_index"]),
            "layout_canonical_sha256": _sha256_bytes(_canonical_json(layout)),
            "all_layouts_canonical_sha256": all_layouts_hash,
        }
        for seed in config["seeds"]
        for layout in ordered_layouts
    ]
    for cell, expected in zip(cells, expected_metadata):
        if not isinstance(cell, Mapping) or any(cell.get(key) != value for key, value in expected.items()):
            raise _GlobalFailure("aggregate cell materialized metadata drifted")
    counts = {status: 0 for status in ("success", "partial", "inconclusive", "failed")}
    fingerprint_by_layout: dict[str, set[str]] = {layout["layout_id"]: set() for layout in config["layouts"]}
    observations_by_layout: dict[str, set[str]] = {layout["layout_id"]: set() for layout in config["layouts"]}
    for cell in cells:
        if not isinstance(cell, Mapping) or cell.get("status") not in counts:
            raise _GlobalFailure("aggregate cell status is invalid")
        status = cell["status"]
        counts[status] += 1
        evaluator_status = cell.get("evaluator_status")
        artifacts = cell.get("artifacts")
        if not isinstance(artifacts, Mapping):
            raise _GlobalFailure("aggregate cell artifacts are missing")
        if status == "failed":
            if evaluator_status is not None or not isinstance(cell.get("failure_stage"), str) or not cell["failure_stage"] or not isinstance(cell.get("error_type"), str) or not cell["error_type"] or not isinstance(cell.get("reason"), str) or not cell["reason"] or artifacts.get("evaluation") is not None:
                raise _GlobalFailure("failed cell status fields are inconsistent")
            failure_stage = cell["failure_stage"]
            if failure_stage not in {"write_configs", "generate_dataset", "validate_dataset", "run_evaluator", "validate_evaluation"}:
                raise _GlobalFailure("failed cell failure stage is invalid")
            if failure_stage != "write_configs" and any(artifacts.get(key) is None for key in ("generator_config", "evaluator_config")):
                raise _GlobalFailure("failed cell is missing materialized config evidence required by its failure stage")
            if failure_stage in ("write_configs", "generate_dataset", "validate_dataset") and artifacts.get("dataset") is not None:
                raise _GlobalFailure("failed cell has dataset evidence beyond its failure stage")
            if failure_stage in ("run_evaluator", "validate_evaluation") and artifacts.get("dataset") is None:
                raise _GlobalFailure("failed cell is missing dataset evidence required by its failure stage")
        else:
            evaluation = artifacts.get("evaluation")
            expected_status_tuple = {
                "success": ("pass", "success", "pass"),
                "partial": ("partial", "partial", "partial"),
                "inconclusive": ("inconclusive", "inconclusive", "inconclusive"),
            }[status]
            actual_status_tuple = (
                evaluator_status,
                evaluation.get("status") if isinstance(evaluation, Mapping) else None,
                evaluation.get("evaluator_status") if isinstance(evaluation, Mapping) else None,
            )
            if actual_status_tuple != expected_status_tuple or cell.get("error_type") is not None or cell.get("reason") is not None or cell.get("failure_stage") is not None:
                raise _GlobalFailure("successful cell status fields are inconsistent")
            if any(artifacts.get(key) is None for key in ("generator_config", "evaluator_config", "dataset", "evaluation")):
                raise _GlobalFailure("completed cell is missing required artifact evidence")
        dataset = artifacts.get("dataset")
        if isinstance(dataset, Mapping):
            layout_id = cell.get("layout_id")
            if layout_id not in fingerprint_by_layout or not isinstance(dataset.get("dataset_fingerprint"), str) or not isinstance(dataset.get("observations_sha256"), str):
                raise _GlobalFailure("cell dataset evidence is inconsistent")
            fingerprint_by_layout[layout_id].add(dataset["dataset_fingerprint"])
            observations_by_layout[layout_id].add(dataset["observations_sha256"])
    expected_counts = {"total": 120, **counts}
    if result.get("counts") != expected_counts:
        raise _GlobalFailure("aggregate counts do not match cell inventory")
    invariants = {
        "all_cells_processed": len(cells) == 120,
        "cell_order": actual_ids == expected_ids,
        "event_inventory": all(isinstance(cell.get("artifacts"), Mapping) and cell["artifacts"].get("dataset") is not None for cell in cells),
        "distinct_dataset_fingerprints_by_layout": all(len(values) == len(config["seeds"]) for values in fingerprint_by_layout.values()),
        "distinct_observations_by_layout": all(len(values) == len(config["seeds"]) for values in observations_by_layout.values()),
    }
    if result.get("invariants") != invariants:
        raise _GlobalFailure("aggregate invariants do not match cell inventory")
    expected_engineering = "pass" if all(invariants.values()) and counts["success"] == 120 else "fail"
    if result.get("engineering_status") != expected_engineering or result.get("status") != ("pass" if expected_engineering == "pass" else "not_complete"):
        raise _GlobalFailure("aggregate status is inconsistent with cell inventory")
    if result.get("run_status") != "complete" or result.get("performance_status") != "not_evaluated":
        raise _GlobalFailure("aggregate run status is inconsistent")


def _output_state(output: Path) -> tuple[str, str]:
    if _is_link(output):
        raise _GlobalFailure(f"output root must not be a symlink or junction: {output}")
    if not output.exists():
        return "absent", ""
    if not output.is_dir():
        raise _GlobalFailure(f"output root must be a directory: {output}")
    marker = output / COMPLETION_MARKER
    if _is_link(marker) or not marker.is_file():
        return "incomplete", "completion marker is missing"
    try:
        marker_value, _ = _strict_json_object(marker, "matrix completion marker")
        result = output / "result.json"
        summary = output / "summary.md"
        if set(marker_value) != {"marker_type", "schema_version", "result_sha256", "summary_sha256"} or marker_value.get("marker_type") != COMPLETION_MARKER_TYPE or marker_value.get("schema_version") != SCHEMA_VERSION or _is_link(result) or _is_link(summary) or not result.is_file() or not summary.is_file() or marker_value.get("result_sha256") != _sha256_bytes(result.read_bytes()) or marker_value.get("summary_sha256") != _sha256_bytes(summary.read_bytes()):
            return "incomplete", "completion marker or payload is inconsistent"
    except (AnomalyMatrixRunnerError, OSError):
        return "incomplete", "completion marker is invalid"
    return "complete", ""


def _quarantine(output: Path) -> Path:
    for _ in range(32):
        candidate = output.parent / f".{output.name}.incomplete-{uuid4().hex}"
        if candidate.exists() or _is_link(candidate):
            continue
        try:
            output.rename(candidate)
            return candidate
        except FileExistsError:
            continue
        except OSError as exc:
            raise _GlobalFailure(f"could not quarantine incomplete output: {output}") from exc
    raise _GlobalFailure("could not allocate a unique incomplete-output quarantine name")


def _claim_output(output: Path, recover_incomplete: bool) -> tuple[Path | None, bool]:
    state, reason = _output_state(output)
    if state == "complete":
        raise AnomalyMatrixRunnerError(f"refusing to overwrite complete output: {output}")
    quarantine: Path | None = None
    if state == "incomplete":
        if not recover_incomplete:
            raise AnomalyMatrixRunnerError(f"existing output is incomplete: {output} ({reason}); pass recover_incomplete=True to quarantine it")
        quarantine = _quarantine(output)
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.mkdir()
    except FileExistsError as exc:
        raise AnomalyMatrixRunnerError(f"refusing to race or overwrite output root: {output}") from exc
    except OSError as exc:
        raise _GlobalFailure(f"could not claim output root: {output}") from exc
    if quarantine is not None:
        recovery = {"schema_version": SCHEMA_VERSION, "recovery_type": "quarantined-incomplete-output", "output_root": output.relative_to(output.parent).as_posix(), "quarantine_path": quarantine.name}
        _write_exclusive(output / "recovery.json", _json_bytes(recovery), "recovery evidence")
    return quarantine, True


def _failure_evidence(output: Path, root: Path, exc: BaseException) -> None:
    target = output / "failure.json"
    if target.exists():
        return
    payload = {"schema_version": SCHEMA_VERSION, "failure_type": type(exc).__name__, "reason": _safe_error(exc, root)}
    try:
        _write_exclusive(target, _json_bytes(payload), "failure evidence")
    except AnomalyMatrixRunnerError:
        pass


def _publish(root: Path, output: Path, result: Mapping[str, Any], verify_before_marker: Callable[[], None]) -> Path:
    result_bytes = _json_bytes(result)
    summary_lines = [
        "# Event-aware anomaly matrix",
        "",
        f"- status: `{result['status']}`",
        f"- run_status: `{result['run_status']}`",
        f"- engineering_status: `{result['engineering_status']}`",
        f"- performance_status: `{result['performance_status']}`",
        f"- cells: {result['counts']['total']} total; {result['counts']['success']} success; {result['counts']['partial']} partial; {result['counts']['inconclusive']} inconclusive; {result['counts']['failed']} failed",
        f"- canonicalization: `{result['provenance']['canonicalization']}`",
        "",
        "## Cell inventory",
        "",
    ]
    for cell in result["cells"]:
        summary_lines.append(f"- `{cell['cell_id']}`: `{cell['status']}`")
    summary_bytes = ("\n".join(summary_lines) + "\n").encode("utf-8")
    marker_bytes = _json_bytes({"marker_type": COMPLETION_MARKER_TYPE, "schema_version": SCHEMA_VERSION, "result_sha256": _sha256_bytes(result_bytes), "summary_sha256": _sha256_bytes(summary_bytes)})
    temporary = Path(tempfile.mkdtemp(prefix=".matrix-publish.", dir=output))
    try:
        _write_exclusive(temporary / "result.json", result_bytes, "matrix result temporary file")
        _write_exclusive(temporary / "summary.md", summary_bytes, "matrix summary temporary file")
        _write_exclusive(temporary / COMPLETION_MARKER, marker_bytes, "matrix completion marker temporary file")
        _place_no_replace(temporary / "result.json", output / "result.json", "matrix result")
        _place_no_replace(temporary / "summary.md", output / "summary.md", "matrix summary")
        verify_before_marker()
        _place_no_replace(temporary / COMPLETION_MARKER, output / COMPLETION_MARKER, "matrix completion marker")
    finally:
        shutil.rmtree(temporary, ignore_errors=True)
    return output


def run_anomaly_matrix(
    config_path: str | Path,
    root: Path,
    *,
    generator: Callable[..., Any] = generate_synthetic,
    evaluator: Callable[..., Any] = evaluate_anomalies,
    recover_incomplete: bool = False,
) -> Path:
    """Run exactly the preregistered 10-seed × 12-layout anomaly matrix."""
    repository = Path(root).expanduser().resolve()
    output: Path | None = None
    claimed = False
    try:
        validation = anomaly_matrix.validate_anomaly_matrix_config(config_path, repository)
        sources, values = _snapshot_inputs(repository, config_path)
        config = values["matrix_config"]
        base = values["base_generator_config"]
        if validation.get("config_canonical_sha256") != sources["matrix_config"]["canonical_sha256"] or validation.get("config_raw_sha256") != sources["matrix_config"]["raw_sha256"] or validation.get("canonicalization") != anomaly_matrix.CANONICALIZATION_ID:
            raise _GlobalFailure("Savepoint A validation provenance does not match input snapshot")
        if validation.get("config_path") != sources["matrix_config"]["path"]:
            raise _GlobalFailure("Savepoint A config path provenance does not match input snapshot")
        for validation_key, source_key in {
            "schema": "matrix_schema",
            "base_generator": "base_generator_config",
            "base_generator_schema": "base_generator_schema",
        }.items():
            validation_source = validation.get(validation_key)
            source = sources[source_key]
            if not isinstance(validation_source, Mapping) or any(validation_source.get(field) != source[field] for field in ("path", "canonical_sha256", "raw_sha256")):
                raise _GlobalFailure(f"Savepoint A {source_key} provenance does not match input snapshot")
        revision = _require_revision(repository, boundary="preflight")
        _assert_contained_path(repository / config["output_root"], repository, "output_root", must_exist=False)
        output = anomaly_matrix._safe_repo_path(repository, config["output_root"], "output_root", must_exist=False)
        _assert_inputs_unchanged(repository, sources, values, "pre-claim")
        _require_revision(repository, revision, "pre-claim")
        _quarantine_path, claimed = _claim_output(output, recover_incomplete)
        category_dirs = [output / "configs" / "generator", output / "configs" / "evaluator", output / "datasets", output / "evaluations"]
        for directory in category_dirs:
            directory.mkdir(parents=True, exist_ok=False)
        if _quarantine_path is not None:
            _assert_inputs_unchanged(repository, sources, values, "post-recovery")
            _require_revision(repository, revision, "post-recovery")
        cells: list[dict[str, Any]] = []
        runtime_snapshots: dict[str, dict[str, Any]] = {}
        layout_fingerprints: dict[str, set[str]] = {layout["layout_id"]: set() for layout in config["layouts"]}
        layout_observation_hashes: dict[str, set[str]] = {layout["layout_id"]: set() for layout in config["layouts"]}
        expected_cell_count = len(config["seeds"]) * len(config["layouts"])
        for seed in config["seeds"]:
            for layout in sorted(config["layouts"], key=lambda item: item["layout_index"]):
                _assert_inputs_unchanged(repository, sources, values, "cell-boundary")
                _require_revision(repository, revision, "cell-boundary")
                cell = _materialize_cell(config, base, seed, layout, repository, output)
                generator_config_raw = _json_bytes(cell["generator_config"])
                evaluator_config_raw = _json_bytes(cell["evaluator_config"])
                dataset: Mapping[str, Any] | None = None
                dataset_snapshot: Mapping[str, Any] | None = None
                dataset_ledger: Mapping[str, Any] | None = None
                evaluation_snapshot: Mapping[str, Any] | None = None
                failure_stage = "write_configs"
                generator_config_written = False
                evaluator_config_written = False
                try:
                    _assert_cell_paths_contained(cell, repository)
                    _write_exclusive(cell["paths"]["generator_config"], generator_config_raw, "generator config")
                    generator_config_written = True
                    _write_exclusive(cell["paths"]["evaluator_config"], evaluator_config_raw, "evaluator config")
                    evaluator_config_written = True
                    _assert_materialized_config(cell["paths"]["generator_config"], generator_config_raw, "generator config after write", repository)
                    _assert_materialized_config(cell["paths"]["evaluator_config"], evaluator_config_raw, "evaluator config after write", repository)
                    failure_stage = "generate_dataset"
                    generated_path = _call_injected(generator, cell["paths"]["generator_config"], cell["paths"]["dataset"], repository)
                    _assert_materialized_config(cell["paths"]["generator_config"], generator_config_raw, "generator config after generator", repository)
                    _assert_materialized_config(cell["paths"]["evaluator_config"], evaluator_config_raw, "evaluator config after generator", repository)
                    _assert_cell_parents_contained(cell, repository)
                    returned_dataset_path = Path(generated_path)
                    if not returned_dataset_path.is_absolute():
                        returned_dataset_path = (repository / returned_dataset_path).absolute()
                    if returned_dataset_path != cell["paths"]["dataset"].absolute():
                        raise _GlobalFailure("generator returned a path outside the planned dataset output")
                    failure_stage = "validate_dataset"
                    dataset, dataset_snapshot, dataset_ledger = _validate_dataset(cell, base, repository, values["dataset_manifest_schema"], generator_config_raw)
                    layout_fingerprints[cell["layout_id"]].add(dataset["dataset_fingerprint"])
                    layout_observation_hashes[cell["layout_id"]].add(dataset["observations_sha256"])
                    evaluation_kwargs = {"recover_incomplete": False, "allowed_output_parent": output / "evaluations"}
                    failure_stage = "run_evaluator"
                    evaluation_return = _call_injected(evaluator, cell["paths"]["evaluator_config"], repository, **evaluation_kwargs)
                    _assert_materialized_config(cell["paths"]["generator_config"], generator_config_raw, "generator config after evaluator", repository)
                    _assert_materialized_config(cell["paths"]["evaluator_config"], evaluator_config_raw, "evaluator config after evaluator", repository)
                    _assert_cell_parents_contained(cell, repository)
                    _assert_tree_unchanged(cell["paths"]["dataset"], dataset_snapshot, "dataset after evaluator", repository)
                    failure_stage = "validate_evaluation"
                    evaluation, evaluation_snapshot = _validate_evaluation(cell, evaluation_return, repository, values["anomaly_result_schema"], sources, revision, dataset, dataset_ledger, _sha256_bytes(evaluator_config_raw))
                    cells.append(_cell_success(cell, repository, generator_config_raw, evaluator_config_raw, dataset, evaluation))
                    runtime_snapshots[cell["cell_id"]] = {
                        "repository_root": repository,
                        "generator_config_path": cell["paths"]["generator_config"],
                        "generator_config_raw": generator_config_raw if generator_config_written else None,
                        "evaluator_config_path": cell["paths"]["evaluator_config"],
                        "evaluator_config_raw": evaluator_config_raw if evaluator_config_written else None,
                        "dataset": (cell["paths"]["dataset"], dataset_snapshot),
                        "evaluation": (cell["paths"]["evaluation"], evaluation_snapshot),
                    }
                except _GlobalFailure:
                    raise
                except Exception as exc:
                    _assert_cell_parents_contained(cell, repository)
                    if generator_config_written:
                        _assert_materialized_config(cell["paths"]["generator_config"], generator_config_raw, "generator config after cell failure", repository)
                    if evaluator_config_written:
                        _assert_materialized_config(cell["paths"]["evaluator_config"], evaluator_config_raw, "evaluator config after cell failure", repository)
                    cells.append(_cell_failure(cell, exc, repository, failure_stage, generator_config_raw, evaluator_config_raw, dataset))
                    runtime_snapshots[cell["cell_id"]] = {
                        "repository_root": repository,
                        "generator_config_path": cell["paths"]["generator_config"],
                        "generator_config_raw": generator_config_raw if generator_config_written else None,
                        "evaluator_config_path": cell["paths"]["evaluator_config"],
                        "evaluator_config_raw": evaluator_config_raw if evaluator_config_written else None,
                        "dataset": (cell["paths"]["dataset"], dataset_snapshot) if dataset_snapshot is not None else None,
                        "evaluation": (cell["paths"]["evaluation"], evaluation_snapshot) if evaluation_snapshot is not None else None,
                    }
                _assert_runtime_snapshot(runtime_snapshots[cell["cell_id"]], "cell-completion")
                _assert_inputs_unchanged(repository, sources, values, "cell-completion")
                _require_revision(repository, revision, "cell-completion")
                # Replay inputs are cell-local validation state; do not retain parsed observations or events in runtime snapshots.
                if isinstance(dataset_ledger, dict):
                    dataset_ledger.pop("replay_dataset", None)
        if len(cells) != expected_cell_count:
            raise _GlobalFailure("matrix did not process the fixed cell count")
        distinct_fingerprints = all(len(layout_fingerprints[layout_id]) == len(config["seeds"]) for layout_id in layout_fingerprints)
        distinct_observations = all(len(layout_observation_hashes[layout_id]) == len(config["seeds"]) for layout_id in layout_observation_hashes)
        order_ok = [cell["cell_id"] for cell in cells] == [
            _materialize_cell(config, base, seed, layout, repository, output)["cell_id"]
            for seed in config["seeds"]
            for layout in sorted(config["layouts"], key=lambda item: item["layout_index"])
        ]
        success_count = sum(cell["status"] == "success" for cell in cells)
        partial_count = sum(cell["status"] == "partial" for cell in cells)
        inconclusive_count = sum(cell["status"] == "inconclusive" for cell in cells)
        failed_count = sum(cell["status"] == "failed" for cell in cells)
        invariants = {
            "all_cells_processed": len(cells) == 120,
            "cell_order": order_ok,
            "event_inventory": all(cell["artifacts"] is not None and cell["artifacts"]["dataset"] is not None for cell in cells),
            "distinct_dataset_fingerprints_by_layout": distinct_fingerprints,
            "distinct_observations_by_layout": distinct_observations,
        }
        if not all(invariants.values()):
            engineering_status = "fail" if failed_count or not distinct_fingerprints or not distinct_observations else "not_complete"
        else:
            engineering_status = "pass" if success_count == 120 else "fail"
        result = {
            "schema_version": SCHEMA_VERSION,
            "result_type": RESULT_TYPE,
            "matrix_id": config["matrix_id"],
            "status": "pass" if engineering_status == "pass" else "not_complete",
            "run_status": "complete",
            "engineering_status": engineering_status,
            "performance_status": "not_evaluated",
            "provenance": {
                "canonicalization": anomaly_matrix.CANONICALIZATION_ID,
                "inputs": {key: _public_source(value) for key, value in sources.items() if not key.startswith("_")},
                "code_revision": revision,
                "recovery": {"recovered_incomplete": _quarantine_path is not None},
            },
            "counts": {"total": len(cells), "success": success_count, "partial": partial_count, "inconclusive": inconclusive_count, "failed": failed_count},
            "invariants": invariants,
            "cells": cells,
            "limitations": [
                "Savepoint Bはsynthetic anomaly matrixのengineering runnerであり、実設備性能を示さない。",
                "performance_statusは常にnot_evaluatedであり、bootstrap、CI、promotion gate、metric threshold判定は実行しない。",
                "customer data、checkpoint、weights、control write、Banto Hub writeは使用しない。",
            ],
        }
        try:
            validate(result, values["matrix_result_schema"])
        except ManifestValidationError as exc:
            raise _GlobalFailure(f"matrix result does not satisfy its schema: {exc}") from exc
        _verify_aggregate_result(result, config)
        _assert_runtime_snapshots(runtime_snapshots, "aggregate")
        _assert_inputs_unchanged(repository, sources, values, "aggregate-marker")
        _require_revision(repository, revision, "aggregate-marker")
        return _publish(repository, output, result, lambda: (_verify_aggregate_result(result, config), _assert_runtime_snapshots(runtime_snapshots, "before-marker"), _assert_inputs_unchanged(repository, sources, values, "before-marker"), _require_revision(repository, revision, "before-marker")))
    except BaseException as exc:
        if claimed and output is not None:
            _failure_evidence(output, repository, exc)
        if isinstance(exc, AnomalyMatrixRunnerError):
            raise
        raise AnomalyMatrixRunnerError(f"anomaly matrix run failed: {_safe_error(exc, repository)}") from exc


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="run_anomaly_matrix.py", description="Run the fixed event-aware anomaly matrix")
    parser.add_argument("--config", required=True, help="fixed matrix config")
    parser.add_argument("--root", default=None, help="repository root")
    parser.add_argument("--recover-incomplete", action="store_true", help="quarantine an incomplete output root before starting")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[2]
    try:
        output = run_anomaly_matrix(args.config, root, recover_incomplete=args.recover_incomplete)
    except (AnomalyMatrixRunnerError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print(f"Event-aware anomaly matrix: {output}")
    return 0


__all__ = ["AnomalyMatrixRunnerError", "run_anomaly_matrix"]
