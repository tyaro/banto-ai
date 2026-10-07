"""Worker archive/resolver gates; reuse fake fixtures, never prior test suites."""
import copy
import gzip
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_preformal_worker_git_archive as archive
from tests import test_anomaly_v03_worker_git_proof as fixtures

proof, tree = archive.proof, archive.proof.tree


class WorkerGitArchiveTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.WorkerGitProofTests('test_normal_raw_close_then_lease_proof_and_real_parent_fence_path')
        self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        self.checkpoint = Mock(return_value=None)

    def configure(self, calls=1):
        f = self.fixture
        f.inventory['calls'] = [f.call(n,'pre' if n == 0 else 'post') for n in range(calls)]
        f.configure()
        self.writer = archive.WorkerGitArchive(path=f.measured/'worker-git.bin',
            verifier=f.verifier,checkpoint=self.checkpoint)
        return f

    def saved(self, *, endpoint=None, manifest=None):
        f = self.fixture
        raw,pin = self.writer.manifest() if manifest is None else manifest
        return archive.SavedWorkerGitArchive(endpoint=endpoint or f.child,manifest_raw=raw,manifest_pin=pin,
            inventory_raw=self.writer.inventory_raw,inventory_pin=f.verifier.inventory_pin,
            checkpoint=self.checkpoint)

    def retype(self, operation, stdout, source=None):
        f = self.fixture; packet = f.packets[0];receipt=tree.v.strict_json(packet['raw']['receipt.json'])
        expected=tree.observed._pin(stdout) if operation=='source_blob' else None
        receipt.update(operation=operation,source_path=source,expected_output_pin=expected,
                       stdout_pin=tree.observed._pin(stdout),stdout_bytes=len(stdout))
        receipt['argv']=receipt['argv'][:-2]+tree.direct._command(f.policy,operation,source,expected)
        packet['raw']['stdout.bin']=stdout;packet['raw']['receipt.json']=tree.io.json_bytes(receipt)
        packet['event']['receipt_pin']=tree.observed._pin(packet['raw']['receipt.json'])

    def test_original_raw_and_post_close_event_roundtrip_without_source_cleanup(self):
        f=self.configure();target=f.receipt();original=copy.deepcopy(f.packets[0])
        row=self.writer.append(0);saved=self.saved()
        self.assertEqual(saved.read(0),original);self.assertEqual(saved.verifier.record(0)[0],row)
        self.assertEqual(set(p.name for p in target.iterdir()),{'receipt.json','stdout.bin','stderr.bin'})
        returned=saved.read(0);returned['event'].clear()
        self.assertEqual(saved.read(0),original);self.assertGreater(self.checkpoint.call_count,0)

    def test_archived_raw_drives_lease_ack_and_independent_parent_fence(self):
        f=self.configure();f.child.begin_job();f.receipt();self.writer.append(0)
        child_saved=self.saved();parent_saved=self.saved(endpoint=f.parent)
        adapter=proof.VerifiedLeases(child=f.child,verifier=child_saved.verifier)
        f.parent.verify_quiescent=parent_saved.verifier.verify
        adapter.finish(0);adapter.acknowledge();self.assertTrue(f.parent.fence(f.process))
        self.assertEqual(f.child.finished,1);self.assertFalse(f.child.active)

    def test_head_status_and_source_blob_binding_use_saved_receipt_policy_checks(self):
        # This case covers status; head is covered above and source_blob below.
        f=self.fixture;f.inventory['calls'][0]['operation']='status';f.configure()
        self.writer=archive.WorkerGitArchive(path=f.measured/'worker-git.bin',verifier=f.verifier,checkpoint=self.checkpoint)
        f.receipt();self.retype('status',b'');self.writer.append(0)
        self.assertEqual(self.saved().read(0)['raw']['stdout.bin'],b'')

    def test_source_blob_raw_pin_and_close_witness_are_preserved(self):
        f=self.fixture;stdout=b'invented source bytes\n';source='src/fixture-source.py'
        f.inventory['calls'][0].update(operation='source_blob',source_path=source,
            expected_output_pin=tree.observed._pin(stdout));f.configure()
        self.writer=archive.WorkerGitArchive(path=f.measured/'worker-git.bin',verifier=f.verifier,checkpoint=self.checkpoint)
        f.receipt();self.retype('source_blob',stdout,source);self.writer.append(0)
        self.assertEqual(self.saved().read(0),f.packets[0])

    def test_failed_receipt_is_saved_but_forbids_later_call(self):
        f=self.configure(calls=2);f.receipt(code=17);self.writer.append(0)
        self.assertEqual(self.saved().statuses,['failed'])
        before=self.writer.path.read_bytes()
        with self.assertRaises(ValueError):self.writer.append(1)
        self.assertEqual(self.writer.path.read_bytes(),before)

    def test_exact_recovery_partial_raw_roundtrip_keeps_original_owner_until_adapter(self):
        f=self.configure();f.child.begin_job();keeper,kernel=f.recovery()
        original=copy.deepcopy(f.packets[0]);self.writer.append(0);saved=self.saved()
        self.assertEqual(saved.read(0),original);self.assertIs(f.child.owners[0],keeper.original)
        self.assertEqual(f.child.active,{0});self.assertEqual(kernel.CloseHandle.call_count,4)
        adapter=proof.VerifiedLeases(child=f.child,verifier=saved.verifier)
        adapter.finish(0,keeper=keeper);self.assertEqual(f.child.finished,1)
        self.assertIs(adapter.kept[0],keeper);self.assertEqual(f.packets[0],original)

    def test_partial_append_keeps_pending_packet_and_poisoned_writer_without_retry(self):
        f=self.configure();f.receipt();original=copy.deepcopy(f.packets[0]);failure=OSError('invented partial write')
        def partial(path,frame):
            with path.open('ab') as stream:stream.write(frame[:len(frame)//2])
            raise failure
        with patch.object(archive,'_append_frame',side_effect=partial):
            with self.assertRaises(OSError):self.writer.append(0)
        partial_raw=self.writer.path.read_bytes();pending=self.writer.pending
        self.assertTrue(partial_raw);self.assertEqual(pending['packet'],original)
        with self.assertRaises(ValueError):self.writer.append(0)
        self.assertIs(self.writer.pending,pending);self.assertEqual(self.writer.path.read_bytes(),partial_raw)
        with self.assertRaises(ValueError):self.writer.manifest()

    def test_readback_interruption_keeps_complete_bytes_pending_and_source_raw(self):
        f=self.configure();target=f.receipt();failure=KeyboardInterrupt('invented readback interruption')
        with patch.object(archive.SavedWorkerGitArchive,'_current',side_effect=failure):
            with self.assertRaises(KeyboardInterrupt):self.writer.append(0)
        self.assertTrue(self.writer.failed);self.assertTrue(self.writer.path.read_bytes())
        self.assertEqual(self.writer.pending['packet'],f.packets[0]);self.assertTrue((target/'stdout.bin').exists())

    def test_corrupted_or_missing_close_link_rejects_before_any_frame_write(self):
        f=self.configure();f.receipt();f.packets[0]['event']['closed']['closed_handles']['job']=False
        with self.assertRaises(ValueError):self.writer.append(0)
        self.assertEqual(self.writer.path.read_bytes(),b'');self.assertTrue(self.writer.failed)

    def test_archived_bytes_change_is_detected_even_by_exposed_verifier(self):
        f=self.configure();f.receipt();self.writer.append(0);saved=self.saved()
        self.writer.path.write_bytes(self.writer.path.read_bytes()+b'trailing')
        with self.assertRaises(ValueError):saved.read(0)
        with self.assertRaises(ValueError):saved.verifier.record(0)

    def test_external_manifest_pin_and_added_permission_are_rejected(self):
        f=self.configure();f.receipt();self.writer.append(0);raw,pin=self.writer.manifest()
        with self.assertRaises(ValueError):self.saved(manifest=(raw,{'bytes':1,'sha256':'b'*64}))
        value=tree.v.strict_json(raw);value['formal_permission']=True;changed=tree.io.json_bytes(value)
        with self.assertRaises(ValueError):self.saved(manifest=(changed,tree.observed._pin(changed)))

    def test_frame_reorder_or_trailing_coverage_is_rejected_with_self_consistent_raw_pin(self):
        f=self.configure();f.receipt();self.writer.append(0);raw,_=self.writer.manifest()
        value=tree.v.strict_json(raw);value['rows'][0]['offset']=1;changed=tree.io.json_bytes(value)
        with self.assertRaises(ValueError):self.saved(manifest=(changed,tree.observed._pin(changed)))
        self.writer.path.write_bytes(self.writer.raw+b'trailing')
        value=tree.v.strict_json(raw);value['archive_pin']=tree.observed._pin(self.writer.path.read_bytes())
        changed=tree.io.json_bytes(value)
        with self.assertRaises(ValueError):self.saved(manifest=(changed,tree.observed._pin(changed)))

    def test_bounded_gzip_expansion_rejects_malicious_record_without_process_api(self):
        f=self.configure();f.receipt();self.writer.append(0);raw,_=self.writer.manifest()
        compressed=gzip.compress(b'x'*(archive.MAX_RAW+1),mtime=0)
        frame=archive.MAGIC+len(compressed).to_bytes(4,'big')+compressed;self.writer.path.write_bytes(frame)
        value=tree.v.strict_json(raw);value['archive_pin']=tree.observed._pin(frame)
        value['rows'][0].update(tree.observed._pin(frame));changed=tree.io.json_bytes(value)
        with self.assertRaises(ValueError):self.saved(manifest=(changed,tree.observed._pin(changed)))

    def test_existing_file_wrong_path_and_wider_stdout_plan_refuse_creation(self):
        f=self.configure()
        with self.assertRaises(ValueError):archive.WorkerGitArchive(path=self.writer.path,
            verifier=f.verifier,checkpoint=self.checkpoint)
        with self.assertRaises(ValueError):archive.WorkerGitArchive(path=f.root/'worker-git.bin',
            verifier=f.verifier,checkpoint=self.checkpoint)
        f.inventory['calls'][0]['operation']='source_blob';f.inventory['calls'][0]['source_path']='src/fixture.py'
        f.inventory['calls'][0]['expected_output_pin']=tree.observed._pin(b'x')
        f.inventory['calls'][0]['raw_inventory']['stdout.bin']=archive.bounds.MAX_STDOUT+1;f.configure()
        path=f.measured/'other'/'worker-git.bin';path.parent.mkdir()
        with self.assertRaises(ValueError):archive.WorkerGitArchive(path=path,verifier=f.verifier,checkpoint=self.checkpoint)
        self.assertFalse(path.exists())

    def test_checkpoint_stop_preserves_pending_and_denies_later_append(self):
        f=self.configure();f.receipt();failure=KeyboardInterrupt('invented shared checkpoint stop')
        self.checkpoint.side_effect=failure
        with self.assertRaises(KeyboardInterrupt):self.writer.append(0)
        self.assertTrue(self.writer.failed);self.assertEqual(self.writer.pending,{'lease':0})
        self.assertEqual(self.writer.path.read_bytes(),b'')

    def test_duplicate_original_identity_in_later_frame_is_rejected_and_retained(self):
        f=self.configure(calls=2);f.receipt();self.writer.append(0);f.receipt(1)
        with self.assertRaises(ValueError):self.writer.append(1)
        self.assertTrue(self.writer.failed);self.assertEqual(len(self.writer.rows),1)
        self.assertEqual(self.writer.pending['packet'],f.packets[1])
        self.assertGreater(len(self.writer.path.read_bytes()),len(self.writer.raw))
