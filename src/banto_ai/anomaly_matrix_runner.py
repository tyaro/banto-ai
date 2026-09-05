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
from typing import Any, Callable, Mapping
from uuid import uuid4

from . import anomaly_matrix
from .anomaly_evaluation import evaluate_anomalies
from .benchmark import _revision
from .generator import FINGERPRINT_ALGORITHM, FINGERPRINT_FILE_NAMES, FINGERPRINT_CANONICALIZATION, generate_synthetic
from .manifest import ManifestValidationError, validate


SCHEMA_VERSION = "0.1"
RESULT_TYPE = "event-aware-anomaly-matrix"
COMPLETION_MARKER = ".complete"
COMPLETION_MARKER_TYPE = "event-aware-anomaly-matrix-complete"
RESULT_SCHEMA_PATH = "schemas/anomaly-multiseed-matrix-result.schema.json"
ANOMALY_CONFIG_SCHEMA_PATH = "schemas/anomaly-evaluation-config.schema.json"
ANOMALY_RESULT_SCHEMA_PATH = "schemas/anomaly-evaluation-result.schema.json"


class AnomalyMatrixRunnerError(ValueError):
    """A matrix run could not be safely completed or published."""


class _GlobalFailure(AnomalyMatrixRunnerError):
    """A provenance, input, path, or schema failure that invalidates the run."""


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
    return path.is_symlink() or bool(junction_check(path) if junction_check is not None else False)


def _strict_json_object(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        if _is_link(path) or not path.is_file():
            raise OSError(f"not a regular file: {path}")
        raw = path.read_bytes()

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
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise _GlobalFailure(f"{label} is not strict UTF-8 JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise _GlobalFailure(f"{label} must be a JSON object")
    return value, raw


def _jsonl_objects(path: Path, label: str) -> tuple[list[dict[str, Any]], bytes]:
    try:
        if _is_link(path) or not path.is_file():
            raise OSError(f"not a regular file: {path}")
        raw = path.read_bytes()
        rows: list[dict[str, Any]] = []
        for line_number, line in enumerate(raw.splitlines(), start=1):
            value = json.loads(
                line.decode("utf-8"),
                object_pairs_hook=lambda pairs: _reject_duplicate_pairs(pairs, label, line_number),
                parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-finite JSON constant: {value}")),
            )
            if not isinstance(value, dict):
                raise ValueError(f"line {line_number} is not an object")
            rows.append(value)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise AnomalyMatrixRunnerError(f"{label} is not strict JSONL: {exc}") from exc
    return rows, raw


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]], label: str, line_number: int) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"{label} line {line_number} has duplicate JSON property: {key}")
        result[key] = value
    return result


def _safe_relative(path: Path, root: Path, label: str) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError as exc:
        raise _GlobalFailure(f"{label} escaped the repository") from exc


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
    except OSError:
        pass
    descriptor: int | None = None
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
        descriptor = os.open(target, flags, 0o644)
        with os.fdopen(descriptor, "wb") as handle, source.open("rb") as source_handle:
            descriptor = None
            shutil.copyfileobj(source_handle, handle)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise AnomalyMatrixRunnerError(f"refusing to replace published {label}: {target}") from exc
    except OSError as exc:
        try:
            target.unlink(missing_ok=True)
        except OSError:
            pass
        raise AnomalyMatrixRunnerError(f"could not place published {label}: {target}") from exc
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass


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
    config_resolved = anomaly_matrix._resolve_config_path(config_path, root)
    config, config_source = _source_entry(root, config_resolved, config_relative, "matrix config")
    raw_paths = {
        "matrix_schema": (config.get("schema_path"), "matrix config schema"),
        "base_generator_config": (config.get("base_generator_config_path"), "base generator config"),
        "base_generator_schema": (config.get("base_generator_schema_path"), "base generator schema"),
        "anomaly_config_schema": (ANOMALY_CONFIG_SCHEMA_PATH, "anomaly evaluation config schema"),
        "anomaly_result_schema": (ANOMALY_RESULT_SCHEMA_PATH, "anomaly evaluation result schema"),
        "matrix_result_schema": (RESULT_SCHEMA_PATH, "anomaly matrix result schema"),
    }
    sources: dict[str, Any] = {"matrix_config": config_source}
    values: dict[str, Any] = {"matrix_config": config}
    for key, (relative, label) in raw_paths.items():
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


