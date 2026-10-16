"""Close one non-improving GEMM-bias candidate without running a full model."""
import json
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
from care_rust_r0_close import verify_evidence
from verification_records import EvidenceStore

def main():
    out=Files(ROOT/'artifacts/rust-r1-fused-linear-results-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        names=['rust-r1-fused-linear-declaration-20261016','rust-r1-fused-linear-declaration-20261016-records','rust-r1-fused-linear-format-20261016','rust-r1-fused-linear-lock-refresh-20261016','rust-r1-fused-linear-features-20261016','rust-r1-fused-linear-dependencies-20261016','rust-r1-fused-linear-dependencies-20261016-records','rust-r1-fused-linear-probe-20261016','rust-r1-fused-linear-probe-20261016-records','rust-r1-fused-linear-local-kernel-20261016','rust-r1-fused-linear-local-kernel-20261016-records','rust-r1-fused-linear-local-comparison-20261016','rust-r1-fused-linear-local-comparison-20261016-records']
        pins=[validate_root(ROOT/'artifacts'/n) for n in names]
        def read(n,file='summary.json'):return json.loads((ROOT/'artifacts'/n/file).read_bytes())
        probe=read('rust-r1-fused-linear-probe-20261016');local=read('rust-r1-fused-linear-local-comparison-20261016');cases=read('rust-r1-fused-linear-local-comparison-20261016','case-comparisons.json')
        assert probe['exact_elements']==74 and probe['boundary_rejections']==13 and probe['parent_only_graph_routes']==3 and probe['high_rank_wrapper'] and probe['backward_calls']==0
        assert not local['local_gate_pass'] and local['candidate_equals_baseline_bytes']==154 and local['elements']==465696 and local['candidate_failing_elements']==0
        assert local['baseline_SSE']==local['candidate_SSE'] and local['case_nonincrease_count']==7 and local['full_forward']==0
        declaration=ROOT/'artifacts/rust-r1-fused-linear-declaration-20261016';verify_closed(declaration)
        assert (ROOT/'crates/banto-ai/src/model.rs').read_bytes()==(declaration/'model.rs.before').read_bytes()
        package=tomllib.loads((ROOT/'crates/banto-ai/Cargo.toml').read_text());assert package['features'].get('default',[])==[] and package['dependencies']['gemm']=={'version':'=0.19.0','default-features':False,'optional':True}
        # Recheck immutable numerical inputs/implementation before document updates.
        before=read('rust-r1-fused-linear-dependencies-20261016','source-pins-before-kernels.json')
        for p in before:assert digest(ROOT/p['path'])==p['sha256']
        priorpins=read('rust-r1-fused-linear-declaration-20261016','root-pins.json')
        for p in priorpins:verify_closed(ROOT/p['path']);assert digest(ROOT/p['path']/'root-closed.json')==p['sha256']
        resources={}
        for name in names:
            p=ROOT/'artifacts'/name/'exit.json'
            if not p.exists():continue
            e=json.loads(p.read_bytes());g=e['sampled_group_peak'];assert e['returncode']==(1 if name=='rust-r1-fused-linear-local-comparison-20261016-records' else 0)
            assert e['elapsed_seconds']<870 and e['sampled_cache_bytes']<1536*1024**2 and max(g['monitor_inclusive_footprint'],g['monitor_inclusive_rss'],e['child_wait_peak_rss_bytes'])<2*1024**3;resources[name]=e
        registry=ROOT/'environments/rust-cpu/cargo-home/registry/src/index.crates.io-1949cf8c6b5b557f'
        micro=registry/'gemm-common-0.19.0/src/microkernel.rs'
        text=micro.read_text();assert 'let mut accum_storage = [[splat(::core::mem::zeroed()); $mr_div_n]; $nr];' in text and '*dst_ij = scalar_mul_add(beta, *src_ij, *dst_ij);' in text
        lines=text.splitlines();evidence_lines=[]
        for lo,hi in [(408,428),(630,700)]:evidence_lines.append({'source':str(micro.relative_to(ROOT)),'source_sha256':digest(micro),'first_line':lo,'last_line':hi,'text':'\n'.join(lines[lo-1:hi]),'runtime_hot_path_proved':False})
        sources=list(dict.fromkeys([Path(__file__),*source_files(),*[ROOT/'tools/public-data'/n for n in ['rust_r1_fused_linear_fixture.py','rust_r1_fused_linear_dependencies.py','rust_r1_fused_linear_compare.py','rust_r1_compare.py','rust_r1_moments_audit.py']],ROOT/'examples/configs/rust-r1-fused-linear-admission-20261016.json',ROOT/'docs/research/rust-fused-linear-safety-2026-10-16.md',ROOT/'tools/verification_records.py',micro,registry/'gemm-common-0.19.0/src/horizontal_microkernel.rs',registry/'gemm-common-0.19.0/src/gemm.rs',registry/'gemm-f32-0.19.0/src/microkernel.rs',registry/'gemm-f32-0.19.0/src/gemm.rs',registry/'gemm-0.19.0/src/gemm.rs',registry/'burn-flex-0.22.0/src/tensor.rs',registry/'burn-flex-0.22.0/src/layout.rs',registry/'burn-flex-0.22.0/src/ops/matmul.rs']))
        phase={'candidate':'pure-Rust existing GEMM with bias destination/read_dst=true','candidate_count':1,'artificial_forward_pass':True,'graph_participation_pass':True,'backward_verified':False,'local_gate_pass':False,'decision':'rejected: all154 outputs byte-identical to current baseline; no strict SSE decrease','candidate_adopted':False,'primitive_retained_opt_in':True,'model_unchanged_bytes':True,'default_unchanged':True,'package_set_unchanged':154,'effective_features_unchanged':True,'lock_change':'root dependency edge to existing gemm only','full_forward':0,'R1_complete':False,'R2_started':False,'training':False,'tolerance_changed':False,'CARE_or_demand2015_reevaluation':False}
        maxfp=max(e['sampled_group_peak']['monitor_inclusive_footprint'] for e in resources.values());maxrss=max(max(e['sampled_group_peak']['monitor_inclusive_rss'],e['child_wait_peak_rss_bytes']) for e in resources.values());cache=disk_bytes();assert cache<1536*1024**2
        report='docs/results/banto-ai-rust-r1-fused-linear-2026-10-16.md'
        body=f'''# Rust R1 — pure-Rust fused linear候補は改善なしで不採用（2026-10-16）

**fused linearを公開backend extensionで実装し、独立人工8caseの通常/Autodiff forward、graph参加、13拒否条件を通過した。一方、保存済み154linearの465,696値は現行baselineと全bit一致し、参照との差が減らなかった。事前条件のSSE厳密減少を満たさず不採用とし、モデル全体の再実行は0。** model.rs/default/許容差は不変、R1は安定版の累積1点未達、R2未開始。

## 先に固定した方式と保護

[受入条件](../../examples/configs/rust-r1-fused-linear-admission-20261016.json)を維持し、実装・依存変更より前に `artifacts/rust-r1-fused-linear-declaration-20261016` へ元model/lib/Cargo.toml/Cargo.lock、既存rootsのclosure、独立人工fixtureを保存した。fixtureはPython Fractionで計算したexact integer/dyadic結果がfloat32で厳密表現できることを検査している。Rustの候補出力を見て期待値や計算順を変えていない。

候補は既存gemm0.19.0の同じfloat32/stride/orientation/Parallelism::Noneで、全出力を行broadcast biasへ初期化しread_dst=true・出力係数1・積係数1とした1方式。高水準APIは公開reshape/dispatchだけでgraphを保つ。新backend、Accelerate FFI、padding、f64 matmul、packing調整、scalar-dot代替、ケース/点別switchは0。

`fused-linear-extension` は非defaultで既存fma-extensionとoptional gemmを有効にする。gemmの直接依存はexact0.19.0/default-features=false。offline lock refreshは一度、Cargo.lockの差はbanto-ai root依存に既存gemm edgeが1本増えた箇所だけ。全package/version集合154と有効dependency feature集合は前後で同一、SIMD/rayon/vendor機能追加やdownloadはない。元のlock bytesも閉鎖保存した。

## 実装と安全性

[安全性の説明](../research/rust-fused-linear-safety-2026-10-16.md)とcode内SAFETYをGEMM前に保存した。rank/dtype/shape/device/autodiff/checkpointを検査し、m1..120/k1..128/n1..128に制限する。primitive側でも検査し、公開storage/layoutから非負strideとstart offsetを読み、全index/byte最大値をchecked arithmeticで証明してからpointerを作る。weightをcontiguousへ変換して別の算術候補にしない。

出力は独立した新規allocationで、全m×n値をbias初期化してからread_dstを許可する。immutable input同士の共有は読取りだけ、出力は他とaliasせず、連続strideは一意に書く。unsafeはこの検査後の公開gemm呼出し1箇所に隔離し、private bridge/表現変換は使わない。範囲・負stride・非有限はGEMM前に拒否し、overflowなど非有限出力も拒否する。

Autodiffは三parent guardをchild登録まで保持し、x/weightをstateへ残す。dx=dY@W.T、dW=x.T@dY、db=sum_rows(dY)のコードは既存backend演算でcompile済み。**今回確認したのはforwardとgraph参加で、backward・gradient・optimizerの数値正しさは未実行/未認定**。

## 人工確認

| 項目 | 結果 |
| --- | --- |
| ordinary / zero input / zero weight / mixed sign / broadcast / transposed weight / offset input / dyadic | 固定8case |
| plain・Autodiff | 各37値、合計74値の期待bits一致 |
| 親がxだけ/weightだけ/biasだけ | 各経路でgraph参加と期待bits一致 |
| rank4 wrapper・入力/weight/bias不変 | 確認 |
| shape・bias長・empty・dtype・context・m/k/n上限 | 8拒否 |
| input/weight/bias非有限、出力overflow、weight負stride | 5拒否 |
| backward呼出し | 0 |

拒否5件のkernel panicはcatchした意図的境界試験であり、stderrへ保持した。probe自体はexit0。compile失敗や科学的retryはなく、同じfixture1回の判定で完了した。

## 保存済み全154linearの局所比較

人工gate後、新候補だけをpatch7、attention projection84、output projection28、FF28、head7へ各1回適用した。入力は閉鎖済みPPの発行/時点を持つ既存値、比較先は同じ閉鎖済みPPとRP。旧baselineのkernelや55node全層再生を再実行していない。variate q/k/vは既存sourceと同じseries/time入替え、weight transposeのstrideも維持した。

| 判定 | 結果 |
| --- | --- |
| 比較 | 154組 / 465,696値 |
| 候補と現行RPのbytes一致 | 154 / 154組 |
| 元許容差の超過・非有限 | 0 |
| baseline SSE | {local['baseline_SSE']:.17g} |
| candidate SSE | {local['candidate_SSE']:.17g} |
| 各caseの合計SSE非増加 | 7 / 7 |
| 合計SSEの厳密減少 | **なし、不採用** |

'''
        for c in cases:body+=f"- {c['case']}: baseline=candidate SSE {c['baseline_SSE']:.17g}。\n"
        body+='''
全154組が現行bytesと同じなので、train patchで見つけた7,241値のfused/別加算差も、人工floorのmatmul差も今回の方式では減っていない。局所の許容差内だけを採用理由にせず、事前の厳密改善条件を維持した。比較結果rootはcomplete/local_gate=false、commandは科学的負の結果を示すexit1として保存した。

## 改善しなかった理由と次工程

gemm-common0.19.0のreal microkernel sourceでは、積のaccumulatorをゼロで開始し、Kループを終えてからdestinationを組み込むepilogueを持つ。alpha_status1のscalar経路は `scalar_mul_add(beta, accumulated_product, old_destination)`、vector経路も同様。今回はbeta1なので、既に丸められた積へのbiasの最終加算となり得る。GEMMのdestinationへbiasを渡すAPIと、積の累積中にbiasを保持する計算順は同義ではない。

該当sourceの行番号/hash/原文を結果rootのgemm-epilogue-source.jsonへ保存した。今回の実行でどのmicrokernel命令を通ったかはtraceしておらず、これだけで全backend/寸法のbit同一性を証明したとはしない。固定154組が同一だった事実と、それを説明するsource上の順序を分けて報告する。

この候補のkernel/全体を反復せず、モデルhookを置かない。primitiveは非defaultの研究APIとして保持する。次は参照SGEMMのbias統合位置とサイズ依存経路を読取り監査する条件を固定する。実際にloadされたsymbolと対象範囲/byte上限を先に決め、一般方式を支持する根拠が得られるまで別の丸め順・bias-first scalar候補・vendor FFIを起動しない。単独加算の置換や、既読の失敗1点に合わせた調整も行わない。

## 現在の状態と資源・OS分離

model.rsは宣言前とbytes同一、SHA acefec42e7506d807f7deae22269f30f9bf409a8c8cf9d1ddb59c2ef6af7fa80。全体7case・既存baseline・学習/CARE test/需要2015再評価は0。今回の局所gateが不通過のため、全体接続後の既存3テスト工程へも進めていない。過去の既存3テストpassを今回の再実行とは扱わない。R1未達/R2停止、許容差・参照・weights/defaultは維持。

保全・点検支援第一、自作モデルの産業/需要での実用性、Rustでの学習/optimizer保存再開の目的を維持。需要は2014以前だけ調整、同休業mean28、四季平均の過小/過大非増加、観測のみ/欠測0分離。下流編集・Git push・製品採用0、heartbeat PAUSED。新primitiveはOS専用bindingを含まないが実行確認はMacのみ、Windows native/OS依存suiteは別途未実行。

'''
        body+=f'全単位が親900/子870秒、physical footprint・peak RSS各2GiB、build cache+target1.5GiBと旧artifact/EvidenceStore/stdio枠内。最大監視込みfootprint {maxfp:,}B、最大RSS系 {maxrss:,}B、最終cache+target {cache:,}B。process group sampleには短命process等の捕捉限界がありhard OS capではない。全source/stdio/exit/state/closure、独立fixture、依存前後、source説明、集計と文書前後をartifacts/rust-r1-fused-linear-results-20261016-evidenceへ保存し、旧成果/失敗/closed rootsを保持した。\n'
        headline='公開extensionでpure-Rust GEMM bias初期化を実装。人工8case/74値・graph・13拒否はpassだが、全154linear/465,696値が現行baselineとbytes一致しSSE減少0で不採用。model/default不変、full forward0。'
        changes={report:body}
        n='docs/current-handoff.md';changes[n]='## 最新 — fused linearは人工pass・改善なしで不採用（2026-10-16）\n\n[結果と採否](results/banto-ai-rust-r1-fused-linear-2026-10-16.md)。'+headline+' R1は安定版累積1点未達/R2停止、許容差/参照/weights維持。Cargo.lockは既存gemmへのroot edge1本だけ追加、package154/有効feature集合は不変。primitiveは非default研究API、backwardはcompileのみで未検証。\n\nGEMM sourceは積をゼロaccumulatorで計算後にdestinationをepilogueで統合し、API上のbias初期化だけでは参照の丸め順を変えられない。実際のmicrokernel命令経路は未証明。次は参照SGEMMのbias統合位置/サイズ依存経路を読取り監査する条件を固定する。対象symbol/byte上限を決め、根拠が得られるまで新kernel/full forward/別のbias-first算術候補を起動しない。同候補・全55node・baseline再生を反復しない。全証跡/文書前後はartifacts/rust-r1-fused-linear-results-20261016-evidence。\n\n各2GiB/build1.5GiB/時間/保存枠、既存成果/失敗/closed roots保護、保全第一/Rust学習目的、需要2015停止/2014以前調整/同休業mean28/四季両側非増加/観測欠測0分離、Windows別検証、heartbeat PAUSED維持。以下は旧記録。\n\n---\n\n'+(ROOT/n).read_text()
        for n,marker,entry in [('docs/results/README.md','## Rustクレートの移植\n','- [Rust R1 pure-Rust fused linearの実装と不採用](banto-ai-rust-r1-fused-linear-2026-10-16.md) — 人工pass、154組がbaseline bytes同一で改善なし。'),('docs/research/README.md','## 文書\n','- [Rust fused linearの安全性](rust-fused-linear-safety-2026-10-16.md)・[局所比較と不採用](../results/banto-ai-rust-r1-fused-linear-2026-10-16.md) — 公開extension、stride/bounds証明とgraphを確認。')]:
            prior=(ROOT/n).read_text();assert marker in prior;changes[n]=prior.replace(marker,marker+'\n'+entry+'\n',1)
        for n in ['docs/research/banto-ai-rust-implementation-plan-2026-10-16.md','docs/research/rust-small-forecaster-r0-2026-10-16.md']:
            changes[n]=re.sub(r'^状態:.*$','状態: R1a済み/R1bは安定版の累積1点未達/R2停止。pure-Rust fused linearは人工8case pass、154局所がbaseline bytes同一・改善なしで不採用。model/default不変、次は参照SGEMMの読取り監査条件。[最新結果](../results/banto-ai-rust-r1-fused-linear-2026-10-16.md)。2026-10-16 JST。',(ROOT/n).read_text(),count=1,flags=re.M)
        n='docs/research/research-roadmap.md';changes[n]='## 現在 — fused linearは改善なしで不採用（2026-10-16）\n\n[結果](../results/banto-ai-rust-r1-fused-linear-2026-10-16.md)。'+headline+' R1未達/R2停止。次は参照SGEMMを読取り監査する条件の固定、根拠なしの丸め順探索はしない。以下は旧記録。\n\n---\n\n'+(ROOT/n).read_text()
        n='docs/research/rust-fused-linear-safety-2026-10-16.md';changes[n]='進捗（2026-10-16）: [人工forward/graphはpass、全154局所はbaseline bytes同一で改善なし・不採用](../results/banto-ai-rust-r1-fused-linear-2026-10-16.md)。primitiveは非default、model接続/全体forward/学習0。以下の安全性条件を保持する。\n\n'+(ROOT/n).read_text()
        n='crates/banto-ai/README.md';changes[n]=(ROOT/n).read_text()+'''\n## 研究用GEMM bias初期化\n\n非defaultの `fused-linear-extension` は既存pure-Rust gemm0.19.0を使うfinite_fused_linearを公開する。人工8caseのplain/Autodiff forward・graph・13拒否条件は確認済み。backwardはcompileのみで未検証。保存済み154linearは現行とbytes同一で改善しなかったため、SmallForecasterへ接続していない。[採否](../../docs/results/banto-ai-rust-r1-fused-linear-2026-10-16.md)と[安全性](../../docs/research/rust-fused-linear-safety-2026-10-16.md)を参照。metadata不一致はError、非有限/負stride/primitive範囲不正はkernel panicで拒否する研究API。\n'''
        out.sources(sources);out.json('phase.json',phase);out.json('root-pins.json',pins);out.json('prior-root-pins.json',priorpins);out.json('resources.json',resources);out.json('gemm-epilogue-source.json',evidence_lines);out.json('case-results.json',cases)
        evidence=ROOT/'artifacts/rust-r1-fused-linear-results-20261016-evidence'
        with EvidenceStore(evidence) as store:
            store.write_json('phase',phase);store.write_json('root-pins',pins);store.write_json('prior-root-pins',priorpins);store.write_json('document-paths',list(changes))
            for i,p in enumerate(sources):store.write_bytes(f'source-{i}',p.read_bytes())
            for i,n in enumerate(changes):
                if (ROOT/n).exists():store.write_bytes(f'before-{i}',(ROOT/n).read_bytes())
            for n,value in changes.items():(ROOT/n).write_text(value)
            for i,n in enumerate(changes):store.write_bytes(f'after-{i}',(ROOT/n).read_bytes())
            for i,name in enumerate(names):
                for j,p in enumerate(sorted((ROOT/'artifacts'/name).iterdir())):
                    if p.suffix!='.bin':store.write_bytes(f'root-{i}-{j}',p.read_bytes())
            for target in re.findall(r'\]\(([^)]+)\)',body):assert ((ROOT/report).parent/target).exists(),target
            for p in pins:assert validate_root(ROOT/p['root'])['closure_sha256']==p['closure_sha256']
            for p in priorpins:assert digest(ROOT/p['path']/'root-closed.json')==p['sha256']
            store.write_json('documents-after',[{'path':n,'sha256':digest(ROOT/n)} for n in changes])
        ev=verify_evidence(evidence,'complete');out.json('evidence-check.json',ev);out.json('summary.json',{**phase,'verified_roots':len(pins),'model_sha256':digest(ROOT/'crates/banto-ai/src/model.rs'),'resources':check.check()});print(json.dumps({'published':True,'candidate_adopted':False,'full_forward':0,'R1_complete':False,'evidence':ev}));status='complete'
    finally:out.close(status)

if __name__=='__main__':main()
