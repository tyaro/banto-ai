"""Freeze exact dyadic/integer artificial inputs and pre-implementation pins."""
import json
import struct
import sys
from fractions import Fraction
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'models/mini-transformer')]
from metropt_multiday import Files,digest,verify_closed
from macos_demand_runtime import MacCheckpoint

def main():
    out=Files(ROOT/'artifacts/rust-r1-fused-linear-declaration-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        config=ROOT/'examples/configs/rust-r1-fused-linear-admission-20261016.json'
        roots=[ROOT/'artifacts'/n for n in ['rust-r1-linear-results-20261016','rust-r1-layer-fixture2-20261016','rust-r1-layer-kernel-20261016','rust-r1-context-local-comparison-20261016','rust-r1-fma-local-comparison-20261016','rust-r1-python-reference-20261016']]
        for p in roots:verify_closed(p)
        for name in ['Cargo.toml','src/lib.rs','src/model.rs']:
            out.write(Path(name).name+'.before',(ROOT/'crates/banto-ai'/name).read_bytes())
        out.write('Cargo.lock.before',(ROOT/'Cargo.lock').read_bytes())
        assert digest(ROOT/'crates/banto-ai/src/model.rs')=='acefec42e7506d807f7deae22269f30f9bf409a8c8cf9d1ddb59c2ef6af7fa80'
        sources=[Path(__file__),config,ROOT/'Cargo.lock',*[ROOT/'crates/banto-ai'/n for n in ['Cargo.toml','src/lib.rs','src/model.rs','src/fma.rs','src/context.rs']],ROOT/'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json']
        out.sources(sources);out.json('phase.json',json.loads(config.read_bytes()));out.json('source-pins-before.json',[{'path':str(p.relative_to(ROOT)),'sha256':digest(p)} for p in sources]);out.json('root-pins.json',[{'path':str(p.relative_to(ROOT)),'sha256':digest(p/'root-closed.json')} for p in roots])
        rows=[
            ('ordinary',[2,3,2],[1,2,3,4,5,6],[2,1,-1,3,4,-2],[1,-2],'normal'),
            ('zero_input',[2,3,2],[0]*6,[2,1,-1,3,4,-2],[2,-3],'normal'),
            ('zero_weight',[2,3,2],[1,2,3,4,5,6],[0]*6,[-5,6],'normal'),
            ('mixed_sign',[2,3,2],[3,-3,2,-4,5,-6],[2,-1,2,1,-3,2],[1,4],'normal'),
            ('broadcast_bias',[3,2,3],[1,2,3,4,-1,1],[1,2,3,4,5,6],[2,-2,1],'normal'),
            ('transposed_weight',[2,3,2],[2,-1,1,-2,3,4],[1,2,3,4,5,6],[1,-1],'transpose'),
            ('offset_input',[2,2,2],[1,3,2,-1],[2,-1,1,4],[1,1],'offset'),
            ('dyadic',[2,3,2],[.5,-.25,2,1.5,.25,-.5],[.5,1,-2,.25,.125,-.5],[.0625,-.125],'normal')]
        cases=[]
        for name,shape,x,w,b,layout in rows:
            m,k,n=shape;assert len(x)==m*k and len(w)==k*n and len(b)==n
            exact=[sum((Fraction(x[i*k+t])*Fraction(w[t*n+j]) for t in range(k)),Fraction(b[j])) for i in range(m) for j in range(n)]
            bits=[]
            for v in exact:
                binary=struct.pack('<f',float(v));assert Fraction(struct.unpack('<f',binary)[0])==v
                bits.append(struct.unpack('<I',binary)[0])
            cases.append({'name':name,'shape':shape,'x':x,'weight':w,'bias':b,'layout':layout,'expected_bits':bits,'exact_rationals':[str(v) for v in exact]})
        out.json('fixture.json',{'schema':'banto.fused-linear-artificial.v1','cases':cases,'oracle':'independent Fraction arithmetic; every exact value is exactly representable in f32','backward_calls':0})
        out.json('summary.json',{'artificial_cases':8,'expected_elements':sum(len(c['expected_bits']) for c in cases),'candidate_kernels':0,'declared_before_code_and_dependency_change':True,'resources':check.check()});print(json.dumps({'declared':True,'fixture_sha256':digest(out.root/'fixture.json')}));status='complete'
    finally:out.close(status)

if __name__=='__main__':main()
