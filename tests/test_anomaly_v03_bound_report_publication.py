"""Small storage fixtures, not numerical evaluation or a hostile-writer model."""
import copy
from contextlib import ExitStack
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_bound_report_publication as pub

pin=pub.prepared._pin;encode=pub.io.json_bytes
READINESS=pub.prepared.report.inputs.formal_readiness(pub.v.strict_json(
    (Path(__file__).resolve().parents[1]/pub.prepared.report.inputs.SCHEMA).read_bytes()))


def fixture(mode='fixture'):
    lineage={'coverage':{'success':719,'inconclusive':1},'failed_attempt_history':[{'attempt':1}],
        'source_summaries':[{'chunk_index':0,'opaque_path':'not-opened'}]}
    fields={**pub.prepared.CLOSED,'mode':mode,'formal_fields':pub.prepared.FORMAL_FIELDS,
        'formal_readiness':copy.deepcopy(READINESS),'source_lineage':lineage,
        'data_origin':'invented-compact-summaries' if mode=='fixture' else 'saved-dev-smoke-compact-summaries'}
    packet={**fields,'format':'anomaly-v03-dev-smoke-descriptive-report-v1'}
    files={'report.json':encode(packet),'report.md':'# 架空データ\n'.encode(),'report.html':'<h1>架空データ</h1>\n'.encode()}
    receipt={**fields,'format':pub.prepared.FORMAT,'status':'bound_summary_report_prepared',
        'report_files':{n:pin(raw) for n,raw in files.items()},'current_source_payloads_read':0,
        'aggregate_recalculations':0,'summary_binding_recalculations':0,'detector_recalculations':0,
        'ledger_recalculations':0,'report_mapping_runs':1,'report_cell_validation_runs':1}
    files['consumer-receipt.json']=encode(receipt)
    return files,{n:pin(raw) for n,raw in files.items()}


