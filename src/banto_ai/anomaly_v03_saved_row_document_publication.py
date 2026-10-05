"""Owned local writer and fresh reader for same-budget invented full draws.

The five canonical payloads retain their original bytes plus JSON newline
framing. Workers recheck their pinned arithmetic/input/document bindings and
replay the count/mapping audit, not the 50,000-draw arithmetic. This serialized
platform fixture does not open a registered campaign or claim source closure.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import sys

from . import _anomaly_v03_io as io
from . import anomaly_v03_preformal_contiguous_document_budget as chain
from . import anomaly_v03_process_supervisor as supervisor
from . import anomaly_v03_reader_evidence as observed
from . import anomaly_v03_platform_fixture as platform


ROOT = chain.ROOT
OUTPUT_PARENT = ROOT / 'artifacts/anomaly-v03-preformal-saved-row-document-budget'
FORMAT = 'anomaly-v03-saved-row-document-publication-v1'
SCOPE = 'pinned-invented-saved-rows-to-50000-document-local-writer-fresh-reader'
PAYLOAD_LIMITS = {
    'calculation.json': chain.draw_bridge.OUTPUT_BYTES,
    'audit.json': chain.draw_bridge.OUTPUT_BYTES,
    'document.json': chain.document_bridge.MAX_DOCUMENT_BYTES,
    'slices.json': chain.slice_bridge.MAX_SLICES_BYTES,
    'slice-count-audit.json': chain.MAX_CONTROL,
}
LIMITS = {'wall_seconds': 60, 'private_bytes': 512 * 1024**2,
          'output_bytes': 64 * 1024}
SOURCE_NAMES = (
    'src/banto_ai/anomaly_v03_saved_row_document_publication.py',
    'src/banto_ai/anomaly_v03_process_supervisor.py',
    'src/banto_ai/anomaly_v03_reader_evidence.py',
    'src/banto_ai/anomaly_v03_platform_fixture.py',
    'src/banto_ai/anomaly_v03_platform_fixture_runtime.py',
    'src/banto_ai/_anomaly_v03_io.py',
    'src/banto_ai/_anomaly_v03_runtime.py',
    'src/banto_ai/anomaly_v03_engineering_contract.py',
)
REQUEST_MAX = 32 * 1024


class PublicationBudget(chain.ContiguousBudget):
    phase_names = (*chain.PHASES[:-1], 'writer', 'reader', 'postflight')

    def __init__(self, root, value=None):
        super().__init__(root, value, publication_roots=[root / 'published'])

    def checkpoint(self, phase=None):
        super().checkpoint(self.phase if phase is None else phase)

    def close(self):
        report = super().close()
        report.update(format=FORMAT + '-resource-budget', scope=SCOPE,
                      saved_control_loading_inside_budget=False,
                      saved_control_projection_inside_budget=True)
        def completed(names):
            return all(name in self.roles and
                       self.roles[name]['status'] == 'complete' and
                       self.roles[name]['worker_exit_confirmed'] is True
                       for name in names)
        report['both_arithmetic_child_exits_reported'] = completed(('analysis', 'audit'))
        report['all_four_child_exits_reported'] = (
            set(self.roles) == {'analysis', 'audit', 'writer', 'reader'} and
            completed(('analysis', 'audit', 'writer', 'reader')))
        return report


def _pin(raw):
    return chain.draw_bridge._pin(raw)


def _read(path, pin, maximum):
    return chain.draw_bridge._read(path, pin, maximum)


def _canonical(path, pin, maximum):
    raw = _read(path, pin, maximum)
    value = chain.draw_bridge.projection.v.strict_json(raw)
    if chain.draw_bridge._raw(value) != raw:
        raise ValueError('publication source canonical framing differs')
    return raw, value


def _source_recheck(pins):
    if type(pins) is not dict or not set(SOURCE_NAMES).issubset(pins):
        raise ValueError('publication selected source inventory differs')
    for name, pin in pins.items():
        chain.draw_bridge.projection.v.safe_relative_path(name)
        if not name.startswith(('src/banto_ai/', 'tools/')) or not name.endswith('.py'):
            raise ValueError('publication selected source path differs')
        _read(ROOT / name, pin, 1024**2)


def _retained(request):
    root = Path(request['receipt_root']).absolute()
    if (root.parent != OUTPUT_PARENT or not root.name.startswith('trial-') or
            request['publication_root'] != str(root / 'published')):
        raise ValueError('publication receipt ownership differs')
    io.regular_path(root, directory=True)
    if set(request['payload_source_pins']) != set(PAYLOAD_LIMITS):
        raise ValueError('publication payload inventory differs')
    inputs = request['projection_input_pins']
    if set(inputs) != set(chain.draw_bridge.projection.analysis.INPUT_LIMITS):
        raise ValueError('publication projection inventory differs')
    _, fixture = _canonical(root / 'inputs/input.json', inputs['fixture/input.json'], 1024**2)
    _, slice_source = _canonical(root / 'inputs/slices.json', inputs['fixture/slices.json'], 8 * 1024**2)
    for name in ('fixture/coverage.json', 'fixture/operation.json'):
        _canonical(root / 'inputs' / Path(name).name, inputs[name],
                   chain.draw_bridge.projection.analysis.INPUT_LIMITS[name])
    chain.document_bridge.document._input(fixture)
    _, draw_input = _canonical(root / 'input.json', request['input_pin'], 512 * 1024)
    chain.draw_bridge._check_input(draw_input)
    if (draw_input['clusters'] != fixture['clusters'] or
            draw_input['projection_input_pins'] != inputs or
            draw_input['projection_source_revision'] != request['source_revision'] or
            draw_input['saved_row_projection_pin'] != request['projection_pin']):
        raise ValueError('publication saved-row input binding differs')
    _, projection = _canonical(root / 'projection.json', request['projection_pin'], 8 * 1024**2)
    if (projection['worker_input_pins'] != inputs or
            projection['formal_permission'] is not False or
            projection['registered_observations_read'] is not False):
        raise ValueError('publication saved-row projection differs')
    values, files = {}, {}
    for name, maximum in PAYLOAD_LIMITS.items():
        raw, values[name] = _canonical(root / name, request['payload_source_pins'][name], maximum)
        files[name] = io.json_bytes(values[name])
        if files[name] != raw + b'\n':
            raise ValueError('publication payload framing differs')
    calc, audit, document, slices, count = (values[name] for name in PAYLOAD_LIMITS)
    chain.draw_bridge.draw_budget._verify_audit_report(audit, request['payload_source_pins']['calculation.json'])
    if audit['draw_sha256'] != chain.draw_bridge.frozen.BOOTSTRAP_HASH:
        raise ValueError('publication draw digest differs')
    for value in (document, slices):
        chain.document_bridge._same_fields(value, chain.CLOSED, 'publication closed claims')
        if (value['saved_row_projection_pin'] != request['projection_pin'] or
                value['saved_row_projection_input_pins'] != inputs or
                value['input_pin'] != request['input_pin'] or
                value['calculation_pin'] != request['payload_source_pins']['calculation.json'] or
                value['arithmetic_audit_pin'] != request['payload_source_pins']['audit.json'] or
                value['saved_reader_control_inputs_used'] is not True or
                'producer_result_pin' in value):
            raise ValueError('publication document provenance differs')
    chain.document_bridge._same_fields(document, {
        'format': chain.FORMAT + '-fixture-draft',
        'scope': 'same-budget-invented-primary-to-document-draft',
        'status': 'fixture_draft_prepared', 'invented_only': True,
        'legacy_projection_draws': 1,
        'numeric_draw_contract': {'clusters': 40, 'replicates': 50000,
            'accepted_indices': 2000000,
            'indices_raw_sha256': chain.draw_bridge.frozen.BOOTSTRAP_HASH,
            'source': 'same-budget-owned-invented-arithmetic'},
        'field_coverage': chain.document_bridge.document._coverage(),
        'formal_requirements': {'clusters': 40, 'replicates': 50000,
            'missing_fields': list(chain.document_bridge.document.PENDING), 'ready': False},
    }, 'publication primary draft claims')
    schema = chain.contract.schemas(chain.contract._expected_configs())[7]
    packet = chain.document_bridge.adapter.map_precomputed_fixture_packet(
        fixture['clusters'], fixture['diagnostics'], schema, calc,
        draw_sha256=audit['draw_sha256'])
    draft = chain.document_bridge.document._draft(packet)
    if document['fixture_packet'] != packet or document['document_draft'] != draft:
        raise ValueError('publication primary document mapping differs')
    derived = chain.slice_bridge.slices.derive_precomputed_slices(
        fixture['clusters'], fixture['diagnostics'], packet, slice_source, schema)
    expected = copy.deepcopy(document)
    expected['document_draft']['slices'] = derived['slices']
    expected.update(format=chain.FORMAT + '-fixture-slices',
        scope='same-budget-invented-primary-to-slices', status='fixture_slices_connected',
        field_coverage=chain.slice_bridge.slices._coverage(),
        formal_requirements=chain.slice_bridge.slices._requirements(),
        primary_document_pin=request['payload_source_pins']['document.json'],
        slice_source_pin=inputs['fixture/slices.json'],
        primary_packet_canonical_sha256=chain.slice_bridge.contract.canonical_sha256(packet),
        slice_source_canonical_sha256=derived['slice_input_canonical_sha256'],
        diagnostic_series=derived['diagnostic_series'], diagnostic_details=derived['diagnostic_details'],
        independent_count_audit_process_executed=False)
    if slices != expected:
        raise ValueError('publication full slice mapping differs')
    checked = chain.slice_bridge.independent.audit_precomputed_slices(
        fixture['clusters'], fixture['diagnostics'], packet, slice_source,
        chain.slice_bridge._audit_input(slices))
    if count != checked:
        raise ValueError('publication independent count audit differs')
    return files


def _semantic(files, expected):
    if dict(files) != expected:
        raise ValueError('published payload bytes differ from pinned source')


def worker_main(argv):
    try:
        if len(argv) != 3:
            raise ValueError('publication worker arguments')
        path, size, digest = argv
        request_path = Path(path).absolute()
        request_pin = {'bytes': int(size), 'sha256': digest}
        request = chain.draw_bridge.projection.v.strict_json(_read(request_path, request_pin, REQUEST_MAX))
        if (request['format'] != FORMAT + '-request' or
                request['role'] not in ('writer', 'reader') or
                request_path != Path(request['receipt_root']) / request['role'] / 'request.json'):
            raise ValueError('publication worker request ownership differs')
        _source_recheck(request['source_pins'])
        files = _retained(request)
        publication = Path(request['publication_root'])
        def boundary():
            _source_recheck(request['source_pins'])
            _semantic(_retained(request), files)
        if request['role'] == 'writer':
            result = io.publish_local_result(publication.parent, publication.name, files,
                verify_semantics=lambda saved: _semantic(saved, files), precommit_recheck=boundary)
        else:
            result = io.verify_local_publication(publication,
                expected_marker_sha256=request['expected_marker_sha256'],
                verify_semantics=lambda saved: _semantic(saved, files))
            result['marker_raw_sha256'] = request['expected_marker_sha256']
        boundary()
        result.update(format=FORMAT, role=request['role'], status='verified',
            request_pin=request_pin, source_pins=request['source_pins'],
            payload_source_pins=request['payload_source_pins'],
            payload_pins={name: _pin(raw) for name, raw in files.items()},
            count_mapping_audit_replayed=True, numeric_draws_recomputed=False,
            formal_permission=False, registered_data_read=False, independent_s6_complete=False,
            process={**observed.creation_observation(os.getpid()), 'parent_pid': os.getppid()})
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({'status': 'rejected', 'error_type': type(error).__name__,
                          'detail': str(error)[:500], 'formal_permission': False}, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


def _role(request, root, budget):
    role = request['role']
    target = root / role
    target.mkdir()
    raw = io.json_bytes(request)
    if len(raw) > REQUEST_MAX:
        raise ValueError('publication request byte limit')
    pin = _pin(raw)
    io._exclusive(target / 'request.json', raw)
    launch = {}
    def boundary():
        budget.checkpoint(role)
        _read(target / 'request.json', pin, REQUEST_MAX)
        _source_recheck(request['source_pins'])
    def started(process):
        launch.update(observed.creation_observation(process.pid, process._handle))
        io._exclusive(target / 'launch.json', io.json_bytes(launch))
    bootstrap = ('import sys;sys.path.insert(0,sys.argv.pop(1));'
                 'from banto_ai.anomaly_v03_saved_row_document_publication import worker_main;'
                 'raise SystemExit(worker_main(sys.argv[1:]))')
    argv = [sys.executable, '-I', '-S', '-B', '-c', bootstrap, str(ROOT / 'src'),
            str(target / 'request.json'), str(pin['bytes']), pin['sha256']]
    try:
        with platform._platform_scope():
            monitor = supervisor.supervise(argv, ROOT, target / 'worker', LIMITS,
                boundary=boundary, on_started=started, resource_probe=budget.probe)
    except supervisor.UnreapedWorker as error:
        io._exclusive(target / 'supervision.json', io.json_bytes(error.report))
        raise
    supervision_pin = chain._write_value(target / 'supervision.json', monitor, chain.MAX_CONTROL)
    budget.record_role(role, monitor['status'], result_pin=supervision_pin,
                       worker_pid=monitor['worker_pid'], exit_confirmed=monitor['worker_exit_confirmed'])
    if (monitor['status'] != 'complete' or monitor['worker_exit_confirmed'] is not True or
            monitor['exit_code'] != 0 or monitor['observation_errors'] or
            monitor['worker_pid'] != launch.get('pid')):
        raise ValueError('owned publication ' + role + ' failed: ' + str(monitor['stop_reason']))
    reply = chain.draw_bridge.projection.v.strict_json(
        _read(target / 'worker/report.json', monitor['output'], LIMITS['output_bytes']))
    chain.document_bridge._same_fields(reply, {
        'format': FORMAT, 'role': role, 'status': 'verified', 'request_pin': pin,
        'source_pins': request['source_pins'], 'payload_source_pins': request['payload_source_pins'],
        'payload_pins': request['payload_pins'], 'count_mapping_audit_replayed': True,
        'numeric_draws_recomputed': False, 'formal_permission': False,
        'registered_data_read': False, 'independent_s6_complete': False,
        'process': {**launch, 'parent_pid': os.getpid()},
    }, 'owned publication reply')
    chain.draw_bridge.projection.evidence._digest(reply['marker_raw_sha256'])
    if role == 'reader' and (reply.get('local_verified') is not True or
                            reply.get('payloads') != len(PAYLOAD_LIMITS) or
                            reply['marker_raw_sha256'] != request['expected_marker_sha256']):
        raise ValueError('fresh reader marker binding differs')
    result = {**reply, 'worker_exit_confirmed': True, 'supervision_pin': supervision_pin,
              'worker_reply_pin': monitor['output'], 'launch_pin': _pin(io.json_bytes(launch))}
    chain._write_value(target / 'result.json', result, chain.MAX_CONTROL)
    return result


def publish(root, budget, result, revision, source_pins, input_pins):
    request = {'format': FORMAT + '-request', 'role': 'writer',
        'source_revision': revision, 'source_pins': source_pins,
        'receipt_root': str(root), 'publication_root': str(root / 'published'),
        'projection_pin': result['saved_row_projection_pin'],
        'projection_input_pins': input_pins, 'input_pin': result['input_pin'],
        'payload_source_pins': {name: result[key] for name, key in (
            ('calculation.json', 'calculation_pin'), ('audit.json', 'arithmetic_audit_pin'),
            ('document.json', 'document_pin'), ('slices.json', 'slices_pin'),
            ('slice-count-audit.json', 'slice_count_audit_pin'))}}
    files = _retained(request)
    request['payload_pins'] = {name: _pin(raw) for name, raw in files.items()}
    result.update(publication_status='unconfirmed', stage='writer')
    budget.checkpoint('writer')
    writer = _role(request, root, budget)
    result.update(writer=writer, publication_status='completed',
                  marker_raw_sha256=writer['marker_raw_sha256'],
                  writer_reaped_before_reader_start=True, stage='reader', reader_status='unconfirmed')
    budget.checkpoint('reader')
    reader = _role({**request, 'role': 'reader',
                    'expected_marker_sha256': writer['marker_raw_sha256']}, root, budget)
    if (reader['process']['pid'] == writer['process']['pid'] or
            reader['process']['start_token'] == writer['process']['start_token']):
        raise ValueError('fresh reader process identity differs')
    _semantic(_retained(request), files)
    io.verify_local_publication(root / 'published',
        expected_marker_sha256=writer['marker_raw_sha256'],
        verify_semantics=lambda saved: _semantic(saved, files))
    result.update(reader=reader, reader_status='completed', publication_performed=True,
                  local_publication_performed=True, payload_source_pins=request['payload_source_pins'],
                  payload_pins=request['payload_pins'])
