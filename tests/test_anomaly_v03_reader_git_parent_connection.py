"""Reader parent connection protocol; fake supervisor/identity, no native run."""
import copy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_preformal_reader_git_worker as worker
from banto_ai import anomaly_v03_preformal_owned_generated_attempt as generated
from tests import test_anomaly_v03_worker_git_proof as facts
from tests import test_anomaly_v03_generation_runtime_observation as generation_fixtures


class ReaderGitParentControllerTests(unittest.TestCase):
    def setUp(self):
        self.f=facts.WorkerGitProofTests('test_normal_raw_close_then_lease_proof_and_real_parent_fence_path')
        self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.names=worker.source_names(generated.copied.SOURCE_FILES)
        self.pins={}
        for name in self.names:
            path=self.f.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'fake source\n')
            self.pins[name]=worker.observed._pin(path.read_bytes())
        self.shared=SimpleNamespace(root=self.f.measured,roots={'outer':self.f.measured,
            'producer':self.f.root/'artifacts/producer','saved-reader':self.f.root/'artifacts/saved-reader',
            'publication':self.f.root/'artifacts/publication'},started_at=100.0,limits={'wall_seconds':90},
            _thread=SimpleNamespace(is_alive=lambda:True),_closed=None,probe=Mock(return_value=None),
            checkpoint=Mock(),require_stage=Mock())
        self.budget=SimpleNamespace(outer=self.shared,root=self.shared.roots['producer'],
            stage='producer',probe=Mock(return_value=None),checkpoint=Mock())
        self.root=self.f.measured/'reader-channel'
        self.policy={'path':self.f.parent.request['policy_path'],'expected_pin':self.f.parent.request['policy_pin']}
        self.profile_pin=worker.observed._pin(b'fake fresh profile')
        self.f.current=self.f.parent_id

    def create(self, **options):
        args={'root':self.root,'revision':self.f.revision,'repository':self.f.root,'policy':self.policy,
            'budget':self.budget,'source_pins':self.pins,'names':self.names,'profile_pin':self.profile_pin}
        args.update(options);return worker.ReaderGitParent.create(**args)

    def test_new_exact_thirty_source_sixty_four_plan_uses_original_outer_clock_and_sampler(self):
        controller=self.create();raw=Path(controller.entry['inventory_path']).read_bytes()
        inventory=worker.v.strict_json(raw)
        self.assertEqual(len(self.names),30);self.assertEqual(len(inventory['calls']),64)
        self.assertLessEqual(len(raw),32768);self.assertEqual(controller.parent.request['clock']['started_at'],100.0)
        self.assertIs(controller.shared,self.shared);self.assertIs(controller.budget,self.budget)
        self.shared.checkpoint.assert_called_with('producer');self.budget.checkpoint.assert_not_called()
        self.assertEqual(controller.source()['selected_files'],[{'path':n,'pin':self.pins[n]} for n in self.names])
        self.assertIs(controller.parent.verify_quiescent,controller.verifier)
        self.assertFalse((self.f.measured/'worker-git.bin').exists())

    def test_unlinked_or_wrong_outer_leaf_denies_before_channel_publication(self):
        with self.assertRaises(ValueError):self.create(budget=self.shared)
        self.assertFalse(self.root.exists())
        with self.assertRaises(ValueError):self.create(root=self.f.root/'artifacts/unused-channel')
        self.assertFalse(self.root.exists())

    def test_modified_or_incomplete_external_source_inventory_denies_before_request(self):
        pins=copy.deepcopy(self.pins);pins.pop(self.names[-1])
        with self.assertRaises(ValueError):self.create(source_pins=pins)
        (self.f.root/self.names[-1]).write_bytes(b'changed')
        with self.assertRaises(ValueError):self.create()
        self.assertFalse(self.root.exists())

    def test_clock_reset_is_latched_without_new_sampler_or_inner_phase_log(self):
        controller=self.create();self.shared.started_at=101.0
        with self.assertRaises(ValueError) as caught:controller.checkpoint()
        self.assertIs(controller.error,caught.exception)
        with self.assertRaises(ValueError) as held:controller.checkpoint()
        self.assertIs(held.exception,caught.exception);self.budget.checkpoint.assert_not_called()

    def test_bind_partial_io_retains_original_popen_before_diagnostics_and_fence_stays_closed(self):
        controller=self.create();failure=OSError('fake binding IO');write=worker.channel._write
        def partial(path,value):
            if path.name=='binding.json':
                (path.parent/'binding.json.pending').write_bytes(b'{partial binding');raise failure
            return write(path,value)
        with patch.object(worker.channel,'_write',side_effect=partial),self.assertRaises(OSError) as caught:
            controller.bind(self.f.process)
        self.assertIs(caught.exception,failure);self.assertIs(controller.worker,self.f.process)
        self.assertIs(controller.parent.worker,self.f.process);self.assertIs(controller.parent.binding_error,failure)
        self.assertFalse(controller.fence(self.f.process));self.assertTrue((self.root/'stop.json').exists())
        self.assertEqual((self.root/'binding.json.pending').read_bytes(),b'{partial binding')

    def test_linked_shared_stop_latches_original_reason_before_source_or_launch(self):
        controller=self.create();self.budget.probe.return_value='fake_outer_stop'
        with self.assertRaises(worker.monitor.resources.ResourceStop) as caught:controller.source()
        self.assertIs(controller.error,caught.exception);self.assertEqual(caught.exception.reason,'fake_outer_stop')
        self.assertIsNone(controller.parent.worker)


