"""code licenseとweights licenseを分離して扱うpromotion gate。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


KNOWN_LICENSES = frozenset({
    "MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "MPL-2.0",
    "CC-BY-4.0", "CC-BY-NC-4.0", "timesfm-non-commercial-license-v1.0",
})
COMMERCIAL_LICENSES = frozenset({"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "MPL-2.0"})
ALLOWED_USES = frozenset({"research-only", "commercial-evaluation", "product-candidate"})


@dataclass(frozen=True, slots=True)
class LicenseDecision:
    allowed: bool
    reason: str


def evaluate_promotion(manifest: Mapping[str, object], target: str) -> LicenseDecision:
    """targetへの利用昇格を判定する。未知・空の値は必ず拒否する。"""
    code_license = manifest.get("code_license")
    weights_license = manifest.get("weights_license")
    allowed_use = manifest.get("allowed_use")
    if not all(isinstance(value, str) and value for value in (code_license, weights_license, allowed_use)):
        return LicenseDecision(False, "code_license, weights_license, and allowed_use are required")
    if code_license not in KNOWN_LICENSES or weights_license not in KNOWN_LICENSES:
        return LicenseDecision(False, "unknown license; fail closed")
    if allowed_use not in ALLOWED_USES:
        return LicenseDecision(False, "unknown allowed_use; fail closed")
    if target not in ALLOWED_USES:
        return LicenseDecision(False, "unknown promotion target; fail closed")
    if target == "research-only":
        return LicenseDecision(True, "research-only use is permitted")
    if allowed_use == "research-only":
        return LicenseDecision(False, "research-only artifact cannot be promoted")
    if target == "product-candidate" and allowed_use != "product-candidate":
        return LicenseDecision(False, "artifact is not marked product-candidate")
    if code_license not in COMMERCIAL_LICENSES or weights_license not in COMMERCIAL_LICENSES:
        return LicenseDecision(False, "license is not approved for product use")
    return LicenseDecision(True, "promotion permitted by manifest")
