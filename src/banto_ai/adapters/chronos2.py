"""外部依存を遅延ロードするChronos-2アダプター。

このモジュールのimport時にはnumpy、torch、chronosをimportしない。公式依存は
``Chronos2Adapter._load_official_backend``からだけロードし、通常の契約テストと
ライセンス検証を軽量なPython環境でも実行できるようにしている。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import isfinite
import re
import threading
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


OFFICIAL_QUANTILES = (
    0.01, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5,
    0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 0.99,
)
DEFAULT_REVISION = "29ec3766d36d6f73f0696f85560a422f50e8498c"
OFFICIAL_CHECKPOINT = "amazon/chronos-2"
OFFICIAL_SOURCE_URL = "https://huggingface.co/amazon/chronos-2"
OFFICIAL_PACKAGE_NAME = "chronos-forecasting"
OFFICIAL_PACKAGE_VERSION = "2.3.1"
OFFICIAL_PACKAGE_SHA256 = "d9d00ec9b1621235bfb26685638bf054885f4c000863678f1c775dfab2697496"
PROVENANCE_VERIFIED_AT = "2026-09-04"
MAX_CONTEXT_LENGTH = 8192
MAX_PREDICTION_LENGTH = 1024
_SHA = re.compile(r"^[0-9a-f]{40}$")

_REQUIRED_LICENSE_FIELDS = {
    "schema_version": "0.1",
    "manifest_type": "model-license",
    "model_id": "chronos-2",
    "code_license": "Apache-2.0",
    "weights_license": "Apache-2.0",
    "allowed_use": "commercial-evaluation",
    "source_url": OFFICIAL_SOURCE_URL,
    "package_name": OFFICIAL_PACKAGE_NAME,
    "package_version": OFFICIAL_PACKAGE_VERSION,
    "package_sha256": OFFICIAL_PACKAGE_SHA256,
    "checkpoint": OFFICIAL_CHECKPOINT,
    "checkpoint_revision": DEFAULT_REVISION,
    "verified_at": PROVENANCE_VERIFIED_AT,
}
_LICENSE_FIELDS = frozenset((*_REQUIRED_LICENSE_FIELDS, "notes"))


class Chronos2UnavailableError(RuntimeError):
    """公式Chronos-2 backendをこの環境で利用できない場合のエラー。"""


def validate_chronos2_license_manifest(
    manifest: Mapping[str, object],
    requested_use: str,
    *,
    package_version: str = OFFICIAL_PACKAGE_VERSION,
    checkpoint_path: str = OFFICIAL_CHECKPOINT,
    checkpoint_revision: str = DEFAULT_REVISION,
) -> None:
    """公式成果物の固定情報と商用評価用途をfail-closedで検証する。"""
    if not isinstance(manifest, Mapping):
        raise ValueError("model-license manifest must be a mapping")
    if requested_use != "commercial-evaluation":
        raise ValueError("Chronos-2 may only be requested for commercial-evaluation")
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
class Chronos2Config:
    """固定済みChronos-2成果物と推論時の安全な既定値。"""

    package_version: str = OFFICIAL_PACKAGE_VERSION
    checkpoint_path: str = OFFICIAL_CHECKPOINT
    checkpoint_revision: str = DEFAULT_REVISION
    cache_dir: str | None = None
    local_files_only: bool = True
    device_map: str | Mapping[str, object] | None = "cpu"
    batch_size: int = 1
    context_length: int = 2048
    cross_learning: bool = False
    requested_use: str = "commercial-evaluation"

    def __post_init__(self) -> None:
        if self.package_version != OFFICIAL_PACKAGE_VERSION:
            raise ValueError("package_version must be exactly 2.3.1")
        if self.checkpoint_path != OFFICIAL_CHECKPOINT:
            raise ValueError("checkpoint_path must identify amazon/chronos-2")
        if not isinstance(self.checkpoint_revision, str) or not _SHA.fullmatch(self.checkpoint_revision):
            raise ValueError("checkpoint_revision must be a lowercase 40-character SHA")
        if self.checkpoint_revision != DEFAULT_REVISION:
            raise ValueError("checkpoint_revision must be the pinned Chronos-2 revision")
        if self.cache_dir is not None and (not isinstance(self.cache_dir, str) or not self.cache_dir):
            raise ValueError("cache_dir must be None or a non-empty string")
        if not isinstance(self.local_files_only, bool):
            raise ValueError("local_files_only must be boolean")
        _validate_device_map(self.device_map)
        _validate_positive_int(self.batch_size, "batch_size")
        _validate_positive_int(self.context_length, "context_length")
        if not 2 <= self.context_length <= MAX_CONTEXT_LENGTH:
            raise ValueError("context_length must be between 2 and 8192")
        if not isinstance(self.cross_learning, bool):
            raise ValueError("cross_learning must be boolean")
        if self.requested_use != "commercial-evaluation":
            raise ValueError("requested_use must be commercial-evaluation")


@dataclass(frozen=True, slots=True)
class BackendForecast:
    """Banto向けに正規化するtargets x horizonの予測。"""

    point_forecast: Sequence[Sequence[float]]
    quantile_forecast: Sequence[Sequence[Sequence[float]]] | None = None
    quantile_levels: Sequence[float] | None = None


class Chronos2Backend(Protocol):
    """公式実装とfake実装の間の外部依存なし境界。"""

    def forecast(
        self,
        targets: Sequence[Sequence[float]],
        past_covariates: Mapping[str, Sequence[float]],
        future_covariates: Mapping[str, Sequence[float]],
        horizon: int,
        quantiles: Sequence[float],
        *,
        batch_size: int,
        context_length: int,
        cross_learning: bool,
    ) -> BackendForecast: ...


class OfficialChronos2Backend:
    """Chronos2PipelineのAPI形状をBanto境界へ変換する薄いwrapper。"""

    def __init__(self, pipeline: Any, numpy_module: Any) -> None:
        self._pipeline = pipeline
        self._numpy = numpy_module

    def forecast(
        self,
        targets: Sequence[Sequence[float]],
        past_covariates: Mapping[str, Sequence[float]],
        future_covariates: Mapping[str, Sequence[float]],
        horizon: int,
        quantiles: Sequence[float],
        *,
        batch_size: int,
        context_length: int,
        cross_learning: bool,
    ) -> BackendForecast:
        payload: dict[str, Any] = {"target": self._array(targets)}
        if past_covariates:
            payload["past_covariates"] = {
                key: self._vector(values) for key, values in past_covariates.items()
            }
        if future_covariates:
            payload["future_covariates"] = {
                key: self._vector(values) for key, values in future_covariates.items()
            }
        inputs = [payload]
        kwargs = {
            "prediction_length": horizon,
            "batch_size": batch_size,
            "context_length": context_length,
            "cross_learning": cross_learning,
            "limit_prediction_length": True,
        }
        if quantiles:
            try:
                result = self._pipeline.predict_quantiles(
                    inputs=inputs,
                    quantile_levels=list(quantiles),
                    **kwargs,
                )
                quantile_outputs, point_outputs = result
                quantile_outputs = self._one_output(quantile_outputs, "quantile")
                point_outputs = self._one_output(point_outputs, "point")
            except (TypeError, ValueError) as exc:
                raise ValueError("Chronos-2 predict_quantiles returned an invalid result") from exc
            return BackendForecast(
                self._tolist(point_outputs),
                self._tolist(quantile_outputs),
                tuple(float(quantile) for quantile in quantiles),
            )

        try:
            outputs = self._pipeline.predict(inputs=inputs, **kwargs)
            raw = self._one_output(outputs, "prediction")
            values = self._tolist(raw)
            point = self._point_from_predict(values, len(targets), horizon)
        except (TypeError, ValueError, AttributeError, IndexError) as exc:
            raise ValueError("Chronos-2 predict returned an invalid result") from exc
        return BackendForecast(point)

    def _array(self, values: Sequence[Sequence[float]]) -> Any:
        try:
            matrix = tuple(tuple(value for value in row) for row in values)
        except TypeError as exc:
            raise ValueError("Chronos-2 target must be a nested sequence") from exc
        return self._numpy.asarray(matrix, dtype=self._numpy.float32)

    def _vector(self, values: Sequence[float]) -> Any:
        try:
            vector = tuple(value for value in values)
        except TypeError as exc:
            raise ValueError("Chronos-2 covariate must be a sequence") from exc
        return self._numpy.asarray(vector, dtype=self._numpy.float32)

    @staticmethod
    def _one_output(outputs: Any, label: str) -> Any:
        if not isinstance(outputs, (list, tuple)) or len(outputs) != 1:
            raise ValueError(f"Chronos-2 {label} output must contain exactly one item")
        return outputs[0]

    @staticmethod
    def _tolist(values: Any) -> Any:
        try:
            return values.tolist()
        except AttributeError:
            return values

    def _point_from_predict(
        self, values: Any, target_count: int, horizon: int,
    ) -> list[list[float]]:
        """predictのtargets x quantiles x horizonからp50だけを取り出す。"""
        if target_count <= 0 or not isinstance(values, (list, tuple)) or len(values) != target_count:
            raise ValueError("prediction target dimension mismatch")
        try:
            quantiles = tuple(float(value) for value in self._pipeline.quantiles)
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError("Chronos-2 pipeline must expose training quantiles") from exc
        if quantiles != OFFICIAL_QUANTILES:
            raise ValueError("Chronos-2 pipeline training quantiles do not match the pinned contract")
        if any(
            not isinstance(target, (list, tuple))
            or len(target) != len(quantiles)
            or any(
                not isinstance(quantile, (list, tuple)) or len(quantile) != horizon
                for quantile in target
            )
            for target in values
        ):
            raise ValueError(
                "prediction must be a targets-by-training-quantiles-by-horizon tensor"
            )
        p50_index = quantiles.index(0.5)
        return [list(target[p50_index]) for target in values]


@dataclass(frozen=True, slots=True)
class _PreparedInput:
    targets: tuple[tuple[float, ...], ...]
    past_covariates: Mapping[str, tuple[float, ...]]
    future_covariates: Mapping[str, tuple[float, ...]]
    last_timestamp: datetime
    interval_ms: int


class Chronos2Adapter(Forecaster):
    """固定済みChronos-2をBantoのForecaster契約へ適応する。"""

    def __init__(
        self,
        license_manifest: Mapping[str, object],
        config: Chronos2Config | None = None,
        backend: Chronos2Backend | None = None,
    ) -> None:
        self.config = config or Chronos2Config()
        validate_chronos2_license_manifest(
            license_manifest,
            self.config.requested_use,
            package_version=self.config.package_version,
            checkpoint_path=self.config.checkpoint_path,
            checkpoint_revision=self.config.checkpoint_revision,
        )
        self.license_manifest = MappingProxyType(dict(license_manifest))
        self._backend = backend
        self._backend_lock = threading.Lock()

    @property
    def model_version(self) -> str:
        return f"chronos2-{self.config.package_version}@{self.config.checkpoint_revision}"

    def forecast(self, request: ForecastRequest) -> ForecastResult:
        quantiles = self._validate_request(request)
        prepared = self._prepare(request)
        backend = self._get_backend()
        try:
            output = backend.forecast(
                prepared.targets,
                prepared.past_covariates,
                prepared.future_covariates,
                request.horizon,
                quantiles,
                batch_size=self.config.batch_size,
                context_length=self.config.context_length,
                cross_learning=self.config.cross_learning,
            )
        except Chronos2UnavailableError:
            raise
        except (ImportError, ModuleNotFoundError) as exc:
            raise Chronos2UnavailableError("Chronos-2 dependencies are unavailable") from exc
        return self._build_result(request, output, quantiles, prepared)

    def _get_backend(self) -> Chronos2Backend:
        backend = self._backend
        if backend is not None:
            return backend
        with self._backend_lock:
            backend = self._backend
            if backend is None:
                backend = self._load_official_backend()
                self._backend = backend
        return backend

    @staticmethod
    def _validate_request(request: ForecastRequest) -> tuple[float, ...]:
        if request.horizon > MAX_PREDICTION_LENGTH:
            raise ValueError("horizon must be at most 1024")
        if request.quantiles and 0.5 not in request.quantiles:
            raise ValueError("requested quantiles must contain 0.5")
        if any(quantile not in OFFICIAL_QUANTILES for quantile in request.quantiles):
            raise ValueError("requested quantiles must be a supported Chronos-2 subset")
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
            Chronos2Adapter._validate_points(series, "context")
        for series in request.known_future_covariates:
            if series.metadata.role == "target":
                raise ValueError("known-future covariate cannot have target role")
            Chronos2Adapter._validate_points(series, "known-future covariate")
        return tuple(request.quantiles)

    @staticmethod
    def _validate_points(series: TimeSeries, label: str) -> None:
        if any(
            point.quality_status != QualityStatus.OK
            or point.value is None
            or not _is_finite_real(point.value)
            for point in series.points
        ):
            raise ValueError(f"all {label} values must be finite int/float values with OK quality")
        interval = timedelta(milliseconds=series.metadata.sampling_interval_ms)
        if any(current.timestamp - previous.timestamp != interval for previous, current in zip(series.points, series.points[1:])):
            raise ValueError(f"all {label} timestamps must match sampling_interval_ms")

    def _prepare(self, request: ForecastRequest) -> _PreparedInput:
        contexts = {series.metadata.signal_id: series for series in request.contexts}
        reference = contexts[request.target_signal_ids[0]]
        context_timestamps = tuple(point.timestamp for point in reference.points)
        context_length = len(context_timestamps)
        if context_length < 2:
            raise ValueError("request context length must be at least 2")
        if context_length > self.config.context_length:
            raise ValueError("request context length exceeds configured context_length")
        interval_ms = reference.metadata.sampling_interval_ms
        for series in request.contexts:
            if len(series.points) != context_length:
                raise ValueError("all context series must have equal lengths")
            if series.metadata.sampling_interval_ms != interval_ms:
                raise ValueError("all context series must have equal sampling intervals")
            if tuple(point.timestamp for point in series.points) != context_timestamps:
                raise ValueError("all context series must have equal timestamps")

        future_by_id = {series.metadata.signal_id: series for series in request.known_future_covariates}
        expected_future_timestamps = tuple(
            context_timestamps[-1] + timedelta(milliseconds=interval_ms * step)
            for step in range(1, request.horizon + 1)
        )
        past: dict[str, tuple[float, ...]] = {}
        future: dict[str, tuple[float, ...]] = {}
        target_ids = set(request.target_signal_ids)
        for series in request.contexts:
            signal_id = series.metadata.signal_id
            if signal_id in target_ids:
                continue
            context_values = tuple(float(point.value) for point in series.points)
            combined = future_by_id.get(signal_id)
            if combined is None:
                past[signal_id] = context_values
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
            past[signal_id] = context_values
            future[signal_id] = tuple(float(point.value) for point in suffix)

        targets = tuple(
            tuple(float(point.value) for point in contexts[signal_id].points)
            for signal_id in request.target_signal_ids
        )
        return _PreparedInput(
            targets,
            MappingProxyType(past),
            MappingProxyType(future),
            context_timestamps[-1],
            interval_ms,
        )

    def _load_official_backend(self) -> Chronos2Backend:
        try:
            import numpy
            from chronos import Chronos2Pipeline

            pipeline = Chronos2Pipeline.from_pretrained(
                self.config.checkpoint_path,
                revision=self.config.checkpoint_revision,
                cache_dir=self.config.cache_dir,
                local_files_only=self.config.local_files_only,
                device_map=self.config.device_map,
            )
        except (ImportError, ModuleNotFoundError) as exc:
            raise Chronos2UnavailableError(
                "install chronos-forecasting==2.3.1 and its optional dependencies to use this adapter"
            ) from exc
        except OSError as exc:
            raise Chronos2UnavailableError(
                "the pinned Chronos-2 checkpoint is unavailable in the configured cache"
            ) from exc
        return OfficialChronos2Backend(pipeline, numpy)

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
        points = self._validate_point_matrix(output.point_forecast, len(request.target_signal_ids), request.horizon)
        full_quantiles = self._validate_quantile_tensor(
            output.quantile_forecast,
            output.quantile_levels,
            len(request.target_signal_ids),
            request.horizon,
            requested_quantiles,
            points,
        )
        timestamps = tuple(
            prepared.last_timestamp + timedelta(milliseconds=prepared.interval_ms * step)
            for step in range(1, request.horizon + 1)
        )
        forecasts = []
        for target_index, signal_id in enumerate(request.target_signal_ids):
            quantile_forecasts = tuple(
                QuantileForecast(
                    quantile,
                    tuple(full_quantiles[target_index][step][quantile_index] for step in range(request.horizon)),
                )
                for quantile, quantile_index in zip(
                    requested_quantiles,
                    range(len(requested_quantiles)),
                )
            )
            forecasts.append(ForecastSeriesResult(
                signal_id=signal_id,
                timestamps=timestamps,
                point_forecast=points[target_index],
                quantile_forecasts=quantile_forecasts,
            ))
        return ForecastResult(tuple(forecasts), self.model_version, request.profile_version)

    @staticmethod
    def _validate_point_matrix(
        values: Sequence[Sequence[float]], target_count: int, horizon: int,
    ) -> tuple[tuple[float, ...], ...]:
        try:
            if len(values) != target_count:
                raise ValueError("point output target dimension mismatch")
            if any(len(row) != horizon for row in values):
                raise ValueError("point output horizon dimension mismatch")
            if any(not _is_finite_real(value) for row in values for value in row):
                raise ValueError("point output must contain finite int/float values")
            return tuple(tuple(float(value) for value in row) for row in values)
        except (TypeError, OverflowError) as exc:
            raise ValueError("point output must be a targets-by-horizon matrix") from exc

    @staticmethod
    def _validate_quantile_tensor(
        values: Sequence[Sequence[Sequence[float]]] | None,
        levels: Sequence[float] | None,
        target_count: int,
        horizon: int,
        requested: tuple[float, ...],
        points: tuple[tuple[float, ...], ...],
    ) -> tuple[tuple[tuple[float, ...], ...], ...]:
        if not requested:
            if values is not None:
                try:
                    has_quantiles = len(values) != 0
                except (TypeError, ValueError) as exc:
                    raise ValueError("point-only request must not return quantile output") from exc
                if has_quantiles:
                    raise ValueError("point-only request must not return quantile output")
            return ()
        if values is None:
            raise ValueError("quantile output is required")
        if levels is None:
            raise ValueError("quantile output levels are required")
        try:
            actual_levels = tuple(levels)
        except TypeError as exc:
            raise ValueError("quantile output levels must be a sequence") from exc
        if actual_levels != requested:
            raise ValueError("quantile output levels do not match the request")
        try:
            if len(values) != target_count:
                raise ValueError("quantile output target dimension mismatch")
            if any(len(target) != horizon for target in values):
                raise ValueError("quantile output horizon dimension mismatch")
            if any(len(step) != len(requested) for target in values for step in target):
                raise ValueError("quantile output quantile dimension mismatch")
            if any(not _is_finite_real(value) for target in values for step in target for value in step):
                raise ValueError("quantile output must contain finite int/float values")
            result = tuple(
                tuple(tuple(float(value) for value in step) for step in target)
                for target in values
            )
        except (TypeError, OverflowError) as exc:
            raise ValueError("quantile output must be a targets-by-horizon-by-quantiles tensor") from exc
        if any(left > right for target in result for step in target for left, right in zip(step, step[1:])):
            raise ValueError("quantile crossing detected")
        p50_index = requested.index(0.5)
        # The official API calls this return value mean, but it is the p50/median.
        if any(
            not _close(points[target_index][step], result[target_index][step][p50_index])
            for target_index in range(target_count)
            for step in range(horizon)
        ):
            raise ValueError("point output must match the requested p50 quantile")
        return result


def _validate_positive_int(value: object, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")


def _validate_device_map(value: object) -> None:
    if value is None:
        return
    if isinstance(value, str):
        if not value:
            raise ValueError("device_map must be None or a non-empty string/mapping")
        return
    if not isinstance(value, Mapping) or not value:
        raise ValueError("device_map must be None or a non-empty string/mapping")
    if any(not isinstance(key, str) or not key for key in value):
        raise ValueError("device_map mapping keys must be non-empty strings")
    if any(
        not (
            isinstance(mapped, str) and mapped
        ) and not (
            isinstance(mapped, int) and not isinstance(mapped, bool) and mapped >= 0
        )
        for mapped in value.values()
    ):
        raise ValueError("device_map mapping values must be non-empty strings or non-negative integers")


def _is_finite_real(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and isfinite(value)


def _close(left: float, right: float) -> bool:
    return isfinite(left) and isfinite(right) and abs(left - right) <= 1e-5 + 1e-5 * max(abs(left), abs(right))
