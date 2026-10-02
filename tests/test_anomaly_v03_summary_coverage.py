"""Invented retained metadata/receipts only, not 720 numeric audits.

One hand-counted template is copied for binding tests. Copying its counts to
other identities does not assert that those layouts produced these values.
"""
import copy
from contextlib import ExitStack
from functools import lru_cache
import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_summary_coverage as binding
from tests import test_anomaly_v03_consumer_checkpoints as checkpoints
from tests import test_anomaly_v03_saved_chunk_summary as saved

v=binding.v
flow=binding.summary
SAVEPOINT={'bytes':1,'sha256':'b'*64}
EVIDENCE={'bytes':1,'sha256':'c'*64}


def encoded(value):return v.canonical_json(value)+b'\n'
def pin(raw):return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


@lru_cache(maxsize=1)
def fixture_metadata():
    checkpoints.ConsumerCheckpointTests.setUpClass()
    f,entries=copy.deepcopy(checkpoints.ConsumerCheckpointTests.baseline)
    entries[-1]['manifest']['slots'][0]['status']='inconclusive'
    checkpoints.legacy.refresh_coverage(entries[-1]['manifest'])
    f.records[-1]['status']='verified_inconclusive'
    f.records[-1]['outcome']['slots'][0]['status']='inconclusive';f.rechain()
    return checkpoints.adapter.adapt_completed_journal(f.plan,f.records,entries,
        expected_mode=checkpoints.adapter.MODE,expected_plan_sha256=f.plan_hash,
        expected_record_count=len(f.records),expected_head_sha256=f.head,
        expected_manifests_sha256=v.canonical_sha256(entries))


@lru_cache(maxsize=2)
def template(inconclusive):
    result,audit=saved.count_fixture()
    if inconclusive:
        for profile in result['profiles']:profile['status']='inconclusive'
        for score in result['scores']:score['available']=False
        for item in audit['ledger_audit']['metrics']['availability']:item['metric'].update(numerator=0,value=0.0)
        audit['ledger_audit']['metrics'].update(effective_clean_seconds=0,effective_clean_rate=None)
        names=[result['identity']['evaluation_id']+f'-profile-{e}-{t}-{m}'
            for e in ('motor-01','conveyor-01') for t in flow.reader.scores.TARGETS for m in flow.reader.scores.MODES]
        audit['profile_and_score_audit'].update(evaluation_outcome='inconclusive',available_score_rows=0,
            inconclusive_profiles=[{'profile_id':n,'reason':'zero_scale'} for n in names])
        audit['evaluation_outcome']='inconclusive'
    row=flow._summarize(result,audit,evaluation_pin={'bytes':1,'sha256':'a'*64})
    return row,audit


def fixture_report(meta,index,mode='fixture'):
    chunk=meta['chunks'][index];latest=chunk['attempts'][-1];attempt=latest['attempt']
    stem=f'run/attempts/chunks/{index:03d}/attempt-{attempt:04d}'
    pins={'run/metadata/plan.json':{'bytes':1,'sha256':'d'*64},
        stem+'/audit/report.json':{'bytes':1,'sha256':latest['evidence']['audit_sha256']}}
    rows=[];audits=[]
    for slot in latest['evaluations']:
        row,audit=copy.deepcopy(template(slot['status']=='inconclusive'))
        identity=copy.deepcopy(slot['identity']);old=row['identity']['evaluation_id']
        row.update(identity=identity,input_hashes=copy.deepcopy(slot['input_hashes']),
            evaluation_pin={'bytes':1,'sha256':slot['evaluation_sha256']})
        audit['identity']=copy.deepcopy(identity);audit['profile_and_score_audit']['identity']=copy.deepcopy(identity)
        for values in (row['inconclusive_profiles'],audit['profile_and_score_audit']['inconclusive_profiles']):
            for item in values:item['profile_id']=item['profile_id'].replace(old,identity['evaluation_id'])
        rows.append(row);audits.append(audit)
        for key,name in flow.reader.DATASET_INPUTS.items():
            pins[stem+'/result/payload/datasets/'+identity['dataset_id']+'/'+name]={'bytes':1,'sha256':slot['input_hashes'][key]}
        pins[stem+'/result/payload/evaluations/'+identity['evaluation_id']+'.json']=copy.deepcopy(row['evaluation_pin'])
    return {**flow.CLOSED,'format':flow.FORMAT,'mode':mode,'status':'selected_chunk_summaries_verified',
        'scope':'one-completed-dev-smoke-chunk','chunk_index':index,'attempt':attempt,
        'prior_attempts_not_credited':attempt-1,'evaluations_checked':6,'evaluations':rows,
        'current_observation_profile_score_audit':True,'current_ledger_audit':True,
        'primary_slice_consistency_checked':True,'full_event_ledger_bytes_matched':True,
        'all_campaign_payloads_read':False,'raw_generation_verified':False,
        'data_origin':'caller-declared-fixture' if mode=='fixture' else 'saved-dev-smoke',
        'audit':{**flow.primary.QUIET,'format':'anomaly-v03-connected-observation-audit-v1',
            'status':'selected_chunk_checks_passed','scope':'selected-completed-dev-smoke-chunk',
            'chunk_index':index,'attempt':attempt,'prior_attempts_not_credited':attempt-1,
            'evaluations_checked':6,'profile_derivation_verified':True,'score_derivation_verified':True,
            'ledger_derivation_verified':True,'campaign_evaluations_credited':0,'evidence_pin':copy.deepcopy(EVIDENCE),
            'trust_anchor':{'path':'C:/invented/completed.json',**SAVEPOINT},'run_root':'C:/invented/run',
            'input_pins':pins,'input_bytes':sum(p['bytes'] for p in pins.values()),'evaluations':audits}}


