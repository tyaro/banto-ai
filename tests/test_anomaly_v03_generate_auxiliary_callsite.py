"""New generate exception callsites; original Python writer/keeper fixtures.

Upstream publication composition is explicitly stubbed. No native process or
child transport is run, and retained caller objects are not diagnostic bytes.
"""
import copy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

from banto_ai import anomaly_v03_preformal_reader_git_worker as reader
from banto_ai import anomaly_v03_preformal_owned_generated_attempt as generated
from tests import test_anomaly_v03_request_auxiliary_writer_io as fixtures
from tests import test_anomaly_v03_reader_git_parent_connection as callers

OBSERVATIONS=[]


class RetentionEscape(BaseException):pass


class GenerateAuxiliaryCallsiteTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.RequestAuxiliaryWriterIOTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        a=fixtures.archive;b=fixtures.budget
        p=self.parent=reader.ReaderGitParent.__new__(reader.ReaderGitParent)
        p.error=None;p.inventory_checkpoint=self.f.clock;p.worker=None
        p.inventory_publication_error=p.inventory_pending_owner=None
        p.original_bootstrap_inputs=(None,)*10;p.parent=self.f.s.endpoint
        gate=a.ControlPublicationAdmission(endpoint=p.parent,inventory_pin=self.f.s.inventory_pin,
            root_identity=self.f.s.identity,control_limits=self.f.s.gate.control_limits,
            checkpoint=self.f.clock,owner=p)
        p.inventory_publication=gate
        storage=a.PublicationStorageAdmission(endpoint=p.parent,inventory_raw=self.f.s.inventory_raw,
            inventory_pin=self.f.s.inventory_pin,root_identity=self.f.s.identity,
            allocation=self.f.s.allocation,checkpoint=self.f.clock,owner=p)
        publication=b.PartitionedPublicationPreparation.__new__(b.PartitionedPublicationPreparation)
        publication.owner=p;publication.checkpoint=self.f.clock
        publication.original_inputs=(p,self.f.clock,None,self.f.maxima,None,self.f.preparation.context_raw,None)
        publication._fixed=Mock()  # Upstream composition only, not the new callsite or keeper.
        declaration=copy.deepcopy(self.f.preparation.original_inputs[3])
        participants=tuple(zip(b.RequestWriterPreparation.ROLES,
            (gate,object(),object(),self.f.writers['parent_failure'],self.f.writers['diagnostic'])))
        p.prepare_request_writers(publication=publication,declaration=declaration,participants=participants)
        p.connect_request_writers_to_storage(storage)
        for role,writer in self.f.writers.items():p.connect_auxiliary_writer(role,writer)
        self.f.clock.reset_mock()

    def caller(self,error):
        f=callers.ReaderGitCallerConnectionTests();f.setUp();self.addCleanup(f.doCleanups)
        error.reader_git_parent=self.parent;f.create.side_effect=error
        return f

    def actual_catch(self,error):
        f=self.caller(error)
        with patch.object(reader.ParentPublicationRetention,'_pause',side_effect=RetentionEscape()),self.assertRaises(RetentionEscape):
            f.execute()
        held=error.parent_publication_retention;row=held._ParentPublicationRetention__auxiliary_callsite
        self.assertIs(held.parent,self.parent);self.assertIs(held.original_error,error)
        callsite=row['incoming'][0]
        self.assertIs(callsite[0],error);self.assertEqual(callsite[1],'generator')
        self.assertEqual(callsite[2],f.f.attempt/'owned-generator');self.assertIs(callsite[3],error.reader_auxiliary_callsite_inputs[3])
        self.assertIs(held.original_caller_plan,f.plan)
        self.assertFalse((f.f.attempt/'owned-generator/result.json').exists())
        self.assertFalse((f.f.attempt/'owned-generator/invocation.json').exists())
        self.f.clock.assert_not_called()
        for role,writer in self.f.writers.items():
            self.assertIs(writer._RequestAuxiliaryWriter__callsite_inputs[0],held)
            self.assertIs(writer._RequestAuxiliaryWriter__callsite_inputs[1],callsite)
            self.assertIs(writer._RequestAuxiliaryWriter__failure,error)
            self.assertEqual(writer._RequestAuxiliaryWriter__operations,())
        OBSERVATIONS.append({'test':self.id(),'role':callsite[1],'target_name':callsite[2].name,
            'result':copy.deepcopy(callsite[3]),'writer_roles':[r['role'] for r in row['observations']],
            'same_original_error':True,'native_runs':0,'diagnostic_bytes_issued':False})
        return f,held,row

    def test_oserror_actual_generate_catch_connects_both_original_writers_before_diagnostics(self):
        self.actual_catch(OSError('original auxiliary caller failure'))

    def test_resource_stop_actual_generate_catch_keeps_reason_and_clock_without_publication(self):
        error=generated.resources.ResourceStop('original auxiliary stop')
        _,held,_=self.actual_catch(error);self.assertEqual(held.original_error.reason,'original auxiliary stop')

    def test_interrupt_actual_generate_catch_retains_original_before_return(self):
        self.actual_catch(KeyboardInterrupt('original interrupted callsite'))

    def test_error_formatting_callback_is_not_invoked_before_original_callsite_binding(self):
        class Unformattable(ValueError):
            def __str__(self):raise AssertionError('caller formatted before original keeper')
        self.actual_catch(Unformattable())

    def test_original_unreconciled_report_and_keeper_are_bound_before_any_diagnostic_file(self):
        process=SimpleNamespace(pid=8123,_handle=object());report={'worker_started':True,'worker_pid':8123}
        fence=Mock(return_value=False);failure=OSError('original fence failure')
        error=generated.supervisor.UnreconciledWorker(process,report,fence,failure)
        with patch.object(generated.supervisor,'retain_until_exit',return_value=None) as keeper:
            _,held,row=self.actual_catch(error)
        keeper.assert_called_once_with(error);self.assertIs(row['report'],report)
        self.assertTrue(row['report_return_observed']);self.assertIs(held.existing_worker_error,error)
        self.assertIs(error.process,process);self.assertIs(error.stop_fence,fence);fence.assert_not_called()

    def test_cached_callsite_keeps_first_input_when_display_registry_and_error_are_erased(self):
        error=OSError('first callsite');_,held,row=self.actual_catch(error)
        original=row['incoming'];self.parent._ReaderGitParent__auxiliary_writer_owners=None
        self.parent.error=None;held.auxiliary_callsite=None
        for writer in self.f.writers.values():writer.callsite_inputs=writer.error=None
        later=KeyboardInterrupt('later callsite');inputs=(later,'reader',Path('later-target'),{'later':True})
        with patch.object(reader.ParentPublicationRetention,'_pause',side_effect=RetentionEscape()),self.assertRaises(RetentionEscape):
            reader.retain_parent_publications(later,self.parent,caller_diagnostics=inputs)
        self.assertIs(self.parent.original_publication_retention,held)
        self.assertIs(held._ParentPublicationRetention__auxiliary_callsite,row);self.assertIs(row['incoming'],original)
        self.assertIs(held.rejected_auxiliary_callsite[0],inputs)
        for writer in self.f.writers.values():self.assertIs(writer._RequestAuxiliaryWriter__callsite_inputs[1],original[0])

    def test_callback_swallowing_original_failure_retains_unknown_return_without_replay(self):
        error=OSError('callback original');f=self.caller(error);writer=self.f.writers['diagnostic']
        callback=writer.retain_callsite_inputs;unknown=object()
        def swallowed(*args):
            try:callback(*args)
            except OSError as caught:self.assertIs(caught,error)
            return unknown
        with (patch.object(writer,'retain_callsite_inputs',side_effect=swallowed) as call,
              patch.object(reader.ParentPublicationRetention,'_pause',side_effect=RetentionEscape()),self.assertRaises(RetentionEscape)):
            f.execute()
        call.assert_called_once();held=error.parent_publication_retention;row=held.auxiliary_callsite['observations'][1]
        self.assertIs(row['return'],unknown);self.assertTrue(row['return_observed'])
        self.assertIsInstance(row['error'],ValueError);self.assertIs(held.original_error,error)
        self.assertIs(writer._RequestAuxiliaryWriter__failure,error)

    def test_foreign_registry_participant_is_kept_and_not_invoked_as_original_writer(self):
        foreign=SimpleNamespace(retain_callsite_inputs=Mock());p=self.parent
        registry=(p._ReaderGitParent__auxiliary_writer_owners[0],('diagnostic',foreign))
        p._ReaderGitParent__auxiliary_writer_owners=registry
        error=OSError('foreign candidate');f=self.caller(error)
        with patch.object(reader.ParentPublicationRetention,'_pause',side_effect=RetentionEscape()),self.assertRaises(RetentionEscape):f.execute()
        held=error.parent_publication_retention;foreign.retain_callsite_inputs.assert_not_called()
        self.assertIs(held.auxiliary_callsite['incoming'][1],registry)
        self.assertIs(held.auxiliary_callsite['observations'][-1]['writer'],foreign)
        self.assertIs(held.original_error,error);self.assertIsInstance(held.auxiliary_callsite['diagnostic_error'],ValueError)

    def test_failed_report_getter_keeps_caller_error_candidates_before_original_keeper(self):
        secondary=KeyboardInterrupt('original report getter interrupted')
        class InterruptedReport(OSError):
            @property
            def report(self):raise secondary
        error=InterruptedReport();f=self.caller(error)
        with patch.object(reader.ParentPublicationRetention,'_pause',side_effect=RetentionEscape()),self.assertRaises(RetentionEscape):f.execute()
        row=error.parent_publication_retention.auxiliary_callsite
        self.assertIs(row['incoming'][0][0],error);self.assertIs(row['incoming'][1],self.parent._ReaderGitParent__auxiliary_writer_owners)
        self.assertIs(row['diagnostic_error'],secondary);self.assertFalse(row['report_return_observed'])
        self.assertIs(error.parent_publication_retention.original_error,error)

    def test_report_getter_interrupt_still_forwards_first_original_input_to_both_writers(self):
        secondary=KeyboardInterrupt('report read after candidate retention')
        class InterruptedReport(OSError):
            @property
            def report(self):raise secondary
        error=InterruptedReport();_,held,row=self.actual_catch(error)
        self.assertIs(row['diagnostic_error'],secondary);self.assertFalse(row['report_return_observed'])
        self.assertEqual([r['error'] for r in row['observations']],[error,error])
        self.assertIs(held.original_error,error)

    def test_reentry_from_writer_callback_retains_rejected_callsite_without_second_callback(self):
        error=OSError('first callsite reentry');f=self.caller(error)
        writer=self.f.writers['parent_failure'];callback=writer.retain_callsite_inputs
        later=(KeyboardInterrupt('nested candidate'),'reader',Path('nested-target'),{'nested':True})
        def nested(held,callsite):
            held.connect_auxiliary_callsite(later,())
            return callback(held,callsite)
        with (patch.object(writer,'retain_callsite_inputs',side_effect=nested) as call,
              patch.object(reader.ParentPublicationRetention,'_pause',side_effect=RetentionEscape()),self.assertRaises(RetentionEscape)):
            f.execute()
        call.assert_called_once();held=error.parent_publication_retention
        self.assertIs(held.rejected_auxiliary_callsite[0],later)
        self.assertIs(held.auxiliary_callsite['incoming'][0][0],error)
        self.assertEqual(len(held.auxiliary_callsite['observations']),2)
        self.assertIs(writer._RequestAuxiliaryWriter__failure,error);self.f.clock.assert_not_called()

    def test_preexisting_unknown_pending_and_first_writer_error_survive_actual_caller_connection(self):
        writer=self.f.writers['parent_failure'];stream=object();raw=b'original pending candidate\x00'
        pending={'raw':raw,'stream':stream,'close_return':None,'close_return_observed':False}
        writer._RequestAuxiliaryWriter__operations=(pending,)
        writer._RequestAuxiliaryWriter__pending=writer.pending=pending
        error=OSError('original unknown writer return')
        with self.assertRaises(OSError) as first:writer._failed(error)
        self.assertIs(first.exception,error);f=self.caller(error)
        with (patch.object(fixtures.archive.proof.tree.file_io,'FileIO') as opened,
              patch.object(reader.ParentPublicationRetention,'_pause',side_effect=RetentionEscape()),self.assertRaises(RetentionEscape)):
            f.execute()
        opened.assert_not_called();held=error.parent_publication_retention
        self.assertIs(writer._RequestAuxiliaryWriter__callsite_binding[2],pending)
        self.assertIs(writer.pending,pending);self.assertIs(pending['stream'],stream);self.assertIs(pending['raw'],raw)
        self.assertFalse(pending['close_return_observed']);self.assertIs(writer._RequestAuxiliaryWriter__failure,error)
        self.assertIs(held.original_error,error);self.f.clock.assert_not_called()


if __name__=='__main__':unittest.main()
