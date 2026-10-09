"""New auxiliary IO risks, with upstream publication stub and small real FileIO.

These declared Python participants are not parent/child native authentication.
The full original 32-entry projection still refuses larger compositions.
"""
import base64
import copy
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

from banto_ai import anomaly_v03_preformal_generated_chain_budget as budget
from banto_ai import anomaly_v03_preformal_reader_git_worker as reader
from tests import test_anomaly_v03_publication_storage_path as fixtures

archive=reader.actors.archive
RAW_OBSERVATIONS=[]


class RequestAuxiliaryWriterIOTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.PublicationStoragePathTests()
        self.f.f=fixtures.children.ReaderControlPublicationTests();self.f.f.setUp();self.addCleanup(self.f.f.doCleanups)
        original=self.f.f.f.call
        def call(*args,**kwargs):
            row=original(*args,**kwargs)
            row['raw_inventory']={'receipt.json':4096,'stdout.bin':128,'stderr.bin':1024}
            return row
        self.f.f.f.call=call
        with patch.object(archive.WorkerGitArchive,'__init__',return_value=None):self.f.a=self.f.f.configure()
        a=self.f.a;self.f.gate=a.control_publication
        allocation={'format':archive.PublicationStorageAdmission.FORMAT,'frame_bytes':8192,'archive_bytes':65536,
            'carrier_failure_bytes':16384,'resident_raw_bytes':1572864,
            'parent_raw_limits':{'stdout.bin':4096,'stderr.bin':4096,'receipt.json':16384}}
        self.s=archive.PublicationStorageAdmission(endpoint=a.child,inventory_raw=a.inventory_raw,
            inventory_pin=a.inventory_pin,root_identity=a.pipe_io['root_identity'],allocation=allocation,
            checkpoint=a.checkpoint,owner=a)
        self.owner=a;self.clock=a.checkpoint
        self.writers={role:reader.RequestAuxiliaryWriter.__new__(reader.RequestAuxiliaryWriter)
            for role in ('parent_failure','diagnostic')}
        self.addCleanup(self.close_test_streams)
        self.publication=budget.PartitionedPublicationPreparation.__new__(budget.PartitionedPublicationPreparation)
        context=archive.io.json_bytes({'request_pin':self.s.request_pin,'inventory_pin':self.s.inventory_pin,
            'revision':self.s.request['revision'],'root':str(self.s.root),'root_identity':list(self.s.identity)})
        self.maxima={'parent_raw_maxima':copy.deepcopy(allocation['parent_raw_limits']),
            'diagnostic_maxima':{'diagnostic.json':2048,'diagnostic.log':2048}}
        self.publication.owner=a;self.publication.checkpoint=self.clock
        self.publication.original_inputs=(a,self.clock,None,self.maxima,None,context,None)
        self.publication._fixed=Mock()  # Explicit upstream stub; storage snapshot and new FileIO are real.
        declaration={'format':budget.RequestWriterPreparation.FORMAT,'context_pin':archive.observed._pin(context),
            'roles':list(budget.RequestWriterPreparation.ROLES),'formal_permission':False}
        participants=tuple(zip(budget.RequestWriterPreparation.ROLES,
            (self.s.gate,object(),object(),self.writers['parent_failure'],self.writers['diagnostic'])))
        self.preparation=budget.RequestWriterPreparation(owner=a,checkpoint=self.clock,
            publication=self.publication,declaration=declaration,participants=participants)
        self.s.bind_request_writers(self.preparation);self.clock.reset_mock()

    def connect(self,role='parent_failure'):
        writer=self.writers[role]
        writer.__init__(owner=self.owner,checkpoint=self.clock,storage=self.s,role=role)
        return writer

    def close_test_streams(self):
        # Only test-created Python streams; original raw observations are recorded
        # before cleanup. No native ownership or recovery claim is made.
        for writer in self.writers.values():
            for row in getattr(writer,'_RequestAuxiliaryWriter__operations',()):
                stream=row.get('stream');raw=getattr(stream,'raw',stream)
                if raw is not None and not raw.closed:raw.close()

    def record(self,writer):
        rows=[]
        for row in writer._RequestAuxiliaryWriter__operations:
            path=row.get('path');raw=row['raw'];actual=path.read_bytes() if path is not None and path.exists() else None
            rows.append({'name':row['name'],'input_base64':base64.b64encode(raw).decode() if type(raw) is bytes else None,
                'actual_file_base64':base64.b64encode(actual).decode() if actual is not None else None,
                'readback_base64':base64.b64encode(row['readback']).decode() if row['readback'] is not None else None,
                'write_return':row.get('write_return'),'close_return_observed':row['close_return_observed'],
                'close_return':row['close_return'],'stream_closed':getattr(row.get('stream'),'closed',None)})
        RAW_OBSERVATIONS.append({'test':self.id(),'role':writer.role,'raw_rows':rows,'native_owner_recovered':False})

    def test_parent_raw_real_file_follows_original_claim_and_full_close_readback(self):
        writer=self.connect();factory=archive.proof.tree.file_io.FileIO;seen=[]
        def opened(path,mode):
            seen.append(self.s.request_writer_view()['claimed_io_roles']);return factory(path,mode)
        raw=b'failure original raw\x00\xff'
        with patch.object(archive.proof.tree.file_io,'FileIO',side_effect=opened):pin=writer.publish('stdout.bin',raw)
        self.assertEqual(seen,[['parent_control','parent_failure']]);self.assertEqual(pin,archive.observed._pin(raw))
        self.assertTrue(writer.completed[0]['close_return_observed']);self.assertEqual(writer.completed[0]['readback'],raw)
        self.assertFalse(writer.view()['native_owner_recovered']);self.record(writer)

    def test_diagnostic_real_file_uses_independent_maximum_and_original_role(self):
        writer=self.connect('diagnostic');writer.publish('diagnostic.log',b'diagnostic raw\n')
        self.assertEqual(self.s.request_writer_view()['claimed_io_roles'],['parent_control','diagnostic'])
        self.assertEqual(writer.limits,self.maxima['diagnostic_maxima']);self.record(writer)

    def test_oversize_raw_is_retained_before_clock_and_file_io(self):
        writer=self.connect('diagnostic');self.clock.reset_mock();raw=b'x'*2049
        with patch.object(archive.proof.tree.file_io,'FileIO') as opened,self.assertRaises(ValueError):writer.publish('diagnostic.log',raw)
        opened.assert_not_called();self.clock.assert_not_called();self.assertIs(writer.pending['raw'],raw);self.record(writer)

    def test_unregistered_participant_is_retained_and_refused_before_io(self):
        foreign=reader.RequestAuxiliaryWriter.__new__(reader.RequestAuxiliaryWriter)
        with patch.object(archive.proof.tree.file_io,'FileIO') as opened,self.assertRaises(ValueError):
            foreign.__init__(owner=self.owner,checkpoint=self.clock,storage=self.s,role='diagnostic')
        opened.assert_not_called();self.clock.assert_not_called();self.assertIs(foreign.original_inputs[2],self.s)
        self.assertIs(self.owner._ReaderGitParent__auxiliary_writer_owners[0][1],foreign)

    def test_different_clock_refuses_before_original_claim(self):
        other=Mock()
        with self.assertRaises(ValueError):self.writers['diagnostic'].__init__(owner=self.owner,checkpoint=other,storage=self.s,role='diagnostic')
        self.clock.assert_not_called();other.assert_not_called()

    def test_claim_interruption_and_second_constructor_keep_first_exception(self):
        error=KeyboardInterrupt('auxiliary original claim');self.clock.side_effect=error;writer=self.writers['parent_failure']
        with self.assertRaises(KeyboardInterrupt) as first:self.connect()
        original=writer.original_inputs;self.clock.side_effect=None;self.clock.reset_mock();writer.error=None
        with self.assertRaises(KeyboardInterrupt) as second:writer.__init__(owner=self.owner,checkpoint=self.clock,storage=self.s,role='diagnostic')
        self.assertIs(first.exception,error);self.assertIs(second.exception,error);self.assertIs(writer.original_inputs,original)
        self.clock.assert_not_called()

    def test_swallowed_constructor_reentry_keeps_original_return_prefix(self):
        writer=self.writers['parent_failure'];errors=[]
        def callback():
            try:writer.__init__(owner=self.owner,checkpoint=self.clock,storage=self.s,role='parent_failure')
            except ValueError as error:errors.append(error)
        self.clock.side_effect=callback
        with self.assertRaises(ValueError) as stopped:self.connect()
        self.assertIs(stopped.exception,errors[0]);self.assertIn('result',self.s._PublicationStorageAdmission__request_writer_pending)
        self.assertIs(writer.original_inputs[2],self.s)

    def test_open_callback_erasure_keeps_original_stream_before_write(self):
        writer=self.connect();factory=archive.proof.tree.file_io.FileIO
        def opened(path,mode):
            stream=factory(path,mode);writer.pending=None;return stream
        with patch.object(archive.proof.tree.file_io,'FileIO',side_effect=opened),self.assertRaises(ValueError):writer.publish('stdout.bin',b'raw')
        held=writer._RequestAuxiliaryWriter__operations[0]
        self.assertIsNotNone(held['stream']);self.assertNotIn('write_attempted',held);self.record(writer)

    def test_partial_write_exception_keeps_raw_stream_prefix_and_refuses_retry(self):
        writer=self.connect();factory=archive.proof.tree.file_io.FileIO;error=OSError('partial original write')
        class Partial:
            def __init__(self,path,mode):self.raw=factory(path,mode)
            def fileno(self):return self.raw.fileno()
            def write(self,raw):self.raw.write(raw[:2]);raise error
            def __getattr__(self,name):return getattr(self.raw,name)
        with patch.object(archive.proof.tree.file_io,'FileIO',Partial),self.assertRaises(OSError) as first:writer.publish('stdout.bin',b'failure')
        held=writer.pending;writer.error=None;self.clock.reset_mock()
        with patch.object(archive.proof.tree.file_io,'FileIO') as opened,self.assertRaises(OSError) as second:writer.publish('stderr.bin',b'new')
        opened.assert_not_called();self.clock.assert_not_called();self.assertIs(first.exception,second.exception)
        self.assertIs(writer.pending,held);self.assertEqual(held['path'].read_bytes(),b'fa');self.record(writer)

    def test_unknown_close_after_real_close_stays_unobserved_and_not_reclosed(self):
        writer=self.connect();factory=archive.proof.tree.file_io.FileIO;error=OSError('unknown original close');closes=[]
        class Unknown:
            def __init__(self,path,mode):self.raw=factory(path,mode)
            def close(self):closes.append(self);self.raw.close();raise error
            def __getattr__(self,name):return getattr(self.raw,name)
        with patch.object(archive.proof.tree.file_io,'FileIO',Unknown),self.assertRaises(OSError):writer.publish('stderr.bin',b'raw')
        self.assertFalse(writer.pending['close_return_observed']);self.assertTrue(writer.pending['stream'].closed)
        with self.assertRaises(OSError):writer.view()
        self.assertEqual(len(closes),1);self.record(writer)

    def test_readback_mismatch_retains_actual_return_and_failure(self):
        writer=self.connect();original=reader.observed._file
        def read(path,maximum):return b'changed' if path.name=='stdout.bin' else original(path,maximum)
        with patch.object(reader.observed,'_file',side_effect=read),self.assertRaises(ValueError):writer.publish('stdout.bin',b'raw')
        self.assertEqual(writer.pending['readback'],b'changed');self.record(writer)

    def test_cached_view_has_no_clock_snapshot_or_file_io(self):
        writer=self.connect();first=writer.view();self.clock.reset_mock()
        with patch.object(budget,'_directory_snapshot') as snapshot,patch.object(archive.proof.tree.file_io,'FileIO') as opened:
            self.assertEqual(writer.view(),first)
        snapshot.assert_not_called();opened.assert_not_called();self.clock.assert_not_called()
        self.assertFalse(first['exclusive_root']);self.assertFalse(first['all_writers_registered'])

    def test_capacity_refusal_keeps_same_root_and_raw_without_open(self):
        writer=self.connect()
        for index in range(self.s.last_observation['remaining_entries']+1):(self.s.root/('unclaimed-'+str(index)+'.bin')).write_bytes(b'x')
        raw=b'raw'
        with patch.object(archive.proof.tree.file_io,'FileIO') as opened,self.assertRaises(ValueError):writer.publish('stdout.bin',raw)
        opened.assert_not_called();self.assertIs(writer.pending['raw'],raw)
        self.assertLess(self.s.pending['remaining_entries'],0);self.record(writer)

    def test_diagnostic_original_maximum_mutation_refuses_before_open(self):
        writer=self.connect('diagnostic');self.clock.side_effect=lambda:self.maxima['diagnostic_maxima'].update({'diagnostic.log':2049})
        with patch.object(archive.proof.tree.file_io,'FileIO') as opened,self.assertRaises(ValueError):writer.publish('diagnostic.log',b'raw')
        opened.assert_not_called();self.assertEqual(writer.limits['diagnostic.log'],2048);self.record(writer)

    def test_parent_keeper_retains_original_auxiliary_candidate_after_display_erasure(self):
        class Escape(BaseException):pass
        parent=reader.ReaderGitParent.__new__(reader.ReaderGitParent)
        parent.error=None;parent.inventory_checkpoint=self.clock;parent.inventory_publication=None
        parent.original_publication_storage=self.s;parent.original_bootstrap_inputs=(None,)*10;parent.worker=None
        writer=self.writers['parent_failure']
        with self.assertRaises(ValueError) as failed:parent.connect_auxiliary_writer('parent_failure',writer)
        original=parent._ReaderGitParent__auxiliary_writer_inputs;self.assertIs(original[0][1],writer)
        with patch.object(reader.ParentPublicationRetention,'_pause',side_effect=Escape):
            with self.assertRaises(Escape):reader.retain_parent_publications(failed.exception,parent)
            keeper=parent.original_publication_retention;parent.auxiliary_writer_inputs=None
            with self.assertRaises(Escape):reader.retain_parent_publications(failed.exception,parent)
        self.assertIs(parent.original_publication_retention,keeper);self.assertIs(keeper.owners[-2],original)
        self.assertIs(keeper.original_error,failed.exception)

    def test_parent_readiness_refuses_auxiliary_preparation_before_clock(self):
        parent=reader.ReaderGitParent.__new__(reader.ReaderGitParent)
        parent._ReaderGitParent__auxiliary_writer_inputs=(('diagnostic',self.writers['diagnostic']),)
        parent._ReaderGitParent__auxiliary_writer_failure=None
        with self.assertRaises(ValueError):parent._inventory_ready()
        self.clock.assert_not_called()

    def test_actual_parent_wrapper_connects_both_original_roles_before_failure_file(self):
        parent=reader.ReaderGitParent.__new__(reader.ReaderGitParent)
        parent.error=None;parent.inventory_checkpoint=self.clock;parent.worker=None
        parent.inventory_publication_error=parent.inventory_pending_owner=None
        parent.original_bootstrap_inputs=(None,)*10;parent.parent=self.s.endpoint
        gate=archive.ControlPublicationAdmission(endpoint=self.s.endpoint,inventory_pin=self.s.inventory_pin,
            root_identity=self.s.identity,control_limits=self.s.gate.control_limits,checkpoint=self.clock,owner=parent)
        parent.inventory_publication=gate
        storage=archive.PublicationStorageAdmission(endpoint=self.s.endpoint,inventory_raw=self.s.inventory_raw,
            inventory_pin=self.s.inventory_pin,root_identity=self.s.identity,allocation=self.s.allocation,
            checkpoint=self.clock,owner=parent)
        publication=budget.PartitionedPublicationPreparation.__new__(budget.PartitionedPublicationPreparation)
        publication.owner=parent;publication.checkpoint=self.clock
        publication.original_inputs=(parent,self.clock,None,self.maxima,None,self.preparation.context_raw,None)
        publication._fixed=Mock()  # Same upstream stub; new original Parent/Control/Storage/Writer are real.
        declaration=copy.deepcopy(self.preparation.original_inputs[3])
        participants=tuple(zip(budget.RequestWriterPreparation.ROLES,
            (gate,object(),object(),self.writers['parent_failure'],self.writers['diagnostic'])))
        parent.prepare_request_writers(publication=publication,declaration=declaration,participants=participants)
        parent.connect_request_writers_to_storage(storage)
        parent.connect_auxiliary_writer('parent_failure',self.writers['parent_failure'])
        parent.connect_auxiliary_writer('diagnostic',self.writers['diagnostic'])
        writer=self.writers['parent_failure'];writer.publish('stdout.bin',b'parent original failure')
        self.assertIs(writer.owner,parent);self.assertIs(writer.storage,storage)
        self.assertEqual(storage.request_writer_view()['claimed_io_roles'],['parent_control','parent_failure','diagnostic'])
        self.assertIs(parent._ReaderGitParent__auxiliary_writer_inputs[0][1],writer)
        self.assertFalse(writer.view()['all_writers_registered']);self.assertFalse(writer.view()['formal_permission'])
        self.record(writer)

    def test_zero_conservative_remaining_entries_refuses_next_actual_file_before_open(self):
        writer=self.connect('diagnostic')
        for index in range(self.s.last_observation['remaining_entries']):(self.s.root/('extra-'+str(index)+'.bin')).write_bytes(b'x')
        with patch.object(archive.proof.tree.file_io,'FileIO') as opened,self.assertRaises(ValueError):writer.publish('diagnostic.log',b'raw')
        opened.assert_not_called();self.assertEqual(writer.pending['before']['remaining_entries'],0)
        self.assertFalse((self.s.root/'diagnostic.log').exists());self.record(writer)

    def test_parent_readiness_first_exception_survives_display_error_reset(self):
        parent=reader.ReaderGitParent.__new__(reader.ReaderGitParent)
        original=(('diagnostic',self.writers['diagnostic']),)
        parent._ReaderGitParent__auxiliary_writer_inputs=original;parent.error=None
        with self.assertRaises(ValueError) as first:parent._inventory_ready()
        parent.error=None;parent.auxiliary_writer_inputs=None
        with self.assertRaises(ValueError) as second:parent._inventory_ready()
        self.assertIs(first.exception,second.exception);self.assertIs(parent.error,first.exception)
        self.assertIs(parent._ReaderGitParent__auxiliary_writer_inputs,original);self.clock.assert_not_called()


if __name__=='__main__':unittest.main()
