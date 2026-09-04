from __future__ import annotations

from datetime import datetime, timedelta, timezone
import threading
import unittest
from unittest.mock import patch

from banto_ai.adapters.chronos2 import (
    BackendForecast,
    Chronos2Adapter,
    Chronos2Config,
    Chronos2UnavailableError,
    OfficialChronos2Backend,
    OFFICIAL_QUANTILES,
    validate_chronos2_license_manifest,
)
from banto_ai.contracts import Forecaster
from banto_ai.types import (
    ForecastRequest,
    QualityStatus,
    SignalMetadata,
    SignalPoint,
    TimeSeries,
)


MANIFEST = {
    "schema_version": "0.1",
    "manifest_type": "model-license",
    "model_id": "chronos-2",
    "code_license": "Apache-2.0",
    "weights_license": "Apache-2.0",
    "allowed_use": "commercial-evaluation",
    "source_url": "https://huggingface.co/amazon/chronos-2",
    "package_name": "chronos-forecasting",
    "package_version": "2.3.1",
    "package_sha256": "d9d00ec9b1621235bfb26685638bf054885f4c000863678f1c775dfab2697496",
    "checkpoint": "amazon/chronos-2",
    "checkpoint_revision": "29ec3766d36d6f73f0696f85560a422f50e8498c",
    "verified_at": "2026-09-04",
}


class FakeBackend:
    def __init__(self, *, point=(10.0, 11.0), crossing=False, p50_offset=0.0, bad_shape=False, nonfinite=False):
        self.calls = []
        self.point = point
        self.crossing = crossing
        self.p50_offset = p50_offset
        self.bad_shape = bad_shape
        self.nonfinite = nonfinite

    def forecast(self, targets, past_covariates, future_covariates, horizon, quantiles, **kwargs):
        self.calls.append((targets, past_covariates, future_covariates, horizon, tuple(quantiles), kwargs))
        points = tuple(tuple(float(self.point[step]) for step in range(horizon)) for _ in targets)
        if self.bad_shape:
            points = tuple(tuple(row[:-1]) for row in points)
        if self.nonfinite:
            points = tuple(tuple(float("nan") if step == 0 else value for step, value in enumerate(row)) for row in points)
        if not quantiles:
            return BackendForecast(points)
        output = []
        for target_index, _ in enumerate(targets):
            rows = []
            for step in range(horizon):
                row = [points[target_index][step] - 1.0, points[target_index][step] + self.p50_offset, points[target_index][step] + 1.0]
                if self.crossing:
                    row[0], row[1] = row[1], row[0]
                rows.append(row)
            output.append(rows)
        return BackendForecast(points, output, tuple(quantiles))


class FakeTensor:
    def __init__(self, values):
        self.values = values

    def tolist(self):
        return self.values


class FakeNumpy:
    float32 = "float32"

    def __init__(self):
        self.calls = []

    def asarray(self, values, dtype=None):
        self.calls.append((values, dtype))
        return FakeTensor(values)


class FakePipeline:
    quantiles = list(OFFICIAL_QUANTILES)

    def __init__(self):
        self.quantile_calls = []
        self.predict_calls = []

    def predict_quantiles(self, **kwargs):
        self.quantile_calls.append(kwargs)
        levels = kwargs["quantile_levels"]
        q = [[[9.0 + index for _ in range(2)] for index in range(len(levels))]]
        # The actual Chronos API returns (targets, horizon, quantiles).
        q = [[[9.0 + index for index in range(len(levels))] for _ in range(2)]]
        point = [[10.0, 10.0]]
        return [FakeTensor(q)], [FakeTensor(point)]

    def predict(self, **kwargs):
        self.predict_calls.append(kwargs)
        raw = [[[100.0 for _ in range(2)] for _ in OFFICIAL_QUANTILES]]
        raw[0][OFFICIAL_QUANTILES.index(0.5)] = [10.0, 11.0]
        return [FakeTensor(raw)]


