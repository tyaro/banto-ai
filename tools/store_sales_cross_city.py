"""Fixed recipe on three metadata-selected cities, new series only."""
from pathlib import Path
import argparse,csv,datetime as dt,hashlib,io,json,math,time,zipfile
from demand_forecasting import finite_quantity,metrics
from demand_recent_level import recent_forecasts
from demand_anniversary import fit_anniversaries,correct_baseline
from demand_allocation import redistribute_fourteen
from store_sales_final import private_memory
from verification_records import EvidenceStore,verify_record

REPO=Path(__file__).resolve().parents[1]
STORES=(5,11,12)
ORIGINS=[dt.date(2017,m,1) for m in (1,5,8)]
PATHS=['tools/store_sales_cross_city.py','tools/demand_anniversary.py','tests/test_demand_anniversary_store_ids.py',
       'tools/demand_recent_level.py','tools/demand_allocation.py','tools/demand_forecasting.py',
       'tools/store_sales_final.py','tools/verification_records.py']


def pin(raw):return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


class HashedReader(io.RawIOBase):
    def __init__(self,raw):
        self.raw=raw;self.digest=hashlib.sha256();self.byte_count=0
    def readable(self):return True
    def readinto(self,buffer):
        raw=self.raw.read(len(buffer));buffer[:len(raw)]=raw
        self.digest.update(raw);self.byte_count+=len(raw)
        return len(raw)