def _iso_at(start_timestamp: str, sample: int, interval_ms: int) -> str:
    try:
        start = datetime.fromisoformat(start_timestamp.replace("Z", "+00:00"))
        if start.tzinfo is None or start.utcoffset() != timedelta(0):
            raise ValueError("timestamp must be UTC")
        value = start.astimezone(timezone.utc) + sample * timedelta(milliseconds=interval_ms)
        return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    except (TypeError, ValueError) as exc:
        raise AnomalyMatrixRunnerError(f"base start_timestamp is invalid: {exc}") from exc


def _validate_dataset(cell: Mapping[str, Any], base: Mapping[str, Any], root: Path) -> dict[str, Any]:
    dataset_path = cell["paths"]["dataset"]
    if _is_link(dataset_path) or not dataset_path.is_dir():
        raise AnomalyMatrixRunnerError(f"generated dataset is not a regular directory: {dataset_path}")
    manifest_path = dataset_path / "dataset-manifest.json"
    manifest, manifest_raw = _strict_json_object(manifest_path, "dataset manifest")
    schema_path = anomaly_matrix._safe_repo_path(root, "schemas/synthetic-dataset-manifest.schema.json", "synthetic dataset manifest schema", must_exist=True)
    schema, _schema_raw, _schema_raw_sha256, _schema_canonical_sha256 = anomaly_matrix._load_object_snapshot(schema_path, "synthetic dataset manifest schema")
    try:
        validate(manifest, schema)
    except ManifestValidationError as exc:
        raise AnomalyMatrixRunnerError(f"generated dataset manifest does not satisfy its schema: {exc}") from exc
    if manifest.get("dataset_id") != cell["generator_config"]["dataset_id"] or manifest.get("seed") != cell["seed"]:
        raise AnomalyMatrixRunnerError("generated dataset manifest identity drifted")
    observations_path = dataset_path / "observations.jsonl"
    events_path = dataset_path / "events.jsonl"
    observations, observations_raw = _jsonl_objects(observations_path, "observations")
    events, _events_raw = _jsonl_objects(events_path, "events")
    expected_events = cell["generator_config"]["events"]
    expected_by_id = {event["event_id"]: event for event in expected_events}
    interval_ms = int(base["sampling_interval_ms"])
    actual_by_id: dict[str, dict[str, Any]] = {}
    for event in events:
        event_id = event.get("event_id")
        if event_id in actual_by_id:
            raise AnomalyMatrixRunnerError(f"generated dataset event is duplicated: {event_id}")
        actual_by_id[event_id] = event
    if set(actual_by_id) != set(expected_by_id):
        raise AnomalyMatrixRunnerError("generated dataset event inventory IDs drifted")
    for event_id, expected in expected_by_id.items():
        actual = actual_by_id[event_id]
        expected_values = {
            "event_type": expected["event_type"],
            "equipment_id": expected["equipment_id"],
            "signal_id": expected["signal_id"],
            "start_timestamp": _iso_at(base["start_timestamp"], expected["start_sample"], interval_ms),
            "end_timestamp": _iso_at(base["start_timestamp"], expected["end_sample"], interval_ms),
            "magnitude": expected["magnitude"],
        }
        if any(actual.get(key) != value for key, value in expected_values.items()):
            raise AnomalyMatrixRunnerError(f"generated dataset event inventory drifted: {event_id}")
    fingerprint_path = dataset_path / "fingerprint.json"
    fingerprint, _fingerprint_raw = _strict_json_object(fingerprint_path, "dataset fingerprint")
    if fingerprint.get("algorithm") != FINGERPRINT_ALGORITHM or fingerprint.get("canonicalization") != FINGERPRINT_CANONICALIZATION:
        raise AnomalyMatrixRunnerError("generated dataset fingerprint contract drifted")
    files = fingerprint.get("files")
    if not isinstance(files, dict) or set(files) != set(FINGERPRINT_FILE_NAMES):
        raise AnomalyMatrixRunnerError("generated dataset fingerprint file inventory drifted")
    file_hashes: dict[str, str] = {}
    for name in FINGERPRINT_FILE_NAMES:
        target = dataset_path / name
        if _is_link(target) or not target.is_file():
            raise AnomalyMatrixRunnerError(f"generated dataset fingerprint input is missing: {name}")
        file_hashes[name] = _sha256_bytes(target.read_bytes())
    if file_hashes != files:
        raise AnomalyMatrixRunnerError("generated dataset fingerprint file hash drifted")
    fingerprint_input = "".join(f"{name}\n{digest}\n" for name, digest in sorted(file_hashes.items())).encode("utf-8")
    if fingerprint.get("dataset_fingerprint") != _sha256_bytes(fingerprint_input):
        raise AnomalyMatrixRunnerError("generated dataset fingerprint value drifted")
    summary, _summary_raw = _strict_json_object(dataset_path / "summary.json", "dataset summary")
    if summary.get("dataset_fingerprint") != fingerprint.get("dataset_fingerprint") or summary.get("event_count") != 4:
        raise AnomalyMatrixRunnerError("generated dataset summary drifted")
    return {
        "path": _safe_relative(dataset_path, root, "dataset path"),
        "dataset_fingerprint": fingerprint["dataset_fingerprint"],
        "manifest_sha256": _sha256_bytes(manifest_raw),
        "observations_path": _safe_relative(observations_path, root, "observations path"),
        "observations_sha256": _sha256_bytes(observations_raw),
        "observation_record_count": len(observations),
        "event_count": len(events),
    }


