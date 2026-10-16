"""Recorded branch consolidation, without numerical experiments or archive execution."""
import ast
import hashlib
import io
import json
import posixpath
import re
import subprocess
import sys
import traceback
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'models/mini-transformer'),str(ROOT/'tools/public-data')]
from metropt_multiday import Files,digest,verify_closed
from macos_demand_runtime import MacCheckpoint
from rust_r1_publish_preparation import validate_root
from verification_records import EvidenceStore
from care_rust_r0_close import verify_evidence

BASE='50d69b684acd8af6db6c045e372ce9d564d855f4'
MAIN='6f1285d28a37edf486ba5c49b8dac3708c7f3067'
PREFIX='research-consolidation-20261017'
ARCHIVE='experiments/archive/rust-r1-20261016'
KEEP={'rust_r1_compare.py','rust_r1_python_reference.py','rust_r1_metadata.py','rust_r1_publish_preparation.py'}
FIXED=['crates/banto-ai/src/model.rs','examples/configs/rust-small-forecaster-r0-20261016-r0.1.json',
       'examples/configs/rust-r2p-synthetic-protocol-20261016.json','examples/configs/rust-r2p-synthetic-fixtures-20261016.json',
       'docs/research/rust-r2p-synthetic-training-contract-2026-10-16.md']
def read(p):return json.loads(Path(p).read_bytes())
def root(suffix):return ROOT/'artifacts'/(PREFIX+suffix)
def candidates():
    paths=[p for p in (ROOT/'tools/public-data').glob('rust_r1_*') if p.name not in KEEP and p.suffix in ['.py','.c']]
    paths += [ROOT/'crates/banto-ai/src'/name for name in ['context.rs','fma.rs','fused_linear.rs']]
    paths += [p for p in (ROOT/'crates/banto-ai/examples').glob('*.rs') if p.name!='predict.rs']
    return sorted(paths)
def imports_without_archived_dependencies(paths):
    selected={p.resolve() for p in paths}; names={p.stem for p in paths if p.suffix=='.py'}
    for folder in ['tools','tests','models/mini-transformer']:
        for p in (ROOT/folder).rglob('*.py'):
            if p.resolve() in selected:continue
            tree=ast.parse(p.read_bytes(),filename=str(p))
            for n in ast.walk(tree):
                modules=[n.module or ''] if isinstance(n,ast.ImportFrom) else [a.name for a in n.names] if isinstance(n,ast.Import) else []
                for m in modules:assert m.split('.')[-1] not in names,(str(p),m)
def declare(out,check):
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==BASE
    paths=candidates(); imports_without_archived_dependencies(paths)
    entries=[{'old':str(p.relative_to(ROOT)),'new':ARCHIVE+'/sources/'+str(p.relative_to(ROOT))+'.txt','sha256':digest(p),'bytes':p.stat().st_size} for p in paths]
    protected=[{'path':n,'sha256':digest(ROOT/n)} for n in FIXED]
    previous=[validate_root(ROOT/'artifacts'/('rust-r2p-reference-20261016'+s)) for s in ['-declaration','-lock','-numeric','-publication']]
    assert all(x['status']=='complete' for x in previous)
    out.sources([Path(__file__),*paths,*[ROOT/p for p in FIXED],ROOT/'Cargo.lock',ROOT/'crates/banto-ai/Cargo.toml',ROOT/'crates/banto-ai/src/lib.rs',ROOT/'docs/current-handoff.md'])
    out.json('admission.json',{'authorization':'human: おすすめでお願いします; branch consolidation and reviewable PR',
        'archive_source_commit':BASE,'main_to_integrate':MAIN,'source_archive_is_nonexecuting_text':True,
        'archive_moves':entries,'fixed_pins':protected,'previous_closed_roots':previous,
        'allowed_runtime_changes':['remove undefined, unadopted Rust extension exports','disable implicit Cargo example discovery','apply already verified single gemm root-edge removal'],
        'document_changes':'short current handoff; historical handoff with rebased links; current-purpose entrypoints; archive catalog; consolidation report',
        'limits':read(ROOT/'examples/configs/rust-r2p-synthetic-protocol-20261016.json')['limits'],
        'tests':'bounded locked offline Cargo default targets without reference-tests; syntax/import/link/archive checks; common-runtime smoke and relevant Python tests; no numerical reference regeneration',
        'scope_stops':['pointer tracking','real training or CARE/demand evaluation','tolerance changes','closed evidence mutation','Windows native execution','automatic main merge or deletion of old branches'],
        'resources':check.check()})

