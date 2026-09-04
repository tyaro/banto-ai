"""Dependency-free adapter for the pinned Toto 2.0 4M checkpoint.

The optional ``torch`` and ``toto2`` imports are deliberately confined to the
official backend loader.  The adapter validates Banto's observations before
turning all context series into Toto's multivariate ``batch x variates x time``
input.  Toto predicts every variate; only the declared target variates are
returned to Banto.
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


OFFICIAL_QUANTILES = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
DEFAULT_REVISION = "8306a9801cf98c0f5ffe4b2dcc8f496e616d84d9"
OFFICIAL_CHECKPOINT = "Datadog/Toto-2.0-4m"
OFFICIAL_SOURCE_URL = "https://huggingface.co/Datadog/Toto-2.0-4m"
OFFICIAL_PACKAGE_NAME = "toto-2"
OFFICIAL_PACKAGE_VERSION = "2.0.0"
OFFICIAL_PACKAGE_SHA256 = "5eb922f8162a800d6d31cffb10e3f4c079276b12c41e272129e5b4a930943f71"
UMBRELLA_PACKAGE_NAME = "toto-models"
UMBRELLA_PACKAGE_VERSION = "1.0.0"
UMBRELLA_PACKAGE_SHA256 = "7c77cb79f18e195909a3926a0279f4e28b21b653ce8e65ee384f9f28125208d4"
PACKAGE_PROVENANCE_COMMIT = "44ea4e88852228039564aa3e76fac26aafac0803"
PATCH_SIZE = 32
METROPT3_CONTEXT_LENGTH = 120
EFFECTIVE_CONTEXT_LENGTH = 128
# Toto's public API describes variable context/horizon lengths.  This adapter
# imposes only the safe patch alignment boundary; it does not invent a model
# maximum that is absent from the pinned public config.
MODEL_SAFETENSORS_SIZE_BYTES = 16_582_848
MODEL_SAFETENSORS_SHA256 = "316660d5afb47943e531f39242e0b02ca0b8bb73be5709dfe07ca80dfce9805e"
CHECKPOINT_ALLOW_PATTERNS = (
    "README.md",
    "config.json",
    "model.safetensors",
)
PROVENANCE_VERIFIED_AT = "2026-09-04"
_SHA = re.compile(r"^[0-9a-f]{40}$")
_REQUIRED_LICENSE_FIELDS = {
    "schema_version": "0.1",
    "manifest_type": "model-license",
    "model_id": "toto-2-4m",
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


class Toto2UnavailableError(RuntimeError):
    """The optional official Toto 2.0 backend is unavailable."""


def validate_toto2_license_manifest(
    manifest: Mapping[str, object],
    requested_use: str,
    *,
    package_version: str = OFFICIAL_PACKAGE_VERSION,
    checkpoint_path: str = OFFICIAL_CHECKPOINT,
    checkpoint_revision: str = DEFAULT_REVISION,
) -> None:
    if not isinstance(manifest, Mapping):
        raise ValueError("model-license manifest must be a mapping")
    if requested_use != "commercial-evaluation":
        raise ValueError("Toto 2.0 may only be requested for commercial-evaluation")
    unknown = set(manifest) - _LICENSE_FIELDS
    if unknown:
        raise ValueError(f"model-license manifest has unknown fields: {sorted(unknown)}")
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
class Toto2Config:
    package_version: str = OFFICIAL_PACKAGE_VERSION
    checkpoint_path: str = OFFICIAL_CHECKPOINT
    checkpoint_revision: str = DEFAULT_REVISION
    cache_dir: str | None = None
    local_files_only: bool = True
    device: str = "cpu"
    batch_size: int = 1
    patch_size: int = PATCH_SIZE
    requested_use: str = "commercial-evaluation"

    def __post_init__(self) -> None:
        if self.package_version != OFFICIAL_PACKAGE_VERSION:
            raise ValueError("package_version must be exactly 2.0.0")
        if self.checkpoint_path != OFFICIAL_CHECKPOINT:
            raise ValueError("checkpoint_path must identify Datadog/Toto-2.0-4m")
        if not isinstance(self.checkpoint_revision, str) or not _SHA.fullmatch(self.checkpoint_revision):
            raise ValueError("checkpoint_revision must be a lowercase 40-character SHA")
        if self.checkpoint_revision != DEFAULT_REVISION:
            raise ValueError("checkpoint_revision must be the pinned Toto 2.0 4M revision")
        if self.cache_dir is not None and (not isinstance(self.cache_dir, str) or not self.cache_dir):
            raise ValueError("cache_dir must be None or a non-empty string")
        if self.local_files_only is not True:
            raise ValueError("local_files_only must be true")
        if self.device != "cpu":
            raise ValueError("Toto 2.0 benchmark is CPU-only")
        if isinstance(self.batch_size, bool) or not isinstance(self.batch_size, int) or self.batch_size != 1:
            raise ValueError("batch_size must be exactly 1")
        if self.patch_size != PATCH_SIZE:
            raise ValueError("patch_size must be exactly 32 for Toto 2.0 4M")
        if self.requested_use != "commercial-evaluation":
            raise ValueError("requested_use must be commercial-evaluation")


@dataclass(frozen=True, slots=True)
class BackendForecast:
    """All-variate point and quantile outputs in Toto's quantile-first layout."""

    point_forecast: Sequence[Sequence[float]]
    quantile_forecast: Sequence[Sequence[Sequence[float]]] | None = None
    quantile_levels: Sequence[float] | None = None


