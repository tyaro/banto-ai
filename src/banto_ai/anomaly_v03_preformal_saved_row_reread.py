"""Re-read one pinned invented saved chunk and project its six rows.

The source is an already retained invented g02-style fixture, outside the new
attempt root.  One newly owned child reopens its raw payloads.  The parent then
compares the entire fresh reader value with the old pinned value and projects
the rows while one cooperative fixture budget is live.  This is one chunk of
preformal evidence, not a registered campaign or a formal budget.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys

from . import _anomaly_v03_fixture_budget as budget_module
from . import _anomaly_v03_io as io
from . import _anomaly_v03_runtime as paths
from . import _anomaly_v03_engineering_runtime as resources
from . import anomaly_v03 as v
from . import anomaly_v03_observation_audit as pinned
from . import anomaly_v03_platform_fixture as platform
from . import anomaly_v03_platform_fixture_runtime as runtime
from . import anomaly_v03_preformal_owned_generated_attempt as generated
from . import anomaly_v03_preformal_owned_saved_attempt as copied
from . import anomaly_v03_process_supervisor as supervisor
from . import anomaly_v03_reader_evidence as observed
from . import anomaly_v03_registered_saved_attempt_fixture as fixture
from . import anomaly_v03_registered_saved_row_lineage as lineage
from . import anomaly_v03_registered_saved_summary as saved


ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'anomaly-v03-preformal-saved-row-reread-'
FORMAT = 'anomaly-v03-preformal-saved-row-reread-v1'
CHILD_FORMAT = 'anomaly-v03-preformal-saved-row-reread-child-v1'
INVOCATION_FORMAT = 'anomaly-v03-preformal-saved-row-reread-invocation-v1'
BOOTSTRAP = ('import sys;sys.path.insert(0,sys.argv.pop(1));'
             'from banto_ai.anomaly_v03_preformal_saved_row_reread import reader_worker_main;'
             'raise SystemExit(reader_worker_main(sys.argv[1:]))')
MAX_MANIFEST = 256 * 1024
MAX_OUTER = 256 * 1024
MAX_INVOCATION = 256 * 1024
MAX_ROWS = 512 * 1024
MAX_RESULT = 32 * 1024
MAX_BUDGET = 32 * 1024
RESERVE_BYTES = budget_module.RECEIPT_RESERVE
MANIFEST_FIELDS = {
    'format', 'scope', 'root', 'revision', 'chunk_index', 'recipe_id',
    'source', 'source_snapshots', 'source_snapshot_pins', 'output_pins',
    'output_file_count', 'output_bytes', 'invented_only',
    'actual_registered_observations_read', 'formal_permission',
}
SOURCE_FILES = (
    'src/banto_ai/anomaly_v03_preformal_saved_row_reread.py',
    'tools/preformal_saved_row_reread_trial.py',
    'src/banto_ai/anomaly_v03_registered_saved_row_lineage.py',
    'src/banto_ai/anomaly_v03_registered_saved_attempt_fixture.py',
    'src/banto_ai/anomaly_v03_registered_evaluation_contract.py',
    'src/banto_ai/anomaly_v03_registered_saved_summary.py',
    'src/banto_ai/anomaly_v03_score_audit.py',
    'src/banto_ai/anomaly_v03_preformal_owned_generated_attempt.py',
    'src/banto_ai/anomaly_v03_preformal_owned_saved_attempt.py',
    'src/banto_ai/anomaly_v03_observation_audit.py',
    'src/banto_ai/anomaly_v03_reader_evidence.py',
    'src/banto_ai/anomaly_v03_platform_fixture_runtime.py',
    'src/banto_ai/anomaly_v03_process_supervisor.py',
    'src/banto_ai/_anomaly_v03_fixture_budget.py',
)


def _pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def _source(revision):
    """A selected current checkout check, never complete S4 source closure."""
    v.require(type(revision) is str and re.fullmatch(r'[0-9a-f]{40}', revision),
              'current full source revision required')
    head = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'],
                                   stderr=subprocess.DEVNULL, timeout=10).decode().strip()
    v.require(head == revision, 'current source revision changed')
    dirty = subprocess.check_output(
        ['git', '-c', 'core.fsmonitor=false', '-C', str(ROOT), 'status',
         '--porcelain', '--untracked-files=normal'],
        stderr=subprocess.DEVNULL, timeout=10)
    v.require(not dirty, 'clean current source checkout required')
    rows = []
    for name in SOURCE_FILES:
        working = observed._file(ROOT / name, 1024**2)
        committed = subprocess.check_output(
            ['git', '-C', str(ROOT), 'show', revision + ':' + name],
            stderr=subprocess.DEVNULL, timeout=10)
        v.require(working == committed, 'current source bytes changed: ' + name)
        rows.append({'path': name, 'pin': _pin(working)})
    return {'revision': revision, 'selected_files': rows,
            'scope': 'selected-working-git-raw-only-not-source-closure'}


def _roots(source_root, output_root):
    source = paths.regular_path(Path(source_root), directory=True)
    target = paths.regular_path(Path(output_root), directory=True, missing=True)
    v.require(source.parent == ROOT / 'artifacts' and
              source.name.startswith(fixture.PREFIX) and
              target.parent == ROOT / 'artifacts' and
              target.name.startswith(PREFIX) and
              source != target and not target.exists(),
              'distinct existing invented source and new reread root required')
    suffix = source.name.removeprefix(fixture.PREFIX)
    manifest_path = source.parent / ('anomaly-v03-preformal-generated-pinsets-' +
                                     suffix) / 'pins.json'
    paths.regular_path(manifest_path)
    return source, target, manifest_path


def _manifest(raw, pin, source):
    v.require(_pin(raw) == pin, 'external manifest pin')
    manifest = v.strict_json(raw)
    v.require(raw == v.canonical_json(manifest) and
              type(manifest) is dict and set(manifest) == MANIFEST_FIELDS,
              'exact canonical invented manifest')
    for name, wanted in {
        'format': 'anomaly-v03-preformal-owned-generated-external-pins-v1',
        'scope': 'invented-registered-format-owned-generator-only',
        'root': str(source), 'recipe_id': generated.RECIPE,
        'invented_only': True, 'actual_registered_observations_read': False,
        'formal_permission': False,
    }.items():
        v.require(manifest[name] == wanted, 'invented manifest ' + name)
    v.require(type(manifest['chunk_index']) is int and
              0 <= manifest['chunk_index'] < 480 and
              type(manifest['revision']) is str and
              re.fullmatch(r'[0-9a-f]{40}', manifest['revision']),
              'invented manifest chunk and historical revision')
    names = generated._outputs(source, manifest['chunk_index'])
    pins = manifest['output_pins']
    generated._validate_pins(names, pins)
    v.require(manifest['output_file_count'] == len(names) == 22 and
              manifest['output_bytes'] == sum(p['bytes'] for p in pins.values()),
              'exact invented output inventory/size')
    snapshots = copied._decode_source_snapshots(manifest['source_snapshots'])
    v.require(set(snapshots) == {manifest['revision']} and
              set(manifest['source_snapshot_pins']) ==
              set(snapshots[manifest['revision']]),
              'historical source snapshot inventory')
    for name, source_bytes in snapshots[manifest['revision']].items():
        v.require(_pin(source_bytes) == manifest['source_snapshot_pins'][name],
                  'historical source snapshot pin ' + name)
    return manifest, snapshots


def _read_saved_controls(source, pins):
    return (pinned.read_pinned(source / 'saved/receipt.json',
                               pins['saved/receipt.json'], saved.MAX_RECEIPT),
            pinned.read_pinned(source / 'saved/report.json',
                               pins['saved/report.json'], saved.MAX_REPORT))


def reader_worker_main(argv):
    """One owned child; the supervisor outside this function owns its exit."""
    try:
        v.require(len(argv) == 2, 'reread child arguments')
        path = paths.regular_path(Path(argv[0]))
        raw = observed._file(path, MAX_INVOCATION)
        v.require(_pin(raw)['sha256'] == argv[1], 'reread child invocation pin')
        request = v.strict_json(raw)
        v.require(raw == v.canonical_json(request) and
                  type(request) is dict and set(request) == {
                      'format', 'source_root', 'output_root', 'manifest_path',
                      'manifest_pin', 'external_pins', 'source_snapshots',
                      'chunk_index', 'current_revision', 'current_source',
                      'runtime', 'invocation_id'},
                  'exact reread child invocation')
        source, target, manifest_path = _roots_for_child(
            request['source_root'], request['output_root'])
        v.require(path == target / 'owned-reader/invocation.json' and
                  request['format'] == INVOCATION_FORMAT and
                  request['manifest_path'] == str(manifest_path),
                  'reread child controlled paths')
        manifest_raw = pinned.read_pinned(
            manifest_path, request['manifest_pin'], MAX_MANIFEST)
        manifest, snapshots = _manifest(
            manifest_raw, request['manifest_pin'], source)
        v.require(request['external_pins'] == manifest['output_pins'] and
                  request['source_snapshots'] == manifest['source_snapshots'] and
                  request['chunk_index'] == manifest['chunk_index'],
                  'reread child pinned manifest binding')
        current = _source(request['current_revision'])
        current_runtime = runtime.probe_runtime(ROOT)
        v.require(current == request['current_source'] and
                  current_runtime == request['runtime'],
                  'reread child current source/runtime changed')
        outputs, _ = copied._saved_outputs(source, manifest['chunk_index'],
                                           manifest['output_pins'])
        copied._check_outputs(source, outputs, manifest['output_pins'])
        external = manifest['output_pins']
        read = fixture.read_invented_registered_attempt(
            source, expected_mode=saved.MODE,
            chunk_index=manifest['chunk_index'],
            expected_registry_pin=external['saved/registry.json'],
            expected_savepoint_pin=external['saved/savepoint.json'],
            expected_receipt_pin=external['saved/receipt.json'],
            expected_report_pin=external['saved/report.json'],
            expected_payload_pins={key: pin for key, pin in external.items()
                                   if key not in copied.SAVED},
            source_snapshots=snapshots)
        copied._check_outputs(source, outputs, external)
        v.require(_source(request['current_revision']) == current and
                  runtime.probe_runtime(ROOT) == current_runtime and
                  pinned.read_pinned(manifest_path, request['manifest_pin'],
                                     MAX_MANIFEST) == manifest_raw,
                  'reread child postflight source/runtime/manifest')
        process = observed.creation_observation(os.getpid())
        reply = {'format': CHILD_FORMAT, 'status': 'read',
                 'invocation_id': request['invocation_id'],
                 'process': {'pid': os.getpid(), 'parent_pid': os.getppid(),
                             'start_token': process['start_token']},
                 'source': current, 'runtime': current_runtime,
                 'manifest_pin': request['manifest_pin'],
                 'output_pins': copy.deepcopy(external),
                 'reader_result': read,
                 'actual_registered_observations_read': False,
                 'formal_permission': False}
        print(json.dumps(reply, sort_keys=True))
        return 0
    except (ValueError, OSError, KeyError, TypeError, IndexError,
            subprocess.SubprocessError) as error:
        print(json.dumps({'format': CHILD_FORMAT, 'status': 'failed',
                          'error_type': type(error).__name__,
                          'detail': str(error), 'formal_permission': False},
                         sort_keys=True))
        return 2


def _roots_for_child(source_root, output_root):
    source = paths.regular_path(Path(source_root), directory=True)
    target = paths.regular_path(Path(output_root), directory=True)
    v.require(source.parent == ROOT / 'artifacts' and
              source.name.startswith(fixture.PREFIX) and
              target.parent == ROOT / 'artifacts' and
              target.name.startswith(PREFIX) and source != target,
              'reread child roots')
    suffix = source.name.removeprefix(fixture.PREFIX)
    manifest_path = source.parent / ('anomaly-v03-preformal-generated-pinsets-' +
                                     suffix) / 'pins.json'
    paths.regular_path(manifest_path)
    return source, target, manifest_path


def run_reread(source_root, output_root, *, expected_manifest_pin,
               expected_outer_result_pin, expected_revision):
    """Run an invented saved reader and row projection under one new budget."""
    source, target, manifest_path = _roots(source_root, output_root)
    for pin in (expected_manifest_pin, expected_outer_result_pin):
        copied.evidence._pin(pin)
    target.mkdir()
    budget = budget_module.FixtureBudget(target)
    started = False
    critical = None
    result = {
        'format': FORMAT, 'scope': 'one-invented-saved-chunk-reader-to-row-projection',
        'status': 'failed', 'reason': 'not_started',
        'source_root': str(source), 'output_root': str(target),
        'manifest_path': str(manifest_path),
        'manifest_pin': copy.deepcopy(expected_manifest_pin),
        'old_outer_result_pin': copy.deepcopy(expected_outer_result_pin),
        'current_revision': expected_revision,
        'external_saved_payload_bytes_in_directory_budget': False,
        'external_saved_payloads_reopened_in_child': False,
        'fresh_saved_payload_bytes_rechecked_this_run': False,
        'fresh_owned_reader_exit_confirmed_here': False,
        'fresh_reader_equal_prior_reader': False,
        'row_projection_in_same_budget': False,
        'child_exit_confirmed': False,
        'source_closure_complete': False,
        'runtime_closure_complete': False,
        'execution_authenticated': False,
        'result_trusted': False,
        'campaign_completed': False,
        'full_end_to_end_budget_measured': False,
        'registered_observations_read': False,
        'actual_registered_observations_read': False,
        'campaign_evaluations_credited': 0,
        'formal_permission': False, 'analysis_authorized': False,
        'promotion_allowed': False, 'independent_s6_complete': False,
    }
    try:
        budget.start()
        started = True
        budget.checkpoint()
        v.require(budget.limits['directory_bytes'] > RESERVE_BYTES +
                  copied.READER_LIMITS['output_bytes'] + MAX_INVOCATION,
                  'reread result reserve exceeds root budget')
        manifest_raw = pinned.read_pinned(manifest_path, expected_manifest_pin,
                                           MAX_MANIFEST)
        manifest, _ = _manifest(manifest_raw, expected_manifest_pin, source)
        external = manifest['output_pins']
        outer_raw = pinned.read_pinned(
            source / 'owned-generator/result.json', expected_outer_result_pin,
            MAX_OUTER)
        old_outer = v.strict_json(outer_raw)
        v.require(outer_raw == v.canonical_json(old_outer) and
                  old_outer.get('generated_output_pins') == external,
                  'pinned prior reader/output binding')
        receipt_raw, report_raw = _read_saved_controls(source, external)
        lineage._outer_reader(old_outer, external['saved/receipt.json'],
                              external['saved/report.json'],
                              manifest['chunk_index'])
        current_source = _source(expected_revision)
        current_runtime = runtime.probe_runtime(ROOT)
        result['chunk_index'] = manifest['chunk_index']
        result['historic_source_revision'] = manifest['revision']
        result['external_saved_payload_bytes'] = manifest['output_bytes']
        result['receipt_pin'] = copy.deepcopy(external['saved/receipt.json'])
        result['report_pin'] = copy.deepcopy(external['saved/report.json'])
        result['selected_current_source'] = current_source
        result['runtime'] = current_runtime
        reader_root = target / 'owned-reader'
        reader_root.mkdir()
        invocation = {
            'format': INVOCATION_FORMAT,
            'source_root': str(source), 'output_root': str(target),
            'manifest_path': str(manifest_path),
            'manifest_pin': copy.deepcopy(expected_manifest_pin),
            'external_pins': copy.deepcopy(external),
            'source_snapshots': manifest['source_snapshots'],
            'chunk_index': manifest['chunk_index'],
            'current_revision': expected_revision,
            'current_source': current_source, 'runtime': current_runtime,
            'invocation_id': secrets.token_hex(32),
        }
        invocation_raw = v.canonical_json(invocation)
        v.require(len(invocation_raw) <= MAX_INVOCATION,
                  'bounded reread child invocation')
        invocation_path = reader_root / 'invocation.json'
        io._exclusive(invocation_path, invocation_raw)
        invocation_pin = _pin(invocation_raw)
        result['invocation_pin'] = invocation_pin
        launch = {}

        def boundary():
            v.require(_source(expected_revision) == current_source and
                      runtime.probe_runtime(ROOT) == current_runtime and
                      pinned.read_pinned(manifest_path, expected_manifest_pin,
                                         MAX_MANIFEST) == manifest_raw and
                      pinned.read_pinned(
                          source / 'owned-generator/result.json',
                          expected_outer_result_pin, MAX_OUTER) == outer_raw and
                      _pin(observed._file(invocation_path, MAX_INVOCATION)) ==
                      invocation_pin,
                      'reread parent boundary changed')

        def on_started(process):
            launch.update(observed.creation_observation(
                process.pid, process._handle))

        budget.checkpoint()
        argv = [sys.executable, '-I', '-S', '-B', '-c', BOOTSTRAP,
                str(ROOT / 'src'), str(invocation_path), invocation_pin['sha256']]
        with platform._platform_scope():
            monitor = supervisor.supervise(
                argv, ROOT, reader_root / 'worker', copied.READER_LIMITS,
                boundary=boundary, on_started=on_started,
                resource_probe=budget.probe)
        monitor_raw = v.canonical_json(monitor)
        io._exclusive(reader_root / 'supervision.json', monitor_raw)
        result.update(reader_supervision_pin=_pin(monitor_raw),
                      child_pid=monitor['worker_pid'],
                      child_start_token=launch.get('start_token'),
                      child_exit_confirmed=monitor['worker_exit_confirmed'],
                      child_status=monitor['status'])
        v.require(monitor['status'] == 'complete' and
                  monitor['exit_code'] == 0 and
                  monitor['worker_exit_confirmed'] is True and
                  monitor['worker_pid'] == launch.get('pid'),
                  'new owned reader child completion')
        stdout = observed._file(reader_root / 'worker/report.json',
                                copied.READER_LIMITS['output_bytes'])
        v.require(_pin(stdout) == monitor['output'],
                  'new owned reader stdout pin')
        reply = v.strict_json(stdout)
        v.require(type(reply) is dict and
                  reply.get('format') == CHILD_FORMAT and
                  reply.get('status') == 'read' and
                  reply.get('invocation_id') == invocation['invocation_id'] and
                  reply.get('process') == {
                      'pid': launch['pid'], 'parent_pid': os.getpid(),
                      'start_token': launch['start_token']} and
                  reply.get('source') == current_source and
                  reply.get('runtime') == current_runtime and
                  reply.get('manifest_pin') == expected_manifest_pin and
                  reply.get('output_pins') == external and
                  reply.get('actual_registered_observations_read') is False and
                  reply.get('formal_permission') is False,
                  'new owned reader child reply binding')
        result['child_stdout_pin'] = monitor['output']
        result['external_saved_payloads_reopened_in_child'] = True
        result['fresh_saved_payload_bytes_rechecked_this_run'] = True
        result['fresh_owned_reader_exit_confirmed_here'] = True
        v.require(reply['reader_result'] == old_outer['reader_result'],
                  'fresh saved reader differs from prior pinned reader')
        result['fresh_reader_equal_prior_reader'] = True
        boundary()
        budget.checkpoint()
        projected = lineage.bind_saved_reader_rows(
            receipt_raw, report_raw, outer_raw,
            chunk_index=manifest['chunk_index'],
            expected_receipt_pin=external['saved/receipt.json'],
            expected_report_pin=external['saved/report.json'],
            expected_outer_result_pin=expected_outer_result_pin)
        rows_raw = v.canonical_json(projected)
        v.require(len(rows_raw) <= MAX_ROWS, 'bounded six-row projection')
        io._exclusive(target / 'rows.json', rows_raw)
        result['row_projection_pin'] = _pin(rows_raw)
        result['row_projection_path'] = str(target / 'rows.json')
        result['row_projection_in_same_budget'] = True
        result['verified_evaluations'] = projected['verified_evaluations']
        result['verified_chunks'] = projected['verified_chunks']
        boundary()
        result['selected_current_source_after'] = _source(expected_revision)
        result['runtime_after'] = runtime.probe_runtime(ROOT)
        v.require(result['selected_current_source_after'] == current_source and
                  result['runtime_after'] == current_runtime,
                  'reread parent final source/runtime changed')
        budget.checkpoint()
        result.update(status='verified', reason=None)
    except supervisor.UnreapedWorker as error:
        result.update(reason='unreaped_reader', child_exit_confirmed=False,
                      child_pid=error.report.get('worker_pid'))
        try:
            supervisor.retain_until_exit(error)
            result['reason'] = 'unreaped_reader_reconciled_failure'
        except BaseException:
            critical = error
        try:
            monitor_raw = v.canonical_json(error.report)
            io._exclusive(reader_root / 'supervision.json', monitor_raw)
            result['reader_supervision_pin'] = _pin(monitor_raw)
        except BaseException as save_error:
            critical = critical or save_error
    except resources.ResourceStop as error:
        result.update(reason=error.reason, error_type=type(error).__name__)
    except (ValueError, OSError, KeyError, TypeError, IndexError,
            subprocess.SubprocessError) as error:
        result.update(reason='reread_or_projection_rejected',
                      error_type=type(error).__name__, detail=str(error))
    except BaseException as error:
        result.update(reason='critical_reread_failure',
                      error_type=type(error).__name__)
        critical = error
    finally:
        if started:
            try:
                budget.checkpoint()
                snapshot = budget_module.directory_snapshot(
                    target, budget.limits['directory_entries'])
                v.require(snapshot['directory_bytes'] + RESERVE_BYTES <=
                          budget.limits['directory_bytes'] and
                          snapshot['directory_entries'] + 2 <=
                          budget.limits['directory_entries'],
                          'reread final receipt reserve exceeded')
            except resources.ResourceStop as error:
                result.update(status='failed', reason=error.reason)
            except (ValueError, OSError, KeyError, TypeError) as error:
                result.update(status='failed', reason='reread_reserve_rejected',
                              reserve_error_type=type(error).__name__)
            try:
                report = budget.close()
                budget_raw = v.canonical_json(report)
                v.require(len(budget_raw) <= MAX_BUDGET,
                          'reread resource receipt byte bound')
                io._exclusive(target / 'resource-budget.json', budget_raw)
                result['resource_budget_pin'] = _pin(budget_raw)
                result['budget_passed'] = (
                    report['passed'] is True and
                    report['monitor_exit_confirmed'] is True and
                    report['stop_reason'] is None and
                    report['formal_permission'] is False)
                if not result['budget_passed']:
                    result.update(status='failed',
                                  reason=report['stop_reason'] or
                                  'reread_budget_not_closed')
            except BaseException as error:
                result.update(status='failed', reason='reread_budget_close_failed',
                              budget_error_type=type(error).__name__)
                critical = critical or error
        else:
            try:
                report = budget.close()
                budget_raw = v.canonical_json(report)
                io._exclusive(target / 'resource-budget.json', budget_raw)
                result['resource_budget_pin'] = _pin(budget_raw)
                result['budget_passed'] = False
            except BaseException as error:
                critical = critical or error
        try:
            result_raw = v.canonical_json(result)
            v.require(len(result_raw) <= MAX_RESULT,
                      'reread result byte bound')
            io._exclusive(target / 'result.json', result_raw)
            result['result_pin'] = _pin(result_raw)
        except BaseException as error:
            critical = critical or error
    if critical is not None:
        raise critical
    return result
