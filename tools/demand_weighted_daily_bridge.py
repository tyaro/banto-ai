"""Artificial-only fixed coefficient -> input-only daily bridge; no optimizer."""
import math
from datetime import date,timedelta
from fractions import Fraction as F
from demand_bounded_metrics import Arithmetic
from demand_input_boundary_v2 import INPUT_FIELDS,FIT,CUTS,POLICY,identity
from demand_weighted_problem_consumer import WEIGHTED,exact,transform_meta,quantity,total,add_all,pin_value
from demand_prefix_adapter import fixed_features
from demand_ordered_weight_v2 import encode_features,SCHEMA

STATE_FIELDS={'schema','source_quarter','cutoff','usable_from','beta','fit_performed'}

class BridgeFailure(ValueError):pass

def metadata(payload):
    exact(payload,{'schema','input','transforms','weighted','state'})
    if payload['schema']!='weighted-daily-artificial-request-v1':raise BridgeFailure('artificial request schema')
    inp=payload['input'];weighted=payload['weighted'];st=payload['state'];exact(inp,INPUT_FIELDS);exact(weighted,WEIGHTED);exact(st,STATE_FIELDS)
    o,targets,key=identity(inp['store'],inp['origin']);q=(o.month-1)//3+1
    if o.year!=2014 or inp['schema']!='demand-input-v1' or inp['key']!=key or inp['target_dates']!=targets or inp['policy_ref']!=POLICY:raise BridgeFailure('2014 input identity')
    if st['schema']!='fixed-artificial-coefficients-v1' or st['fit_performed'] is not False or type(st['source_quarter']) is not int or st['source_quarter']!=q or st['cutoff']!=CUTS[q-1] or st['usable_from']!=st['cutoff'] or st['usable_from']>inp['origin']:raise BridgeFailure('same issue quarter available artificial coefficients')
    transform_meta(payload['transforms'],inp['origin'])
    for field,n in (('past_dates',56),('past_available_at',56),('target_dates',14)):
        if type(inp[field]) is not list or len(inp[field])!=n or any(type(x) is not str for x in inp[field]):raise BridgeFailure('metadata arrays')
    dates=[str(o-timedelta(days=j)) for j in range(56,0,-1)]
    if dates[0]<'2013-01-01' or inp['past_dates']!=dates or inp['past_available_at']!=[str(date.fromisoformat(d)+timedelta(days=1)) for d in dates]:raise BridgeFailure('available past56 only')
    mask=[d[5:] not in ('01-01','12-25') for d in targets]
    if inp['assumed_open_mask']!=mask or any(type(b) is not bool for b in inp['assumed_open_mask']) or inp['operating_status']!='unknown':raise BridgeFailure('fixed mask unknown')
    p=weighted['state_pin']
    if type(p) is not dict or set(p)!={'bytes','sha256'} or type(p['bytes']) is not int or p['bytes']<=0 or type(p['sha256']) is not str or len(p['sha256'])!=64:raise BridgeFailure('encoder pin')
    if type(st['beta']) is not list or len(st['beta'])!=3 or any(type(x) is not str for x in st['beta']):raise BridgeFailure('three exact rational coefficient strings')
    return q

