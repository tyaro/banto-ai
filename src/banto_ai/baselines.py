"""外部依存ゼロの比較用forecast baseline群。"""

from __future__ import annotations

from math import isfinite

from .contracts import Forecaster
from .naive import LastValueForecaster
from .types import ForecastRequest, ForecastResult, ForecastSeriesResult, QuantileForecast, QualityStatus


class BaselineError(ValueError):
    """baselineの入力または推定に失敗した。暗黙fallbackは行わない。"""


def _finite_history(request: ForecastRequest, signal_id: str) -> tuple[float, ...]:
    series = next((item for item in request.contexts if item.metadata.signal_id == signal_id), None)
    if series is None:
        raise BaselineError(f"context not found: {signal_id}")
    values = tuple(point.value for point in series.points if point.value is not None and point.quality_status == QualityStatus.OK)
    if not values:
        raise BaselineError(f"no valid history: {signal_id}")
    return tuple(float(value) for value in values)


def _result(request: ForecastRequest, model_version: str, values_by_id: dict[str, tuple[float, ...]]) -> ForecastResult:
    forecasts = []
    for signal_id in request.target_signal_ids:
        series = next(item for item in request.contexts if item.metadata.signal_id == signal_id)
        if len(values_by_id[signal_id]) != request.horizon or any(not isfinite(v) for v in values_by_id[signal_id]):
            raise BaselineError(f"non-finite or invalid horizon output: {signal_id}")
        interval = series.metadata.sampling_interval_ms
        end = series.points[-1].timestamp
        timestamps = tuple(end + __import__("datetime").timedelta(milliseconds=interval * step) for step in range(1, request.horizon + 1))
        values = values_by_id[signal_id]
        forecasts.append(ForecastSeriesResult(signal_id, timestamps, values, tuple(QuantileForecast(q, values) for q in request.quantiles)))
    return ForecastResult(tuple(forecasts), model_version, request.profile_version)


class SeasonalNaiveForecaster(Forecaster):
    def __init__(self, season_length: int, model_version: str = "seasonal-naive-0.1.0") -> None:
        if season_length <= 0:
            raise BaselineError("season_length must be positive")
        self.season_length, self.model_version = season_length, model_version

    def forecast(self, request: ForecastRequest) -> ForecastResult:
        values = {}
        for sid in request.target_signal_ids:
            history = _finite_history(request, sid)
            if len(history) < self.season_length:
                raise BaselineError(f"insufficient history for season_length: {sid}")
            values[sid] = tuple(history[-self.season_length + i % self.season_length] for i in range(request.horizon))
        return _result(request, self.model_version, values)


class MovingAverageForecaster(Forecaster):
    def __init__(self, window: int, model_version: str = "moving-average-0.1.0") -> None:
        if window <= 0:
            raise BaselineError("window must be positive")
        self.window, self.model_version = window, model_version

    def forecast(self, request: ForecastRequest) -> ForecastResult:
        values = {}
        for sid in request.target_signal_ids:
            history = _finite_history(request, sid)
            if len(history) < self.window:
                raise BaselineError(f"insufficient history for window: {sid}")
            mean = sum(history[-self.window:]) / self.window
            values[sid] = (mean,) * request.horizon
        return _result(request, self.model_version, values)


class EWMAForecaster(Forecaster):
    def __init__(self, alpha: float, model_version: str = "ewma-0.1.0") -> None:
        if not 0.0 < alpha <= 1.0 or not isfinite(alpha):
            raise BaselineError("alpha must be finite and in (0, 1]")
        self.alpha, self.model_version = alpha, model_version

    def forecast(self, request: ForecastRequest) -> ForecastResult:
        values = {}
        for sid in request.target_signal_ids:
            history = _finite_history(request, sid)
            estimate = history[0]
            for value in history[1:]:
                estimate = self.alpha * value + (1.0 - self.alpha) * estimate
            values[sid] = (estimate,) * request.horizon
        return _result(request, self.model_version, values)


class HoltLinearForecaster(Forecaster):
    def __init__(self, alpha: float = 0.8, beta: float = 0.2, model_version: str = "holt-linear-0.1.0") -> None:
        if not (0 < alpha <= 1 and 0 < beta <= 1):
            raise BaselineError("alpha and beta must be in (0, 1]")
        self.alpha, self.beta, self.model_version = alpha, beta, model_version

    def forecast(self, request: ForecastRequest) -> ForecastResult:
        values = {}
        for sid in request.target_signal_ids:
            history = _finite_history(request, sid)
            if len(history) < 2:
                raise BaselineError("Holt linear trend needs at least two points")
            level, trend = history[0], history[1] - history[0]
            for value in history[1:]:
                old = level
                level = self.alpha * value + (1 - self.alpha) * (level + trend)
                trend = self.beta * (level - old) + (1 - self.beta) * trend
            values[sid] = tuple(level + step * trend for step in range(1, request.horizon + 1))
        return _result(request, self.model_version, values)


