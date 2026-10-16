"""Source-ordered moment attribution, separate from model candidate evaluation."""
import argparse
import ctypes
import json
import math
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'tools'),str(ROOT/'models/mini-transformer'),str(ROOT/'tools/public-data')]
from metropt_multiday import Files,digest,verify_closed
from macos_demand_runtime import MacCheckpoint
from rust_r1_compare import floats

CONFIG = ROOT/'examples/configs/rust-r1-moments-audit-20261016.json'
DECLARATION = ROOT/'artifacts/rust-r1-moments-declaration-20261016'
TORCH_INCLUDE = ROOT/'environments/demand-macos/.venv/lib/python3.14/site-packages/torch/include'
REGISTRY = ROOT/'environments/rust-cpu/cargo-home/registry/src/index.crates.io-1949cf8c6b5b557f'


def source_paths():
    return [Path(__file__),CONFIG,ROOT/'crates/banto-ai/src/model.rs',ROOT/'Cargo.lock',
            ROOT/'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json',
            TORCH_INCLUDE/'ATen/native/cpu/moments_utils.h',
            TORCH_INCLUDE/'ATen/cpu/vec/vec128/vec128_float_neon.h',
            REGISTRY/'burn-flex-0.22.0/src/ops/activation.rs',
            REGISTRY/'burn-tensor-0.22.0/src/tensor/module.rs',
            REGISTRY/'burn-autodiff-0.22.0/src/ops/tensor.rs']


def declare():
    out=Files(DECLARATION);status='failed';check=MacCheckpoint(seconds=870)
    try:
        c=json.loads(CONFIG.read_bytes());pins=[]
        for key in ['fixture','balanced_outputs','serial_outputs']:
            p=ROOT/c[key];verify_closed(p)
            pins.append({'path':str(p.relative_to(ROOT)),'closure_sha256':digest(p/'root-closed.json')})
        assert digest(ROOT/'crates/banto-ai/src/model.rs')=='acefec42e7506d807f7deae22269f30f9bf409a8c8cf9d1ddb59c2ef6af7fa80'
        out.sources(source_paths());out.json('phase.json',c);out.json('root-pins.json',pins)
        out.json('source-pins.json',[{'path':str(p.relative_to(ROOT)),'sha256':digest(p)} for p in source_paths()])
        out.json('summary.json',{'declared_before_kernels':True,'training':False,'resources':check.check()})
        status='complete';print(json.dumps({'declared':True,'contract_sha256':digest(CONFIG)}))
    finally:out.close(status)


def f32(x):
    return struct.unpack('<f',struct.pack('<f',x))[0]


def packed(xs):
    return struct.pack('<'+'f'*len(xs),*xs)


def balanced(row):
    def mean(v):
        while len(v)>1:v=[f32(v[i]+v[i+1]) for i in range(0,len(v),2)]
        return f32(v[0]/64)
    mu=mean(row[:]);center=[f32(x-mu) for x in row]
    var=mean([f32(x*x) for x in center])
    return mu,var


def serial(row):
    mu=m2=0.
    for k,x in enumerate(row,1):
        delta=f32(x-mu);mu=f32(mu+f32(delta/k))
        m2=f32(m2+f32(delta*f32(x-mu)))
    return mu,f32(m2/64)


def ordered(row,fma):
    means=[0.]*4;moments=[0.]*4
    for step in range(16):
        c=f32(1/(step+1))
        for lane in range(4):
            x=row[step*4+lane];delta=f32(x-means[lane])
            means[lane]=fma(c,delta,means[lane])
            moments[lane]=fma(delta,f32(x-means[lane]),moments[lane])
    # AddMomentsVec into the source's initial all-zero stack.
    for lane in range(4):
        delta=means[lane]
        means[lane]=f32(0.+f32(1.*delta))
        moments[lane]=fma(f32(delta*0.),f32(1.*delta),f32(0.+moments[lane]))
    n=0;mu=m2=0.
    for lane in range(4):
        c=f32(16/(n+16));delta=f32(means[lane]-mu)
        mu=f32(mu+f32(c*delta))
        cross=f32(f32(f32(delta*delta)*c)*n)
        m2=f32(m2+f32(moments[lane]+cross));n+=16
    return mu,f32(m2/64)


