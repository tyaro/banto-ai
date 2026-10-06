"""Direct fixture counts retain the descriptive reader's rejection rules."""
import copy
import unittest

from banto_ai import anomaly_v03_analysis_inputs as inputs
from banto_ai import anomaly_v03_slice_fixture as fixture
from tests import test_anomaly_v03_slice_fixture as hand


class RawSliceCountValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        primary = hand.hand.invented_input()
        candidate = fixture.I.CANDIDATES[0]
        cls.raw = hand.raw_cell(primary['clusters'][0]['candidates'][candidate]['core'],
                                primary['diagnostics'][0]['candidates'][candidate]['core'])

    def check(self, raw):
        fixture._raw_shape(raw, fixture.slices.empty_counts())
        inputs._validate_slice_raw(raw, 12)

    def test_valid_counts_and_descriptive_reader_agree_without_mutation(self):
        original = copy.deepcopy(self.raw)
        self.check(self.raw)
        reconstructed = inputs._slice_counts(fixture.slices.describe(self.raw), 12)
        self.assertEqual(reconstructed, original)
        self.assertEqual(self.raw, original)

    def test_each_count_partition_and_omission_failure_still_rejects(self):
        changes = {
            'boolean_count': lambda r: r['incident_slices']['class']['machine'].update(detected=True),
            'negative_count': lambda r: r['score_slices']['full-target'][fixture.slices.TARGETS[0]].update(planned=-1),
            'delay_shape': lambda r: r['delay_histogram'].pop(),
            'delay_count': lambda r: r['incident_slices']['class']['machine']['delay_histogram'].__setitem__(
                0, r['incident_slices']['class']['machine']['delay_histogram'][0] + 1),
            'incident_plan': lambda r: r['incident_slices']['class']['machine'].update(planned=121),
            'subset': lambda r: r['score_slices']['full-target'][fixture.slices.TARGETS[0]].update(signal_onsets=172801),
            'partition_omission': lambda r: r['score_slices']['phase']['0'].update(observed=5759, outside_test=1),
            'offset_reference': lambda r: r['score_slices']['event-offset']['0'].update(planned=481, unscored_target=121),
            'profile_coverage': lambda r: r.update(profile_inconclusive_evaluations=13),
            'context_subset': lambda r: r['equipment_context']['clean'].update(unmatched=172801),
            'clean_exposure': lambda r: r['equipment_context']['clean'].update(planned_seconds=40379),
            'context_exposure': lambda r: r['score_slices']['context']['grace'].update(planned=1679, observed=1679),
            'decision_partition': lambda r: r['score_slices']['quality-current']['ok'].update(signal_onsets=1),
        }
        for name, mutate in changes.items():
            raw = copy.deepcopy(self.raw)
            mutate(raw)
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.check(raw)

    def test_descriptive_reader_still_checks_derived_fields_and_row_inventory(self):
        for mutate in (
            lambda t: t['score_slices'].pop(),
            lambda t: t['incident_slices'][0].update(recall=-1),
            lambda t: t['delay_summary'].update(unit='milliseconds'),
            lambda t: t['equipment_context']['clean'].update(extra=0),
        ):
            table = copy.deepcopy(fixture.slices.describe(self.raw))
            mutate(table)
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                inputs._slice_counts(table, 12)


if __name__ == '__main__':
    unittest.main()
