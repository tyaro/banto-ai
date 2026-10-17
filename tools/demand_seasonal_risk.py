"""Finite signed total blending under seasonal mean under/over constraints."""
import datetime as dt
import math
from demand_autonomous_mean import FIT
from demand_seasonal_quantity import quarter
from demand_shortfall_quantity import measure

ORDER = ('matched_mean28', 'signed_raw_blend', 'signed_recent14_blend')


def recent14(row):
    origin = dt.date.fromisoformat(row['origin'])
    values = row['past_original_quantity']
    if len(values) != 56: raise ValueError('fixed past-only context required')
    weekdays = [[] for _ in range(7)]
    for k, value in enumerate(values[-14:]):
        day = origin-dt.timedelta(days=14-k)
        if str(day)[5:] in ('01-01', '12-25') or value is None: continue
        if not math.isfinite(value) or value < 0: raise ValueError('observed nonnegative past quantity required')
        weekdays[day.weekday()].append(value)
    counts = [len(v) for v in weekdays]
    result = []
    for k, (b, good) in enumerate(zip(row['matched_mean28'], row['open_mask'])):
        w = (origin+dt.timedelta(days=k)).weekday()
        result.append(math.fsum(weekdays[w])/counts[w] if good and counts[w] >= 2 else b)
    return result, {'weekday_counts': counts, 'fallback_weekdays': [w for w in range(7) if counts[w] < 2],
                    'first': str(origin-dt.timedelta(days=14)), 'last_exclusive': str(origin)}


def candidates(row):
    recent, _ = recent14(row)
    result = {'matched_mean28': list(row['matched_mean28']), 'signed_raw_blend': list(row['raw_prediction']),
              'signed_recent14_blend': recent}
    if any(len(p) != 14 for p in result.values()) or len(row['open_mask']) != 14: raise ValueError('fixed forecast horizon required')
    if any(not math.isfinite(v) or v < 0 or (not good and v != 0.) for p in result.values() for v, good in zip(p, row['open_mask'])):
        raise ValueError('finite nonnegative matched-closure forecasts required')
    return result


def side_bound(samples, side):
    if side not in ('under', 'over') or not samples: raise ValueError('supported signed side required')
    sign = -1. if side == 'under' else 1.
    def excess(alpha):
        return math.fsum(s['weight']*(max(sign*(s['e']+alpha*s['D']), 0.)-max(sign*s['e'], 0.)) for s in samples)
    points = sorted({0., 1., *(-s['e']/s['D'] for s in samples if s['D'] != 0 and 0 < -s['e']/s['D'] < 1)})
    previous, before, upper, segment = 0., 0., 1., None
    for point in points[1:]:
        after = excess(point)
        if after > 0:
            upper = previous+(point-previous)*(-before)/(after-before)
            upper = max(0., min(1., upper))
            if upper > 0: upper = math.nextafter(upper, 0.)
            segment = [previous, point]; break
        previous, before = point, after
    slope = math.fsum(s['weight']*(sign*s['D'] if sign*s['e'] > 0 else max(sign*s['D'], 0.) if s['e'] == 0 else 0.) for s in samples)
    return {'upper': upper, 'breakpoints': points, 'limiting_segment': segment, 'initial_slope': slope,
            'baseline': math.fsum(s['weight']*max(sign*s['e'], 0.) for s in samples),
            'excess_at_upper': excess(upper), 'excess_at_one': excess(1.)}


