import copy,datetime as dt,sys,unittest
from fractions import Fraction as F
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import demand_constrained_2014 as m
from demand_input_boundary_v2 import project_input
from test_demand_input_boundary import legacy,transform
from test_demand_common_residual import full_batch

class ReplayIntegrationTests(unittest.TestCase):
    def row(self):return project_input(legacy('2014-02-15'))
    def state(self,beta=('0','0','0')):return {'cutoff':'2014-01-01','supported':True,'beta':list(beta)}
    def test_training_only_concrete_batch_no_reads(self):
        batch=full_batch();before=copy.deepcopy(batch)
        with patch.object(Path,'open',side_effect=AssertionError('no files')):state=m.train_batch(batch,lambda:None)
        self.assertEqual(batch,before);self.assertEqual(state['beta'],['1/10','0','0']);self.assertEqual(state['verification']['gap'],'0')
    def test_zero_delta_preserves_baseline_and_rounded_sum_exception(self):
        r=self.row();weekday=[.1,.2,0.,0.,0.,0.,0.]
        r['past_values']=[weekday[dt.date.fromisoformat(d).weekday()] for d in r['past_dates']]
        r['matched_mean28']=[weekday[dt.date.fromisoformat(d).weekday()] for d in r['target_dates']]
        f=m.forecast(r,transform(),self.state())
        self.assertEqual(f['candidate_display'],r['matched_mean28']);self.assertEqual(f['delta_total'],'0')
        self.assertNotEqual(f['allocation']['canonical_baseline_minus_exact_sum'],'0')
    def test_changed_daily_sum_and_floor_zero(self):
        for beta in (['1/10','0','0'],['-100','0','0']):
            f=m.forecast(self.row(),transform(),self.state(beta));self.assertEqual(sum(map(F,f['candidate_daily_exact'])),F(f['candidate_total']))
        self.assertEqual(f['allocation']['branch'],'floor_zero');self.assertEqual(f['candidate_display'],[0.]*14)
    def test_unsupported_context_and_wrong_quarter(self):
        r=self.row();r['past_values'][-1]=None;r['past_observed'][-1]=False
        f=m.forecast(r,transform(),self.state(['1','0','0']));self.assertEqual(f['allocation']['branch'],'baseline_copy')
        state=self.state();state['cutoff']='2014-04-01'
        with self.assertRaises(ValueError):m.forecast(self.row(),transform(),state)
    def test_exact_positive_risk_is_not_hidden_by_float_total(self):
        rows=[];eps=F(1,10**30)
        for store in m.FIT:
            f=m.forecast(self.row(),transform(),self.state());f['store']=store
            f['candidate_total']=str(F(f['baseline_total'])+eps);f['candidate_daily_exact']=[str(F(10)+eps/14)]*14
            rows.append({'forecast':f,'observed':[10.]*14})
        v=m.score_group(rows,'observed')
        self.assertEqual(float(F(rows[0]['forecast']['candidate_total'])),140.)
        self.assertGreater(F(v['paired_exact']['over']),0);self.assertIn('over',v['violations'])
    def test_missing_scenarios_stay_separate(self):
        rows=[]
        for store in m.FIT:
            for missing in (False,True):
                f=m.forecast(self.row(),transform(),self.state());f['store']=store
                actual=[10.]*14
                if missing:actual[0]=None
                rows.append({'forecast':f,'observed':actual,'assumed_missing_zero':[0. if a is None else a for a in actual]})
        a=m.score_group(rows,'observed');b=m.score_group(rows,'assumed_missing_zero')
        self.assertEqual(a['candidate']['complete_totals'],10);self.assertEqual(b['candidate']['complete_totals'],20)
        self.assertEqual(a['paired_exact']['total_MSE'],'0');self.assertEqual(b['paired_exact']['total_MSE'],'0')

if __name__=='__main__':unittest.main()
