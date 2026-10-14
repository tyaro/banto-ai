import datetime as dt
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from demand_training_diagnostics import read_prefix, zero_runs, reference_window


class TrainingDiagnosticsChecks(unittest.TestCase):
    def test_prefix_parser_ignores_later_payload(self):
        raw = b'store_nbr,date,sales,observed\n5,2015-01-01,0,1\n5,2015-01-02,,0\nBAD,2016-01-01,BOMB,BOMB\n'
        h = read_prefix(raw)[5]
        self.assertEqual(h[dt.date(2015, 1, 1)], 0.)
        self.assertIsNone(h[dt.date(2015, 1, 2)])
        self.assertEqual(len(h), 2)

    def test_zero_run_is_broken_by_missing_and_gap(self):
        start = dt.date(2015, 1, 1)
        h = {start+dt.timedelta(days=k): 0. for k in range(32)}
        h[start+dt.timedelta(days=14)] = None
        del h[start+dt.timedelta(days=29)]
        self.assertEqual([r['days'] for r in zero_runs(h)], [14, 14])

    def test_initial_objective_and_zero_denominator(self):
        origin = dt.date(2015, 3, 1)
        h = {origin+dt.timedelta(days=k): 10. for k in range(-56, 14)}
        r = reference_window(h, origin, 10., [])
        self.assertAlmostEqual(r['initial_objective'], .5*(.04/3))
        self.assertEqual(r['total_error'], 0.)
        for day in h:
            h[day] = 0.
        r = reference_window(h, origin, 10., [])
        self.assertEqual(r['actual_total'], 0.)
        self.assertGreater(r['initial_objective'], 0.)
        with self.assertRaises(ValueError):
            reference_window(h, dt.date(2015, 12, 20), 10., [])


if __name__ == '__main__':
    unittest.main()
