"""A prior candidate stays independent from the subsequent reader's reply."""
import copy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_reader_evidence as observed
from banto_ai import anomaly_v03_reader_profile as preparation
from banto_ai import _anomaly_v03_reader_dependencies as dep
from tests import test_anomaly_v03_consumer_evidence as pure
from tests import test_anomaly_v03_reader_evidence as fixtures


class ProfileValues(unittest.TestCase):
    def setUp(self):
        runtime=pure.case()['expected']['runtime']
        self.root=Path('C:/invented')
        self.value={'format':dep.PROFILE_FORMAT,'mode':observed.consumer.MODE,'role':'reader',
            'acceptance':'candidate-not-accepted','source_revision':'a'*40,'root':str(self.root),
            'runtime':runtime,'snapshot':{'format':dep.FORMAT,'scope':dict(dep.SCOPE),'modules':{},
                'files':{'invented':{}},'native_files':[]},'boundary':dep.PROFILE_BOUNDARY,
            'reference':{n:pure.pin(b'invented') for n in ('result_pin','evidence_pin','dependency_pin','stdout_pin')},
            'scope':dict(dep.SCOPE)}

    def load(self,value=None,**changes):
        raw=observed.io.json_bytes(value or self.value)
        return dep.load_profile(raw,**({'expected_pin':pure.pin(raw),'root':self.root,'revision':'a'*40}|changes))

    def test_candidate_decode_does_not_claim_acceptance(self):
        profile=self.load()
        self.assertEqual(profile['acceptance'],'candidate-not-accepted')
        self.assertFalse(profile['scope']['formal_permission'])

    def test_external_pin_is_required(self):
        with self.assertRaisesRegex(ValueError,'profile pin'):self.load(expected_pin=pure.pin(b'other'))

    def test_role_mode_and_acceptance_are_closed_before_io(self):
        for field,value in [('mode','formal'),('role','analysis'),('acceptance','accepted')]:
            changed=copy.deepcopy(self.value);changed[field]=value
            with self.subTest(field=field),patch.object(Path,'open',side_effect=AssertionError('IO')):
                with self.assertRaisesRegex(ValueError,'role/mode/acceptance'):self.load(changed)

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
        raw=b' '*(dep.PROFILE_MAX+1)
        with self.assertRaisesRegex(ValueError,'profile size'):
            dep.load_profile(raw,pure.pin(raw),root=self.root,revision='a'*40)


@unittest.skipUnless(os.name=='nt','owned Windows reader profile checks')
class LiveProfile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=fixtures.ReaderEvidenceTests('test_observed_reader_binds_retained_expectations')
        cls.fixture.setUp();cls.addClassCleanup(cls.fixture.doCleanups)
        cls.request=cls.fixture.request(cls.fixture.publish())
        cls.reference=cls.fixture.call(cls.request,observe_dependencies=True,receipt_name='reference')
        if cls.reference['status']!='verified':raise AssertionError(cls.reference)
        cls.candidate=preparation.prepare_profile(cls.reference['check_directory'],
            expected_result_pin=cls.reference['result_pin'],expected_revision=cls.fixture.revision,
            profile_parent=cls.fixture.root/'checks',profile_name='candidate.json')

    def call(self,**kwargs):
        return self.fixture.call(self.request,**({'observe_dependencies':True,'receipt_name':self._testMethodName,
            'dependency_profile':self.candidate['profile_path'],
            'expected_dependency_profile_pin':self.candidate['profile_pin']}|kwargs))

    def clone(self,change):
        value=json.loads(Path(self.candidate['profile_path']).read_bytes());change(value)
        path=self.fixture.root/'checks'/(self._testMethodName+'.json');raw=observed.io.json_bytes(value)
        path.write_bytes(raw);return {'dependency_profile':str(path),'expected_dependency_profile_pin':pure.pin(raw)}

    def test_different_process_matches_separately_prepared_candidate(self):
        result=self.call();self.assertEqual(result['status'],'verified',result)
        self.assertNotEqual(result['reader_pid'],self.reference['reader_pid'])
        self.assertEqual(result['authenticated_input_files'],16)
        self.assertEqual(result['dependency_profile_pin'],self.candidate['profile_pin'])
        target=Path(result['check_directory'])
        binding=json.loads((target/'dependency-profile-binding.json').read_bytes())
        self.assertEqual(binding['reference_result_pin'],self.reference['result_pin'])
        self.assertFalse(binding['formal_permission']);self.assertFalse(binding['execution_authenticated'])
        self.assertEqual((target/'dependency-profile.json').read_bytes(),Path(self.candidate['profile_path']).read_bytes())

    def test_wrong_profile_pin_prevents_launch(self):
        with patch.object(observed.supervisor,'supervise',side_effect=AssertionError('launch')):
            result=self.call(expected_dependency_profile_pin=pure.pin(b'other'))
        self.assertEqual(result['status'],'failed');self.assertIn('profile pin',result['detail'])
        self.assertIsNone(result['reader_pid'])

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
        self.assertNotIn('reader_report',reply);self.assertTrue(result['reader_exit_confirmed'])

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
        self.assertEqual(result['status'],'failed');self.assertIn('retained dependency profile changed',result['detail'])

    def test_reference_result_cannot_be_selected_without_its_retained_pin(self):
        with self.assertRaises(ValueError):
            preparation.prepare_profile(self.reference['check_directory'],expected_result_pin=pure.pin(b'other'),
                expected_revision=self.fixture.revision,profile_parent=self.fixture.root/'checks',profile_name='wrong-reference.json')
        self.assertFalse((self.fixture.root/'checks/wrong-reference.json').exists())

    def test_profile_cannot_be_written_inside_original_publication(self):
        with self.assertRaisesRegex(ValueError,'publication/inputs'):
            preparation.prepare_profile(self.reference['check_directory'],expected_result_pin=self.reference['result_pin'],
                expected_revision=self.fixture.revision,profile_parent=self.request['publication_root'],profile_name='forbidden.json')
        self.assertFalse((Path(self.request['publication_root'])/'forbidden.json').exists())


if __name__=='__main__':unittest.main()
