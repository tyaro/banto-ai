"""Owned, invented-only producer join for the unadopted 26H2 platform.

The external archive is a retained fixture declaration, not a registered
observation or evidence that an evaluation ran.  This owns one child that
joins those bytes and projects one numerical analysis input.  Selected source
and two Python binary checks are deliberately short of S4 dependency closure.
"""
from __future__ import annotations

import copy
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import zipfile

from . import anomaly_v03_bound_fixture_pipeline as projection
from . import anomaly_v03_platform_fixture as platform
from . import anomaly_v03_platform_fixture_runtime as runtime
from . import anomaly_v03_producer_input_fixture as primary
from . import anomaly_v03_producer_slice_fixture as slices
from . import anomaly_v03_process_supervisor as supervisor
from . import anomaly_v03_reader_evidence as observed
from . import _anomaly_v03_io as io


ROOT = Path(__file__).resolve().parents[2]
FORMAT = 'anomaly-v03-preformal-owned-producer-join-v1'
INVOCATION = 'anomaly-v03-preformal-owned-producer-invocation-v1'
ARCHIVE_MAX = 12 * 1024**2
UNCOMPRESSED_MAX = 24 * 1024**2
OUTPUT_MAX = 12 * 1024**2
LIMITS = {'wall_seconds': 120, 'private_bytes': 512 * 1024**2,
          'output_bytes': 1024**2}
SOURCE_FILES = (
    'src/banto_ai/anomaly_v03_owned_producer_fixture.py',
    'src/banto_ai/anomaly_v03_bound_fixture_pipeline.py',
    'src/banto_ai/anomaly_v03_producer_input_fixture.py',
    'src/banto_ai/anomaly_v03_producer_slice_fixture.py',
    'src/banto_ai/anomaly_v03_platform_fixture.py',
    'src/banto_ai/anomaly_v03_platform_fixture_runtime.py',
    'src/banto_ai/anomaly_v03_process_supervisor.py',
)
BOOTSTRAP = ('import sys;sys.path.insert(0,sys.argv.pop(1));'
             'from banto_ai.anomaly_v03_owned_producer_fixture import worker_main;'
             'raise SystemExit(worker_main(sys.argv[1:]))')


def _pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def _same(actual, expected, label):
    primary.evidence._same(actual, expected, label)


def _sources(revision):
    rows = []
    for name in SOURCE_FILES:
        raw = observed._file(ROOT / name, 1024**2)
        rows.append({'path': name, 'pin': _pin(raw)})
    return {'revision': revision, 'selected_files': rows,
            'scope': 'selected-working-raw-only-not-source-closure'}


def _git_sources(revision):
    """Bind selected working bytes to the current local HEAD, not a full tree."""
    primary.evidence._digest(revision, 40)
    head = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'],
                                   stderr=subprocess.DEVNULL, timeout=10).decode().strip()
    primary.v.require(head == revision, 'selected source revision changed')
    value = _sources(revision)
    for row in value['selected_files']:
        raw = subprocess.check_output(['git', '-C', str(ROOT), 'show',
                                       revision + ':' + row['path']],
                                      stderr=subprocess.DEVNULL, timeout=10)
        _same(_pin(raw), row['pin'], 'selected working/Git raw source')
    return value


