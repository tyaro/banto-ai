"""Past completed raw forecast errors only; finite mean-bias update comparison."""
import time
STARTED = time.monotonic()
import argparse
import copy
import datetime as dt
import json
import math
from pathlib import Path
import sys
import traceback

from demand_autonomous_mean import calibrate, score, development_metrics, FIT, STATE_SHA
from demand_macos_rebuild import pin
from macos_demand_runtime import MacCheckpoint
from verify_demand_transfer import verify, pin as file_pin

REPO = Path(__file__).resolve().parents[1]
CONTRACT = 'docs/research/demand-prequential-bias-design-2026-10-15.md'
LOOKBACK, MINIMUM = 56, 14
METHODS = ('baseline', 'incumbent', 'updated_baseline', 'updated_incumbent')


def bias_before(history, store, origin):
    eligible = [r for r in history if r['store'] == store
                and dt.date.fromisoformat(r['complete_by']) < origin
                and origin-dt.timedelta(days=LOOKBACK) <= dt.date.fromisoformat(r['day']) < origin]
    count = len(eligible)
    bias = {name: math.fsum(r[name] for r in eligible)/count if count >= MINIMUM else 0.
            for name in ('baseline_error', 'incumbent_error')}
    if not all(math.isfinite(v) for v in bias.values()):
        raise ValueError('nonfinite completed forecast error')
    return bias, {'count': count, 'fallback': count < MINIMUM,
                  'first_error_day': min((r['day'] for r in eligible), default=None),
                  'last_error_day': max((r['day'] for r in eligible), default=None),
                  'latest_completed_by': max((r['complete_by'] for r in eligible), default=None)}


def run_period(rows, initial_history=()):
    history = copy.deepcopy(list(initial_history))
    output, traces, seen = [], [], set()
    for row in sorted(rows, key=lambda r: (r['origin'], r['store'])):
        s, origin, u = row['store'], dt.date.fromisoformat(row['origin']), row['scale']
        if (s, str(origin)) in seen or s not in FIT or type(u) not in (int, float) or not math.isfinite(u) or u <= 0:
            raise ValueError('distinct fixed store and positive scale required')
        seen.add((s, str(origin)))
        for name in ('baseline', 'incumbent'):
            if len(row[name]) != 14 or any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in row[name]):
                raise ValueError('finite nonnegative fixed raw forecast required')
        bias, support = bias_before(history, s, origin)
        forecast = {k: row[k] for k in ('store', 'origin', 'scale', 'baseline', 'incumbent')}
        forecast['updated_baseline'] = [max(0., p-u*bias['baseline_error']) for p in row['baseline']]
        forecast['updated_incumbent'] = [max(0., p-u*bias['incumbent_error']) for p in row['incumbent']]
        output.append(forecast)
        traces.append({'store': s, 'origin': str(origin), 'bias': bias, **support})
        # Calendar horizon completion is encoded here; observed-label completeness
        # is a separate mask. bias_before rejects a not-yet-completed whole window.
        actual = row['actual']
        if len(actual) != 14:
            raise ValueError('fixed actual horizon required')
        for k, y in enumerate(actual):
            if y is None:
                continue
            if type(y) not in (int, float) or not math.isfinite(y) or y < 0:
                raise ValueError('finite nonnegative observed actual required')
            history.append({'store': s, 'day': str(origin+dt.timedelta(days=k)),
                            'complete_by': str(origin+dt.timedelta(days=13)),
                            'baseline_error': (row['baseline'][k]-y)/u,
                            'incumbent_error': (row['incumbent'][k]-y)/u})
    return output, traces, history


def choose(scores):
    selected = METHODS[0]
    for name in METHODS[1:]:
        if scores[name]['joint'] < scores[selected]['joint']-1e-12:
            selected = name
    return selected


