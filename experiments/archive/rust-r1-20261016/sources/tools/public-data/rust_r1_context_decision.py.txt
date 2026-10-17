"""Apply only the declared hook, then adopt or restore using the whole R1 gate."""
import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'models/mini-transformer')]
from metropt_multiday import Files,digest,verify_closed
from macos_demand_runtime import MacCheckpoint
DECL=ROOT/'artifacts/rust-r1-context-model-declaration-20261016'
CONFIG=ROOT/'examples/configs/rust-r1-context-model-20261016.json'

def candidate(original):
    old='    fn norm<const D: usize>(&self, x: Tensor<D>, name: &str) -> Tensor<D> {'
    new='''    #[cfg(feature = "reference-normalization")]
    fn norm<const D: usize>(&self, x: Tensor<D>, name: &str) -> Tensor<D> {
        crate::fma::reference_layer_norm(
            x,
            self.p(&format!("{name}.weight"), [64]),
            self.p(&format!("{name}.bias"), [64]),
        )
    }
    #[cfg(not(feature = "reference-normalization"))]
'''+old
    assert original.count(old)==1
    original=original.replace(old,new,1)
    old='''        let mu = mean_last(x.clone());
        let centered = x - mu.clone();
        let scale = mean_last(centered.clone().square())
            .sqrt()
            .max_pair(self.p("scale_floor", [1, 3, 1]));
        let normalized = centered / scale.clone();'''
    new='''        #[cfg(feature = "reference-normalization")]
        let (mu, _raw_std, scale, normalized) =
            crate::context::reference_context(x, self.p("scale_floor", [1, 3, 1]));
        #[cfg(not(feature = "reference-normalization"))]
        let (mu, scale, normalized) = {
            let mu = mean_last(x.clone());
            let centered = x - mu.clone();
            let scale = mean_last(centered.clone().square())
                .sqrt()
                .max_pair(self.p("scale_floor", [1, 3, 1]));
            let normalized = centered / scale.clone();
            (mu, scale, normalized)
        };'''
    assert original.count(old)==1
    original=original.replace(old,new,1)
    old='fn mean_last<const D: usize>(x: Tensor<D>) -> Tensor<D> {'
    assert original.count(old)==1
    return original.replace(old,'#[cfg(not(feature = "reference-normalization"))]\n'+old,1)

def main(phase):
    out=Files(ROOT/f'artifacts/rust-r1-context-model-{phase}-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        verify_closed(DECL);model=ROOT/'crates/banto-ai/src/model.rs';original=(DECL/'model.rs.before').read_text();expected=candidate(original)
        local=ROOT/'artifacts/rust-r1-context-local-comparison-20261016';verify_closed(local)
        assert json.loads((local/'summary.json').read_bytes())['local_gate_pass']
        out.json('phase.json',{'phase':phase,'contract_sha256':digest(CONFIG),'model_candidates':1})
        if phase=='hook':
            assert model.read_text()==original,'unexpected existing changes'
            out.write('model.rs.before',model.read_bytes());model.write_text(expected)
            summary={'uniform_context_and_LayerNorm_hook':True,'kernel_gate_pass':True,'full_forward':0,'training':False}
        else:
            assert model.read_text()==expected,'unexpected concurrent changes'
            comparison=ROOT/'artifacts/rust-r1-context-full-comparison-20261016';verify_closed(comparison)
            c=json.loads((comparison/'summary.json').read_bytes());assert c['elements_compared']==389214 and c['cases']==7
            out.write('model.rs.candidate',model.read_bytes());out.json('comparison-pin.json',{'sha256':digest(comparison/'root-closed.json')})
            if c['parity_pass']:
                package=ROOT/'crates/banto-ai/Cargo.toml';before=package.read_text();assert '\ndefault =' not in before
                out.write('Cargo.toml.before',package.read_bytes());package.write_text(before.replace('[features]\n','[features]\ndefault = ["reference-normalization"]\n',1))
                summary={'candidate_adopted':True,'R1_numerical_gate_pass':True,'failing_elements':0,'legacy_no_default_features':True,'default_tests_pending':True,'R2_started':False,'training':False}
            else:
                model.write_text(original);assert digest(model)=='acefec42e7506d807f7deae22269f30f9bf409a8c8cf9d1ddb59c2ef6af7fa80'
                summary={'candidate_adopted':False,'candidate_failing_elements':c['failing_elements'],'model_restored_byte_exact':True,'baseline_failing_elements':1,'R1_complete':False,'R2_started':False,'training':False}
        out.sources([Path(__file__),CONFIG,model,ROOT/'crates/banto-ai/src/context.rs',ROOT/'crates/banto-ai/src/fma.rs',ROOT/'crates/banto-ai/src/lib.rs',ROOT/'crates/banto-ai/Cargo.toml',ROOT/'Cargo.lock']);summary['resources']=check.check();out.json('summary.json',summary);print(json.dumps(summary));status='complete'
    finally:out.close(status)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['hook','decision']);a=p.parse_args();main(a.phase)
