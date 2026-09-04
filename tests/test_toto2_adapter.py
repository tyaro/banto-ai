from __future__ import annotations

from datetime import datetime, timedelta, timezone
import threading
import unittest
from unittest.mock import patch

from banto_ai.adapters.toto2 import (
    BackendForecast,
    OFFICIAL_QUANTILES,
    OfficialToto2Backend,
    Toto2Adapter,
    Toto2Config,
    validate_toto2_license_manifest,
)
from banto_ai.contracts import Forecaster
from banto_ai.types import ForecastRequest, QualityStatus, SignalMetadata, SignalPoint, TimeSeries


MANIFEST = {
    "schema_version": "0.1", "manifest_type": "model-license", "model_id": "toto-2-4m",
    "code_license": "Apache-2.0", "weights_license": "Apache-2.0", "allowed_use": "commercial-evaluation",
    "source_url": "https://huggingface.co/Datadog/Toto-2.0-4m", "package_name": "toto-2",
    "package_version": "2.0.0", "package_sha256": "5eb922f8162a800d6d31cffb10e3f4c079276b12c41e272129e5b4a930943f71",
    "checkpoint": "Datadog/Toto-2.0-4m", "checkpoint_revision": "8306a9801cf98c0f5ffe4b2dcc8f496e616d84d9", "verified_at": "2026-09-04",
}


class FakeBackend:
    def __init__(self, *, crossing=False):
        self.calls = []
        self.crossing = crossing

    def forecast(self, variates, observed_mask, horizon, **kwargs):
        self.calls.append((variates, observed_mask, horizon, kwargs))
        point = [[10.0 + variate for _ in range(horizon)] for variate in range(len(variates))]
        quantiles = []
        for index, _ in enumerate(OFFICIAL_QUANTILES):
            quantiles.append([[value + (index - 4) for value in row] for row in point])
        if self.crossing:
            quantiles[0][0][0], quantiles[1][0][0] = quantiles[1][0][0], quantiles[0][0][0]
        return BackendForecast(point, quantiles, OFFICIAL_QUANTILES)


class Toto2AdapterTests(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def series(self, signal_id, values, *, role="target", interval_ms=1000, quality=QualityStatus.OK):
        meta = SignalMetadata(signal_id, signal_id, "unit", interval_ms, role)
        return TimeSeries(meta, tuple(SignalPoint(self.start + timedelta(milliseconds=interval_ms * i), value, quality) for i, value in enumerate(values)))

    def request(self, contexts, *, targets=("a",), horizon=2, quantiles=(0.1, 0.5, 0.9), future=()):
        return ForecastRequest(tuple(contexts), tuple(targets), horizon, tuple(quantiles), known_future_covariates=tuple(future))

    def test_multivariate_padding_and_target_projection(self):
        backend = FakeBackend()
        target = self.series("a", tuple(float(i) for i in range(120)))
        other = self.series("b", tuple(float(i + 1) for i in range(120)), role="covariate")
        result = Toto2Adapter(MANIFEST, backend=backend).forecast(self.request((other, target)))
        self.assertIsInstance(Toto2Adapter(MANIFEST, backend=backend), Forecaster)
        variates, masks, _, kwargs = backend.calls[0]
        self.assertEqual(len(variates), 2)
        self.assertEqual(len(variates[0]), 128)
        self.assertEqual(variates[0][:8], (0.0,) * 8)
        self.assertEqual(masks[0][:8], (False,) * 8)
        self.assertEqual(masks[0][8:], (True,) * 120)
        self.assertEqual(kwargs, {"decode_block_size": None, "has_missing_values": True})
        self.assertEqual([forecast.signal_id for forecast in result.forecasts], ["a"])
        self.assertEqual(result.forecasts[0].point_forecast, (10.0, 10.0))
        self.assertEqual([q.quantile for q in result.forecasts[0].quantile_forecasts], [0.1, 0.5, 0.9])

    def test_known_future_missing_and_short_context_fail_closed(self):
        target = self.series("a", tuple(float(i) for i in range(120)))
        future = self.series("f", tuple(float(i) for i in range(135)), role="covariate")
        with self.assertRaisesRegex(ValueError, "known-future"):
            Toto2Adapter(MANIFEST, backend=FakeBackend()).forecast(self.request((target,), future=(future,)))
        with self.assertRaises(ValueError):
            Toto2Adapter(MANIFEST, backend=FakeBackend()).forecast(self.request((self.series("a", tuple(range(31))),)))
        with self.assertRaises(ValueError):
            Toto2Adapter(MANIFEST, backend=FakeBackend()).forecast(self.request((self.series("a", tuple(range(120)), quality=QualityStatus.MISSING),)))

    def test_crossing_and_config_are_rejected(self):
        target = self.series("a", tuple(float(i) for i in range(120)))
        with self.assertRaisesRegex(ValueError, "crossing"):
            Toto2Adapter(MANIFEST, backend=FakeBackend(crossing=True)).forecast(self.request((target,)))
        with self.assertRaises(ValueError):
            Toto2Config(device="cuda")
        with self.assertRaises(ValueError):
            validate_toto2_license_manifest({**MANIFEST, "weights_license": "MIT"}, "commercial-evaluation")

    def test_lazy_backend_is_loaded_once(self):
        target = self.series("a", tuple(float(i) for i in range(120)))
        adapter = Toto2Adapter(MANIFEST)
        backend = FakeBackend(); calls = []
        errors = []
        def load():
            calls.append(1); return backend
        def worker():
            try:
                adapter.forecast(self.request((target,), quantiles=()))
            except BaseException as exc:
                errors.append(exc)
        with patch.object(adapter, "_load_official_backend", load):
            threads = [threading.Thread(target=worker) for _ in range(4)]
            for thread in threads: thread.start()
            for thread in threads: thread.join()
        self.assertEqual(len(calls), 1)
        self.assertEqual(errors, [])


class OfficialToto2BackendTests(unittest.TestCase):
    def test_normalizes_q_b_v_h_and_passes_official_arguments(self):
        class Tensor:
            def __init__(self, value): self.value = value
            def tolist(self): return self.value
            def detach(self): return self
            def cpu(self): return self
        class Torch:
            float32 = "float32"; bool = "bool"; long = "long"
            def tensor(self, value, **kwargs): return Tensor(value)
            def zeros(self, shape, **kwargs): return Tensor([[0] * shape[1]])
            def no_grad(self):
                class Context:
                    def __enter__(self): return self
                    def __exit__(self, *args): return False
                return Context()
        class Model:
            def __init__(self): self.call = None
            def forecast(self, inputs, **kwargs):
                self.call = (inputs, kwargs)
                return Tensor([[[[float(q + v + h) for h in range(2)] for v in range(2)]] for q in range(9)])
        model = Model(); backend = OfficialToto2Backend(model, Torch())
        output = backend.forecast(((1.0, 2.0), (3.0, 4.0)), ((True, True), (True, True)), 2, decode_block_size=None, has_missing_values=False)
        self.assertEqual(len(output.quantile_forecast), 9)
        self.assertEqual(output.quantile_forecast[4], [[4.0, 5.0], [5.0, 6.0]])
        self.assertEqual(model.call[1], {"horizon": 2, "decode_block_size": None, "has_missing_values": False})


if __name__ == "__main__":
    unittest.main()
