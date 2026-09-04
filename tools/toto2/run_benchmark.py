"""Offline MetroPT-3 benchmark entrypoint for Toto 2.0 4M."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "src"))
from banto_ai.benchmark import BenchmarkError, ModelRegistry, run_benchmark  # noqa: E402
from banto_ai.manifest import load_json  # noqa: E402
from banto_ai.adapters.toto2 import Toto2Adapter, Toto2Config  # noqa: E402
from tools.toto2 import DEFAULT_REVISION, MANIFEST_PATH, cache_environment, external_cache, find_verified_snapshot, load_manifest, offline_environment, verify_installed_package  # noqa: E402

_external_cache = external_cache
_verify_cached_checkpoint = find_verified_snapshot
_verify_installed_package = verify_installed_package
_offline_environment = offline_environment
_cache_environment = cache_environment
_load_and_validate_license = load_manifest


def make_shared_toto_factory(manifest: Mapping[str, object], cache_dir: Path):
    shared: Toto2Adapter | None = None
    def factory(_equipment_id: str, parameters: dict[str, Any]):
        nonlocal shared
        allowed = {"checkpoint_revision", "device", "batch_size", "local_files_only", "patch_size"}
        unknown = set(parameters) - allowed
        if unknown:
            raise ValueError(f"unsupported Toto 2.0 parameters: {sorted(unknown)}")
        revision = parameters.get("checkpoint_revision", DEFAULT_REVISION)
        device = parameters.get("device", "cpu")
        local_files_only = parameters.get("local_files_only", True)
        batch_size = parameters.get("batch_size", 1)
        patch_size = parameters.get("patch_size", 32)
        if not isinstance(revision, str) or revision != DEFAULT_REVISION:
            raise ValueError("Toto 2.0 benchmark requires the pinned checkpoint revision")
        if device != "cpu" or local_files_only is not True:
            raise ValueError("Toto 2.0 benchmark requires device=cpu and local_files_only=true")
        if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size != 1:
            raise ValueError("Toto 2.0 benchmark requires batch_size=1")
        if isinstance(patch_size, bool) or not isinstance(patch_size, int) or patch_size != 32:
            raise ValueError("Toto 2.0 benchmark requires patch_size=32")
        config = Toto2Config(checkpoint_revision=revision, cache_dir=str(cache_dir), device=device, batch_size=batch_size, patch_size=patch_size)
        if shared is None:
            shared = Toto2Adapter(manifest, config=config)
        return shared
    return factory


def run_toto_benchmark(config_path: Path, root: Path, cache_dir: Path, manifest_path: Path = MANIFEST_PATH) -> Path:
    root = Path(root).expanduser().resolve()
    cache = _external_cache(cache_dir, must_exist=True)
    manifest = _load_and_validate_license(manifest_path)
    _verify_cached_checkpoint(cache)
    _verify_installed_package()
    config = load_json(Path(config_path).expanduser().resolve())
    if not isinstance(config, dict):
        raise BenchmarkError("benchmark config must be an object")
    models = [model for model in config.get("models", []) if isinstance(model, dict) and model.get("name") == "toto2"]
    if len(models) != 1:
        raise ValueError("benchmark config must contain exactly one toto2 model")
    if any(model.get("quantile_policy", "native") != "native" for model in models):
        raise ValueError("Toto 2.0 must use native quantile policy")
    registry = ModelRegistry({"toto2": make_shared_toto_factory(manifest, cache)})
    with _cache_environment(cache), _offline_environment():
        return run_benchmark(Path(config_path).expanduser().resolve(), root, registry)


run_toto2_benchmark = run_toto_benchmark


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="run_benchmark.py")
    parser.add_argument("--config", required=True); parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--manifest", default=str(MANIFEST_PATH)); parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args(argv)
    config = Path(args.config).expanduser(); root = Path(args.root).expanduser().resolve()
    if not config.is_absolute(): config = root / config
    try: output = run_toto_benchmark(config, root, Path(args.cache_dir), Path(args.manifest))
    except (BenchmarkError, ImportError, KeyError, OSError, TypeError, ValueError, RuntimeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr); return 1
    print(f"benchmark: PASS ({output})"); return 0


if __name__ == "__main__":
    raise SystemExit(main())
