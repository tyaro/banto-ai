"""Close the same-input diagnosis while retaining the unchanged R1 failure."""
import json,math,re,struct,sys
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
NAMES=['rust-r1-ff-fixture-20261016','rust-r1-ff-fixture-20261016-records','rust-r1-ff-format-20261016','rust-r1-ff-kernel-20261016','rust-r1-ff-kernel-20261016-records','rust-r1-ff-diagnosis-20261016','rust-r1-ff-diagnosis-20261016-records','rust-r1-ff-diagnosis2-20261016','rust-r1-ff-diagnosis2-20261016-records']
def read(name,file='summary.json'):return json.loads((ROOT/'artifacts'/name/file).read_bytes())
def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]
def main():
    out=Files(ROOT/'artifacts/rust-r1-ff-results-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        roots=[validate_root(ROOT/'artifacts'/n) for n in NAMES]
        preserved=[validate_root(ROOT/'artifacts'/n) for n in ['rust-r1-python-reference-20261016','rust-r1-burn-predictions2-20261016','rust-r1-compare2-20261016','rust-r1-results-20261016']]
        d=read('rust-r1-ff-diagnosis2-20261016');assert d['same_input_linear_comparisons_pass'] and d['identical_operand_add_byte_exact'] and d['Rust_saved_block_reproduced_byte_exact']
        assert d['point']['signed_error_decomposition']['same_input_linear_backend']==0
        assert d['point']['signed_error_decomposition']['residual_add_rounding_difference']==0
        original=read('rust-r1-compare2-20261016');assert original['failing_elements']==1 and not original['parity_pass']
        p0=ROOT/'artifacts/rust-r1-python-reference-20261016';p1=ROOT/'artifacts/rust-r1-burn-predictions2-20261016'
        operands={}
        for side,p in [('python',p0),('rust',p1)]:
            man=read(p.name,'fixtures.json' if side=='python' else 'traces-layout.json');case=man['cases'][0]
            raw=(p/('python-traces.bin' if side=='python' else 'rust-traces.bin')).read_bytes()
            ts={e['name']:floats(raw,e) for e in case['traces']}
            # [4,1,3,7] maps to variate [4*5+3,1,7].
            base=ts['blocks.0'][4359];temporal=ts['blocks.1.temporal'][4359];variate=ts['blocks.1.variate'][4487]
            residual=f32(f32(base+temporal)+variate)
            assert residual==d['point']['values'][f'{side}_residual']
            operands[side]={'blocks0':base,'temporal':temporal,'variate':variate,'residual':residual}
        upstream={k:operands['rust'][k]-operands['python'][k] for k in ['blocks0','temporal','variate']}
        upstream['addition_rounding']=operands['rust']['residual']-operands['python']['residual']-math.fsum(upstream.values())
        condition=(abs(d['point']['values']['python_residual'])+abs(d['point']['values']['torch_linear_python_input']))/abs(d['point']['values']['python_block'])
        out.json('upstream-residual-breakdown.json',{'values':operands,'signed_difference':upstream,'local_cancellation_ratio':condition})
        cfgs=[ROOT/'examples/configs'/n for n in ['rust-small-forecaster-r0-20261016.json','rust-small-forecaster-r0-20261016-r0.1.json','care-a-maintenance-20261016-r1.json','rust-r1-build-budget-20261016-r1.json']]
        cfgpins={str(p):digest(p) for p in cfgs};assert cfgpins[str(cfgs[1])]=='bd5c962c711decbad2e590af71ed9474d1f6256351571d3b16a8e3ada047c57a'
        state=read('rust-r1-tests3-20261016','state.json')['source_pins_after']
        core=[x for x in state if x['path'].startswith('crates/banto-ai/src/') or x['path']=='Cargo.lock']
        for x in core:assert digest(ROOT/x['path'])==x['sha256']
        resources={n:read(n,'exit.json') for n in ['rust-r1-ff-fixture-20261016-records','rust-r1-ff-kernel-20261016-records','rust-r1-ff-diagnosis2-20261016-records']}
        for n,e in resources.items():assert e['returncode']==0 and e['elapsed_seconds']<870
        rust=resources['rust-r1-ff-kernel-20261016-records'];assert max(rust['sampled_group_peak']['monitor_inclusive_footprint'],rust['sampled_group_peak']['monitor_inclusive_rss'],rust['child_wait_peak_rss_bytes'])<2*1024**3
        assert rust['sampled_cache_bytes']<1536*1024**2
        phase={'scope':'publish completed same-input ff/residual diagnosis; original full parity remains failed','R1_complete':False,'diagnosis_complete':True,'core_source_unchanged':True,'new_full_forward_calls':0,'training':False,'labels_or_CARE_test_or_demand2015':False,'tolerance_changed':False,'R2_started':False,'memory_cap_bytes':2*1024**3,'build_cache_cap_bytes':1536*1024**2,'prior_failure_preserved':True}
        out.json('phase.json',phase);out.json('root-pins.json',roots+preserved);out.json('resources.json',resources)
        report='docs/results/banto-ai-rust-r1-intermediate-diagnosis-2026-10-16.md'
        point=d['point'];values=point['values'];pieces=point['signed_error_decomposition']
        text=f'''# Rust R1 — 残る1点の演算差の切り分け（2026-10-16）

[計画](../research/banto-ai-rust-implementation-plan-2026-10-16.md)に沿い、残るtrain-first/block1の1点を共通入力で診断した。**この点のff.2線形演算は共通入力ならRust/Pythonで一致し、残差加算も同じ結果だった。超過は上流2経路の誤差が相殺の大きい和へ集まった結果**。局所演算の違いと上流伝播を分離できたが、元のR1全体は1点未達のまま。許容差は変更しない。

## 固定入力と実施範囲

保存済みPython参照とbalanced Rustのtrain-first全120行を使い、block0出力＋block1 temporal＋variateからFF前残差を再構成した。ff.1出力[8,3,5,128]、固定ff.2 weight[64,128]/bias[64]を取り出し、Python入力とRust入力それぞれを両backendへ同じbytesで渡した。Python側の保存block1再構成はbytes一致。Rust側も実際のFlex線形＋残差和で保存block1全7,680要素にbytes一致し、診断経路が対象経路を再現することを確認。

全model forward0、学習/backward/optimizer0、label/CARE test/需要2015の参照0。PyTorchとFlexは各2回の局所linearだけ。新しい予測やPython参照の再生成は行っていない。model.rsを含むcore sourceとCargo.lockは前回テスト成功時と同じ。追加した [diagnose_ff実行例](../../crates/banto-ai/examples/diagnose_ff.rs) はlocked/offline CPU build・実行済み。coreに変更がないため、既存3テストの無目的な再実行はしていない。

## 共通入力での比較

| 比較 | 要素数 | 最大絶対差 | 超過数 |
| --- | --- | --- | --- |
| Python保存FF入力→各backendのff.2 | 7,680 | 1.430511475e-6 | 0 |
| Rust保存FF入力→各backendのff.2 | 7,680 | 9.536743164e-7 | 0 |
| 同一の残差/線形出力を足す | 各7,680 | 0 | 0 |

線形出力自身にも従来の中間値許容差2e-6＋2e-5×abs(reference)を適用。両共通入力で全要素pass。全linearがbytes一致という意味ではないが、問題のindex4359では両入力ともff.2出力もbytes一致した。独立高精度dotは診断だけに用い、モデルのdtype/演算を高精度値へ置換していない。

## 残る1点の誤差分解

対象は[batch4,series1,token3,dim7]、0始まり。

| 枝 | Python | Rust | Rust−Python |
| --- | --- | --- | --- |
| FF前の残差 | {values['python_residual']!r} | {values['rust_residual']!r} | {pieces['upstream_residual']!r} |
| ff.2（各自のFF入力） | {values['torch_linear_python_input']!r} | {values['flex_linear_rust_input']!r} | {pieces['upstream_ff_input_through_torch']!r} |
| 出力の和 | {values['python_block']!r} | {values['rust_block']!r} | {point['signed_total']!r} |

符号付き誤差の内訳は、上流残差1.370906830e-6＋上流FF入力が伝わった差9.238719940e-7＋この点の同一入力backend差0＋加算丸めの差0＝2.294778824e-6。固定限界2.112383962e-6を超える。約0.368と−0.373の和が約−0.00562となり、枝に比べて出力が小さいため、この出力に対する限界が厳しくなる。枝の大きさの和/出力絶対値は約{condition:.2f}倍。閾値変更の根拠にはしない。

FF前残差をさらにblock0/temporal/variateへ分解した数値をupstream-residual-breakdown.jsonへ保存した。現在の結果から「ff.2のバグ」「残差加算のバグ」や「ある1つの上流演算だけが原因」とは断定しない。上流のfloat32演算順・累積差をどこまで参照へ合わせられるかが残る課題である。

## 失敗・資源・保存

診断集計の初回はRust JSONのfloat32最短表現をPython float64のままbytes等価比較し、再構成一致assertが失敗した。読戻しをfloat32へ戻して比較するよう修正し、同じ保存済み出力だけをfresh診断rootで集計し直した。最初の失敗と全stdio/source/exit/closureは保持。モデル/局所kernelの再実行は0。この不具合は元のbinary方式R1比較器にはない。

PyTorch診断は7.294秒・child peak RSS304,250,880B。Rust build/局所演算は5.351秒、監視込みphysical footprint286,624,768B/RSS397,443,072B、子peak RSS4,161,536Bを別々に保存。RSSの定義とsampling値を混同せず、各2GiB・子870/親900秒以内。build cache観測929,981,148Bで1.5GiB内。samplingの短命process捕捉限界を維持する。旧artifact24file/768MiB・単一32MiB、EvidenceStore16MiB等の保存枠も不変。

主要rootはartifacts/rust-r1-ff-fixture-20261016、rust-r1-ff-kernel-20261016、rust-r1-ff-diagnosis2-20261016。失敗はrust-r1-ff-diagnosis-20261016とそのrecordsへ保存。全source/stdio/exit/state/closure、文書前後と旧成果pinはartifacts/rust-r1-ff-results-20261016-evidence。全part/SHAを読戻して閉鎖する。

Mac共通CPUの局所演算比較はpass、元の固定7ケース全体一致は未達のまま。以前の最終予測7case/各6,048要素passを変更せず、R1完了/製品採用とはしない。Windows native/OS依存suite、下流toolchain1.98.1、lockなし解決は未検証。banto-industrial/denroku編集、新取得/外部送信/pushなし。

## 次工程

次は**上流の同一入力での演算順の差**を有限に切り分ける。保存値から第2blockのnorm/attention/FF入力を共通化し、参照と実装の一般的な演算順の相違があるか確認する。特定indexだけの補正、値の置換、許容差拡大、同じfull forwardの反復は行わない。修正根拠が得られた場合にだけ、事前宣言した一般的な修正を行い、元の7ケース全部で確認する。R1未達の間はR2へ進まない。

保全・点検支援第一、学習を含むRustとbanto統合の目的、AI本体banto-ai/利用側責務は維持。需要2015停止・調整2014以前・同休業mean28・四季両側非増加・観測のみ/欠測0評価分離、heartbeat PAUSEDも維持する。
'''
        changes={report:text}
        h='docs/current-handoff.md';lead='残る1点は上流残差1.370906830e-6＋FF入力伝播9.238719940e-7の合計。共通入力ff.2の対象点差0、同一operandsの加算差0。全linear各7,680要素も固定許容差内。'
        changes[h]='## 最新 — Rust R1の1点を共通入力で分解、上流累積差と確認（2026-10-16）\n\n[診断結果と次工程](results/banto-ai-rust-r1-intermediate-diagnosis-2026-10-16.md)。'+lead+' 保存Rust block1の局所再構成はbytes一致。0.368と−0.373の相殺で出力が小さくなり、累積差2.294778824e-6が元の限界2.112383962e-6を超える。R1全体未達は不変、許容差変更なし。\n\nfull forward/学習0、Python/Flex各2局所linearだけ。core/Cargo.lock不変、診断exampleをbuild実行。最初の診断集計はJSON f32最短表現をf64のまま比較して失敗、f32読戻しへ修正し保存値だけfresh集計。失敗を保持、kernel再実行0。次は第2blockのnorm/attention等を同一入力で比較し、一般的な演算順の差を特定。根拠なしの修正やfull forward反復をしない。\n\nR1a/既存3テストpass、R1b未達・R2未開始。メモリ各2GiB/build1.5GiB/時間・保存枠維持、Windows/OS suite未実行。CARE test/需要2015再評価0、下流編集/push0。保全第一・Rust学習目的と需要条件・heartbeat PAUSED維持。全証跡/文書前後はartifacts/rust-r1-ff-results-20261016-evidence。以下は旧記録。\n\n---\n\n'+(ROOT/h).read_text()
        for name,marker,entry in [('docs/results/README.md','## Rustクレートの移植\n','- [Rust R1の中間値1点の切り分け](banto-ai-rust-r1-intermediate-diagnosis-2026-10-16.md) — 共通入力線形/加算を確認、上流2枝の累積差。R1未達は維持。'),('docs/research/README.md','## 文書\n','- [Rust R1の共通入力診断](../results/banto-ai-rust-r1-intermediate-diagnosis-2026-10-16.md) — 局所演算差と上流伝播を分離。次は上流演算順。')]:
            old=(ROOT/name).read_text();assert marker in old;changes[name]=old.replace(marker,marker+'\n'+entry+'\n',1)
        for name in ['docs/research/banto-ai-rust-implementation-plan-2026-10-16.md','docs/research/rust-small-forecaster-r0-2026-10-16.md']:
            changes[name]=re.sub(r'^状態:.*$', '状態: R1a CPU build/3テストpass。R1b残差1点の共通入力診断完了、局所ff.2/加算自身ではなく上流累積差。全体一致は未達、R2未着手。[診断と次工程](../results/banto-ai-rust-r1-intermediate-diagnosis-2026-10-16.md)。2026-10-16 JST。',(ROOT/name).read_text(),count=1,flags=re.M)
        name='docs/research/research-roadmap.md';changes[name]='## 現在 — R1の局所診断完了、上流累積差の演算順を確認する（2026-10-16）\n\n[結果](../results/banto-ai-rust-r1-intermediate-diagnosis-2026-10-16.md)。'+lead+' 元の全体gateは未達、R2未開始。以下は旧記録。\n\n---\n\n'+(ROOT/name).read_text()
        sources=list(dict.fromkeys([Path(__file__),*source_files(),*[ROOT/'tools/public-data'/n for n in ['rust_r1_ff_fixture.py','rust_r1_ff_compare.py','rust_r1_compare.py','care_rust_r0_close.py']],ROOT/'tools/verification_records.py']))
        out.sources(sources);evidence=ROOT/'artifacts/rust-r1-ff-results-20261016-evidence'
        summary={**phase,'same_input_ff_elements':15360,'remaining_point':point,'upstream_residual_breakdown':upstream,'disk_bytes':disk_bytes()}
        with EvidenceStore(evidence) as store:
            store.write_json('phase',phase);store.write_json('root-pins',roots+preserved);store.write_json('summary',summary)
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
            for i,r in enumerate(preserved):store.write_bytes(f'old-closure-{i}',(ROOT/r['root']/'root-closed.json').read_bytes())
            store.write_bytes('upstream-breakdown',(out.root/'upstream-residual-breakdown.json').read_bytes())
            links=0
            for target in re.findall(r'\]\(([^)]+)\)',text):
                assert ((ROOT/report).parent/target).exists(),target;links+=1
            for r in roots+preserved:assert digest(ROOT/r['root']/'root-closed.json')==r['closure_sha256']
            assert {str(p):digest(p) for p in cfgs}==cfgpins
            for x in core:assert digest(ROOT/x['path'])==x['sha256']
            store.write_json('readback',{'original_closures_unchanged':True,'core_lock_configs_unchanged':True,'links_checked':links})
            store.write_terminal('terminal',{'exit':0,'state':'diagnosis complete; original R1 remains failed','resources':check.check()})
        out.json('evidence-readback.json',verify_evidence(evidence,'complete'));out.json('summary.json',{**summary,'resources':check.check()})
        print(json.dumps({'diagnosis_complete':True,'R1_complete':False,'local_add_exact':True,'core_unchanged':True}));status='complete'
    finally:out.close(status)
if __name__=='__main__':main()
