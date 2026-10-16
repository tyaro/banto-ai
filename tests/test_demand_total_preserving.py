import copy
import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import demand_total_preserving as q


def levels(): return {str(k): {'value': .2} for k in range(1, 5)}
def row(store=6, origin='2014-03-26'):
    return {'store': store, 'origin': origin, 'scale': 10., 'matched_mean28': [10.]*14,
            'open_mean28': [10.]*14, 'open_mask': [True]*14, 'raw_prediction': [12.]+[10.]*12+[8.], 'actual': [10.]*14}
def policy():
    return {'quarter_levels': levels(), 'quarter_coefficients': {str(k): {m: {'alpha': .2 if k == 1 else .9} for m in q.ORDER} for k in range(1, 5)}}
def groups():
    v = {'quantity': {'macro': {'MSE': 1.}}, 'macro': {'total': 1., 'joint': 1.},
         'shortfall': {'macro': {'under': 2., 'over': 3.}},
         'total_invariance': {'max_total_absolute_difference': 0., 'max_window_under_increase': 0., 'max_window_over_increase': 0.}}
    return {g: {mode: {m: copy.deepcopy(v) for m in q.ORDER} for mode in ('observed', 'assumed_missing_zero')}
            for g in ('normal_Q1', 'normal_Q2', 'normal_Q3', 'normal_Q4', 'newyear')}


class TotalPreservingChecks(unittest.TestCase):
    def test_simplex_known_solution_zero_and_closure(self):
        base = [1., 1.]+[0.]*12; mask = [True, True]+[False]*12
        self.assertEqual(q.project([3., -1.]+[99.]*12, base, mask), [2., 0.]+[0.]*12)
        self.assertEqual(q.project([5.]*14, [0.]*14, [False]*14), [0.]*14)
        with self.assertRaises(ValueError): q.project([float('nan')]*14, base, mask)

    def test_uniform_level_has_no_new_direction(self):
        base = [float(k) for k in range(1, 15)]
        self.assertEqual(q.project([v+4. for v in base], base, [True]*14), base)

    def test_common_origin_quarter_and_convex_total(self):
        r = row(); p = policy(); result = q.choices(r, p); projected = q.shapes(r, levels())
        for method in q.ORDER:
            self.assertAlmostEqual(math.fsum(result[method]), 140., places=10)
            for a, b, c in zip(result[method], r['matched_mean28'], projected[method]): self.assertAlmostEqual(a, .8*b+.2*c)
        p['quarter_coefficients']['1']['ridge_shape']['alpha'] = 0.
        self.assertEqual(q.choices(r, p)['ridge_shape'], r['matched_mean28'])

    def test_weekday_pooling_excludes_closed_day(self):
        r = row(origin='2015-01-01'); r['open_mask'][0] = False; r['matched_mean28'][0] = 0.; r['open_mean28'][0] = 0.; r['raw_prediction'][0] = 10000.
        projected = q.shapes(r, levels())
        expected = [0.]+[10.]*5+[9.,10.,10.,10.,10.,10.,10.,9.]
        self.assertEqual(projected['weekly_ridge_shape'], q.project(expected, r['matched_mean28'], r['open_mask']))
        self.assertEqual(projected['weekly_ridge_shape'][0], 0.)

    def test_projection_never_reads_actual(self):
        class Poison(dict):
            def __getitem__(self, key):
                if key == 'actual': raise AssertionError('future label accessed')
                return super().__getitem__(key)
        self.assertEqual(q.choices(Poison(row()), policy()), q.choices(row(), policy()))

    def test_calibration_equal_store_weights_and_missing_exclusion(self):
        rows = []
        for month in (1, 4, 7, 10):
            for s in q.FIT:
                r = row(s, f'2014-{month:02d}-15')
                if s == 6: r['actual'] = [12.]+[None]*13
                rows.append(r)
        c = q.calibrate(rows, {str(k): {'value': 0.} for k in range(1, 5)})
        self.assertAlmostEqual(c['quarter_coefficients']['1']['ridge_shape']['alpha'], .4375)
        self.assertEqual(c['quarter_coefficients']['1']['ridge_shape']['observed_quantity_per_store']['6'], 1)
        self.assertEqual(c['quarter_coefficients']['1']['level_shape']['alpha'], 0.)

    def test_normal_q1_harm_cannot_be_hidden_by_newyear_gain(self):
        g = groups()
        for mode in g['normal_Q1'].values(): mode['ridge_shape']['macro']['joint'] = .8; mode['ridge_shape']['quantity']['macro']['MSE'] = 1.1
        for mode in g['newyear'].values(): mode['ridge_shape']['quantity']['macro']['MSE'] = .5
        self.assertEqual(q.choose(g)['selected_by_quarter']['1'], 'matched_mean28')

    def test_total_or_over_harm_rejected_and_tie_baseline(self):
        g = groups(); self.assertTrue(all(m == 'matched_mean28' for m in q.choose(g)['selected_by_quarter'].values()))
        for mode in g['normal_Q2'].values(): mode['ridge_shape']['macro']['joint'] = .8; mode['ridge_shape']['shortfall']['macro']['over'] = 3.1
        self.assertEqual(q.choose(g)['selected_by_quarter']['2'], 'matched_mean28')
        g['normal_Q3']['observed']['weekly_ridge_shape']['macro']['total'] = 1.01
        self.assertFalse(q.choose(g)['eligibility']['3']['weekly_ridge_shape']['eligible'])

    def test_both_sided_total_error_identity_for_any_label(self):
        r = row(); outputs = q.choices(r, policy()); total = math.fsum(r['matched_mean28'])
        for values in outputs.values():
            for actual in (0., 80., total, 150., 1000.):
                self.assertAlmostEqual(max(actual-math.fsum(values), 0.), max(actual-total, 0.), places=9)
                self.assertAlmostEqual(max(math.fsum(values)-actual, 0.), max(total-actual, 0.), places=9)


if __name__ == '__main__': unittest.main()
