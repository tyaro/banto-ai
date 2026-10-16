"""Finite internal choice of two mean corrections, then fixed 2015 development."""
import time
STARTED = time.monotonic()
import argparse
import csv
import datetime as dt
import json
import math
from pathlib import Path
import subprocess
import sys
import traceback

from demand_macos_rebuild import PastOnly, pin, snapshot
from demand_existing_store_evaluation import metrics, ORIGINS, FIRST, LAST, FIT
from demand_public_calendar import build_inputs
from demand_statistical_features import encode_profile, COLUMNS as STAT_COLUMNS
from demand_statistical_overlay import describe_history
from macos_demand_runtime import MacCheckpoint
from verify_demand_transfer import verify, pin as file_pin

REPO = Path(__file__).resolve().parents[1]
CONTRACT = 'docs/research/demand-autonomous-mean-design-2026-10-15.md'
STATE_SHA = '166171df43537141ea6174b0180f21e5044ddc54d4ea35c4ea7af5018d05aaf6'
LAMBDA = .01
FEATURES = ('intercept', *STAT_COLUMNS, 'context_mean_over_u', 'context_cv',
            *(f'future_calendar_{k}' for k in range(60)), 'lead_fraction')


def read_history(path, first, last):
    histories = {s: {} for s in FIT}
    stores = frozenset(map(str, FIT))
    with path.open(newline='', encoding='utf-8') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ['store_nbr', 'date', 'sales', 'observed']:
            raise ValueError('unexpected closed snapshot schema')
        seen = set()
        for row in reader:
            if row['store_nbr'] not in stores or not str(first) <= row['date'] <= str(last):
                continue
            s, day = int(row['store_nbr']), dt.date.fromisoformat(row['date'])
            if (s, day) in seen or row['observed'] not in ('0', '1'):
                raise ValueError('duplicate snapshot key or invalid mask')
            seen.add((s, day))
            if (row['observed'] == '1') != bool(row['sales']):
                raise ValueError('snapshot missing quantity/mask mismatch')
            if row['observed'] == '1':
                value = float(row['sales'])
                if not math.isfinite(value) or value < 0:
                    raise ValueError('invalid selected snapshot quantity')
                histories[s][day] = value
    expected = {(s, first+dt.timedelta(days=k)) for s in FIT for k in range((last-first).days+1)}
    if seen != expected:
        raise ValueError('complete fixed snapshot calendar required')
    return histories


def features(x, encoded):
    if not x['available']:
        raise ValueError('positive supported input required')
    rows = [[1., *encoded['features'], *x['context_statistics'], *calendar, k/13]
            for k, calendar in enumerate(x['future_calendar'])]
    if any(len(r) != 72 or not all(math.isfinite(v) for v in r) for r in rows):
        raise ValueError('fixed 72 finite as-of features required')
    return rows


def assemble(histories, keys, scales, enabled, checkpoint):
    inputs, encoded, ledger, raw = [], [], [], []
    for s, text in keys:
        origin = dt.date.fromisoformat(text)
        past = PastOnly(histories[s], origin)
        x = build_inputs(past, origin, scales[s], 'pre_post', enabled)
        profile = describe_history(past, origin)
        e = encode_profile(profile, origin, scales[s])
        inputs.append(x); encoded.append(e); raw.append(features(x, e))
        ledger.append({'store': s, 'origin': text, 'profile': profile, 'encoded': e})
        checkpoint()
    return inputs, encoded, ledger, raw


