"""Connect invented forty-cluster diagnostic counts to a document draft.

No registered observations, inference recomputation, IO or formal acceptance.
The proposed single-metric slice mapping is exercised, not formally adopted.
"""
from __future__ import annotations

import copy

from . import anomaly_v03_document_fixture as document
from . import anomaly_v03_analysis_inputs as inputs
from . import anomaly_v03_descriptive_report as report
from . import anomaly_v03_slices as slices

I = document.I
INPUT_FORMAT = 'anomaly-v03-slice-fixture-input-v1'
OUTPUT_FORMAT = 'anomaly-v03-document-with-slices-fixture-v1'
PENDING = tuple(k for k in document.PENDING if k != 'slices')
EXTRA = ('slice_input_canonical_sha256', 'diagnostic_series', 'diagnostic_details')


def _raw_shape(value, template):
    if type(template) is dict:
        document._fields(value, template, 'raw diagnostic fields')
        for key in template:
            _raw_shape(value[key], template[key])
    elif type(template) is list:
        slices.delay_summary(value)
    else:
        inputs.integer(value)


def _sum_cells(cells):
    total = copy.deepcopy(cells[0])
    for key in total:
        total[key] = ([sum(cell[key][j] for cell in cells) for j in range(5)]
                      if type(total[key]) is list else sum(cell[key] for cell in cells))
    return total


def _marginals(raw):
    # Matching partition totals alone would miss reassignment between classes,
    # equipment or modes. Retain their joint-to-marginal correspondence too.
    inc = raw['incident_slices']
    joint = inc['class-equipment-mode']
    for dimension, part in (('class', 0), ('equipment', 1), ('mode', 2)):
        for key, cell in inc[dimension].items():
            chosen = [v for k, v in joint.items() if k.split('.')[part] == key]
            I.exact(cell, _sum_cells(chosen), 'incident joint/marginal correspondence')
    score = raw['score_slices']
    for target, cell in score['full-target'].items():
        chosen = [score['signal-mode'][target+'.'+mode] for mode in slices.MODES]
        I.exact(cell, _sum_cells(chosen), 'target/mode correspondence')


def _primary(raw, metrics, *, described):
    """Bind slice counts to fixture input pairs or saved document metrics."""
    def pair(name):
        value = (next(v['metric'] for v in metrics['availability']
                      if v['full_target'] == name.split(':', 1)[1])
                 if described and name.startswith('availability:') else metrics[name])
        return [value['numerator'], value['denominator']] if described else value
    for kind in ('machine', 'sensor'):
        cell = raw['incident_slices']['class'][kind]
        I.exact(cell['planned'], 10*raw['evaluations'], 'class planned denominator')
        I.exact([cell['detected'], cell['planned']], pair(kind+'_recall'), 'slice/recall binding')
    for target in slices.TARGETS:
        cell = raw['score_slices']['full-target'][target]
        I.exact(cell['planned'], 1800*raw['evaluations'], 'target planned denominator')
        I.exact([cell['available'], cell['observed']], pair('availability:'+target), 'slice/availability binding')
    context = raw['equipment_context']
    detected = sum(raw['delay_histogram'])
    I.exact([detected, sum(c['episodes'] for c in context.values())], pair('precision'), 'slice/precision binding')
    I.exact([sum(c['unmatched'] for c in context.values()), 20*raw['evaluations']],
            pair('false_alert_burden'), 'slice/unmatched binding')
    I.exact([context['clean']['unmatched'], context['clean']['planned_seconds']],
            pair('clean_rate'), 'slice/clean binding')


def _coverage():
    rows = document._coverage()
    row = next(r for r in rows if r['field'] == 'slices')
    row.update(state='fixture_value_only', reason='invented incident recall/availability mapping; formal adoption pending')
    return rows


def _requirements():
    return {'clusters': 40, 'replicates': 50000, 'missing_fields': list(PENDING), 'ready': False}


