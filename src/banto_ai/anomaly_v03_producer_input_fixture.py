"""Pure byte-bound producer-to-aggregate rehearsal using invented registrations.

No filesystem, actual registered observations, score reconstruction, inference,
process authentication, or formal acceptance. Caller-retained pins are trusted.
"""
from __future__ import annotations
from collections import Counter
import copy
import hashlib

from . import anomaly_v03_consumer_input as metadata
from . import anomaly_v03_consumer_evidence as evidence
from . import anomaly_v03_inference_audit as arithmetic

v = metadata.v
FORMAT = 'anomaly-v03-producer-input-fixture-manifest-v1'
PLAN_FORMAT = 'anomaly-v03-producer-input-fixture-plan-v1'
ATTEMPT_FORMAT = 'anomaly-v03-producer-input-fixture-attempt-v1'
SUMMARY_FORMAT = 'anomaly-v03-producer-input-fixture-summary-v1'
CLOSE_FORMAT = 'anomaly-v03-producer-input-fixture-completion-v1'
INPUT_FORMAT = 'anomaly-v03-producer-input-fixture-placeholder-v1'
MAX_ATTEMPTS = 4  # Parser bound, never permission to retry.
MAX_FILES = 20000
MAX_MANIFEST = 4*1024**2
MAX_FILE = 128*1024
MAX_TOTAL = 32*1024**2
CLOSED = {**evidence.CLOSED,'registered_data_read':False,'formal_bootstrap_performed':False,
    'campaign_evaluations_credited':0,'analysis_authorized':False,'producer_execution_authenticated':False,
    'raw_observation_derivation_checked':False,'numerical_inference_performed':False}


def pin(raw):
    v.require(type(raw) is bytes,'raw bytes required')
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def plan(cluster_count=40):
    v.require(type(cluster_count) is int and 1 <= cluster_count <= 40,'1..40 invented registered clusters')
    return {'format':PLAN_FORMAT,'mode':'fixture','invented_only':True,'registration_id':'invented-producer-v1',
        'clusters':[{'registered_index':i,'seed':i,'cluster_id':f'invented-{i:02d}'} for i in range(cluster_count)],
        'layouts':list(range(12)),'candidates':list(arithmetic.CANDIDATES),'strata':list(arithmetic.STRATA[:2])}


def inventory(registration):
    """Fixed, ordered, paired identities. Never expand the real seed registry."""
    v.require(type(registration) is dict and type(registration.get('clusters')) is list,'fixture registration')
    evidence._same(registration,plan(len(registration['clusters'])),'fixed invented registration')
    rows = []
    for cluster in registration['clusters']:
        for layout in registration['layouts']:
            pair = f"{cluster['cluster_id']}-layout-{layout:02d}"
            for layer in registration['strata']:
                dataset = pair+'-'+layer
                for candidate in registration['candidates']:
                    rows.append({'role':'fixture','seed':cluster['seed'],'registered_index':cluster['registered_index'],
                        'cluster_id':cluster['cluster_id'],'layout':layout,'stratum':layer,'candidate_id':candidate,
                        'pair_id':pair,'dataset_id':dataset,'evaluation_id':dataset+'-'+candidate})
    return rows


def attempt_path(chunk,number):return f'chunks/{chunk:04d}/attempt-{number:02d}.json'
def summary_path(identity,number):return f"summaries/{identity['evaluation_id']}/attempt-{number:02d}.json"
def input_path(identity,kind):return f"inputs/{identity['dataset_id']}/{kind}.json"


def _worker(value,state):
    evidence._keys(value,'exit_confirmed exit_code observation_errors','producer worker fields')
    v.require(type(value['exit_confirmed']) is bool,'worker exit boolean')
    if value['exit_confirmed']:
        v.require(type(value['exit_code']) is int and -(2**31) <= value['exit_code'] < 2**32,'worker exit code')
    else:v.require(value['exit_code'] is None,'unconfirmed worker exit code')
    errors = value['observation_errors']
    v.require(type(errors) is list and len(errors) <= 16 and all(type(x) is str and 0 < len(x) <= 256 for x in errors),'bounded worker errors')
    if state == 'complete':evidence._same(value,{'exit_confirmed':True,'exit_code':0,'observation_errors':[]},'complete worker needs confirmed clean exit')
    if state in ('in_progress','not_started'):
        evidence._same(value,{'exit_confirmed':False,'exit_code':None,'observation_errors':[]},'unfinished worker state')


