import copy
import datetime as dt
import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import demand_rolling_ridge as rolling

requires_torch = unittest.skipUnless(importlib.util.find_spec('torch'), 'torch is not installed')


def packet(store, origin, x=1.):
    raw = [[1., x]+[0.]*70 for _ in range(14)]
    return {'store': store, 'origin': str(origin), 'scale': 1., 'raw': raw, 'baseline': [10.]*14,
            'actual': [10.+x]*14, 'complete_label': True}


def pool(origin):
    return [packet(s, origin-dt.timedelta(days=300-14*k), float(k)) for s in rolling.FIT for k in range(14)]


class ForbiddenTargets(dict):
    def __getitem__(self, key):
        if key in ('actual', 'raw', 'complete_label'):
            raise AssertionError('uncompleted or foreign target payload accessed')
        return super().__getitem__(key)


class RollingRidgeChecks(unittest.TestCase):
    def test_metadata_rejection_precedes_target_and_mask(self):
        origin = dt.date(2014, 7, 1)
        rows = [ForbiddenTargets({'store': s, 'origin': str(day)}) for s, day in
                ((6, origin), (7, origin+dt.timedelta(days=1)), (6, origin-dt.timedelta(days=13)),
                 (6, origin-dt.timedelta(days=366)))]
        rows.append(ForbiddenTargets({'store': 31, 'origin': 'INVALID'}))
        self.assertEqual(rolling.select_pool(rows, origin), [])

    def test_inclusive_365_and_strict_label_completion(self):
        origin = dt.date(2014, 7, 1)
        first = packet(6, origin-dt.timedelta(days=365))
        latest = packet(7, origin-dt.timedelta(days=14))
        incomplete = packet(6, origin-dt.timedelta(days=20)); incomplete['complete_label'] = False
        selected = rolling.select_pool([first, latest, incomplete], origin)
        self.assertEqual(selected, [first, latest])

    @requires_torch
    def test_current_and_other_store_future_poison_does_not_change_fit(self):
        origin = dt.date(2014, 7, 1)
        training = pool(origin)
        current = [packet(s, origin, 2.) for s in rolling.FIT]
        future = [packet(s, origin+dt.timedelta(days=14), 1e6) for s in rolling.FIT]
        clean, journal, _ = rolling.roll_period(training+current+future, current)
        poisoned = copy.deepcopy(current+future)
        for p in poisoned:
            p['actual'] = [999999.]*14
        changed, changed_journal, _ = rolling.roll_period(training+poisoned, current)
        self.assertEqual(clean, changed)
        self.assertEqual(journal, changed_journal)
        self.assertEqual(journal[0]['pool_windows'], 140)
        self.assertAlmostEqual(journal[0]['state']['mean'][1], 6.5)
        self.assertLess(journal[0]['last_label_day'], str(origin))

    @requires_torch
    def test_current_features_do_not_change_training_normalization(self):
        origin = dt.date(2014, 7, 1)
        current = [packet(s, origin, 2.) for s in rolling.FIT]
        _, journal, _ = rolling.roll_period(pool(origin), current)
        changed = [packet(s, origin, 1000.) for s in rolling.FIT]
        _, other, _ = rolling.roll_period(pool(origin), changed)
        self.assertEqual(journal[0]['state'], other[0]['state'])

    @requires_torch
    def test_cold_pool_falls_back_and_does_not_mutate_input_pool(self):
        origin = dt.date(2014, 7, 1)
        initial = []
        current = [packet(s, origin) for s in rolling.FIT]
        forecasts, journal, later = rolling.roll_period(initial, current)
        self.assertEqual(initial, [])
        self.assertEqual(len(later), 10)
        self.assertTrue(journal[0]['fallback'])
        self.assertIsNone(journal[0]['state'])
        self.assertTrue(all(r['rolling_raw'] == r['baseline'] for r in forecasts))

    @requires_torch
    def test_unequal_fixed_store_support_and_duplicate_packets_rejected(self):
        origin = dt.date(2014, 7, 1)
        training = pool(origin)+[packet(6, origin-dt.timedelta(days=320))]
        current = [packet(s, origin) for s in rolling.FIT]
        with self.assertRaisesRegex(ValueError, 'unequal'):
            rolling.roll_period(training, current)
        with self.assertRaisesRegex(ValueError, 'duplicate eligible'):
            rolling.select_pool(pool(origin)+[pool(origin)[0]], origin)
        with self.assertRaisesRegex(ValueError, 'duplicate forecast'):
            rolling.roll_period([], current+[current[0]])

    def test_choice_tie_prefers_existing_reference_and_preserves_order(self):
        scores = {m: {'joint': 1.} for m in rolling.ORDER}
        self.assertEqual(rolling.choose(scores), 'baseline')
        scores['incumbent']['joint'] = .9
        scores['rolling_calibrated']['joint'] = .9-1e-13
        self.assertEqual(rolling.choose(scores), 'incumbent')
        scores['rolling_calibrated']['joint'] = .8
        self.assertEqual(rolling.choose(scores), 'rolling_calibrated')


if __name__ == '__main__':
    unittest.main(verbosity=2)
