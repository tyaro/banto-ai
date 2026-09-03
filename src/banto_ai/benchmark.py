"""外部依存ゼロの chronological rolling-origin benchmark runner。"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
import tempfile
import time
import tracemalloc
from datetime import datetime
from pathlib import Path, PureWindowsPath
from typing import Any, Callable, Mapping

from .baselines import BaselineError, build_baseline
from .contracts import Forecaster
from .manifest import ManifestValidationError, load_json, validate
from .metrics import MetricError, interval_coverage, interval_width, mae, mase, rmse, weighted_interval_score
from .quality import check_dataset
from .runtime import process_peak_memory_bytes
from .types import ForecastRequest, ForecastResult, ForecastSeriesResult, QualityStatus, SignalMetadata, SignalPoint, TimeSeries


class BenchmarkError(ValueError):
    """benchmark設定、データ、または評価に失敗した。"""


class ModelInvocationError(BenchmarkError):
    """注入されたmodelのforecast呼び出しだけを隔離する。"""


ModelFactory = Callable[[str, dict[str, Any]], Forecaster]


class ModelRegistry:
    """モデル名からForecaster生成処理への明示的な注入境界。"""

    _BASELINE_NAMES = frozenset({
        "last-value", "seasonal-naive", "moving-average", "ewma",
        "holt-linear", "linear-regression-covariates",
    })

    def __init__(self, factories: Mapping[str, ModelFactory] | None = None) -> None:
        self._factories: dict[str, ModelFactory] = {
            name: (lambda _equipment_id, parameters, model_name=name: build_baseline(model_name, parameters))
            for name in self._BASELINE_NAMES
        }
        if factories:
            for name, factory in factories.items():
                if not isinstance(name, str) or not name or not callable(factory):
                    raise BenchmarkError("model registry entries must be named callables")
                self._factories[name] = factory

    def has(self, name: str) -> bool:
        return name in self._factories

    def build(self, name: str, equipment_id: str, parameters: dict[str, Any]) -> Forecaster:
        try:
            factory = self._factories[name]
        except KeyError as exc:
            raise BenchmarkError(f"no model factory is registered for {name}") from exc
        return factory(equipment_id, dict(parameters))


def _finite_json(value: Any) -> Any:
    if isinstance(value, float) and not (value == value and abs(value) != float("inf")):
        raise BenchmarkError("non-finite output is forbidden")
    if isinstance(value, dict):
        return {str(k): _finite_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_finite_json(v) for v in value]
    return value


def _quantile(values: list[float], q: float) -> float:
    if not values:
        raise BenchmarkError("cannot calibrate quantile from empty validation residuals")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = (len(ordered) - 1) * q
    low, high = int(index), min(len(ordered) - 1, int(index) + 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (index - low)


def _validate_config(config: dict[str, Any], root: Path, registry: ModelRegistry | None = None) -> None:
    configured_models = config.get("models")
    if isinstance(configured_models, list) and any(
        isinstance(model, dict) and model.get("name") == "autoets"
        for model in configured_models
    ):
        raise BenchmarkError(
            "autoets is not implemented and is intentionally rejected; use holt-linear"
        )
    schema = load_json(root / "schemas" / "benchmark-run-config.schema.json")
    try:
        validate(config, schema)
    except ManifestValidationError as exc:
        raise BenchmarkError(str(exc)) from exc
    for key in ("dataset_path", "output_dir"):
        path = str(config[key])
        if Path(path).is_absolute() or PureWindowsPath(path).drive or "\\" in path or any(part == ".." for part in Path(path).parts):
            raise BenchmarkError(f"{key} must be repository-relative POSIX path")
    quantiles = config["quantiles"]
    if quantiles != sorted(set(quantiles)):
        raise BenchmarkError("quantiles must be sorted and unique")
    if 0.5 not in quantiles or any(quantile != 0.5 and not any(abs(candidate - (1.0 - quantile)) <= 1e-12 for candidate in quantiles) for quantile in quantiles):
        raise BenchmarkError("quantiles must contain 0.5 and symmetric central-interval pairs")
    for key in ("past_only_covariate_ids", "known_future_covariate_ids"):
        values = config.get(key, [])
        if len(values) != len(set(values)):
            raise BenchmarkError(f"{key} must contain unique IDs")
    if set(config.get("past_only_covariate_ids", [])) & set(config.get("known_future_covariate_ids", [])):
        raise BenchmarkError("a covariate cannot be both past-only and known-future")
    names = [model["name"] for model in config["models"]]
    if len(names) != len(set(names)):
        raise BenchmarkError("duplicate model name is forbidden")
    for key in ("target_signal_ids", "equipment_ids"):
        values = config.get(key)
        if values is not None and len(values) != len(set(values)):
            raise BenchmarkError(f"{key} must contain unique IDs")
    target_ids = config.get("target_signal_ids")
    if target_ids is not None:
        target_keys = [str(value).rsplit(".", 1)[-1] for value in target_ids]
        if len(target_keys) != len(set(target_keys)):
            raise BenchmarkError("target_signal_ids must contain unique logical target keys")
    registry = registry or ModelRegistry()
    for model in config["models"]:
        if not registry.has(model["name"]):
            raise BenchmarkError(f"no model factory is registered for {model['name']}")
        if model["name"] in ModelRegistry._BASELINE_NAMES:
            try:
                build_baseline(model["name"], dict(model.get("parameters", {})))
            except BaselineError as exc:
                raise BenchmarkError(str(exc)) from exc
    if not (root / config["dataset_path"]).is_dir():
        raise BenchmarkError("dataset_path does not exist")


def _repo_path(root: Path, relative: str, label: str) -> Path:
    if Path(relative).is_absolute() or PureWindowsPath(relative).drive or "\\" in relative or any(part == ".." for part in Path(relative).parts):
        raise BenchmarkError(f"{label} must be a repository-relative POSIX path")
    resolved = (root / relative).resolve()
    if resolved == root or root not in resolved.parents:
        raise BenchmarkError(f"{label} must remain inside repository")
    return resolved


def _revision(root: Path) -> dict[str, Any]:
    try:
        head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
        diff = subprocess.check_output(["git", "-C", str(root), "diff", "--binary", "HEAD"], stderr=subprocess.DEVNULL)
        status = subprocess.check_output(["git", "-C", str(root), "status", "--porcelain"], text=True, stderr=subprocess.DEVNULL)
        return {"status": "git", "head": head, "dirty": bool(status), "diff_sha256": hashlib.sha256(diff + status.encode("utf-8")).hexdigest()}
    except (OSError, subprocess.SubprocessError):
        return {"status": "git-unavailable", "head": None, "dirty": None, "diff_sha256": None}


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    lower, upper = int(index), min(len(ordered) - 1, int(index) + 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


PREDICTION_KEYS = frozenset({"model", "equipment_id", "target_signal_id", "operating_mode", "split", "origin_timestamp", "timestamp", "lead_time", "actual", "point_forecast", "quantiles"})


def _model_state_bytes(models: list[dict[str, Any]]) -> dict[str, int]:
    sizes: dict[str, int] = {}
    for model in models:
        serialized = json.dumps(
            {
                "model_name": model["name"],
                "parameters": model.get("parameters", {}),
                "learned_state": {},
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        sizes[model["name"]] = len(serialized)
    return sizes


def _split_indices_for_rows(
    rows: list[dict[str, Any]],
    chronological: dict[str, Any],
    equipment_id: str,
) -> dict[str, tuple[int, int]]:
    row_times = [datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00")) for row in rows]
    boundaries: dict[str, tuple[int, int]] = {}
    for item in chronological["splits"]:
        start = datetime.fromisoformat(item["start_timestamp"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(item["end_timestamp"].replace("Z", "+00:00"))
        starts = [index for index, value in enumerate(row_times) if value == start]
        ends = [index for index, value in enumerate(row_times) if value >= end]
        if not ends and row_times and end > row_times[-1]:
            ends = [len(row_times)]
        if not starts or not ends or starts[0] >= ends[0]:
            raise BenchmarkError(f"split boundary does not align to equipment timestamps: {equipment_id}/{item['split_id']}")
        boundaries[item["split_id"]] = (starts[0], ends[0])
    return boundaries


def _validate_prediction(row: dict[str, Any], quantiles: tuple[float, ...]) -> None:
    if (
        set(row) != PREDICTION_KEYS
        or row["split"] != "test"
        or not isinstance(row["lead_time"], int)
        or row["lead_time"] <= 0
    ):
        raise BenchmarkError("prediction row keys or split metadata are invalid")
    if not isinstance(row["quantiles"], dict) or list(row["quantiles"]) != [str(q) for q in quantiles]:
        raise BenchmarkError("prediction quantile keys are not ordered as configured")
    values = [row["actual"], row["point_forecast"], *row["quantiles"].values()]
    if any(
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not (value == value and abs(value) != float("inf"))
        for value in values
    ):
        raise BenchmarkError("prediction values must be finite numbers")
    ordered = [row["quantiles"][str(q)] for q in quantiles]
    if any(left > right for left, right in zip(ordered, ordered[1:])):
        raise BenchmarkError("prediction quantile crossing detected")


def _aggregate_predictions(
    items: list[dict[str, Any]],
    quantiles: tuple[float, ...],
    train_scales: dict[tuple[str, str], tuple[float, ...]],
) -> dict[str, float | int | str]:
    if not items:
        raise BenchmarkError("cannot aggregate zero prediction points")
    for item in items:
        _validate_prediction(item, quantiles)
    actual = tuple(float(item["actual"]) for item in items)
    predicted = tuple(float(item["point_forecast"]) for item in items)
    quantile_forecasts = {
        quantile: tuple(float(item["quantiles"][str(quantile)]) for item in items)
        for quantile in quantiles
    }
    lower_q, upper_q = min(quantiles), max(quantiles)
    result: dict[str, float | int | str] = {
        "count": len(items),
        "mae": mae(actual, predicted),
        "rmse": rmse(actual, predicted),
        "wis": weighted_interval_score(actual, quantile_forecasts),
        "nominal_interval_coverage": interval_coverage(
            actual,
            quantile_forecasts[lower_q],
            quantile_forecasts[upper_q],
        ),
        "interval_width": interval_width(
            quantile_forecasts[lower_q],
            quantile_forecasts[upper_q],
        ),
    }
    try:
        normalized_errors = [mase((float(item["actual"]),), (float(item["point_forecast"]),), train_scales[(item["equipment_id"], item["target_signal_id"])]) for item in items]
        result["mase"] = sum(normalized_errors) / len(normalized_errors)
    except (KeyError, MetricError) as exc:
        result["mase_status"] = "inconclusive: " + str(exc)
    return result


def _dimension_metrics(
    predictions: list[dict[str, Any]],
    quantiles: tuple[float, ...],
    train_scales: dict[tuple[str, str], tuple[float, ...]],
    model_names: tuple[str, ...],
    equipment_ids: tuple[str, ...],
    target_pairs_by_equipment: dict[str, tuple[tuple[str, str], ...]],
    target_units: dict[tuple[str, str], str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build deterministic target and equipment-target metrics from test rows only."""
    target_order = tuple(
        dict.fromkeys(
            target_key
            for equipment_id in equipment_ids
            for _, target_key in target_pairs_by_equipment[equipment_id]
        )
    )
    by_model_target: list[dict[str, Any]] = []
    by_model_equipment_target: list[dict[str, Any]] = []

    for model_name in model_names:
        for target_key in target_order:
            matching = [
                item for item in predictions
                if item["model"] == model_name
                and item["target_signal_id"].rsplit(".", 1)[-1] == target_key
            ]
            if not matching:
                continue
            units = {
                target_units[(item["equipment_id"], item["target_signal_id"])]
                for item in matching
            }
            if len(units) != 1:
                raise BenchmarkError(
                    f"cannot aggregate mixed units for {model_name}/{target_key}"
                )
            by_model_target.append({
                "model": model_name,
                "target_signal_key": target_key,
                "unit": next(iter(units)),
                "metrics": _aggregate_predictions(matching, quantiles, train_scales),
            })

        for equipment_id in equipment_ids:
            for target_id, _ in target_pairs_by_equipment[equipment_id]:
                matching = [
                    item for item in predictions
                    if item["model"] == model_name
                    and item["equipment_id"] == equipment_id
                    and item["target_signal_id"] == target_id
                ]
                if not matching:
                    continue
                by_model_equipment_target.append({
                    "model": model_name,
                    "equipment_id": equipment_id,
                    "target_signal_id": target_id,
                    "unit": target_units[(equipment_id, target_id)],
                    "metrics": _aggregate_predictions(matching, quantiles, train_scales),
                })
    return by_model_target, by_model_equipment_target


