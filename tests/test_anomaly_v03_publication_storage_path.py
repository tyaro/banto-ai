"""Coupled storage gate path: original fake owners and real small root files."""
import copy
from types import SimpleNamespace
from unittest.mock import Mock,patch
import unittest

from banto_ai import anomaly_v03_preformal_reader_git_worker as reader
from banto_ai import anomaly_v03_preformal_generated_chain_budget as monitor
from tests import test_anomaly_v03_reader_control_publication as children
from tests import test_anomaly_v03_parent_inventory_publication as parents
from tests import test_anomaly_v03_publication_carrier_path as carriers

archive,tree=reader.actors.archive,reader.tree


class PublicationStoragePathTests(unittest.TestCase):
    def setUp(self):
        self.f=children.ReaderControlPublicationTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        original=self.f.f.call
        def call(*args,**kwargs):
            row=original(*args,**kwargs)
            row['raw_inventory']={'receipt.json':16384,'stdout.bin':128,'stderr.bin':1024,'partial-archive.bin':65536}
            return row
        self.f.f.call=call
        self.a=self.f.configure();self.gate=self.a.control_publication
        self.allocation={'format':archive.PublicationStorageAdmission.FORMAT,'frame_bytes':8192,
            'archive_bytes':65536,'carrier_failure_bytes':16384,'resident_raw_bytes':1572864,
            'parent_raw_limits':{'stdout.bin':4096,'stderr.bin':4096,'receipt.json':16384}}
        self.addCleanup(self.close_test_files)

    def close_test_files(self):
        # Test-created Python files only, after the retained fixture is escaped.
        # No kernel handle or production recovery is performed by this cleanup.
        stream=(self.gate.pending or {}).get('stream')
        if stream is not None and not stream.closed:getattr(stream,'raw',stream).close()
        storage=getattr(self.a,'original_publication_storage',None)
        sink=getattr(storage,'sink',None)
        for stream in getattr(sink,'streams',{}).values():
            if not stream.closed:getattr(stream,'raw',stream).close()

    def arm(self):
        return self.a.arm_publication_storage(self.allocation)

    def creator(self):
        self.kernel=carriers.QueueKernel()
        creator=tree.owner.NativeGitPipes(self.kernel,checkpoint=Mock());creator.create();return creator

    def test_same_inventory_root_clock_and_separate_raw_growth_failure_quantities_are_held(self):
        storage=self.arm();view=storage.last_observation
        self.assertIs(storage.owner,self.a);self.assertIs(storage.endpoint,self.a.child)
        self.assertIs(storage.checkpoint,self.a.checkpoint);self.assertIs(storage.inventory_raw,self.a.inventory_raw)
        self.assertIs(self.gate.original_publication_storage,storage)
        self.assertIs(self.a.append_admission.original_publication_storage,storage)
        raw=max(sum(call['raw_inventory'].values()) for call in storage.inventory['calls'])
        future=sum(self.gate.control_limits.values())+raw+65536+16384+24576
        self.assertEqual(view['future_bytes'],future);self.assertEqual(storage.raw_bytes,raw)
        self.assertFalse(view['atomic_reservation']);self.assertFalse(view['capacity_pass'])
        self.assertFalse(view['private_memory_measured']);self.assertGreaterEqual(view['remaining_entries'],0)

    def test_allocation_copy_precedes_shared_callback_and_does_not_follow_caller_changes(self):
        held=copy.deepcopy(self.allocation)
        self.a.checkpoint.side_effect=lambda:self.allocation.update(frame_bytes=41,parent_raw_limits={})
        storage=self.arm();self.assertEqual(storage.allocation,held)
        self.assertIs(storage.original_inputs[4],self.allocation)
        self.assertNotEqual(storage.allocation,self.allocation)

    def test_closed_allocation_and_bool_or_relaxed_hard_caps_are_rejected(self):
        variants=[]
        for field,value in [('frame_bytes',True),('frame_bytes',32769),('archive_bytes',524289),
                            ('resident_raw_bytes',1),('carrier_failure_bytes',16383)]:
            v=copy.deepcopy(self.allocation);v[field]=value;variants.append(v)
        v=copy.deepcopy(self.allocation);v['unregistered_carrier_file']=1;variants.append(v)
        v=copy.deepcopy(self.allocation);v['parent_raw_limits']['foreign.bin']=1;variants.append(v)
        for value in variants:
            with self.subTest(value=value),self.assertRaises(ValueError):archive.PublicationStorageAdmission.validate_allocation(value)

    def test_invalid_constructor_keeps_original_owner_inputs_and_exception_before_file_or_pipe_io(self):
        self.allocation['archive_bytes']=True
        with patch.object(tree.file_io,'FileIO') as opened,self.assertRaises(ValueError) as caught:self.arm()
        opened.assert_not_called();storage=caught.exception.publication_storage
        self.assertIs(storage.original_inputs[4],self.allocation);self.assertIs(storage.owner,self.a)
        self.assertIs(self.a.original_publication_storage,storage);self.assertIs(storage.original_error,caught.exception)

    def test_full_parent_failure_maximum_is_refused_before_any_new_pipe_or_file(self):
        self.allocation['parent_raw_limits']['stdout.bin']=1024**2
        with patch.object(tree.owner,'NativeGitPipes') as creator,patch.object(tree.file_io,'FileIO') as opened,\
             self.assertRaises(ValueError) as caught:self.arm()
        creator.assert_not_called();opened.assert_not_called()
        self.assertLess(caught.exception.publication_storage.pending['remaining_bytes'],0)

    def test_actual_retained_entry_exceeds_coupled_entry_remaining_and_stays_latched(self):
        storage=self.arm();(storage.root/'other-one.bin').write_bytes(b'a');(storage.root/'other-two.bin').write_bytes(b'b')
        with self.assertRaises(ValueError) as caught:storage.view('external_writer')
        pending=storage.pending;self.assertLess(pending['remaining_entries'],0)
        self.gate.error=self.gate.pending=None;storage.error=None
        with self.assertRaises(ValueError) as again:storage.view('no_retry')
        self.assertIs(again.exception,caught.exception);self.assertIs(storage.pending,pending)

    def test_actual_retained_bytes_and_parent_future_raw_are_counted_without_old_width_model(self):
        storage=self.arm();remaining=storage.last_observation['remaining_bytes']
        (storage.root/'retained-parent-raw.bin').write_bytes(b'x'*(remaining+1))
        with self.assertRaises(ValueError):storage.view('retained_bytes')
        self.assertLess(storage.pending['remaining_bytes'],0)
        self.assertGreater(storage.pending['snapshot']['directory_bytes'],remaining)

    def test_control_over_cap_and_late_original_plan_mutation_retain_observations(self):
        storage=self.arm();path=self.a.child.root/'git-proof.json';path.write_bytes(b'x'*32769)
        with self.assertRaises(ValueError):storage.view('control_limit')
        self.assertEqual(storage.pending['controls']['git-proof.json']['bytes'],32769)
        self.assertIsNotNone(storage.original_error)

    def test_callback_mutated_plan_is_refused_before_snapshot_and_keeps_original_allocation(self):
        storage=self.arm();before=storage.plan_raw
        self.a.checkpoint.side_effect=lambda:storage.allocation.update(archive_bytes=65537)
        with patch.object(monitor,'_directory_snapshot') as snapshot,self.assertRaises(ValueError):storage.view('mutation')
        snapshot.assert_not_called();self.assertEqual(storage.plan_raw,before)
        self.assertEqual(storage.pending['stage'],'mutation')

    def test_archive_growth_cap_is_separate_from_partial_archive_raw_cap(self):
        self.allocation['archive_bytes']=4096;storage=self.arm()
        self.assertEqual(storage.inventory['calls'][0]['raw_inventory']['partial-archive.bin'],65536)
        self.assertEqual(storage.allocation['archive_bytes'],4096)
        (storage.root/'worker-git.bin').write_bytes(b'x'*4097)
        with self.assertRaises(ValueError):storage.view('archive_limit')
        self.assertEqual(storage.pending['archive_bytes'],4097)

    def test_carrier_frame_mismatch_is_held_before_native_write_and_cannot_bypass_storage(self):
        storage=self.arm();creator=self.creator()
        with self.assertRaises(ValueError):self.gate.arm_publication_carrier(creator,frame_limit=8193)
        sender=self.gate.original_publication_carrier
        self.assertIs(storage.carriers[0],sender);self.assertIs(sender.creator,creator)
        self.kernel.WriteFile.assert_not_called();self.assertIsNotNone(storage.original_error)

    def test_bounded_frame_links_every_storage_view_with_explicit_stub_root_snapshot(self):
        storage=self.arm();creator=self.creator()
        # Only this composing test stubs root totals; it is not capacity evidence.
        with patch.object(monitor,'_directory_snapshot',return_value={'directory_bytes':0,'directory_entries':0,'directory_depth':1}):
            sender=self.gate.arm_publication_carrier(creator,frame_limit=8192)
            self.f.guarded(self.f.call)
        self.assertIs(sender.storage_admission,storage);self.assertIs(sender.native.publication_storage,storage)
        self.assertIs(storage.writer,self.a.writer);self.assertEqual(storage.last_observation['stage'],'carrier_io')
        self.assertFalse(sender.completion['parent_ack_authorized']);self.assertFalse(storage.last_observation['capacity_pass'])

    def test_real_root_control_publication_overrun_retains_python_stream_before_terminal_return(self):
        storage=self.arm()
        with self.assertRaises(children.RetentionEscape):self.f.guarded(self.f.call)
        self.assertIsNotNone(storage.original_error);self.assertIs(self.gate.error,storage.original_error)
        self.assertIs(self.a.terminal_guard.control_latch,self.gate)
        self.assertIsNotNone(self.a.pending)
        self.assertIsNone(self.gate.pending)  # Coupled gate refused before control publication was attempted.
        self.assertTrue((self.a.inflight/'receipt.json').exists())
        self.assertIsNotNone(self.a.pending['event'])
        self.assertFalse((self.a.child.root/'ack.json').exists())

    def test_sink_before_and_after_creation_preserves_same_original_budget_and_unattempted_streams(self):
        storage=self.arm();call=self.a.verifier.inventory['calls'][0]
        admission=tree.GitSinkAdmission(root=storage.root,root_identity=storage.identity,
            revision=self.a.child.request['revision'],call=call,checkpoint=self.a.checkpoint,publication_storage=storage)
        self.assertIs(admission.native.publication_storage,storage);self.assertIs(storage.sink,admission)
        with self.assertRaises(tree.owner.UnreapedJob) as caught:admission.create()
        self.assertIs(caught.exception,admission.native)
        self.assertIs(admission.original_publication_storage,storage);self.assertLessEqual(len(admission.streams),1)
        self.assertIsNotNone(storage.original_error)

    def test_erased_storage_gate_sidecar_is_retained_and_cannot_be_restored_into_permission(self):
        storage=self.arm();self.gate.original_publication_storage=None
        with self.assertRaises(ValueError) as caught:self.gate.capture_pending()
        self.assertIs(self.gate.rejected_storage_binding[0],storage)
        self.gate.original_publication_storage=storage;self.gate.error=None
        self.assertTrue(self.gate.capture_pending());self.assertIs(storage.original_error,caught.exception)
        self.assertIs(self.gate.error,caught.exception)

    def test_foreign_storage_rearm_keeps_original_and_rejected_plan_without_io_retry(self):
        storage=self.arm()
        with self.assertRaises(ValueError) as caught:self.arm()
        self.assertIs(self.a.original_publication_storage,storage)
        self.assertIs(storage.rejected_storage.original_inputs[4],self.allocation)
        self.assertIs(storage.original_error,caught.exception)

    def test_real_parent_gate_and_carrier_hold_same_storage_context_but_native_preview_is_false(self):
        f=parents.ParentInventoryPublicationTests();f.setUp();self.addCleanup(f.doCleanups)
        # This fixture retains an earlier channel. Isolate the composing path;
        # the actual occupied-root rejection has a separate explicit test below.
        with patch.object(monitor,'_directory_snapshot',return_value={'directory_bytes':0,'directory_entries':0,'directory_depth':1}):
            p=f.create();storage=p.arm_publication_storage(self.allocation);p.bind(f.f.f.process)
            creator=self.creator();carrier=p.bind_publication_carrier(creator,frame_limit=8192)
            preview=storage.native_launch_preview()
        self.assertIs(carrier.storage_admission,storage);self.assertIs(storage.gate,p.inventory_publication)
        self.assertFalse(preview['native_launch_authorized'])
        self.assertIs(preview['original_owner'],p);self.assertEqual(preview['plan_pin'],storage.plan_pin)
        self.kernel.ReadFile.assert_not_called();self.kernel.WriteFile.assert_not_called()

    def test_upper_caller_retains_original_storage_after_sidecar_and_error_metadata_are_hidden(self):
        f=parents.ParentInventoryPublicationTests();f.setUp();self.addCleanup(f.doCleanups)
        with patch.object(monitor,'_directory_snapshot',return_value={'directory_bytes':0,'directory_entries':0,'directory_depth':1}):
            p=f.create();storage=p.arm_publication_storage(self.allocation)
        failure=KeyboardInterrupt('storage root observation')
        with self.assertRaises(KeyboardInterrupt):storage._failed(failure)
        p.error=p.inventory_publication_error=storage.error=p.inventory_publication.error=None;p.publication_storage=None
        with patch.object(reader.ParentPublicationRetention,'_pause',side_effect=children.RetentionEscape),\
             self.assertRaises(children.RetentionEscape):reader.retain_parent_publications(OSError('caller report'),p)
        self.assertIs(p.original_publication_retention.owners[6],storage)
        self.assertIs(storage.original_error,failure)

    def test_cached_original_keeper_is_blocked_by_storage_failure_without_job_or_core_replay(self):
        original,keeper,kernel,wait,creation=self.f.native_keeper();self.assertIsNotNone(keeper.reconcile_once())
        before=(kernel.CloseHandle.call_count,wait.call_count);storage=self.arm();failure=OSError('storage checkpoint')
        with self.assertRaises(OSError):storage._failed(failure)
        self.gate.error=self.gate.pending=storage.error=None
        self.assertIsNone(keeper.reconcile_once());self.assertIs(keeper.original,original)
        self.assertEqual(before,(kernel.CloseHandle.call_count,wait.call_count))

    def test_default_has_no_storage_sidecar_and_native_entry_rejects_before_clock_or_kernel(self):
        self.assertFalse(hasattr(self.a,'original_publication_storage'))
        with patch.object(tree.owner,'_kernel') as kernel,patch.object(reader.time,'monotonic') as clock,\
             self.assertRaises(reader.monitor.resources.ResourceStop):reader.ReaderGitParent.create_native(root=object())
        kernel.assert_not_called();clock.assert_not_called()

    def test_real_parent_retained_prior_channel_is_counted_and_rejects_before_carrier_issuance(self):
        f=parents.ParentInventoryPublicationTests();f.setUp();self.addCleanup(f.doCleanups)
        p=f.create()
        with patch.object(tree.owner,'NativeGitPipes') as creator,self.assertRaises(ValueError) as caught:
            p.arm_publication_storage(self.allocation)
        creator.assert_not_called();storage=caught.exception.publication_storage
        self.assertLess(storage.pending['remaining_entries'],0)
        self.assertTrue((f.f.f.parent.root/'request.json').exists())
        self.assertIs(storage.owner,p);self.assertIs(p.original_publication_storage,storage)

    def test_unknown_control_close_is_retained_with_original_storage_error_and_no_metadata_release(self):
        storage=self.arm();factory=tree.file_io.FileIO;failure=KeyboardInterrupt('unknown original manifest close')
        class Unknown:
            def __init__(self,path,mode):self.raw=factory(path,mode)
            def __getattr__(self,name):return getattr(self.raw,name)
            def close(self):self.raw.close();raise failure
        def selected(path,mode):
            return Unknown(path,mode) if str(path).endswith('git-manifest.json.pending') else factory(path,mode)
        with patch.object(monitor,'_directory_snapshot',return_value={'directory_bytes':0,'directory_entries':0,'directory_depth':1}),\
             patch.object(tree.file_io,'FileIO',side_effect=selected),self.assertRaises(children.RetentionEscape):
            self.f.guarded(self.f.call)
        self.assertIs(storage.original_error,failure);self.assertIs(self.gate.error,failure)
        self.assertTrue(self.gate.pending['stream'].closed)
        self.assertFalse(self.gate.pending['close_return_observed'])
        self.gate.error=storage.error=None
        self.assertTrue(self.gate.capture_pending());self.assertIs(storage.error,failure)

    def test_hidden_archive_storage_reference_is_refused_before_any_append(self):
        storage=self.arm();self.a.append_admission.original_publication_storage=None
        gate=self.a.append_admission;frame=b'held frame';writer=self.a.writer
        gate.pending={'before_raw':writer.raw,'lease':0}
        with self.assertRaises(ValueError):gate._remaining(len(frame),'before')
        self.assertIs(writer.original_publication_storage,storage)
        self.assertEqual(writer.raw,b'');self.assertEqual(writer.rows,[])

    def test_hidden_sink_storage_reference_keeps_original_bootstrap_and_rejects_before_open(self):
        storage=self.arm();admission=tree.GitSinkAdmission(root=storage.root,root_identity=storage.identity,
            revision=self.a.child.request['revision'],call=self.a.verifier.inventory['calls'][0],
            checkpoint=self.a.checkpoint,publication_storage=storage)
        admission.original_publication_storage=None;admission.publication_storage=None
        with patch.object(tree.file_io,'FileIO') as opened,self.assertRaises(tree.owner.UnreapedJob) as caught:
            admission.checkpoint()
        opened.assert_not_called();self.assertIs(caught.exception,admission.native)
        self.assertIs(admission.publication_storage_input[0],storage)
