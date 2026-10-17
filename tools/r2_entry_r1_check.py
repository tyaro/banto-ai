"""Formal R2 entry check (R0.2): R1 numeric conditions re-run on the R2 platform.

Repeats the saved Mac R1 procedure with this machine's Torch and Rust, unchanged R0.1
tolerances and the same 7 fixed cases (two saved fold0 train batches, five artificial):

1. Torch reference forward with the 23 named R1 traces;
2. Rust `predict` example (the crate's own traced forward);
3. original R1 comparison of all 23 traces (389,214 elements), final outputs separately;
4. Torch functional replay at the 55 fixed nodes, byte-equal to the hooked traces;
5. Rust `r1_layer_audit` example: own path (byte-equal to step 2) and same-input kernels;
6. 385 same-input local comparisons (RP-PP) and the total/propagated decomposition.

Entry needs final outputs and the 385 local comparisons within R0.1; the cumulative
intermediate comparison is recorded as a diagnostic (R0.2). No training, no CARE test or
truth access. Writes only under --output (a new directory, gitignored artifacts/).

    <python with torch> tools/r2_entry_r1_check.py --output artifacts/r2-entry-r1-20261017
"""
import argparse
import hashlib
import json
import math
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'models/mini-transformer'))
CONFIG = ROOT/'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json'
MAC_FIXTURE = ROOT/'artifacts/rust-r1-layer-fixture2-20261016'
MAC_KERNEL = ROOT/'artifacts/rust-r1-layer-kernel-20261016'
CASES = ['train-first', 'train-last', 'zero', 'constant', 'floor-below', 'floor-equal', 'floor-above']
HOOKED = ['patch', 'final_norm', 'head', 'blocks.0', 'blocks.1'] + [
    f'blocks.{i}.{v}' for i in range(2) for v in ['norms.0', 'norms.1', 'norms.2', 'temporal', 'variate', 'ff.1']]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def floats(raw, e):
    b = raw[e['offset_bytes']:e['offset_bytes']+e['length_bytes']]
    assert len(b) == e['length_bytes'] == math.prod(e['shape'])*4
    return [v[0] for v in struct.iter_unpack('<f', b)]


def pack(values):
    return struct.pack(f'<{len(values)}f', *values)


def write_new(path, raw):
    with open(path, 'xb') as f:
        f.write(raw if isinstance(raw, bytes) else json.dumps(raw, indent=1).encode())


def close(root):
    """Closure record; a sub-root is listed by the hash of its own closure record."""
    files = [{'name': p.name, 'bytes': p.stat().st_size, 'sha256': digest(p)} if p.is_file()
             else {'name': p.name+'/', 'root_closed_sha256': digest(p/'root-closed.json')} for p in sorted(root.iterdir())]
    write_new(root/'root-closed.json', {'status': 'complete', 'files': files})


def cargo_example(name, *args):
    cmd = ['cargo', 'run', '--release', '--locked', '-q', '-p', 'banto-ai', '--example', name, '--', *map(str, args)]
    subprocess.run(cmd, cwd=ROOT, check=True)


def non_numeric():
    """The non-numeric R1 items: locked toolchain/backend, effective license graph, the crate's artificial cases."""
    def run(*cmd, env=None):
        import os
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env={**os.environ, **(env or {})})
        return r.returncode, r.stdout
    _, rustc = run('rustc', '-vV')
    code, tree = run('cargo', 'tree', '-e', 'normal', '--locked', '-p', 'banto-ai', '--prefix', 'none', '--format', '{p}|{l}')
    assert code == 0
    packages = sorted({line.removesuffix(' (*)') for line in tree.splitlines() if line})
    tests = {}
    for label, cmd, env in [('crate_unit_tests', ['--lib'], None),
                            ('neutral_integrity', ['--features', 'reference-tests', '--test', 'neutral_integrity'], {'BANTO_R1_REPO': str(ROOT)})]:
        code, out = run('cargo', 'test', '--locked', '-p', 'banto-ai', *cmd, env=env)
        tests[label] = {'exit': code, 'results': [l for l in out.splitlines() if l.startswith(('test ', 'test result'))]}
        assert code == 0, label
    return {'rustc': rustc.split(), 'cargo_lock_sha256': digest(ROOT/'Cargo.lock'),
            'effective_normal_graph': {'packages': len(packages), 'listing': packages,
                                       'licenses': {l: sum(p.split('|')[1] == l for p in packages) for l in sorted({p.split('|')[1] for p in packages})}},
            'tests': tests}


