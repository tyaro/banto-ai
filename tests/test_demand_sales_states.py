import datetime as dt
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from demand_sales_states import observation_state, fit_occurrence, compose_sales, operating_statuses

DAY = dt.date(2014, 6, 1)
ISSUE = dt.datetime(2014, 6, 1, tzinfo=dt.timezone.utc)


def record(day, status, **kwargs):
    result = {'record_id': str(day), 'known_at': ISSUE, 'date': day,
              'stores': [6], 'status': status, 'cancelled': False}
    result.update(kwargs)
    return result


def labels():
    return [{'store': 6, 'date': str(DAY-dt.timedelta(days=k+1)), 'quantity': 0. if k < 7 else 20.,
             'observed': True, 'operating_status': 'open'} for k in range(14)]


class NeverGet:
    def get(self, day):
        raise AssertionError('unsupported/closed branch must not read conditional quantity')


class SalesStateChecks(unittest.TestCase):
    def test_observation_zero_causes_and_missing_remain_distinct(self):
        for status in ('open', 'closed', 'unknown'):
            self.assertEqual(observation_state(status, 0., True), status+'_zero')
            self.assertEqual(observation_state(status, None, False), 'missing')
        self.assertEqual(observation_state('unknown', 10., True), 'unknown_positive')

    def test_closed_positive_is_inconsistent_not_clipped(self):
        with self.assertRaisesRegex(ValueError, 'contradicts'):
            observation_state('closed', 10., True)
        with self.assertRaises(ValueError):
            observation_state('open', 0., False)

    def test_probability_excludes_missing_and_closed_zeros(self):
        rows = labels()+[{'store': 6, 'date': '2014-04-01', 'quantity': None,
                         'observed': False, 'operating_status': 'closed'},
                        {'store': 6, 'date': '2014-04-02', 'quantity': 0.,
                         'observed': True, 'operating_status': 'closed'}]
        state = fit_occurrence(rows)
        self.assertEqual(state['per_store']['6']['open']['p_positive'], .5)
        self.assertEqual(state['per_store']['6']['mixed']['observed'], 14)
        self.assertEqual(state['observation_classes']['missing'], 1)
        self.assertEqual(state['observation_classes']['closed_zero'], 1)

    def test_unknown_zero_not_claimed_as_open_or_closed(self):
        rows = [{**r, 'operating_status': 'unknown'} for r in labels()]
        state = fit_occurrence(rows)
        self.assertEqual(state['per_store']['6']['mixed']['p_positive'], .5)
        self.assertEqual(state['per_store']['6']['open']['observed'], 0)
        self.assertEqual(state['observation_classes']['unknown_zero'], 7)

    def test_no_zero_class_keeps_unestimated_probability_null(self):
        state = fit_occurrence([{**r, 'quantity': 20.} for r in labels()])
        self.assertIsNone(state['per_store']['6']['open']['p_positive'])
        result = compose_sales(NeverGet(), {DAY: 12.}, [record(DAY, 'open')], [DAY], ISSUE, 6,
                               state, closed_implies_zero=True)
        self.assertEqual(result['total_sales_mean'], 12.)
        self.assertIsNone(result['daily'][0]['p_positive'])
        self.assertTrue(result['daily'][0]['reference_fallback'])

    def test_fit_scope_rejected_before_payload_and_duplicates_fail(self):
        class Forbidden(dict):
            def __getitem__(self, key):
                if key in ('operating_status', 'quantity', 'observed'):
                    raise AssertionError('unselected training payload accessed')
                return super().__getitem__(key)
        rejected = [Forbidden(store=31, date='POISON'), Forbidden(store=6, date='2014-07-01'),
                    Forbidden(store=6, date='2015-01-01')]
        self.assertEqual(fit_occurrence(rejected)['eligible_distinct_labels'], 0)
        with self.assertRaises(ValueError):
            fit_occurrence(labels()+labels()[:1])

    def test_confirmed_closed_bypasses_both_getters_and_positive_blend_floor(self):
        state = fit_occurrence([])
        result = compose_sales(NeverGet(), NeverGet(), [record(DAY, 'closed')], [DAY], ISSUE, 6,
                               state, closed_implies_zero=True)
        self.assertEqual(result['daily'][0]['sales_mean'], 0.)
        self.assertEqual(result['total_sales_mean'], 0.)

    def test_open_and_unknown_probability_scopes_and_holiday_not_closure(self):
        state = fit_occurrence(labels())
        result = compose_sales({DAY: 20.}, NeverGet(), [record(DAY, 'open')], [DAY], ISSUE, 6,
                               state, closed_implies_zero=True)
        self.assertEqual(result['total_sales_mean'], 10.)
        self.assertEqual(result['daily'][0]['probability_scope'], 'open')
        holiday = dt.date(2014, 12, 25)
        unknown = compose_sales({holiday: 20.}, NeverGet(), [], [holiday], ISSUE, 6, state, closed_implies_zero=True)
        self.assertEqual(unknown['total_sales_mean'], 10.)
        self.assertEqual(unknown['daily'][0]['operating_status'], 'unknown')
        self.assertEqual(unknown['daily'][0]['probability_scope'], 'mixed')
        self.assertFalse(unknown['holiday_implies_closed'])

    def test_unavailable_future_versions_not_accessed_and_latest_unknown_wins(self):
        class Future(dict):
            def __getitem__(self, key):
                if key not in ('record_id', 'known_at'):
                    raise AssertionError('unavailable operating payload accessed')
                return super().__getitem__(key)
        future = Future(record_id=str(DAY), known_at=ISSUE+dt.timedelta(days=1))
        statuses, excluded = operating_statuses([future], [DAY], ISSUE, 6)
        self.assertEqual(statuses[DAY], 'unknown')
        self.assertEqual(excluded[0]['reason'], 'not_yet_known')
        older = record(DAY, 'closed', known_at=ISSUE-dt.timedelta(days=1))
        statuses, _ = operating_statuses([older, record(DAY, 'unknown')], [DAY], ISSUE, 6)
        self.assertEqual(statuses[DAY], 'unknown')

    def test_no_closure_contract_has_no_partial_total_and_conflicts_fail(self):
        days = [DAY, DAY+dt.timedelta(days=1)]
        result = compose_sales(NeverGet(), {days[1]: 10.}, [record(DAY, 'closed')], days, ISSUE, 6,
                               fit_occurrence([]), closed_implies_zero=False)
        self.assertIsNone(result['daily'][0]['sales_mean'])
        self.assertIsNone(result['total_sales_mean'])
        with self.assertRaises(ValueError):
            operating_statuses([record(DAY, 'open'), record(DAY, 'closed', record_id='other')], [DAY], ISSUE, 6)


if __name__ == '__main__':
    unittest.main()
