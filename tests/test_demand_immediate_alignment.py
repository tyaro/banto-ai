import copy
import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import demand_immediate_alignment as q
from test_demand_annual_reliability_v2 import row as previous_row

def row(origin='2014-06-18',store=6):
    r=previous_row(origin,store);r['past_original_quantity'][-14:]=[13.]*7+[15.]*7
    return r

class AlignmentChecks(unittest.TestCase):
    def test_current_level_change_and_year_agree(self):
        r=row();p,t=q.candidates(r)
        self.assertTrue(t['prior_reliability']['no_cross_gate']);self.assertTrue(t['aligned_gate'])
        self.assertEqual(t['pair_count'],7);self.assertEqual(t['latest14_replay'],210.);self.assertEqual(t['level_gap'],28.);self.assertEqual(t['week_change'],14.)
        self.assertAlmostEqual(math.fsum(p['aligned_anchor']),218.4);self.assertAlmostEqual(math.fsum(p['aligned_cap']),210.)
        self.assertTrue(t['cap_reduced'])

    def test_opposite_year_direction_vetoes(self):
        r=row();r['annual_input']['values'][28:]=[8.]*14
        p,t=q.candidates(r);self.assertTrue(t['prior_reliability']['no_cross_gate']);self.assertFalse(t['aligned_gate'])
        self.assertIn('level_year_direction_disagreement',t['reasons']);self.assertEqual(p['aligned_cap'],r['matched_mean28'])

    def test_zero_latest_change_is_not_alignment(self):
        r=row();r['past_original_quantity'][-14:]=[14.]*14
        p,t=q.candidates(r);self.assertTrue(t['prior_reliability']['no_cross_gate']);self.assertFalse(t['aligned_gate'])
        self.assertIn('zero_alignment_signal',t['reasons']);self.assertEqual(p['aligned_anchor'],r['matched_mean28'])

    def test_old_reliability_still_required(self):
        r=row();r['reliability_input']['14']['values'][28:]=[30.]*14
        p,t=q.candidates(r);self.assertFalse(t['prior_reliability']['no_cross_gate']);self.assertIn('past_no_cross_failed',t['reasons'])
        self.assertFalse(t['aligned_gate']);self.assertEqual(p['aligned_cap'],r['matched_mean28'])

    def test_missing_is_not_imputed_and_observed_zero_remains_supported(self):
        r=row();r['past_original_quantity'][-1]=None;r['past_original_observed'][-1]=False
        p,t=q.candidates(r);self.assertEqual(t['pair_count'],6);self.assertIn('latest_pair_support',t['reasons']);self.assertIsNone(t['latest14_replay'])
        r=row();r['past_original_quantity'][-1]=0.
        p,t=q.candidates(r);self.assertEqual(t['pair_count'],7);self.assertEqual(t['recent7'][-1],0.)

    def test_past_closure_excluded_without_erasing_raw(self):
        r=row('2015-01-15');p,t=q.candidates(r)
        self.assertEqual(t['pair_count'],6);self.assertEqual(t['previous7'][0],13.);self.assertIn('latest_pair_support',t['reasons'])

    def test_current_closure_mask_used_in_level_and_output(self):
        r=row();r['open_mask'][0]=False;r['matched_mean28'][0]=0.
        p,t=q.candidates(r);self.assertEqual(t['latest14_replay'],195.);self.assertTrue(all(values[0]==0. for values in p.values()))
        self.assertGreater(t['level_gap'],0.)

    def test_current_target_and_alpha_not_used_in_gate(self):
        class Poison(dict):
            def __getitem__(self,k):
                if k=='actual':raise AssertionError('future target read')
                return super().__getitem__(k)
        r=Poison(row());raw,trace=q.candidates(r)
        for alpha in (0.,.5,1.):
            policy={'quarter_coefficients':{str(i):{m:{'alpha':alpha} for m in q.ORDER} for i in range(1,5)}}
            p=q.choices(r,policy);self.assertEqual(q.candidates(r)[1],trace)
            self.assertAlmostEqual(math.fsum(p['aligned_cap']),182.+28.*alpha)

    def test_large_year_endpoint_capped_in_total_units(self):
        r=row();r['annual_input']['values'][28:]=[20.]*14
        p,t=q.candidates(r);self.assertTrue(t['aligned_gate']);self.assertAlmostEqual(t['capped_difference'],28.)
        self.assertAlmostEqual(math.fsum(p['aligned_anchor'])-182.,182.)
        self.assertAlmostEqual(math.fsum(p['aligned_cap'])-182.,28.)

    def test_quarter_calibration_and_metadata_are_separate(self):
        rows=[row(f'2014-{month:02d}-18',s) for month in (3,6,9,11) for s in q.FIT]
        for r in rows:
            if r['origin'].startswith('2014-03'):r['actual']=[12.]*14
        policy,_=q.calibrate(rows)
        self.assertEqual(policy['quarter_coefficients']['1']['aligned_anchor']['alpha'],0.)
        self.assertGreater(policy['quarter_coefficients']['2']['aligned_anchor']['alpha'],0.)
        with self.assertRaises(ValueError):q.calibrate([{'store':6,'origin':'2015-01-01'}])

if __name__=='__main__':unittest.main()
