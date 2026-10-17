"""Pure five-payload rehearsal with caller-retained fixture evidence.

No IO, process launch, inference computation, publication or formal result.
Expected pins/launch records must be held independently by the caller. Matching
invented bytes cannot establish execution, provenance, or numerical independence.
"""
from __future__ import annotations

import copy
import hashlib
from collections import Counter

from . import anomaly_v03_consumer_evidence as evidence
from . import anomaly_v03_consumer_input as inputs
from . import anomaly_v03_slice_fixture as slices

v = evidence.v
document = slices.document
FORMAT = 'anomaly-v03-wrapper-fixture-input-v1'
OUTPUT_FORMAT = 'anomaly-v03-wrapper-fixture-v1'
COVERAGE_FORMAT = 'anomaly-v03-wrapper-fixture-coverage-v1'
OPERATION = 'assemble-invented-document-v1'
PAYLOADS = ('execution.json', 'coverage.json', 'analysis.json',
            'diagnostics.json', 'verification.json')
CLOSED = {**document.CLOSED, **evidence.CLOSED, 'published': False,
          'independent_numerical_audit_performed': False,
          'numerical_analysis_performed': False}


def _pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def operation_descriptor(revision):
    """Describe a fixture operation, never a launch or revision attestation."""
    evidence._digest(revision, 40)
    return {'format': 'anomaly-v03-wrapper-fixture-operation-v1', 'mode': 'fixture',
            'operation': OPERATION, 'source_revision': revision}


def _coverage(value, fixture_input):
    evidence._keys(value, 'format invented_only layout_ids clusters', 'fixture coverage fields')
    evidence._same(value['format'], COVERAGE_FORMAT, 'fixture coverage identity')
    evidence._same(value['invented_only'], True, 'invented coverage only')
    evidence._same(value['layout_ids'], list(range(12)), 'twelve ordered layout IDs')
    rows = value['clusters']
    v.require(type(rows) is list and len(rows) == 40, 'forty coverage clusters')
    counts = Counter({state: 0 for state in inputs.SLOT_STATES})
    for row, cluster in zip(rows, fixture_input['clusters']):
        evidence._keys(row, 'cluster_id candidates', 'coverage cluster fields')
        evidence._same(row['cluster_id'], cluster['cluster_id'], 'coverage cluster identity/order')
        evidence._keys(row['candidates'], ' '.join(document.I.CANDIDATES), 'coverage candidates')
        for candidate in document.I.CANDIDATES:
            layers = row['candidates'][candidate]
            evidence._keys(layers, ' '.join(document.I.STRATA[:2]), 'coverage strata')
            for layer in document.I.STRATA[:2]:
                states = layers[layer]
                v.require(type(states) is list and len(states) == 12, 'twelve layout outcomes')
                v.require(all(type(s) is str and s in inputs.SLOT_STATES for s in states),
                          'known fixture slot state')
                counts.update(states)
                if all(s in ('success', 'inconclusive') for s in states):
                    profile = cluster['candidates'][candidate][layer]['profile_status']
                    evidence._same(profile, 'inconclusive' if 'inconclusive' in states else 'calibrated',
                                   'coverage/profile correspondence')
    complete = counts['success'] + counts['inconclusive'] == 2880
    state = ('complete' if complete else 'failed' if counts['failed'] else
             'not_started' if counts['not_started'] == 2880 else 'partial')
    return {'planned_evaluations': 2880, 'clusters': 40, 'layouts': 12,
            'counts': dict(counts), 'state': state, 'complete': complete,
            'scope': 'invented-declarations-only'}


def _payload(kind, **values):
    return {'format': 'anomaly-v03-'+kind+'-wrapper-fixture-v1', 'mode': 'fixture',
            'invented_only': True, **values, **CLOSED}


def _ordered_slice_input(source):
    # JSON object member order is not semantic. The older slice validator uses
    # fixed insertion order when deriving row lists, so restore that order at
    # this new boundary without changing values, arrays or canonical input pins.
    def ordered(value, template):
        if type(template) is dict:
            document._fields(value, template, 'slice count fields')
            return {key: ordered(value[key], item) for key, item in template.items()}
        return copy.deepcopy(value)

    template = slices.slices.empty_counts()
    rows = []
    for row in source['clusters']:
        evidence._keys(row['candidates'], ' '.join(document.I.CANDIDATES), 'slice candidate fields')
        candidates = {}
        for candidate in document.I.CANDIDATES:
            layers = row['candidates'][candidate]
            evidence._keys(layers, ' '.join(document.I.STRATA[:2]), 'slice stratum fields')
            candidates[candidate] = {layer: ordered(layers[layer], template) for layer in document.I.STRATA[:2]}
        rows.append({'cluster_id': row['cluster_id'], 'candidates': candidates})
    return {'format': source['format'], 'invented_only': source['invented_only'], 'clusters': rows}


