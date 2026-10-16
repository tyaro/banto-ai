"""Close SDK contract audit and preserve both API-binding stops."""
import ast
import difflib
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
from rust_r1_once_contract import verify,DECL,SOURCE,CONFIG,BIND,WARM,PUBLIC,sources as original_sources,branch
from rust_r1_once_contract_repair import BDECL as REPAIR_DECL,sources as repaired_sources
from verification_records import EvidenceStore
from care_rust_r0_close import verify_evidence

REPORT='docs/results/banto-ai-rust-r1-once-contract-2026-10-16.md'
NEXT=ROOT/'examples/configs/rust-r1-once-call-target-admission-20261016.json'
NAMES=[n for stem in ['rust-r1-once-source-declaration','rust-r1-once-source','rust-r1-once-api-declaration',
    'rust-r1-once-api-binding','rust-r1-once-api-repair-declaration','rust-r1-once-api-repair-binding']
    for n in [stem+'-20261016',stem+'-20261016-records']]

def read(path,name): return json.loads((path/name).read_bytes())

def main():
    out=Files(ROOT/'artifacts/rust-r1-once-results-20261016'); status='failed'; check=MacCheckpoint(seconds=870)
    try:
        verify(DECL); verify(REPAIR_DECL)
        pins=[validate_root(ROOT/'artifacts'/n) for n in NAMES]
        expected=['complete']*6+['failed']*2+['complete']*2+['failed']*2
        assert [p['status'] for p in pins]==expected
        source=read(SOURCE,'summary.json'); assert source['source_audit_complete'] and not source['private_encoding_proved']
        identity=read(SOURCE,'identity.json'); assert identity['SDK_version']=='27.0' and identity['SDK_build']=='26A425'
        first=ROOT/'artifacts/rust-r1-once-api-binding-20261016'; second=ROOT/'artifacts/rust-r1-once-api-repair-binding-20261016'
        firstfailure=read(first,'failure.json'); assert "meta['platform']==saved['platform']" in firstfailure['traceback']
        assert not (first/'API-binding.json').exists()
        m1=read(first,'libBLAS-metadata.json'); m2=read(second,'libBLAS-metadata.json'); old=read(WARM,'image-metadata.json')
        assert m1['platform']==m2['platform']==old['platform']
        assert m1['image_UUID']==m2['image_UUID']==old['image_UUID']=='31104d4f4a7e3fa79e1855937b2011f2'
        binding=read(second,'API-binding.json'); assert binding['dladdr_return']==0
        assert binding['public_symbol_runtime_address']!=binding['wanted_runtime_address'] and not binding['public_function_called']
        assert 'public==wanted==info.saddr' in read(second,'failure.json')['traceback']
        selectors=read(REPAIR_DECL,'saved-BL-selectors.json'); assert len(selectors)==2
        assert all(s['kind']=='BL' and s['target']=='0x1880e1a60' for s in selectors)
        before=(ROOT/'tools/public-data/rust_r1_once_contract.py').read_text(); repaired=(ROOT/'tools/public-data/rust_r1_once_contract_repair.py').read_text()
        transforms={
            "BDECL=ROOT/'artifacts/rust-r1-once-api-declaration-20261016'":"BDECL=ROOT/'artifacts/rust-r1-once-api-repair-declaration-20261016'",
            "BOUT=ROOT/'artifacts/rust-r1-once-api-binding-20261016'":"BOUT=ROOT/'artifacts/rust-r1-once-api-repair-binding-20261016'",
            "return [Path(__file__),CONFIG,BIND,WARM_CONFIG,":"return [Path(__file__),ROOT/'tools/public-data/rust_r1_once_contract.py',ROOT/'examples/configs/rust-r1-once-api-format-repair-20261016.json',CONFIG,BIND,WARM_CONFIG,",
            "assert meta['platform']==saved['platform']":"assert json.loads(json.dumps(meta['platform']))==saved['platform']"}
        transformed=before
        for a,b in transforms.items(): assert transformed.count(a)==1; transformed=transformed.replace(a,b)
        assert transformed==repaired
        delta=''.join(difflib.unified_diff(before.splitlines(True),repaired.splitlines(True),fromfile='original',tofile='format-repair'))
        resources={}
        for p in pins:
            root=ROOT/p['root']
            if not (root/'exit.json').exists(): continue
            e=read(root,'exit.json'); assert e['returncode']==(0 if p['status']=='complete' else 1)
            g=e['sampled_group_peak']; assert e['elapsed_seconds']<870 and e['sampled_cache_bytes']<1536*1024**2
            assert max(g['monitor_inclusive_footprint'],g['monitor_inclusive_rss'],e['child_wait_peak_rss_bytes'])<2*1024**3
            resources[p['root']]=e
        maxfp=max(e['sampled_group_peak']['monitor_inclusive_footprint'] for e in resources.values())
        maxrss=max(max(e['sampled_group_peak']['monitor_inclusive_rss'],e['child_wait_peak_rss_bytes']) for e in resources.values())
        cache=disk_bytes(); assert cache<1536*1024**2
        phase={'scope':'closed SDK/public contract audit plus independent metadata-only API binding',
            'SDK_source_complete':True,'minus_one_only_inline_fastpath_recognized':True,
            'private_predicate_encoding_proved':False,'exact_public_API_identity':False,
            'API_binding_preflight_format_failures':1,'API_identity_observations':1,'API_identity_failures':1,
            'public_function_calls':0,'new_tensor_BLAS_calls':0,'new_executable_reads':0,'new_configuration_reads':0,
            'query_result_proved':False,'train_dispatch_proved':False,'old_warm_gate_pass':False,
            'model_changed':False,'tolerance_changed':False,'R1_complete':False,'R2_started':False,
            'training':False,'next_target_mapping_executed':False}
        body=f'''# Rust R1 — 初期化判定の公開契約確認と呼出先照合（2026-10-16）

**SDKの-1比較はinline fast pathで、初期化完了の一般的な外部判定として数値を読む方法は公開APIの契約ではない。Appleの同期APIの保証を使うには、保存命令の呼出先との同一性が必要だった。独立のmetadata照合ではその直接同一性を確認できず、query/train経路は保留した。** 保存済みonce値52638546の内部表現は未解釈。元warm-binding失敗、モデル・許容差、R1安定版累積1点未達/R2停止を保持した。

## SDKと公開APIの仕様

[事前のsource/design条件](../../examples/configs/rust-r1-sgemm-once-semantics-admission-20261016.json)に沿い、installed SDKのdispatch/once.h、base.h、dispatch_once.3、libdispatch.tbd、SDKSettings.json、SDK/Xcodeの版plistをhashと共に保存した。SDK27.0/build26A425、Xcode27.1/build27A9275、stub current-version1605.0.2。保存した実行OSは27.0.1/Darwin27.0.0。SDKは実行時libraryそのものではなく、stub版を実行中の版と認定していない。

once.hはpredicateのzero初期化と、初期化した変数を使う前にdispatch_onceを呼ぶことを要求する。inlineはpredicate==~0lならcompiler barrier、それ以外なら公開関数を呼ぶ。末尾にはcompiler assumptionもある。base.hではそのassumptionが__builtin_assumeであることを確認した。これらはSDKで生成するwrapperの定義であり、実行時のprivate predicate状態が常に-1と読めるという検査仕様に読み替えていない。

Appleの[dispatch_once公式仕様](https://developer.apple.com/documentation/dispatch/dispatch_once-c.func)は、処理を一度実行し、競合する呼出しも完了を待つ同期動作を保証する。predicateはglobal/static storageが前提。このAPI保証と内部predicateの数値表現を区別した。今回、その内部表現を説明する同版runtime sourceは得ておらず、他版のlibdispatch実装を根拠に52638546をgeneration値などと断定していない。

公式ページの検索抽出は読めたが、HTML openはJavaScript案内、Markdownリンク取得はtoolのcontent-type/cache errorだった。帰属付き要約とURL、取得方法の限界を記録し、完全なpage snapshotや版対応sourceの代わりにしていない。SDK本文は別途zipで保存した。

## API identity確認を別工程として固定

source auditは新数値演算/live read0でcomplete閉鎖。その後、[独立したmetadata照合条件](../../examples/configs/rust-r1-once-api-binding-20261016.json)を先に保存した。保存済みqueryのBL@0x18123cdd4とcoreのBL@0x181392aacを元code bytesからdecodeし、両targetが0x1880e1a60であることを検証した。元六関数codeのlive再読取りはない。

一度目は、OS情報に含まれるruntimeのtupleと保存JSONのlistを直接比較していたため、dispatch API照合前のharnessチェックで停止した。二つの閉鎖済みmetadataのJSONを比較するとOS情報とlibBLAS UUIDは一致した。[形式修正の固定条件](../../examples/configs/rust-r1-once-api-format-repair-20261016.json)を保存し、元source/failed rootを変更せずfresh source/rootsを作成。修正はplatformのJSON正規化、出力root名とsource来歴の追加だけで、差分を機械照合した。

その修正後の一度のAPI identity観測では、保存target+shared-cache slideと、libSystemから解決した公開dispatch_onceが一致しなかった。targetに対するdladdrの戻り値は0だった。

| 観測 | 値 |
| --- | --- |
| 保存BL target / image virtual | {binding['saved_target_virtual']} |
| current shared-cache slide | {binding['shared_cache_slide']} |
| 計算したtarget runtime address | {binding['wanted_runtime_address']} |
| 解決したpublic dispatch_once runtime address | {binding['public_symbol_runtime_address']} |
| targetのdladdr | 0（image/symbolを識別できず） |
| native dispatch_once/query/initializer呼出し | 0 |

このaddress照合は公開関数を呼ばずに行った。条件未達で即停止し、別symbolや別addressの探索・再観測はしていない。dispatch image header/版取得はこのgate後の予定だったため未実行。したがって実dispatch UUID/版は今回も未確定。dladdr0は未mappingの証明ではなく、中間stubの証明でもない。直接の公開API入口ではない、という今回の照合結果だけを扱う。

## 保存値からできる判断と残る不足

元warm runの6,144出力bit一致、global@940=1、設定の二度同一という観測は変更していない。元once==-1 gateの失敗もfailedのまま。呼出先の意味が未確認なので、global1だけでquery1、あるいは初期化の成功/失敗を宣言しない。Appleの公開保証を未同定のcallへ当てはめず、train kernelも未確定とする。

次の不足は内部predicateを推測することではなく、既に固定されたtarget0x1880e1a60の転送先/役割である。[次unitの限定条件](../../examples/configs/rust-r1-once-call-target-admission-20261016.json)を保存した。fresh declarationでown-task VM mappingのSDK宣言をpinし、readable+executable/boundsを確認できる場合だけ、正確なtargetの最大64bytesを非実行で読む。一つの転送先が見えてもこのunitで追跡せず、別条件として固定する。mapping/SDK/読取りに不明点があればそのまま停止する。今回はこの読取りをまだ実行していない。

元六関数scopeやfailed rootsの上限をリセットせず、別のexact-address scopeとして扱う。新しいtensor/BLAS/operator/model比較や算術候補の試行を追加しない。

## 資源・保護・OS分離

全12rootsを検証し、うち4failed roots（型比較のpreflightとAPI identity未達、各records込み）を保持した。元warmの2failed rootsも別途pinのまま保持。全source/SDK/hash/stdio/exit/state/closure、修正差分、保存selectorと観測、文書前後をartifacts/rust-r1-once-results-20261016と同-evidenceに保存。publication自体のstdio/exit/stateは同-records。

全phaseは親900/子870秒、physical footprintとpeakRSS各2GiB、build cache+target1.5GiB、旧artifact/EvidenceStore/stdio枠を維持。今回最大監視込みfootprint {maxfp:,}B、RSS系 {maxrss:,}B、cache+target {cache:,}B。sample監視には捕捉限界がありhard OS capではない。

model.rs SHA acefec42e7506d807f7deae22269f30f9bf409a8c8cf9d1ddb59c2ef6af7fa80、Cargo/lock/default/許容差/元参照は不変。共通coreや新Rust候補の変更がないためRustテスト・全7case再評価は追加実行していない。R1安定版累積1点未達/R2停止。保全・点検支援第一、自作モデルの産業/需要での実用性、Rustの学習/推論/optimizer再開の目的を維持。

需要2015/CARE test再評価・学習・下流編集・Git push・製品採用0。需要2014以前調整、同休業mean28、四季過小量/過大量非増加、観測のみ/欠測0分離、heartbeat PAUSED維持。SDK/Accelerate/dyld/own-process metadataはMac固有の証拠であり、Windows固有機能・OS依存suiteは未実行として分ける。
'''
        headline='SDKのonce fast pathと公開APIの同期保証を区別。独立metadata照合では保存BL targetがpublic dispatch_onceと直接一致せず、dladdr0で停止。内部predicate/query/train経路は未確定。数値演算/新code読取り0。'
        changes={REPORT:body}
        n='docs/current-handoff.md'
        changes[n]='## 最新 — once仕様確認、呼出先の直接API照合は未達（2026-10-16）\n\n[結果と次条件](results/banto-ai-rust-r1-once-contract-2026-10-16.md)。'+headline+' 元warmの-1 gate失敗/6,144値bit一致を保持。SDK27.0とruntime27.0.1を混同せず、52638546のprivate意味を推測しない。元sourceと型形式のpreflight失敗、修正後のidentity未達を全保持。model/Cargo/default/許容差不変、R1安定版累積1点未達/R2停止。\n\n次は[正確なcall targetの独立条件](../examples/configs/rust-r1-once-call-target-admission-20261016.json)。saved BL target0x1880e1a60だけ、先にown-task mappingとSDK宣言を確認できる場合に最大64bytesを非実行で読む。dladdr0をstubと断定しない。元六関数/failed scopesを再開せず、他target/pointer追跡は別事前条件が必要。新数値演算・full model・学習は含めない。この次unitはまだ未実行。全証跡/文書前後はartifacts/rust-r1-once-results-20261016-evidence。\n\n各2GiB/build1.5GiB/時間/保存枠、既存成果/失敗/closed roots保護、保全第一/Rust学習目的、需要2015停止/2014以前調整/同休業mean28/四季両側非増加/観測欠測0分離、CARE test停止、Windows別検証、heartbeat PAUSED維持。以下は旧記録。\n\n---\n\n'+(ROOT/n).read_text()
        for n,marker,entry in [('docs/results/README.md','## Rustクレートの移植\n','- [Rust R1 once公開契約とAPI呼出先照合](banto-ai-rust-r1-once-contract-2026-10-16.md) — SDK確認、targetの直接同一性未達を保存、次は単一targetのmapping。'),('docs/research/README.md','## 文書\n','- [Rust R1 初期化判定と未同定のcall target](../results/banto-ai-rust-r1-once-contract-2026-10-16.md) — 公開API保証とprivate状態を分離、数値演算0。')]:
            prior=(ROOT/n).read_text(); assert marker in prior; changes[n]=prior.replace(marker,marker+'\n'+entry+'\n',1)
        for n in ['docs/research/banto-ai-rust-implementation-plan-2026-10-16.md','docs/research/rust-small-forecaster-r0-2026-10-16.md']:
            changes[n]=re.sub(r'^状態:.*$','状態: R1a済み/R1bは安定版累積1点未達/R2停止。once SDK/API契約を確認、保存targetの直接API identityは未達。次はexact targetのmapping/最大64byte観測の固定工程、今回新数値演算0。[最新結果](../results/banto-ai-rust-r1-once-contract-2026-10-16.md)。2026-10-16 JST。',(ROOT/n).read_text(),count=1,flags=re.M)
        n='docs/research/research-roadmap.md'; changes[n]='## 現在 — once仕様を確認、call target未同定を保持（2026-10-16）\n\n[結果](../results/banto-ai-rust-r1-once-contract-2026-10-16.md)。'+headline+' R1未達/R2停止。次はmapping確認後の単一target64byte上限の独立工程。以下は旧記録。\n\n---\n\n'+(ROOT/n).read_text()
        sources=list(dict.fromkeys([Path(__file__),*original_sources(),*repaired_sources(),NEXT,*source_files(),ROOT/'tools/verification_records.py',ROOT/'tools/public-data/care_rust_r0_close.py']))
        for p in sources:
            if p.suffix=='.py': ast.parse(p.read_text())
        out.sources(sources); out.json('phase.json',phase); out.json('root-pins.json',pins); out.json('resources.json',resources)
        out.write('format-repair.diff',delta.encode()); out.json('API-binding.json',binding)
        out.json('next-admission-pin.json',{'path':str(NEXT.relative_to(ROOT)),'sha256':digest(NEXT),'executed':False})
        evidence=ROOT/'artifacts/rust-r1-once-results-20261016-evidence'
        with EvidenceStore(evidence) as store:
            store.write_json('phase',phase); store.write_json('root-pins',pins); store.write_json('document-paths',list(changes))
            for i,p in enumerate(sources): store.write_bytes(f'source-{i}',p.read_bytes())
            for i,n in enumerate(changes):
                if (ROOT/n).exists(): store.write_bytes(f'before-{i}',(ROOT/n).read_bytes())
            for n,value in changes.items(): (ROOT/n).write_text(value)
            for i,n in enumerate(changes): store.write_bytes(f'after-{i}',(ROOT/n).read_bytes())
            for i,name in enumerate(NAMES):
                for j,p in enumerate(sorted((ROOT/'artifacts'/name).iterdir())): store.write_bytes(f'root-{i}-{j}',p.read_bytes())
            for target in re.findall(r'\]\(([^)]+)\)',body):
                if not target.startswith('https://'): assert ((ROOT/REPORT).parent/target).exists(),target
            verify(DECL); verify(REPAIR_DECL)
            for p in pins: assert validate_root(ROOT/p['root'])==p
            store.write_json('documents-after',[{'path':n,'sha256':digest(ROOT/n)} for n in changes])
        ev=verify_evidence(evidence,'complete'); out.json('evidence-check.json',ev)
        out.json('summary.json',{**phase,'verified_roots':12,'failed_roots_preserved':4,'original_warm_failed_roots_preserved':2,
            'model_sha256':digest(ROOT/'crates/banto-ai/src/model.rs'),'resources':check.check()})
        print(json.dumps({'published':True,'source_audit_complete':True,'API_identity_proved':False,'failed_roots_preserved':4,'evidence':ev})); status='complete'
    finally: out.close(status)

if __name__=='__main__': main()