def run(directory):
    root=Path(directory).absolute()
    if root.parent!=REPO/'artifacts' or root.exists():raise ValueError('fresh local record root required')
    start=time.monotonic();peak=0
    def checkpoint():
        nonlocal peak
        peak=max(peak,private_memory());files=list(root.iterdir())
        if time.monotonic()-start>900 or peak>2*1024**3 or len(files)>32 or sum(p.stat().st_size for p in files)>1024**3 or any(p.stat().st_size>32*1024**2 for p in files):
            raise RuntimeError('execution bound; preserve and stop, no blind retry')
    with EvidenceStore(root) as evidence:
        with evidence.operation('three-fixed-new-cities',{'old_series_evaluated':False,'parameters_searched':False}):
            sources={p:(REPO/p).read_bytes() for p in PATHS}
            evidence.write_json('config-before-input',{'family':'BREAD/BAKERY','stores':list(STORES),
                'selection':'store-number order, first three distinct non-Quito cities; metadata only',
                'training_cutoff_exclusive':'2016-01-01','origins':[str(d) for d in ORIGINS],'horizon':14,
                'support_years':2,'shrink_prior':3,'baseline_window_days':28,'future_holiday_rows':False,
                'convenience_sample_not_population_claim':True,'formal_permission':False,
                'source_pins':{p:pin(r) for p,r in sources.items()}})
            for i,(p,r) in enumerate(sources.items()):evidence.write_bytes('source-'+str(i),r)
            calroot=REPO/'artifacts/representative-store-sales-calendar-20261014-records'
            cm=verify_record(calroot);assert cm['status']=='complete'
            def saved(directory,m,label):return b''.join((directory/p['path']).read_bytes() for p in m['items'][label]['parts'])
            metadata_raw=saved(calroot,cm,'stores-csv');metadata=list(csv.DictReader(io.StringIO(metadata_raw.decode())))
            seen={'Quito'};selected=[]
            for row in sorted(metadata,key=lambda r:int(r['store_nbr'])):
                if row['city'] not in seen:
                    selected.append(row);seen.add(row['city'])
                if len(selected)==3:break
            assert tuple(int(r['store_nbr']) for r in selected)==STORES
            calendar=json.loads(saved(calroot,cm,'calendar-analysis'))
            candidates=calendar['recurring_national_nominal_candidates_from_prefix']
            evidence.write_json('metadata-selection',{'stores':selected,'source':pin(metadata_raw),
                'fixed_nominal_anniversaries':{name:r['month_day'] for name,r in candidates.items()}})
            # Reuse unchanged, checked numerical calculators; only the store-ID API was expanded.
            allocation_root=REPO/'artifacts/representative-store-sales-allocation-20261014-records'
            am=verify_record(allocation_root);assert am['status']=='complete'
            old=json.loads(saved(allocation_root,am,'summary'))
            anniversary_root=REPO/'artifacts/representative-store-sales-anniversary-20261014-records'
            nm=verify_record(anniversary_root);assert nm['status']=='complete'
            prior=json.loads(saved(anniversary_root,nm,'summary'))
            for p in ['tools/demand_allocation.py','tools/demand_forecasting.py']:
                assert pin(sources[p])==old['source_pins'][p]
            assert pin(sources['tools/demand_recent_level.py'])==prior['source_pins']['tools/demand_recent_level.py']
            source=REPO/'data/public/store-sales-user-provided-20261014'
            manifest=json.loads((source/'source-manifest.json').read_text());archive=source/manifest['archive']['filename']
            stat_before=archive.stat();digest=hashlib.sha256()
            with archive.open('rb') as stream:
                while raw:=stream.read(256*1024):digest.update(raw)
            assert stat_before.st_size==manifest['archive']['bytes'] and digest.hexdigest()==manifest['archive']['sha256']
            member=next(r for r in manifest['members'] if r['name']=='train.csv')
            histories={s:{} for s in STORES};last_date={s:None for s in STORES};count=0
            with zipfile.ZipFile(archive) as z, z.open('train.csv') as raw_stream:
                hashed=HashedReader(raw_stream)
                with io.TextIOWrapper(io.BufferedReader(hashed),encoding='utf-8',newline='') as stream:
                    reader=csv.DictReader(stream);assert reader.fieldnames==['id','date','store_nbr','family','sales','onpromotion']
                    for row in reader:
                        count+=1
                        if count%100000==0:checkpoint()
                        if row['store_nbr'] not in ('5','11','12') or row['family']!='BREAD/BAKERY':continue
                        date=dt.date.fromisoformat(row['date'])
                        if not dt.date(2013,1,1)<=date<=dt.date(2017,8,14):continue
                        store=int(row['store_nbr'])
                        if date in histories[store] or last_date[store] is not None and date<=last_date[store]:
                            raise ValueError('selected series duplicate or unordered date')
                        histories[store][date]=finite_quantity(float(row['sales']));last_date[store]=date
            assert hashed.byte_count==member['bytes'] and hashed.digest.hexdigest()==member['sha256'] and count==member['rows']
            now=archive.stat()
            assert (now.st_dev,now.st_ino,now.st_size,now.st_mtime_ns)==(stat_before.st_dev,stat_before.st_ino,stat_before.st_size,stat_before.st_mtime_ns)
            evidence.write_json('original-source-binding',{'archive':manifest['archive'],'train_member':{k:member[k] for k in ['bytes','sha256','rows']},
                'raw_train_streamed_once':True,'numeric_conversion':'selected stores/family/date only; no onpromotion',
                'unchanged_archive_identity':True,'other_series_numerically_processed':False})
            snapshot=io.StringIO(newline='');writer=csv.writer(snapshot,lineterminator='\n');writer.writerow(['store_nbr','date','sales','observed'])
            quality={}
            for store,h in histories.items():
                quality[str(store)]={'observed':len(h),'observed_zero':sum(v==0 for v in h.values()),'missing_dates':[]}
                date=dt.date(2013,1,1)
                while date<=dt.date(2017,8,14):
                    value=h.get(date)
                    writer.writerow([store,str(date),value if value is not None else '',int(value is not None)])
                    if value is None:quality[str(store)]['missing_dates'].append(str(date))
                    date+=dt.timedelta(days=1)
            evidence.write_bytes('selected-input-csv',snapshot.getvalue().encode())
            evidence.write_json('selected-input-quality',quality)
            anniversary_rows=[]
            for description,candidate in candidates.items():
                rows=[]
                for year in [2013,2014,2015]:
                    day=dt.date.fromisoformat(str(year)+'-'+candidate['month_day'])
                    for store,h in histories.items():
                        dates=sorted(d for d,v in h.items() if day-dt.timedelta(days=28)<=d<day and d.weekday()==day.weekday())
                        rows.append({'store':store,'date':str(day),'sales':h.get(day),
                            'past_same_weekday_mean':math.fsum(h[d] for d in dates)/len(dates) if len(dates)>=3 else None,
                            'support':len(dates),'source_dates':[str(d) for d in dates]})
                anniversary_rows.append({'description':description,'month_day':candidate['month_day'],'rows':rows})
            model=fit_anniversaries(anniversary_rows,stores=STORES)
            evidence.write_json('fixed-prefix-model',{'training_rows':anniversary_rows,'model':model,'stores':list(STORES),
                'cutoff_exclusive':'2016-01-01','recipe_changed':False,'real_store_id_api_only':True})
            rows=[];cells=[];deltas=[]
            for origin in ORIGINS:
                checkpoint();bundles=[]
                try:
                    for store,h in histories.items():
                        forecast=recent_forecasts(h,origin)
                        factors=[correct_baseline(model,store,dt.date.fromisoformat(p['date']),p['weekday_mean_28'])['factor'] for p in forecast['predictions']]
                        allocation=redistribute_fourteen([p['weekday_mean_28'] for p in forecast['predictions']],factors)
                        targets=[]
                        for p,f,value in zip(forecast['predictions'],factors,allocation['predictions']):
                            row={'store':store,'origin':str(origin),**p,'factor':f,'allocated':value,'actual':h.get(dt.date.fromisoformat(p['date']))}
                            targets.append(row);rows.append(row)
                        names=['weekday_mean_28','allocated']
                        valid=[r for r in targets if r['actual'] is not None and all(r[n] is not None for n in names)]
                        cell={'store':store,'origin':str(origin),'paired':len(valid),'methods':{n:metrics([(r[n],r['actual']) for r in valid]) for n in names},
                            'cumulative':{n:{'actual':math.fsum(r['actual'] for r in targets),'prediction':math.fsum(r[n] for r in targets),
                                'error':math.fsum(r[n] for r in targets)-math.fsum(r['actual'] for r in targets)} for n in names} if len(valid)==14 else None,
                            'normalization':{k:v for k,v in allocation.items() if k!='predictions'}}
                        cells.append(cell);deltas.append(allocation['total_drift']);bundles.append({'cell':cell,'predictions':targets,
                            'input_window':{k:v for k,v in forecast.items() if k!='predictions'}})
                    evidence.write_json('origin-'+origin.strftime('%Y%m%d'),{'cells':bundles})
                except BaseException:
                    if bundles:evidence.write_terminal('partial-origin',{'origin':str(origin),'completed_cells':bundles})
                    raise
            def group(rs):
                valid=[r for r in rs if r['actual'] is not None and r['weekday_mean_28'] is not None and r['allocated'] is not None]
                return {'targets':len(rs),'paired':len(valid),'missing_actual':sum(r['actual'] is None for r in rs),
                    'methods':{n:metrics([(r[n],r['actual']) for r in valid]) for n in ['weekday_mean_28','allocated']}}
            summary={'status':'complete','all':group(rows),'stores':{str(s):group([r for r in rows if r['store']==s]) for s in STORES},
                'origins':{str(d):group([r for r in rows if r['origin']==str(d)]) for d in ORIGINS},
                'changed_nominal_dates':group([r for r in rows if r['factor']!=1.]),'cells':cells,'selected_stores':selected,
                'quality':quality,'max_absolute_total_drift':max(abs(v) for v in deltas if v is not None),
                'source_pins':{p:pin(r) for p,r in sources.items()},'unseen_population_claim':False,'formal_permission':False,
                'elapsed_seconds':time.monotonic()-start,'OS_peak_private_or_pagefile_bytes':peak,'old_series_evaluated':False}
            assert all((REPO/p).read_bytes()==r for p,r in sources.items())
            checkpoint();evidence.write_json('summary',summary)
            print(json.dumps({k:summary[k] for k in ['status','all','stores','origins','quality','max_absolute_total_drift','elapsed_seconds','OS_peak_private_or_pagefile_bytes']}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--records',required=True)
    run(parser.parse_args().records)