def calibrate(rows):
    coefficients, sample_journal = {}, {}
    seen = set()
    for r in rows:
        if r['store'] not in FIT or not r['origin'].startswith('2014-') or dt.date.fromisoformat(r['origin'])+dt.timedelta(days=13) >= dt.date(2015, 1, 1):
            raise ValueError('fixed pre-2015 calibration metadata required')
        key = r['store'], r['origin']
        if key in seen: raise ValueError('duplicate calibration key')
        seen.add(key)
    for q in range(1, 5):
        selected = [r for r in rows if quarter(r['origin']) == q and all(v is not None for v in r['actual'])]
        counts = {s: sum(r['store'] == s for r in selected) for s in FIT}
        if not selected or any(n == 0 for n in counts.values()): raise ValueError('complete real-label support in every store required')
        coefficients[str(q)], sample_journal[str(q)] = {}, {}
        for method in ORDER:
            samples = []
            for r in selected:
                if len(r['actual']) != 14 or any(not math.isfinite(v) or v < 0 for v in r['actual']) or not math.isfinite(r['scale']) or r['scale'] <= 0:
                    raise ValueError('real finite complete total and positive scale required')
                b, y = math.fsum(r['matched_mean28']), math.fsum(r['actual'])
                raw = math.fsum(candidates(r)[method])
                samples.append({'store': r['store'], 'origin': r['origin'], 'e': b-y, 'D': raw-b,
                                'baseline_total': b, 'raw_total': raw, 'actual_total': y, 'scale': r['scale'],
                                'weight': 1/(10*counts[r['store']])})
            under, over = side_bound(samples, 'under'), side_bound(samples, 'over')
            upper = min(1., under['upper'], over['upper'])
            energy = math.fsum(s['weight']*(s['D']/(14*s['scale']))**2 for s in samples)
            covariance = math.fsum(s['weight']*(-s['e'])*s['D']/(14*s['scale'])**2 for s in samples)
            unconstrained = covariance/energy if energy > 1e-24 else 0.
            alpha = max(0., min(upper, unconstrained))
            if not all(math.isfinite(v) for v in (energy, covariance, alpha)): raise ValueError('finite total coefficient required')
            changes = {side: math.fsum(s['weight']*(max(sign*(s['e']+alpha*s['D']), 0.)-max(sign*s['e'], 0.)) for s in samples)
                       for side, sign in (('under', -1.), ('over', 1.))}
            if any(v > 1e-8 for v in changes.values()): raise ValueError('calibration mean risk constraint failed')
            coefficients[str(q)][method] = {'alpha': alpha, 'upper': upper, 'unconstrained': unconstrained,
                                            'energy': energy, 'covariance': covariance, 'under': under, 'over': over,
                                            'mean_risk_changes': changes,
                                            'complete_windows': len(selected), 'per_store': {str(s): n for s, n in counts.items()}}
            sample_journal[str(q)][method] = samples
    return {'quarter_coefficients': coefficients, 'observed_only': True, '2015_used': False}, sample_journal


def choices(row, policy):
    raw = candidates(row); base = row['matched_mean28']; result = {}
    for method in ORDER:
        alpha = policy['quarter_coefficients'][str(quarter(row['origin']))][method]['alpha']
        if not math.isfinite(alpha) or not 0 <= alpha <= 1: raise ValueError('finite convex coefficient required')
        result[method] = [(1-alpha)*b+alpha*p if good else 0. for b, p, good in zip(base, raw[method], row['open_mask'])]
    return result


def choose(groups):
    selected, eligibility = {}, {}
    for q in range(1, 5):
        group = groups[f'normal_Q{q}']; eligibility[str(q)] = {}
        if set(group) != {'observed', 'assumed_missing_zero'}: raise ValueError('both label scenarios required')
        for method in ORDER:
            reasons = []
            for mode, scores in group.items():
                b, v = scores['matched_mean28'], scores[method]
                if not all(math.isfinite(x) for x in (v['macro']['total'], v['shortfall']['macro']['under'], v['shortfall']['macro']['over'])):
                    raise ValueError('finite seasonal risks required')
                if v['macro']['total'] > b['macro']['total']+1e-12: reasons.append(mode+'/total_MSE')
                for side in ('under', 'over'):
                    if v['shortfall']['macro'][side] > b['shortfall']['macro'][side]+1e-8: reasons.append(mode+'/'+side)
            eligibility[str(q)][method] = {'eligible': not reasons, 'reasons': reasons}
        if not eligibility[str(q)]['matched_mean28']['eligible']: raise ValueError('baseline must be eligible')
        best = ORDER[0]
        for method in ORDER:
            if eligibility[str(q)][method]['eligible'] and group['observed'][method]['macro']['total'] < group['observed'][best]['macro']['total']-1e-12:
                best = method
        selected[str(q)] = best
    return {'selected_by_quarter': selected, 'eligibility': eligibility, '2015_used': False, 'newyear_used': False}
