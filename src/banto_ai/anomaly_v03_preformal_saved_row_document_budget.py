"""Pinned invented reader controls -> full draws, audit, document and slices.

Supplied control bytes are loaded by the caller before this clock. The disk
entry reads a fixed, externally pinned control inventory inside the clock.
Validation, projection, owned arithmetic children and mappings share one
sampled budget. Optional local publication adds an owned writer and fresh
reader. No producer or raw observation derivation is run.
"""
from __future__ import annotations

import copy
from pathlib import Path
import subprocess
import time

from . import anomaly_v03_preformal_contiguous_document_budget as chain
from . import anomaly_v03_saved_row_fixture_projection as projection
from . import anomaly_v03_saved_row_document_publication as publication
from . import anomaly_v03_saved_control_file_reader as control_files
from . import anomaly_v03_observation_subset_fixture_projection as subset_projection
from . import _anomaly_v03_outer_budget_link as outer_link


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
    'src/banto_ai/anomaly_v03_observation_subset_fixture_projection.py',
    'src/banto_ai/_anomaly_v03_outer_budget_link.py',
    *publication.SOURCE_NAMES,
    *control_files.SOURCE_NAMES,
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


class ObservationSubsetBudget(control_files.ControlFileBudget):
    def close(self):
        report = super().close()
        report.update(format=subset_projection.PIPELINE_FORMAT + '-resource-budget',
                      scope=subset_projection.SCOPE,
                      observation_subset_control_loading_inside_budget=False,
                      observation_payload_reader_executed_inside_budget=False,
                      complete_observation_campaign_verified=False)
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


def _prepare(entries, revision, expected_pins, observation_subset=None,
             expected_observation_subset=None):
    if observation_subset is None:
        prepared = projection.prepare_inputs(
            entries, expected_mode='fixture', expected_revision=revision,
            draws=[list(range(40))])
    else:
        prepared = subset_projection.prepare_inputs(entries, observation_subset,
            expected_subset=expected_observation_subset, expected_mode='fixture',
            expected_revision=revision, draws=[list(range(40))])
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


def _recheck_controls(entries, binding):
    """Verify the identical pinned bytes; their pure projection is unchanged."""
    chunks = binding.get('metadata_source_chunks', binding['source_chunks'])
    projection.v.require(type(entries) is list and len(entries) == len(chunks),
                         'saved-row control inventory changed')
    names = set(projection.coverage.RAW_LIMITS)
    for entry, chunk in zip(entries, chunks):
        projection.v.require(type(entry) is dict and set(entry) ==
                             {name + '_raw' for name in names} | {'expected_pins'},
                             'saved-row control fields changed')
        projection.evidence._same(entry['expected_pins'], chunk['entry_pins'],
                                  'saved-row external pins changed')
        for name, maximum in projection.coverage.RAW_LIMITS.items():
            raw = entry[name + '_raw']
            projection.v.require(type(raw) is bytes and 0 < len(raw) <= maximum,
                                 'saved-row control byte bound changed')
            projection.evidence._raw(raw, chunk['entry_pins'][name],
                                     'saved-row retained ' + name + ' pin')


