"""One-store past-week inputs; no fitting, labels, forecasting or external IO."""
import datetime as dt
import math


def quantity(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError('finite nonnegative quantity required')
    return float(value)


def fit_scale(rows, store, cutoff=dt.date(2015, 1, 1)):
    """Only declared-store 2013..cutoff quantities may determine the scale."""
    values = []
    seen = set()
    for row in rows:
        if row['store'] != store:
            continue
        day = dt.date.fromisoformat(row['date'])
        if not dt.date(2013, 1, 1) <= day < cutoff:
            continue
        if day in seen or type(row['observed']) is not bool:
            raise ValueError('duplicate scale date or invalid observation flag')
        seen.add(day)
        if row['observed']:
            values.append(quantity(row['quantity']))
        elif row['quantity'] is not None:
            raise ValueError('missing scale quantity must be null')
    mean = math.fsum(values)/len(values) if values else None
    reason = 'no_observed_fit_quantity' if mean is None else 'nonpositive_fit_scale' if mean <= 0 else None
    return {'store': store, 'cutoff_exclusive': str(cutoff), 'observed_days': len(values),
            'mean': mean, 'available': reason is None, 'reason': reason}


def build_inputs(history, origin, scale):
    if type(origin) is not dt.date:
        raise ValueError('prediction date required')
    u = quantity(scale)
    days = [origin-dt.timedelta(days=k) for k in range(56, 0, -1)]
    raw = [history.get(day) for day in days]
    observed = [v is not None for v in raw]
    values = [quantity(v) if good else None for v, good in zip(raw, observed)]
    counts = [sum(d.weekday() == w and good for d, good in zip(days[-28:], observed[-28:])) for w in range(7)]
    baseline = None
    if min(counts) >= 3:
        weekday_means = [math.fsum(v for d, v in zip(days[-28:], values[-28:])
                                  if d.weekday() == w and v is not None)/counts[w] for w in range(7)]
        baseline = math.fsum(weekday_means[(origin+dt.timedelta(days=k)).weekday()] for k in range(14))
    weeks = []
    for k in range(8):
        subset = values[7*k:7*k+7]
        count = sum(v is not None for v in subset)
        weeks.append({'first': str(days[7*k]), 'last': str(days[7*k+6]),
                      'observed_days': count, 'total': math.fsum(subset) if count == 7 else None})
    reasons = []
    if u <= 0:
        reasons.append('nonpositive_fit_scale')
    if baseline is None:
        reasons.append('baseline_weekday_support')
    if any(w['observed_days'] < 7 for w in weeks):
        reasons.append('weekly_support')
    features = [(w['total']-baseline/2)/(7*u) for w in weeks] if not reasons else None
    recent_supported = all(v is not None for v in values[-14:])
    old_x = ((math.fsum(values[-14:])-baseline)/(14*u)
             if u > 0 and baseline is not None and sum(observed) >= 49 and recent_supported else None)
    return {'origin': str(origin), 'past_start': str(days[0]), 'past_end': str(days[-1]),
            'baseline': baseline, 'baseline_available': baseline is not None,
            'baseline_weekday_support': counts, 'weeks': weeks, 'features': features,
            'available': not reasons, 'reasons': reasons, 'old_x': old_x,
            'fallback': 'baseline' if reasons and baseline is not None else 'unavailable' if reasons else None}
