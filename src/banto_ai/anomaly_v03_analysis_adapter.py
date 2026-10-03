"""Fixture-only bridge from independent inference to frozen analysis table shape.

This deliberately emits a fixture packet, NOT a formal analysis document. Actual
draw dimensions are retained; missing source/runtime/slice evidence is never
filled with invented formal metadata. No filesystem or observation IO occurs.
"""
from __future__ import annotations

import copy
import statistics

from . import anomaly_v03 as contract
from . import anomaly_v03_inference_audit as inference
from . import _anomaly_v03_contract as frozen


def _delay(values):
    return {'count': len(values), 'median': statistics.median(values) if values else None,
            'mean': statistics.mean(values) if values else None,
            'min': min(values) if values else None, 'max': max(values) if values else None,
            'conditioned_on': 'causal-detected-only', 'undetected_fill': 'forbidden', 'unit': 'seconds'}


def _diagnostics(clusters, diagnostics):
    inference.need(type(diagnostics) is list and len(diagnostics) == len(clusters), 'fixture diagnostics coverage')
    for cluster, diagnostic in zip(clusters, diagnostics):
        inference.need(type(diagnostic) is dict and set(diagnostic) == {'cluster_id', 'candidates'}, 'diagnostic fields')
        inference.exact(diagnostic['cluster_id'], cluster['cluster_id'], 'diagnostic cluster order')
        inference.exact(sorted(diagnostic['candidates']), sorted(inference.CANDIDATES), 'diagnostic candidate coverage')
        for candidate in inference.CANDIDATES:
            layers = diagnostic['candidates'][candidate]
            inference.exact(sorted(layers), sorted(inference.STRATA[:2]), 'diagnostic stratum coverage')
            for layer in inference.STRATA[:2]:
                cell, raw = layers[layer], cluster['candidates'][candidate][layer]['counts']
                inference.need(type(cell) is dict and set(cell) == {'effective_clean_seconds', 'detected_delays'}, 'diagnostic cell fields')
                effective, delays = cell['effective_clean_seconds'], cell['detected_delays']
                inference.need(type(effective) is int and 0 <= effective <= raw['clean_rate'][1], 'effective exposure bounds')
                detected = raw['machine_recall'][0] + raw['sensor_recall'][0]
                inference.need(type(delays) is list and len(delays) == detected, 'detected-only delay inventory')
                for delay in delays:
                    inference.need(1 <= inference.finite(delay) < 6, 'detected delay range')


def _shape_member(value, schema, name):
    contract._shape(value, {**schema['properties'][name], '$defs': schema['$defs']})


def _metric(row, kind):
    if kind.startswith('availability:'):
        return next(v['metric'] for v in row['availability'] if v['full_target'] == kind.split(':', 1)[1])
    return row[kind]


