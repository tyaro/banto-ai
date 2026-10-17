"""Materialize permitted rows and fixed input-only features; no regression or score."""
import copy
import datetime as dt
import math
from demand_input_boundary_v2 import (FIT,CUTS,day,exact,quantity,canonical,strict_json,validate_input,validate_transforms,input_readiness,fit_prefix,load_inputs,load_transforms,identity)
FEATURE_SPEC='common-signed-level-week-v1'
ROW_FIELDS={'key','store','origin','target_dates','label_available_at','raw_actual','baseline','assumed_open_mask','past14_dates','past14_values','scale','transform_usable_from','features','reasons'}


def fixed_features(past14,dates,baseline,mask,scale):
    if type(past14) is not list or len(past14)!=14 or len(dates)!=14 or len(baseline)!=14 or len(mask)!=14:raise ValueError('fixed feature arrays required')
    quantity(scale)
    if scale<=0:raise ValueError('positive scale')
    for v in past14:quantity(v,True)
    for v in baseline:quantity(v)
    reasons=[];total=math.fsum(baseline)
    if None in past14:reasons.append('past14_missing')
    if any(d[5:] in ('01-01','12-25') for d in dates):reasons.append('past14_assumed_closure')
    if total<=0:reasons.append('zero_baseline_total')
    if reasons:return None,reasons
    latest=past14[7:];previous=past14[:7]
    replay=math.fsum(latest[j%7] for j,good in enumerate(mask) if good)
    x=[1.,(replay-total)/(14*scale),2*(math.fsum(latest)-math.fsum(previous))/(14*scale)]
    if not all(math.isfinite(v) for v in x):raise ValueError('nonfinite feature')
    return x,[]


def input_features(row,t):
    validate_input(row);validate_transforms(t)
    return fixed_features(row['past_values'][-14:],row['past_dates'][-14:],row['matched_mean28'],row['assumed_open_mask'],t['scales'][str(row['store'])])


def materialize(inputs,t,reader,cutoff):
    ledger=fit_prefix(inputs,t,reader,cutoff);allowed=set(ledger['accepted_keys']);rows=[]
    for r in inputs:
        if r['key'] not in allowed:continue
        # Reader still enforces the cutoff. No external reader/path/reference enters output.
        label=reader.read_available(r,cutoff);x,reasons=input_features(r,t)
        rows.append({'key':r['key'],'store':r['store'],'origin':r['origin'],'target_dates':list(r['target_dates']),
            'label_available_at':label['available_at'],'raw_actual':list(label['raw_actual']),'baseline':list(r['matched_mean28']),
            'assumed_open_mask':list(r['assumed_open_mask']),'past14_dates':list(r['past_dates'][-14:]),'past14_values':list(r['past_values'][-14:]),
            'scale':t['scales'][str(r['store'])],'transform_usable_from':max(t['scale_usable_from'],t['closure_usable_from']),'features':x,'reasons':reasons})
    batch={'schema':'demand-permitted-prefix-v1','cutoff':cutoff,'feature_spec':FEATURE_SPEC,'rows':rows}
    validate_batch(batch)
    return batch,ledger


def validate_batch(batch):
    exact(batch,{'schema','cutoff','feature_spec','rows'})
    if batch['schema']!='demand-permitted-prefix-v1' or batch['cutoff'] not in CUTS or batch['feature_spec']!=FEATURE_SPEC or type(batch['rows']) is not list:raise ValueError('prefix schema/cutoff required')
    at=day(batch['cutoff']);seen=set()
    for r in batch['rows']:
        exact(r,ROW_FIELDS);o=day(r['origin'])
        if type(r['store']) is not int or r['store'] not in FIT or not dt.date(2013,1,1)<=o<at or r['key'] in seen:raise ValueError('past unique FIT input required')
        if identity(r['store'],r['origin'])[2]!=r['key']:raise ValueError('prefix identity mismatch')
        targets=[str(o+dt.timedelta(days=j)) for j in range(14)];past=[str(o-dt.timedelta(days=k)) for k in range(14,0,-1)]
        if r['target_dates']!=targets or day(targets[-1])>=at or r['label_available_at']!=str(o+dt.timedelta(days=14)) or day(r['label_available_at'])>at:raise ValueError('label outside permitted cutoff')
        if r['past14_dates']!=past or r['transform_usable_from']!='2014-01-01' or day(r['transform_usable_from'])>at:raise ValueError('context or transform cutoff mismatch')
        if r['assumed_open_mask']!=[d[5:] not in ('01-01','12-25') for d in targets] or any(type(v) is not bool for v in r['assumed_open_mask']):raise ValueError('fixed assumed mask required')
        if any(not good and v!=0. for good,v in zip(r['assumed_open_mask'],r['baseline'])):raise ValueError('closed baseline must be zero')
        if r['features'] is not None and (type(r['features']) is not list or len(r['features'])!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in r['features'])):raise ValueError('finite feature vector required')
        if len(r['raw_actual'])!=14:raise ValueError('real label14 required')
        for value in r['raw_actual']:quantity(value)
        x,reasons=fixed_features(r['past14_values'],past,r['baseline'],r['assumed_open_mask'],r['scale'])
        if x!=r['features'] or reasons!=r['reasons']:raise ValueError('feature/context consistency mismatch')
        seen.add(r['key'])
    return batch


def deliver(batch,consumer):
    validate_batch(batch)
    # JSON round trip breaks references to parent rows. This is an API boundary, not a sandbox.
    return consumer(strict_json(canonical(batch)))


def feature_support(batch):
    validate_batch(batch)
    rr=batch['rows'];eligible=[r for r in rr if r['features'] is not None]
    from collections import Counter
    return {'complete_rows':len(rr),'eligible_rows':len(eligible),'eligible_stores':sorted({r['store'] for r in eligible}),
        'eligible_origins':sorted({r['origin'] for r in eligible}),'store_quarter_counts':{f'{s}/Q{q}':sum(r['store']==s and (int(r['origin'][5:7])-1)//3+1==q for r in eligible) for s in FIT for q in range(1,5)},
        'reasons':dict(Counter(reason for r in rr for reason in r['reasons'])),
        'feature_min':[min((r['features'][j] for r in eligible),default=None) for j in range(3)],
        'feature_max':[max((r['features'][j] for r in eligible),default=None) for j in range(3)],
        'features_share_same_context':True,'independent_sample_size_claim':False,'target_values_used_for_support':False}
