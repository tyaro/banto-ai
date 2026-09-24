"""Descriptive slices of authenticated saved ledgers, without detector replay.

The caller authenticates each evaluation against its completed independent audit.
This module checks coverage and independently groups existing ledger decisions;
it does not establish score values, redo matching, compute CIs or select models.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import math

from . import anomaly_v03 as registry
from . import anomaly_v03_ledger_audit as ledger

MODES = ('stopped', 'startup', 'low_speed', 'nominal', 'high_load', 'cooldown')
TARGETS = ledger.TARGETS
EQUIPMENT = ledger.EQUIPMENT
PHASES = ('0', '1', '2', '3', '4..6', '7..13', '14..20', '21..29')
QUALITY = ('ok', 'missing', 'stale', 'invalid', 'absent')
INCIDENT_KEYS = {
    'class': ('machine', 'sensor'), 'equipment': EQUIPMENT, 'mode': MODES,
    'class-equipment-mode': tuple(f'{c}.{e}.{m}' for c in ('machine','sensor') for e in EQUIPMENT for m in MODES),
    'test-cycle': tuple(str(i) for i in range(10)), 'event-start-phase': ('0','7','14','21')}
SCORE_KEYS = {'full-target': TARGETS, 'signal-mode': tuple(f'{t}.{m}' for t in TARGETS for m in MODES),
    'phase': PHASES, 'event-offset': tuple('minus-'+str(-i) if i < 0 else str(i) for i in range(-2,6)),
    'context': ('raw-event','grace','clean'), 'quality-current': QUALITY, 'quality-previous': QUALITY,
    'fault-quality-overlap': ('no','yes'), 'profile-status': ('calibrated','inconclusive')}


def need(ok, message):
    if not ok: raise ValueError('slice audit: '+message)


def exact(a, b, message):
    need(registry.canonical_json(a) == registry.canonical_json(b), message)


def delay_summary(histogram):
    """Exact pooled multiset: samples are integer seconds in this frozen replay."""
    need(type(histogram) is list and len(histogram) == 5 and all(type(n) is int and n >= 0 for n in histogram), 'delay histogram')
    total = sum(histogram)
    values = {'median': None, 'mean': None, 'min': None, 'max': None}
    if total:
        def at(position):
            cursor = 0
            for second, amount in enumerate(histogram, 1):
                cursor += amount
                if cursor > position: return second
            raise ValueError('delay order statistic')
        values = {'median': (at((total-1)//2)+at(total//2))/2,
                  'mean': sum((i+1)*n for i,n in enumerate(histogram))/total,
                  'min': float(at(0)), 'max': float(at(total-1))}
    return {'count':total, **values, 'conditioned_on':'causal-detected-only', 'undetected_fill':'forbidden', 'unit':'seconds'}


def empty_counts():
    return {'incident_slices': {d:{k:{'planned':0,'detected':0,'delay_histogram':[0]*5} for k in keys} for d,keys in INCIDENT_KEYS.items()},
            'score_slices': {d:{k:{'planned':0,'observed':0,'available':0,'threshold_exceeded':0,'signal_onsets':0,
                                   'unscored_target':0,'outside_test':0} for k in keys} for d,keys in SCORE_KEYS.items()},
            'equipment_context': {k:{'planned_seconds':0,'episodes':0,'unmatched':0} for k in SCORE_KEYS['context']},
            'delay_histogram':[0]*5, 'evaluations':0, 'profile_inconclusive_evaluations':0}


def add_counts(target, source):
    """Add compact integer histograms; never average ratios or medians."""
    for key, value in source.items():
        if type(value) is dict: add_counts(target[key],value)
        elif type(value) is list:
            for i,n in enumerate(value):target[key][i] += n
        else: target[key] += value


def describe(counts):
    result = {'evaluations': counts['evaluations'], 'profile_inconclusive_evaluations':counts['profile_inconclusive_evaluations'],
              'delay_histogram':counts['delay_histogram'], 'delay_summary':delay_summary(counts['delay_histogram']),
              'incident_slices':[], 'score_slices':[], 'equipment_context':counts['equipment_context']}
    for dimension, cells in counts['incident_slices'].items():
        for key, cell in cells.items():
            n,d=cell['detected'],cell['planned']
            result['incident_slices'].append({'dimension':dimension,'key':key,**cell,
                'recall':None if not d else n/d, 'ci_status':'not_evaluated' if d else 'not_applicable',
                'delay_summary':delay_summary(cell['delay_histogram'])})
    for dimension,cells in counts['score_slices'].items():
        for key,cell in cells.items():
            # Event offset may refer outside test. planned includes those refs;
            # observed is the complete scheduled in-test origin denominator.
            d=cell['observed']
            result['score_slices'].append({'dimension':dimension,'key':key,**cell,
                'availability':None if not d else cell['available']/d,
                'threshold_exceedance_rate':None if not d else cell['threshold_exceeded']/d,
                'signal_onset_rate':None if not d else cell['signal_onsets']/d,
                'ci_status':'not_evaluated' if d else 'not_applicable'})
    return result


def summarize_evaluation(result, prior_audit):
    identity=result['identity'];registry.validate_identity(identity)
    need(identity['role'] in ('dev','smoke'),'dev/smoke only')
    exact(prior_audit['identity'],identity,'prior audit identity')
    exact(prior_audit['ledger_audit']['status'],'ledger_checks_passed','prior ledger audit')
    exact(prior_audit['profile_and_score_audit']['score_derivation_verified'],True,'prior score audit')
    events=registry.event_inventory(identity)
    exact(result['events'],events,'registered event inventory')
    exact(result['status']['run_status'],'complete','complete evaluation required')
    counts=empty_counts();counts['evaluations']=1
    profiles={p['profile_id']:p for p in result['profiles']}
    need(len(profiles)==len(result['profiles'])==48,'profile inventory')
    need(all(p['status'] in ('calibrated','inconclusive') for p in profiles.values()),'profile state')
    counts['profile_inconclusive_evaluations']=int(any(p['status']=='inconclusive' for p in profiles.values()))
    expected_outcome='inconclusive' if counts['profile_inconclusive_evaluations'] else 'success'
    exact(prior_audit['evaluation_outcome'],expected_outcome,'prior profile outcome')
    own_events={equipment:[e for e in events if e['equipment']==equipment] for equipment in EQUIPMENT}
    contexts={}
    for equipment in EQUIPMENT:
        for sample in range(7200,9000):
            es=own_events[equipment]
            context='raw-event' if any(e['start_sample']<=sample<e['end_sample'] for e in es) else (
                'grace' if any(e['end_sample']<=sample<e['window_end_sample'] for e in es) else 'clean')
            contexts[equipment,sample]=context
            counts['equipment_context'][context]['planned_seconds']+=1
    offset_refs=defaultdict(list)
    for event in events:
        for offset in range(-2,6):
            key='minus-'+str(-offset) if offset<0 else str(offset)
            cell=counts['score_slices']['event-offset'][key];cell['planned']+=1
            if event['full_target'] not in TARGETS:cell['unscored_target']+=1
            elif not 7200<=event['start_sample']+offset<9000:cell['outside_test']+=1
            offset_refs[event['full_target'],event['start_sample']+offset].append(key)
    overlap=set()
    # Whole positive window on its target if it intersects an ENABLED quality
    # raw interval. Disabled core masks remain only in planned context/offsets.
    for event in events:
        if event['event_class'] not in ('machine','sensor'):continue
        if any(q['event_class']=='data_quality' and q['enabled'] and q['full_target']==event['full_target']
               and event['start_sample']<q['end_sample'] and q['start_sample']<event['window_end_sample'] for q in events):
            overlap.update((event['full_target'],s) for s in range(event['start_sample'],event['window_end_sample']))
    score_seen=set();score_ids=set();available=Counter();onsets=0
    support_wanted={s for i in result['incidents'] for s in i['support_score_ids']}
    support={}
    need(len(result['scores'])==14400,'scheduled score count')
    for row in result['scores']:
        target,sample=row['full_target'],row['sample'];key=(target,sample)
        need(target in TARGETS and type(sample) is int and 7200<=sample<9000 and key not in score_seen,'score origin coverage')
        score_seen.add(key)
        expected_id=f"{identity['evaluation_id']}-score-{target.replace('.', '-')}-{sample:04d}"
        exact(row['score_id'],expected_id,'score ID')
        need(row['score_id'] not in score_ids,'duplicate score ID');score_ids.add(row['score_id'])
        exact(row['dataset_id'],identity['dataset_id'],'score dataset');exact(row['candidate_id'],identity['candidate_id'],'score candidate')
        equipment=target.split('.')[0];exact(row['equipment'],equipment,'score equipment')
        phase=sample%30;mode=MODES[(sample%180)//30]
        exact(row['phase'],phase,'score phase');exact(row['mode'],mode,'score mode')
        exact(row['timestamp_ms'],ledger.START_MS+sample*1000,'score time')
        profile=profiles[row['profile_id']]
        exact([profile['full_target'],profile['mode']],[target,mode],'score profile lookup')
        need(type(row['available']) is bool and type(row['threshold_exceeded']) is bool,'score decisions')
        need(not row['threshold_exceeded'] or row['available'],'unavailable threshold exceedance')
        available[target]+=int(row['available'])
        onset=bool(row['source_episode_id'] is not None and row['streak']==2)
        onsets+=onset
        deps={(d['full_target'],d['sample']):d for d in row['dependencies']}
        need(len(deps)==len(row['dependencies']),'duplicate dependency')
        q=[deps.get((target,s),{}).get('quality','absent') for s in (sample,sample-1)]
        need(all(v in QUALITY for v in q),'quality labels')
        phase_key=str(phase) if phase<4 else ('4..6' if phase<7 else '7..13' if phase<14 else '14..20' if phase<21 else '21..29')
        labels={'full-target':target,'signal-mode':target+'.'+mode,'phase':phase_key,
                'context':contexts[equipment,sample],'quality-current':q[0],'quality-previous':q[1],
                'fault-quality-overlap':'yes' if key in overlap else 'no','profile-status':profile['status']}
        cells=[]
        for dimension,label in labels.items():
            cell=counts['score_slices'][dimension][label];cell['planned']+=1;cells.append(cell)
        cells.extend(counts['score_slices']['event-offset'][k] for k in offset_refs.get(key,()))
        for cell in cells:
            cell['observed']+=1;cell['available']+=row['available'];cell['threshold_exceeded']+=row['threshold_exceeded'];cell['signal_onsets']+=onset
        if row['score_id'] in support_wanted:support[row['score_id']]=row
    groups={g['episode_id']:g for g in result['equipment_episodes']}
    sources={s['episode_id']:s for s in result['source_episodes']}
    need(len(groups)==len(result['equipment_episodes']) and len(sources)==len(result['source_episodes'])==onsets,'episode inventory')
    for group in groups.values():
        sample=(group['onset_ms']-ledger.START_MS)//1000
        cell=counts['equipment_context'][contexts[group['equipment'],sample]]
        cell['episodes']+=1;cell['unmatched']+=group['matched_event_id'] is None
    positives={e['event_id']:e for e in events if e['event_class'] in ('machine','sensor')}
    incidents={i['event_id']:i for i in result['incidents']}
    need(len(incidents)==len(result['incidents'])==20 and set(incidents)==set(positives),'incident coverage')
    detected_by_class=Counter()
    for event_id,event in positives.items():
        item=incidents[event_id]
        exact(item['dataset_id'],identity['dataset_id'],'incident dataset');exact(item['status'],'processed','unprocessed incident')
        need(type(item['causal_detected']) is bool,'detected flag')
        detected=item['causal_detected'];delay=item['delay_seconds']
        if detected:
            group=groups[item['matched_episode_id']];source=sources[item['selected_source_episode_id']]
            need(group['matched_event_id']==event_id and source['episode_id'] in group['source_episode_ids'],'matched backlinks')
            need(source['full_target']==event['full_target'] and source['onset_ms']==group['onset_ms'],'causal target onset')
            need(type(delay) in (int,float) and math.isfinite(delay) and delay in (1,2,3,4,5),'delay seconds')
            need(delay==(group['onset_ms']-event['start_ms'])/1000,'delay from onset')
            need(len(item['support_score_ids'])==2 and all(event['start_ms']<=support[s]['timestamp_ms']<event['window_end_ms'] for s in item['support_score_ids']),'post-event support')
            counts['delay_histogram'][int(delay)-1]+=1;detected_by_class[event['event_class']]+=1
        else: exact(delay,None,'undetected delay must be null')
        labels={'class':event['event_class'],'equipment':event['equipment'],'mode':event['mode'],
            'class-equipment-mode':f"{event['event_class']}.{event['equipment']}.{event['mode']}",
            'test-cycle':str(event['cycle']),'event-start-phase':str(event['start_sample']%30)}
        for dimension,label in labels.items():
            cell=counts['incident_slices'][dimension][label];cell['planned']+=1;cell['detected']+=detected
            if detected:cell['delay_histogram'][int(delay)-1]+=1
    metrics=prior_audit['ledger_audit']['metrics']
    for kind in ('machine','sensor'):exact(metrics[kind+'_recall']['numerator'],detected_by_class[kind],'prior recall count')
    exact(metrics['precision']['numerator'],sum(counts['delay_histogram']),'prior detections')
    exact(metrics['precision']['denominator'],len(groups),'prior episodes')
    exact(metrics['false_alert_burden']['numerator'],sum(c['unmatched'] for c in counts['equipment_context'].values()),'prior false episodes')
    exact(metrics['clean_rate']['numerator'],counts['equipment_context']['clean']['unmatched'],'prior clean false count')
    exact(counts['equipment_context']['clean']['planned_seconds'],3365,'planned clean exposure')
    for row in metrics['availability']:exact(row['metric']['numerator'],available[row['full_target']],'prior availability')
    ledger._numeric_equal(metrics['delay_summary'],delay_summary(counts['delay_histogram']))
    for dimension,cells in counts['score_slices'].items():
        if dimension!='event-offset':exact(sum(c['observed'] for c in cells.values()),14400,'score partition')
        else:
            for cell in cells.values():exact(cell['planned'],cell['observed']+cell['unscored_target']+cell['outside_test'],'event-relative reference coverage')
    for cells in counts['incident_slices'].values():exact(sum(c['planned'] for c in cells.values()),20,'incident partition')
    return {'identity':identity,'counts':counts,'status':'saved_slice_counts_checked',
            'formal_permission':False,'performance_status':'not_evaluated','new_score_computations':0}


class SliceAccumulator:
    """Ordered fixed inventory; retain compact counts, never large score rows."""
    def __init__(self):
        self.expected=registry.evaluation_inventory('dev')+registry.evaluation_inventory('smoke')
        self.position=0
        self.seed_counts={}

    def add(self, row):
        need(self.position<len(self.expected),'too many evaluations')
        exact(row['status'],'saved_slice_counts_checked','slice status')
        exact(row['identity'],self.expected[self.position],'ordered complete slice inventory')
        identity=row['identity']
        key=tuple(identity[k] for k in ('role','seed','candidate_id','stratum'))
        self.seed_counts.setdefault(key,empty_counts())
        add_counts(self.seed_counts[key],row['counts'])
        self.position+=1

    def finish(self):
        need(self.position==720,'incomplete slice campaign')
        by_seed=[];roles={}
        for entry in registry.seed_registry()['entries'][:2]:
            role=entry['role']
            for seed in entry['seeds']:
                for candidate in ledger.THRESHOLDS:
                    core=self.seed_counts[role,seed,candidate,'core']
                    stress=self.seed_counts[role,seed,candidate,'quality-stress']
                    exact([core['evaluations'],stress['evaluations']],[12,12],'twelve layouts')
                    overall=empty_counts();add_counts(overall,core);add_counts(overall,stress)
                    for layer,counts in zip(('core','quality-stress','overall'),(core,stress,overall)):
                        by_seed.append({'role':role,'seed':seed,'candidate_id':candidate,'stratum':layer,**describe(counts)})
                        key=(role,candidate,layer);roles.setdefault(key,empty_counts());add_counts(roles[key],counts)
        return {'status':'complete_dev_smoke_descriptive_slices','evaluations':720,'by_seed':by_seed,
            'by_role':[{'role':k[0],'candidate_id':k[1],'stratum':k[2],**describe(v)} for k,v in roles.items()],
            'formal_permission':False,'promotion_allowed':False,'independent_s6_complete':False,
            'performance_status':'not_evaluated','selected_candidate':None,'bootstrap_performed':False,
            'class_precision':'not_applicable','event_offsets_exclusive_partition':False,
            'limits':['inherited authenticated profile/score/matching audits; no detector replay',
                      'descriptive dev/smoke only; no formal analysis document or CI']}
