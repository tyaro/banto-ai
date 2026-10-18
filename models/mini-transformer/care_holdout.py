"""CARE Farm B/C one-shot holdout (CARE-BC-HOLDOUT-20261018): input, preparation and fold units.

The recipe, floors and alarm rule are those of CARE-A-MAINT-20261016-r1; only the farm, the three
signals, the split and the number of train assets change. No event truth is read here: the event
information is opened only by tools/care_holdout.py score, after every fold is frozen.
"""
import base64
from collections import Counter
import json
import math
import os
from pathlib import Path
import platform
import resource
import struct
import time
import zipfile
from metropt_multiday import ROOT,Files,digest,verify_closed
from care_input import Consumer,EventData,no_truth
from care_training_preparation import (BATCH,SAMPLER_SEED,SCHEDULE_RECORD,UPDATES,baseline_profile,encode_origins,
                                       normal_rows,normalization,schedule)

CONTRACT=ROOT/'examples/configs/care-holdout-bc-20261018.json'
CONTRACT_SHA='22b4dfc8e3bd3dc18807701682e1a81ca0e145b27b5a49167d8611d250fb31bc'
INVENTORY=ROOT/'artifacts/care-metadata-inventory-20261016/file-inventory.json'
ARCHIVE=ROOT/'artifacts/care-zenodo-v6-holdout-20261018/CARE_To_Compare.zip'
RECIPE=ROOT/'artifacts/care-input-contract-20261016/learning.json'
RECIPE_SHA='b238248f4b5055311f562bb099f26c446448d2c1e4b113fd453fd86825f566f3'
WORK=ROOT/'artifacts/care-holdout-20261018'
FARMS=('B','C')
TRUTH_PATHS=('event_info','care-evaluator-contract-','care-label-metadata-','label-manifest.json','care-holdout-scores-')


def contract():
    if digest(CONTRACT)!=CONTRACT_SHA:raise ValueError('holdout contract changed')
    return json.loads(CONTRACT.read_bytes())


def inventory():
    c=contract()
    if digest(INVENTORY)!=c['known_before_opening']['structural_inventory_sha256']:raise ValueError('structural inventory changed')
    return json.loads(INVENTORY.read_bytes())


def check_farm(farm):
    if farm not in FARMS:raise ValueError('unregistered farm')


def feature_order(farm):
    check_farm(farm);return [s['column'] for s in contract()['signals'][farm]]


def asset_key(farm,asset):return f'{farm}:{asset}'


def folds(farm):
    """The fixed split, recomputed from the structural inventory and required to equal the contract."""
    check_farm(farm);files=[f for f in inventory() if f['farm']==farm]
    assets=sorted({f['asset_id'] for f in files},key=int)
    anchors={a:min(f['event_id'] for f in files if f['asset_id']==a) for a in assets};result=[]
    for i,a in enumerate(assets):
        v=assets[(i+1)%len(assets)];train=[x for x in assets if x not in (a,v)]
        result.append({'fold':i,'test_asset':a,'validation_asset':v,'train_assets':train,'train_anchor_events':[anchors[x] for x in train],
                       'validation_anchor_event':anchors[v],'test_events':sorted(f['event_id'] for f in files if f['asset_id']==a)})
    fixed=contract()['split'][farm]
    if result!=fixed['folds'] or assets!=fixed['assets'] or {k:int(v) for k,v in fixed['anchors'].items()}!=anchors:raise ValueError('split differs from the contract')
    return result


def manifest(farm):
    """Structural metadata of every fixed file, in the A input-manifest form (no event truth)."""
    anchors={f['validation_anchor_event'] for f in folds(farm)};keys=('farm','event_id','member','member_sha256','asset_id','rows','split_row_counts','split_transitions')
    files=[]
    for f in sorted((f for f in inventory() if f['farm']==farm),key=lambda f:f['event_id']):
        item={k:f[k] for k in keys};item['anchor']=f['event_id'] in anchors
        if item['anchor']:item['validation_cut_ordinal']=7*f['split_row_counts']['train']//10
        files.append(item)
    m={'contract_id':contract()['id'],'contract_sha256':CONTRACT_SHA,'farm':farm,'model_feature_order':feature_order(farm),'files':files,'folds':folds(farm)}
    no_truth(m);return m