def inverse(var):
    return f32(1/f32(math.sqrt(f32(var+f32(1e-5)))))


def affine(row,mu,inv,w,b,flex=False):
    if flex:return [f32(f32(f32(x-mu)*f32(inv*g))+be) for x,g,be in zip(row,w,b,strict=True)]
    return [f32(f32(f32(f32(x-mu)*inv)*g)+be) for x,g,be in zip(row,w,b,strict=True)]


def metrics(xs,ys,tolerance=False):
    assert len(xs)==len(ys) and all(math.isfinite(x) for x in xs+ys)
    ds=[abs(x-y) for x,y in zip(xs,ys,strict=True)]
    result={'elements':len(xs),'bit_mismatches':sum(packed([x])!=packed([y]) for x,y in zip(xs,ys,strict=True)),
            'SSE':math.fsum(d*d for d in ds),'max_abs':max(ds,default=0.)}
    if tolerance:result['failing_elements']=sum(d>2e-6+2e-5*abs(x) for d,x in zip(ds,xs,strict=True))
    return result


def audit():
    out=Files(ROOT/'artifacts/rust-r1-moments-audit-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        verify_closed(DECLARATION)
        for pin in json.loads((DECLARATION/'source-pins.json').read_bytes()):assert digest(ROOT/pin['path'])==pin['sha256']
        for pin in json.loads((DECLARATION/'root-pins.json').read_bytes()):assert digest(ROOT/pin['path']/'root-closed.json')==pin['closure_sha256']
        c=json.loads(CONFIG.read_bytes());roots=[ROOT/c[k] for k in ['fixture','balanced_outputs','serial_outputs']]
        for p in roots:verify_closed(p)
        manifests=[json.loads((p/'manifest.json').read_bytes()) for p in roots]
        raws=[(p/'tensors.bin').read_bytes() for p in roots]
        for p,m in zip(roots,manifests,strict=True):assert digest(p/'tensors.bin')==m['payload_sha256']
        fm,bm,sm=manifests;fr,br,sr=raws
        out.sources(source_paths());out.json('phase.json',{'contract_sha256':digest(CONFIG),'declaration_sha256':digest(DECLARATION/'root-closed.json'),'scope':c['scope']})
        lib=ctypes.CDLL('/usr/lib/libSystem.B.dylib');fma=lib.fmaf
        fma.argtypes=[ctypes.c_float]*3;fma.restype=ctypes.c_float
        a=f32(1+2**-23);b=f32(1-2**-23)
        witness={'a':a,'b':b,'c':-1.,'fused':fma(a,b,-1.),'separate':f32(f32(a*b)-1.)}
        assert witness['fused']==-2**-46 and witness['separate']==0
        out.json('fma-witness.json',witness)
        import torch
        torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True);torch.set_grad_enabled(False)
        out.json('runtime.json',{'torch_version':torch.__version__,'torch_git_version':torch.version.git_version,
                                 'torch_build':torch.__config__.show(),'fma_library':'/usr/lib/libSystem.B.dylib::fmaf'})
        payload=bytearray();entries={};results=[];anchors=[];row_total=0
        def put(key,xs,shape):
            start=len(payload);payload.extend(packed(xs));entries[key]={'shape':shape,'offset_bytes':start,'length_bytes':len(xs)*4}
        def saved(raw,e):return raw[e['offset_bytes']:e['offset_bytes']+e['length_bytes']]
        for case in fm['cases']:
            cid=case['id'];assert cid in c['cases']
            for index,name in enumerate(c['modules']):
                if index<6:
                    block=index//3;norm=index%3
                    source=('tokens' if block==0 else 'blocks.0') if norm==0 else f'blocks.{block}.residual{norm-1}'
                else:source='blocks.1'
                xs=floats(fr,fm['tensors'][cid+'/pp/'+source])
                if index==6:xs=[x for offset in range(0,len(xs),320) for x in xs[offset+256:offset+320]]
                rows=len(xs)//64;assert rows==(case['batch']*3 if index==6 else case['batch']*15)
                w=floats(fr,fm['tensors']['weight/'+name+'.weight']);b=floats(fr,fm['tensors']['weight/'+name+'.bias'])
                x=torch.tensor(xs,dtype=torch.float32).reshape(rows,64)
                y,mu,inv=torch.native_layer_norm(x,[64],torch.tensor(w),torch.tensor(b),1e-5)
                native=y.flatten().tolist();native_mu=mu.flatten().tolist();native_inv=inv.flatten().tolist()
                assert packed(native)==saved(fr,fm['tensors'][cid+'/pp/'+name]),(cid,name,'native anchor')
                outputs={p:[] for p in c['fixed_paths']};moments={p:[] for p in ['balanced','serial','source_ordered']}
                for r in range(rows):
                    row=xs[r*64:(r+1)*64]
                    for method,fn,path,flex in [
                        ('balanced',balanced,'balanced_reference_affine',False),
                        ('serial',serial,'serial_flex_affine',True),
                        ('source_ordered',lambda row:ordered(row,fma),'source_ordered_reference_affine',False)]:
                        m,v=fn(row);iv=inverse(v);moments[method].append((m,v,iv))
                        outputs[path].extend(affine(row,m,iv,w,b,flex))
                    outputs['native_moments_reference_affine'].extend(affine(row,native_mu[r],native_inv[r],w,b))
                    outputs['native_moments_flex_affine'].extend(affine(row,native_mu[r],native_inv[r],w,b,True))
                baseline_exact=packed(outputs['balanced_reference_affine'])==saved(br,bm['tensors'][cid+'/rp/'+name])
                serial_exact=packed(outputs['serial_flex_affine'])==saved(sr,sm['tensors'][cid+'/candidate/'+name])
                anchors.append({'case':cid,'module':name,'native_PP_exact':True,'balanced_RP_exact':baseline_exact,'serial_Flex_exact':serial_exact})
                assert baseline_exact and serial_exact,(cid,name,'existing arithmetic anchor')
                record={'case':cid,'module':name,'rows':rows,'moments':{},'outputs':{path:metrics(native,vs,True) for path,vs in outputs.items()}}
                for method,vs in moments.items():
                    ms=[v[0] for v in vs];ivs=[v[2] for v in vs]
                    record['moments'][method]={'mean':metrics(native_mu,ms),'rstd':metrics(native_inv,ivs)}
                    put(cid+'/'+name+'/'+method+'_moments',[a for v in vs for a in v],[rows,3])
                put(cid+'/'+name+'/native_moments',[a for pair in zip(native_mu,native_inv,strict=True) for a in pair],[rows,2])
                for path,vs in outputs.items():put(cid+'/'+name+'/'+path,vs,[rows,64])
                results.append(record);row_total+=rows;check.check()
        assert len(results)==49 and row_total==1953
        summary={'inputs':49,'rows':row_total,'elements_per_output_path':124992,'native_calls':49,'anchor_groups_exact':len(anchors),
                 'source_ordered_mean_bit_mismatches':sum(r['moments']['source_ordered']['mean']['bit_mismatches'] for r in results),
                 'source_ordered_rstd_bit_mismatches':sum(r['moments']['source_ordered']['rstd']['bit_mismatches'] for r in results),
                 'source_ordered_output_bit_mismatches':sum(r['outputs']['source_ordered_reference_affine']['bit_mismatches'] for r in results),
                 'native_reference_affine_bit_mismatches':sum(r['outputs']['native_moments_reference_affine']['bit_mismatches'] for r in results),
                 'native_flex_affine_bit_mismatches':sum(r['outputs']['native_moments_flex_affine']['bit_mismatches'] for r in results),
                 'full_forward_calls':0,'model_candidates':0,'core_changed':False,'R1_complete':False,'R2_started':False,'training':False,'resources':check.check()}
        out.write('tensors.bin',bytes(payload));out.json('manifest.json',{'tensors':entries,'payload_sha256':digest(out.root/'tensors.bin'),'declaration_sha256':digest(DECLARATION/'root-closed.json')})
        out.json('anchor-certificates.json',anchors);out.json('component-comparisons.json',results);out.json('summary.json',summary)
        print(json.dumps(summary));status='complete'
    finally:out.close(status)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['declare','audit']);a=p.parse_args()
    declare() if a.phase=='declare' else audit()
