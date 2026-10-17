"""Authenticate retained dev/smoke audit reports and aggregate their raw counts.

Only small audit reports and the fixed plan are read. Payload integrity is the
historical, pinned audit's assertion, not a new check of today's payload bytes.
No observations, scores, bootstrap draws, confidence intervals or gates are run.
The public aggregation function alone does not authenticate its caller's rows.
"""
from __future__ import annotations

import math
from pathlib import Path

from . import anomaly_v03_inference_audit as arithmetic
from .anomaly_v03_observation_audit import (
    DATASET_INPUTS, MIB, checkpoints, paths, read_pinned, registry, same, scores,
)

QUIET = {'formal_permission': False, 'promotion_allowed': False,
         'independent_s6_complete': False, 'performance_status': 'not_evaluated'}
GENERATION_FILES = ('observations.jsonl', 'events.jsonl', 'event-ledger.jsonl', 'quality-mask.jsonl')


def fields(value, expected, context):
    for key, wanted in expected.items():
        same(value[key], wanted, context + ': ' + key)


def point_matches(actual, expected):
    if expected is None:
        same(actual, None, 'zero denominator point')
    else:
        arithmetic.finite(actual)
        scores.need(math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), 'reported point differs')


def metric_counts(metric, kind):
    pair = arithmetic.counts([metric['numerator'], metric['denominator']], kind)
    fields(metric, {'ci_status': 'not_evaluated' if pair[1] else 'inconclusive', 'ci_lower': None, 'ci_upper': None,
                    'null_replicates': 0}, 'saved CI must be unevaluated')
    point_matches(metric['value'], arithmetic.ratio(*pair, kind))
    return list(pair)


def evaluation_counts(row, identity):
    same(row['identity'], identity, 'evaluation identity/order/coverage')
    profile, ledger = row['profile_and_score_audit'], row['ledger_audit']
    fields(profile, {**QUIET, 'identity': identity, 'status': 'observation_profile_score_checks_passed',
        'profile_derivation_verified': True, 'score_derivation_verified': True,
        'profiles_checked': 48, 'observation_rows': 18000, 'score_rows_checked': 14400}, 'profile audit')
    inconclusive = profile['inconclusive_profiles']
    scores.need(type(inconclusive) is list and len(inconclusive) <= 48, 'inconclusive profile list')
    seen = set()
    profile_ids = {identity['evaluation_id'] + f'-profile-{equipment}-{target}-{mode}'
                   for equipment in ('motor-01', 'conveyor-01') for target in scores.TARGETS for mode in scores.MODES}
    for item in inconclusive:
        scores.need(type(item) is dict and set(item) == {'profile_id', 'reason'}, 'profile diagnostic fields')
        name = item['profile_id']
        scores.need(type(name) is str and name in profile_ids and name not in seen, 'profile diagnostic identity/duplicate')
        scores.need(item['reason'] in ('zero_scale', 'nonfinite', 'cholesky_failure', 'insufficient_points'), 'profile diagnostic reason')
        seen.add(name)
    outcome = 'inconclusive' if inconclusive else 'success'
    same(row['evaluation_outcome'], outcome, 'evaluation outcome/profile state')
    same(profile['evaluation_outcome'], outcome, 'profile outcome')
    fields(ledger, {'status': 'ledger_checks_passed', 'score_rows': 14400, 'incidents': 20,
                   'independent_s6_complete': False, 'performance_status': 'not_evaluated'}, 'ledger audit')
    metrics = ledger['metrics']
    result = {kind: metric_counts(metrics[kind], kind) for kind in arithmetic.METRICS[:5]}
    same([v['full_target'] for v in metrics['availability']], list(arithmetic.TARGETS), 'eight ordered targets')
    for item, kind in zip(metrics['availability'], arithmetic.AVAILABILITY):
        result[kind] = metric_counts(item['metric'], kind)
    for kind, expected in {'machine_recall': 10, 'sensor_recall': 10, 'clean_rate': 3365,
                          'false_alert_burden': 20, **dict.fromkeys(arithmetic.AVAILABILITY, 1800)}.items():
        same(result[kind][1], expected, 'planned denominator: ' + kind)
    detected = result['machine_recall'][0] + result['sensor_recall'][0]
    same(result['precision'][0], detected, 'detected incident partition')
    same(result['precision'][1], ledger['equipment_episodes'], 'precision episode denominator')
    same(result['precision'][1], detected + result['false_alert_burden'][0], 'false episode partition')
    scores.need(result['clean_rate'][0] <= result['false_alert_burden'][0], 'clean alerts subset')
    same(sum(result[k][0] for k in arithmetic.AVAILABILITY), profile['available_score_rows'], 'available rows')
    same(metrics['scheduled_clean_seconds'], 3365, 'scheduled clean exposure')
    effective = metrics['effective_clean_seconds']
    scores.need(type(effective) is int and 0 <= effective <= 3365, 'effective clean exposure')
    point_matches(metrics['effective_clean_rate'], arithmetic.ratio(result['clean_rate'][0], effective, 'clean_rate'))
    return {'identity': identity, 'counts': result, 'effective_clean_seconds': effective,
            'inconclusive_profiles': inconclusive, 'evaluation_outcome': outcome}


