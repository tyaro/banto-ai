"""One fixed direct ridge comparison of own versus related past quantities.

Observed civil dates only; no future store quantity, promotion or tuning.
"""
import datetime as dt
import hashlib
import json
import math
from demand_forecasting import past_observations


def available_window(history, origin):
    start = origin - dt.timedelta(days=28)
    past = {date: value for date, value in past_observations(history, origin) if date >= start}
    raw = json.dumps([[str(d), v] for d, v in sorted(past.items())], separators=(',', ':'), allow_nan=False).encode()
    return {'values': past, 'input_sha256': hashlib.sha256(raw).hexdigest()}


def level_features(window, origin, target):
    if not origin <= target < origin + dt.timedelta(days=14):
        raise ValueError('target must be within fixed fourteen-day horizon')
    past = window['values']
    if any(not origin-dt.timedelta(days=28) <= d < origin for d in past):
        raise ValueError('window contains unavailable date')
    weekday = [v for d, v in past.items() if d.weekday() == target.weekday()]
    last = [v for d, v in past.items() if d >= origin-dt.timedelta(days=7)]
    previous = [v for d, v in past.items() if origin-dt.timedelta(days=14) <= d < origin-dt.timedelta(days=7)]
    support = [len(weekday), len(last), len(previous)]
    if support[0] < 3 or min(support[1:]) < 6:
        return {'features': None, 'support': support, 'reason': 'insufficient_observed_window'}
    return {'features': [math.fsum(weekday)/len(weekday), math.fsum(last)/len(last),
                         math.fsum(previous)/len(previous)], 'support': support, 'reason': None}


def comparison_features(windows, store, origin, target, *, related):
    own = level_features(windows[store], origin, target)
    if own['features'] is None:
        return None
    features = [*own['features'], float((target-origin).days >= 7)]
    if related:
        for peer in sorted(windows):
            if peer == store:
                continue
            levels = level_features(windows[peer], origin, target)
            if levels['features'] is None:
                return None
            features.extend(levels['features'])
    return features
