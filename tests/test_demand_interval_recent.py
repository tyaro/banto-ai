"""Only the new completed-window selection and sequential-calibration checks."""
from pathlib import Path
import datetime as dt,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from demand_interval_recent import calibrate_recent_completed


class RecentIntervalTests(unittest.TestCase):
    def records(self):
        return [{'target_end':str(dt.date(2016,1,14)+dt.timedelta(days=14*i)),
            'prediction':100.,'actual':100.+i} for i in range(25)]
    def test_only_latest_twenty_five_valid_completed_used(self):
        records=self.records()+[{'target_end':'2017-01-14','prediction':100.,'actual':200.}]
        model=calibrate_recent_completed(records,dt.date(2017,1,15))
        self.assertEqual(model['support'],25);self.assertEqual(model['eligible_count'],26)
        self.assertEqual(model['scores'][0]['target_end'],records[1]['target_end'])
        self.assertEqual(model['scores'][-1]['target_end'],'2017-01-14')
        self.assertAlmostEqual(model['radius'],.21)
    def test_current_target_and_future_poison_are_not_read(self):
        records=self.records();before=calibrate_recent_completed(records,dt.date(2017,1,15))
        records.extend([{'target_end':d,'prediction':object(),'actual':object()} for d in ['2017-01-15','2017-12-31']])
        later=calibrate_recent_completed(records,dt.date(2017,1,15))
        self.assertEqual(before['scores'],later['scores']);self.assertEqual(before['radius'],later['radius'])
        self.assertEqual(later['excluded']['not_completed'],2)
    def test_prior_target_becomes_available_only_after_its_end(self):
        records=self.records()+[{'target_end':'2017-01-14','prediction':100.,'actual':200.}]
        earlier=calibrate_recent_completed(records,dt.date(2017,1,14))
        later=calibrate_recent_completed(records,dt.date(2017,1,15))
        self.assertEqual(earlier['eligible_count'],25);self.assertEqual(later['eligible_count'],26)
    def test_missing_window_does_not_displace_an_older_valid_one(self):
        records=self.records()+[{'target_end':'2017-01-14','prediction':100.,'actual':None}]
        model=calibrate_recent_completed(records,dt.date(2017,1,15))
        self.assertEqual(model['support'],25);self.assertEqual(model['excluded']['missing_total'],1)
        self.assertEqual(model['scores'][0]['target_end'],records[0]['target_end'])
    def test_duplicate_and_insufficient_history_are_explicit(self):
        records=self.records()
        with self.assertRaises(ValueError):calibrate_recent_completed(records+[records[0]],dt.date(2017,1,1))
        self.assertIsNone(calibrate_recent_completed(records[:19],dt.date(2017,1,1))['radius'])
        with self.assertRaises(ValueError):calibrate_recent_completed(records,dt.date(2016,1,1))


if __name__=='__main__':unittest.main(verbosity=2)
