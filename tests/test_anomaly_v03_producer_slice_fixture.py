"""Receipt joins and per-evaluation diagnostic partitions, with invented data."""
import copy
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
from banto_ai import anomaly_v03_producer_slice_fixture as bound
from tests import test_anomaly_v03_producer_input_fixture as main

P = bound.primary
S = bound.S


def spread(total,capacities):
    values=[]
    for cap in capacities:
        n=min(total,cap);values.append(n);total-=n
    assert total == 0
    return values


def take(hist,n):
    values=spread(n,hist)
    for i,v in enumerate(values):hist[i]-=v
    return values


def scores(cells,plans,available,threshold,onsets):
    av=spread(available,plans);th=spread(threshold,av);ons=spread(onsets,th)
    for cell,p,a,t,o in zip(cells,plans,av,th,ons):
        cell.update(planned=p,observed=p,available=a,threshold_exceeded=t,signal_onsets=o)


def raw_counts(summary):
    raw=S.empty_counts();raw['evaluations']=1
    raw['profile_inconclusive_evaluations']=int(summary['profile_status']=='inconclusive')
    raw['delay_histogram']=summary['delay_histogram'].copy();counts=summary['counts']
    remaining=raw['delay_histogram'].copy();joint=raw['incident_slices']['class-equipment-mode']
    for kind in ('machine','sensor'):
        cells=[v for k,v in joint.items() if k.startswith(kind+'.')]
        plans=[1]*10+[0]*2
        for cell,p,n in zip(cells,plans,spread(counts[kind+'_recall'][0],plans)):
            cell.update(planned=p,detected=n,delay_histogram=take(remaining,n))
    for dimension,part in (('class',0),('equipment',1),('mode',2)):
        for key,cell in raw['incident_slices'][dimension].items():
            for name,source in joint.items():
                if name.split('.')[part]==key:S.add_counts(cell,source)
    for dimension,planned in (('test-cycle',2),('event-start-phase',5)):
        remaining=raw['delay_histogram'].copy()
        for cell in raw['incident_slices'][dimension].values():
            n=min(sum(remaining),planned);cell.update(planned=planned,detected=n,delay_histogram=take(remaining,n))
    score=raw['score_slices'];available=0
    for target,cell in score['full-target'].items():
        n,d=counts['availability:'+target];available+=n
        cell.update(planned=d,observed=d,available=n,threshold_exceeded=10,signal_onsets=2)
        scores([score['signal-mode'][target+'.'+m] for m in S.MODES],[300]*6,n,10,2)
    plans={'phase':[480*n for n in (1,1,1,1,3,7,7,9)],'context':[800,140,13460],
        'quality-current':[available,14400-available,0,0,0],'quality-previous':[available,0,14400-available,0,0],
        'fault-quality-overlap':[14200,200],
        'profile-status':[14399,1] if raw['profile_inconclusive_evaluations'] else [14400,0]}
    for dimension,plan in plans.items():scores(list(score[dimension].values()),plan,available,80,16)
    for key,cell in score['event-offset'].items():
        outside=2 if key=='minus-2' else 1 if key=='minus-1' else 0;observed=30-outside
        cell.update(planned=40,unscored_target=10,outside_test=outside,observed=observed,
            available=observed//2,threshold_exceeded=observed//4,signal_onsets=observed//8)
    detected=sum(raw['delay_histogram']);false=counts['false_alert_burden'][0];clean=counts['clean_rate'][0]
    raw['equipment_context']['raw-event'].update(planned_seconds=200,episodes=detected+false-clean,unmatched=false-clean)
    raw['equipment_context']['grace'].update(planned_seconds=35)
    raw['equipment_context']['clean'].update(planned_seconds=3365,episodes=clean,unmatched=clean)
    return raw


def compact(raw):
    return {'incident':[[c['planned'],c['detected'],*c['delay_histogram']]
            for d,k in bound.INCIDENT for c in [raw['incident_slices'][d][k]]],
        'score':[[raw['score_slices'][d][k][f] for f in bound.connection.inputs.SC] for d,k in bound.SCORE],
        'context':[[raw['equipment_context'][k][f] for f in bound.ENCODING['context_fields']] for k in bound.CONTEXT],
        **{k:copy.deepcopy(raw[k]) for k in ('evaluations','profile_inconclusive_evaluations','delay_histogram')}}


def pack(primary_input,snapshots):
    manifest={'format':bound.FORMAT,'mode':'fixture','invented_only':True,
        'primary_manifest_pin':primary_input['expected_manifest_pin'],'registration_pin':primary_input['expected_registration_pin'],
        'encoding':copy.deepcopy(bound.ENCODING),'payload_pins':{n:P.pin(b) for n,b in snapshots.items()}}
    raw=P.v.canonical_json(manifest)
    return {'primary_input':primary_input,'manifest_raw':raw,'snapshots':snapshots,
        'expected_mode':'fixture','expected_manifest_pin':P.pin(raw)}


def example(primary_input=None):
    primary_input=main.example() if primary_input is None else primary_input
    m=json.loads(primary_input['manifest_raw']);snapshots={}
    for chunk in m['chunks']:
        for number in range(1,chunk['attempt_count']+1):
            path=P.attempt_path(chunk['chunk_index'],number);record=json.loads(primary_input['snapshots'][path])
            for slot in record['attempt_record']['evaluations']:
                if slot['evaluation_sha256'] is None:continue
                identity=slot['identity'];summary_path=P.summary_path(identity,number)
                summary=json.loads(primary_input['snapshots'][summary_path])
                row={'format':bound.ROW_FORMAT,'mode':'fixture','invented_only':True,
                    'primary_manifest_pin':primary_input['expected_manifest_pin'],'registration_pin':primary_input['expected_registration_pin'],
                    'attempt_receipt_pin':m['payload_pins'][path],'summary_pin':m['payload_pins'][summary_path],
                    'identity':copy.deepcopy(identity),'attempt':number,'input_hashes':copy.deepcopy(slot['input_hashes']),
                    'cells':compact(raw_counts(summary))}
                snapshots[bound.slice_path(identity,number)]=P.v.canonical_json(row)
    return pack(primary_input,snapshots)


def historical_case():
    case=main.example(retry=True);snapshots=case['snapshots']
    old=json.loads(snapshots[P.attempt_path(0,1)]);latest=json.loads(snapshots[P.attempt_path(0,2)])
    slot=copy.deepcopy(latest['attempt_record']['evaluations'][0]);summary=json.loads(snapshots[P.summary_path(slot['identity'],2)])
    summary['attempt']=1;name=P.summary_path(slot['identity'],1);snapshots[name]=P.v.canonical_json(summary)
    slot['evaluation_sha256']=P.pin(snapshots[name])['sha256'];old['attempt_record']['evaluations'][0]=slot
    snapshots[P.attempt_path(0,1)]=P.v.canonical_json(old)
    return example(main.reseal(case))


class ProducerSliceFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.base=example()
    def call(self,case=None):return bound.bind_producer_slices(**(self.base if case is None else case))
    def edit(self,case,fn,name=None):
        name=next(iter(case['snapshots'])) if name is None else name
        row=json.loads(case['snapshots'][name]);fn(row);case['snapshots'][name]=P.v.canonical_json(row)
        return pack(case['primary_input'],case['snapshots'])
    def mutate_raw(self,case,fn):
        def change(row):
            raw=bound._decode(row['cells']);fn(raw);row['cells']=compact(raw)
        return self.edit(case,change)

    def test_latest_slice_totals_and_input_immutability(self):
        before=copy.deepcopy(self.base);value=self.call();self.assertEqual(self.base,before)
        self.assertEqual(value['verified_slice_files'],72);self.assertTrue(value['complete_for_aggregation'])
        raw=value['slice_source']['clusters'][0]['candidates'][P.arithmetic.CANDIDATES[0]]['core']
        self.assertEqual(raw['evaluations'],12);self.assertEqual(raw['incident_slices']['class']['machine']['detected'],36)
        self.assertEqual(raw['equipment_context']['clean']['unmatched'],12)
        self.assertEqual(sum(raw['delay_histogram']),72)
        for k,v in P.CLOSED.items():self.assertEqual(value[k],v)

    def test_full_inventory_preserves_inconclusive_zero_cells_and_omissions(self):
        value=self.call(example(main.example(40,inconclusive=True,zero_control=True,retry=True)))
        self.assertEqual(value['verified_slice_files'],2880);self.assertEqual(len(value['latest_slice_pins']),2880)
        self.assertEqual(len(value['slice_source']['clusters']),40)
        raw=value['slice_source']['clusters'][0]['candidates'][P.arithmetic.CANDIDATES[0]]['core']
        self.assertEqual(raw['profile_inconclusive_evaluations'],1)
        self.assertEqual(raw['delay_histogram'],[0]*5)
        self.assertEqual(raw['score_slices']['event-offset']['minus-2']['outside_test'],24)
        self.assertEqual(raw['score_slices']['event-offset']['minus-2']['unscored_target'],120)
        for cluster in value['slice_source']['clusters']:
            for layers in cluster['candidates'].values():
                for cell in layers.values():bound.connection.inputs._slice_counts(S.describe(cell),12);bound.connection._marginals(cell)

    def test_old_successful_slot_with_failed_attempt_is_checked_but_not_added(self):
        case=historical_case();value=self.call(case)
        self.assertEqual(value['historical_summary_count'],1);self.assertEqual(value['verified_slice_files'],73)
        self.assertEqual(value['slice_source'],self.call()['slice_source'])
        old=next(n for n in case['snapshots'] if n.endswith('attempt-01.json'))
        case=self.edit(case,lambda r:r.update(attempt=2),old)
        with self.assertRaisesRegex(ValueError,'binding attempt'):self.call(case)

    def test_failed_latest_retains_coverage_without_aggregates(self):
        value=self.call(example(main.example(failed_latest=True)))
        self.assertFalse(value['complete_for_aggregation']);self.assertIsNone(value['slice_source'])
        self.assertIsNone(value['primary']['clusters']);self.assertEqual(value['primary']['coverage']['success'],72)
        self.assertEqual(len(value['primary']['failed_attempt_history']),1)

    def test_not_started_has_full_coverage_and_no_sidecars(self):
        value=self.call(example(main.example(empty=True)))
        self.assertEqual(value['primary']['coverage']['not_started'],72);self.assertEqual(value['verified_slice_files'],0)
        self.assertIsNone(value['slice_source'])

    def test_mode_rejection_precedes_any_decoding(self):
        for mode in ('formal','holdout','engineering-dev-smoke',True):
            with patch.object(P.v,'strict_json',side_effect=AssertionError('decoded')),self.assertRaises(ValueError):
                bound.bind_producer_slices(None,None,None,expected_mode=mode,expected_manifest_pin=None)

    def test_no_files_process_registry_or_inference(self):
        with (patch('builtins.open',side_effect=AssertionError('IO')),patch.object(Path,'open',side_effect=AssertionError('IO')),
            patch.object(subprocess,'Popen',side_effect=AssertionError('process')),
            patch.object(P.v,'evaluation_inventory',side_effect=AssertionError('registry')),
            patch.object(P.arithmetic,'compute_fixture_tables',side_effect=AssertionError('inference'))):self.call()

    def test_external_manifest_pin_and_raw_payload_tamper_rejected(self):
        case=copy.deepcopy(self.base);case['expected_manifest_pin']['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'external slice manifest pin'):self.call(case)
        case=copy.deepcopy(self.base);case['snapshots'][next(iter(case['snapshots']))]+=b' '
        with self.assertRaisesRegex(ValueError,'slice payload pin'):self.call(case)

    def test_missing_extra_and_same_count_substitution_rejected(self):
        for mode in ('missing','extra','substitute'):
            case=copy.deepcopy(self.base)
            if mode!='extra':case['snapshots'].pop(next(iter(case['snapshots'])))
            if mode!='missing':case['snapshots']['slices/unrelated.json']=b'{}'
            with self.subTest(mode=mode),self.assertRaises(ValueError):self.call(pack(case['primary_input'],case['snapshots']))

    def test_primary_and_registration_pins_are_bound(self):
        for key in ('primary_manifest_pin','registration_pin'):
            case=copy.deepcopy(self.base);m=json.loads(case['manifest_raw']);m[key]['sha256']='f'*64
            case['manifest_raw']=P.v.canonical_json(m);case['expected_manifest_pin']=P.pin(case['manifest_raw'])
            with self.subTest(key=key),self.assertRaises(ValueError):self.call(case)

    def test_row_receipt_summary_identity_attempt_and_input_bindings(self):
        for key in ('primary_manifest_pin','registration_pin','attempt_receipt_pin','summary_pin','identity','attempt','input_hashes'):
            case=copy.deepcopy(self.base)
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'slice row binding'):
                self.call(self.edit(case,lambda r:r.update({key:None})))

    def test_compact_encoding_is_fixed_not_inferred_from_counts(self):
        case=copy.deepcopy(self.base);m=json.loads(case['manifest_raw']);m['encoding']['score_fields'].reverse()
        case['manifest_raw']=P.v.canonical_json(m);case['expected_manifest_pin']=P.pin(case['manifest_raw'])
        with self.assertRaisesRegex(ValueError,'encoding'):self.call(case)

    def test_boolean_negative_huge_wrong_shape_and_unknown_cells_rejected(self):
        for value in (True,-1,14401,1.5):
            case=copy.deepcopy(self.base)
            with self.subTest(value=value),self.assertRaises(ValueError):
                self.call(self.edit(case,lambda r:r['cells']['score'][0].__setitem__(0,value)))
        for change in (lambda c:c['incident'].pop(),lambda c:c['score'][0].append(0),lambda c:c.update(extra=0)):
            with self.assertRaises(ValueError):self.call(self.edit(copy.deepcopy(self.base),lambda r:change(r['cells'])))

    def test_joint_to_marginal_reassignment_with_same_total_rejected(self):
        def change(raw):
            cells=raw['incident_slices']['class-equipment-mode'];names=list(cells)
            cells[names[0]],cells[names[6]]=cells[names[6]],cells[names[0]]
        # First machine joint cells have different detection counts.
        with self.assertRaisesRegex(ValueError,'joint/marginal'):
            self.call(self.mutate_raw(copy.deepcopy(self.base),change))

    def test_target_mode_reassignment_with_same_total_rejected(self):
        def change(raw):
            cells=raw['score_slices']['signal-mode'];a=S.TARGETS[0]+'.'+S.MODES[0];b=S.TARGETS[1]+'.'+S.MODES[-1]
            cells[a],cells[b]=cells[b],cells[a]
        with self.assertRaisesRegex(ValueError,'target/mode'):
            self.call(self.mutate_raw(copy.deepcopy(self.base),change))

    def test_internally_consistent_wrong_primary_counts_rejected(self):
        def change(row):
            raw=bound._decode(row['cells']);identity=row['identity']
            summary=json.loads(self.base['primary_input']['snapshots'][P.summary_path(identity,1)])
            summary['counts']['machine_recall'][0]+=1;summary['counts']['precision'][0]+=1;summary['counts']['precision'][1]+=1
            summary['delay_histogram'][0]+=1;row['cells']=compact(raw_counts(summary))
        with self.assertRaisesRegex(ValueError,'slice/recall'):
            self.call(self.edit(copy.deepcopy(self.base),change))

    def test_same_total_different_delay_distribution_rejected(self):
        def change(row):
            summary=json.loads(self.base['primary_input']['snapshots'][P.summary_path(row['identity'],1)])
            summary['delay_histogram'][1]=summary['delay_histogram'][0];summary['delay_histogram'][0]=0
            row['cells']=compact(raw_counts(summary))
        with self.assertRaisesRegex(ValueError,'slice/summary delay'):
            self.call(self.edit(copy.deepcopy(self.base),change))

    def test_profile_outcome_and_profile_score_cells_rejected(self):
        with self.assertRaisesRegex(ValueError,'slice/summary profile'):
            self.call(self.edit(copy.deepcopy(self.base),lambda r:r['cells'].update(profile_inconclusive_evaluations=1)))
        def change(raw):
            cells=raw['score_slices']['profile-status'];cells['calibrated'],cells['inconclusive']=cells['inconclusive'],cells['calibrated']
        with self.assertRaisesRegex(ValueError,'calibrated evaluation'):
            self.call(self.mutate_raw(copy.deepcopy(self.base),change))

    def test_omission_accounting_and_score_subsets_rejected(self):
        for change in (lambda r:r['score_slices']['event-offset']['minus-2'].update(unscored_target=9),
            lambda r:r['score_slices']['quality-current']['missing'].update(available=1,threshold_exceeded=2)):
            with self.assertRaises(ValueError):self.call(self.mutate_raw(copy.deepcopy(self.base),change))

    def test_primary_bytes_and_failed_close_are_not_bypassed(self):
        case=copy.deepcopy(self.base);case['primary_input']['snapshots']['registration.json']+=b' '
        with self.assertRaises(ValueError):self.call(case)
        p=main.example();close=json.loads(p['snapshots']['producer/completion.json'])
        close.update(state='failed',worker={'exit_confirmed':True,'exit_code':1,'observation_errors':[]},
            failure={'stage':'supervision','reason':'worker_exit','evidence_sha256':None})
        p['snapshots']['producer/completion.json']=P.v.canonical_json(close)
        self.assertIsNone(self.call(example(main.reseal(p)))['slice_source'])

    def test_byte_limits_and_unsafe_path_rejected(self):
        for constant in ('MAX_FILE','MAX_MANIFEST','MAX_FILES'):
            with patch.object(bound,constant,1),self.assertRaises(ValueError):self.call()
        own=len(self.base['manifest_raw'])+sum(map(len,self.base['snapshots'].values()))
        with patch.object(bound,'MAX_TOTAL',own),self.assertRaisesRegex(ValueError,'combined'):self.call()
        case=copy.deepcopy(self.base);case['snapshots']['../escape.json']=b'{}'
        with self.assertRaises(ValueError):self.call(pack(case['primary_input'],case['snapshots']))


if __name__=='__main__':unittest.main()