def table(rows, **identity):
    counts = {kind: [sum(r['counts'][kind][i] for r in rows) for i in (0, 1)] for kind in arithmetic.METRICS}
    diagnostics = [{'evaluation_id': r['identity']['evaluation_id'], 'profiles': r['inconclusive_profiles']}
                   for r in rows if r['inconclusive_profiles']]
    undefined = [{'evaluation_id': r['identity']['evaluation_id'],
                  'metrics': [k for k, pair in r['counts'].items() if pair[1] == 0]}
                 for r in rows if any(pair[1] == 0 for pair in r['counts'].values())]
    return {**identity, 'evaluations': len(rows), 'counts': counts,
        'points': {kind: arithmetic.ratio(*pair, kind) for kind, pair in counts.items()},
        'scheduled_clean_seconds': counts['clean_rate'][1],
        'effective_clean_seconds': sum(r['effective_clean_seconds'] for r in rows),
        'profile_status': 'inconclusive' if diagnostics else 'success', 'profile_diagnostics': diagnostics,
        'undefined_input_points': undefined,
        'ci_status': 'not_evaluated', 'ci_lower': None, 'ci_upper': None}


def aggregate_evaluations(evaluations):
    """Validate all 720 ordered rows; aggregate counts before dividing.

    Registration is metadata only. No holdout observation or inference is used.
    Inconclusive rows remain present with their full counts and diagnostics.
    """
    expected = registry.evaluation_inventory('dev') + registry.evaluation_inventory('smoke')
    scores.need(type(evaluations) is list and len(evaluations) == len(expected) == 720, '720 evaluations required')
    rows = [evaluation_counts(row, identity) for row, identity in zip(evaluations, expected)]
    clusters, by_seed, by_role, paired = [], [], [], []
    for entry in registry.seed_registry()['entries'][:2]:
        role, seeds = entry['role'], entry['seeds']
        for index, seed in enumerate(seeds):
            selected = [r for r in rows if r['identity']['role'] == role and r['identity']['seed'] == seed]
            cluster = {'role': role, 'seed': seed, 'registered_index': index, 'layouts': list(range(12)),
                       'evaluation_ids': [r['identity']['evaluation_id'] for r in selected], 'candidates': {}}
            for candidate in arithmetic.CANDIDATES:
                cluster['candidates'][candidate] = {}
                for layer in arithmetic.STRATA:
                    subset = [r for r in selected if r['identity']['candidate_id'] == candidate and
                              (layer == 'overall' or r['identity']['stratum'] == layer)]
                    item = table(subset, role=role, seed=seed, candidate_id=candidate, stratum=layer)
                    by_seed.append(item)
                    if layer != 'overall':
                        cluster['candidates'][candidate][layer] = {
                            'counts': item['counts'],
                            'profile_status': 'calibrated' if item['profile_status'] == 'success' else 'inconclusive'}
            clusters.append(cluster)
        for layer in arithmetic.STRATA:
            tables = {}
            for candidate in arithmetic.CANDIDATES:
                subset = [r for r in rows if r['identity']['role'] == role and
                          r['identity']['candidate_id'] == candidate and
                          (layer == 'overall' or r['identity']['stratum'] == layer)]
                item = table(subset, role=role, seeds=len(seeds), candidate_id=candidate, stratum=layer)
                by_role.append(item)
                tables[candidate] = item
            control = tables[arithmetic.CANDIDATES[0]]
            for candidate in arithmetic.CANDIDATES[1:]:
                current = tables[candidate]
                paired.append({'role': role, 'stratum': layer, 'candidate_id': candidate,
                    'comparison': 'candidate-minus-c0-descriptive-only',
                    'profile_status': 'success' if current['profile_status'] == control['profile_status'] == 'success' else 'inconclusive',
                    'points': {kind: None if current['points'][kind] is None or control['points'][kind] is None
                               else current['points'][kind] - control['points'][kind] for kind in arithmetic.PAIRED_METRICS},
                    'ci_status': 'not_evaluated', 'ci_lower': None, 'ci_upper': None})
    return {**QUIET, 'format': 'anomaly-v03-dev-smoke-seed-counts-v1',
        'status': 'complete_dev_smoke_counts', 'evaluations': 720, 'seed_clusters': clusters,
        'zero_denominator_input_metrics': sum(pair[1] == 0 for r in rows for pair in r['counts'].values()),
        'by_seed': by_seed, 'by_role': by_role, 'paired_descriptive': paired,
        'selected_candidate': None, 'bootstrap_performed': False, 'real_performance_intervals_computed': 0,
        'limits': ['dev8 and smoke2 kept separate; no combined inferential population',
                   'profile inconclusive counts retained as diagnostics, not certification',
                   'delay/slices/runtime and formal analysis schema not assessed']}


