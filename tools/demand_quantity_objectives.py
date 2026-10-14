"""Finite distribution examples and train descriptions, never forecast fitting."""
import math
import statistics


def number(value, *, nonnegative=False):
    if type(value) not in (int, float) or not math.isfinite(value) or (nonnegative and value < 0):
        raise ValueError('finite numeric value required')
    return float(value)


def distribution(rows):
    values = [(number(v, nonnegative=True), number(w, nonnegative=True)) for v, w in rows]
    if not values or any(w == 0 for _, w in values):
        raise ValueError('positive probability weights required')
    total = math.fsum(w for _, w in values)
    if not math.isfinite(total) or total <= 0:
        raise ValueError('invalid probability weight total')
    return sorted(values), total


def quantile(rows, level):
    level = number(level)
    if not 0 < level < 1:
        raise ValueError('quantile level must be inside (0,1)')
    values, total = distribution(rows)
    for i, (v, _) in enumerate(values):
        if math.fsum(w for _, w in values[:i+1]) >= level*total:
            return v
    return values[-1][0]


def expected_metrics(rows, point):
    point = number(point, nonnegative=True)
    values, total = distribution(rows)
    mean = math.fsum(v*w for v, w in values)/total
    return {'mean': mean, 'bias': point-mean,
            'expected_absolute_error': math.fsum(w*abs(point-v) for v, w in values)/total,
            'expected_squared_error': math.fsum(w*(point-v)**2 for v, w in values)/total}


def decision_quantity(rows, underage_cost, overage_cost):
    # Unknown business costs never imply symmetric costs or a default p90.
    distribution(rows)
    if underage_cost is None or overage_cost is None:
        return {'quantity': None, 'quantile_level': None, 'reason': 'unknown_underage_or_overage_cost'}
    cu, co = number(underage_cost), number(overage_cost)
    if cu <= 0 or co <= 0:
        raise ValueError('positive marginal costs required for this simple model')
    level = cu/(cu+co)
    q = quantile(rows, level); values, total = distribution(rows)
    cost = math.fsum(w*(cu*max(v-q, 0)+co*max(q-v, 0)) for v, w in values)/total
    return {'quantity': q, 'quantile_level': level, 'expected_cost': cost,
            'reason': None, 'model': 'single-period unconstrained linear marginal costs',
            'business_costs_are_illustrative': True}


def describe(values):
    values = [number(v) for v in values]
    if not values:
        return {'n': 0, 'mean': None, 'median': None, 'std': None, 'reason': 'no_valid_rows'}
    mean = math.fsum(values)/len(values)
    return {'n': len(values), 'mean': mean, 'median': statistics.median(values),
            'std': math.hypot(*[v-mean for v in values])/math.sqrt(len(values)),
            'min': min(values), 'max': max(values), 'reason': None}
