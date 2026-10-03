"""Invented saved receipts, real owned publication/readback, and fail-closed boundaries."""
import copy
from contextlib import nullcontext, redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from banto_ai import anomaly_v03_fixture_publication as flow
from banto_ai import anomaly_v03_fixture_audit_worker as audit
from tests import test_anomaly_v03_wrapper_fixture as hand
from tests import test_anomaly_v03_consumer_evidence as supplied


def example():
    # Prior receipts here are deliberately invented, never historical observations.
    request,kwargs = hand.example();wrapped = hand.wrapper.assemble_fixture_wrapper(request,hand.SCHEMA,**kwargs)
    files = {'analysis/document.json':flow.v.canonical_json(request['document']),
        'analysis/evidence.json':kwargs['analysis_record'],
        'analysis/binding.json':flow.io.json_bytes(wrapped['payloads']['execution.json']['analysis_binding'])}
    files.update({'wrapper/'+n:flow.v.canonical_json(p) for n,p in wrapped['payloads'].items()})
    record = flow.v.strict_json(kwargs['analysis_record'])
    a = {'format':'anomaly-v03-fixture-worker-check-v1','status':'verified','mode':'fixture','role':'analysis',
        'worker_exit_confirmed':True,'worker_pid':record['process']['pid'],'new_evaluations':0,'formal_permission':False,
        'registered_data_read':False,'resource_budget_passed':True,'operation':'assemble-invented-document-v1',
        'fixture_inference_performed':True,'evidence_pin':flow.observed._pin(files['analysis/evidence.json']),
        'document_pin':flow.observed._pin(files['analysis/document.json']),'binding_pin':flow.observed._pin(files['analysis/binding.json']),
        'wrapper_payload_pins':wrapped['payload_pins'],'computation':{'fixture_only':True,'clusters':40,'replicates':len(request['fixture_input']['draws'])}}
    files['analysis/result.json'] = flow.io.json_bytes(a)
    ar = {'result_pin':flow.observed._pin(files['analysis/result.json']),'evidence_pin':a['evidence_pin'],'source_revision':hand.REVISION}
    verdict = audit._success_summary({'operation':audit.SLICE_OPERATION},{'fixture/input.json':request['fixture_input'],'fixture/slices.json':request['slice_input']})
    files['audit/verdict.json'] = flow.v.canonical_json(verdict)
    br = supplied.case(role='audit')['evidence']
    br['inputs'] = {n:record['inputs'][n] for n in ('fixture/input.json','fixture/slices.json')}
    br['inputs'].update({'fixture/document.json':a['document_pin'],'analysis/result.json':ar['result_pin'],'analysis/evidence.json':ar['evidence_pin']})
    br['outputs'] = {'fixture/primary-and-slices-audit.json':flow.observed._pin(files['audit/verdict.json'])}
    files['audit/evidence.json'] = flow.io.json_bytes(br)
    b = {'format':'anomaly-v03-fixture-audit-check-v1','status':'verified','mode':'fixture','role':'audit',
        'worker_exit_confirmed':True,'worker_pid':br['process']['pid'],'new_evaluations':0,'formal_permission':False,
        'registered_data_read':False,'resource_budget_passed':True,'operation':audit.SLICE_OPERATION,
        'fixture_numerical_audit_performed':True,'fixture_slice_audit_performed':True,'analysis_reference':ar,
        'audit_pin':flow.observed._pin(files['audit/verdict.json']),'evidence_pin':flow.observed._pin(files['audit/evidence.json'])}
    files['audit/result.json'] = flow.io.json_bytes(b)
    return files,ar,{'result_pin':flow.observed._pin(files['audit/result.json']),'evidence_pin':b['evidence_pin'],'source_revision':hand.REVISION}


