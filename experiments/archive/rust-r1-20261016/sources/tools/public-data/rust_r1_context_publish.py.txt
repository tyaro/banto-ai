"""Publish the verified context diagnosis and rejected combined candidate."""
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
from rust_r1_moments_audit import metrics
from verification_records import EvidenceStore
from care_rust_r0_close import verify_evidence

def main():
    out=Files(ROOT/'artifacts/rust-r1-context-results-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        names=['rust-r1-context-source-20261016','rust-r1-context-source-20261016-records','rust-r1-context-declaration-20261016','rust-r1-context-declaration-20261016-records','rust-r1-context-audit-20261016','rust-r1-context-audit-20261016-records','rust-r1-context-model-declaration-20261016','rust-r1-context-model-declaration-20261016-records','rust-r1-context-format-20261016','rust-r1-context-local-kernel-20261016','rust-r1-context-local-kernel-20261016-records','rust-r1-context-local-comparison-20261016','rust-r1-context-local-comparison-20261016-records','rust-r1-context-model-hook-20261016','rust-r1-context-model-hook-20261016-records','rust-r1-context-model-tests-20261016','rust-r1-context-predictions-20261016','rust-r1-context-predictions-20261016-records','rust-r1-context-full-comparison-20261016','rust-r1-context-full-comparison-20261016-records','rust-r1-context-model-decision-20261016','rust-r1-context-model-decision-20261016-records','rust-r1-context-tree-20261016','rust-r1-context-features-20261016']
        pins=[validate_root(ROOT/'artifacts'/n) for n in names]
        def read(name,file='summary.json'):return json.loads((ROOT/'artifacts'/name/file).read_bytes())
        audit=read('rust-r1-context-audit-20261016');local=read('rust-r1-context-local-comparison-20261016');full=read('rust-r1-context-full-comparison-20261016');decision=read('rust-r1-context-model-decision-20261016')
        assert audit['local_gate_pass'] and audit['rows']==63 and local['bit_exact_comparisons']==84 and local['tracked_outputs']==28
        assert full['elements_compared']==389214 and not full['parity_pass'] and full['failing_elements']==1
        assert decision['model_restored_byte_exact'] and not decision['candidate_adopted']
        assert digest(ROOT/'crates/banto-ai/src/model.rs')=='acefec42e7506d807f7deae22269f30f9bf409a8c8cf9d1ddb59c2ef6af7fa80'
        assert digest(ROOT/'Cargo.lock')=='3e839d59923988b78155e1ed785d8f5f56fda9e072a69f64e52ea2e8e96f11e5'
        assert digest(ROOT/'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json')=='bd5c962c711decbad2e590af71ed9474d1f6256351571d3b16a8e3ada047c57a'
        package=tomllib.loads((ROOT/'crates/banto-ai/Cargo.toml').read_text());assert package['features'].get('default',[])==[]
        assert package['features']['reference-normalization']==['fma-extension']
        def packages(p):return set(tuple(m.groups()) for line in p.read_text().splitlines() if (m:=re.match(r'^(\S+) v([^ ]+)',line)))
        before=packages(ROOT/'artifacts/rust-r1-tree-20261016/stdout.txt');after=packages(ROOT/'artifacts/rust-r1-context-tree-20261016/stdout.txt');assert before==after and len(after)==154
        features=(ROOT/'artifacts/rust-r1-context-features-20261016/stdout.txt').read_text();assert 'burn-flex feature "simd"' not in features and 'burn-flex feature "rayon"' not in features
        tests=(ROOT/'artifacts/rust-r1-context-model-tests-20261016/stdout.txt').read_text();assert '2 passed; 0 failed' in tests and '1 passed; 0 failed' in tests
        resources={}
        for name in names:
            path=ROOT/'artifacts'/name/'exit.json'
            if not path.exists():continue
            e=json.loads(path.read_bytes());assert e['returncode']==(1 if name=='rust-r1-context-full-comparison-20261016-records' else 0)
            g=e['sampled_group_peak'];assert e['elapsed_seconds']<870 and max(g['monitor_inclusive_footprint'],g['monitor_inclusive_rss'],e['child_wait_peak_rss_bytes'])<2*1024**3 and e['sampled_cache_bytes']<1536*1024**2
            resources[name]=e
        prior=['rust-r1-python-reference-20261016','rust-r1-burn-predictions3-20261016','rust-r1-layer-comparison-20261016']
        priorpins=[validate_root(ROOT/'artifacts'/n) for n in prior]
        pred=ROOT/'artifacts/rust-r1-context-predictions-20261016';ref=ROOT/'artifacts'/prior[0];old=ROOT/'artifacts'/prior[1]
        ms=[json.loads((p/f).read_bytes()) for p,f in [(ref,'fixtures.json'),(pred,'traces-layout.json'),(old,'traces-layout.json')]]
        raws=[(p/f).read_bytes() for p,f in [(ref,'python-traces.bin'),(pred,'rust-traces.bin'),(old,'rust-traces.bin')]]
        prefix=[]
        for cases in zip(*(m['cases'] for m in ms),strict=True):
            assert len({c['id'] for c in cases})==1
            maps=[{e['name']:e for e in c['traces']} for c in cases]
            for name in ['context_center','context_scale','normalized_context','patch','tokens']:
                values=[floats(raw,m[name]) for raw,m in zip(raws,maps,strict=True)]
                current=metrics(values[0],values[1],True);base=metrics(values[0],values[2],True)
                prefix.append({'case':cases[0]['id'],'node':name,'candidate':current,'baseline':base})
                if name in ['context_center','context_scale','normalized_context']:assert current['bit_mismatches']==0
        assert len(prefix)==35
        comps=read('rust-r1-context-full-comparison-20261016','tensor-comparisons.json');failures=[r for r in comps if r['failing_elements']]
        assert len(failures)==1 and failures[0]['case']=='train-last' and failures[0]['tensor']=='blocks.1' and failures[0]['failure_examples'][0]['index']==183
        assert all(r['failing_elements']==0 for r in comps if r['tensor'] in ['normalized_quantiles','quantiles'])
        assert all(next(r for r in prefix if r['case']==cid and r['node']=='patch')['candidate']['bit_mismatches']>0 for cid in ['train-first','train-last'])
        oldnodes=read('rust-r1-layer-comparison-20261016','node-comparisons.json')
        local_linear=[r for r in oldnodes if r['family'] in ['patch','attention_projection','attention_output_projection','ff_linear','head']]
        assert len(local_linear)==154
        phase={'context_source_audit_pass':True,'Rust_context_plain_autodiff_forward_pass':True,'graph_participation_pass':True,'backward_verified':False,'model_candidates':1,'candidate_adopted':False,'candidate_failing_elements':1,'model_restored_byte_exact':True,'baseline_failing_elements':1,'R1_complete':False,'R2_started':False,'training':False,'tolerance_changed':False,'CARE_or_demand2015_reevaluation':False}
        maxfp=max(e['sampled_group_peak']['monitor_inclusive_footprint'] for e in resources.values());maxrss=max(max(e['sampled_group_peak']['monitor_inclusive_rss'],e['child_wait_peak_rss_bytes']) for e in resources.values());cache=disk_bytes();assert cache<1536*1024**2
        report='docs/results/banto-ai-rust-r1-context-normalization-2026-10-16.md'
        text=f'''# Rust R1 — 初期contextのbit一致、全体候補は1点未達（2026-10-16）

**初期contextの平均・標準偏差・尺度・正規化入力の差を説明し、Rustの通常/自動微分forwardで参照と全bit一致した。ただし既知のLayerNorm修正と合わせた全体候補は389,214要素中1点が元の許容差を超え、不採用としてmodel.rsを元bytesへ戻した。** R1未合格・R2未開始。最終予測だけの通過で中間値条件を変更しない。

## ソースで特定した違い

インストール済みtorchのgit版 `08187d9e0fba026dc8217405802ab5381dc88d90` と同じ公式ソースを取得し、URL・bytes・hashを固定した。タグ名だけで版を推測しない。各ソースはartifacts/rust-r1-context-source-20261016へ保存した。

- CPU meanはfloat32のsum_out後に128で除算する。[ReduceOps.cpp](https://github.com/pytorch/pytorch/blob/08187d9e0fba026dc8217405802ab5381dc88d90/aten/src/ATen/native/ReduceOps.cpp)。
- 連続幅128、NEON4laneでは4ベクトル×各8回の逐次加算を行い、ベクトル4本・lane4個を順に統合する。[SumKernel.cpp](https://github.com/pytorch/pytorch/blob/08187d9e0fba026dc8217405802ab5381dc88d90/aten/src/ATen/native/cpu/SumKernel.cpp)。サイズ8はcascadeの最小level16より小さい。既存Rustの隣接pair treeとは加算順が異なる。
- std_cpuはmeanとは独立にWelfordData<double>を使う。[ReduceOpsKernel.cpp](https://github.com/pytorch/pytorch/blob/08187d9e0fba026dc8217405802ab5381dc88d90/aten/src/ATen/native/cpu/ReduceOpsKernel.cpp)、インストール済みReduce.h/SharedReduceOps.h。各128値行は単一threadの逐次処理で、float64で人口分散とsqrtを計算してからfloat32へ戻す。現行Rustは丸めたfloat32 meanからcentered varianceを計算していた。

これはLayerNormのfloat32/vector Welfordとは別の契約である。今回のfloat64は参照stdが実際に使う型を表現するもので、f32 FMAをf64で代用するものではない。WelfordのC++積和のバイナリ縮約は今回調査しておらず、非縮約のsource表現が固定入力のf32結果を再現した事実までを報告する。

## 事前固定した局所検証

[診断条件](../../examples/configs/rust-r1-context-audit-20261016.json)を閉鎖保存後、既存train先頭/末尾batchとzero/constant/floor前後3caseだけを使った。補助のnative context pipelineを各case1回実行し、元のmean/scale/normalized anchor21組のbytes一致を確認した。元の参照rootは再生成していない。標準偏差のfloor前値だけ補助保存し、全体model forwardやlabel/target読取りは0。

| 確認 | 結果 |
| --- | --- |
| scalarで現行Rustを再現 | 元21anchorのbytes一致 |
| ソース順のmean/raw std/scale | 各63値、全bit一致 |
| ソース順のnormalized context | 8,064値、全bit一致 |
| Rust baseline / plain候補 / Autodiff候補 | 全84比較のbytes一致 |
| Autodiff graph参加・入力不変 | 4出力×7case=28箇所、入力不変 |
| backward・gradient・学習 | 未実行、正しさ未認定 |

Rustの `context::reference_context` は公開tensorのslice/reshape/cast/通常演算だけで表現した。float64 Welfordを含めてgraphを保ち、host読戻し・値の注入・unsafe/private bridgeを使わない。読み出しは診断exampleの出力境界だけ。zeroやfloorを理由に入力を欠測へ変えない。

## 全体の有限候補と採否

[モデル接続条件](../../examples/configs/rust-r1-context-model-20261016.json)をRust実装前に固定した。今回の一般候補は、独立に根拠を得た初期contextと既存のbinary順LayerNormを一律に合わせる1方式だけ。LayerNormだけの過去の不採用候補を再試行したものではなく、当時不変だった上流入力を今回初めて修正した。contextだけの追加full候補や結果に応じた混合は行わなかった。

局所gate後、既存3テストpass、固定7caseの全体forwardを1回実行した。元の23anchor/389,214要素の比較は次の1点が未達。

| 項目 | 値 |
| --- | --- |
| case / tensor / index | train-last / blocks.1 / 183 |
| Python | 0.004164397716522217 |
| Rust候補 | 0.0041619837284088135 |
| 絶対差 | 2.4139881134033203e-6 |
| 元の許容差 | 2.0832879543304442e-6 |
| 合計 | 1 / 389,214要素 |

正規化後/元単位の最終分位点は各6,048値が元許容差内、全caseで有限・分位点順序を維持。しかし全体の元gateは不通過で、候補を採用しない。結果rootはcomplete/parity=false、比較command exit1という科学的負の結果であり、保存失敗ではない。

model.rsはSHA `acefec42e7506d807f7deae22269f30f9bf409a8c8cf9d1ddb59c2ef6af7fa80` へbytes復元した。現在の安定版は旧train-last index3450の累積1点未達で、今回の候補index183と区別する。`reference-normalization` は非defaultでcontext API/診断を公開するだけであり、featureを有効にしても復元後のSmallForecasterの処理は切り替わらない。FMAも研究APIのまま。Cargo.lockと有効package154件の集合は不変、Flex SIMD/rayonを追加せず、依存download0。

## 次の工程

保存済みの今回のtracesでは、context3anchor×7caseはPythonと全bit一致した。その直後のpatchでは両train batchにbit差が残り、初期正規化だけでは消えない差がある。patchはlinearのmatmulとbiasを含む境界であり、この保存結果だけでmatmul・bias・layoutのどれかへ単独帰属しない。prefix35組の候補/旧版のbits・SSEを同結果rootのprefix-comparisons.jsonへ保存した。

次はpatchのlinear境界を出発点に、参照CPU/Flexのmatmul・biasとlayoutのソースを確認し、一般的に直せる差があるか判断する。閉鎖済み55node診断の局所差も再利用し、全層再生や同じmodel候補のfull比較を反復しない。同一operandの有限比較・採否条件が固定できるまでは新kernel/full forwardを起動しない。index183へ合わせる分岐・許容差緩和・参照再生成は禁止。R1通過前にR2学習へ進めない。

保全・点検支援を第一優先とし、自作モデルの産業/需要での実用性、学習とoptimizer保存再開を含むRust移植の目的は維持。CARE test/需要2015再評価、実学習、下流repo変更、push、製品採用0。需要は2014以前調整、同休業mean28、四季過小/過大非増加、観測のみ/欠測0評価分離を維持。heartbeat PAUSED。Windows native/OS依存suiteは今回も未実行でMac共通CPU確認と分ける。

## 資源と保存

親900秒/子870秒、physical footprint・peak RSS各2GiB、build cache+target1.5GiBと旧artifact/EvidenceStore/stdio枠を維持。全単位で上限内、監視込み最大footprint {maxfp:,}B、RSS系最大 {maxrss:,}B、最終cache+target {cache:,}B。process group sampleは短命process等の捕捉限界がありhard OS capではない。全source/stdio/exit/state/closureと文書前後をartifacts/rust-r1-context-results-20261016-evidenceへ保存し、旧roots・失敗・既存変更を保持した。
'''
        headline='初期contextのmean/raw std/scale各63値とnormalized8,064値が参照bits一致。Rust plain/Autodiffを含む84局所比較もbytes一致。contextと既知LayerNormを合わせた一律候補は全体389,214要素中1点未達で不採用、model元bytes復元。'
        changes={report:text}
        h='docs/current-handoff.md';changes[h]='## 最新 — 初期context差を解明、全体候補は1点未達・復元（2026-10-16）\n\n[結果と採否](results/banto-ai-rust-r1-context-normalization-2026-10-16.md)。'+headline+' 安定版は旧index3450の1点未達、候補はindex183であり区別。R1未合格/R2未開始、許容差/参照/weights/default/Cargo.lock不変、有効package154も同一。\n\n次は保存済みで初期3anchor一致後に最初のbit差が出るpatchのlinear（matmul/bias/layout）のソースを確認し、一般方式の根拠を判断。閉鎖した全層再生・同候補のfull比較を繰り返さず、同一operandの有限条件が固定できるまで新kernel/full forwardをしない。float64 Welfordのbinary縮約やbackwardは今回未認定。全証跡/文書前後はartifacts/rust-r1-context-results-20261016-evidence。\n\n各2GiB/build1.5GiB/時間/保存枠、旧成果/失敗/closed roots保護、保全第一/Rust学習目的、需要2015停止/2014以前調整/同休業mean28/四季両側非増加/観測欠測0分離、Windows別検証、heartbeat PAUSEDを維持。以下は旧記録。\n\n---\n\n'+(ROOT/h).read_text()
        for name,marker,entry in [('docs/results/README.md','## Rustクレートの移植\n','- [Rust R1 初期contextのbit一致と全体候補の採否](banto-ai-rust-r1-context-normalization-2026-10-16.md) — 局所84組一致、全体1点未達でmodel復元。'),('docs/research/README.md','## 文書\n','- [Rust R1 context差のソース診断と有限候補](../results/banto-ai-rust-r1-context-normalization-2026-10-16.md) — 独立f64 stdとf32 mean、全体gateは未通過。')]:
            beforetext=(ROOT/name).read_text();assert marker in beforetext;changes[name]=beforetext.replace(marker,marker+'\n'+entry+'\n',1)
        for name in ['docs/research/banto-ai-rust-implementation-plan-2026-10-16.md','docs/research/rust-small-forecaster-r0-2026-10-16.md']:
            changes[name]=re.sub(r'^状態:.*$','状態: R1a/既存3テストpass。初期contextの参照bits一致をRust plain/Autodiffで確認。context+LayerNorm候補は全体1点未達で不採用・model復元。安定版R1累積1点未達/R2停止。[最新結果](../results/banto-ai-rust-r1-context-normalization-2026-10-16.md)。2026-10-16 JST。',(ROOT/name).read_text(),count=1,flags=re.M)
        name='docs/research/research-roadmap.md';changes[name]='## 現在 — context差を解明、全体は未達（2026-10-16）\n\n[結果](../results/banto-ai-rust-r1-context-normalization-2026-10-16.md)。'+headline+' R1未合格/R2停止。次はpatchのlinear境界のソース確認、同一評価は反復しない。以下は旧記録。\n\n---\n\n'+(ROOT/name).read_text()
        name='crates/banto-ai/README.md';changes[name]=(ROOT/name).read_text()+'''\n## 研究用context正規化\n\n非defaultの `reference-normalization` featureで `context::reference_context` と診断exampleを公開する。固定幅128のCPU参照順f32 meanと独立f64 Welford stdをtensor graph内で計算し、固定7caseのplain/Autodiff forwardは参照bits一致。backward/gradientは未検証。SmallForecasterへのcontext+LayerNorm接続候補は元R1全体で1点未達となり取り消したため、このfeatureで現在のSmallForecasterの算術は切り替わらない。[採否](../../docs/results/banto-ai-rust-r1-context-normalization-2026-10-16.md)を参照。\n'''
        sources=list(dict.fromkeys([Path(__file__),*source_files(),*[ROOT/'tools/public-data'/n for n in ['rust_r1_context_audit.py','rust_r1_context_model.py','rust_r1_context_decision.py','rust_r1_compare.py','rust_r1_moments_audit.py']],ROOT/'examples/configs/rust-r1-context-audit-20261016.json',ROOT/'examples/configs/rust-r1-context-model-20261016.json',ROOT/'tools/verification_records.py']))
        out.sources(sources);out.json('phase.json',phase);out.json('root-pins.json',pins);out.json('prior-root-pins.json',priorpins);out.json('resources.json',resources);out.json('prefix-comparisons.json',prefix);out.json('candidate-failures.json',failures);out.json('prior-linear-diagnosis.json',local_linear);out.json('package-identity.json',{'before':sorted(before),'after':sorted(after),'default_features':[]})
        evidence=ROOT/'artifacts/rust-r1-context-results-20261016-evidence'
        with EvidenceStore(evidence) as store:
            store.write_json('phase',phase);store.write_json('root-pins',pins);store.write_json('prior-root-pins',priorpins);store.write_json('document-paths',list(changes))
            for i,p in enumerate(sources):store.write_bytes(f'source-{i}',p.read_bytes())
            for i,name in enumerate(changes):
                if (ROOT/name).exists():store.write_bytes(f'before-{i}',(ROOT/name).read_bytes())
            for name,value in changes.items():(ROOT/name).write_text(value)
            for i,name in enumerate(changes):store.write_bytes(f'after-{i}',(ROOT/name).read_bytes())
            for i,name in enumerate(names):
                for j,p in enumerate(sorted((ROOT/'artifacts'/name).iterdir())):
                    if p.suffix!='.bin':store.write_bytes(f'root-{i}-{j}',p.read_bytes())
            for target in re.findall(r'\]\(([^)]+)\)',text):
                if not target.startswith('https://'):assert ((ROOT/report).parent/target).exists(),target
            for pin in pins+priorpins:assert validate_root(ROOT/pin['root'])['closure_sha256']==pin['closure_sha256']
            store.write_json('documents-after',[{'path':name,'sha256':digest(ROOT/name)} for name in changes])
        verify_evidence(evidence,'complete');out.json('summary.json',{**phase,'documents':len(changes),'verified_roots':len(pins),'resources':check.check()});print(json.dumps({'published':True,'candidate_adopted':False,'R1_complete':False,'verified_roots':len(pins)}));status='complete'
    finally:out.close(status)

if __name__=='__main__':main()
