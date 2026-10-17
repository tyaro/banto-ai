"""One fixed total-interval calibration on 2016, retained 2017 totals."""
from pathlib import Path
import argparse,csv,datetime as dt,hashlib,io,json,math,time
from demand_forecasting import metrics
from demand_recent_level import recent_forecasts
from demand_interval import calibrate_relative_total,relative_total_interval
from store_sales_final import private_memory
from verification_records import EvidenceStore,verify_record

REPO=Path(__file__).resolve().parents[1]
PATHS=['tools/demand_interval.py','tools/store_sales_interval.py','tests/test_demand_interval.py',
       'tools/demand_forecasting.py','tools/demand_recent_level.py','tools/store_sales_final.py','tools/verification_records.py']


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
        with evidence.operation('fixed-total-interval-study',{'old_forecasts_recomputed':False,'width_tuned_on_2017':False}):
            sources={p:(REPO/p).read_bytes() for p in PATHS}
            origins=[dt.date(2016,1,1)+dt.timedelta(days=14*k) for k in range(26)]
            evidence.write_json('config-before-results',{'stores':[5,11,12],'family':'BREAD/BAKERY','horizon':14,
                'calibration_origins':[str(d) for d in origins],'calibration_cutoff_exclusive':'2017-01-01',
                'calibration_minimum_support':20,'nominal_coverage':.8,'score':'abs(actual-point)/point',
                'rank':'ceil((n+1)*0.8)','interval':'[max(0,point*(1-q)),point*(1+q)]',
                'point_forecast':'retained mean28 total','temporal_exchangeability_established':False,
                'retrospective_not_unseen':True,'formal_permission':False,'source_pins':{p:pin(r) for p,r in sources.items()}})
            evidence.write_json('calculator-sources',{p:r.decode('utf-8') for p,r in sources.items()})
            evidence.write_json('method-reference',{'url':'https://arxiv.org/html/2107.07511v6',
                'title':'A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification',
                'sections':['1.1','2.3','5.3'],'code_or_weights_copied':False,'coverage_guarantee_established':False})
            prior=REPO/'artifacts/representative-store-sales-cross-city-20261014-records';pm=verify_record(prior);assert pm['status']=='complete'
            rolling=REPO/'artifacts/representative-store-sales-rolling-20261014-records';rm=verify_record(rolling);assert rm['status']=='complete'
            def item(directory,m,label):return b''.join((directory/p['path']).read_bytes() for p in m['items'][label]['parts'])
            rolling_raw=item(rolling,rm,'summary');rs=json.loads(rolling_raw)
            for p in ['tools/demand_forecasting.py','tools/demand_recent_level.py']:
                assert pin(sources[p])==rs['source_pins'][p]
            snapshot=item(prior,pm,'selected-input-csv');histories={s:{} for s in (5,11,12)}
            for r in csv.DictReader(io.StringIO(snapshot.decode())):
                store=int(r['store_nbr']);date=dt.date.fromisoformat(r['date'])
                assert store in histories and date not in histories[store] and r['observed'] in ('0','1')
                assert (r['observed']=='1')==(r['sales']!='')
                histories[store][date]=float(r['sales']) if r['sales']!='' else None
            evidence.write_json('input-binding',{'snapshot':pin(snapshot),'snapshot_record':str(prior),
                'evaluation_summary':pin(rolling_raw),'evaluation_record':str(rolling),
                'source_archive_read':False,'calibration_numeric_scope':'2016 labels, origin-past only input'})
            calibration={s:[] for s in histories};ledger=[]
            try:
                for origin in origins:
                    checkpoint()
                    end=origin+dt.timedelta(days=13);assert end<dt.date(2017,1,1)
                    for store,h in histories.items():
                        prediction=recent_forecasts(h,origin)
                        actual=[h.get(origin+dt.timedelta(days=i)) for i in range(14)]
                        forecast=[r['weekday_mean_28'] for r in prediction['predictions']]
                        point=math.fsum(forecast) if all(v is not None for v in forecast) else None
                        target=math.fsum(actual) if all(v is not None for v in actual) else None
                        record={'target_end':str(end),'origin':str(origin),'store':store,'prediction':point,'actual':target}
                        calibration[store].append(record)
                        ledger.append({**record,'forecast':prediction,'actual_vector':actual,
                            'target_missing_days':sum(v is None for v in actual),
                            'reason':None if point is not None and target is not None else 'incomplete_fourteen_day_prediction_or_actual'})
                evidence.write_json('calibration-ledger',ledger)
            except BaseException:
                if ledger:evidence.write_terminal('calibration-prefix',ledger)
                raise
            models={s:calibrate_relative_total(records) for s,records in calibration.items()}
            evidence.write_json('fixed-calibration-before-eval',models)
            assert all(m['radius'] is not None for m in models.values())
            intervals=[]
            for cell in rs['cells']:
                point=cell['cumulative']['weekday_mean_28']['prediction'] if cell['cumulative'] is not None else None
                actual=cell['cumulative']['weekday_mean_28']['actual'] if cell['cumulative'] is not None else None
                bound=relative_total_interval(point,models[cell['store']])
                valid=actual is not None and bound['lower'] is not None
                below=valid and actual<bound['lower'];above=valid and actual>bound['upper']
                interval_score=bound['width']+10*(max(bound['lower']-actual,0)+max(actual-bound['upper'],0)) if valid else None
                intervals.append({'store':cell['store'],'origin':cell['origin'],'point':point,'actual':actual,
                    **bound,'valid':valid,'covered':valid and not below and not above,'below':below,'above':above,
                    'interval_score':interval_score,'prediction_reused':True})
            evidence.write_json('evaluation-intervals',intervals)
            def group(rows):
                valid=[r for r in rows if r['valid']]
                n=len(valid)
                return {'windows':len(rows),'valid':n,'covered':sum(r['covered'] for r in valid),
                    'coverage':sum(r['covered'] for r in valid)/n if n else None,
                    'below':sum(r['below'] for r in valid),'above':sum(r['above'] for r in valid),
                    'mean_width':math.fsum(r['width'] for r in valid)/n if n else None,
                    'mean_width_over_point':math.fsum(r['width']/r['point'] for r in valid)/n if n else None,
                    'mean_interval_score':math.fsum(r['interval_score'] for r in valid)/n if n else None,
                    'point_metrics':metrics([(r['point'],r['actual']) for r in valid])}
            summary={'status':'complete','all':group(intervals),'stores':{str(s):group([r for r in intervals if r['store']==s]) for s in histories},
                'quarters':{str(q):group([r for r in intervals if (dt.date.fromisoformat(r['origin']).month-1)//3+1==q]) for q in (1,2,3)},
                'calibration':models,'new_calibration_forecasts':78,'evaluation_point_forecasts_recomputed':0,
                'new_interval_windows':len(intervals),'calibration_missing_windows':sum(r['actual'] is None for r in ledger),
                'calibration_not_guaranteed_exchangeable':True,'width_tuned_on_2017':False,'unseen_claim':False,
                'formal_permission':False,'source_pins':{p:pin(r) for p,r in sources.items()},
                'elapsed_seconds':time.monotonic()-started,'OS_peak_private_or_pagefile_bytes':peak}
            assert all((REPO/p).read_bytes()==r for p,r in sources.items())
            checkpoint();evidence.write_json('summary',summary)
            print(json.dumps({k:summary[k] for k in ['status','all','stores','quarters','calibration_missing_windows','elapsed_seconds']}))
            print(json.dumps({'radii':{str(s):{k:m[k] for k in ['radius','support','rank','excluded']} for s,m in models.items()}}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--records',required=True)
    run(parser.parse_args().records)
