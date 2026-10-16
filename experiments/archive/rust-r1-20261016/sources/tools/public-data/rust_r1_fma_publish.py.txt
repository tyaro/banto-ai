"""Publish verified opt-in FMA and rejected model integration, with restoration."""
import json
import math
import re
import sys
import tomllib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'models/mini-transformer'),str(ROOT/'tools/public-data')]
from metropt_multiday import Files,digest,verify_closed
from macos_demand_runtime import MacCheckpoint
from macos_rust_run import source_files,disk_bytes
from rust_r1_publish_preparation import validate_root
from rust_r1_compare import floats
from verification_records import EvidenceStore
from care_rust_r0_close import verify_evidence


def main():
    out=Files(ROOT/'artifacts/rust-r1-fma-results-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        names=['rust-r1-fma-fixture-20261016','rust-r1-fma-fixture-20261016-records','rust-r1-fma-format-20261016',
               'rust-r1-fma-tree-20261016','rust-r1-fma-probe-20261016-records','rust-r1-fma-probe2-20261016-records',
               'rust-r1-fma-harness-repair-20261016','rust-r1-fma-harness-repair-20261016-records','rust-r1-fma-probe3-20261016-records',
               'rust-r1-fma-final-format-20261016','rust-r1-fma-probe4-20261016','rust-r1-fma-probe4-20261016-records',
               'rust-r1-fma-tests-20261016','rust-r1-fma-model-declaration-20261016','rust-r1-fma-model-declaration-20261016-records',
               'rust-r1-fma-local-format-20261016','rust-r1-fma-local-kernel-20261016','rust-r1-fma-local-kernel-20261016-records',
               'rust-r1-fma-local-comparison-20261016','rust-r1-fma-local-comparison-20261016-records','rust-r1-fma-model-tests-20261016',
               'rust-r1-fma-predictions-20261016','rust-r1-fma-predictions-20261016-records','rust-r1-fma-full-comparison-20261016',
               'rust-r1-fma-full-comparison-20261016-records','rust-r1-fma-model-restore-20261016','rust-r1-fma-model-restore-20261016-records',
               'rust-r1-fma-features-20261016']
        pins=[validate_root(ROOT/'artifacts'/n) for n in names]
        def read(n,f='summary.json'):return json.loads((ROOT/'artifacts'/n/f).read_bytes())
        primitive=read('rust-r1-fma-probe4-20261016');local=read('rust-r1-fma-local-comparison-20261016');full=read('rust-r1-fma-full-comparison-20261016')
        assert primitive['plain_bits']==primitive['autodiff_bits']==20 and primitive['tracked_output'] and primitive['backward_calls']==0
        assert local['local_gate_pass'] and local['candidate_bit_exact_inputs']==49
        assert not full['parity_pass'] and full['failing_elements']==3 and full['elements_compared']==389214
        assert read('rust-r1-fma-model-restore-20261016')['model_restored_byte_exact']
        initial=read('rust-r1-fma-fixture-20261016','source-pins-before.json')
        for p in initial:
            if p['path'] not in ['crates/banto-ai/Cargo.toml','crates/banto-ai/src/lib.rs']:assert digest(ROOT/p['path'])==p['sha256'],p['path']
        assert digest(ROOT/'crates/banto-ai/src/model.rs')=='acefec42e7506d807f7deae22269f30f9bf409a8c8cf9d1ddb59c2ef6af7fa80'
        package=tomllib.loads((ROOT/'crates/banto-ai/Cargo.toml').read_text());assert package['features'].get('default',[])==[]
        assert package['dependencies']['burn']['version']=='=0.22.0'
        def packages(p):return set(tuple(m.groups()) for line in p.read_text().splitlines() if (m:=re.match(r'^(\S+) v([^ ]+)',line)))
        baseline=packages(ROOT/'artifacts/rust-r1-tree-20261016/stdout.txt');extended=packages(ROOT/'artifacts/rust-r1-fma-tree-20261016/stdout.txt')
        assert baseline==extended and len(extended)==154
        features=(ROOT/'artifacts/rust-r1-fma-features-20261016/stdout.txt').read_text()
        assert 'burn-flex feature "simd"' not in features and 'burn-flex feature "rayon"' not in features
        # Confirm the unchanged prefix using saved traces; no new kernels.
        old=ROOT/'artifacts/rust-r1-burn-predictions3-20261016';candidate=ROOT/'artifacts/rust-r1-fma-predictions-20261016';ref=ROOT/'artifacts/rust-r1-python-reference-20261016'
        oldpins=[]
        for p in [old,ref]:verify_closed(p);oldpins.append({'root':str(p.relative_to(ROOT)),'closure_sha256':digest(p/'root-closed.json')})
        ms=[read('rust-r1-burn-predictions3-20261016','traces-layout.json'),read('rust-r1-fma-predictions-20261016','traces-layout.json'),read('rust-r1-python-reference-20261016','fixtures.json')]
        raws=[(old/'rust-traces.bin').read_bytes(),(candidate/'rust-traces.bin').read_bytes(),(ref/'python-traces.bin').read_bytes()]
        prefix=[]
        for a,b,c in zip(*(m['cases'] for m in ms),strict=True):
            assert a['id']==b['id']==c['id']
            maps=[{e['name']:e for e in case['traces']} for case in [a,b,c]]
            for name in ['context_center','context_scale','normalized_context','patch','tokens']:
                entries=[m[name] for m in maps]
                blobs=[raw[e['offset_bytes']:e['offset_bytes']+e['length_bytes']] for raw,e in zip(raws,entries,strict=True)]
                assert blobs[0]==blobs[1]
                xs=floats(raws[2],entries[2]);ys=floats(raws[1],entries[1])
                prefix.append({'case':a['id'],'node':name,'candidate_equals_baseline_bytes':True,'reference_SSE':math.fsum((x-y)**2 for x,y in zip(xs,ys,strict=True))})
        comparisons=read('rust-r1-fma-full-comparison-20261016','tensor-comparisons.json');failures=[r for r in comparisons if r['failing_elements']]
        assert sum(r['failing_elements'] for r in comparisons if r['tensor'] in ['normalized_quantiles','quantiles'])==0
        resources={};failed_codes={'rust-r1-fma-probe-20261016-records':101,'rust-r1-fma-probe2-20261016-records':101,'rust-r1-fma-probe3-20261016-records':101,'rust-r1-fma-full-comparison-20261016-records':1}
        for name in names:
            p=ROOT/'artifacts'/name/'exit.json'
            if not p.exists():continue
            e=json.loads(p.read_bytes());g=e['sampled_group_peak'];assert e['returncode']==failed_codes.get(name,0)
            assert e['elapsed_seconds']<870 and max(g['monitor_inclusive_footprint'],g['monitor_inclusive_rss'],e['child_wait_peak_rss_bytes'])<2*1024**3
            assert e['sampled_cache_bytes']<1536*1024**2
            resources[name]=e
        phase={'FMA_artificial_forward_pass':True,'FMA_graph_participation':True,'backward_verified':False,
               'local_LayerNorm_bit_exact_inputs':49,'candidate_whole_R1_failing_elements':3,
               'candidate_adopted':False,'model_restored_byte_exact':True,'baseline_R1_failing_elements':1,
               'R1_complete':False,'R2_started':False,'training':False,'tolerance_changed':False,
               'feature_opt_in':True,'dependency_package_set_unchanged':True,'CARE_or_demand2015_reevaluation':False}
        report='docs/results/banto-ai-rust-r1-fma-extension-2026-10-16.md'
        text=f'''# Rust R1 — FMA拡張forward成功、モデル接続候補は不採用（2026-10-16）

**公開APIによるFMA拡張の人工forwardと局所LayerNormの全bit一致は通過した。一方、モデル全体では中間値3点が元の許容差を超えたため、接続候補は不採用としてmodel.rsを元bytesへ戻した。現在の安定版は従来の1点未達のまま**。許容差・参照・weightsを変更せず、R1は未合格・R2学習は未開始。

## 公開拡張APIと人工forward

[FMAの事前条件](../../examples/configs/rust-r1-fma-extension-20261016.json)を保存後に実装した。Burn0.22.0の `extension` featureに公開のbackend_extension、into_dispatch/from_dispatch、具体backend primitiveの安全な変換口があることを確認した。private bridgeやunsafe表現変換は不要だった。

`crates/banto-ai/src/fma.rs` はFlex CPUのprimitive storage上でRust標準f32::mul_addを使う。Autodiff<Flex>には三親のNodeGuardを保ってchildを登録し、既存tensor APIのexpandでbroadcastを表現する。高水準to_data/from_dataの読戻し・値の再注入はしない。backwardの実装コードはcompileしたが、逆伝播は実行も認定もしていない。

専用の非default feature `fma-extension` からburn/extensionとburn/autodiffを有効にする。Burn=0.22.0、Cargo.lock、既存defaultは維持。offline/lockedで実行し、Cargo treeのpackage集合は前後とも154で同一、FlexのSIMD/rayonは有効化していない。新package/versionの追加・download・registry編集・backend変更は0。

| 人工確認 | 結果 |
| --- | --- |
| 独立system fmafとRust scalar oracle | 固定20値のbits一致 |
| 通常Flex / Autodiff FlexのFMA | 各20値のbits一致 |
| broadcast / 転置viewとalias / offset view | 6 / 6 / 4値一致 |
| 入力不変・中間graph参加 | 確認 |
| shape/dtype/空shape/自動微分context・非有限境界 | 7拒否条件を確認 |
| 既存Rustの入力/causal/neutral整合テスト | 3件pass（接続前と候補接続後） |
| backward / optimizer / 学習 | 0、正しさ未確認 |

相殺、subnormal、signed zero、積単独はoverflowしても積和はfiniteの例を含めた。f64のmul+addをf32へcastすると0x3fc00002になるが、正しいFMAは0x3fc00001となる固定反例も確認し、その代用方式は使わなかった。

三つの技術的失敗を保存した。初回はprivate into_contiguousの呼出しでcompile失敗し、公開to_contiguousへ修正。次はテストがis_require_gradをgraph参加と誤解していたため、pinしたAPIの意味に従いis_trackedへ修正した（勾配を保持する葉と中間ノードの区別）。三回目はDeviceの等値比較がautodiff設定を区別しないことを境界試験で検出し、autodiff/checkpoint設定を明示比較した。演算式・期待bits・入力は変更しておらず、成功判定はfresh probe4のみ。非有限拒否でcatchした3件のpanicは意図した境界試験で、最終exit0と区別してstderrへ保持した。

## 一般的なモデル接続候補の有限比較

[接続前の固定条件](../../examples/configs/rust-r1-fma-model-20261016.json)に従った。binaryで確定した4lane/幅64のWelfordとscalar FMA統合を、host診断ループではなくtensor slice・普通のf32演算・公開FMAノードで表現した。全7ケース/全7LayerNormの同一Python経路入力で候補49組の124,992出力がPPとbits一致し、旧balanced式49組も保存RPとbytes一致した。

局所gate通過後に、一度だけ全LayerNormへ一律のcfg hookを置き、既存3テストと固定7ケースのfull forwardを実行。入力、context正規化、attention、linear/GELU、weightsなどは不変。元の23anchor/389,214要素に元R0.1許容差を適用した結果は以下。

| ケース | 元R1中間値の超過 |
| --- | --- |
| train-first | 1 |
| train-last | 2 |
| zero / constant / floor-below / equal / above | 各0 |
| 合計 | 3 / 389,214 |

'''
        for r in failures:
            text+=f"- {r['case']} / {r['tensor']}: {r['failing_elements']}要素、最大許容差比{r['max_tolerance_ratio']:.9f}。\n"
        text+='''
正規化後/元単位の最終分位点は、それぞれ全7ケース/6,048要素が元許容差内で、非有限・順序違反はない。しかし全体の中間値gateは不通過であり、最終出力の通過や局所の完全一致だけで合格へ変更しない。

保存tracesで、最初のLayerNormより前のcontext_center/context_scale/normalized_context/patch/tokensは、候補と安定版が全35箇所でbytes一致した。参照Pythonとの差はそのまま残っており、同一Python入力での局所一致と、自経路の入力差を含むモデル全体の一致が別であることを確認した。3点を特定の一演算だけへ因果帰属せず、誤差伝播を別に検討する。

## 採否と現在の状態

事前の復元条件に従い、hookだけを戻しmodel.rsの元SHA `acefec42e7506d807f7deae22269f30f9bf409a8c8cf9d1ddb59c2ef6af7fa80` とbytes一致を確認した。候補source・全予測・局所/全体比較・失敗recordsは保持し、default featureは変えていない。FMAとreference_layer_normはopt-inの研究APIとして残るがSmallForecasterからは呼ばれない。現在の安定版の累積1点未達は不変で、今回の候補3点と混同しない。

同じ候補のretry、3点向け例外、許容差緩和、参照再生成を行わない。次は保存済みの初期context平均/尺度の差をソースと演算順から整理し、一般方式の根拠があるかを判断する。LayerNorm単体一致を再検証する必要はない。新候補/有限比較/採否を事前に固定できるまで新model forwardは起動しない。

保全・点検支援第一優先、産業/需要の自作モデル実用性、学習を含むRust移植の目的を維持。CARE test/需要2015再評価・実学習・下流repo編集・Git push・製品採用0。需要調整2014以前、同休業mean28、四季過小/過大非増加、観測のみ/欠測0評価分離、heartbeat PAUSEDを維持。Windows native/OS依存suiteは未実行。

## 資源と保存

'''
        maxfp=max(e['sampled_group_peak']['monitor_inclusive_footprint'] for e in resources.values());maxrss=max(max(e['sampled_group_peak']['monitor_inclusive_rss'],e['child_wait_peak_rss_bytes']) for e in resources.values())
        text+=f'全単位が親900/子870秒、physical footprint/peak RSS各2GiB以内。監視込み最大footprint {maxfp:,}B、最大RSS系指標 {maxrss:,}B、cache+target最終 {disk_bytes():,}Bで1.5GiB以内。process group sampleの捕捉限界がありhard OS capではない。旧artifact/EvidenceStore/stdio枠を維持した。\n\n'
        text+='主要rootはartifacts/rust-r1-fma-fixture-20261016、rust-r1-fma-probe4-20261016、rust-r1-fma-local-kernel-20261016、rust-r1-fma-full-comparison-20261016、rust-r1-fma-model-restore-20261016および各records。全source/stdio/exit/state/closure、package/feature確認、集計/文書前後はartifacts/rust-r1-fma-results-20261016-evidenceへ保存。全体比較は結果rootがcompleteでもparity=falseによりcommand exit1であり、技術的失敗のexit101と区別した。\n'
        headline='公開backend extensionのFMA人工forward/graph参加と全49 LayerNormの局所bit一致はpass。一律hookの全体固定7case/389,214要素は中間3点超過で不採用。model.rsを元bytesへ復元、FMAはopt-inの研究APIとして保持。安定版は従来の累積1点未達、R1未合格/R2停止。'
        changes={report:text}
        h='docs/current-handoff.md';changes[h]='## 最新 — FMA拡張を実装、全体候補は不採用・model復元（2026-10-16）\n\n[結果と採否](results/banto-ai-rust-r1-fma-extension-2026-10-16.md)。'+headline+' 許容差/参照/weights/Cargo.lockとdefaultは不変、Cargo treeのpackage集合154も同一。\n\n初回compile・graph判定API・混在context拒否の3技術的失敗を保持し、probe4だけで人工forward採否。backward実装はcompileしたが実行0・未検証。接続条件を事前固定し、候補は1方式/49局所+7fullのみ。既存3テストpass。prefix5node×7caseは候補/安定版bytes一致で、局所一致だけでは上流誤差を消せない。全source/stdio/exit/state/closureと文書前後はartifacts/rust-r1-fma-results-20261016-evidence。\n\n次は初期context平均/尺度の差をソースと演算順から整理し、一般方式の根拠があるか判断する。同候補やLayerNorm局所確認を反復せず、有限条件を固定するまで追加model forwardをしない。各2GiB/build1.5GiB/時間/保存枠、旧成果/失敗/closed roots、保全第一/Rust学習目的、需要2015停止/2014以前調整/同休業mean28/四季両側非増加/観測欠測0分離、Windows別検証、heartbeat PAUSED維持。以下は旧記録。\n\n---\n\n'+(ROOT/h).read_text()
        for name,marker,entry in [('docs/results/README.md','## Rustクレートの移植\n','- [Rust R1 FMA拡張と全体候補の不採用](banto-ai-rust-r1-fma-extension-2026-10-16.md) — 人工/局所pass、全体3点未達でmodel復元。'),('docs/research/README.md','## 文書\n','- [Rust R1 FMA拡張の実装・採否](../results/banto-ai-rust-r1-fma-extension-2026-10-16.md) — 公開拡張API、独立oracleとgraph、R2未開始。')]:
            before=(ROOT/name).read_text();assert marker in before;changes[name]=before.replace(marker,marker+'\n'+entry+'\n',1)
        for name in ['docs/research/banto-ai-rust-implementation-plan-2026-10-16.md','docs/research/rust-small-forecaster-r0-2026-10-16.md']:
            changes[name]=re.sub(r'^状態:.*$','状態: R1a/既存3テストpass。FMA人工forwardと局所49組bit一致はpass、全体候補3点超過で不採用・model元bytes復元。安定版R1は累積1点未達、R2未開始。[最新結果](../results/banto-ai-rust-r1-fma-extension-2026-10-16.md)。2026-10-16 JST。',(ROOT/name).read_text(),count=1,flags=re.M)
        for name in ['docs/research/rust-fma-primitive-contract-2026-10-16.md','docs/research/rust-r1-moments-admission-2026-10-16.md']:
            changes[name]='現在の進捗（2026-10-16）: [FMA人工forward/局所一致は完了、全体候補は不採用](../results/banto-ai-rust-r1-fma-extension-2026-10-16.md)。modelは復元済み。is_require_gradは葉の勾配保持、graph参加はis_trackedで確認した。backward/学習は未実行。以下の当初条件と過去記録を保持する。\n\n'+(ROOT/name).read_text()
        n='docs/research/research-roadmap.md';changes[n]='## 現在 — FMA拡張を保持、全体候補は復元（2026-10-16）\n\n[結果](../results/banto-ai-rust-r1-fma-extension-2026-10-16.md)。'+headline+' 次は初期contextモーメントの差のソース確認、無目的な再評価はしない。以下は旧記録。\n\n---\n\n'+(ROOT/n).read_text()
        n='crates/banto-ai/README.md';changes[n]=(ROOT/n).read_text()+'''\n## 研究用FMA拡張\n\n非defaultの `fma-extension` featureで公開Burn backend extensionのfinite f32 FMAと幅64のreference-order LayerNormを利用できる。人工forwardとgraph参加、局所49入力のbit一致は確認済み。backwardはコードをcompileしただけで未検証。SmallForecasterへの一律接続は元R1基準で中間3点が未達となり取り消したため、featureを有効にしても現在のSmallForecasterは従来のnormを使う。[採否と保存結果](../../docs/results/banto-ai-rust-r1-fma-extension-2026-10-16.md)を参照。FMAはshape/dtype/device-context不一致をError、非有限入力/結果をkernel panicで拒否する研究APIである。\n'''
        sources=list(dict.fromkeys([Path(__file__),*source_files(),*[ROOT/'tools/public-data'/n for n in ['rust_r1_fma_fixture.py','rust_r1_fma_harness_repair.py','rust_r1_fma_model.py','rust_r1_fma_restore.py','rust_r1_compare.py']],ROOT/'examples/configs/rust-r1-fma-extension-20261016.json',ROOT/'examples/configs/rust-r1-fma-model-20261016.json',ROOT/'tools/verification_records.py']))
        out.sources(sources);out.json('phase.json',phase);out.json('root-pins.json',pins);out.json('resources.json',resources);out.json('prefix-identity.json',prefix);out.json('candidate-failures.json',failures)
        out.json('package-identity.json',{'before':sorted(baseline),'after':sorted(extended),'Cargo_lock_sha256':digest(ROOT/'Cargo.lock'),'default_features':[]})
        evidence=ROOT/'artifacts/rust-r1-fma-results-20261016-evidence'
        with EvidenceStore(evidence) as store:
            store.write_json('phase',phase);store.write_json('root-pins',pins);store.write_json('prior-root-pins',oldpins);store.write_json('document-paths',list(changes))
            for i,p in enumerate(sources):store.write_bytes(f'source-{i}',p.read_bytes())
            for i,name in enumerate(changes):
                if (ROOT/name).exists():store.write_bytes(f'before-{i}',(ROOT/name).read_bytes())
            for name,value in changes.items():(ROOT/name).write_text(value)
            for i,name in enumerate(changes):store.write_bytes(f'after-{i}',(ROOT/name).read_bytes())
            for i,name in enumerate(names):
                for j,p in enumerate(sorted((ROOT/'artifacts'/name).iterdir())):
                    if p.suffix!='.bin':store.write_bytes(f'root-{i}-{j}',p.read_bytes())
            for target in re.findall(r'\]\(([^)]+)\)',text):assert ((ROOT/report).parent/target).exists(),target
            for p in pins:assert validate_root(ROOT/p['root'])['closure_sha256']==p['closure_sha256']
            for p in oldpins:assert digest(ROOT/p['root']/'root-closed.json')==p['closure_sha256']
            assert digest(ROOT/'crates/banto-ai/src/model.rs')=='acefec42e7506d807f7deae22269f30f9bf409a8c8cf9d1ddb59c2ef6af7fa80'
            store.write_terminal('terminal',{'exit':0,'state':'FMA primitive retained opt-in; model candidate rejected and restored; R1 incomplete; no R2','resources':check.check()})
        out.json('evidence-readback.json',verify_evidence(evidence,'complete'));out.json('summary.json',{**phase,'resources':check.check()})
        print(json.dumps({'published':True,'primitive_forward_pass':True,'candidate_adopted':False,'model_restored':True,'R1_complete':False}));status='complete'
    finally:out.close(status)


if __name__=='__main__':main()
