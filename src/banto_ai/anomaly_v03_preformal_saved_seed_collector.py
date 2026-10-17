"""Collect pinned invented seed contributions without promoting a campaign.

The one-seed contribution omits the historical recipe/source/registry anchor.
Each supplied chunk therefore also needs its externally pinned historical
manifest bytes.  These declarations can be compared across seeds, but neither
those pins nor this collector authenticate a common producer execution or
rederive the contributions from the saved reader rows.
"""
from __future__ import annotations

import copy
from pathlib import PureWindowsPath
import re

from . import anomaly_v03 as v
from . import anomaly_v03_analysis_adapter as adapter
from . import anomaly_v03_consumer_evidence as evidence
from . import anomaly_v03_inference_audit as arithmetic
from . import anomaly_v03_preformal_saved_row_coverage as coverage
from . import anomaly_v03_preformal_saved_seed_contribution as seed
from . import anomaly_v03_slice_fixture as slice_fixture
from . import anomaly_v03_slices as slices


FORMAT = 'anomaly-v03-preformal-saved-seed-collector-v1'
MAX_SEED_RAW = 512 * 1024
MAX_TOTAL_INPUT_BYTES = 256 * 1024**2
SEED_FIELDS = (set(seed.CLOSED) | {
    'format', 'scope', 'status', 'registered_seed_index',
    'invented_cluster_id', 'planned_layouts', 'bound_layouts',
    'layout_ids', 'missing_layouts', 'bound_evaluations',
    'planned_evaluations_for_seed', 'source_chunks',
    'cluster_contribution',
})
OPTIONAL_SEED_FIELDS = {'external_pinset_pin', 'trial_source_revision'}
CLOSED = {
    **seed.CLOSED,
    'producer_campaign_anchor': None,
    'campaign_coherence_authenticated': False,
    'historical_producer_execution_authenticated': False,
    'seed_contributions_rederived_from_rows_here': False,
    'reader_execution_authenticated_here': False,
    'saved_payload_bytes_reopened_here': False,
}


def _manifest(raw, expected_pin, chunk, index):
    """Bind one canonical manifest to one declared source-chunk pin."""
    coverage._same(expected_pin, chunk['entry_pins']['manifest'],
                   'seed/manifest external pin binding')
    value = coverage._load(raw, expected_pin, coverage.RAW_LIMITS['manifest'],
                           'manifest')
    v.require(set(value) == coverage.MANIFEST_FIELDS,
              'exact historical manifest fields')
    coverage._closed(value, {
        'format': coverage.MANIFEST_FORMAT,
        'scope': 'invented-registered-format-owned-generator-only',
        'chunk_index': index,
        'invented_only': True,
        'actual_registered_observations_read': False,
        'formal_permission': False,
    }, 'historical manifest')
    v.require(type(value['revision']) is str and
              re.fullmatch(r'[0-9a-f]{40}', value['revision']) is not None and
              type(value['recipe_id']) is str and bool(value['recipe_id']) and
              type(value['source']) is dict and
              value['source'].get('revision') == value['revision'] and
              type(value['source_snapshots']) is dict and
              set(value['source_snapshots']) == {value['revision']} and
              type(value['source_snapshot_pins']) is dict and
              bool(value['source_snapshot_pins']),
              'historical manifest recipe/source declaration')
    coverage._pins(value['source_snapshot_pins'],
                   'historical source snapshot pins')
    coverage._pins(value['output_pins'], 'historical manifest outputs')
    coverage._same(value['output_file_count'], len(value['output_pins']),
                   'historical output file count')
    coverage._same(value['output_bytes'],
                   sum(pin['bytes'] for pin in value['output_pins'].values()),
                   'historical output byte count')
    for name, output in (('receipt', 'saved/receipt.json'),
                         ('report', 'saved/report.json'),
                         ('savepoint', 'saved/savepoint.json')):
        coverage._same(value['output_pins'].get(output),
                       chunk['entry_pins'][name],
                       'historical manifest ' + name + ' pin')
    registry_pin = value['output_pins'].get('saved/registry.json')
    evidence._pin(registry_pin)
    evidence._absolute(value['root'])
    v.require(PureWindowsPath(value['root']).name.startswith(
        'anomaly-v03-preformal-registered-attempt-'),
        'historical invented attempt root')
    return {
        'revision': value['revision'],
        'recipe_id': value['recipe_id'],
        'source': value['source'],
        'source_snapshots': value['source_snapshots'],
        'source_snapshot_pins': value['source_snapshot_pins'],
        'registry_pin': registry_pin,
    }


