"""Descriptive dev/smoke tables from caller-pinned complete summary bindings.

No filesystem access, metadata replay, detector/ledger audit, bootstrap or gate.
The retained binding is a trusted receipt, not a signature or execution proof.
"""
from __future__ import annotations
from collections import Counter
import copy

from . import anomaly_v03_summary_coverage as binding

v=binding.v
flow=binding.summary
same=binding.same
inputs=flow.compact.connection.inputs
FORMAT='anomaly-v03-bound-summary-tables-v1'
MAX_BINDING=4*1024**2


def _receipt(raw,summaries,expected_pin,mode):
    v.require(type(mode) is str and mode in ('fixture','engineering'),'formal/unknown table mode is closed')
    v.require(type(raw) is bytes and type(summaries) is dict,'binding and summary bytes required')
    v.require(all(type(i) is int for i in summaries) and set(summaries)==set(range(120)),
              'all 120 summary chunks required before aggregation')
    v.require(all(type(b) is bytes for b in summaries.values()),'summary bytes required')
    v.require(len(raw)+sum(map(len,summaries.values()))<=binding.MAX_TOTAL,'total table input bytes')
    retained=binding._load(raw,expected_pin,MAX_BINDING)
    binding._fields(retained,{**flow.CLOSED,'format':binding.FORMAT,'mode':mode,'status':'complete_summary_binding',
        'registry_raw_sha256':v.REGISTRY_RAW_SHA256,'planned_chunks':120,'planned_evaluations':720,
        'bound_summary_chunks':120,'bound_summary_evaluations':720,'missing_summary_chunks':[],
        'unverified_summary_evaluations':0,'all_summary_inputs_bound':True,
        'current_source_payloads_read':0,'numeric_audits_repeated':0,'ledger_audits_repeated':0,'raw_generation_verified':False})
    refs=retained['summaries'];v.require(type(refs) is list and len(refs)==120,'complete binding references')
    identities=v.evaluation_inventory('dev')+v.evaluation_inventory('smoke')
    for index,ref in enumerate(refs):
        same(ref['chunk_index'],index,'ordered binding chunks')
        same(ref['evaluation_ids'],[i['evaluation_id'] for i in identities[index*6:index*6+6]],'registered binding identities')
        v.require(type(ref['attempt']) is int and 1<=ref['attempt']<=binding.metadata.consumer.MAX_ATTEMPTS,'bound attempt')
        binding.evidence._pin(ref['summary_pin'])
        v.require(0<len(summaries[index])<=binding.MAX_SUMMARY,'summary size limit')
        binding.evidence._raw(summaries[index],ref['summary_pin'],'bound summary bytes changed')
    return retained,identities


def _rows(report,ref,identities,mode,retained):
    binding._fields(report,{**flow.CLOSED,'format':flow.FORMAT,'mode':mode,'status':'selected_chunk_summaries_verified',
        'chunk_index':ref['chunk_index'],'attempt':ref['attempt'],'evaluations_checked':6,
        'prior_attempts_not_credited':ref['attempt']-1,
        'data_origin':'caller-declared-fixture' if mode=='fixture' else 'saved-dev-smoke'})
    audit=report['audit'];context=retained['summary_context']
    same(audit['run_root'],context['run_root'],'bound run context')
    same(audit['trust_anchor'],{'path':context['savepoint_path'],**retained['completed_savepoint_pin']},'bound savepoint')
    same(audit['evidence_pin'],retained['evidence_pin'],'bound evidence')
    same(audit['input_pins']['run/metadata/plan.json'],context['plan_file_pin'],'bound plan file')
    rows=report['evaluations'];audits=audit['evaluations']
    v.require(type(rows) is list and type(audits) is list and len(rows)==len(audits)==6,'six bound evaluations')
    states=Counter();undefined=0;projected=[]
    for row,checked,identity in zip(rows,audits,identities):
        binding._fields(row,{**flow.CLOSED,'identity':identity})
        derived=flow.primary.evaluation_counts(checked,identity)
        same(row['evaluation_outcome'],derived['evaluation_outcome'],'bound summary outcome')
        same(row['inconclusive_profiles'],derived['inconclusive_profiles'],'bound profile diagnostics')
        for name in ('counts','effective_clean_seconds'):same(row['primary'][name],derived[name],'bound primary '+name)
        same(row['primary']['profile_status'],'inconclusive' if derived['inconclusive_profiles'] else 'calibrated','profile state')
        shape=flow.slices.empty_counts();flow.compact.connection._raw_shape(row['slices'],shape)
        raw=binding._ordered_counts(row['slices'],shape)
        same(raw['evaluations'],1,'one bound slice evaluation');flow.compact._check(raw,row['primary'])
        flow.reader.ledger._numeric_equal(checked['ledger_audit']['metrics']['delay_summary'],flow.slices.delay_summary(raw['delay_histogram']))
        zero=[k for k,pair in derived['counts'].items() if pair[1]==0]
        same(row['zero_denominator_metrics'],zero,'bound undefined diagnostics')
        undefined+=len(zero);states[row['evaluation_outcome']]+=1
        projected.append((checked,{'status':'saved_slice_counts_checked','identity':identity,'counts':raw}))
    same(dict(states),ref['coverage'],'per-chunk coverage')
    same(undefined,ref['zero_denominator_metrics'],'per-chunk undefined count')
    return projected,states


