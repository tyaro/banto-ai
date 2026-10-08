"""Dedicated duplicate/offer/Popen association; fake API, no actual launch."""
from types import SimpleNamespace
from unittest.mock import Mock,patch
import unittest

from banto_ai import anomaly_v03_preformal_reader_git_worker as reader
from tests import test_anomaly_v03_publication_pipe_resources as issued

native=reader.tree.owner


class Escape(BaseException):pass


class PublicationPipeInheritanceTests(unittest.TestCase):
    def setUp(self):
        self.f=issued.PublicationPipeResourceTests();self.f.setUp()
        self.r=self.f.resources;self.k=self.f.kernel;self.r.issue()
        self.k.GetCurrentProcess=Mock(return_value=-1)
        self.effects=[];self.k.DuplicateHandle=Mock(side_effect=self.duplicate)
        self.owner=SimpleNamespace(process=None)

    def duplicate(self,source_process,source,target_process,output,access,inheritable,options):
        self.effects.append((source_process,source,target_process,access,inheritable,options))
        output._obj.value=300+len(self.effects)
        return 1

    def prepare(self):
        self.h=native.PublicationPipeInheritance(self.r,owner=self.owner)
        self.result=self.h.prepare();return self.h

    def test_original_api_and_two_duplicates_are_held_separately_from_stdio_and_source_four(self):
        h=self.prepare()
        self.assertEqual(self.effects,[(-1,104,-1,0,True,native.DUPLICATE_SAME_ACCESS),(-1,105,-1,0,True,native.DUPLICATE_SAME_ACCESS)])
        self.assertEqual(h.original_duplicates,(('stdout',301),('stderr',302)))
        self.assertEqual(h.native.extra_handles,{'stdout':301,'stderr':302})
        self.assertEqual(len(self.r.native.extra_handles),4);self.assertIs(self.r.native.publication_inheritance,h)
        self.assertEqual(self.result['dedicated_count'],2);self.assertEqual(self.result['stdio_slots_used'],0)
        self.assertFalse(self.result['inheritance_observed']);self.assertFalse(self.result['native_launch_authorized'])
        self.k.CloseHandle.assert_not_called()

    def test_cached_preparation_has_no_get_process_duplicate_create_or_clock_replay(self):
        h=self.prepare();self.f.checkpoint.reset_mock()
        self.assertIs(h.prepare(),self.result);self.f.checkpoint.assert_not_called()
        self.assertEqual(self.k.GetCurrentProcess.call_count,1);self.assertEqual(self.k.DuplicateHandle.call_count,2)
        self.assertEqual(self.k.CreatePipe.call_count,2)

    def test_original_current_process_return_is_held_before_validation_and_no_duplicate(self):
        returned=object();self.k.GetCurrentProcess.return_value=returned
        h=native.PublicationPipeInheritance(self.r,owner=self.owner)
        with self.assertRaises(ValueError) as caught:h.prepare()
        self.assertIs(h.pending['process_return'],returned);self.assertIs(h.original_process_return,returned)
        self.assertIs(caught.exception,h.native.original_error);self.k.DuplicateHandle.assert_not_called()

    def test_second_false_duplicate_keeps_indeterminate_output_and_known_prefix_without_close(self):
        def duplicate(*args):
            self.duplicate(*args);return 1 if len(self.effects)==1 else 0
        self.k.DuplicateHandle.side_effect=duplicate
        h=native.PublicationPipeInheritance(self.r,owner=self.owner)
        with self.assertRaises(OSError) as caught:h.prepare()
        self.assertEqual(h.native.extra_handles,{'stdout':301});self.assertEqual(h.pending['observed_output'],302)
        self.assertTrue(h.pending['output_indeterminate']);self.assertTrue(h.pending['return_observed'])
        self.assertEqual(h.pending['return'],0);self.assertIs(h.original_error,caught.exception)
        with self.assertRaises(OSError):h.prepare()
        self.assertEqual(self.k.DuplicateHandle.call_count,2);self.k.CloseHandle.assert_not_called()

    def test_unknown_second_duplicate_return_retains_output_buffer_and_same_first_error(self):
        failure=KeyboardInterrupt('duplicate output changed, return unknown')
        def duplicate(*args):
            self.duplicate(*args)
            if len(self.effects)==2:raise failure
            return 1
        self.k.DuplicateHandle.side_effect=duplicate
        h=native.PublicationPipeInheritance(self.r,owner=self.owner)
        with self.assertRaises(KeyboardInterrupt) as caught:h.prepare()
        self.assertIs(caught.exception,failure);self.assertFalse(h.pending['return_observed'])
        self.assertNotIn('return',h.pending);self.assertEqual(h.pending['output'].value,302)
        self.assertEqual(h.native.extra_handles,{'stdout':301});self.r.error=h.error=None
        with self.assertRaises(KeyboardInterrupt) as again:h.offer()
        self.assertIs(again.exception,failure);self.assertEqual(self.k.DuplicateHandle.call_count,2)
        self.k.CloseHandle.assert_not_called()

    def test_unknown_bool_return_is_observed_without_registering_output_as_closeable(self):
        def duplicate(*args):self.duplicate(*args);return None
        self.k.DuplicateHandle.side_effect=duplicate
        h=native.PublicationPipeInheritance(self.r,owner=self.owner)
        with self.assertRaises(ValueError):h.prepare()
        self.assertTrue(h.pending['return_observed']);self.assertIsNone(h.pending['return'])
        self.assertEqual(h.native.extra_handles,{});self.assertTrue(h.pending['output_indeterminate'])

    def test_known_alias_output_keeps_original_value_and_refuses_later_close(self):
        def duplicate(*args):self.duplicate(*args);args[3]._obj.value=104;return 1
        self.k.DuplicateHandle.side_effect=duplicate
        h=native.PublicationPipeInheritance(self.r,owner=self.owner)
        with self.assertRaises(ValueError):h.prepare()
        self.assertEqual(h.native.extra_handles,{'stdout':104});self.assertEqual(h.pending['observed_output'],104)
        with self.assertRaises(ValueError):h.close_before_offer()
        self.k.CloseHandle.assert_not_called()

    def test_api_callback_row_and_pending_binding_change_cannot_replace_original_call(self):
        h=native.PublicationPipeInheritance(self.r,owner=self.owner)
        def duplicate(*args):
            self.duplicate(*args);h.pending['source']=999
            h.pending_binding=('stdout',999,self.k.DuplicateHandle,-1,h.pending['output'],True,0,2)
            return 1
        self.k.DuplicateHandle.side_effect=duplicate
        with self.assertRaises(ValueError):h.prepare()
        self.assertTrue(h.pending['return_observed']);self.assertEqual(h.pending['return'],1)
        self.assertEqual(h.native.extra_handles,{'stdout':301});self.assertEqual(self.k.DuplicateHandle.call_count,1)

    def test_post_known_duplicate_clock_interrupt_preserves_prefix_and_no_second_call(self):
        h=native.PublicationPipeInheritance(self.r,owner=self.owner)
        failure=KeyboardInterrupt('after first duplicate')
        def checkpoint():
            if self.effects:raise failure
        self.f.checkpoint.side_effect=checkpoint
        with self.assertRaises(KeyboardInterrupt):h.prepare()
        self.assertEqual(h.native.extra_handles,{'stdout':301});self.assertEqual(h.events['stdout']['return'],1)
        self.assertEqual(self.k.DuplicateHandle.call_count,1);self.k.CloseHandle.assert_not_called()

    def test_duplicate_offer_is_irrevocable_even_if_metadata_is_cleared_before_popen(self):
        h=self.prepare();offered=h.offer();self.assertIs(offered,h.original_duplicates)
        h.offered=None
        with self.assertRaises(ValueError):h.close_before_offer()
        self.assertIs(h.original_offer,offered);self.k.CloseHandle.assert_not_called()

    def test_before_offer_close_only_closes_local_duplicates_once_and_retains_source_owner(self):
        h=self.prepare();closed=h.close_before_offer()
        self.assertEqual([c.args[0] for c in self.k.CloseHandle.call_args_list],[301,302])
        self.assertEqual(closed['closed_handles'],{'stdout':301,'stderr':302})
        self.assertEqual(h.close_owner.handles,{});self.assertFalse(closed['native_owner_recovered'])
        self.f.checkpoint.reset_mock();self.assertIs(h.close_before_offer(),closed);self.f.checkpoint.assert_not_called()
        self.assertEqual(len(self.r.native.extra_handles),4);self.assertTrue(self.r.unresolved())
        with self.assertRaises(ValueError):self.r.creator.create()
        self.assertEqual(self.k.CreatePipe.call_count,2);self.assertEqual(self.k.CloseHandle.call_count,2)

    def test_unknown_local_close_retains_remaining_and_source_four_without_reclose(self):
        h=self.prepare();failure=KeyboardInterrupt('local close return unknown')
        self.k.CloseHandle.side_effect=[1,failure]
        with self.assertRaises(native.UnclosedHandles) as caught:h.close_before_offer()
        self.assertIs(caught.exception.close_error,failure);self.assertEqual(caught.exception.handles,{'stderr':302})
        self.assertEqual(len(self.r.native.extra_handles),4);self.assertFalse(h.pending['call']['return_observed'])
        self.assertNotIn('return',h.pending['call']);h.error=self.r.error=None
        with self.assertRaises(native.UnclosedHandles) as again:h.close_before_offer()
        self.assertIs(again.exception,caught.exception);self.assertEqual(self.k.CloseHandle.call_count,2)

    def test_false_close_keeps_original_return_and_both_duplicates_without_blind_retry(self):
        h=self.prepare();self.k.CloseHandle.return_value=0
        with self.assertRaises(native.UnclosedHandles):h.close_before_offer()
        self.assertEqual(h.close_owner.handles,{'stdout':301,'stderr':302})
        self.assertEqual(h.pending['call']['return'],0);self.assertTrue(h.pending['call']['return_observed'])
        self.assertEqual(self.k.CloseHandle.call_count,1)

    def test_local_close_keeps_original_caller_popen_before_refusing_it(self):
        h=self.prepare();process=SimpleNamespace(pid=32,_handle=object());self.owner.process=process
        with self.assertRaises(native.UnclosedHandles):h.close_before_offer()
        self.assertIs(h.pending['caller_process'],process);self.k.CloseHandle.assert_not_called()

    def parent_launch(self):
        parent=self.f.parent();self.addCleanup(self.f.f.doCleanups)
        parent.issue_publication_resources(Mock(return_value=self.k))
        self.launch=parent.prepare_publication_launch(pipe_io={'kernel':self.k,'stdin':Mock()},creator=parent.original_publication_resources.creator)
        return parent,self.launch

    def test_parent_storage_clock_duplicate_offer_and_exact_popen_binding_are_connected(self):
        parent,launch=self.parent_launch();h=launch.prepare_inheritance();offered=launch.offer_inheritance()
        process=self.f.pf.f.process;options=launch.bind(process)
        self.assertIs(h.process,process);self.assertIs(h.worker_binding['creation'],h.original_worker_inputs[2])
        self.assertEqual(h.worker_binding['process_handle'],parent.publication_carrier_binding['process_handle'])
        self.assertEqual(h.worker_binding['context_raw'],launch.context_wrapper_raw)
        self.assertIs(h.worker_binding['dedicated_handles'],offered);self.assertFalse(h.worker_binding['inheritance_observed'])
        self.assertEqual(set(options['publication_io']),{'creator','context'});self.assertEqual(set(options['pipe_io']),{'kernel','stdin'})
        self.k.GetCurrentProcess.reset_mock();self.k.DuplicateHandle.reset_mock()
        with patch.object(reader.observed,'creation_observation') as creation:self.assertIs(launch.cached_options(),options)
        creation.assert_not_called();self.k.GetCurrentProcess.assert_not_called();self.k.DuplicateHandle.assert_not_called()

    def test_parent_unknown_duplicate_preserves_original_inheritance_and_python_retention(self):
        parent,launch=self.parent_launch();failure=KeyboardInterrupt('duplicate unknown')
        self.k.DuplicateHandle.side_effect=failure
        with self.assertRaises(KeyboardInterrupt) as caught:launch.prepare_inheritance()
        h=launch.original_publication_inheritance
        self.assertIs(h.original_error,failure);self.assertIs(h.native.original_error,failure)
        parent.publication_resources=None;parent.error=None
        with patch.object(reader.ParentPublicationRetention,'_pause',side_effect=Escape),self.assertRaises(Escape):
            reader.retain_parent_publications(caught.exception,parent)
        self.assertIn(parent.original_publication_resources,parent.original_publication_retention.owners)
        self.assertIs(parent.original_publication_resources.native.publication_inheritance,h)
        self.assertEqual(self.k.DuplicateHandle.call_count,1);self.k.CloseHandle.assert_not_called()

    def test_second_inheritance_retains_original_and_rejected_owner_without_duplicate_replay(self):
        h=self.prepare();foreign=SimpleNamespace(process=None)
        with self.assertRaises(ValueError):native.PublicationPipeInheritance(self.r,owner=foreign)
        self.assertIs(self.r.original_publication_inheritance,h);self.assertIs(h.rejected.owner,foreign)
        self.assertEqual(self.k.DuplicateHandle.call_count,2);self.k.CloseHandle.assert_not_called()

    def test_missing_original_resources_rejects_with_original_owner_and_input_preserved(self):
        owner=SimpleNamespace(process=None)
        with self.assertRaises(ValueError) as caught:native.PublicationPipeInheritance(None,owner=owner)
        h=caught.exception.publication_inheritance
        self.assertIs(h.original_inputs[0],None);self.assertIs(h.original_inputs[1],owner)
        self.assertIs(h.original_error,caught.exception);self.k.DuplicateHandle.assert_not_called()

    def test_bound_creation_metadata_change_refuses_cached_options_without_handle_reobservation(self):
        parent,launch=self.parent_launch();h=launch.prepare_inheritance();launch.offer_inheritance()
        launch.bind(self.f.pf.f.process);creation=h.original_worker_inputs[2]
        original_snapshot=h.creation_snapshot;creation['start_token']='changed-after-binding'
        with patch.object(reader.observed,'creation_observation') as observation,self.assertRaises(ValueError) as caught:
            launch.cached_options()
        self.assertEqual(h.creation_snapshot,original_snapshot);observation.assert_not_called()
        self.assertIs(launch.original_error,caught.exception);self.assertIs(h.original_worker_inputs[2],creation)
        self.k.CloseHandle.assert_not_called();self.assertEqual(self.k.DuplicateHandle.call_count,2)

    def test_known_close_prefix_ledger_cannot_be_hidden_during_post_return_checkpoint(self):
        h=self.prepare()
        def checkpoint():
            if h.original_close_returns:
                h.close_events.clear();h.close_bindings.clear()
        self.f.checkpoint.side_effect=checkpoint
        with self.assertRaises(native.UnclosedHandles) as caught:h.close_before_offer()
        self.assertEqual(h.original_close_returns[0][:4],('stdout',301,1,True))
        self.assertEqual(caught.exception.handles,{'stderr':302});self.assertEqual(self.k.CloseHandle.call_count,1)
        with self.assertRaises(native.UnclosedHandles):h.close_before_offer()
        self.assertEqual(self.k.CloseHandle.call_count,1);self.assertEqual(len(self.r.native.extra_handles),4)

    def test_original_duplicate_tuple_ignores_global_option_change_and_keeps_success_before_callback_rejection(self):
        h=native.PublicationPipeInheritance(self.r,owner=self.owner)
        def checkpoint():native.DUPLICATE_SAME_ACCESS=1
        def duplicate(*args):
            self.duplicate(*args);h.pending['options']=1
            h.pending_binding=('stdout',104,self.k.DuplicateHandle,-1,h.pending['output'],True,0,1)
            return 1
        self.f.checkpoint.side_effect=checkpoint;self.k.DuplicateHandle.side_effect=duplicate
        with patch.object(native,'DUPLICATE_SAME_ACCESS',2),self.assertRaises(ValueError):h.prepare()
        self.assertEqual(self.effects,[(-1,104,-1,0,True,2)])
        self.assertEqual(h.call_bindings['stdout'][1],104);self.assertEqual(h.call_bindings['stdout'][7],2)
        self.assertIs(h.native.duplicate_call_bindings,h.call_bindings)
        self.assertEqual(h.native.extra_handles,{'stdout':301});self.assertEqual(h.pending['observed_output'],301)
        self.assertTrue(h.pending['return_observed']);self.assertFalse(h.pending['output_indeterminate'])
        self.k.CloseHandle.assert_not_called();self.assertEqual(self.k.DuplicateHandle.call_count,1)


if __name__=='__main__':unittest.main()
