"""Explicit bounded same-initial pair; does not run on import."""
import time
STARTED=time.monotonic()
from pathlib import Path
import argparse,csv,io,json,hashlib,math,os,random,sys,traceback,platform
import torch
REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/'tools'))
from verification_records import verify_record
from store_sales_final import private_memory
from demand_public_calendar import build_inputs,matches,COLUMNS
from demand_calendar_model import CalendarSalesMean,mean_loss

ACTIVE=(6,7,9,10,13,14,15,17,18,19,23,25,26,27,30)
ZERO=(21,22,29)
STORES=tuple(sorted(ACTIVE+ZERO))
SOURCES=['models/mini-transformer/demand_calendar_model.py','models/mini-transformer/demand_calendar_train.py',
 'models/mini-transformer/check_demand_calendar_model.py','tools/demand_public_calendar.py',
 'tools/demand_weekly_history.py','tools/verification_records.py','tools/store_sales_final.py',
 'docs/research/demand-calendar-model-connection-design-2026-10-14.md']


def pin(raw):return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def item(root,label):
    manifest=verify_record(root)
    return b''.join((root/p['path']).read_bytes() for p in manifest['items'][label]['parts'])


class Files:
    def __init__(self,root):
        self.root=root;root.mkdir();self.pins={}
    def write(self,name,raw,failure=False):
        files=list(self.root.iterdir())
        if Path(name).name!=name or name in self.pins or (self.root/'root-closed.json').exists():raise ValueError('fresh output entry required')
        if any(not p.is_file() or p.is_symlink() for p in files):raise ValueError('unexpected output entry')
        maxfiles,maxbytes=(32,1024**3) if failure else (24,768*1024**2)
        if len(files)+1>maxfiles or len(raw)>32*1024**2 or sum(p.stat().st_size for p in files)+len(raw)>maxbytes:raise RuntimeError('output capacity checkpoint')
        with (self.root/name).open('xb') as f:
            if f.write(raw)!=len(raw):raise OSError('short output write')
            f.flush();os.fsync(f.fileno())
        self.pins[name]=pin(raw)
    def json(self,name,value,failure=False):self.write(name,json.dumps(value,allow_nan=False,sort_keys=True).encode(),failure)
    def state(self,name,state,failure=False):
        buffer=io.BytesIO();torch.save(state,buffer);self.write(name,buffer.getvalue(),failure)


def tensors(inputs):
    return [torch.tensor([x[field] for x in inputs],dtype=torch.bool if field=='observed' else torch.float32)
            for field in ('normalized_values','observed','past_calendar','future_calendar','context_statistics','baseline','scale')]


def control_inputs(full):
    result=[x.clone() for x in full]
    removed=[4+i for i,(_,offset) in enumerate(COLUMNS) if offset!=0]
    result[2][:,:,removed]=0;result[3][:,:,removed]=0
    return result


def error_metrics(errors,actuals,scales=None):
    n=len(errors);volume=math.fsum(actuals)
    return {'count':n,'scaled_MSE':math.fsum((e/u)**2 for e,u in zip(errors,scales))/n if n and scales is not None else None,
            'RMSE':math.sqrt(math.fsum(e*e for e in errors)/n) if n else None,
            'MAE':math.fsum(abs(e) for e in errors)/n if n else None,
            'WAPE_percent':100*math.fsum(abs(e) for e in errors)/volume if volume else None,
            'Bias_percent':100*math.fsum(errors)/volume if volume else None}


