"""Pin the single source-backed LayerNorm repair before the seven-case run."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'models/mini-transformer')]
from metropt_multiday import Files,digest,verify_closed
def main():
    out=Files(ROOT/'artifacts/rust-r1-norm-repair-declaration-20261016');status='failed'
    try:
        p=ROOT/'artifacts/rust-r1-upstream-comparison2-20261016';verify_closed(p);s=json.loads((p/'summary.json').read_bytes());assert s['candidate_gate_pass'] and s['attention_failing_elements']==0
        out.sources([Path(__file__),ROOT/'crates/banto-ai/src/model.rs',ROOT/'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json'])
        out.json('phase.json',{'scope':'one general LayerNorm arithmetic repair then fixed R1 confirmation',
                 'repair':'centered / sqrt(var+eps) -> centered * reciprocal(sqrt(var+eps)), all LayerNorm incl final_norm',
                 'evidence_root':str(p.relative_to(ROOT)),'evidence_closure_sha256':digest(p/'root-closed.json'),
                 'candidate_gate_pass':True,'native_source':'https://github.com/pytorch/pytorch/blob/v2.14.0/aten/src/ATen/native/cpu/layer_norm_kernel.cpp',
                 'unchanged':['balanced f32 moments','weights','dtype','eps','architecture','attention','original Python references','R0 tolerances','memory2GiB','artifact/EvidenceStore budgets'],
                 'confirm':'cargo tests then one original seven-case forward and saved comparison; if not all pass preserve failure, no further arithmetic candidate search',
                 'R2_or_performance_evaluation':False,'core_before_sha256':digest(ROOT/'crates/banto-ai/src/model.rs')})
        status='complete'
    finally:out.close(status)
if __name__=='__main__':main()
