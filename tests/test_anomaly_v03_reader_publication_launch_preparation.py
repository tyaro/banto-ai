"""Local launcher preparation/entry path; fake kernel/Popen, real small files."""
import copy
import builtins
import contextlib
import io
from pathlib import Path
from unittest.mock import Mock,patch
import unittest

from banto_ai import anomaly_v03_preformal_owned_saved_attempt as saved
from tests import test_anomaly_v03_publication_storage_forwarding as storage
from tests import test_anomaly_v03_publication_carrier_path as carriers

reader,tree,archive=storage.reader,storage.tree,storage.archive


class Escape(BaseException):pass


class ReaderPublicationLaunchPreparationTests(unittest.TestCase):
    def setUp(self):
        self.f=storage.PublicationStorageForwardingTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.f.compose()  # Explicit composing snapshot stub, not a capacity proof.
        self.parent_fixture,self.parent=self.f.parent()
        self.kernel=carriers.QueueKernel();self.stdin=Mock()
        self.creator=tree.owner.NativeGitPipes(self.kernel,checkpoint=self.parent.inventory_checkpoint)
        self.creator.create()  # Fake API only. No actual pipe/HANDLE is created.
        self.pipe={'kernel':self.kernel,'stdin':self.stdin}

    def prepare(self):
        self.launch=self.parent.prepare_publication_launch(pipe_io=self.pipe,creator=self.creator)
        return self.launch

    def bind(self):
        self.prepare();self.options=self.launch.bind(self.parent_fixture.f.process)
        self.parent_fixture.f.current=self.parent_fixture.f.child_id
        return self.options

    def worker(self,options=None):
        return reader.ReaderGitWorker(self.parent.entry,revision=self.parent_fixture.f.revision,
            repository=self.parent_fixture.f.root,names=self.parent_fixture.names,**(options or self.options))

    def repin(self,options):
        context=options['publication_io']['context']
        context['pin']=reader.observed._pin(reader.io.json_bytes(context['value']))

    def test_same_original_parent_binding_entry_child_sender_and_archive_are_connected(self):
        self.bind();w=self.worker();inputs=w.publication_inputs;a=w.actor
        self.assertIs(inputs.actor,a);self.assertIs(inputs.carrier_return,a.control_publication.original_publication_carrier)
        self.assertIs(inputs.creator,self.creator);self.assertIs(a.pipe_io['kernel'],self.kernel)
        self.assertIs(a.pipe_io['stdin'],self.stdin);self.assertIs(inputs.worker,w)
        self.assertIs(self.launch.pending,None);self.assertIs(self.launch.process,self.parent_fixture.f.process)
        self.assertIs(self.launch.options['publication_io']['creator'],self.creator)
        self.assertIs(self.parent.publication_carrier_binding['process'],self.launch.process)
        self.assertEqual(inputs.context['value']['worker_identity'],w.child.identity)
        self.assertEqual(inputs.context['value']['clock'],self.parent.clock)
        self.assertEqual(a.writer.rows,[]);self.assertTrue(a.writer.initial_completion['close_return_observed'])
        self.assertEqual(self.kernel.CreatePipe.call_count,2)
        self.kernel.WriteFile.assert_not_called();self.kernel.ReadFile.assert_not_called();self.kernel.CloseHandle.assert_not_called()
        self.stdin.close.assert_not_called();self.assertFalse(a.original_publication_storage.native_launch_preview()['native_launch_authorized'])

    def test_cached_issued_options_do_not_reobserve_popen_or_native_or_file_io(self):
        self.bind()
        with patch.object(reader.observed,'creation_observation') as creation,patch.object(tree.file_io,'FileIO') as opened:
            self.assertIs(self.launch.cached_options(),self.options)
        creation.assert_not_called();opened.assert_not_called();self.kernel.PeekNamedPipe.assert_not_called()

    def test_parent_copies_local_pipe_mapping_before_clock_callback(self):
        original=self.parent.shared.checkpoint.side_effect
        self.parent.shared.checkpoint.side_effect=lambda *_:self.pipe.clear()
        launch=self.prepare();self.parent.shared.checkpoint.side_effect=original
        self.assertEqual(launch.pipe_io,{'kernel':self.kernel,'stdin':self.stdin})
        self.assertIs(launch.original_inputs[1],self.pipe);self.assertEqual(self.pipe,{})

    def test_parent_rebind_keeps_original_and_rejected_popen_without_identity_replay(self):
        self.bind();foreign=Mock()
        with patch.object(reader.observed,'creation_observation') as identity,self.assertRaises(ValueError) as caught:
            self.launch.bind(foreign)
        identity.assert_not_called();self.assertIs(self.launch.process,self.parent_fixture.f.process)
        self.assertIs(self.launch.rejected_process,foreign);self.assertIs(caught.exception,self.launch.error)
        self.assertIs(self.parent.worker,self.launch.process)

    def test_parent_second_preparation_retains_both_original_creators_and_latches(self):
        first=self.prepare();other=tree.owner.NativeGitPipes(self.kernel,checkpoint=self.parent.inventory_checkpoint)
        with self.assertRaises(ValueError):self.parent.prepare_publication_launch(pipe_io=self.pipe,creator=other)
        self.assertIs(self.parent.original_publication_launch,first);self.assertIs(first.rejected.creator,other)
        with self.assertRaises(ValueError):first.bind(self.parent_fixture.f.process)
        self.assertIsNone(first.process);self.kernel.CloseHandle.assert_not_called()

    def test_parent_sidecar_restore_does_not_clear_first_error_or_python_retention(self):
        self.prepare();self.parent.publication_launch=None
        with self.assertRaises(ValueError) as caught:self.launch.cached_options()
        self.parent.publication_launch=self.launch;self.parent.error=None
        with patch.object(reader.ParentPublicationRetention,'_pause',side_effect=Escape),self.assertRaises(Escape):
            reader.retain_parent_publications(caught.exception,self.parent)
        self.assertIn(self.launch,self.parent.original_publication_retention.owners)
        with self.assertRaises(ValueError) as again:self.launch.bind(self.parent_fixture.f.process)
        self.assertIs(again.exception,caught.exception)

    def test_shared_callback_entry_change_denies_before_binding_and_keeps_original_raw(self):
        self.prepare();old=self.launch.entry_raw
        self.parent.entry['storage_plan']['value']['formal_permission']=True
        with patch.object(reader.channel.ParentChannel,'bind') as bind,self.assertRaises(ValueError):
            self.launch.bind(self.parent_fixture.f.process)
        bind.assert_not_called();self.assertEqual(self.launch.entry_raw,old)
        self.assertIsNone(self.launch.process);self.assertIs(self.launch.rejected_process,self.parent_fixture.f.process)

    def test_original_popen_creation_interrupt_is_retained_before_carrier_issue(self):
        self.prepare();failure=KeyboardInterrupt('original Popen creation unknown')
        with patch.object(reader.observed,'creation_observation',side_effect=failure),self.assertRaises(KeyboardInterrupt):
            self.launch.bind(self.parent_fixture.f.process)
        self.assertIs(self.launch.process,self.parent_fixture.f.process)
        self.assertIs(self.launch.pending['process'],self.launch.process)
        self.assertIs(self.parent.worker,self.launch.process);self.assertIs(self.launch.error,failure)
        self.assertNotIn('creation_return',self.launch.pending)
        self.assertFalse(hasattr(self.parent,'original_publication_carrier'))

    def test_binding_unknown_file_close_keeps_original_popen_stream_raw_and_launch(self):
        self.prepare();inject,failure,made=self.f.inject('binding.json.pending',close=True)
        with inject,self.assertRaises(KeyboardInterrupt):self.launch.bind(self.parent_fixture.f.process)
        held=self.parent.inventory_publication.pending
        self.assertIs(held['stream'],made[0]);self.assertTrue(made[0].closed)
        self.assertFalse(held['close_return_observed']);self.assertIs(self.launch.error,failure)
        self.assertIs(self.parent.worker,self.launch.process)
        with patch.object(tree.file_io,'FileIO') as opened,self.assertRaises(KeyboardInterrupt):self.launch.cached_options()
        opened.assert_not_called();self.kernel.CloseHandle.assert_not_called()

    def test_changed_child_context_pin_rejects_before_channel_or_archive_and_retains_inputs(self):
        self.bind();self.options['publication_io']['context']['value']['revision']='changed'
        with patch.object(reader.channel,'ChildChannel') as child,self.assertRaises(ValueError) as caught:self.worker()
        child.assert_not_called();inputs=caught.exception.reader_publication_inputs
        self.assertIs(inputs.original_inputs[2],self.options['publication_io'])
        self.assertIs(inputs.creator,self.creator)

    def test_foreign_request_with_recomputed_pin_rejects_before_actor_and_keeps_binding_return(self):
        self.bind();self.options['publication_io']['context']['value']['request_pin']=reader.observed._pin(b'foreign')
        self.repin(self.options)
        with patch.object(reader.actors,'WorkerGitActor') as actor,self.assertRaises(ValueError) as caught:self.worker()
        actor.assert_not_called();inputs=caught.exception.reader_publication_inputs
        self.assertIsNotNone(inputs.worker.child);self.assertIsNotNone(inputs.binding_return)
        self.assertFalse((self.parent_fixture.f.measured/'worker-git.bin').exists())

    def test_foreign_kernel_rejects_before_channel_and_never_closes_borrowed_stdin(self):
        self.bind();self.options['pipe_io']['kernel']=Mock()
        with patch.object(reader.channel,'ChildChannel') as child,self.assertRaises(ValueError) as caught:self.worker()
        child.assert_not_called();self.assertIs(caught.exception.reader_publication_inputs.creator,self.creator)
        self.stdin.close.assert_not_called()

    def test_child_archive_unknown_close_retains_already_armed_original_sender_before_exit(self):
        self.bind();inject,failure,made=self.f.inject('worker-git.bin',close=True)
        with inject,self.assertRaises(KeyboardInterrupt):self.worker()
        inputs=failure.reader_publication_inputs;a=inputs.actor
        self.assertIs(inputs.carrier_return,a.control_publication.original_publication_carrier)
        self.assertIs(a.writer.initial_pending['stream'],made[0]);self.assertTrue(made[0].closed)
        with patch.object(reader.ReaderPublicationInputs,'_pause',side_effect=Escape),self.assertRaises(Escape):
            reader.retain_reader_initialization(failure)
        self.assertTrue(inputs.worker.child.stopped);self.assertIs(inputs.error,failure)
        self.kernel.CloseHandle.assert_not_called();self.kernel.WriteFile.assert_not_called()

    def test_reader_main_parse_error_holds_original_local_resources_before_diagnostic_print(self):
        self.bind();output=io.StringIO()
        with contextlib.redirect_stdout(output),patch.object(reader.ReaderPublicationInputs,'_pause',side_effect=Escape),self.assertRaises(Escape):
            saved.reader_worker_main([],**self.options)
        self.assertEqual(output.getvalue(),'');self.stdin.close.assert_not_called()
        self.kernel.ReadFile.assert_not_called();self.kernel.WriteFile.assert_not_called()

    def main_invocation(self):
        f=self.parent_fixture;root=f.f.root/'artifacts'/(saved.fixture.PREFIX+'launch-preparation')
        target=root/'owned-reader';target.mkdir(parents=True)
        profile=b'fake fresh profile';(target/'inventory-profile.json').write_bytes(profile)
        request={'format':saved.READER_INVOCATION,'root':str(root),'expected_mode':saved.saved.MODE,
            'chunk_index':0,'output_names':{},'external_pins':{},'source_snapshots':{},'source_revision':f.f.revision,
            'source':{},'runtime':{},'invocation_id':'invented','worker_git_entry':copy.deepcopy(self.parent.entry),
            'runtime_inventory_profile_pin':reader.observed._pin(profile)}
        raw=saved.v.canonical_json(request);path=target/'invocation.json';path.write_bytes(raw)
        return [str(path),reader.observed._pin(raw)['sha256']]

    def test_real_reader_main_forwards_original_resources_before_actor_archive(self):
        self.bind();argv=self.main_invocation();f=self.parent_fixture;held=[]
        original=reader.ReaderGitWorker.run
        def run(worker,operation):held.append(worker);return {'status':'local-fixture','formal_permission':False}
        with (patch.object(saved,'ROOT',f.f.root),patch.object(reader.ReaderGitWorker,'run',run),
              patch.object(reader.ReaderPublicationInputs,'_pause',side_effect=Escape),contextlib.redirect_stdout(io.StringIO())):
            with self.assertRaises(Escape):saved.reader_worker_main(argv,**self.options)
        self.assertEqual(len(held),1);self.assertIs(held[0].publication_inputs.original_inputs[2],self.options['publication_io'])
        self.assertIs(held[0].actor.pipe_io['stdin'],self.stdin)
        self.assertIsNotNone(held[0].publication_inputs.carrier_return);self.assertIs(reader.ReaderGitWorker.run,original)
        self.kernel.CloseHandle.assert_not_called()

    def test_unchecked_local_input_object_cannot_bypass_validation_before_channel_io(self):
        self.bind();unchecked=reader.ReaderPublicationInputs(None,self.pipe,self.options['publication_io'])
        with patch.object(reader.channel,'ChildChannel') as child,self.assertRaises(ValueError) as caught:
            self.worker({'pipe_io':self.pipe,'publication_io':unchecked})
        child.assert_not_called();self.assertIs(caught.exception.reader_publication_inputs,unchecked)
        self.assertIs(unchecked.original_inputs[2],self.options['publication_io'])
        self.kernel.CloseHandle.assert_not_called()

    def test_child_input_sidecar_restore_never_clears_gate_or_first_error(self):
        self.bind();w=self.worker();original=w.actor.publication_inputs;w.actor.publication_inputs=None
        with self.assertRaises(ValueError) as caught:w.actor.probe()
        self.assertIs(w.actor.control_publication.error,caught.exception)
        self.assertIs(original.error,caught.exception);w.actor.publication_inputs=original
        w.actor.control_publication.error=None;w.actor.error=None
        with self.assertRaises(ValueError) as again:w.actor.probe()
        self.assertIs(again.exception,caught.exception);self.assertIs(w.actor.control_publication.error,caught.exception)

    def test_entry_import_failure_retains_original_argv_kernel_creator_before_report(self):
        self.bind();failure=OSError('reader publication bridge import');original=builtins.__import__
        def imported(name,globals=None,locals=None,fromlist=(),level=0):
            if 'anomaly_v03_preformal_reader_git_worker' in fromlist:raise failure
            return original(name,globals,locals,fromlist,level)
        argv=[];output=io.StringIO()
        with (patch.object(builtins,'__import__',side_effect=imported),
              patch.object(saved.ReaderEntryPublicationRetention,'_pause',side_effect=Escape),
              contextlib.redirect_stdout(output),self.assertRaises(Escape)):
            saved.reader_worker_main(argv,**self.options)
        owner=failure.reader_entry_publication_retention
        self.assertIs(owner.original_inputs[0],argv);self.assertIs(owner.original_inputs[2],self.options['publication_io'])
        self.assertIs(owner.error,failure);self.assertEqual(output.getvalue(),'');self.kernel.CloseHandle.assert_not_called()

    def test_successful_operation_return_stays_owned_before_print_without_native_close_witness(self):
        self.bind();argv=self.main_invocation();held=[];reply={'status':'fixture-complete','formal_permission':False}
        def run(worker,operation):held.append(worker);return reply
        output=io.StringIO()
        with (patch.object(saved,'ROOT',self.parent_fixture.f.root),patch.object(reader.ReaderGitWorker,'run',run),
              patch.object(reader.ReaderPublicationInputs,'_pause',side_effect=Escape),
              contextlib.redirect_stdout(output),self.assertRaises(Escape)):
            saved.reader_worker_main(argv,**self.options)
        inputs=held[0].publication_inputs
        self.assertIs(inputs.operation_return,reply)
        self.assertEqual(inputs.error.reason,'reader_publication_launcher_owner_not_reconciled')
        self.assertTrue(inputs.worker.child.stopped);self.assertEqual(output.getvalue(),'')
        self.stdin.close.assert_not_called();self.kernel.CloseHandle.assert_not_called()

    def test_default_bootstrap_and_native_refusal_do_not_issue_resources(self):
        self.assertIn('reader_worker_main(sys.argv[1:])',saved.READER_BOOTSTRAP)
        self.assertNotIn('publication_io',saved.READER_BOOTSTRAP)
        with (patch.object(tree.owner,'_kernel') as kernel,
              patch.object(reader.channel.ParentChannel,'create') as channel,
              self.assertRaises(reader.monitor.resources.ResourceStop)):
            reader.ReaderGitParent.create_native(root=self.parent_fixture.root)
        kernel.assert_not_called();channel.assert_not_called();self.stdin.close.assert_not_called()

    def test_parent_error_metadata_clear_preserves_original_failed_resource_owner(self):
        self.prepare();self.parent.publication_launch=None
        with self.assertRaises(ValueError) as caught:self.launch.cached_options()
        self.parent.publication_launch=self.launch;self.launch.error=self.parent.error=None
        with patch.object(reader.observed,'creation_observation') as creation,self.assertRaises(ValueError) as again:
            self.launch.bind(self.parent_fixture.f.process)
        self.assertIs(again.exception,caught.exception);self.assertIs(self.launch.original_error,caught.exception)
        creation.assert_not_called();self.assertIs(self.launch.creator,self.creator)

    def test_child_pre_actor_error_metadata_clear_never_rearms_copy_or_new_reader(self):
        self.bind();inputs=reader.ReaderPublicationInputs(None,self.pipe,self.options['publication_io']).checked()
        inputs.context['pin']=reader.observed._pin(b'foreign')
        with patch.object(reader.channel,'ChildChannel') as child,self.assertRaises(ValueError) as caught:
            self.worker({'pipe_io':self.pipe,'publication_io':inputs})
        child.assert_not_called();inputs.context=copy.deepcopy(self.options['publication_io']['context']);inputs.error=None
        with self.assertRaises(ValueError) as again:inputs.checked()
        self.assertIs(again.exception,caught.exception);self.assertIs(inputs.original_error,caught.exception)
        self.kernel.CloseHandle.assert_not_called()
