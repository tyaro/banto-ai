"""Caller-pinned runtime observations at actual fixture worker boundaries.

This candidate records whole stdlib disk pins and loaded import/image snapshots.
It authenticates neither in-memory code nor transient loads, external programs,
or a formal campaign. The existing operation and owned-process limits remain.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import sys

from . import anomaly_v03 as v
from . import _anomaly_v03_inventory as inventory
from . import _anomaly_v03_reader_dependencies as dependencies
from . import _anomaly_v03_runtime as paths
from . import anomaly_v03_platform_fixture_runtime as runtime
from . import anomaly_v03_reader_evidence as process_evidence

FORMAT = 'anomaly-v03-arithmetic-runtime-profile-v1'
RECEIPT = 'anomaly-v03-arithmetic-runtime-observation-v1'
PUBLICATION_FORMAT = 'anomaly-v03-publication-runtime-profile-v1'
PUBLICATION_RECEIPT = 'anomaly-v03-publication-runtime-observation-v1'
SAVED_READER_FORMAT = 'anomaly-v03-saved-reader-runtime-profile-v1'
SAVED_READER_RECEIPT = 'anomaly-v03-saved-reader-runtime-observation-v1'
MAX_PROFILE = 2 * 1024**2
MAX_RECEIPT = 2 * 1024**2
MAX_SOURCES = 4096
MAX_STDLIB_FILES = 8192
MAX_STDLIB_BYTES = 128 * 1024**2
OPERATIONS = {'analysis': 'invented40-cluster-50000-primary',
              'audit': 'invented40-cluster-50000-independent-primary-audit',
              'writer': 'publish-invented-full-draw-five-payloads',
              'reader': 'fresh-readback-invented-full-draw-five-payloads',
              'saved-reader': 'reread-invented-saved-chunk-and-rederive-six-evaluations'}
CLOSED = {'formal_permission': False, 'source_closure_complete': False,
          'runtime_closure_complete': False, 'execution_authenticated': False,
          'independent_s6_complete': False}


def _pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def profile_format(role):
    v.require(role in OPERATIONS, 'runtime observation role')
    if role == 'saved-reader':
        return SAVED_READER_FORMAT
    return PUBLICATION_FORMAT if role in ('writer', 'reader') else FORMAT


def receipt_format(role):
    v.require(role in OPERATIONS, 'runtime observation role')
    if role == 'saved-reader':
        return SAVED_READER_RECEIPT
    return PUBLICATION_RECEIPT if role in ('writer', 'reader') else RECEIPT


def required_sources(role):
    v.require(role in OPERATIONS, 'runtime observation role')
    worker = ('anomaly_v03_saved_row_document_publication.py' if role in ('writer', 'reader')
              else 'anomaly_v03_preformal_bound_draw_bridge.py')
    if role == 'saved-reader':
        worker = 'anomaly_v03_preformal_saved_row_reread.py'
    return ['src/banto_ai/' + worker, 'src/banto_ai/anomaly_v03_role_runtime_observation.py']


def _file_pin(value):
    v.require(type(value) is dict and set(value) == {'bytes', 'sha256'}
              and type(value['bytes']) is int and 0 <= value['bytes'] <= 64 * 1024**2
              and type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}', value['sha256']),
              'runtime profile file pin')


def _map(value, maximum, *, source=False):
    v.require(type(value) is dict and 0 < len(value) <= maximum, 'runtime profile inventory size')
    v.require(all(type(name) is str for name in value), 'runtime profile file name')
    v.require(len({name.casefold() for name in value}) == len(value), 'runtime profile path alias')
    for name, pin in value.items():
        v.require(type(name) is str, 'runtime profile file name')
        if not source or name != inventory.a.WORKFLOW:
            v.safe_relative_path(name)
        if source:
            v.require(paths._source_path(name) or name == inventory.a.WORKFLOW,
                      'runtime profile source path')
        _file_pin(pin)


def validate_profile(profile, *, root, role):
    v.require(role in OPERATIONS, 'runtime observation role')
    v.require(type(profile) is dict and set(profile) == {'format', 'mode', 'acceptance',
        'role', 'operation', 'source_root', 'source_revision', 'runtime', 'source_files',
        'stdlib_files', 'native_files', 'cache_files', 'scope'}, 'runtime profile fields')
    v.require(profile['format'] == profile_format(role) and profile['mode'] == 'fixture'
              and profile['acceptance'] == 'candidate-not-accepted'
              and profile['role'] == role and profile['operation'] == OPERATIONS[role]
              and profile['source_root'] == str(Path(root).absolute())
              and v.canonical_json(profile['scope']) == v.canonical_json(CLOSED), 'runtime profile role/root/scope')
    v.require(type(profile['source_revision']) is str
              and re.fullmatch('[0-9a-f]{40}', profile['source_revision']), 'runtime profile revision')
    runtime.validate_runtime(profile['runtime'])
    _map(profile['source_files'], MAX_SOURCES, source=True)
    _map(profile['stdlib_files'], MAX_STDLIB_FILES)
    v.require(sum(p['bytes'] for p in profile['stdlib_files'].values()) <= MAX_STDLIB_BYTES,
              'runtime profile stdlib bytes')
    required = set(required_sources(role))
    v.require(required <= set(profile['source_files']), 'runtime profile worker source missing')
    for section in ('native_files', 'cache_files'):
        values = profile[section]
        v.require(type(values) is dict and len(values) <= dependencies.MAX_FILES
                  and (bool(values) or section == 'cache_files'), 'runtime profile loaded file size')
        v.require(all(type(n) is str for n in values), 'runtime profile physical path')
        v.require(len({n.casefold() for n in values}) == len(values), 'runtime profile physical alias')
        for name, pin in values.items():
            v.require(type(name) is str and Path(name).is_absolute(), 'runtime profile physical path')
            _file_pin(pin)
    return profile


def load_profile(raw, expected_pin, *, root, role):
    v.require(type(raw) is bytes and 0 < len(raw) <= MAX_PROFILE, 'runtime profile byte limit')
    _file_pin(expected_pin)
    v.require(_pin(raw) == expected_pin, 'runtime profile external pin differs')
    return validate_profile(v.strict_json(raw), root=root, role=role)


def _sources(root, expected):
    observed = {}
    total = 0
    for name, pin in sorted(expected.items()):
        row = inventory.hash_file(Path(root) / name, name)
        actual = {'bytes': row['byte_count'], 'sha256': row['raw_sha256']}
        total += actual['bytes']
        v.require(total <= dependencies.MAX_TOTAL, 'runtime observation source bytes')
        v.require(actual == pin, 'runtime observation source bytes differ: ' + name)
        observed[name] = actual
    return observed


def _stdlib():
    before = inventory.stdlib_paths()
    v.require(0 < len(before) <= MAX_STDLIB_FILES, 'runtime observation stdlib files')
    rows, total = {}, 0
    for name, path in before:
        v.require(path.stat().st_size <= MAX_STDLIB_BYTES - total, 'runtime observation stdlib bytes')
        observed = inventory.hash_file(path, name)
        total += observed['byte_count']
        rows[name] = {'bytes': observed['byte_count'], 'sha256': observed['raw_sha256']}
    v.require(before == inventory.stdlib_paths(), 'runtime observation stdlib inventory changed')
    return rows


def prepare_profile(*, root, revision, role, source_files):
    """Candidate self-observation; caller must verify Git origin and retain pin.

    No role operation, source capture via Git, new output, or acceptance occurs.
    Native/cache paths come only from this inspection process's loaded inventory.
    """
    v.require(role in OPERATIONS, 'runtime observation role')
    _map(source_files, MAX_SOURCES, source=True)
    source = _sources(root, source_files)
    observed_runtime = runtime.probe_runtime(root)
    stdlib = _stdlib()
    loaded = dependencies.collect(root)
    native, caches = {}, {}
    for row in loaded['files'].values():
        if row['native']:
            native[row['physical_path']] = row['pin']
        elif row['category'] == 'bytecode-cache-candidate':
            caches[row['physical_path']] = row['pin']
    profile = {'format': profile_format(role), 'mode': 'fixture', 'acceptance': 'candidate-not-accepted',
        'role': role, 'operation': OPERATIONS[role], 'source_root': str(Path(root).absolute()),
        'source_revision': revision, 'runtime': observed_runtime, 'source_files': source,
        'stdlib_files': stdlib, 'native_files': native, 'cache_files': caches, 'scope': dict(CLOSED)}
    return validate_profile(profile, root=root, role=role)


def _loaded_expected(profile, loaded, source, stdlib, root):
    stdlib_paths = {str(path).casefold(): name for name, path in inventory.stdlib_paths()}
    source_paths = {str(Path(root) / name).casefold(): pin for name, pin in source.items()}
    native = {name.casefold(): pin for name, pin in profile['native_files'].items()}
    caches = {name.casefold(): pin for name, pin in profile['cache_files'].items()}
    for row in loaded['files'].values():
        name = row['physical_path'].casefold()
        if row['native']:
            expected = native.get(name)
        elif row['category'] == 'bytecode-cache-candidate':
            expected = caches.get(name)
        elif row['category'] == 'project':
            expected = source_paths.get(name)
        else:
            expected = stdlib.get(stdlib_paths.get(name))
        v.require(expected is not None and row['pin'] == expected,
                  'runtime observation unexpected/changed loaded file: ' + row['physical_path'])


def observe(profile, *, root, phase):
    v.require(phase in ('before', 'after'), 'runtime observation phase')
    observed_runtime = runtime.probe_runtime(root)
    v.require(observed_runtime == profile['runtime'], 'runtime observation tuple differs')
    source = _sources(root, profile['source_files'])
    stdlib = _stdlib()
    v.require(stdlib == profile['stdlib_files'], 'runtime observation stdlib pins differ')
    loaded = dependencies.collect(root)
    _loaded_expected(profile, loaded, source, stdlib, root)
    return {'format': receipt_format(profile['role']), 'role': profile['role'], 'phase': phase,
        'source_revision': profile['source_revision'], 'runtime': observed_runtime,
        'source_files': len(source), 'source_inventory_pin': _pin(v.canonical_json(source)),
        'stdlib_files': len(stdlib), 'stdlib_bytes': sum(p['bytes'] for p in stdlib.values()),
        'stdlib_inventory_pin': _pin(v.canonical_json(stdlib)), 'loaded': loaded, **CLOSED}


def crosscheck_saved(profile, before, after, *, root, input_pin, process, profile_pin):
    """Fresh post-exit disk checks against caller pins; no fresh Git execution."""
    source = _sources(root, profile['source_files'])
    stdlib = _stdlib()
    v.require(stdlib == profile['stdlib_files'], 'runtime post-exit stdlib pins differ')
    for phase, snapshot in (('before', before), ('after', after)):
        v.require(type(snapshot) is dict and set(snapshot) == {'format', 'role', 'phase',
            'source_revision', 'runtime', 'source_files', 'source_inventory_pin', 'stdlib_files',
            'stdlib_bytes', 'stdlib_inventory_pin', 'loaded', 'profile_pin', 'input_pin', 'process',
            *CLOSED}, 'runtime saved observation fields')
        expected = {'format': receipt_format(profile['role']), 'role': profile['role'], 'phase': phase,
            'source_revision': profile['source_revision'], 'runtime': profile['runtime'],
            'source_files': len(source), 'source_inventory_pin': _pin(v.canonical_json(source)),
            'stdlib_files': len(stdlib), 'stdlib_bytes': sum(p['bytes'] for p in stdlib.values()),
            'stdlib_inventory_pin': _pin(v.canonical_json(stdlib)), 'profile_pin': profile_pin,
            'input_pin': input_pin, 'process': process, **CLOSED}
        v.require(all(v.canonical_json(snapshot[k]) == v.canonical_json(value)
                      for k, value in expected.items()), 'runtime saved observation binding differs')
        _loaded_expected(profile, snapshot['loaded'], source, stdlib, root)

    def retained_source(*args):
        v.require(len(args) == 2 and args[0] == 'show' and
                  args[1].startswith(profile['source_revision'] + ':'), 'runtime source lookup')
        name = args[1].split(':', 1)[1]
        v.require(name in source, 'runtime loaded source not pinned')
        raw = process_evidence._file(Path(root) / name, 64 * 1024**2)
        v.require(_pin(raw) == source[name], 'runtime post-exit source changed')
        return raw

    result = dependencies.verify_pair(before['loaded'], after['loaded'], root=root,
        revision=profile['source_revision'], git=retained_source,
        required_sources=required_sources(profile['role']))
    result.update(status='observed_dependencies_external_source_disk_matched',
                  expectation_origin='caller-pinned-source-manifest-not-fresh-git-process')
    return result


def verify_receipt(receipt, *, root, source_root, role, profile_raw, profile_pin, input_pin, process):
    """Bind saved phases to the caller's original-handle identity after exit."""
    profile = load_profile(profile_raw, profile_pin, root=source_root, role=role)
    v.require(type(receipt) is dict and set(receipt) == {'format', 'profile_pin', 'input_pin',
        'before_pin', 'after_pin', 'process', *CLOSED}, 'runtime receipt fields')
    expected = {'format': receipt_format(role), 'profile_pin': profile_pin,
                'input_pin': input_pin, 'process': process, **CLOSED}
    v.require(all(v.canonical_json(receipt[k]) == v.canonical_json(value)
                  for k, value in expected.items()), 'runtime receipt external binding differs')
    snapshots = {}
    for phase in ('before', 'after'):
        _file_pin(receipt[phase + '_pin'])
        raw = process_evidence._file(Path(root) / (role + '-runtime-' + phase + '.json'), MAX_RECEIPT)
        v.require(_pin(raw) == receipt[phase + '_pin'], 'runtime receipt phase pin differs')
        snapshots[phase] = v.strict_json(raw)
    return crosscheck_saved(profile, snapshots['before'], snapshots['after'], root=source_root,
        input_pin=input_pin, process=process, profile_pin=profile_pin)


