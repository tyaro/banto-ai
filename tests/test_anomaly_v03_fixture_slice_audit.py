"""Independent slice mapping, conserved-total mutations and explicit boundaries."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from banto_ai import anomaly_v03_fixture_slice_audit as audit
from tests import test_anomaly_v03_slice_fixture as hand


class SliceAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = hand.hand.invented_input();cls.source = hand.invented_slices(cls.fixture)
        cls.base = hand.connection.document.build_fixture_document(cls.fixture,hand.SCHEMA)
        cls.document = hand.connection.attach_fixture_slices(cls.base,cls.fixture,cls.source,hand.SCHEMA)

    def check(self, *, document=None, source=None, fixture=None):
        return audit.audit_slices(self.fixture if fixture is None else fixture,
            self.source if source is None else source,self.document if document is None else document)

    def raw_case(self):
        source = copy.deepcopy(self.source)
        return source,source['clusters'][0]['candidates'][audit.CANDIDATES[0]]['core']

    def reseal_source(self, source):
        doc = copy.deepcopy(self.document)
        doc['slice_input_canonical_sha256'] = hashlib.sha256(audit.canonical(source)).hexdigest()
        return doc

    def test_independent_stdlib_only_and_full_inventory(self):
        tree = ast.parse(Path(audit.__file__).read_text(encoding='utf-8'))
        self.assertFalse(any(isinstance(n,ast.ImportFrom) for n in ast.walk(tree)))
        self.assertEqual({a.name for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names},{'hashlib','json'})
        with (patch.object(hand.connection.slices,'describe',side_effect=AssertionError('producer describe')),
              patch.object(hand.connection.slices,'add_counts',side_effect=AssertionError('producer grouping')),
              patch.object(hand.connection.report,'_mapped_slice',side_effect=AssertionError('producer mapping'))):
            result = self.check()
        self.assertEqual((result['main_slice_rows'],result['diagnostic_rows'],result['diagnostic_tables']),(1233,2835,9))
        self.assertTrue(result['fixture_slice_audit_performed']);self.assertFalse(result['independent_s6_complete'])
        self.assertIn('raw producer observation derivation',result['not_checked'])

    def test_known_recall_and_event_offset_denominator(self):
        self.check()
        cell = hand.pick(self.document['document_draft']['slices'])
        self.assertEqual((cell['metric']['numerator'],cell['metric']['denominator']),(4600,4800))
        cell = hand.pick(self.document['diagnostic_series']['score-availability'],dimension='event-offset',key='minus-2')
        self.assertEqual((cell['planned_count'],cell['metric']['numerator'],cell['metric']['denominator']),(19200,6720,13440))
        self.assertEqual(cell['metric']['value'],.5)

    def test_main_and_each_sidecar_series_mutation_rejected(self):
        for name in ('main',*audit.SERIES):
            doc = copy.deepcopy(self.document)
            rows = doc['document_draft']['slices'] if name == 'main' else doc['diagnostic_series'][name]
            row = next(r for r in rows if r['metric']['denominator']);row['metric']['value'] += .001
            with self.subTest(name=name),self.assertRaises(ValueError):self.check(document=doc)

    def test_details_omissions_histogram_and_profile_mutation_rejected(self):
        for kind in ('omissions','histogram','profile','exposure'):
            doc = copy.deepcopy(self.document);detail = doc['diagnostic_details'][0]
            if kind == 'omissions':next(c for c in detail['score_slices'] if c['dimension']=='event-offset')['outside_test'] += 1
            if kind == 'histogram':detail['delay_histogram'][0] += 1
            if kind == 'profile':detail['profile_inconclusive_evaluations'] = 1
            if kind == 'exposure':detail['equipment_context']['clean']['planned_seconds'] += 1
            with self.subTest(kind=kind),self.assertRaisesRegex(ValueError,'diagnostic details'):self.check(document=doc)

    def test_duplicate_missing_and_relabelled_rows_rejected(self):
        for kind in ('duplicate','missing','labels','overall'):
            doc = copy.deepcopy(self.document);rows = doc['document_draft']['slices']
            if kind == 'duplicate':rows[1] = copy.deepcopy(rows[0])
            if kind == 'missing':rows.pop()
            if kind == 'labels':rows[0]['key'],rows[1]['key'] = rows[1]['key'],rows[0]['key']
            if kind == 'overall':next(r for r in rows if r['stratum']=='overall')['planned_count'] += 1
            with self.subTest(kind=kind),self.assertRaisesRegex(ValueError,'main slice rows'):self.check(document=doc)

    def test_joint_reassignment_with_unchanged_totals_rejected(self):
        source,raw = self.raw_case();cells = raw['incident_slices']['class-equipment-mode']
        left,right = cells['machine.motor-01.stopped'],cells['sensor.conveyor-01.cooldown']
        self.assertLess(left['detected'],left['planned']);self.assertGreater(right['detected'],0)
        bucket = next(i for i,n in enumerate(right['delay_histogram']) if n)
        left['detected'] += 1;right['detected'] -= 1
        left['delay_histogram'][bucket] += 1;right['delay_histogram'][bucket] -= 1
        with self.assertRaisesRegex(ValueError,'joint/marginal'):self.check(source=source,document=self.reseal_source(source))

    def test_target_mode_reassignment_with_unchanged_totals_rejected(self):
        source,raw = self.raw_case();cells = raw['score_slices']['signal-mode']
        left,right = next((a,b) for a in cells for b in cells if a.rsplit('.',1)[0] != b.rsplit('.',1)[0] and cells[a]['available'] != cells[b]['available'])
        cells[left],cells[right] = cells[right],cells[left]
        with self.assertRaisesRegex(ValueError,'target/mode'):self.check(source=source,document=self.reseal_source(source))

    def test_raw_shapes_integer_domains_and_partition_omissions(self):
        for kind in ('missing','extra','bool','negative','histogram','omissions','subset'):
            source,raw = self.raw_case()
            if kind == 'missing':del raw['incident_slices']['class']['machine']
            if kind == 'extra':raw['score_slices']['quality-current']['extra'] = {}
            if kind == 'bool':raw['evaluations'] = True
            if kind == 'negative':raw['profile_inconclusive_evaluations'] = -1
            if kind == 'histogram':raw['delay_histogram'].append(0)
            if kind == 'omissions':raw['score_slices']['event-offset']['minus-2']['outside_test'] += 1
            if kind == 'subset':raw['score_slices']['full-target'][audit.TARGETS[0]]['available'] = 21601
            with self.subTest(kind=kind),self.assertRaises(ValueError):self.check(source=source,document=self.reseal_source(source))

    def test_per_cluster_profile_and_primary_binding(self):
        source,raw = self.raw_case();raw['profile_inconclusive_evaluations'] = 1
        with self.assertRaisesRegex(ValueError,'profile binding'):self.check(source=source,document=self.reseal_source(source))
        doc = copy.deepcopy(self.document);doc['document_draft']['candidate_tables'][0]['metrics']['precision']['denominator'] += 1
        with self.assertRaisesRegex(ValueError,'primary precision binding'):self.check(document=doc)

    def test_histogram_binding_detects_consistent_partition_shift(self):
        source,raw = self.raw_case()
        # Move every delay bucket one second; partitions still agree internally.
        raw['delay_histogram'] = raw['delay_histogram'][1:]+raw['delay_histogram'][:1]
        for cells in raw['incident_slices'].values():
            for cell in cells.values():cell['delay_histogram'] = cell['delay_histogram'][1:]+cell['delay_histogram'][:1]
        with self.assertRaisesRegex(ValueError,'per-cluster delay binding'):self.check(source=source,document=self.reseal_source(source))

    def test_zero_denominator_and_null_states(self):
        fixture = hand.hand.invented_input(zero_control=True);source = hand.invented_slices(fixture)
        base = hand.connection.document.build_fixture_document(fixture,hand.SCHEMA)
        doc = hand.connection.attach_fixture_slices(base,fixture,source,hand.SCHEMA)
        self.check(fixture=fixture,source=source,document=doc)
        row = next(r for r in doc['diagnostic_series']['score-availability'] if not r['metric']['denominator'])
        self.assertIsNone(row['metric']['value']);self.assertEqual(row['metric']['ci_status'],'not_applicable')
        row['metric']['value'] = 0
        with self.assertRaises(ValueError):self.check(fixture=fixture,source=source,document=doc)

    def test_changed_offset_reference_recomputed_with_observed_denominator(self):
        source,raw = self.raw_case();cell = raw['score_slices']['event-offset']['minus-2']
        cell.update(observed=0,available=0,threshold_exceeded=0,signal_onsets=0,outside_test=360)
        doc = hand.connection.attach_fixture_slices(self.base,self.fixture,source,hand.SCHEMA)
        self.check(source=source,document=doc)
        changed = self.reseal_source(source)
        with self.assertRaisesRegex(ValueError,'main slice rows'):self.check(source=source,document=changed)

    def test_input_identity_and_pin_binding(self):
        for kind in ('digest','identity','registered','extra_cluster','candidate'):
            source = copy.deepcopy(self.source);doc = copy.deepcopy(self.document)
            if kind == 'digest':doc['slice_input_canonical_sha256'] = 'f'*64
            if kind == 'identity':source['clusters'][0]['cluster_id'] = 'invented-01'
            if kind == 'registered':source['invented_only'] = False
            if kind == 'extra_cluster':source['clusters'].append(copy.deepcopy(source['clusters'][0]))
            if kind == 'candidate':source['clusters'][0]['candidates']['other'] = {}
            with self.subTest(kind=kind),self.assertRaises(ValueError):self.check(source=source,document=doc)

    def test_sorted_json_and_literal_delay_hand_values(self):
        self.check(source=json.loads(json.dumps(self.source,sort_keys=True)))
        result = audit.delay_summary([0,2,0,1,1])
        self.assertEqual((result['median'],result['mean'],result['min'],result['max']),(3.,3.25,2.,5.))
        self.assertIsNone(audit.delay_summary([0]*5)['mean'])
        with self.assertRaises(ValueError):audit.delay_summary([True,0,0,0,0])


if __name__ == '__main__':unittest.main()
