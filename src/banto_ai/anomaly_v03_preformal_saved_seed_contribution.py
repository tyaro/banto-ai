"""Pure one-seed contribution from pinned invented registered-format readers.

Each supplied entry is the ten-raw-file boundary accepted by the existing
saved-row coverage checker. A complete contribution needs the twelve ordered
layouts of one seed. This does not authorize a 40-cluster analysis input or
authenticate the historical producer, process tree, or saved payloads anew.
"""
from __future__ import annotations

import copy

from . import anomaly_v03 as v
from . import anomaly_v03_analysis_adapter as adapter
from . import anomaly_v03_inference_audit as arithmetic
from . import anomaly_v03_preformal_saved_row_coverage as coverage
from . import anomaly_v03_slice_fixture as slice_fixture
from . import anomaly_v03_slices as slices


FORMAT = 'anomaly-v03-preformal-saved-seed-contribution-v1'
LAYOUTS = 12
SLOTS_PER_LAYOUT = 6
SEEDS = 40
CLOSED = {
    'invented_only': True,
    'registered_observations_read': False,
    'actual_registered_observations_read': False,
    'saved_payload_bytes_reopened_here': False,
    'reader_execution_authenticated_here': False,
    'campaign_coherence_authenticated': False,
    'source_closure_complete': False,
    'runtime_closure_complete': False,
    'full_end_to_end_budget_measured': False,
    'campaign_evaluations_credited': 0,
    'formal_permission': False,
    'analysis_authorized': False,
    'promotion_allowed': False,
    'independent_s6_complete': False,
    'clusters': None,
    'diagnostics': None,
    'slice_source': None,
}


def _check_chunk(index, requested, checked, rows):
    """Keep the exact frozen identity and latest-attempt relation visible."""
    start = requested * LAYOUTS
    v.require(start <= index < start + LAYOUTS,
              'saved seed contribution has a foreign chunk')
    layout = index - start
    identities = v.evaluation_inventory('holdout')[index * SLOTS_PER_LAYOUT:
                                                      (index + 1) * SLOTS_PER_LAYOUT]
    v.require(len(identities) == SLOTS_PER_LAYOUT,
              'saved seed contribution frozen inventory')
    for name, wanted in (
        ('chunk_index', index),
        ('registered_seed_index', requested),
        ('registered_seed', identities[0]['seed']),
        ('layout', layout),
    ):
        coverage._same(checked[name], wanted,
                       'saved seed contribution chunk ' + name)
    for name, wanted in (
        ('chunk_index', index),
        ('registered_seed_index', requested),
        ('registered_seed', identities[0]['seed']),
        ('invented_cluster_id', f'invented-{requested:02d}'),
        ('verified_layout', layout),
        ('latest_attempt', checked['latest_attempt']),
    ):
        coverage._same(rows[name], wanted,
                       'saved seed contribution rows ' + name)
    supplied = rows['rows']
    v.require(type(supplied) is list and len(supplied) == SLOTS_PER_LAYOUT,
              'saved seed contribution six rows')
    coverage._same([row['identity'] for row in supplied], identities,
                   'saved seed contribution ordered identities')
    for row in supplied:
        coverage._same(row['chunk_index'], index, 'row chunk')
        coverage._same(row['registered_seed_index'], requested, 'row seed')
        coverage._same(row['invented_cluster_id'],
                       f'invented-{requested:02d}', 'row cluster')
        coverage._same(row['attempt'], checked['latest_attempt'],
                       'row latest attempt')
        v.require((row['status'], row['profile_status']) in
                  (('success', 'calibrated'),
                   ('inconclusive', 'inconclusive')),
                  'complete seed row outcome/profile')
    return supplied


