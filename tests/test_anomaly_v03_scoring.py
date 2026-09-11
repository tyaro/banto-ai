"""S2 arithmetic/causality fixtures, not registered-seed materialization or runs."""

from __future__ import annotations

import copy
import hashlib
import inspect
import math
import unittest
from contextlib import ExitStack
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from banto_ai import _anomaly_v03_contract as c
from banto_ai import _anomaly_v03_numeric as n
from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_scoring as s
from tools.ci_shared_fixtures import record


def identity(candidate=0, layout=0, stratum="core"):
    return v.evaluation_inventory("dev")[layout*6+(3 if stratum == "quality-stress" else 0)+candidate]


def saved_row(equipment, sample, *, constant=False):
    """Explicit algebraic fixture, no generator/random seed/event model."""
    phase, mode, cycle = sample % 30, (sample % 180)//30, sample//180
    values = [float(100+i*10) if constant else round(100+i*10+mode*2+phase*0.25+(((cycle*(i+3)+phase*(i+5)+phase*phase*(i+2))%23)-11)*0.02, 6) for i in range(4)]
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)+timedelta(seconds=sample)
    return {"timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%S.000Z"), "equipment_id": equipment,
            "equipment_type": "motor" if equipment == "motor-01" else "conveyor", "operating_mode": c.MODES[mode], "recipe_step": c.RECIPES[mode],
            "signals": {t: {"value": value, "unit": "fixture"} for t, value in zip((*c.TARGETS, "load_proxy"), (*values, 0.0))},
            "quality": {t: "ok" for t in (*c.TARGETS, "load_proxy")}}


def encode(rows):
    raw = b"".join(v.canonical_json(row)+b"\n" for row in rows)
    return raw, hashlib.sha256(raw).hexdigest()


def fit(candidate, raw, digest):
    return s.fit_profiles(identity(candidate), raw, expected_sha256=digest)


def obs(sample, *, mode="stopped", recipe="stop", equipment="motor-01", values=(1.0, 2.0, 3.0, 4.0), quality=("ok",)*4):
    return s.Observation(equipment, c.START_MS+sample*1000, mode, recipe, values, quality)