def assemble_fixture_wrapper(request, schema, *, expected_mode, expected_revision,
                             expected_input_pins, analysis_record=None,
                             expected_analysis=None, source_snapshots=None,
                             runtime_snapshots=None):
    """Assemble five JSON values; no paths or files are opened.

    expected_input_pins binds canonical bytes of input/slices/coverage/operation.
    expected_analysis contains evidence_pin and invocation retained by the caller;
    it is NOT derived from analysis_record. Snapshots are supplied byte mappings.
    Only analysis evidence for OPERATION is connected here. Producer/audit/writer/
    reader execution remains unsupplied, and formal document fields stay null.

    An incomplete coverage can be retained with document=None and no analysis
    evidence. A full fixture document requires complete coverage and bound evidence.
    Inconclusive is a completed evaluation outcome, not a software failure.
    """
    v.require(type(expected_mode) is str and expected_mode == 'fixture',
              'formal/non-fixture wrapper mode is closed')
    operation = operation_descriptor(expected_revision)
    evidence._keys(request, 'format mode invented_only fixture_input slice_input coverage document',
                   'wrapper fixture fields')
    evidence._same(request['format'], FORMAT, 'wrapper fixture identity')
    evidence._same(request['mode'], expected_mode, 'wrapper mode binding')
    evidence._same(request['invented_only'], True, 'invented wrapper only')
    document._schema(schema)
    fixture_input = request['fixture_input']
    document._input(fixture_input)
    document.I._fixture_clusters(fixture_input['clusters'])
    document.adapter._diagnostics(fixture_input['clusters'], fixture_input['diagnostics'])
    source = request['slice_input']
    evidence._keys(source, 'format invented_only clusters', 'slice declaration fields')
    evidence._same(source['format'], slices.INPUT_FORMAT, 'slice declaration identity')
    evidence._same(source['invented_only'], True, 'invented slice declaration only')
    v.require(type(source['clusters']) is list and len(source['clusters']) == 40, 'forty slice declarations')
    for row, identifier in zip(source['clusters'], document.IDS):
        evidence._keys(row, 'cluster_id candidates', 'slice declaration cluster fields')
        evidence._same(row['cluster_id'], identifier, 'slice declaration order')
    coverage = _coverage(request['coverage'], fixture_input)
    raw_inputs = {name: v.canonical_json(value) for name, value in {
        'fixture/input.json': fixture_input, 'fixture/slices.json': source,
        'fixture/coverage.json': request['coverage'], 'fixture/operation.json': operation}.items()}
    evidence._inventory(expected_input_pins)
    evidence._snapshots(raw_inputs, expected_input_pins, 'retained wrapper inputs')
    connected = request['document']
    binding = None
    if connected is None:
        v.require(all(x is None for x in (analysis_record, expected_analysis, source_snapshots, runtime_snapshots)),
                  'no analysis claims without a document')
        check = None
        missing = list(document.FIELDS)
        stage = 'not_supplied' if coverage['complete'] else 'blocked_by_coverage'
    else:
        v.require(coverage['complete'], 'incomplete coverage cannot support a full document')
        evidence._keys(expected_analysis, 'evidence_pin invocation', 'retained analysis expectation required')
        expected = expected_analysis['invocation']
        evidence._expectation(expected)
        evidence._same(expected['source']['revision'], expected_revision, 'analysis revision binding')
        evidence._same(expected['inputs'], expected_input_pins, 'analysis operation/input inventory')
        check = slices.validate_connected_document(connected, fixture_input, _ordered_slice_input(source), schema)
        raw_outputs = {'fixture/document.json': v.canonical_json(connected)}
        binding = evidence.validate_execution_evidence(analysis_record, expected_mode='fixture',
            expected_role='analysis', expected_pin=expected_analysis['evidence_pin'], expected=expected,
            source_snapshots=source_snapshots, runtime_snapshots=runtime_snapshots,
            input_snapshots=raw_inputs, output_snapshots=raw_outputs)
        missing = list(slices.PENDING)
        stage = 'supplied_evidence_bound'
    analysis = _payload('analysis', document_draft=copy.deepcopy(connected['document_draft']) if connected else None,
        fixture_draws=copy.deepcopy(connected['fixture_draws']) if connected else None,
        fixture_packet=copy.deepcopy(connected['fixture_packet']) if connected else None,
        fixture_input_canonical_sha256=connected['input_canonical_sha256'] if connected else None)
    diagnostics = _payload('diagnostics',
        series=copy.deepcopy(connected['diagnostic_series']) if connected else None,
        details=copy.deepcopy(connected['diagnostic_details']) if connected else None,
        slice_input_canonical_sha256=connected['slice_input_canonical_sha256'] if connected else None)
    payloads = {
        'execution.json': _payload('execution', operation=operation, input_pins=copy.deepcopy(expected_input_pins),
            analysis_binding=binding, stages={'producer': 'fixture_declarations_only', 'analysis': stage,
                'writer': 'not_run', 'reader': 'not_run', 'audit': 'not_run'}),
        'coverage.json': _payload('coverage', declarations=copy.deepcopy(request['coverage']), summary=coverage),
        'analysis.json': analysis,
        'diagnostics.json': diagnostics,
        'verification.json': _payload('verification', status='fixture_wrapper_bound' if connected else 'fixture_wrapper_incomplete',
            checks={'coverage': 'declarations_checked', 'document_and_slices': check,
                    'analysis_evidence': 'supplied_bytes_bound' if binding else 'not_supplied'},
            missing_formal_fields=missing, formal_ready=False, inference_recomputed=False),
    }
    # Pins stay outside all payloads, so neither verification nor a future marker
    # contains its own digest. This is a pure descriptor, not a publication marker.
    return {'format': OUTPUT_FORMAT, 'mode': 'fixture', 'invented_only': True,
            'payloads': payloads, 'payload_pins': {n: _pin(v.canonical_json(payloads[n])) for n in PAYLOADS},
            **CLOSED}


def validate_fixture_wrapper(value, request, schema, **expected):
    """Recheck every payload/pin against external inputs without recomputing CIs."""
    rebuilt = assemble_fixture_wrapper(request, schema, **expected)
    evidence._same(value, rebuilt, 'wrapper payload or binding changed')
    return {'status': 'fixture_wrapper_mapping_valid', 'payloads': len(PAYLOADS),
            'missing_formal_fields': rebuilt['payloads']['verification.json']['missing_formal_fields'],
            'inference_recomputed': False, **CLOSED}
