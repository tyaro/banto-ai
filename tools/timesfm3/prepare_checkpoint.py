"""Explicit TimesFM 3 research checkpoint preparation entrypoint."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from banto_ai.adapters.timesfm3 import (  # noqa: E402
    DEFAULT_REVISION,
    OFFICIAL_CHECKPOINT,
    validate_timesfm3_license_manifest,
)
from banto_ai.manifest import load_json, validate  # noqa: E402

PROVENANCE_PATH = ROOT / "environments" / "timesfm3" / "package-provenance.json"
CHECKPOINT_ALLOW_PATTERNS = ("config.json", "model.safetensors", "LICENSE", "README.md")
EXPECTED_MODEL_SIZE_BYTES = 1_322_898_824
EXPECTED_MODEL_SHA256 = "a7592b0a8432baee54483254e5647856911ce69e09d09a9bb65904b2d98f17da"


@contextmanager
def _xet_fallback_environment():
    """明示download中のWindows Xet並列socket failureを避ける。"""
    name = "HF_HUB_DISABLE_XET"
    previous = os.environ.get(name)
    os.environ[name] = "1"
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous


def _outside_repository(path: Path) -> bool:
    try:
        path.relative_to(ROOT)
    except ValueError:
        return True
    return False


def load_license_manifest(path: Path) -> Mapping[str, object]:
    schema_path = ROOT / "schemas" / "model-license-manifest.schema.json"
    manifest = load_json(path)
    validate(manifest, load_json(schema_path))
    if not isinstance(manifest, dict):
        raise ValueError("model-license manifest must be an object")
    validate_timesfm3_license_manifest(manifest, "research-only")
    return manifest


def load_checkpoint_provenance() -> Mapping[str, object]:
    provenance = load_json(PROVENANCE_PATH)
    if not isinstance(provenance, dict):
        raise ValueError("TimesFM 3 package provenance must be an object")
    if provenance.get("checkpoint") != OFFICIAL_CHECKPOINT:
        raise ValueError("package provenance checkpoint is not the official TimesFM 3 checkpoint")
    if provenance.get("checkpoint_revision") != DEFAULT_REVISION:
        raise ValueError("package provenance revision is not the pinned official revision")
    if tuple(provenance.get("checkpoint_allow_patterns", ())) != CHECKPOINT_ALLOW_PATTERNS:
        raise ValueError("package provenance allow_patterns do not match the fixed artifact set")
    if provenance.get("checkpoint_model_size_bytes") != EXPECTED_MODEL_SIZE_BYTES:
        raise ValueError("package provenance model size does not match the expected artifact")
    if provenance.get("checkpoint_model_sha256") != EXPECTED_MODEL_SHA256:
        raise ValueError("package provenance model SHA-256 does not match the expected artifact")
    return provenance


def _verify_model_artifact(snapshot_path: Path) -> dict[str, object]:
    for filename in CHECKPOINT_ALLOW_PATTERNS:
        if not (snapshot_path / filename).is_file():
            raise ValueError(f"downloaded checkpoint is missing {filename}")
    model_path = snapshot_path / "model.safetensors"
    if not model_path.is_file():
        raise ValueError(f"downloaded checkpoint is missing {model_path.name}")
    size = model_path.stat().st_size
    if size != EXPECTED_MODEL_SIZE_BYTES:
        raise ValueError(
            f"model.safetensors size mismatch: expected {EXPECTED_MODEL_SIZE_BYTES}, got {size}"
        )
    digest = hashlib.sha256()
    with model_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    sha256 = digest.hexdigest()
    if sha256 != EXPECTED_MODEL_SHA256:
        raise ValueError(
            f"model.safetensors SHA-256 mismatch: expected {EXPECTED_MODEL_SHA256}, got {sha256}"
        )
    return {"path": str(model_path), "size_bytes": size, "sha256": sha256}


def prepare_checkpoint(cache_dir: Path, manifest_path: Path, *, accepted: bool) -> dict[str, Any]:
    if not accepted:
        raise ValueError("--accept-research-only-license is required; no download was attempted")
    cache_dir = Path(cache_dir).expanduser().resolve()
    if not _outside_repository(cache_dir):
        raise ValueError("cache-dir must be outside the repository")
    if cache_dir.exists() and not cache_dir.is_dir():
        raise ValueError("cache-dir must be a directory")
    cache_dir.mkdir(parents=True, exist_ok=True)
    manifest = load_license_manifest(Path(manifest_path).expanduser().resolve())
    load_checkpoint_provenance()
    if manifest.get("model_id") != "timesfm-3.0" or manifest.get("checkpoint") != OFFICIAL_CHECKPOINT:
        raise ValueError("manifest does not identify the official TimesFM 3 checkpoint")
    revision = manifest.get("checkpoint_revision")
    if revision != DEFAULT_REVISION:
        raise ValueError("manifest checkpoint revision is not the pinned official revision")
    if manifest.get("allowed_use") != "research-only" or manifest.get("weights_license") != "timesfm-non-commercial-license-v1.0":
        raise ValueError("TimesFM 3 weights are accepted only for research-only use")

    hub = importlib.import_module("huggingface_hub")
    snapshot_download = getattr(hub, "snapshot_download", None)
    if not callable(snapshot_download):
        raise RuntimeError("huggingface_hub.snapshot_download is unavailable")
    with _xet_fallback_environment():
        snapshot_path = snapshot_download(
            repo_id=OFFICIAL_CHECKPOINT,
            revision=revision,
            cache_dir=str(cache_dir),
            allow_patterns=list(CHECKPOINT_ALLOW_PATTERNS),
            local_files_only=False,
            max_workers=1,
        )
    snapshot_path = Path(snapshot_path).expanduser().resolve()
    try:
        snapshot_path.relative_to(cache_dir)
    except ValueError as exc:
        raise ValueError("snapshot_download returned a path outside cache-dir") from exc
    model_artifact = _verify_model_artifact(snapshot_path)
    return {
        "schema_version": "0.1",
        "status": "downloaded-or-reused",
        "model_id": manifest["model_id"],
        "repo_id": OFFICIAL_CHECKPOINT,
        "revision": revision,
        "cache_dir": str(cache_dir),
        "snapshot_path": str(snapshot_path),
        "allow_patterns": list(CHECKPOINT_ALLOW_PATTERNS),
        "model_artifact": model_artifact,
        "allowed_use": "research-only",
        "weights_license": manifest["weights_license"],
        "network_policy": "explicit preparation only; run_smoke uses local_files_only=True",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="prepare_checkpoint.py")
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--manifest", default=str(ROOT / "examples" / "manifests" / "model-license-timesfm3.json"))
    parser.add_argument("--accept-research-only-license", action="store_true", required=True)
    args = parser.parse_args(argv)
    try:
        result = prepare_checkpoint(Path(args.cache_dir), Path(args.manifest), accepted=args.accept_research_only_license)
    except (ImportError, KeyError, OSError, TypeError, ValueError, RuntimeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
