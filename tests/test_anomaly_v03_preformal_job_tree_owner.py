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


if __name__ == '__main__':
    unittest.main()
