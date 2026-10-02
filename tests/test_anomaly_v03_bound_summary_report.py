"""Descriptive rendering from invented retained tables, not new performance."""
import copy
from contextlib import ExitStack
from html.parser import HTMLParser
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_bound_summary_report as mapper
from tests import test_anomaly_v03_bound_summary_tables as prior

pin=mapper._pin
encode=mapper._json


class HtmlCounts(HTMLParser):
    def __init__(self):super().__init__();self.tags={};self.text=[]
    def handle_starttag(self,tag,attrs):self.tags[tag]=self.tags.get(tag,0)+1
    def handle_data(self,data):self.text.append(data)


class BoundSummaryReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prior.BoundSummaryTablesTests.setUpClass()
        cls.value=prior.BoundSummaryTablesTests.output;cls.raw=encode(cls.value)
        cls.schema=(Path(__file__).resolve().parents[1]/mapper.report.inputs.SCHEMA).read_bytes()
        with ExitStack() as stack:
            for target in ('builtins.open','io.open','subprocess.Popen',
                           'banto_ai.anomaly_v03_bound_summary_tables.aggregate_bound_summaries',
                           'banto_ai.anomaly_v03_summary_coverage.bind_summary_coverage',
                           'banto_ai.anomaly_v03_seed_aggregate.aggregate_evaluations',
                           'banto_ai.anomaly_v03_checkpoints.reduce_journal',
                           'banto_ai.anomaly_v03_score_audit.audit_score_derivation',
                           'banto_ai.anomaly_v03_ledger_audit.audit_evaluation',
                           'banto_ai.anomaly_v03_inference_audit.draw_index'):
                stack.enter_context(patch(target,side_effect=AssertionError('forbidden '+target)))
            stack.enter_context(patch.object(Path,'read_bytes',side_effect=AssertionError('file read')))
            cls.files,cls.receipt=mapper.prepare_bound_report(cls.raw,cls.schema,
                expected_tables_pin=pin(cls.raw),expected_schema_pin=pin(cls.schema),expected_mode='fixture')

    def call(self,value=None,**overrides):
        raw=self.raw if value is None else encode(value)
        return mapper.prepare_bound_report(raw,self.schema,**({'expected_tables_pin':pin(raw),
            'expected_schema_pin':pin(self.schema),'expected_mode':'fixture'}|overrides))

    def test_complete_four_payloads_and_cell_inventory(self):
        self.assertEqual(set(self.files),set(mapper.PAYLOAD_LIMITS))
        self.assertEqual([self.receipt['checks'][k] for k in ('cohorts','candidate_tables','primary_metrics','diagnostic_rows')],[2,18,234,5670])
        for name,raw in self.files.items():
            self.assertTrue(raw.endswith(b'\n'));self.assertNotIn(b'\r',raw)
            self.assertLessEqual(len(raw),mapper.PAYLOAD_LIMITS[name]);raw.decode('utf-8')
        for name,p in self.receipt['report_files'].items():self.assertEqual(pin(self.files[name]),p)
        self.assertEqual(json.loads(self.files['consumer-receipt.json']),self.receipt)

    def test_hand_count_nulls_and_cohorts_remain_distinct(self):
        packet=json.loads(self.files['report.json']);dev,smoke=packet['cohorts']
        self.assertEqual([(c['role'],c['seed_count'],c['evaluations']) for c in packet['cohorts']],[('dev',8,576),('smoke',2,144)])
        m=dev['candidate_tables'][0]['metrics']
        self.assertEqual((m['sensor_recall']['numerator'],m['sensor_recall']['denominator']),(1,960))
        self.assertEqual(m['precision']['value'],1.0);self.assertEqual(m['delay_summary']['median'],1.0)
        self.assertIsNone(smoke['candidate_tables'][0]['metrics']['precision']['value'])
        self.assertTrue(any(t['profile_status']=='inconclusive' for t in smoke['candidate_tables']))
        self.assertEqual(self.receipt['source_lineage']['zero_denominator_input_metrics'],719)

    def test_original_lineage_failure_history_and_formal_gaps_preserved(self):
        packet=json.loads(self.files['report.json'])
        for key in ('binding_pin','metadata_pin','journal_bindings','completed_savepoint_pin','evidence_pin',
                    'source_summaries','coverage','failed_attempt_history','zero_denominator_input_metrics'):
            self.assertEqual(packet['source_lineage'][key],self.value[key])
        self.assertEqual(packet['formal_fields'],dict.fromkeys(('status','provenance','analysis_consumer','bootstrap')))
        self.assertFalse(packet['formal_readiness']['formal_ready'])
        for key,value in mapper.CLOSED.items():self.assertEqual(packet[key],value);self.assertEqual(self.receipt[key],value)
        self.assertEqual(self.receipt['aggregate_recalculations'],0)
        self.assertEqual(self.receipt['report_mapping_runs'],1)
        self.assertEqual(self.receipt['report_cell_validation_runs'],1)
        self.assertEqual(encode(self.value),self.raw)

    def test_fixture_is_explicit_in_both_views_and_html_has_no_scripts(self):
        markdown=self.files['report.md'].decode();html=self.files['report.html'].decode()
        for text in (markdown,html):
            self.assertIn('架空データ',text);self.assertIn('実際の検出性能を示す結果ではありません',text)
            self.assertIn('架空要約720枠',text);self.assertNotIn('保存済み720評価',text)
            self.assertIn('判定不能を含む評価は1件',text);self.assertIn('—',text)
        parser=HtmlCounts();parser.feed(html)
        self.assertEqual(parser.tags['details'],18);self.assertEqual(parser.tags['table'],54)
        self.assertEqual(parser.tags['tr'],2610);self.assertNotIn('script',parser.tags)

    def test_formal_unknown_rejected_before_decode(self):
        with patch.object(mapper.binding,'_load',side_effect=AssertionError('decode')):
            for mode in ('formal','holdout',None,True):
                with self.subTest(mode=mode),self.assertRaises(ValueError):
                    mapper.prepare_bound_report(None,None,expected_tables_pin=None,expected_schema_pin=None,expected_mode=mode)

    def test_external_table_and_schema_pins_cannot_be_replaced(self):
        for args in ({'expected_tables_pin':pin(b'wrong')},{'expected_schema_pin':pin(b'wrong')}):
            with self.subTest(args=args),self.assertRaises(ValueError):self.call(**args)

    def test_missing_incomplete_promoted_or_wrong_population_fails_before_mapping(self):
        for kind in ('missing','incomplete','formal','selection','population','mode'):
            value=copy.deepcopy(self.value)
            if kind=='missing':value['by_role'].pop()
            if kind=='incomplete':value['coverage'].update(success=718,failed=1)
            if kind=='formal':value['formal_permission']=True
            if kind=='selection':value['selected_candidate']='c1-phase-level'
            if kind=='population':value['by_role'][0]['role']='holdout'
            if kind=='mode':value['mode']='engineering'
            with self.subTest(kind=kind),patch.object(mapper.report,'build_report',side_effect=AssertionError('mapper')), \
                 self.assertRaises(ValueError):self.call(value)

    def test_resealed_point_or_diagnostic_mismatch_is_rejected(self):
        for kind in ('point','delay','profile'):
            value=copy.deepcopy(self.value);row=value['by_role'][0]
            if kind=='point':row['points']['sensor_recall']=.9
            if kind=='delay':row['delay_summary']['median']=5
            if kind=='profile':row['profile_diagnostics']=[{'evaluation_id':'wrong','profiles':[]}]
            with self.subTest(kind=kind),self.assertRaises(ValueError):self.call(value)

    def test_engineering_presentation_keeps_mode_without_fixture_relabelling(self):
        value=copy.deepcopy(self.value);value['mode']='engineering'
        files,receipt=self.call(value,expected_mode='engineering')
        self.assertEqual(receipt['data_origin'],'saved-dev-smoke-compact-summaries')
        self.assertNotIn('架空データ',files['report.md'].decode())
        self.assertIn('保存済み720評価',files['report.md'].decode())
        self.assertFalse(receipt['result_trusted']);self.assertFalse(receipt['published'])

    def test_oversize_or_render_failure_does_not_return_partial_payloads(self):
        with patch.object(mapper.report,'detailed_html',side_effect=ValueError('render stopped')),self.assertRaisesRegex(ValueError,'render stopped'):
            self.call()
        with patch.object(mapper.report,'summary_markdown',return_value='保存済み720評価'+('a'*mapper.PAYLOAD_LIMITS['report.md'])),self.assertRaisesRegex(ValueError,'bounded UTF-8/LF'):
            self.call()


if __name__=='__main__':unittest.main()
