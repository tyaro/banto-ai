"""Pre-2015 seasonal calibration with explicit missing daily and total support."""
import datetime as dt
import math
from demand_autonomous_mean import FIT
from demand_frozen_recent_quantity import select_recent, fit_forecast

ORDER = ('matched_mean28', 'open_mean28', 'seasonal_level', 'recent_gated_ridge')


def validation_keys():
    return [(s, str(dt.date(2014, 1, 1)+dt.timedelta(days=14*k))) for k in range(26) for s in FIT]


def quarter(text):
    return (dt.date.fromisoformat(text).month-1)//3+1


def scales_2013(history):
    scales, evidence = {}, {}
    for s in FIT:
        values = [v for day, v in history[s].items() if day.year == 2013]
        if len(values) != 364 or any(not math.isfinite(v) or v < 0 for v in values):
            raise ValueError('complete 2013 observation support required')
        scales[s] = math.fsum(values)/len(values)
        if scales[s] <= 0: raise ValueError('positive 2013 scale required')
        evidence[str(s)] = {'scale': scales[s], 'observed': len(values),
                            'zeros': sum(v == 0 for v in values), 'last_allowed': '2013-12-31'}
    return scales, evidence


def complete_recent(pool, origin):
    selected = select_recent(pool, origin)  # Reject future/foreign metadata before labels.
    return [p for p in selected if len(p['actual']) == 14 and all(v is not None for v in p['actual'])]


def fit_past(pool, current, guard=lambda: None):
    return fit_forecast(complete_recent(pool, dt.date.fromisoformat(current[0]['origin'])), current, guard)


def coefficient(rows, directions, upper):
    if len(rows) != len(directions) or not rows: raise ValueError('calibration support required')
    daily_d, daily_r, total_d, total_r = [], [], [], []
    for row, direction in zip(rows, directions):
        if len(direction) != 14 or len(row['actual']) != 14: raise ValueError('fixed calibration horizon')
        residual = [(a-b)/row['scale'] if a is not None else None for a, b in zip(row['actual'], row['open_mean28'])]
        for d, r in zip(direction, residual):
            if r is not None: daily_d.append(d); daily_r.append(r)
        if all(v is not None for v in residual):
            total_d.append(math.fsum(direction)/14); total_r.append(math.fsum(residual)/14)
    if not daily_d or not total_d: raise ValueError('both daily and complete-total support required')
    ed = math.fsum(v*v for v in daily_d)/len(daily_d)
    cd = math.fsum(d*r for d, r in zip(daily_d, daily_r))/len(daily_d)
    et = math.fsum(v*v for v in total_d)/len(total_d)
    ct = math.fsum(d*r for d, r in zip(total_d, total_r))/len(total_d)
    bound = upper
    for e, c in ((ed, cd), (et, ct)):
        if e > 0: bound = min(bound, max(0., 2*c/e))
    value = max(0., min(bound, (cd+ct)/(ed+et))) if ed+et > 0 else 0.
    if not all(math.isfinite(v) for v in (ed, cd, et, ct, value)): raise ValueError('invalid calibration')
    return {'value': value, 'upper': bound, 'daily_energy': ed, 'daily_covariance': cd,
            'total_energy': et, 'total_covariance': ct, 'daily_support': len(daily_d),
            'complete_totals': len(total_d)}


def calibrate_seasons(rows):
    alpha = coefficient(rows, [[(p-b)/r['scale'] for p, b in zip(r['raw_prediction'], r['open_mean28'])] for r in rows], 1.)
    levels = {}
    for q in range(1, 5):
        selected = [r for r in rows if quarter(r['origin']) == q]
        levels[str(q)] = coefficient(selected, [[float(v) for v in r['open_mask']] for r in selected], float('inf'))
    return {'alpha': alpha, 'quarter_levels': levels, '2015_used': False}


def alternatives(row, calibration):
    delta = calibration['quarter_levels'][str(quarter(row['origin']))]['value']
    alpha = calibration['alpha']['value']
    return {'matched_mean28': list(row['matched_mean28']), 'open_mean28': list(row['open_mean28']),
            'seasonal_level': [b+delta*row['scale'] if good else 0. for b, good in zip(row['open_mean28'], row['open_mask'])],
            'recent_gated_ridge': [b+alpha*(p-b) for p, b in zip(row['raw_prediction'], row['open_mean28'])]}


def choose(scores):
    if set(scores) != set(ORDER): raise ValueError('fixed four-way comparison required')
    best = ORDER[0]
    for name in ORDER:
        if not math.isfinite(scores[name]['joint']): raise ValueError('unsupported selection score')
        if scores[name]['joint'] < scores[best]['joint']-1e-12: best = name
    return best


def score_rows(rows, prediction):
    from demand_macos_rebuild import eval_metrics
    per_store = {}
    quantity = {}
    for s in FIT:
        selected = [dict(r, candidate=prediction(r)) for r in rows if r['store'] == s]
        if not selected: raise ValueError('all ten stores required')
        per_store[str(s)] = eval_metrics(selected, selected[0]['scale'], 'candidate')
        errors = [(p-a, r['scale']) for r in selected for p, a, flag in zip(r['candidate'], r['actual'], r['assumed_closure']) if a is not None and not flag]
        quantity[str(s)] = {'count': len(errors), 'MSE': math.fsum((e/u)**2 for e, u in errors)/len(errors),
                            'MAE': math.fsum(abs(e) for e, u in errors)/len(errors), 'bias': math.fsum(e for e, u in errors)/len(errors)}
    fields = ('daily', 'total', 'joint', 'daily_MAE', 'total_MAE', 'daily_bias', 'total_bias')
    macro = {k: math.fsum(v[k] for v in per_store.values())/10 if all(v[k] is not None for v in per_store.values()) else None for k in fields}
    return {'macro': macro, 'per_store': per_store, 'quantity': {'observed_nonclosure_days': sum(v['count'] for v in quantity.values()),
            'macro': {k: math.fsum(v[k] for v in quantity.values())/10 for k in ('MSE', 'MAE', 'bias')}},
            'daily_support': sum(sum(v is not None for v in r['actual']) for r in rows),
            'complete_totals': sum(r['complete_label'] for r in rows), 'windows': len(rows)}
