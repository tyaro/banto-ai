"""Bounded CARE metadata audit. Sensor values remain opaque bytes, never floats.

Structural columns only: time_stamp, asset_id, id, train_test, status_type_id.
Event payloads are copied to a DIFFERENT root after label-blind splits are saved.
"""
from collections import Counter
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import sys
import traceback
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'models/mini-transformer'));sys.path.insert(0,str(ROOT/'tools'))
from metropt_multiday import Files,digest
from macos_demand_runtime import MacCheckpoint


def main(output,labels):
    files=Files(output);truth=None;check=MacCheckpoint(seconds=870);status='failed'
    try:
        local=json.loads((ROOT/'docs/research/care-local-archive-metadata-2026-10-16.json').read_bytes())
        official_path=ROOT/'artifacts/care-zenodo-v6-metadata-20261016/record.json'
        official=json.loads(official_path.read_bytes());archive=Path(local['source_path'])
        policy_path=ROOT/'artifacts/care-contract-20261016-evidence/prescan-policy.json'
        policy=json.loads(policy_path.read_bytes())
        files.write('prescan-policy.json',policy_path.read_bytes())
        files.sources([Path(__file__),ROOT/'models/mini-transformer/metropt_multiday.py',ROOT/'tools/macos_demand_runtime.py'])
        if archive.stat().st_size!=local['archive_bytes']:raise ValueError('local archive size changed')
        sha=hashlib.sha256();md5=hashlib.md5()
        with archive.open('rb') as f:
            for b in iter(lambda:f.read(8*1024*1024),b''):sha.update(b);md5.update(b);check.check()
        remote=next(x for x in official['files'] if x['key']=='CARE_To_Compare.zip')
        if sha.hexdigest()!=local['archive_sha256'] or archive.stat().st_size!=remote['size'] or 'md5:'+md5.hexdigest()!=remote['checksum']:
            raise ValueError('archive not equal to pinned local and official v6 checksum')
        files.json('provenance.json',{'record_id':official['id'],'doi':official['doi'],'publication_date':official['metadata']['publication_date'],
                   'record_updated':official['updated'],'license':official['metadata']['license'],'access_right':official['metadata']['access_right'],
                   'record_json_sha256':digest(official_path),'source_bytes':archive.stat().st_size,'sha256':sha.hexdigest(),'md5':md5.hexdigest(),
                   'official_md5_matched':True,'official_sha256_published':False,'local_source':str(archive)})
        inventory=[];features={};event_payload={};headers={}
        with zipfile.ZipFile(archive) as z:
            files.write('README-source.md',z.read(local['readme_member']))
            for farm in ('A','B','C'):
                prefix=f'CARE_To_Compare/Wind Farm {farm}/'
                feature=z.read(prefix+'feature_description.csv')
                files.write('feature-description-'+farm+'.csv',feature)
                features[farm]={'sha256':hashlib.sha256(feature).hexdigest(),'literal_replacement_character_count':feature.decode('utf-8-sig').count('\ufffd')}
                # Retain event bytes but do not decode label rows before split commitment.
                event_payload[farm]=z.read(prefix+'event_info.csv')
                members=sorted((x for x in z.namelist() if x.startswith(prefix+'datasets/') and x.endswith('.csv')),key=lambda s:int(Path(s).stem))
                for name in members:
                    h=hashlib.sha256();assets=set();ids=set();counts=Counter();status_counts={};bounds={};transitions=[]
                    rows=duplicate_ids=duplicate_times=reverse_times=gaps=0;previous=None;previous_split=None;max_gap=0
                    first=last=None;first_id=last_id=None;seen_times=set()
                    with z.open(name) as f:
                        header=f.readline();h.update(header);columns=header.decode('utf-8-sig').strip().split(';')
                        if columns[:5]!=['time_stamp','asset_id','id','train_test','status_type_id']:raise ValueError('structural columns differ')
                        if farm in headers and headers[farm]!=columns:raise ValueError('within-farm schema differs')
                        headers[farm]=columns
                        for line in f:
                            h.update(line);parts=line.rstrip(b'\r\n').split(b';',5)
                            if len(parts)!=6:raise ValueError('structural delimiter shortfall')
                            stamp,asset,rowid,split,oper=parts[:5]
                            t=datetime.fromisoformat(stamp.decode('ascii'));asset=asset.decode('ascii');rowid=int(rowid)
                            split=split.decode('ascii');oper=oper.decode('ascii')
                            if t.tzinfo is not None:raise ValueError('unexpected timezone annotation')
                            if split not in ('train','prediction','test'):raise ValueError('unknown train_test value')
                            assets.add(asset);duplicate_ids+=rowid in ids;ids.add(rowid)
                            duplicate_times+=stamp in seen_times;seen_times.add(stamp)
                            if first is None:first=t;first_id=rowid
                            last=t;last_id=rowid;rows+=1;counts[split]+=1
                            status_counts.setdefault(split,Counter())[oper]+=1
                            b=bounds.setdefault(split,{'first_timestamp':t.isoformat(),'first_id':rowid})
                            b.update(last_timestamp=t.isoformat(),last_id=rowid)
                            if previous is not None:
                                delta=(t-previous).total_seconds();reverse_times+=delta<0;gaps+=delta>600;max_gap=max(max_gap,delta)
                            if split!=previous_split:transitions.append({'row_ordinal':rows-1,'split':split,'id':rowid,'timestamp':t.isoformat()})
                            previous=t;previous_split=split
                            if rows%10000==0:check.check()
                    if len(assets)!=1:raise ValueError('one asset per file not satisfied')
                    inventory.append({'farm':farm,'event_id':int(Path(name).stem),'member':name,'member_bytes':z.getinfo(name).file_size,
                       'member_sha256':h.hexdigest(),'columns':len(columns),'asset_id':next(iter(assets)),
                       'rows':rows,'split_row_counts':dict(counts),'status_counts':{k:dict(v) for k,v in status_counts.items()},
                       'bounds':bounds,'split_transitions':transitions,'first_timestamp':first.isoformat(),'last_timestamp':last.isoformat(),
                       'first_id':first_id,'last_id':last_id,'duplicate_ids':duplicate_ids,'duplicate_timestamps':duplicate_times,
                       'reversed_timestamps':reverse_times,'gaps_over_600_seconds':gaps,'max_delta_seconds':max_gap})
                    print(json.dumps({'farm':farm,'event_id':int(Path(name).stem),'structural_rows':rows}),flush=True)
        files.json('file-inventory.json',inventory);files.json('sensor-schemas.json',{'columns':headers,'feature_metadata':features})
        if len(inventory)!=95:raise ValueError('95 event files expected')
        assets_by_farm={farm:sorted({x['asset_id'] for x in inventory if x['farm']==farm},key=int) for farm in ('A','B','C')}
        chosen=assets_by_farm['A']
        if len(chosen)!=5:raise ValueError('first bounded contract expects 5 Farm A assets')
        if any(name not in headers['A'] for name in policy['signals']):raise ValueError('selected Avg signal missing')
        anchors={asset:min((x for x in inventory if x['farm']=='A' and x['asset_id']==asset),key=lambda x:x['event_id'])['event_id'] for asset in chosen}
        folds=[]
        for i,asset in enumerate(chosen):
            validation=chosen[(i+1)%len(chosen)];train=[a for a in chosen if a not in (asset,validation)]
            folds.append({'fold':i,'test_asset':asset,'validation_asset':validation,'train_assets':train,
                          'train_anchor_events':[anchors[a] for a in train],'validation_anchor_event':anchors[validation],
                          'test_events':sorted(x['event_id'] for x in inventory if x['farm']=='A' and x['asset_id']==asset)})
        files.json('split-manifest.json',{'farm':'A','asset_key':'(farm,asset_id)','assets':chosen,'anchors':anchors,'folds':folds,
                   'selected_signals':policy['signals'],'event_labels_consulted_for_split':False,'cross_file_timestamps_not_a_physical_identity':True})
        split_sha=digest(files.root/'split-manifest.json')
        # Splits now committed; labels are an explicitly separate read/output path.
        truth=Files(labels);label_rows={}
        import csv
        for farm,raw in event_payload.items():
            truth.write('event-info-'+farm+'.csv',raw)
            rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig')),delimiter=';'))
            label_rows[farm]=rows
            mapping={x['event_id']:x['asset_id'] for x in inventory if x['farm']==farm}
            if {int(x['event_id']) for x in rows}!=set(mapping):raise ValueError('label/file inventory mismatch')
            for row in rows:
                if row.get('asset_id',row.get('asset'))!=mapping[int(row['event_id'])]:raise ValueError('label asset mismatch')
        truth.json('label-index.json',{'split_manifest_sha256_before_label_decode':split_sha,'purpose':'metadata and later scorer only; no model input',
                    'counts':{farm:dict(Counter(row['event_label'] for row in rows)) for farm,rows in label_rows.items()},
                    'dataset_version_uses_label_metadata_over_stale_README':True})
        truth.close('complete')
        files.json('summary.json',{'status':'care-metadata-and-label-separation-complete','file_count':len(inventory),
                   'structural_rows':sum(x['rows'] for x in inventory),'assets_by_farm':assets_by_farm,
                   'files_by_farm':dict(Counter(x['farm'] for x in inventory)),'source_feature_columns':{k:len(v) for k,v in headers.items()},
                   'chosen_farm':'A','folds':len(folds),'split_manifest_sha256':split_sha,'label_root':str(Path(labels).resolve()),
                   'label_closure_sha256':digest(Path(labels)/'root-closed.json'),'sensor_values_decoded':0,'model_runs':0,'training_runs':0,
                   'evaluation_runs':0,'normal_operation_truth_certified':False,'resources':check.check()})
        status='complete'
    except BaseException:
        files.json('failure.json',{'traceback':traceback.format_exc()},True)
        if truth is not None and not truth.closed:truth.close('failed')
        raise
    finally:files.close(status)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--labels',required=True)
    a=p.parse_args();main(a.output,a.labels)
