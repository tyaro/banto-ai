"""New archive growth gates; reuse setup helpers, never prior test methods."""
import copy
import unittest
from unittest.mock import Mock,patch

from banto_ai import anomaly_v03_preformal_worker_git_archive as archive
from tests import test_anomaly_v03_worker_git_proof as fixtures


class WorkerGitAppendAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.WorkerGitProofTests('test_normal_raw_close_then_lease_proof_and_real_parent_fence_path')
        self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.clock=Mock(return_value=None)
        self.controls={n:archive.proof.channel.MAX_CONTROL for n in archive.ArchiveAppendAdmission.CONTROL_NAMES}

    def configure(self, *, inventory_pin=None, partial_cap=1):
        f=self.f
        f.inventory['calls'][0]['raw_inventory']['partial-archive.bin']=partial_cap
        f.configure()
        info=f.measured.lstat()
        self.admission=archive.ArchiveAppendAdmission(root=f.measured,root_identity=(info.st_dev,info.st_ino),
            revision=f.revision,inventory_pin=inventory_pin or f.verifier.inventory_pin,
            control_limits=self.controls,checkpoint=self.clock)
        self.writer=archive.WorkerGitArchive(path=f.measured/'worker-git.bin',verifier=f.verifier,
            checkpoint=self.clock,append_admission=self.admission)
        return f

    def test_original_partial_raw_cap_is_independent_of_new_frame_growth(self):
        f=self.configure();self.controls.clear();f.receipt()
        original=copy.deepcopy(f.packets[0]);self.writer.append(0)
        row=self.admission.completed[0]
        self.assertGreater(row['frame_pin']['bytes'],1)
        self.assertEqual(f.packets[0],original)
        self.assertEqual(self.admission.control_limits.keys(),set(archive.ArchiveAppendAdmission.CONTROL_NAMES))
        self.assertFalse(row['atomic_reservation']);self.assertFalse(row['lease_completed'])
        self.assertFalse(row['parent_ack_authorized']);self.assertFalse(row['execution_authenticated'])

    def test_retained_failure_raw_is_counted_before_frame_write(self):
        f=self.configure();f.receipt();retained=f.measured/'original-failure.bin'
        retained.write_bytes(b'x'*(600*1024));before=retained.read_bytes()
        with patch.object(archive,'_append_frame') as append:
            with self.assertRaisesRegex(ValueError,'outer remaining budget'):self.writer.append(0)
        append.assert_not_called();self.assertEqual(self.writer.path.read_bytes(),b'')
        self.assertEqual(retained.read_bytes(),before);self.assertEqual(self.writer.pending['packet'],f.packets[0])
        self.assertTrue(self.admission.pending['frame']);self.assertTrue(self.writer.failed)
        pending=self.writer.pending
        with self.assertRaises(ValueError):self.writer.append(0)
        self.assertIs(self.writer.pending,pending)

    def test_pending_control_entries_and_diagnostic_reserve_are_counted(self):
        f=self.configure();f.receipt()
        for n in range(24):(f.measured/('kept-'+str(n)+'.bin')).write_bytes(b'')
        with patch.object(archive,'_append_frame') as append:
            with self.assertRaisesRegex(ValueError,'outer remaining budget'):self.writer.append(0)
        append.assert_not_called();self.assertEqual(len(list(f.measured.glob('kept-*'))),24)
        self.assertGreater(self.admission.pending['before']['future_entries'],0)

    def test_clock_interruption_preserves_original_frame_without_replay(self):
        f=self.configure();f.receipt();failure=KeyboardInterrupt('invented append clock interruption')
        def clock():
            if self.admission.pending is not None:raise failure
        self.clock.side_effect=clock
        with patch.object(archive,'_append_frame') as append:
            with self.assertRaises(KeyboardInterrupt) as caught:self.writer.append(0)
        self.assertIs(caught.exception,failure);self.assertIs(self.admission.error,failure)
        self.assertIs(self.admission.pending['frame'],self.writer.pending['frame']);append.assert_not_called()
        self.assertEqual(self.writer.path.read_bytes(),b'')

    def test_control_growth_after_write_poison_keeps_archive_and_raw(self):
        f=self.configure();target=f.receipt();original=copy.deepcopy(f.packets[0]);real=archive._append_frame
        def write(path,frame):
            real(path,frame);(f.measured/'concurrent-retained.bin').write_bytes(b'x'*(600*1024))
        with patch.object(archive,'_append_frame',side_effect=write) as append:
            with self.assertRaisesRegex(ValueError,'outer remaining budget'):self.writer.append(0)
        self.assertEqual(append.call_count,1);stored=self.writer.path.read_bytes();self.assertTrue(stored)
        self.assertEqual(self.admission.pending['readback_raw'],stored)
        self.assertEqual(self.writer.pending['packet'],original);self.assertTrue((target/'receipt.json').exists())
        self.assertEqual(self.admission.completed,[])
        with self.assertRaises(ValueError):self.writer.append(0)
        self.assertEqual(self.writer.path.read_bytes(),stored)

    def test_foreign_inventory_denies_before_creating_empty_archive(self):
        bad={'bytes':1,'sha256':'0'*64}
        with self.assertRaisesRegex(ValueError,'exact inventory'):self.configure(inventory_pin=bad)
        self.assertFalse((self.f.measured/'worker-git.bin').exists())
        self.assertIsNotNone(self.admission.writer);self.assertIsNotNone(self.admission.error)

    def test_closed_control_inventory_rejects_missing_or_boolean_maximum(self):
        f=self.f;f.configure();info=f.measured.lstat()
        for bad in ({}, {**self.controls,'ack.json':True}):
            with self.assertRaisesRegex(ValueError,'control maxima'):
                archive.ArchiveAppendAdmission(root=f.measured,root_identity=(info.st_dev,info.st_ino),
                    revision=f.revision,inventory_pin=f.verifier.inventory_pin,control_limits=bad,checkpoint=self.clock)
        self.assertFalse((f.measured/'worker-git.bin').exists())

    def test_clock_cannot_reduce_held_future_control_plan(self):
        f=self.configure();f.receipt();held=self.admission.plan_raw
        def clock():
            if self.admission.pending is not None:self.admission.control_limits.clear()
        self.clock.side_effect=clock
        with patch.object(archive,'_append_frame') as append:
            with self.assertRaisesRegex(ValueError,'held plan'):self.writer.append(0)
        append.assert_not_called();self.assertEqual(self.admission.plan_raw,held)
        self.assertEqual(self.writer.path.read_bytes(),b'');self.assertTrue(self.admission.pending['frame'])

    def test_control_publication_after_root_scan_cannot_unreserve_future_slot(self):
        from banto_ai import anomaly_v03_preformal_generated_chain_budget as monitor
        f=self.configure();f.receipt();snapshot=monitor._directory_snapshot;real_append=archive._append_frame
        observations=[]
        def scan(*args):
            value=snapshot(*args)
            if not observations:
                (f.child.root/'git-proof.json').write_bytes(b'x'*archive.proof.channel.MAX_CONTROL)
            observations.append(value)
            return value
        def append(path,frame):
            held=self.admission.pending['before']
            self.assertEqual(held['future_bytes'],sum(self.controls.values()))
            self.assertEqual(held['future_entries'],len(self.controls))
            real_append(path,frame)
        with patch.object(monitor,'_directory_snapshot',side_effect=scan), \
             patch.object(archive,'_append_frame',side_effect=append):
            self.writer.append(0)
        self.assertEqual(len(observations),2)
        self.assertGreater(observations[1]['directory_entries'],observations[0]['directory_entries'])
        self.assertFalse(self.admission.completed[0]['atomic_reservation'])
