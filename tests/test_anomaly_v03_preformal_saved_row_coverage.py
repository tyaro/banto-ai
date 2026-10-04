"""Pinned partial saved-row coverage never becomes a campaign aggregate."""
import copy
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_preformal_saved_row_coverage as coverage
from banto_ai import anomaly_v03_registered_saved_row_lineage as lineage
from tests.test_anomaly_v03_registered_saved_row_lineage import inputs
from tests.test_anomaly_v03_registered_saved_summary import pin


ROOT = r'D:\invented\artifacts\anomaly-v03-preformal-registered-attempt-t01'
OUTPUT = r'D:\invented\artifacts\anomaly-v03-preformal-saved-row-reread-t01'
REVISION = 'a' * 40


def make_entry():
    receipt, report, outer, _ = inputs()
    savepoint = {
        'format': coverage.SAVEPOINT_FORMAT,
        'mode': 'preformal-fixture', 'invented_only': True,
        'chunk_index': 0, 'run_root': ROOT + r'\run-root',
        'campaign_completed': False,
        'actual_registered_observations_read': False,
    }
    savepoint_raw = v.canonical_json(savepoint)
    receipt['savepoint_pin'] = pin(savepoint_raw)
    receipt_raw = v.canonical_json(receipt)
    report['savepoint_pin'] = pin(savepoint_raw)
    report['receipt_pin'] = pin(receipt_raw)
    report_raw = v.canonical_json(report)
    outer['reader_result']['receipt_pin'] = pin(receipt_raw)
    outer['reader_result']['report_pin'] = pin(report_raw)
    outer['generated_output_pins']['saved/receipt.json'] = pin(receipt_raw)
    outer['generated_output_pins']['saved/report.json'] = pin(report_raw)
    outer['generated_output_pins']['saved/savepoint.json'] = pin(savepoint_raw)
    outer_raw = v.canonical_json(outer)
    rows = lineage.bind_saved_reader_rows(
        receipt_raw, report_raw, outer_raw, chunk_index=0,
        expected_receipt_pin=pin(receipt_raw),
        expected_report_pin=pin(report_raw),
        expected_outer_result_pin=pin(outer_raw))
    manifest = {
        'format': coverage.MANIFEST_FORMAT,
        'scope': 'invented-registered-format-owned-generator-only',
        'root': ROOT, 'revision': REVISION, 'chunk_index': 0,
        'recipe_id': 'invented-test-recipe',
        'source': {'revision': REVISION, 'selected_files': []},
        'source_snapshots': {REVISION: {'file': 'aGlzdG9yaWNhbA=='}},
        'source_snapshot_pins': {'file': pin(b'historical')},
        'output_pins': outer['generated_output_pins'],
        'output_file_count': len(outer['generated_output_pins']),
        'output_bytes': sum(value['bytes'] for value in
                            outer['generated_output_pins'].values()),
        'invented_only': True,
        'actual_registered_observations_read': False,
        'formal_permission': False,
    }
    manifest_raw = v.canonical_json(manifest)
    selected_source = {'revision': REVISION}
    runtime = {'invented': True}
    stdout = {
        'format': coverage.CHILD_FORMAT, 'status': 'read',
        'process': {'pid': 42, 'parent_pid': 41, 'start_token': 'token'},
        'source': selected_source, 'runtime': runtime,
        'manifest_pin': pin(manifest_raw),
        'output_pins': outer['generated_output_pins'],
        'reader_result': outer['reader_result'],
        'actual_registered_observations_read': False,
        'formal_permission': False,
    }
    stdout_raw = (v.canonical_json(stdout) + b'\n')
    supervision = {
        'format': coverage.SUPERVISION_FORMAT,
        'status': 'complete', 'exit_code': 0,
        'worker_started': True, 'worker_exit_confirmed': True,
        'worker_pid': 42, 'stop_reason': None,
        'formal_permission': False, 'output': pin(stdout_raw),
    }
    budget = {
        'format': coverage.BUDGET_FORMAT,
        'passed': True, 'monitor_exit_confirmed': True,
        'stop_reason': None, 'formal_permission': False,
        'enforcement': 'sampled-and-cooperative-not-hard-quota',
        'scope': 'one-fixture-call-and-new-receipt-directory',
        'shared_root': None, 'samples': 3,
    }
    result = {
        'format': coverage.REREAD_FORMAT,
        'scope': 'one-invented-saved-chunk-reader-to-row-projection',
        'status': 'verified', 'reason': None, 'chunk_index': 0,
        'source_root': ROOT, 'output_root': OUTPUT,
        'manifest_path': r'D:\invented\artifacts\anomaly-v03-preformal-generated-pinsets-t01\pins.json',
        'row_projection_path': OUTPUT + r'\rows.json',
        'historic_source_revision': REVISION,
        'current_revision': REVISION,
        'external_saved_payload_bytes': manifest['output_bytes'],
        'selected_current_source': selected_source,
        'selected_current_source_after': selected_source,
        'runtime': runtime, 'runtime_after': runtime,
        'manifest_pin': pin(manifest_raw),
        'row_projection_pin': pin(v.canonical_json(rows)),
        'old_outer_result_pin': pin(outer_raw),
        'receipt_pin': pin(receipt_raw), 'report_pin': pin(report_raw),
        'resource_budget_pin': pin(v.canonical_json(budget)),
        'reader_supervision_pin': pin(v.canonical_json(supervision)),
        'child_stdout_pin': pin(stdout_raw),
        'child_pid': 42, 'child_start_token': 'token',
        'child_exit_confirmed': True, 'child_status': 'complete',
        'budget_passed': True,
        'external_saved_payload_bytes_in_directory_budget': False,
        'external_saved_payloads_reopened_in_child': True,
        'fresh_saved_payload_bytes_rechecked_this_run': True,
        'fresh_owned_reader_exit_confirmed_here': True,
        'fresh_reader_equal_prior_reader': True,
        'row_projection_in_same_budget': True,
        'verified_chunks': 1, 'verified_evaluations': 6,
        'source_closure_complete': False,
        'runtime_closure_complete': False,
        'execution_authenticated': False, 'result_trusted': False,
        'campaign_completed': False,
        'full_end_to_end_budget_measured': False,
        'registered_observations_read': False,
        'actual_registered_observations_read': False,
        'campaign_evaluations_credited': 0,
        'formal_permission': False, 'analysis_authorized': False,
        'promotion_allowed': False, 'independent_s6_complete': False,
    }
    objects = {'result': result, 'rows': rows, 'manifest': manifest,
               'receipt': receipt, 'report': report, 'savepoint': savepoint,
               'budget': budget, 'supervision': supervision,
               'stdout': stdout, 'outer': outer}
    entry = {name + '_raw': stdout_raw if name == 'stdout' else
             v.canonical_json(value) for name, value in objects.items()}
    entry['expected_pins'] = {name: pin(entry[name + '_raw']) for name in objects}
    return entry, objects