@unittest.skipUnless(os.name=='nt','ordinary Windows local storage')
class BoundReportPublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='banto-bound-report-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'source';self.source.mkdir()
        self.files,self.pins=fixture()
        for name,raw in self.files.items():(self.source/name).write_bytes(raw)

    def call(self,name='chain',**kw):
        args=dict(expected_mode='fixture',expected_payload_pins=self.pins,output_parent=self.root,output_name=name)
        args.update(kw);return pub.publish_and_check(self.source,**args)

    def local(self,name='saved'):
        r=pub.io.publish_local_result(self.root,name,self.files,
            verify_semantics=lambda f:pub._validate(dict(f),self.pins,'fixture'))
        return self.root/name,r['marker_raw_sha256']

    def test_owned_writer_exits_before_reader_and_source_is_unchanged(self):
        before={n:(pin((self.source/n).read_bytes()),(self.source/n).stat().st_mtime_ns) for n in self.files}
        r=self.call();self.assertEqual(r['status'],'verified',r)
        self.assertTrue(r['writer_reaped_before_reader_start'] and r['resource_budget_passed'])
        for role in ('writer','reader'):
            self.assertTrue(r[role]['worker_exit_confirmed']);self.assertNotEqual(r[role]['worker_pid'],os.getpid())
        self.assertEqual(r['reader']['source_lineage_pin'],r['writer']['source_lineage_pin'])
        self.assertEqual(r['payload_files'],4)
        for n,raw in self.files.items():
            self.assertEqual((self.root/'chain/published/payload'/n).read_bytes(),raw)
            self.assertEqual((pin((self.source/n).read_bytes()),(self.source/n).stat().st_mtime_ns),before[n])
        with self.assertRaises(FileExistsError):self.call()

    def test_metadata_validation_never_calls_mapper_aggregate_or_process(self):
        with ExitStack() as stack:
            for target in ('builtins.open','io.open','subprocess.Popen',
                'banto_ai.anomaly_v03_bound_summary_report.prepare_bound_report',
                'banto_ai.anomaly_v03_bound_summary_tables.aggregate_bound_summaries',
                'banto_ai.anomaly_v03_summary_coverage.bind_summary_coverage'):
                stack.enter_context(patch(target,side_effect=AssertionError(target)))
            checked=pub._validate(self.files,self.pins,'fixture')
        self.assertEqual(checked['output_bytes_verified'],sum(map(len,self.files.values())))
        for mode in ('engineering',):
            files,pins=fixture(mode);pub._validate(files,pins,mode)

    def test_formal_and_invalid_pins_reject_before_io(self):
        variants=[dict(expected_mode='formal'),dict(expected_mode=True)]
        for key,val in (('bytes',True),('bytes',9*1024**2),('sha256','x')):
            pins=copy.deepcopy(self.pins);pins['report.json'][key]=val;variants.append(dict(expected_payload_pins=pins))
        with patch.object(pub.io,'regular_path',side_effect=AssertionError('filesystem')):
            for kw in variants:
                with self.subTest(kw=kw),self.assertRaises(ValueError):self.call(**kw)

    def test_real_schema_readiness_shape_and_promoted_readiness(self):
        self.assertIn('formal_ready',READINESS);self.assertNotIn('ready',READINESS)
        pub._validate(self.files,self.pins,'fixture')
        files=dict(self.files)
        for name in ('report.json','consumer-receipt.json'):
            value=pub.v.strict_json(files[name]);value['formal_readiness']['formal_ready']=True
            if name=='consumer-receipt.json':value['report_files']['report.json']=pin(files['report.json'])
            files[name]=encode(value)
        with self.assertRaises(ValueError):pub._validate(files,{n:pin(b) for n,b in files.items()},'fixture')

    def test_promotion_lineage_labels_and_receipt_hash_disagreement_reject(self):
        for field,value in (('formal_permission',True),('source_lineage',{}),('formal_fields',{})):
            files=dict(self.files);packet=pub.v.strict_json(files['report.json']);packet[field]=value
            files['report.json']=encode(packet)
            receipt=pub.v.strict_json(files['consumer-receipt.json']);receipt['report_files']['report.json']=pin(files['report.json'])
            files['consumer-receipt.json']=encode(receipt);pins={n:pin(b) for n,b in files.items()}
            with self.subTest(field=field),self.assertRaises(ValueError):pub._validate(files,pins,'fixture')
        files=dict(self.files);files['report.md']=b'actual result\n'
        with self.assertRaises(ValueError):pub._validate(files,self.pins,'fixture')
        receipt=pub.v.strict_json(files['consumer-receipt.json']);receipt['report_files']['report.md']=pin(files['report.md'])
        files['consumer-receipt.json']=encode(receipt)
        with self.assertRaises(ValueError):pub._validate(files,{n:pin(b) for n,b in files.items()},'fixture')

    def test_reader_rejects_changed_missing_extra_or_unbounded_saved_files(self):
        for case in ('changed','missing','extra','oversized','marker'):
            root,marker=self.local(case);payload=root/'payload'
            if case=='changed':(payload/'report.md').write_bytes(b'x'*len(self.files['report.md']))
            elif case=='missing':(payload/'report.md').unlink()
            elif case=='extra':(payload/'extra.txt').write_bytes(b'other')
            elif case=='oversized':(payload/'report.md').write_bytes(b'x'*(1024**2+1))
            else:marker='0'*64
            with self.subTest(case=case),self.assertRaises(ValueError):pub._read(root,self.pins,'fixture',marker)

    def test_invalid_source_never_publishes_or_starts_reader(self):
        (self.source/'report.md').write_bytes(b'changed\n')
        r=self.call();self.assertEqual(r['status'],'failed');self.assertEqual(r['reader_status'],'not_started')
        self.assertFalse((self.root/'chain/published/.complete').exists())
        self.assertTrue((self.root/'chain/writer/supervision.json').exists())

    def test_reader_failure_preserves_complete_publication(self):
        original=pub._role;seen=[]
        def fail(request,target,budget):
            seen.append(request['role'])
            if request['role']=='reader':raise ValueError('reader rejected')
            return original(request,target,budget)
        with patch.object(pub,'_role',side_effect=fail):r=self.call()
        self.assertEqual(seen,['writer','reader']);self.assertEqual(r['status'],'failed')
        self.assertEqual(r['publication_status'],'completed');self.assertEqual(r['reader_status'],'unconfirmed')
        self.assertTrue((self.root/'chain/published/.complete').exists())
        self.assertTrue(pub._read(self.root/'chain/published',self.pins,'fixture',r['marker_raw_sha256'])['local_verified'])

    def test_lost_writer_reply_preserves_marker_and_does_not_start_reader(self):
        original=pub._role;seen=[]
        def lost(request,target,budget):
            seen.append(request['role']);original(request,target,budget);raise OSError('lost reply')
        with patch.object(pub,'_role',side_effect=lost):r=self.call()
        self.assertEqual(seen,['writer']);self.assertEqual(r['publication_status'],'unconfirmed')
        self.assertEqual(r['reader_status'],'not_started');self.assertTrue((self.root/'chain/published/.complete').exists())

    def test_overlap_and_existing_partial_are_preserved(self):
        with self.assertRaises(ValueError):self.call(output_parent=self.source)
        partial=self.root/'chain';partial.mkdir();(partial/'note').write_bytes(b'keep')
        with self.assertRaises(FileExistsError):self.call()
        self.assertEqual((partial/'note').read_bytes(),b'keep')

    def test_unreaped_worker_retains_owner_and_blocks_reader(self):
        owner=object();error=pub.supervisor.UnreapedWorker(owner,{'worker_exit_confirmed':False})
        with patch.object(pub,'_role',side_effect=error) as role:
            with self.assertRaises(pub.supervisor.UnreapedWorker) as caught:self.call()
        self.assertIs(caught.exception.process,owner);self.assertEqual(role.call_count,1)
        record=pub.v.strict_json((self.root/'chain/unreaped.json').read_bytes())
        self.assertEqual(record['reader_status'],'not_started');self.assertEqual(record['publication_status'],'unconfirmed')
