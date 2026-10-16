"""Quantity-free provenance/time preflight. Calls only new consumer batch_meta."""
import copy,re
from collections import Counter
from datetime import date,timedelta
from fractions import Fraction as F
from demand_input_boundary_v2 import FIT,CUTS,POLICY,DAY_ASSUMPTION,identity
from demand_weighted_problem_consumer import batch_meta,WEIGHTED
HEX=re.compile(r'[0-9a-f]{64}')

class PreflightFailure(ValueError):pass
class OpaqueQuantity:
    def fail(self,*a,**k):raise AssertionError('metadata placeholder quantity access')
    __bool__=__float__=__int__=__iter__=__len__=__str__=__eq__=__getitem__=fail

def ensure(ok,message):
    if not ok:raise PreflightFailure(message)

def pin_metadata(p):ensure(type(p) is dict and set(p)=={'bytes','sha256'} and type(p['bytes']) is int and 0<p['bytes']<=8*1024**2 and type(p['sha256']) is str and HEX.fullmatch(p['sha256']),'pin metadata')

def dummy_batch(cutoff,rows,transforms,excluded):
    opaque=OpaqueQuantity();out=[]
    for row in rows:
        inp=copy.deepcopy(row['input']);enc=row['encoded'];idx=row['index']
        for k in ('past_values','past_observed','matched_mean28'):inp[k]=opaque
        label={k:copy.deepcopy(idx[k]) for k in ('key','store','origin','target_dates','available_at')};label.update(schema='demand-label-v1',availability_basis=DAY_ASSUMPTION,raw_actual=opaque,observed=opaque)
        weighted={k:opaque for k in WEIGHTED};weighted['state_pin']=enc['encoded']['state']['source_span']['pin']
        out.append({'input':inp,'label':label,'weighted':weighted})
    t=copy.deepcopy(transforms);t['scales']={s:opaque for s in t['scales']}
    return {'schema':'demand-weighted-season-input-v1','cutoff':cutoff,'excluded_origin':excluded,'transforms':t,'rows':out}