def _contribution(requested, projected):
    """Pool counts and slice cells, preserving the twelve source layouts."""
    cluster_id = f'invented-{requested:02d}'
    cluster = {'cluster_id': cluster_id, 'candidates': {}}
    diagnostic = {'cluster_id': cluster_id, 'candidates': {}}
    source = {'cluster_id': cluster_id, 'candidates': {}}
    for candidate in arithmetic.CANDIDATES:
        cluster['candidates'][candidate] = {}
        diagnostic['candidates'][candidate] = {}
        source['candidates'][candidate] = {}
        for layer in arithmetic.STRATA[:2]:
            selected = [row for row in projected
                        if row['identity']['candidate_id'] == candidate and
                        row['identity']['stratum'] == layer]
            v.require(len(selected) == LAYOUTS and
                      [row['identity']['layout'] for row in selected] ==
                      list(range(LAYOUTS)),
                      'twelve ordered cell layouts')
            counts = {
                name: [sum(row['primary']['counts'][name][part]
                           for row in selected) for part in (0, 1)]
                for name in arithmetic.METRICS
            }
            profile = ('inconclusive' if any(
                row['profile_status'] == 'inconclusive' for row in selected)
                else 'calibrated')
            histogram = [sum(row['primary']['delay_histogram'][part]
                             for row in selected) for part in range(5)]
            cell = slices.empty_counts()
            for row in selected:
                slices.add_counts(cell, row['slices'])
            v.require(cell['evaluations'] == LAYOUTS,
                      'twelve saved slice evaluations')
            coverage._same(cell['delay_histogram'], histogram,
                           'saved seed pooled delay histogram')
            coverage._same(cell['profile_inconclusive_evaluations'] > 0,
                           profile == 'inconclusive',
                           'saved seed pooled profile status')
            slice_fixture.inputs._slice_counts(slices.describe(cell), LAYOUTS)
            slice_fixture._marginals(cell)
            slice_fixture._primary(cell, counts, described=False)
            cluster['candidates'][candidate][layer] = {
                'profile_status': profile, 'counts': counts}
            diagnostic['candidates'][candidate][layer] = {
                'effective_clean_seconds': sum(
                    row['primary']['effective_clean_seconds']
                    for row in selected),
                'detected_delays': [second for second, amount in
                                    enumerate(histogram, 1)
                                    for _ in range(amount)],
            }
            source['candidates'][candidate][layer] = cell
    arithmetic._fixture_clusters([cluster])
    adapter._diagnostics([cluster], [diagnostic])
    return {'cluster': cluster, 'diagnostic': diagnostic,
            'slice_source_cluster': source}


def aggregate_saved_seed(entries, *, registered_seed_index):
    """Check up to twelve pinned reader entries and return one contribution.

    Partial input is informative only: no cluster contribution is returned.
    Even a complete contribution does not become a 40-cluster input, and
    source/runner/campaign authenticity must be established elsewhere.
    """
    v.require(type(registered_seed_index) is int and
              0 <= registered_seed_index < SEEDS,
              'registered seed index 0..39')
    v.require(type(entries) is list and len(entries) <= LAYOUTS,
              'at most twelve saved reader entries')
    checked = coverage.collect_saved_row_coverage(entries)
    v.require(checked['invented_only'] is True and
              checked['campaign_coherence_authenticated'] is False and
              checked['clusters'] is None and
              checked['diagnostics'] is None and
              checked['slice_source'] is None,
              'saved row coverage remains unanchored')
    projected = []
    sources = []
    for entry, chunk in zip(entries, checked['chunks']):
        index = chunk['chunk_index']
        rows = coverage._load(entry['rows_raw'], entry['expected_pins']['rows'],
                              coverage.RAW_LIMITS['rows'], 'rows')
        projected.extend(_check_chunk(index, registered_seed_index, chunk, rows))
        sources.append({
            'chunk_index': index,
            'layout': chunk['layout'],
            'latest_attempt': chunk['latest_attempt'],
            'entry_pins': copy.deepcopy(entry['expected_pins']),
        })
    found = [row['layout'] for row in sources]
    missing = [layout for layout in range(LAYOUTS) if layout not in found]
    complete = not missing
    v.require(not complete or len(projected) == LAYOUTS * SLOTS_PER_LAYOUT,
              'complete seed needs seventy-two rows')
    contribution = _contribution(registered_seed_index, projected) if complete else None
    return {
        **CLOSED,
        'format': FORMAT,
        'scope': 'one-invented-seed-saved-reader-contribution-only',
        'status': ('complete_seed_contribution_unanchored' if complete
                   else 'partial_seed_contribution_unanchored'),
        'registered_seed_index': registered_seed_index,
        'invented_cluster_id': f'invented-{registered_seed_index:02d}',
        'planned_layouts': LAYOUTS,
        'bound_layouts': len(found),
        'layout_ids': found,
        'missing_layouts': missing,
        'bound_evaluations': len(projected),
        'planned_evaluations_for_seed': LAYOUTS * SLOTS_PER_LAYOUT,
        'source_chunks': sources,
        'cluster_contribution': contribution,
    }
