from pathlib import Path
import sys,datetime as dt,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from demand_event_calendar import build_inputs

ASOF=dt.datetime(2014,12,20,tzinfo=dt.timezone.utc)
DAY=dt.date(2015,1,1)
KINDS=('new_year','other_holiday')


def event(identity='a',**kwargs):
    return dict(record_id=identity,known_at=ASOF,stores=[6],cancelled=False,date=DAY,kind='new_year',**kwargs)


class EventCalendarChecks(unittest.TestCase):
    def test_before_on_after_and_year_boundary(self):
        days=[DAY+dt.timedelta(days=k) for k in (-3,-1,0,1,3,4)]
        result=build_inputs([event()],[],days,ASOF,6,KINDS)
        for row,k in zip(result['daily'],(-3,-1,0,1,3,4)):
            expected=[0]*14
            if k<=3:expected[k+3]=1
            self.assertEqual(row['features'],expected)
        self.assertEqual(result['daily'][0]['date'],'2014-12-29')

    def test_kinds_and_overlapping_events_are_retained(self):
        a=event();b=event('b');b.update(kind='other_holiday',date=DAY+dt.timedelta(days=1))
        row=build_inputs([a,b],[],[DAY],ASOF,6,KINDS)['daily'][0]
        self.assertEqual((row['features'][3],row['features'][9]),(1,1))
        self.assertEqual(len(row['event_matches']),2)

    def test_future_cancellation_payload_not_accessed(self):
        class HeaderOnly(dict):
            def __getitem__(self,key):
                if key not in ('record_id','known_at'):raise AssertionError('unavailable future payload accessed')
                return super().__getitem__(key)
        future=HeaderOnly(record_id='a',known_at=ASOF+dt.timedelta(days=1))
        row=build_inputs([event(),future],[],[DAY],ASOF,6,KINDS)['daily'][0]
        self.assertEqual(row['features'][3],1)
        cancel=event();cancel.update(known_at=ASOF+dt.timedelta(hours=1),cancelled=True)
        later=build_inputs([event(),cancel],[],[DAY],cancel['known_at'],6,KINDS)
        self.assertEqual(later['daily'][0]['features'],[0]*14)

    def test_unknown_availability_is_not_normal_day_certification(self):
        item=event();item['known_at']=None
        result=build_inputs([item],[],[DAY],ASOF,6,KINDS)
        self.assertFalse(result['event_schedule_complete'])
        self.assertEqual(result['excluded_event_versions'][0]['reason'],'unknown_availability_time')
        with self.assertRaisesRegex(ValueError,'completeness'):
            build_inputs([item],[],[DAY],ASOF,6,KINDS,True)

    def test_holiday_and_store_closure_are_separate(self):
        default=build_inputs([event()],[],[DAY],ASOF,6,KINDS)['daily'][0]
        self.assertEqual(default['operating_status'],'unknown')
        closure=dict(record_id='op',known_at=ASOF,stores=[6],cancelled=False,date=DAY,status='closed')
        row=build_inputs([event()],[closure],[DAY],ASOF,6,KINDS)['daily'][0]
        self.assertEqual(row['operating_status'],'closed')
        self.assertEqual(row['features'][3],1)
        self.assertFalse(build_inputs([event()],[closure],[DAY],ASOF,7,KINDS)['daily'][0]['operating_known'])

    def test_operating_cancel_and_invalid_version(self):
        closed=dict(record_id='op',known_at=ASOF,stores=None,cancelled=False,date=DAY,status='closed')
        cancel=dict(closed,known_at=ASOF+dt.timedelta(hours=1),cancelled=True)
        row=build_inputs([],[closed,cancel],[DAY],cancel['known_at'],6,KINDS)['daily'][0]
        self.assertEqual(row['operating_status'],'unknown')
        with self.assertRaisesRegex(ValueError,'ambiguous'):
            build_inputs([event(),event()],[],[DAY],ASOF,6,KINDS)
        with self.assertRaisesRegex(ValueError,'timezone-aware'):
            build_inputs([],[],[DAY],dt.datetime(2014,12,20),6,KINDS)


if __name__=='__main__':unittest.main()
