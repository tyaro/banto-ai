"""Bind invented per-attempt slice bytes to producer receipts, without IO.

Caller-retained pins authenticate supplied bytes, not historical executions or
observation-to-count derivation. This additive format leaves primary v1 intact.
"""
from __future__ import annotations
import copy

from . import anomaly_v03_producer_input_fixture as primary
from . import anomaly_v03_slice_fixture as connection

v = primary.v
evidence = primary.evidence
S = connection.slices
FORMAT = 'anomaly-v03-producer-slice-fixture-manifest-v1'
ROW_FORMAT = 'anomaly-v03-producer-slice-fixture-row-v1'
OUTPUT_FORMAT = 'anomaly-v03-producer-slice-fixture-bound-v1'
MAX_FILE = 32*1024
MAX_MANIFEST = 4*1024**2
MAX_TOTAL = 32*1024**2  # Both manifests and both sets of supplied payloads.
MAX_FILES = 11520  # 480 chunks * 6 slots * 4 attempts; not retry permission.
INCIDENT = tuple((d,k) for d,keys in S.INCIDENT_KEYS.items() for k in keys)
SCORE = tuple((d,k) for d,keys in S.SCORE_KEYS.items() for k in keys)
CONTEXT = tuple(S.SCORE_KEYS['context'])
ENCODING = {'format':'anomaly-v03-ordered-slice-cells-v1',
    'incident_rows':[list(x) for x in INCIDENT],
    'incident_fields':['planned','detected','delay_1','delay_2','delay_3','delay_4','delay_5'],
    'score_rows':[list(x) for x in SCORE], 'score_fields':list(connection.inputs.SC),
    'context_rows':list(CONTEXT),'context_fields':['planned_seconds','episodes','unmatched']}


def slice_path(identity,attempt):
    return f"slices/{identity['evaluation_id']}/attempt-{attempt:02d}.json"


def _matrix(value,rows,columns,bound,name):
    v.require(type(value) is list and len(value) == rows,name+' rows')
    v.require(all(type(row) is list and len(row) == columns and
        all(type(n) is int and 0 <= n <= bound for n in row) for row in value),name+' bounded integer cells')


def _decode(cells):
    evidence._keys(cells,'incident score context delay_histogram evaluations profile_inconclusive_evaluations','compact slice cells')
    _matrix(cells['incident'],len(INCIDENT),7,20,'incident')
    _matrix(cells['score'],len(SCORE),7,14400,'score')
    _matrix(cells['context'],len(CONTEXT),3,14400,'context')
    _matrix([cells['delay_histogram']],1,5,20,'delay')
    v.require(type(cells['evaluations']) is int and cells['evaluations'] == 1,'one evaluation per slice row')
    n = cells['profile_inconclusive_evaluations']
    v.require(type(n) is int and n in (0,1),'one profile outcome')
    raw = S.empty_counts();raw['evaluations'] = 1;raw['profile_inconclusive_evaluations'] = n
    raw['delay_histogram'] = cells['delay_histogram'].copy()
    for (d,k),row in zip(INCIDENT,cells['incident']):
        raw['incident_slices'][d][k] = {'planned':row[0],'detected':row[1],'delay_histogram':row[2:].copy()}
    for (d,k),row in zip(SCORE,cells['score']):raw['score_slices'][d][k] = dict(zip(connection.inputs.SC,row))
    for k,row in zip(CONTEXT,cells['context']):raw['equipment_context'][k] = dict(zip(ENCODING['context_fields'],row))
    return raw


def _check(raw,summary):
    connection.inputs._slice_counts(S.describe(raw),1)
    connection._marginals(raw)
    connection._primary(raw,summary['counts'],described=False)
    evidence._same(raw['delay_histogram'],summary['delay_histogram'],'slice/summary delay histogram')
    evidence._same(raw['profile_inconclusive_evaluations'],int(summary['profile_status'] == 'inconclusive'),'slice/summary profile')
    if summary['profile_status'] == 'calibrated':
        # An inconclusive evaluation may contain both kinds of target profiles.
        evidence._same(raw['score_slices']['profile-status']['inconclusive'],
            S.empty_counts()['score_slices']['profile-status']['inconclusive'],'calibrated evaluation has inconclusive scores')
    else:v.require(raw['score_slices']['profile-status']['inconclusive']['planned'] > 0,'inconclusive profile score coverage')


