"""Fixed sixteen-block retrospective validation; completed January reused."""
from pathlib import Path
import argparse,csv,datetime as dt,hashlib,io,json,math,time
from demand_forecasting import metrics
from demand_recent_level import recent_forecasts
from demand_anniversary import correct_baseline
from demand_allocation import redistribute_fourteen
from demand_total import recent_fourteen_total,rescale_retained_shape
from store_sales_final import private_memory
from verification_records import EvidenceStore,verify_record

REPO=Path(__file__).resolve().parents[1]
ORIGINS=[dt.date(2017,1,1)+dt.timedelta(days=14*k) for k in range(16)]
PATHS=['tools/store_sales_rolling.py','tools/demand_forecasting.py','tools/demand_recent_level.py',
       'tools/demand_anniversary.py','tools/demand_allocation.py','tools/demand_total.py',
       'tools/store_sales_final.py','tools/verification_records.py']
METHODS=['weekday_mean_28','allocated','recent_total_allocated']


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
        with evidence.operation('fixed-sixteen-block-study',{'completed_january_reused':True,'new_algorithms':False}):
            sources={p:(REPO/p).read_bytes() for p in PATHS}
            evidence.write_json('config-before-results',{'stores':[5,11,12],'origins':[str(d) for d in ORIGINS],
                'horizon':14,'new_origin_windows':45,'reused_origin_windows':3,'new_fit':False,
                'new_algorithms':False,'retrospective_not_unseen':True,'formal_permission':False,
                'source_pins':{p:pin(r) for p,r in sources.items()}})
            evidence.write_json('calculator-sources',{p:r.decode('utf-8') for p,r in sources.items()})
            prior=REPO/'artifacts/representative-store-sales-cross-city-20261014-records'
            pm=verify_record(prior);assert pm['status']=='complete'
            total_root=REPO/'artifacts/representative-store-sales-total-20261014-records'
            tm=verify_record(total_root);assert tm['status']=='complete'
            def item(directory,m,label):return b''.join((directory/p['path']).read_bytes() for p in m['items'][label]['parts'])
            previous=json.loads(item(prior,pm,'summary'));total_previous=json.loads(item(total_root,tm,'summary'))
            for p in ['tools/demand_recent_level.py','tools/demand_allocation.py','tools/demand_anniversary.py']:
                assert pin(sources[p])==previous['source_pins'][p]
            for p in ['tools/demand_total.py','tools/demand_forecasting.py']:
                assert pin(sources[p])==total_previous['source_pins'][p]
            raw_model=item(prior,pm,'fixed-prefix-model');saved_model=json.loads(raw_model)
            model={int(k):v for k,v in saved_model['model'].items()};assert set(model)=={5,11,12}
            assert saved_model['cutoff_exclusive']=='2016-01-01'
            snapshot=item(prior,pm,'selected-input-csv');histories={s:{} for s in (5,11,12)}
            for r in csv.DictReader(io.StringIO(snapshot.decode())):
                s=int(r['store_nbr']);d=dt.date.fromisoformat(r['date'])
                assert s in histories and d not in histories[s] and (r['observed']=='1')==(r['sales']!='')
                histories[s][d]=float(r['sales']) if r['observed']=='1' else None
            raw_january=item(total_root,tm,'origin-20170101');january=json.loads(raw_january)
            evidence.write_json('input-binding',{'snapshot':pin(snapshot),'snapshot_record':str(prior),
                'model':pin(raw_model),'january':pin(raw_january),'january_record':str(total_root),
                'original_archive_read':False,'new_fit':False,'old_checks_repeated':False})
            all_rows=[];cells=[]
            for origin in ORIGINS:
                checkpoint();bundles=[]
                try:
                    if origin==dt.date(2017,1,1):
                        bundles=january['cells']
                        for b in bundles:
                            assert b['cell']['origin']==str(origin) and b['cell']['store'] in histories
                            for r in b['predictions']:
                                assert r['actual']==histories[r['store']].get(dt.date.fromisoformat(r['date']))
                            cells.append({**b['cell'],'reused':True});all_rows.extend(b['predictions'])
                    else:
                        for store,h in histories.items():
                            base=recent_forecasts(h,origin)
                            factors=[correct_baseline(model,store,dt.date.fromisoformat(r['date']),r['weekday_mean_28'])['factor'] for r in base['predictions']]
                            allocation=redistribute_fourteen([r['weekday_mean_28'] for r in base['predictions']],factors)
                            total=recent_fourteen_total(h,origin)
                            rescaled=rescale_retained_shape(allocation['predictions'],total['total'])
                            rows=[]
                            for r,f,p,q in zip(base['predictions'],factors,allocation['predictions'],rescaled['predictions']):
                                rows.append({'store':store,'origin':str(origin),**r,'factor':f,'allocated':p,
                                    'recent_total_allocated':q,'actual':h.get(dt.date.fromisoformat(r['date']))})
                            valid=[r for r in rows if r['actual'] is not None and all(r[n] is not None for n in METHODS)]
                            cell={'store':store,'origin':str(origin),'reused':False,'paired':len(valid),
                                'methods':{n:metrics([(r[n],r['actual']) for r in valid]) for n in METHODS},
                                'cumulative':{n:{'prediction':math.fsum(r[n] for r in rows),'actual':math.fsum(r['actual'] for r in rows),
                                    'error':math.fsum(r[n] for r in rows)-math.fsum(r['actual'] for r in rows)} for n in METHODS} if len(valid)==14 else None,
                                'recent_total':total,'total_drift':allocation['total_drift']}
                            bundles.append({'cell':cell,'predictions':rows,'input_window':{k:v for k,v in base.items() if k!='predictions'}})
                            cells.append(cell);all_rows.extend(rows)
                    evidence.write_json('origin-'+origin.strftime('%Y%m%d'),{'reused':origin==dt.date(2017,1,1),'cells':bundles})
                except BaseException:
                    if bundles:evidence.write_terminal('partial-origin',{'origin':str(origin),'completed_cells':bundles})
                    raise
            def group(rs):
                paired=[r for r in rs if r['actual'] is not None and all(r[n] is not None for n in METHODS)]
                return {'targets':len(rs),'paired':len(paired),'methods':{n:metrics([(r[n],r['actual']) for r in paired]) for n in METHODS}}
            full=[c for c in cells if c['cumulative'] is not None]
            cumulative={n:metrics([(c['cumulative'][n]['prediction'],c['cumulative'][n]['actual']) for c in full]) for n in METHODS}
            summary={'status':'complete','all':group(all_rows),'stores':{str(s):group([r for r in all_rows if r['store']==s]) for s in (5,11,12)},
                'weeks':{str(w):group([r for r in all_rows if (r['lead']-1)//7+1==w]) for w in (1,2)},
                'months':{str(m):group([r for r in all_rows if dt.date.fromisoformat(r['date']).month==m]) for m in range(1,9)},
                'cumulative':cumulative,'cells':cells,'new_origin_windows':45,'reused_origin_windows':3,
                'source_pins':{p:pin(r) for p,r in sources.items()},'source_archive_read':False,'new_fit':False,
                'unseen_claim':False,'formal_permission':False,'elapsed_seconds':time.monotonic()-started,
                'OS_peak_private_or_pagefile_bytes':peak}
            assert len(all_rows)==672 and len(cells)==48 and sum(c.get('reused',False) for c in cells)==3
            assert all((REPO/p).read_bytes()==r for p,r in sources.items())
            checkpoint();evidence.write_json('summary',summary)
            print(json.dumps({k:summary[k] for k in ['status','all','stores','cumulative','new_origin_windows','reused_origin_windows','elapsed_seconds']}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--records',required=True)
    run(parser.parse_args().records)
