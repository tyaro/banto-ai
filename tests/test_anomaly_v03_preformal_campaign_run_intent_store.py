"""The invented run-budget request is externally pinned before any native run."""
from pathlib import Path
import copy
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_preformal_campaign_controller as controller
from banto_ai import anomaly_v03_preformal_campaign_metadata as metadata
from banto_ai import anomaly_v03_preformal_campaign_run_intent_store as intent
from tests.test_anomaly_v03_preformal_campaign_metadata import _plan


def example(repo):
    original = _plan()
    plan = metadata.fixed_plan(
        original['campaign_id'],
        str(repo / 'artifacts' / 'anomaly-v03-preformal-campaign-aaaaaaaa'),
        original['path_code'], original['registry_pin'], original['source'],
        original['runtime_candidate'], original['budget_candidate'])
    plan_raw = metadata.encode_plan(plan)
    plan_pin = metadata.pin(plan_raw)
    manifest_raw = v.canonical_json({
        'root': metadata.attempt_root(plan, 0, 1), 'chunk_index': 0,
        'invented_only': True,
        'actual_registered_observations_read': False,
        'formal_permission': False,
    })
    manifest_pin = metadata.pin(manifest_raw)
    record_raw = metadata.encode_record(metadata.make_record(
        plan_pin, plan_pin['sha256'], 1, 0, 1, 'started',
        metadata.attempt_root(plan, 0, 1), manifest_pin,
        source_revision=plan['source']['revision'],
        runtime_tuple_sha256=plan['runtime_candidate']['tuple_sha256']))
    record_pin = metadata.pin(record_raw)
    control_root = str(repo / 'artifacts' /
                       'anomaly-v03-preformal-campaign-control-aaaaaaaa')
    initial_pin = metadata.pin(b'initial checkpoint')
    next_pin = metadata.pin(b'next checkpoint')
    intention_pin = metadata.pin(b'prepare intention')
    receipt_raw = v.canonical_json({
        'status': 'prepared', 'reason': None,
        'campaign_root': plan['root'], 'control_root': control_root,
        'anchor_pin': plan_pin, 'checkpoint_pin': initial_pin,
        'intention_pin': intention_pin,
        'manifest_pin': manifest_pin,
        'direct_cli_exit_code': 0, 'direct_cli_exit_confirmed': True,
        'direct_cli_pid': 42, 'direct_cli_start_token': 'a' * 64,
        'next_stage_authorized': False, 'retry_authorized': False,
        'actual_registered_observations_read': False,
        'campaign_evaluations_credited': 0,
        'formal_permission': False,
        'campaign_coherence_authenticated': False,
    }) + b'\n'
    receipt_pin = metadata.pin(receipt_raw)
    state = {
        'campaign_root': plan['root'], 'control_root': control_root,
        'plan_raw': plan_raw, 'plan_pin': plan_pin,
        'record_raws': [record_raw],
        'checkpoint': {'record_count': 1,
                       'head_sha256': record_pin['sha256']},
        'manifest_raw': manifest_raw, 'manifest_pin': manifest_pin,
        'prepare_receipt_raw': receipt_raw,
        'prepare_receipt_pin': receipt_pin,
        'started_record_pin': record_pin,
        'next_checkpoint_pin': next_pin,
        'initial_checkpoint_pin': initial_pin,
        'intention_pin': intention_pin,
        'campaign_coherence_authenticated': False,
        'formal_permission': False,
    }
    request = {
        'format': controller.REQUEST_FORMAT, 'phase': 'run-budget',
        'anchor_pin': plan_pin, 'journal_count': 1,
        'journal_head_sha256': record_pin['sha256'],
        'chunk_index': 0, 'attempt': 1,
        'attempt_root': metadata.attempt_root(plan, 0, 1),
        'reread_root': str(repo / 'artifacts' /
                             'anomaly-v03-preformal-saved-row-reread-h001'),
        'manifest_pin': manifest_pin,
        'generation_receipt_pin': None, 'outer_result_pin': None,
        'invented_only': True,
        'actual_registered_observations_read': False,
        'campaign_evaluations_credited': 0,
        'formal_permission': False,
    }
    campaign = Path(plan['root'])
    (campaign / 'intents').mkdir(parents=True)
    (campaign / 'pending').mkdir()
    (campaign / 'journal').mkdir()
    (campaign / 'plan.json').write_bytes(plan_raw)
    return state, request


