"""Publish the source-backed normalization repair and its mixed full-case result."""
import json,math,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/public-data'),str(ROOT/'models/mini-transformer')]
from metropt_multiday import Files,digest
from verification_records import EvidenceStore
from macos_demand_runtime import MacCheckpoint
from macos_rust_run import source_files,disk_bytes
from rust_r1_publish_preparation import validate_root
from rust_r1_compare import floats
from care_rust_r0_close import verify_evidence
NAMES=['rust-r1-upstream-fixture-20261016','rust-r1-upstream-fixture-20261016-records','rust-r1-upstream-format-20261016','rust-r1-upstream-kernel-20261016-records','rust-r1-upstream-kernel2-20261016-records','rust-r1-upstream-kernel-20261016','rust-r1-upstream-comparison-20261016','rust-r1-upstream-comparison-20261016-records','rust-r1-upstream-comparison2-20261016','rust-r1-upstream-comparison2-20261016-records','rust-r1-norm-repair-declaration-20261016','rust-r1-norm-repair-declaration-20261016-records','rust-r1-tests4-20261016','rust-r1-predict3-20261016-records','rust-r1-burn-predictions3-20261016','rust-r1-compare3-20261016','rust-r1-compare3-20261016-records']
def read(n,f='summary.json'):return json.loads((ROOT/'artifacts'/n/f).read_bytes())
def point(root,case,index):
    folder=ROOT/'artifacts'/root
    ref=root=='rust-r1-python-reference-20261016'
    m=read(root,'fixtures.json' if ref else 'traces-layout.json');raw=(folder/('python-traces.bin' if ref else 'rust-traces.bin')).read_bytes()
    e=next(e for e in m['cases'][case]['traces'] if e['name']=='blocks.1')
    return floats(raw,e)[index]
