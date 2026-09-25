"""Observe saved-result preparation, without raw data or numerical replay."""
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_analysis_evidence as analysis
from tests import test_anomaly_v03_engineering_consumer as fixtures


@unittest.skipUnless(os.name=='nt','owned Windows analysis preparation')
class AnalysisEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.EngineeringConsumerTests('test_formal_rejected_before_io')
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.root;(self.root/'checks').mkdir()
        self.revision=subprocess.check_output(['git','-C',str(analysis.ROOT),'rev-parse','HEAD'],encoding='utf-8').strip()

    def request(self):
        f=self.fixture
        return {'format':analysis.FORMAT,'mode':analysis.consumer.MODE,'role':'analysis','operation':analysis.OPERATION,
            'binding_savepoint':str(f.binding_path),'report_savepoint':str(f.report_path),'analysis_input':str(f.input_path),
            'expected_binding_pin':f.binding_pin,'expected_report_pin':f.report_pin}

    def call(self,request=None,**kwargs):
        return analysis.prepare_with_evidence(request or self.request(),**({'expected_revision':self.revision,
            'receipt_parent':self.root/'checks','receipt_name':'check'}|kwargs))

    def inputs(self):
        return {str(p):p.read_bytes() for folder in ('analysis','binding','report')
                for p in (self.root/folder).iterdir() if p.is_file()}

    def test_owned_analysis_prepares_four_expected_payloads_without_publishing(self):
        before=self.inputs();expected,_=self.fixture.call();result=self.call()
        self.assertEqual(result['status'],'verified',result)
        self.assertTrue(result['worker_exit_confirmed']);self.assertNotEqual(result['worker_pid'],os.getpid())
        self.assertEqual(result['selected_source_files'],12);self.assertEqual(result['authenticated_input_files'],9)
        self.assertEqual(len(result['payload_pins']),4);self.assertEqual(result['runtime_files'],2)
        target=Path(result['check_directory'])
        self.assertEqual({p.name:p.read_bytes() for p in (target/'payload').iterdir()},expected)
        value=json.loads((target/'evidence.json').read_bytes());retained=json.loads((target/'expected.json').read_bytes())
        self.assertEqual(value['role'],'analysis');self.assertEqual(value['process'],retained['process'])
        self.assertEqual(value['runtime_before'],value['runtime_after']);self.assertEqual(value['runtime_before'],retained['runtime'])
        self.assertEqual(value['source_before'],value['source_after']);self.assertEqual(value['source_before'],retained['source'])
        self.assertTrue(result['parent_and_child_creation_matched'])
        self.assertGreater(result['dependency_observation']['project_files'],12)
        self.assertFalse((target/'.complete').exists());self.assertEqual(before,self.inputs())
        receipt=json.loads((target/'payload/consumer-receipt.json').read_bytes())
        for name in ('score_recalculations','aggregate_recalculations','report_value_recalculations','source_payload_bytes_read'):
            self.assertEqual(receipt[name],0)
        for name in ('formal_permission','execution_authenticated','published','numerical_analysis_performed'):
            self.assertIs(result[name],False)

    def test_existing_attempt_is_not_overwritten(self):
        (self.root/'checks/check').mkdir();marker=self.root/'checks/check/retained';marker.write_bytes(b'retain')
        with patch.object(analysis.supervisor,'supervise',side_effect=AssertionError('launch')),self.assertRaises(FileExistsError):self.call()
        self.assertEqual(marker.read_bytes(),b'retain')

    def test_role_mode_operation_and_reader_profile_rejected_before_io(self):
        cases=[('role','reader'),('role','audit'),('mode','formal'),('operation','recompute'),('dependency_profile','reader.json')]
        for field,value in cases:
            request=self.request();request[field]=value
            with self.subTest(field=field,value=value),patch.object(analysis.io,'_local_parent',side_effect=AssertionError('IO')):
                with self.assertRaises(ValueError):self.call(request)

    def test_output_cannot_overlap_source_inputs(self):
        with patch.object(analysis.supervisor,'supervise',side_effect=AssertionError('launch')),self.assertRaisesRegex(ValueError,'overlaps'):
            self.call(receipt_parent=self.root/'report')
        self.assertFalse((self.root/'report/check').exists())

    def test_incorrect_external_anchor_prevents_launch(self):
        request=self.request();request['expected_report_pin']={'bytes':1,'sha256':'0'*64}
        with patch.object(analysis.supervisor,'supervise',side_effect=AssertionError('launch')):result=self.call(request)
        self.assertEqual(result['status'],'failed');self.assertIsNone(result['worker_pid'])

    def test_analysis_source_git_mismatch_prevents_launch(self):
        original=analysis.observed._file
        def changed(path,*args,**kwargs):
            if Path(path)==analysis.ROOT/'src/banto_ai/anomaly_v03_analysis_evidence.py':return b'# changed\n'
            return original(path,*args,**kwargs)
        with patch.object(analysis.observed,'_file',changed),patch.object(analysis.supervisor,'supervise',side_effect=AssertionError('launch')):
            result=self.call()
        self.assertEqual(result['status'],'failed');self.assertIn('source differs from Git',result['detail'])

    def corrupt(self,change):
        before=self.inputs();original=analysis.supervisor.supervise
        def corrupted(*args,**kwargs):
            monitor=original(*args,**kwargs);self.assertEqual(monitor['status'],'complete',monitor)
            path=Path(args[2])/'report.json';reply=json.loads(path.read_bytes())
            change(reply,Path(args[2]).parent)
            raw=analysis.io.json_bytes(reply);path.write_bytes(raw);monitor['output']=analysis.observed._pin(raw)
            return monitor
        with patch.object(analysis.supervisor,'supervise',corrupted):result=self.call()
        self.assertEqual(result['status'],'failed',result);self.assertTrue(result['worker_exit_confirmed'])
        self.assertEqual(before,self.inputs());self.assertFalse((Path(result['check_directory'])/'binding.json').exists())
        return result

    def test_resealed_reader_role_is_rejected(self):
        result=self.corrupt(lambda reply,path:reply['evidence'].update(role='reader'))
        self.assertIn('role',result['detail'])

    def test_resealed_runtime_is_not_parent_expectation(self):
        result=self.corrupt(lambda reply,path:reply['evidence']['runtime_before']['platform'].update(ubr=9999))
        self.assertIn('runtime before binding',result['detail'])

    def test_resealed_payload_cannot_replace_retained_expected_bytes(self):
        def changed(reply,path):
            raw=b'# Altered saved report\n';(path/'payload/report.md').write_bytes(raw)
            reply['evidence']['outputs']['analysis/report.md']=analysis.observed._pin(raw)
        result=self.corrupt(changed)
        self.assertIn('output differs from retained expectation',result['detail'])

    def test_extra_output_is_rejected(self):
        result=self.corrupt(lambda reply,path:(path/'payload/extra.json').write_bytes(b'{}\n'))
        self.assertIn('saved output inventory',result['detail'])

    def test_child_creation_must_match_original_owned_handle(self):
        result=self.corrupt(lambda reply,path:reply['creation_observation'].update(start_token='0'*64))
        self.assertIn('child/owned creation differs',result['detail'])

    def test_saved_expectation_replacement_is_rejected(self):
        result=self.corrupt(lambda reply,path:(path/'expected.json').write_bytes(b'{}\n'))
        self.assertIn('retained expectation changed',result['detail'])

    def test_dependency_omission_does_not_get_a_success_binding(self):
        def changed(reply,path):
            name='project/src/banto_ai/anomaly_v03_analysis_evidence.py'
            for phase in ('before','after'):
                snapshot=reply['dependencies_'+phase];snapshot['files'].pop(name)
                snapshot['modules']={n:r for n,r in snapshot['modules'].items() if r['file']!=name}
        result=self.corrupt(changed)
        self.assertIn('required reader dependency missing',result['detail'])

    def test_unreaped_worker_owner_is_not_lost_on_save_failure(self):
        owner=object();error=analysis.supervisor.UnreapedWorker(owner,{'status':'failed','worker_exit_confirmed':False})
        original=analysis.observed._save
        def fail(path,value):
            if path.name=='result.json':raise OSError('invented write failure')
            return original(path,value)
        with patch.object(analysis.supervisor,'supervise',side_effect=error),patch.object(analysis.observed,'_save',fail):
            with self.assertRaises(analysis.supervisor.UnreapedWorker) as raised:self.call()
        self.assertIs(raised.exception,error);self.assertIs(raised.exception.process,owner)

    def test_unreaped_worker_output_is_not_read(self):
        owner=object();error=analysis.supervisor.UnreapedWorker(owner,{'status':'failed','worker_exit_confirmed':False})
        original=analysis.consumer.pinned.read_pinned
        def guarded(path,*args,**kwargs):
            self.assertNotIn('worker',Path(path).parts);return original(path,*args,**kwargs)
        with patch.object(analysis.supervisor,'supervise',side_effect=error),patch.object(analysis.consumer.pinned,'read_pinned',guarded):
            with self.assertRaises(analysis.supervisor.UnreapedWorker):self.call()
        saved=json.loads((self.root/'checks/check/result.json').read_bytes())
        self.assertEqual(saved['reason'],'worker_exit_unconfirmed');self.assertFalse(saved['worker_exit_confirmed'])


if __name__=='__main__':unittest.main()
