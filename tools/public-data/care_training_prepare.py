"""Prepare r1 train-only profile and schedule, no neural training/forward/scoring."""
import json
from pathlib import Path
import struct
import sys
import traceback
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'models/mini-transformer'));sys.path.insert(0,str(ROOT/'tools'))
from care_training_preparation import *
from metropt_multiday import Files
from macos_demand_runtime import MacCheckpoint


def artificial():
    checks={}
    q,c=empirical([(0.,.25),(0.,.25),(10.,.5)],.5);assert q==0 and c['cdf_at64']==.5
    assert empirical([(0.,.25),(0.,.25),(10.,.5)],.75)[0]==10
    checks['weighted_inverse_cdf_lower_boundary_and_equal_value_grouping']=True
    toy=[[(0.,0.,0.)],[(10.,10.,10.)]*3,[(20.,20.,20.)]*9]
    scales,alarm=normalization(toy);assert scales[0]['mean64']==10 and math.isclose(scales[0]['variance64'],200/3)
    assert alarm[0]['weighted_median64']==10
    checks['asset_equal_not_pooled_or_window_weighted']=True
    flat,alarms=normalization([[(5.,5.,5.)]]*3)
    assert all(s['T64']==1e-5 and s['context_floor64']==1e-5 for s in flat) and all(a['R64']==1e-3 for a in alarms)
    checks['constant_signal_floors_finite_positive']=True
    assert map_empty_bins([2,0,3,0])==[0,0,2,2]
    checks['empty_bin_nearest_and_lower_tie']=True
    profile=baseline_profile([[(2.,(float(a),float(a)))]*128 for a in range(3)])
    assert profile['load_cuts64']==[2.,2.,2.] and profile['pair_counts']==[384,0,0,0]
    assert baseline_predict(profile,2.)==(1.,1.) and baseline_predict(profile,3.)==(1.,1.) and profile['support_passed']
    checks['duplicate_cuts_equality_lower_and_empty_bin_fallback']=True
    unsupported=baseline_profile([[(1.,(0.,0.))]]*3);assert not unsupported['support_passed']
    checks['small_nonempty_bin_fails_without_rebinning']=True
    train=[('0',0),('10',3),('21',13)];origins={0:[128,129],3:[200,201],13:[300,301]}
    a,counts=schedule(train,origins);b,_=schedule(train,origins)
    assert a==b and len(a)==4096*8*12 and sum(counts)==32768
    checks['full_schedule_deterministic_replacement_and_exact_length']=True
    for values in ([],[(1.,0.)],[(float('nan'),1.)]):
        try:empirical(values,.5)
        except ValueError:pass
        else:raise AssertionError('invalid quantile population accepted')
    checks['empty_zero_mass_nonfinite_rejected']=True
    return checks


