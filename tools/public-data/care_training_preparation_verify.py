"""Independent arithmetic, full schedule replay and real frozen-consumer check.

Integer binary-rational cumulative masses reproduce float64 fsum rounding
without calling the preparation empirical() implementation. Population variance
uses within/between-asset decomposition. No learned model or event truth.
"""
from collections import Counter
import base64
import ctypes
from itertools import groupby
import json
import math
from pathlib import Path
import random
import statistics
import struct
import sys
import traceback
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'models/mini-transformer'));sys.path.insert(0,str(ROOT/'tools'))
from metropt_multiday import Files,digest,verify_closed
from care_input import Consumer,pinned_input
from care_training_preparation import FrozenPreparation,baseline_profile,baseline_predict,normal_rows
from macos_demand_runtime import MacCheckpoint


class ReferenceCDF:
    def __init__(self,arrays,weights):
        ratios=[w.as_integer_ratio() for w in weights];denom=max(d for n,d in ratios)
        unit=[n*(denom//d) for n,d in ratios];rows=sorted((x,a) for a,xs in enumerate(arrays) for x in xs)
        self.values=[];self.cumulative=[];total=0
        for value,group in groupby(rows,key=lambda t:t[0]):
            counts=Counter(r[1] for r in group)
            # float(int/int) rounds one equal-value fsum; subsequent mass sum exact in integer units.
            rounded=sum(unit[a]*n for a,n in counts.items())/denom
            n,d=rounded.as_integer_ratio();total+=n*(denom//d)
            self.values.append(value);self.cumulative.append(total)
        self.denom=denom;self.total64=total/denom
    def quantile(self,p):
        for x,cumulative in zip(self.values,self.cumulative,strict=True):
            if (cumulative/self.denom)/self.total64>=p:return x
        raise AssertionError('invalid reference CDF')


def below(n,rng):
    k=n.bit_length();x=rng.getrandbits(k)
    while x>=n:x=rng.getrandbits(k)
    return x


def main(prepared,dataset,output):
    out=Files(output);check=MacCheckpoint(seconds=870);status='failed';opened=set()
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes)):
            path=str(args[0])
            if any(s in path for s in ('care-evaluator-contract-','care-label-metadata-','event-info-','label-manifest.json')):
                raise PermissionError('truth forbidden in independent profile verification')
            if '/care-' in path:opened.add(path)
    sys.addaudithook(audit)
    try:
        out.sources([Path(__file__),ROOT/'models/mini-transformer/care_training_preparation.py',ROOT/'models/mini-transformer/care_input.py',ROOT/'models/mini-transformer/metropt_multiday.py',ROOT/'tools/macos_demand_runtime.py'])
        root=Path(prepared);verify_closed(root);m=pinned_input();population={};pair={};indices={};prefix_tests=[]
        for event in sorted({e for f in m['folds'] for e in f['train_anchor_events']}):
            f=next(f['fold'] for f in m['folds'] if event in f['train_anchor_events']);reader=Consumer(dataset,f,'fit');d=reader.event(event)
            nt=d.meta['split_row_counts']['train'];all_rows=d._rows
            # Tripwire: population selector must not read prediction quantities.
            class PrefixOnly(list):
                def __getitem__(self,k):
                    if not isinstance(k,int) or not 0<=k<nt:raise AssertionError('outside train prefix')
                    return super().__getitem__(k)
            d._rows=PrefixOnly(all_rows);selected=normal_rows(d);d._rows=all_rows
            independent=[i for i in range(nt) if all_rows[i][2]==7 and (d._normal[i//8]>>(i%8))&1]
            assert selected==independent
            population[event]=[all_rows[i][3:6] for i in independent];indices[event]=d.origins('fit')
            pair[event]=[(all_rows[n-1][5],all_rows[n][3:5]) for n in indices[event]]
            saved=[x[0] for x in struct.iter_unpack('<I',(root/f'anchor-{event}-origins.bin').read_bytes())]
            assert saved==indices[event]
            assert all(n>=128 and n+32<=nt for n in saved)
            prefix_tests.append({'event_id':event,'scale_population':len(selected),'fit_origins':len(saved),'outside_prefix_access':0})
            del d,reader;check.check()
        diagnostics=[];quantile_checks=0;max_mean_error=max_var_error=0.;batch_checks=[]
        for fold in m['folds']:
            k=fold['fold'];es=fold['train_anchor_events'];profile=json.loads((root/f'fold-{k}-profile.json').read_bytes())
            for v in range(3):
                arrays=[[row[v] for row in population[e]] for e in es]
                means=[statistics.mean(xs) for xs in arrays];mean=statistics.mean(means)
                variance=statistics.mean([statistics.pvariance(xs)+(mu-mean)**2 for xs,mu in zip(arrays,means,strict=True)])
                saved=profile['normalization'][v]
                max_mean_error=max(max_mean_error,abs(mean-saved['mean64']));max_var_error=max(max_var_error,abs(variance-saved['variance64']))
                assert math.isclose(mean,saved['mean64'],rel_tol=1e-12,abs_tol=1e-12)
                assert math.isclose(variance,saved['variance64'],rel_tol=1e-12,abs_tol=1e-12)
                assert math.isclose(max(math.sqrt(variance),1e-5),saved['T64'],rel_tol=1e-12)
                assert ctypes.c_float(saved['T64']).value==saved['T32'] and ctypes.c_float(saved['context_floor64']).value==saved['context_floor32']
                if v<2:
                    weights=[1/(3*len(xs)) for xs in arrays];median=ReferenceCDF(arrays,weights).quantile(.5)
                    deviations=[[abs(x-median) for x in xs] for xs in arrays];mad=ReferenceCDF(deviations,weights).quantile(.5)
                    a=profile['alarm_scales'][v];assert median==a['weighted_median64'] and mad==a['weighted_MAD64'] and max(1.4826*mad,1e-3)==a['R64'];quantile_checks+=2
            baseline=profile['baseline'];powers=[[p for p,y in pair[e]] for e in es];weights=[1/(3*len(xs)) for xs in powers]
            ref=ReferenceCDF(powers,weights);cuts=[ref.quantile(p) for p in (.25,.5,.75)];assert cuts==baseline['load_cuts64'];quantile_checks+=3
            bins=[[] for _ in range(4)]
            for a,e in enumerate(es):
                for load,ys in pair[e]:
                    bin_id=sum(load>cut for cut in cuts);bins[bin_id].append((a,ys))
            counts=[len(xs) for xs in bins];assert counts==baseline['pair_counts'] and all(n==0 or n>=128 for n in counts)
            for b,rows in enumerate(bins):
                if not rows:continue
                for v in range(2):
                    arrays=[[ys[v] for a,ys in rows if a==asset] for asset in range(3)]
                    assert ReferenceCDF(arrays,weights).quantile(.5)==baseline['thermal_medians64'][b][v];quantile_checks+=1
            rng=random.Random(20262016);expected=bytearray();draws=[0,0,0]
            for _ in range(4096*8):
                slot=below(3,rng);event=es[slot];n=indices[event][below(len(indices[event]),rng)]
                expected+=struct.pack('<III',int(fold['train_assets'][slot]),event,n);draws[slot]+=1
            assert bytes(expected)==(root/f'fold-{k}-schedule.bin').read_bytes() and draws==profile['schedule']['draw_counts_by_train_asset']
            frozen=FrozenPreparation(root,dataset,k);batch_raw=bytearray()
            for step in (0,4095):
                xs,ys=frozen.batch(step);assert len(xs)==len(ys)==8
                for x,y in zip(xs,ys,strict=True):
                    assert len(x)==3 and all(len(v)==128 for v in x) and len(y)==3 and all(len(v)==32 for v in y)
                    for ch in (*x,*y):
                        assert all(math.isfinite(value) for value in ch);batch_raw+=struct.pack('<'+'f'*len(ch),*ch)
            for bad_step in (-1,4096,True):
                try:frozen.batch_indices(bad_step)
                except ValueError:pass
                else:raise AssertionError('invalid schedule step accepted')
            out.write(f'fold-{k}-batch-reference.bin',batch_raw)
            batch_checks.append({'fold':k,'steps':[0,4095],'layout':'per step per example: x3x128 then y3x32 float32-le','bytes':len(batch_raw),'shape_context':[8,3,128],'shape_targets':[8,3,32]})
            diagnostics.append({'fold':k,'normalization_and_MAD_reference_match':True,'baseline_bins_and_medians_match':True,'pair_counts':counts,'schedule_32768_records_byte_equal':True,'draw_counts':draws})
            del frozen;check.check()
        # Distinguish fixed original asset masses from wrongly equalizing assets within each bin.
        toy=baseline_profile([[(0.,(0.,0.))]+[(1.,(0.,0.))]*99,[(0.,(10.,10.))]*49+[(1.,(10.,10.))]*51,[(0.,(20.,20.))]])
        assert toy['thermal_medians64'][0]==[20.,20.] and baseline_predict(toy,0.)==(20.,20.)
        # Its support is intentionally inadequate; it must not silently become a runnable profile.
        assert not toy['support_passed']
        out.json('independent-checks.json',{'folds':diagnostics,'prefix_tripwires':prefix_tests,'quantile_values_checked':quantile_checks,'max_mean64_absolute_error':max_mean_error,'max_variance64_absolute_error':max_var_error,
            'restricted_bin_preserves_original_pair_masses':True,'small_toy_support_failure_retained':True,'batch_checks':batch_checks,
            'cdf_reference':'exact binary-rational integer masses; round equal-value masses and cumulative mass to float64 independently, no preparation empirical call',
            'schedule_reference':'getrandbits + rejection sampling; no preparation schedule helper or randrange calls'})
        out.json('summary.json',{'status':'complete','profile_and_schedule_verified':True,'folds':5,'all_schedule_records_verified':163840,'real_batches_verified':10,'label_bytes_read':0,'care_paths_opened':sorted(opened),
            'model_training':False,'model_forward':False,'threshold_calibration':False,'performance_scoring':False,'resources':check.check()})
        status='complete'
    except BaseException:
        out.json('failure.json',{'traceback':traceback.format_exc()},True);raise
    finally:out.close(status)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--prepared',required=True);p.add_argument('--dataset',required=True);p.add_argument('--output',required=True);a=p.parse_args();main(a.prepared,a.dataset,a.output)
