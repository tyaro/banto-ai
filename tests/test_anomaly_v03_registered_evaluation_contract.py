"""Registered contract checks on hand-written, invented no-run bytes."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import unittest

from banto_ai import anomaly_v03 as v
from banto_ai import _anomaly_v03_contract as frozen
from banto_ai import anomaly_v03_registered_evaluation_contract as contract
from tests.test_anomaly_v03_registered_saved_summary import example, call
from tests.test_anomaly_v03_registered_summary_fixture import SUMMARY


def _source():
    raw = b'# invented schema specimen source\n'
    revision = 'f' * 40
    descriptor = {'revision': revision, 'sources': [{
        'path': 'src/invented-specimen.py', 'raw_sha256': hashlib.sha256(raw).hexdigest(),
        'byte_count': len(raw)}]}
    return revision, descriptor


def _no_run():
    identity = v.evaluation_inventory('holdout')[0]
    revision, source = _source()
    events = v.event_inventory(identity)
    positives = [e for e in events if e['event_class'] in ('machine', 'sensor')]
    incidents = [{'dataset_id': identity['dataset_id'], 'event_id': e['event_id'],
                  'status': 'not_processed', 'candidate_count': 0,
                  'candidate_episode_ids': [], 'selected_candidate_episode_id': None,
                  'selected_source_episode_id': None, 'support_score_ids': [],
                  'reason': 'not_processed', 'matched_episode_id': None,
                  'causal_detected': None, 'delay_seconds': None,
                  'secondary_canonical_detected': None} for e in positives]
    hashes = {name: 'a' * 64 for name in
              ('observations', 'events', 'quality_mask', 'split', 'origins', 'targets')}
    value = {'schema_version': '0.3', 'result_type': 'event-aware-anomaly-v03',
             'identity': identity, 'input_hashes': hashes,
             'status': {'run_status': 'not_run', 'engineering_status': 'not_evaluated',
                        'performance_status': 'not_evaluated'},
             'provenance': {'science_revision': frozen.SCIENCE_REVISION,
                            'post_audit_revision': frozen.STATUS_REVISION,
                            'producer_revision': revision, 'producer_source': source,
                            'registry_raw_sha256': v.REGISTRY_RAW_SHA256,
                            'inventory': [{'path': 'invented/specimen.json',
                                           'raw_sha256': 'a' * 64,
                                           'canonical_sha256': 'b' * 64,
                                           'row_count': 0}]},
             'splits': {'warmup': [0, 1800], 'fit': [1800, 5400],
                        'calibration': [5400, 7200], 'test': [7200, 9000]},
             'events': events, 'profiles': [], 'scores': [], 'source_episodes': [],
             'equipment_episodes': [], 'incidents': incidents,
             'metrics': None, 'slices': [],
             'row_counts': {'events': 40, 'profiles': 0, 'scores': 0,
                            'source_episodes': 0, 'equipment_episodes': 0,
                            'incidents': 20}}
    return value


class RegisteredEvaluationContractTests(unittest.TestCase):
    def check(self, value, *, outcome='not_started'):
        raw = v.canonical_json(value)
        return contract.check_evaluation_contract_bytes(
            raw, identity=value['identity'], input_hashes=value['input_hashes'],
            outcome=outcome)

    def test_hand_written_holdout_no_run_schema_is_valid_but_closed(self):
        value = _no_run()
        checked = self.check(value)
        self.assertEqual(checked['contract']['validation_status'], 'result_contract_valid')
        self.assertIsNone(checked['ledger'])
        self.assertEqual(checked['value']['identity']['role'], 'holdout')

    def test_complete_claim_cannot_be_inferred_from_no_run_contract(self):
        value = _no_run()
        with self.assertRaises(ValueError):
            self.check(value, outcome='success')
        value['status']['run_status'] = 'complete'
        value['status']['engineering_status'] = 'pass'
        with self.assertRaises(ValueError):
            self.check(value, outcome='success')

    def test_registered_schema_rejects_mutations_and_wrong_identity(self):
        value = _no_run()
        bad = copy.deepcopy(value)
        bad['metrics'] = {'invented': 1}
        with self.assertRaises(ValueError):
            self.check(bad)
        bad = copy.deepcopy(value)
        bad['status']['performance_status'] = 'pass'
        with self.assertRaises(ValueError):
            self.check(bad)
        bad = copy.deepcopy(value)
        bad['events'][0]['dataset_id'] = 'wrong'
        with self.assertRaises(ValueError):
            self.check(bad)
        with self.assertRaises(ValueError):
            contract.check_evaluation_contract_bytes(
                v.canonical_json(value), identity=v.evaluation_inventory('holdout')[1],
                input_hashes=value['input_hashes'], outcome='not_started')

    def test_noncanonical_bytes_and_re_pinned_false_status_metrics_fail(self):
        value = _no_run()
        with self.assertRaises(ValueError):
            contract.check_evaluation_contract_bytes(
                b' ' + v.canonical_json(value), identity=value['identity'],
                input_hashes=value['input_hashes'], outcome='not_started')
        receipt, report, payloads = example()
        # A false status/metrics claim is re-pinned through all three layers.
        # The byte/identity adapter deliberately accepts it; this layer cannot.
        receipt, report, payloads = copy.deepcopy(receipt), copy.deepcopy(report), dict(payloads)
        identity = report['rows'][0]['identity']
        path = contract.saved._payload_path(identity)
        false_evaluation = v.strict_json(payloads[path])
        false_evaluation['status'] = {'run_status': 'complete',
                                      'engineering_status': 'pass',
                                      'performance_status': 'pass'}
        false_evaluation['metrics'] = {'invented': 1}
        payloads[path] = v.canonical_json(false_evaluation)
        pin = lambda raw: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        receipt['attempts'][0]['evaluations'][0]['evaluation_sha256'] = pin(payloads[path])['sha256']
        report['rows'][0]['evaluation_pin'] = pin(payloads[path])
        report['payload_pins'][path] = pin(payloads[path])
        report['receipt_pin'] = pin(v.canonical_json(receipt))
        self.assertEqual(call(receipt, report, payloads)['latest_rows_bound'], 6)
        receipt_raw, report_raw = v.canonical_json(receipt), v.canonical_json(report)
        registry_raw = (Path(__file__).resolve().parents[1] /
                         'examples/configs/anomaly-v03-freeze-registry.json').read_bytes()
        with self.assertRaises(ValueError):
            contract.audit_saved_contract_candidate(
                registry_raw, receipt_raw, report_raw, payloads,
                expected_mode=contract.saved.MODE, chunk_index=0,
                expected_registry_pin=pin(registry_raw),
                expected_receipt_pin=pin(receipt_raw),
                expected_report_pin=pin(report_raw),
                expected_savepoint_pin=receipt['savepoint_pin'],
                expected_payload_pins={name: pin(raw) for name, raw in payloads.items()},
                source_snapshots={})

    def test_primary_projection_is_computed_from_independently_reported_ledger(self):
        metrics = {kind: {'numerator': pair[0], 'denominator': pair[1]}
                   for kind, pair in SUMMARY['counts'].items()
                   if not kind.startswith('availability:')}
        metrics['availability'] = [
            {'full_target': target,
             'metric': {'numerator': SUMMARY['counts']['availability:' + target][0],
                        'denominator': SUMMARY['counts']['availability:' + target][1]}}
            for target in contract.arithmetic.TARGETS]
        metrics['effective_clean_seconds'] = SUMMARY['effective_clean_seconds']
        evaluation = {'incidents': [{'causal_detected': True, 'delay_seconds': 1}] * 5}
        row = {'primary': {name: copy.deepcopy(SUMMARY[name]) for name in
                           ('counts', 'effective_clean_seconds', 'delay_histogram')}}
        contract._compare_primary(row, evaluation, {'metrics': metrics})
        changed = copy.deepcopy(row)
        changed['primary']['counts']['machine_recall'][0] += 1
        with self.assertRaisesRegex(ValueError, 'primary counts'):
            contract._compare_primary(changed, evaluation, {'metrics': metrics})
        changed = copy.deepcopy(row)
        changed['primary']['delay_histogram'] = [4, 1, 0, 0, 0]
        with self.assertRaisesRegex(ValueError, 'delay histogram'):
            contract._compare_primary(changed, evaluation, {'metrics': metrics})


if __name__ == '__main__':
    unittest.main()