def _call_injected(function: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    try:
        signature = inspect.signature(function)
        accepts_kwargs = any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in signature.parameters.values())
        filtered = kwargs if accepts_kwargs else {key: value for key, value in kwargs.items() if key in signature.parameters}
        return function(*args, **filtered)
    except (TypeError, ValueError):
        return function(*args, **kwargs)


def _validate_evaluation(cell: Mapping[str, Any], evaluation_return: Any, root: Path, result_schema: Mapping[str, Any], sources: Mapping[str, Any], revision: Mapping[str, Any], dataset: Mapping[str, Any], evaluator_config_raw_sha256: str) -> dict[str, Any]:
    expected_path = cell["paths"]["evaluation"]
    returned_path = Path(evaluation_return)
    if not returned_path.is_absolute():
        returned_path = (root / returned_path).absolute()
    if returned_path != expected_path:
        raise _GlobalFailure("evaluator returned a path outside the planned evaluation output")
    if _is_link(returned_path) or not returned_path.is_dir():
        raise AnomalyMatrixRunnerError("evaluator output is not a regular directory")
    result_path = returned_path / "result.json"
    summary_path = returned_path / "summary.md"
    marker_path = returned_path / COMPLETION_MARKER
    result, result_raw = _strict_json_object(result_path, "cell evaluator result")
    try:
        validate(result, result_schema)
    except ManifestValidationError as exc:
        raise AnomalyMatrixRunnerError(f"cell evaluator result does not satisfy its schema: {exc}") from exc
    if result.get("status") not in ("pass", "partial", "inconclusive"):
        raise AnomalyMatrixRunnerError("cell evaluator status is invalid")
    if _is_link(summary_path) or not summary_path.is_file() or _is_link(marker_path) or not marker_path.is_file():
        raise AnomalyMatrixRunnerError("cell evaluator completion payload is incomplete")
    summary_raw = summary_path.read_bytes()
    marker, _marker_raw = _strict_json_object(marker_path, "cell evaluator completion marker")
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
    return {
        "path": _safe_relative(returned_path, root, "evaluation path"),
        "result_path": _safe_relative(result_path, root, "cell result path"),
        "result_sha256": _sha256_bytes(result_raw),
        "summary_path": _safe_relative(summary_path, root, "cell summary path"),
        "summary_sha256": _sha256_bytes(summary_raw),
        "completion_marker_path": _safe_relative(marker_path, root, "cell completion marker path"),
        "completion_marker_sha256": _sha256_bytes(marker_path.read_bytes()),
        "status": result["status"],
    }


def _safe_error(exc: BaseException, root: Path) -> str:
    value = str(exc).replace("\\", "/")
    return value.replace(str(root).replace("\\", "/"), "<repository>")


