"""Bind supplied consumer evidence to caller-retained expectations and bytes.

Pure validation: no path access, Git, process launch or runtime collection.
The caller owns the trust boundary for expectations, revision snapshots and
process observations. Equality does not attest execution or complete a gate.
"""
from __future__ import annotations

import copy
import hashlib
from collections.abc import Mapping
from pathlib import PureWindowsPath
import re

from . import anomaly_v03 as v

FORMAT = 'anomaly-v03-consumer-execution-evidence-v1'
MODES = ('fixture', 'engineering-dev-smoke')
ROLES = ('analysis', 'audit', 'reader')
MAX_EVIDENCE_BYTES = 1024**2  # Metadata parser bound, not a run resource budget.
MAX_FILES = 4096
FLAGS = {'isolated': 1, 'ignore_environment': 1, 'no_user_site': 1,
         'no_site': 1, 'safe_path': True, 'dont_write_bytecode': 1}
CLOSED = {'formal_permission': False, 'promotion_allowed': False,
          'independent_s6_complete': False, 'result_trusted': False,
          'execution_authenticated': False, 'source_closure_complete': False,
          'runtime_closure_complete': False, 'performance_status': 'not_evaluated',
          'selected_candidate': None}


def _keys(value, names, reason):
    v.require(type(value) is dict and set(value) == set(names.split()), reason)


def _same(actual, expected, reason):
    v.require(v.canonical_json(actual) == v.canonical_json(expected), reason)


def _text(value):
    v.require(type(value) is str and bool(value) and '\0' not in value, 'nonempty text required')


def _digest(value, size=64):
    v.require(type(value) is str and re.fullmatch('[0-9a-f]{'+str(size)+'}', value), 'invalid digest/revision')


def _integer(value, minimum=0):
    v.require(type(value) is int and value >= minimum, 'invalid integer')


def _pin(value):
    _keys(value, 'bytes sha256', 'pin fields')
    _integer(value['bytes']);_digest(value['sha256'])


def _raw(raw, expected, reason):
    v.require(type(raw) is bytes and len(raw) == expected['bytes'] and
              hashlib.sha256(raw).hexdigest() == expected['sha256'], reason)


def _absolute(value):
    # Lexical Windows profile only. Never resolve, stat, or open a named path.
    _text(value)
    v.require(re.match(r'^[A-Za-z]:[\\/]', value) and PureWindowsPath(value).is_absolute(),
              'local absolute Windows path required')
    parts = re.split(r'[\\/]', value[3:]) if len(value) > 3 else []
    for part in parts:
        v.require(part not in ('', '.', '..') and not part.endswith(('.', ' ')) and
                  not re.search(r'[\x00-\x1f<>:"|?*]', part), 'ambiguous absolute path')
        v.require(part.split('.')[0].upper() not in {'CON', 'PRN', 'AUX', 'NUL',
                  *(f'COM{i}' for i in range(10)), *(f'LPT{i}' for i in range(10))}, 'reserved path')
    return str(PureWindowsPath(value)).casefold()


def _inventory(value, *, runtime=False):
    v.require(type(value) is dict and 1 <= len(value) <= MAX_FILES, 'nonempty bounded file inventory')
    names = list(value)
    for name in names:v.safe_relative_path(name)
    v.require(len(set(n.casefold() for n in names)) == len(names), 'case-alias file inventory')
    physical = []
    for row in value.values():
        if runtime:
            _keys(row, 'physical_path category pin', 'runtime file fields')
            _text(row['category'])
            v.require(row['category'] in ('python', 'stdlib', 'extension', 'native', 'tool'), 'runtime category')
            physical.append(_absolute(row['physical_path']));_pin(row['pin'])
        else:_pin(row)
    v.require(len(set(physical)) == len(physical), 'duplicate runtime physical file')


def _source(source):
    _keys(source, 'revision sources', 'source descriptor fields');_digest(source['revision'], 40)
    rows = source['sources']
    v.require(type(rows) is list and 1 <= len(rows) <= MAX_FILES, 'bounded source inventory')
    names = []
    for row in rows:
        _keys(row, 'path raw_sha256 byte_count', 'source entry fields')
        names.append(v.safe_relative_path(row['path']))
        _digest(row['raw_sha256']);_integer(row['byte_count'])
    v.require(names == sorted(names) and len(set(n.casefold() for n in names)) == len(names),
              'source order/uniqueness')


def _runtime(runtime):
    _keys(runtime, 'platform python startup files', 'runtime fields')
    platform = runtime['platform']
    _keys(platform, 'system release build ubr architecture cpu_identity', 'platform fields')
    _same(platform['system'], 'Windows', 'Windows observation required')
    _same(platform['architecture'], 'AMD64', 'architecture')
    for name in ('release', 'cpu_identity'):_text(platform[name])
    _integer(platform['build'], 22000);_integer(platform['ubr'])
    # OS build/UBR are caller-pinned observations, not the old formal pin.
    _same(runtime['python'], {'implementation': 'CPython', 'version': '3.14.0',
          'pointer_bits': 64, 'gil_disabled': False}, 'consumer Python profile')
    startup = runtime['startup']
    _keys(startup, 'flags sys_path site_imported hooks', 'startup fields')
    _same(startup['flags'], FLAGS, 'isolated no-site startup flags')
    _same(startup['site_imported'], False, 'site initialization');_same(startup['hooks'], [], 'startup hooks')
    paths = startup['sys_path']
    v.require(type(paths) is list and 1 <= len(paths) <= 64, 'bounded search path')
    normalized = [_absolute(p) for p in paths]
    v.require(len(set(normalized)) == len(paths), 'duplicate search path')
    v.require(not any({'site-packages', 'dist-packages'} & set(PureWindowsPath(p).parts)
                      for p in normalized), 'site package search path')
    files = runtime['files'];_inventory(files, runtime=True)
    for name in ('python/executable', 'python/shared-library'):
        v.require(name in files and files[name]['category'] == 'python', 'Python file inventory')


