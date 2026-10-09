"""New storage IO risks; upstream publication stub, real small files, no native launch.

The complete nonempty request-root projection still refuses the original 32-entry
bound. This fixture isolates the new IO connection; it grants no capacity proof.
"""
import copy
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

from banto_ai import anomaly_v03_preformal_generated_chain_budget as budget
from banto_ai import anomaly_v03_preformal_reader_git_worker as reader
from tests import test_anomaly_v03_publication_storage_path as fixtures

archive=reader.actors.archive


class RequestWriterStorageConnectionTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.PublicationStoragePathTests()
        self.f.f=fixtures.children.ReaderControlPublicationTests();self.f.f.setUp();self.addCleanup(self.f.f.doCleanups)
        original=self.f.f.f.call
        def call(*args,**kwargs):
            row=original(*args,**kwargs)
            row['raw_inventory']={'receipt.json':4096,'stdout.bin':128,'stderr.bin':1024}
            return row
        self.f.f.f.call=call
        # Suppress only the fixture actor's earlier archive constructor. The new
        # original writer below uses the real constructor and real first FileIO.
        with patch.object(archive.WorkerGitArchive,'__init__',return_value=None):self.f.a=self.f.f.configure()
        self.f.gate=self.f.a.control_publication
        self.f.allocation={'format':archive.PublicationStorageAdmission.FORMAT,'frame_bytes':8192,
            'archive_bytes':65536,'carrier_failure_bytes':16384,'resident_raw_bytes':1572864,
            'parent_raw_limits':{'stdout.bin':4096,'stderr.bin':4096,'receipt.json':16384}}
        self.addCleanup(self.f.close_test_files)
        a=self.f.a
        self.storage=archive.PublicationStorageAdmission(endpoint=a.child,inventory_raw=a.inventory_raw,
            inventory_pin=a.inventory_pin,root_identity=a.pipe_io['root_identity'],allocation=self.f.allocation,
            checkpoint=a.checkpoint,owner=a)
        s=self.storage;self.owner=s.owner;self.clock=s.checkpoint
        self.writer=archive.WorkerGitArchive.__new__(archive.WorkerGitArchive)
        self.carrier=archive.PublicationCarrier.__new__(archive.PublicationCarrier)
        self.carrier.owner=self.owner;self.carrier.checkpoint=self.clock
        self.carrier.frame_limit=s.allocation['frame_bytes'];self.carrier.native=SimpleNamespace()
        self.context={'request_pin':copy.deepcopy(s.request_pin),'inventory_pin':copy.deepcopy(s.inventory_pin),
            'revision':s.request['revision'],'root':str(s.root),'root_identity':list(s.identity)}
        self.context_raw=archive.io.json_bytes(self.context)
        self.publication=budget.PartitionedPublicationPreparation.__new__(budget.PartitionedPublicationPreparation)
        self.publication.owner=self.owner;self.publication.checkpoint=self.clock
        self.publication.original_inputs=(self.owner,self.clock,None,None,None,self.context_raw,None)
        self.publication._fixed=Mock()  # Upstream only; storage snapshot and FileIO remain real.
        declaration={'format':budget.RequestWriterPreparation.FORMAT,'context_pin':archive.observed._pin(self.context_raw),
            'roles':list(budget.RequestWriterPreparation.ROLES),'formal_permission':False}
        participants=tuple(zip(budget.RequestWriterPreparation.ROLES,
            (s.gate,self.writer,self.carrier,object(),object())))
        self.preparation=budget.RequestWriterPreparation(owner=self.owner,checkpoint=self.clock,
            publication=self.publication,declaration=declaration,participants=participants)
        self.clock.reset_mock()

    def bind(self):return self.storage.bind_request_writers(self.preparation)

    def initialize_writer(self,writer=None):
        writer=self.writer if writer is None else writer
        writer.__init__(path=self.storage.root/'worker-git.bin',verifier=self.storage.verifier,
            checkpoint=self.clock,append_admission=self.owner.append_admission,storage_admission=self.storage)
        return writer

    def test_real_empty_archive_creation_follows_original_declared_claim(self):
        self.bind();factory=archive.proof.tree.file_io.FileIO;seen=[]
        def open_file(path,mode):
            if mode=='xb':
                seen.append(self.storage.request_writer_view()['claimed_io_roles'])
                self.assertIs(self.storage.writer,self.writer)
            return factory(path,mode)
        with patch.object(archive.proof.tree.file_io,'FileIO',side_effect=open_file):self.initialize_writer()
        self.assertEqual(seen,[['parent_control','worker_archive']])
        self.assertEqual(self.writer.initial_completion['readback'],b'')
        self.assertTrue(self.writer.initial_completion['close_return_observed'])
        self.assertIsNone(self.writer.initial_completion['close_return'])
        self.assertTrue(self.storage.unresolved())
        self.assertFalse(any(v for k,v in self.storage.request_writer_view().items() if k.endswith('authorized') or k in
            ('all_writers_registered','exclusive_root','atomic_reservation','capacity_pass','execution_authenticated','formal_permission')))

    def test_foreign_writer_refuses_before_file_creation_and_retains_original_candidate(self):
        self.bind();foreign=archive.WorkerGitArchive.__new__(archive.WorkerGitArchive)
        with patch.object(archive.proof.tree.file_io,'FileIO') as opened:
            with self.assertRaises(ValueError):self.initialize_writer(foreign)
        opened.assert_not_called();self.assertIs(self.storage.writer,foreign)
        self.assertIs(self.storage._PublicationStorageAdmission__request_writer_pending['incoming'][1],foreign)
        self.assertFalse((self.storage.root/'worker-git.bin').exists())

    def test_foreign_owner_refuses_before_claim_clock(self):
        self.preparation.owner=object()
        with self.assertRaises(ValueError):self.bind()
        self.clock.assert_not_called()
        self.assertIs(self.storage._PublicationStorageAdmission__request_writer_inputs[1],self.preparation)

    def test_different_original_clock_refuses_before_claim(self):
        self.preparation.checkpoint=lambda:None
        with self.assertRaises(ValueError):self.bind()
        self.clock.assert_not_called()

    def test_foreign_request_root_context_refuses_before_clock(self):
        self.storage.request['revision']='d'*40
        with self.assertRaises(ValueError):self.bind()
        self.clock.assert_not_called()

    def test_bound_carrier_claims_original_object_without_native_issue(self):
        self.bind();self.storage.bind_carrier(self.carrier)
        self.assertIs(self.carrier.native.publication_storage,self.storage)
        self.assertEqual(self.storage.request_writer_view()['claimed_io_roles'],['parent_control','worker_carrier'])
        self.assertTrue(self.storage.unresolved())

    def test_second_carrier_retained_and_refused_before_snapshot(self):
        self.bind();self.storage.bind_carrier(self.carrier)
        with patch.object(budget,'_directory_snapshot') as snapshot:
            with self.assertRaises(ValueError):self.storage.bind_carrier(self.carrier)
        snapshot.assert_not_called();self.assertEqual(self.storage.carriers,[self.carrier,self.carrier])

    def test_control_alias_erasure_refuses_before_clock_snapshot_or_file_io(self):
        self.bind();self.storage.request_writer_binding=None;self.clock.reset_mock()
        with patch.object(archive.proof.tree.file_io,'FileIO') as opened,patch.object(budget,'_directory_snapshot') as snapshot:
            with self.assertRaises(ValueError):self.storage.view('control_before')
        opened.assert_not_called();snapshot.assert_not_called();self.clock.assert_not_called()
        self.assertIs(self.storage._PublicationStorageAdmission__request_writer_anchor[1],self.owner)

    def test_callback_binding_erasure_keeps_unknown_original_return_prefix(self):
        def erase():self.storage.request_writer_binding=None
        self.clock.side_effect=erase
        with self.assertRaises(ValueError):self.bind()
        held=self.storage._PublicationStorageAdmission__request_writer_pending
        self.assertIn('result',held);self.assertEqual(held['result']['claimed_roles'],['parent_control'])
        self.assertIs(held['preparation'],self.preparation)
        self.clock.side_effect=None;self.clock.reset_mock()
        with self.assertRaises(ValueError):self.storage.request_writer_view()
        self.clock.assert_not_called()

    def test_interrupt_does_not_allow_second_connection_after_alias_reset(self):
        failure=KeyboardInterrupt('new connection claim interruption');self.clock.side_effect=failure
        with self.assertRaises(KeyboardInterrupt) as first:self.bind()
        self.assertIs(first.exception,failure)
        original=self.storage._PublicationStorageAdmission__request_writer_inputs
        self.storage.request_writer_binding=None;self.clock.side_effect=None;self.clock.reset_mock()
        with self.assertRaises(KeyboardInterrupt) as second:self.storage.bind_request_writers(object())
        self.assertIs(second.exception,failure);self.assertIs(self.storage._PublicationStorageAdmission__request_writer_inputs,original)
        self.clock.assert_not_called()

    def test_cached_connection_view_does_not_repeat_clock_or_snapshot(self):
        first=self.bind();self.clock.reset_mock()
        with patch.object(budget,'_directory_snapshot') as snapshot:
            second=self.storage.request_writer_view()
        self.assertEqual(first,second);snapshot.assert_not_called();self.clock.assert_not_called()

    def test_changed_original_return_is_not_replaced_by_new_success_metadata(self):
        self.bind();record=self.storage._PublicationStorageAdmission__request_writer_claims[0]
        record[2]['native_authorized']=True
        with self.assertRaises(ValueError):self.storage.request_writer_view()
        self.assertIs(self.storage._PublicationStorageAdmission__request_writer_claims[0],record)

    def test_parent_wrapper_rejects_child_storage_and_retains_candidate_before_getter(self):
        parent=reader.ReaderGitParent.__new__(reader.ReaderGitParent)
        parent.error=None;parent.inventory_checkpoint=self.clock;parent.inventory_publication=None
        with self.assertRaises(ValueError):parent.connect_request_writers_to_storage(self.storage)
        self.assertIs(parent.request_writer_storage_input[0],self.storage)
        self.assertIsNone(self.storage._PublicationStorageAdmission__request_writer_inputs)
        self.clock.assert_not_called()

    def test_completed_archive_is_refused_without_retroactive_claim(self):
        path=self.storage.root/'worker-git.bin';path.write_bytes(b'prior fixture bytes')
        with self.assertRaises(ValueError):self.bind()
        self.assertEqual(path.read_bytes(),b'prior fixture bytes');self.clock.assert_not_called()
        self.assertEqual(self.preparation.view()['claimed_roles'],[])

    def test_parent_private_original_candidate_survives_display_alias_erasure(self):
        parent=reader.ReaderGitParent.__new__(reader.ReaderGitParent)
        parent.error=None;parent.inventory_checkpoint=self.clock;parent.inventory_publication=None
        with self.assertRaises(ValueError) as first:parent.connect_request_writers_to_storage(self.storage)
        original=parent._ReaderGitParent__request_writer_storage_inputs
        parent.request_writer_storage_input=None
        with self.assertRaises(ValueError) as second:parent.connect_request_writers_to_storage(object())
        self.assertIs(first.exception,second.exception)
        self.assertIs(parent._ReaderGitParent__request_writer_storage_inputs,original)
        self.assertIs(original[0],self.storage);self.clock.assert_not_called()

    def test_control_view_checks_cached_claim_without_claiming_again(self):
        self.bind();original=self.preparation._claims
        self.storage.gate.pending={}  # Existing publisher's pre-IO holder, before _view.
        self.storage.gate._view('new_connection')
        self.storage.gate.pending=None
        self.assertIs(self.preparation._claims,original)
        self.assertEqual(self.storage.request_writer_view()['claimed_io_roles'],['parent_control'])

    def test_parent_original_retention_keeps_foreign_candidate_without_new_keeper(self):
        class Escape(BaseException):pass
        parent=reader.ReaderGitParent.__new__(reader.ReaderGitParent)
        parent.error=None;parent.inventory_checkpoint=self.clock;parent.inventory_publication=None
        parent.original_bootstrap_inputs=(None,)*10;parent.worker=None
        with self.assertRaises(ValueError) as failed:parent.connect_request_writers_to_storage(self.storage)
        with patch.object(reader.ParentPublicationRetention,'_pause',side_effect=Escape):
            with self.assertRaises(Escape):reader.retain_parent_publications(failed.exception,parent)
            keeper=parent.original_publication_retention
            parent.request_writer_storage_input=None
            with self.assertRaises(Escape):reader.retain_parent_publications(failed.exception,parent)
        self.assertIs(parent.original_publication_retention,keeper)
        self.assertIs(keeper.owners[-2][0],self.storage)
        self.assertIs(keeper.original_error,failed.exception)

    def test_swallowed_rebind_error_keeps_first_error_and_original_return_pending(self):
        failures=[]
        def callback():
            try:self.storage.bind_request_writers(object())
            except ValueError as error:failures.append(error)
        self.clock.side_effect=callback
        with self.assertRaises(ValueError) as stopped:self.bind()
        self.assertIs(stopped.exception,failures[0])
        held=self.storage._PublicationStorageAdmission__request_writer_pending
        self.assertIn('result',held);self.assertIs(held['preparation'],self.preparation)
        self.clock.side_effect=None;self.clock.reset_mock()
        with self.assertRaises(ValueError) as again:self.storage.request_writer_view()
        self.assertIs(again.exception,stopped.exception);self.assertIs(self.storage._PublicationStorageAdmission__request_writer_pending,held)
        self.clock.assert_not_called()


if __name__=='__main__':unittest.main()