def _summary(value,slot,number,registration_pin):
    evidence._keys(value,'format mode invented_only registration_pin identity attempt input_hashes profile_status counts effective_clean_seconds delay_histogram','summary fields')
    for key,want in {'format':SUMMARY_FORMAT,'mode':'fixture','invented_only':True,'registration_pin':registration_pin,
        'identity':slot['identity'],'attempt':number,'input_hashes':slot['input_hashes'],'profile_status':slot['profile_status']}.items():
        evidence._same(value[key],want,'summary binding '+key)
    raw = value['counts'];v.require(type(raw) is dict and set(raw) == set(arithmetic.METRICS),'summary metric inventory')
    for kind in arithmetic.METRICS:arithmetic.counts(raw[kind],kind)
    for kind,d in {'machine_recall':10,'sensor_recall':10,'clean_rate':3365,'false_alert_burden':20,
                   **dict.fromkeys(arithmetic.AVAILABILITY,1800)}.items():
        evidence._same(raw[kind][1],d,'one-layout denominator')
    detected = raw['machine_recall'][0]+raw['sensor_recall'][0]
    v.require(raw['precision'][0] == detected and raw['precision'][1] == detected+raw['false_alert_burden'][0],'matched/unmatched summary partition')
    v.require(raw['clean_rate'][0] <= raw['false_alert_burden'][0],'clean false-alert subset')
    exposure = value['effective_clean_seconds']
    v.require(type(exposure) is int and 0 <= exposure <= 3365,'effective exposure bounds')
    histogram = value['delay_histogram']
    v.require(type(histogram) is list and len(histogram) == 5 and all(type(n) is int and 0 <= n <= 20 for n in histogram)
        and sum(histogram) == detected,'detected-only delay histogram')


