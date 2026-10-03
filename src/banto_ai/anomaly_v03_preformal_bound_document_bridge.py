"""Map a retained invented 50,000-draw arithmetic result to a fixture draft.

This is a new, saved-result-only boundary.  The arithmetic children ran in a
previous attempt; this module neither replays them nor adopts their budget as
the budget of document creation.  It never reads registered observations or
publishes a document.
"""
from __future__ import annotations

import copy
import hashlib
import os
from pathlib import Path
import subprocess
import time

from . import _anomaly_v03_contract as frozen
from . import anomaly_v03 as formal_contract
from . import anomaly_v03_analysis_adapter as adapter
from . import anomaly_v03_document_fixture as document
from . import anomaly_v03_preformal_bound_draw_bridge as bridge
from . import anomaly_v03_preformal_draw_budget as bounded
from . import anomaly_v03_platform_fixture_runtime as platform_runtime


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PARENT = ROOT / 'artifacts' / 'anomaly-v03-preformal-bound-document-bridge'
FORMAT = 'anomaly-v03-preformal-bound-document-bridge-v1'
DOCUMENT_FORMAT = FORMAT + '-fixture-draft'
MAX_DOCUMENT_BYTES = 4 * 1024**2
MAX_RESULT_BYTES = 64 * 1024
WALL_SECONDS = 120
SOURCE_NAMES = (
    'src/banto_ai/anomaly_v03_preformal_bound_document_bridge.py',
    'tools/preformal_bound_document_trial.py',
    'src/banto_ai/anomaly_v03_analysis_adapter.py',
    'src/banto_ai/anomaly_v03_document_fixture.py',
    'src/banto_ai/anomaly_v03_inference_audit.py',
    'src/banto_ai/anomaly_v03_preformal_draw_audit.py',
    'src/banto_ai/anomaly_v03_preformal_bound_draw_bridge.py',
    'src/banto_ai/anomaly_v03_preformal_draw_budget.py',
    'src/banto_ai/anomaly_v03_bound_fixture_pipeline.py',
    'src/banto_ai/anomaly_v03_platform_fixture_runtime.py',
    'src/banto_ai/anomaly_v03.py',
    'src/banto_ai/_anomaly_v03_contract.py',
)
CLOSED = {
    'registered_data_read': False,
    'formal_bootstrap_performed': False,
    'formal_document_emitted': False,
    'formal_document_validated': False,
    'formal_permission': False,
    'promotion_allowed': False,
    'independent_s6_complete': False,
    'execution_authenticated': False,
    'source_closure_complete': False,
    'runtime_closure_complete': False,
    'publication_performed': False,
    'same_run_arithmetic_performed': False,
    'current_document_outer_budget_measured': False,
    'full_end_to_end_budget_measured': False,
    'formal_50000_draw_budget_measured': False,
    'campaign_evaluations_credited': 0,
}


def _same_fields(value, expected, label):
    if type(value) is not dict:
        raise ValueError(label + ' object required')
    for key, wanted in expected.items():
        if key not in value or type(value[key]) is not type(wanted) or value[key] != wanted:
            raise ValueError(label + ' differs: ' + key)


def _path(path, parent):
    candidate = Path(path).absolute()
    if candidate != Path(os.path.abspath(candidate)) or candidate.parent != parent or not candidate.name.startswith('trial-'):
        raise ValueError('retained trial root required')
    bridge.projection.io.regular_path(parent, directory=True)
    bridge.projection.io.regular_path(candidate, directory=True)
    return candidate


def _read_json(path, pin, limit):
    bridge.projection.evidence._pin(pin)
    return bridge.projection.v.strict_json(bounded._read(path, pin, limit))


def _source_pins(revision):
    bridge.projection.evidence._digest(revision, 40)

    def git(*args):
        return subprocess.check_output(['git', '-C', str(ROOT), *args],
                                       stderr=subprocess.DEVNULL, timeout=10)

    if git('rev-parse', 'HEAD').decode().strip() != revision or git('status', '--porcelain').strip():
        raise ValueError('document mapping requires clean expected HEAD')
    pins = {}
    for name in SOURCE_NAMES:
        raw = bounded._bounded_file(ROOT / name, 1024**2)
        if raw != git('show', revision + ':' + name):
            raise ValueError('document mapping source differs from Git: ' + name)
        pins[name] = bounded._pin(raw)
    return pins


