"""Small, dependency-free forecasting baselines for the fixed retail pilot.

Civil dates and observed quantities only. Future covariates and PSI are outside
this module. Missing observations stay missing; model fitting is origin-bound.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math


EPOCH = dt.date(2013, 1, 1)
FEATURE_NAMES = ['trend_days', *[f'weekday_{i}' for i in range(1, 7)],
                 *[f'annual_{kind}_{k}' for k in range(1, 4) for kind in ('sin', 'cos')]]


def finite_quantity(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('quantity must be numeric or explicitly missing')
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError('quantity must be finite and nonnegative')
    return value


def past_observations(history, origin):
    """Do not validate or convert future values: they cannot enter the fit."""
    if type(origin) is not dt.date:
        raise ValueError('origin must be a civil date')
    rows = []
    for date in sorted(history):
        if type(date) is not dt.date:
            raise ValueError('history key must be a civil date')
        if date >= origin:
            continue
        value = history[date]
        if value is not None:
            rows.append((date, finite_quantity(value)))
    return rows


def calendar_features(date):
    days = (date - EPOCH).days
    features = [float(days), *[float(date.weekday() == i) for i in range(1, 7)]]
    for k in range(1, 4):
        phase = 2 * math.pi * k * days / 365.2425
        features.extend((math.sin(phase), math.cos(phase)))
    return features


def _solve_positive_definite(matrix, rhs):
    """Cholesky solve; fixed positive ridge makes the centered matrix SPD."""
    size = len(rhs)
    lower = [[0.0] * size for _ in range(size)]
    for i in range(size):
        for j in range(i + 1):
            value = matrix[i][j] - math.fsum(lower[i][k] * lower[j][k] for k in range(j))
            if j == i:
                if not math.isfinite(value) or value <= 0:
                    raise ArithmeticError('ridge system is not positive definite')
                lower[i][j] = math.sqrt(value)
            else:
                lower[i][j] = value / lower[j][j]
    intermediate = [0.0] * size
    for i in range(size):
        intermediate[i] = (rhs[i] - math.fsum(lower[i][j] * intermediate[j] for j in range(i))) / lower[i][i]
    solution = [0.0] * size
    for i in reversed(range(size)):
        solution[i] = (intermediate[i] - math.fsum(lower[j][i] * solution[j] for j in range(i + 1, size))) / lower[i][i]
    return solution


def fit_ridge(features, targets, penalty=1.0):
    """Minimize sum squared errors + penalty*sum(beta**2).

    All non-intercept features are standardized on fitting rows. Centering X
    and y leaves the intercept unpenalized; zero-variance columns use scale 1.
    """
    if not math.isfinite(penalty) or penalty <= 0:
        raise ValueError('penalty must be positive')
    if len(features) != len(targets) or len(targets) < 2:
        raise ValueError('ridge requires at least two aligned fitting rows')
    width = len(features[0])
    if not width or any(len(row) != width or not all(math.isfinite(x) for x in row) for row in features):
        raise ValueError('invalid feature matrix')
    y = [finite_quantity(value) for value in targets]
    n = len(y)
    means = [math.fsum(row[j] for row in features) / n for j in range(width)]
    scales = [math.sqrt(math.fsum((row[j] - means[j])**2 for row in features) / n) for j in range(width)]
    scales = [value if value > 0 else 1.0 for value in scales]
    z = [[(row[j] - means[j]) / scales[j] for j in range(width)] for row in features]
    mean_y = math.fsum(y) / n
    matrix = [[math.fsum(row[i] * row[j] for row in z) + (penalty if i == j else 0.0)
               for j in range(width)] for i in range(width)]
    rhs = [math.fsum(row[j] * (value - mean_y) for row, value in zip(z, y)) for j in range(width)]
    coefficients = _solve_positive_definite(matrix, rhs)
    if not all(math.isfinite(value) for value in coefficients):
        raise ArithmeticError('nonfinite ridge coefficients')
    return {'means': means, 'scales': scales, 'coefficients': coefficients,
            'intercept': mean_y, 'penalty': penalty, 'fit_rows': n}


def predict_ridge(model, features):
    if len(features) != len(model['coefficients']):
        raise ValueError('prediction feature width differs')
    raw = model['intercept'] + math.fsum(beta * (x - mean) / scale for beta, x, mean, scale in
        zip(model['coefficients'], features, model['means'], model['scales']))
    if not math.isfinite(raw):
        raise ArithmeticError('nonfinite ridge prediction')
    return max(0.0, raw), raw < 0


def forecast_pair(history, origin, horizon=14):
    if horizon != 14:
        raise ValueError('this pilot contract fixes a fourteen-day horizon')
    past = past_observations(history, origin)
    if len(past) < 2:
        raise ValueError('insufficient observed history for the pair')
    past_map = dict(past)
    model = fit_ridge([calendar_features(date) for date, _ in past], [value for _, value in past])
    fitting_raw = json.dumps([[str(date), value] for date, value in past], separators=(',', ':'), allow_nan=False).encode()
    model.update({'feature_names': FEATURE_NAMES, 'fit_start': str(past[0][0]), 'fit_end': str(past[-1][0]),
                  'origin': str(origin), 'fitting_input_sha256': hashlib.sha256(fitting_raw).hexdigest()})
    forecasts = []
    for lead in range(1, horizon + 1):
        target = origin + dt.timedelta(days=lead - 1)
        source_date = origin - dt.timedelta(days=1)
        source_date -= dt.timedelta(days=(source_date.weekday() - target.weekday()) % 7)
        while (origin - source_date).days <= 28 and source_date not in past_map:
            source_date -= dt.timedelta(days=7)
        available = (origin - source_date).days <= 28 and source_date in past_map
        ridge, clipped = predict_ridge(model, calendar_features(target))
        forecasts.append({'date': str(target), 'lead': lead,
            'weekly_naive': past_map[source_date] if available else None,
            'naive_source_date': str(source_date) if available else None,
            'naive_missing_reason': None if available else 'no_observed_same_weekday_within_28_days',
            'calendar_ridge': ridge, 'ridge_clipped_at_zero': clipped})
    return {'model': model, 'forecasts': forecasts}


def metrics(pairs):
    """Observed valid (prediction, actual) pairs, including zero actuals."""
    pairs = [(finite_quantity(pred), finite_quantity(actual)) for pred, actual in pairs]
    if not pairs:
        return {'n': 0, 'MAE': None, 'WAPE': None, 'Bias': None, 'null_reason': 'no_valid_pairs'}
    denominator = math.fsum(actual for _, actual in pairs)
    absolute = math.fsum(abs(pred - actual) for pred, actual in pairs)
    signed = math.fsum(pred - actual for pred, actual in pairs)
    return {'n': len(pairs), 'MAE': absolute / len(pairs),
            'WAPE': 100 * absolute / denominator if denominator else None,
            'Bias': 100 * signed / denominator if denominator else None,
            'null_reason': None if denominator else 'zero_actual_sum'}
