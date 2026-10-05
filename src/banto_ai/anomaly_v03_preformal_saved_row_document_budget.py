"""Pinned invented reader controls -> full draws, audit, document and slices.

The caller loads the control bytes before this clock. Their validation and
projection, both owned arithmetic children and all mappings share one sampled
budget. No producer, observation derivation, writer or fresh reader is run.
"""
from __future__ import annotations

import copy
from pathlib import Path
import subprocess
import time

from . import anomaly_v03_preformal_contiguous_document_budget as chain
from . import anomaly_v03_saved_row_fixture_projection as projection


ROOT = chain.ROOT
OUTPUT_PARENT = ROOT / 'artifacts/anomaly-v03-preformal-saved-row-document-budget'
FORMAT = 'anomaly-v03-preformal-saved-row-document-budget-v1'
SCOPE = 'pinned-invented-saved-rows-to-50000-arithmetic-document-slices-only'
SOURCE_NAMES = tuple(dict.fromkeys((
    'src/banto_ai/anomaly_v03_preformal_saved_row_document_budget.py',
    'src/banto_ai/anomaly_v03_saved_row_fixture_projection.py',
    'src/banto_ai/anomaly_v03_preformal_saved_row_coverage.py',
    'src/banto_ai/anomaly_v03_preformal_saved_seed_contribution.py',
    'src/banto_ai/anomaly_v03_registered_saved_row_lineage.py',
    'src/banto_ai/anomaly_v03_registered_saved_summary.py',
    *chain.SOURCE_NAMES,
)))


class SavedRowBudget(chain.ContiguousBudget):
    def close(self):
        report = super().close()
        report['format'] = FORMAT + '-resource-budget'
        report['scope'] = SCOPE
        report['saved_control_loading_inside_budget'] = False
        report['saved_control_projection_inside_budget'] = True
        return report


def _source_pins(revision):
    projection.evidence._digest(revision, 40)

    def git(*args):
        return subprocess.check_output(['git', '-C', str(ROOT), *args],
                                       stderr=subprocess.DEVNULL, timeout=10)

    if (git('rev-parse', 'HEAD').decode().strip() != revision or
            git('status', '--porcelain').strip()):
        raise ValueError('saved-row document trial requires clean expected HEAD')
    pins = {}
    for name in SOURCE_NAMES:
        raw = chain.draw_bridge.draw_budget._bounded_file(ROOT / name, 1024**2)
        if raw != git('show', revision + ':' + name):
            raise ValueError('saved-row document source differs from Git: ' + name)
        pins[name] = chain.draw_bridge._pin(raw)
    return pins


def _expected_pins(pins):
    if type(pins) is not dict or set(pins) != set(projection.analysis.INPUT_LIMITS):
        raise ValueError('saved-row external projection pin inventory')
    for name, pin in pins.items():
        projection.evidence._pin(pin)
        if not 0 < pin['bytes'] <= projection.analysis.INPUT_LIMITS[name]:
            raise ValueError('saved-row external projection input byte limit')


def _prepare(entries, revision, expected_pins):
    prepared = projection.prepare_inputs(
        entries, expected_mode='fixture', expected_revision=revision,
        draws=[list(range(40))])
    if prepared['binding']['worker_input_pins'] != expected_pins:
        raise ValueError('saved-row external projection pins differ')
    return prepared


def _draw_input(binding, revision):
    value = {
        'format': chain.draw_bridge.SAVED_ROW_INPUT_FORMAT,
        'invented_only': True, 'registered_data_read': False,
        'saved_row_projection_pin': copy.deepcopy(binding['saved_row_projection_pin']),
        'projection_input_pins': copy.deepcopy(binding['projection_pins']),
        'projection_source_revision': revision, 'clusters': binding['clusters'],
    }
    chain.draw_bridge._check_input(value)
    return value


