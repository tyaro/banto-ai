"""Inner-only NN/checkpoint/alpha, outer-only method choice, fixed 2015 use."""
import time
STARTED = time.monotonic()
import argparse
import datetime as dt
import json
import math
from pathlib import Path
import random
import sys
import traceback

from demand_autonomous_mean import (FIT, ORIGINS, FIRST, LAST, read_history, assemble,
    calibrate, score, ridge_predict, development_metrics)
from demand_macos_rebuild import pin
from demand_training_adequacy import EarlyStopper
from macos_demand_runtime import MacCheckpoint
from verify_demand_transfer import verify

REPO = Path(__file__).resolve().parents[1]
CONTRACT = 'docs/research/demand-temporal-selection-design-2026-10-15.md'
BOUNDARY = dt.date(2014, 10, 1)
ORDER = ('baseline', 'nn_calibrated', 'rolling_calibrated')


def temporal_split(keys):
    result = {'inner': [], 'outer': [], 'crossing': []}
    seen = set()
    for store, text in keys:
        if type(store) is not int or store not in FIT:
            continue  # Foreign metadata rejected before date or target access.
        origin = dt.date.fromisoformat(text)
        key = (store, text)
        if key in seen or not dt.date(2014, 7, 1) <= origin or origin+dt.timedelta(days=13) >= dt.date(2015, 1, 1):
            raise ValueError('distinct 2014 time keys required')
        seen.add(key)
        group = 'inner' if origin+dt.timedelta(days=13) < BOUNDARY else 'outer' if origin >= BOUNDARY else 'crossing'
        result[group].append(key)
    return result


def selected_targets(rows, keys):
    wanted = set(map(tuple, keys)); found = {}
    for row in rows:
        if row['store'] not in FIT:
            continue
        key = row['store'], row['origin']
        if key not in wanted:
            continue
        if key in found:
            raise ValueError('duplicate selected label key')
        values = row['actual']
        if len(values) != 14 or any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in values):
            raise ValueError('complete finite selected labels required')
        found[key] = values
    if set(found) != wanted:
        raise ValueError('selected label support changed')
    return [found[tuple(key)] for key in keys]


def select_method(scores):
    if set(scores) != set(ORDER):
        raise ValueError('fixed finite comparison required')
    best = ORDER[0]
    for name in ORDER:
        if not math.isfinite(scores[name]['joint']) or scores[name]['joint'] < 0:
            raise ValueError('invalid outer loss')
        if scores[name]['joint'] < scores[best]['joint']-1e-12:
            best = name
    return best


def tensors(inputs, encoded):
    import torch
    fields = ('normalized_values', 'observed', 'past_calendar', 'future_calendar',
              'context_statistics', 'baseline', 'scale')
    return [torch.tensor([x[f] for x in inputs], dtype=torch.bool if f == 'observed' else torch.float32)
            for f in fields]+[torch.tensor([e['features'] for e in encoded], dtype=torch.float32)]


def predict_nn(model, inputs, checkpoint):
    import torch
    was_training = model.training; model.eval()
    predictions = []
    with torch.no_grad():
        for start in range(0, len(inputs[0]), 8):
            daily, _ = model(*[v[start:start+8] for v in inputs])
            predictions.append(daily.detach().to(torch.float64)); checkpoint()
    model.train(was_training)
    return torch.cat(predictions)


def check_pools(headers, journals):
    if len(headers) != 670 or len(journals) != 37:
        raise ValueError('closed rolling universe changed')
    for journal in journals:
        origin = dt.date.fromisoformat(journal['origin'])
        eligible = {(p['store'], p['origin']) for p in headers if p['store'] in FIT and p['complete_label']
                    and origin-dt.timedelta(days=365) <= dt.date.fromisoformat(p['origin'])
                    and dt.date.fromisoformat(p['origin'])+dt.timedelta(days=13) < origin}
        keys = list(map(tuple, journal['pool_keys']))
        counts = {str(s): sum(k[0] == s for k in eligible) for s in FIT}
        if (set(keys) != eligible or len(keys) != len(eligible) or len(eligible) < 140
                or journal['fallback'] or journal['pool_windows'] != len(eligible)
                or counts != journal['per_store_windows'] or len(set(counts.values())) != 1
                or not dt.date.fromisoformat(journal['last_label_day']) < origin):
            raise ValueError('rolling future/pool/support drift')


