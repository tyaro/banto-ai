from pathlib import Path
import datetime as dt
import math,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from demand_public_calendar import COLUMNS,build_inputs,calendar,fit_support
ENABLED=(True,)*56


class PublicCalendarChecks(unittest.TestCase):
    def test_year_boundary_and_leap_day(self):
        row=calendar(dt.date(2014,12,30),'pre_post',ENABLED)
        self.assertEqual(row[4+COLUMNS.index(('01-01',-2))],1)
        leap=calendar(dt.date(2016,3,1),'pre_post',ENABLED)
        self.assertAlmostEqual(leap[2],math.sin(2*math.pi*60/366))

    def test_control_same_shape_baseline_statistics_and_center(self):
        origin=dt.date(2014,5,1)
        history={origin-dt.timedelta(days=k):float(k) for k in range(1,57)}
        a=build_inputs(history,origin,100,'on_day',ENABLED)
        b=build_inputs(history,origin,100,'pre_post',ENABLED)
        for field in ('values','observed','normalized_values','context_statistics','baseline'):
            self.assertEqual(a[field],b[field])
        self.assertEqual(len(a['future_calendar'][0]),60)
        for ra,rb in zip(a['future_calendar'],b['future_calendar']):
            self.assertEqual(ra[:4],rb[:4])
            for i,(_,offset) in enumerate(COLUMNS):
                self.assertEqual(ra[4+i],rb[4+i] if offset==0 else 0)
        self.assertNotEqual(a['future_calendar'],b['future_calendar'])

    def test_future_getter_zero_and_missing(self):
        origin=dt.date(2014,2,1)
        class Prefix(dict):
            def get(self,d):
                if d>=origin:raise AssertionError('future quantity')
                return super().get(d)
        history=Prefix({origin-dt.timedelta(days=k):0. for k in range(1,57)})
        history[origin-dt.timedelta(days=1)]=None
        row=build_inputs(history,origin,100,'pre_post',ENABLED)
        self.assertTrue(row['available']);self.assertEqual(row['baseline'],[0.]*14)
        self.assertFalse(row['observed'][-1]);self.assertTrue(row['observed'][-2])
        self.assertEqual(row['context_statistics'],[0.,0.])

    def test_quantity_units_support_and_unknown_operating_meaning(self):
        origin=dt.date(2014,5,1)
        history={origin-dt.timedelta(days=k):float(k) for k in range(1,57)}
        a=build_inputs(history,origin,100,'pre_post',ENABLED)
        b=build_inputs({k:v*10 for k,v in history.items()},origin,1000,'pre_post',ENABLED)
        self.assertEqual(a['normalized_values'],b['normalized_values'])
        for x,y in zip(a['context_statistics'],b['context_statistics']):self.assertAlmostEqual(x,y)
        self.assertEqual(a['sales_estimand'],'observed_sales_mean')
        self.assertFalse(a['nominal_closure_mask_applied']);self.assertFalse(a['period_length_supplied'])
        empty=build_inputs({},origin,100,'on_day',ENABLED)
        self.assertFalse(empty['available']);self.assertIn('weekday_support',empty['reasons'])
        self.assertFalse(build_inputs(history,origin,0,'on_day',ENABLED)['available'])

    def test_fit_support_distinct_days_missing_and_event_years(self):
        origin=dt.date(2014,12,20)
        keys=[(6,origin),(6,origin+dt.timedelta(days=1)),(7,origin)]
        observed={(s,origin+dt.timedelta(days=k)):k!=5 for s in (6,7) for k in range(15)}
        r=fit_support(keys,observed,dt.date(2015,2,1))
        center=r['channels'][COLUMNS.index(('12-25',0))]
        before=r['channels'][COLUMNS.index(('12-25',-1))]
        self.assertEqual(center['distinct_store_dates'],0);self.assertFalse(center['enabled'])
        self.assertEqual(before['distinct_store_dates'],2);self.assertEqual(before['event_years'],[2014])
        cal=calendar(dt.date(2014,12,25),'pre_post',r['enabled'])
        self.assertEqual(cal[4+COLUMNS.index(('12-25',0))],0)

    def test_fit_cutoff_before_mask_and_duplicate_rejection(self):
        class Unavailable:
            def get(self,key):raise AssertionError('future mask payload accessed')
        with self.assertRaisesRegex(ValueError,'cutoff'):
            fit_support([(6,dt.date(2014,12,25))],Unavailable())
        origin=dt.date(2014,5,1);mask={(6,origin+dt.timedelta(days=k)):True for k in range(14)}
        with self.assertRaisesRegex(ValueError,'duplicate'):
            fit_support([(6,origin),(6,origin)],mask)


if __name__=='__main__':unittest.main()
