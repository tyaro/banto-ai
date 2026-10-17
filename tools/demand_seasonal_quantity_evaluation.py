"""Bounded full-season 2014 selection followed by frozen 2015 evaluation."""
import time
STARTED = time.monotonic()
import argparse
import datetime as dt
import json
from pathlib import Path
import sys
import traceback
from demand_autonomous_mean import FIT, read_history
from demand_open_quantity_evaluation import assemble, tensor_inputs
from demand_open_quantity import predict_gated
from demand_recurring_closure import attach_scenarios, score_cohort
from demand_seasonal_quantity import ORDER, validation_keys, quarter, scales_2013, fit_past, calibrate_seasons, alternatives, choose, score_rows
from macos_demand_runtime import MacCheckpoint
from verify_demand_transfer import verify, pin

REPO = Path(__file__).resolve().parents[1]
CONTRACT = 'docs/research/demand-seasonal-quantity-design-2026-10-15.md'


def run(output):
    import torch
    from demand_calendar_train import Files
    guard = MacCheckpoint(seconds=870)
    if output.parent != REPO/'artifacts' or output.exists(): raise ValueError('fresh output required')
    files = Files(output); status, stage, journals, packets, forecasts = 'failed', 'sources', [], [], {}
    try:
        if sys.version_info[:3] != (3, 14, 8) or sys.platform != 'darwin' or torch.__version__ != '2.14.0': raise ValueError('fixed Mac runtime required')
        source = REPO/'artifacts/macos-demand-open-quantity-20261015'
        old = json.loads((source/'summary.json').read_bytes())
        protected = [source, Path(old['source_closure']['root']), *[Path(v['root']) for v in old['source_roots'].values()],
                     *[Path(p) for p in old['protected_roots']], REPO/'artifacts/macos-demand-frozen-recent-quantity-20261015-v2',
                     REPO/'artifacts/macos-demand-frozen-recent-quantity-20261015', REPO/'artifacts/macos-demand-frozen-recent-quantity-20261015-execution-records']
        closures = {str(p): verify(p) for p in dict.fromkeys(protected)}
        if verify(source)['recorded_status'] != 'complete': raise ValueError('closed source required')
        names = [CONTRACT, 'tools/demand_seasonal_quantity.py', 'tools/demand_seasonal_quantity_evaluation.py',
                 'tools/demand_frozen_recent_quantity.py', 'tests/test_demand_seasonal_quantity.py', *old['source_pins']]
        pins = {p: pin(REPO/p) for p in dict.fromkeys(names)}
        if any(pins[p] != v for p, v in old['source_pins'].items()): raise ValueError('old source changed')
        files.write('contract.md', (REPO/CONTRACT).read_bytes())
        files.json('sources.json', {p: (REPO/p).read_text() for p in pins})
        old250 = json.loads((Path(old['source_roots']['original250']['root'])/'summary.json').read_bytes())
        original = Path(old250['source_roots']['original']['root'])
        binding = json.loads((Path(old250['primary_root']['root'])/'binding.json').read_bytes())
        fit_keys = [(s, d) for s, d in binding['fit_keys'] if dt.date.fromisoformat(d)+dt.timedelta(days=13) < dt.date(2014, 1, 1)]
        keys = validation_keys(); selected_keys = keys[:0]
        calibration_keys = [key for k, key in enumerate(keys) if (k//10)%2 == 1]
        selected_keys = [key for k, key in enumerate(keys) if (k//10)%2 == 0]
        files.json('config-before-input.json', {'closures': closures, 'source_pins': pins, 'order': ORDER,
                   'fit_keys': fit_keys, 'validation_keys': keys, 'calibration_keys': calibration_keys, 'selection_keys': selected_keys,
                   'model_scale': '2013 observed mean only', '2015_score_scale': 'original u', 'calendar_structural_columns': 56,
                   'features': 72, 'lambda': .01, 'formal_permission': False})
        torch.set_num_threads(2); torch.set_num_interop_threads(1); torch.use_deterministic_algorithms(True)
        history = read_history(original/'selected-internal.csv', dt.date(2013, 1, 1), dt.date(2014, 12, 31))
        scales, evidence = scales_2013(history)
        monthdays = {p['month_day'] for p in old['closure_pattern']['patterns']}
        mask_evidence = [{'store': s, 'date': '2013-'+md, 'quantity': history[s].get(dt.date.fromisoformat('2013-'+md))} for md in sorted(monthdays) for s in FIT]
        if monthdays != {'01-01', '12-25'} or any(r['quantity'] is not None and r['quantity'] > 0 for r in mask_evidence): raise ValueError('2013-only mask evidence mismatch')
        files.json('2013-only-scale-and-mask.json', {'scales': evidence, 'mask_evidence': mask_evidence})
        enabled = [True]*56
        initial = assemble(history, fit_keys, scales, enabled, monthdays, guard)
        def label(row):
            day = dt.date.fromisoformat(row['origin'])
            actual = [history[row['store']].get(day+dt.timedelta(days=j)) for j in range(14)]
            return {**row, 'actual': actual, 'complete_label': all(v is not None for v in actual),
                    'assumed_closure': [not v for v in row['open_mask']]}
        packets.extend(label(r) for r in initial)
        if len(packets) < 140 or any(not r['complete_label'] for r in packets): raise ValueError('initial complete 2013 packets required')
        stage = 'all-season-2014-past-only-fits'
        validation = []
        for offset in range(0, len(keys), 10):
            current = assemble(history, keys[offset:offset+10], scales, enabled, monthdays, guard)
            predicted, journal = fit_past(packets, current, guard.check)
            journals.append(journal); guard.check()
            current = [dict(label(r), raw_prediction=p) for r, p in zip(current, predicted)]
            validation.extend(current); packets.extend(current)
        files.json('packets-and-inputs.json', packets)
        files.json('2014-raw-predictions.json', [{k: r[k] for k in ('store', 'origin', 'actual', 'raw_prediction', 'complete_label')} for r in validation])
        calibration_set = set(calibration_keys)
        calibration = calibrate_seasons([r for r in validation if (r['store'], r['origin']) in calibration_set])
        selection_set = set(selected_keys)
        outer = [r for r in validation if (r['store'], r['origin']) in selection_set]
        scored = {m: score_rows(outer, lambda r, m=m: alternatives(r, calibration)[m]) for m in ORDER}
        selected = choose({m: v['macro'] for m, v in scored.items()})
        selection = {'selected': selected, 'calibration': calibration, 'scores': scored,
                     'calibration_keys': calibration_keys, 'selection_keys': selected_keys, '2015_used': False}
        files.json('frozen-policy-before-2015.json', selection)
        groups = {'calibration': [r for r in validation if (r['store'], r['origin']) in calibration_set],
                  'selection': outer, 'all2014': validation, 'newyear': [r for r in validation if r['origin'] == '2014-01-01']}
        groups.update({f'Q{q}': [r for r in outer if quarter(r['origin']) == q] for q in range(1, 5)})
        files.json('2014-evaluation.json', {g: {m: score_rows(rows, lambda r, m=m: alternatives(r, calibration)[m]) for m in ORDER} for g, rows in groups.items()})
        stage = 'final-state-before-2015'
        final_input = assemble(history, [(s, '2015-01-01') for s in FIT], scales, enabled, monthdays, guard)
        _, journal = fit_past(packets, final_input, guard.check)
        journals.append(journal); guard.check()
        files.json('all-state-journals.json', journals)
        files.json('final-state-before-2015.json', {'journal': journal, 'selection': selection, 'new_2015_fit': False})
        state = {k: torch.tensor(v, dtype=torch.bool if k == 'active' else torch.float64) for k, v in journal['state'].items()}
        print(json.dumps({'stage': 'frozen-before-2015', 'selected': selected, 'calibration': calibration}), flush=True)
        stage = '2015-forecasts-before-labels'
        recent = read_history(Path(old250['source_roots']['development']['root'])/'selected-existing-stores.csv', dt.date(2014, 11, 18), dt.date(2015, 12, 14))
        for s, values in recent.items():
            for day, value in values.items():
                if day.year == 2014:
                    if history[s].get(day) != value: raise ValueError('overlapping source changed')
                else: history[s][day] = value
        score_scales = {int(s): v['scale'] for s, v in binding['scales'].items()}
        development_inputs, cohort_keys = {}, {}
        for cohort in ('original250', 'newyear10'):
            previous = json.loads((source/(cohort+'-predictions-before-labels.json')).read_bytes())
            cohort_keys[cohort] = [(r['store'], r['origin']) for r in previous]
            rows = assemble(history, cohort_keys[cohort], scales, enabled, monthdays, guard)
            raw, base, u, mask = tensor_inputs(rows)
            predicted = predict_gated(raw, base, u, mask, state).tolist()
            rows = [dict(r, raw_prediction=p) for r, p in zip(rows, predicted)]
            development_inputs[cohort] = rows
            forecasts[cohort] = []
            for r, before in zip(rows, previous):
                choices = alternatives(r, calibration)
                if choices['matched_mean28'] != before['baseline_proxy']: raise ValueError('matched mean28 control changed')
                forecasts[cohort].append({'store': r['store'], 'origin': r['origin'], 'scale': score_scales[r['store']],
                    'baseline': before['baseline'], 'prior': before['prior'], 'baseline_proxy': choices['matched_mean28'],
                    'candidate': choices[selected], 'alternatives': choices,
                    'assumed_closure': [not v for v in r['open_mask']], 'operating_status': ['unknown']*14})
            files.json(cohort+'-predictions-before-labels.json', forecasts[cohort])
        files.json('2015-inputs.json', development_inputs)
        stage = 'separate-label-scenarios'
        measured = {}
        for cohort in ('original250', 'newyear10'):
            labels = {(r['store'], r['origin']): r for r in json.loads((source/(cohort+'-observed-labels.json')).read_bytes())}
            obs, assumed, ledger = attach_scenarios(forecasts[cohort], labels)
            files.json(cohort+'-observed-labels.json', obs); files.json(cohort+'-assumed-labels.json', assumed)
            files.json(cohort+'-assumption-ledger.json', ledger)
            measured[cohort] = {}
            for mode, rows in (('observed', obs), ('assumed_missing_zero', assumed)):
                measured[cohort][mode] = {'primary': score_cohort(rows, cohort_keys[cohort]),
                    'quantity_and_totals': {m: score_rows(rows, lambda r, m=m: r['alternatives'][m]) for m in ORDER}}
        if {p: verify(Path(p)) for p in closures} != closures or any(pin(REPO/p) != v for p, v in pins.items()): raise ValueError('protected root/source changed')
        summary = {'status': 'complete', 'closures': closures, 'source_pins': pins, 'selection': selection,
                   'cohorts': measured, 'new_ridge_fits': len(journals), 'final_pool_windows': journal['pool_windows'],
                   'last_fit_label': journal['last_label_day'], 'fit_after_2014': False, 'closure_pattern': old['closure_pattern'],
                   'cohorts_combined': False, 'overlapping_store_days': 20, 'adopted': False, 'formal_permission': False,
                   'resources': guard.check(), 'seconds': time.monotonic()-STARTED}
        files.json('summary.json', summary); status = 'complete'
        print(json.dumps({'status': status, 'selected': selected, 'seconds': summary['seconds']}), flush=True)
    except BaseException as error:
        files.json('failure.json', {'stage': stage, 'type': type(error).__name__, 'message': str(error), 'traceback': traceback.format_exc()}, True)
        files.json('failure-prefix.json', {'journals': journals, 'packets': packets, 'forecasts': forecasts}, True)
        raise
    finally:
        files.json('root-closed.json', {'status': status, 'files': files.pins.copy(), 'immutable': True, 'formal_permission': False}, True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output.absolute())
