"""Weighted empirical total-residual intervals; no coverage guarantee or point fit."""
import math


def select_pool(rows, mode):
    if mode not in ('all', 'past_positive'):
        raise ValueError('declared past-only pool required')
    if any(type(r['zero_context']) is not bool for r in rows):
        raise ValueError('explicit past context flag required')
    return [r for r in rows if mode == 'all' or not r['zero_context']]


def support(rows):
    counts, weights = {}, {}
    for row in rows:
        weight = row['weight']
        if type(weight) not in (int, float) or not math.isfinite(weight) or weight <= 0:
            raise ValueError('positive finite inherited weight required')
        store = row['store']
        counts[store] = counts.get(store, 0)+1
        weights[store] = weights.get(store, 0.)+weight
    return {'rows': len(rows), 'store_counts': counts, 'store_weight_sums': weights,
            'weight_sum': math.fsum(r['weight'] for r in rows),
            'zero_context_rows': sum(r['zero_context'] for r in rows)}


def weighted_quantile(pairs, q):
    if type(q) not in (int, float) or not math.isfinite(q) or not 0 < q <= 1:
        raise ValueError('quantile in (0,1] required')
    if not pairs:
        return None
    if any(type(v) not in (int, float) or not math.isfinite(v) or
           type(w) not in (int, float) or not math.isfinite(w) or w <= 0 for v, w in pairs):
        raise ValueError('finite residual and positive finite weight required')
    ordered = sorted(pairs)
    threshold = q*math.fsum(w for _, w in ordered)
    cumulative = 0.
    for value, weight in ordered:
        cumulative += weight
        if cumulative >= threshold:
            return value
    return ordered[-1][0]  # Floating summation at q=1.


def calibrate(rows):
    pairs = [(r['y'], r['weight']) for r in rows]
    return {'q10': weighted_quantile(pairs, .1), 'q90': weighted_quantile(pairs, .9),
            'support': support(rows), 'reason': None if rows else 'empty_pool',
            'coverage_guarantee_established': False}


def total_interval(point, train_scale, calibration):
    if type(point) not in (int, float) or not math.isfinite(point) or point < 0:
        raise ValueError('finite nonnegative original point required')
    if type(train_scale) not in (int, float) or not math.isfinite(train_scale) or train_scale <= 0:
        raise ValueError('positive finite fixed scale required')
    if calibration['q10'] is None or calibration['q90'] is None:
        return {'point': point, 'lower': None, 'upper': None, 'width': None, 'reason': 'empty_pool'}
    lower = max(0., point+14*train_scale*calibration['q10'])
    upper = max(0., point+14*train_scale*calibration['q90'])
    if not math.isfinite(lower) or not math.isfinite(upper) or lower > upper:
        raise ValueError('invalid total interval')
    return {'point': point, 'lower': lower, 'upper': upper, 'width': upper-lower,
            'reason': None, 'point_inside': lower <= point <= upper}


def assess(interval, actual):
    if actual is None or interval['lower'] is None or interval['upper'] is None:
        return None
    if type(actual) not in (int, float) or not math.isfinite(actual) or actual < 0:
        raise ValueError('finite nonnegative actual required')
    lower, upper = interval['lower'], interval['upper']
    below, above = actual < lower, actual > upper
    score = upper-lower+10*(lower-actual if below else actual-upper if above else 0.)
    return {'covered': not below and not above, 'below': below, 'above': above,
            'width': upper-lower, 'interval_score': score}
