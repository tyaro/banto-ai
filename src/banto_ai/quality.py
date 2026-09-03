"""生成済みsynthetic datasetの構造・split・fingerprint安全検査。"""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .generator import (
    EVENT_TYPES,
    FINGERPRINT_ALGORITHM,
    FINGERPRINT_CANONICALIZATION,
    FINGERPRINT_FILE_NAMES,
    FINGERPRINT_KEYS,
    REGIMES,
    SIGNALS,
    SUMMARY_KEYS,
    SUMMARY_SCHEMA_VERSION,
    SUMMARY_TYPE,
    effective_event_magnitude,
    event_signal,
    expected_catalog,
)
from .manifest import load_json, validate_manifest

QUALITY_STATUSES = frozenset({"ok", "missing"})
OBSERVATION_KEYS = frozenset({"timestamp", "equipment_id", "equipment_type", "operating_mode", "recipe_step", "signals", "quality"})
SIGNAL_KEYS = frozenset({"unit", "value"})
EVENT_KEYS = frozenset({"event_id", "event_type", "equipment_id", "signal_id", "start_timestamp", "end_timestamp", "boundary_semantics", "magnitude", "description"})
DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class DatasetQualityError(ValueError):
    """datasetがPhase 1 Gateの品質条件を満たさない。"""


