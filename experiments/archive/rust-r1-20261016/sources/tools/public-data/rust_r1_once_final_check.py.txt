"""Final artifact check; preserve an independently changed Cargo manifest."""
import ast
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'models/mini-transformer'),str(ROOT/'tools/public-data')]
from metropt_multiday import Files,digest
from macos_demand_runtime import MacCheckpoint
from rust_r1_once_publish import NAMES,REPORT
from rust_r1_once_contract import verify,DECL
from rust_r1_once_contract_repair import BDECL
from rust_r1_publish_preparation import validate_root
from verification_records import EvidenceStore
from care_rust_r0_close import verify_evidence

def main():
    out=Files(ROOT/'artifacts/rust-r1-once-final-check2-20261016'); status='failed'; check=MacCheckpoint(seconds=870)
    try:
        verify(DECL); verify(BDECL)
        names=NAMES+['rust-r1-once-results-20261016','rust-r1-once-results-20261016-records',
            'rust-r1-once-final-integrity-20261016-records']
        pins=[validate_root(ROOT/'artifacts'/n) for n in names]
        assert len(pins)==15 and sum(p['status']=='failed' for p in pins)==5
        prior=verify_evidence(ROOT/'artifacts/rust-r1-once-results-20261016-evidence','complete')
        assert digest(ROOT/'crates/banto-ai/src/model.rs')=='acefec42e7506d807f7deae22269f30f9bf409a8c8cf9d1ddb59c2ef6af7fa80'
        model_before=digest(ROOT/'crates/banto-ai/src/model.rs'); lock_before=digest(ROOT/'Cargo.lock')
        manifest=ROOT/'crates/banto-ai/Cargo.toml'; manifest_before=digest(manifest)
        with zipfile.ZipFile(ROOT/'artifacts/rust-r1-once-source-declaration-20261016-records/sources.zip') as z:
            initial=z.read('crates/banto-ai/Cargo.toml')
        current=manifest.read_bytes(); assert initial!=current
        out.write('Cargo-initial.toml',initial); out.write('Cargo-current-preserved.toml',current)
        git_all=subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True,timeout=20)
        git_docs=subprocess.run(['git','diff','--check','--','docs'],cwd=ROOT,capture_output=True,timeout=20)
        assert git_all.returncode==2 and git_docs.returncode==0
        assert re.fullmatch(rb'crates/banto-ai/Cargo\.toml:\d+: new blank line at EOF\.\n',git_all.stdout) and not git_all.stderr
        out.json('git-checks.json',{'all':{'exit':git_all.returncode,'stdout':git_all.stdout.decode(),'stderr':git_all.stderr.decode()},
            'documents':{'exit':git_docs.returncode,'stdout':git_docs.stdout.decode(),'stderr':git_docs.stderr.decode()},'manifest_edited_by_this_unit':False})
        helpers=[ROOT/'tools/public-data'/n for n in ['rust_r1_once_contract.py','rust_r1_once_contract_repair.py','rust_r1_once_publish.py','rust_r1_once_final_check.py']]
        for p in helpers: ast.parse(p.read_text())
        out.sources([*helpers,ROOT/'tools/verification_records.py',ROOT/'tools/public-data/macos_rust_run.py'])
        changes={}
        report=(ROOT/REPORT).read_text().replace('、Cargo/lock/default/許容差/元参照は不変。','、lock/許容差/元参照は不変。本工程からのCargo/default編集は0（作業中の別差分は次の最終確認注記）。',1)
        report+='''
## 最終確認注記

全artifact/EvidenceStore、元source/SDK/model/lock pinsの確認は通過した。一方、全体git diff --checkはcrates/banto-ai/Cargo.toml末尾の空行を指摘してexit2。このmanifestは本工程では編集しておらず、source declaration時のsnapshotと現在のbytesが異なることを確認した。変更者や意図は推定せず、現在の変更をそのまま保護した。したがって本報告の「変更0」は本工程からの編集が0という意味であり、他作業を含めたworkspace全体が開始時と同じという意味ではない。docs限定のdiff --checkはexit0。

最初の最終検査recordsはfailedのまま保持し、この区別を保存したfresh最終検査はartifacts/rust-r1-once-final-check2-20261016、同-records、同-evidence。追加の数値演算/live read/命令読取りはない。
'''
        changes[REPORT]=report
        handoff=ROOT/'docs/current-handoff.md'; text=handoff.read_text()
        text=text.replace('model/Cargo/default/許容差不変、R1安定版累積1点未達/R2停止。',
            'model/lock/許容差不変、本工程のCargo/default編集0、R1安定版累積1点未達/R2停止。',1)
        pos=text.index('\n\n次は[')
        text=text[:pos]+'\n\n最終確認: 証跡/pins/モデルは通過。作業中に本工程が編集していないCargo.tomlが開始snapshotから変化し、全体diff --checkは末尾空行でexit2。変更を保護し編集せず、docs限定exit0を記録。詳細とfinal-check2証跡は上の結果の最終注記。'+text[pos:]
        changes['docs/current-handoff.md']=text
        evidence=ROOT/'artifacts/rust-r1-once-final-check2-20261016-evidence'
        with EvidenceStore(evidence) as store:
            store.write_json('root-pins',pins); store.write_json('prior-evidence',prior)
            for i,p in enumerate(helpers): store.write_bytes(f'source-{i}',p.read_bytes())
            for i,n in enumerate(changes): store.write_bytes(f'before-{i}',(ROOT/n).read_bytes())
            for n,value in changes.items(): (ROOT/n).write_text(value)
            for i,n in enumerate(changes): store.write_bytes(f'after-{i}',(ROOT/n).read_bytes())
            store.write_bytes('Cargo-initial',initial); store.write_bytes('Cargo-current-preserved',current)
            for p in sorted((ROOT/'artifacts/rust-r1-once-final-integrity-20261016-records').iterdir()): store.write_bytes('first-final-'+p.name,p.read_bytes())
            store.write_json('documents-after',[{'path':n,'sha256':digest(ROOT/n)} for n in changes])
        ev=verify_evidence(evidence,'complete'); out.json('evidence-check.json',ev); out.json('root-pins.json',pins)
        assert digest(manifest)==manifest_before and digest(ROOT/'Cargo.lock')==lock_before and digest(ROOT/'crates/banto-ai/src/model.rs')==model_before
        verify(DECL); verify(BDECL)
        for p in pins: assert validate_root(ROOT/p['root'])==p
        last=subprocess.run(['git','diff','--check','--','docs'],cwd=ROOT,capture_output=True,timeout=20); assert last.returncode==0
        summary={'artifact_and_source_integrity_pass':True,'verified_roots':15,'failed_roots_preserved':5,
            'workspace_global_whitespace_clean':False,'documents_whitespace_clean':True,'independent_manifest_change_preserved':True,
            'new_tensor_BLAS_calls':0,'new_live_reads':0,'model_unchanged':True,'R1_complete':False,'R2_started':False,'resources':check.check()}
        out.json('summary.json',summary); print(json.dumps({'final_integrity_pass':True,'global_whitespace_issue_preserved':True,'evidence':ev})); status='complete'
    finally: out.close(status)

if __name__=='__main__': main()
