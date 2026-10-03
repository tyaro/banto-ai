"""Saved invented 50,000-draw document -> bounded slice draft tests.

Retained native artifacts are optional in a source-only checkout. No registered
observation is generated or read, and the existing saved attempts stay intact.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_preformal_bound_slice_bridge as bridge


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / 'artifacts/anomaly-v03-preformal-bound-document-bridge/trial-01-saved-50000-document'
PRODUCER = ROOT / 'artifacts/anomaly-v03-preformal-five-role-26h2/trial-16-two-role-enforced/producer'
DOCUMENT_RESULT_PIN = {
    'bytes': 6001,
    'sha256': '11a2c209c1252a53d9af0ba1ab10ca9a5754729f23c49b4525c09e0b0c15aa03',
}
SLICE_SOURCE_PIN = {
    'bytes': 4336841,
    'sha256': 'c777c2b4b9c513136fd8fbb2a7c030120dc076d00a630be8661c0ee7a50c8f2d',
}
HAVE_RETAINED = all(path.is_file() for path in (
    DOCUMENT / 'result.json', DOCUMENT / 'document.json', PRODUCER / 'result.json',
    PRODUCER / 'output/projection/fixture/slices.json',
))


def _head():
    return subprocess.check_output(
        ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'],
        stderr=subprocess.DEVNULL,
    ).decode().strip()


def _pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


@unittest.skipUnless(HAVE_RETAINED, 'retained invented document/slice fixture absent')
class SavedSliceBridgeTests(unittest.TestCase):
    def _run(self, parent, name, *, document_pin=DOCUMENT_RESULT_PIN,
             slice_pin=SLICE_SOURCE_PIN):
        with (patch.object(bridge, 'OUTPUT_PARENT', parent),
              patch.object(bridge, '_source_pins', return_value={'selected': DOCUMENT_RESULT_PIN})):
            return bridge.run_saved_slices(
                document_root=DOCUMENT,
                expected_document_result_pin=document_pin,
                expected_slice_source_pin=slice_pin,
                expected_revision=_head(),
                trial_name=name,
            )

    def test_external_document_and_slice_pins_reject_before_creating_trial(self):
        wrong_document = {**DOCUMENT_RESULT_PIN, 'sha256': '0' * 64}
        wrong_slice = {**SLICE_SOURCE_PIN, 'sha256': '0' * 64}
        with tempfile.TemporaryDirectory(prefix='slice-bridge-test-', dir=ROOT / 'artifacts') as path:
            parent = Path(path) / 'out'
            for label, document_pin, slice_pin in (
                    ('document', wrong_document, SLICE_SOURCE_PIN),
                    ('slice', DOCUMENT_RESULT_PIN, wrong_slice)):
                with self.subTest(label=label), self.assertRaises(ValueError):
                    self._run(parent, 'trial-rejected-' + label,
                              document_pin=document_pin, slice_pin=slice_pin)
                self.assertFalse(parent.exists(), 'bad externally retained pin created a trial root')

    def test_slice_draft_preserves_primary_tables_and_formal_closure(self):
        with tempfile.TemporaryDirectory(prefix='slice-bridge-test-', dir=ROOT / 'artifacts') as path:
            parent = Path(path) / 'out'
            result = self._run(parent, 'trial-invented-slices')
            target = parent / 'trial-invented-slices'
            saved_result = json.loads((target / 'result.json').read_bytes())
            slices = json.loads((target / 'slices.json').read_bytes())
            audit = json.loads((target / 'audit.json').read_bytes())
            original = json.loads((DOCUMENT / 'document.json').read_bytes())

            self.assertEqual(saved_result['status'], 'verified')
            self.assertEqual(result['status'], 'verified')
            self.assertEqual(slices['document_draft']['candidate_tables'],
                             original['document_draft']['candidate_tables'])
            self.assertEqual(len(slices['document_draft']['candidate_tables']), 9)
            self.assertEqual(len(slices['document_draft']['slices']), 1233)
            self.assertEqual(sum(map(len, slices['diagnostic_series'].values())), 2835)
            self.assertEqual(len(slices['diagnostic_details']), 9)
            self.assertEqual(slices['numeric_draw_contract']['replicates'], 50000)
            self.assertEqual(slices['formal_requirements']['missing_fields'],
                             ['status', 'provenance', 'analysis_consumer', 'bootstrap'])
            self.assertFalse(slices['formal_requirements']['ready'])
            for field in ('status', 'provenance', 'analysis_consumer', 'bootstrap'):
                self.assertIsNone(slices['document_draft'][field])
            for value in (saved_result, slices):
                for field in ('registered_data_read', 'formal_document_emitted',
                              'formal_document_validated', 'formal_permission',
                              'promotion_allowed', 'independent_s6_complete',
                              'publication_performed', 'same_run_arithmetic_performed',
                              'current_document_outer_budget_measured',
                              'full_end_to_end_budget_measured',
                              'formal_50000_draw_budget_measured'):
                    self.assertIs(value[field], False, field)
                self.assertEqual(value['campaign_evaluations_credited'], 0)
            self.assertFalse(audit['independent_s6_complete'])
            self.assertEqual(_pin((target / 'slices.json').read_bytes()),
                             saved_result['slices_pin'])
            self.assertEqual(_pin((target / 'audit.json').read_bytes()),
                             saved_result['audit_pin'])
            self.assertEqual(_pin((target / 'result.json').read_bytes()),
                             result['result_pin'])

            with self.assertRaises((FileExistsError, ValueError)):
                self._run(parent, 'trial-invented-slices')


if __name__ == '__main__':
    unittest.main()
