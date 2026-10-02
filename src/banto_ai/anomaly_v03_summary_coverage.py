"""Pure binding of pinned compact summaries to retained dev/smoke coverage.

No paths are opened, no numeric/ledger audit is repeated, and no missing summary
is inferred from a completed journal. Caller-retained pins are the trust anchors.
"""
from __future__ import annotations
from collections import Counter
import copy

from . import anomaly_v03_saved_chunk_summary as summary
from . import anomaly_v03_consumer_checkpoints as metadata
from . import anomaly_v03_consumer_evidence as evidence

v = metadata.v
same = metadata.consumer._same
FORMAT = 'anomaly-v03-summary-coverage-binding-v1'
MAX_METADATA = 4*1024**2
MAX_SUMMARY = 512*1024
MAX_TOTAL = 32*1024**2


def _fields(value, required):
    v.require(type(value) is dict and set(required) <= set(value),'binding record fields')
    for name,want in required.items():same(value[name],want,'binding field '+name)


def _load(raw,pin,maximum):
    evidence._pin(pin)
    v.require(type(raw) is bytes and 0 < len(raw) <= maximum,'binding byte bound')
    evidence._raw(raw,pin,'external binding pin mismatch')
    return v.strict_json(raw)


def _metadata(value):
    _fields(value,{'format':metadata.FORMAT,'mode':metadata.MODE,'validation_status':'checkpoint_metadata_adapted',
        'journal_declares_coverage_complete':True,'declared_complete_chunks':120,
        **{k:False for k in ('input_bytes_verified','publication_verified','producer_exit_verified','source_runtime_accepted',
            'result_trusted','campaign_completed','execution_authorized','analysis_authorized','formal_permission',
            'promotion_allowed','independent_s6_complete')},'performance_status':'not_evaluated','selected_candidate':None})
    chunks=value['chunks'];v.require(type(chunks) is list and len(chunks)==120,'full planned chunk inventory')
    identities=v.evaluation_inventory('dev')+v.evaluation_inventory('smoke')
    bindings=value['bindings'];metadata.consumer._keys(bindings,'plan_sha256 record_count head_sha256 manifests_metadata_sha256','metadata bindings')
    for n in ('plan_sha256','head_sha256','manifests_metadata_sha256'):metadata.consumer._digest(bindings[n])
    v.require(type(bindings['record_count']) is int and 1 <= bindings['record_count'] <= metadata.journal.MAX_RECORDS,'record count')
    count=Counter();history=[];sequences=[];attempt_count=0;source=None
    for index,chunk in enumerate(chunks):
        same(chunk['chunk_index'],index,'chunk order');same(chunk['identities'],identities[index*6:index*6+6],'registered identity inventory')
        attempts=chunk['attempts'];v.require(type(attempts) is list and 1 <= len(attempts) <= metadata.consumer.MAX_ATTEMPTS,'attempt count bound')
        same(chunk['selected_attempt'],len(attempts),'latest attempt required')
        datasets={}
        for number,attempt in enumerate(attempts,1):
            same(attempt['attempt'],number,'attempt sequence')
            wanted=f'chunks/{index:03d}/attempt-{number:04d}'
            same(attempt['attempt_root'],wanted,'attempt root metadata')
            selected=number==len(attempts)
            v.require(attempt['status'] in (metadata.journal.VERIFIED if selected else ('failed','interrupted')),'selected/failure attempt state')
            if not selected:v.require(attempt['reason'] not in metadata.consumer.INTEGRITY_REASONS,'retry after integrity failure')
            metadata.consumer._digest(attempt['terminal_record_sha256'])
            seq=attempt['record_sequences'];v.require(type(seq) is list and bool(seq) and all(type(n) is int for n in seq),'record sequences')
            sequences.extend(seq)
            current=attempt['context']['source_bindings']
            if source is None:
                source=copy.deepcopy(current)
                same(v.canonical_sha256(metadata.journal.fixed_plan(**source)),bindings['plan_sha256'],'fixed plan binding')
            else:same(current,source,'attempt source bindings')
            rows=attempt['evaluations']
            if rows is None:
                v.require(not selected and attempt['evaluation_detail']=='unreported','unknown failure slots only')
            else:
                v.require(type(rows) is list and len(rows)==6,'six attempt slots')
                for row,identity in zip(rows,chunk['identities']):
                    state=metadata.consumer._slot(row,identity)
                    if selected:v.require(state in ('success','inconclusive'),'latest evaluation incomplete')
                    hashes=row['input_hashes']
                    if hashes is not None:
                        key=identity['dataset_id']
                        if key in datasets:same(hashes,datasets[key],'candidate/retry inputs differ')
                        datasets[key]=hashes
            if selected:
                same(attempt['status'],'verified_inconclusive' if any(r['status']=='inconclusive' for r in rows) else 'verified_complete','latest outcome')
                same(attempt['manifest_state'],'complete','complete selected manifest')
                count.update(r['status'] for r in rows)
            else:history.append((index,number,attempt['terminal_record_sha256']))
        attempt_count+=len(attempts)
    same(sequences,list(range(1,bindings['record_count']+1)),'complete record sequence inventory')
    same(chunks[-1]['attempts'][-1]['terminal_record_sha256'],bindings['head_sha256'],'terminal head binding')
    same(value['attempt_count'],attempt_count,'total attempt count')
    same(value['coverage'],{n:count[n] for n in metadata.consumer.SLOT_STATES},'declared latest coverage')
    failures=value['failed_attempt_history'];v.require(type(failures) is list and len(failures)==len(history),'failure history inventory')
    for failure,(index,number,digest) in zip(failures,history):
        same([failure['chunk_index'],failure['attempt'],failure['terminal_record_sha256']],[index,number,digest],'failure history binding')
        same(metadata.journal.record_hash(failure['terminal_record']),digest,'retained failure record hash')
        same(failure['evaluation_detail'],chunks[index]['attempts'][number-1]['evaluation_detail'],'unknown failure details preserved')
    return chunks