def validate_fixture_packet(packet, schema):
    """Check frozen table shape and reported metrics at the stated FIXTURE size.

    Full validate_result_contract is intentionally inapplicable: its fixed
    40-cluster/50,000-draw declaration must not describe a small hand fixture.
    This shares S1 shape and count/delay checks, not producer computations.
    """
    inference.exact(packet['scope'], 'hand-fixture-analysis-tables-only', 'fixture packet scope')
    for name, expected in {'formal_permission': False, 'promotion_allowed': False,
            'independent_s6_complete': False, 'performance_status': 'not_evaluated',
            'selected_candidate': None, 'formal_document_emitted': False}.items():
        inference.exact(packet[name], expected, 'fixture boundary: '+name)
    tables = packet['fixture_candidate_tables']
    _shape_member(tables, schema, 'candidate_tables')
    _shape_member(packet['fixture_selected_candidate'], schema, 'selected_candidate')
    _shape_member(packet['fixture_decision'], schema, 'decision')
    inference.exact([(t['candidate_id'], t['stratum']) for t in tables],
                    [(c, s) for c in inference.CANDIDATES for s in inference.STRATA], 'ordered nine tables')
    indexed = {(t['candidate_id'], t['stratum']): t for t in tables}
    replicate_count = packet['fixture_draws']['replicates']
    cluster_count = packet['fixture_draws']['clusters']
    inference.need(type(cluster_count) is int and 1 <= cluster_count <= 40, 'fixture clusters')
    inference.need(type(replicate_count) is int and 1 <= replicate_count <= 50000, 'fixture replicates')
    inference.need(type(packet['fixture_engineering_ready']) is bool, 'fixture engineering assumption')
    for table in tables:
        candidate, layer, metrics = table['candidate_id'], table['stratum'], table['metrics']
        inference.need(metrics is not None, 'computed fixture metrics required')
        inference.need(table['profile_status'] in ('calibrated', 'inconclusive'), 'computed profile status required')
        datasets = cluster_count * 12 * (2 if layer == 'overall' else 1)
        contract._reported_metrics(metrics, datasets=datasets)
        control = indexed[inference.CANDIDATES[0], layer]
        expected = [('absolute', k) for k in inference.ABSOLUTE_METRICS]
        if candidate != inference.CANDIDATES[0]:
            expected += [('paired-control', k) for k in inference.PAIRED_METRICS]
        inference.exact([(g['comparison'], 'availability:'+g['full_target'] if g['full_target'] else g['name'])
                         for g in table['gates']], expected, 'gate inventory')
        for kind in inference.METRICS:
            primary = _metric(metrics, kind)
            inference.counts([primary['numerator'], primary['denominator']], kind)
            inference.need(type(primary['null_replicates']) is int and 0 <= primary['null_replicates'] <= replicate_count, 'fixture null count exceeds draws')
            inference.need(primary['ci_status'] in ('complete', 'inconclusive'), 'computed fixture CI status required')
            if table['profile_status'] == 'inconclusive':
                inference.exact(primary['ci_status'], 'inconclusive', 'profile unavailable for primary CI')
        for gate, (comparison, kind) in zip(table['gates'], expected):
            primary = _metric(metrics, kind)
            ready = table['profile_status'] == 'calibrated'
            if comparison == 'absolute':
                inference.exact(gate, inference.gate(primary, kind, layer, ready=ready), 'mapped absolute gate')
            else:
                baseline = _metric(control['metrics'], kind)
                ready = ready and control['profile_status'] == 'calibrated' and primary['ci_status'] == baseline['ci_status'] == 'complete'
                delta = None if primary['value'] is None or baseline['value'] is None else primary['value']-baseline['value']
                inference.exact(gate['point'], delta, 'mapped paired point')
                contract._reported_ci(delta, gate['lower'], gate['upper'], gate['ci_status'], gate['null_replicates'],
                                     domain=(-1, 1) if kind not in ('clean_rate', 'false_alert_burden') else None)
                inference.need(type(gate['null_replicates']) is int and 0 <= gate['null_replicates'] <= replicate_count, 'paired null count exceeds draws')
                inference.need(gate['ci_status'] in ('complete', 'inconclusive'), 'computed paired CI required')
                if not ready:
                    inference.exact(gate['ci_status'], 'inconclusive', 'paired profile unavailable')
                mapped = {'value': delta, 'ci_lower': gate['lower'], 'ci_upper': gate['upper'],
                          'ci_status': gate['ci_status'], 'null_replicates': gate['null_replicates']}
                inference.exact(gate, inference.gate(mapped, kind, layer, paired=True, ready=ready), 'mapped paired gate')
    for candidate in inference.CANDIDATES:
        core, stress, overall = [indexed[candidate, s]['metrics'] for s in inference.STRATA]
        for kind in inference.METRICS:
            for count in ('numerator', 'denominator'):
                inference.exact(_metric(overall, kind)[count], _metric(core, kind)[count]+_metric(stress, kind)[count], 'overall raw counts')
        inference.exact(overall['effective_clean_seconds'], core['effective_clean_seconds']+stress['effective_clean_seconds'], 'overall effective exposure')
    qualified = {candidate: candidate != inference.CANDIDATES[0] and packet['fixture_engineering_ready']
        and all(indexed[inference.CANDIDATES[0], s]['profile_status'] == 'calibrated' for s in inference.STRATA)
        and all(t['profile_status'] == 'calibrated' and all(g['status'] == 'pass' for g in t['gates'])
                for t in tables if t['candidate_id'] == candidate) for candidate in inference.CANDIDATES}
    for table in tables:
        inference.exact(table['qualified'], qualified[table['candidate_id']], 'fixture qualification')
    selected = next((c for c in inference.CANDIDATES[1:] if qualified[c]), None)
    decisive = packet['fixture_engineering_ready'] and all(any(g['status'] == 'fail' for t in tables
        if t['candidate_id'] == c for g in t['gates']) for c in inference.CANDIDATES[1:])
    inference.exact(packet['fixture_selected_candidate'], selected, 'fixture C1-first selection')
    inference.exact(packet['fixture_decision'], 'qualified' if selected else ('no_promotion' if decisive else 'inconclusive'), 'fixture decision')
    return {'status': 'fixture_table_contract_valid', 'tables': 9, 'gates': 180,
            'formal_document_validated': False, 'source_runtime_slices_validated': False}


