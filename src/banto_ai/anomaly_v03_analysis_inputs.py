"""Join authenticated dev/smoke summaries without rereading evaluation payloads.

The public IO entry point anchors compact prior results in an external digest.
Pure join_inputs validates identities, counts and additivity but authenticates
no bytes. Neither entry computes bootstrap intervals, gates or a formal report.
"""
from __future__ import annotations

import copy
from pathlib import Path

from . import anomaly_v03 as registry
from . import anomaly_v03_inference_audit as arithmetic
from . import anomaly_v03_slices as slices
from .anomaly_v03_observation_audit import read_pinned, paths, scores

QUIET = {'formal_permission': False, 'promotion_allowed': False,
         'independent_s6_complete': False, 'performance_status': 'not_evaluated',
         'selected_candidate': None, 'bootstrap_performed': False}
SCHEMA = 'schemas/anomaly-multiseed-analysis-result-v0.3.schema.json'
SC = ('planned', 'observed', 'available', 'threshold_exceeded', 'signal_onsets', 'unscored_target', 'outside_test')


def need(ok, context):
    if not ok: raise ValueError('analysis inputs: '+context)


def exact(a, b, context):need(registry.canonical_json(a)==registry.canonical_json(b), context)


def integer(n):
    need(type(n) is int and n>=0, 'nonnegative integer required')
    return n


def fields(value, expected, context):
    for k,v in expected.items():exact(value[k],v,context+': '+k)


def index(rows, names, expected):
    keys=[tuple(r[k] for k in names) for r in rows]
    need(len(keys)==len(set(keys))==len(expected) and set(keys)==set(expected),'table identity inventory')
    return dict(zip(keys,rows))


def _slice_counts(table, n):
    raw=slices.empty_counts();raw['evaluations']=n
    raw['profile_inconclusive_evaluations']=integer(table['profile_inconclusive_evaluations'])
    need(raw['profile_inconclusive_evaluations']<=n,'profile diagnostic coverage')
    histogram=table['delay_histogram'];slices.delay_summary(histogram)
    raw['delay_histogram']=copy.deepcopy(histogram)
    for group, inventory in (('incident_slices',slices.INCIDENT_KEYS),('score_slices',slices.SCORE_KEYS)):
        cells=index(table[group],('dimension','key'),[(d,k) for d,keys in inventory.items() for k in keys])
        for dimension,keys in inventory.items():
            for key in keys:
                cell=cells[dimension,key];dest=raw[group][dimension][key]
                if group=='incident_slices':
                    dest.update(planned=integer(cell['planned']),detected=integer(cell['detected']),
                                delay_histogram=copy.deepcopy(cell['delay_histogram']))
                    delay=slices.delay_summary(dest['delay_histogram'])
                    need(dest['detected']==delay['count']<=dest['planned'],'incident delay coverage')
                else:
                    dest.update({k:integer(cell[k]) for k in SC})
                    need(dest['signal_onsets']<=dest['threshold_exceeded']<=dest['available']<=dest['observed'],'score decision subsets')
                    exact(dest['planned'],dest['observed']+dest['unscored_target']+dest['outside_test'],'reference accounting')
                    if dimension!='event-offset':
                        exact([dest['unscored_target'],dest['outside_test']],[0,0],'score partition omissions')
                    else:
                        exact([dest['planned'],dest['unscored_target']],[40*n,10*n],'event offset planned references')
            if group=='incident_slices':
                exact(sum(c['planned'] for c in raw[group][dimension].values()),20*n,'incident planned partition')
                exact([sum(c['delay_histogram'][i] for c in raw[group][dimension].values()) for i in range(5)],histogram,'incident histogram partition')
            elif dimension!='event-offset':
                exact(sum(c['planned'] for c in raw[group][dimension].values()),14400*n,'score planned partition')
    need(set(table['equipment_context'])==set(raw['equipment_context']),'equipment context keys')
    for k,dest in raw['equipment_context'].items():
        source=table['equipment_context'][k]
        exact(sorted(source),sorted(dest),'equipment context fields')
        dest.update({name:integer(source[name]) for name in dest})
        need(dest['unmatched']<=dest['episodes'],'unmatched episode subset')
    exact(sum(c['planned_seconds'] for c in raw['equipment_context'].values()),3600*n,'equipment exposure')
    exact(raw['equipment_context']['clean']['planned_seconds'],3365*n,'clean planned exposure')
    for key,context in raw['equipment_context'].items():
        exact(raw['score_slices']['context'][key]['planned'],4*context['planned_seconds'],'score/equipment context exposure')
    for dimension,cells in raw['score_slices'].items():
        if dimension=='event-offset':continue
        for field in ('available','threshold_exceeded','signal_onsets'):
            exact(sum(c[field] for c in cells.values()),
                  sum(c[field] for c in raw['score_slices']['full-target'].values()),'score decision partition totals')
    # Rebuild all derived fractions and null states, while retaining zero cells.
    fields(table,slices.describe(raw),'slice derived fields')
    return raw


