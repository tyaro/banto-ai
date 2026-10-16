"""Publish the original-output success and preregistered once-gate failure."""
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
from rust_r1_sgemm_warm_binding import verify_declaration,sources as diagnostic_sources,OUTPUT,DECL,CONFIG
from verification_records import EvidenceStore
from care_rust_r0_close import verify_evidence

NEXT=ROOT/'examples/configs/rust-r1-sgemm-once-semantics-admission-20261016.json'
REPORT='docs/results/banto-ai-rust-r1-sgemm-warm-binding-2026-10-16.md'
NAMES=['rust-r1-sgemm-warm-declaration-20261016','rust-r1-sgemm-warm-declaration-20261016-records',
       'rust-r1-sgemm-warm-binding-20261016','rust-r1-sgemm-warm-binding-20261016-records']

def read(root,name): return json.loads((root/name).read_bytes())

def main():
    out=Files(ROOT/'artifacts/rust-r1-sgemm-warm-results-20261016'); status='failed'; check=MacCheckpoint(seconds=870)
    try:
        verify_declaration()
        pins=[validate_root(ROOT/'artifacts'/n) for n in NAMES]
        assert [p['status'] for p in pins]==['complete','complete','failed','failed']
        comp=read(OUTPUT,'output-comparison.json'); fields=read(OUTPUT,'configuration-fields.json')
        assert comp['elements']==6144 and comp['bytes_equal'] and comp['bit_mismatches']==0
        assert digest(OUTPUT/'patch-output.bin')==comp['actual_sha256']==comp['original_sha256']
        before,after=fields['before'],fields['after']
        assert all(v['value']==0 for v in before.values())
        assert fields['stable'] and not fields['once_initialized'] and fields['proven_query_result'] is None
        assert {k:v['value'] for k,v in after.items()}=={'0x1e63de940':1,'0x1e63de950':2,'0x1e63de958':1,'0x1e63de960':1,'0x1e63de968':12582912,'0x1e63de980':0,'0x1e63de988':52638546}
        assert (OUTPUT/'configuration-after.bin').read_bytes()==(OUTPUT/'configuration-recheck.bin').read_bytes()
        failure=read(OUTPUT,'failure.json'); assert 'warm configuration not stable/initialized; no retry' in failure['traceback']
        meta=read(OUTPUT,'image-metadata.json'); assert meta['image_UUID']=='31104d4f4a7e3fa79e1855937b2011f2'
        reads=read(OUTPUT,'memory-reads.json')
        assert [r['label'] for r in reads]==['Mach-O header','Mach-O load commands','LC_FUNCTION_STARTS','warm data before single patch','warm data after single patch','warm data after stability recheck']
        assert len(reads)==6 and all(r['bytes']==r['returned_bytes'] and r['kern_return']==0 for r in reads)
        assert all(r['bytes']==88 for r in reads[-3:])
        resources={}
        for i,name in [(1,NAMES[1]),(3,NAMES[3])]:
            e=read(ROOT/'artifacts'/name,'exit.json'); assert e['returncode']==(0 if i==1 else 1)
            assert e['elapsed_seconds']<870 and e['sampled_cache_bytes']<1536*1024**2
            g=e['sampled_group_peak']; assert max(g['monitor_inclusive_footprint'],g['monitor_inclusive_rss'],e['child_wait_peak_rss_bytes'])<2*1024**3
            resources[name]=e
        maxfp=max(e['sampled_group_peak']['monitor_inclusive_footprint'] for e in resources.values())
        maxrss=max(max(e['sampled_group_peak']['monitor_inclusive_rss'],e['child_wait_peak_rss_bytes']) for e in resources.values())
        cache=disk_bytes(); assert cache<1536*1024**2
        phase={'scope':'one saved train-first patch Linear only; warm-binding gate failed, no retries',
            'CPU_linear_calls':1,'original_patch_values':6144,'original_patch_bit_mismatches':0,
            'data_bytes_per_read':88,'data_reads':3,'configuration_stable':True,
            'required_once_value':-1,'observed_once_value':52638546,'once_gate_pass':False,
            'initialization_completion_proved':False,'query_return_proved':False,'train_dispatch_proved':False,
            'new_executable_reads':0,'new_Rust_candidates':0,'full_model_calls':0,
            'model_changed':False,'tolerance_changed':False,'R1_complete':False,'R2_started':False,'training':False,
            'next_source_semantics_audit_executed':False}
        body=f'''# Rust R1 — patch出力一致、once条件未達で経路確定を停止（2026-10-16）

**保存済みtrain-first patchの一度のLinear実行は元の6,144値と全bit一致した。設定88bytesも実行後二度で一致したが、事前条件のonce値-1は得られず、52638546だった。warm-bindingは失敗として閉鎖し、query結果とtrain実行経路は未確定のまま保持した。** 再実行、追加の実行命令読取り、model全体比較、Rust候補、学習は行っていない。R1は安定版累積1点未達、R2停止。

## 固定条件と一度の実行

[事前条件](../../examples/configs/rust-r1-sgemm-warm-binding-admission-20261016.json)は変更しなかった。fresh declarationで保存入力・参照出力・元六関数roots・source/SDK・model/lockのhashを固定した。入力は閉鎖済みartifacts/rust-r1-linear-python-20261016のtrain-first/input、patch.weight、patch.biasだけ。比較参照は同rootのtrain-first/python/fusedであり、再生成していない。保存payload全体のhashを照合したが、数値として展開したのはこの4entryだけ。ラベルや元データセットは開いていない。

torch2.14.0/git08187d9e0fba026dc8217405802ab5381dc88d90、libtorch_cpu SHA ca979f3619acb92240c2ef46d7581b1a388761e0fccfa7dc491a7eaa153d584a、実load済みlibBLAS UUID31104d4f4a7e3fa79e1855937b2011f2を検証。VECLIB_MAXIMUM_THREADS=1をtorch import前に設定、torch/interopも1。Linearはmeta deviceで作りCPUランダム初期化を避け、保存値をCPU Parameterへ設定した。contiguous input[8,3,4,32]、weight[64,32]、bias[64]とstrideを記録し、eval/no_gradのforwardを一度だけ呼んだ。

出力[8,3,4,64]の6,144値はbit不一致0、bytes SHAは元参照と共に{comp['actual_sha256']}。これは元の補助patch演算との同一性確認であり、Rust modelの改善や元R1全体合格を意味しない。

## 観測と停止理由

同imageのreadable/non-executable __DATA_DIRTY内[0x1e63de938,0x1e63de990)だけをown-task mach_vm_read_overwriteで実行前一度、後二度読んだ。各88bytes、返却size/OS成功/boundsを検証。Mach-O header/load commands/function-starts metadataの読取り以外に実行codeの新規読取りはない。旧六関数scopeは再開していない。

| virtual address / type | 実行前 | 実行後（二度同一） |
| --- | ---: | ---: |
| 0x1e63de940 / int32 | 0 | 1 |
| 0x1e63de950 / int32 | 0 | 2 |
| 0x1e63de958 / int32 | 0 | 1 |
| 0x1e63de960 / int32 | 0 | 1 |
| 0x1e63de968 / uint64 | 0 | 12582912 |
| 0x1e63de980 / int32 | 0 | 0 |
| 0x1e63de988 / int64 (once predicate) | 0 | 52638546 |

raw bytesとfieldsは保持した。global@940=1だけでquery=1とは認定しない。事前条件はonce@988==-1を前提としており、保存query/coreの命令にはその値以外でonce helperへ進む枝がある。そのhelperの意味を未確認のまま、安定した非ゼロ値を「初期化完了」や「初期化失敗」と断定しない。stateのonce_initialized=falseは**この固定-1判定の結果**であり、実際の初期化が未完了と証明したものではない。

数値比較と設定保存の後、固定gateでAssertionError/exit1となった。artifacts/rust-r1-sgemm-warm-binding-20261016と同-recordsはfailedのまま保存し、成功rootへ書き換えていない。再試行・待機後の追加読取り・thread条件変更・TLS query直接呼出しは0。torchのNumPy未導入warningもstderrへ保存した。list/f32 packingで出力を比較し、このwarningはbit比較の失敗原因ではない。

## 次工程と解釈上の限界

[次のsource/design条件](../../examples/configs/rust-r1-sgemm-once-semantics-admission-20261016.json)を保存した。まずinstalled SDKのdispatch_once公開宣言・inline実装と版/hashを確認し、once predicateの表現と完了保証を区別する。実OS/runtimeへ対応する根拠が得られなければ不足として残す。別版sourceや今回の出力一致に合わせて-1条件を後付けで緩めない。

このsource工程に新たな数値演算、live memory読取り、選択leaf監査は含めない。保存事実だけで次の判断ができるかを先に整理し、必要な場合だけ有限の独立観測条件を別に事前固定する。今回はこのsource工程をまだ実行していない。query/dispatch経路を推定した次leafアドレスは固定していない。

## 状態・資源・OS分離

model.rs SHA acefec42e7506d807f7deae22269f30f9bf409a8c8cf9d1ddb59c2ef6af7fa80、Cargo/lock/default/許容差/元参照は不変。新Rustテストはdiagnostic-only変更のため追加実行していない。R1累積1点未達/R2停止、保全・点検支援第一、自作モデルの産業・需要での実用性、学習とoptimizer再開を含むRust移植の目的を維持。需要2015/CARE test再評価・学習・下流編集・Git push・製品採用0。需要2014以前調整、同休業mean28、四季両側非増加、観測のみ/欠測0分離、heartbeat PAUSEDを維持。

本観測はMacの実load済みAccelerateとown-process memoryに限る。Windows固有機能・OS依存suiteは未実行で、共通Rust coreの成立やWindowsでの結果とは分ける。

親900/子870秒、physical footprint/peakRSS各2GiB、build cache+target1.5GiBと既存artifact/EvidenceStore/stdio枠を維持。宣言/一度の実行の最大監視込みfootprint {maxfp:,}B、RSS系 {maxrss:,}B、cache+target {cache:,}B。監視はsample方式でhard OS capではない。全source/stdio/exit/state/closure、失敗、入力pins、前後raw設定、出力、文書前後を保存した。集約はartifacts/rust-r1-sgemm-warm-results-20261016と同-evidence、publication自体のstdio/exit/stateは同-records。
'''
        headline='保存済みtrain-first patchを一度だけ実行、元6,144値と全bit一致。88byte設定は前後で変化・実行後二度同一だが、once値52638546は固定条件-1を満たさずfailed閉鎖。query/train経路は未確定、追加実行/命令読取り0。'
        changes={REPORT:body}
        n='docs/current-handoff.md'
        changes[n]='## 最新 — patch一致、once条件未達でwarm-binding停止（2026-10-16）\n\n[結果と次条件](results/banto-ai-rust-r1-sgemm-warm-binding-2026-10-16.md)。'+headline+' 実際の初期化未完了と断定せず、-1 gate未達として保持。model/Cargo/default/許容差不変、R1安定版累積1点未達/R2停止。\n\n次は[固定したonce source/design工程](../examples/configs/rust-r1-sgemm-once-semantics-admission-20261016.json)。installed SDKのonce公開契約/inline/版を確認し、保存predicateの意味を根拠から整理する。新しい数値演算・live memory/code読取り・full model比較はこの工程に含めない。失敗root/元-1条件を上書きせず、global@940=1からのquery断定もしない。source工程まだ未実行。全証跡/文書前後はartifacts/rust-r1-sgemm-warm-results-20261016-evidence。\n\n各2GiB/build1.5GiB/時間/保存枠、既存成果/失敗/closed roots保護、保全第一/Rust学習目的、需要2015停止/2014以前調整/同休業mean28/四季両側非増加/観測欠測0分離、CARE test停止、Windows別検証、heartbeat PAUSED維持。以下は旧記録。\n\n---\n\n'+(ROOT/n).read_text()
        for n,marker,entry in [('docs/results/README.md','## Rustクレートの移植\n','- [Rust R1 patch一致とonce gate未達](banto-ai-rust-r1-sgemm-warm-binding-2026-10-16.md) — 一度の実行6,144値一致、warm-binding失敗保持、次はonce source契約。'),('docs/research/README.md','## 文書\n','- [Rust R1 once条件未達と次のsource工程](../results/banto-ai-rust-r1-sgemm-warm-binding-2026-10-16.md) — 出力一致とdispatch未確定を区別。')]:
            prior=(ROOT/n).read_text(); assert marker in prior; changes[n]=prior.replace(marker,marker+'\n'+entry+'\n',1)
        for n in ['docs/research/banto-ai-rust-implementation-plan-2026-10-16.md','docs/research/rust-small-forecaster-r0-2026-10-16.md']:
            changes[n]=re.sub(r'^状態:.*$','状態: R1a済み/R1bは安定版累積1点未達/R2停止。一度のpatchは元6,144値bit一致、once条件-1未達でwarm-binding失敗保持。次は版を固定したonce source契約の確認、追加演算0。[最新結果](../results/banto-ai-rust-r1-sgemm-warm-binding-2026-10-16.md)。2026-10-16 JST。',(ROOT/n).read_text(),count=1,flags=re.M)
        n='docs/research/research-roadmap.md'
        changes[n]='## 現在 — patch一致、once契約確認へ（2026-10-16）\n\n[結果](../results/banto-ai-rust-r1-sgemm-warm-binding-2026-10-16.md)。'+headline+' R1未達/R2停止。次はsourceだけでonce条件の意味を確認し、新演算/命令読取りはしない。以下は旧記録。\n\n---\n\n'+(ROOT/n).read_text()
        sources=list(dict.fromkeys([Path(__file__),*diagnostic_sources(),NEXT,*source_files(),ROOT/'tools/verification_records.py',ROOT/'tools/public-data/care_rust_r0_close.py',ROOT/'tools/public-data/rust_r1_publish_preparation.py']))
        out.sources(sources); out.json('phase.json',phase); out.json('root-pins.json',pins); out.json('resources.json',resources)
        out.json('next-admission-pin.json',{'path':str(NEXT.relative_to(ROOT)),'sha256':digest(NEXT),'executed':False})
        evidence=ROOT/'artifacts/rust-r1-sgemm-warm-results-20261016-evidence'
        with EvidenceStore(evidence) as store:
            store.write_json('phase',phase); store.write_json('root-pins',pins); store.write_json('document-paths',list(changes))
            for i,p in enumerate(sources): store.write_bytes(f'source-{i}',p.read_bytes())
            for i,n in enumerate(changes):
                if (ROOT/n).exists(): store.write_bytes(f'before-{i}',(ROOT/n).read_bytes())
            for n,value in changes.items(): (ROOT/n).write_text(value)
            for i,n in enumerate(changes): store.write_bytes(f'after-{i}',(ROOT/n).read_bytes())
            for i,name in enumerate(NAMES):
                for j,p in enumerate(sorted((ROOT/'artifacts'/name).iterdir())): store.write_bytes(f'root-{i}-{j}',p.read_bytes())
            for target in re.findall(r'\]\(([^)]+)\)',body): assert ((ROOT/REPORT).parent/target).exists(),target
            verify_declaration()
            for p in pins: assert validate_root(ROOT/p['root'])['closure_sha256']==p['closure_sha256']
            store.write_json('documents-after',[{'path':n,'sha256':digest(ROOT/n)} for n in changes])
        ev=verify_evidence(evidence,'complete'); out.json('evidence-check.json',ev)
        out.json('summary.json',{**phase,'verified_roots':4,'failed_roots_preserved':2,'model_sha256':digest(ROOT/'crates/banto-ai/src/model.rs'),'resources':check.check()})
        print(json.dumps({'published':True,'original_patch_bit_exact':True,'warm_gate_pass':False,'failed_roots_preserved':2,'evidence':ev})); status='complete'
    finally: out.close(status)

if __name__=='__main__': main()
