"""Learned origin-statistics branch; mean architecture kept separate from overlays."""
import torch
from torch import nn
from demand_calendar_model import CalendarSalesMean,tensor


class StatisticalFeatureMean(CalendarSalesMean):
    def __init__(self):
        super().__init__()
        self.residual_statistics=nn.Linear(8,32)
        nn.init.zeros_(self.residual_statistics.weight)
        nn.init.zeros_(self.residual_statistics.bias)

    def forward(self,values,observed,past_calendar,future_calendar,stats,baseline,scale,residual_features):
        b=values.shape[0]
        if not 1<=b<=8:raise ValueError('batch must be 1..8')
        for value,shape,name in ((values,(b,56),'normalized values'),(past_calendar,(b,56,60),'past calendar'),
             (future_calendar,(b,14,60),'future calendar'),(stats,(b,2),'statistics'),
             (baseline,(b,14),'baseline'),(scale,(b,),'scale'),(residual_features,(b,8),'residual statistics')):
            tensor(value,shape,name)
        if observed.shape!=(b,56) or observed.dtype!=torch.bool or observed.device.type!='cpu':
            raise ValueError('observation mask required')
        if not bool(observed.any(1).all()) or not bool((scale>0).all()) or not bool((values>=0).all()) or not bool((baseline>=0).all()):
            raise ValueError('observed prefix, positive scale and nonnegative quantities required')
        kept=torch.where(observed,values,0.)
        past=torch.cat([kept[:,:,None],observed.float()[:,:,None],past_calendar],-1).reshape(b,8,434)
        hidden=self.norm(self.encoder(self.patch(past)+self.position)).mean(1)+self.statistics(stats)+self.residual_statistics(residual_features)
        lead=torch.linspace(0,1,14)[None,:,None].expand(b,14,1)
        context=torch.cat([hidden[:,None].expand(b,14,32),future_calendar,lead],-1)
        correction=self.day_head(context).squeeze(-1)
        daily=torch.relu(baseline+scale[:,None]*correction)
        if not bool(torch.isfinite(daily).all()):raise ValueError('nonfinite mean')
        return daily,daily.sum(1)