def _twelve_layout_inputs(clusters, diagnostics):
    """Check the count and diagnostic input shared by both fixture mappers."""
    inference._fixture_clusters(clusters)
    _diagnostics(clusters, diagnostics)
    for cluster in clusters:
        for candidate in inference.CANDIDATES:
            for layer in inference.STRATA[:2]:
                raw = cluster['candidates'][candidate][layer]['counts']
                for kind, d in {'machine_recall': 120, 'sensor_recall': 120, 'clean_rate': 40380,
                               'false_alert_burden': 240, **dict.fromkeys(inference.AVAILABILITY, 21600)}.items():
                    inference.exact(raw[kind][1], d, 'fixture twelve-layout denominator')


def _packet_from_result(clusters, diagnostics, schema, result, *, engineering_ready):
    """Map already computed primary tables; no draw or interval computation."""
    tables = []
    for row in result['candidate_tables']:
        candidate, layer = row['candidate_id'], row['stratum']
        parts = inference.STRATA[:2] if layer == 'overall' else (layer,)
        cells = [c['candidates'][candidate][s] for c in diagnostics for s in parts]
        raw = row['metrics']
        metrics = {kind: copy.deepcopy(raw[kind]) for kind in inference.METRICS[:5]}
        metrics['availability'] = [{'full_target': target, 'metric': copy.deepcopy(raw[kind])}
                                   for target, kind in zip(inference.TARGETS, inference.AVAILABILITY)]
        effective = sum(c['effective_clean_seconds'] for c in cells)
        metrics.update(scheduled_clean_seconds=raw['clean_rate']['denominator'], effective_clean_seconds=effective,
            effective_clean_rate=inference.ratio(raw['clean_rate']['numerator'], effective, 'clean_rate'),
            delay_summary=_delay([d for cell in cells for d in cell['detected_delays']]))
        tables.append({'candidate_id': candidate, 'stratum': layer, 'profile_status': row['profile_status'],
                       'metrics': metrics, 'gates': copy.deepcopy(row['gates']), 'qualified': row['fixture_qualified']})
    packet = {'scope': 'hand-fixture-analysis-tables-only', 'fixture_candidate_tables': tables,
        'fixture_selected_candidate': result['fixture_selected_candidate'], 'fixture_decision': result['fixture_decision'],
        'fixture_engineering_ready': engineering_ready,
        'fixture_draws': {'clusters': len(clusters), 'replicates': result['replicate_count']},
        'selected_candidate': None, 'performance_status': 'not_evaluated', 'formal_permission': False,
        'promotion_allowed': False, 'independent_s6_complete': False, 'formal_document_emitted': False,
        'not_validated': ['registered holdout observations', 'formal bootstrap execution',
                          'source/runtime/publication evidence', 'slice inventory and derivation']}
    packet['validation'] = validate_fixture_packet(packet, schema)
    return packet


def compute_fixture_packet(clusters, draws, diagnostics, schema, *, engineering_ready):
    """Compute invented 12-layout cluster fixtures and map nine result tables.

    diagnostics must supply every detected delay and effective exposure per cell.
    Missing diagnostics are errors; medians are recomputed from the union of
    delays, never averaged across clusters or strata. Input data is not mutated.
    """
    _twelve_layout_inputs(clusters, diagnostics)
    result = inference.compute_fixture_tables(clusters, draws, engineering_ready=engineering_ready)
    return _packet_from_result(clusters, diagnostics, schema, result,
                               engineering_ready=engineering_ready)


