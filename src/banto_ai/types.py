"""Forecast／anomaly契約で共有する最小の型。外部依存を持たない。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from math import isfinite
from typing import Mapping, Sequence


class QualityStatus(StrEnum):
    OK = "ok"
    MISSING = "missing"
    STALE = "stale"
    INVALID = "invalid"
    OUT_OF_ORDER = "out_of_order"


@dataclass(frozen=True, slots=True)
class SignalMetadata:
    signal_id: str
    name: str
    unit: str
    sampling_interval_ms: int
    role: str = "target"

    def __post_init__(self) -> None:
        if not self.signal_id or not self.name or not self.unit:
            raise ValueError("signal_id, name, and unit must be non-empty")
        if self.sampling_interval_ms <= 0:
            raise ValueError("sampling_interval_ms must be positive")


@dataclass(frozen=True, slots=True)
class SignalPoint:
    timestamp: datetime
    value: float | None
    quality_status: QualityStatus = QualityStatus.OK

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        if self.value is not None and not isfinite(self.value):
            raise ValueError("value must be finite or None")


@dataclass(frozen=True, slots=True)
class TimeSeries:
    metadata: SignalMetadata
    points: tuple[SignalPoint, ...]

    def __post_init__(self) -> None:
        if not self.points:
            raise ValueError("points must not be empty")
        timestamps = [point.timestamp for point in self.points]
        if any(previous >= current for previous, current in zip(timestamps, timestamps[1:])):
            raise ValueError("points must have strictly increasing timestamps")


@dataclass(frozen=True, slots=True)
class ForecastRequest:
    contexts: tuple[TimeSeries, ...]
    target_signal_ids: tuple[str, ...]
    horizon: int
    quantiles: tuple[float, ...] = ()
    profile_version: str = "baseline"
    known_future_covariates: tuple[TimeSeries, ...] = ()

    def __post_init__(self) -> None:
        if not self.contexts:
            raise ValueError("contexts must not be empty")
        context_ids = tuple(series.metadata.signal_id for series in self.contexts)
        if len(set(context_ids)) != len(context_ids):
            raise ValueError("context signal IDs must be unique")
        future_covariate_ids = tuple(series.metadata.signal_id for series in self.known_future_covariates)
        if len(set(future_covariate_ids)) != len(future_covariate_ids):
            raise ValueError("known future covariate signal IDs must be unique")
        if not self.target_signal_ids:
            raise ValueError("target_signal_ids must not be empty")
        if len(set(self.target_signal_ids)) != len(self.target_signal_ids):
            raise ValueError("target_signal_ids must be unique")
        if any(signal_id not in context_ids for signal_id in self.target_signal_ids):
            raise ValueError("every target signal ID must have a context")
        if self.horizon <= 0:
            raise ValueError("horizon must be positive")
        if any(not 0.0 < quantile < 1.0 for quantile in self.quantiles):
            raise ValueError("quantiles must be between 0 and 1")
        if tuple(sorted(set(self.quantiles))) != self.quantiles:
            raise ValueError("quantiles must be sorted and unique")


@dataclass(frozen=True, slots=True)
class QuantileForecast:
    quantile: float
    values: tuple[float, ...]

    def __post_init__(self) -> None:
        if not 0.0 < self.quantile < 1.0:
            raise ValueError("quantile must be between 0 and 1")
        if not self.values or any(not isfinite(value) for value in self.values):
            raise ValueError("quantile forecast values must be non-empty and finite")


@dataclass(frozen=True, slots=True)
class ForecastSeriesResult:
    signal_id: str
    timestamps: tuple[datetime, ...]
    point_forecast: tuple[float, ...]
    quantile_forecasts: tuple[QuantileForecast, ...]
    quality_status: QualityStatus = QualityStatus.OK

    def __post_init__(self) -> None:
        if not self.signal_id:
            raise ValueError("signal_id must be non-empty")
        if not self.timestamps or not self.point_forecast:
            raise ValueError("timestamps and point_forecast must be non-empty")
        if any(not isfinite(value) for value in self.point_forecast):
            raise ValueError("point_forecast values must be finite")
        if any(timestamp.tzinfo is None for timestamp in self.timestamps):
            raise ValueError("forecast timestamps must be timezone-aware")
        if any(previous >= current for previous, current in zip(self.timestamps, self.timestamps[1:])):
            raise ValueError("forecast timestamps must be strictly increasing")
        if len(self.timestamps) != len(self.point_forecast):
            raise ValueError("timestamps and point_forecast lengths must match")
        quantiles = tuple(forecast.quantile for forecast in self.quantile_forecasts)
        if quantiles != tuple(sorted(set(quantiles))):
            raise ValueError("quantile forecasts must be sorted and unique")
        if any(len(forecast.values) != len(self.timestamps) for forecast in self.quantile_forecasts):
            raise ValueError("quantile forecast lengths must match timestamps")


@dataclass(frozen=True, slots=True)
class ForecastResult:
    forecasts: tuple[ForecastSeriesResult, ...]
    model_version: str
    profile_version: str

    def __post_init__(self) -> None:
        if not self.forecasts:
            raise ValueError("forecasts must not be empty")
        if not self.model_version or not self.profile_version:
            raise ValueError("model_version and profile_version must be non-empty")
        signal_ids = tuple(forecast.signal_id for forecast in self.forecasts)
        if len(set(signal_ids)) != len(signal_ids):
            raise ValueError("forecast signal IDs must be unique")


@dataclass(frozen=True, slots=True)
class AnomalyRequest:
    observations: tuple[TimeSeries, ...]
    model_version: str
    profile_version: str = "baseline"

    def __post_init__(self) -> None:
        if not self.observations:
            raise ValueError("observations must not be empty")
        signal_ids = tuple(series.metadata.signal_id for series in self.observations)
        if len(set(signal_ids)) != len(signal_ids):
            raise ValueError("observation signal IDs must be unique")
        if not self.model_version or not self.profile_version:
            raise ValueError("model_version and profile_version must be non-empty")


@dataclass(frozen=True, slots=True)
class AnomalySeriesResult:
    signal_id: str
    timestamps: tuple[datetime, ...]
    scores: tuple[float, ...]
    quality_status: QualityStatus
    labels: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.signal_id:
            raise ValueError("signal_id must be non-empty")
        if not self.scores or any(not isfinite(value) for value in self.scores):
            raise ValueError("scores must be non-empty and finite")
        if len(self.timestamps) != len(self.scores):
            raise ValueError("timestamps and scores lengths must match")
        if any(timestamp.tzinfo is None for timestamp in self.timestamps):
            raise ValueError("anomaly timestamps must be timezone-aware")
        if any(previous >= current for previous, current in zip(self.timestamps, self.timestamps[1:])):
            raise ValueError("anomaly timestamps must be strictly increasing")
        if self.labels and len(self.labels) != len(self.scores):
            raise ValueError("labels and scores lengths must match")


@dataclass(frozen=True, slots=True)
class AnomalyResult:
    scores: tuple[AnomalySeriesResult, ...]
    model_version: str
    profile_version: str

    def __post_init__(self) -> None:
        if not self.scores:
            raise ValueError("scores must not be empty")
        if not self.model_version or not self.profile_version:
            raise ValueError("model_version and profile_version must be non-empty")
        signal_ids = tuple(score.signal_id for score in self.scores)
        if len(set(signal_ids)) != len(signal_ids):
            raise ValueError("anomaly signal IDs must be unique")


MetadataMap = Mapping[str, str | int | float | bool | None]
SequenceOfPoints = Sequence[SignalPoint]
