"""Caller terminal retention with fake native owners and real small pending files."""
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_preformal_reader_git_worker as reader
from banto_ai import anomaly_v03_preformal_owned_generated_attempt as generated
from tests import test_anomaly_v03_request_bootstrap_publication as bootstrap
from tests import test_anomaly_v03_parent_inventory_publication as inventory
from tests import test_anomaly_v03_reader_git_parent_connection as callers


class RetentionEscape(BaseException):
    """Test-only escape; production pause catches interruptions and keeps the owner."""


class ParentPublicationRetentionTests(unittest.TestCase):
    def bootstrap_failure(self, *, close=False, stopped=False):
        f=bootstrap.RequestBootstrapPublicationTests();f.setUp();self.addCleanup(f.doCleanups)
        if stopped:
            f.f.f.budget.probe.return_value='fixture_request_stop'
            with self.assertRaises(reader.monitor.resources.ResourceStop) as caught:f.create()
        else:
            inject,original,_=f.injection(close=close)
            with inject,self.assertRaises(KeyboardInterrupt if close else OSError) as caught:f.create()
            self.assertIs(caught.exception,original)
        return caught.exception.reader_git_parent,caught.exception

    def caller(self, failure):
        f=callers.ReaderGitCallerConnectionTests();f.setUp();self.addCleanup(f.doCleanups)
        f.create.side_effect=failure
        return f

    def escape(self):return patch.object(reader.ParentPublicationRetention,'_pause',side_effect=RetentionEscape())

    def test_real_generate_catch_holds_partial_bootstrap_before_result_or_invocation_file(self):
        p,error=self.bootstrap_failure();pending=p.original_request_bootstrap.pending;f=self.caller(error)
        with self.escape(),self.assertRaises(RetentionEscape):f.execute()
        held=error.parent_publication_retention
        self.assertIs(held.parent,p);self.assertIs(held.original_error,error)
        self.assertIs(held.original_caller_plan,f.plan);self.assertIn(pending,held.pending)
        self.assertIs(p.original_request_bootstrap.pending,pending)
        self.assertFalse((f.f.attempt/'owned-generator/result.json').exists())
        self.assertFalse((f.f.attempt/'owned-generator/invocation.json').exists())

    def test_real_generate_keyboard_interrupt_keeps_closed_unknown_return_owner_before_exit(self):
        p,error=self.bootstrap_failure(close=True);pending=p.original_request_bootstrap.pending;f=self.caller(error)
        with self.escape(),self.assertRaises(RetentionEscape):f.execute()
        held=error.parent_publication_retention
        self.assertIs(held.original_error,error);self.assertIn(pending,held.pending)
        self.assertTrue(pending['stream'].closed);self.assertFalse(pending['close_return_observed'])
        self.assertFalse((f.f.attempt/'owned-generator/result.json').exists())

    def test_real_generate_resource_stop_keeps_original_clock_raw_and_bootstrap_owner(self):
        p,error=self.bootstrap_failure(stopped=True);f=self.caller(error)
        with self.escape(),self.assertRaises(RetentionEscape):f.execute()
        held=error.parent_publication_retention;gate=p.original_request_bootstrap
        self.assertIs(held.original_error,error);self.assertEqual(error.reason,'fixture_request_stop')
        self.assertIn(gate.pending,held.pending);self.assertIsNone(gate.pending['stream'])
        self.assertIsNotNone(gate.pending['raw']);self.assertEqual(gate.clock['started_at'],100.0)
        self.assertFalse((f.f.attempt/'owned-generator/result.json').exists())

    def test_inventory_pending_stream_and_bootstrap_completed_owner_are_both_retained(self):
        f=inventory.ParentInventoryPublicationTests();f.setUp();self.addCleanup(f.doCleanups)
        inject,error,_=f.injection()
        with inject,self.assertRaises(OSError):f.create()
        p=error.reader_git_parent;pending=p.inventory_publication.pending
        with self.escape(),self.assertRaises(RetentionEscape):reader.retain_parent_publications(error,p)
        held=error.parent_publication_retention
        self.assertIn(p.original_request_bootstrap,held.owners);self.assertIn(p.inventory_publication,held.owners)
        self.assertIn(pending,held.pending);self.assertFalse(pending['stream'].closed)

    def worker_caller(self, *, interrupt=False):
        p,error=self.bootstrap_failure();f=self.caller(None);f.create.side_effect=None
        def bind(process):f.process=process;p.worker=process;raise error
        f.controller.bind.side_effect=bind
        pause=KeyboardInterrupt('original worker retention interrupted') if interrupt else None
        with (patch.object(generated.supervisor,'retain_until_exit',side_effect=pause) as native_keeper,
              self.escape(),self.assertRaises(RetentionEscape)):f.execute(bind_error=error)
        native_keeper.assert_called_once();worker=native_keeper.call_args.args[0]
        self.assertIsInstance(worker,generated.supervisor.UnreconciledWorker)
        held=worker.parent_publication_retention
        self.assertIs(worker.process,f.process);self.assertIs(worker.fence_error,error)
        self.assertEqual(worker.stop_fence,f.controller.fence);self.assertIs(held.existing_worker_error,worker)
        self.assertIs(held.worker,f.process);self.assertIs(held.original_error,worker)
        self.assertFalse((f.f.attempt/'owned-generator/result.json').exists())
        self.assertTrue((f.f.attempt/'owned-generator/supervision.json').exists())  # Completed producer evidence remains.
        self.assertFalse((f.f.attempt/'owned-reader/supervision.json').exists())
        if interrupt:self.assertIs(held.worker_retention_error,pause)
        return held

    def test_existing_original_worker_keeper_return_does_not_release_python_io_or_write_diagnostics(self):
        self.worker_caller()

    def test_existing_original_worker_keeper_interrupt_keeps_original_handle_fence_error_and_raw(self):
        self.worker_caller(interrupt=True)

    def test_cached_retention_is_not_recreated_or_released_by_metadata_clearing(self):
        p,error=self.bootstrap_failure();gate=p.original_request_bootstrap;pending=gate.pending
        with self.escape(),self.assertRaises(RetentionEscape):reader.retain_parent_publications(error,p)
        held=p.original_publication_retention
        gate.pending=gate.error=None;p.error=None;p.request_bootstrap_owner=None;p.original_request_bootstrap=None
        later=OSError('later diagnostic')
        with self.escape(),self.assertRaises(RetentionEscape):reader.retain_parent_publications(later,p)
        self.assertIs(p.original_publication_retention,held);self.assertIs(later.parent_publication_retention,held)
        self.assertIs(held.original_error,error);self.assertIn(pending,held.pending);self.assertIn(gate,held.owners)

    def test_foreign_retention_sidecar_and_restore_keep_both_original_and_rejected_owner(self):
        p,error=self.bootstrap_failure()
        with self.escape(),self.assertRaises(RetentionEscape):reader.retain_parent_publications(error,p)
        held=p.original_publication_retention;foreign=SimpleNamespace(stream=object(),raw=b'foreign')
        p.publication_retention=foreign
        with self.escape(),self.assertRaises(RetentionEscape):reader.retain_parent_publications(error,p)
        self.assertEqual(held.rejected_retention,(held,foreign));p.publication_retention=held
        with self.escape(),self.assertRaises(RetentionEscape):reader.retain_parent_publications(error,p)
        self.assertEqual(held.rejected_retention,(held,foreign));self.assertIs(error.parent_publication_retention,held)

    def test_secondary_publication_diagnostic_failure_holds_original_error_and_foreign_stream(self):
        p,error=self.bootstrap_failure();failure=KeyboardInterrupt('foreign pending observation interrupted')
        class Foreign:
            stream=object()
            error=None
            @property
            def pending(self):raise failure
        foreign=Foreign();p.request_bootstrap_owner=foreign
        p.original_request_bootstrap.error=None;p.error=None
        with self.escape(),self.assertRaises(RetentionEscape):reader.retain_parent_publications(error,p)
        held=error.parent_publication_retention
        self.assertIs(held.original_error,error);self.assertIn(foreign,held.owners)
        self.assertIs(error.reader_publication_diagnostic_error,failure);self.assertIs(held.diagnostic_error,failure)

    def test_pause_interruption_is_retained_without_io_retry_or_original_error_replacement(self):
        p,error=self.bootstrap_failure()
        with self.escape(),self.assertRaises(RetentionEscape):reader.retain_parent_publications(error,p)
        held=p.original_publication_retention;failure=KeyboardInterrupt('pause interrupted')
        with (patch.object(reader.channel.time,'sleep',side_effect=failure) as sleep,
              patch.object(reader.tree.file_io,'FileIO') as opened):held._pause()
        sleep.assert_called_once_with(0.25);opened.assert_not_called()
        self.assertIs(held.pause_error,failure);self.assertIs(held.original_error,error)

    def test_healthy_observed_publications_do_not_add_retention_or_native_actions(self):
        f=inventory.ParentInventoryPublicationTests();f.setUp();self.addCleanup(f.doCleanups);p=f.create()
        with (patch.object(reader.ParentPublicationRetention,'hold') as hold,
              patch.object(reader.tree.file_io,'FileIO') as opened):
            self.assertFalse(reader.retain_parent_publications(OSError('unrelated failure'),p))
        hold.assert_not_called();opened.assert_not_called();self.assertFalse(hasattr(p,'publication_retention'))

    def test_default_file_directed_controller_keeps_original_exception_path(self):
        f=callers.ReaderGitParentControllerTests();f.setUp();self.addCleanup(f.doCleanups);p=f.create()
        error=OSError('default caller');p.error=error
        with patch.object(reader.ParentPublicationRetention,'hold') as hold:
            self.assertFalse(reader.retain_parent_publications(error,p))
        hold.assert_not_called();self.assertFalse(hasattr(p,'publication_retention'))

    def test_second_worker_error_keeps_first_and_refused_original_handles_without_fence_or_keeper_replay(self):
        p,error=self.bootstrap_failure();fence=Mock(return_value=False)
        first_process=SimpleNamespace(pid=202,_handle=object());p.worker=first_process
        first=generated.supervisor.UnreconciledWorker(first_process,{},fence,error)
        self.assertTrue(reader.retain_parent_publications(first,p))
        held=first.parent_publication_retention
        second_process=SimpleNamespace(pid=303,_handle=object())
        second=generated.supervisor.UnreconciledWorker(second_process,{},fence,error)
        with self.escape(),self.assertRaises(RetentionEscape):reader.retain_parent_publications(second,p)
        self.assertIs(held.existing_worker_error,first);self.assertEqual(held.rejected_worker_error,(first,second))
        self.assertIs(held.worker,first_process);self.assertIs(held.original_error,first);fence.assert_not_called()

    def test_upper_caller_reentry_keeps_original_callable_return_and_refuses_second_keeper_attempt(self):
        p,error=self.bootstrap_failure();process=SimpleNamespace(pid=202,_handle=object());p.worker=process
        worker=generated.supervisor.UnreconciledWorker(process,{},Mock(return_value=False),error)
        self.assertTrue(reader.retain_parent_publications(worker,p));held=worker.parent_publication_retention
        with patch.object(generated.supervisor,'retain_until_exit',return_value=None) as first,self.escape(),self.assertRaises(RetentionEscape):
            held.retain_worker(worker)
        call=held.original_worker_keeper_call
        first.assert_called_once_with(worker);self.assertIs(call['keeper'],first);self.assertIs(call['error'],worker)
        self.assertTrue(call['return_observed']);self.assertIsNone(call['return'])
        f=self.caller(worker)
        with patch.object(generated.supervisor,'retain_until_exit') as second,self.escape(),self.assertRaises(RetentionEscape):f.execute()
        second.assert_not_called();self.assertIs(held.original_worker_keeper_call,call)
        self.assertIs(held.rejected_worker_keeper_call,worker);self.assertIs(held.original_error,worker)
        self.assertFalse((f.f.attempt/'owned-generator/result.json').exists())
