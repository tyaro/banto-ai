"""Single-call transport with fake native APIs and real bounded disk sinks."""
import ctypes
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_preformal_owned_git_job as git
from banto_ai import anomaly_v03_preformal_child_git_keeper as keepers
from tests import test_anomaly_v03_spawn_cleanup_owner as fixture


class GitPipeTransportTests(unittest.TestCase):
    def setUp(self):
        fixture.SpawnCleanupOwnerTests.setUp(self)  # Only fake API setup, no old test discovery.
        tmp=tempfile.TemporaryDirectory(prefix='banto-pipe-transport-')
        self.addCleanup(tmp.cleanup)
        self.repository=Path(tmp.name);root=self.repository/'outer';root.mkdir()
        call={'lease':0,'phase':'pre','operation':'source_blob',
            'source_path':'src/banto_ai/anomaly_v03.py',
            'expected_output_pin':{'bytes':3,'sha256':'a'*64},
            'raw_inventory':{'receipt.json':16384,'stdout.bin':32,'stderr.bin':16}}
        self.ad=git.GitSinkAdmission(root=root,root_identity=(root.stat().st_dev,root.stat().st_ino),
            revision='b'*40,call=call,checkpoint=lambda:None)
        self.addCleanup(lambda:[s.close() for s in self.ad.streams.values() if not s.closed])
        pairs=iter([(74,104),(75,105)])
        def create(read,write,security,hint):
            read._obj.value,write._obj.value=next(pairs);return 1
        self.kernel.CreatePipe=Mock(side_effect=create)
        self.kernel.ResumeThread=Mock(return_value=1)
        self.data={74:b'abc',75:b''}
        def peek(handle,buffer,amount,count,available,left):
            available._obj.value=len(self.data[handle]);return int(bool(self.data[handle]))
        def read(handle,buffer,amount,count,overlapped):
            block=self.data[handle][:amount];self.data[handle]=self.data[handle][amount:]
            ctypes.memmove(buffer,block,len(block));count._obj.value=len(block);return 1
        self.kernel.PeekNamedPipe=Mock(side_effect=peek);self.kernel.ReadFile=Mock(side_effect=read)
        self.enterContext(patch.object(ctypes,'get_last_error',return_value=109,create=True))
        self.accounting={'total_processes':1,'active_processes':0,'limit_terminated_processes':0}
        self.wait.return_value=(self.accounting,0)
        self.account=self.enterContext(patch.object(git.owner,'_accounting',return_value=self.accounting))
        self.exit=self.enterContext(patch.object(git.owner,'_root_exit',return_value=0))
        identity={'pid':44,'creation_time_100ns':111};identity['start_token']=git.v.canonical_sha256(identity)
        self.enterContext(patch.object(keepers,'_creation',return_value=identity))
        self.policy={'revision':'b'*40,'process_ownership':git.direct.JOB_OWNERSHIP}
        self.policy_read=self.enterContext(patch.object(git.direct,'_policy',return_value=(
            self.repository,self.repository/'git.exe',{'PATH':'fixture'},None)))
        self.child=SimpleNamespace(stopped=False,hold_owner=Mock())
        self.clock=Mock(return_value=100.0);self.stop=Mock(return_value=None)
        self.stdin=SimpleNamespace(fileno=lambda:0)

    def transport(self):
        return git.GitPipeTransport(self.ad,kernel=self.kernel,repository=self.repository,
            policy=self.policy,stdin=self.stdin,child=self.child,stop_probe=self.stop,
            clock=self.clock,started_at=100.0)

    def ready(self):
        t=self.transport().start()
        self.assertEqual(t.step(),'pending');self.assertEqual(t.step(),'close_ready')
        return t

    def test_exact_call_spawn_bounded_raw_close_and_cache_without_native_replay(self):
        t=self.ready();result=t.close_once();before=list(self.closed)
        again=t.close_once()
        self.assertEqual(result,again);self.assertEqual(self.closed,before)
        self.assertEqual(self.ad.paths['stdout'].read_bytes(),b'abc')
        self.assertEqual(self.ad.paths['stderr'].read_bytes(),b'')
        self.assertEqual(t.argv[-2:],['show','b'*40+':src/banto_ai/anomaly_v03.py'])
        self.assertIs(t.native,self.ad.native);self.assertIs(t.native.pipe_transport,t)
        self.wait.assert_called_once();self.kernel.ReadFile.assert_called_once()
        self.assertEqual(result['recovery']['format'],git.PIPE_RECOVERY)
        self.assertFalse(result['lease_completed']);self.assertFalse(result['parent_ack_authorized'])

    def test_shared_stop_before_creation_keeps_bootstrap_and_does_not_start_job(self):
        self.stop.return_value='stop';t=self.transport()
        with self.assertRaises(git.owner.UnreapedJob) as caught:t.start()
        self.assertIs(caught.exception,self.ad.bootstrap);self.assertIs(caught.exception.pipe_transport,t)
        self.assertFalse(self.ad.inflight.exists());self.kernel.CreatePipe.assert_not_called()
        self.kernel.CreateProcessW.assert_not_called();self.assertIsNone(t.keeper)

    def test_shared_stop_after_spawn_stops_suspended_root_without_resume_or_core_close(self):
        self.stop.side_effect=[None,'stop'];t=self.transport()
        with self.assertRaises(git.owner.UnreapedJob):t.start()
        self.kernel.ResumeThread.assert_not_called();self.wait.assert_called_once()
        self.assertEqual(self.closed,[61,62,63,104,105]);self.assertIsNotNone(t.keeper.reaped)
        self.assertIsNone(t.keeper.completion)

    def test_output_limit_stops_job_keeps_sentinel_and_refuses_other_pipe_or_close(self):
        self.ad.limits['stdout.bin']=3;self.data[74]=b'abcdef';t=self.transport().start()
        with self.assertRaises(git.owner.UnreapedJob):t.step()
        self.assertEqual(t.reason,'output_limit');self.wait.assert_called_once()
        self.assertEqual(self.ad.paths['stdout'].read_bytes(),b'abc')
        self.assertEqual(self.kernel.ReadFile.call_count,1)
        before=list(self.closed)
        with self.assertRaises(git.owner.UnreapedJob):t.close_once()
        with self.assertRaises(git.owner.UnreapedJob):t.step()
        self.assertEqual(self.closed,before);self.wait.assert_called_once()

    def test_read_interrupt_stops_original_job_and_retains_api_buffer_pending(self):
        t=self.transport().start();failure=KeyboardInterrupt('ReadFile')
        self.kernel.ReadFile.side_effect=failure
        with self.assertRaises(git.owner.UnreapedJob) as caught:t.step()
        self.assertIs(caught.exception,t.native);self.assertIs(t.reader.failure,failure)
        self.assertIsNotNone(t.output.pending['buffer']);self.wait.assert_called_once()
        self.assertIs(t.native.child_keeper,t.keeper);self.assertFalse(self.ad.streams['stdout'].closed)

    def test_native_observation_error_retained_before_keeper_ledger_and_stop(self):
        t=self.transport().start();failure=OSError('accounting')
        self.account.side_effect=failure
        def ledger(lease,native):self.assertIs(t.error,failure)
        self.child.hold_owner.side_effect=ledger
        with self.assertRaises(git.owner.UnreapedJob):t.step()
        self.assertIs(t.error,failure);self.wait.assert_called_once();self.child.hold_owner.assert_called_once()

    def test_unconfirmed_reap_cannot_return_close_ready_or_discard_original_owner(self):
        t=self.transport().start();t.step();self.wait.side_effect=OSError('reap')
        with self.assertRaises(git.owner.UnreapedJob):t.step()
        self.assertIsNone(t.keeper.reaped);self.assertIsNone(t.result)
        before=self.wait.call_count;t.stop_once();self.assertEqual(self.wait.call_count,before)
        self.assertIs(t.native.pipe_transport,t);self.assertEqual(self.closed,[61,62,63,104,105])

    def test_ledger_interrupt_keeps_exact_keeper_and_original_error(self):
        t=self.transport().start();failure=KeyboardInterrupt('ledger');self.child.hold_owner.side_effect=failure
        with self.assertRaises(git.owner.UnreapedJob):t.stop_once()
        self.assertIs(t.keeper,t.native.child_keeper);self.assertIs(t.keeper.ledger_error,failure)
        self.wait.assert_not_called();self.assertFalse(self.ad.streams['stdout'].closed)

    def test_close_unknown_retains_original_read_handle_and_prevents_reclose(self):
        t=self.ready();failure=KeyboardInterrupt('read close');original=self.kernel.CloseHandle.side_effect
        self.kernel.CloseHandle.side_effect=lambda h:(_ for _ in ()).throw(failure) if h==74 else original(h)
        with self.assertRaises(git.owner.UnreapedJob):t.close_once()
        count=self.kernel.CloseHandle.call_count
        with self.assertRaises(git.owner.UnreapedJob):t.close_once()
        self.assertEqual(self.kernel.CloseHandle.call_count,count);self.assertIs(t.closer.error,failure)
        self.assertIsNone(t.keeper.completion);self.assertFalse(self.ad.streams['stdout'].closed)

    def test_clock_expiry_before_pipe_creation_does_not_start_native(self):
        self.clock.return_value=110.0;t=self.transport()
        with self.assertRaises(git.owner.UnreapedJob):t.start()
        self.assertEqual(t.reason,'time_limit');self.kernel.CreatePipe.assert_not_called()

    def test_rebind_preserves_prior_transport_and_starts_no_pipe(self):
        first=self.transport()
        with self.assertRaises(git.owner.UnreapedJob) as caught:self.transport()
        self.assertIs(caught.exception.pipe_transport.previous_transport,first)
        self.kernel.CreatePipe.assert_not_called()

    def test_policy_failure_retains_inputs_before_file_or_native_work(self):
        failure=KeyboardInterrupt('policy');self.policy_read.side_effect=failure
        with self.assertRaises(git.owner.UnreapedJob) as caught:self.transport()
        t=caught.exception.pipe_transport;self.assertIs(t.original_inputs[1],self.policy)
        self.assertIs(t.error,failure);self.assertIs(t.stdin,self.stdin)
        self.kernel.CreatePipe.assert_not_called()

    def test_changed_completion_handles_cannot_replace_original_named_close(self):
        t=self.ready();t.close_once();before=list(self.closed)
        t.keeper.completion['closed_handles']['thread']=34
        t.keeper.io_closed['core_handles']['thread']=34
        with self.assertRaises(git.owner.UnreapedJob):self.ad.checkpoint()
        self.assertEqual(self.closed,before);self.wait.assert_called_once()
        self.assertEqual(t.keeper.closed['thread'],33)
