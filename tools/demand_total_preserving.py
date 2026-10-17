"""Nonnegative daily shapes with baseline-identical fourteen-day totals."""
import datetime as dt
import math
from demand_autonomous_mean import FIT
from demand_seasonal_quantity import quarter
from demand_shortfall_quantity import measure as old_measure

ORDER = ('matched_mean28', 'ridge_shape', 'weekly_ridge_shape', 'level_shape')
TOTAL_TOL = 1e-8
MSE_TOL = 1e-12


def repair_total(values, mask, total):
    result = list(values)
    active = [j for j, good in enumerate(mask) if good]
    if not active:
        if total != 0: raise ValueError('positive total with no active day')
        return [0.]*len(mask)
    pivot = max(active, key=lambda j: result[j])
    result[pivot] = total-math.fsum(v for j, v in enumerate(result) if j != pivot)
    if any(not math.isfinite(v) or v < 0 or (not good and v != 0) for v, good in zip(result, mask)):
        raise ValueError('nonnegative finite closure shape required')
    if abs(math.fsum(result)-total) > TOTAL_TOL: raise ValueError('total preservation failed')
    return result


def project(raw, baseline, mask):
    if len(raw) != 14 or len(baseline) != 14 or len(mask) != 14: raise ValueError('fixed fourteen-day shape required')
    if any(not math.isfinite(v) for v in raw+baseline) or any(v < 0 or (not good and v != 0) for v, good in zip(baseline, mask)):
        raise ValueError('finite shape and matched closure baseline required')
    total = math.fsum(baseline)
    if total == 0: return [0.]*14
    active = [j for j, good in enumerate(mask) if good]
    if not active: raise ValueError('positive baseline must have active support')
    ordered = sorted((raw[j] for j in active), reverse=True)
    prefix, theta = 0., None
    for k, value in enumerate(ordered, 1):
        prefix += value
        trial = (prefix-total)/k
        if value > trial: theta = trial
    if theta is None: raise ValueError('simplex support unavailable')
    result = [max(v-theta, 0.) if good else 0. for v, good in zip(raw, mask)]
    return repair_total(result, mask, total)


def shapes(row, levels):
    baseline, mask, raw = row['matched_mean28'], row['open_mask'], row['raw_prediction']
    if len(raw) != 14 or len(row['open_mean28']) != 14: raise ValueError('supported raw horizon required')
    day = dt.date.fromisoformat(row['origin'])
    by_weekday = {w: [raw[j] for j in range(14) if mask[j] and (day+dt.timedelta(days=j)).weekday() == w] for w in range(7)}
    weekly = [math.fsum(by_weekday[(day+dt.timedelta(days=j)).weekday()])/len(by_weekday[(day+dt.timedelta(days=j)).weekday()]) if good else 0.
              for j, good in enumerate(mask)]
    delta = levels[str(quarter(row['origin']))]['value']
    level = [max(b, p+delta*row['scale']) if good else 0. for b, p, good in zip(baseline, row['open_mean28'], mask)]
    return {'matched_mean28': list(baseline), 'ridge_shape': project(raw, baseline, mask),
            'weekly_ridge_shape': project(weekly, baseline, mask), 'level_shape': project(level, baseline, mask)}


def calibrate(rows, levels):
    result = {}
    for q in range(1, 5):
        selected = [r for r in rows if quarter(r['origin']) == q]
        projected = {(r['store'], r['origin']): shapes(r, levels) for r in selected}
        result[str(q)] = {}
        for method in ORDER:
            energies, covariances, counts = [], [], {}
            for store in FIT:
                ds, rs = [], []
                for r in selected:
                    if r['store'] != store: continue
                    for p, b, a, good in zip(projected[r['store'], r['origin']][method], r['matched_mean28'], r['actual'], r['open_mask']):
                        if good and a is not None:
                            ds.append((p-b)/r['scale']); rs.append((a-b)/r['scale'])
                if not ds: raise ValueError('observed quantity support in each fixed store required')
                counts[str(store)] = len(ds)
                energies.append(math.fsum(d*d for d in ds)/len(ds))
                covariances.append(math.fsum(d*r for d, r in zip(ds, rs))/len(ds))
            energy, covariance = math.fsum(energies)/10, math.fsum(covariances)/10
            alpha = max(0., min(1., covariance/energy)) if energy > 1e-24 else 0.
            if not math.isfinite(alpha): raise ValueError('finite shape coefficient required')
            result[str(q)][method] = {'alpha': alpha, 'energy': energy, 'covariance': covariance,
                                      'observed_quantity_per_store': counts, 'calibration_windows': len(selected)}
    return {'quarter_coefficients': result, 'quarter_levels': levels, '2015_used': False}


