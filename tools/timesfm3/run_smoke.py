"""Explicit, offline-only TimesFM 3 CPU smoke evaluation."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import sys
import tempfile
import time
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from banto_ai.adapters.timesfm3 import (  # noqa: E402
    DEFAULT_REVISION,
    OFFICIAL_CHECKPOINT,
    OFFICIAL_PACKAGE_NAME,
    OFFICIAL_PACKAGE_VERSION,
    TimesFM3Adapter,
    TimesFM3Config,
)
from banto_ai.manifest import load_json, validate  # noqa: E402
from banto_ai.naive import LastValueForecaster  # noqa: E402
from banto_ai.runtime import process_peak_memory_bytes, windows_peak_working_set_bytes  # noqa: E402
from banto_ai.types import (  # noqa: E402
    ForecastRequest,
    QualityStatus,
    SignalMetadata,
    SignalPoint,
    TimeSeries,
)

REQUIRED_QUANTILES = (0.1, 0.5, 0.9)
SMOKE_CONTEXT_LENGTH = 64
SMOKE_HORIZON = 8
MANIFEST_PATH = ROOT / "examples" / "manifests" / "model-license-timesfm3.json"


def _peak_rss_bytes() -> int | None:
    return process_peak_memory_bytes()[0]


def _windows_peak_working_set_bytes(*, psapi: Any | None = None, kernel32: Any | None = None) -> int | None:
    return windows_peak_working_set_bytes(psapi=psapi, kernel32=kernel32)


def _assert_external_cache(cache_dir: Path) -> Path:
    cache_dir = cache_dir.expanduser().resolve()
    try:
        cache_dir.relative_to(ROOT)
    except ValueError:
        pass
    else:
        raise ValueError("cache-dir must be outside the repository")
    if not cache_dir.is_dir():
        raise ValueError("cache-dir must be an existing directory; run preflight or prepare_checkpoint first")
    return cache_dir


def _artifact_path(output: Path) -> Path:
    output = output.expanduser().resolve()
    artifacts = (ROOT / "artifacts").resolve()
    try:
        output.relative_to(artifacts)
    except ValueError as exc:
        raise ValueError("output must be under the repository artifacts directory") from exc
    if output == artifacts:
        raise ValueError("output must be a file below artifacts")
    if os.path.lexists(str(output)):
        raise FileExistsError(f"refusing to overwrite existing output: {output}")
    return output


def _series(signal_id: str, values: tuple[float, ...], *, role: str, unit: str = "u") -> TimeSeries:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    metadata = SignalMetadata(signal_id, signal_id, unit, 1000, role=role)
    points = tuple(
        SignalPoint(start + timedelta(seconds=index), value, QualityStatus.OK)
        for index, value in enumerate(values)
    )
    return TimeSeries(metadata, points)


def _speed_value(index: int) -> float:
    if index < 16:
        return 20.0
    if index < 32:
        return 45.0
    if index < 48:
        return 70.0
    if index < 64:
        return 50.0
    return 80.0


def _load_value(index: int) -> float:
    if index < 16:
        return 0.5
    if index < 32:
        return 1.5
    if index < 48:
        return 2.5
    if index < 64:
        return 1.0
    return 3.0


def _target_values(signal_id: str, indexes: range) -> tuple[float, ...]:
    values = []
    for index in indexes:
        speed = _speed_value(index)
        load = _load_value(index)
        if signal_id == "motor_current":
            value = 8.0 + 0.06 * index + 0.9 * math.sin(index / 4.5) + 0.035 * speed + 0.8 * load
        elif signal_id == "motor_temperature":
            value = 35.0 + 0.04 * index + 0.6 * math.sin(index / 7.0 + 0.3) + 0.05 * speed + 0.4 * load
        else:
            raise ValueError(f"unknown smoke target: {signal_id}")
        values.append(value)
    return tuple(values)


def build_smoke_case() -> tuple[ForecastRequest, dict[str, tuple[float, ...]]]:
    """Build the deterministic non-linear request and its held-out actuals."""
    context_indexes = range(SMOKE_CONTEXT_LENGTH)
    all_indexes = range(SMOKE_CONTEXT_LENGTH + SMOKE_HORIZON)
    contexts = (
        _series("motor_current", _target_values("motor_current", context_indexes), role="target", unit="A"),
        _series("motor_temperature", _target_values("motor_temperature", context_indexes), role="target", unit="degC"),
        _series("speed", tuple(_speed_value(index) for index in context_indexes), role="covariate", unit="percent"),
        _series("planned_load", tuple(_load_value(index) for index in context_indexes), role="covariate", unit="load"),
    )
    known_future = (_series("planned_load", tuple(_load_value(index) for index in all_indexes), role="covariate", unit="load"),)
    request = ForecastRequest(
        contexts=contexts,
        target_signal_ids=("motor_current", "motor_temperature"),
        horizon=SMOKE_HORIZON,
        quantiles=REQUIRED_QUANTILES,
        profile_version="timesfm3-cpu-smoke",
        known_future_covariates=known_future,
    )
    actual = {
        signal_id: _target_values(signal_id, range(SMOKE_CONTEXT_LENGTH, SMOKE_CONTEXT_LENGTH + SMOKE_HORIZON))
        for signal_id in request.target_signal_ids
    }
    return request, actual


def build_smoke_request() -> ForecastRequest:
    """Build the deterministic non-linear 64-point smoke request."""
    return build_smoke_case()[0]


def _request_fingerprint(request: ForecastRequest) -> str:
    payload = {
        "contexts": [
            {
                "signal_id": series.metadata.signal_id,
                "role": series.metadata.role,
                "unit": series.metadata.unit,
                "sampling_interval_ms": series.metadata.sampling_interval_ms,
                "points": [[point.timestamp.isoformat(), point.value, point.quality_status.value] for point in series.points],
            }
            for series in request.contexts
        ],
        "known_future_covariates": [
            {
                "signal_id": series.metadata.signal_id,
                "role": series.metadata.role,
                "unit": series.metadata.unit,
                "sampling_interval_ms": series.metadata.sampling_interval_ms,
                "points": [[point.timestamp.isoformat(), point.value, point.quality_status.value] for point in series.points],
            }
            for series in request.known_future_covariates
        ],
        "target_signal_ids": request.target_signal_ids,
        "horizon": request.horizon,
        "quantiles": request.quantiles,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@contextmanager
def _cache_environment(cache_dir: Path):
    names = ("HF_HOME", "HUGGINGFACE_HUB_CACHE")
    previous = {name: os.environ.get(name) for name in names}
    for name in names:
        os.environ[name] = str(cache_dir)
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


@contextmanager
def _offline_environment():
    """Force and restore Hugging Face offline/telemetry settings for one run."""
    names = ("HF_HUB_OFFLINE", "HF_HUB_DISABLE_TELEMETRY")
    previous = {name: os.environ.get(name) for name in names}
    for name in names:
        os.environ[name] = "1"
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _installed_version(package_name: str) -> str | None:
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _error_metrics(actual: tuple[float, ...], predicted: tuple[float, ...], quantiles: Mapping[str, list[float]]) -> dict[str, float]:
    if len(actual) != len(predicted):
        raise ValueError("held-out actual and point forecast lengths must match")
    errors = [prediction - observed for observed, prediction in zip(actual, predicted)]
    widths = [upper - lower for lower, upper in zip(quantiles["0.1"], quantiles["0.9"])]
    return {
        "mae": sum(abs(error) for error in errors) / len(errors),
        "rmse": math.sqrt(sum(error * error for error in errors) / len(errors)),
        "mean_p90_p10_width": sum(widths) / len(widths),
    }


def _point_metrics(actual: tuple[float, ...], predicted: tuple[float, ...]) -> dict[str, float]:
    if len(actual) != len(predicted) or not actual:
        raise ValueError("held-out actual and point forecast must have the same non-empty length")
    errors = [prediction - observed for observed, prediction in zip(actual, predicted)]
    return {
        "mae": sum(abs(error) for error in errors) / len(errors),
        "rmse": math.sqrt(sum(error * error for error in errors) / len(errors)),
    }


def _comparison_metrics(model: Mapping[str, float], baseline: Mapping[str, float]) -> dict[str, Any]:
    comparison: dict[str, Any] = {}
    for name in ("mae", "rmse"):
        baseline_value = baseline[name]
        model_value = model[name]
        item: dict[str, Any] = {
            "timesfm3": model_value,
            "last_value": baseline_value,
            "absolute_difference": abs(model_value - baseline_value),
        }
        if baseline_value == 0:
            item["improvement_rate"] = None
            item["status"] = "inconclusive: baseline metric is zero"
        else:
            item["improvement_rate"] = (baseline_value - model_value) / baseline_value
            item["status"] = "measurable"
        comparison[name] = item
    return comparison


def _artifact_payload(
    request: ForecastRequest,
    actual: Mapping[str, tuple[float, ...]],
    result: Any,
    baseline_result: Any,
    elapsed: float,
    peak_rss: int | None,
    input_fingerprint: str,
) -> dict[str, Any]:
    if not result.forecasts:
        raise ValueError("smoke result must contain at least one target forecast")
    predictions = []
    all_errors = []
    all_widths = []
    for forecast in result.forecasts:
        quantiles = {str(item.quantile): list(item.values) for item in forecast.quantile_forecasts}
        if set(float(key) for key in quantiles) != set(REQUIRED_QUANTILES):
            raise ValueError("smoke result must contain p10, p50, and p90")
        if forecast.signal_id not in actual:
            raise ValueError(f"smoke result contains an unexpected target: {forecast.signal_id}")
        metric = _error_metrics(actual[forecast.signal_id], forecast.point_forecast, quantiles)
        errors = [prediction - observed for observed, prediction in zip(actual[forecast.signal_id], forecast.point_forecast)]
        all_errors.extend(errors)
        all_widths.extend(quantiles["0.9"][index] - quantiles["0.1"][index] for index in range(len(errors)))
        predictions.append({
            "signal_id": forecast.signal_id,
            "timestamps": [timestamp.isoformat() for timestamp in forecast.timestamps],
            "actual": list(actual[forecast.signal_id]),
            "point_forecast": list(forecast.point_forecast),
            "quantile_forecast": quantiles,
            "metrics": metric,
        })
    if len(predictions) != len(request.target_signal_ids):
        raise ValueError("smoke result target count does not match request")
    baseline_by_target: dict[str, dict[str, float]] = {}
    baseline_errors = []
    for forecast in baseline_result.forecasts:
        if forecast.signal_id not in actual:
            raise ValueError(f"baseline result contains an unexpected target: {forecast.signal_id}")
        metric = _point_metrics(actual[forecast.signal_id], forecast.point_forecast)
        baseline_by_target[forecast.signal_id] = metric
        baseline_errors.extend(
            prediction - observed
            for observed, prediction in zip(actual[forecast.signal_id], forecast.point_forecast)
        )
    if set(baseline_by_target) != set(request.target_signal_ids):
        raise ValueError("baseline result targets do not match request")
    if not baseline_errors or not all_errors or not all_widths:
        raise ValueError("smoke metrics require non-empty target forecasts")
    baseline_aggregate = {
        "mae": sum(abs(error) for error in baseline_errors) / len(baseline_errors),
        "rmse": math.sqrt(sum(error * error for error in baseline_errors) / len(baseline_errors)),
    }
    timesfm_aggregate = {
        "mae": sum(abs(error) for error in all_errors) / len(all_errors),
        "rmse": math.sqrt(sum(error * error for error in all_errors) / len(all_errors)),
    }
    return {
        "schema_version": "0.1",
        "status": "passed",
        "research_only": True,
        "production": False,
        "control_write": False,
        "offline_env_enforced": True,
        "safety": {
            "network_fallback": False,
            "local_files_only": True,
            "banto_hub_write": False,
            "plc_write": False,
            "offline_env_enforced": True,
        },
        "model": {
            "name": "timesfm3",
            "package": OFFICIAL_PACKAGE_NAME,
            "package_version_expected": OFFICIAL_PACKAGE_VERSION,
            "package_version_installed": _installed_version(OFFICIAL_PACKAGE_NAME),
            "checkpoint": OFFICIAL_CHECKPOINT,
            "checkpoint_revision": DEFAULT_REVISION,
            "model_version": result.model_version,
            "weights_license": "timesfm-non-commercial-license-v1.0",
            "allowed_use": "research-only",
        },
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "device": "cpu",
            "elapsed_seconds": elapsed,
            "peak_rss_bytes": peak_rss,
        },
        "input": {
            "generator": "deterministic-built-in-timesfm3-cpu-smoke-v2",
            "fingerprint_sha256": input_fingerprint,
            "context_length": len(request.contexts[0].points),
            "horizon": request.horizon,
            "target_count": len(request.target_signal_ids),
            "covariate_count": len(request.contexts) - len(request.target_signal_ids),
            "known_future_covariate_count": len(request.known_future_covariates),
        },
        "metrics": {
            "target": {item["signal_id"]: item["metrics"] for item in predictions},
            "aggregate": {
                **timesfm_aggregate,
                "mean_p90_p10_width": sum(all_widths) / len(all_widths),
            },
            "baseline": {
                "name": "last-value",
                "target": baseline_by_target,
                "aggregate": baseline_aggregate,
            },
            "comparison": {
                "target": {
                    item["signal_id"]: _comparison_metrics(
                        item["metrics"], baseline_by_target[item["signal_id"]]
                    )
                    for item in predictions
                },
                "aggregate": _comparison_metrics(timesfm_aggregate, baseline_aggregate),
            },
            "interpretation": "Single-window small deterministic synthetic smoke only; these metrics do not represent production equipment performance or general model performance.",
        },
        "predictions": predictions,
    }


def _atomic_publish(output: Path, payload: Mapping[str, Any]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if os.path.lexists(str(output)):
        raise FileExistsError(f"refusing to overwrite existing output: {output}")
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=output.parent, prefix=f".{output.name}.", suffix=".tmp", delete=False) as handle:
            temporary = handle.name
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        # link() atomically creates the destination and fails if a concurrent
        # writer won the race; unlike replace(), it cannot overwrite it.
        os.link(temporary, output)
        os.unlink(temporary)
        temporary = None
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


def run_smoke(
    cache_dir: Path,
    output: Path,
    *,
    adapter_factory: Callable[[Mapping[str, object], TimesFM3Config], Any] | None = None,
    manifest_path: Path = MANIFEST_PATH,
) -> dict[str, Any]:
    cache_dir = _assert_external_cache(cache_dir)
    output = _artifact_path(output)
    manifest = load_json(Path(manifest_path).resolve())
    schema = load_json(ROOT / "schemas" / "model-license-manifest.schema.json")
    validate(manifest, schema)
    request, actual = build_smoke_case()
    fingerprint = _request_fingerprint(request)
    config = TimesFM3Config(
        device="cpu",
        local_files_only=True,
        cache_dir=str(cache_dir),
    )
    factory = adapter_factory or (lambda license_manifest, adapter_config: TimesFM3Adapter(license_manifest, config=adapter_config))
    start = time.perf_counter()
    before_rss = _peak_rss_bytes()
    with _cache_environment(cache_dir), _offline_environment():
        adapter = factory(manifest, config)
        result = adapter.forecast(request)
        baseline_result = LastValueForecaster().forecast(request)
    elapsed = time.perf_counter() - start
    after_rss = _peak_rss_bytes()
    peak_rss = max(value for value in (before_rss, after_rss) if value is not None) if any(value is not None for value in (before_rss, after_rss)) else None
    payload = _artifact_payload(request, actual, result, baseline_result, elapsed, peak_rss, fingerprint)
    _atomic_publish(output, payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="run_smoke.py")
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        payload = run_smoke(Path(args.cache_dir), Path(args.output))
    except (ImportError, KeyError, OSError, TypeError, ValueError, RuntimeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"status": payload["status"], "output": str(Path(args.output).expanduser().resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
