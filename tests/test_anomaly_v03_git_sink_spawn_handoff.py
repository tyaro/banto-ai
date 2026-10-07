"""Real sink ownership and fake pipe/spawn; no real Win API or worker."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from banto_ai import anomaly_v03_preformal_owned_git_job as git
from tests import test_anomaly_v03_spawn_io_handoff as prior


class GitSinkSpawnHandoffTests(unittest.TestCase):
    def setUp(self):
        prior.SpawnIOHandoffTests.setUp(self)
        temporary=tempfile.TemporaryDirectory(prefix='banto-sink-spawn-')
        self.addCleanup(temporary.cleanup)
        root=Path(temporary.name)/'outer';root.mkdir()
        call={'lease':0,'phase':'pre','operation':'source_blob',
            'source_path':'src/banto_ai/anomaly_v03.py',
            'expected_output_pin':{'bytes':48839,'sha256':'a'*64},
            'raw_inventory':{'receipt.json':16384,'stdout.bin':32,'stderr.bin':16}}
        self.ad=git.GitSinkAdmission(root=root,
            root_identity=(root.stat().st_dev,root.stat().st_ino),revision='b'*40,
            call=call,checkpoint=lambda:None).create()
        for stream in self.ad.streams.values():self.addCleanup(stream.close)
        pairs=iter([(74,104),(75,105)])
        def created(read,write,security,hint):
            read._obj.value,write._obj.value=next(pairs)
            return 1
        self.kernel.CreatePipe=Mock(side_effect=created)
        self.creator=git.owner.NativeGitPipes(self.kernel,checkpoint=lambda:None)
        self.creator.create()

    def bind(self):return self.ad.bind_spawn(self.creator)

    def spawn_bound(self):
        return git.owner._spawn_cli(self.kernel,['fixture'],'fixture-root',
            self.streams[0],self.creator.writers['stdout'],self.creator.writers['stderr'],
            spawn_io=self.ad.spawn_io)

    def test_both_bootstraps_retain_same_spawn_and_exact_sinks(self):
        descriptor=self.bind()
        self.assertIs(self.ad.native,descriptor.native)
        self.assertIs(self.ad.bootstrap.sink_successor,descriptor.native)
        self.assertIs(self.creator.native.pipe_successor,descriptor.native)
        self.assertIs(self.creator.native.git_sink_admission,self.ad)
        self.assertIs(descriptor.git_sink_admission,self.ad)
        self.assertIs(descriptor.sinks['stdout'],self.ad.streams['stdout'])
        self.assertIsNone(descriptor.native.job)

    def test_original_spawn_output_uses_same_core_streams_spools(self):
        self.bind();self.assertEqual(self.spawn_bound(),(11,22,33,44))
        output=self.ad.bind_output()
        self.assertIs(output.native_owner,self.ad.native)
        self.assertIs(output.spawn_io_owner,self.ad.spawn_io)
        self.assertIs(output.spools['stdout'],self.ad.spools['stdout'])
        self.assertEqual(output.read_handles,{'stdout':74,'stderr':75})
        self.assertEqual(self.kernel.CreatePipe.call_count,2)
        self.assertEqual(self.closed,[61,62,63])

    def test_output_before_spawn_is_refused_with_original_descriptor(self):
        descriptor=self.bind()
        with self.assertRaises(git.owner.UnreapedJob) as raised:self.ad.bind_output()
        self.assertIs(raised.exception,descriptor.native)
        self.assertIs(raised.exception.git_sink_admission,self.ad)
        self.assertFalse(self.ad.streams['stdout'].closed)
        self.assertIsNone(descriptor.native.job)

    def test_rebind_keeps_prior_spawn_and_rejected_creator_without_pipe_retry(self):
        descriptor=self.bind();foreign=object()
        with self.assertRaises(git.owner.UnreapedJob) as raised:self.ad.bind_spawn(foreign)
        self.assertIs(raised.exception,descriptor.native)
        self.assertIs(self.ad.creator,self.creator);self.assertIs(self.ad.rejected_creator,foreign)
        self.assertEqual(self.kernel.CreatePipe.call_count,2)

    def test_invalid_creator_retained_before_root_clock_io(self):
        rejected=object();self.ad.shared_checkpoint=Mock(side_effect=AssertionError('clock'))
        with self.assertRaises(git.owner.UnreapedJob) as raised:self.ad.bind_spawn(rejected)
        self.assertIs(raised.exception,self.ad.bootstrap);self.assertIs(self.ad.creator,rejected)
        self.ad.shared_checkpoint.assert_not_called()

    def test_pre_bind_clock_interruption_retains_original_pipe_and_sink_owner(self):
        failure=KeyboardInterrupt('clock');self.ad.shared_checkpoint=Mock(side_effect=failure)
        with self.assertRaises(git.owner.UnreapedJob) as raised:self.bind()
        self.assertIs(raised.exception,self.creator.native)
        self.assertIs(raised.exception.git_sink_admission,self.ad)
        self.assertIs(self.ad.error,failure);self.assertIsNone(self.creator.spawn_io)
        self.assertEqual(self.creator.read_handles,{'stdout':74,'stderr':75})
        self.assertFalse(self.ad.streams['stdout'].closed)

    def test_post_bind_clock_interruption_keeps_exact_new_spawn(self):
        failure=OSError('post-bind clock')
        def checkpoint():
            if self.ad.spawn_io is not None:raise failure
        self.ad.shared_checkpoint=checkpoint
        with self.assertRaises(git.owner.UnreapedJob) as raised:self.bind()
        self.assertIs(raised.exception,self.creator.spawn_io.native)
        self.assertIs(self.ad.spawn_io,self.creator.spawn_io)
        self.assertIs(self.ad.error,failure)

    def test_spawn_cleanup_failure_preserves_original_core_and_admission(self):
        descriptor=self.bind();self.deleted_error=KeyboardInterrupt('Delete')
        with self.assertRaises(git.owner.UnreapedJob) as raised:self.spawn_bound()
        self.assertIs(raised.exception,descriptor.native)
        self.assertIs(raised.exception.git_sink_admission,self.ad)
        self.assertTrue(raised.exception.attribute_list_cleanup_pending)
        self.assertEqual((raised.exception.job,raised.exception.process,raised.exception.thread),(11,22,33))
        self.assertFalse(self.ad.streams['stdout'].closed);self.assertEqual(self.closed,[])

    def test_output_post_checkpoint_failure_retains_output_before_io(self):
        self.bind();self.spawn_bound();failure=KeyboardInterrupt('output clock')
        self.ad.shared_checkpoint=Mock(side_effect=failure)
        with self.assertRaises(git.owner.UnreapedJob) as raised:self.ad.bind_output()
        self.assertIs(raised.exception,self.ad.spawn_io.native)
        self.assertIs(raised.exception.git_output_owner,self.ad.output_owner)
        self.assertIs(raised.exception.sink_error,failure)
        self.assertFalse(self.ad.streams['stderr'].closed)

    def test_previous_native_admission_is_retained_on_conflict(self):
        previous=object();self.creator.native.git_sink_admission=previous
        with self.assertRaises(git.owner.UnreapedJob) as raised:self.bind()
        self.assertIs(raised.exception,self.creator.native)
        self.assertIs(self.ad.previous_native_admission,previous)
        self.assertIs(self.ad.native_bindings[0][1],previous)
        self.assertIsNone(self.creator.spawn_io)

    def test_output_rebind_refuses_and_retains_original_output_owner(self):
        self.bind();self.spawn_bound();output=self.ad.bind_output()
        with self.assertRaises(git.owner.UnreapedJob) as raised:self.ad.bind_output()
        self.assertIs(raised.exception,self.ad.native)
        self.assertIs(raised.exception.git_output_owner,output)
        self.assertIs(self.ad.output_owner,output)
        self.assertEqual(self.closed,[61,62,63]);self.assertEqual(self.kernel.CreatePipe.call_count,2)
