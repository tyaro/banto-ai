"""既存benchmark予測をイベント区間別に再集計するpost-hoc analyzer。"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import statistics
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path, PureWindowsPath
from typing import Any, Iterable, Mapping

from .benchmark import PREDICTION_KEYS, _revision
from .generator import FINGERPRINT_ALGORITHM, FINGERPRINT_CANONICALIZATION, FINGERPRINT_FILE_NAMES, FINGERPRINT_KEYS
from .manifest import ManifestValidationError, load_json, validate
from .metrics import MetricError, all_metrics, mase
from .quality import check_dataset


class EventSliceError(ValueError):
    """イベントスライス解析の入力または出力契約違反。"""


FORECAST_EXPOSURES = ("target_event", "other_signal_event", "clean")
CONTEXT_EXPOSURES = ("context_target_event", "context_covariate_event", "context_other_signal_event", "context_clean")
EVENT_KEYS = frozenset({"event_id", "event_type", "equipment_id", "signal_id", "start_timestamp", "end_timestamp", "boundary_semantics", "magnitude", "description"})
MATRIX_CELL_STATUSES = frozenset({"success", "partial"})


def _parse_time(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise EventSliceError(f"{label} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EventSliceError(f"{label} is not a valid timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise EventSliceError(f"{label} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise EventSliceError(f"{label} must be a finite number")
    return float(value)


def _repo_path(root: Path, raw: Any, label: str) -> Path:
    if not isinstance(raw, str) or not raw or Path(raw).is_absolute() or PureWindowsPath(raw).drive or "\\" in raw:
        raise EventSliceError(f"{label} must be a repository-relative POSIX path")
    parts = raw.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise EventSliceError(f"{label} must be a normalized repository-relative POSIX path")
    cursor = root
    for part in parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise EventSliceError(f"{label} cannot traverse a repository symlink")
    resolved = (root / raw).resolve()
    if resolved == root or root not in resolved.parents:
        raise EventSliceError(f"{label} must remain inside repository")
    return resolved


def _artifact_output(root: Path, raw: Any) -> Path:
    output = _repo_path(root, raw, "output")
    artifacts = (root / "artifacts").resolve()
    if output == artifacts or artifacts not in output.parents:
        raise EventSliceError("output must be a new directory below artifacts")
    return output


def _direct_child(directory: Path, name: Any, label: str) -> Path:
    if not isinstance(name, str) or not name or PureWindowsPath(name).drive or "\\" in name or len(name.split("/")) != 1 or name in (".", ".."):
        raise EventSliceError(f"{label} must name one direct child file")
    path = (directory / name).resolve()
    if path.parent != directory.resolve():
        raise EventSliceError(f"{label} must remain directly inside its directory")
    return path


def _load_schema(root: Path, name: str) -> dict[str, Any]:
    schema = load_json(root / "schemas" / name)
    if not isinstance(schema, dict):
        raise EventSliceError(f"schema is not an object: {name}")
    return schema


def _validate_schema(value: Any, schema: dict[str, Any], label: str) -> None:
    try:
        validate(value, schema)
    except ManifestValidationError as exc:
        raise EventSliceError(f"{label} does not satisfy its schema: {exc}") from exc


def _strict_jsonl(path: Path, label: str) -> list[dict[str, Any]]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise EventSliceError(f"{label} is unreadable: {path}") from exc
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise EventSliceError(f"{label} must be strict UTF-8") from exc
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            raise EventSliceError(f"{label}:{line_number} is blank")
        try:
            row = json.loads(line, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        except (json.JSONDecodeError, ValueError) as exc:
            raise EventSliceError(f"{label}:{line_number} is not strict JSON") from exc
        if not isinstance(row, dict):
            raise EventSliceError(f"{label}:{line_number} must be a JSON object")
        rows.append(row)
    if not rows:
        raise EventSliceError(f"{label} must not be empty")
    return rows


def _load_json_snapshot(path: Path, label: str) -> tuple[Any, bytes]:
    try:
        raw = path.read_bytes()
        value = json.loads(
            raw.decode("utf-8"),
            parse_constant=lambda constant: (_ for _ in ()).throw(ValueError(constant)),
            parse_float=lambda number: float(number) if math.isfinite(float(number)) else (_ for _ in ()).throw(ValueError(number)),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise EventSliceError(f"{label} is not strict UTF-8 JSON") from exc
    return value, raw


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_dataset(dataset_dir: Path, root: Path) -> dict[str, Any]:
    try:
        quality = check_dataset(dataset_dir, root)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise EventSliceError(f"dataset quality gate failed: {exc}") from exc
    if not isinstance(quality, dict) or quality.get("status") != "pass":
        raise EventSliceError("dataset quality gate did not pass")
    manifest_path = dataset_dir / "dataset-manifest.json"
    _validate_schema(load_json(manifest_path), _load_schema(root, "synthetic-dataset-manifest.schema.json"), "dataset manifest")
    manifest = load_json(manifest_path)
    for field in ("data_path", "events_path", "split_manifest_path", "fingerprint_path", "generator_config_path", "summary_path"):
        path = _direct_child(dataset_dir, manifest[field], f"dataset manifest {field}")
        if not path.is_file():
            raise EventSliceError(f"dataset manifest file is missing: {path.name}")
    fingerprint = load_json(dataset_dir / manifest["fingerprint_path"])
    if not isinstance(fingerprint, dict) or set(fingerprint) != FINGERPRINT_KEYS:
        raise EventSliceError("dataset fingerprint keys are invalid")
    if fingerprint["algorithm"] != FINGERPRINT_ALGORITHM or fingerprint["canonicalization"] != FINGERPRINT_CANONICALIZATION:
        raise EventSliceError("dataset fingerprint algorithm or canonicalization is invalid")
    if set(fingerprint["files"]) != set(FINGERPRINT_FILE_NAMES):
        raise EventSliceError("dataset fingerprint file set is invalid")
    actual: dict[str, str] = {}
    for name in FINGERPRINT_FILE_NAMES:
        path = _direct_child(dataset_dir, name, "fingerprint file")
        actual[name] = _sha256(path)
        if fingerprint["files"][name] != actual[name]:
            raise EventSliceError(f"dataset fingerprint hash mismatch: {name}")
    canonical = "".join(f"{name}\n{digest}\n" for name, digest in sorted(actual.items())).encode("utf-8")
    expected_fingerprint = hashlib.sha256(canonical).hexdigest()
    if fingerprint.get("dataset_fingerprint") != expected_fingerprint:
        raise EventSliceError("dataset fingerprint digest mismatch")
    observations = _strict_jsonl(dataset_dir / manifest["data_path"], "observations.jsonl")
    events = _strict_jsonl(dataset_dir / manifest["events_path"], "events.jsonl") if (dataset_dir / manifest["events_path"]).stat().st_size else []
    equipment = {item["equipment_id"]: item["equipment_type"] for item in manifest["equipment"]}
    signals = {item["signal_id"]: item for item in manifest["signals"]}
    by_equipment: dict[str, list[dict[str, Any]]] = {key: [] for key in equipment}
    for row in observations:
        if row["equipment_id"] not in equipment:
            raise EventSliceError("observation references unknown equipment")
        by_equipment[row["equipment_id"]].append(row)
    time_index: dict[str, dict[datetime, int]] = {}
    for equipment_id, rows in by_equipment.items():
        time_index[equipment_id] = {}
        for index, row in enumerate(rows):
            stamp = _parse_time(row["timestamp"], "observation timestamp")
            if stamp in time_index[equipment_id]:
                raise EventSliceError(f"duplicate observation timestamp: {equipment_id}/{row['timestamp']}")
            time_index[equipment_id][stamp] = index
    normalized_events: list[dict[str, Any]] = []
    event_ids: set[str] = set()
    for event in events:
        if set(event) not in (EVENT_KEYS, EVENT_KEYS | {"enabled"}):
            raise EventSliceError("event contains an unexpected key")
        if not isinstance(event.get("enabled", True), bool) or not event.get("enabled", True):
            continue
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or not event_id or event_id in event_ids:
            raise EventSliceError("event IDs must be unique non-empty strings")
        event_ids.add(event_id)
        equipment_id = event.get("equipment_id")
        short_signal = event.get("signal_id")
        full_signal = f"{equipment_id}.{short_signal}" if isinstance(equipment_id, str) and isinstance(short_signal, str) and f"{equipment_id}.{short_signal}" in signals else short_signal
        if equipment_id not in equipment or full_signal not in signals or signals[full_signal]["signal_id"] != full_signal:
            raise EventSliceError(f"event references unknown equipment or signal: {event_id}")
        start = _parse_time(event.get("start_timestamp"), "event start_timestamp")
        end = _parse_time(event.get("end_timestamp"), "event end_timestamp")
        if start >= end or event.get("boundary_semantics") != "[start,end)":
            raise EventSliceError(f"event interval is invalid: {event_id}")
        _finite(event.get("magnitude"), f"event magnitude {event_id}")
        if not isinstance(event.get("event_type"), str) or not isinstance(event.get("description"), str):
            raise EventSliceError(f"event metadata is invalid: {event_id}")
        normalized_events.append({**event, "signal_id": full_signal, "start": start, "end": end})
    split = load_json(dataset_dir / manifest["split_manifest_path"])
    chronological = next((item for item in split.get("strategies", []) if item.get("strategy") == "chronological"), None)
    if not chronological or [item.get("split_id") for item in chronological.get("splits", [])] != ["train", "validation", "test"]:
        raise EventSliceError("dataset split manifest lacks chronological train/validation/test")
    split_times = {item["split_id"]: (_parse_time(item["start_timestamp"], "split start"), _parse_time(item["end_timestamp"], "split end")) for item in chronological["splits"]}
    return {"manifest": manifest, "fingerprint": fingerprint, "fingerprint_digest": expected_fingerprint, "observations": by_equipment, "time_index": time_index, "events": normalized_events, "signals": signals, "split_times": split_times, "quality": quality}


def _normalize_ids(values: Iterable[str] | None, equipment_id: str, signals: Mapping[str, Any], role: str | None = None) -> set[str]:
    result: set[str] = set()
    for value in values or ():
        key = str(value).rsplit(".", 1)[-1]
        full = str(value) if str(value) in signals else f"{equipment_id}.{key}"
        if full in signals and not full.startswith(f"{equipment_id}."):
            raise EventSliceError(f"configured {role or 'signal'} belongs to another equipment: {value}")
        item = signals.get(full)
        if item is None or (role is not None and item.get("role") != role):
            raise EventSliceError(f"configured {role or 'signal'} is invalid for {equipment_id}: {value}")
        result.add(full)
    return result


def _event_overlap(event: Mapping[str, Any], start: datetime, end: datetime) -> bool:
    return event["start"] < end and event["end"] > start


def _classify_forecast(events: list[dict[str, Any]], equipment_id: str, target: str, stamp: datetime) -> tuple[str, list[dict[str, Any]]]:
    overlapping = _forecast_overlapping(events, equipment_id, stamp)
    target_events = [event for event in overlapping if event["signal_id"] == target]
    if target_events:
        return "target_event", target_events
    return ("other_signal_event", overlapping) if overlapping else ("clean", [])


def _forecast_overlapping(events: list[dict[str, Any]], equipment_id: str, stamp: datetime) -> list[dict[str, Any]]:
    return [event for event in events if event["equipment_id"] == equipment_id and _event_overlap(event, stamp, stamp + timedelta(microseconds=1))]


def _classify_context(events: list[dict[str, Any]], equipment_id: str, target: str, past_covariates: set[str], future_covariates: set[str], origin: datetime, context_length: int, interval: timedelta) -> tuple[str, list[dict[str, Any]]]:
    overlapping = _context_overlapping(events, equipment_id, origin, context_length, interval)
    target_events = [event for event in overlapping if event["signal_id"] == target]
    covariate_events = [event for event in overlapping if event["signal_id"] in past_covariates or event["signal_id"] in future_covariates]
    if target_events:
        return "context_target_event", target_events
    if covariate_events:
        return "context_covariate_event", covariate_events
    return ("context_other_signal_event", overlapping) if overlapping else ("context_clean", [])


def _context_overlapping(events: list[dict[str, Any]], equipment_id: str, origin: datetime, context_length: int, interval: timedelta) -> list[dict[str, Any]]:
    start = origin - context_length * interval
    return [event for event in events if event["equipment_id"] == equipment_id and _event_overlap(event, start, origin)]


def _metric(points: list[dict[str, Any]], scale_by_equipment: Mapping[str, list[float]]) -> dict[str, Any]:
    actual = [point["actual"] for point in points]
    predicted = [point["point_forecast"] for point in points]
    quantile_values = {float(q): [point["quantiles"][q] for point in points] for q in points[0]["quantiles"]}
    result = all_metrics(actual, predicted, [], quantile_values)
    result.pop("mase_status", None)
    try:
        point_mase = [
            mase((point["actual"],), (point["point_forecast"],), scale_by_equipment[point["equipment_id"]])
            for point in points
        ]
        result["mase"] = statistics.fmean(point_mase)
    except (KeyError, MetricError) as exc:
        result["mase_status"] = "inconclusive: " + str(exc)
    return {"count": len(points), **result}


def _cell_metric_rows(points: list[dict[str, Any]], dataset: Mapping[str, Any], horizon: int, context_length: int) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str, str, str], list[dict[str, Any]]] = {}
    for point in points:
        grouped.setdefault((point["dimension"], point["exposure"], point.get("operating_mode", ""), point["model"], point["target_signal_key"], point["unit"]), []).append(point)
    rows: list[dict[str, Any]] = []
    for (dimension, exposure, mode, model, target_key, unit), items in sorted(grouped.items()):
        scale_by_equipment = {
            equipment_id: [
                float(row["signals"][target_key]["value"])
                for row in equipment_rows
                if _parse_time(row["timestamp"], "observation timestamp") < dataset["split_times"]["validation"][0]
                and row["signals"][target_key]["value"] is not None
            ]
            for equipment_id, equipment_rows in dataset["observations"].items()
        }
        row: dict[str, Any] = {"dimension": dimension, "exposure": exposure, "operating_mode": mode or None, "model": model, "target_signal_key": target_key, "unit": unit, "horizon": horizon, "context_length": context_length, "metrics": _metric(items, scale_by_equipment)}
        rows.append(row)
    return rows


def _summary_stats(values: list[float]) -> dict[str, float | None]:
    return {"mean": statistics.fmean(values), "min": min(values), "max": max(values), "sample_stddev": statistics.stdev(values) if len(values) > 1 else None}


def _macro(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in rows:
        key = (row["dimension"], row["exposure"], row["operating_mode"], row["model"], row["target_signal_key"], row["unit"], row["horizon"], row["context_length"])
        grouped.setdefault(key, []).append(row)
    output: list[dict[str, Any]] = []
    for key, items in sorted(grouped.items(), key=lambda pair: tuple("" if value is None else str(value) for value in pair[0])):
        metrics: dict[str, Any] = {}
        metric_names = ("mae", "rmse", "mase", "wis", "nominal_interval_coverage", "interval_width")
        for name in metric_names:
            values = [item["metrics"][name] for item in items if name in item["metrics"]]
            if len(values) == len(items):
                metrics[name] = _summary_stats([float(value) for value in values])
        counts = [int(item["metrics"]["count"]) for item in items]
        output.append({"dimension": key[0], "exposure": key[1], "operating_mode": key[2], "model": key[3], "target_signal_key": key[4], "unit": key[5], "horizon": key[6], "context_length": key[7], "cell_count": len(items), "total_point_count": sum(counts), "metrics": metrics})
    return output


def _json_bytes(value: Any) -> bytes:
    try:
        return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise EventSliceError(f"result contains a non-serializable or non-finite value: {exc}") from exc


def _load_predictions(path: Path, result: Mapping[str, Any], dataset: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = _strict_jsonl(path, "predictions.jsonl")
    config = result["run_config"]
    quantile_keys = [str(q) for q in config["quantiles"]]
    models = {model["name"] for model in config["models"]}
    configured_equipment = set(config.get("equipment_ids") or dataset["observations"])
    configured_targets = set(config.get("target_signal_ids") or ())
    identity: set[tuple[Any, ...]] = set()
    grouped_leads: dict[tuple[str, str, str, str], set[int]] = {}
    normalized: list[dict[str, Any]] = []
    for index, row in enumerate(rows, 1):
        if set(row) != PREDICTION_KEYS:
            raise EventSliceError(f"prediction row {index} has an unexpected key set")
        if row["model"] not in models or row["split"] != "test" or row["equipment_id"] not in configured_equipment:
            raise EventSliceError(f"prediction row {index} has invalid model, equipment, or split")
        equipment_id = row["equipment_id"]
        target = row["target_signal_id"]
        if not isinstance(target, str) or not target.startswith(f"{equipment_id}.") or target not in dataset["signals"] or dataset["signals"][target]["role"] != "target":
            raise EventSliceError(f"prediction row {index} target signal is invalid")
        if configured_targets and target.rsplit(".", 1)[-1] not in {str(value).rsplit(".", 1)[-1] for value in configured_targets}:
            raise EventSliceError(f"prediction row {index} target is outside run_config")
        if not isinstance(row["lead_time"], int) or isinstance(row["lead_time"], bool) or not 1 <= row["lead_time"] <= result["run_config"]["horizon"]:
            raise EventSliceError(f"prediction row {index} lead_time is invalid")
        if not isinstance(row["quantiles"], dict) or list(row["quantiles"]) != quantile_keys:
            raise EventSliceError(f"prediction row {index} quantile keys are invalid or unordered")
        values = [row["actual"], row["point_forecast"], *row["quantiles"].values()]
        for value in values:
            _finite(value, f"prediction row {index} value")
        q_values = [float(row["quantiles"][key]) for key in quantile_keys]
        if any(left > right for left, right in zip(q_values, q_values[1:])):
            raise EventSliceError(f"prediction row {index} has quantile crossing")
        origin = _parse_time(row["origin_timestamp"], f"prediction row {index} origin_timestamp")
        stamp = _parse_time(row["timestamp"], f"prediction row {index} timestamp")
        index_map = dataset["time_index"].get(equipment_id, {})
        if origin not in index_map:
            raise EventSliceError(f"prediction row {index} origin does not match an observation timestamp")
        # benchmark.py emits lead_time as a one-based label for the zero-based
        # forecast offset, so lead_time=1 is the observation at origin.
        forecast_index = index_map[origin] + row["lead_time"] - 1
        observations = dataset["observations"][equipment_id]
        if forecast_index >= len(observations):
            raise EventSliceError(f"prediction row {index} lead extends beyond observations")
        expected_stamp = _parse_time(observations[forecast_index]["timestamp"], "forecast observation timestamp")
        actual_observation = observations[forecast_index]["signals"][target.rsplit(".", 1)[-1]]["value"]
        if actual_observation is None or float(actual_observation) != float(row["actual"]):
            raise EventSliceError(f"prediction row {index} actual does not match observations")
        if stamp != expected_stamp or row["operating_mode"] != observations[forecast_index]["operating_mode"]:
            raise EventSliceError(f"prediction row {index} timestamp or operating_mode is not aligned to observations")
        test_start, test_end = dataset["split_times"]["test"]
        if origin < test_start or stamp < test_start or stamp >= test_end:
            raise EventSliceError(f"prediction row {index} is outside the chronological test split")
        key = (row["model"], equipment_id, target, origin, row["lead_time"])
        if key in identity:
            raise EventSliceError(f"duplicate prediction row identity: {key}")
        identity.add(key)
        group_key = (row["model"], equipment_id, target, origin)
        grouped_leads.setdefault(group_key, set()).add(row["lead_time"])
        normalized.append({**row, "origin": origin, "stamp": stamp, "target_signal_key": target.rsplit(".", 1)[-1], "unit": dataset["signals"][target]["unit"], "equipment_index": forecast_index})
    if len(rows) != result["prediction_count"]:
        raise EventSliceError("prediction_count does not match predictions.jsonl")
    expected_leads = set(range(1, result["run_config"]["horizon"] + 1))
    if any(leads != expected_leads for leads in grouped_leads.values()):
        raise EventSliceError("each prediction origin must have one complete horizon")
    return normalized


def _prediction_completeness(result: Mapping[str, Any], dataset: Mapping[str, Any], predictions: list[dict[str, Any]]) -> dict[str, Any]:
    config = result["run_config"]
    model_names = [model["name"] for model in config["models"]]
    if len(model_names) != len(set(model_names)):
        raise EventSliceError("run_config model names must be unique")
    configured_equipment = config.get("equipment_ids")
    if configured_equipment is not None and len(configured_equipment) != len(set(configured_equipment)):
        raise EventSliceError("run_config equipment_ids must be unique")
    configured_targets = config.get("target_signal_ids")
    if configured_targets is not None:
        logical_targets = [str(value).rsplit(".", 1)[-1] for value in configured_targets]
        if len(logical_targets) != len(set(logical_targets)):
            raise EventSliceError("run_config target_signal_ids must be unique by logical target key")
    equipment_ids = tuple(config.get("equipment_ids") or dataset["observations"])
    targets_by_equipment: dict[str, set[str]] = {}
    for equipment_id in equipment_ids:
        configured = config.get("target_signal_ids")
        if configured is None:
            configured = [signal_id for signal_id, item in dataset["signals"].items() if item["role"] == "target" and signal_id.startswith(f"{equipment_id}.")]
        targets_by_equipment[equipment_id] = _normalize_ids(configured, equipment_id, dataset["signals"], "target")
    selected = result["provenance"]["origin_selection"]["test"]
    if set(selected) != set(equipment_ids):
        raise EventSliceError("test origin selection equipment keys must match run_config equipment_ids")
    expected_groups: set[tuple[str, str, str, datetime]] = set()
    for equipment_id in equipment_ids:
        selection = selected.get(equipment_id)
        if not isinstance(selection, dict) or not isinstance(selection.get("indices"), list):
            raise EventSliceError(f"test origin selection is missing for {equipment_id}")
        expected_stride = config.get("test_origin_stride", config["horizon"])
        expected_max_origins = config.get("max_test_origins")
        if selection.get("count") != len(selection["indices"]) or selection.get("stride") != expected_stride or selection.get("max_origins") != expected_max_origins or selection.get("rule") != "chronological range with configured stride; endpoint-inclusive uniform cap when max_origins is set":
            raise EventSliceError(f"test origin selection metadata does not match run_config: {equipment_id}")
        seen_indices: set[int] = set()
        test_start, test_end = dataset["split_times"]["test"]
        rows = dataset["observations"][equipment_id]
        for origin_index in selection["indices"]:
            if not isinstance(origin_index, int) or isinstance(origin_index, bool) or origin_index in seen_indices or not 0 <= origin_index < len(rows):
                raise EventSliceError(f"test origin selection is invalid for {equipment_id}")
            seen_indices.add(origin_index)
            origin = _parse_time(rows[origin_index]["timestamp"], "selected test origin")
            if origin < test_start or origin + config["horizon"] * timedelta(milliseconds=dataset["manifest"]["sampling_interval_ms"]) > test_end:
                raise EventSliceError(f"selected test origin is outside a complete test horizon: {equipment_id}/{origin_index}")
            for target in targets_by_equipment[equipment_id]:
                for model in config["models"]:
                    expected_groups.add((model["name"], equipment_id, target, origin))
    expected_leads = set(range(1, config["horizon"] + 1))
    observed: dict[tuple[str, str, str, datetime], set[int]] = {}
    for prediction in predictions:
        key = (prediction["model"], prediction["equipment_id"], prediction["target_signal_id"], prediction["origin"])
        observed.setdefault(key, set()).add(prediction["lead_time"])
    unexpected = set(observed) - expected_groups
    if unexpected:
        sample = next(iter(unexpected))
        raise EventSliceError(f"prediction completeness contains an unselected origin or group: {sample}")
    expected_domain = {(model, equipment_id, target) for model, equipment_id, target, _origin in expected_groups}
    failure_keys = {(failure["model"], failure["equipment_id"], failure["target_signal_id"]) for failure in result["failures"]}
    if len(failure_keys) != len(result["failures"]):
        raise EventSliceError("result failures must not repeat a model/equipment/target key")
    if not failure_keys <= expected_domain:
        raise EventSliceError("result failure is outside the expected prediction group domain")
    if result["status"] == "success" and result["failures"]:
        raise EventSliceError("success result must not contain failure records")
    if result["status"] == "partial" and not result["failures"]:
        raise EventSliceError("partial result must contain at least one failure record")
    missing: list[dict[str, Any]] = []
    for group in sorted(expected_groups, key=lambda item: (item[0], item[1], item[2], item[3].isoformat())):
        leads = observed.get(group, set())
        if leads != expected_leads:
            model, equipment_id, target, origin = group
            missing.append({"model": model, "equipment_id": equipment_id, "target_signal_id": target, "origin_timestamp": origin.isoformat(), "expected_leads": sorted(expected_leads), "observed_leads": sorted(leads), "failure_recorded": (model, equipment_id, target) in failure_keys})
    unaccounted = [item for item in missing if not item["failure_recorded"]]
    if unaccounted:
        raise EventSliceError(f"prediction completeness has unaccounted missing groups: {unaccounted[0]}")
    if result["status"] == "success" and missing:
        raise EventSliceError("success cell has incomplete prediction groups")
    return {"expected_prediction_count": len(expected_groups) * config["horizon"], "observed_prediction_count": len(predictions), "expected_group_count": len(expected_groups), "observed_group_count": sum(leads == expected_leads for leads in observed.values()), "missing_groups": missing}


def _validate_cell(cell: Mapping[str, Any], matrix: Mapping[str, Any], result: Mapping[str, Any], result_path: Path, root: Path) -> None:
    if result["run_id"] != cell["run_id"] or result["seed"] != cell["seed"] or result["dataset_fingerprint"] != cell["dataset_fingerprint"] or result["status"] != cell["status"]:
        raise EventSliceError(f"cell/result identity mismatch: {cell['cell_id']}")
    if result["run_config"]["run_id"] != cell["run_id"] or result["run_config"].get("seed") != cell["seed"] or result["run_config"]["horizon"] != cell["horizon"] or result["run_config"]["context_length"] != cell["context_length"] or result["run_config"]["dataset_path"] != cell["dataset_path"] or result["run_config"]["output_dir"] != cell["output_dir"]:
        raise EventSliceError(f"cell axes or paths do not match result: {cell['cell_id']}")
    if len(result["failures"]) != cell["benchmark_failure_count"]:
        raise EventSliceError(f"cell failure count does not match result: {cell['cell_id']}")
    if result["code_revision"] != matrix["code_revision"]:
        raise EventSliceError(f"cell code revision does not match matrix code revision: {cell['cell_id']}")
    expected_result_path = _direct_child((root / cell["output_dir"]).resolve(), "result.json", "cell result path")
    if result_path != expected_result_path:
        raise EventSliceError(f"cell result_path must be output_dir/result.json: {cell['cell_id']}")


def _validate_matrix_semantics(matrix: Mapping[str, Any]) -> None:
    axes = matrix["axes"]
    seeds, horizons, contexts = axes["seeds"], axes["horizons"], axes["context_lengths"]
    if any(len(values) != len(set(values)) for values in (seeds, horizons, contexts)):
        raise EventSliceError("matrix axes must be unique")
    cells = matrix["cells"]
    if len({cell["cell_id"] for cell in cells}) != len(cells):
        raise EventSliceError("matrix cell_id values must be unique")
    tuples = [(cell["seed"], cell["horizon"], cell["context_length"]) for cell in cells]
    if len(set(tuples)) != len(tuples):
        raise EventSliceError("matrix axis tuples must be unique")
    expected_tuples = {(seed, horizon, context) for seed in seeds for horizon in horizons for context in contexts}
    if set(tuples) != expected_tuples:
        raise EventSliceError("matrix cells must equal the declared axis Cartesian product")
    if any(seed not in seeds or horizon not in horizons or context not in contexts for seed, horizon, context in tuples):
        raise EventSliceError("matrix cell axes are outside matrix axes")
    counts = matrix["counts"]
    actual_counts = {
        "total_cells": len(cells),
        "successful_cells": sum(cell["status"] == "success" for cell in cells),
        "partial_cells": sum(cell["status"] == "partial" for cell in cells),
        "failed_cells": sum(cell["status"] == "failed" for cell in cells),
        "completed_cells": sum(cell["status"] != "failed" for cell in cells),
    }
    if any(counts[key] != value for key, value in actual_counts.items()):
        raise EventSliceError("matrix counts do not match cell statuses")
    expected_status = "failed" if actual_counts["completed_cells"] == 0 else "success" if actual_counts["successful_cells"] == actual_counts["total_cells"] else "partial"
    if matrix["status"] != expected_status:
        raise EventSliceError("matrix status does not match cell statuses")
    datasets = matrix["datasets"]
    for field in ("dataset_id", "dataset_path", "seed"):
        values = [dataset[field] for dataset in datasets]
        if len(values) != len(set(values)):
            raise EventSliceError(f"matrix dataset {field} values must be unique")
    dataset_ids = {dataset["dataset_id"] for dataset in datasets}
    if {dataset["seed"] for dataset in datasets} != set(seeds):
        raise EventSliceError("matrix dataset seed set must equal matrix axes seeds")
    if any(cell["dataset_id"] not in dataset_ids for cell in cells):
        raise EventSliceError("matrix cell references an unknown dataset")


def analyze_event_slices(matrix_result: str | Path, output: str | Path, root: str | Path) -> Path:
    """既存matrix resultからイベントスライス結果を新規atomic出力する。"""
    root_path = Path(root).expanduser().resolve()
    matrix_path = _repo_path(root_path, str(matrix_result), "matrix-result")
    output_path = _artifact_output(root_path, str(output))
    if not matrix_path.is_file():
        raise EventSliceError(f"matrix result does not exist: {matrix_result}")
    if output_path.exists():
        raise EventSliceError(f"refusing to overwrite existing output: {output_path}")
    matrix_source_dir = matrix_path.parent
    if output_path == matrix_source_dir or output_path in matrix_source_dir.parents or matrix_source_dir in output_path.parents:
        raise EventSliceError("source matrix result and output must be disjoint")
    matrix, matrix_bytes = _load_json_snapshot(matrix_path, "matrix result")
    _validate_schema(matrix, _load_schema(root_path, "benchmark-matrix-result.schema.json"), "matrix result")
    _validate_matrix_semantics(matrix)
    matrix_code_revision = matrix["code_revision"]
    dataset_by_id = {dataset["dataset_id"]: dataset for dataset in matrix["datasets"]}
    if len(dataset_by_id) != len(matrix["datasets"]):
        raise EventSliceError("matrix dataset IDs must be unique")
    dataset_cache: dict[Path, dict[str, Any]] = {}
    analyzed_cells: list[dict[str, Any]] = []
    all_cell_metric_rows: list[dict[str, Any]] = []
    total_predictions = 0
    analyzed_predictions = 0
    excluded_by_status: dict[str, int] = {"failed": 0}
    all_forecast_counts = {key: 0 for key in FORECAST_EXPOSURES}
    all_context_counts = {key: 0 for key in CONTEXT_EXPOSURES}
    for cell in matrix["cells"]:
        base_cell = {"cell_id": cell["cell_id"], "run_id": cell["run_id"], "seed": cell["seed"], "horizon": cell["horizon"], "context_length": cell["context_length"], "dataset_id": cell["dataset_id"], "status": cell["status"], "analyzed": False, "prediction_count": 0, "analyzed_prediction_count": 0, "excluded_prediction_count": 0, "completeness": {"expected_prediction_count": 0, "observed_prediction_count": 0, "expected_group_count": 0, "observed_group_count": 0, "missing_groups": []}, "source_failures": [], "failure": cell.get("failure"), "forecast_exposure_counts": {key: 0 for key in FORECAST_EXPOSURES}, "context_exposure_counts": {key: 0 for key in CONTEXT_EXPOSURES}, "operating_mode_counts": {}, "event_coverage": [], "event_provenance": {"forecast": {}, "context": {}}, "metric_rows": []}
        cell_dataset_dir = _repo_path(root_path, cell["dataset_path"], "cell dataset_path")
        cell_output_dir = _repo_path(root_path, cell["output_dir"], "cell output_dir")
        if output_path == cell_dataset_dir or output_path in cell_dataset_dir.parents or cell_dataset_dir in output_path.parents or output_path == cell_output_dir or output_path in cell_output_dir.parents or cell_output_dir in output_path.parents:
            raise EventSliceError(f"analysis output overlaps source dataset or cell output: {cell['cell_id']}")
        if cell["status"] not in MATRIX_CELL_STATUSES or not cell.get("result_path"):
            excluded_by_status[cell["status"]] = excluded_by_status.get(cell["status"], 0) + 1
            analyzed_cells.append(base_cell)
            continue
        dataset_entry = dataset_by_id.get(cell["dataset_id"])
        if dataset_entry is None or dataset_entry["dataset_path"] != cell["dataset_path"] or dataset_entry["seed"] != cell["seed"] or dataset_entry["dataset_fingerprint"] != cell["dataset_fingerprint"]:
            raise EventSliceError(f"matrix cell dataset identity mismatch: {cell['cell_id']}")
        dataset_dir = cell_dataset_dir
        if dataset_dir not in dataset_cache:
            dataset_cache[dataset_dir] = _verify_dataset(dataset_dir, root_path)
        dataset = dataset_cache[dataset_dir]
        if dataset["fingerprint_digest"] != cell["dataset_fingerprint"]:
            raise EventSliceError(f"dataset fingerprint mismatch: {cell['cell_id']}")
        result_path = _repo_path(root_path, cell["result_path"], "cell result_path")
        result = load_json(result_path)
        _validate_schema(result, _load_schema(root_path, "benchmark-result.schema.json"), f"cell result {cell['cell_id']}")
        _validate_cell(cell, matrix, result, result_path, root_path)
        prediction_path = _direct_child(result_path.parent, "predictions.jsonl", "predictions path")
        prediction_hash_before = _sha256(prediction_path)
        predictions = _load_predictions(prediction_path, result, dataset)
        if _sha256(prediction_path) != prediction_hash_before:
            raise EventSliceError(f"predictions.jsonl changed during analysis: {cell['cell_id']}")
        completeness = _prediction_completeness(result, dataset, predictions)
        base_cell["analyzed"] = True
        base_cell["prediction_count"] = len(predictions)
        base_cell["analyzed_prediction_count"] = len(predictions)
        base_cell["excluded_prediction_count"] = completeness["expected_prediction_count"] - completeness["observed_prediction_count"]
        base_cell["completeness"] = completeness
        base_cell["source_failures"] = result["failures"]
        analyzed_predictions += len(predictions)
        total_predictions += len(predictions)
        target_ids_by_equipment: dict[str, set[str]] = {}
        past_by_equipment: dict[str, set[str]] = {}
        future_by_equipment: dict[str, set[str]] = {}
        for equipment_id in dataset["observations"]:
            configured_targets = result["run_config"].get("target_signal_ids")
            if configured_targets is None:
                configured_targets = [signal_id for signal_id, item in dataset["signals"].items() if item["role"] == "target" and signal_id.startswith(f"{equipment_id}.")]
            target_ids_by_equipment[equipment_id] = _normalize_ids(configured_targets, equipment_id, dataset["signals"], "target")
            past_by_equipment[equipment_id] = _normalize_ids(result["run_config"].get("past_only_covariate_ids"), equipment_id, dataset["signals"], "covariate")
            future_by_equipment[equipment_id] = _normalize_ids(result["run_config"].get("known_future_covariate_ids"), equipment_id, dataset["signals"], "covariate")
        interval = timedelta(milliseconds=min(item["sampling_interval_ms"] for item in dataset["manifest"]["signals"]))
        points: list[dict[str, Any]] = []
        event_coverage: dict[str, dict[str, Any]] = {}
        for event in dataset["events"]:
            roles = []
            for equipment_id in dataset["observations"]:
                if event["equipment_id"] == equipment_id:
                    if event["signal_id"] in target_ids_by_equipment[equipment_id]:
                        roles.append("target")
                    elif event["signal_id"] in past_by_equipment[equipment_id] or event["signal_id"] in future_by_equipment[equipment_id]:
                        roles.append("covariate")
                    else:
                        roles.append("other")
            test_start, test_end = dataset["split_times"]["test"]
            event_coverage[event["event_id"]] = {"event_id": event["event_id"], "event_type": event["event_type"], "equipment_id": event["equipment_id"], "signal_id": event["signal_id"], "roles": sorted(set(roles)), "overlaps_test_split": _event_overlap(event, test_start, test_end), "forecast_point_count": 0, "context_point_count": 0, "covered_by_forecast_timestamp": False, "covered_by_context_window": False}
        for prediction in predictions:
            equipment_id = prediction["equipment_id"]
            target = prediction["target_signal_id"]
            forecast_exposure, forecast_events = _classify_forecast(dataset["events"], equipment_id, target, prediction["stamp"])
            context_exposure, context_events = _classify_context(dataset["events"], equipment_id, target, past_by_equipment[equipment_id], future_by_equipment[equipment_id], prediction["origin"], result["run_config"]["context_length"], interval)
            all_forecast_events = _forecast_overlapping(dataset["events"], equipment_id, prediction["stamp"])
            all_context_events = _context_overlapping(dataset["events"], equipment_id, prediction["origin"], result["run_config"]["context_length"], interval)
            for event in all_forecast_events:
                event_coverage[event["event_id"]]["forecast_point_count"] += 1
                event_coverage[event["event_id"]]["covered_by_forecast_timestamp"] = True
            for event in all_context_events:
                event_coverage[event["event_id"]]["context_point_count"] += 1
                event_coverage[event["event_id"]]["covered_by_context_window"] = True
            operating_mode = prediction["operating_mode"]
            base_cell["forecast_exposure_counts"][forecast_exposure] += 1
            base_cell["context_exposure_counts"][context_exposure] += 1
            base_cell["operating_mode_counts"][operating_mode] = base_cell["operating_mode_counts"].get(operating_mode, 0) + 1
            for dimension, exposure, events in (("forecast_exposure", forecast_exposure, all_forecast_events), ("context_exposure", context_exposure, all_context_events)):
                base_cell["event_provenance"]["forecast" if dimension == "forecast_exposure" else "context"].setdefault(exposure, set()).update(event["event_id"] for event in events)
            common = {"model": prediction["model"], "equipment_id": equipment_id, "target_signal_key": prediction["target_signal_key"], "unit": prediction["unit"], "actual": prediction["actual"], "point_forecast": prediction["point_forecast"], "quantiles": prediction["quantiles"]}
            points.append({**common, "dimension": "forecast_exposure", "exposure": forecast_exposure, "operating_mode": None})
            points.append({**common, "dimension": "context_exposure", "exposure": context_exposure, "operating_mode": None})
            points.append({**common, "dimension": "operating_mode", "exposure": forecast_exposure, "operating_mode": operating_mode})
        base_cell["event_coverage"] = sorted(event_coverage.values(), key=lambda item: item["event_id"])
        base_cell["event_provenance"] = {dimension: {key: sorted(value) for key, value in exposures.items()} for dimension, exposures in base_cell["event_provenance"].items()}
        base_cell["metric_rows"] = _cell_metric_rows(points, dataset, cell["horizon"], cell["context_length"])
        all_cell_metric_rows.extend(base_cell["metric_rows"])
        for key, value in base_cell["forecast_exposure_counts"].items():
            all_forecast_counts[key] += value
        for key, value in base_cell["context_exposure_counts"].items():
            all_context_counts[key] += value
        analyzed_cells.append(base_cell)
    macro = _macro(all_cell_metric_rows)
    limitations = ["この出力は既存の成功・部分成功予測にイベントラベルを事後付与した探索的集計であり、再推論を行わない。", "イベントスライス分類は予測timestampとcontext windowの重なりに基づくため、未選択・未観測・stale予測の頑健性や異常検知性能を測定しない。", "seedはpoolせず、cell metricのmacro mean/min/max/sample stddevとして要約する。", "イベントのcovered_by_forecast_timestamp=falseは、そのイベントが予測timestampで一度も評価されていないことを示し、評価済みとは解釈しない。"]
    if any(event["overlaps_test_split"] and not event["covered_by_forecast_timestamp"] for cell in analyzed_cells for event in cell["event_coverage"]):
        limitations.append("test splitと重なるが選択originの予測timestampで未coverのイベントが存在するため、イベント全体の性能評価ではない。")
    if any(cell["completeness"]["missing_groups"] for cell in analyzed_cells):
        limitations.append("partial cellにsource failureと対応する欠落prediction groupがあるため、macro summaryは完全なsuccess matrixと同等に解釈しない。")
    if any(not cell["analyzed"] for cell in analyzed_cells):
        limitations.append(f"{sum(not cell['analyzed'] for cell in analyzed_cells)} cell(s) were excluded because no analyzable success/partial result_path was available.")
    result = {"schema_version": "0.1", "result_type": "benchmark-event-slices", "matrix_result_path": str(Path(matrix_result).as_posix()), "matrix_id": matrix["matrix_id"], "status": "partial" if any(cell["status"] != "success" or not cell["analyzed"] for cell in analyzed_cells) else "success", "matrix_code_revision": matrix_code_revision, "analyzer_code_revision": _revision(root_path), "source_matrix_sha256": hashlib.sha256(matrix_bytes).hexdigest(), "counts": {"total_cells": len(matrix["cells"]), "analyzed_cells": sum(cell["analyzed"] for cell in analyzed_cells), "excluded_cells": sum(not cell["analyzed"] for cell in analyzed_cells), "excluded_by_status": excluded_by_status, "total_prediction_count": total_predictions, "analyzed_prediction_count": analyzed_predictions, "forecast_exposure_counts": all_forecast_counts, "context_exposure_counts": all_context_counts}, "cells": analyzed_cells, "macro_summary": macro, "research_only_notice": "研究・探索専用。既存予測へのpost-hocイベントsliceラベル付与であり、モデルの再推論、missing/stale robustness、異常検知性能の評価ではない。", "limitations": limitations}
    _validate_schema(result, _load_schema(root_path, "benchmark-event-slice-result.schema.json"), "event slice result")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output_path.name}.", dir=output_path.parent))
    try:
        (temporary / "result.json").write_bytes(_json_bytes(result))
        (temporary / "summary.md").write_text(_summary_markdown(result), encoding="utf-8", newline="\n")
        if hashlib.sha256(matrix_path.read_bytes()).hexdigest() != result["source_matrix_sha256"]:
            raise EventSliceError("source matrix result changed during analysis")
        if output_path.exists():
            raise EventSliceError(f"refusing to overwrite existing output: {output_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary.rename(output_path)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return output_path


def _summary_markdown(result: Mapping[str, Any]) -> str:
    lines = ["# Event slice analyzer結果", "", result["research_only_notice"], "", "## 概要", "", f"- matrix: `{result['matrix_id']}`", f"- status: `{result['status']}`", f"- analyzed cells: {result['counts']['analyzed_cells']} / {result['counts']['total_cells']}", f"- analyzed prediction points: {result['counts']['analyzed_prediction_count']}", "", "## 露出別macro summary", "", "| dimension | exposure | operating mode | model | target | unit | horizon | context | cells | points | MAE mean | RMSE mean |", "| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for row in result["macro_summary"]:
        metrics = row["metrics"]
        lines.append(f"| {row['dimension']} | {row['exposure']} | {row['operating_mode'] or '-'} | {row['model']} | {row['target_signal_key']} | {row['unit']} | {row['horizon']} | {row['context_length']} | {row['cell_count']} | {row['total_point_count']} | {metrics.get('mae', {}).get('mean', '-') if isinstance(metrics.get('mae'), dict) else '-'} | {metrics.get('rmse', {}).get('mean', '-') if isinstance(metrics.get('rmse'), dict) else '-'} |")
    lines.extend(["", "## 未coverイベント", "", "予測timestampで `covered_by_forecast_timestamp=false` のイベントは評価済みではありません。"])
    uncovered = [(cell["cell_id"], event["event_id"], event["roles"], event["overlaps_test_split"]) for cell in result["cells"] for event in cell["event_coverage"] if event["overlaps_test_split"] and not event["covered_by_forecast_timestamp"]]
    if uncovered:
        lines.extend(["", "| cell | event ID | role | test overlap |", "| --- | --- | --- | --- |"])
        lines.extend(f"| `{cell_id}` | `{event_id}` | {', '.join(roles) or '-'} | {overlap} |" for cell_id, event_id, roles, overlap in uncovered)
    else:
        lines.append("\nなし")
    lines.extend(["", "`forecast_point_count`は予測row数であり、model／targetごとに同じイベントが重複カウントされ得ます。", "", "## Limitations", ""])
    lines.extend(f"- {item}" for item in result["limitations"])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="analyze_event_slices.py", description="既存benchmark matrix予測をイベント区間別にpost-hoc集計する")
    parser.add_argument("--matrix-result", required=True, help="repo-relative matrix result.json")
    parser.add_argument("--output", required=True, help="repo-relative new output directory below artifacts")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[2]), help="repository root")
    args = parser.parse_args(argv)
    try:
        output = analyze_event_slices(args.matrix_result, args.output, args.root)
    except (EventSliceError, ManifestValidationError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print(f"event slices: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
