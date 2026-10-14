from pathlib import Path
import datetime as dt
import sys, unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from demand_sequential_interval import select_completed, choose_sequential


def rows(count):
    return [{'store': 4, 'origin': str(dt.date(2014, 1, 1)+dt.timedelta(days=14*k)),
             'available': True, 'past_positive': True, 'y': float(k)} for k in range(count)]


class SequentialChecks(unittest.TestCase):
    def test_current_and_future_flags_and_residual_not_accessed(self):
        class HeaderOnly(dict):
            def __getitem__(self, key):
                if key not in ('store', 'origin'):
                    raise AssertionError('unfinished label payload accessed')
                return super().__getitem__(key)
        current = dt.date(2016, 1, 1)
        data = [HeaderOnly(store=4, origin='2015-12-19'),
                HeaderOnly(store=4, origin='2016-01-01'),
                HeaderOnly(store=4, origin='2016-02-01')]
        self.assertEqual(select_completed(data, 4, current), [])
        eligible = rows(1)[0]
        self.assertEqual(len(select_completed([eligible, *data], 4, current)), 1)

    def test_latest_26_and_support_19_20_boundary(self):
        selected = select_completed(rows(30), 4, dt.date(2016, 1, 1))
        self.assertEqual([r['y'] for r in selected], list(map(float, range(4, 30))))
        shared = {'q10': -.1, 'q90': .1}
        short = choose_sequential(selected[:19], 4, [], {}, shared)
        self.assertIsNone(short['own']['q10'])
        self.assertIs(short['selected'], shared)
        enough = choose_sequential(selected[:20], 4, [], {}, shared)
        self.assertEqual((enough['own']['q10'], enough['own']['q90']), (5., 21.))

    def test_exact_pool_reuses_original_quantiles(self):
        selected = select_completed(rows(21), 4, dt.date(2016, 1, 1))
        original = {'q10': 2., 'q90': 18.}
        with patch('demand_sequential_interval.calibrate', side_effect=AssertionError('original Q repeated')):
            result = choose_sequential(selected, 4, list(selected), original, {})
        self.assertIs(result['own'], original)
        self.assertEqual(result['quantile_action'], 'reuse_saved_own')

    def test_foreign_store_rejected_before_numeric_payload(self):
        with self.assertRaisesRegex(ValueError, 'another store'):
            select_completed([{'store': 8}], 4, dt.date(2016, 1, 1))

    def test_missing_and_zero_residual_distinct(self):
        data = rows(3)
        data[0].update(available=False, y=None)
        data[1].update(past_positive=False, y=None)
        data[2]['y'] = 0.
        selected = select_completed(data, 4, dt.date(2016, 1, 1))
        self.assertEqual([r['y'] for r in selected], [0.])
        data[2]['y'] = None
        with self.assertRaisesRegex(ValueError, 'missing is not zero'):
            select_completed(data, 4, dt.date(2016, 1, 1))


if __name__ == '__main__':
    unittest.main()