def _join_table(count, table, n):
    exact(count['evaluations'],n,'count evaluation coverage');exact(table['evaluations'],n,'slice evaluation coverage')
    raw=_slice_counts(table,n)
    need(set(count['counts'])==set(arithmetic.METRICS) and set(count['points'])==set(arithmetic.METRICS),'metric inventory')
    for kind,pair in count['counts'].items():
        arithmetic.counts(pair,kind)
        exact(count['points'][kind],arithmetic.ratio(*pair,kind),'count-derived point')
    metrics=count['counts']
    for kind in ('machine','sensor'):
        cell=raw['incident_slices']['class'][kind]
        exact(metrics[kind+'_recall'],[cell['detected'],cell['planned']],'recall join')
        exact(cell['planned'],10*n,'class denominator')
    ctx=raw['equipment_context']
    exact(metrics['precision'],[sum(raw['delay_histogram']),sum(c['episodes'] for c in ctx.values())],'delay/precision join')
    exact(metrics['false_alert_burden'],[sum(c['unmatched'] for c in ctx.values()),20*n],'unmatched join')
    exact(metrics['precision'][1],metrics['precision'][0]+metrics['false_alert_burden'][0],'episode accounting')
    exact(metrics['clean_rate'],[ctx['clean']['unmatched'],3365*n],'clean join')
    for target in slices.TARGETS:
        cell=raw['score_slices']['full-target'][target]
        exact(metrics['availability:'+target],[cell['available'],cell['planned']],'availability join')
        exact(cell['planned'],1800*n,'full target denominator')
    exact(count['scheduled_clean_seconds'],3365*n,'scheduled exposure')
    need(integer(count['effective_clean_seconds'])<=3365*n,'effective exposure range')
    diagnostics=count['profile_diagnostics']
    exact(len(diagnostics),raw['profile_inconclusive_evaluations'],'profile diagnostic count')
    exact(count['profile_status'],'inconclusive' if diagnostics else 'success','profile outcome')
    fields(count,{'ci_status':'not_evaluated','ci_lower':None,'ci_upper':None},'descriptive only')
    result=copy.deepcopy(count)
    result.update(slices.describe(raw))
    result['effective_clean_rate']=arithmetic.ratio(metrics['clean_rate'][0],count['effective_clean_seconds'],'clean_rate')
    return result,raw


def _sum_matches(total, raw_total, parts, raw_parts):
    combined=slices.empty_counts()
    for part in raw_parts:slices.add_counts(combined,part)
    exact(raw_total,combined,'slice/delay additive coverage')
    for kind in arithmetic.METRICS:
        exact(total['counts'][kind],[sum(p['counts'][kind][i] for p in parts) for i in (0,1)],'count additive coverage')
    for name in ('scheduled_clean_seconds','effective_clean_seconds'):
        exact(total[name],sum(p[name] for p in parts),'exposure additive coverage')
    for name in ('profile_diagnostics','undefined_input_points'):
        exact(sorted(total[name],key=lambda r:r['evaluation_id']),
              sorted([item for p in parts for item in p[name]],key=lambda r:r['evaluation_id']),'diagnostic additive coverage')


