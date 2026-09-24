"""Check descriptive aggregation against hand-worked cases and input boundaries."""
import copy
import hashlib
import itertools
from pathlib import Path
import tempfile
import unittest

from tools.evaluator import summarize_anomaly_v03_audits as summary


def row(detected=0, alerts=0, delay=None, seed=0):
    ratio = summary.ratio
    return {'identity': {'seed': seed}, 'incidents': 20, 'equipment_episodes': alerts,
        'metrics': {'machine_recall': ratio(detected, 10), 'sensor_recall': ratio(0, 10),
            'precision': ratio(detected, alerts), 'clean_rate': ratio(alerts-detected, 3365, 28800),
            'false_alert_burden': ratio(alerts-detected, 20, 100), 'scheduled_clean_seconds': 3365,
            'effective_clean_seconds': 3200, 'availability': [
                {'full_target': t, 'metric': ratio(1740, 1800)} for t in summary.TARGETS],
            'delay_summary': {'count': detected, 'mean': delay, 'median': delay, 'min': delay, 'max': delay,
                'conditioned_on': 'causal-detected-only', 'undetected_fill': 'forbidden', 'unit': 'seconds'}}}


class AuditSummaryTests(unittest.TestCase):
    def test_counts_and_delay_are_weighted_not_cell_averaged(self):
        first, second = row(1, 2, 1.0), row(9, 90, 9.0, seed=1)
        for item in (first, second):
            summary.validate_metrics(item)
        value = summary.aggregate([first, second])
        self.assertAlmostEqual(value['precision']['value'], 10/92)
        self.assertAlmostEqual(value['machine_recall']['value'], 10/20)
        self.assertAlmostEqual(value['clean_rate']['value'], 82*28800/6730)
        self.assertAlmostEqual(value['false_alert_burden']['value'], 82*100/40)
        self.assertAlmostEqual(value['delay']['mean_seconds'], 8.2)
        self.assertIsNone(value['delay']['median'])
        self.assertEqual(value['availability'][summary.TARGETS[0]]['denominator'], 3600)

    def test_zero_alert_precision_and_undetected_delay_stay_null(self):
        summary.validate_metrics(row())
        value = summary.aggregate([row(), row()])
        self.assertIsNone(value['precision']['value'])
        self.assertIsNone(value['delay']['mean_seconds'])
        self.assertEqual(value['machine_recall']['value'], 0)
        mixed = summary.aggregate([row(), row(1, 2, 2.0)])
        self.assertEqual(mixed['delay']['mean_seconds'], 2.0)
        self.assertEqual(mixed['machine_recall']['denominator'], 20)

    def test_invalid_partition_and_delays_rejected(self):
        cases = []
        wrong = row(1, 2, 1.0); wrong['equipment_episodes'] = 3; cases.append(wrong)
        wrong = row(); wrong['metrics']['delay_summary']['mean'] = 0; cases.append(wrong)
        wrong = row(); wrong['metrics']['availability'].pop(); cases.append(wrong)
        wrong = row(); wrong['metrics']['machine_recall']['denominator'] = 9; cases.append(wrong)
        for wrong in cases:
            with self.subTest(wrong=wrong), self.assertRaises(ValueError):
                summary.validate_metrics(wrong)

    def identities(self):
        return [{'evaluation_id': f'{role}-{seed}-{layout}-{layer}-{candidate}',
                 'role': role, 'seed': seed, 'layout': layout, 'stratum': layer, 'candidate_id': candidate}
                for role, seeds in (('dev', range(8)), ('smoke', range(8, 10)))
                for seed, layout, layer, candidate in itertools.product(seeds, range(12), summary.STRATA, summary.CANDIDATES)]

    def test_paired_inventory_missing_duplicate_holdout_and_order_rejected(self):
        identities = self.identities()
        rows = [{'identity': i} for i in identities]
        summary.check_inventory(rows, identities)
        with self.assertRaises(ValueError):
            summary.check_inventory(rows[:-1], identities[:-1])
        repeated = copy.deepcopy(identities); repeated[-1] = repeated[-2]
        with self.assertRaises(ValueError):
            summary.check_inventory([{'identity': i} for i in repeated], repeated)
        holdout = copy.deepcopy(identities); holdout[0]['role'] = 'holdout'
        with self.assertRaises(ValueError):
            summary.check_inventory([{'identity': i} for i in holdout], holdout)
        with self.assertRaises(ValueError):
            summary.check_inventory(rows[::-1], identities)

    def test_overall_recombines_counts_without_losing_stratum(self):
        identities = self.identities()
        rows = []
        for identity in identities:
            item = row(1, 2, 1.0) if identity['stratum'] == 'core' else row()
            item['identity'] = identity
            rows.append(item)
        result = summary.summarize(rows)
        groups = result['groups']
        select = lambda role, layer: next(r for r in groups if r['role']==role and r['stratum']==layer and r['candidate_id']==summary.CANDIDATES[0])
        self.assertEqual(select('dev', 'core')['evaluations'], 96)
        self.assertEqual(select('smoke', 'core')['evaluations'], 24)
        self.assertEqual(select('combined', 'overall')['evaluations'], 240)
        self.assertEqual(select('combined', 'overall')['machine_recall']['value'], 0.05)
        self.assertEqual(select('combined', 'overall')['precision']['value'], 0.5)
        self.assertEqual(select('combined', 'overall')['delay']['mean_seconds'], 1)
        self.assertEqual(len(result['paired_differences']), 18)

    def test_pin_tampering_and_duplicate_keys_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            p = Path(temporary) / 'audit.json'
            raw = b'{"count":1}'; p.write_bytes(raw)
            pin = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
            self.assertEqual(summary.read_pinned(p, pin), {'count': 1})
            p.write_bytes(b'{"count":2}')
            with self.assertRaises(ValueError):
                summary.read_pinned(p, pin)
        with self.assertRaises(ValueError):
            summary.strict_json(b'{"count":1,"count":2}')
        with self.assertRaises(ValueError):
            summary.strict_json(b'{"count":NaN}')

    def test_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, 'output already exists'):
                summary.run(Path('unused'), 'unused', Path(temporary))


if __name__ == '__main__':
    unittest.main()
