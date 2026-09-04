"""Chronos-2専用の隔離実行ツール群。"""

from __future__ import annotations

import hashlib
import importlib.metadata
from contextlib import contextmanager
import json
import os
from pathlib import Path
from typing import Any, Iterator, Mapping

ROOT = Path(__file__).resolve().parents[2]
OFFICIAL_CHECKPOINT = "amazon/chronos-2"
DEFAULT_REVISION = "29ec3766d36d6f73f0696f85560a422f50e8498c"
OFFICIAL_PACKAGE_NAME = "chronos-forecasting"
OFFICIAL_PACKAGE_VERSION = "2.3.1"
OFFICIAL_PACKAGE_SHA256 = "d9d00ec9b1621235bfb26685638bf054885f4c000863678f1c775dfab2697496"
EXPECTED_MODEL_SIZE_BYTES = 477930472
EXPECTED_MODEL_SHA256 = "ddcda3c7508bf2528087723e98a20707cc04b7f370ae275a9fd88078ddba4f42"
CHECKPOINT_ALLOW_PATTERNS = ("README.md", "config.json", "model.safetensors")
MANIFEST_PATH = ROOT / "examples" / "manifests" / "model-license-chronos2.json"
PROVENANCE_PATH = ROOT / "environments" / "chronos2" / "package-provenance.json"


def _outside_repository(path: Path) -> bool:
    try:
        path.resolve().relative_to(ROOT.resolve())
    except ValueError:
        return True
    return False


def external_cache(path: Path, *, must_exist: bool = True) -> Path:
    """Validate an explicitly supplied cache without searching other paths."""
    resolved = Path(path).expanduser().resolve()
    if not _outside_repository(resolved):
        raise ValueError("cache-dir must be outside the repository")
    if must_exist and not resolved.is_dir():
        raise ValueError("cache-dir must be an existing directory")
    if resolved.exists() and not resolved.is_dir():
        raise ValueError("cache-dir must be a directory")
    return resolved


