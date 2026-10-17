"""Separate a fixed horizon total from nominal-calendar daily allocation."""
import math
from demand_forecasting import finite_quantity


def redistribute_fourteen(baseline, factors):
    if len(baseline) != 14 or len(factors) != 14:
        raise ValueError('fixed fourteen-day vectors required')
    if any(value is None for value in baseline):
        return {'predictions': [None]*14, 'reason': 'incomplete_baseline_vector',
                'baseline_total': None, 'allocated_total': None, 'normalization_scale': None, 'total_drift': None}
    values = [finite_quantity(value) for value in baseline]
    weights = [finite_quantity(value) for value in factors]
    total = math.fsum(values)
    shaped = [finite_quantity(value*weight) for value, weight in zip(values, weights)]
    shape_total = math.fsum(shaped)
    if total == 0 or all(weight == 1. for weight in weights):
        predictions, scale, reason = values, 1., None
    elif shape_total == 0:
        predictions, scale, reason = [None]*14, None, 'zero_allocation_weight_with_positive_total'
    else:
        scale = total/shape_total
        predictions = [finite_quantity(value*scale) for value in shaped]
        reason = None
    allocated = math.fsum(predictions) if reason is None else None
    if allocated is not None and not math.isclose(allocated, total, rel_tol=1e-12, abs_tol=1e-9):
        raise ArithmeticError('allocation total changed beyond floating-point tolerance')
    return {'predictions': predictions, 'reason': reason, 'baseline_total': total,
            'allocated_total': allocated, 'normalization_scale': scale,
            'total_drift': allocated-total if allocated is not None else None}
