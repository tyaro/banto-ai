"""A prior candidate stays independent from the subsequent analysis worker's reply."""
import copy
import json
import os
import shutil
from pathlib import Path
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_reader_evidence as observed
from banto_ai import anomaly_v03_analysis_profile as preparation
from banto_ai import _anomaly_v03_reader_dependencies as dep
from tests import test_anomaly_v03_consumer_evidence as pure
from tests import test_anomaly_v03_analysis_evidence as fixtures


class ProfileValues(unittest.TestCase):
    def setUp(self):
        runtime=pure.case()['expected']['runtime']
        self.root=Path('C:/invented')
        self.value={'format':preparation.FORMAT,'mode':observed.consumer.MODE,'role':'analysis','operation':preparation.OPERATION,
            'acceptance':'candidate-not-accepted','source_revision':'a'*40,'root':str(self.root),
            'runtime':runtime,'snapshot':{'format':dep.FORMAT,'scope':dict(dep.SCOPE),'modules':{},
                'files':{'invented':{}},'native_files':[]},'boundary':preparation.BOUNDARY,
            'reference':{n:pure.pin(b'invented') for n in ('result_pin','evidence_pin','dependency_pin','stdout_pin')},
            'scope':dict(dep.SCOPE)}

    def load(self,value=None,**changes):
        raw=observed.io.json_bytes(value or self.value)
        return preparation.load_profile(raw,**({'expected_pin':pure.pin(raw),'root':self.root,'revision':'a'*40}|changes))

    def test_candidate_decode_does_not_claim_acceptance(self):
        profile=self.load()
        self.assertEqual(profile['acceptance'],'candidate-not-accepted')
        self.assertFalse(profile['scope']['formal_permission'])

    def test_reader_profile_format_is_rejected(self):
        value=copy.deepcopy(self.value);value['format']=dep.PROFILE_FORMAT;value['role']='reader';value.pop('operation')
        with self.assertRaises(ValueError):self.load(value)

    def test_external_pin_is_required(self):
        with self.assertRaisesRegex(ValueError,'profile pin'):self.load(expected_pin=pure.pin(b'other'))

    def test_role_mode_and_acceptance_are_closed_before_io(self):
        for field,value in [('mode','formal'),('role','reader'),('operation','recompute'),('acceptance','accepted')]:
            changed=copy.deepcopy(self.value);changed[field]=value
            with self.subTest(field=field),patch.object(Path,'open',side_effect=AssertionError('IO')):
                with self.assertRaisesRegex(ValueError,'role/mode/operation/acceptance'):self.load(changed)

    def test_revision_root_and_boundary_are_fixed(self):
        for field,value in [('source_revision','b'*40),('root','C:/other'),('boundary','after-read')]:
            changed=copy.deepcopy(self.value);changed[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):self.load(changed)

    def test_additional_module_is_a_mismatch(self):
        profile=self.load();snapshot=copy.deepcopy(profile['snapshot'])
        snapshot['modules']['unexpected']={'kind':'built-in','file':None,'cache_candidate':None}
        with self.assertRaisesRegex(ValueError,'inventory before mismatch'):
            dep.match_profile(profile,snapshot,profile['runtime'],phase='before')

    def test_os_update_requires_a_separate_new_candidate(self):
        profile=self.load();runtime=copy.deepcopy(profile['runtime']);runtime['platform']['ubr']+=1
        with self.assertRaisesRegex(ValueError,'runtime after mismatch'):
            dep.match_profile(profile,profile['snapshot'],runtime,phase='after')

    def test_file_identity_change_is_detected(self):
        profile=self.load();snapshot=copy.deepcopy(profile['snapshot']);snapshot['files']['invented']['identity']={'inode':1}
        with self.assertRaisesRegex(ValueError,'inventory after mismatch'):
            dep.match_profile(profile,snapshot,profile['runtime'],phase='after')

    def test_oversized_profile_is_rejected(self):
        raw=b' '*(preparation.MAXIMUM+1)
        with self.assertRaisesRegex(ValueError,'profile size'):
            preparation.load_profile(raw,pure.pin(raw),root=self.root,revision='a'*40)


