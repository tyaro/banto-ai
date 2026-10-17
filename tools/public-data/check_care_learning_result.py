"""Postprocessing-only independent saved-value validation; no model construction.

Recompute validation, threshold order statistics, run-based alarm episodes,
asset metrics, and neutral selected AdamW/model bytes without new forecasts.
"""
from collections import defaultdict
from datetime import datetime
from itertools import groupby
import json
import math
from pathlib import Path
import struct
import sys
import traceback
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'models/mini-transformer'));sys.path.insert(0,str(ROOT/'tools'))
from metropt_multiday import Files,verify_closed,digest
from macos_demand_runtime import MacCheckpoint
PR=struct.Struct('<IIqqqB7x2d2d2d2d9f4x');VR=struct.Struct('<II384f')
METHODS=('neural-common','baseline-common','baseline-native')


def independently_episodes(rows,method,threshold):
    flag=4 if method=='baseline-native' else 2;scoreindex=12 if method=='neural-common' else 13
    segments=[];current=[]
    for row in rows:
        if not row[5]&flag:
            if current:segments.append(current);current=[]
        elif current and row[4]-current[-1][4]!=600:
            segments.append(current);current=[row]
        else:current.append(row)
    if current:segments.append(current)
    result=[]
    for segment in segments:
        active=None
        for high,run in groupby(segment,key=lambda r:r[scoreindex]>threshold):
            group=list(run)
            if high and active is None and len(group)>=3:
                r=group[2];active={'open':r[4],'open_ordinal':r[1],'open_source_id':r[2]}
            elif not high and active is not None and len(group)>=3:
                result.append({**active,'close':group[2][4],'reason':'three-nonexceedances'});active=None
        if active is not None:
            result.append({**active,'close':segment[-1][4]+600,'reason':'file-end' if segment[-1][1]==rows[-1][1] else 'missing-or-gap'})
    return result


def close_float(a,b):return math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-12)


