"""Owned materialization of caller-declared invented registered-format bytes.

The child only copies a caller-pinned 22-file fixture to saved-attempt paths.
It does not generate observations or execute a registered evaluation.  This
separate 26H2 experiment never authorizes S4, S5, S6, or a formal campaign.
"""
from __future__ import annotations

import base64
import binascii
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
from . import anomaly_v03_preformal_campaign_child_context as child_context
from . import anomaly_v03_process_supervisor as supervisor
from . import anomaly_v03_reader_evidence as observed
from . import anomaly_v03_registered_saved_attempt_fixture as fixture
from . import anomaly_v03_registered_saved_summary as saved


ROOT = Path(__file__).resolve().parents[2]
FORMAT = 'anomaly-v03-preformal-owned-saved-attempt-materializer-v1'
INVOCATION = 'anomaly-v03-preformal-owned-saved-attempt-invocation-v1'
CHAIN_FORMAT = 'anomaly-v03-preformal-owned-saved-attempt-two-role-v1'
READER_FORMAT = 'anomaly-v03-preformal-owned-saved-attempt-reader-v1'
READER_INVOCATION = 'anomaly-v03-preformal-owned-saved-attempt-reader-invocation-v1'
CAMPAIGN_READER_FORMAT = 'anomaly-v03-preformal-owned-saved-attempt-reader-v2'
CAMPAIGN_READER_INVOCATION = (
    'anomaly-v03-preformal-owned-saved-attempt-reader-invocation-v2')
LIMITS = {'wall_seconds': 180, 'private_bytes': 512 * 1024**2,
          'output_bytes': 1024**2}
# Per-child engineering stop bounds, not a shared end-to-end budget or S4 limit.
READER_LIMITS = {'wall_seconds': 300, 'private_bytes': 1024**3,
                 'output_bytes': 1024**2}