def authenticate_seed_counts(savepoints, root_sha256, run_root):
    """Read only explicit roots plus fixed report names, anchored by external SHA.

    savepoints maps inference/generation/score/connected/completed to their JSON
    manifests. These are retained audit reports, not a live payload attestation.
    """
    same(sorted(savepoints), sorted(('inference', 'generation', 'score', 'connected', 'completed')), 'savepoint roots')
    roots = {key: paths.regular_path(value) for key, value in savepoints.items()}
    run_root = paths.regular_path(run_root, directory=True)
    used = {}

    def read(path, pin, maximum=MIB):
        raw = read_pinned(path, pin, maximum)
        used[str(path)] = dict(pin)
        return scores.strict_json(raw)

    root_pin = {'bytes': roots['inference'].stat().st_size, 'sha256': root_sha256}
    inference = read(roots['inference'], root_pin)
    fields(inference, {**QUIET, 'status': 'inference_math_checks_completed'}, 'inference manifest')
    source = Path(arithmetic.__file__)
    read_pinned(source, inference['code_pins']['src/banto_ai/anomaly_v03_inference_audit.py'], MIB)
    freeze = source.parents[2]/'examples/configs/anomaly-v03-freeze-registry.json'
    frozen = read(freeze, inference['code_pins']['examples/configs/anomaly-v03-freeze-registry.json'])
    same(frozen['seed_registry'], registry.seed_registry(), 'frozen seed registration')
    generation = read(roots['generation'], inference['prior_generation_manifest'])
    fields(generation, {**QUIET, 'status': 'full_saved_generation_audit_completed', 'pairs_verified': 120,
        'datasets_verified': 240, 'linked_profile_score_ledger_evaluations': 720,
        'normal_generation_verified': True, 'pre_rounding_overlay_verified': True, 'rounding_verified': True,
        'successful_result_directory': 'verified'}, 'generation manifest')
    score = read(roots['score'], generation['previous_score_audit_savepoint'])
    fields(score, {**QUIET, 'status': 'full_saved_numeric_ledger_audit_completed', 'chunks_verified': 120,
                  'evaluations_verified': 720, 'full_720_profile_score_audit_completed': True}, 'score manifest')
    same(score['prior_connected_savepoint'], generation['connected_savepoint'], 'connected manifest binding')
    same(score['completed_campaign_savepoint'], generation['completed_campaign_savepoint'], 'campaign manifest binding')
    connected = read(roots['connected'], generation['connected_savepoint'])
    fields(connected, {**QUIET, 'status': 'bounded_connected_audit_completed'}, 'connected manifest')
    completed_pin = generation['completed_campaign_savepoint']
    completed = read(roots['completed'], completed_pin)
    fields(completed, {'status': 'completed', 'full_120_chunks_completed': True,
        'cumulative_verified_chunks': 120, 'cumulative_verified_evaluations': 720,
        'next_unverified_chunk': None, 'formal_permission': False}, 'completed campaign')
    same(completed['evidence'], completed['artifacts']['evidence.json'], 'evidence binding')
    evidence = read(roots['completed'].parent/'evidence.json', completed['evidence'], 8*MIB)
    scores.need(Path(evidence['run_root']) == run_root, 'explicit run root binding')
    pins, state = evidence['files'], evidence['journal_state']
    plan = read(run_root/'run/metadata/plan.json', pins['run/metadata/plan.json'])
    same(checkpoints.validate_plan(plan)['plan_sha256'], state['plan_sha256'], 'fixed plan binding')
    same(state['next_unverified_chunk'], None, 'unfinished campaign')
    scores.need(len(state['chunks']) == len(plan['chunks']) == 120, '120 chunk inventory')
    rows, attempts_used = [], []
    for index, (chunk, planned) in enumerate(zip(state['chunks'], plan['chunks'])):
        same(chunk['chunk_index'], index, 'chunk order')
        scores.need(chunk['status'] in checkpoints.VERIFIED, 'unverified chunk')
        selected = chunk['attempts'][-1]
        attempt = selected['attempt']
        scores.need(type(attempt) is int and 1 <= attempt <= checkpoints.MAX_RECORDS, 'attempt number')
        stem = f'run/attempts/chunks/{index:03d}/attempt-{attempt:04d}'
        fields(selected, {'status': chunk['status'], 'attempt_root': stem.removeprefix('run/attempts/'),
                          'evidence': chunk['evidence']}, 'final verified attempt')
        same(selected['context']['source_bindings'], plan['source_bindings'], 'historical source binding')
        audit_path = stem+'/audit/report.json'
        same(pins[audit_path]['sha256'], chunk['evidence']['audit_sha256'], 'historical audit digest')
        gen_name = f'verified/chunk-{index:03d}.json'
        gen = read(roots['generation'].parent/gen_name, generation['artifacts'][gen_name])
        old_root, old_manifest = (roots['connected'], connected) if index == 0 else (roots['score'], score)
        old_name = 'verified-final/chunk-000.json' if index == 0 else f'chunk-{index:03d}.json'
        old = read(old_root.parent/old_name, old_manifest['artifacts'][old_name])
        for report, status in ((gen, 'selected_pair_checks_passed'), (old, 'selected_chunk_checks_passed')):
            fields(report, {**QUIET, 'status': status, 'chunk_index': index, 'attempt': attempt,
                'evidence_pin': completed['evidence'], 'prior_attempts_not_credited': len(chunk['attempts'])-1}, 'report binding')
            scores.need(Path(report['trust_anchor']['path']) == roots['completed'], 'report anchor path')
            fields(report['trust_anchor'], completed_pin, 'report anchor pin')
            scores.need(Path(report['run_root']) == run_root, 'report run root')
        fields(old, {'profile_derivation_verified': True, 'score_derivation_verified': True,
                     'ledger_derivation_verified': True, 'evaluations_checked': 6}, 'score derivation flags')
        g = gen['generation_audit']
        fields(g, {**QUIET, 'status': 'generation_checks_passed', 'role': planned['role'], 'seed': planned['seed'],
            'layout': planned['layout'], 'pair_id': planned['identities'][0]['pair_id'], 'datasets_checked': 2,
            'normal_generation_verified': True, 'pre_rounding_overlay_verified': True, 'rounding_verified': True}, 'generation report')
        expected_gen = {'run/metadata/plan.json', audit_path}
        expected_score = set(expected_gen)
        for identity in planned['identities']:
            directory = stem+'/result/payload/datasets/'+identity['dataset_id']+'/'
            for name in GENERATION_FILES:
                relative = directory+name
                expected_gen.add(relative)
                same(g['input_sha256'][identity['stratum']][name], pins[relative]['sha256'], 'generation input hash')
            expected_score.update(directory+name for name in DATASET_INPUTS.values())
            expected_score.add(stem+'/result/payload/evaluations/'+identity['evaluation_id']+'.json')
        for report, expected_inputs in ((gen, expected_gen), (old, expected_score)):
            same(sorted(report['input_pins']), sorted(expected_inputs), 'report input inventory')
            for name in expected_inputs:
                same(report['input_pins'][name], pins[name], 'report input pin: '+name)
        outcome = chunk['outcome']
        same(outcome['worker_exit_confirmed'], True, 'historical worker exit')
        scores.need(len(outcome['slots']) == len(old['evaluations']) == 6, 'six slot reports')
        for row, identity, slot in zip(old['evaluations'], planned['identities'], outcome['slots']):
            same(row['identity'], identity, 'report identity order')
            same(slot['evaluation_id'], identity['evaluation_id'], 'slot identity')
            scores.need(slot['status'] in ('success', 'inconclusive'), 'slot status')
            same(row['evaluation_outcome'], slot['status'], 'saved outcome binding')
            rows.append(row)
        same(chunk['status'], 'verified_inconclusive' if any(s['status'] == 'inconclusive' for s in outcome['slots'])
             else 'verified_complete', 'chunk outcome binding')
        attempts_used.append({'chunk_index': index, 'attempt': attempt,
                              'prior_attempts_not_credited': len(chunk['attempts'])-1})
    result = aggregate_evaluations(rows)
    result.update({'status': 'authenticated_dev_smoke_counts', 'trust_anchor': {**root_pin, 'path': str(roots['inference'])},
        'authenticated_files': used, 'arithmetic_source_pin': inference['code_pins']['src/banto_ai/anomaly_v03_inference_audit.py'],
        'attempts_used': attempts_used, 'payloads_rehashed': False, 'observations_generated': 0,
        'new_producer_evaluations': 0, 'profile_score_recalculations': 0, 'campaign_evaluations_credited': 0})
    return result
