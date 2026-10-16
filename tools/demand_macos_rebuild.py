"""One fresh CPU demand trajectory from the downloaded ZIP; no legacy replay."""
import time
STARTED = time.monotonic()
import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import traceback
import zipfile

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'models/mini-transformer'))
from demand_group_selection import FIT, GROUP_C, POSITIVE, cohort_split, DualSelector, progress
from demand_public_calendar import build_inputs, fit_support
from demand_statistical_features import encode_profile
from demand_statistical_overlay import describe_history
from demand_weekly_history import build_inputs as weekly_inputs
from macos_demand_runtime import MacCheckpoint

EVAL = (4, 8, 16, 20, 24, 28)
ACTIVE_EVAL = (4, 8, 16, 24, 28)
BEGIN, SCALE_END = dt.date(2013, 1, 1), dt.date(2014, 7, 1)
CONTRACT = 'docs/research/demand-macos-rebuild-design-2026-10-15.md'
ZIP_SHA = '12e9c1dc4833cc804b3ff1515bd7b688f45fd8216fb2b340525036b006d625be'


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


class PastOnly:
    def __init__(self, history, origin):
        self.history, self.origin = history, origin
    def get(self, day):
        if not self.origin - dt.timedelta(days=56) <= day < self.origin:
            raise ValueError('input getter outside completed 56-day context')
        return self.history.get(day)


def select_row(row, phase):
    # Scope metadata is tested BEFORE converting or using the sales payload.
    stores = set(map(str, POSITIVE + EVAL)) if phase == 'internal' else set(map(str, EVAL))
    if row['family'] != 'BREAD/BAKERY' or row['store_nbr'] not in stores:
        return None
    text = row['date']
    store = int(row['store_nbr'])
    if phase == 'internal':
        end = '2015-01-01' if store in POSITIVE else '2014-07-01'
        if not '2013-01-01' <= text < end:
            return None
    elif phase == 'development':
        if not '2014-11-18' <= text <= '2015-12-28':
            return None
    else:
        raise ValueError('unknown extraction phase')
    day, value = dt.date.fromisoformat(text), float(row['sales'])
    if not math.isfinite(value) or value < 0:
        raise ValueError('nonnegative finite selected quantity required')
    return store, day, value


class HashedReader(io.RawIOBase):
    def __init__(self, raw):
        self.raw, self.digest, self.byte_count = raw, hashlib.sha256(), 0
    def readable(self): return True
    def readinto(self, buffer):
        raw = self.raw.read(len(buffer))
        buffer[:len(raw)] = raw
        self.digest.update(raw)
        self.byte_count += len(raw)
        return len(raw)


def extract(archive, phase, checkpoint):
    stores = POSITIVE + EVAL if phase == 'internal' else EVAL
    histories = {s: {} for s in stores}
    before = archive.stat()
    count = 0
    with zipfile.ZipFile(archive) as zipped, zipped.open('train.csv') as member:
        hashed = HashedReader(member)
        with io.TextIOWrapper(io.BufferedReader(hashed), encoding='utf-8', newline='') as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != ['id', 'date', 'store_nbr', 'family', 'sales', 'onpromotion']:
                raise ValueError('unexpected train schema')
            for row in reader:
                count += 1
                selected = select_row(row, phase)
                if selected is not None:
                    s, day, value = selected
                    if day in histories[s]: raise ValueError('duplicate selected store/date')
                    if histories[s] and day <= next(reversed(histories[s])):
                        raise ValueError('unordered selected series')
                    histories[s][day] = value
                if count % 100000 == 0: checkpoint()
    after = archive.stat()
    stamp = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
    if stamp(before) != stamp(after) or count != 3000888:
        raise ValueError('archive identity or train row count changed')
    return histories, {'name': 'train.csv', 'rows': count, 'bytes': hashed.byte_count,
                       'sha256': hashed.digest.hexdigest(), 'phase': phase,
                       'quantity_selection_before_conversion': True,
                       'promotion_numeric_read': False, '2016_2017_reserved_numeric_read': False}


def scales(histories):
    result = {}
    days = [BEGIN + dt.timedelta(days=k) for k in range((SCALE_END-BEGIN).days)]
    for store, history in histories.items():
        kept = [history[d] for d in days if d in history]
        if not kept: raise ValueError('missing scale observations')
        result[store] = {'scale': math.fsum(kept)/len(kept), 'observed_days': len(kept),
                         'calendar_days': len(days), 'cutoff_exclusive': str(SCALE_END)}
    return result


