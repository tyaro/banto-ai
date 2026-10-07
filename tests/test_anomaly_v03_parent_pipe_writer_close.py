"""Raw parent writer close/EOF ownership; native APIs remain stubbed."""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_preformal_job_tree_owner as owner
from banto_ai import anomaly_v03_preformal_owned_git_job as git
from banto_ai import anomaly_v03_preformal_child_git_keeper as keepers
from tests import test_anomaly_v03_spawn_io_handoff as prior


class ParentPipeWriterCloseTests(unittest.TestCase):
    def setUp(self):
        prior.SpawnIOHandoffTests.setUp(self)
        self.writers={'stdout':owner.NativePipeWriter(104),'stderr':owner.NativePipeWriter(105)}
        self.streams=[self.streams[0],self.writers['stdout'],self.writers['stderr']]
        self.held=owner.SpawnIOOwner(read_handles={'stdout':74,'stderr':75},
                                   sinks=self.sinks,writers=self.writers)

    def spawn(self):
        return owner._spawn_cli(self.kernel,['fixture'],'root',*self.streams,spawn_io=self.held)

    def spools(self, foreign=None):
        return {name:git.BoundedGitSpool(foreign if name=='stdout' and foreign is not None else sink,
            operation='source_blob',output=name,maximum_stored_bytes=64,
            checkpoint=lambda:None,sync=lambda:None) for name,sink in self.sinks.items()}

    def close(self,checkpoint=None):
        return self.held.close_parent_writers(checkpoint=checkpoint or (lambda:None))

    def test_spawn_duplicates_original_raw_writers_without_file_descriptor_wrappers(self):
        self.assertEqual(self.spawn(),(11,22,33,44))
        self.assertEqual([call.args[1] for call in self.kernel.DuplicateHandle.call_args_list],[100,104,105])
        self.assertEqual(self.held.native_write_handles,{'stdout':104,'stderr':105})
        self.assertEqual(self.closed,[61,62,63]);self.assertFalse(hasattr(self.writers['stdout'],'fileno'))

    def test_close_returns_observed_handles_and_cached_copy_without_native_retry(self):
        self.spawn();result=self.close()
        self.assertEqual(self.closed,[61,62,63,104,105])
        self.assertEqual(result['closed_handles'],{'stdout':104,'stderr':105})
        self.assertFalse(result['io_released']);self.assertFalse(result['parent_ack_authorized'])
        result['closed_handles'].clear();self.assertEqual(self.close()['closed_handles'],{'stdout':104,'stderr':105})
        self.assertEqual(self.closed,[61,62,63,104,105])
        self.assertEqual(self.held.writer_close_events['stdout'],{'api':'CloseHandle','handle':104,'return':1})

    def test_known_false_close_keeps_failed_and_unattempted_writer_and_no_retry(self):
        self.spawn();self.close_false={104}
        with self.assertRaises(owner.UnreapedJob) as raised:self.close()
        self.assertIs(raised.exception,self.held.native)
        self.assertEqual(self.held.writer_close_pending['return'],False)
        self.assertEqual(self.held.writer_close_pending['last_error'],5)
        self.assertEqual(self.held.native_write_handles,{'stdout':104,'stderr':105})
        self.assertEqual(self.closed,[61,62,63,104])
        with self.assertRaises(owner.UnreapedJob):self.close()
        self.assertEqual(self.closed,[61,62,63,104])

    def test_unknown_second_close_keeps_first_event_and_original_unknown_handle(self):
        self.spawn();error=KeyboardInterrupt('Close')
        def native_close(handle):
            self.closed.append(handle)
            if handle==105:raise error
            return True
        self.kernel.CloseHandle=Mock(side_effect=native_close)
        with self.assertRaises(owner.UnreapedJob) as raised:self.close()
        self.assertIs(raised.exception,self.held.native);self.assertIs(self.held.writer_close_error,error)
        self.assertEqual(self.held.writer_close_events['stdout']['handle'],104)
        self.assertEqual(self.held.writer_close_pending['handle'],105)
        self.assertIsNone(self.held.writer_close_pending['return'])
        with self.assertRaises(owner.UnreapedJob):self.close()
        self.assertEqual(self.closed,[61,62,63,104,105])

    def test_checkpoint_interrupt_after_close_keeps_native_return_before_any_next_close(self):
        self.spawn();error=KeyboardInterrupt('checkpoint');checkpoint=Mock(side_effect=[None,error])
        with self.assertRaises(owner.UnreapedJob):self.close(checkpoint)
        self.assertIs(self.held.writer_close_error,error)
        self.assertEqual(self.held.writer_close_pending['return'],True)
        self.assertEqual(self.held.writer_close_events['stdout']['handle'],104)
        self.assertEqual(self.closed,[61,62,63,104])

    def test_stream_close_or_release_metadata_cannot_enable_raw_handle_close(self):
        self.held=owner.SpawnIOOwner(read_handles={'stdout':74,'stderr':75},sinks=self.sinks,
            writers={'stdout':SimpleNamespace(fileno=lambda:1,closed=True),
                     'stderr':SimpleNamespace(fileno=lambda:2,closed=True)})
        self.held.enter(self.kernel,self.streams[0],*self.held.writers.values())
        self.held.released=True
        with self.assertRaises(owner.UnreapedJob):self.close()
        self.assertEqual(self.closed,[])

    def test_changed_raw_writer_handle_is_rejected_before_close_and_original_kept(self):
        self.spawn();self.writers['stdout'].handle=999
        with self.assertRaises(owner.UnreapedJob):self.close()
        self.assertEqual(self.closed,[61,62,63])
        self.assertEqual(self.held.native_write_handles['stdout'],104)

    def test_output_binding_uses_same_native_core_readers_and_original_sinks(self):
        self.spawn();spools=self.spools()
        held=git.GitOutputOwner.from_spawn(self.held,spools=spools,checkpoint=lambda:None)
        self.assertIs(held.native_owner,self.held.native);self.assertIs(held.spawn_io_owner,self.held)
        self.assertEqual(held.read_handles,self.held.read_handles)
        self.assertIs(held.spools['stdout'].stream,self.sinks['stdout'])

    def test_foreign_sink_binding_keeps_original_and_foreign_resources_without_read(self):
        self.spawn();foreign=prior.io.BytesIO();self.addCleanup(foreign.close)
        with self.assertRaises(owner.UnreapedJob) as raised:
            git.GitOutputOwner.from_spawn(self.held,spools=self.spools(foreign),checkpoint=lambda:None)
        self.assertIs(raised.exception,self.held.native)
        self.assertIs(self.held.native.git_output_owner.spools['stdout'].stream,foreign)
        self.assertIs(self.held.sinks['stdout'],self.sinks['stdout'])

    def test_closed_parent_writers_and_root_exit_still_cannot_close_core(self):
        self.spawn();self.close();native=self.held.native
        child=SimpleNamespace(stopped=False,hold_owner=Mock())
        keeper=keepers.ChildGitKeeper(native,child=child,lease=0)
        identity={'pid':44,'creation_time_100ns':111};identity['start_token']=keepers.v.canonical_sha256(identity)
        before=list(self.closed)
        with patch.object(owner,'_kernel',return_value=self.kernel),patch.object(keepers,'_creation',return_value=identity):
            self.assertIsNone(keeper.reconcile_once());self.assertIsNone(keeper.reconcile_once())
        self.assertEqual(self.closed,before);self.assertIsNone(keeper.completion);self.wait.assert_called_once()

    def test_closed_writers_then_observed_eof_keep_same_native_read_handle_and_sink(self):
        self.spawn();self.close()
        output=git.GitOutputOwner.from_spawn(self.held,spools=self.spools(),checkpoint=lambda:None)
        self.kernel.PeekNamedPipe=Mock(return_value=0);self.kernel.ReadFile=Mock()
        readers={name:lambda amount,n=name:self.sinks[n].getvalue()[:amount] for name in self.sinks}
        reader=git.GitPipeReader(output,kernel=self.kernel,readback=readers)
        with patch.object(owner.ctypes,'get_last_error',return_value=109,create=True):
            self.assertEqual(reader.read_once('stdout'),'eof')
        self.assertEqual(output.read_handles['stdout'],74);self.assertFalse(self.sinks['stdout'].closed)
        self.assertIs(output.native_owner,self.held.native);self.kernel.ReadFile.assert_not_called()
