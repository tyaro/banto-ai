"""Formal R2 (CARE fold0) driver: fixture, Torch reference with its float64 check, Rust run, comparison.

Conditions: examples/configs/rust-small-forecaster-r0-20261016-r0.1.json (tolerances) and
examples/configs/rust-r2-formal-20261017.json (cases, R0.2 comparison, run unit, stop rules).
One invocation is one formal R2 run, in order:

1. fixture from the pinned CARE inputs (selected state, fold0 batches 0..7, floor-tie case);
2. Torch float32 reference of every case, kept only if its loss and gradients agree with the
   same procedure in float64 within R0.1; hashed and frozen before any Rust run;
3. `cargo build --release --locked` (outside the limits), then the Rust `r2_formal` example:
   cases, and resume as 4 updates + checkpoint in one process and restore + 4 in another;
4. comparison under R0.1/R0.2 and the records the contract asks for.

`--synthetic` replaces every CARE input by artificial values to exercise the harness only; its
results are not formal R2. Writes only under --output (new directory, gitignored artifacts/).

    <python with torch> tools/r2_formal.py --output artifacts/r2-formal-20261017
"""
import argparse
import hashlib
import json
import os
import struct
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'models/mini-transformer'), str(ROOT/'tools')]
R0 = ROOT/'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json'
CONTRACT = ROOT/'examples/configs/rust-r2-formal-20261017.json'
EXAMPLE = ROOT/'target/release/examples/r2_formal'
UPDATES = 8
K_EPS = 1e-7
BUFFERS = ['scale_floor', 'position', 'time_mask']
SOURCES = ['crates/banto-ai/src', 'crates/banto-ai/examples/r2_formal.rs', 'tools/r2_formal.py',
           'models/mini-transformer/small_model.py', 'tools/r2p_full_model_reference.py', 'Cargo.lock',
           'examples/configs/rust-r2-formal-20261017.json']


def digest(data):
    return hashlib.sha256(data if isinstance(data, bytes) else Path(data).read_bytes()).hexdigest()


def write_new(path, data):
    with open(path, 'xb') as f:
        f.write(data if isinstance(data, bytes) else json.dumps(data, indent=1).encode())


def close(root):
    files = [{'name': p.name, 'bytes': p.stat().st_size, 'sha256': digest(p)} if p.is_file()
             else {'name': p.name+'/', 'root_closed_sha256': digest(p/'root-closed.json')}
             for p in sorted(root.iterdir()) if p.name != 'root-closed.json']
    write_new(root/'root-closed.json', {'status': 'complete', 'files': files})


