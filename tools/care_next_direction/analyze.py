"""Exploratory analysis of the opened CARE holdout (docs/research/care-next-direction-2026-10-18.md).

Reads gitignored artifacts only; extract_status.py writes the CARE-derived status table to
artifacts/care-next-direction-20261018/ (never commit it). Numbers are exploratory, not acceptance results.
"""
import json, pickle, sys, math
from pathlib import Path
from collections import defaultdict, Counter
import numpy as np
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT/'models/mini-transformer'))
from care_alarm import PREDICTION, COMMON, episodes, event_result, calibration_threshold
U=ROOT/'artifacts/care-holdout-20261018/units'
SC=ROOT/'artifacts/care-holdout-scores-20261018'
status=pickle.load(open((ROOT/'artifacts/care-next-direction-20261018/status.pkl'),'rb'))
pe={(e['farm'],e['event_id']):e for e in json.load(open(SC/'per-event.json'))}
cfg=json.load(open(ROOT/'examples/configs/care-holdout-bc-20261018.json'))

# ---- load folds
folds=[]
for d in sorted(U.iterdir()):
    farm,_,k=d.name.partition('-fold-')
    inp=json.load(open(d/'input.json'));prof=inp['profile']
    th=json.load(open(d/'thresholds.json'))
    R=[s['R64'] for s in prof['alarm_scales']]
    rows=list(PREDICTION.iter_unpack((d/'test.bin').read_bytes()))
    cal=list(PREDICTION.iter_unpack((d/'calibration.bin').read_bytes()))
    byev=defaultdict(list)
    for r in rows: byev[r[0]].append(r)
    folds.append(dict(farm=farm,fold=int(k),test_asset=prof['test_asset'],val_asset=prof['validation_asset'],thr=th['methods']['neural']['threshold'],
        R=R,cal=cal,byev=byev,cal_anchor=th['calibration_anchor']))
print('folds',len(folds))

def arr(rows):
    a=np.array([[r[4],r[5],r[6],r[7],r[8],r[9],r[12]] for r in rows],dtype=float)
    return a  # avail, flags, y1,y2,p1,p2,score
MONTH=720.
# ---- per-file table (normal files)
tab=[];all_norm=[]
for F in folds:
    for ev,rows in F['byev'].items():
        meta=pe[(F['farm'],ev)];a=arr(rows);common=(a[:,1].astype(int)&COMMON)>0
        st=status[(F['farm'],ev)]['pred_status'];sids=np.array([st[r[1]][0] for r in rows])
        s=a[:,6];thr=F['thr']
        res1=(a[:,2]-a[:,4])/F['R'][0];res2=(a[:,3]-a[:,5])/F['R'][1]
        eps=episodes(rows,'neural-common',thr)
        exc=s>thr
        tab.append(dict(farm=F['farm'],ev=ev,asset=F['test_asset'],label=meta['event_label'],n=len(rows),hours=len(rows)/6,thr=thr,
            q995=float(np.quantile(s,.995)),q50=float(np.median(s)),q90=float(np.quantile(s,.9)),exc_frac=float(exc.mean()),
            exc_frac_st0=float(exc[sids==0].mean()) if (sids==0).any() else float('nan'),
            frac_st0=float((sids==0).mean()),exc_nonst0_share=float(((sids!=0)&exc).sum()/max(1,exc.sum())),
            bias1=float(np.median(res1)),bias2=float(np.median(res2)),
            mad1=float(np.median(np.abs(res1-np.median(res1)))),mad2=float(np.median(np.abs(res2-np.median(res2)))),
            drive1=float((np.abs(res1)>=np.abs(res2))[exc].mean()) if exc.any() else float('nan'),
            n_eps=len(eps),ep_hours=[(e['close']-e['open'])/3600 for e in eps],
            status_counts=Counter(sids.tolist()),pred_start=status[(F['farm'],ev)]['pred_start'],
            open_status=Counter(st[e['open_ordinal']][0] for e in eps),
            ))
