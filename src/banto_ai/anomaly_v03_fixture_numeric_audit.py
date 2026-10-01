"""Independent, literal-index arithmetic for bounded invented primary tables.

Stdlib only. Never import the calculation/adapter/slice implementation. This
checks nine primary tables, not slice derivation, campaign data, or formal S6.
"""
from fractions import Fraction
import hashlib
import json
import math

CANDIDATES = ('c0-diff-control', 'c1-phase-level', 'c2-phase-conditional')
LAYERS = ('core', 'quality-stress', 'overall')
TARGETS = tuple(e+'.'+s for e in ('motor-01', 'conveyor-01') for s in
                ('motor_current', 'motor_temperature', 'conveyor_speed', 'vibration_feature'))
METRICS = ('machine_recall', 'sensor_recall', 'precision', 'clean_rate', 'false_alert_burden',
           *('availability:'+t for t in TARGETS))
ABSOLUTE = tuple(m for m in METRICS if m != 'false_alert_burden')
PAIRED = tuple(m for m in METRICS if m != 'precision')
MAX_DRAWS = 8
CLOSED = {'formal_permission': False, 'promotion_allowed': False, 'independent_s6_complete': False,
          'execution_authenticated': False, 'source_closure_complete': False, 'runtime_closure_complete': False,
          'registered_data_read': False, 'formal_bootstrap_performed': False, 'published': False,
          'selected_candidate': None, 'performance_status': 'not_evaluated'}


def require(ok, why):
    if not ok:raise ValueError('fixture numeric audit: '+why)


def canonical(value):return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')


def same(actual, expected, where):
    require(canonical(actual) == canonical(expected), where+' differs')


def fields(value, names, where):require(type(value) is dict and set(value) == set(names.split()), where+' fields')


def validate_input(value):
    fields(value, 'format invented_only clusters diagnostics draws engineering_ready_assumption', 'input')
    same(value['format'], 'anomaly-v03-document-fixture-input-v1', 'input identity')
    same(value['invented_only'], True, 'invented input');require(type(value['engineering_ready_assumption']) is bool, 'readiness boolean')
    require(type(value['clusters']) is list and len(value['clusters']) == 40, '40 clusters')
    require(type(value['diagnostics']) is list and len(value['diagnostics']) == 40, '40 diagnostics')
    require(type(value['draws']) is list and 1 <= len(value['draws']) <= MAX_DRAWS, 'one to eight draws')
    for draw in value['draws']:
        require(type(draw) is list and len(draw) == 40 and all(type(i) is int and 0 <= i < 40 for i in draw), 'draw indices')
    denominators = {'machine_recall': 120, 'sensor_recall': 120, 'clean_rate': 40380,
                    'false_alert_burden': 240, **{'availability:'+t:21600 for t in TARGETS}}
    for i, (cluster, diagnostic) in enumerate(zip(value['clusters'], value['diagnostics'])):
        for row in (cluster, diagnostic):
            fields(row, 'cluster_id candidates', 'cluster');same(row['cluster_id'], f'invented-{i:02d}', 'cluster order')
            fields(row['candidates'], ' '.join(CANDIDATES), 'candidates')
        for candidate in CANDIDATES:
            fields(cluster['candidates'][candidate], 'core quality-stress', 'strata')
            fields(diagnostic['candidates'][candidate], 'core quality-stress', 'diagnostic strata')
            for layer in LAYERS[:2]:
                cell = cluster['candidates'][candidate][layer];detail = diagnostic['candidates'][candidate][layer]
                fields(cell, 'profile_status counts', 'cell');require(cell['profile_status'] in ('calibrated','inconclusive'), 'profile')
                fields(cell['counts'], ' '.join(METRICS), 'metrics');counts = cell['counts']
                for metric, pair in counts.items():
                    require(type(pair) is list and len(pair) == 2 and all(type(n) is int and 0 <= n <= 41472000 for n in pair), 'count pair')
                    require(metric in ('clean_rate','false_alert_burden') or pair[0] <= pair[1], 'bounded ratio')
                    if metric in denominators:same(pair[1], denominators[metric], 'planned denominator')
                detected = counts['machine_recall'][0]+counts['sensor_recall'][0]
                same(counts['precision'][0], detected, 'matched partition')
                same(counts['false_alert_burden'][0], counts['precision'][1]-detected, 'false episode partition')
                require(counts['clean_rate'][0] <= counts['false_alert_burden'][0], 'clean episodes')
                fields(detail, 'effective_clean_seconds detected_delays', 'diagnostic')
                effective = detail['effective_clean_seconds'];delays = detail['detected_delays']
                require(type(effective) is int and 0 <= effective <= 40380, 'effective exposure')
                require(type(delays) is list and len(delays) == detected and all(type(d) is int and 1 <= d <= 5 for d in delays), 'integer detected-only delays')
    return len(value['draws'])


