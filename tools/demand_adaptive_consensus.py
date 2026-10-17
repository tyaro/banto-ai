"""Past-only direction persistence with two annually shared coefficients."""
import datetime as dt
import math
from demand_autonomous_mean import FIT
from demand_seasonal_quantity import quarter
from demand_seasonal_risk import side_bound
from demand_shortfall_quantity import measure

ORDER = ('matched_mean28', 'consensus_bias', 'consensus_raw')
EPS = 1e-8


def sign(value): return 0 if value is None or abs(value) <= EPS else 1 if value > 0 else -1


def signals(row):
    origin = dt.date.fromisoformat(row['origin']); values = row['past_original_quantity']
    if len(values) != 56 or any(v is not None and (not math.isfinite(v) or v < 0) for v in values):
        raise ValueError('finite nonnegative past56 with explicit missing required')
    if 'past_original_observed' in row and row['past_original_observed'] != [v is not None for v in values]:
        raise ValueError('raw observation mask changed')
    first = origin-dt.timedelta(days=56)
    def past(day):
        if not first <= day < origin: raise ValueError('current/future or outside-context quantity requested')
        return values[(day-first).days]
    blocks = {}
    for lag in (14, 28):
        issue = origin-dt.timedelta(days=lag); ref = issue-dt.timedelta(days=28)
        weekdays = [[] for _ in range(7)]
        for k in range(28):
            day = ref+dt.timedelta(days=k); v = past(day)
            if v is not None: weekdays[day.weekday()].append(v)
        actual = [past(issue+dt.timedelta(days=k)) for k in range(14)]
        counts = [len(v) for v in weekdays]
        reasons = (['missing_actual'] if any(v is None for v in actual) else [])+(['weekday_support'] if min(counts) < 3 else [])
        forecast = [0. if str(issue+dt.timedelta(days=k))[5:] in ('01-01', '12-25') else
                    math.fsum(weekdays[(issue+dt.timedelta(days=k)).weekday()])/counts[(issue+dt.timedelta(days=k)).weekday()]
                    for k in range(14)] if min(counts) >= 3 else None
        blocks[str(lag)] = {'reference_first': str(ref), 'issue_reconstructed': str(issue), 'actual_end_exclusive': str(issue+dt.timedelta(days=14)),
                            'weekday_counts': counts, 'supported': not reasons, 'reasons': reasons,
                            'actual_total': math.fsum(actual) if None not in actual else None,
                            'baseline_total': math.fsum(forecast) if forecast is not None else None,
                            'residual': math.fsum(actual)-math.fsum(forecast) if not reasons else None}
    pairs = []
    for j in range(7):
        previous = origin-dt.timedelta(days=14-j); recent = previous+dt.timedelta(days=7)
        a, b = past(previous), past(recent)
        if a is not None and b is not None and all(str(day)[5:] not in ('01-01', '12-25') for day in (previous, recent)):
            pairs.append(b-a)
    trend = math.fsum(pairs) if len(pairs) == 7 else None
    directions = [sign(blocks[str(lag)]['residual']) for lag in (14, 28)]+[sign(trend)]
    common = directions[0] if all(v == directions[0] and v != 0 for v in directions) else 0
    reasons = [f'lag{lag}_{reason}' for lag in (14, 28) for reason in blocks[str(lag)]['reasons']]
    if len(pairs) != 7: reasons.append('trend_pair_support')
    if not reasons and 0 in directions: reasons.append('zero_signal')
    if not reasons and not common: reasons.append('direction_disagreement')
    return {'blocks': blocks, 'trend7': trend, 'trend_pairs': len(pairs), 'signs': directions,
            'common_direction': common, 'active': common != 0, 'reasons': reasons,
            'first_input_day': str(first), 'last_input_exclusive': str(origin)}


def candidates(row):
    signal = signals(row); base = list(row['matched_mean28']); raw = list(row['raw_prediction']); mask = row['open_mask']
    if any(len(p) != 14 for p in (base, raw, mask)) or any(not math.isfinite(v) or v < 0 or (not good and v != 0) for p in (base, raw) for v, good in zip(p, mask)):
        raise ValueError('finite nonnegative matched-closure horizon required')
    total = math.fsum(base); delta = math.fsum(raw)-total
    raw_active = signal['active'] and sign(delta) == signal['common_direction']
    bias_active = signal['active'] and total > 0
    if bias_active:
        h1, h2 = (signal['blocks'][str(lag)]['residual'] for lag in (14, 28))
        correction = signal['common_direction']*min(abs(h1), abs(h2))
        target = max(0., total+correction)
        biased = [b*(target/total) for b in base]
    else: biased = list(base)
    trace = {**signal, 'baseline_total': total, 'raw_total_difference': delta,
             'bias_active': bias_active, 'raw_active': raw_active,
             'bias_proposed_difference': math.fsum(biased)-total,
             'raw_proposed_difference': delta if raw_active else 0.}
    return {'matched_mean28': base, 'consensus_bias': biased, 'consensus_raw': raw if raw_active else list(base)}, trace


