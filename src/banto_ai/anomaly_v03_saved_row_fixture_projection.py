"""Derive the existing four analysis-worker inputs from invented saved rows.

The ten raw control files per chunk are caller supplied and externally pinned.
This pure boundary rederives all forty contributions from those rows; it does
not reopen observation payloads, authenticate a producer campaign, or authorize
formal analysis. The existing fixture worker's eight-draw limit is retained.
"""
from __future__ import annotations

import copy

from . import anomaly_v03 as v
from . import anomaly_v03_consumer_evidence as evidence
from . import anomaly_v03_fixture_worker as analysis
from . import anomaly_v03_preformal_saved_row_coverage as coverage
from . import anomaly_v03_preformal_saved_seed_contribution as seed


FORMAT = 'anomaly-v03-saved-row-fixture-projection-v1'
CLOSED = {
    'invented_only': True,
    'registered_observations_read': False,
    'actual_registered_observations_read': False,
    'saved_payload_bytes_reopened_here': False,
    'reader_execution_authenticated_here': False,
    'historical_producer_execution_authenticated': False,
    'campaign_coherence_authenticated': False,
    'source_closure_complete': False,
    'runtime_closure_complete': False,
    'full_end_to_end_budget_measured': False,
    'campaign_evaluations_credited': 0,
    'formal_permission': False,
    'analysis_authorized': False,
    'promotion_allowed': False,
    'independent_s6_complete': False,
}
CONTROL_NAMES = ('result', 'rows', 'manifest', 'receipt', 'report', 'savepoint')
MAX_BINDING_BYTES = 8 * 1024**2


def _distinct_sources(entries, chunks):
    """Do not credit a repeated control record or aliased attempt root twice."""
    roots = set()
    seen = {name: set() for name in CONTROL_NAMES}
    for entry, chunk in zip(entries, chunks):
        root = evidence._absolute(chunk['source_root'])
        v.require(root not in roots, 'unique saved-row source roots')
        roots.add(root)
        for name in CONTROL_NAMES:
            digest = entry['expected_pins'][name]['sha256']
            v.require(digest not in seen[name],
                      'unique saved-row ' + name + ' control pin')
            seen[name].add(digest)


def _pack_inputs(clusters, diagnostics, slice_clusters, coverage_clusters, *,
                 expected_revision, draws):
    """Canonical consumer files shared by explicitly scoped row boundaries."""
    fixture = {
        'format': analysis.wrapper.document.FORMAT, 'invented_only': True,
        'clusters': clusters, 'diagnostics': diagnostics,
        'draws': copy.deepcopy(draws), 'engineering_ready_assumption': False,
    }
    analysis.wrapper.document._input(fixture)
    analysis.wrapper.document.I._fixture_clusters(clusters)
    analysis.wrapper.document.adapter._diagnostics(clusters, diagnostics)
    wrapper_coverage = {
        'format': analysis.wrapper.COVERAGE_FORMAT, 'invented_only': True,
        'layout_ids': list(range(seed.LAYOUTS)), 'clusters': coverage_clusters,
    }
    outcomes = analysis.wrapper._coverage(wrapper_coverage, fixture)
    v.require(outcomes['complete'], 'saved-row worker coverage must be complete')
    values = {
        'fixture/input.json': fixture,
        'fixture/slices.json': {
            'format': analysis.wrapper.slices.INPUT_FORMAT,
            'invented_only': True, 'clusters': slice_clusters,
        },
        'fixture/coverage.json': wrapper_coverage,
        'fixture/operation.json': analysis.wrapper.operation_descriptor(expected_revision),
    }
    files = {name: v.canonical_json(value) for name, value in values.items()}
    v.require(all(0 < len(raw) <= analysis.INPUT_LIMITS[name]
                  for name, raw in files.items()) and
              sum(map(len, files.values())) <= analysis.TOTAL_INPUT_LIMIT,
              'saved-row projected worker input limits')
    return files, outcomes


