"""Independent record-by-record run-length/count/portable-byte verification."""
import base64
from collections import Counter
import ctypes
import json
import math
from pathlib import Path
import struct
import sys
import traceback
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'models/mini-transformer'));sys.path.insert(0,str(ROOT/'tools'))
from metropt_multiday import Files,verify_closed,digest
from care_input import Consumer
from macos_demand_runtime import MacCheckpoint


def main(output):
    log=Files(output);status='failed';check=MacCheckpoint(seconds=870)
    try:
        log.sources([Path(__file__),ROOT/'models/mini-transformer/care_input.py',ROOT/'tools/macos_demand_runtime.py',ROOT/'models/mini-transformer/metropt_multiday.py'])
        data=ROOT/'artifacts/care-numeric-input-20261016';old=ROOT/'artifacts/care-consumer-check-20261016';new=ROOT/'artifacts/care-consumer-check-provenance-20261016'
        prep=ROOT/'artifacts/care-numeric-preparation-20261016';ev=ROOT/'artifacts/care-evaluator-support-20261016'
        for p in (data,old,new,prep,ev):verify_closed(p)
        for name in ('input-support.json','eligibility.json'):
            if (old/name).read_bytes()!=(new/name).read_bytes():raise ValueError('provenance hardening changed frozen support')
        m=json.loads((data/'dataset-manifest.json').read_bytes());support=json.loads((new/'input-support.json').read_bytes())
        eligibility=json.loads((new/'eligibility.json').read_bytes());quality=json.loads((prep/'quality.json').read_bytes())
        if len(list(data.iterdir()))!=24:raise ValueError('dataset file cap/layout')
        counts=[Counter() for _ in range(3)];all_rows=0;comparisons=[]
        for meta in m['files']:
            raw=(data/meta['binary']).read_bytes();nt=meta['split_row_counts']['train'];cut=meta.get('validation_cut_ordinal')
            bits=base64.b64decode(meta.get('offline_prefix_status0_bits_base64',''));goodrun=normalrun=0;prev=None;common=[];native=[];fit=selection=calibration=0
            for i in range(meta['rows']):
                t,ident=struct.unpack_from('<qq',raw,i*32);mask=raw[i*32+16]
                assert raw[i*32+17:i*32+20]==bytes(3) and mask<=7
                xs=struct.unpack_from('<fff',raw,i*32+20)
                for v,x in enumerate(xs):
                    valid=bool(mask&(1<<v));assert valid==math.isfinite(x)
                    if valid:counts[v]['finite_zero' if x==0 else 'finite_nonzero']+=1
                    else:assert raw[i*32+20+4*v:i*32+24+4*v]==bytes.fromhex('0000c07f');counts[v]['invalid']+=1
                contiguous=prev is not None and t-prev[0]==600
                offline=bool(bits and i<nt and bits[i//8]&(1<<(i%8)))
                if i>=nt:
                    if contiguous and goodrun>=128 and mask&3==3:common.append(i)
                    if contiguous and prev[1]&4 and mask&3==3:native.append(i)
                if bits and cut<=i<nt and contiguous and normalrun>=128 and mask&3==3 and offline:calibration+=1
                goodrun=(goodrun+1 if contiguous else 1) if mask==7 else 0
                normalrun=(normalrun+1 if contiguous else 1) if mask==7 and offline else 0
                origin=i-31
                if bits and normalrun>=160 and 128<=origin and i<nt:
                    fit+=1
                    if i<cut and (origin-128)%32==0:selection+=1
                prev=(t,mask);all_rows+=1
            assert common==eligibility[str(meta['event_id'])]['common_ordinals']
            assert native==eligibility[str(meta['event_id'])]['native_ordinals']
            if bits:
                a=support['anchors'][str(meta['event_id'])]
                assert (fit,selection,calibration)==tuple(a[k]['eligible'] for k in ('fit','selection','calibration'))
            comparisons.append({'event_id':meta['event_id'],'all_records_checked':meta['rows'],'common':len(common),'native':len(native),'matches':True})
            check.check()
        # Native C float cast, independently of converter struct.pack path.
        for probe in quality['probes']:
            meta=next(f for f in m['files'] if f['event_id']==probe['event_id']);raw=(data/meta['binary']).read_bytes()
            offset=probe['ordinal']*32+20+4*probe['channel'];token=probe['source_token'].strip()
            if token and math.isfinite(float(token)):
                expected=ctypes.c_float(float(token));encoded=bytes(memoryview(expected))
                assert encoded.hex()==probe['encoded_hex']==raw[offset:offset+4].hex()
        original_read=Path.read_bytes;manifest_path=data/'dataset-manifest.json';rejections=[]
        variations=[('asset',lambda v:v['files'][0].update(asset_id='999')),('row_count',lambda v:v['files'][0].update(rows=1)),
                    ('clock',lambda v:v['files'][0].update(first_timestamp='1970-01-01T00:00:00')),
                    ('path_traversal',lambda v:v['files'][0].update(binary='../outside.bin')),
                    ('duplicate_file',lambda v:v['files'].append(v['files'][0].copy())),
                    ('truth_injection',lambda v:v.update(event_label='anomaly'))]
        for name,mutate in variations:
            altered=json.loads(json.dumps(m));mutate(altered)
            def fake(path):return json.dumps(altered).encode() if path==manifest_path else original_read(path)
            with patch.object(Path,'read_bytes',fake):
                try:Consumer(data,0,'test')
                except ValueError:rejections.append(name)
                else:raise AssertionError('provenance variation accepted: '+name)
        for fold in (-1,5,True):
            try:Consumer(data,fold,'test')
            except ValueError:rejections.append('invalid_fold_'+str(fold))
            else:raise AssertionError('invalid fold accepted')
        truth=json.loads((ev/'summary.json').read_bytes());assert truth['fixed_numeric_window_support_passed']
        phase=ROOT/'artifacts/care-numeric-phase-20261016-evidence';verify_closed(phase)
        assert (phase/'fixed-config-before.json').read_bytes()==(ROOT/'examples/configs/care-a-maintenance-20261016-r1.json').read_bytes()
        log.json('record-verification.json',{'records':all_rows,'cells':all_rows*3,'channels':[dict(c) for c in counts],
            'source_token_float32_probes':len(quality['probes']),'method':'native C float32 bytes + independent sequential run-length support, no prefix-sum reuse','events':comparisons})
        log.json('provenance-rejections.json',{'rejected':rejections,'manifest_mutations_only_in_memory':True,'closed_roots_unchanged':True})
        log.json('support-equivalence.json',{'old_consumer_closure':digest(old/'root-closed.json'),'hardened_consumer_closure':digest(new/'root-closed.json'),
            'input_support_bytes_identical':True,'eligibility_bytes_identical':True,'isolated_evaluator_still_applies_to_same_frozen_bytes':True,'fixed_config_unchanged':True})
        log.json('summary.json',{'status':'complete','all_record_and_support_matches':True,'source_probes':len(quality['probes']),
            'provenance_rejections':len(rejections),'learning':False,'model_forward':False,'performance_scoring':False,'resources':check.check()})
        status='complete'
    except BaseException:
        log.json('failure.json',{'traceback':traceback.format_exc()},True);raise
    finally:log.close(status)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();main(a.output)
