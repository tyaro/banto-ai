"""Timestamp-only inventory for a predeclared MetroPT calendar; no quantity decode."""
from array import array
from collections import Counter
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import sys
import traceback
import zipfile
from macos_industrial_fetch import ROOT,close,digest,write
from macos_demand_runtime import MacCheckpoint


def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--archive',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    archive,out=Path(a.archive),Path(a.output);out.mkdir(parents=True,exist_ok=False)
    check=MacCheckpoint(seconds=870);status='failed'
    start=datetime(2020,2,1);end=datetime(2020,3,15);total=61920
    counts=array('I',[0])*total;bad_gap=bytearray(total)
    previous=None;first=None;last=None;rows=0;duplicates=0;reverse=0;cadence=Counter();scope_cadence=Counter();days=Counter();max_gap=0
    try:
        expected=json.loads((ROOT/'datasets/manifests/metropt3-source.json').read_text())['archive']
        if archive.stat().st_size!=expected['size_bytes'] or digest(archive)!=expected['sha256']:raise ValueError('source archive pin mismatch')
        with zipfile.ZipFile(archive) as z,z.open('MetroPT3(AirCompressor).csv') as f:
            header=f.readline();timestamp_column=header.rstrip(b'\r\n').split(b',')[1]
            if timestamp_column!=b'timestamp':raise ValueError('timestamp column differs')
            for line in f:
                # Parse only the first index delimiter and timestamp; retain no sensor fields.
                _,sep,rest=line.partition(b',');raw,sep2,_=rest.partition(b',')
                if not sep or not sep2:raise ValueError('missing timestamp delimiter')
                t=datetime.fromisoformat(raw.decode('ascii'));rows+=1
                if t.tzinfo is not None:raise ValueError('expected source-naive timestamp')
                if first is None:first=t
                last=t;days[t.date().isoformat()]+=1
                if previous is not None:
                    gap=(t-previous).total_seconds();cadence[str(gap)]+=1
                    duplicates+=gap==0;reverse+=gap<0
                    if start<=previous<end and start<=t<end:
                        scope_cadence[str(gap)]+=1;max_gap=max(max_gap,gap)
                        if gap>60:
                            left=max(0,int((previous-start).total_seconds()//60))
                            right=min(total-1,int((t-start).total_seconds()//60))
                            for i in range(left,right+1):bad_gap[i]=1
                if start<=t<end:
                    counts[int((t-start).total_seconds()//60)]+=1
                previous=t
                if rows%10000==0:check.check()
        bad=array('I',[0])
        for n,b in zip(counts,bad_gap):bad.append(bad[-1]+int(n==0 or bool(b)))
        splits={'train':(0,41760),'validation':(41760,51840),'test':(51840,61920)}
        windows=[];summaries={}
        for split,(left,right) in splits.items():
            origins=range(left+128 if split=='train' else left,right-32+1,1 if split=='train' else 32)
            daily={};accepted=0;count=0
            for origin in origins:
                valid=bad[origin+32]-bad[origin-128]==0
                day=(start+timedelta(minutes=origin)).date().isoformat()
                d=daily.setdefault(day,{'calendar_candidates':0,'timestamp_eligible':0})
                d['calendar_candidates']+=1;d['timestamp_eligible']+=int(valid)
                windows.append({'split':split,'origin_minute':origin,'issue_time_source_naive':(start+timedelta(minutes=origin)).isoformat(),
                                'context_bins':[origin-128,origin],'target_bins':[origin,origin+32],
                                'timestamp_eligible':valid,'reason':None if valid else 'empty_bin_or_source_gap_over_60s'})
                accepted+=int(valid);count+=1
            for d in daily.values():d['minimum_common_support_later']=(9*d['calendar_candidates']+9)//10
            summaries[split]={'calendar_candidates':count,'timestamp_eligible':accepted,'days':daily,
                             'timestamp_gate_90_percent_each_issue_day':all(d['timestamp_eligible']>=d['minimum_common_support_later'] for d in daily.values())}
        with (out/'calendar-windows.jsonl').open('x') as f:
            for w in windows:f.write(json.dumps(w,separators=(',',':'))+'\n')
        write(out/'minute-coverage.json',{'bin_start':'2020-02-01T00:00:00','bin_end_exclusive':'2020-03-15T00:00:00',
              'raw_rows_per_minute':list(counts),'gap_over_60s_affected_bins':[i for i,b in enumerate(bad_gap) if b]})
        summary={'status':'timestamp-inventory-complete','archive_sha256':expected['sha256'],
                 'source_file_counted_rows':rows,'source_first_timestamp':first.isoformat(),'source_last_timestamp':last.isoformat(),
                 'source_timestamp_duplicates':duplicates,'source_timestamp_reversals':reverse,
                 'source_daily_row_counts':dict(sorted(days.items())),'source_delta_seconds':dict(cadence),
                 'campaign_delta_seconds':dict(scope_cadence),'campaign_max_gap_seconds':max_gap,
                 'campaign_empty_minute_bins':sum(n==0 for n in counts),'campaign_gap_affected_bins':sum(bad_gap),
                 'splits':summaries,'fixed_calendar_timestamp_gate':not duplicates and not reverse and all(s['timestamp_gate_90_percent_each_issue_day'] for s in summaries.values()),
                 'quantity_values_decoded':0,'actual_common_quantity_support':'not yet known; fixed finite/quality rules applied in later authorized preparation',
                 'model_runs':0,'source_pins':{'self':digest(__file__)},'resources':check.check()}
        write(out/'summary.json',summary);status='complete'
        print(json.dumps({k:v for k,v in summary.items() if k not in ('source_daily_row_counts','source_delta_seconds','campaign_delta_seconds','splits')}))
    except BaseException:
        write(out/'failure.json',{'traceback':traceback.format_exc()});raise
    finally:close(out,status)


if __name__=='__main__':main()
