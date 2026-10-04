"""One invented saved-reader chunk cannot become a complete holdout source."""
import copy
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_registered_saved_row_lineage as lineage
from tests.test_anomaly_v03_registered_saved_summary import example, pin


def inputs(chunk_index=0):
    receipt, report, payloads = example()
    assert chunk_index == 0
    receipt_raw = v.canonical_json(receipt)
    report_raw = v.canonical_json(report)
    reader = {
        'format': lineage.READER_FORMAT,
        'mode': 'preformal-fixture',
        'status': 'latest_chunk_saved_bytes_bound',
        'scope': 'invented-registered-format-actual-attempt-layout-only',
        'fixture_physical_layout': 'run-attempt-result-payload',
        'chunk_index': 0, 'latest_state': 'complete', 'latest_attempt': 1,
        'latest_rows_bound': 6, 'registered_evaluation_contracts_checked': 6,
        'failed_attempts': 0,
        'receipt_pin': pin(receipt_raw), 'report_pin': pin(report_raw),
        'payload_pins': report['payload_pins'],
        'saved_payload_bytes_verified': True,
        'external_report_bytes_verified': True,
        'source_savepoint_bytes_verified': True,
        'reported_score_ledger_recomputed': True,
        'reported_score_to_primary_summary_checked': True,
        'reported_score_to_slice_summary_recomputed': True,
        'invented_observation_profile_score_recomputed': True,
        'observation_to_summary_recomputed': True,
        'invented_registered_format_observations_read': True,
        'actual_registered_observations_read': False,
        'registered_observations_read': False,
        'actual_worker_exit_authenticated': False,
        'reader_result_provenance_authenticated': False,
        'real_saved_chunk_reader_used': False,
        'formal_permission': False, 'analysis_authorized': False,
        'promotion_allowed': False, 'independent_s6_complete': False,
        'campaign_evaluations_credited': 0,
        'clusters': None, 'diagnostics': None, 'slice_source': None,
    }
    output_pins = dict(report['payload_pins'])
    output_pins.update({
        'saved/receipt.json': pin(receipt_raw),
        'saved/report.json': pin(report_raw),
        'saved/registry.json': receipt['registry_pin'],
        'saved/savepoint.json': receipt['savepoint_pin'],
    })
    outer = {
        'format': lineage.OUTER_FORMAT, 'status': 'verified', 'reason': None,
        'owned_fixture_generator_executed': True,
        'owned_fixture_generator_exit_confirmed': True,
        'owned_fixture_reader_executed': True,
        'owned_fixture_reader_exit_confirmed': True,
        'actual_registered_observations_read': False,
        'registered_observations_read': False,
        'registered_seed_consumed': False,
        'campaign_completed': False,
        'formal_permission': False, 'campaign_evaluations_credited': 0,
        'source_closure_complete': False, 'runtime_closure_complete': False,
        'generated_output_pins': output_pins,
        'reader_result': reader,
    }
    return receipt, report, outer, payloads


def bind(receipt, report, outer, **kwargs):
    receipt_raw = v.canonical_json(receipt)
    report_raw = v.canonical_json(report)
    outer_raw = v.canonical_json(outer)
    return lineage.bind_saved_reader_rows(
        receipt_raw, report_raw, outer_raw, chunk_index=kwargs.get('chunk_index', 0),
        expected_receipt_pin=kwargs.get('receipt_pin', pin(receipt_raw)),
        expected_report_pin=kwargs.get('report_pin', pin(report_raw)),
        expected_outer_result_pin=kwargs.get('outer_pin', pin(outer_raw)))


