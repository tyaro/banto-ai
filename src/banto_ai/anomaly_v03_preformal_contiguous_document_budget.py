"""One sampled invented 50,000-draw arithmetic -> document/slice attempt.

The retained producer is an externally pinned input, outside this clock and
root.  Both arithmetic children and the parent-side document/slice mappings
run before the one monitor closes.  This is not a registered reader, full S6,
publication, or an S4/S5 budget.
"""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path
import subprocess
import sys
import time

from . import anomaly_v03 as contract
from . import anomaly_v03_preformal_bound_document_bridge as document_bridge
from . import anomaly_v03_preformal_bound_draw_bridge as draw_bridge
from . import anomaly_v03_preformal_bound_slice_bridge as slice_bridge
from . import anomaly_v03_preformal_chain_budget as shared_budget
from . import anomaly_v03_platform_fixture_runtime as platform_runtime


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PARENT = ROOT / 'artifacts/anomaly-v03-preformal-contiguous-document-budget'
FORMAT = 'anomaly-v03-preformal-contiguous-document-budget-v1'
PHASES = ('preflight', 'analysis', 'audit', 'document', 'slices', 'postflight')
OUTPUTS = ('document', 'slices', 'slice-count-audit')
MAX_CONTROL = 64 * 1024
LIMITS = {
    'wall_seconds': 1200,
    'parent_private_bytes': 512 * 1024**2,
    'directory_bytes': 96 * 1024**2,
    'directory_entries': 128,
    'directory_depth': 5,
    'minimum_commit_headroom_bytes': 4 * 1024**3,
    'minimum_free_ram_bytes': 4 * 1024**3,
    'minimum_free_disk_bytes': 10 * 1024**3,
}
SOURCE_NAMES = tuple(dict.fromkeys((
    'src/banto_ai/anomaly_v03_preformal_contiguous_document_budget.py',
    'tools/preformal_contiguous_document_budget_trial.py',
    'src/banto_ai/anomaly_v03_preformal_chain_budget.py',
    'src/banto_ai/_anomaly_v03_fixture_budget.py',
    *draw_bridge.SOURCE_NAMES,
    *document_bridge.SOURCE_NAMES,
    *slice_bridge.SOURCE_NAMES,
)))
CLOSED = {
    'registered_data_read': False,
    'registered_saved_reader_used': False,
    'formal_bootstrap_performed': False,
    'formal_document_emitted': False,
    'formal_document_validated': False,
    'independent_s6_complete': False,
    'formal_permission': False,
    'promotion_allowed': False,
    'execution_authenticated': False,
    'source_closure_complete': False,
    'runtime_closure_complete': False,
    'publication_performed': False,
    'full_end_to_end_budget_measured': False,
    'formal_50000_draw_budget_measured': False,
    'smoke_capacity_twice_checked': False,
    'smoke_capacity_twice_passed': None,
    'campaign_evaluations_credited': 0,
}


def _limits(value=None):
    result = dict(LIMITS if value is None else value)
    if set(result) != set(LIMITS):
        raise ValueError('contiguous budget limit fields')
    for name, baseline in LIMITS.items():
        number = result[name]
        valid = (type(number) in (int, float) and math.isfinite(number)
                 if name == 'wall_seconds' else type(number) is int)
        if not valid or number <= 0:
            raise ValueError('contiguous budget positive finite limits')
        if (number < baseline if name.startswith('minimum_') else number > baseline):
            raise ValueError('contiguous budget limits may only tighten')
    return result