def forecast(payload,checkpoint=lambda:None):
    q=metadata(payload);a=Arithmetic(checkpoint);inp=payload['input'];t=payload['transforms'];weighted=payload['weighted'];st=payload['state']
    beta=list(map(a.value,st['beta'])) # Parse even if the eventual row is unsupported/r0/B0.
    for v in t['scales'].values():
        if quantity(v,a)<=0:raise BridgeFailure('positive scales')
    past=inp['past_values'];obs=inp['past_observed']
    if type(past) is not list or len(past)!=56 or type(obs) is not list or len(obs)!=56:raise BridgeFailure('raw past arrays')
    for v,b in zip(past,obs):
        quantity(v,a,True)
        if type(b) is not bool or b!=(v is not None):raise BridgeFailure('past observation flags')
    baseline=inp['matched_mean28'];B=total(baseline,a);mask=inp['assumed_open_mask'];weekdays={k:[] for k in range(7)}
    for d,v in zip(inp['past_dates'][-28:],past[-28:]):
        if v is not None:weekdays[date.fromisoformat(d).weekday()].append(v)
    if min(map(len,weekdays.values()))<3:raise BridgeFailure('old mean28 support')
    expected=[math.fsum(weekdays[date.fromisoformat(d).weekday()])/len(weekdays[date.fromisoformat(d).weekday()]) if op else 0. for d,op in zip(inp['target_dates'],mask)]
    if baseline!=expected:raise BridgeFailure('same mean28 exact binary64')
    scale=t['scales'][str(inp['store'])];unit=a.mul(14,quantity(scale,a));old,reasons=fixed_features(past[-14:],inp['past_dates'][-14:],baseline,mask,scale)
    supplied=weighted['old_features']
    if supplied is not None:
        if type(supplied) is not list or len(supplied)!=3 or any(type(v) not in (int,float) for v in supplied):raise BridgeFailure('old features')
        for v in supplied:a.value(v)
    if supplied!=old or weighted['old_reasons']!=reasons:raise BridgeFailure('old feature binding')
    history={'schema':SCHEMA,'origin':inp['origin'],'records':[{'date':d,'available_at':av,'value':v} for d,av,v in zip(inp['past_dates'],inp['past_available_at'],past)]}
    encoded=encode_features(history,old,checkpoint);state=encoded['state'];a.max_bits=max(a.max_bits,state['max_bits'])
    if weighted['r']!=state['r_stored'] or weighted['features_exact']!=encoded['features_exact'] or weighted['state_pin']!=pin_value(state):raise BridgeFailure('history r z state binding')
    z=None if old is None else list(map(a.value,encoded['features_exact']));dot=F() if z is None or B==0 else add_all((a.mul(x,b) for x,b in zip(z,beta)),a)
    rawP=a.add(B,a.mul(unit,dot));P=max(rawP,F());delta=a.sub(P,B);base_exact=[a.value(v) for v in baseline];E=add_all(base_exact,a)
    if delta==0 or z is None or B==0:
        daily=base_exact[:];display=baseline[:];branch='baseline_copy'
    elif P==0:
        daily=[F()]*14;display=[0.]*14;branch='floor_zero'
    else:
        if E<=0:raise BridgeFailure('positive allocation denominator')
        daily=[a.div(a.mul(b,P),E) for b in base_exact];branch='changed_proportional'
        try:display=list(map(float,daily))
        except OverflowError as e:raise BridgeFailure('finite display required') from e
    if any(x<0 or not op and x!=0 for x,op in zip(daily,mask)):raise BridgeFailure('masked nonnegative daily')
    if not all(math.isfinite(v) for v in display):raise BridgeFailure('finite daily display required')
    try:display_sum=math.fsum(display)
    except OverflowError as e:raise BridgeFailure('finite display sum required') from e
    if not math.isfinite(display_sum):raise BridgeFailure('finite display sum required')
    exact_sum=add_all(daily,a)
    if branch!='baseline_copy' and exact_sum!=P:raise BridgeFailure('changed exact total')
    checkpoint()
    return {'schema':'weighted-daily-artificial-forecast-v1','key':inp['key'],'store':inp['store'],'origin':inp['origin'],'cutoff':st['cutoff'],'source_quarter':q,
        'input_pin':pin_value(payload),'scale':scale,'unit':str(unit),'old_features':old,'feature_reasons':reasons,'r':state['r_stored'],'features_exact':None if z is None else list(map(str,z)),
        'encoder_state':state,'beta':list(map(str,beta)),'dot':str(dot),'raw_candidate_total':str(rawP),'floor_applied':rawP<0,
        'baseline':baseline[:],'baseline_total':str(B),'candidate_total':str(P),'delta_total':str(delta),'candidate_daily_exact':list(map(str,daily)),'candidate_display':display,
        'assumed_open_mask':mask[:],'operating_status':['unknown']*14,'allocation':{'branch':branch,'exact_baseline_sum':str(E),'canonical_baseline_minus_exact_sum':str(a.sub(B,E)),
        'exact_candidate_sum':str(exact_sum),'display_sum_minus_canonical':str(a.sub(a.value(display_sum),P))},
        'max_bits':a.max_bits,'fit_performed':False,'solve_called':False,'daily_bridge_artificial_only':True,'fit_ready':False,'can_launch_learning':False}
