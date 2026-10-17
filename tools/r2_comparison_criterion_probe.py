"""Evidence for the R0.2 update-comparison criterion (reproducible, writes nothing).

On the R2P step 4 artificial fixture, runs the full SmallForecaster training in float32
and float64 (a proxy for Rust-float32 vs Torch-float32 rounding differences) and reports:

- the loss and gradient differences over 8 updates (batches A,B alternating);
- R0.1 one-step and eight-step parameter comparisons as is, and restricted to elements
  whose float64 gradient magnitude is at least K*eps at every step up to the compared
  step (K = 1, 10, 100), with the number of excluded elements;
- the same one-update comparison from a mature state: 64 float64 updates, then the
  whole state rounded to float32 and imported by both sides.

    .venv-r2p/bin/python tools/r2_comparison_criterion_probe.py
"""
import json
import sys

import r2p_full_model_reference as ref

sys.path.insert(0, str(ref.ROOT/'models/mini-transformer'))


def setup(torch, small_model, dtype, recipe):
    model = small_model.SmallForecaster(torch.tensor([0.5, 0.25, 0.125], dtype=torch.float32))
    with torch.no_grad():
        for n, p in model.named_parameters():
            p.copy_(torch.tensor(ref.initial(n, list(p.shape)), dtype=torch.float32).reshape(p.shape))
    model = model.to(dtype)
    params = dict(model.named_parameters())
    opt = torch.optim.AdamW(list(params.values()), lr=recipe['lr'], betas=tuple(recipe['betas']), eps=recipe['eps'],
                            weight_decay=recipe['weight_decay'], foreach=False, fused=False)
    return model, params, opt


def update(torch, small_model, model, params, opt, k, dtype, recipe):
    context, actual = ref.batch(k)
    context = torch.tensor(context, dtype=dtype).reshape(2, 3, 128)
    actual = torch.tensor(actual, dtype=dtype).reshape(2, 3, 32)
    opt.zero_grad()
    if dtype == torch.float32:
        loss = small_model.training_loss(model(context), actual)
    else:
        loss = ref.loss64(torch, ref.forward64(torch, small_model, model, context), actual)
    loss.backward()
    torch.nn.utils.clip_grad_norm_(list(params.values()), recipe['clip_global_norm'], foreach=False)
    grads = {n: p.grad.detach().double().clone() for n, p in params.items()}
    opt.step()
    return float(loss), grads, {n: p.detach().double().clone() for n, p in params.items()}


def gate(tol, kind, a, b, keep=None):
    """R0.1 elementwise rule over all tensors, optionally only on kept elements."""
    t = tol[kind]; fails = kept = 0; worst = 0.
    for n in a:
        d = (a[n]-b[n]).abs(); limit = t['atol']+t['rtol']*b[n].abs()
        mask = keep[n] if keep is not None else d == d
        kept += int(mask.sum()); bad = (d > limit) & mask
        fails += int(bad.sum()); worst = max(worst, float((d*mask).max()))
    return {'failing_elements': fails, 'compared_elements': kept, 'max_abs_compared': worst}


def main():
    import torch
    import small_model
    torch.set_num_threads(1)
    fx = ref.read(ref.FIX); recipe = dict(ref.read(ref.R2P)['optimizer_recipe'])
    tol = ref.read(ref.R0)['tolerance']; eps = recipe['eps']
    schedule = [fx['batches']['k']['A'], fx['batches']['k']['B']]*4
    runs = {}
    for dtype in (torch.float32, torch.float64):
        model, params, opt = setup(torch, small_model, dtype, recipe)
        runs[dtype] = [update(torch, small_model, model, params, opt, k, dtype, recipe) for k in schedule]
    r32, r64 = runs[torch.float32], runs[torch.float64]
    report = {'loss_abs_diff_by_step': [abs(a[0]-b[0]) for a, b in zip(r32, r64)],
              'gradient_max_abs_diff_by_step': [max(float((a[1][n]-b[1][n]).abs().max()) for n in a[1]) for a, b in zip(r32, r64)]}
    total = sum(g.numel() for g in r64[0][1].values())
    for label, step, kind in [('one_update', 0, 'one_step_parameter'), ('eight_updates', 7, 'eight_step_parameter')]:
        result = {'R0.1_all_elements': gate(tol, kind, r32[step][2], r64[step][2])}
        for K in (1, 10, 100):
            keep = {n: torch.stack([r64[s][1][n].abs() >= K*eps for s in range(step+1)]).all(0) for n in r64[0][1]}
            g = gate(tol, kind, r32[step][2], r64[step][2], keep)
            g['excluded_fraction'] = 1-g['compared_elements']/total
            result[f'K={K}'] = g
        report[label] = result

    # Mature state: 64 float64 updates, rounded to float32 and imported by both sides.
    model, params, opt = setup(torch, small_model, torch.float64, recipe)
    for t in range(64):
        update(torch, small_model, model, params, opt, schedule[t % 2], torch.float64, recipe)
    state = {n: (p.detach().float(), opt.state[p]['exp_avg'].float(), opt.state[p]['exp_avg_sq'].float())
             for n, p in params.items()}
    mature = {}
    for dtype in (torch.float32, torch.float64):
        model, params, opt = setup(torch, small_model, dtype, recipe)
        with torch.no_grad():
            for n, p in params.items():
                p.copy_(state[n][0].to(dtype))
                opt.state[p] = {'step': torch.tensor(64.), 'exp_avg': state[n][1].to(dtype).clone(),
                                'exp_avg_sq': state[n][2].to(dtype).clone()}
        mature[dtype] = update(torch, small_model, model, params, opt, schedule[0], dtype, recipe)
    m32, m64 = mature[torch.float32], mature[torch.float64]
    report['mature_import_one_update'] = {'R0.1_all_elements': gate(tol, 'one_step_parameter', m32[2], m64[2])}
    for K in (1, 10):
        keep = {n: m64[1][n].abs() >= K*eps for n in m64[1]}
        report['mature_import_one_update'][f'K={K}'] = gate(tol, 'one_step_parameter', m32[2], m64[2], keep)
    print(json.dumps(report, indent=1))


if __name__ == '__main__':
    main()
