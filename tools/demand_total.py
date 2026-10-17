"""One fixed total candidate, independent of the retained daily shape."""
import datetime as dt
import hashlib,json,math
from demand_forecasting import finite_quantity,past_observations


def recent_fourteen_total(history, origin):
    start=origin-dt.timedelta(days=14)
    past=[(d,v) for d,v in past_observations(history,origin) if d>=start]
    raw=json.dumps([[str(d),v] for d,v in past],separators=(',',':'),allow_nan=False).encode()
    total=finite_quantity(14*math.fsum(v for d,v in past)/len(past)) if len(past)>=12 else None
    return {'total':total,'support':len(past),'source_dates':[str(d) for d,v in past],
        'input_sha256':hashlib.sha256(raw).hexdigest(),'reason':None if total is not None else 'fewer_than_twelve_observed_past_days',
        'missing_not_zero_filled':True}


def rescale_retained_shape(profile, total):
    if len(profile)!=14:raise ValueError('fixed fourteen-day profile required')
    if total is None or any(v is None for v in profile):
        return {'predictions':[None]*14,'reason':'unknown_total_or_incomplete_shape','scale':None,'predicted_total':None}
    total=finite_quantity(total);values=[finite_quantity(v) for v in profile];denominator=math.fsum(values)
    if total==0:
        predictions,scale,reason=[0.]*14,0.,None
    elif denominator==0:
        predictions,scale,reason=[None]*14,None,'zero_shape_with_positive_total'
    else:
        scale=total/denominator
        predictions=[finite_quantity(v*scale) for v in values];reason=None
    output=math.fsum(predictions) if reason is None else None
    if output is not None and not math.isclose(output,total,rel_tol=1e-12,abs_tol=1e-9):
        raise ArithmeticError('requested total differs from allocated total')
    return {'predictions':predictions,'reason':reason,'scale':scale,'predicted_total':output}