def _derive(base, fixture_input, source):
    document._input(fixture_input)
    I._fixture_clusters(fixture_input['clusters'])
    document.adapter._diagnostics(fixture_input['clusters'], fixture_input['diagnostics'])
    I.exact(base['input_canonical_sha256'], document.contract.canonical_sha256(fixture_input), 'fixture input binding')
    document._fields(source, ('format', 'invented_only', 'clusters'), 'slice fixture input fields')
    I.exact(source['format'], INPUT_FORMAT, 'slice fixture identity')
    I.exact(source['invented_only'], True, 'invented slice assertion')
    I.need(type(source['clusters']) is list and len(source['clusters']) == 40, 'forty slice clusters')
    document.contract.json_value(source)
    template = slices.empty_counts()
    totals = {(c, s): slices.empty_counts() for c in I.CANDIDATES for s in I.STRATA}
    for index, entry in enumerate(source['clusters']):
        document._fields(entry, ('cluster_id', 'candidates'), 'slice cluster fields')
        I.exact(entry['cluster_id'], document.IDS[index], 'ordered slice cluster IDs')
        document._fields(entry['candidates'], I.CANDIDATES, 'slice candidates')
        for candidate in I.CANDIDATES:
            document._fields(entry['candidates'][candidate], I.STRATA[:2], 'slice strata')
            for layer in I.STRATA[:2]:
                raw = entry['candidates'][candidate][layer]
                _raw_shape(raw, template)
                I.exact(raw['evaluations'], 12, 'twelve-layout diagnostic coverage')
                # Reuse fixed inventory, denominator, omissions, histogram and
                # partition checks. No dev/smoke IO entry is relaxed or called.
                inputs._slice_counts(slices.describe(raw), 12)
                _marginals(raw)
                primary = fixture_input['clusters'][index]['candidates'][candidate][layer]
                _primary(raw, primary['counts'], described=False)
                detail = fixture_input['diagnostics'][index]['candidates'][candidate][layer]
                histogram = [0]*5
                for delay in detail['detected_delays']:
                    I.need(type(delay) is int and 1 <= delay <= 5, 'integer-second diagnostic delay')
                    histogram[delay-1] += 1
                I.exact(raw['delay_histogram'], histogram, 'per-cluster delay multiset')
                I.exact(raw['profile_inconclusive_evaluations'] > 0,
                        primary['profile_status'] == 'inconclusive', 'profile diagnostic binding')
                slices.add_counts(totals[candidate, layer], raw)
    series = {name: [] for name in report.SERIES}
    details, main = [], []
    for candidate in I.CANDIDATES:
        for layer in I.STRATA[:2]:
            slices.add_counts(totals[candidate, 'overall'], totals[candidate, layer])
        for layer in I.STRATA:
            raw = totals[candidate, layer]
            table = next(t for t in base['document_draft']['candidate_tables']
                         if (t['candidate_id'], t['stratum']) == (candidate, layer))
            _primary(raw, table['metrics'], described=True)
            # Numeric equality permits 2 vs 2.0 from the two existing summary
            # routines. Histogram counts were validated as exact integers.
            I.need(slices.delay_summary(raw['delay_histogram']) == table['metrics']['delay_summary'],
                   'pooled slice/document delay binding')
            I.exact(raw['profile_inconclusive_evaluations'] > 0,
                    table['profile_status'] == 'inconclusive', 'pooled profile binding')
            described = {'candidate_id': candidate, 'stratum': layer, **slices.describe(raw)}
            details.append(described)
            for name in report.SERIES:
                cells = described['incident_slices' if name == 'incident-recall' else 'score_slices']
                rows = [report._mapped_slice(described, cell, name) for cell in cells]
                series[name].extend(rows)
                if name in ('incident-recall', 'score-availability'):
                    main.extend(copy.deepcopy(rows))
    return {'slices': main, 'diagnostic_series': series, 'diagnostic_details': details,
            'slice_input_canonical_sha256': document.contract.canonical_sha256(source)}


def _check(value, expected, schema):
    I.exact(value['format'], OUTPUT_FORMAT, 'connected fixture identity')
    I.exact(value['field_coverage'], _coverage(), 'connected field coverage')
    I.exact(value['formal_requirements'], _requirements(), 'four missing formal fields')
    I.exact(value['document_draft']['slices'], expected['slices'], 'main slice mapping')
    for key in EXTRA:
        I.exact(value[key], expected[key], 'diagnostic mapping: '+key)
    shaped = {**schema['properties']['slices'], '$defs': schema['$defs']}
    for rows in (value['document_draft']['slices'], *value['diagnostic_series'].values()):
        document.contract._shape(rows, shaped)
        document.contract._reported_slices(rows, uncomputed_ci=True)
    I.exact(len(expected['slices']), 1233, 'main slice inventory')
    I.exact(sum(len(rows) for rows in expected['diagnostic_series'].values()), 2835, 'four-series inventory')
    return {'status': 'fixture_slices_connected', 'clusters': 40, 'candidate_tables': 9,
            'main_slice_rows': 1233, 'diagnostic_rows': 2835, 'mapped_fields': 6,
            'missing_fields': list(PENDING), 'formal_document_validated': False,
            'inference_recomputed': False, 'independent_numerical_audit_performed': False}


def _base(value, schema):
    I.need(type(value) is dict and all(k in value for k in EXTRA), 'connected diagnostic fields')
    I.exact(value['format'], OUTPUT_FORMAT, 'connected fixture identity')
    I.exact(value['field_coverage'], _coverage(), 'connected field coverage')
    I.exact(value['formal_requirements'], _requirements(), 'connected requirements')
    base = {k: copy.deepcopy(v) for k, v in value.items() if k not in EXTRA}
    base['format'] = document.OUTPUT_FORMAT
    base['document_draft']['slices'] = None
    base['field_coverage'] = document._coverage()
    base['formal_requirements']['missing_fields'] = list(document.PENDING)
    document.validate_fixture_document(base, schema)
    return base


def attach_fixture_slices(base, fixture_input, source, schema):
    """Attach the proposed mapping to an existing fixture without rerunning CIs."""
    document.validate_fixture_document(base, schema)
    expected = _derive(base, fixture_input, source)
    result = copy.deepcopy(base)
    result['format'] = OUTPUT_FORMAT
    result['document_draft']['slices'] = expected['slices']
    result['field_coverage'] = _coverage()
    result['formal_requirements'] = _requirements()
    result.update({key: expected[key] for key in EXTRA})
    _check(result, expected, schema)
    return result


def validate_connected_document(value, fixture_input, source, schema):
    """Check every emitted row against supplied invented counts, not run proof."""
    base = _base(value, schema)
    expected = _derive(base, fixture_input, source)
    return _check(value, expected, schema)
