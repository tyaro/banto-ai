"""Separate IO owner retention and deferred core close: protocol stubs only."""
import io
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_preformal_owned_git_job as git
from banto_ai import anomaly_v03_preformal_child_git_keeper as keepers


class GitOutputOwnerTests(unittest.TestCase):
    def native(self):
        return git.owner.UnreapedJob(11,22,33,{}, {'inherited_0':61,'inherited_1':62,'inherited_2':63})

    def spools(self):
        return {name:git.BoundedGitSpool(io.BytesIO(),operation='source_blob',output=name,
            maximum_stored_bytes=64,checkpoint=lambda:None,sync=lambda:None)
            for name in ('stdout','stderr')}

    def held(self, native=None, *, checkpoint=None):
        return git.GitOutputOwner(native if native is not None else self.native(),
            read_handles={'stdout':44,'stderr':55},spools=self.spools(),
            checkpoint=checkpoint if checkpoint is not None else lambda:None)

    def test_original_native_io_and_block_are_retained_before_consumer_io(self):
        native=self.native();held=self.held(native)
        self.assertIs(native.git_output_owner,held)
        self.assertEqual(native.extra_handles,{'inherited_0':61,'inherited_1':62,'inherited_2':63})
        self.assertEqual(held.begin_read('stdout'),(44,64))
        raw=b'abc';packet=held.retain_read(raw)
        self.assertIs(packet['raw'],raw)
        self.assertIs(packet['spool'],held.spools['stdout'])
        self.assertEqual(packet['spool'].stream.getvalue(),b'')

    def test_invalid_native_input_still_retains_all_io_inputs(self):
        handles={'stdout':44,'stderr':55};spools=self.spools();native={'closed':True}
        with self.assertRaises(git.GitOutputOwnerFailure) as raised:
            git.GitOutputOwner(native,read_handles=handles,spools=spools,checkpoint=lambda:None)
        self.assertIs(raised.exception.output_owner.native_owner,native)
        self.assertIs(raised.exception.output_owner.original_read_handles,handles)
        self.assertIs(raised.exception.output_owner.original_spools,spools)

    def test_aliasing_core_handle_is_rejected_without_losing_native_owner(self):
        native=self.native();handles={'stdout':11,'stderr':55}
        with self.assertRaises(git.owner.UnreapedJob) as raised:
            git.GitOutputOwner(native,read_handles=handles,spools=self.spools(),checkpoint=lambda:None)
        self.assertIs(raised.exception,native)
        self.assertIs(native.git_output_owner.original_read_handles,handles)
        self.assertIsNotNone(native.git_output_error)

    def test_shared_clock_interrupt_preserves_pending_handle_and_spool(self):
        native=self.native();error=KeyboardInterrupt();held=self.held(native,checkpoint=Mock(side_effect=error))
        with self.assertRaises(git.owner.UnreapedJob) as raised:held.begin_read('stdout')
        self.assertIs(raised.exception,native);self.assertIs(held.error,error)
        self.assertEqual(held.pending['handle'],44)
        self.assertIs(held.pending['spool'],held.spools['stdout'])

    def test_overread_preserves_original_raw_and_rejects_more_work(self):
        native=self.native();held=self.held(native);held.begin_read('stdout');raw=b'x'*65
        with self.assertRaises(git.owner.UnreapedJob):held.retain_read(raw)
        self.assertIs(held.pending['raw'],raw)
        with self.assertRaises(git.owner.UnreapedJob) as raised:held.begin_read('stderr')
        self.assertIs(raised.exception,native);self.assertIs(held.pending['raw'],raw)

    def test_second_read_does_not_overwrite_pending_original_block(self):
        held=self.held();held.begin_read('stdout');held.retain_read(b'abc');packet=held.pending
        with self.assertRaises(git.owner.UnreapedJob):held.begin_read('stderr')
        self.assertIs(held.pending,packet);self.assertEqual(packet['raw'],b'abc')

    def test_duplicate_binding_retains_both_io_owners(self):
        native=self.native();first=self.held(native)
        with self.assertRaises(git.owner.UnreapedJob) as raised:self.held(native)
        self.assertIs(raised.exception,native)
        self.assertIs(native.git_output_owner.previous_owner,first)

    def test_root_exit_and_release_metadata_cannot_close_core_or_repeat_native_reap(self):
        native=self.native();held=self.held(native);held.released=True;held.eof=True
        child=SimpleNamespace(stopped=False,hold_owner=Mock())
        keeper=keepers.ChildGitKeeper(native,child=child,lease=0)
        identity={'pid':77,'creation_time_100ns':1000}
        identity['start_token']=git.v.canonical_sha256(identity)
        kernel=SimpleNamespace(TerminateJobObject=Mock(return_value=True))
        with patch.object(git.owner,'_kernel',return_value=kernel), \
             patch.object(git.owner,'_wait_empty',return_value=({'total_processes':1,'active_processes':0,'limit_terminated_processes':1},0)) as wait, \
             patch.object(keepers,'_creation',return_value=identity) as creation, \
             patch.object(git.owner,'_close_handles') as close:
            self.assertIsNone(keeper.reconcile_once())
            native.git_output_owner=None  # Removing a marker cannot release the cached owner.
            self.assertIsNone(keeper.reconcile_once())
            kernel.TerminateJobObject.assert_called_once();wait.assert_called_once();creation.assert_called_once()
            close.assert_not_called()
        self.assertIs(keeper.output_owner,held);self.assertIsNone(keeper.completion)
        self.assertEqual(keeper.remaining,keeper.initial_handles)

    def test_unknown_core_close_keeps_separate_io_owner_without_native_retry(self):
        native=git.owner.UnclosedHandles({'job':11},{})
        held=self.held(native);keeper=keepers.ChildGitKeeper(native,child=SimpleNamespace(stopped=False,hold_owner=Mock()),lease=0)
        with patch.object(git.owner,'_kernel') as kernel:
            self.assertIsNone(keeper.reconcile_once());kernel.assert_not_called()
        self.assertIs(keeper.original.git_output_owner,held)
        self.assertFalse(held.spools['stdout'].stream.closed)

    def test_child_ledger_io_failure_reraises_original_with_both_owners_retained(self):
        native=self.native();held=self.held(native);error=OSError('ledger')
        child=SimpleNamespace(stopped=False,hold_owner=Mock(side_effect=error))
        with self.assertRaises(git.owner.UnreapedJob) as raised:keepers.ChildGitKeeper(native,child=child,lease=0)
        self.assertIs(raised.exception,native)
        self.assertIs(native.git_output_owner,held)
        self.assertIs(native.child_keeper.ledger_error,error)

    def test_rejected_caller_mapping_changes_cannot_drop_retained_handles_or_sinks(self):
        native=self.native();handles={'stdout':11,'stderr':55};spools=self.spools()
        stdout,stderr=spools['stdout'],spools['stderr']
        with self.assertRaises(git.owner.UnreapedJob):
            git.GitOutputOwner(native,read_handles=handles,spools=spools,checkpoint=lambda:None)
        held=native.git_output_owner;handles.clear();spools.clear()
        self.assertEqual(held.read_handles,{'stdout':11,'stderr':55})
        self.assertIs(held.spools['stdout'],stdout);self.assertIs(held.spools['stderr'],stderr)
