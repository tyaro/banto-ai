"""New declared-roster/retention risks, with memory preparations and fake owners."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, PropertyMock, patch
from banto_ai import anomaly_v03_preformal_generated_chain_budget as budget
from banto_ai import anomaly_v03_preformal_reader_git_worker as reader
from banto_ai import anomaly_v03_preformal_worker_git_archive as archive


class Escape(BaseException):
    """Test-only exit from the original Python retention loop."""


class RequestWriterPreparationTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name).resolve();info=self.root.lstat();self.clock=Mock()
        self.parent=reader.ReaderGitParent.__new__(reader.ReaderGitParent)
        self.parent.original_bootstrap_inputs=(None,)*10;self.parent.worker=None;self.parent.error=None
        self.parent.inventory_publication=self.parent.inventory_publication_error=self.parent.inventory_pending_owner=None
        self.parent.inventory_checkpoint=self.clock
        context={'request_pin':{'bytes':17,'sha256':'a'*64},'inventory_pin':{'bytes':19,'sha256':'b'*64},
            'revision':'c'*40,'root':str(self.root),'root_identity':[info.st_dev,info.st_ino]}
        group=archive.PartitionedArchivePreparation(owner=self.parent,checkpoint=self.clock,allocation={
            'format':archive.PartitionedArchivePreparation.FORMAT,'context':context,
            'call_growth_maxima':[12000,12000],'archive_max_bytes':24000,'formal_permission':False})
        group.prepare();self.context_raw=archive.io.json_bytes(context)
        identity=archive.io.json_bytes({'format':budget.PartitionedPublicationPreparation.FORMAT+'-parent-identity',
            'context_pin':archive.observed._pin(self.context_raw),
            'identity':{'pid':111,'creation_time_100ns':222,'start_token':'e'*64},'formal_permission':False})
        self.publication=self.parent.prepare_partitioned_publication(archive_preparation=group,allocation={
            'format':budget.PartitionedPublicationPreparation.FORMAT,
            'control_limits':dict.fromkeys(archive.ArchiveAppendAdmission.CONTROL_NAMES,512),
            'call_raw_maxima':[{'stdout.bin':4096,'stderr.bin':512,'receipt.json':512} for _ in range(2)],
            'parent_raw_maxima':{'stdout.bin':1024,'stderr.bin':1024,'receipt.json':1024},
            'diagnostic_maxima':{'diagnostic.json':1024,'diagnostic.log':1024},
            'native_buffer_payload_bytes':1024,'resident_extra_bytes':4096},
            entry_raw=b'{"engineering_entry_stub":true}',context_raw=self.context_raw,parent_identity_raw=identity)
        self.declaration={'format':budget.RequestWriterPreparation.FORMAT,
            'context_pin':archive.observed._pin(self.context_raw),
            'roles':list(budget.RequestWriterPreparation.ROLES),'formal_permission':False}
        self.participants=tuple((role,object()) for role in budget.RequestWriterPreparation.ROLES)
        self.clock.reset_mock()

    def prepare(self):
        return self.parent.prepare_request_writers(publication=self.publication,
            declaration=self.declaration,participants=self.participants)

    def claim(self,held,index=0):
        role,participant=self.participants[index]
        return held.claim(role,participant,self.context_raw)

    def test_all_declared_roles_share_context_without_issuing_native_permission(self):
        held=self.prepare()
        for index in range(5):result=self.claim(held,index)
        self.assertEqual(result['claimed_roles'],self.declaration['roles'])
        self.assertTrue(result['declared_python_owners_linked']);self.assertTrue(held.unresolved())
        self.assertFalse(any(result[k] for k in ('all_writers_registered','exclusive_root','atomic_reservation',
            'capacity_pass','native_authorized','execution_authenticated','parent_ack_authorized','formal_permission')))
        self.assertIs(held.original_inputs[4],self.participants);self.assertEqual(list(self.root.iterdir()),[])

    def test_closed_declaration_rejects_extra_field_before_clock(self):
        self.declaration['native_authorized']=True
        with self.assertRaises(ValueError):self.prepare()
        self.clock.assert_not_called();self.assertIs(self.parent._request_writers_owner.original_inputs[3],self.declaration)

    def test_missing_role_refuses_before_clock(self):
        self.declaration['roles'].pop()
        with self.assertRaises(ValueError):self.prepare()
        self.clock.assert_not_called()

    def test_foreign_context_pin_refuses_before_clock(self):
        self.declaration['context_pin']['sha256']='f'*64
        with self.assertRaises(ValueError):self.prepare()
        self.clock.assert_not_called()

    def test_participant_slot_missing_refuses_before_clock(self):
        self.participants=self.participants[:-1]
        with self.assertRaises(ValueError):self.prepare()
        self.clock.assert_not_called()

    def test_foreign_parent_cannot_reuse_publication(self):
        foreign=reader.ReaderGitParent.__new__(reader.ReaderGitParent)
        foreign.error=None;foreign.inventory_checkpoint=self.clock
        with self.assertRaises(ValueError):foreign.prepare_request_writers(publication=self.publication,
            declaration=self.declaration,participants=self.participants)
        self.clock.assert_not_called();self.assertIs(foreign._request_writers_owner.original_inputs[0],foreign)

    def test_original_holder_exists_before_checkpoint_getter_failure(self):
        error=KeyboardInterrupt('engineering getter interruption')
        with patch.object(reader.ReaderGitParent,'inventory_checkpoint',new_callable=PropertyMock,create=True) as getter:
            getter.side_effect=error
            with self.assertRaises(KeyboardInterrupt) as caught:self.prepare()
        held=self.parent._request_writers_owner
        self.assertIs(caught.exception,error);self.assertIs(held._caller_inputs[3],self.declaration)
        self.assertIs(error.request_writers,held);self.assertIs(error.reader_git_parent,self.parent)

    def test_constructor_unknown_return_and_first_error_remain_on_original_holder(self):
        returned=object();self.clock.return_value=returned
        self.clock.side_effect=lambda: (self.declaration.update(formal_permission=True) or returned)
        with self.assertRaises(ValueError) as caught:self.prepare()
        held=self.parent._request_writers_owner
        self.assertIs(held._pending['clock_return'],returned);self.assertIs(held.error,caught.exception)
        self.declaration['formal_permission']=False
        with self.assertRaises(ValueError) as again:held.view()
        self.assertIs(again.exception,caught.exception)

    def test_second_preparation_retains_rejected_holder_and_original_first_error(self):
        held=self.prepare();self.clock.reset_mock()
        with self.assertRaises(ValueError) as caught:self.prepare()
        self.assertIs(self.parent._request_writers_owner,held)
        self.assertIs(held.rejected.original_inputs[4],self.participants);self.clock.assert_not_called()
        self.assertIs(caught.exception,held.error)

    def test_duplicate_role_refuses_without_second_callback(self):
        held=self.prepare();self.claim(held);self.clock.reset_mock()
        with self.assertRaises(ValueError):self.claim(held)
        self.clock.assert_not_called();self.assertIs(held._pending['incoming'][1],self.participants[0][1])

    def test_foreign_participant_retained_before_refusal(self):
        held=self.prepare();foreign=object();self.clock.reset_mock()
        with self.assertRaises(ValueError):held.claim(self.participants[0][0],foreign,self.context_raw)
        self.assertIs(held._pending['incoming'][1],foreign);self.assertIs(held._refused[1],foreign)
        self.clock.assert_not_called()

    def test_foreign_request_root_bytes_refuse_before_callback(self):
        held=self.prepare();context=archive.v.strict_json(self.context_raw);context['root_identity'][1]+=1
        raw=archive.io.json_bytes(context);self.clock.reset_mock()
        with self.assertRaises(ValueError):held.claim(*self.participants[0],raw)
        self.assertIs(held._pending['incoming'][2],raw);self.clock.assert_not_called()

    def test_unlisted_writer_role_refuses_without_callback(self):
        held=self.prepare();self.clock.reset_mock()
        with self.assertRaises(ValueError):held.claim('undeclared_writer',object(),self.context_raw)
        self.clock.assert_not_called()

    def test_claim_interrupt_keeps_original_pending_and_refuses_replay(self):
        held=self.prepare();error=KeyboardInterrupt('engineering claim interruption');self.clock.side_effect=error
        with self.assertRaises(KeyboardInterrupt) as caught:self.claim(held)
        self.assertIs(caught.exception,error);self.assertIs(held._pending['incoming'][1],self.participants[0][1])
        self.clock.reset_mock();self.clock.side_effect=None
        with self.assertRaises(KeyboardInterrupt) as again:self.claim(held,1)
        self.assertIs(again.exception,error);self.clock.assert_not_called()

    def test_reentrant_claim_latches_first_error_without_second_clock(self):
        held=self.prepare();self.clock.reset_mock();self.clock.side_effect=lambda:self.claim(held,1)
        with self.assertRaises(ValueError) as caught:self.claim(held)
        self.assertEqual(self.clock.call_count,1);self.assertIs(held.error,caught.exception)
        self.assertIs(held._pending['incoming'][1],self.participants[0][1])
        self.assertIs(held._refused[1],self.participants[1][1])

    def test_both_display_claim_ledgers_erased_cannot_restore_readiness(self):
        held=self.prepare();self.claim(held);held._claims=held._claims_anchor=()
        with self.assertRaises(ValueError) as caught:held.view()
        self.assertIs(held._RequestWriterPreparation__claims[0][1],self.participants[0][1])
        held._claims=held._claims_anchor=held._RequestWriterPreparation__claims
        with self.assertRaises(ValueError) as again:held.view()
        self.assertIs(again.exception,caught.exception)

    def test_marker_removed_keeps_original_parent_retention(self):
        held=self.prepare();self.parent.request_writers=None
        with self.assertRaises(ValueError) as caught:held.view()
        with patch.object(reader.ParentPublicationRetention,'_pause',side_effect=Escape):
            with self.assertRaises(Escape):reader.retain_parent_publications(caught.exception,self.parent)
        keeper=self.parent.original_publication_retention
        self.assertIs(keeper.parent,self.parent);self.assertIn(held,keeper.owners)
        self.assertIs(keeper.original_error,caught.exception)

    def test_claim_result_replacement_refuses_cached_view(self):
        held=self.prepare();result=self.claim(held);result['claimed_roles']=[]
        with self.assertRaises(ValueError):held.view()
        self.assertIs(held._returns[0],result)

    def test_cached_view_and_execute_repeat_no_clock_or_filesystem_work(self):
        held=self.prepare();self.claim(held);self.clock.reset_mock()
        with patch.object(budget.os,'scandir',side_effect=AssertionError('snapshot repeated')):
            self.assertEqual(held.view(),held.view())
            with self.assertRaisesRegex(ValueError,'not prepared'):held.execute(object())
        self.clock.assert_not_called();self.assertEqual(list(self.root.iterdir()),[])

    def test_inventory_gate_refuses_before_existing_native_or_control_owner_lookup(self):
        held=self.prepare();self.clock.reset_mock()
        with self.assertRaisesRegex(ValueError,'request writer admission unresolved'):self.parent._inventory_ready()
        self.assertIs(self.parent.error.request_writers,held);self.clock.assert_not_called()

    def test_callback_pending_erasure_keeps_original_unknown_return(self):
        held=self.prepare();returned=object()
        def erase():
            held.pending=None
            return returned
        self.clock.side_effect=erase
        with self.assertRaises(ValueError):self.claim(held)
        self.assertIs(held._pending['clock_return'],returned)
        self.assertIs(held._pending['incoming'][1],self.participants[0][1])
        held.pending=held._pending
        with self.assertRaises(ValueError):held.view()

    def test_unknown_local_lock_release_keeps_first_error_and_original_lock(self):
        release_error=RuntimeError('engineering local lock release unknown')
        original_error=KeyboardInterrupt('engineering original callback interruption')
        class LocalLock:
            def acquire(self,blocking):return True
            def release(self):raise release_error
        lock=LocalLock()
        with patch.object(budget.threading,'Lock',return_value=lock):held=self.prepare()
        self.clock.side_effect=original_error
        with self.assertRaises(KeyboardInterrupt) as caught:self.claim(held)
        self.assertIs(caught.exception,original_error);self.assertIs(held._anchor[5],lock)
        self.assertIs(held._release_error,release_error);self.assertIs(held._pending['lock_release_error'],release_error)

    def test_constructor_pending_erasure_keeps_original_return_before_refusal(self):
        returned=object()
        def erase():
            self.parent._request_writers_owner.pending=None
            return returned
        self.clock.side_effect=erase
        with self.assertRaises(ValueError):self.prepare()
        held=self.parent._ReaderGitParent__request_writers_owner
        self.assertIs(held._pending['clock_return'],returned)
        self.assertIs(held._pending['inputs'][3],self.declaration)

    def test_erased_owner_aliases_cannot_replace_original_first_error_or_keeper(self):
        held=self.prepare();error=KeyboardInterrupt('engineering original writer failure')
        self.clock.side_effect=error
        with self.assertRaises(KeyboardInterrupt):self.claim(held)
        self.clock.side_effect=None;self.clock.reset_mock()
        self.parent._request_writers_owner=self.parent.original_request_writers=self.parent.request_writers=None
        with self.assertRaises(KeyboardInterrupt) as caught:self.prepare()
        self.assertIs(caught.exception,error);self.assertIs(self.parent._ReaderGitParent__request_writers_owner,held)
        self.assertIs(held.rejected._caller_inputs[4],self.participants);self.clock.assert_not_called()
        with patch.object(reader.ParentPublicationRetention,'_pause',side_effect=Escape):
            with self.assertRaises(Escape):reader.retain_parent_publications(error,self.parent)
        self.assertIn(held,self.parent.original_publication_retention.owners)
        self.assertIs(self.parent.original_publication_retention.original_error,error)


if __name__=='__main__':unittest.main()
