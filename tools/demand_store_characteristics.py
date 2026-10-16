"""Descriptive pre-origin profiles, no labels, forecast fitting or clustering."""
import datetime as dt
import math

FIT=(6,7,10,13,15,17,19,23,26,27)
CLOSURES=('01-01','12-25')
FIELDS={'date','available_at','value'}

def day(s):
    d=dt.date.fromisoformat(s)
    if d.isoformat()!=s:raise ValueError('canonical day required')
    return d

def select_2013(csv_rows):
    selected={s:[] for s in FIT}
    for r in csv_rows:
        if r['store_nbr'] not in set(map(str,FIT)) or not '2013-01-01'<=r['date']<'2014-01-01':continue
        d=day(r['date']);s=int(r['store_nbr'])
        if r['observed'] not in ('0','1') or (r['observed']=='1')!=bool(r['sales']):raise ValueError('raw observation mismatch')
        v=float(r['sales']) if r['observed']=='1' else None
        if v is not None and (not math.isfinite(v) or v<0):raise ValueError('nonnegative finite quantity')
        selected[s].append({'date':str(d),'available_at':str(d+dt.timedelta(days=1)),'value':v})
    for s in FIT:
        selected[s].sort(key=lambda r:r['date'])
        expected=[str(dt.date(2013,1,1)+dt.timedelta(days=i)) for i in range(365)]
        if [r['date'] for r in selected[s]]!=expected:raise ValueError('complete unique 2013 FIT calendar required')
    return selected

def snapshot_packet(inp):
    o=day(inp['origin']);dates=inp['past_dates'];available=inp['past_available_at'];values=inp['past_values']
    if dates!=[str(o-dt.timedelta(days=i)) for i in range(56,0,-1)] or len(available)!=56 or len(values)!=56:raise ValueError('fixed past56')
    return [{'date':d,'available_at':a,'value':v} for d,a,v in zip(dates,available,values)]

def mean(values):return math.fsum(values)/len(values) if values else None

