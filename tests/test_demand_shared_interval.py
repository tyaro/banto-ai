from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from demand_shared_interval import select_pool,support,weighted_quantile,total_interval,assess,calibrate


class SharedIntervalChecks(unittest.TestCase):
    def test_weighted_quantile_boundaries(self):
        pairs=[(1.,1.),(2.,8.),(100.,1.)]
        self.assertEqual(weighted_quantile(pairs,.1),1.)
        self.assertEqual(weighted_quantile(pairs,.9),2.)
        self.assertEqual(weighted_quantile(pairs,1.),100.)
        with self.assertRaises(ValueError):weighted_quantile([(1.,0.)],.1)

    def test_total_restore_without_point_clip(self):
        value=total_interval(0.,1.,{'q10':1.,'q90':2.})
        self.assertEqual((value['point'],value['lower'],value['upper']),(0.,14.,28.))
        self.assertFalse(value['point_inside'])
        value=total_interval(10.,1.,{'q10':-1.,'q90':1.})
        self.assertEqual((value['lower'],value['upper']),(0.,24.))

    def test_past_selection_does_not_inspect_labels_or_reweight(self):
        class Poison:
            def __bool__(self):raise AssertionError('future label inspected')
        rows=[{'store':1,'weight':2.,'zero_context':True,'actual_zero':Poison(),'y':Poison()},
              {'store':2,'weight':.5,'zero_context':False,'actual_zero':Poison(),'y':Poison()},
              {'store':2,'weight':.5,'zero_context':False,'actual_zero':Poison(),'y':Poison()}]
        selected=select_pool(rows,'past_positive')
        self.assertEqual(support(selected)['weight_sum'],1.)
        self.assertEqual(support(selected)['store_weight_sums'],{2:1.})

    def test_empty_pool_and_missing_actual_remain_null(self):
        c=calibrate([]);self.assertIsNone(c['q10']);self.assertEqual(c['reason'],'empty_pool')
        value=total_interval(0.,1.,c)
        self.assertIsNone(value['width']);self.assertIsNone(assess(value,0.))
        self.assertIsNone(assess({'lower':0.,'upper':10.},None))

    def test_interval_score_by_hand(self):
        value={'lower':10.,'upper':20.}
        self.assertEqual(assess(value,15.)['interval_score'],10.)
        self.assertEqual(assess(value,5.)['interval_score'],60.)
        self.assertEqual(assess(value,25.)['interval_score'],60.)
        self.assertTrue(assess(value,20.)['covered'])


if __name__=='__main__':unittest.main()
