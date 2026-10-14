"""Train-prefix data diagnostics; no torch, weights, inference or fitting."""
import csv
import datetime as dt
import io
import math

STORES = (5, 11, 12)
CUTOFF = dt.date(2016, 1, 1)
EVENTS = ((1, 1), (5, 1), (5, 24), (8, 10), (10, 9), (11, 2), (11, 3), (12, 25))


def read_prefix(raw):
    history = {s: {} for s in STORES}
    for row in csv.DictReader(io.StringIO(raw.decode('utf-8'))):
        day = dt.date.fromisoformat(row['date'])
        if day >= CUTOFF:
            continue  # No later numeric quantity or observed-status inspection.
        s = int(row['store_nbr'])
        if s not in history or day in history[s] or row['observed'] not in ('0', '1'):
            raise ValueError('prefix identity/mask mismatch')
        if (row['observed'] == '1') != bool(row['sales']):
            raise ValueError('prefix missing/value mismatch')
        v = float(row['sales']) if row['sales'] else None
        if v is not None and (not math.isfinite(v) or v < 0):
            raise ValueError('prefix invalid quantity')
        history[s][day] = v
    return history


def zero_runs(history, minimum=14):
    runs = []; start = last = None
    for day, value in sorted(history.items()):
        if value == 0 and (last is None or (day-last).days == 1):
            if start is None:
                start = day
            last = day
            continue
        if start is not None and (last-start).days+1 >= minimum:
            runs.append({'start': str(start), 'end': str(last), 'days': (last-start).days+1})
        start = last = day if value == 0 else None
    if start is not None and (last-start).days+1 >= minimum:
        runs.append({'start': str(start), 'end': str(last), 'days': (last-start).days+1})
    return runs


def overlaps(first, last, runs):
    return any(first <= dt.date.fromisoformat(r['end']) and last >= dt.date.fromisoformat(r['start']) for r in runs)


def same_weekday(history, day):
    values = [history.get(day-dt.timedelta(days=k)) for k in (7, 14, 21, 28)]
    values = [v for v in values if v is not None]
    return math.fsum(values)/len(values) if values else None


def reference_window(history, origin, train_scale, runs):
    if origin+dt.timedelta(days=13) >= CUTOFF or train_scale <= 0:
        raise ValueError('label outside prefix or invalid fixed scale')
    actual = [history.get(origin+dt.timedelta(days=k)) for k in range(14)]
    # Baseline uses a single origin-past28 context, never rolling future labels.
    past = {d: v for d, v in history.items() if origin-dt.timedelta(days=28) <= d < origin and v is not None}
    baseline = []
    for k in range(14):
        day = origin+dt.timedelta(days=k)
        values = [v for d, v in past.items() if d.weekday() == day.weekday()]
        baseline.append(math.fsum(values)/len(values) if values else None)
    if any(v is None for v in actual+baseline):
        raise ValueError('saved eligible origin has incomplete support')
    point, total = math.fsum(baseline), math.fsum(actual)
    scale = max(point, .01*14*train_scale)
    quantiles = [.8*scale, scale, 1.2*scale]
    weights = [v+.01*train_scale for v in baseline]; denominator = math.fsum(weights)
    initial_daily = [scale*w/denominator for w in weights]
    pinball = math.fsum(max(q*(total-p), (q-1)*(total-p)) for q, p in zip((.1, .5, .9), quantiles))/3/(14*train_scale)
    daily_loss = math.fsum(abs(p-a) for p, a in zip(initial_daily, actual))/14/train_scale
    label = overlaps(origin, origin+dt.timedelta(days=13), runs)
    context = overlaps(origin-dt.timedelta(days=56), origin-dt.timedelta(days=1), runs)
    return {'origin': str(origin), 'baseline': baseline, 'actual': actual, 'point_total': point,
            'actual_total': total, 'total_error': point-total,
            'daily_absolute_error': math.fsum(abs(p-a) for p, a in zip(baseline, actual)),
            'initial_total_pinball_scaled': pinball, 'initial_daily_mae_scaled': daily_loss,
            'initial_objective': .5*(pinball+daily_loss),
            'exposure': 'label' if label else 'context_only' if context else 'neither',
            'label_zero_days': sum(v == 0 for v in actual)}


def group(rows):
    n = len(rows); actual = math.fsum(r['actual_total'] for r in rows)
    absolute_total = math.fsum(abs(r['total_error']) for r in rows)
    return {'windows': n, 'actual_quantity': actual,
            'daily_absolute_error': math.fsum(r['daily_absolute_error'] for r in rows),
            'total_absolute_error': absolute_total,
            'total_WAPE': 100*absolute_total/actual if actual > 0 else None,
            'initial_objective_sum': math.fsum(r['initial_objective'] for r in rows),
            'initial_objective_mean': math.fsum(r['initial_objective'] for r in rows)/n if n else None,
            'zero_label_days_with_overlap': sum(r['label_zero_days'] for r in rows),
            'overlapping_labels_not_independent': True}
