"""Isolated label-aware support preflight; consumes frozen eligibility, no scores.

The input consumer has closed before this process starts. No model, learner,
forecast, residual or event-detection metric is computed here.
"""
from datetime import datetime,timedelta
import json
from pathlib import Path
import struct
import sys
import traceback
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'models/mini-transformer'));sys.path.insert(0,str(ROOT/'tools'))
from metropt_multiday import Files,verify_closed,digest
from macos_demand_runtime import MacCheckpoint
LABEL_SHA='22df6b500574223d6754fa9c8bb158259f374898225cbddea1771f4662fbff3d'


def main(dataset,consumer,output):
    log=Files(output);status='failed';check=MacCheckpoint(seconds=870)
    try:
        log.sources([Path(__file__),ROOT/'models/mini-transformer/metropt_multiday.py',ROOT/'tools/macos_demand_runtime.py'])
        root=Path(dataset);prepared=Path(consumer);verify_closed(root);verify_closed(prepared)
        support=json.loads((prepared/'input-support.json').read_bytes());eligible=json.loads((prepared/'eligibility.json').read_bytes())
        if support['dataset_closure_sha256']!=digest(root/'root-closed.json'):raise ValueError('data closure changed')
        # Pin input bytes and role-separated consumer closure before opening truth.
        log.json('input-freeze-before-truth.json',{'dataset_closure_sha256':digest(root/'root-closed.json'),
            'consumer_closure_sha256':digest(prepared/'root-closed.json'),'eligibility_sha256':digest(prepared/'eligibility.json'),
            'input_support_sha256':digest(prepared/'input-support.json'),'performance_scoring':False})
        labels=ROOT/'artifacts/care-evaluator-contract-20261016';verify_closed(labels)
        if digest(labels/'label-manifest.json')!=LABEL_SHA:raise ValueError('label pin')
        truth=json.loads((labels/'label-manifest.json').read_bytes())['rows']
        m=json.loads((root/'dataset-manifest.json').read_bytes());events={f['event_id']:f for f in m['files']}
        if {int(t['event_id']) for t in truth}!=set(events) or len(truth)!=22:raise ValueError('label cohort')
        results=[];normal={};native_normal={}
        for label in truth:
            event=int(label['event_id']);meta=events[event];raw=(root/meta['binary']).read_bytes();base=datetime.fromisoformat(meta['first_timestamp'])
            rows=[struct.unpack_from('<qq',raw,i*32) for i in range(meta['rows'])];nt=meta['split_row_counts']['train']
            lo,hi=int(label['event_start_id']),int(label['event_end_id'])
            lookup={ident:(i,t) for i,(t,ident) in enumerate(rows)}
            assert base+timedelta(seconds=lookup[lo][1])==datetime.fromisoformat(label['event_start'])
            assert base+timedelta(seconds=lookup[hi][1])==datetime.fromisoformat(label['event_end'])
            if label['asset_key']!='A:'+meta['asset_id']:raise ValueError('asset label mismatch')
            interval=[i for i in range(nt,meta['rows']) if lo<=rows[i][1]<=hi]
            common=set(eligible[str(event)]['common_ordinals']);native=set(eligible[str(event)]['native_ordinals'])
            fraction=len(common.intersection(interval))/len(interval) if interval else 0
            if label['event_label']=='anomaly':
                results.append({'event_id':event,'asset_key':label['asset_key'],'recorded_source_timestamps':len(interval),
                    'common_eligible_timestamps':len(common.intersection(interval)),'common_fraction':fraction,'minimum_fraction':.7,
                    'passed':bool(interval) and fraction>=.7,'native_eligible_timestamps':len(native.intersection(interval)),
                    'basis':'inclusive source-ID aligned estimated anomaly interval; availability +600s on both interval and observations'})
            elif label['event_label']=='normal':
                asset=label['asset_key'];normal[asset]=normal.get(asset,0)+len(common)
                native_normal[asset]=native_normal.get(asset,0)+len(native)
            else:raise ValueError('unknown event label')
            check.check()
        hours=[{'asset_key':a,'eligible_recorded_hours':n/6,'minimum_hours':24,'passed':n>=144,
                'native_eligible_recorded_hours':native_normal[a]/6} for a,n in sorted(normal.items())]
        input_ok=all(f['passed'] for f in support['files']) and all(v['passed'] for a in support['anchors'].values() for v in a.values())
        complete=input_ok and all(r['passed'] for r in results) and all(h['passed'] for h in hours)
        log.json('event-and-normal-support.json',{'anomalies':results,'normal_assets':hours,
            'normal_exposure_basis':'all eligible prediction rows of normal-event files, each interval [availability,availability+600); file-local anonymous records never deduplicated as physical hours',
            'truth_source_sha256':LABEL_SHA,'input_consumer_closed_before_truth':True,'no_detection_performance_scored':True})
        log.json('summary.json',{'status':'complete','fixed_numeric_window_support_passed':complete,'input_support_passed':input_ok,
            'anomaly_support_passed':all(r['passed'] for r in results),'normal_hour_support_passed':all(h['passed'] for h in hours),
            'anomalies':len(results),'normal_assets':len(hours),'failed_event_ids':[r['event_id'] for r in results if not r['passed']],
            'all22_retained':True,'can_launch_learning':False,'can_launch_predictions':False,'performance_scoring':False,
            'next_gate':'separate explicit execution instruction and train-only profile/baseline-bin support/frozen training schedule before CARE training',
            'resources':check.check()})
        status='complete'
    except BaseException:
        log.json('failure.json',{'traceback':traceback.format_exc()},True);raise
    finally:log.close(status)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--dataset',required=True);p.add_argument('--consumer',required=True);p.add_argument('--output',required=True);a=p.parse_args();main(a.dataset,a.consumer,a.output)
