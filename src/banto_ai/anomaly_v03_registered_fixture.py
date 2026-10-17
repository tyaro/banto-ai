"""Pure preformal rehearsal of the registered holdout input inventory.

The only evaluation bytes represented here are deterministic invented markers.
No observation, producer output, process, analysis, or publication is read.
"""
from __future__ import annotations

from collections import Counter
import copy
import hashlib

from . import anomaly_v03 as v
from . import anomaly_v03_consumer_input as metadata
from . import anomaly_v03_consumer_evidence as evidence


FORMAT = 'anomaly-v03-registered-input-fixture-v1'
MODE = 'preformal-fixture'
MAX_MANIFEST = 8 * 1024**2
MAX_REGISTRY = 256 * 1024
MAX_ATTEMPTS = 4  # Parser bound, not permission to retry a campaign.


def _marker(kind: str, name: str) -> str:
    return hashlib.sha256(f'anomaly-v03-invented-{kind}-v1:{name}'.encode('utf-8')).hexdigest()


def _worker(value, state):
    evidence._keys(value, 'exit_confirmed exit_code', 'fixture worker fields')
    v.require(type(value['exit_confirmed']) is bool, 'fixture worker exit flag')
    code = value['exit_code']
    if value['exit_confirmed']:
        v.require(type(code) is int and -(2**31) <= code < 2**32, 'fixture worker exit code')
    else:
        v.require(code is None, 'unconfirmed fixture worker has exit code')
    if state == 'complete':
        evidence._same(value, {'exit_confirmed': True, 'exit_code': 0}, 'complete fixture worker exit')
    if state in ('not_started', 'in_progress'):
        evidence._same(value, {'exit_confirmed': False, 'exit_code': None}, 'unfinished fixture worker exit')


