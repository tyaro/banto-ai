"""Fixed 365-day completed-window ridge refits; no future labels in a fit."""
import time
STARTED = time.monotonic()
import argparse
import datetime as dt
import json
import math
from pathlib import Path
import sys
import traceback

from demand_autonomous_mean import (FIT, ORIGINS, FIRST, LAST, FEATURES, LAMBDA, STATE_SHA,
    read_history, assemble, ridge_fit, ridge_predict, calibrate, score, development_metrics)
from demand_macos_rebuild import pin
from macos_demand_runtime import MacCheckpoint
from verify_demand_transfer import verify, pin as file_pin

REPO = Path(__file__).resolve().parents[1]
CONTRACT = 'docs/research/demand-rolling-ridge-design-2026-10-15.md'
WINDOW, MINIMUM = 365, 140
ORDER = ('baseline', 'incumbent', 'rolling_calibrated')


def select_pool(packets, origin):
    selected, seen = [], set()
    for packet in packets:
        # Reject foreign/current/future metadata BEFORE inspecting targets/masks.
        if packet['store'] not in FIT:
            continue
        day = dt.date.fromisoformat(packet['origin'])
        if not origin-dt.timedelta(days=WINDOW) <= day or day+dt.timedelta(days=13) >= origin:
            continue
        if type(packet['complete_label']) is not bool:
            raise ValueError('explicit completed label mask required')
        if not packet['complete_label']:
            continue
        key = (packet['store'], packet['origin'])
        if key in seen:
            raise ValueError('duplicate eligible training packet')
        seen.add(key); selected.append(packet)
    return selected


def roll_period(initial_pool, forecasts, checkpoint=lambda: None):
    import torch
    pool, predictions, journal = list(initial_pool), [], []
    dates = sorted({p['origin'] for p in forecasts})
    if len({(p['store'], p['origin']) for p in forecasts}) != len(forecasts):
        raise ValueError('duplicate forecast packet')
    for text in dates:
        origin = dt.date.fromisoformat(text)
        current = sorted([p for p in forecasts if p['origin'] == text], key=lambda p: p['store'])
        if [p['store'] for p in current] != list(FIT):
            raise ValueError('fixed ten simultaneous forecast stores required')
        selected = select_pool(pool, origin)
        counts = {s: sum(p['store'] == s for p in selected) for s in FIT}
        supported = len(selected) >= MINIMUM and all(counts.values())
        baseline = torch.tensor([p['baseline'] for p in current], dtype=torch.float64)
        scales = torch.tensor([p['scale'] for p in current], dtype=torch.float64)
        state = None
        if supported:
            if len(set(counts.values())) != 1:
                raise ValueError('unequal fixed-store fit support; do not reweight/drop')
            raw = torch.tensor([p['raw'] for p in selected], dtype=torch.float64)
            base = torch.tensor([p['baseline'] for p in selected], dtype=torch.float64)
            actual = torch.tensor([p['actual'] for p in selected], dtype=torch.float64)
            u = torch.tensor([p['scale'] for p in selected], dtype=torch.float64)
            if not bool(torch.isfinite(actual).all()) or not bool((actual >= 0).all()):
                raise ValueError('finite complete past targets required')
            state = ridge_fit(raw, base, actual, u)
            daily = ridge_predict(torch.tensor([p['raw'] for p in current], dtype=torch.float64), baseline, scales, state)
        else:
            daily = baseline
        if not bool(torch.isfinite(daily).all()) or not bool((daily >= 0).all()):
            raise ValueError('invalid rolling mean forecast')
        for k, packet in enumerate(current):
            predictions.append({'store': packet['store'], 'origin': text, 'scale': packet['scale'],
                                'baseline': packet['baseline'], 'rolling_raw': daily[k].tolist()})
        journal.append({'origin': text, 'fallback': not supported, 'pool_windows': len(selected),
                        'per_store_windows': {str(s): n for s, n in counts.items()},
                        'pool_keys': [[p['store'], p['origin']] for p in selected],
                        'first_training_origin': min((p['origin'] for p in selected), default=None),
                        'last_label_day': max((str(dt.date.fromisoformat(p['origin'])+dt.timedelta(days=13))
                                               for p in selected), default=None),
                        'state': {k: v.tolist() for k, v in state.items()} if state else None})
        # All ten forecasts are fixed before their packets can enter a later pool.
        pool.extend(current); checkpoint()
    return predictions, journal, pool


def packetize(history, keys, scales, enabled, checkpoint):
    inputs, encoded, profiles, raw = assemble(history, keys, scales, enabled, checkpoint)
    packets = []
    for k, (store, text) in enumerate(keys):
        origin = dt.date.fromisoformat(text)
        actual = [history[store].get(origin+dt.timedelta(days=j)) for j in range(14)]
        packets.append({'store': store, 'origin': text, 'scale': scales[store],
                        'raw': raw[k], 'baseline': inputs[k]['baseline'], 'actual': actual,
                        'complete_label': all(v is not None for v in actual)})
    return packets, profiles