def join_inputs(counts, diagnostics):
    """Pure, descriptive join. Call authenticate_analysis_inputs for byte trust."""
    fields(counts,{**QUIET,'status':'authenticated_dev_smoke_counts','evaluations':720},'counts scope')
    fields(diagnostics,{**QUIET,'status':'complete_dev_smoke_descriptive_slices','evaluations':720},'slice scope')
    entries=registry.seed_registry()['entries'][:2]
    identities=registry.evaluation_inventory('dev')+registry.evaluation_inventory('smoke')
    seed_keys=[(e['role'],seed,c,s) for e in entries for seed in e['seeds']
               for c in arithmetic.CANDIDATES for s in arithmetic.STRATA]
    role_keys=[(e['role'],c,s) for e in entries for c in arithmetic.CANDIDATES for s in arithmetic.STRATA]
    joined={};raws={}
    for name,names,keys in [('by_seed',('role','seed','candidate_id','stratum'),seed_keys),
                           ('by_role',('role','candidate_id','stratum'),role_keys)]:
        old=index(counts[name],names,keys);new=index(diagnostics[name],names,keys)
        joined[name]={};raws[name]={}
        for key in keys:
            role=key[0];n=12*(2 if key[-1]=='overall' else 1)
            if name=='by_role':n*=len(next(e['seeds'] for e in entries if e['role']==role))
            joined[name][key],raws[name][key]=_join_table(old[key],new[key],n)
            row=joined[name][key]
            ids={i['evaluation_id'] for i in identities if i['role']==role and
                 (name=='by_role' or i['seed']==key[1]) and i['candidate_id']==key[-2] and
                 (key[-1]=='overall' or i['stratum']==key[-1])}
            for diagnostic_name in ('profile_diagnostics','undefined_input_points'):
                reported=[d['evaluation_id'] for d in row[diagnostic_name]]
                need(len(reported)==len(set(reported)) and set(reported)<=ids,'diagnostic identity coverage')
    exact(counts['zero_denominator_input_metrics'],sum(len(d['metrics']) for key,row in joined['by_seed'].items()
          if key[-1]!='overall' for d in row['undefined_input_points']),'undefined input metric inventory')
    for role,seed,c,layer in seed_keys:
        if layer!='overall':continue
        key=(role,seed,c,layer);parts=[(role,seed,c,s) for s in arithmetic.STRATA[:2]]
        _sum_matches(joined['by_seed'][key],raws['by_seed'][key],
                     [joined['by_seed'][k] for k in parts],[raws['by_seed'][k] for k in parts])
    for role,c,layer in role_keys:
        key=(role,c,layer)
        parts=[(role,seed,c,layer) for seed in next(e['seeds'] for e in entries if e['role']==role)]
        _sum_matches(joined['by_role'][key],raws['by_role'][key],
                     [joined['by_seed'][k] for k in parts],[raws['by_seed'][k] for k in parts])
    clusters=copy.deepcopy(counts['seed_clusters'])
    expected=[[e['role'],i,seed] for e in entries for i,seed in enumerate(e['seeds'])]
    exact([[c['role'],c['registered_index'],c['seed']] for c in clusters],expected,'cluster registration')
    for cluster in clusters:
        role,seed=cluster['role'],cluster['seed']
        exact(cluster['layouts'],list(range(12)),'cluster layouts')
        exact(cluster['evaluation_ids'],[i['evaluation_id'] for i in identities if (i['role'],i['seed'])==(role,seed)],'cluster evaluation IDs')
        exact(sorted(cluster['candidates']),sorted(arithmetic.CANDIDATES),'cluster candidates')
        for candidate in arithmetic.CANDIDATES:
            exact(sorted(cluster['candidates'][candidate]),sorted(arithmetic.STRATA[:2]),'cluster strata')
            for layer,cell in cluster['candidates'][candidate].items():
                table=joined['by_seed'][role,seed,candidate,layer]
                exact(cell['counts'],table['counts'],'cluster counts join')
                exact(cell['profile_status'],'calibrated' if table['profile_status']=='success' else 'inconclusive','cluster profile join')
                cell.update({k:copy.deepcopy(table[k]) for k in ('effective_clean_seconds','delay_histogram','delay_summary')})
    return {**QUIET,'format':'anomaly-v03-descriptive-analysis-inputs-v1','status':'joined_dev_smoke_analysis_inputs',
        'evaluations':720,'seed_clusters':clusters,'by_seed':list(joined['by_seed'].values()),'by_role':list(joined['by_role'].values()),
        'zero_denominator_input_metrics':counts['zero_denominator_input_metrics'],
        'formal_document_emitted':False,'formal_schema_validated':False,'new_evaluations':0,'payloads_rehashed':False,
        'checks':{'seed_tables':90,'role_tables':18,'overall_additive_checks':30,'role_additive_checks':18},
        'limits':['descriptive dev/smoke; no formal 40-seed population',
                  'historically authenticated saved summaries, no current raw-payload attestation',
                  'no bootstrap, CI, performance gates, candidate selection or formal source/runtime acceptance']}