def verify_saved_bridge(bridge_root, expected_bridge_result_pin):
    """Read one externally pinned prior attempt and its independent inputs.

    Returns validated in-memory values only.  The prior trial's producer and
    50,000-draw children are never started by this function.
    """
    root = _path(bridge_root, bridge.OUTPUT_PARENT)
    result = _read_json(root / 'result.json', expected_bridge_result_pin, MAX_RESULT_BYTES)
    _same_fields(result, {
        'format': bridge.FORMAT,
        'scope': 'owned-invented-producer-bound-to-50000-primary-arithmetic-only',
        'status': 'measured', 'stage': 'complete', 'reason': None,
        'replicates_required': 50000, 'shared_budget_passed': True,
        'both_arithmetic_child_exits_reported': True,
        'invented_50000_primary_tables_measured': True,
        'invented_50000_independent_arithmetic_matched': True,
        'full_end_to_end_budget_measured': False,
        'formal_50000_draw_budget_measured': False,
        'new_evaluations': 0, **bridge.CLOSED,
    }, 'saved arithmetic result')
    if result['producer_root'] != result['producer_binding']['source_root']:
        raise ValueError('saved producer root differs')
    if result['producer_result_pin'] != result['producer_binding']['producer_result_pin']:
        raise ValueError('saved producer result pin differs')
    if result['runtime_before'] != result['runtime_after']:
        raise ValueError('saved arithmetic runtime changed')

    budget = _read_json(root / 'resource-budget.json', result['resource_budget_pin'], MAX_RESULT_BYTES)
    _same_fields(budget, {
        'format': bridge.FORMAT + '-resource-budget',
        'scope': 'pinned-owned-producer-to-two-arithmetic-children-only',
        'passed': True, 'stop_reason': None,
        'both_arithmetic_child_exits_reported': True,
        'sampler_exit_confirmed': True,
        'registered_data_read': False, 'formal_permission': False,
        'formal_50000_draw_budget_measured': False,
        'independent_s6_complete': False,
    }, 'saved arithmetic budget')
    if budget['root'] != str(root):
        raise ValueError('saved arithmetic budget root differs')
    roles = budget['caller_reported_roles']
    if type(roles) is not dict or set(roles) != {'analysis', 'audit'}:
        raise ValueError('saved arithmetic budget roles differ')

    calculations = {}
    pids = []
    for role, output_name, pin_name in (
            ('analysis', 'calculation.json', 'calculation_pin'),
            ('audit', 'audit.json', 'audit_pin')):
        supervision = _read_json(root / (role + '-supervision.json'),
                                 result[role + '_supervision_pin'], MAX_RESULT_BYTES)
        if supervision != result[role + '_supervision']:
            raise ValueError('saved arithmetic supervision differs: ' + role)
        _same_fields(supervision, {'format': bridge.FORMAT + '-supervision',
                                  'role': role, 'status': 'complete',
                                  'worker_exit_confirmed': True, 'exit_code': 0,
                                  'stop_reason': None, 'observation_errors': [],
                                  'formal_permission': False}, role + ' supervision')
        _same_fields(roles[role], {'status': 'complete',
                                  'result_pin': result[role + '_supervision_pin'],
                                  'worker_pid': supervision['pid'],
                                  'worker_exit_confirmed': True}, role + ' budget role')
        pids.append(supervision['pid'])
        bounded._read(root / (role + '-stderr.txt'), supervision['stderr_pin'], bridge.LOG_BYTES)
        bridge._verify_role(root, role, supervision, result[pin_name])
        calculations[role] = _read_json(root / output_name, result[pin_name], bridge.OUTPUT_BYTES)
    if type(pids[0]) is not int or type(pids[1]) is not int or pids[0] <= 0 or pids[1] <= 0 or pids[0] == pids[1]:
        raise ValueError('saved arithmetic child PIDs differ')

    saved_input = _read_json(root / 'input.json', result['input_pin'], 512 * 1024)
    bridge._check_input(saved_input)
    bound = bridge.bind_producer_counts(result['producer_root'], result['producer_result_pin'])
    if bound != {**result['producer_binding'], 'clusters': saved_input['clusters']}:
        raise ValueError('saved producer binding differs')
    if (saved_input['producer_result_pin'] != result['producer_result_pin'] or
            saved_input['bound_pin'] != bound['bound_pin'] or
            saved_input['projection_input_pin'] != bound['projection_pins']['fixture/input.json']):
        raise ValueError('saved arithmetic input/producer pin differs')

    producer_root = bridge._producer_root(result['producer_root'])
    projection_pin = bound['projection_pins']['fixture/input.json']
    projection_input = _read_json(producer_root / 'output/projection/fixture/input.json',
                                  projection_pin, bridge.projection.analysis.INPUT_LIMITS['fixture/input.json'])
    document._input(projection_input)
    if len(projection_input['draws']) != 1 or projection_input['draws'][0] != list(range(40)):
        raise ValueError('saved producer projection is not the historical one-draw probe')
    if projection_input['engineering_ready_assumption'] is not False or projection_input['clusters'] != saved_input['clusters']:
        raise ValueError('saved producer diagnostics/counts differ')
    adapter._diagnostics(saved_input['clusters'], projection_input['diagnostics'])

    calculation, audit = calculations['analysis'], calculations['audit']
    _same_fields(audit, {'format': bridge.independent.FORMAT,
                         'status': 'invented_primary_numerics_matched',
                         'draw_sha256': frozen.BOOTSTRAP_HASH,
                         'calculation_sha256': result['calculation_pin']['sha256'],
                         'clusters': 40, 'replicates': 50000,
                         'candidate_tables': 9, 'primary_estimates': 117,
                         'paired_estimates': 72, 'gates': 180,
                         'registered_data_read': False,
                         'formal_bootstrap_performed': False,
                         'formal_permission': False, 'promotion_allowed': False,
                         'independent_s6_complete': False,
                         'performance_status': 'not_evaluated'},
                 'saved independent arithmetic')
    if hashlib.sha256(bounded._raw(calculation)).hexdigest() != audit['calculation_sha256']:
        raise ValueError('saved calculation/audit hash differs')
    return {'root': root, 'result': result, 'budget': budget,
            'bridge_input': saved_input, 'calculation': calculation,
            'audit': audit, 'producer_input': projection_input,
            'producer_input_pin': projection_pin}


