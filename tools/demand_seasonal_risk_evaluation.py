"""Astra-reviewed signed totals under seasonal mean risk constraints."""
import time
STARTED = time.monotonic()
import argparse
import json
from pathlib import Path
import sys
import traceback
from demand_seasonal_risk import ORDER, calibrate, choices, measure, choose, recent14
from demand_recurring_closure import attach_scenarios, score_cohort
from demand_seasonal_quantity import quarter
from macos_demand_runtime import MacCheckpoint
from verify_demand_transfer import verify, pin

REPO = Path(__file__).resolve().parents[1]
CONTRACT = 'docs/research/demand-seasonal-risk-design-2026-10-15.md'
REVIEW = 'docs/research/demand-seasonal-risk-astra-review-2026-10-15.md'


def frame(row, policy, selection=None, old=None):
    predictions = choices(row, policy)
    selected = 'matched_mean28' if selection is None else selection['selected_by_quarter'][str(quarter(row['origin']))]
    return {'store': row['store'], 'origin': row['origin'], 'scale': row['scale'] if old is None else old['scale'],
            'baseline': predictions['matched_mean28'] if old is None else old['baseline'],
            'prior': predictions['matched_mean28'] if old is None else old['candidate'],
            'baseline_proxy': predictions['matched_mean28'], 'candidate': predictions[selected], 'alternatives': predictions,
            'selected_method': selected, 'recent14_support': recent14(row)[1], 'assumed_closure': [not v for v in row['open_mask']], 'operating_status': ['unknown']*14}


def groups_2014(rows, selection_keys, calibration_keys):
    selection_rows = [r for r in rows if (r['store'], r['origin']) in selection_keys]
    normal = [r for r in selection_rows if r['origin'] != '2014-01-01']
    groups = {'selection130': selection_rows, 'normal120': normal,
              'newyear': [r for r in selection_rows if r['origin'] == '2014-01-01'],
              'calibration': [r for r in rows if (r['store'], r['origin']) in calibration_keys], 'all2014': rows,
              'yearend': [r for r in rows if r['origin'].startswith('2014-12-')]}
    groups.update({f'normal_Q{q}': [r for r in normal if quarter(r['origin']) == q] for q in range(1, 5)})
    return groups