def ridge_fit(raw, baseline, actual, scales):
    import torch
    if (raw.ndim != 3 or raw.shape[1:] != (14, 72) or baseline.shape != raw.shape[:2]
            or actual.shape != baseline.shape or scales.shape != (len(raw),)):
        raise ValueError('fixed ridge shapes required')
    flat = raw.reshape(-1, 72)
    mean = flat.mean(0)
    std = ((flat-mean).square().mean(0)).sqrt()
    active = std > 1e-12
    mean[0] = 0.; std[0] = 1.; active[0] = True
    safe_std = torch.where(active, std, torch.ones_like(std))
    x = torch.where(active, (raw-mean)/safe_std, 0.)
    y = (actual-baseline)/scales[:, None]
    daily_x, daily_y = x.reshape(-1, 72), y.reshape(-1)
    total_x, total_y = x.mean(1), y.mean(1)
    penalty = torch.eye(72, dtype=torch.float64)*LAMBDA
    penalty[0, 0] = 0.
    gram = .5*(daily_x.T@daily_x)/len(daily_x)+.5*(total_x.T@total_x)/len(total_x)+penalty
    rhs = .5*(daily_x.T@daily_y)/len(daily_x)+.5*(total_x.T@total_y)/len(total_x)
    beta = torch.linalg.solve(gram, rhs)
    if not bool(torch.isfinite(beta).all()):
        raise ValueError('nonfinite ridge coefficients')
    return {'mean': mean, 'std': safe_std, 'active': active, 'beta': beta}


def ridge_predict(raw, baseline, scales, state):
    import torch
    x = torch.where(state['active'], (raw-state['mean'])/state['std'], 0.)
    return torch.relu(baseline+scales[:, None]*(x@state['beta']))


def calibrate(prediction, baseline, actual, scales):
    d, r = (prediction-baseline)/scales[:, None], (actual-baseline)/scales[:, None]
    ed, cd = d.square().mean().item(), (d*r).mean().item()
    et, ct = d.mean(1).square().mean().item(), (d.mean(1)*r.mean(1)).mean().item()
    upper = 1.
    for energy, covariance in ((ed, cd), (et, ct)):
        if energy > 0:
            upper = min(upper, max(0., 2*covariance/energy))
    energy, covariance = .5*(ed+et), .5*(cd+ct)
    alpha = max(0., min(upper, covariance/energy)) if energy > 0 else 0.
    if not all(math.isfinite(v) for v in (ed, cd, et, ct, alpha)):
        raise ValueError('nonfinite internal calibration')
    return {'alpha': alpha, 'upper': upper, 'daily_energy': ed, 'daily_covariance': cd,
            'total_energy': et, 'total_covariance': ct, 'selection_period': '2014 time validation only'}


def score(prediction, actual, scales):
    daily = ((prediction-actual)/scales[:, None]).square().mean().item()
    total = ((prediction.sum(1)-actual.sum(1))/(14*scales)).square().mean().item()
    return {'daily': daily, 'total': total, 'joint': .5*(daily+total)}


def choose(scores):
    best = 'baseline'
    for name in ('ridge_calibrated', 'nn_calibrated'):
        if scores[name]['joint'] < scores[best]['joint']-1e-12:
            best = name
    return best


def development_metrics(rows, scales):
    converted = [{**{k: v for k, v in r.items() if k not in ('candidate', 'incumbent')},
                  'time_selected': r['candidate'], 'transfer_selected': r['incumbent']} for r in rows]
    result = metrics(converted, scales)
    names = {'time_selected': 'candidate', 'transfer_selected': 'incumbent'}
    rename = lambda values: {names.get(k, k): v for k, v in values.items()}
    result['macro'] = rename(result['macro'])
    result['per_store'] = {s: rename(v) for s, v in result['per_store'].items()}
    result['quarter_macro'] = {q: rename(v) for q, v in result['quarter_macro'].items()}
    result['quarter_per_store'] = {q: {s: rename(v) for s, v in stores.items()}
                                 for q, stores in result['quarter_per_store'].items()}
    result['improved_stores'] = rename(result['improved_stores'])
    for counts in result['support_counts'].values():
        counts['methods'] = rename(counts['methods'])
    return result


