"""Critical ownership/recovery through fake Kernel; no native trial or ack."""
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_preformal_child_git_keeper as keeper

owner, tree = keeper.owner, keeper.tree
ACCOUNT = {'total_processes':1,'active_processes':0,'limit_terminated_processes':0}


class ChildGitKeeperTests(unittest.TestCase):
    def setUp(self):
        self.child=SimpleNamespace(stopped=False,owners={},active={0},finished=0)
        self.child.hold_owner=lambda lease,original:self.child.owners.__setitem__(lease,original)
        self.original=owner.UnreapedJob(11,22,33,{'phase':'git_reap'},
            extra_handles={'inherited_0':55,'inherited_1':56,'inherited_2':57})
        self.identity={'pid':44,'creation_time_100ns':111}
        self.identity['start_token']=keeper.v.canonical_sha256(self.identity)
        self.kernel=SimpleNamespace(TerminateJobObject=Mock(return_value=True),
            TerminateProcess=Mock(return_value=True),CloseHandle=Mock(return_value=True))
        self.kernel_mock=self.enterContext(patch.object(owner,'_kernel',return_value=self.kernel))
        self.wait=self.enterContext(patch.object(owner,'_wait_empty',return_value=(ACCOUNT,17)))
        self.creation=self.enterContext(patch.object(keeper,'_creation',return_value=self.identity))

    def make(self,original=None):
        return keeper.ChildGitKeeper(original or self.original,child=self.child,lease=0)

    def test_native_recovery_keeps_original_ledger_and_closes_every_original_extra(self):
        retained=self.make();result=retained.reconcile_once()
        self.assertIs(self.child.owners[0],self.original);self.assertTrue(self.child.stopped)
        self.creation.assert_called_once_with(22)
        self.assertEqual([c.args[0] for c in self.kernel.CloseHandle.call_args_list],[33,22,11,55,56,57])
        self.assertEqual(result['exit_code'],17);self.assertEqual(result['process_identity'],self.identity)
        self.assertFalse(result['parent_ack_authorized']);self.assertFalse(result['failure_raw_verified'])
        self.assertFalse(result['lease_completed']);self.assertEqual(self.child.active,{0})

    def test_live_job_or_missing_root_exit_prevents_every_close(self):
        retained=self.make()
        for account,code in [({**ACCOUNT,'active_processes':1},None),(ACCOUNT,None),(ACCOUNT,True)]:
            self.wait.return_value=(account,code)
            self.assertIsNone(retained.reconcile_once())
        self.kernel.CloseHandle.assert_not_called();self.assertIs(self.child.owners[0],self.original)

    def test_unassigned_suspended_root_is_stopped_by_original_process_handle(self):
        self.original.report['assignment_confirmed']=False
        self.assertIsNotNone(self.make().reconcile_once())
        self.kernel.TerminateJobObject.assert_called_once_with(11,0xE010)
        self.kernel.TerminateProcess.assert_called_once_with(22,0xE011)

    def test_stop_failure_still_checks_native_empty_exit_and_is_retained(self):
        failure=OSError('invented Job stop failure');self.kernel.TerminateJobObject.side_effect=failure
        retained=self.make();result=retained.reconcile_once()
        self.assertIs(retained.stop_error,failure);self.assertIsNotNone(result)
        self.assertEqual(result['call_status'],'failed');self.assertFalse(result['parent_ack_authorized'])

    def test_creation_read_failure_stops_without_closing_or_losing_original(self):
        failure=KeyboardInterrupt('invented creation read interruption');self.creation.side_effect=failure
        retained=self.make();self.assertIsNone(retained.reconcile_once())
        self.kernel.CloseHandle.assert_not_called();self.assertIs(retained.first_error,failure)
        self.assertIs(retained.original,self.original);self.assertTrue(self.child.stopped)

    def test_known_false_close_retries_only_that_original_without_reaping_again(self):
        responses=iter([True,False,True,True,True,True,True])
        self.kernel.CloseHandle.side_effect=lambda handle:next(responses)
        retained=self.make();self.assertIsNone(retained.reconcile_once())
        self.assertEqual(retained.remaining,{'process':22});self.assertFalse(retained.blocked)
        result=retained.reconcile_once();self.assertIsNotNone(result)
        self.assertEqual([c.args[0] for c in self.kernel.CloseHandle.call_args_list],[33,22,11,55,56,57,22])
        self.wait.assert_called_once();self.creation.assert_called_once()

    def test_unknown_close_interruption_retains_unattempted_handles_without_retry(self):
        failure=KeyboardInterrupt('invented close interrupted');self.kernel.CloseHandle.side_effect=[True,failure]
        retained=self.make();self.assertIsNone(retained.reconcile_once())
        self.assertIs(retained.close_owner.close_error,failure)
        self.assertEqual(retained.remaining,{'process':22,'job':11,'inherited_0':55,'inherited_1':56,'inherited_2':57})
        before=self.kernel.CloseHandle.call_count;self.assertIsNone(retained.reconcile_once())
        self.assertEqual(self.kernel.CloseHandle.call_count,before);self.assertTrue(retained.blocked)

    def test_preexisting_unclosed_owner_cannot_use_report_flags_for_auto_close(self):
        original=owner.UnclosedHandles({'job':11},{'all_assigned_processes_exit_confirmed':True})
        retained=self.make(original);self.assertIsNone(retained.reconcile_once())
        self.kernel_mock.assert_not_called();self.assertIs(self.child.owners[0],original)

    def test_marker_and_sleep_failures_keep_cached_native_observation_without_replay(self):
        retained=self.make();marker=OSError('invented marker IO failure');sleep=KeyboardInterrupt('invented sleep interruption')
        seen=[]
        def publish(observation):
            seen.append(observation)
            if len(seen)==1:raise marker
            observation['closed_handles'].clear()  # Callback gets a copy.
        with patch.object(keeper.time,'sleep',side_effect=sleep):result=retained.keep(on_observation=publish)
        self.assertIs(retained.callback_error,marker);self.assertIs(retained.sleep_error,sleep)
        self.wait.assert_called_once();self.assertEqual(self.kernel.CloseHandle.call_count,6)
        self.assertEqual(len(result['closed_handles']),6);self.assertEqual(self.child.active,{0})
        self.assertIs(self.child.owners[0],self.original);self.assertEqual(self.child.finished,0)

    def test_post_close_bookkeeping_failure_never_recloses_originals(self):
        failure=OSError('invented recording failure')
        class Records(dict):
            def update(self,*args,**kwargs):raise failure
        retained=self.make();retained.closed=Records()
        self.assertIsNone(retained.reconcile_once());self.assertIs(retained.first_error,failure)
        self.assertEqual(self.kernel.CloseHandle.call_count,6);self.assertTrue(retained.blocked)
        self.assertIsNone(retained.reconcile_once());self.assertEqual(self.kernel.CloseHandle.call_count,6)

    def test_extra_handle_cannot_override_original_job_or_create_unbounded_cleanup(self):
        self.original.extra_handles={'job':777}
        retained=self.make();self.assertIsNone(retained.reconcile_once())
        self.kernel_mock.assert_not_called();self.assertIs(retained.original,self.original)

    def test_ledger_io_failure_propagates_original_native_owner_with_keeper(self):
        failure=OSError('invented ledger failure');self.child.hold_owner=Mock(side_effect=failure)
        with self.assertRaises(owner.UnreapedJob) as caught:self.make()
        self.assertIs(caught.exception,self.original);self.assertIs(caught.exception.__cause__,failure)
        self.assertIs(self.original.child_keeper.ledger_error,failure);self.assertTrue(self.child.stopped)
        self.kernel_mock.assert_not_called()

    def test_reap_fallback_retains_owner_before_stop_and_cannot_mutate_hostile_original_error(self):
        class HostileError(OSError):
            def __setattr__(self,name,value):
                if name=='git_stop_error':raise AssertionError('diagnostic attribute lost owner')
                super().__setattr__(name,value)
        original=HostileError('invented reap failure');stop=KeyboardInterrupt('invented cleanup stop failure')
        kernel=SimpleNamespace(ResumeThread=Mock(return_value=1),TerminateJobObject=Mock(side_effect=stop),
            CloseHandle=Mock())
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(owner,'_kernel',return_value=kernel), \
             patch.object(owner,'_spawn_cli',return_value=(11,22,33,44)), \
             patch.object(owner,'_accounting',return_value=ACCOUNT), \
             patch.object(owner,'_root_exit',return_value=0), \
             patch.object(owner,'_wait_empty',side_effect=original), \
             patch.object(tree.direct,'_identity',return_value=self.identity):
            with self.assertRaises(owner.UnreapedJob) as caught:
                tree._execute(['fixture'],Path(temp),{'PATH':'fixture'},Path(temp),'head',10,
                              capture_quiescence=True)
        retained=caught.exception
        self.assertEqual((retained.job,retained.process,retained.thread),(11,22,33))
        self.assertIs(retained.original_error,original);self.assertIs(retained.stop_error,stop)
        self.assertIs(retained.__cause__,original);kernel.CloseHandle.assert_not_called()