def bind_producer_slices(primary_input, manifest_raw, snapshots, *, expected_mode, expected_manifest_pin):
    """Join all referenced summaries, retaining history but aggregating latest only.

    A complete primary result cannot accept a missing sidecar. A consistent
    incomplete primary returns full coverage/history and no slice aggregates.
    """
    v.require(type(expected_mode) is str and expected_mode == 'fixture','only fixture slice input is open')
    evidence._keys(primary_input,'manifest_raw snapshots expected_mode expected_manifest_pin expected_registration_pin','primary input arguments')
    evidence._same(primary_input['expected_mode'],expected_mode,'primary/slice mode')
    evidence._pin(expected_manifest_pin)
    v.require(type(manifest_raw) is bytes and 0 < len(manifest_raw) <= MAX_MANIFEST,'slice manifest byte bound')
    evidence._raw(manifest_raw,expected_manifest_pin,'external slice manifest pin')
    manifest = v.strict_json(manifest_raw)
    v.require(manifest_raw == v.canonical_json(manifest),'canonical slice manifest')
    evidence._keys(manifest,'format mode invented_only primary_manifest_pin registration_pin encoding payload_pins','slice manifest fields')
    for key,want in {'format':FORMAT,'mode':'fixture','invented_only':True,
        'primary_manifest_pin':primary_input['expected_manifest_pin'],
        'registration_pin':primary_input['expected_registration_pin'],'encoding':ENCODING}.items():
        evidence._same(manifest[key],want,'slice manifest binding '+key)
    pins = manifest['payload_pins']
    v.require(type(pins) is dict and type(snapshots) is dict and len(pins) <= MAX_FILES and set(pins) == set(snapshots),'exact slice payload inventory')
    total = len(manifest_raw)
    for name,pin in pins.items():
        v.safe_relative_path(name);evidence._pin(pin);raw = snapshots[name]
        v.require(type(raw) is bytes and 0 < len(raw) <= MAX_FILE,'slice payload byte bound')
        total += len(raw);v.require(total <= MAX_TOTAL,'slice byte bound')
        evidence._raw(raw,pin,'slice payload pin '+name)
    result = primary.bind_producer_inputs(**primary_input)
    total += len(primary_input['manifest_raw'])+result['verified_payload_bytes']
    v.require(total <= MAX_TOTAL,'combined primary/slice byte bound')
    main = v.strict_json(primary_input['manifest_raw']);payloads = primary_input['snapshots']
    complete = result['complete_for_aggregation'];groups = {};used = set();latest_pins = {};historical = 0
    for chunk in main['chunks']:
        index,count = chunk['chunk_index'],chunk['attempt_count']
        for number in range(1,count+1):
            attempt_name = primary.attempt_path(index,number)
            receipt = v.strict_json(payloads[attempt_name])
            for slot in receipt['attempt_record']['evaluations']:
                if slot['evaluation_sha256'] is None:continue
                identity = slot['identity'];name = slice_path(identity,number)
                v.require(name in pins,'missing referenced slice payload: '+name);used.add(name)
                raw_bytes = snapshots[name];row = v.strict_json(raw_bytes)
                v.require(raw_bytes == v.canonical_json(row),'canonical slice row')
                evidence._keys(row,'format mode invented_only primary_manifest_pin registration_pin attempt_receipt_pin summary_pin identity attempt input_hashes cells','slice row fields')
                summary_name = primary.summary_path(identity,number)
                for key,want in {'format':ROW_FORMAT,'mode':'fixture','invented_only':True,
                    'primary_manifest_pin':primary_input['expected_manifest_pin'],'registration_pin':primary_input['expected_registration_pin'],
                    'attempt_receipt_pin':main['payload_pins'][attempt_name],'summary_pin':main['payload_pins'][summary_name],
                    'identity':identity,'attempt':number,'input_hashes':slot['input_hashes']}.items():
                    evidence._same(row[key],want,'slice row binding '+key)
                summary = v.strict_json(payloads[summary_name]);raw = _decode(row['cells']);_check(raw,summary)
                if number != count:historical += 1;continue
                latest_pins[name] = copy.deepcopy(pins[name])
                if complete:
                    group = (identity['cluster_id'],identity['candidate_id'],identity['stratum'])
                    if group not in groups:groups[group] = S.empty_counts()
                    S.add_counts(groups[group],raw)
    v.require(used == set(pins),'unreferenced slice payloads')
    source = None
    if complete:
        source = {'format':connection.INPUT_FORMAT,'invented_only':True,'clusters':[]}
        for cluster,detail in zip(result['clusters'],result['diagnostics']):
            entry = {'cluster_id':cluster['cluster_id'],'candidates':{}}
            for candidate in primary.arithmetic.CANDIDATES:
                entry['candidates'][candidate] = {}
                for layer in primary.arithmetic.STRATA[:2]:
                    raw = groups[cluster['cluster_id'],candidate,layer]
                    evidence._same(raw['evaluations'],12,'twelve layout slice coverage')
                    connection._primary(raw,cluster['candidates'][candidate][layer]['counts'],described=False)
                    histogram = [0]*5
                    for delay in detail['candidates'][candidate][layer]['detected_delays']:histogram[delay-1] += 1
                    evidence._same(raw['delay_histogram'],histogram,'aggregate slice/diagnostic delay')
                    evidence._same(raw['profile_inconclusive_evaluations'],
                        result['wrapper_coverage']['clusters'][len(source['clusters'])]['candidates'][candidate][layer].count('inconclusive'),
                        'aggregate inconclusive coverage')
                    entry['candidates'][candidate][layer] = raw
            source['clusters'].append(entry)
    return {**primary.CLOSED,'format':OUTPUT_FORMAT,'mode':'fixture','invented_only':True,
        'status':'fixture_slices_bound' if complete else 'fixture_slices_incomplete',
        'complete_for_aggregation':complete,'scope':'supplied-invented-bytes-only',
        'primary':result,'slice_source':source,'slice_manifest_pin':copy.deepcopy(expected_manifest_pin),
        'verified_slice_files':len(pins),'verified_slice_bytes':sum(p['bytes'] for p in pins.values()),
        'combined_input_bytes':total,'historical_summary_count':historical,'latest_slice_pins':latest_pins,
        'not_checked':['raw observation-to-summary derivation','registered seed and coverage authenticity',
            'historical process/source/runtime authenticity','formal acceptance','inference and publication']}
