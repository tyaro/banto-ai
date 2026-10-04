"""Owned invented prepare stops on precheck failure and retains its receipt."""
from pathlib import Path
from contextlib import nullcontext
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_preformal_campaign_metadata as metadata
from banto_ai import anomaly_v03_preformal_campaign_prepare_owner as owner
from banto_ai import anomaly_v03_preformal_campaign_preflight as preflight
from tests.test_anomaly_v03_preformal_campaign_preflight import PreflightTests


class PrepareOwnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        PreflightTests.setUpClass()

    def setUp(self):
        self.case = PreflightTests()
        self.case.setUp()
        self.state = {
            'status': 'preflight_intention_fixed',
            'campaign_root': self.case.plan['root'],
            'control_root': self.case.plan['root'].replace(
                'campaign-aaaaaaaa', 'campaign-control-aaaaaaaa'),
            'plan_raw': self.case.plan_raw,
            'plan_pin': self.case.plan_pin,
            'checkpoint_pin': metadata.pin(b'checkpoint'),
            'checkpoint': {'record_count': 0,
                           'head_sha256': self.case.plan_pin['sha256']},
            'intention_raw': self.case.intention_raw,
            'intention_pin': self.case.intention_pin,
            'intention': self.case.intention,
            'invented_only': True, 'formal_permission': False,
        }

    def test_precheck_failure_stops_before_cli_and_retains_closed_outcome(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'owner'
            with patch.object(owner, '_store', side_effect=[
                    self.state, ValueError('target already exists')]), \
                    patch.object(owner, '_owner_root', return_value=target), \
                    patch.object(owner.job_owner, 'supervise_cli') as supervise:
                result, receipt_pin = owner.execute(
                    self.state['campaign_root'], self.state['control_root'],
                    expected_plan_pin=self.state['plan_pin'],
                    expected_checkpoint_pin=self.state['checkpoint_pin'],
                    expected_intention_pin=self.state['intention_pin'])
            supervise.assert_not_called()
            self.assertEqual((result['status'], result['reason']),
                             ('failed', 'precheck_rejected'))
            self.assertIsNone(result['manifest_pin'])
            self.assertFalse(result['next_stage_authorized'])
            self.assertFalse(result['formal_permission'])
            self.assertEqual(metadata.pin((target / 'receipt.json').read_bytes()),
                             receipt_pin)
            self.assertTrue((target / 'outcome.json').exists())
            self.assertTrue((target / 'check.json').exists())

    def test_valid_manifest_success_remains_limited(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            manifest_raw = v.canonical_json(self.case._manifest())
            sidecar_raw = (metadata.pin(manifest_raw)['sha256'] + '\n').encode('ascii')
            claim_pin = metadata.pin(b'claim')
            result, receipt_pin = owner._finish(
                target, self.state, claim_pin, {},
                {'exit_code': 0, 'worker_exit_confirmed': True,
                 'output': metadata.pin(b'prepared'),
                 'stderr': metadata.pin(b'')}, False, None,
                manifest_raw=manifest_raw, sidecar_raw=sidecar_raw)
            self.assertEqual(result['status'], 'prepared')
            self.assertFalse(result['next_stage_authorized'])
            self.assertFalse(result['campaign_coherence_authenticated'])
            self.assertEqual(result['campaign_evaluations_credited'], 0)
            self.assertEqual(metadata.pin((target / 'receipt.json').read_bytes()),
                             receipt_pin)
            self.assertEqual(result['manifest_pin'], metadata.pin(manifest_raw))

    def test_actual_zero_exit_integrity_failure_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            result, _ = owner._finish(
                target, self.state, metadata.pin(b'claim'), {},
                {'exit_code': 0, 'worker_exit_confirmed': True},
                False, 'prepare_integrity')
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(result['direct_cli_exit_code'], 0)
            self.assertIsNone(result['manifest_pin'])
            self.assertFalse(result['retry_authorized'])

    def test_empty_stderr_can_be_verified_by_its_zero_byte_pin(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'stderr.json'
            path.write_bytes(b'')
            self.assertEqual(owner._pinned(path, metadata.pin(b''), 16,
                                           allow_empty=True), b'')
            with self.assertRaises(ValueError):
                owner._pinned(path, metadata.pin(b''), 16)

    def test_deep_manifest_rejection_becomes_saved_integrity_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            manifest = self.case._manifest()
            manifest['output_pins']['saved/registry.json'] = metadata.pin(
                b'wrong registry')
            manifest_raw = v.canonical_json(manifest)
            sidecar_raw = (metadata.pin(manifest_raw)['sha256'] + '\n').encode('ascii')
            result, _ = owner._finish(
                target, self.state, metadata.pin(b'claim'), {},
                {'exit_code': 0, 'worker_exit_confirmed': True}, False, None,
                manifest_raw=manifest_raw, sidecar_raw=sidecar_raw)
            self.assertEqual((result['status'], result['reason']),
                             ('failed', 'prepare_integrity'))
            self.assertEqual(result['direct_cli_exit_code'], 0)
            self.assertTrue((target / 'outcome.json').exists())
            self.assertTrue((target / 'check.json').exists())
            self.assertTrue((target / 'receipt.json').exists())

    def test_timeout_or_zero_exit_monitor_failure_keeps_actual_classification(self):
        for report, wanted in (
            ({'status': 'failed', 'exit_code': -9,
              'stop_reason': 'time_limit', 'worker_exit_confirmed': True,
              'output': None, 'stderr': None}, 'prepare_timeout'),
            ({'status': 'failed', 'exit_code': 0,
              'stop_reason': 'observation_error', 'worker_exit_confirmed': True,
              'output': None, 'stderr': None}, 'prepare_integrity'),
        ):
            with self.subTest(wanted=wanted), tempfile.TemporaryDirectory() as directory:
                target = Path(directory) / 'owner'
                with patch.object(owner, '_store', return_value=self.state), \
                        patch.object(owner, '_owner_root', return_value=target), \
                        patch.object(owner, '_targets_absent'), \
                        patch.object(owner, '_optional', return_value=None), \
                        patch.object(owner.platform, '_platform_scope',
                                     return_value=nullcontext()), \
                        patch.object(owner.job_owner, 'supervise_cli',
                                     return_value=report):
                    result, _ = owner.execute(
                        self.state['campaign_root'], self.state['control_root'],
                        expected_plan_pin=self.state['plan_pin'],
                        expected_checkpoint_pin=self.state['checkpoint_pin'],
                        expected_intention_pin=self.state['intention_pin'])
                self.assertEqual(result['reason'], wanted)
                self.assertFalse(result['next_stage_authorized'])

    def test_execute_rechecks_three_external_pins_at_spawn_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'owner'
            state = dict(self.state)
            intention = preflight.make_intention(
                state['plan_raw'], state['plan_pin'], 0, 1, sys.executable)
            state.update(intention=intention,
                         intention_raw=preflight.encode_intention(intention),
                         intention_pin=metadata.pin(
                             preflight.encode_intention(intention)))
            launch = {'pid': 42, 'creation_time_100ns': 12345,
                      'start_token': 'a' * 64}
            calls = []

            def verified_store(*args, **kwargs):
                self.assertEqual(kwargs['expected_plan_pin'], state['plan_pin'])
                self.assertEqual(kwargs['expected_checkpoint_pin'],
                                 state['checkpoint_pin'])
                self.assertEqual(kwargs['expected_intention_pin'],
                                 state['intention_pin'])
                calls.append(kwargs['require_absent_targets'])
                return state

            def supervised(argv, cwd, control, limits, **kwargs):
                self.assertTrue((target / 'prelaunch-claim.json').exists())
                self.assertEqual(argv, intention['argv'])
                self.assertEqual(limits, owner.LIMITS)
                kwargs['boundary']()
                kwargs['on_started'](SimpleNamespace(pid=42, _handle=object()))
                kwargs['boundary']()
                return {'status': 'failed', 'exit_code': 2,
                        'stop_reason': None, 'worker_pid': 42,
                        'worker_exit_confirmed': True,
                        'output': None, 'stderr': None}

            with patch.object(owner.store, 'verify_store',
                              side_effect=verified_store), \
                    patch.object(owner, '_owner_root', return_value=target), \
                    patch.object(owner, '_targets_absent') as absent, \
                    patch.object(owner, '_optional', side_effect=[
                        b'partial manifest', None]), \
                    patch.object(owner.platform, '_platform_scope',
                                 return_value=nullcontext()), \
                    patch.object(owner.observed, 'creation_observation',
                                 return_value=launch), \
                    patch.object(owner.job_owner, 'supervise_cli',
                                 side_effect=supervised):
                result, _ = owner.execute(
                    state['campaign_root'], state['control_root'],
                    expected_plan_pin=state['plan_pin'],
                    expected_checkpoint_pin=state['checkpoint_pin'],
                    expected_intention_pin=state['intention_pin'])
            self.assertEqual(calls, [True, True, True, False])
            self.assertEqual(absent.call_count, 2)
            self.assertEqual((result['status'], result['reason']),
                             ('failed', 'prepare_exit'))
            self.assertEqual(result['direct_cli_pid'], 42)
            self.assertEqual(result['direct_cli_start_token'], 'a' * 64)
            self.assertEqual(result['manifest_pin'],
                             metadata.pin(b'partial manifest'))
            self.assertIsNone(result['sidecar_pin'])
            self.assertFalse(result['next_stage_authorized'])
            self.assertTrue((target / 'creation-observation.json').exists())
            self.assertTrue((target / 'outcome.json').exists())

    def test_completed_cli_requires_selected_runtime_before_and_after(self):
        launch = {'pid': 42, 'creation_time_100ns': 12345,
                  'start_token': 'a' * 64}
        runtime = self.case.plan['runtime_candidate']['tuple']
        report = {
            'status': 'complete', 'exit_code': 0,
            'worker_exit_confirmed': True, 'worker_pid': 42,
            'argv': self.state['intention']['argv'], 'limits': owner.LIMITS,
            'runtime_before': runtime, 'runtime_after': runtime,
            'observation_errors': [], 'stop_reason': None,
            'job': {
                'format': 'anomaly-v03-preformal-owned-cli-job-v1',
                'assignment_confirmed': True, 'root_resumed': True,
                'all_assigned_processes_exit_confirmed': True,
                'accounting': {'active_processes': 0},
                'memory': {'information_class': 9, 'limit_flags': 0x2000,
                           'peak_process_memory_used_bytes': 1024,
                           'peak_job_memory_used_bytes': 2048},
                'individual_descendant_exit_codes_authenticated': False,
                'whole_tree_resource_budget_measured': False},
        }
        owner._completed_cli(report, launch, self.state['intention'],
                             self.case.plan, b'prepared', b'', b'manifest',
                             b'sidecar')
        changed = dict(report, runtime_after={'changed': True})
        with self.assertRaisesRegex(ValueError, 'owned prepare CLI'):
            owner._completed_cli(changed, launch, self.state['intention'],
                                 self.case.plan, b'prepared', b'',
                                 b'manifest', b'sidecar')
        without_job = dict(report, job={**report['job'],
                                        'all_assigned_processes_exit_confirmed': False})
        with self.assertRaisesRegex(ValueError, 'owned prepare CLI'):
            owner._completed_cli(without_job, launch, self.state['intention'],
                                 self.case.plan, b'prepared', b'',
                                 b'manifest', b'sidecar')
        without_memory = dict(report, job={**report['job'], 'memory': None})
        with self.assertRaisesRegex(ValueError, 'owned prepare CLI'):
            owner._completed_cli(without_memory, launch,
                                 self.state['intention'], self.case.plan,
                                 b'prepared', b'', b'manifest', b'sidecar')

    def test_existing_owner_root_is_not_reused_or_launched(self):
        with patch.object(owner, '_store', return_value=self.state), \
                patch.object(owner, '_owner_root', side_effect=ValueError(
                    'new prepare-owner root required')), \
                patch.object(owner.job_owner, 'supervise_cli') as supervise:
            with self.assertRaisesRegex(ValueError, 'new prepare-owner root'):
                owner.execute(
                    self.state['campaign_root'], self.state['control_root'],
                    expected_plan_pin=self.state['plan_pin'],
                    expected_checkpoint_pin=self.state['checkpoint_pin'],
                    expected_intention_pin=self.state['intention_pin'])
        supervise.assert_not_called()


if __name__ == '__main__':
    unittest.main()
