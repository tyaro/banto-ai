"""Shared-stop, disjoint-root and exit accounting for the composed fixture."""
from contextlib import ExitStack
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_preformal_generation_publication_budget as whole
from tests import test_anomaly_v03_preformal_generated_chain_budget as helpers


class EnvelopeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name).resolve()
        self.artifacts = self.repo / 'artifacts'
        self.artifacts.mkdir()
        self.parent = self.artifacts / 'document'
        self.parent.mkdir()
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(whole, 'ROOT', self.repo))
        stack.enter_context(patch.object(whole.generated, 'ROOT', self.repo))
        stack.enter_context(patch.object(whole.monitor, 'ROOT', self.repo))
        stack.enter_context(patch.object(whole.document, 'OUTPUT_PARENT', self.parent))
        stack.enter_context(patch.object(whole.monitor.primitives, 'system_snapshot',
                                         return_value=helpers.healthy_system()))
        self.outer = self.artifacts / (whole.PREFIX + 'one')
        self.producer = self.artifacts / (whole.generated.fixture.PREFIX + 'one')
        self.reader = self.artifacts / (whole.reread.PREFIX + 'one')
        self.roots = whole._new_roots(self.outer, self.producer, self.reader, 'trial-one')

    def budget(self, **overrides):
        self.outer.mkdir()
        self.producer.mkdir()
        value = {**whole.LIMITS, **overrides}
        budget = whole.EnvelopeBudget(self.roots, value).start()
        self.addCleanup(budget.close)
        return budget

    def test_all_seven_exits_and_three_mappings_are_required_and_report_is_bounded(self):
        budget = self.budget()
        pin = {'bytes': 100, 'sha256': 'a' * 64}
        for index, role in enumerate(whole.ROLES):
            budget.record_role(role, 'complete', pin, index + 1, True)
        for name in whole.document.chain.OUTPUTS:
            budget.record_output(name, pin)
        for _ in range(600):
            budget.checkpoint('publication')
        report = budget.close()
        self.assertTrue(report['passed'])
        self.assertTrue(report['all_seven_child_exits_reported'])
        self.assertTrue(report['all_mapping_outputs_reported'])
        self.assertEqual(report['phase_checkpoint_counts']['publication'], 600)
        self.assertEqual(len(report['phase_log']), 1)
        self.assertLess(len(whole.generated.v.canonical_json(report)), 64 * 1024)
        self.assertFalse(report['formal_permission'])
        self.assertFalse(report['complete_observation_campaign_verified'])
        self.assertFalse(report['smoke_capacity_twice_checked'])
        self.assertFalse(budget._thread.is_alive())

    def test_missing_exit_is_not_completed_even_when_sampler_passes(self):
        budget = self.budget()
        for index, role in enumerate(whole.ROLES):
            budget.record_role(role, 'complete', None, index + 1, role != 'saved-reader')
        self.assertFalse(budget.close()['all_seven_child_exits_reported'])

    def test_directory_cap_includes_all_fixed_roots_and_latches(self):
        budget = self.budget(directory_bytes=128 * 1024 + 5)
        self.reader.mkdir()
        (self.reader / 'small.json').write_bytes(b'123456')
        with self.assertRaisesRegex(whole.monitor.resources.ResourceStop, 'generated_directory_limit'):
            budget.checkpoint('saved-reader')
        self.assertFalse(budget.close()['passed'])

    def test_missing_previously_seen_root_is_rejected(self):
        budget = self.budget()
        self.reader.mkdir()
        budget.checkpoint('saved-reader')
        self.reader.rmdir()
        with self.assertRaisesRegex(whole.monitor.resources.ResourceStop, 'envelope_root_missing'):
            budget.checkpoint('saved-reader')

    def test_root_identity_change_is_rejected(self):
        budget = self.budget()
        identity = budget.identities['producer']
        budget.identities['producer'] = (identity[0], identity[1] + 1)
        with self.assertRaisesRegex(whole.monitor.resources.ResourceStop, 'envelope_root_changed'):
            budget.checkpoint('producer')

    def test_stage_link_propagates_outer_stop_to_supervisor_without_closing_outer(self):
        budget = self.budget()
        inner = Mock(root=self.producer)
        inner.probe.return_value = None
        inner.close.return_value = {'passed': True, 'stop_reason': None}
        relay = whole.link.LinkedBudget(inner, budget, stage='producer',
            role_map={'generator': 'producer'})
        relay.record_role('generator', 'complete', result_pin=None,
                          worker_pid=123, exit_confirmed=True)
        budget.reason = 'generated_wall_limit'
        self.assertEqual(relay.probe(), 'generated_wall_limit')
        report = relay.close()
        self.assertFalse(report['passed'])
        self.assertEqual(report['stop_reason'], 'generated_wall_limit')
        self.assertFalse(report['outer_sampler_closed_by_this_stage'])
        self.assertTrue(budget._thread.is_alive())
        self.assertIn('producer', budget.roles)
        with self.assertRaisesRegex(ValueError, 'exact live'):
            whole.link.LinkedBudget(inner, budget, stage='saved-reader')

    def test_existing_roots_and_relaxed_limits_are_rejected_before_children(self):
        self.reader.mkdir()
        with self.assertRaisesRegex(ValueError, 'all be new'):
            whole._new_roots(self.outer, self.producer, self.reader, 'trial-one')
        with self.assertRaisesRegex(ValueError, 'only tighten'):
            whole.limits({**whole.LIMITS, 'wall_seconds': 1801})
        with self.assertRaisesRegex(ValueError, 'only tighten'):
            whole.limits({**whole.LIMITS, 'minimum_free_disk_bytes': 1})

    def test_failed_generation_retains_receipts_and_never_starts_saved_reader(self):
        manifest_path = self.artifacts / 'anomaly-v03-preformal-generated-pinsets-one/pins.json'
        manifest_path.parent.mkdir()
        raw = b'{}'
        manifest_path.write_bytes(raw)
        pins = {'fixture/' + name: {'bytes': 1, 'sha256': 'a' * 64}
                for name in ('input.json', 'slices.json', 'coverage.json', 'operation.json')}
        manifest = {'revision': 'b' * 40, 'recipe_id': whole.generated.RECIPE,
                    'output_bytes': 100, 'chunk_index': 0, 'output_pins': {}}
        with patch.object(whole, '_source', return_value={'source': 'test'}), \
             patch.object(whole.document.chain.platform_runtime, 'probe_runtime', return_value={'test': True}), \
             patch.object(whole.document.control_files, 'validate_request'), \
             patch.object(whole.reread, '_manifest', return_value=(manifest, {})), \
             patch.object(whole.generated, 'generate_and_read',
                return_value={'status': 'failed', 'result_pin': {'bytes': 1, 'sha256': 'a' * 64}}), \
             patch.object(whole.reread, 'run_reread') as saved_reader:
            result = whole.run(outer_root=self.outer, producer_root=self.producer,
                reread_root=self.reader, receipt_name='trial-one',
                expected_manifest_pin=whole.generated.copied._pin(raw),
                expected_revision='b' * 40, control_root=self.artifacts / 'unused',
                expected_control_pinset_pin={'bytes': 1, 'sha256': 'a' * 64}, expected_input_pins=pins)
        self.assertEqual(result['status'], 'failed')
        self.assertIn('did not complete', result['detail'])
        saved_reader.assert_not_called()
        self.assertTrue((self.outer / 'result.json').exists())
        self.assertTrue((self.outer / 'resource-budget.json').exists())
        self.assertTrue((self.producer / 'resource-budget.json').exists())
        self.assertFalse(result['same_outer_budget_generation_to_fresh_reader_measured'])


if __name__ == '__main__':
    unittest.main()
