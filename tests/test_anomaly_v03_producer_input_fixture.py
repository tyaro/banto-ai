"""Invented byte snapshots exercise registration/attempt/count joins without IO."""
import copy
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
from banto_ai import anomaly_v03_producer_input_fixture as bound
from banto_ai import anomaly_v03_analysis_adapter as adapter
from banto_ai import anomaly_v03_document_fixture as document
from banto_ai import anomaly_v03_wrapper_fixture as wrapper


def pack(snapshots,chunks,*,state='complete',worker=None,failure=None):
    registration_pin = bound.pin(snapshots['registration.json'])
    close = {'format':bound.CLOSE_FORMAT,'mode':'fixture','registration_pin':registration_pin,'state':state,
        'worker':worker or {'exit_confirmed':state in ('complete','failed'),'exit_code':0 if state == 'complete' else 1 if state == 'failed' else None,'observation_errors':[]},
        'failure':failure,'latest_attempt_pins':[bound.pin(snapshots[bound.attempt_path(c['chunk_index'],c['attempt_count'])]) if c['attempt_count'] else None for c in chunks]}
    snapshots['producer/completion.json'] = bound.v.canonical_json(close)
    manifest = {'format':bound.FORMAT,'mode':'fixture','registration_pin':registration_pin,'chunks':copy.deepcopy(chunks),
        'payload_pins':{n:bound.pin(b) for n,b in snapshots.items()}}
    raw = bound.v.canonical_json(manifest)
    return {'manifest_raw':raw,'snapshots':snapshots,'expected_mode':'fixture','expected_manifest_pin':bound.pin(raw),
        'expected_registration_pin':registration_pin}


