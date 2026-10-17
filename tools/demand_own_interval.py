"""Own-store prefix calibration, explicitly distinct from shared/zero-shot use."""
import csv
import datetime as dt
import io
import math
from demand_shared_residual import past_input, observed_target
from demand_shared_interval import calibrate, support
from demand_local_interval import local_scale


def read_prefix(raw, stores):
    histories = {s: {} for s in stores}
    ids = {str(s): s for s in stores}
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8')))
    if reader.fieldnames != ['store_nbr', 'date', 'source_id', 'sales', 'observed']:
        raise ValueError('saved own-prefix schema required')
    for row in reader:
        if row['store_nbr'] not in ids:
            continue
        day = dt.date.fromisoformat(row['date'])
        if not dt.date(2013, 1, 1) <= day < dt.date(2016, 1, 1):
            continue  # Do not convert a later quantity/mask.
        store = ids[row['store_nbr']]
        if day in histories[store] or row['observed'] not in ('0', '1'):
            raise ValueError('duplicate or invalid prefix mask')
        if (row['observed'] == '1') != bool(row['sales']):
            raise ValueError('prefix value/mask mismatch')
        value = float(row['sales']) if row['sales'] else None
        if value is not None and (not math.isfinite(value) or value < 0):
            raise ValueError('invalid prefix quantity')
        histories[store][day] = value
    return histories


def own_window(history, store, origin, prefix_mean):
    if origin+dt.timedelta(days=13) >= dt.date(2016, 1, 1):
        raise ValueError('own calibration label must end before 2016')
    features = past_input(history, origin, prefix_mean)
    target = observed_target(history, origin)
    reasons = features['reasons']+([] if target['available'] else ['label_missing'])
    available = not reasons
    size = local_scale(features['baseline'], prefix_mean) if available else None
    return {'store': store, 'origin': str(origin), 'available': available, 'reasons': reasons,
            'past_positive': features['context_positive_days'] > 0,
            'zero_context': features['context_positive_days'] == 0,
            'baseline': features['baseline'], 'actual_total': target['actual_total'],
            'actual_zero': target['actual_zero'], 'local_scale': size,
            'y': (target['actual_total']-features['baseline'])/size['scale'] if available else None,
            'context_observed': features['context_observed'], 'label_observed': target['observed_days']}


def select_own(rows, store):
    if any(r['store'] != store for r in rows):
        raise ValueError('own calibration cannot include another store')
    if any(type(r['available']) is not bool or type(r['past_positive']) is not bool for r in rows):
        raise ValueError('explicit availability/past-context flags required')
    return [dict(r, weight=1.) for r in rows if r['available'] and r['past_positive']]


def choose_calibration(rows, store, shared):
    selected = select_own(rows, store)
    if len(selected) >= 20:
        own = calibrate(selected)
        return {'target_store': store, 'minimum_support': 20, 'own': own, 'selected': own,
                'interval_source': 'own_history', 'own_calibration_used': True, 'zero_shot_claim': False}
    own = {'q10': None, 'q90': None, 'support': support(selected),
           'reason': 'insufficient_own_support', 'coverage_guarantee_established': False}
    return {'target_store': store, 'minimum_support': 20, 'own': own, 'selected': shared,
            'interval_source': 'shared_fallback', 'own_calibration_used': False, 'zero_shot_claim': False}
