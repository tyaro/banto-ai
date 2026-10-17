"""CARE r1 train-only reference statistics, baseline profile and batch schedule.

No Torch/model/optimizer/evaluator access. Weighted inverse CDF uses float64
fsum for equal-value masses and every queried cumulative mass. Renormalization
is cumulative_mass/total_mass, avoiding a drifting sequential cumulative sum.
Portable schedules are authoritative across languages; Python RNG seed alone
is not a claim of Rust RNG equivalence.
"""
from bisect import bisect_left
from itertools import groupby
import json
import math
from pathlib import Path
import random
import struct
from care_input import Consumer,CONTRACT_SHA,INPUT_SHA,RECIPE_SHA,pinned_input,no_truth
from metropt_multiday import ROOT,digest,verify_closed,f32

DATA_CLOSURE_SHA='3c5fc289fdafda0792acd9b5cdec6fcd8e91d7a93cb2a70a5df0b735eae8a352'
SCHEDULE_RECORD=struct.Struct('<III')  # asset ID, anchor event ID, origin ordinal
SAMPLER_SEED=20262016
UPDATES=4096
BATCH=8


def empirical(records,p):
    """Smallest value with renormalized cumulative weight >= p; no interpolation."""
    if not 0<=p<=1 or not records:raise ValueError('empty/invalid quantile request')
    ordered=sorted(records,key=lambda t:t[0]);values=[];weights=[]
    for value,group in groupby(ordered,key=lambda t:t[0]):
        ws=[r[1] for r in group]
        if not math.isfinite(value) or any(not math.isfinite(w) or w<=0 for w in ws):raise ValueError('invalid quantile population')
        values.append(value);weights.append(math.fsum(ws))
    mass=math.fsum(weights)
    if not math.isfinite(mass) or mass<=0:raise ValueError('invalid quantile mass')
    left,right=0,len(values)-1
    while left<right:
        middle=(left+right)//2
        if math.fsum(weights[:middle+1])/mass>=p:right=middle
        else:left=middle+1
    i=left
    proof={'p':p,'value':values[i],'mass64':mass,'cdf_below64':math.fsum(weights[:i])/mass,'cdf_at64':math.fsum(weights[:i+1])/mass,
           'unique_values':len(values),'rows':len(records)}
    if (p>0 and not proof['cdf_below64']<p) or not proof['cdf_at64']>=p:raise ValueError('quantile boundary')
    return values[i],proof


