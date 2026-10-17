"""Verify fixed CARE diagnostics and publish Rust R0 with before/after evidence."""
import hashlib,json,math,re,struct,sys,tomllib,traceback
from itertools import groupby
from pathlib import Path
from zipfile import ZipFile
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'models/mini-transformer'));sys.path.insert(0,str(ROOT/'tools'))
from metropt_multiday import Files,digest,verify_closed
from verification_records import EvidenceStore
from macos_demand_runtime import MacCheckpoint
REC=struct.Struct('<IIqqqB7x2d2d2d2d9f4x')
BASES=['care-saved-diagnostics','rust-r0-source-audit','banto-industrial-r0-intake','banto-industrial-r0-supplement']
CONFIG='examples/configs/rust-small-forecaster-r0-20261016.json'
PLAN='tools/public-data/care-rust-r0-publication-20261016.json'
def load(path):return json.loads((ROOT/path).read_bytes())
def pin(path):return {'path':str(path.relative_to(ROOT)),'bytes':path.stat().st_size,'sha256':digest(path)}
def checks(check):
    cfg=load(CONFIG)
    assert cfg['id']=='RUST-SF-20261016-r0' and cfg['target']['repository']=='tyaro/banto-industrial'
    assert cfg['target']['excluded_repository']=='ScadaProject' and not cfg['target']['external_repository_edits']
    assert cfg['backend']['version']=='=0.22.0' and not cfg['backend']['compile_verified']
    assert cfg['model']['parameters']==109024 and not cfg['model']['mean_head_supported']
    assert digest(ROOT/cfg['model']['source'])==cfg['model']['sha256']
    for ref in cfg['references']:
        p=ROOT/ref['path'];assert p.stat().st_size==ref['bytes'] and digest(p)==ref['sha256']
    recipe=load('artifacts/care-input-contract-20261016/learning.json')['training']['optimizer']
    for k in ['lr','betas','eps','weight_decay']:assert cfg['optimizer'][k]==recipe[k]
    layout=load(cfg['references'][1]['path'])
    raw=(ROOT/cfg['references'][0]['path']).read_bytes();used=set();end=0;count=0
    for t in layout['tensors']:
        assert t['name'] not in used;used.add(t['name'])
        start=t['offset_bytes'];length=t['length_bytes'];assert start>=end and start+length<=len(raw)
        width={'float32-le':4,'bool-u8':1,'uint8':1,'uint8-le':1}.get(t['dtype'])
        assert width is not None,(t['name'],t['dtype'])
        assert length==math.prod(t['shape'])*width
        if t['name'].startswith('model::') and t['name'][7:] not in cfg['package']['buffers']:count+=math.prod(t['shape'])
        end=start+length
    assert count==109024
    source_count=0
    for base in BASES:
        for suffix in ['', '-records']:verify_closed(ROOT/f'artifacts/{base}-20261016{suffix}')
    tree=load('examples/configs/banto-industrial-tree-20261016.json')
    assert tree['sha']==cfg['target']['commit'] and not tree['truncated']
    blobs={x['path']:x['sha'] for x in tree['tree'] if x['type']=='blob'}
    for base in ['banto-industrial-r0-intake','banto-industrial-r0-supplement']:
        folder=ROOT/f'artifacts/{base}-20261016'
        with ZipFile(folder/'banto-industrial-source.zip') as z:
            for item in json.loads((folder/'source-pins.json').read_bytes()):
                payload=z.read(item['path']);git=hashlib.sha1(b'blob '+str(len(payload)).encode()+b'\0'+payload).hexdigest()
                assert git==blobs[item['path']]==item['git_blob_sha']
                assert hashlib.sha256(payload).hexdigest()==item['sha256'];source_count+=1
            if base.endswith('intake'):
                assert tomllib.loads(z.read('rust-toolchain.toml').decode())['toolchain']['channel']==cfg['target']['toolchain_pin']
                types=z.read('crates/banto-tagclient/src/types.rs').decode()
                assert all(x in types for x in ['pub struct ValueEntry','pub v: Option<f64>','pub t: i64','pub enum ValueQuality'])
    assert source_count==23
    diagnoses={x['event_id']:x for x in load('artifacts/care-saved-diagnostics-20261016/anomaly-diagnoses.json')}
    events={x['event_id']:x for x in load('artifacts/care-learning-scores-20261016/per-event.json')}
    allrows={}
    for i in range(5):
        p=ROOT/f'artifacts/care-learning-fold-{i}-20261016';verify_closed(p)
        for event,rows in groupby(REC.iter_unpack((p/'test.bin').read_bytes()),key=lambda r:r[0]):
            assert event not in allrows;allrows[event]=list(rows)
    verified=[];counts={}
    for event,d in diagnoses.items():
        e=events[event];q=d['methods']['neural-common'];threshold=q['threshold']
        # Separate sorted-point adjacency calculation; no use of diagnostics.runs.
        hits=sorted((r[1],r[4]) for r in allrows[event] if e['annotated_interval_start_availability']<=r[4]<=e['annotated_interval_end_availability'] and r[5]&2 and r[12]>threshold)
        lengths=[];size=0;previous=None
        for point in hits:
            adjacent=previous is not None and point[0]==previous[0]+1 and point[1]==previous[1]+600
            size=size+1 if adjacent else 1;lengths.append(size);previous=point
        assert len(hits)==q['strict_exceed_count'] and max(lengths,default=0)==q['longest_consecutive_exceed']
        assert [x[0] for x in hits]==q['exceed_ordinals']
        assert q['primary_hit_unchanged']==e['methods']['neural-common']['hit']
        assert d['asset_key']==e['asset_key']
        counts[q['category']]=counts.get(q['category'],0)+1
        verified.append({'event':event,'strict_exceeds':len(hits),'longest':max(lengths,default=0),'hit':q['primary_hit_unchanged']})
        check.check()
    assert counts=={'not-three-consecutive':8,'never-exceeds':1,'detected':3}
    assert len(allrows)==22 and len(events)==22
    normal=load('artifacts/care-saved-diagnostics-20261016/normal-file-diagnoses.json')
    assert len(normal)==10 and sum(x['neural_false'] for x in normal)==3
    assert all(n['neural_false']==events[n['event_id']]['methods']['neural-common']['episodes'] for n in normal)
    roots=[ROOT/f'artifacts/{base}-20261016' for base in BASES]
    roots.extend(ROOT/f'artifacts/care-learning-fold-{i}-20261016' for i in range(5))
    roots.extend([ROOT/'artifacts/care-learning-scores-20261016',ROOT/'artifacts/care-train-profile-schedule-20261016',ROOT/'artifacts/care-train-preparation-verify-20261016'])
    for p in roots:verify_closed(p)
    return {'status':'passed','independent_sorted_exceedance_adjacency':verified,'counts':counts,'source_blobs_verified':source_count,'reference_layout_parameter_count':count,'config_and_optimizer_pins_pass':True,'all22_predictions_and_outcomes_retained':True,'original_closures':[pin(p/'root-closed.json') for p in roots],'model_runs':0}
