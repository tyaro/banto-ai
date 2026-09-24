"""Read-only generation audit of one authenticated completed dev/smoke pair.

Shares only metadata/path authentication with the connected score audit. Normal
physics, schedule, overlays and rounding use the separate stdlib-only consumer.
Historical runtime/publication attestations are inherited, not re-executed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

from . import anomaly_v03_generation_audit as generation
from .anomaly_v03_observation_audit import MIB, paths, registry, checkpoints, scores, read_pinned, same


def audit_completed_generation(savepoint, savepoint_sha256, run_root, chunk_index):
    started = time.monotonic()
    scores.need(type(chunk_index) is int and 0 <= chunk_index < 120, 'chunk index outside plan')
    savepoint = paths.regular_path(savepoint)
    run_root = paths.regular_path(run_root, directory=True)
    anchor_pin = {'bytes': savepoint.stat().st_size, 'sha256': savepoint_sha256}
    anchor = scores.strict_json(read_pinned(savepoint, anchor_pin, MIB))
    for key, expected in {'status': 'completed', 'full_120_chunks_completed': True,
            'cumulative_verified_chunks': 120, 'cumulative_verified_evaluations': 720,
            'next_unverified_chunk': None, 'formal_permission': False}.items():
        same(anchor[key], expected, 'completed savepoint required: ' + key)
    same(anchor['evidence'], anchor['artifacts']['evidence.json'], 'evidence pin binding')
    evidence = scores.strict_json(read_pinned(savepoint.parent/'evidence.json', anchor['evidence'], 8*MIB))
    # Compare spelling before any access to the path supplied inside the evidence.
    scores.need(Path(evidence['run_root']) == run_root, 'explicit run root differs from savepoint')
    pins, used = evidence['files'], {}

    def read(relative, maximum):
        registry.safe_relative_path(relative)
        raw = read_pinned(run_root/relative, pins[relative], maximum)
        used[relative] = dict(pins[relative])
        return raw

    plan = scores.strict_json(read('run/metadata/plan.json', MIB))
    valid = checkpoints.validate_plan(plan)
    state = evidence['journal_state']
    same(valid['plan_sha256'], state['plan_sha256'], 'savepoint plan binding')
    same(state['next_unverified_chunk'], None, 'unfinished journal state')
    scores.need(len(state['chunks']) == 120, 'complete chunk inventory required')
    chunk = state['chunks'][chunk_index]
    same(chunk['chunk_index'], chunk_index, 'selected chunk binding')
    scores.need(chunk['status'] in checkpoints.VERIFIED, 'selected chunk is not verified')
    attempts = chunk['attempts']
    scores.need(type(attempts) is list and bool(attempts), 'missing selected attempt')
    selected = attempts[-1]
    same(selected['status'], chunk['status'], 'final attempt is not the verified attempt')
    attempt = selected['attempt']
    scores.need(type(attempt) is int and 1 <= attempt <= checkpoints.MAX_RECORDS, 'attempt number')
    stem = f'run/attempts/chunks/{chunk_index:03d}/attempt-{attempt:04d}'
    same(selected['attempt_root'], stem.removeprefix('run/attempts/'), 'attempt path binding')
    same(selected['context']['source_bindings'], plan['source_bindings'], 'historical source binding')
    same(selected['evidence'], chunk['evidence'], 'attempt evidence binding')
    audit_path = stem+'/audit/report.json'
    same(pins[audit_path]['sha256'], chunk['evidence']['audit_sha256'], 'historical audit pin binding')
    old_audit = scores.strict_json(read(audit_path, 4*MIB))
    planned = plan['chunks'][chunk_index]
    same(old_audit['input']['binding'], {'campaign_plan_sha256': valid['plan_sha256'],
        'chunk_index': chunk_index, 'attempt': attempt, 'role': planned['role'],
        'seed': planned['seed'], 'layout': planned['layout'],
        'identities_sha256': planned['identities_sha256']}, 'historical audit selection')
    same(old_audit['status'], 'ledger_checks_passed', 'historical audit unsuccessful')
    outcome = chunk['outcome']
    same(outcome['worker_exit_confirmed'], True, 'historical worker exit missing')
    slots = outcome['slots']
    scores.need(type(slots) is list and len(slots) == 6, 'six saved slot outcomes required')
    expected_status = 'verified_inconclusive' if any(s['status'] == 'inconclusive' for s in slots) else 'verified_complete'
    same(chunk['status'], expected_status, 'inconclusive chunk outcome hidden')
    captures, digests = {}, {}
    for identity, slot in zip(planned['identities'], slots):
        registry.validate_identity(identity)
        same(slot['evaluation_id'], identity['evaluation_id'], 'saved slot identity/order')
        scores.need(slot['status'] in ('success', 'inconclusive'), 'saved slot outcome')
        stratum = identity['stratum']
        if stratum in captures:
            continue
        directory = stem+'/result/payload/datasets/'+identity['dataset_id']+'/'
        captures[stratum], digests[stratum] = {}, {}
        for name in generation.FILES:
            relative = directory + name
            captures[stratum][name] = read(relative, 16*MIB)
            digests[stratum][name] = pins[relative]['sha256']
    result = generation.audit_generation_pair(planned['role'], planned['seed'], planned['layout'],
                                               captures, expected_sha256=digests)
    return {'format': 'anomaly-v03-saved-generation-audit-v1', 'status': 'selected_pair_checks_passed',
        'scope': 'selected-completed-dev-smoke-pair', 'chunk_index': chunk_index, 'attempt': attempt,
        'prior_attempts_not_credited': len(attempts)-1, 'generation_audit': result,
        'trust_anchor': {'path': str(savepoint), **anchor_pin}, 'evidence_pin': anchor['evidence'],
        'run_root': str(run_root), 'input_pins': used, 'input_bytes': sum(p['bytes'] for p in used.values()),
        'elapsed_seconds': time.monotonic()-started, 'new_producer_evaluations': 0,
        'campaign_evaluations_credited': 0, 'independent_s6_complete': False, 'formal_permission': False,
        'promotion_allowed': False, 'performance_status': 'not_evaluated',
        'not_rechecked': ['other chunks', 'historical publication/source/runtime/supervision',
                         'profile/score/ledger derivations', 'bootstrap/CI', 'formal gates'],
        'limits': ['externally trusted completed savepoint required',
                   'not protection against hostile concurrent filesystem mutation',
                   'complete registered dev/smoke pairs only',
                   'Random/gauss/binary64/round/JSON are shared specified runtime primitives']}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Read-only normal/overlay/rounding audit of one saved dev/smoke pair')
    parser.add_argument('--savepoint', type=Path, required=True)
    parser.add_argument('--savepoint-sha256', required=True)
    parser.add_argument('--run-root', type=Path, required=True)
    parser.add_argument('--chunk-index', type=int, required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(audit_completed_generation(args.savepoint, args.savepoint_sha256,
                         args.run_root, args.chunk_index), ensure_ascii=False, sort_keys=True, allow_nan=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        print(json.dumps({'status': 'audit_failed', 'error_type': type(error).__name__,
                          'message': str(error)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