MAX_READER_INVOCATION = 256 * 1024
MAX_SOURCE_SNAPSHOT_BYTES = 64 * 1024
SOURCE_FILES = (
    'src/banto_ai/anomaly_v03_preformal_owned_saved_attempt.py',
    'src/banto_ai/anomaly_v03_role_runtime_observation.py',
    'src/banto_ai/_anomaly_v03_inventory.py',
    'src/banto_ai/_anomaly_v03_reader_dependencies.py',
    'src/banto_ai/anomaly_v03_preformal_campaign_child_context.py',
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
READER_BOOTSTRAP = ('import sys;sys.path.insert(0,sys.argv.pop(1));'
                    'from banto_ai.anomaly_v03_preformal_owned_saved_attempt import reader_worker_main;'
                    'raise SystemExit(reader_worker_main(sys.argv[1:]))')
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


def _source_snapshots(value):
    """Encode caller-held raw source bytes for a bounded JSON child request."""
    v.require(type(value) is dict and len(value) <= 4,
              'bounded caller source snapshots required')
    encoded, total = {}, 0
    for revision, rows in sorted(value.items()):
        evidence._digest(revision, 40)
        v.require(type(rows) is dict and len(rows) <= 32,
                  'bounded source snapshot inventory')
        encoded[revision] = {}
        for name, raw in sorted(rows.items()):
            v.safe_relative_path(name)
            v.require(type(name) is str and len(name) <= 256 and
                      type(raw) is bytes, 'source snapshot path/bytes')
            total += len(raw)
            v.require(total <= MAX_SOURCE_SNAPSHOT_BYTES,
                      'source snapshot total byte bound')
            encoded[revision][name] = base64.b64encode(raw).decode('ascii')
    return encoded


def _decode_source_snapshots(value):
    v.require(type(value) is dict and len(value) <= 4,
              'bounded encoded source snapshots required')
    decoded = {}
    for revision, rows in value.items():
        evidence._digest(revision, 40)
        v.require(type(rows) is dict and len(rows) <= 32,
                  'bounded encoded source snapshot inventory')
        decoded[revision] = {}
        for name, encoded in rows.items():
            v.safe_relative_path(name)
            v.require(type(name) is str and len(name) <= 256 and
                      type(encoded) is str, 'encoded source snapshot path/bytes')
            try:
                raw = base64.b64decode(encoded, validate=True)
            except (ValueError, binascii.Error) as error:
                raise ValueError('invalid source snapshot base64') from error
            decoded[revision][name] = raw
    _same(_source_snapshots(decoded), value, 'canonical source snapshot encoding')
    return decoded


def _saved_outputs(root, chunk_index, external):
    v.require(type(chunk_index) is int and 0 <= chunk_index < 480,
              'invented reader chunk index')
    v.require(type(external) is dict, 'external reader pins required')
    receipt = v.strict_json(_checked_file(
        root, 'saved/receipt.json', external['saved/receipt.json'],
        saved.MAX_RECEIPT))
    v.require(type(receipt) is dict and
              receipt.get('mode') == saved.MODE and
              receipt.get('invented_only') is True and
              receipt.get('chunk_index') == chunk_index,
              'invented reader receipt required')
    attempts = receipt.get('attempts')
    v.require(type(attempts) is list and 1 <= len(attempts) <= 4 and
              type(attempts[-1]) is dict and
              attempts[-1].get('state') == 'complete' and
              type(attempts[-1].get('attempt')) is int and
              attempts[-1]['attempt'] == len(attempts),
              'latest invented attempt is not complete')
    _, physical = fixture._names(chunk_index, attempts[-1]['attempt'])
    outputs = _output_names(physical)
    v.require(set(external) == set(outputs),
              'exact invented reader pin inventory')
    return outputs, attempts[-1]['attempt']


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


def _read_attempt(request, root):
    """The original physical initial read and rederivation, performed once."""
    campaign_mode = 'campaign_context' in request
    snapshots = _decode_source_snapshots(request['source_snapshots'])
    outputs, _ = _saved_outputs(root, request['chunk_index'],
                                request['external_pins'])
    _same(request['output_names'], outputs, 'owned reader output names')
    source_before = _source(request['source_revision'])
    runtime_before = runtime.probe_runtime(ROOT)
    _same(source_before, request['source'], 'owned reader source before')
    _same(runtime_before, request['runtime'], 'owned reader runtime before')
    _check_outputs(root, outputs, request['external_pins'])
    process = observed.creation_observation(os.getpid())
    external = request['external_pins']
    read = fixture.read_invented_registered_attempt(
        root, expected_mode=request['expected_mode'],
        chunk_index=request['chunk_index'],
        expected_registry_pin=external['saved/registry.json'],
        expected_savepoint_pin=external['saved/savepoint.json'],
        expected_receipt_pin=external['saved/receipt.json'],
        expected_report_pin=external['saved/report.json'],
        expected_payload_pins={key: pin for key, pin in external.items()
                               if key not in SAVED},
        source_snapshots=snapshots)
    _check_outputs(root, outputs, external)
    source_after = _source(request['source_revision'])
    runtime_after = runtime.probe_runtime(ROOT)
    _same(source_after, source_before, 'owned reader source after')
    _same(runtime_after, runtime_before, 'owned reader runtime after')
    reply = {'format': (CAMPAIGN_READER_FORMAT if campaign_mode else
                        READER_FORMAT), 'status': 'read',
             'invocation_id': request['invocation_id'],
             'process': {'pid': os.getpid(), 'parent_pid': os.getppid(),
                         'start_token': process['start_token']},
             'output_pins': external,
             'source_before': source_before, 'source_after': source_after,
             'runtime_before': runtime_before, 'runtime_after': runtime_after,
             'reader_result': read, 'formal_permission': False}
    if campaign_mode:
        reply['campaign_context'] = copy.deepcopy(request['campaign_context'])
    return reply


def reader_worker_main(argv):
    """Read the pinned invented saved attempt in a distinct owned process."""
    try:
        v.require(len(argv) == 2, 'reader worker arguments')
        path = paths.regular_path(Path(argv[0]))
        raw = observed._file(path, MAX_READER_INVOCATION)
        v.require(_pin(raw)['sha256'] == argv[1], 'reader invocation pin')
        request = v.strict_json(raw)
        v.require(raw == v.canonical_json(request),
                  'canonical reader invocation required')
        campaign_mode = 'campaign_context' in request
        evidence._keys(request,
            'format root expected_mode chunk_index output_names external_pins '
            'source_snapshots source_revision source runtime invocation_id' +
            (' campaign_context' if campaign_mode else '') +
            (' runtime_inventory_profile_pin' if 'runtime_inventory_profile_pin' in request else ''),
            'reader invocation fields')
        v.require(request['format'] == (
                      CAMPAIGN_READER_INVOCATION if campaign_mode else
                      READER_INVOCATION) and
                  request['expected_mode'] == saved.MODE,
                  'formal/unknown owned reader mode is closed')
        root = _root(request['root'])
        if campaign_mode:
            child_context.verify_context(
                request['campaign_context'], attempt_root=root,
                revision=request['source_revision'])
            v.require(request['campaign_context']['chunk_index'] ==
                      request['chunk_index'],
                      'initial reader campaign chunk context')
        v.require(path == root / 'owned-reader' / 'invocation.json',
                  'owned reader invocation path')
        operation = lambda: _read_attempt(request, root)
        if 'runtime_inventory_profile_pin' in request:
            from . import anomaly_v03_role_runtime_observation as observation
            profile_raw = observed._file(path.parent / 'inventory-profile.json', observation.MAX_PROFILE)
            profile = observation.load_profile(profile_raw, request['runtime_inventory_profile_pin'], root=ROOT, role='initial-reader')
            v.require(profile['source_revision'] == request['source_revision'], 'initial reader runtime profile worker revision differs')
            reply, receipt = observation.run_observed(operation, root=path.parent, source_root=ROOT,
                role='initial-reader', profile_raw=profile_raw, profile_pin=request['runtime_inventory_profile_pin'],
                input_pin=_pin(raw))
            reply['runtime_observation'] = receipt
        else:
            reply = operation()
        print(json.dumps(reply, sort_keys=True))
        return 0
    except (ValueError, OSError, KeyError, TypeError,
            subprocess.SubprocessError) as error:
        print(json.dumps({'format': READER_FORMAT, 'status': 'failed',
                          'error_type': type(error).__name__,
                          'detail': str(error), 'formal_permission': False},
                         sort_keys=True))
        return 2


def materialize_and_read(root, *, expected_mode, chunk_index,
                         expected_registry_pin, expected_savepoint_pin,
                         expected_receipt_pin, expected_report_pin,
                         expected_payload_pins, source_snapshots,
                         expected_revision):
    """Own one fixture copier, then one separate saved-attempt reader.

    ``expected_*`` pins and source snapshots are retained by the caller.  A
    failed attempt leaves both owned role directories and the result intact.
    The read starts only after materializer output pin and owned exit checks.
    """
    v.require(expected_mode == saved.MODE, 'formal materializer mode is closed')
    root = _root(root)
    target = paths.regular_path(root / 'owned-materializer', directory=True,
                                missing=True)
    target.mkdir()
    active_role, active_target = 'materializer', target
    result = {'format': CHAIN_FORMAT, 'status': 'failed',
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
              'owned_fixture_reader_executed': False,
              'owned_fixture_reader_exit_confirmed': False,
              'owned_fixture_reader_exit_reconciled': False,
              'owned_fixture_reader_pid': None,
              'actual_worker_exit_authenticated': False,
              'campaign_completed': False, 'campaign_evaluations_credited': 0,
              'source_closure_complete': False, 'runtime_closure_complete': False,
              'execution_authenticated': False, 'result_trusted': False,
              'formal_permission': False, 'analysis_authorized': False,
              'promotion_allowed': False, 'independent_s6_complete': False}
    try:
        v.require(type(expected_payload_pins) is dict,
                  'external payload pin dictionary required')
        v.require(not set(expected_payload_pins).intersection(SAVED),
                  'saved pin key forbidden in payload pins')
        external = copy.deepcopy({
            **{'saved/registry.json': expected_registry_pin,
               'saved/savepoint.json': expected_savepoint_pin,
               'saved/receipt.json': expected_receipt_pin,
               'saved/report.json': expected_report_pin},
            **expected_payload_pins})
        encoded_snapshots = _source_snapshots(source_snapshots)
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
        selected_outputs, selected_attempt = _saved_outputs(
            root, chunk_index, external)
        _same(selected_outputs, outputs, 'materialized reader output names')
        result.update(owned_fixture_materializer_start_token=
                          launch['start_token'],
                      materializer_stdout_pin=monitor['output'],
                      materializer_output_pins=copy.deepcopy(external),
                      materializer_file_count=len(outputs))
        active_role = 'reader'
        active_target = paths.regular_path(root / 'owned-reader',
                                           directory=True, missing=True)
        active_target.mkdir()
        reader_invocation = {
            'format': READER_INVOCATION, 'root': str(root),
            'expected_mode': expected_mode, 'chunk_index': chunk_index,
            'output_names': outputs, 'external_pins': external,
            'source_snapshots': encoded_snapshots,
            'source_revision': expected_revision, 'source': source,
            'runtime': observed_runtime,
            'invocation_id': secrets.token_hex(32)}
        reader_raw = v.canonical_json(reader_invocation)
        v.require(len(reader_raw) <= MAX_READER_INVOCATION,
                  'reader invocation byte bound')
        reader_path = active_target / 'invocation.json'
        io._exclusive(reader_path, reader_raw)
        reader_pin = _pin(reader_raw)
        result['reader_invocation_pin'] = reader_pin
        reader_launch = {}

        def reader_boundary():
            boundary()
            _check_outputs(root, outputs, external)
            _same(_pin(observed._file(reader_path, MAX_READER_INVOCATION)),
                  reader_pin, 'reader invocation changed')

        def reader_started(process):
            reader_launch.update(observed.creation_observation(
                process.pid, process._handle))

        reader_argv = [sys.executable, '-I', '-S', '-B', '-c',
                       READER_BOOTSTRAP, str(ROOT / 'src'), str(reader_path),
                       reader_pin['sha256']]
        with platform._platform_scope():
            reader_monitor = supervisor.supervise(
                reader_argv, ROOT, active_target / 'worker', READER_LIMITS,
                boundary=reader_boundary, on_started=reader_started)
        io._exclusive(active_target / 'supervision.json',
                      v.canonical_json(reader_monitor))
        result.update(owned_fixture_reader_executed=reader_monitor['worker_started'],
                      owned_fixture_reader_exit_confirmed=
                          reader_monitor['worker_exit_confirmed'],
                      owned_fixture_reader_pid=reader_monitor['worker_pid'],
                      owned_fixture_reader_start_token=
                          reader_launch.get('start_token'),
                      reader_stdout_pin=reader_monitor['output'])
        v.require(reader_monitor['status'] == 'complete' and
                  reader_monitor['exit_code'] == 0 and
                  reader_monitor['worker_exit_confirmed'] is True and
                  reader_launch.get('pid') == reader_monitor['worker_pid'],
                  'owned reader completion required')
        reader_stdout = observed._file(active_target / 'worker' / 'report.json',
                                       READER_LIMITS['output_bytes'])
        _same(_pin(reader_stdout), reader_monitor['output'],
              'owned reader stdout pin')
        reader_reply = v.strict_json(reader_stdout)
        v.require('runtime_observation' not in reader_reply, 'unexpected initial reader runtime observation')
        v.require(reader_reply['format'] == READER_FORMAT and
                  reader_reply['status'] == 'read' and
                  reader_reply['invocation_id'] == reader_invocation['invocation_id'] and
                  reader_reply['process'] == {
                      'pid': reader_launch['pid'], 'parent_pid': os.getpid(),
                      'start_token': reader_launch['start_token']} and
                  reader_reply['formal_permission'] is False,
                  'owned reader process binding')
        for key, expected in (('output_pins', external),
                              ('source_before', source),
                              ('source_after', source),
                              ('runtime_before', observed_runtime),
                              ('runtime_after', observed_runtime)):
            _same(reader_reply[key], expected, 'owned reader child ' + key)
        read = reader_reply['reader_result']
        for key, expected in {
            'format': fixture.FORMAT,
            'status': 'latest_chunk_saved_bytes_bound',
            'mode': saved.MODE,
            'chunk_index': chunk_index,
            'latest_state': 'complete',
            'latest_attempt': selected_attempt,
            'latest_rows_bound': 6,
            'scope': 'invented-registered-format-actual-attempt-layout-only',
            'fixture_physical_layout': 'run-attempt-result-payload',
            'fixture_saved_files_read': True,
            'fixture_files_read': len(outputs),
            'registered_evaluation_contracts_checked': 6,
            'saved_payload_bytes_verified': True,
            'external_report_bytes_verified': True,
            'reported_score_ledger_recomputed': True,
            'reported_score_to_primary_summary_checked': True,
            'reported_score_to_slice_summary_recomputed': True,
            'receipt_pin': external['saved/receipt.json'],
            'report_pin': external['saved/report.json'],
            'payload_pins': {key: value for key, value in external.items()
                             if key not in SAVED},
            'invented_registered_format_observations_read': True,
            'invented_observation_profile_score_recomputed': True,
            'observation_to_profile_recomputed': True,
            'observation_to_score_recomputed': True,
            'observation_to_summary_recomputed': True,
            'source_savepoint_bytes_verified': True,
            'source_snapshots_caller_supplied': True,
            'actual_registered_observations_read': False,
            'registered_observations_read': False,
            'real_saved_chunk_reader_used': False,
            'reader_result_provenance_authenticated': False,
            'registered_input_bytes_verified': False,
            'actual_worker_exit_authenticated': False,
            'campaign_completed': False,
            'campaign_evaluations_credited': 0,
            'execution_authenticated': False,
            'result_trusted': False,
            'source_closure_complete': False,
            'runtime_closure_complete': False,
            'formal_permission': False,
            'analysis_authorized': False,
            'promotion_allowed': False,
            'independent_s6_complete': False,
        }.items():
            _same(read[key], expected, 'owned reader result ' + key)
        reader_boundary()
        _check_outputs(root, outputs, external)
        result.update(status='verified', reason=None,
                      reader_result=read)
    except supervisor.UnreapedWorker as error:
        # Keep the original handle; do not turn a supervisor's unconfirmed
        # exit into a normal completion.  A later recovery is a separate fact.
        report = error.report
        field = 'owned_fixture_' + active_role
        result.update(reason='unreaped_' + active_role + '_failure',
                      failed_stage=active_role)
        result[field + '_executed'] = report.get('worker_started', False)
        result[field + '_pid'] = report.get('worker_pid')
        result[field + '_exit_confirmed'] = False
        result[field + '_exit_reconciled'] = False
        try:
            supervisor.retain_until_exit(error)
        except BaseException:
            # If recovery itself fails, let the caller retain the original
            # UnreapedWorker with its process handle.  Preserve best-effort
            # failure evidence without reading live worker output.
            try:
                io._exclusive(active_target / 'supervision.json',
                              v.canonical_json(report))
                io._exclusive(target / 'result.json', v.canonical_json(result))
            except BaseException:
                pass
            raise error
        io._exclusive(active_target / 'supervision.json',
                      v.canonical_json(report))
        result.update(reason='unreaped_' + active_role + '_reconciled_failure')
        result[field + '_exit_reconciled'] = True
    except (ValueError, OSError, KeyError, TypeError,
            subprocess.SubprocessError) as error:
        result.update(reason='materializer_or_reader_rejected',
                      failed_stage=active_role,
                      error_type=type(error).__name__, detail=str(error))
    io._exclusive(target / 'result.json', v.canonical_json(result))
    return {**result, 'check_directory': str(target),
            'result_pin': _pin(v.canonical_json(result))}
