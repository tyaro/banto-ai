"""Dependency-free TimesFM 3.0 adapter for research-only evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import isfinite
import re
from types import MappingProxyType
from typing import Any, Mapping, Protocol, Sequence

from ..contracts import Forecaster
from ..types import (
    ForecastRequest,
    ForecastResult,
    ForecastSeriesResult,
    QuantileForecast,
    QualityStatus,
    TimeSeries,
)

OFFICIAL_QUANTILES = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
DEFAULT_REVISION = "43046b85ec22d584a13f8098c2ed39c889e129c2"
OFFICIAL_CHECKPOINT = "google/timesfm-3.0-pytorch"
OFFICIAL_SOURCE_URL = "https://huggingface.co/google/timesfm-3.0-pytorch"
OFFICIAL_PACKAGE_NAME = "timesfm"
OFFICIAL_PACKAGE_VERSION = "3.0.0"
OFFICIAL_PACKAGE_SHA256 = "0ad3e6b2226a85d665ebca3b5711b875cdef816a6f8ae0d3acbd5361f3e4b63d"
PROVENANCE_VERIFIED_AT = "2026-09-03"
_SHA = re.compile(r"^[0-9a-f]{40}$")
_REQUIRED_LICENSE_FIELDS = {
    "schema_version": "0.1",
    "manifest_type": "model-license",
    "model_id": "timesfm-3.0",
    "code_license": "Apache-2.0",
    "weights_license": "timesfm-non-commercial-license-v1.0",
    "allowed_use": "research-only",
    "source_url": OFFICIAL_SOURCE_URL,
    "package_name": OFFICIAL_PACKAGE_NAME,
    "package_version": OFFICIAL_PACKAGE_VERSION,
    "package_sha256": OFFICIAL_PACKAGE_SHA256,
    "checkpoint": OFFICIAL_CHECKPOINT,
    "checkpoint_revision": DEFAULT_REVISION,
    "verified_at": PROVENANCE_VERIFIED_AT,
}
_LICENSE_FIELDS = frozenset((*_REQUIRED_LICENSE_FIELDS, "notes"))


class AdapterUnavailableError(RuntimeError):
    """The optional official backend is unavailable in this environment."""


def validate_timesfm3_license_manifest(
    manifest: Mapping[str, object],
    requested_use: str,
    *,
    package_version: str = OFFICIAL_PACKAGE_VERSION,
    checkpoint_path: str = OFFICIAL_CHECKPOINT,
    checkpoint_revision: str = DEFAULT_REVISION,
) -> None:
    """Fail closed unless the supplied manifest is the official research license."""
    if not isinstance(manifest, Mapping):
        raise ValueError("model-license manifest must be a mapping")
    if requested_use != "research-only":
        raise ValueError("TimesFM 3 may only be requested for research-only use")
    unknown_fields = set(manifest) - _LICENSE_FIELDS
    if unknown_fields:
        raise ValueError(
            "model-license manifest has unknown fields: "
            f"{sorted(str(field) for field in unknown_fields)}"
        )
    for field, expected in _REQUIRED_LICENSE_FIELDS.items():
        if field not in manifest:
            raise ValueError(f"model-license manifest is missing {field}")
        if not isinstance(manifest[field], str):
            raise ValueError(f"model-license manifest field {field} must be a string")
        if manifest[field] != expected:
            raise ValueError(f"model-license manifest has invalid {field}")
    if "notes" in manifest and not isinstance(manifest["notes"], str):
        raise ValueError("model-license manifest field notes must be a string")
    if manifest["package_version"] != package_version:
        raise ValueError("manifest package_version does not match adapter config")
    if manifest["checkpoint"] != checkpoint_path:
        raise ValueError("manifest checkpoint does not match adapter config")
    if manifest["checkpoint_revision"] != checkpoint_revision:
        raise ValueError("manifest checkpoint_revision does not match adapter config")


@dataclass(frozen=True, slots=True)
class TimesFM3Config:
    package_version: str = OFFICIAL_PACKAGE_VERSION
    checkpoint_path: str = OFFICIAL_CHECKPOINT
    checkpoint_revision: str = DEFAULT_REVISION
    requested_use: str = "research-only"
    per_core_batch_size: int = 1
    device: str = "cpu"
    local_files_only: bool = True

    def __post_init__(self) -> None:
        if self.package_version != OFFICIAL_PACKAGE_VERSION:
            raise ValueError("package_version must be exactly 3.0.0")
        if self.checkpoint_path != OFFICIAL_CHECKPOINT:
            raise ValueError("checkpoint_path must identify the official TimesFM 3 checkpoint")
        if not isinstance(self.checkpoint_revision, str) or not _SHA.fullmatch(self.checkpoint_revision):
            raise ValueError("checkpoint_revision must be a lowercase 40-character SHA")
        if self.requested_use != "research-only":
            raise ValueError("requested_use must be research-only")
        if isinstance(self.per_core_batch_size, bool) or not isinstance(self.per_core_batch_size, int):
            raise ValueError("per_core_batch_size must be an integer")
        if self.per_core_batch_size <= 0:
            raise ValueError("per_core_batch_size must be positive")
        if not isinstance(self.device, str) or not self.device:
            raise ValueError("device must be a non-empty string")
        if not isinstance(self.local_files_only, bool):
            raise ValueError("local_files_only must be boolean")


@dataclass(frozen=True, slots=True)
class BackendForecast:
    """Backend output shaped targets x horizon [x all nine quantiles]."""

    point_forecast: Sequence[Sequence[float]]
    quantile_forecast: Sequence[Sequence[Sequence[float]]] | None = None


class TimesFM3Backend(Protocol):
    """Dependency-free backend boundary using ordinary nested sequences."""

    def forecast(
        self,
        targets: Sequence[Sequence[float]],
        past_only_covariates: Sequence[Sequence[float]],
        past_future_covariates: Sequence[Sequence[float]],
        horizon: int,
        return_quantiles: bool,
    ) -> BackendForecast: ...


class OfficialTimesFM3Backend:
    """Thin, testable wrapper around an initialized official evaluator."""

    def __init__(self, evaluator: Any, numpy_module: Any) -> None:
        self._evaluator = evaluator
        self._numpy = numpy_module

    def forecast(
        self,
        targets: Sequence[Sequence[float]],
        past_only_covariates: Sequence[Sequence[float]],
        past_future_covariates: Sequence[Sequence[float]],
        horizon: int,
        return_quantiles: bool,
    ) -> BackendForecast:
        target_matrix = self._array(targets)
        past_matrix = self._array(past_only_covariates) if past_only_covariates else None
        past_future_matrix = self._array(past_future_covariates) if past_future_covariates else None
        try:
            outputs = list(self._evaluator.predict_batch(
                contexts=[target_matrix],
                horizon=horizon,
                past_only_covariates=[past_matrix],
                past_future_covariates=[past_future_matrix],
                return_quantiles=return_quantiles,
                use_symmetric_averaging=False,
                sort_quantiles=True,
                padding_mode="none",
            ))
        except TypeError as exc:
            raise ValueError("TimesFM 3 predict_batch must return an iterator") from exc
        if len(outputs) != 1:
            raise ValueError("TimesFM 3 predict_batch must return exactly one ForecastOutput")
        output = outputs[0]
        if not hasattr(output, "forecast"):
            raise ValueError("TimesFM 3 ForecastOutput is missing forecast")
        if not hasattr(output, "quantiles"):
            raise ValueError("TimesFM 3 ForecastOutput is missing quantiles")
        try:
            forecast = output.forecast.tolist()
            quantiles = (
                None if output.quantiles is None else output.quantiles.tolist()
            )
        except AttributeError as exc:
            raise ValueError("TimesFM 3 ForecastOutput arrays must support tolist()") from exc
        return BackendForecast(forecast, quantiles)

    def _array(self, values: Sequence[Sequence[float]]) -> Any:
        try:
            matrix = tuple(tuple(row) for row in values)
        except TypeError as exc:
            raise ValueError("TimesFM 3 input must be a nested sequence") from exc
        if any(
            not _is_finite_real(value)
            for row in matrix
            for value in row
        ):
            raise ValueError("TimesFM 3 input must contain finite int/float values")
        return self._numpy.asarray(matrix, dtype=self._numpy.float32)


@dataclass(frozen=True, slots=True)
class _PreparedInput:
    targets: tuple[tuple[float, ...], ...]
    past_only_covariates: tuple[tuple[float, ...], ...]
    past_future_covariates: tuple[tuple[float, ...], ...]
    last_timestamp: datetime
    interval_ms: int


class TimesFM3Adapter(Forecaster):
    """Adapt Banto series to a pinned, licensed TimesFM 3 evaluation."""

    def __init__(
        self,
        license_manifest: Mapping[str, object],
        config: TimesFM3Config | None = None,
        backend: TimesFM3Backend | None = None,
    ) -> None:
        self.config = config or TimesFM3Config()
        validate_timesfm3_license_manifest(
            license_manifest,
            self.config.requested_use,
            package_version=self.config.package_version,
            checkpoint_path=self.config.checkpoint_path,
            checkpoint_revision=self.config.checkpoint_revision,
        )
        self.license_manifest = MappingProxyType(dict(license_manifest))
        self._backend = backend

    @property
    def model_version(self) -> str:
        return f"timesfm3-{self.config.package_version}@{self.config.checkpoint_revision}"

    def forecast(self, request: ForecastRequest) -> ForecastResult:
        quantiles = self._validate_request(request)
        prepared = self._prepare(request)
        backend = self._backend or self._load_official_backend()
        try:
            output = backend.forecast(
                prepared.targets,
                prepared.past_only_covariates,
                prepared.past_future_covariates,
                request.horizon,
                bool(quantiles),
            )
        except AdapterUnavailableError:
            raise
        except (ImportError, ModuleNotFoundError) as exc:
            raise AdapterUnavailableError("TimesFM 3 dependencies are unavailable") from exc
        return self._build_result(request, output, quantiles, prepared)

    @staticmethod
    def _validate_request(request: ForecastRequest) -> tuple[float, ...]:
        if request.quantiles and 0.5 not in request.quantiles:
            raise ValueError("requested quantiles must contain 0.5")
        if any(quantile not in OFFICIAL_QUANTILES for quantile in request.quantiles):
            raise ValueError("requested quantiles must be a supported TimesFM 3 subset")
        contexts = {series.metadata.signal_id: series for series in request.contexts}
        future_ids = tuple(series.metadata.signal_id for series in request.known_future_covariates)
        if len(set(future_ids)) != len(future_ids):
            raise ValueError("known-future covariate IDs must be unique")
        if set(future_ids) & set(request.target_signal_ids):
            raise ValueError("target signals cannot also be known-future covariates")
        if any(signal_id not in contexts for signal_id in future_ids):
            raise ValueError("known-future covariates require matching context series")
        for signal_id in request.target_signal_ids:
            if contexts[signal_id].metadata.role != "target":
                raise ValueError("target signal context must have target role")
        for series in request.contexts:
            if series.metadata.signal_id not in request.target_signal_ids and series.metadata.role == "target":
                raise ValueError("non-target context cannot have target role")
            TimesFM3Adapter._validate_points(series, "context")
        for series in request.known_future_covariates:
            if series.metadata.role == "target":
                raise ValueError("known-future covariate cannot have target role")
            TimesFM3Adapter._validate_points(series, "known-future covariate")
        return tuple(request.quantiles)

    @staticmethod
    def _validate_points(series: TimeSeries, label: str) -> None:
        if any(
            point.quality_status != QualityStatus.OK
            or point.value is None
            or not _is_finite_real(point.value)
            for point in series.points
        ):
            raise ValueError(
                f"all {label} values must be finite int/float values with OK quality"
            )

    @staticmethod
    def _prepare(request: ForecastRequest) -> _PreparedInput:
        contexts = {series.metadata.signal_id: series for series in request.contexts}
        reference = contexts[request.target_signal_ids[0]]
        context_timestamps = tuple(point.timestamp for point in reference.points)
        context_length = len(context_timestamps)
        interval_ms = reference.metadata.sampling_interval_ms
        for series in request.contexts:
            if len(series.points) != context_length:
                raise ValueError("all context series must have equal lengths")
            if series.metadata.sampling_interval_ms != interval_ms:
                raise ValueError("all context series must have equal sampling intervals")
            if tuple(point.timestamp for point in series.points) != context_timestamps:
                raise ValueError("all context series must have equal timestamps")

        future_by_id = {
            series.metadata.signal_id: series
            for series in request.known_future_covariates
        }
        expected_future_timestamps = tuple(
            context_timestamps[-1] + timedelta(milliseconds=interval_ms * step)
            for step in range(1, request.horizon + 1)
        )
        past_only: list[tuple[float, ...]] = []
        past_future: list[tuple[float, ...]] = []
        target_ids = set(request.target_signal_ids)
        for series in request.contexts:
            signal_id = series.metadata.signal_id
            if signal_id in target_ids:
                continue
            context_values = tuple(float(point.value) for point in series.points)
            combined = future_by_id.get(signal_id)
            if combined is None:
                past_only.append(context_values)
                continue
            if combined.metadata.role != series.metadata.role:
                raise ValueError("known-future covariate role must match its context role")
            if combined.metadata.unit != series.metadata.unit:
                raise ValueError("known-future covariate unit must match its context unit")
            if combined.metadata.sampling_interval_ms != interval_ms:
                raise ValueError("known-future covariate interval is not aligned")
            if len(combined.points) != context_length + request.horizon:
                raise ValueError("known-future covariate must contain context plus exactly horizon points")
            prefix = combined.points[:context_length]
            suffix = combined.points[context_length:]
            if tuple(point.timestamp for point in prefix) != context_timestamps:
                raise ValueError("known-future covariate context timestamps do not match")
            if tuple(float(point.value) for point in prefix) != context_values:
                raise ValueError("known-future covariate context values do not match")
            if tuple(point.timestamp for point in suffix) != expected_future_timestamps:
                raise ValueError("known-future covariate future timestamps are not aligned")
            past_future.append(tuple(float(point.value) for point in combined.points))

        targets = tuple(
            tuple(float(point.value) for point in contexts[signal_id].points)
            for signal_id in request.target_signal_ids
        )
        return _PreparedInput(
            targets,
            tuple(past_only),
            tuple(past_future),
            context_timestamps[-1],
            interval_ms,
        )

    def _load_official_backend(self) -> TimesFM3Backend:
        try:
            import numpy
            from timesfm3 import ModelConfig, TimesFM3Evaluator

            model_config = ModelConfig(
                checkpoint_path=self.config.checkpoint_path,
                revision=self.config.checkpoint_revision,
                device=self.config.device,
                local_files_only=self.config.local_files_only,
                per_core_batch_size=self.config.per_core_batch_size,
            )
            evaluator = TimesFM3Evaluator(model_config)
        except (ImportError, ModuleNotFoundError) as exc:
            raise AdapterUnavailableError(
                "install the optional TimesFM 3 dependencies to use this adapter"
            ) from exc
        return OfficialTimesFM3Backend(evaluator, numpy)

    def _build_result(
        self,
        request: ForecastRequest,
        output: BackendForecast,
        requested_quantiles: tuple[float, ...],
        prepared: _PreparedInput,
    ) -> ForecastResult:
        if not hasattr(output, "point_forecast"):
            raise ValueError("backend output is missing point_forecast")
        if not hasattr(output, "quantile_forecast"):
            raise ValueError("backend output is missing quantile_forecast")
        target_count = len(request.target_signal_ids)
        points = self._validate_point_matrix(
            output.point_forecast, target_count, request.horizon,
        )
        full_quantiles = self._validate_quantile_tensor(
            output.quantile_forecast,
            target_count,
            request.horizon,
            required=bool(requested_quantiles),
        )
        selected_indices = tuple(
            OFFICIAL_QUANTILES.index(quantile) for quantile in requested_quantiles
        )
        timestamps = tuple(
            prepared.last_timestamp
            + timedelta(milliseconds=prepared.interval_ms * step)
            for step in range(1, request.horizon + 1)
        )
        forecasts = []
        for target_index, signal_id in enumerate(request.target_signal_ids):
            quantile_forecasts = tuple(
                QuantileForecast(
                    quantile,
                    tuple(
                        full_quantiles[target_index][step][quantile_index]
                        for step in range(request.horizon)
                    ),
                )
                for quantile, quantile_index in zip(
                    requested_quantiles, selected_indices,
                )
            )
            forecasts.append(ForecastSeriesResult(
                signal_id=signal_id,
                timestamps=timestamps,
                point_forecast=points[target_index],
                quantile_forecasts=quantile_forecasts,
            ))
        return ForecastResult(
            tuple(forecasts), self.model_version, request.profile_version,
        )

    @staticmethod
    def _validate_point_matrix(
        values: Sequence[Sequence[float]], target_count: int, horizon: int,
    ) -> tuple[tuple[float, ...], ...]:
        try:
            if len(values) != target_count:
                raise ValueError("point output target dimension mismatch")
            if any(len(row) != horizon for row in values):
                raise ValueError("point output horizon dimension mismatch")
            if any(
                not _is_finite_real(value)
                for row in values
                for value in row
            ):
                raise ValueError("point output must contain finite int/float values")
            result = tuple(tuple(float(value) for value in row) for row in values)
        except (TypeError, OverflowError) as exc:
            raise ValueError("point output must be a targets-by-horizon matrix") from exc
        return result

    @staticmethod
    def _validate_quantile_tensor(
        values: Sequence[Sequence[Sequence[float]]] | None,
        target_count: int,
        horizon: int,
        *,
        required: bool,
    ) -> tuple[tuple[tuple[float, ...], ...], ...]:
        if values is None:
            if required:
                raise ValueError("quantile output is required")
            return ()
        try:
            if len(values) == 0:
                if required:
                    raise ValueError("quantile output is required")
                return ()
            if len(values) != target_count:
                raise ValueError("quantile output target dimension mismatch")
            if any(len(target) != horizon for target in values):
                raise ValueError("quantile output horizon dimension mismatch")
            if any(
                len(step) != len(OFFICIAL_QUANTILES)
                for target in values
                for step in target
            ):
                raise ValueError("quantile output must contain all nine quantiles")
            if any(
                not _is_finite_real(value)
                for target in values
                for step in target
                for value in step
            ):
                raise ValueError(
                    "quantile output must contain finite int/float values"
                )
            result = tuple(
                tuple(tuple(float(value) for value in step) for step in target)
                for target in values
            )
        except (TypeError, OverflowError) as exc:
            raise ValueError(
                "quantile output must be a targets-by-horizon-by-nine tensor"
            ) from exc
        if any(
            left > right
            for target in result
            for step in target
            for left, right in zip(step, step[1:])
        ):
            raise ValueError("quantile crossing detected")
        return result


def _is_finite_real(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and isfinite(value)
    )
