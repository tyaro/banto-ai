"""Pure contract and stop checks for the separate pinned-producer draw bridge."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_preformal_bound_draw_bridge as bridge
from tests.test_anomaly_v03_bound_fixture_pipeline import example


REVISION = 'a' * 40


class BoundDrawBridgeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='banto-bound-draw-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.producer_parent = self.root / 'artifacts' / 'anomaly-v03-preformal-five-role-26h2'
        self.output_parent = self.root / 'artifacts' / 'anomaly-v03-preformal-bound-draw-bridge'
        self.producer = self.producer_parent / 'trial-01' / 'producer'
        output = self.producer / 'output'
        (output / 'projection' / 'fixture').mkdir(parents=True)
        self.output_parent.mkdir(parents=True)
        bound = bridge.projection.v.canonical_json(example())
        bound_pin = bridge._pin(bound)
        prepared = bridge.projection.prepare_inputs(
            bound, expected_mode='fixture', expected_pin=bound_pin,
            expected_revision=REVISION, draws=[list(range(40))])
        (output / 'bound.json').write_bytes(bound)
        for name, raw in prepared['files'].items():
            (output / 'projection' / name).write_bytes(raw)
        result = {
            'format': bridge.producer.FORMAT, 'mode': 'fixture',
            'status': 'verified', 'owned_producer_join_executed': True,
            'worker_exit_confirmed': True, 'real_producer_executed': False,
            'registered_data_read': False, 'new_evaluations': 0,
            'formal_permission': False, 'promotion_allowed': False,
            'source_revision': REVISION, 'bound_path': str(output / 'bound.json'),
            'projection_root': str(output / 'projection'), 'bound_pin': bound_pin,
            'projection_pins': {name: bridge._pin(raw) for name, raw in
                                prepared['files'].items()},
        }
        raw = bridge._raw(result)
        (self.producer / 'result.json').write_bytes(raw)
        self.result_pin = bridge._pin(raw)
        self.producer_patch = patch.object(bridge, 'PRODUCER_PARENT', self.producer_parent)
        self.producer_patch.start()
        self.addCleanup(self.producer_patch.stop)

    def test_actual_bound_and_all_projection_bytes_feed_both_arithmetic_contracts(self):
        bound = bridge.bind_producer_counts(self.producer, self.result_pin)
        self.assertEqual(bound['source_root'], str(self.producer))
        self.assertEqual(bound['bound_pin']['bytes'],
                         (self.producer / 'output' / 'bound.json').stat().st_size)
        self.assertEqual(len(bound['clusters']), 40)
        self.assertNotEqual(bound['clusters'], bridge.draw_budget.invented_clusters())
        input_value = bridge._input(bound)
        bridge._check_input(input_value)
        draws = [bytes((draw * 13 + position * 7) % 40 for position in range(40))
                 for draw in range(8)]
        actual = bridge.primary.compute_fixture_tables(bound['clusters'], draws,
                                                       engineering_ready=False)
        expected = bridge.independent._expected_tables(bound['clusters'], draws)
        self.assertEqual(bridge._raw(actual['candidate_tables']), bridge._raw(expected))
        self.assertEqual((len(expected), sum(len(row['gates']) for row in expected)),
                         (9, 180))
        self.assertFalse(actual['formal_permission'])
        self.assertFalse(actual['independent_s6_complete'])

    def test_changed_saved_projection_and_bad_result_pin_fail_closed(self):
        path = self.producer / 'output' / 'projection' / 'fixture' / 'input.json'
        path.write_bytes(path.read_bytes() + b' ')
        with self.assertRaisesRegex(ValueError, 'pin differs'):
            bridge.bind_producer_counts(self.producer, self.result_pin)
        with self.assertRaisesRegex(ValueError, 'pin differs'):
            bridge.bind_producer_counts(self.producer,
                                        {'bytes': 1, 'sha256': '0' * 64})

    def test_inconclusive_producer_cells_are_rejected_before_audit(self):
        value = bridge.bind_producer_counts(self.producer, self.result_pin)
        altered = copy.deepcopy(bridge._input(value))
        altered['clusters'][0]['candidates']['c0-diff-control']['core'][
            'profile_status'] = 'inconclusive'
        with self.assertRaisesRegex(ValueError, 'calibrated'):
            bridge._check_input(altered)

    def test_preflight_resource_stop_retains_receipts_and_starts_no_child(self):
        class StoppedBudget:
            def __init__(self, root):
                self.root = root
                self._thread = None
            def start(self):
                self._thread = object()
                return self
            def checkpoint(self, phase):
                raise bridge.resources.ResourceStop('pipeline_free_ram')
            def close(self):
                return {'passed': False, 'stop_reason': 'pipeline_free_ram',
                        'both_arithmetic_child_exits_reported': False,
                        'sampler_exit_confirmed': True}
        with patch.object(bridge, 'OUTPUT_PARENT', self.output_parent), \
             patch.object(bridge, 'BoundDrawBudget', StoppedBudget), \
             patch.object(bridge, '_supervise', side_effect=AssertionError('child launched')):
            result = bridge.run_bridge(
                expected_mode='fixture', producer_root=self.producer,
                expected_producer_result_pin=self.result_pin,
                expected_revision=REVISION, receipt_name='attempt',
                receipt_parent=self.output_parent)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['reason'], 'pipeline_free_ram')
        self.assertEqual(result['stage'], 'preflight')
        self.assertFalse(result['formal_permission'])
        target = self.output_parent / 'attempt'
        self.assertFalse((target / 'input.json').exists())
        self.assertTrue((target / 'resource-budget.json').is_file())
        self.assertEqual(json.loads((target / 'result.json').read_bytes())['reason'],
                         'pipeline_free_ram')

    def test_failed_owned_analysis_retains_stop_and_never_starts_audit(self):
        class Budget:
            def __init__(self, root):
                self.root = root
                self._thread = None
                self.roles = {}
            def start(self):
                self._thread = object()
                return self
            def checkpoint(self, phase):
                return None
            def record_role(self, role, status, result_pin=None, worker_pid=None,
                            exit_confirmed=None):
                self.roles[role] = exit_confirmed
            def close(self):
                return {'passed': True, 'stop_reason': None,
                        'both_arithmetic_child_exits_reported': False,
                        'sampler_exit_confirmed': True}
        failed = {'status': 'failed', 'pid': 123, 'worker_exit_confirmed': True,
                  'stop_reason': 'bridge_child_private_limit'}
        with patch.object(bridge, 'OUTPUT_PARENT', self.output_parent), \
             patch.object(bridge, 'BoundDrawBudget', Budget), \
             patch.object(bridge, '_git_pins', return_value={'selected': self.result_pin}), \
             patch.object(bridge.platform_runtime, 'probe_runtime',
                          return_value={'test': True}), \
             patch.object(bridge, '_supervise', return_value=failed) as supervise:
            result = bridge.run_bridge(
                expected_mode='fixture', producer_root=self.producer,
                expected_producer_result_pin=self.result_pin,
                expected_revision=REVISION, receipt_name='analysis-stop',
                receipt_parent=self.output_parent)
        self.assertEqual(supervise.call_count, 1)
        self.assertEqual(supervise.call_args.args[0], 'analysis')
        self.assertEqual(result['stage'], 'analysis')
        self.assertEqual(result['reason'], 'bridge_child_private_limit')
        self.assertFalse(result['invented_50000_primary_tables_measured'])
        target = self.output_parent / 'analysis-stop'
        self.assertTrue((target / 'analysis-supervision.json').is_file())
        self.assertFalse((target / 'audit-supervision.json').exists())
        self.assertFalse((target / 'audit.json').exists())
        self.assertEqual(json.loads((target / 'result.json').read_bytes())['status'],
                         'failed')

    def test_closed_modes_reject_before_output_io(self):
        with patch.object(bridge, 'OUTPUT_PARENT', self.output_parent):
            for mode in ('formal', 'holdout', 'engineering-dev-smoke', True):
                with self.subTest(mode=mode), self.assertRaises(ValueError):
                    bridge.run_bridge(
                        expected_mode=mode, producer_root=self.producer,
                        expected_producer_result_pin=self.result_pin,
                        expected_revision=REVISION, receipt_name='attempt',
                        receipt_parent=self.output_parent)
        self.assertFalse((self.output_parent / 'attempt').exists())

    def test_versioned_outer_budget_latches_stop_and_joins_sampler(self):
        budget_root = self.output_parent / 'budget-stop'
        budget_root.mkdir()
        snapshot = {
            'commit_total_bytes': 8 * 1024**3,
            'commit_limit_bytes': 16 * 1024**3,
            'commit_headroom_bytes': 8 * 1024**3,
            'free_ram_bytes': bridge.ROOT_LIMITS['minimum_free_ram_bytes'] - 1,
            'free_disk_bytes': 400 * 1024**3,
            'parent_peak_private_bytes': 80 * 1024**2,
        }
        with patch.object(bridge.primitives, 'system_snapshot', return_value=snapshot), \
             patch.object(bridge.primitives, 'directory_snapshot', return_value={
                 'directory_bytes': 0, 'directory_entries': 0}), \
             patch.object(bridge.chain_budget, '_max_depth', return_value=0):
            budget = bridge.BoundDrawBudget(budget_root).start()
            try:
                with self.assertRaisesRegex(bridge.resources.ResourceStop,
                                            'pipeline_free_ram'):
                    budget.checkpoint('preflight')
            finally:
                report = budget.close()
        self.assertEqual(report['format'], bridge.FORMAT + '-resource-budget')
        self.assertEqual(report['limits'], bridge.ROOT_LIMITS)
        self.assertEqual(report['stop_reason'], 'pipeline_free_ram')
        self.assertTrue(report['sampler_exit_confirmed'])
        self.assertFalse(report['passed'])


if __name__ == '__main__':
    unittest.main()
