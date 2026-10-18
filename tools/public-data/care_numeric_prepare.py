"""One bounded fixed A22 conversion; only selected three sensor fields decoded."""
import base64
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import struct
import sys
import traceback
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'models/mini-transformer'));sys.path.insert(0,str(ROOT/'tools'))
from metropt_multiday import Files,digest
from care_input import pinned_input,CONTRACT_SHA,INPUT_SHA,RECORD,NAN32
from macos_demand_runtime import MacCheckpoint
import math


def cell(token):
    token=token.strip()
    if not token:return NAN32,'empty'
    try:x=float(token)
    except ValueError:raise ValueError('unrecognized numeric token; no automatic repair') from None
    if not math.isfinite(x):return NAN32,'nan' if math.isnan(x) else 'infinity'
    try:raw=struct.pack('<f',x)
    except (OverflowError,struct.error):return NAN32,'float32_overflow'
    y=struct.unpack('<f',raw)[0]
    if not math.isfinite(y):return NAN32,'float32_overflow'
    return raw,'finite_zero' if x==0 else ('finite_underflow_to_zero' if y==0 else 'finite_nonzero')


def convert(z,item,order,check,probes):
    """Decode only the ordered Avg fields of one fixed member into 32-byte records."""
    h=hashlib.sha256();out=bytearray();counts=[Counter() for _ in range(3)];first=None;last=None;last_id=None
    nt=item['split_row_counts']['train'];bits=bytearray((nt+7)//8) if item['anchor'] else None
    with z.open(item['member']) as f:
        header=f.readline();h.update(header);cols=header.decode('utf-8-sig').rstrip('\r\n').split(';')
        if cols[:5]!=['time_stamp','asset_id','id','train_test','status_type_id']:raise ValueError('structural schema')
        positions=[cols.index(v) for v in order]
        for n,line in enumerate(f):
            h.update(line);p=line.rstrip(b'\r\n').split(b';')
            if len(p)!=len(cols):raise ValueError('column count')
            t=datetime.fromisoformat(p[0].decode());ident=int(p[2]);split=p[3]
            if n==0:first=t
            offset=int((t-first).total_seconds())
            if t.microsecond or (last is not None and (t<=last or ident<=last_id)):raise ValueError('invalid clock/id')
            if p[1].decode()!=item['asset_id'] or split!=(b'train' if n<nt else b'prediction'):raise ValueError('asset/split mismatch')
            # Only status0 in anchor train prefix is retained; test status discarded.
            if bits is not None and n<nt and p[4]==b'0':bits[n//8]|=1<<(n%8)
            values=[];mask=0
            for v,col in enumerate(positions):
                raw,reason=cell(p[col]);values.append(raw);counts[v][reason]+=1
                if reason.startswith('finite'):mask|=1<<v
                if (n in (0,nt-1,nt,item['rows']-1) or counts[v][reason]==1) and len(probes)<300:
                    probes.append({'event_id':item['event_id'],'ordinal':n,'channel':v,'source_token':p[col].decode(),'encoded_hex':raw.hex(),'reason':reason})
            out+=struct.pack('<qqB3x',offset,ident,mask)+b''.join(values)
            last,last_id=t,ident
            if n%8192==0:check.check()
    if n+1!=item['rows'] or h.hexdigest()!=item['member_sha256']:raise ValueError('source member pin/count')
    return out,first,bits,counts,n


def main(output,records):
    log=Files(records);data=None;check=MacCheckpoint(seconds=870);state='failed'
    try:
        log.sources([Path(__file__),ROOT/'models/mini-transformer/care_input.py',ROOT/'models/mini-transformer/metropt_multiday.py',ROOT/'tools/macos_demand_runtime.py'])
        m=pinned_input();log.json('phase.json',{'numeric_preparation_only':True,'learning':False,'predictions':False,'truth_access':False,'input_pin':INPUT_SHA})
        if digest(m['source_archive'])!=m['source_sha256']:raise ValueError('archive SHA mismatch')
        check.check();data=Files(output);metadata=[];quality=[];probes=[]
        with zipfile.ZipFile(m['source_archive']) as z:
            for item in m['files']:
                out,first,bits,counts,n=convert(z,item,m['model_feature_order'],check,probes)
                name=f"event-{item['event_id']}.bin";data.write(name,out)
                meta={**item,'binary':name,'binary_sha256':digest(data.root/name),'first_timestamp':first.isoformat(),'record_bytes':32}
                if bits is not None:meta['offline_prefix_status0_bits_base64']=base64.b64encode(bits).decode()
                metadata.append(meta);quality.append({'event_id':item['event_id'],'rows':n+1,'channels':[dict(c) for c in counts]})
                print(json.dumps({'event':item['event_id'],'rows':n+1}),flush=True)
        data.json('dataset-manifest.json',{'schema':'banto.care-numeric-input.v1','contract_id':m['contract_id'],'contract_sha256':CONTRACT_SHA,'input_manifest_sha256':INPUT_SHA,'source_sha256':m['source_sha256'],'source_doi':m['source_doi'],'license_id':m['license_id'],'attribution':'CARE to Compare authors; https://doi.org/10.5281/zenodo.15846963','license_url':'https://creativecommons.org/licenses/by-sa/4.0/','changes':'Farm A fixed three Avg fields converted to float32 + finite mask and file-local offsets; no imputation or numerical unit conversion.','model_feature_order':m['model_feature_order'],'status_bitset':'LSB first, anchor train-prefix status0 only, offline annotation not model input; prediction status discarded','layout':'<qqB3xfff, 32 bytes, canonical missing f32 bits0x7fc00000','files':metadata})
        data.close('complete');data=None
        log.json('quality.json',{'files':quality,'probes':probes,'zeros_are_observed_values':True,'truth_access':False,'all22_retained':True})
        log.json('summary.json',{'status':'complete','files':len(metadata),'rows':sum(x['rows'] for x in metadata),'cells':3*sum(x['rows'] for x in metadata),'resources':check.check(),'learning':False,'predictions':False})
        state='complete'
    except BaseException:
        log.json('failure.json',{'traceback':traceback.format_exc()},True);raise
    finally:
        if data is not None:data.close('failed')
        log.close(state)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--records',required=True);a=p.parse_args();main(a.output,a.records)
