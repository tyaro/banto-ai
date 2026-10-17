"""Evidence for the R0.2 update-comparison criterion (reproducible, writes nothing).

On the R2P step 4 artificial fixture, runs the full SmallForecaster training in float32
and float64 (a proxy for Rust-float32 vs Torch-float32 rounding differences) and reports:

- the loss and gradient differences over 8 updates (batches A,B alternating);
- R0.1 parameter, first-moment and second-moment comparisons after one and after eight
  updates, as is and restricted to elements whose float64 clipped gradient (the
  gradient handed to AdamW) is at least K*eps at every update up to and including the
  compared one (K = 1, 10, 100), with the excluded fraction of all trainable elements;
- the same one-update comparison from a mature state: 64 float64 updates, then the
  whole state rounded to float32 and imported by both sides; the mask uses only the
  update made after the import.

Run from the tools directory, where r2p_full_model_reference is importable:

    cd tools && ../.venv-r2p/bin/python r2_comparison_criterion_probe.py
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
    """One update; returns loss, clipped gradients, parameters and (m, v) after it."""
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
    moments = {n: (opt.state[p]['exp_avg'].double().clone(), opt.state[p]['exp_avg_sq'].double().clone())
               for n, p in params.items()}
    return loss.item(), grads, {n: p.detach().double().clone() for n, p in params.items()}, moments


def gate(tol, kind, a, b, keep=None):
    """R0.1 elementwise rule over all tensors, optionally only on kept elements."""
    t = tol[kind]; fails = kept = 0; worst = 0.
    for n in a:
        d = (a[n]-b[n]).abs(); limit = t['atol']+t['rtol']*b[n].abs()
        mask = keep[n] if keep is not None else d == d
        kept += int(mask.sum()); bad = (d > limit) & mask
        fails += int(bad.sum()); worst = max(worst, float((d*mask).max()))
    return {'failing_elements': fails, 'compared_elements': kept, 'max_abs_compared': worst}


def compare(tol, kind, r32, r64, keep, total):
    """Parameters under `kind`, moments under their own R0.1 kinds, on kept elements."""
    moment = lambda r, i: {n: m[i] for n, m in r[3].items()}
    entry = {'parameters': gate(tol, kind, r32[2], r64[2], keep),
             'first_moment': gate(tol, 'first_moment', moment(r32, 0), moment(r64, 0), keep),
             'second_moment': gate(tol, 'second_moment', moment(r32, 1), moment(r64, 1), keep)}
    entry['excluded_fraction'] = 1-entry['parameters']['compared_elements']/total
    return entry


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
        result = {}
        for K in (0, 1, 10, 100):  # K=0 compares every element (R0.1 as is)
            keep = None if K == 0 else {n: torch.stack([r64[s][1][n].abs() >= K*eps for s in range(step+1)]).all(0)
                                        for n in r64[0][1]}
            result['R0.1_all_elements' if K == 0 else f'K={K}'] = compare(tol, kind, r32[step], r64[step], keep, total)
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
                # Torch keeps the step as a float tensor; with foreach/fused off it is only
                # used as a count, so 64. stands for the integer step 64 of R0.1.
                opt.state[p] = {'step': torch.tensor(64.), 'exp_avg': state[n][1].to(dtype).clone(),
                                'exp_avg_sq': state[n][2].to(dtype).clone()}
        mature[dtype] = update(torch, small_model, model, params, opt, schedule[0], dtype, recipe)
    m32, m64 = mature[torch.float32], mature[torch.float64]
    report['mature_import_one_update'] = {}
    for K in (0, 1, 10):  # the mask uses only the update made after the import
        keep = None if K == 0 else {n: m64[1][n].abs() >= K*eps for n in m64[1]}
        key = 'R0.1_all_elements' if K == 0 else f'K={K}'
        report['mature_import_one_update'][key] = compare(tol, 'one_step_parameter', m32, m64, keep, total)
    print(json.dumps(report, indent=1))


if __name__ == '__main__':
    main()
