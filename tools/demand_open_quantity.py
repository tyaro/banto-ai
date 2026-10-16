"""Closure-gated positive-quantity features and daily/total joint ridge."""
import datetime as dt
import math
from demand_macos_rebuild import PastOnly
from demand_public_calendar import build_inputs
from demand_statistical_overlay import describe_history
from demand_statistical_features import encode_profile
from demand_autonomous_mean import features

ORDER = ('matched_mean28', 'open_mean28', 'level_corrected', 'gated_ridge')


class QuantityPast:
    def __init__(self, past, monthdays):
        self.past, self.monthdays = past, monthdays
    def get(self, day):
        value = self.past.get(day)  # Keep origin boundary checks even on closure dates.
        return None if str(day)[5:] in self.monthdays else value


def inputs(history, store, origin, scale, enabled, monthdays):
    past = PastOnly(history, origin)
    original = build_inputs(past, origin, scale, 'pre_post', enabled)
    if not original['available']:
        raise ValueError('original fixed mean28 support required')
    days = [origin-dt.timedelta(days=k) for k in range(56, 0, -1)]
    values = [past.get(day) for day in days]
    usable = [v is not None and str(day)[5:] not in monthdays for v, day in zip(values, days)]
    kept = [v for v, good in zip(values, usable) if good]
    if not kept:
        raise ValueError('conditional quantity context unavailable')
    mean = math.fsum(kept)/len(kept)
    std = math.sqrt(math.fsum((v-mean)**2 for v in kept)/len(kept))
    weekdays = [[v for v, day, good in zip(values[-28:], days[-28:], usable[-28:]) if good and day.weekday() == w] for w in range(7)]
    counts = [len(v) for v in weekdays]
    future = [origin+dt.timedelta(days=k) for k in range(14)]
    open_mask = [str(day)[5:] not in monthdays for day in future]
    conditional = [math.fsum(weekdays[day.weekday()])/counts[day.weekday()] if counts[day.weekday()] >= 2 else original['baseline'][j]
                   for j, day in enumerate(future)]
    base = [v if good else 0. for v, good in zip(conditional, open_mask)]
    matched = [v if good else 0. for v, good in zip(original['baseline'], open_mask)]
    x = {**original, 'context_statistics': [mean/scale, std/max(mean, .01*scale)], 'baseline': base}
    profile = describe_history(QuantityPast(past, monthdays), origin)
    encoded = encode_profile(profile, origin, scale)
    return {'store': store, 'origin': str(origin), 'scale': scale, 'matched_mean28': matched,
            'open_mean28': base, 'open_mask': open_mask, 'raw_features': features(x, encoded),
            'weekday_quantity_counts': counts, 'fallback_weekdays': [w for w, count in enumerate(counts) if count < 2],
            'past_original_quantity': values, 'past_original_observed': [v is not None for v in values],
            'past_quantity_usable': usable, 'quantity_context_statistics': x['context_statistics'],
            'profile': profile, 'encoded': encoded, 'operating_status': 'unknown'}


def fit_gated(raw, base, actual, scales, open_mask):
    import torch
    if raw.shape != (len(base), 14, 72) or actual.shape != base.shape or base.shape != open_mask.shape:
        raise ValueError('fixed gated ridge shapes required')
    flat = raw[open_mask]
    mean = flat.mean(0); std = ((flat-mean).square().mean(0)).sqrt()
    active = std > 1e-12; mean[0] = 0.; std[0] = 1.; active[0] = True
    std = torch.where(active, std, torch.ones_like(std))
    x = torch.where(active, (raw-mean)/std, 0.)*open_mask[:, :, None]
    y = (actual-base)/scales[:, None]
    dx, dy, tx, ty = x.reshape(-1, 72), y.reshape(-1), x.mean(1), y.mean(1)
    penalty = .01*torch.eye(72, dtype=torch.float64); penalty[0, 0] = 0.
    gram = .5*(dx.T@dx)/len(dx)+.5*(tx.T@tx)/len(tx)+penalty
    rhs = .5*(dx.T@dy)/len(dx)+.5*(tx.T@ty)/len(tx)
    beta = torch.linalg.solve(gram, rhs)
    if not bool(torch.isfinite(beta).all()):
        raise ValueError('nonfinite gated coefficients')
    return {'mean': mean, 'std': std, 'active': active, 'beta': beta}


def predict_gated(raw, base, scales, open_mask, state):
    import torch
    x = torch.where(state['active'], (raw-state['mean'])/state['std'], 0.)*open_mask[:, :, None]
    return torch.relu(base+scales[:, None]*(x@state['beta']))*open_mask


def level_delta(base, actual, scales, open_mask):
    direction = open_mask.double()
    residual = (actual-base)/scales[:, None]
    energy = .5*direction.square().mean().item()+.5*direction.mean(1).square().mean().item()
    covariance = .5*(direction*residual).mean().item()+.5*(direction.mean(1)*residual.mean(1)).mean().item()
    delta = max(0., covariance/energy) if energy else 0.
    if not math.isfinite(delta):
        raise ValueError('nonfinite internal level correction')
    return {'delta': delta, 'energy': energy, 'covariance': covariance, 'selection_period': '2014 inner60 only'}


def choose(scores):
    if set(scores) != set(ORDER):
        raise ValueError('fixed four-way comparison required')
    selected = ORDER[0]
    for name in ORDER:
        if not math.isfinite(scores[name]['joint']):
            raise ValueError('finite outer score required')
        if scores[name]['joint'] < scores[selected]['joint']-1e-12:
            selected = name
    return selected
