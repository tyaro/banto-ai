"""Predeclared origin-deletion sensitivity; never score outer labels."""
import argparse,json,math,sys,time,traceback
from pathlib import Path
from fractions import Fraction as F
from demand_seasonal_shared_2014 import (select_season,train_batch,quarter,Output,REPO,CONTRACT)
from demand_constrained_qp_v2 import predict_total,number,Budget
from macos_demand_runtime import MacCheckpoint
from verify_demand_transfer import verify,pin


def probe_difference(primary,q,beta):
    if any(not f['origin'].startswith('2014-') or quarter(f['origin'])!=q for f in primary):raise ValueError('fixed same-Q 2014 probes required')
    changes=[]
    for f in primary:
        unit=14*number(f['scale']);P=predict_total(f['baseline'],unit,f['features'],beta);delta=P-F(f['candidate_total'])
        Budget().check(P,delta)
        changes.append({'key':f['key'],'store':f['store'],'origin':f['origin'],'feature_eligible':f['features'] is not None,
            'alternative_total':str(P),'delta_from_primary':str(delta),'unit':str(unit)})
    def stats(rr):
        if not rr:return {'count':0,'changed':0,'max_absolute':None,'mean_absolute':None,'mean_square':None,'RMS_display':None,'scaled_mean_square':None}
        dd=[F(r['delta_from_primary']) for r in rr];ms=sum((d*d for d in dd),F(0))/len(dd)
        scaled=sum(((F(r['delta_from_primary'])/F(r['unit']))**2 for r in rr),F(0))/len(rr)
        Budget().check(ms,scaled)
        return {'count':len(rr),'changed':sum(d!=0 for d in dd),'max_absolute':str(max(map(abs,dd))),
            'mean_absolute':str(sum(map(abs,dd),F(0))/len(dd)),'mean_square':str(ms),'RMS_display':math.sqrt(float(ms)),
            'scaled_mean_square':str(scaled)}
    return {'all_probes':stats(changes),'eligible_probes':stats([r for r in changes if r['feature_eligible']]),'probes':changes}


def run(output,primary):
    started=time.monotonic();guard=MacCheckpoint(seconds=870)
    if output.parent!=REPO/'artifacts' or output.exists():raise ValueError('fresh root required')
    files=Output(output);status='failed';stage='sources';finished=[];current=[];pending=None
    try:
        if sys.version_info[:3]!=(3,14,8) or sys.platform!='darwin':raise ValueError('fixed Mac runtime')
        if verify(primary)['recorded_status']!='complete':raise ValueError('primary must complete first')
        protected=json.loads((primary/'protected.json').read_bytes());protected['closures'][str(primary)]=verify(primary)
        for suffix in ('-execution-records',):protected['closures'][str(primary)+suffix]=verify(Path(str(primary)+suffix))
        files.json('protected.json',protected);files.write('contract.md',(REPO/CONTRACT).read_bytes())
        forecasts=json.loads((primary/'predictions-before-scoring.json').read_bytes())
        plan=[];states=[]
        for q,cutoff in enumerate(('2014-01-01','2014-04-01','2014-07-01','2014-10-01'),1):
            state=json.loads((primary/('state-'+cutoff+'.json')).read_bytes());states.append(state)
            origins=state['support']['origins'];assert len(origins)==(3,6,7,5)[q-1]
            plan.extend({'q':q,'cutoff':cutoff,'exclude_origin':o} for o in origins)
        assert len(plan)==21
        files.json('plan-before-deletions.json',{'cases':plan,'primary_prediction_pin':pin(primary/'predictions-before-scoring.json'),
            'primary_summary_pin':pin(primary/'summary.json'),'probe_counts':[70,60,70,60],'outer_labels_scored':False})
        for q,state in enumerate(states,1):
            current=[];probes=[f for f in forecasts if quarter(f['origin'])==q];assert len(probes)==(70,60,70,60)[q-1]
            for origin in state['support']['origins']:
                stage=f'Q{q}-remove-{origin}'
                original=state['training_payload'];removed=[r for r in original['rows'] if r['origin']==origin]
                assert len(removed)==10 and len({r['store'] for r in removed})==10
                payload=select_season(original,excluded_origin=origin)
                pending={'quarter':q,'excluded_origin':origin,'payload':payload}
                alternative=train_batch(payload,guard.check)
                changed=probe_difference(probes,q,alternative['beta'])
                coef=[F(a)-F(b) for a,b in zip(alternative['beta'],state['beta'])]
                current.append({'quarter':q,'cutoff':state['cutoff'],'excluded_origin':origin,'removed_keys':[r['key'] for r in removed],
                    'support':alternative['support'],'problem':alternative['problem'],'certificate':alternative['certificate'],'verification':alternative['verification'],
                    'beta':alternative['beta'],'coefficient_difference':list(map(str,coef)),**changed})
                guard.check()
            files.json(f'influence-Q{q}.json',current);finished.extend(current)
            print(json.dumps({'stage':'quarter-deletions-complete','q':q,'cases':len(current)}),flush=True)
        if {p:verify(Path(p)) for p in protected['closures']}!=protected['closures'] or any(pin(REPO/p)!=v for p,v in protected['source_pins'].items()):raise ValueError('protected evidence changed')
        summary={'status':'complete','cases':len(finished),'folds_with_changed_coefficients':sum(any(F(v)!=0 for v in r['coefficient_difference']) for r in finished),
            'folds_with_changed_probes':sum(r['all_probes']['changed']>0 for r in finished),
            'max_absolute_probe_difference':str(max(F(r['all_probes']['max_absolute']) for r in finished)),
            'outer_labels_scored':False,'statistical_independent_validation':False,'primary_selection_changed':False,'new2015':False,
            'resources':guard.check(),'seconds':time.monotonic()-started,'formal_permission':False}
        files.json('summary.json',summary);status='complete';print(json.dumps(summary),flush=True)
    except BaseException as exc:
        files.json('failure.json',{'stage':stage,'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc(),'later_deletions_stopped':True,'primary_unchanged':True},True)
        files.json('failure-partial.json',{'completed_quarters':len(finished),'current_cases':current,'dependence_assessment_incomplete':True},True)
        files.json('failure-pending-fold.json',pending,True)
        raise
    finally:files.json('root-closed.json',{'status':status,'files':files.pins.copy(),'immutable':True,'formal_permission':False},True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--primary',type=Path,required=True)
    a=p.parse_args();run(a.output.absolute(),a.primary.absolute())
