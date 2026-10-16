"""Fixed existing-store saved-error decomposition; no training or forecasting."""
import json
import math
from pathlib import Path
import sys

from demand_correction_decomposition import diagnose, validate_ledger
from demand_macos_diagnosis import adapt, COMPARISONS, MAPPING, ORIGINS
from demand_group_selection import FIT
from macos_demand_runtime import MacCheckpoint
from verify_demand_transfer import verify, pin

REPO = Path(__file__).resolve().parents[1]
CONTRACT = 'docs/research/demand-existing-store-diagnosis-design-2026-10-15.md'


def paired(values, references, actuals, denominator):
    if (not (len(values) == len(references) == len(actuals))
            or type(denominator) not in (int, float) or not math.isfinite(denominator) or denominator <= 0):
        raise ValueError('matching prediction support and positive denominator required')
    changes = []
    for p, b, y in zip(values, references, actuals):
        if y is None:
            continue
        if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in (p, b, y)):
            raise ValueError('finite nonnegative saved value required')
        e, old = p-y, b-y
        under = max(-e, 0)-max(-old, 0)
        over = max(e, 0)-max(old, 0)
        delta = abs(e)-abs(old)
        squared = (e/denominator)**2-(old/denominator)**2
        if (not math.isclose(delta, under+over, rel_tol=1e-10, abs_tol=1e-10)
                or not math.isclose(e-old, over-under, rel_tol=1e-10, abs_tol=1e-10)):
            raise ValueError('absolute error/bias identity mismatch')
        changes.append({'absolute_delta': delta, 'under_delta': under, 'over_delta': over,
                        'bias_delta': e-old, 'scaled_squared_delta': squared, 'actual': y})
    return changes


def aggregate(changes):
    if not changes:
        return {'count': 0, **{k: None for k in ('MAE_delta', 'under_delta', 'over_delta', 'bias_delta',
                                               'WAPE_delta_percent', 'squared_gain', 'squared_loss')},
                'helped': 0, 'hurt': 0, 'tied': 0, 'absolute_gain': None, 'absolute_loss': None}
    n = len(changes)
    mean = lambda key: math.fsum(c[key] for c in changes)/n
    actual = math.fsum(c['actual'] for c in changes)
    return {'count': n, 'MAE_delta': mean('absolute_delta'), 'under_delta': mean('under_delta'),
            'over_delta': mean('over_delta'), 'bias_delta': mean('bias_delta'),
            'WAPE_delta_percent': 100*math.fsum(c['absolute_delta'] for c in changes)/actual if actual else None,
            'helped': sum(c['absolute_delta'] < 0 for c in changes),
            'hurt': sum(c['absolute_delta'] > 0 for c in changes),
            'tied': sum(c['absolute_delta'] == 0 for c in changes),
            'absolute_gain': math.fsum(min(c['absolute_delta'], 0) for c in changes)/n,
            'absolute_loss': math.fsum(max(c['absolute_delta'], 0) for c in changes)/n,
            'squared_gain': math.fsum(min(c['scaled_squared_delta'], 0) for c in changes)/n,
            'squared_loss': math.fsum(max(c['scaled_squared_delta'], 0) for c in changes)/n}


def absolute_group(rows, method, reference):
    daily, total = [], []
    for row in rows:
        if not row['comparable']:
            continue
        daily.extend(paired(row[method], row[reference], row['actual'], row['scale']))
        if row['complete_label']:
            total.extend(paired([math.fsum(row[method])], [math.fsum(row[reference])],
                                [math.fsum(row['actual'])], 14*row['scale']))
    return {'daily': aggregate(daily), 'total': aggregate(total)}


def absolute_macro(by_store):
    fields = ('MAE_delta', 'under_delta', 'over_delta', 'bias_delta', 'WAPE_delta_percent',
              'absolute_gain', 'absolute_loss', 'squared_gain', 'squared_loss')
    result = {}
    for scope in ('daily', 'total'):
        result[scope] = {f: math.fsum(v[scope][f] for v in by_store.values())/len(by_store)
                           if all(v[scope][f] is not None for v in by_store.values()) else None for f in fields}
        result[scope].update({f: sum(v[scope][f] for v in by_store.values()) for f in ('count', 'helped', 'hurt', 'tied')})
    return result


