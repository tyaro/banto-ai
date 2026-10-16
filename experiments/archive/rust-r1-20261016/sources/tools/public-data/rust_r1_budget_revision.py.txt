"""Declare the user-authorized R1 build-only disk revision before execution."""
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'models/mini-transformer'),str(ROOT/'tools/public-data')]
from metropt_multiday import Files,digest
from rust_r1_publish_preparation import validate_root
from macos_demand_runtime import MacCheckpoint
def main():
    out=Files(ROOT/'artifacts/rust-r1-budget-revision-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        pins=[validate_root(ROOT/'artifacts'/n) for n in ['rust-r1-tests-20261016','rust-r1-python-reference-20261016','rust-r1-build-stop-20261016']]
        out.sources([Path(__file__),ROOT/'tools/public-data/macos_rust_run.py',ROOT/'Cargo.toml',ROOT/'Cargo.lock',ROOT/'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json'])
        prior=json.loads((ROOT/'artifacts/rust-r1-build-stop-20261016/disk-inventory.json').read_bytes())
        budget={'schema':'banto.rust-r1-build-budget.v1','id':'R1-BUILD-DISK-20261016-r1',
                'authorization':'human: ビルド用の容量上限を必要な範囲で見直して、計画に沿ってRustのテストとPythonとの数値比較を進めてください。既存成果の保護とメモリ上限は維持してください。',
                'previous_cache_disk_cap_bytes':768*1024**2,'cache_disk_cap_bytes':1536*1024**2,
                'reason':'prior 805979625B stop comprises 479959378B dependency cache and 326020247B unfinished build; allow remaining dependencies, test/example linking and transient compiler outputs without deleting existing data; finite 1.5GiB ceiling, not a claim of required final size',
                'applies_to':['environments/rust-cpu/cargo-home','target'],
                'memory_cap_bytes':2*1024**3,'child_seconds':870,'parent_seconds':900,
                'artifact_and_evidence_limits_unchanged':True,'scientific_tolerances_unchanged':True,
                'scope':['R1 CPU tests','R1 fixed seven-case inference comparison'],
                'no_training_or_test_reevaluation':True,'jobs':1,'threads':1}
        path=ROOT/'examples/configs/rust-r1-build-budget-20261016-r1.json'
        with path.open('x') as f:json.dump(budget,f,ensure_ascii=False,indent=2);f.write('\n')
        out.json('phase.json',budget);out.json('prior-closure-pins.json',pins);out.json('prior-disk-inventory.json',prior)
        out.json('summary.json',{'budget_path':str(path.relative_to(ROOT)),'budget_sha256':digest(path),'resources':check.check(),'new_build_started':False})
        print(json.dumps({'cache_disk_cap_bytes':budget['cache_disk_cap_bytes'],'budget_sha256':digest(path)}));status='complete'
    finally:out.close(status)
if __name__=='__main__':main()
