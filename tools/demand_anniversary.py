"""Fixed shrunk nominal-anniversary correction from observed prefix only."""
import datetime as dt
import math
from demand_forecasting import finite_quantity


def fit_anniversaries(anniversaries, cutoff=dt.date(2016, 1, 1)):
    if cutoff != dt.date(2016, 1, 1):
        raise ValueError('fixed prefix cutoff required')
    result = {s: {} for s in (1, 2, 3)}
    for anniversary in anniversaries:
        month_day = anniversary['month_day']
        # Month/day keys were extracted from the 2013-2015 holiday prefix.
        dt.date.fromisoformat('2015-'+month_day)
        for store in result:
            rows = []
            for row in anniversary['rows']:
                date = dt.date.fromisoformat(row['date'])
                if date >= cutoff or row['store'] != store:
                    continue
                if str(date)[5:] != month_day:
                    raise ValueError('anniversary row/key mismatch')
                actual, baseline = row['sales'], row['past_same_weekday_mean']
                if actual is None or baseline is None:
                    continue
                actual, baseline = finite_quantity(actual), finite_quantity(baseline)
                if baseline > 0 and row['support'] >= 3:
                    rows.append((row['date'], actual, baseline))
            if len(rows) >= 2:
                ratio = math.fsum(r[1] for r in rows)/math.fsum(r[2] for r in rows)
                weight = len(rows)/(len(rows)+3)
                factor = 1 + weight*(ratio-1)
                reason = None
            else:
                ratio, weight, factor, reason = None, 0., 1., 'insufficient_observed_anniversary_support'
            if month_day in result[store]:
                raise ValueError('duplicate nominal month/day')
            result[store][month_day] = {'factor': factor, 'ratio': ratio, 'weight': weight,
                'support': len(rows), 'source_dates': [r[0] for r in rows], 'reason': reason,
                'is_confirmed_closure': False}
    return result


def correct_baseline(model, store, date, baseline):
    entry = model[store].get(str(date)[5:])
    factor = entry['factor'] if entry else 1.
    return {'prediction': finite_quantity(baseline)*factor if baseline is not None else None,
        'factor': factor, 'anniversary': str(date)[5:] if entry else None,
        'support': entry['support'] if entry else 0,
        'reason': entry['reason'] if entry else 'not_a_prefix_nominal_anniversary',
        'is_confirmed_closure': False}
