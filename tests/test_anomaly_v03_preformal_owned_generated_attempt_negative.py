"""Small adversarial checks for the invented generator/reader ownership chain."""
from __future__ import annotations

from contextlib import nullcontext
import os
from pathlib import Path
import secrets
import shutil
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03_preformal_owned_generated_attempt as generated


REVISION = 'a' * 40


class FakeOuterBudget:
    def __init__(self, *, checkpoint_stop=None, probe_stop=None):
        self.checkpoint_stop = checkpoint_stop
        self.probe_stop = probe_stop
        self.phase = None
        self.checkpoints = []
        self.roles = []

    def checkpoint(self, phase):
        self.phase = phase
        self.checkpoints.append(phase)
        if phase == self.checkpoint_stop:
            raise generated.resources.ResourceStop('pipeline_wall_limit')

    def probe(self):
        return 'pipeline_directory_limit' if self.phase == self.probe_stop else None

    def record_role(self, role, status, pin, pid, exit_confirmed):
        self.roles.append((role, status, pin, pid, exit_confirmed))


class OwnedGeneratedAttemptNegativeTests(unittest.TestCase):
    def setUp(self):
        self.roots = []

    def tearDown(self):
        for root in self.roots:
            resolved = root.resolve(strict=True)
            self.assertEqual(resolved.parent, generated.ROOT / 'artifacts')
            self.assertTrue(resolved.name.startswith(generated.fixture.PREFIX))
            shutil.rmtree(resolved)

    def root(self, suffix=None):
        if suffix is None:
            for _ in range(10):
                name = generated.fixture.PREFIX + 'n' + secrets.token_hex(2)
                root = generated.ROOT / 'artifacts' / name
                try:
                    root.mkdir()
                except FileExistsError:
                    continue
                self.roots.append(root)
                return root
            self.fail('could not allocate a short dedicated test root')
        root = generated.ROOT / 'artifacts' / (generated.fixture.PREFIX + suffix)
        root.mkdir()
        self.roots.append(root)
        return root

    @staticmethod
    def content_and_pins(root):
        names = generated._outputs(root, 0)
        registry = (generated.ROOT /
                    'examples/configs/anomaly-v03-freeze-registry.json').read_bytes()
        content = {logical: b'{}' for logical in names}
        content['saved/registry.json'] = registry
        pins = {logical: generated.copied._pin(raw)
                for logical, raw in content.items()}
        return names, content, pins

    @staticmethod
    def reader_result(pins):
        return {
            'format': generated.fixture.FORMAT,
            'status': 'latest_chunk_saved_bytes_bound',
            'mode': generated.saved.MODE,
            'chunk_index': 0, 'latest_state': 'complete',
            'latest_attempt': 1, 'latest_rows_bound': 6,
            'scope': 'invented-registered-format-actual-attempt-layout-only',
            'fixture_physical_layout': 'run-attempt-result-payload',
            'fixture_saved_files_read': True, 'fixture_files_read': 22,
            'registered_evaluation_contracts_checked': 6,
            'saved_payload_bytes_verified': True,
            'external_report_bytes_verified': True,
            'reported_score_ledger_recomputed': True,
            'reported_score_to_primary_summary_checked': True,
            'reported_score_to_slice_summary_recomputed': True,
            'receipt_pin': pins['saved/receipt.json'],
            'report_pin': pins['saved/report.json'],
            'payload_pins': {key: value for key, value in pins.items()
                             if key not in generated.copied.SAVED},
            'invented_registered_format_observations_read': True,
            'invented_observation_profile_score_recomputed': True,
            'observation_to_profile_recomputed': True,
            'observation_to_score_recomputed': True,
            'observation_to_summary_recomputed': True,
            'source_savepoint_bytes_verified': True,
            'source_snapshots_caller_supplied': True,
            **{key: False for key in (
                'actual_registered_observations_read',
                'registered_observations_read', 'real_saved_chunk_reader_used',
                'reader_result_provenance_authenticated',
                'registered_input_bytes_verified',
                'actual_worker_exit_authenticated', 'campaign_completed',
                'execution_authenticated', 'result_trusted',
                'source_closure_complete', 'runtime_closure_complete',
                'formal_permission', 'analysis_authorized',
                'promotion_allowed', 'independent_s6_complete')},
            'campaign_evaluations_credited': 0,
        }

    def run_fake(self, root, *, mutate_reader=None, corrupt_output=False,
                 reader_exit=0, outer_budget=None):
        names, content, pins = self.content_and_pins(root)
        source = {'revision': REVISION}
        calls = []

        def supervise(argv, cwd, control, limits, *, boundary, on_started,
                      resource_probe=None):
            index = len(calls)
            calls.append(argv)
            boundary()
            control.mkdir()
            if outer_budget is not None:
                self.assertIsNotNone(resource_probe)
                reason = resource_probe()
                if reason is not None:
                    return {'status': 'failed', 'exit_code': None,
                            'worker_started': False,
                            'worker_exit_confirmed': False,
                            'worker_pid': None, 'output': None,
                            'stop_reason': reason}
            else:
                self.assertIsNone(resource_probe)
            pid = 401 + index
            on_started(SimpleNamespace(pid=pid, _handle=pid))
            if index == 0:
                self.assertEqual(control, root / 'owned-generator/worker')
                for logical, relative in names.items():
                    target = root / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(content[logical])
                if corrupt_output:
                    (root / next(relative for logical, relative in names.items()
                                 if logical.startswith('datasets/'))).write_bytes(b'bad')
                invocation = generated.v.strict_json((root /
                    'owned-generator/invocation.json').read_bytes())
                reply = {
                    'format': generated.FORMAT, 'status': 'generated',
                    'invocation_id': invocation['invocation_id'],
                    'process': {'pid': pid, 'parent_pid': os.getpid(),
                                'start_token': 'token-' + str(pid)},
                    'recipe_id': generated.RECIPE, 'output_pins': pins,
                    'output_file_count': 22,
                    'output_bytes': sum(p['bytes'] for p in pins.values()),
                    'source_before': source, 'source_after': source,
                    'runtime_before': {}, 'runtime_after': {},
                    'invented_generation_executed': True,
                    'registered_seed_consumed': False,
                    'actual_registered_observations_read': False,
                    'formal_permission': False,
                }
            else:
                self.assertEqual(control, root / 'owned-reader/worker')
                self.assertTrue((root / 'owned-generator/supervision.json').exists())
                if reader_exit:
                    return {'status': 'failed', 'exit_code': reader_exit,
                            'worker_started': True,
                            'worker_exit_confirmed': True,
                            'worker_pid': pid, 'output': None}
                invocation = generated.v.strict_json((root /
                    'owned-reader/invocation.json').read_bytes())
                read = self.reader_result(pins)
                if mutate_reader is not None:
                    mutate_reader(read)
                reply = {
                    'format': generated.copied.READER_FORMAT,
                    'status': 'read',
                    'invocation_id': invocation['invocation_id'],
                    'process': {'pid': pid, 'parent_pid': os.getpid(),
                                'start_token': 'token-' + str(pid)},
                    'output_pins': pins,
                    'source_before': source, 'source_after': source,
                    'runtime_before': {}, 'runtime_after': {},
                    'reader_result': read, 'formal_permission': False,
                }
            raw = generated.v.canonical_json(reply)
            (control / 'report.json').write_bytes(raw)
            boundary()
            return {'status': 'complete', 'exit_code': 0,
                    'worker_started': True, 'worker_exit_confirmed': True,
                    'worker_pid': pid,
                    'output': generated.copied._pin(raw)}

        with patch.object(generated, '_source', return_value=source), \
             patch.object(generated, '_validated_snapshots',
                          return_value=SimpleNamespace()), \
             patch.object(generated.copied, '_source', return_value=source), \
             patch.object(generated.runtime, 'probe_runtime', return_value={}), \
             patch.object(generated.platform, '_platform_scope',
                          return_value=nullcontext()), \
             patch.object(generated.observed, 'creation_observation',
                          side_effect=lambda pid, handle=None: {
                              'pid': pid, 'start_token': 'token-' + str(pid)}), \
             patch.object(generated.supervisor, 'supervise',
                          side_effect=supervise), \
             patch.object(generated.copied, '_saved_outputs',
                          return_value=(names, 1)):
            result = generated.generate_and_read(
                root, expected_pins=pins,
                source_snapshots={REVISION: {}},
                expected_revision=REVISION,
                outer_budget=outer_budget)
        return result, calls

    def test_valid_mock_chain_is_a_rejection_control(self):
        result, calls = self.run_fake(self.root())
        self.assertEqual(result['status'], 'verified', result.get('detail'))
        self.assertEqual(len(calls), 2)
        self.assertTrue(result['invented_generation_executed'])
        self.assertFalse(result['formal_permission'])

    def test_forged_reader_control_pins_or_semantics_do_not_verify(self):
        mutations = {
            'missing receipt pin': lambda read: read.pop('receipt_pin'),
            'wrong report pin': lambda read: read.update(
                report_pin=generated.copied._pin(b'forged')),
            'missing payload pins': lambda read: read.pop('payload_pins'),
            'false saved byte check': lambda read: read.update(
                saved_payload_bytes_verified=False),
            'false score audit': lambda read: read.update(
                reported_score_ledger_recomputed=False),
            'false source snapshot': lambda read: read.update(
                source_snapshots_caller_supplied=False),
            'formal observation flag': lambda read: read.update(
                invented_registered_format_observations_read=False),
            'wrong fixture scope': lambda read: read.update(scope='formal'),
        }
        for label, mutation in mutations.items():
            with self.subTest(label=label):
                root = self.root()
                result, calls = self.run_fake(root, mutate_reader=mutation)
                self.assertEqual(len(calls), 2)
                self.assertEqual(result['status'], 'failed')
                self.assertEqual(result['failed_stage'], 'reader')
                self.assertNotIn('reader_result', result)
                self.assertFalse(result['formal_permission'])
                self.assertTrue((root / 'owned-reader/supervision.json').exists())
                self.assertTrue((root / 'owned-generator/result.json').exists())

    def test_generator_output_mismatch_prevents_reader(self):
        root = self.root()
        result, calls = self.run_fake(root, corrupt_output=True)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['failed_stage'], 'generator')
        self.assertEqual(len(calls), 1)
        self.assertFalse(result['owned_fixture_reader_executed'])
        self.assertTrue((root / 'owned-generator/supervision.json').exists())
        self.assertFalse((root / 'owned-reader').exists())

    def test_reader_nonzero_retains_generator_evidence(self):
        root = self.root()
        result, calls = self.run_fake(root, reader_exit=2)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['failed_stage'], 'reader')
        self.assertEqual(len(calls), 2)
        self.assertTrue(result['owned_fixture_generator_exit_confirmed'])
        self.assertTrue(result['owned_fixture_reader_exit_confirmed'])
        self.assertEqual(result['generated_file_count'], 22)
        self.assertNotIn('reader_result', result)
        self.assertTrue((root / 'owned-generator/supervision.json').exists())
        self.assertTrue((root / 'owned-reader/supervision.json').exists())

    def test_preflight_rejects_bad_pin_path_and_recipe_with_receipt(self):
        for reason in ('bad registry pin', 'long output path', 'bad recipe'):
            with self.subTest(reason=reason):
                root = self.root('n' + 'x' * 30) if reason == 'long output path' \
                    else self.root()
                if reason == 'bad registry pin':
                    _, _, pins = self.content_and_pins(root)
                    pins['saved/registry.json'] = generated.copied._pin(b'bad')
                elif reason == 'bad recipe':
                    _, _, pins = self.content_and_pins(root)
                else:
                    pins = {}
                with patch.object(generated.supervisor, 'supervise',
                                  side_effect=AssertionError('child started')):
                    result = generated.generate_and_read(
                        root, expected_pins=pins,
                        source_snapshots={REVISION: {}},
                        expected_revision=REVISION,
                        recipe_id='unknown' if reason == 'bad recipe'
                        else generated.RECIPE)
                self.assertEqual(result['status'], 'failed')
                self.assertEqual(result['failed_stage'], 'generator')
                self.assertFalse(result['owned_fixture_generator_executed'])
                self.assertFalse(result['owned_fixture_reader_executed'])
                self.assertFalse((root / 'saved').exists())
                self.assertFalse((root / 'run-root').exists())
                receipt = root / 'owned-generator/result.json'
                self.assertTrue(receipt.exists())
                self.assertEqual(generated.v.strict_json(
                    receipt.read_bytes())['status'], 'failed')

    def test_source_snapshot_inventory_rejects_before_generator_child(self):
        snapshots = {
            'empty required files': {REVISION: {}},
            'wrong revision': {'b' * 40: {
                name: b'fake' for name in generated.SNAPSHOT_FILES}},
            'extra invented path': {REVISION: {
                **{name: b'fake' for name in generated.SNAPSHOT_FILES},
                'src/invented-snapshot.py': b'fake'}},
        }
        for label, source_snapshots in snapshots.items():
            with self.subTest(label=label):
                root = self.root()
                _, _, pins = self.content_and_pins(root)
                with patch.object(generated.supervisor, 'supervise',
                                  side_effect=AssertionError('child started')):
                    result = generated.generate_and_read(
                        root, expected_pins=pins,
                        source_snapshots=source_snapshots,
                        expected_revision=REVISION)
                self.assertEqual(result['status'], 'failed')
                self.assertEqual(result['failed_stage'], 'generator')
                self.assertFalse(result['owned_fixture_generator_executed'])
                self.assertFalse(result['owned_fixture_reader_executed'])
                self.assertFalse((root / 'saved').exists())
                self.assertFalse((root / 'run-root').exists())
                self.assertEqual(generated.v.strict_json((root /
                    'owned-generator/result.json').read_bytes())['status'],
                    'failed')

    def test_one_outer_budget_probes_and_records_both_owned_roles(self):
        budget = FakeOuterBudget()
        result, calls = self.run_fake(self.root(), outer_budget=budget)
        self.assertEqual(result['status'], 'verified')
        self.assertEqual(len(calls), 2)
        self.assertEqual(budget.checkpoints,
                         ['preflight', 'generator', 'reader', 'postflight'])
        self.assertEqual([(role, status, confirmed)
                          for role, status, _, _, confirmed in budget.roles],
                         [('generator', 'complete', True),
                          ('reader', 'complete', True)])

    def test_outer_stop_before_reader_retains_generator_and_skips_reader(self):
        budget = FakeOuterBudget(checkpoint_stop='reader')
        root = self.root()
        result, calls = self.run_fake(root, outer_budget=budget)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['reason'], 'pipeline_wall_limit')
        self.assertEqual(result['failed_stage'], 'reader')
        self.assertEqual(len(calls), 1)
        self.assertEqual([row[0] for row in budget.roles], ['generator'])
        self.assertTrue((root / 'owned-generator/supervision.json').exists())
        self.assertFalse((root / 'owned-reader').exists())

    def test_outer_stop_during_each_owned_role_prevents_verification(self):
        for phase, calls_expected in (('generator', 1), ('reader', 2)):
            with self.subTest(phase=phase):
                budget = FakeOuterBudget(probe_stop=phase)
                root = self.root()
                result, calls = self.run_fake(root, outer_budget=budget)
                self.assertEqual(result['status'], 'failed')
                self.assertEqual(len(calls), calls_expected)
                self.assertFalse(result['formal_permission'])
                self.assertNotIn('reader_result', result)
                self.assertEqual(budget.roles[-1][0], phase)
                self.assertEqual(budget.roles[-1][1], 'failed')
                self.assertTrue((root / 'owned-generator/result.json').exists())

    def test_outer_postflight_stop_overrides_inner_success(self):
        budget = FakeOuterBudget(checkpoint_stop='postflight')
        root = self.root()
        result, calls = self.run_fake(root, outer_budget=budget)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['reason'], 'pipeline_wall_limit')
        self.assertEqual(len(calls), 2)
        self.assertEqual([row[0] for row in budget.roles],
                         ['generator', 'reader'])
        self.assertNotIn('reader_result', result)
        self.assertTrue((root / 'owned-reader/supervision.json').exists())


if __name__ == '__main__':
    unittest.main()
