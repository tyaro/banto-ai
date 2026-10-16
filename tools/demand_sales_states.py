"""Separate availability-checked operating status, observed zeros and missingness."""
import datetime as dt
import math

from demand_event_calendar import _aware, _versions
from demand_event_intervals import _operating_calendar
from demand_group_selection import FIT

CUTOFF = dt.date(2014, 7, 1)
MINIMUM = 14


def operating_statuses(records, days, issue_time, store):
    issue_time = _aware(issue_time)
    if type(store) is not int or not days or len(set(days)) != len(days) or any(type(d) is not dt.date for d in days):
        raise ValueError('store and distinct civil dates required')
    if issue_time.date() > min(days):
        raise ValueError('issue must not follow forecast start')
    selected, excluded = _versions(records, issue_time)
    calendar = _operating_calendar(selected, store)
    return {day: calendar.get(day, 'unknown') for day in days}, excluded


def observation_state(status, quantity, observed):
    if status not in ('open', 'closed', 'unknown') or type(observed) is not bool:
        raise ValueError('explicit operating and observation states required')
    if not observed:
        if quantity is not None:
            raise ValueError('missing quantity must be null')
        return 'missing'
    if type(quantity) not in (int, float) or not math.isfinite(quantity) or quantity < 0:
        raise ValueError('observed finite nonnegative quantity required')
    if status == 'closed' and quantity > 0:
        raise ValueError('closed positive observation contradicts sales channel')
    return status+'_zero' if quantity == 0 else status+'_positive'


def fit_occurrence(samples):
    counts = {s: {scope: {'observed': 0, 'positive': 0, 'zero': 0} for scope in ('open', 'mixed')}
              for s in FIT}
    classes, seen = {}, set()
    for sample in samples:
        # Scope checks precede status/mask/quantity; excluded values never classify a closure.
        if sample['store'] not in FIT:
            continue
        day = dt.date.fromisoformat(sample['date'])
        if not dt.date(2013, 1, 1) <= day < CUTOFF:
            continue
        key = sample['store'], sample['date']
        if key in seen:
            raise ValueError('duplicate eligible occurrence label')
        seen.add(key)
        state = observation_state(sample['operating_status'], sample['quantity'], sample['observed'])
        classes[state] = classes.get(state, 0)+1
        if state in ('missing', 'closed_zero'):
            continue
        for scope in (('open', 'mixed') if sample['operating_status'] == 'open' else ('mixed',)):
            value = counts[sample['store']][scope]
            value['observed'] += 1
            value['zero' if sample['quantity'] == 0 else 'positive'] += 1
    states = {}
    for store, scopes in counts.items():
        states[str(store)] = {}
        for scope, values in scopes.items():
            reason = ('insufficient_observations' if values['observed'] < MINIMUM else
                      'no_observed_zero' if values['zero'] == 0 else
                      'no_positive_observation' if values['positive'] == 0 else None)
            states[str(store)][scope] = {**values, 'p_positive': values['positive']/values['observed'] if reason is None else None,
                                        'supported': reason is None, 'reason': reason}
    return {'cutoff_exclusive': str(CUTOFF), 'minimum_observations': MINIMUM, 'per_store': states,
            'observation_classes': classes, 'eligible_distinct_labels': len(seen),
            'operating_status_inferred_from_quantity': False}


def compose_sales(positive_means, reference_means, records, days, issue_time, store,
                  occurrence, *, closed_implies_zero):
    if type(closed_implies_zero) is not bool:
        raise ValueError('explicit sales-channel closure contract required')
    statuses, excluded = operating_statuses(records, days, issue_time, store)
    rows = []
    for day in days:
        status = statuses[day]
        row = {'date': str(day), 'operating_status': status, 'p_positive': None,
               'positive_quantity_mean': None, 'reference_fallback': False}
        if status == 'closed':
            row.update(sales_mean=0. if closed_implies_zero else None,
                       reason='confirmed_closed_zero' if closed_implies_zero else 'closure_zero_contract_absent',
                       probability_scope=None)
        else:
            scope = 'open' if status == 'open' else 'mixed'
            state = occurrence['per_store'][str(store)][scope]
            probability = state['p_positive']
            if state['supported']:
                if type(probability) not in (int, float) or not math.isfinite(probability) or not 0 <= probability <= 1:
                    raise ValueError('valid supported positive-sales probability required')
                mu = positive_means.get(day)
                if type(mu) not in (int, float) or not math.isfinite(mu) or mu <= 0:
                    raise ValueError('supported strictly positive conditional quantity mean required')
                row.update(sales_mean=probability*mu, p_positive=probability, positive_quantity_mean=mu,
                           reason='positive_occurrence_times_quantity', probability_scope=scope)
            else:
                if probability is not None:
                    raise ValueError('unsupported probability must remain null')
                reference = reference_means.get(day)
                if type(reference) not in (int, float) or not math.isfinite(reference) or reference < 0:
                    raise ValueError('finite reference observed-sales mean required')
                row.update(sales_mean=reference, reference_fallback=True,
                           reason='occurrence_'+state['reason'], probability_scope=scope)
        rows.append(row)
    available = all(r['sales_mean'] is not None for r in rows)
    return {'store': store, 'issue_time': issue_time.isoformat(), 'daily': rows,
            'total_sales_mean': math.fsum(r['sales_mean'] for r in rows) if available else None,
            'total_available': available, 'closed_implies_zero': closed_implies_zero,
            'unknown_implies_closed': False, 'holiday_implies_closed': False,
            'excluded_operating_versions': excluded}
