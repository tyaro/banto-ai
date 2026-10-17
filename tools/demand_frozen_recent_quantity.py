"""Past-only 2014 rolling quantity fits, then one frozen pre-2015 state."""
import time
STARTED = time.monotonic()
import argparse
import datetime as dt
import json
import math
from pathlib import Path
import sys
import traceback

from demand_autonomous_mean import FIT, read_history, calibrate, score
from demand_open_quantity import fit_gated, predict_gated
from demand_open_quantity_evaluation import tensor_inputs, assemble
from demand_temporal_selection import temporal_split
from demand_recurring_closure import attach_scenarios, score_cohort
from verify_demand_transfer import verify, pin
from macos_demand_runtime import MacCheckpoint

REPO = Path(__file__).resolve().parents[1]
CONTRACT = 'docs/research/demand-frozen-recent-quantity-design-2026-10-15.md'
ORDER = ('matched_mean28', 'open_mean28', 'recent_gated_ridge')


def select_recent(packets, origin):
    result, seen = [], set()
    for packet in packets:
        if packet['store'] not in FIT:
            continue
        day = dt.date.fromisoformat(packet['origin'])
        if day < origin-dt.timedelta(days=365) or day+dt.timedelta(days=13) >= origin:
            continue
        key = packet['store'], packet['origin']
        if key in seen:
            raise ValueError('duplicate eligible past packet')
        seen.add(key); result.append(packet)
    return result


def fit_forecast(pool, current, guard=lambda: None):
    import torch
    guard()
    if len(current) != 10 or {r['store'] for r in current} != set(FIT) or len({r['origin'] for r in current}) != 1:
        raise ValueError('ten simultaneous forecasts required')
    origin = dt.date.fromisoformat(current[0]['origin'])
    selected = select_recent(pool, origin)
    counts = {str(s): sum(p['store'] == s for p in selected) for s in FIT}
    if len(selected) < 140 or len(set(counts.values())) != 1 or any(n == 0 for n in counts.values()):
        raise ValueError('balanced supported past pool required')
    raw, base, u, mask = tensor_inputs(selected)
    actual = torch.tensor([p['actual'] for p in selected], dtype=torch.float64)
    if not torch.isfinite(actual).all() or (actual < 0).any():
        raise ValueError('complete finite past targets required')
    state = fit_gated(raw, base, actual, u, mask)
    cr, cb, cu, cm = tensor_inputs(current)
    predictions = predict_gated(cr, cb, cu, cm, state).tolist()
    journal = {'origin': str(origin), 'pool_keys': [[r['store'], r['origin']] for r in selected],
               'pool_windows': len(selected), 'per_store': counts,
               'last_label_day': max(str(dt.date.fromisoformat(r['origin'])+dt.timedelta(days=13)) for r in selected),
               'state': {k: v.tolist() for k, v in state.items()}}
    return predictions, journal


def choose(scores):
    if set(scores) != set(ORDER): raise ValueError('fixed three-way comparison required')
    best = ORDER[0]
    for name in ORDER:
        if not math.isfinite(scores[name]['joint']): raise ValueError('invalid outer score')
        if scores[name]['joint'] < scores[best]['joint']-1e-12: best = name
    return best


