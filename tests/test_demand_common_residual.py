import copy,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import demand_common_residual as m
from test_demand_prefix_adapter import sample_batch
from demand_prefix_adapter import fixed_features


def full_batch():
 rows=[]
 for d in ('2013-02-26','2013-05-07','2013-08-27','2013-11-19'):
  for s in m.FIT:rows.extend(sample_batch(d,s)['rows'])
 return {'schema':'demand-permitted-prefix-v1','cutoff':'2014-01-01','feature_spec':'common-signed-level-week-v1','rows':rows}

class CommonResidualTests(unittest.TestCase):
 def test_average_loss_and_intercept_are_penalized(self):
  state=m.train(full_batch());self.assertAlmostEqual(state['beta'][0],.1);self.assertEqual(state['beta'][1:],[0.,0.]);self.assertAlmostEqual(sum(r['weight'] for r in state['weighted_rows']),1.)
  self.assertAlmostEqual(state['gram'][0][0],2.)
 def test_store_quarter_weights_not_window_count(self):
  batch=full_batch();extra=copy.deepcopy(sample_batch('2013-03-12',6)['rows'][0]);batch['rows'].append(extra);state=m.train(batch)
  weights={r['key']:r['weight'] for r in state['weighted_rows']};rows=[r for r in batch['rows'] if r['store']==6 and r['origin'][5:7] in ('02','03')]
  self.assertAlmostEqual(sum(weights[r['key']] for r in rows),1/40)
 def test_structural_support_zero_vector(self):
  batch=full_batch();batch['rows'].pop();state=m.train(batch);self.assertFalse(state['supported']);self.assertEqual(state['beta'],[0.,0.,0.]);self.assertTrue(all(v['alpha']==0. for v in state['calibration'].values()))
 def test_floor_before_alpha_is_linear_endpoint(self):
  self.assertEqual(m.endpoint([10.]*14,10.,[1.,0.,0.],[-2.,0.,0.]),0.)
  B=140.;D=-140.;self.assertEqual(B+.5*D,70.)
  self.assertNotEqual(B+.5*D,max(B+.5*14*10*(-2.),0.))
 def test_no_endpoint_for_unsupported_or_zero_baseline(self):
  self.assertEqual(m.endpoint([10.]*14,10.,None,[999.,0.,0.]),140.)
  self.assertEqual(m.endpoint([0.]*14,10.,[1.,0.,0.],[1.,0.,0.]),0.)
 def test_past_risk_constraints_include_fallback_rows(self):
  batch=full_batch();row=batch['rows'][0];row['past14_values'][0]=None;row['features'],row['reasons']=fixed_features(row['past14_values'],row['past14_dates'],row['baseline'],row['assumed_open_mask'],row['scale'])
  state=m.train(batch);self.assertFalse(state['supported']);self.assertEqual(state['calibration']['1']['complete_windows'],10);self.assertEqual(len(state['calibration_journal']['1']),10)
 def test_cholesky_solution_satisfies_normal_equations(self):
  A=[[3.,1.,.5],[1.,4.,.25],[.5,.25,2.]];rhs=[1.,2.,3.];beta=m.solve_spd(A,rhs)
  for row,y in zip(A,rhs):self.assertAlmostEqual(math.fsum(x*b for x,b in zip(row,beta)),y)
  with self.assertRaises(ValueError):m.solve_spd([[-1.,0.,0.],[0.,1.,0.],[0.,0.,1.]],rhs)
 def test_nonfinite_numerics_fail_not_fallback(self):
  with self.assertRaises(ValueError):m.endpoint([10.]*14,10.,[1.,0.,0.],[float('inf'),0.,0.])

if __name__=='__main__':unittest.main()
