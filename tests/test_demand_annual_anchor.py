import copy
import datetime as dt
import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import demand_annual_anchor as q
from tests.test_demand_adaptive_consensus import row

def example(origin='2014-06-18',ratio=2.):
    r=row(origin);o=dt.date.fromisoformat(origin);a=o-dt.timedelta(days=364)
    r['annual_input']={'first':str(a-dt.timedelta(days=28)),'annual_issue':str(a),'end_exclusive':str(a+dt.timedelta(days=14)),
                       'values':[10.]*28+[10.*ratio]*14,'observed':[True]*42}
    return r

class AnchorChecks(unittest.TestCase):
    def test_scalar_ratio_and_cap_are_separate(self):
        r=example();f,t=q.candidates(r)
        self.assertEqual(t['ratio'],2.);self.assertEqual(f['annual_anchor'],[26.]*14)
        self.assertAlmostEqual(math.fsum(f['anchor_cap']),224.)
        self.assertAlmostEqual(t['cap_difference'],42.)
        r=example(ratio=1.1);f,t=q.candidates(r)
        self.assertAlmostEqual(t['cap_difference'],18.2)
        self.assertAlmostEqual(math.fsum(f['anchor_cap']),200.2)

    def test_direction_veto_rejects_old_positive(self):
        r=example(ratio=.5);f,t=q.candidates(r)
        self.assertGreater(t['old_raw_difference'],0);self.assertLess(t['annual_difference'],0)
        self.assertFalse(t['direction_agrees']);self.assertEqual(f['anchor_cap'],r['matched_mean28'])

    def test_missing_or_holiday_mismatch_falls_back_entire_window(self):
        r=example();r['annual_input']['values'][-1]=None;r['annual_input']['observed'][-1]=False
        f,t=q.candidates(r);self.assertIn('annual_target_missing',t['reasons']);self.assertEqual(f['annual_anchor'],r['matched_mean28'])
        r=example('2014-12-24');f,t=q.candidates(r)
        self.assertIn('annual_target_closure_mismatch',t['reasons']);self.assertEqual(f['anchor_cap'],r['matched_mean28'])

    def test_same_positions_for_ratio_and_current_closure_zero(self):
        r=example();r['open_mask'][0]=False;r['matched_mean28'][0]=r['raw_prediction'][0]=0.
        r['annual_input']['values'][28]=None;r['annual_input']['observed'][28]=False
        f,t=q.candidates(r);self.assertTrue(t['supported']);self.assertEqual(t['numerator'],260.);self.assertEqual(t['denominator'],130.)
        self.assertTrue(all(values[0]==0. for values in f.values()))

    def test_reference_support_and_zero_denominator(self):
        r=example();r['annual_input']['values'][:28]=[0.]*28
        f,t=q.candidates(r);self.assertIn('zero_annual_reference',t['reasons']);self.assertEqual(f['annual_anchor'],r['matched_mean28'])
        r=example();r['annual_input']['values'][:14]=[None]*14;r['annual_input']['observed'][:14]=[False]*14
        f,t=q.candidates(r);self.assertIn('annual_weekday_support',t['reasons'])

    def test_observed_zero_is_not_missing(self):
        r=example();r['annual_input']['values'][28]=0.
        f,t=q.candidates(r);self.assertTrue(t['supported']);self.assertEqual(t['numerator'],260.)
        self.assertEqual(r['annual_input']['observed'][28],True)

    def test_year_offset_and_2012_never_requested(self):
        class Checked(dict):
            def get(self,day):
                if not dt.date(2013,1,1)<=day<dt.date(2015,1,1):raise AssertionError('outside source')
                return 10.
        r=q.attach_annual(row('2014-01-01'),{6:Checked()});f,t=q.candidates(r)
        self.assertEqual(t['annual_input']['annual_issue'],'2013-01-02')
        self.assertIn('annual_weekday_support',t['reasons']);self.assertEqual(f['annual_anchor'],r['matched_mean28'])

    def test_future_label_not_read_and_tampered_dates_rejected(self):
        class Poison(dict):
            def __getitem__(self,k):
                if k=='actual':raise AssertionError('current target read')
                return super().__getitem__(k)
        r=example();self.assertEqual(q.candidates(Poison(r)),q.candidates(r))
        r['annual_input']['end_exclusive']=r['origin']
        with self.assertRaises(ValueError):q.candidates(r)
        with self.assertRaises(ValueError):q.attach_annual({'store':31,'origin':'2014-06-18'},{})

    def test_high_precision_flat_side_boundary(self):
        samples=[{'weight':.1,'e':-14.,'D':28.} for _ in range(10)]
        self.assertAlmostEqual(q.side_bound(samples,1),.5)
        self.assertGreater(q.side_bound(samples,1),0.)
        self.assertAlmostEqual(q.side_bound(samples,-1),1.)

    def test_calibration_before_metadata_and_quarter_independent_selection(self):
        class Poison(dict):
            def __getitem__(self,k):
                if k=='actual':raise AssertionError('future target read')
                return super().__getitem__(k)
        with self.assertRaises(ValueError):q.calibrate([Poison(store=6,origin='2015-01-01')])
        def score(mse=1.,over=1.):return {'macro':{'total':mse},'shortfall':{'macro':{'under':1.,'over':over}}}
        groups={f'normal_Q{i}':{mode:{m:score() for m in q.ORDER} for mode in ('observed','assumed_missing_zero')} for i in range(1,5)}
        for mode in ('observed','assumed_missing_zero'):groups['normal_Q2'][mode]['annual_anchor']=score(.9)
        groups['normal_Q4']['observed']['annual_anchor']=score(.8,2.)
        self.assertEqual(q.choose(groups)['selected_by_quarter'],{'1':'matched_mean28','2':'annual_anchor','3':'matched_mean28','4':'matched_mean28'})

if __name__=='__main__':unittest.main()
