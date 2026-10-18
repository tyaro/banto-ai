"""CARE practical evaluation: score every method after the freeze (labels are read only here).

Conditions: examples/configs/care-a-maintenance-practical-20261017.json. The inherited metrics
follow models/mini-transformer/care_score.py exactly; the saved own-model and baseline results
must reproduce the saved metrics before anything new is reported. Added: detection at lead times
W = 0/24/72/168 h with attainability, false alarms per asset per 30 days, a per-event table.

    python3 tools/care_practical_score.py --campaign artifacts/care-fm-20261017
"""
import argparse
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path = [p for p in sys.path if Path(p or '.').resolve() != Path(__file__).resolve().parent]
sys.path[:0] = [str(ROOT/'models/mini-transformer'), str(ROOT)]
from care_alarm import COMMON, PREDICTION, active_seconds, eligible_seconds, event_result  # noqa: E402
from tools.care_fm import verify_closed  # noqa: E402

SAVED = ('neural-common', 'baseline-common', 'baseline-native')
FOUNDATION = ('timesfm3', 'chronos2', 'toto2')
LEADS = (0, 24, 72, 168)
MONTH_HOURS = 720
EVALUATOR = ROOT/'artifacts/care-evaluator-contract-20261016'
SCORES = ROOT/'artifacts/care-learning-scores-20261016'
LABEL_SHA = '22df6b500574223d6754fa9c8bb158259f374898225cbddea1771f4662fbff3d'  # pins in care_score.py
EVALUATION_SHA = 'a075209d77145540dcb1a535475c369820c507c206b5d99307a32d410d1cb361'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, data):
    with open(path, 'xb') as f:
        f.write(json.dumps(data, indent=1).encode())


def fold_root(k):
    return ROOT/f'artifacts/care-learning-fold-{k}-20261016'


def load_methods(frozen):
    """Rows and episodes per method and event: saved methods from the fold roots, foundation
    models from the frozen campaign. Alarm semantics of a foundation model = 'neural-common'."""
    rows, alarms = {m: {} for m in SAVED+FOUNDATION}, {m: {} for m in SAVED+FOUNDATION}
    for k in range(5):
        saved = list(PREDICTION.iter_unpack((fold_root(k)/'test.bin').read_bytes()))
        eps = json.loads((fold_root(k)/'episodes.json').read_bytes())
        for event in sorted({r[0] for r in saved}):
            part = [r for r in saved if r[0] == event]
            for m in SAVED:
                rows[m][event] = part; alarms[m][event] = eps[str(event)][m]
        for m in FOUNDATION:
            fm = list(PREDICTION.iter_unpack((frozen/m/f'fold-{k}'/'test-rows.bin').read_bytes()))
            feps = json.loads((frozen/m/f'fold-{k}'/'episodes.json').read_bytes())
            for event in sorted({r[0] for r in fm}):
                rows[m][event] = [r for r in fm if r[0] == event]; alarms[m][event] = feps[str(event)]
    return rows, alarms


def semantics(m):
    return m if m in SAVED else 'neural-common'