def formal_readiness(schema):
    """Account for every required top-level field, without fabricating a report."""
    needed=('schema_version','status','provenance','result_type','analysis_consumer','bootstrap',
            'candidate_tables','slices','selected_candidate','decision')
    exact(schema['required'],list(needed),'formal top-level contract')
    props=schema['properties'];boot=props['bootstrap']['properties']
    reasons={
        'schema_version':('known_constant','formal schema version 0.3; descriptive bundle has its own format'),
        'status':('not_accepted','join completion is not engineering or performance acceptance'),
        'provenance':('historical_only','retained dev/smoke pins exist; formal producer inventory/publication evidence not assembled'),
        'result_type':('known_constant','formal analysis identity is not emitted for this dev/smoke bundle'),
        'analysis_consumer':('not_accepted','current implementation revision is saved; formal clean consumer source/runtime acceptance and freeze remain'),
        'bootstrap':('not_executed','fixed draw algorithm was tested; no registered holdout bootstrap execution'),
        'candidate_tables':('descriptive_inputs_ready','counts, exposure, delay ready for dev/smoke; formal 40-seed CI/gates absent'),
        'slices':('descriptive_inputs_ready','diagnostic derivations ready; mapping into formal single-metric slice rows and semantic validation remain'),
        'selected_candidate':('not_evaluated','null retained; no gate-based selection'),
        'decision':('not_evaluated','no formal performance decision')}
    return {'status':'formal_analysis_not_ready','formal_ready':False,'formal_document_emitted':False,
        'required_fields':[{'field':k,'status':reasons[k][0],'reason':reasons[k][1]} for k in needed],
        'population':{'required_holdout_seeds':boot['clusters']['const'],'required_bootstrap_replicates':boot['replicates']['const'],
            'available_dev_seeds':8,'available_smoke_seeds':2,'holdout_data_read':False},
        'next_unblocked_work':'map diagnostic slices and descriptive metrics to a separately identified non-formal report; retain offset omissions and multiple score diagnostics',
        'held_work':['formal holdout execution','formal producer/consumer runtime acceptance','formal source freeze and publication','full independent S6']}


def authenticate_analysis_inputs(savepoints, root_sha256, schema_path):
    """Read three explicit manifests, two compact summaries and a pinned schema.

    No path from a report is opened. Paths are explicit or fixed relative names;
    historical raw input pins are preserved as evidence, not followed.
    """
    exact(sorted(savepoints),['adapter','seeds','slices'],'explicit savepoint roots')
    roots={k:paths.regular_path(v) for k,v in savepoints.items()};used={}
    def read(path,pin,maximum=1024**2):
        raw=read_pinned(path,pin,maximum);used[str(path)]=dict(pin)
        return scores.strict_json(raw)
    root_pin={'bytes':roots['slices'].stat().st_size,'sha256':root_sha256}
    root=read(roots['slices'],root_pin)
    fields(root,{**QUIET,'status':'saved_dev_smoke_slices_completed','evaluations':720,'chunks':120},'slice manifest')
    seed=read(roots['seeds'],root['prior_seed_manifest'])
    adapter=read(roots['adapter'],root['prior_adapter_manifest'])
    exact(adapter['prior_seed_manifest'],root['prior_seed_manifest'],'common prior seed manifest')
    fields(seed,{'status':'authenticated_seed_aggregation_completed'},'seed manifest')
    exact(root['prior_counts'],seed['counts_pin'],'common counts pin')
    exact(root['slices_pin'],root['artifacts']['slices.json'],'slice artifact binding')
    project=Path(__file__).resolve().parents[2]
    for name,pin in [('src/banto_ai/anomaly_v03_slices.py',root['code_pins']['src/banto_ai/anomaly_v03_slices.py']),
                     ('src/banto_ai/anomaly_v03.py',root['code_pins']['src/banto_ai/anomaly_v03.py']),
                     ('src/banto_ai/anomaly_v03_inference_audit.py',seed['code_pins']['src/banto_ai/anomaly_v03_inference_audit.py'])]:
        read_pinned(project/name,pin,1024**2)
    counts=read(roots['seeds'].parent/'verified/authenticated-counts.json',seed['counts_pin'])
    diagnostic=read(roots['slices'].parent/'slices.json',root['slices_pin'],16*1024**2)
    schema=read(paths.regular_path(schema_path),adapter['code_pins'][SCHEMA])
    result=join_inputs(counts,diagnostic)
    result.update(status='authenticated_dev_smoke_analysis_inputs',trust_anchor={'path':str(roots['slices']),**root_pin},
                  authenticated_files=used,source_payload_bytes_read=0,readiness=formal_readiness(schema))
    return result
