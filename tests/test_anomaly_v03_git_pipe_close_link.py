"""Retained IO/core close links with fake native API and nonempty real FileIO."""
import copy
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_preformal_owned_git_job as git
from banto_ai import anomaly_v03_preformal_job_tree_owner as owner
from banto_ai import anomaly_v03_preformal_worker_git_proof as proof
from tests import test_anomaly_v03_git_pipe_close as prior
from tests import test_anomaly_v03_git_quiescence as receipts


class GitPipeCloseLinkTests(unittest.TestCase):
    def setUp(self):
        prior.GitPipeCloseTests.setUp(self)
        self.raw=b'a'*40+b'\n'
        # Simulate draining data retained by a pipe after cached Job termination.
        self.reader.eof.clear()
        def available(handle,buffer,amount,count,total,left):
            total._obj.value=len(self.raw);return True
        def read(handle,buffer,amount,count,overlapped):
            owner.ctypes.memmove(buffer,self.raw,len(self.raw))
            count._obj.value=len(self.raw);return True
        self.kernel.PeekNamedPipe=Mock(side_effect=available)
        self.kernel.ReadFile=Mock(side_effect=read)
        self.assertEqual(self.reader.read_once('stdout'),'data')
        self.kernel.PeekNamedPipe=Mock(return_value=False)
        with patch.object(owner.ctypes,'get_last_error',return_value=109,create=True):
            self.reader.read_once('stdout');self.reader.read_once('stderr')
        self.adapter=git.GitPipeClose(self.reader,keeper=self.keeper)
        self.before=list(self.closed);self.checkpoint.reset_mock()

    def recover(self):
        self.keeper.bind_io_close(self.adapter)
        return self.keeper.reconcile_once()

    def test_opt_in_links_nonempty_raw_named_io_and_core_closes_without_native_reap_replay(self):
        event=self.recover();self.assertEqual(event['format'],git.PIPE_RECOVERY)
        self.assertTrue(git.verify_pipe_recovery(event,stdout_raw=self.raw,stderr_raw=b''))
        self.assertEqual(self.closed,self.before+[74,75,33,22,11])
        self.assertEqual(event['io_closed']['sink_closed']['stdout']['raw_pin'],git.observed._pin(self.raw))
        self.assertFalse(event['lease_completed']);self.assertFalse(event['parent_ack_authorized'])
        self.assertFalse(event['execution_authenticated']);self.wait.assert_called_once()
        event['io_closed'].clear();again=self.keeper.reconcile_once()
        self.assertEqual(again['io_closed']['format'],git.PIPE_CLOSE_LINK)
        self.assertEqual(self.closed,self.before+[74,75,33,22,11])

    def test_completed_close_without_explicit_binding_stays_guarded(self):
        self.adapter.close_once();self.output.released=True
        self.assertIsNone(self.keeper.reconcile_once());self.assertIsNone(self.keeper.completion)
        self.assertEqual(self.closed,self.before+[74,75])

    def test_release_metadata_cannot_substitute_original_close_events(self):
        self.output.released=True;self.adapter.result={'io_released':True}
        self.keeper.bind_io_close(self.adapter)
        self.assertIsNone(self.keeper.reconcile_once());self.assertIsNone(self.keeper.completion)
        self.assertEqual(self.closed,self.before)

    def test_foreign_adapter_is_retained_before_rejection(self):
        foreign=SimpleNamespace(result={'io_released':True})
        with self.assertRaises(owner.UnreapedJob):self.keeper.bind_io_close(foreign)
        self.assertIs(self.keeper.io_close_adapter,foreign)
        self.assertIs(self.held.native.child_keeper,self.keeper);self.assertEqual(self.closed,self.before)

    def test_raw_tamper_between_io_close_and_core_close_holds_core_no_close_retry(self):
        self.adapter.close_once();self.files['stdout'].write_bytes(b'tampered')
        self.keeper.bind_io_close(self.adapter)
        self.assertIsNone(self.keeper.reconcile_once());self.assertIsNone(self.keeper.reconcile_once())
        self.assertEqual(self.closed,self.before+[74,75]);self.assertIsNone(self.keeper.completion)
        self.assertIsNotNone(self.adapter.error);self.wait.assert_called_once()

    def test_unknown_core_close_holds_secondary_owner_and_completed_io_no_retry(self):
        failure=KeyboardInterrupt('core close')
        def close(handle):
            self.closed.append(handle)
            if handle==22:raise failure
            return True
        self.kernel.CloseHandle=Mock(side_effect=close)
        self.assertIsNone(self.recover());self.assertIsNone(self.keeper.reconcile_once())
        self.assertIs(self.keeper.close_owner.close_error,failure)
        self.assertEqual(self.keeper.close_owner.handles,{'process':22,'job':11})
        self.assertEqual(self.closed,self.before+[74,75,33,22]);self.assertIsNotNone(self.keeper.io_closed)

    def test_known_false_core_retry_reuses_cached_io_and_original_native_reap(self):
        self.close_false={22};self.assertIsNone(self.recover())
        self.close_false=set();event=self.keeper.reconcile_once()
        self.assertEqual(event['format'],git.PIPE_RECOVERY)
        self.assertEqual(self.closed,self.before+[74,75,33,22,11,22]);self.wait.assert_called_once()
        self.assertTrue(git.verify_pipe_recovery(event,stdout_raw=self.raw,stderr_raw=b''))

    def test_new_recovery_verifier_rejects_changed_raw(self):
        event=self.recover()
        with self.assertRaises(ValueError):git.verify_pipe_recovery(event,stdout_raw=b'changed',stderr_raw=b'')

    def test_new_recovery_verifier_rejects_extra_fields_alias_return_and_identity_tamper(self):
        event=self.recover()
        variants=[]
        altered=copy.deepcopy(event);altered['io_closed']['released']=True;variants.append(altered)
        altered=copy.deepcopy(event);altered['io_closed']['read_closed']['stdout']['handle']=11;variants.append(altered)
        altered=copy.deepcopy(event);altered['io_closed']['read_closed']['stdout']['return']=0;variants.append(altered)
        altered=copy.deepcopy(event);altered['io_closed']['process_identity']['creation_time_100ns']+=1;variants.append(altered)
        for altered in variants:
            with self.assertRaises(ValueError):git.verify_pipe_recovery(altered,stdout_raw=self.raw,stderr_raw=b'')

    def test_second_raw_read_error_retains_first_return_before_diagnostics(self):
        self.adapter.close_once()
        error=OSError('second reader')
        self.reader.readback['stderr']=Mock(side_effect=[b'',error])
        self.keeper.bind_io_close(self.adapter)
        self.assertIsNone(self.keeper.reconcile_once())
        self.assertEqual(self.adapter.pending['raw']['stdout'],self.raw)
        self.assertIs(self.adapter.error,error);self.assertEqual(self.closed,self.before+[74,75])

    def test_pipe_receipt_verifier_requires_full_receipt_policy_raw_and_exact_io_link(self):
        event=self.recover()
        receipts.GitQuiescenceTests.setUp(self)
        self.identity['creation_time_100ns']=111
        self.identity['start_token']=git.v.canonical_sha256({key:self.identity[key] for key in ('pid','creation_time_100ns')})
        result,target,_=receipts.GitQuiescenceTests.run_call(self,code=17)
        witness=copy.deepcopy(result['quiescence']);witness['format']=git.PIPE_QUIESCENCE
        witness['io_closed']=event['io_closed']
        raw=(target/'receipt.json').read_bytes()
        options={'root':self.root,'policy':self.policy,'stdout_raw':self.raw,'stderr_raw':b''}
        self.assertTrue(git.verify_quiescence(raw,result['receipt_pin'],witness,**options))
        changed=copy.deepcopy(witness);changed['io_closed']['sink_closed']['stdout']['raw_pin']=git.observed._pin(b'wrong')
        with self.assertRaises(ValueError):git.verify_quiescence(raw,result['receipt_pin'],changed,**options)
        with self.assertRaises(ValueError):git.verify_quiescence(raw+b' ',result['receipt_pin'],witness,**options)

    def test_compact_recovery_record_reads_all_raw_and_preserves_failed_status(self):
        event=self.recover()
        packet={'kind':'recovery','raw':{'receipt.json':b'{partial','stdout.bin':self.raw,'stderr.bin':b''},'event':event}
        call={'lease':0,'phase':'pre','operation':'head','source_path':None,'expected_output_pin':None,
              'raw_inventory':{'receipt.json':16384,'stdout.bin':128,'stderr.bin':65536}}
        verifier=proof.ProofVerifier.__new__(proof.ProofVerifier)
        verifier.inventory={'calls':[call],'repository':str(self.tmp.name)}
        verifier.read_evidence=lambda lease:packet;verifier._live=lambda:None
        verifier.endpoint=SimpleNamespace(_policy=lambda:{})
        with patch.object(git.direct,'_policy',return_value=None):
            row,identity,status,retained=verifier.record(0)
        self.assertEqual(row['kind'],'recovery');self.assertEqual(status,'failed')
        self.assertEqual(identity,event['process_identity']);self.assertEqual(retained,event)
        packet['raw']['stdout.bin']=b'changed'
        with patch.object(git.direct,'_policy',return_value=None),self.assertRaises(ValueError):verifier.record(0)

    def test_late_pending_output_error_cannot_release_core_from_cached_close_events(self):
        self.adapter.close_once()
        failure=OSError('late retained IO error')
        self.output.error=failure
        self.output.pending={'raw':b'original pending block'}
        self.keeper.bind_io_close(self.adapter)
        self.assertIsNone(self.keeper.reconcile_once());self.assertIsNone(self.keeper.completion)
        self.assertIs(self.output.error,failure)
        self.assertEqual(self.output.pending['raw'],b'original pending block')
        self.assertEqual(self.closed,self.before+[74,75])
