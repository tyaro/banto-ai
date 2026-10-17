"""Bind invented summaries to the frozen holdout identities without a formal run.

This pure fixture boundary accepts no saved observation or producer result. The
summary rows and worker exits remain caller supplied declarations, even when all
registered identity slots are present. An attempt-specific invented marker
checks labels but cannot authenticate the actual origin of summary values.
"""
from __future__ import annotations

import copy
import hashlib

from . import anomaly_v03_registered_fixture as registration
from . import anomaly_v03_producer_input_fixture as primary
from . import anomaly_v03_producer_slice_fixture as compact
from . import anomaly_v03_analysis_adapter as adapter
from . import _anomaly_v03_contract as c


v = registration.v
evidence = registration.evidence
S = compact.S
FORMAT = 'anomaly-v03-registered-summary-fixture-v1'
MAX_SUMMARY = 64 * 1024**2


def _latest_result_slots(manifest):
    """Select every latest success/inconclusive slot, including failed attempts."""
    selected = []
    for chunk in manifest['chunks']:
        attempts = chunk['attempts']
        if attempts:
            record = attempts[-1]['record']
            selected.extend((row, record['attempt']) for row in record['evaluations']
                            if row['status'] in ('success', 'inconclusive'))
    return selected


def _summary_marker(identity, attempt):
    """An invented declaration tag, not proof of the summary's actual origin."""
    raw = (f"anomaly-v03-invented-summary-v1:{identity['evaluation_id']}:"
           f"attempt-{attempt}").encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def _row(row, slot, attempt, registry_pin):
    evidence._keys(row,
        'identity attempt evaluation_marker_sha256 summary_marker_sha256 counts '
        'effective_clean_seconds delay_histogram slice_cells',
        'registered invented summary fields')
    evidence._same(row['identity'], slot['identity'], 'latest registered summary identity/order')
    evidence._same(row['attempt'], attempt, 'latest registered summary attempt')
    evidence._same(row['evaluation_marker_sha256'], slot['evaluation_sha256'],
                   'latest invented evaluation marker')
    evidence._same(row['summary_marker_sha256'], _summary_marker(slot['identity'], attempt),
                   'latest invented summary attempt marker')
    summary = {'format': primary.SUMMARY_FORMAT, 'mode': 'fixture', 'invented_only': True,
        'registration_pin': registry_pin, 'identity': slot['identity'], 'attempt': attempt,
        'input_hashes': slot['input_hashes'], 'profile_status': slot['profile_status'],
        'counts': row['counts'], 'effective_clean_seconds': row['effective_clean_seconds'],
        'delay_histogram': row['delay_histogram']}
    primary._summary(summary, slot, attempt, registry_pin)
    raw = compact._decode(row['slice_cells'])
    compact._check(raw, summary)
    return raw


def _aggregates(rows, selected, validated_slices):
    seeds = v.seed_registry()['entries'][c.ROLES.index('holdout')]['seeds']
    seed_index = {seed: index for index, seed in enumerate(seeds)}
    metrics = primary.arithmetic.METRICS
    candidates = primary.arithmetic.CANDIDATES
    strata = primary.arithmetic.STRATA[:2]
    groups = {}
    for row, (slot, _), raw in zip(rows, selected, validated_slices):
        identity = slot['identity']
        key = (seed_index[identity['seed']], identity['candidate_id'], identity['stratum'])
        if key not in groups:
            groups[key] = {'counts': {name: [0, 0] for name in metrics},
                'effective': 0, 'histogram': [0] * 5, 'inconclusive': False,
                'slices': S.empty_counts(), 'layouts': []}
        group = groups[key]
        group['layouts'].append(identity['layout'])
        for name in metrics:
            pair = row['counts'][name]
            group['counts'][name][0] += pair[0]
            group['counts'][name][1] += pair[1]
        group['effective'] += row['effective_clean_seconds']
        for i, value in enumerate(row['delay_histogram']):
            group['histogram'][i] += value
        group['inconclusive'] |= slot['status'] == 'inconclusive'
        S.add_counts(group['slices'], raw)

    clusters = []
    diagnostics = []
    slice_source = {'format': compact.connection.INPUT_FORMAT, 'invented_only': True,
                    'clusters': []}
    mapping = []
    for index, seed in enumerate(seeds):
        identifier = f'invented-{index:02d}'
        mapping.append({'registered_index': index, 'registered_seed': seed,
                        'invented_cluster_id': identifier})
        cluster = {'cluster_id': identifier, 'candidates': {}}
        diagnostic = {'cluster_id': identifier, 'candidates': {}}
        slice_cluster = {'cluster_id': identifier, 'candidates': {}}
        for candidate in candidates:
            cluster['candidates'][candidate] = {}
            diagnostic['candidates'][candidate] = {}
            slice_cluster['candidates'][candidate] = {}
            for stratum in strata:
                group = groups[index, candidate, stratum]
                evidence._same(group['layouts'], list(range(12)), 'twelve registered layouts')
                raw = group['slices']
                evidence._same(raw['evaluations'], 12, 'twelve invented slice evaluations')
                compact.connection._primary(raw, group['counts'], described=False)
                evidence._same(raw['delay_histogram'], group['histogram'],
                               'aggregate invented delay histogram')
                cluster['candidates'][candidate][stratum] = {
                    'profile_status': 'inconclusive' if group['inconclusive'] else 'calibrated',
                    'counts': copy.deepcopy(group['counts'])}
                diagnostic['candidates'][candidate][stratum] = {
                    'effective_clean_seconds': group['effective'],
                    'detected_delays': [second for second, count in enumerate(group['histogram'], 1)
                                        for _ in range(count)]}
                slice_cluster['candidates'][candidate][stratum] = raw
        clusters.append(cluster)
        diagnostics.append(diagnostic)
        slice_source['clusters'].append(slice_cluster)
    primary.arithmetic._fixture_clusters(clusters)
    adapter._diagnostics(clusters, diagnostics)
    return mapping, clusters, diagnostics, slice_source


