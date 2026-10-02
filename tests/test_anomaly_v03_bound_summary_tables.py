"""Invented compact receipts and hand counts; no actual campaign replay."""
import copy
from contextlib import ExitStack
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_bound_summary_tables as tables
from tests import test_anomaly_v03_summary_coverage as fixture
from tests import test_anomaly_v03_slices as hand


def detected_template():
    result,audit=fixture.saved.count_fixture();hand.detect_one(result,audit)
    metrics=audit['ledger_audit']['metrics'];metrics['sensor_recall']['value']=.1
    metrics['precision'].update(value=1.0,ci_status='not_evaluated',ci_lower=None,ci_upper=None,null_replicates=0)
    audit['ledger_audit']['equipment_episodes']=1
    return fixture.flow._summarize(result,audit,evaluation_pin={'bytes':1,'sha256':'a'*64}),audit


class BoundSummaryTablesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        meta=fixture.fixture_metadata();summaries={};pins={}
        for index in range(120):
            report=fixture.fixture_report(meta,index)
            if index==0:
                row,audit=detected_template();old=report['evaluations'][0]
                # This row is the hand template's original registered identity.
                assert row['identity']==old['identity']
                row['input_hashes']=old['input_hashes'];row['evaluation_pin']=old['evaluation_pin']
                report['evaluations'][0]=row;report['audit']['evaluations'][0]=audit
            raw=fixture.encoded(report);summaries[index]=raw;pins[index]=fixture.pin(raw)
        raw=fixture.encoded(meta)
        bound=tables.binding.bind_summary_coverage(raw,summaries,expected_mode='fixture',expected_metadata_pin=fixture.pin(raw),
            expected_summary_pins=pins,expected_savepoint_pin=fixture.SAVEPOINT,expected_evidence_pin=fixture.EVIDENCE)
        cls.retained=bound;cls.raw=fixture.encoded(bound);cls.summaries=summaries
        with ExitStack() as stack:
            for target in ('builtins.open','io.open','subprocess.Popen',
                           'banto_ai.anomaly_v03_checkpoints.reduce_journal',
                           'banto_ai.anomaly_v03_summary_coverage.bind_summary_coverage',
                           'banto_ai.anomaly_v03_score_audit.audit_score_derivation',
                           'banto_ai.anomaly_v03_ledger_audit.audit_evaluation',
                           'banto_ai.anomaly_v03_inference_audit.draw_index'):
                stack.enter_context(patch(target,side_effect=AssertionError('forbidden '+target)))
            stack.enter_context(patch.object(Path,'read_bytes',side_effect=AssertionError('path read')))
            cls.output=tables.aggregate_bound_summaries(cls.raw,summaries,expected_binding_pin=fixture.pin(cls.raw),expected_mode='fixture')

    def call(self,*,retained=None,summaries=None,**overrides):
        raw=self.raw if retained is None else fixture.encoded(retained)
        return tables.aggregate_bound_summaries(raw,self.summaries if summaries is None else summaries,
            **({'expected_binding_pin':fixture.pin(raw),'expected_mode':'fixture'}|overrides))

    def modified_first(self,edit):
        bound=copy.deepcopy(self.retained);summaries=self.summaries.copy()
        report=json.loads(summaries[0]);edit(report);summaries[0]=fixture.encoded(report)
        bound['summaries'][0]['summary_pin']=fixture.pin(summaries[0])
        return bound,summaries

    def test_registered_tables_keep_populations_and_expected_sizes(self):
        out=self.output
        self.assertEqual(out['status'],'complete_dev_smoke_descriptive_tables')
        self.assertEqual([len(out[k]) for k in ('by_seed','by_role','seed_clusters','paired_descriptive')],[90,18,10,12])
        self.assertEqual({r['role'] for r in out['by_role']},{'dev','smoke'})
        self.assertEqual(out['coverage'],self.retained['declared_coverage'])
        for r in out['by_seed']:self.assertEqual(r['evaluations'],24 if r['stratum']=='overall' else 12)
        for r in out['by_role']:
            self.assertEqual(r['evaluations'],(8 if r['role']=='dev' else 2)*(24 if r['stratum']=='overall' else 12))

    def test_pooling_keeps_zero_denominator_inputs_and_hand_detection(self):
        core=self.output['by_seed'][0];overall=self.output['by_seed'][2]
        self.assertEqual(core['counts']['precision'],[1,1]);self.assertEqual(core['points']['precision'],1.0)
        self.assertEqual(core['counts']['sensor_recall'],[1,120]);self.assertEqual(core['points']['sensor_recall'],1/120)
        self.assertEqual(len(core['undefined_input_points']),11)
        self.assertEqual(overall['counts']['sensor_recall'],[1,240]);self.assertEqual(overall['delay_histogram'],[1,0,0,0,0])
        self.assertEqual(overall['delay_summary']['mean'],1.0)
        self.assertEqual(self.output['zero_denominator_input_metrics'],719)
        empty=next(r for r in self.output['by_role'] if r['role']=='smoke')
        self.assertIsNone(empty['points']['precision']);self.assertIsNone(empty['delay_summary']['median'])

    def test_inconclusive_and_failed_retry_remain_visible(self):
        rows=[r for r in self.output['by_seed'] if r['profile_status']=='inconclusive']
        self.assertEqual(len(rows),2)
        self.assertTrue(all(r['profile_inconclusive_evaluations']==1 for r in rows))
        self.assertTrue(all(len(r['profile_diagnostics'][0]['profiles'])==48 for r in rows))
        self.assertEqual(self.output['failed_attempt_history'],self.retained['failed_attempt_history'])
        self.assertEqual(self.output['source_summaries'][-1]['attempt'],2)

    def test_all_closed_flags_and_no_replays_are_retained(self):
        for key,value in tables.flow.CLOSED.items():self.assertEqual(self.output[key],value)
        self.assertFalse(self.output['journal_replayed'])
        self.assertEqual(self.output['numeric_audits_repeated'],0)
        self.assertEqual(self.output['ledger_audits_repeated'],0)
        self.assertEqual(self.output['current_source_payloads_read'],0)
        self.assertEqual(self.output['real_performance_intervals_computed'],0)
        self.assertTrue(all(r['ci_status']=='not_evaluated' for r in self.output['by_role']))
        self.assertEqual(fixture.encoded(self.retained),self.raw)

    def test_formal_unknown_rejected_before_decode(self):
        with patch.object(tables.binding,'_load',side_effect=AssertionError('decode')):
            for mode in ('formal','holdout',None,True):
                with self.subTest(mode=mode),self.assertRaises(ValueError):
                    tables.aggregate_bound_summaries(None,None,expected_binding_pin=None,expected_mode=mode)

    def test_partial_binding_cannot_produce_whole_tables(self):
        for name,value in (('status','partial_summary_binding'),('all_summary_inputs_bound',False),
                           ('missing_summary_chunks',[119]),('unverified_summary_evaluations',6)):
            bound=copy.deepcopy(self.retained);bound[name]=value
            with self.subTest(name=name),patch.object(tables,'_tables',side_effect=AssertionError('aggregation')), \
                 self.assertRaises(ValueError):self.call(retained=bound)

    def test_missing_extra_and_bool_summary_indexes_rejected(self):
        for change in ('missing','extra','bool'):
            rows=self.summaries.copy()
            if change=='missing':rows.pop(119)
            if change=='extra':rows[120]=rows[0]
            if change=='bool':rows[False]=rows.pop(0)
            with self.subTest(change=change),self.assertRaises(ValueError):self.call(summaries=rows)

    def test_external_pin_and_changed_last_summary_fail_before_aggregation(self):
        with self.assertRaises(ValueError):self.call(expected_binding_pin=fixture.SAVEPOINT)
        rows=self.summaries.copy();rows[119]+=b' '
        with patch.object(tables,'_rows',side_effect=AssertionError('count processing')),self.assertRaises(ValueError):
            self.call(summaries=rows)

    def test_bound_duplicate_reordered_or_relabelled_identity_rejected(self):
        for kind in ('duplicate','reordered','identity','bool_attempt'):
            bound=copy.deepcopy(self.retained)
            if kind=='duplicate':bound['summaries'][1]=copy.deepcopy(bound['summaries'][0])
            if kind=='reordered':bound['summaries'][:2]=bound['summaries'][:2][::-1]
            if kind=='identity':bound['summaries'][0]['evaluation_ids'][0]='holdout'
            if kind=='bool_attempt':bound['summaries'][0]['attempt']=True
            with self.subTest(kind=kind),self.assertRaises(ValueError):self.call(retained=bound)

    def test_resealed_summary_attempt_context_or_counts_cannot_disagree(self):
        edits=[lambda r:r.update(attempt=2),lambda r:r['audit'].update(run_root='C:/other'),
               lambda r:r['evaluations'][0]['primary']['counts'].update(precision=[0,0]),
               lambda r:r['evaluations'][0]['slices']['score_slices']['full-target']['motor-01.motor_current'].update(available=1),
               lambda r:r['evaluations'][0].update(zero_denominator_metrics=['precision'])]
        for index,edit in enumerate(edits):
            bound,rows=self.modified_first(edit)
            with self.subTest(index=index),self.assertRaises(ValueError):self.call(retained=bound,summaries=rows)

    def test_binding_permission_or_population_changes_rejected(self):
        for key,value in (('formal_permission',True),('analysis_authorized',True),('mode','engineering'),('planned_evaluations',2880)):
            bound=copy.deepcopy(self.retained);bound[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.call(retained=bound)

    def test_json_object_order_and_output_serialization(self):
        # Canonical input sorting has already passed the full real path once.
        self.assertEqual(json.loads(fixture.encoded(self.output)),self.output)
        self.assertEqual(self.output['by_seed'][0]['score_slices'][0]['dimension'],'full-target')


if __name__=='__main__':unittest.main()
