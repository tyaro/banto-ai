"""Pure, invented-only tests for externally pinned five-role profile creation."""
from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from banto_ai import anomaly_v03_preformal_role_profiles as profiles
from banto_ai import anomaly_v03_platform_fixture_runtime as runtime
from banto_ai import anomaly_v03_consumer_evidence as evidence
from banto_ai import _anomaly_v03_reader_dependencies as dependencies
from banto_ai import _anomaly_v03_io as io
from banto_ai import anomaly_v03 as v


REVISION = 'a' * 40
SUMMARY = {'status': 'observed_dependencies_disk_git_matched'}


def child_runtime():
    return {'platform': {'system': 'Windows', 'release': '26H2',
                         'build': 26300, 'ubr': 9457, 'architecture': 'AMD64',
                         'cpu_identity': 'invented CPU'},
            'python': {'implementation': 'CPython', 'version': '3.14.0',
                       'pointer_bits': 64, 'gil_disabled': False},
            'startup': {'flags': copy.deepcopy(evidence.FLAGS),
                        'sys_path': [r'D:\develop\banto-ai\src'],
                        'site_imported': False, 'hooks': []},
            'files': {
                'python/executable': {'physical_path': r'C:\Python314\python.exe',
                                      'category': 'python',
                                      'pin': {'bytes': 1,
                                              'sha256': runtime.EXPECTED['python_exe_raw_sha256']}},
                'python/shared-library': {'physical_path': r'C:\Python314\python314.dll',
                                          'category': 'python',
                                          'pin': {'bytes': 1,
                                                  'sha256': runtime.EXPECTED['python_dll_raw_sha256']}}}}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = io.json_bytes(value)
    path.write_bytes(raw)
    return {'bytes': len(raw), 'sha256': profiles.observed._pin(raw)['sha256']}


class RoleProfileTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.reference_parent = self.root / 'artifacts' / 'anomaly-v03-preformal-five-role-26h2'
        self.profile_parent = self.root / 'artifacts' / 'anomaly-v03-preformal-role-profiles-26h2'
        self.reference = self.reference_parent / 'reference-01'
        self.output = self.profile_parent / 'candidate-01'
        self.reference.mkdir(parents=True)
        self.profile_parent.mkdir(parents=True)
        for name, value in (('ROOT', self.root),
                            ('REFERENCE_PARENT', self.reference_parent),
                            ('PROFILE_PARENT', self.profile_parent)):
            context = patch.object(profiles, name, value)
            context.start()
            self.addCleanup(context.stop)
        for name, value in (('_head_clean', lambda revision: None),
                            ('_verify_selected_source',
                             lambda role, source, revision: None)):
            context = patch.object(profiles, name, value)
            context.start()
            self.addCleanup(context.stop)
        self.expected_role_pins = {}
        self.result_pins = {}
        self.identities = {}
        self.budget_roles = {}
        self._reference()

    def _reference(self, *, producer_addition=False, producer_change=False):
        snapshot = {'format': dependencies.FORMAT,
                    'scope': copy.deepcopy(dependencies.SCOPE),
                    'files': {'project/src/banto_ai/invented.py':
                              {'category': 'project'}},
                    'modules': {}, 'native_files': []}
        for index, role in enumerate(profiles.ROLES):
            path = self.reference / profiles.ROLE_PATHS[role]
            path.mkdir(parents=True, exist_ok=True)
            pid = 1000 + index
            token = format(index + 1, '064x')
            invocation = format(index + 11, '064x')
            self.identities[role] = {'pid': pid, 'start_token': token,
                                     'invocation_id': invocation}
            pair = {'before': copy.deepcopy(snapshot),
                    'after': copy.deepcopy(snapshot)}
            if role == 'producer' and producer_addition:
                pair['after']['files']['python-files/Lib/encodings/cp437.py'] = {
                    'category': 'stdlib'}
                pair['after']['files'][
                    'python-files/Lib/encodings/__pycache__/cp437.cpython-314.pyc'
                ] = {'category': 'bytecode-cache-candidate'}
                pair['after']['modules']['encodings.cp437'] = {'kind': 'file'}
            if role == 'producer' and producer_change:
                pair['after']['files']['project/src/banto_ai/invented.py'] = {
                    'category': 'project', 'pin': 'changed'}
            dependency_pin = save(path / 'dependencies.json', pair)
            checked = {**dependencies.SCOPE,
                       'status': 'observed_dependencies_disk_git_matched',
                       'expectation_origin':
                           'child-inventory-crosschecked-by-parent-after-exit',
                       'project_files': sum(row['category'] == 'project'
                                            for row in pair['after']['files'].values()),
                       'files': len(pair['after']['files']),
                       'modules': len(pair['after']['modules']),
                       'native_files': len(pair['after']['native_files']),
                       'added_files_during_read': sorted(
                           set(pair['after']['files']) - set(pair['before']['files'])),
                       'added_modules_during_read': sorted(
                           set(pair['after']['modules']) - set(pair['before']['modules']))}
            crosscheck_pin = save(path / 'dependency-crosscheck.json', checked)
            if role == 'producer':
                stdout = {'format': profiles.producer.FORMAT, 'status': 'joined',
                          'process': {'pid': pid, 'start_token': token},
                          'invocation_id': invocation,
                          'source_before': {'revision': REVISION},
                          'source_after': {'revision': REVISION},
                          'runtime_before': copy.deepcopy(runtime.EXPECTED),
                          'runtime_after': copy.deepcopy(runtime.EXPECTED),
                          'dependencies_before': pair['before'],
                          'dependencies_after': pair['after']}
                evidence_pin = None
            else:
                record = {'format': evidence.FORMAT,
                          'role': role, 'mode': 'fixture',
                          'process': {'pid': pid, 'start_token': token},
                          'invocation_id': invocation,
                          'completion': {'status': 'completed', 'exit_code': 0,
                                         'worker_exit_confirmed': True,
                                         'observation_errors': []},
                          'source_before': {'revision': REVISION},
                          'source_after': {'revision': REVISION},
                          'runtime_before': child_runtime(),
                          'runtime_after': child_runtime()}
                evidence_pin = save(path / 'evidence.json', record)
                stdout = {'evidence': record,
                          'dependencies_before': pair['before'],
                          'dependencies_after': pair['after']}
            stdout_pin = save(path / 'worker' / 'report.json', stdout)
            monitor = {'format': 'anomaly-v03-owned-process-monitor-v1',
                       'status': 'complete', 'exit_code': 0,
                       'worker_exit_confirmed': True, 'worker_pid': pid,
                       'stop_reason': None, 'observation_errors': [],
                       'runtime_before': copy.deepcopy(runtime.EXPECTED),
                       'runtime_after': copy.deepcopy(runtime.EXPECTED),
                       'output': stdout_pin}
            supervision_pin = save(path / 'supervision.json', monitor)
            result = {'status': 'verified', 'worker_exit_confirmed': True,
                      'worker_pid': pid, 'dependency_observation': checked}
            if role in ('producer', 'analysis', 'audit'):
                result['formal_permission'] = False
                result['mode'] = 'fixture'
                result['format'] = {
                    'producer': profiles.producer.FORMAT,
                    'analysis': 'anomaly-v03-fixture-worker-check-v1',
                    'audit': 'anomaly-v03-fixture-audit-check-v1'}[role]
            if role == 'producer':
                result.update(source_revision=REVISION, stdout_pin=stdout_pin,
                              dependency_pin=dependency_pin)
            else:
                result['role'] = role
                result['evidence_pin'] = evidence_pin
                if role in ('writer', 'reader'):
                    result.update(role=role, source_revision=REVISION,
                                  supervision_pin=supervision_pin,
                                  stdout_pin=stdout_pin,
                                  dependency_pin=dependency_pin)
                if role == 'analysis':
                    result['stdout_pin'] = stdout_pin
                if role in ('analysis', 'audit'):
                    result['operation'] = profiles.OPERATIONS[role]
            result_pin = save(path / 'result.json', result)
            self.result_pins[role] = result_pin
            if role == 'producer':
                self.identities[role].update(result_pin=result_pin,
                                             stdout_pin=stdout_pin)
            else:
                self.identities[role]['evidence_pin'] = evidence_pin
            self.expected_role_pins[role] = {'result': result_pin,
                                             'supervision': supervision_pin,
                                             'stdout': stdout_pin,
                                             'dependencies': dependency_pin,
                                             'crosscheck': crosscheck_pin}
            self.budget_roles[role] = {'result_pin': result_pin,
                                       'status': 'verified',
                                       'worker_exit_confirmed': True,
                                       'worker_pid': pid}
        publication = {**evidence.CLOSED, 'status': 'verified',
                       'mode': 'fixture', 'publication_status': 'completed',
                       'reader_status': 'completed',
                       'writer': v.strict_json((self.reference / 'publication' /
                                                'writer' / 'result.json').read_bytes()),
                       'reader': v.strict_json((self.reference / 'publication' /
                                                'reader' / 'result.json').read_bytes())}
        publication_pin = save(self.reference / 'publication' / 'result.json',
                               publication)
        budget = {'root': str(self.reference), 'passed': True,
                  'caller_reported_all_five_exits': True,
                  'sampler_exit_confirmed': True,
                  'caller_reported_roles': self.budget_roles}
        budget_pin = save(self.reference / 'resource-budget.json', budget)
        top = {**evidence.CLOSED,
               'format': 'anomaly-v03-platform-five-role-fixture-v1',
               'mode': 'fixture', 'status': 'verified', 'stage': 'complete',
               'owned_producer_join_executed': True,
               'combined_resource_budget_passed': True,
               'registered_data_read': False, 'real_producer_executed': False,
               'new_evaluations': 0, 'source_revision': REVISION,
               'identities': self.identities, 'resource_budget_pin': budget_pin,
               'producer': {'result_pin': self.result_pins['producer']},
               'analysis': {'result_pin': self.result_pins['analysis']},
               'audit': {'result_pin': self.result_pins['audit']},
               'publication': {'result_pin': publication_pin}}
        self.top_pin = save(self.reference / 'result.json', top)

    def prepare(self, *, pins=None, top_pin=None, output=None):
        return profiles.prepare_profiles(
            self.reference, self.top_pin if top_pin is None else top_pin,
            output_root=self.output if output is None else output,
            expected_role_pins=(self.expected_role_pins if pins is None else pins))

    def test_five_candidate_profiles_and_manifest_are_saved_once(self):
        result = self.prepare()
        self.assertEqual(result['status'], 'candidate_profiles_prepared')
        self.assertEqual(set(result['role_profiles']), set(profiles.ROLES))
        manifest_raw = (self.output / 'candidate-set.json').read_bytes()
        self.assertEqual(profiles.observed._pin(manifest_raw),
                         result['candidate_set_pin'])
        manifest = v.strict_json(manifest_raw)
        self.assertFalse(manifest['formal_permission'])
        for role in profiles.ROLES:
            row = result['role_profiles'][role]
            raw = Path(row['path']).read_bytes()
            self.assertEqual(profiles.observed._pin(raw), row['pin'])
            profile = v.strict_json(raw)
            self.assertEqual(profile['role'], role)
            self.assertEqual(profile['source_revision'], REVISION)
            self.assertEqual(profile['boundary'], profiles.BOUNDARIES[role])
            self.assertEqual(profile['reference']['dependency_pin'],
                             self.expected_role_pins[role]['dependencies'])
            self.assertEqual(profile['reference']['crosscheck_pin'],
                             self.expected_role_pins[role]['crosscheck'])
            self.assertEqual(profile['snapshots']['before'],
                             profile['snapshots']['after'])
            self.assertEqual(profile['observation_semantics'],
                             'two-point-before-and-after-with-additions-only')
            self.assertFalse(profile['runtime_closure_complete'])
        with self.assertRaises((ValueError, OSError)):
            self.prepare()

    def test_missing_external_audit_pin_rejected_before_output(self):
        pins = copy.deepcopy(self.expected_role_pins)
        del pins['audit']['stdout']
        with self.assertRaises((ValueError, KeyError)):
            self.prepare(pins=pins)
        self.assertFalse(self.output.exists())

    def test_changed_retained_bytes_rejected_before_output(self):
        path = self.reference / 'analysis' / 'dependencies.json'
        path.write_bytes(path.read_bytes() + b' ')
        with self.assertRaises((ValueError, OSError)):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_crosscheck_pin_and_role_result_must_agree(self):
        path = self.reference / 'producer' / 'dependency-crosscheck.json'
        check = v.strict_json(path.read_bytes())
        check['files'] += 1
        pins = copy.deepcopy(self.expected_role_pins)
        pins['producer']['crosscheck'] = save(path, check)
        with self.assertRaises(ValueError):
            self.prepare(pins=pins)
        self.assertFalse(self.output.exists())

    def test_wrong_top_or_role_pin_rejected(self):
        wrong_top = {'bytes': self.top_pin['bytes'], 'sha256': '0' * 64}
        with self.assertRaises((ValueError, OSError)):
            self.prepare(top_pin=wrong_top)
        pins = copy.deepcopy(self.expected_role_pins)
        pins['audit']['result'] = self.result_pins['analysis']
        with self.assertRaises((ValueError, OSError)):
            self.prepare(pins=pins)
        self.assertFalse(self.output.exists())

    def test_embedded_writer_result_must_match_external_pinned_child(self):
        publication_path = self.reference / 'publication' / 'result.json'
        publication = v.strict_json(publication_path.read_bytes())
        publication['writer']['status'] = 'failed'
        publication_pin = save(publication_path, publication)
        top_path = self.reference / 'result.json'
        top = v.strict_json(top_path.read_bytes())
        top['publication']['result_pin'] = publication_pin
        self.top_pin = save(top_path, top)
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_reference_output_overlap_rejected(self):
        with self.assertRaises((ValueError, OSError)):
            self.prepare(output=self.reference / 'profiles')
        self.assertFalse((self.reference / 'profiles').exists())

    def test_child_supervisor_runtime_disagreement_rejected(self):
        child = child_runtime()
        child['platform']['ubr'] += 1
        with self.assertRaises(ValueError):
            profiles._bind_runtime('analysis', child, runtime.EXPECTED)
        producer_runtime = copy.deepcopy(runtime.EXPECTED)
        producer_runtime['os_ubr'] += 1
        with self.assertRaises(ValueError):
            profiles._bind_runtime('producer', producer_runtime,
                                   runtime.EXPECTED)

    def test_producer_late_import_is_saved_as_second_observation(self):
        self._reference(producer_addition=True)
        self.prepare()
        producer = v.strict_json((self.output / 'producer.json').read_bytes())
        before, after = producer['snapshots']['before'], producer['snapshots']['after']
        self.assertEqual(len(after['files']) - len(before['files']), 2)
        self.assertEqual(set(after['modules']) - set(before['modules']),
                         {'encodings.cp437'})
        for role in profiles.ROLES[1:]:
            candidate = v.strict_json((self.output / (role + '.json')).read_bytes())
            self.assertEqual(candidate['snapshots']['before'],
                             candidate['snapshots']['after'])

    def test_changed_existing_dependency_rejected_even_with_new_external_pins(self):
        self._reference(producer_change=True)
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
