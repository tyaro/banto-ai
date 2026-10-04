"""Pinned invented seed inventory remains outside the formal campaign gate."""
import copy
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_inference_audit as arithmetic
from banto_ai import anomaly_v03_preformal_saved_seed_collector as collector
from banto_ai import anomaly_v03_preformal_saved_seed_contribution as seed
from tests.test_anomaly_v03_preformal_saved_seed_contribution import chunk_entry
from tests.test_anomaly_v03_registered_saved_summary import pin


def package(result, manifests):
    raw = v.canonical_json(result)
    return {
        'result_raw': raw,
        'expected_result_pin': pin(raw),
        'manifest_entries': [{'raw': raw_manifest,
                              'expected_pin': pin(raw_manifest)}
                             for raw_manifest in manifests],
    }


def edit_result(entry, change):
    altered = copy.deepcopy(entry)
    result = v.strict_json(altered['result_raw'])
    change(result)
    altered['result_raw'] = v.canonical_json(result)
    altered['expected_result_pin'] = pin(altered['result_raw'])
    return altered


def edit_manifest(entry, change):
    altered = copy.deepcopy(entry)
    manifest_entry = altered['manifest_entries'][0]
    manifest = v.strict_json(manifest_entry['raw'])
    change(manifest)
    manifest_entry['raw'] = v.canonical_json(manifest)
    manifest_entry['expected_pin'] = pin(manifest_entry['raw'])
    result = v.strict_json(altered['result_raw'])
    result['source_chunks'][0]['entry_pins']['manifest'] = \
        manifest_entry['expected_pin']
    altered['result_raw'] = v.canonical_json(result)
    altered['expected_result_pin'] = pin(altered['result_raw'])
    return altered


class SavedSeedCollectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        first = chunk_entry(0)
        next_seed = chunk_entry(12)
        cls.partial_zero = package(
            seed.aggregate_saved_seed([first], registered_seed_index=0),
            [first['manifest_raw']])
        cls.partial_one = package(
            seed.aggregate_saved_seed([next_seed], registered_seed_index=1),
            [next_seed['manifest_raw']])
        source = [chunk_entry(layout) for layout in range(12)]
        cls.complete_zero = package(
            seed.aggregate_saved_seed(source, registered_seed_index=0),
            [entry['manifest_raw'] for entry in source])

    def test_partial_inventory_checks_pins_but_emits_no_forty_cluster_input(self):
        with patch('builtins.open', side_effect=AssertionError('unexpected I/O')):
            result = collector.collect_saved_seed_contributions(
                [self.partial_zero, self.partial_one])
        self.assertEqual(result['seed_indices'], [0, 1])
        self.assertEqual(result['chunk_indices'], [0, 12])
        self.assertEqual(result['bound_evaluations'], 12)
        self.assertEqual(result['missing_seed_indices'], list(range(2, 40)))
        self.assertIn(1, result['missing_chunk_indices'])
        self.assertTrue(result['historical_manifest_anchor_consistency_checked'])
        self.assertIsNone(result['unanchored_40_seed_contribution'])
        self.assertIsNone(result['clusters'])
        self.assertIsNone(result['diagnostics'])
        self.assertIsNone(result['slice_source'])
        self.assertFalse(result['formal_permission'])
        self.assertFalse(result['analysis_authorized'])
        self.assertFalse(result['campaign_coherence_authenticated'])
        self.assertEqual(result['campaign_evaluations_credited'], 0)

    def test_missing_duplicate_order_and_foreign_chunk_reject(self):
        partial = collector.collect_saved_seed_contributions(
            [self.partial_zero])
        self.assertEqual(partial['missing_seed_indices'], list(range(1, 40)))
        self.assertIsNone(partial['unanchored_40_seed_contribution'])
        for entries in ([self.partial_zero, self.partial_zero],
                        [self.partial_one, self.partial_zero]):
            with self.assertRaisesRegex(ValueError,
                                        'strictly increasing unique seed'):
                collector.collect_saved_seed_contributions(entries)
        foreign = edit_result(self.partial_zero,
                              lambda result: result['source_chunks'][0].update(
                                  chunk_index=12))
        with self.assertRaisesRegex(ValueError, 'frozen seed source chunk'):
            collector.collect_saved_seed_contributions([foreign])
        missing = edit_result(self.complete_zero,
                              lambda result: result['source_chunks'].pop())
        with self.assertRaises(ValueError):
            collector.collect_saved_seed_contributions([missing])

    def test_cross_seed_anchor_flag_needs_manifests_from_two_seeds(self):
        first = chunk_entry(0)
        second = chunk_entry(1)
        two_in_one_seed = package(seed.aggregate_saved_seed(
            [first, second], registered_seed_index=0),
            [first['manifest_raw'], second['manifest_raw']])
        no_manifests = package(seed.aggregate_saved_seed(
            [], registered_seed_index=1), [])
        result = collector.collect_saved_seed_contributions(
            [two_in_one_seed, no_manifests])
        self.assertTrue(result['historical_manifest_anchor_consistency_checked'])
        self.assertFalse(result['cross_seed_manifest_anchor_consistency_checked'])

    def test_external_result_manifest_and_canonical_pins_reject(self):
        bad_result = copy.deepcopy(self.partial_zero)
        bad_result['expected_result_pin'] = pin(b'wrong')
        with self.assertRaisesRegex(ValueError, 'external seed contribution pin'):
            collector.collect_saved_seed_contributions([bad_result])
        bad_manifest = copy.deepcopy(self.partial_zero)
        bad_manifest['manifest_entries'][0]['expected_pin'] = pin(b'wrong')
        with self.assertRaisesRegex(ValueError, 'seed/manifest external pin'):
            collector.collect_saved_seed_contributions([bad_manifest])
        noncanonical = copy.deepcopy(self.partial_zero)
        noncanonical['result_raw'] += b'\n'
        noncanonical['expected_result_pin'] = pin(noncanonical['result_raw'])
        with self.assertRaisesRegex(ValueError, 'canonical seed contribution'):
            collector.collect_saved_seed_contributions([noncanonical])

    def test_cross_seed_revision_recipe_source_and_registry_disagreement_reject(self):
        def different_revision(manifest):
            old = manifest['revision']
            new = 'b' * 40
            manifest['revision'] = new
            manifest['source']['revision'] = new
            manifest['source_snapshots'] = {
                new: manifest['source_snapshots'][old]}

        def different_recipe(manifest):
            manifest['recipe_id'] = 'another-invented-recipe'

        def different_source(manifest):
            manifest['source']['selected_files'] = ['src/invented.py']

        def different_registry(manifest):
            manifest['output_pins']['saved/registry.json'] = pin(b'other')
            manifest['output_bytes'] = sum(
                item['bytes'] for item in manifest['output_pins'].values())

        for change in (different_revision, different_recipe, different_source,
                       different_registry):
            with self.subTest(change=change.__name__):
                changed = edit_manifest(self.partial_one, change)
                with self.assertRaisesRegex(ValueError,
                                            'cross-seed historical'):
                    collector.collect_saved_seed_contributions(
                        [self.partial_zero, changed])

        duplicate_root = edit_manifest(
            self.partial_one,
            lambda manifest: manifest.update(root=v.strict_json(
                self.partial_zero['manifest_entries'][0]['raw'])['root']))
        with self.assertRaisesRegex(ValueError, 'unique invented source roots'):
            collector.collect_saved_seed_contributions(
                [self.partial_zero, duplicate_root])

        duplicate_rows = edit_result(
            self.partial_one,
            lambda result: result['source_chunks'][0]['entry_pins'].update(
                rows=v.strict_json(self.partial_zero['result_raw'])
                ['source_chunks'][0]['entry_pins']['rows']))
        with self.assertRaisesRegex(ValueError,
                                    'unique frozen source chunk rows pin'):
            collector.collect_saved_seed_contributions(
                [self.partial_zero, duplicate_rows])

    def test_complete_seed_arithmetic_and_gate_claims_are_rechecked(self):
        complete = collector.collect_saved_seed_contributions(
            [self.complete_zero])
        self.assertEqual(complete['bound_evaluations'], 72)
        self.assertIsNone(complete['unanchored_40_seed_contribution'])

        formal = edit_result(self.complete_zero,
                             lambda result: result.update(formal_permission=True))
        with self.assertRaisesRegex(ValueError, 'closed seed contribution'):
            collector.collect_saved_seed_contributions([formal])

        def wrong_count(result):
            contribution = result['cluster_contribution']
            cell = contribution['cluster']['candidates'][arithmetic.CANDIDATES[0]]
            cell = cell[arithmetic.STRATA[0]]['counts']
            cell['machine_recall'][0] += 1
            cell['precision'][0] += 1
            cell['precision'][1] += 1
            diagnostic = contribution['diagnostic']['candidates'][
                arithmetic.CANDIDATES[0]][arithmetic.STRATA[0]]
            diagnostic['detected_delays'].append(1)

        wrong = edit_result(self.complete_zero, wrong_count)
        with self.assertRaises(ValueError):
            collector.collect_saved_seed_contributions([wrong])

        def wrong_delay(result):
            delays = result['cluster_contribution']['diagnostic'][
                'candidates'][arithmetic.CANDIDATES[0]][
                    arithmetic.STRATA[0]]['detected_delays']
            delays[0] = 5 if delays[0] != 5 else 1

        wrong = edit_result(self.complete_zero, wrong_delay)
        with self.assertRaisesRegex(ValueError,
                                    'seed slice/diagnostic delay histogram'):
            collector.collect_saved_seed_contributions([wrong])

    def test_synthetic_forty_seed_inventory_keeps_formal_fields_closed(self):
        base = v.strict_json(self.complete_zero['result_raw'])
        manifests = [v.strict_json(entry['raw'])
                     for entry in self.complete_zero['manifest_entries']]
        entries = []
        for seed_index in range(40):
            result = copy.deepcopy(base)
            result['registered_seed_index'] = seed_index
            cluster_id = f'invented-{seed_index:02d}'
            result['invented_cluster_id'] = cluster_id
            for item in result['cluster_contribution'].values():
                item['cluster_id'] = cluster_id
            wrapped_manifests = []
            for layout, (chunk, source_manifest) in enumerate(zip(
                    result['source_chunks'], manifests)):
                index = seed_index * 12 + layout
                chunk['chunk_index'] = index
                manifest = copy.deepcopy(source_manifest)
                manifest['chunk_index'] = index
                manifest['root'] = (
                    rf'D:\invented\artifacts\anomaly-v03-preformal-registered-attempt-'
                    f's{seed_index:02d}-l{layout:02d}')
                for name in ('result', 'rows', 'receipt', 'report',
                             'savepoint'):
                    unique = pin(v.canonical_json({
                        'synthetic_chunk_index': index, 'kind': name}))
                    chunk['entry_pins'][name] = unique
                    if name in ('receipt', 'report', 'savepoint'):
                        manifest['output_pins']['saved/' + name + '.json'] = unique
                manifest['output_bytes'] = sum(
                    item['bytes'] for item in manifest['output_pins'].values())
                raw = v.canonical_json(manifest)
                wrapped_manifests.append(raw)
                chunk['entry_pins']['manifest'] = pin(raw)
            entries.append(package(result, wrapped_manifests))
        almost = collector.collect_saved_seed_contributions(entries[:-1])
        self.assertEqual((almost['bound_seeds'], almost['bound_chunks'],
                          almost['bound_evaluations']), (39, 468, 2808))
        self.assertEqual(almost['missing_seed_indices'], [39])
        self.assertIsNone(almost['unanchored_40_seed_contribution'])
        with patch('builtins.open', side_effect=AssertionError('unexpected I/O')):
            result = collector.collect_saved_seed_contributions(entries)
        self.assertEqual(result['status'],
                         'complete_unanchored_contribution_inventory')
        self.assertEqual((result['bound_seeds'], result['bound_chunks'],
                          result['bound_evaluations']), (40, 480, 2880))
        self.assertEqual(result['missing_seed_indices'], [])
        self.assertEqual(result['missing_chunk_indices'], [])
        candidate = result['unanchored_40_seed_contribution']
        self.assertEqual(len(candidate['clusters']), 40)
        self.assertEqual(candidate['clusters'][39]['cluster_id'], 'invented-39')
        self.assertEqual(len(candidate['slice_source']['clusters']), 40)
        machine = arithmetic.CANDIDATES[0]
        core = arithmetic.STRATA[0]
        first = candidate['clusters'][0]['candidates'][machine][core]
        self.assertEqual(sum(item['candidates'][machine][core]['counts']
                             ['machine_recall'][1]
                             for item in candidate['clusters']),
                         40 * first['counts']['machine_recall'][1])
        self.assertEqual(sum(item['candidates'][machine][core]['evaluations']
                             for item in candidate['slice_source']['clusters']),
                         480)
        self.assertIsNone(result['clusters'])
        self.assertIsNone(result['diagnostics'])
        self.assertIsNone(result['slice_source'])
        self.assertFalse(result['formal_permission'])
        self.assertFalse(result['campaign_coherence_authenticated'])
        self.assertFalse(result['historical_producer_execution_authenticated'])


if __name__ == '__main__':
    unittest.main()