def run(output):
    import torch
    from demand_calendar_train import Files
    root = output.absolute()
    if root.parent != REPO/'artifacts' or root.exists():
        raise ValueError('fresh artifact root required')
    files = Files(root); guard = MacCheckpoint(seconds=870)
    status, stage, rows = 'failed', 'source', []
    internal = REPO/'artifacts/macos-demand-autonomous-mean-20261015'
    development = REPO/'artifacts/macos-demand-existing-stores-2015-20261015'
    original = REPO/'artifacts/macos-demand-rebuild-20261015'
    try:
        if sys.version_info[:3] != (3, 14, 8) or torch.__version__ != '2.14.0' or sys.platform != 'darwin':
            raise ValueError('fixed Mac Python/Torch required')
        source_roots = {'internal': verify(internal), 'development': verify(development), 'original': verify(original)}
        if any(v['recorded_status'] != 'complete' for v in source_roots.values()):
            raise ValueError('complete source roots required')
        internal_summary = json.loads((internal/'summary.json').read_bytes())
        dev_config = json.loads((development/'config-before-input.json').read_bytes())
        sources = {p: (REPO/p).read_bytes() for p in dict.fromkeys(
                   [CONTRACT, 'tools/demand_prequential_bias.py', *internal_summary['source_pins'], *dev_config['source_pins']])}
        for metadata in (internal_summary, dev_config):
            if any(pin(sources[p]) != expected for p, expected in metadata['source_pins'].items()):
                raise ValueError('original pinned source changed')
        if file_pin(original/'time_selected.pt')['sha256'] != STATE_SHA:
            raise ValueError('original NN state changed')
        binding = json.loads((internal/'binding.json').read_bytes())
        scales = {int(s): v['scale'] for s, v in binding['scales'].items()}
        files.write('contract.md', sources[CONTRACT]); files.json('sources.json', {p: raw.decode() for p, raw in sources.items()})
        files.json('config-before-internal.json', {'lookback_days': LOOKBACK, 'minimum_observed_errors': MINIMUM,
                   'method_order': METHODS, 'tie_tolerance': 1e-12, 'incumbent_state_pin': file_pin(original/'time_selected.pt'),
                   'source_roots': source_roots, 'source_pins': {p: pin(raw) for p, raw in sources.items()},
                   'new_fit': False, 'new_nn_forward': False, 'formal_permission': False})
        guard.check(); stage = 'internal-past-only-update'
        internal_saved = json.loads((internal/'time-validation-predictions.json').read_bytes())
        if (len(internal_saved) != 120 or {(r['store'], r['origin']) for r in internal_saved}
                != {(s, text) for s, text in binding['time_keys']}):
            raise ValueError('fixed time120 grid changed')
        internal_rows = [{**r, 'incumbent': r['raw_nn'], 'scale': scales[r['store']]} for r in internal_saved]
        forecasts, traces, warm = run_period(internal_rows)
        labels = {(r['store'], r['origin']): r['actual'] for r in internal_rows}
        actual = torch.tensor([labels[r['store'], r['origin']] for r in forecasts], dtype=torch.float64)
        u = torch.tensor([r['scale'] for r in forecasts], dtype=torch.float64)
        values = {m: torch.tensor([r[m] for r in forecasts], dtype=torch.float64) for m in METHODS}
        calibration = {}
        for updated, reference in (('updated_baseline', 'baseline'), ('updated_incumbent', 'incumbent')):
            calibration[updated] = calibrate(values[updated], values[reference], actual, u)
            values[updated] = values[reference]+calibration[updated]['alpha']*(values[updated]-values[reference])
        scores = {m: score(p, actual, u) for m, p in values.items()}
        selected = choose(scores)
        selection = {'selected': selected, 'calibrations': calibration, 'scores': scores,
                     'selection_data': '2014 time120 only', 'development_used_for_selection': False,
                     'history_uses_raw_forecast_errors': True, 'new_nn_training': False}
        files.json('internal-past-support.json', traces)
        files.json('internal-update-predictions.json', forecasts)
        files.json('internal-warm-history.json', warm)
        files.json('frozen-selection-before-development.json', selection)
        print(json.dumps({'stage': 'frozen', **selection}), flush=True)
        guard.check(); stage = 'fixed-2015-prequential-update'
        old_labelled = json.loads((development/'predictions-and-labels.json').read_bytes())
        old_before = json.loads((development/'predictions-before-labels.json').read_bytes())
        if [{k: v for k, v in r.items() if k not in ('actual', 'complete_label')} for r in old_labelled] != old_before:
            raise ValueError('old predictions changed during label attachment')
        dev_rows = [{**r, 'incumbent': r['time_selected']} for r in old_labelled]
        candidates, dev_traces, _ = run_period(dev_rows, warm)
        rows = []
        originals = {(r['store'], r['origin']): r for r in old_labelled}
        for forecast in candidates:
            if selected in ('baseline', 'incumbent'):
                candidate = forecast[selected]
            else:
                reference = 'baseline' if selected == 'updated_baseline' else 'incumbent'
                alpha = calibration[selected]['alpha']
                candidate = [b+alpha*(p-b) for p, b in zip(forecast[selected], forecast[reference])]
            old = originals[forecast['store'], forecast['origin']]
            rows.append({k: forecast[k] for k in ('store', 'origin', 'scale', 'baseline', 'incumbent')}
                        | {'candidate': candidate, 'model_available': old['model_available'], 'input_reasons': old['input_reasons']})
        files.json('development-past-support.json', dev_traces)
        files.json('predictions-before-labels.json', rows)
        labelled = [{**r, 'actual': originals[r['store'], r['origin']]['actual'],
                     'complete_label': originals[r['store'], r['origin']]['complete_label']} for r in rows]
        files.json('predictions-and-labels.json', labelled)
        stage = 'fixed-metrics'
        measured = development_metrics(labelled, scales)
        if measured['requested'] != 250 or measured['complete_label_windows'] != 240:
            raise ValueError('fixed development grid/support changed')
        if (any((REPO/p).read_bytes() != raw for p, raw in sources.items())
                or {k: verify(r) for k, r in (('internal', internal), ('development', development), ('original', original))} != source_roots):
            raise ValueError('source or original root changed')
        summary = {'status': 'complete', 'selection': selection, 'source_roots': source_roots,
                   'source_pins': {p: pin(raw) for p, raw in sources.items()}, 'new_fit': False,
                   'new_nn_forward': False, 'development_already_read': True, 'adopted': False,
                   'formal_permission': False, 'internal_fallback_windows': sum(t['fallback'] for t in traces),
                   'development_fallback_windows': sum(t['fallback'] for t in dev_traces),
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