def prepare_inputs(entries, *, expected_mode, expected_revision, draws):
    """Return canonical worker files and a closed, pin-bearing derivation record.

    Exactly 480 ordered invented chunks are needed. Partial, failed, stale,
    duplicated, or differently anchored inputs produce no analysis packet.
    Neither the caller's revision nor a matching historical declaration is an
    attestation of the executed source. No files or processes are accessed.
    """
    v.require(type(expected_mode) is str and expected_mode == 'fixture',
              'only invented saved-row projection mode is open')
    evidence._digest(expected_revision, 40)
    v.require(type(draws) is list and 1 <= len(draws) <= analysis.MAX_DRAWS,
              'one to eight saved-row fixture draws')
    analysis.wrapper.document._draws(draws)
    checked = coverage.collect_saved_row_coverage(entries)
    v.require(checked['status'] == 'full_coverage_unanchored' and
              checked['chunk_indices'] == list(range(seed.SEEDS * seed.LAYOUTS)) and
              checked['bound_evaluations'] == 2880 and
              not checked['missing_chunk_indices'],
              'complete ordered saved-row inventory required')
    _distinct_sources(entries, checked['chunks'])
    clusters, diagnostics, slice_clusters, coverage_clusters = [], [], [], []
    source_chunks = []
    failed_attempt_history = []
    for index in range(seed.SEEDS):
        start = index * seed.LAYOUTS
        projected = []
        for entry, chunk in zip(entries[start:start + seed.LAYOUTS],
                                checked['chunks'][start:start + seed.LAYOUTS]):
            rows = coverage._load(entry['rows_raw'], entry['expected_pins']['rows'],
                                  coverage.RAW_LIMITS['rows'], 'rows')
            projected.extend(seed._check_chunk(chunk['chunk_index'], index,
                                               chunk, rows))
            source_chunks.append({
                'chunk_index': chunk['chunk_index'],
                'latest_attempt': chunk['latest_attempt'],
                'source_root': chunk['source_root'],
                'entry_pins': copy.deepcopy(entry['expected_pins']),
            })
            receipt = coverage._load(entry['receipt_raw'], entry['expected_pins']['receipt'],
                                     coverage.RAW_LIMITS['receipt'], 'receipt')
            for attempt in receipt['attempts'][:-1]:
                failed_attempt_history.append({
                    'chunk_index': chunk['chunk_index'], 'attempt': attempt['attempt'],
                    'state': attempt['state'], 'failure': copy.deepcopy(attempt['failure']),
                    'receipt_pin': copy.deepcopy(entry['expected_pins']['receipt']),
                })
        part = seed._contribution(index, projected)
        clusters.append(part['cluster'])
        diagnostics.append(part['diagnostic'])
        slice_clusters.append(part['slice_source_cluster'])
        candidates = {}
        for candidate in seed.arithmetic.CANDIDATES:
            candidates[candidate] = {}
            for layer in seed.arithmetic.STRATA[:2]:
                rows = [row for row in projected
                        if row['identity']['candidate_id'] == candidate and
                        row['identity']['stratum'] == layer]
                candidates[candidate][layer] = [row['status'] for row in rows]
        coverage_clusters.append({'cluster_id': part['cluster']['cluster_id'],
                                  'candidates': candidates})
    files, outcomes = _pack_inputs(
        clusters, diagnostics, slice_clusters, coverage_clusters,
        expected_revision=expected_revision, draws=draws)
    binding = {
        **CLOSED, 'format': FORMAT, 'mode': 'fixture',
        'status': 'fixture_worker_inputs_prepared',
        'source_revision': expected_revision,
        'declared_historical_source_revision':
            checked['chunks'][0]['historic_source_revision'],
        'recipe_id': checked['chunks'][0]['recipe_id'],
        'registry_pin': copy.deepcopy(checked['chunks'][0]['registry_pin']),
        'saved_row_projection_rechecked_here': True,
        'seed_contributions_rederived_from_rows_here': True,
        'planned_seeds': seed.SEEDS, 'planned_chunks': 480,
        'planned_evaluations': 2880, 'bound_evaluations': 2880,
        'coverage': outcomes, 'source_chunks': source_chunks,
        'failed_attempt_history': failed_attempt_history,
        'fixture_replicates': len(draws),
        'worker_input_pins': {name: analysis.observed._pin(raw)
                              for name, raw in files.items()},
        'trust_boundary': 'pinned invented reader/control bytes; '
                          'raw observations and campaign execution not authenticated',
    }
    v.require(len(v.canonical_json(binding)) <= MAX_BINDING_BYTES,
              'saved-row projection binding byte limit')
    return {'files': files, 'binding': binding}
