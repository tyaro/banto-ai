"""Phase 0/1の検証・評価CLI。"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from math import isclose, isfinite
from pathlib import Path

from .license_gate import evaluate_promotion
from .generator import GeneratorError, generate_synthetic
from .manifest import ManifestValidationError, load_json, validate_manifest
from .naive import LastValueForecaster, mean_absolute_error
from .quality import DatasetQualityError, check_dataset
from .safety import RepositorySafetyError, scan_repository
from .types import ForecastRequest, SignalMetadata, SignalPoint, TimeSeries


MANIFEST_SCHEMA_NAMES = ("dataset", "run", "result", "model-license")


def _repo_root(explicit: str | None = None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    candidates = [Path.cwd(), Path(__file__).resolve().parents[2]]
    for candidate in candidates:
        if (candidate / "schemas").is_dir() and (candidate / "examples").is_dir():
            return candidate
    return Path.cwd()


def validate_samples(root: Path) -> int:
    manifest_dir = root / "examples" / "manifests"
    schema_dir = root / "schemas"
    count = 0
    for schema_name in MANIFEST_SCHEMA_NAMES:
        schema = schema_dir / f"{schema_name}-manifest.schema.json"
        manifests = sorted(manifest_dir.glob(f"{schema_name}*.json"))
        if not manifests:
            raise ManifestValidationError(f"no sample manifests found for type {schema_name}")
        for manifest in manifests:
            validate_manifest(manifest, schema)
            count += 1
    return count


def evaluate_fixture(root: Path) -> float:
    fixture = load_json(root / "examples" / "fixtures" / "synthetic-motor.json")
    series_data = fixture["series"][0]
    metadata = SignalMetadata(
        signal_id=series_data["signal_id"], name=series_data["name"], unit=series_data["unit"],
        sampling_interval_ms=series_data["sampling_interval_ms"],
    )
    points = tuple(
        SignalPoint(datetime.fromisoformat(point["timestamp"].replace("Z", "+00:00")), point["value"])
        for point in series_data["points"]
    )
    context_length = fixture["evaluation"]["context_length"]
    horizon = fixture["evaluation"]["horizon"]
    context = TimeSeries(metadata, points[:context_length])
    actual = tuple(point.value for point in points[context_length:context_length + horizon])
    result = LastValueForecaster().forecast(ForecastRequest((context,), (metadata.signal_id,), horizon))
    return mean_absolute_error(actual, result.forecasts[0].point_forecast)


def command_smoke(root: Path) -> int:
    count = validate_samples(root)
    mae = evaluate_fixture(root)
    validate_naive_result(root, mae)
    print(f"manifest validation: PASS ({count} manifests)")
    print(f"naive evaluation: PASS (last-value, mae={mae:.6f})")
    return 0


def validate_naive_result(root: Path, computed_mae: float) -> None:
    result = load_json(root / "examples" / "manifests" / "result-naive.json")
    declared_mae = result.get("metrics", {}).get("mae")
    if not isinstance(declared_mae, (int, float)) or not isfinite(declared_mae):
        raise ManifestValidationError("result-naive.json metrics.mae must be a finite number")
    if not isclose(computed_mae, declared_mae, rel_tol=0.0, abs_tol=1e-12):
        raise ManifestValidationError(
            f"naive MAE drift: computed={computed_mae}, declared={declared_mae}"
        )


def command_validate(root: Path) -> int:
    count = validate_samples(root)
    print(f"manifest validation: PASS ({count} manifests)")
    return 0


def command_safety(root: Path) -> int:
    findings = scan_repository(root)
    if findings:
        for finding in findings:
            print(f"SAFETY FAIL: {finding}", file=sys.stderr)
        return 1
    print("repository safety: PASS")
    return 0


def command_license(root: Path) -> int:
    for path in sorted((root / "examples" / "manifests").glob("model-license*.json")):
        manifest = load_json(path)
        decision = evaluate_promotion(manifest, "product-candidate")
        state = "PASS" if decision.allowed else "BLOCKED"
        print(f"{path.name}: {state} - {decision.reason}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="banto-ai")
    parser.add_argument("command", choices=("smoke", "validate-manifests", "safety", "license", "generate-synthetic", "check-quality"))
    parser.add_argument("--root", help="repository root; defaults to the current checkout")
    parser.add_argument("--config", help="synthetic generator config JSON")
    parser.add_argument("--output", help="synthetic output directory; defaults below artifacts/generated")
    parser.add_argument("--dataset", help="generated dataset directory for quality check")
    args = parser.parse_args(argv)
    root = _repo_root(args.root)
    try:
        if args.command == "generate-synthetic":
            if not args.config:
                parser.error("generate-synthetic requires --config")
            config_path = Path(args.config)
            if not config_path.is_absolute():
                config_path = (root / config_path).resolve()
            output = generate_synthetic(config_path, args.output, root)
            print(f"synthetic generation: PASS ({output})")
            return 0
        if args.command == "check-quality":
            if not args.dataset:
                parser.error("check-quality requires --dataset")
            dataset_path = Path(args.dataset)
            if not dataset_path.is_absolute():
                dataset_path = (root / dataset_path).resolve()
            result = check_dataset(dataset_path, root)
            print(f"dataset quality: PASS ({result['observation_record_count']} rows, {result['equipment_count']} equipment)")
            return 0
        return {
            "smoke": command_smoke,
            "validate-manifests": command_validate,
            "safety": command_safety,
            "license": command_license,
        }[args.command](root)
    except (ManifestValidationError, RepositorySafetyError, GeneratorError, DatasetQualityError, KeyError, ValueError, OSError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