def main(dataset,output):
    out=Files(output);check=MacCheckpoint(seconds=870);state='failed';active=None;opened=set();denied=[]
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes)):
            path=str(args[0])
            if any(s in path for s in ('care-evaluator-contract-','care-label-metadata-','event-info-','label-manifest.json')):
                denied.append(path);raise PermissionError('event truth forbidden in preparation')
            if '/care-' in path:opened.add(path)
    sys.addaudithook(audit)
    try:
        out.json('phase.json',{'contract_id':'CARE-A-MAINT-20261016-r1','scope':'train-only normalization/MAD/baseline profile, bin support and schedule freeze',
            'hypothesis':'Every fixed fold has positive finite train scales and >=128 pairs in every nonempty baseline bin; schedules contain fit-prefix origins only. Failure stops without population/bin/seed changes.',
            'quantile_implementation_before_value_access':'group equal values with float64 fsum row masses; total mass fsum; cumulative fsum/mass inverse CDF using binary search, no interpolation',
            'schedule_format':'32768 little-endian <III records: asset uint32, anchor event uint32, source origin ordinal uint32; batch8/4096updates, ordered by update then within-batch',
            'normalization_population':'all-3-finite status0 train bins once per asset, even if near a gap; not window/sampler weighted',
            'baseline_pair_population':'one lagged power[n-1], two thermal[n] pair per eligible full160-row train origin, asset equal; restricted bins retain original asset pair masses',
            'model_training':False,'model_forward':False,'threshold_calibration':False,'test_predictions':False,'event_truth_access':False,'demand_2015':False,
            'portable_schedule_authoritative':'seed alone does not promise Rust RNG equivalence','rust_goal':'training/backward/optimizer/resume/inference/alarm and banto integration'})
        out.sources([Path(__file__),ROOT/'models/mini-transformer/care_training_preparation.py',ROOT/'models/mini-transformer/care_input.py',ROOT/'models/mini-transformer/metropt_multiday.py',ROOT/'tools/macos_demand_runtime.py'])
        out.json('artificial-checks.json',artificial());m=pinned_input()
        if digest(Path(dataset)/'root-closed.json')!=DATA_CLOSURE_SHA:raise ValueError('numeric dataset changed')
        verify_closed(Path(dataset));populations={};pairs={};origins={};population_counts={};meta_by_event={f['event_id']:f for f in m['files']}
        for event in sorted({e for f in m['folds'] for e in f['train_anchor_events']}):
            fold=next(f['fold'] for f in m['folds'] if event in f['train_anchor_events'])
            reader=Consumer(dataset,fold,'fit');d=reader.event(event);ns=normal_rows(d);fit=d.origins('fit')
            if len(fit)<4096 or not ns:raise ValueError('train support')
            populations[event]=[tuple(d._rows[i][3:6]) for i in ns]
            pairs[event]=[(d._rows[n-1][5],tuple(d._rows[n][3:5])) for n in fit]
            origins[event]=fit;population_counts[event]={'all3_finite_status0_bins_once':len(ns),'fit_origins_pairs':len(fit),'train_prefix_rows':d.meta['split_row_counts']['train'],'asset_id':d.meta['asset_id']}
            out.write(f'anchor-{event}-origins.bin',encode_origins(fit));del reader,d;check.check()
        folds=[]
        for fold in m['folds']:
            active=fold['fold'];es=fold['train_anchor_events'];train=list(zip(fold['train_assets'],es,strict=True))
            scales,alarm=normalization([populations[e] for e in es]);baseline=baseline_profile([pairs[e] for e in es])
            raw,draw_counts=schedule(train,origins)
            profile={'schema':'banto.care-training-profile.v1','contract_id':m['contract_id'],'fold':active,'train_assets':fold['train_assets'],
                'train_anchor_events':es,'validation_asset':fold['validation_asset'],'test_asset':fold['test_asset'],
                'normalization_population':[{'event_id':e,**population_counts[e]} for e in es],'normalization':scales,'alarm_scales':alarm,'baseline':baseline,
                'schedule':{'format':'<III asset/event/origin uint32-le','records':32768,'batch':8,'updates':4096,'sampler_seed':SAMPLER_SEED,'draw_counts_by_train_asset':draw_counts},
                'profiles_fit_from_train_only':True,'neural_training':False,'thresholds_not_fitted':True}
            no_truth(profile);out.json(f'fold-{active}-profile.json',profile)
            if not baseline['support_passed']:raise ValueError('nonempty baseline bin below fixed128 floor')
            out.write(f'fold-{active}-schedule.bin',raw)
            folds.append({'fold':active,'profile_sha256':digest(out.root/f'fold-{active}-profile.json'),'schedule_sha256':digest(out.root/f'fold-{active}-schedule.bin'),'baseline_pair_counts':baseline['pair_counts'],'train_assets':fold['train_assets']})
            print(json.dumps({'fold':active,'bin_counts':baseline['pair_counts'],'draw_counts':draw_counts}),flush=True);check.check()
        out.json('manifest.json',{'schema':'banto.care-frozen-training-preparation.v1','contract_id':m['contract_id'],'contract_sha256':CONTRACT_SHA,'input_manifest_sha256':INPUT_SHA,'recipe_sha256':RECIPE_SHA,
            'dataset_closure_sha256':DATA_CLOSURE_SHA,'folds':folds,'origins':[{'event_id':e,'count':len(ns),'sha256':digest(out.root/f'anchor-{e}-origins.bin')} for e,ns in sorted(origins.items())],
            'schedule_records_total':5*32768,'model_source_sha256':'eb0e92990f34cea46cb4f824beb2328767c1de1ae9c110f6501e838c18a0ab99','model_training':False,'forward':False,'performance_scoring':False})
        out.json('summary.json',{'status':'complete','folds':folds,'population_counts':population_counts,'label_bytes_read':0,'baseline_profiles_prepared':5,'schedule_records':163840,
            'all_scale_and_baseline_support_passed':True,'model_training':False,'model_forward':False,'threshold_calibration':False,'performance_scoring':False,
            'care_paths_opened':sorted(opened),'unexpected_label_attempts':denied,'resources':check.check()})
        state='complete'
    except BaseException:
        out.json('failure.json',{'fold':active,'traceback':traceback.format_exc(),'no_rebinning_or_replacement':True},True);raise
    finally:out.close(state)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--dataset',required=True);p.add_argument('--output',required=True);a=p.parse_args();main(a.dataset,a.output)
