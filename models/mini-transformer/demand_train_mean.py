"""One fixed bounded demand pilot. Explicit execution trains one fresh model."""
import time
STARTED = time.monotonic()
import argparse
import datetime as dt
from io import BytesIO
import hashlib
import json
from pathlib import Path
import platform
import math
import sys
import traceback
import torch

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO/'tools'))
from verification_records import verify_record
from store_sales_final import private_memory
from demand_forecasting import metrics
from train import Files
from demand_data_inputs import STORES, load_snapshot
from demand_model_mean import DemandMeanForecaster, loss_parts

SOURCES = ['models/mini-transformer/'+p for p in
           ('demand_train_mean.py', 'demand_data_inputs.py', 'demand_model_mean.py', 'check_demand_mean.py',
            'demand_model_inputs.py',
            'demand_data.py', 'demand_model.py', 'small_model.py', 'train.py', 'data.py', 'check_model.py')]
SOURCES += ['tools/verification_records.py', 'tools/store_sales_final.py', 'tools/demand_forecasting.py',
            'docs/research/store-sales-mean-pilot-design-2026-10-14.md',
            'tools/demand_input_features.py', 'tests/test_demand_input_features.py']


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def item(root, manifest, label):
    return b''.join((root/p['path']).read_bytes() for p in manifest['items'][label]['parts'])


