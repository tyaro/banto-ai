"""Real CARE consumer and finite support preflight, with event-truth I/O denied.

No optimizer, learned forecasts, residual thresholds or performance scoring.
"""
from collections import Counter
import base64
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import traceback

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'models/mini-transformer'));sys.path.insert(0,str(ROOT/'tools'))
from care_input import Consumer,EventData,RECORD,NAN32,no_truth,pinned_input,INPUT_SHA,CONTRACT_SHA
from metropt_multiday import Files,digest,verify_closed
from macos_demand_runtime import MacCheckpoint


def artificial():
    count=400;nt=300
    meta={'rows':count,'split_row_counts':{'train':nt,'prediction':count-nt},'anchor':True,'validation_cut_ordinal':210,
          'offline_prefix_status0_bits_base64':base64.b64encode(bytes([255]*37+[15])).decode()}
    raw=b''.join(RECORD.pack(i*600,i,7,0.,float(i),float(i+1)) for i in range(count));d=EventData(raw,meta);n=260
    tests={}
    ctx=d.context(n,n*600);assert ctx.shape==(3,128) and len(ctx.channels[0])==128 and ctx.channels[0]==(0.,)*128
    tests['finite_zero_preserved']=True
    mutated=bytearray(raw);mutated[n*32+16]=0
    for v in range(3):mutated[n*32+20+4*v:n*32+24+4*v]=NAN32
    other=EventData(mutated,meta)
    assert other.context(n,n*600)==ctx and not other.common_ok(n)
    tests['current_missing_changes_later_eligibility_not_issued_context']=True
    future=bytearray(raw)
    for j in range(n,count):future[j*32+20:j*32+32]=struct.pack('<fff',-100.,200.,300.)
    assert EventData(future,meta).context(n,n*600)==ctx
    tests['all_current_future_quantities_do_not_change_past_context']=True
    # Instrument the real boundary: it cannot read any current/future row.
    class PastOnly(list):
        def __getitem__(self,k):
            if not isinstance(k,int) or not 0<=k<n:raise AssertionError('future row access')
            return super().__getitem__(k)
    saved=d._rows;d._rows=PastOnly(saved)
    assert d.context(n,n*600)==ctx;d._rows=saved
    tests['forward_boundary_reads_past_rows_only']=True
    try:d.observation(n,n*600)
    except ValueError:pass
    else:raise AssertionError('early current value accepted')
    assert d.observation(n,(n+1)*600).available_offset_seconds==(n+1)*600
    tests['current_thermal_requires_own_availability']=True
    gapraw=b''.join(RECORD.pack(i*600+(600 if i>=130 else 0),i,7,0.,1.,2.) for i in range(count))
    gap=EventData(gapraw,meta)
    assert not gap.past_ok(257) and gap.past_ok(258) and not gap.common_ok(130)
    tests['gap_requires_128_restored_past_rows']=True
    power=bytearray(raw);power[n*32+16]=3;power[n*32+28:n*32+32]=NAN32
    p=EventData(power,meta);assert p.common_ok(n) and p.native_ok(n) and not p.common_ok(n+1)
    tests['current_power_not_alarm_actual_but_next_context_requires_it']=True
    statusmeta={**meta,'offline_prefix_status0_bits_base64':base64.b64encode(bytes(38)).decode()}
    q=EventData(raw,statusmeta);assert q.common_ok(310) and not q.common_ok(n,True)
    tests['test_ignores_offline_status_but_prefix_filter_applies']=True
    for key in ('event_label','event_start','event_end','event_start_id','event_end_id','label_root'):
        try:no_truth({'nested':[{'key':'ok',key:'injected'}]})
        except ValueError:pass
        else:raise AssertionError('truth injection accepted')
    tests['truth_field_injections_rejected']=True
    corrupt=bytearray(raw);corrupt[16]=0
    try:EventData(corrupt,meta)
    except ValueError:pass
    else:raise AssertionError('mask inconsistency accepted')
    tests['mask_mismatch_rejected']=True
    return tests


