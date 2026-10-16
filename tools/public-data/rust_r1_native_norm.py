"""One standard LayerNorm candidate: declare before kernels, then score all inputs."""
import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'tools'), str(ROOT/'models/mini-transformer'), str(ROOT/'tools/public-data')]
from metropt_multiday import Files, digest, verify_closed
from macos_demand_runtime import MacCheckpoint
from rust_r1_compare import floats

CONFIG = ROOT/'examples/configs/rust-r1-native-norm-20261016.json'
DECLARATION = ROOT/'artifacts/rust-r1-native-norm-declaration-20261016'
KERNEL = ROOT/'artifacts/rust-r1-native-norm-kernel-20261016'


def declare():
    out = Files(DECLARATION)
    status = 'failed'
    check = MacCheckpoint(seconds=870)
    try:
        c = json.loads(CONFIG.read_bytes())
        roots = [ROOT/c[k] for k in ['fixture', 'baseline_kernel']]
        pins = []
        for p in roots:
            verify_closed(p)
            pins.append({'path':str(p.relative_to(ROOT)), 'closure_sha256':digest(p/'root-closed.json')})
        local = ROOT/'environments/rust-cpu/cargo-home/registry/src/index.crates.io-1949cf8c6b5b557f'
        paths = [CONFIG, Path(__file__), ROOT/'crates/banto-ai/examples/diagnose_native_norm.rs',
                 ROOT/'crates/banto-ai/src/model.rs', ROOT/'Cargo.lock',
                 ROOT/'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json',
                 local/'burn-flex-0.22.0/src/ops/activation.rs',
                 local/'burn-tensor-0.22.0/src/tensor/module.rs']
        assert digest(ROOT/'crates/banto-ai/src/model.rs') == 'acefec42e7506d807f7deae22269f30f9bf409a8c8cf9d1ddb59c2ef6af7fa80'
        source_pins = [{'path':str(p.relative_to(ROOT)), 'sha256':digest(p)} for p in paths]
        out.sources(paths)
        out.json('phase.json', c)
        out.json('source-pins.json', source_pins)
        out.json('root-pins.json', pins)
        out.json('summary.json', {'phase':'preregistered before candidate kernels', 'candidate_count':1,
                                 'candidate_kernel_calls':0, 'training':False, 'resources':check.check()})
        status = 'complete'
        print(json.dumps({'declared':True, 'fixture_manifest_sha256':digest(roots[0]/'manifest.json')}))
    finally:
        out.close(status)


def compare():
    out = Files(ROOT/'artifacts/rust-r1-native-norm-comparison-20261016')
    status = 'failed'
    check = MacCheckpoint(seconds=870)
    try:
        verify_closed(DECLARATION)
        for pin in json.loads((DECLARATION/'source-pins.json').read_bytes()):
            assert digest(ROOT/pin['path']) == pin['sha256'], pin['path']
        c = json.loads(CONFIG.read_bytes())
        fixture = ROOT/c['fixture']
        baseline = ROOT/c['baseline_kernel']
        for root in [fixture, baseline, KERNEL]:
            verify_closed(root)
        for pin in json.loads((DECLARATION/'root-pins.json').read_bytes()):
            assert digest(ROOT/pin['path']/'root-closed.json') == pin['closure_sha256']
        manifests = [json.loads((p/'manifest.json').read_bytes()) for p in [fixture,baseline,KERNEL]]
        payloads = [(p/'tensors.bin').read_bytes() for p in [fixture,baseline,KERNEL]]
        for m,p,b in zip(manifests,[fixture,baseline,KERNEL],payloads,strict=True):
            assert digest(p/'tensors.bin') == m['payload_sha256']
        lm,bm,km = manifests
        lb,bb,kb = payloads
        assert bm['fixture_manifest_sha256'] == km['fixture_manifest_sha256'] == digest(fixture/'manifest.json')
        out.sources([Path(__file__),CONFIG,ROOT/'crates/banto-ai/examples/diagnose_native_norm.rs'])
        out.json('phase.json', {'declaration_sha256':digest(DECLARATION/'root-closed.json'),
                               'scope':'49 same-input comparisons; no forward, training, labels or point-based selection'})
        rows = []
        per_case = []
        baseline_exact = 0
        for case in c['cases']:
            case_rows = []
            for name in c['modules']:
                ref = lm['tensors'][case+'/pp/'+name]
                old = bm['tensors'][case+'/rp/'+name]
                replay = km['tensors'][case+'/baseline/'+name]
                candidate = km['tensors'][case+'/candidate/'+name]
                def raw(b,e): return b[e['offset_bytes']:e['offset_bytes']+e['length_bytes']]
                assert raw(bb,old) == raw(kb,replay), (case,name,'baseline anchor mismatch')
                baseline_exact += 1
                xs = floats(lb,ref)
                ys = floats(kb,replay)
                zs = floats(kb,candidate)
                assert len(xs) == len(ys) == len(zs)
                def metric(vs):
                    assert all(math.isfinite(v) for v in vs)
                    errors = [abs(y-x) for x,y in zip(xs,vs,strict=True)]
                    limits = [2e-6+2e-5*abs(x) for x in xs]
                    return {'elements':len(xs), 'SSE':math.fsum(e*e for e in errors),
                            'max_abs':max(errors), 'max_tolerance_ratio':max(e/t for e,t in zip(errors,limits,strict=True)),
                            'failing_elements':sum(e>t for e,t in zip(errors,limits,strict=True))}
                row = {'case':case, 'module':name, 'baseline':metric(ys), 'candidate':metric(zs)}
                rows.append(row)
                case_rows.append(row)
            base = math.fsum(r['baseline']['SSE'] for r in case_rows)
            candidate = math.fsum(r['candidate']['SSE'] for r in case_rows)
            per_case.append({'case':case,'baseline_SSE':base,'candidate_SSE':candidate,'nonincrease':candidate<=base})
            check.check()
        total_base = math.fsum(r['baseline']['SSE'] for r in rows)
        total_candidate = math.fsum(r['candidate']['SSE'] for r in rows)
        bad = sum(r['candidate']['failing_elements'] for r in rows)
        gate = baseline_exact==49 and bad==0 and total_candidate<total_base and all(r['nonincrease'] for r in per_case)
        summary = {'comparisons':len(rows), 'baseline_byte_exact':baseline_exact,
                   'elements_per_method':sum(r['candidate']['elements'] for r in rows),
                   'baseline_SSE':total_base,'candidate_SSE':total_candidate,
                   'candidate_failing_elements':bad,'case_SSE_nonincrease_count':sum(r['nonincrease'] for r in per_case),
                   'local_gate_pass':gate,'core_changed':False,'R1_complete':False,'R2_started':False,
                   'full_forward_calls':0,'training':False,'resources':check.check()}
        out.json('module-comparisons.json',rows)
        out.json('case-comparisons.json',per_case)
        out.json('summary.json',summary)
        print(json.dumps(summary))
        status = 'complete'
    finally:
        out.close(status)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('phase', choices=['declare','compare'])
    a = p.parse_args()
    declare() if a.phase == 'declare' else compare()
