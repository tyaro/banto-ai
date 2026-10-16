"""A separate January 1 issue, with pre-2015 fits and unknown-zero labels."""
import time
STARTED = time.monotonic()
import argparse
import csv
import datetime as dt
import json
import math
from pathlib import Path
import sys
import traceback

from demand_autonomous_mean import FIT, assemble, read_history
from demand_rolling_ridge import select_pool, packetize, roll_period
from demand_macos_rebuild import pin, eval_metrics, PastOnly
from demand_sales_states import compose_sales, observation_state
from macos_demand_runtime import MacCheckpoint
from verify_demand_transfer import verify

REPO = Path(__file__).resolve().parents[1]
CONTRACT = 'docs/research/demand-newyear-evaluation-design-2026-10-15.md'
ORIGIN = dt.date(2015, 1, 1)
DAYS = tuple(ORIGIN+dt.timedelta(days=j) for j in range(14))
METHODS = ('baseline', 'candidate', 'raw_rolling')


def selected_label(row):
    # Target identity before interpreting quantity or observation mask.
    if row['store_nbr'] not in set(map(str, FIT)) or row['date'] not in set(map(str, DAYS)):
        return None
    s, day = int(row['store_nbr']), dt.date.fromisoformat(row['date'])
    if row['observed'] not in ('0', '1') or (row['observed'] == '1') != bool(row['sales']):
        raise ValueError('explicit selected observation mask required')
    value = None if row['observed'] == '0' else float(row['sales'])
    if value is not None and (not math.isfinite(value) or value < 0):
        raise ValueError('selected finite nonnegative target required')
    return s, day, value


def read_labels(path):
    values = {}
    with path.open(newline='') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ['store_nbr', 'date', 'sales', 'observed']:
            raise ValueError('closed snapshot schema changed')
        for row in reader:
            selected = selected_label(row)
            if selected is None:
                continue
            s, day, value = selected
            if (s, day) in values:
                raise ValueError('duplicate selected label')
            values[s, day] = value
    if set(values) != {(s, day) for s in FIT for day in DAYS}:
        raise ValueError('complete selected calendar required')
    return values


def subset_daily(rows, method, kind):
    by_store = {}
    for s in FIT:
        pairs = [(p, y, row['scale']) for row in rows if row['store'] == s
                 for p, y in zip(row[method], row['actual']) if y is not None
                 and ((y == 0) if kind == 'zero' else (y > 0))]
        if not pairs:
            by_store[str(s)] = {'count': 0, 'scaled_MSE': None, 'MAE': None, 'bias': None,
                                'mean_prediction': None, 'WAPE_percent': None, 'overpredicted': 0, 'point_zero': 0}
            continue
        errors = [p-y for p, y, _ in pairs]; n = len(pairs); volume = math.fsum(y for _, y, _ in pairs)
        by_store[str(s)] = {'count': n, 'scaled_MSE': math.fsum(((p-y)/u)**2 for p, y, u in pairs)/n,
                            'MAE': math.fsum(abs(e) for e in errors)/n, 'bias': math.fsum(errors)/n,
                            'mean_prediction': math.fsum(p for p, _, _ in pairs)/n,
                            'WAPE_percent': 100*math.fsum(abs(e) for e in errors)/volume if volume else None,
                            'overpredicted': sum(p > y for p, y, _ in pairs), 'point_zero': sum(p == 0 for p, _, _ in pairs)}
    fields = ('scaled_MSE', 'MAE', 'bias', 'mean_prediction', 'WAPE_percent')
    macro = {k: math.fsum(v[k] for v in by_store.values())/10 if all(v[k] is not None for v in by_store.values()) else None for k in fields}
    macro.update({k: sum(v[k] for v in by_store.values()) for k in ('count', 'overpredicted', 'point_zero')})
    return {'macro': macro, 'per_store': by_store}


