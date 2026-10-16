import copy
import datetime as dt
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import demand_prequential_bias as update


def row(origin, actual=9., store=6):
    return {'store': store, 'origin': str(origin), 'scale': 1., 'baseline': [10.]*14,
            'incumbent': [12.]*14, 'actual': [actual]*14}


class PrequentialBiasChecks(unittest.TestCase):
    def test_current_and_future_label_poison_does_not_change_current_prediction(self):
        first = dt.date(2014, 7, 1)
        rows = [row(first+dt.timedelta(days=14*k)) for k in range(3)]
        clean, traces, _ = update.run_period(rows)
        poisoned = copy.deepcopy(rows)
        poisoned[1]['actual'] = [999.]*14
        poisoned[2]['actual'] = [888.]*14
        changed, _, _ = update.run_period(poisoned)
        self.assertEqual(changed[:2], clean[:2])
        self.assertNotEqual(changed[2]['updated_incumbent'], clean[2]['updated_incumbent'])
        self.assertTrue(traces[0]['fallback'])
        self.assertEqual(clean[1]['updated_incumbent'], [9.]*14)

    def test_whole_horizon_completion_precedes_error_use(self):
        first = dt.date(2014, 7, 1)
        _, _, history = update.run_period([row(first)])
        for offset in (1, 7, 13):
            bias, support = update.bias_before(history, 6, first+dt.timedelta(days=offset))
            self.assertEqual(support['count'], 0)
            self.assertEqual(bias['incumbent_error'], 0.)
        bias, support = update.bias_before(history, 6, first+dt.timedelta(days=14))
        self.assertEqual(support['count'], 14)
        self.assertEqual(bias['incumbent_error'], 3.)

    def test_lookback_boundary_excludes_oldest_and_other_store_payload(self):
        origin = dt.date(2015, 3, 1)
        history = [{'store': 6, 'day': str(origin-dt.timedelta(days=k)),
                    'complete_by': str(origin-dt.timedelta(days=1)), 'baseline_error': 1., 'incumbent_error': 2.}
                   for k in range(43, 57)]
        history.append({'store': 31, 'day': 'INVALID', 'complete_by': 'INVALID',
                        'baseline_error': object(), 'incumbent_error': object()})
        bias, support = update.bias_before(history, 6, origin)
        self.assertEqual(support['count'], 14)
        self.assertEqual(bias['incumbent_error'], 2.)
        later = origin+dt.timedelta(days=1)
        bias, support = update.bias_before(history, 6, later)
        self.assertEqual(support['count'], 13)
        self.assertEqual(bias['incumbent_error'], 0.)

    def test_observed_zero_retained_missing_day_does_not_create_complete_support(self):
        first = dt.date(2014, 7, 1)
        value = row(first, actual=0.)
        value['actual'][3] = None
        _, _, history = update.run_period([value])
        self.assertEqual(len(history), 13)
        self.assertTrue(all(e['baseline_error'] == 10. for e in history))
        bias, support = update.bias_before(history, 6, first+dt.timedelta(days=14))
        self.assertTrue(support['fallback'])
        self.assertEqual(bias['baseline_error'], 0.)

    def test_warm_history_not_mutated_and_store_states_separate(self):
        first = dt.date(2014, 7, 1)
        _, _, warm = update.run_period([row(first)])
        prior = copy.deepcopy(warm)
        forecasts, traces, _ = update.run_period([row(first+dt.timedelta(days=14), store=7)], warm)
        self.assertEqual(warm, prior)
        self.assertEqual(forecasts[0]['updated_incumbent'], [12.]*14)
        self.assertTrue(traces[0]['fallback'])

    def test_tie_preserves_incumbent_and_fixed_method_order(self):
        scores = {m: {'joint': 1.} for m in update.METHODS}
        self.assertEqual(update.choose(scores), 'baseline')
        scores['incumbent']['joint'] = .9
        scores['updated_baseline']['joint'] = .9
        self.assertEqual(update.choose(scores), 'incumbent')
        scores['updated_incumbent']['joint'] = .8
        self.assertEqual(update.choose(scores), 'updated_incumbent')

    def test_duplicate_and_nonfinite_input_rejected_and_clip_nonnegative(self):
        first = dt.date(2014, 7, 1)
        with self.assertRaises(ValueError):
            update.run_period([row(first), row(first)])
        bad = row(first); bad['incumbent'][0] = float('nan')
        with self.assertRaises(ValueError):
            update.run_period([bad])
        prior = row(first, actual=0.)
        forecasts, _, _ = update.run_period([prior, row(first+dt.timedelta(days=14))])
        self.assertTrue(all(v >= 0 for v in forecasts[1]['updated_incumbent']))


if __name__ == '__main__':
    unittest.main(verbosity=2)
