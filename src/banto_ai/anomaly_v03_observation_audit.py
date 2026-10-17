"""Read-only, selected-chunk numeric/ledger audit anchored to retained bytes.

The external SHA256 is the trust anchor, not a signature. Historical publication,
source/runtime and campaign coverage checks are inherited from that savepoint;
only selected input bytes and numeric/ledger derivations are checked here anew.
No producer, controller, journal writer, generator or formal gate is invoked.
The separate partial-fixture entry has no completed-campaign inheritance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

from . import _anomaly_v03_runtime as paths
from . import anomaly_v03 as registry
from . import anomaly_v03_checkpoints as checkpoints
from . import anomaly_v03_ledger_audit as ledger
from . import anomaly_v03_score_audit as scores

MIB = 1024**2
DATASET_INPUTS = {'observations': 'observations.jsonl', 'events': 'event-ledger.jsonl',
    'origins': 'origins.json', 'quality_mask': 'quality-mask.jsonl',
    'split': 'split-manifest.json', 'targets': 'targets.json'}
PARTIAL_FIXTURE_FORMAT = 'anomaly-v03-preformal-one-chunk-fixture-anchor-v1'


def same(actual, expected, reason):
    scores.need(registry.canonical_json(actual) == registry.canonical_json(expected), reason)


def read_pinned(path, pin, maximum):
    """Bound allocation before reading; authenticate the actual in-memory bytes."""
    scores.need(type(pin) is dict and set(pin) == {'bytes', 'sha256'}, 'file pin fields')
    size, digest = pin['bytes'], pin['sha256']
    scores.need(type(size) is int and 0 <= size <= maximum, 'file size limit')
    scores.need(type(digest) is str and re.fullmatch('[0-9a-f]{64}', digest), 'file SHA256')
    path = paths.regular_path(path)
    before = path.stat()
    scores.need(before.st_size == size, 'pinned file size changed')
    with path.open('rb') as stream:
        opened = os.fstat(stream.fileno())
        scores.need((opened.st_dev, opened.st_ino, opened.st_size) ==
                    (before.st_dev, before.st_ino, size), 'file changed before read')
        raw = stream.read(size + 1)
    after = paths.regular_path(path).stat()
    scores.need((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), 'file changed during read')
    scores.need(len(raw) == size and hashlib.sha256(raw).hexdigest() == digest, 'pinned file hash changed')
    return raw


def _audit_selected_chunk(savepoint, savepoint_sha256, run_root, chunk_index, *,
                          include_summaries=False, partial_fixture=False):
    scores.need(type(include_summaries) is bool, 'summary option must be boolean')
    started = time.monotonic()
    scores.need(type(chunk_index) is int and 0 <= chunk_index < 120, 'chunk index outside plan')
    if partial_fixture:
        scores.need(chunk_index == 0, 'partial fixture supports chunk 0 only')
    savepoint = paths.regular_path(savepoint)
    run_root = paths.regular_path(run_root, directory=True)
    anchor_pin = {'bytes': savepoint.stat().st_size, 'sha256': savepoint_sha256}
    anchor = scores.strict_json(read_pinned(savepoint, anchor_pin, MIB))
    if partial_fixture:
        scores.need(type(anchor) is dict and set(anchor) == {
            'format', 'status', 'completed_chunk_index', 'next_unverified_chunk',
            'formal_permission', 'registered_data_read', 'evidence', 'artifacts'},
            'partial fixture anchor fields')
        for key, expected in {'format': PARTIAL_FIXTURE_FORMAT, 'status': 'partial_fixture',
                'completed_chunk_index': 0, 'next_unverified_chunk': 1,
                'formal_permission': False, 'registered_data_read': False}.items():
            same(anchor[key], expected, 'partial fixture anchor: ' + key)
        same(anchor['artifacts'], {'evidence.json': anchor['evidence']},
             'partial fixture evidence pin binding')
    else:
        for key, expected in {'status': 'completed', 'full_120_chunks_completed': True,
                'cumulative_verified_chunks': 120, 'cumulative_verified_evaluations': 720,
                'next_unverified_chunk': None, 'formal_permission': False}.items():
            same(anchor[key], expected, 'completed savepoint required: ' + key)
        same(anchor['evidence'], anchor['artifacts']['evidence.json'], 'evidence pin binding')
    evidence = scores.strict_json(read_pinned(savepoint.parent/'evidence.json', anchor['evidence'], 8*MIB))
    # Compare spelling before any access to the path supplied inside the evidence.
    scores.need(Path(evidence['run_root']) == run_root, 'explicit run root differs from savepoint')
    if partial_fixture:
        same(evidence['fixture_scope'], 'caller-declared-invented-one-chunk',
             'partial fixture evidence scope')
        same(evidence['registered_data_read'], False, 'partial fixture registered data flag')
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
    if partial_fixture:
        same(state['next_unverified_chunk'], 1, 'partial fixture next chunk')
        scores.need(type(state['chunks']) is list and len(state['chunks']) == 1,
                    'one partial fixture chunk required')
    else:
        same(state['next_unverified_chunk'], None, 'unfinished journal state')
        scores.need(type(state['chunks']) is list and len(state['chunks']) == 120 and
                    all(type(item) is dict and item.get('chunk_index') == index and
                        item.get('status') in checkpoints.VERIFIED
                        for index, item in enumerate(state['chunks'])),
                    'complete chunk inventory required')
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
    reports, summaries, dataset, observations, input_hashes = [], [], None, None, None
    event_bytes = None
    for identity, slot in zip(planned['identities'], slots):
        registry.validate_identity(identity)
        same(slot['evaluation_id'], identity['evaluation_id'], 'saved slot identity/order')
        scores.need(slot['status'] in ('success', 'inconclusive'), 'saved slot outcome')
        if dataset != identity['dataset_id']:
            dataset = identity['dataset_id']
            directory = stem+'/result/payload/datasets/'+dataset+'/'
            observations, input_hashes = None, {}
            for key, name in DATASET_INPUTS.items():
                raw = read(directory+name, 16*MIB)
                input_hashes[key] = hashlib.sha256(raw).hexdigest()
                if key == 'observations':
                    observations = raw
                if include_summaries and key == 'events':
                    event_bytes = raw
                del raw
        relative = stem+'/result/payload/evaluations/'+identity['evaluation_id']+'.json'
        result = scores.strict_json(read(relative, 32*MIB))
        same(result['identity'], identity, 'evaluation identity changed')
        same(result['input_hashes'], input_hashes, 'evaluation dataset hash binding')
        same(result['events'], registry.event_inventory(identity), 'registered event inventory changed')
        if include_summaries:
            scores.need(event_bytes == b''.join(registry.canonical_json(e)+b'\n' for e in result['events']),
                        'saved full event ledger differs from evaluation events')
        numeric = scores.audit_score_derivation(result, observations,
            expected_observation_sha256=input_hashes['observations'])
        same(numeric['evaluation_outcome'], slot['status'], 'numeric outcome differs from saved outcome')
        ledgers = ledger.audit_evaluation(result)
        row = {'identity': identity, 'evaluation_outcome': numeric['evaluation_outcome'],
            'profile_and_score_audit': numeric, 'ledger_audit': ledgers}
        reports.append(row)
        if include_summaries:
            from .anomaly_v03_saved_chunk_summary import _summarize
            summaries.append(_summarize(result, row, evaluation_pin=pins[relative]))
        del result
    report = {'format': 'anomaly-v03-connected-observation-audit-v1',
        'scope': ('selected-invented-partial-fixture-chunk' if partial_fixture else
                  'selected-completed-dev-smoke-chunk'), 'status': 'selected_chunk_checks_passed',
        'chunk_index': chunk_index, 'attempt': attempt, 'evaluations_checked': len(reports),
        'prior_attempts_not_credited': len(attempts)-1, 'evaluations': reports,
        'trust_anchor': {'path': str(savepoint), **anchor_pin}, 'evidence_pin': anchor['evidence'],
        'run_root': str(run_root), 'input_pins': used, 'input_bytes': sum(p['bytes'] for p in used.values()),
        'profile_derivation_verified': True, 'score_derivation_verified': True, 'ledger_derivation_verified': True,
        'elapsed_seconds': time.monotonic()-started, 'campaign_evaluations_credited': 0,
        'independent_s6_complete': False, 'formal_permission': False, 'promotion_allowed': False,
        'performance_status': 'not_evaluated', 'shared_metadata_checks': ['fixed plan', 'registered identities/events', 'regular paths'],
        'not_rechecked': ['other chunks', 'historical publication/source/runtime/supervision',
                         'normal generation', 'pre-rounding overlay', 'bootstrap/CI', 'formal gates'],
        'limits': ['externally trusted completed savepoint required', 'not protection against hostile concurrent filesystem mutation',
                   'complete dev/smoke captures with healthy normal prefix only']}
    if partial_fixture:
        report.update(fixture_partial=True, registered_data_read=False,
            execution_authenticated=False, result_trusted=False,
            source_closure_complete=False, runtime_closure_complete=False,
            other_chunks_authenticated=False,
            not_rechecked=['other 119 chunks absent', 'historical publication/source/runtime/supervision',
                           'normal generation', 'pre-rounding overlay', 'bootstrap/CI', 'formal gates'],
            limits=['external digest authenticates saved bytes, not invented data origin',
                    'only chunk 0 is represented; no completed campaign coverage',
                    'not protection against hostile concurrent filesystem mutation',
                    'healthy normal prefix required for score derivation'])
    if include_summaries:
        report['evaluation_summaries'] = summaries
    return report


def audit_completed_chunk(savepoint, savepoint_sha256, run_root, chunk_index, *, include_summaries=False):
    """Audit six evaluations from one completed campaign's final verified attempt.

    Paths come only from the explicit roots and fixed registered identifiers.
    Reads at most one evaluation plus one dataset's observations at a time.
    Returns a report; never writes to the run or the old savepoint.
    """
    return _audit_selected_chunk(savepoint, savepoint_sha256, run_root, chunk_index,
                                 include_summaries=include_summaries)


def audit_partial_fixture_chunk(savepoint, savepoint_sha256, run_root, chunk_index, *,
                                include_summaries=False):
    """Audit one caller-declared invented chunk without completed-campaign claims."""
    return _audit_selected_chunk(savepoint, savepoint_sha256, run_root, chunk_index,
                                 include_summaries=include_summaries, partial_fixture=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Read-only profile, score and ledger audit of one saved dev/smoke chunk')
    parser.add_argument('--savepoint', type=Path, required=True)
    parser.add_argument('--savepoint-sha256', required=True)
    parser.add_argument('--run-root', type=Path, required=True)
    parser.add_argument('--chunk-index', type=int, required=True)
    args = parser.parse_args(argv)
    try:
        report = audit_completed_chunk(args.savepoint, args.savepoint_sha256, args.run_root, args.chunk_index)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, allow_nan=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        print(json.dumps({'status': 'audit_failed', 'error_type': type(error).__name__, 'message': str(error)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
