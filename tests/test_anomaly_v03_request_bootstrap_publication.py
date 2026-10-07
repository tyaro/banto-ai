"""First request FileIO publication, fake creation/budget and real small files."""
import copy
import builtins
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_preformal_reader_git_worker as reader
from tests import test_anomaly_v03_parent_inventory_publication as fixtures

archive,tree,channel=reader.actors.archive,reader.tree,reader.channel


class RequestBootstrapPublicationTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ParentInventoryPublicationTests()
        self.f.setUp();self.addCleanup(self.f.doCleanups)

    def create(self):return self.f.create()

    def injection(self, *, close=False):
        factory=tree.file_io.FileIO;made=[]
        failure=KeyboardInterrupt('unknown original request close') if close else OSError('partial original request write')
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
        def select(path,mode):
            return Wrapped(path,mode) if Path(path)==self.f.f.root/'request.json.pending' else factory(path,mode)
        def cleanup():
            for stream in made:
                if not stream.raw.closed:stream.raw.close()  # Test-owned Python file, no native recovery claim.
        self.addCleanup(cleanup)
        return patch.object(tree.file_io,'FileIO',side_effect=select),failure,made

    def test_first_request_return_raw_then_endpoint_then_inventory_pin_and_cached_no_reclose(self):
        factory=tree.file_io.FileIO;events=[]
        def opened(path,mode):events.append(Path(path).name);return factory(path,mode)
        with patch.object(tree.file_io,'FileIO',side_effect=opened):
            p=self.create();gate=p.original_request_bootstrap
            self.assertEqual(events,['request.json.pending','worker-inventory.json.pending'])
            initial=gate.verification;row=gate.completed['request.json']['original']
            self.assertIs(gate.owner,p);self.assertIs(gate.endpoint,p.parent)
            self.assertIs(p.parent.request_bootstrap_owner,gate)
            self.assertTrue(row['close_return_observed']);self.assertIsNone(row['close_return'])
            self.assertEqual(row['raw'],gate.request_raw);self.assertEqual(row['published_raw'],gate.request_raw)
            inv=reader.v.strict_json(p.verifier.inventory_raw)
            self.assertEqual(inv['request_pin'],gate.request_pin);self.assertEqual(len(inv['calls']),64)
            self.assertEqual(set(p.parent.request),{'format','role','revision','root','root_identity','budget_root',
                'parent_identity','policy_path','policy_pin','nonce','clock','formal_permission'})
            p.source();p.bind(self.f.f.f.process);self.assertFalse(p.fence(self.f.f.f.process))
            self.assertEqual(events,['request.json.pending','worker-inventory.json.pending','binding.json.pending','stop.json.pending'])
            self.assertIs(gate.verification,initial);self.assertIs(gate.cached_verification['original_verification'],initial)
            self.assertIs(gate.completed['request.json']['original'],row)
        self.f.f.budget.checkpoint.assert_not_called()
        self.assertFalse(gate.completed['request.json']['observation']['native_owner_recovered'])

    def test_partial_first_write_holds_stream_raw_owner_error_and_denies_restart(self):
        inject,failure,made=self.injection()
        with inject,self.assertRaises(OSError) as caught:self.create()
        self.assertIs(caught.exception,failure);gate=failure.request_bootstrap_owner;p=failure.reader_git_parent
        self.assertIs(gate.owner,p);self.assertIs(gate.pending['stream'],made[0])
        self.assertEqual((self.f.f.root/'request.json.pending').read_bytes(),gate.pending['raw'][:9])
        self.assertFalse(hasattr(p,'parent'));self.assertFalse((self.f.f.root/'worker-inventory.json').exists())
        with patch.object(tree.file_io,'FileIO') as opened,self.assertRaises(OSError) as denied:p.source()
        self.assertIs(denied.exception,failure);opened.assert_not_called()

    def test_unknown_close_disk_and_closed_metadata_do_not_release_original_pending(self):
        inject,failure,_=self.injection(close=True)
        with inject,self.assertRaises(KeyboardInterrupt) as caught:self.create()
        self.assertIs(caught.exception,failure);gate=failure.request_bootstrap_owner;p=failure.reader_git_parent
        pending=gate.pending
        self.assertTrue(pending['stream'].closed);self.assertFalse(pending['close_return_observed'])
        self.assertEqual((self.f.f.root/'request.json.pending').read_bytes(),pending['raw'])
        with patch.object(tree.file_io,'FileIO') as opened,self.assertRaises(KeyboardInterrupt) as denied:p.bind(self.f.f.f.process)
        self.assertIs(denied.exception,failure);self.assertIs(p.worker,self.f.f.f.process)
        self.assertIs(gate.pending,pending);opened.assert_not_called()

    def test_request_cap_denies_before_file_and_before_inventory_pin_issuance(self):
        self.f.controls['request.json']=10
        with patch.object(tree.file_io,'FileIO') as opened,self.assertRaises(ValueError) as caught:self.create()
        gate=caught.exception.request_bootstrap_owner
        opened.assert_not_called();self.assertGreater(len(gate.pending['raw']),10)
        self.assertIsNone(gate.pending['stream']);self.assertEqual(gate.request_pin,reader.observed._pin(gate.pending['raw']))
        self.assertFalse(hasattr(gate.owner,'verifier'));self.assertFalse((self.f.f.root/'request.json').exists())

    def test_invalid_caps_keep_original_owner_inputs_before_root_or_creation_io(self):
        self.f.controls['ack.json']=True
        with patch.object(channel.observed,'creation_observation') as creation,self.assertRaises(ValueError) as caught:self.create()
        gate=caught.exception.request_bootstrap_owner;p=caught.exception.reader_git_parent
        self.assertIs(gate.original_controls,self.f.controls);self.assertIs(gate.owner,p)
        self.assertIs(p.original_bootstrap_inputs[-1],self.f.controls)
        creation.assert_not_called();self.assertFalse(self.f.f.root.exists())

    def test_creation_interrupt_holds_clock_root_and_partial_request_before_file(self):
        failure=KeyboardInterrupt('original parent creation unavailable')
        with (patch.object(channel.observed,'creation_observation',side_effect=failure),
              patch.object(tree.file_io,'FileIO') as opened,self.assertRaises(KeyboardInterrupt) as caught):self.create()
        self.assertIs(caught.exception,failure);gate=failure.request_bootstrap_owner
        self.assertEqual(gate.generation['clock']['started_at'],100.0)
        self.assertEqual(gate.generation['created_root'],self.f.f.root)
        self.assertGreater(gate.generation['parent_pid'],0)
        self.assertIn('root_identity',gate.generation['request']);opened.assert_not_called()

    def test_caller_caps_and_policy_snapshot_survive_shared_callback_mutation(self):
        controls=copy.deepcopy(self.f.controls);policy=copy.deepcopy(self.f.f.policy)
        self.f.f.shared.require_stage.side_effect=lambda *_:self.f.controls.clear()
        p=self.create();gate=p.original_request_bootstrap
        self.assertEqual(gate.control_limits,controls);self.assertEqual(gate.policy,policy)
        self.assertEqual(p.append_controls,controls)
        self.assertIs(gate.budget,self.f.f.shared)

    def test_published_request_then_non_none_rename_return_keeps_raw_and_rejects_endpoint(self):
        rename=channel.io._rename_no_replace
        def unknown(src,dst):
            value=rename(src,dst)
            return False if Path(dst)==self.f.f.root/'request.json' else value
        with patch.object(channel.io,'_rename_no_replace',side_effect=unknown),self.assertRaises(ValueError) as caught:self.create()
        gate=caught.exception.request_bootstrap_owner
        self.assertFalse(gate.pending['rename_return'])
        self.assertEqual((self.f.f.root/'request.json').read_bytes(),gate.request_raw)
        self.assertFalse(hasattr(gate.owner,'parent'));self.assertFalse(hasattr(gate.owner,'verifier'))

    def test_changed_request_after_success_keeps_initial_and_changed_raw_without_reopen(self):
        p=self.create();gate=p.original_request_bootstrap;initial=gate.verification['raw']['request.json']
        (self.f.f.root/'request.json').write_bytes(b'changed request')
        with patch.object(tree.file_io,'FileIO') as opened,self.assertRaises(ValueError) as caught:p.source()
        opened.assert_not_called();self.assertIs(p.error,caught.exception)
        self.assertEqual(gate.pending['raw']['request.json'],b'changed request');self.assertEqual(gate.request_raw,initial)

    def test_foreign_bootstrap_sidecar_stays_retained_after_metadata_restoration(self):
        p=self.create();gate=p.original_request_bootstrap;foreign=SimpleNamespace(stream=object(),raw=b'foreign')
        p.request_bootstrap_owner=foreign
        with self.assertRaises(ValueError) as caught:p.source()
        self.assertEqual(p.rejected_request_bootstrap,(gate,foreign))
        p.request_bootstrap_owner=gate
        with self.assertRaises(ValueError) as denied:p.source()
        self.assertIs(denied.exception,caught.exception);self.assertEqual(p.rejected_request_bootstrap,(gate,foreign))

    def test_rearm_keeps_original_request_and_refused_input_without_io(self):
        p=self.create();gate=p.original_request_bootstrap;request=gate.original_request;foreign={'formal_permission':True}
        with self.assertRaises(ValueError):gate.arm(foreign)
        self.assertIs(gate.original_request,request);self.assertIs(gate.rejected_request,foreign)
        with patch.object(tree.file_io,'FileIO') as opened,self.assertRaises(ValueError):p.source()
        opened.assert_not_called()

    def test_native_entry_still_denies_before_bootstrap_constructor(self):
        with patch.object(archive,'RequestBootstrapAdmission') as bootstrap,self.assertRaises(reader.monitor.resources.ResourceStop):
            reader.ReaderGitParent.create_native(append_control_limits=self.f.controls)
        bootstrap.assert_not_called();self.assertFalse(self.f.f.root.exists())

    def test_bootstrap_entry_import_failure_retains_original_input_and_exception_before_root_io(self):
        owner=SimpleNamespace();checkpoint=lambda:None
        gate=archive.RequestBootstrapAdmission(root=self.f.f.root,revision=self.f.f.f.revision,policy=self.f.f.policy,
            budget=self.f.f.shared,control_limits=self.f.controls,checkpoint=checkpoint,owner=owner)
        original=builtins.__import__;failure=ImportError('original bootstrap entry import interrupted')
        def importing(name,*args,**options):
            if name=='anomaly_v03_preformal_worker_git_archive':raise failure
            return original(name,*args,**options)
        with patch.object(builtins,'__import__',side_effect=importing),self.assertRaises(ImportError) as caught:
            channel.ParentChannel.create(root=self.f.f.root,revision=self.f.f.f.revision,policy=self.f.f.policy,
                budget=self.f.f.shared,verify_quiescent=lambda *_:False,request_admission=gate)
        self.assertIs(caught.exception,failure);self.assertIs(failure.request_bootstrap_input,gate)
        self.assertIs(gate.error,failure)
        self.assertIs(gate.owner,owner);self.assertIs(owner.request_bootstrap_owner,gate)
        self.assertFalse(self.f.f.root.exists())
