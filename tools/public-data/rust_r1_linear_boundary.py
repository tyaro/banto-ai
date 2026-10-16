"""Seven fixed patch boundaries, with bias/matmul attribution kept separate."""
import argparse
import ctypes
import json
import math
import os
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'models/mini-transformer'),str(ROOT/'tools/public-data')]
from metropt_multiday import Files,digest,verify_closed
from macos_demand_runtime import MacCheckpoint
from rust_r1_compare import floats
from rust_r1_moments_audit import packed,metrics
CONFIG=ROOT/'examples/configs/rust-r1-linear-boundary-20261016.json'
DECL=ROOT/'artifacts/rust-r1-linear-declaration-20261016'
NAMES=['rust-r1-linear-source-20261016','rust-r1-layer-fixture2-20261016','rust-r1-layer-kernel-20261016','rust-r1-context-predictions-20261016']

def sources():return [Path(__file__),CONFIG,ROOT/'tools/public-data/rust_r1_compare.py',ROOT/'tools/public-data/rust_r1_moments_audit.py',ROOT/'crates/banto-ai/src/model.rs',ROOT/'Cargo.lock',ROOT/'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json']

def declare():
    out=Files(DECL);status='failed';check=MacCheckpoint(seconds=870)
    try:
        roots=[ROOT/'artifacts'/n for n in NAMES]
        for p in roots:verify_closed(p)
        out.sources(sources());out.json('phase.json',json.loads(CONFIG.read_bytes()));out.json('root-pins.json',[{'path':str(p.relative_to(ROOT)),'sha256':digest(p/'root-closed.json')} for p in roots]);out.json('source-pins.json',[{'path':str(p.relative_to(ROOT)),'sha256':digest(p)} for p in sources()]);out.json('summary.json',{'declared_before_kernels':True,'resources':check.check()});print(json.dumps({'declared':True}));status='complete'
    finally:out.close(status)

def pins():
    verify_closed(DECL)
    for p in json.loads((DECL/'root-pins.json').read_bytes()):verify_closed(ROOT/p['path']);assert digest(ROOT/p['path']/'root-closed.json')==p['sha256']
    for p in json.loads((DECL/'source-pins.json').read_bytes()):assert digest(ROOT/p['path'])==p['sha256']

