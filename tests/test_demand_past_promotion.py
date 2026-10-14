import datetime as dt
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from demand_past_promotion import parse_count, past_features


class PromotionChecks(unittest.TestCase):
    def test_count_contract(self):
        self.assertEqual(parse_count('12'), 12)
        self.assertEqual(parse_count('0'), 0)
        self.assertIsNone(parse_count(''))
        for text in ('-1', '1.0', ' 1', 'nan', '１'):
            with self.assertRaises(ValueError):
                parse_count(text)

    def test_no_future_lookup(self):
        origin = dt.date(2015, 6, 1)
        class PastOnly(dict):
            def get(self, key, default=None):
                if key >= origin:
                    raise AssertionError('future accessed')
                return super().get(key, default)
        history = PastOnly({origin-dt.timedelta(days=k): 0 for k in range(1, 29)})
        self.assertEqual(past_features(history, origin)['recent_state'], 'recorded_zero')

    def test_missing_is_not_zero(self):
        origin = dt.date(2015, 6, 1)
        history = {origin-dt.timedelta(days=k): 0 for k in range(1, 29)}
        history[origin-dt.timedelta(days=1)] = None
        value = past_features(history, origin)
        self.assertEqual(value['support7'], 6)
        self.assertEqual(value['recent_state'], 'insufficient')
        self.assertIsNone(value['delta'])

    def test_window_boundary_and_change(self):
        origin = dt.date(2015, 6, 1)
        history = {origin-dt.timedelta(days=k): (4 if k <= 7 else 0) for k in range(1, 29)}
        history[origin] = 999
        value = past_features(history, origin)
        self.assertEqual((value['mean7'], value['mean28'], value['delta']), (4, 1, 3))
        self.assertEqual(value['change_state'], 'up')
        self.assertEqual(value['first_date'], '2015-05-04')
        self.assertEqual(value['last_date'], '2015-05-31')


if __name__ == '__main__':
    unittest.main()
