import datetime as dt
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from demand_training_adequacy import split_keys,fit_scales,EarlyStopper


class NewAdequacyChecks(unittest.TestCase):
    def test_labels_cannot_cross_temporal_boundary(self):
        rows=[(1,'2014-06-17'),(1,'2014-06-18'),(1,'2014-07-01')]
        value=split_keys(rows)
        self.assertEqual(value['train'],rows[:1]);self.assertEqual(value['crossing'],rows[1:2]);self.assertEqual(value['validation'],rows[2:])
        with self.assertRaises(ValueError):split_keys(rows+rows[:1])

    def test_validation_quantity_not_read_for_scale(self):
        class Future(dict):
            def __getitem__(self,key):
                if key in ('sales','observed'):raise AssertionError('validation payload accessed')
                return super().__getitem__(key)
        rows=[{'store_nbr':'1','date':'2014-06-29','sales':'0','observed':'1'},
              {'store_nbr':'1','date':'2014-06-30','sales':'10','observed':'1'},
              Future(store_nbr='1',date='2014-07-01')]
        result=fit_scales(rows,[1],dt.date(2014,6,29),dt.date(2014,7,1))['1']
        self.assertEqual(result['scale'],5);self.assertEqual(result['observed_days'],2)

    def test_warmup_patience_and_no_reentry(self):
        policy=EarlyStopper(interval=1,warmup=3,patience=2,min_relative=.01)
        for step in range(4):self.assertFalse(policy.observe(step,1.)['stop'])
        self.assertTrue(policy.observe(4,1.)['stop']);self.assertEqual(policy.best_step,0)
        with self.assertRaises(ValueError):policy.observe(5,1.)

    def test_small_best_and_meaningful_improvement_are_separate(self):
        policy=EarlyStopper(interval=1,warmup=1,patience=3,min_relative=.01)
        policy.observe(0,1.)
        value=policy.observe(1,.995)
        self.assertTrue(value['new_best']);self.assertFalse(value['meaningful_improvement']);self.assertEqual(value['bad_checkpoints'],1)
        value=policy.observe(2,.98);self.assertTrue(value['meaningful_improvement']);self.assertEqual(value['bad_checkpoints'],0)
        with self.assertRaises(ValueError):policy.observe(3,float('nan'))
        self.assertEqual(policy.last_step,2)


if __name__=='__main__':unittest.main(verbosity=2)
