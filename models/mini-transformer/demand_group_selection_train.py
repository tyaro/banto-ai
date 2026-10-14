"""One new trajectory; two internal selections frozen before known development."""
import time
STARTED = time.monotonic()
from pathlib import Path
import argparse
import csv
import datetime as dt
import io
import json
import math
import random
import sys
import traceback
import torch

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO/'tools'))
from demand_group_selection import FIT, GROUP_C, POSITIVE, cohort_split, DualSelector, progress
from demand_training_adequacy import split_keys
from demand_public_calendar import build_inputs, fit_support
from demand_statistical_feature_model import StatisticalFeatureMean
from demand_statistical_feature_train import model_inputs
from demand_statistical_feature_validate import AsOfHistory
from demand_calendar_train import Files, pin, error_metrics
from demand_calendar_model import mean_loss
from store_sales_final import private_memory

CONTRACT = 'docs/research/demand-group-selection-design-2026-10-14.md'
EXTRA_SOURCES = ['models/mini-transformer/demand_group_selection_train.py',
                 'tools/demand_group_selection.py', 'tests/test_demand_group_selection.py', CONTRACT]
TRAIN_PINS = {
    'selected-2013-14.csv': {'bytes': 327118, 'sha256': 'b3fffdae4a4a560b9575461469c5d4755c0b69b065bb029d514519251ac027b1'},
    'split-scale-and-support.json': {'bytes': 20623, 'sha256': '4d05f9a77802c16102f09c1fd5ded72e7ac8000b6d9132bc99337d8edb8f1038'},
    'input-ledger.json': {'bytes': 506868, 'sha256': 'a13fb0edee312eacb8aec19f091fe0c8e0fd28517dee0251cb8a15e8f3c60f1f'},
    'summary.json': {'bytes': 4215, 'sha256': '939c8304db03e16abcebeb2082ee21d759d0e67719d722a47c5bcfacdbac604a'}}
EVAL_PINS = {
    'selected-2014-context-2015.csv': {'bytes': 76877, 'sha256': 'c2c54a5e1b8cc112466b62ae7105c24309442d69fd05bbd0f62b1c96a81af4f3'},
    'new-series-profiles.json': {'bytes': 706631, 'sha256': 'e1ec112ffb664ccca632a8eb4f6ab7ef6067243683e6e96d5346089dddb77f92'},
    'preperiod-scales-before-targets.json': {'bytes': 707, 'sha256': '8e85a1a8089157dce088f52fa2af447076b6e65e7d61e96b88774254be5d2f7b'},
    'predictions-before-labels.json': {'bytes': 119404, 'sha256': '85b15801b16d8a0c0413ed7b54f1b3fc0f36aced3b0555dd96e31b267b7127b7'},
    'summary.json': {'bytes': 15402, 'sha256': 'b8d012bc5de7c33631b3e2fb7e69f26eb56455fbed528d813db755af2649b08a'}}


def inventory(root):
    return {p.name: {'bytes': p.stat().st_size, 'mtime_ns': p.stat().st_mtime_ns,
                     'inode': p.stat().st_ino} for p in root.iterdir()}


def saved(root, closure, name, expected):
    assert closure['files'][name] == expected and (root/name).stat().st_size == expected['bytes']
    raw = (root/name).read_bytes()
    assert pin(raw) == expected
    return raw


def parse_history(raw, stores, cutoff):
    histories = {s: {} for s in stores}
    for row in csv.DictReader(io.StringIO(raw.decode('utf-8'))):
        s, day = int(row['store_nbr']), dt.date.fromisoformat(row['date'])
        if s not in histories or day >= cutoff:
            raise ValueError('saved snapshot metadata outside fixed scope')
        assert day not in histories[s] and row['observed'] in ('0', '1')
        assert (row['observed'] == '1') == bool(row['sales'])
        value = float(row['sales']) if row['observed'] == '1' else None
        assert value is None or (math.isfinite(value) and value >= 0)
        histories[s][day] = value
    return histories