def score(truth, meta, rows, alarms):
    per_asset = {m: {} for m in rows}; per_event = []
    for t in truth:
        event = int(t['event_id']); asset = t['asset_key']; base = datetime.fromisoformat(meta[event]['first_timestamp'])
        start = int((datetime.fromisoformat(t['event_start'])-base).total_seconds())+600
        end = int((datetime.fromisoformat(t['event_end'])-base).total_seconds())+600
        interval = [r for r in rows['neural-common'][event] if int(t['event_start_id']) <= r[2] <= int(t['event_end_id'])]
        assert interval and interval[0][4] == start and interval[-1][4] == end, 'label timestamp/ID alignment'
        out = {'event_id': event, 'asset_key': asset, 'event_label': t['event_label'], 'start': start, 'end': end,
               'interval_hours': (end-start)/3600, 'attainable': {str(w): end-start >= w*3600 for w in LEADS}, 'methods': {}}
        for m in rows:
            s = per_asset[m].setdefault(asset, {'anomaly_events': 0, 'hits': 0, 'earliness_sum': 0., 'normal_files': 0, 'normal_seconds': 0,
                                                'normal_active_seconds': 0, 'false_episodes': 0, 'hits_at': {str(w): 0 for w in LEADS},
                                                'attainable_at': {str(w): 0 for w in LEADS}, 'mae_sum': [0., 0.], 'mae_n': 0})
            part = rows[m][event]; eps = alarms[m][event]; kind = semantics(m)
            seconds = eligible_seconds(part, kind); active = active_seconds(part, kind, eps)
            d = {'episodes': len(eps), 'eligible_seconds': seconds}
            if t['event_label'] == 'anomaly':
                er = event_result(eps, start, end); s['anomaly_events'] += 1; s['hits'] += er['hit']; s['earliness_sum'] += er['earliness']
                for w in LEADS:
                    hit = er['hit'] and er['first_open'] <= end-w*3600
                    s['hits_at'][str(w)] += hit; s['attainable_at'][str(w)] += end-start >= w*3600
                    d[f'hit_{w}h'] = hit
                d.update(hit=er['hit'], first_open=er['first_open'], lead_proxy_hours=None if er['lead_proxy_seconds'] is None else er['lead_proxy_seconds']/3600,
                         earliness=er['earliness'], active_before_start=len(er['already_active_before_start']), off_window=len(er['off_window_episodes']))
            else:
                assert t['event_label'] == 'normal'
                s['normal_files'] += 1; s['normal_seconds'] += seconds; s['normal_active_seconds'] += active; s['false_episodes'] += len(eps)
                d['false_episodes'] = len(eps)
            pred = 10 if m.startswith('baseline') else 8
            common = [r for r in part if r[5] & COMMON]
            for v in range(2):
                s['mae_sum'][v] += math.fsum(abs(r[6+v]-r[pred+v]) for r in common)
            s['mae_n'] += len(common); out['methods'][m] = d
        per_event.append(out)
    results = {}
    for m, stats in per_asset.items():
        for s in stats.values():
            s['recall'] = s['hits']/s['anomaly_events'] if s['anomaly_events'] else None
            s['earliness'] = s['earliness_sum']/s['anomaly_events'] if s['anomaly_events'] else None
            rate = s['false_episodes']*3600*1000/s['normal_seconds'] if s['normal_seconds'] else None
            s['false_episodes_per_1000_record_hours'] = rate
            s['false_episodes_per_asset_30_days'] = rate*MONTH_HOURS/1000 if rate is not None else None
            s['normal_alarm_fraction'] = s['normal_active_seconds']/s['normal_seconds'] if s['normal_seconds'] else None
            s['recall_at'] = {w: s['hits_at'][w]/s['anomaly_events'] for w in s['hits_at']} if s['anomaly_events'] else None
        def mean(key, sub=None):
            xs = [(s[key] if sub is None else s[key][sub]) for s in stats.values() if s[key] is not None]
            return math.fsum(xs)/len(xs) if xs else None
        macro = {k: mean(k) for k in ('recall', 'false_episodes_per_1000_record_hours', 'normal_alarm_fraction', 'earliness', 'false_episodes_per_asset_30_days')}
        macro['recall_at'] = {str(w): mean('recall_at', str(w)) for w in LEADS}
        keys = ('anomaly_events', 'hits', 'normal_files', 'normal_seconds', 'normal_active_seconds', 'false_episodes', 'mae_n')
        pooled = {k: sum(s[k] for s in stats.values()) for k in keys}
        pooled.update(recall=pooled['hits']/pooled['anomaly_events'], earliness=math.fsum(s['earliness_sum'] for s in stats.values())/pooled['anomaly_events'],
                      false_episodes_per_1000_record_hours=pooled['false_episodes']*3600*1000/pooled['normal_seconds'],
                      normal_alarm_fraction=pooled['normal_active_seconds']/pooled['normal_seconds'],
                      hits_at={str(w): sum(s['hits_at'][str(w)] for s in stats.values()) for w in LEADS},
                      attainable_at={str(w): sum(s['attainable_at'][str(w)] for s in stats.values()) for w in LEADS},
                      lead1_mae_common_thermal=[math.fsum(s['mae_sum'][v] for s in stats.values())/pooled['mae_n'] for v in range(2)])
        pooled['false_episodes_per_asset_30_days'] = pooled['false_episodes_per_1000_record_hours']*MONTH_HOURS/1000
        results[m] = {'asset_macro': macro, 'pooled': pooled, 'per_asset': stats}
    return results, per_event


