"""Exploratory analysis of the opened CARE holdout (docs/research/care-next-direction-2026-10-18.md).

Reads gitignored artifacts only; extract_status.py writes the CARE-derived status table to
artifacts/care-next-direction-20261018/ (never commit it). Numbers are exploratory, not acceptance results.
"""
import json, pickle, sys
from pathlib import Path
from collections import defaultdict
import numpy as np
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT/'models/mini-transformer'))
from care_alarm import PREDICTION, COMMON
status=pickle.load(open((ROOT/'artifacts/care-next-direction-20261018/status.pkl'),'rb'))
def load(units_glob,scores,farmname=None):
    pe={}
    for e in json.load(open(scores/'per-event.json')):
        e=dict(e);e.setdefault('farm',farmname);e.setdefault('start',e.get('annotated_interval_start_availability'));e.setdefault('end',e.get('annotated_interval_end_availability'))
        e.setdefault('interval_hours',(e['end']-e['start'])/3600 if e['start'] else None)
        mm=e['methods']['neural-common'];mm.setdefault('hit_72h',mm.get('hit'))
        pe[(e['farm'],e['event_id'])]=e
    out=[]
    for d in units_glob:
        prof=json.load(open(d/'input.json'))['profile'];thr=json.load(open(d/'thresholds.json'))['methods']['neural']['threshold']
        farm=farmname or d.name.split('-fold-')[0]
        rows=list(PREDICTION.iter_unpack((d/'test.bin').read_bytes()))
        by=defaultdict(list)
        for r in rows: by[r[0]].append(r)
        R=[s['R64'] for s in prof['alarm_scales']]
        for ev,rs in by.items():
            a=np.array([[r[4],bool(r[5]&COMMON),r[12],r[6],r[7]] for r in rs],dtype=float)
            out.append(dict(farm=farm,ev=ev,asset=prof['test_asset'],thr=thr,R=R,meta=pe[(farm,ev)],avail=a[:,0],common=a[:,1]>0,score=a[:,2],y1=a[:,3],y2=a[:,4]))
    return out
BC=load(sorted((ROOT/'artifacts/care-holdout-20261018/units').iterdir()),ROOT/'artifacts/care-holdout-scores-20261018')
A=load([ROOT/f'artifacts/care-learning-fold-{k}-20261016' for k in range(5)],ROOT/'artifacts/care-learning-scores-20261016','A')
print('A files',len(A),'BC files',len(BC))
for name,fs in (('A',A),('B',[f for f in BC if f['farm']=='B']),('C',[f for f in BC if f['farm']=='C'])):
    norm=[f for f in fs if f['meta']['event_label']=='normal']
    ratios=[np.quantile(f['score'][f['common']],.995)/f['thr'] for f in norm]
    exc=[(f['score'][f['common']]>f['thr']).mean()*100 for f in norm]
    print(f"{name}: normal files {len(norm)}  thr median {np.median([f['thr'] for f in fs]):.3f} (min {min(f['thr'] for f in fs):.3f} max {max(f['thr'] for f in fs):.3f})  test q99.5/thr median {np.median(ratios):.2f} (IQR {np.quantile(ratios,.25):.2f}-{np.quantile(ratios,.75):.2f})  exceed% median {np.median(exc):.2f} mean {np.mean(exc):.2f} (design 0.5)")
# anomaly separation within file
print('\nanomaly events: in-window vs pre-window exceedance (same file, same thr) and score AUC in-window vs out-window')
summ=defaultdict(list)
for fs,name in ((A,'A'),(BC,'BC')):
    for f in fs:
        m=f['meta']
        if m['event_label']!='normal':
            c=f['common'];s=f['score'];inw=(f['avail']>=m['start'])&(f['avail']<=m['end'])
            if (inw&c).sum()<10 or ((~inw)&c).sum()<10: continue
            ei=(s[inw&c]>f['thr']).mean();eo=(s[(~inw)&c]>f['thr']).mean()
            x=s[inw&c];y=s[(~inw)&c]
            # AUC via average ranks (ties count 1/2, as in the Mann-Whitney U statistic)
            allv=np.concatenate([x,y]);order=allv.argsort(kind='stable');sv=allv[order];ranks=np.empty(len(allv))
            starts=np.r_[0,np.flatnonzero(np.diff(sv))+1];ends=np.r_[starts[1:],len(sv)]
            for a0,b0 in zip(starts,ends):ranks[order[a0:b0]]=(a0+1+b0)/2
            auc=(ranks[:len(x)].sum()-len(x)*(len(x)+1)/2)/(len(x)*len(y))
            q_in=np.quantile(x,.995)/f['thr'];q_out=np.quantile(y,.995)/f['thr']
            summ[name].append((f['farm'],f['ev'],f['asset'],round(ei*100,2),round(eo*100,2),auc,round(q_in,2),round(q_out,2),m['interval_hours'],m['methods']['neural-common']['hit_72h']))
for name,v in summ.items():
    print(name,'farm ev asset exc_in% exc_out% AUC q995in/thr q995out/thr window_h hit72')
    for r in sorted(v,key=lambda r:-r[5]): print(' ',*r[:5],round(r[5],2),*r[6:])
    aucs=np.array([r[5] for r in v]);print(name,'median AUC',round(float(np.median(aucs)),3),'AUC>=0.7:',(aucs>=.7).sum(),'/',len(aucs),' exc_in>2*exc_out:',sum(r[3]>2*max(r[4],0.1) for r in v))
# C:2 zero dropouts: episodes within 128 rows after a zero-row
f=[f for f in BC if f['farm']=='C' and f['ev']==36][0]
z=(f['y1']==0)|(f['y2']==0);print('\nC:2 ev36 zero rows',z.sum(),'of',len(z))
after=np.zeros(len(z),bool)
for i in np.where(z)[0]: after[i:i+129]=True
exc=(f['score']>f['thr'])&f['common'];print('exceeding rows',exc.sum(),'of which within 128 rows after a zero',(exc&after).sum())
# zero rows across all B/C normal/anomaly files
for lab in ('normal','anomaly'):
    zs=[(f['farm'],f['ev'],int(((f['y1']==0)|(f['y2']==0)).sum())) for f in BC if f['meta']['event_label']==lab and ((f['y1']==0)|(f['y2']==0)).any()]
    print(lab,'files with zero temps:',zs)
