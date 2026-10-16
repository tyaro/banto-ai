"""Publish R1 preparation as incomplete pending human Xcode setup."""
import ast,json,re,sys,tomllib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/public-data'),str(ROOT/'models/mini-transformer')]
from verification_records import EvidenceStore
from metropt_multiday import Files,digest
from macos_demand_runtime import MacCheckpoint
from macos_rust_run import source_files
from care_rust_r0_close import verify_evidence
REPORT='docs/results/banto-ai-rust-r1-preparation-2026-10-16.md'
ROOTS=['rust-r1-declaration-20261016','rust-r1-declaration2-20261016','rust-r1-lock-20261016','rust-r1-resolve-analysis-20261016','rust-r1-lock-seed-20261016','rust-r1-tree-20261016','rust-r1-metadata-20261016','rust-r1-metadata-20261016-records','rust-r1-metadata2-20261016','rust-r1-metadata2-20261016-records','rust-r1-effective-features-20261016','rust-r1-metadata3-20261016','rust-r1-metadata3-20261016-records','rust-r1-format-20261016','rust-r1-format-final-20261016','rust-r1-compiler-preflight-20261016','rust-r1-monitor-smoke-20261016','rust-r1-python-reference-20261016','rust-r1-python-reference-20261016-records']
def validate_root(path):
    c=json.loads((path/'root-closed.json').read_bytes())
    assert c['status'] in ['complete','failed']
    assert {p.name for p in path.iterdir()}=={f['name'] for f in c['files']}|{'root-closed.json'}
    for f in c['files']:
        p=path/f['name'];assert p.name==f['name'] and not p.is_symlink()
        assert p.stat().st_size==f['bytes'] and digest(p)==f['sha256']
    return {'root':str(path.relative_to(ROOT)),'status':c['status'],'closure_sha256':digest(path/'root-closed.json')}
