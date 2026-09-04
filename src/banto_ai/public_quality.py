"""provenance=public dataset専用の標準ライブラリ品質ゲート。"""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from .manifest import ManifestValidationError, load_json, validate
from .public_source import METROPT3_ARCHIVE_SHA256, load_source_manifest


ROOT = Path(__file__).resolve().parents[2]
FINGERPRINT_FILES = (
    "source-manifest.json", "transform-config.json", "observations.jsonl",
    "split-manifest.json", "dataset-manifest.json", "quality-report.json",
)
EXPECTED_SOURCE_HEADER = ("", "timestamp", "TP2", "TP3", "H1", "DV_pressure", "Reservoirs", "Oil_temperature", "Motor_current", "COMP", "DV_eletric", "Towers", "MPG", "LPS", "Pressure_switch", "Oil_level", "Caudal_impulses")
EXPECTED_TIMEZONE_ASSUMPTION = "source-naive timestamps are interpreted as UTC for ordering and output formatting only; actual timezone is unspecified and not claimed"
EXPECTED_SIGNALS = (
    ("TP2", "tp2", "TP2", "bar", "covariate", "mean"),
    ("TP3", "tp3", "TP3", "bar", "target", "mean"),
    ("H1", "h1", "H1", "bar", "covariate", "mean"),
    ("DV_pressure", "dv_pressure", "DV_pressure", "bar", "covariate", "mean"),
    ("Reservoirs", "reservoirs", "Reservoirs", "bar", "covariate", "mean"),
    ("Oil_temperature", "oil_temperature", "Oil_temperature", "ºC", "target", "mean"),
    ("Motor_current", "motor_current", "Motor_current", "A", "target", "mean"),
    ("COMP", "comp", "COMP", "binary", "covariate", "last"),
    ("DV_eletric", "dv_electric", "DV_eletric", "binary", "covariate", "last"),
    ("Towers", "towers", "Towers", "binary", "covariate", "last"),
    ("MPG", "mpg", "MPG", "binary", "covariate", "last"),
    ("LPS", "lps", "LPS", "binary", "covariate", "last"),
    ("Pressure_switch", "pressure_switch", "Pressure_switch", "binary", "covariate", "last"),
    ("Oil_level", "oil_level", "Oil_level", "binary", "covariate", "last"),
)
EXPECTED_HEADER_KEYS = frozenset({"timestamp", "equipment_id", "equipment_type", "operating_mode", "recipe_step", "signals", "quality"})
QUALITY_REPORT_KEYS = frozenset({"schema_version", "report_type", "status", "dataset_id", "source_rows_in_window", "source_cadence", "output_rows", "empty_bins", "missing_cells", "nonfinite_cells", "large_gaps", "checks", "timezone_assumption"})
SOURCE_CADENCE_KEYS = frozenset({"first_timestamp_raw", "last_timestamp_raw", "min_delta_ms", "max_delta_ms", "delta_ms_histogram", "min_observations_per_bin", "max_observations_per_bin"})
FINGERPRINT_CANONICALIZATION = "UTF-8 JSON with deterministic object key order and compact separators; JSONL row order is timestamp order; aggregate input is sorted file name and digest"


class PublicDatasetQualityError(ValueError):
    """public datasetがcanonical quality gateを満たさない。"""


