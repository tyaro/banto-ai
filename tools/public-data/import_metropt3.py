"""MetroPT-3 fixed sourceからcanonical public datasetを作るstreaming importer。"""

from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import shutil
import sys
import tempfile
import zipfile
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from banto_ai.manifest import ManifestValidationError, load_json, validate  # noqa: E402
from banto_ai.public_quality import check_public_dataset  # noqa: E402
from banto_ai.public_source import load_source_manifest, prepare_source, verify_archive  # noqa: E402


DEFAULT_CONFIG_PATH = ROOT / "examples" / "configs" / "metropt3-public-2020-02-21.json"
SOURCE_MANIFEST_PATH = ROOT / "datasets" / "manifests" / "metropt3-source.json"
CONFIG_SCHEMA_PATH = ROOT / "schemas" / "public-transform-config.schema.json"
SOURCE_CSV_MEMBER = "MetroPT3(AirCompressor).csv"
EXPECTED_HEADER = ("", "timestamp", "TP2", "TP3", "H1", "DV_pressure", "Reservoirs", "Oil_temperature", "Motor_current", "COMP", "DV_eletric", "Towers", "MPG", "LPS", "Pressure_switch", "Oil_level", "Caudal_impulses")
TIMEZONE_ASSUMPTION = "source-naive timestamps are interpreted as UTC for ordering and output formatting only; actual timezone is unspecified and not claimed"
FINGERPRINT_FILES = ("source-manifest.json", "transform-config.json", "observations.jsonl", "split-manifest.json", "dataset-manifest.json", "quality-report.json")
ANALOG_AGGREGATION = "mean"
DIGITAL_AGGREGATION = "last"
FINGERPRINT_CANONICALIZATION = "UTF-8 JSON with deterministic object key order and compact separators; JSONL row order is timestamp order; aggregate input is sorted file name and digest"


class MetroPT3ImportError(ValueError):
    """MetroPT-3 canonical importの契約違反。"""


def _canonical_bytes(value: Any, *, sort_keys: bool = True) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=sort_keys, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def _write_json(path: Path, value: Any, *, sort_keys: bool = True) -> None:
    path.write_bytes(_canonical_bytes(value, sort_keys=sort_keys))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _repo_file(path: Path | str, label: str, root: Path = ROOT) -> Path:
    raw = str(path)
    candidate = Path(raw)
    if candidate.is_absolute() or PureWindowsPath(raw).drive:
        resolved = candidate.resolve()
        if root.resolve() not in resolved.parents:
            raise MetroPT3ImportError(f"{label} must remain inside repository")
    else:
        if "\\" in raw or any(part in ("", ".", "..") for part in PurePosixPath(raw).parts):
            raise MetroPT3ImportError(f"{label} must be a repository-relative POSIX path")
        resolved = (root / candidate).resolve()
    if resolved == root or root not in resolved.parents or not resolved.is_file() or resolved.is_symlink():
        raise MetroPT3ImportError(f"{label} must be a regular file inside repository")
    return resolved


def _output_path(relative: str, root: Path = ROOT) -> Path:
    if Path(relative).is_absolute() or PureWindowsPath(relative).drive or "\\" in relative or any(part in ("", ".", "..") for part in PurePosixPath(relative).parts):
        raise MetroPT3ImportError("output_dir must be a repository-relative POSIX path")
    lexical_boundary = root / "artifacts" / "public-datasets"
    for candidate in (root / "artifacts", lexical_boundary):
        if candidate.is_symlink():
            raise MetroPT3ImportError("public dataset output boundary must not contain symlinks")
    output = (root / relative).resolve()
    boundary = lexical_boundary.resolve()
    if output == boundary or boundary not in output.parents:
        raise MetroPT3ImportError("output_dir must be under artifacts/public-datasets")
    cursor = output.parent
    while cursor != boundary:
        if cursor.is_symlink():
            raise MetroPT3ImportError("public dataset output path must not contain symlinks")
        cursor = cursor.parent
    return output


