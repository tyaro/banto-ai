"""Independent stdlib readback: source bin probes and train-scale population."""
import csv
from datetime import datetime
import io
import json
import math
from pathlib import Path
import statistics
import struct
import sys
import traceback
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'models/mini-transformer'));sys.path.insert(0,str(ROOT/'tools'))
from metropt_multiday import Files, contract, verify_closed, digest
from macos_demand_runtime import MacCheckpoint


def main(dataset,archive,output):
    files=Files(output);check=MacCheckpoint(seconds=870);status='failed'
    try:
        files.sources([Path(__file__),ROOT/'models/mini-transformer/metropt_multiday.py',ROOT/'tools/macos_demand_runtime.py'])
        c=contract();checks=[]
        roots=[Path(dataset),*(ROOT/'artifacts'/name for name in ('metropt-multiday-prepare-20261016-records','metropt-m0-connect-20261016',
                 'metropt-m0-connect-20261016-records','metropt-m0-guards-20261016','metropt-m0-guards-20261016-records'))]
        pins=[]
        for root in roots:
            closure=verify_closed(root);sizes=[p.stat().st_size for p in root.iterdir()]
            assert len(sizes)<=24 and max(sizes)<=32*1024**2 and sum(sizes)<=768*1024**2
            pins.append({'root':str(root),'closure_sha256':digest(root/'root-closed.json'),'files':len(sizes),'bytes':sum(sizes)})
        checks.append('six data/process/connection/guard roots closed, pinned and within artifact budgets')
        data=Path(dataset);raw=(data/'train.f32').read_bytes()
        floats=struct.unpack('<'+'f'*(len(raw)//4),raw)
        observed=json.loads((data/'scales.json').read_bytes())
        for v in range(3):
            xs=[floats[(day*3+v)*1440+n] for day in range(7) for n in range(1440)]
            sigma=math.sqrt(statistics.pvariance(xs));avg=statistics.fmean(xs)
            assert observed[v]['n']==10080
            assert math.isclose(sigma,observed[v]['sigma64'],rel_tol=1e-12,abs_tol=1e-14)
            assert math.isclose(avg,observed[v]['mean64'],rel_tol=1e-12,abs_tol=1e-14)
        checks.append('all 10080 unique train bins per target match independent population statistics')
        first=c['calendar']['selected_days']['train'][0];minutes={0,127,128,1439}
        probes={n:[[],[],[]] for n in minutes};decoded=0
        with zipfile.ZipFile(archive) as z,z.open('MetroPT3(AirCompressor).csv') as f:
            for i,row in enumerate(csv.DictReader(io.TextIOWrapper(f,encoding='utf-8',newline=''))):
                day=row['timestamp'][:10]
                if day>first:break
                if day==first:
                    t=datetime.fromisoformat(row['timestamp']);n=t.hour*60+t.minute
                    if n in minutes:
                        for v,target in enumerate(c['targets']):probes[n][v].append(float(row[target['raw_column']]));decoded+=1
                if i%10000==0:check.check()
        for n in sorted(minutes):
            for v in range(3):
                expected=struct.unpack('<f',struct.pack('<f',math.fsum(probes[n][v])/len(probes[n][v])))[0]
                assert floats[v*1440+n]==expected
        checks.append('12 source-to-binary probes exact at first/context boundary/last minute')
        connection=json.loads((ROOT/'artifacts/metropt-m0-connect-20261016/summary.json').read_bytes())
        assert connection['model_forward_calls']==2 and connection['optimizer_updates']==0 and connection['performance_scoring_runs']==0
        checks.append('minimal connection uses exactly two untrained forwards and no fitting/scoring')
        files.json('summary.json',{'status':'m0-readback-complete','checks':checks,'pinned_roots':pins,'source_probe_values_decoded':decoded,
                   'real_test_source_probe_values_decoded':0,'model_runs':0,'training_runs':0,'performance_scoring_runs':0,'resources':check.check()})
        status='complete';print(json.dumps({'status':status,'checks':checks}))
    except BaseException:
        files.json('failure.json',{'traceback':traceback.format_exc()},True);raise
    finally:files.close(status)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--dataset',required=True);p.add_argument('--archive',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();main(a.dataset,a.archive,a.output)
