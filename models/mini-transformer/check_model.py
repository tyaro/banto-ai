"""Focused checks of the new structure, not a forecast performance benchmark."""
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback

import torch

from small_model import Attention, Forecast, SmallForecaster, pinball, selection_score, training_loss


def pair():
    torch.manual_seed(20261013)
    full = SmallForecaster(torch.tensor([0.001]*3), series_attention="full")
    control = SmallForecaster(torch.tensor([0.001]*3), series_attention="self-only")
    control.load_state_dict(full.state_dict())
    return full, control


def context():
    t = torch.arange(128, dtype=torch.float32)
    series = torch.stack([3+torch.sin(t/9), 25+2*torch.cos(t/17), 4+t/100])
    return torch.stack([series, series*1.2+0.3])


def close(actual, expected, atol=1e-5):
    torch.testing.assert_close(actual, expected, rtol=1e-5, atol=atol)


def shape_parameter_order():
    full, control = pair()
    for model in (full, control):
        assert sum(p.numel() for p in model.parameters()) == 109024
        out = model(context())
        assert out.quantiles.shape == (2, 3, 32, 3)
        assert torch.isfinite(out.quantiles).all()
        assert (out.quantiles[..., 0] <= out.quantiles[..., 1]).all()
        assert (out.quantiles[..., 1] <= out.quantiles[..., 2]).all()
        close(out.quantiles, out.normalized*out.scale[..., None]+out.mean[..., None])
    assert torch.equal(control.series_mask, torch.eye(3, dtype=torch.bool))
    assert all(torch.equal(full.state_dict()[n], p) for n, p in control.state_dict().items())


def future_label_boundary():
    full, _ = pair()
    x = context()
    original = x.clone()
    forecast = full(x)
    y = torch.zeros(2, 3, 32)
    first = training_loss(forecast, y)
    changed = training_loss(forecast, y+100)
    assert first.item() != changed.item()
    close(full(x).quantiles, forecast.quantiles)
    assert torch.equal(x, original)
    # The public forward API accepts context only; labels are loss-side inputs.
    try:
        full(x, y)
    except TypeError:
        pass
    else:
        raise AssertionError("future labels accepted by forward")


def self_only_isolation():
    _, model = pair()
    x = context()
    changed = x.clone()
    changed[:, 1] = torch.sin(torch.arange(128, dtype=torch.float32)/2)*20
    close(model(changed).quantiles[:, 0], model(x).quantiles[:, 0])
    close(model(changed).quantiles[:, 2], model(x).quantiles[:, 2])


def full_network_cross_series_path():
    full, control = pair()
    x = context()
    changed = x.clone()
    changed[:, 1] = torch.sin(torch.arange(128, dtype=torch.float32)/2)*20
    assert not torch.allclose(full(changed).quantiles[:, 0], full(x).quantiles[:, 0],
                              rtol=1e-6, atol=1e-6)
    close(control(changed).quantiles[:, 0], control(x).quantiles[:, 0])


def attention_path_hand_example():
    attention = Attention()
    with torch.no_grad():
        attention.q.weight.zero_(); attention.k.weight.zero_()
        attention.q.bias.zero_(); attention.k.bias.zero_()
        attention.v.weight.copy_(torch.eye(64)); attention.out.weight.copy_(torch.eye(64))
        attention.v.bias.zero_(); attention.out.bias.zero_()
    x = torch.tensor([0., 2., 4.])[None, :, None].expand(1, 3, 64)
    close(attention(x, torch.ones(3, 3, dtype=torch.bool)), torch.full_like(x, 2.))
    close(attention(x, torch.eye(3, dtype=torch.bool)), x)
    # With causal keys, uniform attention returns successive prefix means.
    close(attention(x, torch.ones(3, 3, dtype=torch.bool).tril()),
          torch.tensor([0., 1., 2.])[None, :, None].expand_as(x))


def series_permutation():
    full, control = pair()
    x = context()
    order = [2, 0, 1]
    for model in (full, control):
        close(model(x[:, order]).quantiles, model(x).quantiles[:, order])


def loss_hand_example():
    prediction = torch.tensor([0., 1., 2.]).expand(2, 3, 32, 3)
    y = torch.ones(2, 3, 32)
    close(pinball(prediction, y), torch.tensor(1/15))
    full, _ = pair()
    forecast = full(context())
    train_scale = torch.tensor([2., 4., 8.])
    actual = forecast.quantiles[..., 1].detach()
    residual = actual[..., None]-forecast.quantiles
    q = torch.tensor([0.1, 0.5, 0.9])
    expected = (torch.maximum(q*residual, (q-1)*residual)/train_scale[None, :, None, None]).mean()
    close(selection_score(forecast, actual, train_scale), expected)