def _contribution(value, requested):
    """Recheck supplied one-seed arithmetic, never its row provenance."""
    v.require(type(value) is dict and set(value) == {
        'cluster', 'diagnostic', 'slice_source_cluster'},
        'seed contribution fields')
    cluster = value['cluster']
    diagnostic = value['diagnostic']
    source = value['slice_source_cluster']
    cluster_id = f'invented-{requested:02d}'
    arithmetic._fixture_clusters([cluster])
    adapter._diagnostics([cluster], [diagnostic])
    v.require(type(source) is dict and set(source) ==
              {'cluster_id', 'candidates'} and
              type(source['candidates']) is dict and
              set(source['candidates']) == set(arithmetic.CANDIDATES),
              'seed slice source candidates')
    for item in (cluster, diagnostic, source):
        coverage._same(item['cluster_id'], cluster_id,
                       'ordered seed contribution cluster ID')
    template = slices.empty_counts()
    for candidate in arithmetic.CANDIDATES:
        layers = source['candidates'][candidate]
        v.require(type(layers) is dict and
                  set(layers) == set(arithmetic.STRATA[:2]),
                  'seed slice source strata')
        for layer in arithmetic.STRATA[:2]:
            supplied = layers[layer]
            slice_fixture._raw_shape(supplied, template)
            raw = slice_fixture._ordered_raw(supplied, template)
            coverage._same(raw['evaluations'], seed.LAYOUTS,
                           'seed slice evaluation coverage')
            slice_fixture.inputs._slice_counts(slices.describe(raw),
                                               seed.LAYOUTS)
            slice_fixture._marginals(raw)
            primary = cluster['candidates'][candidate][layer]
            slice_fixture._primary(raw, primary['counts'], described=False)
            delays = diagnostic['candidates'][candidate][layer][
                'detected_delays']
            v.require(all(type(delay) is int and 1 <= delay <= 5
                          for delay in delays),
                      'seed diagnostic integer delay seconds')
            histogram = [delays.count(second) for second in range(1, 6)]
            coverage._same(raw['delay_histogram'], histogram,
                           'seed slice/diagnostic delay histogram')
            coverage._same(raw['profile_inconclusive_evaluations'] > 0,
                           primary['profile_status'] == 'inconclusive',
                           'seed slice/profile status')
    return value


