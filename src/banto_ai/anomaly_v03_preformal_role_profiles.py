"""Prepare five externally anchored dependency candidates from an invented run.

These profiles record two child inventory observations. They do not attest
in-memory code, complete source/runtime closure, registered data, or a formal
campaign. A separate, clean-revision reference run must finish before this
function is called; the next run must retain the returned candidate-set pin.
"""
from __future__ import annotations

import copy
import subprocess
from pathlib import Path

from . import anomaly_v03 as v
from . import anomaly_v03_consumer_evidence as evidence
from . import anomaly_v03_reader_evidence as observed
from . import anomaly_v03_owned_producer_fixture as producer
from . import anomaly_v03_platform_numeric_fixture as numeric
from . import anomaly_v03_platform_fixture as publication_platform
from . import anomaly_v03_platform_fixture_runtime as platform_runtime
from . import _anomaly_v03_reader_dependencies as dependencies
from . import _anomaly_v03_io as io


ROOT = Path(__file__).resolve().parents[2]
REFERENCE_PARENT = ROOT / 'artifacts' / 'anomaly-v03-preformal-five-role-26h2'
PROFILE_PARENT = ROOT / 'artifacts' / 'anomaly-v03-preformal-role-profiles-26h2'
FORMAT = 'anomaly-v03-preformal-five-role-dependency-profile-v1'
SET_FORMAT = 'anomaly-v03-preformal-five-role-profile-set-v1'
ROLES = ('producer', 'analysis', 'audit', 'writer', 'reader')
ROLE_PATHS = {'producer': 'producer', 'analysis': 'analysis', 'audit': 'audit',
              'writer': 'publication/writer', 'reader': 'publication/reader'}
OPERATIONS = {'producer': 'join-invented-archive-and-project-one-draw',
              'analysis': 'assemble-invented-document-v1',
              'audit': 'audit-invented-primary-and-slices-v1',
              'writer': 'publish-invented-five-payloads',
              'reader': 'readback-invented-five-payloads'}
BOUNDARIES = {'producer': 'invocation-decoded-before-invented-archive-read-v1',
              'analysis': 'request-loaded-before-invented-document-assembly-v1',
              'audit': 'request-loaded-before-independent-invented-audit-v1',
              'writer': 'publication-inputs-loaded-before-publish-v1',
              'reader': 'publication-inputs-loaded-before-readback-v1'}
MAX_RESULT = 64 * 1024
MAX_SUPERVISION = 64 * 1024
MAX_REPORT = 1024**2
MAX_DEPENDENCIES = 1024**2
MAX_PROFILE = dependencies.PROFILE_MAX


def _same(actual, expected, label):
    evidence._same(actual, expected, label)


def _read(path, maximum, *, pin=None):
    raw = observed._file(path, maximum)
    if pin is not None:
        evidence._pin(pin)
        evidence._raw(raw, pin, 'retained ' + str(path.name) + ' pin')
    return raw, v.strict_json(raw)


def _head_clean(revision):
    """Require the reference's source revision to be the current clean HEAD."""
    evidence._digest(revision, 40)
    head = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'],
                                   stderr=subprocess.DEVNULL, timeout=10).decode().strip()
    v.require(head == revision, 'reference revision differs from clean HEAD')
    status = subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain'],
                                     stderr=subprocess.DEVNULL, timeout=10)
    v.require(not status.strip(), 'reference candidate must be clean')


def _git_blob(revision):
    cache = {}

    def git(*args):
        v.require(len(args) == 2 and args[0] == 'show' and
                  type(args[1]) is str and args[1].startswith(revision + ':'),
                  'profile Git source request')
        name = args[1][len(revision) + 1:]
        v.safe_relative_path(name)
        v.require(name.startswith('src/'), 'profile Git source scope')
        if name not in cache:
            raw = subprocess.check_output(['git', '-C', str(ROOT), 'show',
                                           revision + ':' + name],
                                          stderr=subprocess.DEVNULL, timeout=10)
            v.require(len(raw) <= dependencies.MAX_FILE, 'profile Git blob limit')
            cache[name] = raw
        return cache[name]

    return git


def _crosscheck(role, before, after, revision):
    required = (producer.SOURCE_FILES if role == 'producer' else
                numeric.SOURCE_FILES if role in ('analysis', 'audit') else
                publication_platform.SOURCE_FILES)
    return dependencies.verify_pair(before, after, root=ROOT, revision=revision,
                                    git=_git_blob(revision), required_sources=required)