def audit(packet,checkpoint=lambda:None,progress=lambda event:None):
    ensure(type(packet) is dict and set(packet)=={'schema','inputs','encoded','transforms','index','availability','groups','binding','membership','lineage'},'packet fields')
    ensure(packet['schema']=='weighted-prefix-metadata-v1','metadata schema');inp_list=packet['inputs'];enc_map=packet['encoded'];t=packet['transforms'];idxs=packet['index'];ledger=packet['availability'];groups=packet['groups']
    ensure(type(inp_list) is list and len(inp_list)==470 and type(enc_map) is dict and len(enc_map)==470 and type(idxs) is list and len(idxs)==470,'full frozen metadata counts')
    ensure(t['schema']=='demand-transform-v1' and t['policy_ref']==POLICY and t['availability_basis']==DAY_ASSUMPTION and t['month_days']==['01-01','12-25'] and set(t['scales'])==set(map(str,FIT)) and all(x is None for x in t['scales'].values()),'fixed transform metadata')
    for prefix in ('scale','closure'):ensure(t[prefix+'_period']=={'start':'2013-01-01','end':'2013-12-31'} and t[prefix+'_usable_from']=='2014-01-01','transform2013 usable2014')
    inputs={p['metadata']['key']:p for p in inp_list};index={x['key']:x for x in idxs}
    ensure(len(inputs)==len(index)==470 and set(inputs)==set(index)==set(enc_map),'unique one-to-one keys')
    binding=packet['binding'];ensure(binding['schema']=='demand-input-label-binding-v1','binding schema')
    ensure(set(binding['keys'])==set(inputs) and len(binding['keys'])==470 and binding['historical_selection_not_prospective_population'] is True and binding['input_hash_excludes_label_pins'] is True and binding['availability_assumption']==DAY_ASSUMPTION,'prior binding flags')
    ensure(packet['membership']==ledger,'old availability lineage exact')
    ensure(set(ledger)==set(CUTS),'four cutoff ledgers');joined={};offset=0
    for ix in idxs:
        ensure(type(ix['offset']) is int and type(ix['length']) is int and ix['offset']==offset and 0<ix['length']<=32768,'contiguous bounded index');offset+=ix['length'];pin_metadata(ix['pin']);ensure(ix['pin']['bytes']==ix['length'],'index length pin')
    ensure(offset==binding['file_pins']['labels.jsonl']['bytes'],'label payload indexed size')
    lineage=packet['lineage'];ensure(set(lineage)=={'boundary','weighted','boundary_files','weighted_files','weighted_input_pins','weighted_freeze'},'lineage fields')
    for which in ('boundary','weighted'):ensure(lineage[which]['recorded_status']=='complete' and lineage[which]['integrity']=='passed','closed lineage')
    for name,p in binding['file_pins'].items():ensure(lineage['boundary_files'][name]==p,'boundary binding file pin')
    for name,p in lineage['weighted_input_pins'].items():ensure(lineage['boundary_files'][name]==p,'weighted original input pin')
    for field,name in (('encoded_rows','encoded-rows.json'),('groups','audit-groups.json'),('audit','support-audit.json')):ensure(lineage['weighted_freeze'][field]==lineage['weighted_files'][name],'weighted freeze file pin')
    historical=[]
    for key,item in inputs.items():
        checkpoint();inp=item['metadata'];encoded=enc_map[key]['metadata'];idx=index[key];o,targets,expectedkey=identity(inp['store'],inp['origin'])
        ensure(inp['schema']=='demand-input-v1' and inp['key']==expectedkey and inp['target_dates']==targets and inp['policy_ref']==POLICY,'input identity')
        ensure(inp['past_values'] is None and inp['past_observed'] is None and inp['matched_mean28'] is None,'quantity subtrees omitted')
        dates=[str(o-timedelta(days=j)) for j in range(56,0,-1)];available=[str(date.fromisoformat(d)+timedelta(days=1)) for d in dates]
        ensure(dates[0]>='2013-01-01' and inp['past_dates']==dates and inp['past_available_at']==available,'past56 and next-day')
        ensure(inp['assumed_open_mask']==[d[5:] not in ('01-01','12-25') for d in targets] and all(type(x) is bool for x in inp['assumed_open_mask']) and inp['operating_status']=='unknown','mask unknown')
        ensure(all(idx[k]==inp[k] for k in ('key','store','origin','target_dates')) and idx['available_at']==str(o+timedelta(days=14)),'label index identity availability')
        ensure(all(encoded[k]==inp[k] for k in ('key','store','origin')) and encoded['assumed_open_mask']==inp['assumed_open_mask'] and encoded['transform_usable_from']=='2014-01-01','encoded identity')
        history=encoded['history'];ensure(history['schema']=='ordered-weight-history-v1' and history['origin']==inp['origin'] and len(history['records'])==56,'history metadata')
        ensure(history['records']==[{'date':d,'available_at':av,'value':None} for d,av in zip(dates,available)],'saved history dates available')
        st=encoded['encoded']['state'];sm=st['metadata'];pin_metadata(sm['input_pin']);pin_metadata(st['source_span']['pin']);pin_metadata(item['source_span']['pin']);pin_metadata(enc_map[key]['source_span']['pin'])
        ensure(sm['schema']=='ordered-weight-state-v1' and sm['origin']==inp['origin'] and sm['past_start']==dates[0] and sm['past_end']==dates[-1] and sm['availability']=='next_calendar_day' and sm['tau']=='1/20' and sm['precision_bits_absolute']==32 and sm['rounding']=='nearest_ties_even','fixed encoder state metadata')
        ensure(encoded['encoded']['retain_old_objective_and_risk_denominators'] is True and type(encoded['encoded']['old_eligible']) is bool and type(encoded['old_reasons']) is list,'old eligibility metadata')
        ensure(all(encoded[k] is None for k in ('old_features','baseline','scale')) and encoded['encoded']['features_exact'] is None,'encoded quantities omitted')
        joined[key]={'input':inp,'encoded':encoded,'index':idx,'input_span':item['source_span'],'encoded_span':enc_map[key]['source_span']}
        progress({'event':'joined','key':key})
        if o.year==2013:historical.append((inp['store'],inp['origin']))
    calendar={(s,str(date(2013,2,26)+timedelta(days=14*j))) for j in range(21) for s in FIT}
    ensure(set(historical)==calendar and len(historical)==210 and {tuple(x) for x in binding['archived_2013_keys']}==calendar and len(binding['archived_2013_keys'])==210,'exact archived calendar')
    groupmap={g['name']:g for g in groups};ensure(len(groupmap)==len(groups)==16,'unique saved audit groups');result=[];plans=[]
    issue_calendar={(s,str(date(2014,1,1)+timedelta(days=14*j))) for j in range(26) for s in FIT}
    issue=[row for row in joined.values() if row['input']['origin'].startswith('2014-')]
    ensure({(row['input']['store'],row['input']['origin']) for row in issue}==issue_calendar and len(issue)==260,'exact input-only2014 issue calendar')
    issue_subsets={'issue_all260':(issue,None),'issue_normal250':([row for row in issue if row['input']['origin']!='2014-01-01'],None),'issue_newyear10':([row for row in issue if row['input']['origin']=='2014-01-01'],None),'issue_yearend':([row for row in issue if row['input']['origin'].startswith('2014-12-')],None)}
    for q in range(1,5):
        same=[row for row in issue if (int(row['input']['origin'][5:7])-1)//3+1==q];issue_subsets['issue_Q'+str(q)+'_all']=(same,q);issue_subsets['issue_Q'+str(q)+'_normal']=([row for row in same if row['input']['origin']!='2014-01-01'],q)
    ensure(set(groupmap)==set(issue_subsets)|{'train_Q'+str(q) for q in range(1,5)},'all16 group names')
    for name,(rows,q) in issue_subsets.items():
        E=Counter(row['input']['store'] for row in rows if row['encoded']['encoded']['old_eligible']);expected=[]
        for row in sorted(rows,key=lambda row:(row['input']['origin'],row['input']['store'])):
            inp=row['input'];eligible=row['encoded']['encoded']['old_eligible'];expected.append({'key':inp['key'],'store':inp['store'],'origin':inp['origin'],'old_E':eligible,'objective_weight':str(F(1,10*E[inp['store']])) if eligible else '0','risk_weight':None})
        ensure(groupmap[name]=={'name':name,'kind':'issue','quarter':q,'cutoff':None,'I_provenance':'unknown_no_labels_decoded','members':expected},'old issue group metadata '+name)
    for q,cutoff in enumerate(CUTS,1):
        checkpoint();l=ledger[cutoff];accepted=l['accepted_keys'];excluded=l['excluded']
        ensure(l['cutoff']==cutoff and l['model_fit_performed'] is False and len(set(accepted))==len(accepted) and accepted==l['decoded_keys'],'trusted old accepted/decoded')
        ensure(set(accepted).isdisjoint(x['key'] for x in excluded) and len({x['key'] for x in excluded})==len(excluded) and set(accepted)|{x['key'] for x in excluded}==set(inputs),'full accepted excluded partition')
        for key in accepted:ensure(joined[key]['index']['available_at']<=cutoff and joined[key]['input']['target_dates'][-1]<cutoff,'accepted label timing')
        selected=sorted((joined[key] for key in accepted if joined[key]['input']['origin'].startswith('2013-') and (int(joined[key]['input']['origin'][5:7])-1)//3+1==q),key=lambda row:(row['input']['origin'],row['input']['store']))
        expected={(s,o) for s,o in calendar if (int(o[5:7])-1)//3+1==q};ensure({(row['input']['store'],row['input']['origin']) for row in selected}==expected and len(selected)==len(expected),'own Q complete FIT10')
        old=groupmap['train_Q'+str(q)];ensure(old['kind']=='historical' and old['quarter']==q and old['cutoff']==cutoff and old['I_provenance']=='pinned_prior_accepted_keys','old group identity')
        members=old['members'];ensure(len(members)==len(selected) and [m['key'] for m in members]==[row['input']['key'] for row in selected],'same old membership order')
        def group_plan(rows,excluded_origin):
            E=Counter(row['input']['store'] for row in rows if row['encoded']['encoded']['old_eligible']);I=Counter(row['input']['store'] for row in rows);ensure(all(E[s] and I[s] for s in FIT),'all original E I stores')
            mm=[{'key':row['input']['key'],'store':row['input']['store'],'origin':row['input']['origin'],'old_E':row['encoded']['encoded']['old_eligible'],'objective_weight':str(F(1,10*E[row['input']['store']])) if row['encoded']['encoded']['old_eligible'] else '0','risk_weight':str(F(1,10*I[row['input']['store']]))} for row in rows]
            if excluded_origin is None:ensure(mm==members,'old E I w v unchanged')
            batch=dummy_batch(cutoff,rows,t,excluded_origin);ensure(batch_meta(batch)==q,'new consumer metadata')
            # Only bounded calendar counts enter this arithmetic (10 stores, <=470 rows).
            objective_sum=sum((F(E[s],10*E[s]) for s in FIT),F());risk_sum=sum((F(I[s],10*I[s]) for s in FIT),F())
            ensure(objective_sum==risk_sum==1,'metadata weight sums')
            plan={'quarter':q,'cutoff':cutoff,'excluded_origin':excluded_origin,'members':mm,'nE':{str(s):E[s] for s in FIT},'nI':{str(s):I[s] for s in FIT},'objective_weight_sum':str(objective_sum),'risk_weight_sum':str(risk_sum),'consumer_batch_meta_passed':True}
            progress({'event':'metadata_plan','value':plan})
            return plan
        primary=group_plan(selected,None);result.append(primary)
        for origin in sorted({row['input']['origin'] for row in selected}):plans.append(group_plan([row for row in selected if row['input']['origin']!=origin],origin))
    return {'status':'passed','scope':'metadata_only','metadata_inputs':470,'primary_rows':sum(len(q['members']) for q in result),'primary':result,'deletion_metadata_plans':plans,'consumer_metadata_payloads':len(result)+len(plans),'new_label_quantity_decode':False,'new_x_r_z':False,'quantity_payload_materialized':False,'consumer_compile_executed':False,'new_fit':False,'solve_calls':0,'new_predictions':False,'new_scores':False,'new2015':False,'fit_ready':False,'can_launch_learning':False}
