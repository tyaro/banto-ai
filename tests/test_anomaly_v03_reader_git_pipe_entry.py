"""Borrowed IO entry bridge only: no process, pipe or dataset observation."""
import contextlib
import copy
import io
from pathlib import Path
from unittest.mock import Mock, patch
import unittest

from banto_ai import anomaly_v03_preformal_reader_git_worker as worker
from banto_ai import anomaly_v03_preformal_owned_saved_attempt as copied
from tests import test_anomaly_v03_reader_git_worker as fixtures


class ReaderGitPipeEntryTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.ReaderGitWorkerTests()
        self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.kernel, self.stdin = Mock(name='borrowed kernel'), Mock(name='borrowed stdin')
        self.descriptor = {'kernel':self.kernel,'stdin':self.stdin}

    def create(self, **changes):
        entry = self.f.prepare()
        return worker.ReaderGitWorker(entry, revision=self.f.f.revision,
            repository=self.f.f.root, names=self.f.names, pipe_io=changes.get('pipe_io',self.descriptor))

    def test_exact_io_uses_same_checkpoint_clock_and_external_root_identity_without_native(self):
        child = self.create(); actor = child.actor
        self.assertIs(actor.pipe_io['kernel'], self.kernel); self.assertIs(actor.pipe_io['stdin'], self.stdin)
        self.assertIs(actor.pipe_io['clock'], child.clock)
        self.assertEqual(actor.pipe_io['root_identity'], tuple(self.f.entry['budget_root_identity']))
        self.assertEqual(actor.writer.path, self.f.f.measured/'worker-git.bin')
        self.assertEqual(actor.writer.path.read_bytes(), b''); self.assertEqual(child.child.active,set())
        self.kernel.CreatePipe.assert_not_called(); self.kernel.CreateProcessW.assert_not_called()
        self.stdin.close.assert_not_called()

    def test_descriptor_mutation_does_not_replace_original_resources_or_shared_clock(self):
        child = self.create(); clock = child.clock; self.descriptor.clear()
        with patch.object(worker.time, 'monotonic', return_value=999999): child.checkpoint()
        self.assertIs(child.clock, clock); self.assertIs(child.actor.pipe_io['clock'], clock)
        self.assertIs(child.pipe_io['kernel'], self.kernel); self.stdin.close.assert_not_called()

    def test_foreign_clock_or_root_fields_deny_before_child_or_archive_creation(self):
        entry = self.f.prepare(); rejected = {**self.descriptor,'clock':lambda:100}
        with patch.object(worker.channel, 'ChildChannel') as channel, self.assertRaises(ValueError):
            worker.ReaderGitWorker(entry, revision=self.f.f.revision, repository=self.f.f.root,
                names=self.f.names, pipe_io=rejected)
        channel.assert_not_called(); self.assertFalse((self.f.f.measured/'worker-git.bin').exists())
        self.kernel.CreatePipe.assert_not_called()

    def test_json_entry_cannot_inject_native_io_or_change_exact_entry_fields(self):
        entry = copy.deepcopy(self.f.prepare()); entry['pipe_io']={'kernel':'declared'}
        with patch.object(worker.channel,'ChildChannel') as channel, self.assertRaises(ValueError):
            worker.ReaderGitWorker(entry,revision=self.f.f.revision,repository=self.f.f.root,
                names=self.f.names,pipe_io=self.descriptor)
        channel.assert_not_called(); self.assertFalse((self.f.f.measured/'worker-git.bin').exists())

    def test_reader_cli_forwards_snapshot_before_observation_and_guarded_data_callback(self):
        _, argv = self.f.invocation(); self.f.fake_worker()
        original = copied.observed._file
        def read(path, maximum):
            raw = original(path, maximum)
            if path == Path(argv[0]): self.descriptor.clear()
            return raw
        with patch.object(copied.observed, '_file', side_effect=read), \
             patch.object(copied, '_read_attempt', return_value={'formal_permission':False}) as read_data, \
             contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(copied.reader_worker_main(argv, pipe_io=self.descriptor),0)
        options = worker.ReaderGitWorker.call_args.kwargs
        self.assertIs(options['pipe_io']['kernel'],self.kernel); self.assertIs(options['pipe_io']['stdin'],self.stdin)
        self.assertEqual(self.descriptor,{}); self.assertEqual(self.f.events,['guard','profile'])
        self.assertIs(read_data.call_args.kwargs['git_blob'],self.f.fake.blob)
        self.assertIn('runtime_observation',out.getvalue()); self.stdin.close.assert_not_called()

    def test_pipe_io_without_worker_entry_rejects_before_data_or_native_work(self):
        _, argv = self.f.invocation(entry=False,profile=False)
        with patch.object(worker,'ReaderGitWorker') as constructor, \
             patch.object(copied,'_read_attempt') as read, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(copied.reader_worker_main(argv,pipe_io=self.descriptor),2)
        constructor.assert_not_called(); read.assert_not_called(); self.kernel.CreatePipe.assert_not_called()

    def test_pipe_io_requires_fresh_profile_before_child_or_callback_work(self):
        _, argv = self.f.invocation(profile=False)
        with patch.object(worker,'ReaderGitWorker') as constructor, \
             patch.object(copied,'_read_attempt') as read, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(copied.reader_worker_main(argv,pipe_io=self.descriptor),2)
        constructor.assert_not_called(); read.assert_not_called(); self.stdin.close.assert_not_called()

    def test_native_parent_still_refuses_before_any_root_channel_or_kernel_issuance(self):
        with patch.object(worker.ReaderGitParent,'create') as create, \
             patch.object(worker.channel.ParentChannel,'create') as channel, \
             self.assertRaises(worker.monitor.resources.ResourceStop):
            worker.ReaderGitParent.create_native(pipe_io=self.descriptor)
        create.assert_not_called(); channel.assert_not_called(); self.kernel.CreatePipe.assert_not_called()


if __name__ == '__main__': unittest.main()
