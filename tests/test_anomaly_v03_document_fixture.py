"""Bounded invented forty-cluster wiring and hand-derived paired CI checks."""
import copy
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_document_fixture as fixture
from tests import test_anomaly_v03_analysis_adapter as hand

SCHEMA = hand.SCHEMA


def invented_input(*, ready=True, c1=114, c2=114, zero_control=False):
    base, diagnostic = hand.hand_inputs(c1=c1, c2=c2, zero_control=zero_control)
    clusters, diagnostics = [], []
    for index, identifier in enumerate(fixture.IDS):
        cluster, detail = copy.deepcopy((base[index % 2], diagnostic[index % 2]))
        cluster['cluster_id'] = detail['cluster_id'] = identifier
        # Two equal halves with distinct recall, exposure and delay, so the
        # paired delta is NOT difference of separately computed CI bounds.
        if not zero_control and index >= 20:
            for candidate in fixture.I.CANDIDATES:
                for layer in fixture.I.STRATA[:2]:
                    counts = cluster['candidates'][candidate][layer]['counts']
                    increment = 6 if candidate == fixture.I.CANDIDATES[0] else 2
                    counts['machine_recall'][0] += increment
                    counts['precision'][0] += increment
                    counts['precision'][1] += increment
                    detail['candidates'][candidate][layer]['detected_delays'] += [4]*increment
                    detail['candidates'][candidate][layer]['effective_clean_seconds'] = 39000
        clusters.append(cluster); diagnostics.append(detail)
    return {'format': fixture.FORMAT, 'invented_only': True,
            'clusters': clusters, 'diagnostics': diagnostics,
            'draws': [[0]*40, list(range(40)), list(reversed(range(40))), [39]*40],
            'engineering_ready_assumption': ready}


def build(**kwargs):
    return fixture.build_fixture_document(invented_input(**kwargs), SCHEMA)


class DocumentFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.example = build()

    def test_forty_clusters_hand_calculated_absolute_and_paired_bounds(self):
        result = self.example
        table = result['document_draft']['candidate_tables'][3]
        metric = table['metrics']['machine_recall']
        self.assertEqual((metric['numerator'], metric['denominator']), (4600, 4800))
        self.assertEqual(metric['value'], 4600/4800)
        # Type-7 2.5/97.5 percentiles of [.95,115/120,115/120,116/120].
        self.assertAlmostEqual(metric['ci_lower'], .95+.075*(115/120-.95))
        self.assertAlmostEqual(metric['ci_upper'], 115/120+.925*(116/120-115/120))
        gate = next(g for g in table['gates'] if g['name']=='machine_recall'
                    and g['comparison']=='paired-control')
        lo, mid, hi = 116/120-102/120, 115/120-99/120, 114/120-96/120
        self.assertAlmostEqual(gate['point'], mid)
        self.assertAlmostEqual(gate['lower'], lo+.075*(mid-lo))
        self.assertAlmostEqual(gate['upper'], mid+.925*(hi-mid))
        self.assertEqual(table['metrics']['effective_clean_seconds'], 1580000)
        self.assertEqual(len(result['fixture_draws']), 4)
        self.assertEqual(sum(len(t['gates']) for t in result['document_draft']['candidate_tables']),180)

    def test_all_ten_fields_mapped_without_inventing_missing_evidence(self):
        result = self.example
        self.assertEqual(tuple(result['document_draft']), fixture.FIELDS)
        self.assertEqual([r['field'] for r in result['field_coverage']],list(fixture.FIELDS))
        for field in fixture.PENDING:
            self.assertIsNone(result['document_draft'][field])
        self.assertEqual(result['fixture_packet']['fixture_selected_candidate'], 'c1-phase-level')
        for field, expected in fixture.CLOSED.items():
            self.assertEqual(result[field], expected)
        with self.assertRaises(ValueError):
            fixture.contract.validate_result_contract(result)
        with self.assertRaises(ValueError):
            fixture.contract.validate_result_contract(result['document_draft'])

    def test_overall_raw_sums_and_detected_delay_union(self):
        rows = self.example['document_draft']['candidate_tables']
        core, stress, overall = [r['metrics'] for r in rows[3:6]]
        self.assertEqual(overall['machine_recall']['denominator'],9600)
        self.assertEqual(overall['sensor_recall']['numerator'],8880)
        self.assertEqual(overall['effective_clean_seconds'],3160000)
        self.assertEqual(overall['delay_summary']['count'],18080)
        self.assertEqual(overall['delay_summary']['median'],4)
        self.assertEqual(overall['delay_summary']['mean'],54320/18080)

    def test_input_is_unchanged_and_output_does_not_alias_it_or_packet(self):
        source = invented_input(); before = copy.deepcopy(source)
        result = fixture.build_fixture_document(source,SCHEMA)
        self.assertEqual(source,before)
        self.assertEqual(result['input_canonical_sha256'],fixture.contract.canonical_sha256(source))
        result['fixture_draws'][0][0]=2
        result['document_draft']['candidate_tables'][0]['qualified']=True
        self.assertEqual(source,before)
        self.assertFalse(result['fixture_packet']['fixture_candidate_tables'][0]['qualified'])

    def test_inventory_and_real_input_fields_rejected_before_inference(self):
        base=invented_input()
        for mutate in (lambda v:v.update(role='holdout'),
                       lambda v:v.update(invented_only=False),
                       lambda v:v.update(engineering_ready_assumption=1),
                       lambda v:v['clusters'].pop(),
                       lambda v:v['clusters'][0].update(seed=123),
                       lambda v:v['clusters'][0].update(cluster_id='invented-01'),
                       lambda v:v['clusters'].reverse()):
            value=copy.deepcopy(base);mutate(value)
            with self.subTest(mutate=mutate), patch.object(fixture.adapter,'compute_fixture_packet',side_effect=AssertionError('inference reached')):
                with self.assertRaises(ValueError):fixture.build_fixture_document(value,SCHEMA)

    def test_draw_limits_and_index_types_rejected_before_inference(self):
        for draws in ([],[[0]*40]*65,[[0]*40]*50000,[[0]*39],[[40]*40],[[True]*40],[[1.0]*40]):
            value=invented_input();value['draws']=draws
            with self.subTest(count=len(draws)),patch.object(fixture.adapter,'compute_fixture_packet',side_effect=AssertionError('inference reached')):
                with self.assertRaises(ValueError):fixture.build_fixture_document(value,SCHEMA)

    def test_unpaired_diagnostics_counts_and_denominators_rejected(self):
        base=invented_input()
        for mutate in (lambda v:v['diagnostics'].reverse(),
                       lambda v:v['diagnostics'][0]['candidates']['c1-phase-level']['core']['detected_delays'].pop(),
                       lambda v:v['clusters'][0]['candidates']['c1-phase-level']['core']['counts']['machine_recall'].__setitem__(1,119)):
            value=copy.deepcopy(base);mutate(value)
            with self.subTest(mutate=mutate),patch.object(fixture.I,'compute_fixture_tables',side_effect=AssertionError('inference reached')):
                with self.assertRaises(ValueError):fixture.build_fixture_document(value,SCHEMA)

    def test_undefined_control_precision_preserved_and_readiness_blocks_selection(self):
        zero=build(zero_control=True)
        # Control precision is not a paired non-inferiority metric. Its null
        # does not invent an additional selection rule for C1/C2.
        self.assertEqual(zero['document_draft']['selected_candidate'],'c1-phase-level')
        self.assertIsNone(zero['selected_candidate'])
        unready=build(ready=False)
        self.assertIsNone(unready['document_draft']['selected_candidate'])
        self.assertEqual(unready['document_draft']['decision'],'inconclusive')
        self.assertFalse(unready['formal_permission'])
        control=zero['document_draft']['candidate_tables'][0]['metrics']
        self.assertIsNone(control['precision']['value'])
        self.assertEqual(control['precision']['null_replicates'],4)

    def test_c2_fallback_and_no_promotion_mapping(self):
        c2=build(c1=100)
        neither=build(c1=100,c2=100)
        self.assertEqual(c2['document_draft']['selected_candidate'],'c2-phase-conditional')
        self.assertEqual(c2['document_draft']['decision'],'qualified')
        self.assertIsNone(neither['document_draft']['selected_candidate'])
        self.assertEqual(neither['document_draft']['decision'],'no_promotion')
        self.assertIsNone(c2['selected_candidate'])

    def test_bound_of_64_draws_is_supported_with_actual_dimensions(self):
        value=invented_input();value['draws']*=16
        result=fixture.build_fixture_document(value,SCHEMA)
        self.assertEqual(result['fixture_packet']['fixture_draws'],{'clusters':40,'replicates':64})
        self.assertIsNone(result['document_draft']['bootstrap'])
        self.assertFalse(result['formal_bootstrap_performed'])

    def test_schema_changes_are_not_accepted(self):
        schema=copy.deepcopy(SCHEMA)
        schema['properties']['bootstrap']['properties']['replicates']['const']=4
        with patch.object(fixture.adapter,'compute_fixture_packet',side_effect=AssertionError('inference reached')):
            with self.assertRaises(ValueError):fixture.build_fixture_document(invented_input(),schema)

    def test_document_and_acceptance_tampering_rejected_without_recomputation(self):
        for mutate in (lambda v:v.update(formal_permission=True),
                       lambda v:v.update(extra='x'),
                       lambda v:v['document_draft'].update(bootstrap={'replicates':50000}),
                       lambda v:v['document_draft'].update(slices=[]),
                       lambda v:v['document_draft'].update(selected_candidate='c2-phase-conditional'),
                       lambda v:v['field_coverage'].pop(),
                       lambda v:v['fixture_packet']['fixture_draws'].update(replicates=50000)):
            value=copy.deepcopy(self.example);mutate(value)
            with self.subTest(mutate=mutate),patch.object(fixture.I,'compute_fixture_tables',side_effect=AssertionError('recalculated')):
                with self.assertRaises(ValueError):fixture.validate_fixture_document(value,SCHEMA)


if __name__ == '__main__':
    unittest.main()
