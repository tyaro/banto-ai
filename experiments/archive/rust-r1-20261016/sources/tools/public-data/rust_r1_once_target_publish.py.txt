"""Publish exactly one bounded64byte observation, without following its slot."""
import ast
import json
import re
import struct
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'models/mini-transformer'),str(ROOT/'tools/public-data')]
from metropt_multiday import Files,digest,verify_closed
from macos_demand_runtime import MacCheckpoint
from macos_rust_run import source_files,disk_bytes
from rust_r1_once_target import verify,check_abi,DECL,ABI,OUTPUT,sources as target_sources
from rust_r1_publish_preparation import validate_root
from verification_records import EvidenceStore
from care_rust_r0_close import verify_evidence

REPORT='docs/results/banto-ai-rust-r1-once-target-2026-10-16.md'
NEXT=ROOT/'examples/configs/rust-r1-once-slot-admission-20261016.json'
NAMES=[n for stem in ['rust-r1-once-target-declaration','rust-r1-once-target-abi','rust-r1-once-target']
    for n in [stem+'-20261016',stem+'-20261016-records']]

def read(p,name): return json.loads((p/name).read_bytes())

def main():
    out=Files(ROOT/'artifacts/rust-r1-once-target-results-20261016'); status='failed'; check=MacCheckpoint(seconds=870)
    try:
        verify(); pins=[validate_root(ROOT/'artifacts'/n) for n in NAMES]; assert all(p['status']=='complete' for p in pins)
        prior=read(DECL,'root-pins.json'); assert sum(p['status']=='failed' for p in prior)==7
        a=read(ABI,'abi.json'); check_abi(a)
        summary=read(OUTPUT,'summary.json'); assert summary['observation_complete'] and summary['target_code_bytes']==64
        assert summary['target_code_reads']==2 and summary['bytes_unchanged'] and summary['other_target_reads']==summary['target_executions']==summary['new_tensor_BLAS_calls']==0
        mapping=read(OUTPUT,'mapping.json'); assert mapping['admitted'] and len(mapping['queries'])==2
        assert [q['info']['is_submap'] for q in mapping['queries']]==[1,0]
        assert mapping['queries'][-1]['info']['protection']&5==5
        assert mapping['effective_begin']<=mapping['runtime_address'] and mapping['runtime_address']+64<=mapping['effective_end']
        raw=(OUTPUT/'code.bin').read_bytes(); region=read(OUTPUT,'region.json'); assert len(raw)==64 and digest(OUTPUT/'code.bin')==region['sha256']
        words=list(struct.unpack('<4I',raw[:16])); assert words==[0xf02ff871,0x9136e231,0xf9400230,0xd71f0a11]
        pc=region['image_virtual_address']; assert pc==0x1880e1a60
        w=words[0]; assert w&0x9f000000==0x90000000 and w&31==17
        imm=(((w>>5)&0x7ffff)<<2)|((w>>29)&3); imm=imm-(1<<21) if imm&(1<<20) else imm
        page=(pc&~4095)+(imm<<12)
        w=words[1]; assert w&0xff000000==0x91000000 and w&31==17 and (w>>5)&31==17
        add=((w>>10)&4095)<<(12*((w>>22)&1)); slot=page+add
        assert page==0x1e7ff0000 and slot==0x1e7ff0db8
        listing=(OUTPUT/'disassembly.stdout').read_text()
        for pc_text,insn in [('1880e1a60','adrp x17, 0x1e7ff0000'),('1880e1a64','add x17, x17, #0xdb8'),
            ('1880e1a68','ldr x16, [x17]'),('1880e1a6c','braa x16, x17')]:
            lines=[line for line in listing.splitlines() if line.strip().startswith(pc_text+':')]; assert len(lines)==1
            actual=re.sub(r'\s+',' ',lines[0].split(':',1)[1].strip()); assert actual.startswith(insn)
        reads=read(OUTPUT,'memory-reads.json'); assert len(reads)==5
        assert [r['label'] for r in reads]==['Mach-O header','Mach-O load commands','LC_FUNCTION_STARTS','fixed call target 64bytes','fixed call target identical recheck']
        assert all(r['bytes']==64 and r['returned_bytes']==64 and r['kern_return']==0 for r in reads[-2:])
        assert all(r['address']==mapping['runtime_address'] for r in reads[-2:])
        resources={}
        for n in NAMES:
            p=ROOT/'artifacts'/n
            if not (p/'exit.json').exists(): continue
            e=read(p,'exit.json'); g=e['sampled_group_peak']
            assert e['returncode']==0 and e['elapsed_seconds']<870 and e['sampled_cache_bytes']<1536*1024**2
            assert max(g['monitor_inclusive_footprint'],g['monitor_inclusive_rss'],e['child_wait_peak_rss_bytes'])<2*1024**3
            resources[n]=e
        maxfp=max(e['sampled_group_peak']['monitor_inclusive_footprint'] for e in resources.values())
        maxrss=max(max(e['sampled_group_peak']['monitor_inclusive_rss'],e['child_wait_peak_rss_bytes']) for e in resources.values())
        cache=disk_bytes(); assert cache<1536*1024**2
        manifest_sha=digest(ROOT/'crates/banto-ai/Cargo.toml')
        allgit=subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True,timeout=20)
        docgit=subprocess.run(['git','diff','--check','--','docs'],cwd=ROOT,capture_output=True,timeout=20)
        assert allgit.returncode==2 and re.fullmatch(rb'crates/banto-ai/Cargo\.toml:\d+: new blank line at EOF\.\n',allgit.stdout) and not allgit.stderr
        assert docgit.returncode==0
        phase={'scope':'one exact target64bytes after SDK layout and own-task VM bounds/protection proof',
            'SDK_ABI_size':84,'SDK_ABI_fields':23,'mapping_queries':2,'unique_code_bytes':64,'code_reads_including_recheck':2,
            'target_transfer_stub_identified':True,'target_prefix_bytes_used':16,'derived_slot_virtual':hex(slot),
            'slot_reads':0,'other_target_reads':0,'target_executions':0,'new_tensor_BLAS_calls':0,'full_model_calls':0,'training':False,
            'query_return_proved':False,'train_dispatch_proved':False,'private_once_encoding_proved':False,
            'old_warm_failure_preserved':True,'model_changed':False,'tolerance_changed':False,'R1_complete':False,'R2_started':False,'next_slot_unit_executed':False}
        derivation={'PC':hex(pc),'words':[hex(w) for w in words],'ADRP_signed_immediate_pages':imm,'page':hex(page),'ADD_immediate':add,
            'slot_virtual':hex(slot),'load':'LDR X16,[X17]','transfer':'BRAA X16,X17','pointer_value_observed':False,
            'adjacent_48bytes_not_followed':True,'full_function_boundary_assumed':False}
        body=f'''# Rust R1 — 固定call target64bytesの確認（2026-10-16）

**固定target0x1880e1a60の最大64bytesを範囲・権限確認後に読み、同じ64bytesの再照合も一致した。先頭16bytesはADRP→ADD→LDR→BRAAの間接転送stubで、pointer slot0x1e7ff0db8を導いた。そのslotや分岐先は読まず、公開API identity/query/train経路は未確定のまま工程を閉じた。** ターゲット実行・数値演算・full model・学習0。元warmの-1 gate失敗を保持。R1安定版累積1点未達/R2停止。

## 事前条件・SDK型の証明

[固定した64byte条件](../../examples/configs/rust-r1-once-call-target-admission-20261016.json)と[具体的な実行条件](../../examples/configs/rust-r1-once-target-execution-20261016.json)に従った。fresh declarationでsource、SDK Mach宣言、元BL selectors、libtorch/model/lock、開始時のCargo manifest、旧22rootsのclosureをpin。旧scopeの失敗7rootsもstatusを変えず保持した。元六関数codeは再読取りしていない。

SDK vm_region.hのpack4をPython側で推測するだけにせず、SDKをincludeした小さなC helperをpinしたclangでcompileした。C helperはsizeof/offsetof/constantsを出力するだけでMach APIやtargetを呼ばない。struct vm_region_submap_info_64は84bytes、V3 count21、全23fieldのoffset、関数引数用の各整数型size、READ1/EXECUTE4/KERN_SUCCESS0をctypes定義と照合した。全て一致、compile/helper exit0。SDK本文とhash、C source/binary/commands/stdioを保存した。

loaded libBLASのUUID31104d4f4a7e3fa79e1855937b2011f2、元libtorch_cpu SHA、torch gitと同一OS情報を検証。platformはJSONの表現へ正規化して比較し、前工程のtuple/list形式問題を繰り返していない。

## own-task mappingと64byte読取り

mach_vm_region_recurseはmach_task_selfだけに使った。要求addressは毎回同じtargetへ戻し、submapのときだけdepthを増やす上限16の手順を固定した。実際は2queryで終わった。

| depth | 結果 | 保護属性 | 次の処理 |
| --- | --- | --- | --- |
| 0 | targetを含むsubmap、returned count21 | READ | 同じtargetでdepth1へ |
| 1 | targetを含むleaf、returned count21 | READ+EXECUTE | 全64bytesの境界を確認 |

leaf/effective boundsは[{mapping['effective_begin']}, {mapping['effective_end']})、target runtime addressは{mapping['runtime_address']}。親submapとの共通範囲にもtarget..target+64が収まることを確認した。上位submapのREAD属性だけでleafを判断せず、返却されたleafのREAD+EXECUTEを確認した。region探査で別addressへ移動していない。

mach_vm_read_overwriteで64bytesを一度読み、同じ64bytesだけ一度再照合した。両方OS成功/返却64bytes、bytes不変。unique64bytes、SHA {region['sha256']}。これ以外のlive executable read0、pointer/data/TLS/config read0。Mach-O header/load commands/function-startsはlibrary identity用の既定上限内metadataとして分けて保存した。

## 命令から分かること

pinしたllvm-objdumpで非実行ELF containerの.textだけをdisassemble。これはMach-O原fileでも実行用binaryでもない。対象の先頭4命令は次の通り。

| image virtual PC | 命令 | 今回の解釈 |
| --- | --- | --- |
| 0x1880e1a60 | ADRP X17, 0x1e7ff0000 | PC relative page address |
| 0x1880e1a64 | ADD X17, X17, #0xdb8 | slot0x1e7ff0db8 |
| 0x1880e1a68 | LDR X16, [X17] | pointerをload |
| 0x1880e1a6c | BRAA X16, X17 | load値への認証付き間接transfer |

元machine wordsはf02ff871/9136e231/f9400230/d71f0a11。ADRPのsigned21bit page offsetとADD immediateをbytesから独立decodeし、listingとslotを照合した。これは行列積や初期化処理本体ではなくtransfer stub。関数全体の境界は仮定していない。残り48bytesにも似た並びは見えるが、隣のentryやslotを追っていない。

dladdr0だった位置に実際の転送命令があることは確認できたが、転送先の値や公開dispatch_onceとのidentityは依然未観測。元の直接API不一致を公開APIの破損や初期化失敗と解釈しない。元once値52638546を-1へ読み替えず、数値許容差も変えていない。

## 次工程

[一つの8byte slotだけを扱う次条件](../../examples/configs/rust-r1-once-slot-admission-20261016.json)を保存した。slotは今回の保存命令から導いた0x1e7ff0db8だけ。新たなfresh declarationとown-taskのreadable/bounds確認が必要。認証付きpointerの表現はSDKに根拠のある方法だけを使い、上位bitのmaskを推測しない。表現処理を証明できなければraw bytesと不明点を保持する。

次unitでもpointerの実行・認証・callee codeの読取り・BLAS/tensor/query/initializerはしない。公開entryとの比較はmetadataとして限定し、identityが得られるまでquery/train kernelを確定しない。今回のunitではslot内容/分岐先読取り0で停止し、この次工程はまだ実行していない。

## 資源・保護・OS分離

新規6rootsは全complete。全source/SDK/commands/stdio/exit/state/closure、layout proof、mapping全返答、raw64bytesと再照合、disassembly、派生slot、文書前後はartifacts/rust-r1-once-target-results-20261016と同-evidence。publication自身のstdio/exit/stateは同-records。

親900/子870秒、physical footprintとpeakRSS各2GiB、cache+target1.5GiB、元artifact/EvidenceStore/stdio上限を維持。今回最大監視込みfootprint {maxfp:,}B、RSS系 {maxrss:,}B、cache+target {cache:,}B。sample監視でありhard OS capではない。C helper/clang/linkerも同一process group監視下。

model.rs SHA acefec42e7506d807f7deae22269f30f9bf409a8c8cf9d1ddb59c2ef6af7fa80、lock/許容差/参照と開始時source pins不変。Cargo/default/製品側編集0。開始時から残るCargo.toml末尾空行により全体diff --checkはexit2、docs限定はexit0。manifestは開始時hash {manifest_sha}のまま保持し、本工程で修正していない。Rust core変更がないため既存Rustテスト/固定7caseを反復していない。

保全・点検支援第一、自作モデルの産業/需要での実用性、Rustの学習/推論/optimizer再開目的を維持。R1累積1点未達/R2停止、需要2015/CARE test再評価・学習・下流編集・Git push・製品採用0。需要2014以前調整、同休業mean28、四季過小/過大非増加、観測のみ/欠測0分離、heartbeat PAUSEDを維持。

SDK/Mach mapping/Accelerate/PAC transferの今回の証拠はMac固有。Windows固有機能・OS依存suiteは未実行で、共通RustモデルやWindows上での数値成立はこの観測で認定していない。
'''
        headline='固定call targetをown-task mapping/SDK型確認後に64bytes読取り、再照合一致。先頭16bytesはADRP/ADD/LDR/BRAA transfer stub、slot0x1e7ff0db8を導出。slot/分岐先は未読、数値演算/target実行0。'
        changes={REPORT:body}
        n='docs/current-handoff.md'; changes[n]='## 最新 — 固定64bytesで間接転送stubを確認（2026-10-16）\n\n[結果と次条件](results/banto-ai-rust-r1-once-target-2026-10-16.md)。'+headline+' SDK struct84bytes/23field/count21をCとctypesで照合、mapping2queryでREAD+EXECUTE leaf内64bytesを確認。元warm/once/API失敗を保持、query/train/private once値は未確定。model/lock/許容差/開始時manifest不変、R1安定版累積1点未達/R2停止。\n\n次は[固定した単一8byte slot条件](../examples/configs/rust-r1-once-slot-admission-20261016.json)。保存命令からのslot0x1e7ff0db8だけ、SDKに基づくpointer表現の扱いとmapping/boundsを先に固定。bit mask推測/認証/実行/callee code追跡はしない。元六関数やfailed scopesを再開せず、この次unitはまだ未実行。全証跡/文書前後はartifacts/rust-r1-once-target-results-20261016-evidence。\n\n各2GiB/build1.5GiB/時間/保存枠、既存成果/失敗/closed roots保護、保全第一/Rust学習目的、需要2015停止/2014以前調整/同休業mean28/四季両側非増加/観測欠測0分離、CARE test停止、Windows別検証、heartbeat PAUSED維持。Cargo末尾空行の全体diff --check exit2は開始時からの変更として保護、docs限定exit0。以下は旧記録。\n\n---\n\n'+(ROOT/n).read_text()
        for n,marker,entry in [('docs/results/README.md','## Rustクレートの移植\n','- [Rust R1 固定64byte呼出先と間接転送stub](banto-ai-rust-r1-once-target-2026-10-16.md) — SDK配置とVM境界を確認、単一slot導出までで閉鎖。'),('docs/research/README.md','## 文書\n','- [Rust R1 固定call target64bytesの結果](../results/banto-ai-rust-r1-once-target-2026-10-16.md) — transfer stubを確認、slot読取りは次の独立条件。')]:
            prior_text=(ROOT/n).read_text(); assert marker in prior_text; changes[n]=prior_text.replace(marker,marker+'\n'+entry+'\n',1)
        for n in ['docs/research/banto-ai-rust-implementation-plan-2026-10-16.md','docs/research/rust-small-forecaster-r0-2026-10-16.md']:
            changes[n]=re.sub(r'^状態:.*$','状態: R1a済み/R1bは安定版累積1点未達/R2停止。fixed64byte targetのtransfer stubと単一slotを特定、slot/callee未読。次は固定した8byte slotの独立条件、今回数値演算0。[最新結果](../results/banto-ai-rust-r1-once-target-2026-10-16.md)。2026-10-16 JST。',(ROOT/n).read_text(),count=1,flags=re.M)
        n='docs/research/research-roadmap.md'; changes[n]='## 現在 — call target64bytesはtransfer stub（2026-10-16）\n\n[結果](../results/banto-ai-rust-r1-once-target-2026-10-16.md)。'+headline+' R1未達/R2停止。次はSDK/pointer表現条件を守った単一slot工程。以下は旧記録。\n\n---\n\n'+(ROOT/n).read_text()
        sources=list(dict.fromkeys([Path(__file__),*target_sources(),NEXT,*source_files(),ROOT/'tools/verification_records.py',ROOT/'tools/public-data/care_rust_r0_close.py']))
        for p in sources:
            if p.suffix=='.py': ast.parse(p.read_text())
        out.sources(sources); out.json('phase.json',phase); out.json('root-pins.json',pins); out.json('prior-root-pins.json',prior)
        out.json('derivation.json',derivation); out.json('resources.json',resources); out.json('git-checks.json',{'all':{'exit':allgit.returncode,'stdout':allgit.stdout.decode()},'docs':{'exit':docgit.returncode},'manifest_preserved':True})
        out.json('next-admission-pin.json',{'path':str(NEXT.relative_to(ROOT)),'sha256':digest(NEXT),'executed':False})
        evidence=ROOT/'artifacts/rust-r1-once-target-results-20261016-evidence'
        with EvidenceStore(evidence) as store:
            store.write_json('phase',phase); store.write_json('root-pins',pins); store.write_json('prior-root-pins',prior); store.write_json('document-paths',list(changes))
            for i,p in enumerate(sources): store.write_bytes(f'source-{i}',p.read_bytes())
            for i,n in enumerate(changes):
                if (ROOT/n).exists(): store.write_bytes(f'before-{i}',(ROOT/n).read_bytes())
            for n,value in changes.items(): (ROOT/n).write_text(value)
            for i,n in enumerate(changes): store.write_bytes(f'after-{i}',(ROOT/n).read_bytes())
            for i,name in enumerate(NAMES):
                for j,p in enumerate(sorted((ROOT/'artifacts'/name).iterdir())): store.write_bytes(f'root-{i}-{j}',p.read_bytes())
            for target in re.findall(r'\]\(([^)]+)\)',body): assert ((ROOT/REPORT).parent/target).exists(),target
            verify()
            for p in [*pins,*prior]: assert validate_root(ROOT/p['root'])==p
            assert digest(ROOT/'crates/banto-ai/Cargo.toml')==manifest_sha
            store.write_json('documents-after',[{'path':n,'sha256':digest(ROOT/n)} for n in changes])
        ev=verify_evidence(evidence,'complete'); out.json('evidence-check.json',ev)
        out.json('summary.json',{**phase,'verified_new_roots':6,'verified_prior_roots':len(prior),'preserved_prior_failed_roots':7,
            'model_sha256':digest(ROOT/'crates/banto-ai/src/model.rs'),'resources':check.check()})
        print(json.dumps({'published':True,'unique_code_bytes':64,'slot':hex(slot),'slot_read':False,'evidence':ev})); status='complete'
    finally: out.close(status)

if __name__=='__main__': main()
