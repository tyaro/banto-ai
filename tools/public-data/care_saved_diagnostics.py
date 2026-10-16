"""Fixed retrospective diagnosis from closed CARE outputs, no new model runs."""
from collections import Counter
from itertools import groupby
import json,math,struct,statistics,sys,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'models/mini-transformer'));sys.path.insert(0,str(ROOT/'tools'))
from metropt_multiday import Files,digest,verify_closed
from macos_demand_runtime import MacCheckpoint
PRED=struct.Struct('<IIqqqB7x2d2d2d2d9f4x')
METHODS=('neural-common','baseline-common','baseline-native')


def runs(rows,index,flag,threshold):
    longest=count=0;last=None;exceeds=[]
    for r in rows:
        valid=bool(r[5]&flag)
        if not valid or (last is not None and r[4]-last!=600):count=0
        if valid:
            if r[index]>threshold:count+=1;exceeds.append(r[1]);longest=max(longest,count)
            else:count=0
            last=r[4]
        else:last=None
    return longest,exceeds


def main(output):
    out=Files(output);status='failed';check=MacCheckpoint(seconds=870)
    try:
        out.json('phase-before-read.json',{'scope':'closed saved-prediction diagnostics only','hypothesis':'Missed windows may have no score exceedance, isolated/nonpersistent exceedances, prior-active alarms, or insufficient supported observations. Availability differs at native-only detections. These are mechanical categories, not physical causes.',
            'population':'all12 anomaly intervals plus all10 normal files, not just one asset/event','fixed_categories':['detected','no-eligible-points','never-exceeds','not-three-consecutive','prior-active-no-new-open','requires-review'],
            'no_changes':['training','model forward','thresholds','confirmation length','signals','support','event selection','CARE outcome','demand2015']})
        out.sources([Path(__file__),ROOT/'models/mini-transformer/metropt_multiday.py',ROOT/'tools/macos_demand_runtime.py'])
        campaign=ROOT/'artifacts/care-learning-campaign-launch2-20261016';verify_closed(campaign);c=json.loads((campaign/'campaign.json').read_bytes());sroot=Path(c['score_root']);verify_closed(sroot)
        events=json.loads((sroot/'per-event.json').read_bytes());rows={};eps={};ths={};folds={};profile={};pins={'campaign':digest(campaign/'root-closed.json'),'score':digest(sroot/'root-closed.json')}
        for k,path in enumerate(c['unit_roots']):
            p=Path(path);verify_closed(p);pins[str(k)]=digest(p/'root-closed.json');rr=list(PRED.iter_unpack((p/'test.bin').read_bytes()));alarm=json.loads((p/'episodes.json').read_bytes());threshold=json.loads((p/'thresholds.json').read_bytes())['methods']
            for event in {r[0] for r in rr}:
                rows[event]=[r for r in rr if r[0]==event];eps[event]=alarm[str(event)];ths[event]={m:threshold['neural' if m=='neural-common' else 'baseline']['threshold'] for m in METHODS};folds[event]=k
        diagnoses=[];normal=[];native_only=[];counts=Counter()
        for e in events:
            event=e['event_id'];rr=rows[event];start=e['annotated_interval_start_availability'];end=e['annotated_interval_end_availability'];interval=[r for r in rr if start<=r[4]<=end]
            if e['event_label']=='anomaly':
                results={}
                for method in METHODS:
                    flag=4 if method=='baseline-native' else 2;index=12 if method=='neural-common' else 13;threshold=ths[event][method];valid=[r for r in interval if r[5]&flag];longest,exceed=runs(interval,index,flag,threshold)
                    reported=e['methods'][method]
                    if reported['hit']:category='detected'
                    elif not valid:category='no-eligible-points'
                    elif not exceed:category='never-exceeds'
                    elif reported['already_active_before_start']:category='prior-active-no-new-open'
                    elif longest<3:category='not-three-consecutive'
                    else:category='requires-review'
                    if method=='neural-common':counts[category]+=1
                    results[method]={'category':category,'threshold':threshold,'eligible':len(valid),'recorded_source_points':len(interval),'excluded':len(interval)-len(valid),
                        'strict_exceed_count':len(exceed),'longest_consecutive_exceed':longest,'max_score':max((r[index] for r in valid),default=None),
                        'max_threshold_ratio':max((r[index]/threshold for r in valid),default=None) if threshold>0 else None,
                        'exceed_ordinals':exceed,'primary_hit_unchanged':reported['hit']}
                common=[r for r in interval if r[5]&2]
                signatures={'n_common':len(common),'baseline_exceeds_nn_does_not':sum(r[13]>ths[event]['baseline-common'] and r[12]<=ths[event]['neural-common'] for r in common),
                    'nn_exceeds_baseline_does_not':sum(r[12]>ths[event]['neural-common'] and r[13]<=ths[event]['baseline-common'] for r in common),
                    'median_abs_neural_error':[statistics.median(abs(r[6+v]-r[8+v]) for r in common) for v in range(2)],
                    'median_abs_baseline_error':[statistics.median(abs(r[6+v]-r[10+v]) for r in common) for v in range(2)],
                    'median_abs_neural_prediction_minus_baseline':[statistics.median(abs(r[8+v]-r[10+v]) for r in common) for v in range(2)]}
                diagnoses.append({'event_id':event,'asset_key':e['asset_key'],'fold':folds[event],'methods':results,'descriptive_signatures_not_causal':signatures})
                if e['methods']['baseline-native']['hit'] and not e['methods']['neural-common']['hit']:
                    raw=(ROOT/f'artifacts/care-numeric-input-20261016/event-{event}.bin').read_bytes();opens=[]
                    for ep in eps[event]['baseline-native']:
                        if start<=ep['open']<=end:
                            r=next(r for r in rr if r[4]==ep['open']);n=r[1];gap=[j for j in range(n-127,n) if struct.unpack_from('<q',raw,j*32)[0]-struct.unpack_from('<q',raw,(j-1)*32)[0]!=600]
                            opens.append({'ordinal':n,'flags':r[5],'past128_gap_ordinals':gap,'common_available_at_open':bool(r[5]&2),'neural_issued_at_open':bool(r[5]&1)})
                    native_only.append({'event_id':event,'asset_key':e['asset_key'],'opens':opens})
            else:
                episodes=[]
                for ep in eps[event]['neural-common']:
                    r=next(r for r in rr if r[4]==ep['open']);episodes.append({'open_ordinal':r[1],'duration_seconds':ep['close']-ep['open'],
                        'neural_score_ratio':r[12]/ths[event]['neural-common'],'baseline_score_ratio':r[13]/ths[event]['baseline-common'],
                        'thermal_actual':list(r[6:8]),'neural_p50':list(r[8:10]),'baseline_p50':list(r[10:12]),
                        'baseline_common_active_at_nn_open':any(b['open']<=r[4]<b['close'] for b in eps[event]['baseline-common'])})
                normal.append({'event_id':event,'asset_key':e['asset_key'],'common_eligible':sum(bool(r[5]&2) for r in rr),'neural_false':len(episodes),
                    'baseline_common_false':len(eps[event]['baseline-common']),'baseline_native_false':len(eps[event]['baseline-native']),'neural_episodes':episodes})
            check.check()
        assert len(diagnoses)==12 and len(normal)==10 and counts['detected']==3 and sum(counts.values())==12
        assert not counts['requires-review'] and not counts['no-eligible-points']
        out.json('anomaly-diagnoses.json',diagnoses);out.json('normal-file-diagnoses.json',normal);out.json('native-availability.json',native_only);out.json('input-pins.json',pins)
        out.json('summary.json',{'status':'complete','neural_category_counts':dict(counts),'neural_missed_events':[d['event_id'] for d in diagnoses if d['methods']['neural-common']['category']!='detected'],
            'all12_anomalies_and10_normal_files_kept':True,'all_original_outcomes_unchanged':True,'normal_false_episode_count':sum(n['neural_false'] for n in normal),'native_only_detected_events':[e['event_id'] for e in native_only],
            'new_model_runs':0,'new_training':False,'threshold_or_support_changes':False,'causal_explanation_verified':False,'resources':check.check()})
        print(json.dumps({'counts':dict(counts),'native_only':[e['event_id'] for e in native_only]}));status='complete'
    except BaseException:
        out.json('failure.json',{'traceback':traceback.format_exc()},True);raise
    finally:out.close(status)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();main(a.output)
