"""Projection and failure boundaries; real owned chain is saved separately."""
import copy
from contextlib import ExitStack
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from banto_ai import anomaly_v03_bound_fixture_pipeline as flow
from tests import test_anomaly_v03_slice_fixture as hand

REVISION='a'*40
PIN=flow.producer.primary.pin(b'{}')


def example():
    fixture=hand.hand.invented_input(ready=False)
    coverage={'format':flow.analysis.wrapper.COVERAGE_FORMAT,'invented_only':True,'layout_ids':list(range(12)),
        'clusters':[{'cluster_id':r['cluster_id'],'candidates':{c:{s:['success']*12 for s in flow.producer.primary.arithmetic.STRATA[:2]}
            for c in flow.producer.primary.arithmetic.CANDIDATES}} for r in fixture['clusters']]}
    main={**flow.producer.primary.CLOSED,'format':'anomaly-v03-producer-input-fixture-bound-v1','mode':'fixture',
        'invented_only':True,'status':'fixture_inputs_bound','complete_for_aggregation':True,'planned_chunks':480,
        'planned_evaluations':2880,'producer_state':'complete','producer_failure':None,'manifest_pin':PIN,'registration_pin':PIN,
        'clusters':fixture['clusters'],'diagnostics':fixture['diagnostics'],'wrapper_coverage':coverage,
        'coverage':{'success':2880,'inconclusive':0,'partial':0,'failed':0,'not_started':0},'failed_attempt_history':[]}
    return {**flow.producer.primary.CLOSED,'format':flow.producer.OUTPUT_FORMAT,'mode':'fixture','invented_only':True,
        'status':'fixture_slices_bound','complete_for_aggregation':True,'scope':'supplied-invented-bytes-only',
        'primary':main,'slice_manifest_pin':PIN,'latest_slice_pins':{str(i):PIN for i in range(2880)},
        'slice_source':hand.invented_slices(fixture)}


class BoundFixturePipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.base=example();cls.raw=flow.v.canonical_json(cls.base);cls.pin=flow.producer.primary.pin(cls.raw)
    def prepare(self,value=None,draws=None):
        raw=self.raw if value is None else flow.v.canonical_json(value)
        return flow.prepare_inputs(raw,expected_mode='fixture',expected_pin=flow.producer.primary.pin(raw),
            expected_revision=REVISION,draws=[list(range(40))] if draws is None else draws)
    def fresh(self):return copy.deepcopy(self.base)

    def test_four_files_preserve_values_and_pin_the_projection(self):
        value=self.prepare();self.assertEqual(set(value['files']),set(flow.analysis.INPUT_LIMITS))
        self.assertEqual(json.loads(value['files']['fixture/slices.json']),self.base['slice_source'])
        self.assertEqual(json.loads(value['files']['fixture/input.json'])['clusters'],self.base['primary']['clusters'])
        self.assertEqual(value['binding']['bound_result_pin'],self.pin)
        self.assertEqual(value['binding']['worker_input_pins'],{n:flow.producer.primary.pin(b) for n,b in value['files'].items()})
        self.assertFalse(json.loads(value['files']['fixture/input.json'])['engineering_ready_assumption'])

    def test_projection_has_no_io_inference_or_producer_replay(self):
        with (patch('builtins.open',side_effect=AssertionError('IO')),patch.object(Path,'open',side_effect=AssertionError('IO')),
            patch.object(subprocess,'Popen',side_effect=AssertionError('process')),
            patch.object(flow.analysis.wrapper.document,'build_fixture_document',side_effect=AssertionError('inference')),
            patch.object(flow.producer,'bind_producer_slices',side_effect=AssertionError('replay'))):self.prepare()

    def test_modes_rejected_before_decode_or_receipt_access(self):
        for mode in ('formal','holdout','engineering-dev-smoke',True):
            with patch.object(flow.v,'strict_json',side_effect=AssertionError('decode')),self.assertRaises(ValueError):
                flow.prepare_inputs(None,expected_mode=mode,expected_pin=None,expected_revision=None,draws=None)
            with patch.object(flow.io,'_local_parent',side_effect=AssertionError('IO')),self.assertRaises(ValueError):
                flow.run_pipeline(None,expected_mode=mode,expected_pin=None,expected_revision=None,draws=None,
                    expected_document_pin=None,receipt_parent=None,receipt_name=None)

    def test_wrong_pin_and_modified_raw_bytes_rejected(self):
        for raw,pin in ((self.raw,PIN),(self.raw+b' ',self.pin)):
            with self.assertRaisesRegex(ValueError,'caller bound result pin'):
                flow.prepare_inputs(raw,expected_mode='fixture',expected_pin=pin,expected_revision=REVISION,draws=[list(range(40))])

    def test_closed_fields_and_incomplete_primary_cannot_be_promoted(self):
        for parent,key,value in ((None,'formal_permission',True),(None,'complete_for_aggregation',False),
            ('primary','producer_state','failed'),('primary','planned_evaluations',2879),('primary','analysis_authorized',True)):
            case=self.fresh();target=case if parent is None else case[parent];target[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.prepare(case)

    def test_coverage_state_and_count_disagreements_rejected(self):
        case=self.fresh();case['primary']['coverage']['success']-=1
        with self.assertRaisesRegex(ValueError,'declared coverage'):self.prepare(case)
        case=self.fresh();c=flow.producer.primary.arithmetic.CANDIDATES[0]
        case['primary']['wrapper_coverage']['clusters'][0]['candidates'][c]['core'][0]='failed'
        with self.assertRaises(ValueError):self.prepare(case)

    def test_draw_count_shape_and_index_limits(self):
        for draws in ([],[list(range(40))]*9,[[0]*39],[[40]*40],[[True]*40]):
            with self.subTest(draws=draws[:1]),self.assertRaises(ValueError):self.prepare(draws=draws)

    def test_slice_count_profile_delay_and_identity_disagreements(self):
        c=flow.producer.primary.arithmetic.CANDIDATES[0]
        changes=[lambda r:r.update(cluster_id='invented-39'),
            lambda r:r['candidates'][c]['core'].update(evaluations=11),
            lambda r:r['candidates'][c]['core'].update(profile_inconclusive_evaluations=1),
            lambda r:r['candidates'][c]['core']['delay_histogram'].__setitem__(0,1)]
        for change in changes:
            case=self.fresh();change(case['slice_source']['clusters'][0])
            with self.assertRaises(ValueError):self.prepare(case)

    def test_unknown_slice_fields_and_missing_latest_pins_rejected(self):
        case=self.fresh();case['slice_source']['clusters'][0]['candidates']['unknown']={}
        with self.assertRaises(ValueError):self.prepare(case)
        case=self.fresh();case['latest_slice_pins'].pop('0')
        with self.assertRaises(ValueError):self.prepare(case)

    def test_bound_and_projected_byte_limits(self):
        with patch.object(flow,'BOUND_LIMIT',1),self.assertRaises(ValueError):self.prepare()
        with patch.object(flow.analysis,'TOTAL_INPUT_LIMIT',1),self.assertRaises(ValueError):self.prepare()

    def run_flow(self,root):
        with ExitStack() as stack:
            if os.name!='nt':
                # These tests exercise pipeline ordering and retained receipts.
                # The production budget samples Windows GetPerformanceInfo.
                gib=1024**3
                stack.enter_context(patch.object(flow.budgets,'system_snapshot',return_value={
                    'commit_total_bytes':gib,'commit_limit_bytes':16*gib,'commit_headroom_bytes':15*gib,
                    'free_ram_bytes':8*gib,'free_disk_bytes':30*gib,'parent_peak_private_bytes':0}))
            return flow.run_pipeline(self.raw,expected_mode='fixture',expected_pin=self.pin,expected_revision=REVISION,
                draws=[list(range(40))],expected_document_pin=PIN,receipt_parent=root,receipt_name='attempt')
    def git_stub(self,*args):
        if args[0]=='status':return b''
        if args[0]=='show':return (flow.ROOT/flow.SOURCE).read_bytes()
        raise AssertionError(args)

    def test_analysis_failure_prevents_audit_and_retains_result(self):
        with tempfile.TemporaryDirectory(prefix='banto-bound-failure-') as root, \
            patch.object(flow.analysis.observed,'_git_sources',return_value=(None,None,self.git_stub)), \
            patch.object(flow.analysis,'calculate_with_evidence',return_value={'status':'failed'}) as analysis, \
            patch.object(flow.audit,'audit_with_evidence',side_effect=AssertionError('audit after failure')):
            value=self.run_flow(root)
            self.assertEqual(value['status'],'failed');self.assertEqual(value['analysis_runs'],1);self.assertEqual(value['audit_runs'],0)
            self.assertFalse(value['fixture_numerical_audit_performed']);self.assertEqual(analysis.call_count,1)
            self.assertTrue((Path(root)/'attempt/result.json').is_file())

    def test_audit_failure_keeps_analysis_and_does_not_retry(self):
        with tempfile.TemporaryDirectory(prefix='banto-bound-audit-') as root, \
            patch.object(flow.analysis.observed,'_git_sources',return_value=(None,None,self.git_stub)), \
            patch.object(flow.analysis,'calculate_with_evidence',return_value={'status':'verified','resource_budget_passed':True,'result_pin':PIN,'evidence_pin':PIN}) as a, \
            patch.object(flow.audit,'audit_with_evidence',return_value={'status':'failed'}) as b:
            value=self.run_flow(root)
            self.assertEqual(value['status'],'failed');self.assertEqual((a.call_count,b.call_count),(1,1))
            self.assertEqual(value['analysis']['status'],'verified');self.assertFalse(value['fixture_slice_audit_performed'])
            self.assertTrue(value['fixture_inference_performed'])

    def test_unreaped_owner_survives_and_audit_never_runs(self):
        owner=object();error=flow.analysis.supervisor.UnreapedWorker(owner,{'status':'unconfirmed'})
        with tempfile.TemporaryDirectory(prefix='banto-bound-owner-') as root, \
            patch.object(flow.analysis.observed,'_git_sources',return_value=(None,None,self.git_stub)), \
            patch.object(flow.analysis,'calculate_with_evidence',side_effect=error), \
            patch.object(flow.audit,'audit_with_evidence',side_effect=AssertionError('audit after unreaped')):
            with self.assertRaises(flow.analysis.supervisor.UnreapedWorker) as caught:self.run_flow(root)
            self.assertIs(caught.exception,error);self.assertIs(caught.exception.process,owner)


if __name__=='__main__':unittest.main()
