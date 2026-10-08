"""New all-call memory preparation risks; no native or legacy focus execution."""
import copy
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from banto_ai import anomaly_v03_preformal_worker_git_archive as archive


class PartitionedArchivePreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.owner=object();self.clock=Mock()
        self.context={'request_pin':{'bytes':17,'sha256':'a'*64},'inventory_pin':{'bytes':19,'sha256':'b'*64},
            'revision':'c'*40,'root':str(self.root),'root_identity':[1,2]}
        self.allocation={'format':archive.PartitionedArchivePreparation.FORMAT,'context':self.context,
            'call_growth_maxima':[60000,60000],'archive_max_bytes':120000,'formal_permission':False}
        self.group=archive.PartitionedArchivePreparation(owner=self.owner,checkpoint=self.clock,allocation=self.allocation)

    def packet(self,lease,kind='receipt',**kwargs):
        raw={'receipt.json':None,'stdout.bin':random.Random(831+lease).randbytes(40000),
            'stderr.bin':b'engineering-stderr','partial-archive.bin':b'original-partial' if kind=='recovery' else None}
        prep=archive.PacketPartitionPreparation(owner=kwargs.get('owner',self.owner),checkpoint=kwargs.get('clock',self.clock),
            context=kwargs.get('context',{**copy.deepcopy(self.context),'lease':lease}),
            packet={'kind':kind,'event':{'engineering_stub':True,'lease':lease},'raw':raw},
            raw_limits={'receipt.json':16384,'stdout.bin':131072,'stderr.bin':16384,'partial-archive.bin':65536})
        prep.prepare();return prep

    def full(self):
        self.group.prepare();first=self.packet(0);last=self.packet(1,'recovery')
        self.group.register(first);self.group.register(last);return first,last,self.group.bundle()

    def test_all_planned_calls_full_raw_manifest_and_partial_remain_separate(self):
        first,last,view=self.full()
        packets=self.group.readback(archive_raw=view['archive_raw'],manifest_raw=view['manifest_raw'],manifest_pin=view['manifest_pin'])
        self.assertEqual(packets,(first.original_packet,last.original_packet))
        manifest=archive.v.strict_json(view['manifest_raw'])
        self.assertEqual(manifest['archive_pin'],archive.observed._pin(view['archive_raw']))
        self.assertEqual([r['lease'] for r in manifest['packets']],[0,1])
        self.assertEqual(manifest['packets'][1]['offset'],manifest['packets'][0]['growth_bytes'])
        self.assertEqual(packets[-1]['raw']['partial-archive.bin'],b'original-partial')
        self.assertEqual(self.group.plan()['reserved_maxima_bytes'],120000)
        self.assertEqual(list(self.root.iterdir()),[])
        self.assertFalse(any(view[n] for n in ('native_authorized','atomic_reservation','capacity_pass',
            'lease_completed','parent_ack_authorized','execution_authenticated')))

    def test_all_future_maxima_exceed_archive_before_clock_or_packet_codec(self):
        self.allocation['call_growth_maxima']=[300000,300000];self.allocation['archive_max_bytes']=archive.MAX_BYTES
        with self.assertRaises(ValueError):self.group.prepare()
        self.clock.assert_not_called();self.assertIs(self.group._inputs[2],self.allocation)
        self.assertEqual(self.group._returns,())

    def test_closed_allocation_extra_field_cannot_grant_native(self):
        self.allocation['native_authorized']=True
        with self.assertRaises(ValueError):self.group.prepare()
        self.assertIs(self.group.original_owner,self.owner);self.clock.assert_not_called()

    def test_boolean_growth_maximum_is_not_a_byte_reservation(self):
        self.allocation['call_growth_maxima']=[True]
        with self.assertRaises(ValueError):self.group.prepare()
        self.clock.assert_not_called()

    def test_completed_slot_does_not_discount_original_all_future_maxima(self):
        self.group.prepare();self.group.register(self.packet(0))
        self.allocation['call_growth_maxima'][0]=1
        with self.assertRaises(ValueError) as caught:self.group.plan()
        self.allocation['call_growth_maxima'][0]=60000;self.group.error=None
        with self.assertRaises(ValueError) as again:self.group.plan()
        self.assertIs(again.exception,caught.exception);self.assertEqual(len(self.group._ledger),1)

    def test_same_shape_foreign_owner_is_retained_and_refused(self):
        self.group.prepare();foreign=self.packet(0,owner=object())
        with self.assertRaises(ValueError):self.group.register(foreign)
        self.assertIs(self.group._owners[0][1],foreign);self.assertIs(self.group.original_owner,self.owner)
        self.assertEqual(self.group.completed,[])

    def test_foreign_clock_is_refused_before_packet_readback(self):
        self.group.prepare();foreign=self.packet(0,clock=Mock())
        with self.assertRaises(ValueError):self.group.register(foreign)
        self.assertEqual(foreign._readback_owners,())

    def test_foreign_request_inventory_root_identity_or_revision_cannot_be_rebound(self):
        self.group.prepare();foreign_context={**copy.deepcopy(self.context),'lease':0}
        foreign_context['inventory_pin']['sha256']='d'*64
        foreign=self.packet(0,context=foreign_context)
        with self.assertRaises(ValueError):self.group.register(foreign)
        self.assertEqual(foreign._readback_owners,());self.assertIs(self.group._owners[0][1],foreign)

    def test_duplicate_original_packet_cannot_supply_next_lease(self):
        self.group.prepare();first=self.packet(0);self.group.register(first)
        with self.assertRaises(ValueError):self.group.register(first)
        self.assertEqual(len(first._readback_owners),1);self.assertEqual(len(self.group._ledger),1)

    def test_per_call_growth_refused_even_with_room_in_total_archive(self):
        self.allocation['call_growth_maxima']=[1000,60000];self.group.prepare();first=self.packet(0)
        with self.assertRaises(ValueError):self.group.register(first)
        self.assertGreater(self.group.pending['growth_bytes'],1000)
        self.assertIs(self.group._returns[-1],self.group.pending['readback'])
        self.assertEqual(self.group.completed,[])

    def test_no_later_packet_after_recovery_prefix_and_no_false_complete_bundle(self):
        self.group.prepare();failure=self.packet(0,'recovery');self.group.register(failure);later=self.packet(1)
        with self.assertRaises(ValueError):self.group.register(later)
        self.assertEqual(len(self.group._ledger),1);self.assertEqual(later._readback_owners,())

    def test_zero_or_partial_planned_call_coverage_cannot_bundle(self):
        self.group.prepare();self.group.register(self.packet(0))
        with self.assertRaises(ValueError):self.group.bundle()
        self.assertIsNone(self.group._bundle);self.assertEqual(len(self.group._ledger),1)

    def test_callback_readback_return_mutation_retains_original_packet_and_first_error(self):
        self.group.prepare();first=self.packet(0)
        def clock():
            if self.group.pending and 'readback' in self.group.pending:
                self.group.pending['readback']['kind']='recovery'
        self.clock.side_effect=clock
        with self.assertRaises(ValueError) as caught:self.group.register(first)
        self.assertEqual(archive.v.strict_json(self.group._return_bindings[0][-1])['kind'],'receipt')
        self.assertIs(self.group._returns[-1],self.group.pending['readback'])
        self.clock.reset_mock(side_effect=True);self.group.error=None
        with self.assertRaises(ValueError) as again:self.group.register(first)
        self.assertIs(again.exception,caught.exception);self.clock.assert_not_called()

    def test_callback_incoming_owner_deletion_keeps_original_reference(self):
        self.group.prepare();first=self.packet(0)
        self.clock.side_effect=lambda:self.group.rejected[-1].pop('preparation',None)
        with self.assertRaises(ValueError):self.group.register(first)
        self.assertIs(self.group._owners[0][1],first);self.assertEqual(first._readback_owners,())

    def test_reentrant_register_cannot_replace_original_pending_owner(self):
        self.group.prepare();first=self.packet(0);second=self.packet(1)
        self.clock.side_effect=lambda:self.group.register(second)
        with self.assertRaises(ValueError):self.group.register(first)
        self.assertIs(self.group._pending_input[1],first);self.assertEqual(self.group.completed,[])
        self.assertIs(self.group._owners[-1][1],second)

    def test_clock_interrupt_retains_original_pending_and_forbids_replay(self):
        self.group.prepare();first=self.packet(0);failure=KeyboardInterrupt('new aggregate clock risk')
        self.clock.side_effect=failure
        with self.assertRaises(KeyboardInterrupt) as caught:self.group.register(first)
        self.assertIs(caught.exception,failure);self.clock.reset_mock(side_effect=True)
        with self.assertRaises(KeyboardInterrupt) as again:self.group.register(first)
        self.assertIs(again.exception,failure);self.clock.assert_not_called();self.assertIs(self.group._owners[0][1],first)

    def test_completed_row_and_bundle_metadata_cannot_be_rebased(self):
        self.full();self.group.completed[0]['packet_manifest_pin']['sha256']='d'*64
        with self.assertRaises(ValueError):self.group.bundle()
        self.assertIsNotNone(self.group._bundle_anchor)

    def test_cached_bundle_refuses_replaced_original_bytes(self):
        self.full();original=self.group._bundle_anchor[0]
        self.group._bundle=(original[0]+b'x',original[1],original[2])
        with self.assertRaises(ValueError):self.group.bundle()
        self.assertIs(self.group._bundle_anchor[0],original)

    def test_registered_ledger_and_display_rows_cannot_be_transplanted_together(self):
        self.group.prepare();first=self.packet(0);self.group.register(first)
        original=self.group._ledger_anchor
        replacement=list(original[0]);replacement[0]=copy.deepcopy(replacement[0]);replacement[0]['growth_bytes']=1
        replacement[1]=archive.io.json_bytes(replacement[0])
        self.group._ledger=(tuple(replacement),);self.group.completed=[replacement[0]]
        with self.assertRaises(ValueError):self.group.plan()
        self.assertIs(self.group._ledger_anchor,original);self.assertIs(original[0][2],first)

    def test_external_repin_of_foreign_manifest_retains_incoming_without_publication(self):
        _,_,view=self.full();manifest=archive.v.strict_json(view['manifest_raw']);manifest['packets'][0]['lease']=7
        raw=archive.io.json_bytes(manifest);pin=archive.observed._pin(raw)
        with self.assertRaises(ValueError):self.group.readback(archive_raw=view['archive_raw'],manifest_raw=raw,manifest_pin=pin)
        self.assertIs(self.group._incoming[0][2],raw);self.assertIs(self.group._incoming[0][3],pin)
        self.assertEqual(list(self.root.iterdir()),[])

    def test_cached_plan_bundle_and_execute_do_not_call_clock_or_codec(self):
        self.full();self.clock.reset_mock();self.clock.side_effect=AssertionError('cached clock forbidden')
        plan=self.group.plan();view=self.group.bundle();self.assertEqual(plan,self.group.prepare())
        view['native_authorized']=True;plan['atomic_reservation']=True
        self.assertFalse(self.group.bundle()['native_authorized']);self.assertFalse(self.group.plan()['atomic_reservation'])
        with self.assertRaisesRegex(ValueError,'admission not prepared'):self.group.execute()
        self.clock.assert_not_called()


if __name__=='__main__':unittest.main()
