"""Live owned-reader observations on tiny invented saved reports."""
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import Mock,patch

from banto_ai import anomaly_v03_reader_evidence as observed
from tests import test_anomaly_v03_engineering_consumer as fixtures
from tests import test_anomaly_v03_process_supervisor as process_fixtures


@unittest.skipUnless(os.name=='nt','observed reader uses owned Windows process handles')
class ReaderEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.EngineeringConsumerTests('test_formal_rejected_before_io')
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.root;(self.root/'checks').mkdir()
        self.revision=subprocess.check_output(['git','-C',str(observed.ROOT),'rev-parse','HEAD'],encoding='utf-8').strip()

    def publish(self):return self.fixture.call(publish=True)

    def request(self,published):
        f=self.fixture
        return {'format':observed.reader.FORMAT,'mode':observed.consumer.MODE,'publication_root':published['output_path'],
            'expected_marker_sha256':published['marker_raw_sha256'],'binding_savepoint':str(f.binding_path),
            'report_savepoint':str(f.report_path),'analysis_input':str(f.input_path),
            'expected_binding_pin':f.binding_pin,'expected_report_pin':f.report_pin}

    def call(self,request,**kwargs):
        return observed.check_with_evidence(request,**({'expected_revision':self.revision,
            'receipt_parent':self.root/'checks','receipt_name':'check'}|kwargs))

    def saved(self,root):return {p.relative_to(root):p.read_bytes() for p in root.rglob('*') if p.is_file()}

    def test_observed_reader_binds_retained_expectations(self):
        published=self.publish();root=Path(published['output_path']);before=self.saved(root)
        result=self.call(self.request(published));self.assertEqual(result['status'],'verified',result)
        self.assertTrue(result['reader_exit_confirmed']);self.assertNotEqual(result['reader_pid'],os.getpid())
        self.assertEqual(result['authenticated_input_files'],15);self.assertEqual(result['selected_source_files'],10)
        self.assertEqual(result['runtime_files'],2);self.assertEqual(before,self.saved(root))
        target=Path(result['check_directory'])
        expected=json.loads((target/'expected.json').read_bytes());value=json.loads((target/'evidence.json').read_bytes())
        launch=json.loads((target/'launch.json').read_bytes())
        self.assertGreater(launch['creation_time_100ns'],0)
        self.assertEqual(expected['process'],value['process'])
        self.assertEqual(expected['process']['start_token'],launch['start_token'])
        self.assertEqual(value['runtime_before'],value['runtime_after'])
        self.assertEqual(value['runtime_before'],expected['runtime'])
        self.assertEqual(value['runtime_before']['startup']['flags']['no_site'],1)
        self.assertFalse(value['runtime_before']['startup']['site_imported'])
        self.assertEqual(value['source_before'],value['source_after'])
        for key in ('formal_permission','execution_authenticated','source_closure_complete','runtime_closure_complete'):
            self.assertFalse(result[key])
        retained=self.saved(target)
        with patch.object(observed.supervisor,'supervise',side_effect=AssertionError('relaunch')),self.assertRaises(FileExistsError):
            self.call(self.request(published))
        self.assertEqual(retained,self.saved(target))

    def _tamper_reply(self,mutate,*,name='check'):
        published=self.publish();root=Path(published['output_path']);before=self.saved(root)
        original=observed.supervisor.supervise
        def corrupt(*args,**kwargs):
            report=original(*args,**kwargs);self.assertEqual(report['status'],'complete',report)
            path=Path(args[2])/'report.json';value=json.loads(path.read_bytes());mutate(value)
            raw=observed.io.json_bytes(value);path.write_bytes(raw);report['output']=observed._pin(raw)
            return report
        with patch.object(observed.supervisor,'supervise',corrupt):result=self.call(self.request(published),receipt_name=name)
        self.assertEqual(result['status'],'failed',result);self.assertTrue(result['reader_exit_confirmed'])
        self.assertEqual(before,self.saved(root))
        self.assertFalse((Path(result['check_directory'])/'binding.json').exists())
        return result

    def test_resealed_child_output_cannot_replace_parent_expected_result(self):
        result=self._tamper_reply(lambda r:r['reader_report'].update(authenticated_artifacts=8))
        self.assertIn('reader output differs',result['detail'])

    def test_resealed_child_runtime_cannot_become_expected_runtime(self):
        result=self._tamper_reply(lambda r:r['evidence']['runtime_before']['platform'].update(ubr=9999))
        self.assertIn('runtime before binding',result['detail'])

    def test_process_generation_must_match_original_owned_handle(self):
        result=self._tamper_reply(lambda r:r['creation_observation'].update(start_token='0'*64))
        self.assertIn('child/owned creation differs',result['detail'])

    def test_revision_mismatch_prevents_launch(self):
        request=self.request(self.publish())
        with patch.object(observed.supervisor,'supervise',side_effect=AssertionError('launch')):
            result=self.call(request,expected_revision='a'*40)
        self.assertEqual(result['status'],'failed');self.assertIn('reader revision changed',result['detail'])

    def test_selected_working_source_change_prevents_launch(self):
        request=self.request(self.publish());original=observed._file
        def changed(path,*args,**kwargs):
            if Path(path)==observed.ROOT/observed.SOURCE_FILES[0]:return b'# changed fixture source\n'
            return original(path,*args,**kwargs)
        with patch.object(observed,'_file',changed),patch.object(observed.supervisor,'supervise',side_effect=AssertionError('launch')):
            result=self.call(request)
        self.assertEqual(result['status'],'failed');self.assertIn('working/Git bytes differ',result['detail'])

    def test_unreaped_owner_survives_failed_receipt_write(self):
        request=self.request(self.publish());owner=object()
        error=observed.supervisor.UnreapedWorker(owner,{'status':'failed','worker_exit_confirmed':False})
        original=observed._save
        def fail_result(path,value):
            if path.name=='result.json':raise OSError('fixture receipt failure')
            return original(path,value)
        with patch.object(observed.supervisor,'supervise',side_effect=error),patch.object(observed,'_save',fail_result):
            with self.assertRaises(observed.supervisor.UnreapedWorker) as raised:self.call(request)
        self.assertIs(raised.exception,error);self.assertIs(raised.exception.process,owner)
        self.assertTrue((self.root/'checks/check/supervision.json').exists())

    def test_unreaped_failure_is_recorded_without_reading_worker_output(self):
        request=self.request(self.publish());owner=object()
        error=observed.supervisor.UnreapedWorker(owner,{'status':'failed','worker_exit_confirmed':False})
        original=observed.consumer.pinned.read_pinned
        def guard(path,*args,**kwargs):
            self.assertNotIn('worker',path.parts);return original(path,*args,**kwargs)
        with patch.object(observed.supervisor,'supervise',side_effect=error),patch.object(observed.consumer.pinned,'read_pinned',guard):
            with self.assertRaises(observed.supervisor.UnreapedWorker):self.call(request)
        result=json.loads((self.root/'checks/check/result.json').read_bytes())
        self.assertEqual(result['reason'],'worker_exit_unconfirmed');self.assertFalse(result['reader_exit_confirmed'])

    def test_formal_rejected_before_paths_or_git(self):
        request=self.request({'output_path':str(self.root/'unused'),'marker_raw_sha256':'a'*64});request['mode']='formal'
        with patch.object(observed.io,'_local_parent',side_effect=AssertionError('IO')),self.assertRaises(ValueError):self.call(request)


