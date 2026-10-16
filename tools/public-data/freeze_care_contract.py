"""Freeze label-blind input/learning view and a separate evaluator/truth view.

Metadata only. No sensor float parsing, model construction, training or scoring.
"""
import csv
import io
import json
from pathlib import Path
import sys
import traceback

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'models/mini-transformer'));sys.path.insert(0,str(ROOT/'tools'))
from metropt_multiday import Files,digest,verify_closed
from macos_demand_runtime import MacCheckpoint


def reject_truth_fields(value):
    forbidden={'event_label','event_start','event_end','event_start_id','event_end_id','event_description','truth_rows','label_root'}
    if isinstance(value,dict):
        if set(value)&forbidden:raise ValueError('truth field in learning/input view')
        for item in value.values():reject_truth_fields(item)
    elif isinstance(value,list):
        for item in value:reject_truth_fields(item)


def main(input_root,evaluator_root,output):
    inputs=Files(input_root);evaluator=Files(evaluator_root);audit=Files(output);check=MacCheckpoint(seconds=870);status='failed'
    try:
        meta=ROOT/'artifacts/care-metadata-inventory-20261016';support_root=ROOT/'artifacts/care-contract-support-20261016'
        for root in (meta,support_root,ROOT/'artifacts/care-label-metadata-20261016'):verify_closed(root)
        split=json.loads((meta/'split-manifest.json').read_bytes());inv=json.loads((meta/'file-inventory.json').read_bytes())
        support=json.loads((support_root/'input-support.json').read_bytes())['events']
        provenance=json.loads((meta/'provenance.json').read_bytes())
        features=list(csv.DictReader(io.StringIO((meta/'feature-description-A.csv').read_text()),delimiter=';'))
        a=sorted((x for x in inv if x['farm']=='A'),key=lambda x:x['event_id'])
        if len(a)!=22 or len(split['folds'])!=5:raise ValueError('fixed cohort size')
        seen=[]
        for fold in split['folds']:
            groups=[set(fold['train_assets']),{fold['validation_asset']},{fold['test_asset']}]
            if any(groups[i]&groups[j] for i in range(3) for j in range(i)):raise ValueError('asset split overlap')
            if set.union(*groups)!=set(split['assets']):raise ValueError('asset coverage')
            seen.extend(fold['test_events'])
        if sorted(seen)!=[x['event_id'] for x in a] or len(set(seen))!=22:raise ValueError('test files must appear exactly once')
        signals=[]
        for name in split['selected_signals']:
            row=next(x for x in features if x['sensor_name']==name.removesuffix('_avg'))
            signals.append({'column':name,'description':row['description'],'source_unit_literal':row['unit'],
                            'numerical_unit_conversion':None,'unit_note':'literal corrupted temperature symbol retained; numeric native units, no engineering threshold' if '\ufffd' in row['unit'] else 'power anonymization/scaling retained; not true rated capacity',
                            'statistic':'10-minute average','alarm_target':name!='power_30_avg'})
        recipe={'schema':'banto.care-learning-contract.v1','contract_id':'CARE-A-MAINT-20261016-r1',
          'model_feature_order':split['selected_signals'],'model':{'source':'models/mini-transformer/small_model.py','source_sha256':digest(ROOT/'models/mini-transformer/small_model.py'),
          'class':'SmallForecaster','variant':'full','parameters':109024,'V':3,'C':128,'H':32,'P':32,'width':64,'blocks':2,'heads':4,'ff':128,
          'quantiles':[.1,.5,.9],'device':'cpu','dtype':'float32','dropout':0,'official_weights':False,'reuse_metropt_weights':False},
          'cadence_seconds':600,'availability_delay_seconds':600,'time_assumption':'source-naive file-local; timestamp may be interval start, so add one full bin conservatively',
          'forecast_context':'rows [n-128,n), target rows [n,n+32); no file/gap crossing; forward never sees row n',
          'alarm_forecast':'lead 1 p50 only; current thermal observations enter residual only after their availability time',
          'normal_filter':'status_type_id==0 only for offline fit/selection/calibration prefix; not a healthy truth guarantee',
          'runtime_status_input_or_gate':False,'train_test_is_feature':False,'asset_or_event_id_is_feature':False,
          'normalization':{'population':'each all-3-finite status0 train-anchor bin once; train asset equal weight, bins within asset equal',
          'mean_variance':'float64 fsum asset means and asset squared deviations about shared mean; population sigma',
          'T':'max(sigma,1e-5 native)','context_floor':'max(.01*sigma,1e-5 native)','tensor':'float32 pinned, finite positive before/after rounding',
          'context':'existing forward mean and std(correction=0), CPU float32; context only',
          'alarm_scale':'for two thermal targets, max(1.4826*weighted_median(abs(x-weighted_median(x))),1e-3 native); train only, same for both detectors',
          'weighted_quantile':'inverse weighted empirical CDF, smallest sorted value with cumulative weight >=p; weight 1/(3*N_asset), identical-value weights combined using fsum; renormalize restricted populations'},
          'training':{'init_seed_each_fold':20261016,'sampler_seed_each_fold':20262016,'folds_are_not_independent_seeds':True,'batch':8,'updates':4096,
          'sampler':'Random(seed): randrange(3) sorted train assets, then randrange(sorted eligible origins); replacement; persist full schedule',
          'optimizer':{'name':'AdamW','lr':3e-4,'betas':[.9,.999],'eps':1e-8,'weight_decay':.01,'foreach':False,'fused':False},
          'grad_clip':1.0,'loss':'existing context-normalized training_loss pinball, all 3 targets/32 leads/3 quantiles equal',
          'threads':2,'interop_threads':1,'deterministic_algorithms':True,'nonfinite':'stop','scheduler':None,'early_stopping':False},
          'selection':{'steps':[512,1024,2048,4096],'metric':'fixed train-scale pinball; origins/3 targets/32 leads/3 quantiles equal within one validation anchor',
          'prefix_fraction':.7,'cut':'floor(7*N_train/10) row ordinal','stride':32,'ties':'earlier checkpoint; exact equality'},
          'baseline':{'name':'load-bin thermal median','inputs':'same observed context; use power_30_avg at n-1',
          'fit_pairs':'one (power[n-1], thermal[n]) per eligible neural train origin; train anchors only; asset equal',
          'load_cuts':'weighted train 0.25/0.5/0.75 quantiles; equality belongs to lower bin; duplicate cuts kept with empty bins unused',
          'estimate':'weighted median thermal[n] per bin; empty bin predicts nearest populated ordered bin, ties lower; no target-label use',
          'minimum_pairs_per_nonempty_bin':128,'no_baseline_selection_grid':True},
          'alarm':{'targets':['sensor_13_avg','sensor_12_avg'],'score':'max absolute residual / common train thermal MAD scale',
          'calibration':'validation anchor train-prefix suffix [cut,N_train), status0 contiguous context and current thermal; stride1; no event labels',
          'threshold':'per method inverse empirical quantile 0.995: sorted score at ceil(.995*N)-1; strict score>threshold',
          'raise_after':3,'clear_after':3,'cooldown_samples':0,'gap_or_missing':'end active at last available time+600s, reset all counters; no imputation',
          'open_time':'availability time of third consecutive exceedance, never first exceedance or forecast issue',
          'close_time':'availability time of third consecutive nonexceedance; active intervals [open,close)',
          'file_end':'close at last eligible availability+600s; reset between files',
          'baseline_native_support':'same fixed baseline and threshold, independent alarm state; requires lagged power and current two thermal values, one contiguous lag; report separately'},
          'quality':{'zeros':'finite observed zero remains valid; never closure/normal truth','missing':'raw empty/nonfinite or float32 overflow marked invalid; no zero fill/interpolation/clamping',
          'fit_selection_window':'all 160 rows finite in all 3 signals, status0 and exact 600s cadence',
          'calibration_window':'128 past 3-signal rows plus current two thermal finite, status0 and exact cadence',
          'test_common_window':'128 past 3-signal rows plus current two thermal finite, exact cadence; ignore all test status labels',
          'minimum_fit_origins_per_anchor':4096,'minimum_selection_origins':256,'minimum_calibration_scores':512,
          'minimum_common_prediction_fraction_each_file':.7,
          'support_floor_reason':'chosen after structural-only audit (worst 77.7003%) and before any sensor numeric decode; research availability floor, not sufficiency certification',
          'quantity_failure':'stop and keep fixed cohort; never replace assets/files or discard an event by outcome'},
          'portable_format':{'dataset':'one binary per event + manifest/closure; raw source remains ZIP',
          'record_bytes':32,'layout':'offset_seconds int64-le @0, source_row_id int64-le @8, finite mask uint8 @16, 3 pad bytes, three float32-le @20',
          'missing_payload':'canonical float32 NaN with mask false; never sent into model','clock':'offset from file-local first timestamp; not a true UTC feature'},
          'can_launch_learning':False,'can_launch_predictions':False,'care_learning_scope':'requires next explicit execution instruction, fixed quality preparation and boundary checks first',
          'rust_goal':'Rust preprocessing/forward/backward/optimizer/checkpoint-resume/alarm-state and banto API/job management; current reference Python only'}
        sources=[]
        for item in a:
            rec={k:item[k] for k in ('farm','event_id','member','member_sha256','asset_id','rows','split_row_counts','split_transitions')}
            rec['anchor']=item['event_id']==split['anchors'][item['asset_id']]
            if rec['anchor']:rec['validation_cut_ordinal']=support[str(item['event_id'])]['validation_cut_ordinal']
            sources.append(rec)
        input_manifest={'schema':'banto.care-input-manifest.v1','contract_id':recipe['contract_id'],'source_archive':provenance['local_source'],
          'source_sha256':provenance['sha256'],'source_md5':provenance['md5'],'license_id':'CC-BY-SA-4.0','source_doi':provenance['doi'],
          'farm':'A','model_feature_order':split['selected_signals'],'signal_metadata':signals,'files':sources,'folds':split['folds'],
          'anchor_policy':'lowest numeric event_id within each asset, independent of event outcomes','anonymous_file_times_never_joined':True,
          'feature_interface':'only the three selected numerical channels enter model tensor; structural IDs are lineage, never features',
          'status_interface':'offline anchor prefix filter only; inference reader drops status before model and alarm',
          'future_preparation_only':True,'sensor_values_decoded_so_far':0}
        reject_truth_fields(recipe);reject_truth_fields(input_manifest)
        for injected in ('event_label','event_start','event_end','event_description','label_root'):
            try:reject_truth_fields({**input_manifest,injected:'injected'})
            except ValueError:pass
            else:raise AssertionError('truth injection not rejected')
        inputs.json('learning.json',recipe);inputs.json('input-manifest.json',input_manifest)
        input_sha=digest(inputs.root/'input-manifest.json');recipe_sha=digest(inputs.root/'learning.json')
        # Evaluator alone gets label paths/records. Input-side bytes are already fixed.
        raw_path=ROOT/'artifacts/care-label-metadata-20261016/event-info-A.csv'
        rows=list(csv.DictReader(io.StringIO(raw_path.read_text()),delimiter=';'))
        truth=[]
        for row in rows:
            truth.append({k:row[k] for k in ('event_id','event_label','event_start','event_end','event_start_id','event_end_id')})
            truth[-1]['asset_key']='A:'+row.get('asset_id',row.get('asset'))
        evaluator.json('label-manifest.json',{'contract_id':recipe['contract_id'],'input_manifest_sha256_before_label_read':input_sha,
                        'source':str(raw_path.resolve()),'source_sha256':digest(raw_path),'rows':truth,'source_root_cause_not_used_for_selection':True})
        evaluation={'schema':'banto.care-event-evaluation.v1','contract_id':recipe['contract_id'],'input_manifest_sha256':input_sha,'learning_recipe_sha256':recipe_sha,
          'label_manifest_sha256':digest(evaluator.root/'label-manifest.json'),
          'freeze_gate':'all 5 fixed folds selected, thresholds frozen and complete neural/common-baseline/native-baseline alarm outputs pinned before scoring labels',
          'label_preexposure':'metadata audit already inspected labels/counts/time alignment, not a blind formal holdout; consumer still must not receive truth',
          'primary_events':22,'expected_anomaly_events':12,'expected_normal_events':10,
          'anomaly_interval':'source event_start..event_end inclusive; map row timestamps to availability by +600 seconds',
          'hit':'first episode OPEN inside shifted anomaly interval; each episode matches at most one event; no across-file matching',
          'already_active_before_start':'report separately; does not count as primary newly-raised detection',
          'lead_proxy':'event_end availability minus matched episode-open availability; not guaranteed physical failure lead',
          'earliness_proxy':'(end-open)/(end-start), clipped [0,1]; miss=0; average over all anomaly events, never detected-only',
          'false_alarm':'episode opens in a normal-event prediction section; other off-window episodes in anomaly files reported separately',
          'exposure':'eligible record intervals [availability,availability+600); file-local recorded exposure only; unique physical equipment-hours not recoverable across anonymized event files',
          'primary_metrics':['asset-macro event recall','asset-macro false episodes per 1000 eligible normal-record-hours','asset-macro normal alarm-duration fraction','asset-macro earliness proxy including misses'],
          'secondary_metrics':['pooled counts/rates','per-event/per-asset support and censored duration','baseline on native support','episode already active before anomaly start','off-window alarms','forecast lead1 MAE on common support','runtime/memory'],
          'macro_denominators':'all fixed assets with the relevant class; show class counts and assets, null where class absent; no silent event removal',
          'exploratory_advantage':'neural common-support macro recall strictly higher, false-episode rate and normal alarm-duration fraction nonincreasing, earliness proxy nondecreasing versus common-support baseline',
          'native_availability_rule':'native-support baseline comparison mandatory; common-support success alone is not operational superiority',
          'official_care_score':'not the primary metric and not an exact paper/official CARE-score reproduction; no aggregate CARE number in this first contract',
          'event_support_gate':'every anomaly interval at least 70% eligible source timestamps and nonempty; each normal asset >=24 eligible recorded hours; shortfall makes campaign incomplete, no event replacement',
          'threshold_selection_uses_event_labels':False,'test_calibration':False,'business_lead_requirement':'unset; this uses annotated anomaly window and proxy end only',
          'statistical_significance_claim':False,'product_adoption':False,'can_launch_scoring':False}
        evaluator.json('evaluation.json',evaluation)
        old=json.loads((ROOT/'examples/configs/metropt-macos-multiday-20261016.json').read_bytes())['budget']
        budget={**old,'fold_units':5,'seed_units':None,'maximum_parent_campaign_seconds':4500,
                'last_fold_includes_scoring_in_same_child_seconds':870,'additional_fit_or_grid':False}
        full={'schema':'banto.care-fixed-contract.v1','contract_id':recipe['contract_id'],'source':provenance,'signals':signals,
          'input_root':str(inputs.root.resolve()),'input_manifest_sha256':input_sha,'learning_recipe_sha256':recipe_sha,
          'evaluator_root':str(evaluator.root.resolve()),'evaluation_sha256':digest(evaluator.root/'evaluation.json'),
          'metadata_split_manifest_sha256':digest(meta/'split-manifest.json'),'budget':budget,
          'stages':{'metadata_and_contract_fixed':True,'sensor_numeric_preparation':False,'learner_implemented_for_care':False,'training':False,'scoring':False,'rust_port':False},
          '2015_reevaluation':False,'heartbeat':'PAUSED','care_score_reproduction_claim':False}
        example=ROOT/'examples/configs/care-a-maintenance-20261016-r1.json'
        with example.open('x') as f:json.dump(full,f,ensure_ascii=False,indent=2);f.write('\n')
        audit.write('fixed-config.json',example.read_bytes());audit.sources([Path(__file__),ROOT/'models/mini-transformer/metropt_multiday.py',ROOT/'tools/macos_demand_runtime.py'])
        audit.json('checks.json',{'asset_fold_disjointness':True,'all_22_events_test_once':True,'anchors_fixed_before_label_decode':True,
          'input_and_recipe_truth_fields_absent':True,'truth_injection_rejections':5,'input_bytes_fixed_before_evaluator_truth_read':True,
          'structural_quantity_boundary':'sensor floats not read; finite support still unknown','model_feature_count':3})
        for out in (inputs,evaluator):out.close('complete')
        audit.json('summary.json',{'status':'care-contract-fixed-not-trained','contract_id':recipe['contract_id'],'input_closure_sha256':digest(inputs.root/'root-closed.json'),
          'evaluator_closure_sha256':digest(evaluator.root/'root-closed.json'),'config_sha256':digest(example),'sensor_values_decoded':0,'training_runs':0,'scoring_runs':0,'resources':check.check()})
        status='complete'
    except BaseException:
        audit.json('failure.json',{'traceback':traceback.format_exc()},True);raise
    finally:
        for out in (inputs,evaluator,audit):
            if not out.closed:out.close(status)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--inputs',required=True);p.add_argument('--evaluator',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();main(a.inputs,a.evaluator,a.output)