def run(output):
    from demand_calendar_train import Files
    import torch
    guard = MacCheckpoint(seconds=870)
    if output.parent != REPO/'artifacts' or output.exists(): raise ValueError('fresh artifact root required')
    files = Files(output); status, stage, forecasts, policy = 'failed', 'sources', {}, None
    source = REPO/'artifacts/macos-demand-total-preserving-20261015'
    seasonal = REPO/'artifacts/macos-demand-seasonal-quantity-20261015'
    try:
        if sys.version_info[:3] != (3, 14, 8) or sys.platform != 'darwin' or torch.__version__ != '2.14.0': raise ValueError('fixed Mac runtime required')
        previous = json.loads((source/'summary.json').read_bytes())
        closures = {str(source): verify(source), **previous['closures']}
        for suffix in ('execution-records', 'readback-records', 'doc-records', 'doc-records-v2'):
            path = Path(str(source)+'-'+suffix); closures[str(path)] = verify(path)
        if closures[str(source)]['recorded_status'] != 'complete' or {p: verify(Path(p)) for p in closures} != closures: raise ValueError('protected closure changed')
        names = [CONTRACT, REVIEW, 'tools/demand_seasonal_risk.py', 'tools/demand_seasonal_risk_evaluation.py',
                 'tests/test_demand_seasonal_risk.py', *previous['source_pins']]
        pins = {p: pin(REPO/p) for p in dict.fromkeys(names)}
        if any(pins[p] != v for p, v in previous['source_pins'].items()): raise ValueError('protected source changed')
        config = json.loads((source/'config-before-input.json').read_bytes())
        state = json.loads((source/'source-final-state.json').read_bytes())
        if state['journal']['last_label_day'] >= '2015-01-01' or state['new_2015_fit']: raise ValueError('pre-2015 state required')
        files.write('contract.md', (REPO/CONTRACT).read_bytes()); files.write('astra-review.md', (REPO/REVIEW).read_bytes())
        files.json('sources.json', {p: (REPO/p).read_text() for p in pins})
        files.json('config-before-input.json', {'closures': closures, 'source_pins': pins, 'order': ORDER,
                   '2014_keys': config['2014_keys'], 'calibration_keys': config['calibration_keys'], 'selection_keys': config['selection_keys'],
                   'source_state_pin': pin(source/'source-final-state.json'), 'new_ridge_fits': 0, 'formal_permission': False})
        files.json('source-final-state.json', state)
        stage = '2014-complete-total-calibration'
        packets = json.loads((seasonal/'packets-and-inputs.json').read_bytes())
        by_key = {(r['store'], r['origin']): r for r in packets}
        cal_keys = set(map(tuple, config['calibration_keys'])); selected_keys = set(map(tuple, config['selection_keys']))
        calibration_rows = [by_key[tuple(k)] for k in config['calibration_keys']]
        policy, sample_journal = calibrate(calibration_rows)
        files.json('frozen-calibration.json', {'policy': policy, 'calibration_keys': config['calibration_keys'], 'observed_only': True, 'sample_journal': sample_journal})
        validation = [by_key[tuple(k)] for k in config['2014_keys']]
        labels = {(r['store'], r['origin']): r for r in validation}
        before = [frame(r, policy) for r in validation]
        obs, assumed, ledger = attach_scenarios(before, labels)
        files.json('2014-observed-labels.json', obs); files.json('2014-assumed-labels.json', assumed); files.json('2014-assumption-ledger.json', ledger)
        grouped, grouped_rows = {}, {}
        for mode, rows in (('observed', obs), ('assumed_missing_zero', assumed)):
            groups = groups_2014(rows, selected_keys, cal_keys); grouped_rows[mode] = groups
            if len(groups['normal120']) != 120 or len(groups['newyear']) != 10 or any(len(groups[f'normal_Q{q}']) != 30 for q in range(1, 5)):
                raise ValueError('disjoint ordinary quarters and newyear support required')
            for group, selected_rows in groups.items():
                grouped.setdefault(group, {})[mode] = {m: measure(selected_rows, lambda r, m=m: r['alternatives'][m]) for m in ORDER}
        stage = 'four-quarter-mean-risk-selection'
        selection = choose(grouped)
        for mode, groups in grouped_rows.items():
            for group, rows in groups.items():
                grouped[group][mode]['selected_policy'] = measure(rows, lambda r: r['alternatives'][selection['selected_by_quarter'][str(quarter(r['origin']))]])
        files.json('2014-evaluation.json', grouped)
        frozen = {'policy': policy, 'selection': selection, 'source_state_pin': pin(source/'source-final-state.json'),
                  'new_fit_after_2014': False, '2015_used': False}
        files.json('frozen-policy-before-2015.json', frozen); guard.check()
        print(json.dumps({'stage': 'frozen-before-2015', 'selection': selection}), flush=True)
        stage = 'signed-total-2015-forecasts'
        inputs = json.loads((source/'2015-inputs.json').read_bytes()); files.json('2015-inputs.json', inputs)
        total_changes = {}
        import math
        for cohort in ('original250', 'newyear10'):
            old = json.loads((source/(cohort+'-predictions-before-labels.json')).read_bytes())
            if len(old) != len(inputs[cohort]): raise ValueError('cohort size changed')
            forecasts[cohort] = [frame(r, policy, selection, old_row) for r, old_row in zip(inputs[cohort], old)]
            for row, old_row in zip(forecasts[cohort], old):
                if row['baseline_proxy'] != old_row['baseline_proxy']: raise ValueError('matched baseline changed')
            differences = [math.fsum(r['candidate'])-math.fsum(r['baseline_proxy']) for r in forecasts[cohort]]
            total_changes[cohort] = {'changed_windows': sum(abs(d)>1e-8 for d in differences), 'min': min(differences), 'max': max(differences)}
            files.json(cohort+'-predictions-before-labels.json', forecasts[cohort])
        stage = 'separate-2015-label-scenarios'
        measured, season_metrics = {}, {}
        for cohort in ('original250', 'newyear10'):
            labels = {(r['store'], r['origin']): r for r in json.loads((source/(cohort+'-observed-labels.json')).read_bytes())}
            obs, assumed, ledger = attach_scenarios(forecasts[cohort], labels)
            files.json(cohort+'-observed-labels.json', obs); files.json(cohort+'-assumed-labels.json', assumed); files.json(cohort+'-assumption-ledger.json', ledger)
            keys = [(r['store'], r['origin']) for r in obs]; measured[cohort] = {}
            for mode, rows in (('observed', obs), ('assumed_missing_zero', assumed)):
                measured[cohort][mode] = {'primary': score_cohort(rows, keys), 'selected_policy': measure(rows, lambda r: r['candidate']),
                                        'fixed_candidates': {m: measure(rows, lambda r, m=m: r['alternatives'][m]) for m in ORDER}}
                if cohort == 'original250':
                    for q in range(1, 5):
                        qs = [r for r in rows if quarter(r['origin']) == q]
                        season_metrics.setdefault(f'Q{q}', {})[mode] = {m: measure(qs, lambda r, m=m: r['alternatives'][m]) for m in ORDER}
                        season_metrics[f'Q{q}'][mode]['selected_policy'] = measure(qs, lambda r: r['candidate'])
            guard.check()
        files.json('2015-quarter-evaluation.json', season_metrics)
        if {p: verify(Path(p)) for p in closures} != closures or any(pin(REPO/p) != v for p, v in pins.items()): raise ValueError('protected source/closures changed')
        summary = {'status': 'complete', 'closures': closures, 'source_pins': pins, 'selection': selection, 'policy': policy,
                   'cohorts': measured, 'forecast_total_changes': total_changes, 'universal_window_guarantee': False, 'calibration_risk': 'observed complete totals only',
                   'source_final_windows': state['journal']['pool_windows'], 'source_last_label': state['journal']['last_label_day'],
                   'new_ridge_fits': 0, 'fit_after_2014': False, 'cohorts_combined': False, 'overlapping_store_days': 20,
                   'adopted': False, 'formal_permission': False, 'resources': guard.check(), 'seconds': time.monotonic()-STARTED}
        files.json('summary.json', summary); status = 'complete'
        print(json.dumps({'status': status, 'selected_by_quarter': selection['selected_by_quarter'], 'forecast_total_changes': total_changes,
                          'seconds': summary['seconds']}), flush=True)
    except BaseException as error:
        files.json('failure.json', {'stage': stage, 'type': type(error).__name__, 'message': str(error), 'traceback': traceback.format_exc()}, True)
        files.json('failure-prefix.json', {'policy': policy, 'forecasts': forecasts}, True); raise
    finally:
        files.json('root-closed.json', {'status': status, 'files': files.pins.copy(), 'immutable': True, 'formal_permission': False}, True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output.absolute())
