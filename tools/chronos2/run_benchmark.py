"""Chronos-2専用、商用評価用offline benchmark入口。"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from banto_ai.benchmark import BenchmarkError, ModelRegistry, run_benchmark  # noqa: E402
from banto_ai.manifest import load_json  # noqa: E402
from tools.chronos2 import (  # noqa: E402
    DEFAULT_REVISION,
    MANIFEST_PATH,
    cache_environment,
    external_cache,
    find_verified_snapshot,
    load_manifest,
    offline_environment,
    verify_installed_package,
)

try:
    from banto_ai.adapters.chronos2 import Chronos2Adapter, Chronos2Config
except ImportError:  # pragma: no cover - adapter is developed in parallel
    Chronos2Adapter = None  # type: ignore[assignment,misc]
    Chronos2Config = None  # type: ignore[assignment,misc]

_external_cache = external_cache
_verify_cached_checkpoint = find_verified_snapshot
_verify_installed_package = verify_installed_package
_offline_environment = offline_environment
_cache_environment = cache_environment
_load_and_validate_license = load_manifest


def make_shared_chronos_factory(manifest: Mapping[str, object], cache_dir: Path):
    """Return a factory that shares one adapter instance across all equipment."""
    if Chronos2Adapter is None or Chronos2Config is None:
        raise RuntimeError("Chronos2Adapter is unavailable")
    shared_adapter: Any | None = None

    def factory(_equipment_id: str, parameters: dict[str, Any]):
        nonlocal shared_adapter
        allowed = {"checkpoint_revision", "device_map", "local_files_only", "context_length", "batch_size", "cross_learning"}
        unknown = set(parameters) - allowed
        if unknown:
            raise ValueError(f"unsupported Chronos-2 parameters: {sorted(unknown)}")
        revision_value = parameters.get("checkpoint_revision", DEFAULT_REVISION)
        if not isinstance(revision_value, str):
            raise ValueError("checkpoint_revision must be a string")
        revision = revision_value
        device_map = parameters.get("device_map", "cpu")
        local_files_only = parameters.get("local_files_only", True)
        if not isinstance(device_map, str):
            raise ValueError("device_map must be a string")
        if not isinstance(local_files_only, bool):
            raise ValueError("local_files_only must be boolean")
        if revision != DEFAULT_REVISION:
            raise ValueError("Chronos-2 benchmark requires the pinned checkpoint revision")
        if device_map != "cpu" or local_files_only is not True:
            raise ValueError("Chronos-2 benchmark requires device_map=cpu and local_files_only=true")
        config_kwargs: dict[str, Any] = {"checkpoint_revision": revision, "cache_dir": str(cache_dir), "device_map": "cpu", "local_files_only": True}
        if "context_length" in parameters:
            context_length = parameters["context_length"]
            if isinstance(context_length, bool) or not isinstance(context_length, int) or not 2 <= context_length <= 8192:
                raise ValueError("context_length must be an integer between 2 and 8192")
            config_kwargs["context_length"] = context_length
        if "batch_size" in parameters:
            batch_size = parameters["batch_size"]
            if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size <= 0:
                raise ValueError("batch_size must be a positive integer")
            config_kwargs["batch_size"] = batch_size
        if "cross_learning" in parameters:
            cross_learning = parameters["cross_learning"]
            if not isinstance(cross_learning, bool):
                raise ValueError("cross_learning must be boolean")
            if cross_learning is not False:
                raise ValueError("Chronos-2 benchmark fixes cross_learning=false")
            config_kwargs["cross_learning"] = False
        if shared_adapter is None:
            shared_adapter = Chronos2Adapter(manifest, config=Chronos2Config(**config_kwargs))
        return shared_adapter

    return factory


make_shared_chronos2_factory = make_shared_chronos_factory


def run_chronos_benchmark(config_path: Path, root: Path, cache_dir: Path, manifest_path: Path = MANIFEST_PATH) -> Path:
    root = Path(root).expanduser().resolve()
    cache = _external_cache(cache_dir, must_exist=True)
    manifest = _load_and_validate_license(manifest_path)
    _verify_cached_checkpoint(cache)
    _verify_installed_package()
    config = load_json(Path(config_path).expanduser().resolve())
    if not isinstance(config, dict):
        raise BenchmarkError("benchmark config must be an object")
    chronos_models = [model for model in config.get("models", []) if isinstance(model, dict) and model.get("name") == "chronos2"]
    if len(chronos_models) != 1:
        raise ValueError("benchmark config must contain exactly one chronos2 model")
    for model in chronos_models:
        if model.get("quantile_policy", "native") != "native":
            raise ValueError("Chronos-2 must use native quantile policy")
    registry = ModelRegistry({"chronos2": make_shared_chronos_factory(manifest, cache)})
    with _cache_environment(cache), _offline_environment():
        return run_benchmark(Path(config_path).expanduser().resolve(), root, registry)


run_chronos2_benchmark = run_chronos_benchmark


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="run_benchmark.py")
    parser.add_argument("--config", required=True)
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--manifest", default=str(MANIFEST_PATH))
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    config = Path(args.config).expanduser()
    if not config.is_absolute():
        config = root / config
    try:
        output = run_chronos_benchmark(config, root, Path(args.cache_dir), Path(args.manifest))
    except (BenchmarkError, ImportError, KeyError, OSError, TypeError, ValueError, RuntimeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"benchmark: PASS ({output})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
