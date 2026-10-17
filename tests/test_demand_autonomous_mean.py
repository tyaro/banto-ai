"""Invented-data boundaries and algebra for the finite mean comparison."""
import csv
import datetime as dt
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import demand_autonomous_mean as experiment

requires_torch = unittest.skipUnless(importlib.util.find_spec('torch'), 'torch is not installed')


class AutonomousMeanChecks(unittest.TestCase):
    def test_snapshot_metadata_filter_before_quantity(self):
        day = dt.date(2013, 1, 1)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'fixture.csv'
            with path.open('w', newline='') as stream:
                writer = csv.writer(stream)
                writer.writerow(['store_nbr', 'date', 'sales', 'observed'])
                for s in experiment.FIT:
                    writer.writerow([s, str(day), 0, 1])
                for s, text in ((31, str(day)), (9, str(day)), (6, '2016-01-01'), (6, '2017-01-01')):
                    writer.writerow([s, text, 'FORBIDDEN', 1])
            result = experiment.read_history(path, day, day)
            self.assertEqual(set(result), set(experiment.FIT))
            self.assertTrue(all(h == {day: 0.} for h in result.values()))

    def test_as_of_features_do_not_read_future_labels(self):
        origin = dt.date(2014, 8, 1)
        class BoundedHistory:
            def get(self, day):
                if not origin-dt.timedelta(days=56) <= day < origin:
                    raise AssertionError('feature read outside past context')
                return 1.
        inputs, encoded, ledger, raw = experiment.assemble({6: BoundedHistory()}, [(6, str(origin))],
                                                          {6: 1.}, [False]*56, lambda: None)
        self.assertEqual(len(experiment.FEATURES), 72)
        self.assertEqual(len(raw[0]), 14)
        self.assertTrue(all(len(r) == 72 for r in raw[0]))
        self.assertNotIn('actual', ledger[0])
        self.assertEqual(raw[0][0][-1], 0.)
        self.assertEqual(raw[0][-1][-1], 1.)

    @requires_torch
    def test_ridge_normal_equation_and_fit_only_inactive_column(self):
        import torch
        raw = torch.zeros((4, 14, 72), dtype=torch.float64)
        raw[:, :, 0] = 1.; raw[:, :, 70] = 2.
        raw[:, :, 1] = torch.tensor([-1., 1., -1., 1.], dtype=torch.float64)[:, None]
        baseline = torch.full((4, 14), 10., dtype=torch.float64)
        actual = baseline+2*raw[:, :, 1]
        scales = torch.ones(4, dtype=torch.float64)
        state = experiment.ridge_fit(raw, baseline, actual, scales)
        self.assertAlmostEqual(state['beta'][1].item(), 2/(1+experiment.LAMBDA), places=10)
        self.assertFalse(state['active'][70].item())
        before = {k: v.clone() for k, v in state.items()}
        changed = raw.clone(); changed[:, :, 70] = 1000000.
        self.assertTrue(torch.equal(experiment.ridge_predict(raw, baseline, scales, state),
                                    experiment.ridge_predict(changed, baseline, scales, state)))
        self.assertTrue(all(torch.equal(v, before[k]) for k, v in state.items()))
        low = raw.clone(); low[:, :, 1] = -100.
        self.assertTrue(bool((experiment.ridge_predict(low, baseline, scales, state) >= 0).all()))

    @requires_torch
    def test_analytic_calibration_finds_half_and_keeps_mean_target(self):
        import torch
        baseline = torch.full((2, 14), 10., dtype=torch.float64)
        scales = torch.ones(2, dtype=torch.float64)
        calibration = experiment.calibrate(baseline+2, baseline, baseline+1, scales)
        self.assertEqual(calibration['alpha'], .5)
        prediction = baseline+calibration['alpha']*2
        self.assertEqual(experiment.score(prediction, baseline+1, scales)['joint'], 0.)
        self.assertEqual(experiment.calibrate(baseline, baseline, baseline+1, scales)['alpha'], 0.)

    @requires_torch
    def test_component_constraint_can_reject_positive_joint_direction(self):
        import torch
        baseline = torch.full((1, 14), 10., dtype=torch.float64)
        delta = torch.tensor([[2., -1.]*7], dtype=torch.float64)
        required = torch.tensor([[1., 3.]*7], dtype=torch.float64)
        result = experiment.calibrate(baseline+delta, baseline, baseline+required, torch.ones(1, dtype=torch.float64))
        self.assertLess(result['daily_covariance'], 0.)
        self.assertGreater(result['total_covariance'], 0.)
        self.assertEqual(result['alpha'], 0.)

    def test_choice_tie_prefers_baseline_then_ridge(self):
        scores = {m: {'joint': 1.} for m in ('baseline', 'ridge_calibrated', 'nn_calibrated')}
        self.assertEqual(experiment.choose(scores), 'baseline')
        scores['ridge_calibrated']['joint'] = .9
        scores['nn_calibrated']['joint'] = .9-1e-13
        self.assertEqual(experiment.choose(scores), 'ridge_calibrated')
        scores['nn_calibrated']['joint'] = .8
        self.assertEqual(experiment.choose(scores), 'nn_calibrated')

    def test_development_adapter_keeps_fixed_population_and_column_roles(self):
        rows = []
        for s in experiment.FIT:
            for k, origin in enumerate(experiment.ORIGINS):
                actual = [1.]*14
                if k == 24:
                    actual[10] = None
                rows.append({'store': s, 'origin': str(origin), 'scale': 1., 'baseline': [2.]*14,
                             'candidate': [1.]*14, 'incumbent': [3.]*14, 'actual': actual,
                             'complete_label': k != 24, 'model_available': True})
        result = experiment.development_metrics(rows, {s: 1. for s in experiment.FIT})
        self.assertEqual(result['requested'], 250)
        self.assertEqual(result['complete_label_windows'], 240)
        self.assertEqual(result['macro']['candidate']['joint'], 0.)
        self.assertEqual(result['macro']['incumbent']['joint'], 4.)
        self.assertEqual(result['improved_stores']['candidate'], 10)
        self.assertIn('candidate', rows[0])
        self.assertNotIn('time_selected', rows[0])


if __name__ == '__main__':
    unittest.main(verbosity=2)