def _select_origins(start: int, end: int, context_length: int, horizon: int, split_name: str, config: dict[str, Any]) -> tuple[int, ...]:
    stride = int(config.get(f"{split_name}_origin_stride", 1 if split_name == "validation" else horizon))
    maximum = config.get(f"max_{split_name}_origins")
    candidates = tuple(range(max(context_length, start), end - horizon + 1, stride))
    if maximum is None or len(candidates) <= maximum:
        return candidates
    if maximum <= 0:
        raise BenchmarkError(f"max_{split_name}_origins must be positive")
    if maximum == 1:
        return (candidates[0],)
    selected = tuple(candidates[round(index * (len(candidates) - 1) / (maximum - 1))] for index in range(maximum))
    return tuple(dict.fromkeys(selected))


def _make_request(
    rows: list[dict[str, Any]],
    signals: dict[str, dict[str, Any]],
    target_ids: tuple[str, ...],
    origin: int,
    context_length: int,
    horizon: int,
    quantiles: tuple[float, ...] = (),
    past_only_ids: tuple[str, ...] = (),
    known_future_ids: tuple[str, ...] = (),
) -> ForecastRequest:
    """origin直前のpast-onlyとorigin+horizonまでのknown-futureを分離して組み立てる。"""
    if set(target_ids) & (set(past_only_ids) | set(known_future_ids)):
        raise BenchmarkError("target cannot also be a covariate")
    if set(past_only_ids) & set(known_future_ids):
        raise BenchmarkError("covariate cannot be both past-only and known-future")

    def series(signal_id: str, begin: int, upto: int) -> TimeSeries:
        metadata = signals[signal_id]
        key = signal_id.rsplit(".", 1)[-1]
        points = tuple(
            SignalPoint(
                datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00")),
                row["signals"][key]["value"],
                QualityStatus(row["quality"][key]),
            )
            for row in rows[begin:upto]
        )
        return TimeSeries(
            SignalMetadata(
                signal_id,
                metadata["name"],
                metadata["unit"],
                metadata["sampling_interval_ms"],
                metadata["role"],
            ),
            points,
        )

    if origin < context_length:
        raise BenchmarkError("origin must have the complete configured context")
    if origin + horizon > len(rows):
        raise BenchmarkError("forecast horizon exceeds available observation rows")
    begin = origin - context_length
    context_ids = tuple(dict.fromkeys((*target_ids, *past_only_ids, *known_future_ids)))
    contexts = tuple(series(signal_id, begin, origin) for signal_id in context_ids)
    future = tuple(series(signal_id, begin, origin + horizon) for signal_id in known_future_ids)
    return ForecastRequest(contexts, target_ids, horizon, quantiles=quantiles, known_future_covariates=future)