class HoldoutFiles(Files):
    """Flat writer with room for the larger B/C cohorts: 128 files, 1 GiB, single file 32 MiB."""
    def write(self,name,raw,failure=False):
        if self.closed or Path(name).name!=name or (self.root/name).exists():raise ValueError('closed/reused/unsafe output')
        files=list(self.root.iterdir())
        if any(not p.is_file() or p.is_symlink() for p in files):raise ValueError('invalid output entry')
        if len(files)+1>128 or len(raw)>32*1024**2 or sum(p.stat().st_size for p in files)+len(raw)>1024**3:raise RuntimeError('artifact budget exceeded')
        with (self.root/name).open('xb') as f:
            if f.write(raw)!=len(raw):raise OSError('short write')


class Checkpoint:
    """Linux wall-clock and peak-RSS checkpoints (sampled, not an OS hard cap)."""
    def __init__(self,seconds=870,memory_bytes=2*1024**3):
        self.started=time.monotonic();self.seconds=seconds;self.memory_bytes=memory_bytes

    def check(self):
        elapsed=time.monotonic()-self.started;peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        if elapsed>self.seconds or peak>self.memory_bytes:raise RuntimeError('resource checkpoint exceeded; preserve evidence')
        return {'elapsed_seconds':elapsed,'peak_rss_bytes':peak,'peak_source':'Linux getrusage(RUSAGE_SELF).ru_maxrss','limits':{'wall_seconds':self.seconds,'peak_rss_bytes':self.memory_bytes},'hard_os_limit':False}


def runtime():
    """The pinned runtime; any difference stops before training."""
    import importlib.util
    import torch
    pin=contract()['runtime'];lib=Path(torch.__file__).parent/'lib/libtorch_cpu.so'
    record={'python':'CPython '+platform.python_version(),'torch':torch.__version__,'torch_git_version':torch.version.git_version,
            'libtorch_cpu_sha256':digest(lib),'numpy':'not installed' if importlib.util.find_spec('numpy') is None else 'installed',
            'platform':platform.platform(),'machine':platform.machine(),'glibc':'-'.join(platform.libc_ver())}
    wanted={k:pin[k] for k in ('python','torch','torch_git_version','libtorch_cpu_sha256','numpy')}
    if platform.python_implementation()!='CPython' or {k:record[k] for k in wanted}!=wanted or record['machine']!='x86_64' or record['glibc']!='glibc-2.39':
        raise RuntimeError('runtime differs from the contract pins: '+json.dumps(record))
    threads=pin['threads'];torch.set_num_threads(threads['torch.set_num_threads']);torch.set_num_interop_threads(threads['torch.set_num_interop_threads'])
    torch.use_deterministic_algorithms(threads['torch.use_deterministic_algorithms'])
    record['threads']={'num_threads':torch.get_num_threads(),'interop_threads':torch.get_num_interop_threads(),'deterministic':torch.are_deterministic_algorithms_enabled()}
    if record['threads']!={'num_threads':2,'interop_threads':1,'deterministic':True}:raise RuntimeError('thread settings')
    return record


# Input: one closed root per event, plus a closed manifest root binding them.

def event_root(farm,event):return WORK/'input'/farm/f'event-{event}'


def manifest_root(farm):return WORK/'input'/farm/'manifest'


def prepare_event(farm,event,check):
    """Decode the three fixed Avg fields of one member; event_info.csv is never opened."""
    import sys
    sys.path.insert(0,str(ROOT/'tools/public-data'))
    from care_numeric_prepare import convert
    m=manifest(farm);item=next(f for f in m['files'] if f['event_id']==event)
    out=HoldoutFiles(event_root(farm,event));state='failed';probes=[]
    try:
        with zipfile.ZipFile(ARCHIVE) as z:
            if item['member'] not in z.namelist() or 'event_info' in item['member']:raise ValueError('unexpected member')
            raw,first,bits,counts,n=convert(z,item,m['model_feature_order'],check,probes)
        name=f'event-{event}.bin';out.write(name,bytes(raw))
        meta={**item,'binary':f'event-{event}/{name}','binary_sha256':digest(out.root/name),'first_timestamp':first.isoformat(),'record_bytes':32}
        if bits is not None:meta['offline_prefix_status0_bits_base64']=base64.b64encode(bits).decode()
        out.json('meta.json',meta);out.json('quality.json',{'event_id':event,'rows':n+1,'channels':[dict(c) for c in counts],'probes':probes,'resources':check.check()})
        state='complete'
    finally:out.close(state)


