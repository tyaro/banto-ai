"""Outer invented chain budget: upstream compatibility and joined stop latch."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_preformal_chain_budget as outer


def system_snapshot(root):
    return {'commit_total_bytes': 8 * 1024**3,
            'commit_limit_bytes': 16 * 1024**3,
            'commit_headroom_bytes': 8 * 1024**3,
            'free_ram_bytes': 8 * 1024**3,
            'free_disk_bytes': 400 * 1024**3,
            'parent_peak_private_bytes': 80 * 1024**2}


class PreformalChainBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / 'artifacts')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / 'analysis').mkdir()
        self.publication = self.root / 'publication' / 'published'

    def _mock_observations(self):
        return (patch.object(outer.primitives, 'system_snapshot', side_effect=system_snapshot),
                patch.object(outer.primitives, 'directory_snapshot',
                             return_value={'directory_bytes': 24 * 1024**2,
                                           'directory_entries': 80}),
                patch.object(outer, '_max_depth', return_value=4))

    def test_live_upstream_accepts_nested_fixture_budget_and_joins_sampler(self):
        first, second, third = self._mock_observations()
        with first, second as tree, third:
            budget = outer.PreformalChainBudget(
                self.root, publication_roots=(self.publication,)).start()
            try:
                budget.checkpoint('analysis')
                child = outer.primitives.FixtureBudget(self.root / 'analysis', upstream=budget)
                child.start()
                try:
                    child.checkpoint()
                finally:
                    child_report = child.close()
                self.assertTrue(child_report['monitor_exit_confirmed'])
                pin = {'bytes': 3, 'sha256': 'a' * 64}
                budget.record_role('analysis', 'verified', pin, 1234, True)
                budget.checkpoint('postflight')
            finally:
                report = budget.close()
        self.assertTrue(report['sampler_exit_confirmed'])
        self.assertFalse(budget._thread.is_alive())
        self.assertTrue(report['passed'])
        self.assertEqual(report['summary']['maximum_root_logical_bytes'], 24 * 1024**2)
        self.assertEqual(report['summary']['maximum_root_depth'], 4)
        self.assertEqual(report['caller_reported_roles']['analysis']['result_pin'], pin)
        self.assertFalse(report['caller_reported_all_five_exits'])
        self.assertFalse(report['formal_50000_draw_budget_measured'])
        self.assertEqual(tree.call_args.kwargs['publication_roots'], (self.publication,))

    def test_resource_stop_is_latched_and_close_still_joins(self):
        snapshot = system_snapshot(self.root)
        with patch.object(outer.primitives, 'system_snapshot', return_value=snapshot), \
             patch.object(outer.primitives, 'directory_snapshot',
                          return_value={'directory_bytes': 0, 'directory_entries': 1}), \
             patch.object(outer, '_max_depth', return_value=1):
            budget = outer.PreformalChainBudget(self.root).start()
            try:
                snapshot['free_ram_bytes'] = 1024
                with self.assertRaisesRegex(outer.resources.ResourceStop, 'pipeline_free_ram'):
                    budget.checkpoint('producer')
                self.assertEqual(budget.probe(), 'pipeline_free_ram')
            finally:
                report = budget.close()
        self.assertTrue(report['sampler_exit_confirmed'])
        self.assertFalse(report['passed'])
        self.assertEqual(report['stop_reason'], 'pipeline_free_ram')

    def test_depth_measurement_and_limits_are_bounded(self):
        nested = self.root / 'analysis' / 'worker' / 'report'
        nested.mkdir(parents=True)
        self.assertEqual(outer._max_depth(self.root, 32, 8), 3)
        with self.assertRaisesRegex(outer.resources.ResourceStop, 'pipeline_directory_depth'):
            outer._max_depth(self.root, 32, 2)
        with self.assertRaisesRegex(ValueError, 'only tighten'):
            outer.limits({**outer.DEFAULTS, 'wall_seconds': 241})

    def test_final_receipt_reserve_is_within_directory_cap(self):
        almost_full = outer.DEFAULTS['directory_bytes'] - 64 * 1024
        with patch.object(outer.primitives, 'system_snapshot', side_effect=system_snapshot), \
             patch.object(outer.primitives, 'directory_snapshot', return_value={
                 'directory_bytes': almost_full, 'directory_entries': 80}), \
             patch.object(outer, '_max_depth', return_value=4):
            budget = outer.PreformalChainBudget(self.root).start()
            try:
                with self.assertRaisesRegex(outer.resources.ResourceStop,
                                            'pipeline_directory_limit'):
                    budget.checkpoint('preflight')
            finally:
                report = budget.close()
        self.assertEqual(report['receipt_reserve_bytes'], 128 * 1024)
        self.assertFalse(report['passed'])


if __name__ == '__main__':
    unittest.main()
