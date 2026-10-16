"""Only new r2 metric/launch/freeze guards. No model fit or real test labels."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

from metropt_multiday import ROOT, Files, pinball_score
from metropt_multiday_run import authorize
from metropt_multiday_score import describe, finite_shape, freeze_gate
import metropt_multiday_slot
sys.path.insert(0,str(ROOT/'tools'))
from macos_demand_runtime import MacCheckpoint


class Guards(unittest.TestCase):
    def test_fixed_config_is_not_training_or_scoring_permission(self):
        for phase in ('M1-train-predict','M1-score'):
            with self.assertRaises(PermissionError):authorize(ROOT/'examples/configs/metropt-macos-multiday-20261016.json',phase)

    def test_incomplete_or_duplicate_campaign_never_gets_labels(self):
        with self.assertRaises(ValueError):freeze_gate([],Path('not-opened'),None)
        with self.assertRaises(ValueError):freeze_gate(['same']*3,Path('not-opened'),None)
        with tempfile.TemporaryDirectory() as temp:
            temp=Path(temp);dataset=temp/'data';dataset.mkdir();(dataset/'root-closed.json').write_text('{}')
            roots=[]
            for i in range(3):
                out=Files(temp/str(i));out.close('incomplete');roots.append(out.root)
            with self.assertRaisesRegex(ValueError,'incomplete'):freeze_gate(roots,dataset,None)

    def test_day_equal_reduction_is_not_window_weighted(self):
        keys=[('2020-01-01',128),('2020-01-02',128),('2020-01-02',160)]
        actual=[[[0.0]*32 for _ in range(3)] for _ in keys]
        predictions=[[[[x,x,x] for _ in range(32)] for _ in range(3)] for x in (1.,3.,3.)]
        self.assertAlmostEqual(pinball_score(predictions,actual,keys,[1.,1.,1.]),1.)
        metrics=describe(predictions,actual,keys,[1.,1.,1.])
        for target in metrics['targets']:
            self.assertEqual(target['mae'],2.)
            self.assertEqual(target['lower_miss_rate'],1.)
            self.assertEqual(target['coverage80'],0.)
            self.assertEqual(target['width80'],0.)
        self.assertAlmostEqual(metrics['fixed_scale_wis'],2.)

    def test_interval_endpoints_and_units(self):
        keys=[('2020-01-01',128)];actual=[[[0.]*32,[1.]*32,[10.]*32]]
        predictions=[[[[0.,0.,1.] for _ in range(32)],[[0.,1.,1.] for _ in range(32)],[[10.,10.,11.] for _ in range(32)]]]
        metrics=describe(predictions,actual,keys,[1.,2.,10.])
        for target in metrics['targets']:
            self.assertEqual(target['mae'],0.);self.assertEqual(target['coverage80'],1.)
            self.assertEqual(target['lower_miss_rate'],0.);self.assertEqual(target['upper_miss_rate'],0.)

    def test_saved_prediction_shape_and_nonfinite_rejected(self):
        with self.assertRaises(ValueError):finite_shape([1.,2.],[3])
        with self.assertRaises(ValueError):finite_shape([float('nan')],[1])

    def test_imports_never_load_training_backend(self):
        self.assertNotIn('torch',sys.modules)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    files=Files(a.output);check=MacCheckpoint(seconds=870);status='failed'
    try:
        files.sources([Path(__file__),Path(__file__).with_name('metropt_multiday.py'),Path(__file__).with_name('metropt_multiday_run.py'),
                       Path(__file__).with_name('metropt_multiday_score.py'),Path(__file__).with_name('metropt_multiday_slot.py')])
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Guards))
        files.json('checks.json',{'tests':result.testsRun,'failures':result.failures,'errors':result.errors,'successful':result.wasSuccessful(),
                   'synthetic_labels_only':True,'real_test_labels_read':False,'model_forward_calls':0,'optimizer_updates':0,'resources':check.check()})
        if not result.wasSuccessful():raise SystemExit(1)
        status='complete'
    finally:files.close(status)
