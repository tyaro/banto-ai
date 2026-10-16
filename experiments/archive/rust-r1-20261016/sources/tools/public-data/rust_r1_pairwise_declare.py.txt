"""Freeze one arithmetic repair hypothesis before new R1 outputs."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'models/mini-transformer'),str(ROOT/'tools/public-data')]
from metropt_multiday import Files,digest,verify_closed
def main():
    out=Files(ROOT/'artifacts/rust-r1-pairwise-declaration-20261016');status='failed'
    try:
        diagnosis=ROOT/'artifacts/rust-r1-saved-diagnosis-20261016';verify_closed(diagnosis)
        out.sources([Path(__file__),ROOT/'crates/banto-ai/src/model.rs',ROOT/'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json'])
        cached=ROOT/'environments/rust-cpu/cargo-home/registry/src/index.crates.io-1949cf8c6b5b557f'
        for name,path in [('flex-reduce.rs',cached/'burn-flex-0.22.0/src/ops/reduce.rs'),('burn-stats.rs',cached/'burn-tensor-0.22.0/src/tensor/stats/mod.rs')]:out.write(name,path.read_bytes())
        out.json('phase.json',{'scope':'one bounded numerical implementation repair, no model tuning','hypothesis':'replace sequential f32 reductions for C128 and LayerNorm64 with balanced pairwise f32 reductions; same population variance equation, eps, dtype, weights and architecture; remain in Burn tensor operations for future gradients','evidence':'independent context moment aggregate error: serial Rust 7.691141e-5, balanced f32 3.352761e-8, reference 0; all physical quantiles already within tolerance','diagnosis_closure_sha256':digest(diagnosis/'root-closed.json'),'fixed_contract_sha256':digest(ROOT/'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json'),'evaluation':'same three tests and unchanged seven-case comparison; no threshold widening, no new data or Python reference regeneration','stop':'if residual mismatch, preserve it and document unresolved operation differences; no arbitrary arithmetic search','memory_bytes':2*1024**3,'build_budget':'examples/configs/rust-r1-build-budget-20261016-r1.json'})
        status='complete'
    finally:out.close(status)
if __name__=='__main__':main()
