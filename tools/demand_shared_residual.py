"""Store-balanced shared residual regression; past inputs and labels stay separate."""
import datetime as dt
import math


def _valid_quantity(value):
    if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
        raise ValueError('quantity must be finite nonnegative or missing')
    return value


def past_input(history, origin, train_scale):
    past = [(origin-dt.timedelta(days=k), _valid_quantity(history.get(origin-dt.timedelta(days=k))))
            for k in range(1, 57)]
    counts = [sum(d.weekday() == day and v is not None for d, v in past[:28]) for day in range(7)]
    reasons = []
    if sum(v is not None for _, v in past) < 49:
        reasons.append('context_support')
    if min(counts) < 3:
        reasons.append('baseline_weekday_support')
    if type(train_scale) not in (int, float) or not math.isfinite(train_scale) or train_scale <= 0:
        reasons.append('scale_not_positive')
    baseline = None
    if min(counts) >= 3:
        weekday_means = [math.fsum(v for d, v in past[:28] if d.weekday() == day and v is not None)/counts[day]
                         for day in range(7)]
        baseline = math.fsum(weekday_means[(origin+dt.timedelta(days=k)).weekday()] for k in range(14))
    recent = [v for _, v in past[:14]]
    complete = all(v is not None for v in recent)
    x = ((math.fsum(recent)-baseline)/(14*train_scale)
         if not reasons and complete else None)
    return {'available': not reasons, 'reasons': reasons, 'baseline': baseline, 'x': x,
            'recent14_supported': complete, 'context_observed': sum(v is not None for _, v in past),
            'context_positive_days': sum(v is not None and v > 0 for _, v in past),
            'baseline_weekday_support': counts, 'first_date': str(past[-1][0]), 'last_date': str(past[0][0])}


def observed_target(history, origin):
    values = [_valid_quantity(history.get(origin+dt.timedelta(days=k))) for k in range(14)]
    complete = all(v is not None for v in values)
    return {'available': complete, 'observed_days': sum(v is not None for v in values),
            'actual_total': math.fsum(values) if complete else None,
            'actual_zero': all(v == 0 for v in values) if complete else None}


def fit(rows, train_stores):
    stores = tuple(train_stores)
    if not stores or len(set(stores)) != len(stores):
        raise ValueError('distinct declared training stores required')
    keys = set()
    for row in rows:
        key = row['store'], row['origin']
        if row['store'] not in stores or dt.date.fromisoformat(row['origin'])+dt.timedelta(days=13) >= dt.date(2016, 1, 1):
            raise ValueError('row outside training store/time declaration')
        if key in keys:
            raise ValueError('duplicate training window')
        keys.add(key)
        if any(type(row[k]) not in (int, float) or not math.isfinite(row[k]) for k in ('x', 'y')):
            raise ValueError('supported finite training values required')
    counts = {s: sum(r['store'] == s for r in rows) for s in stores}
    if any(n < 10 for n in counts.values()):
        raise ValueError('at least ten supported training windows per declared store')
    n = len(rows)
    weights = [n/(len(stores)*counts[r['store']]) for r in rows]
    weight_sum = math.fsum(weights)
    center = math.fsum(w*r['x'] for w, r in zip(weights, rows))/weight_sum
    scale = math.sqrt(math.fsum(w*(r['x']-center)**2 for w, r in zip(weights, rows))/weight_sum)
    intercept = math.fsum(w*r['y'] for w, r in zip(weights, rows))/weight_sum
    z = [(r['x']-center)/scale for r in rows] if scale > 0 else [0.0]*n
    slope = math.fsum(w*v*(r['y']-intercept) for w, v, r in zip(weights, z, rows))/(math.fsum(w*v*v for w, v in zip(weights, z))+1)
    return {'rows': n, 'train_stores': stores, 'store_counts': counts,
            'store_weight_sums': {s: math.fsum(w for w, r in zip(weights, rows) if r['store'] == s) for s in stores},
            'weight_sum': weight_sum, 'center': center, 'scale': scale,
            'intercept': intercept, 'slope': slope, 'ridge': 1}


def predict(model, baseline, train_scale, x):
    if _valid_quantity(baseline) is None or not math.isfinite(train_scale) or train_scale <= 0:
        raise ValueError('nonnegative baseline and positive fixed scale required')
    if x is not None and not math.isfinite(x):
        raise ValueError('finite feature or missing required')
    z = (x-model['center'])/model['scale'] if x is not None and model['scale'] > 0 else 0.0
    return {'baseline': baseline, 'intercept': max(0.0, baseline+14*train_scale*model['intercept']),
            'shared': max(0.0, baseline+14*train_scale*(model['intercept']+model['slope']*z)),
            'standardized_feature': z, 'feature_supported': x is not None}
