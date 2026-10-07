"""Spawn cleanup keeps original handles and attribute buffer: fake Win API only."""
import ctypes
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_preformal_job_tree_owner as owner
from banto_ai import anomaly_v03_preformal_child_git_keeper as keeper


class SpawnCleanupOwnerTests(unittest.TestCase):
    def setUp(self):
        self.deleted_error=self.close_error=None
        self.close_false=set();self.assigned=True;self.closed=[];self.attribute=None
        self.next_duplicate=60
        def duplicate(current,source,current2,out,*args):
            self.next_duplicate+=1
            ctypes.cast(out,ctypes.POINTER(owner.w.HANDLE))[0]=self.next_duplicate
            return True
        def initialize(attributes,count,flags,size):
            ctypes.cast(size,ctypes.POINTER(ctypes.c_size_t))[0]=128
            return attributes is not None
        def create(*args):
            info=ctypes.cast(args[-1],ctypes.POINTER(owner._ProcessInformation)).contents
            info.hProcess=22;info.hThread=33;info.dwProcessId=44
            return True
        def member(process,job,out):
            ctypes.cast(out,ctypes.POINTER(owner.w.BOOL))[0]=1
            return True
        def delete(attributes):
            self.attribute=attributes
            if self.deleted_error is not None:raise self.deleted_error
        def close(handle):
            self.closed.append(handle)
            if handle==62 and self.close_error is not None:raise self.close_error
            return handle not in self.close_false
        self.kernel=SimpleNamespace(GetCurrentProcess=Mock(return_value=99),
            DuplicateHandle=Mock(side_effect=duplicate),InitializeProcThreadAttributeList=Mock(side_effect=initialize),
            UpdateProcThreadAttribute=Mock(return_value=True),CreateProcessW=Mock(side_effect=create),
            AssignProcessToJobObject=Mock(side_effect=lambda *args:self.assigned),IsProcessInJob=Mock(side_effect=member),
            DeleteProcThreadAttributeList=Mock(side_effect=delete),CloseHandle=Mock(side_effect=close),
            TerminateJobObject=Mock(return_value=True),TerminateProcess=Mock(return_value=True))
        self.enterContext(patch.dict(sys.modules,{'msvcrt':SimpleNamespace(get_osfhandle=lambda fd:100+fd)}))
        self.enterContext(patch.object(ctypes,'get_last_error',return_value=5,create=True))
        self.enterContext(patch.object(owner,'_new_job',return_value=11))
        self.wait=self.enterContext(patch.object(owner,'_wait_empty',return_value=(
            {'total_processes':1,'active_processes':0,'limit_terminated_processes':0},17)))

    def spawn(self):
        streams=[SimpleNamespace(fileno=lambda n=n:n) for n in range(3)]
        return owner._spawn_cli(self.kernel,['fixture'],'fixture-root',*streams)

    def test_success_returns_same_original_tuple_after_stdio_and_attribute_cleanup(self):
        self.assertEqual(self.spawn(),(11,22,33,44));self.assertEqual(self.closed,[61,62,63])
        self.kernel.DeleteProcThreadAttributeList.assert_called_once()
        self.kernel.TerminateJobObject.assert_not_called();self.wait.assert_not_called()

    def test_delete_io_failure_retains_buffer_and_every_original_without_any_close(self):
        failure=OSError('invented attribute cleanup failure');self.deleted_error=failure
        with self.assertRaises(owner.UnreapedJob) as caught:self.spawn()
        retained=caught.exception
        self.assertEqual((retained.job,retained.process,retained.thread),(11,22,33))
        self.assertEqual(retained.extra_handles,{'inherited_0':61,'inherited_1':62,'inherited_2':63})
        self.assertIs(retained.attributes,self.attribute);self.assertTrue(retained.attribute_list_cleanup_pending)
        self.assertIs(retained.cleanup_error,failure);self.assertIs(retained.__cause__,failure)
        self.assertEqual(self.closed,[]);self.wait.assert_not_called()

    def test_body_and_delete_interruptions_keep_both_errors_and_unassigned_root(self):
        self.assigned=False;self.deleted_error=KeyboardInterrupt('invented Delete interruption')
        with self.assertRaises(owner.UnreapedJob) as caught:self.spawn()
        retained=caught.exception
        self.assertIsInstance(retained.original_error,OSError)
        self.assertIs(retained.cleanup_error,self.deleted_error)
        self.assertIs(retained.report['assignment_confirmed'],False);self.assertEqual(self.closed,[])

    def test_stdio_unknown_close_retains_core_and_only_failed_unattempted_duplicates(self):
        self.close_error=KeyboardInterrupt('invented stdio Close interruption')
        with self.assertRaises(owner.UnreapedJob) as caught:self.spawn()
        retained=caught.exception
        self.assertEqual(self.closed,[61,62]);self.assertEqual((retained.job,retained.process,retained.thread),(11,22,33))
        self.assertEqual(retained.extra_handles,{'inherited_1':62,'inherited_2':63})
        self.assertEqual(retained.unknown_close_handles,('inherited_1','inherited_2'))
        self.assertIs(retained.cleanup_error.close_error,self.close_error)
        self.assertFalse(retained.attribute_list_cleanup_pending);self.wait.assert_not_called()

    def test_known_stdio_false_preserves_legacy_reap_and_exact_unclosed_stdio_owner(self):
        self.close_false={62}
        with self.assertRaises(owner.UnclosedHandles) as caught:self.spawn()
        self.assertEqual(caught.exception.handles,{'inherited_1':62})
        self.assertEqual(self.closed,[61,62,63,33,22,11])
        self.kernel.TerminateJobObject.assert_called_once_with(11,0xE004);self.wait.assert_called_once()

    def test_known_stdio_false_and_failed_reap_preserve_core_and_extra_together(self):
        self.close_false={62};self.wait.side_effect=OSError('invented failed spawn reap')
        with self.assertRaises(owner.UnreapedJob) as caught:self.spawn()
        retained=caught.exception
        self.assertEqual((retained.job,retained.process,retained.thread),(11,22,33))
        self.assertEqual(retained.extra_handles,{'inherited_1':62});self.assertEqual(self.closed,[61,62,63])

    def recovery(self,retained):
        child=SimpleNamespace(stopped=False,owners={},active={0})
        child.hold_owner=lambda lease,value:child.owners.__setitem__(lease,value)
        record={'pid':44,'creation_time_100ns':111};record['start_token']=keeper.v.canonical_sha256(record)
        holder=keeper.ChildGitKeeper(retained,child=child,lease=0)
        with patch.object(owner,'_kernel',return_value=self.kernel),patch.object(keeper,'_creation',return_value=record):
            self.assertIsNone(holder.reconcile_once())
            self.assertTrue(holder.blocked);before=len(self.closed)
            self.assertIsNone(holder.reconcile_once());self.assertEqual(len(self.closed),before)
        self.assertIs(child.owners[0],retained);self.assertTrue(child.stopped)
        return holder

    def test_keeper_stops_root_but_never_redeletes_unknown_attribute_list_or_closes_handles(self):
        self.deleted_error=OSError('invented Delete failure')
        with self.assertRaises(owner.UnreapedJob) as caught:self.spawn()
        self.recovery(caught.exception)
        self.assertEqual(self.closed,[]);self.kernel.DeleteProcThreadAttributeList.assert_called_once()
        self.kernel.TerminateJobObject.assert_called_once_with(11,0xE010)

    def test_keeper_stops_unassigned_root_and_preserves_unknown_stdio_close_without_retry(self):
        self.assigned=False;self.close_error=OSError('invented Close failure')
        with self.assertRaises(owner.UnreapedJob) as caught:self.spawn()
        self.recovery(caught.exception)
        self.assertEqual(self.closed,[61,62]);self.kernel.TerminateProcess.assert_called_once_with(22,0xE011)

    def test_original_body_failure_with_successful_cleanup_reaps_and_keeps_default_error(self):
        self.assigned=False
        with self.assertRaises(OSError):self.spawn()
        self.assertEqual(self.closed,[61,62,63,33,22,11])
        self.kernel.TerminateProcess.assert_called_once_with(22,0xE005)
