"""Predeclare a single uniform LayerNorm integration and verify its local gate."""
import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'models/mini-transformer'),str(ROOT/'tools/public-data')]
from metropt_multiday import Files,digest,verify_closed
from macos_demand_runtime import MacCheckpoint
CONFIG=ROOT/'examples/configs/rust-r1-fma-model-20261016.json'
DECLARATION=ROOT/'artifacts/rust-r1-fma-model-declaration-20261016'


def declare():
    out=Files(DECLARATION);status='failed';check=MacCheckpoint(seconds=870)
    try:
        roots=[ROOT/'artifacts'/n for n in ['rust-r1-fma-probe4-20261016','rust-r1-layer-fixture2-20261016','rust-r1-layer-kernel-20261016','rust-r1-python-reference-20261016']]
        for p in roots:verify_closed(p)
        probe=json.loads((roots[0]/'summary.json').read_bytes());assert probe['plain_bits']==probe['autodiff_bits']==20 and probe['tracked_output'] and probe['backward_calls']==0
        assert digest(ROOT/'crates/banto-ai/src/model.rs')=='acefec42e7506d807f7deae22269f30f9bf409a8c8cf9d1ddb59c2ef6af7fa80'
        paths=[Path(__file__),CONFIG,*[ROOT/'crates/banto-ai'/p for p in ['Cargo.toml','src/lib.rs','src/fma.rs','src/model.rs']],ROOT/'Cargo.lock',ROOT/'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json']
        out.sources(paths);out.json('phase.json',json.loads(CONFIG.read_bytes()))
        out.json('source-pins-before.json',[{'path':str(p.relative_to(ROOT)),'sha256':digest(p)} for p in paths])
        out.json('root-pins.json',[{'path':str(p.relative_to(ROOT)),'closure_sha256':digest(p/'root-closed.json')} for p in roots])
        out.write('model.rs.before',(ROOT/'crates/banto-ai/src/model.rs').read_bytes());out.write('Cargo.toml.before',(ROOT/'crates/banto-ai/Cargo.toml').read_bytes())
        out.json('summary.json',{'model_candidates':1,'kernels_before_declaration':0,'training':False,'resources':check.check()})
        print(json.dumps({'declared':True}));status='complete'
    finally:out.close(status)


def compare():
    out=Files(ROOT/'artifacts/rust-r1-fma-local-comparison-20261016');status='failed';check=MacCheckpoint(seconds=870);passed=False
    try:
        verify_closed(DECLARATION)
        for p in json.loads((DECLARATION/'root-pins.json').read_bytes()):assert digest(ROOT/p['path']/'root-closed.json')==p['closure_sha256']
        roots=[ROOT/'artifacts'/n for n in ['rust-r1-layer-fixture2-20261016','rust-r1-layer-kernel-20261016','rust-r1-fma-local-kernel-20261016']]
        for p in roots:verify_closed(p)
        ms=[json.loads((p/'manifest.json').read_bytes()) for p in roots];raws=[(p/'tensors.bin').read_bytes() for p in roots]
        for p,m in zip(roots,ms,strict=True):assert digest(p/'tensors.bin')==m['payload_sha256']
        assert ms[1]['fixture_manifest_sha256']==ms[2]['fixture_manifest_sha256']==digest(roots[0]/'manifest.json')
        out.sources([Path(__file__),CONFIG,ROOT/'crates/banto-ai/src/fma.rs',ROOT/'crates/banto-ai/examples/diagnose_fma_norm.rs'])
        out.json('phase.json',{'declaration_sha256':digest(DECLARATION/'root-closed.json'),'local_gate':'candidate equals PP bits and baseline equals RP bytes across all inputs','training':False})
        def blob(i,key):
            e=ms[i]['tensors'][key];return raws[i][e['offset_bytes']:e['offset_bytes']+e['length_bytes']]
        rows=[];elements=0
        modules=[f'blocks.{i}.norms.{j}' for i in range(2) for j in range(3)]+['final_norm']
        for case in ms[0]['cases']:
            cid=case['id']
            for name in modules:
                pp=blob(0,cid+'/pp/'+name);rp=blob(1,cid+'/rp/'+name)
                base=blob(2,cid+'/baseline/'+name);candidate=blob(2,cid+'/candidate/'+name)
                rows.append({'case':cid,'module':name,'baseline_RP_byte_exact':base==rp,'candidate_PP_bit_exact':candidate==pp});elements+=len(pp)//4
            check.check()
        passed=all(r['baseline_RP_byte_exact'] and r['candidate_PP_bit_exact'] for r in rows)
        assert len(rows)==49 and elements==124992
        out.json('comparisons.json',rows);out.json('summary.json',{'local_gate_pass':passed,'comparisons':49,'elements':elements,'candidate_bit_exact_inputs':sum(r['candidate_PP_bit_exact'] for r in rows),'baseline_byte_exact_inputs':sum(r['baseline_RP_byte_exact'] for r in rows),'model_hooked':False,'resources':check.check()})
        print(json.dumps({'local_gate_pass':passed,'comparisons':49,'elements':elements}));status='complete'
    finally:out.close(status)
    return 0 if passed else 1


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['declare','compare']);a=p.parse_args()
    if a.phase=='declare':declare()
    else:sys.exit(compare())
