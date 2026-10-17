"""Shared self-series sales mean model with nominal calendar; no operational mask."""
import torch
from torch import nn


def tensor(value, shape, name):
    if not isinstance(value,torch.Tensor) or value.device.type!='cpu' or value.dtype!=torch.float32 or tuple(value.shape)!=shape or not bool(torch.isfinite(value).all()):
        raise ValueError(name+' requires finite CPU float32 tensor of declared shape')


class CalendarSalesMean(nn.Module):
    def __init__(self):
        super().__init__()
        self.patch=nn.Linear(434,32)
        self.position=nn.Parameter(torch.empty(8,32))
        layer=nn.TransformerEncoderLayer(32,4,128,dropout=0.,activation='gelu',
                                        batch_first=True,norm_first=True)
        self.encoder=nn.TransformerEncoder(layer,1,enable_nested_tensor=False)
        self.norm=nn.LayerNorm(32)
        self.statistics=nn.Linear(2,32)
        self.day_head=nn.Sequential(nn.Linear(93,32),nn.GELU(),nn.Linear(32,1))
        nn.init.normal_(self.position,std=.02)
        nn.init.zeros_(self.day_head[-1].weight);nn.init.zeros_(self.day_head[-1].bias)

    def forward(self, values, observed, past_calendar, future_calendar, stats, baseline, scale):
        b=values.shape[0]
        if not 1<=b<=8:raise ValueError('batch must be 1..8')
        for value,shape,name in ((values,(b,56),'normalized values'),(past_calendar,(b,56,60),'past calendar'),
              (future_calendar,(b,14,60),'future calendar'),(stats,(b,2),'statistics'),
              (baseline,(b,14),'baseline'),(scale,(b,),'scale')):
            tensor(value,shape,name)
        if observed.shape!=(b,56) or observed.dtype!=torch.bool or observed.device.type!='cpu':
            raise ValueError('observation mask required')
        if not bool(observed.any(1).all()) or not bool((scale>0).all()) or not bool((values>=0).all()) or not bool((baseline>=0).all()):
            raise ValueError('observed prefix, positive scale and nonnegative quantities required')
        values=torch.where(observed,values,0.)
        past=torch.cat([values[:,:,None],observed.float()[:,:,None],past_calendar],-1).reshape(b,8,434)
        hidden=self.norm(self.encoder(self.patch(past)+self.position)).mean(1)+self.statistics(stats)
        lead=torch.linspace(0,1,14)[None,:,None].expand(b,14,1)
        context=torch.cat([hidden[:,None].expand(b,14,32),future_calendar,lead],-1)
        correction=self.day_head(context).squeeze(-1)
        daily=torch.relu(baseline+scale[:,None]*correction)
        total=daily.sum(1)
        if not bool(torch.isfinite(daily).all()):raise ValueError('nonfinite mean')
        return daily,total


def mean_loss(daily, total, actual, label_mask, scale):
    b=daily.shape[0]
    tensor(daily,(b,14),'daily mean');tensor(total,(b,),'total mean');tensor(scale,(b,),'scale')
    if label_mask.shape!=(b,14) or label_mask.dtype!=torch.bool or actual.shape!=(b,14) or actual.dtype!=torch.float32:
        raise ValueError('actual and observation mask shape required')
    if not bool((scale>0).all()) or not bool(label_mask.any()) or not bool(torch.isfinite(actual[label_mask]).all()) or not bool((actual[label_mask]>=0).all()):
        raise ValueError('valid observed labels and scale required')
    complete=label_mask.all(1)
    if not bool(complete.any()):raise ValueError('no complete total label in batch')
    kept=torch.where(label_mask,actual,0.)
    squared=torch.where(label_mask,((daily-kept)/scale[:,None]).square(),0.)
    daily_mse=squared.sum()/label_mask.sum()
    total_mse=((total[complete]-kept[complete].sum(1))/(14*scale[complete])).square().mean()
    loss=.5*(daily_mse+total_mse)
    return loss,{'daily_mse':daily_mse.item(),'total_mse':total_mse.item()}