def _bind_runtime(role, child_runtime, supervisor_runtime):
    """Bind the child detail schema to the owner's flat 26H2 observation."""
    platform_runtime.validate_runtime(supervisor_runtime)
    if role == 'producer':
        _same(child_runtime, supervisor_runtime,
              'producer/supervisor runtime')
        return
    evidence._runtime(child_runtime)
    platform = child_runtime['platform']
    python = child_runtime['python']
    files = child_runtime['files']
    _same({key: platform[key] for key in
           ('release', 'architecture', 'build', 'ubr')},
          {'release': supervisor_runtime['release'],
           'architecture': supervisor_runtime['architecture'],
           'build': supervisor_runtime['os_build'],
           'ubr': supervisor_runtime['os_ubr']},
          role + ' child/supervisor OS')
    _same(python,
          {'implementation': supervisor_runtime['implementation'],
           'version': supervisor_runtime['python_version'],
           'pointer_bits': supervisor_runtime['pointer_bits'],
           'gil_disabled': supervisor_runtime['gil_disabled']},
          role + ' child/supervisor Python')
    _same(files['python/executable']['pin']['sha256'],
          supervisor_runtime['python_exe_raw_sha256'],
          role + ' child/supervisor Python executable')
    _same(files['python/shared-library']['pin']['sha256'],
          supervisor_runtime['python_dll_raw_sha256'],
          role + ' child/supervisor Python DLL')


def _reference_result(top, publication):
    return {'producer': top['producer']['result_pin'],
            'analysis': top['analysis']['result_pin'],
            'audit': top['audit']['result_pin'],
            'writer': publication['writer']['result_pin'],
            'reader': publication['reader']['result_pin']}


def _require_reference_top(reference, top, budget, publication):
    v.require(top['format'] == 'anomaly-v03-platform-five-role-fixture-v1' and
              top['mode'] == 'fixture' and top['status'] == 'verified' and
              top['stage'] == 'complete' and top['owned_producer_join_executed'] is True and
              top['combined_resource_budget_passed'] is True,
              'completed invented five-role reference required')
    for key, value in evidence.CLOSED.items():
        _same(top[key], value, 'reference top acceptance boundary ' + key)
        _same(publication[key], value,
              'reference publication acceptance boundary ' + key)
    for key in ('registered_data_read', 'real_producer_executed'):
        v.require(top[key] is False, 'reference formal boundary ' + key)
    v.require(top['new_evaluations'] == 0 and
              set(top['identities']) == set(ROLES) and
              not any(key in top for key in ('dependency_profile_set_pin',
                                              'profile_set_pin', 'role_profiles')),
              'unprofiled five-role reference required')
    v.require(budget['root'] == str(reference) and budget['passed'] is True and
              budget['caller_reported_all_five_exits'] is True and
              budget['sampler_exit_confirmed'] is True and
              set(budget['caller_reported_roles']) == set(ROLES),
              'reference shared budget completion')
    v.require(publication['status'] == 'verified' and
              publication['publication_status'] == 'completed' and
              publication['reader_status'] == 'completed' and
              publication['mode'] == 'fixture',
              'reference writer/reader completion')
    return _reference_result(top, publication)