class ContiguousBudget(shared_budget.PreformalChainBudget):
    """Versioned scope and phases, with the existing cooperative stop probe."""

    phase_names = PHASES

    def __init__(self, root, value=None, *, publication_roots=()):
        super().__init__(root, publication_roots=publication_roots)
        self.limits = _limits(value)
        self.outputs = {}

    def checkpoint(self, phase):
        if phase not in self.phase_names or self._thread is None or self._closed is not None:
            raise ValueError('invalid contiguous budget checkpoint')
        with self._state_lock:
            self.phase = phase
            self.phase_log.append({
                'phase': phase,
                'elapsed_seconds': time.monotonic() - self.started_at,
                'stop_before_sample': self.reason,
            })
        self._observe()
        reason = self.probe()
        if reason is not None:
            raise draw_bridge.resources.ResourceStop(reason)

    def record_output(self, name, pin):
        if name not in OUTPUTS or name in self.outputs or self._closed is not None:
            raise ValueError('contiguous budget output report')
        draw_bridge.projection.evidence._pin(pin)
        self.outputs[name] = copy.deepcopy(pin)

    def close(self):
        report = super().close()
        report['format'] = FORMAT + '-resource-budget'
        report['scope'] = 'invented-40-cluster-50000-arithmetic-document-slices-only'
        report['both_arithmetic_child_exits_reported'] = (
            set(self.roles) == {'analysis', 'audit'} and all(
                row['status'] == 'complete' and row['worker_exit_confirmed']
                for row in self.roles.values()))
        report['reported_output_pins'] = copy.deepcopy(self.outputs)
        report['all_mapping_outputs_reported'] = set(self.outputs) == set(OUTPUTS)
        report.pop('caller_reported_all_five_exits')
        return report


def _source_pins(revision):
    draw_bridge.projection.evidence._digest(revision, 40)

    def git(*args):
        return subprocess.check_output(['git', '-C', str(ROOT), *args],
                                       stderr=subprocess.DEVNULL, timeout=10)

    if (git('rev-parse', 'HEAD').decode().strip() != revision or
            git('status', '--porcelain').strip()):
        raise ValueError('contiguous trial requires clean expected HEAD')
    pins = {}
    for name in SOURCE_NAMES:
        raw = draw_bridge.draw_budget._bounded_file(ROOT / name, 1024**2)
        if raw != git('show', revision + ':' + name):
            raise ValueError('contiguous selected source differs from Git: ' + name)
        pins[name] = draw_bridge._pin(raw)
    return pins


def _external(producer_root, result_pin, projection_pins):
    """Rebind externally supplied raw pins before creating an output root."""
    draw_bridge.projection.evidence._pin(result_pin)
    if type(projection_pins) is not dict or set(projection_pins) != set(
            draw_bridge.projection.analysis.INPUT_LIMITS):
        raise ValueError('external producer projection pin inventory')
    for pin in projection_pins.values():
        draw_bridge.projection.evidence._pin(pin)
    binding = draw_bridge.bind_producer_counts(producer_root, result_pin)
    if binding['projection_pins'] != projection_pins:
        raise ValueError('external projection pins differ from producer result')
    producer_input = draw_bridge.projection.v.strict_json(draw_bridge._read(
        Path(binding['source_root']) / 'output/projection/fixture/input.json',
        projection_pins['fixture/input.json'],
        draw_bridge.projection.analysis.INPUT_LIMITS['fixture/input.json']))
    document_bridge.document._input(producer_input)
    if producer_input['clusters'] != binding['clusters'] or len(producer_input['draws']) != 1:
        raise ValueError('external producer input/counts differ')
    slice_source = draw_bridge.projection.v.strict_json(draw_bridge._read(
        Path(binding['source_root']) / 'output/projection/fixture/slices.json',
        projection_pins['fixture/slices.json'],
        draw_bridge.projection.analysis.INPUT_LIMITS['fixture/slices.json']))
    return binding, producer_input, slice_source


def _write_value(path, value, maximum):
    raw = draw_bridge._raw(value)
    if not 0 < len(raw) <= maximum:
        raise ValueError('contiguous output byte bound')
    return draw_bridge._write(path, raw)