def calculate(rows, before, scales, summary):
    rows = [adapt(r, labelled=True) for r in rows]
    before = [adapt(r, labelled=False) for r in before]
    validate_ledger(rows, before, scales, FIT, ORIGINS)
    if summary['primary'] != 'time_selected':
        raise ValueError('primary selection changed')
    for s in FIT:
        kept = [r for r in rows if r['store'] == s]
        if (scales[s] <= 0 or len(kept) != 25 or sum(r['complete_label'] for r in kept) != 24
                or not all(r['comparable'] for r in kept)
                or sum(a is not None for r in kept for a in r['actual']) != 349):
            raise ValueError('fixed store support changed')
    raw = diagnose(rows, FIT)
    comparisons, errors = {}, []
    for name, (old_name, candidate, reference) in COMPARISONS.items():
        method = next(k for k, v in MAPPING.items() if v == candidate)
        ref = next((k for k, v in MAPPING.items() if v == reference), reference)
        squared = raw[old_name]
        absolute = {str(s): absolute_group([r for r in rows if r['store'] == s], method, ref) for s in FIT}
        sq_scopes = [('macro', squared['macro'], absolute_macro(absolute), summary['macro'])]
        sq_scopes += [('store-'+s, g, absolute[s], summary['per_store'][s]) for s, g in squared['per_store'].items()]
        quarter_absolute = {}
        for q, groups in squared['quarters'].items():
            by_store = {str(s): absolute_group([r for r in rows if r['store'] == s and
                        (int(r['origin'][5:7])-1)//3+1 == int(q)], method, ref) for s in FIT}
            quarter_absolute[q] = {'per_store': by_store, 'macro': absolute_macro(by_store)}
            sq_scopes.append(('quarter-'+q, groups['macro'], absolute_macro(by_store), summary['quarter_macro'][q]))
            sq_scopes += [('quarter-'+q+'/store-'+s, g, by_store[s], summary['quarter_per_store'][q][s])
                          for s, g in groups['per_store'].items()]
        for location, sq, ab, saved in sq_scopes:
            checks = [(f, sq[f]['mse_delta']) for f in ('daily', 'total', 'joint')]
            checks += [(scope+'_'+field, ab[scope][key]) for scope in ('daily', 'total') for field, key in
                       (('MAE', 'MAE_delta'), ('bias', 'bias_delta'), ('WAPE_percent', 'WAPE_delta_percent'))]
            for field, actual in checks:
                expected = saved[candidate][field]-saved[reference][field]
                if not math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-10):
                    raise ValueError('saved summary difference mismatch: '+location+'/'+field)
                errors.append(abs(actual-expected))
        comparisons[name] = {'squared': squared, 'absolute': {'per_store': absolute, 'macro': absolute_macro(absolute),
                                                             'quarters': quarter_absolute}}
    return {'primary': 'time_selected', 'comparisons': comparisons,
            'summary_checks': {'count': len(errors), 'max_absolute_error': max(errors)},
            'support': {'requested': 250, 'observed_daily_labels': 3490, 'complete_total_labels': 240},
            'new_fit': False, 'new_forward': False, 'formal_permission': False, 'adopted': False}


def main():
    if sys.version_info[:3] != (3, 14, 8):
        raise ValueError('Python3.14.8 required')
    guard = MacCheckpoint(seconds=870)
    root = REPO/'artifacts/macos-demand-existing-stores-2015-20261015'
    original = verify(root)
    if original['recorded_status'] != 'complete':
        raise ValueError('complete source required')
    read = lambda name: json.loads((root/name).read_bytes())
    summary = read('summary.json')
    for name, expected in summary['source_pins'].items():
        if pin(REPO/name) != expected:
            raise ValueError('original source changed: '+name)
    guard.check()
    scales = {int(s): v['scale'] for s, v in read('scale-and-calendar-binding.json')['scales'].items()}
    result = calculate(read('predictions-and-labels.json'), read('predictions-before-labels.json'), scales, summary)
    if verify(root) != original:
        raise ValueError('original evaluation root changed')
    result.update(source=original, original_root_unchanged=True, resources=guard.check())
    print(json.dumps(result, sort_keys=True, ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