def _bind_report(report,chunk,mode,savepoint_pin,evidence_pin):
    index=chunk['chunk_index'];latest=chunk['attempts'][-1];attempt=latest['attempt']
    _fields(report,{**summary.CLOSED,'format':summary.FORMAT,'mode':mode,'status':'selected_chunk_summaries_verified',
        'scope':'one-completed-dev-smoke-chunk','chunk_index':index,'attempt':attempt,
        'prior_attempts_not_credited':len(chunk['attempts'])-1,'evaluations_checked':6,
        'current_observation_profile_score_audit':True,'current_ledger_audit':True,
        'primary_slice_consistency_checked':True,'full_event_ledger_bytes_matched':True,
        'all_campaign_payloads_read':False,'raw_generation_verified':False,
        'data_origin':'caller-declared-fixture' if mode=='fixture' else 'saved-dev-smoke'})
    audit=report['audit']
    _fields(audit,{**summary.primary.QUIET,'format':'anomaly-v03-connected-observation-audit-v1',
        'status':'selected_chunk_checks_passed','scope':'selected-completed-dev-smoke-chunk',
        'chunk_index':index,'attempt':attempt,'prior_attempts_not_credited':len(chunk['attempts'])-1,
        'evaluations_checked':6,'profile_derivation_verified':True,'score_derivation_verified':True,
        'ledger_derivation_verified':True,'campaign_evaluations_credited':0,'evidence_pin':evidence_pin})
    anchor=audit['trust_anchor'];metadata.consumer._keys(anchor,'path bytes sha256','summary trust anchor')
    same({n:anchor[n] for n in ('bytes','sha256')},savepoint_pin,'common completed savepoint')
    v.require(type(anchor['path']) is str and 0 < len(anchor['path']) <= 4096,'anchor path metadata')
    v.require(type(audit['run_root']) is str and 0 < len(audit['run_root']) <= 4096,'run root metadata')
    stem=f'run/attempts/chunks/{index:03d}/attempt-{attempt:04d}'
    old_audit=stem+'/audit/report.json';wanted={'run/metadata/plan.json',old_audit}
    for identity in chunk['identities']:
        wanted.update(stem+'/result/payload/datasets/'+identity['dataset_id']+'/'+name for name in summary.reader.DATASET_INPUTS.values())
        wanted.add(stem+'/result/payload/evaluations/'+identity['evaluation_id']+'.json')
    pins=audit['input_pins'];v.require(type(pins) is dict and set(pins)==wanted,'exact selected input inventory')
    for name,pin in pins.items():
        evidence._pin(pin)
        maximum=32*1024**2 if '/evaluations/' in name else 16*1024**2
        v.require(0 < pin['bytes'] <= maximum,'saved source pin byte bound')
    same(audit['input_bytes'],sum(p['bytes'] for p in pins.values()),'saved source byte count')
    same(pins[old_audit]['sha256'],latest['evidence']['audit_sha256'],'selected historical audit pin')
    rows=report['evaluations'];audits=audit['evaluations']
    v.require(type(rows) is list and type(audits) is list and len(rows)==len(audits)==6,'six summary/audit rows')
    outcomes=Counter();undefined=0
    for row,checked,slot,identity in zip(rows,audits,latest['evaluations'],chunk['identities']):
        _fields(row,{**summary.CLOSED,'identity':identity,'evaluation_outcome':slot['status'],'input_hashes':slot['input_hashes']})
        epin=pins[stem+'/result/payload/evaluations/'+identity['evaluation_id']+'.json']
        same(row['evaluation_pin'],epin,'summary evaluation pin');same(epin['sha256'],slot['evaluation_sha256'],'manifest evaluation hash')
        for key,name in summary.reader.DATASET_INPUTS.items():
            same(pins[stem+'/result/payload/datasets/'+identity['dataset_id']+'/'+name]['sha256'],slot['input_hashes'][key],'manifest input hash')
        derived=summary.primary.evaluation_counts(checked,identity)
        same(derived['evaluation_outcome'],slot['status'],'audit outcome binding')
        same(row['inconclusive_profiles'],derived['inconclusive_profiles'],'profile diagnostics binding')
        primary=row['primary'];raw=row['slices']
        metadata.consumer._keys(primary,'counts effective_clean_seconds delay_histogram profile_status','primary summary fields')
        for key in ('counts','effective_clean_seconds'):same(primary[key],derived[key],'primary/audit '+key)
        same(primary['profile_status'],slot['profile_status'],'profile declaration binding')
        summary.compact.connection._raw_shape(raw,summary.slices.empty_counts())
        same(raw['evaluations'],1,'one evaluation slice');summary.compact._check(raw,primary)
        summary.reader.ledger._numeric_equal(checked['ledger_audit']['metrics']['delay_summary'],summary.slices.delay_summary(raw['delay_histogram']))
        zero=[n for n,pair in derived['counts'].items() if pair[1]==0]
        same(row['zero_denominator_metrics'],zero,'zero denominator diagnostics')
        undefined+=len(zero);outcomes[slot['status']]+=1
    return {'chunk_index':index,'attempt':attempt,'evaluation_ids':[i['evaluation_id'] for i in chunk['identities']],
        'coverage':dict(outcomes),'zero_denominator_metrics':undefined,
        'run_root':audit['run_root'],'savepoint_path':anchor['path'],'plan_file_pin':pins['run/metadata/plan.json']}


