"""Pure metadata preflight for fixture and engineering consumer inputs.

No files, paths, runtime probes, observation/score/inference or publication IO.
An external canonical digest binds a declaration, never its evidence bytes or
execution authenticity. A complete declaration does not authorize analysis.
"""
from __future__ import annotations

import copy
import re
from collections import Counter

from . import anomaly_v03 as v
from . import _anomaly_v03_contract as c

FORMAT = 'anomaly-v03-consumer-input-metadata-v1'
MODES = ('fixture', 'engineering-dev-smoke')
SLOT_STATES = ('success', 'inconclusive', 'partial', 'failed', 'not_started')
FAILURE_STAGES = ('input', 'compute', 'publication', 'supervision', 'verification')
FAILURE_REASONS = ('exception', 'worker_exit', 'resource_limit', 'interrupted',
                   'hash_mismatch', 'source_mismatch', 'runtime_changed', 'verification_failed')
INTEGRITY_REASONS = ('hash_mismatch', 'source_mismatch', 'runtime_changed')
INPUT_HASHES = ('observations', 'events', 'quality_mask', 'split', 'origins', 'targets')
MAX_ATTEMPTS = 64  # Metadata size limit only; not a retry or runtime allowance.


def _mode(mode):
    v.require(type(mode) is str and mode in MODES, 'unsupported consumer mode; formal input is closed')


def _keys(value, fields, message):
    v.require(type(value) is dict and set(value) == set(fields.split()), message)


def _same(value, expected, message):
    v.require(v.canonical_json(value) == v.canonical_json(expected), message)


def _digest(value):
    v.require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value), 'invalid digest')


def _inventory(mode):
    _mode(mode)
    if mode == 'engineering-dev-smoke':
        return v.evaluation_inventory('dev') + v.evaluation_inventory('smoke')
    rows = []
    pair = 'consumer-fixture-00'
    for layer in c.STRATA:
        dataset = pair + '-' + layer
        for candidate in c.CANDIDATES:
            rows.append({'role': 'fixture', 'seed': 0, 'layout': 0, 'stratum': layer,
                'candidate_id': candidate, 'pair_id': pair, 'dataset_id': dataset,
                'evaluation_id': dataset + '-' + candidate})
    return rows


