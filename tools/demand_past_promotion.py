"""Past-only recorded promotion features; no future-plan inference or model fit."""
import datetime as dt
import math


def parse_count(text):
    if text == '':
        return None
    if not isinstance(text, str) or not text.isascii() or not text.isdecimal():
        raise ValueError('promotion count must be a nonnegative ASCII integer or empty')
    return int(text)


def past_features(history, origin):
    dates = [origin - dt.timedelta(days=k) for k in range(28, 0, -1)]
    values = [history.get(d) for d in dates]
    if any(v is not None and (type(v) is not int or v < 0) for v in values):
        raise ValueError('invalid recorded promotion count')
    last = values[-7:]
    support7 = sum(v is not None for v in last)
    support28 = sum(v is not None for v in values)
    mean7 = math.fsum(last)/7 if support7 == 7 else None
    mean28 = math.fsum(values)/28 if support28 == 28 else None
    delta = mean7 - mean28 if mean7 is not None and mean28 is not None else None
    return {'first_date': str(dates[0]), 'last_date': str(dates[-1]),
            'support7': support7, 'support28': support28, 'mean7': mean7,
            'mean28': mean28, 'delta': delta,
            'recent_state': ('insufficient' if support7 < 7 else
                             'positive' if any(v > 0 for v in last) else 'recorded_zero'),
            'change_state': ('insufficient' if delta is None else
                             'up' if delta > 0 else 'down' if delta < 0 else 'equal')}


def describe(rows):
    errors = [r['residual_scaled'] for r in rows]
    ordered = sorted(errors)
    n = len(errors)
    median = (ordered[n//2] if n % 2 else (ordered[n//2-1]+ordered[n//2])/2) if n else None
    valid = [(r['promotion']['delta'], r['residual_scaled']) for r in rows
             if r['promotion']['delta'] is not None]
    correlation = None
    if len(valid) >= 2:
        mx = math.fsum(x for x, _ in valid)/len(valid)
        my = math.fsum(y for _, y in valid)/len(valid)
        xx = math.fsum((x-mx)**2 for x, _ in valid)
        yy = math.fsum((y-my)**2 for _, y in valid)
        if xx > 0 and yy > 0:
            correlation = math.fsum((x-mx)*(y-my) for x, y in valid)/math.sqrt(xx*yy)
    return {'n': n, 'mean_residual_scaled': math.fsum(errors)/n if n else None,
            'median_residual_scaled': median,
            'RMSE_scaled': math.sqrt(math.fsum(e*e for e in errors)/n) if n else None,
            'delta_pairs': len(valid), 'delta_residual_Pearson': correlation}
