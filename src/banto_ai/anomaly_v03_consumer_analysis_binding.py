"""Join retained analysis provenance to verified publication metadata.

Read ten compact artifacts under explicit savepoint roots. Do not follow old
payload paths, rerun arithmetic, or promote historical authentication to current
payload/source/runtime acceptance. Both top-level savepoint pins are external.
"""
from __future__ import annotations

from pathlib import Path
import re

from . import anomaly_v03 as v
from . import anomaly_v03_consumer_checkpoints as adapter
from . import anomaly_v03_consumer_input as consumer
from . import anomaly_v03_observation_audit as pinned
from . import _anomaly_v03_runtime as paths

ROOTS = ('publication','analysis','adapter','seeds','completed')
INPUT_NAMES = {'observations':'observations.jsonl','events':'event-ledger.jsonl',
    'quality_mask':'quality-mask.jsonl','split':'split-manifest.json','origins':'origins.json','targets':'targets.json'}
FALSE_FIELDS = ('bootstrap_performed','formal_permission','independent_s6_complete','promotion_allowed')


def _fields(value, expected, message):
    v.require(type(value) is dict and set(expected) <= set(value), message)
    consumer._same({k:value[k] for k in expected}, expected, message)


def _quiet(value, status):
    _fields(value, {**dict.fromkeys(FALSE_FIELDS,False),'performance_status':'not_evaluated',
                   'selected_candidate':None,'status':status,'evaluations':720}, 'historical analysis scope')


def _table_key(row, seed):
    return tuple(row[k] for k in (('role','seed','candidate_id','stratum') if seed else ('role','candidate_id','stratum')))


def _bind_tables(analysis, counts, identities):
    # Equality joins only. Previously checked ratios, diagnostics and slice
    # arithmetic are retained; no aggregate or inferential math is repeated.
    for name, seed, size in (('by_seed',True,90),('by_role',False,18)):
        left, right = analysis[name], counts[name]
        v.require(type(left) is list and type(right) is list and len(left)==len(right)==size,'analysis table inventory')
        keys = []
        for identity in identities:
            for layer in (identity['stratum'],'overall'):
                key = _table_key({**identity,'stratum':layer},seed)
                if key not in keys: keys.append(key)
        v.require(len(set(_table_key(r,seed) for r in left))==size and
                  set(_table_key(r,seed) for r in left)==set(keys), 'analysis table identity inventory')
        v.require(len(set(_table_key(r,seed) for r in right))==size and
                  set(_table_key(r,seed) for r in right)==set(keys), 'counts table identity inventory')
        source = {_table_key(r,seed):r for r in right}
        for row in left: _fields(row,source[_table_key(row,seed)],'historical table value changed')
    a,b = analysis['seed_clusters'],counts['seed_clusters']
    v.require(type(a) is list and type(b) is list and len(a)==len(b)==10,'registered cluster count')
    groups = []
    for identity in identities:
        pair=(identity['role'],identity['seed'])
        if pair not in groups: groups.append(pair)
    for target, source, (role,seed) in zip(a,b,groups):
        expected_ids = [i['evaluation_id'] for i in identities if (i['role'],i['seed'])==(role,seed)]
        _fields(source,{'role':role,'seed':seed,'layouts':list(range(12)),
                       'evaluation_ids':expected_ids},'cluster registration/coverage')
        _fields(target,{k:val for k,val in source.items() if k!='candidates'},'cluster provenance changed')
        consumer._same(sorted(target['candidates']),sorted(source['candidates']),'cluster candidates')
        for candidate,cells in source['candidates'].items():
            consumer._same(sorted(target['candidates'][candidate]),sorted(cells),'cluster strata')
            for layer,cell in cells.items():
                _fields(target['candidates'][candidate][layer],cell,'historical cluster value changed')
    consumer._same(analysis['zero_denominator_input_metrics'],counts['zero_denominator_input_metrics'],
                   'undefined metric inventory changed')


