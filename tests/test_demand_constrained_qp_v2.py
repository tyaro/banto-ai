import copy,math,sys,unittest
from fractions import Fraction as F
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import demand_constrained_qp as old
import demand_constrained_qp_v2 as m
from demand_constrained_qp_verify import verify
from demand_prefix_adapter import fixed_features
from tests.test_demand_common_residual import full_batch

class ConsistentTotalTests(unittest.TestCase):
    def test_fractional_binary64_regression(self):
        b=[.1,.2]+[0.]*12
        expected=F.from_float(math.fsum(b))
        self.assertEqual(m.quantity_total(b),expected)
        self.assertEqual(m.predict_total(b,140,[1,0,0],[0,0,0]),expected)
        self.assertNotEqual(old.predict_total(b,140,[1,0,0],[0,0,0]),expected)

    def test_prefix_and_prediction_share_total_conversion(self):
        batch=full_batch();r=batch['rows'][0];r['baseline']=[.1,.2]+[0.]*12
        r['features'],r['reasons']=fixed_features(r['past14_values'],r['past14_dates'],r['baseline'],r['assumed_open_mask'],r['scale'])
        before=copy.deepcopy(batch);built=m.from_prefix(batch);self.assertEqual(batch,before)
        row=built['problem']['rows'][0]
        self.assertEqual(F(row['B']),m.predict_total(r['baseline'],row['unit'],row['x'],['0']*3))

    def test_integer_floor_and_fallback_results_unchanged(self):
        self.assertEqual(m.predict_total([10]*14,140,[1,0,0],[-2,0,0]),0)
        self.assertEqual(m.predict_total([10]*14,140,None,[-2,0,0]),140)
        self.assertEqual(m.predict_total([0]*14,140,[1,0,0],[2,0,0]),0)

    def test_daily_quantity_and_unit_rejected(self):
        for values in ([1]*13,[-1]+[1]*13,[True]+[1]*13,[float('nan')]+[0]*13):
            with self.assertRaises(ValueError):m.quantity_total(values)
        for unit in (0,-1,True):
            with self.assertRaises(ValueError):m.predict_total([1]*14,unit,[1,0,0],[0]*3)
        with self.assertRaises(ValueError):m.predict_total([1]*14,14,[1,0],[0]*3)

    def test_artificial_prefix_same_exact_solution(self):
        built=m.from_prefix(full_batch());cert=m.solve(built['problem'])
        self.assertEqual(cert['beta'],['1/10','0','0']);self.assertEqual(verify(built['problem'],cert)['gap'],'0')

if __name__=='__main__':unittest.main()