def bind_producer_inputs(manifest_raw, snapshots, *, expected_mode, expected_manifest_pin, expected_registration_pin):
    """Authenticate supplied invented bytes and aggregate only complete latest attempts.

    Incomplete but consistent histories return no cluster aggregates. A failed
    latest attempt cannot fall back to a prior success. Nothing is read or run.
    """
    v.require(type(expected_mode) is str and expected_mode == 'fixture','only fixture producer input is open')
    v.require(type(manifest_raw) is bytes and 0 < len(manifest_raw) <= MAX_MANIFEST,'manifest byte bound')
    evidence._pin(expected_manifest_pin);evidence._pin(expected_registration_pin)
    evidence._raw(manifest_raw,expected_manifest_pin,'external manifest pin')
    manifest = v.strict_json(manifest_raw)
    v.require(manifest_raw == v.canonical_json(manifest),'canonical manifest')
    evidence._keys(manifest,'format mode registration_pin chunks payload_pins','producer manifest fields')
    evidence._same(manifest['format'],FORMAT,'producer manifest format');evidence._same(manifest['mode'],'fixture','manifest mode')
    evidence._same(manifest['registration_pin'],expected_registration_pin,'external registration pin')
    pins = manifest['payload_pins']
    v.require(type(pins) is dict and type(snapshots) is dict and 2 <= len(pins) <= MAX_FILES and set(pins) == set(snapshots),'exact supplied payload inventory')
    total = len(manifest_raw)
    for name,p in pins.items():
        v.safe_relative_path(name);evidence._pin(p);raw = snapshots[name]
        v.require(type(raw) is bytes and 0 < len(raw) <= MAX_FILE,'payload byte bound')
        total += len(raw);v.require(total <= MAX_TOTAL,'total fixture byte bound')
        evidence._raw(raw,p,'external payload pin: '+name)
    used = set()
    def get(name):
        v.require(name in pins,'missing referenced payload: '+name);used.add(name)
        raw = snapshots[name];value = v.strict_json(raw)
        v.require(raw == v.canonical_json(value),'canonical fixture payload: '+name)
        return value
    def failure_evidence(failure,name):
        if failure is None or failure['evidence_sha256'] is None:return
        value = get(name);evidence._same(pins[name]['sha256'],failure['evidence_sha256'],'failure evidence bytes')
        evidence._keys(value,'format mode scope stage reason detail','failure evidence fields')
        for key,want in {'format':'anomaly-v03-producer-input-fixture-failure-v1','mode':'fixture','scope':name,
            'stage':failure['stage'],'reason':failure['reason']}.items():evidence._same(value[key],want,'failure evidence binding '+key)
        v.require(type(value['detail']) is str and len(value['detail']) <= 4096,'bounded failure detail')
    registration = get('registration.json')
    evidence._same(pins['registration.json'],expected_registration_pin,'registration bytes pin')
    identities = inventory(registration);planned = len(identities)//6
    chunks = manifest['chunks']
    v.require(type(chunks) is list and len(chunks) == planned,'complete planned chunk inventory required')
    latest = [];latest_pins = [];history = [];attempt_total = 0;coverage = Counter();latest_rows = []
    known_inputs = set()
    for index,chunk in enumerate(chunks):
        evidence._keys(chunk,'chunk_index attempt_count','chunk declaration fields')
        v.require(type(chunk['chunk_index']) is int and chunk['chunk_index'] == index,'chunk order/index')
        count = chunk['attempt_count'];v.require(type(count) is int and 0 <= count <= MAX_ATTEMPTS,'bounded attempt count')
        wanted = identities[index*6:index*6+6];by_dataset = {};state = 'not_started';rows = [];current = Counter({'not_started':6})
        for number in range(1,count+1):
            name = attempt_path(index,number);record = get(name)
            evidence._keys(record,'format mode registration_pin chunk_index attempt_record worker','attempt receipt fields')
            for key,want in {'format':ATTEMPT_FORMAT,'mode':'fixture','registration_pin':expected_registration_pin,'chunk_index':index}.items():
                evidence._same(record[key],want,'attempt receipt binding '+key)
            attempt = record['attempt_record'];current = metadata._attempt(attempt,wanted,number,by_dataset)
            state = attempt['state'];_worker(record['worker'],state)
            failure_evidence(attempt['failure'],f'failures/chunk-{index:04d}-attempt-{number:02d}.json')
            if number < count:
                v.require(state == 'failed','retry without failed prior attempt')
                v.require(attempt['failure']['reason'] not in metadata.INTEGRITY_REASONS,'retry after integrity failure')
            if state == 'failed':history.append({'chunk_index':index,'attempt':number,'failure':copy.deepcopy(attempt['failure']),
                'is_latest':number == count,'receipt_pin':copy.deepcopy(pins[name])})
            rows = []
            for slot in attempt['evaluations']:
                identity = slot['identity'];hashes = slot['input_hashes'];summary = None
                if hashes is not None:
                    for kind,digest in hashes.items():
                        source = input_path(identity,kind)
                        v.require(source in pins and pins[source]['sha256'] == digest,'slot input byte binding')
                        if source not in known_inputs:
                            value = get(source);evidence._keys(value,'format invented_only dataset_id kind token','placeholder fields')
                            for key,want in {'format':INPUT_FORMAT,'invented_only':True,'dataset_id':identity['dataset_id'],'kind':kind}.items():
                                evidence._same(value[key],want,'invented input binding '+key)
                            v.require(type(value['token']) is str and len(value['token']) <= 256,'bounded placeholder token');known_inputs.add(source)
                if slot['evaluation_sha256'] is not None:
                    path = summary_path(identity,number);summary = get(path)
                    evidence._same(pins[path]['sha256'],slot['evaluation_sha256'],'slot summary bytes')
                    _summary(summary,slot,number,expected_registration_pin)
                rows.append((copy.deepcopy(identity),slot['status'],summary))
        coverage.update(current);attempt_total += count;latest.append(state)
        latest_pins.append(copy.deepcopy(pins[attempt_path(index,count)]) if count else None)
        if count:latest_rows.extend(rows)
        else:latest_rows.extend((copy.deepcopy(i),'not_started',None) for i in wanted)
    close = get('producer/completion.json')
    evidence._keys(close,'format mode registration_pin state worker failure latest_attempt_pins','producer completion fields')
    for key,want in {'format':CLOSE_FORMAT,'mode':'fixture','registration_pin':expected_registration_pin,'latest_attempt_pins':latest_pins}.items():
        evidence._same(close[key],want,'producer completion binding '+key)
    state = close['state'];v.require(type(state) is str and state in ('not_started','in_progress','complete','failed'),'producer completion state')
    metadata._failure(state,close['failure']);_worker(close['worker'],state)
    failure_evidence(close['failure'],'producer/failure.json')
    if state == 'not_started':v.require(attempt_total == 0,'not-started producer has attempts')
    if state == 'complete':v.require(all(s == 'complete' for s in latest),'complete producer has unfinished chunk')
    v.require(used == set(pins),'unreferenced supplied payloads')
    complete = state == 'complete';counts = {s:coverage[s] for s in metadata.SLOT_STATES}
    cluster_values = [];diagnostics = []
    declared = {'format':'anomaly-v03-wrapper-fixture-coverage-v1','invented_only':True,'layout_ids':list(range(12)),'clusters':[]}
    grouped = {(r['cluster_id'],c,s):[] for r in registration['clusters'] for c in arithmetic.CANDIDATES for s in arithmetic.STRATA[:2]}
    for identity,status,summary in latest_rows:grouped[identity['cluster_id'],identity['candidate_id'],identity['stratum']].append((status,summary))
    for entry in registration['clusters']:
        key = entry['cluster_id'];cluster = {'cluster_id':key,'candidates':{}};diagnostic = {'cluster_id':key,'candidates':{}}
        declaration = {'cluster_id':key,'candidates':{}}
        for candidate in arithmetic.CANDIDATES:
            cluster['candidates'][candidate] = {};diagnostic['candidates'][candidate] = {};declaration['candidates'][candidate] = {}
            for layer in arithmetic.STRATA[:2]:
                cells = grouped[key,candidate,layer];v.require(len(cells) == 12,'twelve layout slots per aggregate')
                declaration['candidates'][candidate][layer] = [s for s,_ in cells]
                if not complete:continue
                values = [value for _,value in cells];profile = 'inconclusive' if any(s == 'inconclusive' for s,_ in cells) else 'calibrated'
                cluster['candidates'][candidate][layer] = {'profile_status':profile,
                    'counts':{m:[sum(x['counts'][m][i] for x in values) for i in (0,1)] for m in arithmetic.METRICS}}
                histogram = [sum(x['delay_histogram'][i] for x in values) for i in range(5)]
                diagnostic['candidates'][candidate][layer] = {'effective_clean_seconds':sum(x['effective_clean_seconds'] for x in values),
                    'detected_delays':[i+1 for i,n in enumerate(histogram) for _ in range(n)]}
        declared['clusters'].append(declaration)
        if complete:cluster_values.append(cluster);diagnostics.append(diagnostic)
    if complete:arithmetic._fixture_clusters(cluster_values)
    return {**CLOSED,'format':'anomaly-v03-producer-input-fixture-bound-v1','mode':'fixture','invented_only':True,
        'status':'fixture_inputs_bound' if complete else 'fixture_inputs_incomplete','complete_for_aggregation':complete,
        'all_profiles_calibrated':complete and counts['inconclusive'] == 0,'input_bytes_verified':True,'scope':'supplied-invented-bytes-only',
        'manifest_pin':copy.deepcopy(expected_manifest_pin),'registration_pin':copy.deepcopy(expected_registration_pin),
        'planned_chunks':planned,'planned_evaluations':len(identities),'verified_payload_files':len(pins),'verified_payload_bytes':total-len(manifest_raw),
        'producer_state':state,'producer_failure':copy.deepcopy(close['failure']),'attempt_count':attempt_total,
        'latest_attempt_pins':latest_pins,'coverage':counts,'failed_attempt_history':history,
        'clusters':cluster_values if complete else None,'diagnostics':diagnostics if complete else None,'wrapper_coverage':declared,
        'not_checked':['raw observation-to-summary derivation','registered coverage and seed adoption','source/runtime and historical process authenticity',
                       'formal retries and acceptance','slice/sidecar count derivation','inference and publication']}