def _expectation(expected):
    _keys(expected, 'invocation_id source process runtime inputs outputs', 'external expectation fields')
    v.json_value(expected);_digest(expected['invocation_id']);_source(expected['source'])
    process = expected['process']
    _keys(process, 'pid parent_pid start_token argv cwd', 'process fields')
    _integer(process['pid'], 1);_integer(process['parent_pid'], 1)
    v.require(process['pid'] != process['parent_pid'], 'separate worker PID required')
    _digest(process['start_token']);_absolute(process['cwd'])
    argv = process['argv']
    v.require(type(argv) is list and 6 <= len(argv) <= 256, 'explicit launch command')
    for arg in argv:_text(arg)
    _absolute(argv[0])
    v.require(argv[1:4] == ['-I', '-S', '-B'] and argv[4] in ('-c', '-m'), 'isolated launch options')
    _runtime(expected['runtime'])
    _same(argv[0], expected['runtime']['files']['python/executable']['physical_path'], 'launched Python identity')
    for name in ('inputs', 'outputs'):_inventory(expected[name])


def _snapshots(supplied, pins, reason):
    # Mapping permits a caller-owned lazy byte provider: at most one supplied
    # file value is retained here. This module never interprets paths as IO.
    v.require(isinstance(supplied, Mapping) and set(supplied) == set(pins), reason+' inventory')
    for name, expected in pins.items():_raw(supplied[name], expected, reason+' bytes/hash')


def validate_execution_evidence(raw, *, expected_mode, expected_role, expected_pin,
                                expected, source_snapshots, runtime_snapshots,
                                input_snapshots, output_snapshots):
    """Check one completed invocation and bind every listed input/output byte.

    All expected arguments MUST come from a caller-retained plan/launch record,
    not be copied from the evidence being checked. Source snapshots must come
    from that externally selected full revision. Runtime/IO snapshots and PID/
    start-token observations are also caller responsibilities. A forged bundle
    plus forged expectations cannot be detected by this pure function.

    Modes are fixture or engineering-dev-smoke; no formal entry is opened.
    The returned descriptor is for evidence wiring, not document promotion.
    """
    v.require(type(expected_mode) is str and expected_mode in MODES, 'formal/unknown evidence mode is closed')
    v.require(type(expected_role) is str and expected_role in ROLES, 'unsupported consumer role')
    _pin(expected_pin)
    v.require(expected_pin['bytes'] <= MAX_EVIDENCE_BYTES, 'evidence metadata size limit')
    _raw(raw, expected_pin, 'external evidence pin mismatch')
    value = v.strict_json(raw)
    _expectation(expected)
    _keys(value, 'format mode role invocation_id source_before source_after process runtime_before runtime_after inputs outputs completion',
          'execution evidence fields')
    _same(value['format'], FORMAT, 'execution evidence format')
    _same(value['mode'], expected_mode, 'evidence mode');_same(value['role'], expected_role, 'evidence role')
    for name in ('invocation_id', 'process', 'inputs', 'outputs'):
        _same(value[name], expected[name], name+' binding')
    for phase in ('before', 'after'):
        _same(value['source_'+phase], expected['source'], 'source '+phase+' binding')
        _same(value['runtime_'+phase], expected['runtime'], 'runtime '+phase+' binding')
    _same(value['completion'], {'status': 'completed', 'exit_code': 0,
          'worker_exit_confirmed': True, 'observation_errors': []}, 'successful observed completion required')
    source = expected['source'];revision = source['revision']
    v.require(isinstance(source_snapshots, Mapping) and set(source_snapshots) == {revision}, 'source revision inventory')
    source_pins = {r['path']: {'bytes': r['byte_count'], 'sha256': r['raw_sha256']} for r in source['sources']}
    _snapshots(source_snapshots[revision], source_pins, 'source snapshot')
    runtime_pins = {n: r['pin'] for n, r in expected['runtime']['files'].items()}
    _snapshots(runtime_snapshots, runtime_pins, 'runtime snapshot')
    _snapshots(input_snapshots, expected['inputs'], 'input snapshot')
    _snapshots(output_snapshots, expected['outputs'], 'output snapshot')
    return {**CLOSED, 'status': 'supplied_consumer_evidence_bound', 'scope': 'supplied-bytes-only',
            'mode': expected_mode, 'role': expected_role, 'invocation_id': value['invocation_id'],
            'evidence_pin': copy.deepcopy(expected_pin), 'source_descriptor': copy.deepcopy(source),
            'input_pins': copy.deepcopy(expected['inputs']), 'output_pins': copy.deepcopy(expected['outputs']),
            'source_files': len(source_pins), 'runtime_files': len(runtime_pins),
            'process_binding_checked': True, 'revision_authentication_requires_trusted_caller': True}