def _role_observation(reference, role, external_pins, result_pin, top,
                      budget, revision, top_pin):
    base = reference / ROLE_PATHS[role]
    _same(external_pins['result'], result_pin,
          role + ' external/top result pin')
    _, result = _read(base / 'result.json', MAX_RESULT,
                      pin=external_pins['result'])
    v.require(result['status'] == 'verified' and
              result.get('worker_exit_confirmed') is True and
              'dependency_profile_pin' not in result and
              'dependency_profile_binding_pin' not in result,
              'completed unprofiled ' + role + ' result required')
    if role in ('producer', 'analysis', 'audit'):
        expected_format = {'producer': producer.FORMAT,
                           'analysis': 'anomaly-v03-fixture-worker-check-v1',
                           'audit': 'anomaly-v03-fixture-audit-check-v1'}[role]
        v.require(result['format'] == expected_format and
                  result['mode'] == 'fixture',
                  role + ' reference result schema')
    if role in ('analysis', 'audit', 'writer', 'reader'):
        v.require(result['role'] == role, role + ' reference result role')
    if role == 'analysis':
        v.require(result['operation'] == OPERATIONS[role],
                  'reference analysis operation')
    if role == 'audit':
        v.require(result['operation'] == OPERATIONS[role],
                  'reference audit operation')
    identity = top['identities'][role]
    budget_role = budget['caller_reported_roles'][role]
    _same(budget_role['result_pin'], result_pin, role + ' budget result pin')
    if 'result_pin' in identity:
        _same(identity['result_pin'], result_pin,
              role + ' top identity result pin')
    v.require(budget_role['status'] == 'verified' and
              budget_role['worker_exit_confirmed'] is True and
              budget_role['worker_pid'] == identity['pid'] == result['worker_pid'],
              role + ' owned exit identity')
    _, supervision = _read(base / 'supervision.json', MAX_SUPERVISION,
                           pin=external_pins['supervision'])
    if 'supervision_pin' in result:
        _same(result['supervision_pin'], external_pins['supervision'],
              role + ' result supervision pin')
    v.require(supervision['format'] == 'anomaly-v03-owned-process-monitor-v1' and
              supervision['status'] == 'complete' and supervision['exit_code'] == 0 and
              supervision['worker_exit_confirmed'] is True and
              supervision['worker_pid'] == identity['pid'] and
              supervision['stop_reason'] is None and
              not supervision['observation_errors'], role + ' supervision completion')
    _same(supervision['runtime_before'], supervision['runtime_after'],
          role + ' supervisor runtime changed')
    stdout_pin = supervision['output']
    evidence._pin(stdout_pin)
    _same(stdout_pin, external_pins['stdout'],
          role + ' external/supervision stdout pin')
    if 'stdout_pin' in identity:
        _same(identity['stdout_pin'], stdout_pin,
              role + ' top identity stdout pin')
    if 'stdout_pin' in result:
        _same(stdout_pin, result['stdout_pin'], role + ' result stdout pin')
    _, stdout = _read(base / 'worker' / 'report.json', MAX_REPORT,
                      pin=external_pins['stdout'])
    dependency_pin = external_pins['dependencies']
    if 'dependency_pin' in result:
        _same(result['dependency_pin'], dependency_pin,
              role + ' result dependency pin')
    _, pair = _read(base / 'dependencies.json', MAX_DEPENDENCIES,
                    pin=dependency_pin)
    evidence._keys(pair, 'before after', role + ' dependency pair')
    _same(pair, {'before': stdout['dependencies_before'],
                 'after': stdout['dependencies_after']},
          role + ' pinned stdout/dependency pair')
    _same(pair['before'], pair['after'], role + ' reference imports changed')
    before = pair['before']
    v.require(before['format'] == dependencies.FORMAT and
              before['scope'] == dependencies.SCOPE and
              0 < len(before['files']) <= dependencies.MAX_FILES and
              len(before['modules']) <= 2048,
              role + ' bounded dependency snapshot')
    checked = _crosscheck(role, before, pair['after'], revision)
    _same(checked, result['dependency_observation'], role + ' dependency crosscheck')

    if role == 'producer':
        v.require(result['source_revision'] == revision and
                  stdout['format'] == producer.FORMAT and
                  stdout['status'] == 'joined' and
                  stdout['process']['pid'] == identity['pid'] and
                  stdout['process']['start_token'] == identity['start_token'] and
                  stdout['invocation_id'] == identity['invocation_id'],
                  'producer reference identity')
        _same(stdout['source_before'], stdout['source_after'],
              'producer selected source changed')
        v.require(stdout['source_before']['revision'] == revision,
                  'producer reference revision')
        _same(stdout['runtime_before'], stdout['runtime_after'],
              'producer runtime changed')
        runtime = stdout['runtime_before']
        evidence_pin = None
    else:
        evidence_pin = result['evidence_pin']
        if 'evidence_pin' in identity:
            _same(identity['evidence_pin'], evidence_pin,
                  role + ' top identity evidence pin')
        _, record = _read(base / 'evidence.json', MAX_RESULT, pin=evidence_pin)
        _same(stdout['evidence'], record, role + ' pinned evidence/stdout')
        v.require(record['format'] == evidence.FORMAT and
                  record['role'] == role and record['mode'] == 'fixture' and
                  record['process']['pid'] == identity['pid'] and
                  record['process']['start_token'] == identity['start_token'] and
                  record['invocation_id'] == identity['invocation_id'] and
                  record['completion'] == {'status': 'completed', 'exit_code': 0,
                                           'worker_exit_confirmed': True,
                                           'observation_errors': []},
                  role + ' reference evidence identity')
        _same(record['source_before'], record['source_after'],
              role + ' selected source changed')
        v.require(record['source_before']['revision'] == revision,
                  role + ' reference revision')
        _same(record['runtime_before'], record['runtime_after'],
              role + ' runtime changed')
        runtime = record['runtime_before']
        if role in ('writer', 'reader'):
            v.require(result['source_revision'] == revision and
                      result['role'] == role, role + ' result role/revision')
    _bind_runtime(role, runtime, supervision['runtime_before'])
    if role in ('producer', 'analysis', 'audit'):
        v.require(result['formal_permission'] is False,
                  role + ' formal boundary')
    reference_pins = {'top_result_pin': copy.deepcopy(top_pin),
                      'result_pin': copy.deepcopy(external_pins['result']),
                      'supervision_pin': copy.deepcopy(external_pins['supervision']),
                      'stdout_pin': copy.deepcopy(external_pins['stdout']),
                      'dependency_pin': copy.deepcopy(external_pins['dependencies'])}
    if evidence_pin is not None:
        reference_pins['evidence_pin'] = copy.deepcopy(evidence_pin)
    return runtime, before, reference_pins