class Chronos2AdapterTests(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def series(self, signal_id, values, *, role="target", interval_ms=1000, start=None, quality=QualityStatus.OK):
        start = self.start if start is None else start
        metadata = SignalMetadata(signal_id, signal_id, "unit", interval_ms, role)
        points = tuple(
            SignalPoint(start + timedelta(milliseconds=interval_ms * index), value, quality)
            for index, value in enumerate(values)
        )
        return TimeSeries(metadata, points)

    def request(self, *, contexts, targets=("target-a",), horizon=2, quantiles=(0.1, 0.5, 0.9), future=()):
        return ForecastRequest(tuple(contexts), tuple(targets), horizon, tuple(quantiles), known_future_covariates=tuple(future))

    def adapter(self, backend=None, config=None):
        return Chronos2Adapter(MANIFEST, config=config, backend=backend)

    def context_and_future(self):
        target = self.series("target-a", (1.0, 2.0, 3.0))
        cov = self.series("load", (4.0, 5.0, 6.0), role="covariate")
        future = self.series("load", (4.0, 5.0, 6.0, 7.0, 8.0), role="covariate")
        return target, cov, future

    def test_is_forecaster_and_point_quantiles_preserve_signal_order(self):
        backend = FakeBackend()
        target, cov, _ = self.context_and_future()
        result = self.adapter(backend).forecast(self.request(contexts=(cov, target)))
        self.assertIsInstance(self.adapter(backend), Forecaster)
        self.assertEqual([item.signal_id for item in result.forecasts], ["target-a"])
        self.assertEqual(result.forecasts[0].point_forecast, (10.0, 11.0))
        self.assertEqual([item.quantile for item in result.forecasts[0].quantile_forecasts], [0.1, 0.5, 0.9])
        self.assertEqual(result.forecasts[0].timestamps[-1], self.start + timedelta(seconds=4))

    def test_multivariate_targets_keep_declared_order(self):
        backend = FakeBackend()
        a = self.series("a", (1.0, 2.0, 3.0))
        b = self.series("b", (3.0, 2.0, 1.0))
        result = self.adapter(backend).forecast(self.request(contexts=(a, b), targets=("b", "a")))
        self.assertEqual([item.signal_id for item in result.forecasts], ["b", "a"])
        self.assertEqual(backend.calls[0][0], ((3.0, 2.0, 1.0), (1.0, 2.0, 3.0)))

    def test_past_only_and_known_future_covariates_are_split_for_chronos(self):
        target, cov, future = self.context_and_future()
        other = self.series("ambient", (20.0, 21.0, 22.0), role="covariate")
        backend = FakeBackend()
        self.adapter(backend).forecast(self.request(contexts=(target, cov, other), future=(future,)))
        _, past, known_future, *_ = backend.calls[0]
        self.assertEqual(dict(past), {"load": (4.0, 5.0, 6.0), "ambient": (20.0, 21.0, 22.0)})
        self.assertEqual(dict(known_future), {"load": (7.0, 8.0)})

    def test_point_only_request_does_not_require_quantile_output(self):
        target = self.series("target-a", (1.0, 2.0, 3.0))
        backend = FakeBackend()
        result = self.adapter(backend).forecast(self.request(contexts=(target,), quantiles=()))
        self.assertEqual(result.forecasts[0].quantile_forecasts, ())
        self.assertEqual(backend.calls[0][4], ())

    def test_lazy_backend_is_a_singleton_under_concurrent_access(self):
        target = self.series("target-a", (1.0, 2.0, 3.0))
        adapter = self.adapter()
        backend = FakeBackend()
        calls = []
        original = adapter._load_official_backend

        def load():
            calls.append(1)
            return backend

        with patch.object(adapter, "_load_official_backend", load):
            threads = [threading.Thread(target=lambda: adapter.forecast(self.request(contexts=(target,), quantiles=()))) for _ in range(8)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
        self.assertEqual(len(calls), 1)
        self.assertIsNotNone(original)

    def test_unavailable_error_is_dedicated(self):
        target = self.series("target-a", (1.0, 2.0, 3.0))
        adapter = self.adapter()
        with patch.object(adapter, "_load_official_backend", side_effect=Chronos2UnavailableError("offline")):
            with self.assertRaises(Chronos2UnavailableError):
                adapter.forecast(self.request(contexts=(target,), quantiles=()))

    def test_bad_quality_nonfinite_and_limits_are_rejected(self):
        bad = self.series("target-a", (1.0, 2.0, 3.0), quality=QualityStatus.MISSING)
        with self.assertRaises(ValueError):
            self.adapter(FakeBackend()).forecast(self.request(contexts=(bad,)))
        with self.assertRaises(ValueError):
            self.adapter(FakeBackend()).forecast(self.request(contexts=(self.series("target-a", (1.0, 2.0, 3.0)),), horizon=1025, quantiles=()))
        with self.assertRaises(ValueError):
            self.adapter(FakeBackend()).forecast(self.request(contexts=(self.series("target-a", tuple(float(index) for index in range(8193))),), horizon=1, quantiles=()))
        with self.assertRaisesRegex(ValueError, "at least 2"):
            self.adapter(FakeBackend()).forecast(
                self.request(
                    contexts=(self.series("target-a", (1.0,)),),
                    horizon=1,
                    quantiles=(),
                )
            )
        with self.assertRaisesRegex(ValueError, "configured context_length"):
            self.adapter(FakeBackend(), Chronos2Config(context_length=2)).forecast(
                self.request(
                    contexts=(self.series("target-a", (1.0, 2.0, 3.0)),),
                    horizon=1,
                    quantiles=(),
                )
            )

    def test_timestamp_interval_role_and_future_alignment_are_rejected(self):
        irregular = self.series("target-a", (1.0, 2.0, 3.0), interval_ms=1000)
        irregular = TimeSeries(irregular.metadata, (irregular.points[0], irregular.points[1], SignalPoint(self.start + timedelta(seconds=3), 3.0)))
        with self.assertRaises(ValueError):
            self.adapter(FakeBackend()).forecast(self.request(contexts=(irregular,), quantiles=()))
        target, cov, future = self.context_and_future()
        wrong_future = self.series("load", (4.0, 999.0, 6.0, 7.0, 8.0), role="covariate")
        with self.assertRaises(ValueError):
            self.adapter(FakeBackend()).forecast(self.request(contexts=(target, cov), future=(wrong_future,)))
        wrong_role = self.series("target-a", (1.0, 2.0, 3.0), role="covariate")
        with self.assertRaises(ValueError):
            self.adapter(FakeBackend()).forecast(self.request(contexts=(wrong_role,), quantiles=()))

    def test_quantile_rules_and_output_validation(self):
        target = self.series("target-a", (1.0, 2.0, 3.0))
        for quantiles in ((0.1,), (0.11, 0.5, 0.9)):
            with self.subTest(quantiles=quantiles), self.assertRaises(ValueError):
                self.adapter(FakeBackend()).forecast(self.request(contexts=(target,), quantiles=quantiles))
        with self.assertRaises(ValueError):
            self.adapter(FakeBackend(crossing=True)).forecast(self.request(contexts=(target,)))
        with self.assertRaises(ValueError):
            self.adapter(FakeBackend(p50_offset=0.1)).forecast(self.request(contexts=(target,)))
        with self.assertRaises(ValueError):
            self.adapter(FakeBackend(bad_shape=True)).forecast(self.request(contexts=(target,), quantiles=()))
        with self.assertRaises(ValueError):
            self.adapter(FakeBackend(nonfinite=True)).forecast(self.request(contexts=(target,), quantiles=()))
        point_only = self.adapter(FakeBackend())
        point_only_request = self.request(contexts=(target,), quantiles=())
        with self.assertRaises(ValueError):
            point_only._build_result(
                point_only_request,
                BackendForecast(((10.0, 11.0),), (((9.0,),),), ()),
                (),
                point_only._prepare(point_only_request),
            )
        with self.assertRaises(ValueError):
            quantile_request = self.request(contexts=(target,), quantiles=(0.1, 0.5, 0.9))
            missing = self.adapter(FakeBackend())
            missing._build_result(
                quantile_request,
                BackendForecast(((10.0, 11.0),), None),
                (0.1, 0.5, 0.9),
                missing._prepare(quantile_request),
            )

    def test_config_and_manifest_are_fail_closed(self):
        with self.assertRaises(ValueError):
            Chronos2Config(package_version="2.3.0")
        with self.assertRaises(ValueError):
            Chronos2Config(checkpoint_revision="a" * 40)
        with self.assertRaises(ValueError):
            Chronos2Config(context_length=8193)
        with self.assertRaises(ValueError):
            Chronos2Config(context_length=1)
        with self.assertRaises(ValueError):
            Chronos2Config(device_map="")
        with self.assertRaises(ValueError):
            Chronos2Config(cross_learning=1)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            validate_chronos2_license_manifest({**MANIFEST, "allowed_use": "product-candidate"}, "product-candidate")
        with self.assertRaisesRegex(ValueError, "unknown fields"):
            validate_chronos2_license_manifest(
                {**MANIFEST, "checkpoint_weights_sha256": "d" * 64},
                "commercial-evaluation",
            )

    def test_official_backend_uses_real_api_shapes_and_arguments(self):
        numpy = FakeNumpy()
        pipeline = FakePipeline()
        backend = OfficialChronos2Backend(pipeline, numpy)
        output = backend.forecast(
            ((1.0, 2.0, 3.0),), {"load": (4.0, 5.0, 6.0)}, {"load": (7.0, 8.0)}, 2, (0.1, 0.5, 0.9),
            batch_size=3, context_length=12, cross_learning=True,
        )
        self.assertEqual(output.point_forecast, [[10.0, 10.0]])
        self.assertEqual(output.quantile_forecast, [[[9.0, 10.0, 11.0], [9.0, 10.0, 11.0]]])
        call = pipeline.quantile_calls[0]
        self.assertEqual(call["prediction_length"], 2)
        self.assertEqual(call["batch_size"], 3)
        self.assertEqual(call["context_length"], 12)
        self.assertTrue(call["cross_learning"])
        self.assertTrue(call["limit_prediction_length"])
        payload = call["inputs"][0]
        self.assertEqual(payload["target"].tolist(), ((1.0, 2.0, 3.0),))
        self.assertEqual(payload["past_covariates"]["load"].tolist(), (4.0, 5.0, 6.0))
        self.assertEqual(payload["future_covariates"]["load"].tolist(), (7.0, 8.0))

    def test_official_point_path_extracts_p50_from_predict(self):
        pipeline = FakePipeline()
        output = OfficialChronos2Backend(pipeline, FakeNumpy()).forecast(
            ((1.0, 2.0, 3.0),), {}, {}, 2, (), batch_size=1, context_length=3, cross_learning=False,
        )
        self.assertEqual(output.point_forecast, [[10.0, 11.0]])
        self.assertEqual(pipeline.predict_calls[0]["prediction_length"], 2)

    def test_official_point_path_rejects_api_shape_or_quantile_drift(self):
        class TwoDimensionalPipeline(FakePipeline):
            def predict(self, **kwargs):
                return [FakeTensor([[10.0, 11.0]])]

        class WrongQuantilesPipeline(FakePipeline):
            quantiles = list(OFFICIAL_QUANTILES[:-1])

            def predict(self, **kwargs):
                raw = [[[10.0, 11.0] for _ in self.quantiles]]
                return [FakeTensor(raw)]

        for pipeline in (TwoDimensionalPipeline(), WrongQuantilesPipeline()):
            with self.subTest(pipeline=type(pipeline).__name__), self.assertRaises(ValueError):
                OfficialChronos2Backend(pipeline, FakeNumpy()).forecast(
                    ((1.0, 2.0, 3.0),), {}, {}, 2, (),
                    batch_size=1, context_length=3, cross_learning=False,
                )

    def test_requested_quantiles_require_explicit_matching_backend_levels(self):
        target = self.series("target-a", (1.0, 2.0, 3.0))
        request = self.request(contexts=(target,))
        adapter = self.adapter(FakeBackend())
        quantiles = (
            ((9.0, 10.0, 11.0), (10.0, 11.0, 12.0)),
        )
        with self.assertRaisesRegex(ValueError, "levels are required"):
            adapter._build_result(
                request,
                BackendForecast(((10.0, 11.0),), quantiles, None),
                request.quantiles,
                adapter._prepare(request),
            )


if __name__ == "__main__":
    unittest.main()