def reproduce_saved(results):
    """The saved own-model and baseline metrics must come out unchanged."""
    saved = json.loads((SCORES/'metrics.json').read_bytes()); checks = {}
    close = lambda a, b: a is None and b is None or math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)
    for m in SAVED:
        for k in ('recall', 'false_episodes_per_1000_record_hours', 'normal_alarm_fraction', 'earliness'):
            assert close(results[m]['asset_macro'][k], saved[m]['asset_macro'][k]), (m, k)
        for k in ('anomaly_events', 'hits', 'normal_files', 'normal_seconds', 'normal_active_seconds', 'false_episodes'):
            assert results[m]['pooled'][k] == saved[m]['pooled'][k], (m, k)
        for v in range(2):
            assert close(results[m]['pooled']['lead1_mae_common_thermal'][v], saved[m]['pooled']['lead1_mae_common_thermal'][v]), (m, 'mae')
        checks[m] = 'reproduced'
    return checks


def main(campaign):
    campaign = Path(campaign); frozen = campaign/'frozen'; out = campaign/'scores'
    verify_closed(frozen)
    freeze = json.loads((frozen/'freeze.json').read_bytes())
    assert not freeze['labels_read'] and not freeze['any_unsupported_stop'], 'freeze stopped or already read labels'
    out.mkdir()
    write_new(out/'before-labels.json', {'frozen_closure_sha256': digest(frozen/'root-closed.json'), 'labels_opened_yet': False,
                                         'fold_roots': {k: digest(fold_root(k)/'root-closed.json') for k in range(5)}})
    rows, alarms = load_methods(frozen)
    # First label access, after the freeze record above.
    verify_closed(EVALUATOR)
    assert digest(EVALUATOR/'label-manifest.json') == LABEL_SHA and digest(EVALUATOR/'evaluation.json') == EVALUATION_SHA
    truth = json.loads((EVALUATOR/'label-manifest.json').read_bytes())['rows']
    meta = {f['event_id']: f for f in json.loads((ROOT/'artifacts/care-numeric-input-20261016/dataset-manifest.json').read_bytes())['files']}
    results, per_event = score(truth, meta, rows, alarms)
    checks = reproduce_saved(results)
    write_new(out/'metrics.json', results); write_new(out/'per-event.json', per_event)
    summary = {'saved_methods': checks, 'development_material_not_blind_holdout': True, 'no_acceptance_thresholds': True,
               'timesfm3_research_reference_only': True, 'significance_claims': False,
               'asset_macro': {m: results[m]['asset_macro'] for m in results},
               'pooled': {m: {k: results[m]['pooled'][k] for k in ('hits', 'anomaly_events', 'hits_at', 'attainable_at', 'false_episodes',
                                                                    'false_episodes_per_1000_record_hours', 'false_episodes_per_asset_30_days',
                                                                    'normal_alarm_fraction', 'earliness', 'lead1_mae_common_thermal')} for m in results}}
    write_new(out/'summary.json', summary)
    files = [{'name': p.name, 'bytes': p.stat().st_size, 'sha256': digest(p)} for p in sorted(out.iterdir())]
    write_new(out/'root-closed.json', {'status': 'complete', 'files': files})
    print(json.dumps(summary['pooled'], indent=1))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--campaign', required=True)
    main(p.parse_args().campaign)
