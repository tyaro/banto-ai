from pathlib import Path
import datetime as dt
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from demand_event_intervals import build_interval_inputs

ORIGIN = dt.datetime(2025, 12, 20, tzinfo=dt.timezone.utc)
START = dt.date(2026, 1, 1)
KINDS = ('holiday', 'promotion')


def day(offset):
    return START + dt.timedelta(days=offset)


def event(identity='holiday', **kwargs):
    result = dict(record_id=identity, known_at=ORIGIN, stores=[6], cancelled=False,
                  kind='holiday', start=START, end=day(4), end_status='scheduled')
    result.update(kwargs)
    return result


def operations(offset_status):
    return [dict(record_id=f'op-{offset}', known_at=ORIGIN, stores=[6],
                 cancelled=False, date=day(offset), status=status)
            for offset, status in offset_status]


def build(events, ops=(), offsets=(0,), origin=ORIGIN, store=6, complete=False):
    return build_interval_inputs(events, ops, [day(k) for k in offsets], origin,
                                 store, KINDS, complete)


class IntervalChecks(unittest.TestCase):
    def test_single_and_multi_day_boundaries_without_horizon_clipping(self):
        single = build([event(end=START)], offsets=(-1, 0, 1))
        self.assertEqual([r['event_positions'][0]['phase'] for r in single['daily']],
                         ['before', 'during', 'after'])
        self.assertEqual(single['intervals'][0]['length'], 1)
        multi = build([event()], offsets=(-1, 0, 3, 4, 5))
        self.assertEqual([r['event_positions'][0]['phase'] for r in multi['daily']],
                         ['before', 'during', 'during', 'during', 'after'])
        narrow = build([event()], offsets=(2,))
        self.assertEqual(narrow['intervals'][0]['length'], 5)
        self.assertEqual(narrow['daily'][0]['event_positions'][0]['days_from_end'], -2)
        self.assertEqual(multi['daily'][0]['date'], '2025-12-31')
        self.assertEqual(multi['daily'][-1]['features'][4], 1)

    def test_mid_event_open_day_splits_closures_in_full_calendar(self):
        ops = operations([(-1,'open'), (0,'closed'), (1,'closed'), (2,'open'),
                          (3,'closed'), (4,'closed'), (5,'open')])
        rows = build([event()], ops, offsets=(1, 2, 3))['daily']
        self.assertEqual([r['event_positions'][0]['length'] for r in rows], [5,5,5])
        self.assertEqual(rows[0]['closure_run']['length'], 2)
        self.assertIsNone(rows[1]['closure_run'])
        self.assertEqual(rows[2]['closure_run']['length'], 2)
        self.assertNotEqual(rows[0]['closure_run']['start_confirmed'], rows[2]['closure_run']['start_confirmed'])

    def test_event_can_be_open_throughout_and_closure_boundaries_unknown(self):
        rows = build([event()], operations([(k,'open') for k in range(5)]), offsets=(0,4))['daily']
        self.assertTrue(all(r['operating_status']=='open' and r['closure_run'] is None for r in rows))
        self.assertTrue(all(r['event_positions'][0]['phase']=='during' for r in rows))
        partial = build([], operations([(0,'closed'),(1,'closed'),(2,'unknown')]), offsets=(1,))['daily'][0]
        self.assertEqual(partial['closure_run']['length_lower_bound'], 2)
        self.assertIsNone(partial['closure_run']['length'])
        self.assertFalse(partial['closure_run']['left_boundary_known'])
        self.assertFalse(partial['closure_run']['right_boundary_known'])

    def test_unresolved_end_reasons_and_unknown_extent(self):
        for reason in ('ongoing', 'schedule_unavailable'):
            item = event(end=None, end_status=reason, confirmed_through=day(1))
            result = build([item], offsets=(1,2))
            self.assertEqual([r['event_positions'][0]['phase'] for r in result['daily']], ['during','undetermined'])
            self.assertTrue(all(r['event_positions'][0]['length'] is None for r in result['daily']))
            self.assertEqual(result['daily'][1]['event_positions'][0]['length_unknown_reason'], reason)
            self.assertIsNone(result['daily'][1]['event_positions'][0]['days_from_end'])
            with self.assertRaisesRegex(ValueError,'completeness'):
                build([item], complete=True)

    def test_later_extension_and_operating_payloads_are_unavailable(self):
        class HeadersOnly(dict):
            def __getitem__(self, key):
                if key not in ('record_id','known_at'):
                    raise AssertionError('future payload read')
                return super().__getitem__(key)
        later = ORIGIN + dt.timedelta(days=1)
        unavailable = HeadersOnly(record_id='holiday', known_at=later)
        op_future = HeadersOnly(record_id='op', known_at=later)
        old = event(end=day(2))
        original = build([old,unavailable], [op_future], offsets=(3,))
        self.assertEqual(original['daily'][0]['event_positions'][0]['phase'], 'after')
        self.assertEqual(original['intervals'][0]['length'], 3)
        self.assertEqual(original['daily'][0]['operating_status'], 'unknown')
        new = build([old,event(known_at=later)], offsets=(3,), origin=later)
        self.assertEqual(new['daily'][0]['event_positions'][0]['phase'], 'during')
        self.assertEqual(new['intervals'][0]['length'], 5)
        cancelled = build([old,event(known_at=later,cancelled=True)], origin=later)
        self.assertEqual(cancelled['intervals'], [])

    def test_overlap_scope_and_invalid_intervals(self):
        events = [event(),event('b'),event('promo',kind='promotion'),event('other',stores=[7])]
        result = build(events, operations([(0,'closed'),(1,'open'),(-1,'open')]))
        row = result['daily'][0]
        self.assertEqual(len(row['event_positions']), 3)
        self.assertEqual(sum(row['features']), 2)  # same-kind flag is not a summed duration
        self.assertEqual(row['closure_run']['length'], 1)
        self.assertEqual(len(build(events,store=8)['intervals']), 0)
        for invalid in (event(end=day(-1)), event(end=None,end_status='scheduled',confirmed_through=START),
                        event(end=None,end_status='ongoing',confirmed_through=day(-1))):
            with self.assertRaises(ValueError):
                build([invalid])
        self.assertFalse(result['sales_or_forecast_changed'])


if __name__ == '__main__':
    unittest.main()
