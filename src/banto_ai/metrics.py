"""外部依存ゼロのforecast metrics。入力不整合は黙って補正しない。"""

from __future__ import annotations

from math import isfinite, sqrt
from typing import Mapping, Sequence


class MetricError(ValueError):
    """metric入力が不正、または評価不能。"""


def _pair(actual: Sequence[float], predicted: Sequence[float]) -> list[tuple[float, float]]:
    if not actual or len(actual) != len(predicted):
        raise MetricError("actual and predicted must have the same non-empty length")
    pairs = list(zip(actual, predicted))
    if any(not isfinite(a) or not isfinite(p) for a, p in pairs):
        raise MetricError("metric inputs must be finite")
    return pairs


def mae(actual: Sequence[float], predicted: Sequence[float]) -> float:
    pairs = _pair(actual, predicted)
    return sum(abs(a - p) for a, p in pairs) / len(pairs)


def rmse(actual: Sequence[float], predicted: Sequence[float]) -> float:
    pairs = _pair(actual, predicted)
    return sqrt(sum((a - p) ** 2 for a, p in pairs) / len(pairs))


def mase(actual: Sequence[float], predicted: Sequence[float], scale_history: Sequence[float], seasonality: int = 1) -> float:
    if seasonality <= 0 or len(scale_history) <= seasonality:
        raise MetricError("MASE scale history is insufficient")
    if any(not isfinite(v) for v in scale_history):
        raise MetricError("MASE scale history must be finite")
    scale = sum(abs(scale_history[i] - scale_history[i - seasonality]) for i in range(seasonality, len(scale_history))) / (len(scale_history) - seasonality)
    if scale == 0:
        raise MetricError("MASE scale is zero; metric is inconclusive")
    return mae(actual, predicted) / scale


def _validate_quantiles(actual: Sequence[float], forecasts: Mapping[float, Sequence[float]]) -> list[float]:
    if not actual or not forecasts:
        raise MetricError("actual and quantile forecasts must be non-empty")
    quantiles = list(forecasts)
    if quantiles != sorted(set(quantiles)) or any(not 0 < q < 1 or not isfinite(q) for q in quantiles) or 0.5 not in forecasts:
        raise MetricError("quantiles must be finite, unique, sorted, and in (0, 1)")
    for quantile in quantiles:
        if quantile < 0.5 and 1.0 - quantile not in forecasts:
            raise MetricError("quantiles must contain symmetric central interval pairs")
    for values in forecasts.values():
        if len(values) != len(actual) or any(not isfinite(v) for v in values):
            raise MetricError("quantile values must match actual length and be finite")
    for i in range(len(actual)):
        if any(forecasts[quantiles[j]][i] > forecasts[quantiles[j + 1]][i] for j in range(len(quantiles) - 1)):
            raise MetricError("quantile crossing detected")
    return quantiles


def interval_coverage(actual: Sequence[float], lower: Sequence[float], upper: Sequence[float]) -> float:
    if len(actual) != len(lower) or len(actual) != len(upper) or not actual:
        raise MetricError("interval arrays must have the same non-empty length")
    if any(not isfinite(v) for v in (*actual, *lower, *upper)):
        raise MetricError("interval inputs must be finite")
    if any(lo > hi for lo, hi in zip(lower, upper)):
        raise MetricError("interval lower exceeds upper")
    return sum(lo <= value <= hi for value, lo, hi in zip(actual, lower, upper)) / len(actual)


def interval_width(lower: Sequence[float], upper: Sequence[float]) -> float:
    if not lower or len(lower) != len(upper):
        raise MetricError("interval arrays must have the same non-empty length")
    if any(not isfinite(v) for v in (*lower, *upper)) or any(lo > hi for lo, hi in zip(lower, upper)):
        raise MetricError("invalid interval")
    return sum(hi - lo for lo, hi in zip(lower, upper)) / len(lower)


def weighted_interval_score(actual: Sequence[float], forecasts: Mapping[float, Sequence[float]]) -> float:
    quantiles = _validate_quantiles(actual, forecasts)
    intervals = [(q, 1.0 - q) for q in quantiles if q < 0.5]
    if not intervals:
        raise MetricError("WIS requires at least one central interval")
    score = 0.0
    for i, value in enumerate(actual):
        score += 0.5 * abs(value - forecasts[0.5][i])
    for lower_q, upper_q in intervals:
        lower, upper = forecasts[lower_q], forecasts[upper_q]
        alpha = 2.0 * lower_q
        for i, value in enumerate(actual):
            width = upper[i] - lower[i]
            penalty = 2 / alpha * (lower[i] - value) if value < lower[i] else 2 / alpha * (value - upper[i]) if value > upper[i] else 0.0
            interval_score = width + penalty
            score += alpha * interval_score / 2
    return score / (len(actual) * (0.5 + len(intervals)))


def all_metrics(actual: Sequence[float], predicted: Sequence[float], scale_history: Sequence[float], quantiles: Mapping[float, Sequence[float]] | None = None) -> dict[str, float | str]:
    result: dict[str, float | str] = {"mae": mae(actual, predicted), "rmse": rmse(actual, predicted)}
    try:
        result["mase"] = mase(actual, predicted, scale_history)
    except MetricError as exc:
        result["mase_status"] = "inconclusive: " + str(exc)
    if quantiles is not None:
        qs = _validate_quantiles(actual, quantiles)
        result["wis"] = weighted_interval_score(actual, quantiles)
        lower_q, upper_q = min(qs), max(qs)
        result["nominal_interval_coverage"] = interval_coverage(actual, quantiles[lower_q], quantiles[upper_q])
        result["interval_width"] = interval_width(quantiles[lower_q], quantiles[upper_q])
    return result
