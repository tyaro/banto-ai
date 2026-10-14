from pathlib import Path
import datetime as dt
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from demand_weekly_ridge import fit,predict


def row(store,k,features,y):
    return {'store':store,'origin':str(dt.date(2014,1,1)+dt.timedelta(days=14*k)),'features':features,'y':y}


class WeeklyRidgeChecks(unittest.TestCase):
    def test_known_collinear_ridge_solution(self):
        rows=[row(s,k,[(-1.)**k]*2+[7.]*6,2+3*((-1.)**k)) for s in (6,7) for k in range(10)]
        model=fit(rows,(6,7))
        self.assertAlmostEqual(model['intercept'],2.)
        for b in model['slopes'][:2]:self.assertAlmostEqual(b,60/41)
        self.assertEqual(model['slopes'][2:],[0.]*6)
        self.assertLess(model['normal_equation_max_abs_residual'],1e-10)

    def test_store_equal_weight_and_constant_columns(self):
        rows=[row(6,k,[3.]*8,0.) for k in range(10)]+[row(7,k,[3.]*8,10.) for k in range(20)]
        model=fit(rows,(6,7))
        self.assertEqual(model['store_weight_sums'],{6:15.,7:15.})
        self.assertEqual(model['intercept'],5.)
        self.assertEqual(model['slopes'],[0.]*8)

    def test_fit_store_and_time_guards_before_payload(self):
        with self.assertRaisesRegex(ValueError,'declared training stores'):fit([{'store':21}],(6,7))
        with self.assertRaisesRegex(ValueError,'before 2015'):fit([{'store':6,'origin':'2014-12-20'}],(6,))

    def test_missing_features_and_zero_scale_baseline_fallback(self):
        model={'intercept':1.}
        self.assertEqual(predict(model,100.,2.,None)['weekly'],100.)
        class Poison:
            def __len__(self):raise AssertionError('zero-scale features inspected')
        result=predict({},100.,0.,Poison())
        self.assertEqual((result['baseline'],result['intercept'],result['weekly']),(100.,100.,100.))
        self.assertEqual(result['reason'],'unsupported_zero_fit_scale')

    def test_nonnegative_restore_and_unavailable_null(self):
        model={'intercept':-100.,'center':[0.]*8,'scale':[1.]*8,'slopes':[0.]*8}
        result=predict(model,100.,1.,[0.]*8)
        self.assertEqual((result['intercept'],result['weekly']),(0.,0.))
        missing=predict({},None,0.,None)
        self.assertFalse(missing['available'])
        self.assertIsNone(missing['weekly'])


if __name__=='__main__':unittest.main()
