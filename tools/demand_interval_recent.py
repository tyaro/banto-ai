"""One fixed recency alternative, using only completed past target windows."""
import datetime as dt
from demand_forecasting import finite_quantity
from demand_interval import relative_total_interval


def calibrate_recent_completed(records, origin):
    if type(origin) is not dt.date or origin<dt.date(2017,1,1):
        raise ValueError('a 2017-or-later civil forecast origin is required')
    eligible=[];seen=set();excluded={'not_completed':0,'missing_total':0,'zero_prediction_scale':0}
    for record in records:
        end=dt.date.fromisoformat(record['target_end'])
        if end>=origin:
            excluded['not_completed']+=1
            continue  # Future values are never inspected.
        if end<dt.date(2016,1,1):raise ValueError('unexpected pre-2016 calibration endpoint')
        if end in seen:raise ValueError('duplicate completed target endpoint')
        seen.add(end)
        point,actual=record['prediction'],record['actual']
        if point is None or actual is None:
            excluded['missing_total']+=1;continue
        point,actual=finite_quantity(point),finite_quantity(actual)
        if point==0:
            excluded['zero_prediction_scale']+=1;continue
        eligible.append({'target_end':str(end),'score':finite_quantity(abs(actual-point)/point)})
    selected=sorted(eligible,key=lambda r:r['target_end'])[-25:]
    n=len(selected);rank=(4*(n+1)+4)//5
    radius=sorted(r['score'] for r in selected)[rank-1] if n>=20 and rank<=n else None
    return {'radius':radius,'support':n,'rank':rank,'scores':selected,'eligible_count':len(eligible),
        'excluded':excluded,'origin':str(origin),'latest_valid_completed_windows':25,'nominal_coverage':.8,
        'reason':None if radius is not None else 'insufficient_calibration_support',
        'coverage_guarantee_established':False}


__all__=['calibrate_recent_completed','relative_total_interval']
