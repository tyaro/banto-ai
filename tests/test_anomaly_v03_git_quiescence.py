"""Post-close links and owner retention with fake Kernel/policy/identity only."""
import copy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_preformal_owned_git_job as tree

owner, direct = tree.owner, tree.direct
ACCOUNT = {'total_processes':1,'active_processes':0,'limit_terminated_processes':0}
MEMORY = {'information_class':9,'limit_flags':0x2000,
          'peak_process_memory_used_bytes':1024,'peak_job_memory_used_bytes':2048}


class GitQuiescenceTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(prefix='banto-quiescent-git-')
        self.addCleanup(temporary.cleanup);self.root=Path(temporary.name).resolve()
        self.revision='a'*40;self.number=0
        self.identity={'pid':44,'creation_time_100ns':11}
        self.identity['start_token']=tree.v.canonical_sha256(self.identity)
        self.identity['native_start_identity_authenticated']=True
        self.pin=tree.observed._pin(b'fake executable observation')
        self.observation={'pin':self.pin,'identity':{'links':1}}
        self.policy={'revision':self.revision,'process_ownership':direct.JOB_OWNERSHIP,
            'executable_path':str(self.root/'git.exe'),'executable_pin':self.pin,
            'executable_links':1,'environment':{'PATH':'fixture'}}
        self.enterContext(patch.object(direct,'_policy',return_value=(
            self.root,self.root/'git.exe',{'PATH':'fixture'},self.observation)))
        self.enterContext(patch.object(direct.dependencies,'file_observation',return_value=self.observation))
        self.enterContext(patch.object(direct,'_identity',return_value=self.identity))
        # Module-local os proxies; do not change pathlib/global os.name on Linux CI.
        self.enterContext(patch.object(tree,'os',SimpleNamespace(name='nt',devnull=tree.os.devnull)))
        self.enterContext(patch.object(direct,'os',SimpleNamespace(name='nt')))

    def run_call(self, *, capture=True, code=0, close_failure=None, spawn_failure=None):
        self.number+=1;target=self.root/('call-'+str(self.number));closed=[]
        def close(handle):
            closed.append(handle)
            if close_failure is not None and handle==22:raise close_failure
            return True
        kernel=SimpleNamespace(ResumeThread=Mock(return_value=1),
            TerminateJobObject=Mock(return_value=True),CloseHandle=Mock(side_effect=close))
        def spawn(k,argv,root,stdin,stdout,stderr,*,environment):
            if spawn_failure is not None:raise spawn_failure
            stdout.write(self.revision.encode()+b'\n');stdout.flush()
            return 11,22,33,44
        with patch.object(owner,'_kernel',return_value=kernel), \
             patch.object(owner,'_spawn_cli',side_effect=spawn), \
             patch.object(owner,'_accounting',return_value=ACCOUNT), \
             patch.object(owner,'_root_exit',return_value=code), \
             patch.object(owner,'_wait_empty',return_value=(ACCOUNT,code)), \
             patch.object(owner,'_job_memory',return_value=MEMORY):
            result=direct.run_owned(root=self.root,policy=self.policy,operation='head',
                receipt_root=target,capture_quiescence=capture)
        return result,target,closed

    def verify(self,result,target,**changes):
        options={'root':self.root,'policy':self.policy,
            'stdout_raw':(target/'stdout.bin').read_bytes(),'stderr_raw':(target/'stderr.bin').read_bytes()}
        options.update(changes)
        return tree.verify_quiescence((target/'receipt.json').read_bytes(),result['receipt_pin'],
                                      result['quiescence'],**options)

    def test_capture_links_real_executor_return_position_after_all_fake_closes(self):
        result,target,closed=self.run_call()
        self.assertEqual(closed,[33,22,11]);self.assertTrue(self.verify(result,target))
        self.assertEqual(result['quiescence']['closed']['closed_handles'],{'thread':33,'process':22,'job':11})
        self.assertEqual(set(result['receipt']),tree._FIELDS)
        self.assertIs(result['receipt']['execution_authenticated'],False)

    def test_default_result_and_saved_receipt_have_no_new_witness_fields(self):
        result,target,closed=self.run_call(capture=False)
        self.assertEqual(set(result),{'receipt','receipt_pin','receipt_root','stdout'})
        self.assertEqual(set(tree.v.strict_json((target/'receipt.json').read_bytes())),tree._FIELDS)
        self.assertEqual(closed,[33,22,11])

    def test_reaped_failed_call_can_have_quiescence_without_success_credit(self):
        result,target,closed=self.run_call(code=17)
        self.assertEqual(result['receipt']['status'],'failed');self.assertTrue(self.verify(result,target))
        self.assertEqual(result['quiescence']['exit_code'],17)
        self.assertIs(result['quiescence']['formal_permission'],False);self.assertEqual(closed,[33,22,11])

    def test_executor_close_exception_keeps_unattempted_handles_and_no_receipt(self):
        failure=KeyboardInterrupt('invented close interruption')
        with self.assertRaises(owner.UnclosedHandles) as caught:self.run_call(close_failure=failure)
        self.assertEqual(caught.exception.handles,{'process':22,'job':11})
        self.assertIs(caught.exception.close_error,failure)
        self.assertFalse((self.root/'call-1'/'receipt.json').exists())

    def test_unreaped_spawn_keeps_exact_original_and_extra_handles(self):
        original=owner.UnreapedJob(11,22,33,{'phase':'spawn'},extra_handles={'inherited_0':55})
        with self.assertRaises(owner.UnreapedJob) as caught:self.run_call(spawn_failure=original)
        self.assertIs(caught.exception,original);self.assertEqual(original.extra_handles,{'inherited_0':55})
        self.assertFalse((self.root/'call-1'/'receipt.json').exists())

    def test_close_false_preserves_failed_handle_without_success_event(self):
        kernel=SimpleNamespace(CloseHandle=Mock(side_effect=[True,False,True]))
        with self.assertRaises(owner.UnclosedHandles) as caught:
            owner._close_owned(kernel,11,22,33,{})
        self.assertEqual(caught.exception.handles,{'process':22})
        self.assertEqual([c.args[0] for c in kernel.CloseHandle.call_args_list],[33,22,11])

    def test_close_exception_before_any_success_retains_every_original_handle(self):
        failure=OSError('invented first close observation failure')
        kernel=SimpleNamespace(CloseHandle=Mock(side_effect=failure))
        with self.assertRaises(owner.UnclosedHandles) as caught:owner._close_owned(kernel,11,22,33,{})
        self.assertEqual(caught.exception.handles,{'thread':33,'process':22,'job':11})
        self.assertIs(caught.exception.__cause__,failure);kernel.CloseHandle.assert_called_once_with(33)

    def test_diagnostic_io_failure_cannot_discard_close_owner_or_original_error(self):
        failure=OSError('invented native close failure');diagnostic=KeyboardInterrupt('invented diagnostic interruption')
        class Report(dict):
            def __setitem__(self,key,value):raise diagnostic
        report=Report();kernel=SimpleNamespace(CloseHandle=Mock(side_effect=failure))
        with self.assertRaises(owner.UnclosedHandles) as caught:owner._close_owned(kernel,11,22,33,report)
        self.assertIs(caught.exception.close_error,failure);self.assertIs(caught.exception.diagnostic_error,diagnostic)
        self.assertIs(caught.exception.report,report)
        self.assertEqual(caught.exception.handles,{'thread':33,'process':22,'job':11})

    def test_full_stdout_pin_must_pass_before_close_link(self):
        result,target,_=self.run_call()
        with self.assertRaises(ValueError):self.verify(result,target,stdout_raw=b'changed')

    def test_full_policy_boundary_must_pass_before_close_link(self):
        result,target,_=self.run_call()
        with self.assertRaises(ValueError):self.verify(result,target,policy={**self.policy,'revision':'b'*40})

    def test_witness_from_different_original_process_cannot_release_job(self):
        result,target,_=self.run_call();result['quiescence']['process_identity']['creation_time_100ns']=99
        with self.assertRaises(ValueError):self.verify(result,target)

    def test_witness_active_accounting_or_boolean_exit_cannot_release_job(self):
        result,target,_=self.run_call();original=copy.deepcopy(result['quiescence'])
        for change in ({'accounting':{**ACCOUNT,'active_processes':1}},{'exit_code':False},
                       {'accounting':{**ACCOUNT,'total_processes':True}}):
            with self.subTest(change=change):
                result['quiescence']={**original,**change}
                with self.assertRaises(ValueError):self.verify(result,target)

    def test_missing_duplicated_or_boolean_handle_witness_cannot_release_job(self):
        result,target,_=self.run_call();original=copy.deepcopy(result['quiescence'])
        for handles in ({'thread':33,'process':22},{'thread':33,'process':22,'job':22},
                        {'thread':True,'process':22,'job':11}):
            with self.subTest(handles=handles):
                result['quiescence']=copy.deepcopy(original)
                result['quiescence']['closed']['closed_handles']=handles
                with self.assertRaises(ValueError):self.verify(result,target)

    def test_receipt_pin_change_or_added_permission_is_rejected(self):
        result,target,_=self.run_call();original=copy.deepcopy(result['quiescence'])
        for change in ({'receipt_pin':{'bytes':1,'sha256':'b'*64}},
                       {'formal_permission':True},{'new_permission':True}):
            with self.subTest(change=change):
                result['quiescence']={**original,**change}
                with self.assertRaises(ValueError):self.verify(result,target)

    def test_direct_handle_policy_cannot_opt_into_job_quiescence(self):
        with patch.object(direct.subprocess,'Popen') as launch:
            with self.assertRaises(ValueError):
                direct.run_owned(root=self.root,policy={'revision':self.revision},operation='head',
                                 receipt_root=self.root/'direct',capture_quiescence=True)
            launch.assert_not_called();self.assertFalse((self.root/'direct').exists())

    def test_non_boolean_capture_option_rejects_before_policy_or_output(self):
        with patch.object(direct,'_policy') as policy:
            with self.assertRaises(ValueError):
                direct.run_owned(root=self.root,policy=self.policy,operation='head',
                                 receipt_root=self.root/'invalid',capture_quiescence=1)
            policy.assert_not_called();self.assertFalse((self.root/'invalid').exists())
