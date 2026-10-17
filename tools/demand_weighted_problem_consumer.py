"""Compile a concrete weighted season problem; never import/call an optimizer.

Only artificial invocation is authorized by the 2026-10-15 consumer contract.
"""
import hashlib
import json
import math
from collections import Counter
from datetime import date,timedelta
from fractions import Fraction as F

from demand_bounded_metrics import Arithmetic,atoms
from demand_input_boundary_v2 import (FIT,CUTS,POLICY,DAY_ASSUMPTION,INPUT_FIELDS,LABEL_FIELDS,TRANSFORM_FIELDS,identity)
from demand_prefix_adapter import fixed_features
from demand_ordered_weight_v2 import encode_features,SCHEMA

WEIGHTED={'old_features','old_reasons','r','features_exact','state_pin'}

class ConsumerFailure(ValueError):pass

def exact(obj,fields):
    if type(obj) is not dict or set(obj)!=set(fields):raise ConsumerFailure('strict_fields')

def pin_value(value):
    raw=json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

def transform_meta(t,cutoff):
    exact(t,TRANSFORM_FIELDS)
    if t['schema']!='demand-transform-v1' or t['policy_ref']!=POLICY or t['availability_basis']!=DAY_ASSUMPTION:raise ConsumerFailure('transform_policy')
    if type(t['scales']) is not dict or set(t['scales'])!=set(map(str,FIT)):raise ConsumerFailure('scale_keys')
    for prefix in ('scale','closure'):
        if t[prefix+'_period']!={'start':'2013-01-01','end':'2013-12-31'} or t[prefix+'_usable_from']!='2014-01-01' or t[prefix+'_usable_from']>cutoff:raise ConsumerFailure('transform_availability')
    if t['month_days']!=['01-01','12-25']:raise ConsumerFailure('closure_policy')

def pair_meta(pair,cutoff):
    """No quantity/features/weight values are read in this phase."""
    exact(pair,{'input','label','weighted'});inp=pair['input'];lab=pair['label'];exact(inp,INPUT_FIELDS);exact(lab,LABEL_FIELDS);exact(pair['weighted'],WEIGHTED)
    for values,n in ((inp['target_dates'],14),(lab['target_dates'],14),(inp['past_dates'],56),(inp['past_available_at'],56)):
        if type(values) is not list or len(values)!=n or any(type(v) is not str for v in values):raise ConsumerFailure('ISO_metadata_arrays')
    if type(lab['available_at']) is not str:raise ConsumerFailure('ISO_label_availability')
    p=pair['weighted']['state_pin']
    if type(p) is not dict or set(p)!={'bytes','sha256'} or type(p['bytes']) is not int or p['bytes']<=0 or type(p['sha256']) is not str or len(p['sha256'])!=64:raise ConsumerFailure('encoder_pin_metadata')
    o,targets,key=identity(inp['store'],inp['origin'])
    if inp['schema']!='demand-input-v1' or inp['key']!=key or inp['target_dates']!=targets or inp['policy_ref']!=POLICY:raise ConsumerFailure('input_identity')
    if lab['schema']!='demand-label-v1' or any(lab[k]!=inp[k] for k in ('key','store','origin','target_dates')) or lab['availability_basis']!=DAY_ASSUMPTION:raise ConsumerFailure('label_identity')
    available=str(o+timedelta(days=14))
    if lab['available_at']!=available or available>cutoff or targets[-1]>=cutoff or cutoff>='2015-01-01':raise ConsumerFailure('label_cutoff')
    past=[str(o-timedelta(days=j)) for j in range(56,0,-1)]
    if past[0]<'2013-01-01' or inp['past_dates']!=past or inp['past_available_at']!=[str(date.fromisoformat(dt)+timedelta(days=1)) for dt in past]:raise ConsumerFailure('past_grid_availability')
    mask=[dt[5:] not in ('01-01','12-25') for dt in targets]
    if inp['assumed_open_mask']!=mask or any(type(v) is not bool for v in inp['assumed_open_mask']) or inp['operating_status']!='unknown':raise ConsumerFailure('fixed_mask_unknown')