def load_model(torch, cfg):
    from small_model import SmallForecaster
    layout = json.loads((ROOT/cfg['references'][1]['path']).read_bytes())
    weights = (ROOT/cfg['references'][0]['path']).read_bytes()
    state = {}
    for e in layout['tensors']:
        if not e['name'].startswith('model::'):
            continue
        b = weights[e['offset_bytes']:e['offset_bytes']+e['length_bytes']]
        if e['dtype'] == 'float32-le':
            t = torch.tensor([x[0] for x in struct.iter_unpack('<f', b)], dtype=torch.float32)
        else:
            t = torch.tensor(list(b), dtype=torch.bool)
        state[e['name'][7:]] = t.reshape(e['shape'])
    model = SmallForecaster(state['scale_floor'], series_attention='full')
    model.load_state_dict(state, strict=True)
    return model.eval(), state


def build_cases(torch, cfg, state):
    raw = (ROOT/cfg['references'][2]['path']).read_bytes()
    cases = []
    for step, name in enumerate(CASES[:2]):
        batch = [struct.unpack_from('<384f', raw, (step*8+i)*(384+96)*4) for i in range(8)]
        cases.append((name, torch.tensor(batch, dtype=torch.float32).reshape(8, 3, 128)))
    floors = state['scale_floor'].tolist()
    cases.append(('zero', torch.zeros([1, 3, 128])))
    cases.append(('constant', torch.tensor([3.25, -1.5, 0.]).reshape(1, 3, 1).expand(1, 3, 128).contiguous()))
    for level, name in [(.5, 'floor-below'), (1., 'floor-equal'), (2., 'floor-above')]:
        cases.append((name, torch.tensor([[[f*level*(-1 if t % 2 else 1) for t in range(128)] for f in floors]],
                                         dtype=torch.float32)))
    return cases


def reference(torch, model, cases, out):
    """Step 1: hooked forward, same trace names and order as the saved Mac reference."""
    inputs = bytearray(); traces = bytearray(); index = []; hooked = {}
    for name, x in cases:
        collected = {}; handles = []
        for n, m in model.named_modules():
            if n in HOOKED:
                handles.append(m.register_forward_hook(lambda m, a, y, n=n: collected.__setitem__(n, y.detach().clone())))
        handles.append(model.blocks[0].register_forward_pre_hook(lambda m, a: collected.__setitem__('tokens', a[0].detach().clone())))
        with torch.no_grad():
            f = model(x)
        for h in handles:
            h.remove()
        collected.update(context_center=f.mean, context_scale=f.scale, normalized_context=(x-f.mean)/f.scale,
                         normalized_quantiles=f.normalized, quantiles=f.quantiles)
        q = f.quantiles
        assert bool((q[..., 0] <= q[..., 1]).all()) and bool((q[..., 1] <= q[..., 2]).all())
        offset = len(inputs); inputs += pack(x.flatten().tolist()); entries = []
        for key, t in collected.items():
            assert bool(torch.isfinite(t).all())
            start = len(traces); traces += pack(t.flatten().tolist())
            entries.append({'name': key, 'shape': list(t.shape), 'offset_bytes': start, 'length_bytes': len(traces)-start})
        if name.startswith('floor-'):  # this platform must take the floor branch exactly as the Mac R1 did
            floors = model.scale_floor.tolist(); std = x.std(dim=-1, correction=0).flatten().tolist(); scale = f.scale.flatten().tolist()
            assert {'floor-equal': std == floors, 'floor-below': scale == floors, 'floor-above': all(a > b for a, b in zip(scale, floors))}[name], name
        hooked[name] = collected
        index.append({'id': name, 'batch': x.shape[0], 'offset_bytes': offset, 'length_bytes': len(inputs)-offset, 'traces': entries})
    out.mkdir()
    write_new(out/'inputs.bin', bytes(inputs)); write_new(out/'python-traces.bin', bytes(traces))
    return index, hooked, bytes(inputs), bytes(traces)