class RoleObservationPinTests(unittest.TestCase):
    """Saved observation anchors need no native runtime or owned process."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='banto-role-anchor-');self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()

    def saved_observations(self,name):
        target = self.root/name;target.mkdir();(target/'worker').mkdir()
        report = b'{"invented_report":true}\n'
        (target/'worker/report.json').write_bytes(report)
        monitor = {'status':'complete','output':flow.observed._pin(report)}
        flow.observed._save(target/'supervision.json',monitor)
        pair = {'before':{'invented':['source']},'after':{'invented':['source']}}
        return target,monitor,pair

    def test_writer_and_reader_pin_parent_values_to_saved_bytes(self):
        for role in ('writer','reader'):
            with self.subTest(role=role):
                target,monitor,pair = self.saved_observations(role)
                pins = flow._retain_role_observation_pins(role,target,monitor,pair)
                self.assertEqual(set(pins),{'dependency_pin','stdout_pin','supervision_pin'})
                for field,name in (('dependency_pin','dependencies.json'),('stdout_pin','worker/report.json'),
                                   ('supervision_pin','supervision.json')):
                    self.assertEqual(pins[field],flow.observed._pin((target/name).read_bytes()))
                self.assertEqual(pins['stdout_pin'],monitor['output'])

    def test_saved_copy_change_is_rejected_for_each_anchor(self):
        for name in ('supervision.json','worker/report.json','dependencies.json'):
            with self.subTest(name=name):
                target,monitor,pair = self.saved_observations(name.replace('/','-'))
                if name == 'dependencies.json':
                    original = flow.observed._save
                    def changed(path,value):
                        original(path,value)
                        if Path(path) == target/'dependencies.json':Path(path).write_bytes(b'{}\n')
                    context = patch.object(flow.observed,'_save',side_effect=changed)
                else:
                    (target/name).write_bytes(b'{}\n')
                    context = nullcontext()
                with context,self.assertRaisesRegex(ValueError,'retained writer '+name+' changed'):
                    flow._retain_role_observation_pins('writer',target,monitor,pair)

    def test_other_role_is_rejected_before_saving_dependencies(self):
        target,monitor,pair = self.saved_observations('other-role')
        with self.assertRaisesRegex(ValueError,'publication role'):
            flow._retain_role_observation_pins('analysis',target,monitor,pair)
        self.assertFalse((target/'dependencies.json').exists())


@unittest.skipUnless(os.name == 'nt' and sys.version_info[:2] == (3,14),'Windows CPython 3.14 observation')
class FixturePublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files,cls.analysis,cls.audit = example()
        cls.revision = subprocess.check_output(['git','-C',str(flow.ROOT),'rev-parse','HEAD'],text=True).strip()

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='banto-five-payload-');self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve();inputs = self.root/'inputs';inputs.mkdir();self.receipts = self.root/'receipts';self.receipts.mkdir()
        rows = {}
        for name,raw in self.files.items():
            path = inputs/name.replace('/','-');path.write_bytes(raw);rows[name] = {'path':str(path),'pin':flow.observed._pin(raw),'links':1}
        self.request = {'format':flow.FORMAT,'mode':'fixture','inputs':rows,'analysis_reference':copy.deepcopy(self.analysis),'audit_reference':copy.deepcopy(self.audit)}

    def run_flow(self,**kwargs):
        return flow.publish_with_evidence(self.request,expected_revision=self.revision,receipt_parent=self.receipts,receipt_name='chain',**kwargs)

    def replace(self,name,value):
        row = self.request['inputs'][name];raw = flow.v.canonical_json(value);Path(row['path']).write_bytes(raw);row['pin'] = flow.observed._pin(raw)
        if name in ('analysis/result.json','audit/result.json'):self.request[name.split('/')[0]+'_reference']['result_pin'] = row['pin']

    def test_actual_owned_writer_then_reader_preserves_five_values_and_adds_LF(self):
        order = [];original = flow._run_role
        def run(role,*args):
            if role == 'reader':self.assertEqual(order,['writer_reaped'])
            result = original(role,*args);self.assertTrue(result['worker_exit_confirmed']);order.append(role+'_reaped');return result
        with patch.object(flow,'_run_role',side_effect=run),patch.object(hand.wrapper,'assemble_fixture_wrapper',side_effect=AssertionError('rebuild')):
            result = self.run_flow()
        self.assertEqual(result['status'],'verified',result);self.assertTrue(result['resource_budget_passed'])
        self.assertEqual(order,['writer_reaped','reader_reaped']);self.assertEqual(result['analysis_runs']+result['audit_runs'],0)
        self.assertEqual((result['selected_source_files'],result['runtime_files'],result['retained_input_files']),(13,2,12))
        root = Path(result['check_directory'])
        for n in flow.PAYLOADS:self.assertEqual((root/'published/payload'/n).read_bytes(),self.files['wrapper/'+n]+b'\n')
        writer = json.loads((root/'writer/evidence.json').read_bytes());reader = json.loads((root/'reader/evidence.json').read_bytes())
        self.assertEqual((writer['role'],reader['role']),('writer','reader'));self.assertNotEqual(writer['invocation_id'],reader['invocation_id'])
        for role in ('writer','reader'):
            receipt = result[role]
            self.assertEqual(json.loads((root/role/'result.json').read_bytes()),receipt)
            for field,name in (('dependency_pin','dependencies.json'),('stdout_pin','worker/report.json'),
                               ('supervision_pin','supervision.json')):
                self.assertEqual(receipt[field],flow.observed._pin((root/role/name).read_bytes()))
            self.assertEqual(receipt['stdout_pin'],json.loads((root/role/'supervision.json').read_bytes())['output'])
        self.assertEqual(os.stat(root/'published/.complete').st_nlink,2)
        for k,v in flow.CLOSED.items():self.assertEqual(result[k],v)
        self.assertEqual(json.loads((root/'published/payload/execution.json').read_bytes())['stages']['writer'],'not_run')

    def test_formal_mode_rejected_before_io(self):
        for mode in ('formal','engineering-dev-smoke','holdout'):
            self.request['mode'] = mode
            with patch.object(flow.io,'_local_parent',side_effect=AssertionError('IO')),self.assertRaises(ValueError):self.run_flow()

    def test_external_pins_not_rederived(self):
        self.request['analysis_reference']['result_pin']['sha256'] = 'f'*64
        with patch.object(flow.io,'_local_parent',side_effect=AssertionError('IO')),self.assertRaises(ValueError):self.run_flow()

    def test_legacy_primary_audit_rejected_without_launch(self):
        value = json.loads(self.files['audit/result.json']);value['operation'] = audit.OPERATION;self.replace('audit/result.json',value)
        with patch.object(flow,'_run_role',side_effect=AssertionError('launch')):result = self.run_flow()
        self.assertEqual(result['status'],'failed');self.assertIn('operation',result['detail'])

    def test_audit_of_different_analysis_rejected(self):
        value = json.loads(self.files['audit/result.json']);value['analysis_reference']['source_revision'] = 'b'*40;self.replace('audit/result.json',value)
        with patch.object(flow,'_run_role',side_effect=AssertionError('launch')):result = self.run_flow()
        self.assertEqual(result['status'],'failed');self.assertIn('analysis_reference',result['detail'])

    def test_changed_saved_payload_rejected_without_launch(self):
        row = self.request['inputs']['wrapper/analysis.json'];Path(row['path']).write_bytes(b'{}')
        with patch.object(flow,'_run_role',side_effect=AssertionError('launch')):result = self.run_flow()
        self.assertEqual(result['status'],'failed');self.assertEqual(result['publication_status'],'not_started')

    def test_resealed_payload_mapping_still_rejected(self):
        value = json.loads(self.files['wrapper/analysis.json']);value['fixture_packet'] = {};self.replace('wrapper/analysis.json',value)
        a = json.loads(self.files['analysis/result.json']);a['wrapper_payload_pins']['analysis.json'] = self.request['inputs']['wrapper/analysis.json']['pin']
        self.replace('analysis/result.json',a)
        # Keep the supplied audit reference coherent, so rejection reaches semantic mapping.
        b = json.loads(self.files['audit/result.json']);b['analysis_reference'] = self.request['analysis_reference']
        br = json.loads(self.files['audit/evidence.json']);br['inputs']['analysis/result.json'] = b['analysis_reference']['result_pin']
        self.replace('audit/evidence.json',br);b['evidence_pin'] = self.request['inputs']['audit/evidence.json']['pin']
        self.request['audit_reference']['evidence_pin'] = b['evidence_pin'];self.replace('audit/result.json',b)
        with patch.object(flow,'_run_role',side_effect=AssertionError('launch')):result = self.run_flow()
        self.assertEqual(result['status'],'failed');self.assertIn('analysis mapping',result['detail'])

    def test_existing_target_preserved(self):
        root = self.receipts/'chain';root.mkdir();(root/'keep').write_bytes(b'keep')
        with self.assertRaises((ValueError,OSError)):self.run_flow()
        self.assertEqual((root/'keep').read_bytes(),b'keep')

    def test_input_output_overlap_rejected(self):
        self.request['inputs']['wrapper/analysis.json']['path'] = str(self.receipts/'chain/input.json')
        with self.assertRaisesRegex(ValueError,'overlaps'):self.run_flow()

    def test_writer_partial_failure_preserved_and_reader_not_started(self):
        original = flow.io.LocalPublication.write
        count = []
        def broken(store,*args):
            if count:raise OSError('second write failed')
            count.append(1);return original(store,*args)
        def role(role,request,target,publication,revision,budget,files,inputs,source_context):
            self.assertEqual(role,'writer')
            with patch.object(flow.io.LocalPublication,'write',broken):
                flow.io.publish_local_result(publication.parent,publication.name,files,verify_semantics=flow._semantic(files))
        with patch.object(flow,'_run_role',side_effect=role) as call:result = self.run_flow()
        self.assertEqual(call.call_count,1);self.assertEqual(result['publication_status'],'unconfirmed')
        self.assertTrue(list((self.receipts/'chain/published/stage').iterdir()));self.assertFalse((self.receipts/'chain/reader').exists())

    def test_lost_writer_response_does_not_infer_success_from_marker(self):
        original = flow.supervisor.supervise
        def lost(*args,**kwargs):
            monitor = original(*args,**kwargs);self.assertEqual(monitor['status'],'complete',monitor)
            (args[2]/'report.json').unlink();return monitor
        with patch.object(flow.supervisor,'supervise',side_effect=lost) as call:result = self.run_flow()
        self.assertEqual(call.call_count,1);self.assertEqual(result['status'],'failed');self.assertEqual(result['publication_status'],'unconfirmed')
        self.assertTrue((self.receipts/'chain/published/.complete').is_file());self.assertFalse((self.receipts/'chain/reader').exists())

    def test_child_precommit_profile_mismatch_leaves_no_marker(self):
        target = self.receipts/'child-precommit'
        writer = target/'writer';writer.mkdir(parents=True)
        publication = target/'published'
        _,files = flow._load(self.request)
        marker = flow._marker(files)
        raw_profile = b'{}\n'
        flow.io._exclusive(writer/'dependency-profile.json',raw_profile)
        bundle = {'format':flow.INVOCATION,'invocation_id':'a'*64,
                  'source':flow._source(self.revision),'request':self.request,
                  'role':'writer','publication':str(publication),
                  'expected_outputs':{name:flow.observed._pin(raw) for name,raw in
                      flow._role_outputs('writer',self.request,files,marker).items()},
                  'dependency_profile_pin':flow.observed._pin(raw_profile)}
        raw_invocation = flow.io.json_bytes(bundle)
        path = writer/'invocation.json';flow.io._exclusive(path,raw_invocation)
        pin = flow.observed._pin(raw_invocation)
        after_calls = []
        def compare(profile, snapshot, runtime, *, phase):
            if phase == 'after':
                after_calls.append(True)
                if len(after_calls) == 2:
                    raise ValueError('five-role profile inventory after mismatch')
        output = StringIO()
        with patch.object(flow.dependencies,'load_five_role_profile',return_value={'invented':'candidate'}), \
             patch.object(flow.dependencies,'collect',return_value={'invented':'snapshot'}), \
             patch.object(flow.dependencies,'match_five_role_profile',side_effect=compare), \
             patch.object(flow.observed,'_observed_runtime',return_value={'invented':'runtime'}), \
             redirect_stdout(output):
            exit_code = flow.worker_main([str(path),str(pin['bytes']),pin['sha256']])
        self.assertEqual(exit_code,2)
        self.assertEqual(after_calls,[True,True])
        rejection = json.loads(output.getvalue())
        self.assertEqual(rejection['status'],'fixture_publication_rejected')
        self.assertFalse(rejection['formal_permission'])
        self.assertIn('five-role profile inventory after mismatch',rejection['detail'])
        self.assertTrue((publication/'payload/analysis.json').is_file())
        self.assertTrue((publication/'marker-pending.json').is_file())
        self.assertFalse((publication/'.complete').exists())
        self.assertFalse((target/'reader').exists())

    def test_child_precommit_rejection_retains_failed_parent_receipt(self):
        def rejected(role, request, target, publication, revision,
                     budget, files, inputs, source_context, profile):
            self.assertEqual(role,'writer')
            self.assertEqual(profile,{'invented':'pinned-candidate'})
            def mismatch():raise ValueError('writer profile before commit mismatch')
            flow.io.publish_local_result(publication.parent,publication.name,files,
                verify_semantics=flow._semantic(files),precommit_recheck=mismatch)
        candidates = {'writer':{'invented':'pinned-candidate'},
                      'reader':{'invented':'pinned-candidate'}}
        with patch.object(flow,'_git_sources',return_value=({}, {}, object())), \
             patch.object(flow,'_cached_git',return_value=None), \
             patch.object(flow,'_run_role',side_effect=rejected) as launched:
            result = self.run_flow(dependency_profiles=candidates)
        self.assertEqual(launched.call_count,1)
        self.assertEqual(result['status'],'failed')
        self.assertEqual(result['publication_status'],'unconfirmed')
        self.assertEqual(result['reader_status'],'not_started')
        self.assertTrue(result['profile_required'])
        self.assertFalse(result['formal_permission'])
        self.assertIn('writer profile before commit mismatch',result['detail'])
        target = self.receipts/'chain'
        self.assertEqual(flow.v.strict_json((target/'result.json').read_bytes())['detail'],result['detail'])
        self.assertFalse((target/'published/.complete').exists())
        self.assertFalse((target/'reader').exists())

    def test_parent_postflight_profile_failure_can_keep_marker_but_not_success_claim(self):
        def after_mismatch(role, request, target, publication, revision,
                           budget, files, inputs, source_context, profile):
            self.assertEqual(role, 'writer')
            self.assertEqual(profile, {'invented': 'pinned-candidate'})
            flow.io.publish_local_result(publication.parent, publication.name,
                                         files, verify_semantics=flow._semantic(files))
            raise ValueError('writer after profile mismatch')
        candidates = {'writer': {'invented': 'pinned-candidate'},
                      'reader': {'invented': 'pinned-candidate'}}
        with patch.object(flow, '_git_sources', return_value=({}, {}, object())), \
             patch.object(flow, '_cached_git', return_value=None), \
             patch.object(flow, '_run_role', side_effect=after_mismatch) as launched:
            result = self.run_flow(dependency_profiles=candidates)
        self.assertEqual(launched.call_count, 1)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['publication_status'], 'unconfirmed')
        self.assertEqual(result['reader_status'], 'not_started')
        self.assertTrue(result['profile_required'])
        self.assertFalse(result['before_work_profile_enforcement'])
        self.assertFalse(result['formal_permission'])
        self.assertFalse(result['source_closure_complete'])
        self.assertFalse(result['runtime_closure_complete'])
        self.assertTrue((self.receipts/'chain/published/.complete').is_file())
        self.assertFalse((self.receipts/'chain/reader').exists())

    def test_changed_writer_observation_cannot_be_retained_as_a_successful_receipt(self):
        for name in ('supervision.json','worker/report.json','dependencies.json'):
            with self.subTest(name=name):
                receipt_name = 'anchor-'+name.replace('/','-').replace('.','-')
                target = self.receipts/receipt_name
                if name == 'worker/report.json':
                    original = flow.dependencies.verify_pair
                    def changed(*args,**kwargs):
                        result = original(*args,**kwargs)
                        (target/'writer/worker/report.json').write_bytes(b'{}\n')
                        return result
                    context = patch.object(flow.dependencies,'verify_pair',side_effect=changed)
                else:
                    original = flow.observed._save
                    def changed(path,value):
                        original(path,value)
                        if Path(path) == target/'writer'/name:Path(path).write_bytes(b'{}\n')
                    context = patch.object(flow.observed,'_save',side_effect=changed)
                with context:
                    result = flow.publish_with_evidence(self.request,expected_revision=self.revision,
                        receipt_parent=self.receipts,receipt_name=receipt_name)
                self.assertEqual(result['status'],'failed',result)
                self.assertIn('retained writer '+name+' changed',result['detail'])
                self.assertEqual(result['publication_status'],'unconfirmed')
                self.assertTrue((target/'published/.complete').is_file())
                self.assertFalse((target/'reader').exists())

    def test_reader_failure_retains_completed_publication_and_writer_receipt(self):
        original = flow._run_role
        def run(role,*args):
            if role == 'reader':raise OSError('reader failed')
            return original(role,*args)
        with patch.object(flow,'_run_role',side_effect=run):result = self.run_flow()
        self.assertEqual(result['status'],'failed');self.assertEqual(result['publication_status'],'completed')
        self.assertTrue((self.receipts/'chain/writer/evidence.json').is_file());self.assertTrue((self.receipts/'chain/published/.complete').is_file())

    def test_forged_writer_role_after_actual_exit_rejected(self):
        original = flow.supervisor.supervise
        def alter(*args,**kwargs):
            monitor = original(*args,**kwargs);self.assertEqual(monitor['status'],'complete',monitor)
            path = args[2]/'report.json';reply = json.loads(path.read_bytes());reply['evidence']['role'] = 'reader'
            raw = flow.io.json_bytes(reply);path.write_bytes(raw);monitor['output'] = flow.observed._pin(raw);return monitor
        with patch.object(flow.supervisor,'supervise',side_effect=alter) as call:result = self.run_flow()
        self.assertEqual(call.call_count,1);self.assertEqual(result['status'],'failed');self.assertIn('role',result['detail'])

    def test_unreaped_owner_survives_receipt_failure(self):
        owner = object();error = flow.supervisor.UnreapedWorker(owner,{'worker_exit_confirmed':False})
        save = flow.observed._save
        def broken(path,value):
            if path.name in ('supervision.json','unreaped.json'):raise OSError('save failed')
            return save(path,value)
        with patch.object(flow.supervisor,'supervise',side_effect=error),patch.object(flow.observed,'_save',side_effect=broken):
            with self.assertRaises(flow.supervisor.UnreapedWorker) as caught:self.run_flow()
        self.assertIs(caught.exception.process,owner)

    def test_resource_pressure_stops_before_writer(self):
        snapshot = flow.budgets.system_snapshot(self.receipts);snapshot['free_ram_bytes'] = 1
        with patch.object(flow.budgets,'system_snapshot',return_value=snapshot),patch.object(flow,'_run_role',side_effect=AssertionError('launch')):
            result = self.run_flow()
        self.assertEqual(result['status'],'failed');self.assertFalse(result['resource_budget_passed']);self.assertEqual(result['publication_status'],'not_started')

    def test_only_immutable_revision_blobs_reused_within_one_call(self):
        calls = []
        def git(*args):calls.append(args);return b'disk'
        git.tool_record = {}
        cached = flow._cached_git(git,self.revision,{self.revision:{'known.py':b'known'}})
        self.assertEqual(cached('show',self.revision+':known.py'),b'known');self.assertEqual(calls,[])
        for unused in range(2):self.assertEqual(cached('show',self.revision+':new.py'),b'disk')
        self.assertEqual(len(calls),1)
        for unused in range(2):cached('status','--porcelain');cached('show','HEAD:known.py')
        self.assertEqual(len(calls),5)
        with self.assertRaises(ValueError):cached('show',self.revision+':../outside.py')
