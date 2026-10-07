"""Strict receipt/witness publication: fake native/policy, real bounded files."""
import copy
from unittest.mock import Mock, patch
import unittest

from banto_ai import anomaly_v03_preformal_owned_git_job as git
from tests import test_anomaly_v03_git_pipe_normal_completion as prior


class GitPipeReceiptPublisherTests(unittest.TestCase):
    def setUp(self):
        prior.GitPipeNormalCompletionTests.setUp(self)  # Only fixture setup, no old test discovery.
        pin=git.observed._pin(b'fake executable')
        self.observation={'pin':pin,'identity':{'links':1}}
        self.policy.update({'executable_path':str(self.repository/'git.exe'),'executable_pin':pin,
                            'executable_links':1,'environment':{'PATH':'fixture'}})
        self.policy_read.return_value=(self.repository,self.repository/'git.exe',{'PATH':'fixture'},self.observation)
        self.after=self.enterContext(patch.object(git.dependencies,'file_observation',return_value=self.observation))
        self.memory={'information_class':9,'limit_flags':0x2000,
                     'peak_process_memory_used_bytes':1024,'peak_job_memory_used_bytes':2048}
        self.memory_read=self.enterContext(patch.object(git.owner,'_job_memory',return_value=self.memory))
        self.ad.call['expected_output_pin']=git.observed._pin(b'abc')
        self.original_file=git.file_io.FileIO
        self.addCleanup(lambda:[s.close() for s in getattr(self,'receipt_streams',[]) if not s.closed])
        self.receipt_streams=[]

    def normal(self):
        return git.GitPipeTransport(self.ad,kernel=self.kernel,repository=self.repository,
            policy=self.policy,stdin=self.stdin,child=self.child,stop_probe=self.stop,
            clock=self.clock,started_at=100.0,normal_completion=True)

    def ready(self):
        t=self.normal().start();self.assertEqual(t.step(),'pending')
        self.assertEqual(t.step(),'close_ready');return t

    def captured(self):
        t=self.ready();t.capture_receipt_inputs();t.close_once();return t

    def verify(self,t,result):
        return git.verify_quiescence((self.ad.inflight/'receipt.json').read_bytes(),
            result['receipt_pin'],result['quiescence'],root=self.repository,policy=t.policy,
            stdout_raw=self.ad.paths['stdout'].read_bytes(),stderr_raw=self.ad.paths['stderr'].read_bytes())

    def test_original_pre_close_memory_and_returns_publish_strict_normal_receipt(self):
        t=self.ready()
        def memory(kernel,job):
            self.assertIs(kernel,self.kernel);self.assertEqual(job,11)
            self.assertNotIn(11,self.closed);self.assertNotIn(22,self.closed);return self.memory
        self.memory_read.side_effect=memory
        t.capture_receipt_inputs();t.close_once();result=t.publish_receipt()
        self.assertTrue(self.verify(t,result));self.assertEqual(set(result['receipt']),git._FIELDS)
        self.assertEqual(result['receipt']['status'],'verified')
        self.assertEqual(result['receipt']['job']['memory'],self.memory)
        self.assertEqual(result['quiescence']['format'],git.PIPE_QUIESCENCE)
        self.assertIsNone(t.native.pending_pipe_receipt_owner);self.assertFalse(self.child.stopped)
        self.assertEqual(self.child.active,{0});self.assertEqual(self.child.finished,0)
        self.assertFalse(result['receipt']['execution_authenticated']);self.memory_read.assert_called_once()

    def test_cached_publisher_rechecks_disk_without_new_file_native_or_memory_query(self):
        t=self.captured();result=t.publish_receipt();closed=list(self.closed)
        with patch.object(git.file_io,'FileIO',side_effect=AssertionError('no reopen')):
            self.assertEqual(t.publish_receipt(),result)
        self.assertEqual(self.closed,closed);self.memory_read.assert_called_once()

    def test_missing_pre_close_inputs_or_declared_success_cannot_publish(self):
        t=self.ready();t.close_once();t.result['execution_authenticated']=True
        with self.assertRaises(git.owner.UnreapedJob):t.publish_receipt()
        self.assertFalse((self.ad.inflight/'receipt.json').exists())
        self.memory_read.assert_not_called();self.assertIs(t.native.pending_pipe_receipt_owner,t)
        self.assertIsNone(t.keeper.reconcile_once())

    def test_capture_after_core_close_refuses_closed_handle_memory_query(self):
        t=self.ready();t.close_once()
        with self.assertRaises(git.owner.UnreapedJob):t.capture_receipt_inputs()
        self.memory_read.assert_not_called();self.assertIsNone(t.receipt_inputs)

    def test_memory_interrupt_keeps_original_native_error_without_core_close(self):
        t=self.ready();failure=KeyboardInterrupt('memory');self.memory_read.side_effect=failure
        with self.assertRaises(git.owner.UnreapedJob):t.capture_receipt_inputs()
        self.assertIs(t.error,failure);self.assertIs(self.child.owners[0],t.native)
        self.assertTrue(self.child.stopped);self.assertNotIn(11,self.closed)
        self.assertFalse(self.ad.streams['stdout'].closed)

    def test_blob_pin_mismatch_publishes_failed_receipt_and_stops_new_work(self):
        self.ad.call['expected_output_pin']['sha256']='a'*64;t=self.captured();result=t.publish_receipt()
        self.assertEqual(result['receipt']['status'],'failed')
        self.assertEqual(result['receipt']['reason'],'blob_pin_mismatch');self.assertTrue(self.verify(t,result))
        self.assertTrue(self.child.stopped);self.assertEqual(self.child.active,{0});self.assertEqual(self.child.owners,{})

    def test_changed_executable_after_observation_remains_failed_not_verified(self):
        changed=copy.deepcopy(self.observation);changed['pin']=git.observed._pin(b'changed executable')
        self.after.return_value=changed;t=self.captured();result=t.publish_receipt()
        self.assertEqual(result['receipt']['reason'],'executable_changed')
        self.assertEqual(result['receipt']['executable_after'],changed);self.assertTrue(self.verify(t,result))
        self.assertTrue(self.child.stopped)

    def test_expired_original_elapsed_clock_refuses_before_receipt_file(self):
        t=self.captured();self.clock.return_value=110.0
        with self.assertRaises(git.owner.UnreapedJob):t.publish_receipt()
        self.assertFalse((self.ad.inflight/'receipt.json').exists())
        self.assertTrue(self.child.stopped);self.assertIsNone(t.keeper.reconcile_once())

    def test_partial_write_retains_stream_full_pending_raw_and_denies_recovery(self):
        t=self.captured();original=self.original_file;returned=[]
        class Partial:
            def __init__(self,path,mode):
                self.raw=original(path,mode);returned.append(self);self.calls=0
            def __getattr__(self,name):return getattr(self.raw,name)
            def write(self,raw):self.calls+=1;return self.raw.write(raw[:1])
        with patch.object(git.file_io,'FileIO',Partial):
            with self.assertRaises(git.owner.UnreapedJob):t.publish_receipt()
        self.receipt_streams.append(returned[0].raw)
        self.assertIs(t.publication_stream,returned[0]);self.assertFalse(returned[0].closed)
        self.assertGreater(len(t.publication_pending['receipt_raw']),1)
        self.assertEqual((self.ad.inflight/'receipt.json').stat().st_size,1)
        self.assertIsNone(t.keeper.reconcile_once());self.assertIs(self.child.owners[0],t.native)
        with self.assertRaises(git.owner.UnreapedJob):t.publish_receipt()
        self.assertEqual(returned[0].calls,1)

    def test_unknown_receipt_close_is_retained_despite_closed_metadata_and_full_raw(self):
        t=self.captured();original=self.original_file;returned=[];failure=KeyboardInterrupt('receipt close')
        class Unknown:
            def __init__(self,path,mode):self.raw=original(path,mode);returned.append(self)
            def __getattr__(self,name):return getattr(self.raw,name)
            def close(self):self.raw.close();raise failure
        with patch.object(git.file_io,'FileIO',Unknown):
            with self.assertRaises(git.owner.UnreapedJob):t.publish_receipt()
        self.assertTrue(returned[0].closed);self.assertIs(t.publication_stream,returned[0])
        self.assertIs(t.error,failure);self.assertIsNone(t.keeper.reconcile_once())
        self.assertIs(t.native.pending_pipe_receipt_owner,t);self.assertTrue(self.child.stopped)

    def test_root_checkpoint_error_after_write_retains_open_file_and_never_rewrites(self):
        t=self.captured();failure=OSError('root checkpoint')
        def check():
            if t.publication_stream is not None:raise failure
        self.ad.shared_checkpoint=check
        with self.assertRaises(git.owner.UnreapedJob):t.publish_receipt()
        self.receipt_streams.append(t.publication_stream)
        before=(self.ad.inflight/'receipt.json').read_bytes()
        with self.assertRaises(git.owner.UnreapedJob):t.publish_receipt()
        self.assertEqual((self.ad.inflight/'receipt.json').read_bytes(),before)
        self.assertFalse(t.publication_stream.closed);self.assertIsNone(t.keeper.reconcile_once())

    def test_cached_receipt_tamper_keeps_changed_raw_and_blocks_native_completion(self):
        t=self.captured();t.publish_receipt();path=self.ad.inflight/'receipt.json'
        changed=path.read_bytes().replace(b'"reason":null',b'"reason":"x"');path.write_bytes(changed)
        before=list(self.closed)
        with self.assertRaises(git.owner.UnreapedJob):t.publish_receipt()
        self.assertEqual(t.publication_pending['receipt_raw'],changed)
        self.assertEqual(self.closed,before);self.assertIsNone(t.keeper.reconcile_once())

    def test_changed_original_io_witness_refuses_before_receipt_file(self):
        t=self.captured();t.keeper.io_closed['read_closed']['stdout']['handle']=11
        with self.assertRaises(git.owner.UnreapedJob):t.publish_receipt()
        self.assertFalse((self.ad.inflight/'receipt.json').exists())
        self.assertTrue(self.child.stopped);self.assertIsNone(t.keeper.reconcile_once())
