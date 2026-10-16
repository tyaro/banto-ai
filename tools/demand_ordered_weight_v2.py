"""Pure past56 D1 encoder. No readers, targets, baselines, optimizer or store IDs.

Contract: docs/research/demand-ordered-weight-numeric-contract-2026-10-15.md.
This artificial-tested building block does not authorize real-data execution.
"""
import hashlib
import json
from datetime import date, timedelta
from fractions import Fraction as F

from demand_bounded_metrics import Arithmetic

TAU = F(1, 20)
PRECISION = 32
SCALE = 1 << PRECISION
SCHEMA = 'ordered-weight-history-v1'


def origin_date(text):
    if type(text) is not str:
        raise ValueError('ISO origin required')
    d = date.fromisoformat(text)
    if d.isoformat() != text or not date(2013, 1, 1) <= d < date(2015, 1, 1):
        raise ValueError('only 2013-2014 origins allowed')
    if d - timedelta(days=56) < date(2013, 1, 1):
        raise ValueError('past56 must start in 2013 or later')
    return d


def project_past(origin, wide_records):
    """Select date metadata before touching values; not a sandbox or file loader."""
    end = origin_date(origin)
    start = end - timedelta(days=56)
    records = []
    for row in wide_records:
        text = row['date']
        if type(text) is not str:
            raise ValueError('ISO record date required')
        d = date.fromisoformat(text)
        if text != d.isoformat():
            raise ValueError('canonical date required')
        if start <= d < end:
            records.append({k: row[k] for k in ('date', 'available_at', 'value')})
    return {'schema': SCHEMA, 'origin': origin, 'records': records}


def quantize(x, arithmetic):
    """One signed nearest-even rounding to an absolute 2^-32 grid."""
    x = arithmetic.value(x)
    scaled = arithmetic.imul(x.numerator, SCALE)
    whole, remainder = divmod(scaled, x.denominator)
    twice = arithmetic.imul(remainder, 2)
    if twice > x.denominator or (twice == x.denominator and whole % 2):
        whole = arithmetic.iadd(whole, 1)
    return arithmetic.value(F(whole, SCALE))


