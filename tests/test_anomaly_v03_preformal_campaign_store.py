"""Durable invented prelaunch metadata; no native child or registered read."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_preformal_campaign_metadata as metadata
from banto_ai import anomaly_v03_preformal_campaign_preflight as preflight
from banto_ai import anomaly_v03_preformal_campaign_store as store
from tests.test_anomaly_v03_preformal_campaign_metadata import _plan
from tests._anomaly_v03_preformal_campaign_test_paths import PortableCampaignPaths

REAL_LIVE_MATCHES = store._live_matches


class StoreTests(PortableCampaignPaths):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=store.ROOT)
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.artifacts = self.repo / 'artifacts'
        self.artifacts.mkdir()
        self.campaign_id = 'f' * 64
        self.campaign = self.artifacts / (
            'anomaly-v03-preformal-campaign-' + self.campaign_id[:8])
        self.control = self.artifacts / (
            'anomaly-v03-preformal-campaign-control-' + self.campaign_id[:8])
        base = _plan()
        self.plan = metadata.fixed_plan(
            self.campaign_id, str(self.campaign), 'd',
            base['registry_pin'], base['source'],
            base['runtime_candidate'], store.BUDGET_CANDIDATE)
        self.patch_root = patch.object(store, 'ROOT', self.repo)
        self.patch_live = patch.object(store, '_live_matches')
        self.patch_root.start()
        self.patch_live.start()
        self.addCleanup(self.patch_live.stop)
        self.addCleanup(self.patch_root.stop)

    def _create(self):
        return store.create_store(self.plan, self.control, sys.executable)

    def _verify(self, created, **overrides):
        args = {
            'expected_plan_pin': created['plan_pin'],
            'expected_checkpoint_pin': created['checkpoint_pin'],
            'expected_intention_pin': created['intention_pin'],
        }
        args.update(overrides)
        return store.verify_store(self.campaign, self.control, **args)

    def _append(self, created):
        return store.append_started(
            self.campaign, self.control,
            expected_plan_pin=created['plan_pin'],
            expected_initial_checkpoint_pin=created['checkpoint_pin'],
            expected_intention_pin=created['intention_pin'],
            expected_prepare_receipt_pin=metadata.pin(b'prepared receipt'))

    def _verify_started(self, created, started, **overrides):
        args = {
            'expected_plan_pin': created['plan_pin'],
            'expected_initial_checkpoint_pin': created['checkpoint_pin'],
            'expected_intention_pin': created['intention_pin'],
            'expected_prepare_receipt_pin': metadata.pin(b'prepared receipt'),
            'expected_started_record_pin': started['started_record_pin'],
            'expected_next_checkpoint_pin': started['next_checkpoint_pin'],
        }
        args.update(overrides)
        return store.verify_started_store(self.campaign, self.control,
                                          **args)

    @staticmethod
    def _fake_owner():
        return {'manifest_raw': b'invented manifest',
                'manifest_pin': metadata.pin(b'invented manifest'),
                'prepare_receipt_raw': b'prepared receipt',
                'prepare_receipt_pin': metadata.pin(b'prepared receipt')}

    def test_fresh_store_is_pinned_empty_journal_with_fixed_slot_zero_intention(self):
        created = self._create()
        self.assertEqual(created['status'], 'preflight_intention_fixed')
        self.assertEqual(created['checkpoint']['record_count'], 0)
        self.assertEqual(created['checkpoint']['head_sha256'],
                         created['plan_pin']['sha256'])
        self.assertEqual(created['intention']['chunk_index'], 0)
        self.assertEqual(created['intention']['attempt'], 1)
        self.assertEqual(created['intention']['anchor_pin'], created['plan_pin'])
        self.assertFalse(created['launch_authorized'])
        self.assertFalse(created['resume_authorized'])
        self.assertFalse(created['campaign_coherence_authenticated'])
        self.assertFalse(created['formal_permission'])
        self.assertEqual(created['campaign_evaluations_credited'], 0)
        self.assertEqual({p.name for p in self.campaign.iterdir()},
                         store.PLAN_FILES)
        self.assertEqual({p.name for p in self.control.iterdir()},
                         store.CONTROL_FILES)
        self.assertEqual(self._verify(created)['intention_pin'],
                         created['intention_pin'])

    def test_existing_root_or_preflight_target_rejected_without_writes(self):
        self.control.mkdir()
        with self.assertRaises(ValueError):
            self._create()
        self.assertFalse(self.campaign.exists())
        self.control.rmdir()
        plan_raw = metadata.encode_plan(self.plan)
        intent = preflight.make_intention(plan_raw, metadata.pin(plan_raw),
                                          0, 1, sys.executable)
        Path(intent['attempt_root']).mkdir()
        try:
            with self.assertRaises(ValueError):
                self._create()
            self.assertFalse(self.campaign.exists())
            self.assertFalse(self.control.exists())
        finally:
            Path(intent['attempt_root']).rmdir()
        later = Path(metadata.attempt_root(self.plan, 1, 1))
        later.mkdir()
        try:
            with self.assertRaises(ValueError):
                self._create()
            self.assertFalse(self.campaign.exists())
        finally:
            later.rmdir()
        pinset = Path(intent['manifest_path']).parent
        pinset.mkdir()
        try:
            with self.assertRaises(ValueError):
                self._create()
            self.assertFalse(self.campaign.exists())
            (pinset / 'pins.json.sha256').write_bytes(b'partial\n')
            with self.assertRaises(ValueError):
                self._create()
            self.assertFalse(self.campaign.exists())
        finally:
            (pinset / 'pins.json.sha256').unlink(missing_ok=True)
            pinset.rmdir()

    def test_mismatched_external_pins_count_head_and_extra_file_fail_closed(self):
        created = self._create()
        wrong = {'bytes': created['plan_pin']['bytes'], 'sha256': '0' * 64}
        with self.assertRaises(ValueError):
            self._verify(created, expected_plan_pin=wrong)
        wrong = {'bytes': created['checkpoint_pin']['bytes'],
                 'sha256': '0' * 64}
        with self.assertRaises(ValueError):
            self._verify(created, expected_checkpoint_pin=wrong)
        checkpoint_path = self.control / 'checkpoint.json'
        original = checkpoint_path.read_bytes()
        for name, value in (('record_count', 1),
                            ('head_sha256', '0' * 64)):
            changed = copy.deepcopy(created['checkpoint'])
            changed[name] = value
            raw = v.canonical_json(changed) + b'\n'
            checkpoint_path.write_bytes(raw)
            with self.assertRaises(ValueError):
                self._verify(created,
                             expected_checkpoint_pin=metadata.pin(raw))
        checkpoint_path.write_bytes(original)
        (self.control / 'extra.json').write_bytes(b'{}')
        with self.assertRaises(ValueError):
            self._verify(created)
        (self.control / 'extra.json').unlink()
        (self.campaign / 'pending' / 'orphan').write_bytes(b'x')
        with self.assertRaises(ValueError):
            self._verify(created)

    def test_live_selected_source_and_runtime_drift_are_rejected(self):
        source = copy.deepcopy(self.plan['source'])
        source['selected_files'][0]['pin']['sha256'] = '0' * 64
        with patch.object(store, '_revision', return_value=self.plan['source']['revision']), \
             patch.object(store, '_selected_source', return_value=source), \
             patch.object(store, '_registry_pin', return_value=self.plan['registry_pin']), \
             patch.object(store, '_runtime_candidate',
                          return_value=self.plan['runtime_candidate']):
            with self.assertRaises(ValueError):
                REAL_LIVE_MATCHES(self.plan)
        runtime = copy.deepcopy(self.plan['runtime_candidate'])
        runtime['tuple']['os_ubr'] += 1
        runtime['tuple_sha256'] = v.canonical_sha256(runtime['tuple'])
        with patch.object(store, '_revision', return_value=self.plan['source']['revision']), \
             patch.object(store, '_selected_source', return_value=self.plan['source']), \
             patch.object(store, '_registry_pin', return_value=self.plan['registry_pin']), \
             patch.object(store, '_runtime_candidate', return_value=runtime):
            with self.assertRaises(ValueError):
                REAL_LIVE_MATCHES(self.plan)
        created = self._create()
        with patch.object(store, '_live_matches', side_effect=ValueError('drift')):
            with self.assertRaises(ValueError):
                self._verify(created)

    def test_forged_repin_of_intention_cannot_change_slot_or_invocation(self):
        created = self._create()
        changed = copy.deepcopy(created['intention'])
        changed['chunk_index'] = 1
        raw = preflight.encode_intention(changed)
        (self.control / 'preflight-intention.json').write_bytes(raw)
        (self.control / 'preflight-intention-pin.json').write_bytes(
            store._lf(store._intention_pin(created['plan_pin'],
                                           metadata.pin(raw))))
        with self.assertRaises(ValueError):
            self._verify(created,
                         expected_intention_pin=metadata.pin(raw))

    def test_partial_creation_is_retained_and_unusable(self):
        original = store.io._exclusive

        def fail_checkpoint(path, raw):
            if Path(path).name == 'checkpoint.json':
                raise OSError('simulated checkpoint write failure')
            return original(path, raw)

        with patch.object(store.io, '_exclusive', side_effect=fail_checkpoint):
            with self.assertRaises(OSError):
                self._create()
        self.assertTrue(self.campaign.exists())
        self.assertTrue(self.control.exists())
        self.assertFalse((self.control / 'checkpoint.json').exists())
        with self.assertRaises(ValueError):
            self._create()
        with self.assertRaises(ValueError):
            store.verify_store(
                self.campaign, self.control,
                expected_plan_pin=metadata.pin(metadata.encode_plan(self.plan)),
                expected_checkpoint_pin=metadata.pin(b'checkpoint'),
                expected_intention_pin=metadata.pin(b'intention'))

    def test_started_append_commits_record_then_external_immutable_checkpoint(self):
        created = self._create()
        original_checkpoint = (self.control / 'checkpoint.json').read_bytes()
        with patch.object(store, '_prepared_owner',
                          return_value=self._fake_owner()):
            started = self._append(created)
            reread = self._verify_started(created, started)
            with self.assertRaises(ValueError):
                self._append(created)
        self.assertEqual(reread['status'], 'started_record_fixed')
        self.assertEqual(reread['checkpoint']['record_count'], 1)
        self.assertEqual(reread['checkpoint']['head_sha256'],
                         started['started_record_pin']['sha256'])
        self.assertEqual(reread['record_raws'], [
            (self.campaign / 'journal' / '000001.json').read_bytes()])
        self.assertEqual((self.control / 'checkpoint.json').read_bytes(),
                         original_checkpoint)
        self.assertEqual(list((self.campaign / 'pending').iterdir()), [])
        self.assertEqual(list((self.campaign / 'intents').iterdir()), [])
        self.assertFalse(started['campaign_coherence_authenticated'])
        self.assertFalse(started['launch_authorized'])
        self.assertFalse(started['formal_permission'])
        self.assertEqual(started['campaign_evaluations_credited'], 0)

    def test_started_checkpoint_gap_stays_partial_and_blocks_every_reader(self):
        created = self._create()
        original = store.io._exclusive

        def fail_checkpoint(path, raw):
            if Path(path).name == 'checkpoint-000001.json':
                raise OSError('simulated external checkpoint failure')
            return original(path, raw)

        with patch.object(store, '_prepared_owner',
                          return_value=self._fake_owner()), \
             patch.object(store.io, '_exclusive', side_effect=fail_checkpoint):
            with self.assertRaises(OSError):
                self._append(created)
        self.assertTrue((self.campaign / 'journal' / '000001.json').exists())
        self.assertFalse((self.control / 'checkpoint-000001.json').exists())
        with patch.object(store, '_prepared_owner',
                          return_value=self._fake_owner()):
            with self.assertRaises(ValueError):
                self._append(created)
            with self.assertRaises(ValueError):
                self._verify(created)
            with self.assertRaises(ValueError):
                store.verify_started_store(
                    self.campaign, self.control,
                    expected_plan_pin=created['plan_pin'],
                    expected_initial_checkpoint_pin=created['checkpoint_pin'],
                    expected_intention_pin=created['intention_pin'],
                    expected_prepare_receipt_pin=metadata.pin(b'prepared receipt'),
                    expected_started_record_pin=metadata.pin(
                        (self.campaign / 'journal' / '000001.json').read_bytes()),
                    expected_next_checkpoint_pin=metadata.pin(b'missing'))

    def test_started_reader_rejects_mismatched_pins_pending_and_stale_source(self):
        created = self._create()
        with patch.object(store, '_prepared_owner',
                          return_value=self._fake_owner()):
            started = self._append(created)
            wrong = {'bytes': started['started_record_pin']['bytes'],
                     'sha256': '0' * 64}
            with self.assertRaises(ValueError):
                self._verify_started(created, started,
                                     expected_started_record_pin=wrong)
            wrong = {'bytes': started['next_checkpoint_pin']['bytes'],
                     'sha256': '0' * 64}
            with self.assertRaises(ValueError):
                self._verify_started(created, started,
                                     expected_next_checkpoint_pin=wrong)
            (self.campaign / 'pending' / 'orphan').write_bytes(b'x')
            with self.assertRaises(ValueError):
                self._verify_started(created, started)
            (self.campaign / 'pending' / 'orphan').unlink()
            with patch.object(store, '_live_matches',
                              side_effect=ValueError('stale source')):
                with self.assertRaises(ValueError):
                    self._verify_started(created, started)

    def test_run_intent_requires_exact_pinned_single_file(self):
        created = self._create()
        with patch.object(store, '_prepared_owner',
                          return_value=self._fake_owner()):
            started = self._append(created)
            request_raw = v.canonical_json({'invented_request': True}) + b'\n'
            (self.campaign / 'intents' / '0001-run-budget.json').write_bytes(
                request_raw)
            with self.assertRaises(ValueError):
                self._verify_started(created, started)
            result = self._verify_started(
                created, started,
                expected_run_intent_pin=metadata.pin(request_raw))
            self.assertEqual(result['run_intent_pin'],
                             metadata.pin(request_raw))
            (self.campaign / 'intents' / 'extra.json').write_bytes(b'{}')
            with self.assertRaises(ValueError):
                self._verify_started(
                    created, started,
                    expected_run_intent_pin=metadata.pin(request_raw))


if __name__ == '__main__':
    unittest.main()
