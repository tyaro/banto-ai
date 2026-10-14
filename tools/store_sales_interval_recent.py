"""Sequential completed-window calibration; immutable point forecasts reused."""
from pathlib import Path
import argparse,datetime as dt,hashlib,json,math,time
from demand_interval_recent import calibrate_recent_completed,relative_total_interval
from store_sales_final import private_memory
from verification_records import EvidenceStore,verify_record

REPO=Path(__file__).resolve().parents[1]
PATHS=['tools/demand_interval_recent.py','tools/store_sales_interval_recent.py','tests/test_demand_interval_recent.py',
       'tools/demand_interval.py','tools/demand_forecasting.py','tools/store_sales_final.py','tools/verification_records.py']


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
        with evidence.operation('completed-window-intervals',{'future_labels_used':False,'point_forecasts_recomputed':False}):
            sources={p:(REPO/p).read_bytes() for p in PATHS}
            evidence.write_json('config-before-results',{'latest_valid_completed_windows':25,'minimum_support':20,
                'nominal_coverage':.8,'horizon':14,'first_three_intervals_reused':True,
                'availability':'target_end strictly before origin; previous-day-close assumption',
                'grid_or_alpha_tuning':False,'prospective_order_retrospective_research':True,'unseen_claim':False,
                'source_pins':{p:pin(r) for p,r in sources.items()},'formal_permission':False})
            evidence.write_json('calculator-sources',{p:r.decode('utf-8') for p,r in sources.items()})
            prior=REPO/'artifacts/representative-store-sales-interval-20261014-records'
            pm=verify_record(prior);assert pm['status']=='complete'
            def item(label):return b''.join((prior/p['path']).read_bytes() for p in pm['items'][label]['parts'])
            raw_summary=item('summary');old=json.loads(raw_summary)
            for p in ['tools/demand_interval.py','tools/demand_forecasting.py']:
                assert pin(sources[p])==old['source_pins'][p]
            raw_ledger=item('calibration-ledger');ledger=json.loads(raw_ledger)
            raw_eval=item('evaluation-intervals');fixed=json.loads(raw_eval)
            evidence.write_json('input-binding',{'prior':str(prior),'summary':pin(raw_summary),
                'calibration_ledger':pin(raw_ledger),'evaluation_points_and_fixed_intervals':pin(raw_eval),
                'raw_dataset_read':False,'calibration_forecasts_recomputed':False,'evaluation_forecasts_recomputed':False})
            rows=[]
            try:
                for original in sorted(fixed,key=lambda r:(r['origin'],r['store'])):
                    checkpoint();origin=dt.date.fromisoformat(original['origin']);store=original['store']
                    if origin==dt.date(2017,1,1):
                        model=old['calibration'][str(store)]
                        assert model['support']==25 and model['rank']==21
                        assert all(dt.date.fromisoformat(r['target_end'])<origin for r in model['scores'])
                        row={**original,'calibration':model,'reused_initial_interval':True}
                    else:
                        # Read 2017 numeric labels only after their target end is checked.
                        bank=[r for r in ledger if r['store']==store]
                        for previous in fixed:
                            end=dt.date.fromisoformat(previous['origin'])+dt.timedelta(days=13)
                            if previous['store']==store and end<origin:
                                bank.append({'target_end':str(end),'prediction':previous['point'],'actual':previous['actual']})
                        model=calibrate_recent_completed(bank,origin)
                        assert model['support']==25 and all(dt.date.fromisoformat(r['target_end'])<origin for r in model['scores'])
                        bound=relative_total_interval(original['point'],model)
                        actual=original['actual'];valid=actual is not None and bound['lower'] is not None
                        below=valid and actual<bound['lower'];above=valid and actual>bound['upper']
                        score=bound['width']+10*(max(bound['lower']-actual,0)+max(actual-bound['upper'],0)) if valid else None
                        row={'store':store,'origin':str(origin),'point':original['point'],'actual':actual,
                            **bound,'valid':valid,'covered':valid and not below and not above,'below':below,'above':above,
                            'interval_score':score,'calibration':model,'reused_initial_interval':False}
                    rows.append(row)
                evidence.write_json('sequential-calibration-intervals',rows)
            except BaseException:
                if rows:evidence.write_terminal('completed-interval-prefix',rows)
                raise
            def group(rs):
                valid=[r for r in rs if r['valid']];n=len(valid)
                return {'windows':len(rs),'valid':n,'covered':sum(r['covered'] for r in valid),
                    'coverage':sum(r['covered'] for r in valid)/n if n else None,
                    'below':sum(r['below'] for r in valid),'above':sum(r['above'] for r in valid),
                    'mean_width':math.fsum(r['width'] for r in valid)/n if n else None,
                    'mean_width_over_point':math.fsum(r['width']/r['point'] for r in valid)/n if n else None,
                    'mean_interval_score':math.fsum(r['interval_score'] for r in valid)/n if n else None}
            summary={'status':'complete','all':{'recent':group(rows),'fixed':old['all']},
                'stores':{str(s):{'recent':group([r for r in rows if r['store']==s]),'fixed':old['stores'][str(s)]} for s in [5,11,12]},
                'quarters':{str(q):{'recent':group([r for r in rows if (dt.date.fromisoformat(r['origin']).month-1)//3+1==q]),
                    'fixed':old['quarters'][str(q)]} for q in [1,2,3]},
                'point_metrics_reused':old['all']['point_metrics'],'point_forecasts_recomputed':0,'calibration_forecasts_recomputed':0,
                'new_intervals':45,'reused_initial_intervals':3,'future_calibration_label_used':False,
                'coverage_guarantee_established':False,'unseen_claim':False,'formal_permission':False,
                'source_pins':{p:pin(r) for p,r in sources.items()},'elapsed_seconds':time.monotonic()-started,
                'OS_peak_private_or_pagefile_bytes':peak}
            assert len(rows)==48 and sum(r['reused_initial_interval'] for r in rows)==3
            assert all((REPO/p).read_bytes()==r for p,r in sources.items())
            checkpoint();evidence.write_json('summary',summary)
            print(json.dumps({k:summary[k] for k in ['status','all','stores','quarters','new_intervals','reused_initial_intervals','elapsed_seconds']}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--records',required=True)
    run(parser.parse_args().records)