def assemble(farm):
    """Bind the per-event roots once all of them are closed and complete."""
    m=manifest(farm);out=HoldoutFiles(manifest_root(farm));state='failed'
    try:
        files=[];quality=[]
        for item in m['files']:
            root=event_root(farm,item['event_id']);verify_closed(root);meta=json.loads((root/'meta.json').read_bytes())
            if {k:meta[k] for k in item}!=item:raise ValueError('event metadata differs from the fixed manifest')
            files.append({**meta,'event_root_closure_sha256':digest(root/'root-closed.json')})
            q=json.loads((root/'quality.json').read_bytes());quality.append({'event_id':item['event_id'],'rows':q['rows'],'channels':q['channels']})
        no_truth(files)
        out.json('dataset-manifest.json',{'schema':'banto.care-holdout-input.v1','contract_id':m['contract_id'],'contract_sha256':CONTRACT_SHA,'farm':farm,
            'source_sha256':contract()['source']['sha256'],'model_feature_order':m['model_feature_order'],'folds':m['folds'],'files':files,
            'license':'CC-BY-SA-4.0; CARE to Compare authors, https://doi.org/10.5281/zenodo.15846963',
            'changes':f'Farm {farm}: three fixed Avg fields as float32 + finite mask, file-local offsets; no imputation or unit conversion',
            'layout':'<qqB3xfff, 32 bytes, canonical missing f32 bits 0x7fc00000','status_bitset':'anchor train-prefix status 0 only; offline, never model input'})
        out.json('quality.json',{'files':quality,'truth_access':False});state='complete'
    finally:out.close(state)


class HoldoutConsumer(Consumer):
    """The A role boundary (fit/selection/calibration/test) on a fixed B/C fold."""
    def __init__(self,farm,fold,role):
        check_farm(farm);root=manifest_root(farm);verify_closed(root)
        m=json.loads((root/'dataset-manifest.json').read_bytes());no_truth(m);expected=manifest(farm)
        if m['contract_sha256']!=CONTRACT_SHA or m['model_feature_order']!=expected['model_feature_order'] or m['folds']!=expected['folds']:raise ValueError('holdout input pin')
        if [f['event_id'] for f in m['files']]!=[f['event_id'] for f in expected['files']]:raise ValueError('cohort changed')
        for f,item in zip(m['files'],expected['files'],strict=True):
            if {k:f[k] for k in item}!=item or f['binary']!=f"event-{item['event_id']}/event-{item['event_id']}.bin":raise ValueError('event metadata/path')
        if type(fold) is not int or not 0<=fold<len(m['folds']):raise ValueError('invalid fold')
        self.root=WORK/'input'/farm;self.manifest=m;self.fold=m['folds'][fold];self.role=role;self.farm=farm
        if role=='fit':self.allowed=set(self.fold['train_anchor_events'])
        elif role in ('selection','calibration'):self.allowed={self.fold['validation_anchor_event']}
        elif role=='test':self.allowed=set(self.fold['test_events'])
        else:raise ValueError('unknown consumer role')
        for f in m['files']:
            if f['event_id'] in self.allowed:
                r=event_root(farm,f['event_id']);verify_closed(r)
                if digest(r/'root-closed.json')!=f['event_root_closure_sha256'] or digest(self.root/f['binary'])!=f['binary_sha256']:raise ValueError('event root pin')
        self._cache={}


# Train-only preparation: profiles, schedules and origin indices for every fold of one farm.

def prep_root(farm):return WORK/'prep'/farm


