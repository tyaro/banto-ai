"""Project one pinned invented saved-reader result into six aggregate input rows.

This pure boundary checks the saved declarations and their byte pins.  The
caller supplied outer result is a claim about a prior reader, not an
authentication of that process or of the observation bytes.  In particular,
one chunk can never yield a 40-cluster analysis input.
"""
from __future__ import annotations

import copy

from . import anomaly_v03 as v
from . import _anomaly_v03_contract as frozen
from . import anomaly_v03_consumer_evidence as evidence
from . import anomaly_v03_consumer_input as metadata
from . import anomaly_v03_producer_input_fixture as primary
from . import anomaly_v03_producer_slice_fixture as compact
from . import anomaly_v03_registered_saved_summary as saved
from . import anomaly_v03_summary_coverage as coverage


FORMAT = 'anomaly-v03-registered-saved-row-lineage-v1'
OUTER_FORMAT = 'anomaly-v03-preformal-owned-generated-two-role-v1'
READER_FORMAT = 'anomaly-v03-preformal-registered-saved-attempt-fixture-v1'
MAX_OUTER = 64 * 1024


def _load(raw, pin, maximum, label):
    evidence._pin(pin)
    v.require(type(raw) is bytes and 0 < len(raw) <= maximum, label + ' byte bound')
    evidence._raw(raw, pin, 'external ' + label + ' pin')
    value = v.strict_json(raw)
    v.require(raw == v.canonical_json(value), 'canonical ' + label + ' bytes')
    return value


def _outer_reader(outer, receipt_pin, report_pin, chunk_index):
    v.require(type(outer) is dict, 'owned outer result object')
    for name, wanted in {
        'format': OUTER_FORMAT, 'status': 'verified', 'reason': None,
        'owned_fixture_generator_executed': True,
        'owned_fixture_generator_exit_confirmed': True,
        'owned_fixture_reader_executed': True,
        'owned_fixture_reader_exit_confirmed': True,
        'actual_registered_observations_read': False,
        'registered_observations_read': False,
        'registered_seed_consumed': False,
        'campaign_completed': False,
        'formal_permission': False, 'campaign_evaluations_credited': 0,
        'source_closure_complete': False, 'runtime_closure_complete': False,
    }.items():
        evidence._same(outer.get(name), wanted, 'owned outer result ' + name)
    reader = outer.get('reader_result')
    v.require(type(reader) is dict, 'nested reader result object')
    for name, wanted in {
        'format': READER_FORMAT, 'mode': saved.MODE,
        'status': 'latest_chunk_saved_bytes_bound',
        'scope': 'invented-registered-format-actual-attempt-layout-only',
        'fixture_physical_layout': 'run-attempt-result-payload',
        'chunk_index': chunk_index, 'latest_state': 'complete',
        'latest_rows_bound': 6, 'registered_evaluation_contracts_checked': 6,
        'receipt_pin': receipt_pin, 'report_pin': report_pin,
        'saved_payload_bytes_verified': True,
        'external_report_bytes_verified': True,
        'source_savepoint_bytes_verified': True,
        'reported_score_ledger_recomputed': True,
        'reported_score_to_primary_summary_checked': True,
        'reported_score_to_slice_summary_recomputed': True,
        'invented_observation_profile_score_recomputed': True,
        'observation_to_summary_recomputed': True,
        'invented_registered_format_observations_read': True,
        'actual_registered_observations_read': False,
        'registered_observations_read': False,
        'actual_worker_exit_authenticated': False,
        'reader_result_provenance_authenticated': False,
        'real_saved_chunk_reader_used': False,
        'formal_permission': False, 'analysis_authorized': False,
        'promotion_allowed': False, 'independent_s6_complete': False,
        'campaign_evaluations_credited': 0,
        'clusters': None, 'diagnostics': None, 'slice_source': None,
    }.items():
        evidence._same(reader.get(name), wanted, 'nested reader result ' + name)
    return reader


