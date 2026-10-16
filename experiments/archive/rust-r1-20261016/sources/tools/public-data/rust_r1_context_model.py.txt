"""Declare one combined general normalization candidate and gate its prefix."""
import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'models/mini-transformer'),str(ROOT/'tools/public-data')]
from metropt_multiday import Files,digest,verify_closed
from macos_demand_runtime import MacCheckpoint
CONFIG=ROOT/'examples/configs/rust-r1-context-model-20261016.json'
DECL=ROOT/'artifacts/rust-r1-context-model-declaration-20261016'

def declare():
    out=Files(DECL);status='failed';check=MacCheckpoint(seconds=870)
    try:
        names=['rust-r1-context-audit-20261016','rust-r1-fma-local-comparison-20261016','rust-r1-python-reference-20261016']
        roots=[ROOT/'artifacts'/n for n in names]
        for p in roots:verify_closed(p)
        assert json.loads((roots[0]/'summary.json').read_bytes())['local_gate_pass']
        assert json.loads((roots[1]/'summary.json').read_bytes())['candidate_bit_exact_inputs']==49
        assert digest(ROOT/'crates/banto-ai/src/model.rs')=='acefec42e7506d807f7deae22269f30f9bf409a8c8cf9d1ddb59c2ef6af7fa80'
        paths=[Path(__file__),CONFIG,ROOT/'Cargo.lock',ROOT/'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json',*[ROOT/'crates/banto-ai'/n for n in ['src/model.rs','src/lib.rs','src/fma.rs','Cargo.toml']]]
        out.sources(paths);out.json('phase.json',json.loads(CONFIG.read_bytes()));out.json('source-pins.json',[{'path':str(p.relative_to(ROOT)),'sha256':digest(p)} for p in paths]);out.json('root-pins.json',[{'path':str(p.relative_to(ROOT)),'sha256':digest(p/'root-closed.json')} for p in roots])
        out.write('model.rs.before',(ROOT/'crates/banto-ai/src/model.rs').read_bytes());out.write('Cargo.toml.before',(ROOT/'crates/banto-ai/Cargo.toml').read_bytes());out.json('summary.json',{'declared_before_new_Rust_kernel':True,'model_candidates':1,'resources':check.check()});print(json.dumps({'declared':True}));status='complete'
    finally:out.close(status)

def compare():
    out=Files(ROOT/'artifacts/rust-r1-context-local-comparison-20261016');status='failed';check=MacCheckpoint(seconds=870);passed=False
    try:
        verify_closed(DECL)
        for p in json.loads((DECL/'root-pins.json').read_bytes()):verify_closed(ROOT/p['path']);assert digest(ROOT/p['path']/'root-closed.json')==p['sha256']
        a=ROOT/'artifacts/rust-r1-context-audit-20261016';b=ROOT/'artifacts/rust-r1-context-local-kernel-20261016'
        verify_closed(a);verify_closed(b)
        am=json.loads((a/'manifest.json').read_bytes());bm=json.loads((b/'manifest.json').read_bytes());ar=(a/'tensors.bin').read_bytes();br=(b/'tensors.bin').read_bytes()
        assert digest(a/'tensors.bin')==am['payload_sha256'] and digest(b/'tensors.bin')==bm['payload_sha256']
        assert bm['fixture_manifest_sha256']==digest(a/'manifest.json')
        def blob(raw,e):return raw[e['offset_bytes']:e['offset_bytes']+e['length_bytes']]
        results=[]
        for cid in ['train-first','train-last','zero','constant','floor-below','floor-equal','floor-above']:
            for node in ['context_center','raw_std','context_scale','normalized_context']:
                for kind,target in [('baseline','baseline'),('plain','native'),('autodiff','native')]:
                    ae=am['tensors'][cid+'/'+target+'/'+node];be=bm['tensors'][cid+'/'+kind+'/'+node]
                    assert ae['shape']==be['shape'];results.append({'case':cid,'node':node,'kind':kind,'byte_exact':blob(ar,ae)==blob(br,be),'elements':ae['length_bytes']//4})
        kernel=json.loads((b/'summary.json').read_bytes());assert kernel['tracked_outputs']==28 and kernel['backward_calls']==0 and kernel['input_unchanged']
        passed=all(r['byte_exact'] for r in results)
        out.sources([Path(__file__),CONFIG,ROOT/'crates/banto-ai/src/context.rs',ROOT/'crates/banto-ai/examples/diagnose_context.rs']);out.json('comparisons.json',results);out.json('summary.json',{'local_gate_pass':passed,'comparisons':84,'bit_exact_comparisons':sum(r['byte_exact'] for r in results),'tracked_outputs':28,'full_forward':0,'training':False,'resources':check.check()});print(json.dumps({'local_gate_pass':passed,'bit_exact_comparisons':sum(r['byte_exact'] for r in results),'comparisons':84}));status='complete'
    finally:out.close(status)
    return 0 if passed else 1

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['declare','compare']);a=p.parse_args()
    if a.phase=='declare':declare()
    else:sys.exit(compare())
