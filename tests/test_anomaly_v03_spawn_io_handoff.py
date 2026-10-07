"""Opt-in spawn IO/core handoff; all native APIs/resources are stubs."""
import io
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_preformal_job_tree_owner as owner
from banto_ai import anomaly_v03_preformal_child_git_keeper as keepers
from tests import test_anomaly_v03_spawn_cleanup_owner as prior


class SpawnIOHandoffTests(unittest.TestCase):
    def setUp(self):
        # Reuse only the fake API setup, without importing/discovering old tests.
        prior.SpawnCleanupOwnerTests.setUp(self)
        self.streams=[SimpleNamespace(fileno=lambda n=n:n) for n in range(3)]
        self.sinks={'stdout':io.BytesIO(),'stderr':io.BytesIO()}
        for stream in self.sinks.values():self.addCleanup(stream.close)
        self.writers={'stdout':self.streams[1],'stderr':self.streams[2]}
        self.held=owner.SpawnIOOwner(read_handles={'stdout':74,'stderr':75},
                                   sinks=self.sinks,writers=self.writers)

    def spawn(self,held=None,**kw):
        return owner._spawn_cli(self.kernel,['fixture'],'fixture-root',*self.streams,
                               spawn_io=self.held if held is None else held,**kw)

    def test_success_keeps_original_core_io_and_returns_existing_tuple(self):
        self.assertEqual(self.spawn(),(11,22,33,44))
        native=self.held.native
        self.assertEqual((native.job,native.process,native.thread),(11,22,33))
        self.assertEqual(native.extra_handles,{})
        self.assertEqual(self.closed,[61,62,63])
        self.assertEqual(self.held.read_handles,{'stdout':74,'stderr':75})
        self.assertIs(self.held.sinks['stdout'],self.sinks['stdout'])
        self.assertEqual(self.held.binding,(self.kernel,*self.streams))
        self.assertIsNone(native.pending_duplicate);self.wait.assert_not_called()

    def test_delete_failure_keeps_same_core_io_and_attribute_buffer(self):
        self.deleted_error=KeyboardInterrupt('Delete')
        with self.assertRaises(owner.UnreapedJob) as raised:self.spawn()
        native=raised.exception;self.assertIs(native,self.held.native)
        self.assertIs(native.spawn_io_owner,self.held);self.assertIs(native.attributes,self.attribute)
        self.assertEqual(native.extra_handles,{'inherited_0':61,'inherited_1':62,'inherited_2':63})
        self.assertTrue(native.attribute_list_cleanup_pending);self.assertEqual(self.closed,[])
        self.assertIs(native.cleanup_error,self.deleted_error);self.wait.assert_not_called()

    def test_unknown_stdio_close_keeps_core_and_separate_io_without_reap(self):
        self.close_error=OSError('Close')
        with self.assertRaises(owner.UnreapedJob) as raised:self.spawn()
        native=raised.exception;self.assertIs(native,self.held.native)
        self.assertEqual(native.extra_handles,{'inherited_1':62,'inherited_2':63})
        self.assertEqual(native.unknown_close_handles,('inherited_1','inherited_2'))
        self.assertEqual(self.closed,[61,62]);self.wait.assert_not_called()
        self.assertEqual(self.held.read_handles,{'stdout':74,'stderr':75})

    def test_known_false_stdio_keeps_original_core_instead_of_legacy_close(self):
        self.close_false={62}
        with self.assertRaises(owner.UnreapedJob) as raised:self.spawn()
        self.assertIs(raised.exception,self.held.native)
        self.assertEqual(self.closed,[61,62,63]);self.wait.assert_not_called()
        self.kernel.TerminateJobObject.assert_not_called()
        self.assertEqual(self.held.native.extra_handles,{'inherited_1':62})
        self.assertIsInstance(self.held.native.cleanup_error,owner.UnclosedHandles)

    def test_body_failure_keeps_original_unassigned_root_and_write_streams(self):
        self.assigned=False
        with self.assertRaises(owner.UnreapedJob) as raised:self.spawn()
        self.assertIs(raised.exception,self.held.native)
        self.assertIsInstance(raised.exception.original_error,OSError)
        self.assertFalse(raised.exception.report['assignment_confirmed'])
        self.assertEqual((raised.exception.process,raised.exception.thread),(22,33))
        self.assertIs(self.held.binding[2],self.writers['stdout'])
        self.assertEqual(self.closed,[61,62,63]);self.wait.assert_not_called()

    def test_pre_job_failure_keeps_original_io_before_any_stdio_api(self):
        failure=KeyboardInterrupt('new Job')
        with patch.object(owner,'_new_job',side_effect=failure):
            with self.assertRaises(owner.UnreapedJob) as raised:self.spawn()
        self.assertIs(raised.exception,self.held.native);self.assertIs(raised.exception.original_error,failure)
        self.assertEqual(self.held.binding,(self.kernel,*self.streams))
        self.kernel.GetCurrentProcess.assert_not_called();self.assertIsNone(raised.exception.job)

    def test_secondary_new_job_owner_keeps_same_native_exception_and_io(self):
        secondary=owner.UnclosedHandles({'job':11},{})
        with patch.object(owner,'_new_job',side_effect=secondary):
            with self.assertRaises(owner.UnclosedHandles) as raised:self.spawn()
        self.assertIs(raised.exception,secondary);self.assertIs(secondary.spawn_io_owner,self.held)
        self.assertIs(self.held.secondary_owner,secondary);self.assertEqual(self.closed,[])

    def test_duplicate_read_alias_is_refused_before_process_or_close(self):
        self.held=owner.SpawnIOOwner(read_handles={'stdout':61,'stderr':75},
                                    sinks=self.sinks,writers=self.writers)
        with self.assertRaises(owner.UnreapedJob) as raised:self.spawn()
        self.assertIs(raised.exception,self.held.native);self.assertEqual(self.held.alias_conflict,(61,))
        self.assertEqual(raised.exception.extra_handles,{'inherited_0':61})
        self.assertEqual(self.closed,[]);self.kernel.CreateProcessW.assert_not_called()
        self.assertEqual(self.held.read_handles['stdout'],61)

    def test_invalid_mapping_retains_fixed_other_io_inputs_before_rejection(self):
        handles={'wrong':74};sinks=dict(self.sinks);writers=dict(self.writers)
        with self.assertRaises(owner.UnreapedJob) as raised:
            owner.SpawnIOOwner(read_handles=handles,sinks=sinks,writers=writers)
        held=raised.exception.spawn_io_owner;handles.clear();sinks.clear();writers.clear()
        self.assertEqual(held.read_handles,{'wrong':74})
        self.assertIs(held.sinks['stdout'],self.sinks['stdout'])
        self.assertIs(held.writers['stderr'],self.streams[2])

    def test_rearm_is_refused_without_losing_original_binding_or_repeating_spawn(self):
        self.spawn();binding=self.held.binding;calls=self.kernel.DuplicateHandle.call_count
        with self.assertRaises(owner.UnreapedJob) as raised:self.spawn()
        self.assertIs(raised.exception,self.held.native);self.assertIs(self.held.binding,binding)
        self.assertIsNotNone(self.held.rejected_binding)
        self.assertEqual(self.kernel.DuplicateHandle.call_count,calls)

    def test_keeper_caches_original_io_even_if_marker_removed_and_never_closes_core(self):
        self.spawn();native=self.held.native
        child=SimpleNamespace(stopped=False,hold_owner=Mock())
        keeper=keepers.ChildGitKeeper(native,child=child,lease=0)
        identity={'pid':44,'creation_time_100ns':111}
        identity['start_token']=keepers.v.canonical_sha256(identity)
        before=list(self.closed)
        with patch.object(owner,'_kernel',return_value=self.kernel), \
             patch.object(keepers,'_creation',return_value=identity):
            self.assertIsNone(keeper.reconcile_once())
            native.spawn_io_owner=None;self.held.released=True
            self.assertIsNone(keeper.reconcile_once())
        self.assertIs(keeper.spawn_io_owner,self.held);self.assertEqual(self.closed,before)
        self.wait.assert_called_once();self.kernel.TerminateJobObject.assert_called_once_with(11,0xE010)
        self.assertIsNone(keeper.completion)

    def test_invalid_descriptor_keeps_entry_streams_before_native_io(self):
        invalid={'released':True}
        with self.assertRaises(owner.UnreapedJob) as raised:
            owner._spawn_cli(self.kernel,['fixture'],'root',*self.streams,spawn_io=invalid)
        self.assertEqual(raised.exception.spawn_io_inputs,(invalid,self.kernel,*self.streams))
        self.kernel.DuplicateHandle.assert_not_called();self.assertEqual(self.closed,[])

    def test_foreign_write_stream_is_refused_before_job_and_retained_in_binding(self):
        foreign=SimpleNamespace(fileno=lambda:9)
        with patch.object(owner,'_new_job') as new_job:
            with self.assertRaises(owner.UnreapedJob) as raised:
                owner._spawn_cli(self.kernel,['fixture'],'root',self.streams[0],foreign,self.streams[2],
                                 spawn_io=self.held)
        self.assertIs(raised.exception,self.held.native);self.assertIs(self.held.binding[2],foreign)
        self.assertIs(self.held.writers['stdout'],self.streams[1]);new_job.assert_not_called()
