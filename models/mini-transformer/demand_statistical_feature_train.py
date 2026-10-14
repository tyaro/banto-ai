"""Fixed-budget matched learned-feature pair; no work runs on import."""
import time
STARTED = time.monotonic()
from pathlib import Path
import argparse, csv, datetime as dt, io, json, math, random, sys, traceback, platform
import torch
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'tools'))
from verification_records import verify_record
from store_sales_final import private_memory
from demand_public_calendar import build_inputs
from demand_statistical_overlay import describe_history
from demand_statistical_features import encode_profile, COLUMNS
from demand_statistical_feature_model import StatisticalFeatureMean
from demand_calendar_train import Files, pin, item, tensors, error_metrics, ACTIVE, ZERO, STORES
from demand_calendar_model import mean_loss

SOURCES = ['models/mini-transformer/demand_statistical_feature_train.py',
 'models/mini-transformer/demand_statistical_feature_model.py',
 'models/mini-transformer/demand_calendar_train.py', 'models/mini-transformer/demand_calendar_model.py',
 'tools/demand_statistical_features.py', 'tools/demand_statistical_overlay.py',
 'tools/demand_public_calendar.py', 'tools/demand_weekly_history.py',
 'tools/verification_records.py', 'tools/store_sales_final.py',
 'docs/research/demand-statistical-feature-input-design-2026-10-14.md']


def saved(root, closure, name):
    raw = (root / name).read_bytes()
    assert pin(raw) == closure['files'][name]
    return raw


def read_selection(raw, stores, allowed, cutoff):
    histories = {s: {} for s in stores}
    for row in csv.DictReader(io.StringIO(raw.decode())):
        s, day = int(row['store_nbr']), dt.date.fromisoformat(row['date'])
        if s not in stores or day not in allowed or day >= cutoff:
            raise ValueError('saved selection scope mismatch before numeric quantity')
        assert day not in histories[s] and row['observed'] in ('0', '1')
        assert (row['observed'] == '1') == bool(row['sales'])
        histories[s][day] = float(row['sales']) if row['observed'] == '1' else None
    assert all(set(h) == allowed for h in histories.values())
    return histories


def model_inputs(inputs, encodings):
    return tensors(inputs) + [torch.tensor([e['features'] for e in encodings], dtype=torch.float32)]


def without_features(full):
    # Calendar, values, masks, scale and model shape remain identical on both sides.
    return full[:-1] + [torch.zeros_like(full[-1])]


