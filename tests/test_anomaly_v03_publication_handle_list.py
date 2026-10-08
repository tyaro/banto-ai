"""Explicit five-handle attribute preparation; fake API, no native launch."""
import ctypes
from types import SimpleNamespace
from unittest.mock import Mock,patch
import unittest
from tests import test_anomaly_v03_publication_pipe_inheritance as inherited

native=inherited.native
reader=inherited.reader


class PublicationHandleListTests(unittest.TestCase):
    def setUp(self):
        self.f=inherited.PublicationPipeInheritanceTests();self.f.setUp()
        self.k=self.f.k;self.h=self.f.prepare();self.h.offer();self.owner=self.f.owner
        self.k.InitializeProcThreadAttributeList=Mock(side_effect=self.initialize)
        self.k.UpdateProcThreadAttribute=Mock(return_value=1)
        self.k.DeleteProcThreadAttributeList=Mock(return_value=None)
        self.k.CreateProcessW=Mock(side_effect=AssertionError('actual CreateProcess forbidden'))
        self.last_error=Mock(return_value=122)
        self.addCleanup(self.f.doCleanups)

    def initialize(self,buffer,count,flags,size):
        if buffer is None:size._obj.value=96;return 0
        return 1

    def new(self,stdio=(201,202,203)):
        self.a=native.PublicationHandleListPreparation(self.h,stdio,owner=self.owner,last_error=self.last_error)
        return self.a

    def ready(self):
        a=self.new();self.result=a.prepare();return a

    def test_exact_separate_three_and_two_original_array_and_startup_no_launch(self):
        a=self.ready();args=self.k.UpdateProcThreadAttribute.call_args.args
        self.assertEqual(tuple(a.handle_array),(201,202,203,301,302))
        self.assertEqual(args[1:3],(0,0x00020002));self.assertEqual(args[4],ctypes.sizeof(a.handle_array))
        self.assertEqual(ctypes.cast(args[3],ctypes.POINTER(native.w.HANDLE*5)).contents[:],list(a.handles))
        self.assertEqual((a.startup.StartupInfo.hStdInput,a.startup.StartupInfo.hStdOutput,a.startup.StartupInfo.hStdError),(201,202,203))
        self.assertEqual(a.result['explicit_handle_count'],5);self.assertEqual(a.result['attribute_bytes'],96)
        for key in ('native_launch_authorized','inheritance_observed','parent_ack_authorized','execution_authenticated','atomic_reservation'):self.assertFalse(a.result[key])
        self.k.CreateProcessW.assert_not_called();self.k.CloseHandle.assert_not_called()
        self.assertEqual(len(self.h.resources.native.extra_handles),4);self.assertEqual(len(self.h.native.extra_handles),2)

    def test_cached_result_preserves_original_and_no_api_or_clock_replay(self):
        a=self.ready();self.f.f.checkpoint.reset_mock();self.k.InitializeProcThreadAttributeList.reset_mock();self.k.UpdateProcThreadAttribute.reset_mock()
        self.assertIs(a.prepare(),self.result);self.f.f.checkpoint.assert_not_called()
        self.k.InitializeProcThreadAttributeList.assert_not_called();self.k.UpdateProcThreadAttribute.assert_not_called();self.k.CreateProcessW.assert_not_called()

    def test_non_tuple_stdio_rejected_before_api_with_original_input(self):
        value=[201,202,203]
        with self.assertRaises(ValueError) as caught:self.new(value)
        self.assertIs(caught.exception.publication_handle_list.original_inputs[1],value)
        self.k.InitializeProcThreadAttributeList.assert_not_called()

    def test_bool_handle_rejected_before_attribute_api(self):
        with self.assertRaises(ValueError):self.new((True,202,203))
        self.k.InitializeProcThreadAttributeList.assert_not_called()

    def test_alias_source_four_rejected_without_dup_or_close(self):
        with self.assertRaises(ValueError):self.new((104,202,203))
        self.k.InitializeProcThreadAttributeList.assert_not_called();self.k.CloseHandle.assert_not_called()

    def test_alias_dedicated_and_pseudo_handle_reject_as_one_tuple(self):
        with self.assertRaises(ValueError):self.new((301,202,2**(ctypes.sizeof(native.w.HANDLE)*8)-1))
        self.k.InitializeProcThreadAttributeList.assert_not_called()

    def test_oversized_sizing_output_retained_and_no_allocation_or_update(self):
        def sizing(buffer,count,flags,size):size._obj.value=32769;return 0
        self.k.InitializeProcThreadAttributeList.side_effect=sizing;a=self.new()
        with self.assertRaises(ValueError) as caught:a.prepare()
        self.assertEqual(a.size.value,32769);self.assertEqual(a.pending['return'],0);self.assertTrue(a.pending['return_observed'])
        self.assertIs(a.original_error,caught.exception);self.assertIsNone(a.buffer);self.k.UpdateProcThreadAttribute.assert_not_called()

    def test_sizing_wrong_last_error_cannot_be_expected_success(self):
        self.last_error.return_value=5;a=self.new()
        with self.assertRaises(ValueError):a.prepare()
        self.assertEqual(a.pending['last_error_return'],5);self.assertTrue(a.pending['last_error_observed']);self.assertIsNone(a.buffer)

    def test_last_error_unknown_keeps_original_zero_return_before_clock(self):
        failure=KeyboardInterrupt('original last error getter unknown');self.last_error.side_effect=failure;a=self.new()
        with self.assertRaises(KeyboardInterrupt) as caught:a.prepare()
        self.assertIs(caught.exception,failure);self.assertTrue(a.pending['return_observed']);self.assertEqual(a.pending['return'],0)
        self.assertFalse(a.pending['last_error_observed']);self.assertEqual(len(a.records),1)
        with self.assertRaises(KeyboardInterrupt):a.prepare()
        self.assertEqual(self.k.InitializeProcThreadAttributeList.call_count,1)

    def test_initialize_false_keeps_original_buffer_and_size_without_delete_retry(self):
        self.k.InitializeProcThreadAttributeList.side_effect=lambda b,c,f,s: self.initialize(b,c,f,s) if b is None else 0
        a=self.new()
        with self.assertRaises(ValueError):a.prepare()
        self.assertIs(a.buffer,a.native.attributes);self.assertEqual(len(a.buffer),96);self.assertEqual(a.pending['return'],0)
        with self.assertRaises(ValueError):a.cleanup_unlaunched()
        self.k.DeleteProcThreadAttributeList.assert_not_called();self.k.UpdateProcThreadAttribute.assert_not_called()

    def test_update_unknown_preserves_opaque_buffer_array_and_original_pending(self):
        failure=KeyboardInterrupt('Update return unknown');self.k.UpdateProcThreadAttribute.side_effect=failure;a=self.new()
        with self.assertRaises(KeyboardInterrupt) as caught:a.prepare()
        self.assertIs(caught.exception,failure);self.assertIs(a.native.attributes,a.buffer);self.assertIs(a.native.attribute_handles,a.handle_array)
        self.assertFalse(a.pending['return_observed']);self.assertEqual(a.pending['stage'],'update')
        a.error=None;self.h.error=None;self.h.resources.error=None
        with self.assertRaises(KeyboardInterrupt) as again:a.cleanup_unlaunched()
        self.assertIs(again.exception,failure);self.k.DeleteProcThreadAttributeList.assert_not_called();self.k.CreateProcessW.assert_not_called()

    def test_returning_update_callback_array_change_keeps_actual_return_before_rejection(self):
        a=self.new()
        def update(*args):a.handle_array[4]=999;return 1
        self.k.UpdateProcThreadAttribute.side_effect=update
        with self.assertRaises(ValueError):a.prepare()
        self.assertEqual(a.pending['return'],1);self.assertTrue(a.pending['return_observed']);self.assertEqual(a.returns[-1][1],1)
        self.assertEqual(a.handles,(201,202,203,301,302));self.k.DeleteProcThreadAttributeList.assert_not_called()

    def test_known_void_delete_keeps_buffer_and_handles_no_native_recovery(self):
        a=self.ready();done=a.cleanup_unlaunched()
        self.assertTrue(done['delete_return_observed']);self.assertIsNone(done['delete_return']);self.assertEqual(done['handles_closed'],0)
        self.assertFalse(done['native_owner_recovered']);self.assertIs(a.buffer,a.native.attributes)
        self.assertEqual(len(self.h.native.extra_handles),2);self.assertEqual(len(self.h.resources.native.extra_handles),4)
        self.f.f.checkpoint.reset_mock();self.assertIs(a.cleanup_unlaunched(),done);self.f.f.checkpoint.assert_not_called()
        self.assertEqual(self.k.DeleteProcThreadAttributeList.call_count,1);self.k.CloseHandle.assert_not_called()

    def test_nonvoid_delete_return_keeps_original_and_no_replay(self):
        a=self.ready();returned=object();self.k.DeleteProcThreadAttributeList.return_value=returned
        with self.assertRaises(ValueError):a.cleanup_unlaunched()
        self.assertIs(a.pending['return'],returned);self.assertTrue(a.pending['return_observed']);self.assertIs(a.buffer,a.native.attributes)
        with self.assertRaises(ValueError):a.cleanup_unlaunched()
        self.assertEqual(self.k.DeleteProcThreadAttributeList.call_count,1)

    def test_unknown_delete_error_latched_against_sidecar_restore_and_replay(self):
        a=self.ready();failure=KeyboardInterrupt('Delete unknown');self.k.DeleteProcThreadAttributeList.side_effect=failure
        with self.assertRaises(KeyboardInterrupt):a.cleanup_unlaunched()
        self.assertFalse(a.pending['return_observed']);a.error=None;self.owner.publication_handle_list=a
        with self.assertRaises(KeyboardInterrupt) as caught:self.h._fixed()
        self.assertIs(caught.exception,failure);self.assertIs(a.native.attributes,a.buffer)
        with self.assertRaises(KeyboardInterrupt):a.cleanup_unlaunched()
        self.assertEqual(self.k.DeleteProcThreadAttributeList.call_count,1);self.k.CloseHandle.assert_not_called()

    def test_popen_before_delete_is_preserved_and_delete_refused(self):
        a=self.ready();process=SimpleNamespace(pid=44,_handle=object());self.owner.process=process
        with self.assertRaises(ValueError):a.cleanup_unlaunched()
        self.assertIs(a.rejected_process,process);self.k.DeleteProcThreadAttributeList.assert_not_called()

    def test_second_preparation_retains_original_and_rejected_inputs_without_api(self):
        a=self.ready()
        with self.assertRaises(ValueError) as caught:native.PublicationHandleListPreparation(self.h,(211,212,213),owner=self.owner,last_error=self.last_error)
        self.assertIs(caught.exception.publication_handle_list,a);self.assertEqual(a.rejected.original_inputs[1],(211,212,213))
        self.assertIs(self.h.original_handle_list,a);self.assertEqual(self.k.UpdateProcThreadAttribute.call_count,1)

    def test_parent_clock_storage_and_unknown_api_owner_reach_original_retention(self):
        parent,launch=self.f.parent_launch();launch.prepare_inheritance();launch.offer_inheritance()
        failure=KeyboardInterrupt('original attribute IO');self.k.UpdateProcThreadAttribute.side_effect=failure
        with self.assertRaises(KeyboardInterrupt) as caught:launch.prepare_handle_list((201,202,203),last_error=self.last_error)
        a=launch.original_publication_handle_list
        self.assertIs(a.owner,launch);self.assertIs(a.checkpoint,parent.inventory_checkpoint)
        self.assertIs(caught.exception,failure);self.assertIs(a.buffer,a.native.attributes)
        with patch.object(reader.ParentPublicationRetention,'_pause',side_effect=inherited.Escape),self.assertRaises(inherited.Escape):reader.retain_parent_publications(failure,parent)
        self.assertIn(parent.original_publication_resources,parent.original_publication_retention.owners)
        self.assertIs(parent.original_publication_resources.native.publication_inheritance.original_handle_list,a)
        self.k.CreateProcessW.assert_not_called();self.k.CloseHandle.assert_not_called()

    def test_sizing_callback_api_change_uses_original_last_error_return_and_latches(self):
        a=self.new();foreign=Mock(return_value=5)
        def sizing(*args):
            args[3]._obj.value=96;a.apis=(*a.apis[:4],foreign);return 0
        self.k.InitializeProcThreadAttributeList.side_effect=sizing
        with self.assertRaises(ValueError):a.prepare()
        self.last_error.assert_called_once();foreign.assert_not_called()
        self.assertEqual(a.pending['return'],0);self.assertEqual(a.pending['last_error_return'],122)
        self.assertIs(a.pending['last_error_api'],self.last_error);self.k.DeleteProcThreadAttributeList.assert_not_called()

    def test_delete_popen_getter_exception_keeps_original_owner_before_observation(self):
        class Owner:
            failure=None
            @property
            def process(self):
                if self.failure is not None:raise self.failure
                return None
        owner=Owner()
        # Reference fixture issuance uses a fresh resource, no completed body replay.
        fixture=inherited.PublicationPipeInheritanceTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        fixture.owner=owner;h=fixture.prepare();h.offer();kernel=fixture.k
        kernel.InitializeProcThreadAttributeList=Mock(side_effect=self.initialize)
        kernel.UpdateProcThreadAttribute=Mock(return_value=1);kernel.DeleteProcThreadAttributeList=Mock(return_value=None);kernel.CreateProcessW=Mock()
        a=native.PublicationHandleListPreparation(h,(201,202,203),owner=owner,last_error=self.last_error);a.prepare()
        failure=KeyboardInterrupt('Popen getter unknown');owner.failure=failure
        with self.assertRaises(KeyboardInterrupt) as caught:a.cleanup_unlaunched()
        self.assertIs(caught.exception,failure);self.assertIs(a.rejected_owner,owner);self.assertIs(a.native.attributes,a.buffer)
        self.assertIs(a.original_error,failure);kernel.DeleteProcThreadAttributeList.assert_not_called()

    def test_float_last_error_cannot_authorize_attribute_allocation(self):
        self.last_error.return_value=122.0;a=self.new()
        with self.assertRaises(ValueError):a.prepare()
        self.assertEqual(a.pending['last_error_return'],122.0);self.assertIsNone(a.buffer)
        self.k.UpdateProcThreadAttribute.assert_not_called()

    def test_callback_return_ledger_erase_preserves_original_prefix_and_actual_update(self):
        a=self.new()
        def update(*args):a.returns=();return 1
        self.k.UpdateProcThreadAttribute.side_effect=update
        with self.assertRaises(ValueError):a.prepare()
        held=a.native.attribute_original_returns
        self.assertEqual(len(held),3);self.assertEqual(held[0][0]['stage'],'sizing');self.assertEqual(held[1][0]['stage'],'initialize')
        self.assertIs(held[2][0],a.pending);self.assertEqual(held[2][1],1);self.assertIs(a.rejected_returns,())
        self.assertTrue(a.pending['return_observed']);self.k.DeleteProcThreadAttributeList.assert_not_called()


if __name__=='__main__':unittest.main()
