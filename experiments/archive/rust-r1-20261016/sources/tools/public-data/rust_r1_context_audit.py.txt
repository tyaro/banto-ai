"""One preregistered source-ordered context audit, no model or target reads."""
import argparse
import json
import math
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'models/mini-transformer'),str(ROOT/'tools/public-data')]
from metropt_multiday import Files,digest,verify_closed
from macos_demand_runtime import MacCheckpoint
from rust_r1_compare import floats
from rust_r1_moments_audit import f32,packed,metrics
CONFIG=ROOT/'examples/configs/rust-r1-context-audit-20261016.json'
DECL=ROOT/'artifacts/rust-r1-context-declaration-20261016'
SOURCE=ROOT/'artifacts/rust-r1-context-source-20261016'
INCLUDE=ROOT/'environments/demand-macos/.venv/lib/python3.14/site-packages/torch/include'
ROOTS=['rust-r1-python-reference-20261016','rust-r1-burn-predictions3-20261016','rust-r1-layer-fixture2-20261016']

def paths():
    return [Path(__file__),CONFIG,ROOT/'tools/public-data/rust_r1_moments_audit.py',ROOT/'tools/public-data/rust_r1_compare.py',ROOT/'crates/banto-ai/src/model.rs',ROOT/'Cargo.lock',ROOT/'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json']

def source():
    out=Files(SOURCE);status='failed'
    try:
        c=json.loads(CONFIG.read_bytes());out.sources(paths());records=[]
        for name,relative in [('SumKernel.cpp','cpu/SumKernel.cpp'),('ReduceOps.cpp','ReduceOps.cpp'),('ReduceOpsKernel.cpp','cpu/ReduceOpsKernel.cpp')]:
            p=Path('/private/tmp/banto-r1-context-'+name)
            out.write(name,p.read_bytes());records.append({'name':name,'sha256':digest(p),'url':f'https://raw.githubusercontent.com/pytorch/pytorch/{c["source_commit"]}/aten/src/ATen/native/{relative}'})
        for name,relative in [('Reduce.h','ATen/native/cpu/Reduce.h'),('SharedReduceOps.h','ATen/native/SharedReduceOps.h'),('vec128_float_neon.h','ATen/cpu/vec/vec128/vec128_float_neon.h')]:
            p=INCLUDE/relative;out.write(name,p.read_bytes());records.append({'name':name,'sha256':digest(p),'installed_header':str(p.relative_to(ROOT))})
        out.json('source-pins.json',records);out.json('phase.json',{'source_read_only':True,'numerical_experiments':0,'source_commit':c['source_commit']});print(json.dumps({'source_intake':True}));status='complete'
    finally:out.close(status)

def declare():
    out=Files(DECL);status='failed';check=MacCheckpoint(seconds=870)
    try:
        roots=[SOURCE,*[ROOT/'artifacts'/n for n in ROOTS]]
        for p in roots:verify_closed(p)
        assert digest(ROOT/'crates/banto-ai/src/model.rs')=='acefec42e7506d807f7deae22269f30f9bf409a8c8cf9d1ddb59c2ef6af7fa80'
        out.sources(paths());out.json('phase.json',json.loads(CONFIG.read_bytes()))
        out.json('source-pins.json',[{'path':str(p.relative_to(ROOT)),'sha256':digest(p)} for p in paths()])
        out.json('root-pins.json',[{'path':str(p.relative_to(ROOT)),'sha256':digest(p/'root-closed.json')} for p in roots]);out.json('summary.json',{'declared_before_kernels':True,'resources':check.check()});print(json.dumps({'declared':True}));status='complete'
    finally:out.close(status)

def baseline(row):
    def mean(xs):
        while len(xs)>1:xs=[f32(xs[i]+xs[i+1]) for i in range(0,len(xs),2)]
        return f32(xs[0]/128)
    mu=mean(row[:]);center=[f32(x-mu) for x in row]
    return mu,f32(math.sqrt(mean([f32(x*x) for x in center])))

def ordered(row):
    accum=[[0.]*4 for _ in range(4)]
    for j in range(8):
        for k in range(4):
            for lane in range(4):accum[k][lane]=f32(accum[k][lane]+row[16*j+4*k+lane])
    for k in range(1,4):
        for lane in range(4):accum[0][lane]=f32(accum[0][lane]+accum[k][lane])
    mu=0.
    for v in accum[0]:mu=f32(mu+v)
    mu=f32(f32(0.+mu)/128)
    mean=m2=0.
    for n,x in enumerate(row,1):
        delta=x-mean;mean=mean+delta/n;m2=m2+delta*(x-mean)
    return mu,f32(math.sqrt(m2/128))

