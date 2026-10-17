"""Completed-window calibration, under an explicit next-day label assumption."""
import datetime as dt
import math
from demand_shared_interval import calibrate, support


def select_completed(rows, store, origin):
    """Check headers before accessing flags or residuals; use latest 26 windows."""
    headers = []
    seen = set()
    for row in rows:
        if row['store'] != store:
            raise ValueError('sequential calibration cannot include another store')
        day = dt.date.fromisoformat(row['origin'])
        if day in seen:
            raise ValueError('duplicate calibration origin')
        seen.add(day)
        if day+dt.timedelta(days=13) < origin:
            headers.append((day, row))
    selected = []
    for day, row in sorted(headers, key=lambda pair: pair[0]):
        if type(row['available']) is not bool or type(row['past_positive']) is not bool:
            raise ValueError('explicit availability/past-context flags required')
        if row['available'] and row['past_positive']:
            selected.append((day, row))
    result = []
    for day, row in selected[-26:]:
        residual = row['y']
        if type(residual) not in (int, float) or not math.isfinite(residual):
            raise ValueError('finite completed residual required; missing is not zero')
        result.append({'store': store, 'origin': str(day),
                       'target_end': str(day+dt.timedelta(days=13)),
                       'y': residual, 'weight': 1., 'zero_context': False})
    return result


def pool_signature(rows):
    return tuple((r['store'], r['origin'], r['y'], r['weight']) for r in rows)


def choose_sequential(selected, store, baseline_selected, saved_own, shared):
    if any(r['store'] != store for r in selected+baseline_selected):
        raise ValueError('calibration reuse requires the same store')
    if len(selected) < 20:
        own = {'q10': None, 'q90': None, 'support': support(selected),
               'reason': 'insufficient_completed_support',
               'coverage_guarantee_established': False}
        return {'own': own, 'selected': shared, 'interval_source': 'shared_fallback',
                'quantile_action': 'fallback', 'zero_shot_claim': False}
    reused = pool_signature(selected) == pool_signature(baseline_selected)
    own = saved_own if reused else calibrate(selected)
    return {'own': own, 'selected': own, 'interval_source': 'own_completed_history',
            'quantile_action': 'reuse_saved_own' if reused else 'new_pool',
            'zero_shot_claim': False}
