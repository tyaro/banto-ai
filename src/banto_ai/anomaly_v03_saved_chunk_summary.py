"""One selected saved dev/smoke chunk to audited primary and slice counts.

Reuse the existing pinned reader and independent arithmetic, keeping one large
evaluation in memory. No full-campaign aggregation, formal entry or publication.
"""
from __future__ import annotations
import copy

from . import anomaly_v03_observation_audit as reader
from . import anomaly_v03_seed_aggregate as primary
from . import anomaly_v03_slices as slices
from . import anomaly_v03_producer_slice_fixture as compact

FORMAT = 'anomaly-v03-saved-chunk-summary-v1'
CLOSED = {**primary.QUIET,'analysis_authorized':False,'producer_execution_authenticated':False,
    'execution_authenticated':False,'result_trusted':False,'source_closure_complete':False,
    'runtime_closure_complete':False,'bootstrap_performed':False,'new_evaluations':0,
    'campaign_evaluations_credited':0,'selected_candidate':None}


def _summarize(result, audit, *, evaluation_pin):
    """Internal projection; caller supplies the just-completed audits, not claims."""
    counts = primary.evaluation_counts(audit,result['identity'])
    sidecar = slices.summarize_evaluation(result,audit)['counts']
    summary = {'counts':counts['counts'],'effective_clean_seconds':counts['effective_clean_seconds'],
        'delay_histogram':sidecar['delay_histogram'],
        'profile_status':'inconclusive' if counts['evaluation_outcome'] == 'inconclusive' else 'calibrated'}
    # Reuse the boundary's primary/slice consistency checks without relabelling
    # real-format dev/smoke identities as the invented 40-cluster registration.
    compact._check(sidecar,summary)
    return {**CLOSED,'identity':copy.deepcopy(result['identity']),
        'evaluation_pin':copy.deepcopy(evaluation_pin),'input_hashes':copy.deepcopy(result['input_hashes']),
        'evaluation_outcome':counts['evaluation_outcome'],'primary':summary,'slices':sidecar,
        'inconclusive_profiles':copy.deepcopy(counts['inconclusive_profiles']),
        'zero_denominator_metrics':[n for n,pair in counts['counts'].items() if pair[1] == 0]}


def _summaries_from_report(report, expected_mode, *, partial_fixture=False):
    rows = report.pop('evaluation_summaries')
    reader.same(len(rows),6,'six ordered summaries required')
    for row,audit in zip(rows,report['evaluations']):
        reader.same(row['identity'],audit['identity'],'summary/audit identity')
        reader.same(row['evaluation_outcome'],audit['evaluation_outcome'],'summary/audit outcome')
    result = {**CLOSED,'format':FORMAT,'mode':expected_mode,'status':'selected_chunk_summaries_verified',
        'scope':('one-invented-partial-fixture-chunk' if partial_fixture else
                 'one-completed-dev-smoke-chunk'),
        'chunk_index':report['chunk_index'],'attempt':report['attempt'],
        'prior_attempts_not_credited':report['prior_attempts_not_credited'],
        'evaluations':rows,'audit':report,'evaluations_checked':6,
        'current_observation_profile_score_audit':True,'current_ledger_audit':True,
        'primary_slice_consistency_checked':True,'full_event_ledger_bytes_matched':True,
        'all_campaign_payloads_read':False,'raw_generation_verified':False,
        'data_origin':'caller-declared-fixture' if expected_mode == 'fixture' else 'saved-dev-smoke',
        'limits':['external savepoint is a trusted anchor, not a signature',
                  'only selected latest attempt rechecked; historical failures not credited',
                  'other chunks and historical process/source/runtime checks inherited',
                  'origins/quality-mask/split/targets bytes pinned; their generation not derived',
                  'no formal 40-seed mapping or 50000-draw inference',
                  'caller must bound whole-call time, memory and resource use']}
    if partial_fixture:
        result.update(fixture_partial=True, other_chunks_authenticated=False,
            limits=['external digest authenticates saved bytes, not invented data origin',
                    'only chunk 0 is represented; no completed campaign coverage',
                    'origins/quality-mask/split/targets bytes pinned; their generation not derived',
                    'no formal 40-seed mapping or 50000-draw inference',
                    'caller must bound whole-call time, memory and resource use'])
    return result


def read_chunk_summaries(savepoint, savepoint_sha256, run_root, chunk_index, *, expected_mode):
    """Read one externally pinned completed chunk, auditing each selected result.

    fixture means the caller supplies invented bytes in the saved dev/smoke
    format; engineering permits those real saved bytes. Neither authenticates
    how observations were generated or opens registered holdout processing.
    """
    reader.scores.need(type(expected_mode) is str and expected_mode in ('fixture','engineering'),
                       'formal/unknown summary mode is closed')
    report = reader.audit_completed_chunk(savepoint,savepoint_sha256,run_root,chunk_index,include_summaries=True)
    return _summaries_from_report(report, expected_mode)


def read_partial_fixture_chunk_summaries(savepoint, savepoint_sha256, run_root, chunk_index):
    """Read an invented one-chunk scaffold with no completed savepoint claim."""
    report = reader.audit_partial_fixture_chunk(savepoint,savepoint_sha256,run_root,chunk_index,
                                                include_summaries=True)
    return _summaries_from_report(report, 'fixture', partial_fixture=True)