def _child_path(dataset_dir: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or PureWindowsPath(relative).drive or "\\" in relative:
        raise PublicDatasetQualityError(f"dataset artifact path must be repository-relative POSIX: {relative!r}")
    parts = PurePosixPath(relative).parts
    if any(part in ("", ".", "..") for part in parts):
        raise PublicDatasetQualityError(f"dataset artifact path is unsafe: {relative!r}")
    candidate = dataset_dir / relative
    resolved = candidate.resolve()
    if resolved != dataset_dir.resolve() and dataset_dir.resolve() not in resolved.parents:
        raise PublicDatasetQualityError(f"dataset artifact path escapes dataset directory: {relative}")
    if candidate.is_symlink() or not candidate.is_file():
        raise PublicDatasetQualityError(f"dataset artifact must be a regular file: {relative}")
    return resolved


def _parse_utc(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise PublicDatasetQualityError("public timestamps must be explicit UTC with Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise PublicDatasetQualityError(f"invalid UTC timestamp: {value!r}") from exc
    if parsed.utcoffset() != timedelta(0):
        raise PublicDatasetQualityError("public timestamp must be UTC")
    return parsed.astimezone(timezone.utc)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_json(path: Path, schema_path: Path, label: str) -> dict[str, Any]:
    try:
        value = load_json(path)
        validate(value, load_json(schema_path))
    except ManifestValidationError as exc:
        raise PublicDatasetQualityError(f"{label} schema validation failed: {exc}") from exc
    if not isinstance(value, dict):
        raise PublicDatasetQualityError(f"{label} must be an object")
    return value


def _check_fingerprint(dataset_dir: Path, manifest: dict[str, Any], root: Path) -> dict[str, Any]:
    fingerprint_path = _child_path(dataset_dir, manifest["fingerprint_path"])
    fingerprint = load_json(fingerprint_path)
    if not isinstance(fingerprint, dict) or set(fingerprint) != {"algorithm", "canonicalization", "files", "dataset_fingerprint"}:
        raise PublicDatasetQualityError("fingerprint keys are invalid")
    if fingerprint["algorithm"] != "sha256" or fingerprint["canonicalization"] != FINGERPRINT_CANONICALIZATION:
        raise PublicDatasetQualityError("fingerprint algorithm or canonicalization is invalid")
    declared = fingerprint["files"]
    if not isinstance(declared, dict) or set(declared) != set(FINGERPRINT_FILES):
        raise PublicDatasetQualityError("fingerprint file set is invalid")
    actual: dict[str, str] = {}
    for name in FINGERPRINT_FILES:
        path = _child_path(dataset_dir, name)
        actual[name] = _hash_file(path)
        if declared[name] != actual[name] or not isinstance(declared[name], str) or len(declared[name]) != 64 or declared[name].lower() != declared[name]:
            raise PublicDatasetQualityError(f"fingerprint mismatch: {name}")
    canonical_input = "".join(f"{name}\n{actual[name]}\n" for name in sorted(actual)).encode("utf-8")
    expected = hashlib.sha256(canonical_input).hexdigest()
    if fingerprint["dataset_fingerprint"] != expected:
        raise PublicDatasetQualityError("dataset_fingerprint mismatch")
    return fingerprint


def _check_observations(dataset_dir: Path, manifest: dict[str, Any], config: dict[str, Any], split: dict[str, Any]) -> tuple[int, list[datetime]]:
    data_path = _child_path(dataset_dir, manifest["data_path"])
    equipment = manifest["equipment"][0]
    catalog = {item["logical_signal_id"]: item for item in manifest["signals"]}
    if len(catalog) != len(manifest["signals"]):
        raise PublicDatasetQualityError("public signal logical IDs must be unique")
    expected_ids = set(catalog)
    start = _parse_utc(manifest["raw_window_start"])
    expected_delta = timedelta(milliseconds=manifest["sampling_interval_ms"])
    count = 0
    timestamps: list[datetime] = []
    with data_path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise PublicDatasetQualityError(f"invalid observations JSONL at line {line_number}") from exc
            if not isinstance(row, dict) or set(row) != EXPECTED_HEADER_KEYS:
                raise PublicDatasetQualityError(f"observation keys are invalid at line {line_number}")
            if row["equipment_id"] != equipment["equipment_id"] or row["equipment_type"] != equipment["equipment_type"] or row["operating_mode"] != "unknown" or row["recipe_step"] != "not-applicable":
                raise PublicDatasetQualityError(f"observation metadata is invalid at line {line_number}")
            timestamp = _parse_utc(row["timestamp"])
            expected_timestamp = start + count * expected_delta + expected_delta
            if timestamp != expected_timestamp:
                raise PublicDatasetQualityError(f"observation timestamp/bin-end mismatch at line {line_number}")
            signals = row["signals"]
            quality = row["quality"]
            if not isinstance(signals, dict) or not isinstance(quality, dict) or set(signals) != expected_ids or set(quality) != expected_ids:
                raise PublicDatasetQualityError(f"observation signal keys are invalid at line {line_number}")
            for logical_id, definition in catalog.items():
                payload = signals[logical_id]
                if not isinstance(payload, dict) or set(payload) != {"unit", "value"} or payload["unit"] != definition["unit"]:
                    raise PublicDatasetQualityError(f"unit/payload mismatch at line {line_number}: {logical_id}")
                value = payload["value"]
                if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
                    raise PublicDatasetQualityError(f"non-finite observation at line {line_number}: {logical_id}")
                if quality[logical_id] != "ok":
                    raise PublicDatasetQualityError(f"public output quality must be ok at line {line_number}: {logical_id}")
                if definition["aggregation"] == "last" and value not in (0, 1):
                    raise PublicDatasetQualityError(f"binary signal is not 0/1 at line {line_number}: {logical_id}")
            timestamps.append(timestamp)
            count += 1
    if count != manifest["sample_count"] or count != config["output"]["sample_count"]:
        raise PublicDatasetQualityError(f"observation count mismatch: {count}")
    if count != 1440:
        raise PublicDatasetQualityError("MetroPT-3 public output must contain exactly 1440 rows")
    return count, timestamps


def _parse_raw_timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", value):
        raise PublicDatasetQualityError("source cadence raw timestamps must be naive CSV timestamps")
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError as exc:
        raise PublicDatasetQualityError("source cadence raw timestamp is invalid") from exc


def _check_source_cadence(quality: dict[str, Any], manifest: dict[str, Any], config: dict[str, Any]) -> None:
    cadence = quality["source_cadence"]
    if not isinstance(cadence, dict) or set(cadence) != SOURCE_CADENCE_KEYS:
        raise PublicDatasetQualityError("source cadence keys are invalid")
    source_rows = quality["source_rows_in_window"]
    if not isinstance(source_rows, int) or isinstance(source_rows, bool) or source_rows <= 1:
        raise PublicDatasetQualityError("source rows must be greater than one for cadence evidence")
    first = _parse_raw_timestamp(cadence["first_timestamp_raw"])
    last = _parse_raw_timestamp(cadence["last_timestamp_raw"])
    raw_start = _parse_utc(manifest["raw_window_start"]).replace(tzinfo=None)
    raw_end = _parse_utc(manifest["raw_window_end"]).replace(tzinfo=None)
    if not raw_start <= first <= last < raw_end:
        raise PublicDatasetQualityError("source cadence timestamps are outside the raw window")
    for key in ("min_delta_ms", "max_delta_ms", "min_observations_per_bin", "max_observations_per_bin"):
        value = cadence[key]
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise PublicDatasetQualityError(f"source cadence {key} must be a positive integer")
    if cadence["min_delta_ms"] > cadence["max_delta_ms"] or cadence["max_delta_ms"] > config["binning"]["max_gap_ms"]:
        raise PublicDatasetQualityError("source cadence delta bounds are invalid")
    if cadence["min_observations_per_bin"] > cadence["max_observations_per_bin"]:
        raise PublicDatasetQualityError("source cadence bin count bounds are invalid")
    histogram = cadence["delta_ms_histogram"]
    if not isinstance(histogram, dict) or not histogram:
        raise PublicDatasetQualityError("source cadence histogram must be a non-empty object")
    keys = list(histogram)
    if any(not isinstance(key, str) or not key.isascii() or not key.isdecimal() or int(key) <= 0 for key in keys):
        raise PublicDatasetQualityError("source cadence histogram keys must be positive decimal milliseconds")
    if keys != sorted(keys, key=int):
        raise PublicDatasetQualityError("source cadence histogram keys must be in numeric order")
    counts = list(histogram.values())
    if any(not isinstance(value, int) or isinstance(value, bool) or value <= 0 for value in counts):
        raise PublicDatasetQualityError("source cadence histogram counts must be positive integers")
    if sum(counts) != source_rows - 1:
        raise PublicDatasetQualityError("source cadence histogram count does not match source rows")
    if int(keys[0]) != cadence["min_delta_ms"] or int(keys[-1]) != cadence["max_delta_ms"]:
        raise PublicDatasetQualityError("source cadence histogram bounds do not match min/max")
    elapsed = last - first
    elapsed_ms = elapsed.days * 86_400_000 + elapsed.seconds * 1_000 + elapsed.microseconds // 1_000
    histogram_elapsed_ms = sum(int(key) * value for key, value in histogram.items())
    if histogram_elapsed_ms != elapsed_ms:
        raise PublicDatasetQualityError("source cadence histogram does not reconstruct raw timestamp span")
    if source_rows < cadence["min_observations_per_bin"] * 1440 or source_rows > cadence["max_observations_per_bin"] * 1440:
        raise PublicDatasetQualityError("source cadence bin count range does not cover source rows")


def _check_split(split: dict[str, Any], manifest: dict[str, Any], timestamps: list[datetime]) -> None:
    expected = [
        ("train", "2020-02-21T00:01:00Z", "2020-02-21T14:25:00Z", 864),
        ("validation", "2020-02-21T14:25:00Z", "2020-02-21T19:13:00Z", 288),
        ("test", "2020-02-21T19:13:00Z", "2020-02-22T00:01:00Z", 288),
    ]
    strategies = split["strategies"]
    if len(strategies) != 1 or strategies[0]["strategy"] != "chronological":
        raise PublicDatasetQualityError("public split must contain exactly one chronological strategy")
    actual_splits = strategies[0]["splits"]
    actual = [(item["split_id"], item["start_timestamp"], item["end_timestamp"], item["record_count"]) for item in actual_splits]
    if actual != expected or any(item["equipment_ids"] != ["metropt3-apu-01"] for item in actual_splits):
        raise PublicDatasetQualityError("public chronological split does not match the fixed 864/288/288 contract")
    if split["dataset_id"] != manifest["dataset_id"] or split["sample_count"] != 1440:
        raise PublicDatasetQualityError("public split identity is invalid")
    if len(timestamps) != 1440 or timestamps[0].isoformat().replace("+00:00", "Z") != expected[0][1] or timestamps[-1].isoformat().replace("+00:00", "Z") != "2020-02-22T00:00:00Z":
        raise PublicDatasetQualityError("public observations do not cover the exact output period")
    for name, start_text, end_text, declared in expected:
        start = _parse_utc(start_text)
        end = _parse_utc(end_text)
        actual_rows = [timestamp for timestamp in timestamps if start <= timestamp < end]
        if len(actual_rows) != declared:
            raise PublicDatasetQualityError(f"public split record_count mismatch: {name}")
        if actual_rows and (actual_rows[0] != start or actual_rows[-1] + timedelta(milliseconds=60000) != end):
            raise PublicDatasetQualityError(f"public split boundary coverage mismatch: {name}")
    if any(left >= right for left, right in zip(timestamps, timestamps[1:])) or any(right - left != timedelta(milliseconds=60000) for left, right in zip(timestamps, timestamps[1:])):
        raise PublicDatasetQualityError("public split observations have a gap or overlap")


def check_public_dataset(dataset_dir: Path, root: Path = ROOT) -> dict[str, Any]:
    """public dataset成果物を再読込し、hashと全canonical契約を検査する。"""
    dataset_dir = Path(dataset_dir).expanduser().resolve()
    if not dataset_dir.is_dir():
        raise PublicDatasetQualityError("public dataset directory does not exist")
    manifest_path = dataset_dir / "dataset-manifest.json"
    manifest = _validate_json(manifest_path, root / "schemas" / "public-dataset-manifest.schema.json", "dataset manifest")
    config = _validate_json(_child_path(dataset_dir, manifest["transform_config_path"]), root / "schemas" / "public-transform-config.schema.json", "transform config")
    split = _validate_json(_child_path(dataset_dir, manifest["split_manifest_path"]), root / "schemas" / "public-split-manifest.schema.json", "split manifest")
    source = _validate_json(_child_path(dataset_dir, manifest["source_manifest_path"]), root / "schemas" / "public-dataset-source.schema.json", "source manifest")
    quality = load_json(_child_path(dataset_dir, manifest["quality_report_path"]))
    if not isinstance(quality, dict) or set(quality) != QUALITY_REPORT_KEYS or quality["status"] != "pass" or "dataset_fingerprint" in quality:
        raise PublicDatasetQualityError("quality report must contain facts only and must not contain dataset_fingerprint")
    if quality["dataset_id"] != manifest["dataset_id"] or quality["timezone_assumption"] != manifest["timezone_assumption"]:
        raise PublicDatasetQualityError("quality report identity or timezone assumption mismatch")
    if source != load_source_manifest(root / "datasets" / "manifests" / "metropt3-source.json"):
        raise PublicDatasetQualityError("copied source manifest does not match the fixed source pin")
    if manifest["source"]["archive_sha256"] != METROPT3_ARCHIVE_SHA256 or manifest["source"]["archive_sha256"] != source["archive"]["sha256"]:
        raise PublicDatasetQualityError("public dataset source archive identity mismatch")
    if manifest["known_future_covariate_ids"] or config["known_future_covariate_ids"]:
        raise PublicDatasetQualityError("MetroPT-3 public dataset must not contain known-future covariates")
    if config["dataset_id"] != manifest["dataset_id"] or config["timezone_assumption"] != manifest["timezone_assumption"]:
        raise PublicDatasetQualityError("public transform identity mismatch")
    tracked_config = _validate_json(root / "examples" / "configs" / "metropt3-public-2020-02-21.json", root / "schemas" / "public-transform-config.schema.json", "tracked transform config")
    if config != tracked_config or tuple(config["expected_source_header"]) != EXPECTED_SOURCE_HEADER or config["excluded_source_columns"] != ["Caudal_impulses"] or config["source_archive_member"] != "MetroPT3(AirCompressor).csv" or config["timezone_assumption"] != EXPECTED_TIMEZONE_ASSUMPTION:
        raise PublicDatasetQualityError("public transform config does not match the fixed tracked contract")
    expected_signals = [
        {"signal_id": f"{config['equipment']['equipment_id']}.{item['logical_signal_id']}", "logical_signal_id": item["logical_signal_id"], "name": item["name"], "unit": item["unit"], "role": item["role"], "aggregation": item["aggregation"], "sampling_interval_ms": 60000}
        for item in config["signals"]
    ]
    if manifest["signals"] != expected_signals:
        raise PublicDatasetQualityError("dataset signal catalog does not match transform config")
    if [item["logical_signal_id"] for item in config["signals"] if item["role"] == "target"] != ["tp3", "oil_temperature", "motor_current"]:
        raise PublicDatasetQualityError("public target signal catalog is invalid")
    _check_source_cadence(quality, manifest, config)
    count, timestamps = _check_observations(dataset_dir, manifest, config, split)
    _check_split(split, manifest, timestamps)
    fingerprint = _check_fingerprint(dataset_dir, manifest, root)
    if quality["output_rows"] != count or quality["source_rows_in_window"] < count or quality["empty_bins"] != 0 or quality["missing_cells"] != 0 or quality["nonfinite_cells"] != 0 or quality["large_gaps"] != 0:
        raise PublicDatasetQualityError("quality report facts do not match the verified output")
    return {"status": "pass", "dataset_id": manifest["dataset_id"], "observation_record_count": count, "equipment_count": 1, "dataset_fingerprint": fingerprint["dataset_fingerprint"], "checks": list(quality["checks"])}


check_dataset = check_public_dataset
