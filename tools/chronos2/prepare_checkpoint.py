"""Chronos-2 checkpointの明示的な取得・固定artifact検証入口。"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from pathlib import Path
import sys
from contextlib import contextmanager
import os
from typing import Any

from tools.chronos2 import (
    CHECKPOINT_ALLOW_PATTERNS,
    DEFAULT_REVISION,
    MANIFEST_PATH,
    OFFICIAL_CHECKPOINT,
    external_cache,
    load_manifest,
    load_provenance,
)

# TimesFM tool parity makes the safety boundaries easy to audit and mock.
PROVENANCE_PATH = Path(__file__).resolve().parents[2] / "environments" / "chronos2" / "package-provenance.json"
EXPECTED_MODEL_SIZE_BYTES = 477930472
EXPECTED_MODEL_SHA256 = "ddcda3c7508bf2528087723e98a20707cc04b7f370ae275a9fd88078ddba4f42"
load_license_manifest = load_manifest
load_checkpoint_provenance = load_provenance


@contextmanager
def _xet_fallback_environment():
    """Avoid Windows Xet parallel socket failures during the explicit download."""
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


def _verify_model_artifact(snapshot_path: Path) -> dict[str, object]:
    snapshot = Path(snapshot_path).expanduser().resolve()
    if not snapshot.is_dir():
        raise ValueError("checkpoint snapshot must be a directory")
    files = tuple(sorted(path.relative_to(snapshot).as_posix() for path in snapshot.rglob("*") if path.is_file()))
    if files != tuple(sorted(CHECKPOINT_ALLOW_PATTERNS)):
        raise ValueError(f"checkpoint file set mismatch: expected {CHECKPOINT_ALLOW_PATTERNS}, got {files}")
    model_path = snapshot / "model.safetensors"
    size = model_path.stat().st_size
    digest = hashlib.sha256()
    with model_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    sha256 = digest.hexdigest()
    if size != EXPECTED_MODEL_SIZE_BYTES:
        raise ValueError(f"model.safetensors size mismatch: expected {EXPECTED_MODEL_SIZE_BYTES}, got {size}")
    if sha256 != EXPECTED_MODEL_SHA256:
        raise ValueError(f"model.safetensors SHA-256 mismatch: expected {EXPECTED_MODEL_SHA256}, got {sha256}")
    return {"path": str(model_path), "size_bytes": size, "sha256": sha256}


def prepare_checkpoint(cache_dir: Path, manifest_path: Path = MANIFEST_PATH, *, accepted: bool) -> dict[str, Any]:
    if not accepted:
        raise ValueError("--accept-apache-2.0 is required; no download was attempted")
    manifest = load_license_manifest(manifest_path)
    provenance = load_checkpoint_provenance()
    if manifest.get("allowed_use") != "commercial-evaluation":
        raise ValueError("Chronos-2 preparation is limited to commercial-evaluation")
    cache = external_cache(cache_dir, must_exist=False)
    cache.mkdir(parents=True, exist_ok=True)
    hub = importlib.import_module("huggingface_hub")
    download = getattr(hub, "snapshot_download", None)
    if not callable(download):
        raise RuntimeError("huggingface_hub.snapshot_download is unavailable")
    with _xet_fallback_environment():
        snapshot = Path(download(
            repo_id=OFFICIAL_CHECKPOINT,
            revision=DEFAULT_REVISION,
            cache_dir=str(cache),
            allow_patterns=list(CHECKPOINT_ALLOW_PATTERNS),
            local_files_only=False,
            max_workers=1,
        )).expanduser().resolve()
    try:
        snapshot.relative_to(cache)
    except ValueError as exc:
        raise ValueError("snapshot_download returned a path outside cache-dir") from exc
    artifact = _verify_model_artifact(snapshot)
    return {
        "schema_version": "0.1",
        "status": "downloaded-or-reused",
        "repo_id": OFFICIAL_CHECKPOINT,
        "revision": DEFAULT_REVISION,
        "cache_dir": str(cache),
        "snapshot_path": str(snapshot),
        "allow_patterns": list(CHECKPOINT_ALLOW_PATTERNS),
        "model_artifact": artifact,
        "package_provenance": {"package_sha256": provenance["package_sha256"], "model_size_bytes": EXPECTED_MODEL_SIZE_BYTES, "model_sha256": EXPECTED_MODEL_SHA256},
        "allowed_use": "commercial-evaluation",
        "weights_license": "Apache-2.0",
        "network_policy": "explicit preparation only; execution tools force local_files_only=True",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="prepare_checkpoint.py")
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--manifest", default=str(MANIFEST_PATH))
    parser.add_argument("--accept-apache-2.0", action="store_true", required=True)
    args = parser.parse_args(argv)
    try:
        result = prepare_checkpoint(Path(args.cache_dir), Path(args.manifest), accepted=args.accept_apache_2_0)
    except (ImportError, KeyError, OSError, TypeError, ValueError, RuntimeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
