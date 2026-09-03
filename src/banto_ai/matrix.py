"""単一benchmarkをseed／horizon／contextで反復する安全なmatrix runner。"""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import statistics
import tempfile
from pathlib import Path, PureWindowsPath
from typing import Any, Callable, Mapping

from .benchmark import (
    BenchmarkError,
    ModelRegistry,
    QualityChecker,
    _revision,
    _validate_config_contract,
    run_benchmark,
)
from .generator import GeneratorError, _validate_config as validate_generator_config
from .generator import generate_synthetic
from .manifest import ManifestValidationError, load_json, validate
from .quality import DatasetQualityError, check_dataset


MATRIX_SCHEMA_VERSION = "0.1"
EXPANSION_ORDER = ("seed", "horizon", "context_length")
METRIC_NAMES = (
    "mae",
    "rmse",
    "mase",
    "wis",
    "nominal_interval_coverage",
    "interval_width",
)
TIMESFM_RESEARCH_NOTICE = (
    "TimesFM 3.0 weights are research-only/non-commercial; matrix results are not "
    "eligible for product or customer deployment."
)

Generator = Callable[[Path, str | Path | None, Path], Path]
BenchmarkRunner = Callable[
    [Path, Path, ModelRegistry | None, QualityChecker | None], Path
]


class MatrixError(ValueError):
    """matrix設定、出力契約、または集計契約に違反した。"""


class MatrixProvenanceError(MatrixError):
    """実行中に入力またはcode revisionの不変性が失われた。"""


