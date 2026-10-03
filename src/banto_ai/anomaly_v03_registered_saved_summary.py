"""Read supplied saved bytes into a registered, preformal chunk candidate.

The current on-disk saved reader is specific to completed dev/smoke campaigns.
This pure boundary does not invoke it, follow report paths, or promote its output
to the registered holdout. Payload names are logical receipt keys, not physical
paths in the current saved run. A caller must retain independent raw-byte pins.
Even matching saved bytes do not prove observation-to-summary derivation or execution.
"""
from __future__ import annotations

import copy

from . import anomaly_v03 as v
from . import anomaly_v03_consumer_evidence as evidence
from . import anomaly_v03_consumer_input as metadata
from . import anomaly_v03_producer_input_fixture as primary
from . import anomaly_v03_producer_slice_fixture as compact
from . import anomaly_v03_summary_coverage as coverage


MODE = 'preformal-fixture'
RECEIPT_FORMAT = 'anomaly-v03-registered-saved-chunk-candidate-receipt-v1'
REPORT_FORMAT = 'anomaly-v03-registered-saved-chunk-candidate-report-v1'
OUTPUT_FORMAT = 'anomaly-v03-registered-saved-chunk-candidate-bound-v1'
MAX_REGISTRY = 256 * 1024
MAX_RECEIPT = 512 * 1024
MAX_REPORT = 512 * 1024
MAX_PAYLOAD = 32 * 1024**2
MAX_TOTAL = 128 * 1024**2


def _load(raw, pin, maximum, name, *, canonical=True):
    evidence._pin(pin)
    v.require(type(raw) is bytes and 0 < len(raw) <= maximum, name + ' byte bound')
    evidence._raw(raw, pin, 'external ' + name + ' pin')
    value = v.strict_json(raw)
    if canonical:
        v.require(raw == v.canonical_json(value), 'canonical ' + name + ' bytes')
    return value


def _payload_path(identity, kind=None):
    if kind is None:
        return 'evaluations/' + identity['evaluation_id'] + '.json'
    return 'datasets/' + identity['dataset_id'] + '/' + kind


