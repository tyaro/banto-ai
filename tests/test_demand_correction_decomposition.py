import copy
import datetime as dt
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from demand_correction_decomposition import group, macro, validate_ledger


def row(store=1, baseline=10, candidate=12, actual=11, scale=2):
    return {'store': store, 'origin': '2015-01-13', 'scale': scale,
            'baseline': [baseline]*14, 'feature_off': [candidate]*14,
            'feature_on': [candidate]*14, 'actual': [actual]*14,
            'complete_label': True, 'comparable': True, 'model_available': True,
            'input_reasons': [], 'role': 'positive_scale' if scale else 'zero_scale_baseline_only'}


class CorrectionDiagnosisChecks(unittest.TestCase):
    def test_same_direction_overshoot_can_worsen(self):
        result = group([row(candidate=13)], 'feature_on')
        for scope in ('daily', 'total', 'joint'):
            self.assertEqual(result[scope]['correction_squared'], 2.25)
            self.assertEqual(result[scope]['alignment'], 1.5)
            self.assertEqual(result[scope]['mse_delta'], .75)
        self.assertEqual(result['daily']['directions']['same'], 14)
        self.assertEqual(result['total']['over_twice_required'], 1)

    def test_wrong_direction_adds_error_and_exact_correction_improves(self):
        wrong = group([row(candidate=9)], 'feature_on')
        right = group([row(candidate=11)], 'feature_on')
        self.assertEqual(wrong['joint']['alignment'], -.5)
        self.assertEqual(wrong['joint']['mse_delta'], .75)
        self.assertEqual(right['joint']['mse_delta'], -.25)

    def test_missing_day_is_not_zero_or_partial_total(self):
        value = row(actual=0)
        value['actual'][0] = None
        value['complete_label'] = False
        result = group([value], 'feature_on')
        self.assertEqual(result['daily']['count'], 13)
        self.assertEqual(result['total']['count'], 0)
        self.assertIsNone(result['joint']['mse_delta'])
        self.assertEqual(result['daily']['mse_delta'], 11)

    def test_macro_keeps_equal_store_weights_with_unequal_support(self):
        a = group([row(candidate=11)], 'feature_on')
        b = group([row(store=2, candidate=13)]*3, 'feature_on')
        result = macro({'1': a, '2': b})
        self.assertEqual(result['joint']['mse_delta'], .25)
        self.assertEqual(result['support']['1']['total'], 1)
        self.assertEqual(result['support']['2']['total'], 3)

    def test_zero_scale_remains_fallback_and_is_not_normalized(self):
        value = row(candidate=10, scale=0)
        before = {k: v for k, v in value.items() if k not in ('actual', 'complete_label', 'comparable')}
        validate_ledger([value], [before], {1: 0}, [1], [dt.date(2015, 1, 13)])
        with self.assertRaises(ValueError):
            group([value], 'feature_on')

    def test_rejects_changed_prediction_mask_nonfinite_and_duplicate_id(self):
        value = row()
        before = copy.deepcopy({k: v for k, v in value.items() if k not in ('actual', 'complete_label', 'comparable')})
        for change in ({'complete_label': False}, {'feature_on': [15]*14}, {'actual': [float('nan')]*14}):
            changed = {**value, **change}
            with self.assertRaises(ValueError):
                validate_ledger([changed], [before], {1: 2}, [1], [dt.date(2015, 1, 13)])
        with self.assertRaises(ValueError):
            validate_ledger([value]*2, [before]*2, {1: 2}, [1], [dt.date(2015, 1, 13), dt.date(2015, 1, 27)])


if __name__ == '__main__':
    unittest.main(verbosity=2)
