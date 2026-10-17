"""New mechanism cases; do not repeat prior forecast or plan test suites."""
import datetime as dt
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from demand_recent_level import recent_forecasts


class RecentLevelTests(unittest.TestCase):
    origin = dt.date(2020, 2, 3)

    def history(self):
        return {self.origin-dt.timedelta(days=i): float(i) for i in range(1, 36)}

    def test_four_same_weekdays_have_hand_calculated_mean(self):
        rows = recent_forecasts(self.history(), self.origin)['predictions']
        self.assertEqual(rows[0]['weekday_mean_28'], 17.5)
        self.assertEqual(rows[0]['mean_support'], 4)
        self.assertEqual(rows[0]['mean_source_dates'], ['2020-01-06','2020-01-13','2020-01-20','2020-01-27'])
        self.assertEqual([r['weekday_mean_28'] for r in rows[:7]], [r['weekday_mean_28'] for r in rows[7:]])

    def test_missing_zero_and_window_boundary(self):
        history = self.history()
        for days, value in [(7, 0.), (14, None), (21, 4.), (28, 8.), (35, 9999.)]:
            history[self.origin-dt.timedelta(days=days)] = value
        first = recent_forecasts(history, self.origin, include_weekly_naive=True)['predictions'][0]
        self.assertEqual(first['weekday_mean_28'], 4.)
        self.assertEqual(first['mean_support'], 3)
        self.assertEqual(first['weekly_naive'], 0.)

    def test_no_weekday_history_has_explicit_null(self):
        history = self.history()
        for days in (7,14,21,28):
            history[self.origin-dt.timedelta(days=days)] = None
        first = recent_forecasts(history, self.origin, include_weekly_naive=True)['predictions'][0]
        self.assertIsNone(first['weekday_mean_28'])
        self.assertIsNone(first['weekly_naive'])
        self.assertEqual(first['mean_support'], 0)
        self.assertIsNotNone(first['mean_missing_reason'])

    def test_unavailable_future_cannot_change_sources_or_predictions(self):
        history = self.history()
        expected = recent_forecasts(history, self.origin, include_weekly_naive=True)
        history.update({self.origin+dt.timedelta(days=i): object() for i in range(21)})
        self.assertEqual(expected, recent_forecasts(history, self.origin, include_weekly_naive=True))

    def test_recent_mean_can_lag_a_new_level(self):
        history = {self.origin-dt.timedelta(days=i): (100. if i<=7 else 40.) for i in range(1,29)}
        first = recent_forecasts(history, self.origin, include_weekly_naive=True)['predictions'][0]
        self.assertEqual(first['weekday_mean_28'], 55.)
        self.assertEqual(first['weekly_naive'], 100.)


if __name__ == '__main__':
    unittest.main(verbosity=2)
