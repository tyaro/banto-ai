"""Join retained invented 50,000-draw primary tables to invented slice counts.

The previous arithmetic and producer attempts remain separate, pinned inputs.
This local rehearsal does no draw replay, observation generation, formal S6
acceptance or publication.  The independent count audit uses a separate
stdlib implementation, but is called in this process.
"""
from __future__ import annotations

import copy
from pathlib import Path
import subprocess
import time

from . import _anomaly_v03_contract as frozen
from . import anomaly_v03 as contract
from . import anomaly_v03_fixture_slice_audit as independent
from . import anomaly_v03_preformal_bound_document_bridge as previous
from . import anomaly_v03_platform_fixture_runtime as platform_runtime
from . import anomaly_v03_slice_fixture as slices


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PARENT = ROOT / 'artifacts' / 'anomaly-v03-preformal-bound-slice-bridge'
FORMAT = 'anomaly-v03-preformal-bound-slice-bridge-v1'
SLICE_FORMAT = FORMAT + '-fixture-document'
WALL_SECONDS = 180
MAX_SLICES_BYTES = 16 * 1024**2
MAX_RESULT_BYTES = 64 * 1024
SOURCE_NAMES = (
    'src/banto_ai/anomaly_v03_preformal_bound_slice_bridge.py',
    'tools/preformal_bound_slice_trial.py',
    'src/banto_ai/anomaly_v03_slice_fixture.py',
    'src/banto_ai/anomaly_v03_fixture_slice_audit.py',
    'src/banto_ai/anomaly_v03_preformal_bound_document_bridge.py',
    'src/banto_ai/anomaly_v03_analysis_adapter.py',
    'src/banto_ai/anomaly_v03_document_fixture.py',
    'src/banto_ai/anomaly_v03_analysis_inputs.py',
    'src/banto_ai/anomaly_v03_descriptive_report.py',
    'src/banto_ai/anomaly_v03_slices.py',
    'src/banto_ai/anomaly_v03_preformal_bound_draw_bridge.py',
    'src/banto_ai/anomaly_v03_preformal_draw_budget.py',
    'src/banto_ai/anomaly_v03_platform_fixture_runtime.py',
    'src/banto_ai/anomaly_v03.py',
    'src/banto_ai/_anomaly_v03_contract.py',
)
CLOSED = {**previous.CLOSED, 'independent_count_audit_process_executed': False}


def _source_pins(revision):
    previous.bridge.projection.evidence._digest(revision, 40)

    def git(*args):
        return subprocess.check_output(['git', '-C', str(ROOT), *args],
                                       stderr=subprocess.DEVNULL, timeout=10)

    if git('rev-parse', 'HEAD').decode().strip() != revision or git('status', '--porcelain').strip():
        raise ValueError('slice mapping requires clean expected HEAD')
    pins = {}
    for name in SOURCE_NAMES:
        raw = previous.bounded._bounded_file(ROOT / name, 1024**2)
        if raw != git('show', revision + ':' + name):
            raise ValueError('slice mapping source differs from Git: ' + name)
        pins[name] = previous.bounded._pin(raw)
    return pins


def _read_slice_source(saved, expected_slice_source_pin):
    """Authenticate a producer projection against an external raw pin."""
    previous.bridge.projection.evidence._pin(expected_slice_source_pin)
    bound_pin = saved['result']['producer_binding']['projection_pins']['fixture/slices.json']
    if expected_slice_source_pin != bound_pin:
        raise ValueError('external slice source pin differs from producer binding')
    producer_root = previous.bridge._producer_root(saved['result']['producer_root'])
    source = previous._read_json(
        producer_root / 'output/projection/fixture/slices.json', bound_pin,
        previous.bridge.projection.analysis.INPUT_LIMITS['fixture/slices.json'])
    return source


