"""Six new demand mechanisms; no old model checks or data evaluation."""
import datetime as dt
import math
import unittest
import torch
from demand_data import Prepared, STORES, START, origins
from demand_model import DemandForecaster, DemandForecast, loss_parts


class DemandChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.history = {s: {START+dt.timedelta(days=k): float(100+i*10+k%7)
                          for k in range(1687)} for i, s in enumerate(STORES)}
        for h in cls.history.values():
            for year in range(2013, 2017):
                h[dt.date(year, 12, 25)] = None
            h[dt.date(2016, 1, 1)] = 0.
        cls.data = Prepared(cls.history)
        torch.set_num_threads(2)

    def new_model(self):
        torch.manual_seed(20261014)
        return DemandForecaster(self.data.train_scale)

    def test_missing_zero_and_origin_guard(self):
        d = dt.date(2016, 1, 15)
        original = self.data.features(d)
        # Poison future quantities after preparation: features never touch them.
        saved = [self.history[s][d] for s in STORES]
        try:
            for s in STORES:
                self.history[s][d] = object()
            for a, b in zip(original, self.data.features(d)):
                torch.testing.assert_close(a, b)
        finally:
            for s, v in zip(STORES, saved):
                self.history[s][d] = v
        _, mask, _, _, _ = original
        first = d-dt.timedelta(days=56)
        self.assertFalse(mask[:, (dt.date(2015, 12, 25)-first).days].any())
        self.assertTrue(mask[:, (dt.date(2016, 1, 1)-first).days].all())

    def test_label_boundary_and_missing_exclusion(self):
        self.assertEqual(origins('train')[-1]+dt.timedelta(days=13), dt.date(2015, 12, 31))
        self.assertIn({'origin': '2015-12-18', 'reason': 'missing_target'}, self.data.excluded['train'])
        self.assertIn({'origin': '2016-12-16', 'reason': 'missing_target'}, self.data.excluded['validation'])
        with self.assertRaises(ValueError):
            self.data.batch([dt.date(2017, 1, 1)], 'train')
        # Fixed scales cannot change when a validation value changes.
        before = self.data.train_scale.clone()
        self.history[5][dt.date(2016, 2, 1)] = 90000.
        try:
            torch.testing.assert_close(Prepared(self.history).train_scale, before)
        finally:
            self.history[5][dt.date(2016, 2, 1)] = float(100+((dt.date(2016, 2, 1)-START).days)%7)

    def test_nonnegative_order_and_total_allocation(self):
        x, _ = self.data.batch([dt.date(2017, 1, 1)], 'test')
        out = self.new_model()(*x)
        self.assertEqual(out.totals.shape, (1, 3, 3))
        self.assertTrue((out.totals >= 0).all())
        self.assertTrue((out.totals.diff(dim=-1) >= 0).all())
        torch.testing.assert_close(out.daily.sum(-1), out.totals[..., 1])
        torch.testing.assert_close(out.shares.sum(-1), torch.ones(1, 3))

    def test_future_calendar_path_and_masked_payload(self):
        x, _ = self.data.batch([dt.date(2016, 1, 15)], 'validation')
        model = self.new_model()
        with torch.no_grad():
            model.total_head.weight.normal_(std=.03)
        before = model(*x).totals
        changed = list(x); changed[3] = x[3].clone(); changed[3][..., 4] = 1-changed[3][..., 4]
        self.assertGreater((model(*changed).totals-before).abs().max().item(), 1e-4)
        changed = list(x); changed[0] = torch.where(x[1], x[0], 123456.)
        torch.testing.assert_close(model(*changed).totals, before)

    def test_direct_total_loss(self):
        y = torch.ones(1, 3, 14)
        out = DemandForecast(torch.tensor([[[10., 14., 18.]]]*3).transpose(0, 1), y, y/14)
        value, parts = loss_parts(out, y, torch.ones(3))
        expected = ((.1*4/14)+(.1*4/14))/3
        self.assertAlmostEqual(parts['total_pinball'], expected, places=6)
        self.assertAlmostEqual(value.item(), .5*expected, places=6)

    def test_finite_gradient_with_zero_context(self):
        x, y = self.data.batch([dt.date(2016, 1, 15)], 'validation')
        x = list(x); x[0] = torch.zeros_like(x[0]); x[4] = torch.zeros_like(x[4])
        model = self.new_model(); value, _ = loss_parts(model(*x), y, self.data.train_scale)
        value.backward()
        self.assertTrue(math.isfinite(value.item()))
        self.assertTrue(all(p.grad is None or torch.isfinite(p.grad).all() for p in model.parameters()))
        self.assertGreater(model.total_head.weight.grad.abs().sum().item(), 0.)


if __name__ == '__main__':
    unittest.main()