def run_saved_rows(entries, *, expected_mode, expected_input_pins,
                   expected_revision, receipt_name, receipt_parent=OUTPUT_PARENT,
                   budget_limits=None):
    """Run a new non-overwriting invented attempt, with exactly two children."""
    if type(expected_mode) is not str or expected_mode != 'fixture':
        raise ValueError('only invented saved-row document mode is open')
    projection.evidence._digest(expected_revision, 40)
    _expected_pins(expected_input_pins)
    expected_input_pins = copy.deepcopy(expected_input_pins)
    projection.v.safe_relative_path(receipt_name)
    if ('/' in receipt_name or '\\' in receipt_name or
            not receipt_name.startswith('trial-')):
        raise ValueError('new saved-row document trial name required')
    parent = Path(receipt_parent).absolute()
    if parent != OUTPUT_PARENT:
        raise ValueError('saved-row document output parent differs')
    limits = chain._limits(budget_limits)
    parent.mkdir(exist_ok=True)
    chain.draw_bridge.projection.io.regular_path(parent, directory=True)
    root = chain.draw_bridge.projection.io.regular_path(
        parent / receipt_name, directory=True, missing=True)
    root.mkdir()
    started = time.monotonic()
    result = {
        **chain.CLOSED, 'format': FORMAT, 'scope': SCOPE,
        'status': 'failed', 'reason': None, 'stage': 'preflight',
        'root': str(root), 'source_revision': expected_revision,
        'input_kind': 'invented saved-reader control bytes',
        'expected_input_pins': expected_input_pins,
        'saved_reader_control_inputs_used': True,
        'saved_control_loading_inside_budget': False,
        'saved_control_projection_inside_budget': True,
        'raw_observation_derivation_checked': False,
        'campaign_coherence_authenticated': False,
        'historical_producer_execution_authenticated': False,
        'new_evaluations': 0,
        'same_budget_50000_arithmetic_document_slices_measured': False,
        'both_arithmetic_children_verified': False,
    }
    budget = None
    critical = None
    result_pin = None
    try:
        budget = SavedRowBudget(root, limits).start()
        budget.checkpoint('preflight')
        before = _source_pins(expected_revision)
        runtime = chain.platform_runtime.probe_runtime(ROOT)
        result.update(source_pins_before=before, runtime_before=runtime)
        prepared = _prepare(entries, expected_revision, expected_input_pins)
        budget.checkpoint('preflight')
        projection_pin = chain._write_value(
            root / 'projection.json', prepared['binding'], projection.MAX_BINDING_BYTES)
        (root / 'inputs').mkdir()
        for name, raw in prepared['files'].items():
            chain.draw_bridge._write(root / 'inputs' / Path(name).name, raw)
        fixture = projection.v.strict_json(prepared['files']['fixture/input.json'])
        slices = projection.v.strict_json(prepared['files']['fixture/slices.json'])
        binding = {'clusters': fixture['clusters'],
                   'projection_pins': copy.deepcopy(expected_input_pins),
                   'saved_row_projection_pin': projection_pin}
        result.update(
            saved_row_projection_pin=projection_pin,
            coverage=copy.deepcopy(prepared['binding']['coverage']),
            declared_historical_source_revision=
                prepared['binding']['declared_historical_source_revision'],
            inherited_failed_attempts=len(prepared['binding']['failed_attempt_history']))
        draw_input = _draw_input(binding, expected_revision)
        result['input_pin'] = chain._write_value(root / 'input.json', draw_input, 512 * 1024)
        calculation, audit = chain._arithmetic(root, result['input_pin'], budget, result)
        result['stage'] = 'document'
        document, schema = chain._document(
            root, binding, fixture, calculation, audit, budget, result)
        result['stage'] = 'slices'
        chain._slices(root, binding, fixture, slices, document, schema, budget, result)
        result['stage'] = 'postflight'
        budget.checkpoint('postflight')
        # Revalidate all pinned caller bytes and integer contributions. No
        # consumer is replayed and no historical process claim is upgraded.
        after = _prepare(entries, expected_revision, expected_input_pins)
        if after != prepared:
            raise ValueError('saved-row controls changed during document trial')
        if (_source_pins(expected_revision) != before or
                chain.platform_runtime.probe_runtime(ROOT) != runtime):
            raise ValueError('saved-row document source/runtime changed')
        for name, raw in prepared['files'].items():
            chain.draw_bridge._read(root / 'inputs' / Path(name).name,
                                    expected_input_pins[name],
                                    projection.analysis.INPUT_LIMITS[name])
        outputs = (
            ('projection.json', projection_pin, projection.MAX_BINDING_BYTES),
            ('input.json', result['input_pin'], 512 * 1024),
            ('calculation.json', result['calculation_pin'], chain.draw_bridge.OUTPUT_BYTES),
            ('audit.json', result['arithmetic_audit_pin'], chain.draw_bridge.OUTPUT_BYTES),
            ('document.json', result['document_pin'], chain.document_bridge.MAX_DOCUMENT_BYTES),
            ('slices.json', result['slices_pin'], chain.slice_bridge.MAX_SLICES_BYTES),
            ('slice-count-audit.json', result['slice_count_audit_pin'], chain.MAX_CONTROL),
        )
        for name, pin, maximum in outputs:
            chain.draw_bridge._read(root / name, pin, maximum)
        budget.checkpoint('postflight')
        result.update(status='measured', stage='complete',
                      source_pins_after=before, runtime_after=runtime)
    except chain.draw_bridge.draw_budget.UnreapedMeasurement as error:
        result.update(reason='owned_child_exit_unconfirmed',
                      unreaped_role=error.role, worker_exit_confirmed=False)
        error.receipt = root
        critical = error
    except chain.draw_bridge.resources.ResourceStop as error:
        result['reason'] = error.reason
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as error:
        result.update(reason='saved_row_document_rejected',
                      error_type=type(error).__name__, detail=str(error)[:500])
    except BaseException as error:
        result.update(reason='unexpected_saved_row_document_exception',
                      error_type=type(error).__name__)
        critical = error
    finally:
        if budget is not None and budget._thread is not None:
            try:
                report = budget.close()
                result['resource_budget_pin'] = chain._write_value(
                    root / 'resource-budget.json', report, chain.MAX_CONTROL)
                result['shared_budget_passed'] = report['passed']
                result['both_arithmetic_child_exits_reported'] = report[
                    'both_arithmetic_child_exits_reported']
                result['all_mapping_outputs_reported'] = report[
                    'all_mapping_outputs_reported']
                if result['status'] == 'measured' and (
                        not report['passed'] or not report['both_arithmetic_child_exits_reported']
                        or not report['all_mapping_outputs_reported']):
                    result.update(status='failed', reason=report['stop_reason'] or
                                  'saved_row_document_completion_incomplete')
            except BaseException as error:
                result.update(status='failed', reason='saved_row_document_budget_close_failed',
                              budget_error_type=type(error).__name__)
                critical = critical or error
        result['same_budget_50000_arithmetic_document_slices_measured'] = (
            result['status'] == 'measured')
        result['wall_seconds'] = time.monotonic() - started
        try:
            result_pin = chain._write_value(root / 'result.json', result, chain.MAX_CONTROL)
        except BaseException as error:
            critical = critical or error
    if critical is not None:
        raise critical
    return {**result, 'result_pin': result_pin, 'receipt_root': str(root)}
