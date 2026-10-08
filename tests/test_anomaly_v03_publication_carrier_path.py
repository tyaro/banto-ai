"""Grouped carrier path: fake Win API, original owners, real small raw files."""
import copy
import ctypes
from types import SimpleNamespace
from unittest.mock import Mock,patch
import unittest

from banto_ai import anomaly_v03_preformal_reader_git_worker as reader
from tests import test_anomaly_v03_reader_control_publication as children
from tests import test_anomaly_v03_parent_inventory_publication as parents

archive,tree,terminal=reader.actors.archive,reader.tree,reader.terminal


class QueueKernel:
    def __init__(self):
        self.queue=bytearray();self.created=0;self.peek_max=32768;self.write_fault=None;self.read_fault=None
        self.CreatePipe=Mock(side_effect=self.create)
        self.WriteFile=Mock(side_effect=self.write)
        self.ReadFile=Mock(side_effect=self.read)
        self.PeekNamedPipe=Mock(side_effect=self.peek)
        self.CloseHandle=Mock(side_effect=AssertionError('no carrier close'))
    def create(self,read,write,*_):
        read._obj.value=74+self.created;write._obj.value=104+self.created;self.created+=1;return 1
    def write(self,handle,buffer,amount,count,_):
        self.queue.extend(buffer.raw[:amount]);count._obj.value=amount
        if self.write_fault:return self.write_fault(handle,buffer,amount,count)
        return 1
    def peek(self,handle,buffer,size,count,available,_):
        available._obj.value=min(len(self.queue),self.peek_max);return 1
    def read(self,handle,buffer,amount,count,_):
        raw=bytes(self.queue[:amount]);del self.queue[:amount]
        ctypes.memmove(buffer,raw,len(raw));count._obj.value=len(raw)
        if self.read_fault:return self.read_fault(handle,buffer,amount,count)
        return 1


