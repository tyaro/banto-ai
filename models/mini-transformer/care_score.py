"""CARE r1 isolated event scorer, only after all five fold closures are pinned."""
from datetime import datetime,timedelta
import json
import math
from pathlib import Path
import struct
import traceback
from metropt_multiday import ROOT,Files,digest,verify_closed
from care_input import Consumer
from care_training_preparation import baseline_predict
from care_alarm import *

EVALUATION_SHA='a075209d77145540dcb1a535475c369820c507c206b5d99307a32d410d1cb361'
LABEL_SHA='22df6b500574223d6754fa9c8bb158259f374898225cbddea1771f4662fbff3d'


def freeze_units(declaration):
    roots=declaration['unit_roots']
    if len(roots)!=5 or len(set(roots))!=5:raise ValueError('five distinct folds required')
    result=[]
    for fold,path in enumerate(roots):
        root=Path(path);verify_closed(root);s=json.loads((root/'summary.json').read_bytes())
        if s['fold']!=fold or s['updates']!=4096 or s['performance_scored'] is not False:raise ValueError('fold incomplete')
        result.append({'fold':fold,'root':str(root),'closure_sha256':digest(root/'root-closed.json'),
            'selection_sha256':digest(root/'selection.json'),'thresholds_sha256':digest(root/'thresholds.json'),
            'calibration_sha256':digest(root/'calibration.bin'),'test_sha256':digest(root/'test.bin'),'episodes_sha256':digest(root/'episodes.json')})
    return result


def macro(per_asset):
    def mean_supported(key):
        xs=[a[key] for a in per_asset.values() if a[key] is not None]
        return math.fsum(xs)/len(xs) if xs else None
    return {k:mean_supported(k) for k in ('recall','false_episodes_per_1000_record_hours','normal_alarm_fraction','earliness')}


