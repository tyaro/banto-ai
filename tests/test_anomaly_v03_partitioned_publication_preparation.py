"""New parent failure and payload accounting risks; no native execution."""
import copy
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, PropertyMock, patch
from banto_ai import anomaly_v03_preformal_worker_git_archive as archive
from banto_ai import anomaly_v03_preformal_reader_git_worker as reader
from banto_ai import anomaly_v03_preformal_generated_chain_budget as budget


class Escape(BaseException):
    """Test only: leave the original Python retention loop without claiming recovery."""


class PartitionedPublicationPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();info=self.root.lstat();self.clock=Mock()
        self.parent=reader.ReaderGitParent.__new__(reader.ReaderGitParent)
        self.parent.original_bootstrap_inputs=(None,)*10;self.parent.worker=None;self.parent.error=None
        self.parent.inventory_publication=None;self.parent.inventory_publication_error=None
        self.parent.inventory_pending_owner=None;self.parent.inventory_checkpoint=self.clock
        self.context={'request_pin':{'bytes':17,'sha256':'a'*64},'inventory_pin':{'bytes':19,'sha256':'b'*64},
            'revision':'c'*40,'root':str(self.root),'root_identity':[info.st_dev,info.st_ino]}
        self.group=archive.PartitionedArchivePreparation(owner=self.parent,checkpoint=self.clock,allocation={
            'format':archive.PartitionedArchivePreparation.FORMAT,'context':self.context,
            'call_growth_maxima':[12000,12000],'archive_max_bytes':24000,'formal_permission':False})
        self.group.prepare();self.clock.reset_mock()
        self.context_raw=archive.io.json_bytes(self.context);self.entry_raw=archive.io.json_bytes({'engineering_entry_stub':True})
        self.identity_raw=archive.io.json_bytes({'format':budget.PartitionedPublicationPreparation.FORMAT+'-parent-identity',
            'context_pin':archive.observed._pin(self.context_raw),
            'identity':{'pid':111,'creation_time_100ns':222,'start_token':'e'*64},'formal_permission':False})
        self.allocation={'format':budget.PartitionedPublicationPreparation.FORMAT,
            'control_limits':dict.fromkeys(archive.ArchiveAppendAdmission.CONTROL_NAMES,512),
            'call_raw_maxima':[{'stdout.bin':4096,'stderr.bin':512,'receipt.json':512} for _ in range(2)],
            'parent_raw_maxima':{'stdout.bin':1024,'stderr.bin':1024,'receipt.json':1024},
            'diagnostic_maxima':{'diagnostic.json':1024,'diagnostic.log':1024},
            'native_buffer_payload_bytes':1024,'resident_extra_bytes':4096}

    def prepare(self):
        return self.parent.prepare_partitioned_publication(archive_preparation=self.group,allocation=self.allocation,
            entry_raw=self.entry_raw,context_raw=self.context_raw,parent_identity_raw=self.identity_raw)

    def packet(self,lease=0,partial=False):
        raw={'stdout.bin':random.Random(963+lease).randbytes(2000),'stderr.bin':b'engineering stderr',
            'receipt.json':None,'partial-archive.bin':b'original partial' if partial else None}
        prep=archive.PacketPartitionPreparation(owner=self.parent,checkpoint=self.clock,context={**copy.deepcopy(self.context),'lease':lease},
            packet={'kind':'recovery' if partial else 'receipt','event':{'engineering_stub':True},'raw':raw},
            raw_limits={'stdout.bin':4096,'stderr.bin':512,'receipt.json':512,'partial-archive.bin':512})
        prep.prepare();self.group.register(prep);return prep

    def test_full_future_raw_parent_diagnostics_and_actual_bytes_remain_independent(self):
        held=self.prepare();view=held.view()
        actual=sum(map(len,(self.entry_raw,self.context_raw,self.identity_raw)))
        self.assertEqual(view['snapshot'],{'directory_bytes':0,'directory_entries':0,'directory_depth':0})
        self.assertEqual(view['future_bytes'],14*512+2*5120+3072+2048+actual+24000)
        self.assertEqual(view['future_entries'],29);self.assertEqual(view['remaining_entries'],1)
        self.assertEqual(view['entry_context_identity_bytes'],actual);self.assertEqual(view['archive_growth_maxima_bytes'],24000)
        self.assertGreater(view['python_payload_graph_bytes'],0);self.assertGreater(view['python_payload_graph_objects'],0)
        self.assertEqual(view['memory_projection_bytes'],view['future_bytes']+1024+4096+view['python_payload_graph_bytes'])
        self.assertFalse(any(view[k] for k in ('native_authorized','atomic_reservation','exclusive_root','capacity_pass',
            'global_memory_measured','rss_measured','all_writers_registered','parent_ack_authorized','execution_authenticated')))
        self.assertTrue(held.unresolved());self.assertEqual(list(self.root.iterdir()),[])

    def test_parent_failure_and_two_diagnostics_are_required_before_clock(self):
        self.allocation['parent_raw_maxima'].pop('receipt.json')
        with self.assertRaises(ValueError):self.prepare()
        held=self.parent._partitioned_publication_owner
        self.assertIs(held.original_inputs[3],self.allocation);self.clock.assert_not_called()

    def test_missing_independent_diagnostic_cannot_spend_reserved_slots(self):
        self.allocation['diagnostic_maxima'].pop('diagnostic.log')
        with self.assertRaises(ValueError):self.prepare()
        self.clock.assert_not_called()

    def test_parent_future_bytes_refuse_without_discounting_completed_control(self):
        self.allocation['parent_raw_maxima']['stdout.bin']=1024**2
        with self.assertRaises(ValueError):self.prepare()
        held=self.parent._partitioned_publication_owner
        self.assertLess(held.pending['projection']['remaining_bytes'],0)
        self.assertEqual(held.pending['projection']['parent_failure_bytes'],1024**2+2048)
        self.assertIs(held._returns[-1],held.pending['projection'])

    def test_all_planned_raw_entries_refuse_before_native_even_when_bytes_fit(self):
        self.group=archive.PartitionedArchivePreparation(owner=self.parent,checkpoint=self.clock,allocation={
            'format':archive.PartitionedArchivePreparation.FORMAT,'context':self.context,
            'call_growth_maxima':[12000]*3,'archive_max_bytes':36000,'formal_permission':False})
        self.group.prepare();self.allocation['call_raw_maxima'].append(copy.deepcopy(self.allocation['call_raw_maxima'][0]))
        with self.assertRaises(ValueError):self.prepare()
        view=self.parent._partitioned_publication_owner.pending['projection']
        self.assertGreater(view['remaining_bytes'],0);self.assertEqual(view['remaining_entries'],-2)

    def test_original_partial_raw_is_added_separately_from_all_future_growth(self):
        self.allocation['call_raw_maxima'][0]['partial-archive.bin']=512
        held=self.prepare();prep=self.packet(partial=True);view=held.observe('post-failure')
        self.assertEqual(view['all_call_raw_maxima_bytes'],10752);self.assertEqual(view['archive_growth_maxima_bytes'],24000)
        self.assertEqual(view['remaining_entries'],0)
        self.assertEqual(prep.original_packet['raw']['partial-archive.bin'],b'original partial')

    def test_actual_call_raw_larger_than_independent_declared_slot_is_retained(self):
        self.allocation['call_raw_maxima'][0]['stdout.bin']=1000
        held=self.prepare();prep=self.packet()
        with self.assertRaises(ValueError):held.observe('registered')
        self.assertIs(self.group._owners[0][1],prep);self.assertEqual(len(prep.original_packet['raw']['stdout.bin']),2000)

    def test_occupied_root_entries_count_in_addition_to_future_and_reserve(self):
        (self.root/'one').write_bytes(b'x');(self.root/'two').write_bytes(b'y')
        with self.assertRaises(ValueError):self.prepare()
        row=self.parent._partitioned_publication_owner.pending['projection']
        self.assertEqual(row['snapshot']['directory_entries'],2);self.assertEqual(row['remaining_entries'],-1)

    def test_foreign_parent_context_pin_cannot_become_identity_authentication(self):
        value=archive.v.strict_json(self.identity_raw);value['context_pin']['sha256']='f'*64
        self.identity_raw=archive.io.json_bytes(value)
        with self.assertRaises(ValueError):self.prepare()
        self.clock.assert_not_called();self.assertIs(self.parent._partitioned_publication_owner.original_inputs[-1],self.identity_raw)

    def test_boolean_native_payload_is_not_a_byte_allowance(self):
        self.allocation['native_buffer_payload_bytes']=True
        with self.assertRaises(ValueError):self.prepare()
        self.clock.assert_not_called()

    def test_local_memory_projection_refuses_without_claiming_rss_or_global_peak(self):
        self.allocation['resident_extra_bytes']=321*1024**2
        with self.assertRaises(ValueError):self.prepare()
        row=self.parent._partitioned_publication_owner.pending['projection']
        self.assertGreater(row['memory_projection_bytes'],321*1024**2)
        self.assertFalse(row['global_memory_measured']);self.assertFalse(row['rss_measured'])

    def test_unknown_python_payload_graph_is_retained_without_getter_or_retry(self):
        held=self.prepare();unknown=object();self.group._returns+=(unknown,)
        with self.assertRaises(ValueError) as caught:held.observe('unknown')
        self.assertIs(held.pending['python_graph'][3][-1],unknown);self.clock.reset_mock()
        with self.assertRaises(ValueError) as again:held.observe('again')
        self.assertIs(again.exception,caught.exception);self.clock.assert_not_called()

    def test_unknown_width_return_is_held_before_validation(self):
        held=self.prepare();unknown=object();held._python_width=Mock(return_value=unknown)
        with self.assertRaises(ValueError):held.observe('width')
        self.assertIs(held.pending['python_width_return'],unknown);self.assertIs(held._returns[-1],unknown)

    def test_clock_interrupt_preserves_original_inputs_first_error_and_pending(self):
        error=KeyboardInterrupt('new publication clock risk');self.clock.side_effect=error
        with self.assertRaises(KeyboardInterrupt) as caught:self.prepare()
        held=self.parent._partitioned_publication_owner;self.clock.reset_mock(side_effect=True)
        self.assertIs(held.pending['inputs'],held.original_inputs);self.assertIs(caught.exception,error)
        with self.assertRaises(KeyboardInterrupt) as again:held.view()
        self.assertIs(again.exception,error);self.clock.assert_not_called()

    def test_clock_getter_interrupt_keeps_partial_original_parent_and_all_inputs(self):
        error=KeyboardInterrupt('new parent checkpoint getter risk')
        with patch.object(reader.ReaderGitParent,'inventory_checkpoint',new_callable=PropertyMock,create=True,side_effect=error):
            with self.assertRaises(KeyboardInterrupt) as caught:self.prepare()
        held=self.parent._partitioned_publication_owner
        self.assertIs(held.original_inputs[0],self.parent);self.assertIs(held.original_inputs[3],self.allocation)
        self.assertIs(held._failure,error);self.assertIs(caught.exception.partitioned_publication,held)
        with self.assertRaises(KeyboardInterrupt) as again:self.parent._inventory_ready()
        self.assertIs(again.exception,error)

    def test_callback_projection_mutation_cannot_be_restored_into_permission(self):
        def mutate():
            held=self.parent._partitioned_publication_owner
            if held.pending and 'projection' in held.pending:held.pending['projection']['native_authorized']=True
        self.clock.side_effect=mutate
        with self.assertRaises(ValueError) as caught:self.prepare()
        held=self.parent._partitioned_publication_owner;held.pending['projection']['native_authorized']=False
        held.error=None;self.clock.reset_mock(side_effect=True)
        with self.assertRaises(ValueError) as again:held.view()
        self.assertIs(again.exception,caught.exception);self.clock.assert_not_called()

    def test_reentrant_observe_cannot_overwrite_original_pending(self):
        held=self.prepare();self.clock.side_effect=lambda:held.observe('nested')
        with self.assertRaises(ValueError):held.observe('outer')
        self.assertEqual(held.pending['stage'],'outer');self.assertIs(held.pending['inputs'],held.original_inputs)

    def test_cached_view_has_no_clock_snapshot_width_repetition_and_execute_refuses(self):
        held=self.prepare();self.clock.reset_mock();held._python_width=Mock(side_effect=AssertionError('repeat'))
        view=held.view();view['native_authorized']=True
        self.assertFalse(held.view()['native_authorized']);self.clock.assert_not_called();held._python_width.assert_not_called()
        with self.assertRaises(ValueError):held.execute()
        self.clock.assert_not_called();self.assertEqual(list(self.root.iterdir()),[])

    def test_cached_observation_cannot_cover_later_registered_packet(self):
        held=self.prepare();self.packet()
        with self.assertRaises(ValueError):held.view()
        self.assertIsNotNone(held._completion_anchor)

    def test_completion_and_display_row_transplant_cannot_replace_original(self):
        held=self.prepare();original=held._completion_anchor;row=copy.deepcopy(held.last_observation);row['remaining_bytes']+=1
        held.last_observation=row;held._completed=(row,archive.io.json_bytes(row),original[2])
        with self.assertRaises(ValueError):held.view()
        self.assertIs(held._completion_anchor,original)

    def test_parent_marker_deletion_and_second_preparation_keep_original_and_rejected_inputs(self):
        held=self.prepare();original=self.parent.partitioned_publication_inputs
        self.parent.partitioned_publication=None
        with self.assertRaises(ValueError) as caught:self.prepare()
        self.assertIs(self.parent._partitioned_publication_owner,held);self.assertIs(self.parent.partitioned_publication_inputs,original)
        self.assertIs(held.rejected.original_inputs[3],self.allocation);self.assertIs(caught.exception.partitioned_publication,held)

    def test_unresolved_parent_uses_same_python_retention_before_normal_return(self):
        held=self.prepare()
        with self.assertRaises(ValueError) as caught:self.parent._inventory_ready()
        with patch.object(reader.ParentPublicationRetention,'_pause',side_effect=Escape):
            with self.assertRaises(Escape):reader.retain_parent_publications(caught.exception,self.parent)
        keeper=self.parent.original_publication_retention
        self.assertIs(keeper.parent,self.parent);self.assertIs(keeper.original_error,caught.exception)
        self.assertIs(keeper.owners[-2],held);self.assertIs(keeper.owners[-1],held)
        self.assertIsNone(keeper.worker);self.assertTrue(held.unresolved())

    def test_erased_return_and_binding_ledgers_keep_private_original_payloads(self):
        held=self.prepare();returns=held._returns_anchor;bindings=held._bindings_anchor
        held._returns=();held._observation_bindings=()
        with self.assertRaises(ValueError) as caught:held.view()
        held._returns=returns;held._observation_bindings=bindings;held.error=None
        with self.assertRaises(ValueError) as again:held.observe('restore')
        self.assertIs(again.exception,caught.exception);self.assertIs(held._returns_anchor,returns)
        self.assertIs(held._bindings_anchor,bindings)

    def test_direct_second_constructor_preserves_first_exception_original_owner(self):
        held=self.prepare();second=budget.PartitionedPublicationPreparation.__new__(budget.PartitionedPublicationPreparation)
        with self.assertRaises(ValueError) as caught:second.__init__(owner=self.parent,checkpoint=self.clock,
            archive_preparation=self.group,allocation=self.allocation,entry_raw=self.entry_raw,
            context_raw=self.context_raw,parent_identity_raw=self.identity_raw)
        self.assertIs(held.rejected,second);self.assertIs(second.original_inputs[3],self.allocation)
        self.assertIs(held._failure,caught.exception);self.assertIs(second._failure,caught.exception)
        self.assertIs(caught.exception.partitioned_publication,held);self.assertIs(self.parent._partitioned_publication_owner,held)
