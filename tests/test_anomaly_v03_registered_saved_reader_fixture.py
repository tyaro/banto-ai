"""Read actual invented saved files through the registered byte boundary."""
from __future__ import annotations

import copy
import os
from pathlib import Path
import tempfile
import unittest

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_registered_saved_reader_fixture as reader
from banto_ai import anomaly_v03_registered_saved_summary as saved
from tests.test_anomaly_v03_registered_saved_summary import REGISTRY_RAW, example, pin
from tests.test_anomaly_v03_registered_completed_contract_fixture import invented_completed_chunk


def write_case(root, receipt, report, payloads):
    (root / 'registry.json').write_bytes(REGISTRY_RAW)
    receipt_raw = v.canonical_json(receipt)
    (root / 'receipt.json').write_bytes(receipt_raw)
    report_raw = v.canonical_json(report) if report is not None else None
    if report_raw is not None:
        (root / 'report.json').write_bytes(report_raw)
    for name, raw in payloads.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return receipt_raw, report_raw


def call(root, receipt, report, payloads, **changes):
    receipt_raw = v.canonical_json(receipt)
    report_raw = v.canonical_json(report) if report is not None else None
    return reader.read_saved_chunk_fixture(
        root, expected_mode=changes.get('mode', saved.MODE), chunk_index=0,
        expected_registry_pin=pin(REGISTRY_RAW),
        expected_receipt_pin=changes.get('receipt_pin', pin(receipt_raw)),
        expected_report_pin=changes.get('report_pin', pin(report_raw) if report_raw else None),
        expected_savepoint_pin=receipt['savepoint_pin'],
        expected_payload_pins=changes.get('payload_pins',
                                          {name: pin(raw) for name, raw in payloads.items()}))