def _tables(audits,accumulator):
    primary=flow.primary.aggregate_evaluations(audits)
    slices=accumulator.finish()
    joined={}
    for name,keys in (('by_seed',('role','seed','candidate_id','stratum')),('by_role',('role','candidate_id','stratum'))):
        reference={tuple(r[k] for k in keys):r for r in slices[name]}
        v.require(len(reference)==len(slices[name])==len(primary[name]),'table identity inventory')
        joined[name]=[]
        for row in primary[name]:
            key=tuple(row[k] for k in keys);v.require(key in reference,'matching primary/slice table')
            table,_=inputs._join_table(row,reference.pop(key),row['evaluations'])
            joined[name].append(table)
        v.require(not reference,'no unmatched slice table')
    return {**joined,'seed_clusters':primary['seed_clusters'],'paired_descriptive':primary['paired_descriptive'],
        'zero_denominator_input_metrics':primary['zero_denominator_input_metrics']}


def aggregate_bound_summaries(binding_raw,summaries,*,expected_binding_pin,expected_mode):
    """Reuse one externally pinned complete binding; open no recorded paths.

    Partial inputs are rejected before aggregation. Byte trust comes from the
    retained receipt; counts are pooled before ratios and delay statistics.
    """
    retained,identities=_receipt(binding_raw,summaries,expected_binding_pin,expected_mode)
    accumulator=flow.slices.SliceAccumulator();audits=[];coverage=Counter()
    for index,ref in enumerate(retained['summaries']):
        report=v.strict_json(summaries[index])
        rows,states=_rows(report,ref,identities[index*6:index*6+6],expected_mode,retained)
        for audit,slice_row in rows:audits.append(audit);accumulator.add(slice_row)
        coverage.update(states)
    counts={s:coverage[s] for s in binding.metadata.consumer.SLOT_STATES}
    same(counts,retained['bound_summary_coverage'],'bound whole coverage')
    same(counts,retained['declared_coverage'],'declared whole coverage')
    tables=_tables(audits,accumulator)
    same(tables['zero_denominator_input_metrics'],retained['zero_denominator_metrics_retained'],'whole undefined count')
    return {**flow.CLOSED,'format':FORMAT,'mode':expected_mode,'status':'complete_dev_smoke_descriptive_tables',
        'evaluations':720,'seed_groups':10,'coverage':counts,**tables,
        'binding_pin':copy.deepcopy(expected_binding_pin),'registry_raw_sha256':v.REGISTRY_RAW_SHA256,
        'metadata_pin':copy.deepcopy(retained['metadata_pin']),'journal_bindings':copy.deepcopy(retained['journal_bindings']),
        'completed_savepoint_pin':copy.deepcopy(retained['completed_savepoint_pin']),
        'evidence_pin':copy.deepcopy(retained['evidence_pin']),'source_summaries':copy.deepcopy(retained['summaries']),
        'failed_attempt_history':copy.deepcopy(retained['failed_attempt_history']),
        'current_source_payloads_read':0,'numeric_audits_repeated':0,'ledger_audits_repeated':0,
        'journal_replayed':False,'raw_generation_verified':False,'real_performance_intervals_computed':0,
        'class_precision':'not_applicable','event_offsets_exclusive_partition':False,
        'limits':['caller-pinned retained binding and compact summaries; no current raw payload authentication',
            'dev8 and smoke2 remain separate descriptive populations; no formal 40-seed mapping',
            'no new detector/ledger computation, bootstrap, confidence intervals, gates or candidate selection']}
