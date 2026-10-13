"""Only new recent-total and retained-shape cases."""
from pathlib import Path
import datetime as dt,math,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from demand_total import recent_fourteen_total,rescale_retained_shape


class TotalTests(unittest.TestCase):
    origin=dt.date(2020,2,1)
    def history(self):return {self.origin-dt.timedelta(days=i):float(i) for i in range(1,16)}
    def test_hand_total_and_past_boundary(self):
        p=recent_fourteen_total(self.history(),self.origin)
        self.assertEqual(p['total'],105.)
        self.assertEqual(p['support'],14)
        self.assertNotIn(str(self.origin-dt.timedelta(days=15)),p['source_dates'])
    def test_future_poison_cannot_change_total_or_binding(self):
        h=self.history();before=recent_fourteen_total(h,self.origin)
        h[self.origin]=object();h[self.origin+dt.timedelta(days=14)]=object()
        self.assertEqual(before,recent_fourteen_total(h,self.origin))
    def test_zero_retained_missing_excluded_and_support_gate(self):
        h={self.origin-dt.timedelta(days=i):1. for i in range(1,15)}
        h[self.origin-dt.timedelta(days=1)]=None;h[self.origin-dt.timedelta(days=2)]=None
        h[self.origin-dt.timedelta(days=3)]=0.
        self.assertAlmostEqual(recent_fourteen_total(h,self.origin)['total'],14*11/12)
        h[self.origin-dt.timedelta(days=4)]=None
        self.assertIsNone(recent_fourteen_total(h,self.origin)['total'])
    def test_requested_total_changes_level_but_preserves_shape(self):
        shape=list(range(1,15));p=rescale_retained_shape(shape,210.)
        self.assertEqual(p['predictions'],[2.*v for v in shape])
        self.assertEqual(math.fsum(p['predictions']),210.)
    def test_zero_unknown_and_invalid_profiles(self):
        self.assertEqual(rescale_retained_shape([1.]*14,0.)['predictions'],[0.]*14)
        self.assertEqual(rescale_retained_shape([0.]*14,1.)['reason'],'zero_shape_with_positive_total')
        self.assertIsNone(rescale_retained_shape([None]+[1.]*13,1.)['predicted_total'])
        with self.assertRaises(ValueError):rescale_retained_shape([1.]*13,1.)
        with self.assertRaises(ValueError):rescale_retained_shape([1.]*14,-1.)


if __name__=='__main__':unittest.main(verbosity=2)