def run(output):
    import torch
    from demand_calendar_train import Files
    from demand_statistical_feature_model import StatisticalFeatureMean
    root = output.absolute()
    if root.parent != REPO/'artifacts' or root.exists():
        raise ValueError('fresh output root required')
    files = Files(root); guard = MacCheckpoint(seconds=870)
    status, stage, rows = 'failed', 'source', []
    original = REPO/'artifacts/macos-demand-rebuild-20261015'
    development = REPO/'artifacts/macos-demand-existing-stores-2015-20261015'
    try:
        if sys.version_info[:3] != (3, 14, 8) or torch.__version__ != '2.14.0' or sys.platform != 'darwin':
            raise ValueError('fixed Mac Python/Torch required')
        original_verify, dev_verify = verify(original), verify(development)
        if any(v['recorded_status'] != 'complete' for v in (original_verify, dev_verify)):
            raise ValueError('complete source roots required')
        prior = json.loads((original/'summary.json').read_bytes())
        dev_summary = json.loads((development/'summary.json').read_bytes())
        source_names = [CONTRACT, 'tools/demand_autonomous_mean.py', *prior['source_pins'], *dev_summary['source_pins']]
        sources = {p: (REPO/p).read_bytes() for p in dict.fromkeys(source_names)}
        for summary in (prior, dev_summary):
            if any(pin(sources[p]) != expected for p, expected in summary['source_pins'].items()):
                raise ValueError('original pinned source changed')
        files.write('contract.md', sources[CONTRACT]); files.json('sources.json', {p: r.decode() for p, r in sources.items()})
        state_path = original/'time_selected.pt'
        if file_pin(state_path)['sha256'] != STATE_SHA:
            raise ValueError('frozen incumbent state changed')
        groups_support = json.loads((original/'split-support.json').read_bytes())
        groups, support = groups_support['groups'], groups_support['support']
        scale_meta = json.loads((original/'scale-metadata.json').read_bytes())
        scales = {s: scale_meta[str(s)]['scale'] for s in FIT}
        if (len(groups['fit']) != 300 or len(groups['time_validation']) != 120
                or sum(support['enabled']) != 42 or not all(scales[s] > 0 for s in FIT)):
            raise ValueError('fixed fit/time/support/positive scales required')
        for name in ('fit', 'time_validation'):
            count = 30 if name == 'fit' else 12
            if any(sum(s == store for s, _ in groups[name]) != count for store in FIT):
                raise ValueError('fixed equal store weights changed')
            for s, text in groups[name]:
                origin = dt.date.fromisoformat(text)
                if (s not in FIT or (name == 'fit' and origin+dt.timedelta(days=13) >= dt.date(2014, 7, 1))
                        or (name == 'time_validation' and not dt.date(2014, 7, 1) <= origin
                            or origin+dt.timedelta(days=13) >= dt.date(2015, 1, 1))):
                    raise ValueError('internal temporal split changed')
        torch.set_num_threads(2); torch.set_num_interop_threads(1); torch.use_deterministic_algorithms(True)
        files.json('config-before-internal.json', {'ridge_lambda': LAMBDA, 'features': FEATURES,
                   'candidate_order': ['baseline', 'ridge_calibrated', 'nn_calibrated'], 'tie_tolerance': 1e-12,
                   'primary_target': 'observed_sales_mean', 'new_transformer_training': False,
                   'incumbent_state_pin': file_pin(state_path), 'scopes': ['fit300', 'time120', 'development250'],
                   'source_pins': {p: pin(r) for p, r in sources.items()}, 'formal_permission': False,
                   'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
                   'runtime': {'python': sys.version, 'torch': torch.__version__, 'device': 'cpu',
                               'ridge_dtype': 'float64', 'incumbent_dtype': 'float32'}})
        files.json('binding.json', {'scales': {str(s): scale_meta[str(s)] for s in FIT}, 'support': support,
                   'fit_keys': groups['fit'], 'time_keys': groups['time_validation'],
                   'original_root': original_verify, 'development_root': dev_verify})
        guard.check(); stage = 'internal-inputs'
        history = read_history(original/'selected-internal.csv', dt.date(2013, 1, 1), dt.date(2014, 12, 31))
        files.write('selected-internal.csv', snapshot(history, dt.date(2013, 1, 1), dt.date(2014, 12, 31)))
        data, profiles = {}, []
        for name in ('fit', 'time_validation'):
            inputs, encoded, ledger, raw = assemble(history, groups[name], scales, support['enabled'], guard.check)
            actual = [[history[s].get(dt.date.fromisoformat(text)+dt.timedelta(days=k)) for k in range(14)]
                      for s, text in groups[name]]
            if any(v is None for row in actual for v in row):
                raise ValueError('complete fixed internal labels required')
            profiles.extend({**r, 'split': name} for r in ledger)
            data[name] = {'raw': torch.tensor(raw, dtype=torch.float64),
                          'baseline': torch.tensor([x['baseline'] for x in inputs], dtype=torch.float64),
                          'actual': torch.tensor(actual, dtype=torch.float64),
                          'scales': torch.tensor([scales[s] for s, _ in groups[name]], dtype=torch.float64),
                          'inputs': inputs, 'encoded': encoded}
        files.json('internal-profiles.json', profiles)
        stage = 'single-ridge-fit'
        train, val = data['fit'], data['time_validation']
        ridge = ridge_fit(train['raw'], train['baseline'], train['actual'], train['scales'])
        ridge_json = {k: v.tolist() for k, v in ridge.items()}
        files.json('ridge-state.json', {**ridge_json, 'lambda': LAMBDA, 'features': FEATURES,
                   'fit_only_standardization': True, 'fit_windows': 300})
        raw_ridge = ridge_predict(val['raw'], val['baseline'], val['scales'], ridge)
        clone = StatisticalFeatureMean()
        clone.load_state_dict(torch.load(state_path, weights_only=True, map_location='cpu'), strict=True); clone.eval()
        nn_rows = []
        fields = ('normalized_values', 'observed', 'past_calendar', 'future_calendar', 'context_statistics', 'baseline', 'scale')
        stage = 'frozen-internal-nn-forward'
        with torch.no_grad():
            for start in range(0, 120, 8):
                inputs = val['inputs'][start:start+8]; encoded = val['encoded'][start:start+8]
                tensors = [torch.tensor([x[f] for x in inputs], dtype=torch.bool if f == 'observed' else torch.float32) for f in fields]
                tensors.append(torch.tensor([e['features'] for e in encoded], dtype=torch.float32))
                daily, total = clone(*tensors)
                if not bool(torch.allclose(daily.sum(1), total, rtol=1e-6, atol=1e-5)):
                    raise ValueError('incumbent total inconsistency')
                nn_rows.extend(daily.tolist()); guard.check()
        raw_nn = torch.tensor(nn_rows, dtype=torch.float64)
        files.json('time-validation-predictions.json', [{'store': s, 'origin': text,
                   'baseline': val['baseline'][k].tolist(), 'raw_ridge': raw_ridge[k].tolist(),
                   'raw_nn': raw_nn[k].tolist(), 'actual': val['actual'][k].tolist()}
                   for k, (s, text) in enumerate(groups['time_validation'])])
        stage = 'internal-calibration-and-choice'
        calibrations, predictions = {}, {'baseline': val['baseline']}
        for name, prediction in (('ridge_calibrated', raw_ridge), ('nn_calibrated', raw_nn)):
            calibration = calibrate(prediction, val['baseline'], val['actual'], val['scales'])
            calibrations[name] = calibration
            predictions[name] = val['baseline']+calibration['alpha']*(prediction-val['baseline'])
        scores = {name: score(p, val['actual'], val['scales']) for name, p in predictions.items()}
        selected = choose(scores)
        selection = {'selected': selected, 'calibrations': calibrations, 'scores': scores,
                     'raw_nn_reference': score(raw_nn, val['actual'], val['scales']),
                     'original_time_step': 3328, 'ridge_coefficients': 72,
                     'ridge_active_columns': int(ridge['active'].sum().item()), 'new_transformer_fit': False,
                     'selection_data': '2014 time120 only', 'development_used_for_selection': False,
                     'original_trajectory_stopped_by': 'C_transfer_validation'}
        files.json('internal-selection.json', selection)
        files.json('frozen-selection-before-development.json', {**selection, 'ridge_state_pin': files.pins['ridge-state.json'],
                   'incumbent_state_pin': file_pin(state_path), 'no_further_selection': True})
        print(json.dumps({'stage': 'frozen', 'selected': selected, 'scores': scores, 'calibrations': calibrations}), flush=True)
        guard.check(); del history, data, train, val, clone, profiles
        stage = 'fixed-existing-development'
        history = read_history(development/'selected-existing-stores.csv', FIRST, LAST)
        files.write('selected-development.csv', snapshot(history, FIRST, LAST))
        before = json.loads((development/'predictions-before-labels.json').read_bytes())
        originals = {(r['store'], r['origin']): r for r in before}
        keys = [(s, str(d)) for s in FIT for d in ORIGINS]
        inputs, encoded, profiles, raw = assemble(history, keys, scales, support['enabled'], guard.check)
        base = torch.tensor([x['baseline'] for x in inputs], dtype=torch.float64)
        dev_scales = torch.tensor([scales[s] for s, _ in keys], dtype=torch.float64)
        if len(originals) != 250 or set(originals) != set(keys):
            raise ValueError('fixed development grid changed')
        incumbent = []
        for (s, text), x in zip(keys, inputs):
            prior_row = originals[s, text]
            if prior_row['baseline'] != x['baseline'] or prior_row['scale'] != scales[s] or not prior_row['model_available']:
                raise ValueError('saved incumbent baseline/scale/support changed')
            incumbent.append(prior_row['time_selected'])
        if selected == 'baseline':
            candidate = base
        else:
            raw_prediction = (ridge_predict(torch.tensor(raw, dtype=torch.float64), base, dev_scales, ridge)
                              if selected == 'ridge_calibrated' else torch.tensor(incumbent, dtype=torch.float64))
            candidate = base+calibrations[selected]['alpha']*(raw_prediction-base)
        rows = [{'store': s, 'origin': text, 'scale': scales[s], 'baseline': x['baseline'],
                 'candidate': candidate[k].tolist(), 'incumbent': incumbent[k],
                 'model_available': x['available'], 'input_reasons': x['reasons']}
                for k, ((s, text), x) in enumerate(zip(keys, inputs))]
        files.json('development-profiles.json', profiles)
        files.json('predictions-before-labels.json', rows)
        labelled = [{**r, 'actual': [history[r['store']].get(dt.date.fromisoformat(r['origin'])+dt.timedelta(days=k)) for k in range(14)]}
                    for r in rows]
        for row in labelled:
            row['complete_label'] = all(v is not None for v in row['actual'])
        files.json('predictions-and-labels.json', labelled)
        stage = 'fixed-metrics'
        measured = development_metrics(labelled, scales)
        if (measured['neural_supported'] != 250 or measured['complete_label_windows'] != 240
                or any(v['methods']['candidate']['observed_daily_labels'] != 349 for v in measured['support_counts'].values())):
            raise ValueError('fixed development support changed')
        if (verify(original) != original_verify or verify(development) != dev_verify
                or any((REPO/p).read_bytes() != raw for p, raw in sources.items())):
            raise ValueError('original closed roots or pinned source changed')
        for field in ('daily', 'total', 'joint'):
            if not math.isclose(measured['macro']['incumbent'][field], dev_summary['macro']['time_selected'][field], rel_tol=1e-10, abs_tol=1e-10):
                raise ValueError('saved incumbent metric mismatch')
        summary = {'status': 'complete', 'research_state': 'finite_campaign_complete', 'selection': selection,
                   'sources': {'original': original_verify, 'development': dev_verify},
                   'source_pins': {p: pin(r) for p, r in sources.items()}, 'target': 'observed_sales_mean',
                   'new_ridge_fit': True, 'new_transformer_fit': False, 'new_internal_profiles': 420,
                   'new_development_profiles': 250, 'development_already_read': True,
                   'no_development_reselection': True, 'adopted': False, 'formal_permission': False,
                   'resources': guard.check(), 'seconds': time.monotonic()-STARTED, **measured}
        files.json('summary.json', summary); status = 'complete'
        print(json.dumps({k: summary[k] for k in ('status', 'macro', 'primary_development_decision', 'improved_stores', 'seconds')}), flush=True)
    except BaseException as error:
        files.json('failure.json', {'stage': stage, 'type': type(error).__name__, 'message': str(error),
                                  'traceback': traceback.format_exc()}, True)
        files.json('failure-prefix.json', {'rows': rows}, True)
        raise
    finally:
        files.json('root-closed.json', {'status': status, 'files': files.pins.copy(), 'immutable': True,
                                     'formal_permission': False}, True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
