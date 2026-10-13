"""Only new related-history mechanism checks; prior suites are not repeated."""
import datetime as dt
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from demand_related_history import available_window, level_features, comparison_features


class RelatedHistoryTests(unittest.TestCase):
    origin = dt.date(2020, 2, 3)

    def history(self):
        return {self.origin-dt.timedelta(days=i): float(i) for i in range(1, 36)}

    def test_hand_values_and_second_week_indicator(self):
        window = available_window(self.history(), self.origin)
        first = level_features(window, self.origin, self.origin)
        self.assertEqual(first['features'], [17.5, 4., 11.])
        self.assertEqual(first['support'], [4, 7, 7])
        windows = {1: window}
        self.assertEqual(comparison_features(windows,1,self.origin,self.origin,related=False), [17.5,4.,11.,0.])
        self.assertEqual(comparison_features(windows,1,self.origin,self.origin+dt.timedelta(days=7),related=False), [17.5,4.,11.,1.])

    def test_future_poison_does_not_enter_window_or_features(self):
        history = self.history()
        before = available_window(history, self.origin)
        history.update({self.origin+dt.timedelta(days=i): object() for i in range(30)})
        self.assertEqual(before, available_window(history, self.origin))
        self.assertEqual(min(before['values']), self.origin-dt.timedelta(days=28))

    def test_missing_and_observed_zero(self):
        history = self.history()
        history[self.origin-dt.timedelta(days=7)] = 0.
        history[self.origin-dt.timedelta(days=14)] = None
        feature = level_features(available_window(history,self.origin),self.origin,self.origin)
        self.assertEqual(feature['features'][0], (0+21+28)/3)
        history[self.origin-dt.timedelta(days=21)] = None
        missing = level_features(available_window(history,self.origin),self.origin,self.origin)
        self.assertIsNone(missing['features'])
        self.assertEqual(missing['reason'], 'insufficient_observed_window')

    def test_only_related_path_changes_with_peer_history(self):
        own = available_window(self.history(), self.origin)
        windows = {1: own, 2: available_window({d:2*v for d,v in self.history().items()},self.origin), 3:own}
        self.assertEqual(comparison_features(windows,1,self.origin,self.origin,related=False),[17.5,4.,11.,0.])
        self.assertEqual(comparison_features(windows,1,self.origin,self.origin,related=True),[17.5,4.,11.,0.,35.,8.,22.,17.5,4.,11.])
        windows[2] = available_window({},self.origin)
        self.assertIsNone(comparison_features(windows,1,self.origin,self.origin,related=True))
        self.assertIsNotNone(comparison_features(windows,1,self.origin,self.origin,related=False))

    def test_unavailable_manual_window_and_outside_horizon_rejected(self):
        with self.assertRaises(ValueError):
            level_features({'values':{self.origin:1}},self.origin,self.origin)
        with self.assertRaises(ValueError):
            level_features(available_window(self.history(),self.origin),self.origin,self.origin+dt.timedelta(days=14))


if __name__ == '__main__':
    unittest.main(verbosity=2)
