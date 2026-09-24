"""Exercise the external resume boundary with small real saved files."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from banto_ai.anomaly_v03_attempt_controller import Controller as ActualController
from tools.evaluator import anomaly_v03_verified_resume as resume


class VerifiedResumeTests(unittest.TestCase):
    def setUp(self):
        self.source = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.root = self.source / 'artifacts/v03-runs/r1'
        self.root.mkdir(parents=True)
        self.runtime = {'observed': 'test runtime'}
        self.records = [{'sequence': i + 1, 'chunk_index': 0, 'status': status}
                        for i, status in enumerate(('running', 'saved_pending_verification', 'verified_complete'))]
        self.receipt, self.pins = {'checkpoint': 3}, {'3': 'a' * 64}
        self.closed = {'checkpoint': {'receipt': self.receipt, 'descriptor_pins': self.pins},
                       'status': 'failed', 'formal_permission': False}
        self.write('run/control/000008/closed.json', self.closed)
        for row in self.records:
            self.write(f"run/metadata/journal/{row['sequence']:06d}.json", row)
        self.payload = self.root / 'run/attempts/chunks/000/result.bin'
        self.payload.parent.mkdir(parents=True)
        self.payload.write_bytes(b'a saved payload')
        files = {p.relative_to(self.root).as_posix(): self.pin(p) for p in self.root.rglob('*') if p.is_file()}
        self.snapshot = {'format': resume.FORMAT, 'completed_chunks': 1, 'formal_permission': False,
                         'run_root': str(self.root), 'source_root': str(self.source), 'run_name': 'r1',
                         'source_revision': 'b' * 40, 'closed_sequence': 8, 'runtime': self.runtime,
                         'closed_sha256': files['run/control/000008/closed.json']['sha256'], 'files': files}
        self.snapshot_path = self.source / 'snapshot.json'
        self.report_path = self.source / 'proof.json'
        self.checkout = Mock()
        self.enterContext(patch.object(resume.rt, 'capture_checkout', return_value=self.checkout))
        self.enterContext(patch.object(resume.resources, 'probe_runtime', return_value=self.runtime))
        fixture = self

        class Controller:
            def __init__(self):
                self.root, self.metadata_root = fixture.root / 'run/attempts', fixture.root / 'run/metadata'
                self.producer_root = self.consumer_root = fixture.source
                self.verifier_revision = 'b' * 40
                self.records = copy.deepcopy(fixture.records)
                self.receipt, self.descriptor_pins = fixture.receipt, fixture.pins
                self.state = {'next_unverified_chunk': 1}
                self.pins = {}
                self.verified_in_session, self.audited = set(), []

            def _verify(self, records, pins, digest):
                self.audited.append(records[-1]['chunk_index'])

            _revalidate_completed = ActualController._revalidate_completed

        self.Controller = Controller

    def pin(self, path):
        raw = path.read_bytes()
        return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

    def write(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding='utf-8')

    def policy(self, **kwargs):
        self.snapshot_path.write_text(json.dumps(self.snapshot), encoding='utf-8')
        return resume.VerifiedResume(self.snapshot_path, self.pin(self.snapshot_path)['sha256'], self.report_path, **kwargs)

    def assert_rejected(self, policy, controller=None):
        controller = controller or self.Controller()
        original = self.Controller._revalidate_completed
        with self.assertRaises((ValueError, OSError)), policy.install(self.Controller):
            controller._revalidate_completed()
        self.assertEqual(controller.verified_in_session, set())
        self.assertFalse(self.report_path.exists())
        self.assertIs(self.Controller._revalidate_completed, original)

    def test_old_bytes_reused_but_new_completed_record_still_audited(self):
        discarded, fresh = self.Controller(), self.Controller()
        policy = self.policy()
        with policy.install(self.Controller):
            fresh._revalidate_completed()
            self.assertEqual(fresh.audited, [])
            fresh.records.extend({'sequence': i + 4, 'chunk_index': 1, 'status': status}
                                 for i, status in enumerate(('running', 'saved_pending_verification', 'verified_complete')))
            fresh.descriptor_pins['6'] = 'c' * 64
            fresh._revalidate_completed()
            fresh._revalidate_completed()
        self.assertIs(policy.controller, fresh)
        self.assertEqual(discarded.verified_in_session, set())
        self.assertEqual(fresh.audited, [1])
        proof = json.loads(self.report_path.read_bytes())
        self.assertEqual(proof['completed_chunk_audits_reused'], 1)
        self.assertEqual(proof['files_verified'], len(self.snapshot['files']))
        self.assertTrue(proof['new_chunk_audits_unchanged'])
        self.checkout.recheck.assert_called_once()

    def test_same_length_payload_tampering_rejected(self):
        policy = self.policy()
        self.payload.write_bytes(b'X saved payload')
        self.assert_rejected(policy)

    def add_failed_tail(self):
        tail = [{'sequence': i + 4, 'chunk_index': 1, 'attempt': 1,
                 'status': status, 'reason': reason, 'outcome': None}
                for i, (status, reason) in enumerate((('running', None), ('failed', 'resource_limit')))]
        self.records.extend(tail)
        for row in tail:
            name = f"run/metadata/journal/{row['sequence']:06d}.json"
            self.write(name, row)
            self.snapshot['files'][name] = self.pin(self.root / name)
        self.snapshot['failed_tail_records'] = copy.deepcopy(tail)

    def test_failed_tail_preserved_and_retry_still_requires_new_audit(self):
        self.add_failed_tail()
        before = {name: self.pin(self.root / name) for name in self.snapshot['files']}
        policy, controller = self.policy(), self.Controller()
        with policy.install(self.Controller):
            controller._revalidate_completed()
            self.assertEqual(len(controller.verified_in_session), 1)
            self.assertEqual(controller.audited, [])
            controller.records.extend({'sequence': i + 6, 'chunk_index': 1, 'attempt': 2, 'status': status}
                                      for i, status in enumerate(('running', 'saved_pending_verification', 'verified_complete')))
            controller.descriptor_pins['8'] = 'c' * 64
            controller._revalidate_completed()
            controller._revalidate_completed()
        self.assertEqual(controller.audited, [1])
        self.assertEqual(policy.report['failed_tail_records_preserved'], 2)
        self.assertEqual(policy.report['failed_chunk_audits_reused'], 0)
        self.assertEqual(before, {name: self.pin(self.root / name) for name in before})

    def test_unpinned_failed_tail_rejected(self):
        self.add_failed_tail()
        del self.snapshot['failed_tail_records']
        self.assert_rejected(self.policy())

    def test_failed_tail_controller_or_saved_journal_change_rejected(self):
        self.add_failed_tail()
        controller = self.Controller()
        controller.records[-1]['reason'] = 'interrupted'
        self.assert_rejected(self.policy(), controller)
        self.write('run/metadata/journal/000005.json', {'changed': True})
        self.assert_rejected(self.policy())

    def test_invalid_or_incomplete_failed_tail_rejected(self):
        self.add_failed_tail()
        original = copy.deepcopy(self.snapshot['failed_tail_records'])
        variants = [original[:1], original + [original[-1]]]
        for key, value in (('chunk_index', 0), ('attempt', 2), ('status', 'blocked_integrity'),
                           ('reason', 'interrupted'), ('sequence', 9), ('outcome', {'success': True})):
            rows = copy.deepcopy(original)
            rows[-1][key] = value
            variants.append(rows)
        for rows in variants:
            with self.subTest(rows=rows):
                self.snapshot['failed_tail_records'] = rows
                with self.assertRaises(ValueError):
                    self.policy()

    def test_missing_file_rejected(self):
        policy = self.policy()
        self.payload.unlink()
        self.assert_rejected(policy)

    def test_unexpected_new_file_rejected(self):
        policy = self.policy()
        self.write('unexpected.json', {})
        self.assert_rejected(policy)

    def test_live_invocation_requires_exact_expected_extra_files(self):
        policy = self.policy(live_control=True)
        for name in ('started.json', 'inspection-pin.json', 'inspection/report.json',
                     'inspection/supervision.json', 'inspection/stderr.json'):
            self.write('run/control/000009/' + name, {})
        with policy.install(self.Controller):
            self.Controller()._revalidate_completed()
        self.assertEqual(policy.report['completed_chunk_audits_reused'], 1)

    def test_live_invocation_missing_inspection_rejected(self):
        policy = self.policy(live_control=True)
        self.write('run/control/000009/started.json', {})
        self.assert_rejected(policy)

    def test_changed_runtime_rejected(self):
        with patch.object(resume.resources, 'probe_runtime', return_value={'observed': 'changed'}):
            self.assert_rejected(self.policy())

    def test_changed_source_during_verification_rejected(self):
        self.checkout.recheck.side_effect = ValueError('changed source')
        self.assert_rejected(self.policy())

    def test_stale_closed_or_checkpoint_rejected(self):
        policy = self.policy()
        controller = self.Controller()
        controller.receipt = {'checkpoint': 0}
        self.assert_rejected(policy, controller)

    def test_stale_external_snapshot_pin_rejected(self):
        self.policy()
        with self.assertRaises(ValueError):
            resume.VerifiedResume(self.snapshot_path, '0' * 64, self.report_path)

    def test_report_failure_does_not_prime_cache(self):
        with patch.object(resume.storage, '_exclusive', side_effect=OSError('disk full')):
            self.assert_rejected(self.policy())

    def test_saved_journal_differs_from_controller_rejected(self):
        controller = self.Controller()
        controller.records[-1]['status'] = 'verified_inconclusive'
        self.assert_rejected(self.policy(), controller)

    def test_method_restored_and_replacement_rejected(self):
        policy, original = self.policy(), self.Controller._revalidate_completed
        with policy.install(self.Controller):
            self.Controller()._revalidate_completed()
            other = self.Controller()
            with self.assertRaises(ValueError):
                other._revalidate_completed()
            self.assertEqual(other.verified_in_session, set())
            with self.assertRaises(ValueError), policy.install(self.Controller):
                pass
        self.assertIs(self.Controller._revalidate_completed, original)


if __name__ == '__main__':
    unittest.main()