def normalized_training_loss_hand_example():
    normalized = torch.tensor([-1., 0., 1.]).expand(2, 3, 32, 3)
    mean = torch.full((2, 3, 1), 2.)
    scale = torch.full((2, 3, 1), 2.)
    forecast = Forecast(normalized*scale[..., None]+mean[..., None], normalized, mean, scale)
    # Actual4 normalizes to1: residuals(2,1,0), loss(.2+.5+0)/3.
    close(training_loss(forecast, torch.full((2, 3, 32), 4.)), torch.tensor(7/30))


def finite_backward_no_update():
    full, _ = pair()
    saved = {n: p.detach().clone() for n, p in full.named_parameters()}
    forecast = full(context())
    loss = training_loss(forecast, context()[:, :, -1:].expand(2, 3, 32))
    loss.backward()
    gradients = [p.grad for p in full.parameters()]
    assert all(g is not None and torch.isfinite(g).all() for g in gradients)
    assert sum(g.abs().sum().item() for g in gradients) > 0
    assert all(torch.equal(saved[n], p) for n, p in full.named_parameters())


def invalid_input_refusal():
    full, _ = pair()
    bad = context(); bad[0, 0, 0] = float("nan")
    for x in (bad, torch.zeros(2, 2, 128), context().double(), torch.zeros(9, 3, 128)):
        try:
            full(x)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid context accepted")
    constant = torch.full((2, 3, 128), 7.)
    out = full(constant)
    assert torch.isfinite(out.quantiles).all()
    close(out.scale, torch.full((2, 3, 1), 0.001))


CHECKS = {f.__name__: f for f in (shape_parameter_order, future_label_boundary,
    self_only_isolation, full_network_cross_series_path, attention_path_hand_example,
    series_permutation, loss_hand_example, normalized_training_loss_hand_example,
    finite_backward_no_update, invalid_input_refusal)}


def process_memory():
    """Read this process only; peak pagefile is an OS lifetime counter."""
    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("faults", wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in ("peak_working", "working",
            "peak_paged", "paged", "peak_nonpaged", "nonpaged", "pagefile",
            "peak_pagefile", "private")]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    counters = Counters(); counters.cb = ctypes.sizeof(counters)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return {"private_bytes": counters.private, "peak_pagefile_bytes": counters.peak_pagefile,
            "peak_working_set_bytes": counters.peak_working}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checks", default=",".join(CHECKS))
    args = parser.parse_args()
    names = args.checks.split(",")
    if len(set(names)) != len(names) or any(n not in CHECKS for n in names):
        parser.error("unknown or duplicate check")
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    start = time.monotonic()
    memory = process_memory()
    if max(memory["private_bytes"], memory["peak_pagefile_bytes"]) > 2*1024**3:
        raise RuntimeError("process memory checkpoint exceeded before checks")
    failed = 0
    for name in names:
        try:
            CHECKS[name]()
            print(json.dumps({"check": name, "status": "passed"}), flush=True)
        except Exception as error:
            failed += 1
            print(json.dumps({"check": name, "status": "failed", "error_type": type(error).__name__,
                              "message": str(error)}), flush=True)
            traceback.print_exc()
        memory = process_memory()
        if max(memory["private_bytes"], memory["peak_pagefile_bytes"]) > 2*1024**3:
            raise RuntimeError("process memory checkpoint exceeded")
        if time.monotonic()-start > 900:
            raise RuntimeError("execution wall checkpoint exceeded")
    source = Path(__file__).with_name("small_model.py").read_bytes()
    print(json.dumps({"checks": len(names), "passed": len(names)-failed, "failed": failed,
        "elapsed_seconds": time.monotonic()-start, "torch": torch.__version__,
        "python": sys.version, "model_source_sha256": hashlib.sha256(source).hexdigest(),
        "process_memory": memory, "resource_measurement": "per-check checkpoint, not blocking guard",
        "optimizer_steps": 0, "timesfm_imported": "timesfm3" in sys.modules,
        "data_body_read": False, "forecast_performance_evaluation": False}), flush=True)
    return bool(failed)


if __name__ == "__main__":
    raise SystemExit(main())
