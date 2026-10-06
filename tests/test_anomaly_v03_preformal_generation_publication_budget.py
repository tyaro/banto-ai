"""Shared-stop, disjoint-root and exit accounting for the composed fixture."""
from contextlib import ExitStack
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from banto_ai import anomaly_v03_preformal_generation_publication_budget as whole
from banto_ai import anomaly_v03_role_runtime_observation as obs
from tests import test_anomaly_v03_preformal_generated_chain_budget as helpers
from tests.test_anomaly_v03_arithmetic_runtime_composition import candidates


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

    def test_invalid_runtime_bundle_rejects_before_roots_or_generation(self):
        with patch.object(whole.generated, 'generate_and_read') as producer, \
             self.assertRaisesRegex(ValueError, 'role inventory'):
            whole.run(outer_root=self.outer, producer_root=self.producer,
                reread_root=self.reader, receipt_name='trial-one',
                expected_manifest_pin={'bytes': 1, 'sha256': 'a' * 64},
                expected_revision='b' * 40, control_root=self.artifacts / 'unused',
                expected_control_pinset_pin={'bytes': 1, 'sha256': 'a' * 64},
                expected_input_pins={}, arithmetic_runtime_profiles={})
        producer.assert_not_called()
        self.assertFalse(self.outer.exists())
        self.assertFalse(self.producer.exists())

    def test_invalid_publication_bundle_rejects_before_roots_or_generation(self):
        with patch.object(whole.generated, 'generate_and_read') as producer, \
             self.assertRaisesRegex(ValueError, 'role inventory'):
            whole.run(outer_root=self.outer, producer_root=self.producer,
                reread_root=self.reader, receipt_name='trial-one',
                expected_manifest_pin={'bytes': 1, 'sha256': 'a' * 64},
                expected_revision='b' * 40, control_root=self.artifacts / 'unused',
                expected_control_pinset_pin={'bytes': 1, 'sha256': 'a' * 64},
                expected_input_pins={}, publication_runtime_profiles={})
        producer.assert_not_called()
        self.assertFalse(self.outer.exists())
        self.assertFalse(self.producer.exists())

    def test_invalid_saved_reader_profile_rejects_before_roots_or_generation(self):
        with patch.object(whole.generated, 'generate_and_read') as producer, \
             self.assertRaisesRegex(ValueError, 'entry fields'):
            whole.run(outer_root=self.outer, producer_root=self.producer,
                reread_root=self.reader, receipt_name='trial-one',
                expected_manifest_pin={'bytes': 1, 'sha256': 'a' * 64},
                expected_revision='b' * 40, control_root=self.artifacts / 'unused',
                expected_control_pinset_pin={'bytes': 1, 'sha256': 'a' * 64},
                expected_input_pins={}, saved_reader_runtime_profile={})
        producer.assert_not_called()
        self.assertFalse(self.outer.exists())
        self.assertFalse(self.producer.exists())

    def test_invalid_generation_bundle_rejects_before_roots_or_generation(self):
        with patch.object(whole.generated, 'generate_and_read') as producer, \
             self.assertRaisesRegex(ValueError, 'role inventory'):
            whole.run(outer_root=self.outer, producer_root=self.producer,
                reread_root=self.reader, receipt_name='trial-one',
                expected_manifest_pin={'bytes': 1, 'sha256': 'a' * 64},
                expected_revision='b' * 40, control_root=self.artifacts / 'unused',
                expected_control_pinset_pin={'bytes': 1, 'sha256': 'a' * 64},
                expected_input_pins={}, generation_runtime_profiles={})
        producer.assert_not_called()
        self.assertFalse(self.outer.exists())
        self.assertFalse(self.producer.exists())

    def test_outer_clock_forwards_pins_and_requires_matching_publication_evidence(self):
        bridge = whole.document.chain.draw_bridge
        pin = {'bytes': 1, 'sha256': 'a' * 64}
        sources = {name: pin for name in (*bridge.SOURCE_NAMES, *whole.document.publication.SOURCE_NAMES,
                                         *whole.reread.SOURCE_FILES, *whole.generated.SOURCE_FILES)}
        profiles = candidates(self.repo, sources)
        publication_profiles = {}
        for role in ('writer', 'reader'):
            value = json.loads(profiles['analysis']['raw'])
            value.update(role=role, format=obs.PUBLICATION_FORMAT, operation=obs.OPERATIONS[role])
            raw = obs.v.canonical_json(value)
            publication_profiles[role] = {'raw': raw, 'expected_pin': obs._pin(raw)}
        value.update(role='saved-reader', format=obs.SAVED_READER_FORMAT, operation=obs.OPERATIONS['saved-reader'])
        raw = obs.v.canonical_json(value)
        saved_reader_profile = {'raw': raw, 'expected_pin': obs._pin(raw)}
        generation_profiles = {}
        for role in ('producer', 'initial-reader'):
            value.update(role=role, format=obs.GENERATION_FORMAT, operation=obs.OPERATIONS[role])
            raw = obs.v.canonical_json(value)
            generation_profiles[role] = {'raw': raw, 'expected_pin': obs._pin(raw)}
        manifest = {'revision': 'b' * 40, 'recipe_id': whole.generated.RECIPE,
                    'output_bytes': 100, 'chunk_index': 0, 'output_pins': {}}
        def generated(root, *, outer_budget, generation_runtime_profiles, **kwargs):
            self.assertEqual(generation_runtime_profiles, generation_profiles)
            for role, pid in (('generator', 1), ('reader', 2)):
                outer_budget.record_role(role, 'complete', pin, pid, True)
            result = {'status': 'verified', 'result_pin': pin,
                      'generation_runtime_profile_pins': {k: v['expected_pin'] for k, v in generation_profiles.items()}}
            if case != 'generation-missing':
                result['generation_runtime_observation_checked'] = False if case == 'generation-false' else True
            if case == 'generation-different':
                result['generation_runtime_profile_pins']['initial-reader'] = pin
            return result
        def reread(root, reader_root, *, outer_budget, saved_reader_runtime_profile, **kwargs):
            self.assertEqual(saved_reader_runtime_profile, saved_reader_profile)
            outer_budget.record_role('saved-reader', 'complete', pin, 3, True)
            result = {'status': 'verified', 'result_pin': pin, 'verified_evaluations': 6,
                      'saved_reader_runtime_profile_pin': saved_reader_profile['expected_pin']}
            if case != 'saved-reader-missing':
                result['saved_reader_runtime_observation_checked'] = True
            if case == 'saved-reader-different':
                result['saved_reader_runtime_profile_pin'] = pin
            return result
        def publication(*, outer_budget, arithmetic_runtime_profiles, publication_runtime_profiles, **kwargs):
            self.assertTrue(outer_budget._thread.is_alive())
            self.assertEqual(arithmetic_runtime_profiles, profiles)
            self.assertEqual(publication_runtime_profiles, publication_profiles)
            for pid, role in enumerate(('analysis', 'audit', 'writer', 'reader'), 4):
                outer_budget.record_role(role, 'complete', pin, pid, True)
            for name in whole.document.chain.OUTPUTS:
                outer_budget.record_output(name, pin)
            published = {'status': 'measured', 'result_pin': pin,
                    'arithmetic_runtime_profile_pins': {role: entry['expected_pin']
                        for role, entry in profiles.items()}}
            if case != 'missing':
                published['arithmetic_runtime_observation_checked'] = True
            if case == 'different':
                published['arithmetic_runtime_profile_pins']['audit'] = pin
            published['publication_runtime_profile_pins'] = {role: entry['expected_pin']
                for role, entry in publication_profiles.items()}
            if case != 'publication-missing':
                published['publication_runtime_observation_checked'] = True
            if case == 'publication-different':
                published['publication_runtime_profile_pins']['reader'] = pin
            return published
        with patch.object(bridge, 'ROOT', self.repo), \
             patch.object(whole.document.publication, 'ROOT', self.repo), \
             patch.object(whole.reread, 'ROOT', self.repo), \
             patch.object(whole, '_source', return_value=sources), \
             patch.object(whole.document.chain.platform_runtime, 'probe_runtime', return_value=obs.runtime.EXPECTED), \
             patch.object(whole.document.control_files, 'validate_request'), \
             patch.object(whole.reread, '_manifest', return_value=(manifest, {})), \
             patch.object(whole.generated, 'generate_and_read', side_effect=generated), \
             patch.object(whole.reread, 'run_reread', side_effect=reread), \
             patch.object(whole, '_subset', return_value=([], {}, {})), \
             patch.object(whole.reread, '_recheck_saved_outputs', return_value={'invented-check': True}), \
             patch.object(whole.reread, 'recheck_runtime_profile'), \
             patch.object(whole.generated, 'recheck_runtime_profiles'), \
             patch.object(whole.document, 'run_saved_control_files_with_observation_subset', side_effect=publication):
            for case in ('missing', 'different', 'publication-missing', 'publication-different',
                         'saved-reader-missing', 'saved-reader-different',
                         'generation-missing', 'generation-different', 'generation-false', 'matched'):
                with self.subTest(case=case):
                    manifest_path = self.artifacts / ('anomaly-v03-preformal-generated-pinsets-' + case) / 'pins.json'
                    manifest_path.parent.mkdir()
                    manifest_path.write_bytes(b'{}')
                    outer = self.artifacts / (whole.PREFIX + case)
                    result = whole.run(outer_root=outer,
                        producer_root=self.artifacts / (whole.generated.fixture.PREFIX + case),
                        reread_root=self.artifacts / (whole.reread.PREFIX + case), receipt_name='trial-' + case,
                        expected_manifest_pin=whole.generated.copied._pin(b'{}'), expected_revision='b' * 40,
                        control_root=self.artifacts / 'unused', expected_control_pinset_pin=pin,
                        expected_input_pins={'fixture/' + name: pin
                            for name in ('input.json', 'slices.json', 'coverage.json', 'operation.json')},
                        arithmetic_runtime_profiles=profiles, publication_runtime_profiles=publication_profiles,
                        saved_reader_runtime_profile=saved_reader_profile, generation_runtime_profiles=generation_profiles)
                    matched = case == 'matched'
                    self.assertEqual(result['status'], 'measured' if matched else 'failed')
                    saved_failed = case.startswith('saved-reader-')
                    generation_failed = case.startswith('generation-')
                    self.assertEqual(result['arithmetic_runtime_observation_checked'],
                                     case not in ('missing', 'different') and not saved_failed and not generation_failed)
                    self.assertEqual(result['saved_reader_runtime_observation_checked'], not saved_failed and not generation_failed)
                    self.assertEqual(result['generation_runtime_observation_checked'], not generation_failed)
                    self.assertEqual(result['publication_runtime_observation_checked'], matched)
                    self.assertEqual(result['same_outer_budget_generation_to_fresh_reader_measured'], matched)
                    self.assertTrue((outer / 'result.json').is_file())
                    self.assertEqual(result['all_seven_child_exits_reported'], not saved_failed and not generation_failed)
                    self.assertFalse(result['formal_permission'])
                    self.assertFalse(result['runtime_closure_complete'])
                    if not matched:
                        self.assertIn('not checked' if case == 'missing' else
                            'pins differ' if case == 'different' else
                            'saved reader runtime observations' if saved_failed else
                            'generation runtime observations' if generation_failed else
                            'publication runtime observations', result['detail'])


if __name__ == '__main__':
    unittest.main()
