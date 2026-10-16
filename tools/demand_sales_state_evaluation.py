"""One fixed 2015 composition/evaluation; unavailable operating plans stay unknown."""
import time
STARTED = time.monotonic()
import argparse
import datetime as dt
import json
from pathlib import Path
import sys
import traceback

from demand_autonomous_mean import FIT, ORIGINS, read_history, development_metrics
from demand_macos_rebuild import pin
from demand_sales_states import observation_state, fit_occurrence, compose_sales
from macos_demand_runtime import MacCheckpoint
from verify_demand_transfer import verify

REPO = Path(__file__).resolve().parents[1]
CONTRACT = 'docs/research/demand-sales-state-design-2026-10-15.md'


def run(output):
    guard = MacCheckpoint(seconds=870)
    from demand_calendar_train import Files
    root = output.absolute()
    if root.parent != REPO/'artifacts' or root.exists():
        raise ValueError('fresh artifact root required')
    files = Files(root); status, stage, rows = 'failed', 'source', []
    primary = REPO/'artifacts/macos-demand-temporal-selection-20261015'
    try:
        if sys.version_info[:3] != (3, 14, 8) or sys.platform != 'darwin':
            raise ValueError('fixed Mac Python required')
        closure = verify(primary)
        prior = json.loads((primary/'summary.json').read_bytes())
        roots = {k: Path(v['root']) for k, v in prior['source_roots'].items()}
        closures = {k: verify(p) for k, p in roots.items()}
        if closure['recorded_status'] != 'complete' or closures != prior['source_roots']:
            raise ValueError('closed sources changed')
        names = [CONTRACT, 'tools/demand_sales_states.py', 'tools/demand_sales_state_evaluation.py',
                 'tests/test_demand_sales_states.py', 'tools/demand_event_calendar.py',
                 'tools/demand_event_intervals.py', *prior['source_pins']]
        sources = {p: (REPO/p).read_bytes() for p in dict.fromkeys(names)}
        if any(pin(sources[p]) != expected for p, expected in prior['source_pins'].items()):
            raise ValueError('previous source changed')
        files.write('contract.md', sources[CONTRACT]); files.json('sources.json', {p: b.decode() for p, b in sources.items()})
        binding = json.loads((primary/'binding.json').read_bytes())
        scales = {int(s): v['scale'] for s, v in binding['scales'].items()}
        config = {'primary_root': closure, 'source_roots': closures, 'source_pins': {p: pin(b) for p, b in sources.items()},
                  'fixed_primary_selection': prior['selection'], 'new_nn_fit': False, 'new_ridge_fit': False,
                  'closed_implies_zero': True, 'operating_records': [],
                  'operating_source_reason': 'no verified as-of store operating plans in authorized snapshots',
                  'holiday_implies_closed': False, 'zero_quantity_implies_closed': False,
                  'missing_implies_zero': False, 'target': 'observed_sales_mean', 'formal_permission': False}
        files.json('config-before-input.json', config); guard.check()
        stage = 'fit-occurrence-support-only'
        history = read_history(roots['original']/'selected-internal.csv', dt.date(2013, 1, 1), dt.date(2014, 12, 31))
        samples = []
        for s, text in binding['fit_keys']:
            origin = dt.date.fromisoformat(text)
            if s not in FIT or origin+dt.timedelta(days=13) >= dt.date(2014, 7, 1):
                raise ValueError('fixed fit boundary changed')
            for j in range(14):
                day = origin+dt.timedelta(days=j); quantity = history[s].get(day)
                samples.append({'store': s, 'date': str(day), 'quantity': quantity,
                                'observed': quantity is not None, 'operating_status': 'unknown'})
        occurrence = fit_occurrence(samples)
        if occurrence['eligible_distinct_labels'] != 4200 or occurrence['observation_classes'] != {'unknown_positive': 4200}:
            raise ValueError('predeclared all-positive fit support changed')
        files.json('fit-occurrence-labels.json', samples); files.json('occurrence-state.json', occurrence)
        files.json('frozen-composition-before-development.json', {'source_selection': prior['selection'],
                   'occurrence': occurrence, 'operating_records': [], 'holiday_implies_closed': False,
                   'closed_implies_zero': True, 'no_development_selection': True,
                   'probability_model_supported': False, 'probability_one_claimed_as_fitted': False})
        stage = 'development-prediction-composition'
        before = json.loads((primary/'predictions-before-labels.json').read_bytes())
        expected = {(s, str(day)) for s in FIT for day in ORIGINS}
        if len(before) != 250 or {(r['store'], r['origin']) for r in before} != expected:
            raise ValueError('fixed development grid changed')
        ledgers = []
        for row in before:
            origin = dt.date.fromisoformat(row['origin']); days = [origin+dt.timedelta(days=j) for j in range(14)]
            means = dict(zip(days, row['candidate']))
            composed = compose_sales(means, means, [], days,
                                     dt.datetime.combine(origin, dt.time(), dt.timezone(dt.timedelta(hours=-5))),
                                     row['store'], occurrence, closed_implies_zero=True)
            if not composed['total_available']:
                raise ValueError('fixed demand support became unavailable')
            rows.append({**row, 'prior_primary': row['candidate'],
                         'candidate': [v['sales_mean'] for v in composed['daily']]})
            ledgers.append({'store': row['store'], 'origin': row['origin'], **composed})
            guard.check()
        files.json('operating-and-occurrence-predictions.json', ledgers)
        files.json('predictions-before-labels.json', rows)
        stage = 'labels-after-fixed-predictions'
        original_labels = {(r['store'], r['origin']): r for r in json.loads((primary/'predictions-and-labels.json').read_bytes())}
        lookup = {(r['store'], r['origin']): r for r in ledgers}
        labelled, classified, counts = [], [], {}
        for row in rows:
            old = original_labels[row['store'], row['origin']]
            labelled.append(row | {'actual': old['actual'], 'complete_label': old['complete_label']})
            for j, actual in enumerate(old['actual']):
                forecast = lookup[row['store'], row['origin']]['daily'][j]
                state = observation_state(forecast['operating_status'], actual, actual is not None)
                counts[state] = counts.get(state, 0)+1
                classified.append({'store': row['store'], 'origin': row['origin'], 'date': forecast['date'],
                                   'operating_status': forecast['operating_status'], 'observed': actual is not None,
                                   'quantity': actual, 'observation_state': state})
        if counts != {'unknown_positive': 3490, 'missing': 10}:
            raise ValueError('predeclared label exposure changed')
        files.json('predictions-and-labels.json', labelled); files.json('label-state-ledger.json', classified)
        stage = 'fixed-evaluation'
        measured = development_metrics(labelled, scales)
        if measured['macro'] != prior['macro'] or any(r['candidate'] != r['prior_primary'] for r in rows):
            raise ValueError('unknown/unsupported composition must preserve prior forecast')
        if (verify(primary) != closure or {k: verify(p) for k, p in roots.items()} != closures
                or any((REPO/p).read_bytes() != raw for p, raw in sources.items())):
            raise ValueError('source/root changed')
        summary = {'status': 'complete', 'primary_root': closure, 'source_roots': closures,
                   'source_pins': {p: pin(b) for p, b in sources.items()}, 'fixed_prior_selection': prior['selection'],
                   'occurrence_training_support': occurrence, 'forecast_status_counts': {'unknown': 3500},
                   'observation_state_counts': counts, 'confirmed_closed_days': 0, 'known_open_days': 0,
                   'unknown_zero_labels': 0, 'observed_zero_labels': 0, 'missing_labels': 10,
                   'unsupported_probability_fallback_days': 3500, 'fitted_probability_one_claims': 0,
                   'forced_holiday_zero_days': 0, 'new_closed_or_open_zero_accuracy_measurable': False,
                   'difference_from_prior_primary_joint': measured['macro']['candidate']['joint']-prior['macro']['candidate']['joint'],
                   'new_nn_fit': False, 'new_ridge_fit': False, 'new_model_forward': False,
                   'resources': guard.check(), 'seconds': time.monotonic()-STARTED,
                   'adopted': False, 'formal_permission': False, **measured}
        files.json('summary.json', summary); status = 'complete'
        print(json.dumps({'status': status, 'observation_states': counts, 'macro': measured['macro'],
                         'decision': measured['primary_development_decision'], 'additional_joint_gain': 0.,
                         'zero_accuracy_measurable': False, 'seconds': summary['seconds']}), flush=True)
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
