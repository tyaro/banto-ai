"""Small deterministic Toto 2.0 CPU smoke entrypoint."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "src"))
from banto_ai.naive import LastValueForecaster  # noqa: E402
from banto_ai.types import ForecastRequest, ForecastResult, QualityStatus, SignalMetadata, SignalPoint, TimeSeries  # noqa: E402
from banto_ai.adapters.toto2 import Toto2Adapter, Toto2Config  # noqa: E402
from tools.toto2 import DEFAULT_REVISION, EXPECTED_MODEL_SHA256, EXPECTED_MODEL_SIZE_BYTES, MANIFEST_PATH, OFFICIAL_CHECKPOINT, OFFICIAL_PACKAGE_SHA256, cache_environment, external_cache, find_verified_snapshot, load_manifest, offline_environment, verify_installed_package, verify_snapshot  # noqa: E402

REQUIRED_QUANTILES = (0.1, 0.5, 0.9)
SMOKE_CONTEXT_LENGTH = 120
SMOKE_HORIZON = 15

_assert_external_cache = external_cache
_verify_cached_checkpoint = find_verified_snapshot
_verify_installed_package = verify_installed_package
_verify_model_artifact = verify_snapshot
_offline_environment = offline_environment
_cache_environment = cache_environment


def _series(signal_id: str, values: tuple[float, ...], *, role: str, unit: str) -> TimeSeries:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    meta = SignalMetadata(signal_id, signal_id, unit, 60_000, role=role)
    return TimeSeries(meta, tuple(SignalPoint(start + timedelta(minutes=i), value, QualityStatus.OK) for i, value in enumerate(values)))


def _target_value(signal_id: str, index: int) -> float:
    if signal_id == "motor_current": return 8.0 + index * 0.04
    if signal_id == "oil_temperature": return 35.0 + index * 0.03
    raise ValueError(signal_id)


def build_smoke_case() -> tuple[ForecastRequest, dict[str, tuple[float, ...]]]:
    context = tuple(range(SMOKE_CONTEXT_LENGTH))
    targets = tuple(_series(signal, tuple(_target_value(signal, i) for i in context), role="target", unit=unit) for signal, unit in (("motor_current", "A"), ("oil_temperature", "degC")))
    covariate = _series("load", tuple(0.5 + (i // 10) for i in context), role="covariate", unit="load")
    request = ForecastRequest(contexts=(*targets, covariate), target_signal_ids=("motor_current", "oil_temperature"), horizon=SMOKE_HORIZON, quantiles=REQUIRED_QUANTILES, profile_version="toto2-4m-cpu-smoke", known_future_covariates=())
    actual = {signal: tuple(_target_value(signal, i) for i in range(SMOKE_CONTEXT_LENGTH, SMOKE_CONTEXT_LENGTH + SMOKE_HORIZON)) for signal in request.target_signal_ids}
    return request, actual


def _fingerprint(request: ForecastRequest) -> str:
    payload = {"targets": request.target_signal_ids, "horizon": request.horizon, "quantiles": request.quantiles, "contexts": [[s.metadata.signal_id, [p.value for p in s.points]] for s in request.contexts], "known_future": []}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _result_payload(result: ForecastResult) -> list[dict[str, Any]]:
    return [{"signal_id": item.signal_id, "timestamps": [t.isoformat() for t in item.timestamps], "point_forecast": list(item.point_forecast), "quantiles": {str(q.quantile): list(q.values) for q in item.quantile_forecasts}} for item in result.forecasts]


def _publish(output: Path, payload: Mapping[str, Any]) -> None:
    destination = Path(output).expanduser().resolve(); artifacts = (ROOT / "artifacts").resolve()
    try: destination.relative_to(artifacts)
    except ValueError as exc: raise ValueError("output must be below repository artifacts") from exc
    if destination == artifacts or os.path.lexists(destination): raise FileExistsError(f"refusing to overwrite existing output: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=destination.parent, prefix=f".{destination.name}.", suffix=".tmp", delete=False) as handle:
            temporary = handle.name
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
            handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        os.link(temporary, destination)
        os.unlink(temporary); temporary = None
    finally:
        if temporary is not None:
            try: os.unlink(temporary)
            except FileNotFoundError: pass


def run_smoke(cache_dir: Path, output: Path, *, adapter_factory: Callable[[Mapping[str, object], Toto2Config], Any] | None = None, manifest_path: Path = MANIFEST_PATH, skip_checkpoint_verification: bool = False) -> dict[str, Any]:
    cache = _assert_external_cache(cache_dir)
    manifest = load_manifest(Path(manifest_path).expanduser().resolve())
    if skip_checkpoint_verification:
        snapshot_verified = False; artifact = None
    else:
        artifact_path = _verify_cached_checkpoint(cache); artifact = _verify_model_artifact(artifact_path); snapshot_verified = True
    _verify_installed_package()
    request, actual = build_smoke_case(); config = Toto2Config(cache_dir=str(cache), device="cpu", batch_size=1, local_files_only=True, patch_size=32)
    factory = adapter_factory or (lambda license_manifest, adapter_config: Toto2Adapter(license_manifest, config=adapter_config))
    with _cache_environment(cache), _offline_environment():
        result = factory(manifest, config).forecast(request)
        baseline = LastValueForecaster().forecast(request)
    quantile_map = {f.signal_id: {str(q.quantile): list(q.values) for q in f.quantile_forecasts} for f in result.forecasts}
    if set(quantile_map) != set(request.target_signal_ids): raise ValueError("smoke result targets do not match request")
    payload = {"schema_version": "0.1", "status": "pass", "research_only": False, "production": False, "control_write": False, "safety": {"network_fallback": False, "local_files_only": True, "banto_hub_write": False, "plc_write": False}, "model": {"name": "toto2", "package": "toto-2", "package_version_expected": "2.0.0", "package_sha256": OFFICIAL_PACKAGE_SHA256, "checkpoint": OFFICIAL_CHECKPOINT, "checkpoint_revision": DEFAULT_REVISION, "weights_license": manifest["weights_license"], "allowed_use": manifest["allowed_use"], "provenance": {"verification_status": "verified" if snapshot_verified else "skipped-test-only", "checkpoint_model_size_bytes": artifact["size_bytes"] if artifact else None, "checkpoint_model_sha256": artifact["sha256"] if artifact else None}}, "runtime": {"device": "cpu", "batch_size": 1, "decode_block_size": None, "has_missing_values": True, "snapshot_verified": snapshot_verified}, "input": {"generator": "deterministic-built-in-toto2-4m-cpu-smoke", "fingerprint_sha256": _fingerprint(request), "context_length": SMOKE_CONTEXT_LENGTH, "effective_model_input_length": 128, "padding_left": 8, "patch_size": 32, "horizon": SMOKE_HORIZON, "target_signal_ids": list(request.target_signal_ids), "past_only_covariate_ids": ["load"], "known_future_covariate_ids": []}, "predictions": _result_payload(result), "baseline": _result_payload(baseline)}
    _publish(Path(output), payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="run_smoke.py"); parser.add_argument("--cache-dir", required=True); parser.add_argument("--output", required=True); parser.add_argument("--manifest", default=str(MANIFEST_PATH)); parser.add_argument("--skip-checkpoint-verification", action="store_true")
    args = parser.parse_args(argv)
    try: payload = run_smoke(Path(args.cache_dir), Path(args.output), manifest_path=Path(args.manifest), skip_checkpoint_verification=args.skip_checkpoint_verification)
    except (ImportError, KeyError, OSError, TypeError, ValueError, RuntimeError) as exc: print(f"FAIL: {exc}", file=sys.stderr); return 1
    print(json.dumps({"status": payload["status"], "output": str(Path(args.output).expanduser().resolve())}, ensure_ascii=False)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
