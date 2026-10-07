"""A pending worker fence never falls through to ordinary kill/close cleanup."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_process_supervisor as monitor
from tests import test_anomaly_v03_process_supervisor as helpers


class WorkerStopFenceTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='banto-stop-fence-')
        self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        self.runtime=helpers.fixture_context()[1]
        self.limits={'wall_seconds':60,'private_bytes':1024**3,'output_bytes':1024**2}
        self.sequence=0
        self.enterContext(patch.object(monitor.subprocess,'CREATE_NO_WINDOW',0x08000000,create=True))

    def run_fake(self,process,fence,*,boundary=lambda:None):
        self.sequence+=1
        initial=iter([None])
        def launch(argv,**options):
            options['stdout'].write(b'{}\n');options['stdout'].flush()
            return process
        with patch.object(monitor.subprocess,'Popen',side_effect=launch), \
             patch.object(monitor.resources,'memory_bytes',return_value={'peak_private_bytes':1000}), \
             patch.object(monitor.resources,'require_start_resources',return_value={}), \
             patch.object(monitor.resources,'free_resources',return_value={}), \
             patch.object(monitor.time,'sleep'):
            return monitor.supervise(['python','fixture-only'],self.root,
                self.root/('control-'+str(self.sequence)),self.limits,
                runtime_probe=lambda:copy.deepcopy(self.runtime),boundary=boundary,
                resource_probe=lambda:next(initial,'pipeline_wall_limit'),stop_fence=fence)

    def test_invalid_fence_rejects_before_root_or_launch(self):
        target=self.root/'invalid-control'
        with patch.object(monitor.subprocess,'Popen') as launch:
            with self.assertRaisesRegex(ValueError,'must be callable'):
                monitor.supervise(['python','fixture-only'],self.root,target,self.limits,stop_fence=False)
            launch.assert_not_called();self.assertFalse(target.exists())

    def test_missing_ack_retains_original_owner_without_cleanup_or_readback(self):
        process=helpers.FakeProcess(running=True);handle=process._handle
        fence=Mock(return_value=False);boundary=Mock()
        with patch.object(monitor,'_file_pin') as read:
            with self.assertRaises(monitor.UnreconciledWorker) as caught:
                self.run_fake(process,fence,boundary=boundary)
            read.assert_not_called()
        error=caught.exception
        self.assertIs(error.process,process);self.assertIs(error.process._handle,handle)
        self.assertIs(error.stop_fence,fence);self.assertEqual((process.kills,process.waits),(0,0))
        handle.Close.assert_not_called();self.assertEqual(boundary.call_count,1)
        self.assertIs(error.report['worker_stop_fence_confirmed'],False)
        self.assertEqual(error.report['stop_reason'],'pipeline_wall_limit')
        self.assertIsNone(error.report['runtime_after']);self.assertIsNone(error.report['output'])

    def test_explicit_ack_allows_existing_bounded_kill_wait_close(self):
        process=helpers.FakeProcess(running=True);fence=Mock(return_value=True)
        report=self.run_fake(process,fence)
        self.assertEqual(report['status'],'failed');self.assertEqual(report['stop_reason'],'pipeline_wall_limit')
        self.assertEqual((process.kills,process.waits),(1,1));process._handle.Close.assert_called_once()
        fence.assert_called_once_with(process)

    def test_fence_io_failure_keeps_original_exception_and_worker(self):
        process=helpers.FakeProcess(running=True);failure=OSError('invented ack read failure')
        with self.assertRaises(monitor.UnreconciledWorker) as caught:
            self.run_fake(process,Mock(side_effect=failure))
        self.assertIs(caught.exception.fence_error,failure);self.assertIs(caught.exception.process,process)
        self.assertEqual((process.kills,process.waits),(0,0));process._handle.Close.assert_not_called()

    def test_non_bool_ack_is_not_permission_to_stop(self):
        for value in (None,1,'confirmed'):
            with self.subTest(value=value):
                process=helpers.FakeProcess(running=True)
                with self.assertRaises(monitor.UnreconciledWorker) as caught:
                    self.run_fake(process,Mock(return_value=value))
                self.assertIsInstance(caught.exception.fence_error,ValueError)
                self.assertEqual((process.kills,process.waits),(0,0));process._handle.Close.assert_not_called()

    def test_root_exit_without_job_ack_does_not_close_original_handle(self):
        process=helpers.FakeProcess()
        with self.assertRaises(monitor.UnreconciledWorker) as caught:
            self.run_fake(process,Mock(return_value=False))
        self.assertEqual(process.returncode,0);self.assertIs(caught.exception.report['worker_exit_confirmed'],True)
        self.assertIs(caught.exception.report['worker_stop_fence_confirmed'],False)
        process._handle.Close.assert_not_called();self.assertEqual(process.waits,0)

    def test_opt_in_handle_close_failure_preserves_original_owner(self):
        process=helpers.FakeProcess();failure=OSError('invented original handle close failure')
        process._handle.Close.side_effect=failure
        with self.assertRaises(monitor.UnreconciledWorker) as caught:
            self.run_fake(process,Mock(return_value=True))
        self.assertIs(caught.exception.process,process);self.assertIs(caught.exception.fence_error,failure)
        self.assertIs(caught.exception.report['worker_stop_fence_confirmed'],True)
        self.assertEqual(process.returncode,0)

    def test_unconfirmed_exit_after_ack_keeps_fence_for_later_reconciliation(self):
        process=helpers.FakeProcess(running=True)
        process.kill=Mock()
        process.wait=Mock(side_effect=OSError('invented original wait failure'))
        fence=Mock(return_value=True)
        with self.assertRaises(monitor.UnreconciledWorker) as caught:
            self.run_fake(process,fence)
        self.assertIs(caught.exception.process,process);self.assertIs(caught.exception.stop_fence,fence)
        self.assertIsNone(process.returncode);process._handle.Close.assert_not_called()
        self.assertIs(caught.exception.report['worker_stop_fence_confirmed'],True)
        process.wait.assert_called_once_with(timeout=30)

    def test_keeper_never_kills_before_ack_and_keeps_original_process(self):
        process=helpers.FakeProcess(running=True);observed=[]
        def fence(original):
            self.assertIs(original,process);observed.append(process.kills)
            return len(observed)>1
        error=monitor.UnreconciledWorker(process,{},fence)
        with patch.object(monitor.time,'sleep') as sleep:
            monitor.retain_until_exit(error)
        self.assertEqual(observed,[0,0]);self.assertEqual((process.kills,process.waits),(1,1))
        process._handle.Close.assert_called_once();sleep.assert_called_once_with(0.25)

    def test_keeper_ack_read_exception_cannot_drop_owner(self):
        process=helpers.FakeProcess(running=True);failure=OSError('invented missing ack')
        fence=Mock(side_effect=[failure,True]);error=monitor.UnreconciledWorker(process,{},fence)
        with patch.object(monitor.time,'sleep'):monitor.retain_until_exit(error)
        self.assertIs(error.process,process);self.assertIs(error.fence_error,failure)
        self.assertTrue(all(c.args==(process,) for c in fence.call_args_list))
        self.assertEqual(process.kills,1);process._handle.Close.assert_called_once()

    def test_keeper_sleep_interrupt_cannot_force_unacknowledged_worker(self):
        process=helpers.FakeProcess(running=True);fence=Mock(side_effect=[False,True])
        error=monitor.UnreconciledWorker(process,{},fence)
        with patch.object(monitor.time,'sleep',side_effect=KeyboardInterrupt):monitor.retain_until_exit(error)
        self.assertEqual(process.kills,1);self.assertEqual(fence.call_count,2)
        process._handle.Close.assert_called_once()

    def test_keeper_close_failure_keeps_original_handle_until_closed(self):
        process=helpers.FakeProcess();failure=OSError('invented close failure')
        process._handle.Close.side_effect=[failure,None]
        error=monitor.UnreconciledWorker(process,{},Mock(return_value=True))
        with patch.object(monitor.time,'sleep'):monitor.retain_until_exit(error)
        self.assertEqual(process.kills,0);self.assertEqual(process._handle.Close.call_count,2)
        self.assertIs(error.fence_error,failure)

    def test_keeper_kill_interrupt_retains_owner_and_rechecks_fence(self):
        process=helpers.FakeProcess(running=True);original_kill=process.kill;calls=[]
        def kill():
            calls.append(True)
            if len(calls)==1:raise KeyboardInterrupt
            original_kill()
        process.kill=kill;fence=Mock(return_value=True)
        error=monitor.UnreconciledWorker(process,{},fence)
        with patch.object(monitor.time,'sleep'):monitor.retain_until_exit(error)
        self.assertIs(error.process,process);self.assertEqual(fence.call_count,2)
        self.assertEqual((process.kills,process.waits),(1,1));process._handle.Close.assert_called_once()