def _cell_failure(cell: Mapping[str, Any], exc: BaseException, root: Path) -> dict[str, Any]:
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
        "reason": _safe_error(exc, root),
        "artifacts": {"generator_config": None, "evaluator_config": None, "dataset": None, "evaluation": None},
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
        "evaluator_status": evaluation["status"],
        "error_type": None,
        "reason": None,
        "artifacts": {
            "generator_config": {"path": _safe_relative(cell["paths"]["generator_config"], root, "generator config path"), "raw_sha256": _sha256_bytes(generator_config_raw), "canonical_sha256": _sha256_bytes(_canonical_json(cell["generator_config"]))},
            "evaluator_config": {"path": _safe_relative(cell["paths"]["evaluator_config"], root, "evaluator config path"), "raw_sha256": _sha256_bytes(evaluator_config_raw), "canonical_sha256": _sha256_bytes(_canonical_json(cell["evaluator_config"]))},
            "dataset": dataset,
            "evaluation": evaluation,
        },
    }


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
        if validation.get("config_canonical_sha256") != sources["matrix_config"]["canonical_sha256"] or validation.get("canonicalization") != anomaly_matrix.CANONICALIZATION_ID:
            raise _GlobalFailure("Savepoint A validation provenance does not match input snapshot")
        if validation.get("schema", {}).get("canonical_sha256") != sources["matrix_schema"]["canonical_sha256"] or validation.get("base_generator_schema", {}).get("canonical_sha256") != sources["base_generator_schema"]["canonical_sha256"]:
            raise _GlobalFailure("Savepoint A schema provenance does not match input snapshot")
        revision = _require_revision(repository, boundary="preflight")
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
                try:
                    _write_exclusive(cell["paths"]["generator_config"], generator_config_raw, "generator config")
                    _write_exclusive(cell["paths"]["evaluator_config"], evaluator_config_raw, "evaluator config")
                    generated_path = _call_injected(generator, cell["paths"]["generator_config"], cell["paths"]["dataset"], repository)
                    returned_dataset_path = Path(generated_path)
                    if not returned_dataset_path.is_absolute():
                        returned_dataset_path = (repository / returned_dataset_path).absolute()
                    if returned_dataset_path != cell["paths"]["dataset"].absolute():
                        raise _GlobalFailure("generator returned a path outside the planned dataset output")
                    dataset = _validate_dataset(cell, base, repository)
                    layout_fingerprints[cell["layout_id"]].add(dataset["dataset_fingerprint"])
                    layout_observation_hashes[cell["layout_id"]].add(dataset["observations_sha256"])
                    evaluation_kwargs = {"recover_incomplete": False, "allowed_output_parent": output / "evaluations"}
                    evaluation_return = _call_injected(evaluator, cell["paths"]["evaluator_config"], repository, **evaluation_kwargs)
                    evaluation = _validate_evaluation(cell, evaluation_return, repository, values["anomaly_result_schema"], sources, revision, dataset, _sha256_bytes(evaluator_config_raw))
                    cells.append(_cell_success(cell, repository, generator_config_raw, evaluator_config_raw, dataset, evaluation))
                except _GlobalFailure:
                    raise
                except Exception as exc:
                    cells.append(_cell_failure(cell, exc, repository))
                _assert_inputs_unchanged(repository, sources, values, "cell-completion")
                _require_revision(repository, revision, "cell-completion")
        if len(cells) != expected_cell_count:
            raise _GlobalFailure("matrix did not process the fixed cell count")
        distinct_fingerprints = all(len(layout_fingerprints[layout_id]) == len(config["seeds"]) for layout_id in layout_fingerprints)
        distinct_observations = all(len(layout_observation_hashes[layout_id]) == len(config["seeds"]) for layout_id in layout_observation_hashes)
        order_ok = [cell["cell_id"] for cell in cells] == [
            _materialize_cell(config, base, seed, layout, repository, output)["cell_id"]
            for seed in config["seeds"]
            for layout in sorted(config["layouts"], key=lambda item: item["layout_index"])
        ]
        success_count = sum(cell["status"] == "pass" for cell in cells)
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
            engineering_status = "pass" if success_count == 120 else ("fail" if failed_count else "not_complete")
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
        _assert_inputs_unchanged(repository, sources, values, "aggregate-marker")
        _require_revision(repository, revision, "aggregate-marker")
        return _publish(repository, output, result, lambda: (_assert_inputs_unchanged(repository, sources, values, "before-marker"), _require_revision(repository, revision, "before-marker")))
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
