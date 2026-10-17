"""New temporal training diagnostic; completed outer evaluations are not replayed."""
import time
STARTED=time.monotonic()
from pathlib import Path
import argparse,csv,datetime as dt,io,json,math,random,sys,traceback
import torch
REPO=Path(__file__).resolve().parents[2];sys.path.insert(0,str(REPO/'tools'))
from verification_records import verify_record
from store_sales_final import private_memory
from demand_training_adequacy import split_keys,fit_scales,EarlyStopper
from demand_statistical_feature_model import StatisticalFeatureMean
from demand_statistical_feature_train import model_inputs,without_features
from demand_calendar_train import Files,pin,item,ACTIVE,ZERO
from demand_calendar_model import mean_loss
from demand_statistical_feature_validate import AsOfHistory
from demand_public_calendar import build_inputs,fit_support
from demand_statistical_features import encode_profile

SOURCES=['models/mini-transformer/demand_training_adequacy_train.py','tools/demand_training_adequacy.py',
 'tests/test_demand_training_adequacy.py','docs/research/demand-training-adequacy-design-2026-10-14.md',
 'models/mini-transformer/demand_statistical_feature_model.py','models/mini-transformer/demand_statistical_feature_train.py',
 'models/mini-transformer/demand_statistical_feature_validate.py','models/mini-transformer/demand_calendar_model.py',
 'models/mini-transformer/demand_calendar_train.py','tools/demand_public_calendar.py','tools/demand_statistical_features.py',
 'tools/demand_statistical_overlay.py','tools/demand_weekly_history.py','tools/verification_records.py','tools/store_sales_final.py']


