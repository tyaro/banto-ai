"""Bounded shortfall-constrained mean selection without additional ridge fits."""
import time
STARTED = time.monotonic()
import argparse
import datetime as dt
import json
from pathlib import Path
import sys
import traceback
from demand_shortfall_quantity import ORDER, upward_alpha, choices, measure, choose
from demand_recurring_closure import attach_scenarios, score_cohort
from demand_seasonal_quantity import quarter
from macos_demand_runtime import MacCheckpoint
from verify_demand_transfer import verify, pin

REPO = Path(__file__).resolve().parents[1]
CONTRACT = 'docs/research/demand-shortfall-quantity-design-2026-10-15.md'


def frame(row, policy, selected, old=None):
    predictions = choices(row, policy)
    return {'store': row['store'], 'origin': row['origin'], 'scale': row['scale'] if old is None else old['scale'],
            'baseline': predictions['matched_mean28'] if old is None else old['baseline'],
            'prior': predictions['matched_mean28'] if old is None else old['candidate'],
            'baseline_proxy': predictions['matched_mean28'], 'candidate': predictions[selected], 'alternatives': predictions,
            'assumed_closure': [not v for v in row['open_mask']], 'operating_status': ['unknown']*14}


def run(output):
    from demand_calendar_train import Files
    import torch
    guard = MacCheckpoint(seconds=870)
    if output.parent != REPO/'artifacts' or output.exists(): raise ValueError('fresh artifact root required')
    files = Files(output); status, stage, forecasts, policy = 'failed', 'source', {}, None
    source = REPO/'artifacts/macos-demand-seasonal-quantity-20261015'
    try:
        if sys.version_info[:3] != (3, 14, 8) or sys.platform != 'darwin' or torch.__version__ != '2.14.0': raise ValueError('fixed Mac runtime required')
        previous = json.loads((source/'summary.json').read_bytes())
        closures = {str(source): verify(source), **previous['closures']}
        for suffix in ('execution-records', 'readback-records', 'doc-records', 'doc-attempt-records'):
            path = Path(str(source)+'-'+suffix); closures[str(path)] = verify(path)
        if closures[str(source)]['recorded_status'] != 'complete' or {p: verify(Path(p)) for p in closures} != closures: raise ValueError('protected closures changed')
        sources = [CONTRACT, 'tools/demand_shortfall_quantity.py', 'tools/demand_shortfall_quantity_evaluation.py',
                   'tests/test_demand_shortfall_quantity.py', *previous['source_pins']]
        pins = {p: pin(REPO/p) for p in dict.fromkeys(sources)}
        if any(pins[p] != v for p, v in previous['source_pins'].items()): raise ValueError('protected source changed')
        config = json.loads((source/'config-before-input.json').read_bytes())
        previous_policy = json.loads((source/'frozen-policy-before-2015.json').read_bytes())
        source_state = json.loads((source/'final-state-before-2015.json').read_bytes())
        if source_state['journal']['last_label_day'] >= '2015-01-01' or source_state['new_2015_fit']: raise ValueError('pre-2015 state required')
        files.write('contract.md', (REPO/CONTRACT).read_bytes())
        files.json('sources.json', {p: (REPO/p).read_text() for p in pins})
        files.json('config-before-input.json', {'closures': closures, 'source_pins': pins, 'order': ORDER,
                   'source_state_pin': pin(source/'final-state-before-2015.json'), '2014_keys': config['validation_keys'],
                   'calibration_keys': config['calibration_keys'], 'selection_keys': config['selection_keys'],
                   'model_scale': 'source 2013-only mean', '2015_score_scale': 'original u', 'new_ridge_fits': 0,
                   'event_interval': ['12-26..12-31', '01-02..01-14'], 'formal_permission': False})
        files.json('source-final-state.json', source_state)
        stage = '2014-observed-only-upward-calibration'
        packets = json.loads((source/'packets-and-inputs.json').read_bytes())
        by_key = {(r['store'], r['origin']): r for r in packets}
        cal = [by_key[tuple(k)] for k in config['calibration_keys']]
        policy = {'alpha': upward_alpha(cal), 'quarter_levels': previous_policy['calibration']['quarter_levels'],
                  'newyear_specific_coefficient_fitted': False, '2015_used': False}
        files.json('frozen-calibration.json', {'policy': policy, 'calibration_keys': config['calibration_keys'],
                   'base': 'matched_mean28', 'direction': 'max(raw_prediction-matched_mean28,0)',
                   'source_quarter_calibration_pin': pin(source/'frozen-policy-before-2015.json'),
                   'post_newyear_calibration_target_days': 0, 'newyear_fixed_weight': 1})
        validation = [by_key[tuple(k)] for k in config['validation_keys']]
        before = [frame(r, policy, ORDER[0]) for r in validation]
        labels = {(r['store'], r['origin']): r for r in validation}
        obs, assumed, ledger = attach_scenarios(before, labels)
        files.json('2014-observed-labels.json', obs); files.json('2014-assumed-labels.json', assumed)
        files.json('2014-assumption-ledger.json', ledger)
        selection_keys = set(map(tuple, config['selection_keys'])); cal_keys = set(map(tuple, config['calibration_keys']))
        grouped = {}
        for mode, rows in (('observed', obs), ('assumed_missing_zero', assumed)):
            groups = {'selection': [r for r in rows if (r['store'], r['origin']) in selection_keys],
                      'newyear': [r for r in rows if r['origin'] == '2014-01-01'],
                      'calibration': [r for r in rows if (r['store'], r['origin']) in cal_keys], 'all2014': rows,
                      'yearend': [r for r in rows if r['origin'].startswith('2014-12-')]}
            groups.update({f'Q{q}': [r for r in groups['selection'] if quarter(r['origin']) == q] for q in range(1, 5)})
            for group, selected_rows in groups.items():
                grouped.setdefault(group, {})[mode] = {m: measure(selected_rows, lambda r, m=m: r['alternatives'][m]) for m in ORDER}
        files.json('2014-evaluation.json', grouped)
        selection = choose({g: grouped[g] for g in ('selection', 'newyear')})
        selected = selection['selected']
        frozen = {'policy': policy, 'selection': selection, 'source_state_pin': pin(source/'final-state-before-2015.json'),
                  'new_fit_after_2014': False, '2015_used': False}
        files.json('frozen-policy-before-2015.json', frozen); guard.check()
        print(json.dumps({'stage': 'frozen-before-2015', 'selection': selection, 'alpha': policy['alpha']}), flush=True)
        stage = '2015-pointwise-bound-before-labels'
        inputs = json.loads((source/'2015-inputs.json').read_bytes())
        files.json('2015-inputs.json', inputs)
        for cohort in ('original250', 'newyear10'):
            previous_predictions = json.loads((source/(cohort+'-predictions-before-labels.json')).read_bytes())
            forecasts[cohort] = [frame(r, policy, selected, old) for r, old in zip(inputs[cohort], previous_predictions)]
            if len(forecasts[cohort]) != len(previous_predictions): raise ValueError('cohort size changed')
            for row, old in zip(forecasts[cohort], previous_predictions):
                if row['baseline_proxy'] != old['baseline_proxy']: raise ValueError('matched mean28 changed')
            files.json(cohort+'-predictions-before-labels.json', forecasts[cohort])
        stage = 'two-cohort-two-label-evaluation'
        measured = {}
        for cohort in ('original250', 'newyear10'):
            labels = {(r['store'], r['origin']): r for r in json.loads((source/(cohort+'-observed-labels.json')).read_bytes())}
            obs, assumed, ledger = attach_scenarios(forecasts[cohort], labels)
            files.json(cohort+'-observed-labels.json', obs); files.json(cohort+'-assumed-labels.json', assumed)
            files.json(cohort+'-assumption-ledger.json', ledger)
            keys = [(r['store'], r['origin']) for r in obs]
            measured[cohort] = {}
            for mode, rows in (('observed', obs), ('assumed_missing_zero', assumed)):
                measured[cohort][mode] = {'primary': score_cohort(rows, keys),
                                        'fixed_candidates': {m: measure(rows, lambda r, m=m: r['alternatives'][m]) for m in ORDER}}
        if {p: verify(Path(p)) for p in closures} != closures or any(pin(REPO/p) != v for p, v in pins.items()): raise ValueError('protected closures/source changed')
        summary = {'status': 'complete', 'closures': closures, 'source_pins': pins, 'selection': selection,
                   'policy': policy, 'cohorts': measured, 'pointwise_bound': True, 'fit_after_2014': False, 'new_ridge_fits': 0,
                   'source_final_windows': source_state['journal']['pool_windows'], 'source_last_label': source_state['journal']['last_label_day'],
                   'cohorts_combined': False, 'overlapping_store_days': 20, 'adopted': False, 'formal_permission': False,
                   'resources': guard.check(), 'seconds': time.monotonic()-STARTED}
        files.json('summary.json', summary); status = 'complete'
        print(json.dumps({'status': status, 'selected': selected, 'alpha': policy['alpha']['value'], 'seconds': summary['seconds']}), flush=True)
    except BaseException as error:
        files.json('failure.json', {'stage': stage, 'type': type(error).__name__, 'message': str(error), 'traceback': traceback.format_exc()}, True)
        files.json('failure-prefix.json', {'policy': policy, 'forecasts': forecasts}, True); raise
    finally:
        files.json('root-closed.json', {'status': status, 'files': files.pins.copy(), 'immutable': True, 'formal_permission': False}, True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output.absolute())