def _seed_result(raw, expected_pin):
    value = coverage._load(raw, expected_pin, MAX_SEED_RAW,
                           'seed contribution')
    v.require(SEED_FIELDS <= set(value) <=
              SEED_FIELDS | OPTIONAL_SEED_FIELDS,
              'seed contribution result fields')
    coverage._closed(value, seed.CLOSED, 'closed seed contribution')
    coverage._same(value['format'], seed.FORMAT,
                   'seed contribution version')
    coverage._same(value['scope'],
                   'one-invented-seed-saved-reader-contribution-only',
                   'seed contribution scope')
    if 'external_pinset_pin' in value:
        evidence._pin(value['external_pinset_pin'])
    if 'trial_source_revision' in value:
        v.require(type(value['trial_source_revision']) is str and
                  re.fullmatch(r'[0-9a-f]{40}',
                               value['trial_source_revision']) is not None,
                  'trial source revision declaration')
    requested = value['registered_seed_index']
    v.require(type(requested) is int and 0 <= requested < seed.SEEDS,
              'frozen seed index')
    coverage._same(value['invented_cluster_id'],
                   f'invented-{requested:02d}', 'invented seed cluster ID')
    coverage._same(value['planned_layouts'], seed.LAYOUTS,
                   'planned seed layouts')
    coverage._same(value['planned_evaluations_for_seed'],
                   seed.LAYOUTS * seed.SLOTS_PER_LAYOUT,
                   'planned seed evaluations')
    chunks = value['source_chunks']
    v.require(type(chunks) is list and len(chunks) <= seed.LAYOUTS,
              'bounded seed source chunks')
    layouts = []
    for chunk in chunks:
        v.require(type(chunk) is dict and set(chunk) == {
            'chunk_index', 'layout', 'latest_attempt', 'entry_pins'},
            'seed source chunk fields')
        layout = chunk['layout']
        v.require(type(layout) is int and 0 <= layout < seed.LAYOUTS and
                  (not layouts or layout > layouts[-1]),
                  'strictly ordered unique seed layouts')
        coverage._same(chunk['chunk_index'],
                       requested * seed.LAYOUTS + layout,
                       'frozen seed source chunk index')
        v.require(type(chunk['latest_attempt']) is int and
                  1 <= chunk['latest_attempt'] <= 64,
                  'bounded latest saved attempt')
        pins = chunk['entry_pins']
        v.require(type(pins) is dict and
                  set(pins) == set(coverage.RAW_LIMITS),
                  'ten seed source raw pins')
        for name, pin in pins.items():
            evidence._pin(pin)
            v.require(0 < pin['bytes'] <= coverage.RAW_LIMITS[name],
                      'bounded seed source raw pin')
        layouts.append(layout)
    coverage._same(value['layout_ids'], layouts,
                   'seed layout inventory')
    coverage._same(value['missing_layouts'],
                   [i for i in range(seed.LAYOUTS) if i not in layouts],
                   'missing seed layouts')
    coverage._same(value['bound_layouts'], len(layouts),
                   'bound seed layouts')
    coverage._same(value['bound_evaluations'],
                   seed.SLOTS_PER_LAYOUT * len(layouts),
                   'bound seed evaluations')
    complete = len(layouts) == seed.LAYOUTS
    coverage._same(value['status'],
                   'complete_seed_contribution_unanchored' if complete else
                   'partial_seed_contribution_unanchored',
                   'seed contribution completeness')
    if complete:
        _contribution(value['cluster_contribution'], requested)
    else:
        v.require(value['cluster_contribution'] is None,
                  'partial seed has no cluster contribution')
    return value


