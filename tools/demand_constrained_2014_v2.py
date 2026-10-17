"""One preregistered already-read 2014 replay. No 2015 content or rescue."""
import argparse
import copy
import json
import math
import os
import sys
import time
import traceback
from fractions import Fraction as F
from pathlib import Path

from demand_constrained_qp_v2 import from_prefix, solve, predict_total, quantity_total, number, Budget
from demand_constrained_qp_verify import verify as verify_certificate
from demand_prefix_adapter import input_features
from demand_input_boundary_v2 import (FIT,CUTS,load_inputs,load_transforms,LabelReader,label_scenarios)
from demand_input_boundary_v2 import _pinned_json
from verify_demand_transfer import verify, pin
from verification_records import verify_record
from macos_demand_runtime import MacCheckpoint

REPO=Path(__file__).resolve().parents[1]
CONTRACT='docs/research/demand-constrained-2014-contract-v2-2026-10-15.md'
MANDATORY=[f'Q{q}_{kind}' for q in range(1,5) for kind in ('all','normal')]+['newyear10']


class Output:
    """Same reviewed artifact limits without importing the unrelated torch trainer."""
    def __init__(self,root):self.root=root;root.mkdir();self.pins={}
    def write(self,name,raw,failure=False):
        files=list(self.root.iterdir());maxfiles,maxbytes=(32,1024**3) if failure else (24,768*1024**2)
        if Path(name).name!=name or name in self.pins or (self.root/'root-closed.json').exists():raise ValueError('fresh entry required')
        if any(not p.is_file() or p.is_symlink() for p in files):raise ValueError('regular output files required')
        if len(files)+1>maxfiles or len(raw)>32*1024**2 or sum(p.stat().st_size for p in files)+len(raw)>maxbytes:raise RuntimeError('artifact_limit')
        with (self.root/name).open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        self.pins[name]=pin(self.root/name)
    def json(self,name,value,failure=False):self.write(name,json.dumps(value,allow_nan=False,sort_keys=True).encode(),failure)


