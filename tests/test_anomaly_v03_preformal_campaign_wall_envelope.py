"""One live clock includes stage gaps and preserves limited failure evidence."""
from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_preformal_campaign_metadata as metadata
from banto_ai import anomaly_v03_preformal_campaign_prepare_owner as prepare
from banto_ai import anomaly_v03_preformal_campaign_reread_intent_store as reread
from banto_ai import anomaly_v03_preformal_campaign_run_budget_owner as run_owner
from banto_ai import anomaly_v03_preformal_campaign_wall_envelope as wall


def _pin(name):
    return metadata.pin(name.encode('ascii'))


class FakeClock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value


class WallEnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.campaign = Path(self.folder.name) / 'anomaly-v03-preformal-campaign-aaaaaaaa'
        self.control = Path(self.folder.name) / 'anomaly-v03-preformal-campaign-control-aaaaaaaa'
        self.campaign.mkdir()
        self.control.mkdir()
        self.checkpoint_pin = _pin('checkpoint')
        self.intention_pin = _pin('intention')
        plan = {'campaign_id': 'a' * 64,
                'root': str(self.campaign),
                'source': {'revision': 'f' * 40},
                'budget_candidate': {'limits': {'wall_seconds': 100}}}
        self.state = {'campaign_root': str(self.campaign),
                      'control_root': str(self.control),
                      'plan_raw': v.canonical_json(plan)}
        self.plan_pin = metadata.pin(self.state['plan_raw'])
        self.clock = FakeClock()
        self.calls = []
        self.durations = {}
        self.stop_at = None
        self.failed_return_at = None

    def _action(self, name, result, *, available=None):
        self.calls.append((name, available))
        self.clock.value += self.durations.get(name, 1.0)
        if name == self.stop_at:
            raise ValueError('invented stage error')
        if name == self.failed_return_at:
            result = ({'status': 'failed'}, result[1])
        return result

    def _patched(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(
            wall.store, 'verify_store',
            side_effect=lambda *a, **k: self._action('preflight', self.state)))
        stack.enter_context(patch.object(
            wall.prepare, 'execute',
            side_effect=lambda *a, **k: self._action(
                'prepare', ({'status': 'prepared'}, _pin('prepared')),
                available=k['remaining_wall_seconds'])))
        stack.enter_context(patch.object(
            wall.store, 'append_started',
            side_effect=lambda *a, **k: self._action('started', {
                'status': 'started_record_fixed',
                'started_record_pin': _pin('started'),
                'next_checkpoint_pin': _pin('next')})))
        stack.enter_context(patch.object(
            wall.run_intent, 'create_request',
            side_effect=lambda *a, **k: self._action('run-intent', {
                'status': 'run_budget_request_pinned',
                'pin_control_pin': _pin('run-control'),
                'request_pin': _pin('run-request')})))
        stack.enter_context(patch.object(
            wall.run_owner, 'execute_run_budget',
            side_effect=lambda *a, **k: self._action(
                'run-budget', ({'status': 'verified'}, _pin('generation')),
                available=k['remaining_wall_seconds'])))
        stack.enter_context(patch.object(
            wall.reread, 'create_request',
            side_effect=lambda *a, **k: self._action('reread-intent', {
                'status': 'saved_reread_request_pinned',
                'pin_control_pin': _pin('reread-control'),
                'request_pin': _pin('reread-request')})))
        stack.enter_context(patch.object(
            wall.reread, 'execute_request',
            side_effect=lambda *a, **k: self._action(
                'saved-reread', ({'status': 'verified'}, _pin('reread')),
                available=k['remaining_wall_seconds'])))
        stack.enter_context(patch.object(
            wall.completion, 'append_completed',
            side_effect=lambda *a, **k: self._action('completed', {
                'declared_completed_chunks': 1,
                'declared_completed_evaluations': 6,
                'campaign_evaluations_credited': 0,
                'formal_permission': False,
                'completed_record_pin': _pin('completed'),
                'terminal_checkpoint_pin': _pin('terminal')})))
        return stack

    def _run(self, wall_seconds=30):
        return wall.execute(
            self.campaign, self.control,
            expected_plan_pin=self.plan_pin,
            expected_initial_checkpoint_pin=self.checkpoint_pin,
            expected_intention_pin=self.intention_pin,
            wall_seconds=wall_seconds, clock=self.clock)

    def _saved(self, result, pin):
        root = Path(self.folder.name) / 'anomaly-v03-preformal-campaign-wall-aaaaaaaa'
        raw = (root / 'receipt.json').read_bytes()
        self.assertEqual(metadata.pin(raw), pin)
        self.assertEqual(v.strict_json(raw), result)
        self.assertEqual(metadata.pin((root / 'claim.json').read_bytes()),
                         result['claim_pin'])

    def _verify_fixture(self):
        self._patched()
        receipt, pin = self._run()
        self.assertEqual(receipt['status'], 'verified')
        (self.campaign / 'plan.json').write_bytes(self.state['plan_raw'])
        (self.campaign / 'intents').mkdir()
        (self.campaign / 'intents' / '0001-run-budget.json').write_bytes(
            b'run-request')
        (self.campaign / 'intents' / '0001-saved-reread.json').write_bytes(
            b'reread-request')
        envelope = Path(self.folder.name) / (
            'anomaly-v03-preformal-campaign-wall-aaaaaaaa')
        return envelope, receipt, pin

    def _verify_saved(self, pin, *, expected_call=True):
        saved = {
            'status': 'partial_declarations_unverified',
            'declared_completed_chunks': 1,
            'declared_completed_evaluations': 6,
            'campaign_evaluations_credited': 0,
            'formal_permission': False,
            'completed_record_pin': _pin('completed'),
            'terminal_checkpoint_pin': _pin('terminal'),
        }
        with patch.object(wall.metadata, 'encode_plan',
                          return_value=self.state['plan_raw']), \
             patch.object(wall.completion, 'verify_completed',
                          return_value=saved) as completion_check:
            result = wall.verify_completed(
                self.campaign, self.control, expected_receipt_pin=pin)
        if expected_call:
            completion_check.assert_called_once()
            self.assertEqual(completion_check.call_args.kwargs[
                'expected_completed_record_pin'], _pin('completed'))
            self.assertEqual(completion_check.call_args.kwargs[
                'expected_terminal_checkpoint_pin'], _pin('terminal'))
        else:
            completion_check.assert_not_called()
        return result

    def test_single_clock_includes_python_stage_gaps_and_reduces_native_limits(self):
        self.durations = {'preflight': 2.0, 'prepare': 3.0,
                          'started': 4.0, 'run-intent': 5.0,
                          'run-budget': 6.0, 'reread-intent': 7.0,
                          'saved-reread': 8.0, 'completed': 9.0}
        self._patched()
        result, pin = self._run(60)
        self._saved(result, pin)
        self.assertEqual((result['status'], result['elapsed_seconds']),
                         ('verified', 44.0))
        self.assertEqual({name: available for name, available in self.calls
                          if available is not None},
                         {'prepare': 58.0, 'run-budget': 46.0,
                          'saved-reread': 33.0})
        self.assertFalse(result['hard_wall_quota_authenticated'])
        self.assertFalse(result['full_end_to_end_budget_measured'])
        self.assertFalse(result['formal_permission'])

    def test_expiry_after_started_retains_pins_and_blocks_next_stage(self):
        self.durations = {'preflight': 1.0, 'prepare': 1.0,
                          'started': 9.0}
        self._patched()
        result, pin = self._run(10)
        self._saved(result, pin)
        self.assertEqual((result['status'], result['reason'],
                          result['last_stage']),
                         ('failed', 'shared_wall_expired', 'started'))
        self.assertEqual(result['evidence_pins']['prepare_receipt_pin'],
                         _pin('prepared'))
        self.assertEqual(result['evidence_pins']['started_record_pin'],
                         _pin('started'))
        self.assertNotIn('run-intent', [name for name, _ in self.calls])

    def test_failed_native_stage_keeps_prior_pins_and_stops(self):
        self.failed_return_at = 'run-budget'
        self._patched()
        result, pin = self._run()
        self._saved(result, pin)
        self.assertEqual((result['status'], result['reason'],
                          result['error_type']),
                         ('failed', 'stage_failed', 'V03ValidationError'))
        self.assertEqual(result['evidence_pins']['run_request_pin'],
                         _pin('run-request'))
        self.assertEqual(result['evidence_pins']['generation_receipt_pin'],
                         _pin('generation'))
        self.assertNotIn('reread-intent', [name for name, _ in self.calls])

    def test_nonfinite_or_nonpositive_limit_rejected_before_preflight(self):
        self._patched()
        for value in (float('nan'), float('inf'), 0, -1, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self._run(value)
        self.assertEqual(self.calls, [])

    def test_remaining_args_reject_nonfinite_or_nonpositive_before_store(self):
        for value in (float('nan'), float('inf'), 0, -1, True):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    prepare.effective_limits(value)
                with self.assertRaises(ValueError):
                    run_owner.execute_run_budget(
                        self.campaign, self.control,
                        expected_plan_pin=self.plan_pin,
                        expected_initial_checkpoint_pin=self.checkpoint_pin,
                        expected_intention_pin=self.intention_pin,
                        expected_prepare_receipt_pin=_pin('prepare'),
                        expected_started_record_pin=_pin('started'),
                        expected_next_checkpoint_pin=_pin('next'),
                        expected_pin_control_pin=_pin('run'),
                        remaining_wall_seconds=value)
                with self.assertRaises(ValueError):
                    reread.execute_request(
                        self.campaign, self.control,
                        expected_plan_pin=self.plan_pin,
                        expected_initial_checkpoint_pin=self.checkpoint_pin,
                        expected_intention_pin=self.intention_pin,
                        expected_prepare_receipt_pin=_pin('prepare'),
                        expected_started_record_pin=_pin('started'),
                        expected_next_checkpoint_pin=_pin('next'),
                        expected_run_pin_control_pin=_pin('run'),
                        expected_generation_receipt_pin=_pin('generation'),
                        expected_pin_control_pin=_pin('reread'),
                        remaining_wall_seconds=value)
        self.assertEqual(prepare.effective_limits(0.5)['wall_seconds'], 0.5)
        self.assertEqual(prepare.effective_limits(1000), prepare.LIMITS)

    def test_read_only_verify_reopens_success_and_passes_all_completion_pins(self):
        envelope, receipt, pin = self._verify_fixture()
        checked = self._verify_saved(pin)
        self.assertEqual(checked['status'], 'verified_retained')
        self.assertEqual(checked['receipt_pin'], pin)
        self.assertEqual(checked['completed_record_pin'],
                         receipt['evidence_pins']['completed_record_pin'])
        self.assertEqual({path.name for path in envelope.iterdir()},
                         {'claim.json', 'receipt.json'})

    def test_read_only_verify_rejects_receipt_and_claim_raw_tampering(self):
        envelope, _, pin = self._verify_fixture()
        receipt_path = envelope / 'receipt.json'
        receipt_path.write_bytes(receipt_path.read_bytes() + b' ')
        with patch.object(wall.completion, 'verify_completed') as completion_check:
            with self.assertRaises(ValueError):
                wall.verify_completed(self.campaign, self.control,
                                      expected_receipt_pin=pin)
            completion_check.assert_not_called()
        receipt_path.write_bytes(receipt_path.read_bytes()[:-1])
        claim_path = envelope / 'claim.json'
        claim_path.write_bytes(claim_path.read_bytes() + b' ')
        with patch.object(wall.completion, 'verify_completed') as completion_check:
            with self.assertRaises(ValueError):
                wall.verify_completed(self.campaign, self.control,
                                      expected_receipt_pin=pin)
            completion_check.assert_not_called()

    def test_read_only_verify_rejects_missing_evidence_pin_or_request_raw(self):
        envelope, receipt, _ = self._verify_fixture()
        del receipt['evidence_pins']['generation_receipt_pin']
        raw = v.canonical_json(receipt) + b'\n'
        (envelope / 'receipt.json').write_bytes(raw)
        with patch.object(wall.completion, 'verify_completed') as completion_check:
            with self.assertRaises(ValueError):
                wall.verify_completed(self.campaign, self.control,
                                      expected_receipt_pin=metadata.pin(raw))
            completion_check.assert_not_called()
        receipt['evidence_pins']['generation_receipt_pin'] = _pin('generation')
        raw = v.canonical_json(receipt) + b'\n'
        (envelope / 'receipt.json').write_bytes(raw)
        (self.campaign / 'intents' / '0001-run-budget.json').unlink()
        with patch.object(wall.metadata, 'encode_plan',
                          return_value=self.state['plan_raw']), \
             patch.object(wall.completion, 'verify_completed') as completion_check:
            with self.assertRaises((ValueError, OSError)):
                wall.verify_completed(self.campaign, self.control,
                                      expected_receipt_pin=metadata.pin(raw))
            completion_check.assert_not_called()

    def test_read_only_verify_rejects_resealed_out_of_range_elapsed(self):
        envelope, receipt, _ = self._verify_fixture()
        receipt['elapsed_seconds'] = receipt['wall_seconds']
        raw = v.canonical_json(receipt) + b'\n'
        (envelope / 'receipt.json').write_bytes(raw)
        with patch.object(wall.completion, 'verify_completed') as completion_check:
            with self.assertRaises(ValueError):
                wall.verify_completed(self.campaign, self.control,
                                      expected_receipt_pin=metadata.pin(raw))
            completion_check.assert_not_called()


if __name__ == '__main__':
    unittest.main()
