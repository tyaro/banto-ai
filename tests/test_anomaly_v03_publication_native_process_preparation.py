"""Unissued raw Job/process frames; fake APIs, no process creation."""
import os
import sys
from types import SimpleNamespace
from unittest.mock import Mock,patch
import unittest
from tests import test_anomaly_v03_publication_handle_list as attributes

native=attributes.native


class PublicationNativeProcessPreparationTests(unittest.TestCase):
    def setUp(self):
        self.f=attributes.PublicationHandleListTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.a=self.f.ready();self.k=self.f.k;self.owner=self.f.owner
        self.owner.entry_raw=b'{"format":"fake-entry","formal_permission":false}'
        self.k.AssignProcessToJobObject=Mock(side_effect=AssertionError('actual assign forbidden'))
        self.k.IsProcessInJob=Mock(side_effect=AssertionError('actual membership forbidden'))
        self.job=native.UnreapedJob(701,None,None,{'fixture_only':True})
        self.argv=(sys.executable,'-c','pass');self.cwd=os.getcwd()

    def new(self,job=None):
        return native.PublicationNativeProcessPreparation(self.a,self.argv,self.cwd,
            self.job if job is None else job,owner=self.owner,binding=self.owner.entry_raw)

    def no_native(self):
        for api in (self.k.CreateProcessW,self.k.AssignProcessToJobObject,self.k.IsProcessInJob,
                    self.k.CloseHandle,self.k.DeleteProcThreadAttributeList):api.assert_not_called()

    def test_retains_exact_raw_owner_slots_attribute_and_separate_five_handles(self):
        p=self.new();result=p.prepare()
        self.assertIs(result['raw_job_owner'],self.job);self.assertIs(result['attribute_owner'],self.a)
        self.assertIs(result['create_args'],p.create_args);self.assertIs(p.create_args[1],p.command)
        self.assertEqual((result['stdio_count'],result['dedicated_count'],result['explicit_handle_count']),(3,2,5))
        self.assertIs(p.assignment_source[1],self.job);self.assertIs(p.membership_source[-1],p.member_output)
        self.assertEqual(tuple(p.a.handles) if hasattr(p,'a') else tuple(self.a.handles),(201,202,203,301,302))
        for key in ('native_launch_authorized','job_ownership_observed','creation_observed','native_owner_recovered',
                    'parent_ack_authorized','execution_authenticated','atomic_reservation','capacity_pass'):self.assertFalse(result[key])
        self.assertTrue(all(row['return'] is None and not row['return_observed'] for row in p.return_slots))
        self.assertTrue(p.unresolved());self.no_native()

    def test_cached_prepare_has_no_clock_or_native_replay(self):
        p=self.new();result=p.prepare();clock=self.f.f.f.checkpoint;clock.reset_mock()
        self.assertIs(p.prepare(),result);clock.assert_not_called();self.no_native()

    def test_execute_denied_before_clock_even_with_forged_success_flags(self):
        p=self.new();result=p.prepare();result['native_launch_authorized']=True
        clock=self.f.f.f.checkpoint;clock.reset_mock()
        with self.assertRaises(ValueError) as caught:p.execute()
        self.assertIs(caught.exception,p.original_error);self.assertIs(caught.exception.publication_native_process,p)
        p.error=None;self.a.error=None
        with self.assertRaises(ValueError) as again:p.execute()
        self.assertIs(again.exception,caught.exception);clock.assert_not_called();self.no_native()

    def test_raw_job_alias_stdio_rejected_with_original_input(self):
        self.job.job=201
        with self.assertRaises(ValueError) as caught:self.new()
        self.assertIs(caught.exception.publication_native_process.original_inputs[3],self.job);self.no_native()

    def test_bool_job_is_not_positive_native_handle(self):
        self.job.job=True
        with self.assertRaises(ValueError):self.new()
        self.no_native()

    def test_foreign_job_record_is_retained_without_owner_adoption(self):
        foreign=SimpleNamespace(job=701,process=None,thread=None)
        with self.assertRaises(ValueError) as caught:self.new(foreign)
        self.assertIs(caught.exception.publication_native_process.raw_owner,foreign);self.no_native()

    def test_clock_interrupt_keeps_same_error_raw_owner_and_input_pending(self):
        p=self.new();failure=KeyboardInterrupt('original clock unknown')
        self.f.f.f.checkpoint.side_effect=failure
        with self.assertRaises(KeyboardInterrupt) as caught:p.prepare()
        self.assertIs(caught.exception,failure);self.assertIs(p.pending['original_inputs'][3],self.job)
        p.error=None;self.owner.publication_native_process=p
        with self.assertRaises(KeyboardInterrupt) as again:p.prepare()
        self.assertIs(again.exception,failure);self.no_native()

    def test_callback_command_change_keeps_original_buffer_and_refuses_following(self):
        p=self.new();self.f.f.f.checkpoint.side_effect=lambda:setattr(p.command,'value','changed')
        with self.assertRaises(ValueError):p.prepare()
        self.assertIs(p.command,p.original_command);self.assertEqual(p.command.value,'changed');self.no_native()

    def test_unissued_process_output_change_is_not_creation_observation(self):
        p=self.new();p.process_information.hProcess=801;p.member_output.value=1
        with self.assertRaises(ValueError):p.prepare()
        self.assertEqual(p.process_information.hProcess,801);self.assertFalse(p.return_slots[0]['return_observed'])
        self.assertIsNone(self.job.process);self.no_native()

    def test_caller_return_metadata_is_rejected_and_cannot_prove_original_return(self):
        p=self.new();p.return_slots[0]['return']=1;p.return_slots[0]['return_observed']=True
        with self.assertRaises(ValueError):p.prepare()
        self.assertFalse(p.original_slots[0][1]['return_observed']);self.no_native()

    def test_foreign_same_handle_owner_cannot_replace_original_tuple(self):
        p=self.new();foreign=native.UnreapedJob(701,None,None,{})
        foreign.original_publication_native_process=foreign.publication_native_process=p;p.raw_owner=foreign
        with self.assertRaises(ValueError):p.prepare()
        self.assertIs(p.original_inputs[3],self.job);self.no_native()

    def test_second_preparation_retains_first_error_and_both_owners(self):
        first=self.new();first.prepare()
        with self.assertRaises(ValueError) as caught:self.new(native.UnreapedJob(702,None,None,{}))
        self.assertIs(caught.exception.publication_native_process,first)
        self.assertIs(caught.exception.rejected_publication_native_process,first.rejected)
        self.assertIs(self.owner.original_publication_native_process,first);self.no_native()

    def test_attribute_marker_erase_cannot_enable_early_delete(self):
        p=self.new();p.prepare();del self.a.original_native_process
        with self.assertRaises(ValueError):self.a.cleanup_unlaunched()
        self.assertIs(self.a.buffer,self.a.native.attributes);self.no_native()

    def test_api_getter_interrupt_keeps_output_buffers_before_any_native_call(self):
        failure=KeyboardInterrupt('Assign API getter unknown')
        with patch.object(type(self.k),'AssignProcessToJobObject',property(lambda _:(_ for _ in ()).throw(failure)),create=True):
            with self.assertRaises(KeyboardInterrupt) as caught:self.new()
        p=caught.exception.publication_native_process
        self.assertIs(caught.exception,failure);self.assertIs(p.raw_owner,self.job)
        self.assertIs(p.process_information,p.original_information);self.no_native()

    def parent_launch(self):
        parent,launch=self.f.f.parent_launch();self.addCleanup(self.f.f.f.f.doCleanups)
        launch.prepare_inheritance();launch.offer_inheritance()
        launch.prepare_handle_list((201,202,203),last_error=self.f.last_error)
        return parent,launch

    def test_parent_storage_entry_forwarding_retains_raw_owner_and_rejects_popen_before_getter(self):
        parent,launch=self.parent_launch()
        p=launch.prepare_native_process(self.argv,str(launch.endpoint.root),self.job)
        self.assertIs(p.binding,launch.entry_raw);self.assertIs(p.owner,launch);self.assertTrue(launch.unresolved())
        class ForeignProcess:
            @property
            def _handle(self):raise AssertionError('Popen getter must not run')
        process=ForeignProcess()
        with self.assertRaises(ValueError):launch.bind(process)
        self.assertIs(launch.rejected_process,process);self.assertIs(p.raw_owner,self.job);self.no_native()

    def test_parent_wrong_cwd_keeps_original_caller_inputs_before_validation(self):
        parent,launch=self.parent_launch();foreign=native.UnreapedJob(702,None,None,{})
        with self.assertRaises(ValueError):launch.prepare_native_process(self.argv,self.cwd,foreign)
        held=launch.initializing_publication_native_process
        self.assertIs(held.caller_inputs[3],foreign);self.no_native()

    def test_parent_denial_is_same_error_for_cached_raw_preparation_after_metadata_restore(self):
        parent,launch=self.parent_launch()
        p=launch.prepare_native_process(self.argv,str(launch.endpoint.root),self.job)
        with self.assertRaises(ValueError) as caught:launch.bind(SimpleNamespace())
        launch.error=None;launch.publication_native_process=p
        with self.assertRaises(ValueError) as again:p.prepare()
        self.assertIs(again.exception,caught.exception);self.assertIs(p.original_error,caught.exception)
        self.assertIs(p.raw_owner,self.job);self.no_native()


if __name__=='__main__':unittest.main()