def bind_summary_coverage(metadata_raw, summaries, *, expected_mode, expected_metadata_pin,
                          expected_summary_pins, expected_savepoint_pin, expected_evidence_pin):
    """Bind supplied subsets honestly; missing planned summaries stay unverified.

    summaries and expected_summary_pins map integer chunk indexes to raw bytes
    and externally retained pins. The sets must match, even for a partial batch.
    No path strings from a retained report are followed or checked on disk.
    """
    v.require(type(expected_mode) is str and expected_mode in ('fixture','engineering'),'formal/unknown binding mode is closed')
    for pin in (expected_savepoint_pin,expected_evidence_pin):evidence._pin(pin);v.require(pin['bytes']>0,'nonempty external anchor')
    v.require(type(summaries) is dict and type(expected_summary_pins) is dict,'explicit summary inventories')
    v.require(set(summaries)==set(expected_summary_pins) and len(summaries)<=120,'summary/pin inventory mismatch')
    v.require(all(type(i) is int and 0 <= i < 120 for i in summaries),'registered chunk index')
    v.require(type(metadata_raw) is bytes and all(type(b) is bytes for b in summaries.values()),'supplied bytes required')
    v.require(len(metadata_raw)+sum(map(len,summaries.values())) <= MAX_TOTAL,'total binding bytes')
    value=_load(metadata_raw,expected_metadata_pin,MAX_METADATA);chunks=_metadata(value)
    refs=[];coverage=Counter();common=None;undefined=0
    for index in sorted(summaries):
        report=_load(summaries[index],expected_summary_pins[index],MAX_SUMMARY)
        bound=_bind_report(report,chunks[index],expected_mode,expected_savepoint_pin,expected_evidence_pin)
        context={n:bound.pop(n) for n in ('run_root','savepoint_path','plan_file_pin')}
        if common is None:common=context
        else:same(context,common,'different campaign summary context')
        coverage.update(bound['coverage']);undefined+=bound['zero_denominator_metrics']
        refs.append({**bound,'summary_pin':copy.deepcopy(expected_summary_pins[index])})
    missing=[i for i in range(120) if i not in summaries]
    return {**summary.CLOSED,'format':FORMAT,'mode':expected_mode,
        'status':'complete_summary_binding' if not missing else 'partial_summary_binding',
        'registry_raw_sha256':v.REGISTRY_RAW_SHA256,'metadata_pin':copy.deepcopy(expected_metadata_pin),
        'completed_savepoint_pin':copy.deepcopy(expected_savepoint_pin),'evidence_pin':copy.deepcopy(expected_evidence_pin),
        'journal_bindings':copy.deepcopy(value['bindings']),'planned_chunks':120,'planned_evaluations':720,
        'declared_coverage':copy.deepcopy(value['coverage']),'bound_summary_chunks':len(refs),'bound_summary_evaluations':6*len(refs),
        'bound_summary_coverage':{n:coverage[n] for n in metadata.consumer.SLOT_STATES},
        'missing_summary_chunks':missing,'unverified_summary_evaluations':6*len(missing),
        'all_summary_inputs_bound':not missing,'summaries':refs,'summary_context':common,
        'failed_attempt_history':copy.deepcopy(value['failed_attempt_history']),
        'zero_denominator_metrics_retained':undefined,'current_source_payloads_read':0,
        'numeric_audits_repeated':0,'ledger_audits_repeated':0,'raw_generation_verified':False,
        'trust_boundary':'caller-pinned previously verified metadata and summary bytes; no journal replay or current raw payload authentication'}
