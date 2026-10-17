import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import demand_shortfall_quantity as q


def policy():
    return {'alpha': {'value': .5}, 'quarter_levels': {str(k): {'value': .2} for k in range(1, 5)}}


def row(origin='2015-01-01'):
    return {'store': 6, 'origin': origin, 'scale': 10., 'matched_mean28': [0.]+[10.]*13,
            'open_mean28': [0.]+[8.,12.]*6+[10.], 'open_mask': [False]+[True]*13,
            'raw_prediction': [100.]+[5.,20.]*6+[10.]}


def scores():
    item = {'quantity': {'macro': {'MSE': 1.}}, 'macro': {'total': 1., 'joint': 1.},
            'shortfall': {'macro': {'under': 5.}, 'max_window_increase_over_matched': 0.}}
    return {g: {mode: {m: copy.deepcopy(item) for m in q.ORDER} for mode in ('observed', 'assumed_missing_zero')}
            for g in ('selection', 'newyear')}


class ShortfallChecks(unittest.TestCase):
    def test_pointwise_bound_protects_all_complete_label_values(self):
        r = row(); variants = q.choices(r, policy()); control = sum(r['matched_mean28'])
        for predicted in variants.values():
            self.assertTrue(all(p >= b for p, b in zip(predicted, r['matched_mean28'])))
            self.assertEqual(predicted[0], 0.)
            for actual in (0., 100., 150., 1000.):
                self.assertLessEqual(max(actual-sum(predicted), 0.), max(actual-control, 0.))

    def test_event_boundaries_and_ordinary_days(self):
        for day, expected in (('2014-12-25', False), ('2014-12-26', True), ('2014-12-31', True),
                              ('2015-01-01', False), ('2015-01-02', True), ('2015-01-14', True), ('2015-01-15', False)):
            self.assertEqual(q.near_newyear(day), expected)
        r = row('2015-03-01')
        self.assertEqual(q.choices(r, policy())['newyear_uplift'], r['matched_mean28'])

    def test_prediction_does_not_read_actual(self):
        class Poison(dict):
            def __getitem__(self, key):
                if key == 'actual': raise AssertionError('target read during prediction')
                return super().__getitem__(key)
        self.assertEqual(q.choices(Poison(row(), actual='POISON'), policy()), q.choices(row(), policy()))

    def test_negative_or_nonfinite_parameter_rejected(self):
        for value in (-.01, 1.01, float('nan')):
            p = policy(); p['alpha']['value'] = value
            with self.assertRaises(ValueError): q.choices(row(), p)
        r = row(); r['matched_mean28'][0] = 1.
        with self.assertRaises(ValueError): q.choices(r, policy())

    def test_upward_calibration_excludes_missing_total(self):
        r = {'scale': 10., 'matched_mean28': [10.]*14, 'raw_prediction': [12.]*14, 'actual': [11.]*14}
        incomplete = {**r, 'actual': [11.]*13+[None]}
        a = q.upward_alpha([r, incomplete])
        self.assertAlmostEqual(a['value'], .5)
        self.assertEqual(a['daily_support'], 27); self.assertEqual(a['complete_totals'], 1)

    def test_shortfall_harm_overrides_joint_gain(self):
        data = scores()
        for g in data.values():
            for m in g.values():
                m['upward_ridge']['macro']['joint'] = .8
                m['upward_ridge']['shortfall']['macro']['under'] = 5.1
        result = q.choose(data)
        self.assertEqual(result['selected'], 'matched_mean28')
        self.assertFalse(result['eligibility']['upward_ridge']['eligible'])

    def test_newyear_quantity_harm_overrides_ordinary_gain(self):
        data = scores()
        for mode in data['selection'].values(): mode['upward_ridge']['macro']['joint'] = .8
        data['newyear']['observed']['upward_ridge']['quantity']['macro']['MSE'] = 1.1
        result = q.choose(data)
        self.assertEqual(result['selected'], 'matched_mean28')
        self.assertIn('newyear/observed/quantity_MSE', result['eligibility']['upward_ridge']['reasons'])

    def test_fixed_tie_and_eligible_improvement(self):
        data = scores(); self.assertEqual(q.choose(data)['selected'], 'matched_mean28')
        for mode in data['selection'].values(): mode['newyear_uplift']['macro']['joint'] = .9
        self.assertEqual(q.choose(data)['selected'], 'newyear_uplift')
        data['selection']['assumed_missing_zero']['newyear_uplift']['macro']['total'] = 1.1
        self.assertEqual(q.choose(data)['selected'], 'matched_mean28')


if __name__ == '__main__': unittest.main()