class QuantizationAndCaptureTests(unittest.TestCase):
    def test_Q1_overlay_before_rounding(self):
        correct = s.quantize_observation(max(0, 1.0000014*(1-0.55)))
        premature = s.quantize_observation(s.quantize_observation(1.0000014)*(1-0.55))
        self.assertEqual(correct, 0.450001)
        self.assertEqual(premature, 0.45)
        record("Q1", self.id(), lambda: {"overlay_then_round": correct, "premature_round": premature})

    def test_Q2_finalizer_does_not_round_or_replace_normal_latent_state(self):
        normal = {"temperature": 24.123456789}
        result = s.quantize_observation(normal["temperature"]+8.0)
        self.assertEqual(result, 32.123457)
        self.assertEqual(normal["temperature"], 24.123456789)
        record("Q2", self.id(), lambda: {"normal": normal, "observation": result})

    def test_Q3_final_quality_null_is_not_imputed(self):
        normal = 24.123456789
        masked, quality = None, "missing"
        result = s.quantize_observation(masked)
        self.assertIsNone(result)
        self.assertEqual((normal, quality), (24.123456789, "missing"))
        record("Q3", self.id(), lambda: {"normal": normal, "quality": quality, "observation": result})

    def test_Q4_binary64_ties(self):
        result = [s.quantize_observation(x) for x in (0.0078125, 0.0234375)]
        self.assertEqual(result, [0.007812, 0.023438])
        record("Q4", self.id(), lambda: result)

    def test_Q5_signed_zero_numeric_and_saved_JSON_bytes(self):
        value = s.quantize_observation(-0.0000004)
        self.assertEqual(math.copysign(1, value), -1)
        self.assertEqual(v.canonical_json(value), b"-0.0")
        row = saved_row("motor-01", 7200)
        row["signals"]["motor_current"]["value"] = value
        raw, digest = encode([row])
        projected = s.decode_saved_observations(raw, expected_sha256=digest)[0]
        self.assertEqual(math.copysign(1, projected.values[0]), -1)
        record("Q5", self.id(), lambda: {"value": value, "saved_jsonl": raw.decode("utf-8"),
                                         "sha256": digest, "decoded_value": projected.values[0]})

    def test_nonfinite_bool_and_unquantized_rejected(self):
        for value in (True, False, float("nan"), float("inf"), -float("inf"), 10**1000):
            with self.subTest(value=repr(value)), self.assertRaises(v.V03ValidationError):
                s.quantize_observation(value)
        row = saved_row("motor-01", 0)
        for value in (True, False, 1.1234567):
            row["signals"]["motor_current"]["value"] = value
            raw, digest = encode([row])
            with self.subTest(value=value), self.assertRaises(v.V03ValidationError):
                s.decode_saved_observations(raw, expected_sha256=digest)

    def test_strict_saved_bytes_hash_duplicate_nonfinite_newline_and_extra_keys(self):
        row = saved_row("motor-01", 0)
        raw, digest = encode([row])
        bad_bytes = (raw[:-1], raw.replace(b"\n", b"\r\n"), b"\xef\xbb\xbf"+raw,
                     raw.replace(b'"equipment_id":', b'"equipment_id":"motor-01","equipment_id":'),
                     raw.replace(b'"value":99.78', b'"value":NaN'), b" "+raw)
        for bad in bad_bytes:
            with self.subTest(raw=bad[:80]), self.assertRaises(v.V03ValidationError):
                s.decode_saved_observations(bad, expected_sha256=hashlib.sha256(bad).hexdigest())
        with self.assertRaisesRegex(v.V03ValidationError, "hash"):
            s.decode_saved_observations(raw, expected_sha256="0"*64)
        for key in ("event_id", "event_start", "seed", "cycle", "layout", "future", "previous_event_overlap"):
            bad = copy.deepcopy(row); bad[key] = 1
            data, sha = encode([bad])
            with self.subTest(key=key), self.assertRaises(v.V03ValidationError):
                s.decode_saved_observations(data, expected_sha256=sha)

    def test_projection_excludes_load_proxy_metadata_and_other_equipment(self):
        row = saved_row("motor-01", 0)
        a, ah = encode([row])
        row["signals"]["load_proxy"]["value"] = 9999.0
        b, bh = encode([row])
        left = s.decode_saved_observations(a, expected_sha256=ah)
        right = s.decode_saved_observations(b, expected_sha256=bh)
        self.assertEqual(left, right)
        self.assertEqual(set(left[0].__slots__), {"equipment", "timestamp_ms", "mode", "recipe", "values", "quality"})
        with self.assertRaises(FrozenInstanceError): left[0].values = (0.0,)*4

    def test_duplicate_reversed_time_and_equipment_order_rejected(self):
        for rows in ([saved_row("motor-01", 1)]*2,
                     [saved_row("motor-01", 2), saved_row("motor-01", 1)],
                     [saved_row("conveyor-01", 0), saved_row("motor-01", 0)]):
            raw, digest = encode(rows)
            with self.assertRaisesRegex(v.V03ValidationError, "duplicate/reversed"):
                s.decode_saved_observations(raw, expected_sha256=digest)

    def test_bad_timestamp_type_unknown_signal_quality_and_nested_GT(self):
        for kind in ("bool-time", "invalid-date", "extra-signal", "unknown-quality", "nested-GT"):
            row = saved_row("motor-01", 0)
            if kind == "bool-time": row["timestamp"] = True
            elif kind == "invalid-date": row["timestamp"] = "2026-02-31T00:00:00.000Z"
            elif kind == "extra-signal": row["signals"]["event_id"] = {"value": 1, "unit": "x"}
            elif kind == "unknown-quality": row["quality"]["motor_current"] = "good"
            else: row["signals"]["motor_current"]["GT"] = True
            raw, digest = encode([row])
            with self.subTest(kind=kind), self.assertRaises(v.V03ValidationError):
                s.decode_saved_observations(raw, expected_sha256=digest)