def run_observed(operation, *, root, source_root, role, profile_raw, profile_pin, input_pin):
    """Wrap actual work; exclusive phase files preserve a failed operation."""
    root = paths.regular_path(Path(root).absolute(), directory=True)
    _file_pin(input_pin)
    profile = load_profile(profile_raw, profile_pin, root=source_root, role=role)
    source_root = Path(profile['source_root'])
    process = process_evidence.creation_observation(os.getpid())

    def save(name, value):
        raw = v.canonical_json(value)
        v.require(len(raw) <= MAX_RECEIPT, 'runtime observation receipt bytes')
        with (root / (role + '-runtime-' + name + '.json')).open('xb') as stream:
            stream.write(raw)
        return _pin(raw)

    try:
        before = observe(profile, root=source_root, phase='before')
        before.update(profile_pin=profile_pin, input_pin=input_pin, process=process)
        before_pin = save('before', before)
        result = operation()
        after = observe(profile, root=source_root, phase='after')
        for section in ('files', 'modules'):
            v.require(all(after['loaded'][section].get(n) == row
                for n, row in before['loaded'][section].items()), 'runtime observation dependency disappeared/changed')
        after.update(profile_pin=profile_pin, input_pin=input_pin, process=process)
        after_pin = save('after', after)
        return result, {'format': receipt_format(role), 'profile_pin': profile_pin, 'input_pin': input_pin,
                        'before_pin': before_pin, 'after_pin': after_pin, 'process': process, **CLOSED}
    except BaseException as error:
        try:
            save('failure', {'format': receipt_format(role), 'role': role, 'status': 'failed', 'profile_pin': profile_pin,
                            'process': process, 'error_type': type(error).__name__, 'detail': str(error)[:1000], **CLOSED})
        except BaseException as diagnostic_error:
            error.add_note('runtime failure receipt could not be saved: ' + type(diagnostic_error).__name__)
        raise
