"""Optional, independently initialized forecasting experiment; requires PyTorch.

No TimesFM weights, teacher outputs, dataset IO, or core runtime imports.
The architecture and training choices are our own, documented in the design.
"""
from dataclasses import dataclass
import math

import torch
from torch import nn
from torch.nn import functional as F


QUANTILES = (0.1, 0.5, 0.9)


def require_tensor(value, shape, name):
    if not isinstance(value, torch.Tensor) or tuple(value.shape) != tuple(shape):
        raise ValueError(f"{name}: invalid tensor shape")
    if value.dtype != torch.float32 or value.device.type != "cpu":
        raise ValueError(f"{name}: CPU float32 required")
    if not bool(torch.isfinite(value).all()):
        raise ValueError(f"{name}: nonfinite values")


class Attention(nn.Module):
    def __init__(self):
        super().__init__()
        self.q = nn.Linear(64, 64)
        self.k = nn.Linear(64, 64)
        self.v = nn.Linear(64, 64)
        self.out = nn.Linear(64, 64)

    def forward(self, values, allowed):
        batch, count, _ = values.shape
        def project(layer):
            return layer(values).reshape(batch, count, 4, 16).transpose(1, 2)
        q, k, v = project(self.q), project(self.k), project(self.v)
        logits = q @ k.transpose(-2, -1) / math.sqrt(16)
        logits = logits.masked_fill(~allowed[None, None, :, :], -torch.inf)
        mixed = logits.softmax(dim=-1) @ v
        return self.out(mixed.transpose(1, 2).reshape(batch, count, 64))


class Block(nn.Module):
    def __init__(self):
        super().__init__()
        self.temporal = Attention()
        self.variate = Attention()
        self.norms = nn.ModuleList([nn.LayerNorm(64, eps=1e-5) for _ in range(3)])
        self.ff = nn.Sequential(nn.Linear(64, 128), nn.GELU(), nn.Linear(128, 64))

    def forward(self, values, time_mask, series_mask):
        b, v, n, d = values.shape
        z = self.norms[0](values).reshape(b*v, n, d)
        values = values + self.temporal(z, time_mask).reshape(b, v, n, d)
        z = self.norms[1](values).transpose(1, 2).reshape(b*n, v, d)
        mixed = self.variate(z, series_mask).reshape(b, n, v, d).transpose(1, 2)
        values = values + mixed
        return values + self.ff(self.norms[2](values))


@dataclass(frozen=True)
class Forecast:
    quantiles: torch.Tensor
    normalized: torch.Tensor
    mean: torch.Tensor
    scale: torch.Tensor


class SmallForecaster(nn.Module):
    """Fixed C128/H32/V3/D64/L2 design, with full or self-only series paths."""
    def __init__(self, scale_floor, *, series_attention="full"):
        super().__init__()
        if series_attention not in ("full", "self-only"):
            raise ValueError("unknown series attention mode")
        require_tensor(scale_floor, (3,), "scale floor")
        if not bool((scale_floor > 0).all()):
            raise ValueError("scale floor must be positive")
        self.series_attention = series_attention
        self.register_buffer("scale_floor", scale_floor.detach().clone())
        self.patch = nn.Linear(32, 64)
        self.horizon = nn.Parameter(torch.empty(64))
        self.blocks = nn.ModuleList([Block(), Block()])
        self.final_norm = nn.LayerNorm(64, eps=1e-5)
        self.head = nn.Linear(64, 96)
        position = torch.arange(5, dtype=torch.float32)[:, None]
        frequency = torch.exp(torch.arange(0, 64, 2, dtype=torch.float32)
                              * (-math.log(10000) / 64))
        pe = torch.zeros(5, 64, dtype=torch.float32)
        pe[:, 0::2] = torch.sin(position * frequency)
        pe[:, 1::2] = torch.cos(position * frequency)
        self.register_buffer("position", pe)
        self.register_buffer("time_mask", torch.ones(5, 5, dtype=torch.bool).tril())
        mask = (torch.ones(3, 3, dtype=torch.bool) if series_attention == "full"
                else torch.eye(3, dtype=torch.bool))
        self.register_buffer("series_mask", mask, persistent=False)
        for layer in self.modules():
            if isinstance(layer, nn.Linear):
                nn.init.xavier_uniform_(layer.weight)
                nn.init.zeros_(layer.bias)
        nn.init.normal_(self.horizon, std=0.02)

    def forward(self, context):
        if not isinstance(context, torch.Tensor) or context.ndim != 3:
            raise ValueError("context: [batch,3,128] required")
        if not 1 <= context.shape[0] <= 8:
            raise ValueError("context: batch must be in 1..8")
        require_tensor(context, (context.shape[0], 3, 128), "context")
        mean = context.mean(dim=-1, keepdim=True)
        std = context.std(dim=-1, correction=0, keepdim=True)
        scale = torch.maximum(std, self.scale_floor[None, :, None])
        normalized = (context - mean) / scale
        tokens = self.patch(normalized.reshape(context.shape[0], 3, 4, 32))
        query = self.horizon[None, None, None, :].expand(context.shape[0], 3, 1, 64)
        tokens = torch.cat([tokens, query], dim=2) + self.position[None, None]
        for block in self.blocks:
            tokens = block(tokens, self.time_mask, self.series_mask)
        raw = self.head(self.final_norm(tokens[:, :, -1])).reshape(context.shape[0], 3, 32, 3)
        middle = raw[..., 0]
        output = torch.stack([middle-F.softplus(raw[..., 1]), middle,
                              middle+F.softplus(raw[..., 2])], dim=-1)
        physical = output * scale[..., None] + mean[..., None]
        if not bool(torch.isfinite(physical).all()):
            raise ValueError("forecast: nonfinite output")
        return Forecast(physical, output, mean, scale)


def pinball(prediction, actual):
    require_tensor(actual, prediction.shape[:-1], "actual")
    require_tensor(prediction, (*actual.shape, 3), "prediction")
    levels = prediction.new_tensor(QUANTILES)
    residual = actual[..., None] - prediction
    return torch.maximum(levels*residual, (levels-1)*residual).mean()


def training_loss(forecast, actual):
    require_tensor(actual, forecast.quantiles.shape[:-1], "actual")
    normalized_label = (actual-forecast.mean) / forecast.scale
    return pinball(forecast.normalized, normalized_label)


def selection_score(forecast, actual, train_scale):
    require_tensor(train_scale, (3,), "train scale")
    if not bool((train_scale > 0).all()):
        raise ValueError("train scale must be positive")
    scale = train_scale[None, :, None]
    return pinball(forecast.quantiles/scale[..., None], actual/scale)