class PhaseAndAvailabilityTests(unittest.TestCase):
    def test_first_observation_unknown_then_observed_entry(self):
        state = s.advance_phase(None, obs(17))
        self.assertIsNone(state.phase)
        state = s.advance_phase(state, obs(18, mode="startup", recipe="start"))
        self.assertEqual((state.phase, state.visit_start_ms), (0, c.START_MS+18000))
        state = s.advance_phase(state, obs(19, mode="startup", recipe="start"))
        self.assertEqual(state.phase, 1)  # not absolute sample modulo 30

    def test_gap_never_guesses_phase_or_recovers_until_observed_entry(self):
        state = s.advance_phase(s.advance_phase(None, obs(29)), obs(30, mode="startup", recipe="start"))
        state = s.advance_phase(state, obs(32, mode="startup", recipe="start"))
        self.assertIsNone(state.phase)
        state = s.advance_phase(state, obs(33, mode="startup", recipe="start"))
        self.assertIsNone(state.phase)
        state = s.advance_phase(state, obs(34, mode="nominal", recipe="run"))
        self.assertEqual(state.phase, 0)

    def test_gap_plus_mode_change_unknown_not_entry(self):
        state = s.advance_phase(s.advance_phase(None, obs(29)), obs(31, mode="startup", recipe="start"))
        self.assertIsNone(state.phase)

    def test_recipe_change_unknown_mode_duration_overflow_and_no_fallback(self):
        state = s.advance_phase(s.advance_phase(None, obs(29)), obs(30, mode="startup", recipe="start"))
        for sample in range(31, 60): state = s.advance_phase(state, obs(sample, mode="startup", recipe="start"))
        self.assertEqual(state.phase, 29)
        self.assertIsNone(s.advance_phase(state, obs(60, mode="startup", recipe="start")).phase)
        changed = s.advance_phase(state, obs(60, mode="startup", recipe="run"))
        self.assertIsNone(changed.phase)
        self.assertIsNone(s.advance_phase(changed, obs(61, mode="startup", recipe="start")).phase)
        self.assertIsNone(s.advance_phase(state, obs(60, mode="unknown", recipe="unknown")).phase)

    def test_phase_rejects_duplicate_reversed_and_other_equipment(self):
        state = s.advance_phase(None, obs(30))
        for row in (obs(30), obs(29), obs(31, equipment="conveyor-01")):
            with self.assertRaises(v.V03ValidationError): s.advance_phase(state, row)
        with self.assertRaises(v.V03ValidationError): replace(obs(30), timestamp_ms=True)
        for phase, start in ((True, c.START_MS+29000), (30, c.START_MS), (None, c.START_MS), (1, c.START_MS)):
            with self.assertRaises(v.V03ValidationError): s.PhaseState(obs(30), phase, start)

    def test_current_and_previous_self_quality_all_candidates(self):
        for candidate in c.CANDIDATES:
            previous = obs(31, quality=("missing", "ok", "ok", "ok"), values=(None, 2.0, 3.0, 4.0))
            tags = s.exclusion_tags(candidate, obs(32), previous, 2, 0)
            self.assertEqual(tags, [c.REASONS[3]])
            tags = s.exclusion_tags(candidate, previous, obs(30), 1, 0)
            self.assertEqual(tags, list(c.REASONS[:2]))

    def test_current_and_previous_peer_quality_only_C2(self):
        for candidate in c.CANDIDATES:
            for previous_bad in (False, True):
                a, b = obs(31), obs(32)
                bad = replace(a if previous_bad else b, quality=("ok", "missing", "ok", "ok"), values=(1.0, None, 3.0, 4.0))
                tags = s.exclusion_tags(candidate, b if previous_bad else bad, bad if previous_bad else a, 2, 0)
                self.assertEqual(tags, [c.REASONS[5]] if candidate == c.CANDIDATES[2] else [])

    def test_exclusion_priority_and_all_tags_quality_boundary_gap_profile(self):
        current = obs(32, mode="startup", recipe="start", values=(None, None, 3.0, 4.0), quality=("missing", "missing", "ok", "ok"))
        previous = obs(30, quality=("stale", "ok", "ok", "ok"))
        self.assertEqual(s.exclusion_tags(c.CANDIDATES[2], current, previous, None, 0, profile_ready=False), list(c.REASONS[:7]))


