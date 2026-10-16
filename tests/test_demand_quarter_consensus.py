import copy
import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import demand_quarter_consensus as q
from demand_adaptive_consensus import calibrate
from test_demand_adaptive_consensus import row


def fixture():
    rows=[row(f'2014-{month:02d}-18',s) for month in (3,6,9,11) for s in q.FIT]
    for r in rows:
        r.update(matched_mean28=[14.]*14,raw_prediction=[17.]*14,actual=[15.]*14)
    policy,journal=calibrate(rows)
    return {'policy':policy,'sample_journal':journal}


class QuarterChecks(unittest.TestCase):
    def test_quarter_stop_does_not_stop_other_quarters(self):
        source=fixture(); initial,_=q.separate_coefficients(source)
        changed=copy.deepcopy(source)
        for method in q.ORDER:
            changed['policy']['quarter_constraints']['1'][method]['upper']=0.
        stopped,_=q.separate_coefficients(changed)
        for season in ('2','3','4'):
            self.assertEqual(initial['quarter_coefficients'][season],stopped['quarter_coefficients'][season])
        self.assertEqual(stopped['quarter_coefficients']['1']['consensus_raw']['alpha'],0.)
        self.assertGreater(stopped['quarter_coefficients']['2']['consensus_raw']['alpha'],0.)
        self.assertFalse(stopped['annual_coefficient_shared'])

    def test_independent_scalar_optima_and_upper_clip(self):
        source=fixture(); policy,_=q.separate_coefficients(source)
        for season in ('1','2','3','4'):
            self.assertAlmostEqual(policy['quarter_coefficients'][season]['consensus_bias']['alpha'],.5)
            self.assertAlmostEqual(policy['quarter_coefficients'][season]['consensus_raw']['alpha'],1/3)
        source['policy']['quarter_constraints']['2']['consensus_raw']['upper']=.1
        clipped,_=q.separate_coefficients(source)
        self.assertEqual(clipped['quarter_coefficients']['2']['consensus_raw']['alpha'],.1)
        self.assertEqual(clipped['quarter_coefficients']['1'],policy['quarter_coefficients']['1'])

    def test_zero_energy_and_effective_support_reported(self):
        policy,_=q.separate_coefficients(fixture())
        for season in policy['quarter_coefficients'].values():
            self.assertEqual(season['matched_mean28']['alpha'],0.)
            self.assertEqual(season['matched_mean28']['nonzero_direction_windows'],0)
            self.assertEqual(season['consensus_raw']['complete_windows'],10)
            self.assertEqual(season['consensus_raw']['nonzero_direction_windows'],10)

    def test_origin_quarter_applies_across_entire_horizon(self):
        policy,_=q.separate_coefficients(fixture())
        for m in q.ORDER:policy['quarter_coefficients']['2'][m]['alpha']=0.
        r=row('2014-03-28'); r['actual']=None
        predictions=q.choices(r,policy)
        self.assertAlmostEqual(math.fsum(predictions['consensus_raw']),196.)
        self.assertTrue(all(abs(v-14.)<1e-12 for v in predictions['consensus_raw']))
        self.assertEqual(q.choices(row('2014-04-01'),policy)['consensus_raw'],r['matched_mean28'])

    def test_same_endpoints_gate_and_future_target_not_read(self):
        class Poison(dict):
            def __getitem__(self,key):
                if key=='actual':raise AssertionError('future target read')
                return super().__getitem__(key)
        policy,_=q.separate_coefficients(fixture());r=row()
        for season in policy['quarter_coefficients'].values():
            for m in q.ORDER:season[m]['alpha']=1.
        self.assertEqual(q.choices(Poison(r),policy),q.candidates(r)[0])
        r['past_original_quantity'][-1]=None;r['past_original_observed'][-1]=False
        self.assertEqual(q.choices(Poison(r),policy)['consensus_raw'],r['matched_mean28'])

    def test_closure_zero_and_finite_coefficient(self):
        policy,_=q.separate_coefficients(fixture());r=row()
        r['open_mask'][5]=False;r['matched_mean28'][5]=r['raw_prediction'][5]=0.
        self.assertTrue(all(v[5]==0. for v in q.choices(r,policy).values()))
        policy['quarter_coefficients']['2']['consensus_raw']['alpha']=float('nan')
        with self.assertRaises(ValueError):q.choices(r,policy)

    def test_foreign_future_calibration_metadata_rejected(self):
        for key,value in (('store',31),('origin','2015-01-01')):
            source=fixture();source['sample_journal']['1']['matched_mean28'][0][key]=value
            with self.assertRaises(ValueError):q.separate_coefficients(source)
        source=fixture();source['policy']['observed_only']=False
        with self.assertRaises(ValueError):q.separate_coefficients(source)

    def test_quarter_adoption_and_rejection_are_independent(self):
        def score(mse=1.,under=1.,over=1.):
            return {'macro':{'total':mse},'shortfall':{'macro':{'under':under,'over':over}}}
        groups={f'normal_Q{i}':{mode:{m:score() for m in q.ORDER} for mode in ('observed','assumed_missing_zero')} for i in range(1,5)}
        for mode in groups['normal_Q2']:
            groups['normal_Q2'][mode]['consensus_raw']=score(.8,.9,.9)
        groups['normal_Q1']['assumed_missing_zero']['consensus_raw']=score(.5,1.,1.1)
        selected=q.choose(groups)
        self.assertEqual(selected['selected_by_quarter'],{'1':'matched_mean28','2':'consensus_raw','3':'matched_mean28','4':'matched_mean28'})
        self.assertIn('assumed_missing_zero/over',selected['eligibility']['1']['consensus_raw']['reasons'])
        self.assertFalse(selected['2015_used']);self.assertFalse(selected['newyear_used'])

if __name__=='__main__':unittest.main()