def bind(meta,reports,**overrides):
    raw=encoded(meta);summaries={i:encoded(r) for i,r in reports.items()}
    args={'expected_mode':'fixture','expected_metadata_pin':pin(raw),
        'expected_summary_pins':{i:pin(b) for i,b in summaries.items()},
        'expected_savepoint_pin':SAVEPOINT,'expected_evidence_pin':EVIDENCE}
    return binding.bind_summary_coverage(raw,summaries,**(args|overrides))


class SummaryCoverageTests(unittest.TestCase):
    def setUp(self):
        self.meta=copy.deepcopy(fixture_metadata())
        self.report=fixture_report(self.meta,119)

    def test_one_latest_chunk_keeps_119_missing_and_unknown_failure_history(self):
        out=bind(self.meta,{119:self.report})
        self.assertEqual(out['status'],'partial_summary_binding')
        self.assertEqual(out['bound_summary_evaluations'],6)
        self.assertEqual(out['unverified_summary_evaluations'],714)
        self.assertEqual(out['missing_summary_chunks'],list(range(119)))
        self.assertEqual(out['declared_coverage']['success'],719)
        self.assertEqual(out['bound_summary_coverage']['inconclusive'],1)
        self.assertEqual(out['summaries'][0]['attempt'],2)
        self.assertEqual(out['zero_denominator_metrics_retained'],6)
        self.assertEqual(out['failed_attempt_history'],self.meta['failed_attempt_history'])
        self.assertEqual(out['failed_attempt_history'][0]['evaluation_detail'],'unreported')
        self.assertFalse(out['all_summary_inputs_bound'])
        for key,value in flow.CLOSED.items():self.assertEqual(out[key],value)

    def test_empty_supplied_set_does_not_inherit_declared_completion(self):
        out=bind(self.meta,{})
        self.assertEqual(out['unverified_summary_evaluations'],720)
        self.assertEqual(out['bound_summary_evaluations'],0)
        self.assertEqual(out['status'],'partial_summary_binding')

    def test_formal_unknown_rejected_before_hash_or_decode(self):
        with patch.object(binding,'_load',side_effect=AssertionError('decode')):
            for mode in ('formal','holdout',None,True):
                with self.subTest(mode=mode),self.assertRaises(ValueError):
                    binding.bind_summary_coverage(None,None,expected_mode=mode,expected_metadata_pin=None,
                        expected_summary_pins=None,expected_savepoint_pin=None,expected_evidence_pin=None)

    def test_external_metadata_summary_and_anchor_pins_are_required(self):
        for change in ({'expected_metadata_pin':SAVEPOINT},{'expected_summary_pins':{119:SAVEPOINT}},
                       {'expected_savepoint_pin':EVIDENCE},{'expected_evidence_pin':SAVEPOINT}):
            with self.subTest(change=change),self.assertRaises(ValueError):bind(self.meta,{119:self.report},**change)

    def test_exact_supplied_pin_inventory_and_strict_indexes(self):
        for reports,pins in (({119:self.report},{}),({}, {119:SAVEPOINT}),
                             ({True:self.report},{1:pin(encoded(self.report))}),
                             ({120:self.report},{120:pin(encoded(self.report))})):
            with self.subTest(indexes=list(reports)),self.assertRaises(ValueError):
                bind(self.meta,reports,expected_summary_pins=pins)

    def test_metadata_omission_duplicate_relabel_and_attempt_rewind_rejected(self):
        for kind in ('missing','duplicate','holdout','rewind','head','sequence','failure'):
            value=copy.deepcopy(self.meta)
            if kind=='missing':value['chunks'].pop(0)
            if kind=='duplicate':value['chunks'][1]=copy.deepcopy(value['chunks'][0])
            if kind=='holdout':value['chunks'][0]['identities'][0]['role']='holdout'
            if kind=='rewind':value['chunks'][-1]['selected_attempt']=1
            if kind=='head':value['bindings']['head_sha256']='0'*64
            if kind=='sequence':value['chunks'][0]['attempts'][0]['record_sequences'].pop()
            if kind=='failure':value['failed_attempt_history'].clear()
            with self.subTest(kind=kind),self.assertRaises(ValueError):bind(value,{119:self.report})

    def test_duplicate_chunk_summary_cannot_cover_another_index(self):
        with self.assertRaises(ValueError):bind(self.meta,{118:self.report,119:self.report})

    def test_old_attempt_and_reordered_or_missing_evaluation_rejected(self):
        for kind in ('attempt','order','missing'):
            report=copy.deepcopy(self.report)
            if kind=='attempt':report['attempt']=1
            if kind=='order':report['evaluations'][:2]=report['evaluations'][:2][::-1]
            if kind=='missing':report['evaluations'].pop()
            with self.subTest(kind=kind),self.assertRaises(ValueError):bind(self.meta,{119:report})

    def test_summary_input_result_and_historical_audit_hash_disagreement_rejected(self):
        for kind in ('input','result','audit','inventory'):
            report=copy.deepcopy(self.report)
            if kind=='input':report['evaluations'][0]['input_hashes']['observations']='0'*64
            if kind=='result':report['evaluations'][0]['evaluation_pin']['sha256']='0'*64
            if kind=='audit':
                name=next(n for n in report['audit']['input_pins'] if n.endswith('/audit/report.json'))
                report['audit']['input_pins'][name]['sha256']='0'*64
            if kind=='inventory':report['audit']['input_pins']['unexpected']={'bytes':1,'sha256':'a'*64}
            with self.subTest(kind=kind),self.assertRaises(ValueError):bind(self.meta,{119:report})

    def test_common_campaign_context_cannot_mix_reports(self):
        for key in ('run_root','trust_anchor','plan'):
            earlier=fixture_report(self.meta,0)
            if key=='run_root':earlier['audit'][key]='C:/other/run'
            if key=='trust_anchor':earlier['audit'][key]['path']='C:/other/completed.json'
            if key=='plan':earlier['audit']['input_pins']['run/metadata/plan.json']['sha256']='0'*64
            with self.subTest(key=key),self.assertRaises(ValueError):bind(self.meta,{0:earlier,119:self.report})

    def test_counts_slices_and_inconclusive_diagnostics_cannot_be_resealed_inconsistently(self):
        for kind in ('primary','slice','diagnostics','outcome','zero'):
            report=copy.deepcopy(self.report);row=report['evaluations'][0]
            if kind=='primary':row['primary']['counts']['precision']=[0,1]
            if kind=='slice':row['slices']['score_slices']['full-target']['motor-01.motor_current']['available']=1
            if kind=='diagnostics':row['inconclusive_profiles'].clear()
            if kind=='outcome':row['evaluation_outcome']='success'
            if kind=='zero':row['zero_denominator_metrics'].clear()
            with self.subTest(kind=kind),self.assertRaises(ValueError):bind(self.meta,{119:report})

    def test_permission_or_audit_claim_changes_rejected(self):
        for key,value in (('formal_permission',True),('analysis_authorized',True),('current_ledger_audit',False),
                          ('mode','engineering'),('data_origin','saved-dev-smoke')):
            report=copy.deepcopy(self.report);report[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):bind(self.meta,{119:report})

    def test_engineering_mode_preserves_real_format_identity_without_promoting_trust(self):
        report=fixture_report(self.meta,119,mode='engineering')
        out=bind(self.meta,{119:report},expected_mode='engineering')
        self.assertEqual(out['mode'],'engineering');self.assertFalse(out['result_trusted'])
        self.assertEqual(out['summaries'][0]['evaluation_ids'],[i['evaluation_id'] for i in self.meta['chunks'][119]['identities']])

    def test_duplicate_json_keys_and_byte_caps_fail_closed(self):
        raw=encoded(self.meta);good=encoded(self.report)
        for bad in (b'{"a":1,"a":2}',b' '*(binding.MAX_SUMMARY+1)):
            with self.subTest(size=len(bad)),self.assertRaises(ValueError):
                binding.bind_summary_coverage(raw,{119:bad},expected_mode='fixture',expected_metadata_pin=pin(raw),
                    expected_summary_pins={119:pin(bad)},expected_savepoint_pin=SAVEPOINT,expected_evidence_pin=EVIDENCE)

    def test_pure_boundary_does_not_open_paths_replay_or_mutate(self):
        before=encoded([self.meta,self.report])
        with ExitStack() as stack:
            for target in ('builtins.open','io.open','subprocess.Popen',
                           'banto_ai.anomaly_v03_checkpoints.reduce_journal',
                           'banto_ai.anomaly_v03_observation_audit.audit_completed_chunk',
                           'banto_ai.anomaly_v03_score_audit.audit_score_derivation',
                           'banto_ai.anomaly_v03_ledger_audit.audit_evaluation'):
                stack.enter_context(patch(target,side_effect=AssertionError('forbidden '+target)))
            stack.enter_context(patch.object(Path,'read_bytes',side_effect=AssertionError('path read')))
            out=bind(self.meta,{119:self.report})
        self.assertEqual(out['current_source_payloads_read'],0)
        self.assertEqual(out['numeric_audits_repeated'],0)
        out['failed_attempt_history'][0]['terminal_record'].clear()
        self.assertEqual(encoded([self.meta,self.report]),before)


if __name__=='__main__':unittest.main()