def rewrap(entry, name, value):
    entry[name + '_raw'] = (v.canonical_json(value) + b'\n') if name == 'stdout' \
        else v.canonical_json(value)
    entry['expected_pins'][name] = pin(entry[name + '_raw'])


class SavedRowCoverageTests(unittest.TestCase):
    def test_one_chunk_is_partial_and_pure(self):
        entry, _ = make_entry()
        with patch('builtins.open', side_effect=AssertionError('unexpected I/O')):
            result = coverage.collect_saved_row_coverage([entry])
        self.assertEqual((result['bound_chunks'], result['bound_evaluations']),
                         (1, 6))
        self.assertEqual(result['chunk_indices'], [0])
        self.assertEqual(result['missing_chunk_indices'], list(range(1, 480)))
        self.assertEqual(result['status'], 'partial_coverage_unanchored')
        self.assertIsNone(result['producer_campaign_anchor'])
        self.assertFalse(result['campaign_coherence_authenticated'])
        self.assertIsNone(result['clusters'])
        self.assertIsNone(result['diagnostics'])
        self.assertIsNone(result['slice_source'])
        self.assertFalse(result['formal_permission'])
        self.assertEqual(result['campaign_evaluations_credited'], 0)

    def test_empty_inventory_remains_closed(self):
        result = coverage.collect_saved_row_coverage([])
        self.assertEqual(result['missing_chunk_indices'], list(range(480)))
        self.assertEqual(result['bound_evaluations'], 0)
        self.assertFalse(result['campaign_coherence_authenticated'])

    def test_total_input_bound_precedes_semantic_decode(self):
        entry, _ = make_entry()
        total = sum(len(entry[name + '_raw']) for name in coverage.RAW_LIMITS)
        with patch.object(coverage, 'MAX_TOTAL_INPUT_BYTES', total - 1):
            with self.assertRaisesRegex(ValueError, 'total coverage input byte bound'):
                coverage.collect_saved_row_coverage([entry])

    def test_duplicate_and_out_of_order_index_rejected(self):
        entry, _ = make_entry()
        with self.assertRaisesRegex(ValueError, 'strictly increasing unique'):
            coverage.collect_saved_row_coverage([entry, copy.deepcopy(entry)])

    def test_external_pin_and_reread_links_rejected(self):
        entry, objects = make_entry()
        bad = copy.deepcopy(entry)
        bad['expected_pins']['rows'] = pin(b'wrong')
        with self.assertRaisesRegex(ValueError, 'external rows pin'):
            coverage.collect_saved_row_coverage([bad])
        bad = copy.deepcopy(entry)
        result = copy.deepcopy(objects['result'])
        result['row_projection_pin'] = pin(b'wrong')
        rewrap(bad, 'result', result)
        with self.assertRaisesRegex(ValueError, 'reread rows pin'):
            coverage.collect_saved_row_coverage([bad])

    def test_savepoint_source_and_budget_claims_rejected(self):
        entry, objects = make_entry()
        for name, change, reason in (
            ('savepoint', {'chunk_index': 1}, 'invented savepoint chunk_index'),
            ('manifest', {'recipe_id': ''}, 'historical recipe/source declaration'),
            ('budget', {'passed': False}, 'budget receipt passed'),
            ('supervision', {'worker_exit_confirmed': False},
             'owned reader supervision worker_exit_confirmed'),
        ):
            bad = copy.deepcopy(entry)
            value = copy.deepcopy(objects[name])
            value.update(change)
            rewrap(bad, name, value)
            with self.subTest(name=name), self.assertRaises(ValueError):
                coverage.collect_saved_row_coverage([bad])

    def test_fresh_stdout_and_reprojected_identity_required(self):
        entry, objects = make_entry()
        bad = copy.deepcopy(entry)
        stdout = copy.deepcopy(objects['stdout'])
        stdout['reader_result']['chunk_index'] = 1
        rewrap(bad, 'stdout', stdout)
        with self.assertRaises(ValueError):
            coverage.collect_saved_row_coverage([bad])
        bad = copy.deepcopy(entry)
        rows = copy.deepcopy(objects['rows'])
        rows['rows'][0]['identity'] = rows['rows'][1]['identity']
        rewrap(bad, 'rows', rows)
        result = copy.deepcopy(objects['result'])
        result['row_projection_pin'] = bad['expected_pins']['rows']
        rewrap(bad, 'result', result)
        with self.assertRaisesRegex(ValueError, 'fresh reread row projection'):
            coverage.collect_saved_row_coverage([bad])

    def test_latest_attempt_claim_cannot_go_stale(self):
        entry, objects = make_entry()
        bad = copy.deepcopy(entry)
        report = copy.deepcopy(objects['report'])
        report['attempt'] = 2
        rewrap(bad, 'report', report)
        outer = copy.deepcopy(objects['outer'])
        outer['reader_result']['report_pin'] = bad['expected_pins']['report']
        outer['generated_output_pins']['saved/report.json'] = bad['expected_pins']['report']
        rewrap(bad, 'outer', outer)
        manifest = copy.deepcopy(objects['manifest'])
        manifest['output_pins']['saved/report.json'] = bad['expected_pins']['report']
        rewrap(bad, 'manifest', manifest)
        stdout = copy.deepcopy(objects['stdout'])
        stdout['manifest_pin'] = bad['expected_pins']['manifest']
        stdout['output_pins'] = outer['generated_output_pins']
        stdout['reader_result'] = outer['reader_result']
        rewrap(bad, 'stdout', stdout)
        supervision = copy.deepcopy(objects['supervision'])
        supervision['output'] = bad['expected_pins']['stdout']
        rewrap(bad, 'supervision', supervision)
        result = copy.deepcopy(objects['result'])
        for field, key in (('manifest_pin', 'manifest'), ('old_outer_result_pin', 'outer'),
                           ('report_pin', 'report'), ('child_stdout_pin', 'stdout'),
                           ('reader_supervision_pin', 'supervision')):
            result[field] = bad['expected_pins'][key]
        rewrap(bad, 'result', result)
        with self.assertRaisesRegex(ValueError, 'report attempt'):
            coverage.collect_saved_row_coverage([bad])


if __name__ == '__main__':
    unittest.main()