def apply(out,check):
    verify_closed(root('-declaration')); admission=read(root('-declaration')/'admission.json')
    assert subprocess.check_output(['git','rev-parse','MERGE_HEAD'],cwd=ROOT,stderr=subprocess.DEVNULL).decode().strip()==MAIN
    for pin in admission['fixed_pins']:assert digest(ROOT/pin['path'])==pin['sha256']
    sources=[ROOT/item['old'] for item in admission['archive_moves']];imports_without_archived_dependencies(sources)
    for item in admission['archive_moves']:
        old=ROOT/item['old']; new=ROOT/item['new'];assert digest(old)==item['sha256'] and not new.exists()
        new.parent.mkdir(parents=True,exist_ok=True);old.rename(new)
        assert digest(new)==item['sha256']
    catalog={'schema':'banto.research-source-archive.v1','source_commit':BASE,'status':'historical_not_active_or_runnable',
             'entries':admission['archive_moves'],'runtime_configs':'fixed historical configs stay at their original paths so reports and frozen evidence keep their identities'}
    out.json('archive-catalog.json',catalog)
    (ROOT/ARCHIVE/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    (ROOT/ARCHIVE/'README.md').write_text(f'''# Rust R1の停止済み調査資料

2026-10-17に通常の実行対象から退避した。不採用の拡張、単発の診断・報告生成、ポインタ/SGEMM調査を含む。全source bytesは保存時のまま、拡張子に`.txt`を付けてimport・compile・実行対象から外した。

原版commit: `{BASE}`。保存tag: `archive/preformal-research-20261017`。[catalog](catalog.json)は元パス・保存先・サイズ・SHA256を列挙する。各ファイルを検証して退避し、失敗や不採用の履歴を変更していない。閉鎖済みartifactは元の場所に残す。

ここにあるコードは現checkoutのAPIではない。元の相対パス・ROOT計算・依存・Cargo featureを前提とするため、名前を戻したり直接実行したりしない。歴史的な構成の確認には原版commitと当時の証跡を使う。ポインタ追跡は人の指示で停止しており、通常の「進めて」で再開しない。

現行の比較器・参照producer・metadata・閉鎖検証helperは、共通利用があるため`tools/public-data/`に残した。旧R1 JSONと報告は固定パスを保持し、実行許可や次工程の指示とは扱わない。[現在の引継ぎ](../../../docs/current-handoff.md)を優先する。
''')
    manifest=ROOT/'crates/banto-ai/Cargo.toml'; text=manifest.read_text(); assert 'autoexamples' not in text
    manifest.write_text(text.replace('[package]\n','[package]\nautoexamples = false\n',1).rstrip()+'\n')
    lib=ROOT/'crates/banto-ai/src/lib.rs'; text=lib.read_text()
    for feature,module in [('reference-normalization','context'),('fma-extension','fma'),('fused-linear-extension','fused_linear')]:
        old=f'#[cfg(feature = "{feature}")]\npub mod {module};\n';assert text.count(old)==1;text=text.replace(old,'')
    lib.write_text(text)
    lock=ROOT/'Cargo.lock'; saved=ROOT/'artifacts/rust-r2p-reference-20261016-lock'
    verify_closed(saved); assert lock.read_bytes()==(saved/'Cargo.lock.before').read_bytes()
    lock.write_bytes((saved/'Cargo.lock.proposed').read_bytes())
    handoff=ROOT/'docs/current-handoff.md'; before=handoff.read_text()
    out.write('handoff-before.md',before.encode())
    def rebase(match):
        target=match.group(1)
        if target.startswith(('http:','https:','#','/','mailto:')):return match.group(0)
        return ']('+posixpath.normpath('../'+target)+')'
    history=ROOT/'docs/history/current-handoff-through-20261016.md'; assert not history.exists()
    history.write_text(f'''# 2026-10-16までの引継ぎ履歴

2026-10-17に`docs/current-handoff.md`から退避。原文はcommit `{BASE}` と今回の閉鎖済み宣言snapshotに保存した。本文の状態と「次」は当時の記録であり、現在の指示ではない。移設に伴いMarkdownの相対リンクだけを1階層上へ付け替えた。元sourceへのリンクは[退避catalog](../../{ARCHIVE}/catalog.json)と原版commitで辿る。

[現在の引継ぎ](../current-handoff.md)を優先する。以下は履歴。

---

'''+re.sub(r'\]\(([^)]+)\)',rebase,before))
    handoff.write_text('''# 現在の引継ぎ — 2026-10-17

## 主目的

TimesFM3を参考にした自作モデルの実用性を検証する。保全・点検支援を第一優先に、需要予測・PSIも対象にする。学習・推論・optimizer保存再開をbanto-aiのRustクレートへ実装し、banto-industrialとdenroku-psi-demoから使う。利用側→banto-aiの依存方向を守る。

## 現在地

- [復帰計画](research/banto-ai-practical-training-return-plan-2026-10-16.md)と[実装計画](research/banto-ai-rust-implementation-plan-2026-10-16.md)に沿って進める。
- Rust推論R1は中間値1点未達。許容差を変えず、正式R2の実データ学習は停止中。最終出力の通過を正式合格へ読み替えない。
- [R2P固定契約](research/rust-r2p-synthetic-training-contract-2026-10-16.md)と[人工Python参照](results/rust-r2p-lock-and-python-reference-2026-10-16.md)は保存済み。loss7/clip4/AdamW6/小型8更新、独立照合107件pass。参照を再生成しない。
- 検証済みのCargo.lock案を本整理で適用。gemmの不要な直接edgeだけを除いた。非採用のRust拡張・診断と単発調査は[履歴](../experiments/archive/rust-r1-20261016/README.md)へ退避。学習エンジンと保存再開のRust実装は未着手。
- main側のWindows修正4コミットを整理ブランチへ取り込み、既存機能を維持した。Mac共通coreの確認とWindows native/OS依存試験は分ける。
- [今回の整理と確認結果](results/research-consolidation-2026-10-17.md)を参照。整理PRでmainへ提案し、mainの自動mergeはしない。

## 次に行うこと

1. 固定済み条件に従い、feature-gatedな小型loss/autodiff/gradient/clip/互換AdamWを実装する。
2. 同じ人工入力でRust連続8更新と、4更新→別process復元→4更新を検証する。入力拒否6、checkpoint拒否8、writer途中停止3を維持する。
3. 部品通過後、全モデルの人工接続条件を別途固定する。R1とR2Pが通るまで正式R2実データ学習へ移らない。

## 維持する条件

ポインタ/once/TLS/PAC/vendor内部追跡は停止。CARE/MetroPTの既読testは凍結し、需要2015の再評価も停止。需要の調整は2014以前だけ、同じ休業仮定のmean28比較、四季平均の過小量・過大量非増加、観測のみ・欠測0仮定の分離を維持する。

各unitは親900秒/子870秒、physical footprint・peak RSS各2GiB、cache+target1.5GiB/jobs1。artifact/EvidenceStore/stdioの元上限、既存変更・失敗・closed rootsの保護を維持。許容差は原R0.1のまま。heartbeatはPAUSED。下流編集・本番採用・自動mergeは行わない。

## 保存した研究結果

[CARE学習・評価](results/care-macos-learning-evaluation-2026-10-16.md)は検知3/12・未検知9・正常誤警報3。[MetroPT M1](results/metropt-macos-m1-2026-10-16.md)は改善と悪化を両方保存。移植の成功と保全判断の有用性は別に判定する。

## 履歴

- [2026-10-16までの全引継ぎ](history/current-handoff-through-20261016.md)
- [停止済みRust調査の保存先](../experiments/archive/rust-r1-20261016/README.md)
- 保存地点: `archive/preformal-research-20261017` / `50d69b6`。旧ブランチを削除しない。
''')
    crate=ROOT/'crates/banto-ai/README.md'; text=crate.read_text(); start=text.index('## 現在の研究順序')
    crate.write_text(text[:start]+'''## 現在の研究順序

[現在の引継ぎ](../../docs/current-handoff.md)と[復帰計画](../../docs/research/banto-ai-practical-training-return-plan-2026-10-16.md)に沿って進める。Rust推論R1は中間値1点未達で、正式R2実データ学習は停止中。人工データだけのR2P loss/gradient/AdamW/checkpoint実装が次工程である。Python参照は生成済みだが、Rust学習・保存再開は未実装。

現在の公開moduleはcheckpoint/error/input/model。default testは合成入力のunit testだけで、CARE参照のintegration testはreference-testsで明示opt-inする。暗黙のexample探索は無効、公開exampleはpredictのみ。不採用FMA/context/fused-linear拡張と診断exampleは[履歴資料](../../experiments/archive/rust-r1-20261016/README.md)へ退避した。旧featureは再定義しない。閉鎖済み証跡と原許容差を維持する。

本整理では検証済みのlock最小案を適用し、manifestにないgemmの直接edgeだけを削除した。package/versionの追加更新は行わない。[整理結果](../../docs/results/research-consolidation-2026-10-17.md)に現在の構成での検証結果を記録する。過去時点のbuild成功をRust学習や数値互換の合格へ読み替えない。
''')
    ignore=ROOT/'.gitignore'; text=ignore.read_text(); assert '/outputs/' not in text
    ignore.write_text(text+'\n# Local isolated resolution/source workspaces\n/outputs/\n')
    out.sources([Path(__file__)])
    for pin in admission['fixed_pins']:assert digest(ROOT/pin['path'])==pin['sha256']
    for pin in admission['previous_closed_roots']:assert validate_root(ROOT/pin['root'])==pin
    out.json('summary.json',{'archived_sources':len(admission['archive_moves']),'archive_bytes_verified':True,
        'lock_proposal_applied':True,'fixed_pins_unchanged':admission['fixed_pins'],'old_roots_unchanged':True,
        'original_handoff_lines':len(before.splitlines()),'current_handoff_lines':len(handoff.read_text().splitlines()),
        'reference_or_training_run':False,'resources':check.check()})

def validate(out,check):
    verify_closed(root('-declaration'));verify_closed(root('-apply'))
    admission=read(root('-declaration')/'admission.json')
    for item in admission['archive_moves']:
        assert not (ROOT/item['old']).exists() and digest(ROOT/item['new'])==item['sha256']
        assert (ROOT/item['new']).stat().st_size==item['bytes']
    imports_without_archived_dependencies([ROOT/item['old'] for item in admission['archive_moves']])
    for p in admission['fixed_pins']:assert digest(ROOT/p['path'])==p['sha256']
    for p in admission['previous_closed_roots']:assert validate_root(ROOT/p['root'])==p
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    syntax={'python':0,'json':0}
    for n in tracked:
        if not n:continue
        p=ROOT/n; assert p.is_file() and not p.is_symlink(),n
        if p.suffix=='.py':ast.parse(p.read_bytes(),filename=n);syntax['python']+=1
        if p.suffix=='.json':read(p);syntax['json']+=1
    docs=['README.md','docs/README.md','docs/current-handoff.md','docs/history/README.md',
          'docs/history/current-handoff-through-20261016.md','docs/history/main-document-status-20260925.md',
          'docs/research/banto-ai-rust-implementation-plan-2026-10-16.md',
          'docs/research/banto-ai-practical-training-return-plan-2026-10-16.md',
          'docs/results/research-consolidation-2026-10-17.md','crates/banto-ai/README.md',
          'tools/public-data/README.md',ARCHIVE+'/README.md']
    links=0
    for n in docs:
        for t in re.findall(r'\]\(([^)]+)\)',(ROOT/n).read_text()):
            if t.startswith(('http:','https:','#','/','mailto:')):continue
            assert ((ROOT/n).parent/t.split('#')[0]).exists(),(n,t);links+=1
    assert not subprocess.check_output(['git','ls-files','-u'],cwd=ROOT)
    assert (ROOT/'Cargo.lock').read_bytes()==(ROOT/'artifacts/rust-r2p-reference-20261016-lock/Cargo.lock.proposed').read_bytes()
    for n in ['src/banto_ai/anomaly_v03_native.py','tests/test_anomaly_v03_native.py']:
        assert (ROOT/n).read_bytes()==subprocess.check_output(['git','show',MAIN+':'+n],cwd=ROOT)
    commands=[
        ['ruby','-ryaml','-rjson','-e','workflow=YAML.safe_load(File.read(".github/workflows/ci.yml")); jobs=workflow.fetch("jobs"); abort "wrong jobs" unless jobs.keys.sort==["test","verify-python314-journal","windows-native-fixture"].sort; abort "Python policy changed" unless jobs.fetch("windows-native-fixture").fetch("steps")[1].fetch("with").fetch("python-version")=="3.14"; puts JSON.generate({yaml_parse:"pass",jobs:jobs.keys})'],
        [str(ROOT/'environments/demand-macos/.venv/bin/python'),'-B','tools/smoke.py'],
        [str(ROOT/'environments/demand-macos/.venv/bin/python'),'-B','tools/safety_check.py'],
        ['git','diff','--check'],['git','diff','--cached','--check']]
    rows=[]
    for cmd in commands:
        result=subprocess.run(cmd,cwd=ROOT,capture_output=True,timeout=60)
        assert len(result.stdout)<=1048576 and len(result.stderr)<=131072
        rows.append({'argv':cmd,'exit':result.returncode,'stdout':result.stdout.decode(),'stderr':result.stderr.decode()})
        out.json('command-'+str(len(rows))+'.json',rows[-1]);assert result.returncode==0,rows[-1];check.check()
    out.sources([Path(__file__),ROOT/'tools/smoke.py',ROOT/'tools/safety_check.py',ROOT/'.github/workflows/ci.yml',ROOT/'.gitignore'])
    out.json('summary.json',{'syntax':syntax,'checked_local_links':links,'archive_sources':len(admission['archive_moves']),
        'source_import_boundary_pass':True,'fixed_pins_unchanged':True,'old_closed_roots_unchanged':True,
        'main_native_source_and_test_bytes_preserved':True,'lock_proposal_applied_exactly':True,
        'commands_passed':len(commands),'reference_or_training_run':False,'resources':check.check()})
    print(json.dumps({'validation':'pass','syntax':syntax,'local_links':links,'archived_sources':len(admission['archive_moves'])}))

def publish(out,check):
    suffixes=['-declaration','-declaration-records','-apply','-apply-records','-cargo-metadata-records',
        '-cargo-test-records','-rustfmt-records','-python-tests-records','-python-temp-policy',
        '-python-canonical-temp-records','-validate','-validation-records',
        '-publish','-publication-records']
    roots=[validate_root(root(s)) for s in suffixes]
    expected_failed={'-python-tests-records','-python-canonical-temp-records','-publish','-publication-records'}
    for s,p in zip(suffixes,roots,strict=True):assert p['status']==('failed' if s in expected_failed else 'complete')
    admission=read(root('-declaration')/'admission.json'); validation=read(root('-validate')/'summary.json')
    assert validation['checked_local_links']==642 and validation['archive_sources']==67
    for p in admission['fixed_pins']:assert digest(ROOT/p['path'])==p['sha256']
    for p in admission['previous_closed_roots']:assert validate_root(ROOT/p['root'])==p
    for p in admission['archive_moves']:assert digest(ROOT/p['new'])==p['sha256'] and not (ROOT/p['old']).exists()
    tests=(root('-python-canonical-temp-records')/'stderr.txt').read_text()
    assert 'Ran 146 tests' in tests and 'FAILED (errors=5, skipped=2)' in tests
    assert tests.count('\nERROR: ')==5 and '\nFAIL: ' not in tests
    assert tests.splitlines().count('banto_ai._anomaly_v03_runtime.IntegrityError: atomic no-replace unsupported on this fixture platform')==4
    assert "FileNotFoundError: [Errno 2] No such file or directory: '/proc/self/mountinfo'" in tests
    cargo=(root('-cargo-test-records')/'stdout.txt').read_text();assert '2 passed; 0 failed' in cargo
    metrics=[read(root(s)/'exit.json') for s in suffixes if s.endswith('-records')]
    for m in metrics:
        assert m['elapsed_seconds']<900 and m['sampled_cache_bytes']<=1610612736
        assert max(m['sampled_group_peak']['monitor_inclusive_footprint'],m['sampled_group_peak']['monitor_inclusive_rss'],m['child_wait_peak_rss_bytes'])<=2147483648
    peaks={k:max(m['sampled_group_peak'][k] for m in metrics) for k in ['monitor_inclusive_footprint','monitor_inclusive_rss']}
    cache=max(m['sampled_cache_bytes'] for m in metrics)
    report=ROOT/'docs/results/research-consolidation-2026-10-17.md'; before=report.read_bytes()
    old='検証中。各commandのstdio/exit/source/state/closureは`artifacts/research-consolidation-20261017-*`のfresh rootへ保存する。最終結果は確認後に本節へ追記する。'
    body=f'''| 確認 | 結果 |
| --- | --- |
| Cargo metadata / locked offline | library・predict・reference-tests opt-inのneutral_integrityだけ。未定義featureと暗黙の診断targetなし |
| Cargo default-feature all-targets test | unit 2件pass、predict compile/test-harness pass。CARE参照は未開封 |
| Rustfmt | pass。model.rsの既存to_vec非推奨warningは保持し、モデル演算を編集していない |
| Python構文 / JSON | tracked Python 928件 / JSON 156件pass |
| 文書リンク | 現在の入口と退避した履歴のローカル参照642件pass |
| archive / 固定値 / import境界 | 67sourceのbytes保持、固定5pin・閉鎖済み参照root不変、現役コードから退避moduleへのimportなし |
| YAML / smoke / safety / diff --check | 全pass。naive smokeは7manifest、MAE 0.75。rawデータ・cache・重みのGit追加なし |

Pythonは既存10module/146testを実行した。最初はMacのtemp経路のsymlink祖先により1failure/15error/2skip。失敗rootを保持し、検査を変えずcanonical `/private/tmp`を使って同じmoduleを一度だけ再確認した。その結果は**139pass・5error・2skipで、suite全体は未通過**。

共通runtime/Phase0/Phase1/Phase2/benchmark/docs/CI検証の95件はすべてpass。公開・受入関連は44件pass。残る5errorはMac未実装のatomic no-replace公開4件と、Linux `/proc/self/mountinfo`に依存するnative収集1件で、共通モデルの回帰と混同しない。Windows native2件はskipで未実行。これらを除外して元suiteをgreen扱いにはせず、元assertionと失敗証跡を保存した。Mac対応の追加実装・OS別の正式受入は今回行っていない。Linux/Windows CIの結果は別途PR上で確認する。

初回publicationはTraceback中の引用を例外数へ重複計上してassertで停止した。集計を例外の最終行だけの照合へ修正し、元失敗root/source/stdioを保持して新規rootに保存した。試験結果・assertion・数値条件を変更せず、テストの再実行も行っていない。

最大観測（監視process込み）はphysical footprint {peaks['monitor_inclusive_footprint']:,}B、RSS {peaks['monitor_inclusive_rss']:,}B、cache+target {cache:,}B。各2GiB/1.5GiB内で、全commandは親900/子870秒内。samplingでありhard OS capとは主張しない。source/stdio/exit/state/closureと失敗2rootを`artifacts/{PREFIX}-*`、publicationの文書前後と監査を`artifacts/{PREFIX}-evidence`へ保存した。

整理ブランチはmainの自動merge条件を設定せず、Draft PRとして提出する。累積の研究変更を含むため、今回の整理差分は保存commit `50d69b6`との比較、全統合差分はPRのmain比較で確認する。旧ブランチ・保存tag・既存artifactは削除しない。'''
    text=before.decode();assert old in text;text=text.replace(old,body)
    evidence=root('-evidence')
    out.sources([Path(__file__),ROOT/'.github/workflows/ci.yml',ROOT/'Cargo.toml',ROOT/'Cargo.lock',
        ROOT/'crates/banto-ai/Cargo.toml',ROOT/'crates/banto-ai/src/lib.rs',*[ROOT/p for p in FIXED]])
    out.json('root-pins.json',roots);out.json('archive-catalog.json',read(ROOT/ARCHIVE/'catalog.json'))
    with EvidenceStore(evidence) as store:
        store.write_json('phase',{'operation':'branch consolidation publication','reference_or_training_run':False,
            'archive_sources':67,'Cargo_tests_pass':2,'Python_common_tests_pass':95,'Python_total_pass':139,
            'Python_OS_dependent_errors':5,'Windows_skipped':2,'local_full_suite_green':False,'automatic_main_merge':False})
        store.write_json('roots',roots);store.write_json('fixed-pins',admission['fixed_pins'])
        store.write_bytes('publication-source',Path(__file__).read_bytes())
        for i,s in enumerate(suffixes):
            for j,p in enumerate(sorted(root(s).iterdir())):store.write_bytes(f'root-{i}-{j}',p.read_bytes())
        diff=subprocess.check_output(['git','diff','--cached','--binary','HEAD'],cwd=ROOT);store.write_bytes('staged-change-before-publication',diff)
        store.write_bytes('report-before',before);report.write_text(text);store.write_bytes('report-after',report.read_bytes())
        for i,n in enumerate(['README.md','docs/README.md','docs/current-handoff.md','docs/history/current-handoff-through-20261016.md',
            'docs/history/main-document-status-20260925.md',ARCHIVE+'/README.md',ARCHIVE+'/catalog.json']):store.write_bytes(f'entrypoint-{i}',(ROOT/n).read_bytes())
        for p in admission['fixed_pins']:assert digest(ROOT/p['path'])==p['sha256']
        for p in roots:assert validate_root(ROOT/p['root'])==p
        store.write_json('resource-peaks',{'peaks':peaks,'cache_bytes':cache})
    ev=verify_evidence(evidence,'complete');out.json('evidence-check.json',ev)
    out.json('summary.json',{'consolidation_complete':True,'archive_sources':67,'Cargo_unit_pass':2,
        'Python_common_pass':95,'Python_total_pass':139,'Python_OS_errors':5,'Windows_unrun':2,
        'local_full_suite_green':False,'R1_pass':False,'formal_R2_started':False,'fixed_pins_unchanged':True,
        'closed_evidence_preserved':True,'main_merge_automatic':False,'resources':check.check()})
    print(json.dumps({'publication':'complete','archive_sources':67,'local_full_suite_green':False,'evidence':ev}))

def main():
    phase=sys.argv[1]; out=Files(root('-'+phase));check=MacCheckpoint(seconds=870);status='failed'
    try:
        {'declaration':declare,'apply':apply,'validate':validate,'publish':publish,'publish-final':publish}[phase](out,check);status='complete'
    except BaseException:
        out.json('failure.json',{'traceback':traceback.format_exc()},True);raise
    finally:out.close(status)
if __name__=='__main__':main()