def authenticate_analysis_binding(savepoints, *, expected_mode, expected_publication_pin, expected_analysis_pin):
    """Return a compact binding receipt; leave the saved analysis inputs intact.

    savepoints maps five explicit roles to their savepoint-evidence.json files.
    Every other filename is fixed below. Paths retained inside historical
    reports are compared as metadata and are never opened or enumerated.
    """
    v.require(type(expected_mode) is str and expected_mode==adapter.MODE,'formal/unknown analysis binding mode is closed')
    consumer._keys(savepoints,' '.join(ROOTS),'explicit savepoint roles')
    roots = {k:paths.regular_path(Path(savepoints[k])) for k in ROOTS}
    v.require(len(set(roots.values()))==len(ROOTS),'savepoint roles must be distinct')
    used = {}
    def read(path,pin,maximum=1024**2):
        v.require(str(path) not in used,'duplicate artifact read')
        raw=pinned.read_pinned(path,pin,maximum);used[str(path)]=dict(pin)
        return v.strict_json(raw)
    publication=read(roots['publication'],expected_publication_pin)
    analysis_save=read(roots['analysis'],expected_analysis_pin)
    _fields(publication,{'status':'consumer_publication_metadata_reader_completed','engineering_chunks':120,
        'engineering_evaluations':720,'publication_metadata_verified':True,'worker_exit_records_verified':True,
        'formal_permission':False,'analysis_authorized':False},'publication savepoint scope')
    _fields(analysis_save,{'status':'authenticated_analysis_inputs_completed','evaluations':720,
        'formal_permission':False,'formal_ready':False},'analysis savepoint scope')
    consumer._same(publication['boundaries']['closed'],analysis_save['boundaries']['closed'],'different campaign closures')
    adapter_save=read(roots['adapter'],publication['prior_savepoint'])
    _fields(adapter_save,{'status':'consumer_checkpoint_metadata_adapter_completed','formal_permission':False},'adapter savepoint scope')
    adapted=read(roots['adapter'].parent/'adapted-metadata.json',adapter_save['artifacts']['adapted-metadata.json'],4*1024**2)
    reports=read(roots['publication'].parent/'all-publication-checks.json',publication['artifacts']['all-publication-checks.json'],1024**2)
    analysis_path=roots['analysis'].parent/'analysis-inputs.json'
    analysis_pin=analysis_save['artifacts']['analysis-inputs.json']
    consumer._same(analysis_pin,analysis_save['analysis_inputs_pin'],'analysis artifact pin differs')
    analysis=read(analysis_path,analysis_pin,8*1024**2)
    _quiet(analysis,'authenticated_dev_smoke_analysis_inputs')
    _fields(analysis,{'format':'anomaly-v03-descriptive-analysis-inputs-v1'},'analysis format')
    seeds=read(roots['seeds'],analysis['authenticated_files'][str(roots['seeds'])])
    counts_path=roots['seeds'].parent/'verified/authenticated-counts.json'
    counts_pin=seeds['artifacts']['verified/authenticated-counts.json']
    consumer._same(counts_pin,analysis['authenticated_files'][str(counts_path)],'analysis/counts provenance pin')
    counts=read(counts_path,counts_pin,2*1024**2)
    _quiet(counts,'authenticated_dev_smoke_counts')
    _fields(counts,{'format':'anomaly-v03-dev-smoke-seed-counts-v1'},'counts format')
    completed_pin=counts['authenticated_files'][str(roots['completed'])]
    completed=read(roots['completed'],completed_pin)
    evidence_path=roots['completed'].parent/'evidence.json'
    evidence_pin=completed['artifacts']['evidence.json']
    consumer._same(evidence_pin,counts['authenticated_files'][str(evidence_path)],'counts campaign evidence pin')
    evidence=read(evidence_path,evidence_pin,4*1024**2)
    _fields(evidence,{'status':'completed','full_120_chunks_completed':True,'cumulative_verified_chunks':120,
                      'next_unverified_chunk':None,'formal_permission':False},'completed campaign evidence')
    _fields(adapted,{'format':adapter.FORMAT,'mode':adapter.MODE,'validation_status':'checkpoint_metadata_adapted',
        'declared_complete_chunks':120,'journal_declares_coverage_complete':True,'analysis_authorized':False,
        'formal_permission':False},'checkpoint adapter scope')
    state=evidence['journal_state'];binding=adapted['bindings'];chunks=adapted['chunks']
    consumer._same([binding['plan_sha256'],binding['record_count'],binding['head_sha256']],
                   [state['plan_sha256'],state['record_count'],state['head_sha256']],'campaign journal binding')
    v.require(type(chunks) is list and type(reports) is list and len(chunks)==len(reports)==len(state['chunks'])==120,
              'complete publication/chunk inventory')
    identities=v.evaluation_inventory('dev')+v.evaluation_inventory('smoke')
    adapter_digest=v.canonical_sha256(adapted)
    attempts_used=[];reference_checks=0;input_checks=0;result_checks=0
    for index,(chunk,report,old) in enumerate(zip(chunks,reports,state['chunks'])):
        consumer._same([chunk['chunk_index'],old['chunk_index']],[index,index],'chunk order')
        wanted=identities[index*6:index*6+6]
        consumer._same(chunk['identities'],wanted,'registered identities differ')
        v.require(len(chunk['attempts'])==len(old['attempts'])>0,'attempt history omitted')
        for now,prior in zip(chunk['attempts'],old['attempts']):
            _fields(now,prior,'historical attempt differs')
        latest=chunk['attempts'][-1];number=latest['attempt'];sequence=latest['record_sequences'][-1]
        consumer._same(chunk['selected_attempt'],number,'selected attempt differs')
        expected_report={'format':'anomaly-v03-consumer-publication-metadata-check-v1','mode':adapter.MODE,
            'status':'publication_metadata_verified','chunk_index':index,'attempt':number,'evaluations':6,
            'adapter_sha256':adapter_digest,'closed_sha256':publication['boundaries']['closed']['sha256'],
            'publication_metadata_verified':True,'manifest_bytes_verified':True,'worker_exit_records_verified':True,
            'controller_closure_record_verified':True,'controller_process_exit_verified':False,
            'full_payload_bytes_verified':False,'audit_report_bytes_verified':False,'publication_verified':False,
            'source_runtime_accepted':False,'result_trusted':False,'execution_authorized':False,'analysis_authorized':False,
            'formal_permission':False,'promotion_allowed':False,'independent_s6_complete':False,
            'performance_status':'not_evaluated','selected_candidate':None}
        _fields(report,expected_report,'publication report binding')
        stem=f'attempts/chunks/{index:03d}/attempt-{number:04d}/'
        names={f'metadata/journal/{sequence:06d}.json',stem+f'descriptors/{sequence:06d}.json',
               *(stem+name for name in ('result/.complete','result/marker-pending.json','result/payload/manifest.json',
                                        'producer-control/supervision.json','audit/supervision.json'))}
        read_files=report['files_read']
        v.require(type(read_files) is dict and len(read_files)==8,'publication read inventory')
        closure=set(read_files)-names
        v.require(len(closure)==1 and re.fullmatch(r'control/[0-9]{6}/closed\.json',next(iter(closure))), 'publication closure path')
        v.require(set(read_files)==names|closure,'publication file roles')
        for name,pin in read_files.items():
            consumer._same(pin,evidence['files']['run/'+name],'publication/campaign file pin differs')
            reference_checks+=1
        consumer._same(read_files[next(iter(closure))],publication['boundaries']['closed'],'closure file pin')
        consumer._same(read_files[f'metadata/journal/{sequence:06d}.json']['sha256'],latest['terminal_record_sha256'],'terminal record pin')
        for name,key in (('result/.complete','marker_sha256'),('producer-control/supervision.json','supervision_sha256')):
            consumer._same(read_files[stem+name]['sha256'],old['evidence'][key],'historical publication evidence')
        v.require(len(latest['evaluations'])==6,'six evaluation declarations')
        consumer._same([{'evaluation_id':r['identity']['evaluation_id'],'status':r['status']} for r in latest['evaluations']],
                       old['outcome']['slots'],'historical outcome differs')
        for row,identity in zip(latest['evaluations'],wanted):
            consumer._slot(row,identity)
            for key,filename in INPUT_NAMES.items():
                name='run/'+stem+'result/payload/datasets/'+identity['dataset_id']+'/'+filename
                consumer._same(row['input_hashes'][key],evidence['files'][name]['sha256'],'historical input pin differs')
                input_checks+=1
            name='run/'+stem+'result/payload/evaluations/'+identity['evaluation_id']+'.json'
            consumer._same(row['evaluation_sha256'],evidence['files'][name]['sha256'],'historical evaluation pin differs')
            result_checks+=1
        attempts_used.append({'chunk_index':index,'attempt':number,'prior_attempts_not_credited':len(chunk['attempts'])-1})
    consumer._same(counts['attempts_used'],attempts_used,'aggregation selected different attempts')
    _bind_tables(analysis,counts,identities)
    return {'format':'anomaly-v03-consumer-analysis-binding-v1','status':'historical_analysis_inputs_bound','mode':adapter.MODE,
        'analysis_input_reference':{'path':str(analysis_path),**analysis_pin},'authenticated_files':used,
        'external_anchors':{'publication':dict(expected_publication_pin),'analysis':dict(expected_analysis_pin)},
        'adapter_sha256':adapter_digest,'completed_savepoint_pin':completed_pin,'campaign_evidence_pin':evidence_pin,
        'closed_pin':publication['boundaries']['closed'],'chunks':120,'evaluations':720,'attempts_used':attempts_used,
        'failed_attempts_retained':sum(r['prior_attempts_not_credited'] for r in attempts_used),
        'publication_reference_checks':reference_checks,'input_pin_checks':input_checks,'evaluation_pin_checks':result_checks,
        'seed_clusters':10,'seed_tables':90,'role_tables':18,
        'undefined_input_metrics_retained':analysis['zero_denominator_input_metrics'],
        'historical_aggregate_authentication_reused':True,'historical_diagnostic_join_reused':True,
        'publication_metadata_binding_verified':True,'analysis_input_bytes_verified':True,
        'source_payload_bytes_read':0,'new_evaluations':0,'score_recalculations':0,'aggregate_recalculations':0,
        'full_payload_bytes_verified':False,'controller_process_exit_verified':False,'source_runtime_accepted':False,
        'result_trusted':False,'execution_authorized':False,'analysis_authorized':False,**dict.fromkeys(FALSE_FIELDS,False),
        'performance_status':'not_evaluated','selected_candidate':None,
        'next_step':'connect bound descriptive inputs to the engineering consumer entry point'}