def planned_input(mode):
    """Fresh, not-started declarations: one invented pair or all 120 dev/smoke pairs."""
    identities = _inventory(mode)
    return {'format': FORMAT, 'mode': mode,
        'policy_id': 'anomaly-v03-consumer-fixture-v1' if mode == 'fixture' else 'anomaly-v03-single-writer-v1',
        'registry_raw_sha256': None if mode == 'fixture' else v.REGISTRY_RAW_SHA256,
        'producer': {'state': 'not_started', 'writer_exited': False, 'failure': None,
                     'receipt_sha256': None, 'marker_sha256': None},
        'chunks': [{'chunk_index': i // 6, 'identities': identities[i:i+6], 'attempts': []}
                   for i in range(0, len(identities), 6)],
        'coverage': {state: len(identities) if state == 'not_started' else 0 for state in SLOT_STATES}}


def _slot(slot, identity):
    _keys(slot, 'identity status profile_status input_hashes evaluation_sha256', 'evaluation fields')
    _same(slot['identity'], identity, 'evaluation identity/order mismatch')
    state, profile = slot['status'], slot['profile_status']
    v.require(type(state) is str and state in SLOT_STATES, 'evaluation status')
    v.require(type(profile) is str and profile in ('not_evaluated', 'calibrated', 'inconclusive'), 'profile status')
    hashes, result = slot['input_hashes'], slot['evaluation_sha256']
    if hashes is not None:
        _keys(hashes, ' '.join(INPUT_HASHES), 'input hash fields')
        for digest in hashes.values():
            _digest(digest)
    if result is not None:
        _digest(result)
    v.require(profile == 'not_evaluated' or hashes is not None, 'profile declaration without input pins')
    if state in ('success', 'inconclusive'):
        v.require(profile == ('calibrated' if state == 'success' else 'inconclusive'), 'outcome/profile mismatch')
        v.require(hashes is not None and result is not None, 'completed evaluation missing input/result pins')
    elif state == 'not_started':
        v.require(profile == 'not_evaluated' and hashes is None and result is None, 'not-started evaluation has evidence')
    else:
        # Partial bytes belong in the failure evidence, not a complete evaluation.
        v.require(result is None, 'failed/partial evaluation claims complete result')
    return state


def _failure(state, failure):
    if state == 'failed':
        _keys(failure, 'stage reason evidence_sha256', 'failed state needs failure record')
        v.require(type(failure['stage']) is str and failure['stage'] in FAILURE_STAGES, 'failure stage')
        v.require(type(failure['reason']) is str and failure['reason'] in FAILURE_REASONS, 'failure reason')
        if failure['evidence_sha256'] is not None:
            _digest(failure['evidence_sha256'])
    else:
        v.require(failure is None, 'nonfailed state has failure record')


def _attempt(attempt, identities, number, by_dataset):
    _keys(attempt, 'attempt state failure evaluations', 'attempt fields')
    v.require(type(attempt['attempt']) is int and attempt['attempt'] == number, 'attempt sequence')
    state = attempt['state']
    v.require(type(state) is str and state in ('in_progress', 'complete', 'failed'), 'attempt state')
    _failure(state, attempt['failure'])
    rows = attempt['evaluations']
    v.require(type(rows) is list and len(rows) == 6, 'six ordered evaluation slots required')
    counts = Counter()
    for row, identity in zip(rows, identities):
        counts[_slot(row, identity)] += 1
        hashes = row['input_hashes']
        if hashes is not None:
            dataset = identity['dataset_id']
            if dataset in by_dataset:
                _same(hashes, by_dataset[dataset], 'candidate/retry input pins differ')
            by_dataset[dataset] = hashes
    if state == 'complete':
        v.require(counts['success'] + counts['inconclusive'] == 6, 'complete attempt has unfinished evaluation')
    if state == 'in_progress':
        v.require(not counts['failed'], 'failed evaluation requires failed attempt')
    return counts


def validate_input(value, *, expected_mode, expected_sha256):
    """Check decoded declarations against a caller-retained canonical SHA-256.

    No callback or implicit file access. Formal/unknown mode is rejected before
    identity expansion or digest traversal. Failed attempts remain present and
    known input pins must agree across retries; no retry is authorized here.
    """
    _mode(expected_mode)
    _keys(value, 'format mode policy_id registry_raw_sha256 producer chunks coverage', 'consumer input fields')
    _mode(value['mode'])
    v.require(value['mode'] == expected_mode, 'caller/input mode mismatch')
    _digest(expected_sha256)
    expected = planned_input(expected_mode)
    for field in ('format', 'policy_id', 'registry_raw_sha256'):
        _same(value[field], expected[field], 'consumer contract binding: ' + field)
    producer = value['producer']
    _keys(producer, 'state writer_exited receipt_sha256 marker_sha256 failure', 'producer fields')
    state = producer['state']
    v.require(type(state) is str and state in ('not_started', 'in_progress', 'complete', 'failed'), 'producer state')
    v.require(type(producer['writer_exited']) is bool, 'writer exit declaration must be boolean')
    _failure(state, producer['failure'])
    for name in ('receipt_sha256', 'marker_sha256'):
        if producer[name] is not None:
            _digest(producer[name])
    v.require((producer['receipt_sha256'] is None) == (producer['marker_sha256'] is None), 'partial publication references')
    chunks = value['chunks']
    v.require(type(chunks) is list and len(chunks) == len(expected['chunks']), 'complete planned chunk inventory required')
    total = Counter(); completed = 0; attempt_count = 0; history = []
    for row, wanted in zip(chunks, expected['chunks']):
        _keys(row, 'chunk_index identities attempts', 'chunk fields')
        v.require(type(row['chunk_index']) is int and row['chunk_index'] == wanted['chunk_index'], 'chunk order/index mismatch')
        _same(row['identities'], wanted['identities'], 'planned identities/order mismatch')
        attempts = row['attempts']
        v.require(type(attempts) is list and len(attempts) <= MAX_ATTEMPTS, 'attempt history bound')
        current = Counter({'not_started': 6}); by_dataset = {}
        for index, attempt in enumerate(attempts):
            current = _attempt(attempt, wanted['identities'], index + 1, by_dataset)
            if index < len(attempts) - 1:
                v.require(attempt['state'] == 'failed', 'retry without failed prior attempt')
                v.require(attempt['failure']['reason'] not in INTEGRITY_REASONS, 'retry after integrity failure')
            if attempt['state'] == 'failed':
                history.append({'chunk_index': row['chunk_index'], 'attempt': index + 1,
                    'failure': copy.deepcopy(attempt['failure']), 'is_latest': index == len(attempts) - 1})
        total.update(current)
        attempt_count += len(attempts)
        completed += bool(attempts and attempts[-1]['state'] == 'complete')
    coverage = {name: total[name] for name in SLOT_STATES}
    _same(value['coverage'], coverage, 'declared coverage differs from latest attempts')
    all_complete = completed == len(chunks)
    if state == 'not_started':
        v.require(attempt_count == 0 and producer == expected['producer'], 'not-started producer has execution declarations')
    elif state == 'in_progress':
        v.require(not producer['writer_exited'] and producer['marker_sha256'] is None, 'in-progress producer claims final publication')
    elif state == 'complete':
        v.require(all_complete and producer['writer_exited'] and producer['receipt_sha256'] is not None,
                  'complete producer lacks coverage, exit or publication references')
    # Failed supervision may follow a valid marker; retain both, never retract it.
    _same(v.canonical_sha256(value), expected_sha256, 'external metadata digest mismatch')
    declared_complete = state == 'complete'
    next_step = ('authenticate_input_bytes' if declared_complete else
                 'wait_for_writer' if state == 'in_progress' else 'review_incomplete_declaration')
    return {'format': 'anomaly-v03-consumer-input-check-v1', 'validation_status': 'metadata_contract_valid',
        'mode': expected_mode, 'metadata_sha256': expected_sha256, 'metadata_digest_matches_expected': True,
        'declared_run_state': state, 'declared_complete': declared_complete, 'planned_chunks': len(chunks),
        'producer_failure': copy.deepcopy(producer['failure']),
        'declared_complete_chunks': completed, 'coverage': coverage, 'attempt_count': attempt_count,
        'failed_attempt_history': history, 'next_step': next_step,
        'input_bytes_verified': False, 'source_runtime_accepted': False, 'result_trusted': False,
        'execution_authorized': False, 'analysis_authorized': False, 'formal_permission': False,
        'promotion_allowed': False, 'independent_s6_complete': False,
        'performance_status': 'not_evaluated', 'selected_candidate': None}