def batch_meta(batch):
    exact(batch,{'schema','cutoff','excluded_origin','transforms','rows'})
    if batch['schema']!='demand-weighted-season-input-v1' or type(batch['cutoff']) is not str or batch['cutoff'] not in CUTS:raise ConsumerFailure('fixed_2014_cutoff')
    cutoff=batch['cutoff'];q=CUTS.index(cutoff)+1;transform_meta(batch['transforms'],cutoff)
    origins=[str(date(2013,2,26)+timedelta(days=14*j)) for j in range(21) if ((date(2013,2,26)+timedelta(days=14*j)).month-1)//3+1==q]
    excluded=batch['excluded_origin']
    if excluded is not None and (type(excluded) is not str or excluded not in origins):raise ConsumerFailure('excluded_origin')
    expected={(s,dt) for dt in origins if dt!=excluded for s in FIT}
    rows=batch['rows']
    if type(rows) is not list or not 0<len(rows)<=512 or len(rows)!=len(expected):raise ConsumerFailure('season_row_count')
    pairs=[]
    for row in rows:
        pair_meta(row,cutoff);inp=row['input'];pair=(inp['store'],inp['origin'])
        if pair not in expected:raise ConsumerFailure('own_season_only')
        pairs.append(pair)
    if len(set(pairs))!=len(pairs) or set(pairs)!=expected:raise ConsumerFailure('complete_FIT10_calendar')
    return q

def quantity(v,a,missing=False):
    if v is None and missing:return None
    if type(v) not in (int,float):raise ConsumerFailure('finite_raw_int_float')
    x=a.value(v)
    if x<0:raise ConsumerFailure('negative_quantity')
    return x

def total(values,a):
    if type(values) is not list or len(values)!=14:raise ConsumerFailure('fourteen_days')
    for v in values:quantity(v,a)
    try:result=math.fsum(values)
    except OverflowError as e:raise ConsumerFailure('canonical_total_overflow') from e
    return a.value(result)

def add_all(values,a):
    result=F()
    for v in values:result=a.add(result,v)
    return result

def row_numbers(pair,t,a,complete):
    inp=pair['input'];lab=pair['label'];weighted=pair['weighted'];past=inp['past_values'];flags=inp['past_observed'];raw=lab['raw_actual'];observed=lab['observed']
    if type(past) is not list or len(past)!=56 or type(flags) is not list or len(flags)!=56:raise ConsumerFailure('past_arrays')
    for v,flag in zip(past,flags):
        quantity(v,a,True)
        if type(flag) is not bool or flag!=(v is not None):raise ConsumerFailure('past_observation')
    if type(raw) is not list or len(raw)!=14 or type(observed) is not list or len(observed)!=14:raise ConsumerFailure('label_arrays')
    for v,flag in zip(raw,observed):
        quantity(v,a,True)
        if type(flag) is not bool or flag!=(v is not None):raise ConsumerFailure('label_observation')
    if complete and None in raw:raise ConsumerFailure('training_raw_incomplete')
    baseline=inp['matched_mean28'];B=total(baseline,a);scale=t['scales'][str(inp['store'])];u=quantity(scale,a)
    if u<=0:raise ConsumerFailure('positive_scale')
    days={j:[] for j in range(7)}
    for dt,v in zip(inp['past_dates'][-28:],past[-28:]):
        if v is not None:days[date.fromisoformat(dt).weekday()].append(v)
    if min(map(len,days.values()))<3:raise ConsumerFailure('old_mean28_support')
    expected=[math.fsum(days[date.fromisoformat(dt).weekday()])/len(days[date.fromisoformat(dt).weekday()]) if op else 0. for dt,op in zip(inp['target_dates'],inp['assumed_open_mask'])]
    if baseline!=expected:raise ConsumerFailure('same_mean28_exact_binary64')
    x,reasons=fixed_features(past[-14:],inp['past_dates'][-14:],baseline,inp['assumed_open_mask'],scale)
    supplied=weighted['old_features']
    if supplied is not None:
        if type(supplied) is not list or len(supplied)!=3 or any(type(v) not in (int,float) for v in supplied):raise ConsumerFailure('old_feature_types')
        for v in supplied:a.value(v)
    if supplied!=x or weighted['old_reasons']!=reasons:raise ConsumerFailure('old_feature_consistency')
    packet={'schema':SCHEMA,'origin':inp['origin'],'records':[{'date':d,'available_at':av,'value':v} for d,av,v in zip(inp['past_dates'],inp['past_available_at'],past)]}
    encoded=encode_features(packet,x,a.checkpoint);state=encoded['state']
    if weighted['r']!=state['r_stored'] or weighted['features_exact']!=encoded['features_exact'] or weighted['state_pin']!=pin_value(state):raise ConsumerFailure('weighted_history_binding')
    a.max_bits=max(a.max_bits,state['max_bits'])
    z=None if x is None or B==0 else list(map(a.value,encoded['features_exact']))
    return {'B':B,'Y':None if None in raw else total(raw,a),'unit':a.mul(14,u),'z':z,'old_E':x is not None and B>0,
            'r':state['r_stored'],'old_reasons':reasons,'state_pin':pin_value(state)}

def hinge_facet(problem,side,selected,arithmetic=None):
    a=arithmetic or Arithmetic()
    if type(side) is not int or side not in (-1,1) or type(selected) is not list or any(type(k) is not str for k in selected) or len(set(selected))!=len(selected):raise ConsumerFailure('facet_subset')
    rows=problem['rows'];bykey={row['key']:row for row in rows}
    if not set(selected)<=set(bykey):raise ConsumerFailure('facet_unknown_key')
    rhs=F();linear=[F()]*3;offset=F()
    for row in rows:
        B,Y,unit,v=map(a.value,(row['B'],row['Y'],row['unit'],row['risk_weight']));e=a.sub(B,Y);rhs=a.add(rhs,a.mul(v,max(a.mul(side,e),F())))
        if row['key'] in set(selected):
            offset=a.add(offset,a.mul(v,a.mul(side,e)))
            z=[F()]*3 if row['x'] is None else list(map(a.value,row['x']))
            for j in range(3):linear[j]=a.add(linear[j],a.mul(a.mul(v,side),a.mul(unit,z[j])))
    bound=a.sub(rhs,offset)
    if bound<0:raise AssertionError('baseline facet feasibility')
    return {'side':side,'selected':sorted(selected),'normal':list(map(str,linear)),'bound':str(bound),'beta0_slack':str(bound)}

def compile_problem(batch,checkpoint=lambda:None):
    q=batch_meta(batch);a=Arithmetic(checkpoint)
    # Numeric access starts only after every row has passed metadata validation.
    for value in batch['transforms']['scales'].values():
        if quantity(value,a)<=0:raise ConsumerFailure('positive_scale')
    parsed=[row_numbers(pair,batch['transforms'],a,True) for pair in batch['rows']]
    E=Counter(pair['input']['store'] for pair,row in zip(batch['rows'],parsed) if row['old_E']);I=Counter(pair['input']['store'] for pair in batch['rows'])
    if not all(E[s] and I[s] for s in FIT):raise ConsumerFailure('missing_original_E_or_I_store')
    problem={'rows':[]};ledger=[];G=[[F(i==j) for j in range(3)] for i in range(3)];rhs=[F()]*3;C=F();derived=[];under=over=F();zero=[];normals=[]
    beta0=[F()]*3;paired_under=paired_over=F();slacks=[]
    for pair,row in zip(batch['rows'],parsed):
        checkpoint();inp=pair['input'];key=inp['key'];s=inp['store'];w=F(1,10*E[s]) if row['old_E'] else F();v=F(1,10*I[s]);B,Y,unit,z=(row[k] for k in ('B','Y','unit','z'));target=a.div(a.sub(Y,B),unit);e=a.sub(B,Y)
        h=[F()]*3 if z is None else [a.mul(unit,x) for x in z]
        problem['rows'].append({'key':key,'quarter':q,'B':str(B),'Y':str(Y),'unit':str(unit),'x':None if z is None else list(map(str,z)),'fit_weight':str(w),'risk_weight':str(v)})
        ledger.append({'key':key,'store':s,'origin':inp['origin'],'old_E':row['old_E'],'nE':E[s],'nI':I[s],'r':row['r'],'state_pin':row['state_pin'],'old_reasons':row['old_reasons']})
        if z is not None:
            C=a.add(C,a.mul(w,a.square(target)))
            for j in range(3):
                rhs[j]=a.add(rhs[j],a.mul(w,a.mul(z[j],target)))
                for k in range(3):G[j][k]=a.add(G[j][k],a.mul(w,a.mul(z[j],z[k])))
        uerr=max(-e,F());oerr=max(e,F());under=a.add(under,a.mul(v,uerr));over=a.add(over,a.mul(v,oerr))
        derived.append({'key':key,'target':str(target),'e':str(e),'h':list(map(str,h)),'baseline_under':str(uerr),'baseline_over':str(oerr)})
        normal=[-x for x in h];slack=a.sub(B,add_all((a.mul(x,b) for x,b in zip(normal,beta0)),a));slacks.append(slack)
        normals.append({'key':key,'normal':list(map(str,normal)),'bound':str(B),'beta0_slack':str(slack)})
        P=a.add(B,add_all((a.mul(x,b) for x,b in zip(h,beta0)),a));pe=a.sub(P,Y)
        du=a.sub(max(-pe,F()),uerr);do=a.sub(max(pe,F()),oerr)
        paired_under=a.add(paired_under,a.mul(v,du));paired_over=a.add(paired_over,a.mul(v,do))
        daily=[a.value(x) for x in inp['matched_mean28']];exact_sum=add_all(daily,a)
        zero.append({'key':key,'point_total':str(P),'baseline_canonical_total':str(B),'daily_display_copy':list(inp['matched_mean28']),
            'daily_exact_copy':list(map(str,daily)),'daily_exact_sum':str(exact_sum),'canonical_minus_exact_sum':str(a.sub(B,exact_sum)),
            'paired_under':str(du),'paired_over':str(do),'nonnegative':P>=0})
    if add_all((a.value(row['fit_weight']) for row in problem['rows']),a)!=1 or add_all((a.value(row['risk_weight']) for row in problem['rows']),a)!=1:raise AssertionError('own-quarter weights sum one')
    facets=[]
    for side in (-1,1):
        selected=[row['key'] for row in problem['rows'] if a.mul(side,a.sub(a.value(row['B']),a.value(row['Y'])))>0]
        facets.append(hinge_facet(problem,side,selected,a))
    penalty=add_all((a.square(b) for b in beta0),a)
    quadratic=add_all((a.mul(a.mul(beta0[j],G[j][k]),beta0[k]) for j in range(3) for k in range(3)),a)
    J=a.add(a.sub(quadratic,a.mul(2,add_all((a.mul(x,b) for x,b in zip(rhs,beta0)),a))),C)
    feasible=all(x>=0 for x in slacks) and paired_under<=0 and paired_over<=0 and all(a.value(f['beta0_slack'])>=0 for f in facets)
    if not feasible or J!=C or paired_under!=0 or paired_over!=0 or any(row['point_total']!=row['baseline_canonical_total'] for row in zero):raise AssertionError('beta0 substitution')
    return {'schema':'compiled-weighted-season-problem-v1','cutoff':batch['cutoff'],'quarter':q,'input_pin':pin_value(batch),
        'problem':problem,'ledger':ledger,'nE':{str(s):E[s] for s in FIT},'nI':{str(s):I[s] for s in FIT},
        'lambda':'1','objective_convention':'J=beta^T G beta-2 rhs^T beta+C','objective':{'G':[[str(x) for x in row] for row in G],'rhs':list(map(str,rhs)),'C':str(C)},
        'derived_rows':derived,'nonnegative_constraints':normals,'hinge_spec':{'baseline_under':str(under),'baseline_over':str(over),'original_complete_I':True,'beta0_supporting_facets':facets,'facets_are_not_complete_hinge_representation':True},
        'beta0_witness':{'point':list(map(str,beta0)),'objective_J':str(J),'ridge_penalty':str(penalty),'paired_under':str(paired_under),'paired_over':str(paired_over),'rows':zero,'feasible':feasible,'optimality_claim':False},
        'max_bits':a.max_bits,'solve_called':False,'consumer_artificial_ready_only':True,'fit_ready':False,'can_launch_learning':False}

def beta_zero_replay(pair,t,checkpoint=lambda:None):
    """Artificial scenario check, never a training-label imputation path."""
    cutoff=pair['label']['available_at'];transform_meta(t,cutoff);pair_meta(pair,cutoff)
    a=Arithmetic(checkpoint);row=row_numbers(pair,t,a,False);inp=pair['input'];raw=list(pair['label']['raw_actual']);mask=inp['assumed_open_mask'];B=row['B']
    f={'scale':t['scales'][str(inp['store'])],'baseline':list(inp['matched_mean28']),'candidate_daily_exact':[str(a.value(x)) for x in inp['matched_mean28']],
        'baseline_total':str(B),'candidate_total':str(B),'assumed_open_mask':list(mask)}
    scenarios={}
    for mode,ys in [('observed',raw),('assumed_missing_zero',[0. if x is None and not op else x for x,op in zip(raw,mask)])]:
        losses=atoms(f,ys,a)
        if any(b!=c for values in losses.values() for b,c in values):raise AssertionError('beta0 replay changed baseline loss')
        scenarios[mode]={'actual':ys,'raw_actual':raw[:],'daily_n':len(losses['daily_MSE']),'quantity_n':len(losses['quantity_MSE']),
            'complete_total_n':len(losses['total_MSE']),'loss_pairs':{key:[[str(b),str(c)] for b,c in values] for key,values in losses.items()}}
    return {'baseline_copy':f,'scenarios':scenarios,'imputed_positions':[j for j,(x,op) in enumerate(zip(raw,mask)) if x is None and not op],
        'max_bits':a.max_bits,'training_label_imputed':False,'solve_called':False}