def run_saved_rows(entries, *, expected_mode, expected_input_pins,
                   expected_revision, receipt_name, receipt_parent=OUTPUT_PARENT,
                   budget_limits=None, publish_document=False,
                   control_root=None, expected_control_pinset_pin=None,
                   observation_subset=None, expected_observation_subset=None,
                   outer_budget=None, arithmetic_runtime_profiles=None):
    """Run a new invented attempt; optionally include owned local publication."""
    if type(publish_document) is not bool:
        raise ValueError('publication selection must be boolean')
    if type(expected_mode) is not str or expected_mode != 'fixture':
        raise ValueError('only invented saved-row document mode is open')
    disk_controls = control_root is not None or expected_control_pinset_pin is not None
    if disk_controls:
        if entries is not None or control_root is None or expected_control_pinset_pin is None or not publish_document:
            raise ValueError('disk control route requires no supplied entries and local publication')
        control_root = control_files.validate_request(control_root, expected_control_pinset_pin)
        expected_control_pinset_pin = copy.deepcopy(expected_control_pinset_pin)
    subset_mode = observation_subset is not None or expected_observation_subset is not None
    if subset_mode:
        if not disk_controls:
            raise ValueError('observation-subset route requires pinned disk controls and publication')
        expected_observation_subset = subset_projection.validate_subset_request(
            observation_subset, expected_observation_subset)
    projection.evidence._digest(expected_revision, 40)
    profiles = chain.draw_bridge.validate_runtime_profiles(arithmetic_runtime_profiles,
                                                           revision=expected_revision)
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
    if outer_budget is not None:
        if not subset_mode:
            raise ValueError('outer composition requires the observation subset route')
        outer_budget.require_stage('publication', parent / receipt_name)
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
    if publish_document:
        result.update(format=publication.FORMAT, scope=publication.SCOPE,
                      same_budget_saved_rows_to_fresh_reader_measured=False,
                      local_publication_performed=False, publication_status='not_started',
                      reader_status='not_started', writer_reaped_before_reader_start=False,
                      runtime_scope='serialized-dedicated-caller-platform-fixture-v2',
                      concurrent_calls_supported=False)
    if disk_controls:
        result.update(format=control_files.PIPELINE_FORMAT, scope=control_files.SCOPE,
                      input_kind='pinned invented saved-control files',
                      saved_control_loading_inside_budget=True,
                      saved_control_disk_reread_inside_budget=True,
                      control_fixture_root=str(control_root),
                      external_control_pinset_pin=expected_control_pinset_pin,
                      external_saved_control_bytes_in_directory_budget=False,
                      same_budget_control_disk_to_fresh_reader_measured=False,
                      control_disk_pin_recheck_completed=False,
                      real_saved_chunk_reader_used=False, producer_executed_here=False)
    if subset_mode:
        result.update(format=subset_projection.PIPELINE_FORMAT, scope=subset_projection.SCOPE,
            input_kind='invented metadata fixture plus externally retained saved-reader subset claims',
            expected_observation_subset=expected_observation_subset,
            observation_subset_control_loading_inside_budget=False,
            observation_payload_reader_executed_inside_budget=False,
            complete_observation_campaign_verified=False,
            same_budget_subset_rows_to_fresh_reader_measured=False,
            same_budget_observation_reader_to_fresh_reader_measured=False)
    budget = None
    loaded = None
    critical = None
    result_pin = None
    try:
        budget_type = (ObservationSubsetBudget if subset_mode else
                       control_files.ControlFileBudget if disk_controls else
                       publication.PublicationBudget if publish_document else SavedRowBudget)
        budget = budget_type(root, limits)
        if outer_budget is not None:
            budget = outer_link.LinkedBudget(budget, outer_budget, stage='publication')
        budget = budget.start()
        budget.checkpoint('preflight')
        before = _source_pins(expected_revision)
        runtime = chain.platform_runtime.probe_runtime(ROOT)
        result.update(source_pins_before=before, runtime_before=runtime)
        chain.draw_bridge.stage_runtime_profiles(root, profiles, revision=expected_revision,
            budget=budget, source_pins=before, runtime=runtime, result=result)
        if disk_controls:
            result['stage'] = 'control-read'
            loaded = control_files.load_controls(control_root,
                expected_pinset_pin=expected_control_pinset_pin, budget=budget)
            entries = loaded['entries']
            result['control_file_read_pin'] = chain._write_value(
                root / 'control-files.json', loaded['summary'], chain.MAX_CONTROL)
            result['stage'] = 'preflight'
            budget.checkpoint('preflight')
        if subset_mode:
            prepared = _prepare(entries, expected_revision, expected_input_pins,
                                observation_subset, expected_observation_subset)
            combined_bytes = prepared['binding']['combined_control_input_bytes'] + len(loaded['index_raw'])
            if combined_bytes > control_files.MAX_INPUT_BYTES:
                raise ValueError('combined index, metadata and subset input byte bound')
            result.update(subset_chunks=prepared['binding']['subset_chunks'],
                subset_evaluations=prepared['binding']['subset_evaluations'],
                remaining_metadata_chunks=prepared['binding']['remaining_metadata_chunks'],
                affected_seed_indices=prepared['binding']['affected_seed_indices'],
                combined_control_input_bytes_including_index=combined_bytes,
                observation_subset_projected_input_pins=prepared['binding']['worker_input_pins'])
        else:
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
        budget.checkpoint('document')
        _recheck_controls(entries, prepared['binding'])
        if subset_mode:
            subset_projection.recheck_subset(observation_subset, expected_observation_subset)
        document, schema = chain._document(
            root, binding, fixture, calculation, audit, budget, result)
        result['stage'] = 'slices'
        chain._slices(root, binding, fixture, slices, document, schema, budget, result)
        if publish_document:
            publication.publish(root, budget, result, expected_revision, before, expected_input_pins)
        if disk_controls:
            result['stage'] = 'control-reread'
            result['control_disk_recheck'] = control_files.recheck_controls(loaded, budget=budget)
            result['control_disk_pin_recheck_completed'] = True
        result['stage'] = 'postflight'
        budget.checkpoint('postflight')
        # The deterministic projection is bound to these exact immutable raw
        # bytes and the unchanged source; rehash without parsing/pooling twice.
        _recheck_controls(entries, prepared['binding'])
        if subset_mode:
            subset_projection.recheck_subset(observation_subset, expected_observation_subset)
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
        if disk_controls:
            chain.draw_bridge._read(root / 'control-files.json', result['control_file_read_pin'], chain.MAX_CONTROL)
        budget.checkpoint('postflight')
        chain.draw_bridge.recheck_runtime_profiles(root, result)
        result.update(status='measured', stage='complete',
                      source_pins_after=before, runtime_after=runtime)
    except chain.draw_bridge.draw_budget.UnreapedMeasurement as error:
        result.update(reason='owned_child_exit_unconfirmed',
                      unreaped_role=error.role, worker_exit_confirmed=False)
        error.receipt = root
        critical = error
    except publication.supervisor.UnreapedWorker as error:
        result.update(reason='owned_publication_child_exit_unconfirmed',
                      worker_exit_confirmed=False)
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
                if publish_document:
                    result['all_four_child_exits_reported'] = report['all_four_child_exits_reported']
                if result['status'] == 'measured' and (
                        not report['passed'] or not report['both_arithmetic_child_exits_reported']
                        or not report['all_mapping_outputs_reported'] or
                        (publish_document and not report['all_four_child_exits_reported'])):
                    result.update(status='failed', reason=report['stop_reason'] or
                                  'saved_row_document_completion_incomplete')
            except BaseException as error:
                result.update(status='failed', reason='saved_row_document_budget_close_failed',
                              budget_error_type=type(error).__name__)
                critical = critical or error
        result['same_budget_50000_arithmetic_document_slices_measured'] = (
            result['status'] == 'measured')
        if publish_document:
            result['same_budget_saved_rows_to_fresh_reader_measured'] = result['status'] == 'measured'
        if disk_controls:
            result['same_budget_control_disk_to_fresh_reader_measured'] = (
                result['status'] == 'measured' and result['control_disk_pin_recheck_completed'])
        if subset_mode:
            result['same_budget_subset_rows_to_fresh_reader_measured'] = result['status'] == 'measured'
        result['wall_seconds'] = time.monotonic() - started
        try:
            result_pin = chain._write_value(root / 'result.json', result, chain.MAX_CONTROL)
        except BaseException as error:
            critical = critical or error
    if critical is not None:
        raise critical
    return {**result, 'result_pin': result_pin, 'receipt_root': str(root)}