class StartedObserverTests(unittest.TestCase):
    def setUp(self):process_fixtures.ProcessSupervisorTests.setUp(self)

    def run_with_callback(self,callback,process):
        original=observed.supervisor.supervise
        with patch.object(observed.supervisor,'supervise',side_effect=lambda *a,**kw:original(*a,**kw,on_started=callback)):
            return process_fixtures.ProcessSupervisorTests.run_fake(self,process=process)

    def test_callback_observes_original_handle_before_poll_and_reap(self):
        process=process_fixtures.FakeProcess();seen=[]
        def capture(actual):
            self.assertIs(actual,process);self.assertEqual(actual.waits,0);self.assertIsNone(actual.returncode)
            seen.append(actual._handle)
        report,_=self.run_with_callback(capture,process)
        self.assertEqual(seen,[process._handle]);self.assertEqual(report['status'],'complete')
        process._handle.Close.assert_called_once()

    def test_callback_failure_still_stops_and_reaps_owned_process(self):
        callback=Mock(side_effect=OSError('fixture start observation failure'));process=process_fixtures.FakeProcess(running=True)
        report,_=self.run_with_callback(callback,process)
        self.assertEqual(report['status'],'failed');self.assertEqual((process.kills,process.waits),(1,1))
        self.assertTrue(report['worker_exit_confirmed']);process._handle.Close.assert_called_once()

    def test_callback_failure_and_failed_reap_keep_original_owner(self):
        process=process_fixtures.FakeProcess(running=True)
        process.kill=Mock(side_effect=OSError('fixture kill'));process.wait=Mock(side_effect=subprocess.TimeoutExpired('fixture',30))
        with self.assertRaises(observed.supervisor.UnreapedWorker) as raised:
            self.run_with_callback(Mock(side_effect=OSError('fixture start')),process)
        self.assertIs(raised.exception.process,process);process._handle.Close.assert_not_called()


if __name__=='__main__':unittest.main()
