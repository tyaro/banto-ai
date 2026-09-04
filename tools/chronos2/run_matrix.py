"""Chronos-2専用offline benchmark matrix入口。"""

from __future__ import annotations

import argparse
from pathlib import Path, PureWindowsPath
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from banto_ai.benchmark import ModelRegistry  # noqa: E402
from banto_ai.matrix import MatrixError, run_matrix  # noqa: E402
from banto_ai.manifest import load_json  # noqa: E402
from tools.chronos2 import MANIFEST_PATH, cache_environment, external_cache, find_verified_snapshot, load_manifest, offline_environment, verify_installed_package  # noqa: E402
from tools.chronos2 import run_benchmark as single_run  # noqa: E402

_external_cache = external_cache
_verify_cached_checkpoint = find_verified_snapshot
_verify_installed_package = verify_installed_package
_offline_environment = offline_environment
_cache_environment = cache_environment


def _benchmark_config_path(matrix_config: dict, root: Path) -> Path:
    relative = matrix_config.get("benchmark_config_path")
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or PureWindowsPath(relative).drive or "\\" in relative or any(part in ("", ".", "..") for part in relative.split("/")):
        raise MatrixError("benchmark_config_path must be a repository-relative POSIX path")
    resolved = (root / relative).resolve()
    if resolved == root or root not in resolved.parents or not resolved.is_file():
        raise MatrixError("benchmark_config_path must identify a file inside the repository")
    return resolved


def run_chronos_matrix(config_path: Path, root: Path, cache_dir: Path, manifest_path: Path = MANIFEST_PATH) -> Path:
    root = Path(root).expanduser().resolve()
    config_path = Path(config_path).expanduser()
    if not config_path.is_absolute():
        config_path = root / config_path
    config_path = config_path.resolve()
    cache = _external_cache(cache_dir, must_exist=True)
    manifest = load_manifest(manifest_path)
    _verify_cached_checkpoint(cache)
    _verify_installed_package()
    matrix_config = load_json(config_path)
    if not isinstance(matrix_config, dict):
        raise MatrixError("matrix config must be an object")
    benchmark_path = _benchmark_config_path(matrix_config, root)
    benchmark_config = load_json(benchmark_path)
    if not isinstance(benchmark_config, dict):
        raise MatrixError("benchmark config must be an object")
    models = [model for model in benchmark_config.get("models", []) if isinstance(model, dict) and model.get("name") == "chronos2"]
    if len(models) != 1:
        raise ValueError("Chronos-2 matrix requires exactly one chronos2 model")
    if models[0].get("quantile_policy", "native") != "native":
        raise ValueError("Chronos-2 must use native quantile policy")
    registry = ModelRegistry({"chronos2": single_run.make_shared_chronos_factory(manifest, cache)})
    with _cache_environment(cache), _offline_environment():
        return run_matrix(config_path, root, registry)


run_chronos2_matrix = run_chronos_matrix


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="run_matrix.py")
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
        output = run_chronos_matrix(config, root, Path(args.cache_dir), Path(args.manifest))
    except (ImportError, KeyError, MatrixError, OSError, TypeError, ValueError, RuntimeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"Chronos-2 benchmark matrix: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
