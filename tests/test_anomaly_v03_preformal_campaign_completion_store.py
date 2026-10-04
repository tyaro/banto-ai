"""One invented completed declaration; crash gaps retain incomplete state."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_preformal_campaign_completion_store as store
from banto_ai import anomaly_v03_preformal_campaign_metadata as metadata
from tests.test_anomaly_v03_preformal_campaign_metadata import _plan
from tests._anomaly_v03_preformal_campaign_test_paths import PortableCampaignPaths


class CompletionStoreTests(PortableCampaignPaths):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            dir=Path(store.__file__).resolve().parents[2])
        self.addCleanup(self.temp.cleanup)
        artifacts = Path(self.temp.name) / 'artifacts'
        artifacts.mkdir()
        base = _plan()
        self.campaign = artifacts / 'anomaly-v03-preformal-campaign-ffffffff'
        self.control = artifacts / 'anomaly-v03-preformal-campaign-control-ffffffff'
        self.campaign.mkdir()
        self.control.mkdir()
        (self.campaign / 'pending').mkdir()
        (self.campaign / 'journal').mkdir()
        (self.campaign / 'intents').mkdir()
        for name in ('0001-run-budget.json', '0001-saved-reread.json'):
            (self.campaign / 'intents' / name).write_bytes(b'{}\n')
        for name in ('anchor-pin.json', 'checkpoint.json',
                     'preflight-intention.json',
                     'preflight-intention-pin.json',
                     'checkpoint-000001.json'):
            (self.control / name).write_bytes(b'{}\n')
        (self.campaign / 'control' / '000-1' / 'run-budget').mkdir(parents=True)
        (self.campaign / 'control' / '000-1' / 'saved-reread').mkdir(parents=True)
        self.plan = metadata.fixed_plan(
            'f' * 64, str(self.campaign), 'h', base['registry_pin'],
            base['source'], base['runtime_candidate'], base['budget_candidate'])
        self.plan_raw = metadata.encode_plan(self.plan)
        self.plan_pin = metadata.pin(self.plan_raw)
        (self.campaign / 'plan.json').write_bytes(self.plan_raw)
        self.manifest_pin = metadata.pin(b'manifest')
        self.started = metadata.make_record(
            self.plan_pin, self.plan_pin['sha256'], 1, 0, 1, 'started',
            metadata.attempt_root(self.plan, 0, 1), self.manifest_pin,
            source_revision=self.plan['source']['revision'],
            runtime_tuple_sha256=self.plan['runtime_candidate']['tuple_sha256'])
        self.started_raw = metadata.encode_record(self.started)
        self.started_pin = metadata.pin(self.started_raw)
        (self.campaign / 'journal' / '000001.json').write_bytes(self.started_raw)
        pins = {name: metadata.pin(name.encode())
                for name in metadata._output_names(0)}
        pins['saved/registry.json'] = self.plan['registry_pin']
        evidence = {name: metadata.pin(name.encode())
                    for name in metadata.EVIDENCE_NAMES}
        evidence['fresh_reread_rows'] = evidence['rows']
        for label, name in (
            ('saved_receipt', 'saved/receipt.json'),
            ('saved_report', 'saved/report.json'),
            ('saved_savepoint', 'saved/savepoint.json'),
            ('saved_registry', 'saved/registry.json'),
        ):
            evidence[label] = pins[name]
        completed = metadata.make_record(
            self.plan_pin, self.started_pin['sha256'], 2, 0, 1,
            'completed', self.started['attempt_root'], self.manifest_pin,
            source_revision=self.plan['source']['revision'],
            runtime_tuple_sha256=self.plan['runtime_candidate']['tuple_sha256'],
            evidence_pins=evidence, saved_output_pins=pins)
        self.completed_raw = metadata.encode_record(completed)
        self.generation_pin = metadata.pin(b'run receipt')
        (self.campaign / 'control' / '000-1' / 'run-budget' /
         'receipt.json').write_bytes(b'run receipt')
        reread = {
            'status': 'verified', 'phase': 'saved-reread',
            'actual_registered_observations_read': False,
            'campaign_evaluations_credited': 0, 'formal_permission': False,
        }
        self.reread_raw = v.canonical_json(reread) + b'\n'
        self.reread_pin = metadata.pin(self.reread_raw)
        (self.campaign / 'control' / '000-1' / 'saved-reread' /
         'receipt.json').write_bytes(self.reread_raw)
        for phase in ('run-budget', 'saved-reread'):
            for name in ('report.json', 'stderr.json', 'supervision.json'):
                (self.campaign / 'control' / '000-1' / phase /
                 name).write_bytes(b'')
        self.pins = {
            'expected_plan_pin': self.plan_pin,
            'expected_initial_checkpoint_pin': metadata.pin(b'initial'),
            'expected_intention_pin': metadata.pin(b'intention'),
            'expected_prepare_receipt_pin': metadata.pin(b'prepare'),
            'expected_started_record_pin': self.started_pin,
            'expected_next_checkpoint_pin': metadata.pin(b'checkpoint1'),
            'expected_run_pin_control_pin': metadata.pin(b'run control'),
            'expected_generation_receipt_pin': self.generation_pin,
            'expected_reread_pin_control_pin': metadata.pin(b'reread control'),
            'expected_reread_receipt_pin': self.reread_pin,
        }
        self.state = {
            'campaign_root': str(self.campaign),
            'control_root': str(self.control),
            'plan_raw': self.plan_raw, 'plan_pin': self.plan_pin,
            'record_raws': [self.started_raw],
            'checkpoint': {'record_count': 1,
                           'head_sha256': self.started_pin['sha256']},
            'generation_receipt_pin': self.generation_pin,
            'campaign_coherence_authenticated': False,
            'formal_permission': False,
        }

    def _append(self):
        return store.append_completed(self.campaign, self.control,
                                      **self.pins)

    def _verify(self, completed_pin, checkpoint_pin):
        return store.verify_completed(
            self.campaign, self.control,
            expected_completed_record_pin=completed_pin,
            expected_terminal_checkpoint_pin=checkpoint_pin,
            **self.pins)

    def test_one_completion_is_immutable_partial_metadata_only(self):
        with patch.object(store, '_stage', return_value=self.state), \
             patch.object(store.controller, 'completion_record',
                          return_value=self.completed_raw):
            result = self._append()
            reread = self._verify(result['completed_record_pin'],
                                  result['terminal_checkpoint_pin'])
            with self.assertRaises(ValueError):
                self._append()
        self.assertEqual(result['checkpoint']['record_count'], 2)
        self.assertEqual(result['checkpoint']['head_sha256'],
                         metadata.pin(self.completed_raw)['sha256'])
        self.assertEqual(reread['declared_completed_chunks'], 1)
        self.assertEqual(reread['declared_completed_evaluations'], 6)
        self.assertEqual(len(reread['missing_chunk_indices']), 479)
        self.assertFalse(reread['campaign_coherence_authenticated'])
        self.assertFalse(reread['formal_permission'])
        self.assertEqual(reread['campaign_evaluations_credited'], 0)
        self.assertEqual(list((self.campaign / 'pending').iterdir()), [])

    def test_record_committed_checkpoint_missing_blocks_retry_and_verification(self):
        original = store.io._exclusive

        def fail_checkpoint(path, raw):
            if Path(path).name == store.CHECKPOINT_NAME:
                raise OSError('simulated external checkpoint failure')
            return original(path, raw)

        with patch.object(store, '_stage', return_value=self.state), \
             patch.object(store.controller, 'completion_record',
                          return_value=self.completed_raw):
            with patch.object(store.io, '_exclusive',
                              side_effect=fail_checkpoint):
                with self.assertRaises(OSError):
                    self._append()
            self.assertTrue((self.campaign / 'journal' /
                             store.RECORD_NAME).exists())
            self.assertFalse((self.control / store.CHECKPOINT_NAME).exists())
            with self.assertRaises(ValueError):
                self._append()
            with self.assertRaises(ValueError):
                self._verify(metadata.pin(self.completed_raw),
                             metadata.pin(b'missing'))

    def test_wrong_reread_receipt_or_terminal_pin_is_rejected(self):
        with patch.object(store, '_stage', return_value=self.state), \
             patch.object(store.controller, 'completion_record',
                          return_value=self.completed_raw):
            wrong = dict(self.pins)
            wrong['expected_reread_receipt_pin'] = metadata.pin(b'wrong')
            with self.assertRaises(ValueError):
                store.append_completed(self.campaign, self.control, **wrong)
            self.assertFalse((self.campaign / 'journal' /
                              store.RECORD_NAME).exists())
            result = self._append()
            with self.assertRaises(ValueError):
                self._verify(metadata.pin(b'wrong'),
                             result['terminal_checkpoint_pin'])
            with self.assertRaises(ValueError):
                self._verify(result['completed_record_pin'],
                             metadata.pin(b'wrong'))
            checkpoint_path = self.control / store.CHECKPOINT_NAME
            changed = v.strict_json(checkpoint_path.read_bytes())
            changed['head_sha256'] = '0' * 64
            checkpoint_path.write_bytes(v.canonical_json(changed) + b'\n')
            with self.assertRaises(ValueError):
                self._verify(result['completed_record_pin'],
                             metadata.pin(checkpoint_path.read_bytes()))

    def test_final_inventory_and_receipt_readback_reject_late_change(self):
        with patch.object(store, '_stage', return_value=self.state), \
             patch.object(store.controller, 'completion_record',
                          return_value=self.completed_raw):
            result = self._append()
            extra = self.campaign / 'intents' / 'unexpected.json'
            extra.write_bytes(b'{}\n')
            with self.assertRaises(ValueError):
                self._verify(result['completed_record_pin'],
                             result['terminal_checkpoint_pin'])
            extra.unlink()
            receipt = (self.campaign / 'control' / '000-1' /
                       'saved-reread' / 'receipt.json')
            receipt.write_bytes(b'changed')
            with self.assertRaises(ValueError):
                self._verify(result['completed_record_pin'],
                             result['terminal_checkpoint_pin'])


if __name__ == '__main__':
    unittest.main()