def audit():
    out=Files(ROOT/'artifacts/rust-r1-context-audit-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        verify_closed(DECL)
        pins=json.loads((DECL/'source-pins.json').read_bytes())
        for p in pins:assert digest(ROOT/p['path'])==p['sha256']
        for p in json.loads((DECL/'root-pins.json').read_bytes()):verify_closed(ROOT/p['path']);assert digest(ROOT/p['path']/'root-closed.json')==p['sha256']
        import torch
        torch.set_num_threads(1);torch.set_num_interop_threads(1)
        assert torch.version.git_version==json.loads(CONFIG.read_bytes())['source_commit']
        ref,rs,fixture=[ROOT/'artifacts'/n for n in ROOTS]
        fm=json.loads((ref/'fixtures.json').read_bytes());rm=json.loads((rs/'traces-layout.json').read_bytes());wm=json.loads((fixture/'manifest.json').read_bytes())
        inputs=(ref/'inputs.bin').read_bytes();pr=(ref/'python-traces.bin').read_bytes();rr=(rs/'rust-traces.bin').read_bytes();wr=(fixture/'tensors.bin').read_bytes()
        floor=floats(wr,wm['tensors']['weight/scale_floor']);assert len(floor)==3
        out.sources(paths());out.json('phase.json',{'declaration_sha256':digest(DECL/'root-closed.json'),'torch_git_version':torch.version.git_version,'full_forward':0,'training':False,'context_pipelines':7})
        raw=bytearray();entries={};results=[]
        def put(key,vs,shape):
            start=len(raw);raw.extend(packed(vs));entries[key]={'shape':shape,'offset_bytes':start,'length_bytes':len(vs)*4}
        with torch.no_grad():
            for case,rcase in zip(fm['cases'],rm['cases'],strict=True):
                cid=case['id'];b=case['batch'];assert cid==rcase['id']
                xs=floats(inputs,{**case,'shape':[b,3,128]});x=torch.tensor(xs,dtype=torch.float32).reshape(b,3,128)
                mu=x.mean(-1,keepdim=True);std=x.std(-1,correction=0,keepdim=True);scale=torch.maximum(std,torch.tensor(floor).reshape(1,3,1));norm=(x-mu)/scale
                native={k:t.reshape(-1).tolist() for k,t in [('context_center',mu),('raw_std',std),('context_scale',scale),('normalized_context',norm)]}
                pm={e['name']:e for e in case['traces']};bm={e['name']:e for e in rcase['traces']}
                generated={kind:{k:[] for k in native} for kind in ['baseline','source']}
                for rowindex,start in enumerate(range(0,len(xs),128)):
                    row=xs[start:start+128]
                    for kind,fn in [('baseline',baseline),('source',ordered)]:
                        cm,st=fn(row);sc=max(st,floor[rowindex%3]);g=generated[kind]
                        g['context_center'].append(cm);g['raw_std'].append(st);g['context_scale'].append(sc);g['normalized_context'].extend(f32(f32(v-cm)/sc) for v in row)
                item={'case':cid,'native_anchor_bytes':{},'baseline_saved_bytes':{},'source_metrics':{}}
                for name,values in native.items():
                    shape=[b,3,128 if name=='normalized_context' else 1];put(cid+'/native/'+name,values,shape)
                    for kind in generated:put(cid+'/'+kind+'/'+name,generated[kind][name],shape)
                    target=values
                    if name!='raw_std':
                        target=floats(pr,pm[name]);item['native_anchor_bytes'][name]=packed(values)==packed(target)
                        item['baseline_saved_bytes'][name]=packed(generated['baseline'][name])==packed(floats(rr,bm[name]))
                    item['source_metrics'][name]=metrics(target,generated['source'][name],True)
                results.append(item);check.check()
        assert len(results)==7
        gates={'native_original_anchor_bytes':all(all(r['native_anchor_bytes'].values()) for r in results),'baseline_saved_anchor_bytes':all(all(r['baseline_saved_bytes'].values()) for r in results),'source_all_bits':all(all(v['bit_mismatches']==0 for v in r['source_metrics'].values()) for r in results)}
        summary={'gates':gates,'local_gate_pass':all(gates.values()),'cases':7,'rows':63,'full_forward':0,'model_changed':False,'training':False,'R1_complete':False,'source_std_contract':'uncontracted float64; binary contraction not asserted','totals':{name:{metric:sum(r['source_metrics'][name][metric] for r in results) for metric in ['elements','bit_mismatches','SSE','failing_elements']} for name in native},'resources':check.check()}
        out.write('tensors.bin',bytes(raw));out.json('manifest.json',{'tensors':entries,'payload_sha256':digest(out.root/'tensors.bin')});out.json('comparisons.json',results);out.json('summary.json',summary)
        for p in pins:assert digest(ROOT/p['path'])==p['sha256']
        print(json.dumps(summary));status='complete'
    finally:out.close(status)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['source','declare','audit']);a=p.parse_args();globals()[a.phase]()