def _arithmetic(root, input_pin, budget, result):
    """Own both full-draw children before any document mapping can begin."""
    for role in ('analysis', 'audit'):
        result['stage'] = role
        budget.checkpoint(role)
        options = ({'inventory_profile_pin': result['arithmetic_runtime_profile_pins'][role]}
                   if 'arithmetic_runtime_profile_pins' in result else {})
        supervision = draw_bridge._supervise(
            role, root, input_pin, result.get('calculation_pin'), budget, **options)
        supervision_pin = _write_value(
            root / (role + '-supervision.json'), supervision, MAX_CONTROL)
        result[role + '_supervision_pin'] = supervision_pin
        result[role + '_supervision'] = supervision
        budget.record_role(role, supervision['status'], result_pin=supervision_pin,
                           worker_pid=supervision['pid'],
                           exit_confirmed=supervision['worker_exit_confirmed'])
        if supervision['status'] != 'complete' or not supervision['worker_exit_confirmed']:
            raise draw_bridge.resources.ResourceStop(
                supervision['stop_reason'] or role + '_owned_child_failed')
        name = 'calculation.json' if role == 'analysis' else 'audit.json'
        pin = draw_bridge._pin(draw_bridge.draw_budget._bounded_file(
            root / name, draw_bridge.OUTPUT_BYTES))
        draw_bridge._verify_role(root, role, supervision, pin, **options)
        result['calculation_pin' if role == 'analysis' else 'arithmetic_audit_pin'] = pin
        budget.checkpoint(role)
    calculation = draw_bridge.projection.v.strict_json(draw_bridge._read(
        root / 'calculation.json', result['calculation_pin'], draw_bridge.OUTPUT_BYTES))
    audit = draw_bridge.projection.v.strict_json(draw_bridge._read(
        root / 'audit.json', result['arithmetic_audit_pin'], draw_bridge.OUTPUT_BYTES))
    draw_bridge.draw_budget._verify_audit_report(audit, result['calculation_pin'])
    if audit['draw_sha256'] != draw_bridge.frozen.BOOTSTRAP_HASH:
        raise ValueError('contiguous full draw digest differs')
    result['both_arithmetic_children_verified'] = True
    if 'arithmetic_runtime_profile_pins' in result:
        result['arithmetic_runtime_observation_checked'] = True
    return calculation, audit


def _document(root, binding, producer_input, calculation, audit, budget, result):
    budget.checkpoint('document')
    schema = contract.schemas(contract._expected_configs())[7]
    document_bridge.document._schema(schema)
    packet = document_bridge.adapter.map_precomputed_fixture_packet(
        binding['clusters'], producer_input['diagnostics'], schema, calculation,
        draw_sha256=audit['draw_sha256'])
    draft = document_bridge.document._draft(packet)
    if (set(draft) != set(document_bridge.document.FIELDS) or
            any(draft[name] is not None for name in document_bridge.document.PENDING) or
            draft['candidate_tables'] != packet['fixture_candidate_tables']):
        raise ValueError('contiguous fixture document draft differs')
    budget.checkpoint('document')
    value = {
        **CLOSED,
        'format': FORMAT + '-fixture-draft',
        'scope': 'same-budget-invented-primary-to-document-draft',
        'status': 'fixture_draft_prepared',
        'invented_only': True,
        'numeric_draw_contract': {
            'clusters': 40, 'replicates': 50000, 'accepted_indices': 2000000,
            'indices_raw_sha256': draw_bridge.frozen.BOOTSTRAP_HASH,
            'source': 'same-budget-owned-invented-arithmetic',
        },
        'legacy_projection_draws': 1,
        **({'saved_row_projection_pin': copy.deepcopy(binding['saved_row_projection_pin']),
            'saved_row_projection_input_pins': copy.deepcopy(binding['projection_pins']),
            'saved_reader_control_inputs_used': True}
           if 'saved_row_projection_pin' in binding else {
            'producer_result_pin': copy.deepcopy(binding['producer_result_pin']),
            'producer_projection_pins': copy.deepcopy(binding['projection_pins'])}),
        'input_pin': copy.deepcopy(result['input_pin']),
        'calculation_pin': copy.deepcopy(result['calculation_pin']),
        'arithmetic_audit_pin': copy.deepcopy(result['arithmetic_audit_pin']),
        'fixture_packet': packet,
        'document_draft': draft,
        'field_coverage': document_bridge.document._coverage(),
        'formal_requirements': {
            'clusters': 40, 'replicates': 50000,
            'missing_fields': list(document_bridge.document.PENDING),
            'ready': False,
        },
    }
    pin = _write_value(root / 'document.json', value,
                       document_bridge.MAX_DOCUMENT_BYTES)
    result['document_pin'] = pin
    budget.record_output('document', pin)
    budget.checkpoint('document')
    return value, schema


