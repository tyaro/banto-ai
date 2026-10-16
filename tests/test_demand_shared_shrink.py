import unittest,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from demand_shared_shrink import FIT,ORDER,concentration,summarize,fit_journal,calibrate,influence,choose

def journal():
    dates=('2014-02-12','2014-05-07','2014-08-27','2014-11-19')
    return {str(q):[{'store':st,'origin':dates[q-1],'e':-20.,'D':10. if q==3 and st==6 else 0.,'scale':1.} for st in FIT] for q in range(1,5)}

class SharedShrinkTests(unittest.TestCase):
    def test_zero_energy_has_zero_support(self):
        self.assertEqual(concentration([0.]*120),0.)
        self.assertEqual(concentration([0.,3.,0.]),1.)
    def test_single_sample_ratio_is_residual_ratio(self):
        p,_=fit_journal(journal());q=p['quarter_statistics']['3']
        self.assertAlmostEqual(q['unconstrained'],2.)
        self.assertEqual(q['energy_kish'],1.)
        self.assertAlmostEqual(p['global_shrunk'],.5)
        self.assertAlmostEqual(p['quarter_coefficients']['3']['partial_pool']['alpha'],.5)
    def test_unsupported_quarters_do_not_borrow(self):
        p,_=fit_journal(journal())
        for q in ('1','2','4'):
            self.assertTrue(all(v['alpha']==0 for v in p['quarter_coefficients'][q].values()))
    def test_global_energy_equal_quarters(self):
        p,rr=fit_journal(journal())
        self.assertAlmostEqual(p['global_statistics']['energy'],p['quarter_statistics']['3']['energy']/4)
        self.assertAlmostEqual(sum(r['weight'] for r in rr['3']),1.)
    def test_store_and_within_store_weights(self):
        j=journal();j['3'].append(dict(j['3'][0],origin='2014-09-24'))
        p,rr=fit_journal(j)
        self.assertAlmostEqual(sum(r['weight'] for r in rr['3'] if r['store']==6),.1)
        self.assertAlmostEqual(p['quarter_statistics']['3']['energy_kish'],2.)
        self.assertAlmostEqual(p['quarter_statistics']['3']['store_energy_kish'],1.)
    def test_removal_reweights_and_support_vanishes(self):
        p,rr=fit_journal(journal(),excluded_store=6)
        self.assertEqual(p['quarter_statistics']['3']['energy'],0.)
        self.assertEqual(p['global_shrunk'],0.)
        self.assertTrue(all(abs(r['weight']-1/9)<1e-15 for r in rr['3']))
    def test_one_quarter_guard_does_not_stop_another(self):
        j=journal();j['4'][0]['e']=20.;j['4'][0]['D']=1.
        p,_=fit_journal(j)
        self.assertEqual(p['quarter_statistics']['4']['upper'],0.)
        self.assertGreater(p['quarter_coefficients']['3']['pooled_shrink']['alpha'],0.)
        self.assertEqual(p['quarter_coefficients']['4']['pooled_shrink']['alpha'],0.)
    def test_influence_empty_origin_is_no_information(self):
        j=journal();keys=[(r['store'],r['origin']) for rr in j.values() for r in rr]+[(6,'2014-12-17')]
        d=influence(j,keys,{'fixed':[r for rr in j.values() for r in rr]})
        row=next(r for r in d['folds'] if r['kind']=='origin' and r['value']=='2014-12-17')
        self.assertEqual(row['complete_removed'],0)
        self.assertEqual(row['fixed_D_changes']['fixed']['partial_pool']['max_abs'],0.)
    def test_post_2014_and_duplicate_rejected(self):
        j=journal();j['1'][0]['origin']='2015-02-12'
        with self.assertRaises(ValueError):fit_journal(j)
        j=journal();j['1'].append(dict(j['1'][0]))
        with self.assertRaises(ValueError):fit_journal(j)
        with self.assertRaises(ValueError):calibrate([{'store':6,'origin':'2015-01-01'}])
    def test_selection_rejects_one_side_even_if_mse_better(self):
        def score(mse,under,over):return {'macro':{'total':mse},'shortfall':{'macro':{'under':under,'over':over}}}
        groups={f'normal_Q{q}':{mode:{'matched_mean28':score(1.,1.,1.),'pooled_shrink':score(.9,.8,1.01),'partial_pool':score(.95,.9,.9)} for mode in ('observed','assumed_missing_zero')} for q in range(1,5)}
        p=choose(groups)
        self.assertTrue(all(m=='partial_pool' for m in p['selected_by_quarter'].values()))
        self.assertIn('observed/over',p['eligibility']['1']['pooled_shrink']['reasons'])

if __name__=='__main__':unittest.main()
