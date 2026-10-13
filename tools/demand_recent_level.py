"""One fixed public-data research candidate: recent same-weekday mean.

No annual extrapolation, future promotion, parameter search or learned weights.
"""
import datetime as dt
import hashlib
import json
import math
from demand_forecasting import past_observations


def recent_forecasts(history, origin, *, include_weekly_naive=False):
    past = dict(past_observations(history, origin))
    start = origin - dt.timedelta(days=28)
    recent = {date: value for date, value in past.items() if date >= start}
    rows = []
    for lead in range(1, 15):
        target = origin + dt.timedelta(days=lead-1)
        dates = sorted(date for date in recent if date.weekday() == target.weekday())
        mean = math.fsum(recent[date] for date in dates)/len(dates) if dates else None
        row = {'date': str(target), 'lead': lead, 'weekday_mean_28': mean,
            'mean_source_dates': [str(date) for date in dates], 'mean_support': len(dates),
            'mean_missing_reason': None if dates else 'no_observed_same_weekday_in_past_28_days'}
        if include_weekly_naive:
            row.update(weekly_naive=recent[dates[-1]] if dates else None,
                naive_source_date=str(dates[-1]) if dates else None,
                naive_missing_reason=None if dates else 'no_observed_same_weekday_within_28_days')
        rows.append(row)
    input_raw = json.dumps([[str(date), value] for date, value in sorted(recent.items())],
                           separators=(',', ':'), allow_nan=False).encode('utf-8')
    return {'origin': str(origin), 'window_start': str(start), 'window_end': str(origin-dt.timedelta(days=1)),
        'observed_window_days': len(recent), 'input_sha256': hashlib.sha256(input_raw).hexdigest(),
        'predictions': rows, 'weekly_naive_computed': include_weekly_naive}
