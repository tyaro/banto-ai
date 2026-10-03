"""Saved invented arithmetic -> fixture-draft boundary tests.

The positive native fixture is conditional because retained artifacts are not
part of a source checkout.  No registered observation is read or generated.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_preformal_bound_document_bridge as mapping


ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / 'artifacts/anomaly-v03-preformal-bound-draw-bridge/trial-03-two-role-final-50000'
TOP_PIN = {'bytes': 6417,
           'sha256': '2a932142900222f072e4568488f9a55cb79b669700c86201eeceab26d0027c92'}
HAVE_RETAINED = (BRIDGE / 'result.json').is_file() and (
    ROOT / 'artifacts/anomaly-v03-preformal-five-role-26h2/trial-16-two-role-enforced/producer/result.json').is_file()


@unittest.skipUnless(HAVE_RETAINED, 'retained invented arithmetic fixture absent')
class SavedDocumentBridgeTests(unittest.TestCase):
    def test_saved_pins_and_draft_are_bound_without_arithmetic_replay(self):
        saved = mapping.verify_saved_bridge(BRIDGE, TOP_PIN)
        self.assertEqual(saved['audit']['calculation_sha256'],
                         saved['result']['calculation_pin']['sha256'])
        self.assertEqual(len(saved['producer_input']['draws']), 1)
        saved['external_result_pin'] = TOP_PIN
        schema = mapping.formal_contract.schemas(mapping.formal_contract._expected_configs())[7]
        with (patch.object(mapping.adapter, 'compute_fixture_packet',
                           side_effect=AssertionError('packet recomputation forbidden')),
              patch.object(mapping.adapter.inference, 'compute_fixture_tables',
                           side_effect=AssertionError('arithmetic replay forbidden'))):
            packet = mapping.adapter.map_precomputed_fixture_packet(
                saved['bridge_input']['clusters'], saved['producer_input']['diagnostics'],
                schema, saved['calculation'], draw_sha256=saved['audit']['draw_sha256'])
            value = mapping._fixture_document(saved, packet)
        self.assertEqual(value['numeric_draw_contract']['replicates'], 50000)
        self.assertEqual(value['legacy_projection_draws'], 1)
        self.assertEqual(len(value['document_draft']), 10)
        self.assertEqual(len(value['document_draft']['candidate_tables']), 9)
        self.assertTrue(all(value['document_draft'][name] is None
                            for name in mapping.document.PENDING))
        self.assertFalse(value['same_run_arithmetic_performed'])
        self.assertFalse(value['formal_document_emitted'])
        self.assertFalse(value['publication_performed'])

    def test_wrong_external_top_pin_rejects_before_new_root(self):
        wrong = {**TOP_PIN, 'sha256': '0' * 64}
        with tempfile.TemporaryDirectory(prefix='document-bridge-test-', dir=ROOT / 'artifacts') as path:
            parent = Path(path) / 'out'
            with patch.object(mapping, 'OUTPUT_PARENT', parent):
                with self.assertRaisesRegex(ValueError, 'pin differs'):
                    mapping.run_saved_document(
                        bridge_root=BRIDGE, expected_bridge_result_pin=wrong,
                        expected_revision='0' * 40, trial_name='trial-rejected')
            self.assertFalse(parent.exists())

    def test_run_selects_formal_schema_but_retains_fixture_draft(self):
        revision = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'],
                                           stderr=subprocess.DEVNULL).decode().strip()
        with tempfile.TemporaryDirectory(prefix='document-bridge-test-', dir=ROOT / 'artifacts') as path:
            parent = Path(path) / 'out'
            with (patch.object(mapping, 'OUTPUT_PARENT', parent),
                  patch.object(mapping, '_source_pins', return_value={'test': TOP_PIN}),
                  patch.object(mapping.platform_runtime, 'probe_runtime', return_value={'test': 'runtime'})):
                result = mapping.run_saved_document(
                    bridge_root=BRIDGE, expected_bridge_result_pin=TOP_PIN,
                    expected_revision=revision, trial_name='trial-saved-map')
            target = Path(result['receipt_root'])
            retained = json.loads((target / 'document.json').read_bytes())
            self.assertEqual(retained['document_draft']['status'], None)
            self.assertEqual(retained['formal_requirements']['ready'], False)
            self.assertEqual(retained['fixture_packet']['fixture_draws']['replicates'], 50000)
            self.assertEqual(result['wall_scope'], 'saved_pin_verification_plus_fixture_draft_mapping')
            self.assertFalse(result['current_document_outer_budget_measured'])
            self.assertEqual(mapping.bounded._pin((target / 'document.json').read_bytes()),
                             result['document_pin'])
            self.assertEqual(mapping.bounded._pin((target / 'result.json').read_bytes()),
                             result['result_pin'])
            with (patch.object(mapping, 'OUTPUT_PARENT', parent),
                  patch.object(mapping, '_source_pins', return_value={'test': TOP_PIN}),
                  patch.object(mapping.platform_runtime, 'probe_runtime', return_value={'test': 'runtime'})):
                with self.assertRaises((FileExistsError, ValueError)):
                    mapping.run_saved_document(
                        bridge_root=BRIDGE, expected_bridge_result_pin=TOP_PIN,
                        expected_revision=revision, trial_name='trial-saved-map')


if __name__ == '__main__':
    unittest.main()
