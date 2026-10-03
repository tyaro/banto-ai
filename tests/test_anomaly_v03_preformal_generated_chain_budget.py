"""Focused safety and stop checks for the invented generated two-role budget."""
from __future__ import annotations

import json
import os
from pathlib import Path
import secrets
import shutil
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_preformal_generated_chain_budget as budget_module


def healthy_system():
    return {
        'commit_total_bytes': 8 * 1024**3,
        'commit_limit_bytes': 24 * 1024**3,
        'commit_headroom_bytes': 16 * 1024**3,
        'free_ram_bytes': 8 * 1024**3,
        'free_disk_bytes': 50 * 1024**3,
        'parent_peak_private_bytes': 128 * 1024**2,
    }


class GeneratedChainBudgetTests(unittest.TestCase):
    def setUp(self):
        parent = budget_module.ROOT / 'artifacts'
        for _ in range(10):
            root = parent / (budget_module.fixture.PREFIX + 'b' +
                             secrets.token_hex(2))
            try:
                root.mkdir()
            except FileExistsError:
                continue
            self.root = root
            self.addCleanup(self._remove_root)
            return
        self.fail('could not allocate dedicated invented budget root')

    def _remove_root(self):
        if not self.root.exists():
            return
        resolved = self.root.resolve(strict=True)
        self.assertEqual(resolved.parent, budget_module.ROOT / 'artifacts')
        self.assertTrue(resolved.name.startswith(budget_module.fixture.PREFIX))
        shutil.rmtree(resolved)

    def test_two_role_report_is_bounded_joined_and_retains_identity(self):
        with patch.object(budget_module.primitives, 'system_snapshot',
                          side_effect=lambda root: healthy_system()):
            budget = budget_module.GeneratedChainBudget(self.root).start()
            try:
                for phase in budget_module.PHASES:
                    budget.checkpoint(phase)
                generator_pin = {'bytes': 100, 'sha256': 'a' * 64}
                reader_pin = {'bytes': 200, 'sha256': 'b' * 64}
                budget.record_role('generator', 'complete', generator_pin,
                                   1234, True)
                budget.record_role('reader', 'complete', reader_pin, 5678,
                                   True)
                with self.assertRaisesRegex(ValueError, 'duplicate or late'):
                    budget.record_role('reader', 'complete', reader_pin, 5678,
                                       True)
            finally:
                report = budget.close()
        self.assertIs(report, budget.close())
        self.assertFalse(budget._thread.is_alive())
        self.assertEqual(report['format'], budget_module.FORMAT)
        self.assertEqual(report['root'], str(self.root))
        self.assertEqual(report['root_identity'], {
            'device': self.root.stat().st_dev,
            'inode': self.root.stat().st_ino,
        })
        self.assertTrue(report['both_owned_exits_reported'])
        self.assertTrue(report['sampler_exit_confirmed'])
        self.assertTrue(report['passed'])
        self.assertEqual([row['phase'] for row in report['phase_log']],
                         list(budget_module.PHASES))
        self.assertEqual(report['caller_reported_roles']['generator']['worker_pid'],
                         1234)
        self.assertEqual(report['caller_reported_roles']['reader']['result_pin'],
                         reader_pin)
        self.assertFalse(report['formal_permission'])
        self.assertFalse(report['actual_registered_observations_read'])
        self.assertEqual(report['campaign_evaluations_credited'], 0)
        self.assertLessEqual(len(json.dumps(report).encode('utf-8')),
                             budget_module.REPORT_MAX_BYTES)

    def test_sampled_directory_limit_latches_before_role_and_closes(self):
        fake_tree = {
            'directory_bytes': budget_module.DEFAULTS['directory_bytes'] -
                               budget_module.RECEIPT_RESERVE_BYTES + 1,
            'directory_entries': 1, 'directory_depth': 1,
        }
        with patch.object(budget_module.primitives, 'system_snapshot',
                          return_value=healthy_system()), \
             patch.object(budget_module, '_directory_snapshot',
                          return_value=fake_tree):
            budget = budget_module.GeneratedChainBudget(self.root).start()
            try:
                self.assertEqual(budget.probe(), 'generated_directory_limit')
                with self.assertRaisesRegex(
                        budget_module.resources.ResourceStop,
                        'generated_directory_limit'):
                    budget.checkpoint('generator')
            finally:
                report = budget.close()
        self.assertEqual(report['stop_reason'], 'generated_directory_limit')
        self.assertFalse(report['passed'])
        self.assertFalse(report['both_owned_exits_reported'])
        self.assertTrue(report['sampler_exit_confirmed'])

    def test_metadata_scan_accepts_deep_saved_path_and_stops_at_bound(self):
        directory = self.root
        for _ in range(11):
            directory = directory / 'd'
            directory.mkdir()
        identity = (self.root.stat().st_dev, self.root.stat().st_ino)
        observed = budget_module._directory_snapshot(self.root, 256, 12,
                                                       identity)
        self.assertEqual(observed['directory_depth'], 11)
        (directory / 'd' / 'd').mkdir(parents=True)
        with self.assertRaisesRegex(budget_module.resources.ResourceStop,
                                    'generated_directory_depth'):
            budget_module._directory_snapshot(self.root, 256, 12, identity)

    def test_metadata_scan_rejects_unsafe_hardlink_and_root_identity_change(self):
        identity = (self.root.stat().st_dev, self.root.stat().st_ino)
        first = self.root / 'first.txt'
        second = self.root / 'second.txt'
        first.write_bytes(b'unsafe')
        try:
            os.link(first, second)
        except OSError as error:
            self.skipTest('filesystem cannot create test hardlink: ' + str(error))
        with self.assertRaisesRegex(budget_module.resources.ResourceStop,
                                    'generated_unsafe_directory'):
            budget_module._directory_snapshot(self.root, 256, 12, identity)
        second.unlink()
        with self.assertRaisesRegex(budget_module.resources.ResourceStop,
                                    'generated_root_changed'):
            budget_module._directory_snapshot(self.root, 256, 12,
                                               (identity[0], identity[1] + 1))

    def test_limits_only_tighten_and_root_is_dedicated(self):
        tight = {**budget_module.DEFAULTS, 'wall_seconds': 300,
                 'directory_bytes': 160 * 1024**2}
        self.assertEqual(budget_module.limits(tight), tight)
        with self.assertRaisesRegex(ValueError, 'may only tighten'):
            budget_module.limits({**budget_module.DEFAULTS,
                                  'directory_bytes': 256 * 1024**2})
        with self.assertRaisesRegex(ValueError, 'dedicated invented'):
            budget_module.GeneratedChainBudget(self.root.parent)
        with self.assertRaisesRegex(ValueError, 'invalid generated outer'):
            budget_module.GeneratedChainBudget(self.root).checkpoint('reader')


if __name__ == '__main__':
    unittest.main()