def run(output):
    root = Path(output).absolute()
    if root.parent != REPO/'artifacts' or root.exists():
        raise ValueError('fresh model output root required')
    files = Files(root)
    status, stage, peak = 'failed', 'pre-input-contract', 0
    journal, curve, rows = [], [], []
    model = None
    best_states = {}

    def checkpoint():
        nonlocal peak
        peak = max(peak, private_memory())
        if peak > 2*1024**3 or time.monotonic()-STARTED > 870:
            raise RuntimeError('execution checkpoint; preserve and stop')

    try:
        prior = REPO/'artifacts/representative-demand-training-adequacy-20261014'
        eval_prior = REPO/'artifacts/representative-demand-selected-series-20261014'
        prior_inventory, eval_inventory = inventory(prior), inventory(eval_prior)
        prior_closure_raw = (prior/'root-closed.json').read_bytes()
        eval_closure_raw = (eval_prior/'root-closed.json').read_bytes()
        old_closure, eval_closure = json.loads(prior_closure_raw), json.loads(eval_closure_raw)
        assert old_closure['status'] == eval_closure['status'] == 'complete'
        old_summary = json.loads(saved(prior, old_closure, 'summary.json', TRAIN_PINS['summary.json']))
        sources = {p: (REPO/p).read_bytes() for p in [*old_summary['source_pins'], *EXTRA_SOURCES]}
        for p, expected in old_summary['source_pins'].items():
            assert pin(sources[p]) == expected
        files.json('sources.json', {p: raw.decode('utf-8') for p, raw in sources.items()})
        files.json('config-before-input.json', {
            'group_A': [6, 10, 15, 19, 26], 'group_B': [7, 13, 17, 23, 27], 'group_C': list(GROUP_C),
            'seed': 20261014, 'upper_steps': 4096, 'batch': 8, 'interval': 128,
            'stopping_grace': 512, 'patience': 6, 'min_relative': 1e-4, 'stop_monitor': 'transfer_validation',
            'primary_selection': 'transfer_selected', 'provisional_minimum_joint_improvement_percent': 2.0,
            'old_weights_loaded': False, 'one_training_trajectory': True,
            'train_expected_pins': TRAIN_PINS, 'eval_expected_pins': EVAL_PINS,
            'old_train_closure_pin': pin(prior_closure_raw), 'old_eval_closure_pin': pin(eval_closure_raw),
            'source_pins': {p: pin(raw) for p, raw in sources.items()},
            'compute_parent_head': 'f52513cc80bb19511eb42ab36003c8e55e40b59e',
            'uncommitted_new_sources': True, 'python': sys.version, 'torch': torch.__version__,
            'formal_permission': False, 'previously_read_development': True})
        torch.set_num_threads(2)
        torch.set_num_interop_threads(1)
        torch.use_deterministic_algorithms(True)
        checkpoint()
        stage = 'internal-snapshot-binding'
        raw_train = {name: saved(prior, old_closure, name, expected)
                     for name, expected in TRAIN_PINS.items() if name != 'summary.json'}
        old_split = json.loads(raw_train['split-scale-and-support.json'])
        original_keys = old_split['split']['train'] + old_split['split']['validation']
        parts = cohort_split(original_keys)
        assert len(parts['fit']) == 300 and len(parts['time_validation']) == 120
        assert len(parts['transfer_validation']) == 60 and len(parts['unused_C_preperiod']) == 150
        scales = {int(s): meta['scale'] for s, meta in old_split['scale_metadata'].items()}
        assert all(scales[s] > 0 for s in POSITIVE)
        ledger = json.loads(raw_train['input-ledger.json'])
        lookup = {(r['store'], r['origin']): r for r in ledger}
        assert len(lookup) == 630 and set(lookup) == set(map(tuple, original_keys))
        histories = parse_history(raw_train['selected-2013-14.csv'], POSITIVE, dt.date(2015, 1, 1))
        masks = {(s, day): value is not None for s, history in histories.items() for day, value in history.items()}
        support = fit_support([(s, dt.date.fromisoformat(d)) for s, d in parts['fit']], masks, dt.date(2014, 7, 1))
        assert support['keys'] == 300
        assert all(not r['enabled'] or old for r, old in zip(support['channels'], old_split['support']['enabled']))
        files.json('split-scale-and-support.json', {
            'groups': parts, 'scale_metadata_reused': old_split['scale_metadata'], 'support': support,
            'C_preperiod_parameter_fit': False, 'profiles_recalculated': 0})
        files.json('train-input-binding.json', {
            'original_closure_pin': pin(prior_closure_raw), 'input_pins': TRAIN_PINS,
            'original_inventory': prior_inventory, 'input_getter_days': 56,
            'scale_period': '2013-01-01 <= date < 2014-07-01', '2015_quantity_read': False})
        internal, declared = {}, []
        for name in ('fit', 'time_validation', 'transfer_validation'):
            inputs, encoded, labels = [], [], []
            for s, text in parts[name]:
                origin = dt.date.fromisoformat(text)
                old_row = lookup[s, text]
                assert old_row['scale'] == scales[s] and old_row['encoded']['origin'] == text
                past = AsOfHistory(histories[s], origin)
                x = build_inputs(past, origin, scales[s], 'pre_post', support['enabled'])
                assert x['available']
                actual = [histories[s].get(origin+dt.timedelta(days=k)) for k in range(14)]
                assert actual == old_row['actual'] and all(v is not None for v in actual)
                inputs.append(x)
                encoded.append(old_row['encoded'])
                labels.append(actual)
                declared.append({'split': name, 'store': s, 'origin': text, 'scale': scales[s],
                                 'actual': actual, 'encoded': old_row['encoded'],
                                 'accessed_min': min(past.accessed), 'accessed_max': max(past.accessed)})
            internal[name] = {'inputs': model_inputs(inputs, encoded), 'actual': torch.tensor(labels, dtype=torch.float32),
                              'mask': torch.ones((len(labels), 14), dtype=torch.bool), 'keys': parts[name]}
        assert not set(s for s, _ in internal['fit']['keys']).intersection(GROUP_C)
        files.json('internal-input-ledger.json', declared)
        rng = random.Random(20261014)
        sampler = [[rng.randrange(300) for _ in range(8)] for _ in range(4096)]
        files.json('sampler.json', {'indices': sampler, 'fit_keys': parts['fit'], 'uniform_fixed_windows': True})
        torch.manual_seed(20261014)
        model = StatisticalFeatureMean()
        initial = {k: v.detach().clone() for k, v in model.state_dict().items()}
        files.state('initial.pt', initial)
        optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, betas=(.9, .999), eps=1e-8,
                                      weight_decay=.01, foreach=False, fused=False)
        selector = DualSelector()

        def fixed_metrics(name):
            dataset = internal[name]
            scores = {s: [] for s, _ in dataset['keys']}
            previous_mode = model.training
            model.eval()
            with torch.no_grad():
                for start in range(0, len(dataset['keys']), 8):
                    end = min(start+8, len(dataset['keys']))
                    x = [v[start:end] for v in dataset['inputs']]
                    daily, total = model(*x)
                    actual, u = dataset['actual'][start:end], x[-2]
                    ds = ((daily-actual)/u[:, None]).square().mean(1)
                    ts = ((total-actual.sum(1))/(14*u)).square()
                    for j, (s, _) in enumerate(dataset['keys'][start:end]):
                        scores[s].append((ds[j].item(), ts[j].item()))
                    checkpoint()
            model.train(previous_mode)
            by_store = {str(s): {'daily': math.fsum(v[0] for v in values)/len(values),
                                'total': math.fsum(v[1] for v in values)/len(values), 'windows': len(values)}
                        for s, values in scores.items()}
            daily = math.fsum(v['daily'] for v in by_store.values())/len(by_store)
            total = math.fsum(v['total'] for v in by_store.values())/len(by_store)
            return {'daily': daily, 'total': total, 'joint': .5*(daily+total), 'per_store': by_store}

        def observe(step):
            measured = {name: fixed_metrics(name) for name in internal}
            chosen = selector.observe(step, measured['time_validation']['joint'], measured['transfer_validation']['joint'])
            for name, flag in (('time_selected', 'time_new_best'), ('transfer_selected', 'transfer_new_best')):
                if chosen[flag]:
                    best_states[name] = {k: v.detach().clone() for k, v in model.state_dict().items()}
            curve.append({'step': step, **measured, 'selection': chosen})
            print(json.dumps({'step': step, 'fit': measured['fit']['joint'],
                              'time_validation': measured['time_validation']['joint'],
                              'transfer_validation': measured['transfer_validation']['joint'], **chosen}), flush=True)
            return chosen['stop']

        stage = 'one-new-training-trajectory'
        observe(0)
        model.train()
        stop_reason = 'step_cap'
        for step, indices in enumerate(sampler, 1):
            dataset = internal['fit']
            x = [v[indices] for v in dataset['inputs']]
            optimizer.zero_grad(set_to_none=True)
            loss, components = mean_loss(*model(*x), dataset['actual'][indices], dataset['mask'][indices], x[-2])
            if not bool(torch.isfinite(loss)):
                raise RuntimeError('nonfinite training loss')
            loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
            optimizer.step()
            journal.append({'step': step, 'loss': loss.item(), 'norm': norm.item(), **components})
            checkpoint()
            if step in (1024, 2048):
                files.json('training-prefix-'+str(step)+'.json', {'journal': journal, 'curve': curve})
            if step % 128 == 0 and observe(step):
                stop_reason = 'transfer_early_stop'
                break
        files.state('final.pt', model.state_dict())
        for name, state in best_states.items():
            files.state(name+'.pt', state)
        files.json('training-journal.json', journal)
        files.json('selection-curve.json', curve)
        same_state = all(torch.equal(best_states['time_selected'][k], best_states['transfer_selected'][k])
                         for k in best_states['time_selected'])
        selection = {'steps': step, 'stop_reason': stop_reason, 'time_best_step': selector.time_best_step,
                     'time_best_loss': selector.time_best, 'transfer_best_step': selector.transfer.best_step,
                     'transfer_best_loss': selector.transfer.best, 'same_state': same_state,
                     'selected_weights': {name: files.pins[name+'.pt'] for name in best_states},
                     'development_quantity_interpreted': False, 'no_further_weight_selection': True}
        files.json('selection-frozen-before-development.json', selection)
        frozen_weights = {name: (root/(name+'.pt')).read_bytes() for name in best_states}
        checkpoint()
        stage = 'known-development-input-reuse'
        # Development payload is not interpreted until both selected states have been saved.
        raw_eval = {name: saved(eval_prior, eval_closure, name, expected) for name, expected in EVAL_PINS.items()}
        active, stores = (4, 8, 16, 24, 28), (4, 8, 16, 20, 24, 28)
        eval_scales = {int(s): r['scale'] for s, r in json.loads(raw_eval['preperiod-scales-before-targets.json'])['scale_metadata'].items()}
        assert eval_scales[20] == 0 and all(eval_scales[s] > 0 for s in active)
        eval_histories = parse_history(raw_eval['selected-2014-context-2015.csv'], stores, dt.date(2016, 1, 1))
        profiles = {(r['store'], r['origin']): r for r in json.loads(raw_eval['new-series-profiles.json'])}
        old_before = {(r['store'], r['origin']): r for r in json.loads(raw_eval['predictions-before-labels.json'])}
        dates = [dt.date(2015, 1, 13)+dt.timedelta(days=14*k) for k in range(25)]
        expected_keys = {(s, str(d)) for s in stores for d in dates}
        assert len(profiles) == len(old_before) == 150 and set(profiles) == set(old_before) == expected_keys
        files.json('development-input-binding.json', {
            'original_closure_pin': pin(eval_closure_raw), 'input_pins': EVAL_PINS,
            'original_inventory': eval_inventory, 'selected_weight_pins': selection['selected_weights'],
            'profiles_recalculated': 0, 'new_archive_or_quantity_extraction': False,
            'original_baseline_equality_required': True})
        pending = []
        for s in stores:
            for origin in dates:
                old_row, profile = old_before[s, str(origin)], profiles[s, str(origin)]
                past = AsOfHistory(eval_histories[s], origin)
                x = build_inputs(past, origin, eval_scales[s], 'pre_post', support['enabled'])
                assert x['baseline'] == old_row['baseline'] and x['available'] == old_row['model_available']
                assert old_row['scale'] == eval_scales[s] and profile['encoded']['origin'] == str(origin)
                assert profile['profile']['past_end'] == str(origin-dt.timedelta(days=1))
                baseline = x['baseline'] if None not in x['baseline'] else None
                rows.append({'store': s, 'origin': str(origin), 'scale': eval_scales[s], 'baseline': baseline,
                             'time_selected': baseline if s == 20 else None,
                             'transfer_selected': baseline if s == 20 else None,
                             'model_available': x['available'], 'input_reasons': x['reasons'],
                             'role': 'zero_scale_baseline_only' if s == 20 else 'positive_scale'})
                if s in active and x['available']:
                    pending.append((len(rows)-1, x, profile['encoded']))
        stage = 'frozen-development-forward'
        unique = ('time_selected',) if same_state else ('time_selected', 'transfer_selected')
        models = {}
        for name in unique:
            model = StatisticalFeatureMean()
            model.load_state_dict(best_states[name])
            assert all(torch.equal(v, best_states[name][k]) for k, v in model.state_dict().items())
            model.eval()
            models[name] = model
        with torch.no_grad():
            for start in range(0, len(pending), 8):
                batch = pending[start:start+8]
                inputs = model_inputs([x for _, x, _ in batch], [e for _, _, e in batch])
                for name, selected_model in models.items():
                    daily, total = selected_model(*inputs)
                    for j, (index, _, _) in enumerate(batch):
                        values = daily[j].tolist()
                        assert math.isclose(math.fsum(values), total[j].item(), rel_tol=1e-6, abs_tol=1e-5)
                        rows[index][name] = values
                        if same_state:
                            rows[index]['transfer_selected'] = values.copy()
                checkpoint()
        files.json('predictions-before-labels.json', rows)
        stage = 'labels-after-frozen-predictions'
        methods = ('baseline', 'time_selected', 'transfer_selected')
        for row in rows:
            origin = dt.date.fromisoformat(row['origin'])
            row['actual'] = [eval_histories[row['store']].get(origin+dt.timedelta(days=k)) for k in range(14)]
            row['complete_label'] = all(a is not None for a in row['actual'])
            row['comparable'] = all(row[m] is not None for m in methods)
        files.json('predictions-and-labels.json', rows)

        def metrics(rs, u):
            output = {}
            for method in methods:
                de, da, te, ta = [], [], [], []
                for row in rs:
                    if not row['comparable']:
                        continue
                    for p, a in zip(row[method], row['actual']):
                        if a is not None:
                            de.append(p-a)
                            da.append(a)
                    if row['complete_label']:
                        te.append(math.fsum(row[method])-math.fsum(row['actual']))
                        ta.append(math.fsum(row['actual']))
                output[method] = {'daily': error_metrics(de, da, [u]*len(de) if u else None),
                                  'total': error_metrics(te, ta, [14*u]*len(te) if u else None)}
            return output

        def group(rs):
            by_store = {str(s): metrics([r for r in rs if r['store'] == s], eval_scales[s]) for s in active}
            macro = {}
            for method in methods:
                daily = math.fsum(v[method]['daily']['scaled_MSE'] for v in by_store.values())/5
                total = math.fsum(v[method]['total']['scaled_MSE'] for v in by_store.values())/5
                macro[method] = {'daily': daily, 'total': total, 'joint': .5*(daily+total)}
            return by_store, macro

        stage = 'fixed-development-metrics'
        by_store, macro = group(rows)
        zero_metrics = metrics([r for r in rows if r['store'] == 20], 0)
        original_summary = json.loads(raw_eval['summary.json'])
        for s in active:
            for scope in ('daily', 'total'):
                assert by_store[str(s)]['baseline'][scope] == original_summary['per_store'][str(s)]['baseline'][scope]
        support_counts = {str(s): {'requested': 25, 'comparable': sum(r['store'] == s and r['comparable'] for r in rows),
                                   'complete_comparable': sum(r['store'] == s and r['comparable'] and r['complete_label'] for r in rows)}
                          for s in stores}
        support_ok = all(support_counts[str(s)]['comparable'] == 25 and support_counts[str(s)]['complete_comparable'] == 24 for s in active)
        assert all(v['comparable'] >= 20 and v['complete_comparable'] >= 20 for v in support_counts.values())
        decision = progress(macro['transfer_selected'], macro['baseline'], support_ok)
        store_joint = {s: {m: .5*(v[m]['daily']['scaled_MSE']+v[m]['total']['scaled_MSE']) for m in methods}
                       for s, v in by_store.items()}
        quarters = {str(q): group([r for r in rows if (dt.date.fromisoformat(r['origin']).month-1)//3+1 == q])[1] for q in range(1, 5)}
        sensitivity = {}
        for method in methods[1:]:
            full_difference = macro[method]['joint']-macro['baseline']['joint']
            leave_one = {s: math.fsum(v[method]-v['baseline'] for key, v in store_joint.items() if key != s)/4 for s in store_joint}
            sensitivity[method] = {'full_paired_difference': full_difference,
                                   'leave_one_store_macro_differences': leave_one,
                                   'range': [min(leave_one.values()), max(leave_one.values())],
                                   'confidence_interval': False, 'excluded_from_primary_decision': True}
        for name, raw in frozen_weights.items():
            assert (root/(name+'.pt')).read_bytes() == raw
            if name in models:
                assert all(torch.equal(v, best_states[name][k]) for k, v in models[name].state_dict().items())
        assert inventory(prior) == prior_inventory and inventory(eval_prior) == eval_inventory
        assert (prior/'root-closed.json').read_bytes() == prior_closure_raw
        assert (eval_prior/'root-closed.json').read_bytes() == eval_closure_raw
        assert all((REPO/p).read_bytes() == raw for p, raw in sources.items())
        checkpoint()
        summary = {'status': 'complete', 'research_state': 'PAUSED', 'adopted': False,
                   'one_training_trajectory': True, 'selection': selection,
                   'parameter_count': sum(p.numel() for p in model.parameters()),
                   'train_windows': 300, 'time_validation_windows': 120, 'transfer_validation_windows': 60,
                   'fit_stores': list(FIT), 'transfer_selection_stores': list(GROUP_C),
                   'calendar_enabled_channels': sum(support['enabled']), 'development_macro': macro,
                   'per_store': by_store, 'store_joint': store_joint, 'quarter_macro': quarters,
                   'support_counts': support_counts, 'zero_scale_metrics': zero_metrics, 'concentration_sensitivity': sensitivity,
                   'development_decision': decision, 'requested': len(rows), 'neural_supported': len(pending),
                   'baseline_only_windows': 25, 'complete_label_windows': sum(r['complete_label'] for r in rows),
                   'unique_forward_states': len(unique), 'same_state_prediction_reuse': same_state,
                   'old_source_and_roots_unchanged': True, 'old_models_replayed': False, 'old_profiles_recalculated': 0,
                   'source_pins': {p: pin(raw) for p, raw in sources.items()}, 'input_pins': {'train': TRAIN_PINS, 'evaluation': EVAL_PINS},
                   'previously_read_development': True, 'unknown_confirmation': False, 'convergence_certified': False,
                   'formal_permission': False, 'reserved_holdout_or_2016_2017_read': False,
                   'seconds': time.monotonic()-STARTED, 'OS_peak_private_bytes': peak}
        files.json('summary.json', summary)
        status = 'complete'
        print(json.dumps({k: summary[k] for k in ('status', 'research_state', 'selection', 'development_macro',
            'development_decision', 'unique_forward_states', 'seconds', 'OS_peak_private_bytes')}), flush=True)
    except BaseException as error:
        original_trace = traceback.format_exc()
        try:
            files.json('failure.json', {'stage': stage, 'type': type(error).__name__, 'message': str(error),
                                       'traceback': original_trace, 'research_state': 'PAUSED'}, True)
            files.json('failure-journal-curve.json', {'journal': journal, 'curve': curve}, True)
            if rows:
                files.json('failure-prediction-prefix.json', rows, True)
            if model is not None:
                files.state('failure-model-prefix.pt', model.state_dict(), True)
            for name, state in best_states.items():
                files.state('failure-'+name+'.pt', state, True)
        except BaseException as save_error:
            print('failure save error: '+repr(save_error), file=sys.stderr)
        raise
    finally:
        files.json('root-closed.json', {'status': status, 'files': files.pins.copy(), 'immutable': True}, status != 'complete')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    run(parser.parse_args().output)
