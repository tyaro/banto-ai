"""Original parent binding/stop IO with fake Popen/supervisor and small real files."""
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_preformal_reader_git_worker as reader
from tests import test_anomaly_v03_parent_inventory_publication as parents
from tests import test_anomaly_v03_worker_stop_fence as fences

tree, channel, monitor = reader.tree, reader.channel, fences.monitor


class ParentBindingStopPublicationTests(unittest.TestCase):
    def setUp(self):
        self.fixture=parents.ParentInventoryPublicationTests()
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.f=self.fixture.f

    def create(self):return self.fixture.create()

    def injection(self, name, *, unknown_close=False):
        factory=tree.file_io.FileIO;made=[]
        failure=KeyboardInterrupt('fixture unknown parent control close') if unknown_close else OSError('fixture partial parent control write')
        class Wrapped:
            def __init__(self,path,mode):self.path=Path(path);self.raw=factory(path,mode);made.append(self)
            def __getattr__(self,key):return getattr(self.raw,key)
            def write(self,raw):
                if self.path.name==name and not unknown_close:self.raw.write(raw[:7]);raise failure
                return self.raw.write(raw)
            def close(self):
                value=self.raw.close()
                if self.path.name==name and unknown_close:raise failure
                return value
        def cleanup():
            for stream in made:
                if not stream.raw.closed:stream.raw.close()  # Test-only Python files; never native recovery.
        self.addCleanup(cleanup)
        return patch.object(tree.file_io,'FileIO',Wrapped),failure,made

    def test_same_parent_gate_publishes_binding_stop_and_cached_fence_never_reopens_or_recloses(self):
        factory=tree.file_io.FileIO
        with patch.object(tree.file_io,'FileIO',wraps=factory) as opened:
            p=self.create();gate=p.inventory_publication;initial=gate.verification
            p.bind(self.f.f.process);self.assertFalse(p.fence(self.f.f.process))
            held={name:row['original'] for name,row in gate.completed.items()}
            self.assertFalse(p.fence(self.f.f.process));p.source()
            self.assertEqual(opened.call_count,3)
        self.assertEqual(set(held),{'worker-inventory.json','binding.json','stop.json'})
        self.assertIs(gate.verification,initial)
        self.assertEqual(gate.cached_verification['verification_names'],('worker-inventory.json','binding.json','stop.json'))
        self.assertIs(gate.cached_verification['original_verification'],initial)
        self.assertIs(p.worker,self.f.f.process);self.assertIs(p.parent.worker,self.f.f.process)
        self.assertIs(p.parent.parent_publication_admission,gate)
        for name,row in held.items():
            self.assertIs(gate.completed[name]['original'],row);self.assertTrue(row['close_return_observed'])
            self.assertFalse(gate.completed[name]['observation']['parent_ack_authorized'])

    def test_partial_binding_write_keeps_original_popen_and_exact_error_before_fence_or_reopen(self):
        inject,failure,made=self.injection('binding.json.pending')
        with inject:
            p=self.create()
            with self.assertRaises(OSError) as caught:p.bind(self.f.f.process)
            count=len(made)
            with self.assertRaises(OSError) as fenced:p.fence(self.f.f.process)
            self.assertEqual(len(made),count)
        gate=p.inventory_publication
        self.assertIs(caught.exception,failure);self.assertIs(fenced.exception,failure)
        self.assertIs(p.worker,self.f.f.process);self.assertIs(p.parent.worker,self.f.f.process)
        self.assertIs(p.parent.binding_error,failure);self.assertIs(p.inventory_pending_owner,gate.pending)
        self.assertEqual((p.parent.root/'binding.json.pending').read_bytes(),gate.pending['raw'][:7])
        self.assertFalse((p.parent.root/'stop.json').exists())

    def test_unknown_binding_close_is_not_recovered_by_closed_stream_or_root_exit_metadata(self):
        inject,failure,_=self.injection('binding.json.pending',unknown_close=True)
        with inject:
            p=self.create()
            with self.assertRaises(KeyboardInterrupt):p.bind(self.f.f.process)
        pending=p.inventory_publication.pending
        self.assertTrue(pending['stream'].closed);self.assertFalse(pending['close_return_observed'])
        self.f.f.process.returncode=0
        with self.assertRaises(KeyboardInterrupt) as denied:p.fence(self.f.f.process)
        self.assertIs(denied.exception,failure);self.assertIs(p.inventory_pending_owner,pending)
        self.assertFalse((p.parent.root/'binding.json').exists());self.assertFalse((p.parent.root/'stop.json').exists())

    def test_unknown_stop_close_reaches_original_unreconciled_supervisor_without_kill_wait_handle_close(self):
        helper=fences.WorkerStopFenceTests();helper.setUp();self.addCleanup(helper.doCleanups)
        process=fences.helpers.FakeProcess(running=True);process.pid=self.f.f.child_id['pid']
        p=self.create();p.bind(process);held_fence=p.fence
        inject,failure,made=self.injection('stop.json.pending',unknown_close=True)
        with inject,self.assertRaises(monitor.UnreconciledWorker) as caught:helper.run_fake(process,held_fence)
        owned=caught.exception
        self.assertIs(owned.process,process);self.assertIs(owned.stop_fence,held_fence)
        self.assertIs(owned.fence_error,failure);self.assertIs(failure.reader_git_parent,p)
        self.assertIs(p.inventory_pending_owner,p.inventory_publication.pending)
        self.assertFalse(owned.report['worker_stop_fence_confirmed'])
        self.assertEqual((process.kills,process.waits),(0,0));process._handle.Close.assert_not_called()
        with patch.object(tree.file_io,'FileIO') as opened,self.assertRaises(KeyboardInterrupt) as again:
            monitor._stop_ack(owned.stop_fence,owned.process)
        self.assertIs(again.exception,failure);opened.assert_not_called();self.assertEqual(len(made),1)

    def test_non_none_stop_rename_return_cannot_be_replaced_by_valid_disk_stop_or_success_ack_flags(self):
        p=self.create();p.bind(self.f.f.process);rename=reader.io._rename_no_replace
        def invalid(src,dst):
            value=rename(src,dst)
            return False if Path(dst).name=='stop.json' else value
        with patch.object(reader.io,'_rename_no_replace',side_effect=invalid),self.assertRaises(ValueError) as caught:
            p.fence(self.f.f.process)
        self.assertTrue((p.parent.root/'stop.json').exists())
        self.assertIs(p.inventory_publication.pending['rename_return'],False)
        (p.parent.root/'ack.json').write_bytes(reader.io.json_bytes({'success':True,'no_new_jobs':True}))
        with patch.object(tree.file_io,'FileIO') as opened,self.assertRaises(ValueError) as denied:p.fence(self.f.f.process)
        self.assertIs(denied.exception,caught.exception);opened.assert_not_called()
        self.assertNotIn('stop.json',p.inventory_publication.completed)

    def test_creation_observation_failure_keeps_both_original_popen_holders_before_binding_file(self):
        p=self.create();failure=OSError('fixture binding identity IO')
        with patch.object(channel.observed,'creation_observation',side_effect=failure),self.assertRaises(OSError) as caught:
            p.bind(self.f.f.process)
        self.assertIs(caught.exception,failure);self.assertIs(p.worker,self.f.f.process)
        self.assertIs(p.parent.worker,self.f.f.process);self.assertIs(p.parent.binding_error,failure)
        self.assertFalse((p.parent.root/'binding.json.pending').exists())
        with self.assertRaises(OSError) as fenced:p.fence(self.f.f.process)
        self.assertIs(fenced.exception,failure)

    def test_foreign_gate_override_is_retained_and_latched_before_native_creation_io(self):
        p=self.create();process=self.f.f.process;p.worker=process
        foreign=SimpleNamespace(pending={'stream':object()},error=None)
        with patch.object(channel.observed,'creation_observation') as identity,self.assertRaises(ValueError) as caught:
            p.parent.bind(process,publication_admission=foreign)
        identity.assert_not_called();self.assertIs(p.parent.worker,process)
        self.assertIs(p.parent.rejected_parent_publication[0],p.inventory_publication)
        self.assertIs(p.parent.rejected_parent_publication[1],foreign)
        with self.assertRaises(ValueError) as denied:p.source()
        self.assertIs(denied.exception,caught.exception);self.assertIs(caught.exception.parent_control_channel,p.parent)

    def test_armed_parent_gate_cannot_be_dropped_to_legacy_binding_publisher(self):
        p=self.create();p.worker=self.f.f.process
        with patch.object(channel,'_write') as write,self.assertRaises(ValueError):p.parent.bind(self.f.f.process)
        write.assert_not_called();self.assertIs(p.parent.parent_publication_admission,p.inventory_publication)
        self.assertFalse((p.parent.root/'binding.json').exists())

    def test_unknown_external_stop_frame_is_denied_without_trusting_canonical_metadata(self):
        p=self.create();p.bind(self.f.f.process)
        (p.parent.root/'stop.json').write_bytes(reader.io.json_bytes({
            'format':channel.FORMAT+'-stop','request_pin':p.parent.request_pin,'no_new_jobs':True}))
        with patch.object(p.parent,'fence') as fence,self.assertRaises(ValueError):p.fence(self.f.f.process)
        fence.assert_not_called();self.assertNotIn('stop.json',p.inventory_publication.completed)
        self.assertIs(p.worker,self.f.f.process)

    def test_binding_close_observation_mutation_refuses_native_fence_even_with_exact_disk_raw(self):
        p=self.create();p.bind(self.f.f.process)
        row=p.inventory_publication.completed['binding.json']['original'];raw=row['published_raw']
        row['close_return_observed']=False
        with patch.object(p.parent,'fence') as fence,self.assertRaises(ValueError):p.fence(self.f.f.process)
        fence.assert_not_called();self.assertEqual((p.parent.root/'binding.json').read_bytes(),raw)
        self.assertIs(p.inventory_pending_owner,p.inventory_publication.pending)

    def test_late_pending_control_blocks_true_stub_proof_before_original_worker_release(self):
        p=self.create();p.bind(self.f.f.process);binding,_=p.parent._binding()
        proof=p.parent.root/'git-proof.json';proof.write_bytes(b'{}')
        (p.parent.root/'ack.json').write_bytes(reader.io.json_bytes({
            'format':channel.FORMAT+'-ack','request_pin':p.parent.request_pin,'binding_pin':p.parent.binding_pin,
            'worker_identity':binding['worker_identity'],'no_new_jobs':True,'jobs_finished':1,
            'proof':{'path':str(proof),'pin':reader.observed._pin(b'{}')}}))
        pending={'stream':object(),'raw':b'fixture late publisher'}
        def stub(_raw,_count):p.inventory_publication.pending=pending;return True
        p.parent.verify_quiescent=stub  # Explicit fake verdict, never a native receipt/proof authorization.
        with self.assertRaises(ValueError):p.fence(self.f.f.process)
        self.assertIs(p.inventory_pending_owner,pending);self.assertIs(p.worker,self.f.f.process)
        self.assertIs(p.parent.worker,self.f.f.process)

    def test_cached_completion_cannot_implicitly_extend_original_inventory_verification(self):
        p=self.create();p.bind(self.f.f.process);gate=p.inventory_publication
        original=gate.verification
        with patch.object(tree.file_io,'FileIO') as opened,self.assertRaises(ValueError) as caught:
            gate.verify_publications(('worker-inventory.json','binding.json'),cached=True)
        opened.assert_not_called();self.assertIs(gate.error,caught.exception)
        self.assertIs(gate.verification,original);self.assertIs(gate.pending['original_verification'],original)
        self.assertIs(p.worker,self.f.f.process);self.assertIs(p.parent.worker,self.f.f.process)


if __name__=='__main__':unittest.main()