def snapshot(histories, first, last):
    output = io.StringIO(newline='')
    writer = csv.writer(output, lineterminator='\n')
    writer.writerow(['store_nbr', 'date', 'sales', 'observed'])
    for store, history in sorted(histories.items()):
        for k in range((last-first).days+1):
            day = first+dt.timedelta(days=k)
            value = history.get(day)
            writer.writerow([store, str(day), '' if value is None else value, int(value is not None)])
    return output.getvalue().encode()


def internal_keys(histories, scale):
    candidates = [dt.date(2013, 2, 26)+dt.timedelta(days=14*k) for k in range(48)]
    accepted, rejected = [], []
    for s in POSITIVE:
        for day in candidates:
            past = PastOnly(histories[s], day)
            supported = weekly_inputs(past, day, scale[s])
            complete = all(histories[s].get(day+dt.timedelta(days=k)) is not None for k in range(14))
            if supported['available'] and complete: accepted.append((s, str(day)))
            else: rejected.append({'store': s, 'origin': str(day), 'input_reasons': supported['reasons'],
                                   'complete_label': complete})
    return cohort_split(accepted), rejected


def eval_metrics(rows, u, method):
    daily, total, de, da, te, ta = [], [], [], [], [], []
    for row in rows:
        if row[method] is None: continue
        for prediction, actual in zip(row[method], row['actual']):
            if actual is not None:
                error = prediction-actual
                de.append(error); da.append(actual)
                if u: daily.append((error/u)**2)
        if row['complete_label']:
            error = math.fsum(row[method])-math.fsum(row['actual'])
            te.append(error); ta.append(math.fsum(row['actual']))
            if u: total.append((error/(14*u))**2)
    mean = lambda xs: math.fsum(xs)/len(xs) if xs else None
    return {'daily': mean(daily), 'total': mean(total),
            'joint': .5*(mean(daily)+mean(total)) if daily and total else None,
            'observed_daily_labels': len(de), 'complete_total_labels': len(te),
            'daily_MAE': mean([abs(e) for e in de]), 'total_MAE': mean([abs(e) for e in te]),
            'daily_bias': mean(de), 'total_bias': mean(te),
            'daily_WAPE_percent': 100*math.fsum(abs(e) for e in de)/math.fsum(da) if math.fsum(da) else None,
            'total_WAPE_percent': 100*math.fsum(abs(e) for e in te)/math.fsum(ta) if math.fsum(ta) else None}


