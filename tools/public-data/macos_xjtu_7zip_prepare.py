"""Official 7-Zip fallback for multivolume RAR; raw waveforms stay in cache."""
from collections import defaultdict
import csv
import io
import json
import math
from pathlib import Path
import re
import resource
import subprocess
import sys
import traceback
from macos_industrial_fetch import write,close,digest,ROOT
from macos_demand_runtime import MacCheckpoint


def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--raw',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    raw,out=Path(a.raw),Path(a.output);out.mkdir(parents=True,exist_ok=False)
    tool=raw/'7zip-tool/7zz';archive=raw/'xjtu-multivolume-view/XJTU-SY_Bearing_Datasets.part01.rar'
    check=MacCheckpoint(seconds=870);status='failed';proc=None;operations=[]
    try:
        testroot=ROOT/'artifacts/macos-industrial-xjtu-7zip-test-20261016-records'
        if json.loads((testroot/'exit.json').read_text())['returncode']!=0:raise ValueError('whole RAR CRC test not successful')
        if json.loads((testroot/'root-closed.json').read_text())['status']!='complete':raise ValueError('whole RAR CRC record incomplete')
        test_text=(testroot/'stdout.txt').read_text()
        tail_warning='There are data after the end of archive' in test_text
        cmd=[str(tool),'l','-slt','-ba','-bd','-bsp0',str(archive)]
        with (out/'archive-listing.txt').open('xb') as stdout,(out/'listing-stderr.txt').open('xb') as stderr:
            proc=subprocess.Popen(cmd,stdout=stdout,stderr=stderr)
            import time
            while proc.poll() is None:
                check.check()
                if (out/'archive-listing.txt').stat().st_size>16*1024**2:raise ValueError('listing size limit')
                time.sleep(.2)
            rc=proc.wait()
        operations.append({'command':cmd,'returncode':rc,'stdout':'archive-listing.txt','stderr':'listing-stderr.txt'})
        if rc:raise RuntimeError('7zz listing failed')
        inventory=[];counts=defaultdict(list);selected=[];pilot={'Bearing1_1','Bearing2_1','Bearing3_1'}
        for block in (out/'archive-listing.txt').read_text().split('\n\n'):
            fields=dict(line.split(' = ',1) for line in block.splitlines() if ' = ' in line)
            if 'Path' not in fields:continue
            if 'Type' in fields and 'Physical Size' in fields:continue
            name=fields['Path'].replace('\\','/')
            if name.startswith('/') or '..' in Path(name).parts:raise ValueError('unsafe archive member')
            inventory.append(fields)
            match=re.search(r'(Bearing([123])_([1-5]))/(\d+)\.csv$',name,re.I)
            if match:
                bearing,condition,ordinal,index=match.groups();index=int(index);counts[bearing].append(index)
                if bearing in pilot:selected.append((name,bearing,index))
        expected={f'Bearing{c}_{b}' for c in range(1,4) for b in range(1,6)}
        if set(counts)!=expected:raise ValueError('not all 15 bearings found')
        for b,ids in counts.items():
            if sorted(ids)!=list(range(1,len(ids)+1)):raise ValueError('missing/duplicate waveform index')
        if len({i['Path'] for i in inventory})!=len(inventory):raise ValueError('duplicate path')
        with (out/'pilot-members.txt').open('x') as f:
            for name,_,_ in selected:f.write(name+'\n')
        cmd=[str(tool),'x','-so','-bd','-bsp0','-mmt=1','-scsUTF-8','-spd',str(archive),'@'+str(out/'pilot-members.txt')]
        features=defaultdict(list);axes=[[],[]];member_index=-1;header=None
        def flush():
            if member_index<0:return
            if any(len(v)!=32768 for v in axes):raise ValueError('pilot waveform sample count')
            name,bearing,index=selected[member_index];values=[]
            for v in axes:
                mean=math.fsum(v)/len(v)
                values.extend([mean,math.sqrt(math.fsum(x*x for x in v)/len(v)),
                               math.sqrt(math.fsum((x-mean)**2 for x in v)/len(v)),max(v)-min(v)])
            features[bearing].append({'sample_index':index,'feature_values':values})
        with (out/'stream-stderr.txt').open('xb') as stderr:
            proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=stderr)
            for row in csv.reader(io.TextIOWrapper(proc.stdout,encoding='utf-8-sig',newline='')):
                if not row:continue
                if len(row)==2 and 'horizontal' in row[0].lower() and 'vertical' in row[1].lower():
                    flush();member_index+=1;check.check();axes=[[],[]];header=row
                    if member_index>=len(selected):raise ValueError('unexpected extra waveform')
                    continue
                if header is None or len(row)!=2:raise ValueError('unexpected waveform header/row')
                x,y=map(float,row)
                if not math.isfinite(x) or not math.isfinite(y):raise ValueError('nonfinite pilot waveform')
                axes[0].append(x);axes[1].append(y)
                if len(axes[0])>32768:raise ValueError('waveforms not framed by expected headers')
            flush();rc=proc.wait()
        operations.append({'command':cmd,'returncode':rc,'stdout':'source waveform stream decoded without filesystem extraction; recoverable from pinned originals and exact member list','stderr':'stream-stderr.txt'})
        if rc or member_index+1!=len(selected):raise ValueError('incomplete 7zz waveform stream')
        for b in pilot:
            rows=sorted(features[b],key=lambda r:r['sample_index'])
            if len(rows)!=len(counts[b]) or [r['sample_index'] for r in rows]!=list(range(1,len(rows)+1)):
                raise ValueError('pilot trajectory order/completeness')
            with (out/(b+'-features.jsonl')).open('x') as f:
                for row in rows:f.write(json.dumps(row,separators=(',',':'))+'\n')
        write(out/'member-inventory.json',inventory)
        write(out/'dataset.json',{'bearings':{b:len(v) for b,v in sorted(counts.items())},
              'sampling_hz_within_waveform':25600,'samples_per_waveform':32768,'waveform_duration_seconds':1.28,
              'waveform_interval_minutes':1,'waveforms_are_not_contiguous_raw_sampling':True,
              'pilot_features':sorted(pilot),'pilot_scope':'complete bearing ordinal 1 from each condition, fixed before observation read; remaining original waveforms retained',
              'feature_order':['horizontal_mean','horizontal_rms','horizontal_std','horizontal_peak_to_peak','vertical_mean','vertical_rms','vertical_std','vertical_peak_to_peak'],
              'feature_units':'original vibration units; physical unit not inferred from the publisher page',
              'feature_normalization':'none','remaining_life_or_total_length_in_features':False,
              'label_policy':'no fault type or RUL labels generated; total file counts are metadata only',
              'split_policy':{'unit':'complete bearing, never random waveform/window','train_ordinals':[1,2,3],
              'validation_ordinals':[4],'test_ordinals':[5],'status':'proposed development split, not formal holdout; no training or evaluation'},
              'raw_archive':str(archive),'tool_sha256':digest(tool),'whole_crc_test_record':str(testroot),
              'trailing_bytes_warning':tail_warning,'archive_tail_policy':'original bytes retained; only listed members interpreted; no trailing bytes executed or stripped',
              'previous_libarchive_failure_retained':str(ROOT/'artifacts/public-datasets/xjtu-sy-macos-20261016')})
        children_rss=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        if children_rss>2*1024**3:raise MemoryError('7zz peak RSS limit')
        summary={'status':'prepared','rar_all_members_crc_verified':True,'members':len(inventory),'bearings':len(counts),
                 'archive_trailing_bytes_warning':tail_warning,
                 'waveforms':sum(map(len,counts.values())),'pilot_features':{b:len(v) for b,v in features.items()},
                 'native_child_peak_rss_bytes':children_rss,'model_runs':0,'resources':check.check()}
        write(out/'preparation-summary.json',summary);write(out/'operations.json',operations)
        write(out/'source-pins.json',{'self':digest(__file__),'tool':digest(tool)})
        status='complete';print(json.dumps(summary))
    except BaseException:
        if proc and proc.poll() is None:proc.terminate();proc.wait(timeout=5)
        write(out/'preparation-failure.json',{'traceback':traceback.format_exc()});write(out/'operations.json',operations)
        raise
    finally:close(out,status)


if __name__=='__main__':main()
