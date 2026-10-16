"""2014-only finite shared-shrink stability experiment; no new 2015 read/eval."""
import time
STARTED=time.monotonic()
import argparse,datetime as dt,json,math,sys,traceback
from pathlib import Path
from demand_shared_shrink import ORDER,calibrate,choices,choose,measure,candidates,attach_reliability,influence
from demand_autonomous_mean import read_history
from demand_recurring_closure import attach_scenarios
from demand_persistence_evaluation import groups_2014,activity
from demand_seasonal_quantity import quarter
from macos_demand_runtime import MacCheckpoint
from verify_demand_transfer import verify,pin
REPO=Path(__file__).resolve().parents[1]
PREFIX='docs/research/demand-shared-shrink-'
DOCS=[PREFIX+n+'-2026-10-15.md' for n in ('design','astra-review','process-audit')]


def frame(row,policy):
    pp=choices(row,policy)
    return {'store':row['store'],'origin':row['origin'],'scale':row['scale'],'baseline':pp['matched_mean28'],
            'prior':pp['matched_mean28'],'baseline_proxy':pp['matched_mean28'],'candidate':pp['matched_mean28'],
            'alternatives':pp,'selected_method':'matched_mean28','persistence_support':candidates(row)[1],
            'assumed_closure':[not x for x in row['open_mask']],'operating_status':['unknown']*14}


