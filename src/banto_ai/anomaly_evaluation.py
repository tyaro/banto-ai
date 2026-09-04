"""Event-aware anomaly evaluation v0.1 for synthetic datasets.

This module evaluates a causal one-step residual score separately from the
forecast benchmark.  It is a contract checker for research artifacts, not a
production alerting implementation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path, PureWindowsPath
from typing import Any, Callable, Iterable, Mapping
from uuid import uuid4

from .benchmark import _revision
from .event_slices import EventSliceError, _parse_time, _verify_dataset
from .manifest import ManifestValidationError, validate


class AnomalyEvaluationError(ValueError):
    """Anomaly evaluation input, semantic contract, or publish violation."""


SCHEMA_VERSION = "0.1"
CONFIG_TYPE = "event-aware-anomaly-evaluation"
ANALYZER_ID = "event-aware-anomaly-v0.1"
RESULT_TYPE = "event-aware-anomaly-evaluation"
EVENT_CLASSES = ("machine_fault", "sensor_fault", "data_quality", "ignored")
POSITIVE_CLASSES = frozenset(("machine_fault", "sensor_fault"))
COMPLETION_MARKER = ".complete"
COMPLETION_MARKER_TYPE = "event-aware-anomaly-complete"


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
        if _is_link(path) or not path.is_file():
            raise OSError(f"not a regular file: {path}")
        raw = path.read_bytes()
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=lambda constant: (_ for _ in ()).throw(ValueError(constant)),
            parse_float=lambda number: float(number) if math.isfinite(float(number)) else (_ for _ in ()).throw(ValueError(number)),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise AnomalyEvaluationError(f"{label} is not strict UTF-8 JSON: {exc}") from exc
    return value, raw


def _strict_object(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    value, raw = _strict_json(path, label)
    if not isinstance(value, dict):
        raise AnomalyEvaluationError(f"{label} must be a JSON object")
    return value, raw


def _load_schema(root: Path, name: str) -> tuple[dict[str, Any], bytes]:
    schema_path = _safe_repo_path(root, f"schemas/{name}", f"schema {name}", must_exist=True)
    value, raw = _strict_object(schema_path, f"schema {name}")
    return value, raw


def _validate_schema(value: Any, schema: Mapping[str, Any], label: str) -> None:
    try:
        validate(value, dict(schema))
    except ManifestValidationError as exc:
        raise AnomalyEvaluationError(f"{label} does not satisfy its schema: {exc}") from exc


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha256(path: Path) -> str:
    try:
        if _is_link(path) or not path.is_file():
            raise OSError(f"not a regular file: {path}")
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise AnomalyEvaluationError(f"file is unreadable: {path}") from exc


def _canonical_json(value: Any) -> bytes:
    try:
        return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise AnomalyEvaluationError(f"non-finite or non-serializable output: {exc}") from exc


def _median(values: Iterable[float]) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise AnomalyEvaluationError("median requires at least one value")
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def _canonical_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _parse_dataset_time(value: Any, label: str) -> datetime:
    try:
        return _parse_time(value, label)
    except EventSliceError as exc:
        raise AnomalyEvaluationError(str(exc)) from exc


def _safe_relative(raw: Any, label: str) -> str:
    if not isinstance(raw, str) or not raw or raw.startswith("/") or "\\" in raw or PureWindowsPath(raw).drive:
        raise AnomalyEvaluationError(f"{label} must be a repository-relative POSIX path")
    parts = raw.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise AnomalyEvaluationError(f"{label} must be normalized and traversal-free")
    return raw


def _is_link(path: Path) -> bool:
    junction_check = getattr(os.path, "isjunction", None)
    return path.is_symlink() or bool(junction_check(path) if junction_check is not None else False)


def _safe_repo_path(root: Path, raw: Any, label: str, *, must_exist: bool) -> Path:
    relative = _safe_relative(raw, label)
    root = root.resolve()
    cursor = root
    for part in relative.split("/"):
        cursor = cursor / part
        if _is_link(cursor):
            raise AnomalyEvaluationError(f"{label} cannot traverse a symlink")
    resolved = (root / relative).resolve()
    if resolved == root or root not in resolved.parents:
        raise AnomalyEvaluationError(f"{label} must remain inside repository")
    if must_exist and not resolved.exists():
        raise AnomalyEvaluationError(f"{label} does not exist: {relative}")
    return resolved


def _resolve_config_file(config_path: str | Path, root: Path) -> Path:
    candidate = Path(config_path).expanduser()
    if candidate.is_absolute():
        try:
            # Keep the lexical path here.  Resolving before _safe_repo_path
            # would make an in-repository symlink indistinguishable from its
            # target and would defeat the symlink policy.
            relative = candidate.absolute().relative_to(root.resolve()).as_posix()
        except ValueError as exc:
            raise AnomalyEvaluationError("config must be a repository-local regular file") from exc
    else:
        relative = candidate.as_posix()
    path = _safe_repo_path(root, relative, "config_path", must_exist=True)
    if _is_link(path) or not path.is_file():
        raise AnomalyEvaluationError("config must be a repository-local regular file")
    return path


def _resolve_output(root: Path, raw: Any) -> Path:
    output = _safe_repo_path(root, raw, "output_dir", must_exist=False)
    artifacts = (root / "artifacts").resolve()
    if output == artifacts or output.parent != artifacts:
        raise AnomalyEvaluationError("output_dir must be a new directory directly below artifacts")
    return output


def _inventory_tree(root: Path) -> tuple[tuple[str, str], ...]:
    if _is_link(root) or not root.is_dir():
        raise AnomalyEvaluationError(f"dataset must be a regular directory without symlinks: {root}")
    entries: list[tuple[str, str]] = []
    pending = [root]
    try:
        while pending:
            directory = pending.pop()
            for entry in os.scandir(directory):
                path = Path(entry.path)
                if _is_link(path):
                    raise AnomalyEvaluationError(f"dataset contains a symlink: {path}")
                if entry.is_dir(follow_symlinks=False):
                    entries.append((path.relative_to(root).as_posix(), "directory"))
                    pending.append(path)
                elif entry.is_file(follow_symlinks=False):
                    entries.append((path.relative_to(root).as_posix(), "file"))
                else:
                    raise AnomalyEvaluationError(f"dataset contains a non-regular entry: {path}")
    except OSError as exc:
        raise AnomalyEvaluationError(f"dataset inventory is unreadable: {root}") from exc
    return tuple(sorted(entries))


def _inventory_hashes(root: Path, inventory: tuple[tuple[str, str], ...]) -> dict[str, str]:
    result: dict[str, str] = {}
    for relative, kind in inventory:
        if kind == "file":
            result[relative] = _sha256(root / relative)
    return result


def _assert_input_unchanged(root: Path, inventory: tuple[tuple[str, str], ...], hashes: Mapping[str, str]) -> None:
    current_inventory = _inventory_tree(root)
    if current_inventory != inventory:
        raise AnomalyEvaluationError(f"dataset inventory changed during analysis: {root}")
    current_hashes = _inventory_hashes(root, current_inventory)
    if current_hashes != dict(hashes):
        raise AnomalyEvaluationError(f"dataset source changed during analysis: {root}")


def _snapshot_dataset_fingerprint(dataset_path: Path) -> str:
    fingerprint, _ = _strict_object(dataset_path / "fingerprint.json", "dataset fingerprint")
    value = fingerprint.get("dataset_fingerprint")
    if not isinstance(value, str) or not value:
        raise AnomalyEvaluationError("dataset fingerprint snapshot is invalid")
    return value


def _write_fsync(path: Path, payload: bytes, label: str) -> None:
    try:
        with path.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise AnomalyEvaluationError(f"{label} could not be durably written: {path}") from exc


def _place_no_replace(source: Path, target: Path) -> None:
    try:
        os.link(source, target)
    except FileExistsError as exc:
        raise AnomalyEvaluationError(f"refusing to replace published file: {target}") from exc
    except OSError:
        try:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
            descriptor = os.open(target, flags, 0o644)
            with os.fdopen(descriptor, "wb") as handle, source.open("rb") as source_handle:
                shutil.copyfileobj(source_handle, handle)
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError as exc:
            raise AnomalyEvaluationError(f"refusing to replace published file: {target}") from exc
        except OSError as exc:
            try:
                target.unlink(missing_ok=True)
            except OSError as cleanup_error:
                exc.add_note(f"incomplete output cleanup failed: {cleanup_error!r}")
            raise AnomalyEvaluationError(f"could not place published file: {target}") from exc


def _best_effort_fsync_directory(path: Path, label: str) -> None:
    if os.name == "nt":
        return
    descriptor: int | None = None
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        os.fsync(descriptor)
    except OSError as exc:
        warnings.warn(f"{label} directory fsync failed for {path}: {exc}", RuntimeWarning, stacklevel=2)
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError as exc:
                warnings.warn(f"{label} directory close failed for {path}: {exc}", RuntimeWarning, stacklevel=2)


def _event_ids_at(events: Iterable[Mapping[str, Any]], equipment_id: str, stamp: datetime) -> frozenset[str]:
    return frozenset(
        str(event["event_id"])
        for event in events
        if event["equipment_id"] == equipment_id and event["start"] <= stamp < event["end"]
    )


def _event_timestamp_overlap(events: Iterable[Mapping[str, Any]], equipment_id: str, stamp: datetime) -> bool:
    return bool(_event_ids_at(events, equipment_id, stamp))


def _signal_value(row: Mapping[str, Any], signal_id: str) -> tuple[str, float | None]:
    logical = signal_id.rsplit(".", 1)[-1]
    quality = row["quality"].get(logical)
    value = row["signals"].get(logical, {}).get("value")
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)):
        return str(quality), float(value)
    return str(quality), None


def _residual_at(
    rows: list[Mapping[str, Any]], index: int, signal_id: str, interval: timedelta, events: Iterable[Mapping[str, Any]] = ()
) -> tuple[float | None, str | None, float | None, float | None]:
    current_quality, current_value = _signal_value(rows[index], signal_id)
    previous_value: float | None = None
    if current_quality != "ok":
        return None, "quality_non_ok", current_value, previous_value
    if current_value is None:
        return None, "nonfinite_value", current_value, previous_value
    if index == 0:
        return None, "no_previous_observation", current_value, previous_value
    previous_quality, previous_value = _signal_value(rows[index - 1], signal_id)
    current_stamp = _parse_dataset_time(rows[index]["timestamp"], "current observation timestamp")
    previous_stamp = _parse_dataset_time(rows[index - 1]["timestamp"], "previous observation timestamp")
    if current_stamp - previous_stamp != interval:
        return None, "gap", current_value, previous_value
    if previous_quality != "ok":
        return None, "previous_quality_non_ok", current_value, previous_value
    if previous_value is None:
        return None, "previous_nonfinite_value", current_value, previous_value
    equipment_id = rows[index - 1].get("equipment_id", signal_id.rsplit(".", 1)[0])
    previous_event_ids = _event_ids_at(events, equipment_id, previous_stamp)
    current_event_ids = _event_ids_at(events, equipment_id, current_stamp)
    if previous_event_ids and not previous_event_ids.issubset(current_event_ids):
        return None, "previous_event_overlap", current_value, previous_value
    if str(rows[index].get("operating_mode")) != str(rows[index - 1].get("operating_mode")):
        return None, "mode_boundary", current_value, previous_value
    residual = current_value - previous_value
    if not math.isfinite(residual):
        return None, "nonfinite_residual", current_value, previous_value
    return residual, None, current_value, previous_value


def _resolve_targets(config: Mapping[str, Any], dataset: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    equipment_ids = [item["equipment_id"] for item in dataset["manifest"]["equipment"]]
    signals = dataset["signals"]
    raw_targets = config["target_signal_ids"]
    if len(raw_targets) != len(set(raw_targets)):
        raise AnomalyEvaluationError("target_signal_ids must be unique")
    resolved: list[str] = []
    for raw in raw_targets:
        if not isinstance(raw, str) or not raw:
            raise AnomalyEvaluationError("target_signal_ids must contain non-empty strings")
        candidates = [raw] if raw in signals else [f"{equipment}.{raw}" for equipment in equipment_ids]
        matched = [candidate for candidate in candidates if candidate in signals]
        if not matched:
            raise AnomalyEvaluationError(f"configured target signal is unknown: {raw}")
        for signal_id in matched:
            if signals[signal_id].get("role") != "target":
                raise AnomalyEvaluationError(f"configured target is not a target signal: {signal_id}")
            if signal_id not in resolved:
                resolved.append(signal_id)
    if not resolved:
        raise AnomalyEvaluationError("at least one configured target signal is required")
    return equipment_ids, resolved


def _validate_config(config: Mapping[str, Any], root: Path, dataset: Mapping[str, Any]) -> tuple[list[str], list[str], dict[str, str]]:
    schema, _ = _load_schema(root, "anomaly-evaluation-config.schema.json")
    _validate_schema(config, schema, "anomaly evaluation config")
    if config.get("analyzer_id") != ANALYZER_ID or config.get("config_type") != CONFIG_TYPE:
        raise AnomalyEvaluationError("anomaly evaluation config identity is invalid")
    equipment_ids, target_signal_ids = _resolve_targets(config, dataset)
    event_ids = [event["event_id"] for event in dataset["events"]]
    if len(event_ids) != len(set(event_ids)):
        raise AnomalyEvaluationError("dataset event IDs must be unique")
    classifications: dict[str, str] = {}
    for item in config["event_classifications"]:
        event_id = item["event_id"]
        if event_id in classifications:
            raise AnomalyEvaluationError(f"event classification is duplicated: {event_id}")
        if event_id not in event_ids:
            raise AnomalyEvaluationError(f"event classification references unknown event: {event_id}")
        event_class = item["event_class"]
        if event_class not in EVENT_CLASSES:
            raise AnomalyEvaluationError(f"event class is invalid: {event_class}")
        classifications[event_id] = event_class
    if set(classifications) != set(event_ids):
        missing = sorted(set(event_ids) - set(classifications))
        raise AnomalyEvaluationError(f"event classifications must exactly partition dataset events; missing={missing}")
    return equipment_ids, target_signal_ids, classifications


def _profile_key(equipment_id: str, signal_id: str, operating_mode: str) -> tuple[str, str, str]:
    return equipment_id, signal_id, operating_mode


def _profile_key_json(key: tuple[str, str, str]) -> dict[str, str]:
    return {"equipment_id": key[0], "signal_id": key[1], "operating_mode": key[2]}


def _calibrate_profiles(
    dataset: Mapping[str, Any], equipment_ids: list[str], target_signal_ids: list[str], config: Mapping[str, Any]
) -> tuple[dict[tuple[str, str, str], dict[str, Any]], dict[str, int]]:
    validation_start, validation_end = dataset["split_times"]["validation"]
    test_start, test_end = dataset["split_times"]["test"]
    interval = timedelta(milliseconds=dataset["manifest"]["sampling_interval_ms"])
    events = dataset["events"]
    points: dict[tuple[str, str, str], list[float]] = {}
    excluded: dict[tuple[str, str, str], dict[str, int]] = {}
    total_candidates = 0
    total_event_overlap = 0
    total_non_ok = 0
    total_unavailable = 0
    total_nonfinite = 0
    modes: dict[str, set[str]] = {equipment: set() for equipment in equipment_ids}
    for equipment_id in equipment_ids:
        rows = dataset["observations"].get(equipment_id, [])
        for index, row in enumerate(rows):
            stamp = _parse_dataset_time(row["timestamp"], "validation observation timestamp")
            # Keep a complete profile ledger for every mode that will be
            # scored.  A test-only mode is deliberately represented as an
            # inconclusive profile instead of silently disappearing.
            if validation_start <= stamp < validation_end or test_start <= stamp < test_end:
                modes[equipment_id].add(str(row["operating_mode"]))
            if not validation_start <= stamp < validation_end:
                continue
            mode = row["operating_mode"]
            for signal_id in target_signal_ids:
                if signal_id.rsplit(".", 1)[0] != equipment_id:
                    continue
                key = _profile_key(equipment_id, signal_id, mode)
                points.setdefault(key, [])
                counts = excluded.setdefault(key, {"event_overlap": 0, "quality_non_ok": 0, "residual_unavailable": 0, "nonfinite": 0})
                total_candidates += 1
                previous_stamp = (
                    _parse_dataset_time(rows[index - 1]["timestamp"], "previous validation observation timestamp")
                    if index
                    else None
                )
                if _event_timestamp_overlap(events, equipment_id, stamp) or (
                    previous_stamp is not None and _event_timestamp_overlap(events, equipment_id, previous_stamp)
                ):
                    counts["event_overlap"] += 1
                    total_event_overlap += 1
                    continue
                residual, reason, _current, _previous = _residual_at(rows, index, signal_id, interval, events)
                if residual is None:
                    if reason in ("quality_non_ok", "previous_quality_non_ok"):
                        counts["quality_non_ok"] += 1
                        total_non_ok += 1
                    elif reason in ("nonfinite_value", "previous_nonfinite_value", "nonfinite_residual"):
                        counts["nonfinite"] += 1
                        total_nonfinite += 1
                    else:
                        counts["residual_unavailable"] += 1
                        total_unavailable += 1
                    continue
                points[key].append(residual)

    profiles: dict[tuple[str, str, str], dict[str, Any]] = {}
    for equipment_id in equipment_ids:
        for signal_id in target_signal_ids:
            if signal_id.rsplit(".", 1)[0] != equipment_id:
                continue
            for mode in sorted(modes[equipment_id]):
                key = _profile_key(equipment_id, signal_id, mode)
                values = points.get(key, [])
                counts = excluded.get(key, {"event_overlap": 0, "quality_non_ok": 0, "residual_unavailable": 0, "nonfinite": 0})
                profile: dict[str, Any] = {
                    "profile_key": _profile_key_json(key),
                    "status": "inconclusive",
                    "calibration_point_count": len(values),
                    "excluded_counts": dict(counts),
                    "center": None,
                    "mad": None,
                    "scale": None,
                    "reason": None,
                }
                if len(values) < config["min_calibration_points"]:
                    profile["reason"] = "min_calibration_points_not_met"
                else:
                    center = _median(values)
                    mad = _median([abs(value - center) for value in values])
                    scale = 1.4826 * mad
                    if not all(math.isfinite(value) for value in (center, mad, scale)):
                        profile["reason"] = "nonfinite_profile"
                    elif mad == 0.0 or scale == 0.0:
                        profile["reason"] = "mad_zero"
                    else:
                        profile.update({"status": "calibrated", "center": center, "mad": mad, "scale": scale})
                profiles[key] = profile
    summary = {
        "total_candidate_points": total_candidates,
        "event_overlap": total_event_overlap,
        "quality_non_ok": total_non_ok,
        "residual_unavailable": total_unavailable,
        "nonfinite": total_nonfinite,
        "profiles_inconclusive": sum(profile["status"] != "calibrated" for profile in profiles.values()),
    }
    return profiles, summary


def _score_and_alert(
    dataset: Mapping[str, Any], equipment_ids: list[str], target_signal_ids: list[str], profiles: Mapping[tuple[str, str, str], Mapping[str, Any]], config: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    test_start, test_end = dataset["split_times"]["test"]
    interval = timedelta(milliseconds=dataset["manifest"]["sampling_interval_ms"])
    threshold = float(config["robust_z_threshold"])
    persistence = int(config["persistence_points"])
    scores: list[dict[str, Any]] = []
    episodes: list[dict[str, Any]] = []
    unavailable: dict[str, int] = {}
    total_points = 0
    available_points = 0
    episode_counter = 0
    for equipment_id in equipment_ids:
        rows = dataset["observations"].get(equipment_id, [])
        for signal_id in target_signal_ids:
            if signal_id.rsplit(".", 1)[0] != equipment_id:
                continue
            streak = 0
            active_episode: dict[str, Any] | None = None
            previous_test_stamp: datetime | None = None
            previous_mode: str | None = None
            for index, row in enumerate(rows):
                stamp = _parse_dataset_time(row["timestamp"], "test observation timestamp")
                if not test_start <= stamp < test_end:
                    continue
                total_points += 1
                mode = str(row["operating_mode"])
                key = _profile_key(equipment_id, signal_id, mode)
                profile = profiles.get(key)
                current_quality, _ = _signal_value(row, signal_id)
                residual, reason, actual, previous_actual = _residual_at(rows, index, signal_id, interval, dataset["events"])
                previous_row_mode = str(rows[index - 1]["operating_mode"]) if index else None
                previous_row_stamp = _parse_dataset_time(rows[index - 1]["timestamp"], "previous test observation timestamp") if index else None
                continuity_reset = index > 0 and (
                    previous_row_stamp is None
                    or stamp - previous_row_stamp != interval
                    or mode != previous_row_mode
                )
                if continuity_reset or (previous_test_stamp is not None and (stamp - previous_test_stamp != interval or mode != previous_mode)):
                    streak = 0
                    active_episode = None
                score: float | None = None
                available = False
                if residual is None:
                    exclusion_reason = reason or "score_unavailable"
                elif profile is None or profile["status"] != "calibrated":
                    exclusion_reason = "profile_inconclusive"
                else:
                    scale = float(profile["scale"])
                    center = float(profile["center"])
                    score = abs(residual - center) / scale
                    if not math.isfinite(score):
                        score = None
                        exclusion_reason = "nonfinite_score"
                    else:
                        available = True
                        exclusion_reason = None
                if not available:
                    unavailable[exclusion_reason] = unavailable.get(exclusion_reason, 0) + 1
                    streak = 0
                    active_episode = None
                else:
                    available_points += 1
                    if score is None:
                        raise AnomalyEvaluationError("available score unexpectedly has no numeric value")
                    exceeds = score > threshold
                    if exceeds:
                        streak += 1
                    else:
                        streak = 0
                        active_episode = None
                    if exceeds and streak >= persistence:
                        if active_episode is None:
                            episode_counter += 1
                            active_episode = {
                                "episode_id": f"alert-{episode_counter:06d}",
                                "equipment_id": equipment_id,
                                "signal_id": signal_id,
                                "start_timestamp": _canonical_time(stamp),
                                "onset_timestamp": _canonical_time(stamp),
                                "end_timestamp": _canonical_time(stamp + interval),
                                "point_count": 1,
                                "max_score": score,
                                "profile_key": _profile_key_json(key),
                            }
                            episodes.append(active_episode)
                        else:
                            active_episode["end_timestamp"] = _canonical_time(stamp + interval)
                            active_episode["point_count"] += 1
                            active_episode["max_score"] = max(active_episode["max_score"], score)
                exceeds_value = bool(available and score is not None and score > threshold)
                score_row = {
                    "timestamp": _canonical_time(stamp),
                    "equipment_id": equipment_id,
                    "signal_id": signal_id,
                    "operating_mode": mode,
                    "quality_status": current_quality,
                    "actual": actual,
                    "previous_actual": previous_actual,
                    "residual": residual,
                    "profile_key": _profile_key_json(key),
                    "score": score,
                    "available": available,
                    "exclusion_reason": exclusion_reason,
                    "exceeds_threshold": exceeds_value,
                    "persistence_streak": streak,
                    "alert_episode_id": active_episode["episode_id"] if active_episode is not None and exceeds_value and streak >= persistence else None,
                }
                scores.append(score_row)
                previous_test_stamp = stamp
                previous_mode = mode
    return scores, episodes, {"total_points": total_points, "available_points": available_points, "unavailable_by_reason": unavailable}


def _interval_overlap(start: datetime, end: datetime, other_start: datetime, other_end: datetime) -> bool:
    return start < other_end and other_start < end


def _merge_intervals(intervals: Iterable[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    ordered = sorted((start, end) for start, end in intervals if start < end)
    if not ordered:
        return []
    merged: list[list[datetime]] = [[ordered[0][0], ordered[0][1]]]
    for start, end in ordered[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(start, end) for start, end in merged]


def _merge_seconds(intervals: Iterable[tuple[datetime, datetime]]) -> float:
    return sum((end - start).total_seconds() for start, end in _merge_intervals(intervals))


def _subtract_seconds(base: Iterable[tuple[datetime, datetime]], excluded: Iterable[tuple[datetime, datetime]]) -> float:
    base_intervals = _merge_intervals(base)
    excluded_intervals = _merge_intervals(excluded)
    total = 0.0
    for base_start, base_end in base_intervals:
        cursor = base_start
        for excluded_start, excluded_end in excluded_intervals:
            if excluded_end <= cursor:
                continue
            if excluded_start >= base_end:
                break
            if excluded_start > cursor:
                total += (min(excluded_start, base_end) - cursor).total_seconds()
            cursor = max(cursor, excluded_end)
            if cursor >= base_end:
                break
        if cursor < base_end:
            total += (base_end - cursor).total_seconds()
    return max(0.0, total)


def _delay_summary(delays: list[float]) -> dict[str, Any] | None:
    if not delays:
        return None
    return {"count": len(delays), "mean": sum(delays) / len(delays), "median": _median(delays), "min": min(delays), "max": max(delays)}


def _event_records_and_metrics(
    dataset: Mapping[str, Any], equipment_ids: list[str], target_signal_ids: list[str], classifications: Mapping[str, str], episodes: list[dict[str, Any]], config: Mapping[str, Any], scores: Iterable[Mapping[str, Any]] = ()
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], dict[str, int]]:
    test_start, test_end = dataset["split_times"]["test"]
    interval = timedelta(milliseconds=dataset["manifest"]["sampling_interval_ms"])
    grace = int(config["detection_grace_points"])
    target_set = set(target_signal_ids)
    episode_ids = [episode["episode_id"] for episode in episodes]
    if len(episode_ids) != len(set(episode_ids)):
        raise AnomalyEvaluationError("alert episode IDs must be unique")
    event_rows: list[dict[str, Any]] = []
    windows: list[tuple[str, str, datetime, datetime]] = []
    all_event_windows: list[dict[str, Any]] = []
    for event in dataset["events"]:
        event_id = event["event_id"]
        event_class = classifications.get(event_id)
        if event_class not in EVENT_CLASSES:
            raise AnomalyEvaluationError(f"event classification is missing or invalid: {event_id}")
        overlaps_test = event["start"] < test_end and event["end"] > test_start
        window_start = max(event["start"], test_start) if overlaps_test else None
        window_end = event["end"] + grace * interval if overlaps_test else None
        full_signal = event["signal_id"]
        if window_start is not None and window_end is not None:
            exposure_end = min(window_end, test_end)
            if window_start < exposure_end:
                all_event_windows.append({
                    "event_id": event_id,
                    "event_class": event_class,
                    "equipment_id": event["equipment_id"],
                    "signal_id": full_signal,
                    "window_start": window_start,
                    "window_end": exposure_end,
                })
        eligible = True
        reason: str | None = None
        if event_class not in POSITIVE_CLASSES:
            eligible = False
            reason = f"event_class_{event_class}"
        elif not overlaps_test:
            eligible = False
            reason = "outside_test_split"
        elif event["equipment_id"] not in equipment_ids or full_signal not in target_set:
            eligible = False
            reason = "unconfigured_equipment_or_signal"
        elif event["start"] < test_start:
            eligible = False
            reason = "left_censored"
        elif window_end is None or window_end > test_end:
            eligible = False
            reason = "right_censored_detection_window"
        if eligible:
            if window_start is None or window_end is None:
                raise AnomalyEvaluationError("eligible event is missing a detection window")
            windows.append((event["equipment_id"], full_signal, window_start, window_end))
        event_rows.append({
            "event_id": event_id,
            "event_class": event_class,
            "event_type": event["event_type"],
            "equipment_id": event["equipment_id"],
            "signal_id": full_signal,
            "event_start_timestamp": _canonical_time(event["start"]),
            "event_end_timestamp": _canonical_time(event["end"]),
            "detection_window_start": _canonical_time(window_start) if window_start is not None else None,
            "detection_window_end": _canonical_time(window_end) if window_end is not None else None,
            "eligible": eligible,
            "eligibility_reason": reason,
            "detected": False,
            "matched_alert_episode_id": None,
            "alert_onset_timestamp": None,
            "detection_delay_seconds": None,
        })
    for index, previous in enumerate(all_event_windows):
        for current in all_event_windows[index + 1:]:
            if previous["equipment_id"] != current["equipment_id"] or previous["signal_id"] != current["signal_id"]:
                continue
            if previous["window_end"] <= current["window_start"] or current["window_end"] <= previous["window_start"]:
                continue
            classes = {previous["event_class"], current["event_class"]}
            if classes & POSITIVE_CLASSES and classes & {"data_quality", "ignored"}:
                raise AnomalyEvaluationError(
                    f"positive and suppression event windows overlap for {current['equipment_id']}/{current['signal_id']}"
                )
    ordered_windows = sorted(windows, key=lambda item: (item[0], item[1], item[2], item[3]))
    for previous, current in zip(ordered_windows, ordered_windows[1:]):
        if previous[:2] == current[:2] and previous[3] > current[2]:
            raise AnomalyEvaluationError(f"eligible detection windows overlap for {current[0]}/{current[1]}")

    eligible_episode_ids: set[str] = set()
    eligible_episode_event_ids: dict[str, list[str]] = {}
    used_episode_ids: set[str] = set()
    matched_episode_event_ids: dict[str, str] = {}
    for row in event_rows:
        if not row["eligible"]:
            continue
        event_start = _parse_dataset_time(row["event_start_timestamp"], "event start")
        window_start = _parse_dataset_time(row["detection_window_start"], "detection window start")
        window_end = _parse_dataset_time(row["detection_window_end"], "detection window end")
        candidates: list[dict[str, Any]] = []
        for episode in episodes:
            if episode["equipment_id"] != row["equipment_id"] or episode["signal_id"] != row["signal_id"]:
                continue
            episode_start = _parse_dataset_time(episode["start_timestamp"], "alert episode start")
            episode_end = _parse_dataset_time(episode["end_timestamp"], "alert episode end")
            if _interval_overlap(episode_start, episode_end, window_start, window_end):
                eligible_episode_ids.add(episode["episode_id"])
                eligible_episode_event_ids.setdefault(episode["episode_id"], []).append(row["event_id"])
            onset = _parse_dataset_time(episode["onset_timestamp"], "alert onset")
            if episode["episode_id"] not in used_episode_ids and window_start <= onset < window_end and onset >= event_start:
                candidates.append(episode)
        if candidates:
            matched = min(candidates, key=lambda episode: episode["onset_timestamp"])
            used_episode_ids.add(matched["episode_id"])
            onset = _parse_dataset_time(matched["onset_timestamp"], "alert onset")
            row["detected"] = True
            row["matched_alert_episode_id"] = matched["episode_id"]
            row["alert_onset_timestamp"] = matched["onset_timestamp"]
            row["detection_delay_seconds"] = (onset - event_start).total_seconds()
            if row["detection_delay_seconds"] < 0:
                raise AnomalyEvaluationError("detection delay cannot be negative")
            matched_episode_event_ids[matched["episode_id"]] = row["event_id"]

    def class_metrics(event_class: str) -> dict[str, Any]:
        selected = [row for row in event_rows if row["eligible"] and row["event_class"] == event_class]
        detected = [row for row in selected if row["detected"]]
        delays = [float(row["detection_delay_seconds"]) for row in detected]
        return {
            "eligible_incidents": len(selected),
            "detected_incidents": len(detected),
            "missed_incidents": len(selected) - len(detected),
            "incident_recall": len(detected) / len(selected) if selected else None,
            "detection_delay_seconds": _delay_summary(delays),
        }

    eligible = [row for row in event_rows if row["eligible"]]
    detected = [row for row in eligible if row["detected"]]
    matched_count = len(used_episode_ids)
    unmatched_count = len(eligible_episode_ids - used_episode_ids)

    event_windows_by_equipment: dict[str, list[tuple[datetime, datetime]]] = {equipment: [] for equipment in equipment_ids}
    for event_window in all_event_windows:
        event_windows_by_equipment.setdefault(event_window["equipment_id"], []).append((event_window["window_start"], event_window["window_end"]))

    availability_by_signal: dict[str, dict[str, Any]] = {
        signal: {"available_points": 0, "total_points": 0, "availability_ratio": None} for signal in target_signal_ids
    }
    available_intervals_by_equipment: dict[str, list[tuple[datetime, datetime]]] = {equipment: [] for equipment in equipment_ids}
    available_intervals_by_signal: dict[str, list[tuple[datetime, datetime]]] = {signal: [] for signal in target_signal_ids}
    for score_row in scores:
        signal_id = score_row.get("signal_id")
        if signal_id not in availability_by_signal:
            raise AnomalyEvaluationError("score row references an unconfigured signal")
        availability_by_signal[signal_id]["total_points"] += 1
        if score_row.get("available") is not True:
            continue
        equipment_id = score_row.get("equipment_id")
        if equipment_id not in available_intervals_by_equipment or signal_id not in available_intervals_by_signal:
            raise AnomalyEvaluationError("available score row references an unconfigured equipment or signal")
        availability_by_signal[signal_id]["available_points"] += 1
        start = _parse_dataset_time(score_row.get("timestamp"), "available score timestamp")
        end = min(start + interval, test_end)
        if test_start <= start < end:
            available_intervals_by_equipment[equipment_id].append((start, end))
            available_intervals_by_signal[signal_id].append((start, end))
    for summary in availability_by_signal.values():
        if summary["total_points"]:
            summary["availability_ratio"] = summary["available_points"] / summary["total_points"]

    def event_windows_containing(episode: Mapping[str, Any], stamp: datetime) -> list[dict[str, Any]]:
        return [
            event_window
            for event_window in all_event_windows
            if event_window["equipment_id"] == episode["equipment_id"]
            and event_window["window_start"] <= stamp < event_window["window_end"]
        ]

    suppression_reason_keys = ("data_quality", "ignored")
    suppression_reason_counts = {reason: 0 for reason in suppression_reason_keys}
    positive_nonmatching_count = 0
    positive_ineligible_same_signal_count = 0
    alert_episode_accounting: list[dict[str, Any]] = []
    clean_signal_episodes: list[dict[str, Any]] = []
    for episode in episodes:
        episode_id = episode["episode_id"]
        onset = _parse_dataset_time(episode["onset_timestamp"], "alert onset")
        onset_context = event_windows_containing(episode, onset)
        eligible_event_ids = sorted(set(eligible_episode_event_ids.get(episode_id, [])))
        matched_event_id = None
        if episode_id in matched_episode_event_ids:
            partition = "matched_eligible"
            reason = "matched_eligible_event"
            included_in_precision = True
            matched_event_id = matched_episode_event_ids[episode_id]
        elif episode_id in eligible_episode_ids:
            partition = "unmatched_eligible_same_signal"
            reason = "eligible_window_without_post_event_onset"
            included_in_precision = True
            matched_event_id = None
        elif not onset_context:
            partition = "clean_false_alert"
            reason = "outside_event_window_at_onset"
            included_in_precision = True
            matched_event_id = None
        else:
            event_classes = {event_window["event_class"] for event_window in onset_context}
            if "data_quality" in event_classes:
                reason = "data_quality_event_window"
                reason_key = "data_quality"
            elif "ignored" in event_classes:
                reason = "ignored_event_window"
                reason_key = "ignored"
            elif event_classes & POSITIVE_CLASSES:
                positive_same_signal = any(
                    event_window["event_class"] in POSITIVE_CLASSES
                    and event_window["signal_id"] == episode["signal_id"]
                    for event_window in onset_context
                )
                partition = "positive_event_window_false_alert"
                reason = "positive_ineligible_same_signal" if positive_same_signal else "positive_nonmatching_signal"
                included_in_precision = True
                positive_nonmatching_count += 1
                if positive_same_signal:
                    positive_ineligible_same_signal_count += 1
            else:
                raise AnomalyEvaluationError(f"alert episode has an unsupported onset event context: {episode_id}")
            if event_classes & POSITIVE_CLASSES and "data_quality" not in event_classes and "ignored" not in event_classes:
                matched_event_id = None
            else:
                suppression_reason_counts[reason_key] += 1
                partition = "suppressed_event_window"
                included_in_precision = False
        if partition == "clean_false_alert":
            clean_signal_episodes.append(episode)
        alert_episode_accounting.append({
            "episode_id": episode_id,
            "equipment_id": episode["equipment_id"],
            "signal_id": episode["signal_id"],
            "partition": partition,
            "reason": reason,
            "matched_event_id": matched_event_id,
            "eligible_event_ids": eligible_event_ids,
            "onset_event_ids": sorted({event_window["event_id"] for event_window in onset_context}),
            "onset_event_classes": sorted({event_window["event_class"] for event_window in onset_context}),
            "included_in_precision_denominator": included_in_precision,
        })
    clean_signal_episodes.sort(key=lambda episode: (episode["equipment_id"], episode["start_timestamp"], episode["episode_id"]))
    clean_equipment_episodes: list[dict[str, Any]] = []
    for episode in clean_signal_episodes:
        start = _parse_dataset_time(episode["start_timestamp"], "alert episode start")
        end = _parse_dataset_time(episode["end_timestamp"], "alert episode end")
        if clean_equipment_episodes and clean_equipment_episodes[-1]["equipment_id"] == episode["equipment_id"]:
            current = clean_equipment_episodes[-1]
            current_end = _parse_dataset_time(current["end_timestamp"], "clean alert episode end")
            if start <= current_end:
                current["end_timestamp"] = _canonical_time(max(current_end, end))
                current["source_alert_episode_ids"].append(episode["episode_id"])
                continue
        clean_equipment_episodes.append({
            "equipment_episode_id": f"clean-{len(clean_equipment_episodes) + 1:06d}",
            "equipment_id": episode["equipment_id"],
            "start_timestamp": episode["start_timestamp"],
            "end_timestamp": episode["end_timestamp"],
            "source_alert_episode_ids": [episode["episode_id"]],
        })

    clean_false_signal_count = len(clean_signal_episodes)
    clean_false_equipment_count = len(clean_equipment_episodes)
    suppressed_count = sum(suppression_reason_counts.values())
    evaluated_alert_episode_count = matched_count + unmatched_count + positive_nonmatching_count + clean_false_signal_count
    partition_counts = {
        "matched_eligible_alert_episodes": matched_count,
        "unmatched_eligible_same_signal_alert_episodes": unmatched_count,
        "positive_event_window_false_alert_episodes": positive_nonmatching_count,
        "clean_false_alert_signal_episodes": clean_false_signal_count,
        "suppressed_event_window_alert_episodes": suppressed_count,
    }
    if sum(partition_counts.values()) != len(episodes):
        raise AnomalyEvaluationError("alert episode accounting does not form an exact partition")
    alert_episode_partition = {
        "total_alert_episodes": len(episodes),
        **partition_counts,
        "positive_event_window_false_alert_by_reason": {
            "positive_nonmatching_signal": positive_nonmatching_count - positive_ineligible_same_signal_count,
            "positive_ineligible_same_signal": positive_ineligible_same_signal_count,
        },
        "suppressed_event_window_by_reason": suppression_reason_counts,
        "precision_denominator_alert_episodes": evaluated_alert_episode_count,
        "precision_denominator_excludes_suppressed": True,
    }
    overall = {
        "eligible_incidents": len(eligible),
        "detected_incidents": len(detected),
        "missed_incidents": len(eligible) - len(detected),
        "matched_eligible_alert_episodes": matched_count,
        "unmatched_eligible_alert_episodes": unmatched_count,
        "evaluated_alert_episode_count": evaluated_alert_episode_count,
        "incident_precision": matched_count / evaluated_alert_episode_count if evaluated_alert_episode_count else None,
        "incident_recall": len(detected) / len(eligible) if eligible else None,
        "detection_delay_seconds": _delay_summary([float(row["detection_delay_seconds"]) for row in detected]),
    }

    clean_equipment_seconds = sum(
        _subtract_seconds(available_intervals_by_equipment.get(equipment_id, ()), event_windows_by_equipment.get(equipment_id, ()))
        for equipment_id in equipment_ids
    )
    clean_equipment_hours = clean_equipment_seconds / 3600.0
    clean_target_signal_hours: dict[str, float] = {}
    for signal_id in target_signal_ids:
        equipment_id = signal_id.rsplit(".", 1)[0]
        clean_target_signal_hours[signal_id] = _subtract_seconds(
            available_intervals_by_signal.get(signal_id, ()), event_windows_by_equipment.get(equipment_id, ())
        ) / 3600.0

    event_exclusions: dict[str, int] = {}
    for row in event_rows:
        if not row["eligible"]:
            reason = row["eligibility_reason"] or "ineligible"
            event_exclusions[reason] = event_exclusions.get(reason, 0) + 1
    metrics = {
        "overall": overall,
        "by_class": {"machine_fault": class_metrics("machine_fault"), "sensor_fault": class_metrics("sensor_fault")},
        "clean_false_alert_episode_count": clean_false_equipment_count,
        "clean_false_alert_equipment_episode_count": clean_false_equipment_count,
        "clean_false_alert_signal_episode_count": clean_false_signal_count,
        "evaluated_alert_episode_count": evaluated_alert_episode_count,
        "suppressed_event_window_alert_episode_count": suppressed_count,
        "suppressed_data_quality_event_window_alert_episode_count": suppression_reason_counts["data_quality"],
        "suppressed_ignored_event_window_alert_episode_count": suppression_reason_counts["ignored"],
        "positive_event_window_false_alert_episode_count": positive_nonmatching_count,
        "positive_nonmatching_signal_false_alert_episode_count": positive_nonmatching_count - positive_ineligible_same_signal_count,
        "positive_ineligible_same_signal_false_alert_episode_count": positive_ineligible_same_signal_count,
        "false_alert_signal_episode_count": positive_nonmatching_count + clean_false_signal_count,
        "precision_denominator_excludes_suppressed_event_windows": True,
        "alert_episode_partition": alert_episode_partition,
        "clean_monitored_equipment_hours": clean_equipment_hours,
        "false_alerts_per_8_equipment_hours": clean_false_equipment_count / clean_equipment_hours * 8.0 if clean_equipment_hours else None,
        "clean_monitored_target_signal_hours": clean_target_signal_hours,
        "score_availability_by_signal": availability_by_signal,
    }
    metrics["_alert_episode_accounting"] = alert_episode_accounting
    return event_rows, clean_equipment_episodes, metrics, {"total_events": len(event_rows), "ineligible_by_reason": event_exclusions}


def _summary(result: Mapping[str, Any]) -> str:
    metrics = result["metrics"]
    overall = metrics["overall"]
    partition = metrics["alert_episode_partition"]
    reasons = partition["suppressed_event_window_by_reason"]
    lines = [
        "# Event-aware anomaly evaluation v0.1結果",
        "",
        "これはforecast benchmarkから分離したsynthetic anomaly評価器の契約検証です。Toto性能、早期警報、実設備性能、製品昇格を示しません。",
        "",
        "## 判定",
        "",
        f"- status: `{result['status']}`",
        "- status semantics: pass means the evaluation contract completed with calibratable profiles and at least one eligible incident; it is not a precision/recall target pass.",
        f"- eligible incidents: {overall['eligible_incidents']}",
        f"- detected / missed incidents: {overall['detected_incidents']} / {overall['missed_incidents']}",
        f"- incident precision / recall: {overall['incident_precision']} / {overall['incident_recall']}",
        f"- signal alert episode partition (total = matched + unmatched same-signal + positive-event-window FP + clean FP + suppressed): {partition['total_alert_episodes']} = {partition['matched_eligible_alert_episodes']} + {partition['unmatched_eligible_same_signal_alert_episodes']} + {partition['positive_event_window_false_alert_episodes']} + {partition['clean_false_alert_signal_episodes']} + {partition['suppressed_event_window_alert_episodes']}",
        f"- evaluated signal alert episodes (precision denominator; matched / unmatched / positive-event-window FP / clean FP): {overall['evaluated_alert_episode_count']} ({overall['matched_eligible_alert_episodes']} / {overall['unmatched_eligible_alert_episodes']} / {metrics['positive_event_window_false_alert_episode_count']} / {metrics['clean_false_alert_signal_episode_count']})",
        f"- clean false-alert equipment episodes: {metrics['clean_false_alert_episode_count']}",
        f"- suppressed event-window alerts (data-quality / ignored): {partition['suppressed_event_window_alert_episodes']} ({reasons['data_quality']} / {reasons['ignored']})",
        "- suppressed event-window alerts are excluded from precision because they are neither a same-signal eligible incident alert nor a signal-level false alert; the reason ledger preserves them separately.",
        f"- clean monitored equipment hours: {metrics['clean_monitored_equipment_hours']}",
        f"- false alerts per 8 clean monitored equipment-hours: {metrics['false_alerts_per_8_equipment_hours']}",
        f"- positive event-window FP by reason (nonmatching signal / ineligible same signal): {partition['positive_event_window_false_alert_by_reason']}",
        f"- score availability by target signal: {metrics['score_availability_by_signal']}",
        "",
        "## 契約",
        "",
        "validationだけでmedian residualと1.4826*MAD profileを校正し、testは直前のquality=ok実測との差分だけでscoreします。event windowはclean false-alarm exposureから除外し、persistence確認時刻をalert onsetとします。detection_delay_secondsはevent開始からの非負秒数であり、lead timeではありません。",
        "",
        "同一equipmentで同時刻に発生した複数signalのclean alertはequipment-level episodeへdeduplicateします。Totoはこの評価では実行していません。制御writeはありません。",
    ]
    return "\n".join(lines) + "\n"


def _validate_result(result: Mapping[str, Any], root: Path) -> None:
    schema, _ = _load_schema(root, "anomaly-evaluation-result.schema.json")
    _validate_schema(result, schema, "anomaly evaluation result")


def _publish(root: Path, output: Path, result: Mapping[str, Any], *, verify_before_marker: Callable[[], None] | None = None) -> Path:
    if output.is_symlink() or output.exists():
        raise AnomalyEvaluationError(f"refusing to overwrite existing output: {output}")
    try:
        temporary = Path(tempfile.mkdtemp(prefix=".anomaly-evaluation.", dir=output.parent))
    except OSError as exc:
        raise AnomalyEvaluationError(f"could not create temporary publish directory: {output.parent}") from exc
    try:
        result_bytes = _canonical_json(result)
        summary_bytes = _summary(result).encode("utf-8")
        marker_bytes = _canonical_json({
            "marker_type": COMPLETION_MARKER_TYPE,
            "result_sha256": _sha256_bytes(result_bytes),
            "schema_version": SCHEMA_VERSION,
            "summary_sha256": _sha256_bytes(summary_bytes),
        })
        _write_fsync(temporary / "result.json", result_bytes, "anomaly result")
        _write_fsync(temporary / "summary.md", summary_bytes, "anomaly summary")
        _write_fsync(temporary / COMPLETION_MARKER, marker_bytes, "anomaly completion marker")
        try:
            output.mkdir()
        except OSError as exc:
            raise AnomalyEvaluationError(f"could not claim output directory: {output}") from exc
        _place_no_replace(temporary / "result.json", output / "result.json")
        _place_no_replace(temporary / "summary.md", output / "summary.md")
        if verify_before_marker is not None:
            verify_before_marker()
        _place_no_replace(temporary / COMPLETION_MARKER, output / COMPLETION_MARKER)
        _best_effort_fsync_directory(output, "anomaly output")
        _best_effort_fsync_directory(output.parent, "anomaly output parent")
    except AnomalyEvaluationError:
        raise
    except OSError as exc:
        raise AnomalyEvaluationError(f"anomaly publish failed: {output}") from exc
    finally:
        if temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)
    return output


def _output_state(output: Path) -> tuple[str, str]:
    if _is_link(output):
        raise AnomalyEvaluationError(f"existing output must not be a symlink or junction: {output}")
    if not output.exists():
        return "absent", ""
    if not output.is_dir():
        raise AnomalyEvaluationError(f"existing output must be a directory: {output}")
    marker = output / COMPLETION_MARKER
    if _is_link(marker):
        raise AnomalyEvaluationError(f"existing completion marker must not be a symlink or junction: {marker}")
    if not marker.is_file():
        return "incomplete", "completion marker is missing"
    try:
        value, _ = _strict_object(marker, "completion marker")
    except AnomalyEvaluationError as exc:
        return "incomplete", f"completion marker is invalid: {exc}"
    if set(value) != {"marker_type", "schema_version", "result_sha256", "summary_sha256"}:
        return "incomplete", "completion marker keys are invalid"
    if value.get("marker_type") != COMPLETION_MARKER_TYPE or value.get("schema_version") != SCHEMA_VERSION:
        return "incomplete", "completion marker identity is invalid"
    result = output / "result.json"
    summary = output / "summary.md"
    if _is_link(result) or _is_link(summary):
        raise AnomalyEvaluationError(f"existing completion payload must not contain a symlink or junction: {output}")
    if not result.is_file() or not summary.is_file():
        return "incomplete", "completion payload is incomplete"
    for name in ("result_sha256", "summary_sha256"):
        digest = value.get(name)
        if not isinstance(digest, str) or len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            return "incomplete", f"completion marker {name} is invalid"
    if _sha256(result) != value["result_sha256"] or _sha256(summary) != value["summary_sha256"]:
        return "incomplete", "completion marker hashes do not match payload"
    return "complete", ""


def _quarantine_incomplete(output: Path) -> Path:
    for _ in range(16):
        quarantine = output.parent / f".{output.name}.incomplete-{uuid4().hex}"
        if quarantine.exists() or _is_link(quarantine):
            continue
        try:
            output.rename(quarantine)
            return quarantine
        except FileExistsError:
            continue
        except OSError as exc:
            raise AnomalyEvaluationError(f"could not quarantine incomplete output: {output}") from exc
    raise AnomalyEvaluationError(f"could not allocate a unique quarantine name: {output}")


def _evaluate_core(
    config_path: str | Path,
    root: Path,
    *,
    output: Path | None = None,
    expected_code_revision: Mapping[str, Any] | None = None,
    expected_config_hash: str | None = None,
    expected_dataset_inventory: tuple[tuple[str, str], ...] | None = None,
    expected_dataset_hashes: Mapping[str, str] | None = None,
    expected_dataset_fingerprint: str | None = None,
    expected_config_schema_hash: str | None = None,
    expected_result_schema_hash: str | None = None,
) -> tuple[Path, dict[str, Any]]:
    root = Path(root).expanduser().resolve()
    code_revision = dict(expected_code_revision) if expected_code_revision is not None else _revision(root)
    if expected_code_revision is not None and _revision(root) != code_revision:
        raise AnomalyEvaluationError("repository code revision changed before anomaly evaluation")
    config_file = _resolve_config_file(config_path, root)
    config, config_raw = _strict_object(config_file, "anomaly evaluation config")
    if expected_config_hash is not None and _sha256_bytes(config_raw) != expected_config_hash:
        raise AnomalyEvaluationError("anomaly config changed before core evaluation snapshot")
    dataset_path = _safe_repo_path(root, config.get("dataset_path"), "dataset_path", must_exist=True)
    dataset_inventory = _inventory_tree(dataset_path)
    dataset_hashes = _inventory_hashes(dataset_path, dataset_inventory)
    if expected_dataset_inventory is not None and dataset_inventory != expected_dataset_inventory:
        raise AnomalyEvaluationError("dataset inventory changed before core evaluation snapshot")
    if expected_dataset_hashes is not None and dataset_hashes != dict(expected_dataset_hashes):
        raise AnomalyEvaluationError("dataset source changed before core evaluation snapshot")
    config_schema_path = _safe_repo_path(root, "schemas/anomaly-evaluation-config.schema.json", "anomaly config schema", must_exist=True)
    result_schema_path = _safe_repo_path(root, "schemas/anomaly-evaluation-result.schema.json", "anomaly result schema", must_exist=True)
    config_schema_hash = _sha256(config_schema_path)
    result_schema_hash = _sha256(result_schema_path)
    if expected_config_schema_hash is not None and config_schema_hash != expected_config_schema_hash:
        raise AnomalyEvaluationError("anomaly config schema changed before core evaluation snapshot")
    if expected_result_schema_hash is not None and result_schema_hash != expected_result_schema_hash:
        raise AnomalyEvaluationError("anomaly result schema changed before core evaluation snapshot")
    snapshot_fingerprint = _snapshot_dataset_fingerprint(dataset_path)
    if expected_dataset_fingerprint is not None and snapshot_fingerprint != expected_dataset_fingerprint:
        raise AnomalyEvaluationError("dataset fingerprint changed before core evaluation snapshot")
    try:
        dataset = _verify_dataset(dataset_path, root)
    except (EventSliceError, OSError, ValueError, KeyError, TypeError) as exc:
        raise AnomalyEvaluationError(f"dataset quality gate failed: {exc}") from exc
    equipment_ids, target_signal_ids, classifications = _validate_config(config, root, dataset)
    output_path = _resolve_output(root, config["output_dir"])
    if output is not None and output_path != output:
        raise AnomalyEvaluationError("anomaly output changed after lock claim")
    profiles, calibration_exclusions = _calibrate_profiles(dataset, equipment_ids, target_signal_ids, config)
    scores, episodes, score_exclusions = _score_and_alert(dataset, equipment_ids, target_signal_ids, profiles, config)
    incidents, clean_alerts, metrics, event_exclusions = _event_records_and_metrics(dataset, equipment_ids, target_signal_ids, classifications, episodes, config, scores)
    alert_episode_accounting = metrics.pop("_alert_episode_accounting")
    status = "inconclusive" if (
        calibration_exclusions["profiles_inconclusive"]
        or any(summary["available_points"] == 0 for summary in metrics["score_availability_by_signal"].values())
    ) else ("partial" if not metrics["overall"]["eligible_incidents"] else "pass")
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "result_type": RESULT_TYPE,
        "analyzer_id": ANALYZER_ID,
        "status": status,
        "provenance": {
            "config": {"kind": "anomaly-evaluation-config", "path": config_file.relative_to(root).as_posix(), "sha256": _sha256_bytes(config_raw)},
            "schema": {"kind": "anomaly-evaluation-result-schema", "path": result_schema_path.relative_to(root).as_posix(), "sha256": result_schema_hash},
            "config_schema": {"kind": "anomaly-evaluation-config-schema", "path": config_schema_path.relative_to(root).as_posix(), "sha256": config_schema_hash},
            "dataset": {"kind": "synthetic-dataset", "path": dataset_path.relative_to(root).as_posix(), "dataset_id": dataset["manifest"]["dataset_id"], "dataset_fingerprint": dataset["fingerprint_digest"], "manifest_sha256": dataset_hashes.get("dataset-manifest.json")},
            "quality_gate": dataset["quality"],
            "code_revision": code_revision,
        },
        "parameters": {
            "target_signal_ids": target_signal_ids,
            "min_calibration_points": config["min_calibration_points"],
            "robust_z_threshold": config["robust_z_threshold"],
            "persistence_points": config["persistence_points"],
            "detection_grace_points": config["detection_grace_points"],
            "sampling_interval_ms": dataset["manifest"]["sampling_interval_ms"],
            "calibration_split": "validation",
            "scoring_split": "test",
            "boundary_semantics": "[start,end)",
        },
        "profiles": [profiles[key] for key in sorted(profiles)],
        "scores": scores,
        "alert_episodes": episodes,
        "alert_episode_accounting": alert_episode_accounting,
        "incidents": incidents,
        "clean_false_alert_episodes": clean_alerts,
        "metrics": metrics,
        "exclusions": {"calibration": calibration_exclusions, "scoring": score_exclusions, "events": event_exclusions},
        "row_counts": {
            "dataset_observations": sum(len(rows) for rows in dataset["observations"].values()),
            "score_rows": len(scores),
            "alert_episodes": len(episodes),
            "alert_episode_accounting": len(alert_episode_accounting),
            "incidents": len(incidents),
            "clean_false_alert_episodes": len(clean_alerts),
            "clean_false_alert_signal_episodes": metrics["clean_false_alert_signal_episode_count"],
        },
        "limitations": [
            "synthetic datasetとsingle-seed scenarioの契約検証であり、実設備性能やproduction alertingを評価しない。",
            "status=passは校正可能なprofileとeligible incidentがあり評価契約を完了したことを示すだけで、precision／recall目標の合格ではない。",
            "scoreは観測後のone-step residualであり、detection_delay_secondsをlead timeとして解釈しない。",
            "test event intervalはcalibration除外とprevious-history residual availability判定にだけ使い、current timestampのresidualはeventだけでは隠さない。",
            "Totoは未評価であり、control write、Banto Hub write、commissioning自動調整は行わない。",
            "global fallback、epsilon scale、数値補間、testによるprofile校正は行わない。",
        ],
    }
    _validate_result(result, root)
    if expected_config_hash is not None and result["provenance"]["config"]["sha256"] != expected_config_hash:
        raise AnomalyEvaluationError("result provenance config hash does not match evaluation snapshot")
    if expected_dataset_fingerprint is not None and result["provenance"]["dataset"]["dataset_fingerprint"] != expected_dataset_fingerprint:
        raise AnomalyEvaluationError("result provenance dataset fingerprint does not match evaluation snapshot")
    if expected_config_schema_hash is not None and result["provenance"]["config_schema"]["sha256"] != expected_config_schema_hash:
        raise AnomalyEvaluationError("result provenance config schema hash does not match evaluation snapshot")
    if expected_result_schema_hash is not None and result["provenance"]["schema"]["sha256"] != expected_result_schema_hash:
        raise AnomalyEvaluationError("result provenance result schema hash does not match evaluation snapshot")
    if _revision(root) != code_revision:
        raise AnomalyEvaluationError("repository code revision changed during anomaly evaluation")
    _assert_input_unchanged(dataset_path, dataset_inventory, dataset_hashes)
    if _sha256(config_file) != result["provenance"]["config"]["sha256"]:
        raise AnomalyEvaluationError("anomaly config changed during evaluation")
    if _sha256(config_schema_path) != config_schema_hash or _sha256(result_schema_path) != result_schema_hash:
        raise AnomalyEvaluationError("anomaly evaluation schema changed during evaluation")
    return output_path, result


def evaluate_anomalies(config_path: str | Path, root: Path, *, recover_incomplete: bool = False) -> Path:
    """Evaluate a synthetic dataset and atomically publish a new artifact."""
    root = Path(root).expanduser().resolve()
    entry_code_revision = _revision(root)
    config_file = _resolve_config_file(config_path, root)
    config, config_raw = _strict_object(config_file, "anomaly evaluation config")
    output = _resolve_output(root, config.get("output_dir"))
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise AnomalyEvaluationError(f"could not prepare output parent: {output.parent}") from exc
    state, reason = _output_state(output)
    if state == "complete":
        raise AnomalyEvaluationError(f"refusing to overwrite complete output: {output}")
    if state == "incomplete":
        if not recover_incomplete:
            raise AnomalyEvaluationError(f"existing output is incomplete: {output} ({reason}); pass --recover-incomplete to quarantine it")
        _quarantine_incomplete(output)

    dataset_path = _safe_repo_path(root, config.get("dataset_path"), "dataset_path", must_exist=True)
    dataset_inventory = _inventory_tree(dataset_path)
    dataset_hashes = _inventory_hashes(dataset_path, dataset_inventory)
    dataset_fingerprint = _snapshot_dataset_fingerprint(dataset_path)
    config_schema_path = _safe_repo_path(root, "schemas/anomaly-evaluation-config.schema.json", "anomaly config schema", must_exist=True)
    result_schema_path = _safe_repo_path(root, "schemas/anomaly-evaluation-result.schema.json", "anomaly result schema", must_exist=True)
    config_hash = _sha256_bytes(config_raw)
    config_schema_hash = _sha256(config_schema_path)
    result_schema_hash = _sha256(result_schema_path)
    output_path, result = _evaluate_core(
        config_file,
        root,
        output=output,
        expected_code_revision=entry_code_revision,
        expected_config_hash=config_hash,
        expected_dataset_inventory=dataset_inventory,
        expected_dataset_hashes=dataset_hashes,
        expected_dataset_fingerprint=dataset_fingerprint,
        expected_config_schema_hash=config_schema_hash,
        expected_result_schema_hash=result_schema_hash,
    )

    def verify_before_marker() -> None:
        if _revision(root) != entry_code_revision:
            raise AnomalyEvaluationError("repository code revision changed before completion marker")
        _assert_input_unchanged(dataset_path, dataset_inventory, dataset_hashes)
        if _sha256(config_file) != config_hash:
            raise AnomalyEvaluationError("anomaly config changed before completion marker")
        if _sha256(config_schema_path) != config_schema_hash or _sha256(result_schema_path) != result_schema_hash:
            raise AnomalyEvaluationError("anomaly evaluation schema changed before completion marker")

    return _publish(root, output_path, result, verify_before_marker=verify_before_marker)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="evaluate_anomalies.py", description="Event-aware anomaly evaluation v0.1")
    parser.add_argument("--config", required=True, help="anomaly evaluation config (repository-relative or local absolute path)")
    parser.add_argument("--root", default=None, help="repository root (defaults to the current repository)")
    parser.add_argument("--recover-incomplete", action="store_true", help="quarantine an incomplete existing output before rerunning")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[2]
    try:
        output = evaluate_anomalies(args.config, root, recover_incomplete=args.recover_incomplete)
    except (AnomalyEvaluationError, OSError, TypeError, ValueError, KeyError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"Event-aware anomaly evaluation: {output}")
    return 0


__all__ = ["AnomalyEvaluationError", "evaluate_anomalies"]