class Toto2Backend(Protocol):
    def forecast(
        self,
        variates: Sequence[Sequence[float]],
        observed_mask: Sequence[Sequence[bool]],
        horizon: int,
        *,
        decode_block_size: int | None,
        has_missing_values: bool,
    ) -> BackendForecast: ...


class OfficialToto2Backend:
    """Thin wrapper around Toto2Model.forecast with explicit CPU tensors."""

    def __init__(self, model: Any, torch_module: Any) -> None:
        self._model = model
        self._torch = torch_module

    def forecast(
        self,
        variates: Sequence[Sequence[float]],
        observed_mask: Sequence[Sequence[bool]],
        horizon: int,
        *,
        decode_block_size: int | None,
        has_missing_values: bool,
    ) -> BackendForecast:
        torch = self._torch
        target = torch.tensor([variates], dtype=torch.float32, device="cpu")
        mask = torch.tensor([observed_mask], dtype=torch.bool, device="cpu")
        series_ids = torch.zeros((1, len(variates)), dtype=torch.long, device="cpu")
        with torch.no_grad():
            raw = self._model.forecast(
                {"target": target, "target_mask": mask, "series_ids": series_ids},
                horizon=horizon,
                decode_block_size=decode_block_size,
                has_missing_values=has_missing_values,
            )
        try:
            values = raw.detach().cpu().tolist()
        except AttributeError as exc:
            raise ValueError("Toto 2.0 forecast must return a tensor") from exc
        if not isinstance(values, list) or len(values) != len(OFFICIAL_QUANTILES):
            raise ValueError("Toto 2.0 forecast must return a quantile-first tensor with nine levels")
        quantiles = []
        for quantile_values in values:
            if not isinstance(quantile_values, list) or len(quantile_values) != 1:
                raise ValueError("Toto 2.0 forecast must have batch dimension 1")
            batch_values = quantile_values[0]
            if not isinstance(batch_values, list) or len(batch_values) != len(variates):
                raise ValueError("Toto 2.0 forecast variate dimension mismatch")
            try:
                quantiles.append([list(map(float, row)) for row in batch_values])
            except (TypeError, ValueError) as exc:
                raise ValueError("Toto 2.0 forecast contains an invalid value tensor") from exc
        p50 = quantiles[OFFICIAL_QUANTILES.index(0.5)]
        return BackendForecast(p50, quantiles, OFFICIAL_QUANTILES)


@dataclass(frozen=True, slots=True)
class _PreparedInput:
    variates: tuple[tuple[float, ...], ...]
    observed_mask: tuple[tuple[bool, ...], ...]
    target_count: int
    last_timestamp: datetime
    interval_ms: int
    padding_left: int


