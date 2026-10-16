"""Publish CPU test success and the retained single-element R1 parity failure."""
import json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/public-data'),str(ROOT/'models/mini-transformer')]
from verification_records import EvidenceStore
from metropt_multiday import Files,digest
from macos_demand_runtime import MacCheckpoint
from macos_rust_run import source_files,disk_bytes
from care_rust_r0_close import verify_evidence
from rust_r1_publish_preparation import validate_root

NAMES=['rust-r1-budget-revision-20261016','rust-r1-budget-revision-20261016-records',
       'rust-r1-tests2-20261016','rust-r1-predict-20261016-records','rust-r1-burn-predictions-20261016',
       'rust-r1-compare-20261016','rust-r1-compare-20261016-records',
       'rust-r1-saved-diagnosis-20261016','rust-r1-saved-diagnosis-20261016-records',
       'rust-r1-pairwise-declaration-20261016','rust-r1-pairwise-declaration-20261016-records',
       'rust-r1-pairwise-format-20261016','rust-r1-tests3-20261016',
       'rust-r1-predict2-20261016-records','rust-r1-burn-predictions2-20261016',
       'rust-r1-compare2-20261016','rust-r1-compare2-20261016-records',
       'rust-r1-python-reference-20261016']
def read(name,file='summary.json'):return json.loads((ROOT/'artifacts'/name/file).read_bytes())
def main():
    out=Files(ROOT/'artifacts/rust-r1-results-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        roots=[validate_root(ROOT/'artifacts'/n) for n in NAMES]
        old=read('rust-r1-compare-20261016');new=read('rust-r1-compare2-20261016')
        assert old['failing_elements']==114 and new['failing_elements']==1 and not new['parity_pass']
        assert new['cases']==7 and new['elements_compared']==389214
        entries=read('rust-r1-compare2-20261016','tensor-comparisons.json')
        failed=[e for e in entries if e['failing_elements']];assert len(failed)==1
        failure=failed[0];assert failure['tensor']=='blocks.1' and failure['case']=='train-first'
        assert failure['failure_examples'][0]['index']==4359
        outputs=[e for e in entries if e['tensor'] in ['quantiles','normalized_quantiles']]
        assert all(e['failing_elements']==0 and e['nonfinite']==0 for e in outputs)
        final_q=[e for e in outputs if e['tensor']=='quantiles'];final_n=[e for e in outputs if e['tensor']=='normalized_quantiles']
        unit_names=['rust-r1-tests2-20261016','rust-r1-predict-20261016-records','rust-r1-tests3-20261016','rust-r1-predict2-20261016-records']
        units=[{'root':n,**read(n,'exit.json')} for n in unit_names]
        for u in units:
            assert u['returncode']==0 and u['elapsed_seconds']<870 and u['sampled_cache_bytes']<=1536*1024**2
            assert max(u['sampled_group_peak']['monitor_inclusive_footprint'],u['sampled_group_peak']['monitor_inclusive_rss'],u['child_wait_peak_rss_bytes'])<2*1024**3
        for n in ['rust-r1-tests2-20261016','rust-r1-tests3-20261016']:
            log=(ROOT/'artifacts'/n/'stdout.txt').read_text();assert '2 passed; 0 failed' in log and '1 passed; 0 failed' in log
        for n in ['rust-r1-tests3-20261016','rust-r1-predict2-20261016-records']:
            for pin in read(n,'state.json')['source_pins_after']:assert digest(ROOT/pin['path'])==pin['sha256']
        cfgs=[ROOT/'examples/configs'/n for n in ['rust-small-forecaster-r0-20261016.json','rust-small-forecaster-r0-20261016-r0.1.json','care-a-maintenance-20261016-r1.json','rust-r1-build-budget-20261016-r1.json']]
        cfg_pins={str(p):digest(p) for p in cfgs}
        assert cfg_pins[str(cfgs[1])]=='bd5c962c711decbad2e590af71ed9474d1f6256351571d3b16a8e3ada047c57a'
        meta=read('rust-r1-metadata3-20261016');assert digest(ROOT/'Cargo.lock')==meta['cargo_lock_sha256']
        preserved=[validate_root(ROOT/'artifacts'/n) for n in ['rust-r1-tests-20261016','rust-r1-build-stop-20261016','rust-r1-prepared-20261016','rust-r1-metadata3-20261016']]
        phase={'scope':'publish finite R1 test/parity results; no further forward or arithmetic trial',
               'R1a_CPU_build_tests_pass':True,'R1b_complete':False,'R1_complete':False,'R2_started':False,
               'reason':'one intermediate element remains beyond unchanged R0 tolerance',
               'budget_revision_authorized_by_human':True,'build_disk_cap_bytes':1536*1024**2,
               'memory_cap_bytes':2*1024**3,'scientific_configs_unchanged':True,
               'new_Python_forward_calls':0,'Rust_forward_cases':14,'training':False,
               'CARE_test_or_demand2015_evaluation':False,'downstream_edits':False,'Windows_tested':False}
        out.json('phase.json',phase);out.json('verified-roots.json',roots+preserved)
        out.json('remaining-mismatch.json',failure);out.json('resources.json',units)
        disk=disk_bytes()
        summary={**phase,'tests_passed':3,'comparison_cases':7,'named_tensors_compared':161,
                 'elements_compared':389214,'initial_failing_elements':114,'final_failing_elements':1,
                 'physical_quantiles_elements_passed':sum(e['elements'] for e in final_q),
                 'physical_max_tolerance_ratio':max(e['max_tolerance_ratio'] for e in final_q),
                 'normalized_max_tolerance_ratio':max(e['max_tolerance_ratio'] for e in final_n),
                 'disk_bytes_final':disk,'dependency_lock_unchanged':True,
                 'max_monitored_footprint_bytes':max(u['sampled_group_peak']['monitor_inclusive_footprint'] for u in units),
                 'max_monitored_rss_bytes':max(u['sampled_group_peak']['monitor_inclusive_rss'] for u in units)}
        report='docs/results/banto-ai-rust-r1-tests-parity-2026-10-16.md'
        ex=failure['failure_examples'][0]
        text=f'''# Rust R1 — CPUテスト通過、数値比較は中間値1点で未達（2026-10-16）

[実装計画](../research/banto-ai-rust-implementation-plan-2026-10-16.md)に沿ってR1a/R1bを実行。**CPU buildと3テストは通過。最終予測は7ケースとも許容差内だが、中間値1点が超過しR1全体は未合格**。R2学習へ進まない。保全・点検支援を第一優先とし、banto-ai内で学習・推論・保存再開をRust化する目的は維持する。

## 容量変更と既存成果の保護

人の「容量上限を必要な範囲で見直して…」の指示を受け、[ビルド専用予算](../../examples/configs/rust-r1-build-budget-20261016-r1.json)を実行前に保存。前回の479,959,378B依存cache＋326,020,247B未完targetを維持し、残りの依存・テスト/exampleリンクと一時出力のため、合計上限を768MiBから**1.5GiB**へ変更した。最終regular file合計は{disk:,}B（約{disk/1024**2:.1f}MiB）。この上限分を事前確保したわけではない。

親900秒/子870秒、メモリ各2GiB、jobs1/CPU threads1、通常artifact24file/768MiB・単一32MiB、EvidenceStore16MiB/512file/part256KiBと失敗reserve等は据え置いた。旧source/失敗/closed rootsを保持し、cacheの手動削除・移動、新依存取得、push、下流repo変更なし。offline/locked/native Rust1.95.0で実行。Cargo.lockのSHAは既存inventoryと一致。

## ビルドとテスト

`cargo test -p banto-ai --locked --offline --all-targets --features reference-tests -- --test-threads=1` を実行し、修正後も3テスト成功。

| テスト | 確認内容 |
| --- | --- |
| input | 観測0を保持、非有限/欠測・batch/shape不正を拒否 |
| temporal_query | 将来queryの変更が過去token出力へ影響しない |
| neutral_integrity | 固定参照を読込み、不正hash/shape/重複/offset overflow/NaN/noncausal mask/末尾byteを拒否 |

predict exampleもbuild・link後に実行。crateはprepared finite contextだけを受け、実タグのquality/時刻や利用可能時刻の検査は将来adapter/consumerの責務として残る。loaderはpinned CARE neutral参照用で、製品package/optimizer再開は未実装。TensorData::to_vecのdeprecated警告が1種あり、エラーではない。

## 固定した7ケースの比較

既存fold0 modelとtrain先頭/末尾各B8、人工zero/constant/floor-below/equal/aboveを使用。Python参照は再生成せず、test/validation/calibration/truthは開かない。新Rust forwardは修正前後7ずつ、計14ケース。モデル学習・性能再評価は0。

| 判定 | 修正前 | ペア加算への修正後 |
| --- | --- | --- |
| case / named tensor比較 | 7 / 161 | 7 / 161 |
| 全要素 | 389,214 | 389,214 |
| 許容差超過 | 114 | **1** |
| 正規化後の最終分位点 | 1点超過 | 全6,048要素pass |
| 元単位の最終分位点 | 全6,048要素pass | 全6,048要素pass |
| 全体gate | fail | **fail** |

元単位出力の最大error/許容限界比は{summary['physical_max_tolerance_ratio']:.9f}、正規化後出力は{summary['normalized_max_tolerance_ratio']:.9f}。全出力finite・分位点順序成立。R0の中間値条件 `abs(diff)<=2e-6+2e-5*abs(ref)` と元単位条件は変更していない。合格した最終出力だけを根拠に中間値gateを外さない。q50/context_centerを需要平均として使わない。

## 数値修正の根拠と残差

初回はtrain2caseのblock0出力から超過し、人工5caseは通過。保存値だけの診断で、Flex scalar sumの逐次float32加算によるcontext標準偏差の誤差を確認した。独立した高精度momentをfloat32へ丸めた値に対するscale絶対誤差の総和は、Python参照0、旧Rust7.691141e-5、ペア加算3.352761e-8。これは丸め誤差の一因を支持するが、残り全ての差の単独原因という証明ではない。

原因・修正仮説・停止条件を先に保存し、context128とLayerNorm64のmean/varianceをbalanced pairwise float32加算へ変更した。重み・dtype・分散の式・eps・モデル構成・許容差は不変、Burn tensor操作のままでhost処理へ迂回せず、将来のgradient経路を残した。ただしbackward一致はR2で未検証。

残る超過はtrain-firstの `blocks.1` shape[8,3,5,64]、flatten index4359＝[batch4,series1,token3,dim7]（0始まり）。

| 値 | 数値 |
| --- | --- |
| Python | {ex['reference']!r} |
| Rust | {ex['rust']!r} |
| 絶対差 | {ex['absolute_error']!r} |
| 固定許容限界 | {ex['limit']!r} |
| 差/限界 | {failure['max_tolerance_ratio']:.9f} |

このcaseで最初に条件を超えるのは第2blockの出力段階。先行する保存済みLayerNorm/attention/GELU出力は条件内だが、途中の差が累積し得る。線形演算・残差加算のどちらが決定的かは現時点では未分離であり、特定backendの不具合や物理的意味を断定しない。事前宣言どおり、残差に合わせる追加算術探索や許容差拡大は行わず終了した。

## 資源・OS・保存

| 実行単位 | 秒 | 監視込みfootprint最大B | 監視込みRSS最大B | exit |
| --- | --- | --- | --- | --- |
'''
        for u in units:
            p=u['sampled_group_peak'];text+=f"| {u['root']} | {u['elapsed_seconds']:.3f} | {p['monitor_inclusive_footprint']:,} | {p['monitor_inclusive_rss']:,} | 0 |\n"
        text+='''
全単位で子870秒と各2GiB内。Rust wrapperはCargo/compiler/linker/build-scriptの同process groupを監視し、測定間隔とshort-lived childの捕捉限界を保存。samplingでありhard OS capではない。Mac共通CPU build/テストpass、R1bの全体一致fail。Windows native・OS依存包括suiteと製品側toolchain1.98.1は未実行。下流のlockなし解決に残るyanked任意依存の問題も未解決で、配布成立とはしない。

主要保存先は artifacts/rust-r1-tests3-20261016、rust-r1-burn-predictions2-20261016、rust-r1-compare2-20261016。修正前のcompareは有効な負の結果としてcomplete、対応するcommand記録はexit1/failedを保つ。旧容量超過もfailedのまま。全source/stdio/exit/state/closure、文書前後、全比較と残差、元参照のpinは artifacts/rust-r1-results-20261016-evidence に保存。

次の工程は**R1bの残差1点の演算切り分け**。先に固定する診断は保存済み第2block入力/重みを用い、共通入力でff.2線形出力と残差和を別々に比較し、上流誤差の伝播と演算自身の丸めを区別するものとする。変更理由が得られるまで新しいfull forward/再試行・学習へ進まない。R1a済みをもってR2/CARE再学習/製品利用へ移らない。

保全第一・学習を含むRust移植、AI本体banto-ai/利用側banto-industrialとdenroku-psi-demoの責務を維持。需要2015停止・調整2014以前・同休業mean28・四季両側非増加・観測のみ/欠測0評価分離、heartbeat PAUSEDも不変。
'''
        changes={report:text}
        h='docs/current-handoff.md'
        lead='Rust CPU build・3テストpass。固定7ケース/389,214要素の比較は修正前114超過→修正後1超過、R1b/R1全体は未合格。正規化/元単位の最終予測各6,048要素は全pass。'
        changes[h]='## 最新 — Rust R1a通過、R1bは中間値1点が残る（2026-10-16）\n\n[結果と次工程](results/banto-ai-rust-r1-tests-parity-2026-10-16.md)。'+lead+' 人の指示でbuild cache+targetだけ768MiB→1.5GiBへ変更を事前保存、最終約879MiB。メモリ各2GiB/時間/成果物保存上限は維持。旧失敗・参照・closed roots不変。\n\n保存値診断でscalar逐次加算のmoment誤差を確認し、context/LayerNormの加算をbalanced f32へ一度修正。残るtrain-first blocks.1 index4359=[4,1,3,7]は絶対差2.294778824e-6>限界2.112383962e-6。許容差を変えず負の結果で閉鎖。次は同一第2block入力でff.2と残差和を分ける有限診断を先に固定し、追加full forward/算術探索をしない。\n\nR1a済み/R1未完・R2学習0。CARE test/需要2015再評価0、下流編集/push0、Windows/OS依存suite未実行。AI本体banto-ai、保全第一・学習Rustの目的、需要条件、heartbeat PAUSED維持。全source/stdio/exit/state/closure/文書前後はartifacts/rust-r1-results-20261016-evidence。以下は旧記録。\n\n---\n\n'+(ROOT/h).read_text()
        for name,marker,entry in [
            ('docs/results/README.md','## Rustクレートの移植\n','- [Rust R1 CPUテストと数値比較](banto-ai-rust-r1-tests-parity-2026-10-16.md) — 3テストpass、最終予測pass、中間値1点超過でR1未合格。'),
            ('docs/research/README.md','## 文書\n','- [Rust R1の実行結果と残差切り分け](../results/banto-ai-rust-r1-tests-parity-2026-10-16.md) — build枠1.5GiB、CPUテストpass、数値一致gateは1点未達。')]:
            oldtext=(ROOT/name).read_text();assert marker in oldtext
            changes[name]=oldtext.replace(marker,marker+'\n'+entry+'\n',1)
        for name in ['docs/research/banto-ai-rust-implementation-plan-2026-10-16.md','docs/research/rust-small-forecaster-r0-2026-10-16.md']:
            changes[name]=re.sub(r'^状態:.*$', '状態: R1a CPU build/3テスト通過。R1bは最終予測7case通過、中間値1点超過のためR1未合格、R2未着手。[結果と次工程](../results/banto-ai-rust-r1-tests-parity-2026-10-16.md)を参照。2026-10-16 JST。',(ROOT/name).read_text(),count=1,flags=re.M)
        name='docs/research/research-roadmap.md'
        changes[name]='## 現在 — Rust R1a通過、残る中間値1点を切り分け（2026-10-16）\n\n[結果](../results/banto-ai-rust-r1-tests-parity-2026-10-16.md)。'+lead+' R1bの残差原因を切り分けるまでR2は開始しない。build専用枠1.5GiB、各メモリ2GiB・保存枠・R0許容差は維持。以下は旧記録。\n\n---\n\n'+(ROOT/name).read_text()
        name='README.md';oldtext=(ROOT/name).read_text();start=oldtext.index('## Rust AIクレートの研究実装')
        changes[name]=oldtext[:start]+'''## Rust AIクレートの研究実装

AI本体は [crates/banto-ai](crates/banto-ai/README.md) に置き、学習・推論・保存再開を共通化する。[実装計画](docs/research/banto-ai-rust-implementation-plan-2026-10-16.md)に沿ってCPU buildと3テストが通過した。Pythonとの固定7ケース比較では最終予測は許容差内だが、中間値1点超過でR1全体は未合格。学習のRust実装は次工程。[結果と残差の切り分け](docs/results/banto-ai-rust-r1-tests-parity-2026-10-16.md)を参照。
'''
        name='crates/banto-ai/README.md';oldtext=(ROOT/name).read_text();start=oldtext.index('Current verification:');end=oldtext.index('\n\nThe pinned',start)
        changes[name]=oldtext[:start]+'''Current verification: locked offline CPU build and all three tests pass on
native Rust 1.95.0/macOS. Seven fixed Python comparison cases pass for the final
normalized and physical quantiles, but one intermediate element remains beyond
the unchanged tolerance. R1 as a whole has not passed; R2 training is not started.
Balanced f32 reductions reduce the earlier 114 mismatches to one. Preserve both
results and isolate the remaining arithmetic difference before further trials.
The user-authorized build cache/target ceiling is 1.5 GiB; memory stays at 2 GiB.'''+oldtext[end:]
        sources=list(dict.fromkeys([Path(__file__),*source_files(),ROOT/'tools/verification_records.py',*[ROOT/'tools/public-data'/n for n in ['rust_r1_budget_revision.py','rust_r1_saved_diagnosis.py','rust_r1_pairwise_declare.py','rust_r1_compare.py','care_rust_r0_close.py']]]))
        out.sources(sources)
        evidence=ROOT/'artifacts/rust-r1-results-20261016-evidence'
        with EvidenceStore(evidence) as store:
            store.write_json('phase',phase);store.write_json('root-pins',roots+preserved);store.write_json('summary',summary)
            for i,p in enumerate(sources):store.write_bytes(f'source-{i}',p.read_bytes())
            for i,p in enumerate(cfgs):store.write_bytes(f'config-{i}',p.read_bytes())
            for i,name in enumerate(changes):
                p=ROOT/name
                if p.exists():store.write_bytes(f'before-{i}',p.read_bytes())
            store.write_json('document-paths',list(changes))
            for name,value in changes.items():(ROOT/name).write_text(value)
            for i,name in enumerate(changes):store.write_bytes(f'after-{i}',(ROOT/name).read_bytes())
            for i,r in enumerate(roots):
                for j,p in enumerate(sorted((ROOT/r['root']).iterdir())):store.write_bytes(f'root-{i}-{j}',p.read_bytes())
            for i,r in enumerate(preserved):store.write_bytes(f'prior-closure-{i}',(ROOT/r['root']/'root-closed.json').read_bytes())
            for i,name in enumerate(['active-dependencies.json','active-license-documents.zip']):store.write_bytes(f'license-{i}',(ROOT/'artifacts/rust-r1-metadata3-20261016'/name).read_bytes())
            links=0
            for name in [report,'crates/banto-ai/README.md']:
                for target in re.findall(r'\]\(([^)]+)\)',(ROOT/name).read_text()):
                    if target.startswith(('http:','https:','#')):continue
                    assert ((ROOT/name).parent/target).exists(),(name,target)
                    links+=1
            assert {str(p):digest(p) for p in cfgs}==cfg_pins
            for r in roots+preserved:assert digest(ROOT/r['root']/'root-closed.json')==r['closure_sha256']
            store.write_json('readback',{'all_original_closures_unchanged':True,'fixed_configs_unchanged':True,'new_report_links_checked':links})
            store.write_terminal('terminal',{'exit':0,'state':'R1a passed; R1b negative result preserved; no R2','resources':check.check()})
        out.json('evidence-readback.json',verify_evidence(evidence,'complete'))
        out.json('summary.json',{**summary,'resources':check.check()});print(json.dumps(summary));status='complete'
    finally:out.close(status)
if __name__=='__main__':main()