class ReaderGitCallerConnectionTests(unittest.TestCase):
    def setUp(self):
        self.f=generation_fixtures.GenerationRuntimeTests('test_producer_wraps_one_actual_operation_with_whole_invocation')
        self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.names=worker.source_names(generated.copied.SOURCE_FILES)
        for name in self.names:
            path=self.f.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'value = 1\n')
            self.f.sources[name]=worker.observed._pin(path.read_bytes())
        self.f.source['selected_files']=[{'path':n,'pin':p} for n,p in self.f.sources.items()]
        self.reader_source=worker.selected_source(self.f.root,'a'*40,{n:self.f.sources[n] for n in self.names},self.names)
        for role in ('producer','initial-reader'):
            value=generated.v.strict_json(self.f.profiles[role]['raw']);value['source_files']=self.f.sources
            raw=generated.v.canonical_json(value)
            self.f.profiles[role]={'raw':raw,'expected_pin':worker.observed._pin(raw)}
        self.budget=SimpleNamespace(checkpoint=Mock(),probe=Mock(return_value=None),record_role=Mock())
        self.plan={'channel_root':str(self.f.root/'artifacts/outer/reader-channel'),
            'policy':{'fake':'caller policy'},'source_pins':{n:self.f.sources[n] for n in self.names}}
        self.events=[];self.process=None
        def bind(process):self.events.append('bind');self.process=process;return self.f.processes['initial-reader']
        self.controller=SimpleNamespace(profile_pin=self.f.profiles['initial-reader']['expected_pin'],
            entry={'fake':'prepared held entry'},source=Mock(return_value=self.reader_source),
            bind=Mock(side_effect=bind),fence=Mock(return_value=True))
        self.create=self.enterContext(patch.object(worker.ReaderGitParent,'create',return_value=self.controller))
        self.runtime_reply=self.enterContext(patch.object(generated,'_runtime_reply',return_value={'fake':'runtime check'}))
        self.enterContext(patch.object(generated,'recheck_runtime_profiles'))

    def execute(self, *, plan=True, profiles=True, bind_error=None):
        calls=[]
        def supervise(argv,cwd,output,limits,*,boundary,on_started,resource_probe=None,stop_fence=None):
            role='producer' if not calls else 'initial-reader';self.f.role=role;calls.append(role)
            boundary();process=SimpleNamespace(pid=self.f.processes[role]['pid'],_handle=self.f.handles[role])
            if bind_error is not None and role=='initial-reader':
                with self.assertRaises(OSError) as caught:on_started(process)
                self.assertIs(caught.exception,bind_error)
                raise generated.supervisor.UnreconciledWorker(process,{'worker_started':True,
                    'worker_pid':process.pid},stop_fence,bind_error)
            on_started(process)
            self.assertEqual(limits,generated.LIMITS if role=='producer' else generated.copied.READER_LIMITS)
            if role=='producer':self.assertIsNone(stop_fence)
            elif plan:
                self.assertEqual(stop_fence,self.controller.fence);self.assertIs(self.process,process)
                self.assertEqual(self.events,['bind']);self.assertTrue(stop_fence(process))
            else:self.assertIsNone(stop_fence)
            request=generated.v.strict_json(Path(argv[-2]).read_bytes());output.mkdir()
            reply=(self.f._produce if role=='producer' else self.f._read)(request,self.f.attempt)
            reply.update(source_before=request['source'],source_after=request['source'],
                         runtime_observation={'fake':role})
            if role=='initial-reader' and plan:
                self.assertEqual(request['worker_git_entry'],self.controller.entry)
                self.assertEqual(request['runtime_inventory_profile_pin'],self.controller.profile_pin)
                self.assertEqual(len(request['source']['selected_files']),30)
            raw=generated.v.canonical_json(reply);(output/'report.json').write_bytes(raw)
            boundary()
            return {'status':'complete','exit_code':0,'worker_started':True,'worker_pid':process.pid,
                'worker_exit_confirmed':True,'output':worker.observed._pin(raw)}
        with patch.object(generated.supervisor,'supervise',side_effect=supervise):
            result=generated.generate_and_read(self.f.attempt,expected_pins=self.f.pins,source_snapshots={},
                expected_revision='a'*40,generation_runtime_profiles=self.f.profiles if profiles else None,
                outer_budget=self.budget,reader_git_plan=self.plan if plan else None)
        return result,calls

    def test_real_parent_invocation_supplies_exact_profile_entry_bind_then_reader_only_fence(self):
        copied_source=generated.copied._source;copied_source.reset_mock()
        result,calls=self.execute()
        self.assertEqual(result['status'],'verified',result.get('detail'));self.assertEqual(calls,['producer','initial-reader'])
        copied_source.assert_not_called();self.controller.bind.assert_called_once();self.controller.fence.assert_called_once_with(self.process)
        self.assertIs(self.create.call_args.kwargs['budget'],self.budget)
        self.assertEqual(self.create.call_args.kwargs['names'],self.names)
        self.assertIs(result['formal_permission'],False);self.assertIs(result['execution_authenticated'],False)

    def test_missing_fresh_profile_refuses_before_any_producer_or_reader_launch(self):
        result,calls=self.execute(profiles=False)
        self.assertEqual(result['status'],'failed');self.assertEqual(calls,[]);self.create.assert_not_called()
        self.assertIn('fresh profiles',result['detail'])

    def test_added_reader_source_missing_from_profile_refuses_before_channel_or_worker(self):
        value=generated.v.strict_json(self.f.profiles['initial-reader']['raw']);value['source_files'].pop(self.names[-1])
        raw=generated.v.canonical_json(value);self.f.profiles['initial-reader']={'raw':raw,'expected_pin':worker.observed._pin(raw)}
        result,calls=self.execute()
        self.assertEqual(result['status'],'failed');self.assertEqual(calls,[]);self.create.assert_not_called()
        self.assertIn('selected Git source differs',result['detail'])

    def test_bind_failure_enters_guarded_original_popen_keeper_with_original_error(self):
        failure=OSError('fake parent bind IO')
        def bind(process):self.process=process;raise failure
        self.controller.bind.side_effect=bind
        held=[]
        def retain(error):held.append(error);raise error
        with patch.object(generated.supervisor,'retain_until_exit',side_effect=retain) as keeper, \
             self.assertRaises(generated.supervisor.UnreconciledWorker) as caught:
            self.execute(bind_error=failure)
        keeper.assert_called_once();self.assertIs(held[0],caught.exception)
        self.assertIs(caught.exception.process,self.process);self.assertIs(caught.exception.fence_error,failure)
        self.assertEqual(caught.exception.stop_fence,self.controller.fence)
