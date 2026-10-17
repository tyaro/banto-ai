"""Publish one pinned invented slice draft with an owned writer and reader.

The source document, count audit, and separate-process postcheck are retained
inputs. This step copies their validated values into a local publication. It
uses the existing platform-fixture runtime scope in one serialized dedicated
caller process; concurrent calls are unsupported. It does not replay draws,
perform S6, authenticate all source/runtime dependencies, or enter the
registered campaign. The historical source bytes remain unchanged.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys

from . import _anomaly_v03_fixture_budget as budgets
from . import _anomaly_v03_io as io
from . import anomaly_v03_preformal_bound_slice_bridge as previous
from . import anomaly_v03_process_supervisor as supervisor
from . import anomaly_v03_reader_evidence as observed
from . import anomaly_v03_platform_fixture as platform
from . import anomaly_v03_platform_fixture_runtime as platform_runtime


ROOT = Path(__file__).resolve().parents[2]
slice_bridge = previous
OUTPUT_PARENT = ROOT / 'artifacts/anomaly-v03-preformal-bound-slice-publication'
POSTCHECK_ROOT = ROOT / 'artifacts/anomaly-v03-preformal-bound-slice-postcheck-01'
FORMAT = 'anomaly-v03-preformal-bound-slice-publication-v1'
REQUEST_FORMAT = FORMAT + '-request'
PAYLOAD_NAMES = ('audit.json', 'postcheck-result.json', 'slices.json')
MAX_SOURCE_BYTES = {'audit.json': 64 * 1024,
                    'postcheck-result.json': 64 * 1024,
                    'slices.json': previous.MAX_SLICES_BYTES}
LIMITS = {'wall_seconds': 60, 'private_bytes': 512 * 1024**2,
          'output_bytes': 64 * 1024}
SOURCE_NAMES = (
    'src/banto_ai/anomaly_v03_preformal_bound_slice_publication.py',
    'tools/preformal_bound_slice_publication_trial.py',
    'src/banto_ai/anomaly_v03_preformal_bound_slice_bridge.py',
    'src/banto_ai/anomaly_v03_preformal_bound_document_bridge.py',
    'src/banto_ai/anomaly_v03_fixture_slice_audit.py',
    'src/banto_ai/anomaly_v03_slice_fixture.py',
    'src/banto_ai/anomaly_v03_process_supervisor.py',
    'src/banto_ai/anomaly_v03_reader_evidence.py',
    'src/banto_ai/anomaly_v03_platform_fixture.py',
    'src/banto_ai/anomaly_v03_platform_fixture_runtime.py',
    'src/banto_ai/_anomaly_v03_io.py',
    'src/banto_ai/_anomaly_v03_fixture_budget.py',
    'src/banto_ai/_anomaly_v03_contract.py',
)
CLOSED = {**previous.CLOSED, 'new_evaluations': 0,
          'primary_ci_gate_recomputed_here': False,
          'independent_s6_complete': False,
          'full_end_to_end_budget_measured': False,
          'source_closure_complete': False,
          'runtime_closure_complete': False}


def _pin(raw):
    return previous.previous.bounded._pin(raw)


def _read(path, pin, maximum):
    return previous.previous.bounded._read(path, pin, maximum)


def _fields(value, expected, label):
    previous.previous._same_fields(value, expected, label)


def _source_pins(revision):
    previous.previous.bridge.projection.evidence._digest(revision, 40)

    def git(*args):
        return subprocess.check_output(['git', '-C', str(ROOT), *args],
                                       stderr=subprocess.DEVNULL, timeout=10)

    if (git('rev-parse', 'HEAD').decode().strip() != revision or
            git('status', '--porcelain').strip()):
        raise ValueError('publication requires clean expected HEAD')
    pins = {}
    for name in SOURCE_NAMES:
        raw = previous.previous.bounded._bounded_file(ROOT / name, 1024**2)
        if raw != git('show', revision + ':' + name):
            raise ValueError('publication selected source differs from Git: ' + name)
        pins[name] = _pin(raw)
    return pins


def _raw_source_pins():
    return {name: _pin(previous.previous.bounded._bounded_file(ROOT / name, 1024**2))
            for name in SOURCE_NAMES}


def _inventory(root, names):
    io.regular_path(root, directory=True)
    if {path.name for path in root.iterdir()} != set(names):
        raise ValueError('retained input inventory differs')


def _json(path, pin, maximum):
    raw = _read(path, pin, maximum)
    value = previous.previous.bridge.projection.v.strict_json(raw)
    if previous.previous.bounded._raw(value) != raw:
        raise ValueError('retained canonical JSON differs')
    return raw, value


def _closed(value, label):
    _fields(value, previous.CLOSED, label)
    if type(value.get('campaign_evaluations_credited')) is not int or value['campaign_evaluations_credited'] != 0:
        raise ValueError(label + ' campaign credit differs')


def _validate_values(top, document, audit, postcheck, *, slice_result_pin,
                     source_pins):
    _fields(top, {**previous.CLOSED, 'format': previous.FORMAT,
                  'scope': 'retained-invented-50000-primary-to-fixture-slices-only',
                  'status': 'verified', 'independent_count_audit_matched': True,
                  'independent_count_audit_process_executed': False,
                  'numeric_draws': 50000, 'legacy_projection_draws': 1,
                  'main_slice_rows': 1233, 'diagnostic_rows': 2835,
                  'diagnostic_tables': 9}, 'retained slice result')
    if top['source_pins_before'] != top['source_pins_after'] or top['runtime_before'] != top['runtime_after']:
        raise ValueError('retained slice source/runtime differs')
    _fields(document, {**previous.CLOSED, 'format': previous.SLICE_FORMAT,
                       'scope': 'retained-invented-50000-primary-to-fixture-slices-only',
                       'status': 'fixture_slices_connected', 'invented_only': True,
                       'document_result_pin': top['document_result_pin'],
                       'primary_document_pin': top['primary_document_pin'],
                       'slice_source_pin': top['slice_source_pin'],
                       'independent_count_audit_process_executed': False},
            'retained slice document')
    if (document['formal_requirements'] != previous.slices._requirements() or
            set(document['document_draft']) != set(previous.slices.document.FIELDS) or
            any(document['document_draft'][field] is not None for field in previous.slices.PENDING) or
            len(document['document_draft']['candidate_tables']) != 9 or
            len(document['document_draft']['slices']) != 1233 or
            sum(len(rows) for rows in document['diagnostic_series'].values()) != 2835 or
            len(document['diagnostic_details']) != 9 or
            document['numeric_draw_contract']['replicates'] != 50000 or
            document['legacy_projection_draws'] != 1 or
            document['fixture_packet']['fixture_candidate_tables'] != document['document_draft']['candidate_tables']):
        raise ValueError('retained slice document meaning differs')
    _fields(audit, {'format': 'anomaly-v03-precomputed-fixture-slice-audit-v1',
                    'status': 'precomputed_fixture_slices_matched',
                    'clusters': 40, 'main_slice_rows': 1233,
                    'diagnostic_rows': 2835, 'diagnostic_tables': 9,
                    'fixture_only': True, 'precomputed_primary_packet_used': True,
                    'fixture_slice_audit_performed': True,
                    'primary_ci_gate_recomputed': False,
                    'formal_permission': False, 'promotion_allowed': False,
                    'registered_data_read': False, 'independent_s6_complete': False,
                    'primary_packet_canonical_sha256': document['primary_packet_canonical_sha256'],
                    'slice_source_canonical_sha256': document['slice_source_canonical_sha256']},
            'retained count audit')
    _fields(postcheck, {
        'status': 'independent_saved_slice_postcheck_passed',
        'scope': 'read-only retained invented 50000 primary to fixture slices',
        'trial_result_pin': slice_result_pin,
        'slices_pin': source_pins['slices.json'],
        'saved_audit_pin': source_pins['audit.json'],
        'prior_document_result_pin': top['document_result_pin'],
        'prior_document_pin': top['primary_document_pin'],
        'producer_slice_source_pin': top['slice_source_pin'],
        'primary_packet_canonical_sha256': document['primary_packet_canonical_sha256'],
        'slice_source_canonical_sha256': document['slice_source_canonical_sha256'],
        'numeric_draws_from_prior_saved_arithmetic': 50000,
        'legacy_projection_draws': 1,
        'candidate_tables_unchanged': 9,
        'main_slice_rows_rechecked': 1233,
        'diagnostic_rows_rechecked': 2835,
        'diagnostic_tables_rechecked': 9,
        'saved_count_audit_replayed_in_separate_process': True,
        'same_count_audit_implementation_reused': True,
        'primary_ci_gate_independently_recomputed_here': False,
        'formal_document_validated': False,
        'formal_permission': False,
        'independent_s6_complete': False,
        'full_end_to_end_budget_measured': False,
        'campaign_evaluations_credited': 0,
    }, 'retained postcheck')
    previous.previous.bridge.projection.evidence._pin(postcheck['script_pin'])


def _published_files(raw_files):
    files = {}
    for name in PAYLOAD_NAMES:
        raw = raw_files[name]
        value = previous.previous.bridge.projection.v.strict_json(raw)
        if previous.previous.bounded._raw(value) != raw:
            raise ValueError('source payload is not canonical JSON: ' + name)
        published = io.json_bytes(value)
        if published != raw + b'\n':
            raise ValueError('published framing differs: ' + name)
        files[name] = published
    return files


def _retained(slice_root, expected_slice_result_pin, postcheck_root,
              expected_postcheck_pin):
    """Authenticate both caller-pinned roots before claiming a new trial."""
    previous.previous.bridge.projection.evidence._pin(expected_slice_result_pin)
    previous.previous.bridge.projection.evidence._pin(expected_postcheck_pin)
    source = previous.previous._path(slice_root, previous.OUTPUT_PARENT)
    check = Path(postcheck_root).absolute()
    if check != POSTCHECK_ROOT or check != POSTCHECK_ROOT.absolute():
        raise ValueError('fixed postcheck receipt root required')
    _inventory(source, ('result.json', 'slices.json', 'audit.json'))
    _inventory(check, ('postcheck-result.json', 'postcheck.py'))
    _, top = _json(source / 'result.json', expected_slice_result_pin, 64 * 1024)
    raw_files = {}
    for name, pin in (('slices.json', top['slices_pin']),
                      ('audit.json', top['audit_pin']),
                      ('postcheck-result.json', expected_postcheck_pin)):
        path = (check if name == 'postcheck-result.json' else source) / name
        raw_files[name], _ = _json(path, pin, MAX_SOURCE_BYTES[name])
    document = previous.previous.bridge.projection.v.strict_json(raw_files['slices.json'])
    audit = previous.previous.bridge.projection.v.strict_json(raw_files['audit.json'])
    postcheck = previous.previous.bridge.projection.v.strict_json(raw_files['postcheck-result.json'])
    source_pins = {name: _pin(raw) for name, raw in raw_files.items()}
    _validate_values(top, document, audit, postcheck,
                     slice_result_pin=expected_slice_result_pin,
                     source_pins=source_pins)
    _read(check / 'postcheck.py', postcheck['script_pin'], 64 * 1024)
    files = _published_files(raw_files)
    return {'source_root': str(source), 'postcheck_root': str(check),
            'slice_result_pin': copy.deepcopy(expected_slice_result_pin),
            'postcheck_pin': copy.deepcopy(expected_postcheck_pin),
            'source_payload_pins': source_pins,
            'payload_pins': {name: _pin(raw) for name, raw in files.items()},
            'files': files}


def _semantic(files, retained):
    if set(files) != set(PAYLOAD_NAMES):
        raise ValueError('published payload inventory differs')
    for name in PAYLOAD_NAMES:
        raw = files[name]
        if (type(raw) is not bytes or _pin(raw) != retained['payload_pins'][name] or
                raw != retained['files'][name] or
                _pin(raw[:-1]) != retained['source_payload_pins'][name]):
            raise ValueError('published payload bytes differ: ' + name)
    return {'source_payload_pins': retained['source_payload_pins'],
            'payload_pins': retained['payload_pins'],
            'payload_files': len(PAYLOAD_NAMES),
            'payload_bytes': sum(len(files[name]) for name in PAYLOAD_NAMES)}


def worker_main(argv):
    try:
        if len(argv) != 3:
            raise ValueError('worker bootstrap argument count')
        path, size, digest = argv
        request_path = Path(path).absolute()
        if (request_path != Path(os.path.abspath(request_path)) or
                request_path.name != 'request.json'):
            raise ValueError('worker request path differs')
        request_pin = {'bytes': int(size), 'sha256': digest}
        request = previous.previous.bridge.projection.v.strict_json(
            _read(request_path, request_pin, 16 * 1024))
        if (request['format'] != REQUEST_FORMAT or request['role'] not in ('writer', 'reader') or
                set(request['payload_pins']) != set(PAYLOAD_NAMES)):
            raise ValueError('worker request differs')
        publication = Path(request['publication_root']).absolute()
        if (publication != Path(os.path.abspath(publication)) or
                request_path.parent.name != request['role'] or
                publication != request_path.parent.parent / 'published'):
            raise ValueError('worker publication ownership differs')
        retained = _retained(request['slice_root'], request['slice_result_pin'],
                             request['postcheck_root'], request['postcheck_pin'])
        if (retained['payload_pins'] != request['payload_pins'] or
                retained['source_payload_pins'] != request['source_payload_pins']):
            raise ValueError('worker retained source differs')
        if _raw_source_pins() != request['source_pins']:
            raise ValueError('worker selected source differs')
        if request['role'] == 'writer':
            def precommit_recheck():
                if (_raw_source_pins() != request['source_pins'] or
                        _retained(request['slice_root'], request['slice_result_pin'],
                                  request['postcheck_root'], request['postcheck_pin']) != retained):
                    raise ValueError('writer precommit source/input changed')
            result = io.publish_local_result(publication.parent, publication.name,
                retained['files'],
                verify_semantics=lambda saved: _semantic(dict(saved), retained),
                precommit_recheck=precommit_recheck)
            result.update(status='writer_completed')
        else:
            checked = io.verify_local_publication(publication,
                expected_marker_sha256=request['expected_marker_sha256'],
                verify_semantics=lambda saved: _semantic(dict(saved), retained))
            result = {**checked, 'status': 'reader_verified',
                      'marker_raw_sha256': request['expected_marker_sha256']}
        result.update(CLOSED, format=FORMAT, role=request['role'], mode='fixture',
                      request_pin=request_pin, source_payload_pins=retained['source_payload_pins'],
                      payload_pins=retained['payload_pins'],
                      slice_result_pin=retained['slice_result_pin'],
                      postcheck_pin=retained['postcheck_pin'],
                      selected_source_pins=request['source_pins'],
                      process={**observed.creation_observation(os.getpid()),
                               'parent_pid': os.getppid()})
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({'status': 'rejected', 'error_type': type(error).__name__,
                          'formal_permission': False}, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


def _role(request, target, budget, source_pins):
    target.mkdir()
    raw = io.json_bytes(request)
    pin = _pin(raw)
    io._exclusive(target / 'request.json', raw)
    launch = {}
    def boundary():
        budget.checkpoint()
        if _read(target / 'request.json', pin, 16 * 1024) != raw or _source_pins(
                request['source_revision']) != source_pins:
            raise ValueError('publication request/source changed')
    def started(process):
        launch.update(observed.creation_observation(process.pid, process._handle))
        io._exclusive(target / 'launch.json', io.json_bytes(launch))
    bootstrap = ('import sys;sys.path.insert(0,sys.argv.pop(1));'
                 'from banto_ai.anomaly_v03_preformal_bound_slice_publication import worker_main;'
                 'raise SystemExit(worker_main(sys.argv[1:]))')
    argv = [sys.executable, '-I', '-S', '-B', '-c', bootstrap, str(ROOT / 'src'),
            str(target / 'request.json'), str(pin['bytes']), pin['sha256']]
    try:
        with platform._platform_scope():
            monitor = supervisor.supervise(argv, ROOT, target / 'worker', LIMITS,
                                           boundary=boundary, on_started=started,
                                           resource_probe=budget.probe)
    except supervisor.UnreapedWorker as error:
        io._exclusive(target / 'supervision.json', io.json_bytes(error.report))
        raise
    monitor_raw = io.json_bytes(monitor)
    io._exclusive(target / 'supervision.json', monitor_raw)
    if (monitor['status'] != 'complete' or monitor['worker_exit_confirmed'] is not True or
            monitor['exit_code'] != 0 or monitor['observation_errors'] or
            monitor['worker_pid'] != launch.get('pid') or
            type(monitor['output']) is not dict or
            type(monitor['output'].get('bytes')) is not int or
            monitor['output']['bytes'] <= 0):
        raise ValueError('owned ' + request['role'] + ' did not complete')
    report_raw = _read(target / 'worker/report.json', monitor['output'], LIMITS['output_bytes'])
    reply = previous.previous.bridge.projection.v.strict_json(report_raw)
    _fields(reply, {**CLOSED, 'format': FORMAT, 'mode': 'fixture',
                    'role': request['role'],
                    'status': 'writer_completed' if request['role'] == 'writer' else 'reader_verified',
                    'request_pin': pin,
                    'source_payload_pins': request['source_payload_pins'],
                    'payload_pins': request['payload_pins'],
                    'slice_result_pin': request['slice_result_pin'],
                    'postcheck_pin': request['postcheck_pin'],
                    'selected_source_pins': request['source_pins']},
            'owned worker reply')
    if (reply['process'] != {**launch, 'parent_pid': os.getpid()} or
            reply['process']['pid'] == os.getpid()):
        raise ValueError('owned worker process differs')
    previous.previous.bridge.projection.evidence._digest(reply['marker_raw_sha256'])
    if request['role'] == 'reader' and (reply.get('local_verified') is not True or
                                       reply.get('payloads') != len(PAYLOAD_NAMES) or
                                       reply['marker_raw_sha256'] != request['expected_marker_sha256']):
        raise ValueError('owned reader publication differs')
    result = {**reply, 'worker_exit_confirmed': True,
              'supervision_pin': _pin(monitor_raw),
              'worker_reply_pin': _pin(report_raw),
              'launch_pin': _pin(io.json_bytes(launch))}
    io._exclusive(target / 'result.json', io.json_bytes(result))
    return result


def run_saved_publication(*, slice_root, expected_slice_result_pin,
                          postcheck_root, expected_postcheck_pin,
                          expected_revision, trial_name):
    """One new local publication. A failed/partial root is never reused."""
    previous.previous.bridge.projection.evidence._pin(expected_slice_result_pin)
    previous.previous.bridge.projection.evidence._pin(expected_postcheck_pin)
    previous.previous.bridge.projection.evidence._digest(expected_revision, 40)
    previous.previous.bridge.projection.v.safe_relative_path(trial_name)
    if '/' in trial_name or '\\' in trial_name or not trial_name.startswith('trial-'):
        raise ValueError('new publication trial name required')
    retained = _retained(slice_root, expected_slice_result_pin,
                         postcheck_root, expected_postcheck_pin)
    source_pins = _source_pins(expected_revision)
    runtime_before = platform_runtime.probe_runtime(ROOT)
    OUTPUT_PARENT.mkdir(exist_ok=True)
    io.regular_path(OUTPUT_PARENT, directory=True)
    target = io.regular_path(OUTPUT_PARENT / trial_name, directory=True, missing=True)
    target.mkdir()
    publication = target / 'published'
    budget = budgets.FixtureBudget(target, publication_roots=[publication])
    result = {**CLOSED, 'format': FORMAT,
              'scope': 'saved-invented-slice-and-postcheck-local-publication-only',
              'status': 'failed', 'mode': 'fixture',
              'slice_result_pin': copy.deepcopy(expected_slice_result_pin),
              'postcheck_pin': copy.deepcopy(expected_postcheck_pin),
              'source_payload_pins': retained['source_payload_pins'],
              'payload_pins': retained['payload_pins'],
              'publication_status': 'not_started', 'reader_status': 'not_started',
              'writer_reaped_before_reader_start': False,
              'local_publication_performed': False,
              'postcheck_receipt_consumed': True,
              'postcheck_is_same_count_implementation': True,
              'runtime_scope': 'serialized-dedicated-caller-platform-fixture-v2',
              'concurrent_calls_supported': False,
              'source_revision': expected_revision,
              'source_pins_before': source_pins,
              'candidate_runtime_policy_id': platform_runtime.POLICY_ID,
              'runtime_before': runtime_before}
    request = {'format': REQUEST_FORMAT, 'role': 'writer',
               'source_revision': expected_revision,
               'source_pins': source_pins,
               'slice_root': retained['source_root'],
               'slice_result_pin': copy.deepcopy(expected_slice_result_pin),
               'postcheck_root': retained['postcheck_root'],
               'postcheck_pin': copy.deepcopy(expected_postcheck_pin),
               'source_payload_pins': retained['source_payload_pins'],
               'payload_pins': retained['payload_pins'],
               'publication_root': str(publication)}
    try:
        budget.start()
        result['publication_status'] = 'unconfirmed'
        writer = _role(request, target / 'writer', budget, source_pins)
        marker = writer['marker_raw_sha256']
        previous.previous.bridge.projection.evidence._digest(marker)
        result.update(publication_status='completed', writer=writer,
                      marker_raw_sha256=marker,
                      writer_reaped_before_reader_start=True)
        budget.checkpoint()
        result['reader_status'] = 'unconfirmed'
        reader = _role({**request, 'role': 'reader',
                        'expected_marker_sha256': marker},
                       target / 'reader', budget, source_pins)
        if (reader['marker_raw_sha256'] != marker or
                reader['payload_pins'] != writer['payload_pins'] or
                reader['source_payload_pins'] != writer['source_payload_pins'] or
                reader['process']['start_token'] == writer['process']['start_token'] or
                reader['process']['pid'] == writer['process']['pid']):
            raise ValueError('writer/reader binding differs')
        after = _retained(slice_root, expected_slice_result_pin,
                          postcheck_root, expected_postcheck_pin)
        if after != retained:
            raise ValueError('retained publication inputs changed')
        if _source_pins(expected_revision) != source_pins:
            raise ValueError('publication source changed')
        runtime_after = platform_runtime.probe_runtime(ROOT)
        if runtime_after != runtime_before:
            raise ValueError('publication candidate runtime changed')
        result.update(status='verified', reader_status='completed', reader=reader,
                      local_publication_performed=True,
                      payload_files=len(PAYLOAD_NAMES),
                      payload_bytes=sum(pin['bytes'] for pin in retained['payload_pins'].values()),
                      source_pins_after=source_pins,
                      runtime_after=runtime_after)
    except supervisor.UnreapedWorker as error:
        result['reason'] = 'worker_exit_unconfirmed'
        try:
            io._exclusive(target / 'unreaped.json', io.json_bytes(result))
        finally:
            raise error
    except (ValueError, OSError, KeyError, TypeError,
            subprocess.SubprocessError) as error:
        result.update(reason='publication_or_reader_rejected',
                      error_type=type(error).__name__, detail=str(error)[:500])
    finally:
        budgets.finish(budget, target, result, owner_error=sys.exception())
    budget_raw = previous.previous.bounded._bounded_file(target / 'resource-budget.json',
                                                         budgets.RECEIPT_RESERVE // 2)
    result['resource_budget_pin'] = _pin(budget_raw)
    budgets.save_result(target, result)
    return {**result, 'receipt_root': str(target),
            'result_pin': _pin(io.json_bytes(result))}