def _ratio(n, d, metric):
    if d == 0:return None
    if metric == 'clean_rate':return (8*n)/(d/3600)
    if metric == 'false_alert_burden':return (100*n)/d
    return n/d


def _quantile(values, percentile):
    ordered = sorted(values);position = (len(ordered)-1)*percentile
    left, right = math.floor(position), math.ceil(position)
    return ordered[left]+(ordered[right]-ordered[left])*(position-left)


def _estimate(fixture, candidate, layer, metric, paired=False):
    parts = LAYERS[:2] if layer == 'overall' else (layer,)
    def sampled(indices, candidate_id):
        # Expand every sampled cluster literally, including repeated indices.
        numerator = denominator = 0
        for i in indices:
            for part in parts:
                pair = fixture['clusters'][i]['candidates'][candidate_id][part]['counts'][metric]
                numerator += pair[0];denominator += pair[1]
        return numerator, denominator, _ratio(numerator, denominator, metric)
    def point(indices):
        value = sampled(indices, candidate)[2]
        if paired:
            control = sampled(indices, CANDIDATES[0])[2]
            return None if value is None or control is None else value-control
        return value
    candidates = (candidate,CANDIDATES[0]) if paired else (candidate,)
    ready = all(c['candidates'][identifier][part]['profile_status'] == 'calibrated'
                for c in fixture['clusters'] for identifier in candidates for part in parts)
    base = point(range(40));replicates = [point(draw) for draw in fixture['draws']]
    nulls = replicates.count(None);complete = ready and base is not None and nulls == 0
    result = {'value':base,'ci_status':'complete' if complete else 'inconclusive',
              'ci_lower':_quantile(replicates,.025) if complete else None,
              'ci_upper':_quantile(replicates,.975) if complete else None,'null_replicates':nulls}
    if not paired:
        n,d,_ = sampled(range(40),candidate);result.update(numerator=n,denominator=d)
    return result


def _gate(metric, layer, estimate, paired):
    if paired:
        limits = ((0.,.25) if metric == 'clean_rate' else (0.,1.) if metric == 'false_alert_burden'
                  else (-.0125,-.0125) if metric.startswith('availability:') else (0.,-.02))
    else:
        index = LAYERS.index(layer)
        limits = ((1.,1.5) if metric == 'clean_rate' else ((.90,.85),(.85,.80),(.875,.825))[index]
                  if metric == 'sensor_recall' else ((.960,.960),(.950,.950),(.955,.955))[index]
                  if metric.startswith('availability:') else (.85,.80))
    status = 'inconclusive'
    if estimate['ci_status'] == 'complete':
        if metric in ('clean_rate','false_alert_burden'):
            passed = estimate['value'] <= limits[0] and estimate['ci_upper'] <= limits[1]
        else:passed = estimate['value'] >= limits[0] and estimate['ci_lower'] >= limits[1]
        status = 'pass' if passed else 'fail'
    availability = metric.startswith('availability:')
    return {'name':'availability' if availability else metric,'full_target':metric.split(':',1)[1] if availability else None,
        'comparison':'paired-control' if paired else 'absolute','point':estimate['value'],
        'lower':estimate['ci_lower'],'upper':estimate['ci_upper'],'ci_status':estimate['ci_status'],
        'null_replicates':estimate['null_replicates'],'status':status}


