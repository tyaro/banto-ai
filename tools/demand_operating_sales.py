"""Known-open weekday levels and conditional sales means; no fitting or IO."""
import datetime as dt
import math

from demand_event_calendar import _aware, _versions
from demand_event_intervals import _date, _operating_calendar
from demand_weekly_history import quantity


def _calendar(records, as_of, store):
    as_of = _aware(as_of)
    if type(store) is not int:
        raise ValueError('integer store identity required')
    selected, excluded = _versions(records, as_of)
    return _operating_calendar(selected, store), excluded


def estimate_open_levels(history, operating_records, origin, as_of, store,
                         lookback=28, min_support=3):
    """History must already be available as of the supplied local timestamp.

    Unknown observations are retained in a separate reference, never silently
    classified as closed or used as fallback for the strict open-only mean.
    """
    origin = _date(origin)
    as_of = _aware(as_of)
    if as_of.date() > origin:
        raise ValueError('availability cutoff must not follow prediction origin')
    if type(lookback) is not int or lookback <= 0 or type(min_support) is not int or min_support <= 0:
        raise ValueError('positive lookback and support required')
    calendar, excluded = _calendar(operating_records, as_of, store)
    open_values, reference = [[] for _ in range(7)], [[] for _ in range(7)]
    ledger = []
    for offset in range(lookback, 0, -1):
        day = origin-dt.timedelta(days=offset)
        raw = history.get(day)
        value = None if raw is None else quantity(raw)
        status = calendar.get(day, 'unknown')
        if status == 'closed' and value is not None and value > 0:
            raise ValueError('closed nonzero observation contradicts sales calendar')
        if value is None:
            reason = 'missing'
        elif status == 'closed':
            reason = 'closed_observed_zero'
        elif status == 'unknown':
            reference[day.weekday()].append(value)
            reason = 'operating_unknown_observation'
        else:
            open_values[day.weekday()].append(value)
            reference[day.weekday()].append(value)
            reason = 'open_observation'
        ledger.append({'date':str(day), 'quantity':value, 'observed':value is not None,
                       'operating_status':status, 'reason':reason})
    levels = []
    for weekday in range(7):
        values, mixed = open_values[weekday], reference[weekday]
        supported = len(values) >= min_support
        levels.append({'weekday':weekday, 'open_observed_count':len(values),
                       'open_day_mean':math.fsum(values)/len(values) if supported else None,
                       'reason':None if supported else 'open_weekday_support',
                       'open_unknown_observed_count':len(mixed),
                       'open_unknown_reference_mean':math.fsum(mixed)/len(mixed) if len(mixed)>=min_support else None})
    return {'origin':str(origin), 'as_of':as_of.isoformat(), 'store':store,
            'past_start':ledger[0]['date'], 'past_end':ledger[-1]['date'],
            'lookback':lookback, 'min_support':min_support, 'weekdays':levels,
            'history_ledger':ledger, 'excluded_operating_versions':excluded,
            'unknown_reference_used_as_fallback':False, 'original_history_changed':False}


def apply_operating_sales(open_day_means, operating_records, days, as_of, store,
                          *, closed_implies_zero):
    """Means on unknown operating days are conditional on assumed operation.

    This is a point-mean composer, not a quantile summation interface.
    """
    as_of = _aware(as_of)
    if not days or any(type(d) is not dt.date for d in days) or len(set(days)) != len(days):
        raise ValueError('distinct local forecast dates required')
    if as_of.date() > min(days):
        raise ValueError('availability cutoff must not follow forecast start')
    if type(closed_implies_zero) is not bool:
        raise ValueError('explicit closure zero contract required')
    calendar, excluded = _calendar(operating_records, as_of, store)
    rows = []
    for day in days:
        status = calendar.get(day, 'unknown')
        if status == 'closed':
            value = 0.0 if closed_implies_zero else None
            reason = 'confirmed_closed_zero' if closed_implies_zero else 'closure_zero_contract_absent'
        else:
            raw = open_day_means.get(day)
            value = None if raw is None else quantity(raw)
            reason = 'open_day_mean_unavailable' if value is None else 'open_mean' if status == 'open' else 'conditional_on_open'
        rows.append({'date':str(day), 'operating_status':status,
                     'sales_mean':value, 'reason':reason,
                     'conditional_on_open':status=='unknown'})
    available = all(row['sales_mean'] is not None for row in rows)
    conditional = any(row['conditional_on_open'] for row in rows)
    total = math.fsum(row['sales_mean'] for row in rows) if available else None
    return {'as_of':as_of.isoformat(), 'store':store, 'daily':rows,
            'total_sales_mean':total, 'total_available':available,
            'total_conditional_on_unknown_days_open':conditional,
            'closed_implies_zero':closed_implies_zero,
            'excluded_operating_versions':excluded, 'original_observations_changed':False}
