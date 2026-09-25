"""Invented compact partitions, without observations or detector execution."""
import copy
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_slice_fixture as connection
from tests import test_anomaly_v03_document_fixture as hand

S = connection.slices
SCHEMA = hand.SCHEMA


def _take_hist(hist, count):
    result = [0]*5
    for i in range(5):
        result[i] = min(hist[i], count)
        hist[i] -= result[i]; count -= result[i]
    assert count == 0
    return result


def _spread(total, capacities):
    result = []
    for cap in capacities:
        amount = min(total, cap); result.append(amount); total -= amount
    assert total == 0
    return result


def _scores(cells, plans, available, threshold, onsets):
    av = _spread(available, plans)
    th = _spread(threshold, av)
    ons = _spread(onsets, th)
    for cell, p, a, t, o in zip(cells.values(), plans, av, th, ons):
        cell.update(planned=p, observed=p, available=a, threshold_exceeded=t, signal_onsets=o)


def raw_cell(primary, diagnostic):
    raw = S.empty_counts(); raw['evaluations'] = 12
    counts = primary['counts']
    raw['profile_inconclusive_evaluations'] = 12 if primary['profile_status']=='inconclusive' else 0
    for delay in diagnostic['detected_delays']:
        raw['delay_histogram'][delay-1] += 1
    remaining = raw['delay_histogram'].copy()
    joint = raw['incident_slices']['class-equipment-mode']
    for kind in ('machine', 'sensor'):
        detected = counts[kind+'_recall'][0]
        values = [v for k, v in joint.items() if k.startswith(kind+'.')]
        for i, cell in enumerate(values):
            n = detected//12 + int(i < detected % 12)
            cell.update(planned=10, detected=n, delay_histogram=_take_hist(remaining,n))
    for dimension, part in (('class',0),('equipment',1),('mode',2)):
        for key, cell in raw['incident_slices'][dimension].items():
            for name, source in joint.items():
                if name.split('.')[part] == key:
                    S.add_counts(cell,source)
    for dimension, planned in (('test-cycle',24),('event-start-phase',60)):
        remaining = raw['delay_histogram'].copy()
        for cell in raw['incident_slices'][dimension].values():
            n = min(sum(remaining),planned)
            cell.update(planned=planned,detected=n,delay_histogram=_take_hist(remaining,n))
    score = raw['score_slices']
    for target, cell in score['full-target'].items():
        n,d=counts['availability:'+target]
        cell.update(planned=d,observed=d,available=n,threshold_exceeded=120,signal_onsets=30)
        group={mode:score['signal-mode'][target+'.'+mode] for mode in S.MODES}
        _scores(group,[3600]*6,n,120,30)
    available = sum(c['available'] for c in score['full-target'].values())
    threshold,onsets=960,240
    plans={
        'phase':[5760*n for n in (1,1,1,1,3,7,7,9)],
        'context':[9600,1680,161520],
        'quality-current':[available,172800-available,0,0,0],
        'quality-previous':[available,0,172800-available,0,0],
        'fault-quality-overlap':[170400,2400],
        'profile-status':[172800,0] if primary['profile_status']=='calibrated' else [0,172800],
    }
    for dimension,plan in plans.items():
        _scores(score[dimension],plan,available,threshold,onsets)
    for key,cell in score['event-offset'].items():
        outside=24 if key=='minus-2' else (12 if key=='minus-1' else 0)
        observed=360-outside
        cell.update(planned=480,unscored_target=120,outside_test=outside,observed=observed,
                    available=observed//2,threshold_exceeded=observed//4,signal_onsets=observed//8)
    ctx=raw['equipment_context']
    detected=sum(raw['delay_histogram']);false=counts['false_alert_burden'][0];clean=counts['clean_rate'][0]
    ctx['raw-event'].update(planned_seconds=2400,episodes=detected+false-clean,unmatched=false-clean)
    ctx['grace'].update(planned_seconds=420)
    ctx['clean'].update(planned_seconds=40380,episodes=clean,unmatched=clean)
    return raw


def invented_slices(fixture_input):
    clusters=[]
    for cluster,detail in zip(fixture_input['clusters'],fixture_input['diagnostics']):
        clusters.append({'cluster_id':cluster['cluster_id'],'candidates':{
            c:{s:raw_cell(cluster['candidates'][c][s],detail['candidates'][c][s])
               for s in connection.I.STRATA[:2]} for c in connection.I.CANDIDATES}})
    return {'format':connection.INPUT_FORMAT,'invented_only':True,'clusters':clusters}


def pick(rows, candidate='c1-phase-level', layer='core', dimension='class', key='machine'):
    return next(r for r in rows if (r['candidate_id'],r['stratum'],r['dimension'],r['key'])
                == (candidate,layer,dimension,key))


class SliceFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.input=hand.invented_input()
        cls.base=connection.document.build_fixture_document(cls.input,SCHEMA)
        cls.source=invented_slices(cls.input)
        cls.result=connection.attach_fixture_slices(cls.base,cls.input,cls.source,SCHEMA)

    def test_inventory_and_hand_count_mapping(self):
        value=self.result;main=value['document_draft']['slices']
        self.assertEqual(len(main),1233)
        self.assertEqual(sum(map(len,value['diagnostic_series'].values())),2835)
        row=pick(main)
        self.assertEqual((row['planned_count'],row['actual_count']),(4800,4600))
        self.assertEqual(row['metric']['value'],4600/4800)
        self.assertEqual(row['delay_summary']['count'],4600)
        target=pick(main,dimension='full-target',key=S.TARGETS[0])
        self.assertEqual((target['metric']['numerator'],target['metric']['denominator']),(838080,864000))
        self.assertEqual(target['metric']['ci_status'],'not_evaluated')
        self.assertIsNone(target['delay_summary'])

    def test_overall_pools_counts_histograms_and_not_medians(self):
        main=self.result['document_draft']['slices']
        overall=pick(main,layer='overall',key='sensor')
        core=pick(main,key='sensor');stress=pick(main,layer='quality-stress',key='sensor')
        self.assertEqual((overall['actual_count'],overall['planned_count']),(8880,9600))
        self.assertEqual(overall['delay_summary']['count'],8880)
        self.assertAlmostEqual(overall['delay_summary']['mean'],
            (core['delay_summary']['mean']*4560+stress['delay_summary']['mean']*4320)/8880)
        details=self.result['diagnostic_details'][5]
        self.assertEqual(sum(details['delay_histogram']),18080)
        self.assertEqual(details['delay_summary']['mean'],54320/18080)

    def test_event_offsets_retain_omissions_and_observed_denominator(self):
        row=pick(self.result['document_draft']['slices'],dimension='event-offset',key='minus-2')
        self.assertEqual(row['planned_count'],19200)
        self.assertEqual((row['metric']['numerator'],row['metric']['denominator']),(6720,13440))
        self.assertEqual(row['metric']['value'],.5)
        detail=self.result['diagnostic_details'][3]
        cell=next(c for c in detail['score_slices'] if (c['dimension'],c['key'])==('event-offset','minus-2'))
        self.assertEqual((cell['unscored_target'],cell['outside_test']),(4800,960))

    def test_named_series_do_not_confuse_availability_threshold_and_onset(self):
        series=self.result['diagnostic_series']
        values=[pick(series[k],dimension='full-target',key=S.TARGETS[0])['actual_count']
                for k in ('score-availability','score-threshold-exceedance','score-signal-onset')]
        self.assertEqual(values,[838080,4800,1200])
        main=self.result['document_draft']['slices']
        self.assertEqual(len({(r['candidate_id'],r['stratum'],r['dimension'],r['key']) for r in main}),1233)
        zero=pick(main,dimension='quality-current',key='invalid')
        self.assertEqual(zero['metric']['denominator'],0)
        self.assertIsNone(zero['metric']['value'])
        self.assertEqual(zero['metric']['ci_status'],'not_applicable')

    def test_input_immutable_no_alias_and_no_ci_recomputation(self):
        before=connection.document.contract.canonical_sha256([self.base,self.input,self.source])
        with patch.object(connection.I,'compute_fixture_tables',side_effect=AssertionError('CI recomputed')):
            result=connection.attach_fixture_slices(self.base,self.input,self.source,SCHEMA)
            checked=connection.validate_connected_document(result,self.input,self.source,SCHEMA)
        self.assertFalse(checked['inference_recomputed'])
        result['document_draft']['slices'][0]['metric']['value']=0
        self.assertNotEqual(result['diagnostic_series']['incident-recall'][0]['metric']['value'],0)
        self.assertEqual(connection.document.contract.canonical_sha256([self.base,self.input,self.source]),before)

    def test_identity_shape_and_real_scope_rejected(self):
        for mutate in (lambda v:v.update(role='holdout'),lambda v:v.update(invented_only=False),
                       lambda v:v['clusters'].pop(),lambda v:v['clusters'].reverse(),
                       lambda v:v['clusters'][0]['candidates'].pop('c1-phase-level')):
            value=copy.deepcopy(self.source);mutate(value)
            with self.subTest(mutation=mutate):
                with self.assertRaises(ValueError):connection.attach_fixture_slices(self.base,self.input,value,SCHEMA)
        changed=copy.deepcopy(self.input);changed['engineering_ready_assumption']=False
        with self.assertRaisesRegex(ValueError,'input binding'):
            connection.attach_fixture_slices(self.base,changed,self.source,SCHEMA)

    def test_invalid_count_fields_and_histograms_rejected(self):
        for mutate in (lambda v:v.update(evaluations=11),lambda v:v.update(extra=0),
                       lambda v:v['incident_slices']['class']['machine'].update(detected=True),
                       lambda v:v['score_slices']['quality-current'].pop('absent'),
                       lambda v:v['score_slices']['event-offset']['minus-2'].update(outside_test=0),
                       lambda v:v['delay_histogram'].__setitem__(0,-1)):
            source=copy.deepcopy(self.source)
            mutate(source['clusters'][0]['candidates']['c1-phase-level']['core'])
            with self.subTest(mutation=mutate):
                with self.assertRaises(ValueError):connection.attach_fixture_slices(self.base,self.input,source,SCHEMA)

    def test_cluster_swap_rejected_even_if_aggregate_histogram_unchanged(self):
        source=copy.deepcopy(self.source)
        a,b=(source['clusters'][i]['candidates']['c1-phase-level'] for i in (0,1))
        a['core'],b['core']=b['core'],a['core']
        with self.assertRaisesRegex(ValueError,'per-cluster delay'):
            connection.attach_fixture_slices(self.base,self.input,source,SCHEMA)

    def test_joint_reassignment_rejected_with_unchanged_partition_totals(self):
        source=copy.deepcopy(self.source)
        joint=source['clusters'][0]['candidates']['c1-phase-level']['quality-stress']['incident_slices']['class-equipment-mode']
        a='machine.motor-01.stopped';b='sensor.conveyor-01.nominal'
        joint[a],joint[b]=joint[b],joint[a]
        with self.assertRaisesRegex(ValueError,'joint/marginal'):
            connection.attach_fixture_slices(self.base,self.input,source,SCHEMA)

    def test_target_mode_reassignment_rejected_without_total_change(self):
        source=copy.deepcopy(self.source)
        modes=source['clusters'][0]['candidates']['c1-phase-level']['core']['score_slices']['signal-mode']
        # Use last mode: unlike the first mode it is not already fully available.
        modes[S.TARGETS[0]+'.cooldown']['available']+=1
        modes[S.TARGETS[1]+'.cooldown']['available']-=1
        with self.assertRaisesRegex(ValueError,'target/mode'):
            connection.attach_fixture_slices(self.base,self.input,source,SCHEMA)

    def test_output_tampering_rejected(self):
        mutations=(lambda v:v.update(formal_permission=True),
            lambda v:v['document_draft']['slices'].pop(),
            lambda v:v['diagnostic_series']['score-signal-onset'][0].update(actual_count=999),
            lambda v:v['diagnostic_details'][0]['score_slices'][0].update(available=0),
            lambda v:v['formal_requirements']['missing_fields'].pop(),
            lambda v:v.update(slice_input_canonical_sha256='0'*64))
        for mutate in mutations:
            value=copy.deepcopy(self.result);mutate(value)
            with self.subTest(mutation=mutate):
                with self.assertRaises(ValueError):connection.validate_connected_document(value,self.input,self.source,SCHEMA)

    def test_four_formal_fields_stay_missing_and_full_contract_rejects(self):
        value=self.result
        self.assertEqual(value['formal_requirements']['missing_fields'],['status','provenance','analysis_consumer','bootstrap'])
        for k in connection.PENDING:self.assertIsNone(value['document_draft'][k])
        self.assertIsNone(value['selected_candidate']);self.assertFalse(value['result_trusted'])
        self.assertIsNone(self.base['document_draft']['slices'])
        for candidate in (value,value['document_draft']):
            with self.assertRaises(ValueError):connection.document.contract.validate_result_contract(candidate)

    def test_zero_detections_keep_null_delay_and_positive_denominator(self):
        primary=hand.invented_input(zero_control=True)
        base=connection.document.build_fixture_document(primary,SCHEMA)
        result=connection.attach_fixture_slices(base,primary,invented_slices(primary),SCHEMA)
        row=pick(result['document_draft']['slices'],candidate='c0-diff-control')
        self.assertEqual((row['actual_count'],row['planned_count']),(0,4800))
        self.assertEqual(row['metric']['value'],0)
        self.assertEqual(row['delay_summary']['count'],0)
        self.assertIsNone(row['delay_summary']['mean'])


if __name__=='__main__':unittest.main()
