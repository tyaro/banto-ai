"""Optional model adapters."""

from .timesfm3 import (
    AdapterUnavailableError,
    BackendForecast,
    OfficialTimesFM3Backend,
    TimesFM3Adapter,
    TimesFM3Config,
    validate_timesfm3_license_manifest,
)

__all__ = [
    "AdapterUnavailableError",
    "BackendForecast",
    "OfficialTimesFM3Backend",
    "TimesFM3Adapter",
    "TimesFM3Config",
    "validate_timesfm3_license_manifest",
]
