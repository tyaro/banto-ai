import datetime as dt
import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import demand_temporal_selection as temporal
from demand_training_adequacy import EarlyStopper

requires_torch = unittest.skipUnless(importlib.util.find_spec('torch'), 'torch is not installed')


class ForbiddenLabel(dict):
    def __getitem__(self, key):
        if key == 'actual':
            raise AssertionError('unselected future/crossing/foreign label accessed')
        return super().__getitem__(key)


class TemporalSelectionChecks(unittest.TestCase):
    def test_strict_end_and_origin_boundaries(self):
        keys = [(6, '2014-09-17'), (6, '2014-09-18'), (6, '2014-09-30'), (6, '2014-10-01')]
        split = temporal.temporal_split(keys)
        self.assertEqual(split['inner'], [(6, '2014-09-17')])
        self.assertEqual(split['crossing'], keys[1:3])
        self.assertEqual(split['outer'], keys[3:])

    def test_foreign_metadata_before_invalid_date(self):
        self.assertEqual(temporal.temporal_split([(31, 'POISON'), (54, 'POISON')]),
                         {'inner': [], 'outer': [], 'crossing': []})

    def test_duplicate_and_outside_2014_rejected(self):
        for keys in ([(6, '2014-07-01')]*2, [(6, '2015-01-01')], [(6, '2014-12-31')]):
            with self.assertRaises(ValueError):
                temporal.temporal_split(keys)

    def test_inner_targets_ignore_outer_crossing_and_future_poison(self):
        selected = {'store': 6, 'origin': '2014-07-01', 'actual': [10.]*14}
        excluded = [ForbiddenLabel({'store': 6, 'origin': day}) for day in
                    ('2014-09-23', '2014-10-07', '2015-01-13')]
        excluded.append(ForbiddenLabel({'store': 31}))
        self.assertEqual(temporal.selected_targets(excluded+[selected], [(6, '2014-07-01')]), [[10.]*14])
        with self.assertRaises(ValueError):
            temporal.selected_targets([selected, selected], [(6, '2014-07-01')])

    @requires_torch
    def test_inner_calibration_changes_only_with_selected_labels(self):
        import torch
        rows = [{'store': 6, 'origin': '2014-07-01', 'actual': [11.]*14},
                ForbiddenLabel({'store': 6, 'origin': '2014-10-07'})]
        base = torch.full((1, 14), 10., dtype=torch.float64)
        prediction = torch.full((1, 14), 12., dtype=torch.float64)
        actual = torch.tensor(temporal.selected_targets(rows, [(6, '2014-07-01')]), dtype=torch.float64)
        alpha = temporal.calibrate(prediction, base, actual, torch.ones(1, dtype=torch.float64))
        self.assertEqual(alpha['alpha'], .5)
        rows[0]['actual'] = [8.]*14
        poisoned = torch.tensor(temporal.selected_targets(rows, [(6, '2014-07-01')]), dtype=torch.float64)
        self.assertEqual(temporal.calibrate(prediction, base, poisoned, torch.ones(1))['alpha'], 0.)

    def test_fixed_ties_and_invalid_method_sets(self):
        scores = {name: {'joint': 1.} for name in temporal.ORDER}
        self.assertEqual(temporal.select_method(scores), 'baseline')
        scores['nn_calibrated']['joint'] = .9; scores['rolling_calibrated']['joint'] = .9
        self.assertEqual(temporal.select_method(scores), 'nn_calibrated')
        scores['rolling_calibrated']['joint'] = .8
        self.assertEqual(temporal.select_method(scores), 'rolling_calibrated')
        with self.assertRaises(ValueError):
            temporal.select_method({'baseline': {'joint': 1.}})

    def test_stopping_receives_only_consecutive_inner_checkpoints(self):
        stopper = EarlyStopper()
        for step, value in ((0, 1.), (128, .9), (256, .8), (384, .85), (512, .9),
                            (640, .9), (768, .9), (896, .9), (1024, .9), (1152, .9)):
            observation = stopper.observe(step, value)
        self.assertTrue(observation['stop'])
        self.assertEqual(stopper.best_step, 256)
        with self.assertRaises(ValueError):
            stopper.observe(1280, .1)


if __name__ == '__main__':
    unittest.main()
