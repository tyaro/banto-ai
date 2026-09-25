"""Invented declarations only: no observations, workers, scoring or inference."""
import ast
import copy
import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_consumer_input as consumer


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def failure(reason='worker_exit'):
    return {'stage': 'supervision', 'reason': reason, 'evidence_sha256': digest('failure')}


def attempt(chunk, number=1):
    return {'attempt': number, 'state': 'complete', 'failure': None, 'evaluations': [
        {'identity': copy.deepcopy(i), 'status': 'success', 'profile_status': 'calibrated',
         'input_hashes': {k: digest(i['dataset_id']+k) for k in consumer.INPUT_HASHES},
         'evaluation_sha256': digest(i['evaluation_id'])} for i in chunk['identities']]}


def coverage(value):
    count = dict.fromkeys(consumer.SLOT_STATES, 0)
    for chunk in value['chunks']:
        if chunk['attempts']:
            for row in chunk['attempts'][-1]['evaluations']:
                count[row['status']] += 1
        else:
            count['not_started'] += 6
    value['coverage'] = count


def complete(mode='fixture'):
    value = consumer.planned_input(mode)
    for chunk in value['chunks']:
        chunk['attempts'] = [attempt(chunk)]
    value['producer'].update(state='complete', writer_exited=True,
        receipt_sha256=digest('receipt'), marker_sha256=digest('marker'))
    coverage(value)
    return value


def check(value, **options):
    return consumer.validate_input(value, expected_mode=options.get('mode', value['mode']),
        expected_sha256=options.get('sha', consumer.v.canonical_sha256(value)))