def _decode_archive(raw, expected_counts):
    """Decode a bounded archive without extracting any names to disk."""
    primary.v.require(type(expected_counts) is tuple and len(expected_counts) == 2 and
                      all(type(n) is int and n > 0 for n in expected_counts),
                      'invented archive expected counts')
    primary.v.require(type(raw) is bytes and 0 < len(raw) <= ARCHIVE_MAX,
                      'invented archive byte limit')
    with zipfile.ZipFile(BytesIO(raw)) as archive:
        infos = archive.infolist()
        primary.v.require(len(infos) == 2 + sum(expected_counts),
                          'invented archive entry count')
        names = set()
        primary_snapshots, slice_snapshots = {}, {}
        primary_manifest = slice_manifest = None
        total = 0
        for info in infos:
            name = info.filename
            primary.v.safe_relative_path(name)
            primary.v.require(not info.is_dir() and not info.flag_bits & 1 and
                              not (info.create_system == 3 and
                                   (info.external_attr >> 16) & 0o170000 == 0o120000),
                              'unsafe invented archive entry')
            folded = name.casefold()
            primary.v.require(folded not in names, 'duplicate invented archive entry')
            names.add(folded)
            primary.v.require(0 < info.file_size <= 2 * 1024**2,
                              'invented archive member byte limit')
            total += info.file_size
            primary.v.require(total <= UNCOMPRESSED_MAX,
                              'invented archive expanded byte limit')
            data = archive.read(info)
            primary.v.require(len(data) == info.file_size, 'invented archive member changed')
            if name == 'primary/manifest.json':
                primary_manifest = data
            elif name == 'slices/manifest.json':
                slice_manifest = data
            elif name.startswith('primary/files/'):
                primary_snapshots[name[len('primary/files/'):]] = data
            elif name.startswith('slices/files/'):
                slice_snapshots[name[len('slices/files/'):]] = data
            else:
                raise ValueError('unexpected invented archive member')
    primary.v.require(primary_manifest is not None and slice_manifest is not None and
                      len(primary_snapshots) == expected_counts[0] and
                      len(slice_snapshots) == expected_counts[1],
                      'invented archive layout changed')
    primary_document = primary.v.strict_json(primary_manifest)
    primary.v.require(primary_manifest == primary.v.canonical_json(primary_document),
                      'noncanonical invented primary manifest')
    primary_input = {'manifest_raw': primary_manifest, 'snapshots': primary_snapshots,
                     'expected_mode': 'fixture',
                     'expected_manifest_pin': _pin(primary_manifest),
                     'expected_registration_pin': primary_document['registration_pin']}
    return {'primary_input': primary_input, 'manifest_raw': slice_manifest,
            'snapshots': slice_snapshots, 'expected_mode': 'fixture',
            'expected_manifest_pin': _pin(slice_manifest)}


def _archive_case(raw):
    """Decode the exact retained 40-cluster invented archive."""
    return _decode_archive(raw, (9122, 2880))


def _load_invocation(path, expected_pin):
    raw = observed._file(path, 16 * 1024)
    _same(_pin(raw), expected_pin, 'producer invocation pin')
    value = primary.v.strict_json(raw)
    primary.evidence._keys(value,
        'format invocation_id archive_path archive_pin source_revision source output_root',
        'producer invocation fields')
    primary.v.require(value['format'] == INVOCATION, 'producer invocation format')
    primary.evidence._digest(value['invocation_id'])
    primary.evidence._digest(value['source_revision'], 40)
    primary.evidence._pin(value['archive_pin'])
    primary.v.require(value['archive_pin']['bytes'] <= ARCHIVE_MAX,
                      'producer archive size')
    _same(value['source'], _sources(value['source_revision']),
          'producer selected source at invocation')
    return value


def _save_output(root, name, raw):
    path = root / name
    io._exclusive(path, raw)
    _same(_pin(observed._file(path, OUTPUT_MAX)), _pin(raw),
          'producer output readback')
    return _pin(raw)


def worker_main(argv):
    """Produce only a pinned byte join; a failed child never claims completion."""
    try:
        primary.v.require(len(argv) == 3, 'producer child arguments')
        invocation = _load_invocation(Path(argv[0]),
                                      {'bytes': int(argv[1]), 'sha256': argv[2]})
        output = io.regular_path(Path(invocation['output_root']), directory=True)
        source_before = _sources(invocation['source_revision'])
        runtime_before = runtime.probe_runtime(ROOT)
        process = observed.creation_observation(os.getpid())
        archive_raw = observed._file(invocation['archive_path'], ARCHIVE_MAX)
        _same(_pin(archive_raw), invocation['archive_pin'], 'producer external archive pin')
        case = _archive_case(archive_raw)
        bound = slices.bind_producer_slices(**case)
        primary.v.require(bound['status'] == 'fixture_slices_bound' and
                          bound['verified_slice_files'] == 2880 and
                          bound['primary']['planned_evaluations'] == 2880 and
                          bound['complete_for_aggregation'] and
                          not bound['registered_data_read'] and
                          not bound['formal_permission'],
                          'invented producer join scope')
        bound_raw = primary.v.canonical_json(bound)
        primary.v.require(len(bound_raw) <= 8 * 1024**2,
                          'producer bound output byte limit')
        bound_pin = _save_output(output, 'bound.json', bound_raw)
        projected = projection.prepare_inputs(
            bound_raw, expected_mode='fixture', expected_pin=bound_pin,
            expected_revision=invocation['source_revision'], draws=[list(range(40))])
        primary.v.require(len(bound_raw) + sum(map(len, projected['files'].values())) <= OUTPUT_MAX,
                          'producer total output byte limit')
        pins = {}
        for name, data in projected['files'].items():
            primary.v.require(name in projection.analysis.INPUT_LIMITS and
                              len(data) <= projection.analysis.INPUT_LIMITS[name],
                              'projected producer file limit')
            pins[name] = _save_output(output, 'projection/' + name, data)
        primary.v.require(set(pins) == set(projection.analysis.INPUT_LIMITS),
                          'projected producer inventory')
        runtime_after = runtime.probe_runtime(ROOT)
        source_after = _sources(invocation['source_revision'])
        _same(runtime_after, runtime_before, 'producer child runtime changed')
        _same(source_after, source_before, 'producer child selected source changed')
        _same(source_after, invocation['source'], 'producer selected source expectation')
        _same(_pin(observed._file(invocation['archive_path'], ARCHIVE_MAX)),
              invocation['archive_pin'], 'producer external archive changed')
        report = {'format': FORMAT, 'status': 'joined', 'mode': 'fixture',
                  'invocation_id': invocation['invocation_id'],
                  'process': {'pid': os.getpid(), 'parent_pid': os.getppid(),
                              'start_token': process['start_token']},
                  'archive_pin': invocation['archive_pin'],
                  'bound_pin': bound_pin, 'projection_pins': pins,
                  'source_before': source_before, 'source_after': source_after,
                  'runtime_before': runtime_before, 'runtime_after': runtime_after,
                  'joined_slices': 2880, 'projected_draws': 1,
                  'new_evaluations': 0, 'registered_data_read': False,
                  'real_producer_executed': False, 'formal_permission': False}
        print(json.dumps(report, sort_keys=True, separators=(',', ':')))
        return 0
    except (ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile) as error:
        print(json.dumps({'format': FORMAT, 'status': 'rejected',
                          'error_type': type(error).__name__, 'detail': str(error),
                          'formal_permission': False}, sort_keys=True))
        return 2


