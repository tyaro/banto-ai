"""Strict selected-day/3-target conversion for fixed r2. No model operations."""
from datetime import datetime
import json
import math
from pathlib import Path
import sys
import traceback
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'models/mini-transformer'))
sys.path.insert(0,str(ROOT/'tools'))
from metropt_multiday import CONFIG, CONFIG_SHA, Files, contract, digest, encode_f32, f32, common_origins, scales
from macos_demand_runtime import MacCheckpoint


def convert(archive, output):
    files=Files(output); check=MacCheckpoint(seconds=870); status='failed'
    try:
        c=contract()
        files.json('phase.json',{'plan_id':c['plan_id'],'phase':'M0 strict quantity preparation','training':False,'scoring':False,
                               'days_fixed':True,'replacement_allowed':False})
        files.write('config.json',CONFIG.read_bytes())
        files.sources([Path(__file__),ROOT/'models/mini-transformer/metropt_multiday.py',ROOT/'tools/macos_demand_runtime.py'])
        if digest(archive)!=c['source']['archive_sha256']: raise ValueError('raw archive digest')
        dates={day for days in c['calendar']['selected_days'].values() for day in days}
        values={day:[[None]*1440 for _ in range(3)] for day in dates}
        counts={day:[0]*1440 for day in dates}; gaps={day:0 for day in dates}
        key=None; buckets=[[],[],[]]; previous=None; source_rows=selected_rows=0
        def flush():
            if key is not None:
                day,n=key
                for v in range(3): values[day][v][n]=f32(math.fsum(buckets[v])/len(buckets[v]))
        with zipfile.ZipFile(archive) as z,z.open('MetroPT3(AirCompressor).csv') as source:
            header=source.readline().rstrip(b'\r\n').split(b',')
            if header[1]!=b'timestamp': raise ValueError('timestamp header')
            indices=[header.index(t['raw_column'].encode()) for t in c['targets']]
            for line in source:
                _,sep,rest=line.partition(b',');raw,sep2,_=rest.partition(b',')
                if not sep or not sep2: raise ValueError('raw timestamp delimiters')
                t=datetime.fromisoformat(raw.decode('ascii'));day=t.date().isoformat();source_rows+=1
                if t.tzinfo is not None: raise ValueError('timezone changed')
                if previous is not None:
                    delta=(t-previous).total_seconds()
                    if delta<=0: raise ValueError('duplicate/reversed source timestamp')
                    if day in dates and previous.date()==t.date():
                        gaps[day]=max(gaps[day],delta)
                        if delta>60: raise ValueError('selected within-day gap')
                previous=t
                if day in dates:
                    parts=line.rstrip(b'\r\n').split(b',')
                    if len(parts)!=len(header): raise ValueError('selected raw column count')
                    xs=[float(parts[i]) for i in indices]
                    if not all(math.isfinite(x) for x in xs): raise ValueError('selected raw quantity nonfinite')
                    next_key=(day,t.hour*60+t.minute)
                    if next_key!=key:
                        flush();key=next_key;buckets=[[],[],[]]
                    for v,x in enumerate(xs): buckets[v].append(x)
                    counts[day][next_key[1]]+=1;selected_rows+=1
                if source_rows%10000==0:check.check()
        flush()
        support={}
        for split,days in c['calendar']['selected_days'].items():
            support[split]={}
            for day in days:
                if any(n==0 for n in counts[day]): raise ValueError('selected empty bin')
                keep,excluded=common_origins(values[day],[[True]*1440 for _ in range(3)],split)
                support[split][day]={'candidates':len(keep)+len(excluded),'kept':keep,'excluded':excluded,
                                     'minimum':c['calendar']['minimum_common_support_per_day'][split]}
            flat=[x for day in days for row in values[day] for x in row]
            files.write(split+'.f32',encode_f32(flat))
        stats=scales([values[d] for d in c['calendar']['selected_days']['train']])
        files.json('scales.json',stats);files.json('support.json',support)
        files.write('calendar-windows.jsonl',(ROOT/c['source']['calendar_manifest']).read_bytes())
        files.json('dataset.json',{'plan_id':c['plan_id'],'config_sha256':CONFIG_SHA,'archive_sha256':c['source']['archive_sha256'],
                   'days':c['calendar']['selected_days'],'target_order':c['targets'],'dtype':'little-endian float32',
                   'layout':'[day,target,minute], contiguous C order, 1440 bins/day','bin':'[start,start+60s), bin-end availability',
                   'physical_closure_truth':False,'normal_operation_certified':False})
        files.json('summary.json',{'status':'quantity-preparation-complete','source_rows':source_rows,'selected_raw_rows':selected_rows,
                   'quantity_values_decoded':3*selected_rows,'stored_bins_per_target':13*1440,'raw_missing_nonfinite':0,
                   'interpolated_bins':0,'replacement_days':0,'selected_day_max_raw_gap_seconds':gaps,
                   'common_windows':{s:sum(len(x['kept']) for x in days.values()) for s,days in support.items()},
                   'training_runs':0,'model_runs':0,'scoring_runs':0,'can_launch_learning':False,'resources':check.check()})
        status='complete'
        print(json.dumps({'status':status,'source_rows':source_rows,'selected_raw_rows':selected_rows,'output':str(output)}))
    except BaseException:
        failure={'traceback':traceback.format_exc()}
        try:failure['resources']=check.check()
        except BaseException as e:failure['resource_observation_failure']=repr(e)
        files.json('failure.json',failure,True)
        raise
    finally:files.close(status)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--archive',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();convert(Path(a.archive),Path(a.output))
