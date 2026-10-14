"""Temporal fit boundary and finite, fixed-interval stopping policy."""
import datetime as dt
import math


def split_keys(keys, cutoff=dt.date(2014,7,1)):
    train, validation, crossing, seen = [], [], [], set()
    for store, text in keys:
        origin = dt.date.fromisoformat(text)
        key = (store,text)
        if type(store) is not int or key in seen or not dt.date(2013,1,1) <= origin < dt.date(2015,1,1):
            raise ValueError('distinct declared 2013-14 keys required')
        seen.add(key)
        if origin + dt.timedelta(days=13) < cutoff: train.append(key)
        elif origin >= cutoff: validation.append(key)
        else: crossing.append(key)
    return {'train':train,'validation':validation,'crossing':crossing,'cutoff':str(cutoff)}


def fit_scales(rows, stores, start=dt.date(2013,1,1), cutoff=dt.date(2014,7,1)):
    values, seen = {s:[] for s in stores}, set()
    for row in rows:
        store, day = int(row['store_nbr']), dt.date.fromisoformat(row['date'])
        # Select metadata first; no validation values or masks affect normalization.
        if store not in values or not start <= day < cutoff: continue
        if (store,day) in seen: raise ValueError('duplicate fit observation')
        seen.add((store,day)); mask = row['observed']
        if mask not in ('0','1') or (mask=='1') != bool(row['sales']): raise ValueError('explicit quantity mask required')
        if mask == '1':
            value = float(row['sales'])
            if not math.isfinite(value) or value < 0: raise ValueError('finite nonnegative fit quantity required')
            values[store].append(value)
    expected = {(s,start+dt.timedelta(days=k)) for s in stores for k in range((cutoff-start).days)}
    if seen != expected: raise ValueError('complete declared fit calendar required')
    return {str(s):{'scale':math.fsum(v)/len(v) if v else None,'observed_days':len(v),
                   'calendar_days':(cutoff-start).days} for s,v in values.items()}


class EarlyStopper:
    def __init__(self, interval=128, warmup=512, patience=6, min_relative=1e-4):
        if any(type(v) is not int or v<=0 for v in (interval,warmup,patience)) or warmup%interval or not 0<min_relative<1:
            raise ValueError('fixed valid stopping policy required')
        self.interval,self.warmup,self.patience,self.min_relative = interval,warmup,patience,min_relative
        self.last_step,self.best_step,self.best,self.meaningful_best,self.bad = -interval,None,None,None,0
        self.stopped = False

    def observe(self,step,value):
        if self.stopped or type(step) is not int or step != self.last_step+self.interval:
            raise ValueError('fresh consecutive checkpoint required')
        if type(value) not in (int,float) or not math.isfinite(value) or value<0:
            raise ValueError('finite nonnegative fixed validation loss required')
        self.last_step = step
        new_best = self.best is None or value < self.best
        if new_best: self.best,self.best_step = value,step
        meaningful = self.meaningful_best is None or value < self.meaningful_best*(1-self.min_relative)
        if meaningful: self.meaningful_best,self.bad = value,0
        elif step >= self.warmup: self.bad += 1
        self.stopped = step >= self.warmup and self.bad >= self.patience
        return {'new_best':new_best,'meaningful_improvement':meaningful,'stop':self.stopped,
                'best_step':self.best_step,'best_validation_loss':self.best,'bad_checkpoints':self.bad}
