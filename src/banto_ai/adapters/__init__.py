"""Optional model adapters."""

from .timesfm3 import (
    AdapterUnavailableError,
    BackendForecast,
    OfficialTimesFM3Backend,
    TimesFM3Adapter,
    TimesFM3Config,
    validate_timesfm3_license_manifest,
)
from .chronos2 import (
    Chronos2Adapter,
    Chronos2Backend,
    Chronos2Config,
    Chronos2UnavailableError,
    OfficialChronos2Backend,
    validate_chronos2_license_manifest,
)
from .toto2 import (
    BackendForecast as Toto2BackendForecast,
    OfficialToto2Backend,
    Toto2Adapter,
    Toto2Backend,
    Toto2Config,
    Toto2UnavailableError,
    validate_toto2_license_manifest,
)

__all__ = [
    "AdapterUnavailableError",
    "BackendForecast",
    "OfficialTimesFM3Backend",
    "TimesFM3Adapter",
    "TimesFM3Config",
    "validate_timesfm3_license_manifest",
    "Chronos2Adapter",
    "Chronos2Backend",
    "Chronos2Config",
    "Chronos2UnavailableError",
    "OfficialChronos2Backend",
    "validate_chronos2_license_manifest",
    "Toto2BackendForecast",
    "OfficialToto2Backend",
    "Toto2Adapter",
    "Toto2Backend",
    "Toto2Config",
    "Toto2UnavailableError",
    "validate_toto2_license_manifest",
]