def main():
    out=Files(ROOT/'artifacts/rust-r1-upstream-results-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        roots=[validate_root(ROOT/'artifacts'/n) for n in NAMES]
        prior=[validate_root(ROOT/'artifacts'/n) for n in ['rust-r1-python-reference-20261016','rust-r1-burn-predictions2-20261016','rust-r1-compare2-20261016','rust-r1-ff-results-20261016']]
        diag=read('rust-r1-upstream-comparison2-20261016');assert diag['candidate_gate_pass'] and diag['attention_failing_elements']==0
        result=read('rust-r1-compare3-20261016');assert result['cases']==7 and result['elements_compared']==389214 and result['failing_elements']==1 and not result['parity_pass']
        entries=read('rust-r1-compare3-20261016','tensor-comparisons.json');failed=[e for e in entries if e['failing_elements']]
        assert len(failed)==1 and failed[0]['case']=='train-last' and failed[0]['tensor']=='blocks.1'
        assert failed[0]['failure_examples'][0]['index']==3450
        q=[e for e in entries if e['tensor']=='quantiles'];nq=[e for e in entries if e['tensor']=='normalized_quantiles']
        assert all(e['failing_elements']==0 for e in q+nq)
        points=[]
        for case,index in [(0,4359),(1,3450)]:
            x=point('rust-r1-python-reference-20261016',case,index);old=point('rust-r1-burn-predictions2-20261016',case,index);new=point('rust-r1-burn-predictions3-20261016',case,index);limit=2e-6+2e-5*abs(x)
            points.append({'case':['train-first','train-last'][case],'index':index,'reference':x,'previous_rust':old,'current_rust':new,'previous_absolute_error':abs(old-x),'current_absolute_error':abs(new-x),'fixed_limit':limit,'current_pass':abs(new-x)<=limit})
        assert points[0]['current_pass'] and not points[1]['current_pass']
        out.json('point-before-after.json',points);out.json('remaining-mismatch.json',failed[0])
        cfgs=[ROOT/'examples/configs'/f for f in ['rust-small-forecaster-r0-20261016.json','rust-small-forecaster-r0-20261016-r0.1.json','care-a-maintenance-20261016-r1.json','rust-r1-build-budget-20261016-r1.json']]
        cfgpins={str(p):digest(p) for p in cfgs};assert cfgpins[str(cfgs[1])]=='bd5c962c711decbad2e590af71ed9474d1f6256351571d3b16a8e3ada047c57a'
        assert digest(ROOT/'Cargo.lock')=='3e839d59923988b78155e1ed785d8f5f56fda9e072a69f64e52ea2e8e96f11e5'
        units={n:read(n,'exit.json') for n in ['rust-r1-upstream-fixture-20261016-records','rust-r1-upstream-kernel2-20261016-records','rust-r1-tests4-20261016','rust-r1-predict3-20261016-records','rust-r1-compare3-20261016-records']}
        for n,e in units.items():
            assert e['elapsed_seconds']<870 and e['returncode']==(1 if 'compare3' in n else 0)
            if 'sampled_group_peak' in e:
                g=e['sampled_group_peak'];assert max(g['monitor_inclusive_footprint'],g['monitor_inclusive_rss'],e['child_wait_peak_rss_bytes'])<2*1024**3
                assert e['sampled_cache_bytes']<1536*1024**2
        for name in ['rust-r1-tests4-20261016','rust-r1-predict3-20261016-records']:
            for p in read(name,'state.json')['source_pins_after']:assert digest(ROOT/p['path'])==p['sha256']
        log=(ROOT/'artifacts/rust-r1-tests4-20261016/stdout.txt').read_text();assert '2 passed; 0 failed' in log and '1 passed; 0 failed' in log
        improvement=1-diag['reciprocal_squared_error_sum']/diag['division_squared_error_sum']
        phase={'scope':'publish one declared general LayerNorm correction and original seven-case confirmation','candidate_gate_pass':True,'attention_stage_comparisons_passed':28,'R1_complete':False,'R1a_tests_passed':3,'R1b_failing_elements':1,'original_failed_point_now_passes':True,'new_failure_case':'train-last/blocks.1/index3450','R2_started':False,'tolerances_unchanged':True,'model_training_or_performance_evaluation':False,'new_full_forward_cases':7,'memory_cap_bytes':2*1024**3,'build_disk_cap_bytes':1536*1024**2,'prior_closed_roots_preserved':True}
        out.json('phase.json',phase);out.json('root-pins.json',roots+prior);out.json('resources.json',units)
        report='docs/results/banto-ai-rust-r1-upstream-order-2026-10-16.md'
        text=f'''# Rust R1 — 正規化・attentionの同一入力診断と7ケース再確認（2026-10-16）

[計画](../research/banto-ai-rust-implementation-plan-2026-10-16.md)に沿って実施。**attentionは同一入力の全28段階で固定許容差内。LayerNormに参照との一般的な演算順の相違を確認し、事前条件を通った修正を一度適用した。元の超過点は通過したが、別の中間値1点が超過し、R1全体は未合格のまま**。最終予測は全7ケースで通過。許容差を変えず、追加算術探索やR2学習へ進まない。

## 入力と演算を分離した診断

保存済みtrain-firstのPython/Rust双方の第2blockから、norm0/1/2の入力各120×64を再構成した。norm1はblock0＋temporal、norm2はさらにvariateを足す。attentionへは保存済みの正規化後入力を直接渡し、正規化差をattention単体の差と混同しない。固定weight/eps/causal mask/full-series maskを使用。

Python native LayerNorm6回とattention4moduleを診断用に実行。Python側の保存stageを全てbytes再現し、Rust側も従来の正規化・attention出力を全てbytes再現した。新しい全model forward/学習/target decodeは診断時0。以後の確認でだけ元の7ケースをRustで一度実行した。

| 同一入力の診断 | 結果 |
| --- | --- |
| norm6組/46,080要素、従来の除算 | 全て許容差内 |
| norm6組/46,080要素、逆標準偏差の乗算 | 全て許容差内 |
| attention4組×7段階 | 28/28通過、超過0 |
| attention段階 | q/k/v、masked logits、softmax、mixed、出力 |
| 時間maskの−∞ | 同じ位置で厳密一致 |

attentionでは重み射影・softmax等のfloat32差は残るが、同一入力での条件は通過した。attentionの式・backend・実装は変更していない。局所比較passを全モデル一致と読み替えない。

## 一般的な修正の根拠と固定条件

[PyTorch v2.14 CPU LayerNorm](https://github.com/pytorch/pytorch/blob/v2.14.0/aten/src/ATen/native/cpu/layer_norm_kernel.cpp)は行ごとに `1/sqrt(var+eps)` を計算し、中心化した値へ掛ける。Rustは中心化値をsqrtで要素ごとに割っていた。数学的には同値でもfloat32の丸め順序が異なる。参照sourceと同一入力診断を根拠に、候補を**逆数乗算の一つだけ**に固定した。

候補の採用条件は実行前phase.jsonに保存した「全6入力で元の中間値許容差内、かつ全6入力合計の参照との二乗誤差が減る」。失敗indexの値では選ばない。従来SSE {diag['division_squared_error_sum']!r}、候補SSE {diag['reciprocal_squared_error_sum']!r}で、合計{100*improvement:.3f}%減り条件を通過した。一部入力では最大誤差が増えており、全要素が改善するという意味ではない。

修正前に別declarationへsource/理由/再確認条件/停止条件を保存。coreの全LayerNorm（final_normを含む）で `centered / sqrt` を `centered * reciprocal(sqrt)` へ変更した。balanced float32 mean/variance、eps、weight、モデル構成、context正規化、attention、R0の許容差は不変。参照値の置換、特定店/発行日/indexだけの処理、float64モデル化は行わない。

## 3テストと固定7ケース

Rustの入力0/欠測・shape、因果query、neutral破損拒否の3テストは全pass。診断exampleを含むall-targetsもbuildされた。保存済みPython参照を再生成せず、train先頭/末尾batch＋zero/constant/floor下/境界/上の7ケースを一度比較した。

| 項目 | 結果 |
| --- | --- |
| case / named tensor | 7 / 161 |
| 比較要素 | 389,214 |
| 超過 | **1**（新しい点） |
| 元単位の最終分位点 | 全6,048要素pass |
| 正規化後の最終分位点 | 全6,048要素pass |
| 元単位最大error/limit | {max(e['max_tolerance_ratio'] for e in q):.9f} |
| 正規化後最大error/limit | {max(e['max_tolerance_ratio'] for e in nq):.9f} |
| finite / 分位点順序 | 全case成立 |
| R1全体 | **fail** |

元のtrain-first/block1 index4359は条件内になった。新たにtrain-last/block1 index3450＝[batch3,series1,token3,dim58]（0始まり）が超過。両点の修正前後はpoint-before-after.jsonへ保存し、元の1点だけを再確認して合格としなかった。

| 点 | 修正前絶対差 | 修正後絶対差 | 固定限界 |
| --- | --- | --- | --- |
'''
        for p in points:text+=f"| {p['case']} index{p['index']} | {p['previous_absolute_error']:.12g} | {p['current_absolute_error']:.12g} | {p['fixed_limit']:.12g} |\n"
        text+='''
新しい点のPython値0.0283811092376709、Rust値0.028383851051330566、差2.741813660e-6>限界2.567622185e-6。原因はまだ同一入力で分離していない。前の点と同じ原因だと断定しない。局所SSEの改善が全層の最大誤差条件を保証しない負の結果として保持する。一般的な修正根拠がある今回のsourceを保存し、最後の1点だけに合わせる再変更や旧版への成績選択rollbackは行わない。

## 実行・失敗・保存

初回診断exampleはgeneric shape配列のSerialize未対応でcompile exit101、局所演算0。shapeをVecへ変える記録形式だけの修正後、fresh command rootでbuild/実行した。初回比較器をcompile成功確認前に起動し、未生成closureの読取りでexit1になった。両失敗とsource/stdio/exit/closureを保持し、成功したkernel後のfresh比較器だけを判定に使用。数値候補の試し直しではない。

| 主実行 | 秒 | 監視込みfootprint B | 監視込みRSS B | exit |
| --- | --- | --- | --- | --- |
'''
        for n,e in units.items():
            if 'sampled_group_peak' in e:
                g=e['sampled_group_peak'];text+=f"| {n} | {e['elapsed_seconds']:.3f} | {g['monitor_inclusive_footprint']:,} | {g['monitor_inclusive_rss']:,} | {e['returncode']} |\n"
        text+=f'''
全単位が親900/子870秒、physical footprintとpeak RSS各2GiB内。Python診断のchild peak RSS {units['rust-r1-upstream-fixture-20261016-records']['child_peak_rss_bytes']:,}B。Rust wrapperは同process groupのCargo/compiler/linkerを監視し、sampling間隔と短命childの捕捉限界を記録。hard OS capではない。build cache+targetの上限1.5GiBは維持し、最終regular file合計{disk_bytes():,}B。旧artifact/EvidenceStore/stdio上限も維持。

主要rootはartifacts/rust-r1-upstream-comparison2-20261016、rust-r1-tests4-20261016、rust-r1-burn-predictions3-20261016、rust-r1-compare3-20261016。新しい全体比較rootは有効な負の結果でcomplete、command rootはexit1/failedのまま。旧closed roots/失敗/参照は保持。全source/stdio/exit/state/closureと文書前後はartifacts/rust-r1-upstream-results-20261016-evidenceへ保存し、全part/SHAを読戻す。

Mac共通CPUのテストと局所診断はpass、元のR1全体gateは未達。Windows native/OS依存suite、製品toolchain1.98.1、下流lockなし解決は未実行/未解決のまま。R2学習、CARE test/需要2015再評価、製品repo編集、push、本番採用は0。

## 次工程の境界

同一入力でのnorm/attention診断と一つの事前固定した一般修正、元7ケースでの確認までを完了し閉鎖した。新しい1点へ同様の局所修正を次々選ぶ探索はしない。次に進める診断は、両train batchと人工入力を含めた全層について、単体丸め誤差と上流累積差を共通の指標で分ける有限設計を先に固定するものとする。特定の1点だけを改善する追加candidateや全体forward反復を許可条件にしない。R1 gateの許容差は維持し、未達の間R2は開始しない。

保全・点検第一、学習を含むRust/bantoの目的、AI本体banto-ai/利用側banto-industrialとdenroku-psi-demoを維持。需要2015停止・調整2014以前・同休業mean28・四季両側非増加・観測のみ/欠測0評価分離、heartbeat PAUSEDは不変。
'''
        changes={report:text}
        h='docs/current-handoff.md'
        lead='同一入力norm6組/attention28段階は固定許容差内。参照CPUと同じ逆標準偏差の乗算へ全LayerNormを一度修正、局所SSE23%減。3テストpass、元の7case全体比較は389,214要素中別の1点超過でR1未合格。'
        changes[h]='## 最新 — 正規化の演算順を修正、元7ケースで別の1点が未達（2026-10-16）\n\n[結果と次工程](results/banto-ai-rust-r1-upstream-order-2026-10-16.md)。'+lead+' 元のtrain-first index4359は通過、新しいtrain-last blocks.1 index3450=[3,1,3,58]で差2.741813660e-6>限界2.567622185e-6。正規化/元単位の最終出力各6,048要素は全pass。許容差変更なし、追加算術探索なし。\n\n初回exampleはgeneric shape Serializeでcompile失敗（演算0）、Vec化後fresh実行。compile成功前に起動した比較器のclosure未生成失敗も保持。判定は成功kernel後のcomparison2だけ。全証跡/文書前後はartifacts/rust-r1-upstream-results-20261016-evidence。\n\n次は両train batchと人工入力の全層で単体丸め/累積差を共通指標で分ける有限診断条件を先に固定し、1点ごとのcandidate探索やfull forward反復をしない。R1未達・R2未開始。メモリ各2GiB/build1.5GiB/時間・保存枠、保全第一/Rust学習目的、需要条件/2015停止・heartbeat PAUSEDを維持。Windows/OS suite未実行、CARE test再評価/下流編集/push0。以下は旧記録。\n\n---\n\n'+(ROOT/h).read_text()
        for name,marker,entry in [('docs/results/README.md','## Rustクレートの移植\n','- [Rust R1の正規化・attention演算順診断](banto-ai-rust-r1-upstream-order-2026-10-16.md) — 一般LN修正の根拠確認、7case再確認で別の1点未達。'),('docs/research/README.md','## 文書\n','- [Rust R1の上流演算順と一般修正](../results/banto-ai-rust-r1-upstream-order-2026-10-16.md) — 同一入力pass、修正後3テストpass/全体gateは別点で未達。')]:
            old=(ROOT/name).read_text();assert marker in old;changes[name]=old.replace(marker,marker+'\n'+entry+'\n',1)
        for name in ['docs/research/banto-ai-rust-implementation-plan-2026-10-16.md','docs/research/rust-small-forecaster-r0-2026-10-16.md']:
            changes[name]=re.sub(r'^状態:.*$','状態: R1a/3テストpass。同一入力norm/attention診断後の一般LN修正を固定7caseで確認、元の点は通過したが別の中間値1点未達でR1未合格。R2未着手。[結果と次工程](../results/banto-ai-rust-r1-upstream-order-2026-10-16.md)。2026-10-16 JST。',(ROOT/name).read_text(),count=1,flags=re.M)
        name='docs/research/research-roadmap.md';changes[name]='## 現在 — R1一般修正を全ケースで確認、1点未達を保存（2026-10-16）\n\n[結果](../results/banto-ai-rust-r1-upstream-order-2026-10-16.md)。'+lead+' 次は全層の単体/累積差を分ける有限設計の固定、1点への算術探索は停止。以下は旧記録。\n\n---\n\n'+(ROOT/name).read_text()
        name='README.md';old=(ROOT/name).read_text();start=old.index('## Rust AIクレートの研究実装')
        changes[name]=old[:start]+'''## Rust AIクレートの研究実装

AI本体は [crates/banto-ai](crates/banto-ai/README.md) に置き、学習・推論・保存再開を共通化する。[実装計画](docs/research/banto-ai-rust-implementation-plan-2026-10-16.md)に沿ってCPU buildと3テストが通過した。同一入力の正規化・attention診断を根拠にLayerNormの演算順をそろえ、固定7ケースを確認。最終予測は許容差内だが、別の中間値1点超過でR1全体は未合格。Rust学習は未開始。[結果と次工程](docs/results/banto-ai-rust-r1-upstream-order-2026-10-16.md)を参照。
'''
        name='crates/banto-ai/README.md';old=(ROOT/name).read_text();start=old.index('Current verification:');end=old.index('\n\nThe pinned',start)
        changes[name]=old[:start]+'''Current verification: locked offline CPU build and all three tests pass on
native Rust 1.95.0/macOS. Same-input normalization and attention diagnostics pass.
LayerNorm now multiplies by one row inverse standard deviation, matching the
reference CPU evaluation order; fixed seven-case confirmation resolves the old
mismatch but reveals one different intermediate element beyond the unchanged
tolerance. Final normalized and physical quantiles pass all seven cases.
R1 as a whole remains failed; training is not started. Preserve all results and
avoid arithmetic searches aimed at individual elements. The build cache/target
ceiling is 1.5 GiB; memory stays at 2 GiB.'''+old[end:]
        sources=list(dict.fromkeys([Path(__file__),*source_files(),*[ROOT/'tools/public-data'/n for n in ['rust_r1_upstream_fixture.py','rust_r1_upstream_compare.py','rust_r1_norm_repair_declare.py','rust_r1_compare.py','care_rust_r0_close.py']],ROOT/'tools/verification_records.py']))
        out.sources(sources);evidence=ROOT/'artifacts/rust-r1-upstream-results-20261016-evidence'
        summary={**phase,'same_input_norm_sse_reduction_fraction':improvement,'points':points,'disk_bytes':disk_bytes()}
        with EvidenceStore(evidence) as store:
            store.write_json('phase',phase);store.write_json('root-pins',roots+prior);store.write_json('summary',summary)
            for i,p in enumerate(sources):store.write_bytes(f'source-{i}',p.read_bytes())
            for i,p in enumerate(cfgs):store.write_bytes(f'fixed-config-{i}',p.read_bytes())
            store.write_json('document-paths',list(changes))
            for i,name in enumerate(changes):
                p=ROOT/name
                if p.exists():store.write_bytes(f'before-{i}',p.read_bytes())
            for name,value in changes.items():(ROOT/name).write_text(value)
            for i,name in enumerate(changes):store.write_bytes(f'after-{i}',(ROOT/name).read_bytes())
            for i,r in enumerate(roots):
                for j,p in enumerate(sorted((ROOT/r['root']).iterdir())):store.write_bytes(f'root-{i}-{j}',p.read_bytes())
            for i,r in enumerate(prior):store.write_bytes(f'old-closure-{i}',(ROOT/r['root']/'root-closed.json').read_bytes())
            # Reconstruct the failed comparator source from its exact recorded two edits;
            # distinguish reconstruction from an at-launch snapshot, which was not saved.
            recovered=(ROOT/'tools/public-data/rust_r1_upstream_compare.py').read_text().replace("artifacts/rust-r1-upstream-comparison2-20261016","artifacts/rust-r1-upstream-comparison-20261016")
            oldphase="'training':False,'full_forward_calls':0,'prior_failure':'first Rust diagnostic did not compile: generic shape array serialization; comparator was started before successful compile and failed missing closure; preserve both; serialization changed to Vec, numerical code unchanged'"
            assert oldphase in recovered;recovered=recovered.replace(oldphase,"'training':False,'full_forward_calls':0")
            store.write_bytes('failed-comparator-reconstructed-source',recovered.encode());store.write_json('reconstruction-note',{'reason':'failed comparator validated missing kernel root before inner source snapshot; source reconstructed by reversing exact two edits, not asserted as an at-launch hash'})
            links=0
            for target in re.findall(r'\]\(([^)]+)\)',text):
                if target.startswith(('http:','https:')):continue
                assert ((ROOT/report).parent/target).exists(),target;links+=1
            for r in roots+prior:assert digest(ROOT/r['root']/'root-closed.json')==r['closure_sha256']
            assert {str(p):digest(p) for p in cfgs}==cfgpins
            store.write_json('readback',{'fixed_configs_and_prior_closures_unchanged':True,'local_links_checked':links})
            store.write_terminal('terminal',{'exit':0,'state':'finite diagnosis/repair/confirmation complete; R1 still failed, R2 not started','resources':check.check()})
        out.json('evidence-readback.json',verify_evidence(evidence,'complete'));out.json('summary.json',{**summary,'resources':check.check()})
        print(json.dumps({'local_diagnosis_pass':True,'tests_passed':3,'R1_complete':False,'remaining_case':'train-last','remaining_index':3450}));status='complete'
    finally:out.close(status)
if __name__=='__main__':main()