def prepare_profiles(reference_root, expected_result_pin, *, output_root,
                     expected_role_pins):
    """Save five candidate files and a pin index under one new, disjoint root.

    The caller must retain the top result pin and four file pins for every role
    before this call. Missing pins never fall back to hashes calculated from
    the current reference files.
    """
    evidence._pin(expected_result_pin)
    v.require(type(expected_role_pins) is dict and
              set(expected_role_pins) == set(ROLES),
              'external five-role observation pin inventory')
    for role in ROLES:
        row = expected_role_pins[role]
        v.require(type(row) is dict and
                  set(row) == {'result', 'supervision', 'stdout', 'dependencies'},
                  role + ' external observation pin inventory')
        for pin in row.values():
            evidence._pin(pin)
    reference = Path(reference_root)
    target = Path(output_root)
    v.require(reference.is_absolute() and reference.parent == REFERENCE_PARENT and
              target.is_absolute() and target.parent == PROFILE_PARENT and
              reference != target and not reference.is_relative_to(target) and
              not target.is_relative_to(reference),
              'separate known invented reference/profile roots required')
    io.regular_path(reference, directory=True)
    io.regular_path(PROFILE_PARENT, directory=True, missing=True)
    _, top = _read(reference / 'result.json', MAX_RESULT, pin=expected_result_pin)
    revision = top['source_revision']
    _head_clean(revision)
    _, budget = _read(reference / 'resource-budget.json', MAX_RESULT,
                      pin=top['resource_budget_pin'])
    _, publication = _read(reference / 'publication' / 'result.json', MAX_RESULT,
                           pin=top['publication']['result_pin'])
    result_pins = _require_reference_top(reference, top, budget, publication)
    profiles = {}
    for role in ROLES:
        runtime, snapshot, pins = _role_observation(reference, role,
            expected_role_pins[role], result_pins[role], top, budget,
            revision, expected_result_pin)
        profile = {'format': FORMAT, 'mode': 'fixture', 'role': role,
                   'operation': OPERATIONS[role], 'boundary': BOUNDARIES[role],
                   'acceptance': 'candidate-not-accepted',
                   'source_revision': revision, 'root': str(ROOT),
                   'runtime': runtime, 'snapshot': snapshot,
                   'reference_root': str(reference), 'reference': pins,
                   'scope': copy.deepcopy(dependencies.SCOPE),
                   'formal_permission': False,
                   'source_closure_complete': False,
                   'runtime_closure_complete': False}
        raw = io.json_bytes(profile)
        v.require(0 < len(raw) <= MAX_PROFILE, role + ' candidate profile limit')
        profiles[role] = raw
    _head_clean(revision)
    PROFILE_PARENT.mkdir(exist_ok=True)
    io.regular_path(target, directory=True, missing=True)
    target.mkdir()
    role_pins = {}
    for role, raw in profiles.items():
        path = target / (role + '.json')
        io._exclusive(path, raw)
        pin = observed._pin(raw)
        evidence._raw(observed._file(path, MAX_PROFILE), pin,
                      'saved ' + role + ' candidate changed')
        role_pins[role] = {'path': str(path), 'pin': pin}
    index = {'format': SET_FORMAT, 'status': 'candidate_profiles_prepared',
             'acceptance': 'candidate-not-accepted', 'source_revision': revision,
             'root': str(ROOT), 'reference_root': str(reference),
             'reference_result_pin': copy.deepcopy(expected_result_pin),
             'roles': role_pins, 'scope': copy.deepcopy(dependencies.SCOPE),
             'formal_permission': False, 'registered_data_read': False,
             'source_closure_complete': False, 'runtime_closure_complete': False,
             'execution_authenticated': False, 'promotion_allowed': False}
    index_raw = io.json_bytes(index)
    io._exclusive(target / 'candidate-set.json', index_raw)
    index_pin = observed._pin(index_raw)
    evidence._raw(observed._file(target / 'candidate-set.json', MAX_RESULT),
                  index_pin, 'saved candidate set changed')
    return {'status': 'candidate_profiles_prepared', 'output_root': str(target),
            'candidate_set_pin': index_pin, 'role_profiles': role_pins,
            'source_revision': revision, 'formal_permission': False,
            'source_closure_complete': False, 'runtime_closure_complete': False}
