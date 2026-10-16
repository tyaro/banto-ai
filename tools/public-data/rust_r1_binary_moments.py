"""A single binary-derived reconstruction, consuming only closed saved values."""
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
from rust_r1_moments_audit import f32,packed,inverse,affine,metrics
CONFIG=ROOT/'examples/configs/rust-r1-binary-moments-20261016.json'
DECLARATION=ROOT/'artifacts/rust-r1-binary-moments-declaration-20261016'


def sources():
    return [Path(__file__),CONFIG,ROOT/'tools/public-data/rust_r1_moments_audit.py',ROOT/'tools/public-data/rust_r1_compare.py',ROOT/'crates/banto-ai/src/model.rs',ROOT/'Cargo.lock',ROOT/'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json']


def declare():
    out=Files(DECLARATION);status='failed';check=MacCheckpoint(seconds=870)
    try:
        c=json.loads(CONFIG.read_bytes());pins=[]
        for key in ['binary_audit','prior_moments','fixture']:
            p=ROOT/c[key];verify_closed(p);pins.append({'path':c[key],'closure_sha256':digest(p/'root-closed.json')})
        listing=(ROOT/c['binary_audit']/'region-1.stdout').read_text()
        for entry in c['instructions'].values():
            matches=[line for line in listing.splitlines() if line.strip().startswith(entry['address']+':')]
            assert len(matches)==1
            actual=re.sub(r'\s+',' ',matches[0].split(':',1)[1].strip())
            assert actual==entry['operation'],(actual,entry)
        out.sources(sources());out.json('phase.json',c);out.json('root-pins.json',pins)
        out.json('source-pins.json',[{'path':str(p.relative_to(ROOT)),'sha256':digest(p)} for p in sources()])
        out.json('summary.json',{'declared_before_numerical_replay':True,'resources':check.check()})
        print(json.dumps({'declared':True,'instruction_map_verified':True}));status='complete'
    finally:out.close(status)


def binary_ordered(row,fma):
    means=[0.]*4;m2s=[0.]*4
    for step in range(16):
        c=f32(1/(step+1))
        for lane in range(4):
            x=row[step*4+lane];delta=f32(x-means[lane])
            means[lane]=fma(c,delta,means[lane]);m2s[lane]=fma(delta,f32(x-means[lane]),m2s[lane])
    for lane in range(4):
        delta=means[lane];means[lane]=f32(0.+f32(1.*delta))
        m2s[lane]=fma(f32(delta*0.),f32(1.*delta),f32(0.+m2s[lane]))
    mu=m2=0.;n=0
    for lane in range(4):
        c=f32(16/(n+16));delta=f32(means[lane]-mu)
        cross=f32(f32(delta*delta)*c)
        m2=f32(m2+fma(cross,float(n),m2s[lane]))
        mu=fma(c,delta,mu);n+=16
    return mu,f32(m2/64)


def replay():
    out=Files(ROOT/'artifacts/rust-r1-binary-moments-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        verify_closed(DECLARATION)
        source_pins=json.loads((DECLARATION/'source-pins.json').read_bytes())
        for p in source_pins:assert digest(ROOT/p['path'])==p['sha256']
        c=json.loads(CONFIG.read_bytes())
        for p in json.loads((DECLARATION/'root-pins.json').read_bytes()):
            verify_closed(ROOT/p['path']);assert digest(ROOT/p['path']/'root-closed.json')==p['closure_sha256']
        fixture=ROOT/c['fixture'];old=ROOT/c['prior_moments']
        fm=json.loads((fixture/'manifest.json').read_bytes());om=json.loads((old/'manifest.json').read_bytes())
        fr=(fixture/'tensors.bin').read_bytes();orr=(old/'tensors.bin').read_bytes()
        assert digest(fixture/'tensors.bin')==fm['payload_sha256'] and digest(old/'tensors.bin')==om['payload_sha256']
        out.sources(sources());out.json('phase.json',{'declaration_sha256':digest(DECLARATION/'root-closed.json'),'new_torch_kernels':0,'model_forward':0,'training':False})
        lib=ctypes.CDLL('/usr/lib/libSystem.B.dylib');fma=lib.fmaf;fma.argtypes=[ctypes.c_float]*3;fma.restype=ctypes.c_float
        raw=bytearray();entries={};results=[];row_total=0
        def put(key,vs,shape):
            start=len(raw);raw.extend(packed(vs));entries[key]={'shape':shape,'offset_bytes':start,'length_bytes':len(vs)*4}
        for case in fm['cases']:
            cid=case['id']
            for index in range(7):
                if index<6:
                    block=index//3;norm=index%3;name=f'blocks.{block}.norms.{norm}'
                    source=('tokens' if block==0 else 'blocks.0') if norm==0 else f'blocks.{block}.residual{norm-1}'
                else:name='final_norm';source='blocks.1'
                xs=floats(fr,fm['tensors'][cid+'/pp/'+source])
                if index==6:xs=[x for offset in range(0,len(xs),320) for x in xs[offset+256:offset+320]]
                w=floats(fr,fm['tensors']['weight/'+name+'.weight']);b=floats(fr,fm['tensors']['weight/'+name+'.bias'])
                native_moments=floats(orr,om['tensors'][cid+'/'+name+'/native_moments'])
                ys=[];moments=[]
                for offset in range(0,len(xs),64):
                    row=xs[offset:offset+64];mu,var=binary_ordered(row,fma);inv=inverse(var)
                    moments.extend([mu,var,inv]);ys.extend(affine(row,mu,inv,w,b))
                expected=floats(fr,fm['tensors'][cid+'/pp/'+name]);rows=len(xs)//64
                record={'case':cid,'module':name,'rows':rows,
                        'mean':metrics(native_moments[0::2],moments[0::3]),
                        'rstd':metrics(native_moments[1::2],moments[2::3]),'output':metrics(expected,ys,True)}
                results.append(record);row_total+=rows
                put(cid+'/'+name+'/moments',moments,[rows,3]);put(cid+'/'+name+'/output',ys,[rows,64]);check.check()
        assert len(results)==49 and row_total==1953
        summary={'comparisons':49,'rows':1953,'output_elements':124992,
                 'mean_bit_mismatches':sum(r['mean']['bit_mismatches'] for r in results),
                 'rstd_bit_mismatches':sum(r['rstd']['bit_mismatches'] for r in results),
                 'output_bit_mismatches':sum(r['output']['bit_mismatches'] for r in results),
                 'output_failing_elements':sum(r['output']['failing_elements'] for r in results),
                 'new_torch_kernels':0,'full_forward':0,'model_candidates':0,'core_changed':False,'training':False,'R1_complete':False,'resources':check.check()}
        out.write('tensors.bin',bytes(raw));out.json('manifest.json',{'tensors':entries,'payload_sha256':digest(out.root/'tensors.bin')})
        out.json('comparisons.json',results);out.json('summary.json',summary)
        for p in source_pins:assert digest(ROOT/p['path'])==p['sha256']
        print(json.dumps(summary));status='complete'
    finally:out.close(status)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['declare','replay']);a=p.parse_args()
    declare() if a.phase=='declare' else replay()
