"""Saved-format binding tests and real compact-count checks; no campaign runs."""
import copy
import json
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_saved_chunk_summary as flow
from tests import test_anomaly_v03_observation_audit as existing
from tests.test_anomaly_v03_slices import hand_evaluation
from tests.test_anomaly_v03_ledger_audit import zero_result


def count_fixture():
    result,audit=hand_evaluation()
    result['input_hashes']={n:'a'*64 for n in flow.reader.DATASET_INPUTS}
    metrics=zero_result()['metrics']
    audit['ledger_audit'].update(metrics=metrics,score_rows=14400,incidents=20,equipment_episodes=0,
        independent_s6_complete=False,performance_status='not_evaluated')
    audit['profile_and_score_audit'].update(**flow.primary.QUIET,identity=result['identity'],
        status='observation_profile_score_checks_passed',profile_derivation_verified=True,
        profiles_checked=48,observation_rows=18000,score_rows_checked=14400,
        inconclusive_profiles=[],evaluation_outcome='success',available_score_rows=13920)
    return result,audit


class SavedChunkSummaryTests(unittest.TestCase):
    def setUp(self):
        self.base=existing.ConnectedAuditTests();self.base.setUp()
        self.addCleanup(self.base.doCleanups)
        # Exact full event-ledger bytes, not the enabled-only generation input.
        for identity,name in zip(self.base.identities,self.base.results):
            path=self.base.stem+'/result/payload/datasets/'+identity['dataset_id']+'/event-ledger.jsonl'
            raw=b''.join(flow.reader.registry.canonical_json(e)+b'\n' for e in flow.reader.registry.event_inventory(identity))
            self.base.put(path,raw)
            value=json.loads((self.base.run/name).read_bytes());value['input_hashes']['events']=existing.pin(raw)['sha256']
            self.base.put(name,existing.encoded(value))
        self.base.seal()
        self.project=self.enterContext(patch.object(flow,'_summarize',side_effect=self.project_row))

    def project_row(self,result,audit,*,evaluation_pin):
        self.base.order.append(('summary',result['identity']['evaluation_id']))
        self.assertEqual(audit['ledger_audit']['status'],'ledger_checks_passed')
        self.assertEqual(audit['identity'],result['identity'])
        return {'identity':copy.deepcopy(result['identity']),'evaluation_outcome':audit['evaluation_outcome'],
                'evaluation_pin':evaluation_pin}

    def call(self,**kwargs):
        return flow.read_chunk_summaries(self.base.anchor,self.base.digest,self.base.run,0,expected_mode=kwargs.pop('expected_mode','fixture'),**kwargs)

    def test_formal_unknown_and_wrong_summary_type_fail_before_io(self):
        with patch.object(flow.reader,'read_pinned',side_effect=AssertionError('IO')):
            for mode in ('formal','holdout',None,True):
                with self.subTest(mode=mode),self.assertRaisesRegex(ValueError,'mode is closed'):self.call(expected_mode=mode)
            with self.assertRaisesRegex(ValueError,'boolean'):
                flow.reader.audit_completed_chunk(None,None,None,0,include_summaries=1)

    def test_six_summaries_one_read_each_and_no_failed_attempt_or_write(self):
        before={p:p.read_bytes() for p in self.base.root.rglob('*') if p.is_file()}
        with patch.object(flow.reader,'read_pinned',wraps=flow.reader.read_pinned) as reads:
            result=self.call()
        paths=[str(c.args[0]) for c in reads.call_args_list]
        self.assertEqual(len(paths),22);self.assertEqual(len(set(paths)),22)
        self.assertFalse(any('attempt-0001' in p for p in paths))
        self.assertEqual(self.base.order,[(kind,i['evaluation_id']) for i in self.base.identities for kind in ('numeric','ledger','summary')])
        self.assertEqual(result['prior_attempts_not_credited'],1)
        self.assertEqual(result['evaluations_checked'],6)
        self.assertFalse(result['all_campaign_payloads_read']);self.assertFalse(result['raw_generation_verified'])
        self.assertFalse(result['formal_permission']);self.assertFalse(result['analysis_authorized'])
        for row,name in zip(result['evaluations'],self.base.results):self.assertEqual(row['evaluation_pin'],self.base.files[name])
        self.assertEqual(before,{p:p.read_bytes() for p in self.base.root.rglob('*') if p.is_file()})

    def test_changed_result_rejected_before_summary(self):
        p=self.base.run/self.base.results[0];p.write_bytes(p.read_bytes()+b' ')
        with self.assertRaises(ValueError):self.call()
        self.project.assert_not_called()

    def test_last_failed_attempt_cannot_fall_back(self):
        self.base.chunk['attempts'].append({'attempt':3,'status':'failed'});self.base.seal()
        with self.assertRaisesRegex(ValueError,'final attempt'):self.call()
        self.project.assert_not_called()

    def test_missing_planned_slot_is_rejected(self):
        self.base.chunk['outcome']['slots'].pop();self.base.seal()
        with self.assertRaisesRegex(ValueError,'six saved slot'):self.call()
        self.project.assert_not_called()

    def test_resealed_event_bytes_cannot_disagree_with_result(self):
        identity=self.base.identities[0]
        p=self.base.stem+'/result/payload/datasets/'+identity['dataset_id']+'/event-ledger.jsonl'
        raw=b'{}\n';self.base.put(p,raw)
        for name in self.base.results[:3]:
            value=json.loads((self.base.run/name).read_bytes());value['input_hashes']['events']=existing.pin(raw)['sha256']
            self.base.put(name,existing.encoded(value))
        self.base.seal()
        with self.assertRaisesRegex(ValueError,'full event ledger'):self.call()
        self.base.numeric.assert_not_called();self.project.assert_not_called()

    def test_ledger_failure_never_reaches_summary(self):
        self.base.ledger.side_effect=ValueError('ledger mismatch')
        with self.assertRaisesRegex(ValueError,'ledger mismatch'):self.call()
        self.project.assert_not_called()

    def test_summary_failure_does_not_return_partial_success(self):
        self.project.side_effect=ValueError('slice mismatch')
        with self.assertRaisesRegex(ValueError,'slice mismatch'):self.call()
        self.assertEqual(self.base.numeric.call_count,1)

    def test_inconclusive_is_preserved_and_not_success(self):
        self.base.numeric.side_effect=None;self.base.numeric.return_value={'evaluation_outcome':'inconclusive'}
        self.base.chunk['status']=self.base.chunk['attempts'][-1]['status']='verified_inconclusive'
        for slot in self.base.chunk['outcome']['slots']:slot['status']='inconclusive'
        self.base.seal();result=self.call()
        self.assertEqual({r['evaluation_outcome'] for r in result['evaluations']},{'inconclusive'})


