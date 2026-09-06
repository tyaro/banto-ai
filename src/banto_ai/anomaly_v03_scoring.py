"""S2 saved-observation projection, causal phase state and three fixed scorers.

No files, environment, random generator, event input or campaign execution.
Callers authenticate the expected hash against trusted provenance; matching a
caller-supplied hash alone does not prove where bytes came from. No raw latent
array API exists. Profile/score outputs are not formal acceptance evidence.
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, replace
from datetime import datetime, timezone

from . import _anomaly_v03_contract as c
from . import _anomaly_v03_numeric as n
from . import anomaly_v03 as v

__all__ = ["Observation", "PhaseState", "ProfileSet", "quantize_observation",
           "decode_saved_observations", "advance_phase", "exclusion_tags",
           "fit_profiles", "score_test"]


def quantize_observation(value):
    """One final post-overlay rounding only; null and signed zero survive.

    This scalar helper does not apply overlays or advance latent temperature.
    S3 must retain the unrounded normal latent state before calling it.
    """
    if value is None:
        return None
    v.require(type(value) in (int, float), "numeric observation cannot be bool")
    try:
        value = float(value)
    except OverflowError as exc:
        raise v.V03ValidationError("nonfinite observation") from exc
    v.require(math.isfinite(value), "nonfinite observation")
    return round(value, 6)


@dataclass(frozen=True, slots=True)
class Observation:
    """Detector allowlist: one equipment, four targets, no GT/seed/load_proxy."""

    equipment: str
    timestamp_ms: int
    mode: str
    recipe: str
    values: tuple
    quality: tuple

    def __post_init__(self):
        v.require(type(self.equipment) is str and self.equipment in c.EQUIPMENT, "unknown equipment")
        v.require(type(self.timestamp_ms) is int and self.timestamp_ms >= 0, "timestamp must be an exact integer")
        v.require(type(self.mode) is str and type(self.recipe) is str, "mode/recipe must be strings")
        v.require(type(self.values) is tuple and type(self.quality) is tuple and len(self.values) == len(self.quality) == 4, "four-target allowlist required")
        for value, quality in zip(self.values, self.quality):
            v.require(type(quality) is str and quality in c.QUALITY, "unknown quality")
            # Direct mathematical fixtures must satisfy the same saved precision.
            rounded = quantize_observation(value)
            v.require(value is None or value == rounded, "unquantized observation")


def decode_saved_observations(raw: bytes, *, expected_sha256: str) -> tuple[Observation, ...]:
    """Strict canonical UTF-8 JSONL -> immutable allowlisted projection.

    Partial captures are permitted for unit/prefix diagnostics; complete origin
    coverage is checked separately, never inferred from successful decoding.
    """
    v.require(type(raw) is bytes and bool(raw) and raw.endswith(b"\n") and b"\r" not in raw, "saved JSONL requires LF rows")
    v.require(type(expected_sha256) is str and re.fullmatch("[0-9a-f]{64}", expected_sha256) is not None, "invalid expected digest")
    v.require(hashlib.sha256(raw).hexdigest() == expected_sha256, "saved observation hash mismatch")
    output, last = [], (-1, -1)
    signals = (*c.TARGETS, "load_proxy")
    for line in raw[:-1].split(b"\n"):
        row = v.strict_json(line)
        v.require(type(row) is dict and set(row) == {"timestamp", "equipment_id", "equipment_type", "operating_mode", "recipe_step", "signals", "quality"}, "saved observation field allowlist")
        v.require(v.canonical_json(row) == line, "noncanonical saved JSONL row")
        equipment = row["equipment_id"]
        v.require(type(equipment) is str and equipment in c.EQUIPMENT, "unknown equipment")
        ei = c.EQUIPMENT.index(equipment)
        v.require(row["equipment_type"] == ("motor", "conveyor")[ei], "equipment type mismatch")
        timestamp = row["timestamp"]
        v.require(type(timestamp) is str and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.000Z", timestamp) is not None, "saved UTC millisecond timestamp at whole second required")
        try:
            delta = datetime.fromisoformat(timestamp) - datetime(1970, 1, 1, tzinfo=timezone.utc)
        except ValueError as exc:
            raise v.V03ValidationError("invalid UTC timestamp") from exc
        ms = (delta.days*86400 + delta.seconds)*1000
        v.require(c.START_MS <= ms < c.START_MS+9000000, "observation outside registered capture")
        coordinate = (ei, ms)
        v.require(coordinate > last, "duplicate/reversed observation timestamp or equipment order")
        last = coordinate
        v.require(type(row["signals"]) is dict and type(row["quality"]) is dict and set(row["signals"]) == set(row["quality"]) == set(signals), "saved signal inventory mismatch")
        for signal in signals:
            cell = row["signals"][signal]
            v.require(type(cell) is dict and set(cell) == {"unit", "value"} and type(cell["unit"]) is str, "saved signal field allowlist")
            value = cell["value"]
            rounded = quantize_observation(value)
            v.require(value is None or value == rounded, "unquantized saved observation")
            v.require(type(row["quality"][signal]) is str and row["quality"][signal] in c.QUALITY, "unknown quality")
        output.append(Observation(equipment, ms, row["operating_mode"], row["recipe_step"],
                                  tuple(row["signals"][t]["value"] for t in c.TARGETS),
                                  tuple(row["quality"][t] for t in c.TARGETS)))
    return tuple(output)


@dataclass(frozen=True, slots=True)
class PhaseState:
    previous: Observation
    phase: int | None
    visit_start_ms: int | None

    def __post_init__(self):
        v.require(type(self.previous) is Observation, "phase previous observation required")
        v.require(self.phase is None or type(self.phase) is int and 0 <= self.phase < 30, "invalid phase state")
        v.require((self.phase is None and self.visit_start_ms is None) or
                  (self.phase is not None and type(self.visit_start_ms) is int and self.visit_start_ms >= 0
                   and self.previous.timestamp_ms == self.visit_start_ms+self.phase*1000), "invalid phase visit origin")


def _known(row):
    return row.mode in c.MODES and row.recipe == c.RECIPES[c.MODES.index(row.mode)]


def advance_phase(state: PhaseState | None, row: Observation) -> PhaseState:
    """Observe entries; never modulo a schedule or guess entry after a gap.

    The first observation has unknown phase until a contiguous mode transition.
    Warm-up absorbs this initial uncertainty in the registered capture.
    A recipe-only change invalidates phase until the next observed mode entry.
    """
    v.require(type(row) is Observation and (state is None or type(state) is PhaseState), "invalid phase state input")
    phase = visit = None
    if state is not None:
        previous = state.previous
        v.require(row.equipment == previous.equipment, "phase state crosses equipment")
        v.require(row.timestamp_ms > previous.timestamp_ms, "duplicate/reversed timestamp")
        if row.timestamp_ms == previous.timestamp_ms+1000 and _known(row):
            if row.mode != previous.mode:
                phase, visit = 0, row.timestamp_ms
            elif row.recipe == previous.recipe and state.phase is not None and state.phase < 29:
                phase, visit = state.phase+1, state.visit_start_ms
    return PhaseState(row, phase, visit)


def exclusion_tags(candidate: str, row: Observation, previous: Observation | None,
                   phase: int | None, target: int, *, profile_ready: bool = True) -> list[str]:
    """Ordered, nonexclusive observed-input exclusions, with no GT parameter."""
    v.require(type(candidate) is str and candidate in c.CANDIDATES, "unknown candidate")
    v.require(type(target) is int and 0 <= target < 4 and type(profile_ready) is bool, "invalid target/profile flag")
    v.require(phase is None or type(phase) is int and 0 <= phase < 30, "invalid phase")
    if previous is not None:
        v.require(previous.equipment == row.equipment and previous.timestamp_ms < row.timestamp_ms, "invalid observation history")
    tags = []
    if row.quality[target] != "ok":
        tags.append(c.REASONS[0])
    if row.values[target] is None:
        tags.append(c.REASONS[1])
    contiguous = previous is not None and previous.timestamp_ms+1000 == row.timestamp_ms
    if not contiguous:
        tags.append(c.REASONS[2])
    if previous is not None and (previous.quality[target] != "ok" or previous.values[target] is None):
        tags.append(c.REASONS[3])
    if (phase in (None, 0) or not _known(row) or previous is None
            or (previous.mode, previous.recipe) != (row.mode, row.recipe)):
        tags.append(c.REASONS[4])
    if candidate == c.CANDIDATES[2] and any(
            obs.quality[i] != "ok" or obs.values[i] is None
            for obs in (row, previous) if obs is not None for i in range(4) if i != target):
        tags.append(c.REASONS[5])
    if not profile_ready:
        tags.append(c.REASONS[6])
    return tags


@dataclass(frozen=True, slots=True)
class _Profile:
    equipment: str
    target: int
    mode: str
    status: str = "inconclusive"
    fit_samples: tuple = ()
    calibration_samples: tuple = ()
    phase_medians: tuple | None = None
    center: float | None = None
    scale: float | None = None
    c2_state: tuple | None = None
    reason: str | None = "insufficient_points"

    def identifier(self, identity):
        return f'{identity["evaluation_id"]}-profile-{self.equipment}-{c.TARGETS[self.target]}-{self.mode}'

    def ledger(self, identity):
        state = None if self.c2_state is None else dict(zip(
            ("centers", "scales", "mean", "covariance", "precision"),
            [list(x) if i < 3 else [list(row) for row in x] for i, x in enumerate(self.c2_state)]))
        return {"profile_id": self.identifier(identity), "identity": dict(identity), "profile_version": "0.3",
                "equipment": self.equipment, "full_target": self.equipment+"."+c.TARGETS[self.target],
                "mode": self.mode, "recipe": c.RECIPES[c.MODES.index(self.mode)], "status": self.status,
                "fit_samples": list(self.fit_samples), "calibration_samples": list(self.calibration_samples),
                "planned_calibration_points": 290, "minimum_calibration_points": 250,
                "phase_medians": None if self.phase_medians is None else list(self.phase_medians),
                "center": self.center, "scale": self.scale, "c2_state": state, "reason": self.reason}


@dataclass(frozen=True, slots=True)
class ProfileSet:
    """Immutable independent candidate fit. Exported ledger rows are copies."""

    identity_json: bytes
    profiles: tuple
    normal_prefix_issues: tuple

    def ledger_rows(self) -> list[dict]:
        identity = v.strict_json(self.identity_json)
        return [p.ledger(identity) for p in self.profiles]


def _sample(row):
    return (row.timestamp_ms-c.START_MS)//1000


def _phased(observations):
    states = {}
    for row in observations:
        old = states.get(row.equipment)
        state = advance_phase(old, row)
        states[row.equipment] = state
        yield row, old.previous if old else None, state.phase


def _residual(candidate, row, previous, phase, profiles, target):
    if candidate == c.CANDIDATES[0]:
        return n.finite(row.values[target]-previous.values[target])
    errors = [n.finite(row.values[i]-profiles[i].phase_medians[phase]) for i in range(4)] if candidate == c.CANDIDATES[2] else None
    if errors is not None:
        return n.conditional_residual(errors, profiles[target].c2_state, target)
    return n.finite(row.values[target]-profiles[target].phase_medians[phase])


def fit_profiles(identity: dict, raw: bytes, *, expected_sha256: str) -> ProfileSet:
    """Fit 48 profiles using only saved warm-up/fit/calibration; never test.

    Prefix contract defects are separately reported, even if >=250 residuals
    suffice numerically. A runner must not treat such diagnostics as acceptance.
    """
    v.validate_identity(identity)
    observations = decode_saved_observations(raw, expected_sha256=expected_sha256)
    candidate = identity["candidate_id"]
    phased = [x for x in _phased(observations) if _sample(x[0]) < 7200]
    issues, by_mode = [], {}
    coordinates = {(row.equipment, _sample(row)) for row, _, _ in phased}
    if coordinates != {(e, s) for e in c.EQUIPMENT for s in range(7200)}:
        issues.append("incomplete_normal_prefix")
    for row, previous, phase in phased:
        sample = _sample(row)
        if sample >= 1800:
            if not _known(row) or row.mode != c.MODES[(sample % 180)//30] or phase != sample % 30:
                issues.append("normal_mode_recipe_phase")
            if any(q != "ok" for q in row.quality) or any(x is None for x in row.values):
                issues.append("normal_quality_or_missing")
        by_mode.setdefault((row.equipment, row.mode), []).append((row, previous, phase))
    result = []
    for equipment in c.EQUIPMENT:
        modes = {}
        for mode in c.MODES:
            rows = by_mode.get((equipment, mode), [])
            fit = [(r, p, u) for r, p, u in rows if 1800 <= _sample(r) < 5400]
            profiles = [_Profile(equipment, i, mode) for i in range(4)]
            for i in range(4):
                if candidate == c.CANDIDATES[0]:
                    profiles[i] = replace(profiles[i], reason=None)
                    continue
                usable = [(r, u) for r, _, u in fit if u is not None and _known(r) and r.quality[i] == "ok" and r.values[i] is not None]
                samples = tuple(_sample(r) for r, _ in usable)
                groups = [[r.values[i] for r, u in usable if u == phase] for phase in range(30)]
                profiles[i] = replace(profiles[i], fit_samples=samples)
                if any(len(group) != 20 for group in groups):
                    continue
                try:
                    medians = tuple(n.median(group) for group in groups)
                    profiles[i] = replace(profiles[i], phase_medians=medians, reason=None)
                except (n.NumericalInconclusive, OverflowError) as exc:
                    profiles[i] = replace(profiles[i], reason=str(exc) if isinstance(exc, n.NumericalInconclusive) else "nonfinite")
            if candidate == c.CANDIDATES[2]:
                reason = next((p.reason for p in profiles if p.reason), None)
                state = None
                if reason is None:
                    complete = [(r, u) for r, previous, u in fit if not exclusion_tags(candidate, r, previous, u, 0)]
                    try:
                        errors = [tuple(n.finite(r.values[i]-profiles[i].phase_medians[u]) for i in range(4)) for r, u in complete]
                        state = n.conditional_fit(errors)
                    except (n.NumericalInconclusive, OverflowError) as exc:
                        reason = str(exc) if isinstance(exc, n.NumericalInconclusive) else "nonfinite"
                profiles = [replace(p, c2_state=state, reason=reason) for p in profiles]
            for i in range(4):
                profile = profiles[i]
                if profile.reason is not None:
                    continue
                samples, residuals = [], []
                try:
                    for row, previous, phase in rows:
                        if not 5400 <= _sample(row) < 7200 or exclusion_tags(candidate, row, previous, phase, i):
                            continue
                        residuals.append(_residual(candidate, row, previous, phase, profiles, i))
                        samples.append(_sample(row))
                    if len(samples) < 250:
                        raise n.NumericalInconclusive("insufficient_points")
                    center, scale = n.center_scale(residuals)
                    profiles[i] = replace(profile, status="calibrated", calibration_samples=tuple(samples), center=center, scale=scale)
                except (n.NumericalInconclusive, OverflowError) as exc:
                    profiles[i] = replace(profile, calibration_samples=tuple(samples), reason=str(exc) if isinstance(exc, n.NumericalInconclusive) else "nonfinite")
            modes[mode] = profiles
        result.extend(modes[mode][i] for i in range(4) for mode in c.MODES)
    return ProfileSet(v.canonical_json(identity), tuple(result), tuple(sorted(set(issues))))


def score_test(profiles: ProfileSet, raw: bytes, *, expected_sha256: str) -> list[dict]:
    """Score the supplied test prefix, preserving every present target origin.

    No persistence is assigned here (the separate episode builder does that).
    Unknown labels cannot be encoded in the frozen S1 score enums and raise an
    input-contract error; advance_phase/exclusion_tags expose their unavailable
    diagnostic without inventing a registered mode/recipe in the ledger.
    """
    v.require(type(profiles) is ProfileSet, "locked ProfileSet required")
    identity = v.strict_json(profiles.identity_json)
    v.validate_identity(identity)
    observations = decode_saved_observations(raw, expected_sha256=expected_sha256)
    candidate = identity["candidate_id"]
    bank = {(p.equipment, p.mode, p.target): p for p in profiles.profiles}
    v.require(len(bank) == len(profiles.profiles) == 48, "profile inventory incomplete")
    scores = []
    for row, previous, phase in _phased(observations):
        sample = _sample(row)
        if sample < 7200:
            continue
        v.require(_known(row), "unknown mode/recipe cannot be encoded by frozen score contract")
        own = [bank[row.equipment, row.mode, i] for i in range(4)]
        for i, profile in enumerate(own):
            tags = exclusion_tags(candidate, row, previous, phase, i, profile_ready=profile.status == "calibrated")
            residual = score = None
            if not tags:
                try:
                    residual = _residual(candidate, row, previous, phase, own, i)
                    score = n.finite(abs(residual-profile.center)/profile.scale)
                except (n.NumericalInconclusive, OverflowError, ZeroDivisionError):
                    tags.append(c.REASONS[7])
                    residual = score = None
            dependencies = []
            for j in (range(4) if candidate == c.CANDIDATES[2] else (i,)):
                for obs in (previous, row):
                    if obs is not None and obs.timestamp_ms in (row.timestamp_ms-1000, row.timestamp_ms):
                        dependencies.append({"full_target": row.equipment+"."+c.TARGETS[j], "sample": _sample(obs),
                                             "timestamp_ms": obs.timestamp_ms, "quality": obs.quality[j], "value": obs.values[j]})
            exceeded = score is not None and score > (4.0 if candidate == c.CANDIDATES[0] else 6.0)
            scores.append({"score_id": f'{identity["evaluation_id"]}-score-{row.equipment}-{c.TARGETS[i]}-{sample:04d}',
                           "dataset_id": identity["dataset_id"], "candidate_id": candidate, "sample": sample,
                           "timestamp_ms": row.timestamp_ms, "phase": phase, "equipment": row.equipment,
                           "full_target": row.equipment+"."+c.TARGETS[i], "mode": row.mode, "recipe": row.recipe,
                           "profile_id": profile.identifier(identity), "dependencies": dependencies,
                           "residual": residual, "score": score, "available": not tags, "exclusion_reason": tags[0] if tags else None,
                           "exclusion_tags": tags, "threshold_exceeded": exceeded, "streak": int(exceeded), "source_episode_id": None})
    return scores
