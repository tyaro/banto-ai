"""Independent primary numeric checks and explicit limits on the audit claim."""
import ast
import copy
from pathlib import Path
import unittest
from unittest.mock import patch
from banto_ai import anomaly_v03_fixture_numeric_audit as audit
from tests import test_anomaly_v03_slice_fixture as hand


def connected(fixture):
    base = hand.connection.document.build_fixture_document(fixture,hand.SCHEMA)
    return hand.connection.attach_fixture_slices(base,fixture,hand.invented_slices(fixture),hand.SCHEMA)


class NumericAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = hand.hand.invented_input();cls.document = connected(cls.fixture)

    def check(self, document=None, fixture=None):
        return audit.audit_primary_document(self.fixture if fixture is None else fixture,
                                           self.document if document is None else document)

    def mutate_tables(self, change):
        doc = copy.deepcopy(self.document)
        for tables in (doc['document_draft']['candidate_tables'],doc['fixture_packet']['fixture_candidate_tables']):change(tables)
        return doc

    def test_stdlib_only_and_no_shared_calculation_or_validation_calls(self):
        tree = ast.parse(Path(audit.__file__).read_text(encoding='utf-8'))
        imports = {n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)}
        imports |= {a.name for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names}
        self.assertEqual(imports,{'fractions','hashlib','json','math'})
        with (patch.object(hand.connection.document,'build_fixture_document',side_effect=AssertionError('producer')),
              patch.object(hand.connection.I,'compute_fixture_tables',side_effect=AssertionError('shared numerics'))):
            result = self.check()
        self.assertEqual((result['candidate_tables'],result['primary_estimates'],result['paired_estimates'],result['gates']),(9,117,72,180))
        self.assertTrue(result['fixture_numerical_audit_performed']);self.assertFalse(result['independent_s6_complete'])

    def test_hand_calculated_ratio_interval_and_paired_difference(self):
        metric = audit._estimate(self.fixture,audit.CANDIDATES[1],'core','machine_recall')
        self.assertEqual((metric['numerator'],metric['denominator']),(4600,4800))
        self.assertEqual(metric['value'],115/120)
        self.assertAlmostEqual(metric['ci_lower'],.95+.075*(115/120-.95))
        self.assertAlmostEqual(metric['ci_upper'],115/120+.925*(116/120-115/120))
        delta = audit._estimate(self.fixture,audit.CANDIDATES[1],'core','machine_recall',True)
        self.assertAlmostEqual(delta['ci_lower'],(116/120-102/120)+.075*((115/120-99/120)-(116/120-102/120)))

    def test_resealed_point_or_interval_mutation_rejected(self):
        for key in ('value','ci_lower','ci_upper'):
            def change(tables):tables[3]['metrics']['machine_recall'][key] += .001
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'primary tables'):self.check(self.mutate_tables(change))

    def test_wrong_paired_interval_not_difference_of_separate_bounds(self):
        def change(tables):
            left,right = tables[3]['metrics']['machine_recall'],tables[0]['metrics']['machine_recall']
            gate = next(g for g in tables[3]['gates'] if g['name']=='machine_recall' and g['comparison']=='paired-control')
            gate['lower'] = left['ci_lower']-right['ci_lower']
        with self.assertRaisesRegex(ValueError,'primary tables'):self.check(self.mutate_tables(change))

    def test_overall_counts_and_effective_exposure_mutations_rejected(self):
        for kind in ('counts','exposure'):
            def change(tables):
                if kind == 'counts':tables[5]['metrics']['sensor_recall']['numerator'] += 1
                else:tables[5]['metrics']['effective_clean_seconds'] += 1
            with self.subTest(kind=kind),self.assertRaises(ValueError):self.check(self.mutate_tables(change))

    def test_delay_union_not_mean_of_cluster_medians(self):
        expected = audit._delay([2,2,4,5]);self.assertEqual(expected['median'],3.)
        self.assertEqual(expected['mean'],3.25)
        def change(tables):tables[5]['metrics']['delay_summary']['median'] = 3.
        with self.assertRaises(ValueError):self.check(self.mutate_tables(change))

    def test_gate_equality_inclusive_and_just_outside_fails(self):
        estimate = {'value':.85,'ci_lower':.80,'ci_upper':.90,'ci_status':'complete','null_replicates':0}
        self.assertEqual(audit._gate('machine_recall','core',estimate,False)['status'],'pass')
        estimate['ci_lower'] = .799999999
        self.assertEqual(audit._gate('machine_recall','core',estimate,False)['status'],'fail')
        estimate.update(value=0.,ci_lower=0.,ci_upper=.25)
        self.assertEqual(audit._gate('clean_rate','overall',estimate,True)['status'],'pass')
        estimate['ci_upper'] = .250000001
        self.assertEqual(audit._gate('clean_rate','overall',estimate,True)['status'],'fail')

    def test_zero_denominators_keep_all_replicates_and_null_delay(self):
        fixture = hand.hand.invented_input(zero_control=True);doc = connected(fixture)
        self.check(doc,fixture)
        metric = audit._estimate(fixture,audit.CANDIDATES[0],'core','precision')
        self.assertEqual((metric['null_replicates'],metric['ci_status'],metric['value']),(4,'inconclusive',None))
        self.assertIsNone(audit._delay([])['median'])

    def test_unavailable_control_profile_closes_qualification(self):
        fixture = copy.deepcopy(self.fixture)
        fixture['clusters'][0]['candidates'][audit.CANDIDATES[0]]['core']['profile_status'] = 'inconclusive'
        doc = connected(fixture);self.check(doc,fixture)
        self.assertIsNone(doc['document_draft']['selected_candidate'])
        paired = audit._estimate(fixture,audit.CANDIDATES[1],'core','machine_recall',True)
        self.assertEqual(paired['ci_status'],'inconclusive');self.assertEqual(paired['null_replicates'],0)

    def test_false_readiness_never_qualifies(self):
        fixture = copy.deepcopy(self.fixture);fixture['engineering_ready_assumption'] = False
        doc = connected(fixture);self.check(doc,fixture)
        self.assertIsNone(doc['document_draft']['selected_candidate'])

    def test_inventory_draw_domain_and_fixed_denominators(self):
        for kind in ('nine','bool','denominator','identity'):
            fixture = copy.deepcopy(self.fixture)
            if kind == 'nine':fixture['draws'] *= 3
            if kind == 'bool':fixture['draws'][0][0] = True
            if kind == 'denominator':fixture['clusters'][0]['candidates'][audit.CANDIDATES[0]]['core']['counts']['machine_recall'][1] = 121
            if kind == 'identity':fixture['clusters'][0]['cluster_id'] = 'registered-00'
            with self.subTest(kind=kind),self.assertRaises(ValueError):self.check(fixture=fixture)

    def test_selection_mapping_and_formal_claims_rejected(self):
        for kind in ('selection','formal','packet'):
            doc = copy.deepcopy(self.document)
            if kind == 'selection':doc['document_draft']['selected_candidate'] = audit.CANDIDATES[2]
            if kind == 'formal':doc['formal_permission'] = True
            if kind == 'packet':doc['fixture_packet']['formal_permission'] = True
            with self.subTest(kind=kind),self.assertRaises(ValueError):self.check(doc)

    def test_slice_numbers_explicitly_outside_primary_audit(self):
        doc = copy.deepcopy(self.document);doc['document_draft']['slices'] = []
        result = self.check(doc)
        self.assertIn('slice and diagnostic-sidecar derivation',result['not_checked'])
        self.assertFalse(result['independent_s6_complete'])


if __name__ == '__main__':unittest.main()
