import builtins
import importlib
import json
from math import inf, nan
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import banto_ai.adapters.timesfm3 as timesfm3_module
from banto_ai.adapters.timesfm3 import (
    AdapterUnavailableError,
    BackendForecast,
    DEFAULT_REVISION,
    OFFICIAL_QUANTILES,
    OfficialTimesFM3Backend,
    TimesFM3Adapter,
    TimesFM3Config,
    validate_timesfm3_license_manifest,
)
from banto_ai.contracts import Forecaster
from banto_ai.manifest import ManifestValidationError, validate
from banto_ai.types import (
    ForecastRequest,
    QualityStatus,
    SignalMetadata,
    SignalPoint,
    TimeSeries,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "examples" / "manifests" / "model-license-timesfm3.json"
START = datetime(2026, 1, 1, tzinfo=timezone.utc)


class FakeBackend:
    def __init__(self, output):
        self.output = output
        self.calls = []

    def forecast(
        self,
        targets,
        past_only_covariates,
        past_future_covariates,
        horizon,
        return_quantiles,
    ):
        self.calls.append({
            "targets": targets,
            "past_only_covariates": past_only_covariates,
            "past_future_covariates": past_future_covariates,
            "horizon": horizon,
            "return_quantiles": return_quantiles,
        })
        return self.output


class FakeArray:
    def __init__(self, values):
        self.values = values

    def tolist(self):
        return self.values


class FakeNumpy(ModuleType):
    def __init__(self):
        super().__init__("numpy")
        self.float32 = object()
        self.calls = []

    def asarray(self, values, dtype):
        self.calls.append((values, dtype))
        return FakeArray(values)


def quantile_tensor(targets=1, horizon=2):
    return tuple(
        tuple(
            tuple(float(target * 100 + step * 10 + quantile) for quantile in range(9))
            for step in range(horizon)
        )
        for target in range(targets)
    )


class TimesFM3AdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def series(
        self,
        signal_id,
        values,
        *,
        role="target",
        start=0,
        interval_ms=1000,
        quality=QualityStatus.OK,
        unit="u",
    ):
        metadata = SignalMetadata(signal_id, signal_id, unit, interval_ms, role=role)
        points = tuple(
            SignalPoint(
                START + timedelta(milliseconds=interval_ms * (start + index)),
                float(value),
                quality,
            )
            for index, value in enumerate(values)
        )
        return TimeSeries(metadata, points)

    def request(
        self,
        contexts,
        *,
        targets=("a",),
        horizon=2,
        quantiles=(0.1, 0.5, 0.9),
        known_future=(),
    ):
        return ForecastRequest(
            tuple(contexts),
            tuple(targets),
            horizon,
            tuple(quantiles),
            known_future_covariates=tuple(known_future),
        )

    def adapter(self, output, config=None):
        return TimesFM3Adapter(
            self.manifest,
            config=config,
            backend=FakeBackend(output),
        )

    def test_core_module_import_does_not_import_optional_dependencies(self):
        original_import = builtins.__import__

        def guarded_import(name, *args, **kwargs):
            if name.split(".")[0] in {"numpy", "timesfm3", "torch"}:
                raise AssertionError(f"unexpected optional import: {name}")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=guarded_import):
            importlib.reload(timesfm3_module)

    def test_missing_dependencies_are_deterministic(self):
        original_import = builtins.__import__
        request = self.request([self.series("a", (1, 2, 3))], quantiles=())
        for missing_dependency in ("numpy", "timesfm3"):
            def missing_import(name, *args, **kwargs):
                root = name.split(".")[0]
                if root == missing_dependency:
                    raise ModuleNotFoundError(name)
                if root == "numpy":
                    return FakeNumpy()
                return original_import(name, *args, **kwargs)

            with self.subTest(missing_dependency=missing_dependency):
                with patch("builtins.__import__", side_effect=missing_import):
                    with self.assertRaises(timesfm3_module.AdapterUnavailableError):
                        TimesFM3Adapter(self.manifest).forecast(request)

    def test_adapter_implements_forecaster_and_provenance_is_exact(self):
        adapter = self.adapter(BackendForecast(((4, 5),), None))
        self.assertIsInstance(adapter, Forecaster)
        result = adapter.forecast(
            self.request([self.series("a", (1, 2, 3))], quantiles=()),
        )
        self.assertEqual(
            result.model_version,
            f"timesfm3-3.0.0@{DEFAULT_REVISION}",
        )

    def test_univariate_point_and_quantile_subset(self):
        backend = FakeBackend(BackendForecast(((4, 5),), quantile_tensor()))
        adapter = TimesFM3Adapter(self.manifest, backend=backend)
        result = adapter.forecast(self.request(
            [self.series("a", (1, 2, 3))],
            quantiles=(0.3, 0.5, 0.8),
        ))
        forecast = result.forecasts[0]
        self.assertEqual(forecast.point_forecast, (4.0, 5.0))
        self.assertEqual(
            tuple(item.quantile for item in forecast.quantile_forecasts),
            (0.3, 0.5, 0.8),
        )
        self.assertEqual(forecast.quantile_forecasts[0].values, (2.0, 12.0))
        self.assertTrue(backend.calls[0]["return_quantiles"])

    def test_multivariate_targets_preserve_requested_order(self):
        backend = FakeBackend(BackendForecast(((10, 11), (20, 21)), None))
        adapter = TimesFM3Adapter(self.manifest, backend=backend)
        request = self.request(
            [self.series("b", (4, 5, 6)), self.series("a", (1, 2, 3))],
            targets=("a", "b"),
            quantiles=(),
        )
        result = adapter.forecast(request)
        self.assertEqual(backend.calls[0]["targets"], ((1.0, 2.0, 3.0), (4.0, 5.0, 6.0)))
        self.assertEqual(tuple(item.signal_id for item in result.forecasts), ("a", "b"))
        self.assertEqual(result.forecasts[1].point_forecast, (20.0, 21.0))

    def test_past_only_and_combined_past_future_covariates(self):
        backend = FakeBackend(BackendForecast(((4, 5),), None))
        contexts = [
            self.series("a", (1, 2, 3)),
            self.series("past", (7, 8, 9), role="covariate"),
            self.series("known", (10, 11, 12), role="covariate"),
        ]
        combined = self.series(
            "known", (10, 11, 12, 13, 14), role="covariate",
        )
        TimesFM3Adapter(self.manifest, backend=backend).forecast(self.request(
            contexts, quantiles=(), known_future=(combined,),
        ))
        call = backend.calls[0]
        self.assertEqual(call["past_only_covariates"], ((7.0, 8.0, 9.0),))
        self.assertEqual(
            call["past_future_covariates"],
            ((10.0, 11.0, 12.0, 13.0, 14.0),),
        )

    def test_future_timestamps_are_generated_from_context_interval(self):
        adapter = self.adapter(BackendForecast(((4, 5),), None))
        result = adapter.forecast(
            self.request([self.series("a", (1, 2, 3))], quantiles=()),
        )
        self.assertEqual(
            result.forecasts[0].timestamps,
            (START + timedelta(seconds=3), START + timedelta(seconds=4)),
        )

    def test_official_wrapper_uses_exact_predict_batch_api(self):
        fake_numpy = FakeNumpy()
        module = ModuleType("timesfm3")
        config_calls = []
        evaluator_instances = []

        class FakeModelConfig:
            def __init__(self, **kwargs):
                config_calls.append(kwargs)

        class FakeEvaluator:
            def __init__(self, config):
                self.config = config
                self.calls = []
                evaluator_instances.append(self)

            def predict_batch(self, **kwargs):
                self.calls.append(kwargs)
                yield SimpleNamespace(
                    forecast=FakeArray([[4.0, 5.0]]),
                    quantiles=FakeArray(quantile_tensor()),
                )

        module.ModelConfig = FakeModelConfig
        module.TimesFM3Evaluator = FakeEvaluator
        with patch.dict(sys.modules, {"numpy": fake_numpy, "timesfm3": module}):
            backend = TimesFM3Adapter(self.manifest)._load_official_backend()
            output = backend.forecast(
                ((1.0, 2.0, 3.0),),
                ((7.0, 8.0, 9.0),),
                ((10.0, 11.0, 12.0, 13.0, 14.0),),
                2,
                True,
            )

        self.assertEqual(config_calls, [{
            "checkpoint_path": "google/timesfm-3.0-pytorch",
            "revision": DEFAULT_REVISION,
            "device": "cpu",
            "local_files_only": True,
            "per_core_batch_size": 1,
        }])
        call = evaluator_instances[0].calls[0]
        self.assertEqual(set(call), {
            "contexts", "horizon", "past_only_covariates",
            "past_future_covariates", "return_quantiles",
            "use_symmetric_averaging", "sort_quantiles", "padding_mode",
        })
        self.assertEqual(call["contexts"][0].values, ((1.0, 2.0, 3.0),))
        self.assertEqual(call["past_only_covariates"][0].values, ((7.0, 8.0, 9.0),))
        self.assertEqual(
            call["past_future_covariates"][0].values,
            ((10.0, 11.0, 12.0, 13.0, 14.0),),
        )
        self.assertEqual(call["horizon"], 2)
        self.assertIs(call["return_quantiles"], True)
        self.assertIs(call["use_symmetric_averaging"], False)
        self.assertIs(call["sort_quantiles"], True)
        self.assertEqual(call["padding_mode"], "none")
        self.assertEqual(len(fake_numpy.calls), 3)
        self.assertTrue(all(dtype is fake_numpy.float32 for _, dtype in fake_numpy.calls))
        self.assertEqual(output.point_forecast, [[4.0, 5.0]])

    def test_official_wrapper_passes_none_matrices_and_requires_one_output(self):
        class Evaluator:
            def __init__(self, outputs):
                self.outputs = outputs

            def predict_batch(self, **kwargs):
                self.kwargs = kwargs
                return iter(self.outputs)

        valid = SimpleNamespace(forecast=FakeArray([[1.0]]), quantiles=None)
        evaluator = Evaluator([valid])
        backend = OfficialTimesFM3Backend(evaluator, FakeNumpy())
        backend.forecast(((1.0,),), (), (), 1, False)
        self.assertEqual(evaluator.kwargs["past_only_covariates"], [None])
        self.assertEqual(evaluator.kwargs["past_future_covariates"], [None])
        for outputs in ([], [valid, valid]):
            with self.subTest(output_count=len(outputs)):
                with self.assertRaises(ValueError):
                    OfficialTimesFM3Backend(Evaluator(outputs), FakeNumpy()).forecast(
                        ((1.0,),), (), (), 1, False,
                    )

    def test_official_wrapper_rejects_implicit_numeric_conversion(self):
        class Evaluator:
            def predict_batch(self, **kwargs):
                raise AssertionError("invalid input must not reach predict_batch")

        backend = OfficialTimesFM3Backend(Evaluator(), FakeNumpy())
        for value in (True, "1.0", nan, inf):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    backend.forecast(((value,),), (), (), 1, False)

    def test_license_manifest_is_required_and_fails_closed(self):
        with self.assertRaises(TypeError):
            TimesFM3Adapter()  # type: ignore[call-arg]
        for field in (
            "schema_version", "manifest_type", "model_id", "code_license",
            "weights_license", "allowed_use", "source_url", "package_name",
            "package_version", "package_sha256", "checkpoint",
            "checkpoint_revision", "verified_at",
        ):
            with self.subTest(field=field):
                missing = dict(self.manifest)
                missing.pop(field)
                with self.assertRaises(ValueError):
                    TimesFM3Adapter(missing)
                modified = dict(self.manifest)
                modified[field] = "modified"
                with self.assertRaises(ValueError):
                    TimesFM3Adapter(modified)
        invalid_manifests = []
        unknown = dict(self.manifest)
        unknown["unexpected"] = "value"
        invalid_manifests.append(unknown)
        invalid_manifests.append({**self.manifest, "schema_version": "1.0"})
        invalid_manifests.append({**self.manifest, "manifest_type": "model"})
        for field in (
            "schema_version", "manifest_type", "model_id", "code_license",
            "weights_license", "allowed_use", "source_url", "package_name",
            "package_version", "package_sha256", "checkpoint",
            "checkpoint_revision", "verified_at", "notes",
        ):
            invalid_manifests.append({**self.manifest, field: 1})
        for invalid in invalid_manifests:
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    TimesFM3Adapter(invalid)
        without_notes = dict(self.manifest)
        without_notes.pop("notes")
        TimesFM3Adapter(without_notes)
        for config_field, value in (
            ("package_version", "3.0.1"),
            ("checkpoint_path", "other/checkpoint"),
            ("checkpoint_revision", "1" * 40),
        ):
            with self.subTest(config_field=config_field):
                kwargs = {config_field: value}
                with self.assertRaises(ValueError):
                    validate_timesfm3_license_manifest(
                        self.manifest,
                        "research-only",
                        package_version=kwargs.get("package_version", "3.0.0"),
                        checkpoint_path=kwargs.get(
                            "checkpoint_path", "google/timesfm-3.0-pytorch",
                        ),
                        checkpoint_revision=kwargs.get(
                            "checkpoint_revision", DEFAULT_REVISION,
                        ),
                    )
        for requested_use in ("product", "commercial"):
            with self.subTest(requested_use=requested_use):
                with self.assertRaises(ValueError):
                    validate_timesfm3_license_manifest(self.manifest, requested_use)
                with self.assertRaises(ValueError):
                    TimesFM3Config(requested_use=requested_use)

    def test_config_validation(self):
        invalid = (
            {"package_version": "3.0.1"},
            {"checkpoint_path": "other/model"},
            {"checkpoint_revision": "ABC"},
            {"checkpoint_revision": DEFAULT_REVISION.upper()},
            {"checkpoint_revision": 123},
            {"requested_use": "product"},
            {"per_core_batch_size": True},
            {"per_core_batch_size": 1.5},
            {"per_core_batch_size": 0},
            {"device": ""},
            {"device": 1},
            {"local_files_only": "yes"},
        )
        for fields in invalid:
            with self.subTest(fields=fields):
                with self.assertRaises(ValueError):
                    TimesFM3Config(**fields)

    def test_model_license_schema_keeps_legacy_manifest_and_checks_provenance(self):
        schema = json.loads(
            (ROOT / "schemas" / "model-license-manifest.schema.json").read_text(
                encoding="utf-8",
            )
        )
        legacy = json.loads(
            (ROOT / "examples" / "manifests" / "model-license-last-value.json").read_text(
                encoding="utf-8",
            )
        )
        validate(self.manifest, schema)
        validate(legacy, schema)
        for field, value in (
            ("package_sha256", "A" * 64),
            ("checkpoint_revision", "x" * 40),
            ("verified_at", "2026/09/03"),
        ):
            with self.subTest(field=field):
                invalid = {**self.manifest, field: value}
                with self.assertRaises(ManifestValidationError):
                    validate(invalid, schema)

    def test_request_quantile_validation(self):
        series = [self.series("a", (1, 2, 3))]
        output = BackendForecast(((4, 5),), quantile_tensor())
        for quantiles in ((0.1,), (0.15, 0.5)):
            with self.subTest(quantiles=quantiles):
                with self.assertRaises(ValueError):
                    self.adapter(output).forecast(
                        self.request(series, quantiles=quantiles),
                    )

    def test_context_alignment_failures(self):
        target = self.series("a", (1, 2, 3))
        cases = (
            self.series("x", (1, 2), role="covariate"),
            self.series("x", (1, 2, 3), role="covariate", start=1),
            self.series("x", (1, 2, 3), role="covariate", interval_ms=2000),
        )
        for covariate in cases:
            with self.subTest(points=covariate.points):
                with self.assertRaises(ValueError):
                    self.adapter(BackendForecast(((4, 5),), None)).forecast(
                        self.request([target, covariate], quantiles=()),
                    )

    def test_known_future_length_prefix_and_alignment_failures(self):
        contexts = [
            self.series("a", (1, 2, 3)),
            self.series("x", (10, 11, 12), role="covariate"),
        ]
        cases = [
            self.series("x", (10, 11, 12, 13), role="covariate"),
            self.series("x", (99, 11, 12, 13, 14), role="covariate"),
            self.series("x", (10, 11, 12, 13, 14), role="covariate", start=1),
            self.series("x", (10, 11, 12, 13, 14), role="covariate", interval_ms=2000),
            self.series("x", (10, 11, 12, 13, 14), role="covariate", unit="other"),
        ]
        bad_suffix = self.series("x", (10, 11, 12, 13, 14), role="covariate")
        object.__setattr__(
            bad_suffix.points[-1], "timestamp", START + timedelta(seconds=5),
        )
        cases.append(bad_suffix)
        for combined in cases:
            with self.subTest(points=combined.points):
                with self.assertRaises(ValueError):
                    self.adapter(BackendForecast(((4, 5),), None)).forecast(
                        self.request(contexts, quantiles=(), known_future=(combined,)),
                    )

    def test_role_and_future_target_failures(self):
        undeclared_target = self.series("x", (1, 2, 3))
        with self.assertRaises(ValueError):
            self.adapter(BackendForecast(((4, 5),), None)).forecast(
                self.request([self.series("a", (1, 2, 3)), undeclared_target], quantiles=()),
            )
        target_future = self.series("a", (1, 2, 3, 4, 5))
        with self.assertRaises(ValueError):
            self.adapter(BackendForecast(((4, 5),), None)).forecast(
                self.request(
                    [self.series("a", (1, 2, 3))],
                    quantiles=(),
                    known_future=(target_future,),
                ),
            )

    def test_bad_quality_and_nonfinite_inputs(self):
        bad_quality = self.series(
            "a", (1, 2, 3), quality=QualityStatus.MISSING,
        )
        with self.assertRaises(ValueError):
            self.adapter(BackendForecast(((4, 5),), None)).forecast(
                self.request([bad_quality], quantiles=()),
            )
        for value in (nan, inf, True, "1.0"):
            with self.subTest(value=value):
                series = self.series("a", (1, 2, 3))
                object.__setattr__(series.points[1], "value", value)
                with self.assertRaises(ValueError):
                    self.adapter(BackendForecast(((4, 5),), None)).forecast(
                        self.request([series], quantiles=()),
                    )

    def test_point_output_dimensions_and_finite_values(self):
        request = self.request([self.series("a", (1, 2, 3))], quantiles=())
        invalid = (
            BackendForecast((), None),
            BackendForecast((1, 2), None),
            BackendForecast(((1,),), None),
            BackendForecast(((nan, 2),), None),
            BackendForecast(((inf, 2),), None),
            BackendForecast(((True, 2),), None),
            BackendForecast((("1.0", 2),), None),
        )
        for output in invalid:
            with self.subTest(output=output):
                with self.assertRaises(ValueError):
                    self.adapter(output).forecast(request)

    def test_all_quantile_dimensions_are_validated_before_subset_selection(self):
        request = self.request(
            [self.series("a", (1, 2, 3))], quantiles=(0.5,),
        )
        invalid = (
            BackendForecast(((1, 2),), ()),
            BackendForecast(((1, 2),), quantile_tensor(targets=2)),
            BackendForecast(((1, 2),), quantile_tensor(horizon=1)),
            BackendForecast(((1, 2),), (((0, 1, 2, 3, 4, 5, 6, 7),) * 2,)),
        )
        for output in invalid:
            with self.subTest(output=output):
                with self.assertRaises(ValueError):
                    self.adapter(output).forecast(request)

    def test_quantile_nan_inf_and_crossing_are_rejected_in_unrequested_cells(self):
        request = self.request(
            [self.series("a", (1, 2, 3))], quantiles=(0.5,),
        )
        for value in (nan, inf, True, "1.0"):
            tensor = [[list(step) for step in target] for target in quantile_tensor()]
            tensor[0][0][0] = value
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.adapter(BackendForecast(((1, 2),), tensor)).forecast(request)
        crossing = [[list(step) for step in target] for target in quantile_tensor()]
        crossing[0][0][0] = 2.0
        crossing[0][0][1] = 1.0
        with self.assertRaises(ValueError):
            self.adapter(BackendForecast(((1, 2),), crossing)).forecast(request)

    def test_missing_backend_output_fields_are_value_errors(self):
        request_without_quantiles = self.request(
            [self.series("a", (1, 2, 3))], quantiles=(),
        )
        malformed_outputs = (
            SimpleNamespace(quantile_forecast=None),
            SimpleNamespace(point_forecast=((1, 2),)),
        )
        for output in malformed_outputs:
            with self.subTest(output=output):
                with self.assertRaises(ValueError):
                    self.adapter(output).forecast(request_without_quantiles)

    def test_missing_official_forecast_output_fields_are_value_errors(self):
        class Evaluator:
            def __init__(self, output):
                self.output = output

            def predict_batch(self, **kwargs):
                yield self.output

        malformed_outputs = (
            SimpleNamespace(quantiles=None),
            SimpleNamespace(forecast=FakeArray([[1.0]])),
            SimpleNamespace(forecast=[[1.0]], quantiles=None),
        )
        for output in malformed_outputs:
            with self.subTest(output=output):
                backend = OfficialTimesFM3Backend(Evaluator(output), FakeNumpy())
                with self.assertRaises(ValueError):
                    backend.forecast(((1.0,),), (), (), 1, False)

    def test_empty_quantile_request_accepts_none_or_empty_output(self):
        request = self.request([self.series("a", (1, 2, 3))], quantiles=())
        for values in (None, ()):
            with self.subTest(values=values):
                result = self.adapter(BackendForecast(((1, 2),), values)).forecast(request)
                self.assertEqual(result.forecasts[0].quantile_forecasts, ())


if __name__ == "__main__":
    unittest.main()
