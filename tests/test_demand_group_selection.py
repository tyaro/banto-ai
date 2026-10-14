import datetime as dt
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from demand_group_selection import FIT, GROUP_C, POSITIVE, cohort_split, DualSelector, progress


def fixture_keys():
    train = [str(dt.date(2013, 5, 7)+dt.timedelta(days=14*k)) for k in range(30)]
    validation = [str(dt.date(2014, 7, 1)+dt.timedelta(days=14*k)) for k in range(12)]
    return [(s, d) for s in POSITIVE for d in train+validation]


class StoreSelectionChecks(unittest.TestCase):
    def test_transfer_stores_never_enter_fit_and_full_key_accounting(self):
        parts = cohort_split(fixture_keys())
        self.assertEqual([len(parts[k]) for k in ('fit', 'time_validation', 'transfer_validation', 'unused_C_preperiod')], [300, 120, 60, 150])
        self.assertEqual(set(s for s, _ in parts['fit']), set(FIT))
        self.assertEqual(set(s for s, _ in parts['transfer_validation']), set(GROUP_C))
        combined = [k for name in ('fit', 'time_validation', 'transfer_validation', 'unused_C_preperiod') for k in parts[name]]
        self.assertEqual(len(set(combined)), 630)

    def test_crossing_duplicate_or_missing_keys_cannot_be_replaced(self):
        keys = fixture_keys()
        for bad in (keys[:-1], keys+keys[:1], [(keys[0][0], '2014-06-18')]+keys[1:]):
            with self.assertRaises(ValueError):
                cohort_split(bad)

    def test_time_improvement_cannot_cancel_transfer_stop(self):
        policy = DualSelector(interval=1, warmup=1, patience=2, min_relative=.01)
        policy.observe(0, 1, 1)
        policy.observe(1, .9, 1.1)
        value = policy.observe(2, .8, 1.2)
        self.assertTrue(value['stop'])
        self.assertEqual(value['time_best_step'], 2)
        self.assertEqual(value['transfer_best_step'], 0)
        with self.assertRaises(ValueError):
            policy.observe(3, .7, .9)

    def test_transfer_improvement_can_continue_while_time_worsens(self):
        policy = DualSelector(interval=1, warmup=1, patience=1, min_relative=.01)
        policy.observe(0, 1, 1)
        value = policy.observe(1, 1.1, .8)
        self.assertFalse(value['stop'])
        self.assertEqual(value['time_best_step'], 0)
        self.assertEqual(value['transfer_best_step'], 1)

    def test_invalid_checkpoint_does_not_change_either_best(self):
        policy = DualSelector(interval=1, warmup=1, patience=2, min_relative=.01)
        policy.observe(0, 1, 1)
        for a, b in ((float('nan'), .1), (.1, float('nan'))):
            with self.assertRaises(ValueError):
                policy.observe(1, a, b)
            self.assertEqual(policy.time_best, 1)
            self.assertEqual(policy.transfer.best, 1)
            self.assertEqual(policy.transfer.last_step, 0)

    def test_joint_gain_does_not_hide_total_harm_or_coverage_loss(self):
        baseline = {'daily': 1., 'total': 1., 'joint': 1.}
        candidate = {'daily': .8, 'total': 1.1, 'joint': .95}
        self.assertFalse(progress(candidate, baseline, True)['development_progress'])
        good = {'daily': .9, 'total': .9, 'joint': .9}
        self.assertFalse(progress(good, baseline, False)['development_progress'])
        result = progress(good, baseline, True)
        self.assertTrue(result['development_progress'])
        self.assertFalse(result['business_adoption'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