def run(output):
    guard = MacCheckpoint(seconds=870)
    import torch
    from demand_calendar_train import Files
    root = output.absolute()
    if root.parent != REPO/'artifacts' or root.exists(): raise ValueError('fresh output root required')
    files = Files(root); status, stage, journals, forecasts = 'failed', 'source', [], {}
    source = REPO/'artifacts/macos-demand-open-quantity-20261015'
    try:
        if sys.version_info[:3] != (3,14,8) or sys.platform != 'darwin' or torch.__version__ != '2.14.0': raise ValueError('fixed Mac runtime required')
        source_closure = verify(source); old = json.loads((source/'summary.json').read_bytes())
        roots, protected = old['source_roots'], old['protected_roots']
        additional = old['source_closure']
        if source_closure['recorded_status'] != 'complete' or verify(Path(additional['root'])) != additional or {k:verify(Path(v['root'])) for k,v in roots.items()} != roots or {p:verify(Path(p)) for p in protected} != protected:
            raise ValueError('closed sources changed')
        if any(pin(REPO/p) != value for p,value in old['source_pins'].items()): raise ValueError('old source changed')
        names = [CONTRACT, 'tools/demand_frozen_recent_quantity.py', 'tests/test_demand_frozen_recent_quantity.py', *old['source_pins']]
        sources = {p:(REPO/p).read_bytes() for p in dict.fromkeys(names)}; pins = {p:pin(REPO/p) for p in sources}
        files.write('contract.md', sources[CONTRACT]); files.json('sources.json', {p:v.decode() for p,v in sources.items()})
        config = json.loads((source/'config-before-input.json').read_bytes())
        files.json('config-before-input.json', {'source_closure':source_closure, 'source_roots':roots, 'protected_roots':protected,
                   'additional_root':additional, 'source_pins':pins, 'order':ORDER, 'final_freeze_origin':'2015-01-01',
                   'new_nn_fit':False, '2015_fitting':False, 'formal_permission':False})
        original250 = Path(roots['original250']['root']); original250summary = json.loads((original250/'summary.json').read_bytes())
        original = Path(original250summary['source_roots']['original']['root'])
        binding = json.loads((Path(original250summary['primary_root']['root'])/'binding.json').read_bytes())
        scales = {int(s):v['scale'] for s,v in binding['scales'].items()}
        enabled = json.loads((source/'fit-calendar-support.json').read_bytes())['enabled']
        monthdays = {p['month_day'] for p in old['closure_pattern']['patterns']}
        split = temporal_split(binding['time_keys'])
        torch.set_num_threads(2); torch.set_num_interop_threads(1); torch.use_deterministic_algorithms(True)
        stage = 'past-2014-only-packets'
        saved_fit = json.loads((source/'fit-inputs-and-labels.json').read_bytes())
        pool = [{**r,'actual':a} for r,a in zip(saved_fit['inputs'],saved_fit['actual'])]
        history = read_history(original/'selected-internal.csv', dt.date(2013,1,1), dt.date(2014,12,31))
        validation = assemble(history,binding['time_keys'],scales,enabled,monthdays,guard)
        files.json('time-inputs.json',validation)
        all_packets = pool+[{**r,'actual':[history[r['store']][dt.date.fromisoformat(r['origin'])+dt.timedelta(days=j)] for j in range(14)]} for r in validation]
        files.json('past-packet-labels.json',[{'store':r['store'],'origin':r['origin'],'actual':r['actual']} for r in all_packets])
        raw_internal = []
        stage = 'twelve-2014-past-only-solves'
        for text in sorted({r['origin'] for r in validation}):
            current = sorted([r for r in validation if r['origin']==text],key=lambda r:r['store'])
            predictions,journal = fit_forecast(pool,current,guard.check)
            journals.append(journal); guard.check()
            for r,p in zip(current,predictions): raw_internal.append({'store':r['store'],'origin':text,'raw_prediction':p})
            pool.extend([r for r in all_packets if r['origin']==text])
        files.json('2014-raw-predictions.json',raw_internal)
        raw_lookup = {(r['store'],r['origin']):r['raw_prediction'] for r in raw_internal}
        val_lookup = {(r['store'],r['origin']):r for r in validation}
        def data(keys):
            selected = [val_lookup[tuple(k)] for k in keys]
            _,b,u,m = tensor_inputs(selected)
            y = torch.tensor([[history[s][dt.date.fromisoformat(d)+dt.timedelta(days=j)] for j in range(14)] for s,d in keys],dtype=torch.float64)
            p = torch.tensor([raw_lookup[tuple(k)] for k in keys],dtype=torch.float64)
            matched = torch.tensor([r['matched_mean28'] for r in selected],dtype=torch.float64)
            return b,u,m,y,p,matched
        b,u,m,y,p,_ = data(split['inner'])
        alpha = {**calibrate(p,b,y,u),'selection_period':'2014 inner60 only'}
        ob,ou,om,oy,op,matched = data(split['outer'])
        scores = {name:score(value,oy,ou) for name,value in (('matched_mean28',matched),('open_mean28',ob),('recent_gated_ridge',ob+alpha['alpha']*(op-ob)))}
        selected = choose(scores)
        selection = {'selected':selected,'alpha':alpha,'scores':scores,'2015_used':False,'selection_period':'2014 outer50 only','temporal_split':split}
        files.json('frozen-policy-before-final-fit.json',selection)
        stage = 'final-pre-2015-solve'
        january = assemble(history,[(s,'2015-01-01') for s in FIT],scales,enabled,monthdays,guard)
        _,final_journal = fit_forecast(pool,january,guard.check); journals.append(final_journal); guard.check()
        if final_journal['pool_windows'] != 220 or final_journal['last_label_day'] != '2014-12-15': raise ValueError('final 2014 pool changed')
        files.json('all-state-journals.json',journals)
        files.json('final-state-before-2015.json', {'selection':selection, 'state':final_journal['state'],
                   'origin':'2015-01-01','last_label_day':final_journal['last_label_day'],'new_2015_fit':False})
        print(json.dumps({'stage':'frozen-before-2015','selection':selection,'final_pool':220}),flush=True)
        state = {k:torch.tensor(v,dtype=torch.bool if k=='active' else torch.float64) for k,v in final_journal['state'].items()}
        stage = 'fixed-2015-predictions'
        dev_inputs = json.loads((source/'2015-inputs.json').read_bytes()); keys = {}
        for name in ('original250','newyear10'):
            before = json.loads((source/(name+'-predictions-before-labels.json')).read_bytes())
            values = dev_inputs[name]; dr,db,du,dm = tensor_inputs(values)
            dp = predict_gated(dr,db,du,dm,state)
            choices = {'matched_mean28':[r['matched_mean28'] for r in values],'open_mean28':db.tolist(),
                       'recent_gated_ridge':(db+alpha['alpha']*(dp-db)).tolist()}
            forecasts[name] = []
            for i,(r,old_row) in enumerate(zip(values,before)):
                if (r['store'],r['origin']) != (old_row['store'],old_row['origin']) or r['matched_mean28']!=old_row['baseline_proxy']: raise ValueError('fixed inputs/control changed')
                forecasts[name].append({k:old_row[k] for k in ('store','origin','scale','baseline','prior','baseline_proxy','assumed_closure','operating_status')}
                       | {'candidate':choices[selected][i], 'alternatives':{k:v[i] for k,v in choices.items()}})
            keys[name] = [(r['store'],r['origin']) for r in forecasts[name]]
            files.json(name+'-predictions-before-labels.json',forecasts[name])
        stage = 'two-cohorts-two-labels'
        measured = {}
        for name in ('original250','newyear10'):
            labels = {(r['store'],r['origin']):r for r in json.loads((source/(name+'-observed-labels.json')).read_bytes())}
            obs,assumed,ledger = attach_scenarios(forecasts[name],labels)
            files.json(name+'-observed-labels.json',obs); files.json(name+'-assumed-labels.json',assumed); files.json(name+'-assumption-ledger.json',ledger)
            measured[name] = {mode:{'primary':score_cohort(rows,keys[name]),
                    'fixed_alternatives':{m:score_cohort([{**r,'candidate':r['alternatives'][m]} for r in rows],keys[name]) for m in ORDER}}
                    for mode,rows in (('observed',obs),('assumed_missing_zero',assumed))}
        if verify(source)!=source_closure or verify(Path(additional['root']))!=additional or {k:verify(Path(v['root'])) for k,v in roots.items()}!=roots or {p:verify(Path(p)) for p in protected}!=protected or any(pin(REPO/p)!=v for p,v in pins.items()): raise ValueError('source/root changed')
        summary = {'status':'complete','source_closure':source_closure,'source_roots':roots,'protected_roots':protected,'additional_root':additional,
                   'source_pins':pins,'selection':selection,'cohorts':measured,'new_ridge_fits':len(journals),'2015_fitting':False,
                   'final_fit_windows':220,'final_fit_last_label':'2014-12-15','closure_pattern':old['closure_pattern'],
                   'cohorts_combined':False,'overlapping_store_days':20,'adopted':False,'formal_permission':False,
                   'resources':guard.check(),'seconds':time.monotonic()-STARTED}
        files.json('summary.json',summary); status='complete'
        print(json.dumps({'status':status,'selected':selected,'cohorts':{n:{m:v['primary']['improvement_percent_over'] for m,v in ms.items()} for n,ms in measured.items()},'seconds':summary['seconds']}),flush=True)
    except BaseException as error:
        files.json('failure.json',{'stage':stage,'type':type(error).__name__,'message':str(error),'traceback':traceback.format_exc()},True)
        files.json('failure-prefix.json',{'journals':journals,'forecasts':forecasts},True); raise
    finally:
        files.json('root-closed.json',{'status':status,'files':files.pins.copy(),'immutable':True,'formal_permission':False},True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);run(parser.parse_args().output)