def main(dataset,prepared,campaign,output,check):
    from care_learning import authorize
    files=Files(output);status='failed'
    try:
        declaration=authorize(campaign,dataset,prepared)
        files.sources([Path(__file__),Path(__file__).with_name('care_alarm.py'),Path(__file__).with_name('care_input.py'),ROOT/'tools/macos_demand_runtime.py'])
        freeze=freeze_units(declaration)
        files.json('freeze-before-truth.json',{'units':freeze,'campaign_closure_sha256':digest(Path(campaign)/'root-closed.json'),
            'dataset_closure_sha256':declaration['dataset_closure_sha256'],'preparation_closure_sha256':declaration['preparation_closure_sha256'],
            'all_five_folds_thresholds_predictions_scores_alarms_closed':True,'event_truth_opened_yet':False})
        by_event={};profile_by_event={};alarms={};checks=[]
        for unit in freeze:
            root=Path(unit['root']);rows=list(PREDICTION.iter_unpack((root/'test.bin').read_bytes()));reader=Consumer(dataset,unit['fold'],'test')
            profile=json.loads((root/'input.json').read_bytes())['profile'];eps=json.loads((root/'episodes.json').read_bytes());thresholds=json.loads((root/'thresholds.json').read_bytes())['methods']
            for event in sorted(reader.allowed):
                d=reader.event(event);part=[r for r in rows if r[0]==event];nt=d.meta['split_row_counts']['train']
                if [r[1] for r in part]!=list(range(nt,d.meta['rows'])):raise ValueError('prediction row coverage')
                for r in part:
                    n=r[1];raw=d._rows[n];issued=d.past_ok(n);common=d.common_ok(n);native=d.native_ok(n);baseissued=bool(d._rows[n-1][2]&4)
                    expected_flags=int(issued)+2*int(common)+4*int(native)+8*int(baseissued)
                    if r[5]!=expected_flags or r[2]!=raw[1] or r[3]!=d._rows[n-1][0]+600 or r[4]!=raw[0]+600:raise ValueError('record support/lineage/timing')
                    if raw[2]&3==3 and tuple(r[6:8])!=tuple(raw[3:5]):raise ValueError('observation differs')
                    if issued:
                        if tuple(r[8:10])!=(r[15],r[18]) or not all(math.isfinite(x) for x in r[14:23]):raise ValueError('neural p50/q record')
                        if any(not r[14+3*v]<=r[15+3*v]<=r[16+3*v] for v in range(3)):raise ValueError('quantile order')
                    if baseissued and tuple(r[10:12])!=baseline_predict(profile['baseline'],d._rows[n-1][5]):raise ValueError('baseline differs')
                    for eligible,index,pred_index in ((common,12,8),(native,13,10)):
                        if eligible:
                            expected=max(abs(r[6+v]-r[pred_index+v])/profile['alarm_scales'][v]['R64'] for v in range(2))
                            if r[index]!=expected:raise ValueError('residual score differs')
                for method in METHODS:
                    threshold=thresholds['neural' if method=='neural-common' else 'baseline']['threshold']
                    if episodes(part,method,threshold)!=eps[str(event)][method]:raise ValueError('frozen episode differs')
                if sum(bool(r[5]&COMMON) for r in part)/len(part)<.7:raise ValueError('file support')
                by_event[event]=part;profile_by_event[event]=d.meta;alarms[event]=eps[str(event)]
                checks.append({'event_id':event,'all_rows_verified':len(part)});reader._cache.clear();check.check()
        if len(by_event)!=22:raise ValueError('fixed22 missing')
        files.json('pretruth-verification.json',{'checks':checks,'all22_rows_support_lineage_current_scores_baseline_and_episodes_match':True,'truth_opened_yet':False})
        # First evaluator/label access occurs after the immutable freeze above.
        eroot=ROOT/'artifacts/care-evaluator-contract-20261016';verify_closed(eroot)
        if digest(eroot/'evaluation.json')!=EVALUATION_SHA or digest(eroot/'label-manifest.json')!=LABEL_SHA:raise ValueError('evaluator pin')
        truth=json.loads((eroot/'label-manifest.json').read_bytes())['rows']
        if len(truth)!=22 or {int(t['event_id']) for t in truth}!=set(by_event):raise ValueError('truth cohort')
        assets=sorted({t['asset_key'] for t in truth});per_asset={method:{a:{'anomaly_events':0,'hits':0,'earliness_sum':0.,'normal_files':0,'normal_seconds':0,'normal_active_seconds':0,'false_episodes':0,'common_mae_sum':[0.,0.],'common_mae_n':0} for a in assets} for method in METHODS}
        per_event=[]
        for t in truth:
            event=int(t['event_id']);rows=by_event[event];meta=profile_by_event[event];base=datetime.fromisoformat(meta['first_timestamp']);asset=t['asset_key']
            if asset!='A:'+meta['asset_id']:raise ValueError('label asset mismatch')
            start=int((datetime.fromisoformat(t['event_start'])-base).total_seconds())+600
            end=int((datetime.fromisoformat(t['event_end'])-base).total_seconds())+600
            interval=[r for r in rows if int(t['event_start_id'])<=r[2]<=int(t['event_end_id'])]
            if not interval or interval[0][4]!=start or interval[-1][4]!=end:raise ValueError('label timestamp/ID alignment')
            common_fraction=sum(bool(r[5]&COMMON) for r in interval)/len(interval)
            if t['event_label']=='anomaly' and common_fraction<.7:raise ValueError('anomaly support')
            out={'event_id':event,'asset_key':asset,'event_label':t['event_label'],'annotated_interval_start_availability':start,'annotated_interval_end_availability':end,
                 'recorded_source_rows':len(interval),'interval_common_fraction':common_fraction,'prediction_rows':len(rows),'common_rows':sum(bool(r[5]&COMMON) for r in rows),'native_rows':sum(bool(r[5]&NATIVE) for r in rows),'methods':{}}
            for method in METHODS:
                state=per_asset[method][asset];eps=alarms[event][method];seconds=eligible_seconds(rows,method);active=active_seconds(rows,method,eps)
                details={'episodes':len(eps),'eligible_seconds':seconds,'active_seconds':active,'censored_prediction_rows':len(rows)-seconds//600}
                if t['event_label']=='anomaly':
                    er=event_result(eps,start,end);state['anomaly_events']+=1;state['hits']+=int(er['hit']);state['earliness_sum']+=er['earliness'];details.update(er)
                elif t['event_label']=='normal':
                    state['normal_files']+=1;state['normal_seconds']+=seconds;state['normal_active_seconds']+=active;state['false_episodes']+=len(eps)
                    details['false_episodes']=len(eps)
                else:raise ValueError('unknown event label')
                # All methods' point-MAE uses identical common support, native alarm support stays separate.
                pred_index=8 if method=='neural-common' else 10
                selected=[r for r in rows if r[5]&COMMON]
                for v in range(2):state['common_mae_sum'][v]+=math.fsum(abs(r[6+v]-r[pred_index+v]) for r in selected)
                state['common_mae_n']+=len(selected);out['methods'][method]=details
            per_event.append(out);check.check()
        results={}
        for method,stats in per_asset.items():
            for asset,s in stats.items():
                if s['normal_files'] and s['normal_seconds']<24*3600:raise ValueError('normal asset support')
                s['recall']=s['hits']/s['anomaly_events'] if s['anomaly_events'] else None
                s['earliness']=s['earliness_sum']/s['anomaly_events'] if s['anomaly_events'] else None
                s['false_episodes_per_1000_record_hours']=s['false_episodes']*3600*1000/s['normal_seconds'] if s['normal_seconds'] else None
                s['normal_alarm_fraction']=s['normal_active_seconds']/s['normal_seconds'] if s['normal_seconds'] else None
                s['lead1_mae_common_thermal']=[x/s['common_mae_n'] for x in s['common_mae_sum']] if s['common_mae_n'] else None
            pooled={key:sum(s[key] for s in stats.values()) for key in ('anomaly_events','hits','normal_files','normal_seconds','normal_active_seconds','false_episodes','common_mae_n')}
            pooled.update(recall=pooled['hits']/pooled['anomaly_events'],earliness=math.fsum(s['earliness_sum'] for s in stats.values())/pooled['anomaly_events'],
                false_episodes_per_1000_record_hours=pooled['false_episodes']*3600*1000/pooled['normal_seconds'],normal_alarm_fraction=pooled['normal_active_seconds']/pooled['normal_seconds'],
                lead1_mae_common_thermal=[math.fsum(s['common_mae_sum'][v] for s in stats.values())/pooled['common_mae_n'] for v in range(2)])
            results[method]={'asset_macro':macro(stats),'pooled':pooled,'per_asset':stats}
        nn=results['neural-common']['asset_macro'];bb=results['baseline-common']['asset_macro']
        criteria={'macro_recall_strictly_higher':nn['recall']>bb['recall'],'macro_false_rate_nonincrease':nn['false_episodes_per_1000_record_hours']<=bb['false_episodes_per_1000_record_hours'],
            'macro_alarm_fraction_nonincrease':nn['normal_alarm_fraction']<=bb['normal_alarm_fraction'],'macro_earliness_nonlower':nn['earliness']>=bb['earliness']}
        files.json('per-event.json',per_event);files.json('metrics.json',results)
        files.json('decision.json',{'criteria':criteria,'exploratory_common_advantage':all(criteria.values()),'native_baseline_comparison_included':True,
            'unique_physical_equipment_hours':False,'formal_blind_holdout':False,'official_CARE_score':False,'statistical_significance_claim':False,'business_lead_requirement':'unset','product_adoption':False})
        files.json('summary.json',{'status':'fixed-five-fold-learning-and-event-evaluation-complete','folds':5,'events':22,'anomalies':12,'normal_events':10,
            'methods':{m:results[m]['asset_macro'] for m in METHODS},'exploratory_common_advantage':all(criteria.values()),'no_retuning_or_extra_training':True,'resources':check.check()})
        status='complete';print(json.dumps({'CARE_scoring':'complete','asset_macro':{m:results[m]['asset_macro'] for m in METHODS},'criteria':criteria}),flush=True)
    except BaseException:
        failure={'traceback':traceback.format_exc()}
        try:failure['resources']=check.check()
        except BaseException as error:failure['resource_error']=repr(error)
        files.json('failure.json',failure,True);raise
    finally:files.close(status)
