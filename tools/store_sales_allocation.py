"""One new allocation transformation using immutable prior predictions only."""
from pathlib import Path
import argparse,hashlib,json,math,time
from demand_forecasting import metrics
from demand_allocation import redistribute_fourteen
from store_sales_final import private_memory
from verification_records import EvidenceStore,verify_record

REPO=Path(__file__).resolve().parents[1]
PATHS=['tools/demand_allocation.py','tools/store_sales_allocation.py','tests/test_demand_allocation.py',
       'tools/demand_forecasting.py','tools/store_sales_final.py','tools/verification_records.py']


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
        with evidence.operation('new-calendar-allocation',{'new_fit':False,'prior_forecasts_recomputed':False}):
            sources={p:(REPO/p).read_bytes() for p in PATHS}
            assert pin(sources['tools/demand_forecasting.py'])['sha256']=='f70717704ddf1bcbb1536be1098c6a1235f953d6dccc73b1030d6cde86d553cc'
            evidence.write_json('config-before-results',{'horizon':14,'normalization':'sum(b)*b_i*f_i/sum(b_i*f_i)',
                'actual_or_observed_mask_used_to_normalize':False,'total_rel_tol':1e-12,'total_abs_tol':1e-9,
                'new_fits':0,'source_archive_read':False,'old_baselines_reused':True,'retrospective_not_unseen':True,
                'source_pins':{p:pin(r) for p,r in sources.items()},'formal_permission':False})
            for i,(p,r) in enumerate(sources.items()):evidence.write_bytes('source-'+str(i),r)
            prior=REPO/'artifacts/representative-store-sales-anniversary-20261014-records'
            pm=verify_record(prior);assert pm['status']=='complete'
            def item(label):return b''.join((prior/p['path']).read_bytes() for p in pm['items'][label]['parts'])
            prior_summary_raw=item('summary');prior_summary=json.loads(prior_summary_raw)
            evidence.write_json('prior-binding',{'root':str(prior),'summary':pin(prior_summary_raw),
                'all_input_items':{label:pin(item(label)) for label in pm['items'] if label.startswith('origin-')}})
            rows=[];cells=[];deltas=[]
            for label in sorted(l for l in pm['items'] if l.startswith('origin-')):
                checkpoint();original=json.loads(item(label));bundles=[]
                try:
                    for bundle in original['cells']:
                        old=bundle['predictions'];assert len(old)==14 and [r['lead'] for r in old]==list(range(1,15))
                        baseline=[r['weekday_mean_28'] for r in old];factors=[r['correction']['factor'] for r in old]
                        for row,b,f in zip(old,baseline,factors):
                            assert b is not None and math.isclose(b*f,row['anniversary_shrunk'],rel_tol=1e-12,abs_tol=1e-9)
                        allocation=redistribute_fourteen(baseline,factors)
                        new_rows=[{**r,'allocated':value} for r,value in zip(old,allocation['predictions'])]
                        valid=[r for r in new_rows if r['actual'] is not None and r['allocated'] is not None]
                        assert len(valid)==bundle['cell']['paired']
                        full=len(valid)==14
                        cumulative={'actual':sum(r['actual'] for r in new_rows),'prediction':math.fsum(r['allocated'] for r in new_rows),
                            'error':math.fsum(r['allocated'] for r in new_rows)-sum(r['actual'] for r in new_rows)} if full else None
                        if full:
                            assert math.isclose(cumulative['prediction'],bundle['cell']['cumulative']['weekday_mean_28']['prediction'],rel_tol=1e-12,abs_tol=1e-9)
                        cell={'store':bundle['cell']['store'],'origin':bundle['cell']['origin'],'paired':len(valid),
                            'methods':{**bundle['cell']['methods'],'allocated':metrics([(r['allocated'],r['actual']) for r in valid])},
                            'cumulative':{**bundle['cell']['cumulative'],'allocated':cumulative} if full else None,
                            'normalization':{k:v for k,v in allocation.items() if k!='predictions'}}
                        cells.append(cell);rows.extend(new_rows);deltas.append(allocation['total_drift'])
                        bundles.append({'cell':cell,'predictions':new_rows})
                    evidence.write_json(label,{'cells':bundles})
                except BaseException:
                    if bundles:evidence.write_terminal('partial-origin',{'label':label,'completed_cells':bundles})
                    raise
            def group(rs):
                valid=[r for r in rs if r['actual'] is not None and r['allocated'] is not None]
                return {'targets':len(rs),'paired':len(valid),'missing_actual':sum(r['actual'] is None for r in rs),
                    'metrics':metrics([(r['allocated'],r['actual']) for r in valid])}
            summary={'status':'complete','all':group(rows),'prior_all':prior_summary['all'],
                'origins':{d:{'allocated':group([r for r in rows if r['origin']==d]),'prior':g} for d,g in prior_summary['origins'].items()},
                'calendar_adjusted_days':group([r for r in rows if r['correction']['factor']!=1.]),
                'other_days':group([r for r in rows if r['correction']['factor']==1.]),
                'cells':cells,'max_absolute_total_drift':max(abs(v) for v in deltas if v is not None),
                'new_allocation_windows':12,'new_fits':0,'original_calculators_repeated':False,'raw_dataset_read':False,
                'source_pins':{p:pin(r) for p,r in sources.items()},'unseen_claim':False,'formal_permission':False,
                'elapsed_seconds':time.monotonic()-started,'OS_peak_private_or_pagefile_bytes':peak}
            assert all((REPO/p).read_bytes()==r for p,r in sources.items())
            checkpoint();evidence.write_json('summary',summary)
            print(json.dumps({k:summary[k] for k in ['status','all','origins','calendar_adjusted_days','other_days','max_absolute_total_drift','elapsed_seconds']}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--records',required=True)
    run(parser.parse_args().records)
