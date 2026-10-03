"""Independent bounded invented-count audit, with literal delay multisets.

Stdlib only: no calculation-side grouping, mapping or validation calls. This
checks supplied count partitions and their document mapping, not raw observations.
"""
import hashlib
import json

CANDIDATES = ('c0-diff-control', 'c1-phase-level', 'c2-phase-conditional')
LAYERS = ('core', 'quality-stress', 'overall')
EQUIPMENT = ('motor-01', 'conveyor-01')
MODES = ('stopped', 'startup', 'low_speed', 'nominal', 'high_load', 'cooldown')
TARGETS = tuple(e+'.'+s for e in EQUIPMENT for s in
                ('motor_current', 'motor_temperature', 'conveyor_speed', 'vibration_feature'))
INCIDENT = {'class': ('machine', 'sensor'), 'equipment': EQUIPMENT, 'mode': MODES,
    'class-equipment-mode': tuple(c+'.'+e+'.'+m for c in ('machine', 'sensor') for e in EQUIPMENT for m in MODES),
    'test-cycle': tuple(map(str, range(10))), 'event-start-phase': ('0', '7', '14', '21')}
SCORE = {'full-target': TARGETS, 'signal-mode': tuple(t+'.'+m for t in TARGETS for m in MODES),
    'phase': ('0', '1', '2', '3', '4..6', '7..13', '14..20', '21..29'),
    'event-offset': ('minus-2', 'minus-1', '0', '1', '2', '3', '4', '5'),
    'context': ('raw-event', 'grace', 'clean'),
    'quality-current': ('ok', 'missing', 'stale', 'invalid', 'absent'),
    'quality-previous': ('ok', 'missing', 'stale', 'invalid', 'absent'),
    'fault-quality-overlap': ('no', 'yes'), 'profile-status': ('calibrated', 'inconclusive')}
SCORE_FIELDS = ('planned', 'observed', 'available', 'threshold_exceeded', 'signal_onsets', 'unscored_target', 'outside_test')
SERIES = {'incident-recall': 'detected', 'score-availability': 'available',
          'score-threshold-exceedance': 'threshold_exceeded', 'score-signal-onset': 'signal_onsets'}