def load_transform_config(path: Path = DEFAULT_CONFIG_PATH, root: Path = ROOT) -> Mapping[str, Any]:
    try:
        config = load_json(_repo_file(path, "config_path", root))
        validate(config, load_json(root / "schemas" / "public-transform-config.schema.json"))
    except ManifestValidationError as exc:
        raise MetroPT3ImportError(str(exc)) from exc
    if not isinstance(config, dict):
        raise MetroPT3ImportError("transform config must be an object")
    if tuple(config["expected_source_header"]) != EXPECTED_HEADER or config["source_archive_member"] != SOURCE_CSV_MEMBER or config["timezone_assumption"] != TIMEZONE_ASSUMPTION:
        raise MetroPT3ImportError("transform config does not match the fixed MetroPT-3 source contract")
    if config["excluded_source_columns"] != ["Caudal_impulses"] or config["known_future_covariate_ids"]:
        raise MetroPT3ImportError("Caudal_impulses must be excluded and known-future covariates must be empty")
    source_names = [item["source_name"] for item in config["signals"]]
    logical_ids = [item["logical_signal_id"] for item in config["signals"]]
    if len(source_names) != len(set(source_names)) or len(logical_ids) != len(set(logical_ids)) or len(config["signals"]) != 14:
        raise MetroPT3ImportError("public signal mapping must contain 14 unique signals")
    if {item["source_name"] for item in config["signals"]} | {"Caudal_impulses"} != set(EXPECTED_HEADER[2:]):
        raise MetroPT3ImportError("public signal mapping does not cover the exact source header")
    if [item["logical_signal_id"] for item in config["signals"] if item["role"] == "target"] != ["tp3", "oil_temperature", "motor_current"]:
        raise MetroPT3ImportError("public target signal mapping is invalid")
    if config["output"]["output_dir"] != "artifacts/public-datasets/metropt3-public-2020-02-21":
        raise MetroPT3ImportError("MetroPT-3 output directory is not the fixed public boundary")
    return config


def _source_time(value: str) -> datetime:
    if not isinstance(value, str) or not value or "T" in value or "+" in value or value.endswith("Z"):
        raise MetroPT3ImportError("source timestamp must be naive and timezone unspecified")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError as exc:
        raise MetroPT3ImportError(f"invalid source timestamp: {value!r}") from exc
    if parsed.tzinfo is not None:
        raise MetroPT3ImportError("source timestamp must be naive")
    return parsed


