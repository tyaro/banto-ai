"""Generate the artificial R2P Torch reference that the Rust training tests compare against.

Cloud regeneration (2026-10-17) of the Mac reference from 2026-10-16: same fixed fixtures,
same operations and independent scalar checks under the unchanged R0.1 tolerances, but
written to a tracked fixture directory instead of a local evidence store.

    uv venv -p 3.14 .venv-r2p
    uv pip install -p .venv-r2p/bin/python --index-url https://download.pytorch.org/whl/cpu torch
    .venv-r2p/bin/python tools/r2p_reference.py

The output directory must not exist; the script never overwrites a saved reference.
"""
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import platform
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
FIX = 'examples/configs/rust-r2p-synthetic-fixtures-20261016.json'
SPEC = 'examples/configs/rust-r2p-synthetic-protocol-20261016.json'
R0 = 'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json'
OUT = ROOT/'crates/banto-ai/tests/fixtures/r2p'


def read(p): return json.loads((ROOT/p).read_bytes())
def sha256(p): return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()


def analytic_loss(case):
    """Exact rational loss and prediction gradient for one fixed loss case."""
    B, C, H, Q = case['shape']; assert Q == 3
    assert len(case['prediction']) == B*C*H*3 and len(case['actual']) == B*C*H
    assert len(case['center']) == len(case['scale']) == B*C and all(v > 0 for v in case['scale'])
    N = B*C*H*3; total = Fraction(0); gradient = []
    for i, q in enumerate(case['prediction']):
        point = i//3; channel = point//H; tau = [Fraction(1, 10), Fraction(1, 2), Fraction(9, 10)][i % 3]
        r = (Fraction(str(case['actual'][point]))-Fraction(str(case['center'][channel])))/Fraction(str(case['scale'][channel]))-Fraction(str(q))
        total += max(tau*r, (tau-1)*r)
        g = -tau if r > 0 else 1-tau if r < 0 else Fraction(1, 2)-tau
        gradient.append(g/N)
    loss = total/N; assert loss == Fraction(case['expected_loss_rational'])
    if 'expected_gradient_rational' in case:
        assert gradient == [Fraction(x) for x in case['expected_gradient_rational']]
    return {'id': case['id'], 'loss_rational': str(loss), 'prediction_gradient_rational': [str(x) for x in gradient]}


class Capture:
    def __init__(self, torch, tolerances):
        self.torch = torch; self.tolerances = tolerances; self.raw = bytearray(); self.layout = []; self.checks = []

    def tensor(self, label, tensor):
        assert tensor.dtype == self.torch.float32 and tensor.device.type == 'cpu'
        values = tensor.detach().contiguous().reshape(-1).tolist(); assert all(math.isfinite(v) for v in values)
        raw = struct.pack('<'+'f'*len(values), *values); offset = len(self.raw); self.raw.extend(raw)
        assert label not in {x['name'] for x in self.layout}
        self.layout.append({'name': label, 'shape': list(tensor.shape), 'offset': offset, 'bytes': len(raw),
                            'sha256': hashlib.sha256(raw).hexdigest(), 'values': values})
        return values

    def gate(self, name, native, expected, kind):
        a = list(native); b = list(expected); assert len(a) == len(b) and a
        assert all(math.isfinite(x) for x in a+b)
        tol = self.tolerances[kind]; differences = [abs(x-y) for x, y in zip(a, b)]
        bad = sum(d > tol['atol']+tol['rtol']*abs(y) for d, y in zip(differences, b))
        norm = math.sqrt(math.fsum(y*y for y in b)); delta = math.sqrt(math.fsum(d*d for d in differences))
        rel = delta/norm if norm else None
        passed = bad == 0 and (kind != 'gradient' or (rel <= tol['relative_L2_max'] if norm else delta <= tol['atol']))
        self.checks.append({'name': name, 'category': kind, 'elements': len(a), 'max_abs': max(differences),
                            'element_failures': bad, 'relative_L2': rel, 'pass': passed})
        assert passed, self.checks[-1]


def flat(groups): return [x for group in groups for x in group]


def scalar_clip(groups):
    norm = math.sqrt(math.fsum(x*x for x in flat(groups))); coef = min(1., 1./(norm+1e-6))
    return norm, coef, [[x*coef for x in row] for row in groups]


def scalar_update(parameters, gradients, moments, variances, step, recipe):
    b1, b2 = recipe['betas']; lr = recipe['lr']; t = step+1
    m = [[b1*x+(1-b1)*g for x, g in zip(row, gs)] for row, gs in zip(moments, gradients)]
    v = [[b2*x+(1-b2)*g*g for x, g in zip(row, gs)] for row, gs in zip(variances, gradients)]
    p = [[x*(1-lr*recipe['weight_decay'])-lr*(mm/(1-b1**t))/(math.sqrt(vv/(1-b2**t))+recipe['eps'])
          for x, mm, vv in zip(row, ms, vs)] for row, ms, vs in zip(parameters, m, v)]
    return p, m, v


