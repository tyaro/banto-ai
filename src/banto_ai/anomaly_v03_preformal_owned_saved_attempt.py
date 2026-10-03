"""Owned materialization of caller-declared invented registered-format bytes.

The child only copies a caller-pinned 22-file fixture to saved-attempt paths.
It does not generate observations or execute a registered evaluation.  This
separate 26H2 experiment never authorizes S4, S5, S6, or a formal campaign.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys

from . import _anomaly_v03_io as io
from . import _anomaly_v03_runtime as paths
from . import anomaly_v03 as v
from . import anomaly_v03_consumer_evidence as evidence
from . import anomaly_v03_observation_audit as pinned
from . import anomaly_v03_platform_fixture as platform
from . import anomaly_v03_platform_fixture_runtime as runtime
from . import anomaly_v03_process_supervisor as supervisor
from . import anomaly_v03_reader_evidence as observed
from . import anomaly_v03_registered_saved_attempt_fixture as fixture
from . import anomaly_v03_registered_saved_summary as saved


ROOT = Path(__file__).resolve().parents[2]
FORMAT = 'anomaly-v03-preformal-owned-saved-attempt-materializer-v1'
INVOCATION = 'anomaly-v03-preformal-owned-saved-attempt-invocation-v1'
LIMITS = {'wall_seconds': 180, 'private_bytes': 512 * 1024**2,
          'output_bytes': 1024**2}
SOURCE_FILES = (
    'src/banto_ai/anomaly_v03_preformal_owned_saved_attempt.py',
    'src/banto_ai/anomaly_v03_registered_saved_attempt_fixture.py',
    'src/banto_ai/anomaly_v03_registered_evaluation_contract.py',
    'src/banto_ai/anomaly_v03_registered_saved_summary.py',
    'src/banto_ai/anomaly_v03_score_audit.py',
    'src/banto_ai/anomaly_v03_process_supervisor.py',
    'src/banto_ai/anomaly_v03_platform_fixture_runtime.py',
    'src/banto_ai/_anomaly_v03_runtime.py',
    'src/banto_ai/_anomaly_v03_io.py',
    'src/banto_ai/anomaly_v03.py',
)
BOOTSTRAP = ('import sys;sys.path.insert(0,sys.argv.pop(1));'
             'from banto_ai.anomaly_v03_preformal_owned_saved_attempt import worker_main;'
             'raise SystemExit(worker_main(sys.argv[1:]))')
SAVED = ('saved/savepoint.json', 'saved/registry.json',
         'saved/receipt.json', 'saved/report.json')
MAX_BY_NAME = {'saved/savepoint.json': fixture.MAX_SAVEPOINT,
               'saved/registry.json': saved.MAX_REGISTRY,
               'saved/receipt.json': saved.MAX_RECEIPT,
               'saved/report.json': saved.MAX_REPORT}


def _pin(raw):
    return observed._pin(raw)


def _same(actual, expected, label):
    evidence._same(actual, expected, label)


def _root(root):
    root = paths.regular_path(Path(root), directory=True)
    v.require(root.parent == ROOT / 'artifacts' and
              root.name.startswith(fixture.PREFIX),
              'dedicated invented materializer root required')
    return root


def _input_names(names):
    return {**{name: 'inbox/' + name for name in SAVED},
            **{logical: 'inbox/payloads/' + logical for logical in names}}


def _output_names(names):
    return {**{name: name for name in SAVED},
            **{logical: 'run-root/' + physical
               for logical, physical in names.items()}}


def _maximum(name):
    return MAX_BY_NAME.get(name, saved.MAX_PAYLOAD)


def _checked_file(root, relative, pin, maximum):
    v.safe_relative_path(relative)
    evidence._pin(pin)
    v.require(0 < pin['bytes'] <= maximum, 'materializer file byte bound')
    return pinned.read_pinned(root / relative, pin, maximum)


def _inventory(root, expected):
    actual = set(io._tree_paths(root))
    v.require(actual == set(expected), 'exact invented materializer file inventory')


def _source(expected_revision):
    evidence._digest(expected_revision, 40)
    head = subprocess.check_output(
        ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'],
        stderr=subprocess.DEVNULL, timeout=10).decode().strip()
    v.require(head == expected_revision, 'selected materializer revision changed')
    dirty = subprocess.check_output(
        ['git', '-c', 'core.fsmonitor=false', '-C', str(ROOT), 'status',
         '--porcelain', '--untracked-files=normal'],
        stderr=subprocess.DEVNULL, timeout=10)
    v.require(not dirty, 'clean materializer checkout required')
    rows = []
    for name in SOURCE_FILES:
        working = observed._file(ROOT / name, 1024**2)
        committed = subprocess.check_output(
            ['git', '-C', str(ROOT), 'show', expected_revision + ':' + name],
            stderr=subprocess.DEVNULL, timeout=10)
        v.require(working == committed, 'selected materializer source changed: ' + name)
        rows.append({'path': name, 'pin': _pin(working)})
    return {'revision': expected_revision, 'selected_files': rows,
            'scope': 'selected-working-git-raw-only-not-source-closure'}


def _preflight(root, chunk_index, expected_pins):
    v.require(type(chunk_index) is int and 0 <= chunk_index < 480,
              'invented materializer chunk index')
    v.require(type(expected_pins) is dict, 'external materializer pins required')
    inbox = paths.regular_path(root / 'inbox', directory=True)
    receipt_pin = expected_pins.get('saved/receipt.json')
    evidence._pin(receipt_pin)
    receipt_raw = _checked_file(root, 'inbox/saved/receipt.json',
                                receipt_pin, saved.MAX_RECEIPT)
    receipt = v.strict_json(receipt_raw)
    v.require(receipt_raw == v.canonical_json(receipt) and
              receipt.get('mode') == saved.MODE and
              receipt.get('invented_only') is True and
              receipt.get('chunk_index') == chunk_index,
              'invented materializer receipt required')
    attempts = receipt.get('attempts')
    v.require(type(attempts) is list and 1 <= len(attempts) <= 4,
              'bounded invented attempt history required')
    latest = attempts[-1]
    v.require(type(latest) is dict and latest.get('state') == 'complete',
              'latest invented attempt is not complete')
    attempt = latest.get('attempt')
    v.require(type(attempt) is int and attempt == len(attempts),
              'latest invented attempt number')
    _, physical = fixture._names(chunk_index, attempt)
    inputs, outputs = _input_names(physical), _output_names(physical)
    v.require(set(expected_pins) == set(inputs),
              'exact external materializer pin inventory')
    _inventory(inbox, [relative.removeprefix('inbox/')
                       for relative in inputs.values()])
    total = 0
    for logical, relative in sorted(inputs.items()):
        raw = _checked_file(root, relative, expected_pins[logical],
                            _maximum(logical))
        total += len(raw)
        v.require(total <= saved.MAX_TOTAL, 'materializer total input byte bound')
    for name in ('saved', 'run-root'):
        paths.regular_path(root / name, directory=True, missing=True)
        v.require(not (root / name).exists(),
                  'materializer output must be new')
    savepoint = v.strict_json(_checked_file(
        root, inputs['saved/savepoint.json'],
        expected_pins['saved/savepoint.json'], fixture.MAX_SAVEPOINT))
    v.require(savepoint.get('format') == fixture.SAVEPOINT_FORMAT and
              savepoint.get('mode') == saved.MODE and
              savepoint.get('invented_only') is True and
              savepoint.get('campaign_completed') is False and
              savepoint.get('actual_registered_observations_read') is False and
              savepoint.get('run_root') == str(root / 'run-root') and
              savepoint.get('chunk_index') == chunk_index,
              'invented materializer savepoint required')
    v.require(expected_pins['saved/registry.json']['sha256'] ==
              v.REGISTRY_RAW_SHA256, 'frozen registry external pin required')
    return inputs, outputs


def _read_inputs(root, inputs, pins):
    return {logical: _checked_file(root, relative, pins[logical],
                                   _maximum(logical))
            for logical, relative in sorted(inputs.items())}


def _check_outputs(root, outputs, pins):
    _inventory(root / 'saved',
               [relative.removeprefix('saved/') for relative in SAVED])
    _inventory(root / 'run-root',
               [relative.removeprefix('run-root/') for logical, relative
                in outputs.items() if logical not in SAVED])
    for logical, relative in sorted(outputs.items()):
        _checked_file(root, relative, pins[logical], _maximum(logical))


def worker_main(argv):
    """Child copies exact pinned bytes; no observation generation occurs."""
    try:
        v.require(len(argv) == 2, 'materializer worker arguments')
        path = paths.regular_path(Path(argv[0]))
        raw = observed._file(path, 64 * 1024)
        v.require(_pin(raw)['sha256'] == argv[1], 'materializer invocation pin')
        request = v.strict_json(raw)
        evidence._keys(request,
            'format root chunk_index input_names output_names external_pins '
            'source_revision source runtime invocation_id',
            'materializer invocation fields')
        v.require(request['format'] == INVOCATION, 'materializer invocation format')
        root = _root(request['root'])
        v.require(path == root / 'owned-materializer' / 'invocation.json',
                  'materializer invocation path')
        inputs, outputs = _preflight(root, request['chunk_index'],
                                     request['external_pins'])
        _same(request['input_names'], inputs, 'materializer input names')
        _same(request['output_names'], outputs, 'materializer output names')
        source_before = _source(request['source_revision'])
        runtime_before = runtime.probe_runtime(ROOT)
        _same(source_before, request['source'], 'materializer source before')
        _same(runtime_before, request['runtime'], 'materializer runtime before')
        process = observed.creation_observation(os.getpid())
        data = _read_inputs(root, inputs, request['external_pins'])
        _inventory(root / 'inbox',
                   [relative.removeprefix('inbox/') for relative in inputs.values()])
        for name in ('saved', 'run-root'):
            (root / name).mkdir()
        for logical, relative in sorted(outputs.items()):
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            io._exclusive(target, data[logical])
        _check_outputs(root, outputs, request['external_pins'])
        source_after = _source(request['source_revision'])
        runtime_after = runtime.probe_runtime(ROOT)
        _same(source_after, source_before, 'materializer source after')
        _same(runtime_after, runtime_before, 'materializer runtime after')
        _read_inputs(root, inputs, request['external_pins'])
        reply = {'format': FORMAT, 'status': 'materialized',
                 'invocation_id': request['invocation_id'],
                 'process': {'pid': os.getpid(), 'parent_pid': os.getppid(),
                             'start_token': process['start_token']},
                 'input_pins': request['external_pins'],
                 'output_pins': request['external_pins'],
                 'source_before': source_before, 'source_after': source_after,
                 'runtime_before': runtime_before, 'runtime_after': runtime_after,
                 'input_origin': 'caller_declared_invented',
                 'generation_verified': False,
                 'actual_registered_producer_executed': False,
                 'actual_registered_observations_read': False,
                 'formal_permission': False}
        print(json.dumps(reply, sort_keys=True))
        return 0
    except (ValueError, OSError, KeyError, TypeError,
            subprocess.SubprocessError) as error:
        print(json.dumps({'format': FORMAT, 'status': 'failed',
                          'error_type': type(error).__name__,
                          'detail': str(error), 'formal_permission': False},
                         sort_keys=True))
        return 2


def materialize_and_read(root, *, expected_mode, chunk_index,
                         expected_registry_pin, expected_savepoint_pin,
                         expected_receipt_pin, expected_report_pin,
                         expected_payload_pins, source_snapshots,
                         expected_revision):
    """Own one fixture copier, then apply the existing saved-attempt reader.

    ``expected_*`` pins and source snapshots are retained by the caller.  A
    failed attempt leaves the materializer directory and result receipt intact.
    The independent read runs only after output pin and owned exit checks.
    """
    v.require(expected_mode == saved.MODE, 'formal materializer mode is closed')
    root = _root(root)
    target = paths.regular_path(root / 'owned-materializer', directory=True,
                                missing=True)
    target.mkdir()
    external = {**{'saved/registry.json': expected_registry_pin,
                   'saved/savepoint.json': expected_savepoint_pin,
                   'saved/receipt.json': expected_receipt_pin,
                   'saved/report.json': expected_report_pin},
                **expected_payload_pins}
    result = {'format': FORMAT, 'status': 'failed',
              'reason': 'materializer_not_completed',
              'input_origin': 'caller_declared_invented',
              'generation_verified': False,
              'actual_registered_producer_executed': False,
              'actual_registered_observations_read': False,
              'registered_observations_read': False,
              'owned_fixture_materializer_executed': False,
              'owned_fixture_materializer_exit_confirmed': False,
              'owned_fixture_materializer_exit_reconciled': False,
              'owned_fixture_materializer_pid': None,
              'actual_worker_exit_authenticated': False,
              'campaign_completed': False, 'campaign_evaluations_credited': 0,
              'source_closure_complete': False, 'runtime_closure_complete': False,
              'execution_authenticated': False, 'result_trusted': False,
              'formal_permission': False, 'analysis_authorized': False,
              'promotion_allowed': False, 'independent_s6_complete': False}
    try:
        v.require(type(source_snapshots) is dict,
                  'caller source snapshots required')
        inputs, outputs = _preflight(root, chunk_index, external)
        source = _source(expected_revision)
        observed_runtime = runtime.probe_runtime(ROOT)
        invocation = {'format': INVOCATION, 'root': str(root),
                      'chunk_index': chunk_index, 'input_names': inputs,
                      'output_names': outputs, 'external_pins': external,
                      'source_revision': expected_revision, 'source': source,
                      'runtime': observed_runtime,
                      'invocation_id': secrets.token_hex(32)}
        invocation_raw = v.canonical_json(invocation)
        io._exclusive(target / 'invocation.json', invocation_raw)
        invocation_pin = _pin(invocation_raw)
        launch = {}

        def boundary():
            _same(_source(expected_revision), source,
                  'parent materializer source changed')
            _same(runtime.probe_runtime(ROOT), observed_runtime,
                  'parent materializer runtime changed')
            _same(_pin(observed._file(target / 'invocation.json', 64 * 1024)),
                  invocation_pin, 'materializer invocation changed')
            _read_inputs(root, inputs, external)
            _inventory(root / 'inbox',
                       [relative.removeprefix('inbox/')
                        for relative in inputs.values()])

        def started(process):
            launch.update(observed.creation_observation(process.pid,
                                                        process._handle))

        argv = [sys.executable, '-I', '-S', '-B', '-c', BOOTSTRAP, str(ROOT / 'src'),
                str(target / 'invocation.json'), invocation_pin['sha256']]
        with platform._platform_scope():
            monitor = supervisor.supervise(argv, ROOT, target / 'worker',
                                           LIMITS, boundary=boundary,
                                           on_started=started)
        io._exclusive(target / 'supervision.json', v.canonical_json(monitor))
        result.update(owned_fixture_materializer_executed=monitor['worker_started'],
                      owned_fixture_materializer_exit_confirmed=
                          monitor['worker_exit_confirmed'],
                      owned_fixture_materializer_pid=monitor['worker_pid'])
        v.require(monitor['status'] == 'complete' and
                  monitor['exit_code'] == 0 and
                  monitor['worker_exit_confirmed'] is True and
                  launch.get('pid') == monitor['worker_pid'],
                  'owned materializer completion required')
        stdout = observed._file(target / 'worker' / 'report.json',
                                LIMITS['output_bytes'])
        _same(_pin(stdout), monitor['output'], 'materializer stdout pin')
        reply = v.strict_json(stdout)
        v.require(reply['format'] == FORMAT and
                  reply['status'] == 'materialized' and
                  reply['invocation_id'] == invocation['invocation_id'] and
                  reply['process'] == {
                      'pid': launch['pid'], 'parent_pid': os.getpid(),
                      'start_token': launch['start_token']},
                  'owned materializer process binding')
        for key, expected in (('input_pins', external),
                              ('output_pins', external),
                              ('source_before', source),
                              ('source_after', source),
                              ('runtime_before', observed_runtime),
                              ('runtime_after', observed_runtime)):
            _same(reply[key], expected, 'materializer child ' + key)
        v.require(reply['input_origin'] == 'caller_declared_invented' and
                  reply['generation_verified'] is False and
                  reply['actual_registered_producer_executed'] is False and
                  reply['actual_registered_observations_read'] is False and
                  reply['formal_permission'] is False,
                  'materializer child fixture scope')
        _check_outputs(root, outputs, external)
        boundary()
        read = fixture.read_invented_registered_attempt(
            root, expected_mode=expected_mode, chunk_index=chunk_index,
            expected_registry_pin=expected_registry_pin,
            expected_savepoint_pin=expected_savepoint_pin,
            expected_receipt_pin=expected_receipt_pin,
            expected_report_pin=expected_report_pin,
            expected_payload_pins=expected_payload_pins,
            source_snapshots=source_snapshots)
        _check_outputs(root, outputs, external)
        result.update(status='verified', reason=None,
                      owned_fixture_materializer_start_token=launch['start_token'],
                      materializer_stdout_pin=monitor['output'],
                      materializer_output_pins=copy.deepcopy(external),
                      materializer_file_count=len(outputs),
                      reader_result=read)
    except supervisor.UnreapedWorker as error:
        # Keep the original handle; do not turn a supervisor's unconfirmed
        # exit into a normal completion.  A later recovery is a separate fact.
        report = error.report
        result.update(reason='unreaped_materializer_failure',
                      owned_fixture_materializer_executed=
                          report.get('worker_started', False),
                      owned_fixture_materializer_pid=report.get('worker_pid'),
                      owned_fixture_materializer_exit_confirmed=False,
                      owned_fixture_materializer_exit_reconciled=False)
        try:
            supervisor.retain_until_exit(error)
        except BaseException:
            # If recovery itself fails, let the caller retain the original
            # UnreapedWorker with its process handle.  Preserve best-effort
            # failure evidence without reading live worker output.
            try:
                io._exclusive(target / 'supervision.json', v.canonical_json(report))
                io._exclusive(target / 'result.json', v.canonical_json(result))
            except BaseException:
                pass
            raise error
        io._exclusive(target / 'supervision.json', v.canonical_json(report))
        result.update(reason='unreaped_materializer_reconciled_failure',
                      owned_fixture_materializer_exit_reconciled=True)
    except (ValueError, OSError, KeyError, TypeError,
            subprocess.SubprocessError) as error:
        result.update(reason='materializer_or_reader_rejected',
                      error_type=type(error).__name__, detail=str(error))
    io._exclusive(target / 'result.json', v.canonical_json(result))
    return {**result, 'check_directory': str(target),
            'result_pin': _pin(v.canonical_json(result))}
