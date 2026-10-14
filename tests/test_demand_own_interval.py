from pathlib import Path
import datetime as dt
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from demand_own_interval import read_prefix,own_window,select_own,choose_calibration


class OwnIntervalChecks(unittest.TestCase):
    def test_prefix_store_and_time_guard_before_numbers(self):
        raw=b'store_nbr,date,source_id,sales,observed\n4,2015-01-01,a,0,1\n4,2015-01-02,,,0\n4,2016-01-01,x,future,invalid\n8,2015-01-01,x,foreign,invalid\n'
        h=read_prefix(raw,(4,))[4]
        self.assertEqual(h,{dt.date(2015,1,1):0.,dt.date(2015,1,2):None})

    def test_minimum_support_and_shared_fallback(self):
        shared={'q10':-.1,'q90':.1}
        rows=[{'store':4,'available':True,'past_positive':True,'zero_context':False,'y':float(k)} for k in range(20)]
        insufficient=choose_calibration(rows[:19],4,shared)
        self.assertEqual(insufficient['interval_source'],'shared_fallback')
        self.assertIsNone(insufficient['own']['q10'])
        self.assertEqual(insufficient['selected'],shared)
        enough=choose_calibration(rows,4,shared)
        self.assertEqual(enough['interval_source'],'own_history')
        self.assertEqual((enough['own']['q10'],enough['own']['q90']),(1.,17.))
        self.assertFalse(enough['zero_shot_claim'])

    def test_pool_condition_ignores_future_zero_label(self):
        class Poison:
            def __bool__(self):raise AssertionError('future label inspected')
        rows=[{'store':4,'available':True,'past_positive':True,'actual_zero':Poison()},
              {'store':4,'available':True,'past_positive':False,'actual_zero':Poison()}]
        self.assertEqual(len(select_own(rows,4)),1)

    def test_foreign_store_and_future_label_rejected(self):
        with self.assertRaisesRegex(ValueError,'another store'):
            select_own([{'store':8}],4)
        class NoAccess(dict):
            def get(self,*args):raise AssertionError('future history accessed')
        with self.assertRaisesRegex(ValueError,'before 2016'):
            own_window(NoAccess(),4,dt.date(2015,12,20),1.)


if __name__=='__main__':unittest.main()