def _forecast_map(
    result: ForecastResult,
    target_ids: tuple[str, ...],
    rows: list[dict[str, Any]],
    origin: int,
    horizon: int,
    quantiles: tuple[float, ...],
    policy: str,
) -> dict[str, ForecastSeriesResult]:
    if not isinstance(result, ForecastResult):
        raise BenchmarkError("model must return ForecastResult")
    expected_timestamps = tuple(
        datetime.fromisoformat(
            rows[origin + lead]["timestamp"].replace("Z", "+00:00")
        )
        for lead in range(horizon)
    )
    actual_ids = tuple(item.signal_id for item in result.forecasts)
    if set(actual_ids) != set(target_ids) or len(actual_ids) != len(target_ids):
        raise BenchmarkError("forecast target IDs do not match request")
    by_id = {item.signal_id: item for item in result.forecasts}
    mapped: dict[str, ForecastSeriesResult] = {}
    for target_id in target_ids:
        forecast = by_id[target_id]
        if (
            len(forecast.point_forecast) != horizon
            or len(forecast.timestamps) != horizon
            or tuple(forecast.timestamps) != expected_timestamps
        ):
            raise BenchmarkError("forecast horizon or timestamps do not match requested window")
        levels = tuple(item.quantile for item in forecast.quantile_forecasts)
        if policy == "native":
            if levels != quantiles:
                raise BenchmarkError("native forecast quantile levels do not match configured quantiles")
            median = next(item for item in forecast.quantile_forecasts if item.quantile == 0.5)
            for point, median_value in zip(forecast.point_forecast, median.values):
                tolerance = 1e-5 * max(1.0, abs(float(point)), abs(float(median_value)))
                if abs(float(point) - float(median_value)) > tolerance:
                    raise BenchmarkError("native point forecast is inconsistent with p50")
        mapped[target_id] = forecast
    return mapped


