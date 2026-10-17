"""Invented paired-loss and fixed-ledger checks for the new diagnosis."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import demand_existing_store_diagnosis as diagnosis


def fixture():
    before, rows = [], []
    for store in diagnosis.FIT:
        for k, origin in enumerate(diagnosis.ORIGINS):
            row = {'store': store, 'origin': str(origin), 'scale': 2., 'baseline': [10.]*14,
                   'time_selected': [11.]*14, 'transfer_selected': [13.]*14,
                   'model_available': True, 'input_reasons': []}
            before.append(copy.deepcopy(row))
            row.update(actual=[11.]*14, complete_label=k != 24)
            if k == 24:
                row['actual'][10] = None
            rows.append(row)
    def metrics(mse, error):
        return {'daily': mse, 'total': mse, 'joint': mse, 'daily_MAE': abs(error), 'total_MAE': 14*abs(error),
                'daily_bias': error, 'total_bias': 14*error, 'daily_WAPE_percent': 100*abs(error)/11,
                'total_WAPE_percent': 100*abs(error)/11}
    methods = {m: metrics(mse, error) for m, mse, error in
               (('baseline', .25, -1), ('time_selected', 0., 0), ('transfer_selected', 1., 2))}
    by_store = {str(s): copy.deepcopy(methods) for s in diagnosis.FIT}
    summary = {'primary': 'time_selected', 'macro': copy.deepcopy(methods), 'per_store': by_store,
               'quarter_macro': {str(q): copy.deepcopy(methods) for q in range(1, 5)},
               'quarter_per_store': {str(q): copy.deepcopy(by_store) for q in range(1, 5)}}
    return rows, before, {s: 2. for s in diagnosis.FIT}, summary


class ExistingStoreDiagnosisChecks(unittest.TestCase):
    def test_mse_improvement_can_coexist_with_mae_worsening(self):
        result = diagnosis.aggregate(diagnosis.paired([2., 6.], [0., 10.], [10., 10.], 1.))
        self.assertEqual(result['MAE_delta'], 1.)
        self.assertEqual(result['squared_gain']+result['squared_loss'], -10.)
        self.assertEqual((result['helped'], result['hurt']), (1, 1))
        self.assertEqual(result['absolute_gain']+result['absolute_loss'], 1.)

    def test_crossing_target_preserves_under_over_and_bias_identity(self):
        result = diagnosis.aggregate(diagnosis.paired([9.], [12.], [10.], 1.))
        self.assertEqual(result['under_delta'], 1.)
        self.assertEqual(result['over_delta'], -2.)
        self.assertEqual(result['MAE_delta'], -1.)
        self.assertEqual(result['bias_delta'], -3.)

    def test_zero_actual_has_no_wape_and_nonfinite_inputs_fail(self):
        result = diagnosis.aggregate(diagnosis.paired([2.], [1.], [0.], 1.))
        self.assertIsNone(result['WAPE_delta_percent'])
        self.assertEqual(result['over_delta'], 1.)
        for u in (0, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                diagnosis.paired([1.], [1.], [1.], u)
        with self.assertRaises(ValueError):
            diagnosis.paired([float('nan')], [1.], [1.], 1.)

    def test_partial_horizon_excludes_total_and_keeps_observed_zero(self):
        row = {'scale': 1., 'comparable': True, 'feature_off': [2.]*14, 'baseline': [1.]*14,
               'actual': [0.]*13+[None], 'complete_label': False}
        result = diagnosis.absolute_group([row], 'feature_off', 'baseline')
        self.assertEqual(result['daily']['count'], 13)
        self.assertEqual(result['daily']['MAE_delta'], 1.)
        self.assertEqual(result['total']['count'], 0)
        self.assertIsNone(result['total']['MAE_delta'])

    def test_all_fixed_grains_and_three_comparisons_match(self):
        result = diagnosis.calculate(*fixture())
        self.assertEqual(result['summary_checks']['count'], 1485)
        primary = result['comparisons']['time_selected_vs_baseline']
        self.assertEqual(primary['absolute']['macro']['daily']['MAE_delta'], -1.)
        self.assertEqual(primary['absolute']['macro']['total']['MAE_delta'], -14.)
        self.assertEqual(primary['absolute']['macro']['daily']['helped'], 3490)
        self.assertEqual(primary['squared']['macro']['joint']['mse_delta'], -.25)
        self.assertEqual(len(primary['absolute']['quarters']['4']['per_store']), 10)

    def test_rejects_prediction_mutation_missing_store_and_changed_summary(self):
        rows, before, scales, summary = fixture()
        rows[0]['time_selected'][0] = 12.
        with self.assertRaisesRegex(ValueError, 'prediction changed'):
            diagnosis.calculate(rows, before, scales, summary)
        rows, before, scales, summary = fixture()
        with self.assertRaisesRegex(ValueError, 'grid count'):
            diagnosis.calculate(rows[25:], before[25:], scales, summary)
        summary['quarter_per_store']['4']['6']['baseline']['total_MAE'] = 0.
        with self.assertRaisesRegex(ValueError, 'summary difference'):
            diagnosis.calculate(rows, before, scales, summary)


if __name__ == '__main__':
    unittest.main(verbosity=2)
