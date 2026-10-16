"""Finish readback after publication2 saved its complete EvidenceStore."""
import hashlib,json,sys,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'models/mini-transformer'))
from verification_records import EvidenceStore
from metropt_multiday import Files,digest,verify_closed
from macos_demand_runtime import MacCheckpoint
def verify_evidence(root,expected):
    def joined(item):
        chunks=[]
        for part in item['parts']:
            p=root/part['path']
            assert p.name==part['path'] and p.stat().st_size==part['bytes'] and digest(p)==part['sha256']
            chunks.append(p.read_bytes())
        raw=b''.join(chunks)
        assert len(raw)==item['saved_pin']['bytes'] and hashlib.sha256(raw).hexdigest()==item['saved_pin']['sha256']
        return raw
    marker=json.loads((root/'root-closed.json').read_bytes());assert marker['status']==expected
    m=json.loads(joined(marker['manifest']));assert m['status']==expected
    for name,info in m['files'].items():
        p=root/name;assert p.stat().st_size==info['bytes'] and digest(p)==info['sha256']
    for item in m['items'].values():
        joined(item)
        if item.get('source_pin'):assert item['source_pin']==item['saved_pin']
    actual={p.name for p in root.iterdir()}
    expected_files=set(m['files'])|{p['path'] for p in marker['manifest']['parts']}|{'root-closed.json'}
    assert actual==expected_files
    assert len(actual)<=512 and sum(p.stat().st_size for p in root.iterdir())<=16*1024**2
    return {'root':str(root.relative_to(ROOT)),'status':expected,'parts_verified':len(actual),'bytes':sum(p.stat().st_size for p in root.iterdir()),'closure_sha256':digest(root/'root-closed.json')}
