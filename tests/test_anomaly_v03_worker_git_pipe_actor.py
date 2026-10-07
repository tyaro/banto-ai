"""Pipe actor invocation with fake native APIs and real channel/archive/raw files."""
import copy
import os
from types import SimpleNamespace
from unittest.mock import Mock, patch
import unittest

from banto_ai import anomaly_v03_preformal_worker_git_actor as actors
from banto_ai import anomaly_v03_preformal_worker_git_terminal as terminal
from tests import test_anomaly_v03_git_pipe_receipt_publisher as pipes
from tests import test_anomaly_v03_worker_git_proof as channels

git, keepers = actors.tree, actors.keepers


class WorkerGitPipeActorTests(unittest.TestCase):
    def setUp(self):
        self.g = pipes.GitPipeReceiptPublisherTests()
        self.g.setUp(); self.addCleanup(self.g.doCleanups)
        self.f = channels.WorkerGitProofTests()
        self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.enterContext(patch.object(git, 'os', SimpleNamespace(
            name='nt', devnull=os.devnull, fstat=os.fstat, fsync=os.fsync)))
        self.checkpoint = Mock(return_value=None)
        self.actor = None
        self.addCleanup(self.clean_fake_files)
        self.enterContext(patch.object(git.direct, '_policy', return_value=(
            self.f.root, self.f.root/'git.exe', {'PATH':'fixture'}, self.f.observation)))
        self.enterContext(patch.object(git.dependencies, 'file_observation', return_value=self.f.observation))
        self.created = 110
        def creation(_):
            self.created += 1
            return channels.identity(44, self.created)
        self.enterContext(patch.object(keepers, '_creation', side_effect=creation))

    def clean_fake_files(self):
        # Only test-created Python files; native handles are entirely fake here.
        pending = self.actor.pending if self.actor is not None else None
        transport = None if pending is None else pending.get('transport')
        if transport is not None:
            streams = list(transport.admission.streams.values()) + [transport.publication_stream]
            for stream in streams:
                if stream is not None and not stream.closed:
                    getattr(stream, 'raw', stream).close()

    def configure(self, count=1, **changes):
        f = self.f
        f.inventory['calls'] = [dict(lease=n, phase='pre' if n == 0 else 'post',
            operation='source_blob', source_path='src/banto_ai/anomaly_v03.py',
            expected_output_pin=git.observed._pin(b'abc'),
            raw_inventory={'receipt.json':16384,'stdout.bin':32,'stderr.bin':16}) for n in range(count)]
        f.configure()
        st = f.measured.stat()
        self.descriptor = {'kernel':self.g.kernel,'stdin':self.g.stdin,'clock':self.g.clock,
                           'root_identity':(st.st_dev,st.st_ino)}
        self.descriptor.update(changes)
        self.actor = actors.WorkerGitActor(child=f.child,
            inventory_raw=git.io.json_bytes(f.inventory), inventory_pin=f.verifier.inventory_pin,
            checkpoint=self.checkpoint, pipe_io=self.descriptor)
        return self.actor

    def call(self, n=0):
        call = self.actor.verifier.inventory['calls'][n]
        return self.actor.call(**{key:call[key] for key in (
            'phase','operation','source_path','expected_output_pin')})

    def fault_publisher_close(self):
        original = git.file_io.FileIO; failure = KeyboardInterrupt('publisher close')
        class Unknown:
            def __init__(self, path, mode): self.raw = original(path, mode)
            def __getattr__(self, name): return getattr(self.raw, name)
            def close(self): self.raw.close(); raise failure
        publish = git.GitPipeTransport.publish_receipt
        def injected(transport):
            with patch.object(git.file_io, 'FileIO', Unknown): return publish(transport)
        return failure, injected

    def test_original_pipe_receipt_archive_readback_precedes_exact_lease_and_cleanup(self):
        a = self.configure()
        with patch.object(git, 'run_owned', side_effect=AssertionError('no bare fallback')):
            self.assertEqual(self.call(), b'abc')
        self.assertEqual(a.saved.statuses, ['verified']); self.assertEqual(self.f.child.finished, 1)
        self.assertEqual(a.saved.read(0)['event']['format'], git.PIPE_QUIESCENCE)
        self.assertFalse(self.f.child.stopped); self.assertFalse(a.inflight.exists())
        self.assertEqual(self.f.child.owners, {}); self.g.wait.assert_not_called()
        self.assertFalse((self.f.child.root/'ack.json').exists())

    def test_second_normal_call_uses_new_original_identity_without_terminal_stop_latch(self):
        a = self.configure(2); self.assertEqual(self.call(), b'abc')
        pairs = iter([(84,114),(85,115)])
        def create(read, write, *_):
            read._obj.value, write._obj.value = next(pairs); return 1
        self.g.kernel.CreatePipe.side_effect = create
        self.g.data.update({84:b'abc',85:b''})
        self.assertEqual(self.call(1), b'abc')
        self.assertEqual(self.f.child.finished, 2); self.assertEqual(a.saved.statuses, ['verified']*2)
        self.assertNotEqual(a.saved.read(0)['event']['process_identity'],
                            a.saved.read(1)['event']['process_identity'])
        self.assertEqual(self.g.kernel.CreateProcessW.call_count, 2); self.g.wait.assert_not_called()

    def test_semantic_failed_receipt_preserves_failed_prefix_and_rejects_next_job(self):
        a = self.configure(2); self.g.data[74] = b'abd'
        with self.assertRaises(git.owner.resources.ResourceStop): self.call()
        self.assertEqual(a.saved.statuses, ['failed']); self.assertEqual(self.f.child.finished, 1)
        self.assertEqual(a._read_original(0)['raw']['stdout.bin'], b'abd')
        self.assertEqual(a.saved.read(0), a._read_original(0))
        with self.assertRaises(ValueError): self.call(1)
        self.assertEqual(self.g.kernel.CreateProcessW.call_count, 1)

    def test_unknown_publisher_close_keeps_exact_cached_keeper_and_pending_owner(self):
        a = self.configure(); failure, inject = self.fault_publisher_close()
        with patch.object(self.f.child, 'hold_owner', wraps=self.f.child.hold_owner) as ledger, \
             patch.object(git.GitPipeTransport, 'publish_receipt', inject), \
             self.assertRaises(git.owner.UnreapedJob) as caught: self.call()
        t = a.pending['transport']; original = caught.exception
        self.assertIs(a.keeper, t.keeper); self.assertIs(a.keeper, original.child_keeper)
        self.assertIs(a.critical, original); self.assertIs(t.error, failure); ledger.assert_called_once()
        self.assertIs(original.pending_pipe_receipt_owner, t); self.assertIsNone(a.keeper.reconcile_once())
        self.assertIsNotNone(a.keeper.completion); self.assertEqual(self.f.child.finished, 0)
        self.assertTrue(t.publication_stream.closed); self.assertTrue((a.inflight/'receipt.json').exists())
        self.assertEqual(a.writer.path.stat().st_size, 0)

    def test_read_interrupt_keeps_original_buffer_keeper_and_refuses_native_replay(self):
        a = self.configure(); failure = KeyboardInterrupt('ReadFile')
        self.g.kernel.ReadFile.side_effect = failure
        with self.assertRaises(git.owner.UnreapedJob) as caught: self.call()
        t = a.pending['transport']; self.assertIs(a.critical, caught.exception)
        self.assertIs(a.keeper, t.keeper); self.assertIs(t.reader.failure, failure)
        self.assertIsNotNone(t.output.pending['buffer']); self.g.wait.assert_called_once()
        with self.assertRaises(ValueError): self.call()
        self.g.kernel.ReadFile.assert_called_once(); self.assertEqual(self.f.child.active, {0})

    def test_caller_sleep_interrupt_stops_original_job_and_keeps_same_io_owner(self):
        a = self.configure(); failure = KeyboardInterrupt('caller sleep')
        with patch.object(actors.time, 'sleep', side_effect=failure), \
             self.assertRaises(git.owner.UnreapedJob): self.call()
        t = a.pending['transport']; self.assertIs(t.error, failure); self.assertIs(a.keeper, t.keeper)
        self.assertIs(self.f.child.owners[0], t.native); self.g.wait.assert_called_once()
        self.assertFalse(t.admission.streams['stdout'].closed)

    def test_archive_failure_after_verified_receipt_retains_raw_and_does_not_finish(self):
        a = self.configure(); failure = OSError('partial archive')
        def partial(path, frame): path.write_bytes(frame[:9]); raise failure
        with patch.object(actors.archive, '_append_frame', side_effect=partial), \
             self.assertRaises(OSError): self.call()
        self.assertIs(a.error, failure); self.assertEqual(self.f.child.finished, 0)
        self.assertEqual(a.writer.path.stat().st_size, 9); self.assertTrue((a.inflight/'receipt.json').exists())
        self.assertIsNone(a.pending['transport'].native.pending_pipe_receipt_owner)

    def test_wrong_original_root_identity_keeps_bootstrap_and_refuses_job_before_io(self):
        a = self.configure(root_identity=(0,0))
        with self.assertRaises(git.owner.UnreapedJob) as caught: self.call()
        self.assertIs(a.critical, caught.exception); self.assertIsNone(a.critical.job)
        self.assertIs(a.critical.git_sink_admission.bootstrap, a.critical)
        self.g.kernel.CreatePipe.assert_not_called(); self.g.kernel.CreateProcessW.assert_not_called()
        self.assertFalse(a.inflight.exists()); self.assertEqual(self.f.child.finished, 0)

    def test_pipe_descriptor_snapshot_keeps_original_io_after_caller_dictionary_changes(self):
        a = self.configure(); held = dict(self.descriptor); self.descriptor.clear()
        self.assertEqual(self.call(), b'abc'); self.assertIs(a.pipe_io['kernel'], held['kernel'])
        self.assertIs(a.pipe_io['clock'], held['clock']); self.assertEqual(a.pipe_io['root_identity'], held['root_identity'])

    def test_terminal_retention_runs_before_ack_or_reporting_for_pending_publisher_io(self):
        a = self.configure(); _, inject = self.fault_publisher_close(); sentinel = RuntimeError('test stops retention')
        with patch.object(git.GitPipeTransport, 'publish_receipt', inject), \
             patch.object(terminal.ActorTerminal, 'retain_owner', side_effect=sentinel) as retain, \
             patch.object(terminal.ActorTerminal, 'acknowledge') as ack, \
             self.assertRaises(RuntimeError) as caught:
            terminal.run_guarded(a, self.call)
        self.assertIs(caught.exception, sentinel); retain.assert_called_once(); ack.assert_not_called()
        self.assertIs(a.terminal_guard.original_error, a.critical)
        self.assertIs(a.keeper, a.pending['transport'].keeper); self.assertEqual(self.f.child.finished, 0)


if __name__ == '__main__': unittest.main()