def sources():
    git = lambda *a: subprocess.run(['git', *a], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    files = {}
    for s in SOURCES:
        p = ROOT/s
        for f in sorted(p.rglob('*.rs')) if p.is_dir() else [p]:
            files[str(f.relative_to(ROOT))] = digest(f)
    rustc = subprocess.run(['rustc', '-vV'], capture_output=True, text=True).stdout.split()
    return {'commit': git('rev-parse', 'HEAD'), 'worktree_clean': git('status', '--porcelain') == '',
            'files_sha256': files, 'rustc': rustc}


class Payload:
    """Named float32 tensors in one little-endian payload with a hashed layout."""
    def __init__(self):
        self.raw = bytearray(); self.entries = []

    def put(self, name, shape, values):
        start = len(self.raw); self.raw += struct.pack(f'<{len(values)}f', *values)
        self.entries.append({'name': name, 'shape': list(shape), 'offset': start, 'bytes': len(self.raw)-start,
                             'sha256': digest(bytes(self.raw[start:]))})

    def save(self, directory, payload_name, layout_name, extra):
        directory.mkdir()
        write_new(directory/payload_name, bytes(self.raw))
        write_new(directory/layout_name, {**extra, 'entries': self.entries, 'payload_sha256': digest(bytes(self.raw))})


def load_records(torch, directory, payload_name='records.f32', layout_name='records.json'):
    layout = json.loads((directory/layout_name).read_bytes()); raw = (directory/payload_name).read_bytes()
    assert digest(raw) == layout['payload_sha256']
    out = {}
    for e in layout['entries']:
        chunk = raw[e['offset']:e['offset']+e['bytes']]
        assert digest(chunk) == e['sha256'] and e['name'] not in out
        out[e['name']] = (chunk, torch.frombuffer(bytearray(chunk), dtype=torch.float32).double())
    return layout, out


# ---------------------------------------------------------------- inputs

def care_inputs(torch, contract, cfg):
    """Pinned CARE inputs: fold0 batches 0..7 and the selected step-4096 state."""
    from care_training_preparation import FrozenPreparation
    for pin in contract['inputs']['pins']:
        assert digest(ROOT/pin['path']) == pin['sha256'], pin['path']
    for r in cfg['references']:
        assert digest(ROOT/r['path']) == r['sha256'], r['path']
    prep = FrozenPreparation(ROOT/'artifacts/care-train-profile-schedule-20261016', ROOT/'artifacts/care-numeric-input-20261016', 0)
    flat = lambda xs: [v for x in xs for ch in x for v in ch]
    reference = b''
    for step in (0, 4095):
        xs, ys = prep.batch(step)
        for x, y in zip(xs, ys, strict=True):
            reference += struct.pack('<480f', *flat([x]), *flat([y]))
    assert reference == (ROOT/cfg['references'][2]['path']).read_bytes(), 'batch steps 0/4095 differ from the Mac batch reference'
    batches = []
    for step in range(UPDATES):
        xs, ys = prep.batch(step)
        batches.append((torch.tensor(flat(xs)).reshape(8, 3, 128), torch.tensor(flat(ys)).reshape(8, 3, 32)))
    layout = json.loads((ROOT/cfg['references'][1]['path']).read_bytes()); raw = (ROOT/cfg['references'][0]['path']).read_bytes()
    state = {}
    for e in layout['tensors']:
        b = raw[e['offset_bytes']:e['offset_bytes']+e['length_bytes']]
        t = torch.frombuffer(bytearray(b), dtype=torch.float32 if e['dtype'] == 'float32-le' else torch.uint8)
        state[e['name']] = t.reshape(e['shape']) if e['shape'] else t.reshape([])
    model = {n[7:]: t for n, t in state.items() if n.startswith('model::')}
    names = [m['name'] for m in layout['optimizer_mapping']]
    steps = {float(state[f'adamw::{n}::step']) for n in names}
    assert steps == {4096.0} and layout['step'] == 4096 and layout['sampler_position'] == 32768
    moments = {n: (state[f'adamw::{n}::exp_avg'], state[f'adamw::{n}::exp_avg_sq']) for n in names}
    return model, moments, 4096, batches


def synthetic_inputs(torch):
    """Artificial stand-ins for every CARE input (harness check only)."""
    import r2p_full_model_reference as ref
    from small_model import SmallForecaster
    model = SmallForecaster(torch.tensor([0.5, 0.25, 0.125]))
    state = {n: t.detach().clone() for n, t in model.state_dict().items()}
    for n, p in model.named_parameters():
        state[n] = torch.tensor(ref.initial(n, list(p.shape)), dtype=torch.float32).reshape(p.shape)
    moments = {n: (state[n]*2**-10, state[n]*state[n]*2**-12+2**-20) for n, _ in model.named_parameters()}
    batches = []
    for k in range(UPDATES):
        b = [(ref.batch(k+j)) for j in range(4)]  # four 2-example batches make one of 8
        context = torch.cat([torch.tensor(c).reshape(2, 3, 128) for c, _ in b]); actual = torch.cat([torch.tensor(a).reshape(2, 3, 32) for _, a in b])
        batches.append((context, actual))
    return state, moments, 4096, batches


def floor_tie(floors):
    """R1 floor-equal context: population std equals scale_floor exactly; alternating target."""
    import torch
    context = torch.tensor([[[f*(1 if t % 2 == 0 else -1) for t in range(128)] for f in floors]])
    actual = torch.tensor([[[f*(1 if h % 2 == 0 else -1) for h in range(32)] for f in floors]])
    assert context.std(-1, correction=0).flatten().tolist() == list(floors)
    return context, actual


def write_fixture(torch, out, names, state, moments, step, batches, tie, recipe):
    fx = Payload()
    for n in names:
        fx.put(f'param/{n}', state[n].shape, state[n].flatten().tolist())
    for n in BUFFERS:
        fx.put(f'buffer/{n}', [state[n].numel()], state[n].float().flatten().tolist())
    for n in names:
        fx.put(f'adamw/m/{n}', [state[n].numel()], moments[n][0].flatten().tolist())
        fx.put(f'adamw/v/{n}', [state[n].numel()], moments[n][1].flatten().tolist())
    for k, (x, y) in enumerate(batches):
        fx.put(f'batch/{k}/context', x.shape, x.flatten().tolist()); fx.put(f'batch/{k}/actual', y.shape, y.flatten().tolist())
    fx.put('floor_tie/context', tie[0].shape, tie[0].flatten().tolist()); fx.put('floor_tie/actual', tie[1].shape, tie[1].flatten().tolist())
    fx.save(out, 'inputs.f32', 'inputs.json', {'schema': 'banto.r2-formal-fixture.v1', 'parameter_order': names,
                                               'adamw_step': step, 'recipe': recipe})
    close(out)
    return digest(out/'inputs.json')


# ---------------------------------------------------------------- Torch reference

def torch_run(torch, small_model, ref64, dtype, names, state, moments, step, batches, tie, recipe):
    """Every case in one dtype with the Rust record names; values returned as float64."""
    rec = {}

    def build(mature):
        model = small_model.SmallForecaster(state['scale_floor'].float())
        model.load_state_dict({n: (t.bool() if n == 'time_mask' else t) for n, t in state.items()}, strict=True)
        model = model.to(dtype)
        params = dict(model.named_parameters()); assert list(params) == names
        opt = torch.optim.AdamW(list(params.values()), lr=recipe['lr'], betas=tuple(recipe['betas']), eps=recipe['eps'],
                                weight_decay=recipe['weight_decay'], foreach=False, fused=False)
        if mature:
            for n, p in params.items():
                opt.state[p] = {'step': torch.tensor(float(step)), 'exp_avg': moments[n][0].to(dtype).clone(),
                                'exp_avg_sq': moments[n][1].to(dtype).clone()}
        return model, params, opt

    def forward_loss(model, x, y):
        x, y = x.to(dtype), y.to(dtype)
        if dtype == torch.float32:
            f = model(x)
            return f, small_model.training_loss(f, y)
        f = ref64.forward64(torch, small_model, model, x)
        return f, ref64.loss64(torch, f, y)

    def gradients(label, model, params, x, y):
        model.zero_grad(set_to_none=True)
        _, loss = forward_loss(model, x, y); loss.backward()
        for n, p in params.items():
            rec[f'{label}/raw/{n}'] = p.grad.detach().double().flatten().clone()
        norm = torch.nn.utils.clip_grad_norm_(list(params.values()), recipe['clip_global_norm'], foreach=False)
        coefficient = torch.clamp(recipe['clip_global_norm']/(norm+1e-6), max=1.0)
        rec[f'{label}/loss'] = loss.detach().double().reshape(1); rec[f'{label}/norm'] = norm.detach().double().reshape(1)
        rec[f'{label}/coefficient'] = coefficient.detach().double().reshape(1)
        for n, p in params.items():
            rec[f'{label}/clipped/{n}'] = p.grad.detach().double().flatten().clone()

    def update(label, model, params, opt, k):
        gradients(label, model, params, *batches[k]); opt.step()
        for n, p in params.items():
            rec[f'{label}/param/{n}'] = p.detach().double().flatten().clone()
            rec[f'{label}/m/{n}'] = opt.state[p]['exp_avg'].double().flatten().clone()
            rec[f'{label}/v/{n}'] = opt.state[p]['exp_avg_sq'].double().flatten().clone()
        with torch.no_grad():
            f, _ = forward_loss(model, *batches[min(k+1, UPDATES-1)])
        rec[f'{label}/forward'] = f.normalized.double().flatten().clone()

    update('one_update/1', *build(False), 0)
    model, params, opt = build(False)
    for k in range(UPDATES):
        update(f'eight_updates/{k+1}', model, params, opt, k)
    update('mature_import/1', *build(True), 0)
    model, params, _ = build(False)
    gradients('floor_tie', model, params, *tie)
    return rec


# ---------------------------------------------------------------- comparison

def loss_kind(label):
    return 'normalized_loss' if label.endswith('/1') or label == 'floor_tie' else 'eight_step_loss'


def elementwise(tol, kind, a, b, keep=None):
    t = tol[kind]; d = (a-b).abs(); limit = t['atol']+t['rtol']*b.abs()
    bad = (d > limit) | ~a.isfinite()
    if keep is not None:
        bad &= keep
    idx = bad.nonzero().flatten()[:20].tolist()
    return {'elements': a.numel() if keep is None else int(keep.sum()), 'failing': int(bad.sum()),
            'max_abs': float((d if keep is None else d*keep).max()), 'max_ratio': float(((d/limit) if keep is None else (d/limit)*keep).max()),
            'examples': [{'index': i, 'value': float(a[i]), 'reference': float(b[i])} for i in idx]}


def global_l2(torch, tol, a_list, b_list):
    norm = sum(float((b*b).sum()) for b in b_list); delta = sum(float(((a-b)**2).sum()) for a, b in zip(a_list, b_list))
    cand = sum(float((a*a).sum()) for a in a_list); t = tol['gradient']
    if norm > 0:
        rel = (delta/norm)**.5
        return {'relative_L2': rel, 'pass': rel <= t['relative_L2_max']}
    return {'candidate_L2': cand**.5, 'pass': cand**.5 <= t['atol']}


def gradient_checks(torch, tol, label, names, a, b):
    """Loss, norm, coefficient and raw/clipped gradients of one update: R0.1 gradient rule."""
    rows = {'loss': elementwise(tol, loss_kind(label), a[f'{label}/loss'], b[f'{label}/loss'])}
    for k in ('norm', 'coefficient'):
        rows[k] = elementwise(tol, 'gradient', a[f'{label}/{k}'], b[f'{label}/{k}'])
    for kind in ('raw', 'clipped'):
        per = {n: elementwise(tol, 'gradient', a[f'{label}/{kind}/{n}'], b[f'{label}/{kind}/{n}']) for n in names}
        rows[kind] = {'failing': sum(r['failing'] for r in per.values()), 'max_ratio': max(r['max_ratio'] for r in per.values()),
                      'failures': {n: r for n, r in per.items() if r['failing']},
                      'global': global_l2(torch, tol, [a[f'{label}/{kind}/{n}'] for n in names], [b[f'{label}/{kind}/{n}'] for n in names])}
    ok = all(rows[k]['failing'] == 0 for k in ('loss', 'norm', 'coefficient')) and \
        all(rows[k]['failing'] == 0 and rows[k]['global']['pass'] for k in ('raw', 'clipped'))
    return rows, ok


def compare(torch, tol, names, rust, ref):
    """R0.2: loss/gradients/moments on all elements, parameters on the clipped-gradient mask."""
    out = {}; ok = True; worst_exclusion = 0.
    runs = {'one_update': 1, 'eight_updates': UPDATES, 'mature_import': 1}
    total = sum(ref[f'one_update/1/param/{n}'].numel() for n in names)
    for run, count in runs.items():
        keep = {n: torch.ones(ref[f'{run}/1/param/{n}'].numel(), dtype=torch.bool) for n in names}
        for u in range(1, count+1):
            label = f'{run}/{u}'; rows, good = gradient_checks(torch, tol, label, names, rust, ref)
            for n in names:  # the reference clipped gradient handed to AdamW, at every update so far
                keep[n] &= ref[f'{label}/clipped/{n}'].abs() >= K_EPS
            kind = 'one_step_parameter' if u == 1 else 'eight_step_parameter'
            params = {n: elementwise(tol, kind, rust[f'{label}/param/{n}'], ref[f'{label}/param/{n}'], keep[n]) for n in names}
            excluded = {n: (~keep[n]).nonzero().flatten().tolist() for n in names if not bool(keep[n].all())}
            fraction = sum(len(v) for v in excluded.values())/total; worst_exclusion = max(worst_exclusion, fraction)
            moments = {}
            for key, k2 in (('m', 'first_moment'), ('v', 'second_moment')):
                per = {n: elementwise(tol, k2, rust[f'{label}/{key}/{n}'], ref[f'{label}/{key}/{n}']) for n in names}
                moments[k2] = {'failing': sum(r['failing'] for r in per.values()), 'max_ratio': max(r['max_ratio'] for r in per.values()),
                               'failures': {n: r for n, r in per.items() if r['failing']}}
            rows['parameters'] = {'kind': kind, 'compared': sum(r['elements'] for r in params.values()),
                                  'failing': sum(r['failing'] for r in params.values()),
                                  'max_ratio': max(r['max_ratio'] for r in params.values()),
                                  'failures': {n: r for n, r in params.items() if r['failing']},
                                  'excluded_fraction': fraction, 'excluded': excluded}
            rows['moments'] = moments
            rows['forward_recorded'] = {'max_abs': float((rust[f'{label}/forward']-ref[f'{label}/forward']).abs().max())}
            good = good and rows['parameters']['failing'] == 0 and all(m['failing'] == 0 for m in moments.values())
            out[label] = rows; ok = ok and good
    rows, good = gradient_checks(torch, tol, 'floor_tie', names, rust, ref)
    out['floor_tie'] = rows
    return out, ok and good, worst_exclusion


# ---------------------------------------------------------------- Rust processes

WRAPPER = ("import os,subprocess,sys;p=subprocess.Popen(sys.argv[1:],stdout=subprocess.DEVNULL);"
           "_,s,u=os.wait4(p.pid,0);print(os.waitstatus_to_exitcode(s),u.ru_maxrss)")


def child(*args):
    """One Rust process under the contract's limits; returns wall time and peak RSS. A small
    Python wrapper without Torch forks the child, so the peak does not inherit this process's."""
    start = time.monotonic()
    done = subprocess.run(['/usr/bin/python3', '-I', '-c', WRAPPER, str(EXAMPLE), *map(str, args)],
                          cwd=ROOT, capture_output=True, text=True, timeout=870)
    elapsed = time.monotonic()-start
    code, peak_kb = map(int, done.stdout.split())
    if code != 0:
        raise RuntimeError(f'Rust {args[0]} failed with status {code}: {done.stderr[-2000:]}')
    if peak_kb*1024 > 2 << 30:
        raise RuntimeError(f'Rust {args[0]} exceeded the memory limit: {peak_kb} KB')
    return {'mode': args[0], 'seconds': elapsed, 'peak_rss_bytes': peak_kb*1024}


def main(output, synthetic):
    import torch
    import small_model
    import r2p_full_model_reference as ref64
    torch.set_num_threads(1); torch.set_num_interop_threads(1); torch.use_deterministic_algorithms(True)
    started = time.monotonic()
    out = ROOT/output; out.mkdir(parents=True)
    cfg = json.loads(R0.read_bytes()); contract = json.loads(CONTRACT.read_bytes()); tol = cfg['tolerance']
    src = sources()
    if not synthetic:
        assert src['worktree_clean'], 'formal R2 runs from a committed tree'
    write_new(out/'sources.json', {**src, 'synthetic': synthetic, 'torch': torch.__version__, 'python': sys.version.split()[0]})
    recipe = {'lr': 3e-4, 'betas': [0.9, 0.999], 'eps': 1e-8, 'weight_decay': 0.01, 'clip_global_norm': 1.0}
    state, moments, step, batches = synthetic_inputs(torch) if synthetic else care_inputs(torch, contract, cfg)
    names = [n for n, _ in small_model.SmallForecaster(torch.tensor([0.5, 0.25, 0.125])).named_parameters()]
    assert len(names) == 59 and sum(state[n].numel() for n in names) == 109024
    tie = floor_tie(state['scale_floor'].tolist())
    fixture_sha = write_fixture(torch, out/'fixture', names, state, moments, step, batches, tie, recipe)

    # Reference: float32, checked against float64 on loss and gradients, then frozen.
    f32 = torch_run(torch, small_model, ref64, torch.float32, names, state, moments, step, batches, tie, recipe)
    f64 = torch_run(torch, small_model, ref64, torch.float64, names, state, moments, step, batches, tie, recipe)
    labels = ['one_update/1', *[f'eight_updates/{u}' for u in range(1, UPDATES+1)], 'mature_import/1', 'floor_tie']
    check = {}; check_ok = True
    for label in labels:
        rows, good = gradient_checks(torch, tol, label, names, f32, f64); check[label] = rows; check_ok &= good
    payload = Payload()
    for name, t in f32.items():
        payload.put(name, [t.numel()], t.float().tolist())
    payload.save(out/'reference', 'records.f32', 'records.json', {'dtype': 'float32', 'torch': torch.__version__,
                                                                   'fixture_sha256': fixture_sha, 'float64_check_pass': check_ok})
    write_new(out/'reference'/'float64-check.json', check)
    close(out/'reference')
    summary = {'synthetic': synthetic, 'fixture_sha256': fixture_sha, 'reference_closure_sha256': digest(out/'reference'/'root-closed.json'),
               'float64_check_pass': check_ok}
    if not check_ok:
        summary['result'] = 'stopped: float64 check of the reference failed (no Rust run)'
        write_new(out/'summary.json', summary); close(out); print(json.dumps(summary, indent=1)); return 1

    # Rust: build outside the limits, then the processes.
    t0 = time.monotonic()
    subprocess.run(['cargo', 'build', '--release', '--locked', '-q', '-p', 'banto-ai', '--example', 'r2_formal'], cwd=ROOT, check=True)
    build_seconds = time.monotonic()-t0
    processes = [child('cases', out/'fixture', fixture_sha, out/'rust-cases'),
                 child('resume-first', out/'fixture', fixture_sha, out/'rust-checkpoint'),
                 child('resume-second', out/'fixture', fixture_sha, out/'rust-checkpoint', out/'rust-resume')]
    for d in ('rust-cases', 'rust-checkpoint', 'rust-resume'):
        close(out/d)
    _, rust = load_records(torch, out/'rust-cases'); resume_layout, resume = load_records(torch, out/'rust-resume')
    _, reference = load_records(torch, out/'reference')
    rust_v = {n: v for n, (_, v) in rust.items()}; ref_v = {n: v for n, (_, v) in reference.items()}
    assert set(rust_v) == set(ref_v), 'record names differ'
    comparisons, numeric_ok, worst_exclusion = compare(torch, tol, names, rust_v, ref_v)
    resume_names = [n for n in resume if not n.startswith('resume/1/') and not n.startswith('resume/2/')
                    and not n.startswith('resume/3/') and not n.startswith('resume/4/')]
    mismatched = [n for n in resume_names if resume[n][0] != rust['eight_updates/'+n.split('/', 1)[1]][0]]
    rl = json.loads((out/'rust-cases'/'records.json').read_bytes())['run']
    resume_ok = (not mismatched and len(resume_names) == 4*(5*59+4) and resume_layout['run']['restored_position'] == 4
                 and resume_layout['run']['steps']['resume'] == rl['steps']['eight_updates'] == UPDATES)
    write_new(out/'comparisons.json', comparisons)
    summary.update({
        'numeric_pass': numeric_ok, 'resume_byte_exact': resume_ok, 'resume_mismatched_records': mismatched[:20],
        'max_excluded_fraction': worst_exclusion, 'exclusion_stop_rule_triggered': worst_exclusion > 0.10,
        'build_seconds': build_seconds, 'processes': processes, 'parent_seconds': time.monotonic()-started,
        'per_update': {label: {'loss_ratio': r['loss']['max_ratio'], 'raw_gradient_max_ratio': r['raw']['max_ratio'],
                               'raw_relative_L2': r['raw']['global'].get('relative_L2'),
                               'clipped_relative_L2': r['clipped']['global'].get('relative_L2'),
                               'norm': float(ref_v[f'{label}/norm'][0]), 'coefficient': float(ref_v[f'{label}/coefficient'][0]),
                               **({'parameter_failing': r['parameters']['failing'], 'parameter_max_ratio': r['parameters']['max_ratio'],
                                   'excluded_fraction': r['parameters']['excluded_fraction'],
                                   'moment_failing': {k: m['failing'] for k, m in r['moments'].items()},
                                   'forward_max_abs': r['forward_recorded']['max_abs']} if 'parameters' in r else {})}
                        for label, r in comparisons.items()},
    })
    summary['result'] = 'pass' if numeric_ok and resume_ok and worst_exclusion <= 0.10 else 'fail'
    write_new(out/'summary.json', summary); close(out)
    print(json.dumps({k: v for k, v in summary.items() if k != 'per_update'}, indent=1))
    return 0 if summary['result'] == 'pass' else 1


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--output', required=True); p.add_argument('--synthetic', action='store_true')
    a = p.parse_args(); sys.exit(main(a.output, a.synthetic))
