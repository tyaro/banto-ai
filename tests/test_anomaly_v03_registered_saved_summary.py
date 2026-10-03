"""Raw-byte fixture boundary for future registered saved summaries."""
import copy
import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_consumer_input as metadata
from banto_ai import anomaly_v03_registered_saved_summary as bound
from tests.test_anomaly_v03_registered_summary_fixture import SUMMARY
from tests.test_anomaly_v03_producer_slice_fixture import raw_counts


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_RAW = (ROOT / 'examples/configs/anomaly-v03-freeze-registry.json').read_bytes()


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def example():
    registry_pin = pin(REGISTRY_RAW)
    savepoint_pin = pin(b'caller-retained-invented-savepoint')
    identities = v.evaluation_inventory('holdout')[:6]
    payloads = {}
    hashes = {}
    for identity in identities:
        dataset = identity['dataset_id']
        if dataset in hashes:
            continue
        hashes[dataset] = {}
        for kind in metadata.INPUT_HASHES:
            raw = v.canonical_json({'invented': True, 'dataset_id': dataset,
                                    'kind': kind})
            payloads[bound._payload_path(identity, kind)] = raw
            hashes[dataset][kind] = pin(raw)['sha256']
    slots = []
    rows = []
    for identity in identities:
        input_hashes = hashes[identity['dataset_id']]
        evaluation_raw = v.canonical_json({'identity': identity,
                                           'input_hashes': input_hashes,
                                           'invented': True})
        evaluation_path = bound._payload_path(identity)
        payloads[evaluation_path] = evaluation_raw
        slot = {'identity': identity, 'status': 'success',
                'profile_status': 'calibrated', 'input_hashes': input_hashes,
                'evaluation_sha256': pin(evaluation_raw)['sha256']}
        slots.append(slot)
        rows.append({'identity': identity, 'evaluation_outcome': 'success',
                     'evaluation_pin': pin(evaluation_raw),
                     'input_hashes': input_hashes,
                     'primary': {key: copy.deepcopy(SUMMARY[key]) for key in
                                 ('counts', 'effective_clean_seconds', 'delay_histogram')},
                     'slices': raw_counts(SUMMARY)})
    receipt = {'format': bound.RECEIPT_FORMAT, 'mode': bound.MODE,
               'invented_only': True, 'registry_pin': registry_pin,
               'savepoint_pin': savepoint_pin, 'chunk_index': 0,
               'attempts': [{'attempt': 1, 'state': 'complete', 'failure': None,
                             'evaluations': slots}]}
    receipt_raw = v.canonical_json(receipt)
    report = {'format': bound.REPORT_FORMAT, 'mode': bound.MODE,
              'invented_only': True, 'registry_pin': registry_pin,
              'receipt_pin': pin(receipt_raw), 'savepoint_pin': savepoint_pin,
              'chunk_index': 0, 'attempt': 1, 'rows': rows,
              'payload_pins': {name: pin(raw) for name, raw in payloads.items()}}
    return receipt, report, payloads


def call(receipt, report, payloads, **overrides):
    receipt_raw = v.canonical_json(receipt)
    report_raw = v.canonical_json(report) if report is not None else None
    return bound.bind_saved_chunk_candidate(
        REGISTRY_RAW, receipt_raw, report_raw, payloads,
        expected_mode=overrides.get('mode', bound.MODE), chunk_index=0,
        expected_registry_pin=pin(REGISTRY_RAW),
        expected_receipt_pin=overrides.get('receipt_pin', pin(receipt_raw)),
        expected_report_pin=overrides.get('report_pin', pin(report_raw) if report_raw else None),
        expected_savepoint_pin=receipt['savepoint_pin'],
        expected_payload_pins=overrides.get('payload_pins',
                                            {name: pin(raw) for name, raw in payloads.items()}))


