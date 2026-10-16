"""Publish finite linear attribution and the portable fused-linear admission."""
import json
import re
import sys
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
    out=Files(ROOT/'artifacts/rust-r1-linear-results-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        names=['rust-r1-linear-source-20261016','rust-r1-linear-source-20261016-records','rust-r1-linear-declaration-20261016','rust-r1-linear-declaration-20261016-records','rust-r1-linear-python-20261016','rust-r1-linear-python-20261016-records','rust-r1-linear-format-20261016','rust-r1-linear-kernel-20261016','rust-r1-linear-kernel-20261016-records','rust-r1-linear-comparison-20261016','rust-r1-linear-comparison-20261016-records']
        pins=[validate_root(ROOT/'artifacts'/n) for n in names];assert all(p['status']=='complete' for p in pins)
        def read(name,file='summary.json'):return json.loads((ROOT/'artifacts'/name/file).read_bytes())
        s=read('rust-r1-linear-comparison-20261016');rows=read('rust-r1-linear-comparison-20261016','comparisons.json');py=read('rust-r1-linear-python-20261016');binding=read('rust-r1-linear-python-20261016','runtime-binding.json')
        assert s['cases']==7 and s['elements']==16128 and s['baseline_RP_and_context_candidate_byte_exact_cases']==7 and s['same_input_bias_add_bit_mismatches']==0 and s['decomposition_max_residual']==0.
        assert s['raw_matmul_bit_mismatches']==1620 and py['fused_separate_bit_mismatches']==7241 and py['original_patch_byte_exact_cases']==7
        assert [r['case'] for r in rows]==['train-first','train-last','zero','constant','floor-below','floor-equal','floor-above']
        for r in rows[:2]:assert r['raw_matmul']['bit_mismatches']==0 and r['local_bias_add']['SSE']==0. and r['total']==r['fused_vs_separate']
        for r in rows[4:]:assert r['raw_matmul']['bit_mismatches']==540 and r['fused_vs_separate']['SSE']==0.
        model=ROOT/'crates/banto-ai/src/model.rs';assert digest(model)=='acefec42e7506d807f7deae22269f30f9bf409a8c8cf9d1ddb59c2ef6af7fa80'
        declaration=ROOT/'artifacts/rust-r1-linear-declaration-20261016'
        sourcepins=read('rust-r1-linear-declaration-20261016','source-pins.json')
        for pin in sourcepins:assert digest(ROOT/pin['path'])==pin['sha256']
        priorpins=read('rust-r1-linear-declaration-20261016','root-pins.json')
        for pin in priorpins:verify_closed(ROOT/pin['path']);assert digest(ROOT/pin['path']/'root-closed.json')==pin['sha256']
        resources={}
        for name in names:
            p=ROOT/'artifacts'/name/'exit.json'
            if not p.exists():continue
            e=json.loads(p.read_bytes());g=e['sampled_group_peak'];assert e['returncode']==0 and e['elapsed_seconds']<870 and e['sampled_cache_bytes']<1536*1024**2
            assert max(g['monitor_inclusive_footprint'],g['monitor_inclusive_rss'],e['child_wait_peak_rss_bytes'])<2*1024**3;resources[name]=e
        admission=ROOT/'examples/configs/rust-r1-fused-linear-admission-20261016.json';assert json.loads(admission.read_bytes())['status'].startswith('Design fixed')
        registry=ROOT/'environments/rust-cpu/cargo-home/registry/src/index.crates.io-1949cf8c6b5b557f'
        sources=list(dict.fromkeys([Path(__file__),*source_files(),ROOT/'tools/public-data/rust_r1_linear_source.py',ROOT/'tools/public-data/rust_r1_linear_boundary.py',ROOT/'tools/public-data/rust_r1_compare.py',ROOT/'examples/configs/rust-r1-linear-boundary-20261016.json',admission,ROOT/'tools/verification_records.py',registry/'burn-tensor-0.22.0/src/tensor/module.rs',registry/'burn-backend-0.22.0/src/backend/ops/modules/linear.rs',registry/'burn-flex-0.22.0/src/ops/module.rs',registry/'burn-flex-0.22.0/src/ops/matmul.rs',registry/'burn-flex-0.22.0/Cargo.toml',registry/'gemm-0.19.0/src/gemm.rs',registry/'gemm-0.19.0/Cargo.toml',registry/'burn-autodiff-0.22.0/src/ops/module.rs']))
        phase={'scope':'linear boundary attribution, no model candidate','cases':7,'original_patch_reproduced':7,'current_RP_and_prior_context_candidate_reproduced':7,'train_raw_matmul_bit_exact':True,'standalone_bias_add_bit_exact':True,'fused_separate_train_difference':True,'artificial_floor_matmul_difference':True,'full_forward':0,'core_changed':False,'tolerance_changed':False,'R1_complete':False,'R2_started':False,'training':False,'next_admission_fixed':True,'next_candidate_implemented':False}
        maxfp=max(e['sampled_group_peak']['monitor_inclusive_footprint'] for e in resources.values());maxrss=max(max(e['sampled_group_peak']['monitor_inclusive_rss'],e['child_wait_peak_rss_bytes']) for e in resources.values());cache=disk_bytes();assert cache<1536*1024**2
        report='docs/results/banto-ai-rust-r1-linear-boundary-2026-10-16.md'
        text=f'''# Rust R1 — patchのbias融合と行列積の差を分離（2026-10-16）

**両train batchでは、bias前の行列積はPython/Rustで全bit一致した。patch出力の差は、Pythonのbias込みaddmmとRustのmatmul後加算の違いとして分離できた。単独のbias加算は全7caseでbit一致した。一方、floor境界の人工3caseでは行列積自体に差が残る。** 今回は診断だけでモデルを変更せず、R1は安定版の累積1点未達、R2未開始を維持。

## ソース・版・実行境界

[事前の診断条件](../../examples/configs/rust-r1-linear-boundary-20261016.json)を保存してから演算を開始した。exact installed torch git `08187d9e0fba026dc8217405802ab5381dc88d90` の公式Linear/LinearAlgebra/CPUBlas/BlasKernelを取得・hash保存した。torch2.14.0、CPU capability DEFAULT、BLAS_INFO=accelerate、AT_BUILD_WITH_BLAS=1、MKL/MKLDNNなし。torch threads/interop各1とVECLIB_MAXIMUM_THREADS=1を記録し、その条件でも元のpatch全7anchorをbytes再現した。

[PyTorch Linear.cpp](https://github.com/pytorch/pytorch/blob/08187d9e0fba026dc8217405802ab5381dc88d90/aten/src/ATen/native/Linear.cpp)ではbias付き連続nD入力をflattenしてaddmmへ渡す。[LinearAlgebra.cpp](https://github.com/pytorch/pytorch/blob/08187d9e0fba026dc8217405802ab5381dc88d90/aten/src/ATen/native/LinearAlgebra.cpp)ではbiasを出力へcopyしbeta1でGEMMへ渡す。[CPUBlas.cpp](https://github.com/pytorch/pytorch/blob/08187d9e0fba026dc8217405802ab5381dc88d90/aten/src/ATen/native/CPUBlas.cpp)の今回の型/寸法/BLAS条件はsgemm_分岐に該当する。

libtorch_cpu handleで解決したsgemm_は `{binding['resolved_image']}` の `{binding['resolved_symbol']}` を指した。これはbuild情報と解決symbolの確認であり、hot-pathをtraceした証明やAccelerate内部の積和順を確定したものではない。解決情報、実dylib SHA、入力/weightのshape・strideを保存した。

現行RustはFlexのgemm0.19.0で出力係数0の積を求め、その後biasを別加算する。Burn標準module::linearのFlex経路もmatmul→addのため、API名を置き換えるだけでは融合しない。registryの該当sourceを結果rootとEvidenceStoreへ保存した。

## 固定7caseの比較

閉鎖済みfixtureのPython経路normalized_contextとpatch weight/biasだけを使用した。全modelやlabelを開かず、Pythonでは各caseのnn.Linear・mm・別bias加算各1回、Rustでは同じoperandのmatmul・自前mmへのbias・保存Python mmへのbias各1回を実行した。元PP patch全7組、既存RP patch全7組、前回context修正候補のpatch全7組がbytes一致したため、再生経路の違いを今回の原因と混同しない。

| ケース群 | bias前matmulのbit差 | 同一mmへの単独bias加算 | Python fused/別加算のbit差 |
| --- | --- | --- | --- |
| train-first（6,144値） | 0 | 0 | 3,619 |
| train-last（6,144値） | 0 | 0 | 3,622 |
| zero・constant（各768値） | 各0 | 各0 | 各0 |
| floor-below/equal/above（各768値） | 各540 | 各0 | 各0 |
| 合計（16,128値） | 1,620 | 0 | 7,241 |

両train batchのpatch差は全てfused/別加算の項に一致し、最大絶対差は先頭4.76837158203125e-7、末尾2.384185791015625e-7。floor3caseはfused/別加算差0で、異なる行数/値域でのmatmul実装差が残る。単独加算の丸めを変更して直す根拠はない。

符号付きの出力差を、全16,128値で次のように分解し、float64差分上で残差0を確認した。

~~~text
Rust自前mm+加算 − Python fused Linear
 = (Rust自前mm+加算 − RustによるPython mm+加算)
 + (RustによるPython mm+加算 − Python mm+加算)
 + (Python mm+加算 − Python fused Linear)
~~~

第1項はmatmul差がbias後へ伝わった差、第2項は同一mmの局所加算差、第3項はPython内のfused/別加算差。SSEは順に1.895100742999034e-11、0、2.6417081699100754e-11、総差4.5368089129091095e-11。今回、非ゼロのケース群が分かれているが、一般に各項SSEを独立の寄与率として加算できるとは扱わない。生の出力/各項とケース別集計を保存した。

局所の全値は元R0許容差内だが、上流の相殺・伝播を含む全体gateの合格を意味しない。前回のblocks.1 index183がbias融合だけで解消するとの因果認定もしていない。

## 次の一般候補の受入条件

[fused linearの設計・有限受入条件](../../examples/configs/rust-r1-fused-linear-admission-20261016.json)を固定した。候補の実装/実行はまだ0。既存pure-Rust gemmで出力をbiasに初期化し、出力係数1・積係数1・read_dst=trueとする1方式を検討する。Mac専用Accelerate FFI、vendor backend、scalar積和順探索、padding、f64行列積、case別switchを追加しない。pure-Rustで同じ参照値を保証できるという意味ではない。

公開backend extensionによりgraphを保ち、rank2のshape/dtype/device-context/stride/boundsを検証する。gemmの公開unsafe pointer APIを呼ぶ必要がある場合は、専用primitive helper内だけに隔離し、入力storageのoffset/strideと全アクセス範囲、出力サイズ、alias不在をchecked arithmeticで証明する。private bridgeやunsafe型変換は使わず、安全性を示せなければkernel前に停止する。標準Burn linearへ単に置換する候補は起動しない。

既存gemmを直接参照する場合はoptional exact0.19.0/default-features=falseだけを追加し、既存package/version集合と有効featureを維持する。Cargo.lockのroot依存edge変更は実装前snapshotとoffline一回のrefreshを前提に検査し、registry/他依存versionは変更しない。今回のCargo.toml/Cargo.lockは不変。

実装時は固定8人工caseの独立期待値・graph/入力不変・拒否条件を先に保存して検証する。その後、閉鎖済みPP/RPを使い、新候補だけを全154linear（patch7、attention projection84、output projection28、FF28、head7）へ一度適用する。旧baseline/55node全層再生はしない。全finite/元許容差内、全体SSE厳密減少、各case合計SSE非増加が局所採用条件。

全局所gateを通った場合だけ、全linearと既知のcontext/LayerNorm補正を一律接続し、既存3テスト→元固定7case/389,214要素の全体比較を1回行う。全体未達ならmodel元bytesへ復元し、局所passだけでR1通過へ変えない。backwardは実装・compile・graph参加と数値確認を分け、R2設計前に実行/認定しない。

## 状態・保護・OS分離

model.rsはSHA `acefec42e7506d807f7deae22269f30f9bf409a8c8cf9d1ddb59c2ef6af7fa80` のまま。許容差・参照・weights・Cargo.lock/default不変、既存変更/失敗/closed roots保護。今回のRust診断exampleはcompile/run成功。モデルを変えていないため既存3テストの無目的な再実行やfull forwardは行わなかった。

この結果はMacの共通Flex診断とMac参照BLASの来歴確認である。Windows native/Windowsサービス/OS依存suiteは未実行であり、Macからの移植成立を認定しない。今回の候補にMac専用bindingを導入していない。

保全・点検支援第一、自作モデルの産業/需要での実用性、Rustでの学習・optimizer保存再開の目的を維持。CARE test/需要2015再評価・学習・下流編集・push・製品採用0。需要は2014以前だけ調整、同休業mean28、四季平均の過小/過大非増加、観測のみ/欠測0評価分離。heartbeat PAUSED。

親900/子870秒、各2GiB、build cache+target1.5GiBと旧artifact/EvidenceStore/stdio枠を維持。最大監視込みfootprint {maxfp:,}B、最大RSS系指標 {maxrss:,}B、最終cache+target {cache:,}B。process group sampleの捕捉限界はありhard OS capではない。全source/stdio/exit/state/closure・文書前後はartifacts/rust-r1-linear-results-20261016-evidenceへ保存。
'''
        headline='patchの固定7case/16,128値を分解。両train batchのraw matmulはbit一致、単独bias加算は全case一致。trainの差はPython fused/別加算差7,241値で説明でき、floor人工3caseのraw matmul差各540値とは別。'
        changes={report:text}
        n='docs/current-handoff.md';changes[n]='## 最新 — patchのbias融合と行列積差を分離（2026-10-16）\n\n[結果](results/banto-ai-rust-r1-linear-boundary-2026-10-16.md)。'+headline+' model/Cargo/default/許容差/参照不変、追加full forward/学習0。安定版の累積1点未達/R1未合格/R2停止を維持。\n\n次は[固定したpure-Rust fused linear受入条件](../examples/configs/rust-r1-fused-linear-admission-20261016.json)に従う。公開extension+既存gemmでbiasを出力初期値にする1方式。安全なstorage/stride/bounds証明とgraph、必要ならroot依存edgeだけのoffline lock変更を先に固定し、固定8人工→新候補だけ全154linear局所比較。全局所gate後だけ全体7caseを1回。まだ候補実装/演算0、Accelerate FFI導入0。単独加算修正、同じ全層再生、case/点ごとの丸め探索をしない。全証跡/文書前後はartifacts/rust-r1-linear-results-20261016-evidence。\n\n各2GiB/build1.5GiB/時間/保存枠、既存成果/失敗/closed roots保護、保全第一/Rust学習目的、需要2015停止/2014以前調整/同休業mean28/四季両側非増加/観測欠測0分離、Windows別検証、heartbeat PAUSED維持。以下は旧記録。\n\n---\n\n'+(ROOT/n).read_text()
        for n,marker,entry in [('docs/results/README.md','## Rustクレートの移植\n','- [Rust R1 patchのbias融合/行列積差](banto-ai-rust-r1-linear-boundary-2026-10-16.md) — trainのraw mm一致、単独add一致、一般fused候補の条件を固定。'),('docs/research/README.md','## 文書\n','- [Rust R1 linear境界の診断と次候補条件](../results/banto-ai-rust-r1-linear-boundary-2026-10-16.md) — pure-Rust/graph/有限比較/安全性を実装前に固定。')]:
            before=(ROOT/n).read_text();assert marker in before;changes[n]=before.replace(marker,marker+'\n'+entry+'\n',1)
        for n in ['docs/research/banto-ai-rust-implementation-plan-2026-10-16.md','docs/research/rust-small-forecaster-r0-2026-10-16.md']:
            changes[n]=re.sub(r'^状態:.*$','状態: R1a済み、R1bは安定版の累積1点未達/R2停止。patchのtrain raw mm一致とbias融合差、人工floorの別matmul差を分離。次は固定したpure-Rust fused linear受入条件、安全性/graph/有限局所gate。[最新結果](../results/banto-ai-rust-r1-linear-boundary-2026-10-16.md)。2026-10-16 JST。',(ROOT/n).read_text(),count=1,flags=re.M)
        n='docs/research/research-roadmap.md';changes[n]='## 現在 — patchの差を分解、fused linearの条件を固定（2026-10-16）\n\n[結果](../results/banto-ai-rust-r1-linear-boundary-2026-10-16.md)。'+headline+' モデル不変/R1未達/R2停止。次は既存pure-Rust gemmのbias融合を1候補として公開extensionへ設計、固定人工/154局所gate後だけ全体。以下は旧記録。\n\n---\n\n'+(ROOT/n).read_text()
        out.sources(sources);out.json('phase.json',phase);out.json('root-pins.json',pins);out.json('prior-root-pins.json',priorpins);out.json('resources.json',resources);out.json('runtime-binding.json',binding);out.json('next-admission-pin.json',{'path':str(admission.relative_to(ROOT)),'sha256':digest(admission),'implemented':False});out.json('case-results.json',rows)
        evidence=ROOT/'artifacts/rust-r1-linear-results-20261016-evidence'
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
            for target in re.findall(r'\]\(([^)]+)\)',text):
                if not target.startswith('https://'):assert ((ROOT/report).parent/target).exists(),target
            for pin in pins:assert validate_root(ROOT/pin['root'])['closure_sha256']==pin['closure_sha256']
            for pin in priorpins:assert digest(ROOT/pin['path']/'root-closed.json')==pin['sha256']
            store.write_json('documents-after',[{'path':n,'sha256':digest(ROOT/n)} for n in changes])
        evidence_check=verify_evidence(evidence,'complete');out.json('evidence-check.json',evidence_check);out.json('summary.json',{**phase,'verified_roots':len(pins),'documents':len(changes),'model_sha256':digest(model),'resources':check.check()});print(json.dumps({'published':True,'verified_roots':len(pins),'core_changed':False,'R1_complete':False,'next_candidate_implemented':False,'evidence':evidence_check}));status='complete'
    finally:out.close(status)

if __name__=='__main__':main()
