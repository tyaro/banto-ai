"""Pinned reader rows feed the existing numerical and slice consumers."""
import copy
from contextlib import ExitStack
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_fixture_numeric_audit as numeric_audit
from banto_ai import anomaly_v03_fixture_slice_audit as slice_audit
from banto_ai import anomaly_v03_saved_row_fixture_projection as projection
from banto_ai import anomaly_v03_bound_fixture_pipeline as pipeline
from tests import test_anomaly_v03_preformal_saved_seed_contribution as seed_fixture
from tests.test_anomaly_v03_preformal_saved_seed_contribution import chunk_entry
from tests.test_anomaly_v03_registered_saved_summary import pin


REVISION = 'b' * 40
DRAW = list(range(40))


class SavedRowFixtureProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # These are synthetic control bytes, not generated holdout observations.
        inventory = v.evaluation_inventory('holdout')
        base = seed_fixture.make_entry()
        # chunk_entry deep-copies this template before changing identities/pins.
        with patch.object(v, 'evaluation_inventory', return_value=inventory), \
                patch.object(seed_fixture, 'make_entry', return_value=base):
            cls.entries = [chunk_entry(i, latest_attempt=2 if i == 479 else 1,
                                       inconclusive_first=i == 0)
                           for i in range(480)]
            with patch('builtins.open', side_effect=AssertionError('unexpected I/O')), \
                    patch('subprocess.check_output',
                          side_effect=AssertionError('unexpected launch')):
                cls.prepared = projection.prepare_inputs(
                    cls.entries, expected_mode='fixture',
                    expected_revision=REVISION, draws=[DRAW])

    def prepare(self, entries=None, **options):
        arguments = dict(expected_mode='fixture', expected_revision=REVISION,
                         draws=[DRAW])
        arguments.update(options)
        return projection.prepare_inputs(
            self.entries if entries is None else entries,
            **arguments)

    def test_all_rows_rederive_counts_diagnostics_and_fixed_worker_files(self):
        prepared = self.prepared
        self.assertEqual(set(prepared['files']), set(projection.analysis.INPUT_LIMITS))
        values = {name: v.strict_json(raw) for name, raw in prepared['files'].items()}
        fixture = values['fixture/input.json']
        self.assertEqual(len(fixture['clusters']), 40)
        self.assertEqual(fixture['clusters'][39]['cluster_id'], 'invented-39')
        first_candidate = projection.seed.arithmetic.CANDIDATES[0]
        # Twelve layouts each contain ten machine events and 3365 clean seconds.
        for cluster in fixture['clusters']:
            cell = cluster['candidates'][first_candidate]['core']
            self.assertEqual(cell['counts']['machine_recall'][1], 120)
            self.assertEqual(cell['counts']['clean_rate'][1], 40380)
        self.assertEqual(values['fixture/slices.json']['clusters'][39]
                         ['candidates'][first_candidate]['core']['evaluations'], 12)
        binding = prepared['binding']
        self.assertEqual(binding['coverage']['counts']['success'], 2879)
        self.assertEqual(binding['coverage']['counts']['inconclusive'], 1)
        self.assertEqual(binding['source_chunks'][479]['latest_attempt'], 2)
        self.assertEqual(len(binding['source_chunks']), 480)
        self.assertEqual([(row['chunk_index'], row['attempt'], row['state'])
                          for row in binding['failed_attempt_history']],
                         [(479, 1, 'failed')])
        self.assertTrue(binding['saved_row_projection_rechecked_here'])
        self.assertTrue(binding['seed_contributions_rederived_from_rows_here'])
        for name, raw in prepared['files'].items():
            self.assertEqual(binding['worker_input_pins'][name], pin(raw))
        for key, wanted in projection.CLOSED.items():
            self.assertEqual(binding[key], wanted, key)
        self.assertNotEqual(binding['declared_historical_source_revision'], REVISION)

    def test_existing_worker_loads_exact_four_file_projection(self):
        files, binding = self.prepared['files'], self.prepared['binding']
        worker = projection.analysis
        request = {
            'format': worker.FORMAT, 'mode': 'fixture', 'role': 'analysis',
            'operation': worker.OPERATION,
            'expected_document_pin': pin(b'invented expected document'),
            'inputs': {name: {'path': 'D:/invented/' + name,
                             'pin': binding['worker_input_pins'][name], 'links': 1}
                       for name in files},
        }
        with patch.object(worker.observed, '_inputs', return_value=files), \
                patch('builtins.open', side_effect=AssertionError('unexpected I/O')):
            raw, values = worker._load(request, REVISION)
        self.assertEqual(raw, files)
        self.assertEqual(values['fixture/operation.json']['source_revision'], REVISION)
        self.assertFalse(values['fixture/input.json']['engineering_ready_assumption'])

    def test_primary_and_all_slice_consumers_independently_audit_projection(self):
        worker = projection.analysis
        values = {name: v.strict_json(raw) for name, raw in self.prepared['files'].items()}
        fixture = values['fixture/input.json']
        source = worker.wrapper._ordered_slice_input(values['fixture/slices.json'])
        schema = v.schemas(v._expected_configs())[7]
        with patch('builtins.open', side_effect=AssertionError('unexpected I/O')):
            document = worker.wrapper.document.build_fixture_document(fixture, schema)
            connected = worker.wrapper.slices.attach_fixture_slices(
                document, fixture, source, schema)
            numeric_audit.audit_primary_document(fixture, connected)
            slice_audit.audit_slices(fixture, source, connected)
        self.assertEqual(len(connected['document_draft']['slices']), 1233)
        self.assertEqual(sum(map(len, connected['diagnostic_series'].values())), 2835)
        self.assertEqual(len(connected['diagnostic_details']), 9)
        self.assertFalse(connected['formal_permission'])
        self.assertEqual(connected['document_draft']['bootstrap'], None)

    def test_formal_mode_revision_and_draw_contract_reject_before_rows(self):
        cases = [dict(expected_mode='formal'), dict(expected_revision='short'),
                 *[dict(draws=draws) for draws in (
                     [], [DRAW] * 9, [[0] * 39], [[40] * 40], [[True] * 40])]]
        for options in cases:
            arguments = dict(expected_mode='fixture', expected_revision=REVISION,
                             draws=[DRAW])
            arguments.update(options)
            with self.subTest(options=options), \
                    patch.object(projection.coverage, 'collect_saved_row_coverage',
                                 side_effect=AssertionError('invalid request reached rows')), \
                    self.assertRaises(ValueError):
                projection.prepare_inputs(self.entries, **arguments)

    def test_partial_inventory_cannot_start_contribution_or_consumer(self):
        with patch.object(projection.seed, '_contribution',
                          side_effect=AssertionError('partial input pooled')), \
                self.assertRaisesRegex(ValueError, 'complete ordered'):
            self.prepare(self.entries[:-1])

    def test_duplicate_out_of_order_and_modified_raw_reject(self):
        bad = copy.deepcopy(self.entries[0])
        bad['rows_raw'] += b' '
        for entries in ([self.entries[0], self.entries[0]],
                        [self.entries[1], self.entries[0]], [bad]):
            with self.subTest(kind=len(entries)), self.assertRaises(ValueError):
                self.prepare(entries)

    def test_stale_latest_attempt_cannot_supply_analysis_input(self):
        inventory = v.evaluation_inventory('holdout')
        with patch.object(v, 'evaluation_inventory', return_value=inventory):
            stale = chunk_entry(479, latest_attempt=2, stale_report=True)
        with self.assertRaises(ValueError):
            self.prepare([stale])

    def test_projected_size_limit_rejects_complete_inputs(self):
        with patch.object(projection.analysis, 'TOTAL_INPUT_LIMIT', 1), \
                self.assertRaisesRegex(ValueError, 'projected worker input limits'):
            self.prepare()

    def _run_pipeline(self, parent, *, audit_failed=False, projection_failed=False):
        def git(*arguments):
            if arguments == ('status', '--porcelain'):
                return b''
            if arguments[0] == 'show':
                return (pipeline.ROOT / arguments[1].split(':', 1)[1]).read_bytes()
            raise AssertionError(arguments)

        def role(request, **options):
            name = options['receipt_name']
            if name == 'audit' and audit_failed:
                return {'status': 'failed', 'resource_budget_passed': True}
            target = Path(options['receipt_parent']) / name
            target.mkdir()
            evidence_raw = v.canonical_json({
                'inputs': {key: value['pin'] for key, value in request['inputs'].items()}})
            (target / 'evidence.json').write_bytes(evidence_raw)
            return {'status': 'verified', 'resource_budget_passed': True,
                    'fixture_slice_audit_performed': name == 'audit',
                    'evidence_pin': pin(evidence_raw), 'result_pin': pin(b'fixture role')}

        with ExitStack() as stack:
            gib = 1024**3
            stack.enter_context(patch.object(pipeline.budgets, 'system_snapshot', return_value={
                'commit_total_bytes': gib, 'commit_limit_bytes': 16*gib,
                'commit_headroom_bytes': 15*gib, 'free_ram_bytes': 8*gib,
                'free_disk_bytes': 30*gib, 'parent_peak_private_bytes': 0}))
            prepared = stack.enter_context(patch.object(
                projection, 'prepare_inputs', return_value=self.prepared,
                side_effect=ValueError('bad saved rows') if projection_failed else None))
            stack.enter_context(patch.object(pipeline.analysis.observed, '_git_sources',
                                            return_value=(None, None, git)))
            analysis = stack.enter_context(patch.object(
                pipeline.analysis, 'calculate_with_evidence', side_effect=role))
            audit = stack.enter_context(patch.object(
                pipeline.audit, 'audit_with_evidence', side_effect=role))
            result = pipeline.run_saved_row_pipeline(
                self.entries, expected_mode='fixture', expected_revision=REVISION,
                draws=[DRAW], expected_document_pin=pin(b'invented expected document'),
                receipt_parent=parent, receipt_name='attempt')
        return result, prepared, analysis, audit

    def test_execution_entry_binds_projection_to_both_roles_and_keeps_history(self):
        with tempfile.TemporaryDirectory(prefix='banto-saved-rows-') as parent:
            result, prepared, analysis, audit = self._run_pipeline(parent)
            self.assertEqual(result['status'], 'verified')
            self.assertEqual((analysis.call_count, audit.call_count), (1, 1))
            self.assertEqual(result['inherited_failed_attempts'], 1)
            raw = (Path(parent) / 'attempt/projection.json').read_bytes()
            self.assertGreater(len(raw), 64*1024)
            self.assertEqual(pin(raw), result['projection_pin'])
            self.assertEqual(result['worker_input_pins'], self.prepared['binding']['worker_input_pins'])
            self.assertFalse(result['formal_permission'])
            self.assertFalse(result['campaign_coherence_authenticated'])
            self.assertEqual(result['new_evaluations'], 0)

    def test_bad_rows_stop_before_any_worker_and_preserve_failed_result(self):
        with tempfile.TemporaryDirectory(prefix='banto-bad-rows-') as parent:
            result, prepared, analysis, audit = self._run_pipeline(parent, projection_failed=True)
            self.assertEqual(result['status'], 'failed')
            self.assertEqual((analysis.call_count, audit.call_count), (0, 0))
            self.assertTrue((Path(parent) / 'attempt/result.json').is_file())

    def test_failed_audit_keeps_first_analysis_and_does_not_retry(self):
        with tempfile.TemporaryDirectory(prefix='banto-row-audit-') as parent:
            result, prepared, analysis, audit = self._run_pipeline(parent, audit_failed=True)
            self.assertEqual(result['status'], 'failed')
            self.assertEqual((analysis.call_count, audit.call_count), (1, 1))
            self.assertTrue(result['fixture_inference_performed'])
            self.assertFalse(result['fixture_slice_audit_performed'])


if __name__ == '__main__':
    unittest.main()
