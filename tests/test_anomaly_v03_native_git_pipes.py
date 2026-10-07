"""Pipe creation buffers/owner handoff, with fake Win API only."""
import io
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from banto_ai import anomaly_v03_preformal_job_tree_owner as owner
from tests import test_anomaly_v03_spawn_io_handoff as prior


class NativeGitPipesTests(unittest.TestCase):
    def setUp(self):
        prior.SpawnIOHandoffTests.setUp(self)
        self.pipe_calls=[];self.pipe_return=True;self.pipe_error=None
        self.pipe_values=[(74,104),(75,105)]
        def create(read,write,security,size):
            self.pipe_calls.append((security,size))
            pair=self.pipe_values[len(self.pipe_calls)-1]
            read._obj.value,write._obj.value=pair
            if self.pipe_error is not None:raise self.pipe_error
            return self.pipe_return
        self.kernel.CreatePipe=Mock(side_effect=create)
        self.checkpoint=Mock()
        self.creator=owner.NativeGitPipes(self.kernel,checkpoint=self.checkpoint)

    def test_success_records_original_outputs_and_caches_without_creation_replay(self):
        result=self.creator.create()
        self.assertEqual(result['stdout']['read'],74);self.assertEqual(result['stderr']['write'],105)
        self.assertEqual(self.creator.read_handles,{'stdout':74,'stderr':75})
        self.assertFalse(self.creator.pending['out_parameters_indeterminate'])
        result['stdout']['read']=999
        self.assertEqual(self.creator.create()['stdout']['read'],74)
        self.assertEqual(self.kernel.CreatePipe.call_count,2);self.assertEqual(self.closed,[])

    def test_null_security_disables_inheritance_and_buffer_hint_is_not_a_hard_bound(self):
        result=self.creator.create();self.assertEqual(self.pipe_calls,[(None,4096),(None,4096)])
        self.assertTrue(all(event['kernel_buffer_bound_proven'] is False for event in result.values()))
        self.assertFalse(hasattr(self.creator.writers['stdout'],'fileno'))

    def test_false_first_create_keeps_indeterminate_buffers_without_any_close_or_retry(self):
        self.pipe_return=False
        with self.assertRaises(owner.UnreapedJob) as raised:self.creator.create()
        self.assertIs(raised.exception,self.creator.native)
        self.assertEqual(self.creator.pending['observed_values'],{'read':74,'write':104})
        self.assertTrue(self.creator.pending['out_parameters_indeterminate'])
        self.assertEqual(self.creator.pending['last_error'],5);self.assertEqual(self.creator.events,{})
        with self.assertRaises(owner.UnreapedJob):self.creator.create()
        self.assertEqual(self.kernel.CreatePipe.call_count,1);self.assertEqual(self.closed,[])

    def test_false_second_create_keeps_first_owned_pair_and_second_indeterminate_outputs(self):
        original=self.kernel.CreatePipe.side_effect
        def create(*args):
            original(*args);return len(self.pipe_calls)==1
        self.kernel.CreatePipe.side_effect=create
        with self.assertRaises(owner.UnreapedJob):self.creator.create()
        self.assertEqual(set(self.creator.events),{'stdout'})
        self.assertEqual(self.creator.read_handles,{'stdout':74})
        self.assertTrue(self.creator.pending['out_parameters_indeterminate'])
        self.assertEqual(self.creator.pending['observed_values'],{'read':75,'write':105})
        self.assertEqual(self.closed,[])

    def test_api_interrupt_keeps_original_mutated_output_buffers_and_missing_return(self):
        error=KeyboardInterrupt('CreatePipe');self.pipe_error=error
        with self.assertRaises(owner.UnreapedJob):self.creator.create()
        self.assertIs(self.creator.error,error);self.assertIsNone(self.creator.pending['return'])
        self.assertEqual(self.creator.pending['read'].value,74)
        self.assertEqual(self.creator.pending['write'].value,104)
        self.assertTrue(self.creator.pending['out_parameters_indeterminate']);self.assertEqual(self.closed,[])

    def test_pre_api_clock_failure_keeps_owner_without_creation(self):
        error=OSError('clock');self.checkpoint.side_effect=error
        with self.assertRaises(owner.UnreapedJob):self.creator.create()
        self.assertIs(self.creator.native.original_error,error);self.kernel.CreatePipe.assert_not_called()

    def test_post_api_clock_interrupt_keeps_success_position_before_next_creation(self):
        error=KeyboardInterrupt('clock');self.checkpoint.side_effect=[None,error]
        with self.assertRaises(owner.UnreapedJob):self.creator.create()
        self.assertEqual(self.creator.events['stdout']['return'],1)
        self.assertEqual(self.creator.read_handles,{'stdout':74})
        self.assertEqual(self.kernel.CreatePipe.call_count,1);self.assertEqual(self.closed,[])

    def test_alias_creation_outputs_are_retained_and_cannot_bind_spawn(self):
        self.pipe_values=[(74,104),(74,105)]
        with self.assertRaises(owner.UnreapedJob):self.creator.create()
        self.assertEqual(self.creator.events['stderr']['read'],74)
        with self.assertRaises(owner.UnreapedJob):self.creator.bind_spawn(self.sinks)
        self.assertIsNone(self.creator.spawn_io);self.assertEqual(self.closed,[])

    def test_bind_uses_original_raw_writers_and_retains_creator_with_actual_spawn_owner(self):
        self.creator.create();spawn=self.creator.bind_spawn(self.sinks)
        self.assertIs(spawn.native.pipe_creator,self.creator)
        self.assertIs(self.creator.native.pipe_successor,spawn.native)
        result=owner._spawn_cli(self.kernel,['fixture'],'root',self.streams[0],
            spawn.writers['stdout'],spawn.writers['stderr'],spawn_io=spawn)
        self.assertEqual(result,(11,22,33,44))
        self.assertEqual([call.args[1] for call in self.kernel.DuplicateHandle.call_args_list],[100,104,105])
        self.assertIs(spawn.native.pipe_creator,self.creator)

    def test_foreign_kernel_is_rejected_before_job_or_process_creation(self):
        self.creator.create();spawn=self.creator.bind_spawn(self.sinks)
        with self.assertRaises(owner.UnreapedJob) as raised:
            owner._spawn_cli(SimpleNamespace(),['fixture'],'root',self.streams[0],
                spawn.writers['stdout'],spawn.writers['stderr'],spawn_io=spawn)
        self.assertIs(raised.exception,spawn.native)
        owner._new_job.assert_not_called();self.kernel.CreateProcessW.assert_not_called()
        self.assertEqual(self.closed,[])

    def test_rebind_keeps_first_spawn_and_new_rejected_sinks_with_same_native_owner(self):
        self.creator.create();spawn=self.creator.bind_spawn(self.sinks)
        rejected={'stdout':io.BytesIO(),'stderr':io.BytesIO()}
        for sink in rejected.values():self.addCleanup(sink.close)
        with self.assertRaises(owner.UnreapedJob) as raised:self.creator.bind_spawn(rejected)
        self.assertIs(raised.exception,spawn.native);self.assertIs(self.creator.spawn_io,spawn)
        self.assertIs(self.creator.rejected_sinks,rejected);self.assertIs(spawn.sinks['stdout'],self.sinks['stdout'])

    def test_invalid_checkpoint_keeps_original_kernel_before_any_native_io(self):
        with self.assertRaises(owner.UnreapedJob) as raised:owner.NativeGitPipes(self.kernel,checkpoint=None)
        self.assertIs(raised.exception.pipe_creator.kernel,self.kernel)
        self.kernel.CreatePipe.assert_not_called();self.assertEqual(self.closed,[])