def run(output):
    root=Path(output).absolute()
    if root.parent!=REPO/'artifacts' or root.exists():raise ValueError('fresh output root required')
    files=Files(root);status,stage,peak='failed','sources',0
    model=None;journal=[];curve=[];best_state=None
    def checkpoint():
        nonlocal peak
        peak=max(peak,private_memory())
        if peak>2*1024**3 or time.monotonic()-STARTED>870:raise RuntimeError('execution checkpoint; preserve and stop')
    try:
        sources={p:(REPO/p).read_bytes() for p in SOURCES}
        files.json('sources.json',{p:r.decode('utf-8') for p,r in sources.items()})
        files.json('config-before-input.json',{'fit_cutoff_exclusive':'2014-07-01','outer_years_used':False,
          'seed':20261014,'upper_steps':4096,'batch':8,'interval':128,'warmup':512,'patience':6,'min_relative':1e-4,
          'new_temporal_diagnostic':True,'not_extension_of_old_weights':True,'same_initial_sampler':True,
          'compute_parent_head':'04a423917beefe1a0257b29b8eed9648a1c099d0','uncommitted_new_source':True,
          'source_pins':{p:pin(r) for p,r in sources.items()},'python':sys.version,'torch':torch.__version__,'formal_permission':False})
        torch.set_num_threads(2);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True);checkpoint()
        pair=REPO/'artifacts/representative-demand-stat-feature-pair-20261014'
        closure_raw=(pair/'root-closed.json').read_bytes();closure=json.loads(closure_raw);assert closure['status']=='complete'
        keys_raw=(pair/'fit-keys.json').read_bytes();profile_raw=(pair/'fit-statistics.json').read_bytes()
        assert pin(keys_raw)==closure['files']['fit-keys.json'] and pin(profile_raw)==closure['files']['fit-statistics.json']
        keys=json.loads(keys_raw);split=split_keys(keys);assert len(split['train'])==450 and len(split['validation'])==180 and not split['crossing']
        profiles=json.loads(profile_raw);lookup={(r['store'],r['origin']):r['profile'] for r in profiles}
        assert len(lookup)==630 and set(lookup)==set(map(tuple,keys))
        prefix=REPO/'artifacts/representative-store-sales-shared-prefix-20261014-records';assert verify_record(prefix)['status']=='complete'
        snapshot=item(prefix,'selected-quantity-csv')
        assert pin(snapshot)=={'bytes':776915,'sha256':'b7805b258cb6e7a268b3b3289ac1b9688bd54cf03e1f06b01f8e74172fdeddc4'}
        raw_rows=list(csv.DictReader(io.StringIO(snapshot.decode())))
        scale_metadata=fit_scales(raw_rows,sorted(ACTIVE+ZERO));scales={int(s):r['scale'] for s,r in scale_metadata.items()}
        assert all(scales[s] is not None and scales[s]>0 for s in ACTIVE) and all(scales[s]==0 for s in ZERO)
        histories={s:{} for s in ACTIVE};masks={};selected=[]
        needed={d+dt.timedelta(days=k) for _,text in keys for d in [dt.date.fromisoformat(text)] for k in range(-56,14)}
        needed|={dt.date(2013,1,1)+dt.timedelta(days=k) for k in range((dt.date(2014,7,1)-dt.date(2013,1,1)).days)}
        for row in raw_rows:
            s,day=int(row['store_nbr']),dt.date.fromisoformat(row['date'])
            if s not in ACTIVE or day not in needed or day>=dt.date(2015,1,1):continue
            assert day not in histories[s] and row['observed'] in ('0','1') and (row['observed']=='1')==bool(row['sales'])
            histories[s][day]=float(row['sales']) if row['observed']=='1' else None;masks[s,day]=row['observed']=='1';selected.append(row)
        assert all(set(h)==needed for h in histories.values())
        support=fit_support([(s,dt.date.fromisoformat(text)) for s,text in split['train']],masks,dt.date(2014,7,1))
        stage='new-split-inputs';data={};declared=[]
        for name in ('train','validation'):
            inputs,encodings,labels=[],[],[]
            for s,text in split[name]:
                origin=dt.date.fromisoformat(text)
                past=AsOfHistory(histories[s],origin)
                x=build_inputs(past,origin,scales[s],'pre_post',support['enabled']);assert x['available']
                e=encode_profile(lookup[s,text],origin,scales[s])
                actual=[histories[s].get(origin+dt.timedelta(days=k)) for k in range(14)];assert all(v is not None for v in actual)
                inputs.append(x);encodings.append(e);labels.append(actual)
                declared.append({'split':name,'store':s,'origin':text,'scale':scales[s],'encoded':e,'actual':actual,
                  'profile_reused':True,'past_accessed_min':min(past.accessed),'past_accessed_max':max(past.accessed)})
            full=model_inputs(inputs,encodings)
            data[name]={'feature_on':full,'feature_off':without_features(full),'actual':torch.tensor(labels,dtype=torch.float32),
                        'mask':torch.ones((len(labels),14),dtype=torch.bool),'keys':split[name]}
        assert all(sum(s==store for s,text in split['train'])==30 and sum(s==store for s,text in split['validation'])==12 for store in ACTIVE)
        text=io.StringIO();writer=csv.DictWriter(text,['store_nbr','date','source_id','sales','observed']);writer.writeheader();writer.writerows(selected)
        files.write('selected-2013-14.csv',text.getvalue().encode())
        files.json('split-scale-and-support.json',{'split':split,'scale_metadata':scale_metadata,'support':support,
          'zero_scale_not_trained':list(ZERO),'validation_scale_payload_read':False,'profiles_recalculated':0})
        files.json('input-ledger.json',declared)
        files.json('binding.json',{'snapshot_pin':pin(snapshot),'prefix_closure':pin((prefix/'root-closed.json').read_bytes()),
          'keys_pin':pin(keys_raw),'profiles_pin':pin(profile_raw),'old_pair_closure':pin(closure_raw),
          'old_weights_read':False,'2015_2016_2017_numeric_read':False,'reserved_holdout_read':False})
        rng=random.Random(20261014);schedule=[[rng.randrange(450) for _ in range(8)] for _ in range(4096)]
        files.json('sampler.json',{'indices':schedule,'keys':split['train']})
        torch.manual_seed(20261014);initial_model=StatisticalFeatureMean()
        initial={k:v.detach().clone() for k,v in initial_model.state_dict().items()};files.state('initial.pt',initial);del initial_model
        results={}
        def fixed_metrics(model,mode,name):
            dataset=data[name];inputs=dataset[mode];scores={s:[] for s in ACTIVE}
            was_training=model.training;model.eval()
            with torch.no_grad():
                for start in range(0,len(dataset['keys']),8):
                    end=min(start+8,len(dataset['keys']));x=[v[start:end] for v in inputs]
                    daily,total=model(*x);actual=dataset['actual'][start:end];u=x[-2]
                    daily_scores=((daily-actual)/u[:,None]).square().mean(1)
                    total_scores=((total-actual.sum(1))/(14*u)).square()
                    for j,(s,text) in enumerate(dataset['keys'][start:end]):scores[s].append((daily_scores[j].item(),total_scores[j].item()))
                    checkpoint()
            model.train(was_training)
            per_store={str(s):{'daily':math.fsum(v[0] for v in values)/len(values),'total':math.fsum(v[1] for v in values)/len(values),'windows':len(values)} for s,values in scores.items()}
            daily=math.fsum(v['daily'] for v in per_store.values())/15;total=math.fsum(v['total'] for v in per_store.values())/15
            return {'joint':.5*(daily+total),'daily':daily,'total':total,'per_store':per_store}
        for mode in ('feature_off','feature_on'):
            stage='new-training-'+mode;model=StatisticalFeatureMean();model.load_state_dict(initial)
            assert all(torch.equal(v,initial[k]) for k,v in model.state_dict().items())
            optimizer=torch.optim.AdamW(model.parameters(),lr=3e-4,betas=(.9,.999),eps=1e-8,weight_decay=.01,foreach=False,fused=False)
            policy=EarlyStopper();journal=[];curve=[];best_state=None
            def observe(step):
                nonlocal best_state
                train=fixed_metrics(model,mode,'train');validation=fixed_metrics(model,mode,'validation')
                selection=policy.observe(step,validation['joint'])
                if selection['new_best']:best_state={k:v.detach().clone() for k,v in model.state_dict().items()}
                entry={'step':step,'train':train,'validation':validation,'selection':selection};curve.append(entry)
                print(json.dumps({'model':mode,'step':step,'train_joint':train['joint'],'validation_joint':validation['joint'],
                                  'best_step':selection['best_step'],'bad_checkpoints':selection['bad_checkpoints'],'stop':selection['stop']}),flush=True)
                return selection['stop']
            observe(0);model.train();stopping='step_cap'
            for step,indices in enumerate(schedule,1):
                dataset=data['train'];x=[v[indices] for v in dataset[mode]];optimizer.zero_grad(set_to_none=True)
                loss,parts=mean_loss(*model(*x),dataset['actual'][indices],dataset['mask'][indices],x[-2])
                if not bool(torch.isfinite(loss)):raise RuntimeError('nonfinite training loss')
                loss.backward();norm=torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True);optimizer.step()
                journal.append({'step':step,'loss':loss.item(),'norm':norm.item(),**parts});checkpoint()
                if step in (1024,2048):files.json(mode+'-prefix-'+str(step)+'.json',{'journal':journal,'curve':curve})
                if step%128==0 and observe(step):stopping='early_stop';break
            files.state(mode+'-final.pt',model.state_dict());files.state(mode+'-best.pt',best_state)
            files.json(mode+'-journal.json',journal);files.json(mode+'-curve.json',curve)
            at256=next(r for r in curve if r['step']==256)
            gain=100*(1-policy.best/at256['validation']['joint']) if at256['validation']['joint'] else None
            results[mode]={'steps':step,'stop_reason':stopping,'best_step':policy.best_step,'best_validation_joint':policy.best,
              'at256_validation_joint':at256['validation']['joint'],'at256_train_joint':at256['train']['joint'],
              'best_gain_vs256_percent':gain,'material_post256_improvement':policy.best_step>256 and gain is not None and gain>=.1,
              'final_train_joint':curve[-1]['train']['joint'],'final_validation_joint':curve[-1]['validation']['joint'],
              'initial_train_joint':curve[0]['train']['joint'],'initial_validation_joint':curve[0]['validation']['joint'],
              'selected_initial_baseline':policy.best_step==0,'convergence_certified':False,
              'curve_pin':files.pins[mode+'-curve.json'],'best_weight_pin':files.pins[mode+'-best.pt']}
        assert all((REPO/p).read_bytes()==raw for p,raw in sources.items());checkpoint()
        result={'status':'complete','research_state':'PAUSED','purpose':'internal training-budget diagnostic, no outer evaluation',
          'models':results,'train_windows':450,'validation_windows':180,'same_initial_and_sampler':True,
          'calendar_enabled_channels':sum(support['enabled']),'old_models_replayed':False,'old_profiles_recalculated':0,
          'source_pins':{p:pin(raw) for p,raw in sources.items()},'seconds':time.monotonic()-STARTED,'OS_peak_private_bytes':peak,
          'formal_permission':False,'adopted':False,'2015_2016_2017_reserved_holdout_read':False,'no_automatic_extension_or_grid':True}
        files.json('summary.json',result);status='complete'
        print(json.dumps(result),flush=True)
    except BaseException as error:
        original=traceback.format_exc()
        try:
            files.json('failure.json',{'stage':stage,'type':type(error).__name__,'message':str(error),'traceback':original,'research_state':'PAUSED'},True)
            files.json('failure-journal-curve.json',{'journal':journal,'curve':curve},True)
            if model is not None:files.state('failure-prefix.pt',model.state_dict(),True)
            if best_state is not None:files.state('failure-best.pt',best_state,True)
        except BaseException as save_error:print('failure save error: '+repr(save_error),file=sys.stderr)
        raise
    finally:files.json('root-closed.json',{'status':status,'files':files.pins.copy(),'immutable':True},status!='complete')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);run(parser.parse_args().output)