def _slices(root, binding, producer_input, source, document, schema,
            budget, result):
    budget.checkpoint('slices')
    packet = document['fixture_packet']
    derived = slice_bridge.slices.derive_precomputed_slices(
        binding['clusters'], producer_input['diagnostics'], packet, source, schema)
    budget.checkpoint('slices')
    if set(derived) != {'slices', 'diagnostic_series', 'diagnostic_details',
                        'slice_input_canonical_sha256'}:
        raise ValueError('contiguous derived slice fields')
    value = copy.deepcopy(document)
    value['document_draft']['slices'] = copy.deepcopy(derived['slices'])
    value.update({
        'format': FORMAT + '-fixture-slices',
        'scope': 'same-budget-invented-primary-to-slices',
        'status': 'fixture_slices_connected',
        'field_coverage': slice_bridge.slices._coverage(),
        'formal_requirements': slice_bridge.slices._requirements(),
        'primary_document_pin': copy.deepcopy(result['document_pin']),
        'slice_source_pin': copy.deepcopy(binding['projection_pins']['fixture/slices.json']),
        'primary_packet_canonical_sha256':
            slice_bridge.contract.canonical_sha256(packet),
        'slice_source_canonical_sha256': derived['slice_input_canonical_sha256'],
        'diagnostic_series': copy.deepcopy(derived['diagnostic_series']),
        'diagnostic_details': copy.deepcopy(derived['diagnostic_details']),
        'independent_count_audit_process_executed': False,
    })
    if (value['formal_requirements']['ready'] is not False or
            value['formal_requirements']['missing_fields'] !=
            list(slice_bridge.slices.PENDING)):
        raise ValueError('contiguous formal document fields must remain missing')
    count_audit = slice_bridge.independent.audit_precomputed_slices(
        binding['clusters'], producer_input['diagnostics'], packet, source,
        slice_bridge._audit_input(value))
    document_bridge._same_fields(count_audit, {
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
    }, 'contiguous independent count audit')
    budget.checkpoint('slices')
    slices_pin = _write_value(root / 'slices.json', value,
                              slice_bridge.MAX_SLICES_BYTES)
    result['slices_pin'] = slices_pin
    budget.record_output('slices', slices_pin)
    audit_pin = _write_value(root / 'slice-count-audit.json', count_audit,
                             MAX_CONTROL)
    result['slice_count_audit_pin'] = audit_pin
    budget.record_output('slice-count-audit', audit_pin)
    budget.checkpoint('slices')


