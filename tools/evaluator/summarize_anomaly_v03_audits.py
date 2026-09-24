"""Descriptive dev/smoke comparison from externally pinned, completed audits.

Reads small saved audit reports only. Does not run a producer, rescore data,
perform bootstrap inference, select/promote a candidate, or open holdout.
"""
import argparse
from collections import Counter, defaultdict
import datetime
import hashlib
import itertools
import json
import math
from pathlib import Path
import stat
import time

CANDIDATES = ('c0-diff-control', 'c1-phase-level', 'c2-phase-conditional')
STRATA = ('core', 'quality-stress')
TARGETS = tuple(f'{equipment}.{signal}' for equipment in ('motor-01', 'conveyor-01')
                for signal in ('motor_current', 'motor_temperature', 'conveyor_speed', 'vibration_feature'))
SCALES = {'machine_recall': 1, 'sensor_recall': 1, 'precision': 1,
          'clean_rate': 28800, 'false_alert_burden': 100}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('nonfinite JSON number: ' + value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def read_pinned(path, expected, *, maximum=8 * 1024**2):
    """Read bounded input; the expected digest comes from an external savepoint."""
    info = path.lstat()
    need(stat.S_ISREG(info.st_mode) and not path.is_symlink() and
         not getattr(info, 'st_file_attributes', 0) & 0x400, 'not a regular input')
    need(0 <= info.st_size <= maximum and info.st_size == expected['bytes'], 'input size differs')
    with path.open('rb') as stream:
        raw = stream.read(maximum + 1)
    need({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == expected, 'input hash differs: ' + str(path))
    after = path.stat()
    need((info.st_ino, info.st_size, info.st_mtime_ns) == (after.st_ino, after.st_size, after.st_mtime_ns), 'input changed')
    return strict_json(raw)


def ratio(numerator, denominator, scale=1):
    return {'numerator': numerator, 'denominator': denominator,
            'value': scale * numerator / denominator if denominator else None}


def validate_metrics(row):
    """Check accounting invariants without repeating the prior score audit."""
    m = row['metrics']
    for key, scale in SCALES.items():
        metric = m[key]
        n, d = metric['numerator'], metric['denominator']
        need(type(n) is int and n >= 0 and type(d) is int and d >= 0, 'invalid raw counts')
        expected = ratio(n, d, scale)['value']
        need(metric['value'] is None if expected is None else
             type(metric['value']) in (int, float) and math.isclose(metric['value'], expected, rel_tol=1e-12, abs_tol=1e-12), 'metric ratio differs')
    for key, denominator in (('machine_recall', 10), ('sensor_recall', 10),
                              ('clean_rate', 3365), ('false_alert_burden', 20)):
        need(m[key]['denominator'] == denominator, 'planned denominator differs')
    detected = m['machine_recall']['numerator'] + m['sensor_recall']['numerator']
    need(m['machine_recall']['numerator'] <= 10 and m['sensor_recall']['numerator'] <= 10, 'recall overflow')
    need(m['precision']['numerator'] == detected and row['incidents'] == 20, 'detected partition differs')
    need(m['precision']['denominator'] == detected + m['false_alert_burden']['numerator'] == row['equipment_episodes'], 'episode partition differs')
    need(m['clean_rate']['numerator'] <= m['false_alert_burden']['numerator'], 'clean false count exceeds total')
    need(m['scheduled_clean_seconds'] == 3365 and 0 <= m['effective_clean_seconds'] <= 3365, 'clean exposure differs')
    need([r['full_target'] for r in m['availability']] == list(TARGETS), 'target inventory differs')
    for availability in m['availability']:
        metric = availability['metric']
        need(type(metric['numerator']) is int and 0 <= metric['numerator'] <= 1800 and
             metric['denominator'] == 1800 and math.isclose(metric['value'], metric['numerator']/1800, abs_tol=1e-12), 'availability differs')
    delay = m['delay_summary']
    need(delay['count'] == detected and delay['conditioned_on'] == 'causal-detected-only' and
         delay['undetected_fill'] == 'forbidden' and delay['unit'] == 'seconds', 'delay scope differs')
    if detected:
        need(all(type(delay[k]) in (int, float) and math.isfinite(delay[k]) for k in ('mean', 'min', 'max', 'median')) and
             0 <= delay['min'] <= delay['mean'] <= delay['max'], 'invalid detected delay')
    else:
        need(all(delay[k] is None for k in ('mean', 'min', 'max', 'median')), 'undetected delay must be null')


def aggregate(rows):
    """Sum raw counts/exposure; never average precision or per-cell medians."""
    need(bool(rows), 'empty group')
    result = {'evaluations': len(rows), 'seeds': len({r['identity']['seed'] for r in rows})}
    for key, scale in SCALES.items():
        result[key] = ratio(sum(r['metrics'][key]['numerator'] for r in rows),
                            sum(r['metrics'][key]['denominator'] for r in rows), scale)
    result['availability'] = {t: ratio(sum(r['metrics']['availability'][i]['metric']['numerator'] for r in rows), 1800 * len(rows))
                              for i, t in enumerate(TARGETS)}
    result['scheduled_clean_equipment_hours'] = result['clean_rate']['denominator'] / 3600
    result['effective_clean_equipment_hours'] = sum(r['metrics']['effective_clean_seconds'] for r in rows) / 3600
    delays = [r['metrics']['delay_summary'] for r in rows if r['metrics']['delay_summary']['count']]
    count = sum(d['count'] for d in delays)
    result['delay'] = {'detected_count': count,
        'mean_seconds': math.fsum(d['mean'] * d['count'] for d in delays) / count if count else None,
        'min_seconds': min((d['min'] for d in delays), default=None),
        'max_seconds': max((d['max'] for d in delays), default=None),
        'conditioned_on': 'causal-detected-only', 'median': None,
        'median_status': 'not_recoverable_from_per_evaluation_summaries', 'undetected_fill': 'forbidden'}
    return result


def check_inventory(rows, expected_identities):
    observed = [r['identity'] for r in rows]
    need(observed == expected_identities, 'evaluation inventory/order differs')
    need(len({r['evaluation_id'] for r in observed}) == len(observed) == 720, 'duplicate or missing evaluation')
    need(Counter(r['role'] for r in observed) == {'dev': 576, 'smoke': 144}, 'role inventory differs')
    for role, count in (('dev', 8), ('smoke', 2)):
        selected = [r for r in observed if r['role'] == role]
        seeds = {r['seed'] for r in selected}
        need(len(seeds) == count, 'seed count differs')
        actual = {(r['seed'], r['layout'], r['stratum'], r['candidate_id']) for r in selected}
        need(actual == set(itertools.product(seeds, range(12), STRATA, CANDIDATES)), 'paired inventory differs')


def summarize(rows):
    groups, seed_groups, layout_groups = defaultdict(list), defaultdict(list), defaultdict(list)
    for row in rows:
        i = row['identity']
        for role in (i['role'], 'combined'):
            for layer in (i['stratum'], 'overall'):
                groups[(role, layer, i['candidate_id'])].append(row)
                layout_groups[(role, layer, i['candidate_id'], i['layout'])].append(row)
        for layer in (i['stratum'], 'overall'):
            seed_groups[(i['role'], layer, i['candidate_id'], i['seed'])].append(row)
    def records(mapping, fields):
        return [{**dict(zip(fields, key)), **aggregate(value)} for key, value in sorted(mapping.items())]
    grouped = records(groups, ('role', 'stratum', 'candidate_id'))
    paired = []
    for role, layer in itertools.product(('dev', 'smoke', 'combined'), (*STRATA, 'overall')):
        selected = {r['candidate_id']: r for r in grouped if r['role'] == role and r['stratum'] == layer}
        base = selected[CANDIDATES[0]]
        for candidate in CANDIDATES[1:]:
            other = selected[candidate]
            paired.append({'role': role, 'stratum': layer, 'candidate_id': candidate,
                'comparison': 'candidate minus C0; descriptive matched inventory; no CI',
                **{key: other[key]['value'] - base[key]['value'] for key in
                   ('machine_recall', 'sensor_recall', 'clean_rate', 'false_alert_burden')},
                'availability': {t: other['availability'][t]['value'] - base['availability'][t]['value'] for t in TARGETS}})
    return {'groups': grouped, 'by_seed': records(seed_groups, ('role', 'stratum', 'candidate_id', 'seed')),
            'by_layout': records(layout_groups, ('role', 'stratum', 'candidate_id', 'layout')),
            'paired_differences': paired}


def run(savepoint_path, expected_sha256, output):
    started = time.monotonic()
    need(not output.exists(), 'output already exists; use a new path')
    manifest_pin = {'bytes': savepoint_path.stat().st_size, 'sha256': expected_sha256}
    manifest = read_pinned(savepoint_path, manifest_pin)
    need(manifest['status'] == 'completed' and manifest['cumulative_verified_evaluations'] == 720 and
         manifest['next_unverified_chunk'] is None and manifest['formal_permission'] is False, 'savepoint scope differs')
    evidence_path = savepoint_path.parent / 'evidence.json'
    evidence = read_pinned(evidence_path, manifest['evidence'])
    root, pins = Path(evidence['run_root']), evidence['files']
    inputs = {str(savepoint_path): manifest_pin, str(evidence_path): manifest['evidence']}
    def pinned(name):
        p = Path(name)
        need(not p.is_absolute() and '..' not in p.parts and p.as_posix() == name, 'unsafe input path')
        path = root / name
        need(path.resolve().is_relative_to(root.resolve()), 'input escapes root')
        data = read_pinned(path, pins[name])
        inputs[str(path)] = pins[name]
        return data
    plan = pinned('run/metadata/plan.json')
    closed_name = Path(manifest['closed_state']['path']).relative_to(root).as_posix()
    closed = pinned(closed_name)
    need(pins[closed_name]['sha256'] == manifest['closed_state']['sha256'] and closed['status'] == 'completed', 'closed differs')
    need(len(plan['chunks']) == len(evidence['journal_state']['chunks']) == 120, 'chunk count differs')
    rows, retries = [], []
    for index, (planned, chunk) in enumerate(zip(plan['chunks'], evidence['journal_state']['chunks'])):
        need(planned['chunk_index'] == chunk['chunk_index'] == index and chunk['status'] == 'verified_complete', 'unverified chunk')
        attempt = chunk['attempts'][-1]
        need(attempt['status'] == 'verified_complete', 'last attempt incomplete')
        prefix = f"run/attempts/chunks/{index:03d}/attempt-{attempt['attempt']:04d}"
        audit_name = prefix + '/audit/report.json'
        need(pins[audit_name]['sha256'] == chunk['evidence']['audit_sha256'], 'audit binding differs')
        audit = pinned(audit_name)
        binding = audit['input']['binding']
        need(binding['chunk_index'] == index and binding['attempt'] == attempt['attempt'] and
             binding['seed'] == planned['seed'] and binding['role'] == planned['role'] and
             binding['layout'] == planned['layout'], 'audit chunk identity differs')
        need(audit['status'] == 'ledger_checks_passed' and audit['performance_status'] == 'not_evaluated' and
             audit['formal_permission'] is False and audit['independent_s6_complete'] is False, 'audit scope differs')
        need([r['identity'] for r in audit['evaluations']] == planned['identities'], 'audit slot identity differs')
        need([{'evaluation_id': r['identity']['evaluation_id'], 'status': 'success'} for r in audit['evaluations']]
             == chunk['outcome']['slots'], 'checkpoint outcomes differ')
        for row in audit['evaluations']:
            need(row['status'] == 'ledger_checks_passed' and row['score_derivation_verified'] is False and
                 row['score_rows'] == 14400, 'evaluation audit differs')
            validate_metrics(row)
            rows.append({**row, 'chunk_index': index, 'attempt': attempt['attempt'], 'source_audit': audit_name})
        retries.extend({'chunk_index': index, 'attempt': a['attempt'], 'status': a['status'], 'excluded_from_summary': True}
                       for a in chunk['attempts'][:-1])
    check_inventory(rows, [i for chunk in plan['chunks'] for i in chunk['identities']])
    report = {'format': 'anomaly-v03-dev-smoke-descriptive-summary-v1',
        'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'scope': 'descriptive_saved_audit_metrics_dev_smoke_only', 'performance_status': 'not_evaluated',
        'formal_permission': False, 'promotion_allowed': False, 'holdout_read': False,
        'bootstrap_performed': False, 'profile_or_score_derivation_repeated': False,
        'source_savepoint': {'path': str(savepoint_path), **manifest_pin},
        'source_commit': manifest['saved_revision'], 'execution_revision': manifest['execution_revision'],
        'coverage': {'chunks': 120, 'evaluations': 720, 'dev_evaluations': 576, 'smoke_evaluations': 144,
                     'dev_seeds': 8, 'smoke_seeds': 2, 'paired_layouts': 120, 'datasets': 240,
                     'unique_planned_incidents_per_stratum': 2400, 'candidate_count': 3},
        'excluded_attempts': retries, **summarize(rows),
        'inputs_read': len(inputs), 'input_bytes_read': sum(p['bytes'] for p in inputs.values()),
        'elapsed_seconds': time.monotonic() - started,
        'limits': ['synthetic dev/smoke, not independent holdout', 'no confidence intervals or promotion decision',
                   'delay statistics include detected incidents only; pooled median unavailable',
                   'combined strata reuse paired histories; not independent extra seeds',
                   'prior score-ledger audit reused; raw profiles/scores not independently derived here']}
    # All checks complete before producing a fresh directory; immutable inputs stay untouched.
    output.mkdir(parents=True)
    for name, value in (('summary.json', report), ('evaluations.json', rows), ('input-pins.json', inputs)):
        with (output / name).open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write('\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--savepoint', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    value = run(args.savepoint.resolve(), args.sha256, args.output.resolve())
    print(json.dumps({k: value[k] for k in ('coverage', 'inputs_read', 'input_bytes_read', 'elapsed_seconds', 'excluded_attempts')}))
