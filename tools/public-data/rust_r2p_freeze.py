"""Freeze an artificial-only R2P contract and exact rational loss expectations."""
import ast
from fractions import Fraction
import json
import math
import re
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'models/mini-transformer'),str(ROOT/'tools/public-data')]
from metropt_multiday import Files,digest,verify_closed
from macos_demand_runtime import MacCheckpoint
from rust_r1_publish_preparation import validate_root
from verification_records import EvidenceStore
from care_rust_r0_close import verify_evidence

INVENTORY=ROOT/'artifacts/rust-r2p-inventory-20261016'
DOC='docs/research/rust-r2p-synthetic-training-contract-2026-10-16.md'
SPEC='examples/configs/rust-r2p-synthetic-protocol-20261016.json'
FIXTURES='examples/configs/rust-r2p-synthetic-fixtures-20261016.json'
REPORT='docs/results/rust-r2p-inventory-and-specification-2026-10-16.md'

def read(p): return json.loads(p.read_bytes())

def analytic_loss(case):
    B,C,H,Q=case['shape']; assert Q==3
    assert len(case['prediction'])==B*C*H*3 and len(case['actual'])==B*C*H
    assert len(case['center'])==len(case['scale'])==B*C and all(v>0 for v in case['scale'])
    N=B*C*H*3; total=Fraction(0); gradient=[]
    for i,q in enumerate(case['prediction']):
        point=i//3; channel=point//H; tau=[Fraction(1,10),Fraction(1,2),Fraction(9,10)][i%3]
        r=(Fraction(str(case['actual'][point]))-Fraction(str(case['center'][channel])))/Fraction(str(case['scale'][channel]))-Fraction(str(q))
        total+=max(tau*r,(tau-1)*r)
        g=-tau if r>0 else 1-tau if r<0 else Fraction(1,2)-tau
        gradient.append(g/N)
    loss=total/N; assert loss==Fraction(case['expected_loss_rational'])
    if 'expected_gradient_rational' in case: assert gradient==[Fraction(x) for x in case['expected_gradient_rational']]
    return {'id':case['id'],'loss_rational':str(loss),'prediction_gradient_rational':[str(x) for x in gradient],
        'elements':N,'oracle_kind':'exact rational math on fixed artificial literals; not Torch float32 execution'}

