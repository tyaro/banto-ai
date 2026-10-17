"""One fixed shrunk anniversary candidate on four new retrospective windows."""
from pathlib import Path
import argparse,csv,datetime as dt,hashlib,io,json,time
from demand_forecasting import finite_quantity,metrics
from demand_recent_level import recent_forecasts
from demand_anniversary import fit_anniversaries,correct_baseline
from store_sales_final import private_memory
from verification_records import EvidenceStore,verify_record

REPO=Path(__file__).resolve().parents[1]
ORIGINS=[dt.date(2016,1,1),dt.date(2016,11,1),dt.date(2016,12,18),dt.date(2017,1,1)]
PATHS=['tools/demand_anniversary.py','tools/store_sales_anniversary.py','tests/test_demand_anniversary.py',
       'tools/demand_recent_level.py','tools/demand_forecasting.py','tools/verification_records.py']


def pin(raw):return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def run(directory):
    root=Path(directory).absolute()
    if root.parent!=REPO/'artifacts' or root.exists():raise ValueError('fresh local record root required')
    started=time.monotonic();peak=0
    def checkpoint():
        nonlocal peak
        peak=max(peak,private_memory());files=list(root.iterdir())
        if time.monotonic()-started>900 or peak>2*1024**3 or len(files)>32 or sum(p.stat().st_size for p in files)>1024**3 or any(p.stat().st_size>32*1024**2 for p in files):
            raise RuntimeError('execution bound; preserve and stop without blind retry')
    with EvidenceStore(root) as evidence:
        with evidence.operation('fixed-anniversary-study',{'old_windows_repeated':False,'future_calendar_rows':False}):
            sources={p:(REPO/p).read_bytes() for p in PATHS}
            assert pin(sources['tools/demand_forecasting.py'])['sha256']=='f70717704ddf1bcbb1536be1098c6a1235f953d6dccc73b1030d6cde86d553cc'
            evidence.write_json('config-before-results',{'origins':[str(d) for d in ORIGINS],'stores':[1,2,3],
                'horizon':14,'input_window_days':28,'minimum_observed_anniversary_years':2,'shrink_prior_support':3,
                'training_cutoff_exclusive':'2016-01-01','retrospective_not_unseen':True,'formal_permission':False,
                'source_pins':{p:pin(r) for p,r in sources.items()},'parameters_searched':False})
            for i,(p,r) in enumerate(sources.items()):evidence.write_bytes('source-'+str(i),r)
            prefix=REPO/'artifacts/representative-store-sales-calendar-prefix-20261014-records'
            pm=verify_record(prefix);assert pm['status']=='complete'
            snapshot=REPO/'artifacts/representative-store-sales-final-20261014-records'
            sm=verify_record(snapshot);assert sm['status']=='complete'
            def item(root,m,label):return b''.join((root/p['path']).read_bytes() for p in m['items'][label]['parts'])
            raw=item(prefix,pm,'anniversary-analysis');analysis=json.loads(raw)
            model=fit_anniversaries(analysis['anniversaries'])
            evidence.write_json('fixed-prefix-model',{'source_record':str(prefix),'source_item':pin(raw),'model':model})
            raw=item(snapshot,sm,'final-input-csv')
            histories={s:{} for s in [1,2,3]}
            for r in csv.DictReader(io.StringIO(raw.decode())):
                s=int(r['store_nbr']);d=dt.date.fromisoformat(r['date'])
                assert s in histories and d not in histories[s]
                assert r['observed'] in ('0','1') and (r['observed']=='1')==(r['sales']!='')
                histories[s][d]=finite_quantity(float(r['sales'])) if r['observed']=='1' else None
            evidence.write_json('input-binding',{'source_record':str(snapshot),'snapshot':pin(raw),
                'source_archive_read':False,'future_holiday_row_read':False,'day_close_availability_assumed':True})
            rows=[];cells=[];methods=['weekday_mean_28','anniversary_shrunk']
            for origin in ORIGINS:
                checkpoint();bundles=[]
                try:
                    for store in [1,2,3]:
                        prediction=recent_forecasts(histories[store],origin)
                        cell_rows=[]
                        for p in prediction['predictions']:
                            date=dt.date.fromisoformat(p['date'])
                            correction=correct_baseline(model,store,date,p['weekday_mean_28'])
                            row={'store':store,'origin':str(origin),**p,'actual':histories[store].get(date),
                                'anniversary_shrunk':correction['prediction'],'correction':correction}
                            cell_rows.append(row);rows.append(row)
                        valid=[r for r in cell_rows if r['actual'] is not None and all(r[n] is not None for n in methods)]
                        cell={'store':store,'origin':str(origin),'paired':len(valid),'target_missing':sum(r['actual'] is None for r in cell_rows),
                            'methods':{n:metrics([(r[n],r['actual']) for r in valid]) for n in methods},
                            'cumulative':{n:{'actual':sum(r['actual'] for r in cell_rows),'prediction':sum(r[n] for r in cell_rows),
                                'error':sum(r[n]-r['actual'] for r in cell_rows)} for n in methods} if len(valid)==14 else None}
                        cells.append(cell);bundles.append({'cell':cell,'input_window':{k:v for k,v in prediction.items() if k!='predictions'},'predictions':cell_rows})
                    evidence.write_json('origin-'+origin.strftime('%Y%m%d'),{'cells':bundles})
                except BaseException:
                    if bundles:evidence.write_terminal('partial-origin',{'origin':str(origin),'completed_cells':bundles})
                    raise
            def group(rs):
                valid=[r for r in rs if r['actual'] is not None and all(r[n] is not None for n in methods)]
                return {'targets':len(rs),'paired':len(valid),'missing_actual':sum(r['actual'] is None for r in rs),
                    'observed_zero':sum(r['actual']==0 for r in rs),'methods':{n:metrics([(r[n],r['actual']) for r in valid]) for n in methods}}
            summary={'status':'complete','all':group(rows),'origins':{str(d):group([r for r in rows if r['origin']==str(d)]) for d in ORIGINS},
                'corrected_dates':group([r for r in rows if r['correction']['factor']!=1.]),
                'unchanged_dates':group([r for r in rows if r['correction']['factor']==1.]),
                'cells':cells,'parameters_searched':False,'unseen_claim':False,'formal_permission':False,
                'new_baseline_windows':12,'new_corrected_windows':12,'old_evaluations_repeated':False,
                'source_pins':{p:pin(r) for p,r in sources.items()},'elapsed_seconds':time.monotonic()-started,
                'OS_peak_private_or_pagefile_bytes':peak}
            assert all((REPO/p).read_bytes()==r for p,r in sources.items())
            checkpoint();evidence.write_json('summary',summary)
            print(json.dumps({k:summary[k] for k in ['status','all','origins','corrected_dates','elapsed_seconds','OS_peak_private_or_pagefile_bytes']}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--records',required=True)
    run(parser.parse_args().records)
