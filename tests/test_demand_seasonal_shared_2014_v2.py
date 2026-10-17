import copy,sys,unittest
from fractions import Fraction as F
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import demand_seasonal_shared_2014 as m
from tests.test_demand_common_residual import full_batch
from tests.test_demand_prefix_adapter import sample_batch
from tests.test_demand_input_boundary import legacy,transform
from demand_input_boundary_v2 import project_input
from demand_prefix_adapter import fixed_features

class SeasonalSharingTests(unittest.TestCase):
    def test_own_quarter_weights_and_penalized_intercept(self):
        p=m.select_season(full_batch());self.assertEqual(len(p['rows']),10)
        state=m.train_batch(p,lambda:None)
        self.assertEqual(state['beta'],['1/10','0','0']);self.assertEqual(state['verification']['gap'],'0')
        self.assertEqual(sum(F(r['fit_weight']) for r in state['problem']['rows']),1)
        self.assertEqual(sum(F(r['risk_weight']) for r in state['problem']['rows']),1)
    def test_other_quarter_labels_cannot_affect_payload(self):
        class Bomb:
            def __deepcopy__(self,memo):raise AssertionError('unselected label touched')
        b=full_batch();expected=m.select_season(b)
        for r in b['rows']:
            if m.quarter(r['origin'])!=1:r['raw_actual']=Bomb()
        self.assertEqual(m.select_season(b),expected)
    def test_fresh_delivery_and_learning_no_path_reads(self):
        b=full_batch();before=copy.deepcopy(b);p=m.select_season(b)
        with patch.object(Path,'open',side_effect=AssertionError('no reads')):m.train_batch(p,lambda:None)
        p['rows'][0]['raw_actual'][0]=999.;self.assertEqual(b,before)
    def test_other_q_and_missing_own_store_are_rejected(self):
        with self.assertRaises(ValueError):m.train_batch(full_batch(),lambda:None)
        p=m.select_season(full_batch());p['rows'].pop()
        with patch.object(m,'solve',side_effect=AssertionError('must stop')):
            with self.assertRaisesRegex(RuntimeError,'support_missing'):m.train_batch(p,lambda:None)
    def test_input_fallback_stays_in_risk_denominator(self):
        b=full_batch();r=sample_batch('2013-03-12',6)['rows'][0];r['past14_values'][0]=None
        r['features'],r['reasons']=fixed_features(r['past14_values'],r['past14_dates'],r['baseline'],r['assumed_open_mask'],r['scale']);b['rows'].append(r)
        p=m.seasonal_problem(m.select_season(b));row=next(x for x in p['rows'] if x['key']==r['key'])
        self.assertEqual(row['fit_weight'],'0');self.assertEqual(row['risk_weight'],'1/20');self.assertIsNone(row['x'])
    def test_origin_deletion_is_all_stores_and_reweighted(self):
        b=full_batch()
        for s in m.FIT:b['rows'].extend(sample_batch('2013-03-12',s)['rows'])
        p=m.select_season(b,excluded_origin='2013-02-26')
        self.assertEqual(len(p['rows']),10);self.assertEqual({r['origin'] for r in p['rows']},{'2013-03-12'})
        problem=m.seasonal_problem(p);self.assertTrue(all(r['fit_weight']=='1/10' for r in problem['rows']))
        with self.assertRaises(RuntimeError):m.seasonal_problem(m.select_season(p,excluded_origin='2013-03-12'))
    def test_origin_quarter_used_for_full_horizon(self):
        row=project_input(legacy('2014-03-26'));state={'cutoff':'2014-01-01','supported':True,'beta':['1/10','0','0']}
        f=m.forecast(row,transform(),state);self.assertTrue(row['target_dates'][-1].startswith('2014-04-'))
        self.assertEqual(f['candidate_daily_exact'],['11']*14);self.assertEqual(f['cutoff'],'2014-01-01')
    def test_future_or_missing_labels_rejected(self):
        for k,v in (('label_available_at','2014-01-02'),('raw_actual',[None]*14)):
            p=m.select_season(full_batch());p['rows'][0][k]=v
            with self.assertRaises(ValueError):m.seasonal_problem(p)

if __name__=='__main__':unittest.main()
