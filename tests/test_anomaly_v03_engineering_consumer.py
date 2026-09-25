"""Small invented saved reports; no real campaign data or numerical replay."""
from contextlib import ExitStack, redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_engineering_consumer as consumer


class EngineeringConsumerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for name in ('binding','report','analysis','out'):(self.root/name).mkdir()
        self.binding_path=self.root/'binding/savepoint-evidence.json'
        self.report_path=self.root/'report/savepoint-evidence.json'
        self.input_path=self.root/'analysis/analysis-inputs.json'
        self.input_raw=b'{"saved_input":"invented counts, never parsed"}\n'
        self.input_path.write_bytes(self.input_raw)
        self.input_pin=consumer._pin(self.input_raw)
        self.analysis_pin={'bytes':100,'sha256':'a'*64}
        self.closed={'bytes':99,'sha256':'b'*64}
        self.binding={**consumer.BOUNDARY,
            **{k:consumer.QUIET[k] for k in ('bootstrap_performed','formal_permission','promotion_allowed',
                'independent_s6_complete','performance_status','selected_candidate')},
            'format':'anomaly-v03-consumer-analysis-binding-v1','status':'historical_analysis_inputs_bound',
            'mode':consumer.MODE,'chunks':120,'evaluations':720,'analysis_input_bytes_verified':True,
            'publication_metadata_binding_verified':True,'historical_aggregate_authentication_reused':True,
            'historical_diagnostic_join_reused':True,'source_payload_bytes_read':0,'new_evaluations':0,
            'score_recalculations':0,'aggregate_recalculations':0,'closed_pin':self.closed,
            'analysis_input_reference':{'path':str(self.input_path),**self.input_pin},
            'authenticated_files':{str(self.input_path):self.input_pin},
            'external_anchors':{'analysis':self.analysis_pin},
            'attempts_used':[{'chunk_index':119,'attempt':2,'prior_attempts_not_credited':1}],
            'failed_attempts_retained':1,'undefined_input_metrics_retained':46}
        self.report={**consumer.QUIET,'format':'anomaly-v03-dev-smoke-descriptive-report-v1',
            'scope':'saved-dev-smoke-descriptive-only','bootstrap_replicates':0,
            'authentication':{'trust_anchor':{'path':str(self.input_path.parent/'savepoint-evidence.json'),**self.analysis_pin},
                'files':{str(self.input_path):self.input_pin,str(self.input_path.parent/'savepoint-evidence.json'):self.analysis_pin},
                'source_payload_bytes_read':0},
            'cohorts':[{'role':r,'seed_count':s,'evaluations':n,'candidate_tables':[{'saved_null':None} for _ in range(9)]}
                for r,s,n in (('dev',8,576),('smoke',2,144))]}
        self.report_text={'report.md':b'# Saved report\n','report.html':b'<!doctype html><p>Saved report</p>\n'}
        self.bound_save={'format':'anomaly-v03-consumer-analysis-binding-savepoint-v1',
            'status':'consumer_analysis_provenance_binding_completed','mode':consumer.MODE,
            'engineering_chunks':120,'engineering_evaluations':720,'formal_permission':False,
            'boundaries':{'closed':self.closed}}
        self.report_save={**consumer.QUIET,'format':'anomaly-v03-descriptive-report-savepoint-v1',
            'status':'descriptive_reports_completed','evaluations':720,'cohorts':2,'candidate_tables':18,
            'primary_metrics_verified':234,'diagnostic_rows_verified':5670,'boundaries':{'closed':self.closed},
            'prior_input_manifest':self.analysis_pin}
        self.save()

    def save(self):
        def write(path,value):
            raw=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
            path.write_bytes(raw);return consumer._pin(raw)
        self.bound_save['artifacts']={'analysis-binding.json':write(self.binding_path.parent/'analysis-binding.json',self.binding)}
        self.binding_pin=write(self.binding_path,self.bound_save)
        pins={'report.json':write(self.report_path.parent/'report.json',self.report)}
        for name,raw in self.report_text.items():
            (self.report_path.parent/name).write_bytes(raw);pins[name]=consumer._pin(raw)
        self.report_save.update(artifacts=pins,report_files=pins,report_pin=pins['report.json'])
        self.report_pin=write(self.report_path,self.report_save)

    def call(self,publish=False,**kwargs):
        params={'expected_mode':consumer.MODE,'expected_binding_pin':self.binding_pin,'expected_report_pin':self.report_pin}|kwargs
        if publish:
            return consumer.run_engineering_consumer(self.binding_path,self.report_path,self.input_path,
                output_parent=self.root/'out',output_name='result',**params)
        return consumer.prepare_engineering_result(self.binding_path,self.report_path,self.input_path,**params)

    def test_selection_opens_only_seven_pinned_files_without_recalculation(self):
        allowed={self.binding_path,self.report_path,self.input_path,self.binding_path.parent/'analysis-binding.json',
                 *(self.report_path.parent/n for n in consumer.REPORT_LIMITS)}
        original=Path.open;opened=[]
        def guard(path,*args,**kwargs):
            self.assertIn(path,allowed);self.assertEqual(args,('rb',));opened.append(path)
            return original(path,*args,**kwargs)
        with ExitStack() as stack:
            stack.enter_context(patch.object(Path,'open',guard))
            for target in ('subprocess.Popen','banto_ai.anomaly_v03_descriptive_report.build_report',
                'banto_ai.anomaly_v03_descriptive_report.validate_report','banto_ai.anomaly_v03_analysis_inputs.join_inputs'):
                stack.enter_context(patch(target,side_effect=AssertionError('numerical replay')))
            files,receipt=self.call()
        self.assertEqual(set(opened),allowed);self.assertEqual(len(opened),7)
        self.assertEqual(json.loads(files['report.json']),self.report)
        self.assertEqual(receipt['attempts_used'],self.binding['attempts_used'])
        self.assertEqual(receipt['undefined_input_metrics_retained'],46)
        self.assertEqual(receipt['report_value_recalculations'],0)
        for key in consumer.BOUNDARY:self.assertIs(receipt[key],False)

    def test_formal_rejected_before_io(self):
        with patch.object(consumer.io,'regular_path',side_effect=AssertionError('IO')):
            for mode in ('formal','fixture',None):
                with self.assertRaises(ValueError):self.call(expected_mode=mode)

    def test_both_external_pins_required(self):
        for key in ('expected_binding_pin','expected_report_pin'):
            with self.subTest(key=key),self.assertRaises(ValueError):
                self.call(**{key:{'bytes':1,'sha256':'0'*64}})

    def test_input_bytes_changed_no_output_created(self):
        self.input_path.write_bytes(self.input_raw.replace(b'counts',b'Counts'))
        with self.assertRaises(ValueError):self.call(publish=True)
        self.assertEqual(list((self.root/'out').iterdir()),[])

    def test_saved_input_path_not_followed(self):
        self.binding['analysis_input_reference']['path']=str(self.root/'unrelated/missing.json');self.save()
        original=consumer.pinned.read_pinned;reads=[]
        def read(path,*args):reads.append(path);return original(path,*args)
        with patch.object(consumer.pinned,'read_pinned',read),self.assertRaises(ValueError):self.call()
        self.assertNotIn(self.root/'unrelated/missing.json',reads)
        self.assertNotIn(self.input_path,reads)

    def test_report_refers_to_different_input(self):
        self.report['authentication']['files'][str(self.input_path)]={'bytes':1,'sha256':'c'*64};self.save()
        with self.assertRaises(ValueError):self.call()

    def test_report_refers_to_different_analysis_anchor(self):
        self.report_save['prior_input_manifest']={'bytes':101,'sha256':'d'*64};self.save()
        with self.assertRaises(ValueError):self.call()

    def test_different_campaign_rejected(self):
        self.report_save['boundaries']={'closed':{'bytes':99,'sha256':'c'*64}};self.save()
        with self.assertRaises(ValueError):self.call()

    def test_binding_cannot_upgrade_acceptance(self):
        self.binding['full_payload_bytes_verified']=True;self.save()
        with self.assertRaises(ValueError):self.call()

    def test_report_cannot_upgrade_to_formal(self):
        self.report['formal_permission']=True;self.save()
        with self.assertRaises(ValueError):self.call()

    def test_changed_html_rejected(self):
        (self.report_path.parent/'report.html').write_bytes(b'changed\n')
        with self.assertRaises(ValueError):self.call()

    def test_missing_html_final_lf_only_is_added(self):
        self.report_text['report.html']=b'<!doctype html><p>Saved report</p>';self.save()
        files,receipt=self.call()
        self.assertEqual(files['report.html'],self.report_text['report.html']+b'\n')
        self.assertEqual(receipt['report_files']['report.html'],consumer._pin(files['report.html']))

    def test_oversized_pin_rejected_before_read(self):
        self.binding['analysis_input_reference']['bytes']=8*consumer.MIB+1
        self.binding['authenticated_files'][str(self.input_path)]={k:self.binding['analysis_input_reference'][k] for k in ('bytes','sha256')}
        self.save()
        with self.assertRaisesRegex(ValueError,'file size limit'):self.call()

    def test_publish_readback_preserves_values_text_and_refuses_overwrite(self):
        result=self.call(publish=True);root=Path(result['output_path'])
        self.assertTrue(result['local_verified']);self.assertFalse(result['formal_permission'])
        self.assertEqual(result['payloads'],4)
        self.assertEqual(json.loads((root/'payload/report.json').read_bytes()),self.report)
        for name,raw in self.report_text.items():self.assertEqual((root/'payload'/name).read_bytes(),raw)
        before={p.relative_to(root):p.read_bytes() for p in root.rglob('*') if p.is_file()}
        with self.assertRaises(FileExistsError):self.call(publish=True)
        self.assertEqual(before,{p.relative_to(root):p.read_bytes() for p in root.rglob('*') if p.is_file()})

    def test_failed_write_retained_without_completion(self):
        original=consumer.io.LocalPublication.write
        def fail(store,name,raw):
            if name=='report.md':raise OSError('injected write failure')
            return original(store,name,raw)
        with patch.object(consumer.io.LocalPublication,'write',fail),self.assertRaises(OSError):self.call(publish=True)
        root=self.root/'out/result'
        self.assertTrue((root/'stage/report.json').is_file());self.assertFalse((root/'.complete').exists())

    def test_cli_reports_publication_and_error_exit(self):
        args=['--mode',consumer.MODE,'--binding-savepoint',str(self.binding_path),'--report-savepoint',str(self.report_path),
            '--analysis-input',str(self.input_path),'--output-parent',str(self.root/'out'),'--output-name','cli',
            '--binding-bytes',str(self.binding_pin['bytes']),'--binding-sha256',self.binding_pin['sha256'],
            '--report-bytes',str(self.report_pin['bytes']),'--report-sha256',self.report_pin['sha256']]
        out=io.StringIO()
        with redirect_stdout(out):self.assertEqual(consumer.main(args),0)
        self.assertTrue(json.loads(out.getvalue())['local_verified'])
        with redirect_stderr(io.StringIO()),self.assertRaises(SystemExit) as error:consumer.main(args)
        self.assertEqual(error.exception.code,2)


if __name__=='__main__':unittest.main()
