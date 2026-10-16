"""Restore only our rejected model hook, preserving its full source snapshot."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'models/mini-transformer')]
from metropt_multiday import Files,digest,verify_closed
from macos_demand_runtime import MacCheckpoint


def main():
    out=Files(ROOT/'artifacts/rust-r1-fma-model-restore-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        comparison=ROOT/'artifacts/rust-r1-fma-full-comparison-20261016';verify_closed(comparison)
        s=json.loads((comparison/'summary.json').read_bytes());assert not s['parity_pass'] and s['failing_elements']==3
        original=(ROOT/'artifacts/rust-r1-fma-model-declaration-20261016/model.rs.before').read_text()
        model=ROOT/'crates/banto-ai/src/model.rs'
        needle='    fn norm<const D: usize>(&self, x: Tensor<D>, name: &str) -> Tensor<D> {'
        hook='''    #[cfg(feature = "fma-extension")]
    fn norm<const D: usize>(&self, x: Tensor<D>, name: &str) -> Tensor<D> {
        crate::fma::reference_layer_norm(
            x,
            self.p(&format!("{name}.weight"), [64]),
            self.p(&format!("{name}.bias"), [64]),
        )
    }
    #[cfg(not(feature = "fma-extension"))]
'''+needle
        assert model.read_text()==original.replace(needle,hook,1),'unexpected concurrent model edits'
        out.sources([Path(__file__),model,ROOT/'crates/banto-ai/src/fma.rs',ROOT/'crates/banto-ai/Cargo.toml'])
        out.json('phase.json',{'reason':'original whole R1 gate failed: 3 elements; follow preregistered restoration condition','comparison_sha256':digest(comparison/'root-closed.json'),'candidate_model_sha256':digest(model),'restore_only_our_hook':True})
        model.write_text(original)
        assert digest(model)=='acefec42e7506d807f7deae22269f30f9bf409a8c8cf9d1ddb59c2ef6af7fa80'
        out.json('summary.json',{'model_restored_byte_exact':True,'FMA_primitive_opt_in':True,'default_feature_unchanged':True,'R1_complete':False,'R2_started':False,'resources':check.check()})
        print(json.dumps({'model_restored_byte_exact':True,'candidate_adopted':False}));status='complete'
    finally:out.close(status)


if __name__=='__main__':main()