class RegisteredSavedReaderFixtureTests(unittest.TestCase):
    def test_reads_fixed_invented_files_and_keeps_formal_closed(self):
        receipt, report, payloads = example()
        with tempfile.TemporaryDirectory(prefix='banto-registered-read-') as temporary:
            root = Path(temporary)
            write_case(root, receipt, report, payloads)
            value = call(root, receipt, report, payloads)
        self.assertEqual(value['format'], reader.FORMAT)
        self.assertEqual(value['status'], 'latest_chunk_saved_bytes_bound')
        self.assertEqual(value['fixture_files_read'], 21)
        self.assertTrue(value['fixture_saved_files_read'])
        self.assertEqual(value['fixture_physical_layout'], 'invented-receipt-key-layout')
        self.assertEqual(value['scope'], 'read-only-caller-pinned-invented-saved-files')
        self.assertEqual(value['campaign_evaluations_credited'], 0)
        for key in ('registered_observations_read', 'real_saved_chunk_reader_used',
                    'source_savepoint_bytes_verified', 'actual_worker_exit_authenticated',
                    'formal_permission', 'analysis_authorized', 'independent_s6_complete'):
            self.assertFalse(value[key], key)

    def test_mutated_saved_evaluation_bytes_are_rejected(self):
        receipt, report, payloads = example()
        with tempfile.TemporaryDirectory(prefix='banto-registered-read-') as temporary:
            root = Path(temporary)
            write_case(root, receipt, report, payloads)
            path = root / saved._payload_path(report['rows'][0]['identity'])
            path.write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError, 'pinned file'):
                call(root, receipt, report, payloads)

    def test_receipt_mutation_and_multiply_linked_payload_are_rejected(self):
        receipt, report, payloads = example()
        with tempfile.TemporaryDirectory(prefix='banto-registered-read-') as temporary:
            root = Path(temporary)
            write_case(root, receipt, report, payloads)
            (root / 'receipt.json').write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError, 'pinned file'):
                call(root, receipt, report, payloads)
            (root / 'receipt.json').write_bytes(v.canonical_json(receipt))
            path = root / saved._payload_path(report['rows'][0]['identity'])
            os.link(path, root / 'second-link.json')
            with self.assertRaisesRegex(ValueError, 'multiply-linked'):
                call(root, receipt, report, payloads)

    def test_extra_caller_path_is_rejected_before_it_can_be_read(self):
        receipt, report, payloads = example()
        with tempfile.TemporaryDirectory(prefix='banto-registered-read-') as temporary:
            root = Path(temporary)
            write_case(root, receipt, report, payloads)
            pins = {name: pin(raw) for name, raw in payloads.items()}
            pins['../unexpected.json'] = pin(b'invented')
            with self.assertRaisesRegex(ValueError, 'exact derived path inventory'):
                call(root, receipt, report, payloads, payload_pins=pins)

    def test_no_latest_attempt_reads_no_report_or_payload(self):
        receipt, _, _ = example()
        receipt = copy.deepcopy(receipt)
        receipt['attempts'] = []
        with tempfile.TemporaryDirectory(prefix='banto-registered-read-') as temporary:
            root = Path(temporary)
            write_case(root, receipt, None, {})
            value = call(root, receipt, None, {})
        self.assertEqual(value['status'], 'no_latest_saved_rows')
        self.assertEqual(value['fixture_files_read'], 2)
        self.assertEqual(value['latest_rows_bound'], 0)

    def test_failed_latest_does_not_read_stale_prior_saved_files(self):
        receipt, report, payloads = example()
        failure = {'stage': 'supervision', 'reason': 'worker_exit',
                   'evidence_sha256': None}
        first = receipt['attempts'][0]
        first['state'] = 'failed'
        first['failure'] = failure
        first['evaluations'][-1].update(status='partial',
                                        profile_status='not_evaluated',
                                        evaluation_sha256=None)
        latest = copy.deepcopy(first)
        latest['attempt'] = 2
        for slot in latest['evaluations']:
            slot.update(status='not_started', profile_status='not_evaluated',
                        input_hashes=None, evaluation_sha256=None)
        receipt['attempts'].append(latest)
        with tempfile.TemporaryDirectory(prefix='banto-registered-read-') as temporary:
            root = Path(temporary)
            write_case(root, receipt, report, payloads)
            # The earlier report and payload are deliberately left on disk.
            value = call(root, receipt, None, {})
        self.assertEqual(value['status'], 'no_latest_saved_rows')
        self.assertEqual(value['latest_attempt'], 2)
        self.assertEqual(value['fixture_files_read'], 2)

    def test_invented_completed_six_slot_files_are_read_and_semantically_checked(self):
        registry_raw, receipt_raw, report_raw, payloads, expected = invented_completed_chunk()
        self.assertEqual(registry_raw, REGISTRY_RAW)
        with tempfile.TemporaryDirectory(prefix='banto-registered-read-') as temporary:
            root = Path(temporary)
            write_case(root, v.strict_json(receipt_raw), v.strict_json(report_raw), payloads)
            value = reader.read_saved_chunk_fixture(root, **expected)
        self.assertEqual(value['status'], 'latest_chunk_saved_bytes_bound')
        self.assertTrue(value['fixture_saved_files_read'])
        self.assertTrue(value['fixture_semantic_contract_checked'])
        self.assertEqual(value['registered_evaluation_contracts_checked'], 6)
        self.assertEqual(value['fixture_files_read'], 21)
        self.assertFalse(value['observation_to_score_recomputed'])
        self.assertFalse(value['real_saved_chunk_reader_used'])
        self.assertEqual(value['campaign_evaluations_credited'], 0)

    def test_formal_and_noninvented_receipts_stop_before_payload_read(self):
        receipt, report, payloads = example()
        with tempfile.TemporaryDirectory(prefix='banto-registered-read-') as temporary:
            root = Path(temporary)
            write_case(root, receipt, report, payloads)
            with self.assertRaisesRegex(ValueError, 'formal/unknown saved reader mode'):
                call(root, receipt, report, payloads, mode='formal')
            altered = copy.deepcopy(receipt)
            altered['invented_only'] = False
            write_case(root, altered, report, payloads)
            with self.assertRaisesRegex(ValueError, 'only invented registered saved fixture'):
                call(root, altered, report, payloads)


if __name__ == '__main__':
    unittest.main()
