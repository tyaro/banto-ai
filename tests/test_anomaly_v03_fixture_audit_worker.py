"""Actual owned audit process and binding failures, with invented prior receipts."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from banto_ai import anomaly_v03_fixture_audit_worker as worker
from tests import test_anomaly_v03_fixture_numeric_audit as hand
from tests import test_anomaly_v03_consumer_evidence as supplied


def write_request(parent, revision, fixture, document, *, real_analysis=None):
    parent.mkdir()
    raw_input = worker.v.canonical_json(fixture);raw_document = worker.v.canonical_json(document)
    if real_analysis is None:
        # Deliberately invented prior analysis receipts for unit tests only.
        record = supplied.case(role='analysis')['evidence']
        record['inputs'] = {'fixture/input.json':worker.observed._pin(raw_input)}
        record['outputs'] = {'fixture/document.json':worker.observed._pin(raw_document)}
        raw_record = worker.io.json_bytes(record)
        result = {'format':'anomaly-v03-fixture-worker-check-v1','status':'verified','role':'analysis','mode':'fixture',
            'operation':'assemble-invented-document-v1','fixture_inference_performed':True,'worker_exit_confirmed':True,
            'new_evaluations':0,'formal_permission':False,'registered_data_read':False,'worker_pid':record['process']['pid'],
            'evidence_pin':worker.observed._pin(raw_record),'document_pin':worker.observed._pin(raw_document),
            'computation':{'fixture_only':True,'clusters':40,'replicates':len(fixture['draws'])}}
        raw_result = worker.io.json_bytes(result)
    else:
        raw_result,raw_record = real_analysis
        record = worker.v.strict_json(raw_record)
    reference = {'result_pin':worker.observed._pin(raw_result),'evidence_pin':worker.observed._pin(raw_record),
                 'source_revision':record['source_before']['revision']}
    files = {'fixture/input.json':raw_input,'fixture/document.json':raw_document,'analysis/result.json':raw_result,
        'analysis/evidence.json':raw_record,'fixture/audit-operation.json':worker.v.canonical_json(worker.operation_descriptor(revision,reference))}
    records = {}
    for name,raw in files.items():
        path = parent/name.replace('/','-');path.write_bytes(raw)
        records[name] = {'path':str(path),'pin':worker.observed._pin(raw),'links':1}
    return {'format':worker.FORMAT,'mode':'fixture','role':'audit','operation':worker.OPERATION,'inputs':records,'analysis_reference':reference}


@unittest.skipUnless(os.name == 'nt' and sys.version_info[:2] == (3,14),'Windows CPython 3.14 observation')
class AuditWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = hand.hand.hand.invented_input();cls.document = hand.connected(cls.fixture)
        cls.revision = subprocess.check_output(['git','-C',str(worker.ROOT),'rev-parse','HEAD'],text=True).strip()

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='banto-primary-audit-');self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve();self.receipts = self.root/'receipts';self.receipts.mkdir()
        self.request = write_request(self.root/'inputs',self.revision,self.fixture,self.document)

    def run_audit(self,request=None):
        return worker.audit_with_evidence(self.request if request is None else request,
            expected_revision=self.revision,receipt_parent=self.receipts,receipt_name='audit')

    def test_actual_audit_succeeds_without_parent_numerical_recomputation(self):
        with patch.object(worker.numeric,'audit_primary_document',side_effect=AssertionError('parent audit')):
            result = self.run_audit()
        self.assertEqual(result['status'],'verified',result)
        self.assertTrue(result['fixture_numerical_audit_performed']);self.assertTrue(result['worker_exit_confirmed'])
        self.assertEqual((result['selected_source_files'],result['runtime_files'],result['retained_input_files']),(14,2,5))
        self.assertTrue(result['resource_budget_passed'])
        path = Path(result['check_directory'])/'payload/primary-audit.json'
        self.assertEqual(worker.observed._pin(path.read_bytes()),result['audit_pin'])
        for key,value in worker.numeric.CLOSED.items():self.assertEqual(result[key],value)

    def test_resealed_numerical_mutation_fails_in_actual_child(self):
        doc = copy.deepcopy(self.document)
        for tables in (doc['document_draft']['candidate_tables'],doc['fixture_packet']['fixture_candidate_tables']):
            tables[3]['metrics']['machine_recall']['ci_lower'] += .001
        request = write_request(self.root/'mutated-inputs',self.revision,self.fixture,doc)
        result = self.run_audit(request)
        self.assertEqual(result['status'],'failed');self.assertTrue(result['worker_exit_confirmed'])
        path = Path(result['check_directory']);monitor = json.loads((path/'supervision.json').read_text(encoding='utf-8'))
        self.assertEqual(monitor['exit_code'],2)
        self.assertIn('primary tables differs',(path/'worker/report.json').read_text(encoding='utf-8'))
        self.assertFalse((path/'payload').exists())

    def test_formal_role_and_operation_rejected_before_io(self):
        for key,value in [('mode','formal'),('role','analysis'),('operation','assemble-invented-document-v1')]:
            request = copy.deepcopy(self.request);request[key] = value
            with self.subTest(key=key),patch.object(worker.io,'_local_parent',side_effect=AssertionError('IO')):
                with self.assertRaises(ValueError):self.run_audit(request)

    def test_external_analysis_reference_not_inferred_from_record(self):
        request = copy.deepcopy(self.request);request['analysis_reference']['result_pin']['sha256'] = 'f'*64
        with patch.object(worker.io,'_local_parent',side_effect=AssertionError('IO')):
            with self.assertRaisesRegex(ValueError,'external analysis reference'):self.run_audit(request)

    def test_original_input_mismatch_stops_before_launch(self):
        row = self.request['inputs']['fixture/input.json'];path = Path(row['path'])
        value = json.loads(path.read_text(encoding='utf-8'));value['engineering_ready_assumption'] = False
        raw = worker.v.canonical_json(value);path.write_bytes(raw);row['pin'] = worker.observed._pin(raw)
        with patch.object(worker.supervisor,'supervise',side_effect=AssertionError('launch')):result = self.run_audit()
        self.assertEqual(result['status'],'failed');self.assertIn('numeric input pin',result['detail'])

    def test_resealed_wrong_audit_role_rejected_after_actual_exit(self):
        original = worker.supervisor.supervise
        def alter(*args,**kwargs):
            monitor = original(*args,**kwargs);self.assertEqual(monitor['status'],'complete',monitor)
            path = args[2]/'report.json';reply = json.loads(path.read_text(encoding='utf-8'))
            reply['evidence']['role'] = 'analysis';raw = worker.io.json_bytes(reply);path.write_bytes(raw)
            monitor['output'] = worker.observed._pin(raw);return monitor
        with patch.object(worker.supervisor,'supervise',side_effect=alter):result = self.run_audit()
        self.assertEqual(result['status'],'failed');self.assertIn('role',result['detail'])

    def test_unreaped_owner_survives_save_failure(self):
        owner = object();error = worker.supervisor.UnreapedWorker(owner,{'worker_exit_confirmed':False})
        save = worker.observed._save
        def broken(path,value):
            if path.name == 'supervision.json':raise OSError('save failed')
            return save(path,value)
        with patch.object(worker.supervisor,'supervise',side_effect=error),patch.object(worker.observed,'_save',side_effect=broken):
            with self.assertRaises(worker.supervisor.UnreapedWorker) as caught:self.run_audit()
        self.assertIs(caught.exception.process,owner)

    def test_failed_supervision_does_not_consume_worker_output(self):
        monitor = {'status':'failed','worker_exit_confirmed':True,'worker_pid':12345,'stop_reason':'private_bytes_limit'}
        with patch.object(worker.supervisor,'supervise',return_value=monitor):result = self.run_audit()
        self.assertEqual(result['status'],'failed');self.assertFalse(result['fixture_numerical_audit_performed'])
        self.assertFalse((Path(result['check_directory'])/'evidence.json').exists())

    def test_existing_receipt_never_overwritten(self):
        target = self.receipts/'audit';target.mkdir();(target/'keep').write_bytes(b'evidence')
        with self.assertRaises((ValueError,OSError)):self.run_audit()
        self.assertEqual((target/'keep').read_bytes(),b'evidence')


if __name__ == '__main__':unittest.main()