def main():
    out=Files(ROOT/'artifacts/rust-r2p-specification-20261016'); status='failed'; check=MacCheckpoint(seconds=870)
    try:
        roots=[INVENTORY,INVENTORY.with_name(INVENTORY.name+'-records')]
        pins=[validate_root(p) for p in roots]; assert all(p['status']=='complete' for p in pins)
        originalpins=read(INVENTORY/'source-pins.json')
        for p in originalpins: assert digest(ROOT/p['path'])==p['sha256']
        inv=read(INVENTORY/'summary.json'); assert inv['inventory_complete'] and inv['cargo_tree_exit']==101
        assert 'cannot update the lock file' in (INVENTORY/'cargo-tree.stderr').read_text()
        dep=read(INVENTORY/'dependency-inventory.json'); assert dep['root_lock_edges_not_in_manifest']==['gemm']
        # Supplemental correction from the closed source snapshot, without rerunning Cargo.
        with zipfile.ZipFile(INVENTORY/'sources.zip') as z: lib=z.read('crates/banto-ai/src/lib.rs').decode()
        actual=sorted(re.findall(r'#\[cfg\(feature = "([^"]+)"\)\]',lib))
        assert actual==['fma-extension','fused-linear-extension','reference-normalization']
        assert digest(ROOT/'crates/banto-ai/src/lib.rs')==next(p['sha256'] for p in originalpins if p['path']=='crates/banto-ai/src/lib.rs')
        corrected={**dep,'lib_cfg_features':actual,'undefined_cfg_features':sorted(set(actual)-set(dep['manifest_features'])),
            'correction':'original raw inventory regex expected an extra closing parenthesis and returned an empty list; this supplement parses the already closed lib.rs snapshot; original root/source retained, Cargo not rerun'}
        spec=read(ROOT/SPEC); fx=read(ROOT/FIXTURES); r0path=ROOT/spec['numerical_contract']['path']; r0=read(r0path)
        assert digest(r0path)==spec['numerical_contract']['sha256'] and spec['numerical_contract']['unchanged']
        analytical=[analytic_loss(c) for c in fx['loss_cases']]
        assert len(analytical)==7 and len(fx['clip_cases'])==4 and len(fx['optimizer_cases'])==6
        counts=fx['finite_counts']; assert counts['Rust_optimizer_updates_total']==6+sum(v['updates'] for v in fx['toy_training']['Rust_trajectories'])==22
        assert len(fx['invalid_component_cases'])==counts['component_rejections']==6
        assert len(fx['invalid_checkpoint_cases'])==counts['checkpoint_rejections']==8
        assert len(fx['checkpoint_fault_points'])==counts['writer_cutpoints']==3
        assert set(fx['negative_mutations'])==set(fx['invalid_component_cases']+fx['invalid_checkpoint_cases']+fx['checkpoint_fault_points'])
        assert fx['toy_training']['schedule']==['A','B','C','D','A','C','B','D']
        assert sum(math.prod(p['shape']) for p in fx['toy_training']['parameters'].values())==9
        assert spec['this_turn']['optimizer_updates']==0 and spec['recognition']['R1_still_unmet']
        interpretation={'inventory_complete':True,'dependency_ready':False,'locked_offline_tree_exit':101,
            'undefined_cfg_features':corrected['undefined_cfg_features'],'source_counts':inv['source_derived_counts'],
            'new_training_components_implemented':False,'reference_Torch_bytes_generated':False,
            'analytic_loss_cases_verified':7,'specification_fixed':True,'loss_cases':7,'clip_cases':4,'optimizer_cases':6,
            'future_Rust_update_cap':22,'future_toy_parameters':9,'component_rejections':6,'checkpoint_rejections':8,'writer_cutpoints':3,
            'model_forward':0,'backward':0,'optimizer_updates':0,'pointer_reads':0,'build_or_tests':0,
            'manifest_or_lock_changed':False,'tolerance_changed':False,'R1_pass':False,'formal_R2_started':False}
        body=f'''# Rust人工学習の棚卸しと検証条件の固定

2026-10-16 JST。[人工R2P契約](../research/rust-r2p-synthetic-training-contract-2026-10-16.md)、[機械仕様](../../{SPEC})、[人工入力と期待値](../../{FIXTURES})を固定した。現実装の棚卸しと数式の検算を完了し、学習実装・数値参照生成・Rust学習/保存再開の実行はまだ行っていない。

## 現在の不足と入口条件

推論Tensor経路と名前付きstateはあるが、学習leaf登録、loss、named gradient、互換AdamW、完全な再開checkpointは未実装。source由来schemaは62tensor、学習対象59/109,024値、buffer3/348値。現parameter_count()は定数なので実列挙の試験結果とは区別した。neutral readerはAdamW項目を検査しても返さず、moment完全性/step/schedule/writer/復元を備えていない。

Cargo tree --locked --offlineはexit101でlock更新が必要。manifestにないgemmのroot edgeがlockに残る。Burnのinstalled optim featureはautodiffを有効にするため、それだけのための依存追加は不要と静的には読めるが、実効feature graphは確認できていない。Cargo/lockを編集せず、先に最小整合案を隔離copyで作る条件とした。

初版inventoryのfeature抽出regexに余分な閉じ括弧があり、空リストを出していた。閉鎖済みlib.rs snapshotから独立に再抽出し、未定義cfg featureはfma-extension/fused-linear-extension/reference-normalizationの3つと訂正した。初版root/sourceを変更せず、本rootのcorrected-dependency-inventory.jsonを正とする。Cargoの再実行はせず、実データ/ポインタも読んでいない。

## 固定した有限検証

loss7、global clip4、AdamW1更新6、小型affine1問題を固定。小型問題は人工parameter9値、乱数なし、固定8batch。Rustは連続8、取消保存4、別process復元4の3軌道で、独立AdamW込みの更新数上限22。取消はstep4の確定保存後/step5前を使い、別の学習軌道を増やさない。入力拒否6、checkpoint不正8、writer途中停止3地点も固定し、全変異をJSONへ列挙した。

7つのlossとgradientをFractionによる独立した有理数計算で検算し、L0〜L4の保存gradientと全loss期待値に一致した。これはfloat32のTorch参照や実学習ではない。次の参照生成でinstalled Torchとの一致を要求し、参照bytesを閉鎖してからRust受入を実行する。数学的式だけでPyTorchの丸め順を再現したとはしない。

loss/gradient/1更新/第1第2moment/8更新は元R0.1の条件を参照。小型問題のstep1とsteps2..8の割当ても事前固定した。同じRustの連続と復元はparameter/m/v/counter/schedule/probe bytes一致。既存の数値条件を緩めず、R1未達や正式R2停止を解除しない。

次はmanifest/lockの最小整合案と、固定した人工データの一度のPython参照生成。実データ/CARE weights・全SmallForecasterの人工学習接続はこのv1に含めない。全モデル接続は部品通過後の別条件とする。

## 保護と確認

ポインタ追跡は停止継続。source/manifest/lock/元R0.1/installed Burn/Torch sourceのhashを棚卸し前後と文書保存後に照合し、変更していない。今回の依存確認はbuild/testではなくreadonly metadata probe。Rust学習・forward/backward/optimizer更新・CARE/MetroPT test/需要2015再評価・新取得・下流編集・Git push・製品採用0。heartbeat PAUSED、保全第一、需要の2014以前/同休業mean28/四季両側非増加/観測欠測0分離を維持。

親900/子870秒、physical footprint/peakRSS各2GiB、cache+target1.5GiB、元artifact/EvidenceStore/stdio枠を維持。Mac共通CPUの仕様とWindows native/OS依存試験は分離し、後者は未実行。全source/metadata command/stdio/exit/state/closure、訂正、解析的期待値、条件pinsと文書前後はartifacts/rust-r2p-inventory-20261016と同-records、artifacts/rust-r2p-specification-20261016と同-evidenceへ保存。publication自身のstdio/exit/stateは同-records。
'''
        changes={REPORT:body}
        headline='現実装を棚卸し、人工loss7/clip4/AdamW6と9parameterの8対4+復元4、拒否/途中保存条件を固定。source上は62tensor/59trainable/109,024値。学習・参照数値生成は未実行。locked offline treeはexit101でmanifest/lock整合が次の入口。'
        changes['docs/current-handoff.md']='## 最新 — R2P棚卸しと人工検証条件を固定（2026-10-16）\n\n[現状と契約](research/rust-r2p-synthetic-training-contract-2026-10-16.md)・[機械仕様](../'+SPEC+')・[全fixture](../'+FIXTURES+')・[結果](results/rust-r2p-inventory-and-specification-2026-10-16.md)。'+headline+'\n\n次は元snapshotを保護した隔離copyで最小offline lock整合案（未使用gemm root edge、package/version不変）を作る。既存研究featureを自動復活しない。入口整合後、固定人工入力のTorch参照と独立期待値を一度生成・閉鎖してから、feature-gated小型学習/AdamW/checkpointを実装する。計画0/1の棚卸し/入力と判定規則は固定済みだが、数値参照bytesはまだない。受入commandのtraining-tests/r2p_synthetic targetは未追加。\n\n初版inventoryのcfg抽出regex不備はclosed snapshotの再抽出で訂正、元rootは保持。corrected-dependency-inventory.jsonを優先。現loaderはmomentsを検査しても保持せず再開不能、model葉も未追跡。原許容差/R1の残1点/正式R2実データ停止を維持。人工小型問題の通過をfull modelや保全性能の成立にしない。\n\nポインタ/once/TLS/PAC/vendor追跡は人の指示で停止。8byte slot条件は実行せず、通常の「進めて」で再開しない。各2GiB/build1.5GiB/時間/保存枠、既存変更/失敗/closed roots保護、CARE/MetroPT test凍結・需要2015停止/2014以前/同休業mean28/四季両側非増加/観測欠測0分離、Windows別検証、heartbeat PAUSED、下流編集/push/製品採用0。証跡はartifacts/rust-r2p-specification-20261016-evidence。以下は旧記録。\n\n---\n\n'+(ROOT/'docs/current-handoff.md').read_text()
        n='docs/research/banto-ai-rust-implementation-plan-2026-10-16.md'; text=(ROOT/n).read_text()
        text=re.sub(r'^状態:.*$','状態: 改訂2の棚卸し/人工R2P条件固定まで完了。pointer追跡停止、原R1は1点未達/正式R2停止。現manifest/lockはlocked offline確認で未整合、人工参照数値とRust学習は未実行。[固定条件](rust-r2p-synthetic-training-contract-2026-10-16.md)。2026-10-16 JST。',text,count=1,flags=re.M)
        start=text.index('## 次に着手する内容\n'); text=text[:start]+'''## 次に着手する内容

[現実装棚卸しと人工R2P条件](rust-r2p-synthetic-training-contract-2026-10-16.md)を固定済み。次は隔離copyでmanifest/lockの最小整合案を作り、package/versionや他作業を保護する。入口整合後に、固定人工入力のPython参照と独立期待値を一度生成して閉鎖する。その後、小型のloss/gradient/clip/AdamW/checkpointを実装・有限検証する。

今回R2P学習コードやtraining-tests targetは追加せず、数値参照生成・Rust学習を実行していない。原R1の追加候補は現在なし。原R1未達/正式R2停止、ポインタ追跡停止、CARE/需要の停止とheartbeat PAUSEDを維持する。
'''; changes[n]=text
        n='docs/research/banto-ai-practical-training-return-plan-2026-10-16.md'; text=(ROOT/n).read_text(); pos=text.index('\n\n## 主目的')
        text=text[:pos]+'\n\n工程0/1の追補: [現実装棚卸しと人工検証条件](rust-r2p-synthetic-training-contract-2026-10-16.md)を固定済み。現manifest/lockは未整合。次は最小offline整合案と固定人工参照の生成で、Rust学習/数値受入は未実行。'+text[pos:]; changes[n]=text
        n='docs/research/rust-small-forecaster-r0-2026-10-16.md'; text=(ROOT/n).read_text(); text=re.sub(r'^状態:.*$','状態: 原数値条件不変、R1は1点未達/正式R2停止。pointer追跡停止。[R2P棚卸しと人工仕様](rust-r2p-synthetic-training-contract-2026-10-16.md)を固定、実行はまだ。2026-10-16 JST。',text,count=1,flags=re.M); changes[n]=text
        changes['docs/research/research-roadmap.md']='## 現在 — 人工Rust学習の条件を固定（2026-10-16）\n\n[固定条件](rust-r2p-synthetic-training-contract-2026-10-16.md)。'+headline+' 次は保護した最小lock整合案→人工参照生成→限定Rust実装。pointer追跡/実データ/既読test再評価は停止したまま。以下は旧記録。\n\n---\n\n'+(ROOT/'docs/research/research-roadmap.md').read_text()
        for n,marker,entry in [('docs/research/README.md','## 文書\n','- [Rust現実装棚卸しと人工学習の固定条件](rust-r2p-synthetic-training-contract-2026-10-16.md) — 小型loss/gradient/AdamW/保存再開、manifest/lock未整合を保持。'),('docs/results/README.md','## Rustクレートの移植\n','- [Rust R2P棚卸しと仕様固定](rust-r2p-inventory-and-specification-2026-10-16.md) — readonly依存確認と人工条件、学習は未実行。')]:
            text=(ROOT/n).read_text(); assert marker in text; changes[n]=text.replace(marker,marker+'\n'+entry+'\n',1)
        sources=[Path(__file__),ROOT/'tools/public-data/rust_r2p_inventory.py',ROOT/DOC,ROOT/SPEC,ROOT/FIXTURES,r0path,
            ROOT/'tools/verification_records.py',ROOT/'tools/public-data/care_rust_r0_close.py']
        out.sources(sources); out.json('phase.json',interpretation); out.json('corrected-dependency-inventory.json',corrected)
        out.json('analytic-loss-oracles.json',analytical); out.json('root-pins.json',pins); out.json('protected-source-pins.json',originalpins)
        inputpins=[{'path':n,'sha256':digest(ROOT/n)} for n in [DOC,SPEC,FIXTURES]]
        out.json('input-and-protocol-pins.json',inputpins); out.json('tolerance-pin.json',{'path':str(r0path.relative_to(ROOT)),'sha256':digest(r0path),'tolerance':r0['tolerance']})
        evidence=ROOT/'artifacts/rust-r2p-specification-20261016-evidence'
        with EvidenceStore(evidence) as store:
            store.write_json('phase',interpretation); store.write_json('corrected-dependency-inventory',corrected); store.write_json('analytic-loss-oracles',analytical)
            store.write_json('root-pins',pins); store.write_json('protected-source-pins',originalpins); store.write_json('document-paths',[DOC,*changes])
            for i,p in enumerate(sources): store.write_bytes(f'source-{i}',p.read_bytes())
            for i,n in enumerate(changes):
                if (ROOT/n).exists(): store.write_bytes(f'before-{i}',(ROOT/n).read_bytes())
            for n,value in changes.items(): (ROOT/n).write_text(value)
            for i,n in enumerate(changes): store.write_bytes(f'after-{i}',(ROOT/n).read_bytes())
            for i,p in enumerate(roots):
                for j,f in enumerate(sorted(p.iterdir())): store.write_bytes(f'inventory-{i}-{j}',f.read_bytes())
            for doc,body in [(DOC,(ROOT/DOC).read_text()),(REPORT,body)]:
                for target in re.findall(r'\]\(([^)]+)\)',body): assert ((ROOT/doc).parent/target).exists(),target
            for p in originalpins: assert digest(ROOT/p['path'])==p['sha256']
            for p in inputpins: assert digest(ROOT/p['path'])==p['sha256']
            for p in pins: assert validate_root(ROOT/p['root'])==p
            store.write_json('documents-after',[{'path':n,'sha256':digest(ROOT/n)} for n in [DOC,*changes]])
        ev=verify_evidence(evidence,'complete'); out.json('evidence-check.json',ev)
        docs=subprocess.run(['git','diff','--check','--','docs'],cwd=ROOT,capture_output=True,timeout=20); out.json('document-check.json',{'exit':docs.returncode,'stdout':docs.stdout.decode(),'stderr':docs.stderr.decode()}); assert docs.returncode==0
        ast.parse(Path(__file__).read_text())
        out.json('summary.json',{**interpretation,'protocol_sha256':digest(ROOT/SPEC),'fixtures_sha256':digest(ROOT/FIXTURES),'protected_sources':len(originalpins),'resources':check.check()})
        print(json.dumps({'inventory_and_specification_fixed':True,'dependency_ready':False,'analytic_loss_cases':7,'training_executed':False,'evidence':ev})); status='complete'
    finally: out.close(status)

if __name__=='__main__': main()
