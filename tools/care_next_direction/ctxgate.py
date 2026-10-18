"""Exploratory analysis of the opened CARE holdout (docs/research/care-next-direction-2026-10-18.md).

Reads gitignored artifacts only; extract_status.py writes the CARE-derived status table to
artifacts/care-next-direction-20261018/ (never commit it). Numbers are exploratory, not acceptance results.
"""
from pathlib import Path
import numpy as np, sys
sys.argv=['x']
exec(open(Path(__file__).with_name('whatif.py')).read().split("print('EXPLORATORY")[0])
def ctx_gate(f):
    z=(f['y1']==0.0)|(f['y2']==0.0);after=np.zeros(len(z),bool)
    for i in np.where(z)[0]: after[i:i+129]=True
    return f['common']&~after
evaluate('contract + context gate(128 after zero)',lambda f:(f['score'],np.full(len(f['score']),f['thr']),ctx_gate(f)))
def selfcal2(burn=1008,p=.995):
    def r(f):
        elig=ctx_gate(f);s=f['score'][:burn][elig[:burn]];t=np.full(len(f['score']),np.nan)
        if len(s)>=512:t[burn:]=np.quantile(s,p)
        return f['score'],t,elig
    return r
evaluate('ctx gate + self-cal 7d q99.5',selfcal2())
def rolling2(win=1008,lag=144,p=.995):
    def r(f):
        elig=ctx_gate(f);s=f['score'];t=np.full(len(s),np.nan)
        for i in range(win+lag,len(s)):
            w=s[i-win-lag:i-lag][elig[i-win-lag:i-lag]]
            if len(w)>=512:t[i]=np.quantile(w,p)
        return s,t,elig
    return r
evaluate('ctx gate + rolling 7d lag1d q99.5',rolling2())
evaluate('ctx gate + rolling 7d lag1d q99.9',rolling2(p=.999))