@unittest.skipUnless(os.name=='nt','owned Windows analysis profile checks')
class LiveProfile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=fixtures.AnalysisEvidenceTests('test_owned_analysis_prepares_four_expected_payloads_without_publishing')
        cls.fixture.setUp();cls.addClassCleanup(cls.fixture.doCleanups)
        cls.request=cls.fixture.request()
        cls.reference=cls.fixture.call(cls.request,receipt_name='reference')
        if cls.reference['status']!='verified':raise AssertionError(cls.reference)
        cls.candidate=preparation.prepare_profile(cls.reference['check_directory'],
            expected_result_pin=cls.reference['result_pin'],expected_revision=cls.fixture.revision,
            profile_parent=cls.fixture.root/'checks',profile_name='candidate.json')

    def call(self,**kwargs):
        return self.fixture.call(self.request,**({'receipt_name':self._testMethodName,
            'dependency_profile':self.candidate['profile_path'],
            'expected_dependency_profile_pin':self.candidate['profile_pin']}|kwargs))

    def clone(self,change):
        value=json.loads(Path(self.candidate['profile_path']).read_bytes());change(value)
        path=self.fixture.root/'checks'/(self._testMethodName+'.json');raw=observed.io.json_bytes(value)
        path.write_bytes(raw);return {'dependency_profile':str(path),'expected_dependency_profile_pin':pure.pin(raw)}

    def test_different_process_matches_separately_prepared_candidate(self):
        result=self.call();self.assertEqual(result['status'],'verified',result)
        self.assertNotEqual(result['worker_pid'],self.reference['worker_pid'])
        self.assertEqual(result['authenticated_input_files'],10)
        self.assertEqual(result['dependency_profile_pin'],self.candidate['profile_pin'])
        target=Path(result['check_directory'])
        binding=json.loads((target/'dependency-profile-binding.json').read_bytes())
        self.assertEqual(binding['reference_result_pin'],self.reference['result_pin'])
        self.assertFalse(binding['formal_permission']);self.assertFalse(binding['execution_authenticated'])
        self.assertEqual((target/'dependency-profile.json').read_bytes(),Path(self.candidate['profile_path']).read_bytes())

    def test_path_and_pin_must_be_paired_before_io(self):
        with patch.object(observed.io,'_local_parent',side_effect=AssertionError('IO')):
            for kwargs in ({'dependency_profile':None},{'expected_dependency_profile_pin':None}):
                with self.subTest(kwargs=kwargs),self.assertRaisesRegex(ValueError,'path/pin pair'):self.call(**kwargs)

    def test_reference_payload_tamper_is_rejected(self):
        copied=self.fixture.root/'checks'/self._testMethodName
        shutil.copytree(self.reference['check_directory'],copied)
        (copied/'payload/report.json').write_bytes(b'{}')
        with self.assertRaises(ValueError):
            preparation.prepare_profile(copied,expected_result_pin=self.reference['result_pin'],
                expected_revision=self.fixture.revision,profile_parent=self.fixture.root/'checks',profile_name='tampered-reference.json')
        self.assertFalse((self.fixture.root/'checks/tampered-reference.json').exists())

    def test_profiled_result_cannot_automatically_replace_candidate(self):
        result=self.call();self.assertEqual(result['status'],'verified',result)
        with self.assertRaisesRegex(ValueError,'unprofiled analysis reference'):
            preparation.prepare_profile(result['check_directory'],expected_result_pin=result['result_pin'],
                expected_revision=self.fixture.revision,profile_parent=self.fixture.root/'checks',profile_name='automatic.json')
        self.assertFalse((self.fixture.root/'checks/automatic.json').exists())

    def test_wrong_profile_pin_prevents_launch(self):
        with patch.object(observed.supervisor,'supervise',side_effect=AssertionError('launch')):
            result=self.call(expected_dependency_profile_pin=pure.pin(b'other'))
        self.assertEqual(result['status'],'failed');self.assertIn('profile pin',result['detail'])
        self.assertIsNone(result['worker_pid'])

    def test_resealed_bad_file_pin_fails_preflight(self):
        def corrupt(profile):next(iter(profile['snapshot']['files'].values()))['pin']['sha256']='0'*64
        args=self.clone(corrupt)
        with patch.object(observed.supervisor,'supervise',side_effect=AssertionError('launch')):result=self.call(**args)
        self.assertEqual(result['status'],'failed');self.assertIn('disk mismatch',result['detail'])

    def test_omitted_module_candidate_is_rejected_by_child_before_read(self):
        args=self.clone(lambda profile:profile['snapshot']['modules'].pop('json'))
        result=self.call(**args);self.assertEqual(result['status'],'failed',result)
        reply=json.loads((Path(result['check_directory'])/'worker/report.json').read_bytes())
        self.assertIn('inventory before mismatch',reply['detail'])
        self.assertFalse((Path(result['check_directory'])/'payload').exists());self.assertTrue(result['worker_exit_confirmed'])

    def test_resealed_reply_cannot_redefine_retained_inventory(self):
        original=observed.supervisor.supervise
        def corrupt(*args,**kwargs):
            report=original(*args,**kwargs);self.assertEqual(report['status'],'complete',report)
            path=Path(args[2])/'report.json';value=json.loads(path.read_bytes())
            for phase in ('before','after'):value['dependencies_'+phase]['modules'].pop('json')
            raw=observed.io.json_bytes(value);path.write_bytes(raw);report['output']=pure.pin(raw)
            return report
        with patch.object(observed.supervisor,'supervise',corrupt):result=self.call()
        self.assertEqual(result['status'],'failed');self.assertIn('inventory before mismatch',result['detail'])
        self.assertFalse((Path(result['check_directory'])/'dependency-profile-binding.json').exists())

    def test_saved_candidate_replacement_after_exit_is_rejected(self):
        original=observed.supervisor.supervise
        def corrupt(*args,**kwargs):
            report=original(*args,**kwargs);self.assertEqual(report['status'],'complete',report)
            (Path(args[2]).parent/'dependency-profile.json').write_bytes(b'{}\n')
            return report
        with patch.object(observed.supervisor,'supervise',corrupt):result=self.call()
        self.assertEqual(result['status'],'failed');self.assertIn('retained analysis dependency profile changed',result['detail'])

    def test_reference_result_cannot_be_selected_without_its_retained_pin(self):
        with self.assertRaises(ValueError):
            preparation.prepare_profile(self.reference['check_directory'],expected_result_pin=pure.pin(b'other'),
                expected_revision=self.fixture.revision,profile_parent=self.fixture.root/'checks',profile_name='wrong-reference.json')
        self.assertFalse((self.fixture.root/'checks/wrong-reference.json').exists())

    def test_profile_cannot_be_written_inside_original_inputs(self):
        with self.assertRaisesRegex(ValueError,'original inputs'):
            preparation.prepare_profile(self.reference['check_directory'],expected_result_pin=self.reference['result_pin'],
                expected_revision=self.fixture.revision,profile_parent=str(Path(self.request['report_savepoint']).parent),profile_name='forbidden.json')
        self.assertFalse((Path(str(Path(self.request['report_savepoint']).parent))/'forbidden.json').exists())


if __name__=='__main__':unittest.main()
