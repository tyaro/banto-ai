"""Exploratory analysis of the opened CARE holdout (docs/research/care-next-direction-2026-10-18.md).

Reads gitignored artifacts only; extract_status.py writes the CARE-derived status table to
artifacts/care-next-direction-20261018/ (never commit it). Numbers are exploratory, not acceptance results.
"""
import json, pickle, sys, math
from pathlib import Path
from collections import defaultdict, Counter
import numpy as np
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT/'models/mini-transformer'))
from care_alarm import PREDICTION, COMMON
U=ROOT/'artifacts/care-holdout-20261018/units'; SC=ROOT/'artifacts/care-holdout-scores-20261018'
status=pickle.load(open((ROOT/'artifacts/care-next-direction-20261018/status.pkl'),'rb'))
pe={(e['farm'],e['event_id']):e for e in json.load(open(SC/'per-event.json'))}
MONTH=720.
files=[]  # one entry per (fold, test event)
for d in sorted(U.iterdir()):
    farm,_,k=d.name.partition('-fold-'); prof=json.load(open(d/'input.json'))['profile']
    thr=json.load(open(d/'thresholds.json'))['methods']['neural']['threshold']
    cal=np.array([r[12] for r in PREDICTION.iter_unpack((d/'calibration.bin').read_bytes())])
    R=[s['R64'] for s in prof['alarm_scales']]
    rows=list(PREDICTION.iter_unpack((d/'test.bin').read_bytes()))
    byev=defaultdict(list)
    for r in rows: byev[r[0]].append(r)
    for ev,rs in byev.items():
        st=status[(farm,ev)]['pred_status']
        a=np.array([[r[4],bool(r[5]&COMMON),r[6],r[7],r[8],r[9],r[12],st[r[1]][0]] for r in rs],dtype=float)
        files.append(dict(farm=farm,ev=ev,asset=f'{farm}:{prof["test_asset"]}',meta=pe[(farm,ev)],thr=thr,cal=cal,R=R,
            avail=a[:,0],common=a[:,1]>0,y1=a[:,2],y2=a[:,3],p1=a[:,4],p2=a[:,5],score=a[:,6],status=a[:,7].astype(int)))

def run_episodes(f,score,thr_arr,elig,n_open=3,n_close=3):
    """thr_arr: per-row threshold (nan = row not usable for alarm, treated like ineligible)."""
    high=low=0;active=None;last=None;out=[]
    def close(at):
        nonlocal active
        if active is not None and at>active['open']: out.append({**active,'close':at})
        active=None
    for i in range(len(score)):
        if not elig[i] or not np.isfinite(thr_arr[i]):
            if last is not None: close(last+600)
            high=low=0;last=None;continue
        if last is not None and f['avail'][i]-last!=600: close(last+600);high=low=0
        if score[i]>thr_arr[i]:
            high+=1;low=0
            if active is None and high>=n_open: active={'open':f['avail'][i]}
        else:
            low+=1;high=0
            if active is not None and low>=n_close: close(f['avail'][i])
        last=f['avail'][i]
    if last is not None: close(last+600)
    return out

def evaluate(name,rule):
    """rule(f) -> (score, thr_arr, elig). Returns metrics."""
    hits={24:0,72:0};att={24:0,72:0};false=0;normal_h=0.;per_asset=defaultdict(lambda:[0,0.]);off=0;alarm_h=0.
    for f in files:
        score,thr_arr,elig=rule(f)
        eps=run_episodes(f,score,thr_arr,elig)
        usable=elig&np.isfinite(thr_arr)
        m=f['meta']
        if m['event_label']=='normal':
            false+=len(eps);h=usable.sum()/6;normal_h+=h;per_asset[f['asset']][0]+=len(eps);per_asset[f['asset']][1]+=h
            alarm_h+=sum(e['close']-e['open'] for e in eps)/3600
        else:
            s,e=m['start'],m['end'];cands=[x for x in eps if s<=x['open']<=e]
            lead=(e-min(x['open'] for x in cands))/3600 if cands else None
            for W in (24,72):
                if m['attainable'][str(W)]:
                    att[W]+=1
                    if lead is not None and lead>=W: hits[W]+=1
            off+=sum(1 for x in eps if not s<=x['open']<=e)
    rate=false/(normal_h/MONTH)
    within=sum(1 for a,(n,h) in per_asset.items() if h>0 and n/(h/MONTH)<=1.0);n_assets=sum(1 for a,(n,h) in per_asset.items() if h>0)
    worst=max(((n/(h/MONTH)) ,a) for a,(n,h) in per_asset.items() if h>0)
    print(f"{name:34s} det72 {hits[72]:2d}/{att[72]} ({100*hits[72]/att[72]:4.0f}%)  det24 {hits[24]:2d}/{att[24]} ({100*hits[24]/att[24]:4.0f}%)  false {false:3d} -> {rate:5.2f}/asset-30d  assets<=1.0: {within:2d}/{n_assets}  worst {worst[0]:5.1f} ({worst[1]})  off-window {off:3d}  alarm% {100*alarm_h/normal_h:4.2f}")
    return rate

