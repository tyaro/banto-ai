"""An explicitly enabled native test of the isolated invented Job owner."""
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_preformal_job_tree_owner as owner


class JobOwnerContractTests(unittest.TestCase):
    def test_fixture_modes_and_limits_reject_without_launch(self):
        with patch.object(owner, '_kernel') as kernel:
            for mode, wall in (('unknown', 1), ('success', 0),
                               ('success', float('inf')), ('success', True)):
                with self.subTest(mode=mode, wall=wall), self.assertRaises(ValueError):
                    owner.run_fixture(Path('unused'), mode=mode, wall_seconds=wall)
            kernel.assert_not_called()

    def test_new_job_setup_failure_retains_job_handle_if_close_fails(self):
        class FaultyKernel:
            def CreateJobObjectW(self, *args): return 123
            def SetInformationJobObject(self, *args): return False
            def CloseHandle(self, handle):
                self.closed = handle
                return False
        kernel = FaultyKernel()
        with self.assertRaises(owner.UnclosedHandles) as caught:
            owner._new_job(kernel)
        self.assertEqual(kernel.closed, 123)
        self.assertEqual(caught.exception.handles, {'job': 123})
        self.assertEqual(caught.exception.report['status'], 'failed')

    def test_partial_spawn_retains_unreaped_native_handles(self):
        problem = owner.UnreapedJob(11, 22, 33,
                                   {'status': 'failed', 'phase': 'spawn'},
                                   extra_handles={'inherited_0': 44})
        limits = {'wall_seconds': 5, 'private_bytes': 1024**3,
                  'output_bytes': 1024**2}
        with tempfile.TemporaryDirectory(prefix='banto-job-failed-spawn-') as temp, \
             patch.object(owner, '_kernel', return_value=object()), \
             patch.object(owner, '_spawn_cli', side_effect=problem), \
             patch.object(owner.direct_supervisor.policy, 'validate_runtime'), \
             patch.object(owner.resources, 'require_start_resources',
                          return_value={}), \
             patch.object(owner.resources, 'free_resources',
                          return_value={}):
            with self.assertRaises(owner.UnreapedJob) as caught:
                owner.supervise_cli(
                    [sys.executable], owner.ROOT, Path(temp) / 'control',
                    limits, runtime_probe=lambda: {'fixture': True},
                    boundary=lambda: None, on_started=lambda _: None)
            self.assertIs(caught.exception, problem)
            self.assertEqual(caught.exception.extra_handles,
                             {'inherited_0': 44})

    def test_partial_spawn_close_failure_retains_all_handles(self):
        created = owner._ProcessInformation()
        close_error = owner.UnclosedHandles(
            {'job': 11}, {'status': 'failed', 'phase': 'spawn'})
        with patch.object(owner, '_close_owned', side_effect=close_error):
            with self.assertRaises(owner.UnclosedHandles) as caught:
                owner._reap_partial_spawn(
                    object(), 11, created, False, {'inherited_0': 44})
        self.assertEqual(caught.exception.handles,
                         {'job': 11, 'inherited_0': 44})


@unittest.skipUnless(os.name == 'nt' and sys.version_info[:2] == (3, 14) and
                     os.environ.get('BANTO_PREFORMAL_JOB_TREE_NATIVE') == '1',
                     'explicit 26H2 native Job fixture run')
class NativeJobOwnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='banto-invented-job-tree-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_success_waits_for_cli_and_grandchild(self):
        result = owner.run_fixture(self.root, mode='success', wall_seconds=8)
        self.assertEqual(result['status'], 'complete', result)
        self.assertEqual(result['root_exit_code'], 0)
        self.assertTrue(result['job_assignment_confirmed'])
        self.assertTrue(result['root_resumed'])
        self.assertGreaterEqual(result['job_accounting']['total_processes'], 2)
        self.assertEqual(result['job_accounting']['active_processes'], 0)
        self.assertTrue((self.root / 'grandchild-started.txt').is_file())
        self.assertTrue(result['grandchild_started_confirmed'])
        self.assertTrue(result['job_all_assigned_processes_exit_confirmed'])
        self.assertFalse(result['formal_permission'] or result['registered_data_read'])

    def test_timeout_terminates_cli_and_grandchild(self):
        result = owner.run_fixture(self.root, mode='timeout', wall_seconds=2)
        self.assertEqual(result['status'], 'failed', result)
        self.assertEqual(result['stop_reason'], 'wall_limit')
        self.assertTrue(result['job_all_assigned_processes_exit_confirmed'])
        self.assertGreaterEqual(result['job_accounting']['total_processes'], 2)
        self.assertEqual(result['job_accounting']['active_processes'], 0)
        self.assertLess(result['elapsed_seconds'], 10)
        self.assertTrue((self.root / 'grandchild-started.txt').is_file())

    def test_cli_abnormal_exit_terminates_remaining_grandchild(self):
        result = owner.run_fixture(self.root, mode='parent-fail', wall_seconds=8)
        self.assertEqual(result['status'], 'failed', result)
        self.assertEqual(result['stop_reason'], 'root_exit_nonzero')
        self.assertEqual(result['root_exit_code'], 17)
        self.assertTrue(result['job_all_assigned_processes_exit_confirmed'])
        self.assertGreaterEqual(result['job_accounting']['total_processes'], 2)
        self.assertEqual(result['job_accounting']['active_processes'], 0)
        self.assertLess(result['elapsed_seconds'], 10)
        self.assertTrue((self.root / 'grandchild-started.txt').is_file())

    def test_unconfirmed_accounting_retains_original_handles(self):
        actual = owner._wait_empty
        def unconfirmed(k, job, process, deadline):
            accounting, exit_code = actual(k, job, process, deadline)
            return {**accounting, 'active_processes': 1}, exit_code
        with patch.object(owner, '_wait_empty', side_effect=unconfirmed), \
             self.assertRaises(owner.UnreapedJob) as caught:
            owner.run_fixture(self.root, mode='success', wall_seconds=8)
        problem = caught.exception
        self.assertIsNotNone(problem.job)
        self.assertIsNotNone(problem.process)
        self.assertFalse(problem.report['job_all_assigned_processes_exit_confirmed'])
        # Test-only recovery: the real Job has emptied, then close held handles.
        k = owner._kernel()
        try:
            accounting, exit_code = actual(k, problem.job, problem.process,
                                            time.monotonic() + 5)
            self.assertEqual((accounting['active_processes'], exit_code), (0, 0))
        finally:
            for handle in (problem.thread, problem.process, problem.job):
                if handle is not None:
                    k.CloseHandle(handle)

    def test_missing_grandchild_start_evidence_cannot_complete(self):
        with patch.object(owner, '_grandchild_started', return_value=False):
            result = owner.run_fixture(self.root, mode='success', wall_seconds=8)
        self.assertEqual(result['status'], 'failed', result)
        self.assertEqual(result['stop_reason'], 'grandchild_start_unconfirmed')
        self.assertTrue(result['job_all_assigned_processes_exit_confirmed'])
        self.assertFalse(result['grandchild_started_confirmed'])

    def test_close_failure_retains_handle_and_tries_remaining_handles(self):
        kernel = owner._kernel()
        class CloseFailureKernel:
            def __init__(self): self.calls = []
            def __getattr__(self, name): return getattr(kernel, name)
            def CloseHandle(self, handle):
                self.calls.append(handle)
                if len(self.calls) == 1:
                    return False
                return kernel.CloseHandle(handle)
        faulty = CloseFailureKernel()
        with patch.object(owner, '_kernel', return_value=faulty), \
             self.assertRaises(owner.UnclosedHandles) as caught:
            owner.run_fixture(self.root, mode='success', wall_seconds=8)
        problem = caught.exception
        self.assertEqual(len(faulty.calls), 3)
        self.assertEqual(set(problem.handles), {'thread'})
        self.assertEqual(problem.report['status'], 'failed')
        self.assertEqual(problem.report['unclosed_handles'], ['thread'])
        try:
            self.assertTrue(problem.report['job_all_assigned_processes_exit_confirmed'])
        finally:
            self.assertTrue(kernel.CloseHandle(problem.handles['thread']))

    def _run_cli(self, mode, wall=8):
        argv = [sys.executable, '-B', str(owner.FIXTURE),
                'parent', mode, str(self.root)]
        limits = {'wall_seconds': wall, 'private_bytes': 512 * 1024**2,
                  'output_bytes': 1024**2}
        starts = []
        with patch.object(owner.direct_supervisor.policy, 'validate_runtime'), \
             patch.object(owner.resources, 'require_start_resources',
                          return_value={}), \
             patch.object(owner.resources, 'free_resources',
                          return_value={}):
            report = owner.supervise_cli(
                argv, owner.ROOT, self.root / 'control', limits,
                runtime_probe=lambda: {'fixture': True},
                boundary=lambda: None,
                on_started=lambda process: starts.append(process.pid))
        self.assertEqual(starts, [report['worker_pid']])
        return report

    def test_pinned_cli_supervisor_waits_for_job_members(self):
        report = self._run_cli('success')
        self.assertEqual(report['status'], 'complete', report)
        self.assertEqual(report['exit_code'], 0)
        self.assertEqual(report['job']['accounting']['active_processes'], 0)
        self.assertGreaterEqual(report['job']['accounting']['total_processes'], 2)
        self.assertTrue(report['job']['all_assigned_processes_exit_confirmed'])
        self.assertFalse(report['job']['individual_descendant_exit_codes_authenticated'])
        self.assertFalse(report['job']['whole_tree_resource_budget_measured'])
        self.assertFalse(report['formal_permission'])

    def test_pinned_cli_supervisor_abnormal_root_reaps_grandchild(self):
        report = self._run_cli('parent-fail')
        self.assertEqual(report['status'], 'failed', report)
        self.assertEqual(report['exit_code'], 17)
        self.assertEqual(report['stop_reason'], 'root_exit_nonzero')
        self.assertGreaterEqual(report['job']['accounting']['total_processes'], 2)
        self.assertEqual(report['job']['accounting']['active_processes'], 0)
        self.assertTrue(report['job']['all_assigned_processes_exit_confirmed'])

    def test_pinned_cli_supervisor_timeout_reaps_grandchild(self):
        report = self._run_cli('timeout', wall=1.5)
        self.assertEqual(report['status'], 'failed', report)
        self.assertEqual(report['stop_reason'], 'time_limit')
        self.assertEqual(report['job']['accounting']['active_processes'], 0)
        self.assertTrue(report['job']['all_assigned_processes_exit_confirmed'])


if __name__ == '__main__':
    unittest.main()