def run_chain(*, expected_mode, producer_root, expected_producer_result_pin,
              expected_projection_pins, expected_revision, receipt_name,
              receipt_parent=OUTPUT_PARENT, budget_limits=None,
              arithmetic_runtime_profiles=None):
    """Retain one new attempt; an old arithmetic receipt is never an input."""
    if type(expected_mode) is not str or expected_mode != 'fixture':
        raise ValueError('only invented fixture mode is open')
    draw_bridge.projection.evidence._digest(expected_revision, 40)
    profiles = draw_bridge.validate_runtime_profiles(arithmetic_runtime_profiles, revision=expected_revision)
    draw_bridge.projection.v.safe_relative_path(receipt_name)
    if ('/' in receipt_name or '\\' in receipt_name or
            not receipt_name.startswith('trial-')):
        raise ValueError('new contiguous trial name required')
    parent = Path(receipt_parent).absolute()
    if parent != OUTPUT_PARENT:
        raise ValueError('contiguous output parent differs')
    # All retained producer bytes, all four externally supplied projection
    # pins, and selected source bytes are checked before a new root exists.
    binding, producer_input, slice_source = _external(
        producer_root, expected_producer_result_pin, expected_projection_pins)
    source_before = _source_pins(expected_revision)
    runtime_before = platform_runtime.probe_runtime(ROOT)
    limits = _limits(budget_limits)
    parent.mkdir(exist_ok=True)
    draw_bridge.projection.io.regular_path(parent, directory=True)
    root = draw_bridge.projection.io.regular_path(
        parent / receipt_name, directory=True, missing=True)
    root.mkdir()
    started = time.monotonic()
    result = {
        **CLOSED,
        'format': FORMAT, 'status': 'failed', 'reason': None,
        'scope': 'invented-40-cluster-50000-arithmetic-document-slices-only',
        'stage': 'preflight', 'root': str(root),
        'source_revision': expected_revision,
        'source_pins_before': source_before,
        'runtime_before': runtime_before,
        'producer_root': binding['source_root'],
        'producer_source_revision': binding['producer_source_revision'],
        'producer_result_pin': copy.deepcopy(expected_producer_result_pin),
        'producer_projection_pins': copy.deepcopy(expected_projection_pins),
        'external_producer_logical_bytes_outside_budget':
            binding['external_source_logical_bytes'],
        'external_preflight_inside_budget': False,
        'same_budget_50000_arithmetic_document_slices_measured': False,
        'both_arithmetic_children_verified': False,
    }
    budget = None
    critical = None
    try:
        budget = ContiguousBudget(root, limits).start()
        budget.checkpoint('preflight')
        draw_bridge.stage_runtime_profiles(root, profiles, revision=expected_revision, budget=budget,
            source_pins=source_before, runtime=runtime_before, result=result)
        input_value = draw_bridge._input(binding)
        draw_bridge._check_input(input_value)
        result['input_pin'] = _write_value(root / 'input.json', input_value,
                                           512 * 1024)
        calculation, audit = _arithmetic(root, result['input_pin'], budget, result)
        # Recheck the exact child input and both saved outputs before mapping.
        if draw_bridge.projection.v.strict_json(draw_bridge._read(
                root / 'input.json', result['input_pin'], 512 * 1024)) != input_value:
            raise ValueError('contiguous saved draw input changed')
        before_document_binding, before_document_input, before_document_source = _external(
            producer_root, expected_producer_result_pin, expected_projection_pins)
        if (before_document_binding != binding or
                before_document_input != producer_input or
                before_document_source != slice_source):
            raise ValueError('external producer changed before document mapping')
        result['stage'] = 'document'
        document, schema = _document(root, binding, producer_input, calculation,
                                     audit, budget, result)
        result['stage'] = 'slices'
        _slices(root, binding, producer_input, slice_source, document, schema,
                budget, result)
        result['stage'] = 'postflight'
        budget.checkpoint('postflight')
        after_binding, after_input, after_source = _external(
            producer_root, expected_producer_result_pin, expected_projection_pins)
        if (after_binding != binding or after_input != producer_input or
                after_source != slice_source):
            raise ValueError('external producer changed during contiguous trial')
        if (_source_pins(expected_revision) != source_before or
                platform_runtime.probe_runtime(ROOT) != runtime_before):
            raise ValueError('contiguous source/runtime changed')
        for name, pin, maximum in (
                ('input.json', result['input_pin'], 512 * 1024),
                ('calculation.json', result['calculation_pin'], draw_bridge.OUTPUT_BYTES),
                ('audit.json', result['arithmetic_audit_pin'], draw_bridge.OUTPUT_BYTES),
                ('document.json', result['document_pin'], document_bridge.MAX_DOCUMENT_BYTES),
                ('slices.json', result['slices_pin'], slice_bridge.MAX_SLICES_BYTES),
                ('slice-count-audit.json', result['slice_count_audit_pin'], MAX_CONTROL)):
            draw_bridge._read(root / name, pin, maximum)
        draw_bridge.recheck_runtime_profiles(root, result)
        if profiles is not None:
            budget.checkpoint('postflight')
        result['status'] = 'measured'
        result['stage'] = 'complete'
    except draw_bridge.draw_budget.UnreapedMeasurement as error:
        result.update(reason='owned_child_exit_unconfirmed',
                      unreaped_role=error.role, worker_exit_confirmed=False)
        error.receipt = root
        critical = error
    except draw_bridge.resources.ResourceStop as error:
        result['reason'] = error.reason
    except (ValueError, OSError, KeyError, TypeError,
            subprocess.SubprocessError) as error:
        result.update(reason='contiguous_trial_rejected',
                      error_type=type(error).__name__, detail=str(error)[:500])
    except BaseException as error:
        result.update(reason='unexpected_contiguous_exception',
                      error_type=type(error).__name__)
        critical = error
    finally:
        if budget is not None and budget._thread is not None:
            try:
                report = budget.close()
                result['resource_budget_pin'] = _write_value(
                    root / 'resource-budget.json', report, MAX_CONTROL)
                result['shared_budget_passed'] = report['passed']
                result['both_arithmetic_child_exits_reported'] = report[
                    'both_arithmetic_child_exits_reported']
                result['all_mapping_outputs_reported'] = report[
                    'all_mapping_outputs_reported']
                if (result['status'] == 'measured' and
                        (not report['passed'] or
                         not report['both_arithmetic_child_exits_reported'] or
                         not report['all_mapping_outputs_reported'])):
                    result.update(status='failed', reason=report['stop_reason'] or
                                  'contiguous_completion_incomplete')
            except BaseException as error:
                result.update(status='failed', reason='contiguous_budget_close_failed',
                              budget_error_type=type(error).__name__)
                critical = critical or error
        result['same_budget_50000_arithmetic_document_slices_measured'] = (
            result['status'] == 'measured')
        result['wall_seconds'] = time.monotonic() - started
        try:
            result_pin = _write_value(root / 'result.json', result, MAX_CONTROL)
        except BaseException as error:
            critical = critical or error
    if critical is not None:
        raise critical
    return {**result, 'result_pin': result_pin, 'receipt_root': str(root)}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 7:
        raise SystemExit('usage: TRIAL_NAME PRODUCER_ROOT RESULT_BYTES RESULT_SHA256 '
                         'PROJECTION_PINSET_PATH PINSET_BYTES PINSET_SHA256')
    name, producer_root, result_bytes, result_sha, pinset_path, pinset_bytes, pinset_sha = argv
    path = Path(pinset_path).absolute()
    if not path.is_relative_to(ROOT / 'artifacts'):
        raise ValueError('external projection pinset must be under artifacts')
    raw = draw_bridge._read(path, {'bytes': int(pinset_bytes),
                                   'sha256': pinset_sha}, MAX_CONTROL)
    pins = draw_bridge.projection.v.strict_json(raw)
    revision = subprocess.check_output(
        ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'],
        text=True, timeout=10).strip()
    result = run_chain(
        expected_mode='fixture', producer_root=producer_root,
        expected_producer_result_pin={'bytes': int(result_bytes),
                                      'sha256': result_sha},
        expected_projection_pins=pins, expected_revision=revision,
        receipt_name=name)
    print(draw_bridge._raw({
        'status': result['status'], 'reason': result['reason'],
        'receipt_root': result['receipt_root'],
        'result_pin': result['result_pin'],
    }).decode('utf-8'))
    return 0 if result['status'] == 'measured' else 2


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except draw_bridge.draw_budget.UnreapedMeasurement as owner:
        draw_bridge.draw_budget.retain_unreaped_owner(owner)
        raise
