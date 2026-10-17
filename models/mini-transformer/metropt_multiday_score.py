"""M1 scorer: all 3 seed pairs must be closed/frozen before any test labels.

Never fits a model. Scope interlock is auditable, not an OS security sandbox.
"""
import json
import math
from pathlib import Path
import sys
import traceback

from metropt_multiday import ROOT, CONFIG, CONFIG_SHA, Files, Reader, contract, digest, mean, pinball_score, verify_closed
from metropt_multiday_run import authorize
sys.path.insert(0,str(ROOT/'tools'))
from macos_demand_runtime import MacCheckpoint


def finite_shape(value,shape):
    if not shape:
        if type(value) not in (int,float) or not math.isfinite(value):raise ValueError('nonfinite prediction')
    else:
        if not isinstance(value,list) or len(value)!=shape[0]:raise ValueError('prediction shape')
        for x in value:finite_shape(x,shape[1:])


def freeze_gate(roots,dataset,check):
    c=contract()
    if len(roots)!=3 or len({str(Path(p).resolve()) for p in roots})!=3:raise ValueError('exactly 3 distinct seed roots required')
    dataset_sha=digest(Path(dataset)/'root-closed.json')
    seeds={};common_sources=None;baselines=None;selection=None;freeze=[]
    expected_keys=[[day,n] for day in c['calendar']['selected_days']['test'] for n in range(128,1409,32)]
    for root in map(Path,roots):
        verify_closed(root)
        if digest(root/'config.json')!=CONFIG_SHA:raise ValueError('seed contract differs')
        info=json.loads((root/'input.json').read_bytes());summary=json.loads((root/'summary.json').read_bytes())
        seed=info['seed']
        if seed not in c['training']['init_seeds'] or seed in seeds:raise ValueError('seed identity duplicate/unregistered')
        if info['dataset_closure_sha256']!=dataset_sha:raise ValueError('seed dataset differs')
        if summary['status']!='selected-and-predictions-frozen-unscored' or summary['seed']!=seed:raise ValueError('seed incomplete')
        if summary['steps']!={'full':4096,'self-only':4096} or summary['test_scores_computed'] or summary['test_targets_read']:
            raise ValueError('budget/test isolation violated')
        if common_sources is None:common_sources=info['source_pins']
        if info['source_pins']!=common_sources:raise ValueError('different source between seed units')
        for name,sha in info['source_pins'].items():
            if digest(ROOT/name)!=sha:raise ValueError('source changed after predictions')
        selections=json.loads((root/'selection.json').read_bytes())
        if selections['steps']!=summary['steps'] or selections['variants']!=summary['selected']:raise ValueError('selection bookkeeping')
        if selection is None:selection=selections['baselines']
        if selections['baselines']!=selection:raise ValueError('baseline selected inconsistently')
        b=json.loads((root/'test-baselines.json').read_bytes())
        if baselines is None:baselines=b
        if b!=baselines:raise ValueError('baseline predictions differ by seed')
        for mode,rows in b.items():
            if mode not in ('last-value','moving-average-15') or [row['key'] for row in rows]!=expected_keys:raise ValueError('baseline support')
            for row in rows:finite_shape(row['prediction'],[3,32])
        if set(b)!= {'last-value','moving-average-15'}:raise ValueError('missing baseline')
        predictions={}
        for name in ('full','self-only'):
            p=json.loads((root/('test-'+name+'.json')).read_bytes())
            if p['seed']!=seed or p['variant']!=name or p['targets_read']:raise ValueError('prediction identity')
            if p['selected']!=selections['variants'][name] or p['selected']['step'] not in c['selection']['steps']:raise ValueError('prediction selected state')
            if digest(root/p['selected']['path'])!=p['selected']['sha256']:raise ValueError('selected state changed')
            if [row['key'] for row in p['rows']]!=expected_keys:raise ValueError('model support')
            for row in p['rows']:
                finite_shape(row['prediction'],[3,32,3])
                if any(q[0]>q[1] or q[1]>q[2] for target in row['prediction'] for q in target):raise ValueError('crossed quantiles')
            predictions[name]=p
        seeds[seed]={'root':str(root),'predictions':predictions,'summary':summary}
        freeze.append({'seed':seed,'root':str(root.resolve()),'closure_sha256':digest(root/'root-closed.json'),
                       'prediction_pins':{name:digest(root/name) for name in ('test-full.json','test-self-only.json','test-baselines.json')}})
        check.check()
    if set(seeds)!=set(c['training']['init_seeds']):raise ValueError('missing registered seed')
    return {'seed_units':seeds,'baselines':baselines,'baseline_selection':selection,'keys':expected_keys,
            'freeze':freeze,'dataset_closure_sha256':dataset_sha}