def bind_saved_reader_rows(receipt_raw, report_raw, outer_result_raw, *,
                           chunk_index, expected_receipt_pin,
                           expected_report_pin, expected_outer_result_pin):
    """Normalize six saved invented rows without promoting a partial campaign.

    All three raw JSON values and pins must be retained outside the target
    fixture root.  This does not reopen the 18 payloads; the pinned outer
    reader's semantic claims remain claims, even when internally consistent.
    """
    v.require(type(chunk_index) is int and 0 <= chunk_index < 480,
              'registered chunk index')
    receipt = _load(receipt_raw, expected_receipt_pin, saved.MAX_RECEIPT,
                    'invented receipt')
    report = _load(report_raw, expected_report_pin, saved.MAX_REPORT,
                   'invented report')
    outer = _load(outer_result_raw, expected_outer_result_pin, MAX_OUTER,
                  'owned outer result')
    reader = _outer_reader(outer, expected_receipt_pin, expected_report_pin,
                           chunk_index)

    evidence._keys(receipt,
        'format mode invented_only registry_pin savepoint_pin chunk_index attempts',
        'invented receipt fields')
    for name, wanted in {
        'format': saved.RECEIPT_FORMAT, 'mode': saved.MODE,
        'invented_only': True, 'chunk_index': chunk_index,
    }.items():
        evidence._same(receipt[name], wanted, 'receipt ' + name)
    registry_pin = receipt['registry_pin']
    evidence._pin(registry_pin)
    v.require(0 < registry_pin['bytes'] <= saved.MAX_REGISTRY and
              registry_pin['sha256'] == v.REGISTRY_RAW_SHA256,
              'frozen registry pin')
    evidence._pin(receipt['savepoint_pin'])
    v.require(receipt['savepoint_pin']['bytes'] > 0, 'nonempty invented savepoint pin')
    identities = v.evaluation_inventory('holdout')[chunk_index * 6:chunk_index * 6 + 6]
    v.require(len(identities) == 6, 'six frozen registered identities')
    attempts = receipt['attempts']
    v.require(type(attempts) is list and 1 <= len(attempts) <= 4,
              'bounded invented attempt history')
    by_dataset = {}
    for number, attempt in enumerate(attempts, 1):
        metadata._attempt(attempt, identities, number, by_dataset)
        if number < len(attempts):
            v.require(attempt['state'] == 'failed', 'retry without failed prior attempt')
            v.require(attempt['failure']['reason'] not in metadata.INTEGRITY_REASONS,
                      'retry after integrity failure')
    latest = attempts[-1]
    evidence._same(latest['state'], 'complete', 'latest saved attempt state')
    evidence._same(reader['latest_attempt'], latest['attempt'],
                   'nested reader latest attempt')
    evidence._same(reader['failed_attempts'], sum(a['state'] == 'failed' for a in attempts),
                   'nested reader failed attempt count')

    evidence._keys(report,
        'format mode invented_only registry_pin receipt_pin savepoint_pin '
        'chunk_index attempt rows payload_pins', 'invented report fields')
    for name, wanted in {
        'format': saved.REPORT_FORMAT, 'mode': saved.MODE,
        'invented_only': True, 'registry_pin': registry_pin,
        'receipt_pin': expected_receipt_pin,
        'savepoint_pin': receipt['savepoint_pin'],
        'chunk_index': chunk_index, 'attempt': latest['attempt'],
    }.items():
        evidence._same(report[name], wanted, 'report ' + name)
    rows = report['rows']
    v.require(type(rows) is list and len(rows) == 6, 'six ordered report rows')
    pins = report['payload_pins']
    v.require(type(pins) is dict, 'report payload pins')
    required = {saved._payload_path(identity) for identity in identities}
    required.update(saved._payload_path(identity, kind)
                    for identity in identities for kind in metadata.INPUT_HASHES)
    v.require(set(pins) == required, 'exact report payload pin inventory')
    for name, pin in pins.items():
        v.safe_relative_path(name)
        evidence._pin(pin)
        v.require(0 < pin['bytes'] <= saved.MAX_PAYLOAD, 'bounded payload pin')
    evidence._same(reader.get('payload_pins'), pins, 'nested reader payload pins')
    output_pins = outer.get('generated_output_pins')
    v.require(type(output_pins) is dict, 'owned output pin inventory')
    v.require(set(output_pins) == required | {
        'saved/receipt.json', 'saved/report.json',
        'saved/registry.json', 'saved/savepoint.json'},
        'exact owned output pin inventory')
    for name, pin in pins.items():
        evidence._same(output_pins[name], pin, 'owned output payload pin ' + name)
    for name, pin in {
        'saved/receipt.json': expected_receipt_pin,
        'saved/report.json': expected_report_pin,
        'saved/registry.json': registry_pin,
        'saved/savepoint.json': receipt['savepoint_pin'],
    }.items():
        evidence._same(output_pins[name], pin, 'owned output control pin ' + name)

    seed_ids = v.seed_registry()['entries'][frozen.ROLES.index('holdout')]['seeds']
    seed = identities[0]['seed']
    v.require(seed in seed_ids, 'frozen holdout seed')
    seed_index = seed_ids.index(seed)
    layout = identities[0]['layout']
    v.require(all(identity['seed'] == seed and identity['layout'] == layout
                  for identity in identities), 'one frozen seed/layout per chunk')
    projected = []
    for row, slot in zip(rows, latest['evaluations']):
        identity = slot['identity']
        evidence._keys(row,
            'identity evaluation_outcome evaluation_pin input_hashes primary slices',
            'invented report row fields')
        evidence._same(row['identity'], identity, 'frozen report identity/order')
        evidence._same(row['evaluation_outcome'], slot['status'],
                       'latest report outcome')
        evidence._same(row['input_hashes'], slot['input_hashes'],
                       'latest report input hashes')
        evaluation_pin = pins[saved._payload_path(identity)]
        evidence._same(row['evaluation_pin'], evaluation_pin,
                       'report evaluation pin')
        evidence._same(evaluation_pin['sha256'], slot['evaluation_sha256'],
                       'latest evaluation digest')
        for kind in metadata.INPUT_HASHES:
            evidence._same(pins[saved._payload_path(identity, kind)]['sha256'],
                           slot['input_hashes'][kind], 'latest input digest ' + kind)
        primary_row = row['primary']
        v.require(type(primary_row) is dict and
                  set(primary_row) == {'counts', 'effective_clean_seconds',
                                       'delay_histogram'}, 'primary row fields')
        summary = {'format': primary.SUMMARY_FORMAT, 'mode': 'fixture',
                   'invented_only': True, 'registration_pin': registry_pin,
                   'identity': identity, 'attempt': latest['attempt'],
                   'input_hashes': slot['input_hashes'],
                   'profile_status': slot['profile_status'], **primary_row}
        primary._summary(summary, slot, latest['attempt'], registry_pin)
        raw_slice = row['slices']
        template = compact.S.empty_counts()
        compact.connection._raw_shape(raw_slice, template)
        raw_slice = coverage._ordered_counts(raw_slice, template)
        evidence._same(raw_slice['evaluations'], 1, 'one slice evaluation')
        compact._check(raw_slice, summary)
        projected.append({
            'chunk_index': chunk_index,
            'registered_seed_index': seed_index,
            'invented_cluster_id': f'invented-{seed_index:02d}',
            'identity': copy.deepcopy(identity),
            'attempt': latest['attempt'], 'status': slot['status'],
            'profile_status': slot['profile_status'],
            'input_hashes': copy.deepcopy(slot['input_hashes']),
            'evaluation_pin': copy.deepcopy(evaluation_pin),
            'primary': copy.deepcopy(primary_row), 'slices': copy.deepcopy(raw_slice),
        })
    return {
        'format': FORMAT, 'mode': saved.MODE, 'invented_only': True,
        'status': 'fixture_rows_bound_partial',
        'scope': 'one-pinned-invented-saved-reader-chunk-only',
        'chunk_index': chunk_index, 'latest_attempt': latest['attempt'],
        'receipt_pin': copy.deepcopy(expected_receipt_pin),
        'report_pin': copy.deepcopy(expected_report_pin),
        'outer_result_pin': copy.deepcopy(expected_outer_result_pin),
        'registered_seed_index': seed_index, 'registered_seed': seed,
        'invented_cluster_id': f'invented-{seed_index:02d}',
        'verified_layout': layout, 'verified_layouts_for_seed': 1,
        'planned_layouts_for_seed': 12,
        'verified_chunks': 1, 'planned_chunks': 480,
        'verified_evaluations': 6, 'planned_evaluations': 2880,
        'rows': projected, 'clusters': None, 'diagnostics': None,
        'slice_source': None,
        'receipt_report_outer_bytes_verified': True,
        'owned_reader_result_consistency_checked': True,
        'saved_payload_bytes_rechecked': False,
        'reader_execution_authenticated_here': False,
        'registered_observations_read': False,
        'actual_registered_observations_read': False,
        'campaign_evaluations_credited': 0,
        'formal_permission': False, 'analysis_authorized': False,
        'promotion_allowed': False, 'independent_s6_complete': False,
    }
