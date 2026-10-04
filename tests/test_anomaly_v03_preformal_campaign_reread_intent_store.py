"""Generated attempt remains present while a fresh reread intent is fixed."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_preformal_campaign_controller as controller
from banto_ai import anomaly_v03_preformal_campaign_metadata as metadata
from banto_ai import anomaly_v03_preformal_campaign_preflight as preflight
from banto_ai import anomaly_v03_preformal_campaign_reread_intent_store as intent
from banto_ai import anomaly_v03_preformal_campaign_run_intent_store as run_intent
from banto_ai import anomaly_v03_preformal_campaign_store as store
from tests.test_anomaly_v03_preformal_campaign_metadata import _plan
from tests._anomaly_v03_preformal_campaign_test_paths import PortableCampaignPaths


def _save(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return metadata.pin(raw)


def example(repo):
    original = _plan()
    artifacts = repo / 'artifacts'
    artifacts.mkdir()
    campaign = artifacts / 'anomaly-v03-preformal-campaign-aaaaaaaa'
    controls = artifacts / 'anomaly-v03-preformal-campaign-control-aaaaaaaa'
    plan = metadata.fixed_plan(
        original['campaign_id'], str(campaign), original['path_code'],
        original['registry_pin'], original['source'],
        original['runtime_candidate'], original['budget_candidate'])
    plan_raw = metadata.encode_plan(plan)
    plan_pin = _save(campaign / 'plan.json', plan_raw)
    anchor_raw = store._lf(store._anchor(plan, plan_pin))
    _save(controls / 'anchor-pin.json', anchor_raw)
    initial_pin = _save(controls / 'checkpoint.json',
                        store._lf(store._checkpoint(plan_pin)))
    intention = preflight.make_intention(plan_raw, plan_pin, 0, 1,
                                          intent.sys.executable)
    intention_pin = _save(controls / 'preflight-intention.json',
                          preflight.encode_intention(intention))
    _save(controls / 'preflight-intention-pin.json',
          store._lf(store._intention_pin(plan_pin, intention_pin)))
    manifest_raw = v.canonical_json({'mock': 'manifest'})
    manifest_pin = metadata.pin(manifest_raw)
    prepare_pin = metadata.pin(b'prepared receipt\n')
    record_raw = controller.next_started_record(
        plan_raw, plan_pin, [], expected_record_count=0,
        expected_head_sha256=plan_pin['sha256'], manifest_pin=manifest_pin)
    record_pin = _save(campaign / 'journal' / '000001.json', record_raw)
    next_pin = _save(controls / 'checkpoint-000001.json',
                     store._lf(store._started_checkpoint(
                         plan_pin, initial_pin, intention_pin, prepare_pin,
                         record_pin)))
    (campaign / 'pending').mkdir()
    (campaign / 'intents').mkdir()
    run_control = campaign / 'control' / '000-1' / 'run-budget'
    run_control.mkdir(parents=True)
    for name in ('report.json', 'stderr.json', 'supervision.json'):
        _save(run_control / name, b'{}')
    outer_pin = metadata.pin(b'outer')
    generation = {
        'status': 'verified', 'request_pin': None,
        'formal_permission': False,
        'campaign_coherence_authenticated': False,
        'campaign_evaluations_credited': 0,
        'inner': {'outer_result_pin': outer_pin},
    }
    attempt = Path(metadata.attempt_root(plan, 0, 1))
    attempt.mkdir(parents=True)
    _save(attempt / 'owned-generator' / 'result.json', b'outer')
    reread = artifacts / 'anomaly-v03-preformal-saved-row-reread-h001'
    manifest_path = artifacts / 'anomaly-v03-preformal-generated-pinsets-h001' / 'pins.json'
    run_request = {
        'phase': 'run-budget', 'attempt_root': str(attempt),
        'manifest_path': str(manifest_path), 'reread_root': str(reread),
        'outer_result_pin': None, 'generation_receipt_pin': None,
    }
    run_request_pin = _save(campaign / 'intents' / '0001-run-budget.json',
                            controller.encode_request(run_request))
    generation['request_pin'] = run_request_pin
    generation_raw = v.canonical_json(generation) + b'\n'
    generation_pin = _save(run_control / 'receipt.json', generation_raw)
    checkpoint = v.strict_json((controls / 'checkpoint-000001.json').read_bytes())
    run_state = {
        'control_root': str(controls), 'plan_pin': plan_pin,
        'initial_checkpoint_pin': initial_pin, 'intention_pin': intention_pin,
        'prepare_receipt_pin': prepare_pin, 'manifest_pin': manifest_pin,
        'started_record_pin': record_pin, 'next_checkpoint_pin': next_pin,
        'checkpoint': checkpoint,
    }
    run_pin_root = artifacts / 'anomaly-v03-preformal-campaign-run-intent-aaaaaaaa'
    run_pin_root.mkdir()
    run_control_raw = v.canonical_json(
        run_intent._control(plan, run_state, run_request_pin)) + b'\n'
    run_control_pin = _save(run_pin_root / 'request-pin.json', run_control_raw)
    _save(run_pin_root / 'request-pin.json.sha256',
          (run_control_pin['sha256'] + '\n').encode('ascii'))
    reread_request = {
        'phase': 'saved-reread', 'attempt_root': str(attempt),
        'manifest_path': str(manifest_path), 'reread_root': str(reread),
        'outer_result_pin': outer_pin, 'generation_receipt_pin': generation_pin,
    }
    pins = dict(
        expected_plan_pin=plan_pin,
        expected_initial_checkpoint_pin=initial_pin,
        expected_intention_pin=intention_pin,
        expected_prepare_receipt_pin=prepare_pin,
        expected_started_record_pin=record_pin,
        expected_next_checkpoint_pin=next_pin,
        expected_run_pin_control_pin=run_control_pin,
        expected_generation_receipt_pin=generation_pin)
    owner = {'manifest_raw': manifest_raw, 'manifest_pin': manifest_pin}
    return campaign, controls, pins, owner, generation, run_request, reread_request


class RereadIntentTests(PortableCampaignPaths):
    def _mocks(self, repo, owner, generation, run_request, reread_request):
        def fixed(*_args, phase, **_kwargs):
            return run_request if phase == 'run-budget' else reread_request
        return (
            patch.object(intent, 'ROOT', repo),
            patch.object(intent.store, 'ROOT', repo),
            patch.object(intent.store, '_live_matches'),
            patch.object(intent.store, '_prepared_owner', return_value=owner),
            patch.object(intent.controller, '_manifest'),
            patch.object(intent.controller, 'fixed_request', side_effect=fixed),
            patch.object(intent.controller, '_load_receipt',
                         return_value=generation),
            patch.object(intent.controller, '_verified_inputs'),
            patch.object(intent.controller, '_verified_inputs_before_or_after'),
        )

    def test_create_verify_and_owned_entry_reopen_all_pins(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            fixture = example(repo)
            campaign, controls, pins, owner, generation, run, reread = fixture
            mocks = self._mocks(repo, owner, generation, run, reread)
            with (mocks[0], mocks[1], mocks[2], mocks[3] as prepared,
                  mocks[4], mocks[5], mocks[6], mocks[7], mocks[8],
                  patch.object(intent.controller, 'execute_owned',
                               return_value=({'status': 'verified'},
                                             metadata.pin(b'receipt')))
                  as launched):
                result = intent.create_request(campaign, controls, **pins)
                self.assertEqual(result, intent.verify_request(
                    campaign, controls,
                    expected_pin_control_pin=result['pin_control_pin'],
                    **pins))
                self.assertEqual(intent.execute_request(
                    campaign, controls,
                    expected_pin_control_pin=result['pin_control_pin'],
                    **pins)[0]['status'], 'verified')
            self.assertEqual(result['status'], 'saved_reread_request_pinned')
            self.assertEqual(result['generation_receipt_pin'],
                             pins['expected_generation_receipt_pin'])
            self.assertEqual(prepared.call_args.kwargs,
                             {'require_attempt_absent': False})
            self.assertTrue(launched.called)
            self.assertEqual(launched.call_args.kwargs['expected_record_count'], 1)
            self.assertFalse(result['formal_permission'])
            self.assertEqual(result['campaign_evaluations_credited'], 0)
            self.assertFalse((campaign / 'pending' /
                              '0001-saved-reread.json').exists())

    def test_changed_run_control_or_receipt_blocks_publication(self):
        for target in ('run-control', 'generation-receipt'):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as directory:
                repo = Path(directory)
                campaign, controls, pins, owner, generation, run, reread = example(repo)
                if target == 'run-control':
                    path = (repo / 'artifacts' /
                            'anomaly-v03-preformal-campaign-run-intent-aaaaaaaa' /
                            'request-pin.json.sha256')
                else:
                    path = campaign / 'control' / '000-1' / 'run-budget' / 'receipt.json'
                path.write_bytes(b'changed\n')
                mocks = self._mocks(repo, owner, generation, run, reread)
                with (mocks[0], mocks[1], mocks[2], mocks[3], mocks[4],
                      mocks[5], mocks[6], mocks[7], mocks[8]):
                    with self.assertRaises(ValueError):
                        intent.create_request(campaign, controls, **pins)
                self.assertFalse((campaign / 'intents' /
                                  '0001-saved-reread.json').exists())

    def test_partial_pin_root_and_pending_block_reuse(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            campaign, controls, pins, owner, generation, run, reread = example(repo)
            mocks = self._mocks(repo, owner, generation, run, reread)
            with (mocks[0], mocks[1], mocks[2], mocks[3], mocks[4],
                  mocks[5], mocks[6], mocks[7], mocks[8],
                  patch.object(intent.io, '_rename_no_replace',
                               side_effect=OSError('interrupted'))):
                with self.assertRaisesRegex(OSError, 'interrupted'):
                    intent.create_request(campaign, controls, **pins)
            self.assertTrue((campaign / 'pending' /
                             '0001-saved-reread.json').exists())
            self.assertTrue((repo / 'artifacts' /
                             'anomaly-v03-preformal-campaign-reread-intent-aaaaaaaa').exists())
            mocks = self._mocks(repo, owner, generation, run, reread)
            with (mocks[0], mocks[1], mocks[2], mocks[3], mocks[4],
                  mocks[5], mocks[6], mocks[7], mocks[8]):
                with self.assertRaises(ValueError):
                    intent.create_request(campaign, controls, **pins)

    def test_stale_source_and_changed_saved_pin_block_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            campaign, controls, pins, owner, generation, run, reread = example(repo)
            mocks = self._mocks(repo, owner, generation, run, reread)
            with (mocks[0], mocks[1],
                  patch.object(intent.store, '_live_matches',
                               side_effect=ValueError('stale source')),
                  mocks[3], mocks[4], mocks[5], mocks[6], mocks[7], mocks[8]):
                with self.assertRaisesRegex(ValueError, 'stale source'):
                    intent.create_request(campaign, controls, **pins)
            self.assertFalse((campaign / 'intents' /
                              '0001-saved-reread.json').exists())
            mocks = self._mocks(repo, owner, generation, run, reread)
            with (mocks[0], mocks[1], mocks[2], mocks[3], mocks[4],
                  mocks[5], mocks[6], mocks[7], mocks[8]):
                result = intent.create_request(campaign, controls, **pins)
            pin_sidecar = (repo / 'artifacts' /
                           'anomaly-v03-preformal-campaign-reread-intent-aaaaaaaa' /
                           'request-pin.json.sha256')
            pin_sidecar.write_bytes(b'wrong\n')
            mocks = self._mocks(repo, owner, generation, run, reread)
            with (mocks[0], mocks[1], mocks[2], mocks[3], mocks[4],
                  mocks[5], mocks[6], mocks[7], mocks[8],
                  patch.object(intent.controller, 'execute_owned') as launch):
                with self.assertRaises(ValueError):
                    intent.execute_request(
                        campaign, controls,
                        expected_pin_control_pin=result['pin_control_pin'],
                        **pins)
                launch.assert_not_called()

    def test_postrun_stage_allows_only_exact_reread_control(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            campaign, controls, pins, owner, generation, run, reread = example(repo)
            mocks = self._mocks(repo, owner, generation, run, reread)
            with (mocks[0], mocks[1], mocks[2], mocks[3], mocks[4],
                  mocks[5], mocks[6], mocks[7], mocks[8]):
                result = intent.create_request(campaign, controls, **pins)
            Path(reread['reread_root']).mkdir()
            phase = campaign / 'control' / '000-1' / 'saved-reread'
            phase.mkdir()
            for name in intent.CONTROL_FILES:
                _save(phase / name, b'{}')
            mocks = self._mocks(repo, owner, generation, run, reread)
            with (mocks[0], mocks[1], mocks[2], mocks[3], mocks[4],
                  mocks[5], mocks[6], mocks[7], mocks[8]):
                state = intent.verify_postrun_stage(
                    campaign, controls,
                    expected_pin_control_pin=result['pin_control_pin'],
                    **pins)
                self.assertEqual(state['record_raws'],
                                 [(campaign / 'journal' / '000001.json').read_bytes()])
                _save(phase / 'extra.json', b'{}')
                with self.assertRaises(ValueError):
                    intent.verify_postrun_stage(
                        campaign, controls,
                        expected_pin_control_pin=result['pin_control_pin'],
                        **pins)

    def test_postrun_completion_inventory_is_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            campaign, controls, pins, owner, generation, run, reread = example(repo)
            mocks = self._mocks(repo, owner, generation, run, reread)
            with (mocks[0], mocks[1], mocks[2], mocks[3], mocks[4],
                  mocks[5], mocks[6], mocks[7], mocks[8]):
                result = intent.create_request(campaign, controls, **pins)
            Path(reread['reread_root']).mkdir()
            phase = campaign / 'control' / '000-1' / 'saved-reread'
            phase.mkdir()
            for name in intent.CONTROL_FILES:
                _save(phase / name, b'{}')
            _save(campaign / 'journal' / '000002.json', b'completed\n')
            _save(controls / 'checkpoint-000002.json', b'checkpoint\n')
            mocks = self._mocks(repo, owner, generation, run, reread)
            with (mocks[0], mocks[1], mocks[2], mocks[3], mocks[4],
                  mocks[5], mocks[6], mocks[7], mocks[8]):
                with self.assertRaises(ValueError):
                    intent.verify_postrun_stage(
                        campaign, controls,
                        expected_pin_control_pin=result['pin_control_pin'],
                        **pins)
                state = intent.verify_postrun_stage(
                    campaign, controls,
                    expected_pin_control_pin=result['pin_control_pin'],
                    allow_completion=True, **pins)
            self.assertEqual(len(state['record_raws']), 1)
            self.assertFalse(state['campaign_coherence_authenticated'])


if __name__ == '__main__':
    unittest.main()
