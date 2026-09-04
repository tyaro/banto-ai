"""Chronos-2専用commercial-evaluation／offline benchmark matrix入口。"""

from __future__ import annotations

import argparse
from pathlib import Path, PureWindowsPath
import sys
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from banto_ai.benchmark import ModelRegistry  # noqa: E402
from banto_ai.manifest import ManifestValidationError, load_json, validate  # noqa: E402
from banto_ai.matrix import MatrixError, run_matrix  # noqa: E402
from tools.chronos2 import DEFAULT_REVISION  # noqa: E402
from tools.chronos2 import run_benchmark as single_run  # noqa: E402

MANIFEST_PATH = single_run.MANIFEST_PATH
MatrixRunner = Callable[..., Path]


def _path_text(value: str | Path, label: str) -> str:
    if isinstance(value, Path):
        text = value.as_posix()
    elif isinstance(value, str):
        text = value
    else:
        raise MatrixError(f"{label} must be a repository-relative POSIX path")
    if (
        not text
        or Path(text).is_absolute()
        or PureWindowsPath(text).drive
        or "\\" in text
        or any(part in ("", ".", "..") for part in text.split("/"))
    ):
        raise MatrixError(f"{label} must be a repository-relative POSIX path")
    return text


def _repository_file(value: str | Path, root: Path, label: str) -> Path:
    text = _path_text(value, label)
    resolved = (root / text).resolve()
    if resolved == root or root not in resolved.parents:
        raise MatrixError(f"{label} escaped repository")
    if not resolved.is_file():
        raise MatrixError(f"{label} does not exist: {resolved}")
    return resolved


def _validate_matrix_config(matrix_config: Mapping[str, Any], root: Path) -> None:
    try:
        validate(
            dict(matrix_config),
            load_json(root / "schemas" / "benchmark-matrix-config.schema.json"),
        )
    except ManifestValidationError as exc:
        raise MatrixError(f"matrix config is invalid: {exc}") from exc


def _validate_chronos_model(benchmark_config: Mapping[str, Any], axes: Mapping[str, Any]) -> None:
    models = [
        model
        for model in benchmark_config.get("models", [])
        if isinstance(model, dict) and model.get("name") == "chronos2"
    ]
    if len(models) != 1:
        raise MatrixError("Chronos-2 matrix requires exactly one chronos2 model")
    model = models[0]
    if model.get("quantile_policy", "native") != "native":
        raise MatrixError("Chronos-2 must use native quantile policy")
    parameters = model.get("parameters", {})
    if not isinstance(parameters, dict):
        raise MatrixError("Chronos-2 parameters must be an object")
    revision = parameters.get("checkpoint_revision", DEFAULT_REVISION)
    if not isinstance(revision, str) or revision != DEFAULT_REVISION:
        raise MatrixError("Chronos-2 matrix requires the pinned checkpoint revision")
    device_map = parameters.get("device_map", "cpu")
    if not isinstance(device_map, str) or device_map != "cpu":
        raise MatrixError("Chronos-2 matrix requires device_map=cpu")
    local_files_only = parameters.get("local_files_only", True)
    if not isinstance(local_files_only, bool) or local_files_only is not True:
        raise MatrixError("Chronos-2 matrix requires local_files_only=true")
    cross_learning = parameters.get("cross_learning", False)
    if not isinstance(cross_learning, bool) or cross_learning is not False:
        raise MatrixError("Chronos-2 matrix requires cross_learning=false")
    batch_size = parameters.get("batch_size", 1)
    if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size <= 0:
        raise MatrixError("Chronos-2 matrix requires a positive integer batch_size")
    backend_context_limit = parameters.get("context_length", 2048)
    if (
        isinstance(backend_context_limit, bool)
        or not isinstance(backend_context_limit, int)
        or not 2 <= backend_context_limit <= 8192
    ):
        raise MatrixError("Chronos-2 context_length must be an integer between 2 and 8192")
    context_lengths = axes.get("context_lengths", [])
    if any(
        isinstance(length, bool)
        or not isinstance(length, int)
        or length > backend_context_limit
        for length in context_lengths
    ):
        raise MatrixError("matrix context_lengths must not exceed the Chronos-2 backend context_length")


def run_chronos_matrix(
    config_path: str | Path,
    root: Path,
    cache_dir: Path,
    manifest_path: Path = MANIFEST_PATH,
    *,
    matrix_runner: MatrixRunner = run_matrix,
) -> Path:
    root = Path(root).expanduser().resolve()
    resolved_config = _repository_file(config_path, root, "matrix config path")
    matrix_config = load_json(resolved_config)
    if not isinstance(matrix_config, dict):
        raise MatrixError("matrix config must be an object")
    _validate_matrix_config(matrix_config, root)
    _repository_file(matrix_config["generator_config_path"], root, "generator_config_path")
    benchmark_path = _repository_file(
        matrix_config["benchmark_config_path"], root, "benchmark_config_path"
    )
    benchmark_config = load_json(benchmark_path)
    if not isinstance(benchmark_config, dict):
        raise MatrixError("benchmark config must be an object")
    _validate_chronos_model(benchmark_config, matrix_config["axes"])

    cache = single_run._external_cache(cache_dir, must_exist=True)
    manifest = single_run._load_and_validate_license(manifest_path)
    if manifest.get("allowed_use") != "commercial-evaluation":
        raise MatrixError("Chronos-2 matrix is limited to commercial-evaluation")
    single_run._verify_cached_checkpoint(cache)
    single_run._verify_installed_package()
    shared_factory = single_run.make_shared_chronos_factory(manifest, cache)
    registry = ModelRegistry({"chronos2": shared_factory})
    with single_run._cache_environment(cache), single_run._offline_environment():
        return matrix_runner(resolved_config, root, registry)


run_chronos2_matrix = run_chronos_matrix


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="run_matrix.py")
    parser.add_argument("--config", required=True)
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--manifest", default=str(MANIFEST_PATH))
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args(argv)
    try:
        output = run_chronos_matrix(
            args.config,
            Path(args.root),
            Path(args.cache_dir),
            Path(args.manifest),
        )
    except (ImportError, KeyError, MatrixError, OSError, TypeError, ValueError, RuntimeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"Chronos-2 benchmark matrix: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
