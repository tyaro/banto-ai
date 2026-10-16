"""Migrate already-read pre-2015 packets and verify data contracts; no fit/score."""
import time
STARTED=time.monotonic()
import argparse,copy,datetime as dt,json,sys,traceback
from pathlib import Path
from unittest.mock import patch
import demand_input_boundary as b
from verify_demand_transfer import verify,pin
from verification_records import verify_record
from macos_demand_runtime import MacCheckpoint
REPO=Path(__file__).resolve().parents[1]
DOCS=['docs/research/demand-input-boundary-'+n+'-2026-10-15.md' for n in ('design','astra-review')]


def run(output):
    sys.path.insert(0,str(REPO/'models/mini-transformer'))
    from demand_calendar_train import Files
    guard=MacCheckpoint(seconds=870)
    if output.parent!=REPO/'artifacts' or output.exists():raise ValueError('fresh bounded root required')
    files=Files(output);status='failed';stage='sources'
    source=REPO/'artifacts/macos-demand-shared-shrink-20261015'
    seasonal=REPO/'artifacts/macos-demand-seasonal-quantity-20261015'
    try:
        if sys.version_info[:3]!=(3,14,8) or sys.platform!='darwin':raise ValueError('fixed Mac Python 3.14.8 required')
        previous=json.loads((source/'summary.json').read_bytes())
        closures={str(source):verify(source),**previous['closures']}
        for suffix in ('execution-records','readback-records','doc-records'):
            p=Path(str(source)+'-'+suffix);closures[str(p)]=verify(p)
        plan_records=REPO/'artifacts/macos-demand-support-evaluation-plan-20261015-records';closures[str(plan_records)]=verify(plan_records)
        if verify_record(plan_records)['status']!='complete':raise ValueError('closed prior plan required')
        names=[*DOCS,'tools/demand_input_boundary.py','tools/demand_input_boundary_check.py','tests/test_demand_input_boundary.py',
               'docs/research/demand-support-evaluation-plan-2026-10-15.md','docs/research/demand-support-evaluation-astra-review-2026-10-15.md','docs/research/demand-support-evaluation-decisions-2026-10-15.json',*previous['source_pins']]
        pins={p:pin(REPO/p) for p in dict.fromkeys(names)}
        if any(pins[p]!=v for p,v in previous['source_pins'].items()):raise ValueError('old source changed')
        files.json('sources.json',{p:(REPO/p).read_text() for p in pins})
        files.write('contract.md',(REPO/DOCS[0]).read_bytes());files.write('astra-review.md',(REPO/DOCS[1]).read_bytes())
        files.write('source-final-state.json',(source/'source-final-state.json').read_bytes())
        stage='one-time-mixed-source-migration'
        original=b.strict_json((seasonal/'packets-and-inputs.json').read_bytes())
        evidence=b.strict_json((seasonal/'2013-only-scale-and-mask.json').read_bytes())
        inputs=sorted([b.project_input(r) for r in original],key=lambda r:(r['origin'],r['store']))
        if len(inputs)!=470 or len({r['key'] for r in inputs})!=470:raise ValueError('unique archived470 required')
        groups=b.issue_groups(inputs)
        config=b.strict_json((seasonal/'config-before-input.json').read_bytes())
        old_fit=set(map(tuple,config['fit_keys']));actual_fit={(r['store'],r['origin']) for r in inputs if r['origin'].startswith('2013-')}
        if actual_fit!=old_fit or len(old_fit)!=210:raise ValueError('historical selection inventory changed')
        t={'schema':'demand-transform-v1','policy_ref':b.POLICY,'scale_period':{'start':'2013-01-01','end':'2013-12-31'},
           'scale_usable_from':'2014-01-01','scales':{str(s):evidence['scales'][str(s)]['scale'] for s in b.FIT},
           'closure_period':{'start':'2013-01-01','end':'2013-12-31'},'closure_usable_from':'2014-01-01',
           'month_days':['01-01','12-25'],'availability_basis':b.DAY_ASSUMPTION}
        b.validate_transforms(t)
        if any(r['scale']!=t['scales'][str(r['store'])] for r in original):raise ValueError('old scale mismatch')
        files.write('inputs.json',b.canonical(inputs));files.write('transforms.json',b.canonical(t))
        labels=[b.project_label(r) for r in original];payload,index=b.label_payload(labels)
        files.write('labels.jsonl',payload);files.write('label-index.json',b.canonical(index))
        b.validate_index(index,inputs,len(payload))
        binding={'schema':'demand-input-label-binding-v1','file_pins':{n:files.pins[n] for n in ('inputs.json','transforms.json','labels.jsonl','label-index.json')},
                 'keys':sorted(r['key'] for r in inputs),'migration_source_pin':pin(seasonal/'packets-and-inputs.json'),
                 'scale_mask_source_pin':pin(seasonal/'2013-only-scale-and-mask.json'),'archived_2013_keys':sorted(old_fit),
                 'historical_selection_not_prospective_population':True,'availability_assumption':b.DAY_ASSUMPTION,'input_hash_excludes_label_pins':True}
        files.json('binding.json',binding)
        files.json('issue-schedule.json',{'groups':groups,'defined_from':'2014-01-01+14*k k=0..25 x FIT10; no label dependency','unknown_operating_status':True})
        stage='input-only-consumer'
        blocked_paths={(seasonal/'packets-and-inputs.json').resolve(),(output/'labels.jsonl').resolve(),(output/'label-index.json').resolve()}
        orig_open=Path.open
        def restricted(path,*args,**kwargs):
            if path.resolve() in blocked_paths:raise AssertionError('input consumer attempted mixed/label read')
            return orig_open(path,*args,**kwargs)
        with patch.object(Path,'open',restricted),patch.object(b.LabelReader,'_decode',side_effect=AssertionError('input consumer label decode')):
            clean=b.load_inputs(output/'inputs.json',binding['file_pins']['inputs.json'])
            transforms=b.load_transforms(output/'transforms.json',binding['file_pins']['transforms.json'])
            clean_groups=b.issue_groups(clean)
            ready={r['key']:b.input_readiness(r,transforms) for r in clean}
        if clean_groups!=groups or sum(v['ready'] for v in ready.values())!=260:raise ValueError('2014 input readiness / 2013 blocked expected')
        stage='label-canaries'
        checks=[];original_input_bytes=b.canonical(inputs)
        for name in ('all_zero','all_missing','large_values','label_fields_absent','reversed_rows'):
            altered=copy.deepcopy(original)
            if name=='reversed_rows':altered.reverse()
            for r in altered:
                if name=='all_zero':r['actual']=[0.]*14
                elif name=='all_missing':r['actual']=[None]*14
                elif name=='large_values':r['actual']=[999999.]*14
                elif name=='label_fields_absent':r.pop('actual');r.pop('complete_label',None)
                r['raw_prediction']={'forbidden_future_label_canary':True};r['profile']={'target_actual':'canary'}
            projected=sorted([b.project_input(r) for r in altered],key=lambda r:(r['origin'],r['store']))
            if b.canonical(projected)!=original_input_bytes or b.issue_groups(projected)!=groups or {r['key']:b.input_readiness(r,t) for r in projected}!=ready:raise ValueError('label leaked into input path')
            checks.append({'canary':name,'input_bytes_pin':b.pin_bytes(b.canonical(projected)),'input_groups_and_readiness_unchanged':True})
        files.json('canary-proof.json',{'cases':checks,'label_missing_or_extra_rejected_only_at_binding':True,'historical_selection_bias_not_removed':True,'mixed_and_label_read_blocked_in_input_consumer':True})
        stage='quarter-prefix-availability'
        availability={}
        for cutoff in b.CUTS:
            reader=b.LabelReader(output/'labels.jsonl',index,clean,binding['file_pins']['labels.jsonl'])
            original_decode=reader._decode
            def checked(entry):
                if b.day(entry['target_dates'][-1])>=b.day(cutoff) or b.day(entry['available_at'])>b.day(cutoff):raise AssertionError('future label decode')
                return original_decode(entry)
            with patch.object(reader,'_decode',checked):ledger=b.fit_prefix(clean,t,reader,cutoff)
            expected=[210,270,330,400][b.CUTS.index(cutoff)]
            if len(ledger['accepted_keys'])!=expected or len(ledger['decoded_keys'])!=expected:raise ValueError('cutoff count changed')
            availability[cutoff]=ledger;guard.check()
        files.json('cutoff-availability.json',availability)
        stage='label-scenario-contract-only'
        reader=b.LabelReader(output/'labels.jsonl',index,clean,binding['file_pins']['labels.jsonl']);support={}
        for row in clean:
            label=reader.read_available(row,'2014-12-31');scenarios=b.label_scenarios(row,label)
            if label['raw_actual']!=next(r['actual'] for r in original if (r['store'],r['origin'])==(row['store'],row['origin'])):raise ValueError('raw label changed')
            year=row['origin'][:4];g=support.setdefault(year,{'windows':0,'original_observed_days':0,'raw_nulls':0,'imputed_closure_positions':0,'observed_complete':0,'assumed_complete':0})
            g['windows']+=1;g['original_observed_days']+=scenarios['original_observed_days'];g['raw_nulls']+=sum(v is None for v in label['raw_actual']);g['imputed_closure_positions']+=len(scenarios['imputed_positions']);g['observed_complete']+=scenarios['observed']['complete'];g['assumed_complete']+=scenarios['assumed_missing_zero']['complete']
        files.json('scenario-support.json',{'support':support,'performance_metrics_computed':False,'raw_nulls_preserved':True,'missing_zero_is_not_training_label':True})
        files.json('evaluation-policy-carried.json',{'adjustment_last_year':2014,'quarterly_coefficients_frozen_rule_only':True,'new_state':False,
            'risks_per_quarter':['total_MSE','mean_under','mean_over'],'paired_comparator':'same closure-assumption mean28','label_scenarios':['observed','assumed_missing_zero'],
            'outer_posthoc_replacement':False,'MSE_tolerance':1e-12,'quantity_tolerance':1e-8,'new_performance_evaluation':False,'formal_permission':False})
        if {p:verify(Path(p)) for p in closures}!=closures or any(pin(REPO/p)!=v for p,v in pins.items()):raise ValueError('protected source or root changed')
        summary={'status':'complete','closures':closures,'source_pins':pins,'migration_only_mixed_source_read':True,'input_consumer_label_read':False,
            'rows':470,'history2013':210,'issues2014':260,'issue_groups':26,'readiness2014':260,'readiness2013_blocked_by_transforms':210,
            'cutoff_complete_counts':[len(v['accepted_keys']) for v in availability.values()],'no_future_label_decode_in_prefix':True,
            'actual_arrival_timestamp_or_timezone_verified':False,'availability_assumption':b.DAY_ASSUMPTION,'historical_selection_bias_removed':False,
            'independent_validation':False,'new_fit':False,'new_model_predictions':False,'new_scores':False,'2015_new_content_use_or_evaluation':False,
            'source_state_pin':pin(source/'source-final-state.json'),'baseline_copied_and_context_verified':True,'formal_permission':False,'adopted':False,
            'resources':guard.check(),'seconds':time.monotonic()-STARTED}
        files.json('summary.json',summary);status='complete';print(json.dumps(summary),flush=True)
    except BaseException as error:
        files.json('failure.json',{'stage':stage,'type':type(error).__name__,'message':str(error),'traceback':traceback.format_exc()},True);raise
    finally:files.json('root-closed.json',{'status':status,'files':files.pins.copy(),'immutable':True,'formal_permission':False},True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output.absolute())
