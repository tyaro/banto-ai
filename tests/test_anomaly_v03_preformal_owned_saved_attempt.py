"""Bounded invented input, owned-copy and saved-reader boundary checks."""
from __future__ import annotations

from contextlib import nullcontext
import copy
import os
from pathlib import Path
import subprocess
import tempfile
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

    def test_worker_failure_after_launch_retains_failed_receipt_and_exit(self):
        _, pins = self._input()
        failed_monitor = {'status': 'failed', 'exit_code': 2,
                          'worker_started': True, 'worker_exit_confirmed': True,
                          'worker_pid': 123, 'output': None}
        with patch.object(owned, '_source', return_value={'revision': 'a' * 40}), \
             patch.object(owned.runtime, 'probe_runtime', return_value={}), \
             patch.object(owned.platform, '_platform_scope', return_value=nullcontext()), \
             patch.object(owned.supervisor, 'supervise', return_value=failed_monitor):
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
            self.assertEqual(result['materializer_file_count'], 22)
            self.assertEqual(result['reader_result']['registered_evaluation_contracts_checked'], 6)
            self.assertFalse(result['generation_verified'])
            self.assertFalse(result['actual_registered_observations_read'])
            self.assertFalse(result['formal_permission'])
        finally:
            ManualFixture.tearDownClass()


if __name__ == '__main__':
    unittest.main()
