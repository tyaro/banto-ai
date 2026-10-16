"""Four-way pre-2015 quantity selection, preserving fixed closure assumptions."""
import time
STARTED = time.monotonic()
import argparse
import datetime as dt
import json
from pathlib import Path
import sys
import traceback

from demand_autonomous_mean import FIT, read_history, calibrate, score
from demand_open_quantity import ORDER, inputs, fit_gated, predict_gated, level_delta, choose
from demand_public_calendar import fit_support
from demand_recurring_closure import attach_scenarios, score_cohort
from demand_temporal_selection import temporal_split
from macos_demand_runtime import MacCheckpoint
from verify_demand_transfer import verify, pin

REPO = Path(__file__).resolve().parents[1]
CONTRACT = 'docs/research/demand-open-quantity-design-2026-10-15.md'


def assemble(history, keys, scales, enabled, monthdays, guard):
    result = []
    for s, day in keys:
        result.append(inputs(history[s], s, dt.date.fromisoformat(day), scales[s], enabled, monthdays)); guard.check()
    return result


def tensor_inputs(rows):
    import torch
    return (torch.tensor([r['raw_features'] for r in rows], dtype=torch.float64),
            torch.tensor([r['open_mean28'] for r in rows], dtype=torch.float64),
            torch.tensor([r['scale'] for r in rows], dtype=torch.float64),
            torch.tensor([r['open_mask'] for r in rows], dtype=torch.bool))