def require(ok, reason):
    if not ok: raise ValueError('fixture slice audit: '+reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')


def same(actual, expected, reason):
    require(canonical(actual) == canonical(expected), reason+' differs')


def fields(value, names, reason):
    require(type(value) is dict and set(value) == set(names), reason+' fields')


def integer(value, maximum, reason):
    require(type(value) is int and 0 <= value <= maximum, reason+' integer range')


def histogram(value, maximum):
    require(type(value) is list and len(value) == 5, 'five-bin histogram')
    for amount in value: integer(amount, maximum, 'histogram')
    require(sum(value) <= maximum, 'histogram total')


def delay_summary(hist):
    # Expand the bounded multiset, unlike the producer's cumulative-bin lookup.
    histogram(hist, 19200)
    values = [float(second) for second, amount in enumerate(hist, 1) for _ in range(amount)]
    count = len(values)
    return {'count': count, 'median': (values[(count-1)//2]+values[count//2])/2 if count else None,
        'mean': sum(values)/count if count else None, 'min': values[0] if count else None,
        'max': values[-1] if count else None, 'conditioned_on': 'causal-detected-only',
        'undetected_fill': 'forbidden', 'unit': 'seconds'}


def _sum_incident(cells):
    cells = list(cells)
    return {'planned': sum(c['planned'] for c in cells), 'detected': sum(c['detected'] for c in cells),
            'delay_histogram': [sum(c['delay_histogram'][i] for c in cells) for i in range(5)]}


def _sum_scores(cells):
    cells = list(cells)
    return {field: sum(c[field] for c in cells) for field in SCORE_FIELDS}


def validate_raw(raw):
    fields(raw, ('incident_slices', 'score_slices', 'equipment_context', 'delay_histogram',
                 'evaluations', 'profile_inconclusive_evaluations'), 'raw table')
    same(raw['evaluations'], 12, 'twelve layouts')
    integer(raw['profile_inconclusive_evaluations'], 12, 'profile count')
    histogram(raw['delay_histogram'], 240)
    for group, inventory in (('incident_slices', INCIDENT), ('score_slices', SCORE)):
        fields(raw[group], inventory, group)
        for dimension, keys in inventory.items():
            cells = raw[group][dimension];fields(cells, keys, dimension)
            for cell in cells.values():
                if group == 'incident_slices':
                    fields(cell, ('planned', 'detected', 'delay_histogram'), 'incident cell')
                    for name in ('planned', 'detected'): integer(cell[name], 240, name)
                    histogram(cell['delay_histogram'], 240)
                    require(sum(cell['delay_histogram']) == cell['detected'] <= cell['planned'], 'incident detection/histogram')
                else:
                    fields(cell, SCORE_FIELDS, 'score cell')
                    for name in SCORE_FIELDS: integer(cell[name], 172800, name)
                    require(cell['signal_onsets'] <= cell['threshold_exceeded'] <= cell['available'] <= cell['observed'], 'score decision subsets')
                    same(cell['planned'], cell['observed']+cell['unscored_target']+cell['outside_test'], 'reference omissions')
                    if dimension == 'event-offset':
                        same([cell['planned'], cell['unscored_target']], [480, 120], 'offset planned/unscored')
                    else: same([cell['unscored_target'], cell['outside_test']], [0, 0], 'partition omissions')
            if group == 'incident_slices':
                same(_sum_incident(cells.values()), {'planned': 240, 'detected': sum(raw['delay_histogram']),
                     'delay_histogram': raw['delay_histogram']}, 'incident partition')
            elif dimension != 'event-offset':
                total = _sum_scores(cells.values());same(total['planned'], 172800, 'score partition exposure')
                baseline = _sum_scores(raw[group]['full-target'].values())
                for name in ('available', 'threshold_exceeded', 'signal_onsets'):
                    same(total[name], baseline[name], 'score partition decisions')
    incident = raw['incident_slices'];joint = incident['class-equipment-mode']
    for dimension, position in (('class', 0), ('equipment', 1), ('mode', 2)):
        for key, cell in incident[dimension].items():
            same(cell, _sum_incident(v for k, v in joint.items() if k.split('.')[position] == key), 'joint/marginal '+dimension)
    score = raw['score_slices']
    for target in TARGETS:
        same(score['full-target'][target], _sum_scores(score['signal-mode'][target+'.'+m] for m in MODES), 'target/mode marginal')
    context = raw['equipment_context'];fields(context, SCORE['context'], 'equipment contexts')
    for name, cell in context.items():
        fields(cell, ('planned_seconds', 'episodes', 'unmatched'), 'context cell')
        for key in cell: integer(cell[key], 172800, key)
        require(cell['unmatched'] <= cell['episodes'], 'unmatched subset')
        same(score['context'][name]['planned'], 4*cell['planned_seconds'], 'context score exposure')
    same(sum(c['planned_seconds'] for c in context.values()), 43200, 'equipment exposure')
    same(context['clean']['planned_seconds'], 40380, 'clean exposure')


def _bind_primary(raw, pairs, profile, n):
    for kind in ('machine', 'sensor'):
        cell = raw['incident_slices']['class'][kind]
        same(cell['planned'], 10*n, 'class planned denominator')
        same([cell['detected'], cell['planned']], pairs[kind+'_recall'], 'primary recall binding')
    for target in TARGETS:
        cell = raw['score_slices']['full-target'][target]
        same(cell['planned'], 1800*n, 'target denominator')
        same([cell['available'], cell['observed']], pairs['availability:'+target], 'primary availability binding')
    context = raw['equipment_context']
    same([sum(raw['delay_histogram']), sum(c['episodes'] for c in context.values())], pairs['precision'], 'primary precision binding')
    same([sum(c['unmatched'] for c in context.values()), 20*n], pairs['false_alert_burden'], 'primary unmatched binding')
    same([context['clean']['unmatched'], context['clean']['planned_seconds']], pairs['clean_rate'], 'primary clean binding')
    require(profile in ('calibrated', 'inconclusive'), 'primary profile')
    same(raw['profile_inconclusive_evaluations'] > 0, profile == 'inconclusive', 'profile binding')


def pooled(records):
    # Sum each fixed coordinate over records; no recursive producer accumulator.
    return {'evaluations': sum(r['evaluations'] for r in records),
        'profile_inconclusive_evaluations': sum(r['profile_inconclusive_evaluations'] for r in records),
        'delay_histogram': [sum(r['delay_histogram'][i] for r in records) for i in range(5)],
        'equipment_context': {k: {field: sum(r['equipment_context'][k][field] for r in records)
            for field in ('planned_seconds', 'episodes', 'unmatched')} for k in SCORE['context']},
        'incident_slices': {d: {k: _sum_incident(r['incident_slices'][d][k] for r in records) for k in keys} for d, keys in INCIDENT.items()},
        'score_slices': {d: {k: _sum_scores(r['score_slices'][d][k] for r in records) for k in keys} for d, keys in SCORE.items()}}


def described(raw):
    result = {name: raw[name] for name in ('evaluations', 'profile_inconclusive_evaluations', 'delay_histogram', 'equipment_context')}
    result.update(delay_summary=delay_summary(raw['delay_histogram']), incident_slices=[], score_slices=[])
    for dimension, keys in INCIDENT.items():
        for key in keys:
            cell = raw['incident_slices'][dimension][key];n, d = cell['detected'], cell['planned']
            result['incident_slices'].append({'dimension': dimension, 'key': key, **cell,
                'recall': n/d if d else None, 'ci_status': 'not_evaluated' if d else 'not_applicable',
                'delay_summary': delay_summary(cell['delay_histogram'])})
    for dimension, keys in SCORE.items():
        for key in keys:
            cell = raw['score_slices'][dimension][key];d = cell['observed']
            result['score_slices'].append({'dimension': dimension, 'key': key, **cell,
                'availability': cell['available']/d if d else None,
                'threshold_exceedance_rate': cell['threshold_exceeded']/d if d else None,
                'signal_onset_rate': cell['signal_onsets']/d if d else None,
                'ci_status': 'not_evaluated' if d else 'not_applicable'})
    return result


def mapped(table, cell, series):
    incident = series == 'incident-recall';n = cell[SERIES[series]];d = cell['planned'] if incident else cell['observed']
    return {'candidate_id': table['candidate_id'], 'stratum': table['stratum'], 'dimension': cell['dimension'], 'key': cell['key'],
        'metric': {'numerator': n, 'denominator': d, 'value': n/d if d else None,
            'ci_status': 'not_evaluated' if d else 'not_applicable', 'ci_lower': None, 'ci_upper': None, 'null_replicates': 0},
        'planned_count': cell['planned'], 'actual_count': n, 'delay_summary': cell['delay_summary'] if incident else None}


def success_summary(fixture, source):
    """Required success claim only; this does not derive or certify table values."""
    require(type(fixture) is dict, 'primary input')
    same(fixture['format'], 'anomaly-v03-document-fixture-input-v1', 'primary identity')
    same(fixture['invented_only'], True, 'invented primary input')
    fields(source, ('format', 'invented_only', 'clusters'), 'slice input')
    same(source['format'], 'anomaly-v03-slice-fixture-input-v1', 'slice identity')
    same(source['invented_only'], True, 'invented slice input')
    for clusters in (fixture['clusters'], fixture['diagnostics'], source['clusters']):
        require(type(clusters) is list and len(clusters) == 40, '40 clusters')
        for i, entry in enumerate(clusters):
            fields(entry, ('cluster_id', 'candidates'), 'cluster')
            same(entry['cluster_id'], f'invented-{i:02d}', 'ordered cluster identity')
            fields(entry['candidates'], CANDIDATES, 'candidate inventory')
            for layers in entry['candidates'].values(): fields(layers, LAYERS[:2], 'stratum inventory')
    return {'format': 'anomaly-v03-fixture-slice-audit-v1', 'status': 'slice_numerics_matched',
        'algorithm': 'coordinate-sums-and-expanded-delay-multisets-v1', 'clusters': 40,
        'main_slice_rows': 1233, 'diagnostic_rows': 2835, 'diagnostic_tables': 9,
        'input_canonical_sha256': hashlib.sha256(canonical(fixture)).hexdigest(),
        'slice_input_canonical_sha256': hashlib.sha256(canonical(source)).hexdigest(),
        'fixture_only': True, 'fixture_slice_audit_performed': True,
        'formal_permission': False, 'promotion_allowed': False, 'registered_data_read': False,
        'independent_s6_complete': False,
        'checked': ['fixed count inventories and partitions', 'joint/marginal and target/mode correspondence',
                    'primary counts, profiles and detected delay binding', 'stratum/overall sums and diagnostic details',
                    'all main and four-series rows, denominators, omissions and null states'],
        'not_checked': ['raw producer observation derivation', 'registered coverage or inference',
                        'formal slice mapping adoption', 'publication or complete source/runtime closure']}


def audit_slices(fixture, source, document):
    """Verify all slice/detail rows against pinned invented counts, without IO."""
    result = success_summary(fixture, source)
    same(document['format'], 'anomaly-v03-document-with-slices-fixture-v1', 'document identity')
    for key in ('input_canonical_sha256', 'slice_input_canonical_sha256'): same(document[key], result[key], key)
    tables = {}
    for table in document['document_draft']['candidate_tables']:
        key = table['candidate_id'], table['stratum'];require(key not in tables, 'duplicate primary table');tables[key] = table
    require(set(tables) == {(c, s) for c in CANDIDATES for s in LAYERS}, 'primary table inventory')
    for i, cluster in enumerate(source['clusters']):
        for candidate in CANDIDATES:
            for layer in LAYERS[:2]:
                raw = cluster['candidates'][candidate][layer];validate_raw(raw)
                primary = fixture['clusters'][i]['candidates'][candidate][layer]
                _bind_primary(raw, primary['counts'], primary['profile_status'], 12)
                detail = fixture['diagnostics'][i]['candidates'][candidate][layer]
                delays = detail['detected_delays']
                require(type(delays) is list and len(delays) <= 240 and all(type(d) is int and 1 <= d <= 5 for d in delays), 'detected delays')
                same(raw['delay_histogram'], [delays.count(d) for d in range(1, 6)], 'per-cluster delay binding')
    main, details = [], [];series_rows = {s: [] for s in SERIES}
    for candidate in CANDIDATES:
        for layer in LAYERS:
            parts = LAYERS[:2] if layer == 'overall' else (layer,)
            raw = pooled([entry['candidates'][candidate][part] for entry in source['clusters'] for part in parts])
            primary = tables[candidate, layer];metrics = primary['metrics']
            pairs = {m: [metrics[m]['numerator'], metrics[m]['denominator']] for m in
                     ('machine_recall', 'sensor_recall', 'precision', 'false_alert_burden', 'clean_rate')}
            pairs.update({'availability:'+r['full_target']: [r['metric']['numerator'], r['metric']['denominator']] for r in metrics['availability']})
            _bind_primary(raw, pairs, primary['profile_status'], 960 if layer == 'overall' else 480)
            # Primary summaries may use integral numbers while slice summaries
            # use floats; exact numeric equality is intended for this one join.
            require(delay_summary(raw['delay_histogram']) == metrics['delay_summary'], 'pooled primary delay binding')
            table = {'candidate_id': candidate, 'stratum': layer, **described(raw)};details.append(table)
            for series in SERIES:
                group = 'incident_slices' if series == 'incident-recall' else 'score_slices'
                rows = [mapped(table, cell, series) for cell in table[group]]
                series_rows[series].extend(rows)
                if series in ('incident-recall', 'score-availability'): main.extend(rows)
    same(document['document_draft']['slices'], main, 'main slice rows')
    same(document['diagnostic_series'], series_rows, 'diagnostic series')
    same(document['diagnostic_details'], details, 'diagnostic details')
    require(len(main) == 1233 and sum(map(len, series_rows.values())) == 2835 and len(details) == 9, 'derived inventory')
    return result


def audit_precomputed_slices(clusters, diagnostics, packet, source, enriched):
    """Independently check invented slice rows attached to saved primary tables.

    The caller authenticates the raw files.  This pure check binds the supplied
    forty-cluster counts and diagnostics to the *precomputed* primary packet,
    then checks every main/sidecar/detail row.  It does not replay bootstrap
    draws, verify their CIs or gates, or certify producer observations.
    """
    fields(packet, ('fixture_candidate_tables', 'fixture_decision', 'fixture_draws',
                    'fixture_engineering_ready', 'fixture_selected_candidate',
                    'formal_document_emitted', 'formal_permission',
                    'independent_s6_complete', 'not_validated', 'performance_status',
                    'promotion_allowed', 'scope', 'selected_candidate', 'validation'),
           'precomputed primary packet')
    same(packet['fixture_draws'], {'clusters': 40, 'replicates': 50000},
         'saved primary draw dimensions')
    for key, expected in (('scope', 'hand-fixture-analysis-tables-only'),
                          ('fixture_decision', 'inconclusive'),
                          ('fixture_engineering_ready', False),
                          ('fixture_selected_candidate', None),
                          ('formal_document_emitted', False),
                          ('formal_permission', False),
                          ('independent_s6_complete', False),
                          ('performance_status', 'not_evaluated'),
                          ('promotion_allowed', False),
                          ('selected_candidate', None)):
        same(packet[key], expected, 'precomputed packet '+key)
    fields(packet['validation'], ('formal_document_validated', 'gates',
                                  'source_runtime_slices_validated', 'status',
                                  'tables'), 'precomputed packet validation')
    same(packet['validation'], {
        'formal_document_validated': False, 'gates': 180,
        'source_runtime_slices_validated': False,
        'status': 'fixture_table_contract_valid', 'tables': 9,
    }, 'precomputed packet validation')
    fields(enriched, ('slices', 'diagnostic_series', 'diagnostic_details',
                      'primary_packet_canonical_sha256',
                      'slice_source_canonical_sha256'), 'precomputed slices')
    packet_digest = hashlib.sha256(canonical(packet)).hexdigest()
    source_digest = hashlib.sha256(canonical(source)).hexdigest()
    same(enriched['primary_packet_canonical_sha256'], packet_digest,
         'precomputed primary packet canonical digest')
    same(enriched['slice_source_canonical_sha256'], source_digest,
         'precomputed slice source canonical digest')

    # Reuse only this module's stdlib-only coordinate audit.  The temporary
    # fixture carries no legacy draw list or old document digest; it supplies
    # exactly the primary counts/diagnostics required for a slice crosscheck.
    fixture = {'format': 'anomaly-v03-document-fixture-input-v1',
               'invented_only': True, 'clusters': clusters,
               'diagnostics': diagnostics}
    document = {
        'format': 'anomaly-v03-document-with-slices-fixture-v1',
        'input_canonical_sha256': hashlib.sha256(canonical(fixture)).hexdigest(),
        'slice_input_canonical_sha256': source_digest,
        'document_draft': {
            'candidate_tables': packet['fixture_candidate_tables'],
            'slices': enriched['slices'],
        },
        'diagnostic_series': enriched['diagnostic_series'],
        'diagnostic_details': enriched['diagnostic_details'],
    }
    checked = audit_slices(fixture, source, document)
    return {
        'format': 'anomaly-v03-precomputed-fixture-slice-audit-v1',
        'status': 'precomputed_fixture_slices_matched',
        'algorithm': checked['algorithm'],
        'clusters': checked['clusters'],
        'main_slice_rows': checked['main_slice_rows'],
        'diagnostic_rows': checked['diagnostic_rows'],
        'diagnostic_tables': checked['diagnostic_tables'],
        'primary_packet_canonical_sha256': packet_digest,
        'slice_source_canonical_sha256': source_digest,
        'fixture_only': True,
        'precomputed_primary_packet_used': True,
        'fixture_slice_audit_performed': True,
        'primary_ci_gate_recomputed': False,
        'formal_permission': False,
        'promotion_allowed': False,
        'registered_data_read': False,
        'independent_s6_complete': False,
        'checked': checked['checked'],
        'not_checked': [*checked['not_checked'],
                        'saved 50000 bootstrap CI and gate recomputation',
                        'raw file pin, source/runtime or process authentication'],
    }
