"""Close source arithmetic attribution and preserve the pending R1 gate."""
import json
import math
import re
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/public-data'),str(ROOT/'models/mini-transformer')]
from metropt_multiday import Files,digest
from macos_demand_runtime import MacCheckpoint
from macos_rust_run import disk_bytes
from rust_r1_moments_audit import source_paths,DECLARATION,CONFIG
from rust_r1_publish_preparation import validate_root
from verification_records import EvidenceStore
from care_rust_r0_close import verify_evidence


def main():
    out=Files(ROOT/'artifacts/rust-r1-moments-results-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        names=['rust-r1-moments-declaration-20261016','rust-r1-moments-declaration-20261016-records',
               'rust-r1-moments-audit-20261016','rust-r1-moments-audit-20261016-records']
        pins=[validate_root(ROOT/'artifacts'/name) for name in names]
        source_pins=json.loads((DECLARATION/'source-pins.json').read_bytes())
        old_pins=json.loads((DECLARATION/'root-pins.json').read_bytes())
        for pin in source_pins:assert digest(ROOT/pin['path'])==pin['sha256']
        for pin in old_pins:assert digest(ROOT/pin['path']/'root-closed.json')==pin['closure_sha256']
        audit=ROOT/'artifacts/rust-r1-moments-audit-20261016'
        s=json.loads((audit/'summary.json').read_bytes());rows=json.loads((audit/'component-comparisons.json').read_bytes())
        assert s['inputs']==49 and s['anchor_groups_exact']==49 and s['rows']==1953
        assert s['source_ordered_mean_bit_mismatches']==260 and s['source_ordered_rstd_bit_mismatches']==21
        assert s['native_reference_affine_bit_mismatches']==0 and s['full_forward_calls']==0
        cfg=json.loads(CONFIG.read_bytes());aggregate={}
        for path in cfg['fixed_paths']:
            aggregate[path]={
                'SSE':math.fsum(r['outputs'][path]['SSE'] for r in rows),
                'bit_mismatches':sum(r['outputs'][path]['bit_mismatches'] for r in rows),
                'failing_elements':sum(r['outputs'][path]['failing_elements'] for r in rows),
                'max_abs':max(r['outputs'][path]['max_abs'] for r in rows)}
        moment_totals={}
        for method in ['balanced','serial','source_ordered']:
            moment_totals[method]={key:{
                'bit_mismatches':sum(r['moments'][method][key]['bit_mismatches'] for r in rows),
                'SSE':math.fsum(r['moments'][method][key]['SSE'] for r in rows),
                'max_abs':max(r['moments'][method][key]['max_abs'] for r in rows)} for key in ['mean','rstd']}
        reduction=100*(1-aggregate['source_ordered_reference_affine']['SSE']/aggregate['balanced_reference_affine']['SSE'])
        resources={}
        for name in [n for n in names if n.endswith('-records')]:
            e=json.loads((ROOT/'artifacts'/name/'exit.json').read_bytes());g=e['sampled_group_peak']
            assert e['returncode']==0 and e['elapsed_seconds']<870
            assert max(g['monitor_inclusive_footprint'],g['monitor_inclusive_rss'],e['child_wait_peak_rss_bytes'])<2*1024**3
            assert e['sampled_cache_bytes']<1536*1024**2
            resources[name]=e
        phase={'scope':'source arithmetic attribution and next admission contract only',
               'model_candidates':0,'model_core_changed':False,'source_reconstruction_bit_exact':False,
               'R1_complete':False,'R2_started':False,'training':False,'full_forward_calls':0,
               'CARE_or_demand2015_reevaluation':False,'next_step':'source/binary evidence of scalar lane-merge contraction and a graph-preserving FMA design; no guessed rounding-order search'}
        report='docs/results/banto-ai-rust-r1-moments-audit-2026-10-16.md'
        design='docs/research/rust-r1-moments-admission-2026-10-16.md'
        text=f'''# Rust R1 — モーメント計算と丸め位置の照合（2026-10-16）

計画に沿って全7ケース・全7LayerNormの保存入力を照合した。**参照モーメントと参照順のaffineで全124,992出力をビット再現し、モーメント計算とaffineの結合順の違いを分離できた。4レーンWelford/FMAのソース再現は差を{reduction:.4f}%減らしたが完全一致せず、モデル採用には進めていない**。元の累積1点未達、R1未合格・R2停止は維持する。

## 固定条件・来歴

[数量計算前の条件](../../examples/configs/rust-r1-moments-audit-20261016.json)とdeclaration rootを先に保存した。既存PP入力49組・1,953行/幅64のみ。native_layer_normは49回。既存のbalanced式、前回不採用のserial Flex式、インストール済みPyTorchヘッダーの4レーンWelford/FMAを再構成した。参照モーメントを二種類のaffine順に渡す比較も先に固定した。候補選択、full forward、model変更、学習は0。

インストール済みPyTorch2.14.0の `moments_utils.h` と `vec128_float_neon.h` をpinし、内容を証跡へ保存した。後者のfloat幅は4、fmaddはaarch64のvfmaq_f32を使う。前者は幅64では16回のレーン別更新、初期stackへの統合、4レーンのscalar AddMoments統合を行う。scalarの通常演算は各f32へ丸め、明示fmaddだけsystem fmafで一度丸めた。一つの読み方を固定しており、結果を見た後のFMA有無・lane幅・統合順の変更は0。

普通の乗算と加算はFMAと同じではないことを、(1+2^-23)×(1−2^-23)−1の人工例で確認した。FMAは−2^-46、分離演算は0になる。これだけでモデルの累積差全体の原因をFMAと断定しない。

保存PPとnative出力、保存RPとbalanced再構成、前回保存Flex候補とserial再構成は、それぞれ全49組がbytes一致した。この3系統のanchorを満たしたため、同じ入力に対する以下の成分比較を解釈する。参照や過去rootの更新はない。

## 平均・逆標準偏差の差

各方式の1,953行をnative_layer_normのmean/rstdと比較した。分散はnative APIから直接得られないため、rstdを逆算した値を「参照分散」とはしていない。各方式自身の分散は保存した。

| 方式 | mean不一致行 | rstd不一致行 | mean最大差 | rstd最大差 |
| --- | --- | --- | --- | --- |
'''
        for method,totals in moment_totals.items():
            text+=f"| {method} | {totals['mean']['bit_mismatches']} | {totals['rstd']['bit_mismatches']} | {totals['mean']['max_abs']:.9g} | {totals['rstd']['max_abs']:.9g} |\n"
        text+='''
## 正規化・affine出力

reference affineは `((x−mean)×rstd)×gamma+beta`、Flex affineは `(x−mean)×(rstd×gamma)+beta`。各普通演算の後でf32へ丸める。nativeモーメントを共通にすると、結合順だけによる差を分離できる。

| 固定経路 | SSE | ビット不一致要素 | 元許容差の超過 |
| --- | --- | --- | --- |
'''
        for path,a in aggregate.items():text+=f"| {path} | {a['SSE']:.12g} | {a['bit_mismatches']:,} | {a['failing_elements']} |\n"
        text+=f'''
nativeモーメント＋reference affineは全要素一致、nativeモーメント＋Flex affineは42,216要素でビット差が生じた。モーメント差を含めないaffineの結合順でも差が生じることが確認できた。一方、全経路は局所の元許容差内であり、ビット差の個数をそのままR1超過や予測性能の差と呼ばない。

4レーン/FMAのソース再現はSSEが現行の約{aggregate['source_ordered_reference_affine']['SSE']/aggregate['balanced_reference_affine']['SSE']:.6f}倍となった。ただしmean260行・rstd21行、出力5,827要素がビット一致しない。これを根拠に「参照の演算順を完全再現した」とはしない。compilerのscalar積和縮約やwheelの実行コードとヘッダーの対応は追加確認が必要であり、今回の結果だけでは残差の原因を特定できない。

## 判断と次工程

[次工程の受入条件](../research/rust-r1-moments-admission-2026-10-16.md)を保存した。ソース再構成のSSE減少は診断結果であり、model候補採用条件ではない。scalarの丸め順を複数試して合うものを選ぶことはしない。まず参照build/binaryの証拠を調べ、残差の由来を確定できるか判断する。

学習を含むRust移植には、hostへ値を取り出す今回の診断ループをforwardへ貼り付けられない。計算graphを保つFMAが必要。現在のpin済みBurn公開tensor/backend APIの調査では直接のFMAメソッドを見つけていない。f64乗算＋加算＋f32 castは二重丸めを含み得るため、IEEE f32 FMAの一般的代用品と認定しない。実装方式・forward oracle・将来のbackward条件を別途固定してから接続する。

元R1の7ケース/23anchor/許容差を維持し、これを通過するまでR2学習・保存再開へ進まない。保全・点検第一優先、産業/需要の自作モデル実用性とRust学習目的、需要2015停止・2014以前調整・同休業mean28・四季両側非増加・観測のみ/欠測0評価分離は不変。CARE test再評価・新依存/取得・下流変更・push・製品採用0。

## 資源と記録

| 実行 | 秒 | 監視込みfootprint / RSS |
| --- | --- | --- |
'''
        for name,e in resources.items():
            g=e['sampled_group_peak'];text+=f"| {name} | {e['elapsed_seconds']:.3f} | {g['monitor_inclusive_footprint']:,} / {g['monitor_inclusive_rss']:,} B |\n"
        text+=f'''
全exit0、親900/子870秒・physical footprint/peak RSS各2GiB以内、cache+targetは{disk_bytes():,}Bで1.5GiB以内。旧artifact/EvidenceStore/stdio枠を維持。Mac process groupのsample観測でありhard OS capではない。Windows native/OS依存suiteは未実行、heartbeat PAUSED維持。

実行rootは `artifacts/rust-r1-moments-declaration-20261016` と `rust-r1-moments-audit-20261016` および各records。全source/stdio/exit/state/closure・集計・文書前後を `artifacts/rust-r1-moments-results-20261016-evidence` へ保存。NumPy未導入の既存PyTorch警告はstderrへ保持し、インストールや依存変更は行っていない。
'''
        contract='''# R1モーメント計算 — 次工程の受入条件（2026-10-16）

[照合結果](../results/banto-ai-rust-r1-moments-audit-2026-10-16.md)を受けた設計境界。R1の許容差・参照・元7ケースを変更しない。標準LayerNorm候補の再試行や、既知1点に合う算術探索はしない。現時点でmodelへ採用する追加方式は未選択。

1. **参照の計算順を確定する。** pinしたPyTorch wheel/build情報と実行コードから、4レーン更新後のscalar AddMomentsで積和縮約が行われるか等を確認する。ヘッダーの通常演算を一演算ごとにf32へ丸める解釈では、mean260/rstd21行が一致しなかった事実を維持する。FMAの有無を数値一致だけで選ばず、compiler/binaryから根拠が得られなければ未確定で止める。新たな数値比較を行う場合も、その根拠と有限回数を先に固定する。
2. **graphを保つ演算境界を選ぶ。** 推論だけのhostループやto_data/from_dataでdetachする方式はmodelへ接続しない。既存Burn pin/featureを保つtensor/backend拡張でf32 fused multiply-addを表現できるか調査する。公開APIに見つからなかったことから拡張不能とは断定しない。新依存・backend切替・グローバル変更を自動追加しない。
3. **FMAのforward契約を先に固定する。** 独立oracleはRust標準f32::mul_addとsystem fmafの相互照合を候補とする。人工の通常値、積の丸めが相殺される例、subnormal、signed zero、個別積がoverflowしても積和結果はfiniteの例を含め、入力・期待bits・有限範囲・非有限拒否の役割を事前保存する。f64経由だけで一般のcorrectly-rounded f32 FMAを保証しない。実装方式未決定なので、この文書はprimitive実行開始やAPI完成の宣言ではない。
4. **学習契約も残す。** 実数上の局所微分da=b・db=a・dc=1、broadcast軸のgradient合計、同一tensorを複数引数に使った際の加算を将来の独立確認対象とする。丸めたfloat関数の階段を微分する主張ではない。forwardが合ってもbackward成功とはしない。R2実行はR1全体通過後、既定の有限更新・再開fixtureに従う。
5. **model接続は一般方式で一度だけ。** 実装の根拠、全LayerNormへの一律適用、局所比較/全体比較の有限回数、採用/復元条件を数量計算前に別設定として固定する。元7ケースの全23anchorを通過して初めてR1を合格とする。失敗は保存し、許容差緩和・参照再生成・失敗点の例外処理をしない。

親900秒/子870秒、physical footprint・peak RSS各2GiB、build cache+target1.5GiB、旧artifact/EvidenceStore/stdio上限を維持。既存成果・失敗・closed rootsを保護する。保全・点検第一優先と学習を含むRust移植を維持し、CARE test/需要2015の再評価、下流repo変更、Windows native/OS依存検証は今回の範囲へ足さない。
'''
        changes={report:text,design:contract}
        headline='全49入力/1,953行のnative PP・balanced RP・serial Flexを各bytes再現。参照モーメント＋参照affineは全124,992要素一致。4lane/FMAのソース再現はSSE約94.5%減だがmean260/rstd21行・出力5,827要素が非一致。'
        handoff='docs/current-handoff.md'
        changes[handoff]='## 最新 — モーメント・affineの差を分離、参照の丸め順は未確定（2026-10-16）\n\n[結果](results/banto-ai-rust-r1-moments-audit-2026-10-16.md)・[次工程の受入条件](research/rust-r1-moments-admission-2026-10-16.md)。'+headline+' 元のR1累積1点未達/未合格とR2停止を維持。model候補/変更/full forward/学習0。\n\n次はwheel/build/binaryの証拠でscalar lane mergeの積和縮約などを確認し、graphを保つFMA表現を設計する。数値一致だけで丸め順を選ばず、実装方式/有限条件を先に固定する。host診断ループや未証明のf64 FMA代用をmodelへ接続しない。全source/stdio/exit/state/closureと文書前後はartifacts/rust-r1-moments-results-20261016-evidence。\n\n許容差・旧成果/失敗/closed roots・各2GiB/build1.5GiB/時間/保存枠、保全第一/Rust学習目的、需要2015停止/2014以前調整/同休業mean28/四季両側非増加/観測欠測0分離、Windows別検証、heartbeat PAUSEDを維持。以下は旧記録。\n\n---\n\n'+(ROOT/handoff).read_text()
        for name,marker,entry in [
            ('docs/results/README.md','## Rustクレートの移植\n','- [Rust R1モーメント計算・丸め位置の照合](banto-ai-rust-r1-moments-audit-2026-10-16.md) — 3系統のanchor再現、成分分離、core不変。'),
            ('docs/research/README.md','## 文書\n','- [Rust R1モーメント計算・次工程の受入条件](rust-r1-moments-admission-2026-10-16.md) — 参照build/binaryとgraphを保つFMAの境界。')]:
            before=(ROOT/name).read_text();assert marker in before;changes[name]=before.replace(marker,marker+'\n'+entry+'\n',1)
        for name in ['docs/research/banto-ai-rust-implementation-plan-2026-10-16.md','docs/research/rust-small-forecaster-r0-2026-10-16.md']:
            changes[name]=re.sub(r'^状態:.*$','状態: R1a/既存3テストpass。モーメント/affineの成分照合完了、参照の丸め順は未確定、core不変。元の累積1点未達でR1未合格・R2未着手。[最新結果](../results/banto-ai-rust-r1-moments-audit-2026-10-16.md)。2026-10-16 JST。',(ROOT/name).read_text(),count=1,flags=re.M)
        roadmap='docs/research/research-roadmap.md';changes[roadmap]='## 現在 — モーメントとaffineの差を分離（2026-10-16）\n\n[結果](../results/banto-ai-rust-r1-moments-audit-2026-10-16.md)。'+headline+' 参照build/binaryの根拠とgraphを保つFMA設計へ。core不変・R1未達/R2停止。以下は旧記録。\n\n---\n\n'+(ROOT/roadmap).read_text()
        sources=[Path(__file__),*source_paths(),ROOT/'tools/verification_records.py']
        out.sources(sources);out.json('phase.json',phase);out.json('root-pins.json',pins);out.json('resources.json',resources)
        out.json('aggregate.json',aggregate);out.json('moment-totals.json',moment_totals)
        evidence=ROOT/'artifacts/rust-r1-moments-results-20261016-evidence'
        with EvidenceStore(evidence) as store:
            store.write_json('phase',phase);store.write_json('root-pins',pins);store.write_json('old-root-pins',old_pins)
            store.write_json('document-paths',list(changes))
            for i,p in enumerate(sources):store.write_bytes(f'source-{i}',p.read_bytes())
            for i,name in enumerate(changes):
                if (ROOT/name).exists():store.write_bytes(f'before-{i}',(ROOT/name).read_bytes())
            for name,value in changes.items():(ROOT/name).write_text(value)
            for i,name in enumerate(changes):store.write_bytes(f'after-{i}',(ROOT/name).read_bytes())
            for i,name in enumerate(names):
                for j,p in enumerate(sorted((ROOT/'artifacts'/name).iterdir())):
                    if p.suffix!='.bin':store.write_bytes(f'root-{i}-{j}',p.read_bytes())
            for name in [report,design]:
                for target in re.findall(r'\]\(([^)]+)\)',changes[name]):assert ((ROOT/name).parent/target).exists(),target
            for pin in pins:assert validate_root(ROOT/pin['root'])['closure_sha256']==pin['closure_sha256']
            for pin in source_pins:assert digest(ROOT/pin['path'])==pin['sha256']
            for pin in old_pins:assert digest(ROOT/pin['path']/'root-closed.json')==pin['closure_sha256']
            store.write_terminal('terminal',{'exit':0,'state':'component attribution complete; source/binary rounding unresolved; core unchanged; R1 incomplete','resources':check.check()})
        out.json('evidence-readback.json',verify_evidence(evidence,'complete'))
        out.json('summary.json',{**phase,'source_ordered_SSE_reduction_percent':reduction,'resources':check.check()})
        print(json.dumps({'published':True,'SSE_reduction_percent':reduction,'core_changed':False,'R1_complete':False}));status='complete'
    finally:out.close(status)


if __name__=='__main__':main()
