"""research-only・offline限定のTimesFM 3 matrix entrypoint。"""

from __future__ import annotations

import argparse
from pathlib import Path, PureWindowsPath
import sys
from typing import Callable

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from banto_ai.benchmark import ModelRegistry  # noqa: E402
from banto_ai.manifest import load_json  # noqa: E402
from banto_ai.matrix import MatrixError, TIMESFM_RESEARCH_NOTICE, run_matrix  # noqa: E402
from tools.timesfm3 import run_benchmark as single_run  # noqa: E402


MANIFEST_PATH = single_run.MANIFEST_PATH
MatrixRunner = Callable[..., Path]


def _benchmark_config_path(matrix_config: dict, config_path: Path, root: Path) -> Path:
    relative = matrix_config.get("benchmark_config_path")
    if (
        not isinstance(relative, str)
        or not relative
        or Path(relative).is_absolute()
        or PureWindowsPath(relative).drive
        or "\\" in relative
        or any(part in ("", ".", "..") for part in relative.split("/"))
    ):
        raise MatrixError("benchmark_config_path must be a repository-relative POSIX path")
    resolved = (root / relative).resolve()
    if resolved == root or root not in resolved.parents:
        raise MatrixError("benchmark_config_path escaped repository")
    if not resolved.is_file():
        raise MatrixError(f"benchmark config does not exist: {resolved}")
    if not config_path.is_file():
        raise MatrixError(f"matrix config does not exist: {config_path}")
    return resolved


def run_timesfm_matrix(
    config_path: Path,
    root: Path,
    cache_dir: Path,
    manifest_path: Path,
    *,
    accepted: bool,
    matrix_runner: MatrixRunner = run_matrix,
) -> Path:
    root = Path(root).expanduser().resolve()
    config_path = Path(config_path).expanduser()
    if not config_path.is_absolute():
        config_path = (root / config_path).resolve()
    else:
        config_path = config_path.resolve()
    if not accepted:
        raise ValueError("--accept-research-only-license is required")
    cache_dir = single_run._external_cache(cache_dir)
    manifest = single_run._load_and_validate_license(manifest_path)
    single_run._verify_cached_checkpoint(cache_dir)
    single_run._verify_installed_package()

    matrix_config = load_json(config_path)
    if not isinstance(matrix_config, dict):
        raise MatrixError("matrix config must be an object")
    benchmark_path = _benchmark_config_path(matrix_config, config_path, root)
    benchmark_config = load_json(benchmark_path)
    if not isinstance(benchmark_config, dict):
        raise MatrixError("benchmark config must be an object")
    timesfm_models = [
        model
        for model in benchmark_config.get("models", [])
        if isinstance(model, dict) and model.get("name") == "timesfm3"
    ]
    if len(timesfm_models) != 1:
        raise ValueError("TimesFM matrix requires exactly one timesfm3 model")
    if timesfm_models[0].get("quantile_policy", "native") != "native":
        raise ValueError("TimesFM 3 must use native quantile policy")

    shared_factory = single_run.make_shared_timesfm_factory(manifest, cache_dir)
    registry = ModelRegistry({"timesfm3": shared_factory})
    with single_run._offline_environment():
        return matrix_runner(
            config_path,
            root,
            registry,
            research_only_notice=TIMESFM_RESEARCH_NOTICE,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="run_matrix.py")
    parser.add_argument("--config", required=True)
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--manifest", default=str(MANIFEST_PATH))
    parser.add_argument("--accept-research-only-license", action="store_true", required=True)
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    config = Path(args.config).expanduser()
    if not config.is_absolute():
        config = (root / config).resolve()
    try:
        output = run_timesfm_matrix(
            config,
            root,
            Path(args.cache_dir),
            Path(args.manifest),
            accepted=args.accept_research_only_license,
        )
    except (ImportError, KeyError, MatrixError, OSError, TypeError, ValueError, RuntimeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"TimesFM benchmark matrix: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
