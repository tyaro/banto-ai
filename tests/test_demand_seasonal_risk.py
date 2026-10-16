import copy
import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import demand_seasonal_risk as q


def row(store=6, origin='2014-01-15', raw=130., actual=110.):
    return {'store': store, 'origin': origin, 'scale': 1., 'matched_mean28': [100.]+[0.]*13,
            'raw_prediction': [raw]+[0.]*13, 'actual': [actual]+[0.]*13,
            'open_mask': [True]*14, 'past_original_quantity': [10.]*56}


def groups():
    v = {'macro': {'total': 1.}, 'shortfall': {'macro': {'under': 5., 'over': 5.}}}
    return {f'normal_Q{k}': {mode: {m: copy.deepcopy(v) for m in q.ORDER} for mode in ('observed', 'assumed_missing_zero')} for k in range(1, 5)}


class SeasonalRiskChecks(unittest.TestCase):
    def test_piecewise_crossing_and_two_sided_interval(self):
        samples = [{'e': -10., 'D': 30., 'weight': .5}, {'e': 10., 'D': -30., 'weight': .5}]
        for side in ('under', 'over'):
            b = q.side_bound(samples, side)
            self.assertAlmostEqual(b['upper'], 2/3)
            self.assertIn(1/3, b['breakpoints'])
            self.assertLess(b['initial_slope'], 0.)

    def test_upward_only_harm_has_zero_upper(self):
        samples = [{'e': 10., 'D': 5., 'weight': 1.}]
        self.assertEqual(q.side_bound(samples, 'over')['upper'], 0.)
        self.assertEqual(q.side_bound(samples, 'under')['upper'], 1.)

    def test_mse_optimum_and_complete_support(self):
        rows = []
        for month in (1, 4, 7, 10):
            for store in q.FIT:
                rows.extend([row(store, f'2014-{month:02d}-15'), row(store, f'2014-{month:02d}-29', 70., 90.)])
                rows.append(dict(row(store, f'2014-{month:02d}-01'), actual=[None]*14))
        policy, samples = q.calibrate(rows)
        for coefficients in policy['quarter_coefficients'].values():
            self.assertAlmostEqual(coefficients['signed_raw_blend']['alpha'], 1/3)
            self.assertEqual(coefficients['signed_raw_blend']['complete_windows'], 20)
            self.assertEqual(coefficients['matched_mean28']['alpha'], 0.)

    def test_recent14_ignores_old_context_and_distinguishes_zero_missing(self):
        r = row(); r['matched_mean28'] = [10.]*14
        r['past_original_quantity'] = [999999.]*42+[0.,0.]+[14.]*12
        p, support = q.recent14(r)
        self.assertEqual(support['weekday_counts'][2], 1)  # Jan1 assumed closure is excluded.
        self.assertEqual(p[0], 10.)  # Wed fallback, Jan8 only.
        self.assertEqual(p[1], 7.)   # Thu observed zero Jan2 is retained.
        r['past_original_quantity'][-13] = None
        p, support = q.recent14(r)
        self.assertEqual(p[1], 10.)

    def test_choices_do_not_read_targets_and_total_is_free(self):
        class Poison(dict):
            def __getitem__(self, key):
                if key == 'actual': raise AssertionError('label read during prediction')
                return super().__getitem__(key)
        policy = {'quarter_coefficients': {str(k): {m: {'alpha': .5} for m in q.ORDER} for k in range(1, 5)}}
        r = Poison(row())
        self.assertEqual(math.fsum(q.choices(r, policy)['signed_raw_blend']), 115.)
        r['raw_prediction'] = [70.]+[0.]*13
        self.assertEqual(math.fsum(q.choices(r, policy)['signed_raw_blend']), 85.)

    def test_foreign_future_metadata_precedes_actual(self):
        class Poison(dict):
            def __getitem__(self, key):
                if key == 'actual': raise AssertionError('excluded label read')
                return super().__getitem__(key)
        with self.assertRaises(ValueError): q.calibrate([Poison(store=31, origin='2014-01-15')])
        with self.assertRaises(ValueError): q.calibrate([Poison(store=6, origin='2015-01-01')])

    def test_mean_condition_can_allow_window_harm(self):
        # At alpha .5, errors [-10,10] become [5,-5]: an individual side grows,
        # while both averaged sides decline from 5 to 2.5.
        e = [-10.,10.]; d = [30.,-30.]; after = [a+.5*b for a,b in zip(e,d)]
        self.assertGreater(max(after[0],0),max(e[0],0))
        self.assertLess(sum(max(v,0) for v in after),sum(max(v,0) for v in e))
        self.assertLess(sum(max(-v,0) for v in after),sum(max(-v,0) for v in e))

    def test_side_harm_overrides_mse_gain_and_tie_baseline(self):
        g = groups(); self.assertTrue(all(v=='matched_mean28' for v in q.choose(g)['selected_by_quarter'].values()))
        for mode in g['normal_Q2'].values():
            mode['signed_raw_blend']['macro']['total'] = .8
            mode['signed_raw_blend']['shortfall']['macro']['over'] = 5.1
        self.assertEqual(q.choose(g)['selected_by_quarter']['2'],'matched_mean28')

    def test_newyear_reporting_is_not_selection(self):
        g = groups()
        for mode in g['normal_Q1'].values():mode['signed_raw_blend']['macro']['total'] = .8
        g['newyear'] = {'arbitrary': 'not a selection group'}
        self.assertEqual(q.choose(g)['selected_by_quarter']['1'], 'signed_raw_blend')
        self.assertFalse(q.choose(g)['newyear_used'])


if __name__ == '__main__': unittest.main()
