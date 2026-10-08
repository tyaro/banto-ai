"""New storage allocation path; no old test bodies or native worker launch."""
import contextlib
import copy
import io
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
import unittest

from banto_ai import anomaly_v03_preformal_generation_publication_budget as whole
from banto_ai import anomaly_v03_preformal_reader_git_worker as reader
from tests import test_anomaly_v03_reader_git_append_forwarding as fixtures
from tests import test_anomaly_v03_reader_git_plan_forwarding as plans
from tests import test_anomaly_v03_reader_git_parent_connection as callers
from tests import test_anomaly_v03_reader_git_worker as cli

archive,tree=reader.actors.archive,reader.tree


class Escape(BaseException):pass


class PublicationStorageForwardingTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ReaderGitAppendForwardingTests();self.f.setUp()
        self.controls=copy.deepcopy(self.f.controls);self.limits=copy.deepcopy(self.f.limits)
        self.value={'format':archive.PublicationStorageAdmission.FORMAT,'frame_bytes':8192,
            'archive_bytes':65536,'carrier_failure_bytes':16384,'resident_raw_bytes':1572864,
            'parent_raw_limits':{'stdout.bin':4096,'stderr.bin':4096,'receipt.json':16384}}
        self.allocation={'value':self.value,'pin':reader.observed._pin(reader.io.json_bytes(self.value))}

    def fixture(self,kind):
        f=kind();f.setUp();self.addCleanup(f.doCleanups);return f

    def plan(self):
        f=self.fixture(plans.ReaderGitPlanForwardingTests)
        f.value.update(format=whole.READER_STORAGE_PLAN_FORMAT,pipe_raw_limits=copy.deepcopy(self.limits),
            append_control_limits=copy.deepcopy(self.controls),publication_storage=copy.deepcopy(self.allocation))
        f.entry=f.save(f.value);return f

    def compose(self):
        # Explicit composition stub only. Real occupied-root rejection has its own case.
        self.original_snapshot=reader.monitor._directory_snapshot
        self.snapshot=self.enterContext(patch.object(reader.monitor,'_directory_snapshot',return_value={
            'directory_bytes':0,'directory_entries':0,'directory_depth':1}))

    def parent(self,f=None):
        f=f or self.fixture(callers.ReaderGitParentControllerTests)
        return f,f.create(pipe_raw_limits=self.limits,append_control_limits=self.controls,
            publication_storage=self.allocation)

    def worker(self,f,parent,entry=None):
        parent.bind(f.f.process);f.f.current=f.f.child_id
        return reader.ReaderGitWorker(parent.entry if entry is None else entry,revision=f.f.revision,
            repository=f.f.root,names=f.names,pipe_io={'kernel':Mock(),'stdin':Mock()})

    def inject(self,path_name,*,close=False):
        factory=tree.file_io.FileIO;made=[]
        failure=KeyboardInterrupt('unknown storage forwarded close') if close else OSError('storage partial write')
        class Wrapped:
            def __init__(self,path,mode):self.raw=factory(path,mode);made.append(self)
            def __getattr__(self,name):return getattr(self.raw,name)
            def write(self,raw):
                if not close:self.raw.write(raw[:9]);raise failure
                return self.raw.write(raw)
            def close(self):
                value=self.raw.close()
                if close:raise failure
                return value
        def select(path,mode):return Wrapped(path,mode) if Path(path).name==path_name else factory(path,mode)
        def cleanup():
            for stream in made:
                if not stream.raw.closed:stream.raw.close()  # Test-owned FileIO, never native recovery.
        self.addCleanup(cleanup)
        return patch.object(tree.file_io,'FileIO',side_effect=select),failure,made

    def test_v4_external_closed_allocation_pin_preserves_old_formats(self):
        f=self.plan();resolved=f.load()
        self.assertEqual(resolved['publication_storage'],self.allocation)
        for fmt in (whole.READER_PLAN_FORMAT,whole.READER_PIPE_PLAN_FORMAT,whole.READER_APPEND_PLAN_FORMAT):
            value=copy.deepcopy(f.value);value['format']=fmt
            with self.subTest(fmt=fmt),self.assertRaises(ValueError):f.load(f.save(value))
        value=copy.deepcopy(f.value);value.pop('publication_storage')
        with self.assertRaises(ValueError):f.load(f.save(value))
        self.assertFalse(f.f.outer.exists())

    def test_external_allocation_raw_change_refuses_before_source_or_output_roots(self):
        f=self.plan();f.value['publication_storage']['value']['archive_bytes']=1;f.entry=f.save(f.value)
        with patch.object(reader,'selected_source') as selected,self.assertRaises(ValueError):f.load()
        selected.assert_not_called();self.assertFalse(f.f.outer.exists())

    def test_shared_upper_clock_rereads_and_forwards_same_allocation_pin(self):
        f=self.plan();result,generated,_=f.execute()
        generated.assert_called_once();self.assertEqual(f.forwarded['reader_git_plan']['publication_storage'],self.allocation)
        self.assertEqual(result['reader_git_plan_pin'],f.entry['expected_pin'])
        self.assertEqual(f.forwarded['outer_budget'].outer.roots['outer'],f.f.outer)
        self.assertFalse(result['formal_permission'])

    def test_generate_copies_allocation_before_profile_io_and_forwards_only_opt_in(self):
        f=self.fixture(callers.ReaderGitCallerConnectionTests)
        f.plan.update(pipe_raw_limits=self.limits,append_control_limits=self.controls,publication_storage=self.allocation)
        expected=copy.deepcopy(f.plan);original=whole.generated.validate_runtime_profiles
        def profiles(*args,**kwargs):f.plan.clear();return original(*args,**kwargs)
        with patch.object(whole.generated,'validate_runtime_profiles',side_effect=profiles):result,calls=f.execute()
        self.assertEqual(calls,['producer','initial-reader']);self.assertEqual(result['status'],'verified')
        self.assertEqual(f.create.call_args.kwargs['publication_storage'],expected['publication_storage'])
        self.assertFalse(result['execution_authenticated'])

    def test_invalid_allocation_refuses_generate_before_both_supervisors(self):
        f=self.fixture(callers.ReaderGitCallerConnectionTests)
        bad=copy.deepcopy(self.allocation);bad['value']['archive_bytes']=True
        bad['pin']=reader.observed._pin(reader.io.json_bytes(bad['value']))
        f.plan.update(pipe_raw_limits=self.limits,append_control_limits=self.controls,publication_storage=bad)
        result,calls=f.execute();self.assertEqual(calls,[]);self.assertEqual(result['status'],'failed')
        f.create.assert_not_called()

    def test_invalid_parent_pin_keeps_original_inputs_before_clock_root_or_file_io(self):
        f=self.fixture(callers.ReaderGitParentControllerTests);self.allocation['pin']=reader.observed._pin(b'foreign')
        with patch.object(reader.channel.ParentChannel,'create') as channel,self.assertRaises(ValueError) as caught:
            self.parent(f)
        channel.assert_not_called();self.assertFalse(f.root.exists())
        prep=caught.exception.storage_preparation;p=caught.exception.reader_git_parent
        self.assertIs(prep.owner,p);self.assertIs(prep.original_inputs[3],self.allocation)
        self.assertIs(p.original_bootstrap_inputs[10],self.allocation)
        f.shared.checkpoint.assert_not_called()

    def test_actual_retained_root_slots_refuse_before_initial_request_without_removing_old_raw(self):
        f=self.fixture(callers.ReaderGitParentControllerTests)
        for name in ('held-parent-output.bin','held-parent-diagnostic.bin'):(f.f.measured/name).write_bytes(b'held')
        old={p:p.read_bytes() for p in f.f.measured.rglob('*') if p.is_file()}
        with patch.object(reader.channel.ParentChannel,'create') as channel,self.assertRaises(ValueError) as caught:self.parent(f)
        channel.assert_not_called();self.assertFalse(f.root.exists())
        prep=caught.exception.storage_preparation
        self.assertLess(prep.pending['remaining_entries'],0)
        self.assertEqual(old,{p:p.read_bytes() for p in old})

    def test_request_then_inventory_then_new_entry_then_actor_archive_uses_same_pinned_allocation(self):
        self.compose();factory=tree.file_io.FileIO;events=[]
        def opened(path,mode):events.append(Path(path).name);return factory(path,mode)
        with patch.object(tree.file_io,'FileIO',side_effect=opened):
            f,p=self.parent();w=self.worker(f,p)
        self.assertEqual(events,['request.json.pending','worker-inventory.json.pending','binding.json.pending','worker-git.bin'])
        self.assertEqual(p.entry['format'],reader.STORAGE_ENTRY_FORMAT)
        context=p.entry['storage_plan'];self.assertEqual(context['value']['allocation'],self.allocation)
        self.assertEqual(context['value']['request_pin'],p.parent.request_pin)
        self.assertEqual(context['value']['inventory_pin'],p.entry['inventory_pin'])
        self.assertEqual(context['pin'],reader.observed._pin(reader.io.json_bytes(context['value'])))
        prep=p.original_storage_preparation;self.assertIs(prep.bound_storage,p.original_publication_storage)
        self.assertIs(prep.inventory_raw,p.verifier.inventory_raw)
        storage=w.actor.original_publication_storage
        self.assertIs(storage.checkpoint,w.actor.checkpoint);self.assertIs(storage.writer,w.actor.writer)
        self.assertIs(storage.writer.append_admission.original_publication_storage,storage)
        self.assertTrue(w.actor.writer.initial_completion['close_return_observed'])
        self.assertEqual(w.actor.writer.initial_completion['readback'],b'')
        self.assertEqual(len(storage.inventory['calls']),64);self.assertEqual(w.child.finished,0)
        self.assertFalse(storage.last_observation['native_launch_authorized']);w.pipe_io['stdin'].close.assert_not_called()

    def test_parent_copies_caller_allocation_controls_policy_and_source_before_shared_callback(self):
        self.compose();f=self.fixture(callers.ReaderGitParentControllerTests)
        expected=copy.deepcopy((self.allocation,self.controls,self.limits,f.policy,f.pins))
        def mutate(*_):
            self.allocation.clear();self.controls.clear();self.limits.clear();f.policy.clear();f.pins.clear()
        f.shared.require_stage.side_effect=mutate
        _,p=self.parent(f);prep=p.original_storage_preparation
        self.assertEqual((prep.allocation_entry,prep.controls,prep.raw_limits,prep.policy,prep.source_pins),expected)
        self.assertEqual(p.entry['storage_plan']['value']['allocation'],expected[0])

    def test_parent_creation_interrupt_preserves_preparation_and_partial_request_owner(self):
        self.compose();f=self.fixture(callers.ReaderGitParentControllerTests);failure=KeyboardInterrupt('creation unknown')
        with patch.object(reader.observed,'creation_observation',side_effect=failure),self.assertRaises(KeyboardInterrupt) as caught:
            self.parent(f)
        self.assertIs(caught.exception,failure);prep=failure.storage_preparation;p=prep.owner
        self.assertIs(p.original_request_bootstrap.error,failure);self.assertTrue(f.root.exists())
        self.assertFalse((f.root/'request.json').exists());self.assertIsNone(prep.bound_storage)

    def test_initial_request_unknown_close_retains_original_stream_without_inventory_pin_issuance(self):
        self.compose();f=self.fixture(callers.ReaderGitParentControllerTests)
        inject,failure,made=self.inject('request.json.pending',close=True)
        with inject,self.assertRaises(KeyboardInterrupt):self.parent(f)
        prep=failure.storage_preparation;p=prep.owner;gate=p.original_request_bootstrap
        self.assertIs(gate.pending['stream'],made[0]);self.assertFalse(gate.pending['close_return_observed'])
        self.assertTrue(made[0].closed);self.assertEqual((f.root/'request.json.pending').read_bytes(),gate.pending['raw'])
        self.assertIsNone(prep.inventory_pin);self.assertFalse(hasattr(p,'verifier'))
        with patch.object(tree.file_io,'FileIO') as opened,self.assertRaises(KeyboardInterrupt):p.source()
        opened.assert_not_called();self.assertIs(prep.original_error,failure)

    def test_inventory_partial_write_keeps_same_bound_storage_and_first_raw_error(self):
        self.compose();f=self.fixture(callers.ReaderGitParentControllerTests)
        inject,failure,made=self.inject('worker-inventory.json.pending')
        with inject,self.assertRaises(OSError):self.parent(f)
        prep=failure.storage_preparation;storage=prep.bound_storage;gate=prep.owner.inventory_publication
        self.assertIs(storage.original_error,failure);self.assertIs(gate.pending['stream'],made[0])
        self.assertEqual((f.root/'worker-inventory.json.pending').read_bytes(),gate.pending['raw'][:9])
        self.assertIs(storage.inventory_raw,prep.inventory_raw);self.assertIs(prep.original_error,failure)

    def test_new_entry_missing_pin_or_old_entry_format_denies_before_child_or_archive_io(self):
        self.compose();f,p=self.parent()
        for mode in ('old','missing','changed'):
            entry=copy.deepcopy(p.entry)
            if mode=='old':entry['format']=reader.APPEND_ENTRY_FORMAT
            elif mode=='missing':entry.pop('storage_plan')
            else:entry['storage_plan']['value']['allocation']['value']['archive_bytes']=1
            with self.subTest(mode=mode),patch.object(reader.channel,'ChildChannel') as child,self.assertRaises(ValueError):
                reader.ReaderGitWorker(entry,revision=f.f.revision,repository=f.f.root,names=f.names,
                    pipe_io={'kernel':Mock(),'stdin':Mock()})
            child.assert_not_called()
        self.assertFalse((f.f.measured/'worker-git.bin').exists())

    def test_foreign_storage_request_inventory_root_clock_or_permission_is_not_issued_to_actor(self):
        self.compose();f,p=self.parent();p.bind(f.f.process);f.f.current=f.f.child_id
        for field,value in (('request_pin',reader.observed._pin(b'foreign')),('inventory_pin',reader.observed._pin(b'foreign')),
                            ('budget_root_identity',[1,2]),('clock',{'started_at':101,'wall_seconds':90}),('formal_permission',True)):
            entry=copy.deepcopy(p.entry);context=entry['storage_plan'];context['value'][field]=value
            context['pin']=reader.observed._pin(reader.io.json_bytes(context['value']))
            with self.subTest(field=field),patch.object(reader.actors,'WorkerGitActor') as actor,self.assertRaises(ValueError):
                reader.ReaderGitWorker(entry,revision=f.f.revision,repository=f.f.root,names=f.names,pipe_io={'kernel':Mock(),'stdin':Mock()})
            actor.assert_not_called()
        self.assertFalse((f.f.measured/'worker-git.bin').exists())

    def test_actual_child_storage_refusal_keeps_initializing_actor_before_archive_open(self):
        self.compose();f,p=self.parent();p.bind(f.f.process);f.f.current=f.f.child_id
        self.snapshot.side_effect=self.original_snapshot
        with patch.object(tree.file_io,'FileIO') as opened,self.assertRaises(ValueError) as caught:
            reader.ReaderGitWorker(p.entry,revision=f.f.revision,repository=f.f.root,names=f.names,
                pipe_io={'kernel':Mock(),'stdin':Mock()})
        opened.assert_not_called();w=caught.exception.reader_git_worker;a=w.original_initializing_actor
        self.assertIs(a,caught.exception.worker_git_actor);self.assertIs(a.original_publication_storage.original_error,caught.exception)
        self.assertFalse((f.f.measured/'worker-git.bin').exists())

    def test_reader_copies_storage_entry_before_channel_read_and_never_closes_borrowed_stdin(self):
        self.compose();f,p=self.parent();p.bind(f.f.process);f.f.current=f.f.child_id
        expected=copy.deepcopy(p.entry['storage_plan']);original=reader.channel._read
        def read(path,*args,**kwargs):
            value=original(path,*args,**kwargs)
            if Path(path)==p.parent.root/'request.json':p.entry['storage_plan'].clear()
            return value
        stdin=Mock()
        with patch.object(reader.channel,'_read',side_effect=read):
            w=reader.ReaderGitWorker(p.entry,revision=f.f.revision,repository=f.f.root,names=f.names,
                pipe_io={'kernel':Mock(),'stdin':stdin})
        self.assertEqual(w.actor.storage_plan,expected);self.assertEqual(p.entry['storage_plan'],{})
        stdin.close.assert_not_called();self.assertEqual(w.actor.writer.rows,[])

    def test_archive_unknown_close_keeps_original_writer_stream_and_python_initialization_owner(self):
        self.compose();f,p=self.parent();p.bind(f.f.process);f.f.current=f.f.child_id
        inject,failure,made=self.inject('worker-git.bin',close=True)
        with inject,self.assertRaises(KeyboardInterrupt):
            reader.ReaderGitWorker(p.entry,revision=f.f.revision,repository=f.f.root,names=f.names,
                pipe_io={'kernel':Mock(),'stdin':Mock()})
        w=failure.reader_git_worker;a=w.original_initializing_actor;storage=a.original_publication_storage
        self.assertIs(a.writer,storage.writer);held=a.writer.initial_pending
        self.assertIs(held['stream'],made[0]);self.assertTrue(made[0].closed)
        self.assertNotIn('close_return_observed',held);self.assertEqual(a.writer.path.read_bytes(),b'')
        self.assertIs(storage.original_error,failure);storage.error=None;a.control_publication.error=None
        with patch.object(reader.ReaderInitializationRetention,'_pause',side_effect=Escape),self.assertRaises(Escape):
            reader.retain_reader_initialization(failure)
        self.assertIs(w.original_initialization_retention.actor,a);self.assertTrue(w.child.stopped)

    def test_preparation_plan_callback_mutation_latches_before_request_and_cannot_restore_owner(self):
        self.compose();f=self.fixture(callers.ReaderGitParentControllerTests)
        def mutate(*_):
            prep=getattr(getattr(f.shared,'owner',None),'original_storage_preparation',None)
            if prep is not None:prep.allocation['archive_bytes']=1
        original=archive.PublicationStoragePreparation._fixed
        def fixed(prep):f.shared.owner=prep.owner;mutate();return original(prep)
        with patch.object(archive.PublicationStoragePreparation,'_fixed',fixed),self.assertRaises(ValueError) as caught:self.parent(f)
        prep=caught.exception.storage_preparation;self.assertFalse(f.root.exists());error=prep.original_error
        prep.error=None;prep.owner.storage_preparation=None
        with patch.object(reader.ParentPublicationRetention,'_pause',side_effect=Escape),self.assertRaises(Escape):
            reader.retain_parent_publications(error)
        self.assertIn(prep,prep.owner.original_publication_retention.owners)

    def test_shared_budget_getter_failure_retains_original_caller_input_before_bootstrap_owner_exists(self):
        f=self.fixture(callers.ReaderGitParentControllerTests);failure=OSError('original linked budget getter')
        class Budget:
            @property
            def outer(self):raise failure
        budget=Budget()
        with self.assertRaises(OSError):f.create(budget=budget,pipe_raw_limits=self.limits,
            append_control_limits=self.controls,publication_storage=self.allocation)
        p=failure.reader_git_parent;self.assertIs(p.original_bootstrap_inputs[4],budget)
        self.assertIsNone(p.original_storage_preparation);self.assertFalse(f.root.exists())
        with patch.object(reader.ParentPublicationRetention,'_pause',side_effect=Escape),self.assertRaises(Escape):
            reader.retain_parent_publications(failure)
        self.assertIs(p.original_publication_retention.original_inputs[10],self.allocation)

    def test_reader_main_holds_failed_original_initializer_before_normal_diagnostic_print(self):
        f=self.fixture(cli.ReaderGitWorkerTests);_,argv=f.invocation()
        failure=OSError('retained new storage initializer')
        with patch.object(reader,'ReaderGitWorker',side_effect=failure), \
             patch.object(reader,'retain_reader_initialization',side_effect=Escape) as retain, \
             contextlib.redirect_stdout(io.StringIO()) as out,self.assertRaises(Escape):
            whole.generated.copied.reader_worker_main(argv,pipe_io={'kernel':Mock(),'stdin':Mock()})
        retain.assert_called_once_with(failure);self.assertEqual(out.getvalue(),'')

    def test_parent_preparation_sidecar_removal_latches_before_cached_request_or_source_read(self):
        self.compose();f,p=self.parent();prep=p.original_storage_preparation;p.storage_preparation=None
        with patch.object(reader.observed,'_file') as read,self.assertRaises(ValueError) as caught:p.source()
        read.assert_not_called();error=caught.exception;self.assertIs(prep.original_error,error)
        p.storage_preparation=prep;p.error=None;prep.error=None
        with patch.object(reader.observed,'_file') as read,self.assertRaises(ValueError) as denied:p.source()
        read.assert_not_called();self.assertIs(denied.exception,error)

    def test_actor_issuance_allocation_pin_change_after_clock_is_latched_before_archive_open(self):
        self.compose();f,p=self.parent();p.bind(f.f.process);f.f.current=f.f.child_id
        original=reader.ReaderGitWorker.checkpoint
        def checkpoint(worker):
            result=original(worker)
            actor=getattr(worker,'original_initializing_actor',None)
            storage=getattr(actor,'original_publication_storage',None)
            if storage is not None:actor.storage_plan['value']['allocation']['pin']=reader.observed._pin(b'foreign')
            return result
        with patch.object(reader.ReaderGitWorker,'checkpoint',checkpoint),patch.object(tree.file_io,'FileIO') as opened, \
             self.assertRaises(ValueError) as caught:
            reader.ReaderGitWorker(p.entry,revision=f.f.revision,repository=f.f.root,names=f.names,
                pipe_io={'kernel':Mock(),'stdin':Mock()})
        opened.assert_not_called();a=caught.exception.worker_git_actor;storage=a.original_publication_storage
        self.assertIs(storage.original_error,caught.exception)
        self.assertNotEqual(storage.rejected_issuance_raw,storage.issuance_raw)
        self.assertFalse((f.f.measured/'worker-git.bin').exists())


if __name__=='__main__':unittest.main()
