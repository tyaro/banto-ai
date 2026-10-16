"""Frozen recurring past-zero/missing proxy; paired observed and assumption scores."""
import time
STARTED = time.monotonic()
import argparse
import csv
import json
from pathlib import Path
import sys
import traceback

from demand_recurring_closure import FIT, learn_pattern, apply_pattern, attach_scenarios, score_cohort
from macos_demand_runtime import MacCheckpoint
from verify_demand_transfer import verify, pin

REPO = Path(__file__).resolve().parents[1]
CONTRACT = 'docs/research/demand-recurring-closure-design-2026-10-15.md'


def run(output):
    guard = MacCheckpoint(seconds=870)
    sys.path.insert(0, str(REPO/'models/mini-transformer'))
    from demand_calendar_train import Files
    root = output.absolute()
    if root.parent != REPO/'artifacts' or root.exists():
        raise ValueError('fresh root required')
    files = Files(root); status, stage, forecasts = 'failed', 'source', {}
    roots = {'original250': REPO/'artifacts/macos-demand-sales-state-20261015',
             'newyear10': REPO/'artifacts/macos-demand-newyear-2015-20261015-v2'}
    try:
        if sys.version_info[:3] != (3, 14, 8) or sys.platform != 'darwin':
            raise ValueError('fixed Mac Python required')
        closures = {k: verify(p) for k, p in roots.items()}
        prior = {k: json.loads((p/'summary.json').read_bytes()) for k, p in roots.items()}
        protected = {v['root']: v for p in prior.values() for v in p['source_roots'].values()}
        for p in prior.values():
            key = 'primary_root' if 'primary_root' in p else 'source_closure'
            protected[p[key]['root']] = p[key]
        if any(v['recorded_status'] != 'complete' for v in closures.values()) or {p: verify(Path(p)) for p in protected} != protected:
            raise ValueError('closed original roots changed')
        source_pins = {name: expected for p in prior.values() for name, expected in p['source_pins'].items()}
        if any(pin(REPO/name) != expected for name, expected in source_pins.items()):
            raise ValueError('original source changed')
        names = [CONTRACT, 'tools/demand_recurring_closure.py', 'tools/demand_recurring_closure_evaluation.py',
                 'tests/test_demand_recurring_closure.py', *source_pins]
        sources = {name: (REPO/name).read_bytes() for name in dict.fromkeys(names)}
        pins = {name: {'bytes': len(raw), 'sha256': __import__('hashlib').sha256(raw).hexdigest()} for name, raw in sources.items()}
        files.write('contract.md', sources[CONTRACT]); files.json('sources.json', {p: raw.decode() for p, raw in sources.items()})
        files.json('config-before-history.json', {'training_years': [2013, 2014], 'freeze_exclusive': '2015-01-01',
                   'shared_all_ten_store_rule': True, 'all_original_masks_retained': True,
                   'matched_baseline_same_mask': True, 'source_roots': closures, 'protected_roots': protected,
                   'source_pins': pins, 'new_model_fit': False, 'new_model_forward': False, 'formal_permission': False})
        stage = 'past-calendar-only-pattern'
        original = Path(prior['original250']['source_roots']['original']['root'])
        rows = []
        with (original/'selected-internal.csv').open(newline='') as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != ['store_nbr', 'date', 'sales', 'observed']:
                raise ValueError('original schema changed')
            for r in reader:
                if r['store_nbr'] not in set(map(str, FIT)) or not '2013-01-01' <= r['date'] < '2015-01-01':
                    continue
                if r['observed'] not in ('0', '1') or (r['observed'] == '1') != bool(r['sales']):
                    raise ValueError('historical mask changed')
                rows.append({'store': int(r['store_nbr']), 'date': r['date'], 'observed': r['observed'] == '1',
                             'quantity': float(r['sales']) if r['observed'] == '1' else None})
        state = learn_pattern(rows)
        files.json('historical-calendar-ledger.json', rows)
        files.json('frozen-pattern-before-2015.json', state); guard.check()
        stage = 'apply-frozen-pattern-before-labels'
        keys = {}
        for name, path in roots.items():
            before = json.loads((path/'predictions-before-labels.json').read_bytes())
            keys[name] = [(r['store'], r['origin']) for r in before]
            if len(before) != (250 if name == 'original250' else 10):
                raise ValueError('fixed old cohort changed')
            forecasts[name] = [apply_pattern(r, state) for r in before]
            files.json(name+'-predictions-before-labels.json', forecasts[name])
        stage = 'observed-and-assumption-scoring'
        measured = {}
        for name, path in roots.items():
            labels = {(r['store'], r['origin']): r for r in json.loads((path/'predictions-and-labels.json').read_bytes())}
            observed, assumed, ledger = attach_scenarios(forecasts[name], labels)
            files.json(name+'-observed-labels.json', observed)
            files.json(name+'-assumed-labels.json', assumed)
            files.json(name+'-assumption-ledger.json', ledger)
            measured[name] = {'observed': score_cohort(observed, keys[name]), 'assumed_missing_zero': score_cohort(assumed, keys[name]),
                             'predicted_assumed_closure_days': sum(sum(r['assumed_closure']) for r in forecasts[name]),
                             'positive_contradictions': sum(r['assumption_contradicted_by_positive'] for r in ledger),
                             'original_reference_macro': prior[name]['macro']}
            # The prior means' observed metrics must be exactly their saved values.
            if measured[name]['observed']['macro']['prior'] != prior[name]['macro']['candidate']:
                raise ValueError('original observed scoring changed')
            guard.check()
        if ({k: verify(p) for k, p in roots.items()} != closures or {p: verify(Path(p)) for p in protected} != protected
                or any(pin(REPO/name) != expected for name, expected in pins.items())):
            raise ValueError('original root/source changed')
        summary = {'status': 'complete', 'source_roots': closures, 'protected_roots': protected, 'source_pins': pins,
                   'frozen_pattern': state, 'cohorts': measured, 'cohorts_combined': False, 'overlapping_store_days': 20,
                   'confirmed_closure_claim': False, 'independent_training_years': 2,
                   'new_model_fit': False, 'new_model_forward': False, 'adopted': False, 'formal_permission': False,
                   'resources': guard.check(), 'seconds': time.monotonic()-STARTED}
        files.json('summary.json', summary); status = 'complete'
        print(json.dumps({'status': status, 'pattern_monthdays': [p['month_day'] for p in state['patterns']],
                         'cohorts': {k: {v: {'macro': x['macro'], 'gains': x['improvement_percent_over'],
                                            'scored_daily': x['scored_daily'], 'complete_totals': x['complete_totals'],
                                            'imputed': x['imputed_missing_zero']} for v, x in values.items() if v in ('observed', 'assumed_missing_zero')}
                                     for k, values in measured.items()}, 'seconds': summary['seconds']}), flush=True)
    except BaseException as error:
        files.json('failure.json', {'stage': stage, 'type': type(error).__name__, 'message': str(error), 'traceback': traceback.format_exc()}, True)
        files.json('failure-prefix.json', {'forecasts': forecasts}, True)
        raise
    finally:
        files.json('root-closed.json', {'status': status, 'files': files.pins.copy(), 'immutable': True,
                                     'formal_permission': False}, True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
