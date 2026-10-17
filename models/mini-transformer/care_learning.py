"""One fixed CARE r1 fold, with training/selection/calibration/test role boundaries.

Authorized by the separate closed human phase record, never by frozen false
flags. No event truth is available here. Inference receives past-only tensors;
current temperatures enter scores only after their own availability.
"""
from io import BytesIO
import json
import math
from pathlib import Path
import platform
import sys
import time
import traceback
from metropt_multiday import ROOT,Files,digest,verify_closed
from care_input import Consumer,CONTRACT_SHA,INPUT_SHA,RECIPE_SHA,pinned_input
from care_training_preparation import FrozenPreparation,baseline_predict,DATA_CLOSURE_SHA
from care_alarm import *
sys.path.insert(0,str(ROOT/'tools'))
from macos_demand_runtime import MacCheckpoint


def source_paths():
    names=('care_learning.py','care_learning_slot.py','care_score.py','care_alarm.py','care_input.py','care_training_preparation.py','small_model.py','metropt_multiday.py')
    return [Path(__file__).with_name(n) for n in names]+[ROOT/'tools/macos_demand_runtime.py',ROOT/'tools/public-data/export_metropt_m1_learning_state.py']


def authorize(campaign,dataset,prepared):
    root=Path(campaign);verify_closed(root);permit=json.loads((root/'permit.json').read_bytes())
    if (permit.get('contract_sha256')!=CONTRACT_SHA or permit.get('explicit_human_execution') is not True
        or permit.get('phase')!='CARE-fixed-five-fold-train-calibrate-predict-score' or not permit.get('human_instruction')):
        raise PermissionError('closed human phase execution record required')
    declaration=json.loads((root/'campaign.json').read_bytes())
    if declaration['folds']!=[0,1,2,3,4] or declaration['updates_each']!=4096:raise ValueError('campaign budget changed')
    if digest(Path(dataset)/'root-closed.json')!=declaration['dataset_closure_sha256'] or declaration['dataset_closure_sha256']!=DATA_CLOSURE_SHA:raise ValueError('dataset pin')
    if digest(Path(prepared)/'root-closed.json')!=declaration['preparation_closure_sha256']:raise ValueError('preparation pin')
    for path,sha in declaration['source_pins'].items():
        if digest(ROOT/path)!=sha:raise ValueError('campaign source changed: '+path)
    return declaration


def save_state(files,name,model,optimizer,step,preparation,campaign,failure=False):
    import torch
    b=BytesIO();torch.save({'model':model.state_dict(),'optimizer':optimizer.state_dict(),'step':step,
        'torch_rng':torch.get_rng_state(),'schedule_sha256':preparation.schedule_sha256,'sampler_position':step*8,
        'contract_id':'CARE-A-MAINT-20261016-r1','contract_sha256':CONTRACT_SHA,'campaign_closure_sha256':digest(Path(campaign)/'root-closed.json'),
        'profile':preparation.profile},b)
    files.write(name,b.getvalue(),failure);return digest(files.root/name)


def neutral_state(files,state,selected_sha,check):
    sys.path.insert(0,str(ROOT/'tools/public-data'))
    from export_metropt_m1_learning_state import append_tensor
    model=state['model'];optimizer=state['optimizer'];groups=optimizer['param_groups'];buffers={'scale_floor','position','time_mask'}
    names=[n for n in model if n not in buffers]
    if len(groups)!=1 or len(names)!=len(groups[0]['params']) or sum(model[n].numel() for n in names)!=109024:raise ValueError('neutral parameter mapping')
    binary=bytearray();layout=[];mapping=[]
    for n,t in model.items():append_tensor(binary,layout,'model::'+n,t)
    for identifier,n in zip(groups[0]['params'],names,strict=True):
        fields=optimizer['state'][identifier];mapping.append({'optimizer_id':identifier,'name':n})
        for key,t in fields.items():
            if key not in ('step','exp_avg','exp_avg_sq'):raise ValueError('optimizer field')
            if key=='step' and t.item()!=state['step']:raise ValueError('optimizer step')
            if key!='step' and t.shape!=model[n].shape:raise ValueError('optimizer shape')
            if key=='exp_avg_sq' and not bool((t>=0).all()):raise ValueError('negative second moment')
            append_tensor(binary,layout,'adamw::'+n+'::'+key,t)
    append_tensor(binary,layout,'torch_rng_backend_specific',state['torch_rng'])
    files.write('selected-neutral.bin',bytes(binary));files.json('selected-neutral-layout.json',{'schema':'banto.care-learning-reference.v1','checkpoint_sha256':selected_sha,
        'step':state['step'],'sampler_position':state['sampler_position'],'schedule_sha256':state['schedule_sha256'],'tensors':layout,
        'optimizer_mapping':mapping,'optimizer_param_groups':groups,'buffers':sorted(buffers),'series_mask':'full 3x3 true, reconstruct; nonpersistent',
        'rng':'opaque PyTorch bytes, not a Rust RNG implementation','tensor_roundtrip_exact':True,'rust_training_resume_verified':False});check.check()