def _fixture_document(saved, packet):
    draft = document._draft(packet)
    if set(draft) != set(document.FIELDS) or any(draft[field] is not None for field in document.PENDING):
        raise ValueError('fixture draft formal fields must be missing')
    if draft['candidate_tables'] != packet['fixture_candidate_tables']:
        raise ValueError('fixture draft primary tables differ')
    result = saved['result']
    return {
        **CLOSED,
        'format': DOCUMENT_FORMAT,
        'scope': 'saved-invented-50000-primary-tables-to-fixture-draft-only',
        'invented_only': True,
        'status': 'fixture_draft_prepared',
        'numeric_draw_contract': {'clusters': 40, 'replicates': 50000,
                                  'accepted_indices': 2000000,
                                  'indices_raw_sha256': frozen.BOOTSTRAP_HASH,
                                  'source': 'previous independently audited invented arithmetic attempt'},
        'legacy_projection_draws': len(saved['producer_input']['draws']),
        'bridge_result_pin': copy.deepcopy(saved['external_result_pin']),
        'bridge_input_pin': copy.deepcopy(result['input_pin']),
        'calculation_pin': copy.deepcopy(result['calculation_pin']),
        'arithmetic_audit_pin': copy.deepcopy(result['audit_pin']),
        'diagnostics_input_pin': copy.deepcopy(saved['producer_input_pin']),
        'producer_result_pin': copy.deepcopy(result['producer_result_pin']),
        'prior_arithmetic_budget_pin': copy.deepcopy(result['resource_budget_pin']),
        'fixture_packet': packet,
        'document_draft': draft,
        'field_coverage': document._coverage(),
        'formal_requirements': {'clusters': 40, 'replicates': 50000,
                                'missing_fields': list(document.PENDING), 'ready': False},
    }


def _write_readback(path, raw, maximum):
    if len(raw) > maximum:
        raise ValueError('document bridge output byte limit')
    bounded._write(path, raw)
    pin = bounded._pin(raw)
    bounded._read(path, pin, maximum)
    return pin


