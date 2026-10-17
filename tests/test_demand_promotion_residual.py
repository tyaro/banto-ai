from pathlib import Path
import math,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from demand_promotion_residual import fit,predict


class ResidualChecks(unittest.TestCase):
    def test_known_ridge_and_negative_direction(self):
        rows=[{'x':float(k),'y':3-2*k,'origin':str(k)} for k in range(10)]
        m=fit(rows)
        self.assertAlmostEqual(m['intercept'], -6)
        self.assertAlmostEqual(m['scale'],math.sqrt(8.25))
        self.assertAlmostEqual(m['slope'],-2*math.sqrt(8.25)*10/11)
        self.assertEqual(m['ridge'],1)

    def test_constant_feature_and_support(self):
        rows=[{'x':0.,'y':float(k),'origin':str(k)} for k in range(10)]
        m=fit(rows);self.assertEqual(m['slope'],0.)
        self.assertEqual(m['scale'],0.)
        with self.assertRaises(ValueError):fit(rows[:9])

    def test_missing_fallback_and_nonnegative_boundary(self):
        m={'center':2.,'scale':1.,'intercept':-1.,'slope':2.}
        r=predict(m,10.,1.,None)
        self.assertEqual((r['intercept'],r['promotion']),(0.,0.))
        self.assertFalse(r['feature_supported'])
        r=predict(m,30.,1.,None)
        self.assertEqual((r['intercept'],r['promotion']),(16.,16.))


if __name__=='__main__':unittest.main()
