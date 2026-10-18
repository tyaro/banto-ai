"""Exploratory analysis of the opened CARE holdout (docs/research/care-next-direction-2026-10-18.md).

Reads gitignored artifacts only; extract_status.py writes the CARE-derived status table to
artifacts/care-next-direction-20261018/ (never commit it). Numbers are exploratory, not acceptance results.
"""
import json, zipfile, sys, pickle
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
Z=ROOT/'artifacts/care-zenodo-v6-holdout-20261018/CARE_To_Compare.zip'
out={}
with zipfile.ZipFile(Z) as z:
    for farm in 'BC':
        m=json.load(open(ROOT/f'artifacts/care-holdout-20261018/input/{farm}/manifest/dataset-manifest.json'))
        for item in m['files']:
            nt=item['split_row_counts']['train']
            st={}  # ordinal -> (status, timestamp)
            with z.open(item['member']) as f:
                header=f.readline().decode('utf-8-sig').rstrip('\r\n').split(';')
                si=header.index('status_type_id')
                for n,line in enumerate(f):
                    if n<nt: continue
                    p=line.rstrip(b'\r\n').split(b';')
                    st[n]=(int(p[si]),p[0].decode())
            out[(farm,item['event_id'])]={'asset':item['asset_id'],'train_rows':nt,'pred_status':st,
                'train_start':item['split_transitions'][0]['timestamp'],'pred_start':item['split_transitions'][1]['timestamp']}
            print(farm,item['event_id'],len(st),file=sys.stderr)
pickle.dump(out,open((ROOT/'artifacts/care-next-direction-20261018/status.pkl'),'wb'))
