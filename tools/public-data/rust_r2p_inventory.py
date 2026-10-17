"""Static/source and locked-offline dependency inventory; no tensor execution."""
import hashlib
import io
import json
import math
import os
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'models/mini-transformer'),str(ROOT/'tools/public-data')]
from metropt_multiday import Files,digest
from macos_demand_runtime import MacCheckpoint
from macos_rust_run import source_files
REGISTRY=ROOT/'environments/rust-cpu/cargo-home/registry/src/index.crates.io-1949cf8c6b5b557f'
TORCH=ROOT/'environments/demand-macos/.venv/lib/python3.14/site-packages/torch'
R0=ROOT/'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json'

def shapes():
    s={'horizon':[64],'scale_floor':[3],'position':[5,64],'time_mask':[5,5],
       'patch.weight':[64,32],'patch.bias':[64],'final_norm.weight':[64],'final_norm.bias':[64],
       'head.weight':[96,64],'head.bias':[96]}
    for i in range(2):
        for attention in ['temporal','variate']:
            for layer in ['q','k','v','out']:
                s[f'blocks.{i}.{attention}.{layer}.weight']=[64,64]
                s[f'blocks.{i}.{attention}.{layer}.bias']=[64]
        for j in range(3):
            for kind in ['weight','bias']: s[f'blocks.{i}.norms.{j}.{kind}']=[64]
        for j,o,k in [(0,128,64),(2,64,128)]:
            s[f'blocks.{i}.ff.{j}.weight']=[o,k]; s[f'blocks.{i}.ff.{j}.bias']=[o]
    return s

def dependency_sources():
    return ([REGISTRY/p for p in ['burn-0.22.0/Cargo.toml','burn-tensor-0.22.0/src/tensor/api/autodiff.rs',
        'burn-tensor-0.22.0/src/tensor/api/float.rs','burn-optim-0.22.0/src/optim/adamw.rs']]+
        [TORCH/'optim/adam.py',TORCH/'optim/adamw.py',TORCH/'nn/utils/clip_grad.py'])

