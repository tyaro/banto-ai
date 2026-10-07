"""Private Git Job protocol, cleanup failures, and policy selection."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_preformal_owned_git_job as tree

owner, direct = tree.owner, tree.direct
MEMORY = {'information_class':9, 'limit_flags':0x2000,
          'peak_process_memory_used_bytes':1024, 'peak_job_memory_used_bytes':2048}
ACCOUNT = {'total_processes':2, 'active_processes':0, 'limit_terminated_processes':0}


class GitJobTests(unittest.TestCase):
    def _execute(self, *, code=0, child_active=False, data=b'', failed_identity=False,
                 empty=True, close_fail=False, spawn_error=None, account_fail=False, stop_probe=None):
        class Kernel:
            stopped = False
            closed = []
            resumed = False
            def ResumeThread(self, thread):
                self.resumed = True
                return 1
            def TerminateJobObject(self, job, value):
                self.stopped = True
                return True
            def CloseHandle(self, handle):
                self.closed.append(handle)
                return not (close_fail and handle == 22)
        kernel = Kernel()
        def spawn(k, argv, root, stdin, stdout, stderr, *, environment):
            self.assertEqual(environment, {'PATH':'explicit'})
            stdout.write(data);stdout.flush()
            if spawn_error is not None:
                raise spawn_error
            return 11,22,33,44
        def account(*args):
            if account_fail and not kernel.stopped:
                raise OSError('accounting')
            return {**ACCOUNT,'active_processes':int(not kernel.stopped and (child_active or code is None))}
        def root_exit(*args):
            return 0xE007 if kernel.stopped and code is None else code
        def wait(*args):
            return {**account(),'active_processes':0 if empty else 1},root_exit()
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(owner,'_kernel',return_value=kernel), \
             patch.object(owner,'_spawn_cli',side_effect=spawn), \
             patch.object(owner,'_accounting',side_effect=account), \
             patch.object(owner,'_root_exit',side_effect=root_exit), \
             patch.object(owner,'_wait_empty',side_effect=wait), \
             patch.object(owner,'_job_memory',return_value=MEMORY), \
             patch.object(direct,'_identity',side_effect=OSError('identity') if failed_identity else None,
                          return_value={'pid':44,'native_start_identity_authenticated':True}):
            try:
                result = tree._execute(['fixture'],Path(temp),{'PATH':'explicit'},Path(temp),'head',0.001,
                    **({'stop_probe': stop_probe} if stop_probe is not None else {}))
            except BaseException as error:
                error.test_kernel = kernel
                raise
        return result,kernel

    def test_success_closes_all_handles_only_after_empty_job(self):
        result,kernel = self._execute()
        self.assertEqual(result[1:4],(0,None,None))
        self.assertFalse(kernel.stopped)
        self.assertEqual(kernel.closed,[33,22,11])
        self.assertTrue(result[4]['all_assigned_processes_exit_confirmed'])
        self.assertFalse(result[4]['individual_descendant_exit_codes_authenticated'])

    def test_root_exit_does_not_complete_with_a_live_child(self):
        result,kernel = self._execute(child_active=True)
        self.assertEqual(result[1:3],(0,'time_limit'))
        self.assertTrue(kernel.stopped)
        self.assertEqual(result[4]['accounting']['active_processes'],0)

    def test_nonzero_root_stops_remaining_job_members(self):
        result,kernel = self._execute(code=17,child_active=True)
        self.assertEqual(result[1:3],(17,'exit_nonzero'))
        self.assertTrue(kernel.stopped)

    def test_output_limit_stops_and_reaps_the_job(self):
        result,kernel = self._execute(code=None,data=b'x'*129)
        self.assertEqual(result[2],'output_limit')
        self.assertTrue(kernel.stopped)

    def test_identity_failure_stops_before_resume(self):
        result,kernel = self._execute(code=None,failed_identity=True)
        self.assertFalse(kernel.resumed)
        self.assertTrue(kernel.stopped)
        self.assertEqual(result[2:4],('spawn_or_observation_error','OSError'))
        self.assertFalse(result[4]['root_resumed'])

    def test_accounting_failure_still_stops_and_reaps_members(self):
        result,kernel = self._execute(code=None,account_fail=True)
        self.assertEqual(result[2:4],('spawn_or_observation_error','OSError'))
        self.assertTrue(kernel.stopped)
        self.assertEqual(kernel.closed,[33,22,11])

    def test_shared_stop_after_resume_terminates_running_tree(self):
        responses = iter([None, 'outer_memory'])
        result,kernel = self._execute(code=None,child_active=True,stop_probe=lambda:next(responses))
        self.assertEqual(result[2], 'shared_budget_stop')
        self.assertTrue(kernel.resumed)
        self.assertTrue(kernel.stopped)

    def test_shared_stop_before_spawn_creates_no_receipt_or_process(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / 'not-started'
            policy = {'revision': 'a' * 40, 'process_ownership': direct.JOB_OWNERSHIP}
            with patch.object(direct, '_policy', return_value=(root, root/'git.exe', {}, {})), \
                 patch.object(tree.os, 'name', 'nt'), patch.object(owner, '_spawn_cli') as spawn, \
                 self.assertRaises(owner.resources.ResourceStop):
                tree.run_owned(root=root, policy=policy, operation='head', receipt_root=target,
                               stop_probe=lambda:'outer_time')
            spawn.assert_not_called()
            self.assertFalse(target.exists())

    def test_direct_handle_policy_cannot_ignore_a_shared_stop_probe(self):
        with patch.object(direct, '_policy') as policy, \
             self.assertRaisesRegex(ValueError, 'private Job ownership'):
            direct.run_owned(root='unused', policy={}, operation='head', receipt_root='unused',
                             stop_probe=lambda:None)
        policy.assert_not_called()

    def test_unconfirmed_empty_job_retains_native_handles(self):
        with self.assertRaises(owner.UnreapedJob) as caught:
            self._execute(empty=False)
        error = caught.exception
        self.assertEqual((error.job,error.process,error.thread),(11,22,33))
        self.assertEqual(error.test_kernel.closed,[])

    def test_close_failure_retains_exact_handle_and_closes_others(self):
        with self.assertRaises(owner.UnclosedHandles) as caught:
            self._execute(close_fail=True)
        self.assertEqual(caught.exception.handles,{'process':22})
        self.assertEqual(caught.exception.test_kernel.closed,[33,22,11])

    def test_partial_spawn_error_keeps_original_owner(self):
        original = owner.UnreapedJob(11,22,33,{'status':'failed'},extra_handles={'stdio':55})
        with self.assertRaises(owner.UnreapedJob) as caught:
            self._execute(spawn_error=original)
        self.assertIs(caught.exception,original)
        self.assertEqual(original.extra_handles,{'stdio':55})
        self.assertEqual(original.test_kernel.closed,[])

    def test_shared_stop_terminates_and_confirms_the_assigned_tree(self):
        result,kernel = self._execute(code=None,child_active=True,stop_probe=lambda:'outer_time')
        self.assertEqual(result[2], 'shared_budget_stop')
        self.assertTrue(result[4]['all_assigned_processes_exit_confirmed'])
        self.assertTrue(kernel.stopped)
        self.assertEqual(kernel.closed,[33,22,11])
        self.assertFalse(kernel.resumed)

    def test_shared_stop_with_unreaped_tree_retains_exact_handles(self):
        with self.assertRaises(owner.UnreapedJob) as caught:
            self._execute(code=None,empty=False,stop_probe=lambda:'outer_time')
        self.assertEqual((caught.exception.job,caught.exception.process,caught.exception.thread),(11,22,33))
        self.assertEqual(caught.exception.test_kernel.closed,[])

    def test_invalid_shared_probe_stops_tree_as_observation_failure(self):
        result,kernel = self._execute(code=None,stop_probe=lambda:True)
        self.assertEqual(result[2:4],('spawn_or_observation_error','V03ValidationError'))
        self.assertTrue(kernel.stopped)

    def test_unicode_environment_is_explicit_and_rejects_ambiguous_keys(self):
        block = owner._environment_block({'TEMP':'試験','PATH':'fixed'})
        self.assertEqual(''.join(block),'PATH=fixed\x00TEMP=試験\x00\x00')
        for env in ({},{'PATH':'x','Path':'y'},{'A=B':'x'},{'PATH':'x\x00y'}):
            with self.subTest(env=env), self.assertRaises(ValueError):
                owner._environment_block(env)

    def test_policy_selects_job_executor_without_silent_fallback(self):
        value = object()
        with patch.object(tree,'run_owned',return_value=value) as run:
            self.assertIs(direct.run_owned(root='unused',policy={'process_ownership':direct.JOB_OWNERSHIP},
                operation='head',receipt_root='unused'),value)
            self.assertEqual(run.call_args.kwargs['timeout_seconds'],10)
        with self.assertRaisesRegex(ValueError,'process ownership policy'):
            direct._policy('unused',{'process_ownership':'unknown'},check_current=False)

    def test_saved_job_scope_and_accounting_reject_tampering(self):
        receipt = dict.fromkeys(tree._FIELDS)
        receipt.update(status='verified',direct_process_handle_exit_confirmed=True,
            process_identity={'native_start_identity_authenticated':True},job={
            'format':tree.JOB,'assignment_confirmed':True,'root_resumed':True,
            'accounting':ACCOUNT,'memory':MEMORY,'all_assigned_processes_exit_confirmed':True,
            'individual_descendant_exit_codes_authenticated':False,'loaded_code_authenticated':False,
            'whole_tree_resource_budget_measured':False,'observation_errors':[]})
        with patch.object(owner,'_kernel',side_effect=AssertionError('native API')):
            tree.verify_job(receipt)
            for key,value in (('root_resumed',False),('assignment_confirmed',False),
                              ('loaded_code_authenticated',True),
                              ('individual_descendant_exit_codes_authenticated',True),
                              ('all_assigned_processes_exit_confirmed',False),
                              ('accounting',{**ACCOUNT,'active_processes':1}),
                              ('accounting',{**ACCOUNT,'total_processes':True}),
                              ('memory',{**MEMORY,'limit_flags':0x2800})):
                changed = copy.deepcopy(receipt);changed['job'][key] = value
                with self.subTest(key=key,value=value), self.assertRaises(ValueError):
                    tree.verify_job(changed)
            with self.assertRaises(ValueError):tree.verify_job({**receipt,'unknown':True})


if __name__ == '__main__':
    unittest.main()
