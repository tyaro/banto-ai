"""One new owned invented reader and one measured partial-row projection."""
from __future__ import annotations

import base64
from contextlib import ExitStack, nullcontext
import copy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_preformal_saved_row_reread as reread
from tests.test_anomaly_v03_registered_saved_row_lineage import inputs, pin


OLD_REVISION = 'a' * 40
CURRENT_REVISION = 'b' * 40


class FakeBudget:
    stop_on = None

    def __init__(self, root):
        self.root = root
        self.limits = {'directory_bytes': 32 * 1024**2,
                       'directory_entries': 256}
        self.checkpoints = 0
        self.stopped = False

    def start(self):
        return None

    def checkpoint(self):
        self.checkpoints += 1
        if self.checkpoints == self.stop_on:
            self.stopped = True
        if self.stopped:
            raise reread.resources.ResourceStop('pipeline_wall_limit')

    def probe(self):
        return 'pipeline_wall_limit' if self.stopped else None

    def close(self):
        return {'passed': not self.stopped, 'monitor_exit_confirmed': True,
                'stop_reason': 'pipeline_wall_limit' if self.stopped else None,
                'formal_permission': False}


class SavedRowRereadTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        parent = Path(self.temporary.name)
        self.source = parent / 'old-source'
        self.target = parent / 'new-reread'
        self.manifest_path = parent / 'pinsets' / 'pins.json'
        (self.source / 'saved').mkdir(parents=True)
        (self.source / 'owned-generator').mkdir()
        self.manifest_path.parent.mkdir()
        receipt, report, outer, _ = inputs()
        self.receipt_raw = v.canonical_json(receipt)
        self.report_raw = v.canonical_json(report)
        self.outer_raw = v.canonical_json(outer)
        (self.source / 'saved/receipt.json').write_bytes(self.receipt_raw)
        (self.source / 'saved/report.json').write_bytes(self.report_raw)
        (self.source / 'owned-generator/result.json').write_bytes(self.outer_raw)
        self.output_pins = copy.deepcopy(outer['generated_output_pins'])
        self.old_reader = copy.deepcopy(outer['reader_result'])
        snapshot = b'old captured source bytes'
        self.manifest = {
            'format': 'anomaly-v03-preformal-owned-generated-external-pins-v1',
            'scope': 'invented-registered-format-owned-generator-only',
            'root': str(self.source), 'revision': OLD_REVISION,
            'chunk_index': 0, 'recipe_id': reread.generated.RECIPE,
            'source': {'revision': OLD_REVISION},
            'source_snapshots': {OLD_REVISION: {
                'src/example.py': base64.b64encode(snapshot).decode('ascii')}},
            'source_snapshot_pins': {'src/example.py': pin(snapshot)},
            'output_pins': self.output_pins,
            'output_file_count': 22,
            'output_bytes': sum(x['bytes'] for x in self.output_pins.values()),
            'invented_only': True,
            'actual_registered_observations_read': False,
            'formal_permission': False,
        }
        self.manifest_raw = v.canonical_json(self.manifest)
        self.manifest_path.write_bytes(self.manifest_raw)
        self.manifest_pin = pin(self.manifest_raw)
        self.outer_pin = pin(self.outer_raw)
        self.current_source = {'revision': CURRENT_REVISION,
                               'selected_files': [], 'scope': 'test-selected-source'}
        self.current_runtime = {'runtime': 'test'}

    def _run(self, *, child_status='complete', changed_reader=False,
             stop_on=None, campaign_context=None, tamper_echo=False):
        FakeBudget.stop_on = stop_on

        def supervise(argv, cwd, control, limits, *, boundary,
                      on_started, resource_probe):
            self.assertIsNone(resource_probe())
            boundary()
            control.mkdir()
            on_started(SimpleNamespace(pid=42, _handle=None))
            request = v.strict_json((self.target / 'owned-reader/invocation.json')
                                    .read_bytes())
            reader = copy.deepcopy(self.old_reader)
            if changed_reader:
                reader['reported_score_ledger_recomputed'] = False
            reply = {
                'format': (reread.CAMPAIGN_CHILD_FORMAT if campaign_context
                           is not None else reread.CHILD_FORMAT),
                'status': 'read',
                'invocation_id': request['invocation_id'],
                'process': {'pid': 42, 'parent_pid': reread.os.getpid(),
                            'start_token': 'new-owned-start'},
                'source': self.current_source,
                'runtime': self.current_runtime,
                'manifest_pin': self.manifest_pin,
                'output_pins': self.output_pins,
                'reader_result': reader,
                'actual_registered_observations_read': False,
                'formal_permission': False,
            }
            if campaign_context is not None:
                reply['campaign_context'] = copy.deepcopy(campaign_context)
                if tamper_echo:
                    reply['campaign_context']['chunk_index'] = 1
            raw = v.canonical_json(reply)
            (control / 'report.json').write_bytes(raw)
            (control / 'stderr.json').write_bytes(b'')
            return {'status': child_status,
                    'exit_code': 0 if child_status == 'complete' else 2,
                    'worker_pid': 42, 'worker_exit_confirmed': True,
                    'worker_started': True, 'output': pin(raw)}

        with ExitStack() as stack:
            stack.enter_context(patch.object(reread, '_roots',
                return_value=(self.source, self.target, self.manifest_path)))
            stack.enter_context(patch.object(reread.generated, '_outputs',
                return_value={key: key for key in self.output_pins}))
            stack.enter_context(patch.object(reread, '_source',
                return_value=self.current_source))
            stack.enter_context(patch.object(reread.runtime, 'probe_runtime',
                return_value=self.current_runtime))
            stack.enter_context(patch.object(reread.budget_module, 'FixtureBudget',
                FakeBudget))
            stack.enter_context(patch.object(reread.supervisor, 'supervise',
                side_effect=supervise))
            stack.enter_context(patch.object(reread.observed,
                'creation_observation',
                return_value={'pid': 42, 'start_token': 'new-owned-start'}))
            stack.enter_context(patch.object(reread.platform, '_platform_scope',
                return_value=nullcontext()))
            if campaign_context is not None:
                stack.enter_context(patch.object(
                    reread.child_context, 'verify_context',
                    return_value=campaign_context))
            return reread.run_reread(
                self.source, self.target,
                expected_manifest_pin=self.manifest_pin,
                expected_outer_result_pin=self.outer_pin,
                expected_revision=CURRENT_REVISION,
                campaign_context=campaign_context)

    def test_success_retains_rows_and_small_bounded_receipts(self):
        result = self._run()
        self.assertEqual(result['status'], 'verified')
        self.assertEqual(result['verified_evaluations'], 6)
        self.assertTrue(result['external_saved_payloads_reopened_in_child'])
        self.assertTrue(result['fresh_saved_payload_bytes_rechecked_this_run'])
        self.assertTrue(result['fresh_owned_reader_exit_confirmed_here'])
        self.assertTrue(result['fresh_reader_equal_prior_reader'])
        self.assertTrue(result['row_projection_in_same_budget'])
        self.assertTrue(result['child_exit_confirmed'])
        self.assertFalse(result['formal_permission'])
        rows_raw = (self.target / 'rows.json').read_bytes()
        self.assertEqual(pin(rows_raw), result['row_projection_pin'])
        rows = v.strict_json(rows_raw)
        self.assertFalse(rows['saved_payload_bytes_rechecked'])
        self.assertFalse(rows['reader_execution_authenticated_here'])
        self.assertIsNone(rows['clusters'])
        self.assertEqual(rows['campaign_evaluations_credited'], 0)
        self.assertLessEqual((self.target / 'result.json').stat().st_size,
                             reread.MAX_RESULT)
        self.assertLessEqual((self.target / 'resource-budget.json').stat().st_size,
                             reread.MAX_BUDGET)
        invocation = v.strict_json((self.target / 'owned-reader/invocation.json')
                                   .read_bytes())
        self.assertEqual(invocation['format'], reread.INVOCATION_FORMAT)
        self.assertNotIn('campaign_context', invocation)

    def test_campaign_context_reaches_fresh_reader_and_echo_is_required(self):
        context = {'plan_path': 'p', 'anchor_pin': pin(b'plan'),
                   'chunk_index': 0, 'attempt': 1}
        result = self._run(campaign_context=context)
        self.assertEqual(result['status'], 'verified')
        invocation = v.strict_json((self.target / 'owned-reader/invocation.json')
                                   .read_bytes())
        self.assertEqual(invocation['format'],
                         reread.CAMPAIGN_INVOCATION_FORMAT)
        self.assertEqual(invocation['campaign_context'], context)

    def test_modified_fresh_reader_echo_rejects_rows(self):
        context = {'plan_path': 'p', 'anchor_pin': pin(b'plan'),
                   'chunk_index': 0, 'attempt': 1}
        result = self._run(campaign_context=context, tamper_echo=True)
        self.assertEqual(result['status'], 'failed')
        self.assertFalse((self.target / 'rows.json').exists())

    def test_campaign_fresh_reader_rejects_bad_plan_before_payload_read(self):
        directory = self.target / 'owned-reader'
        directory.mkdir(parents=True)
        invocation = {
            'format': reread.CAMPAIGN_INVOCATION_FORMAT,
            'source_root': str(self.source), 'output_root': str(self.target),
            'manifest_path': str(self.manifest_path),
            'manifest_pin': self.manifest_pin, 'external_pins': {},
            'source_snapshots': {}, 'chunk_index': 0,
            'current_revision': CURRENT_REVISION,
            'current_source': {}, 'runtime': {}, 'invocation_id': 'test',
            'campaign_context': {
                'plan_path': str(self.target / 'missing-plan.json'),
                'anchor_pin': pin(b'plan'),
                'chunk_index': 0, 'attempt': 1},
        }
        path = directory / 'invocation.json'
        raw = v.canonical_json(invocation)
        path.write_bytes(raw)
        with patch.object(reread, '_roots_for_child',
                          return_value=(self.source, self.target,
                                        self.manifest_path)):
            with patch.object(reread.fixture,
                              'read_invented_registered_attempt',
                              side_effect=AssertionError('payload read started')):
                self.assertEqual(reread.reader_worker_main(
                    [str(path), reread._pin(raw)['sha256']]), 2)
        self.assertFalse((self.target / 'rows.json').exists())

    def test_full_fresh_reader_mismatch_rejects_projection(self):
        result = self._run(changed_reader=True)
        self.assertEqual(result['status'], 'failed')
        self.assertIn('fresh saved reader differs', result['detail'])
        self.assertFalse(result['fresh_reader_equal_prior_reader'])
        self.assertFalse((self.target / 'rows.json').exists())
        self.assertTrue((self.target / 'result.json').exists())

    def test_child_failure_rejects_projection_and_retains_receipts(self):
        result = self._run(child_status='failed')
        self.assertEqual(result['status'], 'failed')
        self.assertFalse(result['external_saved_payloads_reopened_in_child'])
        self.assertFalse((self.target / 'rows.json').exists())
        self.assertTrue((self.target / 'owned-reader/supervision.json').exists())
        self.assertTrue((self.target / 'resource-budget.json').exists())
        self.assertTrue((self.target / 'result.json').exists())

    def test_budget_stop_after_child_rejects_projection(self):
        result = self._run(stop_on=3)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['reason'], 'pipeline_wall_limit')
        self.assertFalse((self.target / 'rows.json').exists())
        self.assertFalse(result['budget_passed'])
        self.assertTrue((self.target / 'result.json').exists())


if __name__ == '__main__':
    unittest.main()