class RunIntentStoreTests(unittest.TestCase):
    def _inputs(self, state):
        return {
            'expected_plan_pin': state['plan_pin'],
            'expected_initial_checkpoint_pin':
                state['initial_checkpoint_pin'],
            'expected_intention_pin': state['intention_pin'],
            'expected_prepare_receipt_pin': state['prepare_receipt_pin'],
            'expected_started_record_pin': state['started_record_pin'],
            'expected_next_checkpoint_pin': state['next_checkpoint_pin'],
        }

    def test_create_and_verify_exact_external_request_pin(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            state, request = example(repo)
            with patch.object(intent, 'ROOT', repo), \
                 patch.object(intent.store, '_live_matches'), \
                 patch.object(intent.store, 'verify_started_store',
                              return_value=state, create=True) as verified, \
                 patch.object(intent.controller, 'fixed_request',
                              return_value=request):
                result = intent.create_request(
                    state['campaign_root'], state['control_root'],
                    **self._inputs(state))
                repeated = intent.verify_request(
                    state['campaign_root'], state['control_root'],
                    expected_pin_control_pin=result['pin_control_pin'],
                    **self._inputs(state))
            self.assertEqual(result, repeated)
            self.assertEqual(result['status'], 'run_budget_request_pinned')
            self.assertFalse(result['native_run_started'])
            self.assertFalse(result['campaign_coherence_authenticated'])
            self.assertEqual(result['campaign_evaluations_credited'], 0)
            self.assertFalse(result['formal_permission'])
            self.assertEqual(verified.call_count, 5)
            request_path = Path(result['request_path'])
            self.assertEqual(metadata.pin(request_path.read_bytes()),
                             result['request_pin'])
            self.assertFalse((Path(state['campaign_root']) / 'pending' /
                              '0001-run-budget.json').exists())

    def test_changed_request_or_external_pin_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            state, request = example(repo)
            with patch.object(intent, 'ROOT', repo), \
                 patch.object(intent.store, '_live_matches'), \
                 patch.object(intent.store, 'verify_started_store',
                              return_value=state, create=True), \
                 patch.object(intent.controller, 'fixed_request',
                              return_value=request):
                result = intent.create_request(
                    state['campaign_root'], state['control_root'],
                    **self._inputs(state))
                Path(result['request_path']).write_bytes(b'changed request\n')
                with self.assertRaises(ValueError):
                    intent.verify_request(
                        state['campaign_root'], state['control_root'],
                        expected_pin_control_pin=result['pin_control_pin'],
                        **self._inputs(state))
                Path(result['request_path']).write_bytes(
                    controller.encode_request(request))
                Path(result['pin_control_path']).write_bytes(b'changed pin\n')
                with self.assertRaises(ValueError):
                    intent.verify_request(
                        state['campaign_root'], state['control_root'],
                        expected_pin_control_pin=result['pin_control_pin'],
                        **self._inputs(state))

    def test_existing_pin_root_or_failed_started_state_never_writes_request(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            state, request = example(repo)
            root = (repo / 'artifacts' /
                    'anomaly-v03-preformal-campaign-run-intent-aaaaaaaa')
            root.mkdir()
            with patch.object(intent, 'ROOT', repo), \
                 patch.object(intent.store, '_live_matches'), \
                 patch.object(intent.store, 'verify_started_store',
                              return_value=state, create=True), \
                 patch.object(intent.controller, 'fixed_request',
                              return_value=request):
                with self.assertRaisesRegex(ValueError, 'new external run-budget pin root'):
                    intent.create_request(state['campaign_root'],
                                          state['control_root'],
                                          **self._inputs(state))
            self.assertFalse((Path(state['campaign_root']) / 'intents' /
                              '0001-run-budget.json').exists())
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            state, request = example(repo)
            bad = copy.deepcopy(state)
            bad['prepare_receipt_raw'] = v.canonical_json({'status': 'failed'})
            with patch.object(intent, 'ROOT', repo), \
                 patch.object(intent.store, '_live_matches'), \
                 patch.object(intent.store, 'verify_started_store',
                              return_value=bad, create=True), \
                 patch.object(intent.controller, 'fixed_request',
                              return_value=request):
                with self.assertRaises(ValueError):
                    intent.create_request(state['campaign_root'],
                                          state['control_root'],
                                          **self._inputs(state))
            self.assertFalse((Path(state['campaign_root']) / 'intents' /
                              '0001-run-budget.json').exists())

    def test_stale_live_store_rejection_precedes_any_request_write(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            state, request = example(repo)
            with patch.object(intent, 'ROOT', repo), \
                 patch.object(intent.store, 'verify_started_store',
                              side_effect=ValueError('stale clean source'),
                              create=True):
                with self.assertRaisesRegex(ValueError, 'stale clean source'):
                    intent.create_request(state['campaign_root'],
                                          state['control_root'],
                                          **self._inputs(state))
            self.assertFalse((Path(state['campaign_root']) / 'intents' /
                              '0001-run-budget.json').exists())

    def test_partial_publication_stays_visible_and_cannot_be_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            state, request = example(repo)
            with patch.object(intent, 'ROOT', repo), \
                 patch.object(intent.store, '_live_matches'), \
                 patch.object(intent.store, 'verify_started_store',
                              return_value=state, create=True), \
                 patch.object(intent.controller, 'fixed_request',
                              return_value=request), \
                 patch.object(intent.io, '_rename_no_replace',
                              side_effect=OSError('publish interrupted')):
                with self.assertRaisesRegex(OSError, 'publish interrupted'):
                    intent.create_request(state['campaign_root'],
                                          state['control_root'],
                                          **self._inputs(state))
            pin_root = (repo / 'artifacts' /
                        'anomaly-v03-preformal-campaign-run-intent-aaaaaaaa')
            self.assertTrue(pin_root.exists())
            self.assertTrue((Path(state['campaign_root']) / 'pending' /
                             '0001-run-budget.json').exists())
            with patch.object(intent, 'ROOT', repo), \
                 patch.object(intent.store, '_live_matches'), \
                 patch.object(intent.store, 'verify_started_store',
                              return_value=state, create=True), \
                 patch.object(intent.controller, 'fixed_request',
                              return_value=request):
                with self.assertRaises(ValueError):
                    intent.create_request(state['campaign_root'],
                                          state['control_root'],
                                          **self._inputs(state))
