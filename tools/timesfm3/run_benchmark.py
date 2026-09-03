"""研究専用・offline限定のTimesFM 3 benchmark entrypoint。"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import importlib.metadata
import os
from pathlib import Path
import sys
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from banto_ai.adapters.timesfm3 import DEFAULT_REVISION, TimesFM3Adapter, TimesFM3Config  # noqa: E402
from banto_ai.benchmark import BenchmarkError, ModelRegistry, run_benchmark  # noqa: E402
from banto_ai.manifest import load_json  # noqa: E402
from tools.timesfm3 import prepare_checkpoint  # noqa: E402


MANIFEST_PATH = ROOT / "examples" / "manifests" / "model-license-timesfm3.json"


def _external_cache(cache_dir: Path) -> Path:
    cache_dir = cache_dir.expanduser().resolve()
    try:
        cache_dir.relative_to(ROOT)
    except ValueError:
        pass
    else:
        raise ValueError("cache-dir must be outside the repository")
    if not cache_dir.is_dir():
        raise ValueError("cache-dir must be an existing directory; run prepare_checkpoint first")
    return cache_dir


def _load_and_validate_license(path: Path) -> Mapping[str, object]:
    manifest = prepare_checkpoint.load_license_manifest(path.expanduser().resolve())
    if manifest.get("allowed_use") != "research-only":
        raise ValueError("TimesFM 3 benchmark is research-only")
    return manifest


def _verify_cached_checkpoint(cache_dir: Path) -> Path:
    """許可された4ファイルだけを持つ固定revision snapshotを探し、model hashを再検証する。"""
    prepare_checkpoint.load_checkpoint_provenance()
    candidates = []
    for model_path in cache_dir.rglob("model.safetensors"):
        if model_path.parent.name != DEFAULT_REVISION:
            continue
        try:
            prepare_checkpoint._verify_model_artifact(model_path.parent)
        except (OSError, ValueError):
            continue
        candidates.append(model_path.parent)
    if len(candidates) != 1:
        raise ValueError("exactly one verified TimesFM 3 checkpoint snapshot is required in cache-dir")
    return candidates[0]


@contextmanager
def _offline_environment():
    names = ("HF_HUB_OFFLINE", "HF_HUB_DISABLE_TELEMETRY")
    previous = {name: os.environ.get(name) for name in names}
    for name in names:
        os.environ[name] = "1"
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _verify_installed_package() -> None:
    provenance = load_json(ROOT / "environments" / "timesfm3" / "package-provenance.json")
    expected_name = str(provenance["package_name"])
    expected_version = str(provenance["package_version"])
    installed = importlib.metadata.version(expected_name)
    if installed != expected_version:
        raise ValueError(f"installed {expected_name} version {installed} does not match {expected_version}")


def make_shared_timesfm_factory(
    manifest: Mapping[str, object], cache_dir: Path,
):
    """全equipmentで一つのadapterを共有するfactoryを返す。"""
    shared_adapter: TimesFM3Adapter | None = None

    def factory(_equipment_id: str, parameters: dict[str, Any]) -> TimesFM3Adapter:
        nonlocal shared_adapter
        allowed = {"checkpoint_revision", "per_core_batch_size", "device", "local_files_only"}
        unknown = set(parameters) - allowed
        if unknown:
            raise ValueError(f"unsupported TimesFM 3 parameters: {sorted(unknown)}")
        adapter_config = TimesFM3Config(
            checkpoint_revision=str(parameters.get("checkpoint_revision", DEFAULT_REVISION)),
            cache_dir=str(cache_dir),
            per_core_batch_size=int(parameters.get("per_core_batch_size", 1)),
            device=str(parameters.get("device", "cpu")),
            local_files_only=bool(parameters.get("local_files_only", True)),
        )
        if adapter_config.local_files_only is not True or adapter_config.device != "cpu":
            raise ValueError("TimesFM 3 benchmark requires local_files_only=true and device=cpu")
        if adapter_config.checkpoint_revision != DEFAULT_REVISION:
            raise ValueError("TimesFM 3 benchmark requires the pinned checkpoint revision")
        if shared_adapter is None:
            shared_adapter = TimesFM3Adapter(manifest, config=adapter_config)
        return shared_adapter

    return factory


def run_timesfm_benchmark(config_path: Path, root: Path, cache_dir: Path, manifest_path: Path, *, accepted: bool) -> Path:
    if not accepted:
        raise ValueError("--accept-research-only-license is required")
    cache_dir = _external_cache(cache_dir)
    manifest = _load_and_validate_license(manifest_path)
    _verify_cached_checkpoint(cache_dir)
    _verify_installed_package()
    config = load_json(config_path)
    if not isinstance(config, dict):
        raise BenchmarkError("benchmark config must be an object")
    for model in config.get("models", []):
        if model.get("name") == "timesfm3" and model.get("quantile_policy", "native") != "native":
            raise ValueError("TimesFM 3 must use native quantile policy")

    registry = ModelRegistry({"timesfm3": make_shared_timesfm_factory(manifest, cache_dir)})
    with _offline_environment():
        return run_benchmark(config_path, root, registry)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="run_benchmark.py")
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
        output = run_timesfm_benchmark(config, root, Path(args.cache_dir), Path(args.manifest), accepted=args.accept_research_only_license)
    except (BenchmarkError, ImportError, KeyError, OSError, TypeError, ValueError, RuntimeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"benchmark: PASS ({output})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