class RegisteredSavedSummaryTests(unittest.TestCase):
    def test_one_registered_chunk_binds_supplied_invented_bytes_without_authenticating_origin(self):
        receipt, report, payloads = example()
        with patch('builtins.open', side_effect=AssertionError('unexpected IO')):
            result = call(receipt, report, payloads)
        self.assertEqual(result['status'], 'latest_chunk_saved_bytes_bound')
        self.assertEqual((result['chunk_index'], result['latest_attempt'],
                          result['latest_rows_bound']), (0, 1, 6))
        self.assertEqual(len(result['payload_pins']), 18)
        self.assertEqual(result['scope'], 'supplied-registered-format-raw-byte-fixture')
        self.assertTrue(result['saved_payload_bytes_verified'])
        self.assertTrue(result['external_report_bytes_verified'])
        for name in ('source_savepoint_bytes_verified',
                     'reader_result_provenance_authenticated',
                     'observation_to_summary_recomputed',
                     'actual_worker_exit_authenticated',
                     'registered_observations_read', 'real_saved_chunk_reader_used',
                     'formal_permission', 'analysis_authorized',
                     'independent_s6_complete'):
            self.assertFalse(result[name], name)
        self.assertEqual(result['campaign_evaluations_credited'], 0)
        self.assertIsNone(result['clusters'])

    def test_report_and_payload_pins_must_come_from_caller(self):
        receipt, report, payloads = example()
        original_pins = {name: pin(raw) for name, raw in payloads.items()}
        with self.assertRaisesRegex(ValueError, 'external report pin'):
            call(receipt, report, payloads, report_pin=pin(b'wrong report'))
        name = sorted(payloads)[0]
        changed = copy.deepcopy(report)
        changed['payload_pins'][name] = pin(b'forged payload')
        with self.assertRaisesRegex(ValueError, 'independent saved payload pin'):
            call(receipt, changed, payloads)
        tampered = dict(payloads)
        tampered[name] = b'changed bytes'
        with self.assertRaisesRegex(ValueError, 'independent saved payload pin'):
            call(receipt, report, tampered)
        evaluation_path = bound._payload_path(report['rows'][0]['identity'])
        rewrapped_raw = v.canonical_json({'identity': report['rows'][0]['identity'],
                                          'input_hashes': report['rows'][0]['input_hashes'],
                                          'invented': True, 'changed': True})
        rewrapped_payloads = dict(payloads)
        rewrapped_payloads[evaluation_path] = rewrapped_raw
        rewrapped_receipt = copy.deepcopy(receipt)
        rewrapped_receipt['attempts'][0]['evaluations'][0]['evaluation_sha256'] = pin(rewrapped_raw)['sha256']
        rewrapped_report = copy.deepcopy(report)
        rewrapped_report['receipt_pin'] = pin(v.canonical_json(rewrapped_receipt))
        rewrapped_report['payload_pins'][evaluation_path] = pin(rewrapped_raw)
        rewrapped_report['rows'][0]['evaluation_pin'] = pin(rewrapped_raw)
        with self.assertRaisesRegex(ValueError, 'independent saved payload pin'):
            call(rewrapped_receipt, rewrapped_report, rewrapped_payloads,
                 payload_pins=original_pins)

    def test_missing_byte_and_evaluation_identity_are_rejected(self):
        receipt, report, payloads = example()
        missing = dict(payloads)
        missing.pop(next(iter(missing)))
        with self.assertRaisesRegex(ValueError, 'exact saved payload inventories'):
            call(receipt, report, missing)
        identity = report['rows'][0]['identity']
        path = bound._payload_path(identity)
        wrong = dict(payloads)
        value = v.strict_json(wrong[path])
        value['identity'] = report['rows'][1]['identity']
        wrong[path] = v.canonical_json(value)
        changed = copy.deepcopy(report)
        changed['payload_pins'][path] = pin(wrong[path])
        changed['rows'][0]['evaluation_pin'] = pin(wrong[path])
        changed_receipt = copy.deepcopy(receipt)
        changed_receipt['attempts'][0]['evaluations'][0]['evaluation_sha256'] = pin(wrong[path])['sha256']
        changed['receipt_pin'] = pin(v.canonical_json(changed_receipt))
        with self.assertRaisesRegex(ValueError, 'saved evaluation payload identity'):
            call(changed_receipt, changed, wrong)

    def test_saved_evaluation_payload_requires_explicit_identity_and_hash_fields(self):
        receipt, report, payloads = example()
        identity = report['rows'][0]['identity']
        path = bound._payload_path(identity)
        for malformed in ([], {'identity': identity}):
            with self.subTest(malformed=type(malformed).__name__):
                raw = v.canonical_json(malformed)
                altered_payloads = dict(payloads)
                altered_payloads[path] = raw
                altered_receipt = copy.deepcopy(receipt)
                altered_receipt['attempts'][0]['evaluations'][0]['evaluation_sha256'] = pin(raw)['sha256']
                altered_report = copy.deepcopy(report)
                altered_report['receipt_pin'] = pin(v.canonical_json(altered_receipt))
                altered_report['payload_pins'][path] = pin(raw)
                altered_report['rows'][0]['evaluation_pin'] = pin(raw)
                with self.assertRaisesRegex(ValueError, 'saved evaluation payload fields'):
                    call(altered_receipt, altered_report, altered_payloads)

    def test_latest_attempt_selected_and_failed_attempt_never_falls_back(self):
        receipt, report, payloads = example()
        failed = copy.deepcopy(receipt['attempts'][0])
        failed['state'] = 'failed'
        failed['failure'] = {'stage': 'supervision', 'reason': 'worker_exit',
                             'evidence_sha256': None}
        failed['evaluations'][-1].update(status='partial',
                                        profile_status='not_evaluated',
                                        evaluation_sha256=None)
        receipt['attempts'] = [failed, copy.deepcopy(receipt['attempts'][0])]
        receipt['attempts'][1]['attempt'] = 2
        report['attempt'] = 2
        report['receipt_pin'] = pin(v.canonical_json(receipt))
        self.assertEqual(call(receipt, report, payloads)['failed_attempts'], 1)
        old = copy.deepcopy(report)
        old['attempt'] = 1
        with self.assertRaisesRegex(ValueError, 'report binding attempt'):
            call(receipt, old, payloads)
        receipt['attempts'][1]['state'] = 'failed'
        receipt['attempts'][1]['failure'] = failed['failure']
        for slot in receipt['attempts'][1]['evaluations']:
            slot.update(status='not_started', profile_status='not_evaluated',
                        input_hashes=None, evaluation_sha256=None)
        with self.assertRaisesRegex(ValueError, 'no latest result may consume'):
            call(receipt, report, payloads)
        empty = call(receipt, None, {})
        self.assertEqual(empty['status'], 'no_latest_saved_rows')
        self.assertEqual(empty['latest_attempt'], 2)
        self.assertEqual(empty['latest_rows_bound'], 0)

    def test_failed_latest_attempt_with_five_results_remains_partial(self):
        receipt, report, payloads = example()
        latest = receipt['attempts'][0]
        latest['state'] = 'failed'
        latest['failure'] = {'stage': 'supervision', 'reason': 'worker_exit',
                             'evidence_sha256': None}
        latest['evaluations'][-1].update(status='partial',
                                        profile_status='not_evaluated',
                                        evaluation_sha256=None)
        last = report['rows'].pop()
        evaluation_path = bound._payload_path(last['identity'])
        payloads.pop(evaluation_path)
        report['payload_pins'].pop(evaluation_path)
        report['receipt_pin'] = pin(v.canonical_json(receipt))
        result = call(receipt, report, payloads)
        self.assertEqual(result['status'], 'latest_chunk_saved_bytes_partial')
        self.assertEqual(result['latest_rows_bound'], 5)
        self.assertIsNone(result['clusters'])
        with self.assertRaisesRegex(ValueError, 'exact latest saved summary rows'):
            altered = copy.deepcopy(report)
            altered['rows'].pop()
            call(receipt, altered, payloads)

    def test_dev_smoke_report_and_formal_mode_are_closed(self):
        receipt, report, payloads = example()
        report['format'] = 'anomaly-v03-saved-chunk-summary-v1'
        with self.assertRaisesRegex(ValueError, 'report binding format'):
            call(receipt, report, payloads)
        with self.assertRaisesRegex(ValueError, 'formal/unknown registered saved mode is closed'):
            bound.bind_saved_chunk_candidate(b'?', b'?', b'?', {},
                expected_mode='formal', chunk_index=0, expected_registry_pin=None,
                expected_receipt_pin=None, expected_report_pin=None,
                expected_savepoint_pin=None, expected_payload_pins={})


if __name__ == '__main__':
    unittest.main()
