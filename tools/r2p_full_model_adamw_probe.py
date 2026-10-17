"""Why R2P step 4 does not compare a full-model AdamW update (reproducible evidence).

Runs the fixed step 4 procedure (tools/r2p_full_model_reference.py) in float32 and
float64, then one AdamW update with the R2P recipe in each, and gates the float32
parameters and moments against float64 under the R0.1 tolerances. It prints every
failing tensor with its worst element and that element's gradients. Writes nothing.

    .venv-r2p/bin/python tools/r2p_full_model_adamw_probe.py
"""
import json
import sys

import r2p_full_model_reference as ref


def main():
    import torch
    import small_model
    torch.set_num_threads(1); torch.set_num_interop_threads(1)
    fx = ref.read(ref.FIX); recipe = dict(ref.read(ref.R2P)['optimizer_recipe'])
    recipe.update(batch_first=fx['batches']['k']['A'], batch_second=fx['batches']['k']['B'])
    tol = ref.read(ref.R0)['tolerance']; eps = recipe['eps']
    after = {}
    for dtype in (torch.float32, torch.float64):
        model = small_model.SmallForecaster(torch.tensor([0.5, 0.25, 0.125], dtype=torch.float32))
        with torch.no_grad():
            for n, p in model.named_parameters():
                p.copy_(torch.tensor(ref.initial(n, list(p.shape)), dtype=torch.float32).reshape(p.shape))
        model = model.to(dtype)
        context, actual = ref.batch(recipe['batch_first'])
        context = torch.tensor(context, dtype=dtype).reshape(2, 3, 128)
        actual = torch.tensor(actual, dtype=dtype).reshape(2, 3, 32)
        f = model(context) if dtype == torch.float32 else ref.forward64(torch, small_model, model, context)
        loss = small_model.training_loss(f, actual) if dtype == torch.float32 else ref.loss64(torch, f, actual)
        loss.backward()
        params = dict(model.named_parameters())
        grads = {n: p.grad.clone() for n, p in params.items()}
        torch.nn.utils.clip_grad_norm_(list(params.values()), recipe['clip_global_norm'], foreach=False)
        opt = torch.optim.AdamW(list(params.values()), lr=recipe['lr'], betas=tuple(recipe['betas']), eps=eps,
                                weight_decay=recipe['weight_decay'], foreach=False, fused=False)
        opt.step()
        after[dtype] = {n: (p.detach().clone(), opt.state[p]['exp_avg'], opt.state[p]['exp_avg_sq'], grads[n])
                        for n, p in params.items()}
    total = failures = 0; worst = 0.
    for n, (p32, m32, v32, g32) in after[torch.float32].items():
        p64, m64, v64, g64 = after[torch.float64][n]
        for label, a, b, kind in [('parameter', p32, p64, 'one_step_parameter'),
                                  ('moment1', m32, m64, 'first_moment'), ('moment2', v32, v64, 'second_moment')]:
            total += 1
            t = tol[kind]; d = (a.double()-b).abs(); limit = t['atol']+t['rtol']*b.abs()
            bad = d > limit
            if bad.any():
                failures += 1; i = int(d.argmax()); worst = max(worst, float(d.reshape(-1)[i]))
                print(json.dumps({'tensor': f'{label}/{n}', 'failing_elements': int(bad.sum()),
                                  'max_abs': float(d.reshape(-1)[i]), 'grad32': float(g32.reshape(-1)[i]),
                                  'grad64': float(g64.reshape(-1)[i]), 'eps': eps}))
    print(json.dumps({'checked_tensors': total, 'failing_tensors': failures, 'max_abs': worst}))


if __name__ == '__main__':
    sys.path.insert(0, str(ref.ROOT/'models/mini-transformer'))
    main()
