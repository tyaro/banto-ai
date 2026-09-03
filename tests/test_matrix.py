import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4

from banto_ai.benchmark import ModelRegistry, _revision as benchmark_revision, run_benchmark
from banto_ai.manifest import ManifestValidationError, load_json, validate
from banto_ai.matrix import MatrixError, MatrixProvenanceError, expand_cells, run_matrix
from banto_ai.quality import check_dataset
from tools.timesfm3 import run_matrix as timesfm_matrix


ROOT = Path(__file__).resolve().parents[1]


class MatrixTests(unittest.TestCase):
    def setUp(self):
        self.token = uuid4().hex
        self.artifact_root = ROOT / "artifacts" / "test-matrix" / self.token
        self.control = self.artifact_root / "control"
        self.control.mkdir(parents=True, exist_ok=False)
        self.owned = [self.artifact_root]

    def tearDown(self):
        for path in reversed(self.owned):
            try:
                if path.is_dir() and not path.is_symlink():
                    shutil.rmtree(path)
                else:
                    path.unlink(missing_ok=True)
            except OSError:
                pass

    def _relative(self, path: Path) -> str:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()

    def _write_json(self, path: Path, value: dict) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        return path

    def _matrix_config(
        self,
        label: str,
        *,
        seeds=(17, 42),
        horizons=(1, 3),
        contexts=(6, 12),
        models=None,
    ):
        matrix_id = "tm-" + hashlib.sha256(
            f"{self.token}:{label}".encode("utf-8")
        ).hexdigest()[:20]
        benchmark = load_json(ROOT / "examples" / "configs" / "benchmark-small.json")
        benchmark.update(
            run_id="base",
            models=models or [{"name": "last-value"}],
            past_only_covariate_ids=["load_proxy"],
            known_future_covariate_ids=[],
            validation_origin_stride=3,
            test_origin_stride=3,
            max_validation_origins=1,
            max_test_origins=1,
        )
        benchmark_path = self._write_json(
            self.control / f"benchmark-{label}.json", benchmark
        )
        dataset_root = self.artifact_root / label / "datasets"
        benchmark_root = self.artifact_root / label / "runs"
        matrix_output = self.artifact_root / label / "result"
        config = {
            "schema_version": "0.1",
            "matrix_id": matrix_id,
            "generator_config_path": "examples/configs/synthetic-motor-small.json",
            "benchmark_config_path": self._relative(benchmark_path),
            "dataset_output_root": self._relative(dataset_root),
            "benchmark_output_root": self._relative(benchmark_root),
            "matrix_output_dir": self._relative(matrix_output),
            "axes": {
                "seeds": list(seeds),
                "horizons": list(horizons),
                "context_lengths": list(contexts),
            },
        }
        config_path = self._write_json(self.control / f"matrix-{label}.json", config)
        return config_path, config

    def test_config_schema_and_eight_cell_expansion_are_deterministic(self):
        config_path, config = self._matrix_config("expand")
        validate(config, load_json(ROOT / "schemas" / "benchmark-matrix-config.schema.json"))
        example = load_json(
            ROOT / "examples" / "configs" / "benchmark-matrix-timesfm3-small.json"
        )
        validate(
            example,
            load_json(ROOT / "schemas" / "benchmark-matrix-config.schema.json"),
        )
        self.assertEqual(len(expand_cells(example)), 8)
        expected = (
            (17, 1, 6),
            (17, 1, 12),
            (17, 3, 6),
            (17, 3, 12),
            (42, 1, 6),
            (42, 1, 12),
            (42, 3, 6),
            (42, 3, 12),
        )
        self.assertEqual(expand_cells(config), expected)
        self.assertEqual(expand_cells(load_json(config_path)), expected)
        invalid = copy.deepcopy(config)
        invalid["unexpected"] = True
        with self.assertRaises(ManifestValidationError):
            validate(
                invalid,
                load_json(ROOT / "schemas" / "benchmark-matrix-config.schema.json"),
            )

    def test_eight_cells_regenerate_per_seed_reuse_dataset_and_macro_metrics(self):
        config_path, config = self._matrix_config("actual")
        quality_calls = []

        def counting_quality(dataset_path, root):
            quality_calls.append(dataset_path.resolve())
            return check_dataset(dataset_path, root)

        output = run_matrix(config_path, ROOT, quality_checker=counting_quality)
        result = load_json(output / "result.json")
        validate(result, load_json(ROOT / "schemas" / "benchmark-matrix-result.schema.json"))
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["counts"], {
            "total_cells": 8,
            "successful_cells": 8,
            "partial_cells": 0,
            "failed_cells": 0,
            "completed_cells": 8,
        })
        self.assertEqual(len(quality_calls), 2)
        self.assertEqual(len(set(quality_calls)), 2)
        fingerprints = {item["seed"]: item["dataset_fingerprint"] for item in result["datasets"]}
        self.assertEqual(len(set(fingerprints.values())), 2)
        observation_hashes = {
            item["seed"]: item["observations_sha256"] for item in result["datasets"]
        }
        self.assertEqual(len(set(observation_hashes.values())), 2)
        for seed in (17, 42):
            matching = [cell for cell in result["cells"] if cell["seed"] == seed]
            self.assertEqual(len(matching), 4)
            self.assertEqual({cell["dataset_fingerprint"] for cell in matching}, {fingerprints[seed]})
            dataset = next(item for item in result["datasets"] if item["seed"] == seed)
            generator_config = load_json(ROOT / dataset["generator_config_path"])
            self.assertEqual(generator_config["seed"], seed)
            self.assertEqual(generator_config["dataset_id"], dataset["dataset_id"])
            manifest = load_json(ROOT / dataset["dataset_path"] / "dataset-manifest.json")
            observations = ROOT / dataset["dataset_path"] / manifest["data_path"]
            self.assertEqual(
                dataset["observations_sha256"],
                hashlib.sha256(observations.read_bytes()).hexdigest(),
            )

        self.assertEqual(
            result["base_configs"]["generator"]["sha256"],
            hashlib.sha256(
                (ROOT / config["generator_config_path"]).read_bytes()
            ).hexdigest(),
        )
        self.assertEqual(
            result["base_configs"]["benchmark"]["sha256"],
            hashlib.sha256(
                (ROOT / config["benchmark_config_path"]).read_bytes()
            ).hexdigest(),
        )
        for cell in result["cells"]:
            cell_result = load_json(ROOT / cell["result_path"])
            self.assertEqual(cell_result["code_revision"], result["code_revision"])

        expected_order = list(expand_cells(config))
        actual_order = [
            (cell["seed"], cell["horizon"], cell["context_length"])
            for cell in result["cells"]
        ]
        self.assertEqual(actual_order, expected_order)
        for cell in result["cells"]:
            generated_config = load_json(ROOT / cell["benchmark_config_path"])
            self.assertEqual(generated_config["seed"], cell["seed"])
            self.assertEqual(generated_config["horizon"], cell["horizon"])
            self.assertEqual(generated_config["context_length"], cell["context_length"])
            self.assertEqual(generated_config["run_id"], cell["run_id"])
            self.assertEqual(generated_config["dataset_path"], cell["dataset_path"])
            self.assertEqual(generated_config["output_dir"], cell["output_dir"])

        macro_keys = [
            (
                row["model"], row["target_signal_key"], row["unit"],
                row["horizon"], row["context_length"],
            )
            for row in result["macro_summary"]
        ]
        self.assertEqual(macro_keys, sorted(macro_keys))
        current = next(
            row
            for row in result["macro_summary"]
            if row["model"] == "last-value"
            and row["target_signal_key"] == "motor_current"
            and row["horizon"] == 3
            and row["context_length"] == 12
        )
        source_values = {name: [] for name in (
            "mae", "rmse", "mase", "wis",
            "nominal_interval_coverage", "interval_width",
        )}
        source_points = 0
        for cell in result["cells"]:
            if cell["horizon"] != 3 or cell["context_length"] != 12:
                continue
            cell_result = load_json(ROOT / cell["result_path"])
            row = next(
                item
                for item in cell_result["metrics"]["by_model_target"]
                if item["model"] == "last-value"
                and item["target_signal_key"] == "motor_current"
            )
            for name in source_values:
                source_values[name].append(row["metrics"][name])
            source_points += row["metrics"]["count"]
        self.assertEqual(current["cell_count"], 2)
        self.assertEqual(current["total_point_count"], source_points)
        for name, values in source_values.items():
            with self.subTest(metric=name):
                self.assertAlmostEqual(current["metrics"][name]["mean"], statistics.fmean(values))
                self.assertEqual(current["metrics"][name]["min"], min(values))
                self.assertEqual(current["metrics"][name]["max"], max(values))
                self.assertAlmostEqual(
                    current["metrics"][name]["sample_stddev"], statistics.stdev(values)
                )
        summary = (output / "summary.md").read_text(encoding="utf-8")
        self.assertIn("raw predictionをまとめ直したpooled metricではありません", summary)
        self.assertIn("## 成功・部分成功cell", summary)
        self.assertIn("## 失敗cell", summary)

        invalid = copy.deepcopy(result)
        invalid["unexpected"] = True
        with self.assertRaises(ManifestValidationError):
            validate(
                invalid,
                load_json(ROOT / "schemas" / "benchmark-matrix-result.schema.json"),
            )

    def test_paths_axes_and_existing_outputs_are_rejected_before_generation(self):
        invalid_values = (
            "../escape",
            "/absolute/path",
            "C:/absolute/path",
            "artifacts\\backslash",
            "artifacts//empty",
            "artifacts/./dot",
        )
        for index, invalid_value in enumerate(invalid_values):
            with self.subTest(path=invalid_value):
                config_path, config = self._matrix_config(f"invalid-path-{index}")
                config["matrix_output_dir"] = invalid_value
                self._write_json(config_path, config)
                with self.assertRaises(MatrixError):
                    run_matrix(config_path, ROOT)

        duplicate_axes = (
            {"seeds": (17, 17)},
            {"horizons": (1, 1)},
            {"contexts": (6, 6)},
        )
        for index, override in enumerate(duplicate_axes):
            with self.subTest(duplicate_axis=override):
                config_path, _ = self._matrix_config(
                    f"duplicate-axis-{index}", **override
                )
                with self.assertRaises(MatrixError):
                    run_matrix(config_path, ROOT)

        existing_targets = ("matrix", "dataset", "benchmark")
        for target_name in existing_targets:
            with self.subTest(existing=target_name):
                config_path, config = self._matrix_config(f"existing-{target_name}")
                if target_name == "matrix":
                    existing = ROOT / config["matrix_output_dir"]
                elif target_name == "dataset":
                    existing = ROOT / config["dataset_output_root"] / config["matrix_id"]
                else:
                    existing = ROOT / config["benchmark_output_root"] / config["matrix_id"]
                existing.mkdir(parents=True, exist_ok=False)
                sentinel = existing / "sentinel.txt"
                sentinel.write_text("keep", encoding="utf-8")
                with self.assertRaises(MatrixError):
                    run_matrix(config_path, ROOT)
                self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_one_cell_failure_isolated_as_partial_and_all_failed_is_failed(self):
        config_path, _ = self._matrix_config(
            "partial", seeds=(17,), horizons=(1, 3), contexts=(6,)
        )

        def flaky(config_path, root, registry, quality_checker):
            config = load_json(config_path)
            if config["horizon"] == 3:
                raise RuntimeError("injected one-cell failure")
            return run_benchmark(config_path, root, registry, quality_checker)

        output = run_matrix(config_path, ROOT, benchmark_runner=flaky)
        result = load_json(output / "result.json")
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["counts"]["successful_cells"], 1)
        self.assertEqual(result["counts"]["failed_cells"], 1)
        failed = next(cell for cell in result["cells"] if cell["status"] == "failed")
        self.assertIn("injected one-cell failure", failed["failure"]["reason"])
        self.assertTrue(result["macro_summary"])

        all_path, _ = self._matrix_config(
            "all-failed", seeds=(17,), horizons=(1, 3), contexts=(6,)
        )

        def always_fail(*_args):
            raise RuntimeError("all cells fail")

        all_output = run_matrix(all_path, ROOT, benchmark_runner=always_fail)
        all_result = load_json(all_output / "result.json")
        self.assertEqual(all_result["status"], "failed")
        self.assertEqual(all_result["counts"]["completed_cells"], 0)
        self.assertEqual(all_result["counts"]["failed_cells"], 2)
        self.assertEqual(all_result["macro_summary"], [])

    def test_mixed_units_fail_closed_before_any_cell_runs(self):
        config_path, _ = self._matrix_config(
            "mixed-unit", seeds=(17, 42), horizons=(1,), contexts=(6,)
        )
        benchmark_calls = []

        def fake_generator(config_path, output, root):
            config = load_json(config_path)
            target = (root / output).resolve()
            target.mkdir(parents=True, exist_ok=False)
            current_unit = "A" if config["seed"] == 17 else "mA"
            manifest = {
                "dataset_id": config["dataset_id"],
                "fingerprint_path": "fingerprint.json",
                "data_path": "observations.jsonl",
                "signals": [
                    {
                        "signal_id": "motor-01.motor_current",
                        "unit": current_unit,
                        "role": "target",
                    },
                    {
                        "signal_id": "motor-01.motor_temperature",
                        "unit": "degC",
                        "role": "target",
                    },
                ],
            }
            self._write_json(target / "dataset-manifest.json", manifest)
            self._write_json(
                target / "fingerprint.json",
                {"dataset_fingerprint": f"{config['seed']:064x}"},
            )
            (target / "observations.jsonl").write_text(
                f'{{"seed":{config["seed"]}}}\n', encoding="utf-8"
            )
            return target

        def fake_quality(*_args):
            return {
                "status": "pass",
                "observation_record_count": 1,
                "equipment_count": 1,
                "checks": ["fake"],
            }

        def should_not_run(*_args):
            benchmark_calls.append(True)
            raise AssertionError("benchmark must not run after mixed-unit detection")

        with self.assertRaisesRegex(MatrixError, "mixed units"):
            run_matrix(
                config_path,
                ROOT,
                generator=fake_generator,
                quality_checker=fake_quality,
                benchmark_runner=should_not_run,
            )
        self.assertEqual(benchmark_calls, [])

    def test_identical_observations_across_seeds_fail_closed(self):
        config_path, _ = self._matrix_config(
            "same-observations", seeds=(17, 42), horizons=(1,), contexts=(6,)
        )

        def fake_generator(config_path, output, root):
            config = load_json(config_path)
            target = (root / output).resolve()
            target.mkdir(parents=True, exist_ok=False)
            self._write_json(
                target / "dataset-manifest.json",
                {
                    "dataset_id": config["dataset_id"],
                    "fingerprint_path": "fingerprint.json",
                    "data_path": "observations.jsonl",
                    "signals": [
                        {
                            "signal_id": "motor-01.motor_current",
                            "unit": "A",
                            "role": "target",
                        },
                        {
                            "signal_id": "motor-01.motor_temperature",
                            "unit": "degC",
                            "role": "target",
                        },
                    ],
                },
            )
            self._write_json(
                target / "fingerprint.json",
                {"dataset_fingerprint": f"{config['seed']:064x}"},
            )
            (target / "observations.jsonl").write_text(
                '{"same":"content"}\n', encoding="utf-8"
            )
            return target

        def fake_quality(*_args):
            return {
                "status": "pass",
                "observation_record_count": 1,
                "equipment_count": 1,
                "checks": ["fake"],
            }

        with self.assertRaisesRegex(MatrixError, "identical observations"):
            run_matrix(
                config_path,
                ROOT,
                generator=fake_generator,
                quality_checker=fake_quality,
                benchmark_runner=lambda *_args: self.fail("benchmark must not run"),
            )

    def test_observations_path_must_be_a_direct_dataset_child(self):
        config_path, _ = self._matrix_config(
            "unsafe-observations", seeds=(17,), horizons=(1,), contexts=(6,)
        )

        def fake_generator(config_path, output, root):
            config = load_json(config_path)
            target = (root / output).resolve()
            target.mkdir(parents=True, exist_ok=False)
            self._write_json(
                target / "dataset-manifest.json",
                {
                    "dataset_id": config["dataset_id"],
                    "fingerprint_path": "fingerprint.json",
                    "data_path": "nested/observations.jsonl",
                    "signals": [],
                },
            )
            self._write_json(
                target / "fingerprint.json",
                {"dataset_fingerprint": f"{config['seed']:064x}"},
            )
            return target

        def fake_quality(*_args):
            return {
                "status": "pass",
                "observation_record_count": 1,
                "equipment_count": 1,
                "checks": ["fake"],
            }

        with self.assertRaisesRegex(MatrixError, "data_path must name one direct child"):
            run_matrix(
                config_path,
                ROOT,
                generator=fake_generator,
                quality_checker=fake_quality,
                benchmark_runner=lambda *_args: self.fail("benchmark must not run"),
            )

    def test_base_config_change_during_run_is_not_published_and_is_restored(self):
        for kind in ("generator", "benchmark"):
            with self.subTest(kind=kind):
                config_path, config = self._matrix_config(
                    f"base-change-{kind}", seeds=(17,), horizons=(1,), contexts=(6,)
                )
                if kind == "generator":
                    copied_generator = self.control / f"generator-{kind}.json"
                    self._write_json(
                        copied_generator,
                        load_json(ROOT / "examples" / "configs" / "synthetic-motor-small.json"),
                    )
                    config["generator_config_path"] = self._relative(copied_generator)
                    self._write_json(config_path, config)
                    changed_path = copied_generator
                else:
                    changed_path = ROOT / config["benchmark_config_path"]
                original = changed_path.read_bytes()

                def changing_runner(path, root, registry, quality_checker):
                    output = run_benchmark(path, root, registry, quality_checker)
                    changed_path.write_bytes(original + b"\n")
                    return output

                try:
                    with self.assertRaisesRegex(
                        MatrixProvenanceError, "base generator or benchmark config changed"
                    ):
                        run_matrix(config_path, ROOT, benchmark_runner=changing_runner)
                finally:
                    changed_path.write_bytes(original)
                self.assertEqual(changed_path.read_bytes(), original)
                self.assertFalse((ROOT / config["matrix_output_dir"]).exists())
                self.assertTrue(
                    (ROOT / config["benchmark_output_root"] / config["matrix_id"]).is_dir()
                )

    def test_cell_revision_mismatch_aborts_matrix_without_publish(self):
        config_path, config = self._matrix_config(
            "cell-revision", seeds=(17,), horizons=(1,), contexts=(6,)
        )

        def mismatched_runner(path, root, registry, quality_checker):
            output = run_benchmark(path, root, registry, quality_checker)
            result_path = output / "result.json"
            result = load_json(result_path)
            result["code_revision"] = dict(result["code_revision"])
            current = result["code_revision"]["diff_sha256"]
            result["code_revision"]["diff_sha256"] = (
                "0" * 64 if current != "0" * 64 else "1" * 64
            )
            self._write_json(result_path, result)
            return output

        with self.assertRaisesRegex(
            MatrixProvenanceError, "cell code_revision does not match"
        ):
            run_matrix(config_path, ROOT, benchmark_runner=mismatched_runner)
        self.assertFalse((ROOT / config["matrix_output_dir"]).exists())
        self.assertTrue(
            (ROOT / config["benchmark_output_root"] / config["matrix_id"]).is_dir()
        )

    def test_end_revision_change_aborts_matrix_without_publish(self):
        config_path, config = self._matrix_config(
            "end-revision", seeds=(17,), horizons=(1,), contexts=(6,)
        )
        start = benchmark_revision(ROOT)
        changed = copy.deepcopy(start)
        changed["diff_sha256"] = (
            "0" * 64 if start["diff_sha256"] != "0" * 64 else "1" * 64
        )
        with patch("banto_ai.matrix._revision", side_effect=(start, changed)):
            with self.assertRaisesRegex(
                MatrixProvenanceError, "repository code revision changed"
            ):
                run_matrix(config_path, ROOT)
        self.assertFalse((ROOT / config["matrix_output_dir"]).exists())
        self.assertTrue(
            (ROOT / config["benchmark_output_root"] / config["matrix_id"]).is_dir()
        )