def python():
    out=Files(ROOT/'artifacts/rust-r1-linear-python-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        pins();out.sources(sources());os.environ['VECLIB_MAXIMUM_THREADS']='1'
        import torch
        torch.set_num_threads(1);torch.set_num_interop_threads(1)
        assert torch.version.git_version=='08187d9e0fba026dc8217405802ab5381dc88d90'
        # Runtime lookup records the image that exports the resolved symbol;
        # it does not claim to prove a particular hot-path call occurred.
        dylib=ROOT/'environments/demand-macos/.venv/lib/python3.14/site-packages/torch/lib/libtorch_cpu.dylib'
        class DlInfo(ctypes.Structure):_fields_=[('fname',ctypes.c_char_p),('fbase',ctypes.c_void_p),('sname',ctypes.c_char_p),('saddr',ctypes.c_void_p)]
        lib=ctypes.CDLL(str(dylib));symbol=getattr(lib,'sgemm_');system=ctypes.CDLL('/usr/lib/libSystem.B.dylib');system.dladdr.argtypes=[ctypes.c_void_p,ctypes.POINTER(DlInfo)];system.dladdr.restype=ctypes.c_int
        info=DlInfo();assert system.dladdr(ctypes.cast(symbol,ctypes.c_void_p),ctypes.byref(info))!=0
        out.json('runtime-binding.json',{'symbol':'sgemm_','resolved_image':info.fname.decode(),'resolved_symbol':info.sname.decode() if info.sname else None,'libtorch_cpu_sha256':digest(dylib),'hot_path_proved':False,'VECLIB_MAXIMUM_THREADS':os.environ['VECLIB_MAXIMUM_THREADS']})
        fixture=ROOT/'artifacts'/NAMES[1];fm=json.loads((fixture/'manifest.json').read_bytes());fr=(fixture/'tensors.bin').read_bytes();assert digest(fixture/'tensors.bin')==fm['payload_sha256']
        def get(key):e=fm['tensors'][key];return torch.tensor(floats(fr,e),dtype=torch.float32).reshape(e['shape'])
        layer=torch.nn.Linear(32,64);layer.weight=torch.nn.Parameter(get('weight/patch.weight'));layer.bias=torch.nn.Parameter(get('weight/patch.bias'));layer.eval()
        raw=bytearray();entries={};comparisons=[];cases=[]
        def put(key,t):
            start=len(raw);raw.extend(packed(t.reshape(-1).tolist()));entries[key]={'shape':list(t.shape),'offset_bytes':start,'length_bytes':len(raw)-start}
        with torch.no_grad():
            put('weight/patch.weight',layer.weight);put('weight/patch.bias',layer.bias)
            for case in fm['cases']:
                cid=case['id'];b=case['batch'];x=get(cid+'/pp/normalized_context').reshape(b,3,4,32);expected=get(cid+'/pp/patch');flat=x.reshape(b*12,32)
                y=layer(x);mm=flat@layer.weight.t();separate=mm+layer.bias
                assert packed(y.reshape(-1).tolist())==packed(expected.reshape(-1).tolist()),cid
                put(cid+'/input',x);put(cid+'/python/fused',y);put(cid+'/python/mm',mm.reshape(b,3,4,64));put(cid+'/python/separate',separate.reshape(b,3,4,64))
                comparisons.append({'case':cid,'original_patch_byte_exact':True,'fused_vs_separate':metrics(expected.reshape(-1).tolist(),separate.reshape(-1).tolist(),True),'input_shape':list(x.shape),'input_stride':list(x.stride()),'weight_shape':list(layer.weight.shape),'weight_stride':list(layer.weight.stride()),'transposed_weight_stride':list(layer.weight.t().stride())});cases.append({'id':cid,'batch':b});check.check()
        out.write('tensors.bin',bytes(raw));out.json('manifest.json',{'schema':'banto.r1-linear-boundary.v1','cases':cases,'tensors':entries,'payload_sha256':digest(out.root/'tensors.bin'),'source_fixture_sha256':digest(fixture/'manifest.json')});out.json('comparisons.json',comparisons)
        out.json('summary.json',{'original_patch_byte_exact_cases':7,'linear_calls':7,'mm_calls':7,'separate_add_calls':7,'fused_separate_bit_mismatches':sum(r['fused_vs_separate']['bit_mismatches'] for r in comparisons),'model_forward':0,'training':False,'resources':check.check()});pins();print(json.dumps({'original_patch_byte_exact_cases':7,'fused_separate_bit_mismatches':sum(r['fused_vs_separate']['bit_mismatches'] for r in comparisons)}));status='complete'
    finally:out.close(status)

def compare():
    out=Files(ROOT/'artifacts/rust-r1-linear-comparison-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        pins();out.sources(sources());names=['rust-r1-linear-python-20261016','rust-r1-linear-kernel-20261016','rust-r1-layer-kernel-20261016','rust-r1-context-predictions-20261016']
        roots=[ROOT/'artifacts'/n for n in names]
        for p in roots:verify_closed(p)
        ms=[json.loads((p/('traces-layout.json' if i==3 else 'manifest.json')).read_bytes()) for i,p in enumerate(roots)];raws=[(p/('rust-traces.bin' if i==3 else 'tensors.bin')).read_bytes() for i,p in enumerate(roots)]
        assert ms[1]['fixture_manifest_sha256']==digest(roots[0]/'manifest.json')
        for i in [0,1,2]:assert digest(roots[i]/'tensors.bin')==ms[i]['payload_sha256']
        def get(i,key):return floats(raws[i],ms[i]['tensors'][key])
        results=[];identity=0.;raw=bytearray();entries={}
        def put(key,xs):
            start=len(raw);raw.extend(packed(xs));entries[key]={'shape':[len(xs)],'offset_bytes':start,'length_bytes':len(xs)*4}
        for case,pred in zip(ms[0]['cases'],ms[3]['cases'],strict=True):
            cid=case['id'];assert cid==pred['id'];fused=get(0,cid+'/python/fused');sep=get(0,cid+'/python/separate');pm=get(0,cid+'/python/mm');rm=get(1,cid+'/rust/mm');own=get(1,cid+'/rust/own_add');same=get(1,cid+'/rust/python_mm_add');rp=get(2,cid+'/rp/patch');pe=next(e for e in pred['traces'] if e['name']=='patch');candidate=floats(raws[3],pe)
            assert packed(own)==packed(rp)==packed(candidate),cid
            total=[a-b for a,b in zip(own,fused,strict=True)];prop=[a-b for a,b in zip(own,same,strict=True)];local=[a-b for a,b in zip(same,sep,strict=True)];bias=[a-b for a,b in zip(sep,fused,strict=True)]
            closure=max(abs(t-p-l-b) for t,p,l,b in zip(total,prop,local,bias,strict=True));identity=max(identity,closure)
            def stats(xs):return {'max_abs':max(map(abs,xs),default=0.),'RMS':math.sqrt(math.fsum(x*x for x in xs)/len(xs)),'L1':math.fsum(map(abs,xs)),'SSE':math.fsum(x*x for x in xs)}
            results.append({'case':cid,'elements':len(total),'baseline_RP_and_context_candidate_bytes':True,'raw_matmul':metrics(pm,rm,True),'same_input_bias_add':metrics(sep,same,True),'total':stats(total),'propagated_matmul_after_bias':stats(prop),'local_bias_add':stats(local),'fused_vs_separate':stats(bias),'decomposition_max_residual':closure})
            for name,values in [('total',total),('propagated_matmul_after_bias',prop),('local_bias_add',local),('fused_vs_separate',bias)]:put(cid+'/'+name,values)
            check.check()
        assert identity==0. and len(results)==7
        summary={'cases':7,'elements':sum(r['elements'] for r in results),'baseline_RP_and_context_candidate_byte_exact_cases':7,'raw_matmul_bit_mismatches':sum(r['raw_matmul']['bit_mismatches'] for r in results),'same_input_bias_add_bit_mismatches':sum(r['same_input_bias_add']['bit_mismatches'] for r in results),'decomposition_max_residual':identity,'component_SSE':{name:sum(r[name]['SSE'] for r in results) for name in ['total','propagated_matmul_after_bias','local_bias_add','fused_vs_separate']},'full_forward':0,'model_changed':False,'training':False,'R1_complete':False,'resources':check.check()}
        out.write('decomposition.bin',bytes(raw));out.json('manifest.json',{'tensors':entries,'payload_sha256':digest(out.root/'decomposition.bin'),'precision_note':'signed f32-output differences saved as float32; exact identity was verified with float64 differences before packing'});out.json('comparisons.json',results);out.json('summary.json',summary);pins();print(json.dumps(summary));status='complete'
    finally:out.close(status)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['declare','python','compare']);a=p.parse_args();globals()[a.phase]()
