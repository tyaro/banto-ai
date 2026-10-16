"""Selected Farm A status/time support and independent label-ID alignment only."""
import csv
from datetime import datetime
import io
import json
from pathlib import Path
import sys
import traceback
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'models/mini-transformer'));sys.path.insert(0,str(ROOT/'tools'))
from metropt_multiday import Files,digest,verify_closed
from macos_demand_runtime import MacCheckpoint


def counts(times,status,start,end,horizon,stride,normal):
    bad=[0];gaps=[0]
    for i,t in enumerate(times):
        bad.append(bad[-1]+int(normal and status[i]!='0'))
        gaps.append(gaps[-1]+int(i>0 and (t-times[i-1]).total_seconds()!=600))
    kept=0;total=0
    for n in range(max(128,start),end-horizon+1,stride):
        left=n-128;right=n+horizon;total+=1
        kept+=bad[right]==bad[left] and gaps[right]==gaps[left+1]
    return {'candidates_before_quantity_checks':total,'status_time_eligible':kept,'normal_filter':normal,
            'sensor_finite_support_not_checked':True}


def main(output):
    files=Files(output);check=MacCheckpoint(seconds=870);result='failed'
    try:
        base=ROOT/'artifacts/care-metadata-inventory-20261016';verify_closed(base)
        local=json.loads((ROOT/'docs/research/care-local-archive-metadata-2026-10-16.json').read_bytes())
        split=json.loads((base/'split-manifest.json').read_bytes());inv=json.loads((base/'file-inventory.json').read_bytes())
        files.sources([Path(__file__),ROOT/'models/mini-transformer/metropt_multiday.py',ROOT/'tools/macos_demand_runtime.py'])
        support={};anchors=set(split['anchors'].values());observed={}
        # Read only structural columns, separately from truth. No sensor field decode.
        with zipfile.ZipFile(local['source_path']) as z:
            for item in (x for x in inv if x['farm']=='A'):
                times=[];status=[];ids=[]
                with z.open(item['member']) as f:
                    f.readline()
                    for line in f:
                        p=line.rstrip(b'\r\n').split(b';',5)
                        times.append(datetime.fromisoformat(p[0].decode()));ids.append(int(p[2]));status.append(p[4].decode())
                n=item['split_row_counts']['train'];cut=7*n//10
                record={'asset_id':item['asset_id'],'event_id':item['event_id'],'train_rows':n,'prediction_rows':len(times)-n,
                        'prediction':counts(times,status,n,len(times),1,1,False)}
                if item['event_id'] in anchors:
                    record.update(validation_cut_ordinal=cut,
                                  fit=counts(times,status,128,n,32,1,True),
                                  selection=counts(times,status,128,cut,32,32,True),
                                  calibration=counts(times,status,cut,n,1,1,True))
                support[str(item['event_id'])]=record
                observed[item['event_id']]=dict(zip(ids,times,strict=True));check.check()
        files.json('input-support.json',{'schema':'care.status-time-support.v1','split_manifest_sha256':digest(base/'split-manifest.json'),
                   'events':support,'sensor_values_decoded':0,'event_label_rows_consulted':False})
        # Truth is only consulted AFTER the input-side support has been committed.
        raw=ROOT/'artifacts/care-label-metadata-20261016/event-info-A.csv'
        labels=list(csv.DictReader(io.StringIO(raw.read_text()),delimiter=';'));checks=[]
        for row in labels:
            event=int(row['event_id']);start=datetime.fromisoformat(row['event_start']);end=datetime.fromisoformat(row['event_end'])
            lo=int(row['event_start_id']);hi=int(row['event_end_id']);item=next(x for x in inv if x['farm']=='A' and x['event_id']==event)
            bounds=item['bounds']['prediction']
            ok=(observed[event].get(lo)==start and observed[event].get(hi)==end and start<end and bounds['first_id']<=lo<=hi<=bounds['last_id'])
            checks.append({'event_id':event,'asset_id':row.get('asset_id',row.get('asset')),'label_id_timestamp_alignment':ok})
        files.json('label-alignment.json',{'input_support_sha256_before_label_read':digest(files.root/'input-support.json'),
                   'checks':checks,'all_aligned':all(x['label_id_timestamp_alignment'] for x in checks),'truth_must_not_be_model_input':True})
        if not all(x['label_id_timestamp_alignment'] for x in checks):raise ValueError('label boundaries do not match source IDs and timestamps')
        files.json('summary.json',{'status':'structural-support-and-label-alignment-complete','events':len(support),'boundary_checks':2*len(checks),
                   'sensor_values_decoded':0,'model_runs':0,'evaluation_runs':0,'resources':check.check()})
        result='complete'
    except BaseException:
        files.json('failure.json',{'traceback':traceback.format_exc()},True);raise
    finally:files.close(result)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();main(a.output)
