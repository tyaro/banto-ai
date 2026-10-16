"""Preregister one extension implementation and freeze independent fmaf bits."""
import ctypes
import json
import struct
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'models/mini-transformer')]
from metropt_multiday import Files,digest,verify_closed
from macos_demand_runtime import MacCheckpoint


def main():
    out=Files(ROOT/'artifacts/rust-r1-fma-fixture-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        config=ROOT/'examples/configs/rust-r1-fma-extension-20261016.json'
        prior=ROOT/'artifacts/rust-r1-binary-moments-20261016';verify_closed(prior)
        paths=[Path(__file__),config,ROOT/'crates/banto-ai/Cargo.toml',ROOT/'crates/banto-ai/src/lib.rs',ROOT/'crates/banto-ai/src/model.rs',ROOT/'Cargo.lock']
        registry=ROOT/'environments/rust-cpu/cargo-home/registry/src/index.crates.io-1949cf8c6b5b557f'
        paths += [registry/'burn-tensor-0.22.0/src/tensor/api/extension.rs',registry/'burn-backend-extension-0.22.0/README.md',registry/'burn-autodiff-0.22.0/src/ops/base.rs',registry/'burn-autodiff-0.22.0/src/ops/backward.rs',registry/'burn-flex-0.22.0/src/tensor.rs']
        out.sources(paths);out.json('phase.json',json.loads(config.read_bytes()))
        out.json('source-pins-before.json',[{'path':str(p.relative_to(ROOT)),'sha256':digest(p)} for p in paths])
        out.write('Cargo.toml.before',(ROOT/'crates/banto-ai/Cargo.toml').read_bytes());out.write('lib.rs.before',(ROOT/'crates/banto-ai/src/lib.rs').read_bytes())
        out.json('prior-pin.json',{'path':str(prior.relative_to(ROOT)),'closure_sha256':digest(prior/'root-closed.json')})
        triples=[
            ('ordinary',0x3f800000,0x40000000,0x40400000),
            ('cancel_product_rounding',0x3f800001,0x3f7ffffe,0xbf800000),
            ('min_subnormal',1,0x3f800000,0),
            ('half_min_normal',0x00800000,0x3f000000,0),
            ('tie_to_zero',1,0x3f000000,0),
            ('subnormal_add',1,0x3f800000,1),
            ('negative_zero',0x80000000,0x3f800000,0x80000000),
            ('opposite_zeros',0x80000000,0x3f800000,0),
            ('overflowing_product_finite_sum',0x7f7fffff,0x40000000,0xff7fffff),
            ('max_cancel',0x7f7fffff,0x3f800000,0xff7fffff),
            ('double_rounding_counterexample',0x3f800001,0x3fc00000,0x8d800000),
            ('above_midpoint',0x3f800001,0x3fc00000,0x0d800000),
            ('negative_result',0xc0000000,0x40400000,0x3f800000),
            ('zero_multiplier',0,0x7f7fffff,0x3e800000),
            ('negative_subnormal',0x80000001,0x3f800000,0),
            ('large_cancel',0x4b800000,0x3f800000,0xcb7fffff),
            ('all_ones',0x3f800000,0x3f800000,0x3f800000),
            ('negative_times_negative',0xbf800000,0xc0000000,0xbf000000),
            ('normal_subnormal_boundary',0x00800000,0x3f800000,0x80000001),
            ('signed_underflow',0x80000001,0x3f000000,0x80000000)]
        def value(u):return struct.unpack('<f',struct.pack('<I',u))[0]
        def bits(x):return struct.unpack('<I',struct.pack('<f',x))[0]
        lib=ctypes.CDLL('/usr/lib/libSystem.B.dylib');fma=lib.fmaf;fma.argtypes=[ctypes.c_float]*3;fma.restype=ctypes.c_float
        cases=[{'name':n,'a':a,'b':b,'c':c,'expected':bits(fma(value(a),value(b),value(c)))} for n,a,b,c in triples]
        witness=next(r for r in cases if r['name']=='double_rounding_counterexample')
        double=bits(value(witness['a'])*value(witness['b'])+value(witness['c']))
        assert witness['expected']==0x3fc00001 and double==0x3fc00002
        out.json('fixture.json',{'schema':'banto.fma-forward-fixture.v1','cases':cases,'double_rounding_naive_bits':double,'backward_calls':0})
        out.json('summary.json',{'rows':20,'independent_oracle':'system fmaf','double_rounding_counterexample_confirmed':True,'Rust_kernel_calls':0,'resources':check.check()})
        print(json.dumps({'rows':20,'fixture_sha256':digest(out.root/'fixture.json')}));status='complete'
    finally:out.close(status)


if __name__=='__main__':main()
