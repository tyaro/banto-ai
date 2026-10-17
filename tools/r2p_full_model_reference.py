"""Generate the R2P step 4 Torch reference for the full SmallForecaster on artificial data.

Inputs, procedure and comparisons are fixed in
examples/configs/rust-r2p-full-model-fixtures-20261017.json. The float32 Torch run is
checked against the same model and procedure in float64 under the unchanged R0.1
tolerances before anything is saved.

    uv venv -p 3.14 .venv-r2p
    uv pip install -p .venv-r2p/bin/python --index-url https://download.pytorch.org/whl/cpu torch
    .venv-r2p/bin/python tools/r2p_full_model_reference.py

The output directory must not exist; a saved reference is never overwritten.
"""
import copy
import hashlib
import json
import math
from pathlib import Path
import platform
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'models/mini-transformer'))
FIX = 'examples/configs/rust-r2p-full-model-fixtures-20261017.json'
R2P = 'examples/configs/rust-r2p-synthetic-fixtures-20261016.json'
R0 = 'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json'
MODEL = 'models/mini-transformer/small_model.py'
OUT = ROOT/'crates/banto-ai/tests/fixtures/r2p-full'
BUFFERS = ('scale_floor', 'position', 'time_mask')


def read(p): return json.loads((ROOT/p).read_bytes())
def sha256(b): return hashlib.sha256(b).hexdigest()
def f32_bytes(values): return struct.pack('<'+'f'*len(values), *values)


def salt(name): return sum(name.encode()) % 257


def initial(name, shape):
    """Fixed dyadic-rational initial values (see the fixture's initialization rules)."""
    s = salt(name); n = math.prod(shape)
    norm = '.norms.' in name or name.startswith('final_norm.')
    if name == 'horizon':
        rule = lambda i: ((i*29+s) % 33-16)/1024
    elif norm and name.endswith('.weight'):
        rule = lambda i: 1+((i*13+s) % 9-4)/64
    elif norm and name.endswith('.bias'):
        rule = lambda i: ((i*11+s) % 7-3)/64
    elif name.endswith('.weight'):
        a = 1/8 if shape[1] <= 64 else 1/16
        rule = lambda i: ((i*7919+s) % 257-128)/128*a
    elif name.endswith('.bias'):
        rule = lambda i: ((i*31+s) % 17-8)/256
    else:
        raise ValueError(name)
    return [rule(i) for i in range(n)]


def batch(k):
    context = [((t*(c+3)+5*b+k) % 16-8)/4+c if c < 2 else 2+((t+b+k) % 2)/16
               for b in range(2) for c in range(3) for t in range(128)]
    actual = [((h*5+3*c+b+k) % 11-5)/2+c for b in range(2) for c in range(3) for h in range(32)]
    return context, actual


def run(torch, small_model, dtype, recipe):
    """Fixed procedure in one dtype; returns named tensors (float64 values for comparison)."""
    model = small_model.SmallForecaster(torch.tensor([0.5, 0.25, 0.125], dtype=torch.float32))
    names = [n for n, _ in model.named_parameters()]
    with torch.no_grad():
        for n, p in model.named_parameters():
            p.copy_(torch.tensor(initial(n, list(p.shape)), dtype=torch.float32).reshape(p.shape))
    position = model.position.clone()
    initial_bytes = {n: f32_bytes(p.detach().reshape(-1).tolist()) for n, p in model.named_parameters()}
    model = model.to(dtype)
    out = {'buffer/position': position}

    def tensors(k):
        context, actual = batch(k)
        return (torch.tensor(context, dtype=dtype).reshape(2, 3, 128),
                torch.tensor(actual, dtype=dtype).reshape(2, 3, 32))

    def forward(k, label):
        context, actual = tensors(k)
        # small_model's input check requires float32; the float64 run mirrors forward().
        if dtype == torch.float32:
            f = model(context)
        else:
            f = forward64(torch, small_model, model, context)
        loss = small_model.training_loss(f, actual) if dtype == torch.float32 else loss64(torch, f, actual)
        out[f'{label}/normalized-quantiles'] = f.normalized
        out[f'{label}/context-center'] = f.mean
        out[f'{label}/context-scale'] = f.scale
        out[f'{label}/loss'] = loss.reshape(1)
        return loss

    params = dict(model.named_parameters())
    loss = forward(recipe['batch_first'], 'batchA')
    loss.backward()
    missing = [n for n in names if params[n].grad is None]
    assert not missing, missing
    for n in names: out[f'gradient/{n}'] = params[n].grad.clone()
    norm = torch.nn.utils.clip_grad_norm_([params[n] for n in names], 1., error_if_nonfinite=True, foreach=False)
    out['clip/global-norm'] = norm.reshape(1)
    out['clip/coefficient'] = torch.clamp(1./(norm+1e-6), max=1.).reshape(1)
    for n in names: out[f'clipped-gradient/{n}'] = params[n].grad.clone()
    with torch.no_grad():  # initial parameters; no optimizer update is part of step 4
        forward(recipe['batch_second'], 'batchB')
    return names, out, initial_bytes


def forward64(torch, small_model, model, context):
    """small_model.SmallForecaster.forward without its float32-only input check."""
    F = torch.nn.functional
    mean = context.mean(dim=-1, keepdim=True)
    std = context.std(dim=-1, correction=0, keepdim=True)
    scale = torch.maximum(std, model.scale_floor[None, :, None])
    normalized = (context-mean)/scale
    tokens = model.patch(normalized.reshape(context.shape[0], 3, 4, 32))
    query = model.horizon[None, None, None, :].expand(context.shape[0], 3, 1, 64)
    tokens = torch.cat([tokens, query], dim=2)+model.position[None, None]
    for block in model.blocks:
        tokens = block(tokens, model.time_mask, model.series_mask)
    raw = model.head(model.final_norm(tokens[:, :, -1])).reshape(context.shape[0], 3, 32, 3)
    middle = raw[..., 0]
    output = torch.stack([middle-F.softplus(raw[..., 1]), middle, middle+F.softplus(raw[..., 2])], dim=-1)
    return small_model.Forecast(output*scale[..., None]+mean[..., None], output, mean, scale)