class NumericTests(unittest.TestCase):
    def assertClose(self, actual, expected):
        self.assertTrue(math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), (actual, expected))

    def test_median_even_odd_and_MAD_hand_values(self):
        self.assertEqual(n.median([9.0, 1.0, 5.0, 3.0]), 4.0)
        self.assertEqual(n.median([9.0, 1.0, 5.0]), 5.0)
        center, scale = n.center_scale([1.0, 3.0, 5.0, 9.0])
        self.assertEqual(center, 4.0)
        self.assertClose(scale, 2.9652)

    def test_zero_scale_and_nonfinite_not_epsilon(self):
        for values, reason in (([1.0]*20, "zero_scale"), ([], "insufficient_points"), ([1.0, math.inf], "nonfinite")):
            with self.assertRaisesRegex(n.NumericalInconclusive, reason): n.center_scale(values)
        for value in (True, False, "1"):
            with self.assertRaises(ValueError): n.median([value])

    def test_cholesky_inverse_hand_matrix(self):
        matrix = ((2.0, 1.0, 0.0, 0.0), (1.0, 2.0, 0.0, 0.0), (0.0, 0.0, 4.0, 0.0), (0.0, 0.0, 0.0, 9.0))
        expected = ((2/3, -1/3, 0, 0), (-1/3, 2/3, 0, 0), (0, 0, 1/4, 0), (0, 0, 0, 1/9))
        for row, wanted in zip(n.inverse4(matrix), expected):
            for value, known in zip(row, wanted): self.assertClose(value, known)

    def test_singular_nonpositive_nonfinite_and_asymmetric_rejected(self):
        for matrix in ([[1.0]*4 for _ in range(4)], [[0.0]*4 for _ in range(4)], [[math.inf]*4 for _ in range(4)]):
            with self.assertRaises(n.NumericalInconclusive): n.inverse4(matrix)
        with self.assertRaises(ValueError): n.inverse4([[1.0, 2.0, 0.0, 0.0]]*4)

    def test_covariance_579_shrinkage_rank_one_and_conditional_formula(self):
        errors = [(-1.0,)*4, (1.0,)*4]*290
        state = n.conditional_fit(errors)
        b, q, mean, covariance, precision = state
        self.assertEqual(b, (0.0,)*4)
        self.assertEqual(q, (1.4826,)*4)
        self.assertEqual(mean, (0.0,)*4)
        variance = 580/579/(1.4826**2)
        for i in range(4):
            for j in range(4):
                self.assertClose(covariance[i][j], variance*(1 if i == j else 0.75))
                # Sigma = variance*(.25I+.75J); analytic inverse.
                self.assertClose(precision[i][j], ((4 if i == j else 0)-12/13)/variance)
        actual = n.conditional_residual((2.0, 0.0, 0.0, 0.0), state)
        for i in range(4):
            self.assertClose(actual[i], precision[i][0]*(2/1.4826)/math.sqrt(precision[i][i]))

    def test_finite_extremes_mixed_infinite_products_and_fsum_overflow(self):
        state = n.conditional_fit([(-1.0,)*4, (1.0,)*4]*290)
        with self.assertRaisesRegex(n.NumericalInconclusive, "nonfinite"):
            n.conditional_residual((1.6e308, 1.6e308, 0.0, 0.0), state)
        with self.assertRaisesRegex(n.NumericalInconclusive, "nonfinite"):
            n._sum((1e308, 1e308))


class ProfileAndScoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = [saved_row(equipment, sample) for equipment in c.EQUIPMENT for sample in range(7210)]
        cls.raw, cls.digest = encode(cls.rows)
        cls.banks = [fit(i, cls.raw, cls.digest) for i in range(3)]

    def test_all_48_profiles_fit20_calibrate290_and_frozen(self):
        for i, bank in enumerate(self.banks):
            self.assertEqual(bank.normal_prefix_issues, ())
            self.assertEqual(len(bank.profiles), 48)
            for profile in bank.profiles:
                self.assertEqual((profile.status, profile.reason), ("calibrated", None))
                self.assertEqual(len(profile.fit_samples), 0 if i == 0 else 600)
                self.assertEqual(len(profile.calibration_samples), 290)
                self.assertGreater(profile.scale, 0)
            ledger = bank.ledger_rows()
            v.validate_ledger_rows(identity(i), events=v.event_inventory(identity(i)), profiles=ledger, scores=[], source_episodes=[], equipment_episodes=[], incidents=[])
            numeric = {"phase_medians", "center", "scale", "c2_state"}
            record(f"profiles-C{i}", self.id(), lambda: [{k: value for k, value in row.items() if k not in numeric} for row in ledger])
            record(f"profile-values-C{i}", self.id(), lambda: {row["profile_id"]: {k: row[k] for k in sorted(numeric)} for row in ledger})
        with self.assertRaises(FrozenInstanceError): self.banks[1].profiles[0].center = 999
        exported = self.banks[2].ledger_rows(); exported[0]["c2_state"]["scales"][0] = 999
        self.assertNotEqual(self.banks[2].ledger_rows()[0]["c2_state"]["scales"][0], 999)
        self.assertIsNot(self.banks[1].profiles[0].phase_medians, self.banks[2].profiles[0].phase_medians)

    def test_hand_C0_C1_residual_and_no_profile_or_score_quantization(self):
        for i in (0, 1, 2):
            rows = s.score_test(self.banks[i], self.raw, expected_sha256=self.digest)
            self.assertEqual(len(rows), 80)
            self.assertEqual(sum(r["available"] for r in rows), 72)
            row = next(r for r in rows if r["sample"] == 7201 and r["full_target"] == c.FULL_TARGETS[0])
            profile = self.banks[i].profiles[0]
            now = self.rows[7201]["signals"]["motor_current"]["value"]
            before = self.rows[7200]["signals"]["motor_current"]["value"]
            if i < 2:
                expected = now-before if i == 0 else now-profile.phase_medians[1]
                self.assertEqual(row["residual"], expected)
                self.assertEqual(row["score"], abs(expected-profile.center)/profile.scale)
            self.assertEqual(len(row["dependencies"]), 8 if i == 2 else 2)
            self.assertTrue(any(r["score"] != round(r["score"], 6) for r in rows if r["available"]))
            record(f"scores-C{i}", self.id(), lambda: [{k: value for k, value in row.items() if k not in ("score", "residual")} for row in rows])
            record(f"score-values-C{i}", self.id(), lambda: {row["score_id"]: {k: row[k] for k in ("residual", "score")} for row in rows})

    def test_test_future_values_do_not_change_fit_or_earlier_scores(self):
        changed = copy.deepcopy(self.rows)
        for row in changed:
            if row["timestamp"] >= "2026-01-01T02:00:05.000Z":
                for cell in row["signals"].values(): cell["value"] = round(cell["value"]+123.0, 6)
        raw, digest = encode(changed)
        for i in range(3):
            self.assertEqual(fit(i, raw, digest), self.banks[i])
            original = s.score_test(self.banks[i], self.raw, expected_sha256=self.digest)
            actual = s.score_test(self.banks[i], raw, expected_sha256=digest)
            self.assertEqual([r for r in actual if r["sample"] < 7205], [r for r in original if r["sample"] < 7205])

    def test_warmup_values_do_not_fit_and_other_equipment_does_not_score(self):
        changed = copy.deepcopy(self.rows)
        for row in changed:
            if row["timestamp"] < "2026-01-01T00:30:00.000Z" or row["equipment_id"] == "conveyor-01":
                for cell in row["signals"].values(): cell["value"] = round(cell["value"]+500.0, 6)
        raw, digest = encode(changed)
        bank = fit(2, raw, digest)
        self.assertEqual(bank.profiles[:24], self.banks[2].profiles[:24])
        a = s.score_test(self.banks[2], self.raw, expected_sha256=self.digest)
        b = s.score_test(self.banks[2], raw, expected_sha256=digest)
        self.assertEqual([r for r in a if r["equipment"] == "motor-01"], [r for r in b if r["equipment"] == "motor-01"])

    def test_insufficient_samephase20_and_C2_modewide_failure(self):
        changed = copy.deepcopy(self.rows)
        changed[1805]["signals"]["motor_current"]["value"] = None
        changed[1805]["quality"]["motor_current"] = "missing"
        raw, digest = encode(changed)
        for i in (1, 2):
            bank = fit(i, raw, digest)
            self.assertIn("normal_quality_or_missing", bank.normal_prefix_issues)
            failed = [p for p in bank.profiles if p.status == "inconclusive"]
            self.assertEqual(len(failed), 1 if i == 1 else 4)
            self.assertTrue(all(p.reason == "insufficient_points" for p in failed))

    def test_MAD_zero_is_inconclusive_and_all_test_rows_still_present(self):
        rows = [saved_row(e, sample, constant=True) for e in c.EQUIPMENT for sample in range(7203)]
        raw, digest = encode(rows)
        for i in range(3):
            bank = fit(i, raw, digest)
            self.assertEqual(bank.normal_prefix_issues, ())
            self.assertTrue(all(p.status == "inconclusive" and p.reason == "zero_scale" for p in bank.profiles))
            scores = s.score_test(bank, raw, expected_sha256=digest)
            self.assertEqual(len(scores), 24)
            self.assertTrue(all(not r["available"] and "profile_inconclusive" in r["exclusion_tags"] for r in scores))

    def test_calibration_250_boundary_and_prefix_defect_separately_reported(self):
        changed = copy.deepcopy(self.rows)
        for base in (5400, 5580):
            for sample in range(base, base+20):
                changed[sample]["quality"]["motor_current"] = "invalid"
        raw, digest = encode(changed)
        bank = fit(1, raw, digest)
        self.assertEqual((len(bank.profiles[0].calibration_samples), bank.profiles[0].status), (250, "calibrated"))
        self.assertIn("normal_quality_or_missing", bank.normal_prefix_issues)
        changed[5761]["quality"]["motor_current"] = "invalid"
        raw, digest = encode(changed)
        bank = fit(1, raw, digest)
        self.assertEqual((len(bank.profiles[0].calibration_samples), bank.profiles[0].reason), (248, "insufficient_points"))

    def test_peer_dropout_stops_C2_all_four_but_C1_only_temperature(self):
        changed = copy.deepcopy(self.rows)
        changed[7202]["quality"]["motor_temperature"] = "missing"
        changed[7202]["signals"]["motor_temperature"]["value"] = None
        raw, digest = encode(changed)
        for i in range(3):
            rows = s.score_test(self.banks[i], raw, expected_sha256=digest)
            unavailable = [r for r in rows if r["equipment"] == "motor-01" and r["sample"] in (7202, 7203) and not r["available"]]
            self.assertEqual(len(unavailable), 8 if i == 2 else 2)

    def test_GT_not_accepted_and_pure_no_IO_environment_network(self):
        for function in (s.fit_profiles, s.score_test, s.advance_phase, s.exclusion_tags):
            self.assertNotIn("events", inspect.signature(function).parameters)
        with ExitStack() as traps:
            for name in ("builtins.open", "pathlib.Path.open", "pathlib.Path.stat", "os.stat", "os.getenv", "os.listdir", "socket.socket", "subprocess.run", "subprocess.Popen"):
                traps.enter_context(patch(name, side_effect=AssertionError("unexpected I/O")))
            bank = fit(0, self.raw, self.digest)
            self.assertEqual(bank, self.banks[0])
            self.assertEqual(len(s.score_test(bank, self.raw, expected_sha256=self.digest)), 80)

    def test_score_overflow_is_unavailable_not_infinite_or_zero(self):
        changed = copy.deepcopy(self.rows)
        changed[7201]["signals"]["motor_current"]["value"] = -1e308
        changed[7202]["signals"]["motor_current"]["value"] = 1e308
        raw, digest = encode(changed)
        scores = s.score_test(self.banks[0], raw, expected_sha256=digest)
        row = next(r for r in scores if r["sample"] == 7202 and r["full_target"] == c.FULL_TARGETS[0])
        self.assertFalse(row["available"])
        self.assertEqual(row["exclusion_tags"], ["nonfinite_score"])
        self.assertIsNone(row["score"])

    def test_C2_nonfinite_conditional_component_only_excludes_that_target(self):
        # An explicit locked arithmetic fixture, not a claimed normal fit.
        covariance = tuple(tuple((0.25 if i == 0 else 1.0) if i == j else 0.0 for j in range(4)) for i in range(4))
        state = ((0.0,)*4, (1.0,)*4, (0.0,)*4, covariance, n.inverse4(covariance))
        bank = replace(self.banks[2], profiles=tuple(replace(p, c2_state=state) for p in self.banks[2].profiles))
        changed = copy.deepcopy(self.rows)
        changed[7202]["signals"]["motor_current"]["value"] = 1e308
        raw, digest = encode(changed)
        rows = [r for r in s.score_test(bank, raw, expected_sha256=digest) if r["sample"] == 7202 and r["equipment"] == "motor-01"]
        self.assertEqual([r["available"] for r in rows], [False, True, True, True])
        self.assertEqual(rows[0]["exclusion_tags"], ["nonfinite_score"])

    def test_unknown_recipe_stops_ledger_encoding_without_false_registered_label(self):
        changed = copy.deepcopy(self.rows)
        changed[7202]["recipe_step"] = "unregistered-recipe"
        raw, digest = encode(changed)
        with self.assertRaisesRegex(v.V03ValidationError, "unknown mode/recipe"):
            s.score_test(self.banks[1], raw, expected_sha256=digest)

    def test_valid_test_prefix_extension_preserves_earlier_scores(self):
        prefix = [r for r in self.rows if r["timestamp"] < "2026-01-01T02:00:05.000Z"]
        raw, digest = encode(prefix)
        for bank in self.banks:
            partial = s.score_test(bank, raw, expected_sha256=digest)
            full = s.score_test(bank, self.raw, expected_sha256=self.digest)
            self.assertEqual(partial, [r for r in full if r["sample"] < 7205])

    def test_gap_test_rows_remain_unknown_without_modulo_schedule_recovery(self):
        rows = self.rows[:7202]+self.rows[7203:]
        raw, digest = encode(rows)
        scores = s.score_test(self.banks[1], raw, expected_sha256=digest)
        first = next(r for r in scores if r["sample"] == 7203 and r["full_target"] == c.FULL_TARGETS[0])
        self.assertEqual(first["exclusion_tags"], ["no_previous_or_gap", "mode_recipe_or_phase"])
        self.assertTrue(all(r["phase"] is None and not r["available"] for r in scores if r["sample"] >= 7203 and r["equipment"] == "motor-01"))

    def test_normal_prefix_missing_sample_is_separate_contract_defect(self):
        raw, digest = encode(self.rows[:1805]+self.rows[1806:])
        bank = fit(1, raw, digest)
        self.assertIn("incomplete_normal_prefix", bank.normal_prefix_issues)
        self.assertIn("normal_mode_recipe_phase", bank.normal_prefix_issues)
        self.assertTrue(all(p.reason == "insufficient_points" for p in bank.profiles if p.equipment == "motor-01" and p.mode == "stopped"))

    def test_C2_cholesky_failure_is_modewide_inconclusive_never_jittered(self):
        with patch.object(n, "inverse4", side_effect=n.NumericalInconclusive("cholesky_failure")) as inverse:
            bank = fit(2, self.raw, self.digest)
        self.assertEqual(inverse.call_count, 12)
        self.assertTrue(all(p.status == "inconclusive" and p.reason == "cholesky_failure" and p.c2_state is None for p in bank.profiles))


if __name__ == "__main__":
    unittest.main()
