"""Decode-only bridge from a completed checkpoint journal to consumer slots.

No file access, score replay or execution. External canonical metadata pins do
not authenticate payload bytes. A journal has per-attempt publication markers,
not the single producer marker required by consumer-input-metadata-v1: keep its
own envelope, including unknown failed-attempt slots, without inventing either.
"""
from __future__ import annotations

import copy
from collections import Counter

from . import anomaly_v03 as v
from . import anomaly_v03_checkpoints as journal
from . import anomaly_v03_chunk_contract as contract
from . import anomaly_v03_consumer_input as consumer

FORMAT = 'anomaly-v03-consumer-checkpoint-adapter-v1'
MODE = 'engineering-dev-smoke'


def _slots(manifest, identities, by_dataset):
    rows = []
    for slot, identity in zip(manifest['slots'], identities):
        status = slot['status']
        row = {'identity': copy.deepcopy(slot['identity']), 'status': status,
            'profile_status': ('calibrated' if status == 'success' else
                               'inconclusive' if status == 'inconclusive' else 'not_evaluated'),
            'input_hashes': copy.deepcopy(slot['input_hashes']),
            'evaluation_sha256': None if slot['evaluation'] is None else slot['evaluation']['sha256']}
        # The profile label is inferred from the slot declaration only. No
        # evaluation/profile bytes were read or independently checked here.
        consumer._slot(row, identity)
        hashes = row['input_hashes']
        if hashes is not None:
            dataset = identity['dataset_id']
            if dataset in by_dataset:
                consumer._same(hashes, by_dataset[dataset], 'candidate/retry input pins differ')
            by_dataset[dataset] = hashes
        rows.append(row)
    return rows


def adapt_completed_journal(plan, records, attempt_manifests, *, expected_mode,
                            expected_plan_sha256, expected_record_count,
                            expected_head_sha256, expected_manifests_sha256):
    """Bind a full decoded dev/smoke journal and ordered manifest declarations.

    attempt_manifests has one {chunk_index, attempt, manifest} entry for every
    attempt, in journal order. Only a failed/interrupted attempt may have a null
    manifest; null means unknown slots, never six not-started slots. Its complete
    journal failure record remains available. All four external pins/counts
    must come from a caller-retained anchor, not from untrusted loaded metadata.

    The output is a checkpoint adapter envelope, NOT a producer completion
    declaration. Controller exit and per-attempt publication authentication
    still belong to a later reader. Neither is synthesized from journal status.
    """
    v.require(type(expected_mode) is str and expected_mode == MODE,
              'unsupported checkpoint consumer mode; formal input is closed')
    consumer._digest(expected_manifests_sha256)
    state = journal.reduce_journal(plan, records,
        expected_plan_sha256=expected_plan_sha256,
        expected_record_count=expected_record_count, expected_head_sha256=expected_head_sha256)
    v.require(state['declared_coverage_complete'] and state['next_unverified_chunk'] is None,
              'completed checkpoint coverage required')
    v.require(type(attempt_manifests) is list and len(attempt_manifests) == state['attempt_count'],
              'one manifest entry per historical attempt required')
    consumer._same(v.canonical_sha256(attempt_manifests), expected_manifests_sha256,
                   'external manifest metadata digest mismatch')
    chunks, failures = [], []
    counts = Counter()
    position = 0
    for reduced, planned in zip(state['chunks'], plan['chunks']):
        identities = planned['identities']
        attempts, by_dataset = [], {}
        for attempt in reduced['attempts']:
            entry = attempt_manifests[position]
            position += 1
            consumer._keys(entry, 'chunk_index attempt manifest', 'manifest entry fields')
            consumer._same([entry['chunk_index'], entry['attempt']],
                           [reduced['chunk_index'], attempt['attempt']], 'manifest attempt/order mismatch')
            terminal = records[attempt['record_sequences'][-1] - 1]
            failed = attempt['status'] in journal.FAILURES
            manifest = entry['manifest']
            rows = None
            if manifest is not None:
                contract.validate_manifest(manifest, plan, entry['chunk_index'], entry['attempt'])
                if manifest['runtime'] is not None:
                    consumer._same(manifest['runtime'], attempt['context']['runtime'],
                                   'manifest/journal runtime mismatch')
                v.require(failed or manifest['state'] == 'complete', 'verified attempt lacks complete manifest')
                rows = _slots(manifest, identities, by_dataset)
                if not failed:
                    consumer._same([{'evaluation_id': r['identity']['evaluation_id'], 'status': r['status']}
                                    for r in rows], terminal['outcome']['slots'], 'manifest/journal outcome mismatch')
            else:
                v.require(failed, 'verified attempt missing manifest')
            item = {**copy.deepcopy(attempt),
                'terminal_record_sha256': journal.record_hash(terminal),
                'manifest_metadata_sha256': None if manifest is None else v.canonical_sha256(manifest),
                'manifest_state': None if manifest is None else manifest['state'],
                'manifest_failure': None if manifest is None else copy.deepcopy(manifest['failure']),
                'evaluation_detail': 'unreported' if rows is None else 'manifest_declaration',
                'evaluations': rows}
            attempts.append(item)
            if failed:
                failures.append({'chunk_index': reduced['chunk_index'], 'attempt': attempt['attempt'],
                    'terminal_record_sha256': item['terminal_record_sha256'],
                    'terminal_record': copy.deepcopy(terminal),
                    'evaluation_detail': item['evaluation_detail']})
        latest = attempts[-1]
        counts.update(row['status'] for row in latest['evaluations'])
        chunks.append({'chunk_index': reduced['chunk_index'], 'identities': copy.deepcopy(identities),
                       'selected_attempt': latest['attempt'], 'attempts': attempts})
    return {'format': FORMAT, 'mode': MODE, 'validation_status': 'checkpoint_metadata_adapted',
        'bindings': {'plan_sha256': expected_plan_sha256, 'record_count': expected_record_count,
                     'head_sha256': expected_head_sha256, 'manifests_metadata_sha256': expected_manifests_sha256},
        'journal_declares_coverage_complete': True, 'declared_complete_chunks': len(chunks),
        'coverage': {s: counts[s] for s in consumer.SLOT_STATES},
        'attempt_count': state['attempt_count'], 'failed_attempt_history': failures, 'chunks': chunks,
        'profile_status_source': 'manifest_slot_status_only',
        'input_bytes_verified': False, 'publication_verified': False, 'producer_exit_verified': False,
        'source_runtime_accepted': False, 'result_trusted': False, 'campaign_completed': False,
        'execution_authorized': False, 'analysis_authorized': False, 'formal_permission': False,
        'promotion_allowed': False, 'independent_s6_complete': False,
        'performance_status': 'not_evaluated', 'selected_candidate': None,
        'next_step': 'authenticate_checkpoint_publications_and_controller_exit'}
