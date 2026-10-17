"""Small invented cases check input timing, not retail performance."""
import datetime as dt
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from demand_plans import promotion_features


class DemandPlanTests(unittest.TestCase):
    date = dt.date(2020, 2, 10)
    series = 'synthetic/store-1/food-family'

    def snapshot(self, count=5, stamp='2020-02-01T00:00:00Z', status='known', revision='r1'):
        return {'series_id': self.series, 'target_date': str(self.date), 'available_at': stamp,
            'onpromotion': count, 'status': status, 'source_kind': 'planned', 'scope': 'family_total',
            'source_id': 'synthetic-mechanism-fixture', 'revision_id': revision}

    def select(self, rows, stamp='2020-02-03T00:00:00+00:00', dates=None):
        return promotion_features(rows, series_id=self.series, issue_time=dt.datetime.fromisoformat(stamp),
                                  target_dates=dates or [self.date])

    def test_cancellation_is_selected_only_after_it_is_known(self):
        rows = [self.snapshot(), self.snapshot(0, '2020-02-04T00:00:00Z', 'cancelled', 'r2')]
        self.assertEqual(self.select(rows)[0]['onpromotion'], 5)
        selected = self.select(rows, '2020-02-04T09:00:00+09:00')[0]
        self.assertEqual(selected['onpromotion'], 0)
        self.assertTrue(selected['known'])
        self.assertEqual(selected['revision_id'], 'r2')

    def test_explicit_zero_and_absence_have_different_masks(self):
        selected = self.select([self.snapshot(0)], dates=[self.date, self.date + dt.timedelta(days=1)])
        self.assertTrue(selected[0]['known'])
        self.assertEqual(selected[0]['onpromotion'], 0)
        self.assertFalse(selected[1]['known'])
        self.assertIsNone(selected[1]['onpromotion'])
        self.assertEqual(selected[1]['missing_reason'], 'no_available_snapshot')

    def test_newer_unknown_does_not_restore_an_old_known_plan(self):
        selected = self.select([self.snapshot(), self.snapshot(None, '2020-02-02T00:00:00Z', 'unknown', 'r2')])[0]
        self.assertFalse(selected['known'])
        self.assertIsNone(selected['onpromotion'])
        self.assertEqual(selected['revision_id'], 'r2')

    def test_unavailable_poison_payload_is_never_used(self):
        before = self.select([self.snapshot()])
        poison = self.snapshot(object(), '2020-02-04T00:00:00Z', 'bad-unavailable-status', 'r2')
        self.assertEqual(before, self.select([poison, self.snapshot()]))

    def test_realized_rows_and_incomplete_scope_are_refused(self):
        realized = self.snapshot();realized['source_kind'] = 'realized'
        with self.assertRaisesRegex(ValueError, 'realized promotion'):
            self.select([realized])
        event = self.snapshot(0, status='cancelled');event['scope'] = 'one_event'
        with self.assertRaisesRegex(ValueError, 'complete family-level'):
            self.select([event])

    def test_tied_revisions_cannot_be_resolved_by_input_order(self):
        with self.assertRaisesRegex(ValueError, 'ambiguous revisions'):
            self.select([self.snapshot(), self.snapshot(4, revision='r2')])

    def test_invalid_counts_and_unspecified_timezone_are_refused(self):
        for count in (-1, True, 1.5):
            with self.subTest(count=count), self.assertRaises(ValueError):
                self.select([self.snapshot(count)])
        with self.assertRaises(ValueError):
            self.select([self.snapshot(stamp='2020-02-01T00:00:00')])
        with self.assertRaises(ValueError):
            self.select([self.snapshot(2, status='cancelled')])


if __name__ == '__main__':
    unittest.main(verbosity=2)