class CompactSummaryTests(unittest.TestCase):
    def test_real_counts_and_slice_projection_preserves_null_and_inventory(self):
        result,audit=count_fixture();before=copy.deepcopy(result)
        row=flow._summarize(result,audit,evaluation_pin={'bytes':1,'sha256':'a'*64})
        self.assertEqual(row['primary']['counts']['precision'],[0,0])
        self.assertEqual(row['zero_denominator_metrics'],['precision'])
        self.assertEqual(row['primary']['effective_clean_seconds'],3255)
        self.assertEqual(row['slices']['score_slices']['full-target']['motor-01.motor_current']['observed'],1800)
        self.assertEqual(row['slices']['evaluations'],1)
        self.assertEqual(result,before)

    def test_audit_primary_count_disagreement_is_rejected(self):
        result,audit=count_fixture();audit['ledger_audit']['metrics']['availability'][0]['metric'].update(numerator=1739,value=1739/1800)
        audit['profile_and_score_audit']['available_score_rows']=13919
        with self.assertRaisesRegex(ValueError,'availability'):flow._summarize(result,audit,evaluation_pin={})

    def test_missing_or_relabelled_slice_score_is_rejected(self):
        for change in ('missing','target'):
            result,audit=count_fixture()
            if change=='missing':result['scores'].pop()
            else:result['scores'][0]['full_target']='other'
            with self.subTest(change=change),self.assertRaises(ValueError):flow._summarize(result,audit,evaluation_pin={})
