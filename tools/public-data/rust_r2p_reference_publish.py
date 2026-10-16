"""Verify saved artificial bytes without rerunning Torch, then publish provenance."""
import io
import json
import math
from pathlib import Path
import re
import struct
import subprocess
import sys
import traceback
import zipfile
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'models/mini-transformer'),str(ROOT/'tools/public-data')]
from metropt_multiday import Files,digest,verify_closed
from macos_demand_runtime import MacCheckpoint
from rust_r1_publish_preparation import validate_root
from verification_records import EvidenceStore
from care_rust_r0_close import verify_evidence
from rust_r2p_reference import PREFIX,SPEC,FIX,R0,Capture,read,pins,checkpins,scalar_clip,scalar_update,flat

REPORT='docs/results/rust-r2p-lock-and-python-reference-2026-10-16.md'
def main():
    out=Files(ROOT/'artifacts'/(PREFIX+'-publication')); status='failed'; check=MacCheckpoint(seconds=870)
    try:
        rootnames=[PREFIX+s for s in ['-declaration','-declaration-records','-lock','-lock-records','-numeric','-numeric-records']]
        roots=[validate_root(ROOT/'artifacts'/n) for n in rootnames]; assert all(p['status']=='complete' for p in roots)
        protected=pins(); checkpins(protected)
        # All generated reference phases used identical, still-current generator bytes.
        for suffix in ['-declaration','-lock','-numeric']:
            with zipfile.ZipFile(ROOT/'artifacts'/(PREFIX+suffix)/'sources.zip') as z:
                for n in ['tools/public-data/rust_r2p_reference.py','tools/public-data/rust_r2p_freeze.py',SPEC,FIX,R0]:
                    assert z.read(n)==(ROOT/n).read_bytes(),n
        numeric=ROOT/'artifacts'/(PREFIX+'-numeric'); layout=read(numeric/'reference-layout.json'); raw=(numeric/'reference.f32').read_bytes()
        summary=read(numeric/'summary.json'); assert summary['all_checks_pass'] and summary['checks']==107
        assert digest(numeric/'reference.f32')==summary['reference_sha256']; offset=0; named={}
        for item in layout:
            assert item['name'] not in named and item['offset']==offset and item['bytes']==4*math.prod(item['shape'])
            payload=raw[offset:offset+item['bytes']]; assert len(payload)==item['bytes']
            import hashlib
            assert hashlib.sha256(payload).hexdigest()==item['sha256']
            assert struct.pack('<'+'f'*len(item['values']),*item['values'])==payload
            named[item['name']]=item['values']; offset+=item['bytes']
        assert offset==len(raw)==4608 and len(layout)==427
        # Persist the independent scalar expectations omitted from the compact native check log.
        # This is saved-value arithmetic only: no Torch import, forward, backward, or update.
        fx=read(ROOT/FIX); recipe=fx['optimizer_recipe']; gates=Capture(None,read(ROOT/R0)['tolerance']); expectations=[]
        def gate(name,a,b,kind):
            gates.gate(name,a,b,kind); expectations.append({'name':name,'category':kind,'values':list(b),'dtype':'float64-le mathematical expectation'})
        def get(label,kind): return [named[f'{label}/{kind}/{i}'] for i in range(2)]
        def clip(label):
            before=get(label,'raw-gradient'); expected=scalar_clip(before)[2]
            gate(label+'/clip',flat(get(label,'clipped-gradient')),flat(expected),'gradient')
            return expected
        from fractions import Fraction
        for case,oracle in zip(fx['loss_cases'],read(numeric/'analytic-loss-oracles.json'),strict=True):
            label=case['id']; assert label==oracle['id']
            gate(label+'/loss',named[label+'/loss'],[float(Fraction(oracle['loss_rational']))],'normalized_loss')
            gate(label+'/gradient',named[label+'/gradient'],[float(Fraction(x)) for x in oracle['prediction_gradient_rational']],'gradient')
        for case in fx['clip_cases']: clip(case['id'])
        for case in fx['optimizer_cases']:
            label=case['id']; clipped=clip(label)
            expected=scalar_update(get(label+'/before','parameter'),clipped,get(label+'/before','moment1'),get(label+'/before','moment2'),case['step_before'],recipe)
            for kind,ref,field in zip(['one_step_parameter','first_moment','second_moment'],expected,['parameter','moment1','moment2']): gate(label+'/'+kind,flat(get(label+'/after',field)),flat(ref),kind)
            for i in range(2): assert named[label+f'/after/step-tensor/{i}']==[float(case['step_before']+1)]
        toy=fx['toy_training']
        def forward(xs,pv):
            w,b=pv; return [xs[h*2]*w[q*2]+xs[h*2+1]*w[q*2+1]+b[q] for h in range(2) for q in range(3)]
        gate('toy/probe/0',named['toy/probe/0'],forward(toy['probe_x'],get('toy/step0','parameter')),'normalized_activation')
        for step,batch_id in enumerate(toy['schedule'],1):
            label=f'toy/update{step}'; batch=next(b for b in toy['batch_table'] if b['id']==batch_id)
            previous='toy/step0' if step==1 else f'toy/update{step-1}/after'
            for field in ['parameter','moment1','moment2','step-tensor']:
                assert get(label+'/before',field)==get(previous,field)
            p0=get(label+'/before','parameter'); q=forward(batch['x'],p0); grads=[]; total=0.
            gate(label+'/prediction',named[label+'/prediction'],q,'normalized_activation')
            for h in range(2):
                for qi,t in enumerate([.1,.5,.9]):
                    r=batch['target'][h]-q[h*3+qi]; total+=max(t*r,(t-1)*r)
                    grads.append((-t if r>0 else 1-t if r<0 else .5-t)/6)
            gw=[sum(grads[h*3+qi]*batch['x'][h*2+j] for h in range(2)) for qi in range(3) for j in range(2)]
            gb=[sum(grads[h*3+qi] for h in range(2)) for qi in range(3)]
            gate(label+'/loss',named[label+'/loss'],[total/6],'normalized_loss' if step==1 else 'eight_step_loss')
            clip(label); gate(label+'/analytic-gradient',flat(get(label,'raw-gradient')),gw+gb,'gradient')
            expected=scalar_update(p0,scalar_clip([gw,gb])[2],get(label+'/before','moment1'),get(label+'/before','moment2'),step-1,recipe)
            for kind,ref,field in zip(['one_step_parameter' if step==1 else 'eight_step_parameter','first_moment','second_moment'],expected,['parameter','moment1','moment2']): gate(label+'/'+kind,flat(get(label+'/after',field)),flat(ref),kind)
            for i in range(2): assert named[label+f'/after/step-tensor/{i}']==[float(step)]
            gate(f'toy/probe/{step}',named[f'toy/probe/{step}'],forward(toy['probe_x'],get(label+'/after','parameter')),'normalized_activation')
        originalchecks={x['name']:x for x in read(numeric/'independent-checks.json')}
        assert len(originalchecks)==len(gates.checks)==107
        for c in gates.checks: assert originalchecks[c['name']]==c,c['name']
        expectedraw=bytearray()
        for e in expectations:
            e['offset']=len(expectedraw); b=struct.pack('<'+'d'*len(e['values']),*e['values']); e['bytes']=len(b); expectedraw.extend(b)
        out.write('independent-expectations.f64',bytes(expectedraw)); out.json('independent-expectations-layout.json',expectations)
        out.json('checks-reproduced-from-saved-values.json',gates.checks)
        torchlib=ROOT/'environments/demand-macos/.venv/lib/python3.14/site-packages/torch/lib/libtorch_cpu.dylib'
        assert digest(torchlib)=='ca979f3619acb92240c2ef46d7581b1a388761e0fccfa7dc491a7eaa153d584a'
        locksummary=read(ROOT/'artifacts'/(PREFIX+'-lock')/'summary.json'); assert locksummary['active_packages']==154 and locksummary['active_features_unchanged']
        resource=[read(ROOT/'artifacts'/(PREFIX+s+'-records')/'exit.json') for s in ['-declaration','-lock','-numeric']]
        for r in resource:
            assert r['returncode']==0 and r['elapsed_seconds']<900 and r['sampled_cache_bytes']<=1610612736
            assert max(r['sampled_group_peak']['monitor_inclusive_footprint'],r['sampled_group_peak']['monitor_inclusive_rss'],r['child_wait_peak_rss_bytes'])<=2147483648
        fp=max(r['sampled_group_peak']['monitor_inclusive_footprint'] for r in resource); rss=max(r['sampled_group_peak']['monitor_inclusive_rss'] for r in resource)
        headline='隔離Cargo.lockの最小案と人工Python参照を保存済み。gemm直接edge1行削除のみ、lock662記録/version・有効154package/feature不変。loss7/clip4/AdamW6/小型8更新、独立照合107件すべて原許容差内。'
        report=f'''# R2P: Cargo.lock最小案と人工Python参照

2026-10-16 JST。[復帰計画](../research/banto-ai-practical-training-return-plan-2026-10-16.md)と[固定R2P条件](../research/rust-r2p-synthetic-training-contract-2026-10-16.md)に沿って実施。{headline}

## Cargo.lockの整合案

元workspaceのmanifest/source/lockを新しい隔離workspaceへ複写し、banto-aiのdependenciesからmanifestにない`gemm`直接edgeだけを削除した。既存gemm packageは他依存から使用されるため残す。元lock/manifestは変更していない。提案は[差分](../../artifacts/{PREFIX}-lock/Cargo.lock.diff)と[全lock](../../artifacts/{PREFIX}-lock/Cargo.lock.proposed)へ保存。

隔離側のnative Cargo1.95 `tree --locked --offline`はpackage/feature確認ともexit0。resolverによる追加更新・ダウンロード・compileなし。lockの全662 package記録/versionはこのroot edge以外同一。有効154package/versionとfeature集合を閉鎖済みfused-linear dependency baselineと照合し一致。未定義の旧研究feature3種を復活していない。feature照合は保存済みCargo feature tree集合によるもので、全研究targetのbuild成功を意味しない。

この工程では整合を検証した隔離案をPython参照生成の入口に使った。**元workspaceへはまだ適用していないため、Rust受入実行の前に提案を明示的に適用する必要がある。** 以前の元workspaceでのexit101は解消済みとは記載しない。

## 一度だけ生成した参照

Python3.14.8、固定Torch git `08187d9e0fba026dc8217405802ab5381dc88d90`、CPU float32、thread/interop各1、乱数draw0。固定fixtureのloss7・clip4・単独AdamW6と9parameterの連続8更新を一度だけ実行した。backward15、optimizer更新14、clip18、probe9。小型affineの更新であり、実データや全SmallForecasterの学習は行っていない。

| 保存・照合対象 | 結果 |
| --- | --- |
| loss・tieの勾配・batch/channel/horizonの縮約 | 有理数期待値と7case通過。全tieのloss0でも勾配非ゼロを保持 |
| global clip・zero/boundary・複数parameter | scalar期待値との4caseと全更新の照合通過 |
| AdamW・decay・epsilon・step4096のmoment | 6case通過、全parameter/m1/m2/counter保存 |
| 人工連続8更新 | 日次ではなく固定人工batchの小型学習。全更新のprediction/loss/gradient/clip/parameter/moment/counterとprobe0..8を保存 |
| 独立照合 | 107件すべて固定R0.1条件内。scalar数学計算はTorchのfloat32演算順を再現したという主張ではない |

[参照binary](../../artifacts/{PREFIX}-numeric/reference.f32)はfloat32 little-endian 4,608bytes/1,152値、[layout](../../artifacts/{PREFIX}-numeric/reference-layout.json)は427tensorの名前・shape・offset・長さ・SHA256・値を収録。binary全byteをlayoutと照合し、gap/overlap/重複なし。SHA256は`{summary['reference_sha256']}`。layoutのoptimizer添字は各journalのordered_namesに対応する。Rust consumerはfixtureの初期値から開始し、この参照の中間stateを学習初期値へ流用しない。

[独立期待値](../../artifacts/{PREFIX}-publication/independent-expectations-layout.json)とfloat64数学値payloadも保存。これは閉鎖済み参照の保存値からのscalar検算で、Torch参照を再生成していない。nativeチェック107件の判定値も完全再現した。元有理数期待値、source/recipe/fixture/schedule pins、runtime版、stdio/exit/state/closureを保存した。NumPy未導入警告1件は保持し、NumPyを使わず数値bytesを保存した。

## 保護・資源・次工程

元R0.1許容差、41 source pinsと固定契約/fixture/protocol、元manifest/lock/model、既存失敗とclosed rootsは不変。libtorch_cpu SHAも既存pinと一致。最大観測（監視process込み）はphysical footprint {fp:,}B、RSS {rss:,}B、cache+target1,037,488,009Bで各2GiB/1.5GiB内。各parent900/child870秒とstdio/artifact/EvidenceStore枠を維持した。監視はsampleでありhard OS capではない。

次は保存した最小lock案を適用する工程と、固定条件内のfeature-gated小型loss/gradient/互換AdamW/checkpoint実装。既存推論modelを変更せず、小型Rustの連続8対4+復元4、入力拒否6/checkpoint拒否8/writer停止3を有限検証する。今回はそのRust実装・build・test・保存再開を行っていない。参照生成の成功だけでRust学習やfull modelの数値互換・保全性能の成功にしない。

ポインタ/once/TLS/PAC/vendor追跡は停止継続。R1残1点未達/正式R2実データ学習停止、CARE/MetroPT test凍結、需要2015停止・2014以前調整・同休業mean28比較・四季平均の過小量/過大量非増加・観測のみ/欠測0仮定分離を維持。保全・点検第一、学習を含むRust移植とbanto-ai→利用側の責務を維持する。AI crateはbanto-ai、依存方向はbanto-industrial/denroku-psi-demo→banto-ai。

Mac共通CPU上のPython参照とCargo metadata確認の結果である。Windows native/OS依存テストは未実行として分離。heartbeat PAUSED、外部送信・下流編集・Git push・製品採用0。証跡は`artifacts/{PREFIX}-evidence`、各phaseとpublicationの`-records`。元の固定契約文書の「未実行」は凍結時の状態として保護し、現在状態は本書と引継ぎを参照。
'''
        changes={REPORT:report}
        changes['docs/current-handoff.md']=f'''## 最新 — R2Pのlock最小案と人工Python参照を保存（2026-10-16）

[結果と次工程](results/rust-r2p-lock-and-python-reference-2026-10-16.md)。{headline} 参照427tensor/1,152値/4,608bytesを閉鎖。参照SHA256 `{summary['reference_sha256']}`。元workspaceのlock/manifest/model・41 source pinsと固定契約/fixture/許容差は不変。

lock案は隔離copyでlocked offline通過したが、元workspaceへ未適用。次はこの1行案の明示適用と、固定feature-gated人工consumer/互換AdamW/checkpoint実装。保存済み参照を使い、Rust連続8対4+復元4・拒否/途中保存条件を検証する。今回Rust実装/build/test/学習/保存再開は未実行。参照生成を再走しない。旧固定契約の未実行statusは凍結時点の記録として残す。

ポインタ追跡は再開しない。原R1残1点/正式R2実データ停止、CARE/MetroPT test凍結・需要2015停止/2014以前/同休業mean28/四季両側非増加/観測欠測0分離、各2GiB/build1.5GiB/時間・保存枠/既存失敗とclosed roots保護、Windows/OS試験別で未実行、heartbeat PAUSED、下流編集/push/製品採用0を維持。保全第一・Rustで学習も扱う目的を維持。証跡`artifacts/{PREFIX}-evidence`。以下は旧記録。

---

'''+(ROOT/'docs/current-handoff.md').read_text()
        n='docs/research/banto-ai-rust-implementation-plan-2026-10-16.md'; text=(ROOT/n).read_text()
        text=re.sub(r'^状態:.*$', '状態: 隔離lock最小案と人工Python参照を保存、107独立照合pass。元lockは未適用、Rust人工学習/保存再開は未実行。[結果](../results/rust-r2p-lock-and-python-reference-2026-10-16.md)。ポインタ追跡停止、原R1は1点未達/正式R2停止。2026-10-16 JST。',text,count=1,flags=re.M)
        text=text.replace('次は現source/manifest/lock/featureと学習graphの不足整理、人工fixture仕様固定。','棚卸しと人工fixture仕様固定は完了し、隔離lock最小案とPython人工参照の生成も完了した。次は検証済みlock案の適用と固定小型Rust学習部品の実装。')
        text=text.replace('現manifestの整合確認を次に行い、','現manifestとの整合は隔離lock案で確認済みだが元lockへ未適用で、')
        start=text.index('## 次に着手する内容\n')
        text=text[:start]+'''## 次に着手する内容

[固定R2P条件](rust-r2p-synthetic-training-contract-2026-10-16.md)に沿い、[隔離lock案と人工Python参照](../results/rust-r2p-lock-and-python-reference-2026-10-16.md)を保存済み。元lockからgemmの直接edge1行だけを削除する案を明示適用し、feature-gated小型loss/gradient/clip/互換AdamW/checkpointを実装する。固定fixtureから開始し、閉鎖済みPython参照を再生成しない。

その後の有限Rust受入は連続8対4+復元4、人工AdamW6、拒否6/8、writer途中停止3。元R0.1の許容差を守り、不一致を保存して依存工程を止める。今回Rust実装・build・test・保存再開は未実行。原R1未達/正式R2実データ停止、ポインタ追跡停止、CARE/需要の停止、各資源枠とheartbeat PAUSEDを維持する。
'''; changes[n]=text
        n='docs/research/banto-ai-practical-training-return-plan-2026-10-16.md'; text=(ROOT/n).read_text()
        text=re.sub(r'^工程0/1の追補:.*$', '工程0/1の追補: [固定条件](rust-r2p-synthetic-training-contract-2026-10-16.md)と[lock最小案/Python参照](../results/rust-r2p-lock-and-python-reference-2026-10-16.md)を保存済み。隔離案はpackage/feature不変で通過、107独立照合pass。元lockへ未適用。次は案の適用と固定小型Rust部品実装、Rust学習/保存再開は未実行。',text,count=1,flags=re.M); changes[n]=text
        for n,marker,entry in [('docs/results/README.md','## Rustクレートの移植\n','- [R2P lock最小整合案と人工Python参照](rust-r2p-lock-and-python-reference-2026-10-16.md) — 隔離案通過、107照合pass、元lock未適用/Rust学習未実行。'),('docs/research/README.md','## 文書\n','- [R2P lock案・人工Python参照と次工程](../results/rust-r2p-lock-and-python-reference-2026-10-16.md) — 凍結参照を使う小型Rust実装へ。')]:
            text=(ROOT/n).read_text(); assert marker in text; changes[n]=text.replace(marker,marker+'\n'+entry+'\n',1)
        n='docs/research/research-roadmap.md'; changes[n]='## 現在 — R2P人工参照を閉鎖（2026-10-16）\n\n[lock案と人工参照](../results/rust-r2p-lock-and-python-reference-2026-10-16.md)。'+headline+' 元lockは未適用。次は最小案の適用と人工Rust学習部品の実装。ポインタ追跡・実データ再評価は停止継続。以下は旧記録。\n\n---\n\n'+(ROOT/n).read_text()
        sources=[Path(__file__),ROOT/'tools/public-data/rust_r2p_reference.py',ROOT/'tools/public-data/rust_r2p_freeze.py',ROOT/'tools/verification_records.py',ROOT/'tools/public-data/care_rust_r0_close.py',ROOT/SPEC,ROOT/FIX,ROOT/R0]
        out.sources(sources); out.json('root-pins.json',roots); out.json('protected-pins.json',protected)
        out.json('torch-library-pin.json',{'path':str(torchlib.relative_to(ROOT)),'sha256':digest(torchlib),'source_read_only':True})
        evidence=ROOT/'artifacts'/(PREFIX+'-evidence')
        with EvidenceStore(evidence) as store:
            store.write_json('phase',{'reference_generated_once':True,'saved_value_checks':107,'Rust_learning_run':False,'lock_proposal_only':True})
            store.write_json('input-root-pins',roots); store.write_json('protected-pins',protected)
            for i,p in enumerate(sources): store.write_bytes(f'source-{i}',p.read_bytes())
            for i,n in enumerate(rootnames):
                for j,p in enumerate(sorted((ROOT/'artifacts'/n).iterdir())): store.write_bytes(f'root-{i}-{j}',p.read_bytes())
            store.write_bytes('independent-expectations-layout',(out.root/'independent-expectations-layout.json').read_bytes())
            store.write_bytes('independent-expectations-payload',bytes(expectedraw))
            for i,n in enumerate(changes):
                if (ROOT/n).exists(): store.write_bytes(f'document-before-{i}',(ROOT/n).read_bytes())
            for n,text in changes.items():
                if n==REPORT:
                    with (ROOT/n).open('x') as f: f.write(text)
                else: (ROOT/n).write_text(text)
            for i,n in enumerate(changes): store.write_bytes(f'document-after-{i}',(ROOT/n).read_bytes())
            checkpins(protected)
            for pin in roots: assert validate_root(ROOT/pin['root'])==pin
            for item in read(ROOT/'artifacts'/(PREFIX+'-lock')/'scratch-pins.json'): assert digest(ROOT/item['path'])==item['sha256']
            docs=subprocess.run(['git','diff','--check','--','docs'],cwd=ROOT,capture_output=True,timeout=20)
            out.json('document-check.json',{'exit':docs.returncode,'stdout':docs.stdout.decode(),'stderr':docs.stderr.decode()}); assert docs.returncode==0
            for n in changes:
                for target in re.findall(r'\]\(([^)]+)\)',(ROOT/n).read_text()):
                    if target.startswith(('http://','https://','#')): continue
                    assert ((ROOT/n).parent/target.split('#')[0]).exists(),(n,target)
            store.write_json('documents-after',[{'path':n,'sha256':digest(ROOT/n)} for n in changes])
        ev=verify_evidence(evidence,'complete'); out.json('evidence-check.json',ev)
        out.json('summary.json',{'publication_complete':True,'reference_binary_integrity':True,'saved_value_scalar_checks':107,
            'protected_source_pins':len(protected),'lock_proposal_verified':True,'original_workspace_lock_applied':False,
            'native_reference_generated_again':False,'Rust_learning_run':False,'Windows_native_OS_tests':'unrun','resources':check.check()})
        print(json.dumps({'publication_complete':True,'reference_integrity_pass':True,'saved_value_checks':107,'evidence':ev})); status='complete'
    except BaseException:
        out.json('failure.json',{'traceback':traceback.format_exc()},True); raise
    finally: out.close(status)
if __name__=='__main__': main()