def run(output):
    import torch
    from demand_calendar_train import Files
    from demand_calendar_model import mean_loss
    from demand_statistical_feature_model import StatisticalFeatureMean
    root = output.absolute()
    if root.parent != REPO/'artifacts' or root.exists():
        raise ValueError('fresh artifact root required')
    files = Files(root); guard = MacCheckpoint(seconds=870)
    status, stage, journal, curve, rows, best = 'failed', 'source', [], [], [], {}
    roots = {k: REPO/'artifacts'/name for k, name in (
        ('original', 'macos-demand-rebuild-20261015'), ('internal', 'macos-demand-autonomous-mean-20261015'),
        ('development', 'macos-demand-existing-stores-2015-20261015'), ('rolling', 'macos-demand-rolling-ridge-20261015'))}
    try:
        if sys.version_info[:3] != (3, 14, 8) or torch.__version__ != '2.14.0' or sys.platform != 'darwin':
            raise ValueError('fixed Mac runtime required')
        closures = {k: verify(p) for k, p in roots.items()}
        if any(v['recorded_status'] != 'complete' for v in closures.values()):
            raise ValueError('complete closed source roots required')
        prior = json.loads((roots['rolling']/'summary.json').read_bytes())
        names = [CONTRACT, 'tools/demand_temporal_selection.py', 'tests/test_demand_temporal_selection.py', *prior['source_pins']]
        sources = {p: (REPO/p).read_bytes() for p in dict.fromkeys(names)}
        if any(pin(sources[p]) != expected for p, expected in prior['source_pins'].items()):
            raise ValueError('original source changed')
        binding = json.loads((roots['internal']/'binding.json').read_bytes())
        scales = {int(s): v['scale'] for s, v in binding['scales'].items()}
        enabled = binding['support']['enabled']
        split = temporal_split(binding['time_keys'])
        if (set(scales) != set(FIT) or any(v <= 0 for v in scales.values()) or sum(enabled) != 42
                or len(binding['fit_keys']) != 300 or [len(split[k]) for k in ('inner', 'outer', 'crossing')] != [60, 50, 10]
                or any(sum(s == store for s, _ in split[k]) != n for k, n in (('inner', 6), ('outer', 5), ('crossing', 1)) for store in FIT)):
            raise ValueError('fixed internal split/support drift')
        rolling = roots['rolling']
        rolling_journals = json.loads((rolling/'internal-state-journal.json').read_bytes())+json.loads((rolling/'development-state-journal.json').read_bytes())
        check_pools(json.loads((rolling/'packet-headers.json').read_bytes()), rolling_journals)
        torch.set_num_threads(2); torch.set_num_interop_threads(1); torch.use_deterministic_algorithms(True)
        files.write('contract.md', sources[CONTRACT]); files.json('sources.json', {p: r.decode() for p, r in sources.items()})
        files.json('config-before-input.json', {'split': split, 'boundary': str(BOUNDARY), 'order': ORDER,
                   'seed': 20261014, 'max_steps': 4096, 'microbatch': 8, 'new_nn_trajectories': 1,
                   'new_ridge_fit': False, 'source_roots': closures, 'source_pins': {p: pin(r) for p, r in sources.items()},
                   'formal_permission': False})
        files.json('binding.json', binding)
        stage = 'fit-and-inner-only'
        history = read_history(roots['original']/'selected-internal.csv', dt.date(2013, 1, 1), dt.date(2014, 12, 31))
        dataset, profiles = {}, []
        for name, keys in (('fit', binding['fit_keys']), ('inner', split['inner'])):
            x, e, ledger, _ = assemble(history, keys, scales, enabled, guard.check)
            actual = [[history[s][dt.date.fromisoformat(text)+dt.timedelta(days=j)] for j in range(14)] for s, text in keys]
            dataset[name] = {'inputs': tensors(x, e), 'actual': torch.tensor(actual, dtype=torch.float64),
                             'u': torch.tensor([scales[s] for s, _ in keys], dtype=torch.float64),
                             'baseline': torch.tensor([v['baseline'] for v in x], dtype=torch.float64)}
            profiles.extend([{'split': name, **p} for p in ledger])
        files.json('fit-inner-profiles.json', profiles)
        rng = random.Random(20261014)
        sampler = [[rng.randrange(300) for _ in range(8)] for _ in range(4096)]
        files.json('sampler.json', {'indices': sampler, 'fit_keys': binding['fit_keys']})
        torch.manual_seed(20261014); model = StatisticalFeatureMean()
        if sum(p.numel() for p in model.parameters()) != 30369:
            raise ValueError('fixed NN parameter count changed')
        files.state('initial.pt', model.state_dict())
        optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, betas=(.9, .999), eps=1e-8,
                                     weight_decay=.01, foreach=False, fused=False)
        selector = EarlyStopper()
        def observe(step):
            inner = dataset['inner']
            prediction = predict_nn(model, inner['inputs'], guard.check)
            measured = score(prediction, inner['actual'].to(torch.float64), inner['u'])
            chosen = selector.observe(step, measured['joint'])
            if chosen['new_best']:
                best.clear(); best.update({k: v.detach().clone() for k, v in model.state_dict().items()})
            curve.append({'step': step, 'inner': measured, 'selection': chosen})
            print(json.dumps({'stage': 'inner-checkpoint', 'step': step, 'joint': measured['joint'], **chosen}), flush=True)
            return chosen['stop']
        stage = 'one-inner-selected-trajectory'; observe(0); model.train(); stop = 'step_cap'
        for step, indices in enumerate(sampler, 1):
            fit = dataset['fit']; x = [v[indices] for v in fit['inputs']]; actual = fit['actual'][indices].to(torch.float32)
            optimizer.zero_grad(set_to_none=True)
            loss, parts = mean_loss(*model(*x), actual, torch.ones_like(actual, dtype=torch.bool), x[-2])
            if not bool(torch.isfinite(loss)):
                raise ValueError('nonfinite training loss')
            loss.backward(); norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
            optimizer.step(); journal.append({'step': step, 'loss': loss.item(), 'norm': norm.item(), **parts}); guard.check()
            if step % 128 == 0 and observe(step):
                stop = 'inner_early_stop'; break
        files.state('final.pt', model.state_dict()); files.state('inner-selected.pt', best)
        files.json('training-journal.json', journal); files.json('selection-curve.json', curve)
        model.load_state_dict(best, strict=True)
        inner = dataset['inner']
        nn_inner = predict_nn(model, inner['inputs'], guard.check)
        raw_internal = {(p['store'], p['origin']): p for p in json.loads((rolling/'internal-predictions-before-labels.json').read_bytes())}
        rolling_inner = torch.tensor([raw_internal[tuple(k)]['rolling_raw'] for k in split['inner']], dtype=torch.float64)
        alphas = {name: {**calibrate(pred, inner['baseline'], inner['actual'].to(torch.float64), inner['u']),
                         'selection_period': '2014 inner60 only'} for name, pred in (('nn', nn_inner), ('rolling', rolling_inner))}
        frozen_inner = {'steps': step, 'stop': stop, 'best_step': selector.best_step,
                        'state_pin': files.pins['inner-selected.pt'], 'alphas': alphas,
                        'outer_used': False, 'development_used': False}
        files.json('frozen-inner-before-outer.json', frozen_inner); guard.check()
        stage = 'outer-fixed-method-selection'
        keys = split['outer']
        x, e, _, _ = assemble(history, keys, scales, enabled, guard.check)
        outer_nn = predict_nn(model, tensors(x, e), guard.check)
        old_internal_labels = json.loads((roots['internal']/'time-validation-predictions.json').read_bytes())
        outer_actual = torch.tensor(selected_targets(old_internal_labels, keys), dtype=torch.float64)
        if outer_actual.tolist() != [[history[s][dt.date.fromisoformat(text)+dt.timedelta(days=j)] for j in range(14)] for s, text in keys]:
            raise ValueError('outer target snapshot changed')
        outer_base = torch.tensor([v['baseline'] for v in x], dtype=torch.float64)
        outer_u = torch.tensor([scales[s] for s, _ in keys], dtype=torch.float64)
        outer_rolling = torch.tensor([raw_internal[tuple(k)]['rolling_raw'] for k in keys], dtype=torch.float64)
        outer_predictions = {'baseline': outer_base,
                             'nn_calibrated': outer_base+alphas['nn']['alpha']*(outer_nn-outer_base),
                             'rolling_calibrated': outer_base+alphas['rolling']['alpha']*(outer_rolling-outer_base)}
        scores = {name: score(p, outer_actual, outer_u) for name, p in outer_predictions.items()}
        selected = select_method(scores)
        files.json('outer-predictions.json', [{'store': s, 'origin': text, 'scale': scales[s],
                   **{name: p[k].tolist() for name, p in outer_predictions.items()}, 'actual': outer_actual[k].tolist()}
                   for k, (s, text) in enumerate(keys)])
        selection = {**frozen_inner, 'selected': selected, 'scores': scores, 'selection_period': '2014 outer50 only',
                     'crossing_used_for_selection': False, 'development_used_for_selection': False}
        files.json('frozen-selection-before-development.json', selection)
        print(json.dumps({'stage': 'frozen-before-development', **selection}), flush=True)
        del dataset, optimizer; guard.check()
        stage = 'development-input-after-freeze'
        dev = roots['development']
        dev_history = read_history(dev/'selected-existing-stores.csv', FIRST, LAST)
        keys = [(s, str(day)) for s in FIT for day in ORIGINS]
        x, e, profiles, raw = assemble(dev_history, keys, scales, enabled, guard.check)
        files.json('development-profiles.json', profiles)
        dev_nn = predict_nn(model, tensors(x, e), guard.check)
        states = {j['origin']: j for j in rolling_journals if j['origin'] >= '2015-01-01'}
        old_predictions = {(p['store'], p['origin']): p for p in json.loads((rolling/'predictions-before-labels.json').read_bytes())}
        old_alpha = prior['selection']['calibration']['alpha']
        raw_dev, max_difference = {}, 0.
        stage = 'closed-rolling-state-forward-only'
        for text in sorted(states):
            indices = [k for k, (_, origin) in enumerate(keys) if origin == text]
            state = {k: torch.tensor(v, dtype=torch.bool if k == 'active' else torch.float64) for k, v in states[text]['state'].items()}
            b = torch.tensor([x[k]['baseline'] for k in indices], dtype=torch.float64)
            u = torch.tensor([scales[keys[k][0]] for k in indices], dtype=torch.float64)
            p = ridge_predict(torch.tensor([raw[k] for k in indices], dtype=torch.float64), b, u, state)
            for j, k in enumerate(indices):
                raw_dev[tuple(keys[k])] = p[j].tolist()
                old = old_predictions[tuple(keys[k])]
                reproduced = b[j]+old_alpha*(p[j]-b[j])
                max_difference = max(max_difference, max(abs(a-z) for a, z in zip(reproduced.tolist(), old['rolling_fixed'])))
            guard.check()
        if len(raw_dev) != 250 or max_difference > 1e-8:
            raise ValueError('saved rolling forward changed')
        raw_rows = []
        for k, (s, text) in enumerate(keys):
            old = old_predictions[s, text]; baseline = x[k]['baseline']
            if baseline != old['baseline'] or scales[s] != old['scale']:
                raise ValueError('development support/baseline changed')
            nn_fixed = [b+alphas['nn']['alpha']*(p-b) for p, b in zip(dev_nn[k].tolist(), baseline)]
            rolling_fixed = [b+alphas['rolling']['alpha']*(p-b) for p, b in zip(raw_dev[s, text], baseline)]
            choices = {'baseline': baseline, 'nn_calibrated': nn_fixed, 'rolling_calibrated': rolling_fixed}
            rows.append({'store': s, 'origin': text, 'scale': scales[s], 'baseline': baseline,
                         'candidate': choices[selected], 'incumbent': old['incumbent'],
                         'nn_fixed': nn_fixed, 'rolling_fixed': rolling_fixed,
                         'model_available': x[k]['available'], 'input_reasons': x[k]['reasons']})
            raw_rows.append({'store': s, 'origin': text, 'raw_nn': dev_nn[k].tolist(), 'raw_rolling': raw_dev[s, text]})
        files.json('development-raw-predictions.json', raw_rows)
        files.json('predictions-before-labels.json', rows)
        stage = 'fixed-development-label-attachment'
        old_labels = {(p['store'], p['origin']): p for p in json.loads((dev/'predictions-and-labels.json').read_bytes())}
        labelled = []
        for row in rows:
            old = old_labels[row['store'], row['origin']]
            actual = [dev_history[row['store']].get(dt.date.fromisoformat(row['origin'])+dt.timedelta(days=j)) for j in range(14)]
            if actual != old['actual'] or all(v is not None for v in actual) != old['complete_label']:
                raise ValueError('original development label/mask changed')
            labelled.append(row | {'actual': actual, 'complete_label': old['complete_label']})
        files.json('predictions-and-labels.json', labelled)
        measured = development_metrics(labelled, scales)
        comparators = {name: development_metrics([{**r, 'candidate': r[field]} for r in labelled], scales)
                       for name, field in (('nn_calibrated', 'nn_fixed'), ('rolling_calibrated', 'rolling_fixed'))}
        if measured['requested'] != 250 or measured['complete_label_windows'] != 240:
            raise ValueError('development label support changed')
        if ({k: verify(p) for k, p in roots.items()} != closures
                or any((REPO/p).read_bytes() != raw for p, raw in sources.items())):
            raise ValueError('closed source/root changed')
        summary = {'status': 'complete', 'selection': selection, 'source_roots': closures,
                   'source_pins': {p: pin(r) for p, r in sources.items()}, 'new_nn_trajectories': 1,
                   'new_ridge_fits': 0, 'closed_rolling_pools_checked': 37, 'rolling_reproduction_max_abs': max_difference,
                   'fixed_comparators': comparators, 'resources': guard.check(), 'seconds': time.monotonic()-STARTED,
                   'adopted': False, 'formal_permission': False, **measured}
        files.json('summary.json', summary); status = 'complete'
        print(json.dumps({'status': status, 'selection': selection, 'macro': measured['macro'],
                         'decision': measured['primary_development_decision'], 'seconds': summary['seconds']}), flush=True)
    except BaseException as error:
        files.json('failure.json', {'stage': stage, 'type': type(error).__name__, 'message': str(error),
                                  'traceback': traceback.format_exc()}, True)
        files.json('failure-prefix.json', {'journal': journal, 'curve': curve, 'rows': rows}, True)
        if best:
            files.state('failure-best.pt', best, True)
        raise
    finally:
        files.json('root-closed.json', {'status': status, 'files': files.pins.copy(), 'immutable': True,
                                     'formal_permission': False}, True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
