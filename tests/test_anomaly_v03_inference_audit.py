"""Hand counts and fixed index metadata only; never generate observations."""
import ast
import copy
import inspect
import json
import math
from pathlib import Path
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_inference_audit as audit

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT/'examples/configs/anomaly-multiseed-analysis-v0.3.json').read_text(encoding='utf-8'))


def hand_clusters(*, c1=95, c2=95, zero_control=False):
    """Two invented identical clusters; all bootstrap distributions are constant."""
    clusters = []
    for index in range(2):
        candidates = {}
        for candidate, machine in zip(audit.CANDIDATES, (0 if zero_control else 80, c1, c2)):
            layers = {}
            for layer in audit.STRATA[:2]:
                sensor = (0 if zero_control else 80) if candidate == audit.CANDIDATES[0] else (95 if layer == 'core' else 90)
                false = 5 if candidate == audit.CANDIDATES[0] and not zero_control else 0
                matched = machine + sensor
                values = {'machine_recall': [machine, 100], 'sensor_recall': [sensor, 100],
                    'precision': [matched, matched + false], 'clean_rate': [false, 28800],
                    'false_alert_burden': [false, 200],
                    **{name: [970 if layer == 'core' else 960, 1000] for name in audit.AVAILABILITY}}
                layers[layer] = {'profile_status': 'calibrated', 'counts': values}
            candidates[candidate] = layers
        clusters.append({'cluster_id': f'hand-{index}', 'candidates': candidates})
    return clusters


HAND_DRAWS = ((0, 0), (0, 1), (1, 0), (1, 1))


class DrawAndRuleTests(unittest.TestCase):
    def test_only_stdlib_no_numerical_or_producer_import(self):
        allowed = {'__future__', 'collections', 'hashlib', 'json', 'math'}
        for node in ast.walk(ast.parse(inspect.getsource(audit))):
            if isinstance(node, ast.Import):
                self.assertTrue(all(n.name in allowed for n in node.names))
            elif isinstance(node, ast.ImportFrom):
                self.assertEqual(node.level, 0)
                self.assertIn(node.module, allowed)

    def test_registered_golden_rows(self):
        for row in CONFIG['bootstrap']['golden_draws']:
            self.assertEqual([audit.draw_index(row['replicate'], j) for j in range(40)], row['indices'])

    def test_rejection_cutoff_counter_reset_and_big_endian(self):
        cutoff = 2**256 - 2**256 % 40
        values = iter((cutoff, 2**256 - 1, cutoff-1, 256))
        keys = []
        class Hex:
            def __init__(self, n): self.n = n
            def hexdigest(self): return f'{self.n:064x}'
        def digest(raw):
            keys.append(raw)
            return Hex(next(values))
        with patch.object(audit.hashlib, 'sha256', side_effect=digest):
            self.assertEqual(audit.draw_index(7, 3), 39)
            self.assertEqual(audit.draw_index(7, 4), 16)
        self.assertEqual(keys, [f'sha256-counter-rejection-v1:2026090603:7:{j}:{c}'.encode('ascii')
                                for j, c in ((3,0),(3,1),(3,2),(4,0))])

    def test_invalid_draw_coordinates_and_declared_size_rejected(self):
        for b, j in ((True,0),(-1,0),(50000,0),(0,True),(0,40)):
            with self.assertRaises(ValueError): audit.draw_index(b,j)
        for key, value in (('clusters',10),('replicates',10),('seed',20260905),('accepted_indices',True)):
            declared = copy.deepcopy(CONFIG['bootstrap'])
            declared[key] = value
            with patch.object(audit, 'draw_index', side_effect=AssertionError('must reject first')):
                with self.assertRaises(ValueError): audit.verify_draw_contract(declared)

    def test_rule_contract_matches_frozen_config_and_rejects_drift(self):
        report = audit.verify_rule_contract(CONFIG)
        self.assertEqual(report['absolute_gate_checks'] + report['paired_gate_checks'], 180)
        for mutation in ('threshold','order','unit','control','alpha'):
            config = copy.deepcopy(CONFIG)
            if mutation == 'threshold': config['absolute_gates'][0]['machine_recall'][1] = .79
            elif mutation == 'order': config['selection_order'].reverse()
            elif mutation == 'unit': config['units']['clean_rate'] = 'per-hour'
            elif mutation == 'control': config['control_promotable'] = True
            else: config['multiple_testing']['candidate_alpha'] = .05
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): audit.verify_rule_contract(config)


