"""Independent v0.3 inference arithmetic, stdlib only, no dataset/runtime IO.

This stage verifies fixed draw metadata and computes HAND-FIXTURE inference.
It does not authenticate seed aggregates, certify 12-layout coverage, consume
holdout observations, publish formal analysis, or grant promotion permission.
No producer, registry, analysis helper or shared numerical function is imported.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import math

CANDIDATES = ('c0-diff-control', 'c1-phase-level', 'c2-phase-conditional')
STRATA = ('core', 'quality-stress', 'overall')
TARGETS = tuple(f'{e}.{s}' for e in ('motor-01', 'conveyor-01') for s in
                ('motor_current', 'motor_temperature', 'conveyor_speed', 'vibration_feature'))
AVAILABILITY = tuple('availability:' + t for t in TARGETS)
METRICS = ('machine_recall', 'sensor_recall', 'precision', 'clean_rate', 'false_alert_burden', *AVAILABILITY)
ABSOLUTE_METRICS = ('machine_recall', 'sensor_recall', 'precision', 'clean_rate', *AVAILABILITY)
PAIRED_METRICS = ('machine_recall', 'sensor_recall', 'clean_rate', 'false_alert_burden', *AVAILABILITY)
BOOTSTRAP_DIGEST = 'e375bf3feacb2f04bf5e1d40b141c1cfc5f69fa5437ea2704e323fd7523b22e5'
ABSOLUTE = {layer: {'machine_recall': [.85, .80], 'sensor_recall': sensor,
    'precision': [.85, .80], 'clean_rate': [1., 1.5], 'each_target_availability': availability}
    for layer, sensor, availability in zip(STRATA, ([.90, .85], [.85, .80], [.875, .825]),
                                          ([.960, .960], [.950, .950], [.955, .955]))}
PAIRED = {'machine_recall': [0., -.02], 'sensor_recall': [0., -.02], 'clean_rate': [0., .25],
          'false_alert_burden': [0., 1.], 'each_target_availability': [-.0125, -.0125]}


def need(ok, message):
    if not ok:
        raise ValueError('inference audit: ' + message)


def exact(left, right, message):
    def encoded(value):
        return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
    need(encoded(left) == encoded(right), message)


def draw_index(replicate, position):
    need(type(replicate) is int and 0 <= replicate < 50000, 'replicate index')
    need(type(position) is int and 0 <= position < 40, 'draw position')
    cutoff = 2**256 - 2**256 % 40
    counter = 0
    while True:
        key = f'sha256-counter-rejection-v1:2026090603:{replicate}:{position}:{counter}'.encode('ascii')
        value = int(hashlib.sha256(key).hexdigest(), 16)
        if value < cutoff:
            return value % 40
        counter += 1


def verify_draw_contract(declared):
    """Stream 2M index bytes; no registered observation seed is evaluated."""
    expected = {'algorithm_id': 'sha256-counter-rejection-v1', 'seed': 2026090603,
        'clusters': 40, 'replicates': 50000, 'accepted_indices': 2000000,
        'indices_raw_sha256': BOOTSTRAP_DIGEST, 'sampling': 'paired-seed-clusters-with-replacement',
        'aggregation': 'ratio-of-sums', 'interval': [.025, .975], 'quantile': 'type-7',
        'zero_denominator': 'inconclusive-no-drop-no-redraw'}
    need(type(declared) is dict and set(declared) == set(expected) | {'golden_draws'}, 'bootstrap fields')
    exact({k: declared[k] for k in expected}, expected, 'fixed bootstrap declarations')
    digest, golden = hashlib.sha256(), []
    for replicate in range(50000):
        row = bytes(draw_index(replicate, j) for j in range(40))
        digest.update(row)
        if replicate in (0, 1, 24999, 49999):
            golden.append({'replicate': replicate, 'indices': list(row)})
    need(digest.hexdigest() == BOOTSTRAP_DIGEST, 'independent index digest differs')
    exact(declared['golden_draws'], golden, 'ordered golden draws')
    return {'status': 'draw_contract_checks_passed', 'clusters': 40, 'replicates': 50000,
        'accepted_indices': 2000000, 'indices_raw_sha256': digest.hexdigest(), 'golden_draws': golden,
        'observations_generated': 0, 'formal_permission': False, 'promotion_allowed': False}


def verify_rule_contract(config):
    expected = {'absolute_gates': [{'stratum': layer, **ABSOLUTE[layer]} for layer in STRATA],
        'paired_noninferiority': PAIRED,
        'multiple_testing': {'candidate_alpha': .025, 'candidate_correction': 'Bonferroni-two',
                            'within_candidate': 'intersection-union-all-gates-strata-targets'},
        'selection_order': list(CANDIDATES[1:]), 'fallback': 'no-promotion', 'control_promotable': False,
        'units': {'clean_rate': 'alerts-per-8-equipment-hours',
                  'false_alert_burden': 'false-equipment-episodes-per-100-planned-positive-incidents'}}
    need(type(config) is dict and all(k in config for k in expected), 'missing analysis declarations')
    exact({k: config[k] for k in expected}, expected, 'fixed inference rule declarations')
    return {'status': 'rule_contract_checks_passed', 'absolute_gate_checks': 108, 'paired_gate_checks': 72,
            'candidate_order': list(CANDIDATES[1:]), 'formal_permission': False, 'promotion_allowed': False}


def finite(value):
    need(type(value) in (int, float), 'numeric value required')
    try:
        need(math.isfinite(value), 'nonfinite statistic')
    except OverflowError as exc:
        raise ValueError('inference audit: nonfinite statistic') from exc
    return value


def counts(pair, kind):
    need(kind in METRICS, 'unknown metric')
    need(type(pair) in (tuple, list) and len(pair) == 2, 'numerator/denominator pair')
    need(all(type(v) is int and 0 <= v <= 41472000 for v in pair), 'nonnegative exact integer counts')
    need(kind in ('clean_rate', 'false_alert_burden') or pair[0] <= pair[1], 'ratio numerator exceeds denominator')
    return tuple(pair)


def ratio(numerator, denominator, kind):
    if denominator == 0:
        return None
    # Preserve the frozen count/point arithmetic, including its binary64 order.
    return finite(8*numerator/(denominator/3600) if kind == 'clean_rate' else
                  (100*numerator/denominator if kind == 'false_alert_burden' else numerator/denominator))


def _quantile_sorted(values, p):
    position = (len(values) - 1) * p
    lower = math.floor(position)
    upper = math.ceil(position)
    return finite(values[lower] + (values[upper] - values[lower]) * (position - lower))


def type7(values, p):
    need(type(values) in (list, tuple) and bool(values), 'nonempty quantile sample')
    finite(p)
    need(0 <= p <= 1, 'quantile probability')
    return _quantile_sorted(sorted(finite(x) for x in values), p)


def interval(point, replicates, *, ready=True):
    need(type(ready) is bool, 'exact readiness boolean')
    need(type(replicates) in (list, tuple) and 1 <= len(replicates) <= 50000, 'replicate count')
    if point is not None:
        finite(point)
    nulls = sum(v is None for v in replicates)
    for value in replicates:
        if value is not None:
            finite(value)
    complete = ready and point is not None and nulls == 0
    ordered = sorted(replicates) if complete else None
    return {'value': point, 'ci_status': 'complete' if complete else 'inconclusive',
            'ci_lower': _quantile_sorted(ordered, .025) if complete else None,
            'ci_upper': _quantile_sorted(ordered, .975) if complete else None,
            'null_replicates': nulls}


def draw_weights(draws, cluster_count):
    need(type(cluster_count) is int and 1 <= cluster_count <= 40, 'cluster count')
    need(type(draws) in (list, tuple) and 1 <= len(draws) <= 50000, 'draw row count')
    result = []
    for row in draws:
        need(type(row) in (bytes, list, tuple) and len(row) == cluster_count, 'draw cluster width')
        need(all(type(i) is int and 0 <= i < cluster_count for i in row), 'draw index type/range')
        result.append(tuple(Counter(row).items()))
    return tuple(result)


def _estimate(series, weights, kind, baseline=None, ready=True):
    def total(rows, weight):
        n = sum(rows[i][0] * times for i, times in weight)
        d = sum(rows[i][1] * times for i, times in weight)
        return n, d, ratio(n, d, kind)
    def subtract(left, right):
        return None if left is None or right is None else finite(left - right)
    once = tuple((i, 1) for i in range(len(series)))
    n, d, point = total(series, once)
    if baseline is not None:
        point = subtract(point, total(baseline, once)[2])
    values = []
    for weight in weights:
        value = total(series, weight)[2]
        if baseline is not None:
            value = subtract(value, total(baseline, weight)[2])
        values.append(value)
    result = interval(point, values, ready=ready)
    if baseline is None:
        result.update(numerator=n, denominator=d)
    return result


def estimate_counts(series, draws, kind, *, baseline=None, ready=True):
    """Ratio-of-sums and paired difference using the SAME cluster draws.

    Counts are caller-supplied mathematical inputs, not authenticated campaign data.
    This small primitive accepts reduced fixtures; the fixed contract check above
    always uses 40 clusters and 50,000 draws.
    """
    need(type(series) in (list, tuple), 'count series')
    weights = draw_weights(draws, len(series))
    series = [counts(row, kind) for row in series]
    if baseline is not None:
        need(type(baseline) in (list, tuple) and len(baseline) == len(series), 'paired cluster inventory')
        baseline = [counts(row, kind) for row in baseline]
    return _estimate(series, weights, kind, baseline, ready)


def gate(metric, kind, layer, *, paired=False, ready=True):
    need(kind in (PAIRED_METRICS if paired else ABSOLUTE_METRICS) and layer in STRATA, 'gate identity')
    need(type(paired) is bool and type(ready) is bool, 'exact gate boolean')
    key = 'each_target_availability' if kind in AVAILABILITY else kind
    point_limit, bound_limit = (PAIRED if paired else ABSOLUTE[layer])[key]
    status = 'inconclusive'
    if ready and metric['ci_status'] == 'complete':
        value, lower, upper = (finite(metric[k]) for k in ('value', 'ci_lower', 'ci_upper'))
        need(lower <= upper and metric['null_replicates'] == 0, 'invalid complete interval')
        passed = (value <= point_limit and upper <= bound_limit) if kind in ('clean_rate', 'false_alert_burden') else (value >= point_limit and lower >= bound_limit)
        status = 'pass' if passed else 'fail'
    return {'name': 'availability' if kind in AVAILABILITY else kind,
        'full_target': kind.removeprefix('availability:') if kind in AVAILABILITY else None,
        'comparison': 'paired-control' if paired else 'absolute', 'point': metric['value'],
        'lower': metric['ci_lower'], 'upper': metric['ci_upper'], 'ci_status': metric['ci_status'],
        'null_replicates': metric['null_replicates'], 'status': status}


def _fixture_clusters(clusters):
    need(type(clusters) in (list, tuple) and 1 <= len(clusters) <= 40, 'fixture cluster inventory')
    identifiers = set()
    for cluster in clusters:
        need(type(cluster) is dict and set(cluster) == {'cluster_id', 'candidates'}, 'fixture cluster fields')
        identifier = cluster['cluster_id']
        need(type(identifier) is str and identifier and identifier not in identifiers, 'unique fixture cluster ID')
        identifiers.add(identifier)
        need(type(cluster['candidates']) is dict and set(cluster['candidates']) == set(CANDIDATES), 'three candidates required')
        denominators = {}
        for candidate in CANDIDATES:
            layers = cluster['candidates'][candidate]
            need(type(layers) is dict and set(layers) == set(STRATA[:2]), 'paired core/stress required')
            for layer in STRATA[:2]:
                row = layers[layer]
                need(type(row) is dict and set(row) == {'profile_status', 'counts'}, 'fixture cell fields')
                need(row['profile_status'] in ('calibrated', 'inconclusive'), 'profile state')
                raw = row['counts']
                need(type(raw) is dict and set(raw) == set(METRICS), 'all metrics and eight targets required')
                for name in METRICS:
                    n, d = counts(raw[name], name)
                    if name != 'precision':
                        denominators.setdefault((layer, name), d)
                        need(denominators[layer, name] == d, 'candidate planned denominators differ')
                matched = raw['machine_recall'][0] + raw['sensor_recall'][0]
                need(raw['precision'][0] == matched, 'matched incident/precision partition')
                need(raw['false_alert_burden'][0] == raw['precision'][1] - matched, 'unmatched episode partition')
                need(raw['false_alert_burden'][1] == raw['machine_recall'][1] + raw['sensor_recall'][1], 'planned positive denominator')
                need(raw['clean_rate'][0] <= raw['false_alert_burden'][0], 'clean exceeds all false episodes')


def compute_fixture_tables(clusters, draws, *, engineering_ready):
    """Exercise the complete 3-candidate x 3-stratum gate arithmetic on fixtures.

    A true engineering_ready argument is a TEST ASSUMPTION, not run evidence.
    Actual permission/selection/performance fields remain closed. The input is
    deliberately not the formal analysis schema or a saved-result IO adapter.
    """
    _fixture_clusters(clusters)
    need(type(engineering_ready) is bool, 'exact engineering readiness')
    weights = draw_weights(draws, len(clusters))
    series, ready = {}, {}
    for candidate in CANDIDATES:
        for layer in STRATA:
            parts = STRATA[:2] if layer == 'overall' else (layer,)
            cells = [[cluster['candidates'][candidate][s] for s in parts] for cluster in clusters]
            ready[candidate, layer] = all(cell['profile_status'] == 'calibrated' for group in cells for cell in group)
            for name in METRICS:
                series[candidate, layer, name] = [tuple(sum(cell['counts'][name][k] for cell in group) for k in (0, 1)) for group in cells]
    tables = []
    for candidate in CANDIDATES:
        for layer in STRATA:
            calibrated = ready[candidate, layer]
            metrics = {name: _estimate(series[candidate, layer, name], weights, name, ready=calibrated) for name in METRICS}
            gates = [gate(metrics[name], name, layer, ready=calibrated) for name in ABSOLUTE_METRICS]
            paired = {}
            if candidate != CANDIDATES[0]:
                for name in PAIRED_METRICS:
                    paired[name] = _estimate(series[candidate, layer, name], weights, name,
                        baseline=series[CANDIDATES[0], layer, name], ready=calibrated and ready[CANDIDATES[0], layer])
                    gates.append(gate(paired[name], name, layer, paired=True,
                                      ready=calibrated and ready[CANDIDATES[0], layer]))
            tables.append({'candidate_id': candidate, 'stratum': layer,
                'profile_status': 'calibrated' if calibrated else 'inconclusive',
                'metrics': metrics, 'paired_control': paired, 'gates': gates})
    qualified = {candidate: candidate != CANDIDATES[0] and engineering_ready and
        all(ready[CANDIDATES[0], layer] for layer in STRATA) and
        all(g['status'] == 'pass' for table in tables if table['candidate_id'] == candidate for g in table['gates'])
        for candidate in CANDIDATES}
    for table in tables:
        table['fixture_qualified'] = qualified[table['candidate_id']]
    selected = next((candidate for candidate in CANDIDATES[1:] if qualified[candidate]), None)
    decisive = engineering_ready and all(any(g['status'] == 'fail' for t in tables
        if t['candidate_id'] == candidate for g in t['gates']) for candidate in CANDIDATES[1:])
    return {'scope': 'hand-fixture-inference-only', 'cluster_count': len(clusters), 'replicate_count': len(weights),
        'candidate_tables': tables, 'fixture_engineering_ready': engineering_ready,
        'fixture_selected_candidate': selected,
        'fixture_decision': 'qualified' if selected else ('no_promotion' if decisive else 'inconclusive'),
        'selected_candidate': None, 'formal_permission': False, 'promotion_allowed': False,
        'independent_s6_complete': False, 'performance_status': 'not_evaluated',
        'campaign_evaluations_credited': 0}