def collect_saved_seed_contributions(entries):
    """Bind up to forty externally pinned invented seed contribution reports.

    Each entry holds one `result_raw`, `expected_result_pin`, and ordered
    `manifest_entries` of `{raw, expected_pin}`.  This function performs no
    filesystem access.  The complete nested result remains unanchored and is
    not an authorized formal analysis input.
    """
    v.require(type(entries) is list and len(entries) <= seed.SEEDS,
              'at most forty seed contributions')
    total_bytes = 0
    for entry in entries:
        v.require(type(entry) is dict and set(entry) == {
            'result_raw', 'expected_result_pin', 'manifest_entries'},
            'seed collector entry fields')
        v.require(type(entry['result_raw']) is bytes and
                  0 < len(entry['result_raw']) <= MAX_SEED_RAW,
                  'bounded seed result raw')
        v.require(type(entry['manifest_entries']) is list and
                  len(entry['manifest_entries']) <= seed.LAYOUTS,
                  'bounded seed manifest entries')
        total_bytes += len(entry['result_raw'])
        for item in entry['manifest_entries']:
            v.require(type(item) is dict and set(item) ==
                      {'raw', 'expected_pin'} and
                      type(item['raw']) is bytes and
                      0 < len(item['raw']) <= coverage.RAW_LIMITS['manifest'],
                      'bounded seed manifest raw')
            total_bytes += len(item['raw'])
            v.require(total_bytes <= MAX_TOTAL_INPUT_BYTES,
                      'total seed collector input byte bound')
    previous = -1
    found_chunks = []
    seed_summaries = []
    contributions = []
    anchor = None
    manifest_count = 0
    manifest_seed_indices = set()
    roots = set()
    unique_control_pins = {name: set() for name in (
        'result', 'rows', 'manifest', 'receipt', 'report', 'savepoint')}
    for entry in entries:
        result = _seed_result(entry['result_raw'],
                              entry['expected_result_pin'])
        requested = result['registered_seed_index']
        v.require(requested > previous,
                  'strictly increasing unique seed index')
        previous = requested
        chunks = result['source_chunks']
        v.require(len(entry['manifest_entries']) == len(chunks),
                  'one external manifest per source chunk')
        for chunk, item in zip(chunks, entry['manifest_entries']):
            index = chunk['chunk_index']
            for name, observed in unique_control_pins.items():
                digest = chunk['entry_pins'][name]['sha256']
                v.require(digest not in observed,
                          'unique frozen source chunk ' + name + ' pin')
                observed.add(digest)
            current = _manifest(item['raw'], item['expected_pin'],
                                chunk, index)
            manifest = v.strict_json(item['raw'])
            root = evidence._absolute(manifest['root'])
            v.require(root not in roots, 'unique invented source roots')
            roots.add(root)
            if anchor is None:
                anchor = copy.deepcopy(current)
            else:
                coverage._same(current, anchor,
                               'cross-seed historical recipe/source/registry anchor')
            found_chunks.append(index)
            manifest_count += 1
            manifest_seed_indices.add(requested)
        if result['cluster_contribution'] is not None:
            contributions.append(result['cluster_contribution'])
        seed_summaries.append({
            'registered_seed_index': requested,
            'result_pin': copy.deepcopy(entry['expected_result_pin']),
            'layout_ids': copy.deepcopy(result['layout_ids']),
            'bound_evaluations': result['bound_evaluations'],
            'complete': result['cluster_contribution'] is not None,
        })
    found_seeds = [item['registered_seed_index'] for item in seed_summaries]
    missing_seeds = [i for i in range(seed.SEEDS) if i not in found_seeds]
    missing_chunks = [i for i in range(seed.SEEDS * seed.LAYOUTS)
                      if i not in found_chunks]
    complete = not missing_seeds and not missing_chunks
    v.require(not complete or len(contributions) == seed.SEEDS,
              'forty complete seed contributions required')
    nested = None
    if complete:
        clusters = [part['cluster'] for part in contributions]
        diagnostics = [part['diagnostic'] for part in contributions]
        sources = [part['slice_source_cluster'] for part in contributions]
        arithmetic._fixture_clusters(clusters)
        adapter._diagnostics(clusters, diagnostics)
        nested = {
            'clusters': clusters,
            'diagnostics': diagnostics,
            'slice_source': {'format': slice_fixture.INPUT_FORMAT,
                             'invented_only': True, 'clusters': sources},
        }
    return {
        **CLOSED,
        'format': FORMAT,
        'scope': 'pinned-invented-seed-contribution-inventory-only',
        'status': ('complete_unanchored_contribution_inventory' if complete
                   else 'partial_unanchored_contribution_inventory'),
        'planned_seeds': seed.SEEDS,
        'seed_indices': found_seeds,
        'missing_seed_indices': missing_seeds,
        'bound_seeds': len(found_seeds),
        'planned_chunks': seed.SEEDS * seed.LAYOUTS,
        'chunk_indices': found_chunks,
        'missing_chunk_indices': missing_chunks,
        'bound_chunks': len(found_chunks),
        'planned_evaluations': seed.SEEDS * seed.LAYOUTS *
                               seed.SLOTS_PER_LAYOUT,
        'bound_evaluations': sum(item['bound_evaluations']
                                 for item in seed_summaries),
        'seed_results': seed_summaries,
        'manifest_count': manifest_count,
        'historical_manifest_anchor_consistency_checked':
            manifest_count > 1,
        'cross_seed_manifest_anchor_consistency_checked':
            len(manifest_seed_indices) > 1,
        'declared_historical_manifest_anchor': None if anchor is None else {
            'revision': anchor['revision'],
            'recipe_id': anchor['recipe_id'],
            'registry_pin': anchor['registry_pin'],
            'canonical_sha256': v.canonical_sha256(anchor),
        },
        'unanchored_40_seed_contribution': nested,
    }
