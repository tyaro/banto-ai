"""New existing-store evaluation boundaries on invented data only."""
import copy
import datetime as dt
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import demand_existing_store_evaluation as evaluate


class ForbiddenPayload(dict):
    def __getitem__(self, key):
        if key in ('sales', 'onpromotion'):
            raise AssertionError('out-of-scope numeric payload accessed')
        return super().__getitem__(key)


def scored_fixture():
    rows = []
    for store in evaluate.FIT:
        for k, origin in enumerate(evaluate.ORIGINS):
            actual = [1.]*14
            if k == 24:
                actual[10] = None
            rows.append({'store': store, 'origin': str(origin), 'scale': 1., 'baseline': [2.]*14,
                         'time_selected': [1.]*14, 'transfer_selected': [3.]*14,
                         'model_available': True, 'actual': actual, 'complete_label': k != 24})
    return rows, {s: 1. for s in evaluate.FIT}


class ExistingStoreBoundaries(unittest.TestCase):
    def test_scope_metadata_before_numeric_payload(self):
        for store, family, day in (
            ('31', 'BREAD/BAKERY', '2015-01-13'), ('4', 'BREAD/BAKERY', '2015-01-13'),
            ('9', 'BREAD/BAKERY', '2015-01-13'), ('6', 'OTHER', '2015-01-13'),
            ('6', 'BREAD/BAKERY', '2016-01-01'), ('6', 'BREAD/BAKERY', '2017-01-01'),
            ('6', 'BREAD/BAKERY', '2014-11-17'), ('6', 'BREAD/BAKERY', '2015-12-29')):
            with self.subTest(store=store, day=day):
                self.assertIsNone(evaluate.select_row(ForbiddenPayload(
                    {'store_nbr': store, 'family': family, 'date': day})))

    def test_inclusive_source_bounds_keep_zero_and_reject_nonfinite(self):
        for day in (str(evaluate.FIRST), str(evaluate.LAST)):
            self.assertEqual(evaluate.select_row({'store_nbr': '6', 'family': 'BREAD/BAKERY',
                              'date': day, 'sales': '0', 'onpromotion': object()}), (6, dt.date.fromisoformat(day), 0.))
        for quantity in ('nan', 'inf', '-1'):
            with self.assertRaises(ValueError):
                evaluate.select_row({'store_nbr': '6', 'family': 'BREAD/BAKERY',
                                     'date': '2015-01-13', 'sales': quantity})

    def test_first_origin_inputs_do_not_access_future_labels(self):
        origin = evaluate.ORIGINS[0]
        class PastOnlyHistory:
            def get(self, day):
                if not origin-dt.timedelta(days=56) <= day < origin:
                    raise AssertionError('forecast input accessed future or remote past')
                return 1.
        saved_origins = evaluate.ORIGINS
        try:
            evaluate.ORIGINS = (origin,)
            rows, profiles, pending = evaluate.assemble({s: PastOnlyHistory() for s in evaluate.FIT},
                                            {s: 1. for s in evaluate.FIT}, [False]*56)
        finally:
            evaluate.ORIGINS = saved_origins
        self.assertEqual(len(rows), 10)
        self.assertEqual(len(pending), 10)
        self.assertTrue(all('actual' not in r for r in rows))
        self.assertTrue(all(p['profile']['past_end'] == str(origin-dt.timedelta(days=1)) for p in profiles))

    def test_labels_do_not_mutate_prediction_and_missing_total_stays_out(self):
        row = {'store': 6, 'origin': str(evaluate.ORIGINS[-1]), 'baseline': [1.]*14}
        prior = copy.deepcopy(row)
        history = {evaluate.ORIGINS[-1]+dt.timedelta(days=k): 0. for k in range(14) if k != 10}
        result = evaluate.attach_labels([row], {6: history})
        self.assertEqual(row, prior)
        self.assertFalse(result[0]['complete_label'])
        measured = evaluate.eval_metrics(result, 1., 'baseline')
        self.assertEqual(measured['observed_daily_labels'], 13)
        self.assertEqual(measured['complete_total_labels'], 0)
        self.assertIsNone(measured['total'])

    def test_primary_role_and_fixed_grid_not_reselected(self):
        result = evaluate.metrics(*scored_fixture())
        self.assertEqual(result['requested'], 250)
        self.assertEqual(result['complete_label_windows'], 240)
        self.assertEqual(result['macro']['time_selected']['joint'], 0.)
        self.assertEqual(result['macro']['transfer_selected']['joint'], 4.)
        self.assertTrue(result['primary_development_decision']['development_progress'])
        self.assertEqual(result['improved_stores']['time_selected'], 10)
        self.assertEqual(result['support_counts']['6']['methods']['baseline']['observed_daily_labels'], 349)
        rows, scales = scored_fixture()
        with self.assertRaisesRegex(ValueError, 'grid'):
            evaluate.metrics(rows[1:], scales)
        with self.assertRaisesRegex(ValueError, 'grid'):
            evaluate.metrics(rows[:-1]+[rows[0]], scales)

    def test_equal_store_weight_and_support_mismatch_fails_gate(self):
        rows, scales = scored_fixture()
        for row in rows:
            row['time_selected'] = [4. if row['store'] == 6 else 1.]*14
        result = evaluate.metrics(rows, scales)
        self.assertAlmostEqual(result['macro']['time_selected']['joint'], .9)
        rows[0]['time_selected'] = None
        result = evaluate.metrics(rows, scales)
        self.assertFalse(result['primary_development_decision']['support_unchanged'])
        self.assertFalse(result['primary_development_decision']['development_progress'])

    def test_scale_or_complete_mask_changes_rejected(self):
        rows, scales = scored_fixture()
        scales[6] = 0.
        with self.assertRaisesRegex(ValueError, 'scale'):
            evaluate.metrics(rows, scales)
        rows, scales = scored_fixture()
        rows[-1]['complete_label'] = True
        with self.assertRaisesRegex(ValueError, 'mask'):
            evaluate.metrics(rows, scales)


if __name__ == '__main__':
    unittest.main(verbosity=2)