def run(output):
    root=Path(output).absolute()
    if root.parent!=REPO/'artifacts' or root.exists():raise ValueError('fresh local output root required')
    files=Files(root);status='failed';stage='source';journal=[];model=None;peak=0
    def checkpoint():
        nonlocal peak
        peak=max(peak,private_memory())
        if peak>2*1024**3 or time.monotonic()-STARTED>870:raise RuntimeError('execution checkpoint; preserve and stop')
    try:
        sources={p:(REPO/p).read_bytes() for p in SOURCES}
        files.json('sources.json',{p:r.decode('utf-8') for p,r in sources.items()})
        files.json('config.json',{'seed':20261014,'steps':256,'batch':8,'active':ACTIVE,'baseline_only':ZERO,
          'control':'on_day','candidate':'pre_post','same_initial_and_sampler':True,'selection':'final step256, no development selection',
          'cutoff':'2015-01-01','retrospective_development':2015,'formal_permission':False,
          'source_pins':{p:pin(r) for p,r in sources.items()},'uncommitted_new_sources':True,
          'compute_parent_head':'754842b789b202d39fa18a30041f4e64268b3a0f',
          'runtime':{'python':sys.version,'torch':torch.__version__,'platform':platform.platform()}})
        torch.set_num_threads(2);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
        checkpoint()
        prior=REPO/'artifacts/representative-demand-public-calendar-input-20261014-records'
        assert verify_record(prior)['status']=='failed'  # document TypeError, completed checks/support retained
        support_raw=item(prior,'fit-support');binding_raw=item(prior,'input-binding')
        support=json.loads(support_raw);binding=json.loads(binding_raw)
        assert sum(support['enabled'])==42 and binding['active']==list(ACTIVE)
        keys=[(s,__import__('datetime').date.fromisoformat(d)) for s,d in binding['fit_keys']]
        import datetime as dt
        dates=[dt.date.fromisoformat(d) for d in binding['development_dates']]
        assert len(keys)==630 and len(dates)==25
        scales={int(s):float(u) for s,u in binding['fit_scale_text'].items()}
        assert all(scales[s]>0 for s in ACTIVE) and all(scales[s]==0 for s in ZERO)
        snapshot=item(REPO/'artifacts/representative-store-sales-shared-prefix-20261014-records','selected-quantity-csv')
        assert pin(snapshot)==binding['snapshot_pin']
        files.json('binding.json',{'prior_closure':pin((prior/'root-closed.json').read_bytes()),'support_pin':pin(support_raw),
                   'binding_pin':pin(binding_raw),'snapshot_pin':pin(snapshot),'scales':scales,'development_dates':[str(d) for d in dates]})
        files.json('fit-keys.json',binding['fit_keys']);files.write('fit-support.json',support_raw)
        wanted={d+dt.timedelta(days=k) for s,d in keys for k in range(-56,14)}
        histories={s:{} for s in ACTIVE};selected=[];header=['store_nbr','date','source_id','sales','observed']
        for row in csv.DictReader(io.StringIO(snapshot.decode())):
            s=int(row['store_nbr']);day=dt.date.fromisoformat(row['date'])
            if s not in ACTIVE or day not in wanted or day>=dt.date(2015,1,1):continue
            assert row['observed'] in ('0','1') and (row['observed']=='1')==bool(row['sales']) and day not in histories[s]
            value=float(row['sales']) if row['observed']=='1' else None
            histories[s][day]=value;selected.append(row)
        assert all(set(h)==wanted for h in histories.values())
        text=io.StringIO();writer=csv.DictWriter(text,header);writer.writeheader();writer.writerows(selected);files.write('fit-selection.csv',text.getvalue().encode())
        inputs=[];labels=[];masks=[];stage='assemble-fit'
        for i,(s,day) in enumerate(keys):
            x=build_inputs(histories[s],day,scales[s],'pre_post',support['enabled']);assert x['available']
            values=[histories[s].get(day+dt.timedelta(days=k)) for k in range(14)]
            assert all(v is not None for v in values)
            inputs.append(x);labels.append(values);masks.append([True]*14)
            if i%32==0:checkpoint()
        full=tensors(inputs);del inputs
        control=control_inputs(full);y=torch.tensor(labels);mask=torch.tensor(masks,dtype=torch.bool)
        sampler=random.Random(20261014);schedule=[[sampler.randrange(len(keys)) for _ in range(8)] for _ in range(256)]
        files.json('sampler.json',{'indices':schedule,'fit_keys_pin':files.pins['fit-keys.json']})
        torch.manual_seed(20261014);initial_model=CalendarSalesMean()
        initial={k:v.detach().clone() for k,v in initial_model.state_dict().items()}
        files.state('initial.pt',initial);parameters=sum(p.numel() for p in initial_model.parameters());del initial_model
        trained={};final_loss={}
        for mode,data in (('on_day',control),('pre_post',full)):
            stage='train-'+mode;model=CalendarSalesMean();model.load_state_dict(initial)
            assert all(torch.equal(v,initial[k]) for k,v in model.state_dict().items())
            optimizer=torch.optim.AdamW(model.parameters(),lr=3e-4,betas=(.9,.999),eps=1e-8,weight_decay=.01,foreach=False,fused=False)
            journal=[];model.train()
            for step,indices in enumerate(schedule,1):
                x=[v[indices] for v in data];optimizer.zero_grad(set_to_none=True)
                loss,parts=mean_loss(*model(*x),y[indices],mask[indices],x[-1])
                if not bool(torch.isfinite(loss)):raise RuntimeError('nonfinite training loss')
                loss.backward();norm=torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True)
                optimizer.step();journal.append({'step':step,'loss':loss.item(),'norm':norm.item(),**parts});checkpoint()
                if step in (64,128,192):files.json(mode+'-prefix-'+str(step)+'.json',journal)
            files.state(mode+'-final.pt',model.state_dict());files.json(mode+'-journal.json',journal)
            final_loss[mode]=journal[-1]['loss'];model.eval();trained[mode]=model
            print(json.dumps({'mode':mode,'steps':256,'last_training_loss':final_loss[mode]}),flush=True)
        del full,control,y,mask,optimizer
        checkpoint();stage='development-after-both-weights'
        wanted={d+dt.timedelta(days=k) for d in dates for k in range(-56,14)}
        histories={s:{} for s in STORES};selected=[]
        for row in csv.DictReader(io.StringIO(snapshot.decode())):
            s=int(row['store_nbr']);day=dt.date.fromisoformat(row['date'])
            if s not in STORES or day not in wanted:continue
            assert day<dt.date(2016,1,1) and day not in histories[s]
            assert row['observed'] in ('0','1') and (row['observed']=='1')==bool(row['sales'])
            histories[s][day]=float(row['sales']) if row['observed']=='1' else None;selected.append(row)
        assert all(set(h)==wanted for h in histories.values())
        text=io.StringIO();writer=csv.DictWriter(text,header);writer.writeheader();writer.writerows(selected);files.write('development-selection.csv',text.getvalue().encode())
        rows=[];pending=[]
        for s in STORES:
            for origin in dates:
                x=build_inputs(histories[s],origin,scales[s],'pre_post',support['enabled'])
                baseline=x['baseline'];available=None not in baseline
                target=[histories[s].get(origin+dt.timedelta(days=k)) for k in range(14)]
                row={'store':s,'origin':str(origin),'scale':scales[s],'baseline':baseline if available else None,
                     'actual':target,'on_day':baseline if available else None,'pre_post':baseline if available else None,
                     'role':'positive_scale' if s in ACTIVE else 'zero_scale_baseline_only',
                     'model_available':x['available'],'input_reasons':x['reasons']}
                rows.append(row)
                if s in ACTIVE and x['available']:pending.append((len(rows)-1,x))
        with torch.no_grad():
            for start in range(0,len(pending),8):
                batch=pending[start:start+8];full=tensors([x for i,x in batch]);control=control_inputs(full)
                for mode,data in (('on_day',control),('pre_post',full)):
                    daily,total=trained[mode](*data)
                    for j,(index,x) in enumerate(batch):
                        values=daily[j].tolist();assert math.isclose(math.fsum(values),total[j].item(),rel_tol=1e-6,abs_tol=1e-5)
                        rows[index][mode]=values
                checkpoint()
        files.json('predictions.json',rows);stage='metrics'
        methods=('baseline','on_day','pre_post');by_store={};event_errors={s:{m:{} for m in methods} for s in ACTIVE}
        kind_errors={column:{m:{} for m in methods} for column in COLUMNS}
        for s in STORES:
            by_store[str(s)]={}
            for method in methods:
                daily_errors=[];daily_actual=[];tot_errors=[];tot_actual=[]
                for row in rows:
                    if row['store']!=s or row[method] is None:continue
                    origin=dt.date.fromisoformat(row['origin'])
                    for k,(p,a) in enumerate(zip(row[method],row['actual'])):
                        if a is None:continue
                        error=p-a;daily_errors.append(error);daily_actual.append(a);day=origin+dt.timedelta(days=k)
                        event_matches=matches(day)
                        if s in ACTIVE and event_matches:
                            event_errors[s][method].setdefault(str(day),[]).append((error/scales[s])**2)
                            for kind,offset,year in event_matches:
                                kind_errors[kind,offset][method].setdefault((s,str(day)),[]).append((error/scales[s])**2)
                    if all(a is not None for a in row['actual']):
                        tot_errors.append(math.fsum(row[method])-math.fsum(row['actual']));tot_actual.append(math.fsum(row['actual']))
                by_store[str(s)][method]={'daily':error_metrics(daily_errors,daily_actual,[scales[s]]*len(daily_errors) if scales[s]>0 else None),
                      'total':error_metrics(tot_errors,tot_actual,[14*scales[s]]*len(tot_errors) if scales[s]>0 else None)}
        event_store={str(s):{m:math.fsum(math.fsum(v)/len(v) for v in event_errors[s][m].values())/len(event_errors[s][m]) if event_errors[s][m] else None for m in methods} for s in ACTIVE}
        primary={m:math.fsum(event_store[str(s)][m] for s in ACTIVE)/len(ACTIVE) if all(event_store[str(s)][m] is not None for s in ACTIVE) else None for m in methods}
        secondary={scope:{m:math.fsum(by_store[str(s)][m][scope]['scaled_MSE'] for s in ACTIVE)/len(ACTIVE) for m in methods} for scope in ('daily','total')}
        improved=[s for s in ACTIVE if event_store[str(s)]['pre_post'] is not None and all(event_store[str(s)]['pre_post']<event_store[str(s)][m] for m in ('baseline','on_day'))]
        progress=all(v is not None for v in primary.values()) and all(primary['pre_post']<primary[m] for m in ('baseline','on_day')) and len(improved)>=10 and all(secondary[k]['pre_post']<=secondary[k][m] for k in ('daily','total') for m in ('baseline','on_day'))
        per_kind=[{'kind':kind,'offset':offset,'distinct_store_dates':len(kind_errors[kind,offset]['baseline']),
                  'methods':{m:math.fsum(math.fsum(v)/len(v) for v in kind_errors[kind,offset][m].values())/len(kind_errors[kind,offset][m]) if kind_errors[kind,offset][m] else None for m in methods}} for kind,offset in COLUMNS]
        groups={}
        for name,stores in (('all18',STORES),('positive15',ACTIVE),('zero_scale3',ZERO)):
            groups[name]={}
            for method in methods:
                de=[];da=[];te=[];ta=[]
                for row in rows:
                    if row['store'] not in stores or row[method] is None:continue
                    for p,a in zip(row[method],row['actual']):
                        if a is not None:de.append(p-a);da.append(a)
                    if all(a is not None for a in row['actual']):
                        te.append(math.fsum(row[method])-math.fsum(row['actual']));ta.append(math.fsum(row['actual']))
                groups[name][method]={'daily':error_metrics(de,da),'total':error_metrics(te,ta)}
        checkpoint();assert all((REPO/p).read_bytes()==r for p,r in sources.items())
        result={'status':'complete','progress_passed':bool(progress),'adopted':False,'parameters':parameters,
            'primary_event_macro_scaled_MSE':primary,'secondary_macro_scaled_MSE':secondary,'event_store_MSE':event_store,
            'improved_stores':improved,'per_store':by_store,'kind_offsets':per_kind,'groups':groups,'requested':len(rows),
            'model_supported':len(pending),'baseline_unavailable':sum(r['baseline'] is None for r in rows),
            'complete_label_windows':sum(all(a is not None for a in r['actual']) for r in rows),
            'zero_scale_baseline_only_windows':sum(r['store'] in ZERO for r in rows),
            'source_pins':{p:pin(r) for p,r in sources.items()},'initial_pin':files.pins['initial.pt'],
            'sampler_pin':files.pins['sampler.json'],'same_initial_sampler':True,'final_training_loss':final_loss,
            'seconds':time.monotonic()-STARTED,'OS_peak_private_bytes':peak,'formal_permission':False,
            'registered_holdout_read':False,'2016_2017_reserved_read':False,'retrospective_2015':True,
            'new_year_christmas_fit_support':False,'no_same_hypothesis_grid_on_failure':True}
        files.json('summary.json',result);status='complete'
        print(json.dumps({k:result[k] for k in ('status','progress_passed','primary_event_macro_scaled_MSE','secondary_macro_scaled_MSE','improved_stores','requested','model_supported','seconds','OS_peak_private_bytes')}),flush=True)
    except BaseException as error:
        original=traceback.format_exc()
        try:
            files.json('failure.json',{'stage':stage,'type':type(error).__name__,'message':str(error),'traceback':original},True)
            files.json('failure-journal.json',journal,True)
            if model is not None:files.state('failure-prefix.pt',model.state_dict(),True)
        except BaseException as save_error:
            print('failure save error: '+repr(save_error),file=sys.stderr)
        raise
    finally:
        files.json('root-closed.json',{'status':status,'files':files.pins.copy(),'immutable':True},status!='complete')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    run(parser.parse_args().output)
