"""Past-only recurring closure-equivalent assumptions; original masks stay intact."""
import datetime as dt
import math
from demand_group_selection import FIT

YEARS = (2013, 2014)
FREEZE = dt.date(2015, 1, 1)
METHODS = ('baseline', 'prior', 'baseline_proxy', 'candidate')


def learn_pattern(rows):
    selected = {}
    for row in rows:
        if row['store'] not in FIT:
            continue
        day = dt.date.fromisoformat(row['date'])
        if day.year not in YEARS or day >= FREEZE:
            continue
        key = row['store'], day
        if key in selected:
            raise ValueError('duplicate historical store/date')
        observed, value = row['observed'], row['quantity']
        if type(observed) is not bool or (not observed and value is not None):
            raise ValueError('explicit original observation mask required')
        if observed and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
            raise ValueError('historical finite nonnegative quantity required')
        selected[key] = {'store': row['store'], 'date': str(day), 'observed': observed, 'quantity': value,
                         'historical_state': 'missing' if not observed else 'observed_zero' if value == 0 else 'positive'}
    expected = {(s, dt.date(year, 1, 1)+dt.timedelta(days=k)) for s in FIT for year in YEARS for k in range(365)}
    if set(selected) != expected:
        raise ValueError('full two-year fixed ten-store calendar required')
    patterns = []
    for k in range(365):
        monthday = str(dt.date(2013, 1, 1)+dt.timedelta(days=k))[5:]
        support = [selected[s, dt.date.fromisoformat(f'{year}-{monthday}')] for year in YEARS for s in FIT]
        if all(v['historical_state'] != 'positive' for v in support):
            patterns.append({'month_day': monthday, 'years': list(YEARS), 'stores': list(FIT),
                             'observed_zero': sum(v['historical_state'] == 'observed_zero' for v in support),
                             'missing': sum(v['historical_state'] == 'missing' for v in support),
                             'support': support, 'independent_years': 2, 'confirmed_operating_schedule': False})
    return {'freeze_exclusive': str(FREEZE), 'patterns': patterns, 'calendar_rows': len(selected),
            'confirmed_closed': False, 'rule': 'both years and all ten stores zero or missing',
            'fitted_probability_one': False, 'training_used_2015': False}


def apply_pattern(row, state):
    origin = dt.date.fromisoformat(row['origin'])
    if row['store'] not in FIT or origin < FREEZE or state['freeze_exclusive'] > row['origin']:
        raise ValueError('frozen pattern must precede eligible forecast')
    if len(row['baseline']) != 14 or len(row['candidate']) != 14:
        raise ValueError('fourteen daily reference forecasts required')
    selected = {p['month_day'] for p in state['patterns']}
    flags = [str(origin+dt.timedelta(days=j))[5:] in selected for j in range(14)]
    return {'store': row['store'], 'origin': row['origin'], 'scale': row['scale'],
            'baseline': list(row['baseline']), 'prior': list(row['candidate']),
            'baseline_proxy': [0. if flag else value for flag, value in zip(flags, row['baseline'])],
            'candidate': [0. if flag else value for flag, value in zip(flags, row['candidate'])],
            'operating_status': ['unknown']*14, 'assumed_closure': flags,
            'assumption_source': 'frozen_2013_2014_recurring_nonpositive_pattern'}


def attach_scenarios(forecasts, labels):
    observed, scenario, ledger = [], [], []
    for row in forecasts:
        old = labels[row['store'], row['origin']]
        actual = list(old['actual'])
        if len(actual) != 14 or old['complete_label'] != all(v is not None for v in actual):
            raise ValueError('original label calendar or complete mask changed')
        imputed = [v is None and flag for v, flag in zip(actual, row['assumed_closure'])]
        assumed = [0. if flag else v for v, flag in zip(actual, imputed)]
        observed.append({**row, 'actual': actual, 'raw_actual': actual, 'imputed_missing': [False]*14,
                         'complete_label': old['complete_label']})
        scenario.append({**row, 'actual': assumed, 'raw_actual': actual, 'imputed_missing': imputed,
                         'complete_label': all(v is not None for v in assumed)})
        for j, (raw, value, flag) in enumerate(zip(actual, assumed, imputed)):
            ledger.append({'store': row['store'], 'origin': row['origin'],
                           'date': str(dt.date.fromisoformat(row['origin'])+dt.timedelta(days=j)),
                           'raw_actual': raw, 'original_observed': raw is not None,
                           'scenario_actual': value, 'imputed_missing_zero': flag,
                           'operating_status': 'unknown', 'assumed_closure': row['assumed_closure'][j],
                           'assumption_contradicted_by_positive': row['assumed_closure'][j] and raw is not None and raw > 0})
    return observed, scenario, ledger


def score_cohort(rows, keys):
    from demand_macos_rebuild import eval_metrics
    if len(rows) != len(keys) or {(r['store'], r['origin']) for r in rows} != set(map(tuple, keys)):
        raise ValueError('fixed cohort prediction grid changed')
    if any(s not in FIT for s, _ in keys) or set(s for s, _ in keys) != set(FIT):
        raise ValueError('all fixed stores required')
    for row in rows:
        if type(row['scale']) not in (int, float) or not math.isfinite(row['scale']) or row['scale'] <= 0:
            raise ValueError('positive fixed scale required')
        if len(row['actual']) != 14 or row['complete_label'] != all(v is not None for v in row['actual']):
            raise ValueError('explicit full label mask required')
        if any(v is not None and (type(v) not in (int, float) or not math.isfinite(v) or v < 0) for v in row['actual']):
            raise ValueError('invalid scored label')
        if any(len(row[m]) != 14 or any(not math.isfinite(v) or v < 0 for v in row[m]) for m in METHODS):
            raise ValueError('invalid daily point means')
    per_store = {str(s): {m: eval_metrics([r for r in rows if r['store'] == s],
                                        next(r['scale'] for r in rows if r['store'] == s), m) for m in METHODS} for s in FIT}
    fields = ('daily', 'total', 'joint', 'daily_MAE', 'total_MAE', 'daily_bias', 'total_bias', 'daily_WAPE_percent', 'total_WAPE_percent')
    macro = {m: {f: math.fsum(v[m][f] for v in per_store.values())/10
                 if all(v[m][f] is not None for v in per_store.values()) else None for f in fields} for m in METHODS}
    gains = {}
    for ref in ('baseline', 'prior', 'baseline_proxy'):
        b, p = macro[ref]['joint'], macro['candidate']['joint']
        gains[ref] = 100*(b-p)/b if b is not None and b > 0 and p is not None else None
    return {'macro': macro, 'per_store': per_store, 'improvement_percent_over': gains,
            'scored_daily': sum(v is not None for r in rows for v in r['actual']),
            'original_observed_daily': sum(v is not None for r in rows for v in r['raw_actual']),
            'imputed_missing_zero': sum(sum(r['imputed_missing']) for r in rows),
            'complete_totals': sum(r['complete_label'] for r in rows), 'windows': len(rows),
            'improved_stores_vs_matched': sum(v['candidate']['joint'] < v['baseline_proxy']['joint'] for v in per_store.values())
                if all(v[m]['joint'] is not None for v in per_store.values() for m in ('candidate', 'baseline_proxy')) else None}
