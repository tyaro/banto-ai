"""Opt-in, bounded snapshots of existing hand fixtures; no fixture execution."""

import hashlib
import json
from contextlib import contextmanager
from contextvars import ContextVar

VERSION = "anomaly-v03-shared.1"
MAX_PAYLOAD_BYTES = 512 * 1024
MAX_TOTAL_BYTES = 4 * 1024 * 1024


def _owner(module, cls, method):
    return f"tests.test_anomaly_v03{module}.{cls}.test_{method}"


EXPECTED = {
    **{f"Q{i}": (_owner("_scoring", "QuantizationAndCaptureTests", method), "exact")
       for i, method in enumerate(("Q1_overlay_before_rounding", "Q2_finalizer_does_not_round_or_replace_normal_latent_state",
                                  "Q3_final_quality_null_is_not_imputed", "Q4_binary64_ties",
                                  "Q5_signed_zero_numeric_and_saved_JSON_bytes"), 1)},
    **{f"M{i}": (_owner("_episodes", "MatchingGoldenTests", method), "exact")
       for i, method in enumerate(("M1_first_pre_event_support_no_retry", "M2_minimum_causal_delay_one_second",
                                  "M3_ended_pre_event_episode_not_a_candidate", "M4_right_endpoint_is_outside_half_open_window",
                                  "M5_first_other_target_does_not_retry", "M6_late_target_in_merge_never_moves_group_onset",
                                  "M7_mode_entry_minimum_delay_two_seconds", "M8_equality_does_not_exceed",
                                  "M9_forged_unavailable_support_stops_before_selection"), 1)},
    "seeds": (_owner("", "V03ContractTests", "seed_registry_independent_recalculation"), "exact"),
    "bootstrap": (_owner("", "V03ContractTests", "full_bootstrap_independent_hash_and_golden"), "exact"),
    "accounting": (_owner("_episodes", "AccountingTests", "zero_alert_precision_null_all_planned_incidents_and_origins"), "exact"),
    **{f"{kind}-C{i}": (_owner("_scoring", "ProfileAndScoreTests", method), mode)
       for i in range(3) for kind, method, mode in (
           ("profiles", "all_48_profiles_fit20_calibrate290_and_frozen", "exact"),
           ("profile-values", "all_48_profiles_fit20_calibrate290_and_frozen", "numeric"),
           ("scores", "hand_C0_C1_residual_and_no_profile_or_score_quantization", "exact"),
           ("score-values", "hand_C0_C1_residual_and_no_profile_or_score_quantization", "numeric"))},
}
_current = ContextVar("banto_ci_shared_fixtures", default=None)


def canonical(value):
    def check(item):
        if type(item) is dict:
            if not all(type(key) is str for key in item):
                raise ValueError("fixture JSON keys must be strings")
            for child in item.values(): check(child)
        elif type(item) is list:
            for child in item: check(child)
        elif type(item) not in (str, int, float, bool, type(None)):
            raise ValueError("fixture must contain JSON values")
    check(value)
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


class Capture:
    def __init__(self, emit):
        self.emit = emit
        self.expected = dict(EXPECTED)
        self.seen = set()
        self.total_bytes = 0
        self.failed = False

    def record(self, fixture_id, test_id, payload_factory):
        try:
            if fixture_id not in self.expected or fixture_id in self.seen or self.expected[fixture_id][0] != test_id:
                raise ValueError("unexpected, duplicate or wrong-owner fixture")
            payload = canonical(payload_factory())
            if len(payload) > MAX_PAYLOAD_BYTES or self.total_bytes + len(payload) > MAX_TOTAL_BYTES:
                raise ValueError("shared fixture byte limit exceeded")
            self.emit("shared_fixture", fixture_version=VERSION, fixture_id=fixture_id, test_id=test_id,
                      comparison=self.expected[fixture_id][1], payload_json=payload.decode("utf-8"),
                      payload_bytes=len(payload), payload_sha256=hashlib.sha256(payload).hexdigest())
            self.total_bytes += len(payload)
            self.seen.add(fixture_id)
        except BaseException:
            self.failed = True
            raise

    def complete(self):
        return not self.failed and self.seen == self.expected.keys()


@contextmanager
def capture(emit):
    collector = Capture(emit)
    token = _current.set(collector)
    try:
        yield collector
    finally:
        _current.reset(token)


def record(fixture_id, test_id, payload_factory):
    """Evaluate the payload factory only while an explicit capture is active."""
    collector = _current.get()
    if collector is not None:
        collector.record(fixture_id, test_id, payload_factory)