def example(clusters=1,*,retry=False,empty=False,zero_control=False,inconclusive=False,failed_latest=False):
    registration = bound.plan(clusters);identities = bound.inventory(registration)
    snapshots = {'registration.json':bound.v.canonical_json(registration)};registration_pin = bound.pin(snapshots['registration.json'])
    chunks = [];failure = {'stage':'supervision','reason':'worker_exit','evidence_sha256':None}
    for index in range(len(identities)//6):
        wanted = identities[index*6:index*6+6];count = 0 if empty else 2 if retry and index == 0 else 1
        chunks.append({'chunk_index':index,'attempt_count':count})
        for number in range(1,count+1):
            previous_failed = number < count;state = 'failed' if previous_failed or failed_latest and index == 0 else 'complete'
            slots = []
            for offset,identity in enumerate(wanted):
                hashes = {}
                for kind in bound.metadata.INPUT_HASHES:
                    path = bound.input_path(identity,kind)
                    snapshots[path] = bound.v.canonical_json({'format':bound.INPUT_FORMAT,'invented_only':True,
                        'dataset_id':identity['dataset_id'],'kind':kind,'token':'invented-'+kind})
                    hashes[kind] = bound.pin(snapshots[path])['sha256']
                profile = 'inconclusive' if inconclusive and index == offset == 0 else 'calibrated'
                status = 'inconclusive' if profile == 'inconclusive' else 'success'
                slot = {'identity':copy.deepcopy(identity),'status':'partial' if previous_failed else status,
                    'profile_status':'not_evaluated' if previous_failed else profile,'input_hashes':hashes,'evaluation_sha256':None}
                if not previous_failed:
                    candidate = bound.arithmetic.CANDIDATES.index(identity['candidate_id']);layout = identity['layout']
                    machine = 0 if zero_control and candidate == 0 else 2+layout%3 if candidate == 0 else 9
                    sensor = 0 if zero_control and candidate == 0 else 3+identity['seed']%2 if candidate == 0 else 8
                    false = int(candidate == 0 and not zero_control);detected = machine+sensor
                    counts = {'machine_recall':[machine,10],'sensor_recall':[sensor,10],'precision':[detected,detected+false],
                        'clean_rate':[false,3365],'false_alert_burden':[false,20],
                        **{m:[1700+20*candidate+layout,1800] for m in bound.arithmetic.AVAILABILITY}}
                    histogram = [0]*5;histogram[layout%5] = detected
                    value = {'format':bound.SUMMARY_FORMAT,'mode':'fixture','invented_only':True,'registration_pin':registration_pin,
                        'identity':copy.deepcopy(identity),'attempt':number,'input_hashes':copy.deepcopy(hashes),'profile_status':profile,
                        'counts':counts,'effective_clean_seconds':3300+layout,'delay_histogram':histogram}
                    path = bound.summary_path(identity,number);snapshots[path] = bound.v.canonical_json(value)
                    slot['evaluation_sha256'] = bound.pin(snapshots[path])['sha256']
                slots.append(slot)
            record = {'format':bound.ATTEMPT_FORMAT,'mode':'fixture','registration_pin':registration_pin,'chunk_index':index,
                'attempt_record':{'attempt':number,'state':state,'failure':copy.deepcopy(failure) if state == 'failed' else None,'evaluations':slots},
                'worker':{'exit_confirmed':True,'exit_code':1 if state == 'failed' else 0,'observation_errors':[]}}
            snapshots[bound.attempt_path(index,number)] = bound.v.canonical_json(record)
    state = 'not_started' if empty else 'failed' if failed_latest else 'complete'
    return pack(snapshots,chunks,state=state,failure=failure if state == 'failed' else None)


def reseal(case):
    # Model an attacker updating internal hashes, while the caller deliberately
    # accepts a new outer pin to test semantic checks beyond byte mismatches.
    snapshots = case['snapshots'];manifest = json.loads(case['manifest_raw']);close = json.loads(snapshots['producer/completion.json'])
    return pack(snapshots,manifest['chunks'],state=close['state'],worker=close['worker'],failure=close['failure'])


class ProducerInputFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.base = example()
    def fresh(self):return copy.deepcopy(self.base)
    def call(self,case=None):return bound.bind_producer_inputs(**(self.base if case is None else case))
    def edit(self,case,name,change):
        value = json.loads(case['snapshots'][name]);change(value);case['snapshots'][name] = bound.v.canonical_json(value)
    def record(self,case,chunk=0,attempt=1):return json.loads(case['snapshots'][bound.attempt_path(chunk,attempt)])
    def change_summary(self,case,change,chunk=0,slot=0):
        record = self.record(case,chunk);row = record['attempt_record']['evaluations'][slot];name = bound.summary_path(row['identity'],1)
        self.edit(case,name,change);row['evaluation_sha256'] = bound.pin(case['snapshots'][name])['sha256']
        case['snapshots'][bound.attempt_path(chunk,1)] = bound.v.canonical_json(record)
        return reseal(case)

    def test_complete_bytes_join_to_hand_totals_and_do_not_mutate_inputs(self):
        before = copy.deepcopy(self.base);value = self.call()
        self.assertEqual(self.base,before);self.assertEqual(value['status'],'fixture_inputs_bound')
        self.assertEqual((value['planned_chunks'],value['planned_evaluations'],value['attempt_count']),(12,72,12))
        cell = value['clusters'][0]['candidates'][bound.arithmetic.CANDIDATES[0]]['core']
        self.assertEqual(cell['counts']['machine_recall'],[36,120]);self.assertEqual(cell['counts']['sensor_recall'],[36,120])
        self.assertEqual(cell['counts']['precision'],[72,84]);self.assertEqual(cell['counts']['clean_rate'],[12,40380])
        self.assertEqual(cell['counts'][bound.arithmetic.AVAILABILITY[0]],[20466,21600])
        diagnostic = value['diagnostics'][0]['candidates'][bound.arithmetic.CANDIDATES[0]]['core']
        self.assertEqual(diagnostic['effective_clean_seconds'],39666);self.assertEqual(len(diagnostic['detected_delays']),72)
        adapter._diagnostics(value['clusters'],value['diagnostics'])
        for k,v in bound.CLOSED.items():self.assertEqual(value[k],v)

    def test_full_40_cluster_inventory_fits_existing_document_input_and_coverage(self):
        value = self.call(example(40));self.assertEqual((value['planned_chunks'],value['planned_evaluations']),(480,2880))
        source = {'format':document.FORMAT,'invented_only':True,'clusters':value['clusters'],'diagnostics':value['diagnostics'],
            'draws':[list(range(40))],'engineering_ready_assumption':False}
        with patch.object(adapter,'compute_fixture_packet',side_effect=AssertionError('inference')):
            document._input(source);adapter._diagnostics(source['clusters'],source['diagnostics'])
            coverage = wrapper._coverage(value['wrapper_coverage'],source)
        self.assertTrue(coverage['complete']);self.assertEqual(coverage['counts']['success'],2880)

    def test_pure_adapter_does_not_open_files_expand_real_registry_or_run_inference(self):
        with (patch('builtins.open',side_effect=AssertionError('IO')),patch.object(Path,'open',side_effect=AssertionError('IO')),
            patch.object(subprocess,'Popen',side_effect=AssertionError('process')),
            patch.object(bound.v,'evaluation_inventory',side_effect=AssertionError('registered inventory')),
            patch.object(bound.arithmetic,'compute_fixture_tables',side_effect=AssertionError('inference'))):self.assertTrue(self.call()['complete_for_aggregation'])

    def test_formal_mode_rejected_before_decoding_or_traversal(self):
        for mode in ('formal','holdout','engineering-dev-smoke',True):
            with self.subTest(mode=mode),patch.object(bound.v,'strict_json',side_effect=AssertionError('decode')),self.assertRaises(ValueError):
                bound.bind_producer_inputs(None,None,expected_mode=mode,expected_manifest_pin=None,expected_registration_pin=None)

    def test_external_manifest_and_registration_pins_are_not_inferred(self):
        for key in ('expected_manifest_pin','expected_registration_pin'):
            case = self.fresh();case[key]['sha256'] = 'f'*64
            with self.subTest(key=key),self.assertRaises(ValueError):self.call(case)

    def test_changed_summary_bytes_fail_outer_pin(self):
        case = self.fresh();row = self.record(case)['attempt_record']['evaluations'][0]
        case['snapshots'][bound.summary_path(row['identity'],1)] += b' '
        with self.assertRaisesRegex(ValueError,'payload pin'):self.call(case)

    def test_missing_extra_and_same_count_substituted_files_rejected(self):
        for change in ('missing','extra','substitute'):
            case = self.fresh();name = bound.summary_path(self.record(case)['attempt_record']['evaluations'][0]['identity'],1)
            if change != 'extra':raw = case['snapshots'].pop(name)
            if change != 'missing':case['snapshots']['summaries/unrelated.json'] = b'{}'
            with self.subTest(change=change),self.assertRaises(ValueError):self.call(case)
        case = self.fresh();case['snapshots']['extra.json'] = b'{}'
        with self.assertRaisesRegex(ValueError,'unreferenced'):self.call(reseal(case))

    def test_resealed_wrong_registration_seed_rejected(self):
        case = self.fresh();self.edit(case,'registration.json',lambda v:v['clusters'][0].update(seed=999))
        with self.assertRaises(ValueError):self.call(reseal(case))

    def test_chunk_missing_duplicate_or_reordered_rejected(self):
        for change in ('missing','duplicate','swap'):
            case = self.fresh();m = json.loads(case['manifest_raw'])
            if change == 'missing':m['chunks'].pop()
            elif change == 'duplicate':m['chunks'][1] = copy.deepcopy(m['chunks'][0])
            else:m['chunks'][0],m['chunks'][1] = m['chunks'][1],m['chunks'][0]
            case['manifest_raw'] = bound.v.canonical_json(m);case['expected_manifest_pin'] = bound.pin(case['manifest_raw'])
            with self.subTest(change=change),self.assertRaises(ValueError):self.call(case)

    def test_resealed_evaluation_identity_swap_rejected(self):
        case = self.fresh();record = self.record(case);rows = record['attempt_record']['evaluations'];rows[0],rows[1] = rows[1],rows[0]
        case['snapshots'][bound.attempt_path(0,1)] = bound.v.canonical_json(record)
        with self.assertRaisesRegex(ValueError,'identity'):self.call(reseal(case))

    def test_candidate_input_substitution_rejected_even_with_new_manifest(self):
        case = self.fresh();record = self.record(case);record['attempt_record']['evaluations'][1]['input_hashes']['events'] = 'f'*64
        case['snapshots'][bound.attempt_path(0,1)] = bound.v.canonical_json(record)
        with self.assertRaisesRegex(ValueError,'input pins differ'):self.call(reseal(case))

    def test_resealed_summary_from_other_slot_rejected(self):
        case = self.change_summary(self.fresh(),lambda v:v['identity'].update(layout=11))
        with self.assertRaisesRegex(ValueError,'summary binding identity'):self.call(case)

    def test_resealed_denominator_partition_and_delay_mutations_rejected(self):
        for change in (lambda v:v['counts']['machine_recall'].__setitem__(1,11),
                       lambda v:v['counts']['precision'].__setitem__(0,0),
                       lambda v:v['delay_histogram'].__setitem__(4,1),
                       lambda v:v.update(effective_clean_seconds=3366)):
            with self.subTest(change=change),self.assertRaises(ValueError):self.call(self.change_summary(self.fresh(),change))

    def test_false_integer_counts_rejected(self):
        case = self.change_summary(self.fresh(),lambda v:v['counts']['clean_rate'].__setitem__(0,True))
        with self.assertRaises(ValueError):self.call(case)

    def test_failed_history_retained_and_only_latest_attempt_aggregated(self):
        value = self.call(example(retry=True));self.assertTrue(value['complete_for_aggregation'])
        self.assertEqual(value['coverage']['success'],72);self.assertEqual(value['attempt_count'],13)
        self.assertEqual(len(value['failed_attempt_history']),1);self.assertFalse(value['failed_attempt_history'][0]['is_latest'])
        self.assertEqual(value['clusters'],self.call()['clusters'])

    def test_retry_after_integrity_failure_and_nonfailed_prior_rejected(self):
        for change in ('integrity','nonfailed'):
            case = example(retry=True);record = self.record(case)
            if change == 'integrity':record['attempt_record']['failure']['reason'] = 'hash_mismatch'
            else:record['attempt_record'].update(state='in_progress',failure=None);record['worker'] = {'exit_confirmed':False,'exit_code':None,'observation_errors':[]}
            case['snapshots'][bound.attempt_path(0,1)] = bound.v.canonical_json(record)
            with self.subTest(change=change),self.assertRaises(ValueError):self.call(reseal(case))

    def test_latest_failed_does_not_fall_back_or_emit_aggregates(self):
        value = self.call(example(retry=True,failed_latest=True))
        self.assertEqual(value['status'],'fixture_inputs_incomplete');self.assertIsNone(value['clusters']);self.assertIsNone(value['diagnostics'])
        self.assertTrue(value['failed_attempt_history'][-1]['is_latest']);self.assertFalse(value['all_profiles_calibrated'])

    def test_failure_reference_is_byte_bound_and_cannot_dangle(self):
        case = example(retry=True);record = self.record(case);failure = record['attempt_record']['failure']
        name = 'failures/chunk-0000-attempt-01.json'
        raw = bound.v.canonical_json({'format':'anomaly-v03-producer-input-fixture-failure-v1','mode':'fixture',
            'scope':name,'stage':failure['stage'],'reason':failure['reason'],'detail':'invented worker failure'})
        failure['evidence_sha256'] = bound.pin(raw)['sha256'];case['snapshots'][bound.attempt_path(0,1)] = bound.v.canonical_json(record)
        with self.assertRaisesRegex(ValueError,'missing referenced payload'):self.call(reseal(copy.deepcopy(case)))
        case['snapshots'][name] = raw;value = self.call(reseal(case));self.assertTrue(value['complete_for_aggregation'])
        self.assertEqual(value['failed_attempt_history'][0]['failure']['evidence_sha256'],bound.pin(raw)['sha256'])

    def test_not_started_keeps_all_planned_slots(self):
        value = self.call(example(empty=True));self.assertEqual(value['coverage']['not_started'],72)
        self.assertEqual(value['verified_payload_files'],2);self.assertIsNone(value['clusters']);self.assertEqual(len(value['latest_attempt_pins']),12)

    def test_inconclusive_and_zero_denominators_are_retained(self):
        value = self.call(example(inconclusive=True,zero_control=True));self.assertTrue(value['complete_for_aggregation']);self.assertFalse(value['all_profiles_calibrated'])
        self.assertEqual(value['coverage']['inconclusive'],1)
        cell = value['clusters'][0]['candidates'][bound.arithmetic.CANDIDATES[0]]['core']
        self.assertEqual(cell['profile_status'],'inconclusive');self.assertEqual(cell['counts']['precision'],[0,0])
        self.assertEqual(value['diagnostics'][0]['candidates'][bound.arithmetic.CANDIDATES[0]]['core']['detected_delays'],[])

    def test_complete_needs_clean_confirmed_exit_and_exact_latest_pins(self):
        for target,change in (('producer/completion.json',lambda v:v['worker'].update(exit_confirmed=False,exit_code=None)),
            ('producer/completion.json',lambda v:v['latest_attempt_pins'].__setitem__(0,None)),
            (bound.attempt_path(0,1),lambda v:v['worker'].update(observation_errors=['missing memory sample']))):
            case = self.fresh();self.edit(case,target,change)
            # Retain the deliberately changed completion instead of rebuilding it.
            m = json.loads(case['manifest_raw']);m['payload_pins'] = {n:bound.pin(b) for n,b in case['snapshots'].items()}
            case['manifest_raw'] = bound.v.canonical_json(m);case['expected_manifest_pin'] = bound.pin(case['manifest_raw'])
            with self.subTest(target=target),self.assertRaises(ValueError):self.call(case)

    def test_finished_slots_do_not_override_failed_producer_completion(self):
        case = self.fresh();m = json.loads(case['manifest_raw']);case = pack(case['snapshots'],m['chunks'],state='failed',
            failure={'stage':'verification','reason':'verification_failed','evidence_sha256':None})
        value = self.call(case);self.assertEqual(value['coverage']['success'],72);self.assertIsNone(value['clusters'])

    def test_parser_bounds_and_unsafe_paths_rejected(self):
        for change in ('attempts','file','path'):
            case = self.fresh();m = json.loads(case['manifest_raw'])
            if change == 'attempts':m['chunks'][0]['attempt_count'] = bound.MAX_ATTEMPTS+1
            elif change == 'file':case['snapshots']['registration.json'] = b' '*(bound.MAX_FILE+1);m['payload_pins']['registration.json'] = bound.pin(case['snapshots']['registration.json'])
            else:m['payload_pins']['../escape'] = bound.pin(b'{}');case['snapshots']['../escape'] = b'{}'
            case['manifest_raw'] = bound.v.canonical_json(m);case['expected_manifest_pin'] = bound.pin(case['manifest_raw'])
            with self.subTest(change=change),self.assertRaises(ValueError):self.call(case)
