"""Read-only seed-cluster analysis for the preregistered anomaly matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from . import anomaly_matrix, anomaly_matrix_runner as runner
from .anomaly_evaluation import _canonical_time
from .benchmark import _revision
from .manifest import ManifestValidationError, validate


ANALYSIS_SCHEMA_VERSION = "0.2"
ANALYSIS_CONFIG_TYPE = "event-aware-anomaly-matrix-analysis"
ANALYSIS_RESULT_TYPE = "event-aware-anomaly-matrix-analysis"
ANALYSIS_ID = "anomaly-multiseed-analysis-v02"
ANALYSIS_CONFIG_PATH = "examples/configs/anomaly-multiseed-analysis-v0.2.json"
ANALYSIS_SCHEMA_PATH = "schemas/anomaly-multiseed-analysis-config-v0.2.schema.json"
ANALYSIS_RESULT_SCHEMA_PATH = "schemas/anomaly-multiseed-analysis-result-v0.2.schema.json"
EXPECTED_MATRIX_ID = "anomaly-multiseed-v02"
EXPECTED_MATRIX_CONFIG_PATH = "examples/configs/anomaly-multiseed-v0.2.json"
EXPECTED_MATRIX_RESULT_SCHEMA_PATH = "schemas/anomaly-multiseed-matrix-result-v0.2.schema.json"
EXPECTED_INPUT_ROOT = "artifacts/anomaly-multiseed-v02"
EXPECTED_OUTPUT_ROOT = "artifacts/anomaly-multiseed-v02-analysis"
CANONICALIZATION_ID = anomaly_matrix.CANONICALIZATION_ID
BOOTSTRAP_ALGORITHM_ID = "sha256-counter-rejection-v1"
BOOTSTRAP_SEED = 20260905
BOOTSTRAP_RESAMPLES = 10000
BOOTSTRAP_CONFIDENCE_LEVEL = 0.95
BOOTSTRAP_CLUSTER_COUNT = 10
BOOTSTRAP_LAYOUTS_PER_CLUSTER = 12
BOOTSTRAP_EVENTS_PER_CLUSTER = 48
PROMOTION_THRESHOLDS = {
    "overall_incident_precision": {"point_min": 0.80, "ci_lower_min": 0.60},
    "machine_fault_recall": {"point_min": 0.80, "ci_lower_min": 0.60},
    "sensor_fault_recall": {"point_min": 0.90, "ci_lower_min": 0.75},
    "clean_false_alerts_per_8_equipment_hours": {"point_max": 1.0, "ci_upper_max": 2.0},
    "signal_availability": {"minimum": 0.95},
}

# Filled after the two new JSON contracts are added.
EXPECTED_ANALYSIS_SCHEMA_CANONICAL_SHA256 = "401ebf4ba348212437c2f2e3b9ee4de9c53b9c33803129cfa1384fbf2dc26de5"
EXPECTED_ANALYSIS_CONFIG_CANONICAL_SHA256 = "9fc7b1a97b287050adb97d67cb6aa862d719b07d6b9f5e6e20243f72be4b8e2e"
EXPECTED_ANALYSIS_RESULT_SCHEMA_CANONICAL_SHA256 = "de1254212fbaf4feb9e5be29fb00bc1020ee0c23008cc184477894ebb573e1e9"
EXPECTED_MATRIX_CONFIG_CANONICAL_SHA256 = anomaly_matrix.EXPECTED_V02_CONFIG_CANONICAL_SHA256
EXPECTED_MATRIX_RESULT_SCHEMA_CANONICAL_SHA256 = anomaly_matrix.EXPECTED_V02_RESULT_SCHEMA_CANONICAL_SHA256


class AnomalyMatrixAnalysisError(ValueError):
    """Analysis configuration, artifact, or statistical contract failure."""


class AnalysisGlobalFailure(AnomalyMatrixAnalysisError):
    """A failure that invalidates the complete analysis."""


def _canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise AnomalyMatrixAnalysisError(f"value cannot be canonically serialized: {exc}") from exc


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return _canonical_json(value) + b"\n"


def _strict_object(path: Path, label: str) -> tuple[dict[str, Any], bytes, str, str]:
    try:
        if runner._is_link(path) or not path.is_file():
            raise OSError(f"not a regular file: {path}")
        raw = path.read_bytes()
    except OSError as exc:
        raise AnalysisGlobalFailure(f"{label} cannot be read safely") from exc
    try:
        value = runner._parse_json_object_bytes(raw, label, AnalysisGlobalFailure)
    except AnalysisGlobalFailure:
        raise
    return value, raw, _sha256(raw), _sha256(_canonical_json(value))


def _source(root: Path, relative: str, label: str) -> tuple[dict[str, str], dict[str, Any]]:
    path = anomaly_matrix._safe_repo_path(root, relative, label, must_exist=True)
    value, raw, raw_sha, canonical_sha = _strict_object(path, label)
    return {"path": relative, "raw_sha256": raw_sha, "canonical_sha256": canonical_sha}, {"value": value, "raw": raw, "path": path}


def _require_exact(actual: Any, expected: Any, label: str) -> None:
    if actual != expected or type(actual) is not type(expected):
        raise AnomalyMatrixAnalysisError(f"{label} is not fixed to {expected!r}")


def _profile_config_path(root: Path, value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise AnomalyMatrixAnalysisError(f"{label} must be a repository-relative path")
    relative = anomaly_matrix._config_relative_path(value, root)
    anomaly_matrix._safe_repo_path(root, relative, label, must_exist=True)
    return relative


def _load_analysis_inputs(config_path: str | Path, root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    relative = anomaly_matrix._config_relative_path(config_path, root)
    if relative != ANALYSIS_CONFIG_PATH:
        raise AnomalyMatrixAnalysisError(f"unknown analysis profile: {relative}")
    path = anomaly_matrix._safe_repo_path(root, relative, "analysis config", must_exist=True)
    config, raw, raw_sha, canonical_sha = _strict_object(path, "analysis config")
    schema_relative = config.get("schema_path")
    if schema_relative != ANALYSIS_SCHEMA_PATH:
        raise AnomalyMatrixAnalysisError("analysis schema path is not the preregistered profile")
    schema_path = anomaly_matrix._safe_repo_path(root, schema_relative, "analysis config schema", must_exist=True)
    schema, schema_raw, schema_raw_sha, schema_canonical_sha = _strict_object(schema_path, "analysis config schema")
    if EXPECTED_ANALYSIS_SCHEMA_CANONICAL_SHA256 and schema_canonical_sha != EXPECTED_ANALYSIS_SCHEMA_CANONICAL_SHA256:
        raise AnomalyMatrixAnalysisError("analysis config schema canonical SHA-256 pin is invalid")
    if EXPECTED_ANALYSIS_CONFIG_CANONICAL_SHA256 and canonical_sha != EXPECTED_ANALYSIS_CONFIG_CANONICAL_SHA256:
        raise AnomalyMatrixAnalysisError("analysis config canonical SHA-256 pin is invalid")
    try:
        validate(config, schema)
    except ManifestValidationError as exc:
        raise AnomalyMatrixAnalysisError(f"analysis config does not satisfy its schema: {exc}") from exc
    if config.get("schema_canonical_sha256") != schema_canonical_sha:
        raise AnomalyMatrixAnalysisError("analysis config schema digest pin is invalid")
    return config, {
        "path": relative,
        "raw": raw,
        "raw_sha256": raw_sha,
        "canonical_sha256": canonical_sha,
    }, {
        "path": schema_relative,
        "raw": schema_raw,
        "raw_sha256": schema_raw_sha,
        "canonical_sha256": schema_canonical_sha,
        "value": schema,
    }


def validate_analysis_config(config_path: str | Path = ANALYSIS_CONFIG_PATH, root: Path | None = None) -> dict[str, Any]:
    """Validate the fixed analysis contract without writing to the filesystem."""
    repository = Path(root or Path(__file__).resolve().parents[2]).expanduser().resolve()
    config, config_source, schema_source = _load_analysis_inputs(config_path, repository)
    _require_exact(config.get("schema_version"), ANALYSIS_SCHEMA_VERSION, "schema_version")
    _require_exact(config.get("config_type"), ANALYSIS_CONFIG_TYPE, "config_type")
    _require_exact(config.get("analysis_id"), ANALYSIS_ID, "analysis_id")
    _require_exact(config.get("matrix_id"), EXPECTED_MATRIX_ID, "matrix_id")
    _require_exact(config.get("matrix_config_path"), EXPECTED_MATRIX_CONFIG_PATH, "matrix_config_path")
    _require_exact(config.get("matrix_config_canonical_sha256"), EXPECTED_MATRIX_CONFIG_CANONICAL_SHA256, "matrix_config_canonical_sha256")
    _require_exact(config.get("matrix_result_schema_path"), EXPECTED_MATRIX_RESULT_SCHEMA_PATH, "matrix_result_schema_path")
    _require_exact(config.get("matrix_result_schema_canonical_sha256"), EXPECTED_MATRIX_RESULT_SCHEMA_CANONICAL_SHA256, "matrix_result_schema_canonical_sha256")
    _require_exact(config.get("input_root"), EXPECTED_INPUT_ROOT, "input_root")
    _require_exact(config.get("output_root"), EXPECTED_OUTPUT_ROOT, "output_root")
    _profile_config_path(repository, config["matrix_config_path"], "matrix_config_path")
    _profile_config_path(repository, config["matrix_result_schema_path"], "matrix_result_schema_path")
    anomaly_matrix._safe_repo_path(repository, config["input_root"], "input_root", must_exist=False)
    anomaly_matrix._safe_repo_path(repository, config["output_root"], "output_root", must_exist=False)
    _require_exact(config.get("bootstrap"), {
        "algorithm_id": BOOTSTRAP_ALGORITHM_ID,
        "seed": BOOTSTRAP_SEED,
        "resamples": BOOTSTRAP_RESAMPLES,
        "confidence_level": BOOTSTRAP_CONFIDENCE_LEVEL,
        "cluster_count": BOOTSTRAP_CLUSTER_COUNT,
        "layouts_per_cluster": BOOTSTRAP_LAYOUTS_PER_CLUSTER,
        "events_per_cluster": BOOTSTRAP_EVENTS_PER_CLUSTER,
        "sampling": "seed_cluster_with_replacement",
        "percentile_method": "linear_interpolation_n_minus_1",
    }, "bootstrap")
    _require_exact(config.get("promotion_thresholds"), PROMOTION_THRESHOLDS, "promotion_thresholds")
    return {
        "schema_version": ANALYSIS_SCHEMA_VERSION,
        "summary_type": "event-aware-anomaly-matrix-analysis-validation",
        "status": "configuration_valid",
        "run_status": "not_run",
        "performance_status": "not_evaluated",
        "analysis_id": ANALYSIS_ID,
        "matrix_id": EXPECTED_MATRIX_ID,
        "config_path": config_source["path"],
        "config_canonical_sha256": config_source["canonical_sha256"],
        "schema": {"path": schema_source["path"], "canonical_sha256": schema_source["canonical_sha256"]},
        "safety": {"filesystem_write": False, "matrix_artifact_write": False, "customer_data": False, "network": False, "control_write": False},
    }


def _hash_draws(draws: list[int]) -> str:
    return _sha256(_canonical_json(draws))


def _draw_index(seed: int, replicate: int, cluster: int, count: int) -> int:
    limit = (1 << 256) - ((1 << 256) % count)
    counter = 0
    while True:
        raw = hashlib.sha256(f"{BOOTSTRAP_ALGORITHM_ID}:{seed}:{replicate}:{cluster}:{counter}".encode("ascii")).digest()
        value = int.from_bytes(raw, "big")
        if value < limit:
            return value % count
        counter += 1


def bootstrap_draws(*, seed: int = BOOTSTRAP_SEED, resamples: int = BOOTSTRAP_RESAMPLES, cluster_count: int = BOOTSTRAP_CLUSTER_COUNT) -> tuple[list[list[int]], str]:
    """Generate version-stable seed-cluster draws with SHA-256 rejection sampling."""
    if seed != BOOTSTRAP_SEED or resamples != BOOTSTRAP_RESAMPLES or cluster_count != BOOTSTRAP_CLUSTER_COUNT:
        raise AnomalyMatrixAnalysisError("bootstrap draw parameters are not preregistered")
    flat: list[int] = []
    draws: list[list[int]] = []
    for replicate in range(resamples):
        row = [_draw_index(seed, replicate, cluster, cluster_count) for cluster in range(cluster_count)]
        draws.append(row)
        flat.extend(row)
    return draws, _hash_draws(flat)


def percentile_linear(values: list[float], probability: float) -> float:
    """Use Hyndman-Fan type 7 / linear interpolation at (n-1)*p."""
    if not values or not 0.0 <= probability <= 1.0:
        raise AnomalyMatrixAnalysisError("percentile requires non-empty values and p in [0,1]")
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[lower])
    fraction = position - lower
    return float(ordered[lower] + fraction * (ordered[upper] - ordered[lower]))


@dataclass
class _Aggregate:
    precision_num: int = 0
    precision_den: int = 0
    machine_num: int = 0
    machine_den: int = 0
    sensor_num: int = 0
    sensor_den: int = 0
    clean_alerts: int = 0
    clean_hours: float = 0.0
    availability: dict[str, list[int]] | None = None

    def __post_init__(self) -> None:
        if self.availability is None:
            self.availability = {}

    def add(self, other: "_Aggregate") -> None:
        self.precision_num += other.precision_num
        self.precision_den += other.precision_den
        self.machine_num += other.machine_num
        self.machine_den += other.machine_den
        self.sensor_num += other.sensor_num
        self.sensor_den += other.sensor_den
        self.clean_alerts += other.clean_alerts
        self.clean_hours += other.clean_hours
        assert self.availability is not None and other.availability is not None
        for key, pair in other.availability.items():
            current = self.availability.setdefault(key, [0, 0])
            current[0] += pair[0]
            current[1] += pair[1]


def _ratio(numerator: int | float, denominator: int | float) -> float | None:
    if denominator == 0:
        return None
    value = float(numerator) / float(denominator)
    return value if math.isfinite(value) else None


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise AnalysisGlobalFailure(f"timestamp is invalid: {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _delay_summary(delays: list[float]) -> dict[str, Any]:
    if not delays:
        return {"count": 0, "mean_seconds": None, "median_seconds": None}
    ordered = sorted(float(value) for value in delays)
    if any(not math.isfinite(value) or value < 0 for value in ordered):
        raise AnalysisGlobalFailure("detection delay is nonfinite or negative")
    midpoint = len(ordered) // 2
    median = ordered[midpoint] if len(ordered) % 2 else (ordered[midpoint - 1] + ordered[midpoint]) / 2.0
    return {"count": len(ordered), "mean_seconds": sum(ordered) / len(ordered), "median_seconds": median}


def _primary_values(aggregate: _Aggregate) -> dict[str, float | None]:
    return {
        "overall_incident_precision": _ratio(aggregate.precision_num, aggregate.precision_den),
        "machine_fault_recall": _ratio(aggregate.machine_num, aggregate.machine_den),
        "sensor_fault_recall": _ratio(aggregate.sensor_num, aggregate.sensor_den),
        "clean_false_alerts_per_8_equipment_hours": _ratio(aggregate.clean_alerts * 8.0, aggregate.clean_hours),
    }


def _ci(values: list[float], *, probability: float = BOOTSTRAP_CONFIDENCE_LEVEL, undefined_count: int = 0) -> dict[str, Any]:
    if undefined_count:
        return {"status": "inconclusive", "lower": None, "upper": None, "undefined_replicates": undefined_count}
    alpha = (1.0 - probability) / 2.0
    return {"status": "pass", "lower": percentile_linear(values, alpha), "upper": percentile_linear(values, 1.0 - alpha), "undefined_replicates": 0}


def _gate_status(point: float | None, ci: Mapping[str, Any], threshold: Mapping[str, Any], *, lower: bool = True) -> str:
    if point is None or ci.get("status") != "pass":
        return "inconclusive"
    if "point_min" in threshold:
        return "pass" if point >= threshold["point_min"] and float(ci["lower"]) >= threshold["ci_lower_min"] else "fail"
    if "point_max" in threshold:
        return "pass" if point <= threshold["point_max"] and float(ci["upper"]) <= threshold["ci_upper_max"] else "fail"
    return "inconclusive"


def _verify_source_provenance(result: Mapping[str, Any], sources: Mapping[str, Mapping[str, str]], revision: Mapping[str, Any]) -> None:
    provenance = result.get("provenance")
    if not isinstance(provenance, Mapping) or provenance.get("canonicalization") != CANONICALIZATION_ID or provenance.get("code_revision") != dict(revision):
        raise AnalysisGlobalFailure("matrix result provenance or current code revision is invalid")
    inputs = provenance.get("inputs")
    if not isinstance(inputs, Mapping):
        raise AnalysisGlobalFailure("matrix result input provenance is missing")
    for key, source in sources.items():
        public = {field: source[field] for field in ("path", "raw_sha256", "canonical_sha256")}
        if inputs.get(key) != public:
            raise AnalysisGlobalFailure(f"matrix result provenance drifted: {key}")


def _expected_cell(config: Mapping[str, Any], base: Mapping[str, Any], cell: Mapping[str, Any], root: Path, input_root: Path) -> dict[str, Any]:
    seed = cell.get("seed")
    layout_index = cell.get("layout_index")
    layout = next((item for item in config["layouts"] if item.get("layout_index") == layout_index), None)
    if layout is None or seed not in config["seeds"]:
        raise AnalysisGlobalFailure("matrix cell references an unknown seed or layout")
    expected = runner._materialize_cell(config, base, seed, layout, root, input_root)
    expected_id = expected["cell_id"]
    if cell.get("cell_id") != expected_id:
        raise AnalysisGlobalFailure("matrix cell identity drifted")
    return expected


def _artifact_path(cell: Mapping[str, Any], key: str) -> str:
    artifacts = cell.get("artifacts")
    item = artifacts.get(key) if isinstance(artifacts, Mapping) else None
    if not isinstance(item, Mapping) or not isinstance(item.get("path"), str):
        raise AnalysisGlobalFailure(f"matrix cell artifact path is missing: {key}")
    return item["path"]


def _verify_cell_and_collect(
    cell: Mapping[str, Any],
    config: Mapping[str, Any],
    base: Mapping[str, Any],
    root: Path,
    input_root: Path,
    sources: Mapping[str, Mapping[str, str]],
    values: Mapping[str, Any],
    revision: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], set[str]]:
    expected = _expected_cell(config, base, cell, root, input_root)
    expected_paths = {
        "generator_config": expected["paths"]["generator_config"],
        "evaluator_config": expected["paths"]["evaluator_config"],
        "dataset": expected["paths"]["dataset"],
        "evaluation": expected["paths"]["evaluation"],
    }
    for key in expected_paths:
        actual = _artifact_path(cell, key)
        expected_relative = expected_paths[key].relative_to(root).as_posix()
        if actual != expected_relative:
            raise AnalysisGlobalFailure(f"matrix cell {key} path is not deterministic")
    generator_path = expected_paths["generator_config"]
    evaluator_path = expected_paths["evaluator_config"]
    generator_value, generator_raw, generator_raw_sha, generator_canonical_sha = _strict_object(generator_path, "materialized generator config")
    evaluator_value, evaluator_raw, evaluator_raw_sha, evaluator_canonical_sha = _strict_object(evaluator_path, "materialized evaluator config")
    expected_generator_raw = _json_bytes(expected["generator_config"])
    expected_evaluator_raw = _json_bytes(expected["evaluator_config"])
    if generator_raw != expected_generator_raw or evaluator_raw != expected_evaluator_raw:
        raise AnalysisGlobalFailure("materialized generator/evaluator config drifted")
    artifact_generator = cell["artifacts"]["generator_config"]
    artifact_evaluator = cell["artifacts"]["evaluator_config"]
    if artifact_generator != {"path": generator_path.relative_to(root).as_posix(), "raw_sha256": generator_raw_sha, "canonical_sha256": generator_canonical_sha}:
        raise AnalysisGlobalFailure("generator config artifact evidence drifted")
    if artifact_evaluator != {"path": evaluator_path.relative_to(root).as_posix(), "raw_sha256": evaluator_raw_sha, "canonical_sha256": evaluator_canonical_sha}:
        raise AnalysisGlobalFailure("evaluator config artifact evidence drifted")
    dataset_evidence, dataset_snapshot, dataset_ledger = runner._validate_dataset(
        expected, base, root, values["dataset_manifest_schema"], expected_generator_raw
    )
    if cell["artifacts"]["dataset"] != dataset_evidence:
        raise AnalysisGlobalFailure("dataset artifact evidence drifted")
    evaluation_evidence, evaluation_snapshot = runner._validate_evaluation(
        expected,
        expected_paths["evaluation"],
        root,
        values["anomaly_result_schema"],
        sources,
        revision,
        dataset_evidence,
        dataset_ledger,
        evaluator_raw_sha,
    )
    if cell["artifacts"]["evaluation"] != evaluation_evidence:
        raise AnalysisGlobalFailure("evaluation artifact evidence drifted")
    evaluation_value, evaluation_raw, _evaluation_raw_sha, _evaluation_canonical_sha = _strict_object(expected_paths["evaluation"] / "result.json", "cell evaluation result")
    expected_files = {generator_path.relative_to(input_root).as_posix(), evaluator_path.relative_to(input_root).as_posix()}
    expected_files.update(f"{expected_paths['dataset'].relative_to(input_root).as_posix()}/{name}" for name, kind in dataset_snapshot["inventory"] if kind == "file")
    expected_files.update(f"{expected_paths['evaluation'].relative_to(input_root).as_posix()}/{name}" for name, kind in evaluation_snapshot["inventory"] if kind == "file")
    return evaluation_value, expected, expected_files


def _cell_aggregate(evaluation: Mapping[str, Any], cell: Mapping[str, Any], config: Mapping[str, Any]) -> tuple[_Aggregate, dict[str, Any]]:
    metrics = evaluation.get("metrics")
    if not isinstance(metrics, Mapping):
        raise AnalysisGlobalFailure("cell evaluation metrics are missing")
    overall = metrics.get("overall")
    if not isinstance(overall, Mapping):
        raise AnalysisGlobalFailure("cell overall metrics are missing")
    aggregate = _Aggregate(
        precision_num=int(overall.get("matched_eligible_alert_episodes", 0)),
        precision_den=int(overall.get("evaluated_alert_episode_count", 0)),
        clean_alerts=int(metrics.get("clean_false_alert_equipment_episode_count", 0)),
        clean_hours=float(metrics.get("clean_monitored_equipment_hours", 0.0)),
    )
    availability = metrics.get("score_availability_by_signal")
    if not isinstance(availability, Mapping):
        raise AnalysisGlobalFailure("cell signal availability is missing")
    for signal, value in availability.items():
        if not isinstance(value, Mapping):
            raise AnalysisGlobalFailure("cell availability row is invalid")
        aggregate.availability[signal] = [int(value.get("available_points", 0)), int(value.get("total_points", 0))]
    incidents = evaluation.get("incidents")
    if not isinstance(incidents, list):
        raise AnalysisGlobalFailure("cell incidents are missing")
    mode = next((item["operating_mode"] for item in config["layouts"] if item["layout_id"] == cell["layout_id"]), None)
    equipment = cell["artifacts"]["dataset"].get("path") if isinstance(cell.get("artifacts"), Mapping) else None
    deltas: dict[str, list[float]] = {}
    for incident in incidents:
        if not isinstance(incident, Mapping) or incident.get("eligible") is not True:
            continue
        event_class = incident.get("event_class")
        detected = incident.get("detected") is True
        if event_class == "machine_fault":
            aggregate.machine_den += 1
            aggregate.machine_num += int(detected)
        elif event_class == "sensor_fault":
            aggregate.sensor_den += 1
            aggregate.sensor_num += int(detected)
        if event_class in ("machine_fault", "sensor_fault") and mode:
            key = f"{event_class}|{incident.get('equipment_id')}|{mode}"
            row = deltas.setdefault(key, [0.0, 0.0, 0.0])
            row[0] += 1
            row[1] += int(detected)
            if detected:
                delay = incident.get("detection_delay_seconds")
                if not isinstance(delay, (int, float)) or isinstance(delay, bool) or not math.isfinite(float(delay)) or float(delay) < 0:
                    raise AnalysisGlobalFailure("incident detection delay is invalid")
                row[2] += float(delay)
    return aggregate, {"mode": mode, "equipment": equipment, "incident_slices": deltas}


def _combine_aggregates(aggregates: list[_Aggregate]) -> _Aggregate:
    combined = _Aggregate()
    for aggregate in aggregates:
        combined.add(aggregate)
    return combined


def _bootstrap_metric(seed_aggregates: list[_Aggregate], draws: list[list[int]], metric: str) -> tuple[float | None, dict[str, Any]]:
    values: list[float] = []
    undefined = 0
    for row in draws:
        sampled = _combine_aggregates([seed_aggregates[index] for index in row])
        value = _primary_values(sampled)[metric]
        if value is None or not math.isfinite(value):
            undefined += 1
        else:
            values.append(value)
    if undefined:
        return None, _ci([], undefined_count=undefined)
    return _primary_values(_combine_aggregates(seed_aggregates)), _ci(values)


def _mode_slice_records(slice_rows: Mapping[str, list[float]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, row in sorted(slice_rows.items()):
        denominator, numerator, delay_sum = row
        output[key] = {
            "eligible_incidents": int(denominator),
            "detected_incidents": int(numerator),
            "incident_recall": _ratio(numerator, denominator),
            "detection_delay_seconds": {"count": int(numerator), "mean_seconds": _ratio(delay_sum, numerator), "median_seconds": None},
        }
    return output


def _analysis_summary(result: Mapping[str, Any]) -> bytes:
    estimates = result["estimates"]
    gates = result["promotion_gates"]
    lines = [
        "# Event-aware anomaly matrix v0.2 analysis",
        "",
        f"- status: `{result['status']}`",
        f"- run_status: `{result['run_status']}`",
        f"- engineering_status: `{result['engineering_status']}`",
        f"- performance_status: `{result['performance_status']}`",
        f"- bootstrap: `{result['bootstrap']['algorithm_id']}`, `{result['bootstrap']['resamples']}` resamples, draw digest `{result['bootstrap']['draw_digest']}`",
        "",
        "## Primary estimates",
        "",
    ]
    for key in sorted(estimates.get("primary", {})):
        item = estimates["primary"][key]
        lines.append(f"- {key}: `{item['value']}`; CI `{item['ci']['lower']}` to `{item['ci']['upper']}` (`{item['ci']['status']}`)")
    lines.extend(["", "## Promotion gates", ""])
    for key in sorted(gates):
        lines.append(f"- {key}: `{gates[key]['status']}`")
    lines.extend(["", "Analysis is ratio-of-sums over seed-cluster aggregates; suppressed event-window alerts remain excluded from precision and no lead time is reported.", ""])
    return "\n".join(lines).encode("utf-8")


def _write_exclusive(path: Path, raw: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def _publish_analysis(root: Path, output: Path, result: Mapping[str, Any], verify_before_marker: Any) -> Path:
    if output.exists() or runner._is_link(output):
        raise AnalysisGlobalFailure(f"refusing to overwrite existing analysis output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".analysis-publish-", dir=output.parent))
    try:
        result_raw = _json_bytes(result)
        summary_raw = _analysis_summary(result)
        _write_exclusive(temporary / "result.json", result_raw)
        _write_exclusive(temporary / "summary.md", summary_raw)
        temporary.rename(output)
        verify_before_marker()
        marker = {"marker_type": "event-aware-anomaly-matrix-analysis-complete", "schema_version": ANALYSIS_SCHEMA_VERSION, "result_sha256": _sha256(result_raw), "summary_sha256": _sha256(summary_raw)}
        _write_exclusive(output / ".complete", _json_bytes(marker))
    except BaseException:
        if temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)
        raise
    return output


def analyze_anomaly_matrix(config_path: str | Path = ANALYSIS_CONFIG_PATH, root: Path | None = None) -> Path:
    """Verify a completed v0.2 matrix read-only and publish isolated analysis output."""
    repository = Path(root or Path(__file__).resolve().parents[2]).expanduser().resolve()
    analysis_config, analysis_source, analysis_schema_source = _load_analysis_inputs(config_path, repository)
    validation = validate_analysis_config(config_path, repository)
    matrix_config_path = anomaly_matrix._safe_repo_path(repository, analysis_config["matrix_config_path"], "matrix config", must_exist=True)
    sources, values = runner._snapshot_inputs(repository, matrix_config_path)
    matrix_config = values["matrix_config"]
    if sources["matrix_config"]["canonical_sha256"] != EXPECTED_MATRIX_CONFIG_CANONICAL_SHA256 or sources["matrix_result_schema"]["canonical_sha256"] != EXPECTED_MATRIX_RESULT_SCHEMA_CANONICAL_SHA256:
        raise AnalysisGlobalFailure("matrix config or result schema pin is invalid")
    if matrix_config.get("matrix_id") != EXPECTED_MATRIX_ID:
        raise AnalysisGlobalFailure("matrix profile identity is not v0.2")
    revision = runner._require_revision(repository, boundary="analysis-preflight")
    input_root = anomaly_matrix._safe_repo_path(repository, analysis_config["input_root"], "input_root", must_exist=True)
    output_root = anomaly_matrix._safe_repo_path(repository, analysis_config["output_root"], "output_root", must_exist=False)
    input_snapshot = runner._tree_snapshot(input_root, "matrix artifact", containment_root=repository, failure_scope="global")
    result_path = input_root / "result.json"
    summary_path = input_root / "summary.md"
    marker_path = input_root / ".complete"
    result, result_raw, result_sha, _ = _strict_object(result_path, "matrix aggregate result")
    if runner._is_link(summary_path) or not summary_path.is_file() or runner._is_link(marker_path) or not marker_path.is_file():
        raise AnalysisGlobalFailure("matrix aggregate summary or marker is missing")
    summary_raw = summary_path.read_bytes()
    marker, marker_raw, _marker_sha, _marker_canonical = _strict_object(marker_path, "matrix completion marker")
    if set(marker) != {"marker_type", "schema_version", "result_sha256", "summary_sha256"} or marker.get("marker_type") != runner.COMPLETION_MARKER_TYPE or marker.get("schema_version") != runner.SCHEMA_VERSION or marker.get("result_sha256") != result_sha or marker.get("summary_sha256") != _sha256(summary_raw):
        raise AnalysisGlobalFailure("matrix completion marker is invalid")
    try:
        validate(result, values["matrix_result_schema"])
    except ManifestValidationError as exc:
        raise AnalysisGlobalFailure(f"matrix aggregate result does not satisfy its schema: {exc}") from exc
    _verify_source_provenance(result, {key: value for key, value in sources.items() if not key.startswith("_")}, revision)
    runner._verify_aggregate_result(result, matrix_config)
    base = values["base_generator_config"]
    expected_files = {"result.json", "summary.md", ".complete"}
    seed_aggregates = [_Aggregate() for _ in matrix_config["seeds"]]
    slice_rows: dict[str, list[float]] = {}
    verified_cells = 0
    for cell in result["cells"]:
        if cell["status"] != "success":
            raise AnalysisGlobalFailure("analysis requires every matrix cell to be successful")
        evaluation, expected, cell_files = _verify_cell_and_collect(cell, matrix_config, base, repository, input_root, sources, values, revision)
        expected_files.update(f"configs/generator/{cell['cell_id']}.json" for _ in [0])
        expected_files.update(f"configs/evaluator/{cell['cell_id']}.json" for _ in [0])
        expected_files.update(cell_files)
        aggregate, slices = _cell_aggregate(evaluation, cell, matrix_config)
        seed_index = matrix_config["seeds"].index(cell["seed"])
        seed_aggregates[seed_index].add(aggregate)
        for key, row in slices["incident_slices"].items():
            target = slice_rows.setdefault(key, [0.0, 0.0, 0.0])
            for index in range(3):
                target[index] += row[index]
        verified_cells += 1
    actual_files = {relative for relative, kind in input_snapshot["inventory"] if kind == "file"}
    if actual_files != expected_files:
        raise AnalysisGlobalFailure(f"matrix artifact file inventory differs; missing={sorted(expected_files - actual_files)}, extra={sorted(actual_files - expected_files)}")
    runner._assert_inputs_unchanged(repository, sources, values, "analysis-inputs")
    after_snapshot = runner._tree_snapshot(input_root, "matrix artifact after analysis", containment_root=repository, failure_scope="global")
    if after_snapshot != input_snapshot:
        raise AnalysisGlobalFailure("matrix artifact changed during analysis")
    combined = _combine_aggregates(seed_aggregates)
    draws, draw_digest = bootstrap_draws()
    primary_values = _primary_values(combined)
    primary: dict[str, Any] = {}
    for metric in primary_values:
        point, ci = _bootstrap_metric(seed_aggregates, draws, metric)
        primary[metric] = {"numerator": {"overall_incident_precision": combined.precision_num, "machine_fault_recall": combined.machine_num, "sensor_fault_recall": combined.sensor_num, "clean_false_alerts_per_8_equipment_hours": combined.clean_alerts}.get(metric), "denominator": {"overall_incident_precision": combined.precision_den, "machine_fault_recall": combined.machine_den, "sensor_fault_recall": combined.sensor_den, "clean_false_alerts_per_8_equipment_hours": combined.clean_hours}.get(metric), "value": point, "ci": ci}
    availability: dict[str, Any] = {}
    for signal, pair in sorted(combined.availability.items()):
        value = _ratio(pair[0], pair[1])
        availability[signal] = {"available_points": pair[0], "total_points": pair[1], "availability_ratio": value}
    gates: dict[str, Any] = {}
    for metric in ("overall_incident_precision", "machine_fault_recall", "sensor_fault_recall", "clean_false_alerts_per_8_equipment_hours"):
        gates[metric] = {"status": _gate_status(primary[metric]["value"], primary[metric]["ci"], PROMOTION_THRESHOLDS[metric]), "point": primary[metric]["value"], "ci_lower": primary[metric]["ci"]["lower"], "ci_upper": primary[metric]["ci"]["upper"], "threshold": PROMOTION_THRESHOLDS[metric]}
    gates["signal_availability"] = {"status": "pass" if availability and all(item["availability_ratio"] is not None and item["availability_ratio"] >= 0.95 for item in availability.values()) else "fail", "minimum": PROMOTION_THRESHOLDS["signal_availability"]["minimum"], "signals": availability}
    gate_statuses = [item["status"] for item in gates.values()]
    performance_status = "fail" if "fail" in gate_statuses else ("inconclusive" if "inconclusive" in gate_statuses else "pass")
    result_out: dict[str, Any] = {
        "schema_version": ANALYSIS_SCHEMA_VERSION,
        "result_type": ANALYSIS_RESULT_TYPE,
        "analysis_id": ANALYSIS_ID,
        "matrix_id": EXPECTED_MATRIX_ID,
        "status": performance_status,
        "run_status": "complete",
        "engineering_status": "pass" if verified_cells == 120 and result["engineering_status"] == "pass" else "fail",
        "performance_status": performance_status,
        "provenance": {
            "canonicalization": CANONICALIZATION_ID,
            "inputs": {"analysis_config": {"path": analysis_source["path"], "raw_sha256": analysis_source["raw_sha256"], "canonical_sha256": analysis_source["canonical_sha256"]}, "analysis_schema": {"path": analysis_schema_source["path"], "raw_sha256": analysis_schema_source["raw_sha256"], "canonical_sha256": analysis_schema_source["canonical_sha256"]}, "matrix_artifact": {"path": analysis_config["input_root"], "inventory_sha256": _sha256(_canonical_json(input_snapshot))}, "matrix_sources": {key: {"path": value["path"], "raw_sha256": value["raw_sha256"], "canonical_sha256": value["canonical_sha256"]} for key, value in sources.items() if not key.startswith("_")}},
            "code_revision": revision,
            "bootstrap_algorithm_id": BOOTSTRAP_ALGORITHM_ID,
            "bootstrap_draw_digest": draw_digest,
        },
        "counts": {"cells_verified": verified_cells, "seeds": len(seed_aggregates), "layouts_per_seed": BOOTSTRAP_LAYOUTS_PER_CLUSTER, "events_per_seed": BOOTSTRAP_EVENTS_PER_CLUSTER, "bootstrap_resamples": BOOTSTRAP_RESAMPLES, "bootstrap_clusters": BOOTSTRAP_CLUSTER_COUNT},
        "estimates": {"primary": primary, "availability_by_signal": availability, "incident_slices": _mode_slice_records(slice_rows)},
        "bootstrap": {"algorithm_id": BOOTSTRAP_ALGORITHM_ID, "seed": BOOTSTRAP_SEED, "resamples": BOOTSTRAP_RESAMPLES, "cluster_count": BOOTSTRAP_CLUSTER_COUNT, "layouts_per_cluster": BOOTSTRAP_LAYOUTS_PER_CLUSTER, "events_per_cluster": BOOTSTRAP_EVENTS_PER_CLUSTER, "confidence_level": BOOTSTRAP_CONFIDENCE_LEVEL, "percentile_method": "linear_interpolation_n_minus_1", "draw_digest": draw_digest, "undefined_replicates": {key: value["ci"]["undefined_replicates"] for key, value in primary.items()}},
        "promotion_gates": gates,
        "limitations": ["seed clusterをreplacementありで再標本化し、seed内layout/eventを再標本化しない。", "suppressed event-window alertsはpositiveまたはcleanへ再分類しない。", "detection delayのみを保存し、lead timeは算出しない。", "customer data、weights、checkpoint、network、control write、Banto Hub writeは使用しない。"],
    }
    try:
        result_schema_path = anomaly_matrix._safe_repo_path(repository, ANALYSIS_RESULT_SCHEMA_PATH, "analysis result schema", must_exist=True)
        result_schema, _raw, _raw_sha, result_schema_canonical_sha = _strict_object(result_schema_path, "analysis result schema")
        if EXPECTED_ANALYSIS_RESULT_SCHEMA_CANONICAL_SHA256 and result_schema_canonical_sha != EXPECTED_ANALYSIS_RESULT_SCHEMA_CANONICAL_SHA256:
            raise AnalysisGlobalFailure("analysis result schema canonical SHA-256 pin is invalid")
        validate(result_out, result_schema)
    except ManifestValidationError as exc:
        raise AnalysisGlobalFailure(f"analysis result does not satisfy its schema: {exc}") from exc
    output_root = anomaly_matrix._safe_repo_path(repository, analysis_config["output_root"], "analysis output root", must_exist=False)
    return _publish_analysis(repository, output_root, result_out, lambda: (validate(result_out, result_schema), runner._assert_inputs_unchanged(repository, sources, values, "analysis-before-marker"), runner._require_revision(repository, revision, "analysis-before-marker")))


def _text_summary(summary: Mapping[str, Any]) -> str:
    return f"anomaly matrix analysis: {summary['status']}\nrun_status: {summary['run_status']}\nperformance_status: {summary['performance_status']}\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="analyze_anomaly_matrix")
    parser.add_argument("--config", default=ANALYSIS_CONFIG_PATH)
    parser.add_argument("--root")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root).absolute() if args.root else None
    try:
        if args.validate_only:
            summary = validate_analysis_config(args.config, root)
            print(_text_summary(summary))
        else:
            print(analyze_anomaly_matrix(args.config, root))
    except (AnomalyMatrixAnalysisError, ManifestValidationError, OSError, KeyError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
