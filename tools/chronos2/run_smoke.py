"""Chronos-2の小規模・決定的・offline smoke実行入口。"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import time
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from banto_ai.naive import LastValueForecaster  # noqa: E402
from banto_ai.types import ForecastRequest, ForecastResult, QualityStatus, SignalMetadata, SignalPoint, TimeSeries  # noqa: E402
from tools.chronos2 import (  # noqa: E402
    DEFAULT_REVISION,
    EXPECTED_MODEL_SHA256,
    EXPECTED_MODEL_SIZE_BYTES,
    MANIFEST_PATH,
    OFFICIAL_CHECKPOINT,
    OFFICIAL_PACKAGE_SHA256,
    cache_environment,
    external_cache,
    find_verified_snapshot,
    load_manifest,
    offline_environment,
    verify_installed_package,
    verify_snapshot,
)

try:  # The adapter itself is dependency-free; the official backend is lazy.
    from banto_ai.adapters.chronos2 import Chronos2Adapter, Chronos2Config
except ImportError:  # pragma: no cover - parallel adapter may be introduced later
    Chronos2Adapter = None  # type: ignore[assignment,misc]
    Chronos2Config = None  # type: ignore[assignment,misc]

REQUIRED_QUANTILES = (0.1, 0.5, 0.9)
SMOKE_CONTEXT_LENGTH = 24
SMOKE_HORIZON = 4

_assert_external_cache = external_cache
_verify_cached_checkpoint = find_verified_snapshot
_verify_installed_package = verify_installed_package
_verify_model_artifact = verify_snapshot
_offline_environment = offline_environment
_cache_environment = cache_environment


def _series(signal_id: str, values: tuple[float, ...], *, role: str, unit: str) -> TimeSeries:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    metadata = SignalMetadata(signal_id, signal_id, unit, 1000, role=role)
    return TimeSeries(metadata, tuple(SignalPoint(start + timedelta(seconds=i), value, QualityStatus.OK) for i, value in enumerate(values)))


def _load_value(index: int) -> float:
    return 0.5 + 0.5 * (index // 8)


def _speed_value(index: int) -> float:
    return 20.0 if index < 8 else 50.0 if index < 16 else 80.0


def _target_value(signal_id: str, index: int) -> float:
    load = _load_value(index)
    speed = _speed_value(index)
    if signal_id == "motor_current":
        return 8.0 + 0.04 * index + 0.25 * math.sin(index / 2.5) + 0.03 * speed + 0.8 * load
    if signal_id == "motor_temperature":
        return 35.0 + 0.03 * index + 0.15 * math.sin(index / 3.0) + 0.04 * speed + 0.4 * load
    raise ValueError(f"unknown smoke target: {signal_id}")


def build_smoke_case() -> tuple[ForecastRequest, dict[str, tuple[float, ...]]]:
    context = range(SMOKE_CONTEXT_LENGTH)
    combined = range(SMOKE_CONTEXT_LENGTH + SMOKE_HORIZON)
    targets = tuple(_series(signal, tuple(_target_value(signal, i) for i in context), role="target", unit=unit) for signal, unit in (("motor_current", "A"), ("motor_temperature", "degC")))
    speed = _series("speed", tuple(_speed_value(i) for i in context), role="covariate", unit="percent")
    planned_context = _series("planned_load", tuple(_load_value(i) for i in context), role="covariate", unit="load")
    planned_future = _series("planned_load", tuple(_load_value(i) for i in combined), role="covariate", unit="load")
    request = ForecastRequest(
        contexts=(*targets, speed, planned_context),
        target_signal_ids=("motor_current", "motor_temperature"),
        horizon=SMOKE_HORIZON,
        quantiles=REQUIRED_QUANTILES,
        profile_version="chronos2-cpu-smoke",
        known_future_covariates=(planned_future,),
    )
    actual = {signal: tuple(_target_value(signal, i) for i in range(SMOKE_CONTEXT_LENGTH, SMOKE_CONTEXT_LENGTH + SMOKE_HORIZON)) for signal in request.target_signal_ids}
    return request, actual


def build_smoke_request() -> ForecastRequest:
    return build_smoke_case()[0]


def _fingerprint(request: ForecastRequest) -> str:
    payload = {
        "targets": request.target_signal_ids,
        "horizon": request.horizon,
        "quantiles": request.quantiles,
        "contexts": [[series.metadata.signal_id, [point.value for point in series.points]] for series in request.contexts],
        "known_future": [[series.metadata.signal_id, [point.value for point in series.points]] for series in request.known_future_covariates],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _result_payload(result: ForecastResult) -> list[dict[str, Any]]:
    return [{
        "signal_id": item.signal_id,
        "timestamps": [timestamp.isoformat() for timestamp in item.timestamps],
        "point_forecast": list(item.point_forecast),
        "quantiles": {str(q.quantile): list(q.values) for q in item.quantile_forecasts},
    } for item in result.forecasts]


def _atomic_publish(output: Path, payload: Mapping[str, Any]) -> None:
    destination = Path(output).expanduser().resolve()
    artifacts = (ROOT / "artifacts").resolve()
    try:
        destination.relative_to(artifacts)
    except ValueError as exc:
        raise ValueError("output must be below repository artifacts") from exc
    if destination == artifacts or os.path.lexists(destination):
        raise FileExistsError(f"refusing to overwrite existing output: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=destination.parent, prefix=f".{destination.name}.", suffix=".tmp", delete=False) as handle:
            temporary = handle.name
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, destination)
        os.unlink(temporary)
        temporary = None
    finally:
        if temporary:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


def run_smoke(cache_dir: Path, output: Path, *, adapter_factory: Callable[[Mapping[str, object], Any], Any] | None = None, manifest_path: Path = MANIFEST_PATH, skip_checkpoint_verification: bool = False) -> dict[str, Any]:
    cache = _assert_external_cache(cache_dir, must_exist=True)
    manifest = load_manifest(manifest_path)
    _verify_installed_package()
    if not isinstance(skip_checkpoint_verification, bool):
        raise ValueError("skip_checkpoint_verification must be boolean")
    if skip_checkpoint_verification and adapter_factory is None:
        raise ValueError("checkpoint verification may only be skipped with an injected test adapter")
    if not skip_checkpoint_verification:
        snapshot = _verify_cached_checkpoint(cache)
        artifact = _verify_model_artifact(snapshot)
        checkpoint_provenance = {
            "verification_status": "verified",
            "verification_reason": "model.safetensors size and SHA-256 matched the pinned provenance",
            "snapshot_path": str(snapshot),
            "checkpoint_model_size_bytes": artifact["size_bytes"],
            "checkpoint_model_sha256": artifact["sha256"],
        }
    else:
        snapshot = None
        checkpoint_provenance = {
            "verification_status": "skipped-test-only",
            "verification_reason": "checkpoint was not inspected because an injected test adapter was used",
            "snapshot_path": None,
            "checkpoint_model_size_bytes": None,
            "checkpoint_model_sha256": None,
        }
    if Chronos2Config is None or Chronos2Adapter is None:
        raise RuntimeError("Chronos2Adapter is unavailable")
    config = Chronos2Config(checkpoint_revision=DEFAULT_REVISION, cache_dir=str(cache), device_map="cpu", local_files_only=True, batch_size=1, context_length=SMOKE_CONTEXT_LENGTH, cross_learning=False)
    factory = adapter_factory or (lambda license_manifest, adapter_config: Chronos2Adapter(license_manifest, config=adapter_config))
    request, actual = build_smoke_case()
    start = time.perf_counter()
    with _cache_environment(cache), _offline_environment():
        adapter = factory(manifest, config)
        result = adapter.forecast(request)
        baseline = LastValueForecaster().forecast(request)
    payload = {
        "schema_version": "0.1",
        "status": "pass",
        "model": {
            "id": "chronos-2",
            "package": "chronos-forecasting",
            "package_version": "2.3.1",
            "checkpoint": OFFICIAL_CHECKPOINT,
            "revision": DEFAULT_REVISION,
            "weights_license": "Apache-2.0",
            "provenance": {
                "package_sha256": OFFICIAL_PACKAGE_SHA256,
                "package_verification_status": "pinned-provenance; installed version matched",
                "allowed_use": "commercial-evaluation",
                "expected_checkpoint_model_size_bytes": EXPECTED_MODEL_SIZE_BYTES,
                "expected_checkpoint_model_sha256": EXPECTED_MODEL_SHA256,
                **checkpoint_provenance,
            },
        },
        "request": {"profile_version": request.profile_version, "context_length": SMOKE_CONTEXT_LENGTH, "horizon": SMOKE_HORIZON, "target_signal_ids": list(request.target_signal_ids), "past_only_covariate_ids": ["speed"], "known_future_covariate_ids": ["planned_load"], "quantiles": list(REQUIRED_QUANTILES), "fingerprint": _fingerprint(request)},
        "predictions": _result_payload(result),
        "baseline": _result_payload(baseline),
        "runtime": {"elapsed_seconds": time.perf_counter() - start, "device": "cpu", "local_files_only": True, "snapshot_verified": checkpoint_provenance["verification_status"] == "verified"},
    }
    _atomic_publish(Path(output), payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="run_smoke.py")
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--manifest", default=str(MANIFEST_PATH))
    args = parser.parse_args(argv)
    try:
        payload = run_smoke(Path(args.cache_dir), Path(args.output), manifest_path=Path(args.manifest))
    except (ImportError, KeyError, OSError, TypeError, ValueError, RuntimeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"status": payload["status"], "output": str(Path(args.output).expanduser().resolve())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
