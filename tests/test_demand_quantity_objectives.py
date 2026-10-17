from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from demand_quantity_objectives import quantile, expected_metrics, decision_quantity, describe


class QuantityObjectiveChecks(unittest.TestCase):
    def test_mean_median_different_losses_and_bias(self):
        rows = [(20, 80), (100, 20)]
        median = quantile(rows, .5); self.assertEqual(median, 20)
        at_median = expected_metrics(rows, median); at_mean = expected_metrics(rows, 36)
        self.assertEqual(at_median['bias'], -16); self.assertEqual(at_mean['bias'], 0)
        self.assertEqual(at_median['expected_absolute_error'], 16)
        self.assertAlmostEqual(at_mean['expected_absolute_error'], 25.6)
        self.assertLess(at_mean['expected_squared_error'], at_median['expected_squared_error'])

    def test_means_add_but_medians_need_not(self):
        one_day = [(20, 60), (100, 40)]
        total = [(40, 36), (120, 48), (200, 16)]
        self.assertEqual(2*expected_metrics(one_day, 0)['mean'], expected_metrics(total, 0)['mean'])
        self.assertEqual(2*quantile(one_day, .5), 40); self.assertEqual(quantile(total, .5), 120)

    def test_daily_upper_quantiles_are_not_total_quantiles(self):
        one_day = [(20, 80), (100, 20)]; total = [(40, 64), (120, 32), (200, 4)]
        self.assertEqual(2*quantile(one_day, .9), 200); self.assertEqual(quantile(total, .9), 120)

    def test_three_quantiles_cannot_determine_mean(self):
        a = [(20, 20), (40, 35), (60, 40), (80, 5)]
        b = [(20, 20), (40, 35), (60, 40), (800, 5)]
        self.assertEqual([quantile(a, q) for q in (.1, .5, .9)], [quantile(b, q) for q in (.1, .5, .9)])
        self.assertEqual(expected_metrics(a, 0)['mean'], 46)
        self.assertEqual(expected_metrics(b, 0)['mean'], 82)
        self.assertGreater(expected_metrics(b, 0)['mean'], quantile(b, .9))

    def test_asymmetric_costs_and_missing_costs(self):
        rows = [(20, 80), (100, 20)]
        self.assertEqual(decision_quantity(rows, 1, 1)['quantity'], 20)
        self.assertEqual(decision_quantity(rows, 9, 1)['quantity'], 100)
        self.assertIsNone(decision_quantity(rows, None, 1)['quantity'])

    def test_zero_and_invalid_values(self):
        self.assertEqual(quantile([(0, 1)], .5), 0)
        self.assertIsNone(describe([])['mean'])
        self.assertAlmostEqual(describe([1, 2, 3])['std'], (2/3)**.5)
        for rows in ([(True, 1)], [(1, 0)], [(float('nan'), 1)], [(-1, 1)]):
            with self.assertRaises(ValueError):
                quantile(rows, .5)


if __name__ == '__main__':
    unittest.main()
