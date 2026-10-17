"""Origin-past demand inputs with explicit level, variation and nominal events.

No fitting, labels, forecasting, Torch, operating-calendar inference or IO.
"""
import datetime as dt
import math

STORES = (5, 11, 12)
EVENTS = ((1, 1), (5, 1), (5, 24), (8, 10), (10, 9), (11, 2), (11, 3), (12, 25))
EVENT_KEYS = tuple(f'{m:02}-{d:02}' for m, d in EVENTS)


def quantity(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError('finite nonnegative numeric quantity required')
    return float(value)


def calendar(day):
    year_days = (dt.date(day.year+1, 1, 1)-dt.date(day.year, 1, 1)).days
    annual = 2*math.pi*(day-dt.date(day.year, 1, 1)).days/year_days
    weekly = 2*math.pi*day.weekday()/7
    return [math.sin(weekly), math.cos(weekly), math.sin(annual), math.cos(annual),
            *[float((day.month, day.day) == event) for event in EVENTS]]


def training_support(rows, cutoff):
    """Count distinct observed training-label dates, not origin repetitions.

    Rows are the saved training support ledger; numbers are inspected only
    after the cutoff check. Counts are metadata, never forecasting features.
    """
    counts = {s: {key: 0 for key in EVENT_KEYS} for s in STORES}
    seen = set()
    for row in rows:
        day = dt.date.fromisoformat(row['date'])
        if day >= cutoff:
            continue
        s = row['store']; event = row['event']
        if type(s) is not int or s not in counts or event not in EVENT_KEYS:
            raise ValueError('invalid training support identity')
        if event != day.strftime('%m-%d') or type(row['observed']) is not bool:
            raise ValueError('support date/event/mask mismatch')
        if (s, day) in seen:
            raise ValueError('duplicate training support store/date')
        seen.add((s, day))
        if row['observed'] and row['included_train_origins']:
            quantity(row['actual'])  # Observed zero remains valid support.
            counts[s][event] += 1
    return counts


def build_inputs(histories, origin, train_scales, support):
    if type(origin) is not dt.date or set(histories) != set(STORES) or set(train_scales) != set(STORES) or set(support) != set(STORES):
        raise ValueError('date and exact store mapping required')
    past_days = [origin-dt.timedelta(days=k) for k in range(56, 0, -1)]
    future_days = [origin+dt.timedelta(days=k) for k in range(14)]
    stores = {}
    for s in STORES:
        u = quantity(train_scales[s])
        if u <= 0 or set(support[s]) != set(EVENT_KEYS) or any(type(n) is not int or n < 0 for n in support[s].values()):
            raise ValueError('positive train scale and complete integer support required')
        # Only these 56 get calls can read quantities; future dates are calendar only.
        raw = [histories[s].get(day) for day in past_days]
        observed = [v is not None for v in raw]
        values = [quantity(v) if good else 0. for v, good in zip(raw, observed)]
        kept = [v for v, good in zip(values, observed) if good]
        stats = None; mean = std = None
        if kept:
            mean = math.fsum(kept)/len(kept)
            std = math.hypot(*[v-mean for v in kept])/math.sqrt(len(kept))
            stats = [mean/u, std/max(mean, .01*u)]
            if not all(math.isfinite(v) for v in stats):
                raise ValueError('nonfinite context statistics')
        baseline = []
        for day in future_days:
            kept_weekday = [v for d, v, good in zip(past_days[-28:], values[-28:], observed[-28:])
                            if good and d.weekday() == day.weekday()]
            baseline.append(math.fsum(kept_weekday)/len(kept_weekday) if kept_weekday else None)
        events = []
        for day in future_days:
            key = day.strftime('%m-%d')
            n = support[s][key] if key in EVENT_KEYS else None
            events.append({'date': str(day), 'event': key if key in EVENT_KEYS else None,
                           'training_store_days': n, 'support_status': 'not_event' if n is None else
                           'no_observed_training_labels' if n == 0 else 'few_training_dates',
                           'quantity_effect_verified': False, 'operating_status_known': False})
        reason = 'no_observed_context' if stats is None else 'no_weekday_support' if None in baseline else None
        stores[s] = {'values': values, 'observed': observed, 'context_statistics': stats,
                     'context_mean': mean, 'context_std': std, 'baseline': baseline,
                     'available': reason is None, 'reason': reason, 'future_event_metadata': events}
    return {'origin': str(origin), 'past_end': str(origin-dt.timedelta(days=1)),
            'past_calendar': [calendar(day) for day in past_days],
            'future_calendar': [calendar(day) for day in future_days],
            'stores': stores, 'available': all(row['available'] for row in stores.values())}
