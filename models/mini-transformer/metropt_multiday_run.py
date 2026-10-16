"""Explicit M1 seed unit. Import/M0 never trains. Requires a fresh phase permit.

This is a research scope interlock, not an authenticated security boundary.
Only this new Mac path is used; Windows train.py/check_model.py are not imported.
"""
from io import BytesIO
import json
from pathlib import Path
import platform
import sys
import time
import traceback

from metropt_multiday import ROOT, CONFIG, CONFIG_SHA, Files, Reader, baseline, baseline_selection, contract, digest, pinball_score
sys.path.insert(0,str(ROOT/'tools'))
from macos_demand_runtime import MacCheckpoint


def authorize(path,phase):
    permit=json.loads(Path(path).read_bytes())
    if (permit.get('plan_id')!='MPT-MAC-20261016-r2' or permit.get('config_sha256')!=CONFIG_SHA
            or permit.get('phase')!=phase or permit.get('explicit_human_resume') is not True
            or not isinstance(permit.get('human_instruction'),str) or not permit['human_instruction'].strip()):
        raise PermissionError('explicit human phase-resume record required; fixed config is not authorization')
    return permit


def save_state(files,name,model,optimizer,step,schedule_sha,*,failure=False):
    import torch
    raw=BytesIO()
    torch.save({'model':model.state_dict(),'optimizer':optimizer.state_dict(),'step':step,
                'torch_rng':torch.get_rng_state(),'schedule_sha256':schedule_sha,
                'sampler_position':step*8,'plan_id':'MPT-MAC-20261016-r2','config_sha256':CONFIG_SHA},raw)
    files.write(name,raw.getvalue(),failure)
    return digest(files.root/name)


def validation_score(model,reader,check):
    import torch
    preds=[];actual=[]
    model.eval()
    with torch.no_grad():
        for start in range(0,len(reader.keys),8):
            keys=reader.keys[start:start+8];x,y=reader.batch(keys)
            preds.extend(model(x).quantiles.tolist());actual.extend(y.tolist());check.check()
    model.train()
    return pinball_score(preds,actual,reader.keys,[s['T32'] for s in reader.stats])


