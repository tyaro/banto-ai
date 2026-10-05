"""Source provenance and stop boundaries for saved-control full-draw wiring."""
import copy
from contextlib import ExitStack
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_preformal_saved_row_document_budget as saved
from tests import test_anomaly_v03_preformal_contiguous_document_budget as helpers
from tests.test_anomaly_v03_bound_fixture_pipeline import example


REVISION = 'b' * 40
REAL_DOCUMENT = saved.chain._document


class SavedRowDocumentBudgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # The actual 480-row projection has its own lineage/count tests. Here
        # a small valid aggregate isolates this runner's provenance and stops.
        raw = saved.projection.v.canonical_json(example())
        prepared = saved.chain.draw_bridge.projection.prepare_inputs(
            raw, expected_mode='fixture', expected_pin=saved.chain.draw_bridge._pin(raw),
            expected_revision=REVISION, draws=[list(range(40))])
        cls.prepared = {'files': prepared['files'], 'binding': {
            **saved.projection.CLOSED, 'format': saved.projection.FORMAT,
            'worker_input_pins': prepared['binding']['worker_input_pins'],
            'coverage': {'complete': True, 'counts': {'success': 2880}},
            'declared_historical_source_revision': 'a' * 40,
            'failed_attempt_history': [{'chunk_index': 479, 'attempt': 1}],
        }}

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='banto-saved-draw-')
        self.addCleanup(temporary.cleanup)
        self.parent = Path(temporary.name).resolve() / 'receipts'
        self.pins = copy.deepcopy(self.prepared['binding']['worker_input_pins'])
        self.entries = [{'mocked-control-boundary': True}]
        helpers.FakeBudget.instances = []
        helpers.FakeBudget.stop_phase = None
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(saved, 'OUTPUT_PARENT', self.parent))
        stack.enter_context(patch.object(saved, '_source_pins', return_value={'selected': self.pins['fixture/input.json']}))
        stack.enter_context(patch.object(saved.chain.platform_runtime, 'probe_runtime', return_value={'test': True}))
        stack.enter_context(patch.object(saved, 'SavedRowBudget', helpers.FakeBudget))
        self.prepare = stack.enter_context(patch.object(
            saved.projection, 'prepare_inputs', side_effect=lambda *a, **k: copy.deepcopy(self.prepared)))
        self.arithmetic = stack.enter_context(patch.object(
            saved.chain, '_arithmetic', side_effect=helpers.ContiguousDocumentBudgetTests.fake_arithmetic))
        stack.enter_context(patch.object(
            saved.chain, '_document', side_effect=helpers.ContiguousDocumentBudgetTests.fake_document))
        stack.enter_context(patch.object(
            saved.chain, '_slices', side_effect=helpers.ContiguousDocumentBudgetTests.fake_slices))

    def run_trial(self, name='trial-one', **options):
        arguments = dict(expected_mode='fixture', expected_input_pins=self.pins,
                         expected_revision=REVISION, receipt_name=name,
                         receipt_parent=self.parent)
        arguments.update(options)
        return saved.run_saved_rows(self.entries, **arguments)

    def test_one_clock_includes_projection_recheck_and_all_mappings(self):
        result = self.run_trial()
        self.assertEqual(result['status'], 'measured')
        self.assertEqual(self.prepare.call_count, 2)
        self.assertEqual(self.arithmetic.call_count, 1)
        self.assertEqual(len(helpers.FakeBudget.instances), 1)
        budget = helpers.FakeBudget.instances[0]
        self.assertTrue(budget.closed)
        self.assertEqual(budget.phases, ['preflight', 'preflight', 'analysis', 'audit',
                                      'document', 'slices', 'postflight', 'postflight'])
        self.assertTrue(result['saved_control_projection_inside_budget'])
        self.assertTrue(result['same_budget_50000_arithmetic_document_slices_measured'])
        self.assertEqual(result['inherited_failed_attempts'], 1)
        self.assertFalse(result['campaign_coherence_authenticated'])
        self.assertFalse(result['full_end_to_end_budget_measured'])
        self.assertFalse(result['formal_permission'])
        input_value = json.loads((self.parent/'trial-one/input.json').read_bytes())
        saved.chain.draw_bridge._check_input(input_value)
        self.assertEqual(input_value['projection_source_revision'], REVISION)
        self.assertEqual(input_value['projection_input_pins'], self.pins)
        self.assertNotIn('producer_result_pin', input_value)
        self.assertNotIn('producer_result_pin', result)
        self.assertTrue((self.parent/'trial-one/projection.json').is_file())
        for name in self.prepared['files']:
            self.assertEqual((self.parent/'trial-one/inputs'/Path(name).name).read_bytes(),
                             self.prepared['files'][name])

    def test_wrong_expected_pin_keeps_failure_without_child(self):
        pins = copy.deepcopy(self.pins)
        pins['fixture/input.json']['sha256'] = '0'*64
        result = self.run_trial(expected_input_pins=pins)
        self.assertEqual(result['status'], 'failed')
        self.assertIn('external projection pins differ', result['detail'])
        self.arithmetic.assert_not_called()
        self.assertFalse((self.parent/'trial-one/input.json').exists())
        self.assertTrue((self.parent/'trial-one/result.json').is_file())

    def test_lineage_rejection_keeps_failure_without_child(self):
        self.prepare.side_effect = ValueError('missing saved chunk')
        result = self.run_trial()
        self.assertEqual(result['stage'], 'preflight')
        self.assertEqual(result['status'], 'failed')
        self.assertIn('missing saved chunk', result['detail'])
        self.arithmetic.assert_not_called()

    def test_preflight_stop_blocks_even_projection(self):
        helpers.FakeBudget.stop_phase = 'preflight'
        result = self.run_trial()
        self.assertEqual(result['reason'], 'pipeline_wall_limit')
        self.prepare.assert_not_called()
        self.arithmetic.assert_not_called()
        self.assertTrue(helpers.FakeBudget.instances[0].closed)

    def test_arithmetic_stop_never_maps_document(self):
        self.arithmetic.side_effect = saved.chain.draw_bridge.resources.ResourceStop('bridge_child_private_limit')
        result = self.run_trial()
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['reason'], 'bridge_child_private_limit')
        self.assertFalse((self.parent/'trial-one/document.json').exists())
        self.assertFalse((self.parent/'trial-one/slices.json').exists())

    def test_changed_caller_controls_reject_after_mapping_without_replay(self):
        changed = copy.deepcopy(self.prepared)
        changed['binding']['declared_historical_source_revision'] = 'c'*40
        self.prepare.side_effect = [copy.deepcopy(self.prepared), changed]
        result = self.run_trial()
        self.assertEqual(result['status'], 'failed')
        self.assertIn('controls changed', result['detail'])
        self.assertEqual(self.arithmetic.call_count, 1)
        self.assertFalse(result['same_budget_50000_arithmetic_document_slices_measured'])

    def test_source_change_keeps_failed_terminal(self):
        with patch.object(saved, '_source_pins', side_effect=[{'before': True}, {'after': True}]):
            result = self.run_trial()
        self.assertEqual(result['status'], 'failed')
        self.assertIn('source/runtime changed', result['detail'])

    def test_projection_output_mutation_fails_readback(self):
        def altered(*args, **kwargs):
            value = copy.deepcopy(self.prepared)
            if self.prepare.call_count == 2:
                target = self.parent/'trial-one/inputs/coverage.json'
                target.write_bytes(target.read_bytes()+b' ')
            return value
        self.prepare.side_effect = altered
        result = self.run_trial()
        self.assertEqual(result['status'], 'failed')
        self.assertIn('pin differs', result['detail'])

    def test_unreaped_worker_retains_owner_and_raises(self):
        owner = saved.chain.draw_bridge.draw_budget.UnreapedMeasurement(object(), 'audit', {})
        self.arithmetic.side_effect = owner
        with self.assertRaises(saved.chain.draw_bridge.draw_budget.UnreapedMeasurement) as raised:
            self.run_trial()
        self.assertIs(raised.exception, owner)
        self.assertEqual(owner.receipt, self.parent/'trial-one')
        result = json.loads((owner.receipt/'result.json').read_bytes())
        self.assertEqual(result['reason'], 'owned_child_exit_unconfirmed')
        self.assertFalse(result['worker_exit_confirmed'])

    def test_closed_modes_bad_pins_and_relaxed_limits_reject_before_root(self):
        for mode in ('formal', 'holdout', True):
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                self.run_trial(expected_mode=mode)
        with self.assertRaises(ValueError):
            self.run_trial(expected_input_pins={})
        limits = dict(saved.chain.LIMITS)
        limits['wall_seconds'] += 1
        with self.assertRaises(ValueError):
            self.run_trial(budget_limits=limits)
        self.assertFalse(self.parent.exists())

    def test_existing_receipt_cannot_be_reused(self):
        self.assertEqual(self.run_trial()['status'], 'measured')
        with self.assertRaises((ValueError, FileExistsError)):
            self.run_trial()

    def test_saved_draw_input_rejects_claims_missing_pins_and_wrong_clusters(self):
        fixture = saved.projection.v.strict_json(self.prepared['files']['fixture/input.json'])
        binding = {'clusters': fixture['clusters'], 'projection_pins': self.pins,
                   'saved_row_projection_pin': saved.chain.draw_bridge._pin(b'projection')}
        value = saved._draw_input(binding, REVISION)
        for alteration in ({'registered_data_read': True}, {'source_closure_complete': True},
                           {'projection_input_pins': {}}, {'clusters': fixture['clusters'][:39]}):
            with self.subTest(alteration=list(alteration)), self.assertRaises(ValueError):
                saved.chain.draw_bridge._check_input({**value, **alteration})

    def test_document_metadata_preserves_saved_control_origin(self):
        fixture = saved.projection.v.strict_json(self.prepared['files']['fixture/input.json'])
        binding = {'clusters': fixture['clusters'], 'projection_pins': self.pins,
                   'saved_row_projection_pin': saved.chain.draw_bridge._pin(b'projection')}
        target = self.parent/'mapping'
        target.mkdir(parents=True)
        budget = helpers.FakeBudget(target, saved.chain.LIMITS).start()
        packet = {'fixture_candidate_tables': [], 'fixture_selected_candidate': None,
                  'fixture_decision': 'inconclusive'}
        result = {'input_pin': self.pins['fixture/input.json'],
                  'calculation_pin': self.pins['fixture/input.json'],
                  'arithmetic_audit_pin': self.pins['fixture/input.json']}
        with patch.object(saved.chain.document_bridge.adapter,
                          'map_precomputed_fixture_packet', return_value=packet):
            document, _ = REAL_DOCUMENT(target, binding, fixture, {},
                                       {'draw_sha256': '0'*64}, budget, result)
        self.assertEqual(document['saved_row_projection_pin'], binding['saved_row_projection_pin'])
        self.assertEqual(document['saved_row_projection_input_pins'], self.pins)
        self.assertTrue(document['saved_reader_control_inputs_used'])
        self.assertNotIn('producer_result_pin', document)
        self.assertFalse(document['formal_permission'])
        self.assertFalse(document['formal_requirements']['ready'])


if __name__ == '__main__':
    unittest.main()