@contextmanager
def offline_environment() -> Iterator[None]:
    """Force offline, no-telemetry execution and restore the caller environment."""
    values = {
        "HF_HUB_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "DO_NOT_TRACK": "1",
    }
    previous = {name: os.environ.get(name) for name in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


@contextmanager
def cache_environment(cache_dir: Path) -> Iterator[None]:
    """Point supported HF/Transformers caches at the explicit external cache."""
    cache = external_cache(cache_dir, must_exist=True)
    names = ("HF_HOME", "HF_HUB_CACHE", "TRANSFORMERS_CACHE")
    previous = {name: os.environ.get(name) for name in names}
    for name in names:
        os.environ[name] = str(cache)
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def load_json(path: Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_manifest(path: Path = MANIFEST_PATH) -> Mapping[str, object]:
    manifest = load_json(Path(path).expanduser().resolve())
    if not isinstance(manifest, dict):
        raise ValueError("model-license manifest must be an object")
    required = {
        "schema_version": "0.1",
        "manifest_type": "model-license",
        "model_id": "chronos-2",
        "code_license": "Apache-2.0",
        "weights_license": "Apache-2.0",
        "allowed_use": "commercial-evaluation",
        "source_url": "https://huggingface.co/amazon/chronos-2",
        "package_name": OFFICIAL_PACKAGE_NAME,
        "package_version": OFFICIAL_PACKAGE_VERSION,
        "package_sha256": OFFICIAL_PACKAGE_SHA256,
        "checkpoint": OFFICIAL_CHECKPOINT,
        "checkpoint_revision": DEFAULT_REVISION,
        "verified_at": "2026-09-04",
    }
    unknown = set(manifest) - set(required) - {"notes"}
    if unknown:
        raise ValueError(f"model-license manifest has unknown fields: {sorted(unknown)}")
    for key, expected in required.items():
        if manifest.get(key) != expected:
            raise ValueError(f"model-license manifest has invalid {key}")
    if not isinstance(manifest.get("verified_at"), str):
        raise ValueError("model-license manifest verified_at must be a string")
    if "notes" in manifest and not isinstance(manifest["notes"], str):
        raise ValueError("model-license manifest notes must be a string")
    return manifest


def load_provenance(path: Path = PROVENANCE_PATH) -> Mapping[str, object]:
    provenance = load_json(Path(path))
    if not isinstance(provenance, dict):
        raise ValueError("package provenance must be an object")
    expected = {
        "package_name": OFFICIAL_PACKAGE_NAME,
        "package_version": OFFICIAL_PACKAGE_VERSION,
        "package_sha256": OFFICIAL_PACKAGE_SHA256,
        "checkpoint": OFFICIAL_CHECKPOINT,
        "checkpoint_revision": DEFAULT_REVISION,
        "checkpoint_allow_patterns": list(CHECKPOINT_ALLOW_PATTERNS),
        "checkpoint_model_size_bytes": EXPECTED_MODEL_SIZE_BYTES,
        "checkpoint_model_sha256": EXPECTED_MODEL_SHA256,
        "package_license": "Apache-2.0",
        "weights_license": "Apache-2.0",
        "allowed_use": "commercial-evaluation",
    }
    for key, value in expected.items():
        if provenance.get(key) != value:
            raise ValueError(f"package provenance has invalid {key}")
    return provenance


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_snapshot(snapshot_path: Path) -> dict[str, object]:
    """Fail closed on path, file-set, size, and content digest."""
    snapshot = Path(snapshot_path).expanduser().resolve()
    if not snapshot.is_dir():
        raise ValueError("checkpoint snapshot must be a directory")
    files = tuple(sorted(
        path.relative_to(snapshot).as_posix()
        for path in snapshot.rglob("*")
        if path.is_file()
    ))
    if files != tuple(sorted(CHECKPOINT_ALLOW_PATTERNS)):
        raise ValueError(f"checkpoint file set mismatch: expected {CHECKPOINT_ALLOW_PATTERNS}, got {files}")
    model = snapshot / "model.safetensors"
    size = model.stat().st_size
    digest = sha256_file(model)
    if size != EXPECTED_MODEL_SIZE_BYTES:
        raise ValueError(f"model.safetensors size mismatch: expected {EXPECTED_MODEL_SIZE_BYTES}, got {size}")
    if digest != EXPECTED_MODEL_SHA256:
        raise ValueError(f"model.safetensors SHA-256 mismatch: expected {EXPECTED_MODEL_SHA256}, got {digest}")
    return {"path": str(model), "size_bytes": size, "sha256": digest}


def find_verified_snapshot(cache_dir: Path) -> Path:
    cache = external_cache(cache_dir, must_exist=True)
    load_provenance()
    candidates: list[Path] = []
    for model in cache.rglob("model.safetensors"):
        if model.parent.name != DEFAULT_REVISION:
            continue
        try:
            snapshot = model.parent.resolve()
            snapshot.relative_to(cache)
            verify_snapshot(snapshot)
        except (OSError, ValueError):
            continue
        candidates.append(snapshot)
    unique = tuple(dict.fromkeys(candidates))
    if len(unique) != 1:
        raise ValueError("exactly one verified Chronos-2 checkpoint snapshot is required")
    return unique[0]


def verify_installed_package() -> None:
    load_provenance()
    installed = importlib.metadata.version(OFFICIAL_PACKAGE_NAME)
    if installed != OFFICIAL_PACKAGE_VERSION:
        raise ValueError(f"installed {OFFICIAL_PACKAGE_NAME} version {installed} does not match {OFFICIAL_PACKAGE_VERSION}")


__all__ = [
    "CHECKPOINT_ALLOW_PATTERNS", "DEFAULT_REVISION", "EXPECTED_MODEL_SHA256",
    "EXPECTED_MODEL_SIZE_BYTES", "MANIFEST_PATH", "OFFICIAL_CHECKPOINT",
    "OFFICIAL_PACKAGE_NAME", "OFFICIAL_PACKAGE_SHA256", "OFFICIAL_PACKAGE_VERSION",
    "cache_environment", "external_cache", "find_verified_snapshot", "load_manifest",
    "load_provenance", "offline_environment", "sha256_file", "verify_installed_package",
    "verify_snapshot",
]
