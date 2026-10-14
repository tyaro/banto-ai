from pathlib import Path
import datetime as dt,math,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from demand_statistical_overlay import describe_history,combine_saved_baseline,_summarize
ORIGIN=dt.date(2025,3,1)


def history(value=100.):
    return {ORIGIN-dt.timedelta(days=k):value for k in range(1,57)}


class OverlayChecks(unittest.TestCase):
    def test_pure_weekday_pattern_has_zero_errors_and_no_certainty_claim(self):
        h={d:20.+10*d.weekday() for d in history()}
        p=describe_history(h,ORIGIN)
        self.assertEqual(p['support'],28);self.assertEqual(p['sample_sigma'],0)
        self.assertEqual(p['EMA7'],0);self.assertFalse(p['coverage_guaranteed'])
        b=[40.]*14;r=combine_saved_baseline(b,p)
        self.assertEqual(r['blend_daily'],b);self.assertIsNone(r['prediction_intervals'])

    def test_constant_bias_is_not_sigma_and_future_error_rejected(self):
        rows=[{'date':str(ORIGIN-dt.timedelta(days=k)),'error':10.} for k in range(20,0,-1)]
        p=_summarize(rows,ORIGIN)
        self.assertEqual((p['mean_error'],p['sample_sigma'],p['RMSE']),(10.,0.,10.))
        with self.assertRaisesRegex(ValueError,'past'):
            _summarize([{'date':str(ORIGIN),'error':1}],ORIGIN)

    def test_shift_and_fast_slow_response(self):
        h=history()
        for k in range(1,8):h[ORIGIN-dt.timedelta(days=k)]=120.
        p=describe_history(h,ORIGIN)
        self.assertGreater(p['EMA7'],p['EMA28']);self.assertGreater(p['sample_sigma'],0)
        self.assertGreater(p['fast_minus_slow'],0)
        r=combine_saved_baseline([100.]*14,p)
        self.assertGreater(r['blend_total'],1400);self.assertLess(r['blend_total'],r['ema_total'])

    def test_prefix_only_and_missing_support_fallback(self):
        class Prefix(dict):
            def get(self,d):
                if d>=ORIGIN:raise AssertionError('future actual accessed')
                return super().get(d)
        h=Prefix(history(0.))
        p=describe_history(h,ORIGIN)
        self.assertTrue(p['available']);self.assertEqual(p['sample_sigma'],0)
        for k in range(1,12):h[ORIGIN-dt.timedelta(days=k)]=None
        p=describe_history(h,ORIGIN);self.assertFalse(p['available']);self.assertIsNone(p['sample_sigma'])
        self.assertTrue(any(r['error'] is None for r in p['residual_ledger']))
        r=combine_saved_baseline([100.]*14,p)
        self.assertEqual(r['blend_daily'],[100.]*14);self.assertTrue(r['fallback'])

    def test_unit_change_preserves_formula(self):
        h=history()
        for k in range(1,8):h[ORIGIN-dt.timedelta(days=k)]+=20.
        a=describe_history(h,ORIGIN);b=describe_history({d:v*10 for d,v in h.items()},ORIGIN)
        for field in ('mean_error','sample_sigma','RMSE','EMA7','EMA28'):
            self.assertAlmostEqual(b[field],10*a[field])
        x=combine_saved_baseline([100.]*14,a);y=combine_saved_baseline([1000.]*14,b)
        self.assertAlmostEqual(y['blend_total'],10*x['blend_total'])

    def test_nonnegative_total_integrity_and_null_baseline(self):
        p={'available':True,'EMA7':-200.,'reason':None}
        r=combine_saved_baseline([100.]*14,p)
        self.assertEqual(r['ema_daily'],[0.]*14);self.assertEqual(r['blend_daily'],[50.]*14)
        self.assertEqual(r['blend_total'],sum(r['blend_daily']))
        self.assertFalse(r['sigma_used_to_change_point'])
        self.assertFalse(combine_saved_baseline([None]*14,p)['available'])
        with self.assertRaises(ValueError):combine_saved_baseline([float('nan')]*14,p)


if __name__=='__main__':unittest.main()
