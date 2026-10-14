from pathlib import Path
import datetime as dt
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from demand_weekly_history import build_inputs,fit_scale

ORIGIN = dt.date(2015, 2, 1)


def history(levels):
    return {ORIGIN-dt.timedelta(days=56-k):float(levels[k//7]) for k in range(56)}


class WeeklyHistoryChecks(unittest.TestCase):
    def test_past_only_getters(self):
        class Guard(dict):
            def get(self, day, default=None):
                if day >= ORIGIN:
                    raise AssertionError('future label accessed')
                return super().get(day, default)
        result=build_inputs(Guard(history([100]*8)),ORIGIN,100)
        self.assertTrue(result['available'])
        self.assertEqual(result['past_end'],'2015-01-31')

    def test_same_baseline_x_distinct_older_trajectory(self):
        a=build_inputs(history([100]*8),ORIGIN,100)
        b=build_inputs(history([50,150,50,150,100,100,100,100]),ORIGIN,100)
        self.assertEqual((a['baseline'],a['old_x']),(b['baseline'],b['old_x']))
        self.assertEqual(a['features'],[0.]*8)
        self.assertEqual(b['features'],[-.5,.5,-.5,.5,0.,0.,0.,0.])
        self.assertEqual(b['old_x'],sum(b['features'][-2:])/2)

    def test_zero_missing_and_unsupported_scale(self):
        zero=build_inputs(history([0]*8),ORIGIN,100)
        self.assertEqual(zero['features'],[0.]*8)
        h=history([100]*8);h[ORIGIN-dt.timedelta(days=56)]=None
        missing=build_inputs(h,ORIGIN,100)
        self.assertIsNone(missing['features'])
        self.assertEqual(missing['weeks'][0]['observed_days'],6)
        self.assertIsNone(missing['weeks'][0]['total'])
        self.assertEqual(missing['fallback'],'baseline')
        self.assertEqual(missing['old_x'],0.)
        self.assertFalse(build_inputs({},ORIGIN,100)['baseline_available'])
        self.assertIn('nonpositive_fit_scale',build_inputs(history([100]*8),ORIGIN,0)['reasons'])

    def test_unit_conversion(self):
        a=build_inputs(history([50,150,50,150,100,80,120,110]),ORIGIN,100)
        b=build_inputs(history([500,1500,500,1500,1000,800,1200,1100]),ORIGIN,1000)
        for x,y in zip(a['features'],b['features']):self.assertAlmostEqual(x,y)
        self.assertAlmostEqual(b['baseline'],10*a['baseline'])

    def test_scale_cutoff_before_future_payload(self):
        class HeadersOnly(dict):
            def __getitem__(self,key):
                if key not in ('store','date'):
                    raise AssertionError('excluded quantity accessed')
                return super().__getitem__(key)
        rows=[{'store':6,'date':'2014-01-01','observed':True,'quantity':0},
              {'store':6,'date':'2014-01-02','observed':True,'quantity':100},
              {'store':6,'date':'2014-01-03','observed':False,'quantity':None},
              HeadersOnly(store=6,date='2015-01-01'),HeadersOnly(store=7,date='2014-01-01')]
        result=fit_scale(rows,6)
        self.assertEqual((result['observed_days'],result['mean']),(2,50.))
        self.assertFalse(fit_scale([],6)['available'])


if __name__=='__main__':unittest.main()
