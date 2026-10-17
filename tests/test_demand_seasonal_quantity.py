import datetime as dt
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import demand_seasonal_quantity as q


def row(origin='2014-01-15', actual=None):
    return {'store': 6, 'origin': origin, 'scale': 10., 'open_mean28': [10.]*14,
            'matched_mean28': [10.]*14, 'open_mask': [True]*14,
            'actual': [12.]*14 if actual is None else actual, 'raw_prediction': [12.]*14}


class SeasonalChecks(unittest.TestCase):
    def test_validation_covers_newyear_and_four_seasons(self):
        keys = q.validation_keys()
        self.assertEqual(len(set(keys)), 260)
        calibration = keys[10::20]; selection = keys[::20]
        self.assertEqual(selection[0], (6, '2014-01-01'))
        self.assertEqual({q.quarter(d) for s, d in calibration}, {1, 2, 3, 4})
        self.assertEqual({q.quarter(d) for s, d in selection}, {1, 2, 3, 4})
        self.assertLessEqual(max(d for s, d in keys), '2014-12-17')

    def test_scale_reads_2013_only(self):
        class Poison:
            def __float__(self): raise AssertionError('future value used')
        history = {s: {dt.date(2013, 1, 1)+dt.timedelta(days=k): 10. for k in range(365) if k != 358} for s in q.FIT}
        for values in history.values(): values[dt.date(2014, 1, 1)] = Poison()
        scales, evidence = q.scales_2013(history)
        self.assertTrue(all(v == 10. for v in scales.values()))
        self.assertTrue(all(v['observed'] == 364 for v in evidence.values()))

    def test_future_metadata_precedes_target_read(self):
        class Poison(dict):
            def __getitem__(self, key):
                if key == 'actual': raise AssertionError('excluded target read')
                return super().__getitem__(key)
        packets = [Poison(store=6, origin='2015-01-01'), Poison(store=31, origin='BAD')]
        self.assertEqual(q.complete_recent(packets, dt.date(2015, 1, 1)), [])

    def test_missing_past_not_imputed_and_boundary_exact(self):
        packets = [{'store': 6, 'origin': d, 'actual': a} for d, a in
                   [('2014-01-01', [0.]*14), ('2014-12-17', [0.]*13+[None]), ('2014-12-19', [1.]*14)]]
        self.assertEqual([p['origin'] for p in q.complete_recent(packets, dt.date(2015, 1, 1))], ['2014-01-01'])

    def test_missing_day_excluded_and_missing_total_excluded(self):
        rows = [row(), row(actual=[12.]*13+[None])]
        result = q.coefficient(rows, [[1.]*14]*2, 1.)
        self.assertEqual(result['daily_support'], 27)
        self.assertEqual(result['complete_totals'], 1)
        self.assertAlmostEqual(result['value'], .2)

    def test_safeguards_both_objectives(self):
        r = row(actual=[9.]+[12.]*13)
        d = [1.]+[0.]*13
        result = q.coefficient([r], [d], 1.)
        self.assertEqual(result['value'], 0.)  # Total positive covariance must not hide daily harm.
        self.assertLess(result['daily_covariance'], 0.)
        self.assertGreater(result['total_covariance'], 0.)

    def test_season_calibration_and_closure_gate(self):
        rows = [row(f'2014-{m:02d}-15') for m in (1, 4, 7, 10)]
        result = q.calibrate_seasons(rows)
        self.assertAlmostEqual(result['alpha']['value'], 1.)
        self.assertTrue(all(abs(v['value']-.2) < 1e-12 for v in result['quarter_levels'].values()))
        r = row(); r['open_mask'][0] = False; r['open_mean28'][0] = 0.; r['matched_mean28'][0] = 0.; r['raw_prediction'][0] = 0.
        for values in q.alternatives(r, result).values(): self.assertEqual(values[0], 0.)

    def test_fixed_candidate_tie_and_winner(self):
        scores = {m: {'joint': 1.} for m in q.ORDER}
        self.assertEqual(q.choose(scores), 'matched_mean28')
        scores['seasonal_level']['joint'] = .9
        self.assertEqual(q.choose(scores), 'seasonal_level')
        with self.assertRaises(ValueError): q.choose({'seasonal_level': {'joint': .9}})


if __name__ == '__main__': unittest.main()
