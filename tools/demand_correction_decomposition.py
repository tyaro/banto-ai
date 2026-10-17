"""Saved-prediction diagnosis only: no fitting, forecasting, data extraction or IO."""
import datetime as dt
import math

METHODS = ('baseline', 'feature_off', 'feature_on')
TERMS = ('correction_squared', 'alignment', 'mse_delta',
         'mean_correction', 'mean_required_correction')


def _number(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError('expected a finite nonnegative quantity or scale')
    return value


def validate_ledger(rows, before_labels, scales, stores, origins):
    """Check the full fixed grid and unchanged predictions, masks and roles."""
    expected = {(s, str(d)) for s in stores for d in origins}
    if len(rows) != len(expected) or len(before_labels) != len(expected):
        raise ValueError('requested grid count mismatch')
    before = {}
    for row in before_labels:
        key = (row['store'], row['origin'])
        if key not in expected or key in before:
            raise ValueError('pre-label identity mismatch')
        before[key] = row
    seen = set()
    for row in rows:
        key = (row['store'], row['origin'])
        if key not in expected or key in seen:
            raise ValueError('label identity mismatch')
        seen.add(key)
        prior = {k: v for k, v in row.items()
                 if k not in ('actual', 'complete_label', 'comparable')}
        if prior != before[key]:
            raise ValueError('prediction changed during label attachment')
        scale = _number(row['scale'])
        if scale != scales[row['store']]:
            raise ValueError('preperiod scale mismatch')
        if row['role'] != ('positive_scale' if scale > 0 else 'zero_scale_baseline_only'):
            raise ValueError('scale role mismatch')
        actual = row['actual']
        if len(actual) != 14:
            raise ValueError('label horizon mismatch')
        for a in actual:
            if a is not None:
                _number(a)
        if type(row['complete_label']) is not bool or row['complete_label'] != all(a is not None for a in actual):
            raise ValueError('complete-label mask mismatch')
        predictions = [row[m] for m in METHODS]
        for values in predictions:
            if values is not None:
                if len(values) != 14:
                    raise ValueError('prediction horizon mismatch')
                for p in values:
                    _number(p)
        if type(row['comparable']) is not bool or row['comparable'] != all(p is not None for p in predictions):
            raise ValueError('common prediction support mismatch')
        if type(row['model_available']) is not bool:
            raise ValueError('input availability must be boolean')
        if scale > 0 and row['comparable'] != row['model_available']:
            raise ValueError('positive-scale model support mismatch')
        if scale == 0 and not (row['baseline'] == row['feature_off'] == row['feature_on']):
            raise ValueError('zero-scale fallback predictions changed')


def _terms(p, b, y, denominator):
    d, r = (p - b) / denominator, (y - b) / denominator
    energy, alignment = d * d, 2 * d * r
    delta = energy - alignment
    direct = ((p - y) / denominator)**2 - ((b - y) / denominator)**2
    if not all(math.isfinite(v) for v in (d, r, energy, alignment, delta, direct)):
        raise ValueError('nonfinite diagnostic arithmetic')
    if not math.isclose(delta, direct, rel_tol=1e-10, abs_tol=1e-10):
        raise ValueError('squared-error identity mismatch')
    return {'correction_squared': energy, 'alignment': alignment, 'mse_delta': delta,
            'mean_correction': d, 'mean_required_correction': r,
            'identity_abs_error': abs(delta - direct),
            'direction': 'zero_correction' if d == 0 else 'zero_required' if r == 0
                         else 'same' if d * r > 0 else 'opposite',
            'over_twice_required': abs(d) > 2 * abs(r)}


def _aggregate(values):
    n = len(values)
    result = {'count': n, **{k: math.fsum(v[k] for v in values) / n if n else None for k in TERMS},
              'identity_max_abs_error': max((v['identity_abs_error'] for v in values), default=None),
              'directions': {k: sum(v['direction'] == k for v in values)
                             for k in ('zero_correction', 'zero_required', 'same', 'opposite')},
              'over_twice_required': sum(v['over_twice_required'] for v in values)}
    return result


def group(rows, method, reference='baseline'):
    """Within-store means: observed daily labels and complete totals stay distinct."""
    if method not in METHODS or reference not in METHODS or method == reference:
        raise ValueError('distinct known prediction columns required')
    scales = {_number(r['scale']) for r in rows}
    stores = {r['store'] for r in rows}
    if len(stores) > 1 or len(scales) > 1 or any(u <= 0 for u in scales):
        raise ValueError('one positive-scale store required')
    daily, total = [], []
    comparable = 0
    for row in rows:
        if not row['comparable']:
            continue
        comparable += 1
        u = row['scale']
        p, b, actual = row[method], row[reference], row['actual']
        for pi, bi, yi in zip(p, b, actual):
            if yi is not None:
                daily.append(_terms(pi, bi, yi, u))
        if row['complete_label']:
            total.append(_terms(math.fsum(p), math.fsum(b), math.fsum(actual), 14 * u))
    result = {'requested': len(rows), 'comparable': comparable,
              'daily': _aggregate(daily), 'total': _aggregate(total)}
    result['joint'] = {k: .5 * (result['daily'][k] + result['total'][k])
                       if daily and total else None for k in TERMS}
    return result


def macro(by_store):
    """Equal fixed-store weights, never pooled label-count weights."""
    n = len(by_store)
    if not n:
        raise ValueError('fixed stores required')
    result = {}
    for scope in ('daily', 'total', 'joint'):
        result[scope] = {}
        for k in TERMS:
            values = [v[scope][k] for v in by_store.values()]
            result[scope][k] = math.fsum(values) / n if all(v is not None for v in values) else None
    result['stores'] = n
    result['support'] = {s: {k: v[k]['count'] for k in ('daily', 'total')} for s, v in by_store.items()}
    return result


def diagnose(rows, active_stores):
    """All stores and all four origin quarters; no correction multiplier selection."""
    comparisons = {}
    for name, candidate, reference in (('feature_off_vs_baseline', 'feature_off', 'baseline'),
                                      ('feature_on_vs_baseline', 'feature_on', 'baseline'),
                                      ('feature_on_vs_feature_off', 'feature_on', 'feature_off')):
        stores = {str(s): group([r for r in rows if r['store'] == s], candidate, reference)
                  for s in active_stores}
        quarters = {}
        for q in range(1, 5):
            by_store = {str(s): group([r for r in rows if r['store'] == s and
                (dt.date.fromisoformat(r['origin']).month - 1) // 3 + 1 == q], candidate, reference)
                for s in active_stores}
            quarters[str(q)] = {'per_store': by_store, 'macro': macro(by_store)}
        comparisons[name] = {'per_store': stores, 'macro': macro(stores), 'quarters': quarters}
    return comparisons
