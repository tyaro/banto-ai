"""Independently calibrated quarterly coefficients for fixed consensus endpoints."""
import datetime as dt
import math
from demand_autonomous_mean import FIT
from demand_adaptive_consensus import ORDER, candidates, measure, choose
from demand_seasonal_quantity import quarter


def separate_coefficients(calibration):
    previous = calibration['policy']; journals = calibration['sample_journal']
    if not previous['observed_only'] or previous['2015_used']: raise ValueError('observed pre-2015 source required')
    coefficients = {}
    for q in range(1, 5):
        coefficients[str(q)] = {}
        for method in ORDER:
            constraint = previous['quarter_constraints'][str(q)][method]
            samples = journals[str(q)][method]
            for row in samples:
                if row['store'] not in FIT or not row['origin'].startswith('2014-') or dt.date.fromisoformat(row['origin'])+dt.timedelta(days=13) >= dt.date(2015, 1, 1):
                    raise ValueError('past fixed-store calibration metadata required')
            a, c, upper = constraint['energy'], constraint['covariance'], constraint['upper']
            if not all(math.isfinite(v) for v in (a, c, upper)) or a < 0 or not 0 <= upper <= 1:
                raise ValueError('finite supported quarterly optimization required')
            alpha = max(0., min(upper, c/a)) if a > 1e-24 else 0.
            changes = {}
            for side, sg in (('under', -1.), ('over', 1.)):
                changes[side] = math.fsum(r['weight']*(max(sg*(r['e']+alpha*r['D']), 0.)-max(sg*r['e'], 0.)) for r in samples)
                if changes[side] > 1e-8: raise ValueError('quarterly side constraint failed')
            changes['MSE'] = a*alpha**2-2*c*alpha
            if changes['MSE'] > 1e-12: raise ValueError('quarterly MSE constraint failed')
            counts = {str(s): sum(r['store'] == s for r in samples) for s in FIT}
            if counts != constraint['per_store'] or sum(counts.values()) != constraint['complete_windows'] or any(n == 0 for n in counts.values()):
                raise ValueError('fixed complete calibration support changed')
            nonzero = [r for r in samples if abs(r['D']) > 1e-8]
            coefficients[str(q)][method] = {'alpha': alpha, 'unconstrained': c/a if a > 1e-24 else 0.,
                'energy': a, 'covariance': c, 'upper': upper, 'calibration_changes': changes,
                'complete_windows': len(samples), 'per_store': counts, 'nonzero_direction_windows': len(nonzero),
                'nonzero_direction_origins': sorted({r['origin'] for r in nonzero}),
                'nonzero_direction_stores': sorted({r['store'] for r in nonzero})}
    return {'quarter_coefficients': coefficients, 'observed_only': True, '2015_used': False,
            'annual_coefficient_shared': False}, journals


def choices(row, policy):
    raw, _ = candidates(row); base = row['matched_mean28']; result = {}
    for method in ORDER:
        alpha = policy['quarter_coefficients'][str(quarter(row['origin']))][method]['alpha']
        if not math.isfinite(alpha) or not 0 <= alpha <= 1: raise ValueError('fixed convex quarterly coefficient required')
        result[method] = [(1-alpha)*b+alpha*p if good else 0. for b, p, good in zip(base, raw[method], row['open_mask'])]
    return result