class CovariateLinearRegressionForecaster(Forecaster):
    """通常方程をGauss-Jordan消去で解く小さなOLS。特異行列は失敗する。"""

    def __init__(self, covariate_ids: tuple[str, ...], model_version: str = "linear-regression-covariates-0.1.0") -> None:
        if not covariate_ids or len(set(covariate_ids)) != len(covariate_ids):
            raise BaselineError("covariate_ids must be non-empty and unique")
        self.covariate_ids, self.model_version = covariate_ids, model_version

    @staticmethod
    def _solve(matrix: list[list[float]]) -> list[float]:
        n = len(matrix)
        for col in range(n):
            pivot = max(range(col, n), key=lambda row: abs(matrix[row][col]))
            if abs(matrix[pivot][col]) <= 1e-12:
                raise BaselineError("singular or insufficient regression design matrix")
            matrix[col], matrix[pivot] = matrix[pivot], matrix[col]
            divisor = matrix[col][col]
            matrix[col] = [x / divisor for x in matrix[col]]
            for row in range(n):
                if row == col:
                    continue
                factor = matrix[row][col]
                matrix[row] = [a - factor * b for a, b in zip(matrix[row], matrix[col])]
        return [matrix[row][-1] for row in range(n)]

    def forecast(self, request: ForecastRequest) -> ForecastResult:
        if len(request.known_future_covariates) != len(self.covariate_ids):
            raise BaselineError("known future covariates are required for every configured covariate")
        covs = {s.metadata.signal_id: s for s in request.known_future_covariates}
        for cid in self.covariate_ids:
            if cid not in covs:
                raise BaselineError(f"missing covariate: {cid}")
        values = {}
        for sid in request.target_signal_ids:
            target = next(s for s in request.contexts if s.metadata.signal_id == sid)
            rows = []
            for index, point in enumerate(target.points):
                if point.value is None or point.quality_status != QualityStatus.OK:
                    continue
                row = [1.0]
                for cid in self.covariate_ids:
                    cov = covs[cid]
                    if index >= len(cov.points) or cov.points[index].value is None:
                        raise BaselineError("missing aligned covariate in regression history")
                    row.append(float(cov.points[index].value))
                rows.append((row, float(point.value)))
            width = len(self.covariate_ids) + 1
            if len(rows) < width:
                raise BaselineError("insufficient regression observations")
            normal = [[0.0] * (width + 1) for _ in range(width)]
            for row, y in rows:
                for i in range(width):
                    for j in range(width):
                        normal[i][j] += row[i] * row[j]
                    normal[i][-1] += row[i] * y
            coefficients = self._solve(normal)
            start = len(target.points)
            predictions = []
            for offset in range(request.horizon):
                row = [1.0]
                for cid in self.covariate_ids:
                    cov = covs[cid]
                    index = start + offset
                    if index >= len(cov.points) or cov.points[index].value is None:
                        raise BaselineError("future covariate horizon is missing")
                    row.append(float(cov.points[index].value))
                value = sum(a * b for a, b in zip(coefficients, row))
                if not isfinite(value):
                    raise BaselineError("regression produced non-finite output")
                predictions.append(value)
            values[sid] = tuple(predictions)
        return _result(request, self.model_version, values)


def build_baseline(name: str, parameters: dict[str, object] | None = None) -> Forecaster:
    params = {} if parameters is None else parameters
    if not isinstance(params, dict):
        raise BaselineError("parameters must be an object")
    def exact(allowed: set[str]) -> None:
        unknown = set(params) - allowed
        if unknown:
            raise BaselineError(f"unknown parameters for {name}: {sorted(unknown)}")
    def positive_int(key: str, default: int) -> int:
        value = params.get(key, default)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise BaselineError(f"{key} must be a positive integer")
        return value
    def unit_float(key: str, default: float) -> float:
        value = params.get(key, default)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or not 0 < value <= 1:
            raise BaselineError(f"{key} must be a finite number in (0, 1]")
        return float(value)
    if name == "last-value":
        exact(set())
        return LastValueForecaster()
    if name == "seasonal-naive":
        exact({"season_length"})
        return SeasonalNaiveForecaster(positive_int("season_length", 1))
    if name == "moving-average":
        exact({"window"})
        return MovingAverageForecaster(positive_int("window", 3))
    if name == "ewma":
        exact({"alpha"})
        return EWMAForecaster(unit_float("alpha", 0.3))
    if name in {"holt-linear", "autoets"}:
        exact({"alpha", "beta"})
        return HoltLinearForecaster(unit_float("alpha", 0.8), unit_float("beta", 0.2))
    if name == "linear-regression-covariates":
        exact({"covariate_ids"})
        values = params.get("covariate_ids")
        if not isinstance(values, list) or not values or any(not isinstance(x, str) or not x for x in values) or len(set(values)) != len(values):
            raise BaselineError("covariate_ids must be a non-empty list of unique strings")
        return CovariateLinearRegressionForecaster(tuple(values))
    raise BaselineError(f"unknown baseline: {name}")