def main():
    out=Files(ROOT/'artifacts/rust-r1-prepared-20261016');check=MacCheckpoint(seconds=870);status='failed'
    evidence=ROOT/'artifacts/rust-r1-prepared-20261016-evidence'
    try:
        phase={'scope':'R1 source/reference/dependency preparation publication only','stage_complete':False,'R1_build_verified':False,'R1_parity_verified':False,'R2_started':False,'pending_human_action':'Xcode license review and setup; clang exit69','compiler_license_accepted_by_agent':False}
        out.json('phase.json',phase)
        helpers=[ROOT/'tools/public-data'/n for n in ['rust_r1_python_reference.py','rust_r1_compare.py','rust_r1_metadata.py']]
        sources=list(dict.fromkeys([Path(__file__),ROOT/'.gitignore',ROOT/'tools/verification_records.py',ROOT/'tools/public-data/care_rust_r0_close.py',*source_files(),*helpers]))
        out.sources(sources)
        roots=[validate_root(ROOT/'artifacts'/name) for name in ROOTS]
        assert json.loads((ROOT/'artifacts/rust-r1-compiler-preflight-20261016/exit.json').read_bytes())['returncode']==69
        meta=json.loads((ROOT/'artifacts/rust-r1-metadata3-20261016/summary.json').read_bytes());assert meta['active_dependencies']==154 and meta['flex_cpu_only']
        reference=json.loads((ROOT/'artifacts/rust-r1-python-reference-20261016/summary.json').read_bytes());assert reference['forward_calls']==7 and reference['test_or_truth_opened'] is False
        for helper in helpers+[ROOT/'tools/public-data/macos_rust_run.py']:ast.parse(helper.read_text())
        package=tomllib.loads((ROOT/'crates/banto-ai/Cargo.toml').read_text())
        assert package['test'][0]['required-features']==['reference-tests']
        assert tomllib.loads((ROOT/'rust-toolchain.toml').read_text())['toolchain']['channel']=='1.95.0'
        cfgs=[ROOT/'examples/configs'/n for n in ['rust-small-forecaster-r0-20261016.json','rust-small-forecaster-r0-20261016-r0.1.json','care-a-maintenance-20261016-r1.json']]
        before_cfg={str(p):digest(p) for p in cfgs}
        report=(ROOT/REPORT).read_text().replace('に保存する。','に保存した。')
        report=report.replace('native Rust1.95.0とcargo/rustfmtは直接起動できる。','native Rust1.95.0とcargo/rustfmtは直接起動できる。workspace内に1.95.0のtoolchain pinを保存した。')
        report=report.replace('コード |\n','コード |\n')
        report+='\n監視のdisk走査は別threadへ移してmemory samplingを妨げにくくし、人工の親子process2件でsmokeを実施した。exit0、92sample、実最大間隔23.55ms、監視込みfootprint27,903,224B/RSS50,446,336B。旧監視の最大間隔1.418秒の記録は保持した。研究参照modelを要するintegration testはreference-tests featureのopt-inで、通常のunit testは保存modelを要しない。どちらもRustテスト実行はSDK設定後である。\n'
        changes={REPORT:report}
        h='docs/current-handoff.md'
        changes[h]='## 最新 — Rust R1のソースと参照準備、Xcode設定待ち（2026-10-16）\n\n人の計画実行指示に従い、[R1準備結果と再開手順](results/banto-ai-rust-r1-preparation-2026-10-16.md)を保存。banto-aiのcrates/banto-aiにinput/neutral checkpoint/model/比較用predict exampleと試験コードを実装、root Cargo workspace/lockとlocal Rust1.95.0 pinを追加。前処理→full SmallForecaster分位点推論のソースを作成、rustfmt exit0。**Rustの型検査/build/テスト/数値一致は未確認、R1は未完**。学習は未着手。\n\n新規lockはBurn任意LibTorch枝のyanked zip0.6でexit101。公式v0.22 lockをseedにローカル解決し、effective Cargo treeで154有効package/Flex stdのみ、rayon/SIMD/tch/CubeCLなしを確認。license一覧/本文保存。無効zip0.6等はlockに残り、下流のlockなし解決は配布課題。registry編集/stub/backend切替なし。\n\n固定fold0のtrain先頭/末尾2batchと人工zero/constant/floor3caseのPython forward計7回、全finite/順序/floor境界pass。target数量skip、test/validation/calibration/truth open拒否。artifacts/rust-r1-python-reference-20261016はcompleteで入力/中間値/manifestを保存。これを再生成せずRust比較へ使う。\n\n**現在の阻害要因はclang --versionのexit69、Xcode/Apple SDK利用規約未同意**。人へ非同期に確認・同意の完了連絡を依頼中。自動同意/回避なし。完了後はfresh compiler preflight→R1のcargo test（reference-tests、BANTO_R1_REPO）→predict example→固定R0許容差の比較器の順。具体commandは結果報告にある。既存rootsを再利用しない。\n\nmacOS process groupでcompiler/linker子孫を監視するwrapperを実装。非同期disk走査版の人工親子2process smoke exit0、92sample/最大23.55ms。hard capではなく捕捉限界も保存。親900/子870・2GiB・旧保存上限、cache+target768MiBを維持。全source/記録/文書前後/状態はartifacts/rust-r1-prepared-20261016-evidence。宣言path/lock/metadata保存・active誤分類の失敗も保持。\n\nR2 backward/学習0、CARE test/需要2015再評価0、banto-industrial/denroku変更0。需要2014以前調整/同休業mean28/四季過小過大非増加/観測欠測0分離、Windows別検証・heartbeat PAUSED維持。以下は旧記録。\n\n---\n\n'+(ROOT/h).read_text()
        index='docs/research/README.md'
        changes[index]=(ROOT/index).read_text().replace('## 文書\n','## 文書\n\n- [banto-ai Rust R1の準備と再開手順](../results/banto-ai-rust-r1-preparation-2026-10-16.md) — crateソース/lock/154有効依存と7参照forwardを保存。Xcode規約未同意でbuild/テスト/数値一致は待機、R1未完。\n',1)
        index='docs/results/README.md'
        changes[index]=(ROOT/index).read_text().replace('## 産業設備の保全と点検支援\n','## Rustクレートの移植\n\n- [banto-ai Rust R1の準備と再開手順](banto-ai-rust-r1-preparation-2026-10-16.md) — ソース/参照準備まで。Xcode設定待ち、build/数値一致は未確認。\n\n## 産業設備の保全と点検支援\n',1)
        plan='docs/research/banto-ai-rust-implementation-plan-2026-10-16.md'
        old=(ROOT/plan).read_text()
        changes[plan]=old.replace('状態: 実行計画。2026-10-16 JST。今回の依頼では計画を保存し、クレート作成・依存導入・学習・推論は開始しない。','状態: R1a/R1b着手。Rustクレートのソース/依存解決とPython固定参照を準備。Xcode利用規約の設定待ちでRust build/型検査/テスト/数値比較は未完。[準備結果と再開手順](../results/banto-ai-rust-r1-preparation-2026-10-16.md)を参照。2026-10-16 JST。',1)
        r0='docs/research/rust-small-forecaster-r0-2026-10-16.md'
        changes[r0]=(ROOT/r0).read_text().replace('状態: R0の比較契約と接続方針を固定。R1のcompile/数値比較、R2の学習再開、R4の製品統合は未実施。','状態: R0の比較契約と接続方針を固定。R1のソース/参照は準備済み、Xcode設定待ちでcompile/数値比較は未完。R2の学習再開、R4の製品統合は未実施。',1)
        road='docs/research/research-roadmap.md'
        changes[road]='## 現在 — banto-ai Rust R1準備、compiler設定待ち（2026-10-16）\n\n[R1準備/再開手順](../results/banto-ai-rust-r1-preparation-2026-10-16.md)。crates/banto-aiに前処理/モデル/neutral読込/CLIと試験コード、154依存のCPU lockと7固定Python参照を保存。build/テスト/一致は未確認。clang exit69のXcode規約未同意を人へ連絡中。設定後は固定参照でR1を完了し、R2学習へはまだ進まない。下流のlockなし依存解決は別課題。以下は旧記録。\n\n---\n\n'+(ROOT/road).read_text()
        readme='README.md'
        changes[readme]=(ROOT/readme).read_text()+'\n## Rust AIクレートの研究実装\n\nAI本体は [crates/banto-ai](crates/banto-ai/README.md) に置き、学習・推論・保存再開を共通化する。[実装計画](docs/research/banto-ai-rust-implementation-plan-2026-10-16.md)に沿ってR1へ着手した。現在はソース・依存・Python参照まで準備し、Xcode利用規約の設定待ちでRust build/テスト/数値一致は未確認。[再開手順と状態](docs/results/banto-ai-rust-r1-preparation-2026-10-16.md)を参照。既存Python runtimeと評価結果は維持する。\n'
        for p in [ROOT/REPORT]:
            for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
                if target.startswith(('http://','https://','#')):continue
                assert (p.parent/target.split('#')[0]).exists(),target
        with EvidenceStore(evidence) as store:
            store.write_json('phase',phase);store.write_json('input-root-pins',roots)
            for i,p in enumerate(sources):store.write_bytes(f'source-{i}',p.read_bytes())
            for i,p in enumerate(cfgs):store.write_bytes(f'fixed-config-{i}',p.read_bytes())
            before=[]
            for i,(name,value) in enumerate(changes.items()):
                p=ROOT/name;store.write_bytes(f'before-{i}',p.read_bytes());before.append({'path':name,'sha256':digest(p)})
            store.write_json('before-index',before)
            for name,value in changes.items():(ROOT/name).write_text(value)
            for i,name in enumerate(changes):store.write_bytes(f'after-{i}',(ROOT/name).read_bytes())
            for i,name in enumerate(ROOTS):
                folder=ROOT/'artifacts'/name
                for j,filename in enumerate(['phase.json','command.json','command-exit.json','exit.json','state.json','stdout.txt','stderr.txt','summary.json','root-closed.json','failure.json']):
                    p=folder/filename
                    if p.exists():store.write_bytes(f'root-{i}-{j}',p.read_bytes())
            folder=ROOT/'artifacts/rust-r1-metadata3-20261016'
            store.write_bytes('license-inventory',(folder/'active-dependencies.json').read_bytes())
            store.write_bytes('license-documents',(folder/'active-license-documents.zip').read_bytes())
            store.write_bytes('reference-fixture-index',(ROOT/'artifacts/rust-r1-python-reference-20261016/fixtures.json').read_bytes())
            assert {str(p):digest(p) for p in cfgs}==before_cfg
            for item in roots:assert digest(ROOT/item['root']/'root-closed.json')==item['closure_sha256']
            summary={'publication_status':'complete','R1_complete':False,'crate_source_created':True,'rustfmt_parse_pass':True,'active_dependency_inventory_complete':True,'python_reference_cases':7,'Rust_build_tests_parity_verified':False,'R2_training_started':False,'blocked_on':'human Xcode license setup; clang exit69','pending_async_question':True,'R0_scientific_configs_unchanged':True,'resources':check.check()}
            store.write_json('summary',summary);store.write_terminal('terminal',{'exit':0,'state':'prepared; compiler prerequisite pending','resources':check.check()})
        out.json('evidence-readback.json',verify_evidence(evidence,'complete'));out.json('summary.json',summary)
        print(json.dumps(summary));status='complete'
    finally:out.close(status)
if __name__=='__main__':main()
