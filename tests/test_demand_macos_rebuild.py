"""New raw-source rebuild boundaries on invented data only."""
import datetime as dt
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import demand_macos_rebuild as rebuild


class ForbiddenSales(dict):
    def __getitem__(self,key):
        if key=='sales':raise AssertionError('out-of-scope quantity accessed')
        return super().__getitem__(key)


class RebuildBoundaries(unittest.TestCase):
    def test_metadata_selection_precedes_quantity_for_reserved_future_and_wrong_family(self):
        for phase,row in (
            ('internal',{'family':'BREAD/BAKERY','store_nbr':'31','date':'2013-01-01'}),
            ('internal',{'family':'BREAD/BAKERY','store_nbr':'6','date':'2015-01-01'}),
            ('internal',{'family':'BREAD/BAKERY','store_nbr':'4','date':'2014-07-01'}),
            ('development',{'family':'BREAD/BAKERY','store_nbr':'4','date':'2016-01-01'}),
            ('development',{'family':'BREAD/BAKERY','store_nbr':'6','date':'2015-01-13'}),
            ('internal',{'family':'OTHER','store_nbr':'6','date':'2013-01-01'})):
            with self.subTest(phase=phase,row=row):self.assertIsNone(rebuild.select_row(ForbiddenSales(row),phase))

    def test_scale_ignores_future_values_and_keeps_observed_zero(self):
        history={dt.date(2013,1,1):0.,dt.date(2013,1,2):2.,dt.date(2015,1,1):object()}
        result=rebuild.scales({6:history})[6]
        self.assertEqual(result['scale'],1.)
        self.assertEqual(result['observed_days'],2)

    def test_past_getter_rejects_future_and_older_than_context(self):
        origin=dt.date(2015,1,13);past=rebuild.PastOnly({},origin)
        for day in (origin,origin+dt.timedelta(days=1),origin-dt.timedelta(days=57)):
            with self.assertRaises(ValueError):past.get(day)
        self.assertIsNone(past.get(origin-dt.timedelta(days=56)))

    def test_declared_calendar_keys_keep_group_counts_and_exclude_missing_windows(self):
        histories={s:{} for s in rebuild.POSITIVE}
        for k in range(730):
            day=dt.date(2013,1,1)+dt.timedelta(days=k)
            if (day.month,day.day)!=(12,25):
                for history in histories.values():history[day]=1.
        groups,excluded=rebuild.internal_keys(histories,{s:1. for s in histories})
        self.assertEqual({k:len(groups[k]) for k in ('fit','time_validation','transfer_validation','unused_C_preperiod')},
                         {'fit':300,'time_validation':120,'transfer_validation':60,'unused_C_preperiod':150})
        self.assertEqual(len(excluded),90)
        self.assertFalse(set(s for s,_ in groups['fit']) & set(rebuild.GROUP_C))

    def test_partial_label_is_not_replaced_by_thirteen_day_total(self):
        row={'prediction':[1.]*14,'actual':[1.]*13+[None],'complete_label':False}
        value=rebuild.eval_metrics([row],1.,'prediction')
        self.assertEqual(value['observed_daily_labels'],13)
        self.assertEqual(value['complete_total_labels'],0)
        self.assertIsNone(value['joint'])


if __name__=='__main__':unittest.main()