def loss64(torch, forecast, actual):
    label = (actual-forecast.mean)/forecast.scale
    levels = forecast.normalized.new_tensor((0.1, 0.5, 0.9))
    residual = label[..., None]-forecast.normalized
    return torch.maximum(levels*residual, (levels-1)*residual).mean()


def gate(tolerances, name, native, expected, kind, checks, global_l2=True):
    """Elementwise atol+rtol; gradients also need the relative L2 bound, which R0.1
    defines over all gradients together (global_l2) rather than per tensor."""
    a = [float(x) for x in native]; b = [float(x) for x in expected]
    assert len(a) == len(b) and a and all(math.isfinite(x) for x in a+b), name
    tol = tolerances[kind]; d = [abs(x-y) for x, y in zip(a, b)]
    bad = sum(e > tol['atol']+tol['rtol']*abs(y) for e, y in zip(d, b))
    norm = math.sqrt(math.fsum(y*y for y in b)); delta = math.sqrt(math.fsum(e*e for e in d))
    rel = delta/norm if norm else None
    l2 = kind != 'gradient' or not global_l2 or (rel <= tol['relative_L2_max'] if norm else delta <= tol['atol'])
    ok = bad == 0 and l2
    checks.append({'name': name, 'category': kind, 'global_l2': global_l2, 'elements': len(a), 'max_abs': max(d),
                   'element_failures': bad, 'relative_L2': rel, 'pass': ok})
    assert ok, checks[-1]


def kind(name):
    if name.startswith(('gradient/', 'clipped-gradient/', 'clip/')): return 'gradient'
    if name.endswith('/loss'): return 'normalized_loss'
    return 'normalized_activation'


def main():
    import torch
    import small_model
    assert sys.version_info[:2] == (3, 14)
    torch.set_num_threads(1); torch.set_num_interop_threads(1)
    fx = read(FIX); recipe = dict(read(R2P)['optimizer_recipe'])
    recipe.update(batch_first=fx['batches']['k']['A'], batch_second=fx['batches']['k']['B'])
    tolerances = read(R0)['tolerance']
    names, f32, initial_bytes = run(torch, small_model, torch.float32, recipe)
    _, f64, _ = run(torch, small_model, torch.float64, recipe)
    assert len(names) == 59 and sum(len(b)//4 for b in initial_bytes.values()) == 109024
    checks = []
    for label, t in f32.items():
        if label == 'buffer/position': continue
        per_tensor = label.startswith(('gradient/', 'clipped-gradient/'))
        gate(tolerances, label, t.detach().reshape(-1).tolist(), f64[label].detach().reshape(-1).tolist(), kind(label), checks,
             global_l2=not per_tensor)
    for prefix in ('gradient/', 'clipped-gradient/'):  # global relative L2 over all 59 tensors
        gate(tolerances, prefix+'*', [x for n in names for x in f32[prefix+n].reshape(-1).tolist()],
             [x for n in names for x in f64[prefix+n].reshape(-1).tolist()], 'gradient', checks)
    OUT.mkdir(parents=True, exist_ok=False)
    raw = bytearray(); layout = []
    for label, t in f32.items():
        assert t.dtype == torch.float32
        b = f32_bytes(t.detach().contiguous().reshape(-1).tolist())
        layout.append({'name': label, 'shape': list(t.shape), 'offset': len(raw), 'bytes': len(b), 'sha256': sha256(b)})
        raw.extend(b)
    files = {
        'reference.f32': bytes(raw),
        'reference-layout.json': layout,
        'initial-parameters-sha256.json': {n: sha256(initial_bytes[n]) for n in names},
        'independent-checks.json': checks,
        'runtime.json': {
            'generated_by': 'tools/r2p_full_model_reference.py', 'generated': '2026-10-17 cloud',
            'python': sys.version, 'platform': platform.platform(), 'torch': torch.__version__,
            'torch_git': torch.version.git_version, 'threads': torch.get_num_threads(),
            'interop_threads': torch.get_num_interop_threads(), 'dtype': 'float32-le CPU',
            'independent_check': 'float64 run of the same model and procedure', 'RNG_draws': 0,
            'fixtures_sha256': sha256((ROOT/FIX).read_bytes()), 'recipe_fixtures_sha256': sha256((ROOT/R2P).read_bytes()),
            'tolerance_sha256': sha256((ROOT/R0).read_bytes()), 'model_source_sha256': sha256((ROOT/MODEL).read_bytes())},
    }
    for name, payload in files.items():
        data = payload if isinstance(payload, bytes) else (json.dumps(payload, ensure_ascii=False, indent=1)+'\n').encode()
        with (OUT/name).open('xb') as f: f.write(data)
    summary = {'checks': len(checks), 'all_checks_pass': all(c['pass'] for c in checks), 'saved_tensors': len(layout),
               'float32_values': len(raw)//4, 'reference_sha256': sha256(bytes(raw)), 'trainable_tensors': len(names),
               'trainable_values': 109024, 'batchA_loss': f32['batchA/loss'].item(), 'batchB_loss': f32['batchB/loss'].item()}
    with (OUT/'summary.json').open('x') as f: f.write(json.dumps(summary, indent=1)+'\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
