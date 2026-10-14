"""Independent demand candidate with explicit level/variation and event channels."""
from dataclasses import dataclass
import math
import torch
from torch import nn
from torch.nn import functional as F
from small_model import Block, pinball, require_tensor


@dataclass(frozen=True)
class DemandForecast:
    totals: torch.Tensor
    daily: torch.Tensor
    shares: torch.Tensor


class DemandInputForecaster(nn.Module):
    def __init__(self, train_scale):
        super().__init__()
        require_tensor(train_scale, (3,), 'train scale')
        if not bool((train_scale > 0).all()):
            raise ValueError('positive scale required')
        self.register_buffer('train_scale', train_scale.detach().clone())
        self.patch = nn.Linear(98, 64)
        self.future = nn.Linear(168, 64)
        self.statistics = nn.Linear(2, 64)
        self.query = nn.Parameter(torch.empty(64))
        self.blocks = nn.ModuleList([Block(), Block()])
        self.norm = nn.LayerNorm(64, eps=1e-5)
        self.total_head = nn.Linear(64, 3)
        self.share_head = nn.Sequential(nn.Linear(77, 32), nn.GELU(), nn.Linear(32, 1))
        position = torch.arange(9, dtype=torch.float32)[:, None]
        frequency = torch.exp(torch.arange(0, 64, 2, dtype=torch.float32)*(-math.log(10000)/64))
        pe = torch.zeros(9, 64)
        pe[:, 0::2], pe[:, 1::2] = torch.sin(position*frequency), torch.cos(position*frequency)
        self.register_buffer('position', pe)
        self.register_buffer('time_mask', torch.ones(9, 9, dtype=torch.bool).tril())
        self.register_buffer('series_mask', torch.ones(3, 3, dtype=torch.bool))
        for layer in self.modules():
            if isinstance(layer, nn.Linear):
                nn.init.xavier_uniform_(layer.weight); nn.init.zeros_(layer.bias)
        nn.init.normal_(self.query, std=.02)
        nn.init.zeros_(self.total_head.weight)
        with torch.no_grad():
            self.total_head.bias.copy_(torch.tensor([math.log(math.expm1(v)) for v in (.8, .2, .2)]))
        nn.init.zeros_(self.share_head[-1].weight); nn.init.zeros_(self.share_head[-1].bias)

    def forward(self, values, observed, past_calendar, future_calendar, baseline, context_stats):
        b = values.shape[0]
        if not 1 <= b <= 8:
            raise ValueError('batch in 1..8 required')
        require_tensor(values, (b, 3, 56), 'values')
        require_tensor(past_calendar, (b, 56, 12), 'past calendar')
        require_tensor(future_calendar, (b, 14, 12), 'future calendar')
        require_tensor(context_stats, (b, 3, 2), 'context statistics')
        if not bool((context_stats >= 0).all()):
            raise ValueError('negative context statistics')
        require_tensor(baseline, (b, 3, 14), 'baseline')
        if observed.shape != values.shape or observed.dtype != torch.bool or observed.device.type != 'cpu':
            raise ValueError('observed mask required')
        if not bool((values >= 0).all()) or not bool((baseline >= 0).all()):
            raise ValueError('negative quantities')
        count = observed.sum(-1, keepdim=True)
        if not bool((count > 0).all()):
            raise ValueError('no observed context')
        kept = torch.where(observed, values, 0.)
        mean = kept.sum(-1, keepdim=True)/count
        delta = torch.where(observed, values-mean, 0.)
        std = (delta.square().sum(-1, keepdim=True)/count).sqrt()
        scale = torch.maximum(std, .01*self.train_scale[None, :, None])
        normalized = torch.where(observed, delta/scale, 0.).reshape(b, 3, 8, 7)
        mask = observed.float().reshape(b, 3, 8, 7)
        past = past_calendar.reshape(b, 1, 8, 84).expand(b, 3, 8, 84)
        tokens = self.patch(torch.cat([normalized, mask, past], -1))
        query = (self.future(future_calendar.reshape(b, 168))+self.query)[:, None] + self.statistics(context_stats)
        tokens = torch.cat([tokens, query[:, :, None]], 2)+self.position[None, None]
        for block in self.blocks:
            tokens = block(tokens, self.time_mask, self.series_mask)
        hidden = self.norm(tokens[:, :, -1])
        base_total = baseline.sum(-1)
        total_scale = torch.maximum(base_total, .01*14*self.train_scale[None])
        totals = F.softplus(self.total_head(hidden)).cumsum(-1)*total_scale[..., None]
        lead = torch.linspace(0, 1, 14).reshape(1, 1, 14, 1).expand(b, 3, 14, 1)
        share_input = torch.cat([hidden[:, :, None].expand(b, 3, 14, 64),
                                 future_calendar[:, None].expand(b, 3, 14, 12), lead], -1)
        correction = 2*torch.tanh(self.share_head(share_input).squeeze(-1))
        shares = ((baseline+.01*self.train_scale[None, :, None]).log()+correction).softmax(-1)
        daily = totals[..., 1, None]*shares
        if not bool(torch.isfinite(totals).all()) or not bool(torch.isfinite(daily).all()):
            raise ValueError('nonfinite demand forecast')
        return DemandForecast(totals, daily, shares)


def loss_parts(forecast, actual, train_scale):
    require_tensor(actual, forecast.daily.shape, 'labels')
    require_tensor(train_scale, (3,), 'train scale')
    if not bool((actual >= 0).all()) or not bool((train_scale > 0).all()):
        raise ValueError('nonnegative label / positive scale required')
    total_scale = 14*train_scale[None]
    total = pinball(forecast.totals/total_scale[..., None], actual.sum(-1)/total_scale)
    daily = ((forecast.daily-actual).abs()/train_scale[None, :, None]).mean()
    return .5*(total+daily), {'total_pinball': total.item(), 'daily_mae': daily.item()}