def profile(records,asof):
    at=day(asof);seen=set();raw=[]
    for r in records:
        if set(r)!=FIELDS:raise ValueError('past payload fields only')
        d=day(r['date']);a=day(r['available_at'])
        if d>=at or a>at or a!=d+dt.timedelta(days=1):raise ValueError('pre-origin availability required')
        if d in seen:raise ValueError('unique calendar dates required')
        seen.add(d);v=r['value']
        if v is not None and (type(v) not in (int,float) or not math.isfinite(v) or v<0):raise ValueError('raw quantity')
        raw.append((d,v))
    raw.sort();opened=[(d,v) for d,v in raw if d.isoformat()[5:] not in CLOSURES and v is not None]
    values=[v for d,v in opened];mu=mean(values);undefined=[]
    def ratio(n,d,field):
        if n is None or d is None or d==0:undefined.append(field);return None
        return n/d
    n=len(values);variance=math.fsum((v-mu)**2 for v in values)/n if n else None
    cv=ratio(math.sqrt(variance) if variance is not None else None,mu,'CV')
    weekdays={str(w):{'count':sum(d.weekday()==w for d,v in opened),'mean':mean([v for d,v in opened if d.weekday()==w])} for w in range(7)}
    between=math.fsum(g['count']*(g['mean']-mu)**2 for g in weekdays.values() if g['count']) if n else None
    total=variance*n if variance is not None else None
    strength=ratio(between,total,'weekday_variance_share')
    if strength is not None:strength=min(1.,max(0.,strength))
    residual_var=math.fsum((v-weekdays[str(d.weekday())]['mean'])**2 for d,v in opened)/n if n else None
    residual_relative=ratio(math.sqrt(residual_var) if residual_var is not None else None,mu,'weekday_adjusted_relative_variability')
    weekend_ratio=ratio(mean([v for d,v in opened if d.weekday()>=5]),mean([v for d,v in opened if d.weekday()<5]),'weekend_weekday_ratio')
    valid=dict(opened);pairs=[(valid[d-dt.timedelta(days=7)],v) for d,v in opened if d-dt.timedelta(days=7) in valid]
    corr=None
    if len(pairs)>=2:
        mx=mean([p[0] for p in pairs]);my=mean([p[1] for p in pairs]);sx=math.fsum((x-mx)**2 for x,y in pairs);sy=math.fsum((y-my)**2 for x,y in pairs)
        if sx>0 and sy>0:corr=math.fsum((x-mx)*(y-my) for x,y in pairs)/math.sqrt(sx*sy);corr=min(1.,max(-1.,corr))
    if corr is None:undefined.append('calendar_lag7_correlation')
    def calendar_groups(getter,size,name):
        out={}
        for k in range(1,size+1):
            v=[v for d,v in opened if getter(d)==k];m=mean(v)
            out[str(k)]={'count':len(v),'mean':m,'mean_relative_to_all':ratio(m,mu,name+'-'+str(k))}
        return out
    months=calendar_groups(lambda d:d.month,12,'month');quarters=calendar_groups(lambda d:(d.month-1)//3+1,4,'quarter')
    month_valid={k:v['mean'] for k,v in months.items() if v['mean'] is not None}
    month_range=ratio(max(month_valid.values())-min(month_valid.values()) if month_valid else None,mu,'month_level_range_ratio')
    recent=[v for d,v in opened if at-dt.timedelta(days=28)<=d<at];previous=[v for d,v in opened if at-dt.timedelta(days=56)<=d<at-dt.timedelta(days=28)]
    recent_ratio=ratio(mean(recent),mean(previous),'recent28_previous28_mean_ratio_minus1')
    counts={'calendar':len(raw),'raw_observed':sum(v is not None for d,v in raw),'raw_missing':sum(v is None for d,v in raw),'raw_zero':sum(v==0 for d,v in raw),
        'assumed_closure_days':sum(d.isoformat()[5:] in CLOSURES for d,v in raw),'closure_observed_zero':sum(d.isoformat()[5:] in CLOSURES and v==0 for d,v in raw),
        'closure_missing':sum(d.isoformat()[5:] in CLOSURES and v is None for d,v in raw),'open_observed':n,
        'open_missing':sum(d.isoformat()[5:] not in CLOSURES and v is None for d,v in raw),'open_zero':sum(v==0 for d,v in opened)}
    return {'asof':asof,'first_date':str(raw[0][0]) if raw else None,'last_date':str(raw[-1][0]) if raw else None,
        'last_available_at':max((r['available_at'] for r in records),default=None),'availability_basis':'source-calendar-next-day-assumed; actual-arrival-timezone-unknown',
        'years':sorted({str(d.year) for d,v in raw}),'counts':counts,'raw_observed_mean':mean([v for d,v in raw if v is not None]),
        'open_mean':mu,'open_CV':cv,'weekdays':weekdays,'weekday_variance_share_in_sample':strength,
        'weekday_adjusted_relative_variability':residual_relative,'weekend_weekday_ratio':weekend_ratio,
        'calendar_lag7_pairs':len(pairs),'calendar_lag7_correlation':corr,'months':months,'quarters':quarters,'month_level_range_ratio':month_range,
        'max_months':[k for k,v in month_valid.items() if v==max(month_valid.values())] if month_valid else [],
        'min_months':[k for k,v in month_valid.items() if v==min(month_valid.values())] if month_valid else [],
        'recent28_count':len(recent),'previous28_count':len(previous),'recent28_mean':mean(recent),'previous28_mean':mean(previous),
        'recent28_previous28_mean_ratio_minus1':recent_ratio-1 if recent_ratio is not None else None,
        'annual_seasonality_status':'not_identified_single_year_or_shorter','undefined':undefined,'fixed_class':None}