def encode(packet, checkpoint=lambda: None):
    a = Arithmetic(checkpoint)
    if type(packet) is not dict or set(packet) != {'schema', 'origin', 'records'} or packet['schema'] != SCHEMA:
        raise ValueError('strict history packet required')
    origin = origin_date(packet['origin'])
    rows = packet['records']
    if type(rows) is not list or len(rows) != 56:
        raise ValueError('56 ordered calendar records required')
    start = origin - timedelta(days=56)
    values, opened, dates = [], [], []
    counts = {'open_observed': 0, 'open_zero': 0, 'open_missing': 0,
              'closure_observed': 0, 'closure_zero': 0, 'closure_missing': 0}
    canonical = []
    for i, row in enumerate(rows):
        checkpoint()
        if type(row) is not dict or set(row) != {'date', 'available_at', 'value'}:
            raise ValueError('strict date/available_at/value required')
        d = start + timedelta(days=i)
        if (type(row['date']) is not str or type(row['available_at']) is not str
                or row['date'] != d.isoformat() or row['available_at'] != (d + timedelta(days=1)).isoformat()):
            raise ValueError('ordered past grid and next-day availability required')
        v = row['value']
        if v is not None:
            if type(v) not in (int, float):
                raise ValueError('finite nonnegative int/float or null required')
            v = a.value(v)
            if v < 0:
                raise ValueError('negative quantity')
        is_open = (d.month, d.day) not in ((1, 1), (12, 25))
        prefix = 'open' if is_open else 'closure'
        counts[prefix + ('_missing' if v is None else '_observed')] += 1
        if v == 0:
            counts[prefix + '_zero'] += 1
        values.append(v); opened.append(is_open); dates.append(d)
        canonical.append({'date': row['date'], 'available_at': row['available_at'], 'value_exact': None if v is None else str(v)})
    raw = json.dumps({'schema': SCHEMA, 'origin': packet['origin'], 'records': canonical}, sort_keys=True, separators=(',', ':')).encode()
    J = [j for j in range(14) if all(opened[14*b+j] and values[14*b+j] is not None for b in range(4))]
    s = a.value(F(len(J), 14))
    out = {'schema': 'ordered-weight-state-v1', 'origin': packet['origin'], 'past_start': start.isoformat(),
           'past_end': (origin-timedelta(days=1)).isoformat(), 'availability': 'next_calendar_day',
           'tau': str(TAU), 'precision_bits_absolute': PRECISION, 'rounding': 'nearest_ties_even',
           'input_pin': {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()},
           'counts': counts, 'J': J, 's': str(s), 'mu': None, 'weekday_counts': [], 'weekday_means': [],
           'z_grid': [None]*56, 'z_rounding_error': [None]*56,
           'levels': [], 'changes': [], 'a': None, 'b': None, 'V': None,
           'r_raw': '0', 'r_stored': '0', 'r_grid_numerator': 0, 'r_rounding_error': '0',
           'computed': False, 'reason': None}

    def finish(reason):
        out['reason'] = reason
        out['max_bits'] = a.max_bits
        checkpoint()
        return out

    def mean(xs):
        total = F(0)
        for x in xs:
            total = a.add(total, x)
        return a.div(total, len(xs))

    obs = [v for v, op in zip(values, opened) if op and v is not None]
    if not obs:
        return finish('no_open_observations')
    mu = mean(obs); out['mu'] = str(mu)
    byday = [[v for v, op, d in zip(values, opened, dates) if op and v is not None and d.weekday() == w] for w in range(7)]
    mus = [mean(xs) if xs else None for xs in byday]
    out['weekday_counts'] = list(map(len, byday)); out['weekday_means'] = [None if m is None else str(m) for m in mus]
    if not mu:
        return finish('zero_open_mean')
    if not J:
        return finish('no_common_positions')
    z = []
    for v, op, d in zip(values, opened, dates):
        if not op or v is None:
            z.append(None)
        else:
            exact = a.div(a.sub(v, mus[d.weekday()]), mu)
            rounded = quantize(exact, a)
            error = a.sub(rounded, exact)
            if abs(error) > F(1, 2*SCALE) or abs(exact) > 56:
                raise AssertionError('z domain or rounding bound')
            z.append(rounded)
            out['z_rounding_error'][len(z)-1] = str(error)
    out['z_grid'] = [None if v is None else str(v) for v in z]
    levels = [mean([z[14*b+j] for j in J]) for b in range(4)]
    changes = [a.sub(levels[b+1], levels[b]) for b in range(3)]
    latest = changes[2]; prior = a.div(a.add(changes[0], changes[1]), 2)
    V = mean([a.square(a.sub(z[14*b+j], levels[b])) for b in range(4) for j in J])
    product = a.mul(latest, prior)
    numerator = a.mul(a.mul(2, s), max(product, F(0)))
    denominator = a.add(a.add(a.add(a.square(latest), a.square(prior)), V), a.square(TAU))
    r = a.div(numerator, denominator); stored = quantize(r, a); error = a.sub(stored, r)
    if not (0 <= stored <= s <= 1 and abs(error) <= F(1, 2*SCALE)):
        raise AssertionError('stored weight range or rounding bound')
    out.update(levels=list(map(str, levels)), changes=list(map(str, changes)), a=str(latest), b=str(prior), V=str(V),
               r_raw=str(r), r_stored=str(stored), r_grid_numerator=a.imul(stored.numerator, SCALE//stored.denominator),
               r_rounding_error=str(error), computed=True)
    reason = 'positive_weight' if stored else 'positive_weight_rounded_to_zero' if r else 'opposite_direction' if product < 0 else 'zero_latest_or_past_change'
    return finish(reason)


def encode_features(packet, old_features, checkpoint=lambda: None):
    state = encode(packet, checkpoint)
    a = Arithmetic(checkpoint)
    if old_features is None:
        new_features = None
    else:
        if type(old_features) not in (list, tuple) or len(old_features) != 3 or any(type(x) not in (int, float) for x in old_features):
            raise ValueError('three finite old features required')
        xs = list(map(a.value, old_features))
        if xs[0] != 1:
            raise ValueError('old intercept must be one')
        r = a.value(state['r_stored'])
        new_features = list(map(str, (a.mul(x, r) for x in xs)))
    state['max_bits'] = max(state['max_bits'], a.max_bits)
    return {'state': state, 'old_eligible': old_features is not None, 'features_exact': new_features,
            'retain_old_objective_and_risk_denominators': True}