def calibrate(rows):
    seen = set()
    for r in rows:
        if r['store'] not in FIT or not r['origin'].startswith('2014-') or dt.date.fromisoformat(r['origin'])+dt.timedelta(days=13) >= dt.date(2015, 1, 1):
            raise ValueError('pre-2015 fixed calibration metadata required')
        key = r['store'], r['origin']
        if key in seen: raise ValueError('duplicate calibration key')
        seen.add(key)
    by_quarter, journals = {}, {}
    for q in range(1, 5):
        complete = [r for r in rows if quarter(r['origin']) == q and None not in r['actual']]
        counts = {s: sum(r['store'] == s for r in complete) for s in FIT}
        if any(n == 0 for n in counts.values()): raise ValueError('complete observed support in all ten stores required')
        by_quarter[str(q)], journals[str(q)] = {}, {}
        for method in ORDER:
            samples = []
            for r in complete:
                if len(r['actual']) != 14 or any(not math.isfinite(v) or v < 0 for v in r['actual']) or not math.isfinite(r['scale']) or r['scale'] <= 0:
                    raise ValueError('complete real targets and positive scale required')
                b, y = math.fsum(r['matched_mean28']), math.fsum(r['actual']); p = math.fsum(candidates(r)[0][method])
                samples.append({'store': r['store'], 'origin': r['origin'], 'e': b-y, 'D': p-b,
                                'weight': 1/(10*counts[r['store']]), 'scale': r['scale'], 'baseline_total': b, 'actual_total': y, 'raw_total': p})
            a = math.fsum(v['weight']*(v['D']/(14*v['scale']))**2 for v in samples)
            c = math.fsum(-v['weight']*v['e']*v['D']/(14*v['scale'])**2 for v in samples)
            under, over = side_bound(samples, 'under'), side_bound(samples, 'over')
            mse_upper = max(0., 2*c/a) if a > 1e-24 else 1.
            by_quarter[str(q)][method] = {'energy': a, 'covariance': c, 'under': under, 'over': over, 'MSE_upper': mse_upper,
                                          'upper': min(1., under['upper'], over['upper'], mse_upper), 'complete_windows': len(samples),
                                          'per_store': {str(s): n for s, n in counts.items()}}
            journals[str(q)][method] = samples
    shared = {}
    for method in ORDER:
        a = math.fsum(by_quarter[str(q)][method]['energy'] for q in range(1, 5))/4
        c = math.fsum(by_quarter[str(q)][method]['covariance'] for q in range(1, 5))/4
        upper = min(by_quarter[str(q)][method]['upper'] for q in range(1, 5))
        alpha = max(0., min(upper, c/a)) if a > 1e-24 else 0.
        if not math.isfinite(alpha): raise ValueError('finite shared coefficient required')
        changes = {}
        for q in range(1, 5):
            samples = journals[str(q)][method]; risk = {}
            for side, sg in (('under', -1.), ('over', 1.)):
                risk[side] = math.fsum(v['weight']*(max(sg*(v['e']+alpha*v['D']), 0.)-max(sg*v['e'], 0.)) for v in samples)
                if risk[side] > 1e-8: raise ValueError('shared calibration side risk failed')
            risk['MSE'] = by_quarter[str(q)][method]['energy']*alpha**2-2*by_quarter[str(q)][method]['covariance']*alpha
            if risk['MSE'] > 1e-12: raise ValueError('shared calibration quarter MSE failed')
            changes[str(q)] = risk
        shared[method] = {'alpha': alpha, 'upper': upper, 'unconstrained': c/a if a > 1e-24 else 0.,
                          'equal_quarter_energy': a, 'equal_quarter_covariance': c, 'quarter_changes': changes}
    return {'shared_coefficients': shared, 'quarter_constraints': by_quarter, 'observed_only': True, '2015_used': False}, journals


def choices(row, policy):
    raw, _ = candidates(row); base = row['matched_mean28']; result = {}
    for method in ORDER:
        a = policy['shared_coefficients'][method]['alpha']
        if not math.isfinite(a) or not 0 <= a <= 1: raise ValueError('shared fixed convex coefficient required')
        result[method] = [(1-a)*b+a*p if good else 0. for b, p, good in zip(base, raw[method], row['open_mask'])]
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
                    raise ValueError('finite quarter risks required')
                if v['macro']['total'] > b['macro']['total']+1e-12: reasons.append(mode+'/total_MSE')
                for side in ('under', 'over'):
                    if v['shortfall']['macro'][side] > b['shortfall']['macro'][side]+1e-8: reasons.append(mode+'/'+side)
            eligibility[str(q)][method] = {'eligible': not reasons, 'reasons': reasons}
        if not eligibility[str(q)]['matched_mean28']['eligible']: raise ValueError('baseline must be eligible')
        best = ORDER[0]
        for method in ORDER:
            if eligibility[str(q)][method]['eligible'] and group['observed'][method]['macro']['total'] < group['observed'][best]['macro']['total']-1e-12: best = method
        selected[str(q)] = best
    return {'selected_by_quarter': selected, 'eligibility': eligibility, '2015_used': False, 'newyear_used': False}
