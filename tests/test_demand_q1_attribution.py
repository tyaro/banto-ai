import datetime as dt,sys,unittest
from fractions import Fraction as F
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import demand_q1_attribution as m
from demand_bounded_metrics import Arithmetic,score_group,S

class AttributionTests(unittest.TestCase):
    def test_gross_not_net_denominator(self):
        a=Arithmetic();e={'a':m.components([F(2),F(-1)],a),'b':m.components([F(1),F(-2)],a)};r=m.concentration(e,a)
        self.assertEqual(r['top1']['entities'],['a']);self.assertEqual(F(r['top1']['share_lower']),F(2,3));self.assertEqual(r['top3']['share_display'],1.)
    def test_gross_zero_and_tie(self):
        a=Arithmetic();self.assertEqual(m.concentration({'a':m.components([F(0)],a)},a)['status'],'no_positive_contribution')
        r=m.concentration({'a':m.components([F(1)],a),'b':m.components([F(1)],a)},a);self.assertEqual(r['top1']['status'],'rank_unresolved_or_tied')
    def test_window_weights_match_daily_support_and_identity(self):
        origins=['2014-01-01','2014-01-15','2014-01-29','2014-02-12','2014-02-26','2014-03-12','2014-03-26'];ff=[];ll={};rows=[]
        for s in m.FIT:
            for i,o in enumerate(origins):
                mask=[str(dt.date.fromisoformat(o)+dt.timedelta(days=j))[5:] not in ('01-01','12-25') for j in range(14)]
                b=[10. if x else 0. for x in mask];c=[str(10+(1 if i>=2 else 0)) if x else '0' for x in mask];key=str(s)+'/'+o
                f={'key':key,'store':s,'origin':o,'scale':10.,'baseline':b,'candidate_daily_exact':c,'baseline_total':str(F(sum(b))),'candidate_total':str(sum(map(F,c))),'assumed_open_mask':mask,'features':None if i<2 else [1.,0.,0.]}
                ll[key]={'observed':b,'assumed_missing_zero':b};ff.append(f);rows.append({'forecast':f,**ll[key]})
        saved=score_group(rows,'observed',Arithmetic());r=m.diagnose(ff,ll,'Q1_all','observed',saved,Arithmetic())
        self.assertEqual(r['store_support']['6']['quantity_MSE'],97)
        self.assertEqual(r['metrics']['total_MSE']['total']['positive_windows'],50)
        self.assertEqual(r['rows'][2]['canonical']['MSE_worsening_type'],'same_side_away')
        self.assertEqual(r['metrics']['quantity_MSE']['atomic_reconciliation'],saved['paired']['macro']['quantity_MSE'])

if __name__=='__main__':unittest.main()
