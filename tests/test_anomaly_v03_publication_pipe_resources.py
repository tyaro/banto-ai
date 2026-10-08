"""Original issuance/abort-close boundary: fake Win API, no worker launch."""
from types import SimpleNamespace
from unittest.mock import Mock,patch
import unittest

from banto_ai import anomaly_v03_preformal_reader_git_worker as reader
from tests import test_anomaly_v03_publication_carrier_path as carriers
from tests import test_anomaly_v03_publication_storage_forwarding as storage

native=reader.tree.owner


class Escape(BaseException):pass


class PublicationPipeResourceTests(unittest.TestCase):
    def setUp(self):
        self.kernel=carriers.QueueKernel();self.kernel.CloseHandle=Mock(return_value=1)
        self.owner=SimpleNamespace(worker=None);self.checkpoint=Mock();self.issuer=Mock(return_value=self.kernel)
        self.resources=native.PublicationPipeResources(self.issuer,checkpoint=self.checkpoint,owner=self.owner)

    def issue(self):return self.resources.issue()

    def parent(self):
        self.f=storage.PublicationStorageForwardingTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.f.compose()  # Explicit composing snapshot stub, not a capacity pass.
        self.pf,self.p=self.f.parent()
        return self.p

    def test_original_issuer_return_createpipe_four_handles_and_single_abort_close(self):
        result=self.issue();r=self.resources
        self.assertIs(result['kernel'],self.kernel);self.assertIs(result['creator'],r.creator)
        self.assertIs(r.creator.original_publication_resources,r);self.assertEqual(len(r.handles),4)
        self.assertEqual(r.native.extra_handles,r.handles);self.assertFalse(result['native_launch_authorized'])
        closed=r.close_unlaunched();self.assertEqual(closed['closed_handles'],r.handles)
        self.assertEqual(self.kernel.CloseHandle.call_count,4)
        self.assertTrue(all(row['return_observed'] and row['return']==1 for row in r.close_events.values()))
        self.assertFalse(closed['native_owner_recovered']);self.assertFalse(closed['parent_ack_authorized'])
        self.assertFalse(closed['execution_authenticated']);self.assertEqual(r.close_owner.handles,{})
        self.assertEqual(len(r.native.extra_handles),4)

    def test_issue_and_close_cached_returns_never_repeat_issuer_clock_or_native(self):
        result=self.issue();self.assertIs(self.issue(),result);closed=self.resources.close_unlaunched()
        self.checkpoint.reset_mock();self.assertIs(self.resources.close_unlaunched(),closed)
        self.checkpoint.assert_not_called();self.assertEqual(self.issuer.call_count,1)
        self.assertEqual(self.kernel.CreatePipe.call_count,2);self.assertEqual(self.kernel.CloseHandle.call_count,4)

    def test_issuer_interrupt_keeps_original_callable_pending_and_same_error(self):
        failure=KeyboardInterrupt('issuer return unknown');self.issuer.side_effect=failure
        with self.assertRaises(KeyboardInterrupt) as caught:self.issue()
        self.assertIs(caught.exception,failure);r=self.resources
        self.assertIs(r.pending['issuer'],self.issuer);self.assertNotIn('issuer_return',r.pending)
        self.assertIs(r.native.original_error,failure);r.error=None
        with self.assertRaises(KeyboardInterrupt) as again:self.issue()
        self.assertIs(again.exception,failure);self.assertEqual(self.issuer.call_count,1)
        self.kernel.CloseHandle.assert_not_called()

    def test_kernel_getter_failure_preserves_returned_object_before_creator_or_clock(self):
        returned=object();self.issuer.return_value=returned
        with self.assertRaises(AttributeError) as caught:self.issue()
        self.assertIs(self.resources.pending['issuer_return'],returned)
        self.assertIs(self.resources.kernel,returned);self.assertIs(caught.exception.publication_resources,self.resources)
        self.assertIsNone(self.resources.creator);self.kernel.CreatePipe.assert_not_called()

    def test_second_createpipe_interrupt_keeps_original_creator_native_buffers_and_prefix(self):
        create=self.kernel.create;failure=KeyboardInterrupt('second CreatePipe unknown')
        def interrupted(*args):
            result=create(*args)
            if self.kernel.created==2:raise failure
            return result
        self.kernel.CreatePipe.side_effect=interrupted
        with self.assertRaises(native.UnreapedJob) as caught:self.issue()
        r=self.resources;creator=r.creator
        self.assertIs(caught.exception,creator.native);self.assertIs(creator.native.original_error,failure)
        self.assertEqual(set(creator.events),{'stdout'});self.assertEqual(creator.pending['name'],'stderr')
        self.assertIsNone(creator.pending['return']);self.assertGreater(creator.pending['read'].value,0)
        self.assertIs(r.native.pipe_successor,creator.native)
        with self.assertRaises(native.UnreapedJob):r.close_unlaunched()
        self.kernel.CloseHandle.assert_not_called();self.assertEqual(self.kernel.CreatePipe.call_count,2)

    def test_issued_return_metadata_clear_never_reissues_or_drops_creator(self):
        result=self.issue();creator=self.resources.creator;self.resources.result=None
        with self.assertRaises(ValueError):self.issue()
        self.assertIs(self.resources.original_issue_result,result);self.assertIs(self.resources.creator,creator)
        self.assertEqual(self.issuer.call_count,1);self.assertEqual(self.kernel.CreatePipe.call_count,2)

    def test_false_close_stops_at_original_handle_and_retains_remaining_without_retry(self):
        self.issue();self.kernel.CloseHandle.side_effect=[1,0]
        with self.assertRaises(native.UnclosedHandles) as caught:self.resources.close_unlaunched()
        r=self.resources;held=caught.exception
        self.assertIs(held,r.close_owner);self.assertEqual(len(held.handles),3)
        self.assertTrue(r.pending['call']['return_observed']);self.assertEqual(r.pending['call']['return'],0)
        self.assertEqual(len(r.close_events),1);self.assertEqual(self.kernel.CloseHandle.call_count,2)
        r.error=None;r.close_started=False
        with self.assertRaises(native.UnclosedHandles) as again:r.close_unlaunched()
        self.assertIs(again.exception,held);self.assertEqual(self.kernel.CloseHandle.call_count,2)

    def test_unknown_close_after_kernel_effect_keeps_missing_return_and_original_remaining(self):
        self.issue();failure=KeyboardInterrupt('unknown CloseHandle return');effects=[]
        def close(handle):
            effects.append(handle)
            if len(effects)==2:raise failure
            return 1
        self.kernel.CloseHandle.side_effect=close
        with self.assertRaises(native.UnclosedHandles) as caught:self.resources.close_unlaunched()
        r=self.resources;self.assertIs(caught.exception.close_error,failure)
        self.assertFalse(r.pending['call']['return_observed']);self.assertNotIn('return',r.pending['call'])
        self.assertIn(r.pending['call']['handle'],caught.exception.handles.values())
        self.assertEqual(len(caught.exception.handles),3);self.assertEqual(len(r.native.extra_handles),4)
        with self.assertRaises(native.UnclosedHandles):r.close_unlaunched()
        self.assertEqual(self.kernel.CloseHandle.call_count,2)

    def test_unknown_bool_return_is_retained_without_closing_another_handle(self):
        self.issue();self.kernel.CloseHandle.return_value=None
        with self.assertRaises(native.UnclosedHandles):self.resources.close_unlaunched()
        row=self.resources.pending['call'];self.assertTrue(row['return_observed']);self.assertIsNone(row['return'])
        self.assertEqual(len(self.resources.close_owner.handles),4);self.assertEqual(self.kernel.CloseHandle.call_count,1)

    def test_post_return_clock_interrupt_keeps_known_close_prefix_before_remaining(self):
        self.issue();failure=KeyboardInterrupt('post close clock');self.checkpoint.side_effect=[None,failure]
        with self.assertRaises(native.UnclosedHandles) as caught:self.resources.close_unlaunched()
        self.assertIs(caught.exception.close_error,failure);self.assertEqual(len(self.resources.close_events),1)
        self.assertEqual(len(caught.exception.handles),3);self.assertEqual(self.kernel.CloseHandle.call_count,1)

    def test_api_callback_call_binding_change_keeps_return_and_original_handle_tuple(self):
        self.issue()
        def close(handle):self.resources.pending['call']['handle']=999;return 1
        self.kernel.CloseHandle.side_effect=close
        with self.assertRaises(native.UnclosedHandles):self.resources.close_unlaunched()
        pending=self.resources.pending;self.assertEqual(pending['call_binding'][1],74)
        self.assertEqual(pending['call']['return'],1);self.assertEqual(pending['call']['handle'],999)
        self.assertEqual(len(self.resources.close_owner.handles),4);self.assertEqual(self.kernel.CloseHandle.call_count,1)

    def test_closed_completion_change_is_rejected_without_native_close_replay(self):
        self.issue();closed=self.resources.close_unlaunched();closed['native_owner_recovered']=True
        with self.assertRaises(native.UnclosedHandles):self.resources.close_unlaunched()
        self.assertEqual(self.kernel.CloseHandle.call_count,4)
        self.assertIs(self.resources.original_close_completion,closed)

    def test_shared_carrier_marker_clear_cannot_enable_unlaunched_close(self):
        result=self.issue();owner=SimpleNamespace()
        carrier=reader.actors.archive.PublicationCarrier(creator=result['creator'],owner=owner,
            checkpoint=self.checkpoint,frame_limit=8192,sending=False)
        result['creator'].native.publication_carriers=[]
        with self.assertRaises(native.UnclosedHandles):self.resources.close_unlaunched()
        self.assertIn(carrier,self.resources.original_shares);self.kernel.CloseHandle.assert_not_called()

    def test_original_popen_is_held_before_rejecting_unlaunched_close(self):
        self.issue();process=SimpleNamespace(pid=202,_handle=object());self.owner.worker=process
        with self.assertRaises(native.UnclosedHandles):self.resources.close_unlaunched()
        self.assertIs(self.resources.pending['caller_worker'],process);self.kernel.CloseHandle.assert_not_called()

    def test_closed_creator_cannot_be_recreated_spawned_or_shared(self):
        self.issue();self.resources.close_unlaunched();creator=self.resources.creator
        with self.assertRaises(ValueError):creator.create()
        with self.assertRaises(ValueError):creator.bind_spawn({'stdout':object(),'stderr':object()})
        self.assertEqual(self.kernel.CreatePipe.call_count,2);self.assertEqual(self.kernel.CloseHandle.call_count,4)

    def test_parent_storage_clock_kernel_issue_and_original_launch_options_are_connected(self):
        p=self.parent();r=p.issue_publication_resources(self.issuer)
        self.assertIs(r.owner,p);self.assertIs(r.checkpoint,p.inventory_checkpoint)
        self.assertIs(p.publication_resource_return,r.result)
        launch=p.prepare_publication_launch(pipe_io={'kernel':self.kernel,'stdin':object()},creator=r.creator)
        options=launch.bind(self.pf.f.process)
        self.assertIs(launch.creator,r.creator);self.assertIs(options['publication_io']['creator'],r.creator)
        self.assertEqual(options['publication_io']['context']['value']['clock'],p.clock)
        self.assertFalse(r.result['native_launch_authorized']);self.kernel.CloseHandle.assert_not_called()

    def test_parent_unknown_create_keeps_original_resource_native_and_python_before_report(self):
        p=self.parent();failure=KeyboardInterrupt('CreatePipe unknown')
        self.kernel.CreatePipe.side_effect=failure
        with self.assertRaises(native.UnreapedJob) as caught:p.issue_publication_resources(self.issuer)
        r=p.original_publication_resources;self.assertIs(r.creator.native,caught.exception)
        with patch.object(reader.ParentPublicationRetention,'_pause',side_effect=Escape),self.assertRaises(Escape):
            reader.retain_parent_publications(caught.exception,p)
        self.assertIn(r,p.original_publication_retention.owners)
        self.assertIs(p.initializing_publication_resources,r);self.kernel.CloseHandle.assert_not_called()

    def test_parent_abort_before_preparation_uses_same_checkpoint_and_refuses_later_work(self):
        p=self.parent();r=p.issue_publication_resources(self.issuer);closed=r.close_unlaunched()
        self.assertEqual(len(closed['closed_handles']),4)
        with self.assertRaises(ValueError):p.source()
        self.assertIs(p.original_publication_resources,r);self.assertIsNone(p.worker)
        self.assertEqual(self.kernel.CloseHandle.call_count,4)

    def test_parent_rejected_second_resource_owner_retains_both_issuers(self):
        p=self.parent();first=p.issue_publication_resources(self.issuer);second=Mock()
        with self.assertRaises(ValueError):p.issue_publication_resources(second)
        self.assertIs(p.original_publication_resources,first)
        self.assertIs(first.rejected.original_inputs[0],second);second.assert_not_called()
        self.kernel.CloseHandle.assert_not_called()

    def test_diagnostic_callback_interrupt_never_replaces_original_issuer_error(self):
        failure=OSError('original issuer error');diagnostic=KeyboardInterrupt('owner diagnostic IO')
        self.issuer.side_effect=failure;self.owner._remember_publication=Mock(side_effect=diagnostic)
        with self.assertRaises(OSError) as caught:self.issue()
        self.assertIs(caught.exception,failure);self.assertIs(self.resources.original_error,failure)
        self.assertIs(self.resources.retention_error,diagnostic)
        with self.assertRaises(OSError) as again:self.issue()
        self.assertIs(again.exception,failure);self.assertEqual(self.issuer.call_count,1)
        self.kernel.CloseHandle.assert_not_called()

    def test_api_callback_cannot_change_both_pending_row_and_binding_to_another_handle(self):
        self.issue()
        def close(handle):
            row=self.resources.pending['call'];row['handle']=999
            self.resources.pending['call_binding']=(row['name'],999,self.kernel.CloseHandle)
            return 1
        self.kernel.CloseHandle.side_effect=close
        with self.assertRaises(native.UnclosedHandles) as caught:self.resources.close_unlaunched()
        self.assertEqual(len(caught.exception.handles),4);self.assertEqual(self.resources.pending['call']['return'],1)
        self.assertEqual(self.resources.original_handles[0],('stdout_read',74))
        self.assertEqual(self.kernel.CloseHandle.call_count,1)
