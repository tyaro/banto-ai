"""Pure prepare receipts for invented campaign slots; no native launch."""
from __future__ import annotations

import copy
import unittest

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_preformal_campaign_metadata as campaign
from banto_ai import anomaly_v03_preformal_campaign_preflight as preflight
from banto_ai import anomaly_v03_preformal_owned_generated_attempt as generated
from banto_ai import anomaly_v03_preformal_owned_saved_attempt as copied
from tests.test_anomaly_v03_preformal_campaign_metadata import _plan


PYTHON = r'C:\Python314\python.exe'


class PreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        original = _plan()
        source = copy.deepcopy(original['source'])
        source['selected_files'].append({
            'path': 'src/banto_ai/another_selected.py',
            'pin': campaign.pin(b'another selected source')})
        cls.plan = campaign.fixed_plan(
            original['campaign_id'], original['root'], original['path_code'],
            original['registry_pin'], source, original['runtime_candidate'],
            original['budget_candidate'])
        cls.plan_raw = campaign.encode_plan(cls.plan)
        cls.plan_pin = campaign.pin(cls.plan_raw)

    def setUp(self):
        self.intention = preflight.make_intention(
            self.plan_raw, self.plan_pin, 0, 1, PYTHON)
        self.intention_raw = preflight.encode_intention(self.intention)
        self.intention_pin = campaign.pin(self.intention_raw)

    def check(self, outcome, **extra):
        raw = preflight.encode_outcome(outcome)
        return preflight.check_preflight(
            self.plan_raw, self.plan_pin, self.intention_raw,
            self.intention_pin, raw, campaign.pin(raw), **extra)

    def _manifest(self):
        pins = {name: campaign.pin(name.encode('utf-8'))
                for name in campaign._output_names(0)}
        pins['saved/registry.json'] = self.plan['registry_pin']
        snapshots = {self.plan['source']['revision']:
                     {name: name.encode('utf-8')
                      for name in generated.SNAPSHOT_FILES}}
        return {
            'format': preflight.MANIFEST_FORMAT,
            'scope': 'invented-registered-format-owned-generator-only',
            'root': self.intention['attempt_root'],
            'revision': self.plan['source']['revision'],
            'chunk_index': 0, 'recipe_id': campaign.RECIPE,
            'source': {**self.plan['source'],
                       'selected_files': list(reversed(
                           self.plan['source']['selected_files']))},
            'source_snapshots': copied._source_snapshots(snapshots),
            'source_snapshot_pins': {
                name: campaign.pin(raw)
                for name, raw in snapshots[self.plan['source']['revision']].items()},
            'output_pins': pins,
            'output_file_count': 22,
            'output_bytes': sum(item['bytes'] for item in pins.values()),
            'invented_only': True,
            'actual_registered_observations_read': False,
            'formal_permission': False,
        }

    def test_exact_prepare_paths_and_arguments_without_launch(self):
        item = self.intention
        self.assertTrue(item['attempt_root'].endswith('-h001'))
        self.assertTrue(item['manifest_path'].endswith(
            r'generated-pinsets-h001\pins.json'))
        self.assertEqual(item['sidecar_path'], item['manifest_path'] + '.sha256')
        self.assertEqual(item['argv'][-2:], ['--chunk-index', '0'])
        self.assertEqual(item['expected_absent_paths'], [
            item['attempt_root'], item['manifest_path'], item['sidecar_path']])
        self.assertFalse(item['launch_authorized'])
        self.assertFalse(item['registered_seed_consumed'])
        for bad in (r'C:\Python314\..\Untrusted\python.exe',
                    r'\\server\share\python.exe'):
            with self.assertRaises(ValueError):
                preflight.make_intention(
                    self.plan_raw, self.plan_pin, 0, 1, bad)

    def test_failure_before_manifest_is_retainable_and_not_launchable(self):
        outcome = preflight.make_outcome(
            self.intention_pin, 'failed', reason='precheck_rejected')
        result = self.check(outcome)
        self.assertEqual(result['state'], 'failed')
        self.assertIsNone(result['manifest_pin'])
        self.assertFalse(result['launch_authorized'])
        self.assertFalse(result['prelaunch_temporality_authenticated'])
        self.assertEqual(result['campaign_evaluations_credited'], 0)
        with self.assertRaises(ValueError):
            self.check(outcome, manifest_raw=b'late manifest')

    def test_declared_success_checks_raw_manifest_and_sidecar_but_not_owner(self):
        raw = v.canonical_json(self._manifest())
        manifest_pin = campaign.pin(raw)
        sidecar = (manifest_pin['sha256'] + '\n').encode('ascii')
        outcome = preflight.make_outcome(
            self.intention_pin, 'prepared', exit_code=0,
            process_observation_pin=campaign.pin(b'owner declaration'),
            manifest_pin=manifest_pin, sidecar_pin=campaign.pin(sidecar))
        result = self.check(outcome, manifest_raw=raw, sidecar_raw=sidecar)
        self.assertEqual(result['state'], 'prepared')
        self.assertFalse(result['prepare_process_authenticated'])
        self.assertFalse(result['launch_authorized'])
        self.assertFalse(result['formal_permission'])
        with self.assertRaises(ValueError):
            self.check(outcome, manifest_raw=raw, sidecar_raw=sidecar[:-1])

    def test_slot_manifest_or_intention_substitution_is_rejected(self):
        manifest = self._manifest()
        manifest['chunk_index'] = 1
        raw = v.canonical_json(manifest)
        sidecar = (campaign.pin(raw)['sha256'] + '\n').encode('ascii')
        outcome = preflight.make_outcome(
            self.intention_pin, 'prepared', exit_code=0,
            process_observation_pin=campaign.pin(b'owner declaration'),
            manifest_pin=campaign.pin(raw), sidecar_pin=campaign.pin(sidecar))
        with self.assertRaises(ValueError):
            self.check(outcome, manifest_raw=raw, sidecar_raw=sidecar)
        altered = copy.deepcopy(self.intention)
        altered['manifest_path'] = altered['manifest_path'].replace('h001', 'h011')
        altered_raw = preflight.encode_intention(altered)
        failed = preflight.make_outcome(
            campaign.pin(altered_raw), 'failed', reason='precheck_rejected')
        failed_raw = preflight.encode_outcome(failed)
        with self.assertRaises(ValueError):
            preflight.check_preflight(
                self.plan_raw, self.plan_pin, altered_raw,
                campaign.pin(altered_raw), failed_raw, campaign.pin(failed_raw))

    def test_missing_or_changed_source_snapshot_is_rejected(self):
        for edit in (
            lambda x: x.update(source_snapshots={}),
            lambda x: x['source_snapshot_pins'].update({
                generated.SNAPSHOT_FILES[0]: campaign.pin(b'changed')}),
        ):
            manifest = self._manifest()
            edit(manifest)
            raw = v.canonical_json(manifest)
            sidecar = (campaign.pin(raw)['sha256'] + '\n').encode('ascii')
            outcome = preflight.make_outcome(
                self.intention_pin, 'prepared', exit_code=0,
                process_observation_pin=campaign.pin(b'owner declaration'),
                manifest_pin=campaign.pin(raw),
                sidecar_pin=campaign.pin(sidecar))
            with self.assertRaises(ValueError):
                self.check(outcome, manifest_raw=raw, sidecar_raw=sidecar)

    def test_registry_pin_and_output_bounds_are_enforced(self):
        for edit in (
            lambda x: x['output_pins'].update({
                'saved/registry.json': campaign.pin(b'other registry')}),
            lambda x: x['output_pins'].update({
                'saved/report.json': {
                    'bytes': 10**10, 'sha256': 'a' * 64}}),
        ):
            manifest = self._manifest()
            edit(manifest)
            manifest['output_bytes'] = sum(
                item['bytes'] for item in manifest['output_pins'].values())
            raw = v.canonical_json(manifest)
            sidecar = (campaign.pin(raw)['sha256'] + '\n').encode('ascii')
            outcome = preflight.make_outcome(
                self.intention_pin, 'prepared', exit_code=0,
                process_observation_pin=campaign.pin(b'owner declaration'),
                manifest_pin=campaign.pin(raw),
                sidecar_pin=campaign.pin(sidecar))
            with self.assertRaises(ValueError):
                self.check(outcome, manifest_raw=raw, sidecar_raw=sidecar)

    def test_external_pin_and_failure_evidence_cannot_be_rewritten(self):
        outcome = preflight.make_outcome(
            self.intention_pin, 'failed', exit_code=2,
            process_observation_pin=campaign.pin(b'failed owner declaration'),
            reason='prepare_exit')
        raw = preflight.encode_outcome(outcome)
        with self.assertRaises(ValueError):
            preflight.check_preflight(
                self.plan_raw, self.plan_pin, self.intention_raw,
                self.intention_pin, raw, campaign.pin(b'wrong external head'))
        outcome['exit_code'] = 0
        with self.assertRaises(ValueError):
            self.check(outcome)
        oversized = b' ' * (campaign.MAX_PLAN_BYTES + 1)
        with self.assertRaises(ValueError):
            preflight.make_intention(
                oversized, campaign.pin(oversized), 0, 1, PYTHON)
        outcome['exit_code'] = 2
        outcome['process_observation_pin'] = None
        with self.assertRaises(ValueError):
            self.check(outcome)


if __name__ == '__main__':
    unittest.main()
