"""Toto 2.0 4M commercial-evaluation／offline benchmark matrix入口。"""

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

from banto_ai.benchmark import (  # noqa: E402
    BenchmarkError,
    ModelRegistry,
    _validate_config_contract,
)
from banto_ai.generator import GeneratorError, _validate_config as validate_generator_config  # noqa: E402
from banto_ai.manifest import ManifestValidationError, load_json, validate  # noqa: E402
from banto_ai.matrix import MatrixError, run_matrix  # noqa: E402
from tools.toto2 import DEFAULT_REVISION  # noqa: E402
from tools.toto2 import run_benchmark as single_run  # noqa: E402

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


def _validate_toto_model(
    benchmark_config: Mapping[str, Any], axes: Mapping[str, Any]
) -> None:
    if benchmark_config.get("known_future_covariate_ids", []) != []:
        raise MatrixError("Toto 2.0 matrix requires known_future_covariate_ids=[]")
    models = [
        model
        for model in benchmark_config.get("models", [])
        if isinstance(model, dict) and model.get("name") == "toto2"
    ]
    if len(models) != 1:
        raise MatrixError("Toto 2.0 matrix requires exactly one toto2 model")
    model = models[0]
    if model.get("quantile_policy") != "native":
        raise MatrixError("Toto 2.0 matrix requires native quantile policy")
    parameters = model.get("parameters")
    if not isinstance(parameters, dict):
        raise MatrixError("Toto 2.0 parameters must be an object")
    revision = parameters.get("checkpoint_revision")
    if not isinstance(revision, str) or revision != DEFAULT_REVISION:
        raise MatrixError("Toto 2.0 matrix requires the pinned checkpoint revision")
    if parameters.get("device") != "cpu":
        raise MatrixError("Toto 2.0 matrix requires device=cpu")
    if parameters.get("batch_size") != 1:
        raise MatrixError("Toto 2.0 matrix requires batch_size=1")
    if parameters.get("local_files_only") is not True:
        raise MatrixError("Toto 2.0 matrix requires local_files_only=true")
    if parameters.get("patch_size") != 32:
        raise MatrixError("Toto 2.0 matrix requires patch_size=32")
    context_lengths = axes.get("context_lengths", [])
    if any(
        isinstance(length, bool) or not isinstance(length, int) or length < 32
        for length in context_lengths
    ):
        raise MatrixError("Toto 2.0 matrix context_lengths must be integers >= 32")


def run_toto2_matrix(
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
    generator_path = _repository_file(
        matrix_config["generator_config_path"], root, "generator_config_path"
    )
    generator_config = load_json(generator_path)
    if not isinstance(generator_config, dict):
        raise MatrixError("generator config must be an object")
    try:
        validate_generator_config(
            generator_config,
            root / "schemas" / "synthetic-generator-config.schema.json",
        )
    except (GeneratorError, ManifestValidationError) as exc:
        raise MatrixError(f"generator config is invalid: {exc}") from exc
    benchmark_path = _repository_file(
        matrix_config["benchmark_config_path"], root, "benchmark_config_path"
    )
    benchmark_config = load_json(benchmark_path)
    if not isinstance(benchmark_config, dict):
        raise MatrixError("benchmark config must be an object")
    _validate_toto_model(benchmark_config, matrix_config["axes"])
    validation_registry = ModelRegistry({"toto2": lambda _equipment_id, _parameters: object()})
    try:
        _validate_config_contract(benchmark_config, root, validation_registry)
    except BenchmarkError as exc:
        raise MatrixError(f"base benchmark config is invalid: {exc}") from exc

    cache = single_run._external_cache(cache_dir, must_exist=True)
    manifest = single_run._load_and_validate_license(manifest_path)
    if manifest.get("allowed_use") != "commercial-evaluation":
        raise MatrixError("Toto 2.0 matrix is limited to commercial-evaluation")
    single_run._verify_cached_checkpoint(cache)
    single_run._verify_installed_package()
    shared_factory = single_run.make_shared_toto_factory(manifest, cache)
    registry = ModelRegistry({"toto2": shared_factory})
    with single_run._cache_environment(cache), single_run._offline_environment():
        return matrix_runner(resolved_config, root, registry)


run_toto_matrix = run_toto2_matrix


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="run_matrix.py")
    parser.add_argument("--config", required=True)
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--manifest", default=str(MANIFEST_PATH))
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args(argv)
    try:
        output = run_toto2_matrix(
            args.config,
            Path(args.root),
            Path(args.cache_dir),
            Path(args.manifest),
        )
    except (ImportError, KeyError, MatrixError, OSError, TypeError, ValueError, RuntimeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"Toto 2.0 benchmark matrix: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
