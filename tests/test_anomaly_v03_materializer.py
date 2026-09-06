"""S3 hand-materialized fixtures; registered seeds never reach a PRNG in CI."""

from __future__ import annotations

import copy
import math
import unittest
import weakref
from dataclasses import replace
from unittest.mock import patch

from banto_ai import _anomaly_v03_contract as c
from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_materializer as m
from tests.test_anomaly_v03_scoring import identity


def hand_normal():
    """Explicit algebraic values, not any registered random seed's observations."""
    for equipment in c.EQUIPMENT:
        for sample in range(9000):
            phase, mode, cycle = sample % 30, (sample % 180)//30, sample//180
            values = [100+i*10+mode*2+phase*0.25+(((cycle*(i+3)+phase*(i+5)+phase*phase*(i+2))%23)-11)*0.02
                      for i in range(4)]
            yield equipment, sample, dict(zip(m.SIGNALS, (*values, 42.123456789)))


def hand_pair(ident=None):
    with patch.object(m, "normal_stream", side_effect=AssertionError("registered generation forbidden in S3 fixtures")):
        return m._build_pair(identity() if ident is None else ident, hand_normal())


def release_class_fields(owner, *names):
    """Drop owned fixtures explicitly, including after a failed class setup."""
    for name in names:
        if name in owner.__dict__:
            delattr(owner, name)


class MaterializerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.addClassCleanup(release_class_fields, cls, "pair")
        cls.pair = hand_pair()

    def test_complete_bytes_and_saved_inputs(self):
        m.validate_pair(*self.pair)
        for data in self.pair:
            ident = v.strict_json(data.identity_json)
            files = data.files()
            self.assertEqual(len(files["observations.jsonl"].splitlines()), 18000)
            self.assertEqual(len(files["quality-mask.jsonl"].splitlines()), 18000)
            self.assertEqual(len(files["event-ledger.jsonl"].splitlines()), 40)
            self.assertEqual(len(files["events.jsonl"].splitlines()), 30 if ident["stratum"] == "core" else 40)
            self.assertEqual(v.strict_json(files["origins.json"]), list(range(7200, 9000)))
            self.assertEqual(v.strict_json(files["targets.json"]), list(c.FULL_TARGETS))
            self.assertEqual(m.validate_dataset(ident, files), data.input_hashes())

    def test_pair_repeated_bytes_and_fingerprint_formula(self):
        self.assertEqual(hand_pair(), self.pair)
        for data in self.pair:
            files = data.files()
            fingerprint = v.strict_json(files["fingerprint.json"])
            hashes = {name: m.sha(files[name]) for name in m.FINGERPRINT_FILE_NAMES}
            expected = m.sha("".join(name+"\n"+digest+"\n" for name, digest in sorted(hashes.items())).encode())
            self.assertEqual(fingerprint["dataset_fingerprint"], expected)

    def test_Q1_real_machine_overlay_precedes_rounding(self):
        event = v.event_inventory(identity())[0]
        normal = dict.fromkeys(m.SIGNALS, 1.0000014)
        values, _ = m.overlay_sample(normal, "motor-01", 7200, [event], {})
        self.assertEqual(values["motor_current"], 0.450001)
        self.assertEqual(normal["motor_current"], 1.0000014)
        self.assertEqual(values["vibration_feature"], 2.100001)

    def test_Q2_Q3_unrounded_normal_state_and_quality_last(self):
        ident = identity(stratum="quality-stress")
        sensor = next(e for e in v.event_inventory(ident) if e["cycle"] == 9 and e["event_class"] == "sensor")
        dropout = next(e for e in v.event_inventory(ident) if e["cycle"] == 9 and e["event_class"] == "data_quality")
        normal = dict.fromkeys(m.SIGNALS, 24.123456789)
        before = copy.deepcopy(normal)
        first, _ = m.overlay_sample(normal, "motor-01", sensor["start_sample"], [dropout, sensor], {})
        self.assertEqual(first["motor_temperature"], 32.123457)
        masked, quality = m.overlay_sample(normal, "motor-01", dropout["start_sample"], [dropout, sensor], {})
        self.assertIsNone(masked["motor_temperature"])
        self.assertEqual(quality["motor_temperature"], "missing")
        self.assertEqual(normal, before)
        seen = []
        def base(kind, mode, previous, rng):
            seen.append(previous)
            return dict(normal), normal["motor_temperature"]
        with patch.object(m, "_base_values", side_effect=base), patch.object(m.random, "Random") as rng:
            stream = m.normal_stream(123456)  # explicitly not a registered seed
            next(stream); next(stream)
        self.assertEqual(seen, [24.0, 24.123456789])
        rng.assert_called_once_with(123456)

    def test_Q4_Q5_all_signals_final_round_and_signed_zero_JSON(self):
        normal = dict(zip(m.SIGNALS, (0.0078125, 0.0234375, -0.0000004, 2.0000006, -0.0000004)))
        values, quality = m.overlay_sample(normal, "motor-01", 0, [], {})
        self.assertEqual(list(values.values()), [0.007812, 0.023438, -0.0, 2.000001, -0.0])
        self.assertEqual(math.copysign(1, values["load_proxy"]), -1)
        self.assertIn(b'"load_proxy":-0.0', v.canonical_json(values))
        self.assertTrue(all(q == "ok" for q in quality.values()))

    def test_unrounded_stuck_capture_and_fixed_overlay_order(self):
        events = v.event_inventory(identity())
        # Deliberately overlapping arithmetic-only fixture proves ordering, not
        # a second allowed campaign schedule.
        for e in events[:4]:
            e.update(start_sample=7200, end_sample=7203, enabled=True)
        normal, stuck = dict.fromkeys(m.SIGNALS, 1.0000014), {}
        values, qualities = m.overlay_sample(normal, "motor-01", 7200, list(reversed(events[:4])), stuck)
        self.assertEqual(next(iter(stuck.values())), 1.0000014+0.55*35)
        self.assertEqual(values["load_proxy"], round(1.0000014+0.55*35, 6))
        self.assertEqual(qualities["motor_temperature"], "missing")
        normal["load_proxy"] = 70
        again, _ = m.overlay_sample(normal, "motor-01", 7201, events[:4], stuck)
        self.assertEqual(again["load_proxy"], values["load_proxy"])

    def test_nonfinite_normal_not_hidden_by_quality_or_bool(self):
        events = v.event_inventory(identity(stratum="quality-stress"))
        for value in (True, float("nan"), float("inf"), None):
            normal = dict.fromkeys(m.SIGNALS, 1.0); normal["motor_temperature"] = value
            with self.subTest(value=value), self.assertRaises(v.V03ValidationError):
                m.overlay_sample(normal, "motor-01", events[2]["start_sample"], events, {})

    def test_single_random_stream_equipment_order_and_unrounded_carry(self):
        calls, token = [], object()
        def base(kind, mode, previous, rng):
            self.assertIs(rng, token)
            calls.append((kind, mode, previous))
            return dict.fromkeys(m.SIGNALS, 24.123456789), 24.123456789
        with patch.object(m.random, "Random", return_value=token) as random_factory, patch.object(m, "_base_values", new=base):
            rows = list(m.normal_stream(123456))
        random_factory.assert_called_once_with(123456)
        self.assertEqual(len(rows), 18000)
        self.assertEqual([calls[i][0] for i in (0, 8999, 9000, 17999)], ["motor", "motor", "conveyor", "conveyor"])
        self.assertEqual([calls[i][2] for i in (0, 1, 9000, 9001)], [24.0, 24.123456789, 24.0, 24.123456789])
        self.assertEqual(calls[30][1], "startup")

    def test_full_materialized_quality_coordinates_and_overlap(self):
        core, stress = [data.files()["observations.jsonl"].splitlines() for data in self.pair]
        changed = []
        for index, (a, b) in enumerate(zip(core, stress)):
            if a != b:
                changed.append(index)
        events = v.event_inventory(identity(stratum="quality-stress"))
        expected = sorted(s for e in events if e["event_class"] == "data_quality" for s in range(e["start_sample"], e["end_sample"]))
        self.assertEqual(changed, expected)
        self.assertEqual(len(changed), 30)
        sensor, quality = [next(e for e in events if e["cycle"] == 9 and e["event_class"] == kind) for kind in ("sensor", "data_quality")]
        self.assertEqual(quality["start_sample"], sensor["start_sample"]+1)

    def test_metadata_and_hash_coordinated_tamper_rejected(self):
        files = self.pair[0].files()
        for name in ("event-ledger.jsonl", "events.jsonl", "quality-mask.jsonl", "targets.json", "split-manifest.json", "fingerprint.json"):
            bad = dict(files); bad[name] = b"{}\n"
            with self.subTest(name=name), self.assertRaises(v.V03ValidationError):
                m.validate_dataset(identity(), bad)

    def test_missing_and_reordered_materialized_rows_rejected(self):
        rows = self.pair[0].files()["observations.jsonl"].splitlines(keepends=True)
        for changed in (rows[:-1], [rows[1], rows[0], *rows[2:]]):
            files = self.pair[0].files(); files["observations.jsonl"] = b"".join(changed)
            with self.assertRaises(v.V03ValidationError): m.validate_dataset(identity(), files)

    def test_pair_rejects_different_nonquality_inputs_even_with_fresh_hashes(self):
        data = self.pair[1]
        files = data.files()
        # Rebuild the entire metadata/fingerprint from forged observation bytes.
        rows = files["observations.jsonl"].splitlines(keepends=True)
        row = v.strict_json(rows[100]); row["signals"]["motor_current"]["value"] += 1.0
        rows[100] = m.json_bytes(row)
        masks = files["quality-mask.jsonl"].splitlines(keepends=True)
        ident = v.strict_json(data.identity_json)
        forged = m._dataset(ident, rows, masks, v.event_inventory(ident))
        m.validate_dataset(ident, forged.files())
        with self.assertRaisesRegex(v.V03ValidationError, "paired non-quality"):
            m.validate_pair(self.pair[0], forged)

    def test_short_extra_or_unordered_normal_stream_rejected(self):
        values = dict.fromkeys(m.SIGNALS, 1.0)
        for stream in ([], [("motor-01", 1, values)], [("conveyor-01", 0, values)], [("motor-01", True, values)]):
            with self.assertRaises(v.V03ValidationError): m._build_pair(identity(), stream)

    def test_immutable_payload_inventory_and_bad_registered_identity(self):
        with self.assertRaises(v.V03ValidationError): replace(self.pair[0], entries=self.pair[0].entries[::-1])
        for key, value in (("seed", 42), ("seed", True), ("layout", 12), ("role", "fake")):
            bad = identity(); bad[key] = value
            with patch.object(m, "normal_stream", side_effect=AssertionError("PRNG used")), self.assertRaises(v.V03ValidationError):
                m.materialize_pair(bad)


class FixtureLifetimeTests(unittest.TestCase):
    def test_materializer_class_fixture_released_without_GC(self):
        class Owner(MaterializerTests):
            pass
        Owner.setUpClass()
        reference = weakref.ref(Owner.pair[0])
        try:
            Owner.doClassCleanups()
            self.assertFalse("pair" in Owner.__dict__, "completed class retains paired dataset bytes")
            self.assertIsNone(reference())
        finally:
            if "pair" in Owner.__dict__:
                del Owner.pair


if __name__ == "__main__":
    unittest.main()