def run(output):
    output = Path(output).absolute()
    if output.parent != REPO/'artifacts' or output.exists():
        raise ValueError('fresh local model root required')
    files = Files(output); journal = []; best = None; peak = 0; stage = 'source'
    def checkpoint():
        nonlocal peak
        peak = max(peak, private_memory())
        if peak > 2*1024**3 or time.monotonic()-STARTED > 870:
            raise RuntimeError('execution checkpoint exceeded; preserve and stop')
    try:
        raw_sources = {p: (REPO/p).read_bytes() for p in SOURCES}
        files.json('sources.json', {p: r.decode('utf-8') for p, r in raw_sources.items()})
        files.json('config.json', {'init_seed': 20261014, 'sampler_seed': 20261015, 'steps': 256,
            'batch': 8, 'point_estimand': 'mean-target head', 'selection_objective': 'validation mean MSE', 'quantile_loss_weight': .25, 'sampler': 'original saved batch dates reused', 'validation_steps': [64, 128, 192, 256], 'future_realized_covariates': False,
            'source_pins': {p: pin(r) for p, r in raw_sources.items()}, 'formal_permission': False})
        torch.set_num_threads(2); torch.set_num_interop_threads(1); torch.use_deterministic_algorithms(True)
        checkpoint(); stage = 'prepare'
        data, binding = load_snapshot(REPO)
        files.json('input.json', {'binding': binding, **data.description()})
        schedule = data.schedule()
        torch.manual_seed(20261014); model = DemandMeanForecaster(data.train_scale)
        files.state('initial.pt', model)
        optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, betas=(.9, .999),
            eps=1e-8, weight_decay=.01, foreach=False, fused=False)
        checkpoint(); stage = 'train'
        for step, dates in enumerate(schedule, 1):
            x, y = data.batch(dates, 'train')
            optimizer.zero_grad(set_to_none=True)
            loss, parts = loss_parts(model(*x), y, data.train_scale)
            if not bool(torch.isfinite(loss)):
                raise RuntimeError('nonfinite training loss')
            loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
            optimizer.step(); checkpoint()
            journal.append({'step': step, 'loss': loss.item(), 'preclip_norm': norm.item(), **parts})
            if step in (64, 128, 192, 256):
                stage = 'validation'; scores = []
                with torch.no_grad():
                    for d in data.origins['validation']:
                        x, y = data.batch([d], 'validation')
                        scores.append(loss_parts(model(*x), y, data.train_scale)[1]['mean_objective']); checkpoint()
                score = sum(scores)/len(scores)
                name = 'step-'+str(step)+'.pt'; files.state(name, model)
                if best is None or (score, step) < (best['score'], best['step']):
                    best = {'step': step, 'score': score, 'path': name}
                journal.append({'step': step, 'validation_score': score, 'origins': len(scores)})
                files.json('prefix-'+str(step)+'.json', {'journal': journal, 'best': best})
                print(json.dumps({'step': step, 'best': best}), flush=True); stage = 'train'
        files.json('selection-before-test.json', best)
        raw = (output/best['path']).read_bytes()
        if pin(raw) != files.pins[best['path']]:
            raise ValueError('selected state pin mismatch')
        model.load_state_dict(torch.load(BytesIO(raw), map_location='cpu', weights_only=True))
        stage = 'test'; predictions = []
        with torch.no_grad():
            for d in data.origins['test']:
                x, y = data.batch([d], 'test'); out = model(*x); checkpoint()
                for v, s in enumerate(STORES):
                    predictions.append({'origin': str(d), 'store': s, 'actual': y[0, v].tolist(),
                        'daily_mean': out.daily_mean[0, v].tolist(), 'total_mean': out.total_mean[0, v].item(),
                        'total_quantiles': out.total_quantiles[0, v].tolist(), 'decision_quantity': None,
                        'shares': out.shares[0, v].tolist(), 'future_event_metadata': data.built(d)['stores'][s]['future_event_metadata'], 'baseline_context_total': x[4][0, v].sum().item(),
                        'daily_total_drift': (out.daily_mean[0, v].sum()-out.total_mean[0, v]).item()})
        files.json('test-predictions.json', predictions)
        stage = 'saved-baseline-comparison'
        rolling = REPO/'artifacts/representative-store-sales-rolling-20261014-records'
        rm = verify_record(rolling); assert rm['status'] == 'complete'
        rs_raw = item(rolling, rm, 'summary'); rs = json.loads(rs_raw)
        old = {}
        for d in data.origins['test']:
            rows = json.loads(item(rolling, rm, 'origin-'+d.strftime('%Y%m%d')))
            for cell in rows['cells']:
                old[(str(d), cell['cell']['store'])] = cell['predictions']
        for p in predictions:
            original = old[(p['origin'], p['store'])]
            assert len(original) == 14
            for k, r in enumerate(original):
                assert r['store'] == p['store'] and r['date'] == str(dt.date.fromisoformat(p['origin'])+dt.timedelta(days=k))
                assert abs(p['actual'][k]-r['actual']) <= 1e-4*max(1., abs(r['actual']))
            p['baseline_actual'] = [r['actual'] for r in original]
            p['baseline_mean28'] = [r['weekday_mean_28'] for r in original]
            p['baseline_allocated'] = [r['allocated'] for r in original]
        old_model_root = REPO/'artifacts/representative-store-sales-input-model-pilot-20261014'
        old_model_closure = json.loads((old_model_root/'root-closed.json').read_bytes()); assert old_model_closure['status'] == 'complete'
        original_model_raw = (old_model_root/'summary.json').read_bytes()
        assert pin(original_model_raw) == old_model_closure['files']['summary.json']
        original_model_summary = json.loads(original_model_raw)
        original_predictions_raw = (old_model_root/'paired-comparison.json').read_bytes()
        assert pin(original_predictions_raw) == old_model_closure['files']['paired-comparison.json']
        original_predictions = {(r['origin'], r['store']): r for r in json.loads(original_predictions_raw)}
        assert set(original_predictions) == {(r['origin'], r['store']) for r in predictions}
        for r in predictions:
            prior = original_predictions[(r['origin'], r['store'])]
            assert prior['baseline_actual'] == r['baseline_actual']
            r['prior_daily_median_allocation'] = prior['daily']
            r['prior_total_median'] = prior['total_quantiles'][1]
        def point_metrics(pairs):
            result = metrics(pairs)
            result['RMSE'] = math.sqrt(math.fsum((p-a)**2 for p,a in pairs)/len(pairs)) if pairs else None
            return result
        def group(rows):
            actual = [v for r in rows for v in r['baseline_actual']]
            daily = {name: point_metrics(list(zip([v for r in rows for v in r[field]], actual)))
                     for name, field in [('mean_head', 'daily_mean'), ('prior_median_allocation', 'prior_daily_median_allocation'), ('mean28', 'baseline_mean28'), ('allocated', 'baseline_allocated')]}
            total_getters = {'mean_head': lambda r:r['total_mean'], 'median_head': lambda r:r['total_quantiles'][1],
                             'prior_median': lambda r:r['prior_total_median'], 'mean28': lambda r:sum(r['baseline_mean28']),
                             'allocated': lambda r:sum(r['baseline_allocated'])}
            totals = {name: point_metrics([(getter(r), sum(r['baseline_actual'])) for r in rows]) for name,getter in total_getters.items()}
            losses, covered, below, above, widths, scores, relative_losses = [], 0, 0, 0, [], [], []
            for r in rows:
                a = sum(r['baseline_actual']); qs = r['total_quantiles']
                l = [max(q*(a-p), (q-1)*(a-p)) for q, p in zip((.1, .5, .9), qs)]
                losses.append(sum(l)/3)
                relative_losses.append(sum(l)/3/(14*data.train_scale[STORES.index(r['store'])].item()))
                below += a < qs[0]; above += a > qs[2]; covered += qs[0] <= a <= qs[2]
                widths.append(qs[2]-qs[0]); scores.append(qs[2]-qs[0]+10*(max(qs[0]-a, 0)+max(a-qs[2], 0)))
            n = len(rows)
            return {'daily': daily, 'totals': totals, 'interval': {'windows': n, 'coverage': covered/n,
                'covered': covered, 'below': below, 'above': above, 'width': sum(widths)/n,
                'interval_score': sum(scores)/n, 'pinball': sum(losses)/n, 'scaled_pinball': sum(relative_losses)/n}}
        files.json('paired-comparison.json', predictions)
        old_interval = REPO/'artifacts/representative-store-sales-interval-20261014-records'
        im = verify_record(old_interval); assert im['status'] == 'complete'
        old_interval_raw = item(old_interval, im, 'summary'); old_summary = json.loads(old_interval_raw)
        recent_interval = REPO/'artifacts/representative-store-sales-interval-recent-20261014-records'
        um = verify_record(recent_interval); assert um['status'] == 'complete'
        recent_raw = item(recent_interval, um, 'summary'); recent_summary = json.loads(recent_raw)
        assert len(predictions) == 48
        for name, row in group(predictions)['daily'].items():
            if name in ('mean28', 'allocated'):
                assert abs(row['WAPE']-rs['all']['methods']['weekday_mean_28' if name == 'mean28' else name]['WAPE']) < 1e-8
        assert all((REPO/p).read_bytes() == r for p, r in raw_sources.items())
        checkpoint(); files.json('journal.json', journal)
        summary = {'status': 'candidate-complete', 'selection': best, 'parameter_count': sum(p.numel() for p in model.parameters()),
            'all': group(predictions), 'stores': {str(s): group([r for r in predictions if r['store'] == s]) for s in STORES},
            'baseline_intervals': {'fixed': old_summary['all'], 'recent': recent_summary['all']['recent']},
            'original_model': original_model_summary['all'], 'original_model_stores': original_model_summary['stores'],
            'original_model_binding': pin(original_model_raw), 'original_predictions_binding': pin(original_predictions_raw),
            'point_estimand': 'mean-target head', 'selection_objective': 'validation mean MSE', 'decision_quantity': None,
            'bindings': {'point_summary': pin(rs_raw), 'fixed_interval': pin(old_interval_raw), 'recent_interval': pin(recent_raw)},
            'source_pins': {p: pin(r) for p, r in raw_sources.items()},
            'train_origins': len(data.origins['train']), 'validation_origins': len(data.origins['validation']),
            'test_origins': len(data.origins['test']), 'excluded': data.excluded,
            'steps': 256, 'new_model_test_forwards': 16, 'old_model_or_baseline_recomputed': False,
            'elapsed_seconds': time.monotonic()-STARTED, 'OS_peak_private_or_pagefile_bytes': peak,
            'python': platform.python_version(), 'torch': torch.__version__, 'platform': platform.platform(),
            'formal_permission': False, 'unseen_evaluation': False, 'coverage_guarantee': False, 'adopted': False}
        files.json('summary.json', summary)
        files.json('root-closed.json', {'status': 'complete', 'files': files.pins})
    except BaseException as error:
        original = {'type': type(error).__name__, 'message': str(error), 'traceback': traceback.format_exc(),
                    'stage': stage, 'journal': journal, 'best': best}
        try:
            files.json('failure.json', original, failure=True)
            files.json('root-closed.json', {'status': 'incomplete', 'files': files.pins}, failure=True)
        except BaseException as preservation_error:
            print(json.dumps({'original': original, 'preservation_error': str(preservation_error)}), file=sys.stderr, flush=True)
        raise
    print(json.dumps({'status': 'complete', 'selection': best, 'all': summary['all'],
                      'parameters': summary['parameter_count'], 'seconds': summary['elapsed_seconds'], 'peak': peak}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--output', required=True)
    run(parser.parse_args().output)
