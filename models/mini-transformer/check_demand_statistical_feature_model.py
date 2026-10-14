from pathlib import Path
import sys,unittest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from demand_statistical_feature_model import StatisticalFeatureMean
torch.set_num_threads(2);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)


def inputs():
    return (torch.ones(1,56),torch.ones(1,56,dtype=torch.bool),torch.zeros(1,56,60),
            torch.zeros(1,14,60),torch.tensor([[1.,.2]]),torch.full((1,14),100.),torch.tensor([100.]))


class StatisticalBranchChecks(unittest.TestCase):
    def test_zero_initialization_same_shape_and_baseline(self):
        torch.manual_seed(20261014);model=StatisticalFeatureMean();x=inputs()
        self.assertEqual(sum(p.numel() for p in model.parameters()),30369)
        self.assertEqual(model.residual_statistics.weight.abs().sum().item(),0)
        a=model(*x,torch.zeros(1,8));b=model(*x,torch.ones(1,8))
        self.assertTrue(torch.equal(a[0],b[0]));self.assertTrue(torch.equal(b[0],x[-2]))
        self.assertTrue(torch.equal(b[1],b[0].sum(1)))

    def test_feature_gradient_and_sigma_effect_has_no_fixed_direction(self):
        torch.manual_seed(20261014);model=StatisticalFeatureMean();x=inputs()
        features=torch.zeros(1,8,requires_grad=True)
        with torch.no_grad():
            model.day_head[0].weight.zero_();model.day_head[0].bias.zero_()
            model.day_head[0].weight[0,0]=1.
            model.day_head[-1].weight.zero_();model.day_head[-1].weight[0,0]=.01
            model.residual_statistics.weight[0,3]=1.
        features.data[0,3]=1.
        center=model(*x,torch.zeros(1,8))[0]
        higher=model(*x,features)[0]
        self.assertTrue(bool((higher>center).all()))
        higher.sum().backward()
        self.assertTrue(bool(torch.isfinite(features.grad).all()))
        self.assertGreater(abs(features.grad[0,3].item()),0)
        self.assertTrue(bool(torch.isfinite(model.residual_statistics.weight.grad).all()))
        with torch.no_grad():model.residual_statistics.weight[0,3]=-1.
        lower=model(*x,features.detach())[0]
        self.assertTrue(bool((lower<center).all()))


if __name__=='__main__':unittest.main()