class ArithmeticTests(unittest.TestCase):
    def test_type7_hand_interpolation_endpoints_and_degenerate(self):
        values = [100., 0., 10., 20.]
        self.assertEqual(audit.type7(values,0), 0.)
        self.assertEqual(audit.type7(values,1), 100.)
        # Decimal hand answers tolerate binary64 interpolation's final ulp.
        self.assertAlmostEqual(audit.type7(values,.025), .75, places=14)
        self.assertAlmostEqual(audit.type7(values,.975), 94., places=12)
        self.assertEqual(audit.type7(values,.5), 15.)
        self.assertEqual(audit.type7([7.],.975), 7.)
        self.assertEqual(values, [100., 0., 10., 20.])

    def test_ratio_of_sums_not_mean_and_repeated_cluster_weights(self):
        result = audit.estimate_counts([(1,1),(0,9)], ((0,0),(0,1),(1,1)), 'precision')
        self.assertEqual((result['numerator'],result['denominator'],result['value']), (1,10,.1))
        self.assertAlmostEqual(result['ci_lower'],.005)
        self.assertAlmostEqual(result['ci_upper'],.955)
        self.assertNotEqual(result['value'], .5)

    def test_same_draw_for_paired_difference(self):
        counts = [(1,1),(0,9)]
        result = audit.estimate_counts(counts, HAND_DRAWS, 'machine_recall', baseline=counts)
        self.assertEqual((result['value'],result['ci_lower'],result['ci_upper']), (0.,0.,0.))
        baseline = [(1,4),(9,10)]
        result = audit.estimate_counts(counts, ((0,1),), 'machine_recall', baseline=baseline)
        self.assertAlmostEqual(result['value'], .1-10/14)
        self.assertEqual(result['value'],result['ci_lower'])

    def test_exposure_and_burden_units(self):
        result = audit.estimate_counts([(1,14400),(2,14400)], ((0,1),), 'clean_rate')
        self.assertEqual(result['value'], 3.)
        result = audit.estimate_counts([(1,10),(2,90)], ((0,1),), 'false_alert_burden')
        self.assertEqual(result['value'], 3.)

    def test_any_null_replicate_blocks_ci_without_drop_or_redraw(self):
        result = audit.estimate_counts([(0,0),(1,2)], HAND_DRAWS, 'precision')
        self.assertEqual(result['value'], .5)
        self.assertEqual(result['null_replicates'], 1)
        self.assertEqual(result['ci_status'], 'inconclusive')
        self.assertIsNone(result['ci_lower'])
        self.assertIsNone(result['ci_upper'])
        # The control's zero denominator also invalidates that paired replicate.
        result = audit.estimate_counts([(1,1),(1,1)], HAND_DRAWS, 'precision', baseline=[(0,0),(1,2)])
        self.assertEqual(result['null_replicates'],1)
        self.assertEqual(result['ci_status'],'inconclusive')

    def test_null_point_profile_inconclusive_and_all_nulls(self):
        for point, samples, ready, nulls in ((None,[.5],True,0),(.5,[.5],False,0),(None,[None,None],True,2)):
            result = audit.interval(point,samples,ready=ready)
            self.assertEqual(result['ci_status'],'inconclusive')
            self.assertEqual(result['null_replicates'],nulls)
            self.assertIsNone(result['ci_lower'])

    def test_nonfinite_bool_negative_counts_and_invalid_draws_rejected(self):
        for pair in ((True,1),(1,True),(-1,1),(2,1),(1.,2),(0,41472001)):
            with self.assertRaises(ValueError): audit.estimate_counts([pair],((0,),),'precision')
        for draws in ((), ((0,),), ((0,True),), ((0,-1),), ((0,2),), ((0,1.),)):
            with self.assertRaises(ValueError): audit.estimate_counts([(1,1),(1,1)],draws,'precision')
        for value in (True,float('nan'),float('inf'),10**1000):
            with self.assertRaises(ValueError): audit.interval(value,[0.])
            with self.assertRaises(ValueError): audit.type7([value],.5)
        with self.assertRaises(ValueError): audit.type7([], .5)
        with self.assertRaises(ValueError): audit.type7([0.], True)
        with self.assertRaises(ValueError): audit.type7([0.], 1.1)

    def test_unrounded_inclusive_thresholds_both_point_and_bound_required(self):
        metric = audit.interval(.85, [.80])
        self.assertEqual(audit.gate(metric,'machine_recall','core')['status'],'pass')
        for value, lower in ((math.nextafter(.85,-math.inf),.80),(.85,math.nextafter(.80,-math.inf))):
            metric = audit.interval(value,[lower])
            self.assertEqual(audit.gate(metric,'machine_recall','core')['status'],'fail')
        metric = audit.interval(1.,[1.5])
        self.assertEqual(audit.gate(metric,'clean_rate','core')['status'],'pass')
        metric['ci_upper'] = math.nextafter(1.5, math.inf)
        self.assertEqual(audit.gate(metric,'clean_rate','core')['status'],'fail')

    def test_all_fixed_rules_equality_and_beyond_boundaries(self):
        for layer in audit.STRATA:
            for paired, names in ((False,audit.ABSOLUTE_METRICS),(True,audit.PAIRED_METRICS)):
                for name in names:
                    key = 'each_target_availability' if name in audit.AVAILABILITY else name
                    point, bound = (audit.PAIRED if paired else audit.ABSOLUTE[layer])[key]
                    metric = audit.interval(point,[bound])
                    self.assertEqual(audit.gate(metric,name,layer,paired=paired)['status'],'pass')
                    bad = math.nextafter(bound, math.inf if name in ('clean_rate','false_alert_burden') else -math.inf)
                    metric = audit.interval(point,[bad])
                    self.assertEqual(audit.gate(metric,name,layer,paired=paired)['status'],'fail')