def _canonical_json(payload: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _write_json(path: Path, payload: Mapping[str, Any]) -> str:
    content = _canonical_json(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return hashlib.sha256(content).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_object_snapshot(path: Path, label: str) -> tuple[dict[str, Any], str]:
    """一度だけ取得したraw bytesをparseし、その同じbytesのhashを返す。"""
    try:
        raw = path.read_bytes()

        def reject_constant(value: str) -> None:
            raise MatrixError(f"{label} contains a non-finite JSON constant: {value}")

        def parse_float(value: str) -> float:
            parsed = float(value)
            if not math.isfinite(parsed):
                raise MatrixError(f"{label} contains a non-finite JSON number: {value}")
            return parsed

        value = json.loads(
            raw.decode("utf-8"),
            parse_constant=reject_constant,
            parse_float=parse_float,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MatrixError(f"{label} is not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise MatrixError(f"{label} must be a JSON object")
    return value, hashlib.sha256(raw).hexdigest()


def _validate_relative_path(value: str, label: str) -> None:
    if (
        not isinstance(value, str)
        or not value
        or value.startswith("/")
        or "\\" in value
        or PureWindowsPath(value).drive
    ):
        raise MatrixError(f"{label} must be a repository-relative POSIX path")
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise MatrixError(f"{label} must not contain empty, dot, or traversal segments")


def _repo_path(root: Path, value: str, label: str) -> Path:
    _validate_relative_path(value, label)
    resolved = (root / value).resolve()
    if resolved == root or root not in resolved.parents:
        raise MatrixError(f"{label} must remain inside the repository")
    return resolved


def _artifact_output_path(root: Path, value: str, label: str) -> Path:
    resolved = _repo_path(root, value, label)
    artifact_root = (root / "artifacts").resolve()
    if resolved == artifact_root or artifact_root not in resolved.parents:
        raise MatrixError(f"{label} must be below artifacts and must not be artifacts itself")
    return resolved


def _relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError as exc:
        raise MatrixError(f"path escaped repository: {path}") from exc


def _joined_path(prefix: str, *parts: str) -> str:
    return "/".join((prefix.rstrip("/"), *parts))


def _paths_overlap(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


def _validate_axes(config: Mapping[str, Any]) -> None:
    axes = config["axes"]
    for name in ("seeds", "horizons", "context_lengths"):
        values = axes[name]
        if len(values) != len(set(values)):
            raise MatrixError(f"axes.{name} must not contain duplicates")


def expand_cells(config: Mapping[str, Any]) -> tuple[tuple[int, int, int], ...]:
    """宣言順を保ち、seed→horizon→context_lengthの順で展開する。"""
    axes = config["axes"]
    return tuple(
        (int(seed), int(horizon), int(context_length))
        for seed in axes["seeds"]
        for horizon in axes["horizons"]
        for context_length in axes["context_lengths"]
    )


def _cell_id(seed: int, horizon: int, context_length: int) -> str:
    return f"seed-{seed}--horizon-{horizon}--context-{context_length}"


def _load_object(path: Path, label: str) -> dict[str, Any]:
    value = load_json(path)
    if not isinstance(value, dict):
        raise MatrixError(f"{label} must be a JSON object")
    return value


def _validate_matrix_config(config: dict[str, Any], root: Path) -> None:
    try:
        validate(config, load_json(root / "schemas" / "benchmark-matrix-config.schema.json"))
    except ManifestValidationError as exc:
        raise MatrixError(str(exc)) from exc
    _validate_axes(config)
    for label in (
        "generator_config_path",
        "benchmark_config_path",
        "dataset_output_root",
        "benchmark_output_root",
        "matrix_output_dir",
    ):
        _validate_relative_path(config[label], label)


def _materialize(
    config: dict[str, Any],
    root: Path,
    registry: ModelRegistry,
) -> tuple[
    Path,
    Path,
    dict[str, Any],
    dict[str, Any],
    dict[str, str],
    list[dict[str, Any]],
    list[dict[str, Any]],
    Path,
]:
    generator_path = _repo_path(
        root, config["generator_config_path"], "generator_config_path"
    )
    benchmark_path = _repo_path(
        root, config["benchmark_config_path"], "benchmark_config_path"
    )
    if not generator_path.is_file():
        raise MatrixError("generator_config_path must be an existing file")
    if not benchmark_path.is_file():
        raise MatrixError("benchmark_config_path must be an existing file")

    base_generator, generator_sha256 = _load_object_snapshot(
        generator_path, "generator config"
    )
    base_benchmark, benchmark_sha256 = _load_object_snapshot(
        benchmark_path, "benchmark config"
    )
    try:
        validate_generator_config(
            base_generator, root / "schemas" / "synthetic-generator-config.schema.json"
        )
        _validate_config_contract(base_benchmark, root, registry)
    except (BenchmarkError, GeneratorError, ManifestValidationError) as exc:
        raise MatrixError(f"base config is invalid: {exc}") from exc
    matrix_id = config["matrix_id"]
    dataset_matrix_relative = _joined_path(config["dataset_output_root"], matrix_id)
    benchmark_matrix_relative = _joined_path(config["benchmark_output_root"], matrix_id)
    dataset_matrix_root = _artifact_output_path(
        root, dataset_matrix_relative, "dataset matrix output"
    )
    benchmark_matrix_root = _artifact_output_path(
        root, benchmark_matrix_relative, "benchmark matrix output"
    )
    matrix_output = _artifact_output_path(root, config["matrix_output_dir"], "matrix_output_dir")

    top_outputs = (dataset_matrix_root, benchmark_matrix_root, matrix_output)
    for index, left in enumerate(top_outputs):
        for right in top_outputs[index + 1 :]:
            if _paths_overlap(left, right):
                raise MatrixError("dataset, benchmark, and matrix outputs must be disjoint")
    for output in top_outputs:
        if output.exists():
            raise MatrixError(f"refusing to reuse existing matrix output: {output}")

    dataset_plans: list[dict[str, Any]] = []
    for seed in config["axes"]["seeds"]:
        dataset_id = f"{base_generator['dataset_id']}--{matrix_id}--seed-{seed}"
        dataset_relative = _joined_path(dataset_matrix_relative, f"seed-{seed}")
        dataset_path = _artifact_output_path(root, dataset_relative, "dataset output")
        generated = dict(base_generator)
        generated["dataset_id"] = dataset_id
        generated["seed"] = seed
        try:
            validate_generator_config(
                generated, root / "schemas" / "synthetic-generator-config.schema.json"
            )
        except (GeneratorError, ManifestValidationError) as exc:
            raise MatrixError(f"materialized generator config is invalid: {exc}") from exc
        dataset_plans.append(
            {
                "seed": seed,
                "dataset_id": dataset_id,
                "dataset_path": dataset_path,
                "dataset_relative": dataset_relative,
                "config": generated,
                "config_relative": _joined_path(
                    config["matrix_output_dir"], "configs", "generators", f"seed-{seed}.json"
                ),
            }
        )

    dataset_by_seed = {item["seed"]: item for item in dataset_plans}
    cell_plans: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_paths: set[Path] = set()
    for seed, horizon, context_length in expand_cells(config):
        identifier = _cell_id(seed, horizon, context_length)
        if identifier in seen_ids:
            raise MatrixError(f"duplicate materialized cell ID: {identifier}")
        seen_ids.add(identifier)
        dataset = dataset_by_seed[seed]
        run_id = f"{base_benchmark['run_id']}--{matrix_id}--{identifier}"
        output_relative = _joined_path(benchmark_matrix_relative, identifier)
        output_path = _artifact_output_path(root, output_relative, "cell output")
        if output_path in seen_paths:
            raise MatrixError(f"duplicate materialized cell output: {output_relative}")
        seen_paths.add(output_path)
        materialized = dict(base_benchmark)
        materialized.update(
            run_id=run_id,
            dataset_path=dataset["dataset_relative"],
            output_dir=output_relative,
            seed=seed,
            horizon=horizon,
            context_length=context_length,
        )
        try:
            _validate_config_contract(materialized, root, registry)
        except BenchmarkError as exc:
            raise MatrixError(f"materialized benchmark config is invalid: {exc}") from exc
        cell_plans.append(
            {
                "cell_id": identifier,
                "run_id": run_id,
                "seed": seed,
                "horizon": horizon,
                "context_length": context_length,
                "dataset": dataset,
                "output_path": output_path,
                "output_relative": output_relative,
                "config": materialized,
                "config_relative": _joined_path(
                    config["matrix_output_dir"], "configs", "benchmarks", f"{identifier}.json"
                ),
            }
        )

    planned_paths = [item["dataset_path"] for item in dataset_plans]
    planned_paths.extend(item["output_path"] for item in cell_plans)
    planned_paths.append(matrix_output)
    if len(planned_paths) != len(set(planned_paths)):
        raise MatrixError("materialized output paths must be unique")
    if any(path.exists() for path in planned_paths):
        raise MatrixError("one or more materialized outputs already exist")
    return (
        generator_path,
        benchmark_path,
        base_generator,
        base_benchmark,
        {
            "generator": generator_sha256,
            "benchmark": benchmark_sha256,
        },
        dataset_plans,
        cell_plans,
        matrix_output,
    )


def _dataset_identity(
    dataset_path: Path, expected_dataset_id: str,
) -> tuple[str, str, dict[str, Any]]:
    manifest = _load_object(dataset_path / "dataset-manifest.json", "dataset manifest")
    if manifest.get("dataset_id") != expected_dataset_id:
        raise MatrixError("generated dataset_id does not match materialized config")
    fingerprint_name = manifest.get("fingerprint_path")
    if not isinstance(fingerprint_name, str):
        raise MatrixError("dataset manifest fingerprint_path is invalid")
    fingerprint_path = (dataset_path / fingerprint_name).resolve()
    if fingerprint_path.parent != dataset_path.resolve():
        raise MatrixError("dataset fingerprint must be directly inside its dataset directory")
    fingerprint = _load_object(fingerprint_path, "dataset fingerprint")
    digest = fingerprint.get("dataset_fingerprint")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise MatrixError("generated dataset fingerprint is invalid")
    data_name = manifest.get("data_path")
    if (
        not isinstance(data_name, str)
        or not data_name
        or "\\" in data_name
        or PureWindowsPath(data_name).drive
        or len(data_name.split("/")) != 1
        or data_name in (".", "..")
    ):
        raise MatrixError("dataset data_path must name one direct child file")
    observations_path = (dataset_path / data_name).resolve()
    if observations_path.parent != dataset_path.resolve() or not observations_path.is_file():
        raise MatrixError("dataset observations file must exist directly inside dataset directory")
    observations_sha256 = _file_sha256(observations_path)
    return digest, observations_sha256, manifest


def _merge_target_units(
    known_units: dict[str, str],
    manifest: Mapping[str, Any],
    configured_targets: list[str] | None,
) -> None:
    requested = None
    if configured_targets is not None:
        requested = {value.rsplit(".", 1)[-1] for value in configured_targets}
    found: set[str] = set()
    for signal in manifest.get("signals", []):
        if not isinstance(signal, dict) or signal.get("role") != "target":
            continue
        signal_id = signal.get("signal_id")
        unit = signal.get("unit")
        if not isinstance(signal_id, str) or not isinstance(unit, str) or not unit:
            raise MatrixError("target signal metadata is invalid")
        target_key = signal_id.rsplit(".", 1)[-1]
        if requested is not None and target_key not in requested:
            continue
        found.add(target_key)
        previous = known_units.setdefault(target_key, unit)
        if previous != unit:
            raise MatrixError(
                f"logical target {target_key} has mixed units: {previous!r} and {unit!r}"
            )
    if requested is not None and found != requested:
        missing = sorted(requested - found)
        raise MatrixError(f"configured target metadata was not found: {missing}")
    if not found:
        raise MatrixError("dataset contains no target metadata for matrix aggregation")


def _copy_quality(quality: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(quality, ensure_ascii=False, allow_nan=False))


def _validate_cell_result(
    result: dict[str, Any],
    plan: Mapping[str, Any],
    dataset_fingerprint: str,
    start_revision: Mapping[str, Any],
    root: Path,
) -> None:
    try:
        validate(result, load_json(root / "schemas" / "benchmark-result.schema.json"))
    except ManifestValidationError as exc:
        raise MatrixError(f"cell result does not satisfy benchmark-result 0.2: {exc}") from exc
    if result.get("schema_version") != "0.2":
        raise MatrixError("cell result must use benchmark-result schema 0.2")
    if result.get("run_id") != plan["run_id"]:
        raise MatrixError("cell result run_id does not match materialized config")
    if result.get("dataset_fingerprint") != dataset_fingerprint:
        raise MatrixError("cell result dataset fingerprint does not match generated dataset")
    if result.get("seed") != plan["seed"]:
        raise MatrixError("cell result seed does not match matrix cell")
    if result.get("run_config") != plan["config"]:
        raise MatrixError("cell result run_config does not match materialized config")
    if result.get("code_revision") != start_revision:
        raise MatrixProvenanceError(
            "cell code_revision does not match matrix start revision"
        )


def _finite_metric(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise MatrixError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise MatrixError(f"{label} must be finite and non-negative")
    return result


def _summary_statistic(values: list[float]) -> dict[str, float | None]:
    return {
        "mean": statistics.fmean(values),
        "min": min(values),
        "max": max(values),
        "sample_stddev": statistics.stdev(values) if len(values) > 1 else None,
    }


def _macro_summary(
    completed: list[tuple[Mapping[str, Any], Mapping[str, Any]]],
    expected_units: Mapping[str, str],
) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, int, int], list[dict[str, Any]]] = {}
    for plan, result in completed:
        seen: set[tuple[str, str]] = set()
        for row in result["metrics"]["by_model_target"]:
            model = row["model"]
            target = row["target_signal_key"]
            unit = row["unit"]
            row_key = (model, target)
            if row_key in seen:
                raise MatrixError(f"cell contains duplicate model-target metric: {row_key}")
            seen.add(row_key)
            expected = expected_units.get(target)
            if expected is None or expected != unit:
                raise MatrixError(
                    f"logical target {target} has unexpected unit {unit!r}; expected {expected!r}"
                )
            metrics = row["metrics"]
            count = metrics.get("count")
            if not isinstance(count, int) or isinstance(count, bool) or count < 1:
                raise MatrixError("model-target metric count must be a positive integer")
            values = {
                name: _finite_metric(metrics.get(name), f"{model}/{target}/{name}")
                for name in METRIC_NAMES
            }
            values["count"] = count
            key = (model, target, unit, plan["horizon"], plan["context_length"])
            groups.setdefault(key, []).append(values)

    output: list[dict[str, Any]] = []
    for key in sorted(groups):
        model, target, unit, horizon, context_length = key
        rows = groups[key]
        output.append(
            {
                "model": model,
                "target_signal_key": target,
                "unit": unit,
                "horizon": horizon,
                "context_length": context_length,
                "cell_count": len(rows),
                "total_point_count": sum(int(row["count"]) for row in rows),
                "metrics": {
                    name: _summary_statistic([float(row[name]) for row in rows])
                    for name in METRIC_NAMES
                },
            }
        )
    return output


def _format_statistic(value: Mapping[str, Any]) -> str:
    stddev = "-" if value["sample_stddev"] is None else f"{value['sample_stddev']:.6g}"
    return (
        f"{value['mean']:.6g} [{value['min']:.6g}, {value['max']:.6g}], "
        f"sd={stddev}"
    )


def _summary_markdown(result: Mapping[str, Any]) -> str:
    lines = [
        "# Benchmark matrix結果",
        "",
        "合成データ上の研究用結果であり、実設備性能や製品採用を示しません。",
        "",
        "## 概要",
        "",
        f"- matrix ID: `{result['matrix_id']}`",
        f"- status: `{result['status']}`",
        "- 展開順: `seed → horizon → context_length`（各axisの宣言順を保持）",
        f"- 全cell: {result['counts']['total_cells']}",
        f"- 成功: {result['counts']['successful_cells']}",
        f"- 部分成功: {result['counts']['partial_cells']}",
        f"- 失敗: {result['counts']['failed_cells']}",
        f"- 開始code revision: `{result['code_revision']['head']}`",
        f"- generator base SHA-256: `{result['base_configs']['generator']['sha256']}`",
        f"- benchmark base SHA-256: `{result['base_configs']['benchmark']['sha256']}`",
        "",
        "## dataset",
        "",
        "| seed | dataset ID | fingerprint | observations SHA-256 | quality |",
        "| ---: | --- | --- | --- | --- |",
    ]
    for dataset in result["datasets"]:
        lines.append(
            f"| {dataset['seed']} | `{dataset['dataset_id']}` | "
            f"`{dataset['dataset_fingerprint']}` | `{dataset['observations_sha256']}` | "
            f"`{dataset['quality_gate']['status']}` |"
        )

    lines.extend(
        [
            "",
            "## 成功・部分成功cell",
            "",
            "| cell ID | status | seed | horizon | context | result |",
            "| --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    completed = [cell for cell in result["cells"] if cell["status"] != "failed"]
    if completed:
        for cell in completed:
            lines.append(
                f"| `{cell['cell_id']}` | `{cell['status']}` | {cell['seed']} | "
                f"{cell['horizon']} | {cell['context_length']} | `{cell['result_path']}` |"
            )
    else:
        lines.append("| - | - | - | - | - | - |")

    lines.extend(
        [
            "",
            "## 失敗cell",
            "",
            "| cell ID | seed | horizon | context | failure |",
            "| --- | ---: | ---: | ---: | --- |",
        ]
    )
    failed = [cell for cell in result["cells"] if cell["status"] == "failed"]
    if failed:
        for cell in failed:
            reason = str(cell["failure"]["reason"]).replace("|", "\\|").replace("\n", " ")
            lines.append(
                f"| `{cell['cell_id']}` | {cell['seed']} | {cell['horizon']} | "
                f"{cell['context_length']} | {reason} |"
            )
    else:
        lines.append("| - | - | - | - | なし |")

    lines.extend(
        [
            "",
            "## seed間cell-macro summary",
            "",
            "各cellの`by_model_target` metricを同じ重みで要約したmacro summaryです。"
            "raw predictionをまとめ直したpooled metricではありません。",
            "",
            "| model | target | unit | horizon | context | cells | points | MAE | RMSE | MASE | WIS | coverage | width |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- | --- | --- |",
        ]
    )
    if result["macro_summary"]:
        for row in result["macro_summary"]:
            values = [
                _format_statistic(row["metrics"][name])
                for name in METRIC_NAMES
            ]
            lines.append(
                f"| `{row['model']}` | `{row['target_signal_key']}` | `{row['unit']}` | "
                f"{row['horizon']} | {row['context_length']} | {row['cell_count']} | "
                f"{row['total_point_count']} | " + " | ".join(values) + " |"
            )
    else:
        lines.append("| - | - | - | - | - | - | - | - | - | - | - | - | - |")

    lines.extend(["", "## 限界", ""])
    lines.extend(f"- {item}" for item in result["limitations"])
    if result["research_only_notice"]:
        lines.extend(["", f"- TimesFM注意: {result['research_only_notice']}"])
    return "\n".join(lines) + "\n"


def run_matrix(
    config_path: Path,
    root: Path,
    model_registry: ModelRegistry | None = None,
    *,
    generator: Generator = generate_synthetic,
    quality_checker: QualityChecker = check_dataset,
    benchmark_runner: BenchmarkRunner = run_benchmark,
    research_only_notice: str | None = None,
) -> Path:
    """matrixを安全に展開し、既存単一runをcellごとに実行する。"""
    root = root.resolve()
    config_path = Path(config_path).expanduser()
    if not config_path.is_absolute():
        config_path = (root / config_path).resolve()
    else:
        config_path = config_path.resolve()
    start_revision = _revision(root)
    config = _load_object(config_path, "matrix config")
    _validate_matrix_config(config, root)
    registry = model_registry or ModelRegistry()
    (
        generator_path,
        benchmark_path,
        _base_generator,
        base_benchmark,
        base_config_hashes,
        dataset_plans,
        cell_plans,
        matrix_output,
    ) = _materialize(config, root, registry)

    contains_timesfm = any(
        model.get("name") == "timesfm3" for model in base_benchmark.get("models", [])
    )
    if contains_timesfm and research_only_notice is None:
        research_only_notice = TIMESFM_RESEARCH_NOTICE

    matrix_output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{config['matrix_id']}.", dir=matrix_output.parent)
    )
    completed: list[tuple[Mapping[str, Any], Mapping[str, Any]]] = []
    datasets: list[dict[str, Any]] = []
    cells: list[dict[str, Any]] = []
    quality_cache: dict[Path, dict[str, Any]] = {}
    fingerprint_by_seed: dict[int, str] = {}
    observations_by_seed: dict[int, str] = {}
    units: dict[str, str] = {}

    try:
        generator_config_paths: dict[int, Path] = {}
        benchmark_config_paths: dict[str, Path] = {}
        generator_config_hashes: dict[int, str] = {}
        benchmark_config_hashes: dict[str, str] = {}
        for plan in dataset_plans:
            relative_inside_matrix = Path("configs") / "generators" / f"seed-{plan['seed']}.json"
            path = temporary / relative_inside_matrix
            generator_config_paths[plan["seed"]] = path
            generator_config_hashes[plan["seed"]] = _write_json(path, plan["config"])
        for plan in cell_plans:
            relative_inside_matrix = Path("configs") / "benchmarks" / f"{plan['cell_id']}.json"
            path = temporary / relative_inside_matrix
            benchmark_config_paths[plan["cell_id"]] = path
            benchmark_config_hashes[plan["cell_id"]] = _write_json(path, plan["config"])

        for plan in dataset_plans:
            generated_path = generator(
                generator_config_paths[plan["seed"]], plan["dataset_relative"], root
            )
            if generated_path.resolve() != plan["dataset_path"]:
                raise MatrixError("generator returned an unexpected dataset path")
            quality = quality_checker(plan["dataset_path"], root)
            if not isinstance(quality, dict) or quality.get("status") != "pass":
                raise MatrixError("dataset quality gate did not return pass")
            fingerprint, observations_sha256, manifest = _dataset_identity(
                plan["dataset_path"], plan["dataset_id"]
            )
            if fingerprint in fingerprint_by_seed.values():
                raise MatrixError("different seeds produced the same dataset fingerprint")
            if observations_sha256 in observations_by_seed.values():
                raise MatrixError("different seeds produced identical observations.jsonl content")
            fingerprint_by_seed[plan["seed"]] = fingerprint
            observations_by_seed[plan["seed"]] = observations_sha256
            quality_cache[plan["dataset_path"].resolve()] = _copy_quality(quality)
            _merge_target_units(
                units, manifest, base_benchmark.get("target_signal_ids")
            )
            datasets.append(
                {
                    "seed": plan["seed"],
                    "dataset_id": plan["dataset_id"],
                    "dataset_path": plan["dataset_relative"],
                    "generator_config_path": plan["config_relative"],
                    "generator_config_sha256": generator_config_hashes[plan["seed"]],
                    "dataset_fingerprint": fingerprint,
                    "observations_sha256": observations_sha256,
                    "quality_gate": {
                        "status": "pass",
                        "observation_record_count": quality["observation_record_count"],
                        "equipment_count": quality["equipment_count"],
                    },
                }
            )

        def cached_quality(dataset_path: Path, checked_root: Path) -> dict[str, Any]:
            if checked_root.resolve() != root:
                raise MatrixError("cell quality check used an unexpected repository root")
            try:
                return _copy_quality(quality_cache[dataset_path.resolve()])
            except KeyError as exc:
                raise MatrixError("cell referenced a dataset outside the matrix quality cache") from exc

        result_schema = load_json(root / "schemas" / "benchmark-result.schema.json")
        for plan in cell_plans:
            dataset = plan["dataset"]
            fingerprint = fingerprint_by_seed[plan["seed"]]
            cell = {
                "cell_id": plan["cell_id"],
                "run_id": plan["run_id"],
                "seed": plan["seed"],
                "horizon": plan["horizon"],
                "context_length": plan["context_length"],
                "dataset_id": dataset["dataset_id"],
                "dataset_path": dataset["dataset_relative"],
                "dataset_fingerprint": fingerprint,
                "benchmark_config_path": plan["config_relative"],
                "benchmark_config_sha256": benchmark_config_hashes[plan["cell_id"]],
                "output_dir": plan["output_relative"],
                "result_path": None,
                "status": "failed",
                "benchmark_failure_count": 0,
                "failure": None,
            }
            try:
                output = benchmark_runner(
                    benchmark_config_paths[plan["cell_id"]],
                    root,
                    registry,
                    cached_quality,
                )
                if output.resolve() != plan["output_path"]:
                    raise MatrixError("benchmark runner returned an unexpected output path")
                result = _load_object(output / "result.json", "cell result")
                validate(result, result_schema)
                _validate_cell_result(
                    result, plan, fingerprint, start_revision, root
                )
                cell["status"] = result["status"]
                cell["result_path"] = _joined_path(plan["output_relative"], "result.json")
                cell["benchmark_failure_count"] = len(result["failures"])
                completed.append((plan, result))
            except MatrixProvenanceError:
                raise
            except Exception as exc:
                reason = str(exc).strip() or exc.__class__.__name__
                cell["status"] = "failed"
                cell["failure"] = {
                    "error_type": exc.__class__.__name__,
                    "reason": reason,
                }
            cells.append(cell)

        macro = _macro_summary(completed, units)
        successful_count = sum(cell["status"] == "success" for cell in cells)
        partial_count = sum(cell["status"] == "partial" for cell in cells)
        failed_count = sum(cell["status"] == "failed" for cell in cells)
        completed_count = successful_count + partial_count
        status = (
            "failed"
            if completed_count == 0
            else "success"
            if successful_count == len(cells)
            else "partial"
        )
        result = {
            "schema_version": MATRIX_SCHEMA_VERSION,
            "result_type": "benchmark-matrix",
            "matrix_id": config["matrix_id"],
            "status": status,
            "matrix_config": config,
            "code_revision": start_revision,
            "base_configs": {
                "generator": {
                    "path": config["generator_config_path"],
                    "sha256": base_config_hashes["generator"],
                },
                "benchmark": {
                    "path": config["benchmark_config_path"],
                    "sha256": base_config_hashes["benchmark"],
                },
            },
            "axes": {
                "seeds": list(config["axes"]["seeds"]),
                "horizons": list(config["axes"]["horizons"]),
                "context_lengths": list(config["axes"]["context_lengths"]),
                "expansion_order": list(EXPANSION_ORDER),
            },
            "outputs": {
                "dataset_output_root": config["dataset_output_root"],
                "benchmark_output_root": config["benchmark_output_root"],
                "matrix_output_dir": config["matrix_output_dir"],
            },
            "counts": {
                "total_cells": len(cells),
                "successful_cells": successful_count,
                "partial_cells": partial_count,
                "failed_cells": failed_count,
                "completed_cells": completed_count,
            },
            "datasets": datasets,
            "cells": cells,
            "macro_summary": macro,
            "research_only_notice": research_only_notice,
            "limitations": [
                "macro summaryはseedごとのcell metricを同じ重みで要約し、raw predictionを再集計したpooled metricではない",
                "単位の異なるtargetを混合せず、aggregate／by_modelを優劣判定に使用しない",
                "合成データの結果は実設備性能、製品採用、Phase 2完了を示さない",
                "共有model instanceを使う場合、後続cellのlatencyはcold-startを含まない",
            ],
        }
        try:
            validate(
                result,
                load_json(root / "schemas" / "benchmark-matrix-result.schema.json"),
            )
        except ManifestValidationError as exc:
            raise MatrixError(f"matrix result schema validation failed: {exc}") from exc
        (temporary / "summary.md").write_text(
            _summary_markdown(result), encoding="utf-8", newline="\n"
        )
        (temporary / "result.json").write_bytes(_canonical_json(result))
        try:
            for plan in dataset_plans:
                _, current_observations_sha256, _ = _dataset_identity(
                    plan["dataset_path"], plan["dataset_id"]
                )
                if current_observations_sha256 != observations_by_seed[plan["seed"]]:
                    raise MatrixProvenanceError(
                        "dataset observations changed during matrix execution"
                    )
        except OSError as exc:
            raise MatrixProvenanceError(
                f"dataset observations could not be re-read before publish: {exc}"
            ) from exc
        try:
            current_hashes = {
                "generator": _file_sha256(generator_path),
                "benchmark": _file_sha256(benchmark_path),
            }
        except OSError as exc:
            raise MatrixProvenanceError(
                f"base config could not be re-read before publish: {exc}"
            ) from exc
        if current_hashes != base_config_hashes:
            raise MatrixProvenanceError(
                "base generator or benchmark config changed during matrix execution"
            )
        end_revision = _revision(root)
        if end_revision != start_revision:
            raise MatrixProvenanceError(
                "repository code revision changed during matrix execution"
            )
        temporary.rename(matrix_output)
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)
        raise
    return matrix_output


__all__ = [
    "MatrixError",
    "MatrixProvenanceError",
    "expand_cells",
    "run_matrix",
]
