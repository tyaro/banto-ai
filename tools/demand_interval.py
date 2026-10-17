"""Fixed nominal-80% relative-total interval, past calibration only.

The order statistic is conformal-inspired; temporal exchangeability and
future coverage are not established for this public-data research.
"""
import datetime as dt
from demand_forecasting import finite_quantity


def calibrate_relative_total(records, cutoff=dt.date(2017, 1, 1)):
    if type(cutoff) is not dt.date or cutoff != dt.date(2017, 1, 1):
        raise ValueError('fixed 2017 calibration cutoff required')
    scores=[];dates=set();excluded={'after_cutoff':0,'missing_total':0,'zero_prediction_scale':0}
    for record in records:
        end=dt.date.fromisoformat(record['target_end'])
        if end>=cutoff:
            excluded['after_cutoff']+=1
            continue  # Do not inspect the future numeric payload.
        if end<dt.date(2016, 1, 1):
            raise ValueError('calibration endpoint must be in fixed 2016 period')
        if end in dates:
            raise ValueError('duplicate calibration target endpoint')
        dates.add(end)
        predicted,actual=record['prediction'],record['actual']
        if predicted is None or actual is None:
            excluded['missing_total']+=1
            continue
        predicted,actual=finite_quantity(predicted),finite_quantity(actual)
        if predicted==0:
            excluded['zero_prediction_scale']+=1
            continue
        score=finite_quantity(abs(actual-predicted)/predicted)
        scores.append({'target_end':str(end),'score':score})
    n=len(scores)
    # ceil((n+1)*0.8), using exact integer arithmetic.
    rank=(4*(n+1)+4)//5
    radius=sorted(row['score'] for row in scores)[rank-1] if n>=20 and rank<=n else None
    return {'radius':radius,'support':n,'rank':rank,'nominal_coverage':.8,'minimum_support':20,
        'scores':scores,'excluded':excluded,'cutoff_exclusive':str(cutoff),
        'reason':None if radius is not None else 'insufficient_calibration_support',
        'coverage_guarantee_established':False}


def relative_total_interval(point, calibration):
    if point is None or calibration['radius'] is None:
        return {'lower':None,'upper':None,'width':None,'reason':'unknown_point_or_calibration'}
    point=finite_quantity(point);radius=finite_quantity(calibration['radius'])
    if point==0:
        return {'lower':None,'upper':None,'width':None,'reason':'zero_point_scale'}
    lower=max(0.,point*(1-radius));upper=finite_quantity(point*(1+radius))
    return {'lower':lower,'upper':upper,'width':upper-lower,'reason':None,
        'lower_clipped_at_zero':radius>1,'nominal_coverage':.8,'coverage_guarantee_established':False}
