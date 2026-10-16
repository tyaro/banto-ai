"""Publish a purpose/sequence revision from saved aggregates, no model execution."""
import ast
import hashlib
import io
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'models/mini-transformer'),str(ROOT/'tools/public-data')]
from metropt_multiday import Files,digest
from macos_demand_runtime import MacCheckpoint
from macos_rust_run import source_files,disk_bytes
from rust_r1_publish_preparation import validate_root
from verification_records import EvidenceStore
from care_rust_r0_close import verify_evidence

PLAN='docs/research/banto-ai-practical-training-return-plan-2026-10-16.md'
CONFIG='examples/configs/banto-ai-practical-training-return-20261016.json'
R0='examples/configs/rust-small-forecaster-r0-20261016-r0.1.json'
REPORT='docs/results/banto-ai-rust-practical-training-replan-2026-10-16.md'
NAMES=['rust-r1-python-reference-20261016','rust-r1-burn-predictions3-20261016','rust-r1-compare3-20261016',
    'rust-r1-layer-comparison-20261016','rust-r1-context-model-decision-20261016','rust-r1-context-results-20261016',
    'rust-r1-fma-results-20261016','rust-r1-fused-linear-local-comparison-20261016',
    'rust-r1-once-target-results-20261016','rust-r1-once-target-20261016',
    'care-saved-diagnostics-20261016','care-learning-scores-20261016','metropt-m1-20261016/scores']

def read(root,name): return json.loads((root/name).read_bytes())
def once(text,a,b):
    assert text.count(a)==1,(a,text.count(a)); return text.replace(a,b,1)

