"""Invented saved-primary slice mapping; no draw or registered-data IO."""
import copy
import json
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_slice_fixture as slices
from tests import test_anomaly_v03_document_fixture as document_hand
from tests import test_anomaly_v03_slice_fixture as slice_hand


class PrecomputedSliceFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.primary = document_hand.invented_input()
        legacy = slices.document.build_fixture_document(cls.primary, document_hand.SCHEMA)
        cls.packet = copy.deepcopy(legacy['fixture_packet'])
        cls.packet['fixture_draws']['replicates'] = 50000
        cls.source = slice_hand.invented_slices(cls.primary)
        cls.legacy_rows = slices.attach_fixture_slices(
            legacy, cls.primary, cls.source, document_hand.SCHEMA)

    def derive(self, *, primary=None, packet=None, source=None, schema=None):
        primary = self.primary if primary is None else primary
        return slices.derive_precomputed_slices(
            primary['clusters'], primary['diagnostics'],
            self.packet if packet is None else packet,
            self.source if source is None else source,
            document_hand.SCHEMA if schema is None else schema)

    def test_same_rows_without_legacy_draws_or_recomputation(self):
        before = slices.document.contract.canonical_sha256(
            [self.primary, self.packet, self.source])
        with (patch.object(slices.document, '_input',
                           side_effect=AssertionError('legacy one-draw input')),
              patch.object(slices.I, 'compute_fixture_tables',
                           side_effect=AssertionError('draw replay'))):
            mapped = self.derive()
        for name, legacy_name in (('slices', 'slices'),
                                  ('diagnostic_series', 'diagnostic_series'),
                                  ('diagnostic_details', 'diagnostic_details'),
                                  ('slice_input_canonical_sha256', 'slice_input_canonical_sha256')):
            expected = (self.legacy_rows['document_draft']['slices'] if legacy_name == 'slices'
                        else self.legacy_rows[legacy_name])
            self.assertEqual(mapped[name], expected)
        self.assertEqual(set(mapped), {'slices', 'diagnostic_series',
                                      'diagnostic_details', 'slice_input_canonical_sha256'})
        self.assertEqual(len(mapped['slices']), 1233)
        self.assertEqual(sum(map(len, mapped['diagnostic_series'].values())), 2835)
        self.assertEqual(len(mapped['diagnostic_details']), 9)
        mapped['slices'][0]['metric']['value'] = 0
        self.assertEqual(slices.document.contract.canonical_sha256(
            [self.primary, self.packet, self.source]), before)

    def test_rejects_wrong_draw_dimensions_and_open_formal_flags(self):
        for mutate in (
            lambda p: p['fixture_draws'].update(replicates=1),
            lambda p: p['fixture_draws'].update(replicates=True),
            lambda p: p['fixture_draws'].update(clusters=39),
            lambda p: p.update(formal_permission=True),
            lambda p: p['fixture_candidate_tables'].pop(),
        ):
            packet = copy.deepcopy(self.packet)
            mutate(packet)
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                self.derive(packet=packet)

    def test_canonical_source_key_order_does_not_change_slice_rows(self):
        canonical = json.loads(slices.document.contract.canonical_json(self.source))
        self.assertEqual(self.derive(source=canonical), self.derive())

    def test_rejects_changed_cluster_count_delay_profile_and_joint_partition(self):
        changes = (
            lambda p, s: p['clusters'][0]['candidates']['c1-phase-level']['core']['counts']['machine_recall'].__setitem__(0, 0),
            lambda p, s: p['diagnostics'][0]['candidates']['c1-phase-level']['core']['detected_delays'].pop(),
            lambda p, s: s['clusters'][0]['candidates']['c1-phase-level']['core'].update(profile_inconclusive_evaluations=12),
            lambda p, s: s['clusters'][0]['candidates']['c1-phase-level']['core']['incident_slices']['class-equipment-mode']['machine.motor-01.stopped'].update(detected=999),
        )
        for mutate in changes:
            primary, source = copy.deepcopy(self.primary), copy.deepcopy(self.source)
            mutate(primary, source)
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                self.derive(primary=primary, source=source)

    def test_rejects_pooled_table_or_slice_source_change(self):
        packet = copy.deepcopy(self.packet)
        packet['fixture_candidate_tables'][0]['metrics']['machine_recall']['numerator'] += 1
        with self.assertRaises(ValueError):
            self.derive(packet=packet)
        source = copy.deepcopy(self.source)
        source['clusters'][0]['cluster_id'] = 'invented-01'
        with self.assertRaises(ValueError):
            self.derive(source=source)
        schema = copy.deepcopy(document_hand.SCHEMA)
        schema['properties']['slices']['minItems'] = 1
        with self.assertRaises(ValueError):
            self.derive(schema=schema)


if __name__ == '__main__':
    unittest.main()
