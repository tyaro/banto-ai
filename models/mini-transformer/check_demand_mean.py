"""Four new mean-output mechanisms; no old checks or data evaluation."""
import math
from pathlib import Path
import sys
import unittest
import torch
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'tools'))
from demand_model_mean import DemandMeanForecaster, MeanForecast, loss_parts
from demand_input_features import calendar
import datetime as dt


class MeanOutputChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(2)

    def fixture(self):
        torch.manual_seed(20261014)
        model = DemandMeanForecaster(torch.tensor([100.]*3))
        origin = dt.date(2015, 6, 1)
        values = torch.tensor([100., 200.]*28).reshape(1, 1, 56).expand(1, 3, 56).clone()
        x = [values, torch.ones_like(values, dtype=torch.bool),
             torch.tensor([calendar(origin-dt.timedelta(days=k)) for k in range(56, 0, -1)])[None],
             torch.tensor([calendar(origin+dt.timedelta(days=k)) for k in range(14)])[None],
             torch.full((1, 3, 14), 150.), torch.tensor([1.5, 1/3]).reshape(1, 1, 2).expand(1, 3, 2)]
        return model, x

    def test_mean_is_separate_from_quantile_head_and_adds_up(self):
        model, x = self.fixture(); a = model(*x)
        self.assertEqual(sum(p.numel() for p in model.parameters()), 120805)
        torch.testing.assert_close(a.daily_mean.sum(-1), a.total_mean)
        self.assertTrue((a.daily_mean >= 0).all())
        with torch.no_grad():
            model.total_head.bias.add_(1.)
        b = model(*x)
        torch.testing.assert_close(a.daily_mean, b.daily_mean)
        self.assertGreater((a.total_quantiles-b.total_quantiles).abs().max().item(), 1.)

    def test_mean_not_clipped_to_interval_or_forced_above_median(self):
        model, x = self.fixture()
        with torch.no_grad():
            model.mean_head.bias.fill_(math.log(math.expm1(3.)))
        a = model(*x); self.assertTrue((a.total_mean > a.total_quantiles[..., 2]).all())
        with torch.no_grad():
            model.mean_head.bias.fill_(math.log(math.expm1(.1)))
        b = model(*x); self.assertTrue((b.total_mean < b.total_quantiles[..., 0]).all())

    def test_mean_loss_targets_arithmetic_mean(self):
        # Non-symmetric five scenarios: 20,20,20,20,100 have mean36/median20.
        actual = torch.tensor([20., 20., 20., 20., 100.])[:, None, None].expand(5, 3, 14)
        fixed_q = torch.tensor([140., 280., 1400.]).reshape(1, 1, 3).expand(5, 3, 3)
        scalar = torch.tensor(36., requires_grad=True)
        forecast = MeanForecast(fixed_q, (14*scalar).expand(5, 3), scalar.expand(5, 3, 14), torch.full((5, 3, 14), 1/14))
        loss, parts = loss_parts(forecast, actual, torch.tensor([10.]*3))
        loss.backward(); self.assertLess(abs(scalar.grad.item()), 1e-5)
        self.assertAlmostEqual(parts['mean_objective'], 10.24, places=5)
        median = MeanForecast(fixed_q, torch.full((5, 3), 280.), torch.full((5, 3, 14), 20.), forecast.shares)
        self.assertGreater(loss_parts(median, actual, torch.tensor([10.]*3))[1]['mean_objective'], parts['mean_objective'])

    def test_zero_context_has_finite_new_mean_gradients(self):
        model, x = self.fixture(); x[0] = torch.zeros_like(x[0]); x[4] = torch.zeros_like(x[4]); x[5] = torch.zeros_like(x[5])
        out = model(*x)
        self.assertTrue(torch.isfinite(out.daily_mean).all()); self.assertTrue((out.total_mean > 0).all())
        # Positive floor is explicit; this is not a learned closure/zero prediction.
        loss, _ = loss_parts(out, torch.full((1, 3, 14), 10.), model.train_scale)
        loss.backward()
        self.assertTrue(all(p.grad is None or torch.isfinite(p.grad).all() for p in model.parameters()))
        self.assertGreater(model.mean_head.weight.grad.abs().sum().item(), 0.)
        self.assertGreater(model.total_head.weight.grad.abs().sum().item(), 0.)


if __name__ == '__main__':
    unittest.main()