def save_failure(files,stage,exc,states,forecasts):
    files.json('failure.json',{'stage':stage,'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()},True)
    files.json('failure-progress.json',{'states_finished':len(states),'predictions_finished':len(forecasts),'later_quarters_and_scoring_stopped':True},True)
    files.json('failure-predictions.json',forecasts,True)


def quarter(origin):return (int(origin[5:7])-1)//3+1


def train_batch(batch,checkpoint):
    # Only the concrete permitted prefix enters this function, never full inputs.
    built=from_prefix(copy.deepcopy(batch))
    if not built['supported']:
        raise RuntimeError('required_model_support_missing: '+built['reason'])
    certificate=solve(built['problem'],checkpoint=checkpoint)
    checked=verify_certificate(built['problem'],certificate)
    checkpoint()
    return {'cutoff':batch['cutoff'],'supported':True,'reason':None,'beta':certificate['beta'],
            'problem':built['problem'],'certificate':certificate,'verification':checked}


def forecast(row,transforms,state):
    q=quarter(row['origin'])
    if not row['origin'].startswith('2014-') or state['cutoff']!=CUTS[q-1]:raise ValueError('matching 2014 Q state required')
    x,why=input_features(row,transforms);baseline=list(row['matched_mean28']);B=quantity_total(baseline)
    unit=14*number(transforms['scales'][str(row['store'])])
    P=predict_total(baseline,unit,x,state['beta']) if state['supported'] else B
    exact_base=list(map(number,baseline));E=sum(exact_base,F(0));delta=P-B
    if delta==0 or x is None or B==0 or not state['supported']:
        exact=list(exact_base);display=list(baseline);branch='baseline_copy'
    elif P==0:
        exact=[F(0)]*14;display=[0.]*14;branch='floor_zero'
    else:
        exact=[b*P/E for b in exact_base];display=list(map(float,exact));branch='changed_proportional'
    if any(v<0 or (not good and v!=0) for v,good in zip(exact,row['assumed_open_mask'])):raise ValueError('masked nonnegative prediction required')
    if any(not math.isfinite(v) for v in display):raise ValueError('finite daily display required')
    if branch!='baseline_copy' and sum(exact)!=P:raise ValueError('changed daily total mismatch')
    Budget().check(P,exact)
    return {'key':row['key'],'store':row['store'],'origin':row['origin'],'cutoff':state['cutoff'],
      'scale':transforms['scales'][str(row['store'])],'features':x,'feature_reasons':why,
      'baseline':baseline,'candidate_display':display,'candidate_daily_exact':list(map(str,exact)),
      'baseline_total':str(B),'candidate_total':str(P),'delta_total':str(delta),
      'assumed_open_mask':list(row['assumed_open_mask']),'operating_status':['unknown']*14,
      'allocation':{'branch':branch,'exact_baseline_sum':str(E),'canonical_baseline_minus_exact_sum':str(B-E),
        'exact_candidate_sum':str(sum(exact)),'display_sum_minus_canonical':str(number(math.fsum(display))-P)}}


def score_group(rows,mode,checkpoint=lambda:None):
    result={};scored={name:{} for name in ('matched_mean28','candidate')}
    for store in FIT:
        rr=[r for r in rows if r['forecast']['store']==store]
        if not rr:raise ValueError('all FIT stores in each reported group required')
        for name in scored:
            total=[];under=[];over=[];daily=[];quantity=[]
            for r in rr:
                f=r['forecast'];actual=r[mode];u=number(f['scale']);unit=14*u
                pd=list(map(number,f['baseline'])) if name=='matched_mean28' else list(map(F,f['candidate_daily_exact']))
                for p,a,opened in zip(pd,actual,f['assumed_open_mask']):
                    if a is not None:
                        square=((p-number(a))/u)**2;daily.append(square)
                        if opened:quantity.append(square)
                if None not in actual:
                    Y=quantity_total(actual);P=F(f['baseline_total'] if name=='matched_mean28' else f['candidate_total']);e=P-Y
                    total.append((e/unit)**2);under.append(max(-e,0));over.append(max(e,0))
            if not total or not daily or not quantity:raise ValueError('complete total and daily quantity support required')
            metrics={'total_MSE':sum(total,F(0))/len(total),'under':sum(under,F(0))/len(under),'over':sum(over,F(0))/len(over),
                'daily_MSE':sum(daily,F(0))/len(daily),'quantity_MSE':sum(quantity,F(0))/len(quantity)}
            Budget(checkpoint=checkpoint).check(list(metrics.values()))
            scored[name][str(store)]={'exact':{k:str(v) for k,v in metrics.items()},
                'total_support':len(total),'daily_support':len(daily),'quantity_support':len(quantity)}
        checkpoint()
    for name,per_store in scored.items():
        macro={k:sum(F(v['exact'][k]) for v in per_store.values())/10 for k in ('total_MSE','under','over','daily_MSE','quantity_MSE')}
        Budget(checkpoint=checkpoint).check(list(macro.values()))
        result[name]={'macro_exact':{k:str(v) for k,v in macro.items()},'macro_display':{k:float(v) for k,v in macro.items()},
            'per_store':per_store,'complete_totals':sum(v['total_support'] for v in per_store.values()),
            'daily_support':sum(v['daily_support'] for v in per_store.values()),'quantity_support':sum(v['quantity_support'] for v in per_store.values()),'windows':len(rows)}
    difference={k:F(result['candidate']['macro_exact'][k])-F(result['matched_mean28']['macro_exact'][k]) for k in ('total_MSE','under','over','daily_MSE','quantity_MSE')}
    violations=[k for k in ('total_MSE','under','over') if difference[k]>0]
    result.update({'paired_exact':{k:str(v) for k,v in difference.items()},'paired_display':{k:float(v) for k,v in difference.items()},'violations':violations,'eligible':not violations})
    return result


def evaluate(rows,checkpoint=lambda:None):
    origin=lambda r:r['forecast']['origin'];Q=lambda r:quarter(origin(r))
    groups={'all260':rows,'normal250':[r for r in rows if origin(r)!='2014-01-01'],
        'newyear10':[r for r in rows if origin(r)=='2014-01-01'],'yearend':[r for r in rows if origin(r).startswith('2014-12-')]}
    for q in range(1,5):
        groups[f'Q{q}_all']=[r for r in rows if Q(r)==q]
        groups[f'Q{q}_normal']=[r for r in rows if Q(r)==q and origin(r)!='2014-01-01']
    return {name:{mode:score_group(rr,mode,checkpoint) for mode in ('observed','assumed_missing_zero')} for name,rr in groups.items()}


def run(output):
    started=time.monotonic();guard=MacCheckpoint(seconds=870)
    if output.parent!=REPO/'artifacts' or output.exists():raise ValueError('fresh artifact root required')
    files=Output(output);status='failed';stage='sources';states=[];forecasts=[]
    try:
        if sys.version_info[:3]!=(3,14,8) or sys.platform!='darwin':raise ValueError('Mac Python3.14.8 required')
        oldroot=REPO/'artifacts/macos-demand-common-residual-20261015';old=json.loads((oldroot/'summary.json').read_bytes())
        names=['macos-demand-common-residual-20261015'+suffix for suffix in ('','-execution-records','-readback-records','-doc-records')]
        names += ['macos-demand-constrained-training-20261015'+suffix for suffix in ('-records','-doc-records')]
        names += ['macos-demand-constrained-numerics-20261015'+suffix for suffix in ('-records','-records-readback','-v2-records','-doc-records')]
        closures={**old['closures'],**{str(REPO/'artifacts'/n):verify(REPO/'artifacts'/n) for n in names}}
        new=[CONTRACT,'docs/research/demand-constrained-2014-astra-review-2026-10-15.md',
            'tools/demand_constrained_qp.py','tools/demand_constrained_qp_v2.py','tools/demand_constrained_qp_verify.py',
            'tools/demand_constrained_2014.py','tests/test_demand_constrained_2014.py',
            'tools/demand_constrained_2014_v2.py','tests/test_demand_constrained_2014_v2.py']
        pins={p:pin(REPO/p) for p in dict.fromkeys([*old['source_pins'],*new])}
        if any(pins[p]!=v for p,v in old['source_pins'].items()):raise ValueError('old source changed')
        files.write('contract.md',(REPO/CONTRACT).read_bytes());files.json('sources.json',{p:(REPO/p).read_text() for p in pins})
        files.json('protected.json',{'closures':closures,'source_pins':pins})
        files.json('configuration.json',{'cutoffs':CUTS,'FIT':FIT,'limits':dict(Budget().limits),'mandatory':MANDATORY,'one_pass':True,'2015':False,'formal_permission':False})
        source=REPO/'artifacts/macos-demand-input-boundary-20261015-v2';prefix=REPO/'artifacts/macos-demand-prefix-adapter-20261015'
        binding=_pinned_json(source/'binding.json',pin(source/'binding.json'))
        inputs=load_inputs(source/'inputs.json',binding['file_pins']['inputs.json']);t=load_transforms(source/'transforms.json',binding['file_pins']['transforms.json'])
        for i,cutoff in enumerate(CUTS):
            stage='fit-'+cutoff;path=prefix/('prefix-'+cutoff+'.json');batch=_pinned_json(path,pin(path))
            if len(batch['rows'])!=(210,270,330,400)[i] or sum(r['features'] is not None for r in batch['rows'])!=(210,250,310,380)[i]:raise ValueError('fixed prefix support drift')
            state=train_batch(batch,guard.check);state['source_prefix_pin']=pin(path);states.append(state)
            files.json('state-'+cutoff+'.json',state)
            forecasts.extend(forecast(r,t,state) for r in inputs if r['origin'].startswith('2014-') and quarter(r['origin'])==i+1)
            guard.check();print(json.dumps({'stage':'quarter_verified','cutoff':cutoff,'supported':state['supported'],'beta_display':list(map(lambda v:float(F(v)),state['beta'])),'predictions_so_far':len(forecasts)}),flush=True)
        if len(forecasts)!=260 or len({r['key'] for r in forecasts})!=260:raise ValueError('260 fixed issues required')
        files.json('predictions-before-scoring.json',forecasts)
        freeze={'states':{n:v for n,v in files.pins.items() if n.startswith('state-')},'predictions_pin':files.pins['predictions-before-scoring.json'],
            'source_binding_pin':pin(source/'binding.json'),'input_pin':binding['file_pins']['inputs.json'],'transform_pin':binding['file_pins']['transforms.json'],
            'label_payload_pin':binding['file_pins']['labels.jsonl'],'label_index_pin':binding['file_pins']['label-index.json'],'all_predictions_saved_before_scoring':True}
        files.json('freeze-before-scoring.json',freeze);print(json.dumps({'stage':'260_predictions_frozen_before_scoring'}),flush=True)
        stage='2014-label-scoring';index=_pinned_json(source/'label-index.json',binding['file_pins']['label-index.json'])
        reader=LabelReader(source/'labels.jsonl',index,inputs,binding['file_pins']['labels.jsonl']);by_key={r['key']:r for r in inputs};scoring=[]
        support={'raw_nulls':0,'imputed_closure_positions':0,'newyear_true_zeros':0}
        for f in forecasts:
            inp=by_key[f['key']];label=reader.read_available(inp,'2014-12-31');modes=label_scenarios(inp,label)
            scoring.append({'forecast':f,'observed':modes['observed']['actual'],'assumed_missing_zero':modes['assumed_missing_zero']['actual'],'raw_actual':label['raw_actual']})
            support['raw_nulls']+=sum(v is None for v in label['raw_actual']);support['imputed_closure_positions']+=len(modes['imputed_positions'])
            support['newyear_true_zeros']+=f['origin']=='2014-01-01' and label['raw_actual'][0]==0
        files.json('scoring-labels.json',[{k:v for k,v in r.items() if k!='forecast'}|{'key':r['forecast']['key']} for r in scoring]);files.json('label-support.json',support)
        metrics=evaluate(scoring,guard.check);files.json('evaluation.json',metrics)
        if (metrics['all260']['observed']['candidate']['daily_support'],metrics['all260']['observed']['candidate']['complete_totals'])!=(3630,250):raise ValueError('observed support drift')
        if (metrics['all260']['assumed_missing_zero']['candidate']['daily_support'],metrics['all260']['assumed_missing_zero']['candidate']['complete_totals'])!=(3640,260) or support['newyear_true_zeros']!=10:raise ValueError('assumed support drift')
        if any(pin(output/n)!=p for n,p in freeze['states'].items()) or pin(output/'predictions-before-scoring.json')!=freeze['predictions_pin']:raise ValueError('frozen predictions changed')
        if {p:verify(Path(p)) for p in closures}!=closures or any(pin(REPO/p)!=v for p,v in pins.items()):raise ValueError('protected evidence changed')
        mandatory_pass=all(metrics[g][mode]['eligible'] for g in MANDATORY for mode in ('observed','assumed_missing_zero'))
        strict_improvement=mandatory_pass and all(F(metrics['all260'][mode]['paired_exact']['total_MSE'])<0 for mode in ('observed','assumed_missing_zero'))
        summary={'status':'complete','models':4,'supported_models':sum(s['supported'] for s in states),'zero_optimal_states':sum(s['supported'] and s['verification']['zero_beta'] for s in states),
            'changed_windows':sum(F(f['delta_total'])!=0 for f in forecasts),'input_fallback_windows':sum(f['features'] is None for f in forecasts),
            'mandatory_pass':mandatory_pass,'strict_total_improvement':strict_improvement,'new_2015_content_fit_predict_evaluate':False,
            'all_predictions_retained':True,'independent_validation':False,'adopted':False,'formal_permission':False,'resources':guard.check(),'seconds':time.monotonic()-started}
        files.json('summary.json',summary);status='complete';print(json.dumps(summary),flush=True)
    except BaseException as exc:
        save_failure(files,stage,exc,states,forecasts)
        raise
    finally:files.json('root-closed.json',{'status':status,'files':files.pins.copy(),'immutable':True,'formal_permission':False},True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);run(parser.parse_args().output.absolute())
