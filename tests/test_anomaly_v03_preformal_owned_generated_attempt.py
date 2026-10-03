"""Fast gates for the invented owned generator; full native run is explicit."""
from __future__ import annotations

import secrets
import shutil
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_preformal_owned_generated_attempt as generated
from banto_ai import anomaly_v03_registered_saved_summary as saved


class OwnedGeneratedAttemptTests(unittest.TestCase):
    def root(self, suffix=None):
        if suffix is not None:
            return generated.ROOT / 'artifacts' / (generated.fixture.PREFIX + suffix)
        for _ in range(20):
            root = generated.ROOT / 'artifacts' / (
                generated.fixture.PREFIX + 'g' + secrets.token_hex(1))
            if not root.exists():
                return root
        self.fail('short unused generated-attempt root unavailable')

    def pins(self, root):
        pins = {logical: {'bytes': 1, 'sha256': '0' * 64}
                for logical in generated._outputs(root, 0)}
        pins['saved/registry.json']['sha256'] = generated.v.REGISTRY_RAW_SHA256
        return pins

    def test_exact_shared_dataset_output_paths_and_native_length_gate(self):
        root = self.root()
        names = generated._outputs(root, 0)
        self.assertEqual(len(names), 22)
        self.assertEqual(len(set(names.values())), 22)
        self.assertEqual(sum(name.startswith('evaluations/') for name in names), 6)
        self.assertEqual(sum(name.startswith('datasets/') for name in names), 12)
        self.assertEqual(sum(name.startswith('saved/') for name in names), 4)
        self.assertLessEqual(max(len(str(root / physical))
                                 for physical in names.values()),
                             generated.MAX_NATIVE_PATH)
        with self.assertRaisesRegex(ValueError, 'path exceeds native probe bound'):
            generated._outputs(self.root('g' + 'x' * 30), 0)

    def test_external_pin_inventory_bound_and_registry_are_required(self):
        root = self.root()
        pins = self.pins(root)
        self.assertEqual(generated._preflight(root, 0, pins),
                         generated._outputs(root, 0))
        missing = dict(pins)
        missing.pop(next(name for name in missing if name.startswith('datasets/')))
        with self.assertRaisesRegex(ValueError, 'exact externally retained'):
            generated._preflight(root, 0, missing)
        bad_registry = dict(pins)
        bad_registry['saved/registry.json'] = {'bytes': 1, 'sha256': '1' * 64}
        with self.assertRaisesRegex(ValueError, 'frozen generator registry pin'):
            generated._preflight(root, 0, bad_registry)
        over = dict(pins)
        over[next(name for name in over if name.startswith('evaluations/'))] = {
            'bytes': saved.MAX_PAYLOAD + 1, 'sha256': '2' * 64}
        with self.assertRaisesRegex(ValueError, 'generator output pin byte bound'):
            generated._preflight(root, 0, over)

    def test_fixed_hand_recipe_has_no_registered_seed_or_normal_stream(self):
        with patch.object(generated.materializer, 'materialize_pair',
                          side_effect=AssertionError('registered materialize')):
            with patch.object(generated.materializer, 'normal_stream',
                              side_effect=AssertionError('registered normal stream')):
                rows = generated._normal()
                self.assertEqual(next(rows), ('motor-01', 0, {
                    'motor_current': 10.0, 'motor_temperature': 40.0,
                    'conveyor_speed': 5.0, 'vibration_feature': 1.0,
                    'load_proxy': 50.0}))
                self.assertEqual(sum(1 for _ in rows), 17999)

    def test_worker_rejects_missing_invocation_without_creating_output(self):
        with patch.object(generated, 'build_invented_output_bytes',
                          side_effect=AssertionError('generation started')):
            self.assertEqual(generated.worker_main([]), 2)

    def test_bad_prelaunch_pin_retains_failure_without_starting_child(self):
        root = self.root('g' + secrets.token_hex(2))
        root.mkdir()
        try:
            with patch.object(generated.supervisor, 'supervise',
                              side_effect=AssertionError('child launched')):
                result = generated.generate_and_read(
                    root, expected_pins={}, source_snapshots={},
                    expected_revision='0' * 40)
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(result['failed_stage'], 'generator')
            self.assertFalse(result['owned_fixture_generator_executed'])
            self.assertFalse(result['owned_fixture_reader_executed'])
            self.assertEqual((root / 'owned-generator' / 'result.json').read_bytes(),
                             generated.v.canonical_json({
                                 key: value for key, value in result.items()
                                 if key not in ('check_directory', 'result_pin')}))
        finally:
            self.assertEqual(root.parent, generated.ROOT / 'artifacts')
            shutil.rmtree(root)


if __name__ == '__main__':
    unittest.main()