class PublicationCarrierPathTests(unittest.TestCase):
    def setUp(self):
        self.f=children.ReaderControlPublicationTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.a=self.f.configure();self.gate=self.a.control_publication
        self.kernel=QueueKernel()
        self.creator=tree.owner.NativeGitPipes(self.kernel,checkpoint=Mock())
        self.creator.create()

    def arm(self,limit=32768):
        self.sender=self.gate.arm_publication_carrier(self.creator,frame_limit=limit)
        return self.sender

    def publish(self):
        self.f.guarded(self.f.call);return self.a.child_publication_capture

    def receiver(self):
        owner=SimpleNamespace()
        self.receiver_owner=owner
        return archive.PublicationCarrier(creator=self.creator,owner=owner,checkpoint=Mock(),frame_limit=32768,sending=False)

    def read_all(self,r):
        for _ in range(32768):
            result=r.read_once()
            if result is not None:return result
        self.fail('bounded test frame was not completed')

    def controller(self):
        # Same original real channel/files; independent inventory admission is an
        # explicit fixture checkpoint here. Real Parent issuance is tested below.
        p=reader.ReaderGitParent.__new__(reader.ReaderGitParent)
        p.parent=self.f.f.parent;p.worker=self.f.f.process;p.clock=copy.deepcopy(p.parent.request['clock'])
        p.inventory_checkpoint=Mock();p.entry={'inventory_pin':self.a.inventory_pin,
            'budget_root_identity':list(self.gate.identity)}
        p.error=p.inventory_publication_error=p.inventory_pending_owner=None
        p.original_child_publication_denial=None;p.append_controls=self.gate.control_limits
        p.inventory_publication=archive.ControlPublicationAdmission(endpoint=p.parent,inventory_pin=self.a.inventory_pin,
            root_identity=self.gate.identity,control_limits=self.gate.control_limits,
            checkpoint=p.inventory_checkpoint,owner=p)
        p.parent.parent_publication_admission=p.inventory_publication
        def ready():
            c=getattr(p,'original_publication_carrier',None)
            reader.v.require(c is None or not c.unresolved(),'fixture unresolved carrier')
        p._inventory_ready=Mock(side_effect=ready)
        return p

    def test_full_local_publication_sender_parent_readback_and_fence_keep_permission_false(self):
        self.arm();p=self.controller();r=p.bind_publication_carrier(self.creator,frame_limit=32768)
        cap=self.publish();candidate=p.observe_publication_carrier(p.worker)
        while candidate is None:candidate=p.observe_publication_carrier(p.worker)
        self.assertEqual(candidate['payload_raw'],cap.payload_raw)
        self.assertEqual(set(candidate['raw']),set(cap.NAMES))
        self.assertIs(candidate['binding']['process'],self.f.f.process)
        self.assertFalse(candidate['parent_ack_authorized']);self.assertFalse(r.completion['io_released'])
        p.parent.child_publication_observer=p._deny_child_publication
        self.assertFalse(p.fence(p.worker))
        self.assertIs(p.original_child_publication_denial['carrier_candidate'],candidate)
        self.assertIsNone(p.original_child_publication_denial['child_close_rename_owner_observation'])
        self.kernel.CloseHandle.assert_not_called();self.assertFalse(self.gate.capture_pending())

    def test_fragmented_read_and_cached_candidate_never_repeat_native_or_file_io(self):
        self.arm();p=self.controller();p.bind_publication_carrier(self.creator,frame_limit=32768);self.publish()
        self.kernel.peek_max=257
        candidate=None
        for _ in range(128):
            candidate=p.observe_publication_carrier(p.worker)
            if candidate is not None:break
        self.assertIsNotNone(candidate)
        counts=(self.kernel.WriteFile.call_count,self.kernel.ReadFile.call_count,self.kernel.PeekNamedPipe.call_count)
        with patch.object(reader.observed,'_file') as read,patch.object(reader.observed,'creation_observation') as creation:
            self.assertIs(p.observe_publication_carrier(p.worker),candidate)
            self.assertIs(self.sender.send(self.a.child_publication_capture),self.sender.completion)
        read.assert_not_called();creation.assert_not_called()
        self.assertEqual(counts,(self.kernel.WriteFile.call_count,self.kernel.ReadFile.call_count,self.kernel.PeekNamedPipe.call_count))

    def test_unknown_write_after_bytes_delivered_keeps_original_and_terminal_without_resend(self):
        sender=self.arm();failure=KeyboardInterrupt('unknown WriteFile return')
        def unknown(*_):raise failure
        self.kernel.write_fault=unknown
        with self.assertRaises(children.RetentionEscape):self.publish()
        block=sender.pending['block'];self.assertNotIn('return',block)
        self.assertGreater(len(self.kernel.queue),0);self.assertIs(sender.error,failure)
        self.assertIs(self.a.terminal_guard.control_latch,self.gate)
        self.gate.pending=self.gate.error=None;self.gate.publication_carrier=None
        self.assertTrue(self.gate.capture_pending());self.assertIs(self.gate.error,failure)
        with self.assertRaises(KeyboardInterrupt):sender.send(self.a.child_publication_capture)
        self.assertEqual(self.kernel.WriteFile.call_count,1);self.kernel.CloseHandle.assert_not_called()

    def test_short_write_observed_return_and_count_are_retained_without_retry(self):
        sender=self.arm()
        self.kernel.write_fault=lambda h,b,n,c:(setattr(c._obj,'value',n-1) or 1)
        with self.assertRaises(children.RetentionEscape):self.publish()
        self.assertEqual(sender.pending['block']['return'],1)
        self.assertEqual(sender.pending['block']['observed_count'],len(sender.pending['block']['raw'])-1)
        self.assertIsNotNone(sender.error);self.assertEqual(self.kernel.WriteFile.call_count,1)

    def test_frame_limit_counts_header_before_any_native_write(self):
        sender=self.arm(41)
        with self.assertRaises(children.RetentionEscape):self.publish()
        self.assertGreater(len(sender.raw),41);self.assertIn('frame_raw',sender.pending)
        self.kernel.WriteFile.assert_not_called();self.assertIsNotNone(self.a.child_publication_capture.completion)

    def test_unknown_read_preserves_consumed_raw_buffer_count_and_forbids_replay(self):
        self.arm();self.publish();r=self.receiver();failure=KeyboardInterrupt('unknown ReadFile return')
        def unknown(*_):raise failure
        self.kernel.read_fault=unknown
        with self.assertRaises(KeyboardInterrupt) as caught:r.read_once()
        self.assertIs(caught.exception,failure);self.assertNotIn('read_return',r.pending)
        self.assertGreater(r.pending['count'].value,0);self.assertIs(r.blocks[-1],r.pending)
        with self.assertRaises(KeyboardInterrupt):r.read_once()
        self.assertEqual(self.kernel.ReadFile.call_count,1);self.kernel.CloseHandle.assert_not_called()

    def test_partial_frame_and_empty_available_remain_unresolved_without_eof_permission(self):
        self.arm();self.publish();r=self.receiver();original=bytes(self.kernel.queue)
        self.kernel.queue[:]=original[:10]
        self.assertIsNone(r.read_once());self.assertTrue(r.unresolved())
        self.assertIsNone(r.read_once());self.assertIsNone(r.completion)
        self.kernel.queue.extend(original[10:]);self.assertIsNotNone(self.read_all(r))
        self.assertFalse(r.unresolved());self.assertFalse(r.completion['parent_ack_authorized'])

    def test_bad_digest_and_appended_bytes_latch_original_prefix_without_more_read(self):
        self.arm();self.publish();r=self.receiver();self.kernel.queue[8]^=1
        with self.assertRaises(ValueError):self.read_all(r)
        count=self.kernel.ReadFile.call_count
        with self.assertRaises(ValueError):r.read_once()
        self.assertEqual(self.kernel.ReadFile.call_count,count);self.assertGreater(len(r.raw),0)

    def test_extra_frame_bytes_are_rejected_before_read(self):
        self.arm();self.publish();r=self.receiver();self.kernel.queue.extend(b'x'*32768)
        self.kernel.peek_max=65536  # Report all available bytes; do not clamp this oversize fixture.
        with self.assertRaises(ValueError):r.read_once()
        self.kernel.ReadFile.assert_not_called();self.assertGreater(r.pending['available_count'],32768)

    def test_sender_callback_changes_original_handle_before_write_and_keeps_rejected_owner(self):
        sender=self.arm();checkpoint=sender.checkpoint
        def change():checkpoint();self.creator.writers['stdout'].handle=999
        sender.checkpoint=change
        # Updating the checkpoint pointer itself is forbidden before it is invoked.
        with self.assertRaises(children.RetentionEscape):self.publish()
        self.kernel.WriteFile.assert_not_called();self.assertIsNotNone(sender.error)

    def test_same_direction_rebind_retains_both_owners_and_latches_original(self):
        sender=self.arm();foreign=SimpleNamespace()
        with self.assertRaises(ValueError) as caught:
            archive.PublicationCarrier(creator=self.creator,owner=foreign,checkpoint=Mock(),frame_limit=32768,sending=True)
        self.assertIs(sender.error,caught.exception);self.assertIs(sender.rejected,foreign.original_publication_carrier)
        self.kernel.WriteFile.assert_not_called()

    def test_parent_raw_change_is_kept_and_cannot_be_hidden_by_restoring_metadata(self):
        self.arm();p=self.controller();r=p.bind_publication_carrier(self.creator,frame_limit=32768);self.publish()
        path=p.parent.root/'ack.json';original=path.read_bytes();path.write_bytes(b'{changed raw}')
        with self.assertRaises(ValueError):
            while p.observe_publication_carrier(p.worker) is None:pass
        self.assertEqual(p.publication_carrier_candidate['raw']['ack.json'],b'{changed raw}')
        failure=r.error;path.write_bytes(original);p.error=p.inventory_publication_error=None
        with self.assertRaises(ValueError) as caught:p.observe_publication_carrier(p.worker)
        self.assertIs(caught.exception,failure);self.assertIs(r.owner,p)

    def test_original_keeper_cached_completion_is_blocked_by_sender_failure_without_reap_or_close(self):
        original,keeper,kernel,wait,creation=self.f.native_keeper()
        self.assertIsNotNone(keeper.reconcile_once());before=(kernel.CloseHandle.call_count,wait.call_count)
        sender=self.arm();sender.started=True;sender.pending={'unknown_original_write':object()}
        self.assertIsNone(keeper.reconcile_once())
        failure=OSError('original carrier IO')
        with self.assertRaises(OSError):sender._failed(failure)
        self.gate.error=self.gate.pending=None
        self.assertIsNone(keeper.reconcile_once());self.assertIs(keeper.original,original)
        self.assertEqual(before,(kernel.CloseHandle.call_count,wait.call_count))

    def test_real_parent_issuance_rejects_wrong_handle_creation_before_any_read(self):
        # Reuse setup only: no old test bodies/native launch.
        f=parents.ParentInventoryPublicationTests();f.setUp();self.addCleanup(f.doCleanups)
        p=f.create();p.bind(f.f.f.process)
        with patch.object(reader.observed,'creation_observation',return_value={'pid':999,'creation_identity':1}),self.assertRaises(ValueError):
            p.bind_publication_carrier(self.creator,frame_limit=32768)
        self.kernel.ReadFile.assert_not_called();self.kernel.PeekNamedPipe.assert_not_called()
        self.assertIs(p.publication_carrier_binding['process'],f.f.f.process)
        self.assertIsNotNone(p.original_publication_carrier.error)

    def test_foreign_popen_and_late_candidate_mutation_refuse_without_reobservation(self):
        self.arm();p=self.controller();r=p.bind_publication_carrier(self.creator,frame_limit=32768);self.publish()
        candidate=None
        while candidate is None:candidate=p.observe_publication_carrier(p.worker)
        candidate['parent_ack_authorized']=True;before=self.kernel.ReadFile.call_count
        with self.assertRaises(ValueError):p.observe_publication_carrier(p.worker)
        self.assertEqual(self.kernel.ReadFile.call_count,before);self.assertIsNotNone(r.error)

    def test_default_local_publisher_has_no_carrier_and_native_entry_remains_closed(self):
        self.publish();self.kernel.WriteFile.assert_not_called()
        self.assertFalse(hasattr(self.gate,'original_publication_carrier'))
        with self.assertRaises(reader.monitor.resources.ResourceStop):reader.ReaderGitParent.create_native(root=object())

    def test_cleared_sender_error_metadata_still_raises_original_without_write_replay(self):
        sender=self.arm();failure=KeyboardInterrupt('unknown send owner')
        def unknown(*_):raise failure
        self.kernel.write_fault=unknown
        with self.assertRaises(children.RetentionEscape):self.publish()
        pending=sender.pending;sender.error=None;self.gate.error=self.gate.pending=None
        with self.assertRaises(KeyboardInterrupt) as caught:sender.send(self.a.child_publication_capture)
        self.assertIs(caught.exception,failure);self.assertIs(sender.pending,pending)
        self.assertEqual(self.kernel.WriteFile.call_count,1)

    def test_cleared_reader_error_metadata_still_keeps_original_count_buffer_without_read_replay(self):
        self.arm();self.publish();r=self.receiver();failure=KeyboardInterrupt('unknown read owner')
        def unknown(*_):raise failure
        self.kernel.read_fault=unknown
        with self.assertRaises(KeyboardInterrupt):r.read_once()
        pending=r.pending;r.error=None
        with self.assertRaises(KeyboardInterrupt) as caught:r.read_once()
        self.assertIs(caught.exception,failure);self.assertIs(r.pending,pending)
        self.assertEqual(self.kernel.ReadFile.call_count,1)

    def test_parent_checkpoint_raw_change_retains_both_readbacks_and_denies_completed_bytes(self):
        self.arm();p=self.controller();r=p.bind_publication_carrier(self.creator,frame_limit=32768);self.publish()
        ready=p._inventory_ready;changed=b'{late changed ack}'
        def mutate():ready();(p.parent.root/'ack.json').write_bytes(changed)
        p._inventory_ready=Mock(side_effect=mutate)
        with self.assertRaises(ValueError):
            while p.observe_publication_carrier(p.worker) is None:pass
        candidate=p.publication_carrier_candidate
        self.assertNotEqual(candidate['raw']['ack.json'],changed)
        self.assertEqual(candidate['post_checkpoint_raw']['ack.json'],changed)
        self.assertIsNotNone(r.error);self.assertFalse(candidate['parent_ack_authorized'])

    def test_tiny_fragments_cannot_grow_retained_native_buffers_without_bound(self):
        self.arm();self.publish();r=self.receiver();self.kernel.peek_max=1
        with self.assertRaises(ValueError):
            for _ in range(r.MAX_READ_BLOCKS+1):r.read_once()
        self.assertEqual(len(r.blocks),r.MAX_READ_BLOCKS)
        self.assertEqual(self.kernel.ReadFile.call_count,r.MAX_READ_BLOCKS)
        self.assertEqual(len(r.raw),r.MAX_READ_BLOCKS);self.assertNotIn('buffer',r.pending)
        self.assertTrue(all('raw_prefix' not in block for block in r.blocks))
        self.assertFalse(r.completion is not None);self.kernel.CloseHandle.assert_not_called()

    def test_upper_caller_retains_original_carrier_after_error_metadata_is_hidden(self):
        p=self.controller();p.original_bootstrap_inputs=(p.parent.request,self.creator)
        r=p.bind_publication_carrier(self.creator,frame_limit=32768)
        failure=KeyboardInterrupt('unknown original parent carrier read')
        with self.assertRaises(KeyboardInterrupt):r._failed(failure)
        r.error=p.error=p.inventory_publication_error=None;p.publication_carrier=None
        with patch.object(reader.ParentPublicationRetention,'_pause',side_effect=children.RetentionEscape),\
             self.assertRaises(children.RetentionEscape):reader.retain_parent_publications(OSError('caller report'),p)
        held=p.original_publication_retention
        self.assertIs(held.owners[4],r);self.assertIs(held.parent,p);self.assertIs(r.original_error,failure)
        self.assertIs(held.original_inputs,p.original_bootstrap_inputs)
        self.kernel.ReadFile.assert_not_called();self.kernel.CloseHandle.assert_not_called()