class Toto2Adapter(Forecaster):
    """Adapt Banto requests to Toto 2.0's multivariate forecast contract."""

    def __init__(self, license_manifest: Mapping[str, object], config: Toto2Config | None = None, backend: Toto2Backend | None = None) -> None:
        self.config = config or Toto2Config()
        validate_toto2_license_manifest(
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
        return f"toto2-4m-{self.config.package_version}@{self.config.checkpoint_revision}"

    def forecast(self, request: ForecastRequest) -> ForecastResult:
        quantiles = self._validate_request(request)
        prepared = self._prepare(request)
        backend = self._get_backend()
        try:
            output = backend.forecast(
                prepared.variates,
                prepared.observed_mask,
                request.horizon,
                decode_block_size=None,
                has_missing_values=bool(prepared.padding_left),
            )
        except Toto2UnavailableError:
            raise
        except (ImportError, ModuleNotFoundError) as exc:
            raise Toto2UnavailableError("Toto 2.0 dependencies are unavailable") from exc
        return self._build_result(request, output, quantiles, prepared)

    def _get_backend(self) -> Toto2Backend:
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
        if request.quantiles and 0.5 not in request.quantiles:
            raise ValueError("requested quantiles must contain 0.5")
        if any(q not in OFFICIAL_QUANTILES for q in request.quantiles):
            raise ValueError("requested quantiles must be a supported Toto 2.0 subset")
        if request.known_future_covariates:
            raise ValueError("Toto 2.0 does not support known-future covariates")
        contexts = {series.metadata.signal_id: series for series in request.contexts}
        for signal_id in request.target_signal_ids:
            if contexts[signal_id].metadata.role != "target":
                raise ValueError("target signal context must have target role")
        for series in request.contexts:
            if series.metadata.signal_id not in request.target_signal_ids and series.metadata.role == "target":
                raise ValueError("non-target context cannot have target role")
            Toto2Adapter._validate_points(series, "context")
        return tuple(request.quantiles)

    @staticmethod
    def _validate_points(series: TimeSeries, label: str) -> None:
        if any(point.quality_status != QualityStatus.OK or point.value is None or not _is_finite_real(point.value) for point in series.points):
            raise ValueError(f"all {label} values must be finite int/float values with OK quality")
        interval = timedelta(milliseconds=series.metadata.sampling_interval_ms)
        if any(current.timestamp - previous.timestamp != interval for previous, current in zip(series.points, series.points[1:])):
            raise ValueError(f"all {label} timestamps must match sampling_interval_ms")

    def _prepare(self, request: ForecastRequest) -> _PreparedInput:
        contexts = {series.metadata.signal_id: series for series in request.contexts}
        reference = contexts[request.target_signal_ids[0]]
        timestamps = tuple(point.timestamp for point in reference.points)
        context_length = len(timestamps)
        if context_length < 2:
            raise ValueError("request context length must be at least 2")
        if context_length < self.config.patch_size:
            raise ValueError("request context length must be at least patch_size=32")
        interval_ms = reference.metadata.sampling_interval_ms
        for series in request.contexts:
            if len(series.points) != context_length:
                raise ValueError("all context series must have equal lengths")
            if series.metadata.sampling_interval_ms != interval_ms:
                raise ValueError("all context series must have equal sampling intervals")
            if tuple(point.timestamp for point in series.points) != timestamps:
                raise ValueError("all context series must have equal timestamps")
        padding_left = (-context_length) % self.config.patch_size
        padded_length = context_length + padding_left
        if padded_length % self.config.patch_size:
            raise ValueError("effective Toto 2.0 input length must be divisible by patch_size")
        ordered_ids = (*request.target_signal_ids, *(series.metadata.signal_id for series in request.contexts if series.metadata.signal_id not in request.target_signal_ids))
        variates = []
        masks = []
        for signal_id in ordered_ids:
            values = tuple(float(point.value) for point in contexts[signal_id].points)
            variates.append((0.0,) * padding_left + values)
            masks.append((False,) * padding_left + (True,) * context_length)
        return _PreparedInput(tuple(variates), tuple(masks), len(request.target_signal_ids), timestamps[-1], interval_ms, padding_left)

    def _load_official_backend(self) -> Toto2Backend:
        try:
            import torch
            from toto2 import Toto2Model
            model = Toto2Model.from_pretrained(
                self.config.checkpoint_path,
                revision=self.config.checkpoint_revision,
                cache_dir=self.config.cache_dir,
                local_files_only=self.config.local_files_only,
                map_location="cpu",
            ).to(torch.device("cpu")).eval()
        except (ImportError, ModuleNotFoundError) as exc:
            raise Toto2UnavailableError("install toto-2==2.0.0 and its isolated dependencies to use this adapter") from exc
        except OSError as exc:
            raise Toto2UnavailableError("the pinned Toto 2.0 4M checkpoint is unavailable in the configured cache") from exc
        return OfficialToto2Backend(model, torch)

    def _build_result(self, request: ForecastRequest, output: BackendForecast, requested_quantiles: tuple[float, ...], prepared: _PreparedInput) -> ForecastResult:
        if not hasattr(output, "point_forecast"):
            raise ValueError("backend output is missing point_forecast")
        points = self._validate_matrix(output.point_forecast, len(prepared.variates), request.horizon, "point")
        quantile_values = self._validate_quantiles(output.quantile_forecast, output.quantile_levels, len(prepared.variates), request.horizon, points, requested_quantiles)
        timestamps = tuple(prepared.last_timestamp + timedelta(milliseconds=prepared.interval_ms * step) for step in range(1, request.horizon + 1))
        forecasts = []
        for target_index, signal_id in enumerate(request.target_signal_ids):
            selected = tuple(
                QuantileForecast(q, tuple(quantile_values[OFFICIAL_QUANTILES.index(q)][target_index]))
                for q in requested_quantiles
            )
            forecasts.append(ForecastSeriesResult(signal_id, timestamps, points[target_index], selected))
        return ForecastResult(tuple(forecasts), self.model_version, request.profile_version)

    @staticmethod
    def _validate_matrix(values: Sequence[Sequence[float]], variate_count: int, horizon: int, label: str) -> tuple[tuple[float, ...], ...]:
        try:
            if len(values) != variate_count or any(len(row) != horizon for row in values):
                raise ValueError(f"{label} output shape mismatch")
            if any(not _is_finite_real(v) for row in values for v in row):
                raise ValueError(f"{label} output must contain finite int/float values")
            return tuple(tuple(float(v) for v in row) for row in values)
        except (TypeError, OverflowError) as exc:
            raise ValueError(f"{label} output must be a variates-by-horizon matrix") from exc

    @staticmethod
    def _validate_quantiles(values: Sequence[Sequence[Sequence[float]]] | None, levels: Sequence[float] | None, variate_count: int, horizon: int, points: tuple[tuple[float, ...], ...], requested: tuple[float, ...]) -> tuple[tuple[tuple[float, ...], ...], ...]:
        if values is None or levels is None:
            raise ValueError("quantile output and levels are required")
        try:
            if tuple(float(level) for level in levels) != OFFICIAL_QUANTILES:
                raise ValueError("quantile output levels do not match Toto 2.0")
            if len(values) != len(OFFICIAL_QUANTILES) or any(len(q) != variate_count for q in values) or any(len(row) != horizon for q in values for row in q):
                raise ValueError("quantile output shape mismatch")
            result = tuple(tuple(tuple(float(v) for v in row) for row in q) for q in values)
        except (TypeError, OverflowError) as exc:
            raise ValueError("quantile output must be quantiles-by-variates-by-horizon") from exc
        if any(not _is_finite_real(v) for q in result for row in q for v in row):
            raise ValueError("quantile output must contain finite int/float values")
        if any(result[q][variate][step] > result[q + 1][variate][step] for q in range(len(result) - 1) for variate in range(variate_count) for step in range(horizon)):
            raise ValueError("quantile crossing detected")
        p50_index = OFFICIAL_QUANTILES.index(0.5)
        if any(abs(points[variate][step] - result[p50_index][variate][step]) > 1e-5 + 1e-5 * max(abs(points[variate][step]), abs(result[p50_index][variate][step])) for variate in range(variate_count) for step in range(horizon)):
            raise ValueError("point output must match the Toto 2.0 p50 quantile")
        return result


def _is_finite_real(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and isfinite(value)


__all__ = [
    "BackendForecast", "CHECKPOINT_ALLOW_PATTERNS", "DEFAULT_REVISION",
    "EFFECTIVE_CONTEXT_LENGTH", "MODEL_SAFETENSORS_SHA256", "MODEL_SAFETENSORS_SIZE_BYTES",
    "OFFICIAL_CHECKPOINT", "OFFICIAL_PACKAGE_NAME", "OFFICIAL_PACKAGE_SHA256",
    "OFFICIAL_PACKAGE_VERSION", "OFFICIAL_QUANTILES", "OFFICIAL_SOURCE_URL", "PATCH_SIZE",
    "OfficialToto2Backend", "Toto2Adapter", "Toto2Backend", "Toto2Config",
    "Toto2UnavailableError", "validate_toto2_license_manifest",
]