def pinball_origin(prediction,actual,T):
    losses=[]
    for v in range(3):
        for h in range(32):
            for j,tau in enumerate((.1,.5,.9)):
                residual=(actual[v][h]-prediction[v][h][j])/T[v]
                losses.append(max(tau*residual,(tau-1)*residual))
    return math.fsum(losses)/288


def validation(model,reader,origins,T,step,raw,check):
    import torch
    event=next(iter(reader.allowed));losses=[];model.eval()
    with torch.no_grad():
        for start in range(0,len(origins),8):
            ns=origins[start:start+8];examples=[reader.example(event,n) for n in ns]
            xs=torch.tensor([x.channels for x,y in examples],dtype=torch.float32);actual=[y for x,y in examples]
            predictions=model(xs).quantiles.tolist()
            for n,p,y in zip(ns,predictions,actual,strict=True):
                loss=pinball_origin(p,y,T)
                if not math.isfinite(loss):raise ValueError('nonfinite validation score')
                losses.append(loss);flat=[x for channel in y for x in channel]+[x for channel in p for lead in channel for x in lead]
                raw+=VALIDATION.pack(step,n,*flat)
            check.check()
    model.train();return math.fsum(losses)/len(losses)


def predict_rows(model,reader,event,origins,profile,check):
    """Issue all past-supported predictions before consulting each current value."""
    import torch
    d=reader.event(event);issued=[n for n in origins if d.past_ok(n,reader.role=='calibration')]
    prediction={};model.eval()
    with torch.no_grad():
        for start in range(0,len(issued),8):
            ns=issued[start:start+8]
            contexts=[reader.context(event,n,d._rows[n-1][0]+600) for n in ns]
            x=torch.tensor([c.channels for c in contexts],dtype=torch.float32)
            q=model(x).quantiles[:,:,0,:].tolist()
            prediction.update(zip(ns,q,strict=True));check.check()
    rows=[];R=[v['R64'] for v in profile['alarm_scales']];missing=math.nan
    for n in origins:
        row=d._rows[n];flags=0;nn=[missing]*2;b=[missing]*2;y=[missing]*2;q=[missing]*9;sn=sb=missing
        normal=reader.role=='calibration';common=d.common_ok(n,normal);native=d.native_ok(n) if not normal else common
        issue=d._rows[n-1][0]+600;available=row[0]+600
        if n in prediction:
            flags|=NEURAL_ISSUED;q=[v for ch in prediction[n] for v in ch];nn=[q[1],q[4]]
        if common:flags|=COMMON
        if native:flags|=NATIVE
        if d._rows[n-1][2]&4:
            flags|=BASELINE_ISSUED;b=list(baseline_predict(profile['baseline'],d._rows[n-1][5]))
        if row[2]&3==3:
            observed=d.observation(n,available);y=list(observed.values)
        if common:
            if n not in prediction or available<=issue:raise ValueError('common forecast/current timing')
            sn=max(abs(y[v]-nn[v])/R[v] for v in range(2))
        if native:sb=max(abs(y[v]-b[v])/R[v] for v in range(2))
        rows.append((event,n,row[1],issue,available,flags,*y,*nn,*b,sn,sb,*q))
    return rows


