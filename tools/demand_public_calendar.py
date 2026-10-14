"""Single-series nominal calendar inputs for observed sales, not open-day sales."""
import datetime as dt
import math
from demand_weekly_history import quantity

EVENTS = ('01-01','05-01','05-24','08-10','10-09','11-02','11-03','12-25')
COLUMNS = tuple((kind, offset) for kind in EVENTS for offset in range(-3,4))
POLICY = 'nominal-8-fixed-month-days-v1'


def matches(day):
    result = []
    for kind in EVENTS:
        for year in range(max(1,day.year-1), min(9999,day.year+1)+1):
            event = dt.date.fromisoformat(f'{year:04}-{kind}')
            offset = (day-event).days
            if -3 <= offset <= 3:
                result.append((kind, offset, year))
    return result


def calendar(day, mode, enabled):
    if type(day) is not dt.date or mode not in ('on_day','pre_post') or len(enabled)!=56 or any(type(x) is not bool for x in enabled):
        raise ValueError('calendar date, fixed mode and 56 support flags required')
    length = 366 if day.year%4==0 and (day.year%100!=0 or day.year%400==0) else 365
    annual = 2*math.pi*(day-dt.date(day.year,1,1)).days/length
    weekly = 2*math.pi*day.weekday()/7
    active = {(kind,offset) for kind,offset,_ in matches(day)}
    flags=[float(allowed and (kind,offset) in active and (mode=='pre_post' or offset==0))
           for (kind,offset),allowed in zip(COLUMNS,enabled)]
    return [math.sin(weekly),math.cos(weekly),math.sin(annual),math.cos(annual),*flags]


def build_inputs(history, origin, scale, mode, enabled):
    if type(origin) is not dt.date:
        raise ValueError('local origin date required')
    u=quantity(scale)
    past=[origin-dt.timedelta(days=k) for k in range(56,0,-1)]
    future=[origin+dt.timedelta(days=k) for k in range(14)]
    raw=[history.get(d) for d in past]
    observed=[v is not None for v in raw]
    values=[quantity(v) if good else 0. for v,good in zip(raw,observed)]
    kept=[v for v,good in zip(values,observed) if good]
    stats=None
    if kept and u>0:
        mean=math.fsum(kept)/len(kept)
        std=math.hypot(*(v-mean for v in kept))/math.sqrt(len(kept))
        stats=[mean/u,std/max(mean,.01*u)]
    counts=[sum(good and day.weekday()==weekday for day,good in zip(past[-28:],observed[-28:])) for weekday in range(7)]
    means=[math.fsum(v for d,v,good in zip(past[-28:],values[-28:],observed[-28:])
                      if good and d.weekday()==w)/counts[w] if counts[w]>=3 else None for w in range(7)]
    baseline=[means[d.weekday()] for d in future]
    reasons=[]
    if u<=0:reasons.append('nonpositive_fit_scale')
    if not kept:reasons.append('no_observed_context')
    if None in baseline:reasons.append('weekday_support')
    return {'origin':str(origin),'past_end':str(past[-1]),'scale':u,
            'values':values,'observed':observed,'normalized_values':[v/u for v in values] if u>0 else None,
            'context_statistics':stats,'baseline':baseline,'weekday_support':counts,
            'past_calendar':[calendar(d,mode,enabled) for d in past],
            'future_calendar':[calendar(d,mode,enabled) for d in future],
            'available':not reasons,'reasons':reasons,'mode':mode,'policy':POLICY,
            'sales_estimand':'observed_sales_mean','operating_status':'unknown',
            'nominal_closure_mask_applied':False,'period_length_supplied':False}


def fit_support(keys, observed, cutoff=dt.date(2015,1,1)):
    """Count distinct target store/date and event years without reading quantity.

    observed maps (integer store, local date) to bool. Entire target-window
    cutoff is checked before accessing its observation mask.
    """
    seen=set(); labels={column:set() for column in COLUMNS}; years={column:set() for column in COLUMNS}
    for store,origin in keys:
        if type(store) is not int or type(origin) is not dt.date or origin+dt.timedelta(days=13)>=cutoff:
            raise ValueError('fit identity or label cutoff violation')
        if (store,origin) in seen:raise ValueError('duplicate fit key')
        seen.add((store,origin))
        for offset in range(14):
            target=origin+dt.timedelta(days=offset)
            good=observed.get((store,target))
            if type(good) is not bool:raise ValueError('complete explicit observation mask required')
            if good:
                for kind,relative,year in matches(target):
                    labels[kind,relative].add((store,target));years[kind,relative].add(year)
    channels=[{'kind':kind,'relative_day':offset,'distinct_store_dates':len(labels[kind,offset]),
               'event_years':sorted(years[kind,offset]),'enabled':bool(labels[kind,offset])}
              for kind,offset in COLUMNS]
    return {'policy':POLICY,'cutoff_exclusive':str(cutoff),'keys':len(seen),
            'channels':channels,'enabled':[row['enabled'] for row in channels],
            'operating_calendar_verified':False,'duration_effect_verified':False}
