import datetime as dt
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import demand_newyear_evaluation as january
from demand_autonomous_mean import ORIGINS


def rows():
    return [{'store': s, 'origin': str(january.ORIGIN), 'scale': 1., 'baseline': [10.]*14,
             'candidate': [9.]*14, 'raw_rolling': [8.]*14, 'actual': [0.]+[10.]*13,
             'complete_label': True} for s in january.FIT]


class JanuaryEvaluationChecks(unittest.TestCase):
    def test_training_365_boundary_and_strict_label_end(self):
        origin = january.ORIGIN
        headers = [{'store': 6, 'origin': str(origin-dt.timedelta(days=k)), 'complete_label': True} for k in (366, 365, 14, 13, 0)]
        selected = january.select_pool(headers, origin)
        self.assertEqual([p['origin'] for p in selected], ['2014-01-01', '2014-12-18'])

    def test_future_current_foreign_packet_payload_rejected_first(self):
        class Forbidden(dict):
            def __getitem__(self, key):
                if key in ('complete_label', 'actual'):
                    raise AssertionError('unavailable label read')
                return super().__getitem__(key)
        headers = [Forbidden(store=6, origin='2015-01-01'), Forbidden(store=6, origin='2015-01-13'),
                   Forbidden(store=31, origin='INVALID')]
        self.assertEqual(january.select_pool(headers, january.ORIGIN), [])

    def test_current_label_poison_does_not_change_ridge_or_forecast(self):
        origin = january.ORIGIN
        training = [{'store': s, 'origin': str(origin-dt.timedelta(days=200-14*k)), 'scale': 1.,
                     'baseline': [10.]*14, 'raw': [[1., float(k)]+[0.]*70]*14,
                     'actual': [10.+k]*14, 'complete_label': True} for s in january.FIT for k in range(14)]
        current = [{'store': s, 'origin': str(origin), 'scale': 1., 'baseline': [10.]*14,
                    'raw': [[1., 2.]+[0.]*70]*14, 'actual': None, 'complete_label': False} for s in january.FIT]
        before, state, _ = january.roll_period(training, current)
        poison = [{**p, 'actual': [999999.]*14, 'complete_label': True} for p in current]
        after, other_state, _ = january.roll_period(training+poison, poison)
        self.assertEqual(before, after)
        self.assertEqual(state, other_state)

    def test_input_context_never_includes_origin_zero(self):
        past = january.PastOnly({january.ORIGIN-dt.timedelta(days=1): 10., january.ORIGIN: 0.}, january.ORIGIN)
        self.assertEqual(past.get(january.ORIGIN-dt.timedelta(days=1)), 10.)
        with self.assertRaises(ValueError):
            past.get(january.ORIGIN)

    def test_target_scope_before_quantity_and_missing_mask(self):
        class Forbidden(dict):
            def __getitem__(self, key):
                if key in ('sales', 'observed'):
                    raise AssertionError('out-of-scope quantity accessed')
                return super().__getitem__(key)
        self.assertIsNone(january.selected_label(Forbidden(store_nbr='31', date='INVALID')))
        self.assertIsNone(january.selected_label(Forbidden(store_nbr='6', date='2015-01-15')))
        zero = january.selected_label(dict(store_nbr='6', date='2015-01-01', sales='0', observed='1'))
        missing = january.selected_label(dict(store_nbr='6', date='2015-01-01', sales='', observed='0'))
        self.assertEqual(zero[-1], 0.)
        self.assertIsNone(missing[-1])
        self.assertEqual(january.observation_state('unknown', zero[-1], True), 'unknown_zero')

    def test_zero_only_wape_undefined_and_no_partial_total_subset(self):
        measured = january.evaluate(rows(), {s: 1. for s in january.FIT})
        zero = measured['daily_subsets']['zero']['candidate']['macro']
        self.assertEqual(zero['count'], 10)
        self.assertIsNone(zero['WAPE_percent'])
        self.assertEqual(zero['MAE'], 9.)
        self.assertEqual(zero['scaled_MSE'], 81.)
        self.assertEqual(measured['complete_totals'], 10)
        self.assertNotIn('total', zero)

    def test_exact_grid_duplicate_and_missing_total_handling(self):
        original = rows()
        with self.assertRaises(ValueError):
            january.evaluate(original[:-1]+original[:1], {s: 1. for s in january.FIT})
        original[0]['actual'][1] = None; original[0]['complete_label'] = False
        result = january.evaluate(original, {s: 1. for s in january.FIT})
        self.assertEqual(result['complete_totals'], 9)
        self.assertEqual(result['observed_daily'], 139)
        self.assertIsNone(result['per_store'][str(january.FIT[0])]['candidate']['total'])
        self.assertIsNone(result['improved_stores'])
        self.assertIsNone(result['improvement_percent'])

    def test_new_year_window_is_separate_and_twenty_store_days_overlap(self):
        old = {(s, origin+dt.timedelta(days=j)) for s in january.FIT for origin in ORIGINS for j in range(14)}
        new = {(s, day) for s in january.FIT for day in january.DAYS}
        self.assertEqual(len(old & new), 20)
        self.assertTrue(all(day in (dt.date(2015, 1, 13), dt.date(2015, 1, 14)) for _, day in old & new))
        self.assertEqual(len(new), 140)


if __name__ == '__main__':
    unittest.main()