class ConsumerInputTests(unittest.TestCase):
    def test_planned_fixture_and_engineering_are_fixed_fresh_metadata(self):
        for mode, chunks, slots in [('fixture', 1, 6), ('engineering-dev-smoke', 120, 720)]:
            value = consumer.planned_input(mode); report = check(value)
            self.assertEqual(report['planned_chunks'], chunks)
            self.assertEqual(report['coverage']['not_started'], slots)
            self.assertFalse(report['declared_complete'])
            self.assertEqual(report['next_step'], 'review_incomplete_declaration')
            value['chunks'][0]['identities'][0]['seed'] = -1
            self.assertNotEqual(value, consumer.planned_input(mode))

    def test_complete_metadata_never_grants_trust_or_execution(self):
        for mode, chunks, slots in [('fixture', 1, 6), ('engineering-dev-smoke', 120, 720)]:
            value = complete(mode); before = copy.deepcopy(value); result = check(value)
            self.assertEqual(value, before)
            self.assertTrue(result['declared_complete'])
            self.assertEqual(result['declared_complete_chunks'], chunks)
            self.assertEqual(result['coverage']['success'], slots)
            self.assertEqual(result['next_step'], 'authenticate_input_bytes')
            for key in ('input_bytes_verified', 'source_runtime_accepted', 'result_trusted',
                        'execution_authorized', 'analysis_authorized', 'formal_permission',
                        'promotion_allowed', 'independent_s6_complete'):
                self.assertIs(result[key], False)
            self.assertIsNone(result['selected_candidate'])
            self.assertEqual(result['performance_status'], 'not_evaluated')

    def test_formal_unknown_and_mixed_modes_reject_before_inventory_or_digest(self):
        with patch.object(consumer, 'planned_input', side_effect=AssertionError('no expansion')), \
             patch.object(consumer.v, 'canonical_sha256', side_effect=AssertionError('no traversal')):
            for mode in ('formal', 'holdout', 'anomaly-v03-single-writer-research-v1', '', None, True, []):
                with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, 'formal input is closed'):
                    consumer.validate_input(None, expected_mode=mode, expected_sha256=None)
        value = complete(); value['mode'] = 'formal'
        with self.assertRaisesRegex(ValueError, 'formal input is closed'):
            consumer.validate_input(value, expected_mode='fixture', expected_sha256=digest('x'))
        with self.assertRaisesRegex(ValueError, 'mode mismatch'):
            check(complete(), mode='engineering-dev-smoke')

    def test_closed_fields_reject_authorization_and_extra_nested_claims(self):
        for mutation in (
            lambda v: v.update(formal_permission=True),
            lambda v: v['producer'].update(accepted=True),
            lambda v: v['chunks'][0].update(runtime_accepted=True),
            lambda v: v['chunks'][0]['attempts'][0].update(verified=True),
            lambda v: v['chunks'][0]['attempts'][0]['evaluations'][0].update(raw_data=[]),
        ):
            value = complete(); mutation(value)
            with self.assertRaises(ValueError):check(value)

    def test_wrong_policy_registry_format_or_external_digest_rejected(self):
        for field in ('format', 'policy_id', 'registry_raw_sha256'):
            value = complete('engineering-dev-smoke'); value[field] = digest('wrong')
            with self.assertRaisesRegex(ValueError, 'contract binding'):check(value)
        with self.assertRaisesRegex(ValueError, 'external metadata digest mismatch'):
            check(complete(), sha=digest('wrong external'))
        for sha in (None, '', 'A'*64, 123, 'f'*63):
            with self.assertRaisesRegex(ValueError, 'invalid digest'):check(complete(), sha=sha)

    def test_missing_duplicate_reordered_and_wrong_identity_inventory_rejected(self):
        for mutation in (
            lambda v: v['chunks'].pop(),
            lambda v: v['chunks'].append(copy.deepcopy(v['chunks'][0])),
            lambda v: v['chunks'][0].update(chunk_index=True),
            lambda v: v['chunks'][0]['identities'].reverse(),
            lambda v: v['chunks'][0]['identities'][0].update(role='holdout'),
            lambda v: v['chunks'][0]['identities'][0].update(seed=True),
            lambda v: v['chunks'][0]['attempts'][0]['evaluations'].pop(),
            lambda v: v['chunks'][0]['attempts'][0]['evaluations'].reverse(),
            lambda v: v['chunks'][0]['attempts'][0]['evaluations'][0]['identity'].update(layout=1),
        ):
            value=complete(); mutation(value)
            with self.assertRaises(ValueError):check(value)
        value=complete('engineering-dev-smoke');value['chunks'][0],value['chunks'][1]=value['chunks'][1],value['chunks'][0]
        with self.assertRaises(ValueError):check(value)

    def test_all_six_input_pins_required_and_candidates_share_each_dataset(self):
        for key in consumer.INPUT_HASHES:
            value=complete(); row=value['chunks'][0]['attempts'][0]['evaluations'][1]
            row['input_hashes'][key]=digest('changed '+key)
            with self.assertRaisesRegex(ValueError, 'candidate/retry input pins differ'):check(value)
            value=complete();del value['chunks'][0]['attempts'][0]['evaluations'][0]['input_hashes'][key]
            with self.assertRaisesRegex(ValueError, 'input hash fields'):check(value)
        value=complete();rows=value['chunks'][0]['attempts'][0]['evaluations']
        self.assertNotEqual(rows[0]['input_hashes'],rows[3]['input_hashes'])
        self.assertTrue(check(value)['declared_complete'])

    def test_outcome_profile_and_completed_pin_requirements(self):
        for fields in ({'profile_status':'inconclusive'}, {'input_hashes':None},
                       {'evaluation_sha256':None}, {'evaluation_sha256':'X'*64},
                       {'status':True}, {'profile_status':None}):
            value=complete();value['chunks'][0]['attempts'][0]['evaluations'][0].update(fields)
            with self.assertRaises(ValueError):check(value)

    def test_profile_inconclusive_is_complete_but_not_success(self):
        value=complete();row=value['chunks'][0]['attempts'][0]['evaluations'][2]
        row.update(status='inconclusive',profile_status='inconclusive');coverage(value)
        result=check(value)
        self.assertTrue(result['declared_complete'])
        self.assertEqual(result['coverage'],{'success':5,'inconclusive':1,'partial':0,'failed':0,'not_started':0})
        self.assertEqual(result['failed_attempt_history'],[])
        self.assertFalse(result['analysis_authorized'])

    def test_incomplete_failed_partial_unstarted_counts_retained(self):
        value=complete();a=value['chunks'][0]['attempts'][0]
        a.update(state='failed',failure=failure())
        a['evaluations'][2].update(status='partial',evaluation_sha256=None)
        a['evaluations'][3].update(status='failed',evaluation_sha256=None)
        for row in a['evaluations'][4:]:
            row.update(status='not_started',profile_status='not_evaluated',input_hashes=None,evaluation_sha256=None)
        value['producer'].update(state='failed',failure=failure(),receipt_sha256=None,marker_sha256=None)
        coverage(value);result=check(value)
        self.assertEqual(result['coverage'],{'success':2,'inconclusive':0,'partial':1,'failed':1,'not_started':2})
        self.assertFalse(result['declared_complete']);self.assertEqual(result['declared_complete_chunks'],0)
        value['producer'].update(state='complete',failure=None,receipt_sha256=digest('r'),marker_sha256=digest('m'))
        with self.assertRaisesRegex(ValueError,'complete producer lacks'):check(value)

    def test_complete_attempt_cannot_hide_partial_or_not_started_slots(self):
        for status in ('partial','failed','not_started'):
            value=complete();row=value['chunks'][0]['attempts'][0]['evaluations'][0]
            row.update(status=status,profile_status='not_evaluated',input_hashes=None,evaluation_sha256=None);coverage(value)
            with self.assertRaisesRegex(ValueError,'complete attempt has unfinished'):check(value)

    def test_unstarted_slot_cannot_carry_result_and_partial_cannot_claim_complete_result(self):
        for status in ('not_started','partial','failed'):
            value=complete();a=value['chunks'][0]['attempts'][0];a.update(state='failed',failure=failure())
            a['evaluations'][0]['status']=status
            with self.assertRaises(ValueError):check(value)

    def test_retry_retains_failed_attempt_and_uses_latest_coverage(self):
        value=complete();chunk=value['chunks'][0];first=copy.deepcopy(chunk['attempts'][0])
        first.update(state='failed',failure=failure('resource_limit'))
        first['evaluations'][5].update(status='partial',evaluation_sha256=None)
        chunk['attempts']=[first,attempt(chunk,2)]
        result=check(value)
        self.assertEqual(result['coverage']['success'],6)
        self.assertEqual(result['attempt_count'],2)
        self.assertEqual(result['failed_attempt_history'],[{'chunk_index':0,'attempt':1,'failure':failure('resource_limit'),'is_latest':False}])
        result['failed_attempt_history'][0]['failure']['reason']='changed'
        self.assertEqual(first['failure']['reason'],'resource_limit')

    def test_missing_failed_history_wrong_sequence_integrity_retry_and_changed_inputs_rejected(self):
        for change in ('sequence','bool','successful_previous','integrity','changed_inputs'):
            value=complete();chunk=value['chunks'][0];first=copy.deepcopy(chunk['attempts'][0])
            first.update(state='failed',failure=failure());chunk['attempts']=[first,attempt(chunk,2)]
            if change=='sequence':chunk['attempts'][1]['attempt']=3
            elif change=='bool':first['attempt']=True
            elif change=='successful_previous':first.update(state='complete',failure=None)
            elif change=='integrity':first['failure']['reason']='hash_mismatch'
            else:
                for row in chunk['attempts'][1]['evaluations'][:3]:row['input_hashes']['observations']=digest('changed')
            with self.subTest(change=change),self.assertRaises(ValueError):check(value)

    def test_failed_supervision_after_valid_publication_never_implies_completion(self):
        value=complete();value['producer'].update(state='failed',failure=failure())
        result=check(value)
        self.assertFalse(result['declared_complete'])
        self.assertEqual(result['declared_complete_chunks'],1)
        self.assertEqual(result['producer_failure'],failure())
        self.assertEqual(value['producer']['marker_sha256'],digest('marker'))

    def test_complete_producer_requires_exit_and_both_publication_references(self):
        for fields in ({'writer_exited':False},{'writer_exited':1},{'receipt_sha256':None},
                       {'marker_sha256':None},{'receipt_sha256':None,'marker_sha256':None},
                       {'failure':failure()}):
            value=complete();value['producer'].update(fields)
            with self.assertRaises(ValueError):check(value)

    def test_in_progress_and_prelaunch_failure_do_not_lose_unstarted_slots(self):
        value=consumer.planned_input('fixture');value['producer']['state']='in_progress'
        result=check(value);self.assertEqual(result['next_step'],'wait_for_writer')
        self.assertEqual(result['coverage']['not_started'],6)
        value['producer'].update(state='failed',writer_exited=True,failure=failure('exception'))
        self.assertFalse(check(value)['declared_complete'])
        value['producer']['failure']=None
        with self.assertRaises(ValueError):check(value)

    def test_in_progress_cannot_claim_final_exit_marker_or_failed_evaluation(self):
        for change in ('exit','marker','failed'):
            value=complete();value['producer'].update(state='in_progress',writer_exited=False,receipt_sha256=None,marker_sha256=None)
            a=value['chunks'][0]['attempts'][0];a['state']='in_progress'
            if change=='exit':value['producer']['writer_exited']=True
            elif change=='marker':value['producer'].update(receipt_sha256=digest('r'),marker_sha256=digest('m'))
            else:a['evaluations'][0].update(status='failed',evaluation_sha256=None)
            coverage(value)
            with self.assertRaises(ValueError):check(value)

    def test_coverage_counts_are_derived_not_trusted_and_numbers_are_strict(self):
        for counts in ({'success':True}, {'success':6.0}, {'success':5}, {'extra':0}):
            value=complete();value['coverage'].update(counts)
            with self.assertRaises(ValueError):check(value)

    def test_malformed_failures_and_oversized_attempt_history_are_rejected(self):
        for bad in (None,{},failure('profile_inconclusive'),{'stage':'supervision','reason':'worker_exit','evidence_sha256':True}):
            value=complete();a=value['chunks'][0]['attempts'][0];a.update(state='failed',failure=bad)
            with self.assertRaises(ValueError):check(value)
        value=complete();value['chunks'][0]['attempts']*=consumer.MAX_ATTEMPTS+1
        with self.assertRaisesRegex(ValueError,'attempt history bound'):check(value)

    def test_json_roundtrip_order_and_supplied_digest_not_mutated(self):
        value=complete();raw=consumer.v.canonical_json(value)
        decoded=consumer.v.strict_json(raw)
        self.assertEqual(check(value),check(decoded))
        before=consumer.v.canonical_sha256(value);check(value)
        self.assertEqual(consumer.v.canonical_sha256(value),before)

    def test_validation_has_no_io_or_numerical_execution_calls(self):
        value=complete('engineering-dev-smoke');expected=consumer.v.canonical_sha256(value)
        with patch('builtins.open',side_effect=AssertionError('no file IO')), \
             patch.object(Path,'open',side_effect=AssertionError('no path IO')), \
             patch('subprocess.Popen',side_effect=AssertionError('no process')), \
             patch.object(consumer.v,'bootstrap_indices',side_effect=AssertionError('no bootstrap')):
            result=consumer.validate_input(value,expected_mode=value['mode'],expected_sha256=expected)
        self.assertEqual(result['coverage']['success'],720)
        tree=ast.parse(Path(consumer.__file__).read_bytes())
        imports=[n for n in ast.walk(tree) if isinstance(n,(ast.Import,ast.ImportFrom))]
        self.assertEqual([n.module for n in imports if isinstance(n,ast.ImportFrom) and n.level], [None,None])
        local_names=[a.name for n in imports if isinstance(n,ast.ImportFrom) and n.level for a in n.names]
        self.assertEqual(local_names,['anomaly_v03','_anomaly_v03_contract'])


if __name__=='__main__':unittest.main()
