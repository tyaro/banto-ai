import datetime as dt,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import demand_store_characteristics as m

class ProfileTests(unittest.TestCase):
    def records(self,start='2013-10-01',n=56,value=lambda d:5.):
        first=dt.date.fromisoformat(start)
        return [{'date':str(first+dt.timedelta(days=i)),'available_at':str(first+dt.timedelta(days=i+1)),'value':value(first+dt.timedelta(days=i))} for i in range(n)]
    def test_new_entry_and_weekday_variance_weights(self):
        r=self.records(value=lambda d:float(d.weekday()+1));p=m.profile(r,'2013-12-01')
        self.assertEqual(m.__name__,'demand_store_characteristics');self.assertAlmostEqual(p['weekday_variance_share_in_sample'],1)
        self.assertEqual(p['weekday_adjusted_relative_variability'],0.)
    def test_zeros_missing_closure_separated(self):
        r=self.records('2013-01-01',10);r[0]['value']=0.;r[1]['value']=0.;r[2]['value']=None
        p=m.profile(r,'2013-02-01');self.assertEqual(p['counts']['raw_zero'],2);self.assertEqual(p['counts']['open_zero'],1)
        self.assertEqual(p['counts']['raw_missing'],1);self.assertEqual(p['counts']['open_missing'],1);self.assertEqual(p['counts']['closure_observed_zero'],1)
    def test_future_and_unavailable_rejected(self):
        for row in [{'date':'2014-01-01','available_at':'2014-01-02','value':1.},{'date':'2013-12-31','available_at':'2014-01-02','value':1.}]:
            with self.assertRaises(ValueError):m.profile([row],'2014-01-01')
        with self.assertRaises(ValueError):m.profile([{'date':'2013-12-31','available_at':'2014-01-01','value':1.,'label':1}],'2014-01-01')
    def test_constant_zero_undefined(self):
        p=m.profile(self.records(value=lambda d:0.),'2013-12-01')
        self.assertIsNone(p['open_CV']);self.assertIsNone(p['calendar_lag7_correlation']);self.assertIsNone(p['recent28_previous28_mean_ratio_minus1'])
        p=m.profile(self.records(),'2013-12-01');self.assertEqual(p['open_CV'],0);self.assertIsNone(p['weekday_variance_share_in_sample'])
    def test_lag7_calendar_not_row_position(self):
        p=m.profile([{'date':d,'available_at':str(dt.date.fromisoformat(d)+dt.timedelta(days=1)),'value':v} for d,v in [('2013-01-02',1.),('2013-01-09',2.),('2013-01-16',3.)]],'2013-02-01')
        self.assertEqual(p['calendar_lag7_pairs'],2);self.assertAlmostEqual(p['calendar_lag7_correlation'],1)
    def test_snapshot_ignores_future_labels(self):
        r=self.records('2013-11-06');inp={'origin':'2014-01-01','past_dates':[v['date'] for v in r],'past_available_at':[v['available_at'] for v in r],'past_values':[v['value'] for v in r]}
        expected=m.snapshot_packet(inp);inp['future_label']=object();self.assertEqual(m.snapshot_packet(inp),expected)
    def test_selector_filters_before_quantity_decode(self):
        class Bomb:
            def __float__(self):raise AssertionError('forbidden quantity decoded')
        rows=[]
        for s in m.FIT:
            for i in range(365):rows.append({'store_nbr':str(s),'date':str(dt.date(2013,1,1)+dt.timedelta(days=i)),'sales':'1','observed':'1'})
        expected=m.select_2013(rows)
        rows.extend([{'store_nbr':'6','date':'2014-01-01','sales':Bomb(),'observed':'1'},{'store_nbr':'31','date':'2013-01-01','sales':Bomb(),'observed':'1'}])
        self.assertEqual(m.select_2013(rows),expected)

if __name__=='__main__':unittest.main()