def describe(predictions,actual,keys,scales):
    by_day={day:[i for i,k in enumerate(keys) if k[0]==day] for day,_ in keys}
    result=[]
    for v in range(3):
        def aggregate(cell):
            return mean(mean(mean(cell(i,h) for h in range(32)) for i in rows) for rows in by_day.values())
        def error(i,h):return abs(actual[i][v][h]-predictions[i][v][h][1])
        def losses(i,h):
            return mean(max(tau*(actual[i][v][h]-predictions[i][v][h][j]),(tau-1)*(actual[i][v][h]-predictions[i][v][h][j]))
                        for j,tau in enumerate((.1,.5,.9)))
        native_pinball=aggregate(losses)
        result.append({'mae':aggregate(error),'pinball':native_pinball,'wis':2*native_pinball,
                       'coverage80':aggregate(lambda i,h:float(predictions[i][v][h][0]<=actual[i][v][h]<=predictions[i][v][h][2])),
                       'width80':aggregate(lambda i,h:predictions[i][v][h][2]-predictions[i][v][h][0]),
                       'lower_miss_rate':aggregate(lambda i,h:float(actual[i][v][h]<predictions[i][v][h][0])),
                       'upper_miss_rate':aggregate(lambda i,h:float(actual[i][v][h]>predictions[i][v][h][2])),
                       'lead_mae':[mean(mean(error(i,h) for i in rows) for rows in by_day.values()) for h in range(32)],
                       'daily':{day:{'mae':mean(mean(error(i,h) for h in range(32)) for i in rows),
                                    'pinball':mean(mean(losses(i,h) for h in range(32)) for i in rows)} for day,rows in by_day.items()}})
    score=pinball_score(predictions,actual,keys,scales)
    return {'fixed_scale_pinball':score,'fixed_scale_wis':2*score,'targets':result}


def main(dataset,roots,output,permit):
    authorize(permit,'M1-score')
    files=Files(output);check=MacCheckpoint(seconds=870);status='incomplete'
    try:
        files.sources([Path(__file__),Path(__file__).with_name('metropt_multiday.py'),Path(__file__).with_name('metropt_multiday_run.py'),ROOT/'tools/macos_demand_runtime.py'])
        files.write('config.json',CONFIG.read_bytes())
        files.json('phase.json',{'permit':json.loads(Path(permit).read_bytes()),'permit_sha256':digest(permit)})
        verified=freeze_gate(roots,dataset,check)
        # Closure and every seed prediction pinned before the first test target read.
        files.json('freeze.json',{'units':verified['freeze'],'dataset_closure_sha256':verified['dataset_closure_sha256'],
                   'test_target_reads_before_this_record':0})
        reader=Reader(dataset,'test')
        if [list(k) for k in reader.keys]!=verified['keys']:raise ValueError('prepared test support changed')
        actual=[reader._slice(key,key[1],key[1]+32) for key in reader.keys]
        files.json('evaluation-labels.json',{'keys':verified['keys'],'actual':actual,'freeze_sha256':digest(files.root/'freeze.json')})
        scales=[s['T32'] for s in reader.stats];results={}
        for seed in sorted(verified['seed_units']):
            unit=verified['seed_units'][seed];results[str(seed)]={}
            for name,p in unit['predictions'].items():
                results[str(seed)][name]=describe([row['prediction'] for row in p['rows']],actual,reader.keys,scales);check.check()
        baseline_results={}
        for mode,rows in verified['baselines'].items():
            points=[row['prediction'] for row in rows]
            # Repeated quantiles used only to reuse point-MAE aggregation; do not report synthetic baseline WIS.
            repeated=[[[[x,x,x] for x in target] for target in row] for row in points]
            metrics=describe(repeated,actual,reader.keys,scales)
            baseline_results[mode]=[{'mae':t['mae'],'lead_mae':t['lead_mae'],'daily_mae':{d:m['mae'] for d,m in t['daily'].items()}} for t in metrics['targets']]
        seed_ids=[str(s) for s in sorted(verified['seed_units'])]
        full_mean=mean(results[s]['full']['fixed_scale_pinball'] for s in seed_ids)
        self_mean=mean(results[s]['self-only']['fixed_scale_pinball'] for s in seed_ids)
        agreeing=sum(results[s]['full']['fixed_scale_pinball']<results[s]['self-only']['fixed_scale_pinball'] for s in seed_ids)
        comparisons=[]
        for v,mode in enumerate(verified['baseline_selection']['selected_per_target']):
            base=baseline_results[mode][v]['mae'];model_mean=mean(results[s]['full']['targets'][v]['mae'] for s in seed_ids)
            n=sum(results[s]['full']['targets'][v]['mae']<base for s in seed_ids)
            comparisons.append({'target':reader.config['targets'][v]['name'],'baseline':mode,'baseline_mae':base,'mean_seed_full_mae':model_mean,
                                'difference':model_mean-base,'ratio':model_mean/base if base!=0 else None,'improving_seeds':n,
                                'conditional_exploratory_advantage':model_mean<base and n>=2})
        files.json('metrics.json',{'seeds':results,'point_baselines':baseline_results,'baseline_selection':verified['baseline_selection']})
        files.json('summary.json',{'status':'exploratory-comparison-complete','mean_seed_full_pinball':full_mean,'mean_seed_self_pinball':self_mean,
                   'difference':full_mean-self_mean,'ratio':full_mean/self_mean if self_mean!=0 else None,'improving_paired_seeds':agreeing,
                   'conditional_mechanism_advantage':full_mean<self_mean and agreeing>=2,'point_comparisons':comparisons,
                   'statistical_significance_claim':False,'product_adoption':False,'support':len(reader.keys),'resources':check.check()})
        status='complete'
    except BaseException:
        failure={'traceback':traceback.format_exc()}
        try:failure['resources']=check.check()
        except BaseException as e:failure['resource_observation_failure']=repr(e)
        files.json('failure.json',failure,True);raise
    finally:files.close(status)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--dataset',required=True);p.add_argument('--units',nargs=3,required=True)
    p.add_argument('--output',required=True);p.add_argument('--permit',required=True)
    a=p.parse_args();main(a.dataset,a.units,a.output,a.permit)