class SavedRowLineageTests(unittest.TestCase):
    def test_one_chunk_normalizes_six_rows_and_remains_partial(self):
        receipt, report, outer, _ = inputs()
        with patch('builtins.open', side_effect=AssertionError('unexpected IO')):
            result = bind(receipt, report, outer)
        self.assertEqual((result['verified_chunks'], result['planned_chunks']), (1, 480))
        self.assertEqual((result['verified_evaluations'], result['planned_evaluations']),
                         (6, 2880))
        self.assertEqual((result['registered_seed_index'], result['invented_cluster_id']),
                         (0, 'invented-00'))
        self.assertEqual((result['verified_layouts_for_seed'], result['planned_layouts_for_seed']),
                         (1, 12))
        self.assertEqual([row['identity'] for row in result['rows']],
                         v.evaluation_inventory('holdout')[:6])
        self.assertEqual(result['rows'][0]['primary'], report['rows'][0]['primary'])
        self.assertEqual(result['rows'][0]['slices'], report['rows'][0]['slices'])
        self.assertIsNone(result['clusters'])
        self.assertIsNone(result['diagnostics'])
        self.assertIsNone(result['slice_source'])
        self.assertFalse(result['saved_payload_bytes_rechecked'])
        self.assertFalse(result['reader_execution_authenticated_here'])
        self.assertFalse(result['formal_permission'])
        self.assertEqual(result['campaign_evaluations_credited'], 0)

    def test_external_pins_and_outer_reader_claims_are_required(self):
        receipt, report, outer, _ = inputs()
        with self.assertRaisesRegex(ValueError, 'external invented report pin'):
            bind(receipt, report, outer, report_pin=pin(b'wrong'))
        with self.assertRaisesRegex(ValueError, 'external owned outer result pin'):
            bind(receipt, report, outer, outer_pin=pin(b'wrong'))
        changed = copy.deepcopy(outer)
        changed['status'] = 'failed'
        with self.assertRaisesRegex(ValueError, 'owned outer result status'):
            bind(receipt, report, changed)
        changed = copy.deepcopy(outer)
        changed['reader_result']['observation_to_summary_recomputed'] = False
        with self.assertRaisesRegex(ValueError, 'nested reader result observation_to_summary_recomputed'):
            bind(receipt, report, changed)
        changed = copy.deepcopy(outer)
        changed['generated_output_pins']['saved/report.json'] = pin(b'wrong')
        with self.assertRaisesRegex(ValueError, 'owned output control pin'):
            bind(receipt, report, changed)

    def test_latest_attempt_and_identity_order_fail_closed(self):
        receipt, report, outer, _ = inputs()
        changed = copy.deepcopy(receipt)
        changed['attempts'][0]['state'] = 'failed'
        changed['attempts'][0]['failure'] = {
            'stage': 'supervision', 'reason': 'worker_exit', 'evidence_sha256': None}
        with self.assertRaises(ValueError):
            bind(changed, report, outer)
        changed = copy.deepcopy(report)
        changed['rows'][0]['identity'] = report['rows'][1]['identity']
        changed_outer = copy.deepcopy(outer)
        changed_outer['reader_result']['report_pin'] = pin(v.canonical_json(changed))
        changed_outer['generated_output_pins']['saved/report.json'] = pin(v.canonical_json(changed))
        with self.assertRaisesRegex(ValueError, 'frozen report identity/order'):
            bind(receipt, changed, changed_outer)
        with self.assertRaisesRegex(ValueError, 'registered chunk index'):
            bind(receipt, report, outer, chunk_index=480)

    def test_primary_and_slice_mutations_fail_even_when_re_pinned(self):
        receipt, report, outer, _ = inputs()
        for kind in ('count', 'slice'):
            changed = copy.deepcopy(report)
            if kind == 'count':
                changed['rows'][0]['primary']['counts']['machine_recall'][1] -= 1
            else:
                changed['rows'][0]['slices']['incident_slices']['class']['machine']['planned'] -= 1
            changed_outer = copy.deepcopy(outer)
            changed_outer['reader_result']['report_pin'] = pin(v.canonical_json(changed))
            changed_outer['generated_output_pins']['saved/report.json'] = pin(v.canonical_json(changed))
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                bind(receipt, changed, changed_outer)

    def test_latest_retry_is_selected_and_old_report_is_rejected(self):
        receipt, report, outer, _ = inputs()
        failed = copy.deepcopy(receipt['attempts'][0])
        failed['state'] = 'failed'
        failed['failure'] = {
            'stage': 'supervision', 'reason': 'worker_exit', 'evidence_sha256': None}
        failed['evaluations'][-1].update(
            status='partial', profile_status='not_evaluated',
            evaluation_sha256=None)
        receipt['attempts'] = [failed, copy.deepcopy(receipt['attempts'][0])]
        receipt['attempts'][1]['attempt'] = 2
        report['attempt'] = 2
        report['receipt_pin'] = pin(v.canonical_json(receipt))
        outer['reader_result']['latest_attempt'] = 2
        outer['reader_result']['failed_attempts'] = 1
        outer['reader_result']['receipt_pin'] = pin(v.canonical_json(receipt))
        outer['reader_result']['report_pin'] = pin(v.canonical_json(report))
        outer['generated_output_pins']['saved/receipt.json'] = pin(v.canonical_json(receipt))
        outer['generated_output_pins']['saved/report.json'] = pin(v.canonical_json(report))
        self.assertEqual(bind(receipt, report, outer)['latest_attempt'], 2)
        stale = copy.deepcopy(report)
        stale['attempt'] = 1
        outer['reader_result']['report_pin'] = pin(v.canonical_json(stale))
        outer['generated_output_pins']['saved/report.json'] = pin(v.canonical_json(stale))
        with self.assertRaisesRegex(ValueError, 'report attempt'):
            bind(receipt, stale, outer)


if __name__ == '__main__':
    unittest.main()
