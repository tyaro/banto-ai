"""Explicit failure raw maxima; fake channel budget, real small/retained files."""
import copy
import os
from types import SimpleNamespace
from unittest.mock import patch
import unittest

from banto_ai import anomaly_v03_preformal_reader_git_worker as worker
from tests import test_anomaly_v03_reader_git_parent_connection as fixtures


class ReaderGitRawAllocationTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ReaderGitParentControllerTests()
        self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.limits={operation:{'receipt.json':16384,'stdout.bin':maximum,
            'stderr.bin':16384,'partial-archive.bin':65536} for operation,maximum in
            (('head',128),('status',65536),('source_blob',131072))}

    def create(self, **options):
        return self.f.create(pipe_raw_limits=options.get('limits',self.limits))

    def test_exact_sixty_four_calls_bind_independent_failure_limits_to_original_inventory_pin(self):
        controller=self.create();raw=worker.observed._file(
            controller.parent.root/'worker-inventory.json',worker.channel.MAX_CONTROL)
        inventory=worker.v.strict_json(raw)
        self.assertEqual(worker.observed._pin(raw),controller.entry['inventory_pin'])
        self.assertEqual(len(inventory['calls']),64)
        for call in inventory['calls']:
            self.assertEqual(call['raw_inventory'],self.limits[call['operation']])
            if call['operation']=='source_blob':
                self.assertNotEqual(call['raw_inventory']['stdout.bin'],call['expected_output_pin']['bytes'])
        self.assertIs(controller.shared,self.f.shared);self.assertIs(controller.budget,self.f.budget)
        self.assertIsNone(controller.worker);self.assertFalse((self.f.f.measured/'worker-git-inflight').exists())

    def test_source_and_limit_inputs_are_snapshotted_before_shared_or_source_io(self):
        original=copy.deepcopy(self.f.pins);limits=copy.deepcopy(self.limits)
        def alter(*_):self.f.pins.clear();self.limits.clear()
        self.f.shared.require_stage.side_effect=alter
        controller=self.create()
        self.assertEqual(controller.source_pins,original);self.assertEqual(controller.pipe_raw_limits,limits)
        inventory=worker.v.strict_json((controller.parent.root/'worker-inventory.json').read_bytes())
        self.assertEqual(inventory['calls'][2]['expected_output_pin'],original[self.f.names[0]])
        self.assertEqual(inventory['calls'][2]['raw_inventory'],limits['source_blob'])

    def test_generic_failure_maxima_deny_before_channel_root_or_new_clock(self):
        limits=copy.deepcopy(self.limits)
        limits['source_blob'].update({'stdout.bin':1048576,'stderr.bin':65536,'partial-archive.bin':524288})
        with patch.object(worker.channel.ParentChannel,'create') as create,self.assertRaises(ValueError):
            self.create(limits=limits)
        create.assert_not_called();self.f.shared.require_stage.assert_not_called();self.assertFalse(self.f.root.exists())

    def test_exact_source_or_head_payload_without_detection_byte_is_rejected(self):
        for operation,amount in (('source_blob',max(p['bytes'] for p in self.f.pins.values())),('head',41)):
            with self.subTest(operation=operation):
                limits=copy.deepcopy(self.limits);limits[operation]['stdout.bin']=amount
                with patch.object(worker.channel.ParentChannel,'create') as create,self.assertRaises(ValueError):
                    self.create(limits=limits)
                create.assert_not_called();self.assertFalse(self.f.root.exists())

    def test_closed_positive_allocation_rejects_bool_unknown_names_and_missing_operations(self):
        variants=[]
        for value in (True,0,-1,16385):
            limits=copy.deepcopy(self.limits);limits['head']['receipt.json']=value;variants.append(limits)
        limits=copy.deepcopy(self.limits);limits['status']['unmeasured.bin']=1;variants.append(limits)
        limits=copy.deepcopy(self.limits);limits.pop('status');variants.append(limits)
        for limits in variants:
            with self.subTest(limits=limits),patch.object(worker.channel.ParentChannel,'create') as create, self.assertRaises(ValueError):
                self.create(limits=limits)
            create.assert_not_called();self.assertFalse(self.f.root.exists())

    def test_original_admission_counts_retained_file_and_new_bounded_sinks_without_native_job(self):
        controller=self.create();root=self.f.f.measured
        retained=root/'unverified-retained.bin';retained.write_bytes(b'x'*(512*1024))
        control=root/'unverified-control.bin';control.write_bytes(b'y'*(32*1024))
        call=worker.v.strict_json((controller.parent.root/'worker-inventory.json').read_bytes())['calls'][2]
        identity=(root.stat().st_dev,root.stat().st_ino)
        admission=worker.tree.GitSinkAdmission(root=root,root_identity=identity,
            revision=self.f.f.revision,call=call,checkpoint=controller.checkpoint)
        self.addCleanup(lambda:[stream.close() for stream in admission.streams.values() if not stream.closed])
        with patch.object(worker.tree,'os',SimpleNamespace(
                name='nt',devnull=os.devnull,fstat=os.fstat,fsync=os.fsync)):
            admission.create()
        self.assertEqual(admission.limits,call['raw_inventory'])
        self.assertEqual(sum(admission.limits.values()),229376)
        self.assertIsNone(admission.native.job);self.assertEqual(retained.stat().st_size,512*1024)
        self.assertEqual(admission.snapshot['directory_bytes']+sum(admission.limits.values())+131072 <= 1048576,True)
        self.assertIsNone(controller.worker)

    def test_real_retained_root_overfill_preserves_raw_and_denies_before_sink_or_job(self):
        controller=self.create();root=self.f.f.measured
        retained=root/'unverified-large.bin';retained.write_bytes(b'x'*(700*1024))
        call=worker.v.strict_json((controller.parent.root/'worker-inventory.json').read_bytes())['calls'][2]
        with self.assertRaises(worker.tree.owner.UnreapedJob) as caught:
            worker.tree.GitSinkAdmission(root=root,root_identity=(root.stat().st_dev,root.stat().st_ino),
                revision=self.f.f.revision,call=call,checkpoint=controller.checkpoint)
        self.assertIsNone(caught.exception.job);self.assertEqual(caught.exception.git_sink_admission.streams,{})
        self.assertTrue(retained.exists());self.assertFalse((root/'worker-git-inflight').exists())


if __name__=='__main__':unittest.main()
