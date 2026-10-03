"""Prepare five externally anchored dependency candidates from an invented run.

These profiles fix two child inventory observations and the reference parent's
crosscheck receipt. They do not independently recheck every dependency file,
attest in-memory code, complete closure, or authorize a formal campaign.
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
FORMAT = 'anomaly-v03-preformal-five-role-dependency-profile-v3'
SET_FORMAT = 'anomaly-v03-preformal-five-role-profile-set-v3'
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


def _verify_selected_source(role, source, revision):
    """Recheck selected code only; never reuse this process's loaded images."""
    required = (producer.SOURCE_FILES if role == 'producer' else
                numeric.SOURCE_FILES if role in ('analysis', 'audit') else
                publication_platform.SOURCE_FILES)
    v.require(source['revision'] == revision,
              role + ' selected source revision')
    rows = source['selected_files'] if role == 'producer' else source['sources']
    v.require(type(rows) is list and
              {row['path'] for row in rows} == set(required) and
              len(rows) == len(required), role + ' selected source inventory')
    git = _git_blob(revision)
    for row in rows:
        name = row['path']
        raw = observed._file(ROOT / name, 1024**2)
        expected = (row['pin'] if role == 'producer' else
                    {'bytes': row['byte_count'], 'sha256': row['raw_sha256']})
        evidence._raw(raw, expected, role + ' selected working source pin')
        v.require(raw == git('show', revision + ':' + name),
                  role + ' selected Git source bytes')


def _historical_crosscheck(role, check, before, after):
    """Match the separately pinned historical parent verdict to both snapshots."""
    fields = {'status', 'expectation_origin', 'project_files', 'files',
              'modules', 'native_files', 'added_files_during_read',
              'added_modules_during_read', *dependencies.SCOPE}
    v.require(type(check) is dict and set(check) == fields and
              check['status'] == 'observed_dependencies_disk_git_matched' and
              check['expectation_origin'] ==
                  'child-inventory-crosschecked-by-parent-after-exit',
              role + ' retained historical crosscheck schema')
    for key, value in dependencies.SCOPE.items():
        _same(check[key], value, role + ' historical crosscheck ' + key)
    _same(check['files'], len(after['files']), role + ' crosscheck file count')
    _same(check['modules'], len(after['modules']), role + ' crosscheck module count')
    _same(check['native_files'], len(after['native_files']),
          role + ' crosscheck native count')
    _same(check['project_files'],
          sum(row['category'] == 'project' for row in after['files'].values()),
          role + ' crosscheck project count')
    _same(check['added_files_during_read'],
          sorted(set(after['files']) - set(before['files'])),
          role + ' crosscheck added files')
    _same(check['added_modules_during_read'],
          sorted(set(after['modules']) - set(before['modules'])),
          role + ' crosscheck added modules')


def _two_point_inventory(before, after, role):
    """Keep both observations; only new file/module rows may appear later."""
    fields = {'format', 'modules', 'files', 'native_files', 'scope'}
    for phase, snapshot in (('before', before), ('after', after)):
        v.require(type(snapshot) is dict and set(snapshot) == fields and
                  snapshot['format'] == dependencies.FORMAT and
                  snapshot['scope'] == dependencies.SCOPE and
                  type(snapshot['files']) is dict and
                  0 < len(snapshot['files']) <= dependencies.MAX_FILES and
                  type(snapshot['modules']) is dict and
                  len(snapshot['modules']) <= 2048 and
                  type(snapshot['native_files']) is list and
                  snapshot['native_files'] == sorted(set(snapshot['native_files'])),
                  role + ' ' + phase + ' bounded dependency snapshot')
    for section in ('files', 'modules'):
        v.require(all(after[section].get(name) == row
                      for name, row in before[section].items()),
                  role + ' existing dependency changed/disappeared')
    v.require(set(before['native_files']) <= set(after['native_files']),
              role + ' loaded image disappeared')


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


def _reference_result(top, expected_role_pins):
    return {'producer': top['producer']['result_pin'],
            'analysis': top['analysis']['result_pin'],
            'audit': top['audit']['result_pin'],
            'writer': expected_role_pins['writer']['result'],
            'reader': expected_role_pins['reader']['result']}


def _require_reference_top(reference, top, budget, publication,
                           expected_role_pins):
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
    for role in ('writer', 'reader'):
        _, saved = _read(reference / ROLE_PATHS[role] / 'result.json',
                         MAX_RESULT, pin=expected_role_pins[role]['result'])
        _same(publication[role], saved,
              role + ' publication embedded result')
    return _reference_result(top, expected_role_pins)


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
    before, after = pair['before'], pair['after']
    _two_point_inventory(before, after, role)
    _, checked = _read(base / 'dependency-crosscheck.json', MAX_RESULT,
                       pin=external_pins['crosscheck'])
    _same(checked, result['dependency_observation'],
          role + ' historical result/crosscheck')
    _historical_crosscheck(role, checked, before, after)

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
        _verify_selected_source(role, stdout['source_before'], revision)
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
        _verify_selected_source(role, record['source_before'], revision)
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
    reference_pins['crosscheck_pin'] = copy.deepcopy(external_pins['crosscheck'])
    if evidence_pin is not None:
        reference_pins['evidence_pin'] = copy.deepcopy(evidence_pin)
    return runtime, pair, reference_pins


def prepare_profiles(reference_root, expected_result_pin, *, output_root,
                     expected_role_pins):
    """Save five candidate files and a pin index under one new, disjoint root.

    The caller must retain the top result pin and five file pins for every role
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
                  set(row) == {'result', 'supervision', 'stdout',
                               'dependencies', 'crosscheck'},
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
    result_pins = _require_reference_top(reference, top, budget, publication,
                                         expected_role_pins)
    profiles = {}
    for role in ROLES:
        runtime, snapshots, pins = _role_observation(reference, role,
            expected_role_pins[role], result_pins[role], top, budget,
            revision, expected_result_pin)
        profile = {'format': FORMAT, 'mode': 'fixture', 'role': role,
                   'operation': OPERATIONS[role], 'boundary': BOUNDARIES[role],
                   'acceptance': 'candidate-not-accepted',
                   'source_revision': revision, 'root': str(ROOT),
                   'runtime': runtime, 'snapshots': snapshots,
                   'observation_semantics':
                       'two-point-before-and-after-with-additions-only',
                   'crosscheck_scope':
                       'historical-parent-verdict-pinned-no-current-image-allowlist',
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
