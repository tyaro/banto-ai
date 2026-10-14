from pathlib import Path
import sys,datetime as dt,unittest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from demand_public_calendar import build_inputs
from demand_calendar_model import CalendarSalesMean,mean_loss
torch.set_num_threads(2);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)


def input(mode='pre_post',scale=100.):
    day=dt.date(2014,5,1);history={day-dt.timedelta(days=k):100. for k in range(1,57)}
    x=build_inputs(history,day,scale,mode,(True,)*56)
    return (torch.tensor([x['normalized_values']]),torch.tensor([x['observed']],dtype=torch.bool),
            torch.tensor([x['past_calendar']]),torch.tensor([x['future_calendar']]),
            torch.tensor([x['context_statistics']]),torch.tensor([x['baseline']]),torch.tensor([scale]))


class CalendarModelChecks(unittest.TestCase):
    def test_initial_baseline_exact_total_zero_and_shared_parameters(self):
        torch.manual_seed(20261014);model=CalendarSalesMean();x=input()
        daily,total=model(*x)
        self.assertTrue(torch.equal(daily,x[-2]));self.assertTrue(torch.equal(total,daily.sum(1)))
        zero=list(x);zero[-2]=torch.zeros(1,14)
        self.assertTrue(torch.equal(model(*zero)[0],torch.zeros(1,14)))
        other=CalendarSalesMean();other.load_state_dict(model.state_dict())
        self.assertTrue(all(torch.equal(a,b) for a,b in zip(model.parameters(),other.parameters())))

    def test_pre_post_calendar_has_path_and_finite_gradient(self):
        torch.manual_seed(20261014);model=CalendarSalesMean()
        with torch.no_grad():model.day_head[-1].weight.fill_(.01)
        a=model(*input('on_day'))[0];b,total=model(*input('pre_post'))
        self.assertFalse(torch.equal(a,b))
        loss,_=mean_loss(b,total,torch.full((1,14),120.),torch.ones(1,14,dtype=torch.bool),torch.tensor([100.]))
        loss.backward()
        self.assertTrue(all(p.grad is not None and bool(torch.isfinite(p.grad).all()) for p in model.parameters()))
        self.assertGreater(model.day_head[0].weight.grad[:,32:92].abs().sum().item(),0)

    def test_missing_label_mask_and_partial_total_exclusion(self):
        daily=torch.ones(2,14,requires_grad=True);total=daily.sum(1)
        actual=torch.ones(2,14);actual[1,0]=float('nan')
        mask=torch.ones(2,14,dtype=torch.bool);mask[1,0]=False
        loss,parts=mean_loss(daily,total,actual,mask,torch.ones(2))
        self.assertEqual(parts,{'daily_mse':0.,'total_mse':0.});loss.backward()
        self.assertTrue(bool(torch.isfinite(daily.grad).all()))
        with self.assertRaisesRegex(ValueError,'complete'):
            mean_loss(daily[1:],total[1:],actual[1:],mask[1:],torch.ones(1))


if __name__=='__main__':unittest.main()
