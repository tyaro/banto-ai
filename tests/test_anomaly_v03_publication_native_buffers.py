"""Independent preparation buffer bounds with fake APIs; no native launch."""
import copy
import ctypes
import os
import sys
from types import SimpleNamespace
from unittest.mock import Mock,patch
import unittest
from tests import test_anomaly_v03_publication_handle_list as fixture

native=fixture.native


class PublicationNativeBufferTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.PublicationHandleListTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.owner=self.f.owner;self.k=self.f.k
        self.owner.entry_raw=b'{"format":"fake-entry","formal_permission":false}'
        self.owner.entry_pin=native.PublicationNativeBufferAdmission._pin(self.owner.entry_raw)
        self.owner.storage=SimpleNamespace(plan_pin={'bytes':8,'sha256':'a'*64},_fixed=Mock())
        self.k.AssignProcessToJobObject=Mock(side_effect=AssertionError('actual assign forbidden'))
        self.k.IsProcessInJob=Mock(side_effect=AssertionError('actual membership forbidden'))
        self.job=native.UnreapedJob(701,None,None,{'fixture_only':True})

    def allocation(self,owner=None):
        owner=self.owner if owner is None else owner
        limits=dict(native.PublicationNativeBufferAdmission.CEILINGS)
        limits.update(descriptor=2048,entry=8192,invocation=8192,command=32768,attributes=32768)
        value={'format':native.PublicationNativeBufferAdmission.FORMAT,'entry_pin':copy.deepcopy(owner.entry_pin),
            'storage_pin':copy.deepcopy(owner.storage.plan_pin),'limits':limits,'total_bytes':98304,'formal_permission':False}
        return {'value':value,'pin':native.PublicationNativeBufferAdmission._pin(native.PublicationNativeBufferAdmission._raw(value))}

    def repin(self,allocation):
        allocation['pin']=native.PublicationNativeBufferAdmission._pin(native.PublicationNativeBufferAdmission._raw(allocation['value']))
        return allocation

    def arm(self,allocation=None):
        return native.PublicationNativeBufferAdmission(self.allocation() if allocation is None else allocation,owner=self.owner)

    def attributes(self):return self.f.ready()

    def process(self,a,argv=None):
        return native.PublicationNativeProcessPreparation(a,(sys.executable,'-c','pass') if argv is None else argv,
            os.getcwd(),self.job,owner=self.owner,binding=self.owner.entry_raw)

    def no_native(self):
        for api in (self.k.CreateProcessW,self.k.AssignProcessToJobObject,self.k.IsProcessInJob,
                    self.k.CloseHandle,self.k.DeleteProcThreadAttributeList):api.assert_not_called()

    def test_whole_path_reserves_all_maxima_and_records_actual_separate_buffers(self):
        b=self.arm();a=self.attributes();p=self.process(a);p.prepare();view=b.view()
        actual=len(b.descriptor_raw)+len(self.owner.entry_raw)+ctypes.sizeof(a.buffer)+ctypes.sizeof(a.handle_array)+\
            ctypes.sizeof(a.startup)+len(p.invocation_raw)+ctypes.sizeof(p.command)+ctypes.sizeof(p.process_information)+ctypes.sizeof(p.member_output)
        self.assertEqual(view['used_bytes'],actual);self.assertEqual(view['reserved_maxima_bytes'],sum(b.limits.values()))
        self.assertEqual([stage for _,stage,_,_ in b.records],['entry','attributes','process'])
        self.assertIs(b.completed[-1][1][1],p.command);self.assertIs(b.completed[-2][1][0],a.buffer)
        for key in ('rss_measured','native_launch_authorized','atomic_reservation','capacity_pass'):self.assertFalse(view[key])
        self.no_native()

    def test_all_future_maxima_must_fit_before_any_attribute_api(self):
        allocation=self.allocation();allocation['value']['total_bytes']=1000;self.repin(allocation)
        with self.assertRaises(ValueError) as caught:self.arm(allocation)
        self.assertIs(caught.exception.publication_native_buffers.original_inputs[0],allocation)
        self.k.InitializeProcThreadAttributeList.assert_not_called();self.no_native()

    def test_closed_descriptor_rejects_extra_field_without_old_pin_reinterpretation(self):
        allocation=self.allocation();allocation['value']['legacy_pin']={};self.repin(allocation)
        with self.assertRaises(ValueError):self.arm(allocation)
        self.k.InitializeProcThreadAttributeList.assert_not_called()

    def test_foreign_entry_pin_and_bool_limit_rejected_before_api(self):
        allocation=self.allocation();allocation['value']['entry_pin']['sha256']='b'*64
        self.repin(allocation)
        with self.assertRaises(ValueError):self.arm(allocation)
        self.assertIs(self.owner.original_publication_native_buffers.allocation_input,allocation)
        self.k.InitializeProcThreadAttributeList.assert_not_called()

    def test_bool_limit_is_not_independent_positive_integer(self):
        allocation=self.allocation();allocation['value']['limits']['member']=True;self.repin(allocation)
        with self.assertRaises(ValueError):self.arm(allocation)
        self.k.InitializeProcThreadAttributeList.assert_not_called()

    def test_attribute_size_rejected_before_buffer_allocation_and_update(self):
        allocation=self.allocation();allocation['value']['limits']['attributes']=95;self.repin(allocation)
        b=self.arm(allocation);a=self.f.new()
        with self.assertRaises(ValueError) as caught:a.prepare()
        self.assertIs(caught.exception.publication_native_buffers,b);self.assertIsNone(a.buffer)
        self.assertEqual(a.pending['return'],0);self.assertEqual(b.rejected_claim['sizes_input']['attributes'],96)
        self.k.UpdateProcThreadAttribute.assert_not_called();self.no_native()

    def test_command_limit_rejects_before_command_pi_or_api_getter(self):
        allocation=self.allocation();allocation['value']['limits']['command']=1;self.repin(allocation)
        b=self.arm(allocation);a=self.attributes()
        with patch.object(type(self.k),'AssignProcessToJobObject',property(lambda _:(_ for _ in ()).throw(AssertionError('getter forbidden'))),create=True):
            with self.assertRaises(ValueError) as caught:self.process(a)
        p=caught.exception.publication_native_process
        self.assertIs(p.raw_owner,self.job);self.assertFalse(hasattr(p,'command'))
        self.assertIs(b.rejected_claim['sources_input'][2],self.job);self.no_native()

    def test_update_unknown_keeps_partial_original_buffers_and_same_first_exception(self):
        b=self.arm();failure=KeyboardInterrupt('Update unknown');self.k.UpdateProcThreadAttribute.side_effect=failure
        a=self.f.new()
        with self.assertRaises(KeyboardInterrupt) as caught:a.prepare()
        self.assertIs(caught.exception,failure);self.assertIs(b.original_error,failure)
        self.assertIs(b.pending['sources'][-1],a);self.assertIs(a.buffer,a.native.attributes)
        b.error=None
        with self.assertRaises(KeyboardInterrupt) as again:b.view()
        self.assertIs(again.exception,failure);self.no_native()

    def test_descriptor_caller_mutation_latches_and_cached_view_cannot_follow_restore(self):
        allocation=self.allocation();b=self.arm(allocation);allocation['value']['total_bytes']-=1
        with self.assertRaises(ValueError) as caught:b.view()
        allocation['value']['total_bytes']+=1;b.error=None
        with self.assertRaises(ValueError) as again:b.view()
        self.assertIs(caught.exception,again.exception);self.no_native()

    def test_claim_ledger_or_pending_erasure_cannot_hide_retained_bytes(self):
        b=self.arm();a=self.attributes();b.records=()
        with self.assertRaises(ValueError):b.view()
        self.assertEqual(len(b.original_records),2);self.assertIs(b.original_completed[-1][1][0],a.buffer)
        self.no_native()

    def test_out_of_order_process_claim_keeps_refused_original_sources(self):
        b=self.arm();source=object()
        with self.assertRaises(ValueError):b.claim('process',{'invocation':1,'command':1,'process':1,'member':1},(b'x',source,self.job,self))
        self.assertIs(b.rejected_claim['sources_input'][1],source);self.assertIsNone(b.pending)
        self.assertEqual(len(b.records),1);self.no_native()

    def test_second_allocation_retains_first_descriptor_and_rejected_owner(self):
        b=self.arm();allocation=self.allocation()
        with self.assertRaises(ValueError) as caught:self.arm(allocation)
        self.assertIs(caught.exception.publication_native_buffers,b)
        self.assertIs(caught.exception.rejected_publication_native_buffers,b.rejected)
        self.assertIs(b.rejected.original_inputs[0],allocation);self.assertIs(self.owner.original_publication_native_buffers,b)

    def test_cached_views_do_not_reissue_attribute_or_process_api_or_clock(self):
        b=self.arm();a=self.attributes();p=self.process(a);p.prepare();before=b.view()
        self.f.f.f.checkpoint.reset_mock();self.k.InitializeProcThreadAttributeList.reset_mock();self.k.UpdateProcThreadAttribute.reset_mock()
        self.assertEqual(b.view(),before);self.assertIs(a.prepare(),a.result);self.assertIs(p.prepare(),p.result)
        self.f.f.f.checkpoint.assert_not_called();self.k.InitializeProcThreadAttributeList.assert_not_called()
        self.k.UpdateProcThreadAttribute.assert_not_called();self.no_native()

    def test_parent_entry_storage_clock_route_and_unknown_share_owner_remain_denied(self):
        parent,launch=self.f.f.parent_launch();self.addCleanup(self.f.f.f.f.doCleanups)
        launch.prepare_inheritance();launch.offer_inheritance()
        b=launch.arm_native_buffers(self.allocation(launch))
        a=launch.prepare_handle_list((201,202,203),last_error=self.f.last_error)
        p=launch.prepare_native_process((sys.executable,'-c','pass'),str(launch.endpoint.root),self.job)
        self.assertIs(b.owner,launch);self.assertIs(b.storage,parent.original_publication_storage)
        self.assertIs(a.buffer_admission,p.buffer_admission);self.assertTrue(launch.unresolved())
        with self.assertRaises(ValueError):p.execute()
        self.assertIs(b.original_error,p.original_error);self.no_native()

    def test_attribute_admission_reference_erasure_rejected_before_sizing_api(self):
        b=self.arm();a=self.f.new();a.buffer_admission=None
        with self.assertRaises(ValueError) as caught:a.prepare()
        self.assertIs(a.original_buffer_admission,b)
        self.assertIs(caught.exception.publication_native_buffers,b)
        self.assertEqual(len(b.original_records),1)
        self.k.InitializeProcThreadAttributeList.assert_not_called();self.no_native()


if __name__=='__main__':unittest.main()