def main(dataset,output):
    log=Files(output);status='failed';check=MacCheckpoint(seconds=870);opened=set();denials=[]
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes)):
            path=str(args[0])
            if any(s in path for s in ('care-evaluator-contract-','care-label-metadata-','event-info-','label-manifest.json')):
                denials.append(path);raise PermissionError('evaluator/label I/O forbidden in input consumer')
            if '/care-' in path:opened.add(path)
    sys.addaudithook(audit)
    try:
        log.sources([Path(__file__),ROOT/'models/mini-transformer/care_input.py',ROOT/'models/mini-transformer/metropt_multiday.py',ROOT/'tools/macos_demand_runtime.py'])
        tests=artificial();log.json('artificial-boundaries.json',tests)
        m=pinned_input();file_support=[];anchor_support={};eligibility={};context_hash=hashlib.sha256();examples=[]
        # Each test file is consumed once in its assigned fold, regardless of support.
        for fold in m['folds']:
            test=Consumer(dataset,fold['fold'],'test')
            for event in fold['test_events']:
                d=test.event(event);nt=d.meta['split_row_counts']['train'];end=d.meta['rows'];common=d.origins('test')
                issued=[n for n in range(nt,end) if d.past_ok(n)]
                native=[n for n in range(nt,end) if d.native_ok(n)]
                for n in issued:
                    ctx=test.context(event,n,d._rows[n-1][0]+600)
                    if any(not math.isfinite(x) for row in ctx.channels for x in row):raise ValueError('nonfinite reached input')
                    context_hash.update(struct.pack('<fff',*(row[0] for row in ctx.channels)))
                for n in common:
                    current=d.observation(n,d._rows[n][0]+600)
                    if current.available_offset_seconds<=d._rows[n-1][0]+600:raise ValueError('observation timing')
                fraction=len(common)/(end-nt)
                file_support.append({'event_id':event,'fold':fold['fold'],'asset_id':d.meta['asset_id'],'prediction_rows':end-nt,
                    'past_only_issued_contexts':len(issued),'common_eligible':len(common),'common_fraction':fraction,'floor':.7,'passed':fraction>=.7,
                    'native_baseline_eligible':len(native),'native_minus_common':len(set(native)-set(common)),
                    'excluded_common_reasons':{'past_quality_or_gap':sum(not d.past_ok(n) for n in range(nt,end)),
                    'current_thermal_missing':sum(d._rows[n][2]&3!=3 for n in range(nt,end)),
                    'current_cadence_gap':sum(not d.contiguous(n-1,n+1) for n in range(nt,end))},'exclusion_counts_overlap':True})
                eligibility[str(event)]={'common_ordinals':common,'native_ordinals':native}
                try:test.example(event,common[0] if common else nt)
                except ValueError:pass
                else:raise AssertionError('test consumer released supervised target')
                test._cache.clear();check.check()
            try:test.event(next(e for e in (0,3,13,14,25) if e not in test.allowed))
            except ValueError:pass
            else:raise AssertionError('cross fold event accepted')
            del test
        # Every anchor is a validation anchor once. Check both offline roles + train edge.
        for fold in m['folds']:
            event=fold['validation_anchor_event'];entry={}
            for role,floor in (('selection',256),('calibration',512)):
                reader=Consumer(dataset,fold['fold'],role);d=reader.event(event);origins=d.origins(role)
                entry[role]={'eligible':len(origins),'minimum':floor,'passed':len(origins)>=floor}
                for n in (origins[:1]+origins[-1:]):
                    if role=='selection':
                        ctx,y=reader.example(event,n);examples.append((ctx.channels,y))
                        assert n+32<=d.meta['validation_cut_ordinal']
                    else:
                        ctx=reader.context(event,n,d._rows[n-1][0]+600);d.observation(n,d._rows[n][0]+600)
                del reader
            fitfold=next(f['fold'] for f in m['folds'] if event in f['train_anchor_events'])
            reader=Consumer(dataset,fitfold,'fit');d=reader.event(event);fit=d.origins('fit')
            entry['fit']={'eligible':len(fit),'minimum':4096,'passed':len(fit)>=4096}
            for n in (fit[:1]+fit[-1:]):
                ctx,y=reader.example(event,n);assert n+32<=d.meta['split_row_counts']['train'];examples.append((ctx.channels,y))
            nt=d.meta['split_row_counts']['train']
            try:reader.example(event,nt-31)
            except ValueError:pass
            else:raise AssertionError('training target crosses prefix')
            anchor_support[str(event)]=entry;del reader;check.check()
        # Real batch assembly only: no model import/forward/backward/optimizer.
        import torch
        x=torch.tensor([e[0] for e in examples[:8]],dtype=torch.float32)
        y=torch.tensor([e[1] for e in examples[:8]],dtype=torch.float32)
        assert tuple(x.shape)==(8,3,128) and tuple(y.shape)==(8,3,32) and torch.isfinite(x).all() and torch.isfinite(y).all()
        tests['real_batch_context_and_target_shapes_and_finiteness']=True
        tests['real_cross_role_cross_fold_and_target_prefix_rejections']=True
        # Explicit deny probe, records successful prevention, never reads a label byte.
        try:(ROOT/'artifacts/care-evaluator-contract-20261016/label-manifest.json').read_bytes()
        except PermissionError:tests['label_file_open_denied']=True
        else:raise AssertionError('label boundary not enforced')
        log.json('boundary-checks.json',tests)
        log.json('input-support.json',{'input_manifest_sha256':INPUT_SHA,'contract_sha256':CONTRACT_SHA,'files':file_support,'anchors':anchor_support,
            'consumer_context_digest':context_hash.hexdigest(),'truth_read':False,'dataset_closure_sha256':digest(Path(dataset)/'root-closed.json')})
        log.json('eligibility.json',eligibility)
        log.json('io-audit.json',{'label_bytes_read':0,'denied_probes':denials,'care_paths_opened':sorted(opened),'scope':'input consumer process audit hook; logical role boundary, not hostile-code sandbox'})
        passed=all(f['passed'] for f in file_support) and all(v['passed'] for a in anchor_support.values() for v in a.values())
        log.json('summary.json',{'status':'complete','input_support_passed':passed,'files':22,'boundary_checks':len(tests),'batch_shapes':{'past':[8,3,128],'separate_training_targets':[8,3,32]},'learning':False,'model_forward':False,'performance_scoring':False,'event_support_pending_isolated_evaluator':True,'resources':check.check()})
        status='complete'
    except BaseException:
        log.json('failure.json',{'traceback':traceback.format_exc()},True);raise
    finally:log.close(status)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--dataset',required=True);p.add_argument('--output',required=True);a=p.parse_args();main(a.dataset,a.output)
