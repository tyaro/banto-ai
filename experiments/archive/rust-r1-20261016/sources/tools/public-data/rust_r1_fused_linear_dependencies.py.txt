"""Verify the sole root lock edge and unchanged effective dependency selection."""
import json
import re
import sys
import tomllib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'models/mini-transformer')]
from metropt_multiday import Files,digest,verify_closed
from macos_demand_runtime import MacCheckpoint

def main():
    out=Files(ROOT/'artifacts/rust-r1-fused-linear-dependencies-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        declaration=ROOT/'artifacts/rust-r1-fused-linear-declaration-20261016';verify_closed(declaration)
        before=(declaration/'Cargo.lock.before').read_bytes();after=(ROOT/'Cargo.lock').read_bytes()
        old=tomllib.loads(before.decode());new=tomllib.loads(after.decode());assert old.keys()==new.keys()
        changed=[]
        for a,b in zip(old['package'],new['package'],strict=True):
            if a!=b:
                assert a['name']==b['name']=='banto-ai' and {**a,'dependencies':sorted([*a['dependencies'],'gemm'])}==b
                changed.append(a['name'])
        assert changed==['banto-ai']
        def packages(p):return set(tuple(m.groups()) for line in p.read_text().splitlines() if (m:=re.match(r'^(\S+) v([^ ]+)',line)))
        a=packages(ROOT/'artifacts/rust-r1-fma-tree-20261016/stdout.txt');b=packages(ROOT/'artifacts/rust-r1-fused-linear-lock-refresh-20261016/stdout.txt');assert a==b and len(a)==154
        def features(p):return {m.group(0) for line in p.read_text().splitlines() if (m:=re.match(r'^\S+ feature "[^"]+"',line))}
        af=features(ROOT/'artifacts/rust-r1-context-features-20261016/stdout.txt');bf=features(ROOT/'artifacts/rust-r1-fused-linear-features-20261016/stdout.txt');assert af==bf,(sorted(bf-af),sorted(af-bf))
        paths=[Path(__file__),ROOT/'Cargo.lock',ROOT/'crates/banto-ai/Cargo.toml',ROOT/'crates/banto-ai/src/fused_linear.rs',ROOT/'crates/banto-ai/examples/probe_fused_linear.rs',ROOT/'crates/banto-ai/examples/diagnose_fused_linear.rs',ROOT/'docs/research/rust-fused-linear-safety-2026-10-16.md',ROOT/'examples/configs/rust-r1-fused-linear-admission-20261016.json']
        out.sources(paths);out.write('Cargo.lock.before',before);out.write('Cargo.lock.after',after);out.json('packages.json',sorted(a));out.json('effective-features.json',sorted(af));out.json('source-pins-before-kernels.json',[{'path':str(p.relative_to(ROOT)),'sha256':digest(p)} for p in paths]);out.json('summary.json',{'only_lock_change':'banto-ai root adds existing gemm edge','package_set_unchanged':154,'effective_features_unchanged':True,'default_feature_changed':False,'candidate_kernels':0,'resources':check.check()});print(json.dumps({'dependency_gate_pass':True,'packages':154,'root_edge_only':True,'effective_features_unchanged':True}));status='complete'
    finally:out.close(status)

if __name__=='__main__':main()