def bind_saved_chunk_candidate(registry_raw, receipt_raw, report_raw, payloads, *,
                               expected_mode, chunk_index, expected_registry_pin,
                               expected_receipt_pin, expected_report_pin,
                               expected_savepoint_pin, expected_payload_pins):
    """Verify one supplied chunk's latest slots and actual pinned payload bytes.

    A successful call is a byte/identity candidate only. The report's numeric
    values are not recomputed from observations, and this fixture-only API cannot
    authenticate a saved reader process or open the formal campaign gate.
    """
    v.require(type(expected_mode) is str and expected_mode == MODE,
              'formal/unknown registered saved mode is closed')
    v.require(type(chunk_index) is int and 0 <= chunk_index < 480,
              'registered chunk index')
    evidence._pin(expected_registry_pin)
    v.require(0 < expected_registry_pin['bytes'] <= MAX_REGISTRY and
              expected_registry_pin['sha256'] == v.REGISTRY_RAW_SHA256,
              'frozen registry pin')
    registry = _load(registry_raw, expected_registry_pin, MAX_REGISTRY,
                     'registry', canonical=False)
    v.require(type(registry) is dict and 'seed_registry' in registry,
              'frozen registry structure')
    evidence._same(registry['seed_registry'], v.seed_registry(), 'frozen seed registry')
    evidence._pin(expected_savepoint_pin)
    v.require(expected_savepoint_pin['bytes'] > 0, 'nonempty saved source anchor')
    receipt = _load(receipt_raw, expected_receipt_pin, MAX_RECEIPT, 'receipt')
    evidence._keys(receipt,
        'format mode invented_only registry_pin savepoint_pin chunk_index attempts',
        'registered saved candidate receipt fields')
    for key, expected in {'format': RECEIPT_FORMAT, 'mode': MODE, 'invented_only': True,
                          'registry_pin': expected_registry_pin,
                          'savepoint_pin': expected_savepoint_pin,
                          'chunk_index': chunk_index}.items():
        evidence._same(receipt[key], expected, 'receipt binding ' + key)
    identities = v.evaluation_inventory('holdout')[chunk_index*6:chunk_index*6+6]
    v.require(len(identities) == 6, 'six registered holdout identities')
    attempts = receipt['attempts']
    v.require(type(attempts) is list and len(attempts) <= 4, 'bounded attempt history')
    dataset_hashes = {}
    for number, attempt in enumerate(attempts, 1):
        metadata._attempt(attempt, identities, number, dataset_hashes)
        if number < len(attempts):
            v.require(attempt['state'] == 'failed', 'retry without failed prior attempt')
            v.require(attempt['failure']['reason'] not in metadata.INTEGRITY_REASONS,
                      'retry after integrity failure')
    latest = attempts[-1] if attempts else None
    selected = [slot for slot in latest['evaluations']
                if slot['status'] in ('success', 'inconclusive')] if latest else []
    v.require(type(payloads) is dict and type(expected_payload_pins) is dict,
              'explicit saved payload inventories')
    if not selected:
        v.require(report_raw is None and expected_report_pin is None and
                  not payloads and not expected_payload_pins,
                  'no latest result may consume saved summary bytes')
        return {'format': OUTPUT_FORMAT, 'mode': MODE, 'status': 'no_latest_saved_rows',
                'chunk_index': chunk_index, 'latest_attempt': latest['attempt'] if latest else None,
                'latest_state': latest['state'] if latest else 'not_started',
                'latest_rows_bound': 0, 'receipt_pin': copy.deepcopy(expected_receipt_pin),
                'report_pin': None, 'payload_pins': {},
                'failed_attempts': sum(a['state'] == 'failed' for a in attempts),
                **_closed(False)}

    report = _load(report_raw, expected_report_pin, MAX_REPORT, 'report')
    evidence._keys(report,
        'format mode invented_only registry_pin receipt_pin savepoint_pin '
        'chunk_index attempt rows payload_pins',
        'registered saved candidate report fields')
    for key, expected in {'format': REPORT_FORMAT, 'mode': MODE, 'invented_only': True,
                          'registry_pin': expected_registry_pin,
                          'receipt_pin': expected_receipt_pin,
                          'savepoint_pin': expected_savepoint_pin,
                          'chunk_index': chunk_index, 'attempt': latest['attempt']}.items():
        evidence._same(report[key], expected, 'report binding ' + key)
    rows = report['rows']
    v.require(type(rows) is list and len(rows) == len(selected),
              'exact latest saved summary rows')
    pins = report['payload_pins']
    v.require(type(pins) is dict and set(pins) == set(payloads) == set(expected_payload_pins),
              'exact saved payload inventories')
    required = {_payload_path(slot['identity']) for slot in selected}
    required.update(_payload_path(slot['identity'], kind)
                    for slot in selected for kind in metadata.INPUT_HASHES)
    v.require(set(pins) == required, 'registered saved payload inventory')
    v.require(all(type(raw) is bytes for raw in payloads.values()),
              'saved payload bytes required')
    v.require(len(report_raw) + len(receipt_raw) + len(registry_raw) +
              sum(len(raw) for raw in payloads.values()) <= MAX_TOTAL,
              'combined saved payload byte bound')
    for name, raw in payloads.items():
        v.safe_relative_path(name)
        evidence._pin(pins[name]); evidence._pin(expected_payload_pins[name])
        evidence._same(pins[name], expected_payload_pins[name],
                       'independent saved payload pin ' + name)
        v.require(type(raw) is bytes and 0 < len(raw) <= MAX_PAYLOAD,
                  'saved payload byte bound')
        evidence._raw(raw, pins[name], 'saved payload bytes ' + name)

    for row, slot in zip(rows, selected):
        evidence._keys(row,
            'identity evaluation_outcome evaluation_pin input_hashes primary slices',
            'saved summary row fields')
        identity = slot['identity']
        evidence._same(row['identity'], identity, 'registered saved identity/order')
        evidence._same(row['evaluation_outcome'], slot['status'],
                       'latest saved outcome')
        evidence._same(row['input_hashes'], slot['input_hashes'],
                       'latest saved input hashes')
        evaluation_path = _payload_path(identity)
        evidence._same(row['evaluation_pin'], pins[evaluation_path],
                       'saved evaluation pin')
        evidence._same(pins[evaluation_path]['sha256'], slot['evaluation_sha256'],
                       'latest saved evaluation digest')
        evaluation = v.strict_json(payloads[evaluation_path])
        v.require(type(evaluation) is dict and
                  {'identity', 'input_hashes'} <= set(evaluation),
                  'saved evaluation payload fields')
        evidence._same(evaluation['identity'], identity,
                       'saved evaluation payload identity')
        evidence._same(evaluation['input_hashes'], slot['input_hashes'],
                       'saved evaluation payload input hashes')
        for kind in metadata.INPUT_HASHES:
            evidence._same(pins[_payload_path(identity, kind)]['sha256'],
                           slot['input_hashes'][kind],
                           'saved dataset input digest ' + kind)
        v.require(type(row['primary']) is dict and
                  set(row['primary']) == {'counts', 'effective_clean_seconds',
                                          'delay_histogram'},
                  'saved primary summary fields')
        summary = {'format': primary.SUMMARY_FORMAT, 'mode': 'fixture',
                   'invented_only': True, 'registration_pin': expected_registry_pin,
                   'identity': identity, 'attempt': latest['attempt'],
                   'input_hashes': slot['input_hashes'],
                   'profile_status': slot['profile_status'],
                   **row['primary']}
        primary._summary(summary, slot, latest['attempt'], expected_registry_pin)
        raw_slice = row['slices']
        template = compact.S.empty_counts()
        compact.connection._raw_shape(raw_slice, template)
        raw_slice = coverage._ordered_counts(raw_slice, template)
        evidence._same(raw_slice['evaluations'], 1, 'one saved slice evaluation')
        compact._check(raw_slice, summary)

    return {'format': OUTPUT_FORMAT, 'mode': MODE,
            'status': 'latest_chunk_saved_bytes_bound' if latest['state'] == 'complete'
                      else 'latest_chunk_saved_bytes_partial',
            'chunk_index': chunk_index, 'latest_attempt': latest['attempt'],
            'latest_state': latest['state'], 'latest_rows_bound': len(rows),
            'receipt_pin': copy.deepcopy(expected_receipt_pin),
            'report_pin': copy.deepcopy(expected_report_pin),
            'payload_pins': copy.deepcopy(expected_payload_pins),
            'failed_attempts': sum(a['state'] == 'failed' for a in attempts),
            **_closed(True)}


def _closed(bytes_checked):
    return {'saved_payload_bytes_verified': bytes_checked,
            'external_report_bytes_verified': bytes_checked,
            'scope': 'supplied-registered-format-raw-byte-fixture',
            'source_savepoint_bytes_verified': False,
            'reader_result_provenance_authenticated': False,
            'observation_to_summary_recomputed': False,
            'actual_worker_exit_authenticated': False,
            'registered_observations_read': False,
            'real_saved_chunk_reader_used': False,
            'registered_input_bytes_verified': False,
            'campaign_evaluations_credited': 0,
            'formal_permission': False, 'analysis_authorized': False,
            'promotion_allowed': False, 'independent_s6_complete': False,
            'clusters': None, 'diagnostics': None, 'slice_source': None}
