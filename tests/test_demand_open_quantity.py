import datetime as dt
import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import demand_open_quantity as quantity

requires_torch = unittest.skipUnless(importlib.util.find_spec('torch'), 'torch is not installed')


class OpenQuantityChecks(unittest.TestCase):
    def test_open_average_excludes_closure_and_missing_but_retains_other_zero(self):
        origin = dt.date(2015, 1, 13)
        history = {origin-dt.timedelta(days=k): 10. for k in range(1, 57)}
        history[dt.date(2015, 1, 1)] = 0.
        history.pop(dt.date(2014, 12, 25))
        history[dt.date(2015, 1, 8)] = 0.  # A nonclosure sales zero remains an observation.
        x = quantity.inputs(history, 6, origin, 1., [True]*56, {'01-01', '12-25'})
        self.assertEqual(x['weekday_quantity_counts'][3], 2)
        self.assertEqual(x['open_mean28'][2], 5.)
        self.assertEqual(x['past_original_quantity'][44], 0.)
        self.assertTrue(x['past_original_observed'][44])
        self.assertFalse(x['past_quantity_usable'][44])
        self.assertEqual(history[dt.date(2015, 1, 1)], 0.)

    def test_future_and_origin_quantity_never_accessed(self):
        origin = dt.date(2014, 7, 1)
        class Guard(dict):
            def get(self, day):
                if day >= origin:
                    raise AssertionError('future quantity read')
                return super().get(day)
        history = Guard({origin-dt.timedelta(days=k): 10. for k in range(1, 57)})
        x = quantity.inputs(history, 6, origin, 1., [True]*56, {'01-01', '12-25'})
        self.assertEqual(x['open_mean28'], [10.]*14)
        with self.assertRaises(ValueError):
            quantity.QuantityPast(quantity.PastOnly(history, origin), {'07-01'}).get(origin)

    def test_two_weekday_observations_and_reasoned_fallback(self):
        origin = dt.date(2014, 7, 1)
        history = {origin-dt.timedelta(days=k): 10. for k in range(1, 57)}
        weekdays = [str(d)[5:] for d in history if d >= origin-dt.timedelta(days=28) and d.weekday() == origin.weekday()]
        x = quantity.inputs(history, 6, origin, 1., [True]*56, set(weekdays[:3]))
        self.assertIn(origin.weekday(), x['fallback_weekdays'])
        self.assertEqual(x['open_mean28'][0], x['matched_mean28'][0])

    @requires_torch
    def test_gate_in_fit_and_total_and_normalization_excludes_closed_feature_poison(self):
        import torch
        raw = torch.zeros((2, 14, 72), dtype=torch.float64); raw[:, :, 0] = 1.
        raw[:, :, 1] = torch.arange(14, dtype=torch.float64)
        mask = torch.ones((2, 14), dtype=torch.bool); mask[:, 0] = False
        base = mask.double()*10.; actual = mask.double()*12.; u = torch.ones(2, dtype=torch.float64)
        state = quantity.fit_gated(raw, base, actual, u, mask)
        poisoned = raw.clone(); poisoned[:, 0, :] = 999999.
        other = quantity.fit_gated(poisoned, base, actual, u, mask)
        for key in state:
            self.assertTrue(torch.equal(state[key], other[key]))
        p = quantity.predict_gated(raw, base, u, mask, state)
        self.assertTrue(torch.equal(p[:, 0], torch.zeros(2, dtype=torch.float64)))
        self.assertTrue(torch.allclose(p.sum(1), torch.full((2,), 156., dtype=torch.float64)))

    @requires_torch
    def test_level_delta_uses_joint_objective_and_never_increases_closed_days(self):
        import torch
        mask = torch.ones((1, 14), dtype=torch.bool); mask[0, 0] = False
        base = mask.double()*10.; actual = mask.double()*12.; u = torch.ones(1, dtype=torch.float64)
        state = quantity.level_delta(base, actual, u, mask)
        self.assertAlmostEqual(state['delta'], 2.)
        self.assertEqual((base+state['delta']*u[:, None]*mask)[0, 0].item(), 0.)
        self.assertEqual(quantity.level_delta(base, mask.double()*8., u, mask)['delta'], 0.)

    def test_calendar_support_checks_fit_cutoff_before_mask_and_enables_post_newyear(self):
        from demand_public_calendar import fit_support
        class Forbidden:
            def get(self, key):
                raise AssertionError('future support mask read')
        with self.assertRaises(ValueError):
            fit_support([(6, dt.date(2014, 7, 1))], Forbidden(), cutoff=dt.date(2014, 7, 1))
        origin = dt.date(2014, 1, 1)
        mask = {(6, origin+dt.timedelta(days=j)): j > 0 for j in range(14)}
        result = fit_support([(6, origin)], mask, cutoff=dt.date(2014, 7, 1))
        flags = {(r['kind'], r['relative_day']): r['enabled'] for r in result['channels']}
        self.assertFalse(flags['01-01', 0])
        self.assertTrue(flags['01-01', 1])

    def test_fixed_finite_selection_ties_and_validation(self):
        scores = {name: {'joint': 1.} for name in quantity.ORDER}
        self.assertEqual(quantity.choose(scores), 'matched_mean28')
        scores['gated_ridge']['joint'] = .8
        self.assertEqual(quantity.choose(scores), 'gated_ridge')
        with self.assertRaises(ValueError):
            quantity.choose({'gated_ridge': {'joint': .8}})

    def test_closed_future_day_remains_zero_for_both_baselines(self):
        origin = dt.date(2014, 1, 1)
        history = {origin-dt.timedelta(days=k): 10. for k in range(1, 57)}
        x = quantity.inputs(history, 6, origin, 1., [True]*56, {'01-01', '12-25'})
        self.assertFalse(x['open_mask'][0])
        self.assertEqual(x['matched_mean28'][0], 0.)
        self.assertEqual(x['open_mean28'][0], 0.)


if __name__ == '__main__':
    unittest.main()
