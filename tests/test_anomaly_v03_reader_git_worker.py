"""Reader invocation bridge protocol; no native worker or real dataset read."""
import contextlib
import copy
import io
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_preformal_reader_git_worker as worker
from banto_ai import anomaly_v03_preformal_owned_saved_attempt as copied
from banto_ai import anomaly_v03_role_runtime_observation as observation
from tests import test_anomaly_v03_worker_git_proof as fixtures

tree = worker.tree


class ReaderGitWorkerTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.WorkerGitProofTests('test_normal_raw_close_then_lease_proof_and_real_parent_fence_path')
        self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.enterContext(patch.object(copied,'ROOT',self.f.root))
        self.names=worker.source_names(copied.SOURCE_FILES)
        self.source=b'fake source bytes\n'
        calls=[]
        for phase in ('pre','post'):
            for operation,name in [('head',None),('status',None),*[('source_blob',n) for n in self.names]]:
                call=self.f.call(len(calls),phase);call.update(operation=operation,source_path=name,
                    expected_output_pin=tree.observed._pin(self.source) if name is not None else None)
                calls.append(call)
        self.f.inventory['calls']=calls;self.f.configure()
        self.inventory_raw=tree.io.json_bytes(self.f.inventory)
        self.inventory_pin=tree.observed._pin(self.inventory_raw)

    def prepare(self):
        self.entry=worker.prepare_entry(self.f.parent,inventory_raw=self.inventory_raw,
            inventory_pin=self.inventory_pin,names=self.names);return self.entry

    def create(self):
        return worker.ReaderGitWorker(self.entry,revision=self.f.revision,repository=self.f.root,names=self.names)

    def invocation(self, *, entry=True, profile=True):
        root=self.f.root/'artifacts'/(copied.fixture.PREFIX+'reader-entry');root.mkdir()
        target=root/'owned-reader';target.mkdir()
        request={'format':copied.READER_INVOCATION,'root':str(root),'expected_mode':copied.saved.MODE,
            'chunk_index':0,'output_names':{},'external_pins':{},'source_snapshots':{},
            'source_revision':self.f.revision,'source':{},'runtime':{},'invocation_id':'invented'}
        if entry:request['worker_git_entry']=self.prepare()
        if profile:
            raw=b'invented profile';(target/'inventory-profile.json').write_bytes(raw)
            request['runtime_inventory_profile_pin']=tree.observed._pin(raw)
        raw=copied.v.canonical_json(request);path=target/'invocation.json';path.write_bytes(raw)
        return request,[str(path),tree.observed._pin(raw)['sha256']]

    def fake_worker(self):
        self.events=[]
        def guarded(operation):
            self.events.append('guard')
            try:return operation()
            except BaseException as failure:
                self.guard_error=failure
                raise
        self.fake=SimpleNamespace(identity_bytes=Mock(),blob=Mock(),names=self.names,run=Mock(side_effect=guarded))
        self.enterContext(patch.object(worker,'ReaderGitWorker',return_value=self.fake))
        self.enterContext(patch.object(observation,'load_profile',return_value={'source_revision':self.f.revision}))
        def observed(operation,**kwargs):self.events.append('profile');return operation(),{'fake_runtime':True}
        self.enterContext(patch.object(observation,'run_observed',side_effect=observed))
        return self.fake

    def test_fresh_thirty_sources_sixty_four_calls_and_caller_held_inventory_readback(self):
        entry=self.prepare();self.assertEqual(len(self.names),30);self.assertEqual(len(self.f.inventory['calls']),64)
        self.assertLessEqual(len(self.inventory_raw),32768)
        self.assertEqual(Path(entry['inventory_path']).read_bytes(),self.inventory_raw)
        self.assertEqual(entry['inventory_pin'],self.inventory_pin)
        self.assertEqual(entry['budget_root_identity'],[self.f.measured.stat().st_dev,self.f.measured.stat().st_ino])

    def test_invalid_phase_source_plan_is_rejected_before_inventory_publication(self):
        bad=copy.deepcopy(self.f.inventory);bad['calls'][-1]['source_path']='src/not-the-planned-file.py'
        raw=tree.io.json_bytes(bad)
        with self.assertRaises(ValueError):worker.prepare_entry(self.f.parent,inventory_raw=raw,
            inventory_pin=tree.observed._pin(raw),names=self.names)
        self.assertFalse((self.f.parent.root/'worker-inventory.json').exists())

    def test_binding_ready_child_uses_same_clock_and_new_measured_actor_root(self):
        self.prepare();child=self.create()
        self.assertEqual(child.child.request['clock'],self.f.parent.request['clock'])
        self.assertEqual(child.actor.writer.path,self.f.measured/'worker-git.bin')
        self.assertEqual(child.actor.writer.path.read_bytes(),b'');self.assertEqual(child.child.finished,0)

    def test_expired_shared_clock_denies_actor_before_archive_creation(self):
        self.prepare();self.f.now=191
        with self.assertRaises(ValueError):self.create()
        self.assertFalse((self.f.measured/'worker-git.bin').exists())

    def test_original_outer_leaf_reserve_cap_rejects_before_actor_creation(self):
        self.prepare();(self.f.measured/'retained-fill.bin').write_bytes(b'x'*(901*1024))
        with self.assertRaises(ValueError):self.create()
        self.assertTrue((self.f.measured/'retained-fill.bin').exists())
        self.assertFalse((self.f.measured/'worker-git.bin').exists())

    def test_root_identity_and_external_inventory_pin_mismatch_deny_new_actor(self):
        self.prepare();entry=copy.deepcopy(self.entry);entry['budget_root_identity'][1]+=1
        with self.assertRaises(worker.monitor.resources.ResourceStop):worker.ReaderGitWorker(entry,
            revision=self.f.revision,repository=self.f.root,names=self.names)
        self.entry['inventory_pin']={'bytes':1,'sha256':'0'*64}
        with self.assertRaises(ValueError):self.create()
        self.assertFalse((self.f.measured/'worker-git.bin').exists())

    def test_real_source_callback_pre_post_sequence_has_no_bare_git_fallback(self):
        self.prepare();child=self.create()
        for name in self.names:
            path=self.f.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(self.source)
        calls=[]
        def execute(**options):
            expected=child.actor.verifier.inventory['calls'][len(calls)]
            self.assertEqual((options['phase'],options['operation'],options.get('source_path')),
                (expected['phase'],expected['operation'],expected['source_path']))
            calls.append(options);child.actor.writer.rows.append({'fake_call':len(calls)})
            return self.f.revision.encode()+b'\n' if options['operation']=='head' else b'' if options['operation']=='status' else self.source
        with patch.object(child.actor,'call',side_effect=execute), \
             patch.object(copied.subprocess,'check_output',side_effect=AssertionError('bare Git fallback')):
            before=copied._source(self.f.revision,git_identity=child.identity_bytes,git_blob=child.blob,source_files=child.names)
            after=copied._source(self.f.revision,git_identity=child.identity_bytes,git_blob=child.blob,source_files=child.names)
        self.assertEqual(before,after);self.assertEqual(len(calls),64)
        self.assertEqual([c['phase'] for c in calls],['pre']*32+['post']*32)

    def test_reader_worker_invocation_wraps_observation_before_reporting_with_exact_callbacks(self):
        request,argv=self.invocation();fake=self.fake_worker();reply={'format':'invented','formal_permission':False}
        with patch.object(copied,'_read_attempt',return_value=reply) as read,contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(copied.reader_worker_main(argv),0)
        self.assertEqual(self.events,['guard','profile']);self.assertEqual(fake.run.call_count,1)
        self.assertEqual(read.call_args.kwargs,{'git_identity':fake.identity_bytes,'git_blob':fake.blob,'source_files':self.names})
        self.assertIn('runtime_observation',out.getvalue())

    def test_default_reader_invocation_keeps_prior_callback_free_path(self):
        _,argv=self.invocation(entry=False,profile=False)
        with patch.object(worker,'ReaderGitWorker') as constructor,patch.object(copied,'_read_attempt',return_value={'formal_permission':False}) as read,contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(copied.reader_worker_main(argv),0)
        constructor.assert_not_called();self.assertEqual(read.call_args.kwargs,{})

    def test_opt_in_without_runtime_profile_rejects_before_child_actor_or_data_read(self):
        _,argv=self.invocation(profile=False)
        with patch.object(worker,'ReaderGitWorker') as constructor,patch.object(copied,'_read_attempt') as read,contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(copied.reader_worker_main(argv),2)
        constructor.assert_not_called();read.assert_not_called()
        self.assertIn('requires fresh runtime profile',out.getvalue())

    def test_runtime_profile_failure_passes_inside_guard_before_json_error_reporting(self):
        _,argv=self.invocation();fake=self.fake_worker();failure=ValueError('invented wrong profile')
        with patch.object(observation,'load_profile',side_effect=failure),patch.object(copied,'_read_attempt') as read,contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(copied.reader_worker_main(argv),2)
        self.assertEqual(self.events,['guard']);self.assertEqual(fake.run.call_count,1);read.assert_not_called()

    def test_stop_exception_is_not_converted_into_ordinary_reader_success_or_fallback(self):
        _,argv=self.invocation();self.fake_worker();failure=worker.monitor.resources.ResourceStop('invented shared stop')
        with patch.object(copied,'_read_attempt',side_effect=failure),contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(copied.reader_worker_main(argv),2)
        self.assertIs(self.guard_error,failure);self.assertEqual(self.events,['guard','profile'])
        reply=copied.v.strict_json(out.getvalue().encode())
        self.assertEqual(reply['status'],'failed');self.assertEqual(reply['error_type'],'ResourceStop')
        self.assertIs(reply['formal_permission'],False)
