"""Numerical entry v2: consistent binary64 totals; exact QP core unchanged."""
import math
from demand_constrained_qp import (Budget, NumericFailure, VERSION, LIMITS, number, dot, solve)
from demand_constrained_qp import from_prefix as _v1_from_prefix

ENTRY_VERSION='consistent-binary64-totals-v2'


def quantity_total(values):
    if type(values) is not list or len(values)!=14:
        raise ValueError('14 daily quantities required')
    if any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in values):
        raise ValueError('finite nonnegative daily quantities required')
    return number(math.fsum(values))


def from_prefix(batch):
    built=_v1_from_prefix(batch)
    if not built['supported']:return built
    for source,row in zip(batch['rows'],built['problem']['rows']):
        B,Y=quantity_total(source['baseline']),quantity_total(source['raw_actual'])
        if number(row['B'])!=B or number(row['Y'])!=Y:
            raise NumericFailure('total_conversion_mismatch')
        row['B'],row['Y']=str(B),str(Y)
    return built


def predict_total(baseline,unit,x,beta):
    B=quantity_total(baseline);unit=number(unit)
    if unit<=0:raise ValueError('positive unit required')
    if B==0 or x is None:return B
    if type(x) is not list or type(beta) is not list or len(x)!=3 or len(beta)!=3:
        raise ValueError('three features and coefficients required')
    xx,bb=list(map(number,x)),list(map(number,beta));Budget().check(B,unit,xx,bb)
    return max(B+unit*dot(xx,bb),number(0))