def run_saved_control_files(*, control_root, expected_control_pinset_pin,
                            expected_mode, expected_input_pins, expected_revision,
                            receipt_name, receipt_parent=OUTPUT_PARENT, budget_limits=None,
                            arithmetic_runtime_profiles=None):
    """Read fixed control files and finish local publication under one clock."""
    return run_saved_rows(None, expected_mode=expected_mode,
        expected_input_pins=expected_input_pins, expected_revision=expected_revision,
        receipt_name=receipt_name, receipt_parent=receipt_parent, budget_limits=budget_limits,
        publish_document=True, control_root=control_root,
        expected_control_pinset_pin=expected_control_pinset_pin,
        arithmetic_runtime_profiles=arithmetic_runtime_profiles)


def run_saved_control_files_with_observation_subset(*, observation_subset,
        expected_observation_subset, control_root, expected_control_pinset_pin,
        expected_mode, expected_input_pins, expected_revision,
        receipt_name, receipt_parent=OUTPUT_PARENT, budget_limits=None,
        outer_budget=None, arithmetic_runtime_profiles=None):
    """Full numerical fixture with explicit prior-reader subset provenance.

    The subset's raw observations and reader execution precede this clock.
    Its rows share the clock with control loading, projection and publication.
    """
    return run_saved_rows(None, expected_mode=expected_mode,
        expected_input_pins=expected_input_pins, expected_revision=expected_revision,
        receipt_name=receipt_name, receipt_parent=receipt_parent, budget_limits=budget_limits,
        publish_document=True, control_root=control_root,
        expected_control_pinset_pin=expected_control_pinset_pin,
        observation_subset=observation_subset,
        expected_observation_subset=expected_observation_subset,
        outer_budget=outer_budget, arithmetic_runtime_profiles=arithmetic_runtime_profiles)
