import copy
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from banto_ai import anomaly_v03_descriptive_report as report
from test_anomaly_v03_analysis_inputs import fixture


class TableParser(HTMLParser):
    def __init__(self):super().__init__();self.counts={};self.text=[]
    def handle_starttag(self,tag,attrs):self.counts[tag]=self.counts.get(tag,0)+1
    def handle_data(self,data):self.text.append(data)


class DescriptiveReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[1]
        cls.schema=json.loads((cls.root/report.inputs.SCHEMA).read_text())
        source=report.inputs.join_inputs(*fixture())
        source['status']='authenticated_dev_smoke_analysis_inputs'
        source['readiness']=report.inputs.formal_readiness(cls.schema)
        for t in source['by_role']:t['seeds']=8 if t['role']=='dev' else 2
        cls.source=source;cls.packet=report.build_report(source,cls.schema)

    def test_complete_mapping_zero_nulls_and_input_unchanged(self):
        before=copy.deepcopy(self.source);p=report.build_report(self.source,self.schema)
        self.assertEqual(self.source,before)
        stats=report.validate_report(p,self.source,self.schema)
        self.assertEqual((stats['candidate_tables'],stats['primary_metrics'],stats['diagnostic_rows']),(18,234,5670))
        m=p['cohorts'][0]['candidate_tables'][0]['metrics']
        self.assertEqual(m['machine_recall']['denominator'],960)
        self.assertEqual(m['availability'][0]['metric']['denominator'],172800)
        self.assertIsNone(m['precision']['value']);self.assertEqual(m['precision']['ci_status'],'not_evaluated')
        zero=next(r for r in p['cohorts'][0]['diagnostic_series']['incident-recall'] if not r['planned_count'])
        self.assertIsNone(zero['metric']['value']);self.assertEqual(zero['metric']['ci_status'],'not_applicable')

    def test_offsets_keep_reference_omissions_and_scored_denominator(self):
        c=self.packet['cohorts'][0]
        offset=next(r for r in c['diagnostic_series']['score-availability'] if r['dimension']=='event-offset')
        self.assertEqual((offset['planned_count'],offset['actual_count'],offset['metric']['denominator']),(3840,2880,2880))
        missing=next(r for r in c['diagnostic_details'][0]['score_reference_coverage'] if r['dimension']=='event-offset')
        self.assertEqual(missing['unscored_target'],960)
        self.assertFalse(self.packet['column_mapping']['event_offset_partition'])
        self.assertEqual(self.packet['column_mapping']['class_precision'],'not_applicable')

    def test_three_score_diagnostics_stay_distinct(self):
        c=self.packet['cohorts'][0]
        self.assertEqual(c['diagnostic_series']['score-availability'][0]['metric']['value'],1.)
        self.assertEqual(c['diagnostic_series']['score-threshold-exceedance'][0]['metric']['value'],0.)
        self.assertEqual(c['diagnostic_series']['score-signal-onset'][0]['metric']['value'],0.)

    def test_output_cell_loss_reorder_and_tamper_rejected(self):
        for mutation in ('missing','duplicate','reorder','ratio','omission','delay','gates','selection','formal'):
            p=copy.deepcopy(self.packet);c=p['cohorts'][0]
            if mutation=='missing':c['diagnostic_series']['score-availability'].pop()
            elif mutation=='duplicate':c['diagnostic_series']['incident-recall'][1]=c['diagnostic_series']['incident-recall'][0]
            elif mutation=='reorder':c['diagnostic_details'].reverse()
            elif mutation=='ratio':c['candidate_tables'][0]['metrics']['machine_recall']['value']=.1
            elif mutation=='omission':c['diagnostic_details'][0]['score_reference_coverage'][-1]['outside_test']=1
            elif mutation=='delay':c['diagnostic_details'][0]['delay_histogram'][0]=1
            elif mutation=='gates':c['candidate_tables'][0]['qualified']=True
            elif mutation=='selection':p['selected_candidate']='c1-phase-level'
            else:p['formal_document_emitted']=True
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):report.validate_report(p,self.source,self.schema)

    def test_source_wrong_role_or_incomplete_rejected(self):
        for mutation in ('missing','holdout','ci','seeds'):
            source=copy.deepcopy(self.source)
            if mutation=='missing':source['by_role'].pop()
            elif mutation=='holdout':source['by_role'][0]['role']='holdout'
            elif mutation=='ci':source['bootstrap_performed']=True
            else:source['by_role'][0]['seeds']=40
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):report.build_report(source,self.schema)

    def test_json_roundtrip_and_static_presentations(self):
        p=json.loads(json.dumps(self.packet,sort_keys=True))
        report.validate_report(p,self.source,self.schema)
        text=report.summary_markdown(p);html=report.detailed_html(p);parser=TableParser();parser.feed(html)
        self.assertIn('576評価',text);self.assertIn('144評価',text);self.assertIn('—',text)
        self.assertEqual(parser.counts['details'],18);self.assertEqual(parser.counts['table'],54)
        self.assertEqual(parser.counts['tr'],2610)
        self.assertNotIn('script',parser.counts)
        self.assertIn('信頼区間・正式性能判定・候補採択は未実施',text)

    def test_html_escapes_labels(self):
        p=copy.deepcopy(self.packet);p['cohorts'][0]['candidate_tables'][0]['candidate_id']='<script>alert(1)</script>'
        html=report.detailed_html(p)
        self.assertIn('&lt;script&gt;',html);self.assertNotIn('<script>',html)

    def test_metric_units_by_hand(self):
        self.assertEqual(report.metric(1,3600,'clean_rate')['value'],8)
        self.assertEqual(report.metric(3,20,'false_alert_burden')['value'],15)
        self.assertEqual(report.metric(3,20)['value'],.15)
        self.assertEqual(report.display(.125,percent=True),'12.50%')
        self.assertEqual(report.display(None),'—')

    def test_authenticated_compact_io_rejects_hash_mismatch(self):
        def pin(path):
            raw=path.read_bytes();return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);payload=root/'analysis-inputs.json';payload.write_text(json.dumps(self.source),encoding='utf-8')
            code={f'src/banto_ai/{name}':pin(self.root/'src/banto_ai'/name) for name in
                ('anomaly_v03_analysis_inputs.py','anomaly_v03_slices.py','anomaly_v03.py','anomaly_v03_inference_audit.py')}
            code[report.inputs.SCHEMA]=pin(self.root/report.inputs.SCHEMA)
            manifest={**report.QUIET,'status':'authenticated_analysis_inputs_completed','evaluations':720,
                      'analysis_inputs_pin':pin(payload),'artifacts':{'analysis-inputs.json':pin(payload)},'code_pins':code}
            path=root/'savepoint.json';path.write_text(json.dumps(manifest),encoding='utf-8');root_pin=pin(path)
            with mock.patch.object(report,'read_pinned',wraps=report.read_pinned) as reader:
                p,checks=report.authenticate_report(path,root_pin['sha256'],self.root/report.inputs.SCHEMA)
            self.assertEqual(reader.call_count,7)
            self.assertEqual(len(p['authentication']['files']),3)
            self.assertEqual(p['authentication']['source_payload_bytes_read'],0)
            self.assertEqual(checks['diagnostic_rows'],5670)
            with self.assertRaises(ValueError):report.authenticate_report(path,'0'*64,self.root/report.inputs.SCHEMA)
            payload.write_text('{}')
            with self.assertRaises(ValueError):report.authenticate_report(path,root_pin['sha256'],self.root/report.inputs.SCHEMA)


if __name__=='__main__':unittest.main()
