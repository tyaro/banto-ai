"""Reader integration only; storage and numerical suites are not replayed."""
import io
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout,redirect_stderr

from banto_ai import anomaly_v03_consumer_reader as reader
from tests import test_anomaly_v03_engineering_consumer as fixtures


class ConsumerReaderTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.EngineeringConsumerTests('test_formal_rejected_before_io')
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.root;(self.root/'checks').mkdir()

    def publish(self):return self.fixture.call(publish=True)

    def call(self,published,**kwargs):
        f=self.fixture
        options={'expected_mode':reader.consumer.MODE,'expected_marker_sha256':published['marker_raw_sha256'],
            'expected_binding_pin':f.binding_pin,'expected_report_pin':f.report_pin,
            'receipt_parent':self.root/'checks','receipt_name':'check'}|kwargs
        return reader.check_in_subprocess(published['output_path'],f.binding_path,f.report_path,f.input_path,**options)

    def saved(self,root):return {p.relative_to(root):p.read_bytes() for p in root.rglob('*') if p.is_file()}

    def request(self,published):
        f=self.fixture
        return {'format':reader.FORMAT,'mode':reader.consumer.MODE,'publication_root':published['output_path'],
            'expected_marker_sha256':published['marker_raw_sha256'],'binding_savepoint':str(f.binding_path),
            'report_savepoint':str(f.report_path),'analysis_input':str(f.input_path),
            'expected_binding_pin':f.binding_pin,'expected_report_pin':f.report_pin}

    def test_separate_process_verified_and_check_root_never_reused(self):
        published=self.publish();root=Path(published['output_path']);before=self.saved(root)
        result=self.call(published)
        self.assertEqual(result['status'],'verified');self.assertTrue(result['separate_process_verified'])
        self.assertTrue(result['reader_exit_confirmed']);self.assertNotEqual(result['reader_pid'],os.getpid())
        self.assertEqual(result['authenticated_artifacts'],7)
        self.assertFalse(result['formal_permission']);self.assertFalse(result['independent_numerical_audit_performed'])
        self.assertEqual(before,self.saved(root))
        with patch.object(reader.supervisor,'supervise',side_effect=AssertionError('relaunch')),self.assertRaises(FileExistsError):
            self.call(published)

    def test_wrong_retained_anchor_is_failed_outside_unchanged_publication(self):
        published=self.publish();root=Path(published['output_path']);before=self.saved(root)
        result=self.call(published,expected_binding_pin={'bytes':1,'sha256':'0'*64})
        self.assertEqual(result['status'],'failed');self.assertTrue(result['reader_exit_confirmed'])
        self.assertFalse(result['separate_process_verified']);self.assertEqual(before,self.saved(root))
        self.assertEqual(json.loads((Path(result['check_directory'])/'result.json').read_bytes())['status'],'failed')

    def test_resealed_changed_value_rejected_against_original_source(self):
        files,_=self.fixture.call();value=json.loads(files['report.json'])
        value['cohorts'][0]['candidate_tables'][0]['saved_null']=True
        changed=reader.io.json_bytes(value);self.assertEqual(len(changed),len(files['report.json']))
        files['report.json']=changed
        published=reader.io.publish_local_result(self.root/'out','resealed',files,verify_semantics=lambda _:None)
        root=Path(published['output_path']);before=self.saved(root)
        result=self.call(published)
        self.assertEqual(result['status'],'failed');self.assertEqual(result['worker_exit_code'],2)
        self.assertEqual(before,self.saved(root));self.assertTrue((root/'.complete').is_file())

    def test_lost_writer_reply_recovered_only_with_retained_marker(self):
        original=reader.io.os.link;retained={}
        def lose_reply(source,target,**kwargs):
            retained['marker_raw_sha256']=reader.io.sha(Path(source).read_bytes())
            original(source,target,**kwargs)
            raise OSError('writer reply lost after commit')
        with patch.object(reader.io.os,'link',lose_reply),self.assertRaises(OSError):self.publish()
        root=self.root/'out/result';before=self.saved(root)
        result=self.call({'output_path':str(root),**retained})
        self.assertEqual(result['status'],'verified');self.assertEqual(before,self.saved(root))
        self.assertNotIn(Path('failure.json'),before)

    def test_incomplete_result_stays_incomplete_and_failed(self):
        published=self.publish();root=Path(published['output_path'])
        # Sequential incomplete fixture, not a live/concurrent writer.
        (root/'.complete').unlink();before=self.saved(root)
        result=self.call(published)
        self.assertEqual(result['status'],'failed');self.assertEqual(before,self.saved(root))
        self.assertFalse((root/'.complete').exists())

    def test_mode_or_missing_anchor_rejected_before_paths(self):
        published={'output_path':str(self.root/'unused'),'marker_raw_sha256':'a'*64}
        with patch.object(reader.io,'_local_parent',side_effect=AssertionError('IO')):
            for options in ({'expected_mode':'formal'},{'expected_marker_sha256':None}):
                with self.assertRaises(ValueError):self.call(published,**options)

    def test_outer_receipt_cannot_overlap_original_publication(self):
        published=self.publish();root=Path(published['output_path']);before=self.saved(root)
        with self.assertRaises(ValueError):self.call(published,receipt_parent=root/'payload',receipt_name='check')
        self.assertEqual(before,self.saved(root))

    def test_wrong_sized_output_rejected_before_opening_payload(self):
        published=self.publish();root=Path(published['output_path']);bad=root/'payload/report.html';bad.write_bytes(b'x\n')
        original=Path.open
        def guard(path,*args,**kwargs):
            self.assertNotEqual(path,bad);return original(path,*args,**kwargs)
        with patch.object(Path,'open',guard),self.assertRaisesRegex(ValueError,'payload size'):
            reader.verify_saved_publication(self.request(published))

    def test_worker_request_hash_checked_before_publication_access(self):
        request=self.root/'request.json';request.write_bytes(b'{}\n')
        with patch.object(reader,'verify_saved_publication',side_effect=AssertionError('publication IO')),redirect_stdout(io.StringIO()):
            self.assertEqual(reader.worker_main([str(request),'3','0'*64]),2)

    def test_supervisor_timeout_is_retained_as_failed(self):
        published=self.publish();root=Path(published['output_path']);before=self.saved(root)
        report={'status':'failed','stop_reason':'time_limit','worker_pid':4321,'worker_exit_confirmed':True,'exit_code':1}
        with patch.object(reader.supervisor,'supervise',return_value=report):result=self.call(published)
        self.assertEqual(result['status'],'failed');self.assertEqual(result['reason'],'time_limit')
        self.assertTrue(result['reader_exit_confirmed']);self.assertEqual(before,self.saved(root))

    def test_lost_reader_reply_is_not_promoted_to_verified(self):
        published=self.publish();original=reader.supervisor.supervise
        def lose_reply(*args,**kwargs):
            report=original(*args,**kwargs)
            self.assertEqual(report['status'],'complete')
            path=Path(args[2])/'report.json';path.write_bytes(b'')
            report['output']=reader.consumer._pin(b'')
            return report
        with patch.object(reader.supervisor,'supervise',lose_reply):result=self.call(published)
        self.assertEqual(result['status'],'failed');self.assertEqual(result['reason'],'reader_response_invalid')
        self.assertFalse(result['separate_process_verified']);self.assertTrue(result['reader_exit_confirmed'])

    def test_unconfirmed_exit_keeps_original_owner_and_unconfirmed_record(self):
        published=self.publish();owner=object()
        error=reader.supervisor.UnreapedWorker(owner,{'status':'failed','worker_exit_confirmed':False})
        with patch.object(reader.supervisor,'supervise',side_effect=error),self.assertRaises(reader.supervisor.UnreapedWorker) as raised:
            self.call(published)
        self.assertIs(raised.exception.process,owner)
        result=json.loads((self.root/'checks/check/result.json').read_bytes())
        self.assertEqual(result['reason'],'worker_exit_unconfirmed');self.assertFalse(result['reader_exit_confirmed'])

    def test_cli_rejects_formal_without_launch(self):
        with redirect_stderr(io.StringIO()),patch.object(reader,'check_in_subprocess',side_effect=AssertionError('launch')):
            with self.assertRaises(SystemExit) as raised:reader.main(['--mode','formal'])
        self.assertEqual(raised.exception.code,2)


if __name__=='__main__':unittest.main()
