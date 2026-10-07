"""Named control publication with real small files and fake channel identities."""
from types import SimpleNamespace
from unittest.mock import Mock,patch
import unittest

from banto_ai import anomaly_v03_preformal_worker_git_archive as archive
from tests import test_anomaly_v03_worker_git_proof as fixtures

channel=archive.proof.channel


class ControlPublicationAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.WorkerGitProofTests('test_normal_raw_close_then_lease_proof_and_real_parent_fence_path')
        self.f.setUp();self.addCleanup(self.f.doCleanups);self.f.configure()
        self.controls={name:32768 for name in archive.ArchiveAppendAdmission.CONTROL_NAMES}
        self.owner=SimpleNamespace(original_native=None)
        self.clock=Mock(return_value=None);self.gate=None
        self.addCleanup(self.close_test_files)
        self.value={'format':channel.FORMAT+'-stop','request_pin':self.f.child.request_pin,'no_new_jobs':True}
        self.path=self.f.child.root/'stop.json'

    def close_test_files(self):
        # Only this test's Python-owned files; no real Job/pipe/worker exists.
        if self.gate is None:return
        pending=self.gate.pending
        stream=None if pending is None else pending.get('stream')
        if stream is not None and not stream.closed:getattr(stream,'raw',stream).close()

    def create(self):
        info=self.f.measured.lstat()
        self.gate=archive.ControlPublicationAdmission(endpoint=self.f.child,
            inventory_pin=self.f.verifier.inventory_pin,root_identity=(info.st_dev,info.st_ino),
            control_limits=self.controls,checkpoint=self.clock,owner=self.owner)
        return self.gate

    def publish(self,value=None,path=None):
        return channel._write(self.path if path is None else path,self.value if value is None else value,
                              publication_admission=self.gate)

    def fault_stream(self, kind, failure=None):
        original=archive.proof.tree.file_io.FileIO;counts={'write':0,'close':0}
        class Fault:
            def __init__(self,*args):self.raw=original(*args)
            def __getattr__(self,name):return getattr(self.raw,name)
            def write(self,raw):
                counts['write']+=1
                return self.raw.write(raw[:-1] if kind=='partial' else raw)
            def close(self):
                counts['close']+=1;result=self.raw.close()
                if kind=='unknown_close':raise failure
                if kind=='changed_close':
                    path=self.raw.name
                    with open(path,'r+b') as stream:stream.write(b'!')
                return result
        return Fault,counts

    def test_same_request_control_snapshot_original_stream_and_return_precede_full_readback(self):
        gate=self.create();limits=gate.control_limits.copy();self.controls.clear()
        pin=self.publish();raw=archive.io.json_bytes(self.value)
        self.assertEqual(pin,archive.observed._pin(raw));self.assertEqual(self.path.read_bytes(),raw)
        self.assertFalse(self.path.with_name('stop.json.pending').exists())
        original=gate.completed['stop.json']['original'];row=gate.completed['stop.json']['observation']
        self.assertIs(original['owner'],self.owner);self.assertIs(self.owner.control_publication_owner,gate)
        self.assertIsNone(original['close_return']);self.assertTrue(original['close_return_observed'])
        self.assertTrue(original['stream'].closed);self.assertEqual(original['published_raw'],raw)
        self.assertEqual(original['before']['future_bytes'],sum(limits.values()))
        self.assertEqual(original['after']['future_entries'],14)
        for key in ('atomic_reservation','native_owner_recovered','parent_ack_authorized','execution_authenticated'):
            self.assertFalse(row[key])
        self.assertEqual(self.f.child.finished,0);self.assertFalse(self.f.child.stopped)
        self.assertFalse((self.f.child.root/'ack.json').exists())

    def test_actual_raw_cap_and_fixed_name_reject_before_exclusive_stream_or_clock(self):
        self.controls['stop.json.pending']=1;gate=self.create()
        with patch.object(archive.proof.tree.file_io,'FileIO') as opened,self.assertRaises(ValueError) as caught:
            self.publish()
        opened.assert_not_called();self.clock.assert_not_called();self.assertIs(gate.error,caught.exception)
        self.assertIs(caught.exception.control_publication_owner,gate);self.assertIs(gate.pending['value'],self.value)
        self.assertFalse(self.path.exists())

    def test_foreign_path_preserves_original_owner_and_rejects_without_writing(self):
        gate=self.create();foreign=self.f.measured/'stop.json'
        with patch.object(archive.proof.tree.file_io,'FileIO') as opened,self.assertRaises(ValueError):self.publish(path=foreign)
        opened.assert_not_called();self.clock.assert_not_called()
        self.assertIs(gate.pending['path'],foreign);self.assertIs(gate.owner,self.owner)
        self.assertFalse(foreign.exists());self.assertFalse(self.path.exists())

    def test_original_retained_failure_raw_counts_against_all_fourteen_future_slots(self):
        gate=self.create();retained=self.f.measured/'original-failure.bin';retained.write_bytes(b'x'*(600*1024))
        with patch.object(archive.proof.tree.file_io,'FileIO') as opened,self.assertRaisesRegex(ValueError,'outer byte/entry'):
            self.publish()
        opened.assert_not_called();self.assertEqual(retained.stat().st_size,600*1024)
        self.assertEqual(gate.pending['before']['future_entries'],14);self.assertFalse(self.path.exists())

    def test_retained_entries_and_diagnostic_reserve_deny_before_stream_creation(self):
        gate=self.create()
        for n in range(20):(self.f.measured/('kept-'+str(n))).write_bytes(b'')
        with patch.object(archive.proof.tree.file_io,'FileIO') as opened,self.assertRaisesRegex(ValueError,'outer byte/entry'):
            self.publish()
        opened.assert_not_called();self.assertEqual(len(list(self.f.measured.glob('kept-*'))),20)
        self.assertIs(gate.pending['owner'],self.owner);self.assertFalse(self.path.exists())

    def test_shared_callback_cannot_change_held_plan_or_replace_original_endpoint(self):
        gate=self.create()
        def mutate():gate.endpoint=self.f.parent
        self.clock.side_effect=mutate
        with patch.object(archive.proof.tree.file_io,'FileIO') as opened,self.assertRaisesRegex(ValueError,'original endpoint'):
            self.publish()
        opened.assert_not_called();self.assertIs(gate.original_endpoint,self.f.child)
        self.assertIs(gate.owner,self.owner);self.assertIs(gate.original_checkpoint,self.clock)

    def test_partial_write_retains_original_block_fd_stream_and_denies_all_replay(self):
        gate=self.create();factory,counts=self.fault_stream('partial')
        with patch.object(archive.proof.tree.file_io,'FileIO',factory),self.assertRaises(ValueError) as caught:self.publish()
        pending=gate.pending;self.assertFalse(pending['stream'].closed);self.assertIsNotNone(pending['fd'])
        self.assertEqual(pending['raw'],archive.io.json_bytes(self.value));self.assertFalse(pending['close_return_observed'])
        with patch.object(archive.proof.tree.file_io,'FileIO') as opened,self.assertRaises(ValueError) as again:self.publish()
        self.assertIs(again.exception,caught.exception);opened.assert_not_called();self.assertIs(gate.pending,pending)
        self.assertEqual(counts,{'write':1,'close':0});self.assertTrue(self.path.with_name('stop.json.pending').exists())

    def test_sync_interruption_retains_written_raw_and_open_original_stream_without_close(self):
        gate=self.create();failure=KeyboardInterrupt('control sync interrupted')
        with patch.object(archive.os,'fsync',side_effect=failure),self.assertRaises(KeyboardInterrupt) as caught:self.publish()
        self.assertIs(caught.exception,failure);self.assertIs(failure.control_publication_owner,gate)
        self.assertFalse(gate.pending['stream'].closed);self.assertNotIn('close_attempted',gate.pending)
        self.assertEqual(gate.pending['staging'].read_bytes(),gate.pending['raw']);self.assertFalse(self.path.exists())

    def test_unknown_close_keeps_return_indeterminate_even_when_metadata_and_disk_look_complete(self):
        gate=self.create();failure=KeyboardInterrupt('control close unknown');factory,counts=self.fault_stream('unknown_close',failure)
        with patch.object(archive.proof.tree.file_io,'FileIO',factory),self.assertRaises(KeyboardInterrupt) as caught:self.publish()
        self.assertIs(caught.exception,failure);self.assertTrue(gate.pending['stream'].closed)
        self.assertFalse(gate.pending['close_return_observed']);self.assertEqual(gate.pending['staging_raw'],gate.pending['raw'])
        with self.assertRaises(KeyboardInterrupt) as again:self.publish()
        self.assertIs(again.exception,failure);self.assertEqual(counts,{'write':1,'close':1})
        self.assertEqual(gate.completed,{});self.assertFalse(self.path.exists())

    def test_post_close_changed_raw_keeps_original_and_changed_bytes_without_reclose_or_rename(self):
        gate=self.create();factory,counts=self.fault_stream('changed_close')
        with patch.object(archive.proof.tree.file_io,'FileIO',factory),self.assertRaises(ValueError):self.publish()
        self.assertEqual(gate.pending['staging_raw'],gate.pending['raw'])
        self.assertNotEqual(gate.pending['closed_raw'],gate.pending['raw']);self.assertTrue(gate.pending['close_return_observed'])
        self.assertEqual(counts,{'write':1,'close':1});self.assertNotIn('rename_attempted',gate.pending)
        self.assertFalse(self.path.exists());self.assertEqual(gate.completed,{})

    def test_other_writer_growth_after_rename_poison_preserves_published_raw_and_owner(self):
        gate=self.create();rename=archive.io._rename_no_replace
        def growth(source,target):
            result=rename(source,target);(self.f.measured/'new-other-writer.bin').write_bytes(b'z'*(600*1024));return result
        with patch.object(archive.io,'_rename_no_replace',side_effect=growth),self.assertRaisesRegex(ValueError,'outer byte/entry'):
            self.publish()
        self.assertEqual(self.path.read_bytes(),gate.pending['raw']);self.assertTrue(gate.pending['stream'].closed)
        self.assertEqual(gate.pending['published_raw'],gate.pending['raw']);self.assertEqual(gate.completed,{})
        self.assertIs(self.owner.control_publication_owner,gate);self.assertFalse((self.f.child.root/'ack.json').exists())

    def test_owner_rebind_preserves_original_gate_and_rejected_gate_without_new_io(self):
        first=self.create()
        with self.assertRaisesRegex(ValueError,'cannot replace') as caught:self.create()
        second=caught.exception.control_publication_owner
        self.assertIs(self.owner.control_publication_owner,first);self.assertIs(first.rejected_publication,second)
        self.assertIs(second.owner,self.owner);self.assertIs(second.error,caught.exception)
        self.clock.assert_not_called();self.assertFalse(self.path.exists())

    def test_non_none_rename_return_keeps_completed_file_without_authorizing_publication_or_replay(self):
        gate=self.create();rename=archive.io._rename_no_replace
        def invalid_return(source,target):rename(source,target);return False
        with patch.object(archive.io,'_rename_no_replace',side_effect=invalid_return), \
             self.assertRaisesRegex(ValueError,'publication return') as caught:self.publish()
        self.assertIs(gate.pending['rename_return'],False);self.assertTrue(gate.pending['stream'].closed)
        self.assertEqual(self.path.read_bytes(),gate.pending['raw']);self.assertEqual(gate.completed,{})
        with patch.object(archive.io,'_rename_no_replace') as again,self.assertRaises(ValueError) as held:self.publish()
        again.assert_not_called();self.assertIs(held.exception,caught.exception)
        self.assertIs(self.owner.control_publication_owner,gate)

    def test_rejected_rebind_latches_original_gate_and_original_error_before_further_publication(self):
        first=self.create()
        with self.assertRaises(ValueError) as rejected:self.create()
        self.assertIs(first.error,rejected.exception);self.gate=first
        with patch.object(archive.proof.tree.file_io,'FileIO') as opened,self.assertRaises(ValueError) as stopped:self.publish()
        opened.assert_not_called();self.clock.assert_not_called();self.assertIs(stopped.exception,rejected.exception)
        self.assertIsNone(first.pending);self.assertFalse(self.path.exists())


if __name__=='__main__':unittest.main()
