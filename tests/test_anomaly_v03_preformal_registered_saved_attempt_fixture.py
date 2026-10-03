"""Invented registered bytes in the saved-attempt directory shape only."""
from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_ledger_audit as ledger_audit
from banto_ai import anomaly_v03_scoring as scoring
from banto_ai import anomaly_v03_slices as slices
from banto_ai import anomaly_v03_registered_saved_attempt_fixture as fixture
from banto_ai import anomaly_v03_registered_saved_summary as saved
from tests.test_anomaly_v03_preformal_full_chunk_fixture import pin
from tests.test_anomaly_v03_registered_completed_contract_fixture import (
    invented_complete_inconclusive, invented_completed_chunk)
from tests.test_anomaly_v03_scoring import encode, saved_row


class InventedRegisteredSavedAttemptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(
            prefix=fixture.PREFIX, dir=fixture.ROOT / 'artifacts')
        cls.root = Path(cls.temporary.name)
        cls.run_root = cls.root / 'run-root'
        cls.run_root.mkdir()
        (cls.root / 'saved').mkdir()
        registry_raw, receipt_raw, report_raw, payloads, expected = invented_completed_chunk()
        cls.registry_raw = registry_raw
        cls.receipt = v.strict_json(receipt_raw)
        cls.report = v.strict_json(report_raw)
        cls.payloads = payloads
        cls.source_snapshots = expected['source_snapshots']
        cls.identities = v.evaluation_inventory('holdout')[:6]
        observation_bytes, observation_digest = encode([
            saved_row(equipment, sample, constant=True)
            for equipment in ('motor-01', 'conveyor-01') for sample in range(9000)])
        for identity in cls.identities:
            if identity['candidate_id'] == cls.identities[0]['candidate_id']:
                cls.payloads[saved._payload_path(identity, 'observations')] = observation_bytes
                cls.payloads[saved._payload_path(identity, 'events')] = b''.join(
                    v.canonical_json(event) + b'\n'
                    for event in v.event_inventory(identity))
            hashes = {kind: pin(cls.payloads[saved._payload_path(identity, kind)])['sha256']
                      for kind in fixture.metadata.INPUT_HASHES}
            assert hashes['observations'] == observation_digest
            value = invented_complete_inconclusive(identity, hashes)
            profiles = scoring.fit_profiles(identity, observation_bytes,
                                            expected_sha256=observation_digest)
            value['profiles'] = profiles.ledger_rows()
            value['scores'] = scoring.score_test(profiles, observation_bytes,
                                                 expected_sha256=observation_digest)
            value['row_counts'] = {name: len(value[name]) for name in
                                   ('events', 'profiles', 'scores', 'source_episodes',
                                    'equipment_episodes', 'incidents')}
            logical = saved._payload_path(identity)
            raw = v.canonical_json(value)
            cls.payloads[logical] = raw
            row_index = cls.identities.index(identity)
            cls.receipt['attempts'][0]['evaluations'][row_index].update(
                status='inconclusive', profile_status='inconclusive',
                input_hashes=hashes, evaluation_sha256=pin(raw)['sha256'])
            cls.report['rows'][row_index].update(
                evaluation_outcome='inconclusive', evaluation_pin=pin(raw),
                input_hashes=hashes,
                slices=slices.summarize_evaluation(value, {
                    'identity': identity, 'evaluation_outcome': 'inconclusive',
                    'ledger_audit': ledger_audit.audit_evaluation(value)},
                    reported_only=True)['counts'])
        cls.savepoint = {
            'format': fixture.SAVEPOINT_FORMAT, 'mode': saved.MODE,
            'invented_only': True, 'campaign_completed': False,
            'actual_registered_observations_read': False,
            'run_root': str(cls.run_root), 'chunk_index': 0}
        cls.savepoint_raw = v.canonical_json(cls.savepoint)
        cls.receipt['savepoint_pin'] = pin(cls.savepoint_raw)
        cls.report['savepoint_pin'] = pin(cls.savepoint_raw)
        cls.receipt_raw = v.canonical_json(cls.receipt)
        cls.report['receipt_pin'] = pin(cls.receipt_raw)
        cls.report['payload_pins'] = {name: pin(raw) for name, raw in cls.payloads.items()}
        cls.report_raw = v.canonical_json(cls.report)
        cls.options = {
            'expected_mode': saved.MODE, 'chunk_index': 0,
            'expected_registry_pin': pin(cls.registry_raw),
            'expected_savepoint_pin': pin(cls.savepoint_raw),
            'expected_receipt_pin': pin(cls.receipt_raw),
            'expected_report_pin': pin(cls.report_raw),
            'expected_payload_pins': dict(cls.report['payload_pins']),
            'source_snapshots': cls.source_snapshots}
        cls.write('saved/savepoint.json', cls.savepoint_raw)
        cls.write('saved/registry.json', cls.registry_raw)
        cls.write('saved/receipt.json', cls.receipt_raw)
        cls.write('saved/report.json', cls.report_raw)
        _, names = fixture._names(0, 1)
        for logical, physical in names.items():
            cls.write('run-root/' + physical, cls.payloads[logical])

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    @classmethod
    def write(cls, relative, raw):
        path = cls.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)

    def call(self, **changes):
        return fixture.read_invented_registered_attempt(
            self.root, **(self.options | changes))

    def test_six_invented_evaluations_use_actual_attempt_paths_and_closed_scope(self):
        value = self.call()
        self.assertEqual(value['status'], 'latest_chunk_saved_bytes_bound')
        self.assertEqual(value['fixture_physical_layout'], 'run-attempt-result-payload')
        self.assertEqual(value['fixture_files_read'], 22)
        self.assertEqual(value['registered_evaluation_contracts_checked'], 6)
        self.assertTrue(value['invented_observation_profile_score_recomputed'])
        self.assertTrue(value['observation_to_profile_recomputed'])
        self.assertTrue(value['observation_to_score_recomputed'])
        self.assertTrue(value['observation_to_summary_recomputed'])
        self.assertFalse(value['actual_registered_observations_read'])
        self.assertFalse(value['registered_observations_read'])
        self.assertFalse(value['campaign_completed'])
        self.assertEqual(value['campaign_evaluations_credited'], 0)
        for field in ('actual_worker_exit_authenticated', 'formal_permission',
                      'execution_authenticated', 'result_trusted',
                      'source_closure_complete', 'runtime_closure_complete',
                      'independent_s6_complete'):
            self.assertFalse(value[field], field)

    def test_formal_mode_and_failed_latest_attempt_stop_before_payloads(self):
        with self.assertRaisesRegex(ValueError, 'mode is closed'):
            self.call(expected_mode='formal')
        changed = copy.deepcopy(self.receipt)
        changed['attempts'][0]['state'] = 'failed'
        changed['attempts'][0]['failure'] = {
            'stage': 'supervision', 'reason': 'worker_exit',
            'evidence_sha256': None}
        changed_raw = v.canonical_json(changed)
        original = self.receipt_raw
        try:
            self.write('saved/receipt.json', changed_raw)
            with self.assertRaisesRegex(ValueError, 'latest invented attempt is not complete'):
                self.call(expected_receipt_pin=pin(changed_raw))
        finally:
            self.write('saved/receipt.json', original)

    def test_altered_saved_bytes_and_external_pin_are_rejected(self):
        logical = saved._payload_path(self.identities[0], 'observations')
        physical = fixture._names(0, 1)[1][logical]
        path = self.run_root / physical
        original = path.read_bytes()
        try:
            path.write_bytes(original + b' ')
            with self.assertRaisesRegex(ValueError, 'pinned file'):
                self.call()
        finally:
            path.write_bytes(original)
        with self.assertRaisesRegex(ValueError, 'pinned file'):
            self.call(expected_savepoint_pin=pin(b'wrong external savepoint'))

    def test_resealed_score_dependency_disagrees_with_observations(self):
        logical = saved._payload_path(self.identities[0])
        physical = fixture._names(0, 1)[1][logical]
        path = self.run_root / physical
        value = v.strict_json(self.payloads[logical])
        dependency = value['scores'][0]['dependencies'][0]
        dependency['value'] += 1.0
        altered = v.canonical_json(value)
        receipt = copy.deepcopy(self.receipt)
        report = copy.deepcopy(self.report)
        receipt['attempts'][0]['evaluations'][0]['evaluation_sha256'] = pin(altered)['sha256']
        receipt_raw = v.canonical_json(receipt)
        report['receipt_pin'] = pin(receipt_raw)
        report['rows'][0]['evaluation_pin'] = pin(altered)
        report['payload_pins'][logical] = pin(altered)
        report_raw = v.canonical_json(report)
        payload_pins = dict(self.options['expected_payload_pins'])
        payload_pins[logical] = pin(altered)
        try:
            path.write_bytes(altered)
            self.write('saved/receipt.json', receipt_raw)
            self.write('saved/report.json', report_raw)
            with self.assertRaisesRegex(ValueError, r'scores\[0\]'):
                self.call(expected_receipt_pin=pin(receipt_raw),
                          expected_report_pin=pin(report_raw),
                          expected_payload_pins=payload_pins)
        finally:
            path.write_bytes(self.payloads[logical])
            self.write('saved/receipt.json', self.receipt_raw)
            self.write('saved/report.json', self.report_raw)


if __name__ == '__main__':
    unittest.main()