def normal_rows(event):
    nt=event.meta['split_row_counts']['train']
    return [i for i in range(nt) if event._rows[i][2]==7 and event._normal[i//8]&(1<<(i%8))]


def normalization(populations):
    if len(populations)!=3 or any(not xs for xs in populations):raise ValueError('three supported train assets required')
    result=[];alarm=[]
    for channel in range(3):
        per_asset=[[row[channel] for row in xs] for xs in populations]
        mean=math.fsum(math.fsum(xs)/len(xs) for xs in per_asset)/3
        variance=math.fsum(math.fsum((x-mean)**2 for x in xs)/len(xs) for xs in per_asset)/3
        sigma=math.sqrt(variance);T=max(sigma,1e-5);floor=max(.01*sigma,1e-5)
        t32,floor32=f32(T),f32(floor)
        if not all(math.isfinite(x) for x in (mean,variance,sigma,T,floor,t32,floor32)) or min(T,floor,t32,floor32)<=0:
            raise ValueError('invalid normalization')
        result.append({'mean64':mean,'variance64':variance,'sigma64':sigma,'T64':T,'context_floor64':floor,'T32':t32,'context_floor32':floor32})
        if channel<2:
            weighted=[(x,1/(3*len(xs))) for xs in per_asset for x in xs]
            median,mp=empirical(weighted,.5)
            mad,dp=empirical([(abs(x-median),w) for x,w in weighted],.5)
            R=max(1.4826*mad,1e-3)
            if not math.isfinite(R) or R<=0:raise ValueError('invalid alarm scale')
            alarm.append({'weighted_median64':median,'weighted_MAD64':mad,'R64':R,'median_certificate':mp,'mad_certificate':dp})
    return result,alarm


def map_empty_bins(counts):
    filled=[i for i,n in enumerate(counts) if n]
    if not filled:raise ValueError('no baseline pairs')
    return [min(filled,key=lambda k:(abs(i-k),k)) for i in range(4)]


def baseline_profile(pairs_by_asset):
    if len(pairs_by_asset)!=3 or any(not rows for rows in pairs_by_asset):raise ValueError('baseline asset support')
    pairs=[(power,ys,asset,1/(3*len(rows))) for asset,rows in enumerate(pairs_by_asset) for power,ys in rows]
    cuts=[];cut_proofs=[]
    for p in (.25,.5,.75):
        cut,proof=empirical([(r[0],r[3]) for r in pairs],p);cuts.append(cut);cut_proofs.append(proof)
    bins=[[] for _ in range(4)]
    for row in pairs:bins[bisect_left(cuts,row[0])].append(row)
    counts=[len(rows) for rows in bins];mapping=map_empty_bins(counts);values=[];certs=[]
    for rows in bins:
        estimates=[];proofs=[]
        if rows:
            for target in range(2):
                value,proof=empirical([(r[1][target],r[3]) for r in rows],.5);estimates.append(value);proofs.append(proof)
        values.append(estimates or None);certs.append(proofs)
    return {'load_cuts64':cuts,'cut_certificates':cut_proofs,'pair_counts':counts,
            'per_bin_asset_counts':[[sum(r[2]==a for r in rows) for a in range(3)] for rows in bins],
            'minimum_nonempty_pairs':128,'support_passed':all(n==0 or n>=128 for n in counts),
            'thermal_medians64':values,'median_certificates':certs,'inference_bin_mapping':mapping,
            'weighting':'original pair mass 1/(3*N_asset); restricted-bin CDF renormalized, not re-equalized within bin',
            'equality':'lower bin via bisect_left, duplicate cuts retained'}


def encode_origins(origins):return struct.pack('<'+'I'*len(origins),*origins)


def schedule(train,origins):
    """train is sorted [(asset ID string, anchor event)]; replacement sampling."""
    if len(train)!=3 or train!=sorted(train,key=lambda r:int(r[0])):raise ValueError('train asset ordering')
    rng=random.Random(SAMPLER_SEED);raw=bytearray();counts=[0,0,0]
    for _ in range(UPDATES*BATCH):
        k=rng.randrange(3);asset,event=train[k];n=origins[event][rng.randrange(len(origins[event]))]
        raw+=SCHEDULE_RECORD.pack(int(asset),event,n);counts[k]+=1
    return bytes(raw),counts


def baseline_predict(profile,lagged_power):
    if not math.isfinite(lagged_power):raise ValueError('nonfinite lagged load')
    raw=bisect_left(profile['load_cuts64'],lagged_power)
    return tuple(profile['thermal_medians64'][profile['inference_bin_mapping'][raw]])


class FrozenPreparation:
    """Loads only frozen fold profiles and explicit batch indices; no RNG at use."""
    def __init__(self,prepared,dataset,fold):
        if type(fold) is not int or not 0<=fold<5:raise ValueError('invalid fold')
        root=Path(prepared);verify_closed(root);self.dataset=Path(dataset)
        manifest=json.loads((root/'manifest.json').read_bytes());no_truth(manifest)
        if manifest['contract_sha256']!=CONTRACT_SHA or manifest['recipe_sha256']!=RECIPE_SHA or manifest['input_manifest_sha256']!=INPUT_SHA:
            raise ValueError('preparation contract pin')
        if digest(self.dataset/'root-closed.json')!=DATA_CLOSURE_SHA or manifest['dataset_closure_sha256']!=DATA_CLOSURE_SHA:
            raise ValueError('dataset pin')
        self.profile=json.loads((root/f'fold-{fold}-profile.json').read_bytes());no_truth(self.profile)
        if self.profile['fold']!=fold or not self.profile['baseline']['support_passed']:raise ValueError('fold profile unsupported')
        declared=next(v for v in manifest['folds'] if v['fold']==fold)
        if digest(root/f'fold-{fold}-profile.json')!=declared['profile_sha256'] or digest(root/f'fold-{fold}-schedule.bin')!=declared['schedule_sha256']:
            raise ValueError('fold profile/schedule manifest pin')
        expected=pinned_input()['folds'][fold]
        if self.profile['train_assets']!=expected['train_assets'] or self.profile['train_anchor_events']!=expected['train_anchor_events']:
            raise ValueError('profile train cohort differs')
        self.reader=Consumer(dataset,fold,'fit');self._schedule=(root/f'fold-{fold}-schedule.bin').read_bytes()
        if len(self._schedule)!=UPDATES*BATCH*SCHEDULE_RECORD.size:raise ValueError('schedule length')
        self._allowed={}
        for event in expected['train_anchor_events']:
            index_path=root/f'anchor-{event}-origins.bin'
            declared_index=next(v for v in manifest['origins'] if v['event_id']==event)
            if digest(index_path)!=declared_index['sha256']:raise ValueError('origin population pin')
            raw=index_path.read_bytes()
            if len(raw)%4:raise ValueError('origin index alignment')
            xs=[n[0] for n in struct.iter_unpack('<I',raw)]
            if xs!=sorted(set(xs)) or len(xs)<4096 or len(xs)!=declared_index['count']:raise ValueError('origin population')
            if xs!=self.reader.event(event).origins('fit'):raise ValueError('origin population differs from fixed consumer')
            self._allowed[event]=set(xs)
        event_assets=dict(zip(expected['train_anchor_events'],expected['train_assets'],strict=True))
        for asset,event,n in SCHEDULE_RECORD.iter_unpack(self._schedule):
            if event not in event_assets or str(asset)!=event_assets[event] or n not in self._allowed[event]:raise ValueError('batch index outside fit population')
        self.schedule_sha256=digest(root/f'fold-{fold}-schedule.bin')

    def batch_indices(self,step):
        if type(step) is not int or not 0<=step<UPDATES:raise ValueError('invalid step')
        start=step*BATCH*SCHEDULE_RECORD.size
        return tuple(SCHEDULE_RECORD.iter_unpack(self._schedule[start:start+BATCH*SCHEDULE_RECORD.size]))

    def batch(self,step):
        xs=[];ys=[]
        for asset,event,n in self.batch_indices(step):
            context,target=self.reader.example(event,n);xs.append(context.channels);ys.append(target)
        return tuple(xs),tuple(ys)