def base(f): return f['score'],np.full(len(f['score']),f['thr']),f['common']
def q(f,p):
    c=np.sort(f['cal']);i=min(len(c)-1,(int(p*1000)*len(c)+999)//1000-1);return c[i]
def quant(p): return lambda f:(f['score'],np.full(len(f['score']),q(f,p)),f['common'])
def mult(k): return lambda f:(f['score'],np.full(len(f['score']),f['thr']*k),f['common'])
def zero_gate(f): return f['common']&~((f['y1']==0.0)|(f['y2']==0.0))
def gate_rule(f): return f['score'],np.full(len(f['score']),f['thr']),zero_gate(f)
def status_rule(f): return f['score'],np.full(len(f['score']),f['thr']),f['common']&(f['status']==0)
def selfcal(burn=1008,p=.995,gate=False,floor=False):
    def r(f):
        elig=zero_gate(f) if gate else f['common']
        s=f['score'][:burn][elig[:burn]]
        t=np.full(len(f['score']),np.nan)
        if len(s)>=512:
            v=np.quantile(s,p); t[burn:]=max(v,f['thr']) if floor else v
        return f['score'],t,elig
    return r
def rolling(win=1008,lag=144,p=.995,gate=False):
    def r(f):
        elig=zero_gate(f) if gate else f['common'];s=f['score'];t=np.full(len(s),np.nan)
        for i in range(win+lag,len(s)):
            w=s[i-win-lag:i-lag][elig[i-win-lag:i-lag]]
            if len(w)>=512: t[i]=np.quantile(w,p)
        return s,t,elig
    return r
def detrend(win=144,gate=False,k=1.0):
    """score on residual minus lagged rolling median residual (per channel), same thr*k"""
    def r(f):
        elig=zero_gate(f) if gate else f['common']
        out=np.full(len(f['score']),np.nan)
        r1=(f['y1']-f['p1'])/f['R'][0];r2=(f['y2']-f['p2'])/f['R'][1]
        for i in range(len(out)):
            lo=max(0,i-win-1);m1=np.median(r1[lo:i]) if i-lo>=12 else 0.;m2=np.median(r2[lo:i]) if i-lo>=12 else 0.
            out[i]=max(abs(r1[i]-m1),abs(r2[i]-m2))
        return out,np.full(len(out),f['thr']*k),elig
    return r
def combo(elig_fn,thr_fn,n_open,n_close):
    pass

print('EXPLORATORY what-ifs on opened B/C labels (neural-common); contract rule first')
evaluate('contract (q99.5, 3/3)',base)
evaluate('status0-only eligible',status_rule)
evaluate('zero-value gate',gate_rule)
evaluate('cal q99.9',quant(.999))
evaluate('thr x1.5',mult(1.5))
evaluate('thr x2',mult(2))
evaluate('thr x3',mult(3))
evaluate('self-cal first 7d q99.5',selfcal())
evaluate('self-cal 7d q99.5 +gate',selfcal(gate=True))
evaluate('self-cal 7d q99.9 +gate',selfcal(p=.999,gate=True))
evaluate('self-cal 7d q99.5 floor=contract +gate',selfcal(gate=True,floor=True))
evaluate('rolling 7d lag1d q99.5 +gate',rolling(gate=True))
evaluate('detrend 24h median +gate',detrend(gate=True))
evaluate('detrend 24h +gate thr x2',detrend(gate=True,k=2))
# persistence variants
def with_persist(rule,n_open,n_close):
    def r(f): return rule(f)
    r.persist=(n_open,n_close);return r
_orig=run_episodes
def run_episodes(f,score,thr_arr,elig,n_open=3,n_close=3,_o=_orig):
    return _o(f,score,thr_arr,elig,n_open,n_close)
def evaluate_p(name,rule,n_open,n_close):
    global run_episodes
    saved=run_episodes
    run_episodes=lambda f,s,t,e,_o=_orig,no=n_open,nc=n_close: _o(f,s,t,e,no,nc)
    try: evaluate(name,rule)
    finally: run_episodes=saved
evaluate_p('contract + persist 6/6',base,6,6)
evaluate_p('contract + persist 12/6',base,12,6)
evaluate_p('gate + x2 + persist 6/6',mult(2) and (lambda f:(f['score'],np.full(len(f['score']),f['thr']*2),zero_gate(f))),6,6)
evaluate_p('gate + x3 + persist 6/6',(lambda f:(f['score'],np.full(len(f['score']),f['thr']*3),zero_gate(f))),6,6)
evaluate_p('self-cal 7d q99.5 +gate + persist 6/6',selfcal(gate=True),6,6)
evaluate_p('self-cal 7d q99.9 +gate + persist 6/6',selfcal(p=.999,gate=True),6,6)
evaluate_p('self-cal 7d q99.5 +gate + persist 12/6',selfcal(gate=True),12,6)
