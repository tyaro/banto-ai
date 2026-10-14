from pathlib import Path
import datetime as dt
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from demand_operating_sales import estimate_open_levels, apply_operating_sales

ORIGIN = dt.date(2026,1,1)
ASOF = dt.datetime(2026,1,1,tzinfo=dt.timezone.utc)


def operation(day,status,**kwargs):
    result=dict(record_id=str(day), date=day, status=status, known_at=ASOF,
                stores=[6], cancelled=False)
    result.update(kwargs)
    return result


def past():
    dates=[ORIGIN-dt.timedelta(days=k) for k in range(28,0,-1)]
    return {d:100.0 for d in dates}, [operation(d,'open') for d in dates]


class OperatingSalesChecks(unittest.TestCase):
    def test_open_actual_zero_and_closed_zero_have_different_roles(self):
        history,ops=past()
        dates=sorted(d for d in history if d.weekday()==ORIGIN.weekday())
        history[dates[0]]=0;history[dates[1]]=0
        ops=[operation(d,'closed' if d==dates[0] else 'open') for d in history]
        before=dict(history)
        level=estimate_open_levels(history,ops,ORIGIN,ASOF,6)['weekdays'][ORIGIN.weekday()]
        self.assertEqual(level['open_observed_count'],3)
        self.assertAlmostEqual(level['open_day_mean'],200/3)
        self.assertEqual(history,before)

    def test_missing_and_unknown_zero_retained_with_separate_support(self):
        history,ops=past()
        dates=sorted(d for d in history if d.weekday()==ORIGIN.weekday())
        history[dates[0]]=None;history[dates[1]]=0
        ops=[operation(d,'unknown' if d==dates[1] else 'open') for d in history]
        result=estimate_open_levels(history,ops,ORIGIN,ASOF,6)
        level=result['weekdays'][ORIGIN.weekday()]
        self.assertIsNone(level['open_day_mean'])
        self.assertEqual(level['open_observed_count'],2)
        self.assertAlmostEqual(level['open_unknown_reference_mean'],200/3)
        ledger={r['date']:r for r in result['history_ledger']}
        self.assertFalse(ledger[str(dates[0])]['observed'])
        self.assertEqual(ledger[str(dates[1])]['quantity'],0)
        self.assertEqual(ledger[str(dates[1])]['reason'],'operating_unknown_observation')
        self.assertFalse(result['unknown_reference_used_as_fallback'])

    def test_future_history_and_later_operating_version_not_accessed(self):
        history,ops=past()
        class Prefix(dict):
            def get(self,day):
                if day>=ORIGIN:raise AssertionError('future quantity accessed')
                return super().get(day)
        class HeadersOnly(dict):
            def __getitem__(self,key):
                if key not in ('record_id','known_at'):raise AssertionError('future operating payload accessed')
                return super().__getitem__(key)
        future=HeadersOnly(record_id=str(min(history)),known_at=ASOF+dt.timedelta(days=1))
        result=estimate_open_levels(Prefix(history),ops+[future],ORIGIN,ASOF,6)
        self.assertTrue(all(r['open_day_mean']==100 for r in result['weekdays']))
        self.assertEqual(result['excluded_operating_versions'][0]['reason'],'not_yet_known')
        with self.assertRaisesRegex(ValueError,'cutoff'):
            estimate_open_levels({},[],ORIGIN,ASOF+dt.timedelta(days=1),6)

    def test_daily_mask_and_conditional_total_with_explicit_contract(self):
        days=[ORIGIN+dt.timedelta(days=k) for k in range(3)]
        class Means(dict):
            def get(self,day):
                if day==days[1]:raise AssertionError('closed model mean not needed')
                return super().get(day)
        means=Means({days[0]:10,days[2]:30})
        ops=[operation(days[0],'open'),operation(days[1],'closed')]
        result=apply_operating_sales(means,ops,days,ASOF,6,closed_implies_zero=True)
        self.assertEqual([r['sales_mean'] for r in result['daily']],[10,0,30])
        self.assertEqual(result['total_sales_mean'],40)
        self.assertTrue(result['total_conditional_on_unknown_days_open'])
        no_contract=apply_operating_sales(means,ops,days,ASOF,6,closed_implies_zero=False)
        self.assertIsNone(no_contract['total_sales_mean'])
        self.assertEqual(no_contract['daily'][1]['reason'],'closure_zero_contract_absent')

    def test_all_closed_needs_no_model_or_supported_history(self):
        days=[ORIGIN+dt.timedelta(days=k) for k in range(14)]
        class Unused:
            def get(self,day):raise AssertionError('no open-day mean required')
        result=apply_operating_sales(Unused(),[operation(d,'closed') for d in days],days,ASOF,6,closed_implies_zero=True)
        self.assertEqual(result['total_sales_mean'],0)
        self.assertTrue(result['total_available'])
        self.assertFalse(result['total_conditional_on_unknown_days_open'])
        self.assertTrue(all(r['sales_mean']==0 for r in result['daily']))

    def test_support_composition_and_contradictory_inputs(self):
        levels=estimate_open_levels({},[],ORIGIN,ASOF,6)
        days=[ORIGIN,ORIGIN+dt.timedelta(days=1)]
        means={d:levels['weekdays'][d.weekday()]['open_day_mean'] for d in days}
        result=apply_operating_sales(means,[operation(ORIGIN,'closed')],days,ASOF,6,closed_implies_zero=True)
        self.assertEqual(result['daily'][0]['sales_mean'],0)
        self.assertIsNone(result['daily'][1]['sales_mean'])
        self.assertIsNone(result['total_sales_mean'])
        history,ops=past();closed=min(history)
        ops=[operation(d,'closed' if d==closed else 'open') for d in history]
        with self.assertRaisesRegex(ValueError,'contradicts'):
            estimate_open_levels(history,ops,ORIGIN,ASOF,6)
        with self.assertRaises(ValueError):
            apply_operating_sales({ORIGIN:float('nan')},[],[ORIGIN],ASOF,6,closed_implies_zero=True)


if __name__=='__main__':unittest.main()
