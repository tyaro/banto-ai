"""Explicit fixture composition of a saved-reader subset and invented rows.

The complete metadata fixture and each subset receipt keep their original
pins and histories. Replacements occupy only their exact frozen slots. This
pure function checks retained reader claims, not observation bytes or process
execution. Its complete numerical fixture never becomes a complete observed
campaign. The original same-origin projection contract is unchanged.
"""
from __future__ import annotations

import copy

from . import anomaly_v03_saved_row_fixture_projection as base


FORMAT = 'anomaly-v03-observation-subset-fixture-projection-v1'
PIPELINE_FORMAT = 'anomaly-v03-observation-subset-fixture-document-publication-v1'
SCOPE = 'retained-partial-reader-rows-plus-invented-metadata-full-draw-fixture'


def validate_subset_request(entries, expected_subset):
    """Validate external slot/pin declarations before consuming reader claims."""
    base.v.require(type(entries) is list and 0 < len(entries) <= 480 and
                   type(expected_subset) is list and len(entries) == len(expected_subset),
                   'nonempty bounded explicit reader subset required')
    previous = -1
    for descriptor in expected_subset:
        base.v.require(type(descriptor) is dict and set(descriptor) ==
                       {'chunk_index', 'expected_pins'}, 'subset descriptor fields')
        index = descriptor['chunk_index']
        base.v.require(type(index) is int and previous < index < 480,
                       'strictly ordered unique external subset slots')
        previous = index
        pins = descriptor['expected_pins']
        base.v.require(type(pins) is dict and set(pins) == set(base.coverage.RAW_LIMITS),
                       'exact external subset control pins')
        for name, maximum in base.coverage.RAW_LIMITS.items():
            base.evidence._pin(pins[name])
            base.v.require(0 < pins[name]['bytes'] <= maximum,
                           'external subset control byte bound')
    return copy.deepcopy(expected_subset)


def _final_recheck_claim(entry, chunk):
    result = base.coverage._load(entry['result_raw'], entry['expected_pins']['result'],
                                 base.coverage.RAW_LIMITS['result'], 'subset result')
    manifest = base.coverage._load(entry['manifest_raw'], entry['expected_pins']['manifest'],
                                   base.coverage.RAW_LIMITS['manifest'], 'subset manifest')
    for name in ('saved_attempt_final_disk_recheck_completed',
                 'saved_attempt_final_disk_recheck_inside_budget',
                 'saved_rows_final_disk_recheck_completed'):
        base.evidence._same(result.get(name), True, 'subset final recheck ' + name)
    recheck = result.get('saved_attempt_final_disk_recheck')
    base.evidence._same(recheck, {
        'saved_files': 22, 'saved_bytes': manifest['output_bytes'],
        'latest_attempt': chunk['latest_attempt'], 'disk_pin_recheck_completed': True,
        'path_scope': 'fixed-selected-latest-attempt-files',
        'raw_observations_rederived_during_recheck': False, 'formal_permission': False,
    }, 'subset final selected saved-byte claim')


def recheck_subset(entries, expected_subset):
    expected_subset = validate_subset_request(entries, expected_subset)
    names = set(base.coverage.RAW_LIMITS)
    for entry, descriptor in zip(entries, expected_subset):
        base.v.require(type(entry) is dict and set(entry) ==
                       {name + '_raw' for name in names} | {'expected_pins'},
                       'subset retained control fields changed')
        base.evidence._same(entry['expected_pins'], descriptor['expected_pins'],
                            'subset retained external pins changed')
        for name, maximum in base.coverage.RAW_LIMITS.items():
            raw = entry[name + '_raw']
            base.v.require(type(raw) is bytes and 0 < len(raw) <= maximum,
                           'subset retained control byte bound')
            base.evidence._raw(raw, descriptor['expected_pins'][name],
                               'subset retained ' + name + ' pin')


