"""Pure mapping of saved-shaped invented 50,000-draw primary tables.

The one-draw unit fixture below only exercises the mapping contract. A saved
bridge result and independent arithmetic audit must supply real 50,000-draw
evidence before a caller uses the mapper on an actual retained attempt.
"""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_analysis_adapter as adapter
from banto_ai import _anomaly_v03_contract as frozen
from tests.test_anomaly_v03_document_fixture import invented_input


SCHEMA = json.loads((Path(__file__).parents[1] /
                     'schemas/anomaly-multiseed-analysis-result-v0.3.schema.json').read_text(
                         encoding='utf-8'))


def saved_shaped():
    fixture = invented_input(ready=False)
    clusters, diagnostics = fixture['clusters'], fixture['diagnostics']
    calculation = adapter.inference.compute_fixture_tables(
        clusters, [list(range(40))], engineering_ready=False)
    calculation['replicate_count'] = 50000
    return clusters, diagnostics, calculation


class PrecomputedDocumentPacketTests(unittest.TestCase):
    def test_maps_all_tables_without_generating_draws_or_intervals(self):
        clusters, diagnostics, calculation = saved_shaped()
        before = copy.deepcopy((clusters, diagnostics, calculation))
        with patch.object(adapter.inference, 'compute_fixture_tables',
                          side_effect=AssertionError('draw calculation')), \
             patch.object(frozen, 'bootstrap_indices',
                          side_effect=AssertionError('draw materialization')):
            packet = adapter.map_precomputed_fixture_packet(
                clusters, diagnostics, SCHEMA, calculation,
                draw_sha256=frozen.BOOTSTRAP_HASH)
        self.assertEqual((clusters, diagnostics, calculation), before)
        self.assertEqual(packet['fixture_draws'], {'clusters': 40, 'replicates': 50000})
        self.assertEqual(len(packet['fixture_candidate_tables']), 9)
        self.assertEqual(sum(len(row['gates']) for row in packet['fixture_candidate_tables']), 180)
        self.assertEqual(packet['validation']['status'], 'fixture_table_contract_valid')
        for mapped, source in zip(packet['fixture_candidate_tables'],
                                  calculation['candidate_tables']):
            self.assertEqual(mapped['gates'], source['gates'])
            self.assertEqual(mapped['metrics']['machine_recall'],
                             source['metrics']['machine_recall'])
        self.assertIsNone(packet['selected_candidate'])
        self.assertFalse(packet['formal_document_emitted'])
        self.assertFalse(packet['independent_s6_complete'])

    def test_wrong_digest_dimensions_and_elevated_claims_fail(self):
        clusters, diagnostics, calculation = saved_shaped()
        cases = [
            (lambda c: c.update(replicate_count=49999), frozen.BOOTSTRAP_HASH),
            (lambda c: c.update(cluster_count=39), frozen.BOOTSTRAP_HASH),
            (lambda c: c.update(formal_permission=True), frozen.BOOTSTRAP_HASH),
            (lambda c: c.update(campaign_evaluations_credited=1), frozen.BOOTSTRAP_HASH),
            (lambda c: c.update(extra=True), frozen.BOOTSTRAP_HASH),
            (lambda c: None, '0' * 64),
        ]
        for mutate, digest in cases:
            attempt = copy.deepcopy(calculation)
            mutate(attempt)
            with self.subTest(mutate=mutate, digest=digest), self.assertRaises(ValueError):
                adapter.map_precomputed_fixture_packet(
                    clusters, diagnostics, SCHEMA, attempt, draw_sha256=digest)

    def test_input_counts_points_profiles_and_gates_are_bound(self):
        clusters, diagnostics, calculation = saved_shaped()
        attempts = []
        changed = copy.deepcopy(calculation)
        changed['candidate_tables'][0]['metrics']['machine_recall']['numerator'] += 1
        attempts.append(changed)
        changed = copy.deepcopy(calculation)
        changed['candidate_tables'][0]['metrics']['machine_recall']['value'] = 0
        attempts.append(changed)
        changed = copy.deepcopy(calculation)
        changed['candidate_tables'][0]['profile_status'] = 'inconclusive'
        attempts.append(changed)
        changed = copy.deepcopy(calculation)
        changed['candidate_tables'][3]['paired_control']['machine_recall']['value'] = 0
        attempts.append(changed)
        changed = copy.deepcopy(calculation)
        changed['candidate_tables'][3]['gates'][0]['status'] = 'fail'
        attempts.append(changed)
        for attempt in attempts:
            with self.subTest(attempt=attempt), self.assertRaises(ValueError):
                adapter.map_precomputed_fixture_packet(
                    clusters, diagnostics, SCHEMA, attempt,
                    draw_sha256=frozen.BOOTSTRAP_HASH)

    def test_cluster_identity_diagnostic_and_layout_fail_closed(self):
        clusters, diagnostics, calculation = saved_shaped()
        altered = copy.deepcopy(clusters)
        altered[0]['cluster_id'] = 'holdout-00'
        with self.assertRaises(ValueError):
            adapter.map_precomputed_fixture_packet(
                altered, diagnostics, SCHEMA, calculation,
                draw_sha256=frozen.BOOTSTRAP_HASH)
        altered = copy.deepcopy(clusters)
        altered[0]['candidates'][adapter.inference.CANDIDATES[0]]['core'][
            'counts']['machine_recall'][1] = 119
        with self.assertRaises(ValueError):
            adapter.map_precomputed_fixture_packet(
                altered, diagnostics, SCHEMA, calculation,
                draw_sha256=frozen.BOOTSTRAP_HASH)
        altered_diagnostics = copy.deepcopy(diagnostics)
        altered_diagnostics[0]['candidates'][adapter.inference.CANDIDATES[0]][
            'core']['detected_delays'].pop()
        with self.assertRaises(ValueError):
            adapter.map_precomputed_fixture_packet(
                clusters, altered_diagnostics, SCHEMA, calculation,
                draw_sha256=frozen.BOOTSTRAP_HASH)


if __name__ == '__main__':
    unittest.main()
