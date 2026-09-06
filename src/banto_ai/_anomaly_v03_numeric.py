"""Fixed binary64 arithmetic for S2; no fallback, I/O or fitted global state."""

from __future__ import annotations

import math


class NumericalInconclusive(ValueError):
    """A defined numerical failure, distinct from malformed input."""


def finite(value: float) -> float:
    if type(value) not in (int, float):
        raise ValueError("numeric value cannot be bool or nonnumeric")
    try:
        value = float(value)
    except OverflowError as exc:
        raise NumericalInconclusive("nonfinite") from exc
    if not math.isfinite(value):
        raise NumericalInconclusive("nonfinite")
    return value


def median(values) -> float:
    ordered = sorted(finite(v) for v in values)
    if not ordered:
        raise NumericalInconclusive("insufficient_points")
    n = len(ordered)
    return finite((ordered[(n-1)//2] + ordered[n//2])/2) if n % 2 == 0 else ordered[n//2]


def center_scale(values) -> tuple[float, float]:
    values = tuple(values)
    center = median(values)
    scale = finite(1.4826 * median(abs(x-center) for x in values))
    if scale <= 0:
        raise NumericalInconclusive("zero_scale")
    return center, scale


def _sum(values) -> float:
    """Fixed-order fsum with explicit nonfinite-product/overflow failure.

    math.fsum raises ValueError for mixed infinities and OverflowError for a
    finite intermediate sum overflow. Neither may escape as a software failure
    when a valid finite observation produces an undefined binary64 residual.
    """
    try:
        return finite(math.fsum(finite(value) for value in values))
    except (OverflowError, ValueError) as exc:
        raise NumericalInconclusive("nonfinite") from exc


def inverse4(matrix) -> tuple:
    """Cholesky factorization and four fixed-order triangular solves."""
    if len(matrix) != 4 or any(len(row) != 4 for row in matrix):
        raise ValueError("expected a 4 by 4 matrix")
    for i in range(4):
        for j in range(4):
            finite(matrix[i][j])
            if matrix[i][j] != matrix[j][i]:
                raise ValueError("covariance must be symmetric")
    lower = [[0.0]*4 for _ in range(4)]
    for i in range(4):
        for j in range(i+1):
            term = finite(matrix[i][j] - _sum(lower[i][k]*lower[j][k] for k in range(j)))
            if i == j:
                if term <= 0:
                    raise NumericalInconclusive("cholesky_failure")
                lower[i][j] = math.sqrt(term)
            else:
                lower[i][j] = finite(term/lower[j][j])
    inverse = [[0.0]*4 for _ in range(4)]
    for column in range(4):
        y, x = [0.0]*4, [0.0]*4
        for i in range(4):
            y[i] = finite(((1.0 if i == column else 0.0) - _sum(lower[i][k]*y[k] for k in range(i)))/lower[i][i])
        for i in range(3, -1, -1):
            x[i] = finite((y[i]-_sum(lower[k][i]*x[k] for k in range(i+1, 4)))/lower[i][i])
        for i in range(4):
            inverse[i][column] = x[i]
    if any(inverse[i][i] <= 0 for i in range(4)):
        raise NumericalInconclusive("cholesky_failure")
    return tuple(tuple(row) for row in inverse)


def conditional_fit(errors) -> tuple:
    """580 complete phase-1..29 vectors -> b, q, v, Sigma, Omega."""
    if len(errors) != 580 or any(len(row) != 4 for row in errors):
        raise NumericalInconclusive("insufficient_points")
    pairs = [center_scale(row[i] for row in errors) for i in range(4)]
    b, q = tuple(p[0] for p in pairs), tuple(p[1] for p in pairs)
    r = [tuple(finite((row[i]-b[i])/q[i]) for i in range(4)) for row in errors]
    mean = tuple(finite(_sum(row[i] for row in r)/580) for i in range(4))
    covariance = [[0.0]*4 for _ in range(4)]
    for i in range(4):
        for j in range(i+1):
            sample = finite(_sum((row[i]-mean[i])*(row[j]-mean[j]) for row in r)/579)
            # Keep the registered expression even on the diagonal.
            value = finite(0.75*sample + (0.25*sample if i == j else 0.0))
            covariance[i][j] = covariance[j][i] = value
    covariance = tuple(tuple(row) for row in covariance)
    return b, q, mean, covariance, inverse4(covariance)


def conditional_residual(errors, state, target: int | None = None):
    b, q, mean, _, precision = state
    centered = tuple(finite((errors[i]-b[i])/q[i]-mean[i]) for i in range(4))
    if target is not None and (type(target) is not int or not 0 <= target < 4):
        raise ValueError("invalid conditional target")
    indices = range(4) if target is None else (target,)
    values = tuple(finite(_sum(precision[i][j]*centered[j] for j in range(4))/math.sqrt(precision[i][i])) for i in indices)
    return values if target is None else values[0]
