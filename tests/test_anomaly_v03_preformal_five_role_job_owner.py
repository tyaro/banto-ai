"""Pinned five-role Job entry and its bounded native tree probe."""
from __future__ import annotations

import os
from contextlib import redirect_stdout
import io as text_io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_preformal_five_role_job_owner as owner
from banto_ai import anomaly_v03_preformal_five_role_parent_owned_git as parent_git
from banto_ai import anomaly_v03_preformal_owned_source_git_session as source_git


REVISION = 'a' * 40
PIN = owner.observed._pin(b'{}')


class FiveRoleJobOwnerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='banto-five-job-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.artifacts = self.root / 'artifacts'
        self.artifacts.mkdir()
        self.parent = self.artifacts / 'owner'
        self.join = self.artifacts / 'anomaly-v03-preformal-join-budget-fixture'
        self.source = {'revision': REVISION, 'pin': PIN}
        self.inputs = {'archive_path': str(self.join / 'invented-inputs.zip'),
                       'archive_pin': PIN, 'bound_pin': PIN,
                       'join_lineage': {}, 'candidate_set_pin': None,
                       'profile_pins': None}
        self.inner = {'inner_result_pin': PIN,
                      'resource_budget_pin': PIN,
                      'identities': {role: {'pid': index}
                                     for index, role in
                                     enumerate(owner.profiles.ROLES, 1)}}

    def _report(self, argv, status='complete'):
        return {'format': 'anomaly-v03-owned-process-monitor-v1',
                'limits': dict(owner.LIMITS), 'formal_permission': False,
                'performance_status': 'not_evaluated',
                'status': status, 'exit_code': 0 if status == 'complete' else 17,
                'worker_exit_confirmed': True, 'worker_pid': 123,
                'argv': list(argv), 'stop_reason': None if status == 'complete'
                else 'root_exit_nonzero', 'observation_errors': [],
                'runtime_before': {}, 'runtime_after': {},
                'output': PIN, 'stderr': {'bytes': 0, 'sha256': PIN['sha256']},
                'job': {'format': 'anomaly-v03-preformal-owned-cli-job-v1',
                        'assignment_confirmed': True, 'root_resumed': True,
                        'accounting': {'active_processes': 0,
                                       'total_processes': 6},
                        'all_assigned_processes_exit_confirmed': True,
                        'individual_descendant_exit_codes_authenticated': False,
                        'whole_tree_resource_budget_measured': False,
                        'memory': {'peak_job_memory_used_bytes': 2,
                                   'peak_process_memory_used_bytes': 1}}}

    def _call(self):
        return owner.run_owned(
            expected_mode='fixture', join_root=self.join,
            expected_join_receipt_pin=PIN, expected_revision=REVISION,
            receipt_parent=self.parent, receipt_name='attempt')

    def test_fixed_child_argv_and_retained_success_recheck(self):
        def supervise(argv, cwd, control, limits, *, runtime_probe,
                      boundary, on_started):
            self.assertEqual(cwd, self.root)
            self.assertEqual(control, self.parent / 'attempt' / 'job')
            self.assertEqual(argv[1:4], ['-I', '-S', '-B'])
            self.assertEqual(argv[5], owner.BOOTSTRAP)
            boundary()
            on_started(type('Process', (), {'pid': 123, '_handle': 456})())
            boundary()
            return self._report(argv)

        with patch.object(owner, 'ROOT', self.root), \
             patch.object(owner, '_source', return_value=self.source), \
             patch.object(owner, '_inputs', return_value=self.inputs), \
             patch.object(owner.job_owner, 'supervise_cli', side_effect=supervise), \
             patch.object(owner.observed, 'creation_observation',
                          return_value={'pid': 123, 'start_token': 'start'}), \
             patch.object(owner, '_inner', return_value=self.inner), \
             patch.object(owner.job_owner, 'valid_job_memory', return_value=True):
            result = self._call()
            verified = owner.verify_retained(result['check_directory'],
                                             result['receipt_pin'])
        self.assertEqual(result['status'], 'verified')
        self.assertEqual(verified['status'], 'verified_retained')
        self.assertTrue(result['all_job_processes_exit_confirmed'])
        self.assertFalse(result['job_outside_processes_authenticated'])
        self.assertFalse(result['individual_descendant_exit_codes_authenticated'])
        self.assertFalse(result['source_closure_complete'])
        self.assertFalse(result['runtime_closure_complete'])
        self.assertFalse(result['formal_permission'])
        self.assertFalse(result['retry_authorized'])
        with patch.object(owner, 'ROOT', self.root), \
             patch.object(owner, '_source', return_value=self.source), \
             patch.object(owner, '_inputs', return_value=self.inputs), \
             patch.object(owner, '_inner', return_value=self.inner), \
             patch.object(owner.job_owner, 'valid_job_memory', return_value=True):
            (self.parent / 'attempt' / 'supervision.json').write_bytes(b'{}')
            with self.assertRaises(ValueError):
                owner.verify_retained(result['check_directory'],
                                      result['receipt_pin'])

    def test_child_stdout_cannot_repin_changed_saved_top_result(self):
        target = self.parent / 'attempt'
        inner = target / 'five-role'
        (target / 'job').mkdir(parents=True)
        inner.mkdir()
        child = {'status': 'verified', 'result_pin': PIN,
                 'check_directory': str(inner)}
        stdout = owner.io.json_bytes(child)
        (target / 'job' / 'report.json').write_bytes(stdout)
        (inner / 'result.json').write_bytes(b'{"changed":true}\n')
        report = {'output': owner.observed._pin(stdout)}
        with self.assertRaises(ValueError):
            owner._inner(target, report, {'pid': 123},
                         {'source_revision': REVISION,
                          'candidate_set_pin': None})

    def test_all_five_saved_profiles_bind_and_wrong_pin_rejects(self):
        target = self.parent / 'attempt'
        inner = target / 'five-role'
        identities = {role: {'pid': index, 'start_token': str(index),
                             'invocation_id': role, 'evidence_pin': PIN}
                      for index, role in enumerate(owner.profiles.ROLES, 1)}
        child = {'status': 'verified', 'result_pin': PIN,
                 'check_directory': str(inner)}
        top = {'format': owner.chain.FORMAT, 'status': 'verified',
               'scope': 'invented-26h2-five-owned-role-trial',
               'platform_contract_status': 'proposal-not-accepted',
               'stage': 'complete', 'source_revision': REVISION,
               'combined_resource_budget_measured': True,
               'combined_resource_budget_passed': True,
               'five_role_budget_closure_passed': True,
               'resource_budget_scope':
                   'one sampled outer root plus shared cooperative child stop',
               'owned_producer_join_executed': True,
               'source_closure_complete': False,
               'runtime_closure_complete': False,
               'formal_permission': False,
               'registered_data_read': False,
               'real_producer_executed': False,
               'registered_saved_reader_used': False,
               'new_evaluations': 0,
               'profile_required': True,
               'before_work_profile_enforcement': True,
               'candidate_profile_set_pin': PIN,
               'resource_budget_pin': PIN,
               'publication': {'status': 'verified', 'result_pin': PIN,
                               'publication_status': 'completed',
                               'reader_status': 'completed'},
               'producer': {'status': 'verified', 'result_pin': PIN},
               'analysis': {'status': 'verified', 'result_pin': PIN},
               'audit': {'status': 'verified', 'result_pin': PIN},
               'identities': identities}
        top.update(owner.chain.four.publication.CLOSED)
        publication = {'status': 'verified',
                       'publication_status': 'completed',
                       'reader_status': 'completed'}
        role_results = {
            role: {'status': 'verified', 'worker_exit_confirmed': True,
                   'worker_pid': index, 'dependency_profile_pin': PIN,
                   'stdout_pin': PIN,
                   'before_work_profile_enforcement': True}
            for index, role in enumerate(owner.profiles.ROLES, 1)}
        publication.update(writer=role_results['writer'],
                           reader=role_results['reader'])
        budget = {'format': owner.chain.chain_budget.FORMAT,
                   'scope': 'invented-preformal-five-role-engineering-fixture',
                   'root': str(inner),
                   'limits': dict(owner.chain.chain_budget.DEFAULTS),
                   'publication_roots':
                       [str(inner / 'publication' / 'published')],
                   'sampler_exit_confirmed': True,
                   'stop_reason': None, 'observation_error': None,
                   'formal_permission': False, 'registered_data_read': False,
                   'independent_s6_complete': False,
                   'formal_50000_draw_budget_measured': False,
                  'passed': True, 'caller_reported_all_five_exits': True,
                  'caller_reported_roles': {
                      role: {'status': 'verified',
                             'worker_exit_confirmed': True,
                             'worker_pid': role_results[role]['worker_pid'],
                             'result_pin': (PIN if role in
                                            ('producer', 'analysis', 'audit') else
                                            owner.observed._pin(owner.io.json_bytes(
                                                role_results[role])))}
                      for role in owner.profiles.ROLES}}

        def read(path, pin, maximum):
            path = Path(path)
            if path == inner / 'result.json':
                return owner.io.json_bytes(top)
            if path == inner / 'resource-budget.json':
                return owner.io.json_bytes(budget)
            if path == inner / 'publication' / 'result.json':
                return owner.io.json_bytes(publication)
            for role, role_path in owner.profiles.ROLE_PATHS.items():
                role_root = inner / role_path
                if path == role_root / 'result.json':
                    return owner.io.json_bytes(role_results[role])
                if path == role_root / 'evidence.json':
                    return owner.io.json_bytes(
                        {'process': {'parent_pid': 123}})
            if path == inner / 'producer' / 'worker' / 'report.json':
                return owner.io.json_bytes(
                    {'process': {'parent_pid': 123}})
            return owner.io.json_bytes(child)

        invocation = {'source_revision': REVISION,
                      'candidate_set_pin': PIN,
                      'profile_pins': {role: PIN for role in owner.profiles.ROLES}}
        with patch.object(owner, '_pinned', side_effect=read), \
             patch.object(owner.chain, '_producer_identity',
                          return_value=identities['producer']), \
             patch.object(owner.chain.four, '_role_identity',
                          side_effect=lambda path, role, pin: identities[role]):
            verified = owner._inner(
                target, {'output': PIN}, {'pid': 123}, invocation)
            self.assertEqual(verified['identities'], identities)
            for key, bad in (('format', 'wrong'), ('scope', 'wrong'),
                             ('root', 'wrong'), ('sampler_exit_confirmed', False),
                             ('formal_50000_draw_budget_measured', True),
                             ('independent_s6_complete', True)):
                original = budget[key]
                budget[key] = bad
                with self.subTest(budget_field=key), \
                     self.assertRaisesRegex(ValueError,
                                            'five-role saved shared budget'):
                    owner._inner(target, {'output': PIN}, {'pid': 123}, invocation)
                budget[key] = original
            budget['limits']['wall_seconds'] += 1
            with self.assertRaisesRegex(ValueError, 'five-role saved shared budget'):
                owner._inner(target, {'output': PIN}, {'pid': 123}, invocation)
            budget['limits']['wall_seconds'] -= 1
            budget['caller_reported_roles']['audit']['worker_pid'] += 1
            with self.assertRaisesRegex(ValueError, 'audit saved budget/result binding'):
                owner._inner(target, {'output': PIN}, {'pid': 123}, invocation)
            budget['caller_reported_roles']['audit']['worker_pid'] -= 1
            budget['caller_reported_roles']['analysis']['result_pin'] = \
                owner.observed._pin(b'wrong-budget')
            with self.assertRaisesRegex(ValueError,
                                        'analysis saved budget/result binding'):
                owner._inner(target, {'output': PIN}, {'pid': 123}, invocation)
            budget['caller_reported_roles']['analysis']['result_pin'] = PIN
            top['promotion_allowed'] = True
            with self.assertRaisesRegex(ValueError, 'closed scope'):
                owner._inner(target, {'output': PIN}, {'pid': 123}, invocation)
            top['promotion_allowed'] = False
            top['new_evaluations'] = False
            with self.assertRaisesRegex(ValueError, 'saved top scope'):
                owner._inner(target, {'output': PIN}, {'pid': 123}, invocation)
            top['new_evaluations'] = 0
            top['analysis']['status'] = 'failed'
            with self.assertRaisesRegex(ValueError,
                                        'analysis saved top/result status'):
                owner._inner(target, {'output': PIN}, {'pid': 123}, invocation)
            top['analysis']['status'] = 'verified'
            role_results['producer']['dependency_profile_pin'] = \
                owner.observed._pin(b'wrong')
            with self.assertRaisesRegex(ValueError, 'producer profile pin'):
                owner._inner(target, {'output': PIN}, {'pid': 123}, invocation)

    def test_join_preflight_failure_retains_terminal_receipt_without_launch(self):
        with patch.object(owner, 'ROOT', self.root), \
             patch.object(owner, '_source', return_value=self.source), \
             patch.object(owner, '_inputs', side_effect=ValueError('join pin')), \
             patch.object(owner.job_owner, 'supervise_cli') as supervise:
            result = self._call()
        supervise.assert_not_called()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['reason'], 'preflight_rejected')
        self.assertFalse(result['retry_authorized'])
        self.assertFalse(result['next_stage_authorized'])
        self.assertTrue((self.parent / 'attempt' / 'receipt.json').is_file())
        with patch.object(owner, 'ROOT', self.root), \
             self.assertRaises(FileExistsError):
            self._call()

    def test_root_failure_rejects_inner_result_even_with_empty_job(self):
        def supervise(argv, cwd, control, limits, *, runtime_probe,
                      boundary, on_started):
            on_started(type('Process', (), {'pid': 123, '_handle': 456})())
            return self._report(argv, status='failed')

        with patch.object(owner, 'ROOT', self.root), \
             patch.object(owner, '_source', return_value=self.source), \
             patch.object(owner, '_inputs', return_value=self.inputs), \
             patch.object(owner.job_owner, 'supervise_cli', side_effect=supervise), \
             patch.object(owner.observed, 'creation_observation',
                          return_value={'pid': 123, 'start_token': 'start'}), \
             patch.object(owner, '_inner', side_effect=AssertionError('inner must not verify')):
            result = self._call()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['reason'], 'job_failed')
        self.assertTrue(result['all_job_processes_exit_confirmed'])
        self.assertFalse(result['next_stage_authorized'])

    def test_supervision_report_requires_format_limits_and_scope(self):
        argv = [sys.executable, '-I', '-S', '-B', '-c', owner.BOOTSTRAP,
                str(owner.ROOT / 'src'), 'invocation.json', '2', PIN['sha256']]
        report = self._report(argv)
        with patch.object(owner.job_owner, 'valid_job_memory', return_value=True):
            owner._job_complete(report, argv, {'pid': 123})
            for key in ('format', 'limits', 'formal_permission',
                         'performance_status'):
                changed = dict(report)
                changed.pop(key)
                with self.subTest(key=key), self.assertRaises((KeyError, ValueError)):
                    owner._job_complete(changed, argv, {'pid': 123})
            changed = {**report, 'limits': {**report['limits'],
                                           'wall_seconds': 301}}
            with self.assertRaisesRegex(ValueError, 'five-role CLI or Job'):
                owner._job_complete(changed, argv, {'pid': 123})

    def test_unreaped_job_keeps_original_owner_and_failure_receipt(self):
        problem = owner.job_owner.UnreapedJob(
            1, 2, 3, {'status': 'failed', 'phase': 'reap',
                      'root_pid': 123, 'root_exit_code': None,
                      'job_accounting': {'total_processes': 6,
                                         'active_processes': 1,
                                         'limit_terminated_processes': 0},
                      'formal_permission': False})
        def supervise(argv, cwd, control, limits, *, runtime_probe,
                      boundary, on_started):
            on_started(type('Process', (), {'pid': 123, '_handle': 456})())
            raise problem
        with patch.object(owner, 'ROOT', self.root), \
             patch.object(owner, '_source', return_value=self.source), \
             patch.object(owner, '_inputs', return_value=self.inputs), \
             patch.object(owner.job_owner, 'supervise_cli', side_effect=supervise), \
             patch.object(owner.observed, 'creation_observation',
                          return_value={'pid': 123, 'start_token': 'start'}):
            with self.assertRaises(owner.job_owner.UnreapedJob) as caught:
                self._call()
        self.assertIs(caught.exception, problem)
        saved = owner.v.strict_json((self.parent / 'attempt' / 'receipt.json').read_bytes())
        self.assertEqual(saved['reason'], 'job_reconciliation_required')
        self.assertFalse(saved['all_job_processes_exit_confirmed'])
        self.assertFalse(saved['retry_authorized'])
        self.assertEqual(saved['launch_pin'],
                         owner.observed._pin(owner.io.json_bytes(saved['launch'])))
        self.assertEqual(saved['job_exception_report']['phase'], 'reap')
        self.assertEqual(saved['job_exception_report']['job_accounting'][
            'active_processes'], 1)

    def test_receipt_io_failure_does_not_replace_unreaped_job_owner(self):
        problem = owner.job_owner.UnreapedJob(1, 2, 3, {'status': 'failed'})
        with patch.object(owner, 'ROOT', self.root), \
             patch.object(owner, '_source', return_value=self.source), \
             patch.object(owner, '_inputs', return_value=self.inputs), \
             patch.object(owner.job_owner, 'supervise_cli', side_effect=problem), \
             patch.object(owner, '_receipt', side_effect=OSError('receipt IO')):
            with self.assertRaises(owner.job_owner.UnreapedJob) as caught:
                self._call()
        self.assertIs(caught.exception, problem)
        self.assertIsInstance(problem.outer_receipt_error, OSError)

    def test_unclosed_handles_keep_safe_exception_summary(self):
        problem = owner.job_owner.UnclosedHandles(
            {'job': 7}, {'status': 'failed', 'phase': 'close',
                          'formal_permission': False,
                          'job': {'accounting': {'total_processes': 6,
                                                 'active_processes': 0,
                                                 'limit_terminated_processes': 0}},
                          'unsafe_object': object()})
        with patch.object(owner, 'ROOT', self.root), \
             patch.object(owner, '_source', return_value=self.source), \
             patch.object(owner, '_inputs', return_value=self.inputs), \
             patch.object(owner.job_owner, 'supervise_cli', side_effect=problem):
            with self.assertRaises(owner.job_owner.UnclosedHandles) as caught:
                self._call()
        self.assertIs(caught.exception, problem)
        saved = owner.v.strict_json((self.parent / 'attempt' / 'receipt.json').read_bytes())
        self.assertEqual(saved['job_exception_report']['phase'], 'close')
        self.assertEqual(saved['job_exception_report']['job_accounting'][
            'total_processes'], 6)
        self.assertNotIn('unsafe_object', saved['job_exception_report'])
        self.assertIsNone(saved['launch_pin'])