def _output_time(value: datetime) -> str:
    return value.replace(tzinfo=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _finite_cell(raw: str, signal: str) -> float:
    if raw is None or raw.strip() == "":
        raise MetroPT3ImportError(f"missing source cell: {signal}")
    try:
        value = float(raw)
    except ValueError as exc:
        raise MetroPT3ImportError(f"non-numeric source cell: {signal}") from exc
    if not math.isfinite(value):
        raise MetroPT3ImportError(f"non-finite source cell: {signal}")
    return value


def _stream_transform(archive_path: Path, config: Mapping[str, Any]) -> tuple[list[dict[str, Any]], int, int, dict[str, Any]]:
    raw_start = _source_time(config["raw_window"]["start"])
    raw_end = _source_time(config["raw_window"]["end"])
    bin_delta = timedelta(milliseconds=config["binning"]["interval_ms"])
    bin_count = config["output"]["sample_count"]
    definitions = list(config["signals"])
    indexes: dict[str, int] = {}
    bins: list[dict[str, Any]] = [{"count": 0, "values": {item["logical_signal_id"]: [] for item in definitions}} for _ in range(bin_count)]
    previous: datetime | None = None
    previous_in_window: datetime | None = None
    first_timestamp_raw: str | None = None
    last_timestamp_raw: str | None = None
    delta_histogram: dict[str, int] = {}
    min_delta_ms: int | None = None
    max_delta_ms: int | None = None
    source_rows_in_window = 0
    large_gaps = 0
    try:
        with zipfile.ZipFile(archive_path) as bundle:
            with bundle.open(config["source_archive_member"], "r") as raw_handle:
                import io
                text = io.TextIOWrapper(raw_handle, encoding="utf-8-sig", newline="")
                reader = csv.reader(text)
                try:
                    header = tuple(next(reader))
                except StopIteration as exc:
                    raise MetroPT3ImportError("source CSV is empty") from exc
                if header != EXPECTED_HEADER:
                    raise MetroPT3ImportError("source CSV header does not exactly match the fixed contract")
                indexes = {item["source_name"]: header.index(item["source_name"]) for item in definitions}
                for row in reader:
                    if len(row) != len(EXPECTED_HEADER):
                        raise MetroPT3ImportError("source CSV row width does not match header")
                    timestamp = _source_time(row[1])
                    if previous is not None and timestamp <= previous:
                        raise MetroPT3ImportError("source timestamps contain duplicate or reverse order")
                    previous = timestamp
                    if not raw_start <= timestamp < raw_end:
                        continue
                    if previous_in_window is not None and timestamp - previous_in_window > timedelta(milliseconds=config["binning"]["max_gap_ms"]):
                        large_gaps += 1
                        raise MetroPT3ImportError("large source gap inside raw window")
                    if previous_in_window is not None:
                        delta = timestamp - previous_in_window
                        delta_ms = delta.days * 86_400_000 + delta.seconds * 1_000 + delta.microseconds // 1_000
                        if delta_ms <= 0:
                            raise MetroPT3ImportError("source cadence delta must be positive")
                        key = str(delta_ms)
                        delta_histogram[key] = delta_histogram.get(key, 0) + 1
                        min_delta_ms = delta_ms if min_delta_ms is None else min(min_delta_ms, delta_ms)
                        max_delta_ms = delta_ms if max_delta_ms is None else max(max_delta_ms, delta_ms)
                    if first_timestamp_raw is None:
                        first_timestamp_raw = row[1]
                    last_timestamp_raw = row[1]
                    previous_in_window = timestamp
                    offset = timestamp - raw_start
                    bin_index = int(offset.total_seconds() // bin_delta.total_seconds())
                    if not 0 <= bin_index < bin_count:
                        raise MetroPT3ImportError("source timestamp was interpreted outside raw window")
                    bucket = bins[bin_index]
                    bucket["count"] += 1
                    source_rows_in_window += 1
                    for item in definitions:
                        value = _finite_cell(row[indexes[item["source_name"]]], item["source_name"])
                        if item["aggregation"] == "last":
                            bucket["values"][item["logical_signal_id"]] = [value]
                        else:
                            bucket["values"][item["logical_signal_id"]].append(value)
    except (KeyError, OSError, UnicodeError, zipfile.BadZipFile) as exc:
        if isinstance(exc, MetroPT3ImportError):
            raise
        raise MetroPT3ImportError(f"source CSV streaming failed: {exc}") from exc
    if source_rows_in_window <= 1 or first_timestamp_raw is None or last_timestamp_raw is None or min_delta_ms is None or max_delta_ms is None:
        raise MetroPT3ImportError("raw window must contain at least two source rows for cadence evidence")
    rows: list[dict[str, Any]] = []
    for index, bucket in enumerate(bins):
        if bucket["count"] == 0:
            raise MetroPT3ImportError(f"raw window contains empty output bin: {index}")
        values: dict[str, dict[str, Any]] = {}
        quality: dict[str, str] = {}
        for item in definitions:
            samples = bucket["values"][item["logical_signal_id"]]
            if not samples:
                raise MetroPT3ImportError(f"raw window contains missing cell: {item['source_name']}")
            value = sum(samples) / len(samples) if item["aggregation"] == "mean" else samples[-1]
            if not math.isfinite(value):
                raise MetroPT3ImportError(f"output value is non-finite: {item['logical_signal_id']}")
            if item["aggregation"] == "last" and value not in (0.0, 1.0):
                raise MetroPT3ImportError(f"digital source value is not binary 0/1: {item['source_name']}")
            values[item["logical_signal_id"]] = {"unit": item["unit"], "value": value}
            quality[item["logical_signal_id"]] = "ok"
        rows.append({"timestamp": _output_time(raw_start + (index + 1) * bin_delta), "equipment_id": config["equipment"]["equipment_id"], "equipment_type": config["equipment"]["equipment_type"], "operating_mode": config["equipment"]["operating_mode"], "recipe_step": config["equipment"]["recipe_step"], "signals": values, "quality": quality})
    bins_counts = [bucket["count"] for bucket in bins]
    if not bins_counts or min(bins_counts) <= 0 or min(bins_counts) > max(bins_counts) or source_rows_in_window < min(bins_counts) * bin_count or source_rows_in_window > max(bins_counts) * bin_count:
        raise MetroPT3ImportError("raw bin observation counts are invalid")
    cadence = {
        "first_timestamp_raw": first_timestamp_raw,
        "last_timestamp_raw": last_timestamp_raw,
        "min_delta_ms": min_delta_ms,
        "max_delta_ms": max_delta_ms,
        "delta_ms_histogram": {key: delta_histogram[key] for key in sorted(delta_histogram, key=int)},
        "min_observations_per_bin": min(bins_counts),
        "max_observations_per_bin": max(bins_counts),
    }
    return rows, source_rows_in_window, large_gaps, cadence


def _split_manifest(config: Mapping[str, Any]) -> dict[str, Any]:
    return {"schema_version": "0.1", "manifest_type": "public-split", "dataset_id": config["dataset_id"], "boundary_semantics": "[start,end)", "sampling_interval_ms": 60000, "sample_count": 1440, "strategies": [{"strategy": "chronological", "splits": [{"split_id": "train", "start_timestamp": "2020-02-21T00:01:00Z", "end_timestamp": "2020-02-21T14:25:00Z", "record_count": 864, "equipment_ids": ["metropt3-apu-01"]}, {"split_id": "validation", "start_timestamp": "2020-02-21T14:25:00Z", "end_timestamp": "2020-02-21T19:13:00Z", "record_count": 288, "equipment_ids": ["metropt3-apu-01"]}, {"split_id": "test", "start_timestamp": "2020-02-21T19:13:00Z", "end_timestamp": "2020-02-22T00:01:00Z", "record_count": 288, "equipment_ids": ["metropt3-apu-01"]}]}]}


def _dataset_manifest(config: Mapping[str, Any], source: Mapping[str, Any]) -> dict[str, Any]:
    equipment_id = config["equipment"]["equipment_id"]
    signals = [{"signal_id": f"{equipment_id}.{item['logical_signal_id']}", "logical_signal_id": item["logical_signal_id"], "name": item["name"], "unit": item["unit"], "role": item["role"], "aggregation": item["aggregation"], "sampling_interval_ms": 60000} for item in config["signals"]]
    return {"schema_version": "0.1", "manifest_type": "dataset", "dataset_id": config["dataset_id"], "provenance": "public", "data_path": "observations.jsonl", "split_manifest_path": "split-manifest.json", "fingerprint_path": "fingerprint.json", "source_manifest_path": "source-manifest.json", "transform_config_path": "transform-config.json", "quality_report_path": "quality-report.json", "generator_version": "public-import/0.1.0", "importer_version": "0.1.0", "sample_count": 1440, "sampling_interval_ms": 60000, "raw_window_start": "2020-02-21T00:00:00Z", "raw_window_end": "2020-02-22T00:00:00Z", "timezone_status": "unspecified", "timezone_assumption": TIMEZONE_ASSUMPTION, "source": {"repository": source["source"]["repository"], "dataset_id": source["source"]["dataset_id"], "doi": source["source"]["doi"], "revision": source["source"]["revision"], "archive_sha256": source["archive"]["sha256"], "archive_size_bytes": source["archive"]["size_bytes"]}, "license": {"spdx_id": source["license"]["spdx_id"], "url": source["license"]["url"], "attribution": source["license"]["attribution"], "redistribution_allowed": source["license"]["redistribution_allowed"], "commercial_use_allowed": source["license"]["commercial_use_allowed"]}, "equipment": [{"equipment_id": equipment_id, "equipment_type": config["equipment"]["equipment_type"]}], "signals": signals, "known_future_covariate_ids": []}


def _write_fingerprint(output: Path) -> None:
    files = {name: _sha256(output / name) for name in FINGERPRINT_FILES}
    canonical = "".join(f"{name}\n{digest}\n" for name, digest in sorted(files.items())).encode("utf-8")
    _write_json(output / "fingerprint.json", {"algorithm": "sha256", "canonicalization": FINGERPRINT_CANONICALIZATION, "files": files, "dataset_fingerprint": hashlib.sha256(canonical).hexdigest()})


def _write_observations(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("wb") as handle:
        for row in rows:
            handle.write(_canonical_bytes(row))


def import_metropt3(cache_dir: Path, config_path: Path = DEFAULT_CONFIG_PATH, *, accepted: bool, root: Path = ROOT) -> Path:
    if not accepted:
        raise MetroPT3ImportError("--accept-cc-by-4.0 is required; no cache or output side effect was attempted")
    config = load_transform_config(config_path, root)
    output = _output_path(config["output"]["output_dir"], root)
    if output.exists() or output.is_symlink():
        raise MetroPT3ImportError(f"refusing to overwrite existing dataset output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    lock_path = output.parent / f".{output.name}.publish.lock"
    lock_acquired = False
    temporary: Path | None = None
    try:
        try:
            lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise MetroPT3ImportError("another MetroPT-3 publish is already in progress") from exc
        else:
            os.close(lock_fd)
            lock_acquired = True
        if output.exists() or output.is_symlink():
            raise MetroPT3ImportError(f"refusing to overwrite existing dataset output: {output}")
        source_manifest = load_source_manifest(root / config["source_manifest_path"])
        evidence = prepare_source(cache_dir, root / config["source_manifest_path"], accepted=True)
        archive_path = Path(evidence["archive"]["path"])
        verify_archive(archive_path, source_manifest)
        temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
        rows, source_rows, large_gaps, source_cadence = _stream_transform(archive_path, config)
        _write_json(temporary / "source-manifest.json", source_manifest)
        _write_json(temporary / "transform-config.json", config)
        _write_observations(temporary / "observations.jsonl", rows)
        _write_json(temporary / "split-manifest.json", _split_manifest(config))
        _write_json(temporary / "dataset-manifest.json", _dataset_manifest(config, source_manifest))
        # quality-reportだけはhistogramのnumeric key insertion orderを保持する。他のJSONはsorted keysで出力する。
        _write_json(temporary / "quality-report.json", {"schema_version": "0.1", "report_type": "public-dataset-quality", "status": "pass", "dataset_id": config["dataset_id"], "source_rows_in_window": source_rows, "source_cadence": source_cadence, "output_rows": len(rows), "empty_bins": 0, "missing_cells": 0, "nonfinite_cells": 0, "large_gaps": large_gaps, "checks": ["fixed_source_archive_verified", "exact_header", "strict_source_order", "source_cadence_evidence", "regular_60s_bin_end", "mean_and_last_aggregation", "binary_digital_values", "no_interpolation", "no_known_future_covariates", "chronological_split"], "timezone_assumption": TIMEZONE_ASSUMPTION}, sort_keys=False)
        _write_fingerprint(temporary)
        check_public_dataset(temporary, root)
        if output.exists() or output.is_symlink():
            raise MetroPT3ImportError("dataset output appeared during publish; refusing overwrite")
        os.rename(temporary, output)
        temporary = None
        return output
    except Exception:
        if temporary is not None and temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)
        raise
    finally:
        if lock_acquired:
            lock_path.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(prog="import_metropt3.py")
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--accept-cc-by-4.0", action="store_true", dest="accepted")
    args = parser.parse_args(argv)
    try:
        result = import_metropt3(Path(args.cache_dir), Path(args.config), accepted=args.accepted)
    except (OSError, MetroPT3ImportError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"status": "passed", "dataset_path": str(result)}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
