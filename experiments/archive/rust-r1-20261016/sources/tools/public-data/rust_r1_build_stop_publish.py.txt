"""Preserve bounded R1 build failure and publish the remaining prerequisite."""
import json, os, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'tools'), str(ROOT/'tools/public-data'), str(ROOT/'models/mini-transformer')]
from verification_records import EvidenceStore
from metropt_multiday import Files, digest
from macos_demand_runtime import MacCheckpoint
from macos_rust_run import source_files
from care_rust_r0_close import verify_evidence
from rust_r1_publish_preparation import validate_root

def inventory(folder):
    groups = {}; count = 0
    for base, dirs, names in os.walk(folder):
        for name in names:
            p = Path(base)/name
            if not p.is_file() or p.is_symlink(): continue
            size = p.stat().st_size; count += 1
            rel = p.relative_to(folder)
            key = '/'.join(rel.parts[:2]) if len(rel.parts)>2 else rel.parts[0]
            groups[key] = groups.get(key, 0)+size
    return {'path': str(folder.relative_to(ROOT)), 'logical_bytes': sum(groups.values()), 'files': count, 'groups': groups}

def main():
    out = Files(ROOT/'artifacts/rust-r1-build-stop-20261016'); status = 'failed'; check = MacCheckpoint(seconds=870)
    try:
        roots = [validate_root(ROOT/'artifacts'/n) for n in ['rust-r1-compiler-ready-20261016','rust-r1-tests-20261016','rust-r1-python-reference-20261016']]
        run = ROOT/'artifacts/rust-r1-tests-20261016'
        result = json.loads((run/'exit.json').read_bytes())
        failure = json.loads((run/'failure.json').read_bytes())
        assert roots[0]['status']=='complete' and roots[1]['status']=='failed'
        assert 'build/dependency cache disk cap' in failure['traceback'] and result['returncode']==-15
        assert result['sampled_cache_bytes']>768*1024**2
        pins = json.loads((run/'state.json').read_bytes())['source_pins_after']
        for pin in pins: assert digest(ROOT/pin['path'])==pin['sha256']
        phase = {'scope':'record failed R1 build; no retry, inference or training', 'human_confirmed_Xcode_license':True,
                 'clang_preflight_pass':True, 'R1_complete':False, 'R2_started':False,
                 'reason':'declared combined dependency/build cache disk cap exceeded', 'budget_increased':False,
                 'cache_deleted_or_moved':False, 'prior_closed_roots_preserved':True}
        out.json('phase.json', phase)
        inv = [inventory(ROOT/'environments/rust-cpu/cargo-home'), inventory(ROOT/'target')]
        disk = sum(x['logical_bytes'] for x in inv)
        out.json('disk-inventory.json', {'entries':inv, 'combined_logical_bytes':disk, 'cap_bytes':768*1024**2,
                 'measurement':'post-stop regular file logical lengths; distinct from allocated du sizes'})
        cfgs = [ROOT/'examples/configs'/n for n in ['rust-small-forecaster-r0-20261016.json','rust-small-forecaster-r0-20261016-r0.1.json','care-a-maintenance-20261016-r1.json']]
        cfg_pins = {str(p):digest(p) for p in cfgs}
        report = 'docs/results/banto-ai-rust-r1-build-stop-2026-10-16.md'
        ex = result['sampled_group_peak']
        text = f'''# Rust R1 — Xcode確認通過、ビルド容量上限による停止（2026-10-16）

計画ID BANTO-AI-RUST-PLAN-20261016-v1のR1a/R1bに沿って再開した。人がXcode利用規約の確認・同意完了を連絡し、fresh clang起動確認はexit0。続くCPUビルドは**依存キャッシュとtargetの合計768MiB上限で停止**した。R1未完、Rustのテスト実行・推論の数値一致は未確認。

## 実行結果

| 項目 | 結果 |
| --- | --- |
| clang --version | exit0、artifacts/rust-r1-compiler-ready-20261016 |
| cargo test --locked --offline --all-targets --features reference-tests | process groupをSIGTERM、returncode -15、テスト実行前 |
| 経過 | {result['elapsed_seconds']:.3f}秒、子870秒以内 |
| 停止時の監視disk値 | {result['sampled_cache_bytes']:,}B、上限805,306,368B |
| 停止後のregular file合計 | {disk:,}B（内訳はdisk-inventory.json） |
| 監視込みphysical footprint最大 | {ex['monitor_inclusive_footprint']:,}B、2GiB以内 |
| 監視込み同時RSS最大 | {ex['monitor_inclusive_rss']:,}B、2GiB以内 |
| waitで得た子peak RSS | {result['child_wait_peak_rss_bytes']:,}B、2GiB以内 |
| 監視 | {result['sample_count']:,} sample、最大間隔{result['largest_interval_seconds']:.6f}秒、同時最大{ex['processes']}process |

最終stderrはBurn関連ライブラリのコンパイル中。banto-aiの型検査・テスト成功を示す出力はない。資源監視はsamplingでありhard OS capではなく、短命processの捕捉限界はexit.jsonのまま。停止理由はXcode規約やメモリではなくdisk予算である。OSの空き容量不足という診断でもない。

コマンド、全上限内stdio、source snapshot、source pins、exit/resource/state/failure/closureはartifacts/rust-r1-tests-20261016へ保存した。開始前と停止後のsource/lockは同じ。失敗rootはfailedのまま保持。既存キャッシュ・target・closed rootsの削除/移動、上限の拡大、backend変更は実施していない。

## 残る工程と再開条件

ビルド用cache/targetの容量条件を具体的に見直してから再開する。通常artifact24file/768MiB・単一32MiB、EvidenceStore16MiB等の保存上限とビルドキャッシュ枠は別に扱い、変更が必要なら理由と新上限を先に記録する。現時点では上限引上げは未承認・未実施。現在のcache/targetは停止後も残るため、同じ条件の再試行はしない。完了に必要な最終容量は未確定で、今回の超過値だけを完成容量と見積もらない。

次はfresh rootでcargo test→固定predict example→独立比較器の順。[準備報告](banto-ai-rust-r1-preparation-2026-10-16.md)の7ケースと[R0許容差](../research/rust-small-forecaster-r0-2026-10-16.md)を維持する。Python参照は再生成しない。R2学習/保存再開はR1通過後に別fixtureを固定して進める。

Mac共通経路はcompiler起動のみpass、Rust coreは未検証。Windows native・OS依存包括suiteは未実行。CARE test/需要2015再評価、学習、下流repo編集、push、本番採用は0。AI実装はbanto-ai、banto-industrialとdenroku-psi-demoは利用側。保全・点検を第一優先とし、学習を含むRust移植の目的を維持する。需要2014以前調整/同休業mean28/四季両側非増加/観測のみと欠測0分離、heartbeat PAUSEDも維持。

文書変更前後・固定設定・全実行記録・容量内訳の保存先はartifacts/rust-r1-build-stop-20261016-evidence。過去の準備報告のXcode待ち記述は履歴とし、本報告を現状とする。失敗を成功へ変更していない。
'''
        short = 'Xcode確認通過。R1 CPU buildがcache+target合計768MiB上限で停止、テスト/数値比較未確認。'
        changes = {report:text}
        h = 'docs/current-handoff.md'
        changes[h] = f'## 最新 — Rust R1、Xcode解消・ビルド容量上限で停止（2026-10-16）\n\n[結果と再開条件](results/banto-ai-rust-r1-build-stop-2026-10-16.md)。{short} 274.302秒、監視disk805,979,625B>805,306,368BによりSIGTERM/-15、失敗source/stdio/exit/state/closureを保持。監視込みfootprint922,044,888B/RSS690,470,912Bは各2GiB内。容量枠の見直しが次の前提。同条件retry、cache削除/移動、上限引上げは行わない。\n\n固定7ケース/Python参照/R0許容差は不変。R1未完・R2学習0、CARE test/需要2015再評価0、下流編集/push0、Windows native/OS依存suite未実行。AIはbanto-ai、保全第一/学習を含むRustの目的と需要条件・heartbeat PAUSED維持。文書前後/全記録/容量内訳はartifacts/rust-r1-build-stop-20261016-evidence。以下は旧記録。\n\n---\n\n'+(ROOT/h).read_text()
        for name,marker,entry in [
            ('docs/results/README.md','## Rustクレートの移植\n',f'- [Rust R1のビルド容量上限停止](banto-ai-rust-r1-build-stop-2026-10-16.md) — {short}'),
            ('docs/research/README.md','## 文書\n',f'- [Rust R1の現状と再開条件](../results/banto-ai-rust-r1-build-stop-2026-10-16.md) — {short}')]:
            old=(ROOT/name).read_text(); assert marker in old
            changes[name]=old.replace(marker,marker+'\n'+entry+'\n',1)
        for name in ['docs/research/banto-ai-rust-implementation-plan-2026-10-16.md','docs/research/rust-small-forecaster-r0-2026-10-16.md']:
            old=(ROOT/name).read_text()
            changes[name]=re.sub(r'^状態:.*$',f'状態: {short} R1未完、R2未着手。[停止結果と再開条件](../results/banto-ai-rust-r1-build-stop-2026-10-16.md)を参照。2026-10-16 JST。',old,count=1,flags=re.M)
        road='docs/research/research-roadmap.md'
        changes[road]='## 現在 — Rust R1のビルド容量条件見直し（2026-10-16）\n\n[停止結果と再開条件](../results/banto-ai-rust-r1-build-stop-2026-10-16.md)。'+short+' 固定参照/R0許容差は維持、R2は未開始。同条件retryや容量拡張は未実施。以下は旧記録。\n\n---\n\n'+(ROOT/road).read_text()
        name='README.md'
        changes[name]=(ROOT/name).read_text().replace('現在はソース・依存・Python参照まで準備し、Xcode利用規約の設定待ちでRust build/テスト/数値一致は未確認。','Xcode確認後にCPU buildを再開したが、cache+target合計768MiB上限で停止。テスト/数値一致は未確認。[停止結果と再開条件](docs/results/banto-ai-rust-r1-build-stop-2026-10-16.md)を参照。',1)
        name='crates/banto-ai/README.md'
        old=(ROOT/name).read_text()
        start=old.index('Current verification:'); end=old.index('\n\nThe pinned',start)
        changes[name]=old[:start]+'Current verification: rustfmt parsing and the post-license clang preflight pass.\nThe first CPU build was terminated by the declared combined Cargo cache and\ntarget disk cap (768 MiB), before tests ran. Type checking, tests and numerical\nparity remain unverified. Preserve the failed run; revise the build capacity\ncondition before retrying.'+old[end:]
        sources=list(dict.fromkeys([Path(__file__),*source_files(),ROOT/'tools/verification_records.py',ROOT/'tools/public-data/care_rust_r0_close.py']))
        out.sources(sources)
        evidence=ROOT/'artifacts/rust-r1-build-stop-20261016-evidence'
        with EvidenceStore(evidence) as store:
            store.write_json('phase',phase); store.write_json('roots',roots)
            store.write_json('disk-inventory',{'entries':inv,'combined_bytes':disk})
            for i,p in enumerate(sources): store.write_bytes(f'source-{i}',p.read_bytes())
            for i,p in enumerate(cfgs): store.write_bytes(f'config-{i}',p.read_bytes())
            before=[]
            for i,name in enumerate(changes):
                p=ROOT/name
                if p.exists():store.write_bytes(f'before-{i}',p.read_bytes()); before.append({'path':name,'sha256':digest(p)})
                else:before.append({'path':name,'absent':True})
            store.write_json('before-index',before)
            for name,value in changes.items():(ROOT/name).write_text(value)
            for i,name in enumerate(changes):store.write_bytes(f'after-{i}',(ROOT/name).read_bytes())
            for i,r in enumerate(roots):
                folder=ROOT/r['root']
                for j,p in enumerate(sorted(folder.iterdir())):store.write_bytes(f'root-{i}-{j}',p.read_bytes())
                assert digest(folder/'root-closed.json')==r['closure_sha256']
            assert {str(p):digest(p) for p in cfgs}==cfg_pins
            links=0
            for name in [report, 'crates/banto-ai/README.md']:
                for target in re.findall(r'\]\(([^)]+)\)',(ROOT/name).read_text()):
                    if target.startswith(('http:','https:','#','app:','codex:')):continue
                    target=target.split('#')[0]; target=re.sub(r':\d+$','',target)
                    assert ((ROOT/name).parent/target).exists(),(name,target)
                    links+=1
            summary={**phase,'root_readback_pass':True,'local_links_checked':links,'fixed_configs_unchanged':True,
                     'source_unchanged_during_build':True,'disk_bytes_after_stop':disk,'resources':check.check()}
            store.write_json('summary',summary); store.write_terminal('terminal',{'exit':0,'state':'R1 incomplete; build disk prerequisite','resources':check.check()})
        out.json('evidence-readback.json',verify_evidence(evidence,'complete'))
        out.json('summary.json',summary); print(json.dumps(summary)); status='complete'
    finally:out.close(status)
if __name__=='__main__':main()