def prepare_inputs(metadata_entries, subset_entries, *, expected_subset,
                   expected_mode, expected_revision, draws):
    """Return a closed full fixture with independently retained subset lineage.

    All other rows are explicitly metadata fixtures. No padding or cloning of
    subset rows is permitted, and no raw reader/process is invoked here.
    """
    base.v.require(type(expected_mode) is str and expected_mode == 'fixture',
                   'only observation-subset fixture mode is open')
    base.evidence._digest(expected_revision, 40)
    base.v.require(type(draws) is list and 1 <= len(draws) <= base.analysis.MAX_DRAWS,
                   'one to eight observation-subset fixture draws')
    base.analysis.wrapper.document._draws(draws)
    expected_subset = validate_subset_request(subset_entries, expected_subset)
    recheck_subset(subset_entries, expected_subset)
    base.v.require(type(metadata_entries) is list, 'metadata fixture entries required')
    total = 0
    for entry in [*metadata_entries, *subset_entries]:
        base.v.require(type(entry) is dict, 'fixture composition entry object')
        for name in base.coverage.RAW_LIMITS:
            raw = entry.get(name + '_raw')
            base.v.require(type(raw) is bytes, 'fixture composition raw bytes')
            total += len(raw)
            base.v.require(total <= base.coverage.MAX_TOTAL_INPUT_BYTES,
                           'combined metadata and subset byte bound')

    metadata = base.prepare_inputs(metadata_entries, expected_mode=expected_mode,
                                   expected_revision=expected_revision, draws=draws)
    checked = base.coverage.collect_saved_row_coverage(subset_entries)
    base.evidence._same(checked['chunk_indices'],
                        [row['chunk_index'] for row in expected_subset],
                        'subset retained frozen slots')
    replacements = {}
    effective_chunks = copy.deepcopy(metadata['binding']['source_chunks'])
    for record in effective_chunks:
        record.update(row_origin_kind='invented-metadata-fixture',
            historic_source_revision=metadata['binding']['declared_historical_source_revision'],
            recipe_id=metadata['binding']['recipe_id'])
    subset_chunks = []
    for entry, chunk in zip(subset_entries, checked['chunks']):
        index = chunk['chunk_index']
        _final_recheck_claim(entry, chunk)
        rows = base.coverage._load(entry['rows_raw'], entry['expected_pins']['rows'],
                                   base.coverage.RAW_LIMITS['rows'], 'subset rows')
        replacements[index] = base.seed._check_chunk(
            index, index // base.seed.LAYOUTS, chunk, rows)
        record = {
            'chunk_index': index, 'latest_attempt': chunk['latest_attempt'],
            'source_root': chunk['source_root'],
            'entry_pins': copy.deepcopy(entry['expected_pins']),
            'historic_source_revision': chunk['historic_source_revision'],
            'recipe_id': chunk['recipe_id'],
            'row_origin_kind': 'retained-reader-subset-claims',
        }
        effective_chunks[index] = record
        subset_chunks.append(copy.deepcopy(record))
    combined = list(metadata_entries)
    for entry, descriptor in zip(subset_entries, expected_subset):
        combined[descriptor['chunk_index']] = entry
    # Cross-origin fixtures still cannot reuse a root or a selected control pin.
    base._distinct_sources(combined, effective_chunks)

    values = {name: base.v.strict_json(raw) for name, raw in metadata['files'].items()}
    fixture = values['fixture/input.json']
    slice_clusters = values['fixture/slices.json']['clusters']
    coverage_clusters = values['fixture/coverage.json']['clusters']
    affected = sorted({index // base.seed.LAYOUTS for index in replacements})
    for seed_index in affected:
        projected = []
        for index in range(seed_index * base.seed.LAYOUTS,
                           (seed_index + 1) * base.seed.LAYOUTS):
            if index in replacements:
                projected.extend(replacements[index])
            else:
                entry = metadata_entries[index]
                rows = base.coverage._load(entry['rows_raw'], entry['expected_pins']['rows'],
                                           base.coverage.RAW_LIMITS['rows'], 'metadata rows')
                projected.extend(rows['rows'])
        part = base.seed._contribution(seed_index, projected)
        fixture['clusters'][seed_index] = part['cluster']
        fixture['diagnostics'][seed_index] = part['diagnostic']
        slice_clusters[seed_index] = part['slice_source_cluster']
        coverage_clusters[seed_index] = {
            'cluster_id': part['cluster']['cluster_id'],
            'candidates': {candidate: {layer: [row['status'] for row in projected
                if row['identity']['candidate_id'] == candidate and
                   row['identity']['stratum'] == layer]
                for layer in base.seed.arithmetic.STRATA[:2]}
                for candidate in base.seed.arithmetic.CANDIDATES},
        }
    files, outcomes = base._pack_inputs(
        fixture['clusters'], fixture['diagnostics'], slice_clusters, coverage_clusters,
        expected_revision=expected_revision, draws=draws)
    history = [copy.deepcopy(row) for row in metadata['binding']['failed_attempt_history']
               if row['chunk_index'] not in replacements]
    for entry, descriptor in zip(subset_entries, expected_subset):
        receipt = base.coverage._load(entry['receipt_raw'], entry['expected_pins']['receipt'],
                                      base.coverage.RAW_LIMITS['receipt'], 'subset receipt')
        for attempt in receipt['attempts'][:-1]:
            history.append({'chunk_index': descriptor['chunk_index'],
                'attempt': attempt['attempt'], 'state': attempt['state'],
                'failure': copy.deepcopy(attempt['failure']),
                'receipt_pin': copy.deepcopy(entry['expected_pins']['receipt'])})
    history.sort(key=lambda row: (row['chunk_index'], row['attempt']))
    binding = {
        **metadata['binding'], 'format': FORMAT,
        'declared_historical_source_revision': None, 'recipe_id': None,
        'metadata_historical_source_revision':
            metadata['binding']['declared_historical_source_revision'],
        'metadata_recipe_id': metadata['binding']['recipe_id'],
        'metadata_source_chunks': copy.deepcopy(metadata['binding']['source_chunks']),
        'metadata_worker_input_pins': copy.deepcopy(metadata['binding']['worker_input_pins']),
        'metadata_failed_attempt_history':
            copy.deepcopy(metadata['binding']['failed_attempt_history']),
        'source_chunks': effective_chunks, 'subset_source_chunks': subset_chunks,
        'expected_subset': expected_subset, 'affected_seed_indices': affected,
        'subset_chunks': len(replacements), 'subset_evaluations': 6 * len(replacements),
        'remaining_metadata_chunks': 480 - len(replacements),
        'retained_subset_recheck_claims_checked': True,
        'subset_observation_payloads_reopened_here': False,
        'complete_observation_campaign_verified': False,
        'cross_origin_composition_is_fixture_only': True,
        'combined_control_input_bytes': total,
        'coverage': outcomes, 'failed_attempt_history': history,
        'worker_input_pins': {name: base.analysis.observed._pin(raw)
                              for name, raw in files.items()},
        'trust_boundary': 'retained subset reader claims plus explicitly invented '
                          'metadata rows; separate origins; no complete observed campaign',
    }
    base.v.require(len(base.v.canonical_json(binding)) <= base.MAX_BINDING_BYTES,
                   'observation-subset binding byte limit')
    return {'files': files, 'binding': binding}
