"""Partial reader claims compose an explicit fixture without moving old pins."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_observation_subset_fixture_projection as subset
from banto_ai import anomaly_v03_preformal_saved_row_document_budget as pipeline
from tests import test_anomaly_v03_saved_row_fixture_projection as fixture_tests
from tests.test_anomaly_v03_preformal_saved_seed_contribution import chunk_entry
from tests.test_anomaly_v03_preformal_saved_row_coverage import rewrap
from tests import test_anomaly_v03_saved_control_file_reader as disk_tests

REVISION = fixture_tests.REVISION
DRAW = fixture_tests.DRAW


def retained_subset(index=0, *, inconclusive_first=False):
    entry = chunk_entry(index, latest_attempt=2,
                        inconclusive_first=inconclusive_first)
    result = v.strict_json(entry['result_raw'])
    manifest = v.strict_json(entry['manifest_raw'])
    old = manifest['revision']
    historical = 'c' * 40
    manifest['revision'] = historical
    manifest['source']['revision'] = historical
    manifest['source_snapshots'] = {historical: manifest['source_snapshots'][old]}
    rewrap(entry, 'manifest', manifest)
    stdout = v.strict_json(entry['stdout_raw'])
    stdout['manifest_pin'] = entry['expected_pins']['manifest']
    rewrap(entry, 'stdout', stdout)
    supervision = v.strict_json(entry['supervision_raw'])
    supervision['output'] = entry['expected_pins']['stdout']
    rewrap(entry, 'supervision', supervision)
    result.update(historic_source_revision=historical,
        manifest_pin=entry['expected_pins']['manifest'],
        reader_supervision_pin=entry['expected_pins']['supervision'],
        child_stdout_pin=entry['expected_pins']['stdout'],
        saved_attempt_final_disk_recheck_completed=True,
        saved_attempt_final_disk_recheck_inside_budget=True,
        saved_rows_final_disk_recheck_completed=True,
        saved_attempt_final_disk_recheck={
            'saved_files': 22, 'saved_bytes': manifest['output_bytes'],
            'latest_attempt': 2, 'disk_pin_recheck_completed': True,
            'path_scope': 'fixed-selected-latest-attempt-files',
            'raw_observations_rederived_during_recheck': False,
            'formal_permission': False})
    rewrap(entry, 'result', result)
    return entry


class ObservationSubsetProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture_tests.SavedRowFixtureProjectionTests.setUpClass()
        cls.metadata_entries = fixture_tests.SavedRowFixtureProjectionTests.entries
        cls.metadata = fixture_tests.SavedRowFixtureProjectionTests.prepared
        cls.entry = retained_subset()
        cls.expected = [{'chunk_index': 0,
                         'expected_pins': copy.deepcopy(cls.entry['expected_pins'])}]

    def prepare(self, entries=None, expected=None, **options):
        arguments = dict(expected_mode='fixture', expected_revision=REVISION,
                         draws=[DRAW], expected_subset=self.expected if expected is None else expected)
        arguments.update(options)
        with patch.object(subset.base, 'prepare_inputs',
                          return_value=copy.deepcopy(self.metadata)), \
             patch('builtins.open', side_effect=AssertionError('unexpected file IO')), \
             patch('subprocess.check_output', side_effect=AssertionError('unexpected process')):
            return subset.prepare_inputs(self.metadata_entries,
                [self.entry] if entries is None else entries, **arguments)

    def test_exact_subset_slot_rederives_four_inputs_and_keeps_both_histories(self):
        prepared = self.prepare()
        binding = prepared['binding']
        self.assertEqual(binding['format'], subset.FORMAT)
        self.assertIsNone(binding['declared_historical_source_revision'])
        self.assertEqual(binding['metadata_historical_source_revision'], 'a' * 40)
        self.assertEqual(binding['subset_source_chunks'][0]['historic_source_revision'], 'c' * 40)
        self.assertEqual(binding['metadata_source_chunks'], self.metadata['binding']['source_chunks'])
        self.assertEqual(binding['source_chunks'][0]['entry_pins'], self.entry['expected_pins'])
        self.assertEqual(binding['source_chunks'][1]['entry_pins'], self.metadata_entries[1]['expected_pins'])
        self.assertEqual(binding['affected_seed_indices'], [0])
        self.assertEqual((binding['subset_chunks'], binding['subset_evaluations'],
                          binding['remaining_metadata_chunks']), (1, 6, 479))
        self.assertEqual(binding['coverage']['counts']['success'], 2880)
        self.assertEqual(binding['coverage']['counts']['inconclusive'], 0)
        self.assertEqual([(row['chunk_index'], row['attempt'])
                          for row in binding['failed_attempt_history']], [(0, 1), (479, 1)])
        self.assertEqual(set(prepared['files']), set(subset.base.analysis.INPUT_LIMITS))
        original = v.strict_json(self.metadata['files']['fixture/input.json'])
        changed = v.strict_json(prepared['files']['fixture/input.json'])
        self.assertNotEqual(changed['clusters'][0], original['clusters'][0])
        self.assertEqual(changed['clusters'][1:], original['clusters'][1:])
        self.assertEqual(len(changed['clusters']), 40)
        for key, wanted in subset.base.CLOSED.items():
            self.assertEqual(binding[key], wanted)
        self.assertFalse(binding['complete_observation_campaign_verified'])
        self.assertFalse(binding['subset_observation_payloads_reopened_here'])

    def test_inconclusive_subset_keeps_full_row_denominators_and_profile(self):
        entry = retained_subset(1, inconclusive_first=True)
        expected = [{'chunk_index': 1, 'expected_pins': entry['expected_pins']}]
        prepared = self.prepare([entry], expected)
        self.assertEqual(prepared['binding']['coverage']['counts']['inconclusive'], 2)
        values = v.strict_json(prepared['files']['fixture/input.json'])
        cell = values['clusters'][0]['candidates'][subset.base.seed.arithmetic.CANDIDATES[0]]['core']
        self.assertEqual(cell['counts']['machine_recall'][1], 120)
        self.assertEqual(cell['profile_status'], 'inconclusive')

    def test_formal_and_unbounded_draws_reject_before_metadata_projection(self):
        for options in [dict(expected_mode='formal'), dict(draws=[DRAW] * 9)]:
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.prepare(**options)

    def test_missing_final_recheck_and_changed_external_pins_reject(self):
        changed = copy.deepcopy(self.entry)
        result = v.strict_json(changed['result_raw'])
        result['saved_attempt_final_disk_recheck_completed'] = False
        rewrap(changed, 'result', result)
        expected = [{'chunk_index': 0, 'expected_pins': changed['expected_pins']}]
        with self.assertRaisesRegex(ValueError, 'final recheck'):
            self.prepare([changed], expected)
        with self.assertRaises(ValueError):
            self.prepare([changed])

    def test_duplicate_reordered_and_wrong_subset_slots_reject(self):
        for entries, expected in [([self.entry, self.entry], self.expected * 2),
            ([self.entry], [{'chunk_index': 1, 'expected_pins': self.entry['expected_pins']}])]:
            with self.subTest(expected=expected[0]['chunk_index']), self.assertRaises(ValueError):
                self.prepare(entries, expected)

    def test_subset_final_raw_change_rejects_original_retained_pin(self):
        changed = copy.deepcopy(self.entry)
        changed['rows_raw'] += b' '
        with self.assertRaises(ValueError):
            subset.recheck_subset([changed], self.expected)

    def test_combined_input_limit_rejects_before_projection(self):
        with patch.object(subset.base.coverage, 'MAX_TOTAL_INPUT_BYTES', 1), \
             self.assertRaisesRegex(ValueError, 'combined metadata'):
            self.prepare()

    def test_metadata_recheck_uses_original_pins_after_subset_composition(self):
        prepared = self.prepare()
        pipeline._recheck_controls(self.metadata_entries, prepared['binding'])
        changed = list(self.metadata_entries)
        changed[0] = copy.deepcopy(changed[0])
        changed[0]['rows_raw'] += b' '
        with self.assertRaises(ValueError):
            pipeline._recheck_controls(changed, prepared['binding'])

    def test_subset_route_requires_disk_publication_before_creating_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary) / 'new-parent'
            with patch.object(pipeline, 'OUTPUT_PARENT', parent), self.assertRaises(ValueError):
                pipeline.run_saved_rows(self.metadata_entries,
                    expected_mode='fixture', expected_input_pins=self.metadata['binding']['worker_input_pins'],
                    expected_revision=REVISION, receipt_name='trial-subset', receipt_parent=parent,
                    observation_subset=[self.entry], expected_observation_subset=self.expected)
            self.assertFalse(parent.exists())


class ObservationSubsetPipelineTests(unittest.TestCase):
    setUpClass = classmethod(disk_tests.DiskControlPipelineTests.setUpClass.__func__)
    publish = disk_tests.DiskControlPipelineTests.publish

    def setUp(self):
        disk_tests.DiskControlPipelineTests.setUp(self)
        self.stack.enter_context(patch.object(
            pipeline, 'ObservationSubsetBudget', disk_tests.FakeControlFileBudget))
        self.subset_entries = [copy.deepcopy(self.entry)]
        self.external = [{'chunk_index': 0,
                          'expected_pins': copy.deepcopy(self.entry['expected_pins'])}]
        prepared = copy.deepcopy(self.prepared)
        prepared['binding'].update(format=subset.FORMAT,
            metadata_source_chunks=copy.deepcopy(prepared['binding']['source_chunks']),
            subset_chunks=1, subset_evaluations=6, remaining_metadata_chunks=479,
            combined_control_input_bytes=1000, affected_seed_indices=[0])
        self.subset_prepare = self.stack.enter_context(patch.object(
            subset, 'prepare_inputs', return_value=prepared))

    def run_trial(self):
        return pipeline.run_saved_control_files_with_observation_subset(
            observation_subset=self.subset_entries, expected_observation_subset=self.external,
            control_root=self.source, expected_control_pinset_pin=self.index_pin,
            expected_mode='fixture', expected_input_pins=self.pins, expected_revision=REVISION,
            receipt_name='trial-one', receipt_parent=self.parent)

    def test_composed_rows_share_clock_with_four_roles_but_reader_execution_precedes_clock(self):
        result = self.run_trial()
        self.assertEqual(result['status'], 'measured')
        self.assertEqual(result['format'], subset.PIPELINE_FORMAT)
        self.assertEqual(self.subset_prepare.call_count, 1)
        self.assertTrue(result['same_budget_subset_rows_to_fresh_reader_measured'])
        self.assertTrue(result['all_four_child_exits_reported'])
        self.assertFalse(result['same_budget_observation_reader_to_fresh_reader_measured'])
        self.assertFalse(result['observation_payload_reader_executed_inside_budget'])
        self.assertFalse(result['complete_observation_campaign_verified'])
        self.assertFalse(result['formal_permission'])

    def test_subset_change_after_completed_publication_is_failed_and_retained(self):
        def changed(*args):
            self.publish(*args)
            self.subset_entries[0]['rows_raw'] += b' '
        self.publication.side_effect = changed
        result = self.run_trial()
        self.assertEqual(result['status'], 'failed')
        self.assertTrue(result['local_publication_performed'])
        self.assertFalse(result['same_budget_subset_rows_to_fresh_reader_measured'])
        self.assertTrue((self.parent / 'trial-one/result.json').exists())

    def test_subset_rejection_never_starts_arithmetic_or_publication(self):
        self.subset_prepare.side_effect = ValueError('subset source mismatch')
        result = self.run_trial()
        self.assertEqual(result['status'], 'failed')
        self.arithmetic.assert_not_called()
        self.publication.assert_not_called()


if __name__ == '__main__':
    unittest.main()
