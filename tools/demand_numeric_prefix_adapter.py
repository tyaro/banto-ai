"""Materialize only pinned, selected2013 rows for compile-only consumers."""
import copy,hashlib,json,re
from collections import Counter
from datetime import date,timedelta
from fractions import Fraction as F
from demand_input_boundary_v2 import FIT,CUTS,INPUT_FIELDS,LABEL_FIELDS,strict_json,validate_transforms,identity,DAY_ASSUMPTION
from demand_weighted_prefix_preflight import dummy_batch
from demand_weighted_problem_consumer import batch_meta,pair_meta,pin_value,quantity
from demand_bounded_metrics import Arithmetic

class PrefixFailure(ValueError):pass

def require(ok,why):
    if not ok:raise PrefixFailure(why)

def raw_pin(raw):return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def check_pin(p):require(type(p) is dict and set(p)=={'bytes','sha256'} and type(p['bytes']) is int and 0<p['bytes']<=8*1024**2 and type(p['sha256']) is str and re.fullmatch('[0-9a-f]{64}',p['sha256']),'bounded pin')

def metadata(manifest):
    require(type(manifest) is dict and set(manifest)=={'schema','sources','selections','transforms_meta','plans'},'manifest fields')
    require(manifest['schema']=='real2013-numeric-prefix-v1' and set(manifest['sources'])=={'inputs','encoded','labels','transforms'},'sources schema')
    for p in manifest['sources'].values():check_pin(p)
    selected=manifest['selections'];require(type(selected) is list and len(selected)==210,'exact selected210')
    bykey={};calendar={(s,str(date(2013,2,26)+timedelta(days=14*j))) for j in range(21) for s in FIT};seen=set();spans={k:[] for k in ('inputs','encoded','labels')}
    for row in selected:
        require(type(row) is dict and set(row)=={'input','encoded','index','quarter','cutoff'},'selection fields')
        inp=row['input']['metadata'];enc=row['encoded']['metadata'];ix=row['index'];o,targets,key=identity(inp['store'],inp['origin']);q=(o.month-1)//3+1
        require(o.year==2013 and (inp['store'],inp['origin']) in calendar and key==inp['key'] and key not in bykey,'2013 only unique fixed keys')
        require(row['quarter']==q and row['cutoff']==CUTS[q-1] and targets[-1]<row['cutoff'] and ix['available_at']==str(o+timedelta(days=14)) and ix['available_at']<=row['cutoff'],'selection cutoff')
        require(all(ix[k]==inp[k] for k in ('key','store','origin','target_dates')) and all(enc[k]==inp[k] for k in ('key','store','origin')),'metadata identity')
        for source in ('inputs','encoded'):
            span=row['input' if source=='inputs' else 'encoded']['source_span'];check_pin(span['pin']);start,end=span['start'],span['end']
            require(type(start) is int and type(end) is int and 0<=start<end<=manifest['sources'][source]['bytes'] and end-start==span['pin']['bytes']<=32768,'bounded selected span');spans[source].append((start,end))
        check_pin(ix['pin']);require(type(ix['offset']) is int and type(ix['length']) is int and 0<ix['length']==ix['pin']['bytes']<=32768 and 0<=ix['offset']<ix['offset']+ix['length']<=manifest['sources']['labels']['bytes'],'bounded label index')
        spans['labels'].append((ix['offset'],ix['offset']+ix['length']));bykey[key]=row;seen.add((inp['store'],inp['origin']))
    require(seen==calendar,'complete fixed2013 calendar')
    for source,intervals in spans.items():
        ordered=sorted(intervals);require(all(left[1]<=right[0] for left,right in zip(ordered,ordered[1:])),'overlapping selected spans '+source)
    plans=manifest['plans'];require(type(plans) is list and len(plans)==25,'25 fixed plans')
    expected={(q,None) for q in range(1,5)}|{((int(o[5:7])-1)//3+1,o) for s,o in calendar};identities=[]
    for plan in plans:
        q=plan['quarter'];cut=plan['cutoff'];excluded=plan['excluded_origin'];require(type(q) is int and q in range(1,5) and cut==CUTS[q-1],'plan cutoff')
        own=sorted((row for row in selected if row['quarter']==q and row['input']['metadata']['origin']!=excluded),key=lambda row:(row['input']['metadata']['origin'],row['input']['metadata']['store']))
        E=Counter(row['input']['metadata']['store'] for row in own if row['encoded']['metadata']['encoded']['old_eligible']);I=Counter(row['input']['metadata']['store'] for row in own);require(all(E[s] and I[s] for s in FIT),'missing original E I')
        members=[{'key':r['input']['metadata']['key'],'store':r['input']['metadata']['store'],'origin':r['input']['metadata']['origin'],'old_E':r['encoded']['metadata']['encoded']['old_eligible'],'objective_weight':str(F(1,10*E[r['input']['metadata']['store']])) if r['encoded']['metadata']['encoded']['old_eligible'] else '0','risk_weight':str(F(1,10*I[r['input']['metadata']['store']]))} for r in own]
        require(plan['members']==members and plan['nE']=={str(s):E[s] for s in FIT} and plan['nI']=={str(s):I[s] for s in FIT} and plan['objective_weight_sum']==plan['risk_weight_sum']=='1' and plan['consumer_batch_meta_passed'] is True,'preserved original membership weights')
        rows=[{'input':r['input']['metadata'],'encoded':r['encoded']['metadata'],'index':r['index']} for r in own]
        require(batch_meta(dummy_batch(cut,rows,manifest['transforms_meta'],excluded))==q,'metadata before decode')
        identities.append((q,excluded))
    require(len(set(identities))==25 and set(identities)==expected,'exact primary and delete plan names')
    return bykey

def materialize(manifest,buffers,checkpoint=lambda:None,progress=lambda event:None,decoder=strict_json):
    bykey=metadata(manifest) # All rows/plans before quantity JSON decoding.
    require(type(buffers) is dict and set(buffers)==set(manifest['sources']),'buffer names')
    for source,raw in buffers.items():require(type(raw) is bytes and raw_pin(raw)==manifest['sources'][source],'whole file pin '+source)
    spans={}
    for key,row in bykey.items():
        for source in ('inputs','encoded','labels'):
            meta=row['index'] if source=='labels' else row['input' if source=='inputs' else 'encoded']['source_span'];start=meta['offset'] if source=='labels' else meta['start'];end=start+meta['length'] if source=='labels' else meta['end'];raw=buffers[source][start:end]
            require(raw_pin(raw)==meta['pin'],'selected row pin '+source);spans[(source,key)]=raw
    progress({'event':'all_metadata_and_row_pins_checked','unique_rows':210,'pin_checked_spans':630})
    t=decoder(buffers['transforms']);validate_transforms(t);progress({'event':'transform_decoded','pin':manifest['sources']['transforms']})
    pairs={};states={};ledger=[];a=Arithmetic(checkpoint)
    for key,row in sorted(bykey.items(),key=lambda kv:(kv[1]['input']['metadata']['origin'],kv[1]['input']['metadata']['store'])):
        decoded={}
        for source in ('inputs','encoded','labels'):
            checkpoint();raw=spans[(source,key)];progress({'event':'before_row_decode','source':source,'key':key,'raw_pin':raw_pin(raw),'cutoff':row['cutoff']})
            decoded[source]=decoder(raw);ledger.append({'source':source,'key':key,'pin':raw_pin(raw),'cutoff':row['cutoff']})
        inp,enc,lab=(decoded[k] for k in ('inputs','encoded','labels'))
        progress({'event':'decoded_row_values','key':key,'input':inp,'encoded':enc,'label':lab})
        require(type(inp) is dict and set(inp)==INPUT_FIELDS and type(lab) is dict and set(lab)==LABEL_FIELDS,'strict input label fields')
        for field,value in row['input']['metadata'].items():
            if field not in ('past_values','past_observed','matched_mean28'):require(inp[field]==value,'input metadata unchanged')
        require(all(lab[f]==row['index'][f] for f in ('key','store','origin','target_dates','available_at')) and lab['schema']=='demand-label-v1' and lab['availability_basis']==DAY_ASSUMPTION,'label identity after pin')
        require(type(lab['raw_actual']) is list and len(lab['raw_actual'])==14 and type(lab['observed']) is list and len(lab['observed'])==14,'raw14 arrays')
        for value,observed in zip(lab['raw_actual'],lab['observed']):
            quantity(value,a);require(type(observed) is bool and observed is True,'complete raw observed14, no imputation')
        require(type(inp['past_values']) is list and len(inp['past_values'])==56 and type(inp['past_observed']) is list and len(inp['past_observed'])==56,'past56 quantity arrays')
        for value,observed in zip(inp['past_values'],inp['past_observed']):quantity(value,a,True);require(type(observed) is bool and observed==(value is not None),'past raw flags')
        require(all(enc[f]==inp[f] for f in ('key','store','origin','assumed_open_mask')) and enc['baseline']==inp['matched_mean28'] and enc['scale']==t['scales'][str(inp['store'])] and enc['transform_usable_from']=='2014-01-01','saved encoded input equality')
        require(enc['history']=={'schema':'ordered-weight-history-v1','origin':inp['origin'],'records':[{'date':d,'available_at':av,'value':v} for d,av,v in zip(inp['past_dates'],inp['past_available_at'],inp['past_values'])]},'saved raw history equality')
        state=enc['encoded']['state'];require(pin_value(state)==row['encoded']['metadata']['encoded']['state']['source_span']['pin'],'saved full state canonical pin')
        require(type(enc['encoded']['old_eligible']) is bool and enc['encoded']['old_eligible']==row['encoded']['metadata']['encoded']['old_eligible'] and enc['encoded']['old_eligible']==(enc['old_features'] is not None) and enc['encoded']['retain_old_objective_and_risk_denominators'] is True,'preserved E metadata')
        weighted={'old_features':enc['old_features'],'old_reasons':enc['old_reasons'],'r':state['r_stored'],'features_exact':enc['encoded']['features_exact'],'state_pin':pin_value(state)}
        pair={'input':inp,'label':lab,'weighted':weighted};pair_meta(pair,row['cutoff']);pairs[key]=pair;states[key]=enc
    require(len(ledger)==630 and len(pairs)==210,'exact unique decode scope')
    return {'transforms':t,'pairs':pairs,'saved_encoded':states,'decode_ledger':ledger,'quantity_label_imputation':False,'max_bits_raw_check':a.max_bits}

def make_batch(plan,materialized):
    batch={'schema':'demand-weighted-season-input-v1','cutoff':plan['cutoff'],'excluded_origin':plan['excluded_origin'],'transforms':materialized['transforms'],'rows':[materialized['pairs'][m['key']] for m in plan['members']]}
    # Fresh JSON drops references to buffers, index and source stores.
    return strict_json(json.dumps(batch,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode())