def _delay(values):
    ordered = sorted(values);n = len(ordered)
    if n:
        median = ordered[n//2] if n%2 else (ordered[n//2-1]+ordered[n//2])/2
        mean = Fraction(sum(ordered),n);mean = mean.numerator if mean.denominator == 1 else float(mean)
    else:median = mean = None
    return {'count':n,'median':median,'mean':mean,'min':ordered[0] if n else None,'max':ordered[-1] if n else None,
            'conditioned_on':'causal-detected-only','undetected_fill':'forbidden','unit':'seconds'}


def success_summary(fixture):
    draws = validate_input(fixture)
    return {'format':'anomaly-v03-fixture-numerical-audit-v1','status':'primary_numerics_matched',
        'algorithm':'literal-index-expanded-counts-v1','fixture_only':True,'fixture_numerical_audit_performed':True,
        'clusters':40,'replicates':draws,'candidate_tables':9,'primary_estimates':117,'paired_estimates':72,'gates':180,
        'input_canonical_sha256':hashlib.sha256(canonical(fixture)).hexdigest(),
        'checked':['counts and ratio-of-sums','literal paired draws and type-7 intervals','zero denominators and profile readiness',
                   'absolute and paired gates','effective exposure and pooled detected delays','qualification and C1-first decision',
                   'packet/document primary-table mapping'],
        'not_checked':['slice and diagnostic-sidecar derivation','coverage/producer observations','registered-data inference',
                       'full source/runtime closure','formal analysis or independent S6'],**CLOSED}


def audit_primary_document(fixture, document):
    """Independently recompute primary numerics; explicit slice exclusion in result."""
    result = success_summary(fixture)
    same(document['format'],'anomaly-v03-document-with-slices-fixture-v1','document identity')
    same(document['input_canonical_sha256'],result['input_canonical_sha256'],'input binding')
    same(document['fixture_draws'],fixture['draws'],'draw binding')
    for key in ('formal_permission','promotion_allowed','independent_s6_complete','registered_data_read','formal_bootstrap_performed','formal_document_emitted','formal_document_validated','result_trusted'):
        same(document[key],False,'closed document '+key)
    same(document['selected_candidate'],None,'outer selection');same(document['performance_status'],'not_evaluated','performance')
    same(document['campaign_evaluations_credited'],0,'campaign credit')
    draft, packet = document['document_draft'],document['fixture_packet']
    same(packet['scope'],'hand-fixture-analysis-tables-only','packet scope')
    for key in ('formal_permission','promotion_allowed','independent_s6_complete','formal_document_emitted'):
        same(packet[key],False,'closed packet '+key)
    same(packet['selected_candidate'],None,'outer packet selection')
    same(packet['performance_status'],'not_evaluated','packet performance')
    for key in ('status','provenance','analysis_consumer','bootstrap'):same(draft[key],None,'formal null '+key)
    same(document['formal_requirements'],{'clusters':40,'replicates':50000,'missing_fields':['status','provenance','analysis_consumer','bootstrap'],'ready':False},'formal requirements')
    tables = []
    for candidate in CANDIDATES:
        for layer in LAYERS:
            parts = LAYERS[:2] if layer == 'overall' else (layer,)
            estimates = {m:_estimate(fixture,candidate,layer,m) for m in METRICS}
            metrics = {m:estimates[m] for m in METRICS[:5]}
            metrics['availability'] = [{'full_target':t,'metric':estimates['availability:'+t]} for t in TARGETS]
            details = [d['candidates'][candidate][part] for d in fixture['diagnostics'] for part in parts]
            effective = sum(d['effective_clean_seconds'] for d in details)
            metrics.update(scheduled_clean_seconds=estimates['clean_rate']['denominator'],effective_clean_seconds=effective,
                effective_clean_rate=_ratio(estimates['clean_rate']['numerator'],effective,'clean_rate'),
                delay_summary=_delay([x for d in details for x in d['detected_delays']]))
            gates = [_gate(m,layer,estimates[m],False) for m in ABSOLUTE]
            if candidate != CANDIDATES[0]:gates += [_gate(m,layer,_estimate(fixture,candidate,layer,m,True),True) for m in PAIRED]
            ready = all(c['candidates'][candidate][part]['profile_status'] == 'calibrated' for c in fixture['clusters'] for part in parts)
            tables.append({'candidate_id':candidate,'stratum':layer,'profile_status':'calibrated' if ready else 'inconclusive',
                           'metrics':metrics,'gates':gates})
    qualified = {}
    control_ready = all(t['profile_status'] == 'calibrated' for t in tables[:3])
    for candidate in CANDIDATES:
        qualified[candidate] = candidate != CANDIDATES[0] and fixture['engineering_ready_assumption'] and control_ready and all(
            g['status'] == 'pass' for t in tables if t['candidate_id'] == candidate for g in t['gates'])
    for table in tables:table['qualified'] = qualified[table['candidate_id']]
    selected = next((c for c in CANDIDATES[1:] if qualified[c]),None)
    decisive = fixture['engineering_ready_assumption'] and all(any(g['status'] == 'fail' for t in tables if t['candidate_id'] == c for g in t['gates']) for c in CANDIDATES[1:])
    decision = 'qualified' if selected else 'no_promotion' if decisive else 'inconclusive'
    same(draft['candidate_tables'],tables,'document primary tables')
    same(packet['fixture_candidate_tables'],tables,'packet primary tables')
    for key,value in (('selected_candidate',selected),('decision',decision)):
        same(draft[key],value,'document '+key);same(packet['fixture_'+key],value,'packet '+key)
    same(packet['fixture_draws'],{'clusters':40,'replicates':result['replicates']},'packet dimensions')
    same(packet['fixture_engineering_ready'],fixture['engineering_ready_assumption'],'packet readiness')
    return result
