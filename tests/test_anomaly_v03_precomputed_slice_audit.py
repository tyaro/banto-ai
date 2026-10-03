"""Saved-table slice audit: row tampering, bindings and limited claims."""
import copy
import hashlib
import unittest

from banto_ai import anomaly_v03_fixture_slice_audit as audit
from tests import test_anomaly_v03_slice_fixture as hand


def packet_for_rows(tables):
    # The pure slice audit only checks the precomputed table/count join.  These
    # unit-test tables are synthetic and are not evidence of 50,000 draws.
    return {
        'fixture_candidate_tables': tables,
        'fixture_decision': 'inconclusive',
        'fixture_draws': {'clusters': 40, 'replicates': 50000},
        'fixture_engineering_ready': False,
        'fixture_selected_candidate': None,
        'formal_document_emitted': False,
        'formal_permission': False,
        'independent_s6_complete': False,
        'not_validated': ['registered observations', 'saved primary arithmetic'],
        'performance_status': 'not_evaluated',
        'promotion_allowed': False,
        'scope': 'hand-fixture-analysis-tables-only',
        'selected_candidate': None,
        'validation': {
            'formal_document_validated': False,
            'gates': 180,
            'source_runtime_slices_validated': False,
            'status': 'fixture_table_contract_valid',
            'tables': 9,
        },
    }


def digest(value):
    return hashlib.sha256(audit.canonical(value)).hexdigest()


class PrecomputedSliceAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture = hand.hand.invented_input()
        base = hand.connection.document.build_fixture_document(fixture, hand.SCHEMA)
        source = hand.invented_slices(fixture)
        connected = hand.connection.attach_fixture_slices(base, fixture, source, hand.SCHEMA)
        cls.clusters = fixture['clusters']
        cls.diagnostics = fixture['diagnostics']
        cls.packet = packet_for_rows(base['document_draft']['candidate_tables'])
        cls.source = source
        cls.enriched = {
            'slices': connected['document_draft']['slices'],
            'diagnostic_series': connected['diagnostic_series'],
            'diagnostic_details': connected['diagnostic_details'],
            'primary_packet_canonical_sha256': digest(cls.packet),
            'slice_source_canonical_sha256': digest(source),
        }

    def check(self, **changes):
        value = {name: changes.get(name, getattr(self, name)) for name in
                 ('clusters', 'diagnostics', 'packet', 'source', 'enriched')}
        return audit.audit_precomputed_slices(**value)

    def test_all_rows_checked_without_claiming_primary_ci_or_formal_acceptance(self):
        result = self.check()
        self.assertEqual((result['main_slice_rows'], result['diagnostic_rows'],
                          result['diagnostic_tables']), (1233, 2835, 9))
        self.assertEqual(result['primary_packet_canonical_sha256'], digest(self.packet))
        self.assertEqual(result['slice_source_canonical_sha256'], digest(self.source))
        self.assertTrue(result['fixture_slice_audit_performed'])
        for name in ('primary_ci_gate_recomputed', 'formal_permission',
                     'independent_s6_complete', 'registered_data_read'):
            self.assertFalse(result[name])

    def test_main_each_sidecar_and_details_tamper_rejected(self):
        for name in ('main', *audit.SERIES, 'details'):
            enriched = copy.deepcopy(self.enriched)
            if name == 'main':
                enriched['slices'][0]['actual_count'] += 1
            elif name == 'details':
                enriched['diagnostic_details'][0]['delay_histogram'][0] += 1
            else:
                enriched['diagnostic_series'][name][0]['actual_count'] += 1
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.check(enriched=enriched)

    def test_primary_table_and_diagnostic_binding_rejected(self):
        packet = copy.deepcopy(self.packet)
        packet['fixture_candidate_tables'][0]['metrics']['machine_recall']['numerator'] += 1
        enriched = copy.deepcopy(self.enriched)
        enriched['primary_packet_canonical_sha256'] = digest(packet)
        with self.assertRaisesRegex(ValueError, 'primary recall binding'):
            self.check(packet=packet, enriched=enriched)

        diagnostics = copy.deepcopy(self.diagnostics)
        diagnostics[0]['candidates'][audit.CANDIDATES[0]]['core']['detected_delays'][0] = 5
        with self.assertRaisesRegex(ValueError, 'per-cluster delay binding'):
            self.check(diagnostics=diagnostics)

    def test_source_mismatch_even_if_its_digest_is_resealed(self):
        source = copy.deepcopy(self.source)
        source['clusters'][0]['candidates'][audit.CANDIDATES[0]]['core']['incident_slices']['class']['machine']['detected'] += 1
        enriched = copy.deepcopy(self.enriched)
        enriched['slice_source_canonical_sha256'] = digest(source)
        with self.assertRaises(ValueError):
            self.check(source=source, enriched=enriched)

    def test_digests_and_scope_downgrade_rejected(self):
        for key in ('primary_packet_canonical_sha256', 'slice_source_canonical_sha256'):
            enriched = copy.deepcopy(self.enriched)
            enriched[key] = '0' * 64
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.check(enriched=enriched)
        packet = copy.deepcopy(self.packet)
        packet['fixture_draws']['replicates'] = 4
        with self.assertRaises(ValueError):
            self.check(packet=packet)
        packet = copy.deepcopy(self.packet)
        packet['formal_permission'] = True
        with self.assertRaises(ValueError):
            self.check(packet=packet)


if __name__ == '__main__':
    unittest.main()