class TimesFMMatrixWrapperTests(unittest.TestCase):
    def setUp(self):
        self.token = uuid4().hex
        self.control = ROOT / "artifacts" / "test-timesfm-matrix" / self.token
        self.control.mkdir(parents=True, exist_ok=False)

    def tearDown(self):
        try:
            shutil.rmtree(self.control)
        except OSError:
            pass

    def _relative(self, path: Path) -> str:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()

    def _configs(self):
        benchmark = load_json(
            ROOT / "examples" / "configs" / "benchmark-timesfm3-baselines-past-only.json"
        )
        benchmark_path = self.control / "benchmark.json"
        benchmark_path.write_text(json.dumps(benchmark), encoding="utf-8")
        matrix = {
            "schema_version": "0.1",
            "matrix_id": f"timesfm-wrapper-{self.token}",
            "generator_config_path": "examples/configs/synthetic-motor-small.json",
            "benchmark_config_path": self._relative(benchmark_path),
            "dataset_output_root": f"artifacts/wrapper-data-{self.token}",
            "benchmark_output_root": f"artifacts/wrapper-runs-{self.token}",
            "matrix_output_dir": f"artifacts/wrapper-result-{self.token}",
            "axes": {"seeds": [17], "horizons": [1], "context_lengths": [6]},
        }
        matrix_path = self.control / "matrix.json"
        matrix_path.write_text(json.dumps(matrix), encoding="utf-8")
        return matrix_path

    def test_license_cache_checkpoint_package_offline_and_shared_registry(self):
        config_path = self._configs()
        calls = []
        shared_factory = lambda _equipment_id, _parameters: object()

        def fake_runner(path, root, registry, **kwargs):
            calls.append(
                {
                    "path": path,
                    "root": root,
                    "registry": registry,
                    "notice": kwargs["research_only_notice"],
                    "offline": (
                        os.environ.get("HF_HUB_OFFLINE"),
                        os.environ.get("HF_HUB_DISABLE_TELEMETRY"),
                    ),
                }
            )
            self.assertIs(registry._factories["timesfm3"], shared_factory)
            return self.control / "fake-output"

        cache = self.control / "external-cache"
        manifest_path = self.control / "manifest.json"
        with patch.object(timesfm_matrix.single_run, "_external_cache", return_value=cache) as external:
            with patch.object(
                timesfm_matrix.single_run,
                "_load_and_validate_license",
                return_value={"allowed_use": "research-only"},
            ) as license_check:
                with patch.object(timesfm_matrix.single_run, "_verify_cached_checkpoint") as checkpoint:
                    with patch.object(timesfm_matrix.single_run, "_verify_installed_package") as package:
                        with patch.object(
                            timesfm_matrix.single_run,
                            "make_shared_timesfm_factory",
                            return_value=shared_factory,
                        ) as factory:
                            with patch.dict(
                                os.environ,
                                {
                                    "HF_HUB_OFFLINE": "caller",
                                    "HF_HUB_DISABLE_TELEMETRY": "caller",
                                },
                            ):
                                output = timesfm_matrix.run_timesfm_matrix(
                                    Path(os.path.relpath(config_path, ROOT)),
                                    Path(os.path.relpath(ROOT, Path.cwd())),
                                    cache,
                                    manifest_path,
                                    accepted=True,
                                    matrix_runner=fake_runner,
                                )
                                self.assertEqual(os.environ["HF_HUB_OFFLINE"], "caller")
                                self.assertEqual(os.environ["HF_HUB_DISABLE_TELEMETRY"], "caller")
        self.assertEqual(output, self.control / "fake-output")
        self.assertEqual(calls[0]["path"], config_path.resolve())
        self.assertEqual(calls[0]["root"], ROOT.resolve())
        external.assert_called_once_with(cache)
        license_check.assert_called_once_with(manifest_path)
        checkpoint.assert_called_once_with(cache)
        package.assert_called_once_with()
        factory.assert_called_once_with({"allowed_use": "research-only"}, cache)
        self.assertEqual(calls[0]["offline"], ("1", "1"))
        self.assertIn("research-only/non-commercial", calls[0]["notice"])

    def test_license_acceptance_is_required_before_preflight(self):
        config_path = self._configs()
        with patch.object(timesfm_matrix.single_run, "_external_cache") as external:
            with self.assertRaisesRegex(ValueError, "accept-research-only-license"):
                timesfm_matrix.run_timesfm_matrix(
                    config_path,
                    ROOT,
                    self.control / "cache",
                    self.control / "manifest.json",
                    accepted=False,
                )
        external.assert_not_called()

    def test_wrapper_import_does_not_import_optional_ml_packages(self):
        command = (
            "import sys; import tools.timesfm3.run_matrix; "
            "forbidden={'timesfm','torch','numpy'} & set(sys.modules); "
            "assert not forbidden, sorted(forbidden)"
        )
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join((str(ROOT), str(ROOT / "src")))
        completed = subprocess.run(
            [sys.executable, "-c", command],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