def run(output, archive):
    import torch
    from demand_statistical_feature_model import StatisticalFeatureMean
    from demand_calendar_model import mean_loss
    from demand_calendar_train import Files
    root = output.absolute()
    if root.parent != REPO/'artifacts' or root.exists(): raise ValueError('fresh artifact root required')
    files = Files(root)
    guard = MacCheckpoint(seconds=870)
    status, stage, journal, curve, rows = 'failed', 'source', [], [], []
    model = None
    try:
        checkpoint = guard.check
        if sys.version_info[:3] != (3,14,8) or torch.__version__ != '2.14.0':
            raise ValueError('fixed Python/Torch runtime required')
        source_paths = [CONTRACT, 'tools/demand_macos_rebuild.py', 'tools/macos_demand_runtime.py',
                        'tools/demand_group_selection.py', 'tools/demand_training_adequacy.py',
                        'tools/demand_public_calendar.py', 'tools/demand_statistical_features.py',
                        'tools/demand_statistical_overlay.py', 'tools/demand_weekly_history.py',
                        'models/mini-transformer/demand_statistical_feature_model.py',
                        'models/mini-transformer/demand_calendar_model.py',
                        'models/mini-transformer/demand_calendar_train.py']
        sources = {p: (REPO/p).read_bytes() for p in source_paths}
        files.write('contract.md', sources[CONTRACT])
        files.json('sources.json', {p: raw.decode() for p,raw in sources.items()})
        raw_zip = archive.read_bytes()
        archive_pin = pin(raw_zip); del raw_zip
        if archive_pin != {'bytes':22416355,'sha256':ZIP_SHA}: raise ValueError('fixed ZIP pin mismatch')
        files.json('config-before-input.json', {'archive':archive_pin, 'seed':20261014,
            'upper_steps':4096,'batch':8,'source_pins':{p:pin(raw) for p,raw in sources.items()},
            'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
            'python':sys.version,'torch':torch.__version__,'device':'cpu','dtype':'float32',
            'new_generation':True,'old_weights_loaded':False,'formal_permission':False})
        torch.set_num_threads(2); torch.set_num_interop_threads(1)
        torch.use_deterministic_algorithms(True); checkpoint()
        stage = 'internal-source-extraction'
        histories, member_pin = extract(archive, 'internal', checkpoint)
        scale_meta = scales(histories); scale = {s:m['scale'] for s,m in scale_meta.items()}
        if not all(scale[s]>0 for s in POSITIVE+ACTIVE_EVAL) or scale[20] != 0:
            raise ValueError('fixed scale roles not met')
        files.json('source-manifest.json', {'archive':archive_pin,'archive_path':str(archive),
                                          'train_member':member_pin,'old_source_manifest_recreated':False})
        files.write('selected-internal.csv', snapshot(histories, BEGIN, dt.date(2014,12,31)))
        files.json('scale-metadata.json', {str(s):v for s,v in scale_meta.items()})
        groups, excluded = internal_keys(histories,scale)
        masks = {(s,d):v is not None for s,h in histories.items() for d,v in h.items()}
        # Missing dates need explicit False masks for the reviewed calendar helper.
        for s,h in histories.items():
            for k in range(730): masks[s,BEGIN+dt.timedelta(days=k)] = BEGIN+dt.timedelta(days=k) in h
        support = fit_support([(s,dt.date.fromisoformat(d)) for s,d in groups['fit']], masks, SCALE_END)
        files.json('split-support.json', {'groups':groups,'excluded':excluded,'support':support})
        stage = 'new-profiles-and-inputs'
        data, ledger = {}, []
        def tensors(inputs, encoded):
            fields = ('normalized_values','observed','past_calendar','future_calendar',
                      'context_statistics','baseline','scale')
            return [torch.tensor([x[f] for x in inputs],dtype=torch.bool if f=='observed' else torch.float32)
                    for f in fields]+[torch.tensor([e['features'] for e in encoded],dtype=torch.float32)]
        for name in ('fit','time_validation','transfer_validation'):
            inputs,encoded,labels = [],[],[]
            for s,text in groups[name]:
                origin = dt.date.fromisoformat(text); past = PastOnly(histories[s],origin)
                x = build_inputs(past,origin,scale[s],'pre_post',support['enabled'])
                profile = describe_history(past,origin); e = encode_profile(profile,origin,scale[s])
                actual = [histories[s].get(origin+dt.timedelta(days=k)) for k in range(14)]
                if not x['available'] or any(v is None for v in actual): raise ValueError('internal support drift')
                inputs.append(x);encoded.append(e);labels.append(actual)
                ledger.append({'split':name,'store':s,'origin':text,'profile':profile,'encoded':e,'actual':actual})
                checkpoint()
            data[name] = {'keys':groups[name],'inputs':tensors(inputs,encoded),
                          'actual':torch.tensor(labels,dtype=torch.float32)}
        files.json('internal-profiles.json',ledger)
        rng = random.Random(20261014)
        sampler = [[rng.randrange(300) for _ in range(8)] for _ in range(4096)]
        files.json('sampler.json', {'indices':sampler,'fit_keys':groups['fit']})
        torch.manual_seed(20261014); model = StatisticalFeatureMean()
        if sum(p.numel() for p in model.parameters()) != 30369: raise ValueError('model shape changed')
        files.state('initial.pt',model.state_dict())
        optimizer = torch.optim.AdamW(model.parameters(),lr=3e-4,betas=(.9,.999),eps=1e-8,
                                      weight_decay=.01,foreach=False,fused=False)
        selector, best = DualSelector(), {}
        def fixed_metrics(name):
            dataset = data[name]; by_store = {s:[] for s,_ in dataset['keys']}
            was_training = model.training; model.eval()
            with torch.no_grad():
                for start in range(0,len(dataset['keys']),8):
                    end = min(start+8,len(dataset['keys']))
                    x = [v[start:end] for v in dataset['inputs']]; actual = dataset['actual'][start:end]
                    daily,total = model(*x); u = x[-2]
                    ds = ((daily-actual)/u[:,None]).square().mean(1)
                    ts = ((total-actual.sum(1))/(14*u)).square()
                    for j,(s,_) in enumerate(dataset['keys'][start:end]): by_store[s].append((ds[j].item(),ts[j].item()))
                    checkpoint()
            model.train(was_training)
            per_store = {str(s):{'daily':math.fsum(d for d,t in v)/len(v),
                                 'total':math.fsum(t for d,t in v)/len(v)} for s,v in by_store.items()}
            daily = math.fsum(v['daily'] for v in per_store.values())/len(per_store)
            total = math.fsum(v['total'] for v in per_store.values())/len(per_store)
            return {'daily':daily,'total':total,'joint':.5*(daily+total),'per_store':per_store}
        def observe(step):
            measured = {name:fixed_metrics(name) for name in data}
            chosen = selector.observe(step,measured['time_validation']['joint'],measured['transfer_validation']['joint'])
            for name,flag in (('time_selected','time_new_best'),('transfer_selected','transfer_new_best')):
                if chosen[flag]: best[name] = {k:v.detach().clone() for k,v in model.state_dict().items()}
            curve.append({'step':step,**measured,'selection':chosen})
            print(json.dumps({'step':step,'transfer_validation':measured['transfer_validation']['joint'],**chosen}),flush=True)
            return chosen['stop']
        stage = 'one-training-trajectory'; observe(0); model.train(); stop = 'step_cap'
        for step,indices in enumerate(sampler,1):
            x = [v[indices] for v in data['fit']['inputs']]; actual = data['fit']['actual'][indices]
            optimizer.zero_grad(set_to_none=True)
            loss,parts = mean_loss(*model(*x),actual,torch.ones_like(actual,dtype=torch.bool),x[-2])
            if not bool(torch.isfinite(loss)): raise ValueError('nonfinite loss')
            loss.backward(); norm = torch.nn.utils.clip_grad_norm_(model.parameters(),1.,error_if_nonfinite=True)
            optimizer.step();journal.append({'step':step,'loss':loss.item(),'norm':norm.item(),**parts});checkpoint()
            if step%128 == 0 and observe(step): stop='transfer_early_stop';break
        files.state('final.pt',model.state_dict())
        for name,state in best.items(): files.state(name+'.pt',state)
        files.json('training-journal.json',journal);files.json('selection-curve.json',curve)
        same = all(torch.equal(best['time_selected'][k],best['transfer_selected'][k]) for k in best['time_selected'])
        selection = {'steps':step,'stop':stop,'time_best_step':selector.time_best_step,
                     'transfer_best_step':selector.transfer.best_step,'same_state':same,
                     'weight_pins':{name:files.pins[name+'.pt'] for name in best},
                     'development_quantity_interpreted':False,'no_further_weight_selection':True}
        files.json('frozen-selections-before-development.json',selection)
        del histories,data,ledger,optimizer
        stage = 'development-source-extraction'
        histories, dev_member = extract(archive,'development',checkpoint)
        if {k:member_pin[k] for k in ('bytes','rows','sha256')} != {k:dev_member[k] for k in ('bytes','rows','sha256')}:
            raise ValueError('train member changed between stages')
        files.write('selected-development.csv',snapshot(histories,dt.date(2014,11,18),dt.date(2015,12,28)))
        pending,profiles = [],[]
        for s in EVAL:
            for k in range(25):
                origin = dt.date(2015,1,13)+dt.timedelta(days=14*k); past = PastOnly(histories[s],origin)
                x = build_inputs(past,origin,scale[s],'pre_post',support['enabled'])
                profile = describe_history(past,origin); e = encode_profile(profile,origin,scale[s])
                baseline = x['baseline'] if None not in x['baseline'] else None
                rows.append({'store':s,'origin':str(origin),'scale':scale[s],'baseline':baseline,
                             'time_selected':baseline if s==20 else None,'transfer_selected':baseline if s==20 else None,
                             'model_available':x['available'],'input_reasons':x['reasons']})
                profiles.append({'store':s,'origin':str(origin),'profile':profile,'encoded':e})
                if s in ACTIVE_EVAL and x['available']: pending.append((len(rows)-1,x,e))
                checkpoint()
        files.json('development-profiles.json',profiles)
        stage = 'frozen-development-forward'
        unique = ('time_selected',) if same else ('time_selected','transfer_selected')
        models = {}
        for name in unique:
            clone = StatisticalFeatureMean();clone.load_state_dict(best[name],strict=True);clone.eval();models[name]=clone
        with torch.no_grad():
            for start in range(0,len(pending),8):
                batch = pending[start:start+8]; x = tensors([r[1] for r in batch],[r[2] for r in batch])
                for name,clone in models.items():
                    daily,total = clone(*x)
                    for j,(index,_,_) in enumerate(batch):
                        values = daily[j].tolist()
                        if not math.isclose(math.fsum(values),total[j].item(),rel_tol=1e-6,abs_tol=1e-5):
                            raise ValueError('daily/total inconsistency')
                        rows[index][name] = values
                        if same: rows[index]['transfer_selected']=values.copy()
                checkpoint()
        files.json('predictions-before-labels.json',rows)
        for row in rows:
            origin = dt.date.fromisoformat(row['origin'])
            row['actual'] = [histories[row['store']].get(origin+dt.timedelta(days=k)) for k in range(14)]
            row['complete_label'] = all(v is not None for v in row['actual'])
        files.json('predictions-and-labels.json',rows)
        stage = 'fixed-development-metrics'
        methods = ('baseline','time_selected','transfer_selected')
        by_store = {str(s):{m:eval_metrics([r for r in rows if r['store']==s],scale[s],m) for m in methods} for s in EVAL}
        support_counts = {str(s):{'requested':25,'neural':sum(r['store']==s and r['model_available'] for r in rows),
                                 'complete_labels':sum(r['store']==s and r['complete_label'] for r in rows)} for s in EVAL}
        if not all(support_counts[str(s)]['neural']==25 and support_counts[str(s)]['complete_labels']==24 for s in ACTIVE_EVAL):
            raise ValueError('fixed external support not met')
        def macro(selected):
            values = {str(s):{m:eval_metrics([r for r in selected if r['store']==s],scale[s],m) for m in methods} for s in ACTIVE_EVAL}
            return {m:{f:math.fsum(v[m][f] for v in values.values())/5 for f in ('daily','total','joint')} for m in methods}
        measured = macro(rows)
        quarters = {str(q):macro([r for r in rows if (dt.date.fromisoformat(r['origin']).month-1)//3+1==q]) for q in range(1,5)}
        summary = {'status':'complete','research_state':'PAUSED','adopted':False,'new_macos_generation':True,
                   'one_training_trajectory':True,'selection':selection,'parameter_count':30369,
                   'train_windows':300,'time_validation_windows':120,'transfer_validation_windows':60,
                   'new_internal_profiles':480,'new_development_profiles':150,'calendar_enabled_channels':sum(support['enabled']),
                   'development_macro':measured,'per_store':by_store,'quarter_macro':quarters,'support_counts':support_counts,
                   'development_decision':progress(measured['transfer_selected'],measured['baseline'],True),
                   'requested':150,'neural_supported':len(pending),'baseline_only':25,
                   'complete_label_windows':sum(r['complete_label'] for r in rows),'unique_forward_states':len(unique),
                   'source_pins':{p:pin(raw) for p,raw in sources.items()},'archive_pin':archive_pin,'train_member_pin':member_pin,
                   'resources':checkpoint(),'seconds':time.monotonic()-STARTED,'previously_read_development':True,
                   'windows_results_identical_verified':False,'formal_permission':False,'reserved_2016_2017_numeric_read':False}
        if any((REPO/p).read_bytes()!=raw for p,raw in sources.items()):raise ValueError('source changed during run')
        files.json('summary.json',summary);status='complete'
        print(json.dumps({k:summary[k] for k in ('status','selection','development_macro','development_decision','seconds')}),flush=True)
    except BaseException as error:
        files.json('failure.json',{'stage':stage,'type':type(error).__name__,'message':str(error),
                                  'traceback':traceback.format_exc(),'research_state':'PAUSED'},True)
        files.json('failure-prefix.json',{'journal':journal,'curve':curve,'rows':rows},True)
        if model is not None:files.state('failure-state.pt',model.state_dict(),True)
        raise
    finally:
        files.json('root-closed.json',{'status':status,'files':files.pins.copy(),'immutable':True,'formal_permission':False},True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--archive',type=Path,required=True)
    args=parser.parse_args();run(args.output,args.archive)
