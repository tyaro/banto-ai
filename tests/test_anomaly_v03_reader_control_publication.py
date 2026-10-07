"""Child control publication/retention with fake native facts and real small files."""
import copy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_preformal_reader_git_worker as reader
from tests import test_anomaly_v03_worker_git_actor as fixtures

actors, terminal, channel = reader.actors, reader.terminal, reader.channel
archive, tree, keepers = actors.archive, actors.tree, actors.keepers


class RetentionEscape(BaseException):
    """Test-only stop of a retained fake Python owner, never a production escape."""


class ReaderControlPublicationTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.WorkerGitActorTests(
            'test_exact_private_job_arguments_shared_probe_raw_archive_then_lease_and_cleanup')
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.f=self.fixture.f

    def configure(self, calls=1):
        f=self.f
        f.inventory['calls']=[f.call(n,'pre' if n==0 else 'post') for n in range(calls)]
        f.configure()
        identity=(f.measured.lstat().st_dev,f.measured.lstat().st_ino)
        controls={name:32768 for name in archive.ArchiveAppendAdmission.CONTROL_NAMES}
        value={'format':archive.APPEND_PLAN_FORMAT,'revision':f.revision,
            'request_pin':f.child.request_pin,'inventory_pin':f.verifier.inventory_pin,
            'budget_root':str(f.measured),'budget_root_identity':list(identity),
            'control_limits':controls,'formal_permission':False}
        raw=tree.io.json_bytes(value)
        self.actor=self.fixture.actor=actors.WorkerGitActor(child=f.child,
            inventory_raw=tree.io.json_bytes(f.inventory),inventory_pin=f.verifier.inventory_pin,
            checkpoint=self.fixture.checkpoint,
            pipe_io={'kernel':object(),'stdin':object(),'clock':lambda:100.0,'root_identity':identity},
            append_plan={'value':value,'pin':tree.observed._pin(raw)})
        self.gate=self.actor.control_publication
        # Independent caller inventory fixture; its Parent publisher is outside this unit.
        (f.parent.root/'worker-inventory.json').write_bytes(self.actor.inventory_raw)
        self.verifier=reader.ReaderGitArchiveVerifier(parent=f.parent,
            inventory_raw=self.actor.inventory_raw,inventory_pin=self.actor.inventory_pin,checkpoint=Mock())
        f.parent.verify_quiescent=self.verifier
        return self.actor

    def call(self, code=0, phase='pre'):
        a=self.actor;result,target=self.fixture.receipt(lease=a.child.finished,code=code)
        def run(_call):
            target.rename(a.inflight)
            value=copy.deepcopy(result);value['receipt_root']=str(a.inflight);return value
        with patch.object(a,'_run_pipe',side_effect=run):return self.fixture.call(phase)

    def guarded(self, operation):
        with patch.object(terminal.ActorTerminal,'_pause',side_effect=RetentionEscape):
            return terminal.run_guarded(self.actor,operation,publish_ack=reader.publish_archive_ack)

    def injected_file(self, name, *, unknown_close=False):
        factory=tree.file_io.FileIO;made=[]
        failure=KeyboardInterrupt('fixture unknown control close') if unknown_close else OSError('fixture partial control write')
        class Wrapped:
            def __init__(self,path,mode):self.raw=factory(path,mode);self.path=Path(path);made.append(self)
            def __getattr__(self,key):return getattr(self.raw,key)
            def write(self,raw):
                if self.path.name==name and not unknown_close:
                    self.raw.write(raw[:9]);raise failure
                return self.raw.write(raw)
            def close(self):
                value=self.raw.close()
                if self.path.name==name and unknown_close:raise failure
                return value
        def cleanup():
            for item in made:
                if not item.raw.closed:item.raw.close()  # Test's Python FileIO only; no native handle recovery.
        self.addCleanup(cleanup)
        return patch.object(tree.file_io,'FileIO',Wrapped),failure,made

    def test_actor_issues_same_context_owner_and_final_three_raw_publications(self):
        a=self.configure(2);gate=self.gate
        self.assertIs(gate.owner,a);self.assertIs(gate.endpoint,a.child)
        self.assertIs(gate.checkpoint,a.checkpoint);self.assertEqual(gate.inventory_pin,a.inventory_pin)
        def operation():self.call();return self.call(phase='post')
        self.assertEqual(self.guarded(operation),self.f.revision.encode()+b'\n')
        self.assertEqual(set(gate.completed),{'git-manifest.json','git-proof.json','ack.json'})
        self.assertIsNone(gate.pending);self.assertIsNone(gate.error)
        self.assertEqual(set(gate.verification['raw']),set(gate.completed))
        for name,row in gate.completed.items():
            self.assertTrue(row['original']['close_return_observed'])
            self.assertEqual(gate.verification['raw'][name],row['original']['published_raw'])
            self.assertFalse(row['observation']['parent_ack_authorized'])
            self.assertFalse(row['observation']['execution_authenticated'])
        self.assertTrue(self.f.parent.fence(self.f.process))

    def test_semantic_failed_prefix_uses_gate_but_keeps_business_error_and_raw(self):
        a=self.configure(2)
        with self.assertRaises(tree.owner.resources.ResourceStop) as caught:
            self.guarded(lambda:self.call(code=17))
        self.assertIs(caught.exception,a.error);self.assertEqual(a.saved.statuses,['failed'])
        self.assertTrue((a.inflight/'receipt.json').exists())
        self.assertEqual(set(self.gate.completed),{'git-manifest.json','git-proof.json','ack.json'})
        self.assertTrue(self.f.parent.fence(self.f.process))
        self.assertEqual(tree.v.strict_json((a.child.root/'git-proof.json').read_bytes())['git_proof']['terminal'],'failed')

    def test_zero_job_metadata_cannot_enter_new_control_publisher(self):
        self.configure()
        with patch.object(self.gate,'publish',wraps=self.gate.publish) as publish,self.assertRaises(ValueError):
            self.guarded(lambda:{'success':True,'jobs':0})
        publish.assert_not_called();self.assertFalse((self.actor.child.root/'ack.json').exists())

    def test_partial_manifest_write_retains_original_gate_stream_and_error_before_exit(self):
        a=self.configure();inject,failure,made=self.injected_file('git-manifest.json.pending')
        with inject,self.assertRaises(RetentionEscape):self.guarded(self.call)
        guard=a.terminal_guard
        self.assertIs(guard.ack_error,failure);self.assertIs(guard.original_error,failure)
        self.assertIs(guard.control_latch,self.gate);self.assertIs(self.gate.pending['stream'],made[0])
        self.assertIs(failure.control_publication_owner,self.gate)
        self.assertEqual((a.child.root/'git-manifest.json.pending').read_bytes(),self.gate.pending['raw'][:9])
        with self.assertRaises(OSError) as caught:self.gate.publish(a.child.root/'git-manifest.json',{})
        self.assertIs(caught.exception,failure);self.assertFalse((a.child.root/'ack.json').exists())

    def test_unknown_proof_close_keeps_observed_manifest_and_does_not_accept_closed_metadata(self):
        a=self.configure();inject,failure,_=self.injected_file('git-proof.json.pending',unknown_close=True)
        with inject,self.assertRaises(RetentionEscape):self.guarded(self.call)
        pending=self.gate.pending
        self.assertTrue(pending['stream'].closed);self.assertFalse(pending['close_return_observed'])
        self.assertEqual(set(self.gate.completed),{'git-manifest.json'})
        self.assertIs(a.terminal_guard.control_error,failure)
        self.assertTrue(a.child.stopped);self.assertFalse((a.child.root/'ack.json').exists())

    def test_body_error_and_ack_interruption_remain_separate_original_objects(self):
        a=self.configure();business=ValueError('fixture business operation failed after all calls')
        inject,failure,_=self.injected_file('ack.json.pending',unknown_close=True)
        def operation():self.call();raise business
        with inject,self.assertRaises(RetentionEscape):self.guarded(operation)
        guard=a.terminal_guard
        self.assertIs(guard.original_error,business);self.assertIs(guard.body_error,business)
        self.assertIs(guard.ack_error,failure);self.assertIs(guard.control_error,failure)
        self.assertEqual(set(self.gate.completed),{'git-manifest.json','git-proof.json'})

    def test_swallowed_publication_error_and_metadata_clearing_cannot_release_terminal_latch(self):
        a=self.configure();inject,failure,_=self.injected_file('git-manifest.json.pending')
        def operation():
            try:self.gate.publish(a.child.root/'git-manifest.json',{'inventory_pin':a.inventory_pin})
            except OSError:return 'swallowed'
        with inject,self.assertRaises(RetentionEscape):self.guarded(operation)
        guard=a.terminal_guard;self.assertIs(guard.control_error,failure)
        self.gate.error=None;self.gate.pending=None
        self.assertTrue(guard._control_pending())
        with patch.object(guard,'_pause',side_effect=RetentionEscape),self.assertRaises(RetentionEscape):guard.retain_control()
        self.assertIs(guard.control_latch,self.gate);self.assertFalse((a.child.root/'ack.json').exists())

    def test_final_raw_mutation_holds_original_and_changed_bytes_without_republication(self):
        a=self.configure();verify=self.gate.verify_publications
        def changed(names):
            (a.child.root/'git-proof.json').write_bytes(b'changed final proof')
            return verify(names)
        with patch.object(self.gate,'verify_publications',side_effect=changed),self.assertRaises(RetentionEscape):
            self.guarded(self.call)
        self.assertEqual(self.gate.pending['raw']['git-proof.json'],b'changed final proof')
        self.assertNotEqual(self.gate.completed['git-proof.json']['original']['published_raw'],b'changed final proof')
        self.assertIs(a.terminal_guard.control_latch,self.gate)
        with self.assertRaises(ValueError):self.f.parent.fence(self.f.process)

    def native_keeper(self):
        a=self.actor;lease=a.child.begin_job()
        original=tree.owner.UnreapedJob(11,22,33,{'assignment_confirmed':True})
        original.worker_git_actor=a
        keeper=keepers.ChildGitKeeper(original,child=a.child,lease=lease)
        kernel=SimpleNamespace(TerminateJobObject=Mock(return_value=True),CloseHandle=Mock(return_value=True))
        self.enterContext(patch.object(tree.owner,'_kernel',return_value=kernel))
        wait=self.enterContext(patch.object(tree.owner,'_wait_empty',return_value=(fixtures.fixtures.ACCOUNT,17)))
        creation=self.enterContext(patch.object(keepers,'_creation',return_value=fixtures.fixtures.identity(44,11)))
        return original,keeper,kernel,wait,creation

    def test_cached_keeper_completion_is_blocked_by_same_control_error_without_native_replay(self):
        self.configure();original,keeper,kernel,wait,creation=self.native_keeper()
        self.assertIsNotNone(keeper.reconcile_once())
        before=(kernel.TerminateJobObject.call_count,kernel.CloseHandle.call_count,wait.call_count,creation.call_count)
        inject,failure,_=self.injected_file('git-manifest.json.pending',unknown_close=True)
        with inject,self.assertRaises(KeyboardInterrupt):
            self.gate.publish(self.actor.child.root/'git-manifest.json',{'inventory_pin':self.actor.inventory_pin})
        self.assertIsNone(keeper.reconcile_once());self.assertIs(keeper.control_publication,self.gate)
        self.assertIs(keeper.control_failure,failure);self.assertIs(keeper.original,original)
        self.gate.error=None;self.gate.pending=None
        self.assertIsNone(keeper.reconcile_once())
        self.assertEqual(before,(kernel.TerminateJobObject.call_count,kernel.CloseHandle.call_count,wait.call_count,creation.call_count))

    def test_pending_control_blocks_core_close_after_original_reap_and_creation_only_once(self):
        self.configure();original,keeper,kernel,wait,creation=self.native_keeper()
        failure=OSError('fixture pending publisher');self.gate.error=failure;self.gate.pending={'owner':self.actor}
        self.assertIsNone(keeper.reconcile_once());self.assertIsNone(keeper.reconcile_once())
        self.assertEqual(kernel.TerminateJobObject.call_count,1);self.assertEqual(wait.call_count,1)
        self.assertEqual(creation.call_count,1);kernel.CloseHandle.assert_not_called()
        self.assertIs(keeper.control_failure,failure);self.assertIs(keeper.original,original)
        self.assertIs(keeper.control_actor,self.actor);self.assertIs(keeper.control_publication,self.gate)
        self.assertEqual(set(keeper.remaining),{'job','process','thread'})

    def test_replaced_gate_is_retained_and_refused_by_terminal_before_report(self):
        a=self.configure();original=self.gate;guard=terminal.ActorTerminal(a,reader.publish_archive_ack)
        rejected=SimpleNamespace(pending=None,error=None);a.control_publication=rejected
        self.assertTrue(guard._control_pending());self.assertIn(original,guard.control_owners)
        self.assertIn(rejected,guard.control_owners)
        with patch.object(guard,'_pause',side_effect=RetentionEscape),self.assertRaises(RetentionEscape):guard.retain_control()
        self.assertFalse((a.child.root/'ack.json').exists())

    def test_keeper_foreign_clock_and_terminal_foreign_sidecar_keep_original_gate_without_reap(self):
        a=self.configure();original,keeper,kernel,wait,creation=self.native_keeper()
        self.gate.checkpoint=Mock()
        self.assertTrue(keeper._control_pending());self.assertIs(keeper.control_publication,self.gate)
        self.assertIs(keeper.original,original)
        wait.assert_not_called();creation.assert_not_called();kernel.CloseHandle.assert_not_called()
        self.gate.checkpoint=a.checkpoint
        guard=terminal.ActorTerminal(a,reader.publish_archive_ack)
        foreign=SimpleNamespace(pending=None,error=None);a.control_publication_owner=foreign
        self.assertTrue(guard._control_pending());self.assertIs(guard.original_control,self.gate)
        self.assertIsNotNone(guard.control_error);self.assertIsNotNone(keeper.control_failure)

    def test_rejected_sidecar_is_snapshotted_by_both_original_keeper_and_terminal(self):
        a=self.configure();original,keeper,kernel,wait,creation=self.native_keeper()
        guard=terminal.ActorTerminal(a,reader.publish_archive_ack)
        foreign=SimpleNamespace(pending={'stream':object()},error=None)
        a.control_publication_owner=foreign
        self.assertTrue(keeper._control_pending());self.assertTrue(guard._control_pending())
        a.control_publication_owner=self.gate
        self.assertIs(keeper.rejected_control_owner[2],foreign)
        self.assertTrue(any(item is foreign for item in guard.control_owners))
        self.assertIs(keeper.original,original);self.assertTrue(guard._control_pending())
        wait.assert_not_called();creation.assert_not_called();kernel.CloseHandle.assert_not_called()


if __name__=='__main__':unittest.main()
