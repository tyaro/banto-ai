"""Exercise stage selection and immutable checkpoints with invented compact counts."""
import copy
from contextlib import ExitStack,redirect_stdout
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_saved_report_pipeline as pipeline
from tests import test_anomaly_v03_bound_summary_tables as fixture

encode=pipeline.io.json_bytes;pin=pipeline.prepared._pin


@unittest.skipUnless(os.name=='nt','owned local Windows writer/reader')
class SavedReportPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='banto-saved-pipeline-');cls.addClassCleanup(cls.temp.cleanup)
        cls.root=Path(cls.temp.name);source=cls.root/'source';source.mkdir()
        meta=fixture.fixture.fixture_metadata();summaries={};refs=[]
        for index in range(120):
            value=fixture.fixture.fixture_report(meta,index)
            if index==0:
                row,audit=fixture.detected_template();old=value['evaluations'][0]
                row['input_hashes']=old['input_hashes'];row['evaluation_pin']=old['evaluation_pin']
                value['evaluations'][0]=row;value['audit']['evaluations'][0]=audit
            raw=encode(value);summaries[index]=raw
            path=source/f'{index:03d}.json';path.write_bytes(raw);refs.append({'path':str(path),'pin':pin(raw)})
        raw=encode(meta)
        bound=fixture.tables.binding.bind_summary_coverage(raw,summaries,expected_mode='fixture',expected_metadata_pin=pin(raw),
            expected_summary_pins={i:pin(b) for i,b in summaries.items()},expected_savepoint_pin=fixture.fixture.SAVEPOINT,
            expected_evidence_pin=fixture.fixture.EVIDENCE)
        raw=encode(bound);bp=source/'binding.json';bp.write_bytes(raw)
        schema=Path(__file__).resolve().parents[1]/pipeline.prepared.report.inputs.SCHEMA
        cls.request={'format':pipeline.REQUEST_FORMAT,'mode':'fixture','start_from':'summaries','inputs':{
            'binding':{'path':str(bp),'pin':pin(raw)},'summaries':refs,'schema':{'path':str(schema),'pin':pin(schema.read_bytes())}}}
        del meta,summaries,raw,bound,value
        cls.initial=pipeline.run_pipeline(cls.request,output_parent=cls.root,output_name='initial')
        if cls.initial['status']!='verified':raise AssertionError(cls.initial)
        cls.checkpoints={n:json.loads(Path(r['path']).read_bytes()) for n,r in cls.initial['checkpoints'].items()}

    def run_stage(self,stage,name,**kw):
        request=copy.deepcopy(self.request if stage=='summaries' else self.checkpoints[stage])
        return pipeline.run_pipeline(request,output_parent=self.root,output_name=name,**kw)

    def test_all_stages_run_once_under_shared_budget_and_keep_lineage(self):
        r=self.initial
        self.assertEqual([r[k] for k in ('aggregation_runs','report_runs','publication_runs')],[1,1,1])
        self.assertEqual(set(r['checkpoints']),{'tables','report','publication'})
        child=json.loads((self.root/'initial/publication/resource-budget.json').read_bytes())
        self.assertEqual(Path(child['shared_root']),self.root/'initial');self.assertTrue(child['passed'])
        source=json.loads((self.root/'initial/report/report.json').read_bytes())['source_lineage']
        self.assertEqual(source['binding_pin'],self.request['inputs']['binding']['pin'])
        self.assertEqual(len(source['source_summaries']),120);self.assertEqual(len(source['failed_attempt_history']),1)
        self.assertEqual(source['coverage']['inconclusive'],1);self.assertEqual(source['zero_denominator_input_metrics'],719)
        self.assertFalse(r['formal_permission'] or r['independent_numerical_audit_performed'])

    def test_tables_start_does_not_reaggregate(self):
        with patch.object(pipeline.tables,'aggregate_bound_summaries',side_effect=AssertionError('aggregate replay')):
            r=self.run_stage('tables','from-tables')
        self.assertEqual(r['status'],'verified',r)
        self.assertEqual([r[k] for k in ('aggregation_runs','report_runs','publication_runs')],[0,1,1])
        self.assertEqual(r['publication']['payload_pins'],self.initial['publication']['payload_pins'])

    def test_report_start_does_not_remap_or_reaggregate(self):
        with patch.object(pipeline.prepared,'prepare_bound_report',side_effect=AssertionError('map replay')):
            r=self.run_stage('report','from-report')
        self.assertEqual(r['status'],'verified',r)
        self.assertEqual([r[k] for k in ('aggregation_runs','report_runs','publication_runs')],[0,0,1])
        self.assertEqual(r['publication']['payload_pins'],self.initial['publication']['payload_pins'])

    def test_completed_publication_starts_no_process_or_calculation(self):
        with ExitStack() as stack:
            for target in ('subprocess.Popen','banto_ai.anomaly_v03_bound_report_publication.publish_and_check',
                'banto_ai.anomaly_v03_bound_summary_report.prepare_bound_report',
                'banto_ai.anomaly_v03_bound_summary_tables.aggregate_bound_summaries'):
                stack.enter_context(patch(target,side_effect=AssertionError(target)))
            r=self.run_stage('publication','reused')
        self.assertEqual(r['status'],'verified',r)
        self.assertEqual([r[k] for k in ('aggregation_runs','report_runs','publication_runs')],[0,0,0])
        self.assertTrue(r['publication']['historical_worker_evidence_reused'])
        self.assertFalse(r['publication']['current_worker_execution_verified'])
        self.assertFalse((self.root/'reused/publication').exists())

    def test_formal_missing_duplicate_and_oversized_request_reject_before_io(self):
        variants=[]
        for field,value in (('mode','formal'),('start_from','unknown')):
            r=copy.deepcopy(self.request);r[field]=value;variants.append(r)
        r=copy.deepcopy(self.request);r['inputs']['summaries'].pop();variants.append(r)
        r=copy.deepcopy(self.request);r['inputs']['summaries'][1]=r['inputs']['summaries'][0];variants.append(r)
        r=copy.deepcopy(self.request);r['inputs']['binding']['pin']['bytes']=True;variants.append(r)
        with patch.object(pipeline.io,'_local_parent',side_effect=AssertionError('IO')):
            for request in variants:
                with self.assertRaises(ValueError):pipeline.run_pipeline(request,output_parent=self.root,output_name='invalid')

    def test_bad_source_pin_stops_before_calculation(self):
        request=copy.deepcopy(self.checkpoints['tables']);request['inputs']['tables']['pin']['sha256']='0'*64
        with patch.object(pipeline.prepared,'prepare_bound_report',side_effect=AssertionError('started mapper')):
            r=pipeline.run_pipeline(request,output_parent=self.root,output_name='bad-pin')
        self.assertEqual(r['status'],'failed');self.assertEqual(r['report_runs'],0);self.assertEqual(r['publication_runs'],0)

    def test_publication_failure_preserves_report_checkpoint_for_explicit_resume(self):
        with patch.object(pipeline.publication,'publish_and_check',side_effect=OSError('stopped before writer')):
            r=self.run_stage('tables','stopped')
        self.assertEqual(r['status'],'failed');self.assertIn('report',r['checkpoints'])
        request=json.loads(Path(r['checkpoints']['report']['path']).read_bytes())
        with patch.object(pipeline.prepared,'prepare_bound_report',side_effect=AssertionError('report replay')):
            resumed=pipeline.run_pipeline(request,output_parent=self.root,output_name='continued')
        self.assertEqual(resumed['status'],'verified',resumed)
        self.assertEqual(resumed['publication']['payload_pins'],self.initial['publication']['payload_pins'])
        self.assertEqual(json.loads((self.root/'stopped/result.json').read_bytes())['status'],'failed')

    def test_promoted_or_incomplete_retained_completion_is_rejected(self):
        original=json.loads((self.root/'initial/publication/result.json').read_bytes())
        for key,value in (('formal_permission',True),('writer_reaped_before_reader_start',False),('resource_budget_passed',False)):
            directory=self.root/('altered-'+key);directory.mkdir();changed=copy.deepcopy(original);changed[key]=value
            raw=encode(changed);(directory/'result.json').write_bytes(raw)
            request=copy.deepcopy(self.checkpoints['publication']);request['inputs']={'directory':str(directory),'result_pin':pin(raw)}
            with patch.object(pipeline.publication,'_read',side_effect=AssertionError('read unaccepted result')):
                r=pipeline.run_pipeline(request,output_parent=self.root,output_name='rejected-'+key)
            self.assertEqual(r['status'],'failed')

    def test_budget_stop_blocks_stages_without_increasing_limits(self):
        limits=dict(pipeline.budgets.DEFAULTS,minimum_free_ram_bytes=2**60)
        with patch.object(pipeline.publication,'publish_and_check',side_effect=AssertionError('worker after stop')):
            r=self.run_stage('report','resource-stop',resource_limits=limits)
        self.assertEqual(r['status'],'failed');self.assertFalse(r['resource_budget_passed']);self.assertEqual(r['publication_runs'],0)

    def test_existing_and_source_overlap_are_rejected(self):
        with self.assertRaises(FileExistsError):self.run_stage('publication','initial')
        source=Path(self.checkpoints['publication']['inputs']['directory'])
        with self.assertRaises(ValueError):pipeline.run_pipeline(self.checkpoints['publication'],output_parent=source,output_name='overlap')

    def test_unreaped_worker_owner_propagates_and_checkpoint_remains(self):
        owner=object();error=pipeline.publication.supervisor.UnreapedWorker(owner,{'worker_exit_confirmed':False})
        with patch.object(pipeline.publication,'publish_and_check',side_effect=error):
            with self.assertRaises(pipeline.publication.supervisor.UnreapedWorker) as caught:self.run_stage('report','unreaped')
        self.assertIs(caught.exception.process,owner)
        self.assertTrue((self.root/'unreaped/unreaped.json').exists())
        self.assertTrue(Path(self.initial['checkpoints']['report']['path']).is_file())

    def test_cli_requires_external_request_pin_and_dispatches(self):
        ref=self.initial['checkpoints']['publication'];args=['--request',ref['path'],'--bytes',str(ref['pin']['bytes']),
            '--sha256',ref['pin']['sha256'],'--output-parent',str(self.root),'--output-name','cli']
        with patch.object(pipeline,'run_pipeline',return_value={'status':'verified'}) as call,redirect_stdout(io.StringIO()):
            self.assertEqual(pipeline.main(args),0)
        self.assertEqual(call.call_args.args[0],self.checkpoints['publication'])
        args[5]='0'*64
        with patch.object(pipeline,'run_pipeline',side_effect=AssertionError('unverified request')):
            with self.assertRaises(SystemExit) as result:pipeline.main(args)
        self.assertEqual(result.exception.code,2)
