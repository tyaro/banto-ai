"""外部依存ゼロのchronological rolling-origin benchmark runner。"""

from __future__ import annotations

import json
import platform
import subprocess
import sys
import tempfile
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any

from .baselines import BaselineError, build_baseline
from .manifest import ManifestValidationError, load_json, validate
from .metrics import MetricError, interval_coverage, interval_width, mae, mase, rmse, weighted_interval_score
from .quality import check_dataset
from .types import ForecastRequest, QualityStatus, SignalMetadata, SignalPoint, TimeSeries


class BenchmarkError(ValueError):
    """benchmark設定、データ、または評価に失敗した。"""


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


def _validate_config(config: dict[str, Any], root: Path) -> None:
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
    names = [model["name"] for model in config["models"]]
    if len(names) != len(set(names)):
        raise BenchmarkError("duplicate model name is forbidden")
    for model in config["models"]:
        try:
            build_baseline(model["name"], model.get("parameters", {}))
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
        import hashlib
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
    """baselineのimmutable設定と空の学習stateをcanonical JSON化したbyte数。"""
    sizes: dict[str, int] = {}
    for model in models:
        serialized = json.dumps(
            {"model_name": model["name"], "parameters": model.get("parameters", {}), "learned_state": {}},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        sizes[model["name"]] = len(serialized)
    return sizes


def _split_indices_for_rows(rows: list[dict[str, Any]], chronological: dict[str, Any], equipment_id: str) -> dict[str, tuple[int, int]]:
    """manifestの[start,end) timestamp境界を、この設備の行indexへ解決する。"""
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
    if set(row) != PREDICTION_KEYS or row["split"] != "test" or not isinstance(row["lead_time"], int) or row["lead_time"] <= 0:
        raise BenchmarkError("prediction row keys or split metadata are invalid")
    if not isinstance(row["quantiles"], dict) or list(row["quantiles"]) != [str(q) for q in quantiles]:
        raise BenchmarkError("prediction quantile keys are not ordered as configured")
    values = [row["actual"], row["point_forecast"], *row["quantiles"].values()]
    if any(not isinstance(value, (int, float)) or isinstance(value, bool) or not (value == value and abs(value) != float("inf")) for value in values):
        raise BenchmarkError("prediction values must be finite numbers")
    ordered = [row["quantiles"][str(q)] for q in quantiles]
    if any(left > right for left, right in zip(ordered, ordered[1:])):
        raise BenchmarkError("prediction quantile crossing detected")


def _aggregate_predictions(
    items: list[dict[str, Any]],
    quantiles: tuple[float, ...],
    train_scales: dict[tuple[str, str], tuple[float, ...]],
) -> dict[str, float | int | str]:
    """raw prediction pointを同一重みで集計し、MASEだけ設備・target別train scaleを使う。"""
    if not items:
        raise BenchmarkError("cannot aggregate zero prediction points")
    for item in items:
        _validate_prediction(item, quantiles)
    actual = tuple(float(item["actual"]) for item in items)
    predicted = tuple(float(item["point_forecast"]) for item in items)
    quantile_forecasts = {quantile: tuple(float(item["quantiles"][str(quantile)]) for item in items) for quantile in quantiles}
    lower_q, upper_q = min(quantiles), max(quantiles)
    result: dict[str, float | int | str] = {
        "count": len(items),
        "mae": mae(actual, predicted),
        "rmse": rmse(actual, predicted),
        "wis": weighted_interval_score(actual, quantile_forecasts),
        "nominal_interval_coverage": interval_coverage(actual, quantile_forecasts[lower_q], quantile_forecasts[upper_q]),
        "interval_width": interval_width(quantile_forecasts[lower_q], quantile_forecasts[upper_q]),
    }
    try:
        normalized_errors = [
            mase(
                (float(item["actual"]),),
                (float(item["point_forecast"]),),
                train_scales[(item["equipment_id"], item["target_signal_id"])],
            )
            for item in items
        ]
        result["mase"] = sum(normalized_errors) / len(normalized_errors)
    except (KeyError, MetricError) as exc:
        result["mase_status"] = "inconclusive: " + str(exc)
    return result


def run_benchmark(config_path: Path, root: Path) -> Path:
    config = load_json(config_path)
    if not isinstance(config, dict):
        raise BenchmarkError("benchmark config must be an object")
    _validate_config(config, root)
    root = root.resolve()
    dataset_dir = _repo_path(root, config["dataset_path"], "dataset_path")
    output_dir = _repo_path(root, config["output_dir"], "output_dir")
    if output_dir == dataset_dir or dataset_dir in output_dir.parents or output_dir in dataset_dir.parents:
        raise BenchmarkError("output_dir must be separate from dataset_dir and neither an ancestor nor descendant")
    if output_dir.exists():
        raise BenchmarkError(f"refusing to overwrite existing output: {output_dir}")
    # これは全データ読込より前に必ず実行するgate。
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
    split_indices: dict[str, dict[str, tuple[int, int]]] = {}
    for equipment_id, rows in by_equipment.items():
        split_indices[equipment_id] = _split_indices_for_rows(rows, chronological, equipment_id)
    signals = {item["signal_id"]: item for item in manifest["signals"]}
    configured_targets = tuple(config.get("target_signal_ids") or [item["signal_id"] for item in manifest["signals"] if item["role"] == "target"])
    equipment_ids = tuple(config.get("equipment_ids") or by_equipment.keys())
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
    tracemalloc.start()
    start_time = time.perf_counter()

    def resolve_signal(equipment_id: str, requested: str) -> tuple[str, str]:
        key = requested.rsplit(".", 1)[-1]
        full = requested if requested in signals else f"{equipment_id}.{key}"
        if full not in signals:
            raise BenchmarkError(f"unknown signal for equipment: {requested}")
        return full, key

    def build_model(equipment_id: str, model_cfg: dict[str, Any]):
        parameters = dict(model_cfg.get("parameters", {}))
        if model_cfg["name"] == "linear-regression-covariates":
            parameters["covariate_ids"] = [resolve_signal(equipment_id, str(item))[0] for item in parameters["covariate_ids"]]
        return build_baseline(model_cfg["name"], parameters)

    def record_failure(model_name: str, equipment_id: str, target: str, status: str, reason: str, split_name: str) -> None:
        failure_key = (equipment_id, target, model_name)
        if failure_key in failure_keys:
            return
        failure_keys.add(failure_key)
        failures.append({"model": model_name, "equipment_id": equipment_id, "target_signal_id": target, "status": status, "reason": reason, "split": split_name})

    def make_request(rows: list[dict[str, Any]], equipment_id: str, target: str, origin: int, known_ids: tuple[str, ...] = ()) -> ForecastRequest:
        def series(signal_id: str, begin: int, upto: int) -> TimeSeries:
            metadata = signals[signal_id]
            key = signal_id.rsplit(".", 1)[-1]
            points = tuple(SignalPoint(datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00")), row["signals"][key]["value"], QualityStatus(row["quality"][key])) for row in rows[begin:upto])
            return TimeSeries(SignalMetadata(signal_id, metadata["name"], metadata["unit"], metadata["sampling_interval_ms"], metadata["role"]), points)
        context_ids = [target] + [cid for cid in known_ids if cid != target]
        begin = max(0, origin - context_length)
        contexts = tuple(series(signal_id, begin, origin) for signal_id in context_ids)
        future = tuple(series(signal_id, begin, min(len(rows), origin + horizon)) for signal_id in known_ids)
        return ForecastRequest(contexts, (target,), horizon, q_values, known_future_covariates=future)

    def validate_forecast(forecast: Any, rows: list[dict[str, Any]], origin: int) -> tuple[float, ...]:
        expected_timestamps = tuple(datetime.fromisoformat(rows[origin + lead]["timestamp"].replace("Z", "+00:00")) for lead in range(horizon))
        if len(forecast.point_forecast) != horizon or len(forecast.timestamps) != horizon or tuple(forecast.timestamps) != expected_timestamps:
            raise BenchmarkError("forecast horizon or timestamps do not match the requested test window")
        return tuple(float(value) for value in forecast.point_forecast)

    # validation residualsはvalidation区間内のoriginだけから収集する。
    for equipment_id in equipment_ids:
        if equipment_id not in by_equipment:
            raise BenchmarkError(f"unknown equipment: {equipment_id}")
        rows = by_equipment[equipment_id]
        train_start, train_end = split_indices[equipment_id]["train"]
        validation_start, validation_end = split_indices[equipment_id]["validation"]
        for requested_target in configured_targets:
            target, target_key = resolve_signal(equipment_id, requested_target)
            train_scales[(equipment_id, target)] = tuple(float(row["signals"][target_key]["value"]) for row in rows[train_start:train_end] if row["signals"][target_key]["value"] is not None)
            for model_cfg in config["models"]:
                model_name = model_cfg["name"]
                key = (equipment_id, target, model_name)
                residuals[key] = {lead: [] for lead in range(horizon)}
                try:
                    model = build_model(equipment_id, model_cfg)
                    covariates = tuple(resolve_signal(equipment_id, str(x))[0] for x in model_cfg.get("parameters", {}).get("covariate_ids", ()))
                    for origin in range(max(context_length, validation_start), validation_end - horizon + 1):
                        request = make_request(rows, equipment_id, target, origin, covariates)
                        forecast_series = model.forecast(request).forecasts[0]
                        forecast = validate_forecast(forecast_series, rows, origin)
                        actual = tuple(rows[origin + i]["signals"][target_key]["value"] for i in range(horizon))
                        if any(value is None for value in actual):
                            continue
                        for lead, (actual_value, predicted_value) in enumerate(zip(actual, forecast)):
                            residuals[key][lead].append(float(actual_value) - float(predicted_value))
                except (BaselineError, ValueError, KeyError) as exc:
                    record_failure(model_name, equipment_id, target, "failed", str(exc), "validation")
                    failed_keys.add(key)
                if any(not residuals[key].get(lead) for lead in range(horizon)) and key not in failed_keys:
                    record_failure(model_name, equipment_id, target, "inconclusive", "validation residuals are empty for at least one lead", "validation")
                    failed_keys.add(key)

    validation_seconds = time.perf_counter() - validation_start_time
    test_start_time = time.perf_counter()

    for equipment_id in equipment_ids:
        rows = by_equipment[equipment_id]
        train_start, train_end = split_indices[equipment_id]["train"]
        validation_start, validation_end = split_indices[equipment_id]["validation"]
        test_start, test_end = split_indices[equipment_id]["test"]
        for requested_target in configured_targets:
            target, target_key = resolve_signal(equipment_id, requested_target)
            for model_cfg in config["models"]:
                model_name = model_cfg["name"]
                key = (equipment_id, target, model_name)
                if key in failed_keys:
                    continue
                try:
                    model = build_model(equipment_id, model_cfg)
                    covariates = tuple(resolve_signal(equipment_id, str(x))[0] for x in model_cfg.get("parameters", {}).get("covariate_ids", ()))
                    residual = residuals.get(key, {})
                    if not residual or any(not residual.get(lead) for lead in range(horizon)):
                        raise BenchmarkError("validation residuals are empty; model is inconclusive")
                    for origin in range(max(context_length, test_start), test_end - horizon + 1, horizon):
                        request = make_request(rows, equipment_id, target, origin, covariates)
                        call_start = time.perf_counter()
                        forecast = model.forecast(request).forecasts[0]
                        point_forecast = validate_forecast(forecast, rows, origin)
                        test_latencies.append(time.perf_counter() - call_start)
                        actual = tuple(rows[origin + i]["signals"][target_key]["value"] for i in range(horizon))
                        if any(value is None for value in actual):
                            record_failure(model_name, equipment_id, target, "inconclusive", "test actual contains missing value", "test")
                            continue
                        calibrated = {q: tuple(point_forecast[lead] + _quantile(residual[lead], q) for lead in range(horizon)) for q in q_values}
                        actual_f = tuple(float(v) for v in actual)
                        for lead in range(horizon):
                            mode = rows[origin + lead]["operating_mode"]
                            slice_key = f"{model_name}|{target}|{equipment_id}|{mode}|{lead + 1}"
                            prediction = {"model": model_name, "equipment_id": equipment_id, "target_signal_id": target, "operating_mode": mode, "split": "test", "origin_timestamp": rows[origin]["timestamp"], "timestamp": forecast.timestamps[lead].isoformat().replace("+00:00", "Z"), "lead_time": lead + 1, "actual": actual_f[lead], "point_forecast": point_forecast[lead], "quantiles": {str(q): calibrated[q][lead] for q in q_values}}
                            _validate_prediction(prediction, q_values)
                            records.setdefault(slice_key, []).append(prediction)
                            predictions.append(prediction)
                except (BaselineError, MetricError, BenchmarkError, ValueError, KeyError) as exc:
                    record_failure(model_name, equipment_id, target, "failed" if isinstance(exc, BaselineError) else "inconclusive", str(exc), "test")

    test_seconds = time.perf_counter() - test_start_time
    if not predictions:
        raise BenchmarkError("all models failed or produced zero predictions")

    summary = {key: _aggregate_predictions(value, q_values, train_scales) for key, value in records.items()}
    overall = _aggregate_predictions(predictions, q_values, train_scales)
    elapsed = time.perf_counter() - start_time
    _, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    temp_parent = output_dir.parent
    temp_parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{config['run_id']}.", dir=temp_parent))
    try:
        with (temporary / "predictions.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
            for row in predictions:
                _validate_prediction(row, q_values)
                handle.write(json.dumps(_finite_json(row), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
        split_provenance = {equipment_id: {split_name: {"start_index": bounds[0], "end_index": bounds[1]} for split_name, bounds in split_indices[equipment_id].items()} for equipment_id in equipment_ids}
        result = _finite_json({"schema_version": "0.1", "result_type": "benchmark", "run_id": config["run_id"], "status": "partial" if failures else "success", "dataset_fingerprint": dataset_fingerprint, "generator_version": manifest.get("generator_version"), "run_config": config, "code_revision": _revision(root), "seed": config.get("seed"), "model_parameters": {item["name"]: item.get("parameters", {}) for item in config["models"]}, "prediction_count": len(predictions), "failures": failures, "metrics": {"aggregate": overall, "slices": summary}, "runtime": {"validation_seconds": validation_seconds, "test_seconds": test_seconds, "total_seconds": elapsed, "p50_latency_ms": _percentile([value * 1000 for value in test_latencies], 0.50), "p95_latency_ms": _percentile([value * 1000 for value in test_latencies], 0.95), "peak_memory_bytes": peak_memory, "model_state_bytes": _model_state_bytes(config["models"]), "output_size_bytes_excluding_result": 0, "os": platform.platform(), "python": sys.version, "cpu": platform.processor(), "calibration_source": "validation residuals by lead only"}, "provenance": {"quality_gate": quality, "split": split_provenance, "quantile_calibration": "validation residual only, lead-time specific"}})
        markdown = "# Benchmark結果\n\n合成データの結果であり、実設備の性能を示しません。\n\n## 概要\n\n- データ品質gate: 合格\n- 予測件数: %d\n- 分位点校正: validation residualのみ\n- 失敗・評価不能: %d\n- aggregate: %s\n\n## slice別\n\n%s\n" % (len(predictions), len(failures), overall, "\n".join(f"- `{key}`: {value}" for key, value in summary.items()))
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
