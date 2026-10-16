import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import demand_persistence as q
from test_demand_immediate_alignment import row

class PersistenceChecks(unittest.TestCase):
    def test_broad_persistence_with_strengthening(self):
        r=row();p,t=q.candidates(r)
        self.assertTrue(t['prior_alignment']['aligned_gate']);self.assertTrue(t['persistent_gate']);self.assertTrue(t['nonweakening_gate'])
        self.assertEqual(t['week_totals'],[84.,91.,105.]);self.assertEqual(t['older_sum'],7.);self.assertEqual(t['recent_sum'],14.)
        self.assertEqual(t['older_median'],1.);self.assertEqual(t['recent_median'],2.)
        self.assertEqual(p['persistent_anchor'],p['nonweakening_anchor'])

    def test_deceleration_is_not_persistence_failure(self):
        r=row();r['past_original_quantity'][-7:]=[13.5]*7
        p,t=q.candidates(r);self.assertTrue(t['persistent_gate']);self.assertFalse(t['nonweakening_gate'])
        self.assertEqual(t['older_sum'],7.);self.assertEqual(t['recent_sum'],3.5);self.assertIn('directional_weakening',t['reasons'])
        self.assertEqual(p['nonweakening_anchor'],r['matched_mean28'])

    def test_constant_week_change_is_not_weakening(self):
        r=row();r['past_original_quantity'][-7:]=[14.]*7
        p,t=q.candidates(r);self.assertEqual(t['older_sum'],t['recent_sum']);self.assertTrue(t['nonweakening_gate'])

    def test_weekly_reversal_veto(self):
        r=row();r['past_original_quantity'][-21:-14]=[14.]*7
        p,t=q.candidates(r);self.assertTrue(t['prior_alignment']['aligned_gate']);self.assertLess(t['older_sum'],0.)
        self.assertGreater(t['recent_sum'],0.);self.assertFalse(t['persistent_gate'])

    def test_median_breadth_vetoes_outlier_sum(self):
        r=row();r['past_original_quantity'][-7:]=[12.]*4+[23.]*3
        p,t=q.candidates(r);self.assertTrue(t['prior_alignment']['aligned_gate']);self.assertGreater(t['recent_sum'],0.)
        self.assertLess(t['recent_median'],0.);self.assertFalse(t['persistent_gate'])

    def test_missing_and_observed_zero_are_distinct(self):
        r=row();r['past_original_quantity'][-21]=None;r['past_original_observed'][-21]=False
        p,t=q.candidates(r);self.assertEqual(t['triple_count'],6);self.assertIn('three_week_support',t['reasons']);self.assertIsNone(t['older_sum'])
        r=row();r['past_original_quantity'][-21]=0.
        p,t=q.candidates(r);self.assertEqual(t['triple_count'],7);self.assertEqual(t['weeks_old_to_new'][0][0],0.)

    def test_closure_raw_not_erased_and_future_zero_preserved(self):
        r=row('2015-01-22');p,t=q.candidates(r);self.assertEqual(t['triple_count'],6)
        self.assertEqual(t['weeks_old_to_new'][0][0],12.)
        r=row();r['open_mask'][0]=False;r['matched_mean28'][0]=0.
        p,t=q.candidates(r);self.assertTrue(all(v[0]==0. for v in p.values()))

    def test_future_target_and_alpha_not_used_by_gate(self):
        class Poison(dict):
            def __getitem__(self,key):
                if key=='actual':raise AssertionError('current target read')
                return super().__getitem__(key)
        r=Poison(row());raw,trace=q.candidates(r)
        for alpha in (0.,.5,1.):
            policy={'quarter_coefficients':{str(i):{m:{'alpha':alpha} for m in q.ORDER} for i in range(1,5)}}
            p=q.choices(r,policy);self.assertEqual(q.candidates(r)[1],trace)
            self.assertAlmostEqual(math.fsum(p['persistent_anchor']),182.+36.4*alpha)

    def test_quarter_stop_does_not_propagate(self):
        rows=[row(f'2014-{month:02d}-18',s) for month in (3,6,9,11) for s in q.FIT]
        for r in rows:
            if r['origin'].startswith('2014-03'):r['actual']=[12.]*14
        p,_=q.calibrate(rows);self.assertEqual(p['quarter_coefficients']['1']['persistent_anchor']['alpha'],0.)
        self.assertGreater(p['quarter_coefficients']['2']['persistent_anchor']['alpha'],0.)
        with self.assertRaises(ValueError):q.calibrate([{'store':6,'origin':'2015-01-01'}])

    def test_year_direction_sign_is_used_for_negative_trend(self):
        # A declining sequence can be strengthening in its own direction.
        r=row();r['past_original_quantity']=[16.]*28+[14.]*7+[13.]*7+[12.]*7+[10.]*7
        r['annual_input']['values'][28:]=[8.]*14
        for data in r['reliability_input'].values():data['values'][28:]=[8.]*14
        r['matched_mean28']=[13.]*14
        p,t=q.candidates(r);self.assertEqual(t['year_direction'],-1)
        self.assertEqual(t['older_sum'],-7.);self.assertEqual(t['recent_sum'],-14.);self.assertTrue(t['nonweakening_pass'])

if __name__=='__main__':unittest.main()
