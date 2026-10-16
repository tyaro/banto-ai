"""Correct the graph-participation probe using the pinned API semantics."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'models/mini-transformer')]
from metropt_multiday import Files,digest
from macos_demand_runtime import MacCheckpoint


def main():
    out=Files(ROOT/'artifacts/rust-r1-fma-harness-repair-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        example=ROOT/'crates/banto-ai/examples/probe_fma.rs';kernel=ROOT/'crates/banto-ai/src/fma.rs'
        registry=ROOT/'environments/rust-cpu/cargo-home/registry/src/index.crates.io-1949cf8c6b5b557f'
        sources=[Path(__file__),example,kernel,registry/'burn-tensor-0.22.0/src/tensor/api/autodiff.rs',registry/'burn-autodiff-0.22.0/src/graph/requirement.rs',registry/'burn-autodiff-0.22.0/src/ops/tensor.rs']
        out.sources(sources);before=example.read_text();pin=digest(kernel)
        assert before.count('.is_require_grad()')==3
        out.json('phase.json',{'prior_compile_failure':'private into_contiguous was changed to public to_contiguous; no arithmetic change',
                              'prior_graph_probe_failure':'is_require_grad tests leaf gradient retention; intermediate operation has GradInBackward and is_tracked must be tested',
                              'repair':'three output probes use public is_tracked; keep expected bits, arithmetic, input cases, graph construction and no-backward scope',
                              'kernel_sha256':pin,'fixture_sha256':digest(ROOT/'artifacts/rust-r1-fma-fixture-20261016/fixture.json')})
        example.write_text(before.replace('.is_require_grad()','.is_tracked()'))
        out.write('probe_fma.rs.after',example.read_bytes());assert digest(kernel)==pin
        out.json('summary.json',{'kernel_changed':False,'expectations_changed':False,'probe_semantics_corrected':True,'backward_calls':0,'resources':check.check()})
        print(json.dumps({'repair':'graph participation API','kernel_changed':False}));status='complete'
    finally:out.close(status)


if __name__=='__main__':main()