def prepare_profiles(farm,check):
    m=manifest(farm);out=HoldoutFiles(prep_root(farm));state='failed';populations={};pairs={};origins={};counts={}
    try:
        for fold in m['folds']:
            for event in fold['train_anchor_events']:
                if event in origins:continue
                d=HoldoutConsumer(farm,fold['fold'],'fit').event(event);ns=normal_rows(d);fit=d.origins('fit')
                if len(fit)<4096 or not ns:raise ValueError(f'train support: event {event} has {len(fit)} fit origins')
                populations[event]=[tuple(d._rows[i][3:6]) for i in ns];pairs[event]=[(d._rows[n-1][5],tuple(d._rows[n][3:5])) for n in fit]
                origins[event]=fit;counts[event]={'all3_finite_status0_bins_once':len(ns),'fit_origins_pairs':len(fit),'train_prefix_rows':d.meta['split_row_counts']['train'],'asset_id':d.meta['asset_id']}
                out.write(f'anchor-{event}-origins.bin',encode_origins(fit));check.check()
        summary=[]
        for fold in m['folds']:
            k=fold['fold'];es=fold['train_anchor_events'];train=list(zip(fold['train_assets'],es,strict=True))
            scales,alarm=normalization([populations[e] for e in es]);baseline=baseline_profile([pairs[e] for e in es]);raw,draws=schedule(train,origins)
            profile={'schema':'banto.care-training-profile.v1','contract_id':m['contract_id'],'farm':farm,'fold':k,'train_assets':fold['train_assets'],
                'train_anchor_events':es,'validation_asset':fold['validation_asset'],'test_asset':fold['test_asset'],
                'normalization_population':[{'event_id':e,**counts[e]} for e in es],'normalization':scales,'alarm_scales':alarm,'baseline':baseline,
                'schedule':{'format':'<III asset/event/origin uint32-le','records':UPDATES*BATCH,'batch':BATCH,'updates':UPDATES,'sampler_seed':SAMPLER_SEED,'draw_counts_by_train_asset':draws},
                'profiles_fit_from_train_only':True,'neural_training':False,'thresholds_not_fitted':True}
            no_truth(profile);out.json(f'fold-{k}-profile.json',profile)
            if not baseline['support_passed']:raise ValueError(f'fold {k}: nonempty baseline bin below the fixed 128 floor')
            out.write(f'fold-{k}-schedule.bin',raw)
            summary.append({'fold':k,'profile_sha256':digest(out.root/f'fold-{k}-profile.json'),'schedule_sha256':digest(out.root/f'fold-{k}-schedule.bin'),'baseline_pair_counts':baseline['pair_counts']});check.check()
        out.json('manifest.json',{'schema':'banto.care-holdout-preparation.v1','contract_sha256':CONTRACT_SHA,'farm':farm,'input_closure_sha256':digest(manifest_root(farm)/'root-closed.json'),
            'folds':summary,'origins':[{'event_id':e,'count':len(xs),'sha256':digest(out.root/f'anchor-{e}-origins.bin')} for e,xs in sorted(origins.items())],
            'population_counts':{str(e):c for e,c in sorted(counts.items())},'resources':check.check()})
        state='complete'
    finally:out.close(state)


class HoldoutPreparation:
    """Frozen fold profile and schedule; the same checks as FrozenPreparation."""
    def __init__(self,farm,fold):
        root=prep_root(farm);verify_closed(root);pm=json.loads((root/'manifest.json').read_bytes());no_truth(pm)
        if pm['contract_sha256']!=CONTRACT_SHA or pm['input_closure_sha256']!=digest(manifest_root(farm)/'root-closed.json'):raise ValueError('preparation pin')
        self.profile=json.loads((root/f'fold-{fold}-profile.json').read_bytes());no_truth(self.profile);declared=pm['folds'][fold]
        if self.profile['fold']!=fold or not self.profile['baseline']['support_passed']:raise ValueError('fold profile unsupported')
        if digest(root/f'fold-{fold}-profile.json')!=declared['profile_sha256'] or digest(root/f'fold-{fold}-schedule.bin')!=declared['schedule_sha256']:raise ValueError('profile/schedule pin')
        self.reader=HoldoutConsumer(farm,fold,'fit');spec=self.reader.fold
        if self.profile['train_assets']!=spec['train_assets'] or self.profile['train_anchor_events']!=spec['train_anchor_events']:raise ValueError('profile train cohort differs')
        self._schedule=(root/f'fold-{fold}-schedule.bin').read_bytes()
        if len(self._schedule)!=UPDATES*BATCH*SCHEDULE_RECORD.size:raise ValueError('schedule length')
        allowed={}
        for event in spec['train_anchor_events']:
            declared_index=next(v for v in pm['origins'] if v['event_id']==event);raw=(root/f'anchor-{event}-origins.bin').read_bytes()
            if digest(root/f'anchor-{event}-origins.bin')!=declared_index['sha256']:raise ValueError('origin population pin')
            xs=[n[0] for n in struct.iter_unpack('<I',raw)]
            if xs!=self.reader.event(event).origins('fit'):raise ValueError('origin population differs from the consumer')
            allowed[event]=set(xs)
        assets=dict(zip(spec['train_anchor_events'],spec['train_assets'],strict=True))
        for asset,event,n in SCHEDULE_RECORD.iter_unpack(self._schedule):
            if event not in assets or str(asset)!=assets[event] or n not in allowed[event]:raise ValueError('batch index outside the fit population')
        self.schedule_sha256=digest(root/f'fold-{fold}-schedule.bin')

    def batch(self,step):
        start=step*BATCH*SCHEDULE_RECORD.size;xs=[];ys=[]
        for asset,event,n in SCHEDULE_RECORD.iter_unpack(self._schedule[start:start+BATCH*SCHEDULE_RECORD.size]):
            context,target=self.reader.example(event,n);xs.append(context.channels);ys.append(target)
        return tuple(xs),tuple(ys)