def original_compare(cfg, index, ref_raw, rust_dir, train_scale32):
    """Step 3: the original R1 rule on all 23 traces; final outputs reported separately."""
    layout = json.loads((rust_dir/'traces-layout.json').read_bytes()); raw = (rust_dir/'rust-traces.bin').read_bytes()
    assert digest(rust_dir/'rust-traces.bin') == layout['payload_sha256']
    tol = cfg['tolerance']['normalized_activation']
    rows = []
    for left, right in zip(index, layout['cases'], strict=True):
        lt = {v['name']: v for v in left['traces']}; rt = {v['name']: v for v in right['traces']}
        assert left['id'] == right['id'] and set(lt) == set(rt)
        centers = floats(ref_raw, lt['context_center'])
        for name, e in lt.items():
            xs = floats(ref_raw, e); ys = floats(raw, rt[name]); bad = 0; worst = ratio = 0.; examples = []
            for i, (x, y) in enumerate(zip(xs, ys, strict=True)):
                if name == 'quantiles':
                    limit = 1e-4*train_scale32[(i//96) % 3]+2e-5*abs(x-centers[(i//288)*3+(i//96) % 3])
                else:
                    limit = tol['atol']+tol['rtol']*abs(x)
                err = abs(x-y) if math.isfinite(y) else math.inf
                worst = max(worst, err); ratio = max(ratio, err/limit)
                if err > limit:
                    bad += 1
                    if len(examples) < 5:
                        examples.append({'index': i, 'reference': x, 'rust': y, 'error': err, 'limit': limit})
            if name == 'quantiles':
                assert all(a <= b <= c for a, b, c in zip(ys[0::3], ys[1::3], ys[2::3], strict=True)), left['id']
            rows.append({'case': left['id'], 'tensor': name, 'elements': len(xs), 'failing_elements': bad,
                         'max_abs': worst, 'max_tolerance_ratio': ratio, 'failure_examples': examples})
    return rows, layout, raw


def layer_nodes(torch, model, state, x):
    """Step 4: the fixed 55-node functional replay bound to the reference modules."""
    import torch.nn.functional as F
    modules = dict(model.named_modules()); weights = {**dict(model.named_parameters()), **dict(model.named_buffers())}
    nodes = {}; b = x.shape[0]

    def put(n, t):
        nodes[n] = t
        return t

    def attn(z, n, causal):
        bb, nn_, _ = z.shape
        raw = [put(f'{n}.{k}', modules[f'{n}.{k}'](z)) for k in ['q', 'k', 'v']]
        q, k, v = [t.reshape(bb, nn_, 4, 16).transpose(1, 2) for t in raw]
        logits = q@k.transpose(-2, -1)/4
        if causal:
            logits = logits.masked_fill(~torch.ones(nn_, nn_, dtype=torch.bool).tril(), -torch.inf)
        put(n+'.logits', logits); p = put(n+'.probs', logits.softmax(-1))
        mixed = put(n+'.mixed', (p@v).transpose(1, 2).reshape(bb, nn_, 64))
        return put(n, modules[n+'.out'](mixed))
    mu = put('context_center', x.mean(-1, keepdim=True))
    scale = put('context_scale', torch.maximum(x.std(-1, correction=0, keepdim=True), weights['scale_floor'].reshape(1, 3, 1)))
    z = put('normalized_context', (x-mu)/scale); patch = put('patch', modules['patch'](z.reshape(b, 3, 4, 32)))
    tokens = put('tokens', torch.cat([patch, weights['horizon'].reshape(1, 1, 1, 64).expand(b, 3, 1, 64)], 2)
                 + weights['position'].reshape(1, 1, 5, 64))
    for i in range(2):
        n = f'blocks.{i}'; z = put(n+'.norms.0', modules[n+'.norms.0'](tokens))
        t = attn(z.reshape(b*3, 5, 64), n+'.temporal', True); tokens = put(n+'.residual0', tokens+t.reshape(b, 3, 5, 64))
        z = put(n+'.norms.1', modules[n+'.norms.1'](tokens)); v = attn(z.transpose(1, 2).reshape(b*5, 3, 64), n+'.variate', False)
        tokens = put(n+'.residual1', tokens+v.reshape(b, 5, 3, 64).transpose(1, 2)); z = put(n+'.norms.2', modules[n+'.norms.2'](tokens))
        h = put(n+'.ff.0', modules[n+'.ff.0'](z)); h = put(n+'.ff.1', F.gelu(h))
        ff = put(n+'.ff.2', modules[n+'.ff.2'](h)); tokens = put(n, tokens+ff)
    last = put('final_norm', modules['final_norm'](tokens[:, :, -1])); head = put('head', modules['head'](last))
    raw = head.reshape(b, 3, 32, 3); mid = raw[..., 0]
    q = put('normalized_quantiles', torch.stack([mid-F.softplus(raw[..., 1]), mid, mid+F.softplus(raw[..., 2])], -1))
    put('quantiles', q*scale[..., None]+mu[..., None])
    return nodes


def catalog():
    nodes = ['context_center', 'context_scale', 'normalized_context', 'patch', 'tokens']
    for i in range(2):
        p = f'blocks.{i}'
        for j, kind in [(0, 'temporal'), (1, 'variate')]:
            nodes.append(f'{p}.norms.{j}')
            nodes.extend(f'{p}.{kind}.{s}' for s in ['q', 'k', 'v', 'logits', 'probs', 'mixed'])
            nodes.extend([f'{p}.{kind}', f'{p}.residual{j}'])
        nodes.extend([f'{p}.norms.2', f'{p}.ff.0', f'{p}.ff.1', f'{p}.ff.2', p])
    return nodes+['final_norm', 'head', 'normalized_quantiles', 'quantiles']


def layer_compare(manifest, lb, rb, rmanifest, train_scale32, tol):
    """Step 6: signed decomposition total=RR-PP, local=RP-PP, propagated=RR-RP."""
    rows = []
    for case in manifest['cases']:
        cid = case['id']; centers = floats(lb, manifest['tensors'][cid+'/pp/context_center'])
        for node in case['nodes']:
            p = manifest['tensors'][f'{cid}/pp/{node}']
            xs = floats(lb, p); ys = floats(rb, rmanifest['tensors'][f'{cid}/rr/{node}']); zs = floats(rb, rmanifest['tensors'][f'{cid}/rp/{node}'])
            bad_t = bad_l = 0; max_t = max_l = max_p = ratio_l = 0.; mask = 0; closure = 0.; examples = []
            for i, (x, y, z) in enumerate(zip(xs, ys, zs, strict=True)):
                if not all(math.isfinite(v) for v in (x, y, z)):
                    assert node.endswith('.logits') and x == y == z == -math.inf
                    mask += 1
                    continue
                t = y-x; lo = z-x; up = y-z; closure = max(closure, abs(t-math.fsum([lo, up])))
                if node == 'quantiles':
                    limit = 1e-4*train_scale32[(i//96) % 3]+2e-5*abs(x-centers[(i//288)*3+(i//96) % 3])
                else:
                    limit = tol['atol']+tol['rtol']*abs(x)
                bad_t += abs(t) > limit; bad_l += abs(lo) > limit
                if (abs(t) > limit or abs(lo) > limit) and len(examples) < 5:
                    examples.append({'index': i, 'PP': x, 'RR': y, 'RP': z, 'total': t, 'local': lo, 'limit': limit})
                max_t = max(max_t, abs(t)); max_l = max(max_l, abs(lo)); max_p = max(max_p, abs(up)); ratio_l = max(ratio_l, abs(lo)/limit)
            assert closure == 0, (cid, node, closure)  # the decomposition is exact on stored f32
            rows.append({'case': cid, 'node': node, 'R1_original_gate': node in case['anchors'], 'elements': len(xs),
                         'mask_values': mask, 'total_failing_elements': bad_t, 'local_failing_elements': bad_l,
                         'max_abs_total': max_t, 'max_abs_local': max_l, 'max_abs_propagated': max_p,
                         'local_max_tolerance_ratio': ratio_l, 'decomposition_max_residual': closure, 'failure_examples': examples})
    return rows


def main(output):
    import torch
    torch.set_num_threads(1); torch.set_num_interop_threads(1); torch.use_deterministic_algorithms(True); torch.set_grad_enabled(False)
    out = ROOT/output; out.mkdir(parents=True)
    cfg = json.loads(CONFIG.read_bytes())
    for r in cfg['references']:
        assert digest(ROOT/r['path']) == r['sha256'], r['path']
    assert digest(ROOT/cfg['model']['source']) == cfg['model']['sha256']
    train_scale32 = [v['T32'] for v in json.loads((ROOT/cfg['references'][3]['path']).read_bytes())['normalization']]
    model, state = load_model(torch, cfg)
    cases = build_cases(torch, cfg, state)

    # The 7 inputs must be the ones the Mac R1 audit used.
    mac = json.loads((MAC_FIXTURE/'manifest.json').read_bytes()); mac_raw = (MAC_FIXTURE/'tensors.bin').read_bytes()
    assert digest(MAC_FIXTURE/'tensors.bin') == mac['payload_sha256']
    for name, x in cases:
        assert pack(x.flatten().tolist()) == pack(floats(mac_raw, mac['tensors'][name+'/input'])), name

    ref = out/'reference'
    index, hooked, inputs, ref_raw = reference(torch, model, cases, ref)
    write_new(ref/'fixtures.json', {'schema': 'banto.r1-forward-fixtures.v1', 'cases': index, 'inputs_sha256': hashlib.sha256(inputs).hexdigest(),
                                    'model_layout_sha256': cfg['references'][1]['sha256'], 'model_payload_sha256': cfg['references'][0]['sha256'],
                                    'train_scale32': train_scale32, 'torch': torch.__version__})
    close(ref)
    rust = out/'rust-predict'
    cargo_example('predict', ROOT/cfg['references'][1]['path'], ROOT/cfg['references'][0]['path'], ref/'fixtures.json', ref/'inputs.bin', rust)
    original, rust_layout, rust_raw = original_compare(cfg, index, ref_raw, rust, train_scale32)
    assert sum(r['elements'] for r in original) == 389214

    arrays = {}
    for n, t in {**dict(model.named_parameters()), **dict(model.named_buffers())}.items():
        if t.dtype == torch.float32:
            arrays['weight/'+n] = t.flatten().tolist()
    layer_cases = []; shapes = {}
    for (name, x), right in zip(cases, rust_layout['cases'], strict=True):
        nodes = layer_nodes(torch, model, state, x)
        assert list(nodes) == catalog() and len(nodes) == 55
        for key, t in hooked[name].items():  # replay must reproduce the hooked reference bytes
            assert pack(nodes[key].flatten().tolist()) == pack(t.flatten().tolist()), (name, key)
        arrays[name+'/input'] = x.flatten().tolist()
        shapes.update({f'{name}/pp/{n}': list(t.shape) for n, t in nodes.items()})
        for n, t in nodes.items():
            arrays[f'{name}/pp/{n}'] = t.flatten().tolist()
        for e in right['traces']:
            arrays[f'{name}/anchor/{e["name"]}'] = floats(rust_raw, e)
        layer_cases.append({'id': name, 'batch': x.shape[0], 'nodes': list(nodes), 'anchors': [e['name'] for e in right['traces']]})
    payload = bytearray(); entries = {}
    for key, values in arrays.items():
        if key.startswith('weight/'):
            shape = list(dict(model.named_parameters()).get(key[7:], dict(model.named_buffers()).get(key[7:])).shape)
        elif key.endswith('/input'):
            shape = [len(values)//384, 3, 128]
        elif '/anchor/' in key:
            case, _, n = key.split('/', 2); shape = shapes[f'{case}/pp/{n}']
        else:
            shape = shapes[key]
        start = len(payload); payload += pack(values)
        entries[key] = {'shape': shape, 'offset_bytes': start, 'length_bytes': len(payload)-start}
    fixture = out/'layer-fixture'; fixture.mkdir()
    write_new(fixture/'tensors.bin', bytes(payload))
    lm = {'schema': 'banto.r1-all-layer-audit.v1', 'cases': layer_cases, 'tensors': entries,
          'payload_sha256': hashlib.sha256(payload).hexdigest(), 'train_scale32': train_scale32}
    write_new(fixture/'manifest.json', lm); close(fixture)
    kernel = out/'rust-layer'
    cargo_example('r1_layer_audit', fixture/'manifest.json', fixture/'tensors.bin', digest(fixture/'manifest.json'), kernel)
    rm = json.loads((kernel/'manifest.json').read_bytes()); rb = (kernel/'tensors.bin').read_bytes()
    assert digest(kernel/'tensors.bin') == rm['payload_sha256']
    layers = layer_compare(lm, bytes(payload), rb, rm, train_scale32, cfg['tolerance']['normalized_activation'])
    assert len(layers) == 385

    # Platform differences against the saved Mac run (diagnostic only).
    mk = json.loads((MAC_KERNEL/'manifest.json').read_bytes()); mkb = (MAC_KERNEL/'tensors.bin').read_bytes()
    platform = {}
    for label, (a, araw), (b, braw) in [('torch_pp_cloud_vs_mac', (lm, payload), (mac, mac_raw)),
                                        ('rust_rr_cloud_vs_mac', (rm, rb), (mk, mkb))]:
        kind = '/pp/' if label.startswith('torch') else '/rr/'
        keys = [k for k in a['tensors'] if kind in k]
        same = sum(araw[a['tensors'][k]['offset_bytes']:][:a['tensors'][k]['length_bytes']] ==
                   braw[b['tensors'][k]['offset_bytes']:][:b['tensors'][k]['length_bytes']] for k in keys)
        worst = max(max((abs(x-y) for x, y in zip(floats(araw, a['tensors'][k]), floats(braw, b['tensors'][k]))
                         if math.isfinite(x) and math.isfinite(y)), default=0.) for k in keys)
        platform[label] = {'nodes': len(keys), 'byte_equal_nodes': same, 'max_abs_difference': worst}

    final = [r for r in original if r['tensor'] in ('normalized_quantiles', 'quantiles')]
    summary = {
        'scope': 'formal R2 entry (R0.2): R1 numeric conditions on this platform; R0.1 tolerances unchanged; no training, no CARE test/truth',
        'torch': torch.__version__, 'threads': 1,
        'inputs_equal_to_mac_R1': True, 'replay_equal_to_hooked_reference': True, 'rust_own_path_equal_to_crate_trace': True,
        'final_outputs': {'cases': 7, 'elements': sum(r['elements'] for r in final), 'failing_elements': sum(r['failing_elements'] for r in final),
                          'max_tolerance_ratio': max(r['max_tolerance_ratio'] for r in final)},
        'local_same_input': {'comparisons': len(layers), 'elements': sum(r['elements'] for r in layers),
                             'failing_elements': sum(r['local_failing_elements'] for r in layers),
                             'max_tolerance_ratio': max(r['local_max_tolerance_ratio'] for r in layers)},
        'cumulative_intermediate_diagnostic': {'elements': sum(r['elements'] for r in original), 'failing_elements': sum(r['failing_elements'] for r in original),
                                               'failures': [r for r in original if r['failing_elements']]},
        'decomposition_max_residual': max(r['decomposition_max_residual'] for r in layers),
        'platform_vs_mac': platform,
    }
    summary['entry_numeric_pass'] = summary['final_outputs']['failing_elements'] == 0 and summary['local_same_input']['failing_elements'] == 0
    write_new(out/'non-numeric.json', non_numeric())
    write_new(out/'original-comparisons.json', original); write_new(out/'layer-comparisons.json', layers); write_new(out/'summary.json', summary)
    close(out)
    print(json.dumps({k: v for k, v in summary.items() if k != 'cumulative_intermediate_diagnostic'} |
                     {'cumulative_failing': summary['cumulative_intermediate_diagnostic']['failing_elements']}, indent=1))
    return 0 if summary['entry_numeric_pass'] else 1


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--output', required=True)
    sys.exit(main(p.parse_args().output))