def evaluate(rows, scales):
    if len(rows) != 10 or {(r['store'], r['origin']) for r in rows} != {(s, str(ORIGIN)) for s in FIT}:
        raise ValueError('separate fixed 10-window grid required')
    for row in rows:
        if row['scale'] != scales[row['store']] or row['scale'] <= 0 or len(row['actual']) != 14:
            raise ValueError('fixed positive scale and 14 label calendar required')
        if type(row['complete_label']) is not bool or row['complete_label'] != all(v is not None for v in row['actual']):
            raise ValueError('explicit complete label mask required')
        for values in [row[m] for m in METHODS]:
            if len(values) != 14 or any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in values):
                raise ValueError('invalid nonnegative saved mean')
        if any(v is not None and (type(v) not in (int, float) or not math.isfinite(v) or v < 0) for v in row['actual']):
            raise ValueError('invalid observed target')
    by_store = {str(s): {m: eval_metrics([r for r in rows if r['store'] == s], scales[s], m) for m in METHODS} for s in FIT}
    fields = ('daily', 'total', 'joint', 'daily_MAE', 'total_MAE', 'daily_bias', 'total_bias', 'daily_WAPE_percent', 'total_WAPE_percent')
    macro = {m: {f: math.fsum(v[m][f] for v in by_store.values())/10
                 if all(v[m][f] is not None for v in by_store.values()) else None for f in fields} for m in METHODS}
    return {'macro': macro, 'per_store': by_store, 'daily_subsets': {kind: {m: subset_daily(rows, m, kind) for m in METHODS} for kind in ('zero', 'positive')},
            'requested': 10, 'observed_daily': sum(v is not None for r in rows for v in r['actual']),
            'complete_totals': sum(r['complete_label'] for r in rows),
            'improved_stores': sum(by_store[str(s)]['candidate']['joint'] < by_store[str(s)]['baseline']['joint'] for s in FIT)
                               if all(by_store[str(s)][m]['joint'] is not None for s in FIT for m in ('baseline', 'candidate')) else None,
            'improvement_percent': 100*(macro['baseline']['joint']-macro['candidate']['joint'])/macro['baseline']['joint']
                                   if macro['baseline']['joint'] is not None and macro['baseline']['joint'] > 0 and macro['candidate']['joint'] is not None else None,
            'weighting': 'equal fixed ten stores; zero/positive subsets are daily only'}