def map_precomputed_fixture_packet(clusters, diagnostics, schema, calculation, *, draw_sha256):
    """Map a separately audited invented 40/50,000 primary calculation.

    The caller must authenticate the saved calculation, its exact cluster input,
    and an independent arithmetic audit with raw pins. This pure function checks
    their semantic mapping but does not regenerate draws, intervals, or an S6
    result. Its output retains the fixture-only permission and selection fields.
    """
    inference.need(type(draw_sha256) is str and draw_sha256 == frozen.BOOTSTRAP_HASH,
                   'frozen invented draw digest')
    inference.exact(schema, contract.schemas(contract._expected_configs())[7],
                    'frozen precomputed analysis schema')
    inference.need(type(clusters) is list and len(clusters) == 40,
                   'precomputed forty invented clusters')
    _twelve_layout_inputs(clusters, diagnostics)
    inference.need(all(cluster['cluster_id'] == f'invented-{index:02d}'
                       for index, cluster in enumerate(clusters)),
                   'ordered invented cluster IDs')
    required = {'scope', 'cluster_count', 'replicate_count', 'candidate_tables',
                'fixture_engineering_ready', 'fixture_selected_candidate',
                'fixture_decision', 'selected_candidate', 'formal_permission',
                'promotion_allowed', 'independent_s6_complete',
                'performance_status', 'campaign_evaluations_credited'}
    inference.need(type(calculation) is dict and set(calculation) == required,
                   'precomputed calculation fields')
    expected = {'scope': 'hand-fixture-inference-only', 'cluster_count': 40,
                'replicate_count': 50000, 'fixture_engineering_ready': False,
                'fixture_selected_candidate': None, 'fixture_decision': 'inconclusive',
                'selected_candidate': None, 'formal_permission': False,
                'promotion_allowed': False, 'independent_s6_complete': False,
                'performance_status': 'not_evaluated', 'campaign_evaluations_credited': 0}
    for name, value in expected.items():
        inference.need(type(calculation[name]) is type(value) and calculation[name] == value,
                       'precomputed calculation ' + name)
    source_tables = calculation['candidate_tables']
    inference.need(type(source_tables) is list and len(source_tables) == 9,
                   'precomputed nine table inventory')
    inference.exact([(row.get('candidate_id'), row.get('stratum'))
                     for row in source_tables if type(row) is dict],
                    [(candidate, layer) for candidate in inference.CANDIDATES
                     for layer in inference.STRATA], 'ordered precomputed tables')
    indexed = {(row['candidate_id'], row['stratum']): row for row in source_tables}
    for row in source_tables:
        inference.need(set(row) == {'candidate_id', 'stratum', 'profile_status',
                                    'metrics', 'paired_control', 'gates',
                                    'fixture_qualified'}, 'precomputed table fields')
        candidate, layer = row['candidate_id'], row['stratum']
        parts = inference.STRATA[:2] if layer == 'overall' else (layer,)
        ready = all(cluster['candidates'][candidate][part]['profile_status'] == 'calibrated'
                    for cluster in clusters for part in parts)
        inference.exact(row['profile_status'], 'calibrated' if ready else 'inconclusive',
                        'precomputed profile status')
        inference.need(row['fixture_qualified'] is False, 'precomputed qualification closed')
        inference.need(type(row['metrics']) is dict and set(row['metrics']) == set(inference.METRICS),
                       'precomputed metric inventory')
        for kind in inference.METRICS:
            metric = row['metrics'][kind]
            inference.need(type(metric) is dict and set(metric) ==
                           {'numerator', 'denominator', 'value', 'ci_status',
                            'ci_lower', 'ci_upper', 'null_replicates'},
                           'precomputed metric fields')
            numerator = sum(cluster['candidates'][candidate][part]['counts'][kind][0]
                            for cluster in clusters for part in parts)
            denominator = sum(cluster['candidates'][candidate][part]['counts'][kind][1]
                              for cluster in clusters for part in parts)
            inference.exact((metric['numerator'], metric['denominator']),
                            (numerator, denominator), 'precomputed input count binding')
            inference.exact(metric['value'], inference.ratio(numerator, denominator, kind),
                            'precomputed input point binding')
        expected_paired = set(inference.PAIRED_METRICS) if candidate != inference.CANDIDATES[0] else set()
        inference.need(type(row['paired_control']) is dict and
                       set(row['paired_control']) == expected_paired,
                       'precomputed paired metric inventory')
        gates = [inference.gate(row['metrics'][kind], kind, layer, ready=ready)
                 for kind in inference.ABSOLUTE_METRICS]
        for kind in inference.PAIRED_METRICS if candidate != inference.CANDIDATES[0] else ():
            paired = row['paired_control'][kind]
            inference.need(type(paired) is dict and set(paired) ==
                           {'value', 'ci_status', 'ci_lower', 'ci_upper', 'null_replicates'},
                           'precomputed paired metric fields')
            baseline = indexed[inference.CANDIDATES[0], layer]['metrics'][kind]
            point = row['metrics'][kind]['value']
            inference.exact(paired['value'], None if point is None or baseline['value'] is None
                            else point - baseline['value'], 'precomputed paired point binding')
            control_ready = all(cluster['candidates'][inference.CANDIDATES[0]][part][
                                    'profile_status'] == 'calibrated'
                                for cluster in clusters for part in parts)
            gates.append(inference.gate(paired, kind, layer, paired=True,
                                        ready=ready and control_ready))
        inference.exact(row['gates'], gates, 'precomputed gate binding')
    return _packet_from_result(clusters, diagnostics, schema, calculation,
                               engineering_ready=False)
