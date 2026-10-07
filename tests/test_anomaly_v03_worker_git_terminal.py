"""Entry terminal protocol with fake executor/native facts, no actual worker."""
from pathlib import Path
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_preformal_worker_git_terminal as terminal
from tests import test_anomaly_v03_worker_git_actor as fixtures

tree = terminal.tree


class WorkerGitTerminalTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.WorkerGitActorTests('test_exact_private_job_arguments_shared_probe_raw_archive_then_lease_and_cleanup')
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.f=self.fixture.f

    def configure(self,calls=1):
        self.a=self.fixture.configure(calls);return self.a

    def call(self,phase='pre',code=0):
        result,target=self.fixture.receipt(self.f.child.finished,code)
        with patch.object(tree,'run_owned',side_effect=self.fixture.executor(result,target)):
            return self.fixture.call(phase)

    def fence(self):
        raw,pin=self.a.writer.manifest()
        saved=terminal.actors.archive.SavedWorkerGitArchive(endpoint=self.f.parent,
            manifest_raw=raw,manifest_pin=pin,inventory_raw=self.a.inventory_raw,
            inventory_pin=self.a.inventory_pin,checkpoint=self.fixture.checkpoint)
        self.f.parent.verify_quiescent=saved.verifier.verify
        return self.f.parent.fence(self.f.process)

    def test_full_verified_call_inventory_then_guarded_ack_and_parent_raw_verification(self):
        a=self.configure()
        self.assertEqual(terminal.run_guarded(a,lambda:self.call()),self.f.revision.encode()+b'\n')
        self.assertTrue(self.fence());self.assertTrue(self.f.child.stopped)
        self.assertIsNone(a.terminal_guard.original_error);self.assertFalse(a.inflight.exists())

    def test_zero_job_success_flags_and_missing_marker_do_not_grant_ack(self):
        a=self.configure()
        with patch.object(tree,'run_owned') as run,self.assertRaises(ValueError):
            terminal.run_guarded(a,lambda:{'success':True,'jobs':0})
        run.assert_not_called();self.assertEqual(self.f.child.finished,0)
        self.assertFalse((self.f.child.root/'ack.json').exists())
        self.assertFalse((self.f.child.root/'git-proof.json').exists())
        self.assertIsNotNone(a.terminal_guard.ack_error)

    def test_partial_success_prefix_keeps_exact_body_error_and_refuses_ack(self):
        a=self.configure(2);failure=ValueError('invented stop before post phase')
        def work():self.call();raise failure
        with self.assertRaises(ValueError) as caught:terminal.run_guarded(a,work)
        self.assertIs(caught.exception,failure);self.assertEqual(self.f.child.finished,1)
        self.assertIs(a.terminal_guard.original_error,failure)
        self.assertIsNotNone(a.terminal_guard.ack_error);self.assertFalse((self.f.child.root/'ack.json').exists())
        self.assertEqual(a.saved.statuses,['verified']);self.assertFalse(a.inflight.exists())

    def test_verified_failed_prefix_ack_means_quiescence_not_business_success(self):
        a=self.configure(2)
        with self.assertRaises(tree.owner.resources.ResourceStop) as caught:
            terminal.run_guarded(a,lambda:self.call(code=17))
        self.assertIs(caught.exception,a.error);self.assertTrue(self.fence())
        proof=tree.v.strict_json((self.f.child.root/'git-proof.json').read_bytes())
        self.assertEqual(proof['terminal'],'failed');self.assertIs(proof['formal_permission'],False)
        self.assertTrue((a.inflight/'stdout.bin').exists());self.assertEqual(self.f.child.finished,1)

    def test_swallowed_critical_exception_is_recovered_kept_and_reraised_before_worker_success(self):
        a=self.configure(2);self.fixture.recovery_patches();kept=[]
        def work():kept.append(self.fixture.critical_call());return {'success':True}
        with self.assertRaises(tree.owner.UnreapedJob) as caught:terminal.run_guarded(a,work)
        self.assertIs(caught.exception,kept[0]);self.assertIs(a.terminal_guard.original_error,kept[0])
        self.assertTrue(self.fence());self.assertEqual(self.fixture.kernel.CloseHandle.call_count,4)
        self.assertEqual(a.saved.statuses,['failed']);self.assertTrue((a.inflight/'stderr.bin').exists())

    def test_keeper_and_sleep_interruptions_keep_python_until_same_original_recovery(self):
        a=self.configure();original=self.fixture.critical_call();self.fixture.recovery_patches()
        guard=terminal.ActorTerminal(a);failure=OSError('invented keeper call IO');keep=a.keep_owner
        attempted=0;sleep_error=KeyboardInterrupt('invented sleep interruption')
        def then_recover():
            nonlocal attempted
            attempted+=1
            if attempted==1:raise failure
            return keep()
        with patch.object(a,'keep_owner',side_effect=then_recover) as retry:
            with patch.object(terminal.time,'sleep',side_effect=sleep_error):
                guard.retain_owner()
        self.assertEqual(retry.call_count,2);self.assertIs(a.critical,original)
        self.assertIs(guard.retention_error,failure);self.assertIs(guard.sleep_error,sleep_error)
        self.assertEqual(self.fixture.kernel.CloseHandle.call_count,4)

    def test_partial_ack_publication_preserves_body_error_pending_raw_and_no_retry(self):
        a=self.configure();body=ValueError('invented business failure after Git');failure=OSError('invented ack IO')
        def work():self.call();raise body
        write=terminal.actors.proof.channel._write
        def publish(path,value):
            if path.name=='ack.json':
                (path.parent/'ack.json.pending').write_bytes(b'{partial ack');raise failure
            return write(path,value)
        with patch.object(terminal.actors.proof.channel,'_write',side_effect=publish) as calls, \
             self.assertRaises(ValueError) as caught:terminal.run_guarded(a,work)
        self.assertIs(caught.exception,body);self.assertIs(a.terminal_guard.ack_error,failure)
        self.assertEqual(sum(c.args[0].name=='ack.json' for c in calls.call_args_list),1)
        self.assertTrue((self.f.child.root/'ack.json.pending').exists())
        self.assertFalse((self.f.child.root/'ack.json').exists());self.assertEqual(a.saved.statuses,['verified'])

    def test_unmatched_native_owner_is_retained_before_any_ack_scope_verification(self):
        a=self.configure();self.call();guard=terminal.ActorTerminal(a)
        original=tree.owner.UnreapedJob(11,22,33,{'assignment_confirmed':True})
        guard.unmatched_owner=original
        with self.assertRaises(ValueError):guard.acknowledge()
        self.assertIs(guard.unmatched_owner,original);self.assertFalse((self.f.child.root/'ack.json').exists())

    def test_unknown_close_owner_cannot_be_released_by_terminal_finished_flags(self):
        a=self.configure();original=self.fixture.critical_call(unclosed=True);guard=terminal.ActorTerminal(a)
        self.assertFalse(guard._recovery_ready())
        with patch.object(tree.owner,'_kernel') as kernel,self.assertRaises(ValueError):guard.acknowledge()
        kernel.assert_not_called();self.assertIs(self.f.child.owners[0],original)
        self.assertFalse((self.f.child.root/'ack.json').exists())

    def test_business_error_after_full_git_inventory_preserves_error_with_safe_ack(self):
        a=self.configure();failure=RuntimeError('invented report failure')
        def work():self.call();raise failure
        with self.assertRaises(RuntimeError) as caught:terminal.run_guarded(a,work)
        self.assertIs(caught.exception,failure);self.assertTrue(self.fence())
        self.assertEqual(a.terminal_guard.body_error,failure);self.assertIsNone(a.terminal_guard.ack_error)
