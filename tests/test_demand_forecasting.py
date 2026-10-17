"""Representative checks for the new pilot, independent of public outcomes."""
import datetime as dt
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from demand_forecasting import forecast_pair, fit_ridge, metrics, predict_ridge


class DemandForecastingTests(unittest.TestCase):
    def setUp(self):
        self.origin = dt.date(2020, 2, 3)
        self.history = {self.origin - dt.timedelta(days=i): float(i) for i in range(1, 36)}

    def test_week_two_repeats_past_week_without_actuals(self):
        result = forecast_pair(self.history, self.origin)['forecasts']
        self.assertEqual([row['weekly_naive'] for row in result[:7]], [7., 6., 5., 4., 3., 2., 1.])
        self.assertEqual([row['weekly_naive'] for row in result[:7]], [row['weekly_naive'] for row in result[7:]])
        self.assertTrue(all(dt.date.fromisoformat(row['naive_source_date']) < self.origin for row in result))

    def test_missing_same_weekday_fallback_and_null(self):
        for i in (7, 14, 21):
            self.history[self.origin - dt.timedelta(days=i)] = None
        first = forecast_pair(self.history, self.origin)['forecasts'][0]
        self.assertEqual(first['weekly_naive'], 28.)
        self.history[self.origin - dt.timedelta(days=28)] = None
        first = forecast_pair(self.history, self.origin)['forecasts'][0]
        self.assertIsNone(first['weekly_naive'])
        self.assertIsNotNone(first['naive_missing_reason'])

    def test_observed_zero_is_not_skipped(self):
        self.history[self.origin - dt.timedelta(days=7)] = 0.
        first = forecast_pair(self.history, self.origin)['forecasts'][0]
        self.assertEqual(first['weekly_naive'], 0.)
        self.assertIsNone(first['naive_missing_reason'])

    def test_future_poison_does_not_change_fit_or_forecast(self):
        clean = forecast_pair(self.history, self.origin)
        self.history.update({self.origin + dt.timedelta(days=i): object() for i in range(21)})
        self.assertEqual(clean, forecast_pair(self.history, self.origin))
        self.assertEqual(clean['model']['fit_rows'], 35)
        self.assertLess(dt.date.fromisoformat(clean['model']['fit_end']), self.origin)

    def test_ridge_matches_independent_two_point_solution(self):
        model = fit_ridge([[0.], [2.]], [0., 2.])
        self.assertAlmostEqual(model['means'][0], 1.)
        self.assertAlmostEqual(model['scales'][0], 1.)
        self.assertAlmostEqual(model['intercept'], 1.)
        self.assertAlmostEqual(model['coefficients'][0], 2/3)
        self.assertAlmostEqual(predict_ridge(model, [2.])[0], 5/3)
        self.assertEqual(predict_ridge(model, [-10.]), (0., True))

    def test_unpenalized_constant_and_metrics_zero_cases(self):
        model = fit_ridge([[1., 2.], [1., 2.], [1., 2.]], [42., 42., 42.])
        self.assertEqual(predict_ridge(model, [1., 2.])[0], 42.)
        self.assertEqual(metrics([])['null_reason'], 'no_valid_pairs')
        zero = metrics([(2., 0.), (0., 0.)])
        self.assertEqual(zero['MAE'], 1.)
        self.assertIsNone(zero['WAPE'])
        self.assertIsNone(zero['Bias'])
        scored = metrics([(12., 10.), (4., 5.)])
        self.assertEqual(scored['MAE'], 1.5)
        self.assertEqual(scored['WAPE'], 20.)
        self.assertAlmostEqual(scored['Bias'], 100/15)
        with self.assertRaises(ValueError):
            metrics([(math.nan, 1.)])


if __name__ == '__main__':
    unittest.main(verbosity=2)