T=[t for t in tab if t['label']=='normal']
print('\n== normal files:',len(T))
print('farm ev asset hours thr q995 q50 exc% exc%st0 st0% nonst0share bias1 bias2 drive1 n_eps median_ep_h max_ep_h')
for t in sorted(T,key=lambda t:-t['n_eps']):
    eh=t['ep_hours']
    print(f"{t['farm']} {t['ev']:3d} {t['asset']:>3} {t['hours']:7.0f} {t['thr']:.3f} {t['q995']:.3f} {t['q50']:.3f} {100*t['exc_frac']:5.2f} {100*t['exc_frac_st0']:5.2f} {100*t['frac_st0']:5.1f} {t['exc_nonst0_share']:.2f} {t['bias1']:+.2f} {t['bias2']:+.2f} {t['drive1']:.2f} {t['n_eps']:3d} {np.median(eh) if eh else 0:5.1f} {max(eh) if eh else 0:6.1f} {t['pred_start'][:7]}")
# aggregate: episode length distribution
eh=np.array([h for t in T for h in t['ep_hours']])
print('\nfalse episodes',len(eh),'total alarm h',eh.sum().round(1),'median ep h',np.median(eh),'share of alarm time in episodes >=6h',eh[eh>=6].sum()/eh.sum(),'>=24h',eh[eh>=24].sum()/eh.sum(),'n>=6h',(eh>=6).sum(),'n>=24h',(eh>=24).sum(), 'n<=1h',(eh<=1).sum())
# status at open
oc=Counter();
for t in T: oc.update(t['open_status'])
print('status at false-episode open',oc)
tot=Counter()
for t in T: tot.update(t['status_counts'])
print('status rows in normal test files',tot)
# ratio q995/thr by farm
for farm in 'BC':
    r=[t['q995']/t['thr'] for t in T if t['farm']==farm]
    print(farm,'q995/thr median',np.median(r).round(2),'min',min(r).__round__(2),'max',max(r).__round__(2),'files with ratio>1:',sum(x>1 for x in r),'/',len(r))
# thresholds in deg C
for farm in 'BC':
    fs=[F for F in folds if F['farm']==farm]
    print(farm,'thr(R units) median',np.median([F['thr'] for F in fs]).round(3),'R1 median',np.median([F['R'][0] for F in fs]).round(2),'R2',np.median([F['R'][1] for F in fs]).round(2),
          'thr degC temp1',np.median([F['thr']*F['R'][0] for F in fs]).round(2),'temp2',np.median([F['thr']*F['R'][1] for F in fs]).round(2))
# calibration vs test (status0 normal) exceedance share by top assets
print('\nexceedance drive by temp1 (share of exceeding rows where temp1 residual dominates), normal, by farm')
for farm in 'BC':
    print(farm,np.nanmean([t['drive1'] for t in T if t['farm']==farm]).round(2))

# ---- time position: exceedance fraction by quarter of prediction span for normal files (pooled)
print('\nexceedance fraction by position quartile within prediction span (normal, farm C/B):')
for farm in 'BC':
    q=[[],[],[],[]]
    for F in folds:
        if F['farm']!=farm: continue
        for ev,rows in F['byev'].items():
            if pe[(farm,ev)]['event_label']!='normal':continue
            a=arr(rows);s=a[:,6];n=len(s)
            for i in range(4): q[i].append((s[i*n//4:(i+1)*n//4]>F['thr']).mean())
    print(farm,[round(float(np.mean(x))*100,2) for x in q])

# ---- calendar: calibration window month vs test month? use season of pred_start
print('\nnormal-file false episodes by prediction start month (C):')
mc=Counter();hc=Counter()
for t in T:
    if t['farm']=='C': mc[t['pred_start'][5:7]]+=t['n_eps'];hc[t['pred_start'][5:7]]+=t['hours']
print({m:(mc[m],round(hc[m])) for m in sorted(hc)})

pickle.dump(dict(tab=tab),open((ROOT/'artifacts/care-next-direction-20261018/tab.pkl'),'wb'))