def reference(torch):
    torch.set_num_threads(1); torch.set_num_interop_threads(1)
    assert torch.get_num_threads() == torch.get_num_interop_threads() == 1
    fx = read(FIX); c = Capture(torch, read(R0)['tolerance']); recipe = fx['optimizer_recipe']

    def tensor(values, shape): return torch.tensor(values, dtype=torch.float32, device='cpu').reshape(shape)
    tau = tensor(fx['quantiles'], [3]); c.tensor('quantiles', tau)

    def loss(pred, y, center, scale):
        r = ((y-center)/scale).unsqueeze(-1)-pred
        return torch.maximum(tau*r, (tau-1)*r).mean()

    def clip(ps, label):
        assert all(p.grad is not None and torch.isfinite(p.grad).all().item() for p in ps)
        raw = [c.tensor(label+f'/raw-gradient/{i}', p.grad) for i, p in enumerate(ps)]
        norm = torch.nn.utils.clip_grad_norm_(ps, 1., error_if_nonfinite=True, foreach=False)
        c.tensor(label+'/global-norm', norm); c.tensor(label+'/clip-coefficient', torch.clamp(1./(norm+1e-6), max=1.))
        clipped = [c.tensor(label+f'/clipped-gradient/{i}', p.grad) for i, p in enumerate(ps)]
        _, _, expected = scalar_clip(raw); c.gate(label+'/clip', flat(clipped), flat(expected), 'gradient')
        return raw, clipped

    def optimizer(ps):
        return torch.optim.AdamW(ps, lr=recipe['lr'], betas=tuple(recipe['betas']), eps=recipe['eps'],
                                 weight_decay=recipe['weight_decay'], amsgrad=False, maximize=False, foreach=False, fused=False)

    def state(opt, ps, label):
        p = [c.tensor(label+f'/parameter/{i}', v) for i, v in enumerate(ps)]
        m = [c.tensor(label+f'/moment1/{i}', opt.state[v]['exp_avg']) for i, v in enumerate(ps)]
        v = [c.tensor(label+f'/moment2/{i}', opt.state[v]['exp_avg_sq']) for i, v in enumerate(ps)]
        steps = [int(opt.state[p]['step'].item()) for p in ps]; assert len(set(steps)) == 1
        for i, p0 in enumerate(ps): c.tensor(label+f'/step-tensor/{i}', opt.state[p0]['step'])
        return p, m, v, steps[0]

    oracles = []; journal = []
    for case in fx['loss_cases']:
        B, C, H, Q = case['shape']; label = case['id']; pred = tensor(case['prediction'], [B, C, H, Q]).requires_grad_()
        y = tensor(case['actual'], [B, C, H]); center = tensor(case['center'], [B, C, 1]); scale = tensor(case['scale'], [B, C, 1])
        for n, t in [('prediction', pred), ('actual', y), ('center', center), ('scale', scale)]: c.tensor(label+'/'+n, t)
        l = loss(pred, y, center, scale); l.backward()
        a = analytic_loss(case); oracles.append(a)
        c.gate(label+'/loss', c.tensor(label+'/loss', l), [float(Fraction(a['loss_rational']))], 'normalized_loss')
        c.gate(label+'/gradient', c.tensor(label+'/gradient', pred.grad), [float(Fraction(x)) for x in a['prediction_gradient_rational']], 'gradient')
    for case in fx['clip_cases']:
        ps = [torch.nn.Parameter(torch.zeros(s, dtype=torch.float32)) for s in case['shapes']]
        for p, g in zip(ps, case['gradients']): p.grad = tensor(g, list(p.shape))
        clip(ps, case['id'])
    for case in fx['optimizer_cases']:
        names = fx['optimizer_parameter_order']
        ps = [torch.nn.Parameter(tensor(fx['optimizer_initial_parameters'][n]['values'], fx['optimizer_initial_parameters'][n]['shape'])) for n in names]
        opt = optimizer(ps); label = case['id']
        for i, p in enumerate(ps):
            p.grad = tensor(case['gradients'][i], list(p.shape))
            opt.state[p] = {'step': tensor([case['step_before']], []), 'exp_avg': tensor(case['m_before'][i], list(p.shape)),
                            'exp_avg_sq': tensor(case['v_before'][i], list(p.shape))}
        p0, m0, v0, s0 = state(opt, ps, label+'/before'); raw, clipped = clip(ps, label)
        # Scalar update from the independent global clip, not from the native clipped gradient.
        expected = scalar_update(p0, scalar_clip(raw)[2], m0, v0, s0, recipe)
        opt.step(); pn, mn, vn, sn = state(opt, ps, label+'/after'); assert sn == s0+1
        for values, ref, kind in zip([pn, mn, vn], expected, ['one_step_parameter', 'first_moment', 'second_moment']):
            c.gate(label+'/'+kind, flat(values), flat(ref), kind)
        journal.append({'case': label, 'ordered_names': names, 'step_before': s0, 'step_after': sn})
    toy = fx['toy_training']; names = toy['parameter_order']
    ps = [torch.nn.Parameter(tensor(toy['parameters'][n]['values'], toy['parameters'][n]['shape'])) for n in names]
    opt = optimizer(ps)
    for p in ps: opt.state[p] = {'step': tensor([0], []), 'exp_avg': torch.zeros_like(p), 'exp_avg_sq': torch.zeros_like(p)}
    center = tensor(toy['buffers']['center']['values'], [1, 1, 1]); scale = tensor(toy['buffers']['scale']['values'], [1, 1, 1])
    probe = tensor(toy['probe_x'], [1, 1, 2, 2]); c.tensor('toy/probe-input', probe); c.tensor('toy/center', center); c.tensor('toy/scale', scale)

    def forward(x): return x@ps[0].T+ps[1]

    def scalar_forward(xs, pv):
        w, b = pv; return [xs[h*2]*w[q*2]+xs[h*2+1]*w[q*2+1]+b[q] for h in range(2) for q in range(3)]

    def probe_check(step, pv):
        with torch.no_grad(): q = forward(probe)
        c.gate(f'toy/probe/{step}', c.tensor(f'toy/probe/{step}', q), scalar_forward(toy['probe_x'], pv), 'normalized_activation')

    initial = state(opt, ps, 'toy/step0'); probe_check(0, initial[0])
    for step, batch_id in enumerate(toy['schedule'], 1):
        batch = next(b for b in toy['batch_table'] if b['id'] == batch_id); label = f'toy/update{step}'
        p0, m0, v0, s0 = state(opt, ps, label+'/before'); assert s0 == step-1
        opt.zero_grad(set_to_none=True)
        x = tensor(batch['x'], [1, 1, 2, 2]); y = tensor(batch['target'], [1, 1, 2]); c.tensor(label+'/x', x); c.tensor(label+'/target', y)
        q = forward(x); l = loss(q, y, center, scale); l.backward()
        qmath = scalar_forward(batch['x'], p0); loss_kind = 'normalized_loss' if step == 1 else 'eight_step_loss'
        c.gate(label+'/prediction', c.tensor(label+'/prediction', q), qmath, 'normalized_activation')
        grads = []; total = 0.
        for h in range(2):
            for qi, t in enumerate([.1, .5, .9]):
                r = batch['target'][h]-qmath[h*3+qi]; total += max(t*r, (t-1)*r)
                grads.append((-t if r > 0 else 1-t if r < 0 else .5-t)/6)
        gw = [sum(grads[h*3+qi]*batch['x'][h*2+j] for h in range(2)) for qi in range(3) for j in range(2)]
        gb = [sum(grads[h*3+qi] for h in range(2)) for qi in range(3)]
        c.gate(label+'/loss', c.tensor(label+'/loss', l), [total/6], loss_kind)
        raw, clipped = clip(ps, label); c.gate(label+'/analytic-gradient', flat(raw), gw+gb, 'gradient')
        expected = scalar_update(p0, scalar_clip([gw, gb])[2], m0, v0, s0, recipe)
        opt.step(); pn, mn, vn, sn = state(opt, ps, label+'/after'); assert sn == step
        kinds = ['one_step_parameter' if step == 1 else 'eight_step_parameter', 'first_moment', 'second_moment']
        for values, ref, kind in zip([pn, mn, vn], expected, kinds): c.gate(label+'/'+kind, flat(values), flat(ref), kind)
        probe_check(step, pn)
        journal.append({'case': 'toy', 'batch': batch_id, 'ordered_names': names, 'global_step': sn, 'schedule_next': step})
    return c, oracles, journal


