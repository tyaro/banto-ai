from pathlib import Path
import datetime as dt
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from demand_shared_residual import past_input, observed_target, fit, predict


class SharedResidualChecks(unittest.TestCase):
    def test_past_only_getter(self):
        origin = dt.date(2015, 6, 1)
        class PastOnly(dict):
            def get(self, day, default=None):
                if day >= origin:
                    raise AssertionError('target accessed by input')
                return super().get(day, default)
        history = PastOnly({origin-dt.timedelta(days=k): 10. for k in range(1, 57)})
        value = past_input(history, origin, 10.)
        self.assertTrue(value['available'])
        self.assertEqual((value['baseline'], value['x']), (140., 0.))

    def test_equal_store_weight_and_ridge(self):
        rows = [{'store': s, 'origin': str(dt.date(2015, 1, 1)+dt.timedelta(days=k)),
                 'x': float(k % 2), 'y': float(1+2*(k % 2))} for s, n in ((1, 10), (2, 20)) for k in range(n)]
        model = fit(rows, (1, 2))
        self.assertEqual(model['store_weight_sums'], {1: 15., 2: 15.})
        self.assertEqual(model['weight_sum'], 30.)
        self.assertAlmostEqual(model['intercept'], 2.)
        self.assertAlmostEqual(model['slope'], 30/31)
        self.assertAlmostEqual(model['scale'], .5)

    def test_validation_and_future_fit_rejected_before_values(self):
        poison = object()
        for row in ({'store': 3, 'origin': '2015-01-01', 'x': poison, 'y': poison},
                    {'store': 1, 'origin': '2016-01-01', 'x': poison, 'y': poison}):
            with self.assertRaisesRegex(ValueError, 'outside training'):
                fit([row], (1, 2))

    def test_zero_missing_and_fallback(self):
        origin = dt.date(2015, 6, 1)
        history = {origin-dt.timedelta(days=k): 0. for k in range(1, 57)}
        value = past_input(history, origin, 1.)
        self.assertEqual((value['baseline'], value['x'], value['context_positive_days']), (0., 0., 0))
        history[origin-dt.timedelta(days=1)] = None
        value = past_input(history, origin, 1.)
        self.assertTrue(value['available']);self.assertIsNone(value['x'])
        model = {'center': 1., 'scale': 1., 'intercept': -.5, 'slope': 2.}
        result = predict(model, 14., 1., value['x'])
        self.assertEqual((result['intercept'], result['shared']), (7., 7.))
        self.assertEqual(predict(model, 0., 1., None)['shared'], 0.)

    def test_missing_target_keeps_null(self):
        origin = dt.date(2015, 6, 1)
        history = {origin+dt.timedelta(days=k): 0. for k in range(14)}
        self.assertEqual(observed_target(history, origin)['actual_total'], 0.)
        history[origin+dt.timedelta(days=3)] = None
        target = observed_target(history, origin)
        self.assertFalse(target['available']);self.assertIsNone(target['actual_total'])
        self.assertEqual(target['observed_days'], 13)


if __name__ == '__main__':
    unittest.main()
