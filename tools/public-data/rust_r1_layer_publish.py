"""Close the finite all-layer audit, preserving the original failed R1 gate."""
import json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/public-data'),str(ROOT/'models/mini-transformer')]
from metropt_multiday import Files,digest
from verification_records import EvidenceStore
from macos_demand_runtime import MacCheckpoint
from macos_rust_run import source_files,disk_bytes
from rust_r1_publish_preparation import validate_root
from care_rust_r0_close import verify_evidence
NAMES=['rust-r1-layer-fixture-20261016','rust-r1-layer-fixture-20261016-records','rust-r1-layer-fixture2-20261016','rust-r1-layer-fixture2-20261016-records','rust-r1-layer-format-20261016','rust-r1-layer-kernel-20261016','rust-r1-layer-kernel-20261016-records','rust-r1-layer-comparison-20261016','rust-r1-layer-comparison-20261016-records']
def read(n,f='summary.json'):return json.loads((ROOT/'artifacts'/n/f).read_bytes())
def main():
    out=Files(ROOT/'artifacts/rust-r1-layer-results-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        roots=[validate_root(ROOT/'artifacts'/n) for n in NAMES]
        old=[validate_root(ROOT/'artifacts'/n) for n in ['rust-r1-python-reference-20261016','rust-r1-burn-predictions3-20261016','rust-r1-compare3-20261016','rust-r1-upstream-results-20261016']]
        s=read('rust-r1-layer-comparison-20261016');assert s['diagnosis_complete'] and s['node_comparisons']==385 and s['local_failing_elements']==0 and s['total_failing_elements']==1 and s['signed_decomposition_max_residual']==0
        assert s['reference_saved_anchors_byte_exact']==s['rust_saved_anchors_byte_exact']==161
        cases=read('rust-r1-layer-comparison-20261016','case-comparisons.json');families=read('rust-r1-layer-comparison-20261016','family-comparisons.json')
        failures=read('rust-r1-layer-comparison-20261016','original-gate-failures.json');assert len(failures)==1
        fail=failures[0];assert fail['case']=='train-last' and fail['node']=='blocks.1' and fail['failure_examples'][0]['index']==3450
        fp=fail['failure_examples'][0];assert fp['local']==0 and fp['total']==fp['propagated']
        cfgs=[ROOT/'examples/configs'/n for n in ['rust-small-forecaster-r0-20261016.json','rust-small-forecaster-r0-20261016-r0.1.json','care-a-maintenance-20261016-r1.json','rust-r1-build-budget-20261016-r1.json','rust-r1-all-layer-audit-20261016.json']]
        pins={str(p):digest(p) for p in cfgs};contract=json.loads(cfgs[-1].read_bytes())
        assert digest(ROOT/'crates/banto-ai/src/model.rs')==contract['source_model_sha256']
        assert pins[str(cfgs[1])]=='bd5c962c711decbad2e590af71ed9474d1f6256351571d3b16a8e3ada047c57a'
        assert digest(ROOT/'Cargo.lock')=='3e839d59923988b78155e1ed785d8f5f56fda9e072a69f64e52ea2e8e96f11e5'
        units={n:read(n,'exit.json') for n in ['rust-r1-layer-fixture-20261016-records','rust-r1-layer-fixture2-20261016-records','rust-r1-layer-format-20261016','rust-r1-layer-kernel-20261016-records','rust-r1-layer-comparison-20261016-records']}
        for n,e in units.items():
            assert e['elapsed_seconds']<870 and e['returncode']==(1 if n=='rust-r1-layer-fixture-20261016-records' else 0)
            if 'sampled_group_peak' in e:
                g=e['sampled_group_peak'];assert max(g['monitor_inclusive_footprint'],g['monitor_inclusive_rss'],e['child_wait_peak_rss_bytes'])<2*1024**3 and e['sampled_cache_bytes']<1536*1024**2
            else:assert e['child_peak_rss_bytes']<2*1024**3 and max(e['sampled_child_peak'].values())<2*1024**3
        phase={'scope':'publish closed all-layer diagnostic; no model change or new candidate','diagnosis_complete':True,'R1_complete':False,'R2_started':False,'model_candidates_tried':0,'core_unchanged':True,'original_R0_tolerance_unchanged':True,'same_input_local_failures':0,'cumulative_failures':1,'memory_cap_bytes':2*1024**3,'build_cache_cap_bytes':1536*1024**2,'CARE_or_demand2015_evaluation':False,'training':False}
        out.json('phase.json',phase);out.json('root-pins.json',roots+old);out.json('resources.json',units);out.json('remaining-point.json',fp)
        report='docs/results/banto-ai-rust-r1-all-layer-audit-2026-10-16.md'
        text=f'''# Rust R1 — 全55箇所・7ケースの局所差と累積差の診断（2026-10-16）

[実装計画](../research/banto-ai-rust-implementation-plan-2026-10-16.md)に沿い、[診断条件](../../examples/configs/rust-r1-all-layer-audit-20261016.json)を数量計算前に固定して実行した。**同一入力での局所的な実装差は全385比較で固定許容差内。上流の差を引き継いだ結果は、従来と同じtrain-last/block1の1点が超過した**。1点向けの修正や算術候補選択は行わず、core/weight/許容差は不変。診断は完了、R1全体は未合格のまま。

## 固定条件と分解の意味

対象は両train batch＋人工zero/constant/floor-below/equal/aboveの固定7ケース、各55箇所。context平均/尺度/正規化、patch/tokens、2blockの全LayerNorm、時間・系列attentionのq/k/v線形射影/logits/softmax/mixing/出力、3残差和、FF線形/GELU/線形、final_norm/head、分位点組立と元単位復元を含む。LayerNormやstd/floor等は一つのkernel境界であり、その内部の全CPU命令を個別に分けたものではない。

各箇所で、Pythonの自経路入力にPythonを適用したPP、Rustの自経路入力にRustを適用したRR、Pythonの入力を同じ形・bytesでRustへ渡したRPを保存した。q/k/vは同じtranspose配置を再構成する。

| 分解 | 定義 |
| --- | --- |
| 同一入力の局所差 | RP − PP |
| 上流から伝わる差 | RR − RP |
| 合計差 | RR − PP |

局所差にはfloat32の丸め、数学関数の近似、kernel実装差やlayoutの影響が含まれ得る。「純粋な丸め誤差だけ」と証明した解析的上限ではない。上流差も微分/Jacobian近似ではなく、同じRust演算を実際の2種類の入力で評価した差である。符号付き分解を保存float32からfloat64で集計し、全有限要素で**合計＝局所＋上流が厳密成立**した。絶対誤差の和には相殺があるため、各L1を足せば合計L1になるとはしない。

R0の中間値条件2e-6＋2e-5×abs(PP)、元単位quantile条件1e-4×T32＋2e-5×abs(PP−context_center)は変更していない。追加したprimitive内部比較は診断指標であり、元のR1 gateへ新条件を加えたり、既存条件を外したりしていない。

## 再現・来歴の条件

既存の23 named outputs×7ケース＝161箇所について、Python・Rustの自経路再生がそれぞれ保存済み成果とbytes一致したことを確認してから分解を解釈した。参照Pythonの保存7ケースと現行Rust predictions3を変更せず、モデル・profile・信号順・入力を同じhashで固定した。

初回の診断用Python再生は、plain tensorの関数呼出しと既定grad modeを用い、zero/blocks.0.variateの厳密再現条件に失敗した。そのrootと全記録をfailedのまま保持。診断だけを元のSmallForecaster nn module/Parameterとno_gradにそろえ、fresh rootで全161箇所を再現した。複数の実行条件を一緒にそろえたため、そのうち一つだけが原因とは断定しない。失敗した再生を元のモデル誤差に混ぜず、数値候補や許容差の変更も行っていない。

成功経路はPython参照診断再生7回、Rust診断再生7回と385箇所の独立した同一入力評価。これは新しいモデル候補のfull確認ではなく、保存値を再現する有限診断である。初回失敗で実行した途中の再生も記録に残る。学習/backward/optimizer、target/CARE test/truth、需要2015の再評価は0。

## 全ケースの結果

| 項目 | 結果 |
| --- | --- |
| ケース / 箇所 / 比較 | 7 / 55 / 385 |
| 診断要素 | {s['primitive_elements']:,} |
| 有限要素の分解確認 | {s['primitive_elements']-s['mask_identity_values']:,}、分解残差0 |
| −∞ causal mask | {s['mask_identity_values']:,}値で厳密一致、NaN/予期しない∞なし |
| 同一入力局所差の超過 | **0要素 / 0箇所** |
| 累積差の超過 | **1要素 / 1箇所** |
| 元のR1比較対象 | 389,214要素中1超過、従来結果と一致 |
| Python / Rustの保存出力anchor | 各161箇所でbytes一致 |
| モデル修正・候補探索 | 0 |

| ケース | 局所差の超過 | 累積差の超過 |
| --- | --- | --- |
'''
        for row in cases:text+=f"| {row['case']} | {row['primitive_local_failing_elements']} | {row['primitive_total_failing_elements']} |\n"
        text+='''
## 演算群別の最大絶対差

| 演算群 | 局所差最大 | 上流差最大 | 合計差最大 |
| --- | --- | --- | --- |
'''
        for name,g in families.items():text+=f"| {name} | {g['local_max_abs']:.8g} | {g['propagated_max_abs']:.8g} | {g['total_max_abs']:.8g} |\n"
        text+='''
単位・尺度の違う行の絶対値を単純な優劣の順位にしない。RMS・ULP距離・固定限界比・L1・要素数と先頭失敗例はnode-comparisons.json、全case/演算群は別JSONに保存した。ULPは0近傍で大きくなり得る診断値で、採否基準の置換には使わない。

residual_sumの同一入力差は全42比較で0、attention mixingと分位点組立/復元も今回の同一入力では0だった。他の層の小さな実装差が存在し、上流を通るうちに大きくなる局面がある。有限集合での結果であり、一般の入力すべてに対する誤差上限保証ではない。

## 残る1点と結論

train-last/blocks.1 index3450＝[3,1,3,58]、PP=0.0283811092376709、RR=0.028383851051330566。今回RP=PPで局所差0、合計差2.741813660e-6は全て上流入力の差として分解され、固定限界2.567622185e-6を超える。したがって、この残差加算だけを直す根拠は得られなかった。

元の最終正規化/元単位出力は各6,048要素が許容差内、元R1の中間値1点未達は不変。局所差が全て条件内でも、全体の中間値gateを保証しないことを7ケース全層で確認した。局所passだけでR1合格へ変更せず、R2学習にも進まない。q50/context_centerを需要平均へ読み替えない。

## 資源と保存

| 実行 | 秒 | 測定メモリ |
| --- | --- | --- |
'''
        for name,e in units.items():
            if 'sampled_group_peak' in e:
                g=e['sampled_group_peak'];desc=f"監視込みfootprint {g['monitor_inclusive_footprint']:,}B / 同時RSS {g['monitor_inclusive_rss']:,}B"
            else:desc=f"child peak RSS {e['child_peak_rss_bytes']:,}B"
            text+=f"| {name} | {e['elapsed_seconds']:.3f} | {desc} |\n"
        text+=f'''
全実行は親900/子870秒、physical footprintとpeak RSS各2GiB以内。RustはCargo/compiler/linkerの同process groupを監視し、最大sampling間隔/短命childの捕捉限界も保存。hard OS capではない。build cache+targetは最終{disk_bytes():,}Bで1.5GiB以内。artifact24file/768MiB・単一32MiB、EvidenceStore16MiB/512file/part256KiB等も維持した。

主要rootはartifacts/rust-r1-layer-fixture2-20261016、rust-r1-layer-kernel-20261016、rust-r1-layer-comparison-20261016。最初の失敗はrust-r1-layer-fixture-20261016とrecordsへ保持。数値payloadは各closed artifactで保管し、全hashを読戻し確認。EvidenceStoreへは全source/stdio/exit/state/closure、payload manifest/hash、全診断集計と文書前後をartifacts/rust-r1-layer-results-20261016-evidenceへ保存する。

Mac共通CPUの診断は完了、元R1 gateは未達。Windows native/OS依存suite、製品toolchain1.98.1、lockなし配布は別の未確認項目。core source/Cargo.lockと旧成果不変、新依存/取得/外部送信/製品repo変更/push/本番採用なし。保全第一・学習を含むRust/banto目的、需要2015停止/調整2014以前/同休業mean28/四季両側非増加/観測と欠測0評価分離、heartbeat PAUSEDを維持。

## 今後の境界

今回固定した全層診断は完了し、同じ再生や1点狙いの修正を反復しない。現行の局所誤差が固定許容差内という事実だけでは、追加の一般修正を選ぶ根拠にならない。今後実装方式を比較する場合は、全ケース・全層へ一律適用する方式、その算術上の根拠、有限な比較数、全体gateを含む採否/停止条件を先に定める。現在その追加方式は選んでおらず、この診断をR1通過やRust学習開始の許可に読み替えない。
'''
        changes={report:text};lead='固定55箇所×7case/953,694要素で、同一入力の局所差超過0、上流累積の超過1。PP/RRの既存anchor各161箇所bytes一致、有限948,654要素でtotal=local+propagatedが厳密成立。'
        h='docs/current-handoff.md';changes[h]='## 最新 — 全層診断完了、局所差は全通過・累積1点未達（2026-10-16）\n\n[結果と固定条件](results/banto-ai-rust-r1-all-layer-audit-2026-10-16.md)。'+lead+' 残るtrain-last blocks.1 index3450は局所差0、差2.741813660e-6が全て上流入力の差。元の限界2.567622185e-6を超えR1未合格のまま。core/weight/許容差の変更0、候補探索0、R2未開始。\n\n初回Python診断再生がzeroのstrict anchorに失敗し保持。元のnn module/Parameter/no_grad条件へ診断だけをそろえ、fresh rootで全161anchor再現。候補モデルの再評価ではない。全source/stdio/exit/state/closureと集計/文書前後はartifacts/rust-r1-layer-results-20261016-evidence。\n\n全層診断は閉鎖。同じ再生・1点向け修正を反復しない。追加の一般方式が必要なら、全入力/全層への適用根拠と有限比較・全体採否条件を先に設計する。現時点で方式未選択、R1未達を局所passで覆さない。各2GiB/build1.5GiB/時間・保存枠、保全第一/Rust学習目的、需要条件/2015停止、heartbeat PAUSED維持。Windows/OS suite未実行、CARE test再評価/下流編集/push0。以下は旧記録。\n\n---\n\n'+(ROOT/h).read_text()
        for name,marker,entry in [('docs/results/README.md','## Rustクレートの移植\n','- [Rust R1全55箇所・7ケースの局所/累積差診断](banto-ai-rust-r1-all-layer-audit-2026-10-16.md) — 局所超過0、上流累積1点未達、モデル変更0。'),('docs/research/README.md','## 文書\n','- [Rust R1全層診断と固定条件](../results/banto-ai-rust-r1-all-layer-audit-2026-10-16.md) — 385比較、各161anchor厳密再現、局所と累積の差を分離。')]:
            oldtext=(ROOT/name).read_text();assert marker in oldtext;changes[name]=oldtext.replace(marker,marker+'\n'+entry+'\n',1)
        for name in ['docs/research/banto-ai-rust-implementation-plan-2026-10-16.md','docs/research/rust-small-forecaster-r0-2026-10-16.md']:
            changes[name]=re.sub(r'^状態:.*$','状態: R1a/既存3テストpass。全55箇所×7caseの診断完了、局所超過0・上流累積1点未達でR1未合格。モデル変更/候補探索0、R2未着手。[全層診断結果](../results/banto-ai-rust-r1-all-layer-audit-2026-10-16.md)。2026-10-16 JST。',(ROOT/name).read_text(),count=1,flags=re.M)
        name='docs/research/research-roadmap.md';changes[name]='## 現在 — R1全層診断を閉鎖、局所passで全体未達を覆さない（2026-10-16）\n\n[結果](../results/banto-ai-rust-r1-all-layer-audit-2026-10-16.md)。'+lead+' 追加方式は未選択、1点への修正探索をせずR1未達・R2停止を維持。以下は旧記録。\n\n---\n\n'+(ROOT/name).read_text()
        sources=list(dict.fromkeys([Path(__file__),*source_files(),*[ROOT/'tools/public-data'/n for n in ['rust_r1_layer_fixture.py','rust_r1_layer_compare.py','rust_r1_compare.py','care_rust_r0_close.py']],ROOT/'tools/verification_records.py']))
        out.sources(sources);evidence=ROOT/'artifacts/rust-r1-layer-results-20261016-evidence';summary={**phase,'node_comparisons':385,'primitive_elements':953694,'original_R1_elements':389214,'reference_anchors_byte_exact':161,'rust_anchors_byte_exact':161,'decomposition_residual':0.,'disk_bytes':disk_bytes()}
        with EvidenceStore(evidence) as store:
            store.write_json('phase',phase);store.write_json('root-pins',roots+old);store.write_json('summary',summary)
            for i,p in enumerate(sources):store.write_bytes(f'source-{i}',p.read_bytes())
            for i,p in enumerate(cfgs):store.write_bytes(f'fixed-config-{i}',p.read_bytes())
            store.write_json('document-paths',list(changes))
            for i,name in enumerate(changes):
                p=ROOT/name
                if p.exists():store.write_bytes(f'before-{i}',p.read_bytes())
            for name,value in changes.items():(ROOT/name).write_text(value)
            for i,name in enumerate(changes):store.write_bytes(f'after-{i}',(ROOT/name).read_bytes())
            for i,r in enumerate(roots):
                for j,p in enumerate(sorted((ROOT/r['root']).iterdir())):
                    if p.suffix!='.bin':store.write_bytes(f'root-{i}-{j}',p.read_bytes())
            for i,r in enumerate(old):store.write_bytes(f'old-closure-{i}',(ROOT/r['root']/'root-closed.json').read_bytes())
            links=0
            for target in re.findall(r'\]\(([^)]+)\)',text):
                assert ((ROOT/report).parent/target).exists(),target;links+=1
            for r in roots+old:
                verified=validate_root(ROOT/r['root']);assert verified['closure_sha256']==r['closure_sha256']
            assert {str(p):digest(p) for p in cfgs}==pins
            assert digest(ROOT/'crates/banto-ai/src/model.rs')==contract['source_model_sha256']
            store.write_json('readback',{'all_sources_configs_core_and_closed_roots_preserved':True,'binary_payloads_hash_verified_in_primary_artifacts':True,'local_links_checked':links})
            store.write_terminal('terminal',{'exit':0,'state':'all-layer diagnosis complete; R1 failure unchanged; no training','resources':check.check()})
        out.json('evidence-readback.json',verify_evidence(evidence,'complete'));out.json('summary.json',{**summary,'resources':check.check()})
        print(json.dumps({'diagnosis_complete':True,'local_failures':0,'cumulative_failures':1,'core_changed':False,'R1_complete':False}));status='complete'
    finally:out.close(status)
if __name__=='__main__':main()
