"""CARE r1 portable input and role-aware consumer; no model, optimizer or truth reads.

Time is file-local. PastContext is the sole forward boundary. Current thermal
observations and training targets have separate methods and availability checks.
The prefix status bitset is offline selection metadata, never an input channel.
"""
import base64
from dataclasses import dataclass
import json
import math
from pathlib import Path
import struct
from metropt_multiday import ROOT, digest, verify_closed

CONTRACT_SHA='f199f0f4932a9f419d9aa2a9ee7432793a607ffc2acc654d14467f1727a40cf1'
INPUT_SHA='5cddf48d2399695c49dde59a2370f10351b816f5217d363477a0eb361b31aac8'
RECIPE_SHA='b238248f4b5055311f562bb099f26c446448d2c1e4b113fd453fd86825f566f3'
RECORD=struct.Struct('<qqB3xfff')
NAN32=bytes.fromhex('0000c07f')
FORBIDDEN={'event_label','event_start','event_end','event_start_id','event_end_id','description','truth_rows','label_root'}


def no_truth(value):
    if isinstance(value,dict):
        if FORBIDDEN & value.keys():raise ValueError('truth field in input boundary')
        for v in value.values():no_truth(v)
    elif isinstance(value,list):
        for v in value:no_truth(v)


def pinned_input():
    c=ROOT/'examples/configs/care-a-maintenance-20261016-r1.json'
    base=ROOT/'artifacts/care-input-contract-20261016'
    if digest(c)!=CONTRACT_SHA or digest(base/'input-manifest.json')!=INPUT_SHA or digest(base/'learning.json')!=RECIPE_SHA:
        raise ValueError('fixed CARE contract changed')
    verify_closed(base)
    manifest=json.loads((base/'input-manifest.json').read_bytes())
    # Signal prose is provenance; it is removed from the machine consumer view.
    machine={k:v for k,v in manifest.items() if k!='signal_metadata'}
    no_truth(machine)
    return manifest


@dataclass(frozen=True)
class PastContext:
    channels:tuple
    issue_offset_seconds:int
    last_source_row_id:int
    shape:tuple=(3,128)


@dataclass(frozen=True)
class ThermalObservation:
    values:tuple
    available_offset_seconds:int


