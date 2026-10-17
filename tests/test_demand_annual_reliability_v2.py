import copy
import datetime as dt
import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import demand_annual_reliability_v2 as q

def annual(issue,ratio=1.2):
    a=issue-dt.timedelta(days=364)
    return {'first':str(a-dt.timedelta(days=28)),'annual_issue':str(a),'end_exclusive':str(a+dt.timedelta(days=14)),
            'values':[10.]*28+[10.*ratio]*14,'observed':[True]*42}

def row(origin='2014-06-18',store=6):
    o=dt.date.fromisoformat(origin)
    return {'store':store,'origin':origin,'scale':10.,'matched_mean28':[13.]*14,'open_mask':[True]*14,'actual':[16.]*14,
            'past_original_quantity':[10.]*28+[12.]*14+[14.]*14,'past_original_observed':[True]*56,
            'annual_input':annual(o),'reliability_input':{str(lag):annual(o-dt.timedelta(days=lag)) for lag in (14,28)}}

class ReliabilityChecks(unittest.TestCase):
    def test_two_nonoverlap_hindcasts_and_true_baseline(self):
        r=row();f,t=q.candidates(r);a=t['blocks']['28'];b=t['blocks']['14']
        self.assertEqual(math.fsum(a['baseline']),140.);self.assertEqual(math.fsum(a['actual']),168.)
        self.assertEqual(math.fsum(b['baseline']),154.);self.assertEqual(math.fsum(b['actual']),196.)
        self.assertEqual(a['actual_end_exclusive'],b['issue']);self.assertEqual(b['actual_end_exclusive'],r['origin'])
        self.assertTrue(t['validated_gate']);self.assertTrue(t['no_cross_gate']);self.assertFalse(t['gate_uses_alpha'])
        self.assertAlmostEqual(math.fsum(f['validated_anchor']),218.4)

    def test_past_crossing_can_pass_mse_but_not_no_cross(self):
        r=row();o=dt.date.fromisoformat(r['origin'])
        r['reliability_input']={str(lag):annual(o-dt.timedelta(days=lag),1.3) for lag in (14,28)}
        f,t=q.candidates(r);self.assertTrue(t['validated_gate']);self.assertFalse(t['no_cross_gate'])
        self.assertGreater(t['blocks']['28']['errors']['anchor_over'],0.)
        self.assertEqual(f['no_cross_anchor'],r['matched_mean28'])

    def test_one_failed_block_stops_both_gates(self):
        r=row();r['reliability_input']['14']=annual(dt.date.fromisoformat(r['origin'])-dt.timedelta(days=14),2.)
        f,t=q.candidates(r);self.assertTrue(t['blocks']['28']['strict_improvement']);self.assertFalse(t['validated_gate'])
        self.assertEqual(f['validated_anchor'],r['matched_mean28'])

    def test_same_forecast_not_strict_success(self):
        r=row();r['reliability_input']['28']=annual(dt.date.fromisoformat(r['origin'])-dt.timedelta(days=28),1.)
        f,t=q.candidates(r);self.assertFalse(t['blocks']['28']['strict_improvement']);self.assertFalse(t['no_cross_gate'])

    def test_missing_actual_not_zero_and_observed_zero_retained(self):
        r=row();r['past_original_quantity'][-1]=None;r['past_original_observed'][-1]=False
        f,t=q.candidates(r);self.assertIn('missing_actual',t['blocks']['14']['reasons']);self.assertFalse(t['validated_gate'])
        r=row();r['past_original_quantity'][-1]=0.
        f,t=q.candidates(r);self.assertTrue(t['blocks']['14']['supported']);self.assertEqual(t['blocks']['14']['actual'][-1],0.)

    def test_2012_not_read_and_oldest_reference_is_420_days(self):
        class Checked(dict):
            def get(self,day):
                if not dt.date(2013,1,1)<=day<dt.date(2015,1,1):raise AssertionError('outside raw scope')
                return 10.
        r=row('2014-01-01');r.pop('annual_input');r.pop('reliability_input')
        p=q.attach_reliability(r,{6:Checked()});self.assertEqual(p['reliability_input']['28']['first'],str(dt.date(2014,1,1)-dt.timedelta(days=420)))
        f,t=q.candidates(p);self.assertFalse(t['validated_gate']);self.assertFalse(t['blocks']['28']['supported'])

    def test_current_target_not_read_and_alpha_independent(self):
        class Poison(dict):
            def __getitem__(self,key):
                if key=='actual':raise AssertionError('current label read')
                return super().__getitem__(key)
        r=row();raw,trace=q.candidates(Poison(r))
        for alpha in (0.,.5,1.):
            p={'quarter_coefficients':{str(i):{m:{'alpha':alpha} for m in q.ORDER} for i in range(1,5)}}
            f=q.choices(Poison(r),p);self.assertEqual(q.candidates(Poison(r))[1],trace)
            self.assertAlmostEqual(math.fsum(f['validated_anchor']),182.+alpha*36.4)

    def test_current_closure_zero_and_current_support_required(self):
        r=row();r['open_mask'][0]=False;r['matched_mean28'][0]=0.
        f,t=q.candidates(r);self.assertTrue(all(v[0]==0. for v in f.values()))
        r=row();r['annual_input']['values'][-1]=None;r['annual_input']['observed'][-1]=False
        f,t=q.candidates(r);self.assertTrue(t['blocks']['14']['strict_improvement']);self.assertFalse(t['validated_gate'])

    def test_tampered_year_dates_and_foreign_metadata_rejected(self):
        r=row();r['reliability_input']['28']['end_exclusive']=r['origin']
        with self.assertRaises(ValueError):q.candidates(r)
        class Poison(dict):
            def __getitem__(self,key):
                if key=='past_original_quantity':raise AssertionError('quantity read before metadata')
                return super().__getitem__(key)
        with self.assertRaises(ValueError):q.candidates(Poison(store=31,origin='2014-06-18'))
        with self.assertRaises(ValueError):q.calibrate([{'store':6,'origin':'2015-01-01'}])

    def test_quarter_coefficients_do_not_share_a_stop(self):
        rows=[row(f'2014-{month:02d}-18',s) for month in (3,6,9,11) for s in q.FIT]
        for r in rows:
            if r['origin'].startswith('2014-03'):r['actual']=[12.]*14
        policy,journal=q.calibrate(rows)
        self.assertEqual(policy['quarter_coefficients']['1']['validated_anchor']['alpha'],0.)
        self.assertGreater(policy['quarter_coefficients']['2']['validated_anchor']['alpha'],0.)
        self.assertEqual(policy['quarter_coefficients']['2']['validated_anchor']['complete_windows'],10)

class NumericRegression(unittest.TestCase):
    def test_flat_zero_under_interval_keeps_positive_boundary(self):
        data=[(1302.4155199999996,-494.68321989463584),(253.,-348.5963213939981),(29.,14.40262773722634),(26.758500000000367,-186.86067607973428)]
        samples=[{'e':e,'D':d,'weight':.05} for e,d in data]
        upper=q.side_bound(samples,-1)
        self.assertAlmostEqual(upper,.14320027392270804,places=14)
        self.assertGreater(upper,0.)
        self.assertLessEqual(sum(.05*max(-(e+upper*d),0.) for e,d in data),1e-8)

if __name__=='__main__':unittest.main()