def choices(row, policy):
    projected = shapes(row, policy['quarter_levels']); base = row['matched_mean28']; mask = row['open_mask']
    coefficients = policy['quarter_coefficients'][str(quarter(row['origin']))]
    result = {}
    for method in ORDER:
        alpha = coefficients[method]['alpha']
        if not math.isfinite(alpha) or not 0 <= alpha <= 1: raise ValueError('fixed convex shape coefficient required')
        if alpha == 0: result[method] = list(base)
        else:
            values = [(1-alpha)*b+alpha*p if good else 0. for b, p, good in zip(base, projected[method], mask)]
            result[method] = repair_total(values, mask, math.fsum(base))
    return result


def measure(rows, prediction):
    result = old_measure(rows, prediction)
    max_total, max_under, max_over = 0., 0., 0.
    for r in rows:
        p, b = math.fsum(prediction(r)), math.fsum(r['baseline_proxy'])
        max_total = max(max_total, abs(p-b))
        if r['complete_label']:
            a = math.fsum(r['actual'])
            max_under = max(max_under, max(a-p, 0.)-max(a-b, 0.))
            max_over = max(max_over, max(p-a, 0.)-max(b-a, 0.))
    result['total_invariance'] = {'max_total_absolute_difference': max_total,
                                'max_window_under_increase': max_under, 'max_window_over_increase': max_over,
                                'tolerance_quantity_units': TOTAL_TOL}
    return result


def choose(groups):
    selected, eligibility = {}, {}
    for q in range(1, 5):
        relevant = [f'normal_Q{q}']+(['newyear'] if q == 1 else [])
        eligibility[str(q)] = {}
        for method in ORDER:
            reasons = []
            for group in relevant:
                if set(groups[group]) != {'observed', 'assumed_missing_zero'}: raise ValueError('both label scenarios required')
                for mode, scores in groups[group].items():
                    control, value = scores['matched_mean28'], scores[method]
                    if not all(math.isfinite(v) for v in (value['quantity']['macro']['MSE'], value['macro']['total'], value['macro']['joint'], value['shortfall']['macro']['under'], value['shortfall']['macro']['over'])):
                        raise ValueError('finite selection measurements required')
                    if value['quantity']['macro']['MSE'] > control['quantity']['macro']['MSE']+MSE_TOL:
                        reasons.append(group+'/'+mode+'/quantity_MSE')
                    if abs(value['macro']['total']-control['macro']['total']) > MSE_TOL:
                        reasons.append(group+'/'+mode+'/total_MSE')
                    for side in ('under', 'over'):
                        if abs(value['shortfall']['macro'][side]-control['shortfall']['macro'][side]) > TOTAL_TOL:
                            reasons.append(group+'/'+mode+'/'+side)
                    if any(value['total_invariance'][key] > TOTAL_TOL for key in ('max_total_absolute_difference', 'max_window_under_increase', 'max_window_over_increase')):
                        reasons.append(group+'/'+mode+'/total_invariance')
            eligibility[str(q)][method] = {'eligible': not reasons, 'reasons': reasons}
        if not eligibility[str(q)]['matched_mean28']['eligible']: raise ValueError('baseline must be eligible')
        best = ORDER[0]
        scores = groups[f'normal_Q{q}']['observed']
        for method in ORDER:
            if eligibility[str(q)][method]['eligible'] and scores[method]['macro']['joint'] < scores[best]['macro']['joint']-MSE_TOL:
                best = method
        selected[str(q)] = best
    return {'selected_by_quarter': selected, 'eligibility': eligibility, '2015_used': False}
