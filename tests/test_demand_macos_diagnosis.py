import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from demand_macos_diagnosis import ACTIVE, ORIGINS, STORES, adapt, calculate


def fixture():
    rows, before = [], []
    for store in STORES:
        for k, origin in enumerate(ORIGINS):
            zero = store == 20
            row = {'store': store, 'origin': str(origin), 'scale': 0 if zero else 2,
                   'baseline': [0 if zero else 10]*14,
                   'time_selected': [0 if zero else 11]*14,
                   'transfer_selected': [0 if zero else 13]*14,
                   'model_available': not zero, 'input_reasons': []}
            before.append(copy.deepcopy(row))
            row.update(actual=[0 if zero else 11]*14, complete_label=k != 24)
            if k == 24:
                row['actual'][10] = None
            rows.append(row)
    metrics = {m: {s: v for s in ('daily', 'total', 'joint')}
               for m, v in (('baseline', .25), ('time_selected', 0), ('transfer_selected', 1))}
    summary = {'development_macro': copy.deepcopy(metrics),
               'per_store': {str(s): copy.deepcopy(metrics) for s in ACTIVE},
               'quarter_macro': {str(q): copy.deepcopy(metrics) for q in range(1, 5)}}
    return rows, before, {s: 0 if s == 20 else 2 for s in STORES}, summary


class MacDiagnosisChecks(unittest.TestCase):
    def test_selection_columns_and_summary_identity(self):
        result = calculate(*fixture())
        self.assertEqual(result['summary_checks']['count'], 90)
        expected = {'time_selected_vs_baseline': -.25, 'transfer_selected_vs_baseline': .75,
                    'transfer_selected_vs_time_selected': 1}
        for name, delta in expected.items():
            self.assertEqual(result['comparisons'][name]['macro']['joint']['mse_delta'], delta)

    def test_missing_day_keeps_daily_support_and_excludes_total(self):
        result = calculate(*fixture())
        store = result['comparisons']['transfer_selected_vs_baseline']['per_store']['4']
        self.assertEqual(store['daily']['count'], 349)
        self.assertEqual(store['total']['count'], 24)

    def test_prediction_mutation_rejected(self):
        data = fixture()
        data[0][0]['time_selected'][0] = 12
        with self.assertRaisesRegex(ValueError, 'prediction changed'):
            calculate(*data)

    def test_missing_store_is_not_reweighted(self):
        rows, before, scales, summary = fixture()
        with self.assertRaisesRegex(ValueError, 'grid count'):
            calculate([r for r in rows if r['store'] != 4], before, scales, summary)

    def test_zero_fallback_preserved_and_separate(self):
        data = fixture()
        result = calculate(*data)
        self.assertFalse(result['zero_scale_store20']['normalized'])
        self.assertEqual(result['zero_scale_store20']['errors']['transfer_selected']['daily_squared_error_sum'], 0)
        data[0][75]['transfer_selected'][0] = 1
        data[1][75]['transfer_selected'][0] = 1
        with self.assertRaisesRegex(ValueError, 'fallback'):
            calculate(*data)

    def test_unexpected_column_or_summary_change_rejected(self):
        rows, before, scales, summary = fixture()
        with self.assertRaisesRegex(ValueError, 'schema'):
            adapt({**before[0], 'feature_on': [99]*14}, labelled=False)
        summary['quarter_macro']['4']['baseline']['total'] = 0
        with self.assertRaisesRegex(ValueError, 'summary difference'):
            calculate(rows, before, scales, summary)


if __name__ == '__main__':
    unittest.main(verbosity=2)