def main():
    out=Files(ROOT/'artifacts/rust-r2p-inventory-20261016'); status='failed'; check=MacCheckpoint(seconds=870)
    try:
        sources=list(dict.fromkeys([Path(__file__),*source_files(),R0,
            ROOT/'models/mini-transformer/small_model.py',ROOT/'models/mini-transformer/care_learning.py',
            ROOT/'examples/configs/banto-ai-practical-training-return-20261016.json',*dependency_sources()]))
        pins=[{'path':str(p.relative_to(ROOT)),'sha256':digest(p)} for p in sources]
        out.sources(sources); out.json('source-pins.json',pins)
        manifest=tomllib.loads((ROOT/'crates/banto-ai/Cargo.toml').read_text()); lock=tomllib.loads((ROOT/'Cargo.lock').read_text())
        root_package=next(p for p in lock['package'] if p['name']=='banto-ai')
        dep={n:d for n,d in manifest['dependencies'].items()}; manifest_names=set(dep)
        lock_names={s.split()[0] for s in root_package['dependencies']}
        features=manifest['features']; model=(ROOT/'crates/banto-ai/src/model.rs').read_text(); lib=(ROOT/'crates/banto-ai/src/lib.rs').read_text()
        import re
        cfgs=sorted(set(re.findall(r'#\[cfg\(feature = "([^"]+)"\)\)\]',lib)))
        burn=tomllib.loads((REGISTRY/'burn-0.22.0/Cargo.toml').read_text())['features']
        assert burn['optim']==['burn-optim','autodiff']
        assert '.autodiff(' not in model and '.require_grad(' not in model
        assert 'state: BTreeMap<String, Tensor<1>>' in model and 'let quantiles = read(&physical)?;' in model
        checkpoint=(ROOT/'crates/banto-ai/src/checkpoint.rs').read_text()
        assert 'Ok(Self { tensors: model })' in checkpoint and 'pub fn parameter_count(&self)' in checkpoint
        table=shapes(); frozen={'scale_floor','position','time_mask'}
        counts={'named_tensors':len(table),'trainable_named_tensors':len(table)-len(frozen),
            'trainable_values':sum(math.prod(v) for n,v in table.items() if n not in frozen),
            'buffer_values':sum(math.prod(v) for n,v in table.items() if n in frozen)}
        assert counts=={'named_tensors':62,'trainable_named_tensors':59,'trainable_values':109024,'buffer_values':348}
        out.json('tensor-inventory.json',{'scope':'source-derived schema, not a runtime parameter enumeration','counts':counts,
            'entries':[{'name':n,'shape':v,'role':'buffer' if n in frozen else 'trainable','layout':'row-major [out,in]' if n.endswith('.weight') and len(v)==2 else 'row-major'} for n,v in sorted(table.items())]})
        static={'manifest_features':features,'lib_cfg_features':cfgs,'undefined_cfg_features':sorted(set(cfgs)-set(features)),
            'manifest_dependencies':sorted(manifest_names),'lock_root_dependencies':sorted(lock_names),
            'root_lock_edges_not_in_manifest':sorted(lock_names-manifest_names),'burn_optim_enables_autodiff':True,
            'effective_feature_graph_verified':False,'new_dependency_required_for_autodiff_by_static_manifest':False}
        out.json('dependency-inventory.json',static)
        cargo=Path('/Users/tyaromax/.rustup/toolchains/stable-aarch64-apple-darwin/bin/cargo')
        cmd=[str(cargo),'tree','--locked','--offline','-p','banto-ai','-e','features']
        e=os.environ.copy(); e.update({'CARGO_HOME':str(ROOT/'environments/rust-cpu/cargo-home'),'CARGO_TARGET_DIR':str(ROOT/'target'),
            'CARGO_BUILD_JOBS':'1','CARGO_NET_RETRY':'0','CARGO_INCREMENTAL':'0'})
        q=subprocess.run(cmd,cwd=ROOT,env=e,capture_output=True,timeout=60)
        assert len(q.stdout)<=1024**2 and len(q.stderr)<=128*1024
        out.write('cargo-tree.stdout',q.stdout); out.write('cargo-tree.stderr',q.stderr)
        out.json('cargo-tree-command.json',{'argv':cmd,'exit':q.returncode,'cargo_sha256':digest(cargo),
            'read_only_locked_offline':True,'build_or_tests':False,'result':'feature tree observed' if q.returncode==0 else 'blocked; original manifest/lock retained; no retry'})
        git=subprocess.run(['git','status','--short'],cwd=ROOT,capture_output=True,timeout=20)
        out.write('git-status.stdout',git.stdout); out.write('git-status.stderr',git.stderr); assert git.returncode==0
        out.json('gaps.json',{
            'autodiff':'backend feature reachable via optim, but current model leaves are untracked; no trainable state/gradient API',
            'forward':'tensor math exists, but public result is host Vec; no loss-ready normalized tensor output API',
            'loss_optimizer':'no crate loss/clip/update implementation or named optimizer state manager',
            'checkpoint':'reader validates optional AdamW entries but only returns model; missing moment completeness is not a training-resume check; no writer/schedule/cancel/restore',
            'param_count':'parameter_count is a fixed constant, not runtime enumeration',
            'extensions':'source-only historical experiments; undefined Cargo feature definitions in current manifest; not automatically usable or backward-verified',
            'examples':'auto-discovered examples include historical diagnostic imports; avoid --all-targets as synthetic acceptance command'})
        for pin in pins: assert digest(ROOT/pin['path'])==pin['sha256']
        out.json('summary.json',{'inventory_complete':True,'cargo_tree_exit':q.returncode,'dependency_readiness':q.returncode==0,
            'source_derived_counts':counts,'model_forward':0,'backward':0,'optimizer_updates':0,'real_data_opened':False,
            'pointer_tracking_resumed':False,'files_changed':False,'R1_pass':False,'R2_started':False,'resources':check.check()})
        print(json.dumps({'inventory_complete':True,'cargo_tree_exit':q.returncode,'counts':counts})); status='complete'
    finally: out.close(status)

if __name__=='__main__': main()
