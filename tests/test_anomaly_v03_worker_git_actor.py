"""Actor boundary with fake executor/native facts; no real worker/native gate."""
import copy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_preformal_worker_git_actor as actor
from tests import test_anomaly_v03_worker_git_proof as fixtures

tree, keepers = actor.tree, actor.keepers


class WorkerGitActorTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.WorkerGitProofTests('test_normal_raw_close_then_lease_proof_and_real_parent_fence_path')
        self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.checkpoint = Mock(return_value=None)

    def configure(self, calls=1):
        f = self.f
        f.inventory['calls'] = [f.call(n,'pre' if n == 0 else 'post') for n in range(calls)]
        f.configure()
        self.actor = actor.WorkerGitActor(child=f.child,
            inventory_raw=tree.io.json_bytes(f.inventory), inventory_pin=f.verifier.inventory_pin,
            checkpoint=self.checkpoint)
        return self.actor

    def receipt(self, lease=0, code=0):
        f = self.f
        f.identity.update(fixtures.identity(44+lease,11+lease), native_start_identity_authenticated=True)
        result, target, _ = fixtures.quiescent_fixtures.GitQuiescenceTests.run_call(f,code=code)
        return copy.deepcopy(result),target

    def executor(self, result, target):
        def run(**options):
            self.options = options
            self.assertIsNone(options['stop_probe']())
            target.rename(options['receipt_root'])
            returned = copy.deepcopy(result); returned['receipt_root']=str(options['receipt_root'])
            return returned
        return run

    def call(self, phase='pre', **changes):
        return self.actor.call(phase=phase,operation=changes.pop('operation','head'),**changes)

    def test_exact_private_job_arguments_shared_probe_raw_archive_then_lease_and_cleanup(self):
        a=self.configure();result,target=self.receipt()
        with patch.object(tree,'run_owned',side_effect=self.executor(result,target)) as run:
            self.assertEqual(self.call(),self.f.revision.encode()+b'\n')
        self.assertEqual(run.call_count,1);self.assertTrue(self.options['capture_quiescence'])
        self.assertEqual(self.options['timeout_seconds'],10);self.assertEqual(self.options['root'],self.f.root)
        self.assertEqual(self.options['policy'],self.f.policy)
        self.assertEqual(a.saved.read(0)['event'],result['quiescence'])
        self.assertFalse(a.inflight.exists());self.assertEqual(self.f.child.finished,1)
        self.assertFalse(self.f.child.active);self.assertIsNone(a.pending)
        self.assertFalse((self.f.child.root/'ack.json').exists())

    def test_next_phase_uses_same_new_inflight_after_saved_cleanup_and_unique_identity(self):
        a=self.configure(2);one=self.receipt(0);two=self.receipt(1)
        with patch.object(tree,'run_owned',side_effect=self.executor(*one)):self.call()
        with patch.object(tree,'run_owned',side_effect=self.executor(*two)):self.call('post')
        self.assertEqual(len(a.writer.rows),2);self.assertEqual(self.f.child.finished,2)
        self.assertEqual(a.saved.read(0)['event'],one[0]['quiescence'])
        self.assertNotEqual(a.saved.read(0)['event']['process_identity'],a.saved.read(1)['event']['process_identity'])

    def test_wrong_exact_call_denies_executor_before_lease_or_raw_creation(self):
        a=self.configure()
        with patch.object(tree,'run_owned') as run,self.assertRaises(ValueError):self.call('post')
        run.assert_not_called();self.assertFalse(self.f.child.active)
        self.assertFalse(a.inflight.exists());self.assertEqual(a.writer.path.read_bytes(),b'')

    def test_external_policy_changed_denies_new_job_without_fallback(self):
        a=self.configure();Path(self.f.parent.request['policy_path']).write_bytes(b'{}')
        with patch.object(tree,'run_owned') as run,self.assertRaises(ValueError):self.call()
        run.assert_not_called();self.assertFalse(self.f.child.active);self.assertTrue(self.f.child.stopped)

    def test_shared_stop_during_executor_is_visible_and_failed_receipt_keeps_raw(self):
        a=self.configure(2);result,target=self.receipt(code=17);base=self.executor(result,target)
        def run(**options):
            value=base(**options);self.f.child.stopped=True
            self.assertEqual(options['stop_probe'](),'source_channel_stopped');return value
        with patch.object(tree,'run_owned',side_effect=run),self.assertRaises(tree.owner.resources.ResourceStop):self.call()
        self.assertEqual(a.saved.statuses,['failed']);self.assertEqual(self.f.child.finished,1)
        self.assertEqual(set(p.name for p in a.inflight.iterdir()),{'receipt.json','stdout.bin','stderr.bin'})
        with patch.object(tree,'run_owned') as run,self.assertRaises(ValueError):self.call('post')
        run.assert_not_called();self.assertFalse((self.f.child.root/'ack.json').exists())

    def test_original_return_stdout_mismatch_keeps_inflight_active_and_no_archive(self):
        a=self.configure();result,target=self.receipt();result['stdout']=b'changed return'
        with patch.object(tree,'run_owned',side_effect=self.executor(result,target)),self.assertRaises(ValueError):self.call()
        self.assertEqual(self.f.child.active,{0});self.assertEqual(a.writer.path.read_bytes(),b'')
        self.assertTrue((a.inflight/'receipt.json').exists());self.assertIsNotNone(a.pending['result'])

    def test_archive_partial_write_preserves_raw_and_pending_no_second_executor(self):
        a=self.configure();result,target=self.receipt();failure=OSError('invented partial archive')
        def partial(path,frame):path.write_bytes(frame[:13]);raise failure
        with patch.object(tree,'run_owned',side_effect=self.executor(result,target)), \
             patch.object(actor.archive,'_append_frame',side_effect=partial),self.assertRaises(OSError):self.call()
        self.assertIs(a.error,failure);self.assertTrue(a.writer.failed);self.assertEqual(self.f.child.active,{0})
        self.assertEqual(a.writer.path.stat().st_size,13);self.assertTrue((a.inflight/'stdout.bin').exists())
        with patch.object(tree,'run_owned') as run,self.assertRaises(ValueError):self.call()
        run.assert_not_called();self.assertIs(a.error,failure)

    def test_extra_inflight_file_denies_cleanup_and_keeps_every_original_raw(self):
        a=self.configure();result,target=self.receipt();base=self.executor(result,target)
        def run(**options):
            value=base(**options);(a.inflight/'unexpected.bin').write_bytes(b'keep');return value
        with patch.object(tree,'run_owned',side_effect=run),self.assertRaises(ValueError):self.call()
        self.assertEqual(self.f.child.finished,1);self.assertEqual(len(list(a.inflight.iterdir())),4)
        self.assertTrue((a.inflight/'receipt.json').exists());self.assertTrue(self.f.child.stopped)

    def test_individual_cleanup_io_failure_keeps_saved_raw_and_remaining_files(self):
        a=self.configure();result,target=self.receipt();unlink=Path.unlink;failure=OSError('invented unlink')
        def remove(path,*args,**kwargs):
            if path==a.inflight/'stdout.bin':raise failure
            return unlink(path,*args,**kwargs)
        with patch.object(tree,'run_owned',side_effect=self.executor(result,target)), \
             patch.object(Path,'unlink',new=remove),self.assertRaises(OSError):self.call()
        self.assertEqual(a.saved.read(0)['raw']['stdout.bin'],result['stdout'])
        self.assertIs(a.error,failure);self.assertTrue((a.inflight/'stdout.bin').exists())
        self.assertTrue((a.inflight/'stderr.bin').exists());self.assertEqual(self.f.child.finished,1)

    def critical_call(self, *, unclosed=False):
        original=tree.owner.UnclosedHandles({'job':11},{}) if unclosed else tree.owner.UnreapedJob(
            11,22,33,{'assignment_confirmed':True},extra_handles={'inherited_0':55})
        def run(**options):
            self.actor.inflight.mkdir()
            (self.actor.inflight/'stdout.bin').write_bytes(b'partial output')
            (self.actor.inflight/'stderr.bin').write_bytes(b'failure raw')
            raise original
        with patch.object(tree,'run_owned',side_effect=run),self.assertRaises(type(original)) as caught:self.call()
        self.assertIs(caught.exception,original);return original

    def recovery_patches(self):
        self.kernel=SimpleNamespace(TerminateJobObject=Mock(return_value=True),CloseHandle=Mock(return_value=True))
        self.enterContext(patch.object(tree.owner,'_kernel',return_value=self.kernel))
        self.enterContext(patch.object(tree.owner,'_wait_empty',return_value=(fixtures.ACCOUNT,17)))
        self.enterContext(patch.object(keepers,'_creation',return_value=fixtures.identity(44,11)))

    def test_original_owner_keeper_is_held_before_ledger_io_failure_and_reraised_exactly(self):
        a=self.configure();failure=OSError('invented ledger IO')
        with patch.object(self.f.child,'hold_owner',side_effect=failure):original=self.critical_call()
        self.assertIs(a.critical,original);self.assertIs(original.worker_git_actor,a)
        self.assertIs(a.keeper,original.child_keeper);self.assertIs(a.keeper.ledger_error,failure)
        self.assertEqual(self.f.child.active,{0});self.assertTrue((a.inflight/'stdout.bin').exists())

    def test_keep_owner_actual_callback_saves_recovery_and_finishes_only_exact_lease(self):
        a=self.configure();original=self.critical_call();self.recovery_patches()
        event=a.keep_owner()
        self.assertIs(a.critical,original);self.assertIs(a.leases.kept[0],a.keeper)
        self.assertEqual(a.saved.read(0)['event'],event);self.assertEqual(a.saved.statuses,['failed'])
        self.assertEqual(self.f.child.finished,1);self.assertFalse(self.f.child.owners)
        self.assertEqual(self.kernel.CloseHandle.call_count,4);self.assertTrue((a.inflight/'stdout.bin').exists())
        self.assertFalse((self.f.child.root/'ack.json').exists())

    def test_unknown_close_owner_remains_blocked_and_no_recovery_or_ack(self):
        a=self.configure();original=self.critical_call(unclosed=True)
        with patch.object(tree.owner,'_kernel') as kernel:self.assertIsNone(a.keeper.reconcile_once())
        kernel.assert_not_called();self.assertIs(self.f.child.owners[0],original)
        self.assertEqual(self.f.child.finished,0);self.assertEqual(a.writer.path.read_bytes(),b'')

    def test_keeper_archive_failure_callback_cannot_reappend_or_release_original_owner(self):
        a=self.configure();original=self.critical_call();self.recovery_patches();event=a.keeper.reconcile_once()
        failure=OSError('invented recovery archive IO')
        def keep(*,on_observation):
            for _ in range(2):
                with self.assertRaises(BaseException):on_observation(copy.deepcopy(event))
            return None
        with patch.object(a.keeper,'keep',side_effect=keep), \
             patch.object(actor.archive,'_append_frame',side_effect=failure) as append:
            self.assertIsNone(a.keep_owner())
        self.assertEqual(append.call_count,1);self.assertIs(a.recovery_error,failure)
        self.assertIs(self.f.child.owners[0],original);self.assertEqual(self.f.child.active,{0})
        self.assertTrue(a.writer.failed);self.assertEqual(self.kernel.CloseHandle.call_count,4)
        self.assertTrue((a.inflight/'stderr.bin').exists())
