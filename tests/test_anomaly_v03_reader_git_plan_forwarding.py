"""Pinned composing-caller plan gates, no worker or native trial."""
import copy
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_preformal_generation_publication_budget as whole
from banto_ai import anomaly_v03_preformal_reader_git_worker as reader
from tests import test_anomaly_v03_preformal_generation_publication_budget as fixtures


class ReaderGitPlanForwardingTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.EnvelopeTests('test_failed_generation_retains_receipts_and_never_starts_saved_reader')
        self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.revision='b'*40;self.names=reader.source_names(whole.generated.copied.SOURCE_FILES)
        self.source_pins={}
        for name in self.names:
            path=self.f.repo/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'fake source\n')
            self.source_pins[name]=reader.observed._pin(path.read_bytes())
        self.external=self.f.artifacts/'external-reader-plan';self.external.mkdir()
        policy_path=self.external/'policy.json'
        policy_raw=reader.io.json_bytes({'revision':self.revision,'process_ownership':reader.tree.direct.JOB_OWNERSHIP})
        policy_path.write_bytes(policy_raw)
        self.profiles={role:{'raw':role.encode(),'expected_pin':reader.observed._pin(role.encode())}
                       for role in ('producer','initial-reader')}
        self.value={'format':whole.READER_PLAN_FORMAT,'revision':self.revision,
            'outer_root':str(self.f.outer),'channel_root':str(self.f.outer/'reader-git-channel'),
            'policy':{'path':str(policy_path),'expected_pin':reader.observed._pin(policy_raw)},
            'source_pins':self.source_pins,'profile_pin':self.profiles['initial-reader']['expected_pin'],
            'formal_permission':False}
        self.entry=self.save(self.value)

    def save(self, value, path=None):
        path=path or self.external/'reader-git-plan.json'
        raw=whole.generated.v.canonical_json(value);path.write_bytes(raw)
        return {'path':str(path),'expected_pin':reader.observed._pin(raw)}

    def load(self, entry=None, **kwargs):
        options={'roots':self.f.roots,'revision':self.revision,'profiles':self.profiles};options.update(kwargs)
        return whole._reader_git_plan(self.entry if entry is None else entry,**options)

    def test_external_canonical_pin_retains_exact_thirty_sources_and_caller_profile_context(self):
        plan=self.load()
        self.assertEqual(set(plan),{'channel_root','policy','source_pins'});self.assertEqual(len(plan['source_pins']),30)
        self.assertEqual(plan['source_pins'],self.source_pins);self.assertEqual(plan['policy'],self.value['policy'])
        plan['source_pins'][self.names[0]]['sha256']='0'*64
        self.assertNotEqual(plan,self.load());self.assertFalse(self.f.outer.exists())

    def test_raw_pin_mutation_rejects_before_source_read_or_output_roots(self):
        Path(self.entry['path']).write_bytes(b'{}')
        with patch.object(reader,'selected_source') as read,self.assertRaises(ValueError):self.load()
        read.assert_not_called();self.assertFalse(self.f.outer.exists())

    def test_revision_profile_or_open_permission_cannot_be_relabelled(self):
        for field,value in [('revision','a'*40),('profile_pin',reader.observed._pin(b'old profile')),
                            ('formal_permission',True)]:
            with self.subTest(field=field):
                bad=copy.deepcopy(self.value);bad[field]=value
                with self.assertRaises(ValueError):self.load(self.save(bad))
        self.assertFalse(self.f.outer.exists())

    def test_plan_policy_or_channel_in_wrong_measured_context_is_refused(self):
        for field,value in [('channel_root',str(self.f.producer/'reader-git-channel')),
                            ('outer_root',str(self.f.reader)),
                            ('policy',{'path':str(self.f.producer/'policy.json'),
                                       'expected_pin':self.value['policy']['expected_pin']})]:
            with self.subTest(field=field):
                bad=copy.deepcopy(self.value);bad[field]=value
                with self.assertRaises(ValueError):self.load(self.save(bad))
        self.f.producer.mkdir();entry=self.save(self.value,self.f.producer/'plan.json')
        with self.assertRaises(ValueError):self.load(entry)
        self.assertTrue(Path(entry['path']).exists());self.assertFalse(self.f.outer.exists())

    def test_missing_or_changed_selected_working_source_refuses_without_channel(self):
        bad=copy.deepcopy(self.value);bad['source_pins'].pop(self.names[-1])
        with self.assertRaises(ValueError):self.load(self.save(bad))
        self.entry=self.save(self.value);(self.f.repo/self.names[-1]).write_bytes(b'changed')
        with self.assertRaises(ValueError):self.load()
        self.assertFalse(self.f.outer.exists())

    def execute(self, *, enabled=True, profiles=True, tamper=False, tamper_descriptor=False):
        manifest_path=self.f.artifacts/'anomaly-v03-preformal-generated-pinsets-one/pins.json'
        manifest_path.parent.mkdir();manifest_path.write_bytes(b'{}')
        pins={'fixture/'+name:{'bytes':1,'sha256':'a'*64} for name in
              ('input.json','slices.json','coverage.json','operation.json')}
        manifest={'revision':self.revision,'recipe_id':whole.generated.RECIPE,
                  'output_bytes':100,'chunk_index':0,'output_pins':{}}
        def stage(root,**kwargs):
            self.forwarded=kwargs
            self.assertEqual(root,self.f.producer)
            linked=kwargs['outer_budget'];self.assertEqual(linked.outer.roots['outer'],self.f.outer)
            self.assertEqual(linked.stage,'producer');self.assertTrue(linked.outer._thread.is_alive())
            return {'status':'failed','result_pin':{'bytes':1,'sha256':'a'*64}}
        def runtime(_):
            if tamper:Path(self.entry['path']).write_bytes(b'{}')
            if tamper_descriptor:self.entry['expected_pin']['sha256']='0'*64
            return {'fake':True}
        with patch.object(whole.generated,'validate_runtime_profiles',return_value=self.profiles if profiles else None), \
             patch.object(whole.generated,'check_runtime_profiles') as check, \
             patch.object(whole,'_source',return_value={'source':'fake'}), \
             patch.object(whole.document.chain.platform_runtime,'probe_runtime',side_effect=runtime), \
             patch.object(whole.document.control_files,'validate_request'), \
             patch.object(whole.reread,'_manifest',return_value=(manifest,{})), \
             patch.object(whole.generated,'generate_and_read',side_effect=stage) as generated, \
             patch.object(whole.reread,'run_reread') as reread:
            result=whole.run(outer_root=self.f.outer,producer_root=self.f.producer,reread_root=self.f.reader,
                receipt_name='trial-one',expected_manifest_pin=reader.observed._pin(b'{}'),
                expected_revision=self.revision,control_root=self.f.artifacts/'unused',
                expected_control_pinset_pin={'bytes':1,'sha256':'a'*64},expected_input_pins=pins,
                generation_runtime_profiles=self.profiles if profiles else None,
                reader_git_plan=self.entry if enabled else None)
        reread.assert_not_called()
        return result,generated,check

    def test_real_composing_run_reopens_plan_and_passes_original_linked_budget_to_reader_parent(self):
        result,generated,check=self.execute()
        generated.assert_called_once();self.assertEqual(self.forwarded['reader_git_plan'],self.load())
        self.assertEqual(self.forwarded['generation_runtime_profiles'],self.profiles)
        self.assertEqual(check.call_args.kwargs['reader_source_pins'],self.source_pins)
        self.assertEqual(set(check.call_args.kwargs['reader_source_names']),set(self.names))
        self.assertTrue(result['reader_git_plan_forwarded']);self.assertEqual(result['reader_git_plan_pin'],self.entry['expected_pin'])
        self.assertEqual(result['status'],'failed');self.assertIs(result['formal_permission'],False)
        self.assertTrue((self.f.outer/'resource-budget.json').exists())

    def test_default_composing_path_omits_new_plan_keyword_and_fresh_profile_option(self):
        result,generated,check=self.execute(enabled=False,profiles=False)
        generated.assert_called_once();self.assertNotIn('reader_git_plan',self.forwarded)
        self.assertNotIn('reader_source_names',check.call_args.kwargs)
        self.assertNotIn('reader_git_plan_forwarded',result)

    def test_changed_plan_after_clock_start_stops_before_owned_stage_and_preserves_raw(self):
        result,generated,_=self.execute(tamper=True)
        generated.assert_not_called();self.assertEqual(result['status'],'failed')
        self.assertEqual(Path(self.entry['path']).read_bytes(),b'{}')
        self.assertTrue((self.f.outer/'resource-budget.json').exists())

    def test_caller_descriptor_mutation_does_not_replace_original_held_pin(self):
        expected=copy.deepcopy(self.entry['expected_pin'])
        result,generated,_=self.execute(tamper_descriptor=True)
        generated.assert_called_once();self.assertNotEqual(self.entry['expected_pin'],expected)
        self.assertEqual(result['reader_git_plan_pin'],expected)
        self.assertEqual(self.forwarded['reader_git_plan']['source_pins'],self.source_pins)

    def test_missing_profiles_rejects_before_any_output_root_or_sampler(self):
        with patch.object(whole.generated,'validate_runtime_profiles',return_value=None), \
             patch.object(whole.generated,'generate_and_read') as generated, \
             self.assertRaises(ValueError):
            whole.run(outer_root=self.f.outer,producer_root=self.f.producer,reread_root=self.f.reader,
                receipt_name='trial-one',expected_manifest_pin=reader.observed._pin(b'{}'),
                expected_revision=self.revision,control_root=self.f.artifacts/'unused',
                expected_control_pinset_pin={'bytes':1,'sha256':'a'*64},expected_input_pins={},
                reader_git_plan=self.entry)
        generated.assert_not_called();self.assertFalse(self.f.outer.exists());self.assertFalse(self.f.producer.exists())
