"""Bounded invented input, owned-copy and saved-reader boundary checks."""
from __future__ import annotations

from contextlib import nullcontext, redirect_stdout
import copy
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import _anomaly_v03_io as io
from banto_ai import anomaly_v03_preformal_owned_saved_attempt as owned
from banto_ai import anomaly_v03_registered_saved_attempt_fixture as fixture
from banto_ai import anomaly_v03_registered_saved_summary as saved


class OwnedSavedAttemptMaterializerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(
            prefix=fixture.PREFIX, dir=owned.ROOT / 'artifacts')
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def _input(self, *, latest='complete'):
        receipt = {'format': saved.RECEIPT_FORMAT, 'mode': saved.MODE,
                   'invented_only': True, 'chunk_index': 0,
                   'attempts': [{'attempt': 1, 'state': latest}]}
        savepoint = {'format': fixture.SAVEPOINT_FORMAT, 'mode': saved.MODE,
                     'invented_only': True, 'campaign_completed': False,
                     'actual_registered_observations_read': False,
                     'run_root': str(self.root / 'run-root'), 'chunk_index': 0}
        names = fixture._names(0, 1)[1]
        payloads = {logical: b'{}' for logical in names}
        registry = (owned.ROOT /
                    'examples/configs/anomaly-v03-freeze-registry.json').read_bytes()
        content = {'saved/savepoint.json': v.canonical_json(savepoint),
                   'saved/registry.json': registry,
                   'saved/receipt.json': v.canonical_json(receipt),
                   'saved/report.json': b'{}', **payloads}
        pins = {name: owned._pin(raw) for name, raw in content.items()}
        for logical, relative in owned._input_names(names).items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content[logical])
        return names, pins

    def _mock_reader_result(self, pins):
        payload_pins = {key: value for key, value in pins.items()
                        if key not in owned.SAVED}
        return {
            'format': fixture.FORMAT,
            'status': 'latest_chunk_saved_bytes_bound',
            'mode': saved.MODE,
            'chunk_index': 0,
            'latest_state': 'complete',
            'latest_attempt': 1,
            'latest_rows_bound': 6,
            'scope': 'invented-registered-format-actual-attempt-layout-only',
            'fixture_physical_layout': 'run-attempt-result-payload',
            'fixture_saved_files_read': True,
            'fixture_files_read': 22,
            'registered_evaluation_contracts_checked': 6,
            'saved_payload_bytes_verified': True,
            'external_report_bytes_verified': True,
            'reported_score_ledger_recomputed': True,
            'reported_score_to_primary_summary_checked': True,
            'reported_score_to_slice_summary_recomputed': True,
            'receipt_pin': pins['saved/receipt.json'],
            'report_pin': pins['saved/report.json'],
            'payload_pins': payload_pins,
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

    def _fake_two_workers(self, pins, *, reader_status='complete',
                          reader_mutation=None, materializer_mutation=None):
        inputs, outputs = owned._preflight(self.root, 0, pins)
        source = {'revision': 'a' * 40}
        snapshots = {'a' * 40: {'src/invented-specimen.py': b'# specimen\n'}}
        calls = []

        def supervise(argv, cwd, control, limits, *, boundary, on_started):
            index = len(calls)
            calls.append((argv, control))
            boundary()
            control.mkdir()
            pid = 101 + index
            on_started(SimpleNamespace(pid=pid, _handle=pid))
            if index == 0:
                self.assertEqual(control, self.root / 'owned-materializer/worker')
                for logical, relative in outputs.items():
                    target = self.root / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes((self.root / inputs[logical]).read_bytes())
                if materializer_mutation is not None:
                    materializer_mutation(self.root, outputs)
                invocation = v.strict_json((self.root /
                    'owned-materializer/invocation.json').read_bytes())
                reply = {'format': owned.FORMAT, 'status': 'materialized',
                         'invocation_id': invocation['invocation_id'],
                         'process': {'pid': pid, 'parent_pid': os.getpid(),
                                     'start_token': 'token-' + str(pid)},
                         'input_pins': pins, 'output_pins': pins,
                         'source_before': source, 'source_after': source,
                         'runtime_before': {}, 'runtime_after': {},
                         'input_origin': 'caller_declared_invented',
                         'generation_verified': False,
                         'actual_registered_producer_executed': False,
                         'actual_registered_observations_read': False,
                         'formal_permission': False}
            else:
                self.assertEqual(control, self.root / 'owned-reader/worker')
                self.assertTrue((self.root /
                    'owned-materializer/supervision.json').exists())
                self.assertEqual(argv[1:5], ['-I', '-S', '-B', '-c'])
                invocation = v.strict_json((self.root /
                    'owned-reader/invocation.json').read_bytes())
                self.assertEqual(owned._decode_source_snapshots(
                    invocation['source_snapshots']), snapshots)
                if reader_status != 'complete':
                    return {'status': 'failed', 'exit_code': 2,
                            'worker_started': True,
                            'worker_exit_confirmed': True,
                            'worker_pid': pid, 'output': None}
                reply = {'format': owned.READER_FORMAT, 'status': 'read',
                         'invocation_id': invocation['invocation_id'],
                         'process': {'pid': pid, 'parent_pid': os.getpid(),
                                     'start_token': 'token-' + str(pid)},
                         'output_pins': pins, 'source_before': source,
                         'source_after': source,
                         'runtime_before': {}, 'runtime_after': {},
                         'reader_result': self._mock_reader_result(pins),
                         'formal_permission': False}
                if reader_mutation is not None:
                    reader_mutation(reply)
            raw = v.canonical_json(reply)
            (control / 'report.json').write_bytes(raw)
            boundary()
            return {'status': 'complete', 'exit_code': 0,
                    'worker_started': True, 'worker_exit_confirmed': True,
                    'worker_pid': pid, 'output': owned._pin(raw)}

        return supervise, snapshots, calls

    def _run_fake_chain(self, pins, supervise, snapshots):
        with patch.object(owned, '_source', return_value={'revision': 'a' * 40}), \
             patch.object(owned.runtime, 'probe_runtime', return_value={}), \
             patch.object(owned.platform, '_platform_scope',
                          return_value=nullcontext()), \
             patch.object(owned.observed, 'creation_observation',
                          side_effect=lambda pid, handle=None: {
                              'pid': pid, 'start_token': 'token-' + str(pid)}), \
             patch.object(owned.supervisor, 'supervise',
                          side_effect=supervise), \
             patch.object(owned.fixture, 'read_invented_registered_attempt',
                          side_effect=AssertionError('parent reader forbidden')):
            return owned.materialize_and_read(
                self.root, expected_mode=saved.MODE, chunk_index=0,
                expected_registry_pin=pins['saved/registry.json'],
                expected_savepoint_pin=pins['saved/savepoint.json'],
                expected_receipt_pin=pins['saved/receipt.json'],
                expected_report_pin=pins['saved/report.json'],
                expected_payload_pins={key: value for key, value in pins.items()
                                       if key not in owned.SAVED},
                source_snapshots=snapshots, expected_revision='a' * 40)

    def test_separate_owned_reader_starts_after_materializer_exit_and_pins(self):
        _, pins = self._input()
        supervise, snapshots, calls = self._fake_two_workers(pins)
        result = self._run_fake_chain(pins, supervise, snapshots)
        self.assertEqual(result['status'], 'verified', result.get('detail'))
        self.assertEqual(result['format'], owned.CHAIN_FORMAT)
        self.assertEqual(len(calls), 2)
        self.assertEqual(result['owned_fixture_materializer_pid'], 101)
        self.assertEqual(result['owned_fixture_reader_pid'], 102)
        self.assertTrue(result['owned_fixture_reader_exit_confirmed'])
        self.assertEqual(result['owned_fixture_reader_start_token'], 'token-102')
        self.assertEqual(result['reader_result']['registered_evaluation_contracts_checked'], 6)
        self.assertFalse(result['actual_worker_exit_authenticated'])
        self.assertFalse(result['formal_permission'])
        reader_path = self.root / 'owned-reader/invocation.json'
        with patch.object(owned, '_source', return_value={'revision': 'a' * 40}), \
             patch.object(owned.runtime, 'probe_runtime', return_value={}), \
             patch.object(owned.observed, 'creation_observation',
                          return_value={'pid': os.getpid(), 'start_token': 'self'}), \
             patch.object(owned.fixture, 'read_invented_registered_attempt',
                          return_value=self._mock_reader_result(pins)) as reader:
            rejected = StringIO()
            with redirect_stdout(rejected):
                wrong = owned.reader_worker_main([str(reader_path), '0' * 64])
            self.assertEqual(wrong, 2)
            reader.assert_not_called()
            output = StringIO()
            with redirect_stdout(output):
                code = owned.reader_worker_main(
                    [str(reader_path), result['reader_invocation_pin']['sha256']])
        self.assertEqual(code, 0, output.getvalue())
        self.assertEqual(json.loads(output.getvalue())['status'], 'read')
        self.assertEqual(reader.call_args.kwargs['source_snapshots'], snapshots)

    def test_bad_materializer_output_stops_before_reader_launch(self):
        _, pins = self._input()

        def corrupt(root, outputs):
            logical = next(key for key in outputs if key not in owned.SAVED)
            (root / outputs[logical]).write_bytes(b'changed')

        supervise, snapshots, calls = self._fake_two_workers(
            pins, materializer_mutation=corrupt)
        result = self._run_fake_chain(pins, supervise, snapshots)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(len(calls), 1)
        self.assertFalse(result['owned_fixture_reader_executed'])
        self.assertFalse((self.root / 'owned-reader').exists())

    def test_reader_nonzero_retains_both_role_supervisions_and_materializer_pins(self):
        _, pins = self._input()
        supervise, snapshots, calls = self._fake_two_workers(
            pins, reader_status='failed')
        result = self._run_fake_chain(pins, supervise, snapshots)
        self.assertEqual(len(calls), 2)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['failed_stage'], 'reader')
        self.assertTrue(result['owned_fixture_materializer_exit_confirmed'])
        self.assertTrue(result['owned_fixture_reader_exit_confirmed'])
        self.assertEqual(result['materializer_file_count'], 22)
        self.assertNotIn('reader_result', result)
        self.assertTrue((self.root / 'owned-materializer/supervision.json').exists())
        self.assertEqual(v.strict_json((self.root /
            'owned-reader/supervision.json').read_bytes())['exit_code'], 2)

    def test_reader_unreaped_recovery_keeps_materializer_supervision(self):
        _, pins = self._input()
        ordinary, snapshots, calls = self._fake_two_workers(pins)
        report = {'worker_started': True, 'worker_pid': 102,
                  'worker_exit_confirmed': False, 'status': 'failed'}
        unreaped = owned.supervisor.UnreapedWorker(object(), report)

        def supervise(argv, cwd, control, limits, *, boundary, on_started):
            if len(calls) == 1:
                boundary()
                control.mkdir()
                raise unreaped
            return ordinary(argv, cwd, control, limits,
                            boundary=boundary, on_started=on_started)

        with patch.object(owned.supervisor, 'retain_until_exit') as recover:
            result = self._run_fake_chain(pins, supervise, snapshots)
        recover.assert_called_once_with(unreaped)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['reason'], 'unreaped_reader_reconciled_failure')
        self.assertTrue(result['owned_fixture_materializer_exit_confirmed'])
        self.assertFalse(result['owned_fixture_reader_exit_confirmed'])
        self.assertTrue(result['owned_fixture_reader_exit_reconciled'])
        self.assertTrue((self.root / 'owned-materializer/supervision.json').exists())
        self.assertTrue((self.root / 'owned-reader/supervision.json').exists())
        self.assertNotIn('reader_result', result)

    def test_forged_reader_pid_and_formal_flag_cannot_verify(self):
        for mutation in (
            lambda reply: reply['process'].update(pid=999),
            lambda reply: reply['reader_result'].update(formal_permission=True),
            lambda reply: reply['reader_result'].update(
                saved_payload_bytes_verified=False),
        ):
            with self.subTest(mutation=mutation):
                if (self.root / 'owned-materializer').exists():
                    self.temporary.cleanup()
                    self.temporary = tempfile.TemporaryDirectory(
                        prefix=fixture.PREFIX, dir=owned.ROOT / 'artifacts')
                    self.root = Path(self.temporary.name)
                _, pins = self._input()
                supervise, snapshots, _ = self._fake_two_workers(
                    pins, reader_mutation=mutation)
                result = self._run_fake_chain(pins, supervise, snapshots)
                self.assertEqual(result['status'], 'failed')
                self.assertEqual(result['failed_stage'], 'reader')
                self.assertTrue(result['owned_fixture_reader_exit_confirmed'])
                self.assertFalse(result['formal_permission'])
                self.assertTrue((self.root / 'owned-reader/supervision.json').exists())

    def test_exact_22_invented_input_files_and_physical_attempt_names(self):
        names, pins = self._input()
        inputs, outputs = owned._preflight(self.root, 0, pins)
        self.assertEqual((len(inputs), len(outputs)), (22, 22))
        self.assertEqual(set(inputs), set(outputs))
        self.assertEqual(outputs['saved/receipt.json'], 'saved/receipt.json')
        self.assertTrue(all(value.startswith(
            'run-root/run/attempts/chunks/000/attempt-0001/result/payload/')
            for key, value in outputs.items() if key not in owned.SAVED))
        self.assertEqual(len(names), 18)
        self.assertFalse((self.root / 'run-root').exists())

    def test_external_pin_and_extra_input_reject_before_child(self):
        _, pins = self._input()
        bad = dict(pins)
        bad['saved/report.json'] = owned._pin(b'wrong')
        with self.assertRaisesRegex(ValueError, 'pinned file'):
            owned._preflight(self.root, 0, bad)
        extra = self.root / 'inbox/payloads/extra.json'
        extra.write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError, 'exact invented materializer'):
            owned._preflight(self.root, 0, pins)

    def test_payload_pin_cannot_shadow_explicit_saved_pin(self):
        _, pins = self._input()
        payload_pins = {key: value for key, value in pins.items()
                        if key not in owned.SAVED}
        payload_pins['saved/savepoint.json'] = pins['saved/savepoint.json']
        with patch.object(owned.supervisor, 'supervise',
                          side_effect=AssertionError('child must not start')):
            result = owned.materialize_and_read(
                self.root, expected_mode=saved.MODE, chunk_index=0,
                expected_registry_pin=pins['saved/registry.json'],
                expected_savepoint_pin=owned._pin(b'wrong explicit savepoint'),
                expected_receipt_pin=pins['saved/receipt.json'],
                expected_report_pin=pins['saved/report.json'],
                expected_payload_pins=payload_pins,
                source_snapshots={}, expected_revision='a' * 40)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['failed_stage'], 'materializer')
        self.assertIn('saved pin key forbidden', result['detail'])
        self.assertFalse(result['owned_fixture_materializer_executed'])
        self.assertFalse(result['owned_fixture_reader_executed'])
        self.assertFalse((self.root / 'saved').exists())
        self.assertFalse((self.root / 'run-root').exists())
        self.assertEqual(v.strict_json((self.root /
            'owned-materializer/result.json').read_bytes())['status'], 'failed')

    def test_failed_prior_attempt_selects_only_latest_physical_attempt(self):
        _, pins = self._input()
        receipt_path = self.root / 'inbox/saved/receipt.json'
        receipt = v.strict_json(receipt_path.read_bytes())
        receipt['attempts'] = [
            {'attempt': 1, 'state': 'failed'},
            {'attempt': 2, 'state': 'complete'}]
        receipt_raw = v.canonical_json(receipt)
        receipt_path.write_bytes(receipt_raw)
        pins['saved/receipt.json'] = owned._pin(receipt_raw)
        _, outputs = owned._preflight(self.root, 0, pins)
        self.assertTrue(all('attempt-0002/' in value for key, value
                            in outputs.items() if key not in owned.SAVED))
        self.assertFalse(any('attempt-0001/' in value
                             for value in outputs.values()))

    def test_latest_failed_attempt_stops_before_materializer_and_retains_receipt(self):
        _, pins = self._input(latest='failed')
        with patch.object(owned.supervisor, 'supervise',
                          side_effect=AssertionError('child must not start')):
            result = owned.materialize_and_read(
                self.root, expected_mode=saved.MODE, chunk_index=0,
                expected_registry_pin=pins['saved/registry.json'],
                expected_savepoint_pin=pins['saved/savepoint.json'],
                expected_receipt_pin=pins['saved/receipt.json'],
                expected_report_pin=pins['saved/report.json'],
                expected_payload_pins={k: p for k, p in pins.items()
                                       if k not in owned.SAVED},
                source_snapshots={}, expected_revision='a' * 40)
        self.assertEqual(result['status'], 'failed')
        self.assertIn('latest invented attempt is not complete', result['detail'])
        self.assertFalse(result['owned_fixture_materializer_executed'])
        self.assertEqual(v.strict_json((self.root / 'owned-materializer/result.json')
                                       .read_bytes())['status'], 'failed')
        self.assertFalse((self.root / 'saved').exists())
        self.assertFalse((self.root / 'run-root').exists())

    def test_formal_mode_has_no_output(self):
        with self.assertRaisesRegex(ValueError, 'formal materializer mode'):
            owned.materialize_and_read(
                self.root, expected_mode='formal', chunk_index=0,
                expected_registry_pin={}, expected_savepoint_pin={},
                expected_receipt_pin={}, expected_report_pin={},
                expected_payload_pins={}, source_snapshots={},
                expected_revision='a' * 40)
        self.assertFalse((self.root / 'owned-materializer').exists())

    def test_native_source_check_requires_clean_expected_head(self):
        revision = 'a' * 40
        with patch.object(owned.subprocess, 'check_output',
                          side_effect=[revision.encode(), b' M tracked.py\n']):
            with self.assertRaisesRegex(ValueError, 'clean materializer checkout'):
                owned._source(revision)

    def test_isolated_bootstrap_imports_fixture_worker(self):
        # The worker rejects an empty invocation only after the repository
        # package has imported under isolated Python startup.
        completed = subprocess.run(
            [sys.executable, '-I', '-S', '-B', '-c', owned.BOOTSTRAP,
             str(owned.ROOT / 'src')], cwd=owned.ROOT,
            capture_output=True, text=True, timeout=15, check=False)
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(json.loads(completed.stdout), {
            'format': owned.FORMAT, 'status': 'failed',
            'error_type': 'V03ValidationError',
            'detail': 'materializer worker arguments',
            'formal_permission': False})

    def test_worker_failure_after_launch_retains_failed_receipt_and_exit(self):
        _, pins = self._input()
        failed_monitor = {'status': 'failed', 'exit_code': 2,
                          'worker_started': True, 'worker_exit_confirmed': True,
                          'worker_pid': 123, 'output': None}
        with patch.object(owned, '_source', return_value={'revision': 'a' * 40}), \
             patch.object(owned.runtime, 'probe_runtime', return_value={}), \
             patch.object(owned.platform, '_platform_scope', return_value=nullcontext()), \
             patch.object(owned.supervisor, 'supervise',
                          return_value=failed_monitor) as supervise:
            result = owned.materialize_and_read(
                self.root, expected_mode=saved.MODE, chunk_index=0,
                expected_registry_pin=pins['saved/registry.json'],
                expected_savepoint_pin=pins['saved/savepoint.json'],
                expected_receipt_pin=pins['saved/receipt.json'],
                expected_report_pin=pins['saved/report.json'],
                expected_payload_pins={k: p for k, p in pins.items()
                                       if k not in owned.SAVED},
                source_snapshots={}, expected_revision='a' * 40)
        self.assertEqual(supervise.call_args.args[0][:6],
                         [sys.executable, '-I', '-S', '-B', '-c', owned.BOOTSTRAP])
        self.assertEqual(result['status'], 'failed')
        self.assertTrue(result['owned_fixture_materializer_exit_confirmed'])
        self.assertEqual(result['owned_fixture_materializer_pid'], 123)
        self.assertFalse(result['generation_verified'])
        self.assertFalse(result['formal_permission'])
        self.assertFalse((self.root / 'run-root').exists())
        self.assertTrue((self.root / 'owned-materializer/supervision.json').exists())

    def test_unreaped_child_is_recovered_but_original_exit_stays_unconfirmed(self):
        _, pins = self._input()
        report = {'worker_started': True, 'worker_pid': 123,
                  'worker_exit_confirmed': False, 'status': 'failed'}
        unreaped = owned.supervisor.UnreapedWorker(object(), report)
        with patch.object(owned, '_source', return_value={'revision': 'a' * 40}), \
             patch.object(owned.runtime, 'probe_runtime', return_value={}), \
             patch.object(owned.platform, '_platform_scope', return_value=nullcontext()), \
             patch.object(owned.supervisor, 'supervise', side_effect=unreaped), \
             patch.object(owned.supervisor, 'retain_until_exit') as recover:
            result = owned.materialize_and_read(
                self.root, expected_mode=saved.MODE, chunk_index=0,
                expected_registry_pin=pins['saved/registry.json'],
                expected_savepoint_pin=pins['saved/savepoint.json'],
                expected_receipt_pin=pins['saved/receipt.json'],
                expected_report_pin=pins['saved/report.json'],
                expected_payload_pins={k: p for k, p in pins.items()
                                       if k not in owned.SAVED},
                source_snapshots={}, expected_revision='a' * 40)
        recover.assert_called_once_with(unreaped)
        self.assertEqual(result['status'], 'failed')
        self.assertTrue(result['owned_fixture_materializer_exit_reconciled'])
        self.assertFalse(result['owned_fixture_materializer_exit_confirmed'])
        self.assertTrue((self.root / 'owned-materializer/supervision.json').exists())
        self.assertEqual(v.strict_json((self.root / 'owned-materializer/result.json')
                                       .read_bytes())['reason'],
                         'unreaped_materializer_reconciled_failure')
        self.assertFalse((self.root / 'run-root').exists())

    def test_post_copy_inventory_and_pin_reject_added_or_changed_file(self):
        names, pins = self._input()
        inputs, outputs = owned._preflight(self.root, 0, pins)
        for relative in outputs.values():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            logical = next(k for k, v in outputs.items() if v == relative)
            path.write_bytes((self.root / inputs[logical]).read_bytes())
        owned._check_outputs(self.root, outputs, pins)
        (self.root / 'run-root/extra.json').write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError, 'exact invented materializer'):
            owned._check_outputs(self.root, outputs, pins)
        (self.root / 'run-root/extra.json').unlink()
        target = self.root / outputs[next(iter(names))]
        target.write_bytes(b'wrong')
        with self.assertRaisesRegex(ValueError, 'pinned file'):
            owned._check_outputs(self.root, outputs, pins)

    @unittest.skipUnless(os.environ.get('BANTO_RUN_OWNED_REGISTERED_FIXTURE') == '1',
                         'native owned materializer is an explicit post-commit run')
    def test_native_owned_materializer_then_registered_saved_reader(self):
        # Reuse the hand-declared invented observations and reseal only the
        # path-specific partial savepoint.  Require an explicit new, retained
        # artifacts root.  No generator or holdout run occurs.
        retained = os.environ.get('BANTO_OWNED_REGISTERED_ARTIFACT_ROOT')
        if not retained:
            self.skipTest('explicit retained artifact root required')
        candidate = Path(retained).absolute()
        self.assertEqual(candidate.parent, owned.ROOT / 'artifacts')
        self.assertTrue(candidate.name.startswith(fixture.PREFIX))
        self.assertFalse(candidate.exists(), 'native output root must be new')
        candidate.mkdir()
        self.root = candidate
        from tests.test_anomaly_v03_preformal_registered_saved_attempt_fixture import (
            InventedRegisteredSavedAttemptTests as ManualFixture)
        ManualFixture.setUpClass()
        try:
            registry = ManualFixture.registry_raw
            payloads = dict(ManualFixture.payloads)
            savepoint = dict(ManualFixture.savepoint)
            savepoint['run_root'] = str(self.root / 'run-root')
            savepoint_raw = v.canonical_json(savepoint)
            receipt = copy.deepcopy(ManualFixture.receipt)
            receipt['savepoint_pin'] = owned._pin(savepoint_raw)
            receipt_raw = v.canonical_json(receipt)
            report = copy.deepcopy(ManualFixture.report)
            report['savepoint_pin'] = owned._pin(savepoint_raw)
            report['receipt_pin'] = owned._pin(receipt_raw)
            report_raw = v.canonical_json(report)
            content = {'saved/savepoint.json': savepoint_raw,
                       'saved/registry.json': registry,
                       'saved/receipt.json': receipt_raw,
                       'saved/report.json': report_raw, **payloads}
            pins = {name: owned._pin(raw) for name, raw in content.items()}
            names = fixture._names(0, 1)[1]
            for logical, relative in owned._input_names(names).items():
                path = self.root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content[logical])
            revision = subprocess.check_output(
                ['git', '-C', str(owned.ROOT), 'rev-parse', 'HEAD'],
                stderr=subprocess.DEVNULL, timeout=10).decode().strip()
            manifest = {'format': 'anomaly-v03-owned-saved-attempt-external-pins-v1',
                        'artifact_root': str(self.root),
                        'expected_revision': revision,
                        'expected_mode': saved.MODE, 'chunk_index': 0,
                        'input_origin': 'caller_declared_invented',
                        'generation_verified': False,
                        'actual_registered_observations_read': False,
                        'file_pins': pins,
                        'source_snapshot_pins': {
                            revision: {name: owned._pin(raw)
                                       for name, raw in rows.items()}
                            for revision, rows in
                            ManualFixture.source_snapshots.items()}}
            manifest_path = (self.root.parent /
                             (self.root.name + '-external-pins.json'))
            io._exclusive(manifest_path, v.canonical_json(manifest))
            result = owned.materialize_and_read(
                self.root, expected_mode=saved.MODE, chunk_index=0,
                expected_registry_pin=pins['saved/registry.json'],
                expected_savepoint_pin=pins['saved/savepoint.json'],
                expected_receipt_pin=pins['saved/receipt.json'],
                expected_report_pin=pins['saved/report.json'],
                expected_payload_pins={k: p for k, p in pins.items()
                                       if k not in owned.SAVED},
                source_snapshots=ManualFixture.source_snapshots,
                expected_revision=revision)
            io._exclusive(self.root.parent /
                          (self.root.name + '-external-result-pin.json'),
                          v.canonical_json({'artifact_root': str(self.root),
                                            'result_pin': result['result_pin'],
                                            'external_pins_pin': owned._pin(
                                                manifest_path.read_bytes())}))
            self.assertEqual(result['status'], 'verified', result.get('detail'))
            self.assertTrue(result['owned_fixture_materializer_exit_confirmed'])
            self.assertTrue(result['owned_fixture_reader_exit_confirmed'])
            self.assertNotEqual(result['owned_fixture_materializer_pid'],
                                result['owned_fixture_reader_pid'])
            self.assertTrue((self.root / 'owned-reader/supervision.json').exists())
            self.assertEqual(result['materializer_file_count'], 22)
            self.assertEqual(result['reader_result']['registered_evaluation_contracts_checked'], 6)
            self.assertFalse(result['generation_verified'])
            self.assertFalse(result['actual_registered_observations_read'])
            self.assertFalse(result['formal_permission'])
        finally:
            ManualFixture.tearDownClass()


if __name__ == '__main__':
    unittest.main()