def main():
    import torch
    assert sys.version_info[:2] == (3, 14)
    OUT.mkdir(parents=True, exist_ok=False)
    c, oracles, journal = reference(torch)
    files = {
        'reference.f32': bytes(c.raw),
        'reference-layout.json': c.layout,
        'independent-checks.json': c.checks,
        'analytic-loss-oracles.json': oracles,
        'state-journal.json': journal,
        'runtime.json': {
            'generated_by': 'tools/r2p_reference.py', 'regenerated': '2026-10-17 cloud (replaces the Mac-only 2026-10-16 reference)',
            'python': sys.version, 'platform': platform.platform(), 'machine': platform.machine(),
            'torch': torch.__version__, 'torch_git': torch.version.git_version,
            'threads': torch.get_num_threads(), 'interop_threads': torch.get_num_interop_threads(),
            'dtype': 'float32-le CPU', 'foreach': False, 'fused': False, 'RNG_draws': 0,
            'fixtures_sha256': sha256(FIX), 'protocol_sha256': sha256(SPEC), 'tolerance_sha256': sha256(R0)},
    }
    for name, payload in files.items():
        data = payload if isinstance(payload, bytes) else (json.dumps(payload, ensure_ascii=False, indent=1)+'\n').encode()
        with (OUT/name).open('xb') as f: f.write(data)
    summary = {'checks': len(c.checks), 'all_checks_pass': all(x['pass'] for x in c.checks),
               'saved_tensors': len(c.layout), 'float32_values': len(c.raw)//4,
               'reference_sha256': hashlib.sha256(bytes(c.raw)).hexdigest()}
    with (OUT/'summary.json').open('x') as f: f.write(json.dumps(summary, indent=1)+'\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
