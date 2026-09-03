"""外部依存なしのseed再現可能なsynthetic industrial data generator。"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path, PureWindowsPath
from typing import Any

from .manifest import ManifestValidationError, load_json, validate

GENERATOR_VERSION = "0.1.0"
FINGERPRINT_FILE_NAMES = ("generator-config.json", "observations.jsonl", "events.jsonl", "split-manifest.json", "dataset-manifest.json")
FINGERPRINT_ALGORITHM = "sha256"
FINGERPRINT_CANONICALIZATION = "UTF-8 JSON with sorted keys and compact separators; JSONL row order is equipment order then timestamp order"
FINGERPRINT_KEYS = frozenset({"algorithm", "canonicalization", "dataset_fingerprint", "files"})
SUMMARY_SCHEMA_VERSION = "0.1"
SUMMARY_TYPE = "synthetic-generation"
SUMMARY_KEYS = frozenset({"schema_version", "summary_type", "dataset_id", "generator_version", "seed", "sample_count_per_equipment", "equipment_count", "observation_record_count", "configured_event_count", "disabled_event_count", "event_count", "regime_coverage", "event_coverage", "dataset_fingerprint"})
EVENT_TYPES = ("sensor_drift", "spike", "dropout", "overheating_trend", "jam_or_slip", "stuck_value")
REGIMES = ("stopped", "startup", "low_speed", "nominal", "high_load", "cooldown")
LABELS = ("operating_mode", "recipe_step")
DEFAULT_EVENT_MAGNITUDES = {"sensor_drift": 1.0, "spike": 4.0, "dropout": 0.0, "overheating_trend": 12.0, "jam_or_slip": 0.45, "stuck_value": 0.0}
DEFAULT_EVENT_SIGNALS = {"sensor_drift": "motor_current", "spike": "vibration_feature", "dropout": "motor_temperature", "overheating_trend": "motor_temperature", "jam_or_slip": "conveyor_speed", "stuck_value": "load_proxy"}
SIGNALS = {
    "motor_current": ("motor current", "A", "target"),
    "motor_temperature": ("motor temperature", "degC", "target"),
    "conveyor_speed": ("conveyor speed", "m/s", "target"),
    "load_proxy": ("load proxy", "percent", "covariate"),
    "vibration_feature": ("vibration feature", "mm/s", "target"),
}


class GeneratorError(ValueError):
    """設定または出力先が不安全・不正な場合に発生する。"""


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(_canonical_bytes(value))


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("wb") as handle:
        for row in rows:
            handle.write(_canonical_bytes(row))


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise GeneratorError("start_timestamp must be an explicit UTC timestamp")
    return parsed.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _finite(value: float) -> float:
    if not math.isfinite(value):
        raise GeneratorError("generator produced a non-finite value")
    return round(value, 6)


def _validate_config(config: dict[str, Any], schema_path: Path) -> None:
    try:
        validate(config, load_json(schema_path))
    except ManifestValidationError as exc:
        raise GeneratorError(str(exc)) from exc
    if config["generator_version"] != GENERATOR_VERSION:
        raise GeneratorError(f"unsupported generator_version: {config['generator_version']}")
    count = config["sample_count"]
    equipment_ids = [item["equipment_id"] for item in config["equipment"]]
    if len(equipment_ids) < 2:
        raise GeneratorError("at least two equipment are required for cross_equipment split")
    if len(set(equipment_ids)) != len(equipment_ids):
        raise GeneratorError("equipment_id must be unique")
    regimes = sorted(config["regimes"], key=lambda item: item["start_sample"])
    if regimes[0]["start_sample"] != 0 or regimes[-1]["end_sample"] != count:
        raise GeneratorError("regimes must cover all samples")
    if any(not 0 <= item["start_sample"] < item["end_sample"] <= count for item in regimes):
        raise GeneratorError("regime interval must satisfy 0 <= start < end <= sample_count")
    if any(a["end_sample"] != b["start_sample"] for a, b in zip(regimes, regimes[1:])):
        raise GeneratorError("regime intervals must be contiguous and non-overlapping")
    event_ids: set[str] = set()
    for event in config["events"]:
        if event["event_id"] in event_ids:
            raise GeneratorError("event_id must be unique")
        event_ids.add(event["event_id"])
        if event["equipment_id"] not in equipment_ids:
            raise GeneratorError(f"event references unknown equipment: {event['equipment_id']}")
        if not 0 <= event["start_sample"] < event["end_sample"] <= count:
            raise GeneratorError("event interval must satisfy 0 <= start < end <= sample_count")
        if event["event_type"] not in EVENT_TYPES:
            raise GeneratorError("unsupported event_type")
        if event.get("signal_id") is not None and event["signal_id"] not in SIGNALS:
            raise GeneratorError(f"event signal_id is unknown, including disabled events: {event['signal_id']}")


def _regime_at(regimes: list[dict[str, Any]], index: int) -> dict[str, Any]:
    for regime in regimes:
        if regime["start_sample"] <= index < regime["end_sample"]:
            return regime
    raise GeneratorError(f"no regime for sample {index}")


def _unit(equipment_type: str, signal_id: str) -> str:
    return ("m/s" if equipment_type == "conveyor" else "percent") if signal_id == "conveyor_speed" else SIGNALS[signal_id][1]


def expected_catalog(equipment_id: str, equipment_type: str, sampling_interval_ms: int) -> list[dict[str, Any]]:
    """generator定義から、equipment単位の完全なcatalogを再構成する。"""
    numeric = [
        {"signal_id": f"{equipment_id}.{signal_id}", "name": definition[0], "unit": _unit(equipment_type, signal_id), "role": definition[2], "sampling_interval_ms": sampling_interval_ms}
        for signal_id, definition in SIGNALS.items()
    ]
    labels = [
        {"signal_id": f"{equipment_id}.{label}", "name": label, "unit": "1", "role": "label", "sampling_interval_ms": sampling_interval_ms}
        for label in LABELS
    ]
    return numeric + labels


def event_signal(event: dict[str, Any]) -> str:
    """eventのsignal既定値を適用する。"""
    return event.get("signal_id") or DEFAULT_EVENT_SIGNALS[event["event_type"]]


def effective_event_magnitude(event: dict[str, Any]) -> float:
    """eventの明示値または既定値を返す単一の決定規則。"""
    return float(event.get("magnitude", DEFAULT_EVENT_MAGNITUDES[event["event_type"]]))


def _base_values(equipment_type: str, regime: str, previous_temp: float, rng: random.Random) -> tuple[dict[str, float], float]:
    speed = {"stopped": 0.0, "startup": 35.0, "low_speed": 45.0, "nominal": 70.0, "high_load": 72.0, "cooldown": 20.0}[regime]
    load = {"stopped": 0.0, "startup": 18.0, "low_speed": 32.0, "nominal": 55.0, "high_load": 88.0, "cooldown": 22.0}[regime]
    if equipment_type == "motor":
        current = 1.2 + speed * 0.085 + load * 0.055 + rng.gauss(0.0, 0.08)
        conveyor_speed = speed + rng.gauss(0.0, 0.4)
    else:
        conveyor_speed = speed * 0.018 + rng.gauss(0.0, 0.004)
        current = 0.8 + speed * 0.045 + load * 0.035 + rng.gauss(0.0, 0.06)
    target_temp = 24.0 + current * 0.48 + load * 0.025
    temperature = previous_temp + (target_temp - previous_temp) * 0.12 + rng.gauss(0.0, 0.025)
    vibration = 0.18 + speed * 0.012 + load * 0.009 + abs(rng.gauss(0.0, 0.025))
    return ({"motor_current": current, "motor_temperature": temperature, "conveyor_speed": conveyor_speed, "load_proxy": load + rng.gauss(0.0, 0.45), "vibration_feature": vibration}, temperature)


def _apply_event(values: dict[str, float | None], event: dict[str, Any], index: int, stuck: dict[str, float]) -> tuple[dict[str, float | None], str | None]:
    if not event["enabled"] or not event["start_sample"] <= index < event["end_sample"]:
        return dict(values), None
    event_type = event["event_type"]
    signal_id = event_signal(event)
    if signal_id not in values:
        raise GeneratorError(f"event signal_id is unknown: {signal_id}")
    magnitude = effective_event_magnitude(event)
    progress = (index - event["start_sample"]) / max(1, event["end_sample"] - event["start_sample"] - 1)
    changed = dict(values)
    if event_type in ("sensor_drift", "overheating_trend"):
        if changed[signal_id] is not None:
            changed[signal_id] = float(changed[signal_id]) + magnitude * progress
    elif event_type == "spike":
        if changed[signal_id] is not None:
            changed[signal_id] = float(changed[signal_id]) + magnitude
    elif event_type == "dropout":
        changed[signal_id] = None
    elif event_type == "jam_or_slip":
        if changed[signal_id] is not None:
            changed[signal_id] = max(0.0, float(changed[signal_id]) * max(0.0, 1.0 - magnitude))
        changed["load_proxy"] = min(100.0, float(changed["load_proxy"] or 0.0) + abs(magnitude) * 35.0)
        changed["vibration_feature"] = float(changed["vibration_feature"] or 0.0) + abs(magnitude) * 2.0
    elif event_type == "stuck_value":
        key = f"{event['event_id']}:{signal_id}"
        stuck.setdefault(key, float(changed[signal_id] or 0.0))
        changed[signal_id] = stuck[key]
    return changed, event["event_id"]


def _build_splits(config: dict[str, Any], timestamps: list[datetime], equipment_ids: list[str]) -> dict[str, Any]:
    n = len(timestamps)
    edges = [("train", 0, max(1, n * 6 // 10)), ("validation", max(1, n * 6 // 10), max(2, n * 8 // 10)), ("test", max(2, n * 8 // 10), n)]
    step = timestamps[1] - timestamps[0] if len(timestamps) > 1 else timedelta(milliseconds=config["sampling_interval_ms"])
    chronological = [{"split_id": name, "equipment_ids": equipment_ids, "start_timestamp": _iso(timestamps[start]), "end_timestamp": _iso(timestamps[end - 1] + step), "record_count": (end - start) * len(equipment_ids)} for name, start, end in edges]
    cut = max(1, len(equipment_ids) * 7 // 10)
    cross = [{"split_id": "train", "equipment_ids": equipment_ids[:cut], "start_timestamp": _iso(timestamps[0]), "end_timestamp": _iso(timestamps[-1] + step), "record_count": n * cut}, {"split_id": "test", "equipment_ids": equipment_ids[cut:], "start_timestamp": _iso(timestamps[0]), "end_timestamp": _iso(timestamps[-1] + step), "record_count": n * (len(equipment_ids) - cut)}]
    return {"schema_version": "0.1", "manifest_type": "split", "dataset_id": config["dataset_id"], "generator_version": config["generator_version"], "seed": config["seed"], "sampling_interval_ms": config["sampling_interval_ms"], "sample_count": config["sample_count"], "boundary_semantics": "[start,end)", "strategies": [{"strategy": "chronological", "splits": chronological}, {"strategy": "cross_equipment", "splits": cross}]}


def _resolve_output(root: Path, output: str | Path | None, dataset_id: str) -> Path:
    if output is None:
        return (root / "artifacts" / "generated" / dataset_id).resolve()
    raw = str(output)
    normalized_parts = raw.replace("\\", "/").split("/")
    candidate = Path(output)
    if PureWindowsPath(raw).drive and not candidate.is_absolute():
        raise GeneratorError("drive-qualified output path is not allowed")
    if not candidate.is_absolute() and any(part == ".." for part in normalized_parts):
        raise GeneratorError("relative output path must not contain traversal")
    if not candidate.is_absolute():
        candidate = (root / candidate).resolve()
        if candidate != root and root not in candidate.parents:
            raise GeneratorError("relative output path must remain inside the repository")
    else:
        candidate = candidate.resolve()
        if candidate == root:
            raise GeneratorError("output directory must not be the repository root")
    return candidate


def generate_synthetic(config_path: Path, output: str | Path | None, root: Path) -> Path:
    config = load_json(config_path)
    if not isinstance(config, dict):
        raise GeneratorError("generator config must be a JSON object")
    _validate_config(config, root / "schemas" / "synthetic-generator-config.schema.json")
    target = _resolve_output(root.resolve(), output, config["dataset_id"])
    if target.exists():
        raise GeneratorError(f"refusing to overwrite existing output: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{config['dataset_id']}.", dir=target.parent))
    try:
        start = _parse_utc(config["start_timestamp"])
        interval = timedelta(milliseconds=config["sampling_interval_ms"])
        timestamps = [start + index * interval for index in range(config["sample_count"])]
        equipment = config["equipment"]
        rng = random.Random(config["seed"])
        observations: list[dict[str, Any]] = []
        events: list[dict[str, Any]] = []
        active_events = [event for event in config["events"] if event["enabled"]]
        stuck: dict[str, float] = {}
        for item in equipment:
            temperature = 24.0
            for index, timestamp in enumerate(timestamps):
                regime = _regime_at(config["regimes"], index)
                values, temperature = _base_values(item["equipment_type"], regime["regime"], temperature, rng)
                qualities = {signal_id: "ok" for signal_id in SIGNALS}
                output_values: dict[str, float | None] = dict(values)
                for event in active_events:
                    if event["equipment_id"] != item["equipment_id"]:
                        continue
                    output_values, event_id = _apply_event(output_values, event, index, stuck)
                    if event_id and event["event_type"] == "dropout":
                        qualities[event.get("signal_id") or "motor_temperature"] = "missing"
                signals = {signal_id: {"unit": _unit(item["equipment_type"], signal_id), "value": None if value is None else _finite(float(value))} for signal_id, value in output_values.items()}
                observations.append({"timestamp": _iso(timestamp), "equipment_id": item["equipment_id"], "equipment_type": item["equipment_type"], "operating_mode": regime["regime"], "recipe_step": regime.get("recipe_step", regime["regime"]), "signals": signals, "quality": qualities})
        for event in active_events:
            default_signal = event_signal(event)
            step = interval
            end_timestamp = timestamps[event["end_sample"]] if event["end_sample"] < len(timestamps) else timestamps[-1] + step
            events.append({"event_id": event["event_id"], "event_type": event["event_type"], "equipment_id": event["equipment_id"], "signal_id": default_signal, "start_timestamp": _iso(timestamps[event["start_sample"]]), "end_timestamp": _iso(end_timestamp), "boundary_semantics": "[start,end)", "magnitude": effective_event_magnitude(event), "description": event.get("description", "")})
        catalog = [
            entry
            for item in equipment
            for entry in expected_catalog(item["equipment_id"], item["equipment_type"], config["sampling_interval_ms"])
        ]
        split_manifest = _build_splits(config, timestamps, [item["equipment_id"] for item in equipment])
        _write_json(temporary / "generator-config.json", config)
        _write_jsonl(temporary / "observations.jsonl", observations)
        _write_jsonl(temporary / "events.jsonl", events)
        _write_json(temporary / "split-manifest.json", split_manifest)
        dataset_manifest = {"schema_version": "0.1", "manifest_type": "dataset", "dataset_id": config["dataset_id"], "provenance": "synthetic", "data_path": "observations.jsonl", "events_path": "events.jsonl", "split_manifest_path": "split-manifest.json", "fingerprint_path": "fingerprint.json", "generator_config_path": "generator-config.json", "summary_path": "summary.json", "generator_version": config["generator_version"], "seed": config["seed"], "sampling_interval_ms": config["sampling_interval_ms"], "sample_count": config["sample_count"], "license": "MIT", "equipment": [{"equipment_id": item["equipment_id"], "equipment_type": item["equipment_type"]} for item in equipment], "signals": catalog}
        _write_json(temporary / "dataset-manifest.json", dataset_manifest)
        file_names = FINGERPRINT_FILE_NAMES
        hashes = {name: hashlib.sha256((temporary / name).read_bytes()).hexdigest() for name in file_names}
        fingerprint_input = "".join(f"{name}\n{digest}\n" for name, digest in sorted(hashes.items())).encode("utf-8")
        fingerprint = {"algorithm": FINGERPRINT_ALGORITHM, "canonicalization": FINGERPRINT_CANONICALIZATION, "dataset_fingerprint": hashlib.sha256(fingerprint_input).hexdigest(), "files": hashes}
        _write_json(temporary / "fingerprint.json", fingerprint)
        _write_json(temporary / "summary.json", {"schema_version": SUMMARY_SCHEMA_VERSION, "summary_type": SUMMARY_TYPE, "dataset_id": config["dataset_id"], "generator_version": config["generator_version"], "seed": config["seed"], "sample_count_per_equipment": config["sample_count"], "equipment_count": len(equipment), "observation_record_count": len(observations), "configured_event_count": len(config["events"]), "disabled_event_count": sum(1 for event in config["events"] if not event["enabled"]), "event_count": len(events), "regime_coverage": {regime: sum(item["end_sample"] - item["start_sample"] for item in config["regimes"] if item["regime"] == regime) for regime in REGIMES}, "event_coverage": {event_type: sum(1 for event in events if event["event_type"] == event_type) for event_type in EVENT_TYPES}, "dataset_fingerprint": fingerprint["dataset_fingerprint"]})
        os.replace(temporary, target)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return target
