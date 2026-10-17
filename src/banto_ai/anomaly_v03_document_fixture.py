"""Pure 40-cluster wiring rehearsal, never a formal result or an IO consumer.

Only invented, explicitly numbered clusters and at most 64 caller-supplied
draws are accepted. The ten-field document draft leaves unavailable evidence
as None, so it cannot pass the formal result contract. Fixture selection lives
inside the draft/packet; actual selection and all acceptance flags stay closed.
"""
from __future__ import annotations

import copy

from . import anomaly_v03 as contract
from . import anomaly_v03_analysis_adapter as adapter

I = adapter.inference
FORMAT = 'anomaly-v03-document-fixture-input-v1'
OUTPUT_FORMAT = 'anomaly-v03-document-fixture-v1'
IDS = tuple(f'invented-{index:02d}' for index in range(40))
FIELDS = ('schema_version', 'status', 'provenance', 'result_type',
          'analysis_consumer', 'bootstrap', 'candidate_tables', 'slices',
          'selected_candidate', 'decision')
PENDING = ('status', 'provenance', 'analysis_consumer', 'bootstrap', 'slices')
CLOSED = {'formal_permission': False, 'formal_document_emitted': False,
          'formal_document_validated': False, 'promotion_allowed': False,
          'independent_s6_complete': False, 'result_trusted': False,
          'performance_status': 'not_evaluated', 'selected_candidate': None,
          'campaign_evaluations_credited': 0, 'registered_data_read': False,
          'formal_bootstrap_performed': False}


def _schema(schema):
    # No disk reads; reject a caller's relaxed/replaced analysis schema.
    I.exact(schema, contract.schemas(contract._expected_configs())[7],
            'fixed analysis schema')
    I.exact(schema['required'], list(FIELDS), 'ten document fields')


def _fields(value, expected, message):
    I.need(type(value) is dict and set(value) == set(expected), message)


def _draws(draws):
    I.need(type(draws) is list and 1 <= len(draws) <= 64, '1..64 invented draws')
    for draw in draws:
        I.need(type(draw) is list and len(draw) == 40, '40 indices per draw')
        I.need(all(type(index) is int and 0 <= index < 40 for index in draw),
               'invented draw index domain')


def _input(value):
    _fields(value, ('format', 'invented_only', 'clusters', 'diagnostics',
                    'draws', 'engineering_ready_assumption'), 'fixture input fields')
    I.exact(value['format'], FORMAT, 'fixture input identity')
    I.exact(value['invented_only'], True, 'invented-only assertion')
    I.need(type(value['engineering_ready_assumption']) is bool,
           'exact fixture engineering assumption')
    clusters = value['clusters']
    I.need(type(clusters) is list and len(clusters) == 40, 'exactly 40 invented clusters')
    for cluster, identifier in zip(clusters, IDS):
        _fields(cluster, ('cluster_id', 'candidates'), 'fixture cluster fields')
        I.exact(cluster['cluster_id'], identifier, 'ordered invented cluster IDs')
    _draws(value['draws'])
    contract.json_value(value)
    # The existing adapter checks pairing, counts, exposure, detected-only
    # delays and twelve-layout denominators before any inference computation.


def _draft(packet):
    prepared = {'schema_version': '0.3', 'result_type': 'anomaly-multiseed-analysis-v03',
                'candidate_tables': copy.deepcopy(packet['fixture_candidate_tables']),
                'selected_candidate': packet['fixture_selected_candidate'],
                'decision': packet['fixture_decision']}
    return {field: prepared.get(field) for field in FIELDS}


def _coverage():
    reasons = {
        'status': 'formal run and engineering acceptance are not supplied',
        'provenance': 'formal producer source and publication inventory are not supplied',
        'analysis_consumer': 'clean source/runtime acceptance is not supplied',
        'bootstrap': 'registered 50000-replicate computation was not performed',
        'slices': 'complete formal slice inventory and derivation are not supplied',
    }
    return [{'field': field,
             'state': 'missing_evidence' if field in PENDING else 'fixture_value_only',
             'reason': reasons.get(field, 'mapped for wiring checks, not accepted run evidence')}
            for field in FIELDS]


def validate_fixture_document(value, schema):
    """Validate mapping/claims without recomputing CIs or trusting source bytes.

    This is structural and arithmetic validation of reported fixture values;
    the input digest is a reference, not authentication of a registered run.
    """
    _schema(schema)
    _fields(value, ('format', 'input_canonical_sha256', 'fixture_draws',
                    'fixture_packet', 'document_draft', 'field_coverage',
                    'formal_requirements', *CLOSED), 'fixture document fields')
    contract.json_value(value)
    I.exact(value['format'], OUTPUT_FORMAT, 'fixture output identity')
    for name, expected in CLOSED.items():
        I.exact(value[name], expected, 'closed fixture boundary: '+name)
    digest = value['input_canonical_sha256']
    I.need(type(digest) is str and len(digest) == 64 and
           all(c in '0123456789abcdef' for c in digest), 'input canonical digest')
    draws = value['fixture_draws']
    _draws(draws)
    packet = value['fixture_packet']
    adapter.validate_fixture_packet(packet, schema)
    I.exact(packet['fixture_draws'], {'clusters': 40, 'replicates': len(draws)},
            'actual fixture draw dimensions')
    I.exact(value['document_draft'], _draft(packet), 'document/packet field mapping')
    I.exact(value['field_coverage'], _coverage(), 'complete field coverage')
    I.exact(value['formal_requirements'], {'clusters': 40, 'replicates': 50000,
            'missing_fields': list(PENDING), 'ready': False}, 'formal evidence still missing')
    return {'status': 'fixture_document_mapping_valid', 'clusters': 40,
            'replicates': len(draws), 'tables': 9, 'gates': 180,
            'mapped_fields': 5, 'missing_fields': list(PENDING),
            'formal_document_validated': False, 'inference_recomputed': False}


def build_fixture_document(value, schema):
    """Wire invented inputs through existing inference and document assembly.

    One draw is applied to all candidates and both strata, retaining cluster
    pairing. The bound is intentionally much smaller than formal 50000 draws.
    No file, subprocess, observation generation, publication or runtime IO.
    Caller-owned input/schema are never modified; output has no aliases to them.
    """
    _schema(schema)
    _input(value)
    packet = adapter.compute_fixture_packet(value['clusters'], value['draws'],
        value['diagnostics'], schema,
        engineering_ready=value['engineering_ready_assumption'])
    result = {'format': OUTPUT_FORMAT,
              'input_canonical_sha256': contract.canonical_sha256(value),
              'fixture_draws': copy.deepcopy(value['draws']), 'fixture_packet': packet,
              'document_draft': _draft(packet), 'field_coverage': _coverage(),
              'formal_requirements': {'clusters': 40, 'replicates': 50000,
                                      'missing_fields': list(PENDING), 'ready': False},
              **CLOSED}
    validate_fixture_document(result, schema)
    return result
