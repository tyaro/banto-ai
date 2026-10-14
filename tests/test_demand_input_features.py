import datetime as dt
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from demand_input_features import STORES, EVENTS, EVENT_KEYS, calendar, training_support, build_inputs


class InputFeatureChecks(unittest.TestCase):
    def fixture(self, origin=dt.date(2015, 6, 1)):
        h = {s: {origin-dt.timedelta(days=k): 100. if k % 2 else 200. for k in range(1, 57)} for s in STORES}
        support = {s: {key: 2 if key == '01-01' else 0 if key == '12-25' else 3 for key in EVENT_KEYS} for s in STORES}
        return h, origin, {s: 100. for s in STORES}, support

    def test_shifted_standardization_retains_distinct_statistics(self):
        h, d, u, n = self.fixture(); a = build_inputs(h, d, u, n)['stores'][5]
        for values in h.values():
            for day in values:
                values[day] += 1000.
        b = build_inputs(h, d, u, n)['stores'][5]
        za = [(v-a['context_mean'])/a['context_std'] for v in a['values']]
        zb = [(v-b['context_mean'])/b['context_std'] for v in b['values']]
        self.assertEqual(za, zb)
        self.assertAlmostEqual(a['context_statistics'][0], 1.5)
        self.assertAlmostEqual(b['context_statistics'][0], 11.5)
        self.assertAlmostEqual(a['context_statistics'][1], 1/3)
        self.assertAlmostEqual(b['context_statistics'][1], 1/23)

    def test_future_quantities_are_never_requested(self):
        h, d, u, n = self.fixture(dt.date(2015, 12, 20))
        class PastOnly(dict):
            def get(self, key, default=None):
                if key >= d:
                    raise AssertionError('future numeric lookup')
                return super().get(key, default)
        inputs = build_inputs({s: PastOnly(values) for s, values in h.items()}, d, u, n)
        self.assertTrue(inputs['available'])
        for row in inputs['stores'].values():
            christmas = row['future_event_metadata'][5]
            self.assertEqual(christmas['event'], '12-25')
            self.assertEqual(christmas['support_status'], 'no_observed_training_labels')
            self.assertFalse(christmas['operating_status_known'])

    def test_missing_and_zero_have_different_statistical_weight(self):
        h, d, u, n = self.fixture()
        for values in h.values():
            for day in values:
                values[day] = 10.
            values[d-dt.timedelta(days=1)] = None
            values[d-dt.timedelta(days=2)] = 0.
        row = build_inputs(h, d, u, n)['stores'][5]
        self.assertEqual(sum(row['observed']), 55)
        self.assertAlmostEqual(row['context_mean'], 540/55)
        self.assertTrue(row['observed'][-2]); self.assertFalse(row['observed'][-1])

    def test_all_zero_is_available_all_missing_is_not(self):
        h, d, u, n = self.fixture()
        for values in h.values():
            for day in values:
                values[day] = 0.
        zero = build_inputs(h, d, u, n)
        self.assertTrue(zero['available']); self.assertEqual(zero['stores'][5]['context_statistics'], [0., 0.])
        for values in h.values():
            for day in values:
                values[day] = None
        missing = build_inputs(h, d, u, n)
        self.assertFalse(missing['available']); self.assertIsNone(missing['stores'][5]['context_statistics'])
        self.assertEqual(missing['stores'][5]['reason'], 'no_observed_context')

    def test_event_channels_and_leap_year_calendar(self):
        for i, (m, d) in enumerate(EVENTS):
            value = calendar(dt.date(2015, m, d))
            self.assertEqual(len(value), 12)
            self.assertEqual(value[4:], [float(k == i) for k in range(8)])
        self.assertEqual(sum(calendar(dt.date(2016, 2, 29))[4:]), 0)
        self.assertNotEqual(calendar(dt.date(2015, 3, 1))[2:4], calendar(dt.date(2016, 3, 1))[2:4])

    def test_support_counts_distinct_days_and_skips_future_payload(self):
        rows = [{'date': '2014-01-01', 'store': 5, 'event': '01-01', 'observed': True, 'actual': 0,
                 'included_train_origins': ['2013-12-26', '2014-01-01']},
                {'date': '2015-12-25', 'store': 5, 'event': '12-25', 'observed': False, 'actual': None, 'included_train_origins': []},
                {'date': '2016-01-01', 'store': 'BOMB', 'actual': object()}]
        counts = training_support(rows, dt.date(2016, 1, 1))
        self.assertEqual(counts[5]['01-01'], 1); self.assertEqual(counts[5]['12-25'], 0)
        with self.assertRaises(ValueError):
            training_support([rows[0], rows[0]], dt.date(2016, 1, 1))

    def test_sparse_recent_support_and_invalid_observed_quantity(self):
        h, d, u, n = self.fixture()
        for values in h.values():
            for day in values:
                if (d-day).days <= 28:
                    values[day] = None
        row = build_inputs(h, d, u, n)['stores'][5]
        self.assertIsNotNone(row['context_statistics'])
        self.assertEqual(row['reason'], 'no_weekday_support')
        h[5][d-dt.timedelta(days=30)] = True
        with self.assertRaises(ValueError):
            build_inputs(h, d, u, n)


if __name__ == '__main__':
    unittest.main()