def run(output):
    guard = MacCheckpoint(seconds=870)
    import torch
    from demand_calendar_train import Files
    root = output.absolute()
    if root.parent != REPO/'artifacts' or root.exists():
        raise ValueError('fresh root required')
    files = Files(root); status, stage, forecasts, ridge = 'failed', 'source', {}, None
    source = REPO/'artifacts/macos-demand-recurring-closure-20261015'
    try:
        if sys.version_info[:3] != (3, 14, 8) or sys.platform != 'darwin' or torch.__version__ != '2.14.0':
            raise ValueError('fixed Mac runtime required')
        source_closure = verify(source); previous = json.loads((source/'summary.json').read_bytes())
        closures = previous['source_roots']; protected = previous['protected_roots']
        if source_closure['recorded_status'] != 'complete' or {k: verify(Path(v['root'])) for k, v in closures.items()} != closures or {p: verify(Path(p)) for p in protected} != protected:
            raise ValueError('closed original roots changed')
        if any(pin(REPO/name) != expected for name, expected in previous['source_pins'].items()):
            raise ValueError('old source changed')
        names = [CONTRACT, 'tools/demand_open_quantity.py', 'tools/demand_open_quantity_evaluation.py',
                 'tests/test_demand_open_quantity.py', *previous['source_pins']]
        sources = {name: (REPO/name).read_bytes() for name in dict.fromkeys(names)}
        pins = {name: pin(REPO/name) for name in sources}
        pattern = previous['frozen_pattern']; monthdays = {p['month_day'] for p in pattern['patterns']}
        original250 = Path(closures['original250']['root'])
        old250summary = json.loads((original250/'summary.json').read_bytes())
        original = Path(old250summary['source_roots']['original']['root'])
        binding = json.loads((Path(old250summary['primary_root']['root'])/'binding.json').read_bytes())
        scales = {int(s): v['scale'] for s, v in binding['scales'].items()}
        fit_keys = binding['fit_keys']+[[s, '2014-01-01'] for s in FIT]
        split = temporal_split(binding['time_keys'])
        if len(set(map(tuple, fit_keys))) != 310 or [len(split[k]) for k in ('inner', 'outer', 'crossing')] != [60, 50, 10]:
            raise ValueError('fixed fit310 and temporal split changed')
        files.write('contract.md', sources[CONTRACT]); files.json('sources.json', {name: raw.decode() for name, raw in sources.items()})
        files.json('config-before-input.json', {'source_closure': source_closure, 'source_roots': closures,
                   'protected_roots': protected, 'source_pins': pins, 'closure_pattern': pattern, 'order': ORDER,
                   'lambda': .01, 'features': 72, 'minimum_conditional_weekday_support': 2,
                   'fit_keys': fit_keys, 'temporal_split': split, 'fit_after_2014': False, 'formal_permission': False})
        torch.set_num_threads(2); torch.set_num_interop_threads(1); torch.use_deterministic_algorithms(True)
        history = read_history(original/'selected-internal.csv', dt.date(2013, 1, 1), dt.date(2014, 12, 31))
        if any(any((v := history[s].get(dt.date.fromisoformat('2013-'+md))) is not None and v > 0 for s in FIT) for md in monthdays):
            raise ValueError('2013-only evidence does not support fixed mask for 2014')
        files.json('2013-mask-evidence.json', [{'store': s, 'date': '2013-'+md,
                   'quantity': history[s].get(dt.date.fromisoformat('2013-'+md))} for md in sorted(monthdays) for s in FIT])
        stage = 'fit310-calendar-support'
        actual = []
        observed = {}
        for s, text in fit_keys:
            origin = dt.date.fromisoformat(text)
            if origin+dt.timedelta(days=13) >= dt.date(2014, 7, 1):
                raise ValueError('fit target cutoff changed')
            ys = []
            for j in range(14):
                day = origin+dt.timedelta(days=j); value = history[s].get(day)
                if value is None:
                    raise ValueError('fit target missing; do not train on imputed labels')
                ys.append(value); observed[s, day] = str(day)[5:] not in monthdays
            actual.append(ys)
        support = fit_support([(s, dt.date.fromisoformat(d)) for s, d in fit_keys], observed, cutoff=dt.date(2014, 7, 1))
        enabled = support['enabled']
        files.json('fit-calendar-support.json', support)
        train = assemble(history, fit_keys, scales, enabled, monthdays, guard)
        files.json('fit-inputs-and-labels.json', {'inputs': train, 'actual': actual})
        raw, base, u, mask = tensor_inputs(train)
        ridge = fit_gated(raw, base, torch.tensor(actual, dtype=torch.float64), u, mask)
        files.json('gated-ridge-state.json', {k: v.tolist() for k, v in ridge.items()})
        stage = 'inner60-only-calibration'
        inner = assemble(history, split['inner'], scales, enabled, monthdays, guard)
        iraw, ibase, iu, imask = tensor_inputs(inner)
        iy = torch.tensor([[history[s][dt.date.fromisoformat(d)+dt.timedelta(days=j)] for j in range(14)] for s, d in split['inner']], dtype=torch.float64)
        ip = predict_gated(iraw, ibase, iu, imask, ridge)
        alpha = {**calibrate(ip, ibase, iy, iu), 'selection_period': '2014 inner60 only'}
        delta = level_delta(ibase, iy, iu, imask)
        files.json('frozen-inner-calibration.json', {'inputs': inner, 'actual': iy.tolist(), 'raw_prediction': ip.tolist(),
                   'alpha': alpha, 'delta': delta, 'outer_used': False, '2015_used': False})
        stage = 'outer50-fixed-method-choice'
        outer = assemble(history, split['outer'], scales, enabled, monthdays, guard)
        oraw, obase, ou, omask = tensor_inputs(outer)
        oy = torch.tensor([[history[s][dt.date.fromisoformat(d)+dt.timedelta(days=j)] for j in range(14)] for s, d in split['outer']], dtype=torch.float64)
        op = predict_gated(oraw, obase, ou, omask, ridge)
        alternatives = {'matched_mean28': torch.tensor([r['matched_mean28'] for r in outer], dtype=torch.float64),
                        'open_mean28': obase, 'level_corrected': obase+delta['delta']*ou[:, None]*omask,
                        'gated_ridge': obase+alpha['alpha']*(op-obase)}
        scores = {name: score(p, oy, ou) for name, p in alternatives.items()}
        selected = choose(scores)
        selection = {'selected': selected, 'scores': scores, 'delta': delta, 'alpha': alpha,
                     'selection_period': '2014 outer50 only', '2015_used': False, 'crossing_used': False,
                     'ridge_state_pin': files.pins['gated-ridge-state.json']}
        files.json('outer-fixed-predictions.json', {'inputs': outer, 'actual': oy.tolist(), 'raw_prediction': op.tolist(),
                   'predictions': {k: v.tolist() for k, v in alternatives.items()}})
        files.json('frozen-selection-before-2015.json', selection); guard.check()
        print(json.dumps({'stage': 'frozen-before-2015', **selection}), flush=True)
        stage = '2015-past-only-quantity-inputs'
        dev_path = Path(old250summary['source_roots']['development']['root'])/'selected-existing-stores.csv'
        recent = read_history(dev_path, dt.date(2014, 11, 18), dt.date(2015, 12, 14))
        for s, values in recent.items():
            for day, value in values.items():
                if day < dt.date(2015, 1, 1):
                    if history[s].get(day) != value:
                        raise ValueError('overlapping historical snapshot changed')
                else:
                    history[s][day] = value
        all_dev_inputs, keys = {}, {}
        for name in ('original250', 'newyear10'):
            previous_rows = json.loads((source/(name+'-predictions-before-labels.json')).read_bytes())
            keys[name] = [(r['store'], r['origin']) for r in previous_rows]
            dev_inputs = assemble(history, keys[name], scales, enabled, monthdays, guard)
            all_dev_inputs[name] = dev_inputs
            draw, dbase, du, dmask = tensor_inputs(dev_inputs)
            dp = predict_gated(draw, dbase, du, dmask, ridge)
            choices = {'matched_mean28': [r['matched_mean28'] for r in dev_inputs],
                       'open_mean28': dbase.tolist(),
                       'level_corrected': (dbase+delta['delta']*du[:, None]*dmask).tolist(),
                       'gated_ridge': (dbase+alpha['alpha']*(dp-dbase)).tolist()}
            forecasts[name] = []
            for k, (row, old) in enumerate(zip(dev_inputs, previous_rows)):
                if row['matched_mean28'] != old['baseline_proxy']:
                    raise ValueError('same-mask original mean28 control changed')
                forecasts[name].append({'store': row['store'], 'origin': row['origin'], 'scale': row['scale'],
                     'baseline': old['baseline'], 'prior': old['candidate'], 'baseline_proxy': row['matched_mean28'],
                     'candidate': choices[selected][k], 'alternatives': {m: p[k] for m, p in choices.items()},
                     'assumed_closure': [not v for v in row['open_mask']], 'operating_status': ['unknown']*14})
            files.json(name+'-predictions-before-labels.json', forecasts[name])
        files.json('2015-inputs.json', all_dev_inputs)
        stage = 'two-cohorts-two-label-evaluation'
        measured = {}
        for name in ('original250', 'newyear10'):
            original_labels = {(r['store'], r['origin']): r for r in json.loads((source/(name+'-observed-labels.json')).read_bytes())}
            observed_rows, assumed_rows, ledger = attach_scenarios(forecasts[name], original_labels)
            files.json(name+'-observed-labels.json', observed_rows); files.json(name+'-assumed-labels.json', assumed_rows)
            files.json(name+'-assumption-ledger.json', ledger)
            measured[name] = {}
            for mode, rows in (('observed', observed_rows), ('assumed_missing_zero', assumed_rows)):
                primary = score_cohort(rows, keys[name])
                comparisons = {m: score_cohort([{**r, 'candidate': r['alternatives'][m]} for r in rows], keys[name]) for m in ORDER}
                measured[name][mode] = {'primary': primary, 'fixed_alternatives': comparisons}
        if (verify(source) != source_closure or {k: verify(Path(v['root'])) for k, v in closures.items()} != closures
                or {p: verify(Path(p)) for p in protected} != protected or any(pin(REPO/name) != expected for name, expected in pins.items())):
            raise ValueError('original source/root changed')
        summary = {'status': 'complete', 'source_closure': source_closure, 'source_roots': closures, 'protected_roots': protected,
                   'source_pins': pins, 'selection': selection, 'closure_pattern': pattern, 'calendar_enabled': sum(enabled),
                   'fit_windows': 310, 'fit_closed_days': int((~mask).sum()), 'new_ridge_fits': 1,
                   'fitted_or_calibrated_after_2014': False, 'cohorts': measured, 'cohorts_combined': False,
                   'overlapping_store_days': 20, 'new_nn_fit': False, 'adopted': False, 'formal_permission': False,
                   'resources': guard.check(), 'seconds': time.monotonic()-STARTED}
        files.json('summary.json', summary); status = 'complete'
        print(json.dumps({'status': status, 'selected': selected, 'cohorts': {name: {mode: value['primary']['improvement_percent_over']
                         for mode, value in modes.items()} for name, modes in measured.items()}, 'seconds': summary['seconds']}), flush=True)
    except BaseException as error:
        files.json('failure.json', {'stage': stage, 'type': type(error).__name__, 'message': str(error), 'traceback': traceback.format_exc()}, True)
        files.json('failure-prefix.json', {'forecasts': forecasts, 'ridge': {k: v.tolist() for k, v in ridge.items()} if ridge else None}, True)
        raise
    finally:
        files.json('root-closed.json', {'status': status, 'files': files.pins.copy(), 'immutable': True, 'formal_permission': False}, True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