class EventData:
    def __init__(self, raw, meta):
        if len(raw)!=meta['rows']*32:raise ValueError('record count mismatch')
        self.meta=meta
        self._rows=list(RECORD.iter_unpack(raw))
        self._normal=base64.b64decode(meta.get('offline_prefix_status0_bits_base64',''),validate=True)
        nt=meta['split_row_counts']['train']
        if meta['anchor'] and len(self._normal)!=(nt+7)//8:raise ValueError('offline status bitset length')
        if not meta['anchor'] and self._normal:raise ValueError('unexpected status on nonanchor')
        if self._normal and nt%8 and self._normal[-1]>>(nt%8):raise ValueError('nonzero tail status bits')
        self._bad3=[0];self._bad_normal=[0];self._gap=[0]
        last_t=last_id=None
        for i,(t,ident,mask,*xs) in enumerate(self._rows):
            if mask&~7 or raw[i*32+17:i*32+20]!=b'\0\0\0':raise ValueError('mask/padding')
            if i==0 and t!=0:raise ValueError('file origin')
            if i and (t<=last_t or ident<=last_id):raise ValueError('time/id reversal')
            for v,x in enumerate(xs):
                bits=raw[i*32+20+4*v:i*32+24+4*v]
                if bool(mask&(1<<v))!=math.isfinite(x):raise ValueError('mask/finite mismatch')
                if not mask&(1<<v) and bits!=NAN32:raise ValueError('noncanonical missing')
            normal=bool(self._normal[i//8]&(1<<(i%8))) if self._normal and i<nt else False
            self._bad3.append(self._bad3[-1]+(mask!=7))
            self._bad_normal.append(self._bad_normal[-1]+(not normal))
            self._gap.append(self._gap[-1]+bool(i and t-last_t!=600))
            last_t,last_id=t,ident

    def contiguous(self,left,right):
        return 0<=left<right<=len(self._rows) and self._gap[right]==self._gap[left+1]

    def complete(self,left,right,normal=False):
        return (self.contiguous(left,right) and self._bad3[right]==self._bad3[left]
                and (not normal or self._bad_normal[right]==self._bad_normal[left]))

    def past_ok(self,n,normal=False):return self.complete(n-128,n,normal)

    def common_ok(self,n,normal=False):
        return (self.past_ok(n,normal) and n<len(self._rows) and self.contiguous(n-128,n+1)
                and self._rows[n][2]&3==3 and (not normal or self._bad_normal[n+1]==self._bad_normal[n]))

    def native_ok(self,n):
        return (0<n<len(self._rows) and self.contiguous(n-1,n+1)
                and bool(self._rows[n-1][2]&4) and self._rows[n][2]&3==3)

    def region(self,kind):
        nt=self.meta['split_row_counts']['train'];cut=self.meta.get('validation_cut_ordinal')
        if kind=='test':return nt,len(self._rows),1,1,False
        if not self.meta['anchor']:raise ValueError('offline role requires anchor')
        if kind=='fit':return 128,nt,32,1,True
        if kind=='selection':return 128,cut,32,32,True
        if kind=='calibration':return cut,nt,1,1,True
        raise ValueError('unknown role')

    def origins(self,kind):
        start,end,horizon,stride,normal=self.region(kind)
        return [n for n in range(max(128,start),end-horizon+1,stride)
                if (self.complete(n-128,n+32,True) if horizon==32 else self.common_ok(n,normal))]

    def context(self,n,asof,normal=False):
        if not self.past_ok(n,normal):raise ValueError('unavailable past context')
        # No access to row n, even its mask/status/time. This boundary is past-only.
        last=self._rows[n-1]
        if asof!=last[0]+600:raise ValueError('issue must equal last-past availability')
        channels=tuple(tuple(self._rows[j][3+v] for j in range(n-128,n)) for v in range(3))
        return PastContext(channels,asof,last[1])

    def observation(self,n,asof):
        row=self._rows[n]
        if asof<row[0]+600:raise ValueError('current thermal not yet available')
        if row[2]&3!=3:raise ValueError('current thermal missing')
        return ThermalObservation(tuple(row[3:5]),row[0]+600)


class Consumer:
    """A fold/role boundary with no evaluator-root argument or truth import."""
    def __init__(self,directory,fold,role):
        source=pinned_input();root=Path(directory);verify_closed(root)
        m=json.loads((root/'dataset-manifest.json').read_bytes());no_truth(m)
        if m['input_manifest_sha256']!=INPUT_SHA or m['contract_sha256']!=CONTRACT_SHA:raise ValueError('data contract pin')
        if m['model_feature_order']!=source['model_feature_order']:raise ValueError('feature order')
        if type(fold) is not int or not 0<=fold<5:raise ValueError('invalid fold')
        expected={f['event_id']:f for f in source['files']}
        if len(m['files'])!=22:raise ValueError('fixed file count changed')
        for f in m['files']:
            if f['event_id'] not in expected:raise ValueError('unregistered file')
            original=expected[f['event_id']]
            if any(f.get(k)!=v for k,v in original.items()):raise ValueError('source metadata differs from fixed manifest')
            if f['binary']!=f"event-{f['event_id']}.bin" or f['record_bytes']!=32:raise ValueError('unsafe binary layout/path')
            if f['first_timestamp']!=original['split_transitions'][0]['timestamp']:raise ValueError('file-local clock origin differs')
            if f['binary_sha256']!=digest(root/f['binary']):raise ValueError('binary manifest pin')
        self.root=root;self.manifest=m;self.fold=source['folds'][fold];self.role=role
        if role=='fit':self.allowed=set(self.fold['train_anchor_events'])
        elif role in ('selection','calibration'):self.allowed={self.fold['validation_anchor_event']}
        elif role=='test':self.allowed=set(self.fold['test_events'])
        else:raise ValueError('unknown consumer role')
        if {f['event_id'] for f in m['files']}!={f['event_id'] for f in source['files']}:raise ValueError('cohort changed')
        self._cache={}

    def event(self,event):
        if event not in self.allowed:raise ValueError('cross-fold/role event')
        if event not in self._cache:
            meta=next(f for f in self.manifest['files'] if f['event_id']==event)
            self._cache[event]=EventData((self.root/meta['binary']).read_bytes(),meta)
        return self._cache[event]

    def context(self,event,n,asof):
        d=self.event(event);start,end,_,stride,normal=d.region(self.role)
        if not max(128,start)<=n<end:raise ValueError('origin outside role')
        if self.role=='selection' and (n-128)%stride:raise ValueError('selection stride')
        return d.context(n,asof,normal)

    def example(self,event,n):
        if self.role not in ('fit','selection'):raise ValueError('targets unavailable in this role')
        d=self.event(event);start,end,_,stride,_=d.region(self.role)
        if not max(128,start)<=n<=end-32 or (n-max(128,start))%stride or not d.complete(n-128,n+32,True):
            raise ValueError('invalid supervised window')
        return self.context(event,n,d._rows[n-1][0]+600),tuple(tuple(d._rows[j][3+v] for j in range(n,n+32)) for v in range(3))