def join_with_evidence(archive_path, expected_archive_pin, *, expected_revision,
                       receipt_parent, receipt_name, expected_bound_pin=None):
    """Own, reap and verify one 26H2 invented join child in a new local root."""
    primary.evidence._digest(expected_revision, 40)
    primary.evidence._pin(expected_archive_pin)
    primary.v.require(0 < expected_archive_pin['bytes'] <= ARCHIVE_MAX,
                      'invented archive pin byte limit')
    if expected_bound_pin is not None:
        primary.evidence._pin(expected_bound_pin)
    archive_path = Path(archive_path)
    primary.v.require(archive_path.is_absolute() and
                      archive_path.is_relative_to(ROOT / 'artifacts'),
                      'archive must be a retained local artifact')
    parent = io._local_parent(Path(receipt_parent))
    primary.v.require(parent.is_relative_to(ROOT / 'artifacts'),
                      'producer fixture parent must be under artifacts')
    primary.v.safe_relative_path(receipt_name)
    primary.v.require('/' not in receipt_name and '\\' not in receipt_name and
                      not receipt_name.casefold().startswith('anomaly-multiseed-v0'),
                      'new preformal producer receipt name')
    target = io.regular_path(parent / receipt_name, directory=True, missing=True)
    primary.v.require(not target.is_relative_to(archive_path.parent) and
                      not archive_path.is_relative_to(target),
                      'producer input/output overlap')
    archive_raw = observed._file(archive_path, ARCHIVE_MAX)
    _same(_pin(archive_raw), expected_archive_pin, 'external invented archive pin')
    source = _git_sources(expected_revision)
    expected_runtime = runtime.probe_runtime(ROOT)
    target.mkdir()
    output = target / 'output'
    output.mkdir()
    (output / 'projection').mkdir()
    (output / 'projection' / 'fixture').mkdir()
    invocation = {'format': INVOCATION, 'invocation_id': secrets.token_hex(32),
                  'archive_path': str(archive_path), 'archive_pin': copy.deepcopy(expected_archive_pin),
                  'source_revision': expected_revision, 'source': source,
                  'output_root': str(output)}
    invocation_raw = primary.v.canonical_json(invocation)
    io._exclusive(target / 'invocation.json', invocation_raw)
    invocation_pin = _pin(invocation_raw)
    argv = [sys.executable, '-I', '-S', '-B', '-c', BOOTSTRAP,
            str(ROOT / 'src'), str(target / 'invocation.json'),
            str(invocation_pin['bytes']), invocation_pin['sha256']]
    launch = {}
    outer = {'format': FORMAT, 'status': 'failed', 'mode': 'fixture',
             'scope': 'owned-invented-archive-join-and-one-draw-projection',
             'source_revision': expected_revision,
             'source_closure_complete': False, 'runtime_closure_complete': False,
             'new_evaluations': 0, 'registered_data_read': False,
             'real_producer_executed': False, 'owned_producer_join_executed': False,
             'formal_permission': False, 'promotion_allowed': False,
             'worker_exit_confirmed': False, 'worker_pid': None,
             'archive_pin': copy.deepcopy(expected_archive_pin),
             'invocation_pin': invocation_pin}

    def boundary():
        _same(_git_sources(expected_revision), source, 'parent selected source changed')
        _same(runtime.probe_runtime(ROOT), expected_runtime, 'parent runtime changed')
        _same(_pin(observed._file(archive_path, ARCHIVE_MAX)), expected_archive_pin,
              'external invented archive changed')
        _same(_pin(observed._file(target / 'invocation.json', 16 * 1024)),
              invocation_pin, 'producer invocation changed')

    def started(process):
        launch.update(observed.creation_observation(process.pid, process._handle))

    try:
        with platform._platform_scope():
            monitor = supervisor.supervise(argv, ROOT, target / 'worker', LIMITS,
                                           boundary=boundary, on_started=started)
        io._exclusive(target / 'supervision.json', primary.v.canonical_json(monitor))
        outer.update(worker_exit_confirmed=monitor['worker_exit_confirmed'],
                     worker_pid=monitor['worker_pid'],
                     reason=monitor['stop_reason'] or 'worker_failed')
        if monitor['status'] == 'complete':
            primary.v.require(monitor['exit_code'] == 0 and launch and
                              monitor['worker_pid'] == launch['pid'],
                              'producer owned process completion')
            reply_raw = observed._file(target / 'worker' / 'report.json', LIMITS['output_bytes'])
            _same(_pin(reply_raw), monitor['output'], 'producer child stdout pin')
            reply = primary.v.strict_json(reply_raw)
            primary.v.require(reply['format'] == FORMAT and reply['status'] == 'joined' and
                              reply['mode'] == 'fixture' and reply['invocation_id'] == invocation['invocation_id'] and
                              reply['process']['pid'] == launch['pid'] and
                              reply['process']['parent_pid'] == os.getpid() and
                              reply['process']['start_token'] == launch['start_token'],
                              'producer child process binding')
            for key, expected in (('source_before', source), ('source_after', source),
                                  ('runtime_before', expected_runtime), ('runtime_after', expected_runtime),
                                  ('archive_pin', expected_archive_pin)):
                _same(reply[key], expected, 'producer child ' + key)
            primary.v.require(reply['joined_slices'] == 2880 and
                              reply['projected_draws'] == 1 and
                              reply['new_evaluations'] == 0 and
                              reply['registered_data_read'] is False and
                              reply['real_producer_executed'] is False and
                              reply['formal_permission'] is False,
                              'producer child fixture scope')
            bound_raw = observed._file(output / 'bound.json', 8 * 1024**2)
            bound_pin = _pin(bound_raw)
            _same(bound_pin, reply['bound_pin'], 'producer bound output pin')
            if expected_bound_pin is not None:
                _same(bound_pin, expected_bound_pin, 'external expected bound pin')
            expected_projection = projection.prepare_inputs(
                bound_raw, expected_mode='fixture', expected_pin=bound_pin,
                expected_revision=expected_revision, draws=[list(range(40))])
            pins = {}
            for name, data in expected_projection['files'].items():
                saved = observed._file(output / 'projection' / name,
                                       projection.analysis.INPUT_LIMITS[name])
                primary.v.require(saved == data, 'producer projected bytes')
                pins[name] = _pin(saved)
            expected_paths = ('bound.json', *(('projection/' + name)
                                              for name in projection.analysis.INPUT_LIMITS))
            _same(io._tree_paths(output), tuple(sorted(expected_paths)),
                  'producer exact output inventory')
            primary.v.require(bound_pin['bytes'] + sum(p['bytes'] for p in pins.values()) <= OUTPUT_MAX,
                              'producer saved output total')
            _same(pins, reply['projection_pins'], 'producer projected file pins')
            _same(_git_sources(expected_revision), source, 'producer selected source postflight')
            outer.update(status='verified', reason=None,
                         owned_producer_join_executed=True,
                         child_start_token=launch['start_token'],
                         bound_path=str(output / 'bound.json'), bound_pin=bound_pin,
                         projection_root=str(output / 'projection'),
                         projection_pins=pins, stdout_pin=monitor['output'],
                         selected_source_files=len(SOURCE_FILES))
    except supervisor.UnreapedWorker:
        raise
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as error:
        outer.update(reason='producer_evidence_rejected',
                     error_type=type(error).__name__, detail=str(error))
    io._exclusive(target / 'result.json', primary.v.canonical_json(outer))
    return {**outer, 'check_directory': str(target),
            'result_pin': _pin(primary.v.canonical_json(outer))}
