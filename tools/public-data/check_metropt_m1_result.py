"""Independent saved-prediction arithmetic; no production scorer or model import."""
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
import traceback

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'models/mini-transformer'));sys.path.insert(0,str(ROOT/'tools'))
from metropt_multiday import CONFIG, Files, contract, digest, verify_closed
from macos_demand_runtime import MacCheckpoint


def close_enough(a,b):
    if not math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-12):raise AssertionError((a,b))


def average_days(values,keys):
    return statistics.fmean(statistics.fmean(x for x,key in zip(values,keys,strict=True) if key[0]==day) for day in sorted({k[0] for k in keys}))


def main(campaign,output):
    files=Files(output);check=MacCheckpoint(seconds=870);status='failed'
    try:
        files.sources([Path(__file__),ROOT/'models/mini-transformer/metropt_multiday.py',ROOT/'tools/macos_demand_runtime.py'])
        c=contract();campaign=Path(campaign);checks=[]
        roots=[campaign/('unit-'+str(s)) for s in c['training']['init_seeds']]+[campaign/'scores',ROOT/'artifacts/metropt-m1-learning-export-20261016']
        pins=[]
        for root in roots:
            closure=verify_closed(root);sizes=[p.stat().st_size for p in root.iterdir()]
            assert len(sizes)<=24 and max(sizes)<=32*1024**2 and sum(sizes)<=768*1024**2
            pins.append({'root':str(root),'closure_sha256':digest(root/'root-closed.json'),'files':len(sizes),'bytes':sum(sizes)})
        checks.append('all 3 seed roots, scoring root and Rust reference export closed and hash/size valid')
        scores=campaign/'scores';metrics=json.loads((scores/'metrics.json').read_bytes());summary=json.loads((scores/'summary.json').read_bytes())
        labels=json.loads((scores/'evaluation-labels.json').read_bytes());keys=labels['keys'];actual=labels['actual']
        freeze=json.loads((scores/'freeze.json').read_bytes())
        assert labels['freeze_sha256']==digest(scores/'freeze.json') and freeze['test_target_reads_before_this_record']==0
        assert {x['seed'] for x in freeze['units']}==set(c['training']['init_seeds'])
        scales=json.loads((ROOT/'artifacts/public-datasets/metropt3-multiday-macos-20261016/scales.json').read_bytes())
        scale=[s['T32'] for s in scales];computed={}
        for seed in c['training']['init_seeds']:
            root=campaign/('unit-'+str(seed));journal=json.loads((root/'journal.json').read_bytes())
            for variant in c['model']['variants']:
                steps=[x['step'] for x in journal if x.get('variant')==variant and 'loss' in x]
                assert steps==list(range(1,4097))
            computed[str(seed)]={}
            for variant in c['model']['variants']:
                rows=json.loads((root/('test-'+variant+'.json')).read_bytes())['rows'];assert [row['key'] for row in rows]==keys
                pred=[row['prediction'] for row in rows];by_target=[]
                for v in range(3):
                    native=[];mae=[];coverage=[];width=[];lower=[];upper=[]
                    for i in range(len(keys)):
                        pin=[]
                        for h in range(32):
                            for j,tau in enumerate((.1,.5,.9)):
                                y=actual[i][v][h];q=pred[i][v][h][j]
                                pin.append(tau*(y-q) if y>=q else (1-tau)*(q-y))
                        native.append(statistics.fmean(pin))
                        mae.append(statistics.fmean(abs(actual[i][v][h]-pred[i][v][h][1]) for h in range(32)))
                        coverage.append(statistics.fmean(int(pred[i][v][h][0]<=actual[i][v][h]<=pred[i][v][h][2]) for h in range(32)))
                        width.append(statistics.fmean(pred[i][v][h][2]-pred[i][v][h][0] for h in range(32)))
                        lower.append(statistics.fmean(int(actual[i][v][h]<pred[i][v][h][0]) for h in range(32)))
                        upper.append(statistics.fmean(int(actual[i][v][h]>pred[i][v][h][2]) for h in range(32)))
                    target={name:average_days(values,keys) for name,values in [('mae',mae),('pinball',native),('coverage80',coverage),('width80',width),('lower_miss_rate',lower),('upper_miss_rate',upper)]}
                    for name,x in target.items():close_enough(x,metrics['seeds'][str(seed)][variant]['targets'][v][name])
                    for h in range(32):
                        lead=average_days([abs(actual[i][v][h]-pred[i][v][h][1]) for i in range(len(keys))],keys)
                        close_enough(lead,metrics['seeds'][str(seed)][variant]['targets'][v]['lead_mae'][h])
                    by_target.append(target)
                primary=statistics.fmean(target['pinball']/scale[v] for v,target in enumerate(by_target))
                close_enough(primary,metrics['seeds'][str(seed)][variant]['fixed_scale_pinball'])
                computed[str(seed)][variant]=primary;check.check()
        checks.append('all six models: 4096 ordered updates; independent MAE/pinball/coverage/width/misses/lead and day weighting match')
        baseline_rows=json.loads((roots[0]/'test-baselines.json').read_bytes())
        for mode,rows in baseline_rows.items():
            for v in range(3):
                errors=[statistics.fmean(abs(actual[i][v][h]-row['prediction'][v][h]) for h in range(32)) for i,row in enumerate(rows)]
                close_enough(average_days(errors,keys),metrics['point_baselines'][mode][v]['mae'])
        checks.append('both point baselines independently match saved labels and common support')
        full=statistics.fmean(x['full'] for x in computed.values());self_only=statistics.fmean(x['self-only'] for x in computed.values())
        close_enough(full,summary['mean_seed_full_pinball']);close_enough(self_only,summary['mean_seed_self_pinball'])
        agreeing=sum(x['full']<x['self-only'] for x in computed.values());assert agreeing==summary['improving_paired_seeds']
        assert summary['conditional_mechanism_advantage']==(full<self_only and agreeing>=2)
        checks.append('primary aggregation and registered 2-of-3 rule independently match')
        files.json('summary.json',{'status':'saved-result-independent-check-complete','checks':checks,'source_roots':pins,'computed_primary':computed,
                   'model_forward_calls':0,'optimizer_updates':0,'new_predictions':False,'actuals':'already freeze-gated scoring labels only',
                   'resources':check.check()});status='complete'
        print(json.dumps({'status':status,'checks':checks}))
    except BaseException:
        files.json('failure.json',{'traceback':traceback.format_exc()},True);raise
    finally:files.close(status)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--campaign',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();main(a.campaign,a.output)