@unittest.skipUnless(os.name == 'nt', 'Windows native Job probe')
class FiveRoleJobNativeProbeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='banto-five-job-native-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.probe = (Path(__file__).resolve().parent / 'fixtures' /
                      'anomaly_v03_five_role_job_probe.py')

    def _run(self, mode):
        argv = [sys.executable, '-B', str(self.probe),
                'parent', mode, str(self.root)]
        limits = {'wall_seconds': 8, 'private_bytes': 512 * 1024**2,
                  'output_bytes': 1024**2}
        starts = []
        with patch.object(owner.job_owner.direct_supervisor.policy,
                          'validate_runtime'), \
             patch.object(owner.job_owner.resources,
                          'require_start_resources', return_value={}), \
             patch.object(owner.job_owner.resources,
                          'free_resources', return_value={}):
            report = owner.job_owner.supervise_cli(
                argv, owner.ROOT, self.root / ('control-' + mode), limits,
                runtime_probe=lambda: {'fixture': True},
                boundary=lambda: None,
                on_started=lambda process: starts.append(process.pid))
        self.assertEqual(starts, [report['worker_pid']])
        return argv, report

    def test_six_job_members_complete_and_owner_accepts(self):
        argv, report = self._run('success')
        self.assertGreaterEqual(report['job']['accounting']['total_processes'], 6)
        self.assertEqual(report['job']['accounting']['active_processes'], 0)
        # The small probe uses a test command and short limits. Bind its real
        # Job accounting to the fixed owner command metadata checked separately.
        fixed = [sys.executable, '-I', '-S', '-B', '-c', owner.BOOTSTRAP,
                 str(owner.ROOT / 'src'), 'invocation.json', '2', PIN['sha256']]
        adapted = {**report, 'argv': fixed, 'limits': dict(owner.LIMITS)}
        owner._job_complete(adapted, fixed, {'pid': report['worker_pid']})

    def test_root_failure_stops_five_children_and_owner_rejects(self):
        argv, report = self._run('parent-fail')
        self.assertEqual(report['job']['accounting']['active_processes'], 0)
        self.assertTrue(report['job']['all_assigned_processes_exit_confirmed'])
        with self.assertRaises(ValueError):
            owner._job_complete(report, argv, {'pid': report['worker_pid']})


class ChildOwnedGitRoutingTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name).resolve()
        self.target = self.root / 'artifacts' / 'attempt'
        self.target.mkdir(parents=True)
        self.invocation = {
            'format': owner.INVOCATION, 'source_revision': REVISION,
            'join_root': str(self.root / 'artifacts' / 'join'),
            'join_receipt_pin': PIN, 'archive_pin': PIN, 'bound_pin': PIN,
            'candidate_set_path': None, 'candidate_set_pin': None,
            'profile_pins': None, 'result_root': str(self.target / 'five-role')}

    def test_child_source_and_chain_boundaries_route_exactly_26_calls(self):
        files = {}
        for name in (*owner.chain.SOURCES, owner.SOURCE):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            raw = name.encode() + b'\n'
            path.write_bytes(raw)
            files[name] = raw
        calls = []

        class Reader:
            def run(self, **kwargs):
                calls.append({'index': len(calls), **kwargs,
                              'source_path': kwargs.get('source_path'),
                              'expected_output_pin': kwargs.get('expected_output_pin'),
                              'call_status': 'verified', 'receipt_pin': PIN,
                              'reason': None, 'error_type': None})
                operation = kwargs['operation']
                return ((REVISION + '\n').encode() if operation == 'head' else
                        b'' if operation == 'status' else files[kwargs['source_path']])

        reader = Reader()
        response = {'status': 'verified', 'result_pin': PIN,
                    'check_directory': str(self.target / 'five-role')}

        def chain(**kwargs):
            self.assertIs(kwargs['git_reader'], reader)
            for index in range(2):
                owner.chain._git_sources(
                    REVISION, git_reader=reader,
                    git_call_prefix=f'child-chain-source-{index}-')
            return response

        inputs = {'archive_pin': PIN, 'bound_pin': PIN, 'profile_pins': None}
        with patch.object(owner, 'ROOT', self.root), \
             patch.object(owner.chain, 'ROOT', self.root), \
             patch.object(owner, '_inputs', return_value=inputs), \
             patch.object(owner, '_invocation', return_value=self.invocation), \
             patch.object(owner.chain, 'run_chain', side_effect=chain), \
             patch.object(owner.subprocess, 'check_output',
                          side_effect=AssertionError('bare Git invoked')):
            result = owner._run_child(self.target / 'invocation.json', PIN,
                                      self.invocation, git_reader=reader)
        self.assertEqual(result, response)
        source = {'orchestrator_selected': {
            name: owner.observed._pin(files[name]) for name in owner.chain.SOURCES},
            'owner': owner.observed._pin(files[owner.SOURCE])}
        parent_git._child_calls(calls, source)
        self.assertEqual(len(calls), 26)
        calls[8]['call_id'] = 'wrong-boundary'
        with self.assertRaisesRegex(ValueError, 'call order'):
            parent_git._child_calls(calls, source)

    def test_child_success_is_printed_only_after_manifest_completion(self):
        invocation = {**self.invocation, 'format': owner.OWNED_GIT_INVOCATION,
                      'child_git_policy_path': str(self.root / 'artifacts' / 'policy.json'),
                      'child_git_policy_pin': PIN}
        for count in (26, 25):
            output = text_io.StringIO()
            entered = []
            case = self

            class Session:
                manifest_result = None

                def __init__(self, **kwargs):
                    case.assertEqual(kwargs['receipt_root'], case.target / 'child-git')
                    case.assertEqual(kwargs['expected_policy_pin'], PIN)

                def __enter__(self):
                    entered.append(self)
                    return self

                def __exit__(self, *args):
                    case.assertEqual(output.getvalue(), '')
                    self.manifest_result = {'status': 'verified', 'call_count': count}

            def run(path, pin, value, *, git_reader):
                self.assertIs(git_reader, entered[0])
                return {'status': 'verified', 'result_pin': PIN,
                        'check_directory': invocation['result_root']}

            with self.subTest(count=count), patch.object(owner, 'ROOT', self.root), \
                 patch.object(owner, '_invocation', return_value=invocation), \
                 patch.object(source_git, 'OwnedSourceGitSession', Session), \
                 patch.object(owner, '_run_child', side_effect=run), \
                 redirect_stdout(output):
                argv = [str(self.target / 'invocation.json'), str(PIN['bytes']), PIN['sha256']]
                if count == 26:
                    self.assertEqual(owner.child_main(argv), 0)
                else:
                    with self.assertRaisesRegex(ValueError, 'calls incomplete'):
                        owner.child_main(argv)
            self.assertEqual(bool(output.getvalue()), count == 26)

    def test_child_policy_rejects_profile_or_join_overlap_before_policy_read(self):
        invocation = {**self.invocation,
                      'child_git_policy_path': str(self.root / 'artifacts' / 'external' / 'policy.json'),
                      'child_git_policy_pin': PIN}
        for changed in (
                {**invocation, 'candidate_set_path': 'candidate.json', 'candidate_set_pin': PIN},
                {**invocation, 'child_git_policy_path':
                 str(Path(invocation['join_root']) / 'policy.json')}):
            with patch.object(source_git, '_policy',
                              side_effect=AssertionError('policy read')):
                with self.assertRaisesRegex(ValueError, 'excludes candidate'):
                    owner._child_policy(changed, self.target)

    def test_producer_manifest_finishes_before_success_and_failure_has_no_stdout(self):
        invocation = {**self.invocation, 'format': owner.OWNED_PRODUCER_INVOCATION,
                      'child_git_policy_path': str(self.root / 'artifacts' / 'policy.json'),
                      'child_git_policy_pin': PIN}
        for version, failed_phase in (
                (owner.OWNED_PRODUCER_INVOCATION, None),
                (owner.OWNED_PRODUCER_INVOCATION, owner.PRODUCER_GIT_PHASE),
                (owner.OWNED_ANALYSIS_INVOCATION, None),
                (owner.OWNED_ANALYSIS_INVOCATION, owner.ANALYSIS_GIT_PHASE),
                *((owner.OWNED_AUDIT_INVOCATION, phase) for phase in
                  (None, owner.AUDIT_GIT_PHASE, owner.ANALYSIS_GIT_PHASE,
                   owner.PRODUCER_GIT_PHASE, owner.CHILD_GIT_PHASE)),
                *((owner.OWNED_WRITER_INVOCATION, phase) for phase in
                  (None, owner.WRITER_GIT_PHASE, owner.AUDIT_GIT_PHASE,
                   owner.ANALYSIS_GIT_PHASE, owner.PRODUCER_GIT_PHASE, owner.CHILD_GIT_PHASE))):
            invocation['format'] = version
            output = text_io.StringIO()
            readers = {}
            events = []
            case = self

            class Session:
                def __init__(self, **kwargs):
                    self.phase = kwargs['phase']
                    self.manifest_result = None
                    roots = {owner.CHILD_GIT_PHASE: 'child-git',
                             owner.PRODUCER_GIT_PHASE: 'producer-git',
                             owner.ANALYSIS_GIT_PHASE: 'analysis-git',
                             owner.AUDIT_GIT_PHASE: 'audit-git',
                             owner.WRITER_GIT_PHASE: 'writer-git'}
                    case.assertEqual(kwargs['receipt_root'], case.target / roots[self.phase])

                def __enter__(self):
                    readers[self.phase] = self
                    return self

                def __exit__(self, *args):
                    case.assertEqual(output.getvalue(), '')
                    events.append(self.phase)
                    self.manifest_result = {
                        'status': 'failed' if self.phase == failed_phase else 'verified',
                        'call_count': 26 if self.phase == owner.CHILD_GIT_PHASE else 88}

            def run(path, pin, value, *, git_reader, producer_git_reader,
                    analysis_git_reader=None, audit_git_reader=None, writer_git_reader=None):
                self.assertIs(git_reader, readers[owner.CHILD_GIT_PHASE])
                self.assertIs(producer_git_reader, readers[owner.PRODUCER_GIT_PHASE])
                if version in (owner.OWNED_ANALYSIS_INVOCATION, owner.OWNED_AUDIT_INVOCATION,
                               owner.OWNED_WRITER_INVOCATION):
                    self.assertIs(analysis_git_reader, readers[owner.ANALYSIS_GIT_PHASE])
                else:
                    self.assertIsNone(analysis_git_reader)
                if version in (owner.OWNED_AUDIT_INVOCATION, owner.OWNED_WRITER_INVOCATION):
                    self.assertIs(audit_git_reader, readers[owner.AUDIT_GIT_PHASE])
                else:
                    self.assertIsNone(audit_git_reader)
                if version == owner.OWNED_WRITER_INVOCATION:
                    self.assertIs(writer_git_reader, readers[owner.WRITER_GIT_PHASE])
                else:
                    self.assertIsNone(writer_git_reader)
                return {'status': 'verified', 'result_pin': PIN,
                        'check_directory': invocation['result_root']}

            with self.subTest(version=version, failed_phase=failed_phase), patch.object(owner, 'ROOT', self.root), \
                 patch.object(owner, '_invocation', return_value=invocation), \
                 patch.object(source_git, 'OwnedSourceGitSession', Session), \
                 patch.object(owner, '_run_child', side_effect=run), redirect_stdout(output):
                argv = [str(self.target / 'invocation.json'), str(PIN['bytes']), PIN['sha256']]
                if failed_phase is None:
                    self.assertEqual(owner.child_main(argv), 0)
                else:
                    with self.assertRaisesRegex(ValueError, 'owned .* Git calls incomplete'):
                        owner.child_main(argv)
            expected_events = [owner.PRODUCER_GIT_PHASE, owner.CHILD_GIT_PHASE]
            if version in (owner.OWNED_ANALYSIS_INVOCATION, owner.OWNED_AUDIT_INVOCATION,
                           owner.OWNED_WRITER_INVOCATION):
                expected_events.insert(0, owner.ANALYSIS_GIT_PHASE)
            if version in (owner.OWNED_AUDIT_INVOCATION, owner.OWNED_WRITER_INVOCATION):
                expected_events.insert(0, owner.AUDIT_GIT_PHASE)
            if version == owner.OWNED_WRITER_INVOCATION:
                expected_events.insert(0, owner.WRITER_GIT_PHASE)
            self.assertEqual(events, expected_events)
            self.assertEqual(bool(output.getvalue()), failed_phase is None)


if __name__ == '__main__':
    unittest.main()
