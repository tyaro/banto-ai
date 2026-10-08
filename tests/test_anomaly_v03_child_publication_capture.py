"""Local retained observation, fake native fixtures, real small control files."""
from types import SimpleNamespace
from unittest.mock import Mock,patch
import unittest

from banto_ai import anomaly_v03_preformal_reader_git_worker as reader
from tests import test_anomaly_v03_reader_control_publication as fixtures

archive,terminal,tree=reader.actors.archive,reader.terminal,reader.actors.tree


class ChildPublicationCaptureTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ReaderControlPublicationTests();self.f.setUp();self.addCleanup(self.f.doCleanups)

    def configure(self):
        self.a=self.f.configure();self.gate=self.a.control_publication
        return self.a

    def complete(self):
        self.configure();self.f.guarded(self.f.call)
        return self.a.child_publication_capture

    def envelope_failure(self, *, too_large=False):
        failure=KeyboardInterrupt('unknown local envelope encoding return')
        encode=archive.io.json_bytes
        def wrapped(value):
            if type(value) is dict and value.get('format')=='anomaly-v03-child-publication-local-capture-v1':
                if too_large:return b'x'*(32768+1)
                raise failure
            return encode(value)
        return patch.object(archive.io,'json_bytes',side_effect=wrapped),failure

    def test_original_three_streams_returns_verified_raw_and_separate_envelope_are_retained(self):
        cap=self.complete();state=cap.state;value=tree.v.strict_json(cap.payload_raw)
        self.assertIs(cap,self.gate.original_child_publication_capture)
        self.assertIs(cap.actor,self.a);self.assertIs(state['verification'],self.gate.verification)
        self.assertLessEqual(len(cap.payload_raw),32768)
        self.assertEqual(value['raw_bytes'],sum(len(raw) for raw in state['raw'].values()))
        for name in cap.NAMES:
            original=self.gate.completed[name]['original']
            self.assertIs(state['streams'][name],original['stream'])
            self.assertEqual(state['raw'][name],original['published_raw'])
            self.assertTrue(original['close_return_observed']);self.assertIsNone(original['rename_return'])
            self.assertNotIn('raw',value['publications'][name])
        self.assertFalse(value['parent_ack_authorized']);self.assertFalse(value['execution_authenticated'])
        self.assertFalse(value['atomic_reservation']);self.assertIsNone(cap.pending)
        self.assertFalse(self.gate.capture_pending())

    def test_cached_capture_returns_same_observation_without_clock_file_or_close_replay(self):
        cap=self.complete();original=cap.completion
        with (patch.object(self.gate,'checkpoint') as checkpoint,patch.object(archive.observed,'_file') as read,
              patch.object(archive.io,'_rename_no_replace') as rename,patch.object(tree.file_io,'FileIO') as opened):
            # Keep the original checkpoint pointer: changing it itself must be refused.
            self.gate.checkpoint=cap.actor.checkpoint
            self.assertIs(cap.seal(cap.state['returned_pins']),original)
        checkpoint.assert_not_called();read.assert_not_called();rename.assert_not_called();opened.assert_not_called()

    def test_unknown_envelope_copy_return_after_complete_ack_keeps_original_owner_and_terminal(self):
        self.configure();inject,failure=self.envelope_failure()
        with inject,self.assertRaises(fixtures.RetentionEscape):self.f.guarded(self.f.call)
        cap=self.a.child_publication_capture
        self.assertIs(cap.error,failure);self.assertIs(self.gate.error,failure)
        self.assertTrue((self.a.child.root/'ack.json').exists())
        self.assertIs(self.gate.pending['local_child_capture'],cap)
        self.assertEqual(set(cap.state['raw']),set(cap.NAMES))
        self.assertIs(self.a.terminal_guard.control_latch,self.gate)
        self.assertIs(failure.child_publication_capture,cap)

    def test_returned_verification_object_is_kept_before_invalid_return_rejection(self):
        self.configure();verify=self.gate.verify_publications;returned=object()
        def invalid(names):verify(names);return returned
        with patch.object(self.gate,'verify_publications',side_effect=invalid),self.assertRaises(fixtures.RetentionEscape):
            self.f.guarded(self.f.call)
        cap=self.a.child_publication_capture
        self.assertIs(cap.state['returned_pins'],returned);self.assertIs(cap.state['verification'],self.gate.verification)
        self.assertTrue((self.a.child.root/'ack.json').exists());self.assertIsNotNone(cap.error)

    def test_shared_callback_mutation_retains_original_raw_and_rejects_changed_close_return(self):
        self.configure();checkpoint=self.a.checkpoint;changed=[]
        def mutate():
            checkpoint()
            if self.gate.pending is not None and 'local_child_capture' in self.gate.pending:
                original=self.gate.completed['ack.json']['original']
                original['rename_return']='metadata return';changed.append(original)
        self.a.checkpoint=self.gate.checkpoint=self.gate.original_checkpoint=mutate
        with self.assertRaises(fixtures.RetentionEscape):self.f.guarded(self.f.call)
        cap=self.a.child_publication_capture
        self.assertEqual(len(changed),1);self.assertIs(changed[0],cap.state['originals']['ack.json'])
        self.assertIn('payload_raw',cap.state);self.assertIsNone(cap.completion)
        self.assertIs(self.gate.error,cap.error)

    def test_closed_metadata_does_not_replace_missing_original_close_return_observation(self):
        self.configure();verify=self.gate.verify_publications
        def missing(names):
            returned=verify(names);self.gate.completed['ack.json']['original']['close_return_observed']=False
            return returned
        with patch.object(self.gate,'verify_publications',side_effect=missing),self.assertRaises(fixtures.RetentionEscape):
            self.f.guarded(self.f.call)
        cap=self.a.child_publication_capture
        self.assertTrue(cap.state['streams']['ack.json'].closed)
        self.assertFalse(cap.state['originals']['ack.json']['close_return_observed'])
        self.assertIsNone(cap.completion)

    def test_bool_fd_is_rejected_with_all_original_streams_held(self):
        self.configure();verify=self.gate.verify_publications
        def changed(names):
            returned=verify(names);self.gate.completed['ack.json']['original']['fd']=True;return returned
        with patch.object(self.gate,'verify_publications',side_effect=changed),self.assertRaises(fixtures.RetentionEscape):
            self.f.guarded(self.f.call)
        cap=self.a.child_publication_capture
        self.assertIs(cap.state['originals']['ack.json']['fd'],True)
        self.assertEqual(len(cap.state['streams']),3);self.assertIsNone(cap.completion)

    def test_envelope_limit_keeps_raw_separate_without_creating_any_new_file(self):
        self.configure();inject,_=self.envelope_failure(too_large=True)
        with inject,self.assertRaises(fixtures.RetentionEscape):self.f.guarded(self.f.call)
        cap=self.a.child_publication_capture
        self.assertEqual(len(cap.state['payload_raw']),32769)
        self.assertTrue(all(len(raw)<=32768 for raw in cap.state['raw'].values()))
        self.assertEqual(set(self.gate.completed),set(cap.NAMES));self.assertIsNone(cap.completion)
        self.assertFalse((self.a.child.root/'child-witness.json').exists())

    def test_rearm_keeps_completed_original_and_rejected_capture_without_publication_retry(self):
        cap=self.complete();original=cap.completion
        with patch.object(self.gate,'publish') as publish,self.assertRaises(ValueError) as caught:
            archive.ChildPublicationCapture(gate=self.gate,actor=self.a)
        publish.assert_not_called();self.assertIs(self.a.child_publication_capture,cap)
        self.assertIs(cap.completion,original);self.assertIs(cap.rejected_capture.gate,self.gate)
        self.assertIs(cap.error,caught.exception);self.assertTrue(self.gate.capture_pending())

    def test_late_foreign_sidecar_stays_latched_after_pointer_restoration(self):
        cap=self.complete();foreign=SimpleNamespace(stream=object());self.a.child_publication_capture=foreign
        guard=self.a.terminal_guard
        self.assertTrue(guard._control_pending());failure=cap.error
        self.assertIs(self.gate.rejected_child_capture[1],foreign)
        self.a.child_publication_capture=cap;self.gate.error=None;self.gate.pending=None
        self.assertTrue(guard._control_pending());self.assertIs(cap.error,failure)
        with self.assertRaises(ValueError) as caught:cap.seal(cap.state['returned_pins'])
        self.assertIs(caught.exception,failure)

    def test_pending_capture_blocks_cached_original_keeper_even_after_gate_metadata_is_cleared(self):
        self.configure();original,keeper,kernel,wait,creation=self.f.native_keeper()
        self.assertIsNotNone(keeper.reconcile_once())
        before=(kernel.TerminateJobObject.call_count,kernel.CloseHandle.call_count,wait.call_count,creation.call_count)
        self.a.reader_publication={}
        cap=archive.ChildPublicationCapture(gate=self.gate,actor=self.a)
        self.assertIsNone(keeper.reconcile_once())
        failure=KeyboardInterrupt('unresolved original local capture')
        with self.assertRaises(KeyboardInterrupt):cap._failed(failure)
        self.gate.error=None;self.gate.pending=None;self.a.child_publication_capture=None
        self.assertIsNone(keeper.reconcile_once());self.assertIs(self.gate.error,failure)
        self.assertIs(keeper.original,original);self.assertIs(self.gate.original_child_publication_capture,cap)
        self.assertEqual(before,(kernel.TerminateJobObject.call_count,kernel.CloseHandle.call_count,
            wait.call_count,creation.call_count))

    def test_pending_local_capture_blocks_actor_new_work_and_terminal_normal_return(self):
        self.configure();self.a.reader_publication={}
        cap=archive.ChildPublicationCapture(gate=self.gate,actor=self.a)
        self.assertEqual(self.a.probe(),'worker_git_control_publication_unresolved')
        guard=terminal.ActorTerminal(self.a,reader.publish_archive_ack)
        with patch.object(guard,'_pause',side_effect=fixtures.RetentionEscape),self.assertRaises(fixtures.RetentionEscape):
            guard.retain_control()
        self.assertIs(guard.control_latch,self.gate);self.assertIs(self.gate.original_child_publication_capture,cap)

    def test_default_file_directed_publication_does_not_issue_local_capture(self):
        a=self.f.fixture.configure();self.f.actor=a
        result,target=self.f.fixture.receipt()
        with patch.object(tree,'run_owned',side_effect=self.f.fixture.executor(result,target)):
            self.f.guarded(self.f.fixture.call)
        self.assertIsNone(a.control_publication);self.assertFalse(hasattr(a,'child_publication_capture'))
        self.assertTrue((a.child.root/'ack.json').exists())

    def test_constructor_getter_failure_holds_original_inputs_and_exception_before_sidecar_validation(self):
        self.configure();failure=OSError('original actor publication getter failed')
        def fail(_):raise failure
        with patch.object(type(self.a),'reader_publication',property(fail),create=True),self.assertRaises(OSError) as caught:
            archive.ChildPublicationCapture(gate=self.gate,actor=self.a)
        cap=failure.child_publication_capture
        self.assertIs(caught.exception,failure);self.assertIs(cap.original_inputs[0],self.gate)
        self.assertIs(cap.original_inputs[1],self.a);self.assertIs(cap.pending['actor'],self.a)
        self.assertIs(self.gate.error,failure);self.assertIs(failure.control_publication_owner,self.gate)

    def test_damaged_pending_state_still_holds_verification_return_and_original_error(self):
        self.configure();self.a.reader_publication={}
        cap=archive.ChildPublicationCapture(gate=self.gate,actor=self.a)
        held=cap.pending;returned=object();cap.pending=None
        with self.assertRaises(ValueError) as caught:cap.seal(returned)
        self.assertIs(cap.original_seal_return,returned);self.assertIs(cap.original_inputs[2],held)
        self.assertIs(cap.error,caught.exception);self.assertIs(self.gate.error,caught.exception)
        self.assertTrue(self.gate.capture_pending())

    def test_late_local_envelope_pin_change_latches_original_owner_without_any_io_replay(self):
        cap=self.complete();original=cap.payload_raw
        cap.completion['payload_pin']=tree.observed._pin(b'foreign local envelope')
        with patch.object(archive.observed,'_file') as read,patch.object(archive.io,'_rename_no_replace') as rename:
            self.assertTrue(self.a.terminal_guard._control_pending())
        read.assert_not_called();rename.assert_not_called()
        self.assertEqual(cap.payload_raw,original);self.assertIsNotNone(cap.error)
        self.assertIs(self.gate.error,cap.error);self.assertIs(cap.completion['original_state'],cap.state)