def run(output):
    from demand_calendar_train import Files
    import torch
    guard=MacCheckpoint(seconds=870)
    if output.parent!=REPO/'artifacts' or output.exists():raise ValueError('fresh artifact root required')
    files=Files(output);status='failed';stage='sources';policy=None
    source=REPO/'artifacts/macos-demand-persistence-20261015';seasonal=REPO/'artifacts/macos-demand-seasonal-quantity-20261015'
    try:
        if sys.version_info[:3]!=(3,14,8) or sys.platform!='darwin' or torch.__version__!='2.14.0':raise ValueError('fixed Mac runtime required')
        config=json.loads((source/'config-before-input.json').read_bytes())
        closures={str(source):verify(source),**config['closures']}
        for suffix in ('execution-records','readback-records','doc-records'):
            p=Path(str(source)+'-'+suffix);closures[str(p)]=verify(p)
            if closures[str(p)]['recorded_status']!='complete':raise ValueError('latest complete evidence required')
        if {p:verify(Path(p)) for p in closures}!=closures:raise ValueError('protected closure changed')
        names=[*DOCS,'tools/demand_shared_shrink.py','tools/demand_shared_shrink_evaluation.py','tests/test_demand_shared_shrink.py',*config['source_pins']]
        pins={n:pin(REPO/n) for n in dict.fromkeys(names)}
        if any(pins[p]!=v for p,v in config['source_pins'].items()):raise ValueError('source pin changed')
        files.json('sources.json',{p:(REPO/p).read_text() for p in pins})
        for label,name in zip(('contract.md','astra-review.md','process-audit.md'),DOCS):files.write(label,(REPO/name).read_bytes())
        state=json.loads((source/'source-final-state.json').read_bytes())
        if state['journal']['last_label_day']>='2015-01-01' or state['new_2015_fit']:raise ValueError('pre-2015 state required')
        files.json('source-final-state.json',state)
        files.json('config-before-input.json',{'closures':closures,'source_pins':pins,'order':ORDER,
            **{k:config[k] for k in ('2014_keys','calibration_keys','selection_keys','annual_source_pin','source_packet_pin')},
            'source_state_pin':pin(source/'source-final-state.json'),'source_calibration_pin':pin(source/'frozen-calibration.json'),
            '2015_input_label_metric_reads':0,'formal_permission':False,'fixed_shrink_constant':1.})
        stage='fixed-2014-calibration'
        packets=json.loads((seasonal/'packets-and-inputs.json').read_bytes());allowed=set(map(tuple,config['2014_keys']))
        history=read_history(REPO/'artifacts/macos-demand-rebuild-20261015/selected-internal.csv',dt.date(2013,1,1),dt.date(2014,12,31))
        by_key={(r['store'],r['origin']):attach_reliability(r,history) for r in packets if (r['store'],r['origin']) in allowed}
        if set(by_key)!=allowed or any(not d.startswith('2014-') for s,d in by_key):raise ValueError('2014-only packets required')
        cal=set(map(tuple,config['calibration_keys']));sel=set(map(tuple,config['selection_keys']))
        policy,journal=calibrate([by_key[tuple(k)] for k in config['calibration_keys']])
        old_cal=json.loads((source/'frozen-calibration.json').read_bytes())['sample_journal']
        for q,rows in journal.items():
            if rows!=old_cal[q]['persistent_anchor']:raise ValueError('frozen raw endpoint/journal changed')
        files.json('frozen-calibration.json',{'policy':policy,'sample_journal':journal,'observed_only':True,'calibration_keys':config['calibration_keys']})
        contributions=[]
        for q,rr in journal.items():
            for r in rr:
                a=r['weight']*(r['D']/(14*r['scale']))**2;c=-r['weight']*r['e']*r['D']/(14*r['scale'])**2
                contributions.append(dict(r,quarter=q,energy=a,covariance=c,global_energy=a/4,global_covariance=c/4,
                    single_window_C_over_A=-r['e']/r['D'] if abs(r['D'])>1e-8 else None))
        files.json('calibration-contributions.json',{'rows':contributions,'independent_support_claim':False})
        print(json.dumps({'stage':'concentration-before-performance','global':policy['global_statistics'],'global_shrunk':policy['global_shrunk']}),flush=True)
        validation=[by_key[tuple(k)] for k in config['2014_keys']]
        labels={(r['store'],r['origin']):r for r in validation}
        obs,assumed,ledger=attach_scenarios([frame(r,policy) for r in validation],labels)
        files.json('2014-observed-labels.json',obs);files.json('2014-assumed-labels.json',assumed);files.json('2014-assumption-ledger.json',ledger)
        grouped={};grouped_rows={}
        for mode,rr in (('observed',obs),('assumed_missing_zero',assumed)):
            groups=groups_2014(rr,sel,cal);grouped_rows[mode]=groups
            if len(groups['normal120'])!=120 or len(groups['newyear'])!=10 or any(len(groups[f'normal_Q{q}'])!=30 for q in range(1,5)):raise ValueError('fixed 2014 selection support required')
            for group,rows in groups.items():grouped.setdefault(group,{})[mode]={m:measure(rows,lambda r,m=m:r['alternatives'][m]) for m in ORDER}
        stage='quarter-risk-choice'
        selection=choose(grouped)
        for mode,groups in grouped_rows.items():
            for group,rows in groups.items():grouped[group][mode]['selected_policy']=measure(rows,lambda r:r['alternatives'][selection['selected_by_quarter'][str(quarter(r['origin']))]])
        files.json('2014-evaluation.json',grouped)
        files.json('frozen-policy-2014-only.json',{'policy':policy,'selection':selection,'2015_evaluation_authorized_by_this_contract':False,'no_automatic_next_experiment':True})
        stage='fixed-23-influence-removals'
        normal=[]
        for r in validation:
            if (r['store'],r['origin']) in sel and r['origin']!='2014-01-01':
                raw=candidates(r)[0];normal.append({'store':r['store'],'origin':r['origin'],'D':math.fsum(raw['pooled_shrink'])-math.fsum(raw['matched_mean28'])})
        fixed={'calibration120':[r for rr in journal.values() for r in rr],'normal120':normal}
        diag=influence(journal,config['calibration_keys'],fixed)
        if len(diag['folds'])!=23:raise ValueError('fixed 23 sensitivity removals required')
        files.json('fixed-D-influence.json',diag);files.json('fixed-D-inputs.json',fixed);guard.check()
        # Missing=0 is report-only calibration sensitivity, never a fit or extra guard.
        sensitivity={mode:{m:measure(grouped_rows[mode]['calibration'],lambda r,m=m:r['alternatives'][m]) for m in ORDER} for mode in grouped_rows}
        files.json('calibration-label-sensitivity-report-only.json',sensitivity)
        if {p:verify(Path(p)) for p in closures}!=closures or any(pin(REPO/p)!=v for p,v in pins.items()):raise ValueError('protected evidence changed')
        summary={'status':'complete','closures':closures,'source_pins':pins,'selection':selection,'policy':policy,
            'activity_2014':{g:activity(rows) for g,rows in grouped_rows['observed'].items()},'resources':guard.check(),'seconds':time.monotonic()-STARTED,
            'new_ridge_fits':0,'fit_after_2014':False,'2015_input_label_metric_reads':0,'2015_new_predictions':0,'2015_new_evaluations':0,
            'source_final_windows':state['journal']['pool_windows'],'source_last_label':state['journal']['last_label_day'],
            'universal_window_guarantee':False,'gate_uses_alpha':False,'fixed_gate_thresholds':True,'annual_coefficient_shared':False,
            'finite_study_finished':True,'independent_performance_validation':False,'adopted':False,'formal_permission':False}
        files.json('summary.json',summary);status='complete'
        print(json.dumps({'status':status,'selection':selection,'seconds':summary['seconds'],'2015_new_evaluations':0}),flush=True)
    except BaseException as e:
        files.json('failure.json',{'stage':stage,'type':type(e).__name__,'message':str(e),'traceback':traceback.format_exc()},True)
        files.json('failure-prefix.json',{'policy':policy},True);raise
    finally:files.json('root-closed.json',{'status':status,'files':files.pins.copy(),'immutable':True,'formal_permission':False},True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output.absolute())