def run(dataset,output,seed,permit_path):
    authorize(permit_path,'M1-train-predict')
    c=contract()
    if seed not in c['training']['init_seeds']:raise ValueError('unregistered seed')
    seed_index=c['training']['init_seeds'].index(seed)
    files=Files(output);check=MacCheckpoint(seconds=870);status='incomplete'
    models={};optimizers={};steps={name:0 for name in c['model']['variants']};journal=[];best={name:None for name in steps}
    schedule_sha=None
    try:
        import torch
        from small_model import SmallForecaster,training_loss
        torch.set_num_threads(2);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
        paths=[Path(__file__),Path(__file__).with_name('metropt_multiday.py'),Path(__file__).with_name('small_model.py'),
               Path(__file__).with_name('metropt_multiday_score.py'),Path(__file__).with_name('metropt_multiday_slot.py'),ROOT/'tools/macos_demand_runtime.py']
        source_pins={str(p.relative_to(ROOT)):digest(p) for p in paths}
        files.sources(paths);files.write('config.json',CONFIG.read_bytes())
        files.json('phase.json',{'permit':json.loads(Path(permit_path).read_bytes()),'permit_sha256':digest(permit_path),'seed':seed})
        train=Reader(dataset,'train');validation=Reader(dataset,'validation')
        files.json('input.json',{'dataset':str(Path(dataset).resolve()),'dataset_closure_sha256':digest(Path(dataset)/'root-closed.json'),
                   'config_sha256':CONFIG_SHA,'source_pins':source_pins,'seed':seed,'sampler_seed':c['training']['sampler_seeds'][seed_index],
                   'python':platform.python_version(),'torch':torch.__version__,'runtime':platform.platform()})
        schedule=train.schedule(c['training']['sampler_seeds'][seed_index]);files.json('schedule.json',schedule)
        schedule_sha=digest(files.root/'schedule.json')
        floor=torch.tensor([s['floor32'] for s in train.stats],dtype=torch.float32)
        torch.manual_seed(seed)
        full=SmallForecaster(floor,series_attention='full');control=SmallForecaster(floor,series_attention='self-only')
        control.load_state_dict(full.state_dict());models={'full':full,'self-only':control}
        initial=BytesIO();torch.save(full.state_dict(),initial);files.write('initial.pt',initial.getvalue())
        opts=c['training']['optimizer'];optimizers={name:torch.optim.AdamW(model.parameters(),lr=opts['lr'],betas=tuple(opts['betas']),
                    eps=opts['eps'],weight_decay=opts['weight_decay'],foreach=False,fused=False) for name,model in models.items()}
        for step,keys in enumerate(schedule,1):
            x,y=train.batch(keys)
            for name,model in models.items():
                optimizer=optimizers[name];optimizer.zero_grad(set_to_none=True)
                loss=training_loss(model(x),y)
                if not bool(torch.isfinite(loss)):raise ValueError('nonfinite training loss')
                loss.backward()
                norm=torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True)
                optimizer.step();steps[name]=step
                if not all(bool(torch.isfinite(p).all()) for p in model.parameters()):raise ValueError('nonfinite parameter after update')
                journal.append({'step':step,'variant':name,'loss':loss.item(),'preclip_global_norm':norm.item()});check.check()
            if step in c['selection']['steps']:
                for name,model in models.items():
                    score=validation_score(model,validation,check);path=name+'-step'+str(step)+'.pt'
                    state_sha=save_state(files,path,model,optimizers[name],step,schedule_sha)
                    candidate={'step':step,'validation_score':score,'path':path,'sha256':state_sha}
                    if best[name] is None or (score,step)<(best[name]['validation_score'],best[name]['step']):best[name]=candidate
                    journal.append({'step':step,'variant':name,'validation_score':score})
                print(json.dumps({'seed':seed,'common_steps':step,'selected':best}),flush=True)
        if set(steps.values())!={4096}:raise ValueError('common update budget incomplete')
        selected_baseline=baseline_selection(validation)
        files.json('selection.json',{'variants':best,'baselines':selected_baseline,'steps':steps})
        files.json('journal.json',journal)
        # No test quantities are exposed to fitting/selection. Open contexts only now.
        test=Reader(dataset,'test')
        baselines={mode:[] for mode in ('last-value','moving-average-15')}
        for key in test.keys:
            x=test.context(key)
            for mode in baselines:baselines[mode].append({'key':key,'prediction':baseline(x,mode)})
        files.json('test-baselines.json',baselines)
        inference_seconds={}
        for name,model in models.items():
            choice=best[name];path=files.root/choice['path']
            if digest(path)!=choice['sha256']:raise ValueError('selected state changed')
            state=torch.load(path,map_location='cpu',weights_only=True)
            model.load_state_dict(state['model']);model.eval();predictions=[];started=time.monotonic()
            with torch.no_grad():
                for start in range(0,len(test.keys),8):
                    keys=test.keys[start:start+8];x=test.batch(keys,labels=False)
                    pred=model(x).quantiles.tolist()
                    predictions.extend({'key':key,'prediction':row} for key,row in zip(keys,pred,strict=True));check.check()
            inference_seconds[name]=time.monotonic()-started
            files.json('test-'+name+'.json',{'seed':seed,'variant':name,'selected':choice,'rows':predictions,'targets_read':False})
        files.json('summary.json',{'status':'selected-and-predictions-frozen-unscored','seed':seed,'steps':steps,
                   'selected':best,'test_targets_read':False,'test_scores_computed':False,'inference_seconds':inference_seconds,
                   'resources':check.check(),'formal_permission':False})
        status='complete'
    except BaseException:
        failure={'traceback':traceback.format_exc(),'steps':steps,'selected':best,'journal':journal}
        for name,model in models.items():
            if name in optimizers and schedule_sha:
                try:save_state(files,'partial-'+name+'.pt',model,optimizers[name],steps[name],schedule_sha,failure=True)
                except BaseException as e:failure.setdefault('partial_state_failures',{})[name]=repr(e)
        try:failure['resources']=check.check()
        except BaseException as e:failure['resource_observation_failure']=repr(e)
        files.json('failure.json',failure,True);raise
    finally:files.close(status)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--dataset',required=True);p.add_argument('--output',required=True)
    p.add_argument('--seed',type=int,required=True);p.add_argument('--permit',required=True)
    a=p.parse_args();run(a.dataset,a.output,a.seed,a.permit)
