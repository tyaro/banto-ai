import datetime as dt
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import demand_recurring_closure as proxy


def history():
    return [{'store': s, 'date': str(dt.date(y, 1, 1)+dt.timedelta(days=k)), 'observed': True, 'quantity': 10.}
            for s in proxy.FIT for y in (2013, 2014) for k in range(365)]


def patterned():
    result = history()
    for r in result:
        if r['date'][5:] == '01-01':
            r['quantity'] = 0.
        if r['date'][5:] == '12-25':
            r.update(quantity=None, observed=False)
    return result


def forecast(origin='2015-12-15'):
    return {'store': 6, 'origin': origin, 'scale': 1., 'baseline': [10.]*14, 'candidate': [9.]*14}


class RecurringClosureChecks(unittest.TestCase):
    def test_two_year_pattern_keeps_zero_and_missing_support_separate(self):
        state = proxy.learn_pattern(patterned())
        self.assertEqual([p['month_day'] for p in state['patterns']], ['01-01', '12-25'])
        self.assertEqual(state['patterns'][0]['observed_zero'], 20)
        self.assertEqual(state['patterns'][1]['missing'], 20)
        self.assertFalse(state['confirmed_closed'])
        self.assertFalse(state['fitted_probability_one'])

    def test_future_and_foreign_payload_not_accessed(self):
        class Forbidden(dict):
            def __getitem__(self, key):
                if key in ('quantity', 'observed'):
                    raise AssertionError('excluded history payload read')
                return super().__getitem__(key)
        clean = proxy.learn_pattern(patterned())
        poisoned = proxy.learn_pattern(patterned()+[Forbidden(store=6, date='2015-01-01'), Forbidden(store=31, date='INVALID')])
        self.assertEqual(clean, poisoned)

    def test_full_store_year_support_and_duplicates_required(self):
        rows = patterned()
        for bad in (rows[:-1], rows+rows[:1]):
            with self.assertRaises(ValueError):
                proxy.learn_pattern(bad)

    def test_one_positive_prevents_shared_closure_assumption(self):
        rows = patterned()
        next(r for r in rows if r['store'] == 6 and r['date'] == '2014-01-01')['quantity'] = 1.
        state = proxy.learn_pattern(rows)
        self.assertEqual([p['month_day'] for p in state['patterns']], ['12-25'])

    def test_same_mask_on_baseline_and_candidate_and_no_label_reads(self):
        class NoLabel(dict):
            def __getitem__(self, key):
                if key in ('actual', 'complete_label'):
                    raise AssertionError('forecast accessed future labels')
                return super().__getitem__(key)
        row = NoLabel(forecast('2015-01-01'))
        result = proxy.apply_pattern(row, proxy.learn_pattern(patterned()))
        self.assertEqual(result['candidate'], [0.]+[9.]*13)
        self.assertEqual(result['baseline_proxy'], [0.]+[10.]*13)
        self.assertEqual(result['operating_status'], ['unknown']*14)
        self.assertEqual(row['candidate'][0], 9.)

    def test_missing_scenario_zero_keeps_raw_null_and_nonpattern_null(self):
        predicted = proxy.apply_pattern(forecast(), proxy.learn_pattern(patterned()))
        actual = [10.]*14; actual[10] = None; actual[1] = None
        labels = {(6, '2015-12-15'): {'actual': actual, 'complete_label': False}}
        observed, scenario, ledger = proxy.attach_scenarios([predicted], labels)
        self.assertIsNone(observed[0]['actual'][10])
        self.assertIsNone(scenario[0]['raw_actual'][10])
        self.assertEqual(scenario[0]['actual'][10], 0.)
        self.assertIsNone(scenario[0]['actual'][1])
        self.assertFalse(scenario[0]['complete_label'])
        self.assertEqual(sum(v['imputed_missing_zero'] for v in ledger), 1)
        self.assertIsNone(labels[6, '2015-12-15']['actual'][10])

    def test_positive_on_assumed_day_preserved_and_scored_as_contradiction(self):
        predicted = proxy.apply_pattern(forecast('2015-01-01'), proxy.learn_pattern(patterned()))
        actual = [20.]+[10.]*13
        observed, scenario, ledger = proxy.attach_scenarios([predicted], {(6, '2015-01-01'): {'actual': actual, 'complete_label': True}})
        self.assertEqual(observed[0]['actual'][0], 20.)
        self.assertEqual(scenario[0]['actual'][0], 20.)
        self.assertTrue(ledger[0]['assumption_contradicted_by_positive'])

    def test_fixed_cohort_support_and_zero_wape_without_fake_denominator(self):
        state = proxy.learn_pattern(patterned())
        forecasts = [proxy.apply_pattern({**forecast('2015-01-01'), 'store': s}, state) for s in proxy.FIT]
        labels = {(s, '2015-01-01'): {'actual': [0.]*14, 'complete_label': True} for s in proxy.FIT}
        observed, _, _ = proxy.attach_scenarios(forecasts, labels)
        result = proxy.score_cohort(observed, list(labels))
        self.assertEqual(result['scored_daily'], 140)
        self.assertIsNone(result['macro']['candidate']['daily_WAPE_percent'])
        with self.assertRaises(ValueError):
            proxy.score_cohort(observed[:-1], list(labels))


if __name__ == '__main__':
    unittest.main()