class FixtureMatrixTests(unittest.TestCase):
    def run_fixture(self, clusters=None, ready=True):
        return audit.compute_fixture_tables(clusters if clusters is not None else hand_clusters(), HAND_DRAWS,
                                             engineering_ready=ready)

    def test_all_tables_and_gates_c1_first_with_permissions_closed(self):
        report = self.run_fixture()
        self.assertEqual(len(report['candidate_tables']),9)
        self.assertEqual(sum(len(t['gates']) for t in report['candidate_tables']),180)
        self.assertEqual(report['fixture_selected_candidate'],audit.CANDIDATES[1])
        self.assertTrue(all(t['fixture_qualified'] for t in report['candidate_tables'][3:]))
        self.assertFalse(any(t['fixture_qualified'] for t in report['candidate_tables'][:3]))
        self.assertIsNone(report['selected_candidate'])
        self.assertEqual(report['performance_status'],'not_evaluated')
        for key in ('formal_permission','promotion_allowed','independent_s6_complete'):
            self.assertIs(report[key],False)

    def test_c2_only_no_promotion_and_engineering_unready(self):
        self.assertEqual(self.run_fixture(hand_clusters(c1=50))['fixture_selected_candidate'],audit.CANDIDATES[2])
        self.assertEqual(self.run_fixture(hand_clusters(c1=50,c2=50))['fixture_decision'],'no_promotion')
        report = self.run_fixture(ready=False)
        self.assertEqual(report['fixture_decision'],'inconclusive')
        self.assertIsNone(report['fixture_selected_candidate'])

    def test_one_target_one_stratum_failure_blocks_candidate(self):
        clusters = hand_clusters()
        for cluster in clusters:
            cluster['candidates'][audit.CANDIDATES[1]]['quality-stress']['counts'][audit.AVAILABILITY[-1]][0] = 949
        report = self.run_fixture(clusters)
        self.assertFalse(report['candidate_tables'][3]['fixture_qualified'])
        self.assertEqual(report['fixture_selected_candidate'],audit.CANDIDATES[2])

    def test_control_profile_inconclusive_blocks_both(self):
        clusters = hand_clusters()
        clusters[0]['candidates'][audit.CANDIDATES[0]]['quality-stress']['profile_status']='inconclusive'
        report = self.run_fixture(clusters)
        self.assertIsNone(report['fixture_selected_candidate'])
        self.assertEqual(report['fixture_decision'],'inconclusive')
        for t in report['candidate_tables'][3:]:
            if t['stratum'] != 'core':
                self.assertTrue(all(v['ci_status']=='inconclusive' for v in t['paired_control'].values()))

    def test_zero_alert_control_precision_does_not_block_fixed_denominator_comparisons(self):
        report = self.run_fixture(hand_clusters(zero_control=True))
        self.assertEqual(report['candidate_tables'][0]['metrics']['precision']['ci_status'],'inconclusive')
        self.assertEqual(report['fixture_selected_candidate'],audit.CANDIDATES[1])
        self.assertNotIn('precision',report['candidate_tables'][3]['paired_control'])

    def test_overall_adds_counts_and_keeps_both_strata_in_same_draw(self):
        clusters = hand_clusters()
        for cluster in clusters:
            for layers in cluster['candidates'].values():
                for layer, n, d in (('core',1,1),('quality-stress',0,9)):
                    raw = layers[layer]['counts']
                    raw.update(machine_recall=[n,d],sensor_recall=[n,d],precision=[2*n,2*n],
                               false_alert_burden=[0,2*d],clean_rate=[0,28800])
        report = self.run_fixture(clusters)
        overall = report['candidate_tables'][2]['metrics']['machine_recall']
        self.assertEqual((overall['numerator'],overall['denominator'],overall['value']), (2,20,.1))
        self.assertEqual(overall['ci_lower'],.1)
        # Correlated strata must be retained together: every overall sum is 1/2.
        series = [t['candidates'][audit.CANDIDATES[0]] for t in clusters]
        for i, layers in enumerate(series):
            for layer in audit.STRATA[:2]:
                raw = layers[layer]['counts']
                n = i if layer == 'core' else 1-i
                raw.update(machine_recall=[n,1],sensor_recall=[n,1],precision=[2*n,2*n],false_alert_burden=[0,2])
        # Keep common planned denominators for the two challenger candidates.
        for cluster in clusters:
            for candidate in audit.CANDIDATES[1:]:
                cluster['candidates'][candidate]=copy.deepcopy(cluster['candidates'][audit.CANDIDATES[0]])
        report = self.run_fixture(clusters)
        overall = report['candidate_tables'][2]['metrics']['machine_recall']
        self.assertEqual((overall['value'],overall['ci_lower'],overall['ci_upper']),(.5,.5,.5))

    def test_missing_duplicate_or_mismatched_inventory_and_counts_rejected(self):
        for mutation in ('duplicate','candidate','stratum','target','denominator','partition','bool','profile'):
            clusters = hand_clusters()
            row = clusters[0]['candidates'][audit.CANDIDATES[1]]['core']
            if mutation=='duplicate': clusters[1]['cluster_id']=clusters[0]['cluster_id']
            elif mutation=='candidate': del clusters[0]['candidates'][audit.CANDIDATES[2]]
            elif mutation=='stratum': del clusters[0]['candidates'][audit.CANDIDATES[1]]['quality-stress']
            elif mutation=='target': del row['counts'][audit.AVAILABILITY[-1]]
            elif mutation=='denominator': row['counts']['machine_recall'][1]+=1
            elif mutation=='partition': row['counts']['precision'][0]-=1
            elif mutation=='bool': row['counts']['clean_rate'][0]=False
            else: row['profile_status']='failed'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): self.run_fixture(clusters)


if __name__ == '__main__':
    unittest.main()