def verify_saved_document(document_root, expected_document_result_pin,
                          expected_slice_source_pin):
    """Rebind both prior attempts and return only authenticated invented data."""
    root = previous._path(document_root, previous.OUTPUT_PARENT)
    result = previous._read_json(root / 'result.json', expected_document_result_pin,
                                 previous.MAX_RESULT_BYTES)
    previous._same_fields(result, {
        **previous.CLOSED, 'format': previous.FORMAT,
        'scope': 'retained-invented-50000-primary-to-document-mapping-only',
        'status': 'verified', 'prior_arithmetic_budget_passed': True,
        'prior_arithmetic_child_exits_confirmed': True,
        'legacy_projection_draws': 1, 'numeric_draws': 50000,
        'numeric_draw_sha256': frozen.BOOTSTRAP_HASH,
    }, 'retained document result')
    if result['source_pins_before'] != result['source_pins_after'] or result['runtime_before'] != result['runtime_after']:
        raise ValueError('retained document source/runtime differs')
    payload = previous._read_json(root / 'document.json', result['document_pin'],
                                   previous.MAX_DOCUMENT_BYTES)
    saved = previous.verify_saved_bridge(result['bridge_root'], result['bridge_result_pin'])
    saved['external_result_pin'] = copy.deepcopy(result['bridge_result_pin'])
    schema = contract.schemas(contract._expected_configs())[7]
    previous.document._schema(schema)
    packet = previous.adapter.map_precomputed_fixture_packet(
        saved['bridge_input']['clusters'], saved['producer_input']['diagnostics'],
        schema, saved['calculation'], draw_sha256=saved['audit']['draw_sha256'])
    if payload != previous._fixture_document(saved, packet):
        raise ValueError('retained document differs from pinned arithmetic mapping')
    if (result['prior_arithmetic_revision'] != saved['result']['source_revision'] or
            result['prior_arithmetic_budget_pin'] != saved['result']['resource_budget_pin'] or
            result['document_pin'] != previous.bounded._pin(previous.bounded._raw(payload))):
        raise ValueError('retained document binding differs')
    source = _read_slice_source(saved, expected_slice_source_pin)
    return {'root': root, 'result': result, 'payload': payload,
            'saved': saved, 'source': source, 'schema': schema}


def _slice_document(retained, expected_document_result_pin, expected_slice_source_pin,
                    derived):
    base = retained['payload']
    packet = base['fixture_packet']
    if set(derived) != {'slices', 'diagnostic_series', 'diagnostic_details',
                        'slice_input_canonical_sha256'}:
        raise ValueError('unexpected derived slice fields')
    draft = copy.deepcopy(base['document_draft'])
    if draft['slices'] is not None or any(draft[name] is not None for name in slices.PENDING):
        raise ValueError('retained formal fields are not empty')
    draft['slices'] = copy.deepcopy(derived['slices'])
    result = copy.deepcopy(base)
    result.update({
        'format': SLICE_FORMAT,
        'scope': 'retained-invented-50000-primary-to-fixture-slices-only',
        'status': 'fixture_slices_connected',
        'document_draft': draft,
        'field_coverage': slices._coverage(),
        'formal_requirements': slices._requirements(),
        'document_result_pin': copy.deepcopy(expected_document_result_pin),
        'primary_document_pin': copy.deepcopy(retained['result']['document_pin']),
        'slice_source_pin': copy.deepcopy(expected_slice_source_pin),
        'primary_packet_canonical_sha256': contract.canonical_sha256(packet),
        'slice_source_canonical_sha256': derived['slice_input_canonical_sha256'],
        'diagnostic_series': copy.deepcopy(derived['diagnostic_series']),
        'diagnostic_details': copy.deepcopy(derived['diagnostic_details']),
        'independent_count_audit_process_executed': False,
    })
    if (result['numeric_draw_contract']['replicates'] != 50000 or
            result['legacy_projection_draws'] != 1 or
            result['formal_requirements']['missing_fields'] != list(slices.PENDING) or
            result['formal_requirements']['ready'] is not False):
        raise ValueError('slice document scope differs')
    for name, expected in CLOSED.items():
        if result[name] != expected:
            raise ValueError('slice document formal boundary differs: ' + name)
    return result


def _audit_input(value):
    return {name: value[name] for name in (
        'primary_packet_canonical_sha256', 'slice_source_canonical_sha256',
        'diagnostic_series', 'diagnostic_details') } | {'slices': value['document_draft']['slices']}


def _write_readback(path, value, maximum):
    raw = previous.bounded._raw(value)
    if len(raw) > maximum:
        raise ValueError('slice bridge output byte limit')
    previous.bounded._write(path, raw)
    pin = previous.bounded._pin(raw)
    previous.bounded._read(path, pin, maximum)
    return pin


