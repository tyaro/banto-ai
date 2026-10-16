"""Single instruction-derived replay for all five saved synthetic patch cases."""
import argparse
import ctypes
import json
import re
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'models/mini-transformer'),str(ROOT/'tools/public-data')]
from metropt_multiday import Files,digest,verify_closed
from macos_demand_runtime import MacCheckpoint
from rust_r1_compare import floats
from rust_r1_moments_audit import f32,packed,metrics
CONFIG=ROOT/'examples/configs/rust-r1-sgemm-small-replay-20261016.json'
DECL=ROOT/'artifacts/rust-r1-sgemm-small-replay-declaration-20261016'
NAMES=['rust-r1-sgemm-small-tn-20261016','rust-r1-linear-python-20261016','rust-r1-linear-kernel-20261016']
def sources():return [Path(__file__),CONFIG,ROOT/'tools/public-data/rust_r1_compare.py',ROOT/'tools/public-data/rust_r1_moments_audit.py',ROOT/'crates/banto-ai/src/model.rs',ROOT/'Cargo.lock',ROOT/'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json']
def declare():
    out=Files(DECL);status='failed';check=MacCheckpoint(seconds=870)
    try:
        roots=[ROOT/'artifacts'/n for n in NAMES]
        for p in roots:verify_closed(p)
        c=json.loads(CONFIG.read_bytes());listing=(roots[0]/'disassembly.stdout').read_text()
        for address,instruction in c['instructions'].items():
            match=[line for line in listing.splitlines() if line.strip().startswith(address[2:]+':')];assert len(match)==1
            actual=re.sub(r'\s+',' ',match[0].split(':',1)[1].strip());assert actual==instruction,(actual,instruction)
        out.sources(sources());out.json('phase.json',c);out.json('source-pins.json',[{'path':str(p.relative_to(ROOT)),'sha256':digest(p)} for p in sources()]);out.json('root-pins.json',[{'path':str(p.relative_to(ROOT)),'sha256':digest(p/'root-closed.json')} for p in roots]);out.json('summary.json',{'declared_before_reconstruction':True,'resources':check.check()});print(json.dumps({'declared':True,'instruction_map_verified':True}));status='complete'
    finally:out.close(status)
def replay():
    out=Files(ROOT/'artifacts/rust-r1-sgemm-small-replay-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        verify_closed(DECL)
        for p in json.loads((DECL/'source-pins.json').read_bytes()):assert digest(ROOT/p['path'])==p['sha256']
        for p in json.loads((DECL/'root-pins.json').read_bytes()):verify_closed(ROOT/p['path']);assert digest(ROOT/p['path']/'root-closed.json')==p['sha256']
        roots=[ROOT/'artifacts'/n for n in NAMES];ms=[json.loads((p/'manifest.json').read_bytes()) for p in roots[1:]];raws=[(p/'tensors.bin').read_bytes() for p in roots[1:]]
        for p,m in zip(roots[1:],ms,strict=True):assert digest(p/'tensors.bin')==m['payload_sha256']
        def values(i,key):return floats(raws[i],ms[i]['tensors'][key])
        w=values(0,'weight/patch.weight');bias=values(0,'weight/patch.bias');assert len(w)==64*32 and len(bias)==64
        lib=ctypes.CDLL('/usr/lib/libSystem.B.dylib');fma=lib.fmaf;fma.argtypes=[ctypes.c_float]*3;fma.restype=ctypes.c_float
        out.sources(sources());out.json('phase.json',{'contract_sha256':digest(CONFIG),'SGEMM_calls':0,'torch_kernels':0,'full_forward':0,'training':False});output=bytearray();entries={};results=[]
        def put(key,vs):
            start=len(output);output.extend(packed(vs));entries[key]={'shape':[1,3,4,64],'offset_bytes':start,'length_bytes':len(vs)*4}
        for cid in json.loads(CONFIG.read_bytes())['cases']:
            x=values(0,cid+'/input');assert len(x)==12*32;mm=[];ys=[]
            for row in range(12):
                for col in range(64):
                    lanes=[0.]*4
                    for j in range(8):
                        for lane in range(4):
                            k=4*j+lane;lanes[lane]=fma(x[row*32+k],w[col*32+k],lanes[lane])
                    product=f32(f32(lanes[0]+lanes[1])+f32(lanes[2]+lanes[3]));mm.append(product);ys.append(fma(bias[col],1.,product))
            native_mm=values(0,cid+'/python/mm');native_fused=values(0,cid+'/python/fused');baseline=values(1,cid+'/rust/own_add')
            results.append({'case':cid,'mm':metrics(native_mm,mm,True),'fused':metrics(native_fused,ys,True),'baseline':metrics(native_fused,baseline,True)});put(cid+'/mm',mm);put(cid+'/fused',ys);check.check()
        summary={'cases':5,'elements_per_method':3840,'mm_bit_mismatches':sum(r['mm']['bit_mismatches'] for r in results),'fused_bit_mismatches':sum(r['fused']['bit_mismatches'] for r in results),'baseline_output_bit_mismatches':sum(r['baseline']['bit_mismatches'] for r in results),'SGEMM_calls':0,'torch_kernels':0,'Rust_candidate_calls':0,'full_forward':0,'model_changed':False,'training':False,'R1_complete':False,'resources':check.check()};summary['interpretation_confirmed']=summary['mm_bit_mismatches']==summary['fused_bit_mismatches']==0
        out.write('tensors.bin',bytes(output));out.json('manifest.json',{'tensors':entries,'payload_sha256':digest(out.root/'tensors.bin')});out.json('comparisons.json',results);out.json('summary.json',summary);print(json.dumps(summary));status='complete'
    finally:out.close(status)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['declare','replay']);a=p.parse_args();globals()[a.phase]()
