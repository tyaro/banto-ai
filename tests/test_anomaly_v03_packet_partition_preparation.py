"""New memory codec contract risks; no native/protocol fixture execution."""
import copy
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from banto_ai import anomaly_v03_preformal_worker_git_archive as archive


class PacketPartitionPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.owner=object();self.clock=Mock()
        self.context={'request_pin':{'bytes':17,'sha256':'a'*64},'inventory_pin':{'bytes':19,'sha256':'b'*64},
            'revision':'c'*40,'root':str(self.root),'root_identity':[1,2],'lease':0}
        self.packet={'kind':'recovery','event':{'engineering_stub':True,'status':'failed'},'raw':{
            'receipt.json':None,'stdout.bin':random.Random(771).randbytes(90001),
            'stderr.bin':b'engineering-stderr','partial-archive.bin':b'original-partial'}}
        self.limits={'receipt.json':16384,'stdout.bin':131072,'stderr.bin':16384,'partial-archive.bin':65536}
        self.prep=archive.PacketPartitionPreparation(owner=self.owner,checkpoint=self.clock,
            context=self.context,packet=self.packet,raw_limits=self.limits)

    def prepare(self):return self.prep.prepare()

    def test_split_roundtrip_retains_full_raw_under_original_caps_without_archive_io(self):
        view=self.prepare();packet=self.prep.readback(frames=view['frames'],manifest_raw=view['manifest_raw'],manifest_pin=view['manifest_pin'])
        self.assertEqual(packet,self.packet);self.assertGreater(len(view['frames']),3)
        self.assertTrue(all(len(f)<=archive.MAX_RECORD+8 for f in view['frames']))
        self.assertLessEqual(sum(map(len,view['frames'])),archive.MAX_BYTES)
        self.assertEqual(list(self.root.iterdir()),[]);self.assertIs(self.prep.original_owner,self.owner)
        self.assertFalse(any(view[n] for n in ('native_authorized','capacity_pass','atomic_reservation','lease_completed','parent_ack_authorized','execution_authenticated')))

    def test_empty_stdout_and_none_receipt_remain_distinct_from_missing_raw(self):
        self.packet['raw']['stdout.bin']=b'';view=self.prepare()
        packet=self.prep.readback(frames=view['frames'],manifest_raw=view['manifest_raw'],manifest_pin=view['manifest_pin'])
        self.assertEqual(packet['raw']['stdout.bin'],b'');self.assertIsNone(packet['raw']['receipt.json'])

    def test_missing_original_stderr_retains_original_inputs_and_first_error(self):
        self.packet['raw'].pop('stderr.bin')
        with self.assertRaises(ValueError) as caught:self.prepare()
        self.assertIs(self.prep.original_packet,self.packet);self.assertIs(self.prep.original_owner,self.owner)
        self.prep.error=None
        with self.assertRaises(ValueError) as again:self.prepare()
        self.assertIs(again.exception,caught.exception)

    def test_foreign_request_manifest_refuses_self_consistent_repin_and_keeps_incoming(self):
        view=self.prepare();manifest=archive.v.strict_json(view['manifest_raw']);manifest['context']['request_pin']['sha256']='d'*64
        raw=archive.io.json_bytes(manifest)
        with self.assertRaises(ValueError):self.prep.readback(frames=view['frames'],manifest_raw=raw,manifest_pin=archive.observed._pin(raw))
        self.assertIs(self.prep.rejected[-1]['manifest_raw'],raw)

    def test_frame_reordering_rejects_before_false_full_readback(self):
        view=self.prepare();frames=tuple(reversed(view['frames']))
        with self.assertRaises(ValueError):self.prep.readback(frames=frames,manifest_raw=view['manifest_raw'],manifest_pin=view['manifest_pin'])
        self.assertIs(self.prep.rejected[-1]['frames'],frames)

    def test_missing_frame_or_trailing_frame_rejects_complete_coverage(self):
        view=self.prepare();frames=view['frames'][:-1]
        with self.assertRaises(ValueError):self.prep.readback(frames=frames,manifest_raw=view['manifest_raw'],manifest_pin=view['manifest_pin'])
        self.assertEqual(self.prep.rejected[-1]['frames'],frames)

    def test_changed_payload_is_rejected_with_original_owner_retained(self):
        view=self.prepare();frames=(view['frames'][0][:-1]+bytes([view['frames'][0][-1]^1]),)+view['frames'][1:]
        with self.assertRaises(ValueError):self.prep.readback(frames=frames,manifest_raw=view['manifest_raw'],manifest_pin=view['manifest_pin'])
        self.assertIs(self.prep.original_owner,self.owner)

    def test_original_partial_raw_is_separate_from_new_archive_growth(self):
        view=self.prepare();manifest=archive.v.strict_json(view['manifest_raw'])
        self.assertEqual(manifest['packet']['raw_pins']['partial-archive.bin'],archive.observed._pin(b'original-partial'))
        self.assertEqual(manifest['archive_growth_bytes'],sum(map(len,view['frames'])))
        self.assertEqual(self.limits['partial-archive.bin'],65536)

    def test_unknown_compress_return_retained_before_type_rejection_and_no_replay(self):
        unknown=object()
        with patch.object(archive.gzip,'compress',return_value=unknown) as compress:
            prep=archive.PacketPartitionPreparation(owner=self.owner,checkpoint=self.clock,context=self.context,packet=self.packet,raw_limits=self.limits)
            with self.assertRaises(ValueError) as caught:prep.prepare()
            self.assertIs(prep.retained[0]['compressed'],unknown);self.assertIn(unknown,prep._raw_returns)
            with self.assertRaises(ValueError) as again:prep.prepare()
            self.assertIs(again.exception,caught.exception);self.assertEqual(compress.call_count,1)

    def test_oversized_compressed_return_keeps_encoded_and_compressed_without_frame(self):
        huge=b'x'*(archive.MAX_RECORD+1)
        with patch.object(archive.gzip,'compress',return_value=huge):
            prep=archive.PacketPartitionPreparation(owner=self.owner,checkpoint=self.clock,context=self.context,packet=self.packet,raw_limits=self.limits)
            with self.assertRaises(ValueError):prep.prepare()
        self.assertIs(prep.retained[0]['compressed'],huge);self.assertIn('encoded',prep.retained[0]);self.assertNotIn('frame',prep.retained[0])

    def test_archive_aggregate_limit_refuses_even_when_each_frame_fits(self):
        self.packet['raw']['stdout.bin']=random.Random(991).randbytes(600000);self.limits['stdout.bin']=600000
        with self.assertRaises(ValueError):self.prepare()
        frames=self.prep.pending['frames'];self.assertTrue(all(len(f)<=archive.MAX_RECORD+8 for f in frames))
        self.assertGreater(sum(map(len,frames)),archive.MAX_BYTES);self.assertEqual(list(self.root.iterdir()),[])

    def test_clock_interrupt_keeps_packet_and_original_pending_without_recompression(self):
        failure=KeyboardInterrupt('new partition clock risk');self.clock.side_effect=failure
        with self.assertRaises(KeyboardInterrupt) as caught:self.prepare()
        self.assertIs(caught.exception,failure);pending=self.prep.pending;self.clock.reset_mock(side_effect=True)
        with self.assertRaises(KeyboardInterrupt) as again:self.prepare()
        self.assertIs(again.exception,failure);self.assertIs(self.prep.pending,pending);self.clock.assert_not_called()

    def test_cached_view_and_execute_do_not_recompress_or_call_clock(self):
        view=self.prepare();self.clock.reset_mock()
        with patch.object(archive.gzip,'compress',wraps=archive.gzip.compress):
            # Changing the held callable is itself refused without invoking it.
            with self.assertRaises(ValueError):self.prep.view()
        self.clock.assert_not_called()
        fresh=archive.PacketPartitionPreparation(owner=self.owner,checkpoint=self.clock,context=self.context,packet=self.packet,raw_limits=self.limits)
        other=fresh.prepare();self.clock.reset_mock();self.assertEqual(fresh.view(),other);self.assertEqual(fresh.prepare(),other)
        other['native_authorized']=True
        with self.assertRaisesRegex(ValueError,'admission not prepared'):fresh.execute()
        self.clock.assert_not_called()

    def test_completion_metadata_and_caller_snapshot_cannot_be_rebased_together(self):
        self.prepare();self.packet['event']['status']='verified';self.prep.result['packet']['event']['status']='verified'
        with self.assertRaises(ValueError):self.prep.view()
        self.assertIs(self.prep.original_owner,self.owner);self.assertIsNotNone(self.prep._completion_anchor)

    def test_pending_reference_deletion_from_clock_latches_original_owner(self):
        self.clock.side_effect=lambda:setattr(self.prep,'pending',None)
        with self.assertRaises(ValueError):self.prepare()
        self.assertIs(self.prep._pending_anchor['packet'],self.packet);self.assertIs(self.prep.original_owner,self.owner)

    def test_returned_buffer_row_deletion_keeps_private_original_return_and_refuses(self):
        def clock():
            if self.prep.retained and 'compressed' in self.prep.retained[0]:
                self.prep.retained[0].pop('compressed')
        self.clock.side_effect=clock
        with self.assertRaises(ValueError) as caught:self.prepare()
        self.assertTrue(any(type(raw) is bytes and raw[:2]==b'\x1f\x8b' for raw in self.prep._raw_returns))
        self.assertIs(self.prep.original_packet,self.packet);self.prep.error=None
        with self.assertRaises(ValueError) as again:self.prepare()
        self.assertIs(again.exception,caught.exception)

    def test_incoming_owner_marker_deletion_keeps_original_readback_bytes(self):
        view=self.prepare();self.clock.side_effect=lambda:self.prep.rejected.clear()
        with self.assertRaises(ValueError):self.prep.readback(frames=view['frames'],manifest_raw=view['manifest_raw'],manifest_pin=view['manifest_pin'])
        self.assertIs(self.prep._readback_owners[0][1],view['frames'])
        self.assertIs(self.prep._readback_owners[0][2],view['manifest_raw'])

    def test_pending_packet_metadata_deletion_cannot_hide_original_input(self):
        self.clock.side_effect=lambda:self.prep.pending.pop('packet',None)
        with self.assertRaises(ValueError):self.prepare()
        self.assertIs(self.prep._inputs[3],self.packet);self.assertIs(self.prep.original_owner,self.owner)

    def test_incoming_row_field_deletion_keeps_private_raw_and_refuses(self):
        view=self.prepare();self.clock.side_effect=lambda:self.prep.rejected[-1].pop('manifest_raw',None)
        with self.assertRaises(ValueError):self.prep.readback(frames=view['frames'],manifest_raw=view['manifest_raw'],manifest_pin=view['manifest_pin'])
        self.assertIs(self.prep._readback_owners[0][2],view['manifest_raw'])

    def test_record_value_mutation_refuses_before_compress_and_keeps_original_encoded(self):
        def clock():
            if self.prep.retained:self.prep.retained[0]['record']['offset']=1
        self.clock.side_effect=clock
        with self.assertRaises(ValueError):self.prepare()
        row=self.prep.retained[0];self.assertEqual(archive.v.strict_json(row['encoded'])['offset'],0)
        self.assertNotIn('compressed',row);self.assertIn(row['encoded'],self.prep._raw_returns)


if __name__=='__main__':unittest.main()