# One fold: train, select, calibrate, predict and alarm (care_learning.run without the A pins).

def unit_root(farm,fold):return WORK/'units'/f'{farm}-fold-{fold}'


def run_fold(farm,fold,check):
    from io import BytesIO
    from care_learning import predict_rows,validation
    from care_alarm import COMMON,METHODS,NATIVE,NEURAL_ISSUED,PREDICTION,VALIDATION,calibration_threshold,episodes
    files=Files(unit_root(farm,fold));status='failed';step=0;best=None;journal=[];validation_raw=bytearray()
    try:
        names=('care_holdout.py','care_learning.py','care_alarm.py','care_input.py','care_training_preparation.py','small_model.py','metropt_multiday.py')
        files.sources([Path(__file__).with_name(n) for n in names]+[ROOT/'tools/care_holdout.py',ROOT/'tools/public-data/care_numeric_prepare.py'])
        record=runtime();files.json('runtime.json',record)
        import torch
        from small_model import SmallForecaster,training_loss
        recipe=json.loads(RECIPE.read_bytes())
        if digest(RECIPE)!=RECIPE_SHA or digest(ROOT/recipe['model']['source'])!=recipe['model']['source_sha256']:raise ValueError('recipe/model source pin')
        preparation=HoldoutPreparation(farm,fold);profile=preparation.profile;spec=preparation.reader.fold
        files.json('input.json',{'contract_sha256':CONTRACT_SHA,'farm':farm,'fold':fold,'input_closure_sha256':digest(manifest_root(farm)/'root-closed.json'),
            'preparation_closure_sha256':digest(prep_root(farm)/'root-closed.json'),'profile':profile,'schedule_sha256':preparation.schedule_sha256})
        floor=torch.tensor([s['context_floor32'] for s in profile['normalization']],dtype=torch.float32);T=[s['T32'] for s in profile['normalization']]
        torch.manual_seed(recipe['training']['init_seed_each_fold']);model=SmallForecaster(floor,series_attention='full')
        if sum(p.numel() for p in model.parameters())!=109024:raise ValueError('parameter count')
        raw=BytesIO();torch.save(model.state_dict(),raw);files.write('initial.pt',raw.getvalue())
        opts=recipe['training']['optimizer'];optimizer=torch.optim.AdamW(model.parameters(),lr=opts['lr'],betas=tuple(opts['betas']),eps=opts['eps'],weight_decay=opts['weight_decay'],foreach=False,fused=False)
        selection=HoldoutConsumer(farm,fold,'selection');ve=spec['validation_anchor_event'];selection_origins=selection.event(ve).origins('selection')
        if len(selection_origins)<256:raise ValueError('selection support')
        started=time.monotonic()
        for step0 in range(UPDATES):
            xs,ys=preparation.batch(step0);x=torch.tensor(xs,dtype=torch.float32);y=torch.tensor(ys,dtype=torch.float32)
            optimizer.zero_grad(set_to_none=True);loss=training_loss(model(x),y)
            if not bool(torch.isfinite(loss)):raise ValueError('nonfinite training loss')
            loss.backward();norm=torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True);optimizer.step();step=step0+1
            if not all(bool(torch.isfinite(p).all()) for p in model.parameters()):raise ValueError('nonfinite updated parameter')
            journal.append({'step':step,'loss':loss.item(),'preclip_global_norm':norm.item()})
            if step%64==0:check.check()
            if step in (512,1024,2048,4096):
                score=validation(model,selection,selection_origins,T,step,validation_raw,check);name=f'step-{step}.pt';b=BytesIO()
                torch.save({'model':model.state_dict(),'optimizer':optimizer.state_dict(),'step':step,'torch_rng':torch.get_rng_state(),'schedule_sha256':preparation.schedule_sha256,
                            'sampler_position':step*BATCH,'contract_id':contract()['id'],'contract_sha256':CONTRACT_SHA,'farm':farm,'fold':fold,'profile':profile},b)
                files.write(name,b.getvalue());candidate={'step':step,'validation_score':score,'checkpoint':name,'sha256':digest(files.root/name)}
                if best is None or (score,step)<(best['validation_score'],best['step']):best=candidate
                journal.append({'validation':candidate})
        training_seconds=time.monotonic()-started
        files.write('validation.bin',validation_raw);files.json('validation-layout.json',{'format':'<II384f','record_bytes':VALIDATION.size,'origins':selection_origins,'train_T32':T})
        files.json('selection.json',{'selected':best,'candidates':[r['validation'] for r in journal if 'validation' in r],'selection_origins':len(selection_origins),'tie_rule':'earlier step','updates_completed':step})
        files.json('journal.json',journal)
        state=torch.load(files.root/best['checkpoint'],map_location='cpu',weights_only=True);model.load_state_dict(state['model']);model.eval()
        # Checkpoint selection is frozen before the calibration suffix is opened.
        calibration=HoldoutConsumer(farm,fold,'calibration');cal_ns=calibration.event(ve).origins('calibration')
        if len(cal_ns)<512:raise ValueError('calibration support')
        calibration_rows=predict_rows(model,calibration,ve,cal_ns,profile,check)
        files.write('calibration.bin',b''.join(PREDICTION.pack(*r) for r in calibration_rows))
        thresholds={name:calibration_threshold([r[12 if name=='neural' else 13] for r in calibration_rows]) for name in ('neural','baseline')}
        files.json('thresholds.json',{'methods':thresholds,'calibration_anchor':ve,'calibration_cut':calibration.event(ve).meta['validation_cut_ordinal'],'labels_used':False})
        # Thresholds are frozen before any test context or observation is opened.
        test=HoldoutConsumer(farm,fold,'test');raw_test=bytearray();alarm={};counts={};inference_start=time.monotonic()
        for event in spec['test_events']:
            d=test.event(event);nt=d.meta['split_row_counts']['train'];rows=predict_rows(model,test,event,list(range(nt,d.meta['rows'])),profile,check)
            raw_test+=b''.join(PREDICTION.pack(*r) for r in rows)
            alarm[str(event)]={method:episodes(rows,method,thresholds['neural' if method=='neural-common' else 'baseline']['threshold']) for method in METHODS}
            common=sum(bool(r[5]&COMMON) for r in rows)
            counts[str(event)]={'prediction_rows':len(rows),'neural_issued':sum(bool(r[5]&NEURAL_ISSUED) for r in rows),'common':common,'native':sum(bool(r[5]&NATIVE) for r in rows)}
            if common/len(rows)<.7:raise ValueError(f'test support floor: event {event} common {common}/{len(rows)}')
            test._cache.clear();check.check()
        files.write('test.bin',raw_test);files.json('episodes.json',alarm)
        files.json('summary.json',{'status':'fold-selected-calibrated-predictions-alarms-frozen-unscored','farm':farm,'fold':fold,'updates':step,'selected':best,
            'selection_origins':len(selection_origins),'calibration_scores':len(calibration_rows),'test_support':counts,'training_and_selection_seconds':training_seconds,
            'test_seconds':time.monotonic()-inference_start,'event_truth_bytes_read':0,'performance_scored':False,'resources':check.check()})
        status='complete'
    except BaseException:
        import traceback
        failure={'traceback':traceback.format_exc(),'farm':farm,'fold':fold,'step':step,'selected':best}
        try:failure['resources']=check.check()
        except BaseException as error:failure['resource_error']=repr(error)
        files.json('failure.json',failure,True);raise
    finally:files.close(status)


def unit_complete(farm,fold):
    root=unit_root(farm,fold)
    try:verify_closed(root)
    except (FileNotFoundError,ValueError,KeyError):return False
    s=json.loads((root/'summary.json').read_bytes())
    return s['farm']==farm and s['fold']==fold and s['updates']==UPDATES and s['performance_scored'] is False