def _parse_utc(value: Any) -> datetime:
    if not isinstance(value, str):
        raise DatasetQualityError("timestamp must be a string in explicit UTC")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DatasetQualityError(f"invalid timestamp: {value!r}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise DatasetQualityError("timestamp must be explicit UTC")
    return parsed.astimezone(timezone.utc)


def _load_jsonl(path: Path, *, allow_empty: bool = False) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        handle = path.open(encoding="utf-8")
    except OSError as exc:
        raise DatasetQualityError(f"JSONL file is missing or unreadable: {path}") from exc
    with handle:
        for line_number, line in enumerate(handle, 1):
            try:
                row = json.loads(line, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
            except (json.JSONDecodeError, ValueError) as exc:
                raise DatasetQualityError(f"{path}:{line_number}: invalid JSONL") from exc
            if not isinstance(row, dict):
                raise DatasetQualityError(f"{path}:{line_number}: row must be object")
            rows.append(row)
    if not rows and not allow_empty:
        raise DatasetQualityError(f"{path}: no rows")
    return rows


def _child_path(dataset_dir: Path, relative_path: str) -> Path:
    candidate = (dataset_dir / relative_path).resolve()
    if candidate != dataset_dir.resolve() and dataset_dir.resolve() not in candidate.parents:
        raise DatasetQualityError(f"manifest path escapes dataset directory: {relative_path}")
    return candidate


def _record_count(rows: list[dict[str, Any]], equipment_ids: set[str], start: datetime, end: datetime) -> int:
    return sum(1 for row in rows if row["equipment_id"] in equipment_ids and start <= _parse_utc(row["timestamp"]) < end)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _is_digest(value: Any) -> bool:
    return isinstance(value, str) and DIGEST_PATTERN.fullmatch(value) is not None


def _check_summary_structure(summary: dict[str, Any]) -> None:
    if not isinstance(summary, dict) or set(summary) != SUMMARY_KEYS:
        raise DatasetQualityError("summary keys must exactly match the generated summary schema")
    if summary["schema_version"] != SUMMARY_SCHEMA_VERSION or summary["summary_type"] != SUMMARY_TYPE:
        raise DatasetQualityError("summary schema_version or summary_type is invalid")
    for key in ("dataset_id", "generator_version"):
        if not isinstance(summary[key], str) or not summary[key]:
            raise DatasetQualityError(f"summary field must be a non-empty string: {key}")
    for key in ("seed", "sample_count_per_equipment", "equipment_count", "observation_record_count", "configured_event_count", "disabled_event_count", "event_count"):
        if not isinstance(summary[key], int) or isinstance(summary[key], bool):
            raise DatasetQualityError(f"summary field must be an integer: {key}")
    if not isinstance(summary["regime_coverage"], dict) or not isinstance(summary["event_coverage"], dict):
        raise DatasetQualityError("summary coverage fields must be objects")
    if not _is_digest(summary["dataset_fingerprint"]):
        raise DatasetQualityError("summary dataset_fingerprint must be a lowercase SHA-256 digest")


def _check_observations(rows: list[dict[str, Any]], dataset: dict[str, Any]) -> tuple[dict[str, list[datetime]], datetime, datetime, dict[str, int]]:
    equipment = {item["equipment_id"]: item["equipment_type"] for item in dataset["equipment"]}
    catalog = {item["signal_id"]: item for item in dataset["signals"]}
    if len(catalog) != len(dataset["signals"]) or len(equipment) != len(dataset["equipment"]):
        raise DatasetQualityError("dataset manifest contains duplicate equipment or signal IDs")
    expected_numeric = set(SIGNALS)
    intervals: dict[str, int] = {}
    expected_catalog_all = {
        entry["signal_id"]: entry
        for equipment_id, equipment_type in equipment.items()
        for entry in expected_catalog(equipment_id, equipment_type, dataset["sampling_interval_ms"])
    }
    if set(catalog) != set(expected_catalog_all):
        raise DatasetQualityError("dataset catalog must contain exactly the generator-defined equipment signals and labels")
    for equipment_id in equipment:
        entries = [item for item in dataset["signals"] if item["signal_id"] in {entry["signal_id"] for entry in expected_catalog(equipment_id, equipment[equipment_id], dataset["sampling_interval_ms"])}]
        if not entries or any(item["sampling_interval_ms"] <= 0 for item in entries):
            raise DatasetQualityError(f"sampling interval catalog is missing for {equipment_id}")
        values = {item["sampling_interval_ms"] for item in entries}
        if len(values) != 1:
            raise DatasetQualityError(f"sampling interval catalog is inconsistent for {equipment_id}")
        intervals[equipment_id] = values.pop()
        expected_entries = expected_catalog(equipment_id, equipment[equipment_id], dataset["sampling_interval_ms"])
        actual_entries = {item["signal_id"]: item for item in entries}
        expected_entries_by_id = {item["signal_id"]: item for item in expected_entries}
        if actual_entries != expected_entries_by_id:
            raise DatasetQualityError(f"catalog definition does not match generator constants for {equipment_id}")
    per_equipment: dict[str, list[datetime]] = {equipment_id: [] for equipment_id in equipment}
    for row in rows:
        if set(row) != OBSERVATION_KEYS:
            raise DatasetQualityError("observation contains an unexpected key or a ground-truth label")
        equipment_id = row["equipment_id"]
        if equipment_id not in equipment or row["equipment_type"] != equipment[equipment_id]:
            raise DatasetQualityError(f"unknown or mismatched equipment_type: {equipment_id}")
        if row["operating_mode"] not in REGIMES:
            raise DatasetQualityError(f"unknown operating_mode: {row['operating_mode']!r}")
        if not isinstance(row["recipe_step"], str) or not row["recipe_step"]:
            raise DatasetQualityError("recipe_step must be a non-empty string")
        timestamp = _parse_utc(row["timestamp"])
        timestamps = per_equipment[equipment_id]
        if timestamps and timestamp <= timestamps[-1]:
            raise DatasetQualityError(f"duplicate or out-of-order timestamp for {equipment_id}")
        if timestamps:
            expected_delta = timedelta(milliseconds=intervals[equipment_id])
            if timestamp - timestamps[-1] != expected_delta:
                raise DatasetQualityError(f"timestamp delta does not match catalog sampling interval for {equipment_id}")
        timestamps.append(timestamp)
        signals = row["signals"]
        quality = row["quality"]
        if not isinstance(signals, dict) or not isinstance(quality, dict) or set(signals) != expected_numeric or set(quality) != expected_numeric:
            raise DatasetQualityError("quality keys must exactly match the numeric signal set")
        for signal_id, payload in signals.items():
            catalog_item = catalog.get(f"{equipment_id}.{signal_id}")
            if catalog_item is None or not isinstance(payload, dict) or set(payload) != SIGNAL_KEYS or payload["unit"] != catalog_item["unit"]:
                raise DatasetQualityError(f"unit or signal payload mismatch for {equipment_id}.{signal_id}")
            status = quality[signal_id]
            if status not in QUALITY_STATUSES:
                raise DatasetQualityError(f"unknown quality status: {status!r}")
            value = payload["value"]
            if value is not None and (not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value)):
                raise DatasetQualityError(f"non-finite value for {equipment_id}.{signal_id}")
            if (value is None) != (status == "missing"):
                raise DatasetQualityError(f"value/quality mismatch for {equipment_id}.{signal_id}")
    if not rows or any(not timestamps for timestamps in per_equipment.values()):
        raise DatasetQualityError("observations must contain every manifest equipment")
    starts = [timestamps[0] for timestamps in per_equipment.values()]
    ends = [timestamps[-1] + timedelta(milliseconds=intervals[equipment_id]) for equipment_id, timestamps in per_equipment.items()]
    return per_equipment, min(starts), max(ends), intervals


def _check_splits(split: dict[str, Any], rows: list[dict[str, Any]], expected_equipment: set[str], dataset_start: datetime, dataset_end: datetime) -> None:
    strategies = split["strategies"]
    if len({item["strategy"] for item in strategies}) != 2:
        raise DatasetQualityError("split strategies must be unique and include both required strategies")
    for strategy in strategies:
        kind = strategy["strategy"]
        splits = strategy["splits"]
        split_ids = [item["split_id"] for item in splits]
        if len(split_ids) != len(set(split_ids)):
            raise DatasetQualityError(f"duplicate split_id in {kind}")
        if kind == "chronological" and split_ids != ["train", "validation", "test"]:
            raise DatasetQualityError("chronological split_id must be train/validation/test exactly once")
        if kind == "cross_equipment" and len(splits) < 2:
            raise DatasetQualityError("cross_equipment requires at least two splits")
        previous_end: datetime | None = None
        equipment_seen: set[str] = set()
        for item in splits:
            start = _parse_utc(item["start_timestamp"])
            end = _parse_utc(item["end_timestamp"])
            ids = item["equipment_ids"]
            current = set(ids)
            if not current or len(current) != len(ids) or not current <= expected_equipment:
                raise DatasetQualityError(f"invalid equipment_ids in {kind}/{item['split_id']}")
            if kind == "chronological" and current != expected_equipment:
                raise DatasetQualityError("chronological split must contain all equipment")
            if kind == "cross_equipment" and equipment_seen & current:
                raise DatasetQualityError("cross_equipment split has overlapping equipment")
            if start >= end or (kind == "chronological" and previous_end is not None and start != previous_end):
                raise DatasetQualityError(f"{kind} split has a gap, overlap, or invalid order")
            if start < dataset_start or end > dataset_end:
                raise DatasetQualityError(f"{kind} split is outside dataset period")
            if kind == "cross_equipment" and (start != dataset_start or end != dataset_end):
                raise DatasetQualityError("cross_equipment split time boundary must cover dataset period")
            actual = _record_count(rows, current, start, end)
            if actual != item["record_count"]:
                raise DatasetQualityError(f"wrong record_count in {kind}/{item['split_id']}: manifest={item['record_count']} actual={actual}")
            previous_end = end
            equipment_seen |= current
        if _parse_utc(splits[0]["start_timestamp"]) != dataset_start or _parse_utc(splits[-1]["end_timestamp"]) != dataset_end:
            raise DatasetQualityError(f"{kind} split does not fully cover dataset period")
        if kind == "cross_equipment" and equipment_seen != expected_equipment:
            raise DatasetQualityError("cross_equipment split must cover each equipment exactly once")


def _check_events(events: list[dict[str, Any]], dataset: dict[str, Any], dataset_start: datetime, dataset_end: datetime) -> None:
    equipment = {item["equipment_id"] for item in dataset["equipment"]}
    event_ids: set[str] = set()
    for event in events:
        if set(event) != EVENT_KEYS:
            raise DatasetQualityError("event contains an unexpected key")
        if event["event_id"] in event_ids:
            raise DatasetQualityError(f"duplicate event_id: {event['event_id']}")
        event_ids.add(event["event_id"])
        if event["event_type"] not in EVENT_TYPES or event["equipment_id"] not in equipment or event["signal_id"] not in SIGNALS:
            raise DatasetQualityError("event has unknown type, equipment, or signal")
        if event["boundary_semantics"] != "[start,end)":
            raise DatasetQualityError("event boundary_semantics must be [start,end)")
        start = _parse_utc(event["start_timestamp"])
        end = _parse_utc(event["end_timestamp"])
        if not dataset_start <= start < end <= dataset_end:
            raise DatasetQualityError(f"event interval is outside dataset period: {event['event_id']}")
        if not isinstance(event["magnitude"], (int, float)) or isinstance(event["magnitude"], bool) or not math.isfinite(event["magnitude"]):
            raise DatasetQualityError(f"event magnitude is not finite: {event['event_id']}")
        if not isinstance(event["description"], str):
            raise DatasetQualityError(f"event description must be a string: {event['event_id']}")


def _config_regime_at(config: dict[str, Any], index: int) -> dict[str, Any]:
    for regime in config["regimes"]:
        if regime["start_sample"] <= index < regime["end_sample"]:
            return regime
    raise DatasetQualityError(f"config has no regime for sample {index}")


def _check_config_semantics(config: dict[str, Any], dataset: dict[str, Any], split: dict[str, Any], summary: dict[str, Any], rows: list[dict[str, Any]], events: list[dict[str, Any]], per_equipment: dict[str, list[datetime]], intervals: dict[str, int]) -> None:
    _check_summary_structure(summary)
    config_equipment = config["equipment"]
    dataset_identity = (dataset["dataset_id"], dataset["generator_version"], dataset["seed"], dataset["sampling_interval_ms"], dataset["sample_count"])
    split_identity = (split["dataset_id"], split["generator_version"], split["seed"], split["sampling_interval_ms"], split["sample_count"])
    config_identity = (config["dataset_id"], config["generator_version"], config["seed"], config["sampling_interval_ms"], config["sample_count"])
    if dataset_identity != config_identity:
        raise DatasetQualityError("dataset manifest identity does not match generator config")
    if split_identity != config_identity:
        raise DatasetQualityError("split manifest identity does not match generator config")
    if dataset["equipment"] != config_equipment:
        raise DatasetQualityError("dataset equipment does not match generator config")
    if any(interval != config["sampling_interval_ms"] for interval in intervals.values()):
        raise DatasetQualityError("catalog sampling interval does not match generator config")
    config_start = _parse_utc(config["start_timestamp"])
    expected_delta = timedelta(milliseconds=config["sampling_interval_ms"])
    rows_by_equipment: dict[str, list[dict[str, Any]]] = {item["equipment_id"]: [] for item in config_equipment}
    for row in rows:
        rows_by_equipment[row["equipment_id"]].append(row)
    for item in config_equipment:
        equipment_id = item["equipment_id"]
        timestamps = per_equipment[equipment_id]
        if len(timestamps) != config["sample_count"]:
            raise DatasetQualityError(f"{equipment_id} must contain exactly sample_count observations")
        expected_timestamps = [config_start + index * expected_delta for index in range(config["sample_count"])]
        if timestamps != expected_timestamps:
            raise DatasetQualityError(f"timestamp column does not match config start_timestamp for {equipment_id}")
        ordered_rows = sorted(rows_by_equipment[equipment_id], key=lambda row: _parse_utc(row["timestamp"]))
        for index, row in enumerate(ordered_rows):
            regime = _config_regime_at(config, index)
            expected_recipe = regime.get("recipe_step", regime["regime"])
            if row["operating_mode"] != regime["regime"] or row["recipe_step"] != expected_recipe:
                raise DatasetQualityError(f"mode or recipe_step does not match config at {equipment_id}/{index}")
    expected_active = [event for event in config["events"] if event["enabled"]]
    actual_by_id = {event["event_id"]: event for event in events}
    if set(actual_by_id) != {event["event_id"] for event in expected_active}:
        raise DatasetQualityError("events.jsonl IDs do not match enabled generator config events")
    for event in expected_active:
        start = config_start + event["start_sample"] * expected_delta
        end = config_start + event["end_sample"] * expected_delta
        expected = {"event_id": event["event_id"], "event_type": event["event_type"], "equipment_id": event["equipment_id"], "signal_id": event_signal(event), "start_timestamp": _iso(start), "end_timestamp": _iso(end), "boundary_semantics": "[start,end)", "magnitude": effective_event_magnitude(event), "description": event.get("description", "")}
        if actual_by_id[event["event_id"]] != expected:
            raise DatasetQualityError(f"event ground truth does not match generator config: {event['event_id']}")
    expected_regime_coverage = {regime: sum(item["end_sample"] - item["start_sample"] for item in config["regimes"] if item["regime"] == regime) for regime in REGIMES}
    expected_event_coverage = {event_type: sum(1 for event in expected_active if event["event_type"] == event_type) for event_type in EVENT_TYPES}
    expected_summary = {"dataset_id": config["dataset_id"], "generator_version": config["generator_version"], "seed": config["seed"], "sample_count_per_equipment": config["sample_count"], "equipment_count": len(config_equipment), "observation_record_count": config["sample_count"] * len(config_equipment), "configured_event_count": len(config["events"]), "disabled_event_count": sum(1 for event in config["events"] if not event["enabled"]), "event_count": len(expected_active), "regime_coverage": expected_regime_coverage, "event_coverage": expected_event_coverage}
    for key, expected in expected_summary.items():
        if summary.get(key) != expected:
            raise DatasetQualityError(f"summary field does not match generator config: {key}")


def _check_fingerprint(dataset_dir: Path, dataset: dict[str, Any], summary: dict[str, Any]) -> None:
    fingerprint = load_json(_child_path(dataset_dir, dataset["fingerprint_path"]))
    if not isinstance(fingerprint, dict) or set(fingerprint) != FINGERPRINT_KEYS:
        raise DatasetQualityError("fingerprint keys must exactly match the generated fingerprint schema")
    if fingerprint["algorithm"] != FINGERPRINT_ALGORITHM or fingerprint["canonicalization"] != FINGERPRINT_CANONICALIZATION:
        raise DatasetQualityError("fingerprint algorithm or canonicalization is invalid")
    if not _is_digest(fingerprint["dataset_fingerprint"]):
        raise DatasetQualityError("fingerprint dataset_fingerprint must be a lowercase SHA-256 digest")
    if not isinstance(fingerprint["files"], dict):
        raise DatasetQualityError("fingerprint files must be an object")
    declared = fingerprint["files"]
    expected = set(FINGERPRINT_FILE_NAMES)
    if set(declared) != expected:
        raise DatasetQualityError("fingerprint files must exactly match required dataset files")
    if any(not _is_digest(value) for value in declared.values()):
        raise DatasetQualityError("fingerprint file digests must be lowercase SHA-256 values")
    actual: dict[str, str] = {}
    for name in FINGERPRINT_FILE_NAMES:
        path = dataset_dir / name
        if not path.is_file():
            raise DatasetQualityError(f"fingerprint required file is missing: {name}")
        actual[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        if declared[name] != actual[name]:
            raise DatasetQualityError(f"fingerprint hash mismatch: {name}")
    canonical_input = "".join(f"{name}\n{digest}\n" for name, digest in sorted(actual.items())).encode("utf-8")
    expected_dataset_fingerprint = hashlib.sha256(canonical_input).hexdigest()
    if fingerprint.get("dataset_fingerprint") != expected_dataset_fingerprint:
        raise DatasetQualityError("fingerprint dataset_fingerprint mismatch")
    if summary.get("dataset_fingerprint") != expected_dataset_fingerprint:
        raise DatasetQualityError("summary dataset_fingerprint does not match fingerprint")


def check_dataset(dataset_dir: Path, root: Path) -> dict[str, Any]:
    dataset_manifest_path = dataset_dir / "dataset-manifest.json"
    split_manifest_path = dataset_dir / "split-manifest.json"
    validate_manifest(dataset_manifest_path, root / "schemas" / "synthetic-dataset-manifest.schema.json")
    validate_manifest(split_manifest_path, root / "schemas" / "split-manifest.schema.json")
    dataset = load_json(dataset_manifest_path)
    split = load_json(split_manifest_path)
    config_path = _child_path(dataset_dir, dataset["generator_config_path"])
    validate_manifest(config_path, root / "schemas" / "synthetic-generator-config.schema.json")
    config = load_json(config_path)
    rows = _load_jsonl(_child_path(dataset_dir, dataset["data_path"]))
    events = _load_jsonl(_child_path(dataset_dir, dataset["events_path"]), allow_empty=True)
    summary = load_json(_child_path(dataset_dir, dataset["summary_path"]))
    per_equipment, dataset_start, dataset_end, intervals = _check_observations(rows, dataset)
    expected_equipment = {item["equipment_id"] for item in dataset["equipment"]}
    _check_splits(split, rows, expected_equipment, dataset_start, dataset_end)
    _check_events(events, dataset, dataset_start, dataset_end)
    _check_config_semantics(config, dataset, split, summary, rows, events, per_equipment, intervals)
    _check_fingerprint(dataset_dir, dataset, summary)
    return {"status": "pass", "observation_record_count": len(rows), "equipment_count": len(per_equipment), "checks": ["strictly_increasing_utc", "catalog_sampling_interval", "unit_consistency", "quality_keys", "finite_or_null_values", "event_structure", "split_non_overlap_and_coverage", "record_counts", "fingerprint", "future_leakage"]}
