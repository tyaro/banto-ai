"""Publish one rejected standard LayerNorm candidate without changing the core."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'tools'),str(ROOT/'tools/public-data'),str(ROOT/'models/mini-transformer')]
from metropt_multiday import Files, digest, verify_closed
from verification_records import EvidenceStore
from macos_demand_runtime import MacCheckpoint
from macos_rust_run import source_files, disk_bytes
from rust_r1_publish_preparation import validate_root
from care_rust_r0_close import verify_evidence


def main():
    out = Files(ROOT/'artifacts/rust-r1-native-norm-results-20261016')
    status = 'failed'
    check = MacCheckpoint(seconds=870)
    try:
        names = ['rust-r1-native-norm-format-20261016',
                 'rust-r1-native-norm-declaration-20261016', 'rust-r1-native-norm-declaration-20261016-records',
                 'rust-r1-native-norm-kernel-20261016', 'rust-r1-native-norm-kernel-20261016-records',
                 'rust-r1-native-norm-comparison-20261016', 'rust-r1-native-norm-comparison-20261016-records']
        pins = [validate_root(ROOT/'artifacts'/name) for name in names]
        declaration = ROOT/'artifacts/rust-r1-native-norm-declaration-20261016'
        for pin in json.loads((declaration/'source-pins.json').read_bytes()):
            assert digest(ROOT/pin['path']) == pin['sha256'],pin['path']
        for pin in json.loads((declaration/'root-pins.json').read_bytes()):
            assert digest(ROOT/pin['path']/'root-closed.json') == pin['closure_sha256']
        comparison = ROOT/'artifacts/rust-r1-native-norm-comparison-20261016'
        s = json.loads((comparison/'summary.json').read_bytes())
        cases = json.loads((comparison/'case-comparisons.json').read_bytes())
        assert s['comparisons']==s['baseline_byte_exact']==49
        assert not s['local_gate_pass'] and s['candidate_failing_elements']==0
        assert s['case_SSE_nonincrease_count']==0 and s['elements_per_method']==124992
        assert not s['core_changed'] and s['full_forward_calls']==0
        resources = {}
        for name in [n for n in names if n.endswith('-records') or '-format-' in n]:
            e = json.loads((ROOT/'artifacts'/name/'exit.json').read_bytes())
            g = e['sampled_group_peak']
            assert e['returncode']==0 and e['elapsed_seconds']<870
            assert max(g['monitor_inclusive_footprint'],g['monitor_inclusive_rss'],e['child_wait_peak_rss_bytes'])<2*1024**3
            assert e['sampled_cache_bytes']<1536*1024**2
            resources[name]=e
        ratio = s['candidate_SSE']/s['baseline_SSE']
        phase = {'candidate':'standard Flex scalar LayerNorm, all seven modules and cases',
                 'decision':'rejected by preregistered same-input error gate',
                 'core_changed':False,'tolerance_changed':False,'R1_complete':False,'R2_started':False,
                 'training':False,'CARE_or_demand2015_reevaluation':False,'full_forward_calls':0,
                 'candidate_count':1,'next_candidate_selected':False}
        report = 'docs/results/banto-ai-rust-r1-native-norm-2026-10-16.md'
        text = f'''# Rust R1 — 標準LayerNorm候補は不採用（2026-10-16）

[実装計画](../research/banto-ai-rust-implementation-plan-2026-10-16.md)に沿い、全入力・全LayerNormへ共通に適用できる候補を一つ検証した。**Burn標準LayerNormは同一入力の二乗誤差が全7ケースで増えたため不採用。モデル本体は変更せず、R1は元の累積1点未達のまま**。許容差・weights・参照・Cargo.lock・依存featureを変更していない。

## 先に固定した仮説と判断条件

[固定条件](../../examples/configs/rust-r1-native-norm-20261016.json)とdeclaration rootを候補kernel実行前に保存した。候補は `burn::tensor::module::layer_norm`、epsilon=1e-5、既存Flex CPU/stdのみ。2blockの各3normとfinal_normの全7moduleへ一律に適用する方式であり、特定の店舗・発行日・失敗点を判断材料にしない。

算術上の根拠は、[PyTorchのRowwiseMoments](https://github.com/pytorch/pytorch/blob/v2.14.0/aten/src/ATen/native/cpu/moments_utils.h)と、pin済みBurn0.22.0の標準kernelがWelford方式のモーメント計算を使うこと。既存のbalanced二段階計算から標準operatorへ寄せることで、将来の学習経路と演算境界を共通化できる可能性も検討した。ただし参照はvectorized Welfordとcascade merge、Flexはscalar Welfordで、後者はinv_stdとgammaの積を先に求める。演算順が違うため、安定な方式であることから参照に近いと保証はしない。backwardの正しさは今回は未検証。

固定7ケースの保存済みPython経路入力を各moduleへ与え、候補49回・現行式49回を一度だけ実行した。現行式は保存済みRP出力49組とのbytes一致を必要条件とした。候補は全要素finite・元の2e-6+2e-5×abs(reference)以内、全体SSEの厳密減少、各ケースの全module合計SSE非増加を要求した。通過時だけ一般修正と元7ケースのfull確認を一度許可し、非通過時はモデル変更なしで停止する条件だった。

## 結果

| 項目 | 結果 |
| --- | --- |
| ケース / module / 比較 | 7 / 7 / 49 |
| 比較要素数（各方式） | {s['elements_per_method']:,} |
| 現行式の保存RPとのbytes一致 | 49 / 49 |
| 候補の許容差超過 | 0 |
| 現行式SSE | {s['baseline_SSE']:.12g} |
| 候補SSE | {s['candidate_SSE']:.12g} |
| 候補 / 現行SSE | {ratio:.6f}倍 |
| ケース別SSE非増加 | 0 / 7 |
| 採用条件 | 不通過 |

| ケース | 現行式SSE | 候補SSE | 候補/現行 |
| --- | --- | --- | --- |
'''
        for row in cases:
            text += f"| {row['case']} | {row['baseline_SSE']:.8g} | {row['candidate_SSE']:.8g} | {row['candidate_SSE']/row['baseline_SSE']:.4f} |\n"
        text += '''
SSEは同じ正規化出力の要素別差の平方和である。batch数の異なるケースを単純平均せず全要素集計とケース別を併記した。zeroとconstantなどで値が等しくても独立の追加標本とは数えない。許容差内という結果だけで、より誤差が大きい候補を採用しない。

## 採否・今後の境界

候補は不採用として保存した。モデル本体・標準forwardは実行も変更もしておらず、元の中間値1点が直ったか悪化したかは未評価。既存の最終予測通過・中間値1点未達というR1判定を保持し、R2のRust学習へ進まない。標準operatorが参照に近いという仮説は今回の有限入力では支持されなかった。これをWelford方式一般の劣位や保全性能の悪化に読み替えない。

同一条件のretryや二つ目の候補探索は行わない。次の有益な工程は、参照と現行式のモーメント計算・float32丸め位置のソース上の差を整理し、学習へ接続できる一つの共通方式を選べるか判断する設計レビューである。方式・有限比較・全体採否条件が定まるまでは新kernel/full forwardを起動しない。未達1点への係数調整、参照再生成、許容差緩和は行わない。

保全・点検支援第一優先、TimesFMを参考にした自作モデルの産業/需要実用性、学習を含むRust移植の目的を維持。CARE test/需要2015再評価・実学習・下流repo変更・新依存/取得・Git push・製品採用は0。需要調整2014以前、同休業mean28比較、四季の過小/過大非増加、観測のみ/欠測0評価分離も不変。

## 資源と保存

| 実行 | 秒 | 監視込みfootprint / RSS |
| --- | --- | --- |
'''
        for name,e in resources.items():
            g=e['sampled_group_peak']
            text += f"| {name} | {e['elapsed_seconds']:.3f} | {g['monitor_inclusive_footprint']:,} / {g['monitor_inclusive_rss']:,} B |\n"
        text += f'''
全exit0。親900/子870秒、physical footprintとpeak RSS各2GiB、build cache+target1.5GiB、旧artifact/EvidenceStore/stdio上限を維持。最終cache+targetは{disk_bytes():,}B。process group観測でcompiler/linkerを含むが、sample間の短命childを完全捕捉するhard OS capではない。Mac CPUでの候補診断のみ、Windows native/OS依存suiteは未実行、heartbeat PAUSED維持。

主要rootは `artifacts/rust-r1-native-norm-declaration-20261016`、`rust-r1-native-norm-kernel-20261016`、`rust-r1-native-norm-comparison-20261016` と各records。全source/stdio/exit/source pin/state/closureと集計・文書前後を `artifacts/rust-r1-native-norm-results-20261016-evidence` に保存。旧closed rootsと失敗を保持した。
'''
        headline = '標準Flex LayerNormを全7case×7moduleの同一入力49組/124,992要素で検証。現行RPのbytes再現49/49、候補の許容差超過0だがSSEは現行の約2.804倍、全7caseで増加し事前条件を不通過。'
        changes = {report:text}
        handoff = 'docs/current-handoff.md'
        changes[handoff] = ('## 最新 — 標準LayerNorm候補を不採用、core不変（2026-10-16）\n\n'
                            '[結果と固定条件](results/banto-ai-rust-r1-native-norm-2026-10-16.md)。'+headline+
                            ' 候補1方式で停止、full forward/モデル変更/学習0。元の累積1点未達とR1未合格・R2停止を維持。\n\n'
                            '次はモーメント計算とfloat32丸め位置のソース上の差を整理し、学習へ接続できる共通方式の根拠を判断する設計工程。方式と有限比較・全体採否条件を固定するまで新kernelを起動せず、同じ候補や1点向け探索を反復しない。許容差・旧成果/失敗/closed roots・各2GiB/build1.5GiB/時間・保存枠を保持。全source/stdio/exit/state/closureと文書前後はartifacts/rust-r1-native-norm-results-20261016-evidence。\n\n'
                            '保全第一・Rust学習目的と需要条件/2015停止、Windows別検証、heartbeat PAUSEDを維持。以下は旧記録。\n\n---\n\n'+(ROOT/handoff).read_text())
        for name,marker,entry in [
            ('docs/results/README.md','## Rustクレートの移植\n','- [Rust R1標準LayerNorm候補の不採用](banto-ai-rust-r1-native-norm-2026-10-16.md) — 全7caseでSSE増加、core不変。'),
            ('docs/research/README.md','## 文書\n','- [Rust R1標準LayerNormの固定比較と負の結果](../results/banto-ai-rust-r1-native-norm-2026-10-16.md) — 全49組、候補不採用。')]:
            before=(ROOT/name).read_text();assert marker in before
            changes[name]=before.replace(marker,marker+'\n'+entry+'\n',1)
        for name in ['docs/research/banto-ai-rust-implementation-plan-2026-10-16.md','docs/research/rust-small-forecaster-r0-2026-10-16.md']:
            changes[name]=re.sub(r'^状態:.*$','状態: R1a/既存3テストpass。標準LayerNorm候補は全7caseでSSE増加し不採用、core不変。元の累積1点未達でR1未合格・R2未着手。[最新結果](../results/banto-ai-rust-r1-native-norm-2026-10-16.md)。2026-10-16 JST。',(ROOT/name).read_text(),count=1,flags=re.M)
        roadmap='docs/research/research-roadmap.md'
        changes[roadmap]='## 現在 — 標準LayerNorm候補は不採用（2026-10-16）\n\n[結果](../results/banto-ai-rust-r1-native-norm-2026-10-16.md)。'+headline+' core不変・R1未達/R2停止。追加方式の根拠と有限条件を定めるまで再実行しない。以下は旧記録。\n\n---\n\n'+(ROOT/roadmap).read_text()
        sources=list(dict.fromkeys([Path(__file__),ROOT/'tools/public-data/rust_r1_native_norm.py',ROOT/'tools/verification_records.py',*source_files()]))
        out.sources(sources)
        out.json('phase.json',phase);out.json('root-pins.json',pins);out.json('resources.json',resources)
        evidence=ROOT/'artifacts/rust-r1-native-norm-results-20261016-evidence'
        with EvidenceStore(evidence) as store:
            store.write_json('phase',phase);store.write_json('root-pins',pins)
            store.write_json('document-paths',list(changes))
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
            for pin in pins:assert validate_root(ROOT/pin['root'])['closure_sha256']==pin['closure_sha256']
            for pin in json.loads((declaration/'source-pins.json').read_bytes()):assert digest(ROOT/pin['path'])==pin['sha256']
            store.write_terminal('terminal',{'exit':0,'decision':'candidate rejected; original core preserved; R1 incomplete','resources':check.check()})
        out.json('evidence-readback.json',verify_evidence(evidence,'complete'))
        out.json('summary.json',{**phase,'SSE_ratio':ratio,'comparisons':49,'elements':124992,'resources':check.check()})
        print(json.dumps({'published':True,'candidate_adopted':False,'core_changed':False,'SSE_ratio':ratio,'R1_complete':False}))
        status='complete'
    finally:
        out.close(status)


if __name__=='__main__':main()