def bind_registered_summaries(manifest_raw, registry_raw, summary_raw, *, expected_mode,
                              expected_manifest_pin, expected_registry_pin,
                              expected_summary_pin):
    """Check every supplied fixture row and return aggregates only if complete.

    Incomplete/failed campaigns retain their latest coverage and failure history
    but never return 40-cluster aggregates. This is not the saved chunk reader.
    """
    v.require(type(expected_mode) is str and expected_mode == registration.MODE,
              'formal/unknown registered summary mode is closed')
    checked = registration.validate_fixture(manifest_raw, registry_raw,
        expected_mode=expected_mode, expected_manifest_pin=expected_manifest_pin,
        expected_registry_pin=expected_registry_pin)
    evidence._pin(expected_summary_pin)
    v.require(0 < expected_summary_pin['bytes'] <= MAX_SUMMARY,
              'bounded external invented summary pin')
    evidence._raw(summary_raw, expected_summary_pin, 'external invented summary bytes')
    bundle = v.strict_json(summary_raw)
    v.require(summary_raw == v.canonical_json(bundle), 'canonical invented summary bytes')
    evidence._keys(bundle, 'format mode invented_only registry_pin manifest_pin rows',
                   'invented summary bundle fields')
    evidence._same([bundle['format'], bundle['mode'], bundle['invented_only'],
                    bundle['registry_pin'], bundle['manifest_pin']],
                   [FORMAT, registration.MODE, True, expected_registry_pin,
                    expected_manifest_pin], 'invented summary source pins')
    manifest = v.strict_json(manifest_raw)
    producer = manifest['producer']
    evidence._same(producer['worker']['exit_confirmed'],
                   checked['producer_worker_exit_declared'],
                   'registered fixture producer exit declaration')
    selected = _latest_result_slots(manifest)
    rows = bundle['rows']
    v.require(type(rows) is list and len(rows) == len(selected),
              'exact latest result-marker summary row inventory')
    validated_slices = [_row(row, slot, attempt, expected_registry_pin)
                        for row, (slot, attempt) in zip(rows, selected)]
    complete = checked['status'] == 'fixture_inventory_complete'
    mapping = clusters = diagnostics = slice_source = None
    if complete:
        v.require(len(rows) == 2880, 'all registered summary rows required')
        mapping, clusters, diagnostics, slice_source = _aggregates(rows, selected,
                                                                   validated_slices)
    return {'format': 'anomaly-v03-registered-summary-fixture-bound-v1',
        'mode': registration.MODE,
        'status': 'fixture_summaries_bound' if complete else 'fixture_summaries_incomplete',
        'registry_pin': copy.deepcopy(expected_registry_pin),
        'manifest_pin': copy.deepcopy(expected_manifest_pin),
        'summary_pin': copy.deepcopy(expected_summary_pin),
        'planned_chunks': 480, 'planned_evaluations': 2880,
        'latest_result_marker_rows_checked': len(rows),
        'coverage': copy.deepcopy(checked['coverage']),
        'failed_attempt_history': copy.deepcopy(checked['failed_attempt_history']),
        'producer_state': producer['state'],
        'producer_failure': copy.deepcopy(producer['failure']),
        'producer_worker_exit_declared': producer['worker']['exit_confirmed'],
        'registration_map': mapping, 'clusters': clusters,
        'diagnostics': diagnostics, 'slice_source': slice_source,
        'invented_primary_and_slice_consistency_checked': bool(rows),
        'supplied_summary_bundle_bytes_verified': True,
        'attempt_specific_summary_marker_checked': bool(rows),
        'actual_summary_origin_authenticated': False,
        'real_saved_chunk_reader_used': False, 'registered_observations_read': False,
        'actual_worker_exit_authenticated': False, 'registered_input_bytes_verified': False,
        'campaign_evaluations_credited': 0, 'formal_permission': False,
        'analysis_authorized': False, 'promotion_allowed': False,
        'independent_s6_complete': False}
