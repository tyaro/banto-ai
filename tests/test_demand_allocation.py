"""Only new allocation mechanisms; prior forecasting suites are not repeated."""
from pathlib import Path
import math,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from demand_allocation import redistribute_fourteen


class AllocationTests(unittest.TestCase):
    def test_hand_allocation_preserves_total(self):
        result=redistribute_fourteen([100.]*14,[.6]+[1.]*13)
        self.assertAlmostEqual(result['predictions'][0],100*.6*1400/1360)
        self.assertAlmostEqual(result['predictions'][1],100*1400/1360)
        self.assertAlmostEqual(math.fsum(result['predictions']),1400.)
        self.assertLess(result['predictions'][0],100.)
        self.assertGreater(result['predictions'][1],100.)

    def test_missing_baseline_does_not_normalize_partial_sum(self):
        result=redistribute_fourteen([None]+[100.]*13,[1.]*14)
        self.assertEqual(result['reason'],'incomplete_baseline_vector')
        self.assertEqual(result['predictions'],[None]*14)
        self.assertIsNone(result['allocated_total'])

    def test_observed_zero_total_and_unchanged_weights(self):
        self.assertEqual(redistribute_fourteen([0.]*14,[0.]*14)['predictions'],[0.]*14)
        values=[float(i) for i in range(14)]
        self.assertEqual(redistribute_fourteen(values,[1.]*14)['predictions'],values)

    def test_no_positive_weight_for_positive_total_is_explicit_null(self):
        result=redistribute_fourteen([100.]*14,[0.]*14)
        self.assertEqual(result['reason'],'zero_allocation_weight_with_positive_total')
        self.assertIsNone(result['allocated_total'])

    def test_invalid_width_negative_and_nonfinite_rejected(self):
        with self.assertRaises(ValueError):redistribute_fourteen([1.]*13,[1.]*14)
        for bad in [-1.,float('inf'),float('nan'),True]:
            with self.assertRaises(ValueError):redistribute_fourteen([1.]*14,[bad]+[1.]*13)


if __name__=='__main__':unittest.main(verbosity=2)
