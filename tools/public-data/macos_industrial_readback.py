"""Independent saved-byte and input-boundary checks; no forecast or score."""
import argparse
from array import array
import importlib.util
import json
import math
from pathlib import Path
import sys
from macos_industrial_fetch import close,digest,write,ROOT
from macos_demand_runtime import MacCheckpoint


def main():
    p=argparse.ArgumentParser();p.add_argument('--raw',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    raw,out=Path(a.raw),Path(a.output);out.mkdir(parents=True,exist_ok=False);check=MacCheckpoint(seconds=870)
    status='failed';roots=[];files_checked=0
    try:
        candidates=[raw/n for n in ('metropt3','hydraulic',*[f'xjtu-part{i:02}' for i in range(1,7)])]
        candidates += [ROOT/'artifacts/public-datasets'/n for n in ('metropt3-public-2020-02-21','hydraulic-macos-20261016','xjtu-sy-macos-20261016-7zip')]
        candidates += sorted((ROOT/'artifacts').glob('macos-industrial-fetch-*-20261016-records'))
        candidates += [ROOT/'artifacts'/f'macos-industrial-prepare-{kind}-20261016-records' for kind in ('metro','hydraulic','xjtu')]
        candidates += [ROOT/'artifacts/macos-industrial-prepare-xjtu-7zip-20261016-records',
                       ROOT/'artifacts/macos-industrial-xjtu-7zip-test-20261016-records',
                       ROOT/'artifacts/public-datasets/xjtu-sy-macos-20261016',
                       raw/'7zip-tool',raw/'7zip-macos-26.04']
        for root in candidates:
            closure=json.loads((root/'root-closed.json').read_text())
            expected_status='failed' if root.name in ('macos-industrial-prepare-xjtu-20261016-records','xjtu-sy-macos-20261016') else 'complete'
            if closure['status']!=expected_status:raise ValueError('unexpected root status')
            expected={i['name'] for i in closure['files']}
            actual={p.name for p in root.iterdir() if p.is_file()}-{'root-closed.json'}
            if expected!=actual:raise ValueError('closure file set mismatch')
            for i in closure['files']:
                check.check();f=root/i['name']
                if f.stat().st_size!=i['bytes'] or digest(f)!=i['sha256']:raise ValueError('saved bytes mismatch')
                files_checked+=1
            roots.append({'path':str(root),'files':len(expected),'status_preserved':expected_status,'closure_sha256':digest(root/'root-closed.json')})
            if 'records' in root.name:
                if sum(f.stat().st_size for f in root.iterdir() if f.is_file())>16*1024**2:raise ValueError('record total size cap')
                if len(actual)+1>512 or any(f.stat().st_size>256*1024 for f in root.iterdir() if f.is_file()):raise ValueError('record file count/part size cap')
            elif root in candidates[8:11]:
                if len(actual)+1>24 or sum(f.stat().st_size for f in root.iterdir() if f.is_file())>768*1024**2:raise ValueError('normal artifact cap')
                if any(f.stat().st_size>32*1024**2 for f in root.iterdir() if f.is_file()):raise ValueError('single artifact cap')
        # Reuse the existing input adapter, not its trainer or forecasting model.
        modelpath=ROOT/'models/mini-transformer/data.py'
        spec=importlib.util.spec_from_file_location('metro_existing_input_adapter',modelpath)
        m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
        prepared,pins=m.load_fixed_day(ROOT/'artifacts/public-datasets/metropt3-public-2020-02-21')
        mx,my=prepared.batch(prepared.origins['train'][:1],'train')
        if list(mx.shape)!=[1,3,128] or list(my.shape)!=[1,3,32]:raise ValueError('Metro input shape')
        hydro=ROOT/'artifacts/public-datasets/hydraulic-macos-20261016'
        hm=json.loads((hydro/'dataset.json').read_text())
        for s in hm['signals']:
            if (hydro/s['file']).stat().st_size!=2205*600*4:raise ValueError('hydraulic file shape')
        labels=json.loads((hydro/'condition-labels.json').read_text())
        if len(labels['rows'])!=2205 or hm['labels_are_features']:raise ValueError('hydraulic label separation')
        xroot=ROOT/'artifacts/public-datasets/xjtu-sy-macos-20261016-7zip'
        xm=json.loads((xroot/'dataset.json').read_text());inventory=json.loads((xroot/'member-inventory.json').read_text())
        counts={}
        for bearing in xm['pilot_features']:
            rows=[json.loads(line) for line in (xroot/(bearing+'-features.jsonl')).read_text().splitlines()]
            n=xm['bearings'][bearing]
            if [r['sample_index'] for r in rows]!=list(range(1,n+1)):raise ValueError('pilot order/completeness')
            if any(set(r)!={'sample_index','feature_values'} or len(r['feature_values'])!=8 or not all(map(math.isfinite,r['feature_values'])) for r in rows):raise ValueError('pilot fields')
            if any(min(r['feature_values'][i] for i in (1,2,3,5,6,7))<0 for r in rows):raise ValueError('negative RMS/std/range')
            counts[bearing]=n
        result={'status':'passed','roots_checked':roots,'saved_files_checked':files_checked,
                'metro_input_shape':list(mx.shape),'metro_target_shape':list(my.shape),
                'metro_origins':{k:len(v) for k,v in prepared.origins.items()},
                'hydraulic_cycles':2205,'xjtu_bearings':len(xm['bearings']),
                'xjtu_pilot_complete_sequences':counts,'xjtu_inventory_entries':len(inventory),
                'model_imports':0,'model_fit_or_inference_or_scoring':0,
                'source_pins':{str(f.relative_to(ROOT)):digest(f) for f in [Path(__file__),modelpath,ROOT/'tools/macos_demand_runtime.py']},
                'resources':check.check()}
        write(out/'summary.json',result);status='complete';print(json.dumps({k:v for k,v in result.items() if k!='roots_checked'}))
    finally:close(out,status)


if __name__=='__main__':main()
