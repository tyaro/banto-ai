"""Normal/critical ownership split; native APIs/policy are fake, sinks are real."""
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_preformal_owned_git_job as git
from banto_ai import anomaly_v03_preformal_child_git_keeper as keepers
from tests import test_anomaly_v03_git_pipe_transport as prior


class GitPipeNormalCompletionTests(unittest.TestCase):
    def setUp(self):
        prior.GitPipeTransportTests.setUp(self)  # Only fixture setup; old tests are not discovered/run.
        self.child.active={0};self.child.owners={};self.child.finished=0
        self.child.hold_owner.side_effect=lambda lease,native:self.child.owners.__setitem__(lease,native)

    def normal(self):
        return git.GitPipeTransport(self.ad,kernel=self.kernel,repository=self.repository,
            policy=self.policy,stdin=self.stdin,child=self.child,stop_probe=self.stop,
            clock=self.clock,started_at=100.0,normal_completion=True)

    def ready(self):
        t=self.normal().start();self.assertEqual(t.step(),'pending')
        self.assertEqual(t.step(),'close_ready');return t

    def test_normal_actual_empty_exit_creation_close_keeps_channel_unstopped(self):
        t=self.ready();result=t.close_once()
        self.assertFalse(self.child.stopped);self.assertEqual(self.child.owners,{})
        self.assertEqual(self.child.active,{0});self.assertEqual(self.child.finished,0)
        self.child.hold_owner.assert_not_called();self.kernel.TerminateJobObject.assert_not_called()
        self.wait.assert_not_called();self.assertFalse(t.keeper.normal_promoted)
        self.assertEqual(self.ad.paths['stdout'].read_bytes(),b'abc')
        self.assertFalse(result['lease_completed']);self.assertFalse(result['parent_ack_authorized'])
        self.assertEqual(result['recovery']['call_status'],'failed')

    def test_normal_cached_close_rechecks_raw_without_native_or_ledger_replay(self):
        t=self.ready();t.close_once();before=list(self.closed);reads=self.kernel.ReadFile.call_count
        t.close_once();self.assertEqual(self.closed,before);self.assertEqual(self.kernel.ReadFile.call_count,reads)
        self.assertFalse(self.child.stopped);self.child.hold_owner.assert_not_called()

    def test_new_active_member_at_capture_promotes_exact_owner_without_success(self):
        t=self.normal().start();t.step()
        self.account.side_effect=[self.accounting,{**self.accounting,'active_processes':1}]
        with self.assertRaises(git.owner.UnreapedJob) as caught:t.step()
        self.assertIs(caught.exception,t.native);self.assertTrue(self.child.stopped)
        self.assertIs(self.child.owners[0],t.native);self.assertIs(t.error,t.keeper.first_error)
        self.assertIsNone(t.keeper.reaped);self.assertIsNone(t.result)
        self.kernel.TerminateJobObject.assert_not_called();self.wait.assert_not_called()

    def test_native_creation_interrupt_retains_same_error_and_critical_owner(self):
        t=self.normal().start();t.step();failure=KeyboardInterrupt('creation')
        with patch.object(keepers,'_creation',side_effect=failure):
            with self.assertRaises(git.owner.UnreapedJob):t.step()
        self.assertIs(t.error,failure);self.assertIs(t.keeper.first_error,failure)
        self.assertTrue(self.child.stopped);self.assertIs(self.child.owners[0],t.native)
        self.assertFalse(self.ad.streams['stdout'].closed);self.assertEqual(self.closed,[61,62,63,104,105])

    def test_promotion_ledger_interrupt_keeps_keeper_stop_latch_and_original_observation(self):
        t=self.normal().start();t.step();failure=KeyboardInterrupt('ledger')
        self.child.hold_owner.side_effect=failure
        self.account.side_effect=[self.accounting,{**self.accounting,'active_processes':1}]
        with self.assertRaises(git.owner.UnreapedJob):t.step()
        self.assertTrue(self.child.stopped);self.assertTrue(t.keeper.normal_promoted)
        self.assertIs(t.keeper.ledger_error,failure);self.assertIs(t.native.child_keeper,t.keeper)
        self.assertIs(t.error,t.keeper.first_error);self.child.hold_owner.assert_called_once()

    def test_output_limit_uses_original_stopping_keeper_even_with_normal_option(self):
        self.ad.limits['stdout.bin']=3;self.data[74]=b'abcdef';t=self.normal().start()
        with self.assertRaises(git.owner.UnreapedJob):t.step()
        self.assertFalse(t.keeper.normal_completion);self.assertTrue(self.child.stopped)
        self.assertIs(self.child.owners[0],t.native);self.wait.assert_called_once()
        self.assertEqual(self.ad.paths['stdout'].read_bytes(),b'abc');self.assertIsNone(t.result)

    def test_unknown_read_close_promotes_without_reclose_or_losing_original_handle(self):
        t=self.ready();failure=KeyboardInterrupt('Close');original=self.kernel.CloseHandle.side_effect
        self.kernel.CloseHandle.side_effect=lambda h:(_ for _ in ()).throw(failure) if h==74 else original(h)
        with self.assertRaises(git.owner.UnreapedJob):t.close_once()
        before=self.kernel.CloseHandle.call_count
        with self.assertRaises(git.owner.UnreapedJob):t.close_once()
        self.assertEqual(self.kernel.CloseHandle.call_count,before)
        self.assertTrue(self.child.stopped);self.assertIs(self.child.owners[0],t.native)
        self.assertIs(t.closer.error,failure);self.assertIsNone(t.keeper.completion)

    def test_known_false_core_close_becomes_critical_with_only_remaining_original(self):
        t=self.ready();self.close_false={22}
        with self.assertRaises(git.owner.UnreapedJob):t.close_once()
        self.assertTrue(self.child.stopped);self.assertIs(self.child.owners[0],t.native)
        self.assertEqual(t.keeper.remaining,{'process':22})
        self.assertIsNotNone(t.keeper.close_owner);self.assertIsNone(t.result)
        before=list(self.closed)
        with self.assertRaises(git.owner.UnreapedJob):t.close_once()
        self.assertEqual(self.closed,before)

    def test_changed_raw_after_normal_close_is_critical_without_native_replay(self):
        t=self.ready();t.close_once();before=list(self.closed)
        self.ad.paths['stdout'].write_bytes(b'abd')
        with self.assertRaises(git.owner.UnreapedJob):t.close_once()
        self.assertEqual(self.closed,before);self.assertTrue(self.child.stopped)
        self.assertIs(self.child.owners[0],t.native);self.assertEqual(self.child.active,{0})

    def test_nonbool_normal_option_is_retained_and_refused_before_policy_pipe_job(self):
        with self.assertRaises(git.owner.UnreapedJob) as caught:
            git.GitPipeTransport(self.ad,kernel=self.kernel,repository=self.repository,
                policy=self.policy,stdin=self.stdin,child=self.child,stop_probe=self.stop,
                clock=self.clock,started_at=100.0,normal_completion=1)
        self.assertIs(caught.exception.pipe_transport.stdin,self.stdin)
        self.policy_read.assert_not_called();self.kernel.CreatePipe.assert_not_called()