def run(output):
    root = Path(output).absolute()
    if root.parent != REPO / 'artifacts' or root.exists():
        raise ValueError('fresh local output root required')
    files = Files(root)
    status, stage, journal, model, peak = 'failed', 'source', [], None, 0
    def checkpoint():
        nonlocal peak
        peak = max(peak, private_memory())
        if peak > 2 * 1024**3 or time.monotonic() - STARTED > 870:
            raise RuntimeError('execution checkpoint; preserve and stop')
    try:
        sources = {p: (REPO / p).read_bytes() for p in SOURCES}
        files.json('sources.json', {p: r.decode('utf-8') for p, r in sources.items()})
        files.json('config.json', {'seed': 20261014, 'steps': 256, 'batch': 8,
          'control': 'feature_off', 'candidate': 'feature_on', 'columns': COLUMNS,
          'calendar_both': 'pre_post, same saved enabled42', 'same_initial_and_sampler': True,
          'selection': 'final step256, no development selection', 'cutoff': '2015-01-01',
          'retrospective_development': 2015, 'formal_permission': False,
          'progress_contract': 'positive15 macro joint MSE below both control and saved mean28; >=10 stores below both',
          'source_pins': {p: pin(r) for p, r in sources.items()}, 'uncommitted_new_sources': True,
          'compute_parent_head': '633e2732f9787cceec007dda2cb24f90b468c4d9',
          'runtime': {'python': sys.version, 'torch': torch.__version__, 'platform': platform.platform()}})
        torch.set_num_threads(2); torch.set_num_interop_threads(1)
        torch.use_deterministic_algorithms(True); checkpoint()
        prior = REPO / 'artifacts/representative-demand-public-calendar-input-20261014-records'
        assert verify_record(prior)['status'] == 'failed'  # Completed support; original document failure retained.
        support_raw, binding_raw = item(prior, 'fit-support'), item(prior, 'input-binding')
        support, binding = json.loads(support_raw), json.loads(binding_raw)
        assert sum(support['enabled']) == 42 and binding['active'] == list(ACTIVE)
        keys = [(s, dt.date.fromisoformat(d)) for s, d in binding['fit_keys']]
        dates = [dt.date.fromisoformat(d) for d in binding['development_dates']]
        scales = {int(s): float(u) for s, u in binding['fit_scale_text'].items()}
        assert len(keys) == 630 and len(set(keys)) == 630 and len(dates) == 25
        assert all(scales[s] > 0 for s in ACTIVE) and all(scales[s] == 0 for s in ZERO)
        pair = REPO / 'artifacts/representative-demand-calendar-pair-20261014'
        closure_raw = (pair / 'root-closed.json').read_bytes(); closure = json.loads(closure_raw)
        assert closure['status'] == 'complete'
        fit_raw = saved(pair, closure, 'fit-selection.csv')
        assert json.loads(saved(pair, closure, 'fit-keys.json')) == binding['fit_keys']
        files.json('binding.json', {'support_pin': pin(support_raw), 'binding_pin': pin(binding_raw),
          'prior_closure': pin((prior / 'root-closed.json').read_bytes()), 'calendar_pair_closure': pin(closure_raw),
          'saved_fit_selection_pin': pin(fit_raw), 'snapshot_pin_reused': binding['snapshot_pin'],
          'scales': scales, 'development_dates': [str(d) for d in dates], 'old_weights_loaded': False})
        files.json('fit-keys.json', binding['fit_keys']); files.write('fit-selection.csv', fit_raw)
        wanted = {d + dt.timedelta(days=k) for s, d in keys for k in range(-56, 14)}
        histories = read_selection(fit_raw, ACTIVE, wanted, dt.date(2015, 1, 1))
        inputs, encodings, labels, fit_profiles = [], [], [], []
        stage = 'assemble-fit-statistics'
        for i, (s, origin) in enumerate(keys):
            x = build_inputs(histories[s], origin, scales[s], 'pre_post', support['enabled'])
            assert x['available']
            profile = describe_history(histories[s], origin)
            encoded = encode_profile(profile, origin, scales[s])
            values = [histories[s].get(origin + dt.timedelta(days=k)) for k in range(14)]
            assert all(v is not None for v in values)
            inputs.append(x); encodings.append(encoded); labels.append(values)
            fit_profiles.append({'store': s, 'origin': str(origin), 'profile': profile, 'encoded': encoded})
            if i % 32 == 0: checkpoint()
        files.json('fit-statistics.json', fit_profiles)
        full = model_inputs(inputs, encodings); control = without_features(full)
        del inputs, encodings, fit_profiles, histories
        y = torch.tensor(labels, dtype=torch.float32); mask = torch.ones_like(y, dtype=torch.bool)
        sampler = random.Random(20261014)
        schedule = [[sampler.randrange(len(keys)) for _ in range(8)] for _ in range(256)]
        files.json('sampler.json', {'indices': schedule, 'fit_keys_pin': files.pins['fit-keys.json']})
        torch.manual_seed(20261014); initial_model = StatisticalFeatureMean()
        initial = {k: v.detach().clone() for k, v in initial_model.state_dict().items()}
        parameters = sum(p.numel() for p in initial_model.parameters()); assert parameters == 30369
        files.state('initial.pt', initial); del initial_model
        trained, final_loss = {}, {}
        for mode, data in (('feature_off', control), ('feature_on', full)):
            stage = 'train-' + mode; model = StatisticalFeatureMean(); model.load_state_dict(initial)
            assert all(torch.equal(v, initial[k]) for k, v in model.state_dict().items())
            optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, betas=(.9, .999), eps=1e-8,
                                         weight_decay=.01, foreach=False, fused=False)
            journal = []; model.train()
            for step, indices in enumerate(schedule, 1):
                x = [v[indices] for v in data]; optimizer.zero_grad(set_to_none=True)
                loss, parts = mean_loss(*model(*x), y[indices], mask[indices], x[-2])
                if not bool(torch.isfinite(loss)): raise RuntimeError('nonfinite training loss')
                loss.backward(); norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
                optimizer.step(); journal.append({'step': step, 'loss': loss.item(), 'norm': norm.item(), **parts})
                checkpoint()
                if step in (64, 128, 192): files.json(mode + '-prefix-' + str(step) + '.json', journal)
            files.state(mode + '-final.pt', model.state_dict()); files.json(mode + '-journal.json', journal)
            final_loss[mode] = journal[-1]['loss']; model.eval(); trained[mode] = model
            print(json.dumps({'mode': mode, 'steps': 256, 'last_training_loss': final_loss[mode]}), flush=True)
        del full, control, y, mask, optimizer
        # No 2015 quantities or statistical payloads have been read before both final weights exist.
        checkpoint(); stage = 'development-after-both-weights'
        dev_raw = saved(pair, closure, 'development-selection.csv')
        files.write('development-selection.csv', dev_raw)
        wanted = {d + dt.timedelta(days=k) for d in dates for k in range(-56, 14)}
        histories = read_selection(dev_raw, STORES, wanted, dt.date(2016, 1, 1))
        original_raw = saved(pair, closure, 'predictions.json'); original_rows = json.loads(original_raw)
        old_summary_raw = saved(pair, closure, 'summary.json'); old_summary = json.loads(old_summary_raw)
        overlay = REPO / 'artifacts/representative-demand-statistical-overlay-20261014-records'
        assert verify_record(overlay)['status'] == 'complete'
        profile_raw = item(overlay, 'new-overlay-ledger'); profiles = json.loads(profile_raw)
        profile_lookup = {(r['store'], r['origin']): r for r in profiles}
        originals = {(r['store'], r['origin']): r for r in original_rows}
        assert len(profiles) == len(profile_lookup) == len(originals) == 450
        rows, pending, dev_features = [], [], []
        for s in STORES:
            for origin in dates:
                x = build_inputs(histories[s], origin, scales[s], 'pre_post', support['enabled'])
                prior_row = originals[s, str(origin)]; profile_row = profile_lookup[s, str(origin)]
                target = [histories[s].get(origin + dt.timedelta(days=k)) for k in range(14)]
                assert x['baseline'] == prior_row['baseline'] and target == prior_row['actual'] == profile_row['actual']
                assert scales[s] == prior_row['scale'] == profile_row['scale']
                assert pin(json.dumps(prior_row['baseline'], allow_nan=False, sort_keys=True).encode()) == profile_row['baseline_pin']
                encoded = encode_profile(profile_row['profile'], origin, scales[s])
                row = {'store': s, 'origin': str(origin), 'scale': scales[s], 'baseline': prior_row['baseline'],
                       'actual': target, 'feature_off': prior_row['baseline'], 'feature_on': prior_row['baseline'],
                       'model_available': x['available'], 'input_reasons': x['reasons'],
                       'role': 'positive_scale' if s in ACTIVE else 'zero_scale_baseline_only'}
                rows.append(row); dev_features.append({'store': s, 'origin': str(origin), 'encoded': encoded})
                if s in ACTIVE and x['available']: pending.append((len(rows) - 1, x, encoded))
        files.json('development-features.json', {'profile_source_pin': pin(profile_raw),
          'profile_closure_pin': pin((overlay / 'root-closed.json').read_bytes()),
          'saved_predictions_pin': pin(original_raw), 'saved_baseline_summary_pin': pin(old_summary_raw), 'rows': dev_features})
        with torch.no_grad():
            for start in range(0, len(pending), 8):
                batch = pending[start:start + 8]
                full = model_inputs([x for i, x, e in batch], [e for i, x, e in batch]); control = without_features(full)
                for mode, data in (('feature_off', control), ('feature_on', full)):
                    daily, total = trained[mode](*data)
                    for j, (index, x, e) in enumerate(batch):
                        values = daily[j].tolist()
                        assert math.isclose(math.fsum(values), total[j].item(), rel_tol=1e-6, abs_tol=1e-5)
                        rows[index][mode] = values
                checkpoint()
        files.json('predictions.json', rows); stage = 'new-model-metrics'
        methods = ('baseline', 'feature_off', 'feature_on'); by_store = {}
        for s in STORES:
            # Baseline metrics are copied, not rescored or selected anew.
            by_store[str(s)] = {'baseline': old_summary['per_store'][str(s)]['baseline']}
            for method in methods[1:]:
                de, da, te, ta = [], [], [], []
                for row in rows:
                    if row['store'] != s or row[method] is None: continue
                    for p, a in zip(row[method], row['actual']):
                        if a is not None: de.append(p - a); da.append(a)
                    if all(a is not None for a in row['actual']):
                        te.append(math.fsum(row[method]) - math.fsum(row['actual'])); ta.append(math.fsum(row['actual']))
                by_store[str(s)][method] = {'daily': error_metrics(de, da, [scales[s]] * len(de) if scales[s] > 0 else None),
                  'total': error_metrics(te, ta, [14 * scales[s]] * len(te) if scales[s] > 0 else None)}
                assert all(by_store[str(s)][method][scope]['count'] == by_store[str(s)]['baseline'][scope]['count'] for scope in ('daily', 'total'))
        store_joint = {str(s): {m: .5 * sum(by_store[str(s)][m][scope]['scaled_MSE'] for scope in ('daily', 'total'))
                                for m in methods} for s in ACTIVE}
        primary = {m: math.fsum(store_joint[str(s)][m] for s in ACTIVE) / len(ACTIVE) for m in methods}
        secondary = {scope: {m: math.fsum(by_store[str(s)][m][scope]['scaled_MSE'] for s in ACTIVE) / len(ACTIVE)
                            for m in methods} for scope in ('daily', 'total')}
        improved = [s for s in ACTIVE if all(store_joint[str(s)]['feature_on'] < store_joint[str(s)][m] for m in methods[:2])]
        progress = all(primary['feature_on'] < primary[m] for m in methods[:2]) and len(improved) >= 10
        checkpoint(); assert all((REPO / p).read_bytes() == r for p, r in sources.items())
        result = {'status': 'complete', 'progress_passed': progress, 'adopted': False, 'parameters': parameters,
          'primary_joint_macro_scaled_MSE': primary, 'secondary_macro_scaled_MSE': secondary,
          'store_joint_MSE': store_joint, 'improved_stores': improved, 'per_store': by_store, 'requested': len(rows),
          'model_supported': len(pending), 'complete_label_windows': sum(all(a is not None for a in r['actual']) for r in rows),
          'zero_scale_baseline_only_windows': sum(r['store'] in ZERO for r in rows),
          'source_pins': {p: pin(r) for p, r in sources.items()}, 'initial_pin': files.pins['initial.pt'],
          'sampler_pin': files.pins['sampler.json'], 'same_initial_sampler': True, 'final_training_loss': final_loss,
          'new_fit_profiles': len(keys), 'saved_development_profiles': len(profiles), 'old_weights_or_models_replayed': False,
          'feature_projection_weight_norm': {m: trained[m].residual_statistics.weight.norm().item() for m in methods[1:]},
          'seconds': time.monotonic() - STARTED, 'OS_peak_private_bytes': peak, 'formal_permission': False,
          'registered_holdout_read': False, '2016_2017_reserved_read': False, 'retrospective_2015': True,
          'new_year_christmas_fit_support': False, 'no_same_hypothesis_grid_on_failure': True}
        files.json('summary.json', result); status = 'complete'
        print(json.dumps({k: result[k] for k in ('status', 'progress_passed', 'primary_joint_macro_scaled_MSE',
                          'improved_stores', 'requested', 'model_supported', 'seconds', 'OS_peak_private_bytes')}), flush=True)
    except BaseException as error:
        original = traceback.format_exc()
        try:
            files.json('failure.json', {'stage': stage, 'type': type(error).__name__, 'message': str(error), 'traceback': original}, True)
            files.json('failure-journal.json', journal, True)
            if model is not None: files.state('failure-prefix.pt', model.state_dict(), True)
        except BaseException as save_error:
            print('failure save error: ' + repr(save_error), file=sys.stderr)
        raise
    finally:
        files.json('root-closed.json', {'status': status, 'files': files.pins.copy(), 'immutable': True}, status != 'complete')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output', required=True)
    run(parser.parse_args().output)
