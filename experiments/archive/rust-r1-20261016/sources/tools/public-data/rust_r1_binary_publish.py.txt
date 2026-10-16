"""Publish binary-backed arithmetic attribution without promoting R1 status."""
import json
import re
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'models/mini-transformer'),str(ROOT/'tools/public-data')]
from metropt_multiday import Files,digest
from macos_demand_runtime import MacCheckpoint
from macos_rust_run import disk_bytes
from rust_r1_publish_preparation import validate_root
from verification_records import EvidenceStore
from care_rust_r0_close import verify_evidence
from rust_r1_binary_moments import sources as moment_sources


def main():
    out=Files(ROOT/'artifacts/rust-r1-binary-results-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        names=['rust-r1-binary-declaration-20261016','rust-r1-binary-declaration-20261016-records',
               'rust-r1-binary-audit-20261016','rust-r1-binary-audit-20261016-records',
               'rust-r1-binary-symbols-20261016','rust-r1-binary-symbols-20261016-records',
               'rust-r1-binary-declaration2-20261016','rust-r1-binary-declaration2-20261016-records',
               'rust-r1-binary-audit2-20261016','rust-r1-binary-audit2-20261016-records',
               'rust-r1-binary-moments-declaration-20261016','rust-r1-binary-moments-declaration-20261016-records',
               'rust-r1-binary-moments-20261016','rust-r1-binary-moments-20261016-records']
        pins=[validate_root(ROOT/'artifacts'/name) for name in names]
        assert {p['root'].split('/')[-1] for p in pins if p['status']=='failed'}=={'rust-r1-binary-audit-20261016','rust-r1-binary-audit-20261016-records'}
        declared=ROOT/'artifacts/rust-r1-binary-moments-declaration-20261016'
        source_pins=json.loads((declared/'source-pins.json').read_bytes());prior_pins=json.loads((declared/'root-pins.json').read_bytes())
        for p in source_pins:assert digest(ROOT/p['path'])==p['sha256']
        for p in prior_pins:assert digest(ROOT/p['path']/'root-closed.json')==p['closure_sha256']
        binary=json.loads((ROOT/'artifacts/rust-r1-binary-declaration2-20261016/binary-pin.json').read_bytes())
        assert digest(ROOT/binary['path'])==binary['sha256']
        assert digest(ROOT/'crates/banto-ai/src/model.rs')=='acefec42e7506d807f7deae22269f30f9bf409a8c8cf9d1ddb59c2ef6af7fa80'
        bs=json.loads((ROOT/'artifacts/rust-r1-binary-audit2-20261016/summary.json').read_bytes())
        s=json.loads((ROOT/'artifacts/rust-r1-binary-moments-20261016/summary.json').read_bytes())
        assert bs['regions']==3 and bs['truncated_regions']==0 and bs['loaded_binary_exact']
        assert s['comparisons']==49 and s['rows']==1953 and s['output_elements']==124992
        assert s['mean_bit_mismatches']==s['rstd_bit_mismatches']==s['output_bit_mismatches']==s['output_failing_elements']==0
        resources={}
        for name in [n for n in names if n.endswith('-records')]:
            e=json.loads((ROOT/'artifacts'/name/'exit.json').read_bytes());g=e['sampled_group_peak']
            assert e['returncode']==(1 if name=='rust-r1-binary-audit-20261016-records' else 0)
            assert e['elapsed_seconds']<870 and max(g['monitor_inclusive_footprint'],g['monitor_inclusive_rss'],e['child_wait_peak_rss_bytes'])<2*1024**3
            assert e['sampled_cache_bytes']<1536*1024**2
            resources[name]=e
        phase={'scope':'binary-supported moment/affine attribution complete; no core integration',
               'binary_regions':3,'bit_exact_inputs':49,'bit_exact_rows':1953,'bit_exact_outputs':124992,
               'new_torch_kernels':0,'model_full_forward':0,'model_candidates':0,'core_changed':False,
               'R1_complete':False,'R2_started':False,'training':False,'tolerance_changed':False,
               'next_step':'minimal graph-preserving f32 FMA extension design and finite artificial forward contract; no host diagnostic loop in the model'}
        report='docs/results/banto-ai-rust-r1-binary-moments-2026-10-16.md'
        design='docs/research/rust-fma-primitive-contract-2026-10-16.md'
        text=f'''# Rust R1 — バイナリの丸め順を確定、局所出力を全ビット再現（2026-10-16）

計画に沿って、**前回残った平均260行・逆標準偏差21行の差を、レーン統合時の二つの積和縮約で説明できた**。実バイナリから決めた一つの計算順で、全49入力/1,953行のmean/rstdと全124,992出力がビット一致した。モデル本体は変更していないため、元のR1累積1点未達・R2停止は維持する。

## ソースから実行コードへの結び付け

[読取り条件](../../examples/configs/rust-r1-binary-audit-20261016-r2.json)を実行前に保存した。インストール済みPyTorch2.14.0の `libtorch_cpu.dylib` をSHA-256/サイズ/UUIDでpinし、dyldが読み込む実pathとの一致を確認。pinは調査後も不変。Mach-Oのsymbol tableとfunction startsを解析し、Xcodeのllvm-objdumpでfloat LayerNorm呼出元、幅64で使う `RowwiseMomentsImpl<float,4>`、OMP呼出元の3関数を取得した。各範囲は16KiB以内、切り詰め0、命令列bytesとhash・tool/version/command/stdio/exitを保存した。

Binary SHA-256: `{binary['sha256']}`。このMac wheelの証拠であり、別のPyTorch buildやWindowsへ同じ計算順を一般化しない。

最初のselectorは別depth版とcold関数を含む12関数が見つかり、6範囲の上限で停止した。逆アセンブルや数値kernelは未実行で、そのfailed root/source/stdio/exit/closureを保持。先にsymbol inventoryを保存したうえで、幅64・4レーンではchunk数1/depth<=4となるソース分岐から対象を絞った。上限の引上げや数値に合わせた関数選択ではない。

## 確定した丸め位置

以下のアドレスはslide前のMach-O仮想アドレス。前後のregister/dataflowと4レーン展開を確認し、FMA命令の存在だけではなく、どの式に対応するかを結び付けた。

| 範囲 | 命令 | 対応 |
| --- | --- | --- |
| 0x1f82028 / 0x1f82030 | fmla.4s | レーン内の平均/m2更新 |
| 0x1f822e4–0x1f822f8 | fsub, fmul, fmul, fmadd, fadd | lane0の分散補正項と既存m2の加算 |
| 0x1f82300 | fmadd s2, s4, s7, s2 | lane0の平均更新 |
| 0x1f82314 / 0x1f82320 | fmadd / fmadd | lane1のm2補正/平均更新 |
| 0x1f82334 / 0x1f8233c | fmadd / fmadd | lane2のm2補正/平均更新 |
| 0x1f82348 / 0x1f82358 | fmadd / fmadd | lane3の平均更新/m2補正 |

`delta=round32(lane_mean−mean)`、`c=round32(16/(n+16))` とすると、平均は `fmaf(c,delta,mean)`。m2の補正項は `cross=round32(round32(delta×delta)×c)`、`m2=round32(m2+fmaf(cross,float32(n),lane_m2))`。最後の既存m2との加算は分離される。前回はこの平均更新と補正項の積和を分離演算へ丸めていた。

affineの両weight/biasが存在する分岐では、中心化→rstd乗算→gamma乗算→beta加算という命令順を確認した。ヘッダーだけでscalarの積和縮約有無を決めてはいけないことも保存する。

## 保存値での一度だけの確認

[命令対応と再現条件](../../examples/configs/rust-r1-binary-moments-20261016.json)を数量計算前に固定した。前回の4レーン更新と初期stack統合はそのままに、上記のscalar統合だけを実命令のFMAへそろえた。system fmafを診断oracleに使い、保存済みPython入力・native moments・PP出力だけを読み、Torch kernelやmodel forwardは起動していない。相違時の丸め順探索・retryは0とした。

| 項目 | 結果 |
| --- | --- |
| 入力 / 行 / 出力要素 | 49 / 1,953 / 124,992 |
| 平均のビット不一致 | 0 |
| 逆標準偏差のビット不一致 | 0 |
| 正規化・affine出力のビット不一致 | 0 |
| 元の局所許容差の超過 | 0 |
| 新Torch kernel / model full forward / 学習 | 0 / 0 / 0 |

これは保存済みの有限7ケース/全7LayerNormでの局所再現。入力全般の誤差保証やRust全体のR1合格、需要/保全の性能改善ではない。元のR1 full forwardを修正して再評価した結果ではないことを区別する。

## 実装へ進む境界

[FMAの実装・人工検証条件](../research/rust-fma-primitive-contract-2026-10-16.md)を保存。次はgraphを保つ最小のFMA表現を選び、人工forwardで独立oracleと確認する工程。今回のhost scalar診断をmodelへ貼り付けず、private bridgeのunsafe変換や未証明のf64積和代用も使わない。forward契約の後、全LayerNormへ一律に適用する有限比較を別に事前固定する。Rust学習/backwardはR1全体通過後のR2の条件を維持する。

元の許容差・参照・weights・Cargo.lock・model core・旧成果/失敗/closed rootsを保持。保全・点検支援第一優先、産業/需要の自作モデル実用性と学習を含むRust移植目的も維持。CARE test/需要2015再評価・新データ/依存取得・下流repo変更・Git push・本番採用は0。需要2014以前調整、同休業mean28、四季両側非増加、観測のみ/欠測0評価分離は不変。

## 資源と記録

| 単位 | 秒 | 監視込みfootprint / RSS |
| --- | --- | --- |
'''
        for name,e in resources.items():
            g=e['sampled_group_peak'];text+=f"| {name} | {e['elapsed_seconds']:.3f} | {g['monitor_inclusive_footprint']:,} / {g['monitor_inclusive_rss']:,} B |\n"
        text+=f'''
selectorの初回失敗のみexit1、他はexit0。親900/子870秒、physical footprint/peak RSS各2GiB、build cache+target1.5GiB（最終{disk_bytes():,}B）、旧artifact/EvidenceStore/stdio上限を維持。Mac process groupのsample観測でありhard OS capではない。Windows native/OS依存suite未実行、heartbeat PAUSEDを維持。既存NumPy未導入警告はstderrに保持。

主要rootは `artifacts/rust-r1-binary-audit2-20261016` と `rust-r1-binary-moments-20261016`、各宣言とrecords。失敗rootも保持し、全source/stdio/exit/state/closure・命令対応/集計/文書前後は `artifacts/rust-r1-binary-results-20261016-evidence` に保存。大型dylib本体は重複保存せず、全体hashと選択範囲bytesを保存した。
'''
        contract='''# f32 FMA — Rust実装と人工forwardの受入条件（2026-10-16）

[バイナリ照合結果](../results/banto-ai-rust-r1-binary-moments-2026-10-16.md)で参照の丸め順は局所再現できた。次はmodelへ接続できる演算境界の実装設計。現時点で実装方式・primitive APIの完成、Rust全体のR1成功は認定しない。

- 意味はround-to-nearest/ties-to-evenのf32 fused multiply-add。乗算の中間値をf32へ丸めず、積和を一度丸める。呼出側の普通のmul/addまで無差別にFMAへ変えない。今回確定したWelford/レーン統合の指定箇所へ共通に適用する。
- AI本体はbanto-ai内に置く。Burn0.22.0/Flex CPUのpinを維持して、公開拡張点またはtensor演算でgraphを保持できる最小方式を調べる。公開API調査では直接のFMAは見つからず、bridgeの中身はprivateである。unsafeな内部表現の読替え、registry編集、backendの自動切替、依存追加はしない。既存APIだけで実装できない場合は必要な変更範囲を設計として明示する。
- hostのto_data/from_dataで値を再注入する診断コードを学習modelへ転用しない。f64のmul+addをf32へcastするだけの方式は、二重丸めを排除できず一般のIEEE FMA代用とはしない。形式的根拠なしにその方式を採用しない。
- 人工forward fixtureを実行前に一つ固定する。通常値、相殺（(1+2^-23)×(1−2^-23)−1）、subnormal、signed zero、積単独はoverflowしても積和はfiniteとなる例、broadcast、shape拒否を含める。入力bits、期待bits、有限/非有限の責務を保存。独立なRust f32::mul_addとsystem fmafを相互照合する。実装候補は一方式とし、科学的な不一致後の候補探索をしない。
- 勾配契約は実数の局所微分da=b、db=a、dc=1とbroadcast軸の合計、引数alias時の加算。float丸め関数そのものの数学的微分を主張しない。forwardで一致してもbackward成功とはしない。backward/更新/optimizer再開の実行は元R1全体通過後のR2で行う。
- model接続の前に、全7ケース・全7LayerNormへの一律適用、局所比較とfull forwardの有限回数、元23anchorの許容差、採用/復元条件を別の機械設定で固定する。通過前に学習へ進まず、許容差変更・参照再生成・既知1点だけの例外処理はしない。

親900秒/子870秒、physical footprintとpeak RSS各2GiB、build cache+target1.5GiB、旧artifact/EvidenceStore/stdio枠、既存変更/成果/失敗/closed rootsの保護を維持。保全・点検第一優先、産業/需要の自作モデル実用性、学習を含むRust移植目的は不変。CARE test/需要2015再評価、下流編集、Windows native/OS依存検証をこの人工forwardへ混ぜない。
'''
        changes={report:text,design:contract}
        headline='実際にロードされたMac PyTorchの3関数をpinし、scalar lane mergeの平均更新とm2補正のFMAを命令から確定。命令どおりの一度の保存値再現で、49入力/1,953行のmean/rstd・124,992出力が全bit一致。'
        handoff='docs/current-handoff.md';changes[handoff]='## 最新 — 参照バイナリの丸め順を確定、局所全bit再現（2026-10-16）\n\n[結果](results/banto-ai-rust-r1-binary-moments-2026-10-16.md)・[FMA実装条件](research/rust-fma-primitive-contract-2026-10-16.md)。'+headline+' model core/全体forward/学習0、元の累積1点未達・R1未合格/R2停止を維持。\n\n次はgraphを保つ最小FMA方式の設計と人工forward条件を固定する。host診断の貼付け、private bridgeのunsafe変換、未証明のf64代用、丸め順探索を行わない。最初の12関数selectorの上限停止を保持し、ソースの幅64分岐で3関数へ絞ったfresh読取りだけ成功。全source/stdio/exit/state/closure・命令/文書前後はartifacts/rust-r1-binary-results-20261016-evidence。\n\n旧成果/失敗/closed roots、許容差、各2GiB/build1.5GiB/時間/保存枠、保全第一/Rust学習目的、需要2015停止/2014以前調整/同休業mean28/四季両側非増加/観測欠測0分離、Windows別検証、heartbeat PAUSED維持。以下は旧記録。\n\n---\n\n'+(ROOT/handoff).read_text()
        for name,marker,entry in [
            ('docs/results/README.md','## Rustクレートの移植\n','- [Rust R1バイナリの丸め順と局所全bit再現](banto-ai-rust-r1-binary-moments-2026-10-16.md) — 49入力、124,992出力一致、core不変。'),
            ('docs/research/README.md','## 文書\n','- [f32 FMAのRust実装・人工forward条件](rust-fma-primitive-contract-2026-10-16.md) — graph保持と独立oracle、R1全体通過前の学習停止。')]:
            old=(ROOT/name).read_text();assert marker in old;changes[name]=old.replace(marker,marker+'\n'+entry+'\n',1)
        for name in ['docs/research/banto-ai-rust-implementation-plan-2026-10-16.md','docs/research/rust-small-forecaster-r0-2026-10-16.md']:
            changes[name]=re.sub(r'^状態:.*$','状態: R1a/既存3テストpass。参照binaryのscalar積和縮約を確定し全49入力の局所出力bit一致。core不変、元の累積1点未達でR1未合格・R2未着手。[最新結果](../results/banto-ai-rust-r1-binary-moments-2026-10-16.md)。2026-10-16 JST。',(ROOT/name).read_text(),count=1,flags=re.M)
        prior='docs/research/rust-r1-moments-admission-2026-10-16.md';changes[prior]='現在の進捗（2026-10-16）: 項目1の参照binary確認は[局所全bit再現](../results/banto-ai-rust-r1-binary-moments-2026-10-16.md)まで完了。項目2以降は[FMA実装条件](rust-fma-primitive-contract-2026-10-16.md)に沿って進める。以下の当初条件と旧負の結果は保持する。\n\n'+(ROOT/prior).read_text()
        roadmap='docs/research/research-roadmap.md';changes[roadmap]='## 現在 — 参照の丸め順を実命令で確定（2026-10-16）\n\n[結果](../results/banto-ai-rust-r1-binary-moments-2026-10-16.md)。'+headline+' 次はgraphを保つFMA方式と人工forward。core不変・R1未達/R2停止。以下は旧記録。\n\n---\n\n'+(ROOT/roadmap).read_text()
        sources=list(dict.fromkeys([Path(__file__),*moment_sources(),ROOT/'tools/public-data/rust_r1_binary_audit.py',ROOT/'tools/public-data/rust_r1_binary_audit_r2.py',ROOT/'examples/configs/rust-r1-binary-audit-20261016.json',ROOT/'examples/configs/rust-r1-binary-audit-20261016-r2.json',ROOT/'tools/verification_records.py']))
        out.sources(sources);out.json('phase.json',phase);out.json('root-pins.json',pins);out.json('resources.json',resources)
        evidence=ROOT/'artifacts/rust-r1-binary-results-20261016-evidence'
        with EvidenceStore(evidence) as store:
            store.write_json('phase',phase);store.write_json('root-pins',pins);store.write_json('binary-pin',binary)
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
            for p in pins:assert validate_root(ROOT/p['root'])['closure_sha256']==p['closure_sha256']
            for p in source_pins:assert digest(ROOT/p['path'])==p['sha256']
            assert digest(ROOT/binary['path'])==binary['sha256']
            store.write_terminal('terminal',{'exit':0,'state':'binary contraction attributed; local bit identity; model unchanged; R1 incomplete','resources':check.check()})
        out.json('evidence-readback.json',verify_evidence(evidence,'complete'))
        out.json('summary.json',{**phase,'resources':check.check()})
        print(json.dumps({'published':True,'bit_exact_outputs':124992,'core_changed':False,'R1_complete':False}));status='complete'
    finally:out.close(status)


if __name__=='__main__':main()