def run_saved_document(*, bridge_root, expected_bridge_result_pin,
                       expected_revision, trial_name):
    """Create one new, locally retained fixture document mapping attempt."""
    started = time.monotonic()
    bridge.projection.evidence._pin(expected_bridge_result_pin)
    bridge.projection.evidence._digest(expected_revision, 40)
    bridge.projection.v.safe_relative_path(trial_name)
    if '/' in trial_name or '\\' in trial_name or not trial_name.startswith('trial-'):
        raise ValueError('new document trial name required')
    saved = verify_saved_bridge(bridge_root, expected_bridge_result_pin)
    saved['external_result_pin'] = copy.deepcopy(expected_bridge_result_pin)
    source_before = _source_pins(expected_revision)
    runtime_before = platform_runtime.probe_runtime(ROOT)
    OUTPUT_PARENT.mkdir(exist_ok=True)
    bridge.projection.io.regular_path(OUTPUT_PARENT, directory=True)
    target = bridge.projection.io.regular_path(OUTPUT_PARENT / trial_name, directory=True, missing=True)
    target.mkdir()
    try:
        schema = formal_contract.schemas(formal_contract._expected_configs())[7]
        document._schema(schema)
        packet = adapter.map_precomputed_fixture_packet(
            saved['bridge_input']['clusters'], saved['producer_input']['diagnostics'],
            schema, saved['calculation'], draw_sha256=saved['audit']['draw_sha256'])
        if time.monotonic() - started > WALL_SECONDS:
            raise ValueError('document mapping wall checkpoint exceeded')
        payload = _fixture_document(saved, packet)
        document_pin = _write_readback(target / 'document.json', bounded._raw(payload), MAX_DOCUMENT_BYTES)
        source_after = _source_pins(expected_revision)
        if source_after != source_before:
            raise ValueError('document mapping source changed')
        runtime_after = platform_runtime.probe_runtime(ROOT)
        if runtime_after != runtime_before:
            raise ValueError('document mapping runtime changed')
        # Rebind all prior files after mapping, including producer projections,
        # role logs and the previous budget.  This is still a read-only check.
        after = verify_saved_bridge(bridge_root, expected_bridge_result_pin)
        if after != {key: value for key, value in saved.items()
                     if key != 'external_result_pin'}:
            raise ValueError('retained arithmetic/producer inputs changed during mapping')
        if time.monotonic() - started > WALL_SECONDS:
            raise ValueError('document mapping wall checkpoint exceeded')
        result = {**CLOSED, 'format': FORMAT,
                  'scope': 'retained-invented-50000-primary-to-document-mapping-only',
                  'status': 'verified', 'bridge_root': str(saved['root']),
                  'bridge_result_pin': copy.deepcopy(expected_bridge_result_pin),
                  'prior_arithmetic_budget_pin': copy.deepcopy(saved['result']['resource_budget_pin']),
                  'prior_arithmetic_budget_passed': True,
                  'prior_arithmetic_child_exits_confirmed': True,
                  'document_pin': document_pin, 'source_revision': expected_revision,
                  'prior_arithmetic_revision': saved['result']['source_revision'],
                  'source_pins_before': source_before, 'source_pins_after': source_after,
                  'runtime_before': runtime_before, 'runtime_after': runtime_after,
                  'legacy_projection_draws': 1,
                  'numeric_draws': 50000, 'numeric_draw_sha256': frozen.BOOTSTRAP_HASH,
                  'wall_scope': 'saved_pin_verification_plus_fixture_draft_mapping',
                  'wall_seconds': time.monotonic() - started}
        result_pin = _write_readback(target / 'result.json', bounded._raw(result), MAX_RESULT_BYTES)
        return {**result, 'result_pin': result_pin, 'receipt_root': str(target)}
    except BaseException as error:
        failure = {**CLOSED, 'format': FORMAT + '-failure', 'status': 'failed',
                   'bridge_result_pin': copy.deepcopy(expected_bridge_result_pin),
                   'source_revision': expected_revision,
                   'error_type': type(error).__name__,
                   'reason': str(error)[:500],
                   'wall_seconds': time.monotonic() - started}
        _write_readback(target / 'failure.json', bounded._raw(failure), MAX_RESULT_BYTES)
        raise