def main(campaign,output):
    out=Files(output);check=MacCheckpoint(seconds=870);status='failed'
    try:
        out.sources([Path(__file__),ROOT/'models/mini-transformer/metropt_multiday.py',ROOT/'tools/macos_demand_runtime.py'])
        campaign=Path(campaign);verify_closed(campaign);declaration=json.loads((campaign/'campaign.json').read_bytes())
        score=Path(declaration['score_root']);verify_closed(score);freeze=json.loads((score/'freeze-before-truth.json').read_bytes())
        if freeze['campaign_closure_sha256']!=digest(campaign/'root-closed.json'):raise ValueError('campaign changed')
        rows_by_event={};eps_by_event={};validation_check=[];neutral_check=[];calibration_check=[];support={}
        import torch  # saved-state IO only, no model construction/forward/backward/optimizer
        for k,path in enumerate(declaration['unit_roots']):
            root=Path(path);verify_closed(root);u=next(x for x in freeze['units'] if x['fold']==k)
            if digest(root/'root-closed.json')!=u['closure_sha256']:raise ValueError('unit changed after freeze')
            for name,key in [('selection.json','selection_sha256'),('thresholds.json','thresholds_sha256'),('calibration.bin','calibration_sha256'),('test.bin','test_sha256'),('episodes.json','episodes_sha256')]:
                if digest(root/name)!=u[key]:raise ValueError('frozen output changed')
            selection=json.loads((root/'selection.json').read_bytes());layout=json.loads((root/'validation-layout.json').read_bytes());T=layout['train_T32'];by_step=defaultdict(list);ns=defaultdict(list)
            for r in VR.iter_unpack((root/'validation.bin').read_bytes()):
                step,n=r[:2];ys=r[2:98];pred=r[98:];terms=[]
                for v in range(3):
                    for h in range(32):
                        for j,q in enumerate((.1,.5,.9)):
                            residual=(ys[v*32+h]-pred[v*96+h*3+j])/T[v];terms.append(q*residual if residual>=0 else (q-1)*residual)
                by_step[step].append(math.fsum(terms)/288);ns[step].append(n)
            assert sorted(by_step)==[512,1024,2048,4096]
            recomputed={step:math.fsum(xs)/len(xs) for step,xs in by_step.items()}
            for candidate in selection['candidates']:
                assert ns[candidate['step']]==layout['origins'] and close_float(candidate['validation_score'],recomputed[candidate['step']])
            chosen=min(recomputed,key=lambda step:(recomputed[step],step));assert chosen==selection['selected']['step']
            validation_check.append({'fold':k,'all_four_validation_scores_match':True,'selected_step':chosen,'scores':recomputed})
            thresholds=json.loads((root/'thresholds.json').read_bytes())['methods'];cal=list(PR.iter_unpack((root/'calibration.bin').read_bytes()))
            for name,index in [('neural',12),('baseline',13)]:
                xs=sorted(r[index] for r in cal);expected=xs[math.ceil(.995*len(xs))-1]
                assert expected==thresholds[name]['threshold'] and len(xs)==thresholds[name]['n']
            calibration_check.append({'fold':k,'calibration_scores':len(cal),'thresholds_match':True})
            rows=list(PR.iter_unpack((root/'test.bin').read_bytes()));all_eps=json.loads((root/'episodes.json').read_bytes());summary=json.loads((root/'summary.json').read_bytes())
            assert summary['updates']==4096 and summary['event_truth_bytes_read']==0
            for event in sorted({r[0] for r in rows}):
                part=[r for r in rows if r[0]==event];rows_by_event[event]=part;eps_by_event[event]=all_eps[str(event)]
                for method in METHODS:
                    threshold=thresholds['neural' if method=='neural-common' else 'baseline']['threshold']
                    assert independently_episodes(part,method,threshold)==all_eps[str(event)][method]
                support[event]={'prediction':len(part),'common':sum(bool(r[5]&2) for r in part),'native':sum(bool(r[5]&4) for r in part),'issued':sum(bool(r[5]&1) for r in part)}
            # Check every exported tensor against selected checkpoint, including AdamW moments and RNG.
            choice=selection['selected'];assert digest(root/choice['checkpoint'])==choice['sha256']
            state=torch.load(root/choice['checkpoint'],map_location='cpu',weights_only=True);assert state['step']==chosen and state['sampler_position']==chosen*8
            export=json.loads((root/'selected-neutral-layout.json').read_bytes());binary=(root/'selected-neutral.bin').read_bytes();mapping={r['name']:r['optimizer_id'] for r in export['optimizer_mapping']}
            assert export['checkpoint_sha256']==choice['sha256'] and export['schedule_sha256']==state['schedule_sha256']
            for t in export['tensors']:
                name=t['name']
                if name.startswith('model::'):tensor=state['model'][name.split('::',1)[1]]
                elif name.startswith('adamw::'):
                    _,parameter,field=name.split('::');tensor=state['optimizer']['state'][mapping[parameter]][field]
                else:assert name=='torch_rng_backend_specific';tensor=state['torch_rng']
                raw=binary[t['offset_bytes']:t['offset_bytes']+t['length_bytes']]
                if t['dtype']=='float32-le':values=list(struct.unpack('<'+'f'*(len(raw)//4),raw))
                elif t['dtype']=='bool-u8':values=[bool(x) for x in raw]
                elif t['dtype']=='uint8':values=list(raw)
                else:raise ValueError('unsupported neutral dtype')
                assert list(tensor.shape)==t['shape'] and values==tensor.reshape(-1).tolist()
            neutral_check.append({'fold':k,'selected_step':chosen,'all_exported_tensors_exact':True,'tensor_count':len(export['tensors'])})
            check.check()
        expected=json.loads((ROOT/'artifacts/care-consumer-check-provenance-20261016/input-support.json').read_bytes())['files']
        for e in expected:
            got=support[e['event_id']];assert got=={'prediction':e['prediction_rows'],'common':e['common_eligible'],'native':e['native_baseline_eligible'],'issued':e['past_only_issued_contexts']}
        labels=json.loads((ROOT/'artifacts/care-evaluator-contract-20261016/label-manifest.json').read_bytes())['rows']
        meta=json.loads((ROOT/'artifacts/care-numeric-input-20261016/dataset-manifest.json').read_bytes())['files'];meta={r['event_id']:r for r in meta}
        metrics=json.loads((score/'metrics.json').read_bytes());event_report={e['event_id']:e for e in json.loads((score/'per-event.json').read_bytes())};all_reference={}
        for method in METHODS:
            per=defaultdict(lambda:{'anomaly':0,'hits':0,'early':[],'normal_seconds':0,'false':0,'active_seconds':0,'mae':[[],[]]})
            for label in labels:
                event=int(label['event_id']);part=rows_by_event[event];es=eps_by_event[event][method];asset=label['asset_key'];s=per[asset]
                common=[r for r in part if r[5]&2];pi=8 if method=='neural-common' else 10
                for v in range(2):s['mae'][v].extend(abs(r[6+v]-r[pi+v]) for r in common)
                if label['event_label']=='anomaly':
                    base=datetime.fromisoformat(meta[event]['first_timestamp']);start=int((datetime.fromisoformat(label['event_start'])-base).total_seconds())+600;end=int((datetime.fromisoformat(label['event_end'])-base).total_seconds())+600
                    inside=sorted(e['open'] for e in es if start<=e['open']<=end);s['anomaly']+=1;s['hits']+=bool(inside)
                    early=(end-inside[0])/(end-start) if inside else 0.;s['early'].append(early)
                    reported=event_report[event]['methods'][method];assert reported['hit']==bool(inside) and reported['earliness']==early
                else:
                    flag=4 if method=='baseline-native' else 2;valid=[r for r in part if r[5]&flag]
                    s['normal_seconds']+=len(valid)*600;s['false']+=len(es)
                    s['active_seconds']+=600*sum(any(e['open']<=r[4]<e['close'] for e in es) for r in valid)
            refs={}
            for asset,s in per.items():
                r={'recall':s['hits']/s['anomaly'],'earliness':math.fsum(s['early'])/s['anomaly'],
                   'false_episodes_per_1000_record_hours':s['false']*3600*1000/s['normal_seconds'],'normal_alarm_fraction':s['active_seconds']/s['normal_seconds']}
                for key,value in r.items():assert close_float(value,metrics[method]['per_asset'][asset][key])
                refs[asset]=r
            macro={key:math.fsum(r[key] for r in refs.values())/len(refs) for key in next(iter(refs.values()))}
            for key,value in macro.items():assert close_float(value,metrics[method]['asset_macro'][key])
            pooled=metrics[method]['pooled'];assert sum(s['hits'] for s in per.values())==pooled['hits'] and sum(s['false'] for s in per.values())==pooled['false_episodes']
            assert sum(s['normal_seconds'] for s in per.values())==pooled['normal_seconds'] and sum(s['active_seconds'] for s in per.values())==pooled['normal_active_seconds']
            for v in range(2):
                xs=[x for s in per.values() for x in s['mae'][v]];assert close_float(math.fsum(xs)/len(xs),pooled['lead1_mae_common_thermal'][v])
            all_reference[method]={'asset_macro':macro,'hits':pooled['hits'],'normal_false_episodes':pooled['false_episodes']};check.check()
        a=all_reference['neural-common']['asset_macro'];b=all_reference['baseline-common']['asset_macro']
        expected_adv=a['recall']>b['recall'] and a['false_episodes_per_1000_record_hours']<=b['false_episodes_per_1000_record_hours'] and a['normal_alarm_fraction']<=b['normal_alarm_fraction'] and a['earliness']>=b['earliness']
        assert expected_adv==json.loads((score/'decision.json').read_bytes())['exploratory_common_advantage']
        out.json('validation-and-calibration.json',{'validation':validation_check,'calibration':calibration_check})
        out.json('neutral-state.json',neutral_check);out.json('independent-event-metrics.json',all_reference)
        out.json('summary.json',{'status':'complete','folds':5,'validation_choices':20,'selected_neutral_states_verified':5,'all22_alarm_episodes_and_support_match':True,'asset_and_pooled_event_metrics_match':True,'decision_match':True,
            'new_training':False,'model_construction':False,'forward':False,'new_threshold_selection':False,'saved_calibration_verified_only':True,'resources':check.check()});status='complete'
    except BaseException:
        out.json('failure.json',{'traceback':traceback.format_exc()},True);raise
    finally:out.close(status)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--campaign',required=True);p.add_argument('--output',required=True);a=p.parse_args();main(a.campaign,a.output)
