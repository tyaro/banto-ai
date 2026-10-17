"""Past prequential weekday errors, EMA levels, and uncalibrated sigma diagnostics."""
import datetime as dt
import math
from demand_weekly_history import quantity

MIN_SUPPORT=20


def _ema(rows, half_life):
    value=rows[0]['error'];last=dt.date.fromisoformat(rows[0]['date'])
    for row in rows[1:]:
        day=dt.date.fromisoformat(row['date']);retention=2**(-(day-last).days/half_life)
        value=retention*value+(1-retention)*row['error'];last=day
    return value


def _summarize(rows, origin):
    for row in rows:
        if dt.date.fromisoformat(row['date'])>=origin:raise ValueError('completed past error required')
        e=row['error']
        if type(e) not in (int,float) or not math.isfinite(e):raise ValueError('finite residual required')
    n=len(rows);available=n>=MIN_SUPPORT
    mean=math.fsum(row['error'] for row in rows)/n if available else None
    sigma=math.hypot(*(row['error']-mean for row in rows))/math.sqrt(n-1) if available else None
    rmse=math.hypot(*(row['error'] for row in rows))/math.sqrt(n) if available else None
    fast=_ema(rows,7) if available else None;slow=_ema(rows,28) if available else None
    return {'available':available,'reason':None if available else 'past_residual_support',
            'support':n,'mean_error':mean,'sample_sigma':sigma,'RMSE':rmse,
            'EMA7':fast,'EMA28':slow,'fast_minus_slow':fast-slow if available else None,
            'last_error_date':rows[-1]['date'] if rows else None,
            'staleness_days':(origin-dt.date.fromisoformat(rows[-1]['date'])).days-1 if rows else None,
            'sigma_target':'historical_one_step_weekday_error',
            'future_sigma_by_horizon':None,'prediction_intervals':None,'coverage_guaranteed':False}


def describe_history(history, origin):
    if type(origin) is not dt.date:raise ValueError('local origin date required')
    past=[origin-dt.timedelta(days=k) for k in range(56,0,-1)]
    cache={d:(None if (v:=history.get(d)) is None else quantity(v)) for d in past}
    residuals=[];ledger=[]
    for offset in range(28,0,-1):
        day=origin-dt.timedelta(days=offset)
        dates=[day-dt.timedelta(days=k) for k in range(28,0,-1)]
        kept=[cache[d] for d in dates if d.weekday()==day.weekday() and cache[d] is not None]
        baseline=math.fsum(kept)/len(kept) if len(kept)>=3 else None
        actual=cache[day];error=actual-baseline if actual is not None and baseline is not None else None
        row={'date':str(day),'actual':actual,'baseline':baseline,'weekday_support':len(kept),
             'error':error,'reason':'missing_observation' if actual is None else 'weekday_support' if baseline is None else None}
        ledger.append(row)
        if error is not None:residuals.append(row)
    return {'origin':str(origin),'past_start':str(past[0]),'past_end':str(past[-1]),
            'residual_ledger':ledger,**_summarize(residuals,origin),
            'operating_status':'unknown','quantity_effect_or_interval_verified':False}


def combine_saved_baseline(baseline, profile):
    if baseline is None or len(baseline)!=14 or any(v is None for v in baseline):
        return {'available':False,'ema_daily':None,'blend_daily':None,'ema_total':None,'blend_total':None,
                'fallback':False,'reason':'baseline_unavailable','weight':.5}
    values=[quantity(v) for v in baseline]
    correction=profile['EMA7'] if profile['available'] else 0.
    if type(correction) not in (int,float) or not math.isfinite(correction):raise ValueError('finite EMA level required')
    component=[max(0.,b+correction) for b in values]
    blend=[.5*b+.5*p for b,p in zip(values,component)]
    return {'available':True,'ema_daily':component,'blend_daily':blend,
            'ema_total':math.fsum(component),'blend_total':math.fsum(blend),
            'fallback':not profile['available'],'reason':profile['reason'] if not profile['available'] else None,
            'weight':.5,'sigma_used_to_change_point':False,'prediction_intervals':None}
