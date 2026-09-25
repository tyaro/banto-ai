"""Small saved inputs, one ordinary writer and a subsequent owned reader."""
import json
import os
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_analysis_publication as chain
from tests import test_anomaly_v03_analysis_evidence as fixtures


@unittest.skipUnless(os.name=='nt','owned Windows publication chain')
class PublicationChainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=fixtures.AnalysisEvidenceTests('test_owned_analysis_prepares_four_expected_payloads_without_publishing')
        cls.fixture.setUp();cls.addClassCleanup(cls.fixture.doCleanups)
        cls.reference=cls.fixture.call(receipt_name='reference')
        if cls.reference['status']!='verified':raise AssertionError(cls.reference)
        cls.profile=chain.profiles.prepare_profile(cls.reference['check_directory'],expected_result_pin=cls.reference['result_pin'],
            expected_revision=cls.fixture.revision,profile_parent=cls.fixture.root/'checks',profile_name='profile.json')
        cls.analysis=cls.fixture.call(receipt_name='profiled',dependency_profile=cls.profile['profile_path'],
            expected_dependency_profile_pin=cls.profile['profile_pin'])
        if cls.analysis['status']!='verified':raise AssertionError(cls.analysis)

    def call(self,reference=None,**kwargs):
        return chain.publish_and_check(reference or self.analysis['check_directory'],**({
            'expected_mode':chain.consumer.MODE,'expected_analysis_result_pin':self.analysis['result_pin'],
            'expected_revision':self.fixture.revision,'output_parent':self.fixture.root/'out',
            'output_name':self._testMethodName,'receipt_parent':self.fixture.root/'checks',
            'receipt_name':'chain-'+self._testMethodName}|kwargs))

    def clone(self):
        target=self.fixture.root/'checks'/('copy-'+self._testMethodName)
        shutil.copytree(self.analysis['check_directory'],target);return target

    def assert_no_publication(self):self.assertFalse((self.fixture.root/'out'/self._testMethodName).exists())

    def test_analysis_payloads_published_then_separate_reader_checks_exact_bytes(self):
        before=self.fixture.inputs();original=chain.observed.check_with_evidence;observed_closed=[]
        def reader(request,**kwargs):
            root=Path(request['publication_root'])
            self.assertTrue((root/'.complete').is_file());self.assertFalse((root/'stage').exists())
            self.assertTrue((Path(kwargs['receipt_parent'])/'publication-binding.json').is_file())
            observed_closed.append(True);return original(request,**kwargs)
        with patch.object(chain.observed,'check_with_evidence',reader):result=self.call()
        self.assertEqual(result['status'],'analysis_publication_reader_verified',result)
        self.assertEqual(observed_closed,[True]);self.assertTrue(result['reader_exit_confirmed'])
        self.assertNotEqual(result['reader_pid'],os.getpid());self.assertEqual(self.fixture.inputs(),before)
        target=Path(result['check_directory']);publication=Path(result['publication_root'])
        binding_raw=(target/'publication-binding.json').read_bytes();binding=json.loads(binding_raw)
        self.assertEqual(chain.observed._pin(binding_raw),result['publication_binding_pin'])
        self.assertEqual(binding['analysis_result_pin'],self.analysis['result_pin'])
        self.assertEqual(binding['analysis_profile_pin'],self.profile['profile_pin'])
        self.assertEqual(binding['marker_raw_sha256'],result['marker_raw_sha256'])
        for name,pin in self.analysis['payload_pins'].items():
            self.assertEqual(chain.observed._pin((publication/'payload'/name.removeprefix('analysis/')).read_bytes()),pin)
        for key in chain.evidence.CLOSED:self.assertEqual(result[key],chain.evidence.CLOSED[key])
        self.assertFalse(result['numerical_analysis_performed']);self.assertFalse(result['independent_numerical_audit_performed'])
        before={p.relative_to(publication):p.read_bytes() for p in publication.rglob('*') if p.is_file()}
        with self.assertRaises(FileExistsError):self.call()
        self.assertEqual(before,{p.relative_to(publication):p.read_bytes() for p in publication.rglob('*') if p.is_file()})

    def test_formal_mode_rejected_before_io(self):
        with patch.object(chain.io,'regular_path',side_effect=AssertionError('IO')),self.assertRaises(ValueError):
            self.call(expected_mode='formal')

    def test_wrong_retained_result_pin_prevents_any_publication(self):
        with patch.object(chain.io,'publish_local_result',side_effect=AssertionError('publish')),self.assertRaises(ValueError):
            self.call(expected_analysis_result_pin=chain.observed._pin(b'other'))
        self.assert_no_publication()

    def test_unprofiled_reference_is_not_publishable(self):
        with self.assertRaises((ValueError,KeyError)):
            self.call(self.reference['check_directory'],expected_analysis_result_pin=self.reference['result_pin'])
        self.assert_no_publication()

    def test_changed_staged_payload_is_rejected(self):
        reference=self.clone();(reference/'payload/report.md').write_bytes(b'changed\n')
        with self.assertRaises(ValueError):self.call(reference)
        self.assert_no_publication()

    def test_changed_analysis_evidence_is_rejected(self):
        reference=self.clone();(reference/'evidence.json').write_bytes(b'{}\n')
        with self.assertRaises(ValueError):self.call(reference)
        self.assert_no_publication()

    def test_reader_role_result_cannot_be_resealed_as_analysis(self):
        reference=self.clone();value=json.loads((reference/'result.json').read_bytes());value['role']='reader'
        raw=chain.io.json_bytes(value);(reference/'result.json').write_bytes(raw)
        with self.assertRaisesRegex(ValueError,'verified analysis required'):
            self.call(reference,expected_analysis_result_pin=chain.observed._pin(raw))
        self.assert_no_publication()

    def test_output_and_receipt_overlap_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'overlaps publication'):
            self.call(receipt_parent=self.fixture.root/'out',receipt_name=self._testMethodName)
        self.assert_no_publication()

    def test_output_inside_original_inputs_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'original inputs'):
            self.call(output_parent=self.fixture.root/'report')
        self.assertFalse((self.fixture.root/'report'/self._testMethodName).exists())

    def test_failed_write_retains_partial_attempt_without_reader(self):
        original=chain.io.LocalPublication.write
        def fail(store,name,raw):
            if name=='report.md':raise OSError('injected write failure')
            return original(store,name,raw)
        with patch.object(chain.io.LocalPublication,'write',fail),patch.object(chain.observed,'check_with_evidence',side_effect=AssertionError('reader')):
            result=self.call()
        self.assertEqual(result['status'],'failed');self.assertEqual(result['publication_status'],'unconfirmed')
        root=Path(result['publication_root']);self.assertFalse((root/'.complete').exists())
        self.assertTrue(any((root/'stage').iterdir()));self.assertFalse(result['writer_closed_before_reader'])

    def test_lost_writer_reply_is_unconfirmed_and_never_republished(self):
        original=chain.io.publish_local_result
        def lost(*args,**kwargs):original(*args,**kwargs);raise OSError('lost reply')
        with patch.object(chain.io,'publish_local_result',lost),patch.object(chain.observed,'check_with_evidence',side_effect=AssertionError('reader')):
            result=self.call()
        self.assertEqual(result['publication_status'],'unconfirmed');self.assertEqual(result['status'],'failed')
        self.assertTrue((Path(result['publication_root'])/'.complete').is_file())
        with self.assertRaises(FileExistsError):self.call()

    def test_reader_failure_keeps_completed_publication(self):
        reply={'status':'failed','reader_exit_confirmed':True,'reader_pid':123,'result_pin':chain.observed._pin(b'failed')}
        with patch.object(chain.observed,'check_with_evidence',return_value=reply):result=self.call()
        self.assertEqual(result['status'],'failed');self.assertEqual(result['publication_status'],'completed')
        self.assertTrue(result['reader_exit_confirmed']);self.assertTrue((Path(result['publication_root'])/'.complete').is_file())
        self.assertTrue((Path(result['check_directory'])/'publication-binding.json').is_file())

    def test_publication_binding_changed_after_reader_is_rejected(self):
        original=chain.observed.check_with_evidence
        def changed(*args,**kwargs):
            result=original(*args,**kwargs);self.assertEqual(result['status'],'verified',result)
            (Path(kwargs['receipt_parent'])/'publication-binding.json').write_bytes(b'{}\n');return result
        with patch.object(chain.observed,'check_with_evidence',changed):result=self.call()
        self.assertEqual(result['status'],'failed');self.assertIn('publication binding changed',result['detail'])
        self.assertEqual(result['publication_status'],'completed')

    def test_unreaped_reader_owner_survives_chain_receipt_failure(self):
        owner=object();error=chain.supervisor.UnreapedWorker(owner,{'status':'failed','worker_exit_confirmed':False})
        with patch.object(chain.observed,'check_with_evidence',side_effect=error),patch.object(chain.observed,'_save',side_effect=OSError('receipt')):
            with self.assertRaises(chain.supervisor.UnreapedWorker) as raised:self.call()
        self.assertIs(raised.exception,error);self.assertIs(raised.exception.process,owner)
        self.assertTrue((self.fixture.root/'out'/self._testMethodName/'.complete').is_file())


if __name__=='__main__':unittest.main()
