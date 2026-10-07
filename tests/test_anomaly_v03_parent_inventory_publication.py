"""Parent inventory publisher with original controller, fake budget and small files."""
import copy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_preformal_reader_git_worker as reader
from tests import test_anomaly_v03_reader_git_parent_connection as fixtures

archive, tree = reader.actors.archive, reader.tree


class ParentInventoryPublicationTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ReaderGitParentControllerTests()
        self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.controls={name:32768 for name in archive.ArchiveAppendAdmission.CONTROL_NAMES}
        self.limits={operation:{'receipt.json':16384,'stdout.bin':maximum,'stderr.bin':16384,
            'partial-archive.bin':65536} for operation,maximum in
            (('head',128),('status',65536),('source_blob',131072))}

    def create(self):return self.f.create(pipe_raw_limits=self.limits,append_control_limits=self.controls)

    def injection(self, *, unknown_close=False):
        factory=tree.file_io.FileIO;made=[]
        failure=KeyboardInterrupt('fixture unknown inventory close') if unknown_close else OSError('fixture inventory partial write')
        class Wrapped:
            def __init__(self,path,mode):self.raw=factory(path,mode);made.append(self)
            def __getattr__(self,name):return getattr(self.raw,name)
            def write(self,raw):
                if not unknown_close:self.raw.write(raw[:11]);raise failure
                return self.raw.write(raw)
            def close(self):
                value=self.raw.close()
                if unknown_close:raise failure
                return value
        def cleanup():
            for stream in made:
                if not stream.raw.closed:stream.raw.close()  # This test's Python files only, never native recovery.
        self.addCleanup(cleanup)
        return patch.object(tree.file_io,'FileIO',Wrapped),failure,made

    def test_real_parent_sixty_four_inventory_publication_and_cached_source_bind_fence_do_not_reclose(self):
        factory=tree.file_io.FileIO
        with patch.object(tree.file_io,'FileIO',wraps=factory) as opened:
            p=self.create();gate=p.inventory_publication
            initial=gate.verification;closed=gate.completed['worker-inventory.json']['original']
            self.assertIs(gate.owner,p);self.assertIs(gate.endpoint,p.parent)
            self.assertIs(gate.checkpoint,p.inventory_checkpoint);self.assertIs(p.control_publication_owner,gate)
            raw=Path(p.entry['inventory_path']).read_bytes()
            self.assertEqual(len(reader.v.strict_json(raw)['calls']),64)
            self.assertEqual(reader.observed._pin(raw),p.entry['inventory_pin'])
            self.assertEqual(p.source()['revision'],self.f.f.revision)
            p.bind(self.f.f.process);self.assertFalse(p.fence(self.f.f.process))
            self.assertEqual(sum(Path(call.args[0]).name=='worker-inventory.json.pending'
                                 for call in opened.call_args_list),1)
            self.assertIs(gate.verification,initial);self.assertIs(gate.cached_verification['original_verification'],initial)
            self.assertIs(gate.completed['worker-inventory.json']['original'],closed)
            self.assertTrue(closed['close_return_observed']);self.assertIsNone(closed['close_return'])
            self.assertFalse(gate.completed['worker-inventory.json']['observation']['atomic_reservation'])
        self.assertIs(p.shared,self.f.shared);self.f.budget.checkpoint.assert_not_called()
        self.assertFalse((self.f.f.measured/'worker-git-inflight').exists())

    def test_parent_controls_are_copied_before_original_shared_callback_and_published_pin_stays_fixed(self):
        held=copy.deepcopy(self.controls)
        self.f.shared.require_stage.side_effect=lambda *_:self.controls.clear()
        p=self.create()
        self.assertEqual(p.append_controls,held);self.assertEqual(p.inventory_publication.control_limits,held)
        self.assertEqual(p.entry['append_plan']['value']['control_limits'],held)
        self.assertEqual(p.inventory_publication.inventory_pin,p.entry['inventory_pin'])
        self.assertEqual(p.inventory_publication.identity,tuple(p.entry['budget_root_identity']))

    def test_inventory_too_small_cap_denies_before_new_file_and_holds_original_bootstrap_controller(self):
        self.controls['worker-inventory.json']=10
        with patch.object(tree.file_io,'FileIO') as opened,self.assertRaises(ValueError) as caught:self.create()
        opened.assert_not_called();failure=caught.exception;gate=failure.control_publication_owner
        self.assertIs(failure.reader_git_parent,gate.owner);self.assertIs(gate.owner.inventory_pending_owner,gate.pending)
        self.assertIsNone(gate.pending['stream']);self.assertIsNone(gate.owner.worker)
        self.assertGreater(len(gate.pending['raw']),10)
        self.assertFalse((self.f.root/'worker-inventory.json').exists())

    def test_partial_inventory_write_keeps_stream_fd_raw_and_exact_failure_without_reopen(self):
        inject,failure,made=self.injection()
        with inject,self.assertRaises(OSError) as caught:self.create()
        self.assertIs(caught.exception,failure);p=failure.reader_git_parent;gate=p.inventory_publication
        self.assertIs(p.inventory_pending_owner,gate.pending);self.assertIs(gate.pending['stream'],made[0])
        self.assertEqual((self.f.root/'worker-inventory.json.pending').read_bytes(),gate.pending['raw'][:11])
        with patch.object(tree.file_io,'FileIO') as opened,self.assertRaises(OSError) as denied:p.source()
        self.assertIs(denied.exception,failure);opened.assert_not_called()
        self.assertIsNone(p.worker);self.assertFalse((self.f.root/'worker-inventory.json').exists())

    def test_unknown_inventory_close_keeps_closed_stream_but_denies_original_popen_bind(self):
        inject,failure,_=self.injection(unknown_close=True)
        with inject,self.assertRaises(KeyboardInterrupt) as caught:self.create()
        self.assertIs(caught.exception,failure);p=failure.reader_git_parent;gate=p.inventory_publication
        self.assertTrue(gate.pending['stream'].closed);self.assertFalse(gate.pending['close_return_observed'])
        with patch.object(p.parent,'bind') as bind,self.assertRaises(KeyboardInterrupt) as denied:p.bind(self.f.f.process)
        self.assertIs(denied.exception,failure);self.assertIs(p.worker,self.f.f.process)
        bind.assert_not_called();self.assertIsNone(p.parent.worker)
        self.assertFalse((self.f.root/'worker-inventory.json').exists())

    def test_changed_inventory_before_bind_keeps_original_and_changed_raw_without_native_identity_io(self):
        p=self.create();gate=p.inventory_publication
        original=gate.verification['raw']['worker-inventory.json']
        Path(p.entry['inventory_path']).write_bytes(b'changed inventory')
        with patch.object(p.parent,'bind') as bind,self.assertRaises(ValueError) as caught:p.bind(self.f.f.process)
        bind.assert_not_called();self.assertIs(p.worker,self.f.f.process)
        self.assertIs(p.inventory_publication_error,caught.exception)
        self.assertIs(p.inventory_pending_owner,gate.pending)
        self.assertEqual(gate.pending['raw']['worker-inventory.json'],b'changed inventory')
        self.assertNotEqual(original,b'changed inventory')
        with patch.object(p.parent,'fence') as fence,self.assertRaises(ValueError) as repeated:p.fence(self.f.f.process)
        self.assertIs(repeated.exception,caught.exception);fence.assert_not_called()

    def test_pending_inventory_owner_survives_metadata_clearing_and_cached_controller_denial(self):
        p=self.create();gate=p.inventory_publication;pending={'stream':object(),'raw':b'held pending'}
        gate.pending=pending
        with self.assertRaises(ValueError) as caught:p.source()
        self.assertIs(p.inventory_pending_owner,pending)
        gate.pending=None;gate.error=None;p.error=None
        with self.assertRaises(ValueError) as denied:p.source()
        self.assertIs(denied.exception,caught.exception);self.assertIs(p.inventory_pending_owner,pending)

    def test_foreign_sidecar_and_wrong_prepare_context_refuse_before_parent_or_publication_io(self):
        p=self.create();gate=p.inventory_publication
        controls=copy.deepcopy(self.controls);controls['ack.json']=100
        with patch.object(p.parent,'_live') as live,patch.object(gate,'publish') as publish,self.assertRaises(ValueError):
            reader.prepare_entry(p.parent,inventory_raw=gate.verification['raw']['worker-inventory.json'],
                inventory_pin=p.entry['inventory_pin'],names=self.f.names,append_control_limits=controls,
                publication_admission=gate)
        live.assert_not_called();publish.assert_not_called()
        foreign=SimpleNamespace(pending={'stream':object()},error=None);p.control_publication_owner=foreign
        with self.assertRaises(ValueError):p.source()
        self.assertIs(p.rejected_inventory_publication[0],gate);self.assertIs(p.rejected_inventory_publication[1],foreign)

    def test_original_budget_stop_during_inventory_admission_holds_raw_before_file_or_worker(self):
        self.f.budget.probe.return_value='fixture_inventory_shared_stop'
        with patch.object(tree.file_io,'FileIO') as opened,self.assertRaises(reader.monitor.resources.ResourceStop) as caught:
            self.create()
        opened.assert_not_called();failure=caught.exception;p=failure.reader_git_parent
        self.assertEqual(failure.reason,'fixture_inventory_shared_stop')
        self.assertIs(p.inventory_publication.error,failure);self.assertIsNone(p.worker)
        self.assertIs(p.shared,self.f.shared);self.assertEqual(p.clock['started_at'],100.0)
        self.assertIsNone(p.inventory_pending_owner['stream']);self.assertIsNotNone(p.inventory_pending_owner['raw'])

    def test_rejected_parent_sidecar_stays_retained_after_metadata_restore_and_latched_source_denial(self):
        p=self.create();gate=p.inventory_publication
        foreign=SimpleNamespace(pending={'stream':object(),'raw':b'original rejected owner'},error=None)
        p.control_publication_owner=foreign
        with self.assertRaises(ValueError) as caught:p.source()
        held=p.rejected_inventory_publication
        p.control_publication_owner=gate;p.error=None
        with patch.object(gate,'verify_publications') as verify,self.assertRaises(ValueError) as denied:p.source()
        self.assertIs(denied.exception,caught.exception);verify.assert_not_called()
        self.assertIs(p.rejected_inventory_publication,held);self.assertIs(held[1],foreign)


if __name__=='__main__':unittest.main()