def main(output,evidence):
    out=Files(output);check=MacCheckpoint(seconds=870);status='failed'
    try:
        out.json('phase.json',{'scope':'finish EvidenceStore readback and publication metadata; no repeated model or numeric experiment','reason':'publication2 successfully saved complete evidence, but readback code used part name instead of path; preserve both failures and close in fresh root','new_training':False,'forward':False})
        out.sources([Path(__file__),ROOT/'tools/public-data/care_rust_r0_publish.py',ROOT/'tools/verification_records.py',ROOT/'models/mini-transformer/metropt_multiday.py',ROOT/'tools/macos_demand_runtime.py'])
        first=verify_evidence(ROOT/'artifacts/care-rust-r0-final-20261016-evidence','failed')
        second=verify_evidence(ROOT/'artifacts/care-rust-r0-final2-20261016-evidence','complete')
        third=verify_evidence(ROOT/'artifacts/care-rust-r0-final3-20261016-evidence','failed')
        numeric=json.loads((ROOT/'artifacts/care-rust-r0-publication2-20261016/independent-checks.json').read_bytes())
        assert numeric['status']=='passed'
        for x in numeric['original_closures']:assert digest(ROOT/x['path'])==x['sha256']
        verify_closed(ROOT/'artifacts/care-saved-diagnostics-20261016')
        report=ROOT/'docs/results/care-saved-diagnostics-rust-r0-2026-10-16.md';handoff=ROOT/'docs/current-handoff.md'
        with EvidenceStore(ROOT/evidence) as store:
            store.write_bytes('source',Path(__file__).read_bytes());store.write_bytes('publisher-fixed', (ROOT/'tools/public-data/care_rust_r0_publish.py').read_bytes())
            store.write_json('phase',json.loads((out.root/'phase.json').read_bytes()))
            store.write_bytes('report-before',report.read_bytes());store.write_bytes('handoff-before',handoff.read_bytes())
            store.write_json('prior-evidence-readback',[first,second,third]);store.write_json('independent-numeric-checks',numeric)
            s=report.read_text()
            s=s.replace('fresh publication2で元root/参照SHA、別方式の連続超過集計、機械契約の整合性と文書リンクを検査し、旧文書全文/新source/stdio/exit/状態を', 'fresh publication2で元root/参照SHA、別方式の連続超過集計、機械契約の整合性と文書45リンクを検査し、旧文書全文/新source/stdio/exit/状態を')
            s=s.replace('に保存する。旧closed root/失敗を保持し、artifact/EvidenceStore/part/失敗reserve上限を維持する。','に保存した。そのEvidenceStoreはcompleteだが、直後のreadbackがpartのfieldをnameと誤記しexit1になった。元数値検算や保存内容の失敗ではない。両failureを保持し、fresh publication3で正しいpath fieldから全part/SHA/元rootの不変を検証した。最終状態と文書の前後は artifacts/care-rust-r0-final3-20261016-evidence に保存。旧closed root/失敗を保持し、artifact/EvidenceStore/part/失敗reserve上限を維持した。')
            s=s.replace('両failureを保持し、fresh publication3','3回目は既知のfailed記録を成功専用validatorへ渡して拒否された。3件のfailureを保持し、fresh publication4').replace('care-rust-r0-final3-20261016-evidence','care-rust-r0-final4-20261016-evidence')
            report.write_text(s)
            h=handoff.read_text();tick=chr(96)
            old='最終publicationで別方式run集計/参照pin/契約/linkを検査し、旧文書全文・新文書/設定/保存物を '+tick+'artifacts/care-rust-r0-final2-20261016-evidence'+tick+' に保存する。'
            new='publication2で別方式run集計/参照pin/契約/文書45linkを検査し、旧文書全文・新文書/設定/保存物を '+tick+'artifacts/care-rust-r0-final2-20261016-evidence'+tick+' にcomplete保存。初回linkの行番号suffix誤判定と2回目readbackのpart field名誤記のexit1を保持し、fresh publication3で全part/hashと元root不変を確認。最終状態/文書前後は '+tick+'artifacts/care-rust-r0-final3-20261016-evidence'+tick+'。モデル実験のretryは0。'
            assert old in h or new in h
            h=h.replace(old,new).replace('fresh publication3','fresh publication4').replace('care-rust-r0-final3-20261016-evidence','care-rust-r0-final4-20261016-evidence')
            h=h.replace('モデル実験のretryは0。','既知failed記録を成功専用validatorに渡した3回目の拒否も保存し、失敗3件を明示した。モデル実験のretryは0。',1)
            handoff.write_text(h)
            store.write_bytes('report-after',report.read_bytes());store.write_bytes('handoff-after',handoff.read_bytes())
            for i,name in enumerate(['examples/configs/rust-small-forecaster-r0-20261016.json','docs/research/rust-small-forecaster-r0-2026-10-16.md']):
                store.write_bytes(f'contract-{i}',(ROOT/name).read_bytes())
            for unit in ['care-rust-r0-publication-20261016-records','care-rust-r0-publication2-20261016-records','care-rust-r0-publication3-20261016-records']:
                folder=ROOT/'artifacts'/unit
                closure=json.loads((folder/'root-closed.json').read_bytes());assert closure['status']=='failed'
                assert set(p.name for p in folder.iterdir())=={x['name'] for x in closure['files']}|{'root-closed.json'}
                for item in closure['files']:
                    p=folder/item['name'];assert p.stat().st_size==item['bytes'] and digest(p)==item['sha256']
                for name in ['command.json','stdout.txt','stderr.txt','exit.json','root-closed.json']:
                    store.write_bytes(hashlib.sha256((unit+name).encode()).hexdigest()[:24],(folder/name).read_bytes())
            summary={'status':'complete','prior_evidence_readback_passed':True,'independent_numerical_checks_passed':True,'local_links_checked':45,'failed_publication_records_preserved':3,'new_training_or_forward':0,'Rust_compile':False,'target_repository':'tyaro/banto-industrial','target_repo_writes':False,'resources':check.check()}
            store.write_json('summary',summary);store.write_terminal('terminal',{'exit':0,'state':'complete','resources':check.check()})
        final=verify_evidence(ROOT/evidence,'complete')
        out.json('all-evidence-readback.json',[first,second,third,final]);out.json('summary.json',summary)
        print(json.dumps(summary));status='complete'
    except BaseException:
        out.json('failure.json',{'traceback':traceback.format_exc()},True);raise
    finally:out.close(status)
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--evidence',required=True);a=p.parse_args();main(a.output,a.evidence)
