"""Fixed one-candidate public demand study using retained input/results.

Known 2016/2017 windows are development comparisons with reused baseline
predictions. Supplemental windows are retrospective, not a new unseen test.
"""
from pathlib import Path
import argparse,csv,datetime as dt,hashlib,io,json,subprocess,sys,time
from demand_forecasting import finite_quantity,metrics
from demand_recent_level import recent_forecasts
from store_sales_final import private_memory
from verification_records import EvidenceStore,verify_record

REPO=Path(__file__).resolve().parents[1]
DEVELOPMENT=[dt.date(year,month,1) for year in (2016,2017) for month in (2,5,8)]
SUPPLEMENTAL=[dt.date(2017,month,1) for month in (3,6,7)]
PATHS=['tools/demand_forecasting.py','tools/demand_recent_level.py','tools/store_sales_recent_level.py',
       'tools/store_sales_final.py','tools/verification_records.py','tests/test_demand_recent_level.py']
CORE_SHA='f70717704ddf1bcbb1536be1098c6a1235f953d6dccc73b1030d6cde86d553cc'


def pin(raw):
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def run(record_root):
    root=Path(record_root).absolute()
    if root.parent!=REPO/'artifacts' or root.exists():
        raise ValueError('fresh local record root required')
    started=time.monotonic();peak=0
    def checkpoint():
        nonlocal peak
        peak=max(peak,private_memory())
        if time.monotonic()-started>900 or peak>2*1024**3:
            raise RuntimeError('execution bound; preserve and stop, no blind retry')
        files=list(root.iterdir())
        if len(files)>32 or any(p.stat().st_size>32*1024**2 for p in files) or sum(p.stat().st_size for p in files)>1024**3:
            raise RuntimeError('execution output/file bound')
    with EvidenceStore(root) as evidence:
        with evidence.operation('recent-weekday-study',{'old_forecasts_repeated':False,'parameters_searched':False}):
            raws={name:(REPO/name).read_bytes() for name in PATHS}
            if pin(raws['tools/demand_forecasting.py'])['sha256']!=CORE_SHA:
                raise ValueError('retained baseline calculator differs')
            for index,(name,raw) in enumerate(raws.items()):
                evidence.write_bytes('calculator-source-'+str(index),raw)
            with evidence.operation('base-head',{'read_only':True}) as op:
                completed=subprocess.run(['git','rev-parse','HEAD'],cwd=REPO,capture_output=True,timeout=10)
                op.capture_process(completed)
            config={'family':'BREAD/BAKERY','stores':[1,2,3],'horizon_days':14,
                'candidate':'weekday_mean_28','lookback_calendar_days':28,'missing':'exclude, never zero-fill',
                'zero':'observed zero retained','forecast':'mean of observed same weekdays within [origin-28,origin)',
                'development_origins':[str(d) for d in DEVELOPMENT],
                'supplemental_origins':[str(d) for d in SUPPLEMENTAL],
                'selection':'fixed before candidate output inspection; no grid, no stage-selected winner',
                'supplemental_is_not_independently_unseen':True,
                'supplemental_caveat':'source period already existed as historical fit input in preceding pilot',
                'no_future_promotion':True,'no_new_ridge_fits':True,'formal_permission':False,
                'base_head':completed.stdout.decode().strip(),'working_source_pins':{name:pin(raw) for name,raw in raws.items()},
                'working_new_sources_not_yet_committed':True}
            evidence.write_json('config-before-results',config)
            checkpoint()
            old_roots={2016:REPO/'artifacts/representative-store-sales-validation-20261014-records',
                       2017:REPO/'artifacts/representative-store-sales-final-20261014-records'}
            old_manifests={year:verify_record(directory) for year,directory in old_roots.items()}
            if any(m['status']!='complete' for m in old_manifests.values()):
                raise ValueError('retained original results are incomplete')
            def read_item(year,label):
                return b''.join((old_roots[year]/p['path']).read_bytes() for p in old_manifests[year]['items'][label]['parts'])
            snapshot=read_item(2017,'final-input-csv')
            histories={store:{} for store in (1,2,3)}
            for row in csv.DictReader(io.StringIO(snapshot.decode('utf-8'))):
                store=int(row['store_nbr']);date=dt.date.fromisoformat(row['date'])
                if store not in histories or date in histories[store]:
                    raise ValueError('snapshot series/date duplicate or unexpected')
                if row['observed'] not in ('0','1') or (row['observed']=='1')!=(row['sales']!=''):
                    raise ValueError('snapshot mask mismatch')
                histories[store][date]=finite_quantity(float(row['sales'])) if row['observed']=='1' else None
            evidence.write_json('input-binding',{'retained_snapshot_record':str(old_roots[2017]),'snapshot':pin(snapshot),
                'source_archive_read':False,'past_sales_day_close_availability_assumption':True,
                'old_original_results':{str(year):{'record':str(directory),'summary':pin(read_item(year,'summary'))}
                     for year,directory in old_roots.items()}})
            all_rows=[];cells=[]
            for stage,origins in [('development',DEVELOPMENT),('supplemental',SUPPLEMENTAL)]:
                for origin in origins:
                    origin_cells=[]
                    try:
                        for store in (1,2,3):
                            checkpoint()
                            history=histories[store]
                            # Build predictions from strictly available quantities first.
                            past={date:value for date,value in history.items() if date<origin}
                            prediction=recent_forecasts(past,origin,include_weekly_naive=stage=='supplemental')
                            reused=None
                            if stage=='development':
                                old=json.loads(read_item(origin.year,f'cell-{store}-{origin.month}'))
                                reused={row['date']:row for row in old['predictions']}
                            rows=[]
                            for candidate in prediction['predictions']:
                                target=dt.date.fromisoformat(candidate['date']);actual=history.get(target)
                                if reused is not None:
                                    previous=reused[candidate['date']]
                                    if previous['origin']!=str(origin) or previous['store']!=store or previous['actual']!=actual:
                                        raise ValueError('retained baseline/actual correspondence mismatch')
                                    baseline=previous['weekly_naive'];baseline_date=previous['naive_source_date']
                                else:
                                    baseline=candidate['weekly_naive'];baseline_date=candidate['naive_source_date']
                                row={'stage':stage,'store':store,'origin':str(origin),**candidate,
                                     'weekly_naive':baseline,'naive_source_date':baseline_date,
                                     'baseline_reused':stage=='development','actual':actual,
                                     'actual_missing_reason':None if actual is not None else 'target_unobserved'}
                                rows.append(row);all_rows.append(row)
                            paired=[row for row in rows if row['actual'] is not None and row['weekly_naive'] is not None and row['weekday_mean_28'] is not None]
                            cell={'stage':stage,'store':store,'origin':str(origin),'paired_targets':len(paired),
                                  'target_missing':sum(row['actual'] is None for row in rows),'methods':{}}
                            for name in ('weekly_naive','weekday_mean_28'):
                                valid=[row for row in rows if row['actual'] is not None and row[name] is not None]
                                full=len(valid)==14
                                cell['methods'][name]={'paired':metrics([(row[name],row['actual']) for row in paired]),
                                    'individual':metrics([(row[name],row['actual']) for row in valid]),
                                    'forecast_missing':sum(row[name] is None for row in rows),
                                    'cumulative_14_days':{'actual':sum(row['actual'] for row in rows),
                                        'predicted':sum(row[name] for row in rows),
                                        'signed_error':sum(row[name]-row['actual'] for row in rows)} if full else None}
                            cells.append(cell)
                            origin_cells.append({'input_window':{key:value for key,value in prediction.items() if key!='predictions'},
                                                 'cell':cell,'predictions':rows})
                        evidence.write_json('origin-'+origin.strftime('%Y%m%d'),{'stage':stage,'cells':origin_cells})
                    except BaseException:
                        if origin_cells:
                            evidence.write_terminal('partial-origin',{'stage':stage,'origin':str(origin),'completed_cells':origin_cells})
                        raise
                    print(json.dumps({'stage':stage,'origin':str(origin),'cells':len(origin_cells)}),flush=True)
            methods=('weekly_naive','weekday_mean_28')
            def group_metrics(rows):
                paired=[row for row in rows if row['actual'] is not None and all(row[name] is not None for name in methods)]
                return {'expected_targets':len(rows),'paired_targets':len(paired),
                        'methods':{name:metrics([(row[name],row['actual']) for row in paired]) for name in methods}}
            summary={'status':'complete','stages':{stage:group_metrics([row for row in all_rows if row['stage']==stage])
                for stage in ('development','supplemental')},'development_years':{str(year):group_metrics([row for row in all_rows
                if row['stage']=='development' and row['origin'].startswith(str(year))]) for year in (2016,2017)},
                'stage_store':{stage:{str(store):group_metrics([row for row in all_rows if row['stage']==stage and row['store']==store])
                    for store in (1,2,3)} for stage in ('development','supplemental')},
                'cells':cells,'future_information_used':False,'unseen_performance_claim':False,'formal_permission':False,
                'new_candidate_forecasts':27,'new_naive_forecasts':9,'retained_naive_forecasts_reused':18,
                'old_ridge_forecasts_recomputed':0,'source_archive_read':False,
                'elapsed_seconds':time.monotonic()-started,'OS_peak_private_or_pagefile_bytes':peak,
                'source_pins':config['working_source_pins']}
            if any((REPO/name).read_bytes()!=raw for name,raw in raws.items()):
                raise ValueError('source changed during the study')
            checkpoint()
            evidence.write_json('summary',summary)
            print(json.dumps({'status':'complete','stages':summary['stages'],'development_years':summary['development_years'],
                              'elapsed_seconds':summary['elapsed_seconds'],'peak_bytes':peak}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--records',required=True)
    run(parser.parse_args().records)
