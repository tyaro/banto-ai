"""Mean28-referenced upward corrections and explicit shortfall eligibility."""
import math
from demand_autonomous_mean import FIT
from demand_seasonal_quantity import coefficient, quarter, score_rows

ORDER = ('matched_mean28', 'upward_ridge', 'seasonal_uplift', 'newyear_uplift')


def near_newyear(text):
    md = text[5:]
    return '12-26' <= md <= '12-31' or '01-02' <= md <= '01-14'


def upward_alpha(rows):
    baseline_rows = [dict(r, open_mean28=r['matched_mean28']) for r in rows]
    direction = [[max(p-b, 0.)/r['scale'] for p, b in zip(r['raw_prediction'], r['matched_mean28'])] for r in rows]
    return coefficient(baseline_rows, direction, 1.)


def choices(row, policy):
    import datetime as dt
    base, mask, raw, open_base = row['matched_mean28'], row['open_mask'], row['raw_prediction'], row['open_mean28']
    if any(len(v) != 14 for v in (base, mask, raw, open_base)) or not math.isfinite(row['scale']) or row['scale'] <= 0:
        raise ValueError('supported fourteen-day quantity input required')
    if any(not math.isfinite(v) or v < 0 for v in base+raw+open_base): raise ValueError('finite nonnegative means required')
    if any(v != 0 for v, good in zip(base, mask) if not good): raise ValueError('matched closure zero required')
    alpha = policy['alpha']['value']
    delta = policy['quarter_levels'][str(quarter(row['origin']))]['value']
    if not math.isfinite(alpha) or not 0 <= alpha <= 1 or not math.isfinite(delta) or delta < 0:
        raise ValueError('frozen nonnegative calibration required')
    ridge = [b+alpha*max(p-b, 0.) if good else 0. for b, p, good in zip(base, raw, mask)]
    seasonal = [b+max(p+delta*row['scale']-b, 0.) if good else 0. for b, p, good in zip(base, open_base, mask)]
    day = dt.date.fromisoformat(row['origin'])
    event = [p if near_newyear(str(day+dt.timedelta(days=j))) else b for j, (p, b) in enumerate(zip(seasonal, base))]
    result = {'matched_mean28': list(base), 'upward_ridge': ridge, 'seasonal_uplift': seasonal, 'newyear_uplift': event}
    if any(p < b or (not good and p != 0.) or not math.isfinite(p) for values in result.values() for p, b, good in zip(values, base, mask)):
        raise ValueError('pointwise upward and closure contract violated')
    return result


def measure(rows, prediction):
    result = score_rows(rows, prediction)
    per_store = {}
    max_increase = 0.
    for s in FIT:
        errors, increases = [], []
        for row in rows:
            if row['store'] != s or not row['complete_label']: continue
            actual = math.fsum(row['actual'])
            forecast = math.fsum(prediction(row)); control = math.fsum(row['baseline_proxy'])
            errors.append(forecast-actual)
            increases.append(max(actual-forecast, 0.)-max(actual-control, 0.))
        if not errors: raise ValueError('complete total support required in each store')
        per_store[str(s)] = {'under': math.fsum(max(-e, 0.) for e in errors)/len(errors),
                             'over': math.fsum(max(e, 0.) for e in errors)/len(errors),
                             'under_windows': sum(e < 0 for e in errors), 'complete_totals': len(errors)}
        max_increase = max(max_increase, max(increases))
    result['shortfall'] = {'per_store': per_store, 'macro': {k: math.fsum(v[k] for v in per_store.values())/10 for k in ('under', 'over')},
                          'max_window_increase_over_matched': max_increase}
    return result


def choose(groups):
    if set(groups) != {'selection', 'newyear'}: raise ValueError('ordinary and newyear eligibility required')
    checks = {}
    for method in ORDER:
        reasons = []
        for group in ('selection', 'newyear'):
            if set(groups[group]) != {'observed', 'assumed_missing_zero'}: raise ValueError('separate label scenarios required')
            for mode, scores in groups[group].items():
                if set(scores) != set(ORDER): raise ValueError('fixed candidate comparison required')
                control, candidate = scores['matched_mean28'], scores[method]
                for field, value, limit in (
                    ('quantity_MSE', candidate['quantity']['macro']['MSE'], control['quantity']['macro']['MSE']),
                    ('total_MSE', candidate['macro']['total'], control['macro']['total']),
                    ('under', candidate['shortfall']['macro']['under'], control['shortfall']['macro']['under'])):
                    if not math.isfinite(value) or not math.isfinite(limit): raise ValueError('finite eligibility scores required')
                    if value > limit+1e-12: reasons.append(group+'/'+mode+'/'+field)
                if candidate['shortfall']['max_window_increase_over_matched'] > 1e-12:
                    reasons.append(group+'/'+mode+'/window_shortfall')
        checks[method] = {'eligible': not reasons, 'reasons': reasons}
    if not checks['matched_mean28']['eligible']: raise ValueError('matched baseline must remain eligible')
    selected = ORDER[0]
    for method in ORDER:
        if checks[method]['eligible'] and groups['selection']['observed'][method]['macro']['joint'] < groups['selection']['observed'][selected]['macro']['joint']-1e-12:
            selected = method
    return {'selected': selected, 'eligibility': checks, '2015_used': False}