def run(dataset,prepared,campaign,fold,output,check):
    declaration=authorize(campaign,dataset,prepared);m=pinned_input();spec=m['folds'][fold]
    files=Files(output);status='failed';model=optimizer=preparation=None;step=0;best=None;journal=[];validation_raw=bytearray()
    try:
        files.sources(source_paths());files.json('phase.json',{'campaign_closure_sha256':digest(Path(campaign)/'root-closed.json'),'fold':fold,'execution_authorized_by':str(campaign),'source_pins':declaration['source_pins']})
        import torch
        from small_model import SmallForecaster,training_loss
        torch.set_num_threads(2);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
        preparation=FrozenPreparation(prepared,dataset,fold);profile=preparation.profile
        recipe=json.loads((ROOT/'artifacts/care-input-contract-20261016/learning.json').read_bytes())
        if digest(ROOT/recipe['model']['source'])!=recipe['model']['source_sha256']:raise ValueError('model source pin')
        files.json('input.json',{'dataset_closure_sha256':DATA_CLOSURE_SHA,'preparation_closure_sha256':digest(Path(prepared)/'root-closed.json'),
            'profile':profile,'schedule_sha256':preparation.schedule_sha256,'python':platform.python_version(),'torch':torch.__version__,'runtime':platform.platform()})
        floor=torch.tensor([s['context_floor32'] for s in profile['normalization']],dtype=torch.float32);T=[s['T32'] for s in profile['normalization']]
        torch.manual_seed(20261016);model=SmallForecaster(floor,series_attention='full')
        if sum(p.numel() for p in model.parameters())!=109024:raise ValueError('parameter count')
        raw=BytesIO();torch.save(model.state_dict(),raw);files.write('initial.pt',raw.getvalue())
        opts=recipe['training']['optimizer'];optimizer=torch.optim.AdamW(model.parameters(),lr=opts['lr'],betas=tuple(opts['betas']),eps=opts['eps'],weight_decay=opts['weight_decay'],foreach=False,fused=False)
        selection=Consumer(dataset,fold,'selection');ve=spec['validation_anchor_event'];selection_origins=selection.event(ve).origins('selection')
        if len(selection_origins)<256:raise ValueError('selection support')
        started=time.monotonic()
        for step0 in range(4096):
            xs,ys=preparation.batch(step0);x=torch.tensor(xs,dtype=torch.float32);y=torch.tensor(ys,dtype=torch.float32)
            optimizer.zero_grad(set_to_none=True);loss=training_loss(model(x),y)
            if not bool(torch.isfinite(loss)):raise ValueError('nonfinite training loss')
            loss.backward();norm=torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True);optimizer.step();step=step0+1
            if not all(bool(torch.isfinite(p).all()) for p in model.parameters()):raise ValueError('nonfinite updated parameter')
            journal.append({'step':step,'loss':loss.item(),'preclip_global_norm':norm.item()});check.check()
            if step in (512,1024,2048,4096):
                score=validation(model,selection,selection_origins,T,step,validation_raw,check);name=f'step-{step}.pt'
                sha=save_state(files,name,model,optimizer,step,preparation,campaign)
                candidate={'step':step,'validation_score':score,'checkpoint':name,'sha256':sha}
                if best is None or (score,step)<(best['validation_score'],best['step']):best=candidate
                journal.append({'validation':candidate});print(json.dumps({'fold':fold,'step':step,'selected':best}),flush=True)
        training_seconds=time.monotonic()-started
        files.write('validation.bin',validation_raw);files.json('validation-layout.json',{'format':'<II384f','record_bytes':VALIDATION.size,'columns':'checkpoint step, source ordinal uint32; actual3x32 then quantiles3x32x3 float32-le','records':4*len(selection_origins),'origins':selection_origins,'train_T32':T,'score':'float64 fsum pinball on native residual/T32, origins/targets/leads/quantiles equal'})
        files.json('selection.json',{'selected':best,'candidates':[r['validation'] for r in journal if 'validation' in r],'selection_origins':len(selection_origins),'tie_rule':'earlier step','updates_completed':step})
        files.json('journal.json',journal)
        if digest(files.root/best['checkpoint'])!=best['sha256']:raise ValueError('selected checkpoint changed')
        state=torch.load(files.root/best['checkpoint'],map_location='cpu',weights_only=True);model.load_state_dict(state['model']);model.eval();neutral_state(files,state,best['sha256'],check)
        # Checkpoint selection is frozen before the suffix is opened for calibration.
        calibration=Consumer(dataset,fold,'calibration');cal_ns=calibration.event(ve).origins('calibration')
        if len(cal_ns)<512:raise ValueError('calibration support')
        calibration_rows=predict_rows(model,calibration,ve,cal_ns,profile,check)
        files.write('calibration.bin',b''.join(PREDICTION.pack(*row) for row in calibration_rows))
        thresholds={name:calibration_threshold([r[12 if name=='neural' else 13] for r in calibration_rows]) for name in ('neural','baseline')}
        files.json('thresholds.json',{'methods':thresholds,'calibration_anchor':ve,'calibration_cut':calibration.event(ve).meta['validation_cut_ordinal'],'baseline_native_uses_same_baseline_threshold':True,'labels_used':False,'test_calibration':False})
        # Freeze thresholds/profile before opening test contexts/observations.
        test=Consumer(dataset,fold,'test');raw_test=bytearray();alarm={};counts={};inference_start=time.monotonic()
        for event in spec['test_events']:
            d=test.event(event);nt=d.meta['split_row_counts']['train'];ns=list(range(nt,d.meta['rows']))
            rows=predict_rows(model,test,event,ns,profile,check);raw_test+=b''.join(PREDICTION.pack(*r) for r in rows)
            alarm[str(event)]={method:episodes(rows,method,thresholds['neural' if method=='neural-common' else 'baseline']['threshold']) for method in METHODS}
            common=sum(bool(r[5]&COMMON) for r in rows);native=sum(bool(r[5]&NATIVE) for r in rows)
            if common/len(rows)<.7:raise ValueError('test support floor')
            counts[str(event)]={'prediction_rows':len(rows),'neural_issued':sum(bool(r[5]&NEURAL_ISSUED) for r in rows),'common':common,'native':native}
            test._cache.clear();check.check()
        files.write('test.bin',raw_test);files.json('episodes.json',alarm)
        files.json('prediction-layout.json',{'format':'<IIqqqB7x2d2d2d2d9f4x','record_bytes':144,'fields':'event, ordinal, source ID, issue offset, current availability offset, flags; actual2, neuralp50(2), baselinep50(2), score-neural/score-baseline float64; lead1 quantiles3x3 float32','flags':{'neural_past_only_issued':1,'common_eligible':2,'native_baseline_eligible':4,'baseline_lagged_power_issued':8},'invalid':'IEEE NaN, flag false; never model input','lead':'lead1 only in test/calibration, H32 in validation','clock':'file-local recorded offsets; row availability timestamp+600s'})
        files.json('summary.json',{'status':'fold-selected-calibrated-predictions-alarms-frozen-unscored','fold':fold,'updates':step,'selected':best,'selection_origins':len(selection_origins),'calibration_scores':len(calibration_rows),'test_support':counts,
            'training_and_selection_seconds':training_seconds,'test_seconds':time.monotonic()-inference_start,'event_truth_bytes_read':0,'performance_scored':False,'resources':check.check()})
        status='complete'
    except BaseException:
        failure={'traceback':traceback.format_exc(),'fold':fold,'step':step,'selected':best,'journal':journal}
        if model is not None and optimizer is not None and preparation is not None:
            try:save_state(files,'partial.pt',model,optimizer,step,preparation,campaign,True)
            except BaseException as error:failure['partial_state_failure']=repr(error)
        if validation_raw and not (files.root/'validation.bin').exists():files.write('partial-validation.bin',validation_raw,True)
        try:failure['resources']=check.check()
        except BaseException as error:failure['resource_observation_failure']=repr(error)
        files.json('failure.json',failure,True);raise
    finally:files.close(status)
