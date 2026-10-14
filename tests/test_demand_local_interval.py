from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from demand_local_interval import local_scale,restore


class LocalIntervalChecks(unittest.TestCase):
    def test_unit_scaling_invariance(self):
        cal={'q10':-.1,'q90':.2}
        original=restore(100.,10.,cal);changed=restore(1000.,100.,cal)
        self.assertEqual((original['lower'],original['upper']),(90.,120.))
        for key in ('point','lower','upper','width'):
            self.assertAlmostEqual(changed[key],10*original[key])
        residual=(120.-100.)/local_scale(100.,10.)['scale']
        changed_residual=(1200.-1000.)/local_scale(1000.,100.)['scale']
        self.assertEqual(residual,changed_residual)

    def test_zero_floor_does_not_change_mean(self):
        value=restore(0.,10.,{'q10':-.1,'q90':.2})
        self.assertTrue(value['local_scale']['floor_active'])
        self.assertAlmostEqual(value['local_scale']['scale'],1.4)
        self.assertEqual(value['point'],0.)
        self.assertEqual(value['lower'],0.)
        self.assertAlmostEqual(value['upper'],.28)
        with self.assertRaises(ValueError):local_scale(0.,0.)


if __name__=='__main__':unittest.main()
