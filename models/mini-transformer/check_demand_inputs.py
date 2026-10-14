"""Three new integration paths, not old model checks or performance trials."""
from pathlib import Path
import sys
import datetime as dt
import unittest
import torch
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO/'tools'))
from demand_model_inputs import DemandInputForecaster, loss_parts
from demand_data_inputs import load_snapshot
from demand_input_features import calendar


class InputIntegrationChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(2)

    def model(self):
        torch.manual_seed(20261014)
        model = DemandInputForecaster(torch.tensor([100.]*3))
        with torch.no_grad():
            model.total_head.weight.normal_(std=.03)
            model.share_head[-1].weight.normal_(std=.03)
        return model

    def x(self):
        d = dt.date(2015, 6, 1)
        values = torch.tensor([100., 200.]*28).reshape(1, 1, 56).expand(1, 3, 56).clone()
        mask = torch.ones_like(values, dtype=torch.bool)
        past = torch.tensor([calendar(d-dt.timedelta(days=k)) for k in range(56, 0, -1)])[None]
        future = torch.tensor([calendar(d+dt.timedelta(days=k)) for k in range(14)])[None]
        baseline = torch.full((1, 3, 14), 150.)
        stats = torch.tensor([1.5, 1/3]).reshape(1, 1, 2).expand(1, 3, 2).clone()
        return [values, mask, past, future, baseline, stats]

    def test_shifted_context_changes_normalized_total_multiplier(self):
        model = self.model(); x = self.x(); a = model(*x)
        x[0] += 1000.; x[4] += 1000.; x[5][..., 0] = 11.5; x[5][..., 1] = 1/23
        b = model(*x)
        self.assertGreater((a.totals/2100-b.totals/16100).abs().max().item(), 1e-5)
        self.assertEqual(sum(p.numel() for p in model.parameters()), 120740)
        value, _ = loss_parts(b, torch.full((1, 3, 14), 1150.), model.train_scale)
        value.backward()
        self.assertTrue(torch.isfinite(model.statistics.weight.grad).all())
        self.assertGreater(model.statistics.weight.grad.abs().sum().item(), 0.)

    def test_separate_event_channels_reach_daily_allocation(self):
        model = self.model(); x = self.x()
        # Hold the continuous calendar constant; change only nominal event ID.
        x[3][0, 0, 4] = 1.; a = model(*x)
        x[3][0, 0, 4] = 0.; x[3][0, 0, 5] = 1.; b = model(*x)
        self.assertGreater((a.shares-b.shares).abs().max().item(), 1e-6)
        value, _ = loss_parts(b, torch.full((1, 3, 14), 150.), model.train_scale)
        value.backward()
        self.assertTrue(torch.isfinite(model.future.weight.grad).all())
        self.assertGreater(model.future.weight.grad[:, 5].abs().sum().item(), 0.)

    def test_real_adapter_preserves_declared_schedule_and_event_metadata(self):
        prepared, _ = load_snapshot(REPO)
        self.assertEqual([len(prepared.origins[s]) for s in ('train', 'validation', 'test')], [991, 25, 16])
        self.assertEqual(len(prepared.schedule()), 256)
        # Prepare context only: never open a label or run the old model.
        value = prepared.built(dt.date(2015, 12, 20)); x = prepared.features(dt.date(2015, 12, 20))
        self.assertEqual(tuple(x[2].shape), (56, 12)); self.assertEqual(tuple(x[5].shape), (3, 2))
        self.assertEqual(value['stores'][5]['future_event_metadata'][5]['support_status'], 'no_observed_training_labels')
        self.assertTrue(all(torch.isfinite(t).all() for t in x if t.dtype == torch.float32))


if __name__ == '__main__':
    unittest.main()
