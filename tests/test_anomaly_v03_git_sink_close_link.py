"""Original close events plus real nonempty raw; native APIs are fake."""
import ctypes
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_preformal_owned_git_job as git
from banto_ai import anomaly_v03_preformal_child_git_keeper as keepers
from tests import test_anomaly_v03_git_sink_spawn_handoff as prior


class GitSinkCloseLinkTests(unittest.TestCase):
    def setUp(self):
        prior.GitSinkSpawnHandoffTests.setUp(self)
        self.ad.bind_spawn(self.creator)
        prior.GitSinkSpawnHandoffTests.spawn_bound(self)
        self.output=self.ad.bind_output()
        self.ad.spawn_io.close_parent_writers(checkpoint=self.ad.checkpoint)
        readers={name:lambda amount,n=name:self.ad.paths[n].read_bytes()[:amount]
                 for name in self.ad.paths}
        def peek(handle,buffer,amount,count,available,left):
            available._obj.value=3
            return 1
        def read(handle,buffer,amount,count,overlapped):
            ctypes.memmove(buffer,b'abc',3);count._obj.value=3
            return 1
        self.kernel.PeekNamedPipe=Mock(side_effect=peek);self.kernel.ReadFile=Mock(side_effect=read)
        self.reader=git.GitPipeReader(self.output,kernel=self.kernel,readback=readers)
        self.assertEqual(self.reader.read_once('stdout'),'data')
        self.kernel.PeekNamedPipe=Mock(return_value=0)
        with patch.object(git.owner.ctypes,'get_last_error',return_value=109,create=True):
            self.reader.read_once('stdout');self.reader.read_once('stderr')
        self.keeper=keepers.ChildGitKeeper(self.ad.native,
            child=SimpleNamespace(stopped=False,hold_owner=Mock()),lease=0)
        identity={'pid':44,'creation_time_100ns':111}
        identity['start_token']=keepers.v.canonical_sha256(identity)
        with patch.object(keepers,'_creation',return_value=identity):
            self.assertIsNone(self.keeper.reconcile_once())
        self.closer=git.GitPipeClose(self.reader,keeper=self.keeper)
        self.before=list(self.closed)

    def complete(self):
        self.ad.bind_io_close(self.closer)
        return self.closer.close_once()

    def test_original_close_nonempty_raw_and_cache_without_native_replay(self):
        result=self.complete();self.ad.checkpoint();self.closer.close_once()
        self.assertEqual(self.closed,self.before+[74,75]);self.wait.assert_called_once()
        self.assertEqual(self.ad.closed_observations['stdout']['raw'],b'abc')
        self.assertIs(self.keeper.io_close_adapter,self.closer)
        self.assertFalse(result['io_released']);self.assertFalse(result['parent_ack_authorized'])
        self.assertIsNone(self.keeper.completion)

    def test_intermediate_first_sink_checkpoint_does_not_close_core_or_ack(self):
        seen=[]
        def checkpoint():
            if len(self.closer.sink_events)==1:
                seen.append((self.keeper.completion,list(self.closed)))
        self.ad.shared_checkpoint=checkpoint;self.complete()
        self.assertTrue(seen)
        self.assertTrue(all(value[0] is None and value[1]==self.before+[74,75] for value in seen))
        self.assertEqual(set(self.ad.closed_observations),{'stdout','stderr'})

    def test_closed_metadata_without_original_binding_is_rejected(self):
        self.ad.streams['stdout'].close()
        with self.assertRaises(git.owner.UnreapedJob) as raised:self.ad.checkpoint()
        self.assertIs(raised.exception,self.ad.native)
        self.assertEqual(self.closed,self.before)

    def test_declared_close_adapter_is_retained_but_cannot_authorize(self):
        declared=SimpleNamespace(started=True,sink_events={'stdout':{'return':None}})
        with self.assertRaises(git.owner.UnreapedJob):self.ad.bind_io_close(declared)
        self.assertIs(self.ad.close_adapter,declared);self.assertEqual(self.closed,self.before)

    def test_missing_actual_sink_event_after_close_is_rejected(self):
        self.complete();del self.closer.sink_events['stdout']
        with self.assertRaises(git.owner.UnreapedJob):self.ad.checkpoint()
        self.assertEqual(self.closed,self.before+[74,75])

    def test_foreign_fd_close_event_cannot_match_original_file(self):
        self.complete();self.closer.sink_events['stdout']['fd']+=1
        with self.assertRaises(git.owner.UnreapedJob):self.ad.checkpoint()
        self.assertEqual(self.closed,self.before+[74,75])

    def test_changed_file_identity_in_event_is_rejected(self):
        self.complete();self.closer.sink_events['stdout']['file_identity']['inode']+=1
        with self.assertRaises(git.owner.UnreapedJob):self.ad.checkpoint()
        self.assertEqual(self.closed,self.before+[74,75])

    def test_same_size_raw_change_keeps_original_and_changed_block(self):
        self.complete();self.ad.paths['stdout'].write_bytes(b'abd')
        with self.assertRaises(git.owner.UnreapedJob):self.ad.checkpoint()
        self.assertEqual(self.ad.closed_observations['stdout']['raw'],b'abc')
        self.assertEqual(self.ad.close_pending['raw'],b'abd')
        self.assertEqual(self.closed,self.before+[74,75])

    def test_post_close_clock_interrupt_retains_original_without_reclose(self):
        self.complete();failure=KeyboardInterrupt('clock')
        self.ad.shared_checkpoint=Mock(side_effect=failure)
        with self.assertRaises(git.owner.UnreapedJob) as raised:self.ad.checkpoint()
        self.assertIs(raised.exception,self.ad.native);self.assertIs(self.ad.error,failure)
        self.assertEqual(self.closed,self.before+[74,75])

    def test_close_rebind_preserves_original_and_rejected_adapter(self):
        self.ad.bind_io_close(self.closer);rejected=object()
        with self.assertRaises(git.owner.UnreapedJob):self.ad.bind_io_close(rejected)
        self.assertIs(self.ad.close_adapter,self.closer)
        self.assertIs(self.ad.rejected_close_adapter,rejected);self.assertEqual(self.closed,self.before)

    def test_unknown_read_close_refuses_followup_admission_without_new_io(self):
        self.ad.bind_io_close(self.closer);self.close_error=OSError('Close')
        original=self.kernel.CloseHandle.side_effect
        def uncertain(handle):
            result=original(handle)
            if handle==74:raise self.close_error
            return result
        self.kernel.CloseHandle.side_effect=uncertain
        with self.assertRaises(git.owner.UnreapedJob):self.closer.close_once()
        before=list(self.closed)
        with self.assertRaises(git.owner.UnreapedJob):self.ad.checkpoint()
        self.assertEqual(self.closed,before);self.assertFalse(self.ad.streams['stdout'].closed)
        self.assertIs(self.ad.error,self.close_error)

    def test_first_sink_post_close_interrupt_keeps_event_stream_and_core(self):
        failure=KeyboardInterrupt('first sink checkpoint')
        def checkpoint():
            if len(self.closer.sink_events)==1:raise failure
        self.ad.shared_checkpoint=checkpoint;self.ad.bind_io_close(self.closer)
        with self.assertRaises(git.owner.UnreapedJob) as raised:self.closer.close_once()
        self.assertIs(raised.exception,self.ad.native)
        self.assertEqual(self.closer.sink_events['stdout']['fd'],self.ad.file_descriptors['stdout'])
        self.assertTrue(self.ad.streams['stdout'].closed);self.assertFalse(self.ad.streams['stderr'].closed)
        self.assertIs(self.ad.error,failure);self.assertIsNone(self.keeper.completion)
        self.assertEqual(self.closed,self.before+[74,75])

    def test_pending_raw_cannot_use_prior_close(self):
        self.complete();self.output.pending={'raw':b'pending'}
        with self.assertRaises(git.owner.UnreapedJob):self.ad.checkpoint()
        self.assertEqual(self.output.pending['raw'],b'pending')
        self.assertEqual(self.closed,self.before+[74,75])
