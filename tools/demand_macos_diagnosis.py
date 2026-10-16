"""Describe one closed Mac prediction ledger without training or forecasting."""
import datetime as dt
import json
import math
from pathlib import Path
import sys

from demand_correction_decomposition import diagnose, validate_ledger
from macos_demand_runtime import MacCheckpoint
from verify_demand_transfer import verify, pin

REPO = Path(__file__).resolve().parents[1]
STORES = (4, 8, 16, 20, 24, 28)
ACTIVE = (4, 8, 16, 24, 28)
ORIGINS = tuple(dt.date(2015, 1, 13) + dt.timedelta(days=14*k) for k in range(25))
MAPPING = {'feature_off': 'time_selected', 'feature_on': 'transfer_selected'}
COMPARISONS = {'time_selected_vs_baseline': ('feature_off_vs_baseline', 'time_selected', 'baseline'),
               'transfer_selected_vs_baseline': ('feature_on_vs_baseline', 'transfer_selected', 'baseline'),
               'transfer_selected_vs_time_selected': ('feature_on_vs_feature_off', 'transfer_selected', 'time_selected')}


def adapt(row, *, labelled):
    expected = {'store', 'origin', 'scale', 'baseline', 'time_selected', 'transfer_selected',
                'model_available', 'input_reasons'}
    if labelled:
        expected |= {'actual', 'complete_label'}
    if set(row) != expected:
        raise ValueError('unexpected Mac ledger schema')
    value = {k: v for k, v in row.items() if k not in MAPPING.values()}
    value.update({target: row[source] for target, source in MAPPING.items()})
    value['role'] = 'positive_scale' if row['scale'] > 0 else 'zero_scale_baseline_only'
    if labelled:
        value['comparable'] = all(value[k] is not None for k in ('baseline', *MAPPING))
    return value


def calculate(rows, before, scales, summary):
    rows = [adapt(r, labelled=True) for r in rows]
    before = [adapt(r, labelled=False) for r in before]
    validate_ledger(rows, before, scales, STORES, ORIGINS)
    for store in STORES:
        selected = [r for r in rows if r['store'] == store]
        if (len(selected) != 25 or sum(r['complete_label'] for r in selected) != 24
                or not all(r['comparable'] for r in selected)
                or sum(a is not None for r in selected for a in r['actual']) != 349):
            raise ValueError('fixed support changed')
    if not all(scales[s] > 0 for s in ACTIVE) or scales[20] != 0:
        raise ValueError('fixed scale roles changed')
    raw = diagnose(rows, ACTIVE)
    output, checks = {}, []
    for name, (old_name, candidate, reference) in COMPARISONS.items():
        values = raw[old_name]
        scopes = [('macro', values['macro'], summary['development_macro'])]
        scopes += [('store-' + s, g, summary['per_store'][s]) for s, g in values['per_store'].items()]
        scopes += [('quarter-' + q, g['macro'], summary['quarter_macro'][q]) for q, g in values['quarters'].items()]
        for location, diagnostic, saved in scopes:
            for scope in ('daily', 'total', 'joint'):
                delta = saved[candidate][scope] - saved[reference][scope]
                actual = diagnostic[scope]['mse_delta']
                if not math.isclose(actual, delta, rel_tol=1e-10, abs_tol=1e-10):
                    raise ValueError('saved summary difference mismatch: ' + location + '/' + scope)
                checks.append({'comparison': name, 'location': location, 'scope': scope,
                               'absolute_error': abs(actual - delta)})
        output[name] = values
    zero = [r for r in rows if r['store'] == 20]
    zero_errors = {MAPPING.get(m, m): {'daily_squared_error_sum': math.fsum((p-y)**2 for r in zero
                       for p, y in zip(r[m], r['actual']) if y is not None),
                      'complete_total_squared_error_sum': math.fsum(
                       (math.fsum(r[m])-math.fsum(r['actual']))**2 for r in zero if r['complete_label'])}
                   for m in ('baseline', *MAPPING)}
    return {'comparisons': output, 'summary_checks': {'count': len(checks),
            'max_absolute_error': max(c['absolute_error'] for c in checks)},
            'support': {'requested': len(rows), 'positive_windows': 125, 'baseline_only_windows': 25,
                        'complete_label_windows': 144, 'each_store_daily_labels': 349},
            'zero_scale_store20': {'normalized': False, 'requested': 25, 'errors': zero_errors},
            'new_fit': False, 'new_forward': False, 'formal_permission': False, 'adopted': False}


def main():
    if sys.version_info[:3] != (3, 14, 8):
        raise ValueError('CPython3.14.8 required')
    guard = MacCheckpoint(seconds=870)
    root = REPO / 'artifacts/macos-demand-rebuild-20261015'
    original = verify(root)
    closure = json.loads((root / 'root-closed.json').read_bytes())
    if original['recorded_status'] != 'complete':
        raise ValueError('complete source required')
    summary = json.loads((root / 'summary.json').read_bytes())
    for name, expected in summary['source_pins'].items():
        if pin(REPO / name) != expected:
            raise ValueError('original source changed: ' + name)
    guard.check()
    read = lambda name: json.loads((root / name).read_bytes())
    scales = {int(s): v['scale'] for s, v in read('scale-metadata.json').items()}
    result = calculate(read('predictions-and-labels.json'), read('predictions-before-labels.json'), scales, summary)
    result['source'] = original
    if verify(root) != original or json.loads((root / 'root-closed.json').read_bytes()) != closure:
        raise ValueError('source root changed during diagnosis')
    result['original_root_unchanged'] = True
    result['resources'] = guard.check()
    print(json.dumps(result, sort_keys=True, ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
