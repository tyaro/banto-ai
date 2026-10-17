"""Independent arithmetic for a bounded, invented 50,000-draw budget probe.

This module does not import the producer's inference or draw implementation.
It consumes an invented count fixture and an untrusted calculation report, and
never reads a registered campaign root or asserts formal S6 completion.
"""
from __future__ import annotations

import hashlib
import json
import math

FORMAT = 'anomaly-v03-preformal-draw-budget-audit-v1'
DRAW_SHA256 = 'e375bf3feacb2f04bf5e1d40b141c1cfc5f69fa5437ea2704e323fd7523b22e5'
REPLICATES = 50000
CLUSTERS = 40
CANDIDATES = ('c0-diff-control', 'c1-phase-level', 'c2-phase-conditional')
LAYERS = ('core', 'quality-stress', 'overall')
TARGETS = tuple(e+'.'+s for e in ('motor-01', 'conveyor-01') for s in
                ('motor_current', 'motor_temperature', 'conveyor_speed', 'vibration_feature'))
METRICS = ('machine_recall', 'sensor_recall', 'precision', 'clean_rate', 'false_alert_burden',
           *('availability:'+target for target in TARGETS))
ABSOLUTE = tuple(metric for metric in METRICS if metric != 'false_alert_burden')
PAIRED = tuple(metric for metric in METRICS if metric != 'precision')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def _ratio(numerator, denominator, metric):
    if denominator == 0:
        return None
    if metric == 'clean_rate':
        return 8*numerator/(denominator/3600)
    if metric == 'false_alert_burden':
        return 100*numerator/denominator
    return numerator/denominator


def _quantile(values, probability):
    ordered = sorted(values)
    index = (len(ordered)-1)*probability
    low, high = math.floor(index), math.ceil(index)
    return ordered[low]+(ordered[high]-ordered[low])*(index-low)


def _estimate(clusters, draws, candidate, layer, metric, *, paired=False):
    parts = LAYERS[:2] if layer == 'overall' else (layer,)
    identities = (candidate, CANDIDATES[0]) if paired else (candidate,)
    ready = all(cluster['candidates'][name][part]['profile_status'] == 'calibrated'
                for cluster in clusters for name in identities for part in parts)

    def sample(indices, name):
        numerator = denominator = 0
        for index in indices:
            for part in parts:
                n, d = clusters[index]['candidates'][name][part]['counts'][metric]
                numerator += n
                denominator += d
        return numerator, denominator, _ratio(numerator, denominator, metric)

    def value(indices):
        result = sample(indices, candidate)[2]
        if paired:
            baseline = sample(indices, CANDIDATES[0])[2]
            return None if result is None or baseline is None else result-baseline
        return result

    numerator, denominator, _ = sample(range(CLUSTERS), candidate)
    point = value(range(CLUSTERS))
    replicates = [value(row) for row in draws]
    nulls = replicates.count(None)
    complete = ready and point is not None and nulls == 0
    result = {'value': point, 'ci_status': 'complete' if complete else 'inconclusive',
              'ci_lower': _quantile(replicates, .025) if complete else None,
              'ci_upper': _quantile(replicates, .975) if complete else None,
              'null_replicates': nulls}
    if not paired:
        result.update(numerator=numerator, denominator=denominator)
    return result


def _gate(metric, layer, estimate, paired):
    if paired:
        limits = ((0., .25) if metric == 'clean_rate' else (0., 1.) if metric == 'false_alert_burden'
                  else (-.0125, -.0125) if metric.startswith('availability:') else (0., -.02))
    else:
        layer_index = LAYERS.index(layer)
        limits = ((1., 1.5) if metric == 'clean_rate' else
                  ((.90, .85), (.85, .80), (.875, .825))[layer_index] if metric == 'sensor_recall' else
                  ((.960, .960), (.950, .950), (.955, .955))[layer_index]
                  if metric.startswith('availability:') else (.85, .80))
    status = 'inconclusive'
    if estimate['ci_status'] == 'complete':
        if metric in ('clean_rate', 'false_alert_burden'):
            passed = estimate['value'] <= limits[0] and estimate['ci_upper'] <= limits[1]
        else:
            passed = estimate['value'] >= limits[0] and estimate['ci_lower'] >= limits[1]
        status = 'pass' if passed else 'fail'
    availability = metric.startswith('availability:')
    return {'name': 'availability' if availability else metric,
            'full_target': metric.split(':', 1)[1] if availability else None,
            'comparison': 'paired-control' if paired else 'absolute',
            'point': estimate['value'], 'lower': estimate['ci_lower'],
            'upper': estimate['ci_upper'], 'ci_status': estimate['ci_status'],
            'null_replicates': estimate['null_replicates'], 'status': status}


