"""The tracked run-budget entry accepts saved pins before any native call."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_preformal_campaign_controller as controller
from banto_ai import anomaly_v03_preformal_campaign_metadata as metadata
from banto_ai import anomaly_v03_preformal_campaign_run_budget_owner as owner
from tests.test_anomaly_v03_preformal_campaign_run_intent_store import example
from tests._anomaly_v03_preformal_campaign_test_paths import PortableCampaignPaths


class RunBudgetOwnerTests(PortableCampaignPaths):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state, self.request = example(Path(self.temp.name))
        self.request_raw = controller.encode_request(self.request)
        self.request_pin = metadata.pin(self.request_raw)
        self.state.update(
            status='started_record_fixed',
            run_intent_raw=self.request_raw,
            run_intent_pin=self.request_pin)
        self.pin_control_pin = metadata.pin(b'external control')
        self.verified = {
            'request_path': str(Path(self.state['campaign_root']) /
                                'intents' / '0001-run-budget.json'),
            'request_pin': self.request_pin,
            'record_count': 1,
            'journal_head_sha256': self.state['started_record_pin']['sha256'],
            'native_run_started': False,
            'campaign_coherence_authenticated': False,
            'formal_permission': False,
        }
        self.inputs = dict(
            expected_plan_pin=self.state['plan_pin'],
            expected_initial_checkpoint_pin=self.state['initial_checkpoint_pin'],
            expected_intention_pin=self.state['intention_pin'],
            expected_prepare_receipt_pin=self.state['prepare_receipt_pin'],
            expected_started_record_pin=self.state['started_record_pin'],
            expected_next_checkpoint_pin=self.state['next_checkpoint_pin'],
            expected_pin_control_pin=self.pin_control_pin)
        self.plan = v.strict_json(self.state['plan_raw'])
        self.record = v.strict_json(self.state['record_raws'][0])
        self.receipt_path = controller._control(
            self.plan, self.record, 'run-budget') / 'receipt.json'

    def _receipt(self, status):
        value = {
            'format': controller.RECEIPT_FORMAT,
            'scope': 'invented-two-slot-owned-cli-only',
            'phase': 'run-budget',
            'request_pin': self.request_pin,
            'anchor_pin': self.state['plan_pin'],
            'journal_count': 1,
            'journal_head_sha256':
                self.state['started_record_pin']['sha256'],
            'chunk_index': 0,
            'attempt': 1,
            'status': status,
            'invented_only': True,
            'actual_registered_observations_read': False,
            'campaign_evaluations_credited': 0,
            'campaign_coherence_authenticated': False,
            'full_end_to_end_budget_measured': False,
            'formal_permission': False,
        }
        if status == 'failed':
            value.update(reason='worker_exit', retry_authorized=False,
                         descendant_exit_confirmed=False)
        return value

    def _save(self, value):
        self.receipt_path.parent.mkdir(parents=True)
        raw = v.canonical_json(value) + b'\n'
        self.receipt_path.write_bytes(raw)
        return value, metadata.pin(raw)

    def _run(self):
        return owner.execute_run_budget(
            self.state['campaign_root'], self.state['control_root'],
            **self.inputs)

    def test_reopens_external_pin_twice_and_returns_saved_verified_receipt(self):
        receipt = self._receipt('verified')
        with patch.object(owner.intent, 'verify_request',
                          return_value=self.verified) as verify, \
             patch.object(owner.store, 'verify_started_store',
                          return_value=self.state) as started, \
             patch.object(owner.controller, 'execute_owned',
                          side_effect=lambda *a, **k: self._save(receipt)) as run, \
             patch.object(owner.controller, '_load_receipt',
                          return_value=receipt) as loaded:
            value, pin = self._run()
        self.assertEqual(value, receipt)
        self.assertEqual(pin, metadata.pin(self.receipt_path.read_bytes()))
        self.assertEqual(verify.call_count, 2)
        self.assertEqual(started.call_count, 1)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0],
                         Path(self.verified['request_path']))
        self.assertEqual(run.call_args.args[1], self.request_pin)
        self.assertEqual(run.call_args.args[2], self.state['plan_raw'])
        self.assertEqual(run.call_args.args[4], self.state['record_raws'])
        self.assertEqual(run.call_args.kwargs['expected_record_count'], 1)
        self.assertEqual(run.call_args.kwargs['expected_head_sha256'],
                         self.state['started_record_pin']['sha256'])
        self.assertEqual(loaded.call_count, 1)

    def test_changed_external_pin_at_final_read_prevents_native_call(self):
        changed = dict(self.verified, request_pin=metadata.pin(b'changed'))
        with patch.object(owner.intent, 'verify_request',
                          side_effect=[self.verified, changed]) as verify, \
             patch.object(owner.store, 'verify_started_store',
                          return_value=self.state), \
             patch.object(owner.controller, 'execute_owned') as run:
            with self.assertRaises(ValueError):
                self._run()
        self.assertEqual(verify.call_count, 2)
        run.assert_not_called()

    def test_rejected_upstream_store_never_calls_native_owner(self):
        with patch.object(owner.intent, 'verify_request',
                          side_effect=ValueError('stale source')), \
             patch.object(owner.store, 'verify_started_store') as started, \
             patch.object(owner.controller, 'execute_owned') as run:
            with self.assertRaisesRegex(ValueError, 'stale source'):
                self._run()
        started.assert_not_called()
        run.assert_not_called()

    def test_failed_receipt_is_pinned_and_terminal(self):
        receipt = self._receipt('failed')
        with patch.object(owner.intent, 'verify_request',
                          return_value=self.verified), \
             patch.object(owner.store, 'verify_started_store',
                          return_value=self.state), \
             patch.object(owner.controller, 'execute_owned',
                          side_effect=lambda *a, **k: self._save(receipt)), \
             patch.object(owner.controller, '_load_receipt') as loaded:
            value, pin = self._run()
        self.assertEqual(value['status'], 'failed')
        self.assertEqual(pin, metadata.pin(self.receipt_path.read_bytes()))
        loaded.assert_not_called()

    def test_unsaved_or_divergent_receipt_cannot_be_returned(self):
        receipt = self._receipt('verified')
        with patch.object(owner.intent, 'verify_request',
                          return_value=self.verified), \
             patch.object(owner.store, 'verify_started_store',
                          return_value=self.state), \
             patch.object(owner.controller, 'execute_owned',
                          return_value=(receipt, metadata.pin(
                              v.canonical_json(receipt) + b'\n'))), \
             patch.object(owner.controller, '_load_receipt') as loaded:
            with self.assertRaises((ValueError, OSError)):
                self._run()
        loaded.assert_not_called()
        forged = dict(receipt, status='failed', reason='worker_exit',
                      retry_authorized=False,
                      descendant_exit_confirmed=False)

        def divergent(*args, **kwargs):
            _, pin = self._save(forged)
            return receipt, pin

        with patch.object(owner.intent, 'verify_request',
                          return_value=self.verified), \
             patch.object(owner.store, 'verify_started_store',
                          return_value=self.state), \
             patch.object(owner.controller, 'execute_owned',
                          side_effect=divergent):
            with self.assertRaises(ValueError):
                self._run()


if __name__ == '__main__':
    unittest.main()