def _invoke_forecast(model: Forecaster, request: ForecastRequest) -> ForecastResult:
    """外部model実装の例外を、呼び出し境界でだけrunner failureへ変換する。"""
    try:
        return model.forecast(request)
    except Exception as exc:
        raise ModelInvocationError(str(exc)) from exc


def _policy(model_cfg: dict[str, Any]) -> str:
    explicit = model_cfg.get("quantile_policy")
    if explicit:
        return str(explicit)
    return "native" if model_cfg["name"] == "timesfm3" else "validation-residual-by-lead"


def run_benchmark(config_path: Path, root: Path, model_registry: ModelRegistry | None = None) -> Path:
    config = load_json(config_path)
    if not isinstance(config, dict):
        raise BenchmarkError("benchmark config must be an object")
    registry = model_registry or ModelRegistry()
    _validate_config(config, root, registry)
    root = root.resolve()
    dataset_dir = _repo_path(root, config["dataset_path"], "dataset_path")
    output_dir = _repo_path(root, config["output_dir"], "output_dir")
    if output_dir == dataset_dir or dataset_dir in output_dir.parents or output_dir in dataset_dir.parents:
        raise BenchmarkError("output_dir must be separate from dataset_dir and neither an ancestor nor descendant")
    if output_dir.exists():
        raise BenchmarkError(f"refusing to overwrite existing output: {output_dir}")
    quality = check_dataset(dataset_dir, root)
    manifest = load_json(dataset_dir / "dataset-manifest.json")
    fingerprint_path = (dataset_dir / manifest["fingerprint_path"]).resolve()
    if fingerprint_path.parent != dataset_dir.resolve():
        raise BenchmarkError("fingerprint path must point directly inside dataset directory")
    fingerprint = load_json(fingerprint_path)
    dataset_fingerprint = fingerprint.get("dataset_fingerprint")
    if not isinstance(dataset_fingerprint, str) or len(dataset_fingerprint) != 64 or any(c not in "0123456789abcdef" for c in dataset_fingerprint):
        raise BenchmarkError("verified dataset fingerprint is missing or invalid")
    observations = [json.loads(line) for line in (dataset_dir / manifest["data_path"]).read_text(encoding="utf-8").splitlines()]
    by_equipment: dict[str, list[dict[str, Any]]] = {}
    for row in observations:
        by_equipment.setdefault(row["equipment_id"], []).append(row)
    for rows in by_equipment.values():
        rows.sort(key=lambda row: row["timestamp"])
    split_manifest = load_json(dataset_dir / manifest["split_manifest_path"])
    chronological = next((item for item in split_manifest["strategies"] if item["strategy"] == "chronological"), None)
    if chronological is None or [item["split_id"] for item in chronological["splits"]] != ["train", "validation", "test"]:
        raise BenchmarkError("split manifest must provide chronological train/validation/test")
    split_indices: dict[str, dict[str, tuple[int, int]]] = {equipment_id: _split_indices_for_rows(rows, chronological, equipment_id) for equipment_id, rows in by_equipment.items()}
    signals = {item["signal_id"]: item for item in manifest["signals"]}
    equipment_ids = tuple(config.get("equipment_ids") or by_equipment.keys())
    configured_targets = config.get("target_signal_ids")
    horizon = config["horizon"]
    context_length = config["context_length"]
    q_values = tuple(float(q) for q in config["quantiles"])
    predictions: list[dict[str, Any]] = []
    records: dict[str, list[dict[str, Any]]] = {}
    train_scales: dict[tuple[str, str], tuple[float, ...]] = {}
    residuals: dict[tuple[str, str, str], dict[int, list[float]]] = {}
    failures: list[dict[str, Any]] = []
    failure_keys: set[tuple[str, str, str]] = set()
    failed_keys: set[tuple[str, str, str]] = set()
    validation_start_time = time.perf_counter()
    test_latencies: list[float] = []
    test_latencies_by_model: dict[str, list[float]] = {
        model["name"]: [] for model in config["models"]
    }
    tracemalloc.start()
    start_time = time.perf_counter()

    def resolve_signal(equipment_id: str, requested: str) -> tuple[str, str]:
        key = requested.rsplit(".", 1)[-1]
        is_full_id = requested in signals or "." in requested
        if is_full_id:
            if len(equipment_ids) > 1:
                raise BenchmarkError(
                    f"full signal ID '{requested}' is not allowed for multiple equipment; "
                    f"use short ID '{key}'"
                )
            if not requested.startswith(f"{equipment_id}."):
                owner = next(
                    (
                        candidate
                        for candidate in equipment_ids
                        if requested.startswith(f"{candidate}.")
                    ),
                    "unknown",
                )
                raise BenchmarkError(
                    f"signal ID '{requested}' belongs to equipment '{owner}', "
                    f"not target equipment '{equipment_id}'"
                )
            full = requested
        else:
            full = f"{equipment_id}.{key}"
        if full not in signals:
            raise BenchmarkError(f"unknown signal for equipment '{equipment_id}': {requested}")
        return full, key

    targets_by_equipment: dict[str, tuple[tuple[str, str], ...]] = {}
    covariates_by_equipment: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {}
    target_units: dict[tuple[str, str], str] = {}
    units_by_target_key: dict[str, set[str]] = {}
    for equipment_id in equipment_ids:
        if equipment_id not in by_equipment:
            raise BenchmarkError(f"unknown equipment: {equipment_id}")
        if configured_targets is None:
            target_requests = tuple(
                item["signal_id"].rsplit(".", 1)[-1]
                for item in manifest["signals"]
                if item["role"] == "target"
                and item["signal_id"].startswith(f"{equipment_id}.")
            )
        else:
            target_requests = tuple(str(item) for item in configured_targets)
        targets_by_equipment[equipment_id] = tuple(
            resolve_signal(equipment_id, item) for item in target_requests
        )
        target_keys = [target_key for _, target_key in targets_by_equipment[equipment_id]]
        if not target_keys:
            raise BenchmarkError(f"no target signals configured for equipment '{equipment_id}'")
        if len(target_keys) != len(set(target_keys)):
            raise BenchmarkError(
                f"duplicate logical target key resolved for equipment '{equipment_id}'"
            )
        for target_id, target_key in targets_by_equipment[equipment_id]:
            unit = signals[target_id]["unit"]
            target_units[(equipment_id, target_id)] = unit
            units_by_target_key.setdefault(target_key, set()).add(unit)
        past = tuple(resolve_signal(equipment_id, str(item))[0] for item in config.get("past_only_covariate_ids", ()))
        known = tuple(resolve_signal(equipment_id, str(item))[0] for item in config.get("known_future_covariate_ids", ()))
        if not config.get("past_only_covariate_ids") and not config.get("known_future_covariate_ids"):
            legacy = tuple(resolve_signal(equipment_id, str(item))[0] for model in config["models"] if model["name"] == "linear-regression-covariates" for item in model.get("parameters", {}).get("covariate_ids", ()))
            known = tuple(dict.fromkeys(legacy))
        covariates_by_equipment[equipment_id] = (past, known)
        train_start, train_end = split_indices[equipment_id]["train"]
        for target, target_key in targets_by_equipment[equipment_id]:
            train_scales[(equipment_id, target)] = tuple(float(row["signals"][target_key]["value"]) for row in by_equipment[equipment_id][train_start:train_end] if row["signals"][target_key]["value"] is not None)
    mixed_units = {key: sorted(units) for key, units in units_by_target_key.items() if len(units) > 1}
    if mixed_units:
        raise BenchmarkError(f"target units must match before aggregation: {mixed_units}")

    def record_failure(model_name: str, equipment_id: str, target: str, status: str, reason: str, split_name: str) -> None:
        failure_key = (equipment_id, target, model_name)
        if failure_key in failure_keys:
            return
        failure_keys.add(failure_key)
        failures.append({"model": model_name, "equipment_id": equipment_id, "target_signal_id": target, "status": status, "reason": reason, "split": split_name})

    model_instances: dict[tuple[str, str], Forecaster] = {}
    model_policies = {model["name"]: _policy(model) for model in config["models"]}
    for equipment_id in equipment_ids:
        for model_cfg in config["models"]:
            model_name = model_cfg["name"]
            try:
                parameters = dict(model_cfg.get("parameters", {}))
                if model_name == "linear-regression-covariates":
                    parameters["covariate_ids"] = list(covariates_by_equipment[equipment_id][1])
                model_instances[(equipment_id, model_name)] = registry.build(model_name, equipment_id, parameters)
            except Exception as exc:
                for target, _ in targets_by_equipment[equipment_id]:
                    record_failure(model_name, equipment_id, target, "failed", str(exc), "validation")
                    failed_keys.add((equipment_id, target, model_name))

    origin_selection: dict[str, dict[str, Any]] = {"validation": {}, "test": {}}
    for split_name in ("validation", "test"):
        for equipment_id in equipment_ids:
            start, end = split_indices[equipment_id][split_name]
            origins = _select_origins(start, end, context_length, horizon, split_name, config)
            if any(origin < start or origin < context_length or origin + horizon > end for origin in origins):
                raise BenchmarkError(
                    f"{split_name} origin must keep context+horizon inside its split: {equipment_id}"
                )
            origin_selection[split_name][equipment_id] = {"count": len(origins), "indices": list(origins), "stride": config.get(f"{split_name}_origin_stride", 1 if split_name == "validation" else horizon), "max_origins": config.get(f"max_{split_name}_origins"), "rule": "chronological range with configured stride; endpoint-inclusive uniform cap when max_origins is set"}

    for equipment_id in equipment_ids:
        rows = by_equipment[equipment_id]
        target_pairs = targets_by_equipment[equipment_id]
        past_ids, known_ids = covariates_by_equipment[equipment_id]
        origins = tuple(origin_selection["validation"][equipment_id]["indices"])
        for model_cfg in config["models"]:
            model_name = model_cfg["name"]
            model = model_instances.get((equipment_id, model_name))
            if model is None:
                continue
            policy = model_policies[model_name]
            for target, _ in target_pairs:
                residuals[(equipment_id, target, model_name)] = {lead: [] for lead in range(horizon)}
            for origin in origins:
                active_targets = tuple(
                    target for target, _ in target_pairs
                    if (equipment_id, target, model_name) not in failed_keys
                )
                if not active_targets:
                    break
                request = _make_request(
                    rows, signals, active_targets, origin, context_length, horizon,
                    q_values, past_ids, known_ids,
                )
                try:
                    model_result = _invoke_forecast(model, request)
                except ModelInvocationError as exc:
                    for target, _ in target_pairs:
                        if (equipment_id, target, model_name) not in failed_keys:
                            record_failure(model_name, equipment_id, target, "failed", str(exc), "validation")
                            failed_keys.add((equipment_id, target, model_name))
                    break
                forecast_map = _forecast_map(
                    model_result, active_targets, rows, origin, horizon, q_values, policy,
                )
                for target, target_key in target_pairs:
                    if target not in forecast_map or (equipment_id, target, model_name) in failed_keys:
                        continue
                    actual = tuple(
                        rows[origin + i]["signals"][target_key]["value"]
                        for i in range(horizon)
                    )
                    if any(value is None for value in actual):
                        continue
                    if policy == "validation-residual-by-lead":
                        forecast = forecast_map[target].point_forecast
                        for lead, (actual_value, predicted_value) in enumerate(zip(actual, forecast)):
                            residuals[(equipment_id, target, model_name)][lead].append(
                                float(actual_value) - float(predicted_value)
                            )
            if policy == "validation-residual-by-lead":
                for target, _ in target_pairs:
                    key = (equipment_id, target, model_name)
                    if key not in failed_keys and any(not residuals[key].get(lead) for lead in range(horizon)):
                        record_failure(model_name, equipment_id, target, "inconclusive", "validation residuals are empty for at least one lead", "validation")
                        failed_keys.add(key)

    validation_seconds = time.perf_counter() - validation_start_time
    test_start_time = time.perf_counter()
    for equipment_id in equipment_ids:
        rows = by_equipment[equipment_id]
        target_pairs = targets_by_equipment[equipment_id]
        past_ids, known_ids = covariates_by_equipment[equipment_id]
        origins = tuple(origin_selection["test"][equipment_id]["indices"])
        for model_cfg in config["models"]:
            model_name = model_cfg["name"]
            model = model_instances.get((equipment_id, model_name))
            if model is None:
                continue
            policy = model_policies[model_name]
            for origin in origins:
                active_targets = tuple(
                    target for target, _ in target_pairs
                    if (equipment_id, target, model_name) not in failed_keys
                )
                if not active_targets:
                    break
                request = _make_request(
                    rows, signals, active_targets, origin, context_length, horizon,
                    q_values, past_ids, known_ids,
                )
                call_start = time.perf_counter()
                try:
                    model_result = _invoke_forecast(model, request)
                except ModelInvocationError as exc:
                    for target, _ in target_pairs:
                        if (equipment_id, target, model_name) not in failed_keys:
                            record_failure(model_name, equipment_id, target, "failed", str(exc), "test")
                            failed_keys.add((equipment_id, target, model_name))
                    break
                forecast_map = _forecast_map(
                    model_result, active_targets, rows, origin, horizon, q_values, policy,
                )
                latency = time.perf_counter() - call_start
                test_latencies.append(latency)
                test_latencies_by_model[model_name].append(latency)
                for target, target_key in target_pairs:
                    key = (equipment_id, target, model_name)
                    if target not in forecast_map or key in failed_keys:
                        continue
                    actual = tuple(
                        rows[origin + i]["signals"][target_key]["value"]
                        for i in range(horizon)
                    )
                    if any(value is None for value in actual):
                        record_failure(model_name, equipment_id, target, "inconclusive", "test actual contains missing value", "test")
                        continue
                    forecast = forecast_map[target]
                    point_forecast = tuple(float(value) for value in forecast.point_forecast)
                    if policy == "native":
                        native = {item.quantile: item.values for item in forecast.quantile_forecasts}
                        calibrated = {
                            q: tuple(float(native[q][lead]) for lead in range(horizon))
                            for q in q_values
                        }
                    else:
                        residual = residuals[key]
                        calibrated = {
                            q: tuple(
                                point_forecast[lead] + _quantile(residual[lead], q)
                                for lead in range(horizon)
                            )
                            for q in q_values
                        }
                    actual_f = tuple(float(v) for v in actual)
                    for lead in range(horizon):
                        mode = rows[origin + lead]["operating_mode"]
                        slice_key = f"{model_name}|{target}|{equipment_id}|{mode}|{lead + 1}"
                        prediction = {
                            "model": model_name,
                            "equipment_id": equipment_id,
                            "target_signal_id": target,
                            "operating_mode": mode,
                            "split": "test",
                            "origin_timestamp": rows[origin]["timestamp"],
                            "timestamp": forecast.timestamps[lead].isoformat().replace("+00:00", "Z"),
                            "lead_time": lead + 1,
                            "actual": actual_f[lead],
                            "point_forecast": point_forecast[lead],
                            "quantiles": {str(q): calibrated[q][lead] for q in q_values},
                        }
                        _validate_prediction(prediction, q_values)
                        records.setdefault(slice_key, []).append(prediction)
                        predictions.append(prediction)

    test_seconds = time.perf_counter() - test_start_time
    if not predictions:
        tracemalloc.stop()
        raise BenchmarkError("all models failed or produced zero predictions")
    summary = {
        key: _aggregate_predictions(value, q_values, train_scales)
        for key, value in records.items()
    }
    by_model = {
        model_name: _aggregate_predictions(
            [item for item in predictions if item["model"] == model_name],
            q_values,
            train_scales,
        )
        for model_name in model_policies
        if any(item["model"] == model_name for item in predictions)
    }
    model_names = tuple(model["name"] for model in config["models"])
    by_model_target, by_model_equipment_target = _dimension_metrics(
        predictions,
        q_values,
        train_scales,
        model_names,
        equipment_ids,
        targets_by_equipment,
        target_units,
    )
    overall = _aggregate_predictions(predictions, q_values, train_scales)
    elapsed = time.perf_counter() - start_time
    _, tracemalloc_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    process_peak, memory_source = process_peak_memory_bytes()
    if process_peak is None:
        peak_memory = tracemalloc_peak
        memory_source = "tracemalloc.fallback"
    else:
        peak_memory = process_peak
    temp_parent = output_dir.parent
    temp_parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{config['run_id']}.", dir=temp_parent))
    try:
        with (temporary / "predictions.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
            for row in predictions:
                _validate_prediction(row, q_values)
                handle.write(json.dumps(_finite_json(row), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
        split_provenance = {equipment_id: {split_name: {"start_index": bounds[0], "end_index": bounds[1]} for split_name, bounds in split_indices[equipment_id].items()} for equipment_id in equipment_ids}
        latency_by_model = {
            model_name: {
                "call_count": len(latencies),
                "p50_ms": _percentile([value * 1000 for value in latencies], 0.50),
                "p95_ms": _percentile([value * 1000 for value in latencies], 0.95),
            }
            for model_name, latencies in test_latencies_by_model.items()
        }
        result = _finite_json({
            "schema_version": "0.2",
            "result_type": "benchmark",
            "run_id": config["run_id"],
            "status": "partial" if failures else "success",
            "dataset_fingerprint": dataset_fingerprint,
            "generator_version": manifest.get("generator_version"),
            "run_config": config,
            "code_revision": _revision(root),
            "seed": config.get("seed"),
            "model_parameters": {
                item["name"]: item.get("parameters", {}) for item in config["models"]
            },
            "prediction_count": len(predictions),
            "failures": failures,
            "metrics": {
                "aggregate": overall,
                "by_model": by_model,
                "slices": summary,
                "by_model_target": by_model_target,
                "by_model_equipment_target": by_model_equipment_target,
            },
            "runtime": {
                "validation_seconds": validation_seconds,
                "test_seconds": test_seconds,
                "total_seconds": elapsed,
                "p50_latency_ms": _percentile([value * 1000 for value in test_latencies], 0.50),
                "p95_latency_ms": _percentile([value * 1000 for value in test_latencies], 0.95),
                "latency_by_model": latency_by_model,
                "peak_memory_bytes": peak_memory,
                "memory_source": memory_source,
                "model_state_bytes": _model_state_bytes(config["models"]),
                "output_size_bytes_excluding_result": 0,
                "os": platform.platform(),
                "python": sys.version,
                "cpu": platform.processor(),
                "calibration_source": "model別policy",
                "quantile_policy_by_model": model_policies,
            },
            "provenance": {
                "quality_gate": quality,
                "split": split_provenance,
                "origin_selection": origin_selection,
                "quantile_calibration": "model別policy: nativeまたはvalidation residual by lead",
                "quantile_policy_by_model": model_policies,
            },
        })
        model_lines = "\n".join(
            f"- `{model_name}`: {value}" for model_name, value in by_model.items()
        )
        def table(headers: tuple[str, ...], rows: list[dict[str, Any]]) -> str:
            lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
            for row in rows:
                values = [
                    str(row[key]) if key != "metrics" else json.dumps(row[key], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                    for key in headers
                ]
                lines.append("| " + " | ".join(values) + " |")
            return "\n".join(lines)

        markdown = "# Benchmark結果\n\n合成データの結果であり、実設備の性能を示しません。\n\n## 概要\n\n- 結果schema: `0.2`（`aggregate`は互換表示、判定はdimension別metricsを使用）\n- データ品質gate: 合格\n- 予測件数: %d\n- quantile policy: model別（nativeまたはvalidation residual by lead）\n- 失敗・評価不能: %d\n- aggregate（全model混在・互換表示）: %s\n\n## model別metrics\n\n%s\n\n## model-target別metrics\n\n%s\n\n## model-equipment-target別metrics\n\n%s\n\n## slice別\n\n%s\n" % (
            len(predictions), len(failures), overall, model_lines,
            table(("model", "target_signal_key", "unit", "metrics"), by_model_target),
            table(("model", "equipment_id", "target_signal_id", "unit", "metrics"), by_model_equipment_target),
            "\n".join(f"- `{key}`: {value}" for key, value in summary.items()),
        )
        (temporary / "summary.md").write_text(markdown, encoding="utf-8")
        state_size = sum(path.stat().st_size for path in temporary.iterdir() if path.is_file())
        result["runtime"]["output_size_bytes_excluding_result"] = state_size
        validate(result, load_json(root / "schemas" / "benchmark-result.schema.json"))
        (temporary / "result.json").write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        temporary.rename(output_dir)
    except Exception:
        for child in temporary.iterdir():
            if child.is_file():
                child.unlink()
        temporary.rmdir()
        raise
    return output_dir