def run(output):
    guard = MacCheckpoint(seconds=870)
    import torch
    from demand_calendar_train import Files
    root = output.absolute()
    if root.parent != REPO/'artifacts' or root.exists():
        raise ValueError('fresh output root required')
    files = Files(root); status, stage, rows, journal = 'failed', 'source', [], []
    source = REPO/'artifacts/macos-demand-sales-state-20261015'
    try:
        if sys.version_info[:3] != (3, 14, 8) or sys.platform != 'darwin' or torch.__version__ != '2.14.0':
            raise ValueError('fixed Mac runtime required')
        source_closure = verify(source)
        prior = json.loads((source/'summary.json').read_bytes())
        roots = {k: Path(v['root']) for k, v in prior['source_roots'].items()}
        roots['prior_primary'] = Path(prior['primary_root']['root'])
        closures = {k: verify(p) for k, p in roots.items()}
        if source_closure['recorded_status'] != 'complete' or any(v['recorded_status'] != 'complete' for v in closures.values()):
            raise ValueError('complete closed sources required')
        names = [CONTRACT, 'tools/demand_newyear_evaluation.py', 'tests/test_demand_newyear_evaluation.py', *prior['source_pins']]
        sources = {p: (REPO/p).read_bytes() for p in dict.fromkeys(names)}
        if any(pin(sources[p]) != expected for p, expected in prior['source_pins'].items()):
            raise ValueError('pinned source changed')
        binding = json.loads((roots['prior_primary']/'binding.json').read_bytes())
        scales = {int(s): v['scale'] for s, v in binding['scales'].items()}
        enabled = binding['support']['enabled']
        selection = prior['fixed_prior_selection']
        if selection['selected'] != 'rolling_calibrated':
            raise ValueError('fixed main method changed')
        alpha = selection['alphas']['rolling']['alpha']
        occurrence = json.loads((source/'occurrence-state.json').read_bytes())
        torch.set_num_threads(2); torch.set_num_interop_threads(1); torch.use_deterministic_algorithms(True)
        files.write('contract.md', sources[CONTRACT]); files.json('sources.json', {p: b.decode() for p, b in sources.items()})
        files.json('config-before-input.json', {'origin': str(ORIGIN), 'days': list(map(str, DAYS)), 'methods': METHODS,
                   'original250_separate': True, 'overlap_old_store_days': 20, 'fixed_selection': selection,
                   'occurrence': occurrence, 'operating_records': [], 'operating_status': 'unknown',
                   'source_closure': source_closure, 'source_roots': closures,
                   'source_pins': {p: pin(b) for p, b in sources.items()}, 'formal_permission': False})
        stage = 'metadata-before-training-targets'
        headers = [{'store': s, 'origin': text, 'complete_label': True} for s, text in binding['fit_keys']+binding['time_keys']]
        selected = select_pool(headers, ORIGIN)
        if len(selected) != 210 or any(sum(p['store'] == s for p in selected) != 21 for s in FIT):
            raise ValueError('fixed pre-January fit support changed')
        history = read_history(roots['original']/'selected-internal.csv', dt.date(2013, 1, 1), dt.date(2014, 12, 31))
        packets, profiles = packetize(history, [(p['store'], p['origin']) for p in selected], scales, enabled, guard.check)
        files.json('training-profiles.json', profiles)
        stage = 'january-inputs-before-labels'
        keys = [(s, str(ORIGIN)) for s in FIT]
        x, e, profiles, raw = assemble(history, keys, scales, enabled, guard.check)
        files.json('january-profiles.json', profiles)
        forecast_packets = [{'store': s, 'origin': str(ORIGIN), 'scale': scales[s], 'baseline': x[k]['baseline'],
                             'raw': raw[k], 'actual': None, 'complete_label': False} for k, s in enumerate(FIT)]
        stage = 'one-past-only-ridge-solve'
        predictions, journal, _ = roll_period(packets, forecast_packets, guard.check)
        if len(journal) != 1 or journal[0]['fallback'] or journal[0]['last_label_day'] >= str(ORIGIN):
            raise ValueError('pre-origin ridge support or cutoff changed')
        files.json('january-state-journal.json', journal)
        files.json('training-packet-labels.json', [{'store': p['store'], 'origin': p['origin'], 'actual': p['actual'],
                   'complete_label': p['complete_label']} for p in packets])
        ledgers = []
        for prediction in predictions:
            blended = [b+alpha*(p-b) for b, p in zip(prediction['baseline'], prediction['rolling_raw'])]
            means = dict(zip(DAYS, blended))
            composed = compose_sales(means, means, [], list(DAYS),
                                     dt.datetime(2015, 1, 1, tzinfo=dt.timezone(dt.timedelta(hours=-5))),
                                     prediction['store'], occurrence, closed_implies_zero=True)
            rows.append({'store': prediction['store'], 'origin': str(ORIGIN), 'scale': prediction['scale'],
                         'baseline': prediction['baseline'], 'raw_rolling': prediction['rolling_raw'],
                         'candidate': [r['sales_mean'] for r in composed['daily']], 'operating_status': ['unknown']*14})
            ledgers.append({'origin': str(ORIGIN), **composed})
        files.json('operating-predictions.json', ledgers); files.json('predictions-before-labels.json', rows)
        stage = 'selected-2015-labels-after-forecast'
        labels = read_labels(roots['development']/'selected-existing-stores.csv')
        labelled, states = [], []
        counts = {}
        for row in rows:
            actual = [labels[row['store'], day] for day in DAYS]
            labelled.append({**row, 'actual': actual, 'complete_label': all(v is not None for v in actual)})
            for day, value in zip(DAYS, actual):
                state = observation_state('unknown', value, value is not None)
                counts[state] = counts.get(state, 0)+1
                states.append({'store': row['store'], 'date': str(day), 'operating_status': 'unknown',
                               'quantity': value, 'observed': value is not None, 'observation_state': state})
        files.json('predictions-and-labels.json', labelled); files.json('label-state-ledger.json', states)
        measured = evaluate(labelled, scales)
        if counts != {'unknown_zero': 10, 'unknown_positive': 130} or measured['complete_totals'] != 10:
            raise ValueError('January zero exposure/support changed')
        if (verify(source) != source_closure or {k: verify(p) for k, p in roots.items()} != closures
                or any((REPO/p).read_bytes() != b for p, b in sources.items())):
            raise ValueError('original source/root changed')
        summary = {'status': 'complete', 'source_closure': source_closure, 'source_roots': closures,
                   'source_pins': {p: pin(b) for p, b in sources.items()}, 'fixed_selection': selection,
                   'alpha': alpha, 'observation_state_counts': counts, 'forecast_status_counts': {'unknown': 140},
                   'confirmed_closed_days': 0, 'holiday_forced_zero_days': 0, 'new_ridge_fits': 1,
                   'new_nn_fit': False, 'original250_recomputed': False, 'scores_combined_with_original250': False,
                   'original250_reference': {'macro': prior['macro'], 'requested': 250, 'daily': 3490, 'complete_totals': 240,
                                              'improvement_percent': prior['primary_development_decision']['improvement_percent']},
                   'overlap_with_original250_store_days': 20, 'zero_cause_identified': False,
                   'adopted': False, 'formal_permission': False, 'resources': guard.check(),
                   'seconds': time.monotonic()-STARTED, **measured}
        files.json('summary.json', summary); status = 'complete'
        print(json.dumps({'status': status, 'macro': measured['macro'], 'zero_daily': measured['daily_subsets']['zero'],
                         'improvement_percent': measured['improvement_percent'], 'observation_states': counts,
                         'seconds': summary['seconds']}), flush=True)
    except BaseException as error:
        files.json('failure.json', {'stage': stage, 'type': type(error).__name__, 'message': str(error),
                                  'traceback': traceback.format_exc()}, True)
        files.json('failure-prefix.json', {'rows': rows, 'journal': journal}, True)
        raise
    finally:
        files.json('root-closed.json', {'status': status, 'files': files.pins.copy(), 'immutable': True,
                                     'formal_permission': False}, True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