def planned_fixture(registry_pin):
    """Make a fresh 480-chunk declaration; this does not start a run."""
    evidence._pin(registry_pin)
    v.require(0 < registry_pin['bytes'] <= MAX_REGISTRY and
              registry_pin['sha256'] == v.REGISTRY_RAW_SHA256, 'frozen registry pin')
    identities = v.evaluation_inventory('holdout')
    v.require(len(identities) == 2880, 'registered holdout inventory')
    return {'format': FORMAT, 'mode': MODE, 'invented_only': True,
        'registry_pin': copy.deepcopy(registry_pin),
        'producer': {'state': 'not_started', 'failure': None,
                     'worker': {'exit_confirmed': False, 'exit_code': None}},
        'chunks': [{'chunk_index': i // 6, 'identities': identities[i:i+6], 'attempts': []}
                   for i in range(0, len(identities), 6)],
        'coverage': {state: 2880 if state == 'not_started' else 0
                     for state in metadata.SLOT_STATES}}


def validate_fixture(manifest_raw, registry_raw, *, expected_mode,
                     expected_manifest_pin, expected_registry_pin):
    """Verify caller-pinned invented bytes and every registered identity slot.

    Worker exits are fixture declarations. This function cannot authenticate an
    actual process, input observation, or formal analysis result.
    """
    v.require(type(expected_mode) is str and expected_mode == MODE,
              'formal/unknown registered fixture mode is closed')
    evidence._pin(expected_manifest_pin)
    evidence._pin(expected_registry_pin)
    v.require(0 < expected_manifest_pin['bytes'] <= MAX_MANIFEST and
              0 < expected_registry_pin['bytes'] <= MAX_REGISTRY and
              expected_registry_pin['sha256'] == v.REGISTRY_RAW_SHA256,
              'bounded external fixture pins')
    evidence._raw(registry_raw, expected_registry_pin, 'frozen registry bytes')
    registry = v.strict_json(registry_raw)
    v.require(type(registry) is dict and 'seed_registry' in registry,
              'frozen registry structure')
    evidence._same(registry['seed_registry'], v.seed_registry(), 'frozen seed registration')
    evidence._raw(manifest_raw, expected_manifest_pin, 'external fixture manifest bytes')
    manifest = v.strict_json(manifest_raw)
    v.require(manifest_raw == v.canonical_json(manifest), 'canonical fixture manifest bytes')
    evidence._keys(manifest, 'format mode invented_only registry_pin producer chunks coverage',
                   'registered fixture manifest fields')
    evidence._same([manifest['format'], manifest['mode'], manifest['invented_only'],
                    manifest['registry_pin']],
                   [FORMAT, MODE, True, expected_registry_pin], 'fixture identity and registry pin')

    expected = planned_fixture(expected_registry_pin)
    chunks = manifest['chunks']
    v.require(type(chunks) is list and len(chunks) == 480, 'all registered chunks required')
    coverage = Counter()
    complete_chunks = 0
    history = []
    attempt_count = 0
    for chunk, wanted in zip(chunks, expected['chunks']):
        evidence._keys(chunk, 'chunk_index identities attempts', 'fixture chunk fields')
        evidence._same([chunk['chunk_index'], chunk['identities']],
                       [wanted['chunk_index'], wanted['identities']],
                       'registered chunk identity and order')
        attempts = chunk['attempts']
        v.require(type(attempts) is list and len(attempts) <= MAX_ATTEMPTS,
                  'bounded fixture attempt history')
        current = Counter({'not_started': 6})
        by_dataset = {}
        for number, entry in enumerate(attempts, 1):
            evidence._keys(entry, 'record worker', 'fixture attempt fields')
            record = entry['record']
            current = metadata._attempt(record, wanted['identities'], number, by_dataset)
            state = record['state']
            _worker(entry['worker'], state)
            if number < len(attempts):
                v.require(state == 'failed', 'retry without failed fixture attempt')
                v.require(record['failure']['reason'] not in metadata.INTEGRITY_REASONS,
                          'retry after fixture integrity failure')
            for slot in record['evaluations']:
                hashes = slot['input_hashes']
                if hashes is not None:
                    for kind in metadata.INPUT_HASHES:
                        v.require(hashes[kind] == _marker('input',
                                  slot['identity']['dataset_id'] + ':' + kind),
                                  'noninvented fixture input marker')
                if slot['evaluation_sha256'] is not None:
                    v.require(slot['evaluation_sha256'] == _marker('evaluation',
                              slot['identity']['evaluation_id']),
                              'noninvented fixture evaluation marker')
            if state == 'failed':
                history.append({'chunk_index': wanted['chunk_index'], 'attempt': number,
                    'failure': copy.deepcopy(record['failure']),
                    'is_latest': number == len(attempts)})
        coverage.update(current)
        attempt_count += len(attempts)
        complete_chunks += bool(attempts and attempts[-1]['record']['state'] == 'complete')

    counts = {state: coverage[state] for state in metadata.SLOT_STATES}
    evidence._same(manifest['coverage'], counts, 'fixture coverage derives from latest attempts')
    v.require(sum(counts.values()) == 2880, 'all registered evaluation slots retained')
    producer = manifest['producer']
    evidence._keys(producer, 'state failure worker', 'fixture producer fields')
    state = producer['state']
    v.require(type(state) is str and state in ('not_started', 'in_progress', 'complete', 'failed'),
              'fixture producer state')
    metadata._failure(state, producer['failure'])
    _worker(producer['worker'], state)
    if state == 'not_started':
        v.require(attempt_count == 0, 'unstarted fixture producer has attempts')
    if state == 'complete':
        v.require(complete_chunks == 480, 'complete fixture producer has unfinished chunks')
    return {'format': 'anomaly-v03-registered-input-fixture-check-v1',
        'status': 'fixture_inventory_complete' if state == 'complete' else 'fixture_inventory_incomplete',
        'mode': MODE, 'registry_pin': copy.deepcopy(expected_registry_pin),
        'manifest_pin': copy.deepcopy(expected_manifest_pin),
        'planned_chunks': 480, 'planned_evaluations': 2880,
        'declared_complete_chunks': complete_chunks, 'coverage': counts,
        'attempt_count': attempt_count, 'failed_attempt_history': history,
        'fixture_marker_hashes_checked': True,
        'supplied_manifest_and_registry_bytes_verified': True,
        'producer_worker_exit_declared': producer['worker']['exit_confirmed'],
        'actual_worker_exit_authenticated': False, 'registered_observations_read': False,
        'registered_input_bytes_verified': False, 'campaign_evaluations_credited': 0,
        'analysis_authorized': False, 'formal_permission': False,
        'promotion_allowed': False, 'independent_s6_complete': False}
