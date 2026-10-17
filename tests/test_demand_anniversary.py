"""New fixed-calendar correction checks only."""
import datetime as dt
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from demand_anniversary import fit_anniversaries,correct_baseline


class AnniversaryTests(unittest.TestCase):
    def fixture(self,actuals=(0.,0.),baseline=100.):
        return [{'month_day':'01-01','rows':[{'store':s,'date':f'{year}-01-01','sales':value,
            'past_same_weekday_mean':baseline,'support':4} for s in (1,2,3) for year,value in zip((2014,2015),actuals)]}]

    def test_zero_observation_is_shrunk_without_asserting_closure(self):
        m=fit_anniversaries(self.fixture())
        p=correct_baseline(m,1,dt.date(2016,1,1),100.)
        self.assertEqual(p['prediction'],60.)
        self.assertEqual(p['support'],2)
        self.assertFalse(p['is_confirmed_closure'])

    def test_unobserved_anniversary_does_not_impute_zero(self):
        data=self.fixture(actuals=(None,None))
        m=fit_anniversaries(data);p=correct_baseline(m,1,dt.date(2016,1,1),100.)
        self.assertEqual(p['prediction'],100.)
        self.assertEqual(p['reason'],'insufficient_observed_anniversary_support')
        self.assertIsNone(correct_baseline(m,1,dt.date(2016,1,1),None)['prediction'])

    def test_future_poison_not_in_fit(self):
        data=self.fixture();before=fit_anniversaries(data)
        data[0]['rows'].append({'store':1,'date':'2016-01-01','sales':object(),'past_same_weekday_mean':object()})
        self.assertEqual(before,fit_anniversaries(data))

    def test_positive_correction_and_normal_day(self):
        m=fit_anniversaries(self.fixture(actuals=(200.,200.)))
        self.assertEqual(correct_baseline(m,1,dt.date(2016,1,1),100.)['prediction'],140.)
        self.assertEqual(correct_baseline(m,1,dt.date(2016,1,2),100.)['prediction'],100.)

    def test_duplicate_key_and_changed_cutoff_rejected(self):
        with self.assertRaises(ValueError):fit_anniversaries(self.fixture()*2)
        with self.assertRaises(ValueError):fit_anniversaries(self.fixture(),cutoff=dt.date(2017,1,1))


if __name__=='__main__':unittest.main(verbosity=2)
