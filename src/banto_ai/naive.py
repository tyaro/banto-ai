"""Phase 0のlast-value naive forecasterとMAE。"""

from __future__ import annotations

from datetime import timedelta
from math import isfinite

from .contracts import Forecaster
from .types import ForecastRequest, ForecastResult, ForecastSeriesResult, QuantileForecast, QualityStatus


class LastValueForecaster(Forecaster):
    """contextの最後の有効値をhorizon全体へ延長する。"""

    def __init__(self, model_version: str = "last-value-0.1.0") -> None:
        self.model_version = model_version

    def forecast(self, request: ForecastRequest) -> ForecastResult:
        contexts = {series.metadata.signal_id: series for series in request.contexts}
        forecasts = []
        for signal_id in request.target_signal_ids:
            context = contexts[signal_id]
            valid_points = [
                point for point in context.points
                if point.value is not None and point.quality_status == QualityStatus.OK
            ]
            if not valid_points:
                raise ValueError(f"context has no valid point for {signal_id}")
            last = valid_points[-1]
            interval_ms = context.metadata.sampling_interval_ms
            last_context_timestamp = context.points[-1].timestamp
            timestamps = tuple(
                last_context_timestamp + timedelta(milliseconds=interval_ms * step)
                for step in range(1, request.horizon + 1)
            )
            values = (last.value,) * request.horizon
            quantiles = tuple(QuantileForecast(q, values) for q in request.quantiles)
            status = QualityStatus.OK if context.points[-1].quality_status == QualityStatus.OK else context.points[-1].quality_status
            forecasts.append(ForecastSeriesResult(
                signal_id=signal_id,
                timestamps=timestamps,
                point_forecast=values,
                quantile_forecasts=quantiles,
                quality_status=status,
            ))
        return ForecastResult(tuple(forecasts), self.model_version, request.profile_version)


def mean_absolute_error(actual: tuple[float, ...], predicted: tuple[float, ...]) -> float:
    if not actual or len(actual) != len(predicted):
        raise ValueError("actual and predicted must have the same non-empty length")
    if any(not isfinite(value) for value in actual + predicted):
        raise ValueError("actual and predicted values must be finite")
    return sum(abs(left - right) for left, right in zip(actual, predicted)) / len(actual)