def choose(scores):
    selected = ORDER[0]
    for name in ORDER[1:]:
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
    stage, status, rows, internal_journal, dev_journal = 'source', 'failed', [], [], []
    roots = {k: REPO/'artifacts'/name for k, name in (
        ('original', 'macos-demand-rebuild-20261015'),
        ('internal', 'macos-demand-autonomous-mean-20261015'),
        ('development', 'macos-demand-existing-stores-2015-20261015'))}
    try:
        if sys.version_info[:3] != (3, 14, 8) or torch.__version__ != '2.14.0' or sys.platform != 'darwin':
            raise ValueError('fixed Mac Python/Torch required')
        closures = {k: verify(p) for k, p in roots.items()}
        if any(v['recorded_status'] != 'complete' for v in closures.values()):
            raise ValueError('complete source roots required')
        original = roots['original']; internal = roots['internal']; dev = roots['development']
        prior = json.loads((internal/'summary.json').read_bytes())
        dev_config = json.loads((dev/'config-before-input.json').read_bytes())
        names = [CONTRACT, 'tools/demand_rolling_ridge.py', *prior['source_pins'], *dev_config['source_pins']]
        sources = {p: (REPO/p).read_bytes() for p in dict.fromkeys(names)}
        for meta in (prior, dev_config):
            if any(pin(sources[p]) != expected for p, expected in meta['source_pins'].items()):
                raise ValueError('original source changed')
        if file_pin(original/'time_selected.pt')['sha256'] != STATE_SHA:
            raise ValueError('incumbent state changed')
        binding = json.loads((internal/'binding.json').read_bytes())
        scales = {int(s): v['scale'] for s, v in binding['scales'].items()}
        enabled = binding['support']['enabled']
        if set(scales) != set(FIT) or any(u <= 0 for u in scales.values()) or sum(enabled) != 42:
            raise ValueError('fixed scale/calendar support changed')
        torch.set_num_threads(2); torch.set_num_interop_threads(1); torch.use_deterministic_algorithms(True)
        files.write('contract.md', sources[CONTRACT]); files.json('sources.json', {p: raw.decode() for p, raw in sources.items()})
        files.json('config-before-internal.json', {'window_days': WINDOW, 'minimum_windows': MINIMUM,
                   'lambda': LAMBDA, 'features': FEATURES, 'order': ORDER, 'source_roots': closures,
                   'source_pins': {p: pin(raw) for p, raw in sources.items()}, 'new_nn_fit': False,
                   'new_nn_forward': False, 'formal_permission': False})
        files.json('binding.json', binding); guard.check()
        stage = 'internal-past-only-packets'
        history = read_history(original/'selected-internal.csv', dt.date(2013, 1, 1), dt.date(2014, 12, 31))
        fit, fit_profiles = packetize(history, binding['fit_keys'], scales, enabled, guard.check)
        validation, val_profiles = packetize(history, binding['time_keys'], scales, enabled, guard.check)
        if len(fit) != 300 or len(validation) != 120 or not all(p['complete_label'] for p in fit+validation):
            raise ValueError('fixed complete internal windows required')
        files.json('internal-profiles.json', fit_profiles+val_profiles)
        stage = 'internal-rolling-refits'
        predictions, internal_journal, pool = roll_period(fit, validation, guard.check)
        files.json('internal-state-journal.json', internal_journal)
        files.json('internal-predictions-before-labels.json', predictions)
        targets = {(p['store'], p['origin']): p for p in validation}
        nn = {(r['store'], r['origin']): r for r in json.loads((internal/'time-validation-predictions.json').read_bytes())}
        if set(nn) != set(targets):
            raise ValueError('fixed incumbent/internal grid changed')
        for key, packet in targets.items():
            if nn[key]['baseline'] != packet['baseline'] or nn[key]['actual'] != packet['actual']:
                raise ValueError('internal baseline/actual drift')
        actual = torch.tensor([targets[r['store'], r['origin']]['actual'] for r in predictions], dtype=torch.float64)
        u = torch.tensor([r['scale'] for r in predictions], dtype=torch.float64)
        base = torch.tensor([r['baseline'] for r in predictions], dtype=torch.float64)
        incumbent = torch.tensor([nn[r['store'], r['origin']]['raw_nn'] for r in predictions], dtype=torch.float64)
        rolling = torch.tensor([r['rolling_raw'] for r in predictions], dtype=torch.float64)
        calibration = calibrate(rolling, base, actual, u)
        calibrated = base+calibration['alpha']*(rolling-base)
        scores = {name: score(p, actual, u) for name, p in (('baseline', base), ('incumbent', incumbent), ('rolling_calibrated', calibrated))}
        selected = choose(scores)
        selection = {'selected': selected, 'calibration': calibration, 'scores': scores,
                     'selection_data': '2014 time120 only', 'development_used_for_selection': False,
                     'secondary_fixed_method': 'rolling_calibrated', 'original_time_step': 3328}
        files.json('frozen-selection-before-development.json', selection)
        print(json.dumps({'stage': 'frozen', **selection}), flush=True); guard.check()
        stage = 'development-past-only-packets'
        dev_history = read_history(dev/'selected-existing-stores.csv', FIRST, LAST)
        for s, values in dev_history.items():
            for day, value in values.items():
                if day < dt.date(2015, 1, 1):
                    if history[s].get(day) != value:
                        raise ValueError('overlapping snapshot quantity changed')
                else:
                    history[s][day] = value
        keys = [(s, str(d)) for s in FIT for d in ORIGINS]
        dev_packets, profiles = packetize(history, keys, scales, enabled, guard.check)
        files.json('development-profiles.json', profiles)
        headers = [{k: p[k] for k in ('store', 'origin', 'complete_label')} for p in fit+validation+dev_packets]
        files.json('packet-headers.json', headers)
        stage = 'development-rolling-refits'
        raw_predictions, dev_journal, _ = roll_period(pool, dev_packets, guard.check)
        files.json('development-state-journal.json', dev_journal)
        old = {(r['store'], r['origin']): r for r in json.loads((dev/'predictions-and-labels.json').read_bytes())}
        for prediction in raw_predictions:
            key = (prediction['store'], prediction['origin']); prior_row = old[key]
            if prediction['baseline'] != prior_row['baseline'] or prediction['scale'] != prior_row['scale']:
                raise ValueError('development baseline/scale changed')
            rolling_fixed = [b+calibration['alpha']*(p-b) for p, b in zip(prediction['rolling_raw'], prediction['baseline'])]
            candidate = (rolling_fixed if selected == 'rolling_calibrated' else
                         prior_row['time_selected'] if selected == 'incumbent' else prediction['baseline'])
            rows.append({k: prediction[k] for k in ('store', 'origin', 'scale', 'baseline')}
                        | {'candidate': candidate, 'incumbent': prior_row['time_selected'], 'rolling_fixed': rolling_fixed,
                           'model_available': prior_row['model_available'], 'input_reasons': prior_row['input_reasons']})
        files.json('predictions-before-labels.json', rows)
        packet_lookup = {(p['store'], p['origin']): p for p in dev_packets}
        labelled = []
        for row in rows:
            key = row['store'], row['origin']; packet = packet_lookup[key]
            if packet['actual'] != old[key]['actual'] or packet['complete_label'] != old[key]['complete_label']:
                raise ValueError('development actual/mask drift')
            labelled.append(row | {'actual': packet['actual'], 'complete_label': packet['complete_label']})
        files.json('predictions-and-labels.json', labelled)
        stage = 'fixed-evaluation'
        measured = development_metrics(labelled, scales)
        secondary = development_metrics([{**r, 'candidate': r['rolling_fixed']} for r in labelled], scales)
        if measured['requested'] != 250 or measured['complete_label_windows'] != 240:
            raise ValueError('fixed development support changed')
        if (any((REPO/p).read_bytes() != raw for p, raw in sources.items())
                or {k: verify(p) for k, p in roots.items()} != closures):
            raise ValueError('sources or original roots changed')
        summary = {'status': 'complete', 'selection': selection, 'source_roots': closures,
                   'source_pins': {p: pin(raw) for p, raw in sources.items()}, 'new_nn_fit': False,
                   'new_nn_forward': False, 'ridge_fits': sum(not j['fallback'] for j in internal_journal+dev_journal),
                   'internal_origin_fits': len(internal_journal), 'development_origin_fits': len(dev_journal),
                   'fallback_origin_counts': {'internal': sum(j['fallback'] for j in internal_journal),
                                              'development': sum(j['fallback'] for j in dev_journal)},
                   'fixed_rolling_secondary': secondary, 'adopted': False, 'formal_permission': False,
                   'resources': guard.check(), 'seconds': time.monotonic()-STARTED, **measured}
        files.json('summary.json', summary); status = 'complete'
        print(json.dumps({'status': status, 'selected': selected, 'macro': measured['macro'],
                         'decision': measured['primary_development_decision'],
                         'rolling_secondary_macro': secondary['macro'],
                         'rolling_secondary_decision': secondary['primary_development_decision'],
                         'seconds': summary['seconds']}), flush=True)
    except BaseException as error:
        files.json('failure.json', {'stage': stage, 'type': type(error).__name__, 'message': str(error),
                                  'traceback': traceback.format_exc()}, True)
        files.json('failure-prefix.json', {'rows': rows, 'internal_journal': internal_journal, 'development_journal': dev_journal}, True)
        raise
    finally:
        files.json('root-closed.json', {'status': status, 'files': files.pins.copy(), 'immutable': True,
                                     'formal_permission': False}, True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