def main():
    out=Files(ROOT/'artifacts/rust-practical-training-replan-20261016'); status='failed'; check=MacCheckpoint(seconds=870)
    try:
        contract=json.loads((ROOT/CONFIG).read_bytes()); assert digest(ROOT/R0)==contract['numerical_contract']['sha256']
        assert not contract['pointer_tracking']['slot_read_allowed'] and not contract['formal_R2']['real_training_allowed_now']
        protected=list(dict.fromkeys([p for p in source_files() if p.suffix in ['.rs','.toml'] or p.name=='Cargo.lock']+
            [ROOT/R0,ROOT/'examples/configs/rust-r1-once-slot-admission-20261016.json',
                ROOT/'examples/configs/rust-r1-once-call-target-admission-20261016.json',
                ROOT/'examples/configs/rust-r1-once-api-binding-20261016.json']))
        codepins=[{'path':str(p.relative_to(ROOT)),'sha256':digest(p)} for p in protected]
        pins=[validate_root(ROOT/'artifacts'/n) for n in NAMES]; assert all(p['status']=='complete' for p in pins)
        comparison=ROOT/'artifacts/rust-r1-compare3-20261016'; s=read(comparison,'summary.json')
        rows=read(comparison,'tensor-comparisons.json'); bad=[r for r in rows if r['failing_elements']]
        assert not s['parity_pass'] and s['elements_compared']==389214 and len(bad)==s['failing_elements']==1
        row=bad[0]; p=row['failure_examples'][0]
        assert row['case']=='train-last' and row['tensor']=='blocks.1' and p['index']==3450
        r0=json.loads((ROOT/R0).read_bytes()); tol=r0['tolerance']['normalized_activation']
        assert p['limit']==tol['atol']+tol['rtol']*abs(p['reference'])
        last={name:{'elements':sum(r['elements'] for r in rows if r['tensor']==name),
                    'failures':sum(r['failing_elements'] for r in rows if r['tensor']==name)}
              for name in ['normalized_quantiles','quantiles']}
        assert all(v=={'elements':6048,'failures':0} for v in last.values())
        layers=read(ROOT/'artifacts/rust-r1-layer-comparison-20261016','summary.json')
        assert layers['node_comparisons']==385 and layers['local_failing_elements']==0 and layers['total_failing_elements']==1
        candidate=read(ROOT/'artifacts/rust-r1-context-model-decision-20261016','summary.json'); assert not candidate['candidate_adopted'] and candidate['model_restored_byte_exact']
        gemm=read(ROOT/'artifacts/rust-r1-fused-linear-local-comparison-20261016','summary.json')
        assert gemm['candidate_equals_baseline_bytes']==154 and not gemm['local_gate_pass']
        care=read(ROOT/'artifacts/care-saved-diagnostics-20261016','summary.json'); assert care['neural_category_counts']=={'not-three-consecutive':8,'never-exceeds':1,'detected':3}
        assert care['normal_false_episode_count']==3 and care['all_original_outcomes_unchanged']
        caredecision=read(ROOT/'artifacts/care-learning-scores-20261016','decision.json'); assert all(caredecision['criteria'].values())
        facts={'R1_baseline':{'case':row['case'],'tensor':row['tensor'],**p,'elements':s['elements_compared'],
            'failures':s['failing_elements'],'excess_over_limit':p['absolute_error']-p['limit'],
            'excess_percent_of_limit':100*(p['absolute_error']/p['limit']-1),'final_outputs':last,
            'local_comparisons':385,'local_failures':0,'R1_pass':False},
            'CARE_saved':{'detected':3,'events':12,'missed':9,'normal_false_episodes':3,'four_exploratory_criteria_pass':True,'business_accepted':False},
            'context_candidate_adopted':False,'fused_linear_candidate_adopted':False,'new_model_or_score_runs':0}
        assert digest(ROOT/'crates/banto-ai/src/model.rs')=='acefec42e7506d807f7deae22269f30f9bf409a8c8cf9d1ddb59c2ef6af7fa80'
        phase={'scope':'planning revision and audit of existing aggregate results only','pointer_tracking':'STOPPED_BY_HUMAN',
            'tolerances_changed':False,'R1_pass':False,'formal_R2_real_training':'STOPPED_PENDING_R1',
            'synthetic_R2P':'planned_not_executed','R1_new_candidate':None,'R1_future_candidate_cap':1,
            'model_forward':0,'backward':0,'optimizer_updates':0,'new_scores':0,'live_memory_reads':0,'build_or_tests':0,
            'CARE_test_reevaluation':False,'demand2015_reevaluation':False,'downstream_changes':False,'git_push':False,'heartbeat':'PAUSED'}
        changes={}
        implementation='docs/research/banto-ai-rust-implementation-plan-2026-10-16.md'; text=(ROOT/implementation).read_text()
        text=re.sub(r'^状態:.*$','状態: 実用性/Rust学習へ復帰する改訂2。ポインタ追跡停止、R1は中間値1点未達を保持。人工データのR2Pを独立準備し、正式R2実データ学習は停止を維持。[改訂詳細](banto-ai-practical-training-return-plan-2026-10-16.md)。2026-10-16 JST。',text,count=1,flags=re.M)
        text=once(text,'計画ID: BANTO-AI-RUST-PLAN-20261016-v1。','計画ID: BANTO-AI-RUST-PLAN-20261016-v2。旧v1全文は今回の文書前後証跡へ保存。')
        marker='## 配置と責務\n'
        insert='''## 改訂2の優先事項

[実用性とRust学習へ戻る計画](banto-ai-practical-training-return-plan-2026-10-16.md)を現在の作業順として優先する。OSの初期化・転送stub・pointer追跡は停止し、保存済み8byte slot条件は実行しない。原R0.1の許容差・正式R1条件は変えない。

R1未達の間は、人工入力/label/parameterだけのloss・gradient・clip・AdamW・保存再開を独立したR2Pとして準備できる。正式R2や実データ学習への移行とは区別する。次は現source/manifest/lock/featureと学習graphの不足整理、人工fixture仕様固定。R1の追加候補は一般的根拠がある場合だけ最大1方式、局所一巡/通過後の全7case一回に限る。根拠がなければ実験0で未達保留とする。

'''
        text=once(text,marker,insert+marker)
        text=once(text,'この構成は作成予定である。CLIの外部公開や追加crate、ネットワークAPIは最初のbuildには含めない。',
            'crates/banto-aiの推論/loader/CLIは実装され、過去のCPU build結果を保存済み。train moduleや完全な学習checkpointは未実装。現manifestの整合確認を次に行い、CLIの外部公開や追加crate、ネットワークAPIは含めない。')
        text=once(text,'| 3 | R2 学習と保存再開 |','| 3a | R2P 人工学習基盤の独立準備 | 人工fixture、loss/gradient/clip/AdamW、8対4+復元+4 | 元の数値条件で部品/再開を検証。R1合格や実データ学習とは数えない |\n| 3b | R2 学習と保存再開 |')
        text=once(text,'順序1〜3を最初の実装範囲とする。','次の着手はR2Pの現状整理と人工fixture仕様固定。正式R2は原R1とR2Pの完了後に限る。')
        text=once(text,'R0で固定した許容差に達したらR1を終了する。高速化・GPU・量子化・モデル拡張は後回しにする。',
            'R0で固定した全条件に達した場合だけR1を合格とする。追加修正は改訂2の最大1方式/一巡条件を守り、根拠がなければ未達保留。OS内部追跡や点ごとの調整はしない。高速化・GPU・量子化・モデル拡張は後回しにする。')
        text=once(text,'### R2で学習と再開を移す\n','### R2で学習と再開を移す\n\n下記は正式R2の条件であり、原R1通過前の実データ学習は停止したまま。先行するR2Pは人工state/label/scheduleだけで同じ学習部品と再開を検証し、実行前に別fixtureを固定する。R2Pの実行も今回の計画改訂では開始していない。\n')
        start=text.index('## 最初に着手する内容\n')
        text=text[:start]+'''## 次に着手する内容

現source/manifest/lock/featureの整合と、学習可能なparameter登録・graph・neutral配置の不足を整理する。その上でR2Pの人工fixtureと独立期待値、比較対象、既存許容差、有限実行/保存先を固定する。今回の改訂ではコード・依存・推論・backward・学習を実行していない。

R1の追加候補は現在ない。一般修正の根拠がなければ探査を延長せず、R1未達と実用性の未確認を明記したまま独立準備を進める。正式R2、CARE test再評価、需要2015、下流統合・製品採用は開始しない。heartbeatはPAUSEDを維持する。
'''
        changes[implementation]=text
        n='docs/research/rust-small-forecaster-r0-2026-10-16.md'; text=(ROOT/n).read_text()
        text=re.sub(r'^状態:.*$','状態: 原R0.1の数値条件不変。R1は1点未達/正式R2停止。ポインタ追跡を停止し、人工データのみのR2Pを独立準備する[改訂2](banto-ai-practical-training-return-plan-2026-10-16.md)を作業順へ反映。2026-10-16 JST。',text,count=1,flags=re.M)
        text=once(text,'今回はクレート未作成。','推論クレートは実装済み、学習部品は未実装。')
        text=once(text,'## 次の順序と停止条件\n','## 次の順序と停止条件\n\n改訂2では原R1→正式R2の合格順を維持し、人工入力/label/parameterのみのR2P準備を独立して先行する。これは数値条件の変更や実データ学習停止の解除ではない。OS/vendor pointer追跡は停止。具体的な次工程は[復帰計画](banto-ai-practical-training-return-plan-2026-10-16.md)の0/1とする。以下は正式認定の条件。\n')
        text=once(text,'現在の次工程はR1の実装と有限数値確認。','現在の次工程は現実装の整合整理とR2P人工fixtureの仕様固定。')
        changes[n]=text
        n='docs/research/timesfm-inspired-practical-evaluation-plan-2026-10-16.md'; text=(ROOT/n).read_text(); first=text.index('\n')
        text=text[:first+1]+'''\n## 現在の優先順位

[実用性検証とRust学習へ戻る改訂2](banto-ai-practical-training-return-plan-2026-10-16.md)を優先する。ポインタ追跡は停止。MetroPT/CAREの既存成果と負の結果を再利用し、保全・点検支援を第一優先に、人工データのRust学習部品/保存再開を独立準備する。R1の1点未達と原許容差を維持し、正式R2実データ学習・CARE test/需要2015再評価は停止したまま。以下の各実行時点の記録は履歴として保持する。
'''+text[first+1:]
        text=once(text,'今回実装/学習は開始せず、[R0.1数値契約](rust-small-forecaster-r0-2026-10-16.md)は不変。',
            'Rust推論の実装と固定比較は保存済みでR1は1点未達。今回の改訂では新実装/学習を開始せず、[R0.1数値契約](rust-small-forecaster-r0-2026-10-16.md)は不変。')
        changes[n]=text
        n='crates/banto-ai/README.md'; text=(ROOT/n).read_text(); marker='## 研究用FMA拡張\n'
        note='''## 現在の研究順序

[実用性とRust学習へ戻る計画](../../docs/research/banto-ai-practical-training-return-plan-2026-10-16.md)を優先する。OS/vendor内部のpointer追跡は停止。原R1は1点未達のまま、人工データだけのloss/gradient/AdamW/保存再開をR2Pとして独立準備する。正式R2実データ学習は原R1通過まで開始しない。今回の計画改訂でコードや学習は実行していない。

上のbuild/test結果と下の拡張は各保存時点の構成に対する記録である。現Cargo manifestにはこれらの研究用feature定義がないため、sourceが存在するだけで現在利用できるとはしない。manifest/lock/sourceの整合を先に確認し、他作業の変更を保護する。原許容差は維持する。

'''
        text=once(text,marker,note+marker); changes[n]=text
        headline='人の指示でpointer/once/TLS/PAC/vendor内部追跡を停止。既存成果を整理し、原許容差/R1の1点未達を維持。人工データだけのRust学習部品・保存再開をR2Pとして独立準備する。正式R2実データ学習は停止を維持。'
        changes['docs/current-handoff.md']='## 最新 — ポインタ追跡停止、実用性とRust学習へ戻る改訂2（2026-10-16）\n\n[復帰計画](research/banto-ai-practical-training-return-plan-2026-10-16.md)・[機械条件](../'+CONFIG+')・[整理結果](results/banto-ai-rust-practical-training-replan-2026-10-16.md)。'+headline+' 旧8byte slot条件は履歴として保存し実行しない。通常の「進めて」で再開しない。\n\n次は計画0/1：現source/manifest/lock/featureと学習graphの不足整理→人工fixture/期待値/元許容差/有限回数を固定。コード/学習は今回未実行。一般的根拠のある追加R1候補は最大1方式、局所一巡/通過後全7case一回。現在候補なし、根拠がなければ実験0で未達保留。R1を通過扱いにせず、人工R2Pと正式R2を混同しない。\n\n安定版残差はtrain-last blocks.1 index3450、差2.7418136597e-6/限界2.5676221848e-6（限界比6.784%超）。最終出力各6,048値pass、同一入力局所385比較超過0だがgradient/更新の影響は未確認。context候補index183は別で、不採用。CARE3/12・9未検知/正常false3、MetroPTの改善と悪化を凍結再利用する。\n\n各2GiB/build1.5GiB/時間/保存枠、既存変更/失敗/closed roots保護。CARE test/需要2015停止、2014以前調整/同休業mean28/四季両側非増加/観測欠測0分離、Windows別検証、heartbeat PAUSED、下流編集/push/製品採用0を維持。以下のpointer系「次工程」は旧記録で、本改訂により停止。証跡はartifacts/rust-practical-training-replan-20261016-evidence。\n\n---\n\n'+(ROOT/'docs/current-handoff.md').read_text()
        changes['docs/research/research-roadmap.md']='## 現在 — 実用性とRust学習へ復帰（2026-10-16）\n\n[改訂2](banto-ai-practical-training-return-plan-2026-10-16.md)。'+headline+' 次は現実装の整合整理と人工fixture仕様固定。R1追加対応は一般候補最大1/局所一巡/全7case一回、根拠なしなら実験0で未達保留。CARE/MetroPT testは凍結し、需要条件・Windows分離・heartbeat PAUSEDを維持。以下のpointer追跡予定は旧記録であり実行しない。\n\n---\n\n'+(ROOT/'docs/research/research-roadmap.md').read_text()
        for n,marker,entry in [('docs/research/README.md','## 文書\n','- [実用性検証とRust学習へ戻る改訂2](banto-ai-practical-training-return-plan-2026-10-16.md) — pointer追跡停止、残1点の対応上限、人工R2Pと正式R2を分離。'),
            ('docs/results/README.md','## Rustクレートの移植\n','- [実用性とRust学習への計画改訂結果](banto-ai-rust-practical-training-replan-2026-10-16.md) — 保存成果だけを整理、許容差不変・学習未実行。')]:
            text=(ROOT/n).read_text(); assert marker in text; changes[n]=text.replace(marker,marker+'\n'+entry+'\n',1)
        body=f'''# 実用性検証とRust学習へ戻る計画改訂結果

2026-10-16 JST。[改訂2](../research/banto-ai-practical-training-return-plan-2026-10-16.md)を保存し、人の指示どおりpointer追跡を停止した。既存成果から実用性とRust学習の未確認部分を整理した。新しいモデル実行・学習・評価は行っていない。

## 判断と次工程

原R1は389,214要素中1点未達、最終正規化/元単位分位点は各6,048値pass。同一入力385局所比較の超過0を保存集計と照合。残差index3450の超過は{facts['R1_baseline']['excess_over_limit']:.12g}、限界比{facts['R1_baseline']['excess_percent_of_limit']:.6f}%。小ささだけで無視せず、学習gradient/更新への影響は未確認とした。context候補index183とは分離した。

正式R1を合格にするには元の全条件が必要。bit一致やOS内部の完全解明は追加要件にしない。追加修正は数学/公開Rust演算に根拠のある一般方式を最大1つ、局所一巡と通過後の固定7case全体一回まで。現在新候補なし、根拠がなければ実験0で未達保留とする。

R1未達でも人工データだけの学習部品と保存再開を独立したR2Pとして準備できるよう、作業順を改訂した。人工R2Pは元のloss/gradient/parameter/moment許容差と同backend再開bytes一致を使い、正式R1/R2合格とは数えない。実データの正式R2は原R1通過後という条件を維持。次の具体的な工程は現source/manifest/lock/feature/学習graphの不足整理と人工fixtureの仕様固定。

保全ではCARE検知3/12・未検知9・正常false3、native支持差を保持。MetroPT M1の探索的改善と一部悪化、区間coverage不足も[既存結果](metropt-macos-m1-2026-10-16.md)へ帰属した。既読testの追加評価や校正は行わない。業務上の先行時間・誤警報の必要条件と、移植/学習の正しさを別判定する。

## 保護と確認

R0.1 JSON SHA {digest(ROOT/R0)} は不変。model/manifest/lockを含む{len(codepins)} protected filesと、元13 artifact rootsのclosureを保存し、文書更新後に同じhashを確認した。関連する旧pointer条件JSONやfailed rootsを上書き/削除していない。前後の計画・引継ぎ・READMEはfresh artifact/EvidenceStoreへ保存した。

今回の範囲は既存summary/比較集計の照合と文書改訂だけ。新forward/backward/optimizer更新/score/SDK-memory read/build/テスト/新データ/外部送信/Git push/製品変更0。既存test成功を現manifestで再検証したとはしない。現manifestの研究feature不整合は次の棚卸し事項とし、今回変更しなかった。

親900/子870秒、physical footprint/peakRSS各2GiB、cache+target1.5GiBと元artifact/EvidenceStore/stdio枠を維持。Macの文書/保存集計確認と、Windows native/OS固有機能の未実施を分ける。CARE test/需要2015停止、2014以前調整/同休業mean28/四季過小量・過大量非増加/観測と欠測0分離、heartbeat PAUSEDを維持。

集約はartifacts/rust-practical-training-replan-20261016、文書前後・source・根拠の集計・closure pinsは同-evidence、publication自身のstdio/exit/stateは同-records。今回のplan artifactがcompleteであることは、R1や学習が合格した意味ではない。
'''
        changes[REPORT]=body
        sources=list(dict.fromkeys([Path(__file__),ROOT/PLAN,ROOT/CONFIG,ROOT/R0,ROOT/'tools/verification_records.py',
            ROOT/'tools/public-data/rust_r1_publish_preparation.py',ROOT/'tools/public-data/care_rust_r0_close.py',*source_files()]))
        out.sources(sources); out.json('phase.json',phase); out.json('facts.json',facts); out.json('root-pins.json',pins)
        out.json('protected-file-pins.json',codepins); out.json('contract-pin.json',{'path':R0,'sha256':digest(ROOT/R0),'tolerances':r0['tolerance']})
        before=io.BytesIO()
        with zipfile.ZipFile(before,'w',zipfile.ZIP_DEFLATED) as z:
            for n in changes:
                if (ROOT/n).exists(): z.writestr(n,(ROOT/n).read_bytes())
        out.write('documents-before.zip',before.getvalue())
        evidence=ROOT/'artifacts/rust-practical-training-replan-20261016-evidence'
        with EvidenceStore(evidence) as store:
            store.write_json('phase',phase); store.write_json('facts',facts); store.write_json('root-pins',pins); store.write_json('protected-file-pins',codepins)
            store.write_json('document-paths',[PLAN,*changes]); store.write_bytes('new-plan',(ROOT/PLAN).read_bytes()); store.write_bytes('new-scope',(ROOT/CONFIG).read_bytes())
            for i,pin in enumerate(pins):
                p=ROOT/pin['root']; store.write_bytes(f'root-closure-{i}',(p/'root-closed.json').read_bytes())
                for name in ['summary.json','decision.json']:
                    if (p/name).exists(): store.write_bytes(f'aggregate-{i}-{name}',(p/name).read_bytes())
            for i,p in enumerate(sources): store.write_bytes(f'source-{i}',p.read_bytes())
            for i,n in enumerate(changes):
                if (ROOT/n).exists(): store.write_bytes(f'before-{i}',(ROOT/n).read_bytes())
            for n,value in changes.items(): (ROOT/n).write_text(value)
            for i,n in enumerate(changes): store.write_bytes(f'after-{i}',(ROOT/n).read_bytes())
            for doc,text in [(PLAN,(ROOT/PLAN).read_text()),(REPORT,body)]:
                for target in re.findall(r'\]\(([^)]+)\)',text):
                    if not target.startswith('http'): assert ((ROOT/doc).parent/target).exists(),(doc,target)
            for p in codepins: assert digest(ROOT/p['path'])==p['sha256']
            for p in pins: assert validate_root(ROOT/p['root'])==p
            assert r0['tolerance']==json.loads((ROOT/R0).read_bytes())['tolerance']
            store.write_json('documents-after',[{'path':n,'sha256':digest(ROOT/n)} for n in [PLAN,*changes]])
        ev=verify_evidence(evidence,'complete'); out.json('evidence-check.json',ev)
        docs=subprocess.run(['git','diff','--check','--','docs','crates/banto-ai/README.md'],cwd=ROOT,capture_output=True,timeout=20)
        out.json('document-diff-check.json',{'exit':docs.returncode,'stdout':docs.stdout.decode(),'stderr':docs.stderr.decode()}); assert docs.returncode==0
        for p in [Path(__file__)]: ast.parse(p.read_text())
        cache=disk_bytes(); assert cache<1536*1024**2
        out.json('summary.json',{**phase,'verified_artifact_roots':len(pins),'protected_files':len(codepins),
            'updated_documents':len(changes),'new_plan':PLAN,'cache_bytes':cache,'resources':check.check()})
        print(json.dumps({'plan_revised':True,'pointer_tracking_stopped':True,'R1_still_unmet':True,'synthetic_R2P_planned_only':True,'evidence':ev})); status='complete'
    finally: out.close(status)

if __name__=='__main__': main()