def verify_links(paths):
    checked=[]
    for p in paths:
        for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
            if target.startswith(('https://','http://','mailto:','#','codex:')):continue
            s=re.sub(r':\d+$','',target.split('#',1)[0])
            if not s:continue
            q=(p.parent/s).resolve()
            assert q.exists(),f'broken local link in {p}: {target}'
            checked.append({'from':str(p.relative_to(ROOT)),'target':target})
    return checked
def main(output,evidence):
    out=Files(output);check=MacCheckpoint(seconds=870);status='failed'
    store=EvidenceStore(ROOT/evidence)
    try:
        with store:
            phase={'id':'CARE-SAVED-DIAG-AND-RUST-R0-PUBLISH-20261016','scope':'independent saved-value checks, contracts and documentation only','new_training':False,'new_forward':False,'target_repo_writes':False,'banto_target':'tyaro/banto-industrial','source_and_target_closures_immutable':True}
            out.json('phase.json',phase);store.write_json('phase',phase)
            sources=[Path(__file__),ROOT/PLAN,ROOT/'tools/verification_records.py',ROOT/'models/mini-transformer/metropt_multiday.py',ROOT/'tools/macos_demand_runtime.py',ROOT/'tools/public-data/banto_industrial_r0_intake.py',ROOT/'tools/public-data/banto_industrial_r0_supplement.py',ROOT/'tools/public-data/care_saved_diagnostics.py',ROOT/'tools/public-data/rust_r0_source_audit.py']
            out.sources(sources)
            for i,p in enumerate(sources):store.write_bytes(f'source-{i}',p.read_bytes())
            torchbase=ROOT/'environments/demand-macos/.venv/lib/python3.14/site-packages/torch'
            for i,name in enumerate(['optim/adam.py','optim/adamw.py','nn/utils/clip_grad.py']):
                store.write_bytes(f'torch-reference-{i}',(torchbase/name).read_bytes())
            verified=checks(check);out.json('independent-checks.json',verified);store.write_json('independent-checks',verified)
            plan=load(PLAN);updated={};before=[]
            for name,prefix in plan['prefixes'].items():
                old=(ROOT/name).read_text()
                if old.startswith(prefix.split('\n',1)[0]+'\n'):
                    old=old.split('\n---\n\n',1)[1]
                updated[name]=prefix+old
            for name in ['docs/research/timesfm-inspired-practical-evaluation-plan-2026-10-16.md','docs/research/timesfm-inspired-dual-domain-plan-2026-10-16.md']:
                old=(ROOT/name).read_text();lines=old.split('\n',2)
                updated[name]=old if plan['section'] in old else lines[0]+'\n\n'+plan['section']+lines[2]
            research='docs/research/README.md';old=(ROOT/research).read_text()
            entry='- [CARE保存予測の未検知分析とRust R0](../results/care-saved-diagnostics-rust-r0-2026-10-16.md) / [Rust R0契約](rust-small-forecaster-r0-2026-10-16.md) — 8件は3連続未達、1件は超過なし。banto-industrial source確認、Burn0.22候補・学習再開/数値比較条件固定。次はR1、製品接続未実施。\n'
            updated[research]=old if entry in old else old.replace('## 文書\n','## 文書\n\n'+entry,1)
            result='docs/results/README.md';old=(ROOT/result).read_text()
            result_entry='- [CARE保存予測の未検知分析とRust R0（2026-10-16）](care-saved-diagnostics-rust-r0-2026-10-16.md) — 元結果固定、未検知8+1の内訳とbanto-industrial接続契約。\n'
            updated[result]=old if result_entry in old else old.replace('## 産業設備の保全と点検支援\n','## 産業設備の保全と点検支援\n\n'+result_entry,1)
            for i,name in enumerate(updated):
                p=ROOT/name;before.append(pin(p));store.write_bytes(f'before-{i}',p.read_bytes())
            store.write_json('before-index',before)
            # All original document bytes saved before any mutation.
            for name,text in updated.items():(ROOT/name).write_text(text)
            paths=[ROOT/name for name in [*updated,*plan['new_docs'],CONFIG]]
            link_results=verify_links([p for p in paths if p.suffix=='.md' and p.name not in ['current-handoff.md','research-roadmap.md','README.md']])
            # Full legacy handoff/index links may predate this task; check newly inserted links separately.
            for name,text in {**plan['prefixes']}.items():
                for target in re.findall(r'\]\(([^)]+)\)',text):
                    if not target.startswith('http'):assert ((ROOT/name).parent/target.split('#')[0]).resolve().exists()
            for i,p in enumerate(paths):store.write_bytes(f'after-{i}',p.read_bytes())
            store.write_json('after-index',[pin(p) for p in paths])
            for base in BASES:
                for suffix in ['', '-records']:
                    folder=ROOT/f'artifacts/{base}-20261016{suffix}'
                    for p in sorted(folder.iterdir()):
                        # Public HTML body remains in verified immutable root; save its hash closure instead of duplicate pages.
                        if p.suffix=='.html':continue
                        label='saved-'+hashlib.sha256(str(p).encode()).hexdigest()[:20]
                        store.write_bytes(label,p.read_bytes())
            for item in verified['original_closures']:
                assert digest(ROOT/item['path'])==item['sha256']
            results={'status':'complete','independent_checks_passed':True,'local_document_links_checked':len(link_results),'target':'tyaro/banto-industrial','Rust_R0_contract_fixed':True,'Rust_compiled':False,'training_or_forward_runs':0,'Windows_native_or_OS_suite_run':False,'target_repo_edited':False,'resources':check.check()}
            out.json('summary.json',results);store.write_json('publication-summary',results)
            store.write_terminal('terminal',{'exit':0,'state':'complete','resources':check.check()})
        assert store._marker['status']=='complete'
        # Independent verification of EvidenceStore parts and source/saved hashes.
        marker=json.loads((store.root/'root-closed.json').read_bytes())
        def joined(item):
            parts=[]
            for part in item['parts']:
                p=store.root/part['path'];assert p.stat().st_size==part['bytes'] and digest(p)==part['sha256'];parts.append(p.read_bytes())
            raw=b''.join(parts);assert len(raw)==item['saved_pin']['bytes'] and hashlib.sha256(raw).hexdigest()==item['saved_pin']['sha256']
            return raw
        manifest=json.loads(joined(marker['manifest']))
        assert manifest['status']=='complete'
        for name,info in manifest['files'].items():
            p=store.root/name;assert p.stat().st_size==info['bytes'] and digest(p)==info['sha256']
        for item in manifest['items'].values():
            raw=joined(item)
            if item.get('source_pin'):assert item['source_pin']==item['saved_pin']
        out.json('evidence-readback.json',{'status':'passed','files':len(list(store.root.iterdir())),'bytes':sum(p.stat().st_size for p in store.root.iterdir()),'closure_sha256':digest(store.root/'root-closed.json'),'status_complete':True})
        print(json.dumps(results));status='complete'
    except BaseException:
        out.json('failure.json',{'traceback':traceback.format_exc()},True);raise
    finally:out.close(status)
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--evidence',required=True);a=p.parse_args();main(a.output,a.evidence)
