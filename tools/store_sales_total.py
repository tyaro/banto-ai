"""One recent-total candidate, retaining the prior cross-city daily shape."""
from pathlib import Path
import argparse,csv,datetime as dt,hashlib,io,json,math,time
from demand_total import recent_fourteen_total,rescale_retained_shape
from demand_forecasting import metrics
from store_sales_final import private_memory
from verification_records import EvidenceStore,verify_record

REPO=Path(__file__).resolve().parents[1]
PATHS=['tools/demand_total.py','tools/store_sales_total.py','tests/test_demand_total.py',
       'tools/demand_forecasting.py','tools/store_sales_final.py','tools/verification_records.py']


def pin(raw):return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


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
        with evidence.operation('one-recent-total-study',{'old_forecasts_recomputed':False,'new_fits':False}):
            sources={p:(REPO/p).read_bytes() for p in PATHS}
            assert pin(sources['tools/demand_forecasting.py'])['sha256']=='f70717704ddf1bcbb1536be1098c6a1235f953d6dccc73b1030d6cde86d553cc'
            evidence.write_json('config-before-results',{'stores':[5,11,12],'origins':['2017-01-01','2017-05-01','2017-08-01'],
                'horizon':14,'recent_total_days':14,'minimum_support':12,'shape':'retained cross-city allocation',
                'retrospective_not_unseen':True,'parameters_searched':False,'formal_permission':False,
                'source_pins':{p:pin(r) for p,r in sources.items()}})
            for i,(p,r) in enumerate(sources.items()):evidence.write_bytes('source-'+str(i),r)
            prior=REPO/'artifacts/representative-store-sales-cross-city-20261014-records'
            pm=verify_record(prior);assert pm['status']=='complete'
            def item(label):return b''.join((prior/p['path']).read_bytes() for p in pm['items'][label]['parts'])
            old_raw=item('summary');old=json.loads(old_raw);snapshot=item('selected-input-csv')
            histories={s:{} for s in (5,11,12)}
            for r in csv.DictReader(io.StringIO(snapshot.decode())):
                store=int(r['store_nbr']);date=dt.date.fromisoformat(r['date'])
                assert store in histories and date not in histories[store] and r['observed'] in ('0','1')
                assert (r['observed']=='1')==(r['sales']!='')
                histories[store][date]=float(r['sales']) if r['observed']=='1' else None
            evidence.write_json('input-binding',{'prior':str(prior),'summary':pin(old_raw),'input':pin(snapshot),
                'raw_dataset_read':False,'new_fits':0,'future_quantity_used':False})
            rows=[];cells=[]
            for label in sorted(l for l in pm['items'] if l.startswith('origin-')):
                checkpoint();original=json.loads(item(label));bundles=[]
                try:
                    for bundle in original['cells']:
                        store=bundle['cell']['store'];origin=dt.date.fromisoformat(bundle['cell']['origin']);old_rows=bundle['predictions']
                        total=recent_fourteen_total(histories[store],origin)
                        prediction=rescale_retained_shape([r['allocated'] for r in old_rows],total['total'])
                        targets=[]
                        for r,value in zip(old_rows,prediction['predictions']):
                            assert r['actual']==histories[store].get(dt.date.fromisoformat(r['date']))
                            targets.append({**r,'recent_total_allocated':value});rows.append(targets[-1])
                        valid=[r for r in targets if r['actual'] is not None and r['recent_total_allocated'] is not None]
                        cumulative={'actual':math.fsum(r['actual'] for r in targets),'prediction':math.fsum(r['recent_total_allocated'] for r in targets),
                            'error':math.fsum(r['recent_total_allocated'] for r in targets)-math.fsum(r['actual'] for r in targets)} if len(valid)==14 else None
                        cell={'store':store,'origin':str(origin),'paired':len(valid),
                            'methods':{**bundle['cell']['methods'],'recent_total_allocated':metrics([(r['recent_total_allocated'],r['actual']) for r in valid])},
                            'cumulative':{**bundle['cell']['cumulative'],'recent_total_allocated':cumulative} if cumulative is not None else None,
                            'recent_total':total,'rescale':{k:v for k,v in prediction.items() if k!='predictions'}}
                        cells.append(cell);bundles.append({'cell':cell,'predictions':targets})
                    evidence.write_json(label,{'cells':bundles})
                except BaseException:
                    if bundles:evidence.write_terminal('partial-origin',{'label':label,'completed_cells':bundles})
                    raise
            def group(rs):
                valid=[r for r in rs if r['actual'] is not None and r['recent_total_allocated'] is not None]
                return {'targets':len(rs),'paired':len(valid),'metrics':metrics([(r['recent_total_allocated'],r['actual']) for r in valid])}
            assert len(rows)==126 and group(rows)['paired']==old['all']['paired']
            full=[c for c in cells if c['cumulative'] is not None]
            cumulative={n:metrics([(c['cumulative'][n]['prediction'],c['cumulative'][n]['actual']) for c in full]) for n in ['allocated','recent_total_allocated']}
            summary={'status':'complete','all':group(rows),'prior_all':old['all'],
                'origins':{d:{'new':group([r for r in rows if r['origin']==d]),'prior':v} for d,v in old['origins'].items()},
                'stores':{s:{'new':group([r for r in rows if r['store']==int(s)]),'prior':v} for s,v in old['stores'].items()},
                'cumulative':cumulative,'cells':cells,'source_pins':{p:pin(r) for p,r in sources.items()},
                'new_total_predictions':9,'old_forecasts_recomputed':False,'new_fits':0,'unseen_claim':False,
                'formal_permission':False,'elapsed_seconds':time.monotonic()-start,'OS_peak_private_or_pagefile_bytes':peak}
            assert all((REPO/p).read_bytes()==r for p,r in sources.items())
            checkpoint();evidence.write_json('summary',summary)
            print(json.dumps({k:summary[k] for k in ['status','all','origins','stores','cumulative','elapsed_seconds']}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--records',required=True)
    run(parser.parse_args().records)
