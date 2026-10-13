"""Fixed prefix training, retrospective own/three-store direct ridge comparison."""
from pathlib import Path
import argparse,csv,datetime as dt,hashlib,io,json,sys,time
from demand_forecasting import finite_quantity,fit_ridge,predict_ridge,metrics
from demand_related_history import available_window,comparison_features
from store_sales_final import private_memory
from verification_records import EvidenceStore,verify_record

REPO=Path(__file__).resolve().parents[1]
SOURCES=['tools/demand_forecasting.py','tools/demand_related_history.py','tools/store_sales_related_history.py',
         'tests/test_demand_related_history.py','tools/store_sales_final.py','tools/verification_records.py']
CORE='f70717704ddf1bcbb1536be1098c6a1235f953d6dccc73b1030d6cde86d553cc'
ORIGINS=[dt.date(y,m,1) for y,m in [(2016,2),(2016,5),(2016,8),(2017,2),(2017,5),(2017,8),(2017,3),(2017,6),(2017,7)]]


def pin(raw):
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def run(record_root):
    root=Path(record_root).absolute()
    if root.parent!=REPO/'artifacts' or root.exists():
        raise ValueError('fresh local record root required')
    start=time.monotonic();peak=0
    def checkpoint():
        nonlocal peak
        peak=max(peak,private_memory())
        files=list(root.iterdir())
        if time.monotonic()-start>900 or peak>2*1024**3 or len(files)>32 or any(p.stat().st_size>32*1024**2 for p in files) or sum(p.stat().st_size for p in files)>1024**3:
            raise RuntimeError('execution bound; preserve, stop, no blind retry')
    with EvidenceStore(root) as evidence:
        with evidence.operation('related-store-comparison',{'future_quantities':False,'grid':False}):
            raws={p:(REPO/p).read_bytes() for p in SOURCES}
            assert pin(raws[SOURCES[0]])['sha256']==CORE
            evidence.write_json('config-before-results',{'stores':[1,2,3],'family':'BREAD/BAKERY','horizon':14,
                'training_start':'2013-01-29','training_origin_stride_days':14,'all_training_targets_before':'2016-01-01',
                'input_window_calendar_days':28,'features_per_store':['same_weekday_mean_28','mean_last_7','mean_previous_7'],
                'shared_feature':'week_two_indicator','minimum_support':[3,6,6],'penalty':1.,
                'models':'one pooled direct model per target store per path; six new fits total',
                'matched_training_rows':True,'prior_forecasts_reused':True,'origins':[str(d) for d in ORIGINS],
                'retrospective_not_unseen':True,'parameters_selected_after_output':False,'formal_permission':False,
                'source_pins':{p:pin(r) for p,r in raws.items()}})
            for i,(p,r) in enumerate(raws.items()):evidence.write_bytes('source-'+str(i),r)
            checkpoint()
            prior=REPO/'artifacts/representative-store-sales-recent-level-20261014-records'
            pm=verify_record(prior);assert pm['status']=='complete'
            snapshot_root=REPO/'artifacts/representative-store-sales-final-20261014-records'
            sm=verify_record(snapshot_root);assert sm['status']=='complete'
            def item(directory,manifest,label):
                return b''.join((directory/p['path']).read_bytes() for p in manifest['items'][label]['parts'])
            snapshot=item(snapshot_root,sm,'final-input-csv')
            histories={s:{} for s in (1,2,3)}
            for r in csv.DictReader(io.StringIO(snapshot.decode())):
                d=dt.date.fromisoformat(r['date']);s=int(r['store_nbr'])
                assert s in histories and d not in histories[s]
                assert r['observed'] in ('0','1') and (r['observed']=='1')==(r['sales']!='')
                histories[s][d]=finite_quantity(float(r['sales'])) if r['observed']=='1' else None
            prefix={s:{d:v for d,v in h.items() if d<dt.date(2016,1,1)} for s,h in histories.items()}
            evidence.write_json('input-binding',{'snapshot':pin(snapshot),'record':str(snapshot_root),
                'prior_results':str(prior),'source_archive_read':False,'day_close_availability_assumed':True})
            train={s:{'own':[],'related':[],'y':[],'keys':[]} for s in (1,2,3)}
            train_origin=dt.date(2013,1,29)
            while train_origin+dt.timedelta(days=13)<dt.date(2016,1,1):
                checkpoint()
                windows={s:available_window(h,train_origin) for s,h in prefix.items()}
                for lead in range(14):
                    target=train_origin+dt.timedelta(days=lead)
                    for store in (1,2,3):
                        own=comparison_features(windows,store,train_origin,target,related=False)
                        related=comparison_features(windows,store,train_origin,target,related=True)
                        y=prefix[store].get(target)
                        if own is not None and related is not None and y is not None:
                            t=train[store];t['own'].append(own);t['related'].append(related);t['y'].append(y)
                            t['keys'].append([str(train_origin),str(target)])
                train_origin+=dt.timedelta(days=14)
            models={}
            for store,t in train.items():
                checkpoint()
                models[store]={method:fit_ridge(t[method],t['y'],penalty=1.) for method in ('own','related')}
                raw=json.dumps(t,separators=(',',':'),allow_nan=False).encode()
                evidence.write_json('fit-store-'+str(store),{'training':t,'training_input':pin(raw),
                    'models':models[store],'target_cutoff_exclusive':'2016-01-01'})
            all_rows=[];cells=[]
            names=('weekly_naive','weekday_mean_28','own','related')
            for origin in ORIGINS:
                checkpoint()
                previous=json.loads(item(prior,pm,'origin-'+origin.strftime('%Y%m%d')))
                retained={c['cell']['store']:c for c in previous['cells']}
                windows={s:available_window(h,origin) for s,h in histories.items()}
                bundles=[]
                try:
                    for store in (1,2,3):
                        rows=[]
                        for old in retained[store]['predictions']:
                            target=dt.date.fromisoformat(old['date']);actual=histories[store].get(target)
                            assert old['origin']==str(origin) and old['store']==store and old['actual']==actual
                            row={k:old[k] for k in ('date','lead','weekly_naive','weekday_mean_28')}
                            row.update(store=store,origin=str(origin),actual=actual,features={},clipped={})
                            for method in ('own','related'):
                                x=comparison_features(windows,store,origin,target,related=method=='related')
                                row['features'][method]=x
                                row[method],row['clipped'][method]=predict_ridge(models[store][method],x) if x is not None else (None,False)
                            row['missing_reason']=None if all(row[n] is not None for n in names) else 'insufficient_observed_features_or_retained_baseline'
                            rows.append(row);all_rows.append(row)
                        paired=[r for r in rows if r['actual'] is not None and all(r[n] is not None for n in names)]
                        cell={'store':store,'origin':str(origin),'paired':len(paired),
                            'methods':{n:metrics([(r[n],r['actual']) for r in paired]) for n in names},
                            'cumulative':{n:{'actual':sum(r['actual'] for r in rows),'predicted':sum(r[n] for r in rows),
                                            'error':sum(r[n]-r['actual'] for r in rows)} for n in names} if len(paired)==14 else None}
                        cells.append(cell);bundles.append({'cell':cell,'predictions':rows,
                            'input_sha256':{str(s):w['input_sha256'] for s,w in windows.items()}})
                    evidence.write_json('origin-'+origin.strftime('%Y%m%d'),{'cells':bundles})
                except BaseException:
                    if bundles:evidence.write_terminal('partial-origin',{'origin':str(origin),'completed_cells':bundles})
                    raise
            def group(rows):
                paired=[r for r in rows if r['actual'] is not None and all(r[n] is not None for n in names)]
                return {'targets':len(rows),'paired':len(paired),'methods':{n:metrics([(r[n],r['actual']) for r in paired]) for n in names}}
            summary={'status':'complete','all':group(all_rows),
                'years':{str(y):group([r for r in all_rows if r['origin'].startswith(str(y))]) for y in (2016,2017)},
                'stores':{str(s):group([r for r in all_rows if r['store']==s]) for s in (1,2,3)},
                'weeks':{str(w):group([r for r in all_rows if (r['lead']-1)//7+1==w]) for w in (1,2)},
                'cells':cells,'new_fits':6,'new_forecast_windows_per_path':27,'retained_baseline_windows_per_method':27,
                'training_rows':{str(s):len(t['y']) for s,t in train.items()},
                'source_pins':{p:pin(r) for p,r in raws.items()},'formal_permission':False,'unseen_claim':False,
                'elapsed_seconds':time.monotonic()-start,'OS_peak_private_or_pagefile_bytes':peak}
            assert all((REPO/p).read_bytes()==r for p,r in raws.items())
            checkpoint();evidence.write_json('summary',summary)
            print(json.dumps({k:summary[k] for k in ('status','all','years','training_rows','elapsed_seconds','OS_peak_private_or_pagefile_bytes')}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--records',required=True)
    run(parser.parse_args().records)
