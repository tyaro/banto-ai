"""Encode as-of residual statistics as learned inputs, not fixed point corrections."""
import datetime as dt
import math
from demand_weekly_history import quantity
from demand_statistical_overlay import MIN_SUPPORT

COLUMNS=('mean_error_over_fit_scale','EMA7_over_fit_scale','EMA28_over_fit_scale',
         'error_sigma_over_fit_scale','residual_support_fraction','staleness_fraction',
         'statistics_available','staleness_known')


def encode_profile(profile, origin, scale):
    if type(origin) is not dt.date:raise ValueError('local origin date required')
    # Check forecast identity/time headers before accessing statistics payload.
    if profile['origin']!=str(origin) or profile['past_end']!=str(origin-dt.timedelta(days=1)):
        raise ValueError('profile origin and completed past cutoff must match')
    last=profile['last_error_date']
    if last is not None:
        day=dt.date.fromisoformat(last)
        if not origin-dt.timedelta(days=28)<=day<origin:raise ValueError('completed residual date required')
        age=(origin-day).days-1
    else:age=None
    u=quantity(scale)
    support=profile['support'];available=profile['available']
    if type(support) is not int or not 0<=support<=28 or type(available) is not bool or available!=(support>=MIN_SUPPORT):
        raise ValueError('explicit consistent residual support required')
    if (support==0)!=(last is None) or profile['staleness_days']!=age:
        raise ValueError('residual support and date metadata disagree')
    if u<=0:
        return {'columns':COLUMNS,'features':[0.]*8,'branch_available':False,
                'reason':'nonpositive_fit_scale','origin':str(origin),
                'point_changed':False,'calibrated_interval_provided':False}
    values=[]
    for name in ('mean_error','EMA7','EMA28','sample_sigma'):
        value=profile[name]
        if available:
            if type(value) not in (int,float) or not math.isfinite(value) or (name=='sample_sigma' and value<0):
                raise ValueError('valid supported statistics required')
            values.append(value/u)
        else:
            if value is not None:raise ValueError('unsupported statistics must remain null')
            values.append(0.)
    values.extend([support/28,age/28 if age is not None else 0.,float(available),float(age is not None)])
    if not all(math.isfinite(v) for v in values):raise ValueError('nonfinite statistical feature')
    return {'columns':COLUMNS,'features':values,'branch_available':True,
            'statistics_supported':available,'reason':None if available else 'past_residual_support',
            'origin':str(origin),'point_changed':False,'calibrated_interval_provided':False}
