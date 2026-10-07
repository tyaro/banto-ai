"""Proof-linked archive transfer with fake executor/Kernel, no native trial."""
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_preformal_reader_git_worker as worker
from tests import test_anomaly_v03_worker_git_actor as fixtures

tree, terminal, channel = worker.tree, worker.terminal, worker.channel


class ReaderGitArchiveProofTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.WorkerGitActorTests('test_exact_private_job_arguments_shared_probe_raw_archive_then_lease_and_cleanup')
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.f=self.fixture.f

    def configure(self, calls=1):
        self.actor=self.fixture.configure(calls)
        (self.f.parent.root/'worker-inventory.json').write_bytes(self.actor.inventory_raw)
        self.checkpoint=Mock(return_value=None)
        self.verifier=worker.ReaderGitArchiveVerifier(parent=self.f.parent,
            inventory_raw=self.actor.inventory_raw,inventory_pin=self.actor.inventory_pin,
            checkpoint=self.checkpoint)
        self.f.parent.verify_quiescent=self.verifier
        return self.actor

    def call(self, code=0):
        result,target=self.fixture.receipt(code=code)
        with patch.object(tree,'run_owned',side_effect=self.fixture.executor(result,target)) as run:
            value=self.fixture.call()
        self.assertEqual(run.call_count,1)
        return value

    def guarded(self, operation):
        return terminal.run_guarded(self.actor,operation,publish_ack=worker.publish_archive_ack)

    def proof_raw(self):
        return (self.f.parent.root/'git-proof.json').read_bytes()

    def test_original_raw_linked_manifest_then_parent_fence_uses_original_popen(self):
        actor=self.configure()
        self.assertEqual(self.guarded(self.call),self.f.revision.encode()+b'\n')
        self.assertTrue(self.f.parent.fence(self.f.process))
        self.assertIs(self.f.parent.worker,self.f.process)
        self.assertIsNone(self.verifier.error);self.assertFalse(actor.inflight.exists())
        envelope=tree.v.strict_json(self.proof_raw())
        self.assertEqual(envelope['format'],worker.PROOF_FORMAT)
        self.assertEqual(envelope['manifest']['path'],str(self.f.parent.root/'git-manifest.json'))
        self.assertEqual(self.verifier.saved.read(0)['event'],actor.saved.read(0)['event'])
        self.assertLess(len(self.proof_raw()),32768);self.assertGreater(self.checkpoint.call_count,0)

    def test_confirmed_failed_prefix_grants_quiescence_and_keeps_original_failure_raw(self):
        actor=self.configure(2)
        with self.assertRaises(tree.owner.resources.ResourceStop) as caught:
            self.guarded(lambda:self.call(code=17))
        self.assertIs(caught.exception,actor.error)
        before={p.name:p.read_bytes() for p in actor.inflight.iterdir()}
        self.assertTrue(self.f.parent.fence(self.f.process))
        self.assertEqual(tree.v.strict_json(self.proof_raw())['git_proof']['terminal'],'failed')
        self.assertEqual(before,{p.name:p.read_bytes() for p in actor.inflight.iterdir()})
        self.assertIs(self.verifier.saved.manifest['formal_permission'],False)

    def test_zero_job_and_metadata_success_do_not_publish_any_archive_ack(self):
        actor=self.configure()
        with patch.object(tree,'run_owned') as run,self.assertRaises(ValueError):
            self.guarded(lambda:{'success':True,'jobs':0})
        run.assert_not_called();self.assertFalse((self.f.parent.root/'git-manifest.json').exists())
        self.assertFalse((self.f.parent.root/'ack.json').exists())
        self.assertIsNotNone(actor.terminal_guard.ack_error)

    def test_successful_partial_prefix_preserves_body_error_and_refuses_manifest(self):
        actor=self.configure(2);failure=ValueError('invented body stop before post call')
        def operation():self.call();raise failure
        with self.assertRaises(ValueError) as caught:self.guarded(operation)
        self.assertIs(caught.exception,failure);self.assertEqual(actor.child.finished,1)
        self.assertFalse((self.f.parent.root/'git-manifest.json').exists())
        self.assertFalse(self.f.parent.fence(self.f.process))

    def test_partial_manifest_io_preserves_packet_and_original_archive_without_republication(self):
        actor=self.configure();failure=OSError('invented partial manifest IO');write=channel._write
        def partial(path,value):
            if path.name=='git-manifest.json':
                (path.parent/'git-manifest.json.pending').write_bytes(b'{partial manifest');raise failure
            return write(path,value)
        with patch.object(channel,'_write',side_effect=partial) as calls,self.assertRaises(OSError) as caught:
            self.guarded(self.call)
        self.assertIs(caught.exception,failure);self.assertIs(actor.reader_publication['error'],failure)
        before=actor.writer.path.read_bytes();manifest,pin=actor.writer.manifest()
        with patch.object(channel,'_write') as retry,self.assertRaises(ValueError):
            worker.publish_archive_ack(actor,manifest,pin)
        retry.assert_not_called();self.assertEqual(sum(c.args[0].name=='git-manifest.json' for c in calls.call_args_list),1)
        self.assertEqual(actor.writer.path.read_bytes(),before)
        self.assertEqual((self.f.parent.root/'git-manifest.json.pending').read_bytes(),b'{partial manifest')
        self.assertFalse((self.f.parent.root/'ack.json').exists())

    def test_proof_publication_interruption_retains_manifest_and_pending_proof(self):
        actor=self.configure();failure=KeyboardInterrupt('invented proof interruption');write=channel._write
        def partial(path,value):
            if path.name=='git-proof.json':
                (path.parent/'git-proof.json.pending').write_bytes(b'{partial proof');raise failure
            return write(path,value)
        with patch.object(channel,'_write',side_effect=partial),self.assertRaises(KeyboardInterrupt) as caught:
            self.guarded(self.call)
        self.assertIs(caught.exception,failure);self.assertIs(actor.leases.error,failure)
        self.assertTrue((self.f.parent.root/'git-manifest.json').exists())
        self.assertTrue(actor.reader_publication['proof_raw']);self.assertFalse((self.f.parent.root/'ack.json').exists())

    def test_ack_io_failure_keeps_original_business_error_and_saved_raw(self):
        actor=self.configure();body=ValueError('invented body error after full Git');failure=OSError('invented ack IO')
        def operation():self.call();raise body
        write=channel._write
        def partial(path,value):
            if path.name=='ack.json':
                (path.parent/'ack.json.pending').write_bytes(b'{partial ack');raise failure
            return write(path,value)
        with patch.object(channel,'_write',side_effect=partial),self.assertRaises(ValueError) as caught:
            self.guarded(operation)
        self.assertIs(caught.exception,body);self.assertIs(actor.terminal_guard.ack_error,failure)
        self.assertIs(actor.reader_publication['error'],failure);self.assertTrue(actor.writer.path.exists())
        self.assertFalse((self.f.parent.root/'ack.json').exists())

    def test_changed_archive_after_ack_denies_parent_without_new_executor_or_owner_loss(self):
        actor=self.configure();self.guarded(self.call)
        original=actor.writer.path.read_bytes();actor.writer.path.write_bytes(original[:-1]+bytes([original[-1]^1]))
        with patch.object(tree,'run_owned') as run,self.assertRaises(ValueError):self.f.parent.fence(self.f.process)
        run.assert_not_called();self.assertIs(self.f.parent.worker,self.f.process)
        self.assertIsNotNone(self.verifier.error);self.assertEqual(actor.writer.path.read_bytes()[-1],original[-1]^1)

    def test_changed_manifest_after_ack_denies_parent_with_original_manifest_pin_retained(self):
        self.configure();self.guarded(self.call)
        path=self.f.parent.root/'git-manifest.json';path.write_bytes(b'{}\n')
        with self.assertRaises(ValueError):self.f.parent.fence(self.f.process)
        self.assertEqual(self.verifier.pending['manifest_raw'],b'{}\n')
        self.assertEqual(self.verifier.pending['manifest_pin'],tree.v.strict_json(self.proof_raw())['manifest']['pin'])
        self.assertIs(self.f.parent.worker,self.f.process)

    def test_changed_caller_inventory_file_is_rejected_before_archive_resolver(self):
        self.configure();self.guarded(self.call)
        (self.f.parent.root/'worker-inventory.json').write_bytes(b'{}\n')
        with patch.object(worker.actors.archive,'SavedWorkerGitArchive') as resolver,self.assertRaises(ValueError):
            self.f.parent.fence(self.f.process)
        resolver.assert_not_called();self.assertIs(self.f.parent.worker,self.f.process)

    def test_external_manifest_path_and_zero_finished_count_cannot_authorize_ack(self):
        self.configure();self.guarded(self.call)
        envelope=tree.v.strict_json(self.proof_raw());envelope['manifest']['path']=str(self.f.measured/'outside.json')
        with self.assertRaises(ValueError):self.verifier(tree.io.json_bytes(envelope),1)
        failure=self.verifier.error
        with patch.object(worker.observed,'_file') as read,self.assertRaises(ValueError) as caught:
            self.verifier(self.proof_raw(),0)
        self.assertIs(caught.exception,failure);read.assert_not_called()

    def test_shared_checkpoint_io_latches_original_error_and_preserves_popen(self):
        self.configure();self.guarded(self.call);failure=OSError('invented shared budget IO')
        self.checkpoint.side_effect=failure
        with self.assertRaises(OSError) as caught:self.f.parent.fence(self.f.process)
        self.assertIs(caught.exception,failure);self.assertIs(self.verifier.error,failure)
        self.assertIs(self.f.parent.worker,self.f.process)
        with patch.object(worker.observed,'_file') as read,self.assertRaises(OSError) as held:
            self.verifier(b'{}',1)
        self.assertIs(held.exception,failure);read.assert_not_called()