def independent_draws():
    """Regenerate all registered-index bytes with an independent formulation."""
    digest = hashlib.sha256()
    rows = []
    rejection_ceiling = (1 << 256) - ((1 << 256) % CLUSTERS)
    for replicate in range(REPLICATES):
        row = bytearray()
        for position in range(CLUSTERS):
            counter = 0
            while True:
                key = f'sha256-counter-rejection-v1:2026090603:{replicate}:{position}:{counter}'
                candidate = int(hashlib.sha256(key.encode('ascii')).hexdigest(), 16)
                if candidate < rejection_ceiling:
                    row.append(candidate % CLUSTERS)
                    break
                counter += 1
        digest.update(row)
        rows.append(bytes(row))
    if digest.hexdigest() != DRAW_SHA256:
        raise ValueError('independent draw digest differs')
    return rows, digest.hexdigest()


def _expected_tables(clusters, draws):
    tables = []
    for candidate in CANDIDATES:
        for layer in LAYERS:
            parts = LAYERS[:2] if layer == 'overall' else (layer,)
            statuses = (cluster['candidates'][candidate][part]['profile_status']
                        for cluster in clusters for part in parts)
            calibrated = True
            for status in statuses:
                if status not in ('calibrated', 'inconclusive'):
                    raise ValueError('independent profile state differs')
                calibrated = calibrated and status == 'calibrated'
            metrics = {name: _estimate(clusters, draws, candidate, layer, name)
                       for name in METRICS}
            paired = ({name: _estimate(clusters, draws, candidate, layer, name, paired=True)
                       for name in PAIRED}
                      if candidate != CANDIDATES[0] else {})
            gates = [_gate(name, layer, metrics[name], False) for name in ABSOLUTE]
            gates += [_gate(name, layer, paired[name], True) for name in PAIRED] if paired else []
            tables.append({'candidate_id': candidate, 'stratum': layer,
                           'profile_status': 'calibrated' if calibrated else 'inconclusive',
                           'metrics': metrics,
                           'paired_control': paired, 'gates': gates,
                           'fixture_qualified': False})
    return tables


def audit(clusters, calculation, draws):
    """Compare all reported primary intervals/gates, not a reduced sample."""
    if type(clusters) is not list or len(clusters) != CLUSTERS:
        raise ValueError('exactly forty invented clusters required')
    if type(draws) is not list or len(draws) != REPLICATES or any(
            type(row) is not bytes or len(row) != CLUSTERS for row in draws):
        raise ValueError('exactly 50,000 complete draw rows required')
    expected_fields = {'scope', 'cluster_count', 'replicate_count', 'candidate_tables',
                       'fixture_engineering_ready', 'fixture_selected_candidate',
                       'fixture_decision', 'selected_candidate', 'formal_permission',
                       'promotion_allowed', 'independent_s6_complete',
                       'performance_status', 'campaign_evaluations_credited'}
    if type(calculation) is not dict or set(calculation) != expected_fields or calculation.get('scope') != 'hand-fixture-inference-only':
        raise ValueError('calculation scope differs')
    if calculation.get('cluster_count') != CLUSTERS or calculation.get('replicate_count') != REPLICATES:
        raise ValueError('calculation dimensions differ')
    expected = _expected_tables(clusters, draws)
    if canonical(calculation.get('candidate_tables')) != canonical(expected):
        raise ValueError('independent 50,000-draw primary tables differ')
    for key, value in {'fixture_engineering_ready': False,
                       'fixture_selected_candidate': None,
                       'fixture_decision': 'inconclusive',
                       'selected_candidate': None,
                       'formal_permission': False,
                       'promotion_allowed': False,
                       'independent_s6_complete': False,
                       'performance_status': 'not_evaluated',
                       'campaign_evaluations_credited': 0}.items():
        if type(calculation.get(key)) is not type(value) or calculation[key] != value:
            raise ValueError('calculation closed claim differs: '+key)
    return {'format': FORMAT, 'status': 'invented_primary_numerics_matched',
            'draw_sha256': DRAW_SHA256, 'clusters': CLUSTERS,
            'replicates': REPLICATES, 'candidate_tables': 9,
            'primary_estimates': 117, 'paired_estimates': 72, 'gates': 180,
            'calculation_sha256': hashlib.sha256(canonical(calculation)).hexdigest(),
            'registered_data_read': False, 'formal_bootstrap_performed': False,
            'independent_s6_complete': False, 'formal_permission': False,
            'promotion_allowed': False, 'performance_status': 'not_evaluated'}
