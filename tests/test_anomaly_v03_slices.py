"""Invented score decisions on fixed metadata, never a detector execution."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from banto_ai import anomaly_v03_slices as audit
from banto_ai import anomaly_v03_slice_io as io


def hand_evaluation(stratum='core'):
    identity=next(i for i in audit.registry.evaluation_inventory('dev') if i['stratum']==stratum)
    events=audit.registry.event_inventory(identity)
    profiles=[{'profile_id':f'{t}.{m}','full_target':t,'mode':m,'status':'calibrated'} for t in audit.TARGETS for m in audit.MODES]
    rows=[]
    for sample in range(7200,9000):
        for target in audit.TARGETS:
            mode=audit.MODES[(sample%180)//30]
            rows.append({'dataset_id':identity['dataset_id'],'candidate_id':identity['candidate_id'],
                'score_id':f"{identity['evaluation_id']}-score-{target.replace('.', '-')}-{sample:04d}",
                'sample':sample,'timestamp_ms':audit.ledger.START_MS+1000*sample,'full_target':target,'equipment':target.split('.')[0],
                'mode':mode,'phase':sample%30,'profile_id':target+'.'+mode,'available':sample%30!=0,
                'threshold_exceeded':False,'source_episode_id':None,'streak':0,
                'dependencies':[{'full_target':target,'sample':s,'quality':'ok'} for s in (sample-1,sample)]})
    incidents=[{'event_id':e['event_id'],'dataset_id':identity['dataset_id'],'status':'processed','causal_detected':False,
                'delay_seconds':None,'support_score_ids':[]} for e in events if e['event_class'] in ('machine','sensor')]
    result={'identity':identity,'events':events,'profiles':profiles,'scores':rows,'source_episodes':[],
            'equipment_episodes':[],'incidents':incidents,'status':{'run_status':'complete'}}
    metrics={'machine_recall':{'numerator':0},'sensor_recall':{'numerator':0},'precision':{'numerator':0,'denominator':0},
        'false_alert_burden':{'numerator':0},'clean_rate':{'numerator':0},
        'availability':[{'full_target':t,'metric':{'numerator':1740}} for t in audit.TARGETS],
        'delay_summary':audit.delay_summary([0]*5)}
    prior={'identity':identity,'evaluation_outcome':'success','profile_and_score_audit':{'score_derivation_verified':True},
           'ledger_audit':{'status':'ledger_checks_passed','metrics':metrics}}
    return result,prior


def detect_one(result,prior):
    event=next(e for e in result['events'] if e['event_class']=='sensor')
    start=event['start_sample']
    selected=[next(r for r in result['scores'] if r['full_target']==event['full_target'] and r['sample']==sample) for sample in (start,start+1)]
    sid='source-example';gid='equipment-example'
    for i,row in enumerate(selected):row.update(threshold_exceeded=True,streak=i+1,source_episode_id=None if not i else sid)
    source={'episode_id':sid,'full_target':event['full_target'],'onset_ms':event['start_ms']+1000}
    group={'episode_id':gid,'equipment':event['equipment'],'source_episode_ids':[sid],
           'onset_ms':source['onset_ms'],'matched_event_id':event['event_id']}
    result['source_episodes']=[source];result['equipment_episodes']=[group]
    item=next(i for i in result['incidents'] if i['event_id']==event['event_id'])
    item.update(causal_detected=True,delay_seconds=1.,matched_episode_id=gid,selected_source_episode_id=sid,
                support_score_ids=[s['score_id'] for s in selected])
    metrics=prior['ledger_audit']['metrics'];metrics['sensor_recall']['numerator']=1
    metrics['precision']={'numerator':1,'denominator':1};metrics['delay_summary']=audit.delay_summary([1,0,0,0,0])


class SliceTests(unittest.TestCase):
    def test_full_coverage_zero_cells_partitions_and_offsets(self):
        result,prior=hand_evaluation();r=audit.summarize_evaluation(result,prior);c=r['counts']
        self.assertEqual(c['delay_histogram'],[0]*5)
        for cells in c['incident_slices'].values():self.assertEqual(sum(v['planned'] for v in cells.values()),20)
        self.assertEqual(len(c['incident_slices']['class-equipment-mode']),24)
        for d,cells in c['score_slices'].items():
            if d!='event-offset':self.assertEqual(sum(v['observed'] for v in cells.values()),14400)
        self.assertEqual(c['score_slices']['phase']['0']['available'],0)
        self.assertEqual(c['score_slices']['event-offset']['minus-2']['planned'],40)
        self.assertEqual(c['score_slices']['event-offset']['minus-2']['observed'],29)
        self.assertEqual(c['score_slices']['event-offset']['minus-2']['unscored_target'],10)
        self.assertEqual(c['score_slices']['event-offset']['minus-2']['outside_test'],1)
        self.assertEqual(c['score_slices']['context']['clean']['planned'],3365*4)
        self.assertEqual(c['score_slices']['fault-quality-overlap']['yes']['observed'],0)
        described=audit.describe(c)
        empty=next(s for s in described['incident_slices'] if s['dimension']=='equipment' and s['key']=='conveyor-01')
        self.assertIsNone(empty['recall']);self.assertEqual(empty['ci_status'],'not_applicable')

    def test_causal_delay_and_signal_alert_count(self):
        result,prior=hand_evaluation();detect_one(result,prior)
        counts=audit.summarize_evaluation(result,prior)['counts']
        self.assertEqual(counts['delay_histogram'],[1,0,0,0,0])
        target=counts['score_slices']['full-target']['motor-01.motor_temperature']
        self.assertEqual((target['threshold_exceeded'],target['signal_onsets']),(2,1))
        self.assertEqual(counts['equipment_context']['raw-event']['episodes'],1)
        self.assertEqual(counts['incident_slices']['class']['sensor']['detected'],1)

    def test_enabled_overlap_not_disabled_core_quality(self):
        result,prior=hand_evaluation('quality-stress')
        c=audit.summarize_evaluation(result,prior)['counts']
        self.assertEqual(c['score_slices']['fault-quality-overlap']['yes']['observed'],6)

    def test_missing_duplicate_or_wrong_origin_and_unprocessed_incident_rejected(self):
        for mutation in ('missing','duplicate','wrong_origin','missing_incident','unprocessed','false_delay','wrong_prior'):
            result,prior=hand_evaluation()
            if mutation=='missing':result['scores'].pop()
            elif mutation=='duplicate':result['scores'][-1]=result['scores'][0]
            elif mutation=='wrong_origin':result['scores'][0]['sample']=9000
            elif mutation=='missing_incident':result['incidents'].pop()
            elif mutation=='unprocessed':result['incidents'][0]['status']='not_processed'
            elif mutation=='false_delay':result['incidents'][0]['delay_seconds']=0
            else:prior['ledger_audit']['metrics']['machine_recall']['numerator']=1
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):audit.summarize_evaluation(result,prior)

    def test_bad_delay_onset_and_pre_event_support_rejected(self):
        for mutation in ('delay','onset','support'):
            result,prior=hand_evaluation();detect_one(result,prior)
            item=next(i for i in result['incidents'] if i['causal_detected'])
            if mutation=='delay':item['delay_seconds']=2
            elif mutation=='onset':result['source_episodes'][0]['onset_ms']+=1000
            else:item['support_score_ids'][0]=result['scores'][0]['score_id']
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):audit.summarize_evaluation(result,prior)

    def test_profile_inconclusive_retained(self):
        result,prior=hand_evaluation();result['profiles'][0]['status']='inconclusive';prior['evaluation_outcome']='inconclusive'
        counts=audit.summarize_evaluation(result,prior)['counts']
        self.assertEqual(counts['profile_inconclusive_evaluations'],1)
        self.assertEqual(counts['score_slices']['profile-status']['inconclusive']['planned'],300)

    def test_pooled_histogram_and_additivity(self):
        left=audit.empty_counts();right=audit.empty_counts()
        left['delay_histogram']=[9,0,0,0,0];right['delay_histogram']=[0,0,0,0,1]
        audit.add_counts(left,right)
        summary=audit.delay_summary(left['delay_histogram'])
        self.assertEqual((summary['count'],summary['median'],summary['mean']),(10,1,1.4))
        self.assertEqual(audit.delay_summary([0]*5)['median'],None)
        with self.assertRaises(ValueError):audit.delay_summary([True,0,0,0,0])

    def test_accumulator_order_incomplete_and_role_separation(self):
        acc=audit.SliceAccumulator()
        with self.assertRaises(ValueError):acc.finish()
        c=audit.empty_counts();c['evaluations']=1
        for identity in acc.expected:acc.add({'identity':identity,'status':'saved_slice_counts_checked','counts':c})
        r=acc.finish()
        self.assertEqual((len(r['by_seed']),len(r['by_role'])),(90,18))
        self.assertEqual({x['role'] for x in r['by_role']},{'dev','smoke'})
        self.assertFalse(r['bootstrap_performed']);self.assertIsNone(r['selected_candidate'])
        with self.assertRaises(ValueError):acc.add({'identity':acc.expected[0]})
        acc=audit.SliceAccumulator()
        with self.assertRaises(ValueError):acc.add({'identity':acc.expected[1],'status':'saved_slice_counts_checked','counts':c})

    def test_io_authentication_identity_no_writes(self):
        result,prior=hand_evaluation()
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'result.json';raw=json.dumps(result).encode();path.write_bytes(raw)
            pin={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
            r=io.read_saved_evaluation(path,pin,result['identity'],prior)
            self.assertEqual(r['counts']['evaluations'],1)
            self.assertEqual(path.read_bytes(),raw)
            with self.assertRaises(ValueError):io.read_saved_evaluation(path,{**pin,'sha256':'0'*64},result['identity'],prior)
            wrong=copy.deepcopy(result['identity']);wrong['layout']=1
            with self.assertRaises(ValueError):io.read_saved_evaluation(path,pin,wrong,prior)


if __name__=='__main__':unittest.main()
