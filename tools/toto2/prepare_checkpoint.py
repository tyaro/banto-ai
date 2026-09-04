"""Explicit, accepted download and immutable snapshot verification."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
from typing import Any

from tools.toto2 import CHECKPOINT_ALLOW_PATTERNS, DEFAULT_REVISION, EXPECTED_MODEL_SHA256, EXPECTED_MODEL_SIZE_BYTES, MANIFEST_PATH, OFFICIAL_CHECKPOINT, external_cache, load_manifest, load_provenance


@contextmanager
def _xet_fallback_environment():
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


def verify_snapshot(snapshot_path: Path) -> dict[str, object]:
    snapshot = Path(snapshot_path).expanduser().resolve()
    if not snapshot.is_dir():
        raise ValueError("checkpoint snapshot must be a directory")
    files = tuple(sorted(path.relative_to(snapshot).as_posix() for path in snapshot.rglob("*") if path.is_file()))
    if files != tuple(sorted(CHECKPOINT_ALLOW_PATTERNS)):
        raise ValueError(f"checkpoint file set mismatch: expected {CHECKPOINT_ALLOW_PATTERNS}, got {files}")
    model = snapshot / "model.safetensors"
    digest = hashlib.sha256(model.read_bytes()).hexdigest()
    if model.stat().st_size != EXPECTED_MODEL_SIZE_BYTES:
        raise ValueError("model.safetensors size mismatch")
    if digest != EXPECTED_MODEL_SHA256:
        raise ValueError("model.safetensors SHA-256 mismatch")
    return {"path": str(model), "size_bytes": model.stat().st_size, "sha256": digest}


def prepare_checkpoint(cache_dir: Path, manifest_path: Path = MANIFEST_PATH, *, accepted: bool) -> dict[str, Any]:
    if not accepted:
        raise ValueError("--accept-apache-2.0 is required; no download was attempted")
    manifest = load_manifest(manifest_path)
    provenance = load_provenance()
    cache = external_cache(cache_dir, must_exist=False)
    cache.mkdir(parents=True, exist_ok=True)
    hub = importlib.import_module("huggingface_hub")
    with _xet_fallback_environment():
        snapshot = Path(hub.snapshot_download(repo_id=OFFICIAL_CHECKPOINT, revision=DEFAULT_REVISION, cache_dir=str(cache), allow_patterns=list(CHECKPOINT_ALLOW_PATTERNS), local_files_only=False, max_workers=1)).expanduser().resolve()
    try:
        snapshot.relative_to(cache)
    except ValueError as exc:
        raise ValueError("snapshot_download returned a path outside cache-dir") from exc
    artifact = verify_snapshot(snapshot)
    return {"schema_version": "0.1", "status": "downloaded-or-reused", "repo_id": OFFICIAL_CHECKPOINT, "revision": DEFAULT_REVISION, "cache_dir": str(cache), "snapshot_path": str(snapshot), "allow_patterns": list(CHECKPOINT_ALLOW_PATTERNS), "model_artifact": artifact, "package_provenance": {"package_sha256": provenance["package_sha256"], "model_size_bytes": EXPECTED_MODEL_SIZE_BYTES, "model_sha256": EXPECTED_MODEL_SHA256}, "allowed_use": manifest["allowed_use"], "weights_license": manifest["weights_license"], "network_policy": "explicit preparation only; execution tools force local_files_only=True"}


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