def run_saved_slices(*, document_root, expected_document_result_pin,
                     expected_slice_source_pin, expected_revision, trial_name):
    """Write one no-overwrite fixture slice join and separate count audit."""
    started = time.monotonic()
    previous.bridge.projection.evidence._pin(expected_document_result_pin)
    previous.bridge.projection.evidence._pin(expected_slice_source_pin)
    previous.bridge.projection.evidence._digest(expected_revision, 40)
    previous.bridge.projection.v.safe_relative_path(trial_name)
    if '/' in trial_name or '\\' in trial_name or not trial_name.startswith('trial-'):
        raise ValueError('new slice trial name required')
    retained = verify_saved_document(document_root, expected_document_result_pin,
                                     expected_slice_source_pin)
    source_before = _source_pins(expected_revision)
    runtime_before = platform_runtime.probe_runtime(ROOT)
    OUTPUT_PARENT.mkdir(exist_ok=True)
    previous.bridge.projection.io.regular_path(OUTPUT_PARENT, directory=True)
    target = previous.bridge.projection.io.regular_path(OUTPUT_PARENT / trial_name,
                                                        directory=True, missing=True)
    target.mkdir()
    try:
        saved = retained['saved']
        packet = retained['payload']['fixture_packet']
        derived = slices.derive_precomputed_slices(
            saved['bridge_input']['clusters'], saved['producer_input']['diagnostics'],
            packet, retained['source'], retained['schema'])
        value = _slice_document(retained, expected_document_result_pin,
                                expected_slice_source_pin, derived)
        audit = independent.audit_precomputed_slices(
            saved['bridge_input']['clusters'], saved['producer_input']['diagnostics'],
            packet, retained['source'], _audit_input(value))
        previous._same_fields(audit, {
            'format': 'anomaly-v03-precomputed-fixture-slice-audit-v1',
            'status': 'precomputed_fixture_slices_matched',
            'clusters': 40, 'main_slice_rows': 1233,
            'diagnostic_rows': 2835, 'diagnostic_tables': 9,
            'primary_packet_canonical_sha256': value['primary_packet_canonical_sha256'],
            'slice_source_canonical_sha256': value['slice_source_canonical_sha256'],
            'fixture_only': True, 'precomputed_primary_packet_used': True,
            'fixture_slice_audit_performed': True,
            'primary_ci_gate_recomputed': False,
            'formal_permission': False, 'promotion_allowed': False,
            'registered_data_read': False, 'independent_s6_complete': False,
        }, 'independent count audit')
        if time.monotonic() - started > WALL_SECONDS:
            raise ValueError('slice mapping wall checkpoint exceeded')
        slices_pin = _write_readback(target / 'slices.json', value, MAX_SLICES_BYTES)
        audit_pin = _write_readback(target / 'audit.json', audit, MAX_RESULT_BYTES)
        source_after = _source_pins(expected_revision)
        runtime_after = platform_runtime.probe_runtime(ROOT)
        if source_after != source_before or runtime_after != runtime_before:
            raise ValueError('slice mapping source/runtime changed')
        after = verify_saved_document(document_root, expected_document_result_pin,
                                      expected_slice_source_pin)
        if after != retained:
            raise ValueError('retained document or producer input changed during mapping')
        if time.monotonic() - started > WALL_SECONDS:
            raise ValueError('slice mapping wall checkpoint exceeded')
        result = {**CLOSED, 'format': FORMAT,
                  'scope': 'retained-invented-50000-primary-to-fixture-slices-only',
                  'status': 'verified', 'document_root': str(retained['root']),
                  'document_result_pin': copy.deepcopy(expected_document_result_pin),
                  'primary_document_pin': copy.deepcopy(retained['result']['document_pin']),
                  'slice_source_pin': copy.deepcopy(expected_slice_source_pin),
                  'slices_pin': slices_pin, 'audit_pin': audit_pin,
                  'independent_count_audit_matched': True,
                  'source_revision': expected_revision,
                  'prior_document_revision': retained['result']['source_revision'],
                  'source_pins_before': source_before, 'source_pins_after': source_after,
                  'runtime_before': runtime_before, 'runtime_after': runtime_after,
                  'numeric_draws': 50000, 'legacy_projection_draws': 1,
                  'main_slice_rows': len(derived['slices']),
                  'diagnostic_rows': sum(map(len, derived['diagnostic_series'].values())),
                  'diagnostic_tables': len(derived['diagnostic_details']),
                  'wall_scope': 'saved_pin_verification_plus_fixture_slice_mapping_and_count_audit',
                  'wall_seconds': time.monotonic() - started}
        result_pin = _write_readback(target / 'result.json', result, MAX_RESULT_BYTES)
        return {**result, 'result_pin': result_pin, 'receipt_root': str(target)}
    except BaseException as error:
        failure = {**CLOSED, 'format': FORMAT + '-failure', 'status': 'failed',
                   'document_result_pin': copy.deepcopy(expected_document_result_pin),
                   'slice_source_pin': copy.deepcopy(expected_slice_source_pin),
                   'source_revision': expected_revision,
                   'error_type': type(error).__name__, 'reason': str(error)[:500],
                   'wall_seconds': time.monotonic() - started}
        _write_readback(target / 'failure.json', failure, MAX_RESULT_BYTES)
        raise
