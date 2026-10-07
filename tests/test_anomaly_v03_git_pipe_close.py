"""Named read close and real FileIO sink closure; native observations are stubs."""
import io
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_preformal_owned_git_job as git
from banto_ai import anomaly_v03_preformal_job_tree_owner as owner
from banto_ai import anomaly_v03_preformal_child_git_keeper as keepers
from tests import test_anomaly_v03_parent_pipe_writer_close as prior


class GitPipeCloseTests(unittest.TestCase):
    def setUp(self):
        prior.ParentPipeWriterCloseTests.setUp(self)
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.files = {name:Path(self.tmp.name)/name for name in ('stdout','stderr')}
        self.sinks = {name:io.FileIO(path,'xb') for name,path in self.files.items()}
        for sink in self.sinks.values(): self.addCleanup(sink.close)
        self.held = owner.SpawnIOOwner(read_handles={'stdout':74,'stderr':75},
                                      sinks=self.sinks,writers=self.writers)
        self.checkpoint = Mock()
        owner._spawn_cli(self.kernel,['fixture'],'root',*self.streams,spawn_io=self.held)
        self.held.close_parent_writers(checkpoint=self.checkpoint)
        self.spools = {name:git.BoundedGitSpool(sink,operation='source_blob',output=name,
            maximum_stored_bytes=64,checkpoint=self.checkpoint,
            sync=lambda s=sink:os.fsync(s.fileno())) for name,sink in self.sinks.items()}
        self.output = git.GitOutputOwner.from_spawn(self.held,spools=self.spools,checkpoint=self.checkpoint)
        self.kernel.PeekNamedPipe = Mock(return_value=0); self.kernel.ReadFile = Mock()
        self.readback = {name:lambda amount,n=name:self.files[n].read_bytes()[:amount]
                         for name in self.files}
        self.reader = git.GitPipeReader(self.output,kernel=self.kernel,readback=self.readback)
        with patch.object(owner.ctypes,'get_last_error',return_value=109,create=True):
            self.reader.read_once('stdout'); self.reader.read_once('stderr')
        self.keeper = keepers.ChildGitKeeper(self.held.native,
            child=SimpleNamespace(stopped=False,hold_owner=Mock()),lease=0)
        identity={'pid':44,'creation_time_100ns':111}
        identity['start_token']=keepers.v.canonical_sha256(identity)
        with patch.object(keepers,'_creation',return_value=identity):
            self.assertIsNone(self.keeper.reconcile_once())
        self.before = list(self.closed); self.checkpoint.reset_mock()

    def closer(self): return git.GitPipeClose(self.reader,keeper=self.keeper)

    def test_named_read_and_real_sink_closes_cache_events_without_native_replay(self):
        closer=self.closer();result=closer.close_once()
        self.assertEqual(self.closed,self.before+[74,75])
        self.assertTrue(all(s.closed for s in self.sinks.values()))
        self.assertEqual(result['read_closed']['stdout'],{'api':'CloseHandle','handle':74,'return':1})
        self.assertEqual(result['sink_closed']['stdout']['api'],'FileIO.close')
        self.assertEqual(result['sink_closed']['stdout']['raw_pin']['bytes'],0)
        result['read_closed'].clear()
        self.assertEqual(set(closer.close_once()['read_closed']),{'stdout','stderr'})
        self.assertEqual(self.closed,self.before+[74,75]); self.wait.assert_called_once()
        self.assertFalse(closer.result['io_released']);self.assertFalse(closer.result['parent_ack_authorized'])

    def test_missing_eof_is_rejected_before_any_close(self):
        del self.reader.eof['stderr']; closer=self.closer()
        with self.assertRaises(owner.UnreapedJob):closer.close_once()
        self.assertEqual(self.closed,self.before);self.assertFalse(self.sinks['stdout'].closed)

    def test_missing_cached_native_reap_is_rejected_without_reap_or_close(self):
        self.keeper.reaped=None; closer=self.closer()
        with self.assertRaises(owner.UnreapedJob):closer.close_once()
        self.wait.assert_called_once();self.assertEqual(self.closed,self.before)

    def test_parent_writer_metadata_cannot_replace_observed_close_events(self):
        self.held.writer_close_events={};self.held.released=True;closer=self.closer()
        with self.assertRaises(owner.UnreapedJob):closer.close_once()
        self.assertEqual(self.closed,self.before)

    def test_non_fileio_sink_is_retained_but_cannot_create_close_observation(self):
        original=self.sinks['stdout'];foreign=io.BytesIO();self.addCleanup(foreign.close)
        self.spools['stdout'].stream=foreign
        with self.assertRaises(owner.UnreapedJob):self.closer()
        self.assertIs(self.output.pipe_close.streams['stdout'],foreign)
        self.assertIs(self.held.sinks['stdout'],original);self.assertFalse(original.closed)

    def test_changed_disk_raw_is_retained_before_read_close(self):
        self.files['stdout'].write_bytes(b'changed');closer=self.closer()
        with self.assertRaises(owner.UnreapedJob) as raised:closer.close_once()
        self.assertIs(raised.exception,self.held.native)
        self.assertEqual(closer.pending['readback_raw'],b'c');self.assertEqual(self.closed,self.before)

    def test_known_false_read_close_keeps_failed_and_unattempted_resources_no_retry(self):
        self.close_false={74};closer=self.closer()
        with self.assertRaises(owner.UnreapedJob):closer.close_once()
        self.assertFalse(closer.pending['return']);self.assertEqual(closer.pending['last_error'],5)
        with self.assertRaises(owner.UnreapedJob):closer.close_once()
        self.assertEqual(self.closed,self.before+[74]);self.assertFalse(self.sinks['stdout'].closed)

    def test_unknown_second_read_close_keeps_first_event_and_unknown_return(self):
        error=KeyboardInterrupt('Close')
        def close(handle):
            self.closed.append(handle)
            if handle==75:raise error
            return True
        self.kernel.CloseHandle=Mock(side_effect=close);closer=self.closer()
        with self.assertRaises(owner.UnreapedJob):closer.close_once()
        self.assertIs(closer.error,error);self.assertIsNone(closer.pending['return'])
        self.assertEqual(closer.read_events['stdout']['handle'],74)
        with self.assertRaises(owner.UnreapedJob):closer.close_once()
        self.assertEqual(self.closed,self.before+[74,75])

    def test_checkpoint_interrupt_after_read_close_keeps_actual_return(self):
        closer=self.closer();error=KeyboardInterrupt('checkpoint')
        self.checkpoint.side_effect=[None,None,None,error]
        with self.assertRaises(owner.UnreapedJob):closer.close_once()
        self.assertIs(closer.error,error);self.assertTrue(closer.pending['return'])
        self.assertEqual(closer.read_events['stdout']['handle'],74)
        self.assertEqual(self.closed,self.before+[74])

    def test_sink_sync_error_keeps_stream_and_original_core_after_read_closes(self):
        error=OSError('fsync');self.spools['stdout'].sync=Mock(side_effect=error);closer=self.closer()
        with self.assertRaises(owner.UnreapedJob):closer.close_once()
        self.assertIs(closer.error,error);self.assertIs(closer.pending['stream'],self.sinks['stdout'])
        self.assertFalse(self.sinks['stdout'].closed);self.assertEqual(self.closed,self.before+[74,75])
        with self.assertRaises(owner.UnreapedJob):closer.close_once()
        self.spools['stdout'].sync.assert_called_once()

    def test_post_close_raw_failure_keeps_close_events_and_does_not_reclose(self):
        error=OSError('readback');closer=self.closer()
        self.reader.readback['stdout']=Mock(side_effect=[b'',error])
        with self.assertRaises(owner.UnreapedJob):closer.close_once()
        self.assertIs(closer.error,error);self.assertEqual(set(closer.sink_events),{'stdout','stderr'})
        self.assertTrue(all(s.closed for s in self.sinks.values()))
        with self.assertRaises(owner.UnreapedJob):closer.close_once()
        self.assertEqual(self.closed,self.before+[74,75])

    def test_completed_io_observation_does_not_authorize_core_close_lease_or_ack(self):
        closer=self.closer();closer.close_once();self.output.released=True
        self.assertIsNone(self.keeper.reconcile_once());self.assertIsNone(self.keeper.completion)
        self.wait.assert_called_once();self.assertEqual(self.closed,self.before+[74,75])
        with self.assertRaises(owner.UnreapedJob):self.reader.read_once('stdout')

    def test_foreign_keeper_is_held_and_rejected_before_close(self):
        foreign=SimpleNamespace(original=self.held.native,reaped=self.keeper.reaped)
        with self.assertRaises(owner.UnreapedJob):git.GitPipeClose(self.reader,keeper=foreign)
        self.assertIs(self.output.pipe_close.keeper,foreign);self.assertEqual(self.closed,self.before)
